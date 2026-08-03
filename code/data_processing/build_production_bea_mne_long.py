#!/usr/bin/env python3
"""Build and validate the M4.3 BEA U.S. MNE production-side long tables."""

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


SOURCE_KEY = ["year", "affiliate_country", "industry"]
SOURCE_LONG_KEY = [
    "source_name",
    "source_country_id",
    "model_sector",
    "year",
    "metric_name",
]
ANALYSIS_LONG_KEY = [
    "country_iso3",
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


def join_unique_text(values: pd.Series) -> object:
    items = sorted({str(value) for value in values.dropna() if str(value)})
    return " | ".join(items) if items else pd.NA


def max_abs(values: pd.Series | np.ndarray) -> float:
    array = np.asarray(values, dtype="float64")
    finite = np.abs(array[np.isfinite(array)])
    return float(finite.max()) if finite.size else 0.0


def normalize_source_file(value: object, project_root: Path) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).replace("\\", "/")
    root = project_root.as_posix().rstrip("/") + "/"
    return text[len(root) :] if text.lower().startswith(root.lower()) else text


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
        "can_sum_across_metrics",
        "preliminary_release_flag",
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
        "disclosed_value_negative_flag",
        "disclosed_value_zero_flag",
        "metric_additive_across_source_industries",
        "can_sum_across_metrics",
        "analysis_sector_is_direct_from_one_source_industry",
        "analysis_sector_aggregates_multiple_source_industries",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
        "preliminary_release_flag",
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
    activity = pd.read_parquet(project_root / specs["bea_mne_activity"]["path"])
    countries = pd.read_parquet(project_root / specs["country_crosswalk"]["path"])
    sectors = pd.read_parquet(project_root / specs["source_sector_crosswalk"]["path"])
    with (project_root / specs["build_summary"]["path"]).open(
        "r", encoding="utf-8"
    ) as handle:
        build_summary = json.load(handle)
    with (project_root / specs["raw_manifest"]["path"]).open(
        "r", encoding="utf-8"
    ) as handle:
        raw_manifest = json.load(handle)
    return {
        "activity": activity,
        "countries": countries,
        "sectors": sectors,
        "build_summary": build_summary,
        "raw_manifest": raw_manifest,
    }


