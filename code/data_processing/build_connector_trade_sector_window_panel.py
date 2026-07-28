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


ENTITY_FIELDS = [
    "connector_group",
    "connector_baci_code",
    "connector_is_proxy",
    "analysis_sector_status",
    "sector_eligible_product_count",
]

OUTPUT_METADATA_FIELDS = [
    "trade_value_unit",
    "treatment_concept",
    "historical_exclusions_applied",
    "four_year_review_2024_included",
    "review_2024_treatment",
    "treatment_version",
    "is_analysis_sector_eligible",
    "sector_mapping_weight",
    "baci_absence_treated_as_zero",
    "quantity_included",
    "china_to_usa_common_benchmark",
    "treatment_repeated_across_connectors",
    "coverage_repeated_across_sectors",
    "common_benchmarks_not_additive_across_connectors",
    "product_mapping_version",
    "m3_sector_aggregation_version",
]

BOOLEAN_METADATA_FIELDS = [
    "historical_exclusions_applied",
    "four_year_review_2024_included",
    "is_analysis_sector_eligible",
    "baci_absence_treated_as_zero",
    "quantity_included",
    "china_to_usa_common_benchmark",
    "treatment_repeated_across_connectors",
    "coverage_repeated_across_sectors",
    "common_benchmarks_not_additive_across_connectors",
]

STRING_METADATA_FIELDS = [
    "trade_value_unit",
    "treatment_concept",
    "review_2024_treatment",
    "treatment_version",
    "product_mapping_version",
    "m3_sector_aggregation_version",
]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    usable = denominator.notna() & denominator.ne(0)
    result.loc[usable] = (
        numerator.loc[usable].astype("float64")
        / denominator.loc[usable].astype("float64")
    )
    return result


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


