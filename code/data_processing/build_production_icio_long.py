from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


SOURCE_CELL_KEY = ["source_name", "source_country_id", "model_sector", "year"]
SOURCE_LONG_KEY = SOURCE_CELL_KEY + ["metric_name"]
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


def alias_validation(frame: pd.DataFrame, aliases: dict[str, str]) -> dict[str, Any]:
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


def source_long_schema() -> pa.Schema:
    columns = [
        "year",
        "source_name",
        "source_country_id",
        "country_iso3",
        "canonical_country_name",
        "country_mapping_status",
        "country_is_country",
        "country_is_aggregate",
        "country_is_residual",
        "country_is_proxy",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
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
        "metric_name",
        "metric_order",
        "value",
        "unit",
        "frequency",
        "direction",
        "parent_country_iso3",
        "direct_or_allocated",
        "derivation_status",
        "metric_formula",
        "metric_use",
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "accounting_negative_allowed",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
        "source_file",
        "icio_release",
        "m4_icio_version",
        "rules_config_sha256",
        "schema_version",
    ]
    bool_fields = {
        "country_is_country",
        "country_is_aggregate",
        "country_is_residual",
        "country_is_proxy",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
        "sector_is_main_join_eligible",
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "main_analysis_join_eligible",
        "accounting_negative_allowed",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
    }
    fields: list[pa.Field] = []
    for column in columns:
        if column == "year":
            dtype = pa.int16()
        elif column == "metric_order":
            dtype = pa.int8()
        elif column in {"value", "sector_mapping_weight"}:
            dtype = pa.float64()
        elif column in bool_fields:
            dtype = pa.bool_()
        else:
            dtype = pa.string()
        fields.append(pa.field(column, dtype))
    return pa.schema(fields)


def analysis_long_schema() -> pa.Schema:
    columns = [
        "country_iso3",
        "canonical_country_name",
        "analysis_sector",
        "year",
        "source_name",
        "metric_name",
        "metric_order",
        "value",
        "unit",
        "frequency",
        "direction",
        "parent_country_iso3",
        "direct_or_allocated",
        "derivation_status",
        "metric_formula",
        "metric_use",
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "source_sector_count",
        "source_sector_codes",
        "source_sector_mapping_statuses",
        "source_sector_mapping_rules",
        "source_sector_granularity_note",
        "source_sector_mapping_version",
        "accounting_negative_allowed",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
        "analysis_sector_is_direct_from_one_source_sector",
        "analysis_sector_aggregates_multiple_source_sectors",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
        "source_file",
        "icio_release",
        "m4_icio_version",
        "rules_config_sha256",
        "schema_version",
    ]
    bool_fields = {
        "suppressed_flag",
        "confidential_flag",
        "aggregate_flag",
        "residual_flag",
        "proxy_flag",
        "accounting_negative_allowed",
        "observed_negative_flag",
        "observed_zero_flag",
        "metric_additive_across_source_sectors",
        "can_sum_across_metrics",
        "analysis_sector_is_direct_from_one_source_sector",
        "analysis_sector_aggregates_multiple_source_sectors",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
    }
    fields: list[pa.Field] = []
    for column in columns:
        if column == "year":
            dtype = pa.int16()
        elif column == "metric_order":
            dtype = pa.int8()
        elif column == "source_sector_count":
            dtype = pa.int16()
        elif column == "value":
            dtype = pa.float64()
        elif column in bool_fields:
            dtype = pa.bool_()
        else:
            dtype = pa.string()
        fields.append(pa.field(column, dtype))
    return pa.schema(fields)


def write_parquet(frame: pd.DataFrame, path: Path, schema: pa.Schema) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(
        frame.loc[:, schema.names], schema=schema, preserve_index=False
    )
    pq.write_table(table, path, compression="zstd")
    return table


def read_inputs(
    project_root: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, pa.Schema, pd.DataFrame, pa.Schema, pd.DataFrame, pa.Schema]:
    icio_table = pq.read_table(
        project_root / config["inputs"]["icio_output"]["path"]
    )
    sector_table = pq.read_table(
        project_root / config["inputs"]["source_sector_crosswalk"]["path"]
    )
    country_table = pq.read_table(
        project_root / config["inputs"]["country_crosswalk"]["path"]
    )
    return (
        icio_table.to_pandas(),
        icio_table.schema,
        sector_table.to_pandas(),
        sector_table.schema,
        country_table.to_pandas(),
        country_table.schema,
    )


def join_unique_text(values: pd.Series) -> object:
    unique = sorted({str(value) for value in values.dropna() if str(value).strip()})
    return ";".join(unique) if unique else pd.NA


