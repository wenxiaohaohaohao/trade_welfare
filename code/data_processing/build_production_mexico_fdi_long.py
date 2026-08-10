#!/usr/bin/env python3
"""Build and validate the M4.5 Mexico inward-FDI standardization tables."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


USED_PANEL_IDS = {
    "country_sector_quarterly",
    "national_quarterly",
    "national_investment_type_quarterly",
    "parent_country_annual",
    "sector_annual",
}


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


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def max_abs(values: pd.Series | np.ndarray) -> float:
    array = np.asarray(values, dtype="float64")
    finite = np.abs(array[np.isfinite(array)])
    return float(finite.max()) if finite.size else 0.0


def add_check(
    validation: dict[str, Any], name: str, passed: bool, evidence: Any
) -> None:
    check = {"name": name, "pass": bool(passed), "evidence": jsonable(evidence)}
    validation["checks"].append(check)
    if not passed:
        validation["failures"].append(check)


def project_relative_source_file(value: object) -> object:
    if pd.isna(value):
        return pd.NA
    text = str(value).replace("\\", "/")
    if text.startswith("data/"):
        return text
    if text.lower().endswith(".json"):
        return f"data/raw/mexico_fdi/datamexico_api/{text}"
    return f"data/raw/mexico_fdi/{text}"


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


def output_schema(config: dict[str, Any], output_id: str) -> pa.Schema:
    aliases = config["outputs"][output_id]["stata_aliases"]
    common_bool = {
        "parent_country_is_country",
        "parent_country_is_residual",
        "parent_country_total_flag",
        "parent_country_residual_flag",
        "parent_country_join_eligible",
        "parent_is_source_core",
        "parent_is_source_extended",
        "parent_is_asian_comparator",
        "parent_is_other_candidate",
        "comparison_sample_parent_flag",
        "sector_is_main_join_eligible",
        "complete_period_flag",
        "annual_comparable_flag",
        "h1_comparable_flag",
        "partial_year_flag",
        "value_available_flag",
        "confidential_flag",
        "partial_disclosure_flag",
        "all_components_confidential_flag",
        "observed_negative_flag",
        "reported_zero_flag",
        "exact_zero_flag",
        "cancellation_to_zero_flag",
        "published_component_lattice_complete_flag",
        "published_component_scope_flag",
        "theoretical_full_sector_coverage_not_asserted_flag",
        "main_cross_source_join_eligible",
        "national_total_flag",
        "one_dimensional_margin_flag",
        "nonadditive_to_national_flag",
        "can_sum_across_source_panels",
        "can_sum_across_years",
        "can_sum_across_metrics",
    }
    count_fields = {
        "published_source_industry_count",
        "observed_source_industry_count",
        "expected_source_row_count",
        "source_row_count",
        "source_disclosed_cell_count",
        "source_confidential_cell_count",
        "source_negative_cell_count",
        "source_exact_zero_cell_count",
    }
    return schema_from_aliases(
        aliases,
        bool_fields=common_bool,
        int8_fields={
            "quarter",
            "period_start_quarter",
            "period_end_quarter",
            "expected_quarter_count",
            "observed_quarter_count",
            "confidential_quarter_count",
        },
        int16_fields={"year"},
        int32_fields=count_fields,
        float_fields={"value", "source_disclosed_value_sum", "sector_mapping_weight"},
    )


def alias_validation(schema: pa.Schema, aliases: dict[str, str]) -> dict[str, Any]:
    fields = schema.names
    missing = sorted(set(fields) - set(aliases))
    extra = sorted(set(aliases) - set(fields))
    values = list(aliases.values())
    lowered = [value.lower() for value in values]
    duplicate = sorted(
        {value for value in lowered if lowered.count(value) > 1}
    )
    invalid = {
        name: alias
        for name, alias in aliases.items()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", alias) is None
    }
    over = {name: alias for name, alias in aliases.items() if len(alias) > 32}
    return {
        "pass": not missing and not extra and not duplicate and not invalid and not over,
        "field_count": len(fields),
        "alias_count": len(aliases),
        "missing": missing,
        "extra": extra,
        "duplicate_case_insensitive": duplicate,
        "invalid": invalid,
        "over_32_characters": over,
        "max_alias_length": max(map(len, values), default=0),
    }


def cast_frame_to_table(frame: pd.DataFrame, schema: pa.Schema) -> pa.Table:
    result = frame.reindex(columns=schema.names).copy()
    for field in schema:
        name = field.name
        if pa.types.is_boolean(field.type):
            result[name] = result[name].astype("boolean")
        elif pa.types.is_integer(field.type):
            result[name] = pd.to_numeric(result[name], errors="coerce").astype(
                "Int8" if pa.types.is_int8(field.type) else "Int16" if pa.types.is_int16(field.type) else "Int32"
            )
        elif pa.types.is_floating(field.type):
            result[name] = pd.to_numeric(result[name], errors="coerce").astype("float64")
        else:
            result[name] = result[name].astype("string")
    return pa.Table.from_pandas(result, schema=schema, preserve_index=False, safe=True)


def write_frames(
    path: Path, schema: pa.Schema, frames: Iterable[pd.DataFrame]
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    total_rows = 0
    try:
        writer = pq.ParquetWriter(
            path,
            schema,
            compression="zstd",
            use_dictionary=True,
            write_statistics=True,
            version="2.6",
        )
        for frame in frames:
            table = cast_frame_to_table(frame, schema)
            writer.write_table(table, row_group_size=65536)
            total_rows += table.num_rows
            del table
            gc.collect()
    finally:
        if writer is not None:
            writer.close()
    return {"rows": total_rows, "columns": len(schema), "schema": schema}


def create_owned_temp(path: Path, token: str) -> None:
    if path.exists():
        raise FileExistsError(
            f"Task temp path already exists and will not be removed automatically: {path}"
        )
    path.mkdir(parents=True)
    (path / ".m4_5_owner").write_text(token, encoding="utf-8")


def remove_owned_temp(path: Path, token: str) -> None:
    marker = path / ".m4_5_owner"
    if not path.exists():
        return
    if not marker.is_file() or marker.read_text(encoding="utf-8") != token:
        raise RuntimeError(f"Refusing to remove unowned temp directory: {path}")
    shutil.rmtree(path)


def resolve_temp(project_root: Path, relative: str) -> Path:
    path = (project_root / relative).resolve()
    if not path.is_relative_to(project_root):
        raise ValueError(f"Temporary path escapes project root: {path}")
    if path.drive.lower() != project_root.drive.lower():
        raise ValueError(f"Temporary path is not on the project drive: {path}")
    return path


def read_inputs(
    project_root: Path, config: dict[str, Any]
) -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    frames: dict[str, pd.DataFrame] = {}
    audits: dict[str, Any] = {}
    for input_id, spec in config["inputs"].items():
        if input_id == "build_summary":
            continue
        path = project_root / spec["path"]
        parquet = pq.ParquetFile(path)
        schema = parquet.schema_arrow
        key = spec["natural_key"]
        if input_id in USED_PANEL_IDS or input_id in {
            "country_crosswalk",
            "source_sector_crosswalk",
            "time_aggregation_rules",
        }:
            frame = pd.read_parquet(path)
            frames[input_id] = frame
            key_frame = frame[key]
        else:
            key_frame = pq.read_table(path, columns=key).to_pandas()
        audits[input_id] = {
            "path": spec["path"],
            "sha256": sha256(path),
            "rows": parquet.metadata.num_rows,
            "columns": len(schema),
            "schema_signature": schema_signature(schema),
            "duplicate_key_rows": int(key_frame.duplicated(key).sum()),
            "missing_key_cells": int(key_frame.isna().sum().sum()),
        }
        del key_frame
    return frames, audits


def prepare_detail(
    inputs: dict[str, pd.DataFrame], config: dict[str, Any]
) -> pd.DataFrame:
    detail = inputs["country_sector_quarterly"].copy()
    detail = detail.rename(
        columns={"parent_country_iso3": "embedded_parent_country_iso3"}
    )
    country = inputs["country_crosswalk"]
    country = country.loc[
        country["source_name"].eq(config["source_name"])
    ].copy()
    country = country.rename(
        columns={
            "source_country_id": "source_parent_country_id",
            "source_country_name": "crosswalk_parent_country_name",
            "country_iso3": "cw_parent_country_iso3",
            "country_iso2": "parent_country_iso2",
            "canonical_country_name": "parent_canonical_country_name",
            "mapping_status": "parent_country_mapping_status",
            "mapping_method": "parent_country_mapping_method",
            "is_country": "parent_country_is_country",
            "is_residual": "parent_country_is_residual",
            "is_source_core": "parent_is_source_core",
            "is_source_extended": "parent_is_source_extended",
            "is_asian_comparator": "parent_is_asian_comparator",
            "is_other_candidate": "parent_is_other_candidate",
        }
    )
    country_fields = [
        "source_parent_country_id",
        "crosswalk_parent_country_name",
        "cw_parent_country_iso3",
        "parent_country_iso2",
        "parent_canonical_country_name",
        "parent_country_mapping_status",
        "parent_country_mapping_method",
        "parent_country_is_country",
        "parent_country_is_residual",
        "parent_is_source_core",
        "parent_is_source_extended",
        "parent_is_asian_comparator",
        "parent_is_other_candidate",
    ]
    detail = detail.merge(
        country[country_fields],
        left_on="parent_country_name",
        right_on="source_parent_country_id",
        how="left",
        validate="many_to_one",
        indicator="_country_merge",
    )
    sector = inputs["source_sector_crosswalk"]
    sector = sector.loc[sector["source_name"].eq(config["source_name"])].copy()
    sector = sector.rename(
        columns={
            "source_sector_level": "sector_level",
            "source_sector_code": "sector_code",
            "source_sector_label": "crosswalk_sector_label",
            "mapping_status": "sector_mapping_status",
            "mapping_rule": "sector_mapping_rule",
            "first_round_exclusion": "sector_first_round_exclusion",
            "proxy_analysis_sector": "sector_proxy_analysis_sector",
            "is_main_join_eligible": "sector_is_main_join_eligible",
        }
    )
    sector_fields = [
        "sector_level",
        "sector_code",
        "crosswalk_sector_label",
        "analysis_sector",
        "sector_mapping_status",
        "sector_mapping_rule",
        "sector_first_round_exclusion",
        "sector_proxy_analysis_sector",
        "sector_is_main_join_eligible",
        "mapping_weight",
        "source_granularity_note",
        "source_code_family",
        "mapping_version",
    ]
    detail = detail.merge(
        sector[sector_fields],
        on=["sector_level", "sector_code"],
        how="left",
        validate="many_to_one",
        indicator="_sector_merge",
    )
    detail["parent_country_iso3"] = detail["cw_parent_country_iso3"]
    detail["parent_country_join_eligible"] = detail["parent_country_is_country"].fillna(False)
    detail["comparison_sample_parent_flag"] = (
        detail["parent_is_source_core"].fillna(False)
        | detail["parent_is_source_extended"].fillna(False)
        | detail["parent_is_asian_comparator"].fillna(False)
        | detail["parent_is_other_candidate"].fillna(False)
    )
    return detail


def source_static(detail: pd.DataFrame) -> pd.DataFrame:
    fields = [
        "source_parent_country_id",
        "parent_country_name",
        "parent_country_iso3",
        "parent_country_iso2",
        "parent_canonical_country_name",
        "parent_country_mapping_status",
        "parent_country_mapping_method",
        "parent_country_is_country",
        "parent_country_is_residual",
        "parent_country_total_flag",
        "parent_country_residual_flag",
        "parent_country_join_eligible",
        "parent_is_source_core",
        "parent_is_source_extended",
        "parent_is_asian_comparator",
        "parent_is_other_candidate",
        "comparison_sample_parent_flag",
        "sector_level",
        "sector_code",
        "sector_name",
        "analysis_sector",
        "sector_mapping_status",
        "sector_mapping_rule",
        "sector_first_round_exclusion",
        "sector_proxy_analysis_sector",
        "sector_is_main_join_eligible",
        "mapping_weight",
        "source_granularity_note",
        "source_code_family",
        "mapping_version",
    ]
    return detail[fields].drop_duplicates(
        ["source_parent_country_id", "sector_level", "sector_code"]
    )


def enrich_source_frame(
    frame: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    *,
    period_type: str,
) -> pd.DataFrame:
    metric = config["metric"]
    result = frame.copy()
    result["source_name"] = config["source_name"]
    result["source_parent_country_name"] = result["parent_country_name"]
    result["host_country_iso3"] = "MEX"
    result["host_country_name"] = "Mexico"
    result["investment_direction"] = metric["investment_direction"]
    result["origin_country_iso3"] = result["parent_country_iso3"]
    result["destination_country_iso3"] = "MEX"
    result["source_sector_level"] = result["sector_level"]
    result["source_sector_code"] = result["sector_code"]
    result["source_sector_label"] = result["sector_name"]
    result["sector_mapping_weight"] = result["mapping_weight"]
    result["source_sector_mapping_version"] = result["mapping_version"]
    result["metric_name"] = metric["metric_name"]
    result["unit"] = metric["unit"]
    result["temporal_type"] = metric["temporal_type"]
    result["direct_or_allocated"] = metric["direct_or_allocated"]
    result["metric_use"] = metric["metric_use"]
    if period_type == "quarter":
        result["derivation_status"] = "direct_quarterly_source_value"
        result["metric_formula"] = "official_quarterly_fdi_flow"
    elif period_type == "calendar_year":
        result["derivation_status"] = "derived_period_sum"
        result["metric_formula"] = "sum_q1_q2_q3_q4_if_complete_and_nonconfidential"
    else:
        result["derivation_status"] = "derived_period_sum"
        result["metric_formula"] = "sum_q1_q2_if_complete_and_nonconfidential"
    result["can_sum_across_source_panels"] = metric["can_sum_across_source_panels"]
    result["can_sum_across_years"] = metric["can_sum_across_years"]
    result["can_sum_across_metrics"] = metric["can_sum_across_metrics"]
    result["source_snapshot_date"] = "2026-07-18"
    result["m4_mexico_fdi_version"] = config["construction_version"]
    result["rules_config_sha256"] = config_hash
    result["schema_version"] = config["outputs"]["source_period_long"]["schema_version"]
    result["source_file"] = result["source_file"].map(project_relative_source_file)
    return result


def build_source_quarter(
    detail: pd.DataFrame, config: dict[str, Any], config_hash: str
) -> pd.DataFrame:
    frame = detail.copy()
    frame["period_type"] = "quarter"
    frame["period_id"] = frame["period"]
    frame["period_start_quarter"] = frame["quarter"]
    frame["period_end_quarter"] = frame["quarter"]
    frame["expected_quarter_count"] = 1
    frame["observed_quarter_count"] = 1
    frame["complete_period_flag"] = True
    frame["annual_comparable_flag"] = False
    frame["h1_comparable_flag"] = False
    frame["partial_year_flag"] = True
    frame["value"] = frame["fdi_million_usd"]
    frame["source_disclosed_value_sum"] = frame["fdi_million_usd"]
    frame["value_available_flag"] = frame["value"].notna()
    frame["confidential_quarter_count"] = frame["confidential_flag"].astype("int8")
    frame["partial_disclosure_flag"] = False
    frame["all_components_confidential_flag"] = frame["confidential_flag"]
    frame["observed_negative_flag"] = frame["value"].lt(0).fillna(False)
    frame["reported_zero_flag"] = frame["value"].eq(0).fillna(False)
    frame["exact_zero_flag"] = frame["reported_zero_flag"]
    return enrich_source_frame(frame, config, config_hash, period_type="quarter")


def build_source_period(
    detail: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    *,
    period_type: str,
    quarters: list[int],
) -> pd.DataFrame:
    subset = detail.loc[detail["quarter"].isin(quarters)].copy()
    key = [
        "source_parent_country_id",
        "sector_level",
        "sector_code",
        "year",
    ]
    grouped = subset.groupby(key, dropna=False, sort=True).agg(
        observed_quarter_count=("quarter", "nunique"),
        source_row_count=("quarter", "size"),
        source_disclosed_cell_count=("fdi_million_usd", "count"),
        confidential_quarter_count=("confidential_flag", "sum"),
        source_disclosed_value_sum=("fdi_million_usd", lambda values: values.sum(min_count=1)),
        source_file=("source_file", "first"),
    ).reset_index()
    grouped["expected_quarter_count"] = len(quarters)
    grouped["complete_period_flag"] = (
        grouped["observed_quarter_count"].eq(len(quarters))
        & grouped["source_row_count"].eq(len(quarters))
    )
    grouped["confidential_flag"] = grouped["confidential_quarter_count"].gt(0)
    grouped["value_available_flag"] = (
        grouped["complete_period_flag"] & ~grouped["confidential_flag"]
    )
    grouped["value"] = grouped["source_disclosed_value_sum"].where(
        grouped["value_available_flag"]
    )
    grouped["partial_disclosure_flag"] = (
        grouped["confidential_flag"]
        & grouped["source_disclosed_cell_count"].gt(0)
    )
    grouped["all_components_confidential_flag"] = grouped[
        "source_disclosed_cell_count"
    ].eq(0)
    grouped["observed_negative_flag"] = grouped["value"].lt(0).fillna(False)
    grouped["reported_zero_flag"] = grouped["value"].eq(0).fillna(False)
    grouped["exact_zero_flag"] = grouped["reported_zero_flag"]
    grouped["quarter"] = pd.NA
    grouped["period_type"] = period_type
    grouped["period_id"] = (
        grouped["year"].astype(str)
        + ("" if period_type == "calendar_year" else "H1")
    )
    grouped["period_start_quarter"] = min(quarters)
    grouped["period_end_quarter"] = max(quarters)
    grouped["annual_comparable_flag"] = (
        period_type == "calendar_year"
    ) & grouped["complete_period_flag"]
    grouped["h1_comparable_flag"] = (
        period_type == "h1"
    ) & grouped["complete_period_flag"]
    grouped["partial_year_flag"] = period_type != "calendar_year"
    grouped = grouped.merge(
        source_static(detail),
        on=["source_parent_country_id", "sector_level", "sector_code"],
        how="left",
        validate="many_to_one",
    )
    return enrich_source_frame(grouped, config, config_hash, period_type=period_type)


def prepare_parent_base(detail: pd.DataFrame) -> pd.DataFrame:
    return detail.loc[
        detail["sector_is_main_join_eligible"].fillna(False)
        & detail["mapping_weight"].eq(1)
    ].copy()


def parent_support(base: pd.DataFrame) -> pd.DataFrame:
    key = ["source_parent_country_id", "analysis_sector"]
    return (
        base[key + ["sector_code"]]
        .drop_duplicates()
        .groupby(key, dropna=False)
        .agg(published_source_industry_count=("sector_code", "nunique"))
        .reset_index()
    )


def enrich_parent_frame(
    frame: pd.DataFrame,
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    *,
    period_type: str,
) -> pd.DataFrame:
    meta_fields = [
        "source_parent_country_id",
        "parent_country_name",
        "parent_country_iso3",
        "parent_canonical_country_name",
        "parent_country_mapping_status",
        "parent_country_is_country",
        "parent_country_is_residual",
        "parent_country_join_eligible",
        "parent_is_source_core",
        "parent_is_source_extended",
        "parent_is_asian_comparator",
        "parent_is_other_candidate",
        "comparison_sample_parent_flag",
    ]
    meta = base[meta_fields].drop_duplicates("source_parent_country_id")
    result = frame.merge(
        meta, on="source_parent_country_id", how="left", validate="many_to_one"
    )
    result["source_parent_country_name"] = result["parent_country_name"]
    result["host_country_iso3"] = "MEX"
    result["host_country_name"] = "Mexico"
    result["investment_direction"] = config["metric"]["investment_direction"]
    result["origin_country_iso3"] = result["parent_country_iso3"]
    result["destination_country_iso3"] = "MEX"
    result["source_name"] = config["source_name"]
    result["metric_name"] = config["metric"]["metric_name"]
    result["unit"] = config["metric"]["unit"]
    result["temporal_type"] = config["metric"]["temporal_type"]
    result["direct_or_allocated"] = config["metric"]["direct_or_allocated"]
    result["metric_use"] = "parent_origin_analysis_sector_fdi_composition_evidence"
    result["derivation_status"] = "aggregated_from_published_joint_detail"
    if period_type == "quarter":
        result["metric_formula"] = "sum_published_scians_within_parent_sector_quarter_if_nonconfidential"
    elif period_type == "calendar_year":
        result["metric_formula"] = "sum_published_scians_and_q1_q4_if_complete_nonconfidential"
    else:
        result["metric_formula"] = "sum_published_scians_and_q1_q2_if_complete_nonconfidential"
    result["published_component_scope_flag"] = True
    result["theoretical_full_sector_coverage_not_asserted_flag"] = True
    result["main_cross_source_join_eligible"] = False
    result["can_sum_across_source_panels"] = False
    result["can_sum_across_years"] = False
    result["can_sum_across_metrics"] = False
    result["source_snapshot_date"] = "2026-07-18"
    result["m4_mexico_fdi_version"] = config["construction_version"]
    result["rules_config_sha256"] = config_hash
    result["schema_version"] = config["outputs"]["parent_sector_period_long"]["schema_version"]
    return result


def aggregate_parent_period(
    base: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
    *,
    period_type: str,
    quarters: list[int],
) -> pd.DataFrame:
    subset = base.loc[base["quarter"].isin(quarters)].copy()
    group_key = ["source_parent_country_id", "analysis_sector", "year"]
    if period_type == "quarter":
        group_key.append("quarter")
    grouped = subset.groupby(group_key, dropna=False, sort=True).agg(
        observed_quarter_count=("quarter", "nunique"),
        observed_source_industry_count=("sector_code", "nunique"),
        source_row_count=("sector_code", "size"),
        source_disclosed_cell_count=("fdi_million_usd", "count"),
        source_confidential_cell_count=("confidential_flag", "sum"),
        source_negative_cell_count=("fdi_million_usd", lambda values: int(values.lt(0).sum())),
        source_exact_zero_cell_count=("fdi_million_usd", lambda values: int(values.eq(0).sum())),
        source_disclosed_value_sum=("fdi_million_usd", lambda values: values.sum(min_count=1)),
    ).reset_index()
    grouped = grouped.merge(
        parent_support(base),
        on=["source_parent_country_id", "analysis_sector"],
        how="left",
        validate="many_to_one",
    )
    required_quarter_count = 1 if period_type == "quarter" else len(quarters)
    grouped["expected_quarter_count"] = required_quarter_count
    grouped["expected_source_row_count"] = (
        grouped["published_source_industry_count"] * required_quarter_count
    )
    grouped["published_component_lattice_complete_flag"] = (
        grouped["observed_quarter_count"].eq(required_quarter_count)
        & grouped["observed_source_industry_count"].eq(
            grouped["published_source_industry_count"]
        )
        & grouped["source_row_count"].eq(grouped["expected_source_row_count"])
    )
    grouped["complete_period_flag"] = grouped[
        "published_component_lattice_complete_flag"
    ]
    grouped["confidential_flag"] = grouped[
        "source_confidential_cell_count"
    ].gt(0)
    grouped["value_available_flag"] = (
        grouped["complete_period_flag"] & ~grouped["confidential_flag"]
    )
    grouped["value"] = grouped["source_disclosed_value_sum"].where(
        grouped["value_available_flag"]
    )
    grouped["partial_disclosure_flag"] = (
        grouped["confidential_flag"]
        & grouped["source_disclosed_cell_count"].gt(0)
    )
    grouped["all_components_confidential_flag"] = grouped[
        "source_disclosed_cell_count"
    ].eq(0)
    grouped["observed_negative_flag"] = grouped["value"].lt(0).fillna(False)
    grouped["reported_zero_flag"] = grouped["value"].eq(0).fillna(False)
    grouped["exact_zero_flag"] = (
        grouped["reported_zero_flag"]
        & grouped["source_exact_zero_cell_count"].eq(grouped["source_row_count"])
    )
    grouped["cancellation_to_zero_flag"] = (
        grouped["reported_zero_flag"] & ~grouped["exact_zero_flag"]
    )
    grouped["period_type"] = period_type
    if period_type == "quarter":
        grouped["period_id"] = (
            grouped["year"].astype(str) + "Q" + grouped["quarter"].astype(str)
        )
        grouped["period_start_quarter"] = grouped["quarter"]
        grouped["period_end_quarter"] = grouped["quarter"]
    else:
        grouped["quarter"] = pd.NA
        grouped["period_id"] = grouped["year"].astype(str) + (
            "" if period_type == "calendar_year" else "H1"
        )
        grouped["period_start_quarter"] = min(quarters)
        grouped["period_end_quarter"] = max(quarters)
    grouped["annual_comparable_flag"] = (
        period_type == "calendar_year"
    ) & grouped["complete_period_flag"]
    grouped["h1_comparable_flag"] = (
        period_type == "h1"
    ) & grouped["complete_period_flag"]
    grouped["partial_year_flag"] = period_type != "calendar_year"
    return enrich_parent_frame(
        grouped, base, config, config_hash, period_type=period_type
    )


def benchmark_common(
    frame: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> pd.DataFrame:
    result = frame.copy()
    result["host_country_iso3"] = "MEX"
    result["host_country_name"] = "Mexico"
    result["investment_direction"] = config["metric"]["investment_direction"]
    result["destination_country_iso3"] = "MEX"
    result["source_name"] = config["source_name"]
    result["metric_name"] = config["metric"]["metric_name"]
    result["unit"] = config["metric"]["unit"]
    result["temporal_type"] = config["metric"]["temporal_type"]
    result["direct_or_allocated"] = config["metric"]["direct_or_allocated"]
    result["metric_use"] = "official_mexico_fdi_benchmark_or_one_dimensional_margin"
    result["value_available_flag"] = result["value"].notna()
    result["confidential_flag"] = False
    result["observed_negative_flag"] = result["value"].lt(0).fillna(False)
    result["reported_zero_flag"] = result["value"].eq(0).fillna(False)
    result["exact_zero_flag"] = result["reported_zero_flag"]
    result["can_sum_across_source_panels"] = False
    result["can_sum_across_years"] = False
    result["can_sum_across_metrics"] = False
    result["source_snapshot_date"] = "2026-07-18"
    result["m4_mexico_fdi_version"] = config["construction_version"]
    result["rules_config_sha256"] = config_hash
    result["schema_version"] = config["outputs"]["benchmark_period_long"]["schema_version"]
    result["source_disclosed_value_sum"] = result["value"]
    return result


def build_national_benchmarks(
    inputs: dict[str, pd.DataFrame], config: dict[str, Any], config_hash: str
) -> pd.DataFrame:
    national = inputs["national_quarterly"].copy()
    quarter = national.copy()
    quarter["benchmark_scope"] = "national_total"
    quarter["benchmark_record_id"] = "NATIONAL_TOTAL"
    quarter["source_panel"] = "national_quarterly"
    quarter["source_parent_country_id"] = "ALL_FOREIGN_SOURCES"
    quarter["source_parent_country_name"] = "All foreign sources"
    quarter["parent_country_iso3"] = pd.NA
    quarter["parent_canonical_country_name"] = pd.NA
    quarter["parent_country_record_type"] = "national_all_sources"
    quarter["parent_country_join_eligible"] = False
    quarter["source_sector_level"] = "all_economy"
    quarter["source_sector_code"] = "ALL"
    quarter["source_sector_label"] = "All economy"
    quarter["sector_mapping_status"] = "national_total_not_sector_allocated"
    quarter["sector_is_main_join_eligible"] = False
    quarter["analysis_sector"] = "all_economy"
    quarter["origin_country_iso3"] = pd.NA
    quarter["period_type"] = "quarter"
    quarter["period_id"] = quarter["period"]
    quarter["period_start_quarter"] = quarter["quarter"]
    quarter["period_end_quarter"] = quarter["quarter"]
    quarter["expected_quarter_count"] = 1
    quarter["observed_quarter_count"] = 1
    quarter["complete_period_flag"] = True
    quarter["annual_comparable_flag"] = False
    quarter["h1_comparable_flag"] = False
    quarter["partial_year_flag"] = True
    quarter["value"] = quarter["fdi_million_usd"]
    quarter["national_total_flag"] = True
    quarter["one_dimensional_margin_flag"] = False
    quarter["nonadditive_to_national_flag"] = False
    quarter["main_cross_source_join_eligible"] = True
    quarter["derivation_status"] = "direct_national_quarterly_total"
    quarter["metric_formula"] = "official_national_quarterly_fdi_flow"
    quarter["source_file"] = quarter["source_file"].map(project_relative_source_file)

    derived_frames = []
    for period_type, quarters in (("calendar_year", [1, 2, 3, 4]), ("h1", [1, 2])):
        subset = national.loc[national["quarter"].isin(quarters)]
        frame = subset.groupby("year", sort=True).agg(
            observed_quarter_count=("quarter", "nunique"),
            value=("fdi_million_usd", "sum"),
            source_file=("source_file", "first"),
        ).reset_index()
        frame["benchmark_scope"] = "national_total"
        frame["benchmark_record_id"] = "NATIONAL_TOTAL"
        frame["source_panel"] = "national_quarterly"
        frame["source_parent_country_id"] = "ALL_FOREIGN_SOURCES"
        frame["source_parent_country_name"] = "All foreign sources"
        frame["parent_country_iso3"] = pd.NA
        frame["parent_canonical_country_name"] = pd.NA
        frame["parent_country_record_type"] = "national_all_sources"
        frame["parent_country_join_eligible"] = False
        frame["source_sector_level"] = "all_economy"
        frame["source_sector_code"] = "ALL"
        frame["source_sector_label"] = "All economy"
        frame["sector_mapping_status"] = "national_total_not_sector_allocated"
        frame["sector_is_main_join_eligible"] = False
        frame["analysis_sector"] = "all_economy"
        frame["origin_country_iso3"] = pd.NA
        frame["quarter"] = pd.NA
        frame["period_type"] = period_type
        frame["period_id"] = frame["year"].astype(str) + (
            "" if period_type == "calendar_year" else "H1"
        )
        frame["period_start_quarter"] = min(quarters)
        frame["period_end_quarter"] = max(quarters)
        frame["expected_quarter_count"] = len(quarters)
        frame["complete_period_flag"] = frame["observed_quarter_count"].eq(len(quarters))
        frame["annual_comparable_flag"] = period_type == "calendar_year"
        frame["h1_comparable_flag"] = period_type == "h1"
        frame["partial_year_flag"] = period_type == "h1"
        frame["national_total_flag"] = True
        frame["one_dimensional_margin_flag"] = False
        frame["nonadditive_to_national_flag"] = False
        frame["main_cross_source_join_eligible"] = True
        frame["derivation_status"] = "derived_from_national_quarterly_total"
        frame["metric_formula"] = (
            "sum_national_q1_q4" if period_type == "calendar_year" else "sum_national_q1_q2"
        )
        frame["source_file"] = frame["source_file"].map(project_relative_source_file)
        derived_frames.append(frame)
    return benchmark_common(
        pd.concat([quarter, *derived_frames], ignore_index=True, sort=False),
        config,
        config_hash,
    )


def build_parent_margin_benchmarks(
    inputs: dict[str, pd.DataFrame], config: dict[str, Any], config_hash: str
) -> pd.DataFrame:
    frame = inputs["parent_country_annual"].copy()
    country = inputs["country_crosswalk"]
    country = country.loc[
        country["source_name"].eq(config["source_name"]) & country["is_country"]
    ].drop_duplicates("country_iso3")
    country = country[["country_iso3", "canonical_country_name"]].rename(
        columns={"country_iso3": "parent_country_iso3", "canonical_country_name": "parent_canonical_country_name"}
    )
    frame = frame.merge(country, on="parent_country_iso3", how="left", validate="many_to_one")
    unknown = frame["parent_country_iso3"].eq("XXA")
    frame["benchmark_scope"] = "parent_country_annual_margin"
    frame["benchmark_record_id"] = "PARENT:" + frame["parent_country_iso3"].astype(str)
    frame["source_panel"] = "parent_country_annual"
    frame["source_parent_country_id"] = frame["parent_country_iso3"]
    frame["source_parent_country_name"] = frame["parent_country_name"]
    frame["parent_country_record_type"] = np.where(
        unknown, "unknown_or_residual_source", "actual_parent_country"
    )
    frame["parent_country_join_eligible"] = ~unknown
    frame["source_sector_level"] = "all_economy"
    frame["source_sector_code"] = "ALL"
    frame["source_sector_label"] = "All economy"
    frame["sector_mapping_status"] = "parent_margin_has_no_sector_dimension"
    frame["sector_is_main_join_eligible"] = False
    frame["analysis_sector"] = "all_economy"
    frame["origin_country_iso3"] = frame["parent_country_iso3"].where(~unknown)
    frame["quarter"] = pd.NA
    frame["period_type"] = "calendar_year"
    frame["period_id"] = frame["year"].astype(str)
    frame["period_start_quarter"] = 1
    frame["period_end_quarter"] = 4
    frame["expected_quarter_count"] = 4
    frame["observed_quarter_count"] = pd.NA
    frame["complete_period_flag"] = True
    frame["annual_comparable_flag"] = True
    frame["h1_comparable_flag"] = False
    frame["partial_year_flag"] = False
    frame["value"] = frame["fdi_million_usd"]
    frame["national_total_flag"] = False
    frame["one_dimensional_margin_flag"] = True
    frame["nonadditive_to_national_flag"] = True
    frame["main_cross_source_join_eligible"] = False
    frame["derivation_status"] = "direct_official_parent_country_annual_margin"
    frame["metric_formula"] = "official_parent_country_annual_fdi_margin"
    frame["source_file"] = frame["source_file"].map(project_relative_source_file)
    return benchmark_common(frame, config, config_hash)


def build_sector_margin_benchmarks(
    inputs: dict[str, pd.DataFrame], config: dict[str, Any], config_hash: str
) -> pd.DataFrame:
    frame = inputs["sector_annual"].copy()
    sector = inputs["source_sector_crosswalk"]
    sector = sector.loc[sector["source_name"].eq(config["source_name"])][
        ["source_sector_level", "source_sector_code", "mapping_status", "is_main_join_eligible"]
    ].rename(
        columns={
            "source_sector_level": "sector_level",
            "source_sector_code": "sector_code",
            "mapping_status": "sector_mapping_status",
            "is_main_join_eligible": "sector_is_main_join_eligible",
        }
    )
    frame = frame.merge(
        sector,
        on=["sector_level", "sector_code"],
        how="left",
        validate="many_to_one",
    )
    frame["sector_mapping_status"] = frame["sector_mapping_status"].fillna(
        "unmapped_annual_margin_nonjoin"
    )
    frame["sector_is_main_join_eligible"] = frame[
        "sector_is_main_join_eligible"
    ].fillna(False)
    frame["benchmark_scope"] = "sector_annual_margin"
    frame["benchmark_record_id"] = "SECTOR:" + frame["sector_code"].astype(str)
    frame["source_panel"] = "sector_annual"
    frame["source_parent_country_id"] = "ALL_FOREIGN_SOURCES"
    frame["source_parent_country_name"] = "All foreign sources"
    frame["parent_country_iso3"] = pd.NA
    frame["parent_canonical_country_name"] = pd.NA
    frame["parent_country_record_type"] = "national_all_sources"
    frame["parent_country_join_eligible"] = False
    frame["source_sector_level"] = frame["sector_level"]
    frame["source_sector_code"] = frame["sector_code"]
    frame["source_sector_label"] = frame["sector_name"]
    frame["analysis_sector"] = "not_applicable_broad_sector"
    frame["origin_country_iso3"] = pd.NA
    frame["quarter"] = pd.NA
    frame["period_type"] = "calendar_year"
    frame["period_id"] = frame["year"].astype(str)
    frame["period_start_quarter"] = 1
    frame["period_end_quarter"] = 4
    frame["expected_quarter_count"] = 4
    frame["observed_quarter_count"] = pd.NA
    frame["complete_period_flag"] = True
    frame["annual_comparable_flag"] = True
    frame["h1_comparable_flag"] = False
    frame["partial_year_flag"] = False
    frame["value"] = frame["fdi_million_usd"]
    frame["national_total_flag"] = False
    frame["one_dimensional_margin_flag"] = True
    frame["nonadditive_to_national_flag"] = True
    frame["main_cross_source_join_eligible"] = False
    frame["derivation_status"] = "direct_official_two_digit_sector_annual_margin"
    frame["metric_formula"] = "official_two_digit_sector_annual_fdi_margin"
    frame["source_file"] = frame["source_file"].map(project_relative_source_file)
    return benchmark_common(frame, config, config_hash)


def build_once(
    output_dir: Path,
    config: dict[str, Any],
    config_hash: str,
    inputs: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    detail = prepare_detail(inputs, config)
    source_spec = config["outputs"]["source_period_long"]
    source_path = output_dir / Path(source_spec["path"]).name
    source_schema = output_schema(config, "source_period_long")
    def source_frames() -> Iterable[pd.DataFrame]:
        yield build_source_quarter(detail, config, config_hash)
        yield build_source_period(
            detail,
            config,
            config_hash,
            period_type="calendar_year",
            quarters=[1, 2, 3, 4],
        )
        yield build_source_period(
            detail,
            config,
            config_hash,
            period_type="h1",
            quarters=[1, 2],
        )

    source_stats = write_frames(source_path, source_schema, source_frames())

    parent_base = prepare_parent_base(detail)
    parent = pd.concat(
        [
            aggregate_parent_period(
                parent_base,
                config,
                config_hash,
                period_type="quarter",
                quarters=[1, 2, 3, 4],
            ),
            aggregate_parent_period(
                parent_base,
                config,
                config_hash,
                period_type="calendar_year",
                quarters=[1, 2, 3, 4],
            ),
            aggregate_parent_period(
                parent_base,
                config,
                config_hash,
                period_type="h1",
                quarters=[1, 2],
            ),
        ],
        ignore_index=True,
        sort=False,
    )
    parent_spec = config["outputs"]["parent_sector_period_long"]
    parent_path = output_dir / Path(parent_spec["path"]).name
    parent_schema = output_schema(config, "parent_sector_period_long")
    parent = parent.sort_values(parent_spec["natural_key"], kind="mergesort").reset_index(drop=True)
    parent_stats = write_frames(parent_path, parent_schema, [parent])

    benchmark = pd.concat(
        [
            build_national_benchmarks(inputs, config, config_hash),
            build_parent_margin_benchmarks(inputs, config, config_hash),
            build_sector_margin_benchmarks(inputs, config, config_hash),
        ],
        ignore_index=True,
        sort=False,
    )
    benchmark_spec = config["outputs"]["benchmark_period_long"]
    benchmark_path = output_dir / Path(benchmark_spec["path"]).name
    benchmark_schema = output_schema(config, "benchmark_period_long")
    benchmark = benchmark.sort_values(
        benchmark_spec["natural_key"], kind="mergesort"
    ).reset_index(drop=True)
    benchmark_stats = write_frames(benchmark_path, benchmark_schema, [benchmark])
    return {
        "source_period_long": {"path": source_path, **source_stats},
        "parent_sector_period_long": {"path": parent_path, **parent_stats},
        "benchmark_period_long": {"path": benchmark_path, **benchmark_stats},
    }


def validate_inputs(
    project_root: Path,
    config: dict[str, Any],
    inputs: dict[str, pd.DataFrame],
    audits: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    for input_id, spec in config["inputs"].items():
        if input_id == "build_summary":
            continue
        audit = audits[input_id]
        add_check(validation, f"input_{input_id}_sha256", audit["sha256"] == spec["sha256"], audit)
        add_check(
            validation,
            f"input_{input_id}_shape",
            audit["rows"] == spec["expected_rows"] and audit["columns"] == spec["expected_columns"],
            audit,
        )
        add_check(
            validation,
            f"input_{input_id}_schema_signature",
            audit["schema_signature"] == spec["arrow_schema_signature_sha256"],
            audit,
        )
        add_check(
            validation,
            f"input_{input_id}_key",
            audit["duplicate_key_rows"] == 0 and audit["missing_key_cells"] == 0,
            audit,
        )
        if "filter_source_name" in spec:
            filtered = inputs[input_id].loc[
                inputs[input_id]["source_name"].eq(spec["filter_source_name"])
            ]
            add_check(
                validation,
                f"input_{input_id}_filtered_rows",
                len(filtered) == spec["expected_filtered_rows"],
                len(filtered),
            )
        if "filter_input_id" in spec:
            filtered = inputs[input_id].loc[
                inputs[input_id]["input_id"].eq(spec["filter_input_id"])
            ]
            add_check(
                validation,
                f"input_{input_id}_filtered_rows",
                len(filtered) == spec["expected_filtered_rows"],
                len(filtered),
            )

    build_spec = config["inputs"]["build_summary"]
    build_path = project_root / build_spec["path"]
    add_check(
        validation,
        "input_build_summary_sha256",
        sha256(build_path) == build_spec["sha256"],
        sha256(build_path),
    )
    summary = json.loads(build_path.read_text(encoding="utf-8"))
    source_count = len(summary["sources"])
    add_check(
        validation,
        "build_summary_source_count",
        source_count == build_spec["expected_source_count"],
        source_count,
    )
    raw_checks = []
    for source_id, item in summary["sources"].items():
        raw_path = project_root / str(item["path"]).replace("\\", "/")
        raw_checks.append(
            {
                "source_id": source_id,
                "exists": raw_path.is_file(),
                "bytes_match": raw_path.is_file() and raw_path.stat().st_size == item["bytes"],
                "hash_match": raw_path.is_file() and sha256(raw_path) == item["sha256"],
            }
        )
    add_check(
        validation,
        "raw_sources_exist_size_hash",
        len(raw_checks) == config["validation"]["expected_raw_source_count"]
        and all(item["exists"] and item["bytes_match"] and item["hash_match"] for item in raw_checks),
        raw_checks,
    )
    output_hash_checks = {}
    for input_id in [key for key in config["inputs"] if key not in {"build_summary", "country_crosswalk", "source_sector_crosswalk", "time_aggregation_rules"}]:
        filename = Path(config["inputs"][input_id]["path"]).name
        output_hash_checks[input_id] = summary["output_hashes"].get(filename) == audits[input_id]["sha256"]
    add_check(
        validation,
        "build_summary_output_hashes_match_inputs",
        all(output_hash_checks.values()),
        output_hash_checks,
    )


def validate_source_data(
    config: dict[str, Any],
    inputs: dict[str, pd.DataFrame],
    validation: dict[str, Any],
) -> pd.DataFrame:
    detail = prepare_detail(inputs, config)
    cfg = config["validation"]
    add_check(
        validation,
        "detail_country_crosswalk_join",
        detail["_country_merge"].eq("both").all(),
        detail["_country_merge"].value_counts().to_dict(),
    )
    add_check(
        validation,
        "detail_sector_crosswalk_join",
        detail["_sector_merge"].eq("both").all(),
        detail["_sector_merge"].value_counts().to_dict(),
    )
    embedded_match = (
        detail.loc[detail["parent_country_is_country"], "embedded_parent_country_iso3"]
        .eq(detail.loc[detail["parent_country_is_country"], "parent_country_iso3"])
        .all()
    )
    add_check(validation, "detail_embedded_country_iso_matches_crosswalk", embedded_match, embedded_match)
    scaling_gaps = {}
    for input_id in USED_PANEL_IDS:
        frame = inputs[input_id]
        scaling_gaps[input_id] = max_abs(
            frame["fdi_usd"] - frame["fdi_million_usd"] * 1_000_000.0
        )
    add_check(
        validation,
        "input_usd_scaling_identity",
        max(scaling_gaps.values()) <= cfg["usd_scaling_tolerance"],
        scaling_gaps,
    )
    conf_identity = (
        detail["confidential_flag"].eq(detail["fdi_million_usd"].isna()).all()
        and detail["confidential_flag"].eq(detail["fdi_usd"].isna()).all()
    )
    add_check(validation, "detail_confidential_missing_identity", conf_identity, conf_identity)
    period_counts = detail.groupby(["year", "quarter"]).size()
    structural_key = ["parent_country_name", "sector_level", "sector_code"]
    first_keys = set(map(tuple, detail.loc[(detail["year"] == 2006) & (detail["quarter"] == 1), structural_key].itertuples(index=False, name=None)))
    all_same = True
    for _, frame in detail.groupby(["year", "quarter"], sort=False):
        if set(map(tuple, frame[structural_key].itertuples(index=False, name=None))) != first_keys:
            all_same = False
            break
    add_check(
        validation,
        "detail_quarter_structure_universe",
        len(period_counts) == cfg["expected_detail_quarters"]
        and period_counts.eq(cfg["expected_detail_rows_per_quarter"]).all()
        and len(first_keys) == cfg["expected_detail_structure_key_count"]
        and all_same,
        {"periods": len(period_counts), "min": int(period_counts.min()), "max": int(period_counts.max()), "structure_keys": len(first_keys), "all_same": all_same},
    )
    years = detail.groupby("year")["quarter"].apply(lambda values: sorted(values.unique().tolist())).to_dict()
    coverage_pass = all(years[year] == [1, 2, 3, 4] for year in range(2006, 2024)) and years[2024] == [1, 2]
    add_check(validation, "detail_calendar_coverage", coverage_pass, years)
    counts = {
        "countries": int(detail["parent_country_is_country"].groupby(detail["source_parent_country_id"]).first().sum()),
        "residual_labels": int(detail.loc[detail["parent_country_is_residual"], "source_parent_country_id"].nunique()),
        "confidential": int(detail["confidential_flag"].sum()),
        "residual": int(detail["parent_country_residual_flag"].sum()),
        "total": int(detail["parent_country_total_flag"].sum()),
        "negative": int(detail["fdi_million_usd"].lt(0).sum()),
        "zero": int(detail["fdi_million_usd"].eq(0).sum()),
    }
    expected = {
        "countries": cfg["expected_detail_country_count"],
        "residual_labels": cfg["expected_detail_residual_label_count"],
        "confidential": cfg["expected_detail_confidential_rows"],
        "residual": cfg["expected_detail_residual_rows"],
        "total": cfg["expected_detail_total_rows"],
        "negative": cfg["expected_detail_negative_rows"],
        "zero": cfg["expected_detail_zero_rows"],
    }
    add_check(validation, "detail_quality_snapshot", counts == expected, {"actual": counts, "expected": expected})
    level_rows = detail.groupby("sector_level").size().to_dict()
    level_codes = detail.groupby("sector_level")["sector_code"].nunique().to_dict()
    add_check(
        validation,
        "detail_sector_level_snapshot",
        level_rows == cfg["expected_sector_level_rows"] and level_codes == cfg["expected_sector_level_codes"],
        {"rows": level_rows, "codes": level_codes},
    )
    eligible = prepare_parent_base(detail)
    eligible_counts = {
        "rows": len(eligible),
        "actual": int(eligible["parent_country_is_country"].sum()),
        "residual": int(eligible["parent_country_is_residual"].sum()),
        "confidential": int(eligible["confidential_flag"].sum()),
        "negative": int(eligible["fdi_million_usd"].lt(0).sum()),
    }
    eligible_expected = {
        "rows": cfg["expected_eligible_rows"],
        "actual": cfg["expected_eligible_actual_rows"],
        "residual": cfg["expected_eligible_residual_rows"],
        "confidential": cfg["expected_eligible_confidential_rows"],
        "negative": cfg["expected_eligible_negative_rows"],
    }
    add_check(validation, "eligible_detail_snapshot", eligible_counts == eligible_expected, {"actual": eligible_counts, "expected": eligible_expected})
    code_counts = eligible.groupby("analysis_sector")["sector_code"].nunique().to_dict()
    add_check(
        validation,
        "eligible_analysis_sector_code_counts",
        code_counts == cfg["expected_analysis_sector_code_counts"],
        code_counts,
    )
    support_count = len(parent_support(eligible))
    add_check(
        validation,
        "parent_sector_published_support_count",
        support_count == cfg["expected_parent_sector_support_count"],
        support_count,
    )
    return detail


def read_output(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(path, columns=columns)


def validate_outputs(
    config: dict[str, Any],
    built: dict[str, Any],
    inputs: dict[str, pd.DataFrame],
    validation: dict[str, Any],
) -> None:
    cfg = config["validation"]
    outputs = {}
    for output_id, spec in config["outputs"].items():
        item = built[output_id]
        parquet = pq.ParquetFile(item["path"])
        schema = parquet.schema_arrow
        key = spec["natural_key"]
        key_frame = read_output(item["path"], key)
        shape_pass = parquet.metadata.num_rows == spec["expected_rows"] and len(schema) == spec["expected_columns"]
        key_pass = not key_frame.duplicated(key).any() and not key_frame[key].isna().any().any()
        add_check(validation, f"output_{output_id}_shape", shape_pass, {"rows": parquet.metadata.num_rows, "columns": len(schema)})
        add_check(validation, f"output_{output_id}_key", key_pass, {"duplicates": int(key_frame.duplicated(key).sum()), "missing_key_cells": int(key_frame[key].isna().sum().sum())})
        aliases = alias_validation(schema, spec["stata_aliases"])
        add_check(validation, f"output_{output_id}_stata_aliases", aliases["pass"], aliases)
        outputs[output_id] = {
            "path": spec["path"],
            "sha256": sha256(item["path"]),
            "rows": parquet.metadata.num_rows,
            "columns": len(schema),
            "schema_signature": schema_signature(schema),
        }

    source = read_output(
        built["source_period_long"]["path"],
        ["source_parent_country_id", "source_sector_level", "source_sector_code", "year", "quarter", "period_type", "observed_quarter_count", "complete_period_flag", "value", "source_disclosed_value_sum", "value_available_flag", "confidential_flag", "observed_negative_flag", "reported_zero_flag", "parent_country_residual_flag"],
    )
    source_rows = source.groupby("period_type").size().to_dict()
    source_available = source.groupby("period_type")["value_available_flag"].sum().astype(int).to_dict()
    add_check(validation, "source_period_row_counts", source_rows == cfg["expected_source_period_rows"], source_rows)
    add_check(validation, "source_period_available_counts", source_available == cfg["expected_source_period_available"], source_available)
    incomplete_2024 = source.loc[(source["year"] == 2024) & source["period_type"].eq("calendar_year")]
    source_2024_pass = (
        len(incomplete_2024) == cfg["expected_source_period_incomplete_calendar_rows_2024"]
        and not incomplete_2024["complete_period_flag"].any()
        and not incomplete_2024["value_available_flag"].any()
    )
    add_check(validation, "source_2024_annual_explicit_unavailable", source_2024_pass, {"rows": len(incomplete_2024), "complete": int(incomplete_2024["complete_period_flag"].sum()), "available": int(incomplete_2024["value_available_flag"].sum())})
    detail = inputs["country_sector_quarterly"]
    source_identity = {
        "quarter_negative": int(source.loc[source["period_type"].eq("quarter"), "observed_negative_flag"].sum()),
        "quarter_zero": int(source.loc[source["period_type"].eq("quarter"), "reported_zero_flag"].sum()),
        "quarter_confidential": int(source.loc[source["period_type"].eq("quarter"), "confidential_flag"].sum()),
        "quarter_residual": int(source.loc[source["period_type"].eq("quarter"), "parent_country_residual_flag"].sum()),
    }
    source_identity_expected = {
        "quarter_negative": int(detail["fdi_million_usd"].lt(0).sum()),
        "quarter_zero": int(detail["fdi_million_usd"].eq(0).sum()),
        "quarter_confidential": int(detail["confidential_flag"].sum()),
        "quarter_residual": int(detail["parent_country_residual_flag"].sum()),
    }
    add_check(validation, "source_quarter_identity", source_identity == source_identity_expected, {"actual": source_identity, "expected": source_identity_expected})

    prepared_detail = prepare_detail(inputs, config)
    for period_type, quarters in (("calendar_year", [1, 2, 3, 4]), ("h1", [1, 2])):
        subset = prepared_detail.loc[prepared_detail["quarter"].isin(quarters)]
        reference = subset.groupby(
            ["source_parent_country_id", "sector_level", "sector_code", "year"],
            dropna=False,
            sort=True,
        ).agg(
            reference_observed_quarter_count=("quarter", "nunique"),
            reference_source_row_count=("quarter", "size"),
            reference_confidential_count=("confidential_flag", "sum"),
            reference_disclosed_sum=("fdi_million_usd", lambda values: values.sum(min_count=1)),
        ).reset_index()
        reference["reference_complete"] = (
            reference["reference_observed_quarter_count"].eq(len(quarters))
            & reference["reference_source_row_count"].eq(len(quarters))
        )
        reference["reference_value_available"] = (
            reference["reference_complete"]
            & reference["reference_confidential_count"].eq(0)
        )
        reference["reference_value"] = reference["reference_disclosed_sum"].where(
            reference["reference_value_available"]
        )
        output_slice = source.loc[source["period_type"].eq(period_type)]
        merged = output_slice.merge(
            reference,
            left_on=["source_parent_country_id", "source_sector_level", "source_sector_code", "year"],
            right_on=["source_parent_country_id", "sector_level", "sector_code", "year"],
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        source_recompute = {
            "rows": len(merged),
            "merge_counts": merged["_merge"].value_counts().to_dict(),
            "strict_value_max_gap": max_abs(merged["value"] - merged["reference_value"]),
            "disclosed_sum_max_gap": max_abs(
                merged["source_disclosed_value_sum"] - merged["reference_disclosed_sum"]
            ),
            "value_missing_match": bool(
                merged["value"].isna().eq(merged["reference_value"].isna()).all()
            ),
            "available_count": int(merged["reference_value_available"].sum()),
        }
        source_recompute_pass = (
            merged["_merge"].eq("both").all()
            and merged["value"].isna().eq(merged["reference_value"].isna()).all()
            and source_recompute["strict_value_max_gap"] <= cfg["numeric_tolerance_million_usd"]
            and source_recompute["disclosed_sum_max_gap"] <= cfg["numeric_tolerance_million_usd"]
            and merged["complete_period_flag"].eq(merged["reference_complete"]).all()
            and merged["value_available_flag"].eq(merged["reference_value_available"]).all()
        )
        add_check(
            validation,
            f"source_{period_type}_independent_recompute",
            source_recompute_pass,
            source_recompute,
        )

    parent = read_output(
        built["parent_sector_period_long"]["path"],
        ["year", "quarter", "period_type", "value", "source_disclosed_value_sum", "complete_period_flag", "value_available_flag", "confidential_flag", "source_confidential_cell_count", "source_parent_country_id", "analysis_sector", "parent_country_is_residual", "main_cross_source_join_eligible", "reported_zero_flag", "exact_zero_flag", "cancellation_to_zero_flag", "observed_negative_flag"],
    )
    parent_rows = parent.groupby("period_type").size().to_dict()
    parent_available = parent.groupby("period_type")["value_available_flag"].sum().astype(int).to_dict()
    add_check(validation, "parent_sector_period_row_counts", parent_rows == cfg["expected_parent_sector_period_rows"], parent_rows)
    add_check(validation, "parent_sector_period_available_counts", parent_available == cfg["expected_parent_sector_available"], parent_available)
    parent_2024 = parent.loc[(parent["year"] == 2024) & parent["period_type"].eq("calendar_year")]
    add_check(validation, "parent_2024_annual_explicit_unavailable", len(parent_2024) == cfg["expected_parent_sector_support_count"] and not parent_2024["complete_period_flag"].any() and parent_2024["value"].isna().all(), {"rows": len(parent_2024), "complete": int(parent_2024["complete_period_flag"].sum()), "nonmissing": int(parent_2024["value"].notna().sum())})
    parent_logic = (
        parent["value_available_flag"].eq(parent["value"].notna()).all()
        and parent.loc[parent["confidential_flag"], "value"].isna().all()
        and not parent["main_cross_source_join_eligible"].any()
        and not parent["cancellation_to_zero_flag"].any()
    )
    add_check(validation, "parent_sector_value_and_scope_logic", parent_logic, {"strict_nonmissing": int(parent["value"].notna().sum()), "strict_negative": int(parent["observed_negative_flag"].sum()), "strict_zero": int(parent["reported_zero_flag"].sum()), "exact_zero": int(parent["exact_zero_flag"].sum()), "cancellation_zero": int(parent["cancellation_to_zero_flag"].sum()), "residual_rows": int(parent["parent_country_is_residual"].sum())})

    parent_base = prepare_parent_base(prepared_detail)
    support = parent_support(parent_base)
    for period_type, quarters in (("quarter", [1, 2, 3, 4]), ("calendar_year", [1, 2, 3, 4]), ("h1", [1, 2])):
        subset = parent_base.loc[parent_base["quarter"].isin(quarters)]
        group_key = ["source_parent_country_id", "analysis_sector", "year"]
        if period_type == "quarter":
            group_key.append("quarter")
        reference = subset.groupby(group_key, dropna=False, sort=True).agg(
            reference_observed_quarter_count=("quarter", "nunique"),
            reference_observed_source_industry_count=("sector_code", "nunique"),
            reference_source_row_count=("sector_code", "size"),
            reference_confidential_count=("confidential_flag", "sum"),
            reference_disclosed_sum=("fdi_million_usd", lambda values: values.sum(min_count=1)),
        ).reset_index()
        reference = reference.merge(
            support,
            on=["source_parent_country_id", "analysis_sector"],
            how="left",
            validate="many_to_one",
        )
        required_quarters = 1 if period_type == "quarter" else len(quarters)
        reference["reference_complete"] = (
            reference["reference_observed_quarter_count"].eq(required_quarters)
            & reference["reference_observed_source_industry_count"].eq(
                reference["published_source_industry_count"]
            )
            & reference["reference_source_row_count"].eq(
                reference["published_source_industry_count"] * required_quarters
            )
        )
        reference["reference_value_available"] = (
            reference["reference_complete"]
            & reference["reference_confidential_count"].eq(0)
        )
        reference["reference_value"] = reference["reference_disclosed_sum"].where(
            reference["reference_value_available"]
        )
        output_slice = parent.loc[parent["period_type"].eq(period_type)]
        left_key = ["source_parent_country_id", "analysis_sector", "year"]
        if period_type == "quarter":
            left_key.append("quarter")
        merged = output_slice.merge(
            reference,
            on=left_key,
            how="outer",
            validate="one_to_one",
            indicator=True,
        )
        parent_recompute = {
            "rows": len(merged),
            "merge_counts": merged["_merge"].value_counts().to_dict(),
            "strict_value_max_gap": max_abs(merged["value"] - merged["reference_value"]),
            "disclosed_sum_max_gap": max_abs(
                merged["source_disclosed_value_sum"] - merged["reference_disclosed_sum"]
            ),
            "value_missing_match": bool(
                merged["value"].isna().eq(merged["reference_value"].isna()).all()
            ),
            "available_count": int(merged["reference_value_available"].sum()),
        }
        parent_recompute_pass = (
            merged["_merge"].eq("both").all()
            and merged["value"].isna().eq(merged["reference_value"].isna()).all()
            and parent_recompute["strict_value_max_gap"] <= cfg["numeric_tolerance_million_usd"]
            and parent_recompute["disclosed_sum_max_gap"] <= cfg["numeric_tolerance_million_usd"]
            and merged["complete_period_flag"].eq(merged["reference_complete"]).all()
            and merged["value_available_flag"].eq(merged["reference_value_available"]).all()
        )
        add_check(
            validation,
            f"parent_{period_type}_independent_recompute",
            parent_recompute_pass,
            parent_recompute,
        )

    benchmark = read_output(built["benchmark_period_long"]["path"])
    bench_counts = benchmark.groupby("benchmark_scope").size().to_dict()
    add_check(validation, "benchmark_scope_row_counts", bench_counts == cfg["expected_benchmark_rows"], bench_counts)
    national_2024 = benchmark.loc[(benchmark["benchmark_scope"] == "national_total") & (benchmark["year"] == 2024)]
    annual_value = float(national_2024.loc[national_2024["period_type"] == "calendar_year", "value"].iloc[0])
    h1_value = float(national_2024.loc[national_2024["period_type"] == "h1", "value"].iloc[0])
    add_check(validation, "national_2024_values", abs(annual_value - cfg["expected_national_2024_annual_million_usd"]) <= cfg["numeric_tolerance_million_usd"] and abs(h1_value - cfg["expected_national_2024_h1_million_usd"]) <= cfg["numeric_tolerance_million_usd"], {"annual": annual_value, "h1": h1_value})
    unknown_rows = benchmark.loc[(benchmark["benchmark_scope"] == "parent_country_annual_margin") & (benchmark["parent_country_record_type"] == "unknown_or_residual_source")]
    unmapped_codes = sorted(benchmark.loc[(benchmark["benchmark_scope"] == "sector_annual_margin") & (benchmark["sector_mapping_status"] == "unmapped_annual_margin_nonjoin"), "source_sector_code"].unique().tolist())
    add_check(validation, "benchmark_unknown_and_unmapped_isolation", len(unknown_rows) == cfg["expected_parent_margin_unknown_rows"] and unmapped_codes == cfg["expected_sector_margin_unmapped_codes"] and not unknown_rows["parent_country_join_eligible"].any(), {"unknown_rows": len(unknown_rows), "unmapped_codes": unmapped_codes})

    national = inputs["national_quarterly"]
    by_type = inputs["national_investment_type_quarterly"].groupby(["year", "quarter"])["fdi_million_usd"].sum().rename("type_sum").reset_index()
    national_type = national.merge(by_type, on=["year", "quarter"], validate="one_to_one")
    type_gap = max_abs(national_type["fdi_million_usd"] - national_type["type_sum"])
    national_annual = national.groupby("year")["fdi_million_usd"].sum()
    parent_annual = inputs["parent_country_annual"].groupby("year")["fdi_million_usd"].sum()
    sector_annual = inputs["sector_annual"].groupby("year")["fdi_million_usd"].sum()
    parent_gap = max_abs(national_annual - parent_annual)
    sector_gap = max_abs(national_annual - sector_annual)
    reconciliation = {
        "national_type_max_gap_million_usd": type_gap,
        "parent_margin_max_gap_million_usd": parent_gap,
        "sector_margin_max_gap_million_usd": sector_gap,
    }
    rec_pass = (
        type_gap <= cfg["national_type_reconciliation_tolerance_million_usd"]
        and abs(parent_gap - cfg["expected_parent_margin_max_gap_million_usd"]) <= cfg["numeric_tolerance_million_usd"]
        and abs(sector_gap - cfg["expected_sector_margin_max_gap_million_usd"]) <= cfg["numeric_tolerance_million_usd"]
    )
    add_check(validation, "national_and_margin_reconciliation", rec_pass, reconciliation)
    validation["reconciliation"] = reconciliation
    validation["outputs"] = outputs


def validate_candidate(
    project_root: Path,
    config_path: Path,
    config: dict[str, Any],
    config_hash: str,
    inputs: dict[str, pd.DataFrame],
    audits: dict[str, Any],
    built: dict[str, Any],
) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "validation_status": "PENDING",
        "failures": [],
        "checks": [],
        "validation_version": "production_mexico_fdi_validation_v1",
        "origin_date": config["origin_date"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path.relative_to(project_root).as_posix(),
        "config_sha256": config_hash,
        "construction_version": config["construction_version"],
        "interpretation_contract": {
            "host_country": "MEX",
            "parent_role": "reported_parent_or_source_jurisdiction_not_ultimate_owner",
            "metric": "signed_inward_financial_fdi_flow_not_production",
            "confidentiality": "C_remains_missing_and_is_never_zero_imputed",
            "detail_2024": "H1_only_calendar_year_explicitly_unavailable",
            "hierarchy": "sector_subsector_industry_group_never_summed_together",
            "margins": "national_parent_sector_margins_never_outer_product_or_forced_to_reconcile",
        },
    }
    validate_inputs(project_root, config, inputs, audits, validation)
    validate_source_data(config, inputs, validation)
    validate_outputs(config, built, inputs, validation)
    validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    return validation


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# M4.5 Mexico FDI Standardization Validation",
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
    for item in validation.get("outputs", {}).values():
        lines.append(
            f"| `{item['path']}` | {item['rows']:,} | {item['columns']} | `{item['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation contract",
            "",
            "- All values are signed inward financial FDI flows to Mexico, not output, employment, plant entry, or causal relocation.",
            "- Parent country is the reported source/parent jurisdiction, not necessarily the ultimate owner; host country is always Mexico.",
            "- `C` remains missing. Strict period values require all published source components and required quarters to be present and non-confidential.",
            "- 2024 joint detail is H1 only. Calendar-year rows are retained as explicitly incomplete and missing; national 2024 remains a separate full-year benchmark.",
            "- SCIAN sector, subsector, and industry-group rows are overlapping hierarchy levels and are never summed together.",
            "- Parent-country and sector annual margins are one-dimensional references; they are not outer-joined, allocated, or forced to equal the national total.",
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
        "--config", default="configs/production_mexico_fdi_rules.yaml"
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    config_path = (project_root / args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    destinations = {
        output_id: project_root / spec["path"]
        for output_id, spec in config["outputs"].items()
    }
    if not args.overwrite and any(path.exists() for path in destinations.values()):
        raise FileExistsError(
            "Canonical M4.5 output already exists; use --overwrite only after reviewing the frozen config."
        )

    candidate_dir = resolve_temp(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    determinism_dir = resolve_temp(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    token = str(uuid.uuid4())
    create_owned_temp(candidate_dir, token)
    create_owned_temp(determinism_dir, token)
    validation: dict[str, Any] | None = None
    try:
        inputs, audits = read_inputs(project_root, config)
        candidate = build_once(candidate_dir, config, config_hash, inputs)
        validation = validate_candidate(
            project_root,
            config_path,
            config,
            config_hash,
            inputs,
            audits,
            candidate,
        )
        if validation["failures"]:
            write_validation_reports(project_root, config, validation)
            raise RuntimeError(
                f"M4.5 validation failed with {len(validation['failures'])} failure(s); canonical outputs were not replaced."
            )
        second = build_once(determinism_dir, config, config_hash, inputs)
        determinism: dict[str, Any] = {}
        for output_id in config["outputs"]:
            candidate_hash = sha256(candidate[output_id]["path"])
            second_hash = sha256(second[output_id]["path"])
            passed = candidate_hash == second_hash
            add_check(
                validation,
                f"deterministic_{output_id}_sha256",
                passed,
                {"candidate": candidate_hash, "second_build": second_hash},
            )
            determinism[output_id] = {
                "candidate_sha256": candidate_hash,
                "second_build_sha256": second_hash,
                "sha256_match": passed,
            }
        validation["determinism"] = determinism
        validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
        if validation["failures"]:
            write_validation_reports(project_root, config, validation)
            raise RuntimeError(
                f"M4.5 deterministic validation failed with {len(validation['failures'])} failure(s); canonical outputs were not replaced."
            )
        for output_id, destination in destinations.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate[output_id]["path"], destination)
            passed = sha256(destination) == validation["outputs"][output_id]["sha256"]
            add_check(
                validation,
                f"canonical_{output_id}_hash_matches_candidate",
                passed,
                sha256(destination),
            )
        validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    finally:
        remove_owned_temp(candidate_dir, token)
        remove_owned_temp(determinism_dir, token)

    assert validation is not None
    temp_cleaned = not candidate_dir.exists() and not determinism_dir.exists()
    validation["determinism"]["temporary_output_cleaned"] = temp_cleaned
    add_check(validation, "temporary_output_cleaned", temp_cleaned, temp_cleaned)
    validation["validation_status"] = "PASS" if not validation["failures"] else "FAIL"
    write_validation_reports(project_root, config, validation)
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "check_count": len(validation["checks"]),
                "failure_count": len(validation["failures"]),
                "outputs": validation["outputs"],
                "determinism": validation["determinism"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
