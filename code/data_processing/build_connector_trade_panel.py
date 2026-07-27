from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


def add_grouped(parts: list[pd.DataFrame], frame: pd.DataFrame, keys: list[str], value_name: str) -> None:
    if frame.empty:
        return
    grouped = (
        frame.groupby(keys, as_index=False, observed=True)
        .agg(**{value_name: ("trade_value_usd", "sum"), f"{value_name}_row_count": ("trade_value_usd", "size")})
    )
    parts.append(grouped)


def finalize_parts(parts: list[pd.DataFrame], keys: list[str], value_name: str) -> pd.DataFrame:
    if not parts:
        return pd.DataFrame(columns=[*keys, value_name, f"{value_name}_row_count"])
    return (
        pd.concat(parts, ignore_index=True)
        .groupby(keys, as_index=False, observed=True)
        .agg(
            **{
                value_name: (value_name, "sum"),
                f"{value_name}_row_count": (f"{value_name}_row_count", "sum"),
            }
        )
    )


def country_interfaces(
    country: pd.DataFrame, sample: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str], dict[str, bool], list[str], list[str], list[str]]:
    baci = country[country["source_name"] == "baci"].copy()
    source_to_iso3 = dict(
        zip(baci["source_country_id"].astype(str), baci["country_iso3"].astype(str))
    )
    canonical_to_source: dict[str, str] = {}
    proxy_by_iso3: dict[str, bool] = {}
    for row in baci.itertuples(index=False):
        if pd.isna(row.country_iso3):
            continue
        iso3 = str(row.country_iso3)
        if iso3 in canonical_to_source:
            raise ValueError(f"BACI has multiple source country codes for canonical {iso3}")
        canonical_to_source[iso3] = str(row.source_country_id)
        proxy_by_iso3[iso3] = bool(row.is_proxy)

    connector_groups = ["core_connectors", "asian_comparators", "other_candidates"]
    connectors = [iso3 for group in connector_groups for iso3 in sample["countries"][group]]
    source_core = list(sample["countries"]["source_core"])
    source_extended = list(sample["countries"]["source_extended_east_asia"])
    required = set(connectors + source_core + source_extended + sample["countries"]["destination_core"])
    missing = sorted(required - set(canonical_to_source))
    if missing:
        raise ValueError(f"BACI country crosswalk lacks required canonical countries: {missing}")
    return (
        source_to_iso3,
        canonical_to_source,
        proxy_by_iso3,
        connectors,
        source_core,
        source_extended,
    )


def scan_baci_legs(
    path: Path,
    source_to_iso3: dict[str, str],
    canonical_to_source: dict[str, str],
    connectors: list[str],
    source_core: list[str],
    source_extended: list[str],
    destination: str,
) -> dict[str, pd.DataFrame]:
    connector_codes = {canonical_to_source[iso3] for iso3 in connectors}
    core_codes = {canonical_to_source[iso3] for iso3 in source_core}
    extended_codes = {canonical_to_source[iso3] for iso3 in source_extended}
    destination_code = canonical_to_source[destination]

    china_usa_parts: list[pd.DataFrame] = []
    china_connector_parts: list[pd.DataFrame] = []
    east_connector_parts: list[pd.DataFrame] = []
    connector_usa_parts: list[pd.DataFrame] = []

    parquet = pq.ParquetFile(path)
    for batch in parquet.iter_batches(
        columns=["year", "exporter_iso3", "importer_iso3", "hs6", "trade_value_usd"],
        batch_size=1_000_000,
    ):
        frame = batch.to_pandas()
        frame["hs6"] = frame["hs6"].astype("string").str.zfill(6)

        china_usa = frame[
            frame["exporter_iso3"].isin(core_codes)
            & (frame["importer_iso3"] == destination_code)
        ].copy()
        add_grouped(
            china_usa_parts,
            china_usa,
            ["year", "hs6"],
            "china_to_usa_value_usd",
        )

        china_connector = frame[
            frame["exporter_iso3"].isin(core_codes)
            & frame["importer_iso3"].isin(connector_codes)
        ].copy()
        if not china_connector.empty:
            china_connector["connector_iso3"] = china_connector["importer_iso3"].map(source_to_iso3)
        add_grouped(
            china_connector_parts,
            china_connector,
            ["connector_iso3", "year", "hs6"],
            "china_to_connector_value_usd",
        )

        east_connector = frame[
            frame["exporter_iso3"].isin(extended_codes)
            & frame["importer_iso3"].isin(connector_codes)
        ].copy()
        if not east_connector.empty:
            east_connector["source_iso3"] = east_connector["exporter_iso3"].map(source_to_iso3)
            east_connector["connector_iso3"] = east_connector["importer_iso3"].map(source_to_iso3)
            east_connector = east_connector[
                east_connector["source_iso3"] != east_connector["connector_iso3"]
            ]
        add_grouped(
            east_connector_parts,
            east_connector,
            ["connector_iso3", "year", "hs6"],
            "east_asia_to_connector_value_usd",
        )

        connector_usa = frame[
            frame["exporter_iso3"].isin(connector_codes)
            & (frame["importer_iso3"] == destination_code)
        ].copy()
        if not connector_usa.empty:
            connector_usa["connector_iso3"] = connector_usa["exporter_iso3"].map(source_to_iso3)
        add_grouped(
            connector_usa_parts,
            connector_usa,
            ["connector_iso3", "year", "hs6"],
            "connector_to_usa_value_usd",
        )

    return {
        "china_to_usa": finalize_parts(
            china_usa_parts, ["year", "hs6"], "china_to_usa_value_usd"
        ),
        "china_to_connector": finalize_parts(
            china_connector_parts,
            ["connector_iso3", "year", "hs6"],
            "china_to_connector_value_usd",
        ),
        "east_asia_to_connector": finalize_parts(
            east_connector_parts,
            ["connector_iso3", "year", "hs6"],
            "east_asia_to_connector_value_usd",
        ),
        "connector_to_usa": finalize_parts(
            connector_usa_parts,
            ["connector_iso3", "year", "hs6"],
            "connector_to_usa_value_usd",
        ),
    }