def input_contract(
    project_root: Path,
    spec: dict[str, Any],
    frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    path = project_root / spec["path"]
    result: dict[str, Any] = {
        "path": spec["path"],
        "sha256": sha256(path),
        "expected_sha256": spec["sha256"],
        "hash_match": sha256(path) == spec["sha256"],
    }
    if path.suffix.lower() == ".parquet":
        parquet = pq.ParquetFile(path)
        schema = parquet.schema_arrow
        result.update(
            {
                "rows": parquet.metadata.num_rows,
                "expected_rows": spec["expected_rows"],
                "row_count_match": parquet.metadata.num_rows == spec["expected_rows"],
                "columns": parquet.metadata.num_columns,
                "expected_columns": spec["expected_columns"],
                "column_count_match": parquet.metadata.num_columns
                == spec["expected_columns"],
                "schema_signature": schema_signature(schema),
                "expected_schema_signature": spec["arrow_schema_signature_sha256"],
                "schema_match": schema_signature(schema)
                == spec["arrow_schema_signature_sha256"],
            }
        )
    if frame is not None and "natural_key" in spec:
        key = spec["natural_key"]
        result["key_missing_rows"] = int(frame[key].isna().any(axis=1).sum())
        result["duplicate_key_rows"] = int(frame.duplicated(key).sum())
    return result


def prepare_base(inputs: dict[str, Any], config: dict[str, Any]) -> pd.DataFrame:
    source_name = config["source_name"]
    activity = inputs["activity"].copy()
    countries = inputs["countries"].loc[
        inputs["countries"]["source_name"].eq(source_name)
    ].copy()
    sectors = inputs["sectors"].loc[
        inputs["sectors"]["source_name"].eq(source_name)
    ].copy()

    country_columns = {
        "source_country_id": "cw_source_country_id",
        "source_country_name": "cw_source_country_name",
        "source_area_type": "cw_source_area_type",
        "country_iso3": "country_iso3",
        "country_iso2": "country_iso2",
        "canonical_country_name": "canonical_country_name",
        "mapping_status": "country_mapping_status",
        "mapping_method": "country_mapping_method",
        "is_country": "country_is_country",
        "is_aggregate": "country_is_aggregate",
        "is_residual": "country_is_residual",
        "is_proxy": "country_is_proxy",
        "is_core_connector": "is_core_connector",
        "is_asian_comparator": "is_asian_comparator",
        "is_other_candidate": "is_other_candidate",
    }
    country_join = countries[list(country_columns)].rename(columns=country_columns)
    base = activity.merge(
        country_join,
        left_on="affiliate_country",
        right_on="cw_source_country_id",
        how="left",
        validate="many_to_one",
        indicator="_country_join",
    )

    sector_columns = {
        "source_sector_code": "cw_source_sector_code",
        "source_sector_level": "source_sector_level",
        "source_sector_label": "source_sector_label",
        "analysis_sector": "analysis_sector",
        "mapping_status": "sector_mapping_status",
        "mapping_rule": "sector_mapping_rule",
        "first_round_exclusion": "sector_first_round_exclusion",
        "proxy_analysis_sector": "sector_proxy_analysis_sector",
        "is_main_join_eligible": "sector_is_main_join_eligible",
        "mapping_weight": "sector_mapping_weight",
        "source_granularity_note": "source_granularity_note",
        "source_code_family": "source_code_family",
        "mapping_version": "source_sector_mapping_version",
    }
    sector_join = sectors[list(sector_columns)].rename(columns=sector_columns)
    base = base.merge(
        sector_join,
        left_on="industry",
        right_on="cw_source_sector_code",
        how="left",
        validate="many_to_one",
        indicator="_sector_join",
    )

    rules = config["source_rules"]
    base["source_name"] = source_name
    base["source_country_id"] = base["affiliate_country"]
    base["source_country_name"] = base["affiliate_country"]
    base["source_bea_area_type"] = base["bea_area_type"]
    base["source_bea_parent_area"] = base["bea_parent_area"]
    base["country_area_override_flag"] = (
        base["source_bea_area_type"].ne("aggregate")
        & base["country_is_aggregate"].fillna(False)
    )
    base["main_analysis_country_flag"] = (
        base["country_is_country"].fillna(False)
        & ~base["country_is_aggregate"].fillna(False)
        & ~base["country_is_residual"].fillna(False)
    )
    base["comparison_sample_country_flag"] = base[
        ["is_core_connector", "is_asian_comparator", "is_other_candidate"]
    ].fillna(False).any(axis=1)
    base["parent_country_iso3"] = rules["parent_country_iso3"]
    base["ownership_scope"] = rules["ownership_scope"]
    base["model_sector"] = base["industry"]
    base["aggregate_geography_flag"] = base["country_is_aggregate"].fillna(False)
    base["aggregate_sector_flag"] = base["model_sector"].isin(
        rules["aggregate_sector_codes"]
    )
    base["residual_flag"] = base["country_is_residual"].fillna(False) | base[
        "model_sector"
    ].isin(rules["residual_sector_codes"])
    base["proxy_flag"] = base["country_is_proxy"].fillna(False) | base[
        "sector_proxy_analysis_sector"
    ].notna()
    base["main_analysis_join_eligible"] = (
        base["main_analysis_country_flag"]
        & base["sector_is_main_join_eligible"].fillna(False)
        & base["sector_mapping_weight"].eq(1.0)
    )
    base["preliminary_release_flag"] = base["year"].isin(
        rules["preliminary_years"]
    )
    return base


def build_source_long(
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    project_root: Path,
) -> pd.DataFrame:
    common_fields = [
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
        "parent_country_iso3",
        "ownership_scope",
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
        "aggregate_geography_flag",
        "aggregate_sector_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "preliminary_release_flag",
    ]
    parts: list[pd.DataFrame] = []
    for metric_name, spec in config["metrics"].items():
        part = base[common_fields].copy()
        part["metric_name"] = metric_name
        part["metric_order"] = int(spec["order"])
        part["value"] = pd.to_numeric(base[spec["source_field"]], errors="coerce")
        part["raw_code"] = base[spec["raw_code_field"]].astype("string")
        part["unit"] = spec["unit"]
        part["frequency"] = "annual"
        part["direction"] = spec["direction"]
        part["direct_or_allocated"] = "direct_published"
        part["derivation_status"] = "direct_published_cell"
        part["metric_formula"] = spec["formula"]
        part["metric_use"] = spec["use"]
        part["value_available_flag"] = part["value"].notna()
        part["suppressed_flag"] = base[spec["suppressed_field"]].fillna(False).astype(bool)
        part["small_value_flag"] = base[spec["small_value_field"]].fillna(False).astype(bool)
        part["confidential_flag"] = False
        part["observed_negative_flag"] = part["value"].lt(0).fillna(False)
        part["reported_zero_flag"] = part["value"].eq(0).fillna(False)
        part["exact_zero_flag"] = (
            part["reported_zero_flag"] & ~part["small_value_flag"]
        )
        part["metric_additive_across_source_industries"] = True
        part["can_sum_across_metrics"] = False
        part["source_file"] = base[spec["source_file_field"]].map(
            lambda value: normalize_source_file(value, project_root)
        )
        part["release_vintage"] = base["release_vintage"]
        part["download_date"] = base["download_date"]
        part["source_page"] = base["source_page"]
        part["m4_bea_mne_version"] = config["construction_version"]
        part["rules_config_sha256"] = config_hash
        part["schema_version"] = config["outputs"]["source_long"]["schema_version"]
        parts.append(part)
    output = pd.concat(parts, ignore_index=True)
    output = output.sort_values(
        ["source_country_id", "model_sector", "year", "metric_order"],
        kind="mergesort",
    ).reset_index(drop=True)
    return output


def analysis_components(base: pd.DataFrame) -> pd.DataFrame:
    actual = base.loc[base["main_analysis_country_flag"]].copy()
    main = actual.loc[base.loc[actual.index, "main_analysis_join_eligible"]].copy()
    main["resolved_analysis_sector"] = main["analysis_sector"]
    main["analysis_scope"] = "main"

    proxy = actual.loc[actual["sector_proxy_analysis_sector"].notna()].copy()
    proxy["resolved_analysis_sector"] = proxy["sector_proxy_analysis_sector"]
    proxy["analysis_scope"] = "proxy_robustness"
    return pd.concat([main, proxy], ignore_index=True)


def expected_industry_counts(
    components: pd.DataFrame,
) -> dict[tuple[str, str], int]:
    unique = components[
        ["analysis_scope", "resolved_analysis_sector", "model_sector"]
    ].drop_duplicates()
    counts = unique.groupby(
        ["analysis_scope", "resolved_analysis_sector"], observed=True
    ).size()
    return {(str(scope), str(sector)): int(count) for (scope, sector), count in counts.items()}


def build_analysis_long(
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    project_root: Path,
) -> pd.DataFrame:
    components = analysis_components(base)
    expected_counts = expected_industry_counts(components)
    keys = ["country_iso3", "resolved_analysis_sector", "year"]
    static = (
        components.groupby(keys, sort=True, observed=True)
        .agg(
            source_country_id=("source_country_id", join_unique_text),
            canonical_country_name=("canonical_country_name", join_unique_text),
            analysis_scope=("analysis_scope", "first"),
            source_industry_count=("model_sector", "size"),
            source_industry_codes=("model_sector", join_unique_text),
            source_industry_labels=("source_sector_label", join_unique_text),
            source_mapping_statuses=("sector_mapping_status", join_unique_text),
            source_mapping_rules=("sector_mapping_rule", join_unique_text),
            source_granularity_note=("source_granularity_note", join_unique_text),
            source_sector_mapping_version=(
                "source_sector_mapping_version",
                join_unique_text,
            ),
            is_core_connector=("is_core_connector", "max"),
            is_asian_comparator=("is_asian_comparator", "max"),
            is_other_candidate=("is_other_candidate", "max"),
            comparison_sample_country_flag=(
                "comparison_sample_country_flag",
                "max",
            ),
            release_vintage=("release_vintage", "first"),
        )
        .reset_index()
    )
    static["expected_source_industry_count"] = [
        expected_counts[(str(scope), str(sector))]
        for scope, sector in zip(
            static["analysis_scope"], static["resolved_analysis_sector"]
        )
    ]
    parts: list[pd.DataFrame] = []
    for metric_name, spec in config["metrics"].items():
        metric = components[keys].copy()
        metric["metric_value"] = pd.to_numeric(
            components[spec["source_field"]], errors="coerce"
        )
        metric["metric_suppressed"] = components[spec["suppressed_field"]].fillna(False).astype(bool)
        metric["metric_small"] = components[spec["small_value_field"]].fillna(False).astype(bool)
        metric["metric_negative"] = metric["metric_value"].lt(0).fillna(False)
        metric["metric_zero"] = metric["metric_value"].eq(0).fillna(False)
        metric["metric_exact_zero"] = metric["metric_zero"] & ~metric["metric_small"]
        metric["source_file"] = components[spec["source_file_field"]].map(
            lambda value: normalize_source_file(value, project_root)
        )
        grouped = metric.groupby(keys, sort=True, observed=True)
        stats = grouped.agg(
            source_disclosed_industry_count=("metric_value", "count"),
            source_suppressed_cell_count=("metric_suppressed", "sum"),
            source_small_value_cell_count=("metric_small", "sum"),
            source_negative_cell_count=("metric_negative", "sum"),
            source_reported_zero_cell_count=("metric_zero", "sum"),
            source_exact_zero_cell_count=("metric_exact_zero", "sum"),
            source_file=("source_file", "first"),
        ).reset_index()
        sums = grouped["metric_value"].sum(min_count=1).rename(
            "source_disclosed_value_sum"
        ).reset_index()
        part = static.merge(stats, on=keys, validate="one_to_one").merge(
            sums, on=keys, validate="one_to_one"
        )
        part["source_missing_cell_count"] = (
            part["source_industry_count"]
            - part["source_disclosed_industry_count"]
        )
        full = (
            part["source_industry_count"].eq(part["expected_source_industry_count"])
            & part["source_disclosed_industry_count"].eq(
                part["expected_source_industry_count"]
            )
        )
        part["value"] = part["source_disclosed_value_sum"].where(full)
        direct = part["expected_source_industry_count"].eq(1)
        part["country_iso3"] = part["country_iso3"]
        part["analysis_sector"] = part["resolved_analysis_sector"]
        part["source_name"] = config["source_name"]
        part["parent_country_iso3"] = config["source_rules"]["parent_country_iso3"]
        part["ownership_scope"] = config["source_rules"]["ownership_scope"]
        part["metric_name"] = metric_name
        part["metric_order"] = int(spec["order"])
        part["unit"] = spec["unit"]
        part["frequency"] = "annual"
        part["direction"] = spec["direction"]
        part["direct_or_allocated"] = np.where(
            direct, "direct_published", "sum_of_direct_published"
        )
        part["derivation_status"] = np.where(
            direct,
            "direct_one_source_industry",
            "sum_direct_source_industries_if_all_disclosed",
        )
        part["metric_formula"] = np.where(
            direct,
            spec["formula"],
            f"sum_{spec['formula']}_over_mapped_source_industries_when_all_disclosed",
        )
        part["metric_use"] = spec["use"]
        part["value_available_flag"] = full
        part["disclosed_value_available_flag"] = part[
            "source_disclosed_industry_count"
        ].gt(0)
        part["full_sector_coverage_flag"] = full
        part["suppressed_flag"] = part["source_suppressed_cell_count"].gt(0)
        part["partial_disclosure_flag"] = part["source_suppressed_cell_count"].gt(
            0
        ) & part["source_disclosed_industry_count"].gt(0)
        part["all_components_suppressed_flag"] = part[
            "source_disclosed_industry_count"
        ].eq(0) & part["source_suppressed_cell_count"].eq(
            part["source_industry_count"]
        )
        part["small_value_flag"] = part["source_small_value_cell_count"].gt(0)
        part["confidential_flag"] = False
        part["aggregate_flag"] = False
        part["residual_flag"] = False
        part["proxy_flag"] = part["analysis_scope"].eq("proxy_robustness")
        part["main_analysis_join_eligible"] = part["analysis_scope"].eq("main")
        part["observed_negative_flag"] = part["value"].lt(0).fillna(False)
        part["reported_zero_flag"] = part["value"].eq(0).fillna(False)
        part["exact_zero_flag"] = part["reported_zero_flag"] & ~part[
            "small_value_flag"
        ]
        part["disclosed_value_negative_flag"] = part[
            "source_disclosed_value_sum"
        ].lt(0).fillna(False)
        part["disclosed_value_zero_flag"] = part[
            "source_disclosed_value_sum"
        ].eq(0).fillna(False)
        part["metric_additive_across_source_industries"] = True
        part["can_sum_across_metrics"] = False
        part["analysis_sector_is_direct_from_one_source_industry"] = direct
        part["analysis_sector_aggregates_multiple_source_industries"] = ~direct
        part["preliminary_release_flag"] = part["year"].isin(
            config["source_rules"]["preliminary_years"]
        )
        part["m4_bea_mne_version"] = config["construction_version"]
        part["rules_config_sha256"] = config_hash
        part["schema_version"] = config["outputs"]["analysis_long"][
            "schema_version"
        ]
        parts.append(part)
    output = pd.concat(parts, ignore_index=True)
    output = output.drop(columns=["resolved_analysis_sector"])
    output = output.sort_values(
        ["country_iso3", "analysis_sector", "year", "metric_order"],
        kind="mergesort",
    ).reset_index(drop=True)
    return output


def build_once(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    output_dir: Path,
) -> dict[str, Any]:
    inputs = read_inputs(project_root, config)
    base = prepare_base(inputs, config)
    source = build_source_long(base, config, config_hash, project_root)
    analysis = build_analysis_long(base, config, config_hash, project_root)
    source_path = output_dir / "production_bea_mne_source_industry_long.parquet"
    analysis_path = output_dir / "production_validation_bea_mne_long.parquet"
    source_table = write_parquet(source, source_path, source_long_schema(config))
    analysis_table = write_parquet(analysis, analysis_path, analysis_long_schema(config))
    return {
        "inputs": inputs,
        "base": base,
        "source": source,
        "analysis": analysis,
        "source_path": source_path,
        "analysis_path": analysis_path,
        "source_schema_signature": schema_signature(source_table.schema),
        "analysis_schema_signature": schema_signature(analysis_table.schema),
    }


def jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return value


def add_check(
    validation: dict[str, Any],
    name: str,
    observed: Any,
    expected: Any,
    *,
    tolerance: float | None = None,
) -> None:
    if tolerance is None:
        passed = observed == expected
    else:
        passed = bool(abs(float(observed) - float(expected)) <= tolerance)
    item = {
        "check": name,
        "pass": bool(passed),
        "observed": jsonable(observed),
        "expected": jsonable(expected),
    }
    if tolerance is not None:
        item["tolerance"] = tolerance
    validation["checks"].append(item)
    if not passed:
        validation["failures"].append(name)


def raw_manifest_audit(
    project_root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for item in manifest.get("files", []):
        path = project_root / item["local_path"]
        if not path.exists():
            mismatches.append({"path": item["local_path"], "issue": "missing"})
            continue
        observed_size = path.stat().st_size
        observed_hash = sha256(path)
        if observed_size != item["bytes"] or observed_hash != item["sha256"]:
            mismatches.append(
                {
                    "path": item["local_path"],
                    "expected_bytes": item["bytes"],
                    "observed_bytes": observed_size,
                    "expected_sha256": item["sha256"],
                    "observed_sha256": observed_hash,
                }
            )
    return {
        "file_count": len(manifest.get("files", [])),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def recompute_analysis_from_source(source: pd.DataFrame) -> pd.DataFrame:
    components = source.loc[
        source["main_analysis_country_flag"]
        & (
            source["main_analysis_join_eligible"]
            | source["sector_proxy_analysis_sector"].notna()
        )
    ].copy()
    components["analysis_scope"] = np.where(
        components["main_analysis_join_eligible"], "main", "proxy_robustness"
    )
    components["resolved_analysis_sector"] = np.where(
        components["main_analysis_join_eligible"],
        components["analysis_sector"],
        components["sector_proxy_analysis_sector"],
    )
    unique = components[
        ["analysis_scope", "resolved_analysis_sector", "model_sector"]
    ].drop_duplicates()
    expected_counts = (
        unique.groupby(
            ["analysis_scope", "resolved_analysis_sector"], observed=True
        )
        .size()
        .to_dict()
    )
    keys = [
        "country_iso3",
        "resolved_analysis_sector",
        "year",
        "source_name",
        "metric_name",
    ]
    components["negative_component"] = components["value"].lt(0).fillna(False)
    components["zero_component"] = components["value"].eq(0).fillna(False)
    components["exact_zero_component"] = components["zero_component"] & ~components[
        "small_value_flag"
    ]
    grouped = components.groupby(keys, sort=True, observed=True)
    output = grouped.agg(
        analysis_scope=("analysis_scope", "first"),
        source_industry_count_recomputed=("model_sector", "size"),
        source_disclosed_industry_count_recomputed=("value", "count"),
        source_suppressed_cell_count_recomputed=("suppressed_flag", "sum"),
        source_small_value_cell_count_recomputed=("small_value_flag", "sum"),
        source_negative_cell_count_recomputed=("negative_component", "sum"),
        source_reported_zero_cell_count_recomputed=("zero_component", "sum"),
        source_exact_zero_cell_count_recomputed=("exact_zero_component", "sum"),
    ).reset_index()
    sums = grouped["value"].sum(min_count=1).rename(
        "source_disclosed_value_sum_recomputed"
    ).reset_index()
    output = output.merge(sums, on=keys, validate="one_to_one")
    output["expected_source_industry_count_recomputed"] = [
        int(expected_counts[(str(scope), str(sector))])
        for scope, sector in zip(
            output["analysis_scope"], output["resolved_analysis_sector"]
        )
    ]
    output["source_missing_cell_count_recomputed"] = (
        output["source_industry_count_recomputed"]
        - output["source_disclosed_industry_count_recomputed"]
    )
    full = output["source_industry_count_recomputed"].eq(
        output["expected_source_industry_count_recomputed"]
    ) & output["source_disclosed_industry_count_recomputed"].eq(
        output["expected_source_industry_count_recomputed"]
    )
    output["value_recomputed"] = output[
        "source_disclosed_value_sum_recomputed"
    ].where(full)
    output["full_sector_coverage_flag_recomputed"] = full
    output["partial_disclosure_flag_recomputed"] = output[
        "source_suppressed_cell_count_recomputed"
    ].gt(0) & output["source_disclosed_industry_count_recomputed"].gt(0)
    output["all_components_suppressed_flag_recomputed"] = output[
        "source_disclosed_industry_count_recomputed"
    ].eq(0) & output["source_suppressed_cell_count_recomputed"].eq(
        output["source_industry_count_recomputed"]
    )
    return output.rename(
        columns={"resolved_analysis_sector": "analysis_sector"}
    ).drop(columns=["analysis_scope"])


def metric_count_snapshot(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "missing": int(frame["value"].isna().sum()),
        "suppressed": int(frame["suppressed_flag"].sum()),
        "small": int(frame["small_value_flag"].sum()),
        "zero": int(frame["reported_zero_flag"].sum()),
        "negative": int(frame["observed_negative_flag"].sum()),
    }


def analysis_metric_count_snapshot(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "nonmissing": int(frame["value"].notna().sum()),
        "missing": int(frame["value"].isna().sum()),
        "small": int(frame["small_value_flag"].sum()),
        "zero": int(frame["reported_zero_flag"].sum()),
        "exact_zero": int(frame["exact_zero_flag"].sum()),
        "negative": int(frame["observed_negative_flag"].sum()),
        "partial_suppression": int(frame["partial_disclosure_flag"].sum()),
        "all_suppressed": int(frame["all_components_suppressed_flag"].sum()),
    }


def validate_candidate(
    project_root: Path,
    config_path: Path,
    config: dict[str, Any],
    config_hash: str,
    built: dict[str, Any],
) -> dict[str, Any]:
    tolerance = float(config["validation"]["numeric_tolerance"])
    inputs = built["inputs"]
    base = built["base"]
    source = built["source"]
    analysis = built["analysis"]
    specs = config["inputs"]
    source_spec = config["outputs"]["source_long"]
    analysis_spec = config["outputs"]["analysis_long"]
    validation: dict[str, Any] = {
        "validation_status": "PENDING",
        "failures": [],
        "checks": [],
        "validation_version": 1,
        "origin_date": config["origin_date"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path.relative_to(project_root).as_posix(),
        "config_sha256": config_hash,
        "construction_version": config["construction_version"],
    }

    activity_contract = input_contract(
        project_root, specs["bea_mne_activity"], inputs["activity"]
    )
    country_contract = input_contract(
        project_root, specs["country_crosswalk"], inputs["countries"]
    )
    sector_contract = input_contract(
        project_root, specs["source_sector_crosswalk"], inputs["sectors"]
    )
    summary_contract = input_contract(project_root, specs["build_summary"])
    manifest_contract = input_contract(project_root, specs["raw_manifest"])
    input_contracts = {
        "bea_mne_activity": activity_contract,
        "country_crosswalk": country_contract,
        "source_sector_crosswalk": sector_contract,
        "build_summary": summary_contract,
        "raw_manifest": manifest_contract,
    }
    validation["input_contracts"] = input_contracts
    for name, contract in input_contracts.items():
        add_check(validation, f"{name}_hash", contract["sha256"], contract["expected_sha256"])
        if "row_count_match" in contract:
            add_check(validation, f"{name}_rows", contract["rows"], contract["expected_rows"])
            add_check(
                validation,
                f"{name}_columns",
                contract["columns"],
                contract["expected_columns"],
            )
            add_check(
                validation,
                f"{name}_schema",
                contract["schema_signature"],
                contract["expected_schema_signature"],
            )
            add_check(
                validation,
                f"{name}_key_missing",
                contract.get("key_missing_rows", 0),
                0,
            )
            add_check(
                validation,
                f"{name}_duplicate_key",
                contract.get("duplicate_key_rows", 0),
                0,
            )

    countries = inputs["countries"].loc[
        inputs["countries"]["source_name"].eq(config["source_name"])
    ]
    sectors = inputs["sectors"].loc[
        inputs["sectors"]["source_name"].eq(config["source_name"])
    ]
    add_check(
        validation,
        "country_crosswalk_filtered_rows",
        len(countries),
        specs["country_crosswalk"]["expected_filtered_rows"],
    )
    add_check(
        validation,
        "country_crosswalk_filtered_duplicate_key",
        int(countries.duplicated(["source_name", "source_country_id"]).sum()),
        0,
    )
    add_check(
        validation,
        "source_sector_crosswalk_filtered_rows",
        len(sectors),
        specs["source_sector_crosswalk"]["expected_filtered_rows"],
    )
    add_check(
        validation,
        "source_sector_crosswalk_filtered_duplicate_key",
        int(
            sectors.duplicated(
                ["source_name", "source_sector_level", "source_sector_code"]
            ).sum()
        ),
        0,
    )

    raw_audit = raw_manifest_audit(project_root, inputs["raw_manifest"])
    validation["raw_manifest_audit"] = raw_audit
    add_check(
        validation,
        "raw_manifest_file_count",
        raw_audit["file_count"],
        specs["raw_manifest"]["expected_file_count"],
    )
    add_check(validation, "raw_manifest_file_mismatches", raw_audit["mismatch_count"], 0)

    expected_years = config["source_rules"]["years"]
    add_check(validation, "observed_years", sorted(base["year"].unique().tolist()), expected_years)
    add_check(
        validation,
        "source_geography_labels",
        int(base["source_country_id"].nunique()),
        config["validation"]["expected_source_geography_labels"],
    )
    add_check(
        validation,
        "source_industries",
        int(base["model_sector"].nunique()),
        config["validation"]["expected_source_industries"],
    )
    add_check(validation, "country_join_unmatched", int(base["_country_join"].ne("both").sum()), 0)
    add_check(validation, "sector_join_unmatched", int(base["_sector_join"].ne("both").sum()), 0)
    add_check(validation, "join_row_preservation", len(base), len(inputs["activity"]))
    add_check(
        validation,
        "source_area_aggregate_rows",
        int(base["source_bea_area_type"].eq("aggregate").sum()),
        config["validation"]["expected_source_area_aggregate_rows"],
    )
    add_check(
        validation,
        "country_override_aggregate_rows",
        int(base["country_area_override_flag"].sum()),
        config["validation"]["expected_country_override_aggregate_rows"],
    )
    add_check(
        validation,
        "final_aggregate_rows",
        int(base["aggregate_geography_flag"].sum()),
        config["validation"]["expected_final_aggregate_rows"],
    )
    actual = base.loc[base["main_analysis_country_flag"]]
    add_check(
        validation,
        "actual_country_rows",
        len(actual),
        config["validation"]["expected_actual_country_rows"],
    )
    add_check(
        validation,
        "actual_country_count",
        int(actual["country_iso3"].nunique()),
        config["validation"]["expected_actual_country_count"],
    )
    actual_country_year = actual[["country_iso3", "year"]].drop_duplicates()
    add_check(
        validation,
        "actual_country_year_cells",
        len(actual_country_year),
        config["validation"]["expected_actual_country_year_cells"],
    )
    add_check(
        validation,
        "canonical_country_year_industry_duplicate_key",
        int(actual.duplicated(["country_iso3", "year", "model_sector"]).sum()),
        0,
    )
    add_check(
        validation,
        "main_eligible_source_rows",
        int(base["main_analysis_join_eligible"].sum()),
        config["validation"]["expected_main_eligible_source_rows"],
    )
    proxy_source = actual.loc[actual["sector_proxy_analysis_sector"].notna()]
    add_check(
        validation,
        "proxy_source_rows",
        len(proxy_source),
        config["validation"]["expected_proxy_source_rows"],
    )

    add_check(validation, "source_long_rows", len(source), source_spec["expected_rows"])
    add_check(validation, "source_long_columns", source.shape[1], source_spec["expected_columns"])
    add_check(validation, "source_long_duplicate_key", int(source.duplicated(SOURCE_LONG_KEY).sum()), 0)
    add_check(validation, "source_long_key_missing", int(source[SOURCE_LONG_KEY].isna().any(axis=1).sum()), 0)
    add_check(
        validation,
        "source_long_schema_signature",
        built["source_schema_signature"],
        schema_signature(source_long_schema(config)),
    )
    add_check(
        validation,
        "source_long_final_aggregate_rows",
        int(source["aggregate_geography_flag"].sum()),
        config["validation"]["expected_final_aggregate_rows"] * len(config["metrics"]),
    )
    add_check(
        validation,
        "source_long_transportation_proxy_rows",
        int(source["proxy_flag"].sum()),
        config["validation"]["expected_full_source_proxy_rows"]
        * len(config["metrics"]),
    )

    source_metric_checks: dict[str, Any] = {}
    for metric_name, spec in config["metrics"].items():
        block = source.loc[source["metric_name"].eq(metric_name)].copy()
        snapshot = metric_count_snapshot(block)
        source_metric_checks[metric_name] = snapshot
        add_check(
            validation,
            f"source_{metric_name}_row_count",
            len(block),
            len(inputs["activity"]),
        )
        add_check(
            validation,
            f"source_{metric_name}_snapshot",
            snapshot,
            config["validation"]["expected_source_metric_counts"][metric_name],
        )
        add_check(
            validation,
            f"source_{metric_name}_suppressed_nonmissing",
            int((block["suppressed_flag"] & block["value"].notna()).sum()),
            0,
        )
        add_check(
            validation,
            f"source_{metric_name}_unflagged_missing",
            int((~block["suppressed_flag"] & block["value"].isna()).sum()),
            0,
        )
        add_check(
            validation,
            f"source_{metric_name}_small_nonzero",
            int((block["small_value_flag"] & block["value"].ne(0)).sum()),
            0,
        )
        expected_values = base[
            ["source_country_id", "model_sector", "year", spec["source_field"]]
        ].rename(columns={spec["source_field"]: "expected_value"})
        comparison = block.merge(
            expected_values,
            on=["source_country_id", "model_sector", "year"],
            how="left",
            validate="one_to_one",
        )
        numeric_error = np.where(
            comparison["value"].isna() & comparison["expected_value"].isna(),
            0.0,
            comparison["value"] - comparison["expected_value"],
        )
        add_check(
            validation,
            f"source_{metric_name}_value_identity_max_error",
            max_abs(numeric_error),
            0.0,
            tolerance=tolerance,
        )
    validation["source_metric_checks"] = source_metric_checks
    add_check(
        validation,
        "source_files_project_relative",
        int(source["source_file"].str.match(r"^[A-Za-z]:/").fillna(False).sum()),
        0,
    )
    add_check(
        validation,
        "source_numeric_infinite_values",
        int(np.isinf(source["value"].to_numpy(dtype="float64", na_value=np.nan)).sum()),
        0,
    )

    add_check(validation, "analysis_long_rows", len(analysis), analysis_spec["expected_rows"])
    add_check(validation, "analysis_long_columns", analysis.shape[1], analysis_spec["expected_columns"])
    add_check(validation, "analysis_long_duplicate_key", int(analysis.duplicated(ANALYSIS_LONG_KEY).sum()), 0)
    add_check(validation, "analysis_long_key_missing", int(analysis[ANALYSIS_LONG_KEY].isna().any(axis=1).sum()), 0)
    add_check(
        validation,
        "analysis_long_schema_signature",
        built["analysis_schema_signature"],
        schema_signature(analysis_long_schema(config)),
    )
    add_check(
        validation,
        "analysis_country_count",
        int(analysis["country_iso3"].nunique()),
        analysis_spec["expected_country_count"],
    )
    add_check(
        validation,
        "analysis_sector_count",
        int(analysis["analysis_sector"].nunique()),
        analysis_spec["expected_analysis_sector_count"],
    )
    analysis_cells = analysis[
        ["country_iso3", "analysis_sector", "year", "source_name"]
    ].drop_duplicates()
    add_check(
        validation,
        "analysis_country_sector_year_cells",
        len(analysis_cells),
        analysis_spec["expected_country_sector_year_cells"],
    )
    add_check(
        validation,
        "analysis_main_rows",
        int(analysis["analysis_scope"].eq("main").sum()),
        config["validation"]["expected_main_analysis_rows"],
    )
    add_check(
        validation,
        "analysis_proxy_rows",
        int(analysis["analysis_scope"].eq("proxy_robustness").sum()),
        config["validation"]["expected_proxy_analysis_rows"],
    )
    add_check(
        validation,
        "analysis_aggregate_rows",
        int(analysis["aggregate_flag"].sum()),
        0,
    )
    add_check(
        validation,
        "analysis_proxy_flag_contract",
        int(
            (
                analysis["analysis_scope"].eq("proxy_robustness")
                ^ analysis["proxy_flag"]
            ).sum()
        ),
        0,
    )
    add_check(
        validation,
        "analysis_proxy_main_join_conflict",
        int((analysis["proxy_flag"] & analysis["main_analysis_join_eligible"]).sum()),
        0,
    )
    add_check(
        validation,
        "analysis_autos_nonproxy_rows",
        int((analysis["analysis_sector"].eq("autos") & ~analysis["proxy_flag"]).sum()),
        0,
    )
    add_check(
        validation,
        "analysis_unsupported_sector_rows",
        int(
            analysis["analysis_sector"].isin(
                config["source_rules"]["unsupported_analysis_sectors"]
            ).sum()
        ),
        0,
    )

    comparison_countries = analysis.loc[
        analysis["comparison_sample_country_flag"], "country_iso3"
    ].drop_duplicates()
    comparison_country_year = analysis.loc[
        analysis["comparison_sample_country_flag"], ["country_iso3", "year"]
    ].drop_duplicates()
    add_check(
        validation,
        "comparison_country_count",
        len(comparison_countries),
        config["validation"]["expected_comparison_country_count"],
    )
    add_check(
        validation,
        "comparison_country_year_cells",
        len(comparison_country_year),
        config["validation"]["expected_comparison_country_year_cells"],
    )
    for country, years in config["validation"]["expected_missing_country_years"].items():
        observed = sorted(
            analysis.loc[analysis["country_iso3"].eq(country), "year"].unique().tolist()
        )
        expected_observed = sorted(set(config["source_rules"]["years"]) - set(years))
        add_check(validation, f"{country}_observed_years", observed, expected_observed)
    for country in config["validation"]["expected_absent_country_iso3"]:
        add_check(
            validation,
            f"{country}_analysis_rows",
            int(analysis["country_iso3"].eq(country).sum()),
            0,
        )
    add_check(
        validation,
        "twn_proxy_rows",
        int((analysis["country_iso3"].eq("TWN") & analysis["proxy_flag"] & analysis["analysis_sector"].ne("autos")).sum()),
        0,
    )

    analysis_metric_checks: dict[str, Any] = {}
    for metric_name in config["metrics"]:
        block = analysis.loc[analysis["metric_name"].eq(metric_name)].copy()
        snapshot = analysis_metric_count_snapshot(block)
        analysis_metric_checks[metric_name] = snapshot
        add_check(
            validation,
            f"analysis_{metric_name}_snapshot",
            snapshot,
            config["validation"]["expected_analysis_metric_counts"][metric_name],
        )
    validation["analysis_metric_checks"] = analysis_metric_checks

    recomputed = recompute_analysis_from_source(source)
    merged = analysis.merge(recomputed, on=ANALYSIS_LONG_KEY, how="outer", validate="one_to_one", indicator=True)
    add_check(validation, "analysis_recompute_key_match", int(merged["_merge"].ne("both").sum()), 0)
    strict_error = np.where(
        merged["value"].isna() & merged["value_recomputed"].isna(),
        0.0,
        merged["value"] - merged["value_recomputed"],
    )
    disclosed_error = np.where(
        merged["source_disclosed_value_sum"].isna()
        & merged["source_disclosed_value_sum_recomputed"].isna(),
        0.0,
        merged["source_disclosed_value_sum"]
        - merged["source_disclosed_value_sum_recomputed"],
    )
    add_check(validation, "analysis_strict_value_max_error", max_abs(strict_error), 0.0, tolerance=tolerance)
    add_check(validation, "analysis_disclosed_value_max_error", max_abs(disclosed_error), 0.0, tolerance=tolerance)
    compare_fields = [
        "expected_source_industry_count",
        "source_industry_count",
        "source_disclosed_industry_count",
        "source_suppressed_cell_count",
        "source_small_value_cell_count",
        "source_missing_cell_count",
        "source_negative_cell_count",
        "source_reported_zero_cell_count",
        "source_exact_zero_cell_count",
        "full_sector_coverage_flag",
        "partial_disclosure_flag",
        "all_components_suppressed_flag",
    ]
    for field in compare_fields:
        expected_field = f"{field}_recomputed"
        add_check(
            validation,
            f"analysis_{field}_recomputed",
            int((merged[field] != merged[expected_field]).sum()),
            0,
        )

    other = analysis.loc[analysis["analysis_sector"].eq("other_manufacturing")]
    add_check(
        validation,
        "other_manufacturing_component_count_values",
        sorted(other["expected_source_industry_count"].unique().tolist()),
        [2],
    )
    add_check(
        validation,
        "other_manufacturing_source_industries",
        sorted(other["source_industry_codes"].drop_duplicates().tolist()),
        ["Chemicals | Food"],
    )
    add_check(
        validation,
        "analysis_source_file_multiple_values",
        int(analysis["source_file"].str.contains(r" \| ", regex=True).fillna(False).sum()),
        0,
    )
    add_check(
        validation,
        "analysis_numeric_infinite_values",
        int(
            np.isinf(
                analysis[["value", "source_disclosed_value_sum"]]
                .to_numpy(dtype="float64", na_value=np.nan)
            ).sum()
        ),
        0,
    )

    negative_expected = config["validation"]["expected_negative_value_added_counts"]
    negative_observed = {
        "full_source": int(inputs["activity"]["value_added"].lt(0).sum()),
        "actual_country_source": int(actual["value_added"].lt(0).sum()),
        "main_eligible_source": int(
            base.loc[base["main_analysis_join_eligible"], "value_added"].lt(0).sum()
        ),
        "strict_main_analysis": int(
            analysis.loc[
                analysis["metric_name"].eq("value_added")
                & analysis["analysis_scope"].eq("main"),
                "value",
            ].lt(0).sum()
        ),
        "strict_proxy_analysis": int(
            analysis.loc[
                analysis["metric_name"].eq("value_added")
                & analysis["analysis_scope"].eq("proxy_robustness"),
                "value",
            ].lt(0).sum()
        ),
        "strict_main_plus_proxy_analysis": int(
            analysis.loc[analysis["metric_name"].eq("value_added"), "value"].lt(0).sum()
        ),
    }
    validation["negative_value_added_counts"] = negative_observed
    add_check(validation, "negative_value_added_layers", negative_observed, negative_expected)

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
    add_check(validation, "source_long_stata_aliases", source_aliases["pass"], True)
    add_check(validation, "analysis_long_stata_aliases", analysis_aliases["pass"], True)

    validation["coverage_and_mapping"] = {
        "source_rows": len(base),
        "source_geography_labels": int(base["source_country_id"].nunique()),
        "source_industries": int(base["model_sector"].nunique()),
        "source_area_aggregate_rows": int(base["source_bea_area_type"].eq("aggregate").sum()),
        "country_override_aggregate_rows": int(base["country_area_override_flag"].sum()),
        "final_aggregate_rows": int(base["aggregate_geography_flag"].sum()),
        "actual_country_rows": len(actual),
        "actual_country_count": int(actual["country_iso3"].nunique()),
        "actual_country_year_cells": len(actual_country_year),
        "main_eligible_source_rows": int(base["main_analysis_join_eligible"].sum()),
        "proxy_source_rows": len(proxy_source),
    }
    validation["outputs"] = {
        "source_long": {
            "path": source_spec["path"],
            "sha256": sha256(built["source_path"]),
            "rows": len(source),
            "columns": source.shape[1],
            "schema_signature": built["source_schema_signature"],
        },
        "analysis_long": {
            "path": analysis_spec["path"],
            "sha256": sha256(built["analysis_path"]),
            "rows": len(analysis),
            "columns": analysis.shape[1],
            "schema_signature": built["analysis_schema_signature"],
        },
    }
    validation["validation_status"] = (
        "PASS" if not validation["failures"] else "FAIL"
    )
    return validation


def markdown_report(validation: dict[str, Any]) -> str:
    outputs = validation["outputs"]
    coverage = validation["coverage_and_mapping"]
    determinism = validation.get("determinism", {})
    negative = validation["negative_value_added_counts"]
    lines = [
        "# M4.3 BEA MNE Production Standardization Validation",
        "",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Generated at (UTC): `{validation['generated_at_utc']}`",
        f"- Config SHA256: `{validation['config_sha256']}`",
        f"- Failures: `{len(validation['failures'])}`",
        "",
        "## Canonical outputs",
        "",
        "| Output | Rows | Columns | SHA256 |",
        "|---|---:|---:|---|",
        (
            f"| `{outputs['source_long']['path']}` | "
            f"{outputs['source_long']['rows']:,} | {outputs['source_long']['columns']} | "
            f"`{outputs['source_long']['sha256']}` |"
        ),
        (
            f"| `{outputs['analysis_long']['path']}` | "
            f"{outputs['analysis_long']['rows']:,} | {outputs['analysis_long']['columns']} | "
            f"`{outputs['analysis_long']['sha256']}` |"
        ),
        "",
        "## Grain and coverage",
        "",
        f"- Source input: {coverage['source_rows']:,} country/area-industry-year rows, "
        f"{coverage['source_geography_labels']} source geography labels, "
        f"{coverage['source_industries']} published industries.",
        f"- Raw BEA aggregate rows: {coverage['source_area_aggregate_rows']:,}; "
        f"canonical country override rows: {coverage['country_override_aggregate_rows']:,}; "
        f"final aggregate rows excluded from analysis: {coverage['final_aggregate_rows']:,}.",
        f"- Actual-country input: {coverage['actual_country_rows']:,} rows, "
        f"{coverage['actual_country_count']} ISO3 countries and "
        f"{coverage['actual_country_year_cells']} observed country-years.",
        f"- Strict main source rows: {coverage['main_eligible_source_rows']:,}; "
        f"Transportation-equipment autos-proxy source rows: {coverage['proxy_source_rows']:,}.",
        "- The analysis table contains four main sectors plus a separately flagged "
        "`autos` robustness proxy. It does not materialize unsupported medical-devices "
        "or textiles/apparel rows.",
        "",
        "## Suppression and small values",
        "",
        "- `(D)` and employment size-range codes remain missing with "
        "`suppressed_flag=true`; no suppressed value is converted to zero.",
        "- `(*)` remains numeric 0.0 with `small_value_flag=true`; `exact_zero_flag` "
        "distinguishes it from an ordinary reported zero.",
        "- For multi-industry analysis sectors, `value` is defined only if every "
        "required component is disclosed. `source_disclosed_value_sum` is retained "
        "only as a diagnostic partial sum.",
        "",
        "## Negative value added",
        "",
        "| Layer | Negative observations |",
        "|---|---:|",
        f"| Full source | {negative['full_source']:,} |",
        f"| Actual-country source | {negative['actual_country_source']:,} |",
        f"| Strict main source mapping | {negative['main_eligible_source']:,} |",
        f"| Strict main analysis | {negative['strict_main_analysis']:,} |",
        f"| Autos proxy analysis | {negative['strict_proxy_analysis']:,} |",
        "",
        "Negative values are retained as valid BEA observations; they are not clipped.",
        "",
        "## Determinism and Stata interface",
        "",
        f"- Source-long deterministic SHA256 match: "
        f"`{determinism.get('source_long_sha256_match')}`.",
        f"- Analysis-long deterministic SHA256 match: "
        f"`{determinism.get('analysis_long_sha256_match')}`.",
        f"- Temporary outputs cleaned: `{determinism.get('temporary_output_cleaned')}`.",
        "- All aliases cover the output schemas, are unique, legal Stata names, and "
        "do not exceed 32 characters. `.dta` export remains deferred to M7.",
        "",
        "## Interpretation boundaries",
        "",
        "- `sales` is BEA affiliate sales, not ICIO gross output.",
        "- Affiliate trade is not additive with BACI/Census trade.",
        "- Transportation equipment is broader than autos and is retained only as "
        "`analysis_scope=proxy_robustness`, `proxy_flag=true`, and "
        "`main_analysis_join_eligible=false`.",
        "- Vietnam is observed only for 2019-2023; 2017-2018 are not filled with zeros. "
        "Morocco is absent from this BEA source.",
        "- M4.3 does not construct growth, rankings, cross-source production merges, "
        "structural moments, or counterfactual inputs.",
        "",
    ]
    if validation["failures"]:
        lines.extend(["## Failed checks", ""])
        lines.extend(f"- `{name}`" for name in validation["failures"])
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/production_bea_mne_rules.yaml"),
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    config_path = (
        args.config.resolve()
        if args.config.is_absolute()
        else (project_root / args.config).resolve()
    )
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    candidate_dir = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    determinism_dir = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if candidate_dir.exists() or determinism_dir.exists():
        raise FileExistsError(
            "M4.3 task-owned temporary directory already exists; refusing to reuse it."
        )

    source_target = project_root / config["outputs"]["source_long"]["path"]
    analysis_target = project_root / config["outputs"]["analysis_long"]["path"]
    if not args.overwrite:
        existing = [path for path in (source_target, analysis_target) if path.exists()]
        if existing:
            raise FileExistsError(
                "Canonical output exists; rerun with --overwrite after review: "
                + ", ".join(str(path) for path in existing)
            )

    candidate_dir.mkdir(parents=True)
    validation: dict[str, Any] | None = None
    try:
        candidate = build_once(project_root, config, config_hash, candidate_dir)
        validation = validate_candidate(
            project_root, config_path, config, config_hash, candidate
        )
        if validation["validation_status"] != "PASS":
            failure_path = candidate_dir / "production_bea_mne_validation_failed.json"
            failure_path.write_text(
                json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(
                "M4.3 candidate validation failed: "
                + ", ".join(validation["failures"])
            )

        determinism_dir.mkdir(parents=True)
        second = build_once(project_root, config, config_hash, determinism_dir)
        source_first_hash = sha256(candidate["source_path"])
        source_second_hash = sha256(second["source_path"])
        analysis_first_hash = sha256(candidate["analysis_path"])
        analysis_second_hash = sha256(second["analysis_path"])
        add_check(
            validation,
            "source_long_deterministic_sha256",
            source_second_hash,
            source_first_hash,
        )
        add_check(
            validation,
            "analysis_long_deterministic_sha256",
            analysis_second_hash,
            analysis_first_hash,
        )
        validation["determinism"] = {
            "source_long_candidate_sha256": source_first_hash,
            "source_long_second_build_sha256": source_second_hash,
            "source_long_sha256_match": source_first_hash == source_second_hash,
            "analysis_long_candidate_sha256": analysis_first_hash,
            "analysis_long_second_build_sha256": analysis_second_hash,
            "analysis_long_sha256_match": analysis_first_hash == analysis_second_hash,
            "temporary_output_cleaned": False,
        }
        validation["validation_status"] = (
            "PASS" if not validation["failures"] else "FAIL"
        )
        if validation["validation_status"] != "PASS":
            raise RuntimeError(
                "M4.3 deterministic build failed: "
                + ", ".join(validation["failures"])
            )

        source_target.parent.mkdir(parents=True, exist_ok=True)
        analysis_target.parent.mkdir(parents=True, exist_ok=True)
        candidate["source_path"].replace(source_target)
        candidate["analysis_path"].replace(analysis_target)
        remove_owned_temp_directory(candidate_dir)
        remove_owned_temp_directory(determinism_dir)
        validation["determinism"]["temporary_output_cleaned"] = (
            not candidate_dir.exists() and not determinism_dir.exists()
        )
        add_check(
            validation,
            "temporary_output_cleaned",
            validation["determinism"]["temporary_output_cleaned"],
            True,
        )
        validation["outputs"]["source_long"]["sha256"] = sha256(source_target)
        validation["outputs"]["analysis_long"]["sha256"] = sha256(analysis_target)
        validation["validation_status"] = (
            "PASS" if not validation["failures"] else "FAIL"
        )
        if validation["validation_status"] != "PASS":
            raise RuntimeError("M4.3 post-replacement validation state is not PASS")

        json_path = project_root / config["validation_outputs"]["json"]
        markdown_path = project_root / config["validation_outputs"]["markdown"]
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(markdown_report(validation), encoding="utf-8")
        print(
            json.dumps(
                {
                    "validation_status": validation["validation_status"],
                    "source_long": validation["outputs"]["source_long"],
                    "analysis_long": validation["outputs"]["analysis_long"],
                    "failures": validation["failures"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        remove_owned_temp_directory(candidate_dir)
        remove_owned_temp_directory(determinism_dir)


if __name__ == "__main__":
    main()
