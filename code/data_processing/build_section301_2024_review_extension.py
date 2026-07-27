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


def build_output(project_root: Path, config: dict[str, Any]) -> pd.DataFrame:
    frame = pq.read_table(project_root / config["input"]["path"]).to_pandas()
    frame["integration_status"] = config["output"]["integration_status"]
    frame["historical_hs6_panel_merged"] = bool(config["output"]["historical_hs6_panel_merged"])
    frame["requires_modern_hts_concordance"] = bool(
        config["output"]["requires_modern_hts_concordance"]
    )
    frame["extension_version"] = config["version"]
    for column in [
        "hts_code",
        "scope_note",
        "product_description",
        "source_notice",
        "source_url",
        "integration_status",
        "extension_version",
    ]:
        frame[column] = frame[column].astype("string")
    frame["hts_code_level"] = frame["hts_code_level"].astype("int8")
    frame["timing_year"] = frame["timing_year"].astype("int16")
    frame["source_page"] = frame["source_page"].astype("int16")
    frame["whole_code_applicable"] = frame["whole_code_applicable"].astype("bool")
    frame["historical_hs6_panel_merged"] = frame["historical_hs6_panel_merged"].astype("bool")
    frame["requires_modern_hts_concordance"] = frame["requires_modern_hts_concordance"].astype("bool")
    return frame.sort_values("hts_code").reset_index(drop=True)


def validate(project_root: Path, config: dict[str, Any], output: pd.DataFrame) -> dict[str, Any]:
    failures: list[str] = []
    input_hash_ok = sha256(project_root / config["input"]["path"]) == config["input"]["sha256"]
    if not input_hash_ok:
        failures.append("2024 review exact-HTS input hash does not match")
    duplicate_keys = int(output.duplicated(config["output"]["natural_key"]).sum())
    if duplicate_keys:
        failures.append("2024 review exact-HTS key is duplicated")
    rules = config["validation"]
    row_count_ok = len(output) == int(rules["expected_rows"])
    whole_count = int(output["whole_code_applicable"].sum())
    scoped_count = int((~output["whole_code_applicable"]).sum())
    scope_counts_ok = (
        whole_count == int(rules["expected_whole_code_rows"])
        and scoped_count == int(rules["expected_description_scoped_rows"])
    )
    if not row_count_ok or not scope_counts_ok:
        failures.append("2024 review row or scope counts differ from the validated source summary")
    hts_lengths_ok = bool(
        (
            output["hts_code"].str.len().astype(int)
            == output["hts_code_level"].astype(int)
        ).all()
        and output["hts_code"].str.fullmatch(r"\d{8}|\d{10}").all()
    )
    if not hts_lengths_ok:
        failures.append("HTS code length disagrees with HTS level")
    expected_rates = {float(rate): int(count) for rate, count in rules["expected_rate_counts"].items()}
    actual_rates = {
        float(rate): int(count)
        for rate, count in output["section301_rate"].value_counts().sort_index().items()
    }
    rate_counts_ok = actual_rates == expected_rates
    if not rate_counts_ok:
        failures.append("2024 review rate counts differ from expected validated counts")
    effective_date_ok = bool(
        (pd.to_datetime(output["effective_date"]).dt.strftime("%Y-%m-%d") == rules["expected_effective_date"]).all()
    )
    if not effective_date_ok:
        failures.append("2024 review effective date differs from the configured notice date")
    separation_flags_ok = bool(
        (~output["historical_hs6_panel_merged"]).all()
        and output["requires_modern_hts_concordance"].all()
        and (output["integration_status"] == "separate_exact_hts_extension").all()
        and "analysis_hs6" not in output.columns
    )
    if not separation_flags_ok:
        failures.append("2024 review extension was incorrectly merged or assigned an analysis HS6")
    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_check_pass": input_hash_ok,
        "output_row_count": len(output),
        "duplicate_hts_code_count": duplicate_keys,
        "row_count_check_pass": row_count_ok,
        "whole_code_row_count": whole_count,
        "description_scoped_row_count": scoped_count,
        "scope_count_check_pass": scope_counts_ok,
        "hts_code_length_check_pass": hts_lengths_ok,
        "rate_counts": {str(rate): count for rate, count in actual_rates.items()},
        "rate_count_check_pass": rate_counts_ok,
        "effective_date_check_pass": effective_date_ok,
        "separate_extension_flags_check_pass": separation_flags_ok,
        "analysis_hs6_column_present": "analysis_hs6" in output.columns,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Section 301 2024 Review Exact-HTS Extension Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Exact HTS rows: `{validation['output_row_count']}`",
        "",
        "## Required checks",
        "",
        f"- Input SHA256 matches: `{'yes' if validation['input_hash_check_pass'] else 'no'}`",
        f"- Unique exact HTS code: `{'yes' if validation['duplicate_hts_code_count'] == 0 else 'no'}`",
        f"- HTS8/HTS10 lengths preserved: `{'yes' if validation['hts_code_length_check_pass'] else 'no'}`",
        f"- Whole-code rows: `{validation['whole_code_row_count']}`; description-scoped rows: `{validation['description_scoped_row_count']}`.",
        f"- Rate counts match the official-notice extraction: `{'yes' if validation['rate_count_check_pass'] else 'no'}`",
        f"- Historical HS6 merge prohibited and no `analysis_hs6` assigned: `{'yes' if validation['separate_extension_flags_check_pass'] else 'no'}`",
        "",
        "## Interpretation",
        "",
        "This is a separate 2024 exact-HTS extension. It is not part of the historical HS2017/HS2012 product-treatment panel. Two records are description-scoped and cannot be treated as whole-code coverage. No first-six-digit truncation or forced HS6 assignment is performed; integration requires a separately validated modern HTS concordance and scope rule.",
        "",
    ]
    if validation["failures"]:
        lines.extend(["## Failures", ""] + [f"- {item}" for item in validation["failures"]] + [""])
    return "\n".join(lines)


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Preserve the Section 301 2024 review as an exact-HTS extension.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/policy/section301_2024_review_exact_hts.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/section301_2024_review_extension_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/section301_2024_review_extension_validation.md"),
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
    config = load_yaml(project_root / "configs/section301_2024_review_rules.yaml")
    output = build_output(project_root, config)
    validation = validate(project_root, config, output)
    table = write_parquet(output, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "extension_version": config["version"],
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
                "description_scoped_rows": validation["description_scoped_row_count"],
                "analysis_hs6_present": validation["analysis_hs6_column_present"],
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
