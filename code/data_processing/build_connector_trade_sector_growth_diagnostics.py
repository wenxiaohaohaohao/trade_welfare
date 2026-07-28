from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


KEY_FIELDS = ["connector_iso3", "analysis_sector", "flow_id"]
SOURCE_ENTITY_FIELDS = [
    "connector_group",
    "connector_baci_code",
    "connector_is_proxy",
    "trade_value_unit",
]
SOURCE_FLOW_SUFFIXES = {
    "value_usd_pre": "value_usd_pre",
    "value_usd_shock": "value_usd_shock",
    "value_usd_post": "value_usd_post",
    "value_usd_change_post_pre": "value_usd_change_post_pre",
    "value_usd_dh_growth_post_pre_raw": "value_usd_dh_growth_post_pre",
    "value_usd_log_growth_post_pre_raw": "value_usd_log_growth_post_pre",
    "pre_zero_flag": "pre_zero_flag",
    "post_zero_flag": "post_zero_flag",
    "dh_growth_defined": "dh_growth_defined",
    "log_growth_defined": "log_growth_defined",
    "years_observed_pre": "years_observed_pre",
    "years_observed_shock": "years_observed_shock",
    "years_observed_post": "years_observed_post",
}
BOOLEAN_FIELDS = [
    "connector_is_proxy",
    "pre_zero_flag",
    "post_zero_flag",
    "dh_growth_defined",
    "log_growth_defined",
    "absolute_small_base_flag",
    "sector_relative_threshold_applicable",
    "sector_relative_small_base_flag",
    "small_base_flag",
    "dh_growth_primary_eligible",
    "log_growth_robustness_eligible",
    "dh_growth_no_threshold_eligible",
    "robust_z_defined",
    "robust_z_outlier_flag",
    "mechanical_extreme_dh_flag",
    "abnormal_growth_flag",
    "abnormal_growth_is_advisory",
    "dh_winsorized_affected_flag",
    "log_winsorized_affected_flag",
    "winsorized_values_for_sensitivity_only",
    "raw_level_change_preserved",
    "flow_repeated_across_connectors",
    "flow_not_additive_across_connectors",
]
INT8_FIELDS = [
    "flow_order",
    "years_observed_pre",
    "years_observed_shock",
    "years_observed_post",
    "sector_relative_nearest_rank",
]
INT16_FIELDS = [
    "sector_relative_reference_cell_count",
    "winsor_reference_cell_count",
]
STRING_FIELDS = [
    "connector_iso3",
    "analysis_sector",
    "flow_id",
    "flow_label",
    "connector_group",
    "connector_baci_code",
    "trade_value_unit",
    "winsorization_scope",
    "m3_window_construction_version",
    "m3_growth_diagnostic_version",
    "rules_config_sha256",
    "schema_version",
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


def nearest_rank_cutoff(values: pd.Series, percentile: float) -> float:
    usable = np.sort(values.dropna().astype("float64").to_numpy())
    if not len(usable):
        return float("nan")
    rank = max(1, math.ceil(percentile * len(usable)))
    return float(usable[rank - 1])


def robust_group_statistics(
    frame: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    output = frame.copy()
    group_fields = config["abnormal_growth"]["robust_z"]["group_fields"]
    value_field = "value_usd_dh_growth_post_pre_raw"
    grouped = output.groupby(group_fields, sort=False, observed=True)[value_field]
    output["robust_z_group_median_dh"] = grouped.transform("median").astype("float64")
    output["robust_z_group_mad_dh"] = grouped.transform(
        lambda values: (
            values.astype("float64") - float(values.astype("float64").median())
        )
        .abs()
        .median()
    ).astype("float64")
    consistency = float(
        config["abnormal_growth"]["robust_z"]["consistency_constant"]
    )
    mad_usable = output["robust_z_group_mad_dh"].gt(0)
    raw_usable = output[value_field].notna()
    output["robust_z_defined"] = (mad_usable & raw_usable).astype(bool)
    output["robust_z_score_dh"] = np.nan
    output.loc[output["robust_z_defined"], "robust_z_score_dh"] = (
        consistency
        * (
            output.loc[output["robust_z_defined"], value_field]
            - output.loc[
                output["robust_z_defined"], "robust_z_group_median_dh"
            ]
        )
        / output.loc[output["robust_z_defined"], "robust_z_group_mad_dh"]
    )
    threshold = float(config["abnormal_growth"]["robust_z"]["absolute_threshold"])
    output["robust_z_absolute_threshold"] = threshold
    output["robust_z_outlier_flag"] = (
        output["robust_z_defined"]
        & output["robust_z_score_dh"].abs().gt(threshold)
    ).astype(bool)
    return output


def build_output(
    comparison: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for flow_id, details in config["trade_flows"].items():
        flow = comparison[
            ["connector_iso3", "analysis_sector", *SOURCE_ENTITY_FIELDS]
        ].copy()
        flow["flow_id"] = flow_id
        flow["flow_order"] = int(details["order"])
        flow["flow_label"] = details["label"]
        for output_field, suffix in SOURCE_FLOW_SUFFIXES.items():
            source_field = f"{flow_id}_{suffix}"
            if source_field not in comparison.columns:
                raise KeyError(f"Missing M3.2 source field: {source_field}")
            flow[output_field] = comparison[source_field]
        flow["flow_repeated_across_connectors"] = bool(
            details["repeated_across_connectors"]
        )
        flow["flow_not_additive_across_connectors"] = bool(
            details["not_additive_across_connectors"]
        )
        records.append(flow)
    output = pd.concat(records, ignore_index=True)

    absolute_threshold = float(
        config["small_base"]["absolute"]["threshold_usd"]
    )
    output["absolute_small_base_threshold_usd"] = absolute_threshold
    output["absolute_small_base_flag"] = (
        output["value_usd_pre"].le(absolute_threshold)
    ).astype(bool)

    relative_percentile = float(
        config["small_base"]["sector_relative"]["percentile"]
    )
    relative_groups = config["small_base"]["sector_relative"]["group_fields"]
    relative_grouped = output.groupby(relative_groups, sort=False, observed=True)[
        "value_usd_pre"
    ]
    output["sector_relative_percentile"] = relative_percentile
    output["sector_relative_reference_cell_count"] = (
        relative_grouped.transform("count").astype("int16")
    )
    output["sector_relative_nearest_rank"] = (
        np.ceil(
            relative_percentile
            * output["sector_relative_reference_cell_count"].astype("float64")
        )
        .clip(lower=1)
        .astype("int8")
    )
    output["sector_relative_pre_value_cutoff_usd"] = relative_grouped.transform(
        lambda values: nearest_rank_cutoff(values, relative_percentile)
    ).astype("float64")
    applicability = {
        flow_id: bool(details["sector_relative_threshold_applicable"])
        for flow_id, details in config["trade_flows"].items()
    }
    output["sector_relative_threshold_applicable"] = (
        output["flow_id"].map(applicability).astype(bool)
    )
    output.loc[
        ~output["sector_relative_threshold_applicable"],
        "sector_relative_pre_value_cutoff_usd",
    ] = np.nan
    output.loc[
        ~output["sector_relative_threshold_applicable"],
        "sector_relative_nearest_rank",
    ] = 0
    output["sector_relative_small_base_flag"] = (
        output["sector_relative_threshold_applicable"]
        & output["value_usd_pre"].le(
            output["sector_relative_pre_value_cutoff_usd"]
        )
    ).astype(bool)
    output["small_base_flag"] = (
        output["pre_zero_flag"]
        | output["absolute_small_base_flag"]
        | output["sector_relative_small_base_flag"]
    ).astype(bool)
    output["dh_growth_primary_eligible"] = (
        output["dh_growth_defined"] & ~output["small_base_flag"]
    ).astype(bool)
    output["log_growth_robustness_eligible"] = (
        output["log_growth_defined"] & ~output["small_base_flag"]
    ).astype(bool)
    output["dh_growth_no_threshold_eligible"] = output[
        "dh_growth_defined"
    ].astype(bool)

    output = robust_group_statistics(output, config)
    extreme_threshold = float(
        config["abnormal_growth"]["mechanical_extreme"][
            "absolute_dh_threshold"
        ]
    )
    output["mechanical_extreme_abs_dh_threshold"] = extreme_threshold
    output["mechanical_extreme_dh_flag"] = (
        output["dh_growth_defined"]
        & output["value_usd_dh_growth_post_pre_raw"]
        .abs()
        .ge(extreme_threshold)
    ).astype(bool)
    output["abnormal_growth_flag"] = (
        output["robust_z_outlier_flag"]
        | output["mechanical_extreme_dh_flag"]
    ).astype(bool)
    output["abnormal_growth_is_advisory"] = bool(
        config["abnormal_growth"]["advisory_only"]
    )

    lower_percentile = float(config["winsorization"]["lower_percentile"])
    upper_percentile = float(config["winsorization"]["upper_percentile"])
    winsor_groups = config["winsorization"]["group_fields"]
    output["winsor_lower_percentile"] = lower_percentile
    output["winsor_upper_percentile"] = upper_percentile
    output["winsor_reference_cell_count"] = (
        output.groupby(winsor_groups, sort=False, observed=True)["flow_id"]
        .transform("size")
        .astype("int16")
    )
    for prefix, raw_field in [
        ("dh", "value_usd_dh_growth_post_pre_raw"),
        ("log", "value_usd_log_growth_post_pre_raw"),
    ]:
        grouped = output.groupby(winsor_groups, sort=False, observed=True)[raw_field]
        lower_field = f"{prefix}_winsor_lower_cutoff"
        upper_field = f"{prefix}_winsor_upper_cutoff"
        winsor_field = f"{prefix}_growth_winsorized"
        affected_field = f"{prefix}_winsorized_affected_flag"
        output[lower_field] = grouped.transform(
            lambda values: values.quantile(
                lower_percentile, interpolation="linear"
            )
        ).astype("float64")
        output[upper_field] = grouped.transform(
            lambda values: values.quantile(
                upper_percentile, interpolation="linear"
            )
        ).astype("float64")
        output[winsor_field] = output[raw_field].clip(
            lower=output[lower_field], upper=output[upper_field]
        )
        output[affected_field] = (
            output[raw_field].notna()
            & output[winsor_field].notna()
            & output[raw_field].ne(output[winsor_field])
        ).astype(bool)

    output["winsorization_scope"] = "flow_id_pooled_across_sectors_and_connectors"
    output["winsorized_values_for_sensitivity_only"] = bool(
        config["winsorization"]["sensitivity_only"]
    )
    output["raw_level_change_preserved"] = True
    window_versions = (
        comparison["m3_window_construction_version"].drop_duplicates().tolist()
    )
    if len(window_versions) != 1:
        raise ValueError(
            "Expected exactly one M3.2 window construction version"
        )
    output["m3_window_construction_version"] = str(window_versions[0])
    output["m3_growth_diagnostic_version"] = config["version"]
    output["rules_config_sha256"] = config_hash
    output["schema_version"] = config["schema_version"]

    connector_order = {
        connector: order
        for order, connector in enumerate(config["analysis"]["connectors"])
    }
    sector_order = {
        sector: order
        for order, sector in enumerate(config["analysis"]["sectors"])
    }
    output["_connector_order"] = output["connector_iso3"].map(connector_order)
    output["_sector_order"] = output["analysis_sector"].map(sector_order)
    output = (
        output.sort_values(
            ["_connector_order", "_sector_order", "flow_order"],
            kind="stable",
        )
        .drop(columns=["_connector_order", "_sector_order"])
        .reset_index(drop=True)
    )

    for field in BOOLEAN_FIELDS:
        output[field] = output[field].astype(bool)
    for field in INT8_FIELDS:
        output[field] = output[field].astype("int8")
    for field in INT16_FIELDS:
        output[field] = output[field].astype("int16")
    for field in STRING_FIELDS:
        output[field] = output[field].astype("string")
    return output


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
        if not alias or not alias[0].isalpha() and alias[0] != "_"
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


def validate(
    comparison: pd.DataFrame,
    input_schema: pa.Schema,
    output: pd.DataFrame,
    config: dict[str, Any],
    input_hash_match: bool,
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    input_config = config["inputs"][
        "connector_trade_sector_window_comparison"
    ]
    input_key = input_config["natural_key"]
    output_key = config["outputs"]["diagnostics"]["natural_key"]
    input_duplicate_keys = int(comparison.duplicated(input_key).sum())
    output_duplicate_keys = int(output.duplicated(output_key).sum())
    input_schema_signature = schema_signature(input_schema)
    observed_connectors = sorted(comparison["connector_iso3"].unique().tolist())
    observed_sectors = sorted(comparison["analysis_sector"].unique().tolist())
    expected_connectors = sorted(config["analysis"]["connectors"])
    expected_sectors = sorted(config["analysis"]["sectors"])

    if not input_hash_match:
        failures.append("frozen M3.2 comparison input SHA256 does not match")
    if len(comparison) != int(input_config["expected_rows"]):
        failures.append("M3.2 comparison input row count does not match")
    if len(comparison.columns) != int(input_config["expected_columns"]):
        failures.append("M3.2 comparison input column count does not match")
    if input_duplicate_keys:
        failures.append("M3.2 comparison input natural key is duplicated")
    if input_schema_signature != input_config["arrow_schema_signature_sha256"]:
        failures.append("M3.2 comparison input Arrow schema does not match")
    if observed_connectors != expected_connectors:
        failures.append("connector universe does not match frozen configuration")
    if observed_sectors != expected_sectors:
        failures.append("sector universe does not match frozen configuration")
    if comparison["schema_version"].nunique(dropna=False) != 1 or (
        str(comparison["schema_version"].iloc[0])
        != input_config["expected_schema_version"]
    ):
        failures.append("M3.2 comparison schema version does not match")
    if comparison["m3_window_construction_version"].nunique(dropna=False) != 1 or (
        str(comparison["m3_window_construction_version"].iloc[0])
        != input_config["expected_construction_version"]
    ):
        failures.append("M3.2 comparison construction version does not match")

    expected_output_rows = int(config["analysis"]["expected_output_rows"])
    if len(output) != expected_output_rows:
        failures.append("M3.3 output row count does not match")
    if output_duplicate_keys:
        failures.append("M3.3 output natural key is duplicated")
    flow_count_by_cell = output.groupby(
        ["connector_iso3", "analysis_sector"], observed=True
    )["flow_id"].nunique()
    incomplete_flow_cells = int(
        flow_count_by_cell.ne(len(config["trade_flows"])).sum()
    )
    if incomplete_flow_cells:
        failures.append("one or more connector-sector cells lack four flows")

    source_reconciliation: dict[str, Any] = {}
    boolean_source_fields = {
        "pre_zero_flag",
        "post_zero_flag",
        "dh_growth_defined",
        "log_growth_defined",
    }
    integer_source_fields = {
        "years_observed_pre",
        "years_observed_shock",
        "years_observed_post",
    }
    for flow_id in config["trade_flows"]:
        flow_output = output.loc[output["flow_id"].eq(flow_id)].sort_values(
            input_key
        )
        source = comparison.sort_values(input_key)
        flow_checks: dict[str, Any] = {}
        for output_field, suffix in SOURCE_FLOW_SUFFIXES.items():
            source_field = f"{flow_id}_{suffix}"
            if output_field in boolean_source_fields or output_field in integer_source_fields:
                mismatch = int(
                    flow_output[output_field]
                    .reset_index(drop=True)
                    .ne(source[source_field].reset_index(drop=True))
                    .sum()
                )
                flow_checks[output_field] = {"mismatch_count": mismatch}
                if mismatch:
                    failures.append(
                        f"{flow_id} source field {output_field} was not preserved"
                    )
            else:
                gap, missing_mismatch = maximum_absolute_gap(
                    flow_output[output_field].reset_index(drop=True),
                    source[source_field].reset_index(drop=True),
                )
                flow_checks[output_field] = {
                    "max_abs_gap": gap,
                    "missing_mismatch_count": missing_mismatch,
                }
                tolerance = (
                    float(config["validation"]["value_tolerance_usd"])
                    if output_field
                    in {
                        "value_usd_pre",
                        "value_usd_shock",
                        "value_usd_post",
                        "value_usd_change_post_pre",
                    }
                    else float(config["validation"]["numeric_tolerance"])
                )
                if gap > tolerance or missing_mismatch:
                    failures.append(
                        f"{flow_id} source field {output_field} was not preserved"
                    )
        source_reconciliation[flow_id] = flow_checks

    numeric_tolerance = float(config["validation"]["numeric_tolerance"])
    value_tolerance = float(config["validation"]["value_tolerance_usd"])
    recomputed_change = output["value_usd_post"] - output["value_usd_pre"]
    recomputed_dh = (
        2
        * (output["value_usd_post"] - output["value_usd_pre"])
        / (output["value_usd_post"] + output["value_usd_pre"])
    )
    recomputed_log = np.log(output["value_usd_post"]) - np.log(
        output["value_usd_pre"]
    )
    formula_checks: dict[str, Any] = {}
    for name, actual, expected, tolerance in [
        (
            "change_post_pre",
            output["value_usd_change_post_pre"],
            recomputed_change,
            value_tolerance,
        ),
        (
            "dh_growth_post_pre",
            output["value_usd_dh_growth_post_pre_raw"],
            recomputed_dh,
            numeric_tolerance,
        ),
        (
            "log_growth_post_pre",
            output["value_usd_log_growth_post_pre_raw"],
            recomputed_log,
            numeric_tolerance,
        ),
    ]:
        gap, missing_mismatch = maximum_absolute_gap(actual, expected)
        formula_checks[name] = {
            "max_abs_gap": gap,
            "missing_mismatch_count": missing_mismatch,
        }
        if gap > tolerance or missing_mismatch:
            failures.append(f"{name} independent formula check failed")

    expected_pre_zero = config["validation"]["expected_pre_zero_count_by_flow"]
    expected_negative = config["validation"][
        "expected_negative_change_count_by_flow"
    ]
    zero_and_negative_counts: dict[str, Any] = {}
    for flow_id in config["trade_flows"]:
        flow = output.loc[output["flow_id"].eq(flow_id)]
        counts = {
            "pre_zero": int(flow["pre_zero_flag"].sum()),
            "post_zero": int(flow["post_zero_flag"].sum()),
            "negative_change": int(
                flow["value_usd_change_post_pre"].lt(0).sum()
            ),
        }
        zero_and_negative_counts[flow_id] = counts
        if counts["pre_zero"] != int(expected_pre_zero[flow_id]):
            failures.append(f"{flow_id} pre-zero count changed")
        if counts["negative_change"] != int(expected_negative[flow_id]):
            failures.append(f"{flow_id} negative change count changed")

    absolute_threshold = float(
        config["small_base"]["absolute"]["threshold_usd"]
    )
    relative_percentile = float(
        config["small_base"]["sector_relative"]["percentile"]
    )
    recomputed_absolute = output["value_usd_pre"].le(absolute_threshold)
    recomputed_relative = pd.Series(False, index=output.index)
    recomputed_relative_cutoff = pd.Series(np.nan, index=output.index)
    for _, indices in output.groupby(
        config["small_base"]["sector_relative"]["group_fields"],
        sort=False,
        observed=True,
    ).groups.items():
        group_index = list(indices)
        cutoff = nearest_rank_cutoff(
            output.loc[group_index, "value_usd_pre"], relative_percentile
        )
        applicable = bool(
            output.loc[
                group_index, "sector_relative_threshold_applicable"
            ].iloc[0]
        )
        if applicable:
            recomputed_relative_cutoff.loc[group_index] = cutoff
            recomputed_relative.loc[group_index] = output.loc[
                group_index, "value_usd_pre"
            ].le(cutoff)
    recomputed_combined = (
        output["pre_zero_flag"] | recomputed_absolute | recomputed_relative
    )
    small_base_formula_checks = {
        "absolute_flag_mismatch_count": int(
            output["absolute_small_base_flag"].ne(recomputed_absolute).sum()
        ),
        "relative_cutoff_max_abs_gap": maximum_absolute_gap(
            output["sector_relative_pre_value_cutoff_usd"],
            recomputed_relative_cutoff,
        )[0],
        "relative_cutoff_missing_mismatch_count": maximum_absolute_gap(
            output["sector_relative_pre_value_cutoff_usd"],
            recomputed_relative_cutoff,
        )[1],
        "relative_flag_mismatch_count": int(
            output["sector_relative_small_base_flag"]
            .ne(recomputed_relative)
            .sum()
        ),
        "combined_flag_mismatch_count": int(
            output["small_base_flag"].ne(recomputed_combined).sum()
        ),
    }
    if (
        small_base_formula_checks["absolute_flag_mismatch_count"]
        or small_base_formula_checks["relative_flag_mismatch_count"]
        or small_base_formula_checks["combined_flag_mismatch_count"]
        or small_base_formula_checks["relative_cutoff_max_abs_gap"]
        > value_tolerance
        or small_base_formula_checks["relative_cutoff_missing_mismatch_count"]
    ):
        failures.append("one or more small-base formulas fail independent checks")

    small_base_counts: dict[str, Any] = {}
    for flow_id in config["trade_flows"]:
        flow = output.loc[output["flow_id"].eq(flow_id)]
        counts = {
            "absolute": int(flow["absolute_small_base_flag"].sum()),
            "sector_relative": int(
                flow["sector_relative_small_base_flag"].sum()
            ),
            "combined": int(flow["small_base_flag"].sum()),
            "primary_dh_eligible": int(
                flow["dh_growth_primary_eligible"].sum()
            ),
            "no_threshold_dh_eligible": int(
                flow["dh_growth_no_threshold_eligible"].sum()
            ),
        }
        small_base_counts[flow_id] = counts
        for observed_name, expected_name in [
            ("absolute", "expected_absolute_small_base_count_by_flow"),
            (
                "sector_relative",
                "expected_sector_relative_small_base_count_by_flow",
            ),
            ("combined", "expected_combined_small_base_count_by_flow"),
        ]:
            if counts[observed_name] != int(
                config["validation"][expected_name][flow_id]
            ):
                failures.append(
                    f"{flow_id} {observed_name} small-base count changed"
                )

    relative_reference_counts = sorted(
        output.loc[
            output["sector_relative_threshold_applicable"],
            "sector_relative_reference_cell_count",
        ]
        .unique()
        .tolist()
    )
    relative_rank_values = sorted(
        output.loc[
            output["sector_relative_threshold_applicable"],
            "sector_relative_nearest_rank",
        ]
        .unique()
        .tolist()
    )
    expected_relative_n = int(
        config["small_base"]["sector_relative"][
            "expected_reference_cell_count"
        ]
    )
    expected_rank = math.ceil(relative_percentile * expected_relative_n)
    if relative_reference_counts != [expected_relative_n]:
        failures.append("sector-relative reference group size is not 13")
    if relative_rank_values != [expected_rank]:
        failures.append("sector-relative nearest rank is not the frozen rank")
    common_relative = output.loc[output["flow_id"].eq("china_to_usa")]
    common_relative_nonapplicable = bool(
        (~common_relative["sector_relative_threshold_applicable"]).all()
        and common_relative["sector_relative_pre_value_cutoff_usd"].isna().all()
        and (~common_relative["sector_relative_small_base_flag"]).all()
    )
    if not common_relative_nonapplicable:
        failures.append("common China-USA benchmark received a relative threshold")

    robust_recomputed = robust_group_statistics(
        output.drop(
            columns=[
                "robust_z_group_median_dh",
                "robust_z_group_mad_dh",
                "robust_z_score_dh",
                "robust_z_defined",
                "robust_z_absolute_threshold",
                "robust_z_outlier_flag",
            ]
        ),
        config,
    )
    robust_formula_checks: dict[str, Any] = {}
    for field in [
        "robust_z_group_median_dh",
        "robust_z_group_mad_dh",
        "robust_z_score_dh",
    ]:
        gap, missing_mismatch = maximum_absolute_gap(
            output[field], robust_recomputed[field]
        )
        robust_formula_checks[field] = {
            "max_abs_gap": gap,
            "missing_mismatch_count": missing_mismatch,
        }
        if gap > numeric_tolerance or missing_mismatch:
            failures.append(f"{field} independent formula check failed")
    robust_formula_checks["defined_mismatch_count"] = int(
        output["robust_z_defined"]
        .ne(robust_recomputed["robust_z_defined"])
        .sum()
    )
    robust_formula_checks["outlier_mismatch_count"] = int(
        output["robust_z_outlier_flag"]
        .ne(robust_recomputed["robust_z_outlier_flag"])
        .sum()
    )
    if (
        robust_formula_checks["defined_mismatch_count"]
        or robust_formula_checks["outlier_mismatch_count"]
    ):
        failures.append("robust-z flags fail independent checks")

    robust_group_summary = (
        output.groupby(
            config["abnormal_growth"]["robust_z"]["group_fields"],
            observed=True,
        )
        .agg(
            mad=("robust_z_group_mad_dh", "first"),
            defined=("robust_z_defined", "any"),
        )
        .reset_index()
    )
    mad_zero_group_count = int(robust_group_summary["mad"].eq(0).sum())
    if mad_zero_group_count != int(
        config["validation"]["expected_mad_zero_group_count"]
    ):
        failures.append("MAD-zero group count changed")
    abnormal_counts: dict[str, Any] = {}
    for flow_id in config["trade_flows"]:
        flow = output.loc[output["flow_id"].eq(flow_id)]
        counts = {
            "robust_z_outlier": int(flow["robust_z_outlier_flag"].sum()),
            "mechanical_extreme": int(
                flow["mechanical_extreme_dh_flag"].sum()
            ),
            "combined_abnormal": int(flow["abnormal_growth_flag"].sum()),
        }
        abnormal_counts[flow_id] = counts
        for observed_name, expected_name in [
            ("robust_z_outlier", "expected_robust_z_outlier_count_by_flow"),
            ("mechanical_extreme", "expected_mechanical_extreme_count_by_flow"),
            ("combined_abnormal", "expected_abnormal_growth_count_by_flow"),
        ]:
            if counts[observed_name] != int(
                config["validation"][expected_name][flow_id]
            ):
                failures.append(f"{flow_id} {observed_name} count changed")

    lower_percentile = float(config["winsorization"]["lower_percentile"])
    upper_percentile = float(config["winsorization"]["upper_percentile"])
    winsor_formula_checks: dict[str, Any] = {}
    winsor_counts: dict[str, Any] = {}
    for flow_id in config["trade_flows"]:
        flow = output.loc[output["flow_id"].eq(flow_id)]
        flow_checks: dict[str, Any] = {}
        counts: dict[str, int] = {}
        for prefix, raw_field in [
            ("dh", "value_usd_dh_growth_post_pre_raw"),
            ("log", "value_usd_log_growth_post_pre_raw"),
        ]:
            lower = float(
                flow[raw_field].quantile(
                    lower_percentile, interpolation="linear"
                )
            )
            upper = float(
                flow[raw_field].quantile(
                    upper_percentile, interpolation="linear"
                )
            )
            expected_winsor = flow[raw_field].clip(lower=lower, upper=upper)
            cutoff_lower_gap, _ = maximum_absolute_gap(
                flow[f"{prefix}_winsor_lower_cutoff"],
                pd.Series(lower, index=flow.index),
            )
            cutoff_upper_gap, _ = maximum_absolute_gap(
                flow[f"{prefix}_winsor_upper_cutoff"],
                pd.Series(upper, index=flow.index),
            )
            value_gap, missing_mismatch = maximum_absolute_gap(
                flow[f"{prefix}_growth_winsorized"], expected_winsor
            )
            expected_affected = (
                flow[raw_field].notna()
                & expected_winsor.notna()
                & flow[raw_field].ne(expected_winsor)
            )
            affected_mismatch = int(
                flow[f"{prefix}_winsorized_affected_flag"]
                .ne(expected_affected)
                .sum()
            )
            count = int(
                flow[f"{prefix}_winsorized_affected_flag"].sum()
            )
            counts[prefix] = count
            flow_checks[prefix] = {
                "lower_cutoff": lower,
                "upper_cutoff": upper,
                "lower_cutoff_max_abs_gap": cutoff_lower_gap,
                "upper_cutoff_max_abs_gap": cutoff_upper_gap,
                "winsor_value_max_abs_gap": value_gap,
                "missing_mismatch_count": missing_mismatch,
                "affected_flag_mismatch_count": affected_mismatch,
            }
            if (
                cutoff_lower_gap > numeric_tolerance
                or cutoff_upper_gap > numeric_tolerance
                or value_gap > numeric_tolerance
                or missing_mismatch
                or affected_mismatch
            ):
                failures.append(f"{flow_id} {prefix} winsorization check failed")
            if count != int(
                config["validation"][
                    "expected_winsor_affected_count_by_flow"
                ][flow_id]
            ):
                failures.append(f"{flow_id} {prefix} winsor count changed")
        winsor_formula_checks[flow_id] = flow_checks
        winsor_counts[flow_id] = counts

    winsor_reference_counts = sorted(
        output["winsor_reference_cell_count"].unique().tolist()
    )
    if winsor_reference_counts != [
        int(config["winsorization"]["expected_reference_cell_count"])
    ]:
        failures.append("winsor reference group size is not 91")
    if not output["raw_level_change_preserved"].all():
        failures.append("raw level-change preservation flag is false")
    if not output["winsorized_values_for_sensitivity_only"].all():
        failures.append("winsorized sensitivity-only flag is false")
    if not output["abnormal_growth_is_advisory"].all():
        failures.append("abnormal-growth advisory flag is false")
    required_version_fields = [
        "m3_window_construction_version",
        "m3_growth_diagnostic_version",
        "rules_config_sha256",
        "schema_version",
    ]
    version_missing_counts = {
        field: int(output[field].isna().sum())
        for field in required_version_fields
    }
    version_unique_counts = {
        field: int(output[field].nunique(dropna=False))
        for field in required_version_fields
    }
    if any(version_missing_counts.values()) or any(
        count != 1 for count in version_unique_counts.values()
    ):
        failures.append("M3.3 version metadata is missing or non-constant")

    dh_out_of_bounds_count = int(
        output["value_usd_dh_growth_post_pre_raw"].abs().gt(2).sum()
    )
    infinite_numeric_count = int(
        np.isinf(output.select_dtypes(include=[np.number]).to_numpy()).sum()
    )
    if dh_out_of_bounds_count:
        failures.append("raw DH growth is outside [-2, 2]")
    if infinite_numeric_count:
        failures.append("M3.3 output contains infinite numeric values")

    china_usa = output.loc[output["flow_id"].eq("china_to_usa")]
    common_fields = [
        "value_usd_pre",
        "value_usd_shock",
        "value_usd_post",
        "value_usd_change_post_pre",
        "value_usd_dh_growth_post_pre_raw",
        "value_usd_log_growth_post_pre_raw",
        "robust_z_group_median_dh",
        "robust_z_group_mad_dh",
        "dh_winsor_lower_cutoff",
        "dh_winsor_upper_cutoff",
        "log_winsor_lower_cutoff",
        "log_winsor_upper_cutoff",
    ]
    common_inconsistencies = {
        field: int(
            china_usa.groupby("analysis_sector", observed=True)[field]
            .nunique(dropna=False)
            .gt(1)
            .sum()
        )
        for field in common_fields
    }
    if any(common_inconsistencies.values()):
        failures.append("China-USA repeated benchmark varies across connectors")
    if (
        not china_usa["flow_repeated_across_connectors"].all()
        or not china_usa["flow_not_additive_across_connectors"].all()
    ):
        failures.append("China-USA repeated/non-additive flags are incomplete")
    connector_specific = output.loc[output["flow_id"].ne("china_to_usa")]
    if (
        connector_specific["flow_repeated_across_connectors"].any()
        or connector_specific["flow_not_additive_across_connectors"].any()
    ):
        failures.append("connector-specific flows are incorrectly marked repeated")

    twn = output.loc[output["connector_iso3"].eq("TWN")]
    twn_checks = {
        "row_count": len(twn),
        "proxy_false_count": int((~twn["connector_is_proxy"]).sum()),
    }
    if (
        len(twn) != int(config["validation"]["expected_twn_rows"])
        or twn_checks["proxy_false_count"]
    ):
        failures.append("TWN rows or proxy flags are incomplete")

    aliases = config["outputs"]["diagnostics"]["stata_aliases"]
    stata_alias_validation = alias_validation(output, aliases)
    if not stata_alias_validation["pass"]:
        failures.append("Stata alias map fails completeness or length checks")
    if not determinism["sha256_match"]:
        failures.append("deterministic output SHA256 does not match")
    if not determinism["temporary_output_cleaned"]:
        failures.append("determinism temporary directory was not cleaned")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_match": input_hash_match,
        "input_row_count": len(comparison),
        "input_column_count": len(comparison.columns),
        "input_duplicate_key_count": input_duplicate_keys,
        "input_arrow_schema_signature_sha256": input_schema_signature,
        "output_row_count": len(output),
        "output_column_count": len(output.columns),
        "output_duplicate_key_count": output_duplicate_keys,
        "incomplete_four_flow_cell_count": incomplete_flow_cells,
        "connector_count": len(observed_connectors),
        "sector_count": len(observed_sectors),
        "flow_count": len(config["trade_flows"]),
        "source_reconciliation": source_reconciliation,
        "growth_formula_checks": formula_checks,
        "zero_and_negative_counts": zero_and_negative_counts,
        "small_base_formula_checks": small_base_formula_checks,
        "small_base_counts": small_base_counts,
        "sector_relative_reference_counts": relative_reference_counts,
        "sector_relative_rank_values": relative_rank_values,
        "china_usa_relative_threshold_nonapplicable": (
            common_relative_nonapplicable
        ),
        "robust_z_formula_checks": robust_formula_checks,
        "mad_zero_group_count": mad_zero_group_count,
        "abnormal_growth_counts": abnormal_counts,
        "winsor_formula_checks": winsor_formula_checks,
        "winsor_affected_counts": winsor_counts,
        "winsor_reference_counts": winsor_reference_counts,
        "version_missing_counts": version_missing_counts,
        "version_unique_counts": version_unique_counts,
        "dh_out_of_bounds_count": dh_out_of_bounds_count,
        "infinite_numeric_count": infinite_numeric_count,
        "china_usa_common_field_inconsistencies": common_inconsistencies,
        "twn_checks": twn_checks,
        "stata_alias_validation": stata_alias_validation,
        "determinism_check": determinism,
        "numeric_tolerance": numeric_tolerance,
        "value_tolerance_usd": value_tolerance,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# M3.3 Connector Trade Sector Growth Diagnostics Validation",
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
        f"- Output: `{validation['output']['path']}`",
        f"- Rows / columns: `{validation['output_row_count']} / {validation['output_column_count']}`",
        f"- Natural key: `connector_iso3, analysis_sector, flow_id`",
        f"- SHA256: `{validation['output']['sha256']}`",
        "",
        "## Required gates",
        "",
        f"- Frozen M3.2 hash matches: `{'yes' if validation['input_hash_match'] else 'no'}`.",
        f"- Input rows / columns / duplicate keys: `{validation['input_row_count']} / {validation['input_column_count']} / {validation['input_duplicate_key_count']}`.",
        f"- Output rows / columns / duplicate keys: `{validation['output_row_count']} / {validation['output_column_count']} / {validation['output_duplicate_key_count']}`.",
        f"- Incomplete four-flow connector-sector cells: `{validation['incomplete_four_flow_cell_count']}`.",
        f"- Deterministic Parquet SHA256 match: `{'yes' if validation['determinism_check']['sha256_match'] else 'no'}`.",
        f"- DH out-of-bounds / infinite numeric values: `{validation['dh_out_of_bounds_count']} / {validation['infinite_numeric_count']}`.",
        "",
        "## Small-base rules",
        "",
        "- Absolute threshold: annual-mean pre-period trade value `<= USD 25,000,000`.",
        "- Sector-relative threshold: nearest-rank 10th percentile within `flow_id × analysis_sector`; 13 connectors imply rank 2.",
        "- The repeated China-to-USA benchmark does not receive a connector-relative threshold.",
        "- Combined flag: `pre_zero OR absolute_small_base OR sector_relative_small_base`.",
        "- Raw levels, level changes, DH growth, and log growth are never overwritten.",
        "",
        "| Flow | Absolute | Sector-relative | Combined | Primary DH eligible | No-threshold DH eligible |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for flow_id, counts in validation["small_base_counts"].items():
        lines.append(
            f"| `{flow_id}` | {counts['absolute']} | "
            f"{counts['sector_relative']} | {counts['combined']} | "
            f"{counts['primary_dh_eligible']} | "
            f"{counts['no_threshold_dh_eligible']} |"
        )
    lines.extend(
        [
            "",
            "## Abnormal-growth diagnostics",
            "",
            "- Robust z-score uses the median and MAD within `flow_id × analysis_sector`; `|z| > 3.5` is flagged.",
            "- A second mechanical flag marks `|DH| >= 1.5`, equivalent to a post/pre ratio of at least 7 or at most 1/7.",
            "- The combined abnormal flag is advisory. It does not automatically exclude or alter an observation.",
            f"- MAD-zero groups: `{validation['mad_zero_group_count']}`; these are the seven repeated China-to-USA sector groups and robust z is undefined there.",
            "",
            "| Flow | Robust-z outliers | Mechanical extremes | Combined abnormal |",
            "|---|---:|---:|---:|",
        ]
    )
    for flow_id, counts in validation["abnormal_growth_counts"].items():
        lines.append(
            f"| `{flow_id}` | {counts['robust_z_outlier']} | "
            f"{counts['mechanical_extreme']} | "
            f"{counts['combined_abnormal']} |"
        )
    lines.extend(
        [
            "",
            "## Winsorized sensitivity variables",
            "",
            "- DH and log growth receive flow-level p5/p95 linear/type-7 winsorized alternatives.",
            "- Each flow has 91 reference cells. Winsorized measures are sensitivity variables only.",
            "- Level changes are not winsorized. Raw DH/log values remain in separate fields.",
            "",
            "| Flow | DH affected | Log affected | DH lower | DH upper | Log lower | Log upper |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for flow_id, counts in validation["winsor_affected_counts"].items():
        details = validation["winsor_formula_checks"][flow_id]
        lines.append(
            f"| `{flow_id}` | {counts['dh']} | {counts['log']} | "
            f"{details['dh']['lower_cutoff']:.12f} | "
            f"{details['dh']['upper_cutoff']:.12f} | "
            f"{details['log']['lower_cutoff']:.12f} | "
            f"{details['log']['upper_cutoff']:.12f} |"
        )
    lines.extend(
        [
            "",
            "## Preserved edge cases and interface",
            "",
            f"- Negative post-pre changes by flow are retained: `{validation['zero_and_negative_counts']}`.",
            f"- China-to-USA repeated-field inconsistencies: `{sum(validation['china_usa_common_field_inconsistencies'].values())}`.",
            f"- TWN rows / false proxy flags: `{validation['twn_checks']['row_count']} / {validation['twn_checks']['proxy_false_count']}`.",
            f"- Stata aliases: `{validation['stata_alias_validation']['alias_count']}`; maximum length `{validation['stata_alias_validation']['maximum_alias_length']}`; pass `{'yes' if validation['stata_alias_validation']['pass'] else 'no'}`.",
            "- Canonical format remains Parquet. No `.dta` is generated before M7.",
            "",
            "## Interpretation boundaries",
            "",
            "- `small_base_flag` controls eligibility for the preferred DH/log comparison; the raw no-threshold DH measure remains available for robustness.",
            "- `abnormal_growth_flag` is a review flag, not a deletion rule.",
            "- Winsorized growth values are robustness alternatives, not replacements for raw growth.",
            "- This module does not construct replacement ratios, connector rankings, production-side variables, structural moments, or counterfactual inputs.",
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


def read_input(
    project_root: Path,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pa.Schema]:
    path = (
        project_root
        / config["inputs"]["connector_trade_sector_window_comparison"]["path"]
    )
    table = pq.read_table(path)
    return table.to_pandas(), table.schema


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    candidate_output: Path,
) -> dict[str, Any]:
    temp_directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if temp_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse pre-existing temp directory: {temp_directory}"
        )
    temp_directory.mkdir(parents=True)
    second_output = (
        temp_directory
        / "connector_trade_sector_growth_diagnostics_second.parquet"
    )
    try:
        comparison, _ = read_input(project_root, config)
        second = build_output(comparison, config, config_hash)
        write_parquet(second, second_output)
        result = {
            "required": bool(
                config["validation"]["require_deterministic_parquet_sha256"]
            ),
            "candidate_sha256": sha256(candidate_output),
            "second_build_sha256": sha256(second_output),
            "temporary_directory": temp_directory.relative_to(
                project_root
            ).as_posix(),
        }
        result["sha256_match"] = (
            result["candidate_sha256"] == result["second_build_sha256"]
        )
    finally:
        remove_owned_temp_directory(temp_directory)
    result["temporary_output_cleaned"] = not temp_directory.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate M3.3 zero/small-base, abnormal-growth, "
            "and winsorized sensitivity diagnostics."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/connector_trade_sector_growth_diagnostic_rules.yaml"
        ),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    output_path = relative_or_absolute(
        project_root,
        args.output or Path(config["outputs"]["diagnostics"]["path"]),
    ).resolve()
    validation_json = relative_or_absolute(
        project_root,
        args.validation_json or Path(config["validation_outputs"]["json"]),
    ).resolve()
    validation_md = relative_or_absolute(
        project_root,
        args.validation_md or Path(config["validation_outputs"]["markdown"]),
    ).resolve()
    for path in [output_path, validation_json, validation_md]:
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
    candidate_output = candidate_directory / output_path.name

    try:
        input_path = (
            project_root
            / config["inputs"][
                "connector_trade_sector_window_comparison"
            ]["path"]
        )
        input_hash_match = (
            sha256(input_path)
            == config["inputs"][
                "connector_trade_sector_window_comparison"
            ]["sha256"]
        )
        comparison, input_schema = read_input(project_root, config)
        output = build_output(comparison, config, config_hash)
        output_table = write_parquet(output, candidate_output)
        determinism = deterministic_rebuild(
            project_root,
            config,
            config_hash,
            candidate_output,
        )
        validation = validate(
            comparison,
            input_schema,
            output,
            config,
            input_hash_match,
            determinism,
        )
        validation.update(
            {
                "validation_version": 1,
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path.relative_to(project_root).as_posix(),
                "config_sha256": config_hash,
                "construction_version": config["version"],
                "schema_version": config["schema_version"],
                "output": {
                    "path": output_path.relative_to(project_root).as_posix(),
                    "sha256": sha256(candidate_output),
                    "schema": [
                        {
                            "name": field.name,
                            "type": str(field.type),
                            "nullable": field.nullable,
                        }
                        for field in output_table.schema
                    ],
                },
                "candidate_temp_directory": candidate_directory.relative_to(
                    project_root
                ).as_posix(),
            }
        )
        if validation["validation_status"] != "PASS":
            print(json.dumps(validation, ensure_ascii=False, indent=2))
            raise SystemExit(1)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_output.replace(output_path)
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
                    "output_rows": validation["output_row_count"],
                    "output_columns": validation["output_column_count"],
                    "output_sha256": validation["output"]["sha256"],
                    "deterministic_sha256_match": determinism[
                        "sha256_match"
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