def build_source_cells(
    icio: pd.DataFrame,
    sector_crosswalk: pd.DataFrame,
    country_crosswalk: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    contract = config["source_contract"]
    crosswalk_name = contract["source_crosswalk_name"]
    sectors = sector_crosswalk.loc[
        sector_crosswalk["source_name"].eq(crosswalk_name)
    ].copy()
    countries = country_crosswalk.loc[
        country_crosswalk["source_name"].eq(crosswalk_name)
    ].copy()
    sector_keep = [
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
    country_keep = [
        "source_country_id",
        "canonical_country_name",
        "country_iso3",
        "mapping_status",
        "is_country",
        "is_aggregate",
        "is_residual",
        "is_proxy",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
    ]
    cells = icio.rename(
        columns={"country_iso3": "source_country_id", "sector_oecd": "model_sector"}
    ).copy()
    cells = cells.merge(
        sectors[sector_keep],
        left_on="model_sector",
        right_on="source_sector_code",
        how="left",
        validate="many_to_one",
        indicator="_sector_merge",
        sort=False,
    )
    cells = cells.merge(
        countries[country_keep],
        on="source_country_id",
        how="left",
        validate="many_to_one",
        indicator="_country_merge",
        sort=False,
        suffixes=("", "_country"),
    )
    context = {
        "sector_join_status_counts": {
            str(key): int(value)
            for key, value in cells["_sector_merge"].value_counts().items()
        },
        "country_join_status_counts": {
            str(key): int(value)
            for key, value in cells["_country_merge"].value_counts().items()
        },
    }
    cells["source_name"] = contract["source_name"]
    cells["country_mapping_status"] = cells["mapping_status_country"]
    cells["country_is_country"] = cells["is_country"].astype(bool)
    cells["country_is_aggregate"] = cells["is_aggregate"].astype(bool)
    cells["country_is_residual"] = cells["is_residual"].astype(bool)
    cells["country_is_proxy"] = cells["is_proxy"].astype(bool)
    role_fields = ["is_core_connector", "is_asian_comparator", "is_other_candidate"]
    for field in role_fields:
        cells[field] = cells[field].fillna(False).astype(bool)
    cells["comparison_sample_country_flag"] = cells[role_fields].any(axis=1)
    cells["source_sector_label"] = cells["source_sector_label"].fillna(
        cells["source_sector_code"]
    )
    cells["sector_mapping_status"] = cells["mapping_status"]
    cells["sector_mapping_rule"] = cells["mapping_rule"]
    cells["sector_first_round_exclusion"] = cells["first_round_exclusion"]
    cells["sector_proxy_analysis_sector"] = cells["proxy_analysis_sector"]
    cells["sector_is_main_join_eligible"] = cells[
        "is_main_join_eligible"
    ].astype(bool)
    cells["sector_mapping_weight"] = cells["mapping_weight"].astype("float64")
    cells["source_sector_mapping_version"] = cells["mapping_version"]
    cells["production_accounting_residual"] = cells["gross_output"] - (
        cells["intermediate_inputs"]
        + cells["taxes_less_subsidies"]
        + cells["value_added"]
    )
    cells["sales_accounting_residual"] = cells["gross_output_sales"] - (
        cells["intermediate_sales"] + cells["final_demand"]
    )
    cells["main_analysis_join_eligible"] = (
        cells["country_is_country"]
        & cells["sector_is_main_join_eligible"]
        & cells["sector_mapping_weight"].eq(1.0)
        & cells["analysis_sector"].notna()
    )
    cells = cells.sort_values(
        ["source_country_id", "model_sector", "year"], kind="mergesort"
    ).reset_index(drop=True)
    return cells, context


def build_outputs(
    icio: pd.DataFrame,
    sector_crosswalk: pd.DataFrame,
    country_crosswalk: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    contract = config["source_contract"]
    cells, context = build_source_cells(
        icio, sector_crosswalk, country_crosswalk, config
    )
    source_metadata = [
        "year",
        "source_name",
        "source_country_id",
        "country_iso3",
        "canonical_country_name",
        "country_mapping_status",
        "country_is_country",
        "country_is_aggregate",
        "country_is_residual",
        "country_is_proxy",
        "is_core_connector",
        "is_asian_comparator",
        "is_other_candidate",
        "comparison_sample_country_flag",
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
        "main_analysis_join_eligible",
        "source_file",
    ]
    source_blocks: list[pd.DataFrame] = []
    for metric_name, rules in sorted(
        config["metrics"].items(), key=lambda item: int(item[1]["order"])
    ):
        block = cells[source_metadata].copy()
        block["metric_name"] = metric_name
        block["metric_order"] = np.int8(rules["order"])
        block["value"] = cells[rules["source_field"]].astype("float64")
        block["unit"] = contract["unit"]
        block["frequency"] = contract["frequency"]
        block["direction"] = "not_applicable"
        block["parent_country_iso3"] = pd.NA
        block["direct_or_allocated"] = contract["direct_or_allocated"]
        block["derivation_status"] = rules["derivation_status"]
        block["metric_formula"] = rules["formula"]
        block["metric_use"] = rules["use"]
        block["suppressed_flag"] = False
        block["confidential_flag"] = False
        block["aggregate_flag"] = block["country_is_aggregate"]
        block["residual_flag"] = block["country_is_residual"]
        block["proxy_flag"] = block["country_is_proxy"]
        block["accounting_negative_allowed"] = bool(
            rules["accounting_negative_allowed"]
        )
        block["observed_negative_flag"] = block["value"].lt(0)
        block["observed_zero_flag"] = block["value"].eq(0)
        block["metric_additive_across_source_sectors"] = True
        block["can_sum_across_metrics"] = False
        block["icio_release"] = contract["release"]
        block["m4_icio_version"] = config["version"]
        block["rules_config_sha256"] = config_hash
        block["schema_version"] = config["outputs"]["source_long"]["schema_version"]
        source_blocks.append(block)
    source_long = pd.concat(source_blocks, ignore_index=True)
    source_long = source_long.sort_values(
        ["source_name", "source_country_id", "model_sector", "year", "metric_order"],
        kind="mergesort",
    ).reset_index(drop=True)
    source_long = source_long.loc[:, source_long_schema().names]

    eligible = cells.loc[cells["main_analysis_join_eligible"]].copy()
    base_keys = ["country_iso3", "analysis_sector", "year"]
    metric_fields = [rules["source_field"] for rules in config["metrics"].values()]
    aggregated = (
        eligible.groupby(base_keys, sort=False, observed=True)[metric_fields]
        .sum()
        .reset_index()
    )
    metadata = (
        eligible.groupby(base_keys, sort=False, observed=True)
        .agg(
            canonical_country_name=("canonical_country_name", "first"),
            source_sector_count=("model_sector", "nunique"),
            source_sector_codes=("model_sector", join_unique_text),
            source_sector_mapping_statuses=("sector_mapping_status", join_unique_text),
            source_sector_mapping_rules=("sector_mapping_rule", join_unique_text),
            source_sector_granularity_note=("source_granularity_note", join_unique_text),
            source_sector_mapping_version=(
                "source_sector_mapping_version",
                join_unique_text,
            ),
            is_core_connector=("is_core_connector", "first"),
            is_asian_comparator=("is_asian_comparator", "first"),
            is_other_candidate=("is_other_candidate", "first"),
            comparison_sample_country_flag=(
                "comparison_sample_country_flag",
                "first",
            ),
            source_file=("source_file", join_unique_text),
        )
        .reset_index()
    )
    aggregated = aggregated.merge(
        metadata, on=base_keys, how="left", validate="one_to_one", sort=False
    )
    analysis_blocks: list[pd.DataFrame] = []
    for metric_name, rules in sorted(
        config["metrics"].items(), key=lambda item: int(item[1]["order"])
    ):
        block = aggregated[
            base_keys
            + [
                "canonical_country_name",
                "source_sector_count",
                "source_sector_codes",
                "source_sector_mapping_statuses",
                "source_sector_mapping_rules",
                "source_sector_granularity_note",
                "source_sector_mapping_version",
                "is_core_connector",
                "is_asian_comparator",
                "is_other_candidate",
                "comparison_sample_country_flag",
                "source_file",
            ]
        ].copy()
        block["source_name"] = contract["source_name"]
        block["metric_name"] = metric_name
        block["metric_order"] = np.int8(rules["order"])
        block["value"] = aggregated[rules["source_field"]].astype("float64")
        block["unit"] = contract["unit"]
        block["frequency"] = contract["frequency"]
        block["direction"] = "not_applicable"
        block["parent_country_iso3"] = pd.NA
        block["direct_or_allocated"] = contract["direct_or_allocated"]
        block["derivation_status"] = rules["derivation_status"]
        block["metric_formula"] = rules["formula"]
        block["metric_use"] = rules["use"]
        block["suppressed_flag"] = False
        block["confidential_flag"] = False
        block["aggregate_flag"] = False
        block["residual_flag"] = False
        block["proxy_flag"] = False
        block["accounting_negative_allowed"] = bool(
            rules["accounting_negative_allowed"]
        )
        block["observed_negative_flag"] = block["value"].lt(0)
        block["observed_zero_flag"] = block["value"].eq(0)
        block["metric_additive_across_source_sectors"] = True
        block["can_sum_across_metrics"] = False
        block["analysis_sector_is_direct_from_one_source_sector"] = block[
            "source_sector_count"
        ].eq(1)
        block["analysis_sector_aggregates_multiple_source_sectors"] = block[
            "source_sector_count"
        ].gt(1)
        block["icio_release"] = contract["release"]
        block["m4_icio_version"] = config["version"]
        block["rules_config_sha256"] = config_hash
        block["schema_version"] = config["outputs"]["analysis_long"][
            "schema_version"
        ]
        analysis_blocks.append(block)
    analysis_long = pd.concat(analysis_blocks, ignore_index=True)
    sector_order = {
        sector: order
        for order, sector in enumerate(config["analysis_sectors"], start=1)
    }
    analysis_long["_sector_order"] = analysis_long["analysis_sector"].map(
        sector_order
    )
    analysis_long = analysis_long.sort_values(
        ["country_iso3", "_sector_order", "year", "metric_order"],
        kind="mergesort",
    ).drop(columns="_sector_order")
    analysis_long["source_sector_count"] = analysis_long[
        "source_sector_count"
    ].astype("int16")
    analysis_long = analysis_long.reset_index(drop=True).loc[
        :, analysis_long_schema().names
    ]
    return source_long, analysis_long, cells, context


def input_contract(
    frame: pd.DataFrame,
    schema: pa.Schema,
    path: Path,
    details: dict[str, Any],
) -> dict[str, Any]:
    natural_key = list(details["natural_key"])
    observed_hash = sha256(path)
    observed_signature = schema_signature(schema)
    return {
        "path": path.as_posix(),
        "observed_sha256": observed_hash,
        "expected_sha256": details["sha256"],
        "hash_match": observed_hash == details["sha256"],
        "observed_rows": int(len(frame)),
        "expected_rows": int(details["expected_rows"]),
        "row_count_match": len(frame) == int(details["expected_rows"]),
        "observed_columns": int(len(frame.columns)),
        "expected_columns": int(details["expected_columns"]),
        "column_count_match": len(frame.columns) == int(details["expected_columns"]),
        "observed_arrow_schema_signature_sha256": observed_signature,
        "expected_arrow_schema_signature_sha256": details[
            "arrow_schema_signature_sha256"
        ],
        "schema_match": observed_signature
        == details["arrow_schema_signature_sha256"],
        "duplicate_key_count": int(frame.duplicated(natural_key).sum()),
        "key_null_count": int(frame[natural_key].isna().any(axis=1).sum()),
    }


def max_abs(series: pd.Series) -> float:
    return float(series.abs().max()) if len(series) else 0.0


def validate(
    project_root: Path,
    icio: pd.DataFrame,
    icio_schema: pa.Schema,
    sector_crosswalk: pd.DataFrame,
    sector_schema: pa.Schema,
    country_crosswalk: pd.DataFrame,
    country_schema: pa.Schema,
    source_long: pd.DataFrame,
    analysis_long: pd.DataFrame,
    cells: pd.DataFrame,
    context: dict[str, Any],
    config: dict[str, Any],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    inputs = config["inputs"]
    outputs = config["outputs"]
    validation_cfg = config["validation"]
    tolerance = float(validation_cfg["monetary_tolerance_million_usd"])
    contracts = {
        "icio_output": input_contract(
            icio,
            icio_schema,
            project_root / inputs["icio_output"]["path"],
            inputs["icio_output"],
        ),
        "source_sector_crosswalk": input_contract(
            sector_crosswalk,
            sector_schema,
            project_root / inputs["source_sector_crosswalk"]["path"],
            inputs["source_sector_crosswalk"],
        ),
        "country_crosswalk": input_contract(
            country_crosswalk,
            country_schema,
            project_root / inputs["country_crosswalk"]["path"],
            inputs["country_crosswalk"],
        ),
    }
    for name, contract in contracts.items():
        if not (
            contract["hash_match"]
            and contract["row_count_match"]
            and contract["column_count_match"]
            and contract["schema_match"]
            and contract["duplicate_key_count"] == 0
            and contract["key_null_count"] == 0
        ):
            failures.append(f"frozen input contract failed: {name}")

    source_name = config["source_contract"]["source_crosswalk_name"]
    sectors = sector_crosswalk.loc[sector_crosswalk["source_name"].eq(source_name)]
    countries = country_crosswalk.loc[country_crosswalk["source_name"].eq(source_name)]
    crosswalk_checks = {
        "filtered_sector_rows": int(len(sectors)),
        "expected_filtered_sector_rows": int(
            inputs["source_sector_crosswalk"]["expected_filtered_rows"]
        ),
        "filtered_sector_key_duplicates": int(
            sectors.duplicated(["source_sector_level", "source_sector_code"]).sum()
        ),
        "filtered_country_rows": int(len(countries)),
        "expected_filtered_country_rows": int(
            inputs["country_crosswalk"]["expected_filtered_rows"]
        ),
        "filtered_country_key_duplicates": int(
            countries.duplicated(["source_country_id"]).sum()
        ),
        "sector_mapping_versions": sorted(
            sectors["mapping_version"].dropna().unique().tolist()
        ),
        "eligible_sector_count": int(sectors["is_main_join_eligible"].sum()),
        "eligible_weight_one_count": int(
            sectors.loc[sectors["is_main_join_eligible"], "mapping_weight"].eq(1).sum()
        ),
        "source_sector_code_count": int(sectors["source_sector_code"].nunique()),
        "source_country_id_count": int(countries["source_country_id"].nunique()),
    }
    if not (
        crosswalk_checks["filtered_sector_rows"]
        == crosswalk_checks["expected_filtered_sector_rows"]
        and crosswalk_checks["filtered_sector_key_duplicates"] == 0
        and crosswalk_checks["filtered_country_rows"]
        == crosswalk_checks["expected_filtered_country_rows"]
        and crosswalk_checks["filtered_country_key_duplicates"] == 0
        and crosswalk_checks["sector_mapping_versions"]
        == [inputs["source_sector_crosswalk"]["expected_mapping_version"]]
        and crosswalk_checks["eligible_sector_count"] == 16
        and crosswalk_checks["eligible_weight_one_count"] == 16
        and crosswalk_checks["source_sector_code_count"] == 50
        and crosswalk_checks["source_country_id_count"] == 81
    ):
        failures.append("filtered country/sector crosswalk contract failed")
    if not (
        context["sector_join_status_counts"].get("both", 0) == len(icio)
        and context["sector_join_status_counts"].get("left_only", 0) == 0
        and context["sector_join_status_counts"].get("right_only", 0) == 0
    ):
        failures.append("one or more ICIO sector codes did not match")
    if not (
        context["country_join_status_counts"].get("both", 0) == len(icio)
        and context["country_join_status_counts"].get("left_only", 0) == 0
        and context["country_join_status_counts"].get("right_only", 0) == 0
    ):
        failures.append("one or more ICIO country codes did not match")

    source_checks = {
        "rows": int(len(source_long)),
        "expected_rows": int(outputs["source_long"]["expected_rows"]),
        "columns": int(len(source_long.columns)),
        "expected_columns": int(outputs["source_long"]["expected_columns"]),
        "duplicate_key_count": int(source_long.duplicated(SOURCE_LONG_KEY).sum()),
        "key_null_count": int(source_long[SOURCE_LONG_KEY].isna().any(axis=1).sum()),
        "source_cell_count": int(source_long[SOURCE_CELL_KEY].drop_duplicates().shape[0]),
        "metric_count": int(source_long["metric_name"].nunique()),
        "rows_per_source_cell_min": int(
            source_long.groupby(SOURCE_CELL_KEY, observed=True).size().min()
        ),
        "rows_per_source_cell_max": int(
            source_long.groupby(SOURCE_CELL_KEY, observed=True).size().max()
        ),
    }
    if not (
        source_checks["rows"] == source_checks["expected_rows"]
        and source_checks["columns"] == source_checks["expected_columns"]
        and source_checks["duplicate_key_count"] == 0
        and source_checks["key_null_count"] == 0
        and source_checks["source_cell_count"]
        == int(validation_cfg["expected_full_source_rows"])
        and source_checks["metric_count"] == len(config["metrics"])
        and source_checks["rows_per_source_cell_min"] == len(config["metrics"])
        and source_checks["rows_per_source_cell_max"] == len(config["metrics"])
    ):
        failures.append("source-sector long output shape/key/grid failed")

    long_checks = {
        "rows": int(len(analysis_long)),
        "expected_rows": int(outputs["analysis_long"]["expected_rows"]),
        "columns": int(len(analysis_long.columns)),
        "expected_columns": int(outputs["analysis_long"]["expected_columns"]),
        "duplicate_key_count": int(
            analysis_long.duplicated(ANALYSIS_LONG_KEY).sum()
        ),
        "key_null_count": int(
            analysis_long[ANALYSIS_LONG_KEY].isna().any(axis=1).sum()
        ),
    }
    if not (
        long_checks["rows"] == long_checks["expected_rows"]
        and long_checks["columns"] == long_checks["expected_columns"]
        and long_checks["duplicate_key_count"] == 0
        and long_checks["key_null_count"] == 0
    ):
        failures.append("analysis-sector long output shape/key failed")

    raw = icio.rename(
        columns={"country_iso3": "source_country_id", "sector_oecd": "model_sector"}
    ).copy()
    source_pivot = source_long.pivot(
        index=["source_country_id", "model_sector", "year"],
        columns="metric_name",
        values="value",
    ).reset_index()
    source_pivot_compare = source_pivot.rename(
        columns={metric: f"output__{metric}" for metric in config["metrics"]}
    )
    raw_compare = raw.merge(
        source_pivot_compare,
        on=["source_country_id", "model_sector", "year"],
        how="left",
        validate="one_to_one",
        suffixes=("_raw", "_out"),
    )
    source_preservation: dict[str, Any] = {}
    for metric_name, rules in config["metrics"].items():
        source_field = rules["source_field"]
        if source_field == "production_accounting_residual":
            expected = raw_compare["gross_output"] - (
                raw_compare["intermediate_inputs"]
                + raw_compare["taxes_less_subsidies"]
                + raw_compare["value_added"]
            )
        else:
            expected = raw_compare[source_field]
        error = max_abs(raw_compare[f"output__{metric_name}"] - expected)
        source_preservation[metric_name] = {
            "maximum_absolute_error": error,
            "within_tolerance": error <= float(validation_cfg["numeric_tolerance"]),
        }
    source_files = source_long[
        SOURCE_CELL_KEY + ["source_file"]
    ].drop_duplicates()
    file_check = raw.merge(
        source_files,
        on=["source_country_id", "model_sector", "year"],
        how="left",
        validate="one_to_one",
        suffixes=("_raw", "_out"),
    )
    source_preservation["source_file_mismatch_count"] = int(
        file_check["source_file_raw"].ne(file_check["source_file_out"]).sum()
    )
    if not (
        all(
            result["within_tolerance"]
            for key, result in source_preservation.items()
            if key != "source_file_mismatch_count"
        )
        and source_preservation["source_file_mismatch_count"] == 0
    ):
        failures.append("source metrics or source_file were not preserved")

    production_residual = raw["gross_output"] - (
        raw["intermediate_inputs"]
        + raw["taxes_less_subsidies"]
        + raw["value_added"]
    )
    sales_residual = raw["gross_output_sales"] - (
        raw["intermediate_sales"] + raw["final_demand"]
    )
    source_residual_from_long = source_pivot["gross_output"] - (
        source_pivot["intermediate_inputs"]
        + source_pivot["taxes_less_subsidies"]
        + source_pivot["value_added"]
    )
    residual_formula_checks = {
        "max_abs_source_production_formula_error": max_abs(
            source_pivot["accounting_residual"] - source_residual_from_long
        ),
        "max_abs_source_production_residual": max_abs(production_residual),
        "expected_max_abs_source_production_residual": float(
            validation_cfg["expected_max_abs_source_production_residual"]
        ),
        "max_abs_source_sales_residual": max_abs(sales_residual),
        "expected_max_abs_source_sales_residual": float(
            validation_cfg["expected_max_abs_source_sales_residual"]
        ),
    }
    if not (
        residual_formula_checks["max_abs_source_production_formula_error"]
        <= float(validation_cfg["numeric_tolerance"])
        and abs(
            residual_formula_checks["max_abs_source_production_residual"]
            - residual_formula_checks["expected_max_abs_source_production_residual"]
        )
        <= float(validation_cfg["numeric_tolerance"])
        and abs(
            residual_formula_checks["max_abs_source_sales_residual"]
            - residual_formula_checks["expected_max_abs_source_sales_residual"]
        )
        <= float(validation_cfg["numeric_tolerance"])
    ):
        failures.append("source accounting residual formula or frozen maxima failed")

    classification_counts = {
        "full_source_rows": int(len(cells)),
        "country_rows": int(cells["country_is_country"].sum()),
        "aggregate_geography_rows": int(cells["country_is_aggregate"].sum()),
        "sector_join_eligible_rows_all_geographies": int(
            cells["sector_is_main_join_eligible"].sum()
        ),
        "main_analysis_join_eligible_source_rows": int(
            cells["main_analysis_join_eligible"].sum()
        ),
        "main_analysis_excluded_source_rows": int(
            (~cells["main_analysis_join_eligible"]).sum()
        ),
        "main_first_round_excluded_source_rows": int(
            (
                cells["country_is_country"]
                & cells["sector_mapping_status"].eq("first_round_excluded")
            ).sum()
        ),
        "main_outside_manufacturing_source_rows": int(
            (
                cells["country_is_country"]
                & cells["sector_mapping_status"].eq("outside_manufacturing")
            ).sum()
        ),
        "partition_total": int(
            cells["country_is_aggregate"].sum()
            + cells["main_analysis_join_eligible"].sum()
            + (
                cells["country_is_country"]
                & cells["sector_mapping_status"].eq("first_round_excluded")
            ).sum()
            + (
                cells["country_is_country"]
                & cells["sector_mapping_status"].eq("outside_manufacturing")
            ).sum()
        ),
    }
    expected_classification = {
        key.removeprefix("expected_"): int(value)
        for key, value in validation_cfg.items()
        if key.startswith("expected_")
        and key
        in {
            "expected_full_source_rows",
            "expected_country_rows",
            "expected_aggregate_geography_rows",
            "expected_sector_join_eligible_rows_all_geographies",
            "expected_main_analysis_join_eligible_source_rows",
            "expected_main_analysis_excluded_source_rows",
            "expected_main_first_round_excluded_source_rows",
            "expected_main_outside_manufacturing_source_rows",
        }
    }
    if not (
        all(
            classification_counts[key] == expected
            for key, expected in expected_classification.items()
        )
        and classification_counts["partition_total"]
        == classification_counts["full_source_rows"]
    ):
        failures.append("source-universe classification or partition failed")

    source_negative_counts = {
        metric: int(
            source_long.loc[source_long["metric_name"].eq(metric), "value"].lt(0).sum()
        )
        for metric in config["metrics"]
    }
    source_negative_counts["sales_accounting_residual"] = int(
        sales_residual.lt(0).sum()
    )
    expected_source_negative = {
        "value_added": int(
            validation_cfg["expected_source_value_added_negative_count"]
        ),
        "taxes_less_subsidies": int(
            validation_cfg["expected_source_taxes_less_subsidies_negative_count"]
        ),
        "accounting_residual": int(
            validation_cfg["expected_source_production_residual_negative_count"]
        ),
        "sales_accounting_residual": int(
            validation_cfg["expected_source_sales_residual_negative_count"]
        ),
    }
    if any(
        source_negative_counts[name] != expected
        for name, expected in expected_source_negative.items()
    ):
        failures.append("source negative accounting-cell counts changed")
    main_source = source_long.loc[source_long["main_analysis_join_eligible"]]
    main_source_negative_counts = {
        metric: int(
            main_source.loc[main_source["metric_name"].eq(metric), "value"].lt(0).sum()
        )
        for metric in config["metrics"]
    }
    expected_main_negative = {
        "value_added": int(
            validation_cfg["expected_main_source_value_added_negative_count"]
        ),
        "taxes_less_subsidies": int(
            validation_cfg[
                "expected_main_source_taxes_less_subsidies_negative_count"
            ]
        ),
        "accounting_residual": int(
            validation_cfg[
                "expected_main_source_production_residual_negative_count"
            ]
        ),
    }
    if any(
        main_source_negative_counts[name] != expected
        for name, expected in expected_main_negative.items()
    ):
        failures.append("eligible source negative accounting-cell counts changed")

    analysis_negative_counts = {
        metric: int(
            analysis_long.loc[
                analysis_long["metric_name"].eq(metric), "value"
            ].lt(0).sum()
        )
        for metric in config["metrics"]
    }
    analysis_zero_counts = {
        metric: int(
            analysis_long.loc[
                analysis_long["metric_name"].eq(metric), "value"
            ].eq(0).sum()
        )
        for metric in config["metrics"]
    }
    if analysis_negative_counts != {
        key: int(value)
        for key, value in validation_cfg[
            "expected_analysis_long_negative_counts"
        ].items()
    }:
        failures.append("analysis-long negative counts changed")
    if analysis_zero_counts != {
        key: int(value)
        for key, value in validation_cfg[
            "expected_analysis_long_zero_counts"
        ].items()
    }:
        failures.append("analysis-long zero counts changed")

    eligible_grouped = (
        main_source.groupby(
            ["country_iso3", "analysis_sector", "year", "source_name", "metric_name"],
            sort=False,
            observed=True,
        )["value"]
        .sum()
        .reset_index(name="source_value")
    )
    grouped_compare = eligible_grouped.merge(
        analysis_long[ANALYSIS_LONG_KEY + ["value"]].rename(
            columns={"value": "analysis_value"}
        ),
        on=ANALYSIS_LONG_KEY,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    grouped_compare["absolute_error"] = (
        grouped_compare["analysis_value"] - grouped_compare["source_value"]
    ).abs()
    maximum_group_error = max_abs(grouped_compare["absolute_error"])
    metric_reconciliation: dict[str, Any] = {}
    full_universe_reconciliation: dict[str, Any] = {}
    for metric in config["metrics"]:
        src = main_source.loc[main_source["metric_name"].eq(metric), "value"]
        out = analysis_long.loc[
            analysis_long["metric_name"].eq(metric), "value"
        ]
        source_total = float(src.sum())
        analysis_total = float(out.sum())
        metric_reconciliation[metric] = {
            "eligible_source_total": source_total,
            "analysis_total": analysis_total,
            "absolute_difference": abs(source_total - analysis_total),
            "within_tolerance": abs(source_total - analysis_total) <= tolerance,
        }
        full = float(
            source_long.loc[source_long["metric_name"].eq(metric), "value"].sum()
        )
        excluded = float(
            source_long.loc[
                source_long["metric_name"].eq(metric)
                & ~source_long["main_analysis_join_eligible"],
                "value",
            ].sum()
        )
        partition_error = abs(full - source_total - excluded)
        full_universe_reconciliation[metric] = {
            "full_source_total": full,
            "eligible_total": source_total,
            "excluded_total": excluded,
            "absolute_partition_error": partition_error,
            "within_tolerance": partition_error <= tolerance,
        }
    if not (
        grouped_compare["_merge"].eq("both").all()
        and maximum_group_error <= tolerance
        and all(value["within_tolerance"] for value in metric_reconciliation.values())
        and all(
            value["within_tolerance"]
            for value in full_universe_reconciliation.values()
        )
    ):
        failures.append("source-to-analysis or full-universe reconciliation failed")

    analysis_pivot = analysis_long.pivot(
        index=["country_iso3", "analysis_sector", "year"],
        columns="metric_name",
        values="value",
    )
    analysis_residual_error = max_abs(
        analysis_pivot["accounting_residual"]
        - (
            analysis_pivot["gross_output"]
            - analysis_pivot["intermediate_inputs"]
            - analysis_pivot["taxes_less_subsidies"]
            - analysis_pivot["value_added"]
        )
    )
    if analysis_residual_error > tolerance:
        failures.append("analysis accounting residual did not independently recompute")
    residual_formula_checks[
        "max_abs_analysis_accounting_formula_error"
    ] = analysis_residual_error

    expected_years = sorted(inputs["icio_output"]["expected_years"])
    expected_metrics = list(config["metrics"])
    grid_checks = {
        "country_count": int(analysis_long["country_iso3"].nunique()),
        "analysis_sector_count": int(analysis_long["analysis_sector"].nunique()),
        "country_sector_year_cell_count": int(
            analysis_long[
                ["country_iso3", "analysis_sector", "year"]
            ].drop_duplicates().shape[0]
        ),
        "metric_count": int(analysis_long["metric_name"].nunique()),
        "observed_years": sorted(analysis_long["year"].unique().tolist()),
        "expected_years": expected_years,
        "observed_metrics": sorted(analysis_long["metric_name"].unique().tolist()),
        "expected_metrics": sorted(expected_metrics),
        "rows_per_cell_min": int(
            analysis_long.groupby(
                ["country_iso3", "analysis_sector", "year"], observed=True
            ).size().min()
        ),
        "rows_per_cell_max": int(
            analysis_long.groupby(
                ["country_iso3", "analysis_sector", "year"], observed=True
            ).size().max()
        ),
        "medical_devices_rows": int(
            analysis_long["analysis_sector"].eq("medical_devices").sum()
        ),
    }
    if not (
        grid_checks["country_count"]
        == int(outputs["analysis_long"]["expected_country_count"])
        and grid_checks["analysis_sector_count"]
        == int(outputs["analysis_long"]["expected_analysis_sector_count"])
        and grid_checks["country_sector_year_cell_count"]
        == int(outputs["analysis_long"]["expected_country_sector_year_cells"])
        and grid_checks["metric_count"] == len(expected_metrics)
        and grid_checks["observed_years"] == expected_years
        and grid_checks["observed_metrics"] == sorted(expected_metrics)
        and grid_checks["rows_per_cell_min"] == len(expected_metrics)
        and grid_checks["rows_per_cell_max"] == len(expected_metrics)
        and grid_checks["medical_devices_rows"]
        == int(validation_cfg["expected_medical_devices_rows"])
    ):
        failures.append("analysis-long country/sector/year/metric grid failed")

    connector_count = int(
        analysis_long.loc[
            analysis_long["comparison_sample_country_flag"], "country_iso3"
        ].nunique()
    )
    connector_rows = int(analysis_long["comparison_sample_country_flag"].sum())
    sample_checks = {
        "connector_country_count": connector_count,
        "expected_connector_country_count": int(
            validation_cfg["expected_connector_country_count"]
        ),
        "connector_long_rows": connector_rows,
        "expected_connector_long_rows": int(
            validation_cfg["expected_connector_long_rows"]
        ),
        "role_overlap_rows": int(
            analysis_long[
                ["is_core_connector", "is_asian_comparator", "is_other_candidate"]
            ]
            .astype("int8")
            .sum(axis=1)
            .gt(1)
            .sum()
        ),
    }
    if not (
        sample_checks["connector_country_count"]
        == sample_checks["expected_connector_country_count"]
        and sample_checks["connector_long_rows"]
        == sample_checks["expected_connector_long_rows"]
        and sample_checks["role_overlap_rows"] == 0
    ):
        failures.append("connector/comparator sample flags failed")

    source_flag_checks = {
        "aggregate_rows": int(source_long["aggregate_flag"].sum()),
        "expected_aggregate_rows": int(
            validation_cfg["expected_aggregate_geography_rows"]
            * len(config["metrics"])
        ),
        "residual_rows": int(source_long["residual_flag"].sum()),
        "proxy_rows": int(source_long["proxy_flag"].sum()),
        "main_join_rows": int(source_long["main_analysis_join_eligible"].sum()),
        "expected_main_join_rows": int(
            validation_cfg["expected_main_analysis_join_eligible_source_rows"]
            * len(config["metrics"])
        ),
        "observed_negative_flag_mismatches": int(
            source_long["observed_negative_flag"].ne(source_long["value"].lt(0)).sum()
        ),
        "observed_zero_flag_mismatches": int(
            source_long["observed_zero_flag"].ne(source_long["value"].eq(0)).sum()
        ),
    }
    analysis_flag_checks = {
        "suppressed_true_count": int(analysis_long["suppressed_flag"].sum()),
        "confidential_true_count": int(analysis_long["confidential_flag"].sum()),
        "aggregate_true_count": int(analysis_long["aggregate_flag"].sum()),
        "residual_true_count": int(analysis_long["residual_flag"].sum()),
        "proxy_true_count": int(analysis_long["proxy_flag"].sum()),
        "can_sum_across_metrics_true_count": int(
            analysis_long["can_sum_across_metrics"].sum()
        ),
        "metric_additive_across_source_sectors_all_true": bool(
            analysis_long["metric_additive_across_source_sectors"].all()
        ),
        "parent_country_all_missing": bool(
            analysis_long["parent_country_iso3"].isna().all()
        ),
        "direction_values": sorted(
            analysis_long["direction"].dropna().unique().tolist()
        ),
        "direct_or_allocated_values": sorted(
            analysis_long["direct_or_allocated"].dropna().unique().tolist()
        ),
        "multi_source_sector_rows": int(
            analysis_long[
                "analysis_sector_aggregates_multiple_source_sectors"
            ].sum()
        ),
        "direct_source_sector_rows": int(
            analysis_long[
                "analysis_sector_is_direct_from_one_source_sector"
            ].sum()
        ),
    }
    if not (
        source_flag_checks["aggregate_rows"]
        == source_flag_checks["expected_aggregate_rows"]
        and source_flag_checks["residual_rows"] == 0
        and source_flag_checks["proxy_rows"] == 0
        and source_flag_checks["main_join_rows"]
        == source_flag_checks["expected_main_join_rows"]
        and source_flag_checks["observed_negative_flag_mismatches"] == 0
        and source_flag_checks["observed_zero_flag_mismatches"] == 0
    ):
        failures.append("source-long status flags failed")
    if not (
        analysis_flag_checks["suppressed_true_count"] == 0
        and analysis_flag_checks["confidential_true_count"] == 0
        and analysis_flag_checks["aggregate_true_count"] == 0
        and analysis_flag_checks["residual_true_count"] == 0
        and analysis_flag_checks["proxy_true_count"] == 0
        and analysis_flag_checks["can_sum_across_metrics_true_count"] == 0
        and analysis_flag_checks["metric_additive_across_source_sectors_all_true"]
        and analysis_flag_checks["parent_country_all_missing"]
        and analysis_flag_checks["direction_values"] == ["not_applicable"]
        and analysis_flag_checks["direct_or_allocated_values"] == ["direct"]
        and analysis_flag_checks["multi_source_sector_rows"] == 80 * 3 * 7
        and analysis_flag_checks["direct_source_sector_rows"] == 80 * 5 * 3 * 7
    ):
        failures.append("analysis-long status/additivity flags failed")

    alias_checks = {
        "source_long": alias_validation(
            source_long, outputs["source_long"]["stata_aliases"]
        ),
        "analysis_long": alias_validation(
            analysis_long, outputs["analysis_long"]["stata_aliases"]
        ),
    }
    if not all(check["pass"] for check in alias_checks.values()):
        failures.append("one or more Stata alias contracts failed")
    metadata_checks = {
        "source_version": sorted(source_long["m4_icio_version"].unique().tolist())
        == [config["version"]],
        "analysis_version": sorted(
            analysis_long["m4_icio_version"].unique().tolist()
        )
        == [config["version"]],
        "source_schema": sorted(source_long["schema_version"].unique().tolist())
        == [outputs["source_long"]["schema_version"]],
        "analysis_schema": sorted(analysis_long["schema_version"].unique().tolist())
        == [outputs["analysis_long"]["schema_version"]],
        "config_hash_source": sorted(
            source_long["rules_config_sha256"].unique().tolist()
        )
        == [determinism["config_sha256"]],
        "config_hash_analysis": sorted(
            analysis_long["rules_config_sha256"].unique().tolist()
        )
        == [determinism["config_sha256"]],
        "finite_values": bool(
            np.isfinite(source_long["value"].to_numpy(dtype="float64")).all()
            and np.isfinite(
                analysis_long["value"].to_numpy(dtype="float64")
            ).all()
        ),
    }
    if not all(metadata_checks.values()):
        failures.append("version/schema/config-hash/finite-value checks failed")
    if not (
        determinism["source_long_sha256_match"]
        and determinism["analysis_long_sha256_match"]
        and determinism["temporary_output_cleaned"]
    ):
        failures.append("deterministic rebuild failed")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "input_contracts": contracts,
        "crosswalk_checks": crosswalk_checks,
        "join_status_counts": context,
        "source_long_checks": source_checks,
        "analysis_long_checks": long_checks,
        "source_preservation": source_preservation,
        "residual_formula_checks": residual_formula_checks,
        "classification_counts": classification_counts,
        "classification_expected": expected_classification,
        "source_negative_counts": source_negative_counts,
        "source_negative_expected": expected_source_negative,
        "main_eligible_source_negative_counts": main_source_negative_counts,
        "main_eligible_source_negative_expected": expected_main_negative,
        "analysis_long_negative_counts": analysis_negative_counts,
        "analysis_long_zero_counts": analysis_zero_counts,
        "metric_reconciliation": metric_reconciliation,
        "full_universe_reconciliation": full_universe_reconciliation,
        "maximum_country_sector_year_reconciliation_error": maximum_group_error,
        "grid_checks": grid_checks,
        "sample_checks": sample_checks,
        "source_flag_checks": source_flag_checks,
        "analysis_flag_checks": analysis_flag_checks,
        "stata_alias_validation": alias_checks,
        "metadata_checks": metadata_checks,
        "determinism_check": determinism,
        "monetary_tolerance_million_usd": tolerance,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    source = validation["outputs"]["source_long"]
    analysis = validation["outputs"]["analysis_long"]
    grid = validation["grid_checks"]
    classes = validation["classification_counts"]
    residuals = validation["residual_formula_checks"]
    aliases = validation["stata_alias_validation"]
    lines = [
        "# M4.1 OECD ICIO Production-Side Validation",
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
        f"- Validation status: **{validation['validation_status']}**.",
        (
            f"- Source-sector audit long: `{source['path']}`; "
            f"`{validation['source_long_checks']['rows']} × "
            f"{validation['source_long_checks']['columns']}`; SHA256 `{source['sha256']}`."
        ),
        (
            f"- Analysis-sector long: `{analysis['path']}`; "
            f"`{validation['analysis_long_checks']['rows']} × "
            f"{validation['analysis_long_checks']['columns']}`; SHA256 `{analysis['sha256']}`."
        ),
        "- Both natural keys are unique; both deterministic second-build hashes match.",
        (
            "- Candidate and determinism temporary directories cleaned: "
            f"`{validation.get('candidate_temporary_output_cleaned', False)}` / "
            f"`{validation['determinism_check']['temporary_output_cleaned']}`."
        ),
        "",
        "## Frozen Inputs and Mapping",
        "",
        "- OECD ICIO input: 12,150 rows, 81 geographies, 50 sectors, years 2017/2018/2022.",
        "- All source codes match canonical country and sector crosswalks many-to-one.",
        (
            "- The audit long retains all 12,150 source cells × 7 metrics, including "
            "ROW, first-round exclusions, and outside-manufacturing sectors."
        ),
        (
            f"- Main eligibility: `{classes['main_analysis_join_eligible_source_rows']}` "
            f"source cells; `{classes['main_analysis_excluded_source_rows']}` "
            "source cells remain outside the analysis long and are reconciled."
        ),
        "- Six ICIO-supported analysis sectors are retained; medical devices are not fabricated.",
        "",
        "## Output Grid and Metrics",
        "",
        (
            f"- Analysis grid: `{grid['country_count']}` countries × "
            f"`{grid['analysis_sector_count']}` sectors × 3 years × "
            f"`{grid['metric_count']}` metrics = "
            f"`{validation['analysis_long_checks']['rows']}` rows."
        ),
        "- Metrics: gross output, value added, exports, imports, intermediate inputs, taxes less subsidies, and accounting residual.",
        "- Other manufacturing sums 11 source sectors; the other five supported sectors map one-to-one.",
        "- Different metrics are non-additive. No ICIO year is interpolated or imputed.",
        "",
        "## Accounting and Exception Preservation",
        "",
        (
            "- Maximum absolute source production/sales residuals: "
            f"`{residuals['max_abs_source_production_residual']:.12g}` / "
            f"`{residuals['max_abs_source_sales_residual']:.12g}` current million USD."
        ),
        (
            "- Source negative counts for value added / taxes less subsidies / "
            "production residual / sales residual: "
            f"`{validation['source_negative_counts']['value_added']} / "
            f"{validation['source_negative_counts']['taxes_less_subsidies']} / "
            f"{validation['source_negative_counts']['accounting_residual']} / "
            f"{validation['source_negative_counts']['sales_accounting_residual']}`."
        ),
        "- Negative accounting values remain signed and are flagged; none are recoded to zero.",
        "- Eligible plus excluded values reconcile to the full source universe for every metric.",
        (
            "- Source-to-analysis values reconcile within "
            f"`{validation['monetary_tolerance_million_usd']}` million USD."
        ),
        "",
        "## Stata and Interpretation Boundary",
        "",
        (
            f"- Stata aliases: source long `{aliases['source_long']['alias_count']}`, "
            f"analysis long `{aliases['analysis_long']['alias_count']}`; "
            "all complete, unique, legal, and at most 32 characters."
        ),
        "- Parquet remains canonical; .dta export remains an M7 task.",
        "- ICIO production values are aggregate validation evidence, not firm-level relocation proof or causal estimates.",
        "- This module does not add AMNE, BEA, FDI, national statistics, rankings, structural moments, or welfare inputs.",
    ]
    if validation["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in validation["failures"])
    return "\n".join(lines) + "\n"


def deterministic_rebuild(
    project_root: Path,
    config: dict[str, Any],
    config_hash: str,
    candidate_source: Path,
    candidate_analysis: Path,
) -> dict[str, Any]:
    directory = validate_project_temp_path(
        project_root, config["validation"]["determinism_temp_directory"]
    )
    if directory.exists():
        raise FileExistsError(f"Refusing to reuse determinism directory: {directory}")
    directory.mkdir(parents=True)
    second_source = directory / f"{candidate_source.stem}_second.parquet"
    second_analysis = directory / f"{candidate_analysis.stem}_second.parquet"
    result: dict[str, Any] = {"config_sha256": config_hash}
    try:
        icio, _, sectors, _, countries, _ = read_inputs(project_root, config)
        source_long, analysis_long, _, _ = build_outputs(
            icio, sectors, countries, config, config_hash
        )
        write_parquet(source_long, second_source, source_long_schema())
        write_parquet(analysis_long, second_analysis, analysis_long_schema())
        result.update(
            {
                "source_long_candidate_sha256": sha256(candidate_source),
                "source_long_second_build_sha256": sha256(second_source),
                "source_long_sha256_match": sha256(candidate_source)
                == sha256(second_source),
                "analysis_long_candidate_sha256": sha256(candidate_analysis),
                "analysis_long_second_build_sha256": sha256(second_analysis),
                "analysis_long_sha256_match": sha256(candidate_analysis)
                == sha256(second_analysis),
            }
        )
    finally:
        remove_owned_temp_directory(directory)
    result["temporary_output_cleaned"] = not directory.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate the M4.1 OECD ICIO source-sector and "
            "analysis-sector production long tables."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config", type=Path, default=Path("configs/production_icio_rules.yaml")
    )
    parser.add_argument("--source-long-output", type=Path)
    parser.add_argument("--analysis-long-output", type=Path)
    parser.add_argument("--validation-json", type=Path)
    parser.add_argument("--validation-md", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    config_path = relative_or_absolute(project_root, args.config).resolve()
    config = load_yaml(config_path)
    config_hash = sha256(config_path)
    source_path = relative_or_absolute(
        project_root,
        args.source_long_output or Path(config["outputs"]["source_long"]["path"]),
    ).resolve()
    analysis_path = relative_or_absolute(
        project_root,
        args.analysis_long_output
        or Path(config["outputs"]["analysis_long"]["path"]),
    ).resolve()
    validation_json = relative_or_absolute(
        project_root,
        args.validation_json or Path(config["validation_outputs"]["json"]),
    ).resolve()
    validation_md = relative_or_absolute(
        project_root,
        args.validation_md or Path(config["validation_outputs"]["markdown"]),
    ).resolve()
    for path in [source_path, analysis_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    candidate_directory = validate_project_temp_path(
        project_root, config["validation"]["candidate_temp_directory"]
    )
    if candidate_directory.exists():
        raise FileExistsError(
            f"Refusing to reuse candidate directory: {candidate_directory}"
        )
    candidate_directory.mkdir(parents=True)
    candidate_source = candidate_directory / source_path.name
    candidate_analysis = candidate_directory / analysis_path.name
    candidate_json = candidate_directory / validation_json.name
    candidate_md = candidate_directory / validation_md.name
    try:
        (
            icio,
            icio_schema,
            sectors,
            sector_schema,
            countries,
            country_schema,
        ) = read_inputs(project_root, config)
        source_long, analysis_long, cells, context = build_outputs(
            icio, sectors, countries, config, config_hash
        )
        source_table = write_parquet(
            source_long, candidate_source, source_long_schema()
        )
        analysis_table = write_parquet(
            analysis_long, candidate_analysis, analysis_long_schema()
        )
        determinism = deterministic_rebuild(
            project_root,
            config,
            config_hash,
            candidate_source,
            candidate_analysis,
        )
        validation = validate(
            project_root,
            icio,
            icio_schema,
            sectors,
            sector_schema,
            countries,
            country_schema,
            source_long,
            analysis_long,
            cells,
            context,
            config,
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
                    "source_long": {
                        "path": source_path.relative_to(project_root).as_posix(),
                        "sha256": sha256(candidate_source),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in source_table.schema
                        ],
                    },
                    "analysis_long": {
                        "path": analysis_path.relative_to(project_root).as_posix(),
                        "sha256": sha256(candidate_analysis),
                        "schema": [
                            {
                                "name": field.name,
                                "type": str(field.type),
                                "nullable": field.nullable,
                            }
                            for field in analysis_table.schema
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
        candidate_json.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        candidate_md.write_text(
            markdown_report(validation), encoding="utf-8", newline="\n"
        )
        for path in [source_path, analysis_path, validation_json, validation_md]:
            path.parent.mkdir(parents=True, exist_ok=True)
        candidate_source.replace(source_path)
        candidate_analysis.replace(analysis_path)
        candidate_json.replace(validation_json)
        candidate_md.replace(validation_md)
        remove_owned_temp_directory(candidate_directory)
        validation["candidate_temporary_output_cleaned"] = (
            not candidate_directory.exists()
        )
        validation_json.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        validation_md.write_text(
            markdown_report(validation), encoding="utf-8", newline="\n"
        )
        print(
            json.dumps(
                {
                    "validation_status": validation["validation_status"],
                    "source_long_rows": validation["source_long_checks"]["rows"],
                    "analysis_long_rows": validation["analysis_long_checks"]["rows"],
                    "source_long_sha256": validation["outputs"]["source_long"][
                        "sha256"
                    ],
                    "analysis_long_sha256": validation["outputs"]["analysis_long"][
                        "sha256"
                    ],
                    "deterministic_sha256_match": bool(
                        determinism["source_long_sha256_match"]
                        and determinism["analysis_long_sha256_match"]
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
