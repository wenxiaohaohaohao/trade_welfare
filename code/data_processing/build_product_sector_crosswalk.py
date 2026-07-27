from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, normalize_hs6, read_simple_xlsx_sheet, sha256


STRING_NA = {"", "n/a", "nan", "none", "null"}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text.casefold() in STRING_NA else text


def unique_join(values: pd.Series, separator: str = " | ") -> str | None:
    cleaned = sorted({text for value in values for text in [clean_text(value)] if text})
    return separator.join(cleaned) if cleaned else None


def single_value(values: pd.Series) -> str | None:
    cleaned = sorted({text for value in values for text in [clean_text(value)] if text})
    return cleaned[0] if len(cleaned) == 1 else None


def safe_value_counts(values: pd.Series) -> dict[str, int]:
    counts = values.value_counts(dropna=False).sort_index()
    return {
        "<NA>" if pd.isna(label) else str(label): int(count)
        for label, count in counts.items()
    }


def normalize_isic(value: Any) -> str:
    text = clean_text(value)
    if text is None or not text.isdigit() or len(text) not in {2, 3, 4}:
        raise ValueError(f"Invalid ISIC Rev.4 code {value!r}")
    return text


def read_official_hs12(path: Path, sheet: str) -> pd.DataFrame:
    rows = read_simple_xlsx_sheet(path, sheet)
    header = [str(value or "").strip() for value in rows[0]]
    required = {
        "HS4",
        "HS4Desc",
        "HS6",
        "HS6Desc",
        "BEC5Code1",
        "BEC5Code2",
        "BEC5Category",
        "BEC5EndUse",
        "BEC5Processing",
        "BEC5Specification",
        "BEC5Durability",
        "i4",
        "i4Desc",
        "BEC4Code",
        "BEC4ENDUSE",
    }
    missing = sorted(required - set(header))
    if missing:
        raise ValueError(f"Official workbook is missing required fields: {missing}")
    records = [
        dict(zip(header, row + [None] * (len(header) - len(row))))
        for row in rows[1:]
        if any(value is not None for value in row)
    ]
    frame = pd.DataFrame(records)
    frame["official_hs2012"] = frame["HS6"].map(normalize_hs6)
    frame["hs2"] = frame["official_hs2012"].str[:2]
    frame["hs4"] = frame["official_hs2012"].str[:4]
    frame["isic_rev4"] = frame["i4"].map(normalize_isic)
    frame["isic_rev4_division"] = frame["isic_rev4"].str[:2]
    return frame


def classify_product(row: pd.Series, product_config: dict[str, Any], sector_config: dict[str, Any]) -> dict[str, Any]:
    hs2 = row["hs2"]
    hs4 = row["hs4"]
    division = row["isic_rev4_division"]
    rules = product_config["product_rules"]
    canonical = sector_config["canonical_isic_rev4_rules"]

    if hs4 in set(rules["crude_oil"]["hs4"]):
        return {
            "analysis_sector": None,
            "sector_status": "first_round_excluded",
            "sector_rule": "hs4_crude_oil",
            "first_round_exclusion": "crude_oil",
        }
    if hs2 in set(rules["precious_metals"]["hs2"]):
        return {
            "analysis_sector": None,
            "sector_status": "first_round_excluded",
            "sector_rule": "hs2_precious_metals",
            "first_round_exclusion": "precious_metals",
        }
    if division in set(rules["agricultural_bulk_goods"]["isic_rev4_divisions"]):
        return {
            "analysis_sector": None,
            "sector_status": "first_round_excluded",
            "sector_rule": "isic_primary_agriculture",
            "first_round_exclusion": "agricultural_bulk_goods",
        }
    if division in set(rules["basic_commodities"]["isic_rev4_divisions"]):
        return {
            "analysis_sector": None,
            "sector_status": "first_round_excluded",
            "sector_rule": "isic_extractive_or_basic_metals",
            "first_round_exclusion": "basic_commodities",
        }
    medical = rules["medical_devices"]
    if medical["hs4_start"] <= hs4 <= medical["hs4_end"]:
        return {
            "analysis_sector": "medical_devices",
            "sector_status": "priority_sector",
            "sector_rule": "hs4_medical_devices_9018_9022",
            "first_round_exclusion": None,
        }
    for sector in ["electronics", "electrical_equipment", "machinery", "autos", "textiles_apparel"]:
        if division in set(canonical[sector]["divisions"]):
            return {
                "analysis_sector": sector,
                "sector_status": "priority_sector",
                "sector_rule": f"isic_rev4_{sector}",
                "first_round_exclusion": None,
            }
    start, end = canonical["other_manufacturing"]["division_range"]
    if start <= division <= end:
        return {
            "analysis_sector": sector_config["catch_all_sector"],
            "sector_status": "other_manufacturing",
            "sector_rule": "isic_rev4_other_manufacturing",
            "first_round_exclusion": None,
        }
    return {
        "analysis_sector": None,
        "sector_status": "outside_manufacturing",
        "sector_rule": "isic_rev4_outside_manufacturing",
        "first_round_exclusion": None,
    }


