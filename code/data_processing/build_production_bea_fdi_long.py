#!/usr/bin/env python3
"""Build and validate the M4.4 BEA direct-investment long tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SOURCE_KEY = ["year", "direction", "country", "industry"]
SOURCE_LONG_KEY = [
    "source_name",
    "investment_direction",
    "source_country_id",
    "model_sector",
    "year",
    "metric_name",
]
ANALYSIS_LONG_KEY = [
    "country_iso3",
    "investment_direction",
    "analysis_sector",
    "year",
    "source_name",
    "metric_name",
]


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
        raise ValueError(f"Expected YAML mapping: {path}")
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


def validate_project_temp_path(project_root: Path, relative_path: str) -> Path:
    path = (project_root / relative_path).resolve()
    if not path.is_relative_to(project_root):
        raise ValueError(f"Temporary path escapes project root: {path}")
    if path.drive.lower() != project_root.drive.lower():
        raise ValueError(f"Temporary path is not on project drive: {path}")
    return path


def remove_owned_temp_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def normalize_source_file(value: object, project_root: Path) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).replace("\\", "/")
    root = project_root.as_posix().rstrip("/") + "/"
    return text[len(root) :] if text.lower().startswith(root.lower()) else text


def join_unique_text(values: pd.Series) -> object:
    items = sorted({str(value) for value in values.dropna() if str(value)})
    return " | ".join(items) if items else pd.NA


def max_abs(values: pd.Series | np.ndarray) -> float:
    array = np.asarray(values, dtype="float64")
    finite = np.abs(array[np.isfinite(array)])
    return float(finite.max()) if finite.size else 0.0


def schema_from_aliases(
    aliases: dict[str, str],
    *,
    bool_fields: set[str],
    int8_fields: set[str],
    int16_fields: set[str],
    int32_fields: set[str],
    float_fields: set[str],
) -> pa.Schema:
    fields: list[pa.Field] = []
    for name in aliases:
        if name in bool_fields:
            dtype = pa.bool_()
        elif name in int8_fields:
            dtype = pa.int8()
        elif name in int16_fields:
            dtype = pa.int16()
        elif name in int32_fields:
            dtype = pa.int32()
        elif name in float_fields:
            dtype = pa.float64()
        else:
            dtype = pa.large_string()
        fields.append(pa.field(name, dtype, nullable=True))
    return pa.schema(fields)


def source_long_schema(config: dict[str, Any]) -> pa.Schema:
    bool_fields = {
        "country_area_override_flag",
        "country_is_country",
        "country_is_aggregate",
        "country_is_residual",
        "country_is_proxy",
        "main_analysis_country_flag",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
        "sector_is_main_join_eligible",
        "value_available_flag",
        "suppressed_flag",
        "small_value_flag",
        "confidential_flag",
        "aggregate_geography_flag",
        "aggregate_sector_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "observed_negative_flag",
        "reported_zero_flag",
        "exact_zero_flag",
        "metric_additive_across_source_industries",
        "can_sum_across_years",
        "can_sum_across_metrics",
    }
    return schema_from_aliases(
        config["outputs"]["source_long"]["stata_aliases"],
        bool_fields=bool_fields,
        int8_fields={"metric_order"},
        int16_fields={"year"},
        int32_fields=set(),
        float_fields={"value", "sector_mapping_weight"},
    )


def analysis_long_schema(config: dict[str, Any]) -> pa.Schema:
    bool_fields = {
        "value_available_flag",
        "disclosed_value_available_flag",
        "full_sector_coverage_flag",
        "suppressed_flag",
        "partial_disclosure_flag",
        "all_components_suppressed_flag",
        "small_value_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "observed_negative_flag",
        "reported_zero_flag",
        "exact_zero_flag",
        "zero_with_small_value_flag",
        "cancellation_to_zero_flag",
        "disclosed_value_negative_flag",
        "disclosed_value_zero_flag",
        "metric_additive_across_source_industries",
        "can_sum_across_years",
        "can_sum_across_metrics",
        "analysis_sector_is_direct_from_one_source_industry",
        "analysis_sector_aggregates_multiple_source_industries",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
    }
    count_fields = {
        "expected_source_industry_count",
        "source_industry_count",
        "source_disclosed_industry_count",
        "source_suppressed_cell_count",
        "source_small_value_cell_count",
        "source_missing_cell_count",
        "source_negative_cell_count",
        "source_reported_zero_cell_count",
        "source_exact_zero_cell_count",
    }
    return schema_from_aliases(
        config["outputs"]["analysis_long"]["stata_aliases"],
        bool_fields=bool_fields,
        int8_fields={"metric_order"},
        int16_fields={"year"},
        int32_fields=count_fields,
        float_fields={"value", "source_disclosed_value_sum"},
    )


def alias_validation(schema: pa.Schema, aliases: dict[str, str]) -> dict[str, Any]:
    fields = schema.names
    missing = sorted(set(fields) - set(aliases))
    extra = sorted(set(aliases) - set(fields))
    values = list(aliases.values())
    duplicate = sorted({value for value in values if values.count(value) > 1})
    over = {name: alias for name, alias in aliases.items() if len(alias) > 32}
    invalid = {
        name: alias
        for name, alias in aliases.items()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias) is None
    }
    return {
        "pass": not missing and not extra and not duplicate and not over and not invalid,
        "alias_count": len(aliases),
        "maximum_alias_length": max((len(value) for value in values), default=0),
        "missing_fields": missing,
        "extra_fields": extra,
        "duplicate_aliases": duplicate,
        "over_32_characters": over,
        "invalid_aliases": invalid,
    }


def write_parquet(frame: pd.DataFrame, path: Path, schema: pa.Schema) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = frame.loc[:, schema.names].copy()
    table = pa.Table.from_pandas(frame, schema=schema, preserve_index=False, safe=True)
    pq.write_table(
        table,
        path,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
    )
    return table


def read_inputs(project_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    specs = config["inputs"]
    fdi = pd.read_parquet(project_root / specs["bea_fdi"]["path"])
    countries = pd.read_parquet(project_root / specs["country_crosswalk"]["path"])
    sectors = pd.read_parquet(project_root / specs["source_sector_crosswalk"]["path"])
    time_rules = pd.read_parquet(project_root / specs["time_aggregation_rules"]["path"])
    with (project_root / specs["build_summary"]["path"]).open(
        "r", encoding="utf-8"
    ) as handle:
        build_summary = json.load(handle)
    with (project_root / specs["raw_manifest"]["path"]).open(
        "r", encoding="utf-8"
    ) as handle:
        raw_manifest = json.load(handle)
    return {
        "fdi": fdi,
        "countries": countries,
        "sectors": sectors,
        "time_rules": time_rules,
        "build_summary": build_summary,
        "raw_manifest": raw_manifest,
    }


def input_contract(
    project_root: Path, config: dict[str, Any], inputs: dict[str, Any]
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    frame_names = {
        "bea_fdi": "fdi",
        "country_crosswalk": "countries",
        "source_sector_crosswalk": "sectors",
        "time_aggregation_rules": "time_rules",
    }
    for spec_name, frame_name in frame_names.items():
        spec = config["inputs"][spec_name]
        path = project_root / spec["path"]
        table = pq.read_table(path)
        frame = inputs[frame_name]
        filtered = frame
        if "filter_source_name" in spec:
            filtered = frame.loc[frame["source_name"].eq(spec["filter_source_name"])]
        if "filter_input_id" in spec:
            filtered = frame.loc[frame["input_id"].eq(spec["filter_input_id"])]
        key = list(spec["natural_key"])
        results[spec_name] = {
            "path": spec["path"],
            "sha256": sha256(path),
            "sha256_expected": spec["sha256"],
            "rows": table.num_rows,
            "rows_expected": spec["expected_rows"],
            "columns": table.num_columns,
            "columns_expected": spec["expected_columns"],
            "schema_signature": schema_signature(table.schema),
            "schema_signature_expected": spec["arrow_schema_signature_sha256"],
            "filtered_rows": len(filtered),
            "filtered_rows_expected": spec.get("expected_filtered_rows", len(frame)),
            "key": key,
            "key_duplicate_count": int(filtered.duplicated(key).sum()),
            "key_missing_count": int(filtered[key].isna().any(axis=1).sum()),
        }
    for spec_name in ("build_summary", "raw_manifest"):
        spec = config["inputs"][spec_name]
        path = project_root / spec["path"]
        results[spec_name] = {
            "path": spec["path"],
            "sha256": sha256(path),
            "sha256_expected": spec["sha256"],
        }
    return results


def prepare_base(inputs: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    fdi = inputs["fdi"].copy()
    country_spec = config["inputs"]["country_crosswalk"]
    sector_spec = config["inputs"]["source_sector_crosswalk"]
    countries = inputs["countries"].loc[
        inputs["countries"]["source_name"].eq(country_spec["filter_source_name"])
    ].copy()
    sectors = inputs["sectors"].loc[
        inputs["sectors"]["source_name"].eq(sector_spec["filter_source_name"])
    ].copy()

    country_columns = [
        "source_country_id",
        "source_country_name",
        "country_iso3",
        "country_iso2",
        "canonical_country_name",
        "mapping_status",
        "mapping_method",
        "is_country",
        "is_aggregate",
        "is_residual",
        "is_proxy",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
    ]
    base = fdi.merge(
        countries[country_columns],
        how="left",
        left_on="country",
        right_on="source_country_id",
        validate="many_to_one",
        indicator="_country_join",
    )
    if not base["_country_join"].eq("both").all():
        missing = sorted(base.loc[base["_country_join"].ne("both"), "country"].unique())
        raise ValueError(f"Unmatched BEA FDI geography labels: {missing}")

    sector_columns = [
        "source_sector_level",
        "source_sector_code",
        "source_sector_label",
        "analysis_sector",
        "mapping_status",
        "mapping_rule",
        "first_round_exclusion",
        "proxy_analysis_sector",
        "is_main_join_eligible",
        "mapping_weight",
        "source_granularity_note",
        "source_code_family",
        "mapping_version",
    ]
    sectors = sectors[sector_columns].rename(
        columns={
            "mapping_status": "sector_mapping_status",
            "mapping_rule": "sector_mapping_rule",
            "first_round_exclusion": "sector_first_round_exclusion",
            "proxy_analysis_sector": "sector_proxy_analysis_sector",
            "is_main_join_eligible": "sector_is_main_join_eligible",
            "mapping_weight": "sector_mapping_weight",
            "mapping_version": "source_sector_mapping_version",
        }
    )
    base = base.merge(
        sectors,
        how="left",
        left_on="industry",
        right_on="source_sector_label",
        validate="many_to_one",
        indicator="_sector_join",
    )
    if not base["_sector_join"].eq("both").all():
        missing = sorted(base.loc[base["_sector_join"].ne("both"), "industry"].unique())
        raise ValueError(f"Unmatched BEA FDI industries: {missing}")

    base = base.rename(
        columns={
            "direction": "investment_direction",
            "mapping_status": "country_mapping_status",
            "mapping_method": "country_mapping_method",
            "bea_area_type": "source_bea_area_type",
            "bea_parent_area": "source_bea_parent_area",
        }
    )
    base["source_name"] = config["source_name"]
    base["source_country_name"] = base["source_country_name"].fillna(base["country"])
    base["model_sector"] = base["industry"].astype("string")
    base["country_area_override_flag"] = (
        base["source_bea_area_type"].ne("aggregate") & base["is_aggregate"].fillna(False)
    )
    base["country_is_country"] = base["is_country"].fillna(False).astype(bool)
    base["country_is_aggregate"] = base["is_aggregate"].fillna(False).astype(bool)
    base["country_is_residual"] = base["is_residual"].fillna(False).astype(bool)
    base["country_is_proxy"] = base["is_proxy"].fillna(False).astype(bool)
    base["main_analysis_country_flag"] = (
        base["country_is_country"] & base["country_iso3"].notna()
    )
    for field in ("is_core_connector", "is_asian_comparator", "is_other_candidate"):
        base[field] = base[field].fillna(False).astype(bool)
    base["comparison_sample_country_flag"] = base[
        ["is_core_connector", "is_asian_comparator", "is_other_candidate"]
    ].any(axis=1)

    direction_rules = config["directions"]
    unknown_directions = sorted(set(base["investment_direction"]) - set(direction_rules))
    if unknown_directions:
        raise ValueError(f"Unexpected investment directions: {unknown_directions}")
    base["foreign_country_role"] = base["investment_direction"].map(
        {name: rule["foreign_country_role"] for name, rule in direction_rules.items()}
    )
    base["direction_sign_convention"] = base["investment_direction"].map(
        {name: rule["flow_sign_convention"] for name, rule in direction_rules.items()}
    )
    outward = base["investment_direction"].eq("us_direct_investment_abroad")
    base["origin_country_iso3"] = np.where(outward, "USA", base["country_iso3"])
    base["destination_country_iso3"] = np.where(outward, base["country_iso3"], "USA")
    base.loc[base["country_iso3"].isna(), ["origin_country_iso3", "destination_country_iso3"]] = pd.NA

    base["sector_is_main_join_eligible"] = (
        base["sector_is_main_join_eligible"].fillna(False).astype(bool)
    )
    base["aggregate_sector_flag"] = base["model_sector"].isin(
        config["source_rules"]["aggregate_sector_codes"]
    )
    base["residual_flag"] = base["country_is_residual"] | base["model_sector"].isin(
        config["source_rules"]["residual_sector_codes"]
    )
    base["proxy_flag"] = base["sector_proxy_analysis_sector"].notna()
    base["main_analysis_join_eligible"] = (
        base["main_analysis_country_flag"] & base["sector_is_main_join_eligible"]
    )
    return base.sort_values(
        ["investment_direction", "country", "industry", "year"], kind="mergesort"
    ).reset_index(drop=True)


def build_source_long(
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    project_root: Path,
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    common = [
        "year",
        "source_name",
        "source_country_id",
        "source_country_name",
        "country_iso3",
        "country_iso2",
        "canonical_country_name",
        "country_mapping_status",
        "country_mapping_method",
        "source_bea_area_type",
        "source_bea_parent_area",
        "country_area_override_flag",
        "country_is_country",
        "country_is_aggregate",
        "country_is_residual",
        "country_is_proxy",
        "main_analysis_country_flag",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
        "investment_direction",
        "foreign_country_role",
        "origin_country_iso3",
        "destination_country_iso3",
        "direction_sign_convention",
        "model_sector",
        "source_sector_level",
        "source_sector_label",
        "analysis_sector",
        "sector_mapping_status",
        "sector_mapping_rule",
        "sector_first_round_exclusion",
        "sector_proxy_analysis_sector",
        "sector_is_main_join_eligible",
        "sector_mapping_weight",
        "source_granularity_note",
        "source_code_family",
        "source_sector_mapping_version",
        "aggregate_sector_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
    ]
    for metric_name, rule in config["metrics"].items():
        frame = base[common].copy()
        frame["metric_name"] = metric_name
        frame["metric_order"] = int(rule["order"])
        frame["temporal_type"] = rule["temporal_type"]
        frame["value"] = pd.to_numeric(base[rule["source_field"]], errors="coerce")
        frame["raw_code"] = base[rule["raw_code_field"]].astype("string")
        frame["unit"] = rule["unit"]
        frame["frequency"] = rule["frequency"]
        if rule["sign_convention"] == "direction_specific_flow_convention":
            frame["direction_sign_convention"] = base["direction_sign_convention"].astype("string")
        else:
            frame["direction_sign_convention"] = rule["sign_convention"]
        frame["direct_or_allocated"] = "direct"
        frame["derivation_status"] = "direct_source_industry_value"
        frame["metric_formula"] = rule["formula"]
        frame["metric_use"] = rule["use"]
        frame["value_available_flag"] = frame["value"].notna()
        frame["suppressed_flag"] = base[rule["suppressed_field"]].fillna(False).astype(bool)
        frame["small_value_flag"] = base[rule["small_value_field"]].fillna(False).astype(bool)
        frame["confidential_flag"] = False
        frame["aggregate_geography_flag"] = frame["country_is_aggregate"]
        frame["observed_negative_flag"] = frame["value"].lt(0)
        frame["reported_zero_flag"] = frame["value"].eq(0)
        frame["exact_zero_flag"] = (
            frame["reported_zero_flag"]
            & ~frame["small_value_flag"]
            & ~frame["suppressed_flag"]
        )
        frame["metric_additive_across_source_industries"] = ~(
            frame["aggregate_sector_flag"] | frame["residual_flag"]
        )
        frame["can_sum_across_years"] = bool(rule["can_sum_across_years"])
        frame["can_sum_across_metrics"] = False
        frame["source_file"] = base[rule["source_file_field"]].map(
            lambda value: normalize_source_file(value, project_root)
        )
        frame["source_url"] = base[rule["source_url_field"]].astype("string")
        frame["release_vintage"] = base["release_vintage"].astype("string")
        frame["download_date"] = base["download_date"].astype("string")
        frame["source_page"] = base["source_page"].astype("string")
        frame["m4_bea_fdi_version"] = config["construction_version"]
        frame["rules_config_sha256"] = config_hash
        frame["schema_version"] = config["outputs"]["source_long"]["schema_version"]
        frames.append(frame)
    output = pd.concat(frames, ignore_index=True)
    return output.sort_values(SOURCE_LONG_KEY, kind="mergesort").reset_index(drop=True)


def analysis_components(base: pd.DataFrame) -> pd.DataFrame:
    main = base.loc[base["main_analysis_join_eligible"]].copy()
    main["resolved_analysis_sector"] = main["analysis_sector"].astype("string")
    main["analysis_scope"] = "main"
    proxy = base.loc[
        base["main_analysis_country_flag"] & base["sector_proxy_analysis_sector"].notna()
    ].copy()
    proxy["resolved_analysis_sector"] = proxy["sector_proxy_analysis_sector"].astype("string")
    proxy["analysis_scope"] = "proxy_robustness"
    return pd.concat([main, proxy], ignore_index=True)


def expected_industry_counts(config: dict[str, Any]) -> dict[str, int]:
    return {
        sector: len(spec["source_industries"])
        for sector, spec in config["analysis_sector_components"].items()
    }


def build_analysis_long(
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    project_root: Path,
) -> pd.DataFrame:
    components = analysis_components(base)
    expected_counts = expected_industry_counts(config)
    group_key = [
        "country_iso3",
        "investment_direction",
        "year",
        "resolved_analysis_sector",
        "analysis_scope",
    ]
    frames: list[pd.DataFrame] = []
    for metric_name, rule in config["metrics"].items():
        work = components.copy()
        work["component_value"] = pd.to_numeric(work[rule["source_field"]], errors="coerce")
        work["component_suppressed"] = work[rule["suppressed_field"]].fillna(False).astype(bool)
        work["component_small"] = work[rule["small_value_field"]].fillna(False).astype(bool)
        work["component_negative"] = work["component_value"].lt(0)
        work["component_reported_zero"] = work["component_value"].eq(0)
        work["component_exact_zero"] = (
            work["component_reported_zero"]
            & ~work["component_small"]
            & ~work["component_suppressed"]
        )
        work["component_missing"] = work["component_value"].isna()
        work["component_source_file"] = work[rule["source_file_field"]].map(
            lambda value: normalize_source_file(value, project_root)
        )
        work["component_source_url"] = work[rule["source_url_field"]].astype("string")

        grouped = work.groupby(group_key, sort=True, dropna=False)
        frame = grouped.agg(
            source_country_id=("source_country_id", "first"),
            canonical_country_name=("canonical_country_name", "first"),
            foreign_country_role=("foreign_country_role", "first"),
            origin_country_iso3=("origin_country_iso3", "first"),
            destination_country_iso3=("destination_country_iso3", "first"),
            source_disclosed_value_sum=(
                "component_value",
                lambda values: values.sum(min_count=1),
            ),
            source_industry_count=("model_sector", "size"),
            source_disclosed_industry_count=("component_value", lambda values: int(values.notna().sum())),
            source_suppressed_cell_count=("component_suppressed", "sum"),
            source_small_value_cell_count=("component_small", "sum"),
            source_missing_cell_count=("component_missing", "sum"),
            source_negative_cell_count=("component_negative", "sum"),
            source_reported_zero_cell_count=("component_reported_zero", "sum"),
            source_exact_zero_cell_count=("component_exact_zero", "sum"),
            source_industry_codes=("source_sector_code", join_unique_text),
            source_industry_labels=("source_sector_label", join_unique_text),
            source_mapping_statuses=("sector_mapping_status", join_unique_text),
            source_mapping_rules=("sector_mapping_rule", join_unique_text),
            source_granularity_note=("source_granularity_note", join_unique_text),
            source_sector_mapping_version=("source_sector_mapping_version", join_unique_text),
            is_core_connector=("is_core_connector", "first"),
            is_asian_comparator=("is_asian_comparator", "first"),
            is_other_candidate=("is_other_candidate", "first"),
            comparison_sample_country_flag=("comparison_sample_country_flag", "first"),
            source_file=("component_source_file", join_unique_text),
            source_url=("component_source_url", join_unique_text),
            release_vintage=("release_vintage", join_unique_text),
        ).reset_index()
        frame = frame.rename(columns={"resolved_analysis_sector": "analysis_sector"})
        frame["expected_source_industry_count"] = (
            frame["analysis_sector"].map(expected_counts).astype("int32")
        )
        frame["full_sector_coverage_flag"] = (
            frame["source_industry_count"].eq(frame["expected_source_industry_count"])
            & frame["source_missing_cell_count"].eq(0)
        )
        frame["value"] = frame["source_disclosed_value_sum"].where(
            frame["full_sector_coverage_flag"]
        )
        frame["metric_name"] = metric_name
        frame["metric_order"] = int(rule["order"])
        frame["temporal_type"] = rule["temporal_type"]
        frame["unit"] = rule["unit"]
        frame["frequency"] = rule["frequency"]
        if rule["sign_convention"] == "direction_specific_flow_convention":
            frame["direction_sign_convention"] = frame["investment_direction"].map(
                {
                    name: direction_rule["flow_sign_convention"]
                    for name, direction_rule in config["directions"].items()
                }
            )
        else:
            frame["direction_sign_convention"] = rule["sign_convention"]
        frame["direct_or_allocated"] = "direct"
        frame["analysis_sector_is_direct_from_one_source_industry"] = frame[
            "expected_source_industry_count"
        ].eq(1)
        frame["analysis_sector_aggregates_multiple_source_industries"] = frame[
            "expected_source_industry_count"
        ].gt(1)
        frame["derivation_status"] = np.where(
            frame["analysis_sector_is_direct_from_one_source_industry"],
            "direct_one_source_industry",
            "strict_sum_multiple_source_industries",
        )
        frame["metric_formula"] = rule["formula"]
        frame["metric_use"] = rule["use"]
        frame["value_available_flag"] = frame["value"].notna()
        frame["disclosed_value_available_flag"] = frame["source_disclosed_value_sum"].notna()
        frame["suppressed_flag"] = frame["source_suppressed_cell_count"].gt(0)
        frame["partial_disclosure_flag"] = (
            frame["source_suppressed_cell_count"].gt(0)
            & frame["source_suppressed_cell_count"].lt(frame["expected_source_industry_count"])
        )
        frame["all_components_suppressed_flag"] = frame[
            "source_suppressed_cell_count"
        ].eq(frame["expected_source_industry_count"])
        frame["small_value_flag"] = frame["source_small_value_cell_count"].gt(0)
        frame["confidential_flag"] = False
        frame["aggregate_flag"] = False
        frame["residual_flag"] = False
        frame["proxy_flag"] = frame["analysis_scope"].eq("proxy_robustness")
        frame["main_analysis_join_eligible"] = frame["analysis_scope"].eq("main")
        frame["observed_negative_flag"] = frame["value"].lt(0)
        frame["reported_zero_flag"] = frame["value"].eq(0)
        frame["exact_zero_flag"] = (
            frame["full_sector_coverage_flag"]
            & frame["source_exact_zero_cell_count"].eq(frame["expected_source_industry_count"])
        )
        frame["zero_with_small_value_flag"] = (
            frame["reported_zero_flag"] & frame["small_value_flag"]
        )
        frame["cancellation_to_zero_flag"] = (
            frame["reported_zero_flag"]
            & ~frame["small_value_flag"]
            & ~frame["exact_zero_flag"]
        )
        frame["disclosed_value_negative_flag"] = frame["source_disclosed_value_sum"].lt(0)
        frame["disclosed_value_zero_flag"] = frame["source_disclosed_value_sum"].eq(0)
        frame["metric_additive_across_source_industries"] = True
        frame["can_sum_across_years"] = bool(rule["can_sum_across_years"])
        frame["can_sum_across_metrics"] = False
        frame["source_name"] = config["source_name"]
        frame["m4_bea_fdi_version"] = config["construction_version"]
        frame["rules_config_sha256"] = config_hash
        frame["schema_version"] = config["outputs"]["analysis_long"]["schema_version"]
        frames.append(frame)
    output = pd.concat(frames, ignore_index=True)
    return output.sort_values(ANALYSIS_LONG_KEY, kind="mergesort").reset_index(drop=True)


def build_once(
    project_root: Path,
    output_directory: Path,
    config: dict[str, Any],
    config_hash: str,
    inputs: dict[str, Any],
) -> dict[str, Any]:
    base = prepare_base(inputs, config)
    source = build_source_long(base, config, config_hash, project_root)
    analysis = build_analysis_long(base, config, config_hash, project_root)
    source_path = output_directory / Path(config["outputs"]["source_long"]["path"]).name
    analysis_path = output_directory / Path(config["outputs"]["analysis_long"]["path"]).name
    source_table = write_parquet(source, source_path, source_long_schema(config))
    analysis_table = write_parquet(analysis, analysis_path, analysis_long_schema(config))
    return {
        "base": base,
        "source": source,
        "analysis": analysis,
        "source_path": source_path,
        "analysis_path": analysis_path,
        "source_table": source_table,
        "analysis_table": analysis_table,
    }


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if value is pd.NA:
        return None
    return value


def add_check(
    validation: dict[str, Any], name: str, passed: bool, evidence: Any
) -> None:
    record = {"name": name, "pass": bool(passed), "evidence": jsonable(evidence)}
    validation["checks"].append(record)
    if not passed:
        validation["failures"].append(record)


def raw_manifest_audit(
    project_root: Path, manifest: dict[str, Any], expected_file_count: int
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for item in manifest.get("files", []):
        path = project_root / item["local_path"]
        exists = path.is_file()
        actual_bytes = path.stat().st_size if exists else None
        actual_hash = sha256(path) if exists else None
        records.append(
            {
                "direction": item.get("direction"),
                "indicator": item.get("indicator"),
                "local_path": item.get("local_path"),
                "exists": exists,
                "expected_bytes": item.get("bytes"),
                "actual_bytes": actual_bytes,
                "bytes_match": exists and actual_bytes == item.get("bytes"),
                "expected_sha256": item.get("sha256"),
                "actual_sha256": actual_hash,
                "sha256_match": exists and actual_hash == item.get("sha256"),
            }
        )
    return {
        "expected_file_count": expected_file_count,
        "manifest_file_count": len(manifest.get("files", [])),
        "all_files_exist": all(record["exists"] for record in records),
        "all_sizes_match": all(record["bytes_match"] for record in records),
        "all_hashes_match": all(record["sha256_match"] for record in records),
        "records": records,
    }


def source_metric_snapshot(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "missing": int(frame["value"].isna().sum()),
        "suppressed": int(frame["suppressed_flag"].sum()),
        "small": int(frame["small_value_flag"].sum()),
        "zero": int(frame["reported_zero_flag"].sum()),
        "exact_zero": int(frame["exact_zero_flag"].sum()),
        "negative": int(frame["observed_negative_flag"].sum()),
    }


def analysis_metric_snapshot(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "nonmissing": int(frame["value"].notna().sum()),
        "missing": int(frame["value"].isna().sum()),
        "small": int(frame["small_value_flag"].sum()),
        "zero": int(frame["reported_zero_flag"].sum()),
        "exact_zero": int(frame["exact_zero_flag"].sum()),
        "zero_with_small": int(frame["zero_with_small_value_flag"].sum()),
        "cancellation_zero": int(frame["cancellation_to_zero_flag"].sum()),
        "negative": int(frame["observed_negative_flag"].sum()),
        "partial_suppression": int(frame["partial_disclosure_flag"].sum()),
        "all_suppressed": int(frame["all_components_suppressed_flag"].sum()),
        "disclosed_negative": int(frame["disclosed_value_negative_flag"].sum()),
        "disclosed_zero": int(frame["disclosed_value_zero_flag"].sum()),
    }


def recompute_analysis_from_source(
    source: pd.DataFrame, config: dict[str, Any]
) -> pd.DataFrame:
    main = source.loc[
        source["main_analysis_country_flag"] & source["sector_is_main_join_eligible"]
    ].copy()
    main["resolved_analysis_sector"] = main["analysis_sector"].astype("string")
    main["analysis_scope"] = "main"
    proxy = source.loc[
        source["main_analysis_country_flag"]
        & source["sector_proxy_analysis_sector"].notna()
    ].copy()
    proxy["resolved_analysis_sector"] = proxy["sector_proxy_analysis_sector"].astype("string")
    proxy["analysis_scope"] = "proxy_robustness"
    work = pd.concat([main, proxy], ignore_index=True)
    expected_counts = expected_industry_counts(config)
    key = [
        "country_iso3",
        "investment_direction",
        "resolved_analysis_sector",
        "year",
        "source_name",
        "metric_name",
        "analysis_scope",
    ]
    grouped = work.groupby(key, sort=True, dropna=False)
    out = grouped.agg(
        recomputed_disclosed_value=("value", lambda values: values.sum(min_count=1)),
        recomputed_source_industry_count=("model_sector", "size"),
        recomputed_disclosed_count=("value", lambda values: int(values.notna().sum())),
        recomputed_suppressed_count=("suppressed_flag", "sum"),
        recomputed_small_count=("small_value_flag", "sum"),
        recomputed_missing_count=("value", lambda values: int(values.isna().sum())),
        recomputed_negative_count=("observed_negative_flag", "sum"),
        recomputed_zero_count=("reported_zero_flag", "sum"),
        recomputed_exact_zero_count=("exact_zero_flag", "sum"),
        recomputed_source_industries=("model_sector", join_unique_text),
    ).reset_index()
    out = out.rename(columns={"resolved_analysis_sector": "analysis_sector"})
    out["recomputed_expected_count"] = out["analysis_sector"].map(expected_counts).astype("int32")
    out["recomputed_full_coverage"] = (
        out["recomputed_source_industry_count"].eq(out["recomputed_expected_count"])
        & out["recomputed_missing_count"].eq(0)
    )
    out["recomputed_value"] = out["recomputed_disclosed_value"].where(
        out["recomputed_full_coverage"]
    )
    out["recomputed_suppressed_flag"] = out["recomputed_suppressed_count"].gt(0)
    out["recomputed_partial_flag"] = (
        out["recomputed_suppressed_count"].gt(0)
        & out["recomputed_suppressed_count"].lt(out["recomputed_expected_count"])
    )
    out["recomputed_all_suppressed_flag"] = out["recomputed_suppressed_count"].eq(
        out["recomputed_expected_count"]
    )
    out["recomputed_small_flag"] = out["recomputed_small_count"].gt(0)
    out["recomputed_negative_flag"] = out["recomputed_value"].lt(0)
    out["recomputed_reported_zero_flag"] = out["recomputed_value"].eq(0)
    out["recomputed_exact_zero_flag"] = (
        out["recomputed_full_coverage"]
        & out["recomputed_exact_zero_count"].eq(out["recomputed_expected_count"])
    )
    out["recomputed_zero_with_small_flag"] = (
        out["recomputed_reported_zero_flag"] & out["recomputed_small_flag"]
    )
    out["recomputed_cancellation_zero_flag"] = (
        out["recomputed_reported_zero_flag"]
        & ~out["recomputed_small_flag"]
        & ~out["recomputed_exact_zero_flag"]
    )
    return out


def numeric_equal(left: pd.Series, right: pd.Series, tolerance: float) -> tuple[bool, float]:
    missing_match = left.isna().eq(right.isna()).all()
    both = left.notna() & right.notna()
    error = max_abs(left.loc[both].to_numpy() - right.loc[both].to_numpy()) if both.any() else 0.0
    return bool(missing_match and error <= tolerance), error


def validate_candidate(
    project_root: Path,
    config_path: Path,
    config: dict[str, Any],
    config_hash: str,
    inputs: dict[str, Any],
    built: dict[str, Any],
) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "validation_status": "PENDING",
        "failures": [],
        "checks": [],
        "validation_version": "production_bea_fdi_validation_v1",
        "origin_date": config["origin_date"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path.relative_to(project_root).as_posix(),
        "config_sha256": config_hash,
        "construction_version": config["construction_version"],
    }
    tolerance = float(config["validation"]["numeric_tolerance"])
    contracts = input_contract(project_root, config, inputs)
    validation["input_contracts"] = contracts
    for name, contract in contracts.items():
        add_check(
            validation,
            f"input_{name}_sha256",
            contract["sha256"] == contract["sha256_expected"],
            {"actual": contract["sha256"], "expected": contract["sha256_expected"]},
        )
        if "rows" in contract:
            add_check(
                validation,
                f"input_{name}_shape",
                contract["rows"] == contract["rows_expected"]
                and contract["columns"] == contract["columns_expected"],
                contract,
            )
            add_check(
                validation,
                f"input_{name}_schema_signature",
                contract["schema_signature"] == contract["schema_signature_expected"],
                contract,
            )
            add_check(
                validation,
                f"input_{name}_key",
                contract["key_duplicate_count"] == 0
                and contract["key_missing_count"] == 0,
                contract,
            )
            add_check(
                validation,
                f"input_{name}_filtered_rows",
                contract["filtered_rows"] == contract["filtered_rows_expected"],
                contract,
            )

    raw_audit = raw_manifest_audit(
        project_root,
        inputs["raw_manifest"],
        int(config["inputs"]["raw_manifest"]["expected_file_count"]),
    )
    validation["raw_manifest_audit"] = raw_audit
    add_check(
        validation,
        "raw_manifest_file_count",
        raw_audit["manifest_file_count"] == raw_audit["expected_file_count"],
        raw_audit,
    )
    add_check(
        validation,
        "raw_manifest_files_exist",
        raw_audit["all_files_exist"],
        raw_audit,
    )
    add_check(
        validation,
        "raw_manifest_sizes_match",
        raw_audit["all_sizes_match"],
        raw_audit,
    )
    add_check(
        validation,
        "raw_manifest_hashes_match",
        raw_audit["all_hashes_match"],
        raw_audit,
    )

    fdi = inputs["fdi"]
    base = built["base"]
    source = built["source"]
    analysis = built["analysis"]
    expected_years = list(config["source_rules"]["years"])
    add_check(
        validation,
        "input_years",
        sorted(fdi["year"].unique().tolist()) == expected_years,
        sorted(fdi["year"].unique().tolist()),
    )
    add_check(
        validation,
        "input_no_position_only_2025",
        int(fdi["year"].max()) == 2024 and not fdi["year"].eq(2025).any(),
        {"min": int(fdi["year"].min()), "max": int(fdi["year"].max())},
    )
    add_check(
        validation,
        "input_rows_per_year",
        fdi.groupby("year").size().to_dict() == {year: 2322 for year in expected_years},
        fdi.groupby("year").size().to_dict(),
    )
    expected_direction_rows = {
        "us_direct_investment_abroad": 6660,
        "foreign_direct_investment_in_us": 4950,
    }
    add_check(
        validation,
        "input_direction_rows",
        fdi["direction"].value_counts().to_dict() == expected_direction_rows,
        fdi["direction"].value_counts().to_dict(),
    )
    direction_industries = fdi.groupby("direction")["industry"].nunique().to_dict()
    add_check(
        validation,
        "input_direction_industry_counts",
        direction_industries == {name: 18 for name in expected_direction_rows},
        direction_industries,
    )

    geography = {
        "source_geography_labels": int(fdi["country"].nunique()),
        "source_area_aggregate_rows": int(fdi["bea_area_type"].eq("aggregate").sum()),
        "country_override_aggregate_rows": int(base["country_area_override_flag"].sum()),
        "final_aggregate_rows": int(base["country_is_aggregate"].sum()),
        "actual_country_rows": int(base["main_analysis_country_flag"].sum()),
        "actual_country_count": int(base.loc[base["main_analysis_country_flag"], "country_iso3"].nunique()),
        "country_direction_year_cells": int(
            base.loc[base["main_analysis_country_flag"], ["country_iso3", "investment_direction", "year"]]
            .drop_duplicates()
            .shape[0]
        ),
    }
    validation["geography_and_mapping"] = geography
    for key in (
        "source_geography_labels",
        "source_area_aggregate_rows",
        "country_override_aggregate_rows",
        "final_aggregate_rows",
        "actual_country_rows",
        "actual_country_count",
        "country_direction_year_cells",
    ):
        expected_key = f"expected_{key}"
        add_check(
            validation,
            f"geography_{key}",
            geography[key] == int(config["validation"][expected_key]),
            {"actual": geography[key], "expected": config["validation"][expected_key]},
        )
    add_check(
        validation,
        "source_industry_labels",
        int(fdi["industry"].nunique()) == int(config["validation"]["expected_source_industries"]),
        int(fdi["industry"].nunique()),
    )
    direction_country_counts = (
        base.loc[base["main_analysis_country_flag"]]
        .groupby("investment_direction")["country_iso3"]
        .nunique()
        .to_dict()
    )
    add_check(
        validation,
        "direction_country_counts",
        direction_country_counts == config["validation"]["expected_direction_country_counts"],
        direction_country_counts,
    )

    time_spec = config["inputs"]["time_aggregation_rules"]
    time_rules = inputs["time_rules"].loc[
        inputs["time_rules"]["input_id"].eq(time_spec["filter_input_id"])
    ].set_index("metric_name")
    time_expected = {
        "position": ("end_period_stock", "never_sum_positions_across_time"),
        "flows": ("annual_flow", "do_not_sum_across_years"),
        "income": ("annual_flow", "do_not_sum_across_years"),
    }
    for metric, (semantics, prohibited) in time_expected.items():
        row = time_rules.loc[metric]
        passed = (
            row["temporal_semantics"] == semantics
            and row["prohibited_operation"] == prohibited
            and config["metrics"][metric]["temporal_type"] == semantics
            and not bool(config["metrics"][metric]["can_sum_across_years"])
        )
        add_check(
            validation,
            f"time_rule_{metric}",
            passed,
            {
                "temporal_semantics": row["temporal_semantics"],
                "prohibited_operation": row["prohibited_operation"],
                "config_can_sum_across_years": config["metrics"][metric]["can_sum_across_years"],
            },
        )

    source_spec = config["outputs"]["source_long"]
    add_check(
        validation,
        "source_output_shape",
        len(source) == int(source_spec["expected_rows"])
        and len(source.columns) == int(source_spec["expected_columns"]),
        {"rows": len(source), "columns": len(source.columns)},
    )
    add_check(
        validation,
        "source_output_key",
        int(source.duplicated(SOURCE_LONG_KEY).sum()) == 0
        and int(source[SOURCE_LONG_KEY].isna().any(axis=1).sum()) == 0,
        {
            "duplicates": int(source.duplicated(SOURCE_LONG_KEY).sum()),
            "missing": int(source[SOURCE_LONG_KEY].isna().any(axis=1).sum()),
        },
    )
    add_check(
        validation,
        "source_metric_grid",
        source.groupby(SOURCE_LONG_KEY[:-1])["metric_name"].nunique().eq(3).all(),
        source["metric_name"].value_counts().to_dict(),
    )
    add_check(
        validation,
        "source_actual_and_aggregate_rows",
        int((~source["aggregate_geography_flag"]).sum()) == 25650
        and int(source["aggregate_geography_flag"].sum()) == 9180
        and int(source["country_area_override_flag"].sum()) == 1350,
        {
            "actual_metric_rows": int((~source["aggregate_geography_flag"]).sum()),
            "aggregate_metric_rows": int(source["aggregate_geography_flag"].sum()),
            "override_metric_rows": int(source["country_area_override_flag"].sum()),
        },
    )
    source_direction_rows = source["investment_direction"].value_counts().to_dict()
    add_check(
        validation,
        "source_direction_rows",
        source_direction_rows
        == {
            "us_direct_investment_abroad": 19980,
            "foreign_direct_investment_in_us": 14850,
        },
        source_direction_rows,
    )
    add_check(
        validation,
        "source_proxy_rows",
        int(source["proxy_flag"].sum())
        == int(config["validation"]["expected_full_source_proxy_rows"]) * 3,
        int(source["proxy_flag"].sum()),
    )
    add_check(
        validation,
        "source_paths_project_relative",
        not source["source_file"].astype("string").str.match(r"^[A-Za-z]:[/\\]").fillna(False).any(),
        sorted(source["source_file"].dropna().unique().tolist()),
    )
    manifest_paths = {item["local_path"].replace("\\", "/") for item in inputs["raw_manifest"]["files"]}
    source_paths = set(source["source_file"].dropna().astype(str))
    add_check(
        validation,
        "source_files_match_manifest",
        source_paths == manifest_paths,
        {"source_paths": sorted(source_paths), "manifest_paths": sorted(manifest_paths)},
    )
    add_check(
        validation,
        "source_suppressed_missing_identity",
        source["suppressed_flag"].eq(source["value"].isna()).all(),
        int(source["suppressed_flag"].ne(source["value"].isna()).sum()),
    )
    add_check(
        validation,
        "source_small_values_are_zero",
        source.loc[source["small_value_flag"], "value"].eq(0).all(),
        int(source["small_value_flag"].sum()),
    )
    add_check(
        validation,
        "source_no_infinite_values",
        np.isfinite(source.loc[source["value"].notna(), "value"]).all(),
        int((~np.isfinite(source.loc[source["value"].notna(), "value"])).sum()),
    )
    source_snapshots: dict[str, Any] = {}
    for metric_name, expected in config["validation"]["expected_source_metric_counts"].items():
        metric_frame = source.loc[source["metric_name"].eq(metric_name)]
        snapshot = source_metric_snapshot(metric_frame)
        source_snapshots[metric_name] = snapshot
        add_check(
            validation,
            f"source_metric_snapshot_{metric_name}",
            snapshot == expected,
            {"actual": snapshot, "expected": expected},
        )
    validation["source_metric_checks"] = source_snapshots

    identity_checks: dict[str, Any] = {}
    for metric_name, rule in config["metrics"].items():
        actual = source.loc[source["metric_name"].eq(metric_name)].copy()
        expected = fdi[
            SOURCE_KEY
            + [
                rule["source_field"],
                rule["raw_code_field"],
                rule["suppressed_field"],
                rule["small_value_field"],
                rule["source_file_field"],
                rule["source_url_field"],
            ]
        ].copy()
        expected = expected.rename(
            columns={
                "direction": "investment_direction",
                "country": "source_country_id",
                "industry": "model_sector",
                rule["source_field"]: "expected_value",
                rule["raw_code_field"]: "expected_raw_code",
                rule["suppressed_field"]: "expected_suppressed",
                rule["small_value_field"]: "expected_small",
                rule["source_file_field"]: "expected_source_file",
                rule["source_url_field"]: "expected_source_url",
            }
        )
        expected["expected_source_file"] = expected["expected_source_file"].map(
            lambda value: normalize_source_file(value, project_root)
        )
        merged = actual.merge(
            expected,
            on=["year", "investment_direction", "source_country_id", "model_sector"],
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        value_ok, value_error = numeric_equal(merged["value"], merged["expected_value"], tolerance)
        raw_ok = merged["raw_code"].fillna("<NA>").eq(merged["expected_raw_code"].fillna("<NA>")).all()
        flag_ok = (
            merged["suppressed_flag"].eq(merged["expected_suppressed"]).all()
            and merged["small_value_flag"].eq(merged["expected_small"]).all()
        )
        provenance_ok = (
            merged["source_file"].fillna("<NA>").eq(merged["expected_source_file"].fillna("<NA>")).all()
            and merged["source_url"].fillna("<NA>").eq(merged["expected_source_url"].fillna("<NA>")).all()
        )
        identity_checks[metric_name] = {
            "merge_counts": merged["_merge"].value_counts().to_dict(),
            "value_max_abs_error": value_error,
            "raw_code_match": bool(raw_ok),
            "flags_match": bool(flag_ok),
            "provenance_match": bool(provenance_ok),
        }
        add_check(
            validation,
            f"source_identity_{metric_name}",
            merged["_merge"].eq("both").all()
            and value_ok
            and raw_ok
            and flag_ok
            and provenance_ok,
            identity_checks[metric_name],
        )
    validation["source_identity_checks"] = identity_checks

    mapped_negative: dict[str, int] = {}
    mapped_source = source.loc[
        source["main_analysis_country_flag"]
        & (source["sector_is_main_join_eligible"] | source["proxy_flag"])
    ]
    for metric_name in config["metrics"]:
        mapped_negative[metric_name] = int(
            mapped_source.loc[mapped_source["metric_name"].eq(metric_name), "observed_negative_flag"].sum()
        )
    add_check(
        validation,
        "actual_mapped_source_negative_counts",
        mapped_negative == config["validation"]["expected_actual_mapped_source_negative_counts"],
        mapped_negative,
    )

    analysis_spec = config["outputs"]["analysis_long"]
    add_check(
        validation,
        "analysis_output_shape",
        len(analysis) == int(analysis_spec["expected_rows"])
        and len(analysis.columns) == int(analysis_spec["expected_columns"]),
        {"rows": len(analysis), "columns": len(analysis.columns)},
    )
    add_check(
        validation,
        "analysis_output_key",
        int(analysis.duplicated(ANALYSIS_LONG_KEY).sum()) == 0
        and int(analysis[ANALYSIS_LONG_KEY].isna().any(axis=1).sum()) == 0,
        {
            "duplicates": int(analysis.duplicated(ANALYSIS_LONG_KEY).sum()),
            "missing": int(analysis[ANALYSIS_LONG_KEY].isna().any(axis=1).sum()),
        },
    )
    analysis_cells = analysis[ANALYSIS_LONG_KEY[:-1]].drop_duplicates()
    add_check(
        validation,
        "analysis_cell_and_dimension_counts",
        len(analysis_cells) == int(analysis_spec["expected_country_direction_sector_year_cells"])
        and analysis["country_iso3"].nunique() == int(analysis_spec["expected_country_count"])
        and analysis["analysis_sector"].nunique() == int(analysis_spec["expected_analysis_sector_count"]),
        {
            "cells": len(analysis_cells),
            "countries": int(analysis["country_iso3"].nunique()),
            "sectors": int(analysis["analysis_sector"].nunique()),
        },
    )
    scope_counts = analysis["analysis_scope"].value_counts().to_dict()
    add_check(
        validation,
        "analysis_scope_counts",
        scope_counts
        == {
            "main": int(config["validation"]["expected_main_analysis_rows"]),
            "proxy_robustness": int(config["validation"]["expected_proxy_analysis_rows"]),
        },
        scope_counts,
    )
    add_check(
        validation,
        "analysis_scope_flags",
        analysis.loc[analysis["analysis_scope"].eq("main"), "main_analysis_join_eligible"].all()
        and not analysis.loc[analysis["analysis_scope"].eq("proxy_robustness"), "main_analysis_join_eligible"].any()
        and analysis.loc[analysis["analysis_scope"].eq("proxy_robustness"), "proxy_flag"].all(),
        {
            "main_join_false": int(
                (~analysis.loc[analysis["analysis_scope"].eq("main"), "main_analysis_join_eligible"]).sum()
            ),
            "proxy_join_true": int(
                analysis.loc[analysis["analysis_scope"].eq("proxy_robustness"), "main_analysis_join_eligible"].sum()
            ),
        },
    )
    add_check(
        validation,
        "analysis_no_aggregate_or_residual",
        not analysis["aggregate_flag"].any() and not analysis["residual_flag"].any(),
        {
            "aggregate": int(analysis["aggregate_flag"].sum()),
            "residual": int(analysis["residual_flag"].sum()),
        },
    )
    analysis_direction_rows = analysis["investment_direction"].value_counts().to_dict()
    add_check(
        validation,
        "analysis_direction_rows",
        analysis_direction_rows
        == {
            "us_direct_investment_abroad": 4200,
            "foreign_direct_investment_in_us": 2925,
        },
        analysis_direction_rows,
    )
    add_check(
        validation,
        "analysis_no_synthetic_sectors",
        not analysis["analysis_sector"].isin(config["source_rules"]["unsupported_analysis_sectors"]).any(),
        sorted(analysis["analysis_sector"].unique().tolist()),
    )
    add_check(
        validation,
        "analysis_component_counts_complete",
        analysis["source_industry_count"].eq(analysis["expected_source_industry_count"]).all(),
        analysis.groupby("analysis_sector")[["source_industry_count", "expected_source_industry_count"]]
        .first()
        .to_dict("index"),
    )
    component_sets: dict[str, Any] = {}
    component_sets_pass = True
    for sector, spec in config["analysis_sector_components"].items():
        actual_sets = set(
            analysis.loc[analysis["analysis_sector"].eq(sector), "source_industry_labels"].dropna().unique()
        )
        expected_text = " | ".join(sorted(spec["source_industries"]))
        component_sets[sector] = {"actual": sorted(actual_sets), "expected": expected_text}
        component_sets_pass = component_sets_pass and actual_sets == {expected_text}
    add_check(validation, "analysis_component_sets", component_sets_pass, component_sets)

    recomputed = recompute_analysis_from_source(source, config)
    compare = analysis.merge(
        recomputed,
        on=ANALYSIS_LONG_KEY + ["analysis_scope"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    value_ok, value_error = numeric_equal(compare["value"], compare["recomputed_value"], tolerance)
    disclosed_ok, disclosed_error = numeric_equal(
        compare["source_disclosed_value_sum"], compare["recomputed_disclosed_value"], tolerance
    )
    count_pairs = {
        "source_industry_count": "recomputed_source_industry_count",
        "source_disclosed_industry_count": "recomputed_disclosed_count",
        "source_suppressed_cell_count": "recomputed_suppressed_count",
        "source_small_value_cell_count": "recomputed_small_count",
        "source_missing_cell_count": "recomputed_missing_count",
        "source_negative_cell_count": "recomputed_negative_count",
        "source_reported_zero_cell_count": "recomputed_zero_count",
        "source_exact_zero_cell_count": "recomputed_exact_zero_count",
        "expected_source_industry_count": "recomputed_expected_count",
    }
    flag_pairs = {
        "full_sector_coverage_flag": "recomputed_full_coverage",
        "suppressed_flag": "recomputed_suppressed_flag",
        "partial_disclosure_flag": "recomputed_partial_flag",
        "all_components_suppressed_flag": "recomputed_all_suppressed_flag",
        "small_value_flag": "recomputed_small_flag",
        "observed_negative_flag": "recomputed_negative_flag",
        "reported_zero_flag": "recomputed_reported_zero_flag",
        "exact_zero_flag": "recomputed_exact_zero_flag",
        "zero_with_small_value_flag": "recomputed_zero_with_small_flag",
        "cancellation_to_zero_flag": "recomputed_cancellation_zero_flag",
    }
    counts_ok = all(compare[left].eq(compare[right]).all() for left, right in count_pairs.items())
    flags_ok = all(compare[left].eq(compare[right]).all() for left, right in flag_pairs.items())
    add_check(
        validation,
        "analysis_recomputed_from_source",
        compare["_merge"].eq("both").all()
        and value_ok
        and disclosed_ok
        and counts_ok
        and flags_ok,
        {
            "merge_counts": compare["_merge"].value_counts().to_dict(),
            "value_max_abs_error": value_error,
            "disclosed_value_max_abs_error": disclosed_error,
            "counts_match": counts_ok,
            "flags_match": flags_ok,
        },
    )

    analysis_snapshots: dict[str, Any] = {}
    for metric_name, expected in config["validation"]["expected_analysis_metric_counts"].items():
        metric_frame = analysis.loc[analysis["metric_name"].eq(metric_name)]
        snapshot = analysis_metric_snapshot(metric_frame)
        analysis_snapshots[metric_name] = snapshot
        add_check(
            validation,
            f"analysis_metric_snapshot_{metric_name}",
            snapshot == expected,
            {"actual": snapshot, "expected": expected},
        )
    validation["analysis_metric_checks"] = analysis_snapshots

    strict_negative: dict[str, dict[str, int]] = {}
    for scope in ("main", "proxy_robustness"):
        strict_negative[scope] = {}
        for metric_name in config["metrics"]:
            strict_negative[scope][metric_name] = int(
                analysis.loc[
                    analysis["analysis_scope"].eq(scope)
                    & analysis["metric_name"].eq(metric_name),
                    "observed_negative_flag",
                ].sum()
            )
    add_check(
        validation,
        "analysis_strict_negative_counts",
        strict_negative == config["validation"]["expected_strict_negative_counts"],
        strict_negative,
    )
    add_check(
        validation,
        "analysis_no_infinite_values",
        np.isfinite(analysis.loc[analysis["value"].notna(), "value"]).all()
        and np.isfinite(
            analysis.loc[analysis["source_disclosed_value_sum"].notna(), "source_disclosed_value_sum"]
        ).all(),
        {},
    )
    add_check(
        validation,
        "analysis_metrics_not_additive",
        not analysis["can_sum_across_metrics"].any()
        and not analysis["can_sum_across_years"].any(),
        {
            "metric_add_true": int(analysis["can_sum_across_metrics"].sum()),
            "year_add_true": int(analysis["can_sum_across_years"].sum()),
        },
    )
    sign_contract = {
        "position": sorted(
            source.loc[source["metric_name"].eq("position"), "direction_sign_convention"]
            .dropna()
            .unique()
            .tolist()
        ),
        "income": sorted(
            source.loc[source["metric_name"].eq("income"), "direction_sign_convention"]
            .dropna()
            .unique()
            .tolist()
        ),
        "flows_by_direction": source.loc[source["metric_name"].eq("flows")]
        .groupby("investment_direction")["direction_sign_convention"]
        .unique()
        .map(lambda values: sorted(values.tolist()))
        .to_dict(),
    }
    expected_sign_contract = {
        "position": ["source_reported_signed_position_no_recode"],
        "income": ["source_reported_signed_income_no_recode"],
        "flows_by_direction": {
            name: [rule["flow_sign_convention"]]
            for name, rule in config["directions"].items()
        },
    }
    add_check(
        validation,
        "metric_sign_conventions",
        sign_contract == expected_sign_contract,
        {"actual": sign_contract, "expected": expected_sign_contract},
    )

    role_checks = {
        "outward_origin_usa": bool(
            source.loc[
                source["investment_direction"].eq("us_direct_investment_abroad")
                & source["main_analysis_country_flag"],
                "origin_country_iso3",
            ].eq("USA").all()
        ),
        "outward_destination_foreign": bool(
            source.loc[
                source["investment_direction"].eq("us_direct_investment_abroad")
                & source["main_analysis_country_flag"],
                "destination_country_iso3",
            ].eq(
                source.loc[
                    source["investment_direction"].eq("us_direct_investment_abroad")
                    & source["main_analysis_country_flag"],
                    "country_iso3",
                ]
            ).all()
        ),
        "inward_origin_foreign": bool(
            source.loc[
                source["investment_direction"].eq("foreign_direct_investment_in_us")
                & source["main_analysis_country_flag"],
                "origin_country_iso3",
            ].eq(
                source.loc[
                    source["investment_direction"].eq("foreign_direct_investment_in_us")
                    & source["main_analysis_country_flag"],
                    "country_iso3",
                ]
            ).all()
        ),
        "inward_destination_usa": bool(
            source.loc[
                source["investment_direction"].eq("foreign_direct_investment_in_us")
                & source["main_analysis_country_flag"],
                "destination_country_iso3",
            ].eq("USA").all()
        ),
    }
    add_check(validation, "direction_country_roles", all(role_checks.values()), role_checks)

    comparison = analysis.loc[analysis["comparison_sample_country_flag"]]
    comparison_country_count = int(comparison["country_iso3"].nunique())
    comparison_cells = int(
        comparison[["country_iso3", "investment_direction", "year"]].drop_duplicates().shape[0]
    )
    add_check(
        validation,
        "comparison_country_coverage",
        comparison_country_count == int(config["validation"]["expected_comparison_country_count"])
        and comparison_cells
        == int(config["validation"]["expected_comparison_country_direction_year_cells"]),
        {"countries": comparison_country_count, "country_direction_year_cells": comparison_cells},
    )
    for iso3 in config["validation"]["expected_absent_country_iso3"]:
        add_check(
            validation,
            f"absent_country_{iso3}",
            not analysis["country_iso3"].eq(iso3).any(),
            int(analysis["country_iso3"].eq(iso3).sum()),
        )
    twn = analysis.loc[analysis["country_iso3"].eq("TWN")]
    add_check(
        validation,
        "twn_direction_and_proxy_coverage",
        len(twn) == 150
        and int(twn["proxy_flag"].sum()) == 30
        and twn["investment_direction"].nunique() == 2,
        {"rows": len(twn), "proxy_rows": int(twn["proxy_flag"].sum())},
    )
    mex_proxy = analysis.loc[
        analysis["country_iso3"].eq("MEX") & analysis["analysis_sector"].eq("autos")
    ]
    mex_inward_income = mex_proxy.loc[
        mex_proxy["investment_direction"].eq("foreign_direct_investment_in_us")
        & mex_proxy["metric_name"].eq("income")
    ]
    add_check(
        validation,
        "mexico_autos_proxy_boundary",
        len(mex_proxy) == int(config["validation"]["expected_mexico_autos_proxy_rows"])
        and int(mex_inward_income["suppressed_flag"].sum())
        == int(config["validation"]["expected_mexico_inward_autos_income_suppressed_rows"])
        and not mex_proxy["main_analysis_join_eligible"].any(),
        {
            "proxy_rows": len(mex_proxy),
            "inward_income_suppressed": int(mex_inward_income["suppressed_flag"].sum()),
        },
    )

    source_aliases = alias_validation(
        source_long_schema(config), source_spec["stata_aliases"]
    )
    analysis_aliases = alias_validation(
        analysis_long_schema(config), analysis_spec["stata_aliases"]
    )
    validation["stata_alias_validation"] = {
        "source_long": source_aliases,
        "analysis_long": analysis_aliases,
    }
    add_check(validation, "source_stata_aliases", source_aliases["pass"], source_aliases)
    add_check(validation, "analysis_stata_aliases", analysis_aliases["pass"], analysis_aliases)

    validation["outputs"] = {
        "source_long": {
            "path": source_spec["path"],
            "sha256": sha256(built["source_path"]),
            "rows": len(source),
            "columns": len(source.columns),
            "schema_signature": schema_signature(built["source_table"].schema),
        },
        "analysis_long": {
            "path": analysis_spec["path"],
            "sha256": sha256(built["analysis_path"]),
            "rows": len(analysis),
            "columns": len(analysis.columns),
            "schema_signature": schema_signature(built["analysis_table"].schema),
        },
    }
    validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    return validation


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# M4.4 BEA Direct Investment Standardization Validation",
        "",
        f"- Status: **{validation['validation_status']}**",
        f"- Generated UTC: `{validation['generated_at_utc']}`",
        f"- Config SHA256: `{validation['config_sha256']}`",
        f"- Checks: {len(validation['checks'])}",
        f"- Failures: {len(validation['failures'])}",
        "",
        "## Canonical outputs",
        "",
        "| Output | Rows | Columns | SHA256 |",
        "|---|---:|---:|---|",
    ]
    for name, item in validation.get("outputs", {}).items():
        lines.append(
            f"| `{item['path']}` | {item['rows']:,} | {item['columns']} | `{item['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation contract",
            "",
            "- `position` is an end-period historical-cost stock; `flows` and `income` are separate annual-flow concepts. They must never be added across metrics or mechanically summed across years.",
            "- `us_direct_investment_abroad` treats the foreign country as affiliate host; `foreign_direct_investment_in_us` treats it as foreign investor origin.",
            "- `(D)` remains missing/suppressed. `(*)` remains numeric zero with a small-value flag and is not an exact zero.",
            "- Negative values retain the BEA-reported sign. No absolute-value conversion, clipping, or sign reversal is applied.",
            "- Formal sector `value` is available only when all required source industries are disclosed. `source_disclosed_value_sum` is diagnostic only.",
            "- Transportation equipment is an `autos` robustness proxy with `main_analysis_join_eligible=false`.",
            "",
            "## Checks",
            "",
            "| Check | Status |",
            "|---|---|",
        ]
    )
    for check in validation["checks"]:
        lines.append(f"| `{check['name']}` | {'PASS' if check['pass'] else 'FAIL'} |")
    if validation["failures"]:
        lines.extend(["", "## Failures", ""])
        for failure in validation["failures"]:
            lines.append(
                f"- `{failure['name']}`: `{json.dumps(failure['evidence'], ensure_ascii=False)}`"
            )
    return "\n".join(lines) + "\n"


def write_validation_reports(
    project_root: Path, config: dict[str, Any], validation: dict[str, Any]
) -> None:
    json_path = project_root / config["validation_outputs"]["json"]
    markdown_path = project_root / config["validation_outputs"]["markdown"]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(jsonable(validation), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(markdown_report(validation), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--config", default="configs/production_bea_fdi_rules.yaml"
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    config_path = (project_root / args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    source_destination = project_root / config["outputs"]["source_long"]["path"]
    analysis_destination = project_root / config["outputs"]["analysis_long"]["path"]
    if not args.overwrite and (source_destination.exists() or analysis_destination.exists()):
        raise FileExistsError(
            "Canonical M4.4 output already exists; pass --overwrite only after reviewing the frozen config."
        )

    candidate_dir = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    determinism_dir = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    remove_owned_temp_directory(candidate_dir)
    remove_owned_temp_directory(determinism_dir)
    candidate_dir.mkdir(parents=True, exist_ok=True)
    determinism_dir.mkdir(parents=True, exist_ok=True)

    try:
        inputs = read_inputs(project_root, config)
        candidate = build_once(
            project_root, candidate_dir, config, config_hash, inputs
        )
        validation = validate_candidate(
            project_root, config_path, config, config_hash, inputs, candidate
        )
        if not validation["failures"]:
            second = build_once(
                project_root, determinism_dir, config, config_hash, inputs
            )
            source_candidate_hash = sha256(candidate["source_path"])
            source_second_hash = sha256(second["source_path"])
            analysis_candidate_hash = sha256(candidate["analysis_path"])
            analysis_second_hash = sha256(second["analysis_path"])
            add_check(
                validation,
                "deterministic_source_long_sha256",
                source_candidate_hash == source_second_hash,
                {"candidate": source_candidate_hash, "second_build": source_second_hash},
            )
            add_check(
                validation,
                "deterministic_analysis_long_sha256",
                analysis_candidate_hash == analysis_second_hash,
                {"candidate": analysis_candidate_hash, "second_build": analysis_second_hash},
            )
            validation["determinism"] = {
                "source_long_candidate_sha256": source_candidate_hash,
                "source_long_second_build_sha256": source_second_hash,
                "source_long_sha256_match": source_candidate_hash == source_second_hash,
                "analysis_long_candidate_sha256": analysis_candidate_hash,
                "analysis_long_second_build_sha256": analysis_second_hash,
                "analysis_long_sha256_match": analysis_candidate_hash == analysis_second_hash,
            }
        validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
        if validation["failures"]:
            write_validation_reports(project_root, config, validation)
            raise RuntimeError(
                f"M4.4 validation failed with {len(validation['failures'])} failure(s); canonical outputs were not replaced."
            )

        source_destination.parent.mkdir(parents=True, exist_ok=True)
        analysis_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate["source_path"], source_destination)
        shutil.copy2(candidate["analysis_path"], analysis_destination)
        add_check(
            validation,
            "canonical_source_hash_matches_candidate",
            sha256(source_destination) == validation["outputs"]["source_long"]["sha256"],
            sha256(source_destination),
        )
        add_check(
            validation,
            "canonical_analysis_hash_matches_candidate",
            sha256(analysis_destination) == validation["outputs"]["analysis_long"]["sha256"],
            sha256(analysis_destination),
        )
        validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    finally:
        remove_owned_temp_directory(candidate_dir)
        remove_owned_temp_directory(determinism_dir)

    validation["determinism"]["temporary_output_cleaned"] = (
        not candidate_dir.exists() and not determinism_dir.exists()
    )
    add_check(
        validation,
        "temporary_output_cleaned",
        validation["determinism"]["temporary_output_cleaned"],
        validation["determinism"]["temporary_output_cleaned"],
    )
    validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    write_validation_reports(project_root, config, validation)
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "check_count": len(validation["checks"]),
                "failure_count": len(validation["failures"]),
                "source_long": validation["outputs"]["source_long"],
                "analysis_long": validation["outputs"]["analysis_long"],
                "determinism": validation["determinism"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
