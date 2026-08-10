#!/usr/bin/env python3
"""Build and validate the M4.6 cross-source production evidence interfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "production_validation_long_rules.yaml"
OWNER_FILE = ".m4_6_owner"
PARQUET_COMPRESSION = "zstd"
PARQUET_ROW_GROUP_SIZE = 65536


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_signature(schema: pa.Schema) -> str:
    payload = [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]
    encoded = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_scalar(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return str(value)


def natural_key_json(row: pd.Series, key_columns: list[str]) -> str:
    payload = {column: canonical_scalar(row[column]) for column in key_columns}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def observation_id(source_table: str, key_json: str) -> str:
    return hashlib.sha256(f"{source_table}|{key_json}".encode("utf-8")).hexdigest()


def normalize_path(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    return str(value).replace("\\", "/")


def get_series(df: pd.DataFrame, column: str, default: Any = None) -> pd.Series:
    if column in df.columns:
        return df[column]
    return pd.Series([default] * len(df), index=df.index)


def bool_series(df: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    return get_series(df, column, default).fillna(default).astype(bool)


def output_schema(config: dict[str, Any]) -> pa.Schema:
    aliases = config["stata_aliases"]
    boolean_columns = {
        "complete_period_flag",
        "annual_comparable_flag",
        "partial_year_flag",
        "value_available_flag",
        "suppressed_flag",
        "confidential_flag",
        "suppressed_or_confidential_flag",
        "partial_disclosure_flag",
        "small_value_flag",
        "aggregate_flag",
        "residual_flag",
        "parent_residual_flag",
        "proxy_flag",
        "observed_negative_flag",
        "reported_zero_flag",
        "exact_zero_flag",
        "cancellation_to_zero_flag",
        "national_total_flag",
        "one_dimensional_margin_flag",
        "source_native_join_eligible_flag",
        "host_country_sector_year_evidence_eligible_flag",
        "main_host_activity_join_eligible_flag",
        "country_year_benchmark_eligible_flag",
        "country_period_benchmark_eligible_flag",
        "diagnostic_only_flag",
        "nonadditive_flag",
        "can_sum_across_source_records",
        "can_sum_across_years",
        "can_sum_across_metrics",
        "financial_evidence_only_flag",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
    }
    integer_32_columns = {"year"}
    integer_16_columns = {
        "quarter",
        "period_start_quarter",
        "period_end_quarter",
        "expected_period_count",
        "observed_period_count",
        "metric_order",
    }
    float_columns = {"value", "source_disclosed_value_sum"}
    fields: list[pa.Field] = []
    for column in aliases:
        if column in boolean_columns:
            dtype = pa.bool_()
        elif column in integer_32_columns:
            dtype = pa.int32()
        elif column in integer_16_columns:
            dtype = pa.int16()
        elif column in float_columns:
            dtype = pa.float64()
        else:
            dtype = pa.string()
        fields.append(pa.field(column, dtype, nullable=True))
    return pa.schema(fields)


def load_and_audit_inputs(
    config: dict[str, Any], checks: list[dict[str, Any]]
) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for name, spec in config["inputs"].items():
        path = PROJECT_ROOT / spec["path"]
        exists = path.is_file()
        add_check(checks, f"input_{name}_exists", exists, str(path), "file exists")
        if not exists:
            continue
        observed_sha = sha256_file(path)
        table = pq.read_table(path)
        observed_schema = schema_signature(table.schema)
        df = table.to_pandas()
        add_check(checks, f"input_{name}_sha256", observed_sha == spec["sha256"], observed_sha, spec["sha256"])
        add_check(checks, f"input_{name}_rows", len(df) == spec["expected_rows"], len(df), spec["expected_rows"])
        add_check(checks, f"input_{name}_columns", len(df.columns) == spec["expected_columns"], len(df.columns), spec["expected_columns"])
        add_check(checks, f"input_{name}_schema", observed_schema == spec["arrow_schema_signature_sha256"], observed_schema, spec["arrow_schema_signature_sha256"])
        key = spec["natural_key"]
        key_present = all(column in df.columns for column in key)
        add_check(checks, f"input_{name}_key_columns", key_present, [c for c in key if c in df.columns], key)
        if key_present:
            null_count = int(df[key].isna().any(axis=1).sum())
            duplicate_count = int(df.duplicated(key, keep=False).sum())
            add_check(checks, f"input_{name}_key_nonmissing", null_count == 0, null_count, 0)
            add_check(checks, f"input_{name}_key_unique", duplicate_count == 0, duplicate_count, 0)
        frames[name] = df
    return frames


def audit_upstream_validations(config: dict[str, Any], checks: list[dict[str, Any]]) -> None:
    for name, spec in config["upstream_validations"].items():
        path = PROJECT_ROOT / spec["path"]
        exists = path.is_file()
        add_check(checks, f"upstream_validation_{name}_exists", exists, str(path), "file exists")
        if not exists:
            continue
        observed_sha = sha256_file(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        add_check(checks, f"upstream_validation_{name}_sha256", observed_sha == spec["sha256"], observed_sha, spec["sha256"])
        add_check(checks, f"upstream_validation_{name}_status", payload.get("validation_status") == "PASS", payload.get("validation_status"), "PASS")
        add_check(checks, f"upstream_validation_{name}_failures", payload.get("failures") == [], payload.get("failures"), [])


def add_check(
    checks: list[dict[str, Any]], name: str, passed: bool, observed: Any, expected: Any
) -> None:
    checks.append(
        {
            "name": name,
            "status": "PASS" if bool(passed) else "FAIL",
            "observed": observed,
            "expected": expected,
        }
    )


def country_group_lookup(country_crosswalk: pd.DataFrame) -> dict[str, dict[str, bool]]:
    columns = ["is_core_connector", "is_asian_comparator", "is_other_candidate"]
    actual = country_crosswalk.loc[country_crosswalk["country_iso3"].notna(), ["country_iso3", *columns]].copy()
    for column in columns:
        actual[column] = actual[column].fillna(False).astype(bool)
    consistency = actual.groupby("country_iso3")[columns].nunique(dropna=False)
    if int((consistency > 1).any(axis=1).sum()) != 0:
        raise ValueError("Country group flags are inconsistent within country_iso3.")
    unique = actual.drop_duplicates("country_iso3")
    return {
        str(row.country_iso3): {
            column: bool(getattr(row, column)) for column in columns
        }
        for row in unique.itertuples(index=False)
    }


def initialize_common(
    df: pd.DataFrame,
    source_table: str,
    input_path: str,
    natural_key: list[str],
    config: dict[str, Any],
    config_sha: str,
) -> pd.DataFrame:
    output = pd.DataFrame(index=df.index)
    output["source_table"] = source_table
    output["source_natural_key"] = df.apply(lambda row: natural_key_json(row, natural_key), axis=1)
    output["source_observation_id"] = output["source_natural_key"].map(
        lambda key: observation_id(source_table, key)
    )
    output["source_input_path"] = input_path.replace("\\", "/")
    for column in config["stata_aliases"]:
        if column not in output.columns:
            output[column] = None
    output["m4_6_version"] = config["construction_version"]
    output["rules_config_sha256"] = config_sha
    output["schema_version"] = config["outputs"]["full_registry"]["schema_version"]
    output["can_sum_across_source_records"] = False
    output["nonadditive_flag"] = True
    return output


def add_group_flags(output: pd.DataFrame, lookup: dict[str, dict[str, bool]]) -> None:
    for column in ["is_core_connector", "is_asian_comparator", "is_other_candidate"]:
        output[column] = output["country_iso3"].map(
            lambda iso: lookup.get(str(iso), {}).get(column, False)
            if iso is not None and not pd.isna(iso)
            else False
        )
    output["comparison_sample_country_flag"] = (
        output["is_core_connector"]
        | output["is_asian_comparator"]
        | output["is_other_candidate"]
    )


def set_missing_reason(output: pd.DataFrame) -> None:
    missing = output["value"].isna()
    output["missing_reason"] = "not_missing"
    output.loc[missing, "missing_reason"] = "source_missing_or_unavailable"
    output.loc[missing & output["suppressed_flag"].astype(bool), "missing_reason"] = "suppressed"
    output.loc[missing & output["confidential_flag"].astype(bool), "missing_reason"] = "confidential"
    output.loc[missing & ~output["complete_period_flag"].astype(bool), "missing_reason"] = "incomplete_period"


def finalize_common(output: pd.DataFrame, config: dict[str, Any], lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    boolean_columns = [
        column
        for column in config["stata_aliases"]
        if column.endswith("_flag")
        or column in {"can_sum_across_source_records", "can_sum_across_years", "can_sum_across_metrics"}
    ]
    for column in boolean_columns:
        output[column] = output[column].fillna(False).astype(bool)
    output["suppressed_or_confidential_flag"] = output["suppressed_flag"] | output["confidential_flag"]
    output["value_available_flag"] = output["value"].notna()
    add_group_flags(output, lookup)
    set_missing_reason(output)
    output["source_file"] = output["source_file"].map(normalize_path)
    return output[list(config["stata_aliases"].keys())]


def transform_icio(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "icio_analysis", spec["path"], spec["natural_key"], config, config_sha)
    out["evidence_family"] = "production_accounting"
    out["evidence_scope"] = "host_sector_accounting"
    out["country_iso3"] = df["country_iso3"]
    out["canonical_country_name"] = df["canonical_country_name"]
    out["country_role"] = "production_host_country"
    out["host_country_iso3"] = df["country_iso3"]
    out["foreign_country_role"] = "not_applicable"
    out["investment_direction"] = "not_applicable"
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = "main"
    out["year"] = df["year"]
    out["period_type"] = "calendar_year"
    out["period_id"] = df["year"].astype(str)
    out["expected_period_count"] = 1
    out["observed_period_count"] = 1
    out["complete_period_flag"] = True
    out["annual_comparable_flag"] = True
    out["partial_year_flag"] = False
    out["frequency"] = df["frequency"]
    out["temporal_type"] = "annual_accounting_level"
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = df["metric_order"]
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["icio"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["value"]
    out["unit"] = df["unit"]
    out["direction"] = df["direction"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    out["suppressed_flag"] = bool_series(df, "suppressed_flag")
    out["confidential_flag"] = bool_series(df, "confidential_flag")
    out["aggregate_flag"] = bool_series(df, "aggregate_flag")
    out["residual_flag"] = bool_series(df, "residual_flag")
    out["proxy_flag"] = bool_series(df, "proxy_flag")
    out["observed_negative_flag"] = bool_series(df, "observed_negative_flag")
    out["reported_zero_flag"] = bool_series(df, "observed_zero_flag")
    out["exact_zero_flag"] = bool_series(df, "observed_zero_flag")
    out["source_native_join_eligible_flag"] = True
    out["host_country_sector_year_evidence_eligible_flag"] = True
    out["main_host_activity_join_eligible_flag"] = True
    out["join_role"] = "host_country_sector_year_main"
    out["diagnostic_only_flag"] = df["metric_name"].eq("accounting_residual")
    out["can_sum_across_years"] = False
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = False
    out["source_file"] = df["source_file"]
    out["source_release"] = df["icio_release"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def transform_amne(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "amne_host_sector", spec["path"], spec["natural_key"], config, config_sha)
    out["evidence_family"] = "foreign_affiliate_activity"
    out["evidence_scope"] = "host_sector_foreign_affiliate_activity"
    out["country_iso3"] = df["country_iso3"]
    out["canonical_country_name"] = df["canonical_country_name"]
    out["country_role"] = "affiliate_host_country"
    out["host_country_iso3"] = df["country_iso3"]
    out["foreign_country_role"] = "affiliate_host_country"
    out["investment_direction"] = "foreign_affiliate_activity_in_host"
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = "main"
    out["year"] = df["year"]
    out["period_type"] = "calendar_year"
    out["period_id"] = df["year"].astype(str)
    out["expected_period_count"] = 1
    out["observed_period_count"] = 1
    out["complete_period_flag"] = True
    out["annual_comparable_flag"] = True
    out["partial_year_flag"] = False
    out["frequency"] = df["frequency"]
    out["temporal_type"] = df["unit"].map(lambda value: "annual_ratio" if value == "fraction" else "annual_activity_level")
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = df["metric_order"]
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["amne"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["value"]
    out["unit"] = df["unit"]
    out["direction"] = df["direction"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    out["suppressed_flag"] = bool_series(df, "suppressed_flag")
    out["confidential_flag"] = bool_series(df, "confidential_flag")
    out["aggregate_flag"] = bool_series(df, "aggregate_flag")
    out["residual_flag"] = bool_series(df, "residual_flag")
    out["proxy_flag"] = bool_series(df, "proxy_flag")
    out["observed_negative_flag"] = bool_series(df, "observed_negative_flag")
    out["reported_zero_flag"] = bool_series(df, "observed_zero_flag")
    out["exact_zero_flag"] = bool_series(df, "observed_zero_flag")
    out["source_native_join_eligible_flag"] = True
    out["host_country_sector_year_evidence_eligible_flag"] = True
    out["main_host_activity_join_eligible_flag"] = True
    out["join_role"] = "host_country_sector_year_main"
    out["diagnostic_only_flag"] = df["metric_name"].isin(["bilateral_affiliate_output_sum", "foreign_affiliate_output_share"])
    out["can_sum_across_years"] = False
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = False
    out["source_file"] = df["source_file"]
    out["source_release"] = df["amne_release"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def transform_bea_mne(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "bea_mne_analysis", spec["path"], spec["natural_key"], config, config_sha)
    main = bool_series(df, "main_analysis_join_eligible")
    out["evidence_family"] = "us_mne_affiliate_activity"
    out["evidence_scope"] = df["analysis_scope"].map({"main": "host_sector_majority_owned_affiliate_activity", "proxy_robustness": "host_sector_transportation_equipment_proxy"})
    out["country_iso3"] = df["country_iso3"]
    out["canonical_country_name"] = df["canonical_country_name"]
    out["country_role"] = "affiliate_host_country"
    out["host_country_iso3"] = df["country_iso3"]
    out["parent_country_iso3"] = df["parent_country_iso3"]
    out["origin_country_iso3"] = df["parent_country_iso3"]
    out["destination_country_iso3"] = df["country_iso3"]
    out["foreign_country_role"] = "affiliate_host_country"
    out["investment_direction"] = "us_parent_owned_foreign_affiliate_activity"
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = df["analysis_scope"]
    out["year"] = df["year"]
    out["period_type"] = "calendar_year"
    out["period_id"] = df["year"].astype(str)
    out["expected_period_count"] = 1
    out["observed_period_count"] = 1
    out["complete_period_flag"] = True
    out["annual_comparable_flag"] = True
    out["partial_year_flag"] = False
    out["frequency"] = df["frequency"]
    out["temporal_type"] = "annual_activity_level"
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = df["metric_order"]
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["bea_mne"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["source_disclosed_value_sum"]
    out["unit"] = df["unit"]
    out["direction"] = df["direction"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    for column in ["suppressed_flag", "confidential_flag", "partial_disclosure_flag", "small_value_flag", "aggregate_flag", "residual_flag", "proxy_flag", "observed_negative_flag", "reported_zero_flag", "exact_zero_flag", "cancellation_to_zero_flag"]:
        out[column] = bool_series(df, column)
    out["source_native_join_eligible_flag"] = main
    out["host_country_sector_year_evidence_eligible_flag"] = main
    out["main_host_activity_join_eligible_flag"] = main
    out["join_role"] = main.map(lambda flag: "host_country_sector_year_main" if flag else "host_country_sector_year_proxy")
    out["diagnostic_only_flag"] = ~main
    out["can_sum_across_years"] = False
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = False
    out["source_file"] = df["source_file"]
    out["source_release"] = df["release_vintage"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def transform_bea_fdi(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "bea_fdi_analysis", spec["path"], spec["natural_key"], config, config_sha)
    main = bool_series(df, "main_analysis_join_eligible")
    outward = df["investment_direction"].eq("us_direct_investment_abroad")
    out["evidence_family"] = "direct_investment_financial"
    out["evidence_scope"] = df["analysis_scope"].map({"main": "foreign_country_sector_financial", "proxy_robustness": "foreign_country_transportation_equipment_financial_proxy"})
    out["country_iso3"] = df["country_iso3"]
    out["canonical_country_name"] = df["canonical_country_name"]
    out["country_role"] = df["foreign_country_role"]
    out["host_country_iso3"] = df["destination_country_iso3"]
    out["origin_country_iso3"] = df["origin_country_iso3"]
    out["destination_country_iso3"] = df["destination_country_iso3"]
    out["foreign_country_role"] = df["foreign_country_role"]
    out["investment_direction"] = df["investment_direction"]
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = df["analysis_scope"]
    out["year"] = df["year"]
    out["period_type"] = "calendar_year"
    out["period_id"] = df["year"].astype(str)
    out["expected_period_count"] = 1
    out["observed_period_count"] = 1
    out["complete_period_flag"] = True
    out["annual_comparable_flag"] = True
    out["partial_year_flag"] = False
    out["frequency"] = df["frequency"]
    out["temporal_type"] = df["temporal_type"]
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = df["metric_order"]
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["bea_fdi"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["source_disclosed_value_sum"]
    out["unit"] = df["unit"]
    out["direction"] = df["direction_sign_convention"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    for column in ["suppressed_flag", "confidential_flag", "partial_disclosure_flag", "small_value_flag", "aggregate_flag", "residual_flag", "proxy_flag", "observed_negative_flag", "reported_zero_flag", "exact_zero_flag", "cancellation_to_zero_flag"]:
        out[column] = bool_series(df, column)
    out["source_native_join_eligible_flag"] = main
    out["host_country_sector_year_evidence_eligible_flag"] = outward & main
    out["main_host_activity_join_eligible_flag"] = False
    out["join_role"] = "origin_country_sector_year_financial"
    out.loc[outward & main, "join_role"] = "host_country_sector_year_main"
    out.loc[outward & ~main, "join_role"] = "host_country_sector_year_proxy"
    out["diagnostic_only_flag"] = ~main
    out["can_sum_across_years"] = bool_series(df, "can_sum_across_years")
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = True
    out["source_file"] = df["source_file"]
    out["source_release"] = df["release_vintage"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def transform_mexico_parent(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "mexico_parent_sector_period", spec["path"], spec["natural_key"], config, config_sha)
    residual = bool_series(df, "parent_country_is_residual")
    out["evidence_family"] = "direct_investment_financial"
    out["evidence_scope"] = "parent_origin_sector_period_financial"
    out["country_iso3"] = df["parent_country_iso3"]
    out["canonical_country_name"] = df["parent_canonical_country_name"].fillna(df["source_parent_country_name"])
    out["country_role"] = residual.map(lambda flag: "residual_parent_origin" if flag else "reported_parent_origin_country")
    out["host_country_iso3"] = df["host_country_iso3"]
    out["parent_country_iso3"] = df["parent_country_iso3"]
    out["source_parent_country_id"] = df["source_parent_country_id"]
    out["origin_country_iso3"] = df["origin_country_iso3"]
    out["destination_country_iso3"] = df["destination_country_iso3"]
    out["foreign_country_role"] = "reported_parent_origin"
    out["investment_direction"] = df["investment_direction"]
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = "source_native_parent_sector_period"
    out["year"] = df["year"]
    out["quarter"] = df["quarter"]
    out["period_type"] = df["period_type"]
    out["period_id"] = df["period_id"]
    out["period_start_quarter"] = df["period_start_quarter"]
    out["period_end_quarter"] = df["period_end_quarter"]
    out["expected_period_count"] = df["expected_quarter_count"]
    out["observed_period_count"] = df["observed_quarter_count"]
    out["complete_period_flag"] = bool_series(df, "complete_period_flag")
    out["annual_comparable_flag"] = bool_series(df, "annual_comparable_flag")
    out["partial_year_flag"] = bool_series(df, "partial_year_flag")
    out["frequency"] = df["period_type"].map({"quarter": "quarterly", "calendar_year": "annual", "h1": "semiannual_h1"})
    out["temporal_type"] = df["temporal_type"]
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = 1
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["mexico_fdi"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["source_disclosed_value_sum"]
    out["unit"] = df["unit"]
    out["direction"] = df["investment_direction"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    out["confidential_flag"] = bool_series(df, "confidential_flag")
    out["partial_disclosure_flag"] = bool_series(df, "partial_disclosure_flag")
    out["residual_flag"] = residual
    out["parent_residual_flag"] = residual
    out["observed_negative_flag"] = bool_series(df, "observed_negative_flag")
    out["reported_zero_flag"] = bool_series(df, "reported_zero_flag")
    out["exact_zero_flag"] = bool_series(df, "exact_zero_flag")
    out["cancellation_to_zero_flag"] = bool_series(df, "cancellation_to_zero_flag")
    out["source_native_join_eligible_flag"] = bool_series(df, "main_cross_source_join_eligible")
    out["host_country_sector_year_evidence_eligible_flag"] = False
    out["main_host_activity_join_eligible_flag"] = False
    out["join_role"] = "source_native_only"
    out["diagnostic_only_flag"] = True
    out["can_sum_across_years"] = bool_series(df, "can_sum_across_years")
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = True
    out["source_file"] = spec["source_file_override"]
    out["source_release"] = df["source_snapshot_date"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def transform_mexico_benchmark(df: pd.DataFrame, spec: dict[str, Any], config: dict[str, Any], config_sha: str, lookup: dict[str, dict[str, bool]]) -> pd.DataFrame:
    out = initialize_common(df, "mexico_benchmark_period", spec["path"], spec["natural_key"], config, config_sha)
    national = bool_series(df, "national_total_flag")
    parent_margin = df["benchmark_scope"].eq("parent_country_annual_margin")
    sector_margin = df["benchmark_scope"].eq("sector_annual_margin")
    parent_residual = df["parent_country_record_type"].eq("unknown_or_residual_source")
    out["evidence_family"] = "direct_investment_financial_benchmark"
    out["evidence_scope"] = "mexico_" + df["benchmark_scope"].astype(str)
    out["country_iso3"] = df["host_country_iso3"]
    out.loc[parent_margin, "country_iso3"] = df.loc[parent_margin, "parent_country_iso3"]
    out["canonical_country_name"] = df["host_country_name"]
    out.loc[parent_margin, "canonical_country_name"] = df.loc[parent_margin, "parent_canonical_country_name"].fillna(df.loc[parent_margin, "source_parent_country_name"])
    out["country_role"] = "host_country"
    out.loc[parent_margin, "country_role"] = "reported_parent_origin_country"
    out.loc[parent_residual, "country_role"] = "unknown_or_residual_parent_origin"
    out["host_country_iso3"] = df["host_country_iso3"]
    out["parent_country_iso3"] = df["parent_country_iso3"]
    out["source_parent_country_id"] = df["source_parent_country_id"]
    out["origin_country_iso3"] = df["origin_country_iso3"]
    out["destination_country_iso3"] = df["destination_country_iso3"]
    out["foreign_country_role"] = "benchmark_scope_specific"
    out["investment_direction"] = df["investment_direction"]
    out["analysis_sector"] = df["analysis_sector"]
    out["analysis_scope"] = df["benchmark_scope"]
    out["year"] = df["year"]
    out["quarter"] = df["quarter"]
    out["period_type"] = df["period_type"]
    out["period_id"] = df["period_id"]
    out["period_start_quarter"] = df["period_start_quarter"]
    out["period_end_quarter"] = df["period_end_quarter"]
    out["expected_period_count"] = df["expected_quarter_count"]
    out["observed_period_count"] = df["observed_quarter_count"]
    out["complete_period_flag"] = bool_series(df, "complete_period_flag")
    out["annual_comparable_flag"] = bool_series(df, "annual_comparable_flag")
    out["partial_year_flag"] = bool_series(df, "partial_year_flag")
    out["frequency"] = df["period_type"].map({"quarter": "quarterly", "calendar_year": "annual", "h1": "semiannual_h1"})
    out["temporal_type"] = df["temporal_type"]
    out["source_name"] = df["source_name"]
    out["metric_name"] = df["metric_name"]
    out["metric_order"] = 1
    out["metric_family"] = df["metric_name"].map(config["metric_families"]["mexico_fdi"])
    out["value"] = df["value"]
    out["source_disclosed_value_sum"] = df["source_disclosed_value_sum"]
    out["unit"] = df["unit"]
    out["direction"] = df["investment_direction"]
    out["direct_or_allocated"] = df["direct_or_allocated"]
    out["derivation_status"] = df["derivation_status"]
    out["metric_formula"] = df["metric_formula"]
    out["metric_use"] = df["metric_use"]
    out["confidential_flag"] = bool_series(df, "confidential_flag")
    out["aggregate_flag"] = national | bool_series(df, "one_dimensional_margin_flag")
    out["residual_flag"] = parent_residual
    out["parent_residual_flag"] = parent_residual
    out["observed_negative_flag"] = bool_series(df, "observed_negative_flag")
    out["reported_zero_flag"] = bool_series(df, "reported_zero_flag")
    out["exact_zero_flag"] = bool_series(df, "exact_zero_flag")
    out["national_total_flag"] = national
    out["one_dimensional_margin_flag"] = bool_series(df, "one_dimensional_margin_flag")
    out["source_native_join_eligible_flag"] = bool_series(df, "main_cross_source_join_eligible")
    out["host_country_sector_year_evidence_eligible_flag"] = False
    out["main_host_activity_join_eligible_flag"] = False
    out["country_period_benchmark_eligible_flag"] = national
    out["country_year_benchmark_eligible_flag"] = national & df["period_type"].eq("calendar_year")
    out["join_role"] = "source_native_only"
    out.loc[out["country_year_benchmark_eligible_flag"], "join_role"] = "country_year_benchmark"
    out["diagnostic_only_flag"] = ~out["country_year_benchmark_eligible_flag"]
    out["can_sum_across_years"] = bool_series(df, "can_sum_across_years")
    out["can_sum_across_metrics"] = bool_series(df, "can_sum_across_metrics")
    out["financial_evidence_only_flag"] = True
    out["source_file"] = df["source_file"]
    out["source_release"] = df["source_snapshot_date"]
    out["upstream_rules_config_sha256"] = df["rules_config_sha256"]
    out["upstream_schema_version"] = df["schema_version"]
    return finalize_common(out, config, lookup)


def build_frames(frames: dict[str, pd.DataFrame], config: dict[str, Any], config_sha: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = country_group_lookup(frames["country_crosswalk"])
    transforms = [
        transform_icio(frames["icio_analysis"], config["inputs"]["icio_analysis"], config, config_sha, lookup),
        transform_amne(frames["amne_host_sector"], config["inputs"]["amne_host_sector"], config, config_sha, lookup),
        transform_bea_mne(frames["bea_mne_analysis"], config["inputs"]["bea_mne_analysis"], config, config_sha, lookup),
        transform_bea_fdi(frames["bea_fdi_analysis"], config["inputs"]["bea_fdi_analysis"], config, config_sha, lookup),
        transform_mexico_parent(frames["mexico_parent_sector_period"], config["inputs"]["mexico_parent_sector_period"], config, config_sha, lookup),
        transform_mexico_benchmark(frames["mexico_benchmark_period"], config["inputs"]["mexico_benchmark_period"], config, config_sha, lookup),
    ]
    full = pd.concat(transforms, ignore_index=True)
    full = full.sort_values(["source_table", "source_observation_id"], kind="mergesort").reset_index(drop=True)
    main = full.loc[full["main_host_activity_join_eligible_flag"]].copy()
    main = main.sort_values(["country_iso3", "analysis_sector", "year", "source_name", "metric_name"], kind="mergesort").reset_index(drop=True)
    return full, main


def write_parquet(df: pd.DataFrame, path: Path, schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(df, schema=schema, preserve_index=False, safe=True)
    pq.write_table(
        table,
        path,
        compression=PARQUET_COMPRESSION,
        use_dictionary=True,
        write_statistics=True,
        row_group_size=PARQUET_ROW_GROUP_SIZE,
        version="2.6",
    )


def create_owned_temp(path: Path, owner: str) -> None:
    path.mkdir(parents=True, exist_ok=False)
    (path / OWNER_FILE).write_text(owner, encoding="utf-8")


def cleanup_owned_temp(path: Path, owner: str) -> None:
    marker = path / OWNER_FILE
    if path.exists() and marker.is_file() and marker.read_text(encoding="utf-8") == owner:
        shutil.rmtree(path)


def independently_audit_passthrough(
    frames: dict[str, pd.DataFrame], full: pd.DataFrame, config: dict[str, Any], checks: list[dict[str, Any]]
) -> None:
    for source_table, spec in config["inputs"].items():
        if source_table == "country_crosswalk":
            continue
        source = frames[source_table]
        expected = source.apply(lambda row: natural_key_json(row, spec["natural_key"]), axis=1)
        expected_ids = expected.map(lambda key: observation_id(source_table, key))
        observed = full.loc[full["source_table"].eq(source_table)].set_index("source_observation_id")
        add_check(checks, f"passthrough_{source_table}_id_set", set(expected_ids) == set(observed.index), len(set(expected_ids) ^ set(observed.index)), 0)
        value_by_id = pd.Series(source["value"].to_numpy(), index=expected_ids)
        aligned = observed.loc[value_by_id.index, "value"]
        equal_values = ((value_by_id.isna() & aligned.isna()) | (value_by_id == aligned)).all()
        add_check(checks, f"passthrough_{source_table}_value", bool(equal_values), bool(equal_values), True)
        source_suppressed = bool_series(source, "suppressed_flag")
        source_confidential = bool_series(source, "confidential_flag")
        observed_suppressed = observed.loc[expected_ids, "suppressed_flag"].reset_index(drop=True)
        observed_confidential = observed.loc[expected_ids, "confidential_flag"].reset_index(drop=True)
        add_check(checks, f"passthrough_{source_table}_suppressed", source_suppressed.reset_index(drop=True).equals(observed_suppressed), int((source_suppressed.reset_index(drop=True) != observed_suppressed).sum()), 0)
        add_check(checks, f"passthrough_{source_table}_confidential", source_confidential.reset_index(drop=True).equals(observed_confidential), int((source_confidential.reset_index(drop=True) != observed_confidential).sum()), 0)


def validate_outputs(
    frames: dict[str, pd.DataFrame], full: pd.DataFrame, main: pd.DataFrame, config: dict[str, Any], checks: list[dict[str, Any]]
) -> None:
    validation = config["validation"]
    full_spec = config["outputs"]["full_registry"]
    main_spec = config["outputs"]["main_host_activity"]
    add_check(checks, "full_rows", len(full) == full_spec["expected_rows"], len(full), full_spec["expected_rows"])
    add_check(checks, "full_columns", len(full.columns) == full_spec["expected_columns"], len(full.columns), full_spec["expected_columns"])
    add_check(checks, "full_key_nonmissing", not full[full_spec["natural_key"]].isna().any(axis=1).any(), int(full[full_spec["natural_key"]].isna().any(axis=1).sum()), 0)
    add_check(checks, "full_key_unique", not full.duplicated(full_spec["natural_key"], keep=False).any(), int(full.duplicated(full_spec["natural_key"], keep=False).sum()), 0)
    add_check(checks, "main_rows", len(main) == main_spec["expected_rows"], len(main), main_spec["expected_rows"])
    add_check(checks, "main_columns", len(main.columns) == main_spec["expected_columns"], len(main.columns), main_spec["expected_columns"])
    add_check(checks, "main_key_unique", not main.duplicated(main_spec["natural_key"], keep=False).any(), int(main.duplicated(main_spec["natural_key"], keep=False).sum()), 0)
    add_check(checks, "main_exact_subset", set(main["source_observation_id"]) == set(full.loc[full["main_host_activity_join_eligible_flag"], "source_observation_id"]), len(set(main["source_observation_id"]) ^ set(full.loc[full["main_host_activity_join_eligible_flag"], "source_observation_id"])), 0)
    observed_source_rows = full["source_table"].value_counts().sort_index().to_dict()
    add_check(checks, "source_partition_rows", observed_source_rows == dict(sorted(validation["expected_source_rows"].items())), observed_source_rows, validation["expected_source_rows"])
    observed_period_rows = full["period_type"].value_counts().to_dict()
    add_check(checks, "period_rows", observed_period_rows == validation["expected_period_rows"], observed_period_rows, validation["expected_period_rows"])
    snapshots = {
        "missing_value_rows": int(full["value"].isna().sum()),
        "suppressed_rows": int(full["suppressed_flag"].sum()),
        "confidential_rows": int(full["confidential_flag"].sum()),
        "observed_negative_rows": int(full["observed_negative_flag"].sum()),
        "exact_numeric_zero_rows": int(full["value"].eq(0).fillna(False).sum()),
        "proxy_rows": int(full["proxy_flag"].sum()),
        "source_native_join_eligible_rows": int(full["source_native_join_eligible_flag"].sum()),
        "host_country_sector_year_evidence_eligible_rows": int(full["host_country_sector_year_evidence_eligible_flag"].sum()),
        "main_host_activity_rows": int(full["main_host_activity_join_eligible_flag"].sum()),
        "main_host_activity_available_rows": int((full["main_host_activity_join_eligible_flag"] & full["value_available_flag"]).sum()),
        "main_host_activity_country_count": int(main["country_iso3"].nunique()),
        "main_host_activity_sector_count": int(main["analysis_sector"].nunique()),
        "mexico_parent_main_join_rows": int(full.loc[full["source_table"].eq("mexico_parent_sector_period"), "main_host_activity_join_eligible_flag"].sum()),
        "mexico_national_period_benchmark_rows": int(full["country_period_benchmark_eligible_flag"].sum()),
        "mexico_national_calendar_year_benchmark_rows": int(full["country_year_benchmark_eligible_flag"].sum()),
    }
    for name, observed in snapshots.items():
        expected = validation[f"expected_{name}"]
        add_check(checks, name, observed == expected, observed, expected)
    role_counts = full["join_role"].value_counts().to_dict()
    add_check(checks, "join_role_rows", role_counts == validation["expected_join_role_rows"], role_counts, validation["expected_join_role_rows"])
    add_check(checks, "join_role_complete", full["join_role"].notna().all(), int(full["join_role"].isna().sum()), 0)
    add_check(checks, "all_rows_nonadditive_across_sources", not full["can_sum_across_source_records"].any(), int(full["can_sum_across_source_records"].sum()), 0)
    add_check(checks, "financial_excluded_from_main_activity", not full.loc[full["financial_evidence_only_flag"], "main_host_activity_join_eligible_flag"].any(), int(full.loc[full["financial_evidence_only_flag"], "main_host_activity_join_eligible_flag"].sum()), 0)
    add_check(checks, "proxy_excluded_from_main_activity", not full.loc[full["proxy_flag"], "main_host_activity_join_eligible_flag"].any(), int(full.loc[full["proxy_flag"], "main_host_activity_join_eligible_flag"].sum()), 0)
    icio_years = sorted(full.loc[full["source_table"].eq("icio_analysis"), "year"].unique().tolist())
    add_check(checks, "icio_years_no_interpolation", icio_years == validation["expected_icio_years"], icio_years, validation["expected_icio_years"])
    incomplete_mexico_2024 = int(full.loc[full["source_table"].eq("mexico_parent_sector_period") & full["year"].eq(2024) & full["period_type"].eq("calendar_year") & ~full["complete_period_flag"], :].shape[0])
    add_check(checks, "mexico_2024_incomplete_calendar_year_rows", incomplete_mexico_2024 == 255, incomplete_mexico_2024, 255)
    aliases = config["stata_aliases"]
    alias_values = list(aliases.values())
    aliases_valid = all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", alias) for alias in alias_values)
    aliases_unique = len({alias.lower() for alias in alias_values}) == len(alias_values)
    add_check(checks, "stata_alias_columns_complete", list(aliases.keys()) == list(full.columns), list(aliases.keys()) == list(full.columns), True)
    add_check(checks, "stata_aliases_valid", aliases_valid, aliases_valid, True)
    add_check(checks, "stata_aliases_unique", aliases_unique, aliases_unique, True)
    independently_audit_passthrough(frames, full, config, checks)


def render_markdown(report: dict[str, Any]) -> str:
    outputs = report["outputs"]
    snapshots = report["snapshots"]
    lines = [
        "# M4.6 跨来源 production evidence long validation",
        "",
        f"- Validation status: **{report['validation_status']}**",
        f"- Checks: **{report['pass_count']}/{report['check_count']} PASS**",
        f"- Full registry: `{outputs['full_registry']['path']}`，{outputs['full_registry']['rows']:,} × {outputs['full_registry']['columns']}，SHA256 `{outputs['full_registry']['sha256']}`",
        f"- Main host activity: `{outputs['main_host_activity']['path']}`，{outputs['main_host_activity']['rows']:,} × {outputs['main_host_activity']['columns']}，SHA256 `{outputs['main_host_activity']['sha256']}`",
        "",
        "## 设计结论",
        "",
        "完整 registry 一对一保留六张 M4.1-M4.5 analysis/financial/benchmark 输入。严格 main 表只保留 ICIO、AMNE 与 BEA MNE main-sector 的 host-country activity rows。BEA FDI、Mexico FDI 与 autos proxy 继续存在于 registry，但不会进入 main host activity 表。",
        "",
        "物理主键为 `source_table, source_observation_id`。旧的 `country_iso3, analysis_sector, year, source_name, metric_name` 只对严格 main host activity 子集唯一，不能识别 BEA FDI direction、Mexico parent 或 period。",
        "",
        "## 核验快照",
        "",
        "| 项目 | 结果 |",
        "|---|---:|",
    ]
    for label, value in snapshots.items():
        lines.append(f"| {label} | {value:,} |" if isinstance(value, int) else f"| {label} | {value} |")
    lines.extend(
        [
            "",
            "## 使用边界",
            "",
            "- `join_role` 明确区分 host main、host proxy、origin-country financial、country-year benchmark 和 source-native-only。",
            "- BEA FDI inward 的 `country_iso3` 是 foreign investor origin；Mexico parent 的 `country_iso3` 是 reported parent origin。两者均不能当作当地 production。",
            "- `suppressed_flag` 与 `confidential_flag` 分列保存；`suppressed_or_confidential_flag` 仅为便捷标记。所有 17,116 个缺失值均保留为缺失，未补零。",
            "- 所有行 `can_sum_across_source_records=false`；不同 source、metric、unit、period type 不得相加。",
            "- M4.6 未构造 growth、ranking、production grade、structural moments、welfare inputs 或 `.dta`。",
            "",
            "## Determinism",
            "",
            f"- Full registry second-build hash match: **{report['determinism']['full_registry_hash_match']}**",
            f"- Main host activity second-build hash match: **{report['determinism']['main_host_activity_hash_match']}**",
            f"- Task-owned temporary directories cleaned: **{report['temporary_directories_cleaned']}**",
            "",
        ]
    )
    return "\n".join(lines)


def run(config_path: Path) -> int:
    config_bytes = config_path.read_bytes()
    config_sha = hashlib.sha256(config_bytes).hexdigest()
    config = yaml.safe_load(config_bytes.decode("utf-8"))
    checks: list[dict[str, Any]] = []
    candidate_dir = PROJECT_ROOT / config["validation"]["candidate_temp_directory"]
    deterministic_dir = PROJECT_ROOT / config["validation"]["determinism_temp_directory"]
    for path in [candidate_dir, deterministic_dir]:
        if path.exists():
            raise FileExistsError(f"Refusing to reuse pre-existing task temp directory: {path}")
        if path.drive.upper() != PROJECT_ROOT.drive.upper():
            raise ValueError(f"Task temp directory is not on project drive: {path}")
    owner = str(uuid.uuid4())
    created: list[Path] = []
    report: dict[str, Any] | None = None
    try:
        create_owned_temp(candidate_dir, owner)
        created.append(candidate_dir)
        create_owned_temp(deterministic_dir, owner)
        created.append(deterministic_dir)
        frames = load_and_audit_inputs(config, checks)
        audit_upstream_validations(config, checks)
        if any(check["status"] == "FAIL" for check in checks):
            raise RuntimeError("Frozen input contract failed; canonical outputs were not changed.")
        schema = output_schema(config)
        full, main = build_frames(frames, config, config_sha)
        validate_outputs(frames, full, main, config, checks)
        candidate_full = candidate_dir / Path(config["outputs"]["full_registry"]["path"]).name
        candidate_main = candidate_dir / Path(config["outputs"]["main_host_activity"]["path"]).name
        write_parquet(full, candidate_full, schema)
        write_parquet(main, candidate_main, schema)
        first_hashes = {"full_registry": sha256_file(candidate_full), "main_host_activity": sha256_file(candidate_main)}

        second_checks: list[dict[str, Any]] = []
        second_frames = load_and_audit_inputs(config, second_checks)
        second_full, second_main = build_frames(second_frames, config, config_sha)
        deterministic_full = deterministic_dir / candidate_full.name
        deterministic_main = deterministic_dir / candidate_main.name
        write_parquet(second_full, deterministic_full, schema)
        write_parquet(second_main, deterministic_main, schema)
        second_hashes = {"full_registry": sha256_file(deterministic_full), "main_host_activity": sha256_file(deterministic_main)}
        add_check(checks, "deterministic_full_registry_hash", first_hashes["full_registry"] == second_hashes["full_registry"], second_hashes["full_registry"], first_hashes["full_registry"])
        add_check(checks, "deterministic_main_host_activity_hash", first_hashes["main_host_activity"] == second_hashes["main_host_activity"], second_hashes["main_host_activity"], first_hashes["main_host_activity"])
        failures = [check for check in checks if check["status"] == "FAIL"]
        if failures:
            print(json.dumps(failures, ensure_ascii=False, indent=2), file=sys.stderr)
            raise RuntimeError(f"M4.6 validation failed ({len(failures)} checks); canonical outputs were not changed.")

        canonical_full = PROJECT_ROOT / config["outputs"]["full_registry"]["path"]
        canonical_main = PROJECT_ROOT / config["outputs"]["main_host_activity"]["path"]
        canonical_full.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate_full, canonical_full)
        shutil.copyfile(candidate_main, canonical_main)
        snapshots = {
            "完整 registry 行数": len(full),
            "严格 main host activity 行数": len(main),
            "value 可用行": int(full["value_available_flag"].sum()),
            "value 缺失行": int(full["value"].isna().sum()),
            "suppressed 行": int(full["suppressed_flag"].sum()),
            "confidential 行": int(full["confidential_flag"].sum()),
            "observed negative 行": int(full["observed_negative_flag"].sum()),
            "numeric zero 行": int(full["value"].eq(0).fillna(False).sum()),
            "proxy 行": int(full["proxy_flag"].sum()),
            "financial-only 行": int(full["financial_evidence_only_flag"].sum()),
            "国家数（main union）": int(main["country_iso3"].nunique()),
            "sector 数（main union）": int(main["analysis_sector"].nunique()),
        }
        report = {
            "validation_status": "PASS",
            "failures": [],
            "checks": checks,
            "check_count": len(checks),
            "pass_count": sum(check["status"] == "PASS" for check in checks),
            "validation_version": "production_validation_long_validation_v1",
            "origin_date": config["origin_date"],
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "config_sha256": config_sha,
            "construction_version": config["construction_version"],
            "input_contracts": {name: {"path": spec["path"], "sha256": spec["sha256"], "expected_rows": spec["expected_rows"], "expected_columns": spec["expected_columns"], "arrow_schema_signature_sha256": spec["arrow_schema_signature_sha256"], "natural_key": spec["natural_key"]} for name, spec in config["inputs"].items()},
            "source_partition_rows": full["source_table"].value_counts().sort_index().to_dict(),
            "join_role_rows": full["join_role"].value_counts().to_dict(),
            "period_rows": full["period_type"].value_counts().to_dict(),
            "unit_rows": full["unit"].value_counts().to_dict(),
            "metric_registry": full.groupby(["source_table", "source_name", "metric_name", "metric_family", "unit"], dropna=False).size().reset_index(name="rows").to_dict(orient="records"),
            "snapshots": snapshots,
            "stata_alias_validation": {"column_count": len(config["stata_aliases"]), "aliases": config["stata_aliases"]},
            "outputs": {
                "full_registry": {"path": config["outputs"]["full_registry"]["path"], "rows": len(full), "columns": len(full.columns), "sha256": sha256_file(canonical_full), "schema_signature": schema_signature(pq.read_schema(canonical_full)), "natural_key": config["outputs"]["full_registry"]["natural_key"]},
                "main_host_activity": {"path": config["outputs"]["main_host_activity"]["path"], "rows": len(main), "columns": len(main.columns), "sha256": sha256_file(canonical_main), "schema_signature": schema_signature(pq.read_schema(canonical_main)), "natural_key": config["outputs"]["main_host_activity"]["natural_key"]},
            },
            "determinism": {"full_registry_first_sha256": first_hashes["full_registry"], "full_registry_second_sha256": second_hashes["full_registry"], "full_registry_hash_match": first_hashes["full_registry"] == second_hashes["full_registry"], "main_host_activity_first_sha256": first_hashes["main_host_activity"], "main_host_activity_second_sha256": second_hashes["main_host_activity"], "main_host_activity_hash_match": first_hashes["main_host_activity"] == second_hashes["main_host_activity"]},
            "temporary_directories_cleaned": False,
        }
    finally:
        for path in reversed(created):
            cleanup_owned_temp(path, owner)

    if report is None:
        return 1
    report["temporary_directories_cleaned"] = not candidate_dir.exists() and not deterministic_dir.exists()
    json_path = PROJECT_ROOT / config["validation_outputs"]["json"]
    markdown_path = PROJECT_ROOT / config["validation_outputs"]["markdown"]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"validation_status": report["validation_status"], "checks": f"{report['pass_count']}/{report['check_count']}", "outputs": report["outputs"], "temporary_directories_cleaned": report["temporary_directories_cleaned"]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    config_path = args.config.resolve()
    if not config_path.is_file():
        parser.error(f"Config not found: {config_path}")
    try:
        return run(config_path)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
