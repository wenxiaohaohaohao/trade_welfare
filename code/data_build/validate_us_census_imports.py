from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml

from download_us_census_imports import (
    API_FIELDS,
    OUTPUT_COLUMNS,
    api_key_from_env,
    census_get,
    configured_origins,
    configured_years,
    load_yaml,
    months_for_years,
    raw_file_for,
)


MONEY_FIELDS = {
    "GEN_VAL_MO": "import_value_usd",
    "CON_VAL_MO": "customs_value",
    "CAL_DUT_MO": "duties",
    "DUT_VAL_MO": "dutiable_value_usd",
}
QUANTITY_FIELDS = {"GEN_QY1_MO": "quantity"}
SUM_FIELDS = {**MONEY_FIELDS, **QUANTITY_FIELDS}


def level_dir_key(level: str) -> str:
    return "hs10" if level == "HS10" else "hs6"


def as_source(path: Path) -> str:
    return path.resolve().as_posix()


def numeric_or_zero(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    return float(value)


def first_index(header: list[str], field: str) -> int:
    try:
        return header.index(field)
    except ValueError as exc:
        raise ValueError(f"Missing raw field {field}") from exc


def expected_context(project_root: Path) -> dict[str, Any]:
    config_dir = project_root / "configs"
    data_versions = load_yaml(config_dir / "data_versions.yaml")
    country_groups = load_yaml(config_dir / "country_groups.yaml")
    time_windows = load_yaml(config_dir / "time_windows.yaml")
    country_codes = load_yaml(config_dir / "us_census_country_codes.yaml")["country_codes"]

    origins = configured_origins(country_groups)
    years = configured_years(time_windows, data_versions)
    months = months_for_years(years)
    countries = [
        {
            "origin_iso3": origin,
            "cty_code": str(country_codes[origin]["cty_code"]),
            "cty_name": str(country_codes[origin]["cty_name"]),
        }
        for origin in sorted(origins)
    ]

    raw_dir = (project_root / data_versions["us_census"]["raw_dir"]).resolve()
    output_dir = (project_root / data_versions["us_census"]["batch2_usage"]["output_dir"]).resolve()
    raw_dirs = {
        "hs10": raw_dir / "hs10_monthly_imports",
        "hs6": raw_dir / "hs6_monthly_imports",
        "metadata": raw_dir / "metadata",
    }
    output_paths = {
        "HS10": output_dir / "us_imports_hs10_monthly.parquet",
        "HS6": output_dir / "us_imports_hs6_monthly.parquet",
    }
    return {
        "data_versions": data_versions,
        "years": years,
        "months": months,
        "countries": countries,
        "raw_dirs": raw_dirs,
        "output_paths": output_paths,
        "output_dir": output_dir,
    }


def expected_files(raw_dirs: dict[str, Path], level: str, months: list[str], countries: list[dict[str, str]]) -> list[Path]:
    return [
        raw_file_for(raw_dirs, level, month, country["origin_iso3"], country["cty_code"])
        for month in months
        for country in countries
    ]


def init_sums() -> dict[str, float]:
    return {field: 0.0 for field in SUM_FIELDS.values()}


def scan_raw_level(
    raw_dirs: dict[str, Path],
    level: str,
    months: list[str],
    countries: list[dict[str, str]],
) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
    files = expected_files(raw_dirs, level, months, countries)
    expected_set = {path.resolve() for path in files}
    actual_set = {path.resolve() for path in raw_dirs[level_dir_key(level)].glob(f"us_census_imports_{level}_*.json")}

    summary: dict[str, Any] = {
        "expected_files": len(files),
        "actual_files": len(actual_set),
        "missing_files": sorted(str(path) for path in expected_set - actual_set),
        "extra_files": sorted(str(path) for path in actual_set - expected_set),
        "malformed_files": [],
        "rows": 0,
        "invalid_year_month_rows": 0,
        "invalid_country_rows": 0,
        "invalid_code_length_rows": 0,
        "nonnumeric_import_value_rows": 0,
        "duplicate_raw_header_files": 0,
        "empty_response_files": 0,
    }
    by_source: dict[str, dict[str, float]] = {}
    country_by_code = {country["cty_code"]: country for country in countries}

    for path in files:
        source = as_source(path)
        by_source[source] = {"rows": 0.0, **init_sums()}
        if not path.exists():
            continue
        try:
            rows = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], list):
                raise ValueError("Raw JSON is not a Census list-of-lists response.")
            header = [str(value) for value in rows[0]]
            missing = [field for field in API_FIELDS if field not in header]
            if missing:
                raise ValueError(f"Raw JSON header is missing fields: {missing}")
            if len(header) != len(set(header)):
                summary["duplicate_raw_header_files"] += 1
            indices = {field: first_index(header, field) for field in API_FIELDS}
            data_rows = rows[1:]
            if not data_rows:
                summary["empty_response_files"] += 1
            expected_month = int(path.name.split("_")[5])
            expected_year = int(path.name.split("_")[4])
            expected_code = path.stem.split("_")[-1]
            expected_country = country_by_code[expected_code]
            code_width = 10 if level == "HS10" else 6
            for row in data_rows:
                by_source[source]["rows"] += 1
                summary["rows"] += 1
                if int(row[indices["YEAR"]]) != expected_year or int(row[indices["MONTH"]]) != expected_month:
                    summary["invalid_year_month_rows"] += 1
                if str(row[indices["CTY_CODE"]]) != expected_code or str(row[indices["CTY_NAME"]]) != expected_country["cty_name"]:
                    summary["invalid_country_rows"] += 1
                commodity = str(row[indices["I_COMMODITY"]])
                if len(commodity.zfill(code_width)) != code_width:
                    summary["invalid_code_length_rows"] += 1
                try:
                    numeric_or_zero(row[indices["GEN_VAL_MO"]])
                except (TypeError, ValueError):
                    summary["nonnumeric_import_value_rows"] += 1
                for raw_field, output_field in SUM_FIELDS.items():
                    by_source[source][output_field] += numeric_or_zero(row[indices[raw_field]])
        except Exception as exc:  # noqa: BLE001 - report all malformed raw files.
            summary["malformed_files"].append({"path": str(path), "error": str(exc)})
    return summary, by_source


