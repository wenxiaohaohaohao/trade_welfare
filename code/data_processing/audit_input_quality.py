from __future__ import annotations

import argparse
import gc
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from build_input_manifest import INPUT_SPECS, InputSpec


NUMERIC_FIELDS: dict[str, tuple[str, ...]] = {
    "baci_hs6_panel": ("trade_value_usd", "quantity"),
    "us_census_hs6_monthly": (
        "import_value_usd",
        "quantity",
        "customs_value",
        "duties",
        "dutiable_value_usd",
    ),
    "section301_hs6_exposure": (
        "tariff_rate",
        "china_import_share_2017",
        "tariff_exposure",
    ),
    "oecd_icio_output_va_fd": (
        "gross_output",
        "gross_output_sales",
        "value_added",
        "final_demand",
        "intermediate_inputs",
        "taxes_less_subsidies",
        "exports",
        "imports",
        "intermediate_sales",
        "domestic_absorption",
    ),
    "oecd_amne_affiliate_activity": (
        "affiliate_output",
        "affiliate_value_added",
        "affiliate_employment",
        "affiliate_exports",
        "affiliate_imports",
        "foreign_affiliate_output_total",
        "gross_output",
        "parent_affiliate_output_share",
    ),
    "bea_us_mne_affiliate_country_industry": (
        "employment",
        "sales",
        "value_added",
        "capital_expenditures",
        "goods_exports_to_us",
        "goods_imports_from_us",
    ),
    "bea_direct_investment_country_industry": ("position", "flows", "income"),
    "mexico_fdi_country_sector_quarterly": ("fdi_million_usd", "fdi_usd"),
}


CATEGORY_FIELDS: dict[str, tuple[str, ...]] = {
    "baci_hs6_panel": ("unit",),
    "us_census_hs6_monthly": ("origin_iso3", "month", "quantity_unit"),
    "section301_hs6_exposure": (
        "origin_iso3",
        "destination_iso3",
        "tariffed_product",
        "list_id",
    ),
    "oecd_icio_output_va_fd": ("country_iso3", "sector_oecd"),
    "oecd_amne_affiliate_activity": (
        "host_country_iso3",
        "parent_country_iso3",
        "sector_oecd",
        "ownership_type",
        "allocation_method",
    ),
    "bea_us_mne_affiliate_country_industry": (
        "bea_area_type",
        "industry",
    ),
    "bea_direct_investment_country_industry": (
        "direction",
        "bea_area_type",
        "industry",
        "unit",
    ),
    "mexico_fdi_country_sector_quarterly": (
        "sector_level",
        "parent_country_total_flag",
        "parent_country_residual_flag",
        "confidential_flag",
    ),
}


SUPPRESSION_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "bea_us_mne_affiliate_country_industry": (
        ("capital_expenditures_suppressed", "capital_expenditures"),
        ("sales_suppressed", "sales"),
        ("value_added_suppressed", "value_added"),
        ("employment_suppressed", "employment"),
        ("goods_imports_from_us_suppressed", "goods_imports_from_us"),
        ("goods_exports_to_us_suppressed", "goods_exports_to_us"),
    ),
    "bea_direct_investment_country_industry": (
        ("flows_suppressed", "flows"),
        ("income_suppressed", "income"),
        ("position_suppressed", "position"),
    ),
    "mexico_fdi_country_sector_quarterly": (
        ("confidential_flag", "fdi_million_usd"),
        ("confidential_flag", "fdi_usd"),
    ),
}


