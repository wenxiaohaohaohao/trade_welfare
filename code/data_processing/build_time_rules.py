from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


ALLOWED_OPERATORS = {
    "identity",
    "not_available",
    "sum_reported_monthly_flows",
    "sum_complete_nonconfidential_calendar_periods",
}


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def observed_years(path: Path) -> list[int]:
    parquet_file = pq.ParquetFile(path)
    year_index = parquet_file.schema_arrow.get_field_index("year")
    metadata_years: set[int] = set()
    metadata_complete = year_index >= 0
    for row_group_index in range(parquet_file.metadata.num_row_groups):
        statistics = parquet_file.metadata.row_group(row_group_index).column(year_index).statistics
        if not statistics or not statistics.has_min_max or statistics.min != statistics.max:
            metadata_complete = False
            break
        metadata_years.add(int(statistics.min))
    if metadata_complete and metadata_years:
        return sorted(metadata_years)
    table = pq.read_table(path, columns=["year"])
    return sorted({int(value) for value in table.column("year").to_pylist() if value is not None})


def build_rule_table(project_root: Path, config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    years_by_input: dict[str, list[int]] = {}
    for rule in config["rules"]:
        input_id = str(rule["input_id"])
        relative_path = Path(rule["input_path"])
        input_path = project_root / relative_path
        if input_id not in years_by_input:
            years_by_input[input_id] = observed_years(input_path)
        years = years_by_input[input_id]
        for metric in rule["metrics"]:
            rows.append(
                {
                    "input_id": input_id,
                    "input_path": relative_path.as_posix(),
                    "metric_name": str(metric),
                    "input_frequency": str(rule["input_frequency"]),
                    "temporal_semantics": str(rule["temporal_semantics"]),
                    "annual_operator": str(rule["annual_operator"]),
                    "expected_periods_per_year": rule.get("expected_periods_per_year"),
                    "retain_native_frequency": bool(rule.get("retain_native_frequency", False)),
                    "missing_rule": str(rule["missing_rule"]),
                    "prohibited_operation": str(rule["prohibited_operation"]),
                    "allowed_years": stringify(rule.get("allowed_years")),
                    "complete_calendar_years": stringify(rule.get("complete_calendar_years")),
                    "partial_calendar_years": stringify(rule.get("partial_calendar_years")),
                    "observed_start_year": min(years),
                    "observed_end_year": max(years),
                    "observed_year_count": len(years),
                    "observed_years": ";".join(map(str, years)),
                    "rule_version": str(config["version"]),
                }
            )
    frame = pd.DataFrame(rows).sort_values(["input_id", "metric_name"], kind="stable")
    string_columns = [column for column in frame if frame[column].dtype == "object"]
    for column in string_columns:
        frame[column] = frame[column].astype("string")
    frame["expected_periods_per_year"] = frame["expected_periods_per_year"].astype("Int16")
    frame["observed_start_year"] = frame["observed_start_year"].astype("int16")
    frame["observed_end_year"] = frame["observed_end_year"].astype("int16")
    frame["observed_year_count"] = frame["observed_year_count"].astype("int16")
    return frame.reset_index(drop=True)


def validate_rules(project_root: Path, config: dict[str, Any], frame: pd.DataFrame) -> dict[str, Any]:
    failures: list[str] = []
    duplicate_keys = int(frame.duplicated(["input_id", "metric_name"]).sum())
    if duplicate_keys:
        failures.append(f"time rules contain {duplicate_keys} duplicate input-metric keys")

    invalid_operators = sorted(set(frame["annual_operator"]) - ALLOWED_OPERATORS)
    if invalid_operators:
        failures.append(f"unrecognized annual operators: {invalid_operators}")

    missing_inputs: list[str] = []
    missing_metrics: list[dict[str, str]] = []
    for input_id, group in frame.groupby("input_id", sort=True):
        path = project_root / Path(group.iloc[0]["input_path"])
        if not path.exists():
            missing_inputs.append(str(path.relative_to(project_root)))
            continue
        schema_names = set(pq.read_schema(path).names)
        for metric in group["metric_name"]:
            if metric not in schema_names:
                missing_metrics.append({"input_id": input_id, "metric_name": metric})
    if missing_inputs:
        failures.append(f"missing input paths: {missing_inputs}")
    if missing_metrics:
        failures.append(f"configured metrics absent from inputs: {missing_metrics}")

    census_path = project_root / "data/interim/trade/us_imports_hs6_monthly.parquet"
    census = pq.read_table(census_path, columns=["year", "month", "quantity", "quantity_unit"]).to_pandas()
    census_periods = {
        int(year): sorted({int(value) for value in group["month"]})
        for year, group in census.groupby("year", sort=True)
    }
    census_full_years = all(months == list(range(1, 13)) for months in census_periods.values())
    census_quantity_unavailable = bool(
        (census["quantity"] == 0).all() and set(census["quantity_unit"].astype(str)) == {"-"}
    )
    if not census_full_years:
        failures.append("Census source does not contain all 12 requested months in every observed year")
    if not census_quantity_unavailable:
        failures.append("Census quantity no longer matches the configured unavailable-measure rule")

    census_flow_rules = frame[
        (frame["input_id"] == "us_census_hs6_monthly") & (frame["metric_name"] != "quantity")
    ]
    if not bool((census_flow_rules["annual_operator"] == "sum_reported_monthly_flows").all()):
        failures.append("one or more Census flow metrics lack the required monthly-sum operator")

    mexico_rule = next(
        rule for rule in config["rules"] if rule["input_id"] == "mexico_fdi_country_sector_quarterly"
    )
    mexico_path = project_root / mexico_rule["input_path"]
    mexico = pq.read_table(
        mexico_path,
        columns=["year", "quarter", "parent_country_name", "sector_level", "sector_code", "confidential_flag"],
    ).to_pandas()
    mexico_periods = {
        int(year): sorted({int(value) for value in group["quarter"]})
        for year, group in mexico.groupby("year", sort=True)
    }
    mexico_complete_years = [year for year, quarters in mexico_periods.items() if quarters == [1, 2, 3, 4]]
    mexico_partial_years = {
        year: quarters for year, quarters in mexico_periods.items() if quarters != [1, 2, 3, 4]
    }
    expected_complete = mexico_rule["complete_calendar_years"]
    expected_partial = {
        int(year): details["observed_quarters"]
        for year, details in mexico_rule["partial_calendar_years"].items()
    }
    mexico_calendar_rule_ok = (
        min(mexico_complete_years) == int(expected_complete["start"])
        and max(mexico_complete_years) == int(expected_complete["end"])
        and mexico_partial_years == expected_partial
    )
    if not mexico_calendar_rule_ok:
        failures.append(
            f"Mexico calendar coverage differs from config: complete={mexico_complete_years}, partial={mexico_partial_years}"
        )
    mexico_group_keys = ["year", "parent_country_name", "sector_level", "sector_code"]
    mexico_group = mexico.groupby(mexico_group_keys, dropna=False).agg(
        quarter_count=("quarter", "nunique"),
        any_confidential=("confidential_flag", "any"),
    )
    mexico_incomplete_groups = int((mexico_group["quarter_count"] != 4).sum())
    mexico_confidential_groups = int(mexico_group["any_confidential"].sum())

    position = frame[
        (frame["input_id"] == "bea_direct_investment_country_industry")
        & (frame["metric_name"] == "position")
    ]
    bea_position_rule_ok = bool(
        len(position) == 1
        and position.iloc[0]["temporal_semantics"] == "end_period_stock"
        and "never_sum" in position.iloc[0]["prohibited_operation"]
    )
    if not bea_position_rule_ok:
        failures.append("BEA position is not protected as a non-additive stock")

    icio = frame[frame["input_id"] == "oecd_icio_output_va_fd"]
    icio_year_rule_ok = set(icio["observed_years"]) == {"2017;2018;2022"} and set(
        icio["allowed_years"]
    ) == {"[2017, 2018, 2022]"}
    if not icio_year_rule_ok:
        failures.append("ICIO observed and configured benchmark years do not match")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "row_count": len(frame),
        "input_count": int(frame["input_id"].nunique()),
        "duplicate_input_metric_keys": duplicate_keys,
        "missing_input_count": len(missing_inputs),
        "missing_metric_count": len(missing_metrics),
        "invalid_operators": invalid_operators,
        "census_observed_years": sorted(census_periods),
        "census_all_years_have_12_source_months": census_full_years,
        "census_quantity_unavailable_rule_ok": census_quantity_unavailable,
        "mexico_complete_calendar_years": mexico_complete_years,
        "mexico_partial_calendar_years": mexico_partial_years,
        "mexico_incomplete_country_sector_year_groups": mexico_incomplete_groups,
        "mexico_groups_with_any_confidential_quarter": mexico_confidential_groups,
        "mexico_calendar_rule_ok": mexico_calendar_rule_ok,
        "bea_position_stock_rule_ok": bea_position_rule_ok,
        "icio_benchmark_year_rule_ok": icio_year_rule_ok,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Time Aggregation Rules Validation",
            "",
            f"- Generated at UTC: `{validation['generated_at_utc']}`",
            f"- Output: `{validation['output_path']}`",
            f"- SHA256: `{validation['output_sha256']}`",
            f"- Rule rows: `{validation['row_count']}`",
            f"- Inputs: `{validation['input_count']}`",
            f"- Duplicate input-metric keys: `{validation['duplicate_input_metric_keys']}`",
            f"- Validation status: **{validation['validation_status']}**",
            "",
            "## Required temporal checks",
            "",
            f"- Census source contains all 12 requested months in each 2014-2024 year: `{'yes' if validation['census_all_years_have_12_source_months'] else 'no'}`",
            f"- Census quantity remains structurally unavailable: `{'yes' if validation['census_quantity_unavailable_rule_ok'] else 'no'}`",
            f"- Mexico complete calendar years: `{validation['mexico_complete_calendar_years'][0]}-{validation['mexico_complete_calendar_years'][-1]}`",
            f"- Mexico partial calendar years: `{json.dumps(validation['mexico_partial_calendar_years'], sort_keys=True)}`",
            f"- Mexico country-sector-year groups with incomplete quarters: `{validation['mexico_incomplete_country_sector_year_groups']}`",
            f"- Mexico country-sector-year groups with at least one confidential quarter: `{validation['mexico_groups_with_any_confidential_quarter']}`",
            f"- BEA position protected as a stock: `{'yes' if validation['bea_position_stock_rule_ok'] else 'no'}`",
            f"- ICIO restricted to observed 2017/2018/2022 benchmarks: `{'yes' if validation['icio_benchmark_year_rule_ok'] else 'no'}`",
            "",
            "## Interpretation",
            "",
            "Census additive values may be summed over reported monthly rows while retaining the monthly interface and a months-with-records diagnostic. Mexico FDI may be summed to a calendar-year value only when all four quarters are present and none is confidential; 2024 contains Q1-Q2 only and is not a full-year observation. BEA direct-investment position remains a stock and is never summed across time. ICIO missing years are not imputed.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and validate metric-level time rules.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("data/processed/concordances/time_aggregation_rules.parquet"))
    parser.add_argument("--validation-json", type=Path, default=Path("data/validation/time_aggregation_rules_validation.json"))
    parser.add_argument("--validation-md", type=Path, default=Path("data/validation/time_aggregation_rules_validation.md"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else project_root / args.output
    validation_json = args.validation_json if args.validation_json.is_absolute() else project_root / args.validation_json
    validation_md = args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    for path in (output, validation_json, validation_md):
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/time_aggregation_rules.yaml")
    frame = build_rule_table(project_root, config)
    validation = validate_rules(project_root, config, frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, output, compression="zstd")
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output),
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in table.schema
            ],
        }
    )
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
                "row_count": validation["row_count"],
                "output": str(output),
                "validation_json": str(validation_json),
                "validation_md": str(validation_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