def parquet_level_name(path: Path) -> str:
    return "HS10" if "hs10" in path.name else "HS6"


def scan_parquet(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, float]]]:
    level = parquet_level_name(path)
    key_col = "hts10" if level == "HS10" else "hs6"
    pf = pq.ParquetFile(path)
    summary: dict[str, Any] = {
        "exists": path.exists(),
        "rows": pf.metadata.num_rows,
        "row_groups": pf.metadata.num_row_groups,
        "columns_ok": pf.schema_arrow.names == OUTPUT_COLUMNS,
        "schema": pf.schema_arrow.names,
        "year_min": None,
        "year_max": None,
        "months": [],
        "origins": [],
        "source_files": 0,
        "source_file_missing_on_disk": 0,
        "source_file_points_to_staging": 0,
        "row_groups_with_multiple_source_files": 0,
        "duplicate_key_rows_within_source_file": 0,
        "invalid_code_length_rows": 0,
        "negative_measure_rows": 0,
        "missing_required_rows": 0,
        "hs6_hts10_rule_fail_rows": 0,
    }
    by_source: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, **init_sums()})
    months: set[int] = set()
    origins: set[str] = set()
    year_min: int | None = None
    year_max: int | None = None
    source_files: set[str] = set()

    columns = [
        "year",
        "month",
        "origin_iso3",
        "origin_census_code",
        "origin_name",
        "hts10",
        "hs6",
        "import_value_usd",
        "quantity",
        "customs_value",
        "duties",
        "dutiable_value_usd",
        "source_file",
    ]
    required = ["year", "month", "origin_iso3", "origin_census_code", "origin_name", "hs6", "import_value_usd"]
    if level == "HS10":
        required.append("hts10")

    for row_group in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(row_group, columns=columns)
        if table.num_rows == 0:
            continue

        source_col = table["source_file"].combine_chunks()
        source_values = pc.unique(source_col).to_pylist()
        if len(source_values) != 1:
            summary["row_groups_with_multiple_source_files"] += 1
        source = str(source_values[0])
        source_files.add(source)
        if "_staging_us_census_full" in source:
            summary["source_file_points_to_staging"] += 1
        if not Path(source).exists():
            summary["source_file_missing_on_disk"] += 1

        by_source[source]["rows"] += float(table.num_rows)
        for field in SUM_FIELDS.values():
            value = pc.sum(table[field]).as_py()
            by_source[source][field] += 0.0 if value is None or (isinstance(value, float) and math.isnan(value)) else float(value)

        years = table["year"].to_pylist()
        year_min = min(years) if year_min is None else min(year_min, min(years))
        year_max = max(years) if year_max is None else max(year_max, max(years))
        months.update(int(value) for value in pc.unique(table["month"]).to_pylist())
        origins.update(str(value) for value in pc.unique(table["origin_iso3"]).to_pylist())

        key_values = table[key_col].to_pylist()
        summary["duplicate_key_rows_within_source_file"] += table.num_rows - len(set(key_values))

        hs6_lengths = pc.utf8_length(table["hs6"]).to_pylist()
        summary["invalid_code_length_rows"] += sum(1 for value in hs6_lengths if value != 6)
        if level == "HS10":
            hts10_lengths = pc.utf8_length(table["hts10"]).to_pylist()
            summary["invalid_code_length_rows"] += sum(1 for value in hts10_lengths if value != 10)
            hts10_prefix = [str(value)[:6] for value in table["hts10"].to_pylist()]
            hs6_values = [str(value) for value in table["hs6"].to_pylist()]
            summary["hs6_hts10_rule_fail_rows"] += sum(a != b for a, b in zip(hts10_prefix, hs6_values, strict=True))
        else:
            hts10_values = table["hts10"].to_pylist()
            summary["hs6_hts10_rule_fail_rows"] += sum(value is not None for value in hts10_values)

        for field in required:
            summary["missing_required_rows"] += pc.sum(pc.is_null(table[field])).as_py() or 0
        for field in SUM_FIELDS.values():
            values = table[field]
            summary["negative_measure_rows"] += pc.sum(pc.less(values, 0)).as_py() or 0

    summary["year_min"] = year_min
    summary["year_max"] = year_max
    summary["months"] = sorted(months)
    summary["origins"] = sorted(origins)
    summary["source_files"] = len(source_files)
    return summary, dict(by_source)


