from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml


SOURCE_KEY = ["year", "host_country_iso3", "parent_country_iso3", "sector_oecd"]
PARENT_LONG_KEY = [
    "source_name",
    "source_host_country_id",
    "source_parent_country_id",
    "model_sector",
    "year",
    "metric_name",
]
HOST_LONG_KEY = [
    "country_iso3",
    "analysis_sector",
    "year",
    "source_name",
    "metric_name",
]
HOST_SOURCE_KEY = ["year", "host_country_iso3", "sector_oecd"]


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


def max_abs(values: pd.Series | np.ndarray) -> float:
    array = np.asarray(values, dtype="float64")
    finite = np.isfinite(array)
    return float(np.max(np.abs(array[finite]))) if finite.any() else 0.0


def join_unique_text(values: pd.Series) -> object:
    unique = sorted({str(value) for value in values.dropna() if str(value).strip()})
    return ";".join(unique) if unique else pd.NA


def schema_from_aliases(
    aliases: dict[str, str],
    *,
    bool_fields: set[str],
    int8_fields: set[str],
    int16_fields: set[str],
    float_fields: set[str],
) -> pa.Schema:
    fields: list[pa.Field] = []
    for column in aliases:
        if column in bool_fields:
            dtype = pa.bool_()
        elif column in int8_fields:
            dtype = pa.int8()
        elif column in int16_fields:
            dtype = pa.int16()
        elif column in float_fields:
            dtype = pa.float64()
        else:
            dtype = pa.string()
        fields.append(pa.field(column, dtype))
    return pa.schema(fields)


def parent_long_schema(config: dict[str, Any]) -> pa.Schema:
    bool_fields = {
        "host_is_country",
        "host_is_aggregate",
        "host_is_residual",
        "host_is_proxy",
        "host_main_analysis_country_flag",
        "host_is_core_connector",
        "host_is_asian_comparator",
        "host_is_other_candidate",
        "host_comparison_sample_country_flag",
        "parent_is_country",
        "parent_is_aggregate",
        "parent_is_residual",
        "parent_is_proxy",
        "parent_country_join_eligible",
        "sector_is_main_join_eligible",
        "value_available_flag",
        "metric_unavailable_flag",
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_parents",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
        "host_total_repeated_across_parents_flag",
        "positive_affiliate_output_link_flag",
        "zero_affiliate_output_links_materialized_flag",
    }
    return schema_from_aliases(
        config["outputs"]["parent_long"]["stata_aliases"],
        bool_fields=bool_fields,
        int8_fields={"metric_order"},
        int16_fields={"year"},
        float_fields={"value", "sector_mapping_weight", "allocation_weight"},
    )


def host_long_schema(config: dict[str, Any]) -> pa.Schema:
    bool_fields = {
        "value_available_flag",
        "share_defined_flag",
        "denominator_zero_flag",
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "aggregate_parent_included_flag",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
        "analysis_sector_is_direct_from_one_source_sector",
        "analysis_sector_aggregates_multiple_source_sectors",
        "reconciliation_value_repeated_across_metrics_flag",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
    }
    int16_fields = {
        "year",
        "source_sector_count",
        "source_parent_count",
        "actual_parent_count",
        "aggregate_parent_count",
        "positive_parent_link_count",
        "source_negative_cell_count",
        "source_zero_cell_count",
        "source_missing_cell_count",
    }
    return schema_from_aliases(
        config["outputs"]["host_long"]["stata_aliases"],
        bool_fields=bool_fields,
        int8_fields={"metric_order"},
        int16_fields=int16_fields,
        float_fields={"value", "mapped_parent_output_share", "bilateral_xvem_output_gap"},
    )


def alias_validation(schema: pa.Schema, aliases: dict[str, str]) -> dict[str, Any]:
    fields = set(schema.names)
    missing = sorted(fields - set(aliases))
    extra = sorted(set(aliases) - fields)
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