UNIT_CONTRACTS: dict[str, dict[str, str]] = {
    "baci_hs6_panel": {
        "trade_value_usd": "current USD; BACI v is multiplied by 1,000 in the builder",
        "quantity": "metric tons when available; the unit column applies to quantity",
    },
    "us_census_hs6_monthly": {
        "import_value_usd": "current USD",
        "customs_value": "current USD",
        "duties": "current USD",
        "dutiable_value_usd": "current USD",
        "quantity": "unavailable in the current HS6 output; stored as 0 with quantity_unit '-'",
    },
    "section301_hs6_exposure": {
        "tariff_rate": "fraction in [0, 1]",
        "china_import_share_2017": "fraction in [0, 1]",
        "tariff_exposure": "tariff_rate multiplied by China import share; fraction",
    },
    "oecd_icio_output_va_fd": {
        "value_fields": "current million USD",
    },
    "oecd_amne_affiliate_activity": {
        "value_fields": "current million USD",
        "parent_affiliate_output_share": "fraction in [0, 1]",
        "affiliate_employment": "unavailable in the current source",
    },
    "bea_us_mne_affiliate_country_industry": {
        "employment": "thousands of employees",
        "other_value_fields": "millions of current dollars",
    },
    "bea_direct_investment_country_industry": {
        "position_flows_income": "millions of current dollars",
    },
    "mexico_fdi_country_sector_quarterly": {
        "fdi_million_usd": "millions of current USD",
        "fdi_usd": "current USD; equals fdi_million_usd multiplied by 1,000,000",
    },
}


def scalar_int(value: pa.Scalar | None) -> int:
    if value is None or not value.is_valid:
        return 0
    return int(value.as_py())


def count_true(array: pa.Array) -> int:
    filled = pc.fill_null(array, False)
    return scalar_int(pc.sum(pc.cast(filled, pa.int64())))


def duplicate_and_key_null_audit(
    path: Path,
    spec: InputSpec,
) -> dict[str, Any]:
    duplicate_rows = 0
    scanned_rows = 0
    key_null_rows = Counter({field: 0 for field in spec.natural_key})

    for year in spec.expected_years:
        table = pq.read_table(
            path,
            columns=list(spec.natural_key),
            filters=[("year", "=", year)],
        )
        frame = table.to_pandas(types_mapper=pd.ArrowDtype)
        scanned_rows += len(frame)
        duplicate_rows += int(frame.duplicated(subset=list(spec.natural_key)).sum())
        for field in spec.natural_key:
            key_null_rows[field] += int(frame[field].isna().sum())
        del frame, table
        gc.collect()

    if scanned_rows != spec.expected_rows:
        raise ValueError(
            f"{spec.input_id} key scan read {scanned_rows:,} rows, expected {spec.expected_rows:,}"
        )
    return {
        "scanned_rows": scanned_rows,
        "duplicate_rows": duplicate_rows,
        "key_null_rows": dict(key_null_rows),
    }


def numeric_audit(path: Path, fields: tuple[str, ...]) -> dict[str, Any]:
    parquet_file = pq.ParquetFile(path)
    stats: dict[str, dict[str, Any]] = {
        field: {
            "null_rows": 0,
            "non_null_rows": 0,
            "negative_rows": 0,
            "zero_rows": 0,
            "min": None,
            "max": None,
        }
        for field in fields
    }

    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=list(fields)):
        for index, field in enumerate(fields):
            array = batch.column(index)
            record = stats[field]
            record["null_rows"] += array.null_count
            record["non_null_rows"] += len(array) - array.null_count
            record["negative_rows"] += count_true(pc.less(array, 0))
            record["zero_rows"] += count_true(pc.equal(array, 0))
            if len(array) == array.null_count:
                continue
            min_max = pc.min_max(array).as_py()
            batch_min = min_max["min"]
            batch_max = min_max["max"]
            record["min"] = batch_min if record["min"] is None else min(record["min"], batch_min)
            record["max"] = batch_max if record["max"] is None else max(record["max"], batch_max)
    return stats


def category_audit(path: Path, fields: tuple[str, ...]) -> dict[str, dict[str, int]]:
    parquet_file = pq.ParquetFile(path)
    counts = {field: Counter() for field in fields}
    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=list(fields)):
        for index, field in enumerate(fields):
            for item in pc.value_counts(batch.column(index)).to_pylist():
                value = "<NULL>" if item["values"] is None else str(item["values"])
                counts[field][value] += int(item["counts"])
    return {field: dict(sorted(counter.items())) for field, counter in counts.items()}