def compare_raw_parquet(
    raw_by_source: dict[str, dict[str, float]],
    parquet_by_source: dict[str, dict[str, float]],
) -> dict[str, Any]:
    compared = 0
    missing_in_parquet: list[str] = []
    row_mismatches: list[dict[str, Any]] = []
    sum_mismatches: list[dict[str, Any]] = []
    extra_in_parquet = sorted(set(parquet_by_source) - set(raw_by_source))

    for source, raw_stats in raw_by_source.items():
        parquet_stats = parquet_by_source.get(source)
        if parquet_stats is None:
            if raw_stats["rows"] != 0:
                missing_in_parquet.append(source)
            continue
        compared += 1
        if int(raw_stats["rows"]) != int(parquet_stats["rows"]):
            row_mismatches.append(
                {
                    "source_file": source,
                    "raw_rows": int(raw_stats["rows"]),
                    "parquet_rows": int(parquet_stats["rows"]),
                }
            )
        for field in SUM_FIELDS.values():
            diff = float(parquet_stats[field]) - float(raw_stats[field])
            tolerance = 1e-6 if field == "quantity" else 0.5
            if abs(diff) > tolerance:
                sum_mismatches.append(
                    {
                        "source_file": source,
                        "field": field,
                        "raw_sum": raw_stats[field],
                        "parquet_sum": parquet_stats[field],
                        "diff": diff,
                    }
                )

    return {
        "compared_source_files": compared,
        "missing_in_parquet_nonempty_raw_files": missing_in_parquet[:20],
        "missing_in_parquet_nonempty_raw_files_count": len(missing_in_parquet),
        "extra_in_parquet_source_files": extra_in_parquet[:20],
        "extra_in_parquet_source_files_count": len(extra_in_parquet),
        "row_mismatches": row_mismatches[:20],
        "row_mismatch_count": len(row_mismatches),
        "sum_mismatches": sum_mismatches[:20],
        "sum_mismatch_count": len(sum_mismatches),
    }


def aggregate_rows(rows: list[list[str]]) -> dict[str, float]:
    if not rows:
        return {"rows": 0.0, **init_sums()}
    header = [str(value) for value in rows[0]]
    indices = {field: first_index(header, field) for field in API_FIELDS}
    out = {"rows": float(max(len(rows) - 1, 0)), **init_sums()}
    for row in rows[1:]:
        for raw_field, output_field in SUM_FIELDS.items():
            out[output_field] += numeric_or_zero(row[indices[raw_field]])
    return out


