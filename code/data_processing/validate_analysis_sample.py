from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def year_set(window: dict[str, int]) -> set[int]:
    return set(range(int(window["start"]), int(window["end"]) + 1))


def unique_list(values: list[str], label: str, failures: list[str]) -> None:
    if len(values) != len(set(values)):
        failures.append(f"{label} contains duplicate entries")


def validate(project_root: Path) -> dict[str, Any]:
    sample = load_yaml(project_root / "configs" / "analysis_sample_v1.yaml")
    countries = load_yaml(project_root / "configs" / "country_groups.yaml")
    sectors = load_yaml(project_root / "configs" / "sector_scope.yaml")
    product_rules = load_yaml(project_root / "configs" / "product_sector_rules.yaml")
    source_sector_rules = load_yaml(project_root / "configs" / "source_sector_rules.yaml")
    windows = load_yaml(project_root / "configs" / "time_windows.yaml")
    census = load_yaml(project_root / "configs" / "us_census_country_codes.yaml")
    overrides = load_yaml(project_root / "configs" / "country_code_overrides.yaml")
    manifest = json.loads(
        (project_root / "data" / "validation" / "data_merge_input_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    quality = json.loads(
        (project_root / "data" / "validation" / "data_merge_input_quality_audit.json").read_text(
            encoding="utf-8"
        )
    )
    product_validation = json.loads(
        (project_root / "data" / "validation" / "product_sector_crosswalk_validation.json").read_text(
            encoding="utf-8"
        )
    )
    source_sector_validation = json.loads(
        (project_root / "data" / "validation" / "source_sector_crosswalk_validation.json").read_text(
            encoding="utf-8"
        )
    )
    input_years = {item["input_id"]: set(item["year_coverage"]) for item in manifest["inputs"]}
    quality_by_id = {item["input_id"]: item for item in quality["inputs"]}

    failures: list[str] = []
    checks: dict[str, bool] = {}

    country_contracts = {
        "source_core": countries["source_bloc"]["core"],
        "source_extended_east_asia": countries["source_bloc"]["extended_east_asia"],
        "destination_core": countries["destination_bloc"]["core"],
        "core_connectors": countries["core_connectors"],
        "asian_comparators": countries["asian_comparators"],
        "other_candidates": countries["other_candidates"],
    }
    for field, expected in country_contracts.items():
        actual = sample["countries"][field]
        checks[f"country_contract.{field}"] = actual == expected
        if actual != expected:
            failures.append(f"analysis_sample_v1 countries.{field} differs from country_groups.yaml")
        unique_list(actual, f"countries.{field}", failures)

    connector_groups = [
        set(sample["countries"]["core_connectors"]),
        set(sample["countries"]["asian_comparators"]),
        set(sample["countries"]["other_candidates"]),
    ]
    disjoint = all(
        not connector_groups[left].intersection(connector_groups[right])
        for left in range(len(connector_groups))
        for right in range(left + 1, len(connector_groups))
    )
    checks["connector_groups_disjoint"] = disjoint
    if not disjoint:
        failures.append("core connectors, Asian comparators, and other candidates overlap")

    census_origins = sorted(census["country_codes"])
    frozen_census_origins = sorted(sample["countries"]["census_validation_origins"])
    audited_census_origins = sorted(
        value
        for value in quality_by_id["us_census_hs6_monthly"]["category_counts"]["origin_iso3"]
        if value != "<NULL>"
    )
    checks["census_origin_config_matches_frozen_sample"] = census_origins == frozen_census_origins
    checks["census_origin_data_matches_frozen_sample"] = audited_census_origins == frozen_census_origins
    if census_origins != frozen_census_origins:
        failures.append("frozen Census origin list differs from us_census_country_codes.yaml")
    if audited_census_origins != frozen_census_origins:
        failures.append("frozen Census origin list differs from the validated Census data")

    tw_override = sample["countries"]["baci_country_overrides"]["TWN"]
    source_override = overrides["country_code_overrides"]["TWN"]
    checks["twn_baci_proxy_matches"] = (
        tw_override["baci_iso3"] == source_override["baci_iso3"] == "S19"
        and tw_override["proxy"] is True
        and source_override["proxy"] is True
    )
    if not checks["twn_baci_proxy_matches"]:
        failures.append("TWN BACI proxy is not consistently frozen as S19")

    checks["priority_sectors_match"] = sample["sectors"]["priority"] == sectors["priority_sectors"]
    checks["excluded_sectors_match"] = (
        sample["sectors"]["first_round_exclusions"] == sectors["exclude_first_round"]
    )
    if not checks["priority_sectors_match"]:
        failures.append("frozen priority sectors differ from sector_scope.yaml")
    if not checks["excluded_sectors_match"]:
        failures.append("frozen sector exclusions differ from sector_scope.yaml")
    checks["product_sector_config_reference_matches"] = (
        sample["source_configs"]["product_sector_rules"] == "configs/product_sector_rules.yaml"
    )
    checks["product_sector_mapping_version_matches"] = (
        sample["sectors"]["product_mapping_version"] == product_rules["version"]
        == product_validation["mapping_version"]
    )
    checks["product_sector_mapping_validation_passed"] = (
        product_validation["validation_status"] == "PASS"
    )
    if not checks["product_sector_config_reference_matches"]:
        failures.append("frozen sample does not reference product_sector_rules.yaml")
    if not checks["product_sector_mapping_version_matches"]:
        failures.append("frozen product-sector mapping version is inconsistent")
    if not checks["product_sector_mapping_validation_passed"]:
        failures.append("product-sector crosswalk validation has not passed")
    checks["source_sector_config_reference_matches"] = (
        sample["source_configs"]["source_sector_rules"] == "configs/source_sector_rules.yaml"
    )
    checks["source_sector_mapping_version_matches"] = (
        sample["sectors"]["source_sector_mapping_version"] == source_sector_rules["version"]
        == source_sector_validation["mapping_version"]
    )
    checks["source_sector_mapping_validation_passed"] = (
        source_sector_validation["validation_status"] == "PASS"
    )
    if not checks["source_sector_config_reference_matches"]:
        failures.append("frozen sample does not reference source_sector_rules.yaml")
    if not checks["source_sector_mapping_version_matches"]:
        failures.append("frozen source-sector mapping version is inconsistent")
    if not checks["source_sector_mapping_validation_passed"]:
        failures.append("source-sector crosswalk validation has not passed")

    frozen_time = sample["time"]
    for field in ("pre_period", "shock_period", "post_period"):
        checks[f"time_contract.{field}"] = frozen_time[field] == windows[field]
        if frozen_time[field] != windows[field]:
            failures.append(f"frozen {field} differs from time_windows.yaml")

    trade_years = year_set(frozen_time["annual_trade_panel"])
    pre_years = year_set(frozen_time["pre_period"])
    shock_years = year_set(frozen_time["shock_period"])
    post_years = year_set(frozen_time["post_period"])
    checks["time_windows_disjoint"] = not (
        pre_years.intersection(shock_years)
        or pre_years.intersection(post_years)
        or shock_years.intersection(post_years)
    )
    checks["time_windows_cover_trade_panel"] = pre_years | shock_years | post_years == trade_years
    if not checks["time_windows_disjoint"]:
        failures.append("pre, shock, and post windows overlap")
    if not checks["time_windows_cover_trade_panel"]:
        failures.append("pre, shock, and post windows do not exactly cover the annual trade panel")

    for input_id in (
        "baci_hs6_panel",
        "us_census_hs6_monthly",
        "section301_hs6_exposure",
    ):
        covered = trade_years.issubset(input_years[input_id])
        checks[f"coverage.{input_id}.trade_panel"] = covered
        if not covered:
            failures.append(f"{input_id} does not cover the frozen 2014-2024 trade panel")

    production_windows = frozen_time["production_validation_windows"]
    coverage_contracts = {
        "oecd_amne_affiliate_activity": year_set(production_windows["trade_amne_overlap"]),
        "bea_us_mne_affiliate_country_industry": year_set(production_windows["bea_mne_overlap"]),
        "bea_direct_investment_country_industry": year_set(production_windows["fdi_extension"]),
        "mexico_fdi_country_sector_quarterly": year_set(production_windows["fdi_extension"]),
    }
    for input_id, required_years in coverage_contracts.items():
        covered = required_years.issubset(input_years[input_id])
        checks[f"coverage.{input_id}"] = covered
        if not covered:
            failures.append(f"{input_id} does not cover its frozen production-validation window")

    baselines = frozen_time["structural_baselines"]
    selected_baselines = {
        int(baselines["primary_pre_shock"]),
        int(baselines["shock_onset_interface"]),
        int(baselines["post_shock_robustness"]),
    }
    available_icio_years = input_years["oecd_icio_output_va_fd"]
    checks["selected_structural_baselines_available"] = selected_baselines.issubset(
        available_icio_years
    )
    checks["primary_baseline_is_pre_shock_2017"] = baselines["primary_pre_shock"] == 2017
    checks["unsupported_2019_excluded"] = (
        baselines["excluded_candidate"]["year"] == 2019 and 2019 not in selected_baselines
    )
    if not checks["selected_structural_baselines_available"]:
        failures.append("selected structural baselines are not all available in the ICIO input")
    if not checks["primary_baseline_is_pre_shock_2017"]:
        failures.append("primary structural baseline is not frozen at pre-shock year 2017")
    if not checks["unsupported_2019_excluded"]:
        failures.append("unsupported 2019 ICIO baseline was not explicitly excluded")

    excluded_sources = set(sample["scope_exclusions"])
    checks["fdi_markets_excluded"] = "fDi Markets" in excluded_sources
    if not checks["fdi_markets_excluded"]:
        failures.append("fDi Markets is not listed as excluded from the first-stage scope")

    checks["upstream_quality_audit_passed"] = quality["validation_status"] == "PASS"
    if not checks["upstream_quality_audit_passed"]:
        failures.append("M0.4 input quality audit has not passed")

    return {
        "validation_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_version": sample["version"],
        "status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "checks": checks,
        "frozen_summary": {
            "core_connectors": sample["countries"]["core_connectors"],
            "asian_comparators": sample["countries"]["asian_comparators"],
            "other_candidates": sample["countries"]["other_candidates"],
            "priority_sectors": sample["sectors"]["priority"],
            "trade_years": sorted(trade_years),
            "pre_years": sorted(pre_years),
            "shock_years": sorted(shock_years),
            "post_years": sorted(post_years),
            "selected_structural_baselines": sorted(selected_baselines),
            "excluded_structural_candidate": baselines["excluded_candidate"],
            "census_validation_origins": frozen_census_origins,
        },
    }


def markdown_report(validation: dict[str, Any]) -> str:
    summary = validation["frozen_summary"]
    lines = [
        "# Analysis Sample V1 Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Sample version: `{validation['sample_version']}`",
        f"- Failure count: `{validation['failure_count']}`",
        f"- Validation status: **{validation['status']}**",
        "",
        "## Frozen sample",
        "",
        f"- Core connectors: `{', '.join(summary['core_connectors'])}`",
        f"- Asian comparators: `{', '.join(summary['asian_comparators'])}`",
        f"- Other candidates: `{', '.join(summary['other_candidates'])}`",
        f"- Priority sectors: `{', '.join(summary['priority_sectors'])}`",
        f"- Trade window: `{summary['trade_years'][0]}-{summary['trade_years'][-1]}`",
        f"- Pre period: `{summary['pre_years'][0]}-{summary['pre_years'][-1]}`",
        f"- Shock period: `{summary['shock_years'][0]}-{summary['shock_years'][-1]}`",
        f"- Post period: `{summary['post_years'][0]}-{summary['post_years'][-1]}`",
        f"- Selected structural baselines: `{', '.join(str(year) for year in summary['selected_structural_baselines'])}`",
        f"- Excluded structural candidate: `{summary['excluded_structural_candidate']['year']}` — {summary['excluded_structural_candidate']['reason']}",
        "",
        "## Validation checks",
        "",
        "| Check | Passed |",
        "|---|---|",
    ]
    lines.extend(
        f"| `{name}` | {'yes' if passed else 'no'} |"
        for name, passed in validation["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The frozen sample fixes the first-stage country, sector, and time scope. Product-level and source-sector concordances are validated, including explicit unsupported and ambiguous source categories. The 2017 ICIO baseline is primary because it precedes the 2018 Section 301 shock; 2018 is retained as the shock-onset interface and 2022 as a post-shock robustness baseline. The unsupported 2019 ICIO candidate is explicitly excluded rather than imputed.",
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
    parser = argparse.ArgumentParser(description="Validate the frozen first-stage sample.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/validation/analysis_sample_v1_validation.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("data/validation/analysis_sample_v1_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_json = args.output_json if args.output_json.is_absolute() else project_root / args.output_json
    output_md = args.output_md if args.output_md.is_absolute() else project_root / args.output_md
    result = validate(project_root)
    write_text(
        output_json,
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        overwrite=args.overwrite,
    )
    write_text(output_md, markdown_report(result), overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "status": result["status"],
                "failure_count": result["failure_count"],
                "output_json": str(output_json),
                "output_md": str(output_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