def unique_scalar(frame: pd.DataFrame, column: str) -> Any:
    values = frame[column].drop_duplicates()
    if len(values) != 1:
        raise ValueError(
            f"Expected one unique value for {column}, observed {len(values)}"
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


def window_definition_context(
    config: dict[str, Any],
    source_windows: dict[str, Any],
) -> dict[str, Any]:
    year_to_windows: dict[int, list[str]] = {}
    source_definition_match: dict[str, bool] = {}
    expected_year_counts: dict[str, int] = {}
    for window_id, details in config["windows"].items():
        start = int(details["start"])
        end = int(details["end"])
        expected = int(details["expected_year_count"])
        source = source_windows[details["source_key"]]
        source_definition_match[window_id] = (
            int(source["start"]) == start and int(source["end"]) == end
        )
        expected_year_counts[window_id] = expected
        if end - start + 1 != expected:
            raise ValueError(
                f"Window {window_id} expected count does not match its endpoints"
            )
        for year in range(start, end + 1):
            year_to_windows.setdefault(year, []).append(window_id)
    overlaps = {
        year: windows for year, windows in year_to_windows.items() if len(windows) != 1
    }
    return {
        "year_to_windows": year_to_windows,
        "overlapping_window_years": overlaps,
        "source_window_definition_match": source_definition_match,
        "expected_year_counts": expected_year_counts,
    }


def assign_windows(
    annual: pd.DataFrame,
    config: dict[str, Any],
    source_windows: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    context = window_definition_context(config, source_windows)
    mapping = {
        year: windows[0]
        for year, windows in context["year_to_windows"].items()
        if len(windows) == 1
    }
    output = annual.copy()
    output["window_id"] = output["year"].astype(int).map(mapping).astype("string")
    unassigned = int(output["window_id"].isna().sum())
    window_details = config["windows"]
    output["window_order"] = (
        output["window_id"]
        .map({name: int(details["order"]) for name, details in window_details.items()})
        .astype("Int8")
    )
    output["window_start_year"] = (
        output["window_id"]
        .map({name: int(details["start"]) for name, details in window_details.items()})
        .astype("Int16")
    )
    output["window_end_year"] = (
        output["window_id"]
        .map({name: int(details["end"]) for name, details in window_details.items()})
        .astype("Int16")
    )
    output["expected_year_count"] = (
        output["window_id"]
        .map(
            {
                name: int(details["expected_year_count"])
                for name, details in window_details.items()
            }
        )
        .astype("Int8")
    )
    context["unassigned_annual_row_count"] = unassigned
    return output, context


def build_coverage_windows(
    annual_window: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    coverage_keys = ["connector_iso3", "year", "window_id"]
    first_columns = ["excluded_product_count"]
    for details in config["trade_flows"].values():
        first_columns.append(details["excluded_value_field"])
    coverage_annual = (
        annual_window.sort_values(["connector_iso3", "year", "analysis_sector"])
        .groupby(coverage_keys, as_index=False, sort=True)
        .agg(**{field: (field, "first") for field in first_columns})
    )
    for flow_name, details in config["trade_flows"].items():
        eligible_field = f"_{flow_name}_eligible_value_usd"
        eligible = (
            annual_window.groupby(coverage_keys, sort=True)[details["value_field"]]
            .sum()
            .rename(eligible_field)
            .reset_index()
        )
        coverage_annual = coverage_annual.merge(
            eligible,
            on=coverage_keys,
            how="left",
            validate="one_to_one",
        )

    window_keys = ["connector_iso3", "window_id"]
    aggregation: dict[str, pd.NamedAgg] = {
        "excluded_product_count": pd.NamedAgg(
            column="excluded_product_count", aggfunc="first"
        )
    }
    for flow_name, details in config["trade_flows"].items():
        aggregation[f"{flow_name}_excluded_value_usd_annual_mean"] = pd.NamedAgg(
            column=details["excluded_value_field"], aggfunc="mean"
        )
        aggregation[f"_{flow_name}_eligible_value_usd_sum"] = pd.NamedAgg(
            column=f"_{flow_name}_eligible_value_usd", aggfunc="sum"
        )
        aggregation[f"_{flow_name}_excluded_value_usd_sum"] = pd.NamedAgg(
            column=details["excluded_value_field"], aggfunc="sum"
        )
    output = coverage_annual.groupby(
        window_keys, as_index=False, sort=True
    ).agg(**aggregation)
    for flow_name in config["trade_flows"]:
        numerator = output[f"_{flow_name}_eligible_value_usd_sum"]
        excluded = output[f"_{flow_name}_excluded_value_usd_sum"]
        output[f"{flow_name}_included_value_share"] = safe_divide(
            numerator, numerator + excluded
        )
    temporary = [column for column in output if column.startswith("_")]
    return output.drop(columns=temporary)


def build_policy_windows(
    annual_window: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    policy_annual = (
        annual_window.sort_values(["analysis_sector", "year", "connector_iso3"])
        .drop_duplicates(["analysis_sector", "year"])
        .copy()
    )
    aggregation: dict[str, pd.NamedAgg] = {}
    for field in config["policy"]["denominator_fields"]:
        aggregation[field] = pd.NamedAgg(column=field, aggfunc="first")
    for source, output in config["policy"]["annual_mean_numerator_fields"].items():
        aggregation[output] = pd.NamedAgg(column=source, aggfunc="mean")
    policy = policy_annual.groupby(
        ["analysis_sector", "window_id"],
        as_index=False,
        sort=True,
    ).agg(**aggregation)

    policy["sector_tariff_rate_china_weighted"] = safe_divide(
        policy["sector_tariff_exposure_numerator_usd_annual_mean"],
        policy["sector_china_import_value_2017"],
    )
    policy["sector_tariff_exposure"] = safe_divide(
        policy["sector_tariff_exposure_numerator_usd_annual_mean"],
        policy["sector_total_us_import_value_2017"],
    )
    policy["sector_china_import_share_2017"] = safe_divide(
        policy["sector_china_import_value_2017"],
        policy["sector_total_us_import_value_2017"],
    )
    policy["tariffed_product_share_count"] = safe_divide(
        policy["tariffed_product_count_annual_mean"],
        policy["sector_treatment_product_count"],
    )
    policy["tariffed_product_share_china_value"] = safe_divide(
        policy["tariffed_china_import_value_2017_annual_mean"],
        policy["sector_china_import_value_2017"],
    )
    policy["tariffed_product_share_us_value"] = safe_divide(
        policy["tariffed_total_us_import_value_2017_annual_mean"],
        policy["sector_total_us_import_value_2017"],
    )
    policy["treatment_missing_denominator_product_share"] = safe_divide(
        policy["treatment_missing_denominator_product_count"],
        policy["sector_treatment_product_count"],
    )
    policy["treatment_zero_denominator_product_share"] = safe_divide(
        policy["treatment_zero_denominator_product_count"],
        policy["sector_treatment_product_count"],
    )
    policy["treatment_no_hs17_mapping_product_share"] = safe_divide(
        policy["treatment_no_hs17_mapping_product_count"],
        policy["sector_treatment_product_count"],
    )
    return policy


def finalize_long_types(
    output: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    string_columns = [
        "connector_iso3",
        "analysis_sector",
        "window_id",
        "connector_group",
        "connector_baci_code",
        "analysis_sector_status",
        *STRING_METADATA_FIELDS,
        "m3_window_construction_version",
        "schema_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["window_order"] = output["window_order"].astype("int8")
    output["window_start_year"] = output["window_start_year"].astype("int16")
    output["window_end_year"] = output["window_end_year"].astype("int16")
    output["expected_year_count"] = output["expected_year_count"].astype("int8")
    output["observed_year_count"] = output["observed_year_count"].astype("int8")
    integer_columns = [
        "sector_eligible_product_count",
        "excluded_product_count",
        "sector_treatment_product_count",
        "policy_denominator_observed_product_count",
        "treatment_missing_denominator_product_count",
        "treatment_zero_denominator_product_count",
        "treatment_no_hs17_mapping_product_count",
    ]
    for column in integer_columns:
        output[column] = output[column].astype("int32")
    boolean_columns = [
        "window_complete",
        "connector_is_proxy",
        *BOOLEAN_METADATA_FIELDS,
        "window_level_is_annual_mean",
        "included_value_share_uses_ratio_of_sums",
    ]
    for column in boolean_columns:
        output[column] = output[column].astype("bool")
    output["sector_mapping_weight"] = output["sector_mapping_weight"].astype("float64")
    key = config["outputs"]["long"]["natural_key"]
    ordered = key + [column for column in output.columns if column not in key]
    return output[ordered].sort_values(
        ["connector_iso3", "analysis_sector", "window_order"]
    ).reset_index(drop=True)


def build_long_panel(
    annual_window: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    key = config["outputs"]["long"]["natural_key"]
    aggregation: dict[str, pd.NamedAgg] = {
        "window_order": pd.NamedAgg(column="window_order", aggfunc="first"),
        "window_start_year": pd.NamedAgg(
            column="window_start_year", aggfunc="first"
        ),
        "window_end_year": pd.NamedAgg(column="window_end_year", aggfunc="first"),
        "expected_year_count": pd.NamedAgg(
            column="expected_year_count", aggfunc="first"
        ),
        "observed_year_count": pd.NamedAgg(column="year", aggfunc="nunique"),
    }
    for field in ENTITY_FIELDS:
        aggregation[field] = pd.NamedAgg(column=field, aggfunc="first")
    for flow_name, details in config["trade_flows"].items():
        fields = {
            f"{flow_name}_value_usd_annual_mean": details["value_field"],
            f"{flow_name}_source_row_count_annual_mean": details[
                "source_row_count_field"
            ],
            f"{flow_name}_positive_product_count_annual_mean": details[
                "positive_product_count_field"
            ],
            f"{flow_name}_zero_source_product_count_annual_mean": details[
                "zero_source_product_count_field"
            ],
        }
        for output_field, source_field in fields.items():
            aggregation[output_field] = pd.NamedAgg(
                column=source_field, aggfunc="mean"
            )
    output = annual_window.groupby(key, as_index=False, sort=True).agg(**aggregation)
    output["window_complete"] = output["observed_year_count"].eq(
        output["expected_year_count"]
    )
    output = output.merge(
        build_coverage_windows(annual_window, config),
        on=["connector_iso3", "window_id"],
        how="left",
        validate="many_to_one",
    )
    output = output.merge(
        build_policy_windows(annual_window, config),
        on=["analysis_sector", "window_id"],
        how="left",
        validate="many_to_one",
    )
    for field in OUTPUT_METADATA_FIELDS:
        output[field] = unique_scalar(annual_window, field)
    output["window_level_is_annual_mean"] = True
    output["included_value_share_uses_ratio_of_sums"] = True
    output["m3_window_construction_version"] = config["version"]
    output["schema_version"] = config["long_schema_version"]
    return finalize_long_types(output, config)


def select_window_values(
    long: pd.DataFrame,
    base: pd.DataFrame,
    field: str,
    window_id: str,
) -> pd.Series:
    key = ["connector_iso3", "analysis_sector"]
    values = long.loc[long["window_id"].eq(window_id), key + [field]]
    merged = base[key].merge(values, on=key, how="left", validate="one_to_one")
    return merged[field]


def build_comparison_panel(
    long: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    key = config["outputs"]["comparison"]["natural_key"]
    pre = long.loc[long["window_id"].eq("pre")].copy()
    base_fields = [
        *key,
        *ENTITY_FIELDS,
        "excluded_product_count",
        *config["policy"]["comparison_constant_fields"],
        *OUTPUT_METADATA_FIELDS,
        "window_level_is_annual_mean",
        "included_value_share_uses_ratio_of_sums",
        "m3_window_construction_version",
    ]
    output = pre[base_fields].sort_values(key).reset_index(drop=True)
    derived: dict[str, pd.Series] = {}

    for flow_name in config["trade_flows"]:
        long_value = f"{flow_name}_value_usd_annual_mean"
        for window_id in config["windows"]:
            derived[f"{flow_name}_value_usd_{window_id}"] = select_window_values(
                long, output, long_value, window_id
            )
            derived[f"{flow_name}_years_observed_{window_id}"] = (
                select_window_values(long, output, "observed_year_count", window_id)
                .astype("int8")
            )
            derived[f"{flow_name}_excluded_value_usd_{window_id}"] = (
                select_window_values(
                    long,
                    output,
                    f"{flow_name}_excluded_value_usd_annual_mean",
                    window_id,
                )
            )
            derived[f"{flow_name}_included_value_share_{window_id}"] = (
                select_window_values(
                    long,
                    output,
                    f"{flow_name}_included_value_share",
                    window_id,
                )
            )
        pre_value = derived[f"{flow_name}_value_usd_pre"].astype("float64")
        post_value = derived[f"{flow_name}_value_usd_post"].astype("float64")
        derived[f"{flow_name}_value_usd_change_post_pre"] = post_value - pre_value
        dh_denominator = post_value + pre_value
        derived[f"{flow_name}_value_usd_dh_growth_post_pre"] = safe_divide(
            2.0 * (post_value - pre_value),
            dh_denominator,
        )
        log_defined = pre_value.gt(0) & post_value.gt(0)
        log_growth = pd.Series(np.nan, index=output.index, dtype="float64")
        log_growth.loc[log_defined] = (
            np.log(post_value.loc[log_defined]) - np.log(pre_value.loc[log_defined])
        )
        derived[f"{flow_name}_value_usd_log_growth_post_pre"] = log_growth
        derived[f"{flow_name}_pre_zero_flag"] = pre_value.eq(0)
        derived[f"{flow_name}_post_zero_flag"] = post_value.eq(0)
        derived[f"{flow_name}_dh_growth_defined"] = dh_denominator.ne(0)
        derived[f"{flow_name}_log_growth_defined"] = log_defined

    for field in config["policy"]["comparison_window_fields"]:
        for window_id in config["windows"]:
            derived[f"{field}_{window_id}"] = select_window_values(
                long, output, field, window_id
            )

    output = pd.concat(
        [output, pd.DataFrame(derived, index=output.index)],
        axis=1,
    )
    output["schema_version"] = config["comparison_schema_version"]
    string_columns = [
        "connector_iso3",
        "analysis_sector",
        "connector_group",
        "connector_baci_code",
        "analysis_sector_status",
        *STRING_METADATA_FIELDS,
        "m3_window_construction_version",
        "schema_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    integer_columns = [
        "sector_eligible_product_count",
        "excluded_product_count",
        "sector_treatment_product_count",
        "policy_denominator_observed_product_count",
        "treatment_missing_denominator_product_count",
        "treatment_zero_denominator_product_count",
        "treatment_no_hs17_mapping_product_count",
    ]
    for column in integer_columns:
        output[column] = output[column].astype("int32")
    for flow_name in config["trade_flows"]:
        for window_id in config["windows"]:
            output[f"{flow_name}_years_observed_{window_id}"] = output[
                f"{flow_name}_years_observed_{window_id}"
            ].astype("int8")
    boolean_columns = [
        "connector_is_proxy",
        *BOOLEAN_METADATA_FIELDS,
        "window_level_is_annual_mean",
        "included_value_share_uses_ratio_of_sums",
        *[
            f"{flow_name}_{suffix}"
            for flow_name in config["trade_flows"]
            for suffix in [
                "pre_zero_flag",
                "post_zero_flag",
                "dh_growth_defined",
                "log_growth_defined",
            ]
        ],
    ]
    for column in boolean_columns:
        output[column] = output[column].astype("bool")
    output["sector_mapping_weight"] = output["sector_mapping_weight"].astype("float64")
    ordered = key + [column for column in output.columns if column not in key]
    return output[ordered].sort_values(key).reset_index(drop=True)


def build_outputs(
    annual: pd.DataFrame,
    config: dict[str, Any],
    source_windows: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any], pd.DataFrame]:
    annual_window, window_context = assign_windows(annual, config, source_windows)
    long = build_long_panel(annual_window, config)
    comparison = build_comparison_panel(long, config)
    return long, comparison, window_context, annual_window


def resolve_stata_aliases(
    config: dict[str, Any],
    output_name: str,
) -> dict[str, str]:
    alias_config = config["outputs"][output_name]["stata_aliases"]
    aliases = dict(alias_config["direct"])
    for flow_name, details in config["trade_flows"].items():
        prefix = details["prefix"]
        for suffix, template in alias_config.get("flow_templates", {}).items():
            aliases[f"{flow_name}_{suffix}"] = template.format(prefix=prefix)
    if output_name == "comparison":
        for field, template in alias_config.get(
            "policy_window_templates", {}
        ).items():
            for window_id, details in config["windows"].items():
                aliases[f"{field}_{window_id}"] = template.format(
                    window=details["stata_suffix"]
                )
    return aliases


def alias_validation(
    frame: pd.DataFrame,
    aliases: dict[str, str],
) -> dict[str, Any]:
    output_columns = set(frame.columns)
    alias_columns = set(aliases)
    missing = sorted(output_columns - alias_columns)
    extra = sorted(alias_columns - output_columns)
    duplicate_count = len(aliases.values()) - len(set(aliases.values()))
    overlength = sorted(alias for alias in aliases.values() if len(alias) > 32)
    maximum_length = max(map(len, aliases.values())) if aliases else 0
    return {
        "alias_count": len(aliases),
        "output_column_count": len(frame.columns),
        "missing_output_aliases": missing,
        "extra_stata_aliases": extra,
        "duplicate_alias_count": duplicate_count,
        "over_32_character_aliases": overlength,
        "maximum_alias_length": maximum_length,
        "pass": not (missing or extra or duplicate_count or overlength),
        "resolved_aliases": aliases,
    }


def independent_coverage_expected(
    annual_window: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    keys = ["connector_iso3", "year", "window_id"]
    base = (
        annual_window.sort_values(["connector_iso3", "year", "analysis_sector"])
        .drop_duplicates(["connector_iso3", "year"])
        [["connector_iso3", "year", "window_id", "excluded_product_count"]]
    )
    working = base.copy()
    for flow_name, details in config["trade_flows"].items():
        eligible = (
            annual_window.groupby(keys, sort=True)[details["value_field"]]
            .sum()
            .rename(f"{flow_name}_eligible")
            .reset_index()
        )
        excluded = (
            annual_window.sort_values(["connector_iso3", "year", "analysis_sector"])
            .drop_duplicates(["connector_iso3", "year"])[
                keys + [details["excluded_value_field"]]
            ]
            .rename(
                columns={
                    details[
                        "excluded_value_field"
                    ]: f"{flow_name}_excluded"
                }
            )
        )
        working = working.merge(eligible, on=keys, how="left", validate="one_to_one")
        working = working.merge(excluded, on=keys, how="left", validate="one_to_one")
    aggregation: dict[str, pd.NamedAgg] = {
        "excluded_product_count": pd.NamedAgg(
            column="excluded_product_count", aggfunc="first"
        )
    }
    for flow_name in config["trade_flows"]:
        aggregation[f"{flow_name}_eligible_sum"] = pd.NamedAgg(
            column=f"{flow_name}_eligible", aggfunc="sum"
        )
        aggregation[f"{flow_name}_excluded_sum"] = pd.NamedAgg(
            column=f"{flow_name}_excluded", aggfunc="sum"
        )
        aggregation[f"{flow_name}_excluded_value_usd_annual_mean"] = pd.NamedAgg(
            column=f"{flow_name}_excluded", aggfunc="mean"
        )
    expected = working.groupby(
        ["connector_iso3", "window_id"], as_index=False, sort=True
    ).agg(**aggregation)
    for flow_name in config["trade_flows"]:
        expected[f"{flow_name}_included_value_share"] = safe_divide(
            expected[f"{flow_name}_eligible_sum"],
            expected[f"{flow_name}_eligible_sum"]
            + expected[f"{flow_name}_excluded_sum"],
        )
    return expected


def independent_policy_expected(
    annual_window: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    annual = (
        annual_window.sort_values(["analysis_sector", "year", "connector_iso3"])
        .drop_duplicates(["analysis_sector", "year"])
        .copy()
    )
    aggregation: dict[str, pd.NamedAgg] = {}
    for field in config["policy"]["denominator_fields"]:
        aggregation[field] = pd.NamedAgg(column=field, aggfunc="first")
    for source, output in config["policy"]["annual_mean_numerator_fields"].items():
        aggregation[output] = pd.NamedAgg(column=source, aggfunc="mean")
    expected = annual.groupby(
        ["analysis_sector", "window_id"], as_index=False, sort=True
    ).agg(**aggregation)
    expected["sector_tariff_rate_china_weighted"] = safe_divide(
        expected["sector_tariff_exposure_numerator_usd_annual_mean"],
        expected["sector_china_import_value_2017"],
    )
    expected["sector_tariff_exposure"] = safe_divide(
        expected["sector_tariff_exposure_numerator_usd_annual_mean"],
        expected["sector_total_us_import_value_2017"],
    )
    expected["sector_china_import_share_2017"] = safe_divide(
        expected["sector_china_import_value_2017"],
        expected["sector_total_us_import_value_2017"],
    )
    expected["tariffed_product_share_count"] = safe_divide(
        expected["tariffed_product_count_annual_mean"],
        expected["sector_treatment_product_count"],
    )
    expected["tariffed_product_share_china_value"] = safe_divide(
        expected["tariffed_china_import_value_2017_annual_mean"],
        expected["sector_china_import_value_2017"],
    )
    expected["tariffed_product_share_us_value"] = safe_divide(
        expected["tariffed_total_us_import_value_2017_annual_mean"],
        expected["sector_total_us_import_value_2017"],
    )
    expected["treatment_missing_denominator_product_share"] = safe_divide(
        expected["treatment_missing_denominator_product_count"],
        expected["sector_treatment_product_count"],
    )
    expected["treatment_zero_denominator_product_share"] = safe_divide(
        expected["treatment_zero_denominator_product_count"],
        expected["sector_treatment_product_count"],
    )
    expected["treatment_no_hs17_mapping_product_share"] = safe_divide(
        expected["treatment_no_hs17_mapping_product_count"],
        expected["sector_treatment_product_count"],
    )
    return expected


def validate(
    config: dict[str, Any],
    annual: pd.DataFrame,
    annual_schema: pa.Schema,
    annual_window: pd.DataFrame,
    long: pd.DataFrame,
    comparison: pd.DataFrame,
    window_context: dict[str, Any],
    input_hash_checks: dict[str, bool],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    value_tolerance = float(config["validation"]["value_tolerance_usd"])
    ratio_tolerance = float(config["validation"]["ratio_tolerance"])
    input_config = config["inputs"]["connector_trade_sector_year"]
    input_key = input_config["natural_key"]
    long_key = config["outputs"]["long"]["natural_key"]
    comparison_key = config["outputs"]["comparison"]["natural_key"]

    input_duplicates = int(annual.duplicated(input_key).sum())
    long_duplicates = int(long.duplicated(long_key).sum())
    comparison_duplicates = int(comparison.duplicated(comparison_key).sum())
    input_schema_signature = schema_signature(annual_schema)
    schema_version_values = annual["schema_version"].drop_duplicates().tolist()
    aggregation_version_values = (
        annual["m3_sector_aggregation_version"].drop_duplicates().tolist()
    )
    if not all(input_hash_checks.values()):
        failures.append("one or more frozen M3.2 input hashes do not match")
    if len(annual) != int(input_config["expected_rows"]):
        failures.append("M3.1 input row count differs from the frozen config")
    if len(annual.columns) != int(input_config["expected_columns"]):
        failures.append("M3.1 input column count differs from the frozen config")
    if input_schema_signature != input_config["arrow_schema_signature_sha256"]:
        failures.append("M3.1 Arrow schema signature differs from the frozen config")
    if schema_version_values != [input_config["expected_schema_version"]]:
        failures.append("M3.1 schema_version differs from the frozen config")
    if aggregation_version_values != [input_config["expected_aggregation_version"]]:
        failures.append("M3.1 aggregation version differs from the frozen config")
    if input_duplicates or long_duplicates or comparison_duplicates:
        failures.append("an input or output natural key is duplicated")
    if window_context["overlapping_window_years"]:
        failures.append("one or more years are assigned to overlapping windows")
    if window_context["unassigned_annual_row_count"]:
        failures.append("one or more annual rows were not assigned to a window")
    if not all(window_context["source_window_definition_match"].values()):
        failures.append("frozen windows differ from configs/time_windows.yaml")

    observed_connectors = sorted(long["connector_iso3"].unique().tolist())
    observed_sectors = sorted(long["analysis_sector"].unique().tolist())
    if observed_connectors != sorted(config["analysis"]["connectors"]):
        failures.append("output connector set differs from the frozen config")
    if observed_sectors != sorted(config["analysis"]["sectors"]):
        failures.append("output sector set differs from the frozen config")
    if len(long) != int(config["outputs"]["long"]["expected_rows"]):
        failures.append("long output row count differs from 273")
    if len(comparison) != int(config["outputs"]["comparison"]["expected_rows"]):
        failures.append("comparison output row count differs from 91")

    window_cell_counts = (
        annual_window.groupby(
            ["connector_iso3", "analysis_sector", "window_id"], sort=True
        )["year"]
        .nunique()
        .astype(int)
    )
    expected_counts = {
        window_id: int(details["expected_year_count"])
        for window_id, details in config["windows"].items()
    }
    incomplete_by_window: dict[str, int] = {}
    observed_count_ranges: dict[str, dict[str, int]] = {}
    for window_id, expected in expected_counts.items():
        counts = window_cell_counts.loc[
            window_cell_counts.index.get_level_values("window_id") == window_id
        ]
        incomplete_by_window[window_id] = int(counts.ne(expected).sum())
        observed_count_ranges[window_id] = {
            "min": int(counts.min()),
            "max": int(counts.max()),
            "expected": expected,
        }
    if any(incomplete_by_window.values()) or not long["window_complete"].all():
        failures.append("one or more connector-sector windows are incomplete")

    mean_reconciliation: dict[str, Any] = {}
    diagnostic_reconciliation: dict[str, Any] = {}
    group_key = ["connector_iso3", "analysis_sector", "window_id"]
    long_indexed = long.set_index(group_key).sort_index()
    observed_count = long_indexed["observed_year_count"].astype("float64")
    for flow_name, details in config["trade_flows"].items():
        input_sum = (
            annual_window.groupby(group_key, sort=True)[details["value_field"]]
            .sum()
            .astype("float64")
        )
        reconstructed = (
            long_indexed[f"{flow_name}_value_usd_annual_mean"] * observed_count
        )
        gap, missing_mismatch = maximum_absolute_gap(reconstructed, input_sum)
        mean_reconciliation[flow_name] = {
            "input_window_total_usd": float(input_sum.sum()),
            "reconstructed_window_total_usd": float(reconstructed.sum()),
            "max_abs_window_gap_usd": gap,
            "missing_mismatch_count": missing_mismatch,
        }
        if gap > value_tolerance or missing_mismatch:
            failures.append(f"{flow_name} window mean fails annual-sum reconciliation")
        diagnostic_reconciliation[flow_name] = {}
        for suffix, source_field in [
            ("source_row_count_annual_mean", details["source_row_count_field"]),
            (
                "positive_product_count_annual_mean",
                details["positive_product_count_field"],
            ),
            (
                "zero_source_product_count_annual_mean",
                details["zero_source_product_count_field"],
            ),
        ]:
            expected_sum = annual_window.groupby(group_key, sort=True)[
                source_field
            ].sum()
            reconstructed_count = long_indexed[
                f"{flow_name}_{suffix}"
            ] * observed_count
            count_gap, count_missing = maximum_absolute_gap(
                reconstructed_count, expected_sum
            )
            diagnostic_reconciliation[flow_name][suffix] = {
                "max_abs_window_gap": count_gap,
                "missing_mismatch_count": count_missing,
            }
            if count_gap > ratio_tolerance or count_missing:
                failures.append(
                    f"{flow_name} {suffix} fails annual-count reconciliation"
                )

    long_comparison_level_gaps: dict[str, Any] = {}
    for flow_name in config["trade_flows"]:
        long_comparison_level_gaps[flow_name] = {}
        for window_id in config["windows"]:
            expected = select_window_values(
                long,
                comparison,
                f"{flow_name}_value_usd_annual_mean",
                window_id,
            )
            actual = comparison[f"{flow_name}_value_usd_{window_id}"]
            gap, missing = maximum_absolute_gap(actual, expected)
            long_comparison_level_gaps[flow_name][window_id] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing,
            }
            if gap > ratio_tolerance or missing:
                failures.append(
                    f"{flow_name} {window_id} comparison level differs from long"
                )

    growth_formula_checks: dict[str, Any] = {}
    zero_and_defined_counts: dict[str, Any] = {}
    negative_change_counts: dict[str, int] = {}
    dh_out_of_bounds_count = 0
    infinite_growth_value_count = 0
    for flow_name in config["trade_flows"]:
        pre = comparison[f"{flow_name}_value_usd_pre"].astype("float64")
        post = comparison[f"{flow_name}_value_usd_post"].astype("float64")
        expected_change = post - pre
        expected_dh = safe_divide(2.0 * expected_change, post + pre)
        expected_log = pd.Series(np.nan, index=comparison.index, dtype="float64")
        positive = pre.gt(0) & post.gt(0)
        expected_log.loc[positive] = (
            np.log(post.loc[positive]) - np.log(pre.loc[positive])
        )
        flow_checks: dict[str, Any] = {}
        for label, actual, expected in [
            (
                "change_post_pre",
                comparison[f"{flow_name}_value_usd_change_post_pre"],
                expected_change,
            ),
            (
                "dh_growth_post_pre",
                comparison[f"{flow_name}_value_usd_dh_growth_post_pre"],
                expected_dh,
            ),
            (
                "log_growth_post_pre",
                comparison[f"{flow_name}_value_usd_log_growth_post_pre"],
                expected_log,
            ),
        ]:
            gap, missing = maximum_absolute_gap(actual, expected)
            flow_checks[label] = {
                "max_abs_gap": gap,
                "missing_mismatch_count": missing,
            }
            if gap > ratio_tolerance or missing:
                failures.append(f"{flow_name} {label} fails formula validation")
        growth_formula_checks[flow_name] = flow_checks

        dh = comparison[f"{flow_name}_value_usd_dh_growth_post_pre"]
        dh_out_of_bounds_count += int(((dh < -2) | (dh > 2)).fillna(False).sum())
        growth_fields = [
            f"{flow_name}_value_usd_dh_growth_post_pre",
            f"{flow_name}_value_usd_log_growth_post_pre",
        ]
        infinite_growth_value_count += int(
            np.isinf(comparison[growth_fields].to_numpy(dtype="float64")).sum()
        )
        counts = {
            "pre_zero": int(comparison[f"{flow_name}_pre_zero_flag"].sum()),
            "post_zero": int(comparison[f"{flow_name}_post_zero_flag"].sum()),
            "dh_defined": int(
                comparison[f"{flow_name}_dh_growth_defined"].sum()
            ),
            "log_defined": int(
                comparison[f"{flow_name}_log_growth_defined"].sum()
            ),
        }
        zero_and_defined_counts[flow_name] = counts
        negative_change_counts[flow_name] = int(expected_change.lt(0).sum())
        if counts["pre_zero"] != int(
            config["validation"]["expected_pre_zero_count_by_flow"][flow_name]
        ):
            failures.append(f"{flow_name} pre-zero count differs from expectation")
        if counts["post_zero"] != int(
            config["validation"]["expected_post_zero_count_by_flow"][flow_name]
        ):
            failures.append(f"{flow_name} post-zero count differs from expectation")
        if counts["log_defined"] != int(
            config["validation"]["expected_log_growth_defined_count_by_flow"][
                flow_name
            ]
        ):
            failures.append(
                f"{flow_name} log-growth-defined count differs from expectation"
            )
        if negative_change_counts[flow_name] != int(
            config["validation"]["expected_negative_change_count_by_flow"][
                flow_name
            ]
        ):
            failures.append(
                f"{flow_name} negative post-pre change count differs from expectation"
            )
    if dh_out_of_bounds_count:
        failures.append("one or more DH growth values fall outside [-2, 2]")
    if infinite_growth_value_count:
        failures.append("one or more growth values are infinite")

    coverage_expected = independent_coverage_expected(annual_window, config)
    coverage_fields = ["excluded_product_count"]
    for flow_name in config["trade_flows"]:
        coverage_fields.extend(
            [
                f"{flow_name}_excluded_value_usd_annual_mean",
                f"{flow_name}_included_value_share",
            ]
        )
    coverage_observed = (
        long.sort_values("analysis_sector")
        .drop_duplicates(["connector_iso3", "window_id"])
        [["connector_iso3", "window_id", *coverage_fields]]
    )
    coverage_check = coverage_observed.merge(
        coverage_expected,
        on=["connector_iso3", "window_id"],
        how="outer",
        validate="one_to_one",
        suffixes=("_observed", "_expected"),
        indicator=True,
    )
    coverage_formula_gaps: dict[str, Any] = {}
    for field in coverage_fields:
        gap, missing = maximum_absolute_gap(
            coverage_check[f"{field}_observed"],
            coverage_check[f"{field}_expected"],
        )
        coverage_formula_gaps[field] = {
            "max_abs_gap": gap,
            "missing_mismatch_count": missing,
        }
        tolerance = value_tolerance if "value_usd" in field else ratio_tolerance
        if gap > tolerance or missing:
            failures.append(f"{field} fails independent coverage recomputation")
    coverage_merge_mismatch_count = int(coverage_check["_merge"].ne("both").sum())
    if coverage_merge_mismatch_count:
        failures.append("coverage recomputation key set differs from long output")

    policy_expected = independent_policy_expected(annual_window, config)
    policy_fields = [
        *config["policy"]["denominator_fields"],
        *config["policy"]["annual_mean_numerator_fields"].values(),
        *config["policy"]["recomputed_rate_fields"],
    ]
    policy_observed = (
        long.sort_values("connector_iso3")
        .drop_duplicates(["analysis_sector", "window_id"])
        [["analysis_sector", "window_id", *policy_fields]]
    )
    policy_check = policy_observed.merge(
        policy_expected,
        on=["analysis_sector", "window_id"],
        how="outer",
        validate="one_to_one",
        suffixes=("_observed", "_expected"),
        indicator=True,
    )
    policy_formula_gaps: dict[str, Any] = {}
    for field in policy_fields:
        gap, missing = maximum_absolute_gap(
            policy_check[f"{field}_observed"],
            policy_check[f"{field}_expected"],
        )
        policy_formula_gaps[field] = {
            "max_abs_gap": gap,
            "missing_mismatch_count": missing,
        }
        tolerance = (
            value_tolerance
            if "value" in field or "numerator" in field
            else ratio_tolerance
        )
        if gap > tolerance or missing:
            failures.append(f"{field} fails independent policy recomputation")
    policy_merge_mismatch_count = int(policy_check["_merge"].ne("both").sum())
    if policy_merge_mismatch_count:
        failures.append("policy recomputation key set differs from long output")

    denominator_exception_counts_by_window: dict[str, dict[str, int]] = {}
    for window_id in config["windows"]:
        window_policy = policy_expected.loc[
            policy_expected["window_id"].eq(window_id)
        ]
        zero_count = int(
            window_policy["treatment_zero_denominator_product_count"].sum()
        )
        no_mapping_count = int(
            window_policy["treatment_no_hs17_mapping_product_count"].sum()
        )
        denominator_exception_counts_by_window[window_id] = {
            "zero_denominator_eligible_products": zero_count,
            "no_hs17_mapping_eligible_products": no_mapping_count,
        }
        if zero_count != int(
            config["analysis"]["expected_zero_denominator_eligible_products"]
        ):
            failures.append(
                f"{window_id} zero-denominator eligible product count is not retained"
            )
        if no_mapping_count != int(
            config["analysis"]["expected_no_hs17_mapping_eligible_products"]
        ):
            failures.append(
                f"{window_id} no-HS2017-mapping eligible product count is not retained"
            )

    policy_pre_exposure_nonzero_count = int(
        comparison["sector_tariff_exposure_pre"].ne(0).sum()
    )
    policy_growth_fields = [
        column
        for column in comparison.columns
        if column.startswith("sector_tariff_exposure_")
        and ("growth" in column or "change" in column)
    ]
    if policy_pre_exposure_nonzero_count:
        failures.append("current M3.1 input has unexpected nonzero pre policy exposure")
    if policy_growth_fields:
        failures.append("M3.2 comparison output contains prohibited policy growth fields")

    repeated_fields = [
        *[
            f"china_to_usa_{suffix}"
            for suffix in [
                "value_usd_annual_mean",
                "source_row_count_annual_mean",
                "positive_product_count_annual_mean",
                "zero_source_product_count_annual_mean",
            ]
        ],
        *policy_fields,
    ]
    repeated_counts = long.groupby(["analysis_sector", "window_id"])[
        repeated_fields
    ].nunique(dropna=False)
    inconsistent_repeated_fields = {
        field: int(repeated_counts[field].gt(1).sum()) for field in repeated_fields
    }
    if any(inconsistent_repeated_fields.values()):
        failures.append("a China-USA or policy field varies across connectors")

    coverage_counts = long.groupby(["connector_iso3", "window_id"])[
        coverage_fields
    ].nunique(dropna=False)
    inconsistent_coverage_fields = {
        field: int(coverage_counts[field].gt(1).sum()) for field in coverage_fields
    }
    if any(inconsistent_coverage_fields.values()):
        failures.append("a coverage field varies across sectors")

    required_true_flags = [
        "china_to_usa_common_benchmark",
        "treatment_repeated_across_connectors",
        "coverage_repeated_across_sectors",
        "common_benchmarks_not_additive_across_connectors",
        "window_level_is_annual_mean",
        "included_value_share_uses_ratio_of_sums",
    ]
    required_true_flag_false_counts = {
        "long": {
            field: int((~long[field]).sum()) for field in required_true_flags
        },
        "comparison": {
            field: int((~comparison[field]).sum()) for field in required_true_flags
        },
    }
    if any(
        count
        for table_counts in required_true_flag_false_counts.values()
        for count in table_counts.values()
    ):
        failures.append("one or more required repeated/non-additive flags are false")

    twn_long = long.loc[long["connector_iso3"].eq("TWN")]
    twn_comparison = comparison.loc[comparison["connector_iso3"].eq("TWN")]
    twn_context = {
        "long_row_count": len(twn_long),
        "comparison_row_count": len(twn_comparison),
        "long_proxy_false_count": int((~twn_long["connector_is_proxy"]).sum()),
        "comparison_proxy_false_count": int(
            (~twn_comparison["connector_is_proxy"]).sum()
        ),
    }
    if (
        len(twn_long) != int(config["validation"]["expected_twn_long_rows"])
        or len(twn_comparison)
        != int(config["validation"]["expected_twn_comparison_rows"])
        or twn_context["long_proxy_false_count"]
        or twn_context["comparison_proxy_false_count"]
    ):
        failures.append("TWN rows or proxy flags are incomplete")

    long_aliases = resolve_stata_aliases(config, "long")
    comparison_aliases = resolve_stata_aliases(config, "comparison")
    stata_alias_validation = {
        "long": alias_validation(long, long_aliases),
        "comparison": alias_validation(comparison, comparison_aliases),
    }
    if not all(record["pass"] for record in stata_alias_validation.values()):
        failures.append("one or both Stata alias maps fail completeness or length checks")

    if not determinism["long"]["sha256_match"]:
        failures.append("long output deterministic SHA256 does not match")
    if not determinism["comparison"]["sha256_match"]:
        failures.append("comparison output deterministic SHA256 does not match")
    if not determinism["temporary_output_cleaned"]:
        failures.append("determinism temporary directory was not cleaned")

    required_long_numeric = [
        *[
            field
            for flow_name in config["trade_flows"]
            for field in [
                f"{flow_name}_value_usd_annual_mean",
                f"{flow_name}_source_row_count_annual_mean",
                f"{flow_name}_positive_product_count_annual_mean",
                f"{flow_name}_zero_source_product_count_annual_mean",
                f"{flow_name}_excluded_value_usd_annual_mean",
                f"{flow_name}_included_value_share",
            ]
        ],
        *policy_fields,
    ]
    required_comparison_numeric = [
        column
        for column in comparison.select_dtypes(include=[np.number]).columns
    ]
    required_numeric_missing_count = {
        "long": int(long[required_long_numeric].isna().sum().sum()),
        "comparison": int(
            comparison[required_comparison_numeric].isna().sum().sum()
        ),
    }
    if any(required_numeric_missing_count.values()):
        failures.append("one or more required current-sample numeric fields are missing")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": input_hash_checks,
        "input_row_count": len(annual),
        "input_column_count": len(annual.columns),
        "input_duplicate_key_count": input_duplicates,
        "input_arrow_schema_signature_sha256": input_schema_signature,
        "long_output_row_count": len(long),
        "long_output_column_count": len(long.columns),
        "long_output_duplicate_key_count": long_duplicates,
        "comparison_output_row_count": len(comparison),
        "comparison_output_column_count": len(comparison.columns),
        "comparison_output_duplicate_key_count": comparison_duplicates,
        "connector_count": len(observed_connectors),
        "sector_count": len(observed_sectors),
        "window_count": len(config["windows"]),
        "window_definition_checks": {
            "source_window_definition_match": window_context[
                "source_window_definition_match"
            ],
            "overlapping_window_years": window_context[
                "overlapping_window_years"
            ],
            "unassigned_annual_row_count": window_context[
                "unassigned_annual_row_count"
            ],
            "incomplete_connector_sector_cells_by_window": incomplete_by_window,
            "observed_year_count_ranges": observed_count_ranges,
        },
        "window_mean_reconciliation": mean_reconciliation,
        "window_diagnostic_reconciliation": diagnostic_reconciliation,
        "long_comparison_level_gaps": long_comparison_level_gaps,
        "growth_formula_checks": growth_formula_checks,
        "zero_and_defined_counts": zero_and_defined_counts,
        "negative_change_counts": negative_change_counts,
        "dh_out_of_bounds_count": dh_out_of_bounds_count,
        "infinite_growth_value_count": infinite_growth_value_count,
        "coverage_formula_gaps": coverage_formula_gaps,
        "coverage_merge_mismatch_count": coverage_merge_mismatch_count,
        "policy_formula_gaps": policy_formula_gaps,
        "policy_merge_mismatch_count": policy_merge_mismatch_count,
        "denominator_exception_counts_by_window": (
            denominator_exception_counts_by_window
        ),
        "policy_pre_exposure_nonzero_count": policy_pre_exposure_nonzero_count,
        "policy_growth_fields": policy_growth_fields,
        "inconsistent_repeated_fields": inconsistent_repeated_fields,
        "inconsistent_coverage_fields": inconsistent_coverage_fields,
        "required_true_flag_false_counts": required_true_flag_false_counts,
        "twn_checks": twn_context,
        "required_numeric_missing_count": required_numeric_missing_count,
        "stata_alias_validation": stata_alias_validation,
        "determinism_check": determinism,
        "value_tolerance_usd": value_tolerance,
        "ratio_tolerance": ratio_tolerance,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# M3.2 Connector Trade Sector Window Validation",
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
        f"- Long output: `{validation['outputs']['long']['path']}`",
        f"- Long rows / columns: `{validation['long_output_row_count']} / {validation['long_output_column_count']}`",
        f"- Comparison output: `{validation['outputs']['comparison']['path']}`",
        f"- Comparison rows / columns: `{validation['comparison_output_row_count']} / {validation['comparison_output_column_count']}`",
        f"- Long SHA256: `{validation['outputs']['long']['sha256']}`",
        f"- Comparison SHA256: `{validation['outputs']['comparison']['sha256']}`",
        "",
        "## Required gates",
        "",
        f"- Frozen input and time-window hashes match: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- Annual input rows / columns / duplicate keys: `{validation['input_row_count']} / {validation['input_column_count']} / {validation['input_duplicate_key_count']}`",
        f"- Long/comparison duplicate keys: `{validation['long_output_duplicate_key_count']} / {validation['comparison_output_duplicate_key_count']}`",
        f"- Every annual row assigned exactly once: `{'yes' if validation['window_definition_checks']['unassigned_annual_row_count'] == 0 and not validation['window_definition_checks']['overlapping_window_years'] else 'no'}`",
        f"- Deterministic long/comparison hashes match: `{'yes' if validation['determinism_check']['long']['sha256_match'] and validation['determinism_check']['comparison']['sha256_match'] else 'no'}`",
        f"- Required numeric missing counts, long/comparison: `{validation['required_numeric_missing_count']['long']} / {validation['required_numeric_missing_count']['comparison']}`",
        f"- DH out-of-bounds / infinite growth values: `{validation['dh_out_of_bounds_count']} / {validation['infinite_growth_value_count']}`",
        "",
        "## Window completeness",
        "",
        "| Window | Expected years | Observed min | Observed max | Incomplete cells |",
        "|---|---:|---:|---:|---:|",
    ]
    for window_id, record in validation["window_definition_checks"][
        "observed_year_count_ranges"
    ].items():
        lines.append(
            f"| `{window_id}` | {record['expected']} | {record['min']} | "
            f"{record['max']} | "
            f"{validation['window_definition_checks']['incomplete_connector_sector_cells_by_window'][window_id]} |"
        )
    lines.extend(
        [
            "",
            "## Flow reconstruction and growth checks",
            "",
            "| Flow | Max mean×years gap USD | Pre zero | Post zero | Log defined | Negative post-pre changes | Max change gap | Max DH gap | Max log gap |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for flow_name in validation["window_mean_reconciliation"]:
        checks = validation["growth_formula_checks"][flow_name]
        counts = validation["zero_and_defined_counts"][flow_name]
        lines.append(
            f"| `{flow_name}` | "
            f"{validation['window_mean_reconciliation'][flow_name]['max_abs_window_gap_usd']:.6f} | "
            f"{counts['pre_zero']} | {counts['post_zero']} | {counts['log_defined']} | "
            f"{validation['negative_change_counts'][flow_name]} | "
            f"{checks['change_post_pre']['max_abs_gap']:.3e} | "
            f"{checks['dh_growth_post_pre']['max_abs_gap']:.3e} | "
            f"{checks['log_growth_post_pre']['max_abs_gap']:.3e} |"
        )
    lines.extend(
        [
            "",
            "## Coverage and policy recomputation",
            "",
            f"- Coverage key mismatches: `{validation['coverage_merge_mismatch_count']}`.",
            f"- Policy key mismatches: `{validation['policy_merge_mismatch_count']}`.",
            f"- Zero-denominator / no-HS2017-mapping eligible products retained in each window: `{validation['denominator_exception_counts_by_window']['pre']['zero_denominator_eligible_products']} / {validation['denominator_exception_counts_by_window']['pre']['no_hs17_mapping_eligible_products']}`.",
            f"- Nonzero pre policy exposure cells / policy growth fields: `{validation['policy_pre_exposure_nonzero_count']} / {len(validation['policy_growth_fields'])}`.",
            f"- Repeated China-to-USA/policy inconsistencies: `{sum(validation['inconsistent_repeated_fields'].values())}`.",
            f"- Repeated coverage inconsistencies: `{sum(validation['inconsistent_coverage_fields'].values())}`.",
            f"- TWN long/comparison rows and false proxy flags: `{validation['twn_checks']['long_row_count']} / {validation['twn_checks']['comparison_row_count']} / {validation['twn_checks']['long_proxy_false_count'] + validation['twn_checks']['comparison_proxy_false_count']}`.",
            "",
            "## Stata interface",
            "",
            f"- Long aliases: `{validation['stata_alias_validation']['long']['alias_count']}`; maximum length `{validation['stata_alias_validation']['long']['maximum_alias_length']}`; pass `{'yes' if validation['stata_alias_validation']['long']['pass'] else 'no'}`.",
            f"- Comparison aliases: `{validation['stata_alias_validation']['comparison']['alias_count']}`; maximum length `{validation['stata_alias_validation']['comparison']['maximum_alias_length']}`; pass `{'yes' if validation['stata_alias_validation']['comparison']['pass'] else 'no'}`.",
            "- Canonical files remain Parquet. No `.dta` is generated before M7.",
            "",
            "## Interpretation boundaries",
            "",
            "- Window levels are annual means over complete 4/2/5-year windows; unequal-length window sums are not compared.",
            "- Included-value shares are ratios of summed eligible and full-universe values, not averages of annual shares.",
            "- Negative changes and growth are retained. Current data have no pre/post zero flow cells, but zero/defined flags remain part of the schema.",
            "- Policy pre exposure can be zero. No percentage or log growth is computed for policy exposure.",
            "- This module does not define small-base thresholds, abnormal-growth treatment, winsorization, replacement ratios, rankings, production variables, or structural moments.",
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


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def read_input(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pa.Schema, dict[str, Any]]:
    annual_path = project_root / config["inputs"]["connector_trade_sector_year"]["path"]
    time_path = project_root / config["inputs"]["time_windows"]["path"]
    table = pq.read_table(annual_path)
    return table.to_pandas(), table.schema, load_yaml(time_path)


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    candidate_long: Path,
    candidate_comparison: Path,
) -> dict[str, Any]:
    temp_directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if temp_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse non-empty or pre-existing temp directory: {temp_directory}"
        )
    temp_directory.mkdir(parents=True)
    second_long = temp_directory / "connector_trade_sector_window_second.parquet"
    second_comparison = (
        temp_directory / "connector_trade_sector_window_comparison_second.parquet"
    )
    try:
        annual, _, source_windows = read_input(project_root, config)
        long, comparison, _, _ = build_outputs(annual, config, source_windows)
        write_parquet(long, second_long)
        write_parquet(comparison, second_comparison)
        result = {
            "required": bool(
                config["validation"]["require_deterministic_parquet_sha256"]
            ),
            "long": {
                "candidate_sha256": sha256(candidate_long),
                "second_build_sha256": sha256(second_long),
            },
            "comparison": {
                "candidate_sha256": sha256(candidate_comparison),
                "second_build_sha256": sha256(second_comparison),
            },
            "temporary_directory": temp_directory.relative_to(
                project_root
            ).as_posix(),
        }
        result["long"]["sha256_match"] = (
            result["long"]["candidate_sha256"]
            == result["long"]["second_build_sha256"]
        )
        result["comparison"]["sha256_match"] = (
            result["comparison"]["candidate_sha256"]
            == result["comparison"]["second_build_sha256"]
        )
    finally:
        remove_owned_temp_directory(temp_directory)
    result["temporary_output_cleaned"] = not temp_directory.exists()
    return result


def relative_or_absolute(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate the M3.2 connector-sector pre/shock/post "
            "window and post-pre comparison panels."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/connector_trade_sector_window_rules.yaml"),
    )
    parser.add_argument("--long-output", type=Path)
    parser.add_argument("--comparison-output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    long_output = relative_or_absolute(
        project_root,
        args.long_output or Path(config["outputs"]["long"]["path"]),
    ).resolve()
    comparison_output = relative_or_absolute(
        project_root,
        args.comparison_output or Path(config["outputs"]["comparison"]["path"]),
    ).resolve()
    validation_json = relative_or_absolute(
        project_root,
        args.validation_json or Path(config["validation_outputs"]["json"]),
    ).resolve()
    validation_md = relative_or_absolute(
        project_root,
        args.validation_md or Path(config["validation_outputs"]["markdown"]),
    ).resolve()
    final_paths = [long_output, comparison_output, validation_json, validation_md]
    for path in final_paths:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    candidate_directory = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    if candidate_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse pre-existing candidate directory: {candidate_directory}"
        )
    candidate_directory.mkdir(parents=True)
    candidate_long = candidate_directory / long_output.name
    candidate_comparison = candidate_directory / comparison_output.name

    try:
        input_hash_checks = {
            "connector_trade_sector_year": (
                sha256(
                    project_root
                    / config["inputs"]["connector_trade_sector_year"]["path"]
                )
                == config["inputs"]["connector_trade_sector_year"]["sha256"]
            ),
            "time_windows": (
                sha256(project_root / config["inputs"]["time_windows"]["path"])
                == config["inputs"]["time_windows"]["sha256"]
            ),
        }
        annual, annual_schema, source_windows = read_input(project_root, config)
        long, comparison, window_context, annual_window = build_outputs(
            annual, config, source_windows
        )
        long_table = write_parquet(long, candidate_long)
        comparison_table = write_parquet(comparison, candidate_comparison)
        determinism = deterministic_rebuild(
            project_root,
            config,
            candidate_long,
            candidate_comparison,
        )
        validation = validate(
            config,
            annual,
            annual_schema,
            annual_window,
            long,
            comparison,
            window_context,
            input_hash_checks,
            determinism,
        )
        validation.update(
            {
                "validation_version": 1,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path.relative_to(project_root).as_posix(),
                "config_sha256": sha256(config_path),
                "construction_version": config["version"],
                "long_schema_version": config["long_schema_version"],
                "comparison_schema_version": config[
                    "comparison_schema_version"
                ],
                "outputs": {
                    "long": {
                        "path": long_output.relative_to(project_root).as_posix(),
                        "sha256": sha256(candidate_long),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in long_table.schema
                        ],
                    },
                    "comparison": {
                        "path": comparison_output.relative_to(
                            project_root
                        ).as_posix(),
                        "sha256": sha256(candidate_comparison),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in comparison_table.schema
                        ],
                    },
                },
                "candidate_temp_directory": candidate_directory.relative_to(
                    project_root
                ).as_posix(),
            }
        )
        if validation["validation_status"] != "PASS":
            print(json.dumps(validation, ensure_ascii=False, indent=2))
            raise SystemExit(1)

        long_output.parent.mkdir(parents=True, exist_ok=True)
        comparison_output.parent.mkdir(parents=True, exist_ok=True)
        candidate_long.replace(long_output)
        candidate_comparison.replace(comparison_output)
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
                    "long_output_rows": validation["long_output_row_count"],
                    "comparison_output_rows": validation[
                        "comparison_output_row_count"
                    ],
                    "long_output_sha256": validation["outputs"]["long"]["sha256"],
                    "comparison_output_sha256": validation["outputs"][
                        "comparison"
                    ]["sha256"],
                    "deterministic_long_sha256_match": determinism["long"][
                        "sha256_match"
                    ],
                    "deterministic_comparison_sha256_match": determinism[
                        "comparison"
                    ]["sha256_match"],
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