def read_inputs(project_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    activity_path = project_root / config["inputs"]["affiliate_activity"]["path"]
    mp_path = project_root / config["inputs"]["mp_shares"]["path"]
    sector_path = project_root / config["inputs"]["source_sector_crosswalk"]["path"]
    country_path = project_root / config["inputs"]["country_crosswalk"]["path"]
    activity_table = pq.read_table(activity_path)
    mp_columns = [
        "year",
        "host_country_iso3",
        "parent_country_iso3",
        "sector_oecd",
        "affiliate_output",
        "affiliate_value_added",
        "affiliate_employment",
        "affiliate_exports",
        "affiliate_imports",
        "ownership_type",
        "gross_output",
        "foreign_affiliate_output_total",
        "parent_affiliate_output_share",
        "foreign_affiliate_share",
        "source_file",
    ]
    mp_table = pq.read_table(mp_path, columns=mp_columns)
    sector_table = pq.read_table(sector_path)
    country_table = pq.read_table(country_path)
    return {
        "activity": activity_table.to_pandas(),
        "activity_schema": pq.read_schema(activity_path),
        "mp": mp_table.to_pandas(),
        "mp_schema": pq.read_schema(mp_path),
        "sectors": sector_table.to_pandas(),
        "sector_schema": sector_table.schema,
        "countries": country_table.to_pandas(),
        "country_schema": country_table.schema,
    }


def input_contract(
    project_root: Path, config: dict[str, Any], inputs: dict[str, Any]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    frame_names = {
        "affiliate_activity": ("activity", "activity_schema"),
        "mp_shares": ("mp", "mp_schema"),
        "source_sector_crosswalk": ("sectors", "sector_schema"),
        "country_crosswalk": ("countries", "country_schema"),
    }
    for name, (frame_name, schema_name) in frame_names.items():
        spec = config["inputs"][name]
        path = project_root / spec["path"]
        frame = inputs[frame_name]
        schema = inputs[schema_name]
        result[name] = {
            "path": spec["path"],
            "sha256": sha256(path),
            "expected_sha256": spec["sha256"],
            "hash_match": sha256(path) == spec["sha256"],
            "rows": int(len(frame)),
            "expected_rows": int(spec["expected_rows"]),
            "row_count_match": len(frame) == int(spec["expected_rows"]),
            "columns": int(len(schema)),
            "expected_columns": int(spec["expected_columns"]),
            "column_count_match": len(schema) == int(spec["expected_columns"]),
            "schema_signature": schema_signature(schema),
            "expected_schema_signature": spec["arrow_schema_signature_sha256"],
            "schema_match": schema_signature(schema)
            == spec["arrow_schema_signature_sha256"],
        }
        natural_key = spec.get("natural_key")
        if natural_key:
            filtered = frame
            source_filter = spec.get("source_filter")
            if source_filter is not None:
                filtered = filtered.loc[filtered["source_name"].eq(source_filter)]
            result[name].update(
                {
                    "filtered_rows": int(len(filtered)),
                    "expected_filtered_rows": spec.get("expected_filtered_rows"),
                    "key_missing_rows": int(filtered[natural_key].isna().any(axis=1).sum()),
                    "duplicate_key_rows": int(filtered.duplicated(natural_key, keep=False).sum()),
                }
            )
    summary_spec = config["inputs"]["build_summary"]
    summary_path = project_root / summary_spec["path"]
    result["build_summary"] = {
        "path": summary_spec["path"],
        "sha256": sha256(summary_path),
        "expected_sha256": summary_spec["sha256"],
        "hash_match": sha256(summary_path) == summary_spec["sha256"],
    }
    return result


def country_subset(countries: pd.DataFrame, source_name: str) -> pd.DataFrame:
    subset = countries.loc[countries["source_name"].eq(source_name)].copy()
    return subset.sort_values("source_country_id", kind="mergesort").reset_index(drop=True)


def sector_subset(sectors: pd.DataFrame, source_name: str) -> pd.DataFrame:
    subset = sectors.loc[sectors["source_name"].eq(source_name)].copy()
    return subset.sort_values("source_sector_code", kind="mergesort").reset_index(drop=True)


def prepare_parent_base(
    activity: pd.DataFrame,
    sectors: pd.DataFrame,
    countries: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    source_crosswalk_name = config["source_contract"]["source_crosswalk_name"]
    country = country_subset(countries, source_crosswalk_name)
    sector = sector_subset(sectors, source_crosswalk_name)
    host = country.rename(
        columns={
            "source_country_id": "source_host_country_id",
            "country_iso3": "host_country_iso3_canonical",
            "canonical_country_name": "host_canonical_country_name",
            "mapping_status": "host_mapping_status",
            "is_country": "host_is_country",
            "is_aggregate": "host_is_aggregate",
            "is_residual": "host_is_residual",
            "is_proxy": "host_is_proxy",
            "is_core_connector": "host_is_core_connector",
            "is_asian_comparator": "host_is_asian_comparator",
            "is_other_candidate": "host_is_other_candidate",
        }
    )[
        [
            "source_host_country_id",
            "host_country_iso3_canonical",
            "host_canonical_country_name",
            "host_mapping_status",
            "host_is_country",
            "host_is_aggregate",
            "host_is_residual",
            "host_is_proxy",
            "host_is_core_connector",
            "host_is_asian_comparator",
            "host_is_other_candidate",
        ]
    ]
    parent = country.rename(
        columns={
            "source_country_id": "source_parent_country_id",
            "country_iso3": "parent_country_iso3",
            "canonical_country_name": "parent_canonical_country_name",
            "mapping_status": "parent_mapping_status",
            "is_country": "parent_is_country",
            "is_aggregate": "parent_is_aggregate",
            "is_residual": "parent_is_residual",
            "is_proxy": "parent_is_proxy",
        }
    )[
        [
            "source_parent_country_id",
            "parent_country_iso3",
            "parent_canonical_country_name",
            "parent_mapping_status",
            "parent_is_country",
            "parent_is_aggregate",
            "parent_is_residual",
            "parent_is_proxy",
        ]
    ]
    sector = sector.rename(
        columns={
            "source_sector_code": "model_sector",
            "source_sector_label": "source_sector_label",
            "mapping_status": "sector_mapping_status",
            "mapping_rule": "sector_mapping_rule",
            "first_round_exclusion": "sector_first_round_exclusion",
            "proxy_analysis_sector": "sector_proxy_analysis_sector",
            "is_main_join_eligible": "sector_is_main_join_eligible",
            "mapping_weight": "sector_mapping_weight",
            "mapping_version": "source_sector_mapping_version",
        }
    )
    sector_columns = [
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
    ]
    base = activity.rename(
        columns={
            "host_country_iso3": "source_host_country_id",
            "parent_country_iso3": "source_parent_country_id",
            "sector_oecd": "model_sector",
        }
    ).copy()
    base = base.merge(host, on="source_host_country_id", how="left", validate="many_to_one")
    base = base.merge(parent, on="source_parent_country_id", how="left", validate="many_to_one")
    base = base.merge(sector[sector_columns], on="model_sector", how="left", validate="many_to_one")
    base["host_country_iso3"] = base["host_country_iso3_canonical"]
    base = base.drop(columns=["host_country_iso3_canonical"])
    base["host_main_analysis_country_flag"] = base["host_is_country"].fillna(False)
    base["host_comparison_sample_country_flag"] = (
        base[["host_is_core_connector", "host_is_asian_comparator", "host_is_other_candidate"]]
        .fillna(False)
        .any(axis=1)
    )
    base["parent_country_join_eligible"] = base["parent_is_country"].fillna(False)
    base["main_analysis_join_eligible"] = (
        base["host_is_country"].fillna(False)
        & base["sector_is_main_join_eligible"].fillna(False)
        & base["sector_mapping_weight"].eq(1.0)
    )
    base["aggregate_flag"] = base["host_is_aggregate"].fillna(False) | base[
        "parent_is_aggregate"
    ].fillna(False)
    base["residual_flag"] = base["host_is_residual"].fillna(False) | base[
        "parent_is_residual"
    ].fillna(False)
    base["proxy_flag"] = base["host_is_proxy"].fillna(False) | base[
        "parent_is_proxy"
    ].fillna(False)
    base = base.sort_values(
        ["source_host_country_id", "source_parent_country_id", "model_sector", "year"],
        kind="mergesort",
    ).reset_index(drop=True)
    return base


def arrow_array(value: Any, dtype: pa.DataType, length: int) -> pa.Array | pa.ChunkedArray:
    if isinstance(value, pa.ChunkedArray):
        return value.cast(dtype)
    if isinstance(value, pa.Array):
        return value.cast(dtype)
    if isinstance(value, pd.Series):
        return pa.array(value, type=dtype, from_pandas=True)
    if isinstance(value, np.ndarray):
        return pa.array(value, type=dtype, from_pandas=True)
    if value is None or value is pd.NA:
        return pa.nulls(length, type=dtype)
    return pa.repeat(pa.scalar(value, type=dtype), length)


def write_parent_long(
    base: pd.DataFrame,
    output: Path,
    config: dict[str, Any],
    config_hash: str,
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    schema = parent_long_schema(config)
    n = len(base)
    static: dict[str, Any] = {
        "year": base["year"],
        "source_name": config["source_contract"]["source_name"],
        "source_host_country_id": base["source_host_country_id"],
        "host_country_iso3": base["host_country_iso3"],
        "host_canonical_country_name": base["host_canonical_country_name"],
        "host_mapping_status": base["host_mapping_status"],
        "host_is_country": base["host_is_country"],
        "host_is_aggregate": base["host_is_aggregate"],
        "host_is_residual": base["host_is_residual"],
        "host_is_proxy": base["host_is_proxy"],
        "host_main_analysis_country_flag": base["host_main_analysis_country_flag"],
        "host_is_core_connector": base["host_is_core_connector"],
        "host_is_asian_comparator": base["host_is_asian_comparator"],
        "host_is_other_candidate": base["host_is_other_candidate"],
        "host_comparison_sample_country_flag": base[
            "host_comparison_sample_country_flag"
        ],
        "source_parent_country_id": base["source_parent_country_id"],
        "parent_country_iso3": base["parent_country_iso3"],
        "parent_canonical_country_name": base["parent_canonical_country_name"],
        "parent_mapping_status": base["parent_mapping_status"],
        "parent_is_country": base["parent_is_country"],
        "parent_is_aggregate": base["parent_is_aggregate"],
        "parent_is_residual": base["parent_is_residual"],
        "parent_is_proxy": base["parent_is_proxy"],
        "parent_country_join_eligible": base["parent_country_join_eligible"],
        "model_sector": base["model_sector"],
        "source_sector_level": base["source_sector_level"],
        "source_sector_label": base["source_sector_label"],
        "analysis_sector": base["analysis_sector"],
        "sector_mapping_status": base["sector_mapping_status"],
        "sector_mapping_rule": base["sector_mapping_rule"],
        "sector_first_round_exclusion": base["sector_first_round_exclusion"],
        "sector_proxy_analysis_sector": base["sector_proxy_analysis_sector"],
        "sector_is_main_join_eligible": base["sector_is_main_join_eligible"],
        "sector_mapping_weight": base["sector_mapping_weight"],
        "source_granularity_note": base["source_granularity_note"],
        "source_code_family": base["source_code_family"],
        "source_sector_mapping_version": base["source_sector_mapping_version"],
        "ownership_type": base["ownership_type"],
        "frequency": config["source_contract"]["frequency"],
        "suppressed_flag": False,
        "confidential_flag": False,
        "aggregate_flag": base["aggregate_flag"],
        "residual_flag": base["residual_flag"],
        "proxy_flag": base["proxy_flag"],
        "main_analysis_join_eligible": base["main_analysis_join_eligible"],
        "can_sum_across_metrics": False,
        "host_total_repeated_across_parents_flag": False,
        "positive_affiliate_output_link_flag": True,
        "zero_affiliate_output_links_materialized_flag": False,
        "source_file": base["source_file"],
        "amne_release": config["source_contract"]["release"],
        "m4_amne_version": config["version"],
        "rules_config_sha256": config_hash,
        "schema_version": config["outputs"]["parent_long"]["schema_version"],
    }
    static_arrays = {
        name: arrow_array(value, schema.field(name).type, n)
        for name, value in static.items()
    }
    metric_counts: dict[str, int] = {}
    writer = pq.ParquetWriter(
        output,
        schema,
        compression="zstd",
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
    )
    try:
        metrics = sorted(
            config["parent_metrics"].items(), key=lambda item: int(item[1]["order"])
        )
        for metric_name, metric in metrics:
            values = base[metric["source_field"]]
            available = values.notna()
            if metric_name in {
                "affiliate_value_added",
                "affiliate_exports",
                "affiliate_imports",
                "parent_affiliate_output_share",
            }:
                allocation_weight: Any = base["parent_affiliate_output_share"]
            else:
                allocation_weight = None
            direction = {
                "affiliate_exports": "affiliate_exports_to_world",
                "affiliate_imports": "affiliate_imports_from_world",
            }.get(metric_name, "parent_to_host_ownership_link")
            dynamic: dict[str, Any] = {
                "metric_name": metric_name,
                "metric_order": int(metric["order"]),
                "value": values,
                "unit": metric["unit"],
                "direction": direction,
                "direct_or_allocated": metric["direct_or_allocated"],
                "derivation_status": metric["derivation_status"],
                "metric_formula": metric["formula"],
                "metric_use": metric["use"],
                "allocation_method": metric["allocation_method"],
                "allocation_weight": allocation_weight,
                "value_available_flag": available,
                "metric_unavailable_flag": metric_name == "affiliate_employment",
                "observed_negative_flag": values.lt(0).fillna(False),
                "observed_zero_flag": values.eq(0).fillna(False),
                "metric_additive_across_parents": bool(metric["additive_across_parents"]),
                "metric_additive_across_source_sectors": bool(
                    metric["additive_across_source_sectors"]
                ),
            }
            arrays: list[pa.Array | pa.ChunkedArray] = []
            for field in schema:
                value = dynamic[field.name] if field.name in dynamic else static_arrays[field.name]
                arrays.append(
                    value
                    if isinstance(value, (pa.Array, pa.ChunkedArray))
                    else arrow_array(value, field.type, n)
                )
            table = pa.Table.from_arrays(arrays, schema=schema)
            writer.write_table(
                table,
                row_group_size=int(config["validation"]["parent_row_group_size"]),
            )
            metric_counts[metric_name] = n
            del table, arrays, dynamic
            gc.collect()
    finally:
        writer.close()
    return {
        "rows": int(n * len(config["parent_metrics"])),
        "columns": len(schema),
        "metric_row_counts": metric_counts,
        "schema_signature": schema_signature(schema),
    }


def build_host_source_cells(
    mp: pd.DataFrame,
    sectors: pd.DataFrame,
    countries: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_crosswalk_name = config["source_contract"]["source_crosswalk_name"]
    sector = sector_subset(sectors, source_crosswalk_name).rename(
        columns={
            "source_sector_code": "sector_oecd",
            "mapping_status": "sector_mapping_status",
            "mapping_rule": "sector_mapping_rule",
            "first_round_exclusion": "sector_first_round_exclusion",
            "is_main_join_eligible": "sector_is_main_join_eligible",
            "mapping_weight": "sector_mapping_weight",
            "mapping_version": "source_sector_mapping_version",
        }
    )
    auxiliary_rows = []
    template = {column: pd.NA for column in sector.columns}
    for code, rule in config["source_contract"]["auxiliary_zero_only_source_sectors"].items():
        row = dict(template)
        row.update(
            {
                "source_name": source_crosswalk_name,
                "source_sector_level": "oecd_amne_sector",
                "sector_oecd": code,
                "source_sector_label": code,
                "analysis_sector": pd.NA,
                "sector_mapping_status": rule["status"],
                "sector_mapping_rule": "m4_2_explicit_auxiliary_zero_only_exclusion",
                "sector_first_round_exclusion": pd.NA,
                "proxy_analysis_sector": pd.NA,
                "sector_is_main_join_eligible": bool(rule["main_join_eligible"]),
                "sector_mapping_weight": np.nan,
                "source_granularity_note": (
                    "Zero-only nonmanufacturing code present in the full MP-share universe; "
                    "excluded explicitly without modifying the frozen M1 crosswalk."
                ),
                "source_code_family": "OECD_AMNE_2026_AUXILIARY_ZERO_ONLY",
                "source_sector_mapping_version": config["version"],
            }
        )
        auxiliary_rows.append(row)
    sector_extended = pd.concat([sector, pd.DataFrame(auxiliary_rows)], ignore_index=True)
    country = country_subset(countries, source_crosswalk_name)
    country_flags = country.set_index("source_country_id")
    parent_is_country = mp["parent_country_iso3"].map(country_flags["is_country"])
    parent_is_aggregate = mp["parent_country_iso3"].map(country_flags["is_aggregate"])
    work = mp.copy()
    work["parent_is_country"] = parent_is_country.fillna(False)
    work["parent_is_aggregate"] = parent_is_aggregate.fillna(False)
    work["actual_parent_affiliate_output"] = work["affiliate_output"].where(
        work["parent_is_country"], 0.0
    )
    grouped = work.groupby(HOST_SOURCE_KEY, sort=True, observed=True)
    direct_nunique = grouped[
        ["gross_output", "foreign_affiliate_output_total", "foreign_affiliate_share", "source_file"]
    ].nunique(dropna=False)
    direct_repeat_max_unique = {
        column: int(direct_nunique[column].max()) for column in direct_nunique.columns
    }
    source_cells = grouped.agg(
        bilateral_affiliate_output_sum=("affiliate_output", "sum"),
        foreign_affiliate_value_added_total=("affiliate_value_added", lambda x: x.sum(min_count=1)),
        foreign_affiliate_exports_total=("affiliate_exports", lambda x: x.sum(min_count=1)),
        foreign_affiliate_imports_total=("affiliate_imports", lambda x: x.sum(min_count=1)),
        actual_parent_affiliate_output_sum=("actual_parent_affiliate_output", "sum"),
        gross_output=("gross_output", "first"),
        foreign_affiliate_output_total=("foreign_affiliate_output_total", "first"),
        source_foreign_affiliate_share=("foreign_affiliate_share", "first"),
        source_file=("source_file", "first"),
        source_parent_count=("parent_country_iso3", "nunique"),
        actual_parent_count=("parent_is_country", "sum"),
        aggregate_parent_count=("parent_is_aggregate", "sum"),
    ).reset_index()
    positive_counts = (
        work.loc[work["affiliate_output"].gt(0)]
        .groupby(HOST_SOURCE_KEY, sort=True, observed=True)["parent_country_iso3"]
        .nunique()
        .rename("positive_parent_link_count")
        .reset_index()
    )
    source_cells = source_cells.merge(
        positive_counts, on=HOST_SOURCE_KEY, how="left", validate="one_to_one"
    )
    source_cells["positive_parent_link_count"] = (
        source_cells["positive_parent_link_count"].fillna(0).astype("int16")
    )
    source_cells = source_cells.merge(
        sector_extended,
        on="sector_oecd",
        how="left",
        validate="many_to_one",
    )
    host = country.rename(
        columns={
            "source_country_id": "host_country_iso3",
            "country_iso3": "country_iso3",
            "canonical_country_name": "canonical_country_name",
            "is_country": "host_is_country",
            "is_aggregate": "host_is_aggregate",
            "is_residual": "host_is_residual",
            "is_proxy": "host_is_proxy",
        }
    )[
        [
            "host_country_iso3",
            "country_iso3",
            "canonical_country_name",
            "host_is_country",
            "host_is_aggregate",
            "host_is_residual",
            "host_is_proxy",
            "is_core_connector",
            "is_asian_comparator",
            "is_other_candidate",
        ]
    ]
    source_cells = source_cells.merge(
        host, on="host_country_iso3", how="left", validate="many_to_one"
    )
    source_cells["comparison_sample_country_flag"] = (
        source_cells[["is_core_connector", "is_asian_comparator", "is_other_candidate"]]
        .fillna(False)
        .any(axis=1)
    )
    source_cells["bilateral_xvem_output_gap"] = (
        source_cells["bilateral_affiliate_output_sum"]
        - source_cells["foreign_affiliate_output_total"]
    )
    source_cells["mapped_parent_output_share"] = np.where(
        source_cells["bilateral_affiliate_output_sum"].gt(0),
        source_cells["actual_parent_affiliate_output_sum"]
        / source_cells["bilateral_affiliate_output_sum"],
        np.nan,
    )
    context = {
        "source_cell_rows": int(len(source_cells)),
        "direct_repeat_max_unique": direct_repeat_max_unique,
        "source_max_abs_bilateral_xvem_gap": max_abs(
            source_cells["bilateral_xvem_output_gap"]
        ),
        "source_negative_va_total_cells": int(
            source_cells["foreign_affiliate_value_added_total"].lt(0).sum()
        ),
        "source_foreign_output_zero_cells": int(
            source_cells["foreign_affiliate_output_total"].eq(0).sum()
        ),
        "source_gross_output_zero_cells": int(source_cells["gross_output"].eq(0).sum()),
    }
    return source_cells, context


def build_host_analysis_base(
    mp: pd.DataFrame,
    sectors: pd.DataFrame,
    countries: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_cells, context = build_host_source_cells(mp, sectors, countries, config)
    eligible = source_cells.loc[
        source_cells["host_is_country"].fillna(False)
        & source_cells["sector_is_main_join_eligible"].fillna(False)
        & source_cells["sector_mapping_weight"].eq(1.0)
    ].copy()
    group_key = ["country_iso3", "analysis_sector", "year"]
    aggregation = eligible.groupby(group_key, sort=True, observed=True).agg(
        canonical_country_name=("canonical_country_name", "first"),
        bilateral_affiliate_output_sum=("bilateral_affiliate_output_sum", "sum"),
        foreign_affiliate_output_total=("foreign_affiliate_output_total", "sum"),
        foreign_affiliate_value_added_total=(
            "foreign_affiliate_value_added_total",
            lambda x: x.sum(min_count=1),
        ),
        foreign_affiliate_exports_total=(
            "foreign_affiliate_exports_total",
            lambda x: x.sum(min_count=1),
        ),
        foreign_affiliate_imports_total=(
            "foreign_affiliate_imports_total",
            lambda x: x.sum(min_count=1),
        ),
        gross_output=("gross_output", "sum"),
        actual_parent_affiliate_output_sum=("actual_parent_affiliate_output_sum", "sum"),
        source_sector_count=("sector_oecd", "nunique"),
        source_sector_codes=("sector_oecd", join_unique_text),
        source_sector_mapping_statuses=("sector_mapping_status", join_unique_text),
        source_sector_mapping_rules=("sector_mapping_rule", join_unique_text),
        source_sector_granularity_note=("source_granularity_note", join_unique_text),
        source_sector_mapping_version=("source_sector_mapping_version", join_unique_text),
        source_parent_count=("source_parent_count", "max"),
        actual_parent_count=("actual_parent_count", "max"),
        aggregate_parent_count=("aggregate_parent_count", "max"),
        aggregate_parent_included_flag=("aggregate_parent_count", lambda x: bool((x > 0).all())),
        source_file=("source_file", join_unique_text),
        is_core_connector=("is_core_connector", "first"),
        is_asian_comparator=("is_asian_comparator", "first"),
        is_other_candidate=("is_other_candidate", "first"),
        comparison_sample_country_flag=("comparison_sample_country_flag", "first"),
    ).reset_index()
    positive_parent_counts = (
        mp.loc[mp["affiliate_output"].gt(0)]
        .merge(
            eligible[["year", "host_country_iso3", "sector_oecd", "analysis_sector"]].drop_duplicates(),
            on=["year", "host_country_iso3", "sector_oecd"],
            how="inner",
            validate="many_to_one",
        )
        .groupby(["host_country_iso3", "analysis_sector", "year"], sort=True, observed=True)[
            "parent_country_iso3"
        ]
        .nunique()
        .rename("positive_parent_link_count")
        .reset_index()
        .rename(columns={"host_country_iso3": "country_iso3"})
    )
    aggregation = aggregation.merge(
        positive_parent_counts,
        on=group_key,
        how="left",
        validate="one_to_one",
    )
    aggregation["positive_parent_link_count"] = (
        aggregation["positive_parent_link_count"].fillna(0).astype("int16")
    )
    aggregation["foreign_affiliate_output_share"] = np.where(
        aggregation["gross_output"].gt(0),
        aggregation["foreign_affiliate_output_total"] / aggregation["gross_output"],
        np.nan,
    )
    aggregation["mapped_parent_output_share"] = np.where(
        aggregation["bilateral_affiliate_output_sum"].gt(0),
        aggregation["actual_parent_affiliate_output_sum"]
        / aggregation["bilateral_affiliate_output_sum"],
        np.nan,
    )
    aggregation["bilateral_xvem_output_gap"] = (
        aggregation["bilateral_affiliate_output_sum"]
        - aggregation["foreign_affiliate_output_total"]
    )
    aggregation = aggregation.sort_values(group_key, kind="mergesort").reset_index(drop=True)
    context.update(
        {
            "analysis_cells": int(len(aggregation)),
            "analysis_max_abs_bilateral_xvem_gap": max_abs(
                aggregation["bilateral_xvem_output_gap"]
            ),
            "analysis_bilateral_denominator_zero_cells": int(
                aggregation["bilateral_affiliate_output_sum"].eq(0).sum()
            ),
        }
    )
    return aggregation, context


def source_state_counts(
    eligible_source_cells: pd.DataFrame,
    metric_source_field: str,
) -> pd.DataFrame:
    frame = eligible_source_cells.copy()
    frame["negative"] = frame[metric_source_field].lt(0).fillna(False).astype("int16")
    frame["zero"] = frame[metric_source_field].eq(0).fillna(False).astype("int16")
    frame["missing"] = frame[metric_source_field].isna().astype("int16")
    return (
        frame.groupby(["country_iso3", "analysis_sector", "year"], sort=True, observed=True)
        .agg(
            source_negative_cell_count=("negative", "sum"),
            source_zero_cell_count=("zero", "sum"),
            source_missing_cell_count=("missing", "sum"),
        )
        .reset_index()
    )


def write_host_long(
    mp: pd.DataFrame,
    sectors: pd.DataFrame,
    countries: pd.DataFrame,
    output: Path,
    config: dict[str, Any],
    config_hash: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base, context = build_host_analysis_base(mp, sectors, countries, config)
    source_cells, _ = build_host_source_cells(mp, sectors, countries, config)
    eligible_source = source_cells.loc[
        source_cells["host_is_country"].fillna(False)
        & source_cells["sector_is_main_join_eligible"].fillna(False)
        & source_cells["sector_mapping_weight"].eq(1.0)
    ].copy()
    metric_source_fields = {
        "bilateral_affiliate_output_sum": "bilateral_affiliate_output_sum",
        "foreign_affiliate_output_total": "foreign_affiliate_output_total",
        "foreign_affiliate_value_added_total": "foreign_affiliate_value_added_total",
        "foreign_affiliate_exports_total": "foreign_affiliate_exports_total",
        "foreign_affiliate_imports_total": "foreign_affiliate_imports_total",
        "gross_output": "gross_output",
        "foreign_affiliate_output_share": "source_foreign_affiliate_share",
    }
    schema = host_long_schema(config)
    blocks: list[pd.DataFrame] = []
    metrics = sorted(config["host_metrics"].items(), key=lambda item: int(item[1]["order"]))
    for metric_name, metric in metrics:
        block = base.copy()
        states = source_state_counts(eligible_source, metric_source_fields[metric_name])
        block = block.merge(
            states,
            on=["country_iso3", "analysis_sector", "year"],
            how="left",
            validate="one_to_one",
        )
        block["source_name"] = config["source_contract"]["source_name"]
        block["metric_name"] = metric_name
        block["metric_order"] = int(metric["order"])
        block["value"] = block[metric_name]
        block["unit"] = metric["unit"]
        block["frequency"] = config["source_contract"]["frequency"]
        block["direction"] = (
            "affiliate_exports_to_world"
            if metric_name == "foreign_affiliate_exports_total"
            else "affiliate_imports_from_world"
            if metric_name == "foreign_affiliate_imports_total"
            else "host_activity_or_intensity"
        )
        block["parent_country_iso3"] = pd.NA
        block["direct_or_allocated"] = metric["direct_or_allocated"]
        block["derivation_status"] = metric["derivation_status"]
        block["metric_formula"] = metric["formula"]
        block["metric_use"] = metric["use"]
        block["value_available_flag"] = block["value"].notna()
        block["share_defined_flag"] = (
            block["gross_output"].gt(0)
            if metric_name == "foreign_affiliate_output_share"
            else True
        )
        block["denominator_zero_flag"] = (
            block["gross_output"].eq(0)
            if metric_name == "foreign_affiliate_output_share"
            else False
        )
        block["suppressed_flag"] = False
        block["confidential_flag"] = False
        block["aggregate_flag"] = False
        block["residual_flag"] = False
        block["proxy_flag"] = False
        block["observed_negative_flag"] = block["value"].lt(0).fillna(False)
        block["observed_zero_flag"] = block["value"].eq(0).fillna(False)
        block["metric_additive_across_source_sectors"] = bool(
            metric["additive_across_source_sectors"]
        )
        block["can_sum_across_metrics"] = False
        block["analysis_sector_is_direct_from_one_source_sector"] = block[
            "source_sector_count"
        ].eq(1)
        block["analysis_sector_aggregates_multiple_source_sectors"] = block[
            "source_sector_count"
        ].gt(1)
        block["reconciliation_value_repeated_across_metrics_flag"] = True
        block["amne_release"] = config["source_contract"]["release"]
        block["m4_amne_version"] = config["version"]
        block["rules_config_sha256"] = config_hash
        block["schema_version"] = config["outputs"]["host_long"]["schema_version"]
        blocks.append(block.loc[:, schema.names])
    host_long = pd.concat(blocks, ignore_index=True)
    host_long = host_long.sort_values(
        ["country_iso3", "analysis_sector", "year", "metric_order"], kind="mergesort"
    ).reset_index(drop=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(host_long, schema=schema, preserve_index=False)
    pq.write_table(table, output, compression="zstd", use_dictionary=True, version="2.6")
    context["host_long_rows"] = int(len(host_long))
    context["host_long_columns"] = int(len(host_long.columns))
    return host_long, context


def source_and_formula_checks(
    inputs: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    activity = inputs["activity"]
    mp = inputs["mp"]
    sectors = sector_subset(inputs["sectors"], config["source_contract"]["source_crosswalk_name"])
    countries = country_subset(inputs["countries"], config["source_contract"]["source_crosswalk_name"])
    activity_sorted = activity.sort_values(SOURCE_KEY, kind="mergesort").reset_index(drop=True)
    mp_positive = mp.loc[mp["affiliate_output"].gt(0)].sort_values(
        SOURCE_KEY, kind="mergesort"
    ).reset_index(drop=True)
    positive_keys_equal = activity_sorted[SOURCE_KEY].equals(mp_positive[SOURCE_KEY])
    positive_value_max_differences: dict[str, float] = {}
    for field in [
        "affiliate_output",
        "affiliate_value_added",
        "affiliate_exports",
        "affiliate_imports",
        "parent_affiliate_output_share",
        "gross_output",
        "foreign_affiliate_output_total",
    ]:
        positive_value_max_differences[field] = max_abs(
            activity_sorted[field].to_numpy() - mp_positive[field].to_numpy()
        )
    denominator = mp.groupby(
        ["year", "host_country_iso3", "sector_oecd"], sort=False, observed=True
    )["affiliate_output"].transform("sum")
    recomputed_share = np.where(denominator.gt(0), mp["affiliate_output"] / denominator, 0.0)
    parent_share_formula_max_error = max_abs(
        recomputed_share - mp["parent_affiliate_output_share"].to_numpy()
    )
    allocation_formula_max_errors: dict[str, float] = {}
    for field in ["affiliate_value_added", "affiliate_exports", "affiliate_imports"]:
        host_total = mp.groupby(
            ["year", "host_country_iso3", "sector_oecd"], sort=False, observed=True
        )[field].transform("sum")
        expected = mp["parent_affiliate_output_share"] * host_total
        allocation_formula_max_errors[field] = max_abs(mp[field] - expected)
    expected_foreign_share = np.where(
        mp["gross_output"].gt(0),
        mp["foreign_affiliate_output_total"] / mp["gross_output"],
        np.nan,
    )
    share_mask = np.isfinite(expected_foreign_share) & mp["foreign_affiliate_share"].notna()
    foreign_share_formula_max_error = max_abs(
        mp.loc[share_mask, "foreign_affiliate_share"].to_numpy()
        - expected_foreign_share[share_mask]
    )
    activity_sector_join = activity[["sector_oecd"]].merge(
        sectors[["source_sector_code", "mapping_status", "is_main_join_eligible"]],
        left_on="sector_oecd",
        right_on="source_sector_code",
        how="left",
        validate="many_to_one",
    )
    eligible_activity = activity_sector_join["is_main_join_eligible"].fillna(False)
    first_excluded_activity = activity_sector_join["mapping_status"].eq("first_round_excluded")
    outside_activity = activity_sector_join["mapping_status"].eq("outside_manufacturing")
    mp_sector_codes = set(mp["sector_oecd"].unique())
    canonical_sector_codes = set(sectors["source_sector_code"].unique())
    auxiliary_codes = sorted(mp_sector_codes - canonical_sector_codes)
    auxiliary = mp.loc[mp["sector_oecd"].isin(auxiliary_codes)]
    country_codes = set(mp["host_country_iso3"]) | set(mp["parent_country_iso3"])
    mapped_country_codes = set(countries["source_country_id"])
    return {
        "activity_rows": int(len(activity)),
        "mp_rows": int(len(mp)),
        "activity_key_missing_rows": int(activity[SOURCE_KEY].isna().any(axis=1).sum()),
        "activity_duplicate_key_rows": int(activity.duplicated(SOURCE_KEY, keep=False).sum()),
        "mp_key_missing_rows": int(mp[SOURCE_KEY].isna().any(axis=1).sum()),
        "mp_duplicate_key_rows": int(mp.duplicated(SOURCE_KEY, keep=False).sum()),
        "activity_domestic_diagonal_rows": int(
            activity["host_country_iso3"].eq(activity["parent_country_iso3"]).sum()
        ),
        "mp_domestic_diagonal_rows": int(
            mp["host_country_iso3"].eq(mp["parent_country_iso3"]).sum()
        ),
        "years": sorted(int(value) for value in mp["year"].unique()),
        "host_count": int(mp["host_country_iso3"].nunique()),
        "parent_count": int(mp["parent_country_iso3"].nunique()),
        "activity_source_sector_count": int(activity["sector_oecd"].nunique()),
        "mp_source_sector_count": int(mp["sector_oecd"].nunique()),
        "parents_per_host_sector_year_min": int(
            mp.groupby(["year", "host_country_iso3", "sector_oecd"])["parent_country_iso3"]
            .nunique()
            .min()
        ),
        "parents_per_host_sector_year_max": int(
            mp.groupby(["year", "host_country_iso3", "sector_oecd"])["parent_country_iso3"]
            .nunique()
            .max()
        ),
        "positive_subset_rows": int(len(mp_positive)),
        "zero_link_rows": int(mp["affiliate_output"].eq(0).sum()),
        "positive_keys_equal": bool(positive_keys_equal),
        "positive_value_max_differences": positive_value_max_differences,
        "parent_share_formula_max_error": parent_share_formula_max_error,
        "allocation_formula_max_errors": allocation_formula_max_errors,
        "foreign_share_formula_max_error": foreign_share_formula_max_error,
        "activity_unmatched_sector_rows": int(activity_sector_join["source_sector_code"].isna().sum()),
        "activity_eligible_rows": int(eligible_activity.sum()),
        "activity_first_round_excluded_rows": int(first_excluded_activity.sum()),
        "activity_outside_manufacturing_rows": int(outside_activity.sum()),
        "auxiliary_mp_sector_codes": auxiliary_codes,
        "auxiliary_rows": int(len(auxiliary)),
        "auxiliary_nonzero_affiliate_output_rows": int(auxiliary["affiliate_output"].ne(0).sum()),
        "unmatched_country_codes": sorted(country_codes - mapped_country_codes),
        "activity_negative_value_added_rows": int(activity["affiliate_value_added"].lt(0).sum()),
        "activity_employment_missing_rows": int(activity["affiliate_employment"].isna().sum()),
        "activity_output_nonpositive_rows": int(activity["affiliate_output"].le(0).sum()),
        "infinite_numeric_values": int(
            np.isinf(mp.select_dtypes(include=[np.number]).to_numpy()).sum()
        ),
    }


def validate_candidate(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    inputs: dict[str, Any],
    parent_path: Path,
    host_path: Path,
    parent_build: dict[str, Any],
    host_long: pd.DataFrame,
    context: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def require(condition: bool, name: str, observed: Any, expected: Any) -> None:
        passed = bool(condition)
        checks.append({"check": name, "pass": passed, "observed": observed, "expected": expected})
        if not passed:
            failures.append(f"{name}: observed={observed!r}, expected={expected!r}")

    contracts = input_contract(project_root, config, inputs)
    for name, contract in contracts.items():
        require(contract["hash_match"], f"{name}_hash", contract["sha256"], contract["expected_sha256"])
        if name != "build_summary":
            require(contract["row_count_match"], f"{name}_rows", contract["rows"], contract["expected_rows"])
            require(contract["column_count_match"], f"{name}_columns", contract["columns"], contract["expected_columns"])
            require(contract["schema_match"], f"{name}_schema", contract["schema_signature"], contract["expected_schema_signature"])
            require(contract.get("key_missing_rows", 0) == 0, f"{name}_key_missing", contract.get("key_missing_rows", 0), 0)
            require(contract.get("duplicate_key_rows", 0) == 0, f"{name}_duplicate_key", contract.get("duplicate_key_rows", 0), 0)

    source_checks = source_and_formula_checks(inputs, config)
    validation_config = config["validation"]
    require(source_checks["activity_domestic_diagonal_rows"] == 0, "activity_domestic_diagonal", source_checks["activity_domestic_diagonal_rows"], 0)
    require(source_checks["mp_domestic_diagonal_rows"] == 0, "mp_domestic_diagonal", source_checks["mp_domestic_diagonal_rows"], 0)
    require(source_checks["years"] == config["source_contract"]["observed_years"], "observed_years", source_checks["years"], config["source_contract"]["observed_years"])
    require(source_checks["host_count"] == 81, "host_count", source_checks["host_count"], 81)
    require(source_checks["parent_count"] == 81, "parent_count", source_checks["parent_count"], 81)
    require(source_checks["parents_per_host_sector_year_min"] == 80 and source_checks["parents_per_host_sector_year_max"] == 80, "full_parent_grid", [source_checks["parents_per_host_sector_year_min"], source_checks["parents_per_host_sector_year_max"]], [80, 80])
    require(source_checks["positive_subset_rows"] == validation_config["expected_activity_positive_link_rows"], "positive_subset_rows", source_checks["positive_subset_rows"], validation_config["expected_activity_positive_link_rows"])
    require(source_checks["zero_link_rows"] == validation_config["expected_mp_zero_link_rows"], "zero_link_rows", source_checks["zero_link_rows"], validation_config["expected_mp_zero_link_rows"])
    require(source_checks["positive_keys_equal"], "positive_subset_keys_equal", source_checks["positive_keys_equal"], True)
    require(max(source_checks["positive_value_max_differences"].values()) <= validation_config["allocation_tolerance_million_usd"], "positive_subset_values", max(source_checks["positive_value_max_differences"].values()), validation_config["allocation_tolerance_million_usd"])
    require(source_checks["parent_share_formula_max_error"] <= validation_config["numeric_tolerance"], "parent_share_formula", source_checks["parent_share_formula_max_error"], validation_config["numeric_tolerance"])
    require(max(source_checks["allocation_formula_max_errors"].values()) <= validation_config["allocation_tolerance_million_usd"], "allocated_metric_formulas", max(source_checks["allocation_formula_max_errors"].values()), validation_config["allocation_tolerance_million_usd"])
    require(source_checks["foreign_share_formula_max_error"] <= validation_config["numeric_tolerance"], "source_foreign_share_formula", source_checks["foreign_share_formula_max_error"], validation_config["numeric_tolerance"])
    require(source_checks["activity_unmatched_sector_rows"] == 0, "activity_sector_join", source_checks["activity_unmatched_sector_rows"], 0)
    for field in ["activity_eligible_rows", "activity_first_round_excluded_rows", "activity_outside_manufacturing_rows", "activity_negative_value_added_rows", "activity_employment_missing_rows"]:
        expected = validation_config[f"expected_{field}"]
        require(source_checks[field] == expected, field, source_checks[field], expected)
    require(source_checks["auxiliary_mp_sector_codes"] == ["O84", "T97T98"], "auxiliary_zero_only_codes", source_checks["auxiliary_mp_sector_codes"], ["O84", "T97T98"])
    require(source_checks["auxiliary_nonzero_affiliate_output_rows"] == 0, "auxiliary_codes_zero_output", source_checks["auxiliary_nonzero_affiliate_output_rows"], 0)
    require(not source_checks["unmatched_country_codes"], "country_join_coverage", source_checks["unmatched_country_codes"], [])
    require(source_checks["activity_output_nonpositive_rows"] == 0, "activity_positive_output", source_checks["activity_output_nonpositive_rows"], 0)
    require(source_checks["infinite_numeric_values"] == 0, "input_infinite_values", source_checks["infinite_numeric_values"], 0)

    parent_file = pq.ParquetFile(parent_path)
    parent_schema = parent_long_schema(config)
    parent_file_rows = int(parent_file.metadata.num_rows)
    parent_file_columns = int(len(parent_file.schema_arrow))
    parent_file_schema = parent_file.schema_arrow
    parent_file.close()
    require(parent_file_rows == config["outputs"]["parent_long"]["expected_rows"], "parent_long_rows", parent_file_rows, config["outputs"]["parent_long"]["expected_rows"])
    require(parent_file_columns == config["outputs"]["parent_long"]["expected_columns"], "parent_long_columns", parent_file_columns, config["outputs"]["parent_long"]["expected_columns"])
    require(parent_file_schema.equals(parent_schema), "parent_long_schema", str(parent_file_schema), str(parent_schema))
    metric_column = pq.read_table(parent_path, columns=["metric_name"])["metric_name"]
    metric_counts_table = pc.value_counts(metric_column).to_pylist()
    metric_counts = {item["values"]: int(item["counts"]) for item in metric_counts_table}
    require(metric_counts == parent_build["metric_row_counts"], "parent_metric_row_counts", metric_counts, parent_build["metric_row_counts"])
    require(all(count == len(inputs["activity"]) for count in metric_counts.values()), "parent_each_source_row_has_six_metrics", metric_counts, len(inputs["activity"]))
    parent_alias = alias_validation(parent_schema, config["outputs"]["parent_long"]["stata_aliases"])
    require(parent_alias["pass"], "parent_stata_aliases", parent_alias, "complete_unique_legal_max32")
    employment_values = pq.read_table(parent_path, columns=["value"], filters=[("metric_name", "=", "affiliate_employment")])["value"]
    require(employment_values.null_count == len(inputs["activity"]), "parent_employment_unavailable", employment_values.null_count, len(inputs["activity"]))
    va_values = pq.read_table(parent_path, columns=["value"], filters=[("metric_name", "=", "affiliate_value_added")])["value"]
    va_negative = int(pc.sum(pc.less(va_values, 0)).as_py())
    require(va_negative == validation_config["expected_activity_negative_value_added_rows"], "parent_negative_value_added_preserved", va_negative, validation_config["expected_activity_negative_value_added_rows"])

    host_schema = host_long_schema(config)
    require(len(host_long) == config["outputs"]["host_long"]["expected_rows"], "host_long_rows", len(host_long), config["outputs"]["host_long"]["expected_rows"])
    require(len(host_long.columns) == config["outputs"]["host_long"]["expected_columns"], "host_long_columns", len(host_long.columns), config["outputs"]["host_long"]["expected_columns"])
    require(host_long.duplicated(HOST_LONG_KEY, keep=False).sum() == 0, "host_long_duplicate_key", int(host_long.duplicated(HOST_LONG_KEY, keep=False).sum()), 0)
    require(host_long["country_iso3"].nunique() == 80, "host_analysis_country_count", host_long["country_iso3"].nunique(), 80)
    require(host_long["analysis_sector"].nunique() == 6, "host_analysis_sector_count", host_long["analysis_sector"].nunique(), 6)
    require(host_long[HOST_LONG_KEY[:-1]].drop_duplicates().shape[0] == 7680, "host_analysis_cells", host_long[HOST_LONG_KEY[:-1]].drop_duplicates().shape[0], 7680)
    require(host_long["analysis_sector"].eq("medical_devices").sum() == 0, "no_medical_devices_fabrication", int(host_long["analysis_sector"].eq("medical_devices").sum()), 0)
    require((host_long.loc[host_long["country_iso3"].eq("TWN"), "proxy_flag"] == False).all(), "twn_direct_not_proxy", bool((host_long.loc[host_long["country_iso3"].eq("TWN"), "proxy_flag"] == False).all()), True)
    for metric_name in config["host_metrics"]:
        subset = host_long.loc[host_long["metric_name"].eq(metric_name), "value"]
        observed_zero = int(subset.eq(0).sum())
        observed_missing = int(subset.isna().sum())
        observed_negative = int(subset.lt(0).sum())
        require(observed_zero == validation_config["expected_host_analysis_zero_counts"][metric_name], f"host_{metric_name}_zero_count", observed_zero, validation_config["expected_host_analysis_zero_counts"][metric_name])
        require(observed_missing == validation_config["expected_host_analysis_missing_counts"][metric_name], f"host_{metric_name}_missing_count", observed_missing, validation_config["expected_host_analysis_missing_counts"][metric_name])
        require(observed_negative == validation_config["expected_host_analysis_negative_counts"][metric_name], f"host_{metric_name}_negative_count", observed_negative, validation_config["expected_host_analysis_negative_counts"][metric_name])
    wide = host_long.pivot(index=["country_iso3", "analysis_sector", "year"], columns="metric_name", values="value")
    recomputed = np.where(wide["gross_output"].gt(0), wide["foreign_affiliate_output_total"] / wide["gross_output"], np.nan)
    mask = np.isfinite(recomputed) & wide["foreign_affiliate_output_share"].notna()
    host_share_error = max_abs(wide.loc[mask, "foreign_affiliate_output_share"].to_numpy() - recomputed[mask])
    require(host_share_error <= validation_config["numeric_tolerance"], "host_ratio_of_sums_share", host_share_error, validation_config["numeric_tolerance"])
    require(context["analysis_bilateral_denominator_zero_cells"] == validation_config["expected_host_positive_parent_denominator_zero_cells"], "host_bilateral_zero_cells", context["analysis_bilateral_denominator_zero_cells"], validation_config["expected_host_positive_parent_denominator_zero_cells"])
    require(abs(context["source_max_abs_bilateral_xvem_gap"] - validation_config["expected_max_abs_source_bilateral_xvem_gap"]) <= validation_config["gap_snapshot_tolerance_million_usd"], "source_bilateral_xvem_gap_preserved", context["source_max_abs_bilateral_xvem_gap"], validation_config["expected_max_abs_source_bilateral_xvem_gap"])
    require(abs(context["analysis_max_abs_bilateral_xvem_gap"] - validation_config["expected_max_abs_analysis_bilateral_xvem_gap"]) <= validation_config["gap_snapshot_tolerance_million_usd"], "analysis_bilateral_xvem_gap_preserved", context["analysis_max_abs_bilateral_xvem_gap"], validation_config["expected_max_abs_analysis_bilateral_xvem_gap"])
    require(all(value == 1 for value in context["direct_repeat_max_unique"].values()), "host_repeated_direct_values_unique", context["direct_repeat_max_unique"], {key: 1 for key in context["direct_repeat_max_unique"]})
    connector_cells = host_long.loc[host_long["comparison_sample_country_flag"]].drop_duplicates(["country_iso3", "analysis_sector", "year"])
    connector_countries = host_long.loc[host_long["comparison_sample_country_flag"], "country_iso3"].nunique()
    require(connector_countries == validation_config["expected_connector_country_count"], "connector_country_count", connector_countries, validation_config["expected_connector_country_count"])
    require(len(connector_cells) == validation_config["expected_connector_country_sector_year_cells"], "connector_country_sector_year_cells", len(connector_cells), validation_config["expected_connector_country_sector_year_cells"])
    host_alias = alias_validation(host_schema, config["outputs"]["host_long"]["stata_aliases"])
    require(host_alias["pass"], "host_stata_aliases", host_alias, "complete_unique_legal_max32")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "checks": checks,
        "input_contract": contracts,
        "source_and_formula_checks": source_checks,
        "parent_long_checks": {
            "rows": parent_file_rows,
            "columns": parent_file_columns,
            "metric_row_counts": metric_counts,
            "duplicate_key_rows": 0 if source_checks["activity_duplicate_key_rows"] == 0 and all(count == len(inputs["activity"]) for count in metric_counts.values()) else None,
            "employment_missing_rows": int(employment_values.null_count),
            "negative_value_added_rows": va_negative,
            "stata_alias_validation": parent_alias,
        },
        "host_long_checks": {
            "rows": int(len(host_long)),
            "columns": int(len(host_long.columns)),
            "duplicate_key_rows": int(host_long.duplicated(HOST_LONG_KEY, keep=False).sum()),
            "country_count": int(host_long["country_iso3"].nunique()),
            "analysis_sector_count": int(host_long["analysis_sector"].nunique()),
            "country_sector_year_cells": int(host_long[HOST_LONG_KEY[:-1]].drop_duplicates().shape[0]),
            "host_share_formula_max_error": host_share_error,
            "stata_alias_validation": host_alias,
        },
        "reconciliation": context,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    parent = validation["parent_long_checks"]
    host = validation["host_long_checks"]
    source = validation["source_and_formula_checks"]
    recon = validation["reconciliation"]
    outputs = validation["outputs"]
    lines = [
        "# M4.2 OECD Analytical AMNE Production-Side Validation",
        "",
        f"- Origin Date: `{validation['origin_date']}`",
        "- Verification Status: `VERIFIED`",
        f"- Version Label: `{validation['construction_version']}`",
        "",
        "## Result",
        "",
        f"- Validation status: **{validation['validation_status']}**.",
        f"- Parent-host source-detail long: `{outputs['parent_long']['path']}`; `{parent['rows']} × {parent['columns']}`; SHA256 `{outputs['parent_long']['sha256']}`.",
        f"- Host-analysis-sector long: `{outputs['host_long']['path']}`; `{host['rows']} × {host['columns']}`; SHA256 `{outputs['host_long']['sha256']}`.",
        f"- Natural-key duplicates: parent `{parent['duplicate_key_rows']}`, host `{host['duplicate_key_rows']}`.",
        f"- Deterministic second-build hashes match: parent `{validation['determinism']['parent_long_sha256_match']}`, host `{validation['determinism']['host_long_sha256_match']}`.",
        "",
        "## Frozen Inputs and Coverage",
        "",
        f"- Positive-link affiliate activity: `{source['activity_rows']:,}` rows; full zero-inclusive MP-share universe: `{source['mp_rows']:,}` rows.",
        f"- The MP-share universe contains `{source['zero_link_rows']:,}` zero-output parent links; its positive subset matches the activity table keys: `{source['positive_keys_equal']}`.",
        f"- Coverage is 81 source hosts, 81 source parents, 41 full-universe source sectors, and 16 years (2008–2023). Every host-source-sector-year has exactly 80 foreign parents.",
        f"- The two full-universe auxiliary sectors are `{', '.join(source['auxiliary_mp_sector_codes'])}`; all `{source['auxiliary_rows']:,}` rows have zero affiliate output and are explicitly excluded from manufacturing analysis without modifying M1.",
        "",
        "## Direct, Allocated, Derived, and Unavailable Metrics",
        "",
        "- `affiliate_output` is direct bilateral OECD AMNE output.",
        "- Parent-level value added, exports, and imports are allocated from host-sector foreign-owned totals using bilateral parent output shares; they are not direct bilateral observations.",
        f"- Parent-share formula maximum error is `{source['parent_share_formula_max_error']:.3g}`; allocated-metric formula maximum error is `{max(source['allocation_formula_max_errors'].values()):.3g}` million USD.",
        f"- All `{parent['employment_missing_rows']:,}` positive-link employment values remain missing and are marked unavailable; none are converted to zero.",
        f"- All `{parent['negative_value_added_rows']}` negative allocated parent-level value-added observations remain signed.",
        "",
        "## Host-Sector Totals and Reconciliation",
        "",
        f"- Analysis grid: 80 actual hosts × 6 supported analysis sectors × 16 years = `{host['country_sector_year_cells']:,}` cells; medical devices are not fabricated.",
        "- Host foreign-affiliate output is the direct XVEM total. The bilateral parent-output sum is retained as a separate reconciliation metric and parent-share denominator.",
        f"- Maximum absolute bilateral-minus-XVEM gap is `{recon['source_max_abs_bilateral_xvem_gap']:.12g}` million USD at source-sector level and `{recon['analysis_max_abs_bilateral_xvem_gap']:.12g}` million USD after analysis-sector aggregation; this expected source-concept difference is not forced to zero.",
        f"- The host foreign-affiliate share is recomputed as a ratio of analysis-sector sums; formula maximum error is `{host['host_share_formula_max_error']:.3g}`.",
        "- ROW parent contributions are included in host totals; ROW host is excluded from the actual-country analysis grid.",
        "",
        "## Stata and Interpretation Boundary",
        "",
        f"- Stata aliases: parent long `{parent['stata_alias_validation']['alias_count']}`, host long `{host['stata_alias_validation']['alias_count']}`; all are complete, unique, legal, and at most 32 characters.",
        "- Parquet remains canonical; `.dta` export remains an M7 task.",
        "- This module constructs annual levels only. It does not construct AMNE growth, MPE expansion, ranking, `hgamma`, structural moments, welfare inputs, BEA/FDI integration, or the final cross-source production table.",
        "- AMNE affiliate activity supports incumbent MP-intensive evidence; it does not by itself prove plant entry or firm-level relocation.",
    ]
    if validation["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in validation["failures"])
    return "\n".join(lines) + "\n"


def build_once(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    parent_output: Path,
    host_output: Path,
) -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame, dict[str, Any]]:
    inputs = read_inputs(project_root, config)
    parent_base = prepare_parent_base(
        inputs["activity"], inputs["sectors"], inputs["countries"], config
    )
    parent_build = write_parent_long(parent_base, parent_output, config, config_hash)
    del parent_base
    gc.collect()
    host_long, context = write_host_long(
        inputs["mp"],
        inputs["sectors"],
        inputs["countries"],
        host_output,
        config,
        config_hash,
    )
    return inputs, parent_build, host_long, context


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    candidate_parent: Path,
    candidate_host: Path,
) -> dict[str, Any]:
    directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if directory.exists():
        raise FileExistsError(f"Refusing to reuse determinism directory: {directory}")
    directory.mkdir(parents=True)
    second_parent = directory / f"{candidate_parent.stem}_second.parquet"
    second_host = directory / f"{candidate_host.stem}_second.parquet"
    try:
        inputs, _, _, _ = build_once(
            project_root, config, config_hash, second_parent, second_host
        )
        del inputs
        gc.collect()
        result = {
            "parent_long_candidate_sha256": sha256(candidate_parent),
            "parent_long_second_build_sha256": sha256(second_parent),
            "parent_long_sha256_match": sha256(candidate_parent) == sha256(second_parent),
            "host_long_candidate_sha256": sha256(candidate_host),
            "host_long_second_build_sha256": sha256(second_host),
            "host_long_sha256_match": sha256(candidate_host) == sha256(second_host),
        }
    finally:
        remove_owned_temp_directory(directory)
    result["temporary_output_cleaned"] = not directory.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate the M4.2 OECD Analytical AMNE parent-host "
            "source-detail and host-analysis-sector production long tables."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config", type=Path, default=Path("configs/production_amne_rules.yaml")
    )
    parser.add_argument("--parent-long-output", type=Path)
    parser.add_argument("--host-long-output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    parent_path = relative_or_absolute(
        project_root,
        args.parent_long_output or Path(config["outputs"]["parent_long"]["path"]),
    ).resolve()
    host_path = relative_or_absolute(
        project_root,
        args.host_long_output or Path(config["outputs"]["host_long"]["path"]),
    ).resolve()
    validation_json = relative_or_absolute(
        project_root,
        args.validation_json or Path(config["validation_outputs"]["json"]),
    ).resolve()
    validation_md = relative_or_absolute(
        project_root,
        args.validation_md or Path(config["validation_outputs"]["markdown"]),
    ).resolve()
    for path in [parent_path, host_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    candidate_directory = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    if candidate_directory.exists():
        raise FileExistsError(f"Refusing to reuse candidate directory: {candidate_directory}")
    candidate_directory.mkdir(parents=True)
    candidate_parent = candidate_directory / parent_path.name
    candidate_host = candidate_directory / host_path.name
    candidate_json = candidate_directory / validation_json.name
    candidate_md = candidate_directory / validation_md.name
    try:
        inputs, parent_build, host_long, context = build_once(
            project_root, config, config_hash, candidate_parent, candidate_host
        )
        validation = validate_candidate(
            project_root,
            config,
            config_hash,
            inputs,
            candidate_parent,
            candidate_host,
            parent_build,
            host_long,
            context,
        )
        del host_long
        gc.collect()
        determinism = deterministic_rebuild(
            project_root, config, config_hash, candidate_parent, candidate_host
        )
        validation["determinism"] = determinism
        if not (
            determinism["parent_long_sha256_match"]
            and determinism["host_long_sha256_match"]
            and determinism["temporary_output_cleaned"]
        ):
            validation["failures"].append("Deterministic second-build hashes or cleanup failed")
            validation["validation_status"] = "FAIL"
        parent_table = pq.ParquetFile(candidate_parent)
        host_table = pq.ParquetFile(candidate_host)
        parent_rows = int(parent_table.metadata.num_rows)
        parent_columns = int(len(parent_table.schema_arrow))
        parent_schema_signature = schema_signature(parent_table.schema_arrow)
        host_rows = int(host_table.metadata.num_rows)
        host_columns = int(len(host_table.schema_arrow))
        host_schema_signature = schema_signature(host_table.schema_arrow)
        parent_table.close()
        host_table.close()
        validation.update(
            {
                "validation_version": 1,
                "origin_date": str(config["frozen_date"]),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_path": config_path.relative_to(project_root).as_posix(),
                "config_sha256": config_hash,
                "construction_version": config["version"],
                "outputs": {
                    "parent_long": {
                        "path": parent_path.relative_to(project_root).as_posix(),
                        "sha256": sha256(candidate_parent),
                        "rows": parent_rows,
                        "columns": parent_columns,
                        "schema_signature": parent_schema_signature,
                    },
                    "host_long": {
                        "path": host_path.relative_to(project_root).as_posix(),
                        "sha256": sha256(candidate_host),
                        "rows": host_rows,
                        "columns": host_columns,
                        "schema_signature": host_schema_signature,
                    },
                },
                "candidate_temp_directory": candidate_directory.relative_to(project_root).as_posix(),
            }
        )
        if validation["validation_status"] != "PASS":
            print(json.dumps(validation, ensure_ascii=False, indent=2, default=str))
            raise SystemExit(1)
        candidate_json.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        candidate_md.write_text(markdown_report(validation), encoding="utf-8", newline="\n")
        for path in [parent_path, host_path, validation_json, validation_md]:
            path.parent.mkdir(parents=True, exist_ok=True)
        candidate_parent.replace(parent_path)
        candidate_host.replace(host_path)
        candidate_json.replace(validation_json)
        candidate_md.replace(validation_md)
        remove_owned_temp_directory(candidate_directory)
        validation["candidate_temporary_output_cleaned"] = not candidate_directory.exists()
        validation_json.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        validation_md.write_text(markdown_report(validation), encoding="utf-8", newline="\n")
        print(
            json.dumps(
                {
                    "validation_status": validation["validation_status"],
                    "parent_long_rows": validation["outputs"]["parent_long"]["rows"],
                    "host_long_rows": validation["outputs"]["host_long"]["rows"],
                    "parent_long_sha256": validation["outputs"]["parent_long"]["sha256"],
                    "host_long_sha256": validation["outputs"]["host_long"]["sha256"],
                    "deterministic_sha256_match": bool(
                        determinism["parent_long_sha256_match"]
                        and determinism["host_long_sha256_match"]
                    ),
                    "validation_json": str(validation_json),
                    "candidate_temporary_output_cleaned": not candidate_directory.exists(),
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
