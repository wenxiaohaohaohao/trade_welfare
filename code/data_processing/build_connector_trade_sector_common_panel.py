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


KEY = ["connector_iso3", "analysis_sector"]


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


def mismatch_count(left: pd.Series, right: pd.Series) -> int:
    if len(left) != len(right):
        raise ValueError("Cannot compare Series with different lengths")
    left = left.reset_index(drop=True)
    right = right.reset_index(drop=True)
    both_missing = left.isna() & right.isna()
    equal = left.eq(right).fillna(False)
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
    sector_path = project_root / config["inputs"]["sector_reorganization"]["path"]
    comovement_path = (
        project_root / config["inputs"]["product_comovement"]["path"]
    )
    sector_table = pq.read_table(sector_path)
    comovement_table = pq.read_table(comovement_path)
    analysis_sample = load_yaml(
        project_root / config["inputs"]["analysis_sample"]["path"]
    )
    country_groups = load_yaml(
        project_root / config["inputs"]["country_groups"]["path"]
    )
    return (
        sector_table.to_pandas(),
        sector_table.schema,
        comovement_table.to_pandas(),
        comovement_table.schema,
        analysis_sample,
        country_groups,
    )


def sample_maps(
    config: dict[str, Any],
) -> tuple[
    dict[str, str],
    dict[str, int],
    dict[str, int],
    dict[str, int],
    dict[str, int],
]:
    connector_group: dict[str, str] = {}
    group_order: dict[str, int] = {}
    within_group_order: dict[str, int] = {}
    group_connector_count: dict[str, int] = {}
    for group, details in config["sample"]["groups"].items():
        connectors = list(details["connectors"])
        group_connector_count[group] = len(connectors)
        for within_order, connector in enumerate(connectors, start=1):
            if connector in connector_group:
                raise ValueError(f"Connector appears in multiple groups: {connector}")
            connector_group[connector] = group
            group_order[connector] = int(details["order"])
            within_group_order[connector] = within_order
    sector_order = {
        sector: order
        for order, sector in enumerate(config["sample"]["sectors"], start=1)
    }
    return (
        connector_group,
        group_order,
        within_group_order,
        group_connector_count,
        sector_order,
    )


