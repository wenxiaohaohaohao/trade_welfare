from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


PRODUCT_FIELDS = [
    "product_description",
    "analysis_sector",
    "sector_status",
    "first_round_exclusion",
    "is_analysis_sector_eligible",
    "product_mapping_version",
]


def equal_with_missing(left: pd.Series, right: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(left.dtype) and pd.api.types.is_bool_dtype(right.dtype):
        return left.fillna(False) == right.fillna(False)
    return left.astype("string").fillna("<NA>") == right.astype("string").fillna("<NA>")


def merge_panels(trade: pd.DataFrame, treatment: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, int]]:
    merged = trade.merge(
        treatment,
        on=config["join"]["keys"],
        how=config["join"]["type"],
        validate=config["join"]["cardinality"],
        suffixes=("", "_treatment"),
        indicator=True,
    )
    product_mismatches: dict[str, int] = {}
    for field in PRODUCT_FIELDS:
        treatment_field = f"{field}_treatment"
        product_mismatches[field] = int(
            (~equal_with_missing(merged[field], merged[treatment_field])).sum()
        )
        merged = merged.drop(columns=treatment_field)
    merged["trade_treatment_join_status"] = merged["_merge"].map(
        {"both": "matched", "left_only": "unmatched_treatment", "right_only": "unused_treatment"}
    )
    merged = merged.drop(columns="_merge")
    merged["trade_treatment_merge_version"] = config["version"]
    merged["treatment_repeated_across_connectors"] = True
    merged["common_benchmarks_not_additive_across_connectors"] = True
    for column in [
        "trade_treatment_join_status",
        "trade_treatment_merge_version",
    ]:
        merged[column] = merged[column].astype("string")
    for column in [
        "treatment_repeated_across_connectors",
        "common_benchmarks_not_additive_across_connectors",
    ]:
        merged[column] = merged[column].astype("bool")
    return merged.sort_values(["connector_iso3", "analysis_hs6", "year"]).reset_index(drop=True), product_mismatches


