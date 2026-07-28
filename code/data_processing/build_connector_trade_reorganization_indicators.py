from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


PRODUCT_KEY = ["connector_iso3", "analysis_hs6"]
SECTOR_KEY = ["connector_iso3", "analysis_sector"]
ANNUAL_KEY = ["connector_iso3", "analysis_hs6", "year"]
FLOW_NAMES = [
    "china_to_connector",
    "east_asia_to_connector",
    "connector_to_usa",
    "china_to_usa",
]
ENTITY_FIELDS = [
    "connector_group",
    "connector_baci_code",
    "connector_is_proxy",
    "trade_value_unit",
]
POLICY_REPEATED_FIELDS = [
    "tariffed_product",
    "tariff_exposure",
    "policy_mapping_status",
    "treatment_concept",
    "historical_exclusions_applied",
    "four_year_review_2024_included",
]


def schema_signature(schema: pa.Schema) -> str:
    payload = [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]
    encoded = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def maximum_absolute_gap(
    left: pd.Series,
    right: pd.Series,
) -> tuple[float, int]:
    left_numeric = pd.to_numeric(left, errors="coerce").astype("float64")
    right_numeric = pd.to_numeric(right, errors="coerce").astype("float64")
    missing_mismatch = int((left_numeric.isna() ^ right_numeric.isna()).sum())
    usable = left_numeric.notna() & right_numeric.notna()
    if usable.any():
        gap = float((left_numeric.loc[usable] - right_numeric.loc[usable]).abs().max())
    else:
        gap = 0.0
    return gap, missing_mismatch