def official_api_checks(
    data_versions: dict[str, Any],
    raw_dirs: dict[str, Path],
    parquet_by_level: dict[str, dict[str, dict[str, float]]],
    api_key: str | None,
) -> dict[str, Any]:
    samples = [
        ("HS10", "2014-01", "CAN", "1220"),
        ("HS10", "2018-07", "CHN", "5700"),
        ("HS10", "2019-06", "TWN", "5830"),
        ("HS10", "2020-04", "MEX", "2010"),
        ("HS10", "2024-12", "VNM", "5520"),
        ("HS6", "2014-01", "CAN", "1220"),
        ("HS6", "2018-07", "CHN", "5700"),
        ("HS6", "2019-06", "TWN", "5830"),
        ("HS6", "2020-04", "MEX", "2010"),
        ("HS6", "2024-10", "MEX", "2010"),
        ("HS6", "2024-12", "VNM", "5520"),
    ]
    if not api_key:
        return {"status": "skipped_missing_api_key", "samples": []}

    results = []
    for level, month, iso3, cty_code in samples:
        rows = census_get(
            {
                "get": ",".join(API_FIELDS),
                "time": month,
                "COMM_LVL": level,
                "CTY_CODE": cty_code,
            },
            api_key=api_key,
        )
        path = raw_file_for(raw_dirs, level, month, iso3, cty_code)
        raw_rows = json.loads(path.read_text(encoding="utf-8"))
        api_stats = aggregate_rows(rows)
        raw_stats = aggregate_rows(raw_rows)
        source = as_source(path)
        parquet_stats = parquet_by_level[level].get(source, {"rows": 0.0, **init_sums()})
        sum_diffs = {
            field: float(parquet_stats[field]) - float(api_stats[field])
            for field in SUM_FIELDS.values()
        }
        exact_raw_match = rows == raw_rows
        sorted_raw_match = sorted(rows[1:]) == sorted(raw_rows[1:]) and rows[0] == raw_rows[0]
        results.append(
            {
                "level": level,
                "month": month,
                "origin_iso3": iso3,
                "cty_code": cty_code,
                "api_rows": int(api_stats["rows"]),
                "raw_rows": int(raw_stats["rows"]),
                "parquet_rows": int(parquet_stats["rows"]),
                "api_equals_raw_exact": exact_raw_match,
                "api_equals_raw_sorted": sorted_raw_match,
                "parquet_minus_api_sums": sum_diffs,
            }
        )
    failed = [
        sample
        for sample in results
        if not sample["api_equals_raw_sorted"]
        or sample["api_rows"] != sample["parquet_rows"]
        or any(abs(value) > (1e-6 if field == "quantity" else 0.5) for field, value in sample["parquet_minus_api_sums"].items())
    ]
    return {"status": "completed", "samples": results, "failed_sample_count": len(failed), "failed_samples": failed}


