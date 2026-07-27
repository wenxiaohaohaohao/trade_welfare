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


def load_and_bridge(
    project_root: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    census = pq.read_table(project_root / config["inputs"]["census_monthly"]["path"]).to_pandas()
    bridge = pq.read_table(project_root / config["inputs"]["census_year_hs_bridge"]["path"]).to_pandas()
    product = pq.read_table(project_root / config["inputs"]["product_crosswalk"]["path"]).to_pandas()
    census["source_hs6"] = census["hs6"].astype("string").str.zfill(6)
    bridge_columns = [
        "year",
        "source_hs6",
        "source_revision",
        "target_hs6",
        "analysis_hs6",
        "mapping_method",
        "analysis_mapping_method",
        "mapping_status",
        "is_analysis_eligible",
        "bridge_version",
    ]
    bridged = census.merge(
        bridge[bridge_columns],
        on=["year", "source_hs6"],
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    return bridged, bridge, product


def build_monthly(
    bridged: pd.DataFrame, product: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    eligible = bridged[bridged["is_analysis_eligible"].fillna(False)].copy()
    keys = ["origin_iso3", "analysis_hs6", "year", "month"]
    aggregations: dict[str, tuple[str, Any]] = {
        field: (field, "sum") for field in config["flow_fields"]
    }
    aggregations.update(
        {
            "source_row_count": ("source_hs6", "size"),
            "source_hs6_count": ("source_hs6", "nunique"),
            "source_hs6_first": ("source_hs6", "first"),
            "source_revision_count": ("source_revision", "nunique"),
            "source_revision_first": ("source_revision", "first"),
            "mapping_status_count": ("mapping_status", "nunique"),
            "mapping_status_first": ("mapping_status", "first"),
            "mapping_method_count": ("mapping_method", "nunique"),
            "mapping_method_first": ("mapping_method", "first"),
            "source_file_count": ("source_file", "nunique"),
        }
    )
    monthly = eligible.groupby(keys, as_index=False, observed=True).agg(**aggregations)
    monthly["source_hs6_summary"] = monthly["source_hs6_first"]
    monthly.loc[monthly["source_hs6_count"] > 1, "source_hs6_summary"] = "<MULTIPLE>"
    monthly["source_revision_summary"] = monthly["source_revision_first"]
    monthly.loc[monthly["source_revision_count"] > 1, "source_revision_summary"] = "<MULTIPLE>"
    monthly["mapping_status_summary"] = monthly["mapping_status_first"]
    monthly.loc[monthly["mapping_status_count"] > 1, "mapping_status_summary"] = "<MULTIPLE>"
    monthly["mapping_method_summary"] = monthly["mapping_method_first"]
    monthly.loc[monthly["mapping_method_count"] > 1, "mapping_method_summary"] = "<MULTIPLE>"
    monthly = monthly.drop(
        columns=[
            "source_hs6_first",
            "source_revision_first",
            "mapping_status_first",
            "mapping_method_first",
        ]
    )
    product_fields = [
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "is_analysis_sector_eligible",
        "mapping_version",
    ]
    monthly = monthly.merge(
        product[product_fields].rename(columns={"mapping_version": "product_mapping_version"}),
        on="analysis_hs6",
        how="left",
        validate="many_to_one",
    )
    monthly["quantity_usable"] = False
    monthly["quantity_status"] = "structurally_unavailable_source_zero_placeholder"
    monthly["census_origin_scope"] = "configured_15_origins"
    monthly["is_all_origin_denominator"] = False
    monthly["monthly_event_study_interface"] = True
    monthly["census_panel_version"] = config["version"]
    string_columns = [
        "origin_iso3",
        "analysis_hs6",
        "source_hs6_summary",
        "source_revision_summary",
        "mapping_status_summary",
        "mapping_method_summary",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "product_mapping_version",
        "quantity_status",
        "census_origin_scope",
        "census_panel_version",
    ]
    for column in string_columns:
        monthly[column] = monthly[column].astype("string")
    monthly["year"] = monthly["year"].astype("int16")
    monthly["month"] = monthly["month"].astype("int8")
    for column in [
        "source_row_count",
        "source_hs6_count",
        "source_revision_count",
        "mapping_status_count",
        "mapping_method_count",
        "source_file_count",
    ]:
        monthly[column] = monthly[column].astype("int16")
    for column in [
        "is_analysis_sector_eligible",
        "quantity_usable",
        "is_all_origin_denominator",
        "monthly_event_study_interface",
    ]:
        monthly[column] = monthly[column].astype("bool")
    return monthly.sort_values(keys).reset_index(drop=True)


def build_annual(
    monthly: pd.DataFrame,
    product: pd.DataFrame,
    sample: dict[str, Any],
    config: dict[str, Any],
) -> pd.DataFrame:
    keys = ["origin_iso3", "analysis_hs6", "year"]
    annual_aggregations: dict[str, tuple[str, Any]] = {
        field: (field, "sum") for field in config["flow_fields"]
    }
    annual_aggregations.update(
        {
            "observed_month_count": ("month", "nunique"),
            "source_row_count": ("source_row_count", "sum"),
            "source_file_count": ("source_file_count", "sum"),
        }
    )
    annual_sparse = monthly.groupby(keys, as_index=False, observed=True).agg(**annual_aggregations)
    origins = list(sample["countries"]["census_validation_origins"])
    years = list(
        range(
            int(sample["time"]["annual_trade_panel"]["start"]),
            int(sample["time"]["annual_trade_panel"]["end"]) + 1,
        )
    )
    product_fields = [
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "is_analysis_sector_eligible",
        "mapping_version",
    ]
    grid = (
        pd.DataFrame({"origin_iso3": origins})
        .assign(_join_key=1)
        .merge(pd.DataFrame({"year": years, "_join_key": 1}), on="_join_key")
        .merge(
            product[product_fields]
            .rename(columns={"mapping_version": "product_mapping_version"})
            .assign(_join_key=1),
            on="_join_key",
        )
        .drop(columns="_join_key")
    )
    annual = grid.merge(annual_sparse, on=keys, how="left", validate="one_to_one")
    for field in [*config["flow_fields"], "observed_month_count", "source_row_count", "source_file_count"]:
        annual[field] = annual[field].fillna(0)
    annual["calendar_source_months_complete"] = True
    annual["sparse_row_absence_treated_as_zero_import"] = True
    annual["quantity_usable"] = False
    annual["quantity_status"] = "structurally_unavailable_source_zero_placeholder"
    annual["census_origin_scope"] = "configured_15_origins"
    annual["is_all_origin_denominator"] = False
    annual["census_panel_version"] = config["version"]
    string_columns = [
        "origin_iso3",
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "product_mapping_version",
        "quantity_status",
        "census_origin_scope",
        "census_panel_version",
    ]
    for column in string_columns:
        annual[column] = annual[column].astype("string")
    annual["year"] = annual["year"].astype("int16")
    for column in ["observed_month_count", "source_row_count", "source_file_count"]:
        annual[column] = annual[column].astype("int32")
    for column in [
        "is_analysis_sector_eligible",
        "calendar_source_months_complete",
        "sparse_row_absence_treated_as_zero_import",
        "quantity_usable",
        "is_all_origin_denominator",
    ]:
        annual[column] = annual[column].astype("bool")
    return annual.sort_values(keys).reset_index(drop=True)


def validate(
    project_root: Path,
    config: dict[str, Any],
    sample: dict[str, Any],
    bridged: pd.DataFrame,
    bridge: pd.DataFrame,
    product: pd.DataFrame,
    monthly: pd.DataFrame,
    annual: pd.DataFrame,
) -> dict[str, Any]:
    failures: list[str] = []
    hash_checks = {
        name: sha256(project_root / details["path"]) == details["sha256"]
        for name, details in config["inputs"].items()
    }
    if not all(hash_checks.values()):
        failures.append("one or more configured M2.4 input hashes do not match")
    input_keys = config["inputs"]["census_monthly"]["natural_key"]
    input_duplicates = int(bridged.duplicated(input_keys).sum())
    bridge_duplicates = int(bridge.duplicated(config["inputs"]["census_year_hs_bridge"]["natural_key"]).sum())
    monthly_duplicates = int(monthly.duplicated(config["monthly_output"]["natural_key"]).sum())
    annual_duplicates = int(annual.duplicated(config["annual_output"]["natural_key"]).sum())
    if input_duplicates or bridge_duplicates or monthly_duplicates or annual_duplicates:
        failures.append("input, bridge, monthly, or annual natural key is duplicated")
    unmatched_bridge_rows = int((bridged["_merge"] != "both").sum())
    if unmatched_bridge_rows:
        failures.append(f"{unmatched_bridge_rows} Census rows lack a year-HS bridge status")

    status_summary = (
        bridged.groupby("mapping_status", dropna=False)
        .agg(row_count=("source_hs6", "size"), import_value_usd=("import_value_usd", "sum"))
        .reset_index()
    )
    status_records = status_summary.to_dict(orient="records")
    eligible_mask = bridged["is_analysis_eligible"].fillna(False)
    excluded_mask = bridged["mapping_status"] == "excluded_national_special_code"
    unresolved_mask = bridged["mapping_status"] == "unresolved_nonstandard_code"
    total_import_value = float(bridged["import_value_usd"].sum())
    eligible_import_value = float(bridged.loc[eligible_mask, "import_value_usd"].sum())
    excluded_import_value = float(bridged.loc[excluded_mask, "import_value_usd"].sum())
    unresolved_import_value = float(bridged.loc[unresolved_mask, "import_value_usd"].sum())
    eligible_denominator = total_import_value - excluded_import_value
    gross_value_coverage = eligible_import_value / total_import_value
    eligible_value_coverage = eligible_import_value / eligible_denominator
    if eligible_value_coverage < float(config["validation"]["minimum_eligible_value_coverage"]):
        failures.append("Census eligible product-value coverage is below 95 percent")

    reconciliation: dict[str, dict[str, float]] = {}
    tolerance = float(config["validation"]["tolerance_usd"])
    for field in config["flow_fields"]:
        eligible_input = float(bridged.loc[eligible_mask, field].sum())
        monthly_total = float(monthly[field].sum())
        annual_total = float(annual[field].sum())
        monthly_gap = monthly_total - eligible_input
        annual_gap = annual_total - monthly_total
        reconciliation[field] = {
            "eligible_input_total": eligible_input,
            "monthly_output_total": monthly_total,
            "annual_output_total": annual_total,
            "monthly_minus_input_gap": monthly_gap,
            "annual_minus_monthly_gap": annual_gap,
        }
        if abs(monthly_gap) > tolerance or abs(annual_gap) > tolerance:
            failures.append(f"{field} fails Census monthly/annual reconciliation")

    origins = set(sample["countries"]["census_validation_origins"])
    years = set(
        range(
            int(sample["time"]["annual_trade_panel"]["start"]),
            int(sample["time"]["annual_trade_panel"]["end"]) + 1,
        )
    )
    expected_annual_rows = len(origins) * len(product) * len(years)
    annual_grid_ok = bool(
        len(annual) == expected_annual_rows
        and set(annual["origin_iso3"]) == origins
        and set(annual["analysis_hs6"]) == set(product["analysis_hs6"])
        and set(annual["year"]) == years
    )
    if not annual_grid_ok:
        failures.append("Census annual output is not the complete configured-origin product-year grid")
    calendar_counts = bridged.groupby(["origin_iso3", "year"])["month"].nunique()
    calendar_complete = bool((calendar_counts == 12).all() and len(calendar_counts) == len(origins) * len(years))
    if not calendar_complete:
        failures.append("Census source does not contain all 12 months for every configured origin-year")
    quantity_raw_zero = bool((bridged["quantity"] == 0).all())
    quantity_unit_dash = bool((bridged["quantity_unit"] == "-").all())
    hts10_all_missing = bool(bridged["hts10"].isna().all())
    if not (quantity_raw_zero and quantity_unit_dash):
        failures.append("Census quantity no longer matches the documented unavailable placeholder pattern")
    product_provenance_missing = int(monthly["product_mapping_version"].isna().sum())
    if product_provenance_missing:
        failures.append("monthly Census output lacks product mapping provenance")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": hash_checks,
        "input_row_count": len(bridged),
        "input_duplicate_key_count": input_duplicates,
        "bridge_duplicate_key_count": bridge_duplicates,
        "unmatched_bridge_row_count": unmatched_bridge_rows,
        "mapping_status_summary": status_records,
        "total_import_value_usd": total_import_value,
        "eligible_import_value_usd": eligible_import_value,
        "excluded_national_special_import_value_usd": excluded_import_value,
        "unresolved_nonstandard_import_value_usd": unresolved_import_value,
        "gross_value_coverage_rate": gross_value_coverage,
        "eligible_value_coverage_rate": eligible_value_coverage,
        "monthly_output_row_count": len(monthly),
        "monthly_duplicate_key_count": monthly_duplicates,
        "annual_output_row_count": len(annual),
        "expected_annual_output_row_count": expected_annual_rows,
        "annual_duplicate_key_count": annual_duplicates,
        "annual_full_grid_check_pass": annual_grid_ok,
        "flow_reconciliation": reconciliation,
        "origin_count": len(origins),
        "origin_scope_matches_config": set(bridged["origin_iso3"]) == origins,
        "calendar_12_month_check_pass": calendar_complete,
        "source_file_count": int(bridged["source_file"].nunique()),
        "quantity_raw_all_zero": quantity_raw_zero,
        "quantity_unit_all_dash": quantity_unit_dash,
        "quantity_marked_unusable": bool((~monthly["quantity_usable"]).all() and (~annual["quantity_usable"]).all()),
        "hts10_all_missing_in_hs6_batch": hts10_all_missing,
        "product_mapping_provenance_missing_count": product_provenance_missing,
        "all_origin_denominator_prohibited": True,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Census Harmonized Monthly and Annual Panel Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Monthly output: `{validation['monthly_output_path']}`",
        f"- Annual output: `{validation['annual_output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        "",
        "## Required checks",
        "",
        f"- Configured input SHA256 checks: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- All source rows receive an explicit bridge status: `{'yes' if validation['unmatched_bridge_row_count'] == 0 else 'no'}`",
        f"- Unique monthly analysis key: `{'yes' if validation['monthly_duplicate_key_count'] == 0 else 'no'}`",
        f"- Complete annual configured-origin grid: `{'yes' if validation['annual_full_grid_check_pass'] else 'no'}`",
        f"- Every configured origin-year has 12 source months: `{'yes' if validation['calendar_12_month_check_pass'] else 'no'}`",
        f"- Quantity placeholder identified and disabled: `{'yes' if validation['quantity_raw_all_zero'] and validation['quantity_unit_all_dash'] and validation['quantity_marked_unusable'] else 'no'}`",
        "",
        "## Mapping and value coverage",
        "",
        f"- Gross mapped import-value coverage: `{validation['gross_value_coverage_rate']:.6%}`.",
        f"- Eligible import-value coverage after excluding national chapters 98/99: `{validation['eligible_value_coverage_rate']:.6%}`.",
        f"- Excluded national-special import value: `${validation['excluded_national_special_import_value_usd']:.2f}`.",
        f"- Unresolved nonstandard-code import value: `${validation['unresolved_nonstandard_import_value_usd']:.2f}`.",
        "",
        "## Flow reconciliation",
        "",
        "| Field | Eligible input | Monthly output | Annual output | Monthly gap | Annual gap |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for field, record in validation["flow_reconciliation"].items():
        lines.append(
            f"| `{field}` | {record['eligible_input_total']:.2f} | {record['monthly_output_total']:.2f} | {record['annual_output_total']:.2f} | {record['monthly_minus_input_gap']:.6f} | {record['annual_minus_monthly_gap']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The monthly table is the sparse event-study interface after year-specific HS harmonization. The annual table completes the 15 configured origins, 5,202 analysis products, and 2014-2024 years; missing sparse product rows are recorded as zero reported imports only because the source origin-month files are complete. This batch is not an all-origin U.S. import denominator. National chapters 98/99 and unresolved nonstandard HS6 codes remain outside the internationally comparable output and are reported in coverage diagnostics. Quantity is structurally unavailable: raw zeros with unit `-` are placeholders, not economic zero quantities.",
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
    parser = argparse.ArgumentParser(description="Build M2.4-M2.5 harmonized Census monthly and annual panels.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--monthly-output",
        type=Path,
        default=Path("data/processed/harmonized/census_imports_hs6_monthly_harmonized.parquet"),
    )
    parser.add_argument(
        "--annual-output",
        type=Path,
        default=Path("data/processed/harmonized/census_imports_hs6_annual.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/census_harmonized_panels_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/census_harmonized_panels_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    paths = [
        path if path.is_absolute() else project_root / path
        for path in [args.monthly_output, args.annual_output, args.validation_json, args.validation_md]
    ]
    monthly_output, annual_output, validation_json, validation_md = paths
    for path in paths:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/census_harmonization_rules.yaml")
    sample = load_yaml(project_root / config["analysis_sample_config"])
    bridged, bridge, product = load_and_bridge(project_root, config)
    monthly = build_monthly(bridged, product, config)
    annual = build_annual(monthly, product, sample, config)
    validation = validate(
        project_root, config, sample, bridged, bridge, product, monthly, annual
    )
    monthly_table = write_parquet(monthly, monthly_output)
    annual_table = write_parquet(annual, annual_output)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "monthly_output_path": monthly_output.relative_to(project_root).as_posix(),
            "monthly_output_sha256": sha256(monthly_output),
            "annual_output_path": annual_output.relative_to(project_root).as_posix(),
            "annual_output_sha256": sha256(annual_output),
            "census_panel_version": config["version"],
            "monthly_schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in monthly_table.schema
            ],
            "annual_schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in annual_table.schema
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
                "monthly_rows": validation["monthly_output_row_count"],
                "annual_rows": validation["annual_output_row_count"],
                "eligible_value_coverage": validation["eligible_value_coverage_rate"],
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