def safe_divide_series(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    usable = denominator.notna() & denominator.ne(0)
    result.loc[usable] = (
        numerator.loc[usable].astype("float64")
        / denominator.loc[usable].astype("float64")
    )
    return result


def safe_divide_scalar(numerator: float, denominator: float) -> float:
    if pd.isna(denominator) or float(denominator) == 0:
        return float("nan")
    return float(numerator) / float(denominator)


def unique_scalar(frame: pd.DataFrame, field: str) -> Any:
    values = frame[field].drop_duplicates()
    if len(values) != 1:
        raise ValueError(
            f"Expected one unique value for {field}, observed {len(values)}"
        )
    return values.iloc[0]


def validate_project_temp_path(project_root: Path, relative_path: str) -> Path:
    path = (project_root / relative_path).resolve()
    if not path.is_relative_to(project_root):
        raise ValueError(f"Temporary path escapes project root: {path}")
    if path.drive.lower() != project_root.drive.lower():
        raise ValueError(f"Temporary path is not on the project drive: {path}")
    return path


def remove_owned_temp_directory(path: Path) -> None:
    if not path.exists():
        return
    for child in list(path.iterdir()):
        if child.is_dir():
            remove_owned_temp_directory(child)
        else:
            child.unlink()
    path.rmdir()


def relative_or_absolute(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def alias_validation(
    frame: pd.DataFrame,
    aliases: dict[str, str],
) -> dict[str, Any]:
    missing = sorted(set(frame.columns) - set(aliases))
    extra = sorted(set(aliases) - set(frame.columns))
    alias_values = list(aliases.values())
    duplicate_aliases = sorted(
        {alias for alias in alias_values if alias_values.count(alias) > 1}
    )
    over_length = {
        field: alias for field, alias in aliases.items() if len(alias) > 32
    }
    invalid = {
        field: alias
        for field, alias in aliases.items()
        if not alias or (not alias[0].isalpha() and alias[0] != "_")
    }
    maximum_length = max((len(alias) for alias in alias_values), default=0)
    return {
        "pass": not missing
        and not extra
        and not duplicate_aliases
        and not over_length
        and not invalid,
        "alias_count": len(aliases),
        "maximum_alias_length": maximum_length,
        "missing_fields": missing,
        "extra_fields": extra,
        "duplicate_aliases": duplicate_aliases,
        "over_32_characters": over_length,
        "invalid_aliases": invalid,
    }


def weighted_correlation(
    x: pd.Series,
    y: pd.Series,
    weight: pd.Series,
) -> float:
    usable = x.notna() & y.notna() & weight.gt(0)
    if not usable.any():
        return float("nan")
    x_values = x.loc[usable].astype("float64").to_numpy()
    y_values = y.loc[usable].astype("float64").to_numpy()
    weights = weight.loc[usable].astype("float64").to_numpy()
    x_mean = float(np.average(x_values, weights=weights))
    y_mean = float(np.average(y_values, weights=weights))
    x_variance = float(np.average((x_values - x_mean) ** 2, weights=weights))
    y_variance = float(np.average((y_values - y_mean) ** 2, weights=weights))
    if x_variance <= 0 or y_variance <= 0:
        return float("nan")
    covariance = float(
        np.average(
            (x_values - x_mean) * (y_values - y_mean),
            weights=weights,
        )
    )
    return covariance / float(np.sqrt(x_variance * y_variance))


def join_canonical_crosswalk(
    annual: pd.DataFrame,
    crosswalk: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    canonical = crosswalk[
        [
            "analysis_hs6",
            "analysis_sector",
            "is_analysis_sector_eligible",
            "sector_mapping_weight",
            "mapping_version",
        ]
    ].rename(
        columns={
            "analysis_sector": "canonical_analysis_sector",
            "is_analysis_sector_eligible": (
                "canonical_is_analysis_sector_eligible"
            ),
            "mapping_version": "canonical_product_mapping_version",
        }
    )
    merged = annual.merge(
        canonical,
        on="analysis_hs6",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    sector_mismatch = (
        merged["analysis_sector"].fillna("")
        .ne(merged["canonical_analysis_sector"].fillna(""))
        .sum()
    )
    eligibility_mismatch = (
        merged["is_analysis_sector_eligible"]
        .ne(merged["canonical_is_analysis_sector_eligible"])
        .sum()
    )
    version_mismatch = (
        merged["product_mapping_version"]
        .fillna("")
        .ne(merged["canonical_product_mapping_version"].fillna(""))
        .sum()
    )
    context = {
        "unmatched_row_count": int(merged["_merge"].ne("both").sum()),
        "embedded_sector_mismatch_count": int(sector_mismatch),
        "embedded_eligibility_mismatch_count": int(eligibility_mismatch),
        "embedded_mapping_version_mismatch_count": int(version_mismatch),
    }
    merged = merged.drop(columns=["_merge"])
    return merged, context


def product_policy_reference(
    eligible_annual: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    post = config["windows"]["post"]
    policy = eligible_annual.loc[
        eligible_annual["year"].between(int(post["start"]), int(post["end"]))
    ].copy()
    policy_key = ["analysis_hs6", "year"]
    repeated_nunique = policy.groupby(policy_key, observed=True)[
        POLICY_REPEATED_FIELDS
    ].nunique(dropna=False)
    repeated_inconsistencies = {
        field: int(repeated_nunique[field].gt(1).sum())
        for field in POLICY_REPEATED_FIELDS
    }
    policy = (
        policy.sort_values(["connector_iso3", "analysis_hs6", "year"])
        .drop_duplicates(policy_key)
        .copy()
    )
    product_policy = (
        policy.groupby(
            [
                "analysis_hs6",
                "canonical_analysis_sector",
            ],
            sort=False,
            observed=True,
        )
        .agg(
            post_tariffed_year_share=("tariffed_product", "mean"),
            post_tariff_exposure_mean=("tariff_exposure", "mean"),
            post_policy_mapping_status=("policy_mapping_status", "first"),
        )
        .reset_index()
        .rename(
            columns={
                "canonical_analysis_sector": "analysis_sector",
            }
        )
    )
    product_policy["post_tariffed_product_flag"] = (
        product_policy["post_tariffed_year_share"].gt(0)
    )
    product_policy["post_tariff_exposure_observed"] = product_policy[
        "post_tariff_exposure_mean"
    ].notna()
    product_policy["positive_exposure_flag"] = pd.Series(
        pd.NA, index=product_policy.index, dtype="boolean"
    )
    observed = product_policy["post_tariff_exposure_observed"]
    product_policy.loc[observed, "positive_exposure_flag"] = (
        product_policy.loc[observed, "post_tariff_exposure_mean"].gt(0)
    )
    positive = product_policy.loc[
        product_policy["positive_exposure_flag"].fillna(False)
    ]
    percentile = float(
        config["exposure_overlap"]["high_exposure_definitions"][
            "top_quartile"
        ]["percentile"]
    )
    cutoffs = (
        positive.groupby("analysis_sector", observed=True)[
            "post_tariff_exposure_mean"
        ]
        .quantile(percentile, interpolation="linear")
        .rename("sector_positive_exposure_p75_cutoff")
    )
    product_policy = product_policy.merge(
        cutoffs,
        on="analysis_sector",
        how="left",
        validate="many_to_one",
    )
    product_policy["top_quartile_positive_exposure_flag"] = pd.Series(
        pd.NA, index=product_policy.index, dtype="boolean"
    )
    product_policy.loc[
        observed,
        "top_quartile_positive_exposure_flag",
    ] = (
        product_policy.loc[observed, "positive_exposure_flag"].astype(bool)
        & product_policy.loc[
            observed, "post_tariff_exposure_mean"
        ].ge(
            product_policy.loc[
                observed, "sector_positive_exposure_p75_cutoff"
            ]
        )
    )
    context = {
        "repeated_field_inconsistencies": repeated_inconsistencies,
        "policy_product_year_rows": len(policy),
        "post_year_count": int(policy["year"].nunique()),
    }
    return product_policy, context


def window_product_values(
    eligible_annual: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    window_outputs: dict[str, pd.DataFrame] = {}
    observed_counts: dict[str, dict[str, int]] = {}
    for window_id in ["pre", "post"]:
        details = config["windows"][window_id]
        window = eligible_annual.loc[
            eligible_annual["year"].between(
                int(details["start"]), int(details["end"])
            )
        ].copy()
        grouped = (
            window.groupby(PRODUCT_KEY, sort=False, observed=True)
            .agg(
                analysis_sector=("canonical_analysis_sector", "first"),
                product_description=("product_description", "first"),
                connector_group=("connector_group", "first"),
                connector_baci_code=("connector_baci_code", "first"),
                connector_is_proxy=("connector_is_proxy", "first"),
                trade_value_unit=("trade_value_unit", "first"),
                observed_year_count=("year", "nunique"),
                **{
                    f"{flow}_value_usd": (
                        f"{flow}_value_usd",
                        "mean",
                    )
                    for flow in FLOW_NAMES
                },
            )
            .reset_index()
        )
        observed_counts[window_id] = {
            "minimum": int(grouped["observed_year_count"].min()),
            "maximum": int(grouped["observed_year_count"].max()),
            "expected": int(details["expected_year_count"]),
        }
        renames = {
            "observed_year_count": f"{window_id}_observed_year_count",
            **{
                f"{flow}_value_usd": f"{flow}_value_usd_{window_id}"
                for flow in FLOW_NAMES
            },
        }
        grouped = grouped.rename(columns=renames)
        if window_id == "post":
            grouped = grouped.drop(
                columns=[
                    "analysis_sector",
                    "product_description",
                    *ENTITY_FIELDS,
                ]
            )
        window_outputs[window_id] = grouped
    product = window_outputs["pre"].merge(
        window_outputs["post"],
        on=PRODUCT_KEY,
        how="inner",
        validate="one_to_one",
    )
    for flow in FLOW_NAMES:
        product[f"{flow}_value_usd_change"] = (
            product[f"{flow}_value_usd_post"]
            - product[f"{flow}_value_usd_pre"]
        )
    return product, {"observed_year_counts": observed_counts}


def build_product_output(
    annual: pd.DataFrame,
    crosswalk: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame]:
    joined, join_context = join_canonical_crosswalk(annual, crosswalk)
    eligible = joined.loc[
        joined["canonical_is_analysis_sector_eligible"].eq(True)
        & joined["sector_mapping_weight"].eq(1)
    ].copy()
    product, window_context = window_product_values(eligible, config)
    policy, policy_context = product_policy_reference(eligible, config)
    product = product.merge(
        policy,
        on=["analysis_hs6", "analysis_sector"],
        how="left",
        validate="many_to_one",
    )

    product["china_us_decline_usd"] = (
        product["china_to_usa_value_usd_pre"]
        - product["china_to_usa_value_usd_post"]
    ).clip(lower=0)
    product["china_us_decline_flag"] = product["china_us_decline_usd"].gt(0)
    product["connector_export_positive_gain_usd"] = product[
        "connector_to_usa_value_usd_change"
    ].clip(lower=0)
    product["connector_export_gain_positive_flag"] = product[
        "connector_to_usa_value_usd_change"
    ].gt(0)
    product["china_input_gain_positive_flag"] = product[
        "china_to_connector_value_usd_change"
    ].gt(0)
    product["east_asia_input_gain_positive_flag"] = product[
        "east_asia_to_connector_value_usd_change"
    ].gt(0)
    product["china_both_legs_positive_flag"] = (
        product["china_input_gain_positive_flag"]
        & product["connector_export_gain_positive_flag"]
    )
    product["east_asia_both_legs_positive_flag"] = (
        product["east_asia_input_gain_positive_flag"]
        & product["connector_export_gain_positive_flag"]
    )
    product["china_decline_connector_gain_flag"] = (
        product["china_us_decline_flag"]
        & product["connector_export_gain_positive_flag"]
    )
    product["china_triple_condition_flag"] = (
        product["china_us_decline_flag"]
        & product["china_input_gain_positive_flag"]
        & product["connector_export_gain_positive_flag"]
    )
    product["east_asia_triple_condition_flag"] = (
        product["china_us_decline_flag"]
        & product["east_asia_input_gain_positive_flag"]
        & product["connector_export_gain_positive_flag"]
    )
    for source, flow in [
        ("china", "china_to_connector"),
        ("east_asia", "east_asia_to_connector"),
    ]:
        product[f"{source}_correlation_active_product_flag"] = (
            product[f"{flow}_value_usd_pre"]
            + product[f"{flow}_value_usd_post"]
            + product["connector_to_usa_value_usd_pre"]
            + product["connector_to_usa_value_usd_post"]
        ).gt(0)
        product[f"{source}_correlation_pre_weight_usd"] = (
            product[f"{flow}_value_usd_pre"]
            + product["connector_to_usa_value_usd_pre"]
        )

    product["treatment_concept"] = str(
        unique_scalar(eligible, "treatment_concept")
    )
    product["historical_exclusions_applied"] = bool(
        unique_scalar(eligible, "historical_exclusions_applied")
    )
    product["four_year_review_2024_included"] = bool(
        unique_scalar(eligible, "four_year_review_2024_included")
    )
    product["china_to_usa_common_benchmark"] = True
    product["policy_repeated_across_connectors"] = True
    product["common_fields_not_additive_across_connectors"] = True
    product["product_mapping_version"] = str(
        unique_scalar(eligible, "canonical_product_mapping_version")
    )
    product["trade_treatment_merge_version"] = str(
        unique_scalar(eligible, "trade_treatment_merge_version")
    )
    product["m3_reorganization_indicator_version"] = config["version"]
    product["rules_config_sha256"] = config_hash
    product["schema_version"] = config["product_schema_version"]

    connector_order = {
        connector: order
        for order, connector in enumerate(config["analysis"]["connectors"])
    }
    sector_order = {
        sector: order
        for order, sector in enumerate(config["analysis"]["sectors"])
    }
    product["_connector_order"] = product["connector_iso3"].map(connector_order)
    product["_sector_order"] = product["analysis_sector"].map(sector_order)
    product = (
        product.sort_values(
            ["_connector_order", "_sector_order", "analysis_hs6"],
            kind="stable",
        )
        .drop(columns=["_connector_order", "_sector_order"])
        .reset_index(drop=True)
    )

    string_fields = [
        "connector_iso3",
        "analysis_hs6",
        "analysis_sector",
        "product_description",
        "connector_group",
        "connector_baci_code",
        "trade_value_unit",
        "post_policy_mapping_status",
        "treatment_concept",
        "product_mapping_version",
        "trade_treatment_merge_version",
        "m3_reorganization_indicator_version",
        "rules_config_sha256",
        "schema_version",
    ]
    boolean_fields = [
        "connector_is_proxy",
        "post_tariffed_product_flag",
        "post_tariff_exposure_observed",
        "china_us_decline_flag",
        "connector_export_gain_positive_flag",
        "china_input_gain_positive_flag",
        "east_asia_input_gain_positive_flag",
        "china_both_legs_positive_flag",
        "east_asia_both_legs_positive_flag",
        "china_decline_connector_gain_flag",
        "china_triple_condition_flag",
        "east_asia_triple_condition_flag",
        "china_correlation_active_product_flag",
        "east_asia_correlation_active_product_flag",
        "historical_exclusions_applied",
        "four_year_review_2024_included",
        "china_to_usa_common_benchmark",
        "policy_repeated_across_connectors",
        "common_fields_not_additive_across_connectors",
    ]
    for field in string_fields:
        product[field] = product[field].astype("string")
    for field in boolean_fields:
        product[field] = product[field].astype(bool)
    for field in [
        "positive_exposure_flag",
        "top_quartile_positive_exposure_flag",
    ]:
        product[field] = product[field].astype("boolean")
    for field in ["pre_observed_year_count", "post_observed_year_count"]:
        product[field] = product[field].astype("int8")

    context = {
        "join": join_context,
        "windows": window_context,
        "policy": policy_context,
        "eligible_annual_row_count": len(eligible),
    }
    return product, context, eligible


def aggregate_exposure_overlap(product: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for (connector, sector), group in product.groupby(
        SECTOR_KEY, sort=False, observed=True
    ):
        eligible_count = len(group)
        tariffed = group["post_tariffed_product_flag"]
        exposure_observed = group["post_tariff_exposure_observed"]
        positive_exposure = group["positive_exposure_flag"].fillna(False)
        top_exposure = group[
            "top_quartile_positive_exposure_flag"
        ].fillna(False)
        export_pre = group["connector_to_usa_value_usd_pre"].astype("float64")
        export_post = group["connector_to_usa_value_usd_post"].astype("float64")
        exposure = group["post_tariff_exposure_mean"].astype("float64")
        positive_gain = group["connector_export_positive_gain_usd"].astype(
            "float64"
        )

        tariffed_value_pre = float(export_pre.loc[tariffed].sum())
        tariffed_value_post = float(export_post.loc[tariffed].sum())
        exposure_observed_value_pre = float(
            export_pre.loc[exposure_observed].sum()
        )
        exposure_observed_value_post = float(
            export_post.loc[exposure_observed].sum()
        )
        exposure_numerator_pre = float(
            (
                export_pre.loc[exposure_observed]
                * exposure.loc[exposure_observed]
            ).sum()
        )
        exposure_numerator_post = float(
            (
                export_post.loc[exposure_observed]
                * exposure.loc[exposure_observed]
            ).sum()
        )
        positive_gain_total = float(positive_gain.sum())
        positive_gain_observed = float(
            positive_gain.loc[exposure_observed].sum()
        )
        positive_gain_positive_exposure = float(
            positive_gain.loc[positive_exposure].sum()
        )
        positive_gain_top_exposure = float(
            positive_gain.loc[top_exposure].sum()
        )
        records.append(
            {
                "connector_iso3": connector,
                "analysis_sector": sector,
                "post_tariffed_product_count": int(tariffed.sum()),
                "post_tariffed_product_share": (
                    float(tariffed.sum()) / eligible_count
                ),
                "post_exposure_observed_product_count": int(
                    exposure_observed.sum()
                ),
                "post_exposure_missing_product_count": int(
                    (~exposure_observed).sum()
                ),
                "post_exposure_missing_product_share": (
                    float((~exposure_observed).sum()) / eligible_count
                ),
                "positive_exposure_product_count": int(
                    positive_exposure.sum()
                ),
                "positive_exposure_product_share": (
                    float(positive_exposure.sum()) / eligible_count
                ),
                "top_quartile_positive_exposure_product_count": int(
                    top_exposure.sum()
                ),
                "top_quartile_positive_exposure_product_share": (
                    float(top_exposure.sum()) / eligible_count
                ),
                "sector_positive_exposure_p75_cutoff": float(
                    group["sector_positive_exposure_p75_cutoff"].iloc[0]
                ),
                "connector_export_tariffed_value_usd_pre": (
                    tariffed_value_pre
                ),
                "connector_export_tariffed_value_usd_post": (
                    tariffed_value_post
                ),
                "connector_export_tariff_overlap_pre": safe_divide_scalar(
                    tariffed_value_pre, float(export_pre.sum())
                ),
                "connector_export_tariff_overlap_post": safe_divide_scalar(
                    tariffed_value_post, float(export_post.sum())
                ),
                "exposure_observed_export_value_usd_pre": (
                    exposure_observed_value_pre
                ),
                "exposure_observed_export_value_usd_post": (
                    exposure_observed_value_post
                ),
                "connector_export_exposure_observed_value_share_pre": (
                    safe_divide_scalar(
                        exposure_observed_value_pre,
                        float(export_pre.sum()),
                    )
                ),
                "connector_export_exposure_observed_value_share_post": (
                    safe_divide_scalar(
                        exposure_observed_value_post,
                        float(export_post.sum()),
                    )
                ),
                "connector_export_exposure_numerator_usd_pre": (
                    exposure_numerator_pre
                ),
                "connector_export_exposure_numerator_usd_post": (
                    exposure_numerator_post
                ),
                "connector_export_exposure_weighted_pre": (
                    safe_divide_scalar(
                        exposure_numerator_pre,
                        exposure_observed_value_pre,
                    )
                ),
                "connector_export_exposure_weighted_post": (
                    safe_divide_scalar(
                        exposure_numerator_post,
                        exposure_observed_value_post,
                    )
                ),
                "connector_export_positive_gain_exposure_observed_usd": (
                    positive_gain_observed
                ),
                "connector_export_positive_gain_exposure_observed_share": (
                    safe_divide_scalar(
                        positive_gain_observed,
                        positive_gain_total,
                    )
                ),
                "connector_export_positive_gain_in_positive_exposure_usd": (
                    positive_gain_positive_exposure
                ),
                "gain_in_positive_exposure_products_share": (
                    safe_divide_scalar(
                        positive_gain_positive_exposure,
                        positive_gain_observed,
                    )
                ),
                "connector_export_positive_gain_in_top_quartile_exposure_usd": (
                    positive_gain_top_exposure
                ),
                "gain_in_top_quartile_exposure_products_share": (
                    safe_divide_scalar(
                        positive_gain_top_exposure,
                        positive_gain_observed,
                    )
                ),
            }
        )
    exposure_output = pd.DataFrame.from_records(records)
    exposure_output["connector_export_tariff_overlap_change"] = (
        exposure_output["connector_export_tariff_overlap_post"]
        - exposure_output["connector_export_tariff_overlap_pre"]
    )
    exposure_output["connector_export_exposure_weighted_change"] = (
        exposure_output["connector_export_exposure_weighted_post"]
        - exposure_output["connector_export_exposure_weighted_pre"]
    )
    return exposure_output


def diagnostic_flow_fields(
    diagnostics: pd.DataFrame,
    flow_id: str,
    semantic_prefix: str,
) -> pd.DataFrame:
    fields = diagnostics.loc[
        diagnostics["flow_id"].eq(flow_id),
        [
            *SECTOR_KEY,
            "value_usd_dh_growth_post_pre_raw",
            "value_usd_log_growth_post_pre_raw",
            "small_base_flag",
            "dh_growth_primary_eligible",
            "abnormal_growth_flag",
        ],
    ].copy()
    return fields.rename(
        columns={
            "value_usd_dh_growth_post_pre_raw": (
                f"{semantic_prefix}_dh_growth_raw"
            ),
            "value_usd_log_growth_post_pre_raw": (
                f"{semantic_prefix}_log_growth_raw"
            ),
            "small_base_flag": f"{semantic_prefix}_small_base_flag",
            "dh_growth_primary_eligible": (
                f"{semantic_prefix}_dh_primary_eligible"
            ),
            "abnormal_growth_flag": (
                f"{semantic_prefix}_abnormal_growth_flag"
            ),
        }
    )


def build_sector_output(
    product: pd.DataFrame,
    comparison: pd.DataFrame,
    diagnostics: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    sector = comparison[
        [
            *SECTOR_KEY,
            "connector_group",
            "connector_baci_code",
            "connector_is_proxy",
            "trade_value_unit",
            "sector_eligible_product_count",
            "treatment_concept",
            "historical_exclusions_applied",
            "four_year_review_2024_included",
            "product_mapping_version",
            "m3_window_construction_version",
            "china_to_usa_value_usd_pre",
            "china_to_usa_value_usd_post",
            "connector_to_usa_value_usd_pre",
            "connector_to_usa_value_usd_post",
            "china_to_connector_value_usd_pre",
            "china_to_connector_value_usd_post",
            "east_asia_to_connector_value_usd_pre",
            "east_asia_to_connector_value_usd_post",
        ]
    ].copy()
    sector = sector.rename(
        columns={
            "china_to_usa_value_usd_pre": "china_us_value_usd_pre",
            "china_to_usa_value_usd_post": "china_us_value_usd_post",
            "connector_to_usa_value_usd_pre": (
                "connector_us_value_usd_pre"
            ),
            "connector_to_usa_value_usd_post": (
                "connector_us_value_usd_post"
            ),
            "china_to_connector_value_usd_pre": (
                "china_input_value_usd_pre"
            ),
            "china_to_connector_value_usd_post": (
                "china_input_value_usd_post"
            ),
            "east_asia_to_connector_value_usd_pre": (
                "east_asia_input_value_usd_pre"
            ),
            "east_asia_to_connector_value_usd_post": (
                "east_asia_input_value_usd_post"
            ),
        }
    )
    sector["china_us_decline_usd"] = (
        sector["china_us_value_usd_pre"]
        - sector["china_us_value_usd_post"]
    ).clip(lower=0)
    denominator_threshold = float(
        config["replacement"]["denominator_threshold_usd"]
    )
    sector["replacement_denominator_threshold_usd"] = denominator_threshold
    sector["replacement_ratio_defined"] = sector[
        "china_us_decline_usd"
    ].gt(denominator_threshold)
    sector["connector_us_gain_usd"] = (
        sector["connector_us_value_usd_post"]
        - sector["connector_us_value_usd_pre"]
    )
    sector["connector_us_positive_gain_usd"] = sector[
        "connector_us_gain_usd"
    ].clip(lower=0)
    sector["replacement_ratio"] = np.nan
    sector.loc[
        sector["replacement_ratio_defined"],
        "replacement_ratio",
    ] = (
        sector.loc[
            sector["replacement_ratio_defined"],
            "connector_us_gain_usd",
        ]
        / sector.loc[
            sector["replacement_ratio_defined"],
            "china_us_decline_usd",
        ]
    )
    sector["import_replacement_candidate_flag"] = (
        sector["replacement_ratio_defined"]
        & sector["connector_us_gain_usd"].gt(0)
    )
    sector["china_input_gain_usd"] = (
        sector["china_input_value_usd_post"]
        - sector["china_input_value_usd_pre"]
    )
    sector["east_asia_input_gain_usd"] = (
        sector["east_asia_input_value_usd_post"]
        - sector["east_asia_input_value_usd_pre"]
    )

    for flow_id, semantic_prefix in [
        ("connector_to_usa", "connector_export"),
        ("china_to_connector", "china_input"),
        ("east_asia_to_connector", "east_asia_input"),
    ]:
        flow_fields = diagnostic_flow_fields(
            diagnostics, flow_id, semantic_prefix
        )
        sector = sector.merge(
            flow_fields,
            on=SECTOR_KEY,
            how="left",
            validate="one_to_one",
        )

    for source, numerator_prefix in [
        ("china", "china_input"),
        ("east_asia", "east_asia_input"),
    ]:
        for window in ["pre", "post"]:
            denominator = sector[f"connector_us_value_usd_{window}"]
            defined_field = (
                f"{source}_input_to_export_ratio_{window}_defined"
            )
            ratio_field = f"{source}_input_to_export_ratio_{window}"
            sector[defined_field] = denominator.gt(0)
            sector[ratio_field] = np.nan
            sector.loc[sector[defined_field], ratio_field] = (
                sector.loc[
                    sector[defined_field],
                    f"{numerator_prefix}_value_usd_{window}",
                ]
                / denominator.loc[sector[defined_field]]
            )
        sector[f"{source}_input_to_export_ratio_change"] = (
            sector[f"{source}_input_to_export_ratio_post"]
            - sector[f"{source}_input_to_export_ratio_pre"]
        )

    exposure = aggregate_exposure_overlap(product)
    sector = sector.merge(
        exposure,
        on=SECTOR_KEY,
        how="left",
        validate="one_to_one",
    )
    sector["china_us_benchmark_repeated_across_connectors"] = True
    sector["policy_product_counts_repeated_across_connectors"] = True
    sector["common_fields_not_additive_across_connectors"] = True
    sector["trade_treatment_merge_version"] = str(
        unique_scalar(product, "trade_treatment_merge_version")
    )
    sector["m3_growth_diagnostic_version"] = str(
        unique_scalar(diagnostics, "m3_growth_diagnostic_version")
    )
    sector["m3_reorganization_indicator_version"] = config["version"]
    sector["rules_config_sha256"] = config_hash
    sector["schema_version"] = config["sector_schema_version"]

    connector_order = {
        connector: order
        for order, connector in enumerate(config["analysis"]["connectors"])
    }
    sector_order = {
        name: order
        for order, name in enumerate(config["analysis"]["sectors"])
    }
    sector["_connector_order"] = sector["connector_iso3"].map(connector_order)
    sector["_sector_order"] = sector["analysis_sector"].map(sector_order)
    sector = (
        sector.sort_values(
            ["_connector_order", "_sector_order"], kind="stable"
        )
        .drop(columns=["_connector_order", "_sector_order"])
        .reset_index(drop=True)
    )

    string_fields = [
        "connector_iso3",
        "analysis_sector",
        "connector_group",
        "connector_baci_code",
        "trade_value_unit",
        "treatment_concept",
        "product_mapping_version",
        "trade_treatment_merge_version",
        "m3_window_construction_version",
        "m3_growth_diagnostic_version",
        "m3_reorganization_indicator_version",
        "rules_config_sha256",
        "schema_version",
    ]
    boolean_fields = [
        "connector_is_proxy",
        "historical_exclusions_applied",
        "four_year_review_2024_included",
        "replacement_ratio_defined",
        "import_replacement_candidate_flag",
        "connector_export_small_base_flag",
        "connector_export_dh_primary_eligible",
        "connector_export_abnormal_growth_flag",
        "china_input_small_base_flag",
        "china_input_dh_primary_eligible",
        "china_input_abnormal_growth_flag",
        "east_asia_input_small_base_flag",
        "east_asia_input_dh_primary_eligible",
        "east_asia_input_abnormal_growth_flag",
        "china_input_to_export_ratio_pre_defined",
        "china_input_to_export_ratio_post_defined",
        "east_asia_input_to_export_ratio_pre_defined",
        "east_asia_input_to_export_ratio_post_defined",
        "china_us_benchmark_repeated_across_connectors",
        "policy_product_counts_repeated_across_connectors",
        "common_fields_not_additive_across_connectors",
    ]
    integer_fields = [
        "sector_eligible_product_count",
        "post_tariffed_product_count",
        "post_exposure_observed_product_count",
        "post_exposure_missing_product_count",
        "positive_exposure_product_count",
        "top_quartile_positive_exposure_product_count",
    ]
    for field in string_fields:
        sector[field] = sector[field].astype("string")
    for field in boolean_fields:
        sector[field] = sector[field].astype(bool)
    for field in integer_fields:
        sector[field] = sector[field].astype("int32")
    return sector


def source_comovement_statistics(
    group: pd.DataFrame,
    source: str,
    flow: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    active = group[f"{source}_correlation_active_product_flag"]
    weight = group[f"{source}_correlation_pre_weight_usd"]
    active_count = int(active.sum())
    positive_weight_count = int((active & weight.gt(0)).sum())
    minimum_count = int(
        config["product_comovement"]["correlation"][
            "minimum_active_product_count"
        ]
    )
    minimum_weight_count = int(
        config["product_comovement"]["correlation"][
            "minimum_positive_weight_product_count"
        ]
    )
    correlation_low_n = active_count < minimum_count
    weighted_low_n = positive_weight_count < minimum_weight_count
    source_change = group[f"{flow}_value_usd_change"]
    export_change = group["connector_to_usa_value_usd_change"]
    correlation = float("nan")
    if not correlation_low_n:
        active_source = source_change.loc[active]
        active_export = export_change.loc[active]
        if active_source.nunique(dropna=True) > 1 and active_export.nunique(
            dropna=True
        ) > 1:
            correlation = float(active_source.corr(active_export))
    weighted = float("nan")
    if not weighted_low_n:
        weighted = weighted_correlation(
            source_change.loc[active],
            export_change.loc[active],
            weight.loc[active],
        )
    both = group[f"{source}_both_legs_positive_flag"]
    triple = group[f"{source}_triple_condition_flag"]
    positive_gain = group["connector_export_positive_gain_usd"]
    eligible_count = len(group)
    positive_gain_total = float(positive_gain.sum())
    return {
        f"{source}_active_product_count": active_count,
        f"{source}_positive_weight_product_count": positive_weight_count,
        f"{source}_correlation_low_n_flag": correlation_low_n,
        f"{source}_weighted_correlation_low_n_flag": weighted_low_n,
        f"{source}_product_change_correlation": correlation,
        f"{source}_weighted_product_change_correlation": weighted,
        f"{source}_both_legs_positive_product_count": int(both.sum()),
        f"{source}_both_legs_positive_product_share": (
            float(both.sum()) / eligible_count
        ),
        f"{source}_both_legs_positive_active_share": (
            safe_divide_scalar(float(both.sum()), float(active_count))
        ),
        f"{source}_both_legs_positive_export_gain_share": (
            safe_divide_scalar(
                float(positive_gain.loc[both].sum()),
                positive_gain_total,
            )
        ),
        f"{source}_triple_condition_product_count": int(triple.sum()),
        f"{source}_triple_condition_product_share": (
            float(triple.sum()) / eligible_count
        ),
        f"{source}_triple_condition_active_share": (
            safe_divide_scalar(float(triple.sum()), float(active_count))
        ),
        f"{source}_triple_condition_export_gain_share": (
            safe_divide_scalar(
                float(positive_gain.loc[triple].sum()),
                positive_gain_total,
            )
        ),
    }


def build_comovement_output(
    product: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    minimum_count = int(
        config["product_comovement"]["correlation"][
            "minimum_active_product_count"
        ]
    )
    for (connector, sector), group in product.groupby(
        SECTOR_KEY, sort=False, observed=True
    ):
        positive_gain = group["connector_export_positive_gain_usd"]
        china_decline = group["china_us_decline_flag"]
        rerouting = group["china_decline_connector_gain_flag"]
        record: dict[str, Any] = {
            "connector_iso3": connector,
            "analysis_sector": sector,
            "connector_group": group["connector_group"].iloc[0],
            "connector_baci_code": group["connector_baci_code"].iloc[0],
            "connector_is_proxy": bool(
                group["connector_is_proxy"].iloc[0]
            ),
            "trade_value_unit": group["trade_value_unit"].iloc[0],
            "sector_eligible_product_count": len(group),
            "connector_export_positive_gain_product_count": int(
                group["connector_export_gain_positive_flag"].sum()
            ),
            "connector_export_positive_gain_usd": float(positive_gain.sum()),
            "china_us_decline_product_count": int(china_decline.sum()),
            "china_us_decline_product_share": (
                float(china_decline.sum()) / len(group)
            ),
            "china_decline_connector_gain_product_count": int(
                rerouting.sum()
            ),
            "china_decline_connector_gain_product_share": (
                float(rerouting.sum()) / len(group)
            ),
            "china_decline_connector_gain_export_gain_share": (
                safe_divide_scalar(
                    float(positive_gain.loc[rerouting].sum()),
                    float(positive_gain.sum()),
                )
            ),
        }
        record.update(
            source_comovement_statistics(
                group, "china", "china_to_connector", config
            )
        )
        record.update(
            source_comovement_statistics(
                group, "east_asia", "east_asia_to_connector", config
            )
        )
        record["product_comovement_minimum_count"] = minimum_count
        record[
            "product_comovement_value_share_denominator"
        ] = "sum_positive_connector_export_gain_usd"
        records.append(record)
    output = pd.DataFrame.from_records(records)
    output["product_mapping_version"] = str(
        unique_scalar(product, "product_mapping_version")
    )
    output["trade_treatment_merge_version"] = str(
        unique_scalar(product, "trade_treatment_merge_version")
    )
    output["m3_reorganization_indicator_version"] = config["version"]
    output["rules_config_sha256"] = config_hash
    output["schema_version"] = config["comovement_schema_version"]

    connector_order = {
        connector: order
        for order, connector in enumerate(config["analysis"]["connectors"])
    }
    sector_order = {
        name: order
        for order, name in enumerate(config["analysis"]["sectors"])
    }
    output["_connector_order"] = output["connector_iso3"].map(connector_order)
    output["_sector_order"] = output["analysis_sector"].map(sector_order)
    output = (
        output.sort_values(
            ["_connector_order", "_sector_order"], kind="stable"
        )
        .drop(columns=["_connector_order", "_sector_order"])
        .reset_index(drop=True)
    )
    string_fields = [
        "connector_iso3",
        "analysis_sector",
        "connector_group",
        "connector_baci_code",
        "trade_value_unit",
        "product_comovement_value_share_denominator",
        "product_mapping_version",
        "trade_treatment_merge_version",
        "m3_reorganization_indicator_version",
        "rules_config_sha256",
        "schema_version",
    ]
    boolean_fields = [
        "connector_is_proxy",
        "china_correlation_low_n_flag",
        "china_weighted_correlation_low_n_flag",
        "east_asia_correlation_low_n_flag",
        "east_asia_weighted_correlation_low_n_flag",
    ]
    integer_fields = [
        field
        for field in output.columns
        if field.endswith("_count")
        or field.endswith("_product_count")
    ]
    for field in string_fields:
        output[field] = output[field].astype("string")
    for field in boolean_fields:
        output[field] = output[field].astype(bool)
    for field in integer_fields:
        output[field] = output[field].astype("int32")
    return output


def build_outputs(
    annual: pd.DataFrame,
    crosswalk: pd.DataFrame,
    comparison: pd.DataFrame,
    diagnostics: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    product, product_context, _ = build_product_output(
        annual, crosswalk, config, config_hash
    )
    sector = build_sector_output(
        product, comparison, diagnostics, config, config_hash
    )
    comovement = build_comovement_output(product, config, config_hash)
    return product, sector, comovement, product_context


def check_input_contract(
    frame: pd.DataFrame,
    schema: pa.Schema,
    input_config: dict[str, Any],
    hash_match: bool,
) -> dict[str, Any]:
    key = input_config["natural_key"]
    return {
        "hash_match": hash_match,
        "row_count": len(frame),
        "expected_row_count": int(input_config["expected_rows"]),
        "column_count": len(frame.columns),
        "expected_column_count": int(input_config["expected_columns"]),
        "duplicate_key_count": int(frame.duplicated(key).sum()),
        "arrow_schema_signature_sha256": schema_signature(schema),
        "expected_arrow_schema_signature_sha256": input_config[
            "arrow_schema_signature_sha256"
        ],
    }


def comparison_reconciliation(
    product: pd.DataFrame,
    comparison: pd.DataFrame,
) -> dict[str, Any]:
    grouped = (
        product.groupby(SECTOR_KEY, observed=True, sort=False)[
            [
                f"{flow}_value_usd_{window}"
                for flow in FLOW_NAMES
                for window in ["pre", "post"]
            ]
        ]
        .sum()
        .reset_index()
        .sort_values(SECTOR_KEY)
        .reset_index(drop=True)
    )
    source = comparison.sort_values(SECTOR_KEY).reset_index(drop=True)
    checks: dict[str, Any] = {}
    for flow in FLOW_NAMES:
        for window in ["pre", "post"]:
            field = f"{flow}_value_usd_{window}"
            gap, missing_mismatch = maximum_absolute_gap(
                grouped[field], source[field]
            )
            checks[field] = {
                "max_abs_gap_usd": gap,
                "missing_mismatch_count": missing_mismatch,
            }
    return checks


def independent_comovement_recalculation(
    product: pd.DataFrame,
    comovement: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    expected_records: list[dict[str, Any]] = []
    for (connector, sector), group in product.groupby(
        SECTOR_KEY, observed=True, sort=False
    ):
        positive_gain = group["connector_export_positive_gain_usd"]
        china_decline = group["china_us_decline_flag"]
        rerouting = group["china_decline_connector_gain_flag"]
        record: dict[str, Any] = {
            "connector_iso3": connector,
            "analysis_sector": sector,
            "connector_export_positive_gain_product_count": int(
                group["connector_export_gain_positive_flag"].sum()
            ),
            "connector_export_positive_gain_usd": float(positive_gain.sum()),
            "china_us_decline_product_count": int(china_decline.sum()),
            "china_us_decline_product_share": (
                float(china_decline.sum()) / len(group)
            ),
            "china_decline_connector_gain_product_count": int(
                rerouting.sum()
            ),
            "china_decline_connector_gain_product_share": (
                float(rerouting.sum()) / len(group)
            ),
            "china_decline_connector_gain_export_gain_share": (
                safe_divide_scalar(
                    float(positive_gain.loc[rerouting].sum()),
                    float(positive_gain.sum()),
                )
            ),
        }
        for source, flow in [
            ("china", "china_to_connector"),
            ("east_asia", "east_asia_to_connector"),
        ]:
            active = group[f"{source}_correlation_active_product_flag"]
            weight = group[f"{source}_correlation_pre_weight_usd"]
            source_change = group[f"{flow}_value_usd_change"]
            export_change = group["connector_to_usa_value_usd_change"]
            active_count = int(active.sum())
            positive_weight_count = int((active & weight.gt(0)).sum())
            minimum_count = int(
                config["product_comovement"]["correlation"][
                    "minimum_active_product_count"
                ]
            )
            minimum_weight_count = int(
                config["product_comovement"]["correlation"][
                    "minimum_positive_weight_product_count"
                ]
            )
            correlation = float("nan")
            if (
                active_count >= minimum_count
                and source_change.loc[active].nunique(dropna=True) > 1
                and export_change.loc[active].nunique(dropna=True) > 1
            ):
                correlation = float(
                    source_change.loc[active].corr(export_change.loc[active])
                )
            weighted = float("nan")
            if positive_weight_count >= minimum_weight_count:
                weighted = weighted_correlation(
                    source_change.loc[active],
                    export_change.loc[active],
                    weight.loc[active],
                )
            both = group[f"{source}_both_legs_positive_flag"]
            triple = group[f"{source}_triple_condition_flag"]
            record.update(
                {
                    f"{source}_active_product_count": active_count,
                    f"{source}_positive_weight_product_count": (
                        positive_weight_count
                    ),
                    f"{source}_correlation_low_n_flag": (
                        active_count < minimum_count
                    ),
                    f"{source}_weighted_correlation_low_n_flag": (
                        positive_weight_count < minimum_weight_count
                    ),
                    f"{source}_product_change_correlation": correlation,
                    f"{source}_weighted_product_change_correlation": weighted,
                    f"{source}_both_legs_positive_product_count": int(
                        both.sum()
                    ),
                    f"{source}_both_legs_positive_product_share": (
                        float(both.sum()) / len(group)
                    ),
                    f"{source}_both_legs_positive_active_share": (
                        safe_divide_scalar(float(both.sum()), active_count)
                    ),
                    f"{source}_both_legs_positive_export_gain_share": (
                        safe_divide_scalar(
                            float(positive_gain.loc[both].sum()),
                            float(positive_gain.sum()),
                        )
                    ),
                    f"{source}_triple_condition_product_count": int(
                        triple.sum()
                    ),
                    f"{source}_triple_condition_product_share": (
                        float(triple.sum()) / len(group)
                    ),
                    f"{source}_triple_condition_active_share": (
                        safe_divide_scalar(float(triple.sum()), active_count)
                    ),
                    f"{source}_triple_condition_export_gain_share": (
                        safe_divide_scalar(
                            float(positive_gain.loc[triple].sum()),
                            float(positive_gain.sum()),
                        )
                    ),
                }
            )
        expected_records.append(record)
    expected = (
        pd.DataFrame.from_records(expected_records)
        .sort_values(SECTOR_KEY)
        .reset_index(drop=True)
    )
    actual = comovement.sort_values(SECTOR_KEY).reset_index(drop=True)
    fields = sorted(set(expected.columns) - set(SECTOR_KEY))
    checks: dict[str, Any] = {}
    for field in fields:
        if pd.api.types.is_bool_dtype(expected[field]) or pd.api.types.is_integer_dtype(
            expected[field]
        ):
            mismatch = int(actual[field].ne(expected[field]).sum())
            checks[field] = {"mismatch_count": mismatch}
        else:
            gap, missing_mismatch = maximum_absolute_gap(
                actual[field], expected[field]
            )
            checks[field] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing_mismatch,
            }
    return checks


def independent_exposure_recalculation(
    product: pd.DataFrame,
    sector: pd.DataFrame,
) -> dict[str, Any]:
    expected_records: list[dict[str, Any]] = []
    for (connector, sector_name), group in product.groupby(
        SECTOR_KEY, observed=True, sort=False
    ):
        eligible_count = len(group)
        tariffed = group["post_tariffed_product_flag"]
        observed = group["post_tariff_exposure_observed"]
        positive = group["positive_exposure_flag"].fillna(False)
        top = group["top_quartile_positive_exposure_flag"].fillna(False)
        export_pre = group["connector_to_usa_value_usd_pre"].astype("float64")
        export_post = group[
            "connector_to_usa_value_usd_post"
        ].astype("float64")
        exposure = group["post_tariff_exposure_mean"].astype("float64")
        positive_gain = group[
            "connector_export_positive_gain_usd"
        ].astype("float64")
        tariffed_pre = float(export_pre.loc[tariffed].sum())
        tariffed_post = float(export_post.loc[tariffed].sum())
        observed_pre = float(export_pre.loc[observed].sum())
        observed_post = float(export_post.loc[observed].sum())
        exposure_numerator_pre = float(
            (export_pre.loc[observed] * exposure.loc[observed]).sum()
        )
        exposure_numerator_post = float(
            (export_post.loc[observed] * exposure.loc[observed]).sum()
        )
        gain_total = float(positive_gain.sum())
        gain_observed = float(positive_gain.loc[observed].sum())
        gain_positive = float(positive_gain.loc[positive].sum())
        gain_top = float(positive_gain.loc[top].sum())
        overlap_pre = safe_divide_scalar(
            tariffed_pre, float(export_pre.sum())
        )
        overlap_post = safe_divide_scalar(
            tariffed_post, float(export_post.sum())
        )
        weighted_pre = safe_divide_scalar(
            exposure_numerator_pre, observed_pre
        )
        weighted_post = safe_divide_scalar(
            exposure_numerator_post, observed_post
        )
        expected_records.append(
            {
                "connector_iso3": connector,
                "analysis_sector": sector_name,
                "post_tariffed_product_count": int(tariffed.sum()),
                "post_tariffed_product_share": (
                    float(tariffed.sum()) / eligible_count
                ),
                "post_exposure_observed_product_count": int(observed.sum()),
                "post_exposure_missing_product_count": int(
                    (~observed).sum()
                ),
                "post_exposure_missing_product_share": (
                    float((~observed).sum()) / eligible_count
                ),
                "positive_exposure_product_count": int(positive.sum()),
                "positive_exposure_product_share": (
                    float(positive.sum()) / eligible_count
                ),
                "top_quartile_positive_exposure_product_count": int(
                    top.sum()
                ),
                "top_quartile_positive_exposure_product_share": (
                    float(top.sum()) / eligible_count
                ),
                "sector_positive_exposure_p75_cutoff": float(
                    group[
                        "sector_positive_exposure_p75_cutoff"
                    ].iloc[0]
                ),
                "connector_export_tariffed_value_usd_pre": tariffed_pre,
                "connector_export_tariffed_value_usd_post": tariffed_post,
                "connector_export_tariff_overlap_pre": overlap_pre,
                "connector_export_tariff_overlap_post": overlap_post,
                "connector_export_tariff_overlap_change": (
                    overlap_post - overlap_pre
                ),
                "exposure_observed_export_value_usd_pre": observed_pre,
                "exposure_observed_export_value_usd_post": observed_post,
                "connector_export_exposure_observed_value_share_pre": (
                    safe_divide_scalar(observed_pre, float(export_pre.sum()))
                ),
                "connector_export_exposure_observed_value_share_post": (
                    safe_divide_scalar(
                        observed_post, float(export_post.sum())
                    )
                ),
                "connector_export_exposure_numerator_usd_pre": (
                    exposure_numerator_pre
                ),
                "connector_export_exposure_numerator_usd_post": (
                    exposure_numerator_post
                ),
                "connector_export_exposure_weighted_pre": weighted_pre,
                "connector_export_exposure_weighted_post": weighted_post,
                "connector_export_exposure_weighted_change": (
                    weighted_post - weighted_pre
                ),
                "connector_export_positive_gain_exposure_observed_usd": (
                    gain_observed
                ),
                "connector_export_positive_gain_exposure_observed_share": (
                    safe_divide_scalar(gain_observed, gain_total)
                ),
                "connector_export_positive_gain_in_positive_exposure_usd": (
                    gain_positive
                ),
                "gain_in_positive_exposure_products_share": (
                    safe_divide_scalar(gain_positive, gain_observed)
                ),
                "connector_export_positive_gain_in_top_quartile_exposure_usd": (
                    gain_top
                ),
                "gain_in_top_quartile_exposure_products_share": (
                    safe_divide_scalar(gain_top, gain_observed)
                ),
            }
        )
    expected = (
        pd.DataFrame.from_records(expected_records)
        .sort_values(SECTOR_KEY)
        .reset_index(drop=True)
    )
    actual = sector.sort_values(SECTOR_KEY).reset_index(drop=True)
    checks: dict[str, Any] = {}
    for field in sorted(set(expected.columns) - set(SECTOR_KEY)):
        if pd.api.types.is_integer_dtype(expected[field]):
            checks[field] = {
                "mismatch_count": int(actual[field].ne(expected[field]).sum())
            }
        else:
            gap, missing_mismatch = maximum_absolute_gap(
                actual[field], expected[field]
            )
            checks[field] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing_mismatch,
            }
    return checks


def validate(
    annual: pd.DataFrame,
    annual_schema: pa.Schema,
    crosswalk: pd.DataFrame,
    crosswalk_schema: pa.Schema,
    comparison: pd.DataFrame,
    comparison_schema: pa.Schema,
    diagnostics: pd.DataFrame,
    diagnostics_schema: pa.Schema,
    time_windows: dict[str, Any],
    product: pd.DataFrame,
    sector: pd.DataFrame,
    comovement: pd.DataFrame,
    product_context: dict[str, Any],
    config: dict[str, Any],
    input_hash_matches: dict[str, bool],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    inputs = config["inputs"]
    input_contracts = {
        "connector_trade_hs6_year": check_input_contract(
            annual,
            annual_schema,
            inputs["connector_trade_hs6_year"],
            input_hash_matches["connector_trade_hs6_year"],
        ),
        "product_sector_crosswalk": check_input_contract(
            crosswalk,
            crosswalk_schema,
            inputs["product_sector_crosswalk"],
            input_hash_matches["product_sector_crosswalk"],
        ),
        "connector_trade_sector_window_comparison": check_input_contract(
            comparison,
            comparison_schema,
            inputs["connector_trade_sector_window_comparison"],
            input_hash_matches[
                "connector_trade_sector_window_comparison"
            ],
        ),
        "connector_trade_sector_growth_diagnostics": check_input_contract(
            diagnostics,
            diagnostics_schema,
            inputs["connector_trade_sector_growth_diagnostics"],
            input_hash_matches[
                "connector_trade_sector_growth_diagnostics"
            ],
        ),
    }
    for name, contract in input_contracts.items():
        if not contract["hash_match"]:
            failures.append(f"{name} frozen SHA256 does not match")
        if contract["row_count"] != contract["expected_row_count"]:
            failures.append(f"{name} row count does not match")
        if contract["column_count"] != contract["expected_column_count"]:
            failures.append(f"{name} column count does not match")
        if contract["duplicate_key_count"]:
            failures.append(f"{name} natural key is duplicated")
        if (
            contract["arrow_schema_signature_sha256"]
            != contract["expected_arrow_schema_signature_sha256"]
        ):
            failures.append(f"{name} Arrow schema does not match")
    if not input_hash_matches["time_windows"]:
        failures.append("time_windows frozen SHA256 does not match")

    version_checks = {
        "annual_trade_panel_version": (
            annual["trade_panel_version"].nunique(dropna=False) == 1
            and str(annual["trade_panel_version"].iloc[0])
            == inputs["connector_trade_hs6_year"][
                "expected_trade_panel_version"
            ]
        ),
        "annual_merge_version": (
            annual["trade_treatment_merge_version"].nunique(dropna=False) == 1
            and str(annual["trade_treatment_merge_version"].iloc[0])
            == inputs["connector_trade_hs6_year"]["expected_merge_version"]
        ),
        "crosswalk_mapping_version": (
            crosswalk["mapping_version"].nunique(dropna=False) == 1
            and str(crosswalk["mapping_version"].iloc[0])
            == inputs["product_sector_crosswalk"]["expected_mapping_version"]
        ),
        "comparison_schema_version": (
            comparison["schema_version"].nunique(dropna=False) == 1
            and str(comparison["schema_version"].iloc[0])
            == inputs["connector_trade_sector_window_comparison"][
                "expected_schema_version"
            ]
        ),
        "comparison_construction_version": (
            comparison["m3_window_construction_version"].nunique(
                dropna=False
            )
            == 1
            and str(comparison["m3_window_construction_version"].iloc[0])
            == inputs["connector_trade_sector_window_comparison"][
                "expected_construction_version"
            ]
        ),
        "diagnostics_schema_version": (
            diagnostics["schema_version"].nunique(dropna=False) == 1
            and str(diagnostics["schema_version"].iloc[0])
            == inputs["connector_trade_sector_growth_diagnostics"][
                "expected_schema_version"
            ]
        ),
        "diagnostics_construction_version": (
            diagnostics["m3_growth_diagnostic_version"].nunique(
                dropna=False
            )
            == 1
            and str(diagnostics["m3_growth_diagnostic_version"].iloc[0])
            == inputs["connector_trade_sector_growth_diagnostics"][
                "expected_construction_version"
            ]
        ),
    }
    if not all(version_checks.values()):
        failures.append("one or more frozen input version checks failed")

    frozen_window_checks = {
        window: (
            int(time_windows[f"{window}_period"]["start"])
            == int(config["windows"][window]["start"])
            and int(time_windows[f"{window}_period"]["end"])
            == int(config["windows"][window]["end"])
        )
        for window in ["pre", "post"]
    }
    if not all(frozen_window_checks.values()):
        failures.append("M3.4 windows differ from the canonical window config")

    output_key_duplicates = {
        "product": int(
            product.duplicated(
                config["outputs"]["product"]["natural_key"]
            ).sum()
        ),
        "sector": int(
            sector.duplicated(
                config["outputs"]["sector"]["natural_key"]
            ).sum()
        ),
        "comovement": int(
            comovement.duplicated(
                config["outputs"]["comovement"]["natural_key"]
            ).sum()
        ),
    }
    output_rows = {
        "product": len(product),
        "sector": len(sector),
        "comovement": len(comovement),
    }
    output_columns = {
        "product": len(product.columns),
        "sector": len(sector.columns),
        "comovement": len(comovement.columns),
    }
    for output_name in ["product", "sector", "comovement"]:
        if output_rows[output_name] != int(
            config["outputs"][output_name]["expected_rows"]
        ):
            failures.append(f"{output_name} output row count does not match")
        if output_key_duplicates[output_name]:
            failures.append(f"{output_name} output natural key is duplicated")

    expected_connectors = sorted(config["analysis"]["connectors"])
    expected_sectors = sorted(config["analysis"]["sectors"])
    universe_checks = {
        "connectors_match": (
            sorted(product["connector_iso3"].unique().tolist())
            == expected_connectors
        ),
        "sectors_match": (
            sorted(product["analysis_sector"].unique().tolist())
            == expected_sectors
        ),
        "eligible_product_count": int(product["analysis_hs6"].nunique()),
    }
    if (
        not universe_checks["connectors_match"]
        or not universe_checks["sectors_match"]
        or universe_checks["eligible_product_count"]
        != int(config["analysis"]["expected_eligible_product_count"])
    ):
        failures.append("M3.4 connector, sector, or product universe changed")

    join_context = product_context["join"]
    if any(join_context.values()):
        failures.append("annual panel and canonical crosswalk do not reconcile")
    observed_year_checks = {
        "pre_minimum": int(product["pre_observed_year_count"].min()),
        "pre_maximum": int(product["pre_observed_year_count"].max()),
        "post_minimum": int(product["post_observed_year_count"].min()),
        "post_maximum": int(product["post_observed_year_count"].max()),
    }
    if (
        observed_year_checks["pre_minimum"]
        != int(config["windows"]["pre"]["expected_year_count"])
        or observed_year_checks["pre_maximum"]
        != int(config["windows"]["pre"]["expected_year_count"])
        or observed_year_checks["post_minimum"]
        != int(config["windows"]["post"]["expected_year_count"])
        or observed_year_checks["post_maximum"]
        != int(config["windows"]["post"]["expected_year_count"])
    ):
        failures.append("one or more product cells have incomplete windows")

    eligible_counts = (
        product.loc[product["connector_iso3"].eq(expected_connectors[0])]
        .groupby("analysis_sector", observed=True)["analysis_hs6"]
        .nunique()
        .to_dict()
    )
    if eligible_counts != config["analysis"]["eligible_products_by_sector"]:
        failures.append("eligible HS6 count by sector changed")

    value_tolerance = float(config["validation"]["value_tolerance_usd"])
    ratio_tolerance = float(config["validation"]["ratio_tolerance"])
    product_formula_checks: dict[str, Any] = {}
    for flow in FLOW_NAMES:
        expected_change = (
            product[f"{flow}_value_usd_post"]
            - product[f"{flow}_value_usd_pre"]
        )
        gap, missing_mismatch = maximum_absolute_gap(
            product[f"{flow}_value_usd_change"], expected_change
        )
        product_formula_checks[flow] = {
            "change_max_abs_gap_usd": gap,
            "missing_mismatch_count": missing_mismatch,
        }
        if gap > value_tolerance or missing_mismatch:
            failures.append(f"{flow} product change formula failed")
    sector_sum_reconciliation = comparison_reconciliation(
        product, comparison
    )
    if any(
        check["max_abs_gap_usd"] > value_tolerance
        or check["missing_mismatch_count"]
        for check in sector_sum_reconciliation.values()
    ):
        failures.append("product-to-sector trade values do not reconcile")

    china_common_fields = [
        "china_to_usa_value_usd_pre",
        "china_to_usa_value_usd_post",
        "china_to_usa_value_usd_change",
        "post_tariffed_year_share",
        "post_tariff_exposure_mean",
        "post_policy_mapping_status",
    ]
    common_field_inconsistencies = {
        field: int(
            product.groupby("analysis_hs6", observed=True)[field]
            .nunique(dropna=False)
            .gt(1)
            .sum()
        )
        for field in china_common_fields
    }
    if any(common_field_inconsistencies.values()):
        failures.append("common product benchmarks vary across connectors")
    repeated_policy_inconsistencies = product_context["policy"][
        "repeated_field_inconsistencies"
    ]
    if any(repeated_policy_inconsistencies.values()):
        failures.append("annual policy fields vary across connectors")

    reference_products = product.loc[
        product["connector_iso3"].eq(expected_connectors[0])
    ]
    exposure_counts: dict[str, Any] = {}
    for sector_name, expected in config["exposure_overlap"][
        "expected_product_counts_by_sector"
    ].items():
        group = reference_products.loc[
            reference_products["analysis_sector"].eq(sector_name)
        ]
        observed = group["post_tariff_exposure_observed"]
        counts = {
            "tariffed": int(group["post_tariffed_product_flag"].sum()),
            "exposure_observed": int(observed.sum()),
            "exposure_missing": int((~observed).sum()),
            "positive_exposure": int(
                group["positive_exposure_flag"].fillna(False).sum()
            ),
            "top_quartile_positive_exposure": int(
                group["top_quartile_positive_exposure_flag"]
                .fillna(False)
                .sum()
            ),
        }
        exposure_counts[sector_name] = counts
        if counts != expected:
            failures.append(f"{sector_name} exposure product counts changed")
    missing_exposure_count = int(
        reference_products["post_tariff_exposure_mean"].isna().sum()
    )
    tariffed_missing_exposure_count = int(
        (
            reference_products["post_tariffed_product_flag"]
            & reference_products["post_tariff_exposure_mean"].isna()
        ).sum()
    )
    fractional_tariff_status_count = int(
        (
            reference_products["post_tariffed_year_share"].notna()
            & ~reference_products["post_tariffed_year_share"].isin([0.0, 1.0])
        ).sum()
    )
    nullable_exposure_flag_missing_count = int(
        product["positive_exposure_flag"].isna().sum()
    )
    if (
        missing_exposure_count
        != int(
            config["exposure_overlap"][
                "expected_missing_exposure_product_count"
            ]
        )
        or tariffed_missing_exposure_count
        != int(
            config["exposure_overlap"][
                "expected_tariffed_missing_exposure_product_count"
            ]
        )
        or fractional_tariff_status_count
        != int(
            config["exposure_overlap"][
                "expected_fractional_post_tariff_status_count"
            ]
        )
        or nullable_exposure_flag_missing_count
        != missing_exposure_count * len(expected_connectors)
    ):
        failures.append("missing or fractional policy exposure states changed")

    sector_sorted = sector.sort_values(SECTOR_KEY).reset_index(drop=True)
    recomputed_decline = (
        sector_sorted["china_us_value_usd_pre"]
        - sector_sorted["china_us_value_usd_post"]
    ).clip(lower=0)
    recomputed_gain = (
        sector_sorted["connector_us_value_usd_post"]
        - sector_sorted["connector_us_value_usd_pre"]
    )
    recomputed_defined = recomputed_decline.gt(
        float(config["replacement"]["denominator_threshold_usd"])
    )
    recomputed_ratio = pd.Series(np.nan, index=sector_sorted.index)
    recomputed_ratio.loc[recomputed_defined] = (
        recomputed_gain.loc[recomputed_defined]
        / recomputed_decline.loc[recomputed_defined]
    )
    replacement_checks = {
        "decline_max_abs_gap_usd": maximum_absolute_gap(
            sector_sorted["china_us_decline_usd"], recomputed_decline
        )[0],
        "gain_max_abs_gap_usd": maximum_absolute_gap(
            sector_sorted["connector_us_gain_usd"], recomputed_gain
        )[0],
        "defined_mismatch_count": int(
            sector_sorted["replacement_ratio_defined"]
            .ne(recomputed_defined)
            .sum()
        ),
        "ratio_max_abs_gap": maximum_absolute_gap(
            sector_sorted["replacement_ratio"], recomputed_ratio
        )[0],
        "ratio_missing_mismatch_count": maximum_absolute_gap(
            sector_sorted["replacement_ratio"], recomputed_ratio
        )[1],
        "defined_count": int(recomputed_defined.sum()),
        "candidate_count": int(
            (recomputed_defined & recomputed_gain.gt(0)).sum()
        ),
        "negative_gain_with_defined_denominator_count": int(
            (recomputed_defined & recomputed_gain.lt(0)).sum()
        ),
        "undefined_ratio_missing_count": int(
            sector_sorted.loc[
                ~recomputed_defined, "replacement_ratio"
            ].isna().sum()
        ),
    }
    if (
        replacement_checks["decline_max_abs_gap_usd"] > value_tolerance
        or replacement_checks["gain_max_abs_gap_usd"] > value_tolerance
        or replacement_checks["defined_mismatch_count"]
        or replacement_checks["ratio_max_abs_gap"] > ratio_tolerance
        or replacement_checks["ratio_missing_mismatch_count"]
        or replacement_checks["defined_count"]
        != int(
            config["validation"][
                "expected_replacement_ratio_defined_count"
            ]
        )
        or replacement_checks["candidate_count"]
        != int(
            config["validation"][
                "expected_import_replacement_candidate_count"
            ]
        )
        or replacement_checks[
            "negative_gain_with_defined_denominator_count"
        ]
        != int(
            config["validation"][
                "expected_negative_connector_gain_with_defined_denominator_count"
            ]
        )
    ):
        failures.append("replacement formula or frozen counts failed")

    source_ratio_checks: dict[str, Any] = {}
    for source, prefix in [
        ("china", "china_input"),
        ("east_asia", "east_asia_input"),
    ]:
        checks: dict[str, Any] = {}
        for window in ["pre", "post"]:
            denominator = sector_sorted[
                f"connector_us_value_usd_{window}"
            ]
            expected_defined = denominator.gt(0)
            expected_ratio = pd.Series(np.nan, index=sector_sorted.index)
            expected_ratio.loc[expected_defined] = (
                sector_sorted.loc[
                    expected_defined, f"{prefix}_value_usd_{window}"
                ]
                / denominator.loc[expected_defined]
            )
            gap, missing_mismatch = maximum_absolute_gap(
                sector_sorted[
                    f"{source}_input_to_export_ratio_{window}"
                ],
                expected_ratio,
            )
            defined_mismatch = int(
                sector_sorted[
                    f"{source}_input_to_export_ratio_{window}_defined"
                ]
                .ne(expected_defined)
                .sum()
            )
            checks[window] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing_mismatch,
                "defined_mismatch_count": defined_mismatch,
                "defined_count": int(expected_defined.sum()),
            }
            if (
                gap > ratio_tolerance
                or missing_mismatch
                or defined_mismatch
                or int(expected_defined.sum())
                != int(
                    config["validation"][
                        "expected_source_ratio_defined_count_by_source"
                    ][source]
                )
            ):
                failures.append(
                    f"{source} {window} input-to-export ratio failed"
                )
        expected_change = (
            sector_sorted[f"{source}_input_to_export_ratio_post"]
            - sector_sorted[f"{source}_input_to_export_ratio_pre"]
        )
        change_gap, change_missing = maximum_absolute_gap(
            sector_sorted[f"{source}_input_to_export_ratio_change"],
            expected_change,
        )
        checks["change"] = {
            "max_abs_gap": change_gap,
            "missing_mismatch_count": change_missing,
        }
        if change_gap > ratio_tolerance or change_missing:
            failures.append(f"{source} input-to-export ratio change failed")
        source_ratio_checks[source] = checks

    diagnostic_reconciliation: dict[str, Any] = {}
    for flow_id, prefix in [
        ("connector_to_usa", "connector_export"),
        ("china_to_connector", "china_input"),
        ("east_asia_to_connector", "east_asia_input"),
    ]:
        source = (
            diagnostics.loc[diagnostics["flow_id"].eq(flow_id)]
            .sort_values(SECTOR_KEY)
            .reset_index(drop=True)
        )
        checks: dict[str, Any] = {}
        for actual_field, source_field in [
            (
                f"{prefix}_dh_growth_raw",
                "value_usd_dh_growth_post_pre_raw",
            ),
            (
                f"{prefix}_log_growth_raw",
                "value_usd_log_growth_post_pre_raw",
            ),
        ]:
            gap, missing_mismatch = maximum_absolute_gap(
                sector_sorted[actual_field], source[source_field]
            )
            checks[actual_field] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing_mismatch,
            }
            if gap > ratio_tolerance or missing_mismatch:
                failures.append(f"{actual_field} does not match M3.3")
        for actual_field, source_field in [
            (f"{prefix}_small_base_flag", "small_base_flag"),
            (
                f"{prefix}_dh_primary_eligible",
                "dh_growth_primary_eligible",
            ),
            (f"{prefix}_abnormal_growth_flag", "abnormal_growth_flag"),
        ]:
            mismatch = int(
                sector_sorted[actual_field].ne(source[source_field]).sum()
            )
            checks[actual_field] = {"mismatch_count": mismatch}
            if mismatch:
                failures.append(f"{actual_field} does not match M3.3")
        diagnostic_reconciliation[flow_id] = checks

    share_fields = [
        field for field in sector.columns if field.endswith("_share")
    ] + [
        "connector_export_tariff_overlap_pre",
        "connector_export_tariff_overlap_post",
    ]
    sector_share_out_of_bounds_count = int(
        sum(
            (
                sector[field].notna()
                & (sector[field].lt(-ratio_tolerance)
                   | sector[field].gt(1 + ratio_tolerance))
            ).sum()
            for field in share_fields
        )
    )
    if sector_share_out_of_bounds_count:
        failures.append("one or more sector overlap shares are outside [0,1]")
    positive_gain_denominator_zero_count = int(
        comovement["connector_export_positive_gain_usd"].eq(0).sum()
    )
    exposure_observed_gain_denominator_zero_count = int(
        sector[
            "connector_export_positive_gain_exposure_observed_usd"
        ].eq(0).sum()
    )
    if (
        positive_gain_denominator_zero_count
        != int(
            config["validation"][
                "expected_positive_export_gain_denominator_zero_count"
            ]
        )
        or exposure_observed_gain_denominator_zero_count
        != int(
            config["validation"][
                "expected_exposure_observed_gain_denominator_zero_count"
            ]
        )
    ):
        failures.append("positive-gain exposure denominator state changed")

    exposure_count_inconsistencies = {
        field: int(
            sector.groupby("analysis_sector", observed=True)[field]
            .nunique(dropna=False)
            .gt(1)
            .sum()
        )
        for field in [
            "post_tariffed_product_count",
            "post_exposure_observed_product_count",
            "post_exposure_missing_product_count",
            "positive_exposure_product_count",
            "top_quartile_positive_exposure_product_count",
            "sector_positive_exposure_p75_cutoff",
        ]
    }
    if any(exposure_count_inconsistencies.values()):
        failures.append("policy product counts vary across connectors")
    independent_exposure = independent_exposure_recalculation(
        product, sector
    )
    exposure_value_fields = {
        field
        for field in independent_exposure
        if field.endswith("_usd_pre")
        or field.endswith("_usd_post")
        or field.endswith("_usd")
    }
    if any(
        check.get("mismatch_count", 0)
        or check.get("missing_mismatch_count", 0)
        or check.get("max_abs_gap", 0)
        > (
            value_tolerance
            if field in exposure_value_fields
            else ratio_tolerance
        )
        for field, check in independent_exposure.items()
    ):
        failures.append("exposure-overlap formulas failed recomputation")

    independent_comovement = independent_comovement_recalculation(
        product, comovement, config
    )
    if any(
        check.get("mismatch_count", 0)
        or check.get("missing_mismatch_count", 0)
        or check.get("max_abs_gap", 0) > ratio_tolerance
        for check in independent_comovement.values()
    ):
        failures.append("product co-movement formulas failed recomputation")
    correlation_counts: dict[str, Any] = {}
    for source in ["china", "east_asia"]:
        counts = {
            "correlation_defined": int(
                comovement[f"{source}_product_change_correlation"]
                .notna()
                .sum()
            ),
            "weighted_correlation_defined": int(
                comovement[
                    f"{source}_weighted_product_change_correlation"
                ]
                .notna()
                .sum()
            ),
            "low_n": int(
                comovement[f"{source}_correlation_low_n_flag"].sum()
            ),
            "weighted_low_n": int(
                comovement[
                    f"{source}_weighted_correlation_low_n_flag"
                ].sum()
            ),
            "minimum_active_product_count": int(
                comovement[f"{source}_active_product_count"].min()
            ),
            "minimum_positive_weight_product_count": int(
                comovement[
                    f"{source}_positive_weight_product_count"
                ].min()
            ),
        }
        correlation_counts[source] = counts
        if (
            counts["correlation_defined"]
            != int(
                config["validation"][
                    "expected_correlation_defined_count_by_source"
                ][source]
            )
            or counts["weighted_correlation_defined"]
            != int(
                config["validation"][
                    "expected_weighted_correlation_defined_count_by_source"
                ][source]
            )
            or counts["low_n"]
            != int(
                config["validation"]["expected_low_n_count_by_source"][
                    source
                ]
            )
            or counts["weighted_low_n"]
            != int(
                config["validation"]["expected_low_n_count_by_source"][
                    source
                ]
            )
        ):
            failures.append(f"{source} correlation availability changed")
    correlation_fields = [
        field
        for field in comovement.columns
        if field.endswith("_correlation")
    ]
    correlation_out_of_bounds_count = int(
        sum(
            (
                comovement[field].notna()
                & comovement[field].abs().gt(1 + ratio_tolerance)
            ).sum()
            for field in correlation_fields
        )
    )
    comovement_share_fields = [
        field for field in comovement.columns if field.endswith("_share")
    ]
    comovement_share_out_of_bounds_count = int(
        sum(
            (
                comovement[field].notna()
                & (comovement[field].lt(-ratio_tolerance)
                   | comovement[field].gt(1 + ratio_tolerance))
            ).sum()
            for field in comovement_share_fields
        )
    )
    if correlation_out_of_bounds_count or comovement_share_out_of_bounds_count:
        failures.append("correlations or co-movement shares are out of bounds")

    twn_checks = {
        "product_rows": int(product["connector_iso3"].eq("TWN").sum()),
        "sector_rows": int(sector["connector_iso3"].eq("TWN").sum()),
        "comovement_rows": int(
            comovement["connector_iso3"].eq("TWN").sum()
        ),
        "product_proxy_false_count": int(
            (
                product["connector_iso3"].eq("TWN")
                & ~product["connector_is_proxy"]
            ).sum()
        ),
        "sector_proxy_false_count": int(
            (
                sector["connector_iso3"].eq("TWN")
                & ~sector["connector_is_proxy"]
            ).sum()
        ),
        "comovement_proxy_false_count": int(
            (
                comovement["connector_iso3"].eq("TWN")
                & ~comovement["connector_is_proxy"]
            ).sum()
        ),
    }
    if (
        twn_checks["product_rows"]
        != int(config["validation"]["expected_twn_product_rows"])
        or twn_checks["sector_rows"]
        != int(config["validation"]["expected_twn_sector_rows"])
        or twn_checks["comovement_rows"]
        != int(config["validation"]["expected_twn_comovement_rows"])
        or twn_checks["product_proxy_false_count"]
        or twn_checks["sector_proxy_false_count"]
        or twn_checks["comovement_proxy_false_count"]
    ):
        failures.append("TWN rows or proxy flags are incomplete")

    alias_checks = {
        output_name: alias_validation(
            frame,
            config["outputs"][output_name]["stata_aliases"],
        )
        for output_name, frame in [
            ("product", product),
            ("sector", sector),
            ("comovement", comovement),
        ]
    }
    if not all(check["pass"] for check in alias_checks.values()):
        failures.append("one or more Stata alias maps failed")

    metadata_checks: dict[str, Any] = {}
    for output_name, frame in [
        ("product", product),
        ("sector", sector),
        ("comovement", comovement),
    ]:
        fields = [
            "product_mapping_version",
            "trade_treatment_merge_version",
            "m3_reorganization_indicator_version",
            "rules_config_sha256",
            "schema_version",
        ]
        metadata_checks[output_name] = {
            field: {
                "missing_count": int(frame[field].isna().sum()),
                "unique_count": int(frame[field].nunique(dropna=False)),
            }
            for field in fields
        }
        if any(
            detail["missing_count"] or detail["unique_count"] != 1
            for detail in metadata_checks[output_name].values()
        ):
            failures.append(f"{output_name} version metadata is incomplete")
    infinite_numeric_counts = {
        output_name: int(
            np.isinf(frame.select_dtypes(include=[np.number]).to_numpy()).sum()
        )
        for output_name, frame in [
            ("product", product),
            ("sector", sector),
            ("comovement", comovement),
        ]
    }
    if any(infinite_numeric_counts.values()):
        failures.append("one or more outputs contain infinite numeric values")

    if not determinism["all_sha256_match"]:
        failures.append("deterministic Parquet SHA256 checks failed")
    if not determinism["temporary_output_cleaned"]:
        failures.append("determinism temporary directory was not cleaned")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_contracts": input_contracts,
        "time_windows_hash_match": input_hash_matches["time_windows"],
        "input_version_checks": version_checks,
        "frozen_window_checks": frozen_window_checks,
        "output_row_counts": output_rows,
        "output_column_counts": output_columns,
        "output_duplicate_key_counts": output_key_duplicates,
        "universe_checks": universe_checks,
        "canonical_crosswalk_join": join_context,
        "observed_year_checks": observed_year_checks,
        "eligible_product_counts_by_sector": eligible_counts,
        "product_formula_checks": product_formula_checks,
        "product_to_sector_reconciliation": sector_sum_reconciliation,
        "common_product_field_inconsistencies": (
            common_field_inconsistencies
        ),
        "annual_policy_field_inconsistencies": (
            repeated_policy_inconsistencies
        ),
        "exposure_product_counts_by_sector": exposure_counts,
        "missing_exposure_product_count": missing_exposure_count,
        "tariffed_missing_exposure_product_count": (
            tariffed_missing_exposure_count
        ),
        "fractional_post_tariff_status_count": (
            fractional_tariff_status_count
        ),
        "nullable_exposure_flag_missing_count": (
            nullable_exposure_flag_missing_count
        ),
        "replacement_checks": replacement_checks,
        "source_ratio_checks": source_ratio_checks,
        "m3_3_diagnostic_reconciliation": diagnostic_reconciliation,
        "sector_share_out_of_bounds_count": (
            sector_share_out_of_bounds_count
        ),
        "positive_export_gain_denominator_zero_count": (
            positive_gain_denominator_zero_count
        ),
        "exposure_observed_gain_denominator_zero_count": (
            exposure_observed_gain_denominator_zero_count
        ),
        "policy_count_inconsistencies_across_connectors": (
            exposure_count_inconsistencies
        ),
        "independent_exposure_formula_checks": independent_exposure,
        "independent_comovement_formula_checks": (
            independent_comovement
        ),
        "correlation_counts": correlation_counts,
        "correlation_out_of_bounds_count": (
            correlation_out_of_bounds_count
        ),
        "comovement_share_out_of_bounds_count": (
            comovement_share_out_of_bounds_count
        ),
        "twn_checks": twn_checks,
        "stata_alias_validation": alias_checks,
        "metadata_checks": metadata_checks,
        "infinite_numeric_counts": infinite_numeric_counts,
        "determinism_check": determinism,
        "value_tolerance_usd": value_tolerance,
        "ratio_tolerance": ratio_tolerance,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    outputs = validation["outputs"]
    lines = [
        "# M3.4 Trade Reorganization Indicators Validation",
        "",
        "## Material Passport",
        "",
        "- Origin Skill: `academic-research-suite/experiment-agent`",
        "- Origin Mode: `run + validate`",
        f"- Origin Date: `{validation['generated_at_utc'][:10]}`",
        f"- Verification Status: `{'VERIFIED' if validation['validation_status'] == 'PASS' else 'BLOCKED'}`",
        f"- Version Label: `{validation['construction_version']}`",
        "",
        "## Result",
        "",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Product window output: `{outputs['product']['path']}`; "
        f"`{validation['output_row_counts']['product']} × "
        f"{validation['output_column_counts']['product']}`; SHA256 "
        f"`{outputs['product']['sha256']}`.",
        f"- Sector indicator output: `{outputs['sector']['path']}`; "
        f"`{validation['output_row_counts']['sector']} × "
        f"{validation['output_column_counts']['sector']}`; SHA256 "
        f"`{outputs['sector']['sha256']}`.",
        f"- Product co-movement output: `{outputs['comovement']['path']}`; "
        f"`{validation['output_row_counts']['comovement']} × "
        f"{validation['output_column_counts']['comovement']}`; SHA256 "
        f"`{outputs['comovement']['sha256']}`.",
        "",
        "## Frozen input and structural gates",
        "",
        f"- Frozen hashes and schemas: `{'pass' if all(x['hash_match'] and x['arrow_schema_signature_sha256'] == x['expected_arrow_schema_signature_sha256'] for x in validation['input_contracts'].values()) and validation['time_windows_hash_match'] else 'fail'}`.",
        f"- Output duplicate keys (product / sector / co-movement): "
        f"`{validation['output_duplicate_key_counts']['product']} / "
        f"{validation['output_duplicate_key_counts']['sector']} / "
        f"{validation['output_duplicate_key_counts']['comovement']}`.",
        f"- Eligible products and sectors: "
        f"`{validation['universe_checks']['eligible_product_count']} / "
        f"{len(validation['eligible_product_counts_by_sector'])}`.",
        f"- Product windows observed years (pre min/max; post min/max): "
        f"`{validation['observed_year_checks']['pre_minimum']}/"
        f"{validation['observed_year_checks']['pre_maximum']}; "
        f"{validation['observed_year_checks']['post_minimum']}/"
        f"{validation['observed_year_checks']['post_maximum']}`.",
        f"- Maximum product-to-sector value reconciliation gap: "
        f"`{max(x['max_abs_gap_usd'] for x in validation['product_to_sector_reconciliation'].values()):.12f}` USD.",
        f"- Deterministic hashes all match: "
        f"`{'yes' if validation['determinism_check']['all_sha256_match'] else 'no'}`.",
        "",
        "## Replacement indicator",
        "",
        "- Denominator: `max(China→USA pre − post, 0)`.",
        "- The ratio is defined only when that decline is strictly greater than USD 25 million.",
        "- Numerator: signed connector→USA post-minus-pre gain. Negative gains remain negative; no epsilon and no cap are used.",
        f"- Defined ratios / positive-gain candidates / defined denominators with negative gains: "
        f"`{validation['replacement_checks']['defined_count']} / "
        f"{validation['replacement_checks']['candidate_count']} / "
        f"{validation['replacement_checks']['negative_gain_with_defined_denominator_count']}`.",
        f"- Undefined ratios retained as missing: "
        f"`{validation['replacement_checks']['undefined_ratio_missing_count']}`.",
        "",
        "## Source-input and export relationships",
        "",
        "- China and extended East Asia are kept as separate source concepts.",
        "- Each source-input/export ratio uses connector→USA exports in the same window as denominator and is defined only for a strictly positive denominator.",
        f"- China pre/post defined counts: "
        f"`{validation['source_ratio_checks']['china']['pre']['defined_count']} / "
        f"{validation['source_ratio_checks']['china']['post']['defined_count']}`.",
        f"- East Asia pre/post defined counts: "
        f"`{validation['source_ratio_checks']['east_asia']['pre']['defined_count']} / "
        f"{validation['source_ratio_checks']['east_asia']['post']['defined_count']}`.",
        "",
        "## Section 301 exposure overlap",
        "",
        f"- Products with missing post exposure: "
        f"`{validation['missing_exposure_product_count']}`; tariffed products among them: "
        f"`{validation['tariffed_missing_exposure_product_count']}`.",
        f"- Fractional post tariff-status products: "
        f"`{validation['fractional_post_tariff_status_count']}`.",
        "- Missing exposure is preserved as missing and excluded from exposure-weighted denominators; it is never converted to zero.",
        "- Both positive exposure and the within-sector p75 of positive exposure are reported. These definitions are not substituted for tariffed status.",
        f"- Sector share values outside [0,1]: "
        f"`{validation['sector_share_out_of_bounds_count']}`.",
        "",
        "## Product-level co-movement",
        "",
        "| Source | Correlation defined | Weighted defined | Low n | Minimum active products | Minimum positive-weight products |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for source, counts in validation["correlation_counts"].items():
        lines.append(
            f"| `{source}` | {counts['correlation_defined']} | "
            f"{counts['weighted_correlation_defined']} | "
            f"{counts['low_n']} | "
            f"{counts['minimum_active_product_count']} | "
            f"{counts['minimum_positive_weight_product_count']} |"
        )
    lines.extend(
        [
            "",
            "- Pearson correlations are computed across active HS6 products within each connector-sector cell.",
            "- Weighted correlations use pre-period source input plus connector export value as weights.",
            "- Positive-leg, rerouting, and triple-condition shares retain separate eligible-product, active-product, and positive-export-gain denominators.",
            f"- Correlations outside [-1,1] / shares outside [0,1]: "
            f"`{validation['correlation_out_of_bounds_count']} / "
            f"{validation['comovement_share_out_of_bounds_count']}`.",
            "",
            "## Stata and edge-case interface",
            "",
            f"- Product / sector / co-movement aliases: "
            f"`{validation['stata_alias_validation']['product']['alias_count']} / "
            f"{validation['stata_alias_validation']['sector']['alias_count']} / "
            f"{validation['stata_alias_validation']['comovement']['alias_count']}`; "
            "all complete, unique, and no longer than 32 characters.",
            f"- TWN product / sector / co-movement rows: "
            f"`{validation['twn_checks']['product_rows']} / "
            f"{validation['twn_checks']['sector_rows']} / "
            f"{validation['twn_checks']['comovement_rows']}`; all retain the proxy flag.",
            "- China→USA and policy fields repeat across connectors for comparison and are explicitly marked non-additive.",
            "- Canonical format remains Parquet. Stata `.dta` export remains deferred to M7.",
            "",
            "## Interpretation boundaries",
            "",
            "- `replacement_ratio` is a descriptive reorganization indicator, not a causal estimate.",
            "- M3.3 small-base and abnormal-growth flags are carried forward unchanged and remain advisory.",
            "- Exposure-overlap and co-movement measures are descriptive diagnostics. They do not prove supply-chain rerouting.",
            "- This module does not construct connector ranking, production-side variables, structural moments, or counterfactual inputs.",
            "",
        ]
    )
    if validation["failures"]:
        lines.extend(
            ["## Failures", ""]
            + [f"- {failure}" for failure in validation["failures"]]
            + [""]
        )
    return "\n".join(lines)


def read_inputs(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pa.Schema,
    pd.DataFrame,
    pa.Schema,
    pd.DataFrame,
    pa.Schema,
    pd.DataFrame,
    pa.Schema,
    dict[str, Any],
]:
    tables: dict[str, pa.Table] = {}
    for name in [
        "connector_trade_hs6_year",
        "product_sector_crosswalk",
        "connector_trade_sector_window_comparison",
        "connector_trade_sector_growth_diagnostics",
    ]:
        tables[name] = pq.read_table(
            project_root / config["inputs"][name]["path"]
        )
    time_windows = load_yaml(
        project_root / config["inputs"]["time_windows"]["path"]
    )
    annual = tables["connector_trade_hs6_year"]
    crosswalk = tables["product_sector_crosswalk"]
    comparison = tables["connector_trade_sector_window_comparison"]
    diagnostics = tables["connector_trade_sector_growth_diagnostics"]
    return (
        annual.to_pandas(),
        annual.schema,
        crosswalk.to_pandas(),
        crosswalk.schema,
        comparison.to_pandas(),
        comparison.schema,
        diagnostics.to_pandas(),
        diagnostics.schema,
        time_windows,
    )


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    candidate_outputs: dict[str, Path],
) -> dict[str, Any]:
    temp_directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if temp_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse pre-existing temp directory: {temp_directory}"
        )
    temp_directory.mkdir(parents=True)
    try:
        (
            annual,
            _,
            crosswalk,
            _,
            comparison,
            _,
            diagnostics,
            _,
            _,
        ) = read_inputs(project_root, config)
        product, sector, comovement, _ = build_outputs(
            annual,
            crosswalk,
            comparison,
            diagnostics,
            config,
            config_hash,
        )
        frames = {
            "product": product,
            "sector": sector,
            "comovement": comovement,
        }
        results: dict[str, Any] = {}
        for output_name, frame in frames.items():
            second_path = (
                temp_directory
                / f"{candidate_outputs[output_name].stem}_second.parquet"
            )
            write_parquet(frame, second_path)
            candidate_hash = sha256(candidate_outputs[output_name])
            second_hash = sha256(second_path)
            results[output_name] = {
                "candidate_sha256": candidate_hash,
                "second_build_sha256": second_hash,
                "sha256_match": candidate_hash == second_hash,
            }
        result = {
            "required": bool(
                config["validation"][
                    "require_deterministic_parquet_sha256"
                ]
            ),
            "temporary_directory": temp_directory.relative_to(
                project_root
            ).as_posix(),
            "outputs": results,
            "all_sha256_match": all(
                details["sha256_match"] for details in results.values()
            ),
        }
    finally:
        remove_owned_temp_directory(temp_directory)
    result["temporary_output_cleaned"] = not temp_directory.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate M3.4 replacement, source-input, exposure "
            "overlap, and product co-movement indicators."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/connector_trade_reorganization_indicator_rules.yaml"
        ),
    )
    parser.add_argument("--product-output", type=Path)
    parser.add_argument("--sector-output", type=Path)
    parser.add_argument("--comovement-output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    output_arguments = {
        "product": args.product_output,
        "sector": args.sector_output,
        "comovement": args.comovement_output,
    }
    output_paths = {
        output_name: relative_or_absolute(
            project_root,
            output_arguments[output_name]
            or Path(config["outputs"][output_name]["path"]),
        ).resolve()
        for output_name in output_arguments
    }
    validation_json = relative_or_absolute(
        project_root,
        args.validation_json or Path(config["validation_outputs"]["json"]),
    ).resolve()
    validation_md = relative_or_absolute(
        project_root,
        args.validation_md
        or Path(config["validation_outputs"]["markdown"]),
    ).resolve()
    for path in [*output_paths.values(), validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(
                f"Refusing to overwrite {path}; pass --overwrite"
            )

    candidate_directory = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    if candidate_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse pre-existing candidate directory: "
            f"{candidate_directory}"
        )
    candidate_directory.mkdir(parents=True)
    candidate_outputs = {
        output_name: candidate_directory / path.name
        for output_name, path in output_paths.items()
    }

    try:
        input_hash_matches = {
            name: (
                sha256(project_root / details["path"])
                == details["sha256"]
            )
            for name, details in config["inputs"].items()
        }
        (
            annual,
            annual_schema,
            crosswalk,
            crosswalk_schema,
            comparison,
            comparison_schema,
            diagnostics,
            diagnostics_schema,
            time_windows,
        ) = read_inputs(project_root, config)
        product, sector, comovement, product_context = build_outputs(
            annual,
            crosswalk,
            comparison,
            diagnostics,
            config,
            config_hash,
        )
        output_frames = {
            "product": product,
            "sector": sector,
            "comovement": comovement,
        }
        output_tables = {
            output_name: write_parquet(
                output_frames[output_name], candidate_outputs[output_name]
            )
            for output_name in output_frames
        }
        determinism = deterministic_rebuild(
            project_root,
            config,
            config_hash,
            candidate_outputs,
        )
        validation = validate(
            annual,
            annual_schema,
            crosswalk,
            crosswalk_schema,
            comparison,
            comparison_schema,
            diagnostics,
            diagnostics_schema,
            time_windows,
            product,
            sector,
            comovement,
            product_context,
            config,
            input_hash_matches,
            determinism,
        )
        validation.update(
            {
                "validation_version": 1,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path.relative_to(project_root).as_posix(),
                "config_sha256": config_hash,
                "construction_version": config["version"],
                "outputs": {
                    output_name: {
                        "path": output_paths[output_name]
                        .relative_to(project_root)
                        .as_posix(),
                        "sha256": sha256(candidate_outputs[output_name]),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in output_tables[output_name].schema
                        ],
                    }
                    for output_name in output_frames
                },
                "candidate_temp_directory": (
                    candidate_directory.relative_to(project_root).as_posix()
                ),
            }
        )
        if validation["validation_status"] != "PASS":
            print(json.dumps(validation, ensure_ascii=False, indent=2))
            raise SystemExit(1)

        for output_name, output_path in output_paths.items():
            output_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_outputs[output_name].replace(output_path)
        remove_owned_temp_directory(candidate_directory)
        validation["candidate_temporary_output_cleaned"] = (
            not candidate_directory.exists()
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
                    "output_rows": validation["output_row_counts"],
                    "output_columns": validation["output_column_counts"],
                    "output_sha256": {
                        name: details["sha256"]
                        for name, details in validation["outputs"].items()
                    },
                    "deterministic_sha256_match": determinism[
                        "all_sha256_match"
                    ],
                    "validation_json": str(validation_json),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    except BaseException:
        if candidate_directory.exists():
            remove_owned_temp_directory(candidate_directory)
        raise


if __name__ == "__main__":
    main()
