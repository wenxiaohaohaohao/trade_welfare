from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


PRODUCT_FIELDS = {
    "analysis_sector": "canonical_analysis_sector",
    "sector_status": "canonical_sector_status",
    "first_round_exclusion": "canonical_first_round_exclusion",
    "is_analysis_sector_eligible": "canonical_is_analysis_sector_eligible",
    "product_mapping_version": "canonical_product_mapping_version",
}

POLICY_FIELDS = [
    "total_us_import_value_2017",
    "china_import_value_2017",
    "tariff_rate_china_weighted",
    "tariffed_product",
    "policy_mapping_status",
    "treatment_concept",
    "historical_exclusions_applied",
    "four_year_review_2024_included",
    "review_2024_treatment",
    "treatment_version",
]


def equal_with_missing(left: pd.Series, right: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(left.dtype) and pd.api.types.is_bool_dtype(right.dtype):
        return left.astype("boolean").fillna(False) == right.astype("boolean").fillna(False)
    return left.astype("string").fillna("<NA>") == right.astype("string").fillna("<NA>")


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    usable = denominator.notna() & (denominator != 0)
    result.loc[usable] = numerator.loc[usable] / denominator.loc[usable]
    return result


def prepare_join(
    trade: pd.DataFrame,
    crosswalk: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    crosswalk_fields = [
        "analysis_hs6",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "is_analysis_sector_eligible",
        "sector_mapping_weight",
        "mapping_version",
    ]
    canonical = crosswalk[crosswalk_fields].rename(
        columns={
            "analysis_sector": "canonical_analysis_sector",
            "sector_status": "canonical_sector_status",
            "first_round_exclusion": "canonical_first_round_exclusion",
            "is_analysis_sector_eligible": "canonical_is_analysis_sector_eligible",
            "sector_mapping_weight": "canonical_sector_mapping_weight",
            "mapping_version": "canonical_product_mapping_version",
        }
    )
    joined = trade.merge(
        canonical,
        on=config["join"]["keys"],
        how=config["join"]["type"],
        validate=config["join"]["cardinality"],
        indicator=True,
    )
    unmatched_rows = int((joined["_merge"] != "both").sum())
    joined = joined.drop(columns="_merge")

    mismatch_counts: dict[str, int] = {}
    for embedded, canonical_name in PRODUCT_FIELDS.items():
        mismatch_counts[embedded] = int(
            (~equal_with_missing(joined[embedded], joined[canonical_name])).sum()
        )

    eligible = joined["canonical_is_analysis_sector_eligible"].fillna(False)
    correct_weight = joined["canonical_sector_mapping_weight"].eq(
        float(config["eligibility"]["required_weight"])
    )
    joined["m3_analysis_eligible"] = eligible & correct_weight

    eligible_nonunit_weight_count = int((eligible & ~correct_weight).sum())
    ineligible_nonnull_weight_count = int(
        (~eligible & joined["canonical_sector_mapping_weight"].notna()).sum()
    )
    context = {
        "unmatched_crosswalk_row_count": unmatched_rows,
        "embedded_product_field_mismatch_counts": mismatch_counts,
        "eligible_nonunit_weight_row_count": eligible_nonunit_weight_count,
        "ineligible_nonnull_weight_row_count": ineligible_nonnull_weight_count,
    }
    return joined, context


def verify_policy_replication(joined: pd.DataFrame) -> dict[str, Any]:
    replicated_fields = [
        *POLICY_FIELDS,
        "canonical_analysis_sector",
        "canonical_sector_status",
        "canonical_is_analysis_sector_eligible",
        "canonical_sector_mapping_weight",
    ]
    unique_counts = joined.groupby(["analysis_hs6", "year"], dropna=False)[
        replicated_fields
    ].nunique(dropna=False)
    inconsistent_by_field = {
        field: int((unique_counts[field] > 1).sum()) for field in replicated_fields
    }
    inconsistent_keys = int((unique_counts > 1).any(axis=1).sum())
    return {
        "policy_replication_inconsistent_key_count": inconsistent_keys,
        "policy_replication_inconsistent_counts_by_field": inconsistent_by_field,
    }


def build_trade_sector(
    joined: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    eligible = joined.loc[joined["m3_analysis_eligible"]].copy()
    eligible["analysis_sector"] = eligible["canonical_analysis_sector"].astype("string")
    eligible["analysis_sector_status"] = eligible["canonical_sector_status"].astype("string")

    aggregation: dict[str, pd.NamedAgg] = {
        "connector_group": pd.NamedAgg(column="connector_group", aggfunc="first"),
        "connector_baci_code": pd.NamedAgg(column="connector_baci_code", aggfunc="first"),
        "connector_is_proxy": pd.NamedAgg(column="connector_is_proxy", aggfunc="max"),
        "analysis_sector_status": pd.NamedAgg(
            column="analysis_sector_status", aggfunc="first"
        ),
        "sector_eligible_product_count": pd.NamedAgg(
            column="analysis_hs6", aggfunc="nunique"
        ),
    }
    for details in config["trade_flows"].values():
        value_field = details["value_field"]
        row_count_field = details["source_row_count_field"]
        positive_field = details["positive_product_count_field"]
        zero_source_field = details["zero_source_product_count_field"]
        eligible[positive_field] = eligible[value_field].gt(0).astype("int32")
        eligible[zero_source_field] = eligible[row_count_field].eq(0).astype("int32")
        aggregation[value_field] = pd.NamedAgg(column=value_field, aggfunc="sum")
        aggregation[row_count_field] = pd.NamedAgg(column=row_count_field, aggfunc="sum")
        aggregation[positive_field] = pd.NamedAgg(column=positive_field, aggfunc="sum")
        aggregation[zero_source_field] = pd.NamedAgg(
            column=zero_source_field, aggfunc="sum"
        )

    keys = config["output"]["natural_key"]
    output = eligible.groupby(keys, as_index=False, sort=True).agg(**aggregation)

    coverage_keys = ["connector_iso3", "year"]
    excluded = joined.loc[~joined["m3_analysis_eligible"]].copy()
    coverage = excluded.groupby(coverage_keys, as_index=False, sort=True).agg(
        excluded_product_count=("analysis_hs6", "nunique")
    )
    all_grouped = joined.groupby(coverage_keys, sort=True)
    eligible_grouped = eligible.groupby(coverage_keys, sort=True)
    excluded_grouped = excluded.groupby(coverage_keys, sort=True)
    coverage_index = coverage.set_index(coverage_keys).index

    for details in config["trade_flows"].values():
        value_field = details["value_field"]
        excluded_field = details["excluded_value_field"]
        included_share_field = details["included_share_field"]
        full_values = all_grouped[value_field].sum().reindex(coverage_index)
        included_values = eligible_grouped[value_field].sum().reindex(coverage_index)
        excluded_values = excluded_grouped[value_field].sum().reindex(coverage_index)
        coverage[excluded_field] = excluded_values.to_numpy(dtype="float64")
        coverage[included_share_field] = safe_divide(
            included_values.reset_index(drop=True),
            full_values.reset_index(drop=True),
        ).to_numpy(dtype="float64")

    output = output.merge(
        coverage,
        on=coverage_keys,
        how="left",
        validate="many_to_one",
    )
    return output, eligible


def build_policy_sector(
    joined: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    product_year = (
        joined.sort_values(["connector_iso3", "analysis_hs6", "year"])
        .drop_duplicates(["analysis_hs6", "year"])
        .copy()
    )
    policy = product_year.loc[product_year["m3_analysis_eligible"]].copy()
    policy["analysis_sector"] = policy["canonical_analysis_sector"].astype("string")

    china_imports = policy["china_import_value_2017"].astype("float64")
    china_rate = policy["tariff_rate_china_weighted"].astype("float64")
    policy["policy_exposure_numerator_usd"] = china_imports * china_rate
    policy.loc[china_imports.eq(0), "policy_exposure_numerator_usd"] = 0.0
    policy["policy_denominator_observed"] = (
        policy["total_us_import_value_2017"].notna()
        & policy["total_us_import_value_2017"].gt(0)
    )
    policy["policy_zero_denominator"] = policy["policy_mapping_status"].eq(
        config["treatment"]["zero_denominator_status"]
    )
    policy["policy_no_hs17_mapping"] = policy["policy_mapping_status"].eq(
        config["treatment"]["no_mapping_status"]
    )
    policy["policy_missing_denominator"] = ~policy["policy_denominator_observed"]
    policy["tariffed_product_int"] = policy["tariffed_product"].astype("int32")
    policy["tariffed_china_import_value_2017"] = policy[
        "china_import_value_2017"
    ].where(policy["tariffed_product"], 0.0)
    policy["tariffed_total_us_import_value_2017"] = policy[
        "total_us_import_value_2017"
    ].where(policy["tariffed_product"], 0.0)

    grouped = policy.groupby(["analysis_sector", "year"], as_index=False, sort=True)
    output = grouped.agg(
        sector_total_us_import_value_2017=("total_us_import_value_2017", "sum"),
        sector_china_import_value_2017=("china_import_value_2017", "sum"),
        sector_tariff_exposure_numerator_usd=(
            "policy_exposure_numerator_usd",
            "sum",
        ),
        sector_treatment_product_count=("analysis_hs6", "nunique"),
        policy_denominator_observed_product_count=(
            "policy_denominator_observed",
            "sum",
        ),
        treatment_missing_denominator_product_count=(
            "policy_missing_denominator",
            "sum",
        ),
        treatment_zero_denominator_product_count=(
            "policy_zero_denominator",
            "sum",
        ),
        treatment_no_hs17_mapping_product_count=(
            "policy_no_hs17_mapping",
            "sum",
        ),
        tariffed_product_count=("tariffed_product_int", "sum"),
        tariffed_china_import_value_2017=(
            "tariffed_china_import_value_2017",
            "sum",
        ),
        tariffed_total_us_import_value_2017=(
            "tariffed_total_us_import_value_2017",
            "sum",
        ),
    )
    output["sector_tariff_rate_china_weighted"] = safe_divide(
        output["sector_tariff_exposure_numerator_usd"],
        output["sector_china_import_value_2017"],
    )
    output["sector_tariff_exposure"] = safe_divide(
        output["sector_tariff_exposure_numerator_usd"],
        output["sector_total_us_import_value_2017"],
    )
    output["sector_china_import_share_2017"] = safe_divide(
        output["sector_china_import_value_2017"],
        output["sector_total_us_import_value_2017"],
    )
    output["tariffed_product_share_count"] = safe_divide(
        output["tariffed_product_count"],
        output["sector_treatment_product_count"],
    )
    output["tariffed_product_share_china_value"] = safe_divide(
        output["tariffed_china_import_value_2017"],
        output["sector_china_import_value_2017"],
    )
    output["tariffed_product_share_us_value"] = safe_divide(
        output["tariffed_total_us_import_value_2017"],
        output["sector_total_us_import_value_2017"],
    )
    output["treatment_missing_denominator_product_share"] = safe_divide(
        output["treatment_missing_denominator_product_count"],
        output["sector_treatment_product_count"],
    )
    output["treatment_zero_denominator_product_share"] = safe_divide(
        output["treatment_zero_denominator_product_count"],
        output["sector_treatment_product_count"],
    )
    output["treatment_no_hs17_mapping_product_share"] = safe_divide(
        output["treatment_no_hs17_mapping_product_count"],
        output["sector_treatment_product_count"],
    )
    return output, policy


def finalize_output(
    trade_sector: pd.DataFrame,
    policy_sector: pd.DataFrame,
    joined: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    output = trade_sector.merge(
        policy_sector,
        on=["analysis_sector", "year"],
        how="left",
        validate="many_to_one",
    )
    metadata_fields = [
        "trade_value_unit",
        "treatment_concept",
        "historical_exclusions_applied",
        "four_year_review_2024_included",
        "review_2024_treatment",
        "treatment_version",
    ]
    metadata = {field: joined[field].drop_duplicates().iloc[0] for field in metadata_fields}
    for field, value in metadata.items():
        output[field] = value
    output["is_analysis_sector_eligible"] = True
    output["sector_mapping_weight"] = float(config["eligibility"]["required_weight"])
    output["baci_absence_treated_as_zero"] = True
    output["quantity_included"] = False
    output["china_to_usa_common_benchmark"] = True
    output["treatment_repeated_across_connectors"] = True
    output["coverage_repeated_across_sectors"] = True
    output["common_benchmarks_not_additive_across_connectors"] = True
    output["product_mapping_version"] = joined[
        "canonical_product_mapping_version"
    ].dropna().drop_duplicates().iloc[0]
    output["m3_sector_aggregation_version"] = config["version"]
    output["schema_version"] = config["schema_version"]

    string_columns = [
        "connector_iso3",
        "analysis_sector",
        "connector_group",
        "connector_baci_code",
        "analysis_sector_status",
        "trade_value_unit",
        "treatment_concept",
        "review_2024_treatment",
        "treatment_version",
        "product_mapping_version",
        "m3_sector_aggregation_version",
        "schema_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["year"] = output["year"].astype("int16")

    count_columns = [
        "sector_eligible_product_count",
        "excluded_product_count",
        "sector_treatment_product_count",
        "policy_denominator_observed_product_count",
        "treatment_missing_denominator_product_count",
        "treatment_zero_denominator_product_count",
        "treatment_no_hs17_mapping_product_count",
        "tariffed_product_count",
    ]
    for details in config["trade_flows"].values():
        count_columns.extend(
            [
                details["source_row_count_field"],
                details["positive_product_count_field"],
                details["zero_source_product_count_field"],
            ]
        )
    for column in count_columns:
        output[column] = output[column].astype("int32")

    boolean_columns = [
        "connector_is_proxy",
        "is_analysis_sector_eligible",
        "baci_absence_treated_as_zero",
        "quantity_included",
        "china_to_usa_common_benchmark",
        "historical_exclusions_applied",
        "four_year_review_2024_included",
        "treatment_repeated_across_connectors",
        "coverage_repeated_across_sectors",
        "common_benchmarks_not_additive_across_connectors",
    ]
    for column in boolean_columns:
        output[column] = output[column].astype("bool")

    key_columns = config["output"]["natural_key"]
    ordered = key_columns + [column for column in output.columns if column not in key_columns]
    return output[ordered].sort_values(key_columns).reset_index(drop=True)


def build_panel(
    trade: pd.DataFrame,
    crosswalk: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, pd.DataFrame]:
    joined, context = prepare_join(trade, crosswalk, config)
    context.update(verify_policy_replication(joined))
    trade_sector, eligible = build_trade_sector(joined, config)
    policy_sector, policy_products = build_policy_sector(joined, config)
    output = finalize_output(trade_sector, policy_sector, joined, config)
    return output, context, eligible, policy_products


def maximum_absolute_gap(left: pd.Series, right: pd.Series) -> float:
    difference = left.astype("float64") - right.astype("float64")
    return float(difference.abs().max()) if len(difference) else 0.0


def validate(
    project_root: Path,
    config: dict[str, Any],
    trade: pd.DataFrame,
    crosswalk: pd.DataFrame,
    output: pd.DataFrame,
    context: dict[str, Any],
    eligible: pd.DataFrame,
    policy_products: pd.DataFrame,
    input_hash_checks: dict[str, bool],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    value_tolerance = float(config["validation"]["value_tolerance_usd"])
    ratio_tolerance = float(config["validation"]["ratio_tolerance"])
    input_key = config["inputs"]["connector_trade_hs6_year"]["natural_key"]
    crosswalk_key = config["inputs"]["product_sector_crosswalk"]["natural_key"]
    output_key = config["output"]["natural_key"]

    trade_duplicates = int(trade.duplicated(input_key).sum())
    crosswalk_duplicates = int(crosswalk.duplicated(crosswalk_key).sum())
    output_duplicates = int(output.duplicated(output_key).sum())
    if not all(input_hash_checks.values()):
        failures.append("one or more configured M3.1 input hashes do not match")
    if len(trade) != int(config["inputs"]["connector_trade_hs6_year"]["expected_rows"]):
        failures.append("connector-product-year input row count differs from frozen config")
    if len(crosswalk) != int(config["inputs"]["product_sector_crosswalk"]["expected_rows"]):
        failures.append("product-sector crosswalk row count differs from frozen config")
    if trade_duplicates or crosswalk_duplicates or output_duplicates:
        failures.append("an input or output natural key is duplicated")
    if context["unmatched_crosswalk_row_count"]:
        failures.append("one or more connector-product-year rows did not match the crosswalk")
    if any(context["embedded_product_field_mismatch_counts"].values()):
        failures.append("embedded M2 product-sector fields differ from the canonical crosswalk")
    if context["eligible_nonunit_weight_row_count"]:
        failures.append("one or more eligible rows have a non-unit sector weight")
    if context["ineligible_nonnull_weight_row_count"]:
        failures.append("one or more ineligible rows unexpectedly have a sector weight")
    if context["policy_replication_inconsistent_key_count"]:
        failures.append("policy or product fields vary across connectors within product-year")

    expected_rows = int(config["analysis"]["expected_output_rows"])
    if len(output) != expected_rows:
        failures.append(f"output has {len(output)} rows instead of {expected_rows}")
    observed_connectors = sorted(output["connector_iso3"].dropna().unique().tolist())
    expected_connectors = sorted(config["analysis"]["connectors"])
    observed_years = sorted(output["year"].astype(int).unique().tolist())
    expected_years = list(
        range(
            int(config["analysis"]["years"]["start"]),
            int(config["analysis"]["years"]["end"]) + 1,
        )
    )
    observed_sectors = sorted(output["analysis_sector"].dropna().unique().tolist())
    expected_sectors = sorted(config["analysis"]["sectors"])
    if observed_connectors != expected_connectors:
        failures.append("output connector set differs from frozen config")
    if observed_years != expected_years:
        failures.append("output year set differs from frozen config")
    if observed_sectors != expected_sectors:
        failures.append("output sector set differs from frozen config")

    eligible_products = int(eligible["analysis_hs6"].nunique())
    excluded_products = int(trade["analysis_hs6"].nunique() - eligible_products)
    if eligible_products != int(config["analysis"]["expected_eligible_products"]):
        failures.append("eligible product count differs from frozen config")
    if excluded_products != int(config["analysis"]["expected_excluded_products"]):
        failures.append("excluded product count differs from frozen config")
    sector_product_counts = (
        eligible[["analysis_sector", "analysis_hs6"]]
        .drop_duplicates()
        .groupby("analysis_sector")["analysis_hs6"]
        .nunique()
        .astype(int)
        .to_dict()
    )
    expected_sector_counts = {
        key: int(value) for key, value in config["analysis"]["sectors"].items()
    }
    if sector_product_counts != expected_sector_counts:
        failures.append("eligible product counts by sector differ from frozen config")

    zero_denominator_products = int(
        policy_products.loc[
            policy_products["policy_zero_denominator"], "analysis_hs6"
        ].nunique()
    )
    no_mapping_products = int(
        policy_products.loc[
            policy_products["policy_no_hs17_mapping"], "analysis_hs6"
        ].nunique()
    )
    if zero_denominator_products != int(
        config["analysis"]["expected_zero_denominator_eligible_products"]
    ):
        failures.append("zero-denominator eligible product count differs from config")
    if no_mapping_products != int(
        config["analysis"]["expected_no_hs17_mapping_eligible_products"]
    ):
        failures.append("no-HS2017-mapping eligible product count differs from config")

    trade_reconciliation: dict[str, Any] = {}
    grouped_input = eligible.groupby(["connector_iso3", "year"], sort=True)
    grouped_output = output.groupby(["connector_iso3", "year"], sort=True)
    coverage_once = output.sort_values("analysis_sector").drop_duplicates(
        ["connector_iso3", "year"]
    )
    coverage_once = coverage_once.set_index(["connector_iso3", "year"]).sort_index()
    full_grouped = trade.groupby(["connector_iso3", "year"], sort=True)
    ineligible = trade.loc[
        ~trade.set_index(["connector_iso3", "analysis_hs6", "year"]).index.isin(
            eligible.set_index(["connector_iso3", "analysis_hs6", "year"]).index
        )
    ]
    excluded_grouped = ineligible.groupby(["connector_iso3", "year"], sort=True)

    for details in config["trade_flows"].values():
        value_field = details["value_field"]
        row_count_field = details["source_row_count_field"]
        positive_field = details["positive_product_count_field"]
        zero_source_field = details["zero_source_product_count_field"]
        excluded_field = details["excluded_value_field"]
        included_share_field = details["included_share_field"]

        input_eligible_by_key = grouped_input[value_field].sum()
        output_by_key = grouped_output[value_field].sum()
        value_gap_by_key = output_by_key - input_eligible_by_key
        input_row_count_by_key = grouped_input[row_count_field].sum()
        output_row_count_by_key = grouped_output[row_count_field].sum()
        row_count_gap_by_key = output_row_count_by_key - input_row_count_by_key
        input_positive_count_by_key = grouped_input[value_field].apply(
            lambda values: int(values.gt(0).sum())
        )
        output_positive_count_by_key = grouped_output[positive_field].sum()
        input_zero_source_by_key = grouped_input[row_count_field].apply(
            lambda values: int(values.eq(0).sum())
        )
        output_zero_source_by_key = grouped_output[zero_source_field].sum()
        input_full_by_key = full_grouped[value_field].sum()
        input_excluded_by_key = excluded_grouped[value_field].sum()
        recorded_excluded_by_key = coverage_once[excluded_field]
        recorded_share_by_key = coverage_once[included_share_field]
        expected_share_by_key = input_eligible_by_key / input_full_by_key
        full_reconstruction_gap = (
            input_eligible_by_key + recorded_excluded_by_key - input_full_by_key
        )

        record = {
            "eligible_product_total_usd": float(input_eligible_by_key.sum()),
            "sector_output_total_usd": float(output_by_key.sum()),
            "global_eligible_value_gap_usd": float(
                output_by_key.sum() - input_eligible_by_key.sum()
            ),
            "max_abs_connector_year_value_gap_usd": float(value_gap_by_key.abs().max()),
            "max_abs_connector_year_row_count_gap": int(row_count_gap_by_key.abs().max()),
            "max_abs_connector_year_positive_product_count_gap": int(
                (output_positive_count_by_key - input_positive_count_by_key).abs().max()
            ),
            "max_abs_connector_year_zero_source_product_count_gap": int(
                (output_zero_source_by_key - input_zero_source_by_key).abs().max()
            ),
            "excluded_product_total_usd": float(input_excluded_by_key.sum()),
            "recorded_excluded_total_usd": float(recorded_excluded_by_key.sum()),
            "max_abs_connector_year_excluded_value_gap_usd": maximum_absolute_gap(
                recorded_excluded_by_key, input_excluded_by_key
            ),
            "max_abs_connector_year_full_reconstruction_gap_usd": float(
                full_reconstruction_gap.abs().max()
            ),
            "max_abs_connector_year_included_share_gap": maximum_absolute_gap(
                recorded_share_by_key, expected_share_by_key
            ),
        }
        trade_reconciliation[value_field] = record
        if (
            abs(record["global_eligible_value_gap_usd"]) > value_tolerance
            or record["max_abs_connector_year_value_gap_usd"] > value_tolerance
            or record["max_abs_connector_year_excluded_value_gap_usd"] > value_tolerance
            or record["max_abs_connector_year_full_reconstruction_gap_usd"]
            > value_tolerance
            or record["max_abs_connector_year_row_count_gap"] != 0
            or record["max_abs_connector_year_positive_product_count_gap"] != 0
            or record["max_abs_connector_year_zero_source_product_count_gap"] != 0
            or record["max_abs_connector_year_included_share_gap"] > ratio_tolerance
        ):
            failures.append(f"{value_field} failed product-to-sector reconciliation")

    policy_ratio_checks = {
        "sector_tariff_rate_china_weighted": safe_divide(
            output["sector_tariff_exposure_numerator_usd"],
            output["sector_china_import_value_2017"],
        ),
        "sector_tariff_exposure": safe_divide(
            output["sector_tariff_exposure_numerator_usd"],
            output["sector_total_us_import_value_2017"],
        ),
        "sector_china_import_share_2017": safe_divide(
            output["sector_china_import_value_2017"],
            output["sector_total_us_import_value_2017"],
        ),
        "tariffed_product_share_count": safe_divide(
            output["tariffed_product_count"],
            output["sector_treatment_product_count"],
        ),
        "tariffed_product_share_china_value": safe_divide(
            output["tariffed_china_import_value_2017"],
            output["sector_china_import_value_2017"],
        ),
        "tariffed_product_share_us_value": safe_divide(
            output["tariffed_total_us_import_value_2017"],
            output["sector_total_us_import_value_2017"],
        ),
        "treatment_missing_denominator_product_share": safe_divide(
            output["treatment_missing_denominator_product_count"],
            output["sector_treatment_product_count"],
        ),
        "treatment_zero_denominator_product_share": safe_divide(
            output["treatment_zero_denominator_product_count"],
            output["sector_treatment_product_count"],
        ),
        "treatment_no_hs17_mapping_product_share": safe_divide(
            output["treatment_no_hs17_mapping_product_count"],
            output["sector_treatment_product_count"],
        ),
    }
    policy_formula_max_abs_gaps = {
        field: maximum_absolute_gap(output[field], expected)
        for field, expected in policy_ratio_checks.items()
    }
    if any(gap > ratio_tolerance for gap in policy_formula_max_abs_gaps.values()):
        failures.append("one or more sector policy ratios fail the formula check")

    repeated_fields = [
        "china_to_usa_value_usd",
        "china_to_usa_value_usd_row_count",
        "china_to_usa_positive_product_count",
        "china_to_usa_zero_source_product_count",
        "sector_total_us_import_value_2017",
        "sector_china_import_value_2017",
        "sector_tariff_exposure_numerator_usd",
        *policy_ratio_checks.keys(),
        "treatment_missing_denominator_product_count",
        "treatment_zero_denominator_product_count",
        "treatment_no_hs17_mapping_product_count",
    ]
    repeated_counts = output.groupby(["analysis_sector", "year"])[
        repeated_fields
    ].nunique(dropna=False)
    inconsistent_repeated_fields = {
        field: int((repeated_counts[field] > 1).sum()) for field in repeated_fields
    }
    if any(inconsistent_repeated_fields.values()):
        failures.append("a repeated China-USA or policy field varies across connectors")

    coverage_fields = [
        "excluded_product_count",
        *[
            field
            for details in config["trade_flows"].values()
            for field in [details["excluded_value_field"], details["included_share_field"]]
        ],
    ]
    coverage_counts = output.groupby(["connector_iso3", "year"])[coverage_fields].nunique(
        dropna=False
    )
    inconsistent_coverage_fields = {
        field: int((coverage_counts[field] > 1).sum()) for field in coverage_fields
    }
    if any(inconsistent_coverage_fields.values()):
        failures.append("a connector-year coverage field varies across sectors")

    twn_rows = output.loc[output["connector_iso3"].eq("TWN")]
    twn_proxy_false_count = int((~twn_rows["connector_is_proxy"]).sum())
    if len(twn_rows) != len(expected_years) * len(expected_sectors) or twn_proxy_false_count:
        failures.append("TWN proxy status is incomplete or inconsistent")

    required_numeric = [
        *[
            field
            for details in config["trade_flows"].values()
            for field in [
                details["value_field"],
                details["source_row_count_field"],
                details["positive_product_count_field"],
                details["zero_source_product_count_field"],
                details["excluded_value_field"],
                details["included_share_field"],
            ]
        ],
        "sector_eligible_product_count",
        "excluded_product_count",
        "sector_total_us_import_value_2017",
        "sector_china_import_value_2017",
        "sector_tariff_exposure_numerator_usd",
        *policy_ratio_checks.keys(),
    ]
    required_numeric_missing_count = int(output[required_numeric].isna().sum().sum())
    if required_numeric_missing_count:
        failures.append("one or more required M3.1 numeric output fields are missing")

    stata_aliases = config["output"]["stata_aliases"]
    output_columns = set(output.columns)
    alias_columns = set(stata_aliases)
    missing_output_aliases = sorted(output_columns - alias_columns)
    extra_stata_aliases = sorted(alias_columns - output_columns)
    duplicate_stata_alias_count = len(stata_aliases.values()) - len(
        set(stata_aliases.values())
    )
    overlength_stata_aliases = sorted(
        alias for alias in stata_aliases.values() if len(alias) > 32
    )
    max_stata_alias_length = max(map(len, stata_aliases.values()))
    stata_alias_validation = {
        "alias_count": len(stata_aliases),
        "output_column_count": len(output.columns),
        "missing_output_aliases": missing_output_aliases,
        "extra_stata_aliases": extra_stata_aliases,
        "duplicate_alias_count": duplicate_stata_alias_count,
        "over_32_character_aliases": overlength_stata_aliases,
        "maximum_alias_length": max_stata_alias_length,
        "pass": not (
            missing_output_aliases
            or extra_stata_aliases
            or duplicate_stata_alias_count
            or overlength_stata_aliases
        ),
    }
    if not stata_alias_validation["pass"]:
        failures.append(
            "the frozen Stata alias map is incomplete, duplicated, or exceeds 32 characters"
        )
    if not determinism["sha256_match"]:
        failures.append("deterministic rebuild Parquet SHA256 does not match")
    if not determinism["temporary_output_cleaned"]:
        failures.append("determinism temporary output was not cleaned")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": input_hash_checks,
        "input_row_count": len(trade),
        "crosswalk_row_count": len(crosswalk),
        "input_duplicate_key_count": trade_duplicates,
        "crosswalk_duplicate_key_count": crosswalk_duplicates,
        "output_row_count": len(output),
        "output_duplicate_key_count": output_duplicates,
        "expected_output_row_count": expected_rows,
        "connector_count": len(observed_connectors),
        "sector_count": len(observed_sectors),
        "year_count": len(observed_years),
        "eligible_product_count": eligible_products,
        "excluded_product_count": excluded_products,
        "eligible_product_counts_by_sector": sector_product_counts,
        "zero_denominator_eligible_product_count": zero_denominator_products,
        "no_hs17_mapping_eligible_product_count": no_mapping_products,
        **context,
        "trade_reconciliation": trade_reconciliation,
        "policy_formula_max_abs_gaps": policy_formula_max_abs_gaps,
        "inconsistent_repeated_fields": inconsistent_repeated_fields,
        "inconsistent_coverage_fields": inconsistent_coverage_fields,
        "twn_output_row_count": len(twn_rows),
        "twn_proxy_false_count": twn_proxy_false_count,
        "required_numeric_missing_count": required_numeric_missing_count,
        "stata_alias_validation": stata_alias_validation,
        "value_tolerance_usd": value_tolerance,
        "ratio_tolerance": ratio_tolerance,
        "determinism_check": determinism,
        "common_benchmarks_not_additive_across_connectors": True,
        "treatment_repeated_across_connectors": True,
        "coverage_repeated_across_sectors": True,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# M3.1 Connector Trade Sector Panel Validation",
        "",
        "## Material Passport",
        "",
        "- Origin Skill: `academic-research-suite/experiment-agent`",
        "- Origin Mode: `run + validate`",
        f"- Origin Date: `{validation['generated_at_utc'][:10]}`",
        f"- Verification Status: `{'VERIFIED' if validation['validation_status'] == 'PASS' else 'BLOCKED'}`",
        f"- Version Label: `{validation['aggregation_version']}`",
        "",
        "## Result",
        "",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Output: `{validation['output_path']}`",
        f"- Output rows: `{validation['output_row_count']}`",
        f"- Natural-key duplicates: `{validation['output_duplicate_key_count']}`",
        f"- Connectors / sectors / years: `{validation['connector_count']} / {validation['sector_count']} / {validation['year_count']}`",
        f"- Eligible / excluded products: `{validation['eligible_product_count']} / {validation['excluded_product_count']}`",
        f"- Deterministic Parquet SHA256 match: `{'yes' if validation['determinism_check']['sha256_match'] else 'no'}`",
        "",
        "## Required checks",
        "",
        f"- Configured input SHA256 checks: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- All products matched the canonical crosswalk: `{'yes' if validation['unmatched_crosswalk_row_count'] == 0 else 'no'}`",
        f"- Embedded M2 product fields equal canonical crosswalk: `{'yes' if not any(validation['embedded_product_field_mismatch_counts'].values()) else 'no'}`",
        f"- Expected 1,001-row complete sector grid: `{'yes' if validation['output_row_count'] == validation['expected_output_row_count'] else 'no'}`",
        f"- Zero-denominator / no-HS2017-mapping eligible products retained: `{validation['zero_denominator_eligible_product_count']} / {validation['no_hs17_mapping_eligible_product_count']}`",
        f"- TWN proxy rows valid: `{'yes' if validation['twn_proxy_false_count'] == 0 else 'no'}`",
        f"- Required numeric missing count: `{validation['required_numeric_missing_count']}`",
        f"- Stata alias map complete/unique/<=32 characters: `{'yes' if validation['stata_alias_validation']['pass'] else 'no'}` "
        f"({validation['stata_alias_validation']['alias_count']} aliases; maximum length "
        f"{validation['stata_alias_validation']['maximum_alias_length']})",
        "",
        "## Eligible product counts by sector",
        "",
        "| Analysis sector | Eligible HS6 count |",
        "|---|---:|",
    ]
    for sector, count in sorted(validation["eligible_product_counts_by_sector"].items()):
        lines.append(f"| `{sector}` | {count} |")
    lines.extend(
        [
            "",
            "## Trade-flow reconciliation",
            "",
            "| Flow | Eligible input USD | Sector output USD | Global gap USD | Max connector-year gap USD | Excluded gap USD | Full-universe gap USD | Share gap |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for field, record in validation["trade_reconciliation"].items():
        lines.append(
            f"| `{field}` | {record['eligible_product_total_usd']:.2f} | "
            f"{record['sector_output_total_usd']:.2f} | "
            f"{record['global_eligible_value_gap_usd']:.6f} | "
            f"{record['max_abs_connector_year_value_gap_usd']:.6f} | "
            f"{record['max_abs_connector_year_excluded_value_gap_usd']:.6f} | "
            f"{record['max_abs_connector_year_full_reconstruction_gap_usd']:.6f} | "
            f"{record['max_abs_connector_year_included_share_gap']:.3e} |"
        )
    lines.extend(
        [
            "",
            "## Policy formula checks",
            "",
            "| Field | Maximum absolute formula gap |",
            "|---|---:|",
        ]
    )
    for field, gap in validation["policy_formula_max_abs_gaps"].items():
        lines.append(f"| `{field}` | {gap:.3e} |")
    lines.extend(
        [
            "",
            "## Interpretation boundaries",
            "",
            "- The output is an annual connector-sector panel only. It does not contain pre/shock/post windows, growth rates, replacement ratios, rankings, production-side variables, or structural moments.",
            "- China-to-USA and policy fields repeat across connectors for comparison and are non-additive across connectors.",
            "- Coverage fields repeat across sectors within connector-year and are non-additive across sectors.",
            "- Section 301 remains gross statutory initial-action exposure without historical exclusions or the separate 2024 review extension.",
            "- `source_row_count=0` product states remain visible through flow-specific zero-source product counts; they are not confused with observed zero-value rows.",
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


def read_inputs(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    trade_path = project_root / config["inputs"]["connector_trade_hs6_year"]["path"]
    crosswalk_path = project_root / config["inputs"]["product_sector_crosswalk"]["path"]
    return pq.read_table(trade_path).to_pandas(), pq.read_table(crosswalk_path).to_pandas()


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    canonical_output_path: Path,
) -> dict[str, Any]:
    temp_directory = (
        project_root / config["validation"]["determinism_temp_directory"]
    ).resolve()
    if not temp_directory.is_relative_to(project_root):
        raise ValueError("Determinism temp directory must remain inside the project root")
    temp_directory.mkdir(parents=True, exist_ok=True)
    temp_output = temp_directory / "connector_trade_sector_year_second.parquet"
    second_trade, second_crosswalk = read_inputs(project_root, config)
    second_output, _, _, _ = build_panel(second_trade, second_crosswalk, config)
    write_parquet(second_output, temp_output)
    canonical_hash = sha256(canonical_output_path)
    second_hash = sha256(temp_output)
    match = canonical_hash == second_hash
    temp_output.unlink()
    if not any(temp_directory.iterdir()):
        temp_directory.rmdir()
    return {
        "required": bool(config["validation"]["require_deterministic_parquet_sha256"]),
        "canonical_output_sha256": canonical_hash,
        "second_build_sha256": second_hash,
        "sha256_match": match,
        "temporary_output_path": temp_output.relative_to(project_root).as_posix(),
        "temporary_output_cleaned": not temp_output.exists()
        and not temp_directory.exists(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and validate the M3.1 connector-sector-year annual trade panel."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/connector_trade_sector_rules.yaml"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = (
        args.config if args.config.is_absolute() else project_root / args.config
    )
    config = load_yaml(config_path)
    output_path = (
        args.output
        if args.output and args.output.is_absolute()
        else project_root / (args.output or Path(config["output"]["path"]))
    )
    validation_json = (
        args.validation_json
        if args.validation_json and args.validation_json.is_absolute()
        else project_root
        / (args.validation_json or Path(config["output"]["validation_json"]))
    )
    validation_md = (
        args.validation_md
        if args.validation_md and args.validation_md.is_absolute()
        else project_root / (args.validation_md or Path(config["output"]["validation_md"]))
    )
    for path in [output_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    input_hash_checks = {
        name: sha256(project_root / details["path"]) == details["sha256"]
        for name, details in config["inputs"].items()
    }
    trade, crosswalk = read_inputs(project_root, config)
    output, context, eligible, policy_products = build_panel(trade, crosswalk, config)
    table = write_parquet(output, output_path)
    determinism = deterministic_rebuild(project_root, config, output_path)
    validation = validate(
        project_root,
        config,
        trade,
        crosswalk,
        output,
        context,
        eligible,
        policy_products,
        input_hash_checks,
        determinism,
    )
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": config_path.relative_to(project_root).as_posix(),
            "config_sha256": sha256(config_path),
            "aggregation_version": config["version"],
            "schema_version": config["schema_version"],
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
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
    validation_md.write_text(
        markdown_report(validation),
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "output_rows": validation["output_row_count"],
                "output_sha256": validation["output_sha256"],
                "deterministic_sha256_match": determinism["sha256_match"],
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