def connector_group_map(sample: dict[str, Any]) -> dict[str, str]:
    return {
        iso3: group
        for group in ["core_connectors", "asian_comparators", "other_candidates"]
        for iso3 in sample["countries"][group]
    }


def build_output(
    legs: dict[str, pd.DataFrame],
    product: pd.DataFrame,
    sample: dict[str, Any],
    canonical_to_source: dict[str, str],
    proxy_by_iso3: dict[str, bool],
    connectors: list[str],
    config: dict[str, Any],
) -> pd.DataFrame:
    years = list(
        range(
            int(sample["time"]["annual_trade_panel"]["start"]),
            int(sample["time"]["annual_trade_panel"]["end"]) + 1,
        )
    )
    product_fields = [
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "is_analysis_sector_eligible",
        "mapping_version",
    ]
    base = (
        pd.DataFrame({"connector_iso3": connectors})
        .assign(_join_key=1)
        .merge(pd.DataFrame({"year": years, "_join_key": 1}), on="_join_key")
        .merge(
            product[product_fields]
            .rename(columns={"mapping_version": "product_mapping_version"})
            .assign(_join_key=1),
            on="_join_key",
        )
        .drop(columns="_join_key")
    )
    output = base.copy()
    for name in ["china_to_connector", "east_asia_to_connector", "connector_to_usa"]:
        leg = legs[name].rename(columns={"hs6": "analysis_hs6"})
        output = output.merge(
            leg, on=["connector_iso3", "year", "analysis_hs6"], how="left", validate="one_to_one"
        )
    benchmark = legs["china_to_usa"].rename(columns={"hs6": "analysis_hs6"})
    output = output.merge(
        benchmark, on=["year", "analysis_hs6"], how="left", validate="many_to_one"
    )

    value_fields = [
        "china_to_usa_value_usd",
        "china_to_connector_value_usd",
        "east_asia_to_connector_value_usd",
        "connector_to_usa_value_usd",
    ]
    row_fields = [f"{field}_row_count" for field in value_fields]
    for column in value_fields + row_fields:
        output[column] = output[column].fillna(0)
    output["connector_group"] = output["connector_iso3"].map(connector_group_map(sample))
    output["connector_baci_code"] = output["connector_iso3"].map(canonical_to_source)
    output["connector_is_proxy"] = output["connector_iso3"].map(proxy_by_iso3).fillna(False)
    output["east_asia_self_trade_excluded"] = output["connector_iso3"].isin(
        sample["countries"]["source_extended_east_asia"]
    )
    output["baci_absence_treated_as_zero"] = True
    output["china_to_usa_common_benchmark"] = True
    output["trade_value_unit"] = "current_USD"
    output["quantity_included"] = False
    output["trade_panel_version"] = config["version"]

    string_columns = [
        "connector_iso3",
        "connector_group",
        "connector_baci_code",
        "analysis_hs6",
        "product_description",
        "analysis_sector",
        "sector_status",
        "first_round_exclusion",
        "product_mapping_version",
        "trade_value_unit",
        "trade_panel_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["year"] = output["year"].astype("int16")
    for column in row_fields:
        output[column] = output[column].astype("int32")
    for column in [
        "is_analysis_sector_eligible",
        "connector_is_proxy",
        "east_asia_self_trade_excluded",
        "baci_absence_treated_as_zero",
        "china_to_usa_common_benchmark",
        "quantity_included",
    ]:
        output[column] = output[column].astype("bool")
    return output.sort_values(["connector_iso3", "analysis_hs6", "year"]).reset_index(drop=True)


def validate(
    project_root: Path,
    config: dict[str, Any],
    sample: dict[str, Any],
    legs: dict[str, pd.DataFrame],
    product: pd.DataFrame,
    output: pd.DataFrame,
    connectors: list[str],
) -> dict[str, Any]:
    failures: list[str] = []
    hash_checks = {
        name: sha256(project_root / details["path"]) == details["sha256"]
        for name, details in config["inputs"].items()
    }
    if not all(hash_checks.values()):
        failures.append("one or more configured M2.2 input hashes do not match")
    keys = ["connector_iso3", "analysis_hs6", "year"]
    duplicate_keys = int(output.duplicated(keys).sum())
    if duplicate_keys:
        failures.append(f"connector trade panel has {duplicate_keys} duplicate natural keys")
    years = set(
        range(
            int(sample["time"]["annual_trade_panel"]["start"]),
            int(sample["time"]["annual_trade_panel"]["end"]) + 1,
        )
    )
    expected_rows = len(connectors) * len(product) * len(years)
    full_grid_ok = bool(
        len(output) == expected_rows
        and set(output["connector_iso3"]) == set(connectors)
        and set(output["analysis_hs6"]) == set(product["analysis_hs6"])
        and set(output["year"]) == years
    )
    if not full_grid_ok:
        failures.append("connector trade output is not the complete connector-product-year grid")
    value_fields = [
        "china_to_usa_value_usd",
        "china_to_connector_value_usd",
        "east_asia_to_connector_value_usd",
        "connector_to_usa_value_usd",
    ]
    negative_counts = {column: int((output[column] < 0).sum()) for column in value_fields}
    if any(negative_counts.values()):
        failures.append("one or more BACI trade value fields are negative")

    leg_to_output = {
        "china_to_connector": "china_to_connector_value_usd",
        "east_asia_to_connector": "east_asia_to_connector_value_usd",
        "connector_to_usa": "connector_to_usa_value_usd",
    }
    reconciliation: dict[str, dict[str, float]] = {}
    tolerance = float(config["validation"]["tolerance_usd"])
    for leg_name, field in leg_to_output.items():
        source_total = float(legs[leg_name][field].sum())
        output_total = float(output[field].sum())
        gap = output_total - source_total
        reconciliation[leg_name] = {
            "source_total": source_total,
            "output_total": output_total,
            "gap": gap,
        }
        if abs(gap) > tolerance:
            failures.append(f"{leg_name} fails total-value reconciliation")

    benchmark_source_total = float(legs["china_to_usa"]["china_to_usa_value_usd"].sum())
    benchmark_by_connector = (
        output.groupby("connector_iso3")["china_to_usa_value_usd"].sum().to_dict()
    )
    benchmark_gaps = {
        connector: float(total - benchmark_source_total)
        for connector, total in benchmark_by_connector.items()
    }
    benchmark_repetition_ok = all(abs(gap) <= tolerance for gap in benchmark_gaps.values())
    if not benchmark_repetition_ok:
        failures.append("repeated China-to-USA benchmark differs across connector panels")
    east_ge_china = bool(
        (output["east_asia_to_connector_value_usd"] + tolerance >= output["china_to_connector_value_usd"]).all()
    )
    if not east_ge_china:
        failures.append("East Asia-to-connector value is below China-to-connector for one or more keys")
    tw_proxy_ok = bool(
        output.loc[output["connector_iso3"] == "TWN", "connector_is_proxy"].all()
        and (output.loc[output["connector_iso3"] == "TWN", "connector_baci_code"] == "S19").all()
    )
    if not tw_proxy_ok:
        failures.append("Taiwan connector does not retain the BACI S19 proxy flag")
    self_trade_flags_ok = bool(
        output.loc[output["connector_iso3"].isin(["KOR", "TWN"]), "east_asia_self_trade_excluded"].all()
        and (~output.loc[~output["connector_iso3"].isin(["KOR", "TWN"]), "east_asia_self_trade_excluded"]).all()
    )
    if not self_trade_flags_ok:
        failures.append("East Asia self-trade exclusion flags are inconsistent")
    product_mapping_missing = int(output["product_mapping_version"].isna().sum())
    if product_mapping_missing:
        failures.append("one or more output rows lack product mapping provenance")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "input_hash_checks": hash_checks,
        "connector_count": len(connectors),
        "connectors": connectors,
        "product_count": len(product),
        "year_count": len(years),
        "output_row_count": len(output),
        "expected_output_row_count": expected_rows,
        "duplicate_natural_key_count": duplicate_keys,
        "full_grid_check_pass": full_grid_ok,
        "negative_value_counts": negative_counts,
        "leg_reconciliation": reconciliation,
        "china_to_usa_source_total": benchmark_source_total,
        "china_to_usa_repeated_total_by_connector": benchmark_by_connector,
        "china_to_usa_repetition_gaps": benchmark_gaps,
        "china_to_usa_repetition_check_pass": benchmark_repetition_ok,
        "east_asia_value_at_least_china_value_check_pass": east_ge_china,
        "twn_s19_proxy_check_pass": tw_proxy_ok,
        "east_asia_self_trade_flags_check_pass": self_trade_flags_ok,
        "product_mapping_provenance_missing_count": product_mapping_missing,
        "leg_nonzero_key_counts": {
            name: len(frame) for name, frame in legs.items()
        },
        "quantity_omitted_due_source_missingness": True,
        "common_benchmark_must_not_be_summed_across_connectors": True,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Connector Trade Panel Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Output rows: `{validation['output_row_count']}`",
        "",
        "## Required checks",
        "",
        f"- Configured input SHA256 checks: `{'yes' if all(validation['input_hash_checks'].values()) else 'no'}`",
        f"- Unique connector-product-year key: `{'yes' if validation['duplicate_natural_key_count'] == 0 else 'no'}`",
        f"- Complete connector-product-year grid: `{'yes' if validation['full_grid_check_pass'] else 'no'}`",
        f"- Nonnegative BACI trade values: `{'yes' if not any(validation['negative_value_counts'].values()) else 'no'}`",
        f"- China-to-USA benchmark identical for every connector: `{'yes' if validation['china_to_usa_repetition_check_pass'] else 'no'}`",
        f"- Taiwan retains BACI S19 proxy flag: `{'yes' if validation['twn_s19_proxy_check_pass'] else 'no'}`",
        f"- East Asia self-trade exclusion flags pass: `{'yes' if validation['east_asia_self_trade_flags_check_pass'] else 'no'}`",
        "",
        "## Trade-leg reconciliation",
        "",
        "| Leg | Source total USD | Output total USD | Gap USD |",
        "|---|---:|---:|---:|",
    ]
    for name, record in validation["leg_reconciliation"].items():
        lines.append(
            f"| `{name}` | {record['source_total']:.2f} | {record['output_total']:.2f} | {record['gap']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The output is a completed grid for all configured connector candidates, BACI/CEPII products, and 2014-2024 years. A missing BACI bilateral product row is recorded as zero value with zero source-row count. The East Asia source leg excludes canonical self-trade for KOR and TWN connector rows. China-to-USA is a common product-year benchmark repeated only to support within-connector comparisons; it must never be summed across connectors. BACI quantity is omitted because its source missingness is not interpretable as zero.",
            "",
        ]
    )
    if validation["failures"]:
        lines.extend(["## Failures", ""] + [f"- {item}" for item in validation["failures"]] + [""])
    return "\n".join(lines)


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the M2.2 BACI connector trade panel.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/harmonized/connector_trade_legs_hs6_year.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/connector_trade_panel_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/connector_trade_panel_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    output_path = args.output if args.output.is_absolute() else project_root / args.output
    validation_json = args.validation_json if args.validation_json.is_absolute() else project_root / args.validation_json
    validation_md = args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    for path in [output_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/connector_trade_rules.yaml")
    sample = load_yaml(project_root / config["analysis_sample_config"])
    country = pq.read_table(project_root / config["inputs"]["country_crosswalk"]["path"]).to_pandas()
    product = pq.read_table(project_root / config["inputs"]["product_crosswalk"]["path"]).to_pandas()
    (
        source_to_iso3,
        canonical_to_source,
        proxy_by_iso3,
        connectors,
        source_core,
        source_extended,
    ) = country_interfaces(country, sample)
    destination = sample["countries"]["destination_core"][0]
    legs = scan_baci_legs(
        project_root / config["inputs"]["baci_hs6_panel"]["path"],
        source_to_iso3,
        canonical_to_source,
        connectors,
        source_core,
        source_extended,
        destination,
    )
    output = build_output(
        legs,
        product,
        sample,
        canonical_to_source,
        proxy_by_iso3,
        connectors,
        config,
    )
    validation = validate(
        project_root, config, sample, legs, product, output, connectors
    )
    table = write_parquet(output, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "trade_panel_version": config["version"],
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in table.schema
            ],
        }
    )
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    validation_json.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validation_md.write_text(markdown_report(validation), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "output_rows": validation["output_row_count"],
                "connector_count": validation["connector_count"],
                "leg_nonzero_keys": validation["leg_nonzero_key_counts"],
                "validation_json": str(validation_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