def suppression_audit(
    path: Path,
    pairs: tuple[tuple[str, str], ...],
) -> dict[str, dict[str, int]]:
    columns = sorted({field for pair in pairs for field in pair})
    column_index = {name: index for index, name in enumerate(columns)}
    results = {
        f"{flag}->{value}": {
            "flagged_missing": 0,
            "flagged_nonmissing": 0,
            "unflagged_missing": 0,
            "unflagged_nonmissing": 0,
        }
        for flag, value in pairs
    }
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=columns):
        for flag, value in pairs:
            flag_array = pc.fill_null(batch.column(column_index[flag]), False)
            value_array = batch.column(column_index[value])
            missing = pc.is_null(value_array)
            present = pc.is_valid(value_array)
            not_flagged = pc.invert(flag_array)
            record = results[f"{flag}->{value}"]
            record["flagged_missing"] += count_true(pc.and_(flag_array, missing))
            record["flagged_nonmissing"] += count_true(pc.and_(flag_array, present))
            record["unflagged_missing"] += count_true(pc.and_(not_flagged, missing))
            record["unflagged_nonmissing"] += count_true(pc.and_(not_flagged, present))
    return results


def equality_count(path: Path, left: str, right: str) -> int:
    total = 0
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=[left, right]):
        total += count_true(pc.equal(batch.column(0), batch.column(1)))
    return total


def product_formula_audit(
    path: Path,
    result_field: str,
    left_field: str,
    right_field: str,
    tolerance: float,
) -> dict[str, Any]:
    mismatch_rows = 0
    max_abs_residual = 0.0
    parquet_file = pq.ParquetFile(path)
    columns = [result_field, left_field, right_field]
    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=columns):
        expected = pc.multiply(batch.column(1), batch.column(2))
        residual = pc.abs(pc.subtract(batch.column(0), expected))
        mismatch_rows += count_true(pc.greater(residual, tolerance))
        batch_max = pc.max(residual)
        if batch_max.is_valid:
            max_abs_residual = max(max_abs_residual, float(batch_max.as_py()))
    return {
        "formula": f"{result_field} = {left_field} * {right_field}",
        "tolerance": tolerance,
        "mismatch_rows": mismatch_rows,
        "max_abs_residual": max_abs_residual,
    }


def scale_formula_audit(
    path: Path,
    result_field: str,
    source_field: str,
    scale: float,
    tolerance: float,
) -> dict[str, Any]:
    mismatch_rows = 0
    max_abs_residual = 0.0
    parquet_file = pq.ParquetFile(path)
    for batch in parquet_file.iter_batches(
        batch_size=1_000_000,
        columns=[result_field, source_field],
    ):
        expected = pc.multiply(batch.column(1), scale)
        residual = pc.abs(pc.subtract(batch.column(0), expected))
        mismatch_rows += count_true(pc.greater(residual, tolerance))
        batch_max = pc.max(residual)
        if batch_max.is_valid:
            max_abs_residual = max(max_abs_residual, float(batch_max.as_py()))
    return {
        "formula": f"{result_field} = {source_field} * {scale:g}",
        "tolerance": tolerance,
        "mismatch_rows": mismatch_rows,
        "max_abs_residual": max_abs_residual,
    }