def pass_fail(report: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for level in ["HS10", "HS6"]:
        raw = report["raw"][level]
        parquet = report["parquet"][level]
        compare = report["raw_parquet_compare"][level]
        checks[f"{level} raw file count"] = raw["expected_files"] == raw["actual_files"] and not raw["missing_files"] and not raw["extra_files"]
        checks[f"{level} raw JSON valid"] = not raw["malformed_files"] and raw["invalid_year_month_rows"] == 0 and raw["invalid_country_rows"] == 0 and raw["invalid_code_length_rows"] == 0 and raw["nonnumeric_import_value_rows"] == 0
        checks[f"{level} parquet schema"] = parquet["columns_ok"]
        checks[f"{level} parquet source_file valid"] = parquet["source_file_points_to_staging"] == 0 and parquet["source_file_missing_on_disk"] == 0
        checks[f"{level} parquet grain"] = parquet["duplicate_key_rows_within_source_file"] == 0
        checks[f"{level} parquet validity"] = parquet["invalid_code_length_rows"] == 0 and parquet["negative_measure_rows"] == 0 and parquet["missing_required_rows"] == 0 and parquet["hs6_hts10_rule_fail_rows"] == 0
        checks[f"{level} raw-parquet equality"] = (
            compare["missing_in_parquet_nonempty_raw_files_count"] == 0
            and compare["extra_in_parquet_source_files_count"] == 0
            and compare["row_mismatch_count"] == 0
            and compare["sum_mismatch_count"] == 0
        )
    api = report["official_api"]
    checks["official API sample equality"] = api["status"] == "completed" and api.get("failed_sample_count", 0) == 0
    return checks


def write_markdown(report: dict[str, Any], checks: dict[str, bool], output_path: Path) -> None:
    status = "PASS" if all(checks.values()) else "FAIL"
    lines = [
        "# U.S. Census Imports Validation Report",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"Overall status: **{status}**",
        "",
        "## Check Summary",
        "",
        "| Check | Result |",
        "|---|---|",
    ]
    for name, ok in checks.items():
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} |")
    lines.extend(["", "## Core Metrics", "", "| Dataset | Raw files | Rows | Source files | Row groups |", "|---|---:|---:|---:|---:|"])
    for level, output_name in [("HS10", "us_imports_hs10_monthly.parquet"), ("HS6", "us_imports_hs6_monthly.parquet")]:
        raw = report["raw"][level]
        parquet = report["parquet"][level]
        lines.append(
            f"| {output_name} | {raw['actual_files']:,} | {parquet['rows']:,} | {parquet['source_files']:,} | {parquet['row_groups']:,} |"
        )
    lines.extend(
        [
            "",
            "## Official API Recheck",
            "",
            "| Level | Month | Origin | API rows | Raw rows | Parquet rows | Exact raw match | Sorted raw match |",
            "|---|---|---|---:|---:|---:|---|---|",
        ]
    )
    for sample in report["official_api"].get("samples", []):
        lines.append(
            "| {level} | {month} | {origin_iso3} | {api_rows:,} | {raw_rows:,} | {parquet_rows:,} | {exact} | {sorted_match} |".format(
                level=sample["level"],
                month=sample["month"],
                origin_iso3=sample["origin_iso3"],
                api_rows=sample["api_rows"],
                raw_rows=sample["raw_rows"],
                parquet_rows=sample["parquet_rows"],
                exact="yes" if sample["api_equals_raw_exact"] else "no",
                sorted_match="yes" if sample["api_equals_raw_sorted"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Raw file completeness is checked against the configured 15 origins and 132 months.",
            "- Raw-parquet equality compares row counts and sums of import value, quantity, customs value, duties, and dutiable value for every source file.",
            "- Official API checks re-query selected country-month-level cells and compare the current API response against local raw JSON and parquet aggregates.",
            "- The API key is read from the process environment and is not written to this report.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate U.S. Census monthly import raw and parquet outputs.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--skip-api", action="store_true", help="Skip live Census API sample checks.")
    parser.add_argument("--output-dir", default="data/validation")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    context = expected_context(project_root)
    validation_dir = (project_root / args.output_dir).resolve()
    validation_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project_root),
        "years": context["years"],
        "months": context["months"],
        "origins": [country["origin_iso3"] for country in context["countries"]],
        "raw": {},
        "parquet": {},
        "raw_parquet_compare": {},
        "official_api": {},
    }

    raw_by_level: dict[str, dict[str, dict[str, float]]] = {}
    parquet_by_level: dict[str, dict[str, dict[str, float]]] = {}
    for level in ["HS10", "HS6"]:
        raw_summary, raw_by_source = scan_raw_level(
            context["raw_dirs"],
            level,
            context["months"],
            context["countries"],
        )
        parquet_summary, parquet_by_source = scan_parquet(context["output_paths"][level])
        report["raw"][level] = raw_summary
        report["parquet"][level] = parquet_summary
        report["raw_parquet_compare"][level] = compare_raw_parquet(raw_by_source, parquet_by_source)
        raw_by_level[level] = raw_by_source
        parquet_by_level[level] = parquet_by_source

    api_key = None
    if not args.skip_api:
        try:
            api_key = api_key_from_env(context["data_versions"], explicit_key=None)
        except RuntimeError:
            api_key = None
    report["official_api"] = (
        {"status": "skipped_by_flag", "samples": []}
        if args.skip_api
        else official_api_checks(context["data_versions"], context["raw_dirs"], parquet_by_level, api_key)
    )

    checks = pass_fail(report)
    report["checks"] = checks
    report["overall_status"] = "PASS" if all(checks.values()) else "FAIL"

    json_path = validation_dir / "us_census_imports_validation.json"
    md_path = validation_dir / "us_census_imports_validation.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(report, checks, md_path)
    print(json.dumps({"overall_status": report["overall_status"], "json": str(json_path), "markdown": str(md_path)}, indent=2), flush=True)
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