def validate(
    project_root: Path,
    config: dict[str, Any],
    trade: pd.DataFrame,
    treatment: pd.DataFrame,
    output: pd.DataFrame,
    product_mismatches: dict[str, int],
) -> dict[str, Any]:
    failures: list[str] = []
    hash_checks = {
        name: sha256(project_root / details["path"]) == details["sha256"]
        for name, details in config["inputs"].items()
    }
    if not all(hash_checks.values()):
        failures.append("one or more configured M2.3 input hashes do not match")
    trade_keys = config["inputs"]["connector_trade_legs"]["natural_key"]
    treatment_keys = config["inputs"]["product_treatment"]["natural_key"]
    trade_duplicates = int(trade.duplicated(trade_keys).sum())
    treatment_duplicates = int(treatment.duplicated(treatment_keys).sum())
    output_duplicates = int(output.duplicated(trade_keys).sum())
    if trade_duplicates or treatment_duplicates or output_duplicates:
        failures.append("trade, treatment, or merged output natural key is duplicated")
    unmatched_trade_rows = int((output["trade_treatment_join_status"] != "matched").sum())
    if unmatched_trade_rows:
        failures.append(f"{unmatched_trade_rows} trade rows did not match product treatment")
    if any(product_mismatches.values()):
        failures.append("product or sector fields differ between trade and treatment inputs")

    reconciliation: dict[str, dict[str, float]] = {}
    tolerance = float(config["reconciliation"]["tolerance_usd"])
    for field in config["reconciliation"]["trade_value_fields"]:
        input_total = float(trade[field].sum())
        output_total = float(output[field].sum())
        gap = output_total - input_total
        reconciliation[field] = {
            "input_total": input_total,
            "output_total": output_total,
            "gap": gap,
        }
        if abs(gap) > tolerance:
            failures.append(f"{field} total changed during treatment merge")

    treatment_fields = [
        "tariffed_product",
        "source_list_ids",
        "tariff_rate",
        "china_import_share_2017",
        "tariff_exposure",
        "policy_mapping_status",
        "treatment_version",
    ]
    unique_counts = output.groupby(treatment_keys)[treatment_fields].nunique(dropna=False)
    inconsistent_treatment_keys = int((unique_counts > 1).any(axis=1).sum())
    if inconsistent_treatment_keys:
        failures.append("treatment fields vary across connectors for the same product-year")
    connector_count = int(output["connector_iso3"].nunique())
    replication_counts = output.groupby(treatment_keys)["connector_iso3"].nunique()
    incomplete_replication_keys = int((replication_counts != connector_count).sum())
    if incomplete_replication_keys:
        failures.append("one or more product-year treatment rows are not repeated for every connector")
    treatment_provenance_missing = int(
        output[["policy_mapping_status", "treatment_version", "treatment_concept"]].isna().any(axis=1).sum()
    )
    if treatment_provenance_missing:
        failures.append("one or more merged rows lack treatment provenance")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": hash_checks,
        "trade_input_row_count": len(trade),
        "treatment_input_row_count": len(treatment),
        "output_row_count": len(output),
        "trade_duplicate_key_count": trade_duplicates,
        "treatment_duplicate_key_count": treatment_duplicates,
        "output_duplicate_key_count": output_duplicates,
        "unmatched_trade_row_count": unmatched_trade_rows,
        "product_field_mismatch_counts": product_mismatches,
        "trade_value_reconciliation": reconciliation,
        "connector_count": connector_count,
        "inconsistent_treatment_product_year_count": inconsistent_treatment_keys,
        "incomplete_treatment_replication_count": incomplete_replication_keys,
        "treatment_provenance_missing_count": treatment_provenance_missing,
        "common_benchmarks_not_additive_across_connectors": True,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Trade-Treatment Merge Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Output rows: `{validation['output_row_count']}`",
        "",
        "## Required checks",
        "",
        f"- Configured input SHA256 checks: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- Unique connector-product-year output key: `{'yes' if validation['output_duplicate_key_count'] == 0 else 'no'}`",
        f"- All trade rows matched treatment: `{'yes' if validation['unmatched_trade_row_count'] == 0 else 'no'}`",
        f"- Product/sector fields identical across inputs: `{'yes' if not any(validation['product_field_mismatch_counts'].values()) else 'no'}`",
        f"- Treatment constant across connectors within product-year: `{'yes' if validation['inconsistent_treatment_product_year_count'] == 0 else 'no'}`",
        f"- Treatment provenance complete: `{'yes' if validation['treatment_provenance_missing_count'] == 0 else 'no'}`",
        "",
        "## Trade-value reconciliation",
        "",
        "| Field | Input total USD | Output total USD | Gap USD |",
        "|---|---:|---:|---:|",
    ]
    for field, record in validation["trade_value_reconciliation"].items():
        lines.append(
            f"| `{field}` | {record['input_total']:.2f} | {record['output_total']:.2f} | {record['gap']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The merge is many-to-one from connector-product-year trade rows to product-year treatment. No trade value changes during the join. Treatment and the China-to-USA benchmark are repeated across connector rows for comparison only; they are non-additive across connectors. Section 301 remains gross statutory initial-action exposure, without historical exclusions or 2024 review changes.",
            "",
        ]
    )
    if validation["failures"]:
        lines.extend(["## Failures", ""] + [f"- {item}" for item in validation["failures"]] + [""])
    return "\n".join(lines)


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge M2.1 treatment into the M2.2 connector trade legs.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/harmonized/connector_trade_hs6_year.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/trade_treatment_merge_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/trade_treatment_merge_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output_path = args.output if args.output.is_absolute() else project_root / args.output
    validation_json = args.validation_json if args.validation_json.is_absolute() else project_root / args.validation_json
    validation_md = args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    for path in [output_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/trade_treatment_merge_rules.yaml")
    trade = pq.read_table(project_root / config["inputs"]["connector_trade_legs"]["path"]).to_pandas()
    treatment = pq.read_table(project_root / config["inputs"]["product_treatment"]["path"]).to_pandas()
    output, product_mismatches = merge_panels(trade, treatment, config)
    validation = validate(
        project_root, config, trade, treatment, output, product_mismatches
    )
    table = write_parquet(output, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "merge_version": config["version"],
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in table.schema
            ],
        }
    )
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    validation_json.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validation_md.write_text(markdown_report(validation), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "output_rows": validation["output_row_count"],
                "unmatched_trade_rows": validation["unmatched_trade_row_count"],
                "product_field_mismatches": validation["product_field_mismatch_counts"],
                "validation_json": str(validation_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
