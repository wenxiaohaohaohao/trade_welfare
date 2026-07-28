from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


COMMON_KEY = ["connector_iso3", "analysis_sector"]
ANNUAL_KEY = [*COMMON_KEY, "year"]
TIME_KEY = [*COMMON_KEY, "flow_id", "window_spec_id"]
SOURCE_KEY = [*COMMON_KEY, "source_bloc_id"]
EXPOSURE_KEY = [*COMMON_KEY, "exposure_definition_id"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return value


def schema_signature(schema: pa.Schema) -> str:
    payload = [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]
    encoded = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative_or_absolute(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


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


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def safe_divide(numerator: float, denominator: float) -> float:
    if pd.isna(numerator) or pd.isna(denominator) or float(denominator) == 0:
        return float("nan")
    return float(numerator) / float(denominator)


def dh_growth(pre: float, comparison: float) -> float:
    if pd.isna(pre) or pd.isna(comparison):
        return float("nan")
    pre = float(pre)
    comparison = float(comparison)
    if pre == 0 and comparison == 0:
        return float("nan")
    denominator = comparison + pre
    if denominator == 0:
        return float("nan")
    return 2.0 * (comparison - pre) / denominator


def log_growth(pre: float, comparison: float) -> float:
    if (
        pd.isna(pre)
        or pd.isna(comparison)
        or float(pre) <= 0
        or float(comparison) <= 0
    ):
        return float("nan")
    return math.log(float(comparison)) - math.log(float(pre))


def nullable_same_sign(left: float, right: float) -> bool | pd._libs.missing.NAType:
    if pd.isna(left) or pd.isna(right):
        return pd.NA
    return bool(np.sign(float(left)) == np.sign(float(right)))


def maximum_absolute_gap(
    actual: pd.Series,
    expected: pd.Series,
) -> tuple[float, int]:
    actual_numeric = pd.to_numeric(actual, errors="coerce").astype("float64")
    expected_numeric = pd.to_numeric(expected, errors="coerce").astype("float64")
    missing_mismatch = int(
        (actual_numeric.isna() ^ expected_numeric.isna()).sum()
    )
    usable = actual_numeric.notna() & expected_numeric.notna()
    gap = (
        float(
            (
                actual_numeric.loc[usable]
                - expected_numeric.loc[usable]
            )
            .abs()
            .max()
        )
        if usable.any()
        else 0.0
    )
    return gap, missing_mismatch


def mismatch_count(actual: pd.Series, expected: pd.Series) -> int:
    actual = actual.reset_index(drop=True)
    expected = expected.reset_index(drop=True)
    both_missing = actual.isna() & expected.isna()
    equal = actual.eq(expected).fillna(False)
    return int((~(both_missing | equal)).sum())


def alias_validation(
    frame: pd.DataFrame,
    aliases: dict[str, str],
) -> dict[str, Any]:
    missing = sorted(set(frame.columns) - set(aliases))
    extra = sorted(set(aliases) - set(frame.columns))
    values = list(aliases.values())
    duplicates = sorted({value for value in values if values.count(value) > 1})
    over_length = {
        field: alias for field, alias in aliases.items() if len(alias) > 32
    }
    invalid = {
        field: alias
        for field, alias in aliases.items()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias or "") is None
    }
    return {
        "pass": not missing
        and not extra
        and not duplicates
        and not over_length
        and not invalid,
        "alias_count": len(aliases),
        "maximum_alias_length": max((len(value) for value in values), default=0),
        "missing_fields": missing,
        "extra_fields": extra,
        "duplicate_aliases": duplicates,
        "over_32_characters": over_length,
        "invalid_aliases": invalid,
    }


def nested_value(mapping: dict[str, Any], path: list[str]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise KeyError(f"Missing nested YAML path: {path}")
        value = value[key]
    return value


def ordered_common(common: pd.DataFrame) -> pd.DataFrame:
    order_fields = [
        "connector_group_order",
        "connector_order_within_group",
        "analysis_sector_order",
    ]
    return common.sort_values(order_fields, kind="mergesort").reset_index(drop=True)


def read_inputs(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pa.Schema,
    pd.DataFrame,
    pa.Schema,
    dict[str, Any],
    dict[str, Any],
]:
    common_table = pq.read_table(
        project_root / config["inputs"]["common_panel"]["path"]
    )
    annual_table = pq.read_table(
        project_root / config["inputs"]["annual_sector_panel"]["path"]
    )
    time_windows = load_yaml(
        project_root / config["inputs"]["time_windows"]["path"]
    )
    country_groups = load_yaml(
        project_root / config["inputs"]["country_groups"]["path"]
    )
    return (
        common_table.to_pandas(),
        common_table.schema,
        annual_table.to_pandas(),
        annual_table.schema,
        time_windows,
        country_groups,
    )


def window_statistics(
    annual_group: pd.DataFrame,
    flow: dict[str, Any],
    start: int,
    end: int,
) -> dict[str, Any]:
    selected = annual_group.loc[
        annual_group["year"].between(start, end)
    ].sort_values("year")
    value = selected[flow["annual_value_field"]].astype("float64")
    excluded = selected[flow["annual_excluded_value_field"]].astype("float64")
    source_rows = selected[flow["annual_source_row_count_field"]].astype(
        "float64"
    )
    transitions = [
        dh_growth(float(value.iloc[index - 1]), float(value.iloc[index]))
        for index in range(1, len(value))
    ]
    usable_transitions = [
        item for item in transitions if not pd.isna(item)
    ]
    annual_sd = (
        float(np.std(usable_transitions, ddof=1))
        if len(usable_transitions) >= 2
        else float("nan")
    )
    positive_share = (
        float((np.diff(value.to_numpy()) > 0).mean())
        if len(value) >= 2
        else float("nan")
    )
    eligible_sum = float(value.sum())
    excluded_sum = float(excluded.sum())
    return {
        "observed_year_count": int(selected["year"].nunique()),
        "scale": float(value.mean()),
        "included_value_share": safe_divide(
            eligible_sum, eligible_sum + excluded_sum
        ),
        "source_row_count_annual_mean": float(source_rows.mean()),
        "annual_growth_transition_count": len(usable_transitions),
        "annual_dh_growth_sd": annual_sd,
        "positive_growth_year_share": positive_share,
    }


def build_time_window_output(
    common: pd.DataFrame,
    annual: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    settings = config["time_window_sensitivity"]
    base = settings["base_period"]
    base_start = int(base["start"])
    base_end = int(base["end"])
    reference_spec = settings["reference_spec"]
    rows: list[dict[str, Any]] = []
    annual_index = {
        key: group.copy()
        for key, group in annual.groupby(COMMON_KEY, sort=False, observed=True)
    }
    for _, common_row in ordered_common(common).iterrows():
        key = (common_row["connector_iso3"], common_row["analysis_sector"])
        annual_group = annual_index[key]
        for flow_id, flow in settings["flows"].items():
            pre = window_statistics(
                annual_group, flow, base_start, base_end
            )
            for spec_id, spec in settings["specifications"].items():
                comparison_start = int(spec["start"])
                comparison_end = int(spec["end"])
                comparison = window_statistics(
                    annual_group, flow, comparison_start, comparison_end
                )
                pre_scale = pre["scale"]
                comparison_scale = comparison["scale"]
                level_change = comparison_scale - pre_scale
                dh = dh_growth(pre_scale, comparison_scale)
                log = log_growth(pre_scale, comparison_scale)
                rows.append(
                    {
                        "connector_iso3": common_row["connector_iso3"],
                        "analysis_sector": common_row["analysis_sector"],
                        "connector_group": common_row["connector_group"],
                        "connector_baci_code": common_row[
                            "connector_baci_code"
                        ],
                        "connector_is_proxy": common_row[
                            "connector_is_proxy"
                        ],
                        "flow_id": flow_id,
                        "flow_order": int(flow["order"]),
                        "window_spec_id": spec_id,
                        "window_spec_order": int(spec["order"]),
                        "reference_window_spec_id": reference_spec,
                        "base_start_year": base_start,
                        "base_end_year": base_end,
                        "comparison_start_year": comparison_start,
                        "comparison_end_year": comparison_end,
                        "expected_base_year_count": base_end - base_start + 1,
                        "observed_base_year_count": pre[
                            "observed_year_count"
                        ],
                        "expected_comparison_year_count": (
                            comparison_end - comparison_start + 1
                        ),
                        "observed_comparison_year_count": comparison[
                            "observed_year_count"
                        ],
                        "complete_window_pair": bool(
                            pre["observed_year_count"]
                            == base_end - base_start + 1
                            and comparison["observed_year_count"]
                            == comparison_end - comparison_start + 1
                        ),
                        "pre_trade_scale_usd": pre_scale,
                        "comparison_trade_scale_usd": comparison_scale,
                        "level_change_usd": level_change,
                        "dh_growth": dh,
                        "log_growth": log,
                        "pre_zero_flag": bool(pre_scale == 0),
                        "comparison_zero_flag": bool(comparison_scale == 0),
                        "dh_growth_defined": bool(not pd.isna(dh)),
                        "log_growth_defined": bool(not pd.isna(log)),
                        "annual_growth_transition_count": comparison[
                            "annual_growth_transition_count"
                        ],
                        "annual_dh_growth_sd": comparison[
                            "annual_dh_growth_sd"
                        ],
                        "positive_growth_year_share": comparison[
                            "positive_growth_year_share"
                        ],
                        "included_value_share_pre": pre[
                            "included_value_share"
                        ],
                        "included_value_share_comparison": comparison[
                            "included_value_share"
                        ],
                        "source_row_count_annual_mean_pre": pre[
                            "source_row_count_annual_mean"
                        ],
                        "source_row_count_annual_mean_comparison": comparison[
                            "source_row_count_annual_mean"
                        ],
                        "flow_is_common_benchmark": bool(
                            flow["common_benchmark"]
                        ),
                        "common_benchmark_not_additive_across_connectors": bool(
                            flow["common_benchmark"]
                        ),
                        "trade_value_unit": common_row["trade_value_unit"],
                        "baci_absence_treated_as_zero": bool(
                            annual_group[
                                "baci_absence_treated_as_zero"
                            ].all()
                        ),
                        "window_level_is_annual_mean": True,
                        "included_value_share_uses_ratio_of_sums": True,
                        "sensitivity_variables_constructed": True,
                        "ranking_variables_constructed": False,
                        "m3_common_panel_version": common_row[
                            "m3_common_panel_version"
                        ],
                        "m3_sector_aggregation_version": annual_group[
                            "m3_sector_aggregation_version"
                        ].iloc[0],
                        "m3_sensitivity_version": config["version"],
                        "rules_config_sha256": config_hash,
                        "schema_version": config["outputs"]["time_window"][
                            "schema_version"
                        ],
                    }
                )
    output = pd.DataFrame(rows)
    reference = output.loc[
        output["window_spec_id"].eq(reference_spec),
        [*COMMON_KEY, "flow_id", "level_change_usd", "dh_growth", "log_growth"],
    ].rename(
        columns={
            "level_change_usd": "primary_level_change_usd",
            "dh_growth": "primary_dh_growth",
            "log_growth": "primary_log_growth",
        }
    )
    output = output.merge(
        reference,
        on=[*COMMON_KEY, "flow_id"],
        how="left",
        validate="many_to_one",
        sort=False,
    )
    output["level_change_difference_from_primary_usd"] = (
        output["level_change_usd"] - output["primary_level_change_usd"]
    )
    output["dh_growth_difference_from_primary"] = (
        output["dh_growth"] - output["primary_dh_growth"]
    )
    output["log_growth_difference_from_primary"] = (
        output["log_growth"] - output["primary_log_growth"]
    )
    output["same_level_change_direction_as_primary"] = [
        nullable_same_sign(value, reference_value)
        for value, reference_value in zip(
            output["level_change_usd"],
            output["primary_level_change_usd"],
            strict=True,
        )
    ]
    output["same_dh_growth_direction_as_primary"] = [
        nullable_same_sign(value, reference_value)
        for value, reference_value in zip(
            output["dh_growth"],
            output["primary_dh_growth"],
            strict=True,
        )
    ]
    output = output[
        list(config["outputs"]["time_window"]["stata_aliases"].keys())
    ]
    if output.duplicated(TIME_KEY).any():
        raise ValueError("Time-window sensitivity output has duplicate keys")
    return output.reset_index(drop=True)


def source_field_values(
    row: pd.Series,
    prefix: str,
) -> dict[str, Any]:
    return {
        "input_value_usd_pre": row[f"{prefix}_input_value_usd_pre"],
        "input_value_usd_post": row[f"{prefix}_input_value_usd_post"],
        "input_gain_usd": row[f"{prefix}_input_gain_usd"],
        "input_dh_growth_raw": row[f"{prefix}_input_dh_growth_raw"],
        "input_log_growth_raw": row[f"{prefix}_input_log_growth_raw"],
        "input_small_base_flag": row[f"{prefix}_input_small_base_flag"],
        "input_dh_primary_eligible": row[
            f"{prefix}_input_dh_primary_eligible"
        ],
        "input_abnormal_growth_flag": row[
            f"{prefix}_input_abnormal_growth_flag"
        ],
        "input_to_export_ratio_pre_defined": row[
            f"{prefix}_input_to_export_ratio_pre_defined"
        ],
        "input_to_export_ratio_pre": row[
            f"{prefix}_input_to_export_ratio_pre"
        ],
        "input_to_export_ratio_post_defined": row[
            f"{prefix}_input_to_export_ratio_post_defined"
        ],
        "input_to_export_ratio_post": row[
            f"{prefix}_input_to_export_ratio_post"
        ],
        "input_to_export_ratio_change": row[
            f"{prefix}_input_to_export_ratio_change"
        ],
        "active_product_count": row[f"{prefix}_active_product_count"],
        "positive_weight_product_count": row[
            f"{prefix}_positive_weight_product_count"
        ],
        "correlation_low_n_flag": row[
            f"{prefix}_correlation_low_n_flag"
        ],
        "weighted_correlation_low_n_flag": row[
            f"{prefix}_weighted_correlation_low_n_flag"
        ],
        "product_change_correlation": row[
            f"{prefix}_product_change_correlation"
        ],
        "weighted_product_change_correlation": row[
            f"{prefix}_weighted_product_change_correlation"
        ],
        "both_legs_positive_product_count": row[
            f"{prefix}_both_legs_positive_product_count"
        ],
        "both_legs_positive_product_share": row[
            f"{prefix}_both_legs_positive_product_share"
        ],
        "both_legs_positive_active_share": row[
            f"{prefix}_both_legs_positive_active_share"
        ],
        "both_legs_positive_export_gain_share": row[
            f"{prefix}_both_legs_positive_export_gain_share"
        ],
        "triple_condition_product_count": row[
            f"{prefix}_triple_condition_product_count"
        ],
        "triple_condition_product_share": row[
            f"{prefix}_triple_condition_product_share"
        ],
        "triple_condition_active_share": row[
            f"{prefix}_triple_condition_active_share"
        ],
        "triple_condition_export_gain_share": row[
            f"{prefix}_triple_condition_export_gain_share"
        ],
    }


def build_source_bloc_output(
    common: pd.DataFrame,
    country_groups: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    settings = config["source_bloc_sensitivity"]
    reference_spec = settings["reference_spec"]
    reference_prefix = settings["specifications"][reference_spec][
        "field_prefix"
    ]
    rows: list[dict[str, Any]] = []
    for _, common_row in ordered_common(common).iterrows():
        reference = source_field_values(common_row, reference_prefix)
        connector = str(common_row["connector_iso3"])
        for spec_id, spec in settings["specifications"].items():
            members = list(
                nested_value(country_groups, spec["country_group_path"])
            )
            values = source_field_values(common_row, spec["field_prefix"])
            self_excluded = connector in members
            row: dict[str, Any] = {
                "connector_iso3": connector,
                "analysis_sector": common_row["analysis_sector"],
                "connector_group": common_row["connector_group"],
                "connector_baci_code": common_row["connector_baci_code"],
                "connector_is_proxy": common_row["connector_is_proxy"],
                "source_bloc_id": spec_id,
                "source_bloc_order": int(spec["order"]),
                "reference_source_bloc_id": reference_spec,
                "source_bloc_members_configured": ";".join(members),
                "source_bloc_member_count_configured": len(members),
                "source_bloc_member_count_after_self_exclusion": (
                    len(members) - int(self_excluded)
                ),
                "connector_self_trade_excluded": bool(self_excluded),
                "source_bloc_definitions_nested": bool(
                    settings["comparison_is_nested"]
                ),
                **values,
                "input_value_usd_pre_difference_from_china_only": (
                    values["input_value_usd_pre"]
                    - reference["input_value_usd_pre"]
                ),
                "input_value_usd_post_difference_from_china_only": (
                    values["input_value_usd_post"]
                    - reference["input_value_usd_post"]
                ),
                "input_gain_usd_difference_from_china_only": (
                    values["input_gain_usd"] - reference["input_gain_usd"]
                ),
                "input_dh_growth_difference_from_china_only": (
                    values["input_dh_growth_raw"]
                    - reference["input_dh_growth_raw"]
                ),
                "input_log_growth_difference_from_china_only": (
                    values["input_log_growth_raw"]
                    - reference["input_log_growth_raw"]
                ),
                "input_to_export_ratio_pre_difference_from_china_only": (
                    values["input_to_export_ratio_pre"]
                    - reference["input_to_export_ratio_pre"]
                ),
                "input_to_export_ratio_post_difference_from_china_only": (
                    values["input_to_export_ratio_post"]
                    - reference["input_to_export_ratio_post"]
                ),
                "input_to_export_ratio_change_difference_from_china_only": (
                    values["input_to_export_ratio_change"]
                    - reference["input_to_export_ratio_change"]
                ),
                "product_correlation_difference_from_china_only": (
                    values["product_change_correlation"]
                    - reference["product_change_correlation"]
                ),
                "weighted_product_correlation_difference_from_china_only": (
                    values["weighted_product_change_correlation"]
                    - reference["weighted_product_change_correlation"]
                ),
                "both_legs_positive_product_share_difference_from_china_only": (
                    values["both_legs_positive_product_share"]
                    - reference["both_legs_positive_product_share"]
                ),
                "triple_condition_product_share_difference_from_china_only": (
                    values["triple_condition_product_share"]
                    - reference["triple_condition_product_share"]
                ),
                "same_input_gain_direction_as_china_only": nullable_same_sign(
                    values["input_gain_usd"], reference["input_gain_usd"]
                ),
                "same_input_dh_growth_direction_as_china_only": (
                    nullable_same_sign(
                        values["input_dh_growth_raw"],
                        reference["input_dh_growth_raw"],
                    )
                ),
                "same_input_to_export_ratio_change_direction_as_china_only": (
                    nullable_same_sign(
                        values["input_to_export_ratio_change"],
                        reference["input_to_export_ratio_change"],
                    )
                ),
                "same_product_correlation_direction_as_china_only": (
                    nullable_same_sign(
                        values["product_change_correlation"],
                        reference["product_change_correlation"],
                    )
                ),
                "source_bloc_comparison_is_nested": bool(
                    settings["comparison_is_nested"]
                ),
                "trade_value_unit": common_row["trade_value_unit"],
                "sensitivity_variables_constructed": True,
                "ranking_variables_constructed": False,
                "m3_common_panel_version": common_row[
                    "m3_common_panel_version"
                ],
                "m3_sensitivity_version": config["version"],
                "rules_config_sha256": config_hash,
                "schema_version": config["outputs"]["source_bloc"][
                    "schema_version"
                ],
            }
            rows.append(row)
    output = pd.DataFrame(rows)[
        list(config["outputs"]["source_bloc"]["stata_aliases"].keys())
    ]
    if output.duplicated(SOURCE_KEY).any():
        raise ValueError("Source-bloc sensitivity output has duplicate keys")
    return output.reset_index(drop=True)


def optional_row_value(
    row: pd.Series,
    definition: dict[str, Any],
    field_key: str,
    constant_key: str | None = None,
) -> float:
    if field_key in definition:
        return float(row[definition[field_key]])
    if constant_key is not None and constant_key in definition:
        return float(definition[constant_key])
    return float("nan")


def build_exposure_definition_output(
    common: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    definitions = config["exposure_definition_sensitivity"]["definitions"]
    for _, common_row in ordered_common(common).iterrows():
        for definition_id, definition in definitions.items():
            supports_pre_post = bool(
                definition["supports_pre_post_comparison"]
            )
            if supports_pre_post:
                measure_pre = float(
                    common_row[definition["measure_pre_field"]]
                )
                measure_post = float(
                    common_row[definition["measure_post_field"]]
                )
                measure_change = float(
                    common_row[definition["measure_change_field"]]
                )
                measure_value = measure_post
            else:
                measure_pre = float("nan")
                measure_post = float("nan")
                measure_change = float("nan")
                measure_value = float(
                    common_row[definition["measure_value_field"]]
                )
            numerator_pre = optional_row_value(
                common_row, definition, "numerator_pre_field"
            )
            denominator_pre = optional_row_value(
                common_row, definition, "denominator_pre_field"
            )
            numerator_post_or_gain = optional_row_value(
                common_row, definition, "numerator_post_or_gain_field"
            )
            denominator_post_or_gain = optional_row_value(
                common_row, definition, "denominator_post_or_gain_field"
            )
            coverage_pre = optional_row_value(
                common_row,
                definition,
                "coverage_pre_field",
                "coverage_pre_constant",
            )
            coverage_post_or_gain = optional_row_value(
                common_row,
                definition,
                "coverage_post_or_gain_field",
                "coverage_post_or_gain_constant",
            )
            threshold_value = optional_row_value(
                common_row,
                definition,
                "threshold_value_field",
                "threshold_value_constant",
            )
            rows.append(
                {
                    "connector_iso3": common_row["connector_iso3"],
                    "analysis_sector": common_row["analysis_sector"],
                    "connector_group": common_row["connector_group"],
                    "connector_baci_code": common_row[
                        "connector_baci_code"
                    ],
                    "connector_is_proxy": common_row[
                        "connector_is_proxy"
                    ],
                    "exposure_definition_id": definition_id,
                    "exposure_definition_order": int(definition["order"]),
                    "exposure_definition_label": definition["label"],
                    "measure_basis": definition["measure_basis"],
                    "threshold_rule": definition["threshold_rule"],
                    "supports_pre_post_comparison": supports_pre_post,
                    "uses_positive_export_gain_denominator": bool(
                        definition["uses_positive_export_gain_denominator"]
                    ),
                    "cross_definition_numeric_difference_forbidden": True,
                    "exposure_measure_unit": definition["measure_unit"],
                    "exposure_measure_pre": measure_pre,
                    "exposure_measure_post": measure_post,
                    "exposure_measure_change": measure_change,
                    "exposure_measure_value": measure_value,
                    "measure_value_basis": definition[
                        "measure_value_basis"
                    ],
                    "measure_defined": bool(not pd.isna(measure_value)),
                    "exposure_measure_in_unit_interval": bool(
                        not pd.isna(measure_value)
                        and -1e-12 <= measure_value <= 1.0 + 1e-12
                    ),
                    "pre_post_missing_by_design": bool(
                        not supports_pre_post
                    ),
                    "numerator_usd_pre": numerator_pre,
                    "denominator_usd_pre": denominator_pre,
                    "numerator_usd_post_or_gain": numerator_post_or_gain,
                    "denominator_usd_post_or_gain": denominator_post_or_gain,
                    "value_coverage_share_pre": coverage_pre,
                    "value_coverage_share_post_or_gain": (
                        coverage_post_or_gain
                    ),
                    "high_exposure_threshold_value": threshold_value,
                    "post_exposure_observed_product_count": common_row[
                        "post_exposure_observed_product_count"
                    ],
                    "post_exposure_missing_product_count": common_row[
                        "post_exposure_missing_product_count"
                    ],
                    "post_exposure_missing_product_share": common_row[
                        "post_exposure_missing_product_share"
                    ],
                    "positive_exposure_product_count": common_row[
                        "positive_exposure_product_count"
                    ],
                    "top_quartile_positive_exposure_product_count": (
                        common_row[
                            "top_quartile_positive_exposure_product_count"
                        ]
                    ),
                    "sector_positive_exposure_p75_cutoff": common_row[
                        "sector_positive_exposure_p75_cutoff"
                    ],
                    "underlying_policy_repeated_across_connectors": True,
                    "exposure_measure_not_additive_across_connectors": True,
                    "sensitivity_variables_constructed": True,
                    "ranking_variables_constructed": False,
                    "trade_value_unit": common_row["trade_value_unit"],
                    "treatment_concept": common_row["treatment_concept"],
                    "historical_exclusions_applied": common_row[
                        "historical_exclusions_applied"
                    ],
                    "four_year_review_2024_included": common_row[
                        "four_year_review_2024_included"
                    ],
                    "m3_common_panel_version": common_row[
                        "m3_common_panel_version"
                    ],
                    "m3_sensitivity_version": config["version"],
                    "rules_config_sha256": config_hash,
                    "schema_version": config["outputs"][
                        "exposure_definition"
                    ]["schema_version"],
                }
            )
    output = pd.DataFrame(rows)[
        list(
            config["outputs"]["exposure_definition"][
                "stata_aliases"
            ].keys()
        )
    ]
    if output.duplicated(EXPOSURE_KEY).any():
        raise ValueError(
            "Exposure-definition sensitivity output has duplicate keys"
        )
    return output.reset_index(drop=True)


def input_contract(
    project_root: Path,
    frame: pd.DataFrame,
    schema: pa.Schema,
    specification: dict[str, Any],
    version_field: str,
) -> dict[str, Any]:
    path = project_root / specification["path"]
    observed_versions = sorted(
        str(value) for value in frame[version_field].dropna().unique()
    )
    key = list(specification["natural_key"])
    return {
        "path": specification["path"],
        "observed_sha256": sha256(path),
        "expected_sha256": specification["sha256"],
        "hash_match": sha256(path) == specification["sha256"],
        "observed_rows": len(frame),
        "expected_rows": int(specification["expected_rows"]),
        "row_count_match": len(frame) == int(specification["expected_rows"]),
        "observed_columns": len(frame.columns),
        "expected_columns": int(specification["expected_columns"]),
        "column_count_match": len(frame.columns)
        == int(specification["expected_columns"]),
        "observed_schema_signature_sha256": schema_signature(schema),
        "expected_schema_signature_sha256": specification[
            "arrow_schema_signature_sha256"
        ],
        "schema_signature_match": schema_signature(schema)
        == specification["arrow_schema_signature_sha256"],
        "natural_key": key,
        "duplicate_key_count": int(frame.duplicated(key).sum()),
        "observed_versions": observed_versions,
        "expected_version": specification[
            "expected_construction_version"
        ],
        "version_match": observed_versions
        == [specification["expected_construction_version"]],
        "schema_version_match": sorted(
            str(value) for value in frame["schema_version"].dropna().unique()
        )
        == [specification["expected_schema_version"]],
    }


def time_formula_validation(
    time_output: pd.DataFrame,
    common: pd.DataFrame,
    annual: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    settings = config["time_window_sensitivity"]
    flow_map = settings["flows"]
    reference_spec = settings["reference_spec"]
    annual_index = {
        key: group.copy()
        for key, group in annual.groupby(COMMON_KEY, sort=False, observed=True)
    }
    expected_numeric: dict[str, list[float]] = {
        field: []
        for field in [
            "observed_base_year_count",
            "observed_comparison_year_count",
            "pre_trade_scale_usd",
            "comparison_trade_scale_usd",
            "level_change_usd",
            "dh_growth",
            "log_growth",
            "annual_growth_transition_count",
            "annual_dh_growth_sd",
            "positive_growth_year_share",
            "included_value_share_pre",
            "included_value_share_comparison",
            "source_row_count_annual_mean_pre",
            "source_row_count_annual_mean_comparison",
            "primary_level_change_usd",
            "primary_dh_growth",
            "primary_log_growth",
            "level_change_difference_from_primary_usd",
            "dh_growth_difference_from_primary",
            "log_growth_difference_from_primary",
        ]
    }
    expected_boolean: dict[str, list[Any]] = {
        field: []
        for field in [
            "complete_window_pair",
            "pre_zero_flag",
            "comparison_zero_flag",
            "dh_growth_defined",
            "log_growth_defined",
            "same_level_change_direction_as_primary",
            "same_dh_growth_direction_as_primary",
        ]
    }
    for _, row in time_output.iterrows():
        key = (row["connector_iso3"], row["analysis_sector"])
        annual_group = annual_index[key]
        flow = flow_map[row["flow_id"]]
        pre = window_statistics(
            annual_group,
            flow,
            int(row["base_start_year"]),
            int(row["base_end_year"]),
        )
        comparison = window_statistics(
            annual_group,
            flow,
            int(row["comparison_start_year"]),
            int(row["comparison_end_year"]),
        )
        primary_spec = settings["specifications"][reference_spec]
        primary_comparison = window_statistics(
            annual_group,
            flow,
            int(primary_spec["start"]),
            int(primary_spec["end"]),
        )
        change = comparison["scale"] - pre["scale"]
        dh = dh_growth(pre["scale"], comparison["scale"])
        log = log_growth(pre["scale"], comparison["scale"])
        primary_change = primary_comparison["scale"] - pre["scale"]
        primary_dh = dh_growth(pre["scale"], primary_comparison["scale"])
        primary_log = log_growth(pre["scale"], primary_comparison["scale"])
        values = {
            "observed_base_year_count": pre["observed_year_count"],
            "observed_comparison_year_count": comparison[
                "observed_year_count"
            ],
            "pre_trade_scale_usd": pre["scale"],
            "comparison_trade_scale_usd": comparison["scale"],
            "level_change_usd": change,
            "dh_growth": dh,
            "log_growth": log,
            "annual_growth_transition_count": comparison[
                "annual_growth_transition_count"
            ],
            "annual_dh_growth_sd": comparison["annual_dh_growth_sd"],
            "positive_growth_year_share": comparison[
                "positive_growth_year_share"
            ],
            "included_value_share_pre": pre["included_value_share"],
            "included_value_share_comparison": comparison[
                "included_value_share"
            ],
            "source_row_count_annual_mean_pre": pre[
                "source_row_count_annual_mean"
            ],
            "source_row_count_annual_mean_comparison": comparison[
                "source_row_count_annual_mean"
            ],
            "primary_level_change_usd": primary_change,
            "primary_dh_growth": primary_dh,
            "primary_log_growth": primary_log,
            "level_change_difference_from_primary_usd": (
                change - primary_change
            ),
            "dh_growth_difference_from_primary": dh - primary_dh,
            "log_growth_difference_from_primary": log - primary_log,
        }
        for field, value in values.items():
            expected_numeric[field].append(value)
        booleans = {
            "complete_window_pair": bool(
                pre["observed_year_count"]
                == int(row["expected_base_year_count"])
                and comparison["observed_year_count"]
                == int(row["expected_comparison_year_count"])
            ),
            "pre_zero_flag": bool(pre["scale"] == 0),
            "comparison_zero_flag": bool(comparison["scale"] == 0),
            "dh_growth_defined": bool(not pd.isna(dh)),
            "log_growth_defined": bool(not pd.isna(log)),
            "same_level_change_direction_as_primary": nullable_same_sign(
                change, primary_change
            ),
            "same_dh_growth_direction_as_primary": nullable_same_sign(
                dh, primary_dh
            ),
        }
        for field, value in booleans.items():
            expected_boolean[field].append(value)

    numeric_checks: dict[str, Any] = {}
    for field, values in expected_numeric.items():
        gap, missing_mismatch = maximum_absolute_gap(
            time_output[field], pd.Series(values)
        )
        numeric_checks[field] = {
            "maximum_absolute_gap": gap,
            "missing_mismatch_count": missing_mismatch,
        }
    boolean_mismatches = {
        field: mismatch_count(time_output[field], pd.Series(values))
        for field, values in expected_boolean.items()
    }

    common_index = common.set_index(COMMON_KEY)
    primary_crosschecks: dict[str, Any] = {}
    primary_rows = time_output.loc[
        time_output["window_spec_id"].eq(reference_spec)
    ]
    for flow_id, flow in flow_map.items():
        selected = primary_rows.loc[primary_rows["flow_id"].eq(flow_id)].copy()
        source = common_index.loc[
            list(
                zip(
                    selected["connector_iso3"],
                    selected["analysis_sector"],
                    strict=True,
                )
            )
        ].reset_index()
        checks: dict[str, Any] = {}
        for output_field, config_field in [
            ("pre_trade_scale_usd", "common_pre_field"),
            ("comparison_trade_scale_usd", "common_post_field"),
        ]:
            gap, missing = maximum_absolute_gap(
                selected[output_field].reset_index(drop=True),
                source[flow[config_field]].reset_index(drop=True),
            )
            checks[output_field] = {
                "maximum_absolute_gap": gap,
                "missing_mismatch_count": missing,
            }
        if "common_change_field" in flow:
            for output_field, config_field in [
                ("level_change_usd", "common_change_field"),
                ("dh_growth", "common_dh_field"),
                ("log_growth", "common_log_field"),
            ]:
                gap, missing = maximum_absolute_gap(
                    selected[output_field].reset_index(drop=True),
                    source[flow[config_field]].reset_index(drop=True),
                )
                checks[output_field] = {
                    "maximum_absolute_gap": gap,
                    "missing_mismatch_count": missing,
                }
        else:
            expected_decline = (
                selected["pre_trade_scale_usd"]
                - selected["comparison_trade_scale_usd"]
            ).clip(lower=0)
            gap, missing = maximum_absolute_gap(
                expected_decline.reset_index(drop=True),
                source[flow["common_decline_field"]].reset_index(drop=True),
            )
            checks["china_us_decline_usd"] = {
                "maximum_absolute_gap": gap,
                "missing_mismatch_count": missing,
            }
        primary_crosschecks[flow_id] = checks

    repeated = time_output.loc[
        time_output["flow_id"].eq("china_to_usa")
    ]
    repeated_mismatch_groups = 0
    for _, group in repeated.groupby(
        ["analysis_sector", "window_spec_id"], observed=True
    ):
        for field in [
            "pre_trade_scale_usd",
            "comparison_trade_scale_usd",
            "level_change_usd",
            "dh_growth",
            "log_growth",
        ]:
            if float(group[field].max() - group[field].min()) > 1e-12:
                repeated_mismatch_groups += 1
                break
    return {
        "numeric_formula_checks": numeric_checks,
        "boolean_formula_mismatch_counts": boolean_mismatches,
        "primary_common_panel_crosschecks": primary_crosschecks,
        "china_to_usa_repeated_mismatch_group_count": (
            repeated_mismatch_groups
        ),
    }


def source_formula_validation(
    source_output: pd.DataFrame,
    common: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, Any]:
    settings = config["source_bloc_sensitivity"]
    common_index = common.set_index(COMMON_KEY)
    preserved_numeric_fields = [
        "input_value_usd_pre",
        "input_value_usd_post",
        "input_gain_usd",
        "input_dh_growth_raw",
        "input_log_growth_raw",
        "input_to_export_ratio_pre",
        "input_to_export_ratio_post",
        "input_to_export_ratio_change",
        "active_product_count",
        "positive_weight_product_count",
        "product_change_correlation",
        "weighted_product_change_correlation",
        "both_legs_positive_product_count",
        "both_legs_positive_product_share",
        "both_legs_positive_active_share",
        "both_legs_positive_export_gain_share",
        "triple_condition_product_count",
        "triple_condition_product_share",
        "triple_condition_active_share",
        "triple_condition_export_gain_share",
    ]
    preserved_boolean_fields = [
        "input_small_base_flag",
        "input_dh_primary_eligible",
        "input_abnormal_growth_flag",
        "input_to_export_ratio_pre_defined",
        "input_to_export_ratio_post_defined",
        "correlation_low_n_flag",
        "weighted_correlation_low_n_flag",
    ]
    numeric_gaps: dict[str, dict[str, Any]] = {}
    boolean_mismatches: dict[str, int] = {}
    for spec_id, spec in settings["specifications"].items():
        selected = source_output.loc[
            source_output["source_bloc_id"].eq(spec_id)
        ].reset_index(drop=True)
        source = common_index.loc[
            list(
                zip(
                    selected["connector_iso3"],
                    selected["analysis_sector"],
                    strict=True,
                )
            )
        ].reset_index()
        expected = pd.DataFrame(
            [
                source_field_values(row, spec["field_prefix"])
                for _, row in source.iterrows()
            ]
        )
        for field in preserved_numeric_fields:
            gap, missing = maximum_absolute_gap(
                selected[field], expected[field]
            )
            numeric_gaps[f"{spec_id}:{field}"] = {
                "maximum_absolute_gap": gap,
                "missing_mismatch_count": missing,
            }
        for field in preserved_boolean_fields:
            boolean_mismatches[f"{spec_id}:{field}"] = mismatch_count(
                selected[field], expected[field]
            )

    pivot = {
        spec_id: source_output.loc[
            source_output["source_bloc_id"].eq(spec_id)
        ]
        .sort_values(COMMON_KEY)
        .reset_index(drop=True)
        for spec_id in settings["specifications"]
    }
    china = pivot[settings["reference_spec"]]
    east_asia = pivot["extended_east_asia"]
    difference_fields = {
        "input_value_usd_pre_difference_from_china_only": (
            "input_value_usd_pre"
        ),
        "input_value_usd_post_difference_from_china_only": (
            "input_value_usd_post"
        ),
        "input_gain_usd_difference_from_china_only": "input_gain_usd",
        "input_dh_growth_difference_from_china_only": "input_dh_growth_raw",
        "input_log_growth_difference_from_china_only": "input_log_growth_raw",
        "input_to_export_ratio_pre_difference_from_china_only": (
            "input_to_export_ratio_pre"
        ),
        "input_to_export_ratio_post_difference_from_china_only": (
            "input_to_export_ratio_post"
        ),
        "input_to_export_ratio_change_difference_from_china_only": (
            "input_to_export_ratio_change"
        ),
        "product_correlation_difference_from_china_only": (
            "product_change_correlation"
        ),
        "weighted_product_correlation_difference_from_china_only": (
            "weighted_product_change_correlation"
        ),
        "both_legs_positive_product_share_difference_from_china_only": (
            "both_legs_positive_product_share"
        ),
        "triple_condition_product_share_difference_from_china_only": (
            "triple_condition_product_share"
        ),
    }
    difference_checks: dict[str, Any] = {}
    for output_field, level_field in difference_fields.items():
        expected_east = east_asia[level_field] - china[level_field]
        gap_east, missing_east = maximum_absolute_gap(
            east_asia[output_field], expected_east
        )
        gap_china, missing_china = maximum_absolute_gap(
            china[output_field], pd.Series(0.0, index=china.index)
        )
        difference_checks[output_field] = {
            "east_asia_maximum_absolute_gap": gap_east,
            "east_asia_missing_mismatch_count": missing_east,
            "china_reference_maximum_absolute_gap": gap_china,
            "china_reference_missing_mismatch_count": missing_china,
        }

    direction_fields = {
        "same_input_gain_direction_as_china_only": "input_gain_usd",
        "same_input_dh_growth_direction_as_china_only": (
            "input_dh_growth_raw"
        ),
        "same_input_to_export_ratio_change_direction_as_china_only": (
            "input_to_export_ratio_change"
        ),
        "same_product_correlation_direction_as_china_only": (
            "product_change_correlation"
        ),
    }
    direction_mismatches: dict[str, int] = {}
    for output_field, level_field in direction_fields.items():
        expected = pd.Series(
            [
                nullable_same_sign(east, reference)
                for east, reference in zip(
                    east_asia[level_field], china[level_field], strict=True
                )
            ]
        )
        direction_mismatches[output_field] = mismatch_count(
            east_asia[output_field], expected
        )

    level_nested_violations = int(
        (
            east_asia["input_value_usd_pre"]
            < china["input_value_usd_pre"] - 0.01
        ).sum()
        + (
            east_asia["input_value_usd_post"]
            < china["input_value_usd_post"] - 0.01
        ).sum()
    )
    mechanical_formula_checks: dict[str, Any] = {}
    for frame_id, frame in pivot.items():
        expected_gain = (
            frame["input_value_usd_post"] - frame["input_value_usd_pre"]
        )
        expected_dh = pd.Series(
            [
                dh_growth(pre, post)
                for pre, post in zip(
                    frame["input_value_usd_pre"],
                    frame["input_value_usd_post"],
                    strict=True,
                )
            ]
        )
        expected_log = pd.Series(
            [
                log_growth(pre, post)
                for pre, post in zip(
                    frame["input_value_usd_pre"],
                    frame["input_value_usd_post"],
                    strict=True,
                )
            ]
        )
        mechanical_formula_checks[frame_id] = {}
        for field, expected in [
            ("input_gain_usd", expected_gain),
            ("input_dh_growth_raw", expected_dh),
            ("input_log_growth_raw", expected_log),
        ]:
            gap, missing = maximum_absolute_gap(frame[field], expected)
            mechanical_formula_checks[frame_id][field] = {
                "maximum_absolute_gap": gap,
                "missing_mismatch_count": missing,
            }
    return {
        "preserved_numeric_checks": numeric_gaps,
        "preserved_boolean_mismatch_counts": boolean_mismatches,
        "difference_formula_checks": difference_checks,
        "direction_flag_mismatch_counts": direction_mismatches,
        "nested_level_violation_count": level_nested_violations,
        "mechanical_growth_formula_checks": mechanical_formula_checks,
    }


def exposure_formula_validation(
    exposure_output: pd.DataFrame,
) -> dict[str, Any]:
    supports = exposure_output["supports_pre_post_comparison"].astype(bool)
    expected_value = exposure_output["exposure_measure_post"].where(
        supports,
        safe_series_divide(
            exposure_output["numerator_usd_post_or_gain"],
            exposure_output["denominator_usd_post_or_gain"],
        ),
    )
    expected_pre = safe_series_divide(
        exposure_output["numerator_usd_pre"],
        exposure_output["denominator_usd_pre"],
    )
    expected_post = safe_series_divide(
        exposure_output["numerator_usd_post_or_gain"],
        exposure_output["denominator_usd_post_or_gain"],
    )
    checks: dict[str, Any] = {}
    for field, expected, mask in [
        ("exposure_measure_pre", expected_pre, supports),
        ("exposure_measure_post", expected_post, supports),
        (
            "exposure_measure_change",
            expected_post - expected_pre,
            supports,
        ),
        (
            "exposure_measure_value",
            expected_value,
            pd.Series(True, index=exposure_output.index),
        ),
    ]:
        gap, missing = maximum_absolute_gap(
            exposure_output.loc[mask, field].reset_index(drop=True),
            expected.loc[mask].reset_index(drop=True),
        )
        checks[field] = {
            "maximum_absolute_gap": gap,
            "missing_mismatch_count": missing,
        }
    no_pre_post = exposure_output.loc[~supports]
    pre_post_nonmissing_not_applicable = int(
        no_pre_post[
            [
                "exposure_measure_pre",
                "exposure_measure_post",
                "exposure_measure_change",
                "numerator_usd_pre",
                "denominator_usd_pre",
                "value_coverage_share_pre",
            ]
        ]
        .notna()
        .sum()
        .sum()
    )
    value_in_unit_interval_violations = int(
        (
            exposure_output["exposure_measure_value"].lt(-1e-12)
            | exposure_output["exposure_measure_value"].gt(1 + 1e-12)
        ).sum()
    )
    coverage_in_unit_interval_violations = int(
        (
            exposure_output[
                [
                    "value_coverage_share_pre",
                    "value_coverage_share_post_or_gain",
                ]
            ].lt(-1e-12)
            | exposure_output[
                [
                    "value_coverage_share_pre",
                    "value_coverage_share_post_or_gain",
                ]
            ].gt(1 + 1e-12)
        )
        .sum()
        .sum()
    )
    return {
        "ratio_formula_checks": checks,
        "pre_post_nonmissing_when_not_applicable_count": (
            pre_post_nonmissing_not_applicable
        ),
        "measure_unit_interval_violation_count": (
            value_in_unit_interval_violations
        ),
        "coverage_unit_interval_violation_count": (
            coverage_in_unit_interval_violations
        ),
    }


def safe_series_divide(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    output = pd.Series(np.nan, index=numerator.index, dtype="float64")
    usable = numerator.notna() & denominator.notna() & denominator.ne(0)
    output.loc[usable] = (
        numerator.loc[usable].astype("float64")
        / denominator.loc[usable].astype("float64")
    )
    return output


def all_numeric_checks_within(
    checks: dict[str, Any],
    tolerance: float,
    *,
    usd_tolerance: float | None = None,
) -> bool:
    for name, value in checks.items():
        if isinstance(value, dict):
            gap_keys = [
                key for key in value if key.endswith("maximum_absolute_gap")
            ]
            for gap_key in gap_keys:
                prefix = gap_key[: -len("maximum_absolute_gap")]
                missing_key = f"{prefix}missing_mismatch_count"
                allowed = (
                    usd_tolerance
                    if usd_tolerance is not None
                    and any(
                        marker in name
                        for marker in ["usd", "scale", "level", "value"]
                    )
                    else tolerance
                )
                if float(value[gap_key]) > float(allowed):
                    return False
                if missing_key in value and int(value[missing_key]) != 0:
                    return False
            if not all_numeric_checks_within(
                {
                    key: nested
                    for key, nested in value.items()
                    if isinstance(nested, dict)
                },
                tolerance,
                usd_tolerance=usd_tolerance,
            ):
                return False
    return True


def output_structure(
    frame: pd.DataFrame,
    specification: dict[str, Any],
) -> dict[str, Any]:
    key = list(specification["natural_key"])
    numeric = frame.select_dtypes(include=[np.number])
    infinite_count = (
        int(np.isinf(numeric.to_numpy(dtype="float64", na_value=np.nan)).sum())
        if not numeric.empty
        else 0
    )
    return {
        "observed_rows": len(frame),
        "expected_rows": int(specification["expected_rows"]),
        "row_count_match": len(frame) == int(specification["expected_rows"]),
        "observed_columns": len(frame.columns),
        "expected_columns": int(specification["expected_columns"]),
        "column_count_match": len(frame.columns)
        == int(specification["expected_columns"]),
        "natural_key": key,
        "duplicate_key_count": int(frame.duplicated(key).sum()),
        "connector_count": int(frame["connector_iso3"].nunique()),
        "sector_count": int(frame["analysis_sector"].nunique()),
        "infinite_numeric_count": infinite_count,
    }


def validate(
    project_root: Path,
    common: pd.DataFrame,
    common_schema: pa.Schema,
    annual: pd.DataFrame,
    annual_schema: pa.Schema,
    time_windows: dict[str, Any],
    country_groups: dict[str, Any],
    time_output: pd.DataFrame,
    source_output: pd.DataFrame,
    exposure_output: pd.DataFrame,
    config: dict[str, Any],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    tolerance = float(config["validation"]["numeric_tolerance"])
    usd_tolerance = float(config["validation"]["usd_tolerance"])
    common_contract = input_contract(
        project_root,
        common,
        common_schema,
        config["inputs"]["common_panel"],
        "m3_common_panel_version",
    )
    annual_contract = input_contract(
        project_root,
        annual,
        annual_schema,
        config["inputs"]["annual_sector_panel"],
        "m3_sector_aggregation_version",
    )
    ancillary_contracts = {}
    for input_id in ["time_windows", "country_groups"]:
        specification = config["inputs"][input_id]
        observed_hash = sha256(project_root / specification["path"])
        ancillary_contracts[input_id] = {
            "path": specification["path"],
            "observed_sha256": observed_hash,
            "expected_sha256": specification["sha256"],
            "hash_match": observed_hash == specification["sha256"],
        }

    base = config["time_window_sensitivity"]["base_period"]
    specifications = config["time_window_sensitivity"]["specifications"]
    time_rule_checks = {
        "base_matches_time_windows_pre": (
            int(base["start"]) == int(time_windows["pre_period"]["start"])
            and int(base["end"]) == int(time_windows["pre_period"]["end"])
        ),
        "primary_matches_time_windows_post": (
            int(specifications["primary_post"]["start"])
            == int(time_windows["post_period"]["start"])
            and int(specifications["primary_post"]["end"])
            == int(time_windows["post_period"]["end"])
        ),
        "shock_matches_time_windows_shock": (
            int(specifications["shock_only"]["start"])
            == int(time_windows["shock_period"]["start"])
            and int(specifications["shock_only"]["end"])
            == int(time_windows["shock_period"]["end"])
        ),
        "exclude_2024_ends_in_2023": int(
            specifications["exclude_2024"]["end"]
        )
        == 2023,
    }
    source_rule_checks: dict[str, bool] = {}
    for spec_id, spec in config["source_bloc_sensitivity"][
        "specifications"
    ].items():
        observed_members = list(
            nested_value(country_groups, spec["country_group_path"])
        )
        source_rule_checks[f"{spec_id}_members_match"] = (
            observed_members == list(spec["expected_members"])
        )

    expected_years = list(config["sample"]["expected_years"])
    annual_grid_counts = annual.groupby(COMMON_KEY, observed=True)["year"].agg(
        ["count", "nunique", "min", "max"]
    )
    annual_grid = {
        "connector_sector_cell_count": len(annual_grid_counts),
        "all_cells_have_expected_row_count": bool(
            annual_grid_counts["count"].eq(len(expected_years)).all()
        ),
        "all_cells_have_expected_unique_year_count": bool(
            annual_grid_counts["nunique"].eq(len(expected_years)).all()
        ),
        "all_cells_cover_expected_bounds": bool(
            annual_grid_counts["min"].eq(min(expected_years)).all()
            and annual_grid_counts["max"].eq(max(expected_years)).all()
        ),
        "exact_year_set_mismatch_count": int(
            sum(
                sorted(group["year"].unique().tolist()) != expected_years
                for _, group in annual.groupby(
                    COMMON_KEY, sort=False, observed=True
                )
            )
        ),
        "common_key_set_match": set(
            map(tuple, common[COMMON_KEY].to_numpy())
        )
        == set(map(tuple, annual[COMMON_KEY].drop_duplicates().to_numpy())),
    }
    annual_first = (
        annual.sort_values(ANNUAL_KEY)
        .groupby(COMMON_KEY, observed=True)
        .first()
        .reset_index()
    )
    metadata_merge = common.merge(
        annual_first,
        on=COMMON_KEY,
        how="outer",
        validate="one_to_one",
        suffixes=("_common", "_annual"),
        indicator=True,
    )
    annual_common_metadata_mismatches = {
        field: mismatch_count(
            metadata_merge[f"{field}_common"],
            metadata_merge[f"{field}_annual"],
        )
        for field in [
            "connector_group",
            "connector_baci_code",
            "connector_is_proxy",
            "trade_value_unit",
        ]
    }
    annual_common_metadata_mismatches["join_not_both_count"] = int(
        metadata_merge["_merge"].ne("both").sum()
    )

    output_structures = {
        output_id: output_structure(frame, config["outputs"][output_id])
        for output_id, frame in [
            ("time_window", time_output),
            ("source_bloc", source_output),
            ("exposure_definition", exposure_output),
        ]
    }
    alias_checks = {
        output_id: alias_validation(
            frame, config["outputs"][output_id]["stata_aliases"]
        )
        for output_id, frame in [
            ("time_window", time_output),
            ("source_bloc", source_output),
            ("exposure_definition", exposure_output),
        ]
    }

    time_formulas = time_formula_validation(
        time_output, common, annual, config
    )
    source_formulas = source_formula_validation(
        source_output, common, config
    )
    exposure_formulas = exposure_formula_validation(exposure_output)

    negative_change_counts: dict[str, dict[str, int]] = {}
    for spec_id in specifications:
        negative_change_counts[spec_id] = {}
        for flow_id in config["time_window_sensitivity"]["flows"]:
            selected = time_output.loc[
                time_output["window_spec_id"].eq(spec_id)
                & time_output["flow_id"].eq(flow_id),
                "level_change_usd",
            ]
            negative_change_counts[spec_id][flow_id] = int(
                selected.lt(0).sum()
            )
    time_state_counts = {
        "negative_change_counts": negative_change_counts,
        "endpoint_zero_count": int(
            time_output["pre_zero_flag"].sum()
            + time_output["comparison_zero_flag"].sum()
        ),
        "log_growth_defined_count": int(
            time_output["log_growth_defined"].sum()
        ),
        "annual_growth_sd_defined_count": int(
            time_output["annual_dh_growth_sd"].notna().sum()
        ),
        "positive_growth_year_share_defined_count": int(
            time_output["positive_growth_year_share"].notna().sum()
        ),
        "complete_window_pair_count": int(
            time_output["complete_window_pair"].sum()
        ),
        "dh_out_of_bounds_count": int(
            (
                time_output["dh_growth"].lt(-2 - tolerance)
                | time_output["dh_growth"].gt(2 + tolerance)
            ).sum()
        ),
    }

    source_negative_counts = {
        spec_id: int(
            source_output.loc[
                source_output["source_bloc_id"].eq(spec_id),
                "input_gain_usd",
            ].lt(0).sum()
        )
        for spec_id in config["source_bloc_sensitivity"][
            "specifications"
        ]
    }
    east_asia_rows = source_output.loc[
        source_output["source_bloc_id"].eq("extended_east_asia")
    ]
    direction_count_field_map = {
        "input_gain": "same_input_gain_direction_as_china_only",
        "input_dh_growth": (
            "same_input_dh_growth_direction_as_china_only"
        ),
        "input_to_export_ratio_change": (
            "same_input_to_export_ratio_change_direction_as_china_only"
        ),
        "product_correlation": (
            "same_product_correlation_direction_as_china_only"
        ),
    }
    source_state_counts = {
        "negative_gain_counts": source_negative_counts,
        "self_trade_excluded_rows": int(
            source_output["connector_self_trade_excluded"].sum()
        ),
        "direction_agreement_counts": {
            label: int(east_asia_rows[field].sum())
            for label, field in direction_count_field_map.items()
        },
        "pre_ratio_defined_count": int(
            source_output["input_to_export_ratio_pre_defined"].sum()
        ),
        "post_ratio_defined_count": int(
            source_output["input_to_export_ratio_post_defined"].sum()
        ),
    }

    exposure_negative_counts = {
        definition_id: int(
            exposure_output.loc[
                exposure_output["exposure_definition_id"].eq(definition_id),
                "exposure_measure_change",
            ].lt(0).sum()
        )
        for definition_id in [
            "tariff_overlap",
            "exposure_weighted_rate",
        ]
    }
    missing_product_totals = (
        common.groupby("connector_iso3", observed=True)[
            "post_exposure_missing_product_count"
        ]
        .sum()
        .astype(int)
    )
    exposure_state_counts = {
        "measure_defined_count": int(
            exposure_output["measure_defined"].sum()
        ),
        "pre_post_supported_rows": int(
            exposure_output["supports_pre_post_comparison"].sum()
        ),
        "pre_post_missing_by_design_rows": int(
            exposure_output["pre_post_missing_by_design"].sum()
        ),
        "negative_change_counts": exposure_negative_counts,
        "missing_product_totals_by_connector": {
            key: int(value)
            for key, value in missing_product_totals.items()
        },
        "connectors_with_expected_missing_product_total": int(
            missing_product_totals.eq(
                int(
                    config["validation"][
                        "expected_exposure_missing_product_count_per_connector_total"
                    ]
                )
            ).sum()
        ),
    }

    twn_rows = {
        "time_window": int(time_output["connector_iso3"].eq("TWN").sum()),
        "source_bloc": int(source_output["connector_iso3"].eq("TWN").sum()),
        "exposure_definition": int(
            exposure_output["connector_iso3"].eq("TWN").sum()
        ),
    }
    twn_proxy_mismatch_counts = {
        "time_window": int(
            (
                ~time_output.loc[
                    time_output["connector_iso3"].eq("TWN"),
                    "connector_is_proxy",
                ].astype(bool)
            ).sum()
        ),
        "source_bloc": int(
            (
                ~source_output.loc[
                    source_output["connector_iso3"].eq("TWN"),
                    "connector_is_proxy",
                ].astype(bool)
            ).sum()
        ),
        "exposure_definition": int(
            (
                ~exposure_output.loc[
                    exposure_output["connector_iso3"].eq("TWN"),
                    "connector_is_proxy",
                ].astype(bool)
            ).sum()
        ),
    }
    metadata_flags = {
        output_id: {
            "all_sensitivity_constructed": bool(
                frame["sensitivity_variables_constructed"].all()
            ),
            "any_ranking_constructed": bool(
                frame["ranking_variables_constructed"].any()
            ),
            "schema_versions": sorted(
                str(value) for value in frame["schema_version"].unique()
            ),
            "construction_versions": sorted(
                str(value)
                for value in frame["m3_sensitivity_version"].unique()
            ),
        }
        for output_id, frame in [
            ("time_window", time_output),
            ("source_bloc", source_output),
            ("exposure_definition", exposure_output),
        ]
    }

    failures: list[str] = []
    for name, contract in {
        "common_panel": common_contract,
        "annual_sector_panel": annual_contract,
    }.items():
        for field in [
            "hash_match",
            "row_count_match",
            "column_count_match",
            "schema_signature_match",
            "version_match",
            "schema_version_match",
        ]:
            if not contract[field]:
                failures.append(f"{name} input contract failed: {field}")
        if contract["duplicate_key_count"] != 0:
            failures.append(f"{name} input key contains duplicates")
    if not all(
        contract["hash_match"] for contract in ancillary_contracts.values()
    ):
        failures.append("Ancillary config hash contract failed")
    if not all(time_rule_checks.values()):
        failures.append("Frozen time-window rules do not match time_windows.yaml")
    if not all(source_rule_checks.values()):
        failures.append("Frozen source-bloc members do not match country_groups.yaml")
    if not all(
        [
            annual_grid["all_cells_have_expected_row_count"],
            annual_grid["all_cells_have_expected_unique_year_count"],
            annual_grid["all_cells_cover_expected_bounds"],
            annual_grid["exact_year_set_mismatch_count"] == 0,
            annual_grid["common_key_set_match"],
        ]
    ):
        failures.append("Annual connector-sector grid is incomplete")
    if sum(annual_common_metadata_mismatches.values()) != 0:
        failures.append("Annual/common-panel metadata mismatch")
    for output_id, structure in output_structures.items():
        if not structure["row_count_match"]:
            failures.append(f"{output_id} row count failed")
        if not structure["column_count_match"]:
            failures.append(f"{output_id} column count failed")
        if structure["duplicate_key_count"] != 0:
            failures.append(f"{output_id} key contains duplicates")
        if structure["connector_count"] != int(
            config["sample"]["expected_connector_count"]
        ):
            failures.append(f"{output_id} connector universe failed")
        if structure["sector_count"] != int(
            config["sample"]["expected_sector_count"]
        ):
            failures.append(f"{output_id} sector universe failed")
        if structure["infinite_numeric_count"] != 0:
            failures.append(f"{output_id} contains infinite numeric values")
        if not alias_checks[output_id]["pass"]:
            failures.append(f"{output_id} Stata alias contract failed")
    if not all_numeric_checks_within(
        time_formulas["numeric_formula_checks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Time-window independent numeric formula check failed")
    if any(
        time_formulas["boolean_formula_mismatch_counts"].values()
    ):
        failures.append("Time-window boolean formula check failed")
    if not all_numeric_checks_within(
        time_formulas["primary_common_panel_crosschecks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Primary time window does not match M3.5")
    if time_formulas["china_to_usa_repeated_mismatch_group_count"] != 0:
        failures.append("China-to-USA repeated benchmark mismatch")
    expected_negative = config["validation"][
        "expected_time_negative_change_counts"
    ]
    if negative_change_counts != expected_negative:
        failures.append("Time-window negative-change counts changed")
    if time_state_counts["endpoint_zero_count"] != int(
        config["validation"]["expected_time_endpoint_zero_count"]
    ):
        failures.append("Unexpected time-window zero endpoint count")
    if time_state_counts["log_growth_defined_count"] != int(
        config["validation"]["expected_time_log_growth_defined_count"]
    ):
        failures.append("Unexpected log-growth defined count")
    if time_state_counts["annual_growth_sd_defined_count"] != int(
        config["validation"]["expected_annual_growth_sd_defined_count"]
    ):
        failures.append("Unexpected annual-growth-SD defined count")
    if time_state_counts["positive_growth_year_share_defined_count"] != len(
        time_output
    ):
        failures.append("Positive-growth-year share is unexpectedly missing")
    if time_state_counts["complete_window_pair_count"] != len(time_output):
        failures.append("At least one time-window pair is incomplete")
    if time_state_counts["dh_out_of_bounds_count"] != 0:
        failures.append("DH growth is outside [-2,2]")
    if not all_numeric_checks_within(
        source_formulas["preserved_numeric_checks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Source-bloc preservation check failed")
    if any(source_formulas["preserved_boolean_mismatch_counts"].values()):
        failures.append("Source-bloc boolean preservation check failed")
    if not all_numeric_checks_within(
        source_formulas["difference_formula_checks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Source-bloc difference formula check failed")
    if any(source_formulas["direction_flag_mismatch_counts"].values()):
        failures.append("Source-bloc direction flag check failed")
    if source_formulas["nested_level_violation_count"] != 0:
        failures.append("Nested East Asia levels are below China-only levels")
    if not all_numeric_checks_within(
        source_formulas["mechanical_growth_formula_checks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Source-bloc mechanical growth formula check failed")
    if source_negative_counts != config["validation"][
        "expected_source_negative_gain_counts"
    ]:
        failures.append("Source-bloc negative-gain counts changed")
    if source_state_counts["self_trade_excluded_rows"] != int(
        config["validation"]["expected_source_self_trade_excluded_rows"]
    ):
        failures.append("Source-bloc self-trade exclusion count changed")
    if source_state_counts["direction_agreement_counts"] != config[
        "validation"
    ]["expected_source_direction_agreement_counts"]:
        failures.append("Source-bloc direction-agreement counts changed")
    if source_state_counts["pre_ratio_defined_count"] != len(source_output):
        failures.append("Source-bloc pre ratio unexpectedly missing")
    if source_state_counts["post_ratio_defined_count"] != len(source_output):
        failures.append("Source-bloc post ratio unexpectedly missing")
    if not all_numeric_checks_within(
        exposure_formulas["ratio_formula_checks"],
        tolerance,
        usd_tolerance=usd_tolerance,
    ):
        failures.append("Exposure ratio formula check failed")
    if (
        exposure_formulas[
            "pre_post_nonmissing_when_not_applicable_count"
        ]
        != 0
    ):
        failures.append("Exposure pre/post N/A states were not preserved")
    if exposure_formulas["measure_unit_interval_violation_count"] != 0:
        failures.append("Exposure measure is outside [0,1]")
    if exposure_formulas["coverage_unit_interval_violation_count"] != 0:
        failures.append("Exposure coverage is outside [0,1]")
    if exposure_state_counts["measure_defined_count"] != int(
        config["validation"]["expected_exposure_defined_count"]
    ):
        failures.append("Exposure defined count changed")
    if exposure_state_counts["pre_post_supported_rows"] != int(
        config["validation"]["expected_exposure_pre_post_supported_rows"]
    ):
        failures.append("Exposure pre/post-supported count changed")
    if exposure_negative_counts != config["validation"][
        "expected_exposure_negative_change_counts"
    ]:
        failures.append("Exposure negative-change counts changed")
    if exposure_state_counts[
        "connectors_with_expected_missing_product_total"
    ] != int(config["sample"]["expected_connector_count"]):
        failures.append("Exposure missing-product totals changed")
    if twn_rows != config["validation"]["expected_twn_rows"]:
        failures.append("TWN row counts changed")
    if sum(twn_proxy_mismatch_counts.values()) != 0:
        failures.append("TWN proxy flag was not preserved")
    for output_id, flags in metadata_flags.items():
        if not flags["all_sensitivity_constructed"]:
            failures.append(f"{output_id} sensitivity flag failed")
        if flags["any_ranking_constructed"]:
            failures.append(f"{output_id} incorrectly constructs ranking")
        if flags["construction_versions"] != [config["version"]]:
            failures.append(f"{output_id} construction version failed")
        if flags["schema_versions"] != [
            config["outputs"][output_id]["schema_version"]
        ]:
            failures.append(f"{output_id} schema version failed")
    if not determinism["all_sha256_match"]:
        failures.append("Deterministic Parquet SHA256 check failed")
    if not determinism["temporary_output_cleaned"]:
        failures.append("Determinism temporary directory was not cleaned")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "input_contracts": {
            "common_panel": common_contract,
            "annual_sector_panel": annual_contract,
            **ancillary_contracts,
        },
        "time_rule_checks": time_rule_checks,
        "source_rule_checks": source_rule_checks,
        "annual_grid_checks": annual_grid,
        "annual_common_metadata_mismatch_counts": (
            annual_common_metadata_mismatches
        ),
        "output_structures": output_structures,
        "time_formula_checks": time_formulas,
        "time_state_counts": time_state_counts,
        "source_formula_checks": source_formulas,
        "source_state_counts": source_state_counts,
        "exposure_formula_checks": exposure_formulas,
        "exposure_state_counts": exposure_state_counts,
        "twn_rows": twn_rows,
        "twn_proxy_mismatch_counts": twn_proxy_mismatch_counts,
        "stata_alias_validation": alias_checks,
        "metadata_checks": metadata_flags,
        "determinism_check": determinism,
    }


def build_all_outputs(
    common: pd.DataFrame,
    annual: pd.DataFrame,
    country_groups: dict[str, Any],
    config: dict[str, Any],
    config_hash: str,
) -> dict[str, pd.DataFrame]:
    return {
        "time_window": build_time_window_output(
            common, annual, config, config_hash
        ),
        "source_bloc": build_source_bloc_output(
            common, country_groups, config, config_hash
        ),
        "exposure_definition": build_exposure_definition_output(
            common, config, config_hash
        ),
    }


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    candidate_paths: dict[str, Path],
) -> dict[str, Any]:
    temp_directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if temp_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse pre-existing determinism directory: "
            f"{temp_directory}"
        )
    temp_directory.mkdir(parents=True)
    comparisons: dict[str, Any] = {}
    try:
        common, _, annual, _, _, country_groups = read_inputs(
            project_root, config
        )
        rebuilt = build_all_outputs(
            common, annual, country_groups, config, config_hash
        )
        for output_id, frame in rebuilt.items():
            second_path = temp_directory / (
                f"{candidate_paths[output_id].stem}_second.parquet"
            )
            write_parquet(frame, second_path)
            candidate_hash = sha256(candidate_paths[output_id])
            second_hash = sha256(second_path)
            comparisons[output_id] = {
                "candidate_sha256": candidate_hash,
                "second_build_sha256": second_hash,
                "sha256_match": candidate_hash == second_hash,
            }
    finally:
        remove_owned_temp_directory(temp_directory)
    return {
        "config_sha256": config_hash,
        "outputs": comparisons,
        "all_sha256_match": all(
            value["sha256_match"] for value in comparisons.values()
        ),
        "temporary_output_cleaned": not temp_directory.exists(),
    }


def markdown_report(validation: dict[str, Any]) -> str:
    outputs = validation["outputs"]
    structures = validation["output_structures"]
    aliases = validation["stata_alias_validation"]
    time_states = validation["time_state_counts"]
    source_states = validation["source_state_counts"]
    exposure_states = validation["exposure_state_counts"]
    lines = [
        "# M3.6 Connector-Sector Sensitivity Validation",
        "",
        f"- Origin Date: `{validation['generated_at_utc'][:10]}`",
        (
            "- Verification Status: "
            f"`{'VERIFIED' if validation['validation_status'] == 'PASS' else 'BLOCKED'}`"
        ),
        f"- Version Label: `{validation['construction_version']}`",
        "",
        "## Result",
        "",
        f"- Validation status: **{validation['validation_status']}**",
        (
            "- All three Parquet files reproduced with byte-identical SHA256: "
            f"`{'yes' if validation['determinism_check']['all_sha256_match'] else 'no'}`."
        ),
        "- M3.6 constructs sensitivity inputs only; no connector ranking is constructed.",
        "",
        "## Outputs",
        "",
        "| Output | Rows × columns | Natural key | SHA256 |",
        "|---|---:|---|---|",
    ]
    for output_id, label in [
        ("time_window", "time-window sensitivity"),
        ("source_bloc", "source-bloc sensitivity"),
        ("exposure_definition", "exposure-definition sensitivity"),
    ]:
        structure = structures[output_id]
        output = outputs[output_id]
        key = ", ".join(structure["natural_key"])
        lines.append(
            f"| {label} | {structure['observed_rows']} × "
            f"{structure['observed_columns']} | `{key}` | "
            f"`{output['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Frozen Inputs",
            "",
            (
                "- M3.5 common panel: "
                f"`{validation['input_contracts']['common_panel']['observed_rows']} × "
                f"{validation['input_contracts']['common_panel']['observed_columns']}`; "
                "hash/schema/key/version contract PASS."
            ),
            (
                "- M3.1 annual sector panel: "
                f"`{validation['input_contracts']['annual_sector_panel']['observed_rows']} × "
                f"{validation['input_contracts']['annual_sector_panel']['observed_columns']}`; "
                "hash/schema/key/version contract PASS."
            ),
            "- `time_windows.yaml` and `country_groups.yaml` hashes and frozen members/windows match.",
            "- All 91 connector-sector cells retain the exact 2014-2024 annual grid.",
            "",
            "## Alternative Time Windows",
            "",
            "- `primary_post`: 2014-2017 versus 2020-2024.",
            "- `exclude_2024`: 2014-2017 versus 2020-2023.",
            "- `shock_only`: 2014-2017 versus 2018-2019.",
            "- Levels are annual means. Included-value coverage is recomputed as a ratio of sums.",
            (
                "- Negative level-change counts by specification and flow: "
                f"`{time_states['negative_change_counts']}`."
            ),
            (
                "- Zero endpoints / defined log growth / defined annual DH SD: "
                f"`{time_states['endpoint_zero_count']} / "
                f"{time_states['log_growth_defined_count']} / "
                f"{time_states['annual_growth_sd_defined_count']}`."
            ),
            (
                "- Annual DH SD is intentionally missing for `shock_only`: "
                "a two-year comparison window has only one within-window transition, "
                "which cannot define a sample SD with `ddof=1`."
            ),
            "",
            "## Source-Bloc Definitions",
            "",
            "- `china_only`: CHN.",
            "- `extended_east_asia`: CHN, KOR, JPN, TWN; connector self-trade is excluded when applicable.",
            (
                "- Negative input-gain counts: "
                f"`{source_states['negative_gain_counts']}`; self-trade-excluded rows: "
                f"`{source_states['self_trade_excluded_rows']}`."
            ),
            (
                "- Direction agreement with China-only for input gain / DH growth / "
                "input-export-ratio change / product correlation: "
                f"`{source_states['direction_agreement_counts']}`."
            ),
            (
                "- The definitions are nested. East Asia minus China is the contribution "
                "of the additional East Asian origins after self-exclusion, not an "
                "independent comparison sample."
            ),
            "",
            "## Exposure Definitions",
            "",
            "- `tariff_overlap`: connector export value share on tariffed products.",
            "- `exposure_weighted_rate`: export-value-weighted continuous product exposure among observed products.",
            "- `positive_exposure_gain_share`: positive export gains on products with exposure above zero.",
            "- `top_quartile_exposure_gain_share`: positive export gains on sector p75-or-higher exposure products.",
            (
                "- Defined measures / pre-post-supported rows: "
                f"`{exposure_states['measure_defined_count']} / "
                f"{exposure_states['pre_post_supported_rows']}`."
            ),
            (
                "- Negative pre-post changes for tariff overlap / weighted rate: "
                f"`{exposure_states['negative_change_counts']}`."
            ),
            (
                "- The four definitions have different estimands and units. M3.6 "
                "therefore does not subtract them from each other or convert them "
                "into ranks."
            ),
            "",
            "## Stata and State Preservation",
            "",
            (
                "- Stata aliases complete/unique/max length: time "
                f"`{aliases['time_window']['alias_count']} / "
                f"{aliases['time_window']['maximum_alias_length']}`, source "
                f"`{aliases['source_bloc']['alias_count']} / "
                f"{aliases['source_bloc']['maximum_alias_length']}`, exposure "
                f"`{aliases['exposure_definition']['alias_count']} / "
                f"{aliases['exposure_definition']['maximum_alias_length']}`."
            ),
            (
                "- TWN rows in time/source/exposure outputs: "
                f"`{validation['twn_rows']}`; every row retains the proxy flag."
            ),
            "- Negative changes are retained. No small-base flag, growth value, exposure missing state, or source definition is silently overwritten.",
            "",
            "## Interpretation Boundary",
            "",
            (
                "These files are M6-ready sensitivity inputs, not evidence that a "
                "ranking is stable. Ranking stability can only be assessed after M6 "
                "freezes the score, weights, eligibility rules, and tie handling. "
                "The source-bloc and exposure measures remain descriptive and do not "
                "identify causal rerouting or production relocation."
            ),
        ]
    )
    if validation["failures"]:
        lines.extend(
            ["", "## Failures", ""]
            + [f"- {failure}" for failure in validation["failures"]]
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate M3.6 time-window, source-bloc, and "
            "exposure-definition sensitivity inputs without ranking."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/connector_trade_sector_sensitivity_rules.yaml"
        ),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    output_paths = {
        output_id: (project_root / specification["path"]).resolve()
        for output_id, specification in config["outputs"].items()
    }
    validation_json = (
        project_root / config["validation_outputs"]["json"]
    ).resolve()
    validation_md = (
        project_root / config["validation_outputs"]["markdown"]
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
    candidate_paths = {
        output_id: candidate_directory / path.name
        for output_id, path in output_paths.items()
    }
    try:
        (
            common,
            common_schema,
            annual,
            annual_schema,
            time_windows,
            country_groups,
        ) = read_inputs(project_root, config)
        outputs = build_all_outputs(
            common, annual, country_groups, config, config_hash
        )
        tables = {
            output_id: write_parquet(frame, candidate_paths[output_id])
            for output_id, frame in outputs.items()
        }
        determinism = deterministic_rebuild(
            project_root, config, config_hash, candidate_paths
        )
        validation = validate(
            project_root,
            common,
            common_schema,
            annual,
            annual_schema,
            time_windows,
            country_groups,
            outputs["time_window"],
            outputs["source_bloc"],
            outputs["exposure_definition"],
            config,
            determinism,
        )
        validation.update(
            {
                "validation_version": 1,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path.relative_to(
                    project_root
                ).as_posix(),
                "config_sha256": config_hash,
                "construction_version": config["version"],
                "outputs": {
                    output_id: {
                        "path": output_paths[output_id]
                        .relative_to(project_root)
                        .as_posix(),
                        "sha256": sha256(candidate_paths[output_id]),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in tables[output_id].schema
                        ],
                    }
                    for output_id in outputs
                },
                "candidate_temp_directory": candidate_directory.relative_to(
                    project_root
                ).as_posix(),
            }
        )
        if validation["validation_status"] != "PASS":
            print(json.dumps(validation, ensure_ascii=False, indent=2))
            raise SystemExit(1)

        for output_id, canonical_path in output_paths.items():
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            candidate_paths[output_id].replace(canonical_path)
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
                    "outputs": {
                        output_id: {
                            "rows": len(outputs[output_id]),
                            "columns": len(outputs[output_id].columns),
                            "sha256": validation["outputs"][output_id][
                                "sha256"
                            ],
                        }
                        for output_id in outputs
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
