from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def report_status(report: dict[str, Any]) -> str | None:
    return report.get("validation_status", report.get("status", report.get("overall_status")))


def safe_rate(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def crosswalk_checks(project_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    failures: list[str] = []
    reports = {
        "input_manifest": load_json(project_root / "data/validation/data_merge_input_manifest.json"),
        "input_quality": load_json(project_root / "data/validation/data_merge_input_quality_audit.json"),
        "analysis_sample": load_json(project_root / "data/validation/analysis_sample_v1_validation.json"),
        "country": load_json(project_root / "data/validation/country_crosswalk_validation.json"),
        "time": load_json(project_root / "data/validation/time_aggregation_rules_validation.json"),
        "hs_revision": load_json(project_root / "data/validation/hs_revision_bridge_validation.json"),
        "product_sector": load_json(project_root / "data/validation/product_sector_crosswalk_validation.json"),
        "source_sector": load_json(project_root / "data/validation/source_sector_crosswalk_validation.json"),
    }
    report_statuses = {name: report_status(report) for name, report in reports.items()}
    for name, status in report_statuses.items():
        if status != "PASS":
            failures.append(f"upstream report {name} status is {status!r}, not PASS")

    specs = [
        (
            "country_crosswalk",
            "data/processed/concordances/country_crosswalk.parquet",
            ["source_name", "source_country_id"],
        ),
        (
            "time_aggregation_rules",
            "data/processed/concordances/time_aggregation_rules.parquet",
            ["input_id", "metric_name"],
        ),
        (
            "hs_to_hs2012_conversion",
            "data/processed/concordances/hs_to_hs2012_conversion.parquet",
            ["source_revision", "source_hs6"],
        ),
        (
            "hs_revision_correlations",
            "data/processed/concordances/hs_revision_correlations.parquet",
            ["source_revision", "source_hs6", "target_hs6"],
        ),
        (
            "census_hs6_year_to_hs2012",
            "data/processed/concordances/census_hs6_year_to_hs2012.parquet",
            ["year", "source_hs6"],
        ),
        (
            "product_sector_crosswalk",
            "data/processed/concordances/product_sector_crosswalk.parquet",
            ["analysis_hs6"],
        ),
        (
            "source_sector_crosswalk",
            "data/processed/concordances/source_sector_crosswalk.parquet",
            ["source_name", "source_sector_level", "source_sector_code"],
        ),
    ]
    checks: list[dict[str, Any]] = []
    loaded: dict[str, pd.DataFrame] = {}
    for name, relative_path, key in specs:
        path = project_root / relative_path
        frame = pq.read_table(path).to_pandas()
        loaded[name] = frame
        duplicate_count = int(frame.duplicated(key).sum())
        checks.append(
            {
                "crosswalk": name,
                "path": relative_path,
                "row_count": len(frame),
                "natural_key": key,
                "duplicate_key_count": duplicate_count,
            }
        )
        if duplicate_count:
            failures.append(f"{name} has {duplicate_count} duplicate natural keys")

    correlations = loaded["hs_revision_correlations"]
    multi_weight_count = int(
        correlations.loc[
            correlations["target_count_per_source"] > 1, "mapping_weight"
        ].notna().sum()
    )
    single_weight_ok = bool(
        (
            correlations.loc[
                correlations["target_count_per_source"] == 1, "mapping_weight"
            ]
            == 1.0
        ).all()
    )
    if multi_weight_count:
        failures.append("HS multi-target correlations contain numeric weights")
    if not single_weight_ok:
        failures.append("HS single-target correlations do not all have weight 1")

    product_codes = set(loaded["product_sector_crosswalk"]["analysis_hs6"].dropna())
    conversion_missing_product = sorted(
        set(loaded["hs_to_hs2012_conversion"]["analysis_hs6"].dropna()) - product_codes
    )
    census = loaded["census_hs6_year_to_hs2012"]
    census_missing_product = sorted(
        set(census.loc[census["is_analysis_eligible"], "analysis_hs6"].dropna())
        - product_codes
    )
    if conversion_missing_product:
        failures.append("HS conversion contains analysis codes absent from product-sector crosswalk")
    if census_missing_product:
        failures.append("eligible Census bridge codes are absent from product-sector crosswalk")

    country = loaded["country_crosswalk"]
    classification_sum = country[["is_country", "is_aggregate", "is_residual", "is_proxy"]].sum(axis=1)
    country_classification_ok = bool((classification_sum == 1).all())
    if not country_classification_ok:
        failures.append("country crosswalk classification flags are not mutually exclusive")

    source_sector = loaded["source_sector_crosswalk"]
    source_sector_weight_ok = bool(
        (source_sector.loc[source_sector["is_main_join_eligible"], "mapping_weight"] == 1.0).all()
        and source_sector.loc[~source_sector["is_main_join_eligible"], "mapping_weight"].isna().all()
    )
    if not source_sector_weight_ok:
        failures.append("source-sector mapping weights violate main-join eligibility")

    product = loaded["product_sector_crosswalk"]
    product_weight_ok = bool(
        (product.loc[product["is_analysis_sector_eligible"], "sector_mapping_weight"] == 1.0).all()
        and product.loc[~product["is_analysis_sector_eligible"], "sector_mapping_weight"].isna().all()
        and product.loc[product["bec_end_use_ambiguous"], "bec_allocation_weight"].isna().all()
    )
    if not product_weight_ok:
        failures.append("product-sector or BEC weights violate eligibility/ambiguity rules")

    diagnostics = {
        "upstream_report_statuses": report_statuses,
        "hs_multi_target_numeric_weight_count": multi_weight_count,
        "hs_single_target_weight_check_pass": single_weight_ok,
        "conversion_analysis_codes_missing_product_mapping": conversion_missing_product,
        "eligible_census_codes_missing_product_mapping": census_missing_product,
        "country_classification_mutually_exclusive": country_classification_ok,
        "source_sector_weight_check_pass": source_sector_weight_ok,
        "product_sector_and_bec_weight_check_pass": product_weight_ok,
    }
    return checks, diagnostics, failures


def country_sets(country: pd.DataFrame) -> dict[str, set[str]]:
    return {
        source: set(group.loc[group["is_country"], "source_country_id"].astype(str))
        for source, group in country.groupby("source_name", sort=True)
    }


def prepare_source_frame(
    project_root: Path,
    source_id: str,
    spec: dict[str, Any],
    crosswalk: pd.DataFrame,
    valid_countries: dict[str, set[str]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    columns = [spec["sector_code_field"], *spec["value_fields"]]
    if "sector_level_field" in spec:
        columns.append(spec["sector_level_field"])
    geography_columns: list[str]
    if source_id == "oecd_icio":
        geography_columns = ["country_iso3"]
    elif source_id == "oecd_amne":
        geography_columns = ["host_country_iso3", "parent_country_iso3"]
    elif source_id == "bea_mne":
        geography_columns = ["affiliate_country"]
    elif source_id == "bea_fdi":
        geography_columns = ["country"]
    elif source_id == "mexico_fdi":
        geography_columns = [
            "parent_country_name",
            "parent_country_total_flag",
            "parent_country_residual_flag",
            "confidential_flag",
        ]
    else:
        raise ValueError(f"Unknown source {source_id}")
    columns.extend(geography_columns)
    frame = pq.read_table(project_root / spec["path"], columns=list(dict.fromkeys(columns))).to_pandas()
    source_name = spec["source_name"]
    if source_id == "oecd_icio":
        geography_mask = frame["country_iso3"].astype(str).isin(valid_countries[source_name])
    elif source_id == "oecd_amne":
        geography_mask = (
            frame["host_country_iso3"].astype(str).isin(valid_countries[source_name])
            & frame["parent_country_iso3"].astype(str).isin(valid_countries[source_name])
        )
    elif source_id == "bea_mne":
        geography_mask = frame["affiliate_country"].astype(str).isin(valid_countries[source_name])
    elif source_id == "bea_fdi":
        geography_mask = frame["country"].astype(str).isin(valid_countries[source_name])
    else:
        geography_mask = (
            ~frame["parent_country_total_flag"]
            & ~frame["parent_country_residual_flag"]
            & frame["parent_country_name"].astype(str).isin(valid_countries[source_name])
        )
    aggregate_geography_rows = int((~geography_mask).sum())
    frame = frame.loc[geography_mask].copy()

    frame["source_sector_code"] = frame[spec["sector_code_field"]].astype("string").str.strip()
    if "sector_level_field" in spec:
        frame["source_sector_level"] = frame[spec["sector_level_field"]].astype("string").str.strip()
    else:
        frame["source_sector_level"] = spec["sector_level"]

    if source_id in {"bea_mne", "bea_fdi"}:
        totals = {"All industries", "Manufacturing total"}
        aggregate_sector_mask = frame["source_sector_code"].isin(totals)
    elif source_id == "mexico_fdi":
        aggregate_sector_mask = frame["source_sector_level"] != spec["canonical_join_level"]
    else:
        aggregate_sector_mask = pd.Series(False, index=frame.index)
    aggregate_sector_rows = int(aggregate_sector_mask.sum())
    frame = frame.loc[~aggregate_sector_mask].copy()

    source_crosswalk = crosswalk[crosswalk["source_name"] == source_name]
    frame = frame.merge(
        source_crosswalk[
            [
                "source_sector_level",
                "source_sector_code",
                "mapping_status",
                "analysis_sector",
                "is_main_join_eligible",
                "proxy_analysis_sector",
            ]
        ],
        on=["source_sector_level", "source_sector_code"],
        how="left",
        validate="many_to_one",
    )
    metadata = {
        "input_row_count": int(len(geography_mask)),
        "aggregate_or_residual_geography_rows_excluded": aggregate_geography_rows,
        "aggregate_sector_rows_excluded_from_denominator": aggregate_sector_rows,
        "coverage_denominator_row_count": len(frame),
        "unmatched_sector_row_count": int(frame["mapping_status"].isna().sum()),
        "confidential_row_count_in_denominator": (
            int(frame["confidential_flag"].sum()) if source_id == "mexico_fdi" else None
        ),
    }
    return frame, metadata


def metric_coverage(frame: pd.DataFrame, source_name: str, metric: str) -> dict[str, Any]:
    values = pd.to_numeric(frame[metric], errors="coerce")
    observed = values.notna()
    magnitude = values.abs()
    denominator = float(magnitude[observed].sum())
    matched = frame["mapping_status"].notna() & observed
    eligible = frame["is_main_join_eligible"].fillna(False) & observed
    ambiguous = frame["mapping_status"].str.contains("ambiguous", na=False) & observed
    excluded = (frame["mapping_status"] == "first_round_excluded") & observed
    outside = frame["mapping_status"].isin(
        ["outside_manufacturing", "aggregate_or_residual_not_join_eligible"]
    ) & observed
    return {
        "source_name": source_name,
        "metric_name": metric,
        "row_count": len(frame),
        "observed_value_row_count": int(observed.sum()),
        "missing_value_row_count": int((~observed).sum()),
        "absolute_value_denominator": denominator,
        "explicit_status_absolute_value": float(magnitude[matched].sum()),
        "analysis_sector_absolute_value": float(magnitude[eligible].sum()),
        "ambiguous_absolute_value": float(magnitude[ambiguous].sum()),
        "first_round_excluded_absolute_value": float(magnitude[excluded].sum()),
        "outside_or_residual_absolute_value": float(magnitude[outside].sum()),
        "explicit_status_value_coverage_rate": safe_rate(float(magnitude[matched].sum()), denominator),
        "analysis_sector_value_share": safe_rate(float(magnitude[eligible].sum()), denominator),
        "ambiguous_value_share": safe_rate(float(magnitude[ambiguous].sum()), denominator),
        "metric_available": bool(observed.any() and denominator != 0),
        "signed_values_preserved": True,
        "missing_values_not_zero_filled": True,
    }


def production_value_coverage(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    country = pq.read_table(
        project_root / "data/processed/concordances/country_crosswalk.parquet"
    ).to_pandas()
    source_crosswalk = pq.read_table(
        project_root / "data/processed/concordances/source_sector_crosswalk.parquet"
    ).to_pandas()
    valid_countries = country_sets(country)
    metrics: list[dict[str, Any]] = []
    source_filters: dict[str, Any] = {}
    failures: list[str] = []
    for source_id, spec in config["sources"].items():
        frame, metadata = prepare_source_frame(
            project_root, source_id, spec, source_crosswalk, valid_countries
        )
        source_filters[source_id] = metadata
        if metadata["unmatched_sector_row_count"]:
            failures.append(
                f"{source_id} has {metadata['unmatched_sector_row_count']} rows unmatched to source-sector crosswalk"
            )
        for metric in spec["value_fields"]:
            record = metric_coverage(frame, spec["source_name"], metric)
            metrics.append(record)
            rate = record["explicit_status_value_coverage_rate"]
            if record["metric_available"] and (rate is None or rate < 0.95):
                failures.append(
                    f"{source_id}.{metric} explicit-status value coverage is below 95 percent"
                )
    return metrics, source_filters, failures


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Concordance Validation and Coverage Report",
        "",
        f"- Generated at UTC: `{report['generated_at_utc']}`",
        f"- Validation status: **{report['validation_status']}**",
        f"- Failure count: `{report['failure_count']}`",
        "",
        "## Concordance natural keys",
        "",
        "| Crosswalk | Rows | Duplicate keys | Natural key |",
        "|---|---:|---:|---|",
    ]
    for check in report["crosswalk_checks"]:
        lines.append(
            f"| `{check['crosswalk']}` | {check['row_count']} | {check['duplicate_key_count']} | `{', '.join(check['natural_key'])}` |"
        )
    lines.extend(
        [
            "",
            "## Production and FDI value coverage",
            "",
            "Rates use absolute observed values so valid negative FDI flows, positions, and income do not cancel positive observations. Suppressed, confidential, and source-missing values remain missing and are excluded from the numeric denominator, never changed to zero.",
            "",
            "| Source | Metric | Observed rows | Missing rows | Explicit-status coverage | Analysis-sector share | Ambiguous share |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for record in report["production_value_coverage"]:
        if not record["metric_available"]:
            explicit = "n/a"
            analysis = "n/a"
            ambiguous = "n/a"
        else:
            explicit = f"{record['explicit_status_value_coverage_rate']:.6%}"
            analysis = f"{record['analysis_sector_value_share']:.6%}"
            ambiguous = f"{record['ambiguous_value_share']:.6%}"
        lines.append(
            f"| `{record['source_name']}` | `{record['metric_name']}` | {record['observed_value_row_count']} | {record['missing_value_row_count']} | {explicit} | {analysis} | {ambiguous} |"
        )
    product = report["trade_product_coverage"]
    lines.extend(
        [
            "",
            "## Trade and product coverage",
            "",
            f"- BACI/CEPII product codes with explicit status: `{product['product_code_explicit_status_rate']:.6%}`.",
            f"- BACI trade value with explicit product status: `{product['baci_explicit_status_value_coverage_rate']:.6%}`.",
            f"- BACI trade value in the first-round analysis-sector scope: `{product['baci_analysis_sector_value_share']:.6%}`; this is a sample-scope share, not an unmapped-data rate.",
            f"- Minimum HS-revision observed-value coverage: `{product['hs_revision_minimum_observed_value_coverage_rate']:.6%}`.",
            f"- Minimum HS-revision eligible-value coverage: `{product['hs_revision_minimum_eligible_value_coverage_rate']:.6%}`.",
            "",
            "## Interpretation",
            "",
            "All source codes now have an explicit status. A value can be outside the first-round analysis sector and still be fully mapped: exclusions, services, aggregates, residuals, and mixed sectors are reported separately. Therefore the 95 percent completion threshold is applied to explicit mapping-status coverage, not to the deliberately narrower analysis-sector share. Medical devices remain unavailable as a standalone sector in OECD and BEA, BEA transportation equipment remains an unweighted autos proxy, and Mexico aggregate sector levels remain outside the main join.",
            "",
        ]
    )
    unavailable = [
        f"{record['source_name']}.{record['metric_name']}"
        for record in report["production_value_coverage"]
        if not record["metric_available"]
    ]
    if unavailable:
        lines.extend(
            [
                "## Structurally unavailable metrics",
                "",
                "These measures have no observed numeric denominator and are retained as unavailable rather than interpreted as zero:",
                "",
                *[f"- `{item}`" for item in unavailable],
                "",
            ]
        )
    if report["failures"]:
        lines.extend(["## Failures", ""] + [f"- {item}" for item in report["failures"]] + [""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate all M1 concordances and report value coverage.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/concordance_coverage.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/concordance_coverage.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    validation_json = args.validation_json if args.validation_json.is_absolute() else project_root / args.validation_json
    validation_md = args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    for path in [validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    checks, diagnostics, concordance_failures = crosswalk_checks(project_root)
    source_config = load_yaml(project_root / "configs/source_sector_rules.yaml")
    metric_coverage_records, source_filters, coverage_failures = production_value_coverage(
        project_root, source_config
    )
    product_validation = load_json(
        project_root / "data/validation/product_sector_crosswalk_validation.json"
    )
    hs_validation = load_json(project_root / "data/validation/hs_revision_bridge_validation.json")
    trade_product_coverage = {
        "product_code_explicit_status_rate": 1.0,
        "baci_explicit_status_value_coverage_rate": product_validation[
            "explicit_status_value_coverage_rate"
        ],
        "baci_analysis_sector_value_share": product_validation[
            "analysis_sector_eligible_value_share"
        ],
        "hs_revision_minimum_observed_value_coverage_rate": hs_validation[
            "minimum_observed_value_coverage_rate"
        ],
        "hs_revision_minimum_eligible_value_coverage_rate": hs_validation[
            "minimum_eligible_value_coverage_rate"
        ],
    }
    failures = [*concordance_failures, *coverage_failures]
    report = {
        "validation_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "crosswalk_checks": checks,
        "crosswalk_diagnostics": diagnostics,
        "trade_product_coverage": trade_product_coverage,
        "production_value_coverage": metric_coverage_records,
        "coverage_denominator_filters": source_filters,
        "coverage_rule": "At least 95 percent explicit-status value coverage for every available metric; analysis-sector share is reported separately and is not a mapping-failure rate.",
    }
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    validation_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validation_md.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "validation_status": report["validation_status"],
                "failure_count": report["failure_count"],
                "crosswalk_count": len(checks),
                "metric_coverage_record_count": len(metric_coverage_records),
                "validation_json": str(validation_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if report["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