def bec_labels(group: pd.DataFrame, separator: str) -> list[str]:
    labels: set[str] = set()
    for value in group["BEC5EndUse"]:
        text = clean_text(value)
        if text:
            labels.update(part.strip() for part in text.split(separator) if part.strip())
    return sorted(labels)


def build_crosswalk(project_root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    sector_config = load_yaml(project_root / config["sector_scope_config"])
    source = project_root / config["official_source"]["path"]
    official = read_official_hs12(source, config["official_source"]["sheet"])
    official_duplicate_codes = int(official.duplicated("official_hs2012").sum())

    collapse_lookup = {
        normalize_hs6(code): normalize_hs6(analysis_code)
        for analysis_code, details in config["analysis_code_collapses"].items()
        for code in details["official_hs2012_codes"]
    }
    official["analysis_hs6"] = official["official_hs2012"].map(
        lambda code: collapse_lookup.get(code, code)
    )
    classifications = official.apply(
        lambda row: classify_product(row, config, sector_config), axis=1, result_type="expand"
    )
    official = pd.concat([official, classifications], axis=1)

    allowed_end_uses = set(config["bec_rules"]["allowed_end_uses"])
    output_records: list[dict[str, Any]] = []
    for analysis_hs6, group in official.groupby("analysis_hs6", sort=True):
        sector_values = sorted(set(group["analysis_sector"].dropna()))
        status_values = sorted(set(group["sector_status"]))
        rule_values = sorted(set(group["sector_rule"]))
        exclusion_values = sorted(set(group["first_round_exclusion"].dropna()))
        if len(sector_values) > 1 or len(status_values) != 1 or len(rule_values) != 1 or len(exclusion_values) > 1:
            raise ValueError(f"Analysis-code collapse creates inconsistent sector assignments for {analysis_hs6}")

        labels = bec_labels(group, config["bec_rules"]["composite_separator"])
        invalid_labels = sorted(set(labels) - allowed_end_uses)
        if invalid_labels:
            raise ValueError(f"Unexpected BEC5 end-use labels for {analysis_hs6}: {invalid_labels}")
        all_bec_codes = sorted(
            {
                text
                for column in ["BEC5Code1", "BEC5Code2"]
                for value in group[column]
                for text in [clean_text(value)]
                if text
            }
        )
        collapsed = len(group) > 1
        if not labels:
            bec_status = "official_not_applicable"
        elif collapsed:
            bec_status = "cepii_collapse_multi_label_no_weights"
        elif len(labels) > 1:
            bec_status = "official_multi_label_no_weights"
        else:
            bec_status = "official_single_label"

        record = {
            "analysis_revision": config["analysis_revision"],
            "analysis_hs6": analysis_hs6,
            "hs2": analysis_hs6[:2],
            "hs4": analysis_hs6[:4],
            "product_description": single_value(group["HS6Desc"]),
            "official_hs2012_codes": unique_join(group["official_hs2012"], "|"),
            "official_hs2012_code_count": int(group["official_hs2012"].nunique()),
            "product_mapping_status": "cepii_collapsed_official_codes" if collapsed else "official_exact",
            "isic_rev4_codes": unique_join(group["isic_rev4"], "|"),
            "isic_rev4_divisions": unique_join(group["isic_rev4_division"], "|"),
            "isic_rev4_descriptions": unique_join(group["i4Desc"], " || "),
            "analysis_sector": sector_values[0] if sector_values else None,
            "sector_status": status_values[0],
            "sector_rule": rule_values[0],
            "first_round_exclusion": exclusion_values[0] if exclusion_values else None,
            "is_analysis_sector_eligible": bool(sector_values),
            "sector_mapping_weight": 1.0 if sector_values else None,
            "bec5_code_primary": single_value(group["BEC5Code1"]),
            "bec5_code_secondary": single_value(group["BEC5Code2"]),
            "bec5_codes_all": "|".join(all_bec_codes) if all_bec_codes else None,
            "bec5_categories_all": unique_join(group["BEC5Category"], " || "),
            "bec5_end_use_official": single_value(group["BEC5EndUse"]),
            "bec5_end_use_labels": "|".join(labels) if labels else None,
            "bec5_end_use_count": len(labels),
            "bec_is_intermediate": "INT" in labels,
            "bec_is_capital": "CAP" in labels,
            "bec_is_consumption": "CONS" in labels,
            "bec_end_use_ambiguous": len(labels) > 1,
            "bec_allocation_weight": 1.0 if len(labels) == 1 else None,
            "bec_mapping_status": bec_status,
            "bec5_processing_all": unique_join(group["BEC5Processing"], "|"),
            "bec5_specification_all": unique_join(group["BEC5Specification"], "|"),
            "bec5_durability_all": unique_join(group["BEC5Durability"], "|"),
            "bec4_codes_all": unique_join(group["BEC4Code"], "|"),
            "bec4_end_use_all": unique_join(group["BEC4ENDUSE"], "|"),
            "mapping_source": "UNSD_HS2012_HS2017_BEC5_ISIC4",
            "source_sha256": config["official_source"]["sha256"],
            "mapping_version": config["version"],
        }
        output_records.append(record)

    output = pd.DataFrame(output_records)
    baci_reference = pd.read_csv(
        project_root / config["product_universe"]["reference_path"], dtype="string"
    )
    baci_reference["analysis_hs6"] = baci_reference["code"].map(normalize_hs6)
    baci_descriptions = dict(zip(baci_reference["analysis_hs6"], baci_reference["description"]))
    residual_records: list[dict[str, Any]] = []
    for code, details in config["product_universe"]["residual_codes"].items():
        code = normalize_hs6(code)
        residual_records.append(
            {
                "analysis_revision": config["analysis_revision"],
                "analysis_hs6": code,
                "hs2": code[:2],
                "hs4": code[:4],
                "product_description": baci_descriptions.get(code),
                "official_hs2012_codes": None,
                "official_hs2012_code_count": 0,
                "product_mapping_status": details["status"],
                "isic_rev4_codes": None,
                "isic_rev4_divisions": None,
                "isic_rev4_descriptions": None,
                "analysis_sector": None,
                "sector_status": "residual_product",
                "sector_rule": "configured_residual_product",
                "first_round_exclusion": None,
                "is_analysis_sector_eligible": False,
                "sector_mapping_weight": None,
                "bec5_code_primary": None,
                "bec5_code_secondary": None,
                "bec5_codes_all": None,
                "bec5_categories_all": None,
                "bec5_end_use_official": None,
                "bec5_end_use_labels": None,
                "bec5_end_use_count": 0,
                "bec_is_intermediate": False,
                "bec_is_capital": False,
                "bec_is_consumption": False,
                "bec_end_use_ambiguous": False,
                "bec_allocation_weight": None,
                "bec_mapping_status": "residual_not_mapped",
                "bec5_processing_all": None,
                "bec5_specification_all": None,
                "bec5_durability_all": None,
                "bec4_codes_all": None,
                "bec4_end_use_all": None,
                "mapping_source": "configured_baci_residual",
                "source_sha256": config["official_source"]["sha256"],
                "mapping_version": config["version"],
            }
        )
    output = pd.concat([output, pd.DataFrame(residual_records)], ignore_index=True)
    output["product_description"] = output.apply(
        lambda row: baci_descriptions.get(row["analysis_hs6"], row["product_description"]), axis=1
    )

    string_columns = [
        column
        for column in output.columns
        if column
        not in {
            "official_hs2012_code_count",
            "is_analysis_sector_eligible",
            "sector_mapping_weight",
            "bec5_end_use_count",
            "bec_is_intermediate",
            "bec_is_capital",
            "bec_is_consumption",
            "bec_end_use_ambiguous",
            "bec_allocation_weight",
        }
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["official_hs2012_code_count"] = output["official_hs2012_code_count"].astype("int16")
    output["bec5_end_use_count"] = output["bec5_end_use_count"].astype("int8")
    for column in [
        "is_analysis_sector_eligible",
        "bec_is_intermediate",
        "bec_is_capital",
        "bec_is_consumption",
        "bec_end_use_ambiguous",
    ]:
        output[column] = output[column].astype("bool")
    output = output.sort_values("analysis_hs6").reset_index(drop=True)
    metadata = {
        "official_workbook_row_count": len(official),
        "official_duplicate_hs6_count": official_duplicate_codes,
        "official_code_set": set(official["official_hs2012"]),
        "baci_code_set": set(baci_reference["analysis_hs6"]),
        "collapse_source_codes": set(collapse_lookup),
        "collapse_target_codes": set(collapse_lookup.values()),
        "sector_config": sector_config,
    }
    return output, metadata


def baci_value_totals(path: Path) -> pd.Series:
    totals = pd.Series(dtype="float64")
    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(columns=["hs6", "trade_value_usd"], batch_size=1_000_000):
        frame = batch.to_pandas()
        frame["hs6"] = frame["hs6"].astype("string").str.zfill(6)
        grouped = frame.groupby("hs6", observed=True)["trade_value_usd"].sum()
        totals = totals.add(grouped, fill_value=0.0)
    return totals


def validate_crosswalk(
    project_root: Path,
    config: dict[str, Any],
    output: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    source_path = project_root / config["official_source"]["path"]
    source_hash_ok = source_path.exists() and sha256(source_path) == config["official_source"]["sha256"]
    if not source_hash_ok:
        failures.append("official UNSD HS-BEC-ISIC workbook fails its configured SHA256 check")

    duplicate_keys = int(output.duplicated("analysis_hs6").sum())
    if duplicate_keys:
        failures.append(f"product-sector crosswalk has {duplicate_keys} duplicate analysis_hs6 keys")
    invalid_codes = int((~output["analysis_hs6"].str.fullmatch(r"\d{6}")).sum())
    if invalid_codes:
        failures.append(f"product-sector crosswalk has {invalid_codes} invalid HS6 codes")

    baci_codes = metadata["baci_code_set"]
    output_codes = set(output["analysis_hs6"])
    missing_baci_codes = sorted(baci_codes - output_codes)
    extra_output_codes = sorted(output_codes - baci_codes)
    if missing_baci_codes or extra_output_codes:
        failures.append("output product universe differs from the configured BACI HS2012/CEPII reference")
    expected_count = int(config["product_universe"]["expected_code_count"])
    if len(output) != expected_count:
        failures.append(f"output has {len(output)} rows; expected {expected_count}")

    expected_official_not_baci = metadata["collapse_source_codes"]
    actual_official_not_baci = metadata["official_code_set"] - baci_codes
    expected_baci_not_official = metadata["collapse_target_codes"] | {
        normalize_hs6(code) for code in config["product_universe"]["residual_codes"]
    }
    actual_baci_not_official = baci_codes - metadata["official_code_set"]
    source_universe_difference_ok = (
        actual_official_not_baci == expected_official_not_baci
        and actual_baci_not_official == expected_baci_not_official
    )
    if not source_universe_difference_ok:
        failures.append("UNSD-versus-BACI code differences exceed the configured CEPII collapse and residual code")

    sector_config = metadata["sector_config"]
    expected_priority = set(sector_config["priority_sectors"])
    observed_priority = set(output.loc[output["sector_status"] == "priority_sector", "analysis_sector"].dropna())
    priority_sector_set_ok = expected_priority == observed_priority
    if not priority_sector_set_ok:
        failures.append("observed priority-sector set differs from sector_scope.yaml")
    eligibility_consistent = bool(
        (
            output["is_analysis_sector_eligible"]
            == output["analysis_sector"].notna()
        ).all()
    )
    if not eligibility_consistent:
        failures.append("analysis-sector eligibility flag disagrees with analysis_sector missingness")
    sector_weights_consistent = bool(
        (output.loc[output["is_analysis_sector_eligible"], "sector_mapping_weight"] == 1.0).all()
        and output.loc[~output["is_analysis_sector_eligible"], "sector_mapping_weight"].isna().all()
    )
    if not sector_weights_consistent:
        failures.append("sector mapping weights are not one for eligible products and null otherwise")

    ambiguous_weight_count = int(
        output.loc[output["bec_end_use_ambiguous"], "bec_allocation_weight"].notna().sum()
    )
    if ambiguous_weight_count:
        failures.append("ambiguous BEC end-use rows received an unvalidated numeric weight")
    single_weight_consistent = bool(
        (output.loc[output["bec5_end_use_count"] == 1, "bec_allocation_weight"] == 1.0).all()
    )
    if not single_weight_consistent:
        failures.append("one or more single-label BEC rows lack weight 1")
    expected_na = set(config["bec_rules"]["expected_official_not_applicable_hs2012"])
    actual_na = set(
        output.loc[output["bec_mapping_status"] == "official_not_applicable", "analysis_hs6"]
    )
    bec_na_codes_ok = expected_na == actual_na
    if not bec_na_codes_ok:
        failures.append("official BEC-not-applicable code set differs from the configured expectation")

    collapse_target = next(iter(metadata["collapse_target_codes"]))
    collapse_row = output.loc[output["analysis_hs6"] == collapse_target]
    collapse_ok = bool(
        len(collapse_row) == 1
        and collapse_row.iloc[0]["official_hs2012_code_count"] == len(metadata["collapse_source_codes"])
        and collapse_row.iloc[0]["product_mapping_status"] == "cepii_collapsed_official_codes"
        and collapse_row.iloc[0]["bec_end_use_ambiguous"]
        and pd.isna(collapse_row.iloc[0]["bec_allocation_weight"])
    )
    if not collapse_ok:
        failures.append("CEPII 271000 collapse does not preserve the required sector/BEC ambiguity rules")

    residual_codes = {normalize_hs6(code) for code in config["product_universe"]["residual_codes"]}
    residual = output[output["analysis_hs6"].isin(residual_codes)]
    residual_rules_ok = bool(
        len(residual) == len(residual_codes)
        and (residual["sector_status"] == "residual_product").all()
        and residual["analysis_sector"].isna().all()
        and (residual["bec_mapping_status"] == "residual_not_mapped").all()
    )
    if not residual_rules_ok:
        failures.append("configured residual product codes received a sector or BEC mapping")

    totals = baci_value_totals(project_root / "data/interim/trade/baci_hs6_panel.parquet")
    total_value = float(totals.sum())
    explicit_status_value = float(totals[totals.index.isin(output_codes)].sum())
    official_isic_codes = set(output.loc[output["isic_rev4_codes"].notna(), "analysis_hs6"])
    official_bec_codes = set(output.loc[output["bec5_end_use_count"] > 0, "analysis_hs6"])
    eligible_sector_codes = set(output.loc[output["is_analysis_sector_eligible"], "analysis_hs6"])
    explicit_status_value_coverage = explicit_status_value / total_value if total_value else None
    official_isic_value_coverage = float(totals[totals.index.isin(official_isic_codes)].sum()) / total_value
    official_bec_value_coverage = float(totals[totals.index.isin(official_bec_codes)].sum()) / total_value
    analysis_sector_value_share = float(totals[totals.index.isin(eligible_sector_codes)].sum()) / total_value
    thresholds = config["validation_thresholds"]
    if explicit_status_value_coverage < float(thresholds["explicit_status_code_coverage"]):
        failures.append("explicit product-status value coverage is below 100 percent")
    if official_isic_value_coverage < float(thresholds["official_isic_value_coverage_minimum"]):
        failures.append("official ISIC value coverage is below the configured minimum")
    if official_bec_value_coverage < float(thresholds["official_bec_value_coverage_minimum"]):
        failures.append("official BEC value coverage is below the configured minimum")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "source_sha256_check_pass": source_hash_ok,
        "official_workbook_row_count": metadata["official_workbook_row_count"],
        "official_duplicate_hs6_count": metadata["official_duplicate_hs6_count"],
        "output_row_count": len(output),
        "duplicate_analysis_hs6_count": duplicate_keys,
        "invalid_analysis_hs6_count": invalid_codes,
        "missing_baci_codes": missing_baci_codes,
        "extra_output_codes": extra_output_codes,
        "source_universe_difference_check_pass": source_universe_difference_ok,
        "product_mapping_status_counts": safe_value_counts(output["product_mapping_status"]),
        "sector_status_counts": safe_value_counts(output["sector_status"]),
        "analysis_sector_counts": safe_value_counts(output["analysis_sector"]),
        "first_round_exclusion_counts": safe_value_counts(output["first_round_exclusion"]),
        "priority_sector_set_check_pass": priority_sector_set_ok,
        "eligibility_flag_check_pass": eligibility_consistent,
        "sector_mapping_weight_check_pass": sector_weights_consistent,
        "bec_mapping_status_counts": safe_value_counts(output["bec_mapping_status"]),
        "bec_end_use_count_distribution": safe_value_counts(output["bec5_end_use_count"]),
        "ambiguous_bec_numeric_weight_count": ambiguous_weight_count,
        "single_bec_weight_check_pass": single_weight_consistent,
        "bec_not_applicable_code_check_pass": bec_na_codes_ok,
        "cepii_271000_collapse_check_pass": collapse_ok,
        "residual_product_rule_check_pass": residual_rules_ok,
        "baci_total_trade_value_usd": total_value,
        "explicit_status_value_coverage_rate": explicit_status_value_coverage,
        "official_isic_value_coverage_rate": official_isic_value_coverage,
        "official_bec_value_coverage_rate": official_bec_value_coverage,
        "analysis_sector_eligible_value_share": analysis_sector_value_share,
        "coverage_thresholds_pass": (
            explicit_status_value_coverage >= float(thresholds["explicit_status_code_coverage"])
            and official_isic_value_coverage >= float(thresholds["official_isic_value_coverage_minimum"])
            and official_bec_value_coverage >= float(thresholds["official_bec_value_coverage_minimum"])
        ),
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Product-Sector and BEC Crosswalk Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Product rows: `{validation['output_row_count']}`",
        "",
        "## Required checks",
        "",
        f"- Official source SHA256 matches: `{'yes' if validation['source_sha256_check_pass'] else 'no'}`",
        f"- Unique `analysis_hs6`: `{'yes' if validation['duplicate_analysis_hs6_count'] == 0 else 'no'}`",
        f"- BACI product universe fully covered with explicit status: `{'yes' if not validation['missing_baci_codes'] and not validation['extra_output_codes'] else 'no'}`",
        f"- Priority-sector set matches `sector_scope.yaml`: `{'yes' if validation['priority_sector_set_check_pass'] else 'no'}`",
        f"- Eligible sector weights equal 1 and excluded weights are null: `{'yes' if validation['sector_mapping_weight_check_pass'] else 'no'}`",
        f"- Ambiguous BEC rows kept without numeric allocation weights: `{'yes' if validation['ambiguous_bec_numeric_weight_count'] == 0 else 'no'}`",
        f"- CEPII `271000` collapse preserves BEC ambiguity: `{'yes' if validation['cepii_271000_collapse_check_pass'] else 'no'}`",
        f"- BACI `999999` remains an unmapped residual: `{'yes' if validation['residual_product_rule_check_pass'] else 'no'}`",
        "",
        "## Coverage",
        "",
        "| Measure | Rate | Interpretation |",
        "|---|---:|---|",
        f"| Explicit product status | {validation['explicit_status_value_coverage_rate']:.6%} | Every BACI product is mapped, excluded, outside manufacturing, or identified as residual. |",
        f"| Official ISIC classification | {validation['official_isic_value_coverage_rate']:.6%} | The only non-official residual is BACI `999999`. |",
        f"| Official BEC end use | {validation['official_bec_value_coverage_rate']:.6%} | Excludes official `n/a` monetary-gold/coin codes and BACI `999999`. |",
        f"| First-round analysis-sector share | {validation['analysis_sector_eligible_value_share']:.6%} | Sample-scope share, not an unmapped-data rate. |",
        "",
        "## Sector counts",
        "",
        "| Analysis sector | HS6 rows |",
        "|---|---:|",
    ]
    for sector, count in validation["analysis_sector_counts"].items():
        label = "<excluded or outside scope>" if sector in {None, "<NA>"} else str(sector)
        lines.append(f"| `{label}` | {count} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "`analysis_sector` and BEC end use are separate dimensions. Sector assignment is one-to-one and has weight 1 only for included manufacturing products. BEC composite labels retain all official uses, but they receive no allocation weights; using those labels to split trade values requires a later value-based rule. CEPII `271000` is sector-consistent across its five official HS2012 components but has multiple BEC uses, so it remains explicitly ambiguous for end-use analysis.",
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
    parser = argparse.ArgumentParser(description="Build the HS2012/CEPII product-sector and BEC crosswalk.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/concordances/product_sector_crosswalk.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/product_sector_crosswalk_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/product_sector_crosswalk_validation.md"),
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

    config = load_yaml(project_root / "configs/product_sector_rules.yaml")
    crosswalk, metadata = build_crosswalk(project_root, config)
    validation = validate_crosswalk(project_root, config, crosswalk, metadata)
    table = write_parquet(crosswalk, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "mapping_version": config["version"],
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
                "official_isic_value_coverage": validation["official_isic_value_coverage_rate"],
                "official_bec_value_coverage": validation["official_bec_value_coverage_rate"],
                "analysis_sector_value_share": validation["analysis_sector_eligible_value_share"],
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