def build_output(
    sector: pd.DataFrame,
    comovement: pd.DataFrame,
    config: dict[str, Any],
    config_hash: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    if sector.duplicated(KEY).any() or comovement.duplicated(KEY).any():
        raise ValueError("M3.5 inputs must be unique at connector-sector level")

    overlap_fields = list(config["join"]["overlapping_fields"])
    merged_overlap = sector[overlap_fields].merge(
        comovement[overlap_fields],
        on=KEY,
        how="outer",
        validate="one_to_one",
        suffixes=("_sector", "_comovement"),
        indicator=True,
        sort=False,
    )
    overlap_mismatches: dict[str, int] = {}
    for field in overlap_fields:
        if field in KEY:
            continue
        overlap_mismatches[field] = mismatch_count(
            merged_overlap[f"{field}_sector"],
            merged_overlap[f"{field}_comovement"],
        )

    renames = dict(config["join"]["output_renames"])
    sector_output = sector.rename(columns=renames).copy()
    comovement_unique = [
        field for field in comovement.columns if field not in sector.columns
    ]
    using_fields = KEY + comovement_unique + ["schema_version"]
    using = comovement[using_fields].rename(
        columns={
            "schema_version": config["join"][
                "comovement_schema_output_field"
            ]
        }
    )
    output = sector_output.merge(
        using,
        on=KEY,
        how="outer",
        validate="one_to_one",
        indicator="_m3_join_status",
        sort=False,
    )

    (
        connector_group,
        group_order,
        within_group_order,
        group_connector_count,
        sector_order,
    ) = sample_maps(config)
    output["core_connector_flag"] = output["connector_iso3"].isin(
        config["sample"]["groups"]["core_connectors"]["connectors"]
    )
    output["asian_comparator_flag"] = output["connector_iso3"].isin(
        config["sample"]["groups"]["asian_comparators"]["connectors"]
    )
    output["other_candidate_flag"] = output["connector_iso3"].isin(
        config["sample"]["groups"]["other_candidates"]["connectors"]
    )
    output["comparison_sample_included"] = True
    output["connector_group_order"] = (
        output["connector_iso3"].map(group_order).astype("int32")
    )
    output["connector_order_within_group"] = (
        output["connector_iso3"].map(within_group_order).astype("int32")
    )
    output["analysis_sector_order"] = (
        output["analysis_sector"].map(sector_order).astype("int32")
    )
    output["comparison_sample_connector_count"] = int(
        config["sample"]["expected_connector_count"]
    )
    output["comparison_sample_sector_count"] = int(
        config["sample"]["expected_sector_count"]
    )
    output["connector_group_connector_count"] = (
        output["connector_group"].map(group_connector_count).astype("int32")
    )
    output["connector_sector_cell_count"] = (
        output.groupby("connector_iso3")["analysis_sector"]
        .transform("size")
        .astype("int32")
    )
    output["m3_sector_source_row_matched"] = output["_m3_join_status"].isin(
        ["both", "left_only"]
    )
    output["m3_comovement_source_row_matched"] = output["_m3_join_status"].isin(
        ["both", "right_only"]
    )
    for field in [
        "outcome_based_selection_applied",
        "top_rank_filter_applied",
        "complete_case_filter_applied",
        "ranking_variables_constructed",
        "production_variables_included",
        "sensitivity_variables_constructed",
    ]:
        output[field] = bool(config["sample"][field])
    output["m3_common_panel_version"] = config["version"]
    output["rules_config_sha256"] = config_hash
    output["schema_version"] = config["schema_version"]

    join_counts = {
        str(key): int(value)
        for key, value in output["_m3_join_status"].value_counts().items()
    }
    output = output.drop(columns="_m3_join_status")
    output = output.sort_values(
        [
            "connector_group_order",
            "connector_order_within_group",
            "analysis_sector_order",
        ],
        kind="mergesort",
    ).reset_index(drop=True)

    string_fields = [
        field
        for field in output.columns
        if field.endswith("_version")
        or field.endswith("_sha256")
        or field
        in {
            "connector_iso3",
            "analysis_sector",
            "connector_group",
            "connector_baci_code",
            "trade_value_unit",
            "treatment_concept",
            "product_comovement_value_share_denominator",
        }
    ]
    for field in string_fields:
        output[field] = output[field].astype("string")
    bool_fields = [
        field
        for field in output.columns
        if field.endswith("_flag")
        or field.endswith("_applied")
        or field.endswith("_included")
        or field.endswith("_constructed")
        or field.endswith("_matched")
        or field.endswith("_defined")
        or field.endswith("_eligible")
        or field
        in {
            "connector_is_proxy",
            "four_year_review_2024_included",
            "china_us_benchmark_repeated_across_connectors",
            "policy_product_counts_repeated_across_connectors",
            "common_fields_not_additive_across_connectors",
        }
    ]
    for field in bool_fields:
        output[field] = output[field].astype(bool)
    int_fields = [
        "connector_group_order",
        "connector_order_within_group",
        "analysis_sector_order",
        "comparison_sample_connector_count",
        "comparison_sample_sector_count",
        "connector_group_connector_count",
        "connector_sector_cell_count",
    ]
    for field in int_fields:
        output[field] = output[field].astype("int32")

    context = {
        "join_status_counts": join_counts,
        "overlap_mismatch_counts": overlap_mismatches,
        "comovement_unique_fields": comovement_unique,
        "connector_group_from_config": connector_group,
    }
    return output, context


def input_contract(
    frame: pd.DataFrame,
    schema: pa.Schema,
    path: Path,
    details: dict[str, Any],
    construction_field: str,
) -> dict[str, Any]:
    observed_schema = schema_signature(schema)
    observed_schema_versions = sorted(
        frame["schema_version"].dropna().astype(str).unique().tolist()
    )
    observed_construction_versions = sorted(
        frame[construction_field].dropna().astype(str).unique().tolist()
    )
    return {
        "path": details["path"],
        "observed_sha256": sha256(path),
        "expected_sha256": details["sha256"],
        "hash_match": sha256(path) == details["sha256"],
        "observed_rows": int(len(frame)),
        "expected_rows": int(details["expected_rows"]),
        "observed_columns": int(len(frame.columns)),
        "expected_columns": int(details["expected_columns"]),
        "observed_arrow_schema_signature_sha256": observed_schema,
        "expected_arrow_schema_signature_sha256": details[
            "arrow_schema_signature_sha256"
        ],
        "duplicate_key_count": int(frame.duplicated(details["natural_key"]).sum()),
        "observed_schema_versions": observed_schema_versions,
        "expected_schema_version": details["expected_schema_version"],
        "observed_construction_versions": observed_construction_versions,
        "expected_construction_version": details[
            "expected_construction_version"
        ],
    }


def content_mismatch_count(
    source: pd.DataFrame,
    output: pd.DataFrame,
    source_to_output: dict[str, str],
) -> dict[str, int]:
    joined = source.merge(
        output,
        on=KEY,
        how="outer",
        validate="one_to_one",
        suffixes=("_source", "_output"),
        indicator=True,
    )
    counts: dict[str, int] = {}
    for source_field, output_field in source_to_output.items():
        if source_field in KEY:
            continue
        left_name = (
            f"{source_field}_source"
            if source_field in output.columns
            else source_field
        )
        right_name = (
            f"{output_field}_output"
            if output_field in source.columns
            else output_field
        )
        counts[source_field] = mismatch_count(
            joined[left_name], joined[right_name]
        )
    counts["_unmatched_rows"] = int(joined["_merge"].ne("both").sum())
    return counts


def validate(
    project_root: Path,
    sector: pd.DataFrame,
    sector_schema: pa.Schema,
    comovement: pd.DataFrame,
    comovement_schema: pa.Schema,
    analysis_sample: dict[str, Any],
    country_groups: dict[str, Any],
    output: pd.DataFrame,
    context: dict[str, Any],
    config: dict[str, Any],
    determinism: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []
    sector_details = config["inputs"]["sector_reorganization"]
    comovement_details = config["inputs"]["product_comovement"]
    input_contracts = {
        "sector_reorganization": input_contract(
            sector,
            sector_schema,
            project_root / sector_details["path"],
            sector_details,
            "m3_reorganization_indicator_version",
        ),
        "product_comovement": input_contract(
            comovement,
            comovement_schema,
            project_root / comovement_details["path"],
            comovement_details,
            "m3_reorganization_indicator_version",
        ),
    }
    for name, contract in input_contracts.items():
        if not (
            contract["hash_match"]
            and contract["observed_rows"] == contract["expected_rows"]
            and contract["observed_columns"] == contract["expected_columns"]
            and contract["observed_arrow_schema_signature_sha256"]
            == contract["expected_arrow_schema_signature_sha256"]
            and contract["duplicate_key_count"] == 0
            and contract["observed_schema_versions"]
            == [contract["expected_schema_version"]]
            and contract["observed_construction_versions"]
            == [contract["expected_construction_version"]]
        ):
            failures.append(f"{name} does not match its frozen input contract")

    config_input_contracts: dict[str, Any] = {}
    for name in ["analysis_sample", "country_groups", "m3_reorganization_rules"]:
        details = config["inputs"][name]
        path = project_root / details["path"]
        observed_hash = sha256(path)
        config_input_contracts[name] = {
            "path": details["path"],
            "observed_sha256": observed_hash,
            "expected_sha256": details["sha256"],
            "hash_match": observed_hash == details["sha256"],
        }
        if observed_hash != details["sha256"]:
            failures.append(f"{name} YAML does not match its frozen hash")

    expected_groups = {
        group: list(details["connectors"])
        for group, details in config["sample"]["groups"].items()
    }
    sample_group_checks = {
        group: list(analysis_sample["countries"][group]) == connectors
        for group, connectors in expected_groups.items()
    }
    country_group_checks = {
        group: list(country_groups[group]) == connectors
        for group, connectors in expected_groups.items()
    }
    sample_version_match = (
        analysis_sample.get("version")
        == config["inputs"]["analysis_sample"]["expected_version"]
    )
    if not (
        all(sample_group_checks.values())
        and all(country_group_checks.values())
        and sample_version_match
    ):
        failures.append("sample groups do not match the frozen sample YAML files")

    overlap_mismatches = context["overlap_mismatch_counts"]
    if any(overlap_mismatches.values()):
        failures.append("same-concept fields disagree across the two M3.4 inputs")
    join_counts = context["join_status_counts"]
    if join_counts.get("both", 0) != int(config["sample"]["expected_rows"]):
        failures.append("one-to-one M3.4 merge did not match all 91 cells")
    if join_counts.get("left_only", 0) or join_counts.get("right_only", 0):
        failures.append("one M3.4 input contains unmatched connector-sector cells")

    output_rows = int(len(output))
    output_columns = int(len(output.columns))
    duplicate_keys = int(output.duplicated(config["output"]["natural_key"]).sum())
    if output_rows != int(config["output"]["expected_rows"]):
        failures.append("common panel row count does not match")
    if output_columns != int(config["output"]["expected_columns"]):
        failures.append("common panel column count does not match")
    if duplicate_keys:
        failures.append("common panel natural key is duplicated")

    connector_universe = output["connector_iso3"].astype(str).unique().tolist()
    expected_connector_universe = [
        connector
        for details in config["sample"]["groups"].values()
        for connector in details["connectors"]
    ]
    sector_universe = output["analysis_sector"].astype(str).unique().tolist()
    expected_sector_universe = list(config["sample"]["sectors"])
    complete_grid = (
        output.groupby("connector_iso3")["analysis_sector"].nunique().eq(
            config["sample"]["expected_sector_count"]
        ).all()
        and output.groupby("analysis_sector")["connector_iso3"].nunique().eq(
            config["sample"]["expected_connector_count"]
        ).all()
    )
    if connector_universe != expected_connector_universe:
        failures.append("connector universe/order does not match frozen sample")
    if sector_universe != expected_sector_universe:
        failures.append("sector universe/order does not match frozen sample")
    if not complete_grid:
        failures.append("connector-sector grid is incomplete")

    group_row_counts = {
        str(key): int(value)
        for key, value in output["connector_group"].value_counts().items()
    }
    connector_counts_by_group = {
        str(key): int(value)
        for key, value in output.groupby("connector_group")[
            "connector_iso3"
        ].nunique().items()
    }
    if group_row_counts != {
        key: int(value)
        for key, value in config["sample"]["expected_rows_by_group"].items()
    }:
        failures.append("group row counts do not match 21/49/21")
    if connector_counts_by_group != {
        key: int(value)
        for key, value in config["sample"][
            "expected_connectors_by_group"
        ].items()
    }:
        failures.append("connector counts by group do not match 3/7/3")

    role_sum = output[
        [
            "core_connector_flag",
            "asian_comparator_flag",
            "other_candidate_flag",
        ]
    ].astype("int8").sum(axis=1)
    role_flag_checks = {
        "exactly_one_role_per_row": bool(role_sum.eq(1).all()),
        "core_matches_group": bool(
            output["core_connector_flag"].eq(
                output["connector_group"].eq("core_connectors")
            ).all()
        ),
        "asian_matches_group": bool(
            output["asian_comparator_flag"].eq(
                output["connector_group"].eq("asian_comparators")
            ).all()
        ),
        "other_matches_group": bool(
            output["other_candidate_flag"].eq(
                output["connector_group"].eq("other_candidates")
            ).all()
        ),
    }
    if not all(role_flag_checks.values()):
        failures.append("sample role flags are inconsistent with connector groups")

    selection_fields = [
        "outcome_based_selection_applied",
        "top_rank_filter_applied",
        "complete_case_filter_applied",
        "ranking_variables_constructed",
        "production_variables_included",
        "sensitivity_variables_constructed",
    ]
    selection_checks = {
        field: {
            "true_count": int(output[field].sum()),
            "all_false": bool((~output[field]).all()),
        }
        for field in selection_fields
    }
    keep_checks = {
        "comparison_sample_included_all_true": bool(
            output["comparison_sample_included"].all()
        ),
        "sector_source_all_matched": bool(
            output["m3_sector_source_row_matched"].all()
        ),
        "comovement_source_all_matched": bool(
            output["m3_comovement_source_row_matched"].all()
        ),
    }
    if not all(check["all_false"] for check in selection_checks.values()):
        failures.append("one or more prohibited M3.5 selection flags are true")
    if not all(keep_checks.values()):
        failures.append("one or more common-panel rows are not retained/matched")

    sector_map = {
        field: config["join"]["output_renames"].get(field, field)
        for field in sector.columns
    }
    sector_preservation = content_mismatch_count(sector, output, sector_map)
    comovement_map = {
        field: (
            config["join"]["comovement_schema_output_field"]
            if field == "schema_version"
            else field
        )
        for field in comovement.columns
        if field not in sector.columns or field == "schema_version" or field in KEY
    }
    comovement_preservation = content_mismatch_count(
        comovement, output, comovement_map
    )
    if any(sector_preservation.values()):
        failures.append("one or more M3.4 sector fields changed during M3.5")
    if any(comovement_preservation.values()):
        failures.append("one or more unique M3.4 comovement fields changed")

    missing_state_counts = {
        "replacement_ratio_defined": int(
            output["replacement_ratio_defined"].sum()
        ),
        "replacement_ratio_missing": int(output["replacement_ratio"].isna().sum()),
        "import_replacement_candidate": int(
            output["import_replacement_candidate_flag"].sum()
        ),
    }
    if (
        missing_state_counts["replacement_ratio_defined"]
        != int(
            config["validation"]["expected_replacement_ratio_defined_count"]
        )
        or missing_state_counts["replacement_ratio_missing"]
        != int(
            config["validation"]["expected_replacement_ratio_missing_count"]
        )
        or missing_state_counts["import_replacement_candidate"]
        != int(
            config["validation"][
                "expected_import_replacement_candidate_count"
            ]
        )
    ):
        failures.append("replacement states were not preserved")

    correlation_fields = [
        "china_product_change_correlation",
        "china_weighted_product_change_correlation",
        "east_asia_product_change_correlation",
        "east_asia_weighted_product_change_correlation",
    ]
    correlation_defined_counts = {
        field: int(output[field].notna().sum()) for field in correlation_fields
    }
    low_n_fields = [
        "china_correlation_low_n_flag",
        "china_weighted_correlation_low_n_flag",
        "east_asia_correlation_low_n_flag",
        "east_asia_weighted_correlation_low_n_flag",
    ]
    low_n_counts = {field: int(output[field].sum()) for field in low_n_fields}
    if any(
        count
        != int(
            config["validation"]["expected_defined_correlation_count_per_field"]
        )
        for count in correlation_defined_counts.values()
    ):
        failures.append("one or more product correlations became missing")
    if any(
        count
        != int(config["validation"]["expected_low_n_flag_count_per_field"])
        for count in low_n_counts.values()
    ):
        failures.append("one or more product correlations changed low-n status")

    twn_checks = {
        "rows": int(output["connector_iso3"].eq("TWN").sum()),
        "proxy_all_true": bool(
            output.loc[
                output["connector_iso3"].eq("TWN"), "connector_is_proxy"
            ].all()
        ),
    }
    if (
        twn_checks["rows"] != int(config["validation"]["expected_twn_rows"])
        or not twn_checks["proxy_all_true"]
    ):
        failures.append("TWN proxy rows are incomplete or mislabeled")

    alias_check = alias_validation(output, config["output"]["stata_aliases"])
    if not alias_check["pass"]:
        failures.append("Stata alias contract is incomplete or invalid")
    metadata_checks = {
        "m3_common_panel_version": sorted(
            output["m3_common_panel_version"].dropna().astype(str).unique()
        )
        == [config["version"]],
        "rules_config_sha256": sorted(
            output["rules_config_sha256"].dropna().astype(str).unique()
        )
        == [determinism["config_sha256"]],
        "schema_version": sorted(
            output["schema_version"].dropna().astype(str).unique()
        )
        == [config["schema_version"]],
    }
    if not all(metadata_checks.values()):
        failures.append("common-panel version metadata is incomplete")

    numeric = output.select_dtypes(include=[np.number])
    infinite_numeric_count = int(np.isinf(numeric.to_numpy()).sum())
    if infinite_numeric_count:
        failures.append("common panel contains infinite numeric values")
    if not determinism["sha256_match"]:
        failures.append("deterministic Parquet SHA256 check failed")
    if not determinism["temporary_output_cleaned"]:
        failures.append("determinism temporary directory was not cleaned")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "input_contracts": input_contracts,
        "config_input_contracts": config_input_contracts,
        "sample_yaml_checks": {
            "analysis_sample_version_match": sample_version_match,
            "analysis_sample_group_checks": sample_group_checks,
            "country_group_checks": country_group_checks,
        },
        "join_checks": {
            "cardinality": config["join"]["cardinality"],
            "join_status_counts": join_counts,
            "overlap_mismatch_counts": overlap_mismatches,
            "unique_comovement_field_count": len(
                context["comovement_unique_fields"]
            ),
        },
        "output_row_count": output_rows,
        "output_column_count": output_columns,
        "output_duplicate_key_count": duplicate_keys,
        "connector_universe_in_output_order": connector_universe,
        "sector_universe_in_output_order": sector_universe,
        "complete_connector_sector_grid": bool(complete_grid),
        "group_row_counts": group_row_counts,
        "connector_counts_by_group": connector_counts_by_group,
        "role_flag_checks": role_flag_checks,
        "selection_checks": selection_checks,
        "retention_and_match_checks": keep_checks,
        "sector_source_preservation_mismatch_counts": sector_preservation,
        "comovement_source_preservation_mismatch_counts": (
            comovement_preservation
        ),
        "replacement_state_counts": missing_state_counts,
        "correlation_defined_counts": correlation_defined_counts,
        "correlation_low_n_counts": low_n_counts,
        "twn_checks": twn_checks,
        "stata_alias_validation": alias_check,
        "metadata_checks": metadata_checks,
        "infinite_numeric_count": infinite_numeric_count,
        "determinism_check": determinism,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    output = validation["output"]
    input_contracts = validation["input_contracts"]
    join = validation["join_checks"]
    aliases = validation["stata_alias_validation"]
    replacement = validation["replacement_state_counts"]
    lines = [
        "# M3.5 Connector-Sector Common Panel Validation",
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
            f"- Output: `{output['path']}`; "
            f"`{validation['output_row_count']} × "
            f"{validation['output_column_count']}`; "
            f"SHA256 `{output['sha256']}`."
        ),
        (
            "- Natural key: `connector_iso3, analysis_sector`; duplicate rows: "
            f"`{validation['output_duplicate_key_count']}`."
        ),
        (
            "- Deterministic rebuild SHA256 match: "
            f"`{'yes' if validation['determinism_check']['sha256_match'] else 'no'}`."
        ),
        "",
        "## Frozen Inputs and Join",
        "",
        (
            "- Sector reorganization input: "
            f"`{input_contracts['sector_reorganization']['observed_rows']} × "
            f"{input_contracts['sector_reorganization']['observed_columns']}`; "
            f"hash/schema/key contract "
            f"`{'pass' if input_contracts['sector_reorganization']['hash_match'] else 'fail'}`."
        ),
        (
            "- Product co-movement input: "
            f"`{input_contracts['product_comovement']['observed_rows']} × "
            f"{input_contracts['product_comovement']['observed_columns']}`; "
            f"hash/schema/key contract "
            f"`{'pass' if input_contracts['product_comovement']['hash_match'] else 'fail'}`."
        ),
        (
            "- One-to-one join status: "
            f"`{join['join_status_counts']}`; exact shared-field mismatches: "
            f"`{sum(join['overlap_mismatch_counts'].values())}`."
        ),
        (
            "- Unique co-movement fields appended without transformation: "
            f"`{join['unique_comovement_field_count']}`."
        ),
        "",
        "## Complete Sample and No-Selection Contract",
        "",
        (
            "- Connector groups: core `3`, Asian comparators `7`, other "
            "candidates `3`; rows by group `21 / 49 / 21`."
        ),
        "- All 13 connectors retain all 7 sectors; total cells: `91`.",
        (
            "- `comparison_sample_included`, sector-source match, and "
            "co-movement-source match are true for every row."
        ),
        (
            "- Outcome-based selection, top-rank filtering, complete-case "
            "filtering, ranking construction, production integration, and "
            "M3.6 sensitivity construction are all false for every row."
        ),
        "",
        "## Preserved States",
        "",
        (
            "- Replacement ratio defined / missing / positive-gain candidate: "
            f"`{replacement['replacement_ratio_defined']} / "
            f"{replacement['replacement_ratio_missing']} / "
            f"{replacement['import_replacement_candidate']}`."
        ),
        (
            "- China/East Asia ordinary and weighted product correlations "
            "remain defined for all 91 cells; all low-n counts remain zero."
        ),
        (
            f"- TWN rows: `{validation['twn_checks']['rows']}`; "
            "proxy flag retained on every TWN row."
        ),
        (
            f"- Stata aliases: `{aliases['alias_count']}` complete and unique; "
            f"maximum length `{aliases['maximum_alias_length']}`."
        ),
        "",
        "## Interpretation Boundary",
        "",
        (
            "This file is a complete comparison panel, not a ranked or "
            "selected winner sample. It combines two M3.4 tables at their "
            "shared connector-sector grain and does not create M3.6 "
            "sensitivity variables, production-side evidence, structural "
            "moments, or causal rerouting estimates."
        ),
    ]
    if validation["failures"]:
        lines.extend(
            ["", "## Failures", ""]
            + [f"- {failure}" for failure in validation["failures"]]
        )
    return "\n".join(lines) + "\n"


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
            f"Refusing to reuse pre-existing determinism directory: {temp_directory}"
        )
    temp_directory.mkdir(parents=True)
    second_output = temp_directory / f"{candidate_output.stem}_second.parquet"
    result: dict[str, Any] = {"config_sha256": config_hash}
    try:
        sector, _, comovement, _, _, _ = read_inputs(project_root, config)
        rebuilt, _ = build_output(sector, comovement, config, config_hash)
        write_parquet(rebuilt, second_output)
        candidate_hash = sha256(candidate_output)
        second_hash = sha256(second_output)
        result.update(
            {
                "candidate_sha256": candidate_hash,
                "second_build_sha256": second_hash,
                "sha256_match": candidate_hash == second_hash,
            }
        )
    finally:
        remove_owned_temp_directory(temp_directory)
    result["temporary_output_cleaned"] = not temp_directory.exists()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build and validate the M3.5 complete connector-sector comparison "
            "panel without ranking or outcome-based sample selection."
        )
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/connector_trade_sector_common_panel_rules.yaml"
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
        project_root, args.output or Path(config["output"]["path"])
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
    candidate_output = candidate_directory / output_path.name

    try:
        (
            sector,
            sector_schema,
            comovement,
            comovement_schema,
            analysis_sample,
            country_groups,
        ) = read_inputs(project_root, config)
        output, context = build_output(
            sector, comovement, config, config_hash
        )
        output_table = write_parquet(output, candidate_output)
        determinism = deterministic_rebuild(
            project_root, config, config_hash, candidate_output
        )
        validation = validate(
            project_root,
            sector,
            sector_schema,
            comovement,
            comovement_schema,
            analysis_sample,
            country_groups,
            output,
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
                "candidate_temp_directory": (
                    candidate_directory.relative_to(project_root).as_posix()
                ),
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
                    "deterministic_sha256_match": determinism["sha256_match"],
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