def recursive_unit_metadata(value: Any, prefix: str = "") -> dict[str, Any]:
    found: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            if "unit" in key.casefold():
                found[child_prefix] = child
            found.update(recursive_unit_metadata(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(recursive_unit_metadata(child, f"{prefix}[{index}]"))
    return found


def input_findings(
    spec: InputSpec,
    duplicate_key: dict[str, Any],
    numeric: dict[str, Any],
    categories: dict[str, dict[str, int]],
    suppression: dict[str, dict[str, int]],
    special: dict[str, Any],
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    limitations: list[str] = []
    if duplicate_key["duplicate_rows"]:
        failures.append(f"natural key has {duplicate_key['duplicate_rows']:,} duplicate rows")
    key_null_total = sum(duplicate_key["key_null_rows"].values())
    if key_null_total:
        failures.append(f"natural key fields contain {key_null_total:,} null cells")

    for relation, counts in suppression.items():
        if counts["flagged_nonmissing"]:
            failures.append(
                f"{relation} has {counts['flagged_nonmissing']:,} flagged cells with nonmissing values"
            )
        if counts["flagged_missing"]:
            limitations.append(f"{relation} preserves {counts['flagged_missing']:,} flagged missing cells")
        if counts["unflagged_missing"]:
            limitations.append(f"{relation} also has {counts['unflagged_missing']:,} unflagged missing cells")

    if spec.input_id == "baci_hs6_panel":
        if numeric["trade_value_usd"]["negative_rows"] or numeric["trade_value_usd"]["null_rows"]:
            failures.append("BACI trade_value_usd must be nonnegative and nonmissing")
        if categories["unit"] != {"metric_tons": spec.expected_rows}:
            failures.append("BACI quantity unit is not uniformly metric_tons")
        limitations.append(
            f"BACI quantity is missing in {numeric['quantity']['null_rows']:,} rows and is not required for value-based measures"
        )
        limitations.append("BACI unit describes quantity; trade_value_usd is already expressed in USD")

    elif spec.input_id == "us_census_hs6_monthly":
        for field, record in numeric.items():
            if record["negative_rows"]:
                failures.append(f"Census {field} has {record['negative_rows']:,} negative rows")
        origins = [value for value in categories["origin_iso3"] if value != "<NULL>"]
        if len(origins) != 15:
            failures.append(f"Census configured-origin scope has {len(origins)} origins, expected 15")
        limitations.append("Census scope is the configured 15 origins, not an all-origin U.S. import denominator")
        limitations.append("Census HS6 quantity is unavailable in this output: all values are 0 and quantity_unit is '-'")

    elif spec.input_id == "section301_hs6_exposure":
        for field in ("tariff_rate", "china_import_share_2017", "tariff_exposure"):
            record = numeric[field]
            if record["min"] is None or record["min"] < 0 or record["max"] > 1:
                failures.append(f"Section 301 {field} is outside [0, 1]")
        if set(categories["origin_iso3"]) != {"CHN"}:
            failures.append("Section 301 origin is not uniformly CHN")
        if set(categories["destination_iso3"]) != {"USA"}:
            failures.append("Section 301 destination is not uniformly USA")
        formula = special.get("tariff_exposure_formula", {})
        if formula.get("mismatch_rows"):
            failures.append(
                f"Section 301 tariff_exposure formula has {formula['mismatch_rows']:,} mismatched rows"
            )
        limitations.append("Exposure is gross statutory exposure; historical product exclusions are not applied")

    elif spec.input_id == "oecd_icio_output_va_fd":
        if numeric["gross_output"]["negative_rows"] or numeric["gross_output"]["null_rows"]:
            failures.append("ICIO gross_output must be nonnegative and nonmissing")
        for field, record in numeric.items():
            if record["negative_rows"] and field != "gross_output":
                limitations.append(f"ICIO {field} contains {record['negative_rows']:,} negative accounting cells")
        limitations.append("ICIO is observed only in 2017, 2018, and 2022; missing years will not be imputed")

    elif spec.input_id == "oecd_amne_affiliate_activity":
        if numeric["affiliate_output"]["negative_rows"] or numeric["affiliate_output"]["zero_rows"]:
            failures.append("AMNE affiliate_output must be strictly positive in the activity table")
        share = numeric["parent_affiliate_output_share"]
        if share["min"] is None or share["min"] < 0 or share["max"] > 1:
            failures.append("AMNE parent_affiliate_output_share is outside [0, 1]")
        if special.get("host_equals_parent_rows"):
            failures.append(
                f"AMNE activity contains {special['host_equals_parent_rows']:,} domestic parent-host rows"
            )
        limitations.append(
            f"AMNE affiliate_employment is unavailable and null in {numeric['affiliate_employment']['null_rows']:,} rows"
        )
        limitations.append("AMNE value added, exports, and imports are allocated to parents; allocation_method is retained")

    elif spec.input_id == "bea_us_mne_affiliate_country_industry":
        aggregate_rows = categories["bea_area_type"].get("aggregate", 0)
        if aggregate_rows:
            limitations.append(f"BEA MNE contains {aggregate_rows:,} aggregate geography rows to exclude downstream")
        limitations.append("BEA suppressed and employment size-range cells remain missing, not zero")

    elif spec.input_id == "bea_direct_investment_country_industry":
        aggregate_rows = categories["bea_area_type"].get("aggregate", 0)
        if aggregate_rows:
            limitations.append(f"BEA FDI contains {aggregate_rows:,} aggregate geography rows to exclude downstream")
        negative_total = sum(record["negative_rows"] for record in numeric.values())
        if negative_total:
            limitations.append(
                f"BEA FDI contains {negative_total:,} negative position/flow/income cells; signs are economically valid and retained"
            )
        limitations.append("BEA FDI is a financial-account source, not affiliate output or plant entry")

    elif spec.input_id == "mexico_fdi_country_sector_quarterly":
        formula = special.get("fdi_usd_scale_formula", {})
        if formula.get("mismatch_rows"):
            failures.append(
                f"Mexico FDI USD conversion has {formula['mismatch_rows']:,} mismatched rows"
            )
        total_rows = categories["parent_country_total_flag"].get("True", 0)
        residual_rows = categories["parent_country_residual_flag"].get("True", 0)
        if total_rows:
            limitations.append(f"Mexico FDI contains {total_rows:,} parent-country total rows")
        if residual_rows:
            limitations.append(f"Mexico FDI contains {residual_rows:,} residual-country rows")
        negative_total = sum(record["negative_rows"] for record in numeric.values())
        if negative_total:
            limitations.append(f"Mexico FDI contains {negative_total:,} negative flow cells; flow reversals are retained")
        limitations.append("Mexico confidential C cells remain null and cannot be treated as additive zeros")

    return failures, limitations


def audit_input(project_root: Path, spec: InputSpec) -> dict[str, Any]:
    path = project_root / spec.relative_path
    summary_path = project_root / spec.build_summary
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    duplicate_key = duplicate_and_key_null_audit(path, spec)
    numeric = numeric_audit(path, NUMERIC_FIELDS[spec.input_id])
    categories = category_audit(path, CATEGORY_FIELDS[spec.input_id])
    suppression = suppression_audit(path, SUPPRESSION_FIELDS.get(spec.input_id, ()))
    special: dict[str, Any] = {}
    if spec.input_id == "oecd_amne_affiliate_activity":
        special["host_equals_parent_rows"] = equality_count(
            path,
            "host_country_iso3",
            "parent_country_iso3",
        )
    elif spec.input_id == "section301_hs6_exposure":
        special["tariff_exposure_formula"] = product_formula_audit(
            path,
            "tariff_exposure",
            "tariff_rate",
            "china_import_share_2017",
            tolerance=1e-12,
        )
    elif spec.input_id == "mexico_fdi_country_sector_quarterly":
        special["fdi_usd_scale_formula"] = scale_formula_audit(
            path,
            "fdi_usd",
            "fdi_million_usd",
            scale=1_000_000.0,
            tolerance=0.01,
        )

    failures, limitations = input_findings(
        spec,
        duplicate_key,
        numeric,
        categories,
        suppression,
        special,
    )
    return {
        "input_id": spec.input_id,
        "path": spec.relative_path,
        "natural_grain": spec.natural_grain,
        "natural_key": list(spec.natural_key),
        "duplicate_key_audit": duplicate_key,
        "numeric_audit": numeric,
        "category_counts": categories,
        "suppression_confidentiality_audit": suppression,
        "special_checks": special,
        "unit_contract": UNIT_CONTRACTS[spec.input_id],
        "unit_metadata_from_build_summary": recursive_unit_metadata(summary),
        "failures": failures,
        "expected_limitations": limitations,
        "status": "PASS_WITH_EXPECTED_LIMITATIONS" if not failures else "FAIL",
    }


def build_audit(project_root: Path) -> dict[str, Any]:
    inputs = [audit_input(project_root, spec) for spec in INPUT_SPECS]
    failures = [
        {"input_id": item["input_id"], "failure": failure}
        for item in inputs
        for failure in item["failures"]
    ]
    return {
        "audit_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "M0.4 input quality, natural-key, missingness, aggregate, suppression, confidentiality, and unit audit",
        "input_count": len(inputs),
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "inputs": inputs,
    }


def markdown_report(audit: dict[str, Any]) -> str:
    lines = [
        "# Data Merge Input Quality Audit",
        "",
        f"- Generated at UTC: `{audit['generated_at_utc']}`",
        f"- Input count: `{audit['input_count']}`",
        f"- Failure count: `{audit['failure_count']}`",
        f"- Validation status: **{audit['validation_status']}**",
        "",
        "## Summary",
        "",
        "| Input | Duplicate rows | Key-null cells | Expected limitations | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for item in audit["inputs"]:
        key_null_cells = sum(item["duplicate_key_audit"]["key_null_rows"].values())
        lines.append(
            f"| `{item['input_id']}` | {item['duplicate_key_audit']['duplicate_rows']:,} | "
            f"{key_null_cells:,} | {len(item['expected_limitations'])} | `{item['status']}` |"
        )

    for item in audit["inputs"]:
        lines.extend(
            [
                "",
                f"## `{item['input_id']}`",
                "",
                f"- Path: `{item['path']}`",
                f"- Natural grain: `{item['natural_grain']}`",
                f"- Natural key: `{', '.join(item['natural_key'])}`",
                f"- Duplicate rows: `{item['duplicate_key_audit']['duplicate_rows']:,}`",
                f"- Key-null rows by field: `{json.dumps(item['duplicate_key_audit']['key_null_rows'], ensure_ascii=False)}`",
                f"- Status: **{item['status']}**",
                "",
                "### Numeric fields",
                "",
                "| Field | Null | Negative | Zero | Min | Max |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for field, record in item["numeric_audit"].items():
            lines.append(
                f"| `{field}` | {record['null_rows']:,} | {record['negative_rows']:,} | "
                f"{record['zero_rows']:,} | {record['min']} | {record['max']} |"
            )

        lines.extend(["", "### Expected limitations retained", ""])
        if item["expected_limitations"]:
            lines.extend(f"- {limitation}" for limitation in item["expected_limitations"])
        else:
            lines.append("- None.")

        lines.extend(["", "### Category counts", ""])
        for field, counts in item["category_counts"].items():
            lines.append(f"- `{field}`: `{json.dumps(counts, ensure_ascii=False)}`")

        if item["suppression_confidentiality_audit"]:
            lines.extend(["", "### Suppression/confidentiality consistency", ""])
            for relation, counts in item["suppression_confidentiality_audit"].items():
                lines.append(f"- `{relation}`: `{json.dumps(counts, ensure_ascii=False)}`")

        lines.extend(["", "### Unit contract", ""])
        for key, value in item["unit_contract"].items():
            lines.append(f"- `{key}`: {value}")

        if item["unit_metadata_from_build_summary"]:
            lines.extend(["", "### Unit metadata from build summary", ""])
            for key, value in item["unit_metadata_from_build_summary"].items():
                lines.append(f"- `{key}`: `{json.dumps(value, ensure_ascii=False)}`")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "PASS means the frozen inputs have unique stated natural keys, no null key cells, and no hard inconsistency in the source-specific checks. Expected limitations remain part of the downstream data contract; PASS does not authorize converting suppressed, confidential, aggregate, allocated, or unavailable observations to zero.",
            "",
        ]
    )
    return "\n".join(lines)


def write_text(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit frozen data-merge inputs.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/validation/data_merge_input_quality_audit.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("data/validation/data_merge_input_quality_audit.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_json = args.output_json if args.output_json.is_absolute() else project_root / args.output_json
    output_md = args.output_md if args.output_md.is_absolute() else project_root / args.output_md
    audit = build_audit(project_root)
    write_text(
        output_json,
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        overwrite=args.overwrite,
    )
    write_text(output_md, markdown_report(audit), overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "validation_status": audit["validation_status"],
                "input_count": audit["input_count"],
                "failure_count": audit["failure_count"],
                "output_json": str(output_json),
                "output_md": str(output_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if audit["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
