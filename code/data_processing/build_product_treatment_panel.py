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


def sorted_union(values: pd.Series, input_separator: str = ";", output_separator: str = ";") -> str:
    items = {
        item.strip()
        for value in values.dropna().astype(str)
        for item in value.split(input_separator)
        if item.strip()
    }
    return output_separator.join(sorted(items))


def sorted_codes(values: pd.Series) -> str:
    return "|".join(sorted(set(values.dropna().astype(str))))


def load_inputs(project_root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    inputs = config["inputs"]
    policy = pq.read_table(project_root / inputs["section301_exposure"]["path"]).to_pandas()
    weights = pq.read_table(project_root / inputs["baci_hs17_import_weights"]["path"]).to_pandas()
    conversion = pq.read_table(project_root / inputs["hs_conversion"]["path"]).to_pandas()
    product = pq.read_table(project_root / inputs["product_crosswalk"]["path"]).to_pandas()
    for frame in [policy, weights]:
        frame["hs6"] = frame["hs6"].astype("string").str.zfill(6)
    conversion = conversion[conversion["source_revision"] == "HS2017"].copy()
    return policy, weights, conversion, product


def source_panel(
    policy: pd.DataFrame,
    weights: pd.DataFrame,
    conversion: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    years = list(range(int(config["years"]["start"]), int(config["years"]["end"]) + 1))
    weights = weights.rename(
        columns={
            "hs6": "source_hs17",
            "baci_total_us_import_value_2017": "source_total_us_import_value_2017",
            "baci_china_import_value_2017": "source_china_import_value_2017",
            "china_import_share_2017": "source_china_import_share_2017",
        }
    )
    bridge = conversion[
        [
            "source_hs6",
            "target_hs6",
            "analysis_hs6",
            "mapping_method",
            "analysis_mapping_method",
            "bridge_version",
        ]
    ].rename(columns={"source_hs6": "source_hs17"})
    weights = weights.merge(bridge, on="source_hs17", how="left", validate="one_to_one")
    grid = weights.assign(_join_key=1).merge(
        pd.DataFrame({"year": years, "_join_key": 1}), on="_join_key", how="inner"
    ).drop(columns="_join_key")

    policy = policy.rename(
        columns={
            "hs6": "source_hs17",
            "tariffed_product": "source_tariffed_product",
            "list_id": "source_list_id",
            "tariff_rate": "source_tariff_rate",
            "china_import_share_2017": "policy_china_import_share_2017",
            "tariff_exposure": "policy_tariff_exposure",
        }
    )
    policy_columns = [
        "source_hs17",
        "year",
        "origin_iso3",
        "destination_iso3",
        "source_tariffed_product",
        "source_list_id",
        "source_tariff_rate",
        "policy_china_import_share_2017",
        "policy_tariff_exposure",
    ]
    policy["policy_source_observed"] = True
    policy_columns.append("policy_source_observed")
    panel = grid.merge(policy[policy_columns], on=["source_hs17", "year"], how="left", validate="one_to_one")
    panel["policy_source_observed"] = panel["policy_source_observed"].fillna(False)
    panel["source_tariffed_product"] = panel["source_tariffed_product"].fillna(False)
    panel["source_list_id"] = panel["source_list_id"].fillna("")
    panel["source_tariff_rate"] = panel["source_tariff_rate"].fillna(0.0)
    panel["origin_iso3"] = panel["origin_iso3"].fillna(config["origin_iso3"])
    panel["destination_iso3"] = panel["destination_iso3"].fillna(config["destination_iso3"])

    panel["source_exposure_numerator"] = (
        panel["source_china_import_value_2017"] * panel["source_tariff_rate"]
    )
    panel["source_total_rate_numerator"] = (
        panel["source_total_us_import_value_2017"] * panel["source_tariff_rate"]
    )
    panel["source_has_total_import_denominator"] = panel["source_total_us_import_value_2017"] > 0
    return panel


def aggregate_to_analysis(panel: pd.DataFrame) -> pd.DataFrame:
    numeric = panel.groupby(["analysis_hs6", "year"], as_index=False).agg(
        total_us_import_value_2017=("source_total_us_import_value_2017", "sum"),
        china_import_value_2017=("source_china_import_value_2017", "sum"),
        exposure_numerator=("source_exposure_numerator", "sum"),
        total_rate_numerator=("source_total_rate_numerator", "sum"),
        source_hs17_code_count=("source_hs17", "nunique"),
        policy_source_observed_count=("policy_source_observed", "sum"),
        source_tariffed_hs17_count=("source_tariffed_product", "sum"),
        source_zero_import_hs17_count=(
            "source_has_total_import_denominator",
            lambda values: int((~values).sum()),
        ),
        tariff_rate_max_source=("source_tariff_rate", "max"),
    )
    text = panel.groupby(["analysis_hs6", "year"], as_index=False).agg(
        source_hs17_codes=("source_hs17", sorted_codes),
        source_list_ids=("source_list_id", sorted_union),
        hs_mapping_methods=("mapping_method", sorted_codes),
        analysis_mapping_methods=("analysis_mapping_method", sorted_codes),
        hs_bridge_version=("bridge_version", sorted_codes),
    )
    output = numeric.merge(text, on=["analysis_hs6", "year"], validate="one_to_one")
    has_total = output["total_us_import_value_2017"] > 0
    has_china = output["china_import_value_2017"] > 0
    output["china_import_share_2017"] = pd.NA
    output.loc[has_total, "china_import_share_2017"] = (
        output.loc[has_total, "china_import_value_2017"]
        / output.loc[has_total, "total_us_import_value_2017"]
    )
    output["tariff_rate_china_weighted"] = pd.NA
    output.loc[has_china, "tariff_rate_china_weighted"] = (
        output.loc[has_china, "exposure_numerator"]
        / output.loc[has_china, "china_import_value_2017"]
    )
    output["tariff_rate_total_import_weighted"] = pd.NA
    output.loc[has_total, "tariff_rate_total_import_weighted"] = (
        output.loc[has_total, "total_rate_numerator"]
        / output.loc[has_total, "total_us_import_value_2017"]
    )
    output["tariff_rate"] = output["tariff_rate_china_weighted"].combine_first(
        output["tariff_rate_total_import_weighted"]
    ).combine_first(output["tariff_rate_max_source"])
    output["tariff_exposure"] = pd.NA
    output.loc[has_total, "tariff_exposure"] = (
        output.loc[has_total, "exposure_numerator"]
        / output.loc[has_total, "total_us_import_value_2017"]
    )
    output["tariffed_product"] = output["source_tariffed_hs17_count"] > 0
    output["policy_mapping_status"] = "mapped_hs17_import_weighted"
    output.loc[~has_total, "policy_mapping_status"] = "mapped_hs17_no_2017_import_denominator"
    return output


def complete_product_grid(
    aggregate: pd.DataFrame,
    product: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    years = pd.DataFrame(
        {"year": range(int(config["years"]["start"]), int(config["years"]["end"]) + 1)}
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
    base = product[product_fields].rename(columns={"mapping_version": "product_mapping_version"})
    grid = base.assign(_join_key=1).merge(years.assign(_join_key=1), on="_join_key").drop(columns="_join_key")
    output = grid.merge(aggregate, on=["analysis_hs6", "year"], how="left", validate="one_to_one")
    absent = output["source_hs17_code_count"].isna()
    for column in [
        "source_hs17_code_count",
        "policy_source_observed_count",
        "source_tariffed_hs17_count",
        "source_zero_import_hs17_count",
    ]:
        output[column] = output[column].fillna(0)
    output["tariffed_product"] = output["tariffed_product"].fillna(False)
    for column in [
        "tariff_rate",
        "tariff_rate_china_weighted",
        "tariff_rate_total_import_weighted",
        "tariff_rate_max_source",
    ]:
        output.loc[absent, column] = 0.0
    output.loc[absent, "policy_mapping_status"] = "no_hs17_baci_weight_mapping"
    output.loc[absent, "source_hs17_codes"] = ""
    output.loc[absent, "source_list_ids"] = ""
    output.loc[absent, "hs_mapping_methods"] = ""
    output.loc[absent, "analysis_mapping_methods"] = ""
    output.loc[absent, "hs_bridge_version"] = ""
    output["origin_iso3"] = config["origin_iso3"]
    output["destination_iso3"] = config["destination_iso3"]
    output["treatment_concept"] = config["interpretation"]["treatment_concept"]
    output["historical_exclusions_applied"] = bool(
        config["interpretation"]["historical_exclusions_applied"]
    )
    output["four_year_review_2024_included"] = bool(
        config["interpretation"]["four_year_review_2024_included"]
    )
    output["review_2024_treatment"] = config["interpretation"]["review_2024_treatment"]
    output["treatment_version"] = config["version"]

    string_columns = [
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "product_mapping_version",
        "source_hs17_codes",
        "source_list_ids",
        "hs_mapping_methods",
        "analysis_mapping_methods",
        "hs_bridge_version",
        "policy_mapping_status",
        "origin_iso3",
        "destination_iso3",
        "treatment_concept",
        "review_2024_treatment",
        "treatment_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["year"] = output["year"].astype("int16")
    for column in [
        "source_hs17_code_count",
        "policy_source_observed_count",
        "source_tariffed_hs17_count",
        "source_zero_import_hs17_count",
    ]:
        output[column] = output[column].astype("int16")
    for column in [
        "is_analysis_sector_eligible",
        "tariffed_product",
        "historical_exclusions_applied",
        "four_year_review_2024_included",
    ]:
        output[column] = output[column].astype("bool")
    drop_columns = ["exposure_numerator", "total_rate_numerator"]
    return output.drop(columns=drop_columns).sort_values(["analysis_hs6", "year"]).reset_index(drop=True)


def validate(
    project_root: Path,
    config: dict[str, Any],
    policy: pd.DataFrame,
    weights: pd.DataFrame,
    conversion: pd.DataFrame,
    product: pd.DataFrame,
    source: pd.DataFrame,
    output: pd.DataFrame,
) -> dict[str, Any]:
    failures: list[str] = []
    hash_checks = {
        name: sha256(project_root / details["path"]) == details["sha256"]
        for name, details in config["inputs"].items()
    }
    if not all(hash_checks.values()):
        failures.append("one or more configured M2.1 input hashes do not match")
    policy_duplicate_keys = int(policy.duplicated(["hs6", "year"]).sum())
    weight_duplicate_keys = int(weights.duplicated("hs6").sum())
    output_duplicate_keys = int(output.duplicated(["analysis_hs6", "year"]).sum())
    if policy_duplicate_keys or weight_duplicate_keys or output_duplicate_keys:
        failures.append("policy, weight, or output natural key is duplicated")

    policy_codes = set(policy["hs6"])
    weight_codes = set(weights["hs6"])
    policy_not_weight = sorted(policy_codes - weight_codes)
    weight_not_policy = sorted(weight_codes - policy_codes)
    if policy_not_weight:
        failures.append("Section 301 exposure contains HS2017 codes absent from BACI weights")
    conversion_codes = set(conversion["source_hs6"])
    weight_not_conversion = sorted(weight_codes - conversion_codes)
    if weight_not_conversion:
        failures.append("BACI HS2017 weight codes are absent from the HS conversion")

    expected_years = set(range(int(config["years"]["start"]), int(config["years"]["end"]) + 1))
    expected_rows = len(product) * len(expected_years)
    full_grid_ok = bool(
        len(output) == expected_rows
        and set(output["analysis_hs6"]) == set(product["analysis_hs6"])
        and set(output["year"]) == expected_years
    )
    if not full_grid_ok:
        failures.append("output is not the complete product-by-year grid")

    bounded_columns = [
        "china_import_share_2017",
        "tariff_rate",
        "tariff_rate_china_weighted",
        "tariff_rate_total_import_weighted",
        "tariff_rate_max_source",
        "tariff_exposure",
    ]
    invalid_bounds: dict[str, int] = {}
    for column in bounded_columns:
        observed = pd.to_numeric(output[column], errors="coerce").dropna()
        invalid_bounds[column] = int((~observed.between(0, 1)).sum())
    if any(invalid_bounds.values()):
        failures.append("one or more treatment rates or shares are outside [0, 1]")

    identity_rows = output[
        output["china_import_share_2017"].notna() & output["tariff_exposure"].notna()
    ]
    identity_gap = (
        identity_rows["china_import_share_2017"] * identity_rows["tariff_rate"]
        - identity_rows["tariff_exposure"]
    ).abs()
    max_identity_gap = float(identity_gap.max()) if len(identity_gap) else 0.0
    if max_identity_gap > float(config["validation"]["tolerance_rate"]):
        failures.append("tariff_exposure does not equal aggregate China share times aggregate tariff rate")

    pre = output[output["year"] < 2018]
    pre_policy_zero = bool(
        (~pre["tariffed_product"]).all()
        and (pre["tariff_rate"].fillna(0) == 0).all()
        and (pre["tariff_exposure"].fillna(0) == 0).all()
    )
    if not pre_policy_zero:
        failures.append("pre-2018 rows contain positive Section 301 treatment")

    source_year = source.groupby("year", as_index=False).agg(
        source_total_import=("source_total_us_import_value_2017", "sum"),
        source_china_import=("source_china_import_value_2017", "sum"),
        source_exposure_numerator=("source_exposure_numerator", "sum"),
    )
    output_reconciliation = output.groupby("year", as_index=False).agg(
        output_total_import=("total_us_import_value_2017", "sum"),
        output_china_import=("china_import_value_2017", "sum"),
    )
    output_numerator = output.assign(
        reconstructed_numerator=(
            output["tariff_exposure"].fillna(0)
            * output["total_us_import_value_2017"].fillna(0)
        )
    ).groupby("year", as_index=False)["reconstructed_numerator"].sum()
    reconciliation = source_year.merge(output_reconciliation, on="year").merge(
        output_numerator, on="year"
    )
    reconciliation["total_import_gap"] = (
        reconciliation["source_total_import"] - reconciliation["output_total_import"]
    )
    reconciliation["china_import_gap"] = (
        reconciliation["source_china_import"] - reconciliation["output_china_import"]
    )
    reconciliation["exposure_numerator_gap"] = (
        reconciliation["source_exposure_numerator"]
        - reconciliation["reconstructed_numerator"]
    )
    max_reconciliation_gap = float(
        reconciliation[
            ["total_import_gap", "china_import_gap", "exposure_numerator_gap"]
        ].abs().to_numpy().max()
    )
    if max_reconciliation_gap > float(config["validation"]["tolerance_usd"]):
        failures.append("HS2017-to-analysis aggregation fails value/numerator reconciliation")

    observed_policy = source[source["policy_source_observed"]].copy()
    policy_share_gap = (
        observed_policy["policy_china_import_share_2017"]
        - observed_policy["source_china_import_share_2017"]
    ).abs()
    max_policy_share_gap = float(policy_share_gap.max()) if len(policy_share_gap) else 0.0
    if max_policy_share_gap > float(config["validation"]["tolerance_rate"]):
        failures.append("policy exposure share differs from the configured BACI HS2017 weights")
    policy_exposure_gap = (
        observed_policy["policy_tariff_exposure"]
        - observed_policy["source_tariff_rate"]
        * observed_policy["source_china_import_share_2017"]
    ).abs()
    max_policy_exposure_gap = float(policy_exposure_gap.max()) if len(policy_exposure_gap) else 0.0
    if max_policy_exposure_gap > float(config["validation"]["tolerance_rate"]):
        failures.append("source policy exposure identity fails")

    flags_ok = bool(
        (~output["historical_exclusions_applied"]).all()
        and (~output["four_year_review_2024_included"]).all()
        and (output["treatment_concept"] == "gross_statutory_initial_actions").all()
    )
    if not flags_ok:
        failures.append("gross statutory interpretation flags are inconsistent")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": hash_checks,
        "policy_input_row_count": len(policy),
        "policy_input_unique_hs17_count": len(policy_codes),
        "policy_duplicate_key_count": policy_duplicate_keys,
        "weight_input_row_count": len(weights),
        "weight_duplicate_key_count": weight_duplicate_keys,
        "policy_hs17_not_in_weight_codes": policy_not_weight,
        "weight_hs17_not_in_policy_count": len(weight_not_policy),
        "weight_hs17_not_in_policy_codes": weight_not_policy,
        "weight_hs17_not_in_conversion_codes": weight_not_conversion,
        "source_panel_row_count": len(source),
        "output_row_count": len(output),
        "expected_output_row_count": expected_rows,
        "output_duplicate_key_count": output_duplicate_keys,
        "full_product_year_grid_check_pass": full_grid_ok,
        "invalid_bound_counts": invalid_bounds,
        "max_exposure_identity_gap": max_identity_gap,
        "pre_2018_treatment_zero_check_pass": pre_policy_zero,
        "max_reconciliation_gap_usd": max_reconciliation_gap,
        "annual_reconciliation": reconciliation.to_dict(orient="records"),
        "max_policy_share_gap": max_policy_share_gap,
        "max_policy_exposure_identity_gap": max_policy_exposure_gap,
        "interpretation_flags_check_pass": flags_ok,
        "policy_mapping_status_counts": output["policy_mapping_status"].value_counts().sort_index().to_dict(),
        "tariffed_analysis_product_counts_by_year": (
            output.groupby("year")["tariffed_product"].sum().astype(int).to_dict()
        ),
        "analysis_codes_with_multiple_hs17_sources": int(
            output.loc[output["year"] == min(expected_years), "source_hs17_code_count"].gt(1).sum()
        ),
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Product Treatment Panel Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Output rows: `{validation['output_row_count']}`",
        "",
        "## Required checks",
        "",
        f"- Configured input SHA256 checks: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- Unique `analysis_hs6 × year`: `{'yes' if validation['output_duplicate_key_count'] == 0 else 'no'}`",
        f"- Complete product-year grid: `{'yes' if validation['full_product_year_grid_check_pass'] else 'no'}`",
        f"- All treatment rates and shares within [0, 1]: `{'yes' if not any(validation['invalid_bound_counts'].values()) else 'no'}`",
        f"- Pre-2018 treatment is zero: `{'yes' if validation['pre_2018_treatment_zero_check_pass'] else 'no'}`",
        f"- Weighted imports and exposure numerator reconcile: `{'yes' if validation['max_reconciliation_gap_usd'] <= 0.01 else 'no'}`",
        f"- Gross statutory interpretation flags are fixed: `{'yes' if validation['interpretation_flags_check_pass'] else 'no'}`",
        "",
        "## Source and mapping coverage",
        "",
        f"- Section 301 source rows: `{validation['policy_input_row_count']}` across `{validation['policy_input_unique_hs17_count']}` HS2017 codes.",
        f"- Complete BACI HS2017 weight universe: `{validation['weight_input_row_count']}` codes.",
        f"- BACI weight codes absent from the legal exposure panel: `{validation['weight_hs17_not_in_policy_count']}`; these receive explicit not-listed rate zero before aggregation.",
        f"- Analysis products receiving multiple HS2017 source codes: `{validation['analysis_codes_with_multiple_hs17_sources']}`; their rates use documented import weights.",
        "",
        "## Tariffed analysis products by year",
        "",
        "| Year | Tariffed analysis HS6 |",
        "|---:|---:|",
    ]
    for year, count in validation["tariffed_analysis_product_counts_by_year"].items():
        lines.append(f"| {year} | {count} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The panel measures gross statutory initial-action exposure, not realized duties. Historical exclusions are not applied, and the 2024 four-year-review changes remain a separate extension. When several HS2017 codes map to one HS2012/CEPII product, the aggregate China share is recomputed from import values and the tariff rate is China-import weighted; this preserves the exposure numerator and prevents many-to-one value inflation. Products without a 2017 import denominator retain missing share/exposure rather than a fabricated zero share.",
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
    parser = argparse.ArgumentParser(description="Build the M2.1 Section 301 product-treatment panel.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/harmonized/product_treatment_hs6_year.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/product_treatment_panel_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/product_treatment_panel_validation.md"),
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

    config = load_yaml(project_root / "configs/product_treatment_rules.yaml")
    policy, weights, conversion, product = load_inputs(project_root, config)
    source = source_panel(policy, weights, conversion, config)
    aggregate = aggregate_to_analysis(source)
    output = complete_product_grid(aggregate, product, config)
    validation = validate(
        project_root, config, policy, weights, conversion, product, source, output
    )
    table = write_parquet(output, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "treatment_version": config["version"],
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
                "tariffed_counts": validation["tariffed_analysis_product_counts_by_year"],
                "max_reconciliation_gap_usd": validation["max_reconciliation_gap_usd"],
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
