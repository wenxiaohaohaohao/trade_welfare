from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


PANEL_COLUMNS = [
    "year",
    "exporter_iso3",
    "importer_iso3",
    "hs6",
    "trade_value_usd",
    "quantity",
    "unit",
    "source_file",
]

CONNECTOR_FLOW_COLUMNS = [
    "year",
    "connector_iso3",
    "connector_baci_iso3",
    "flow_leg",
    "exporter_iso3",
    "importer_iso3",
    "hs6",
    "trade_value_usd",
    "quantity",
    "unit",
    "source_file",
]

FLAGS_COLUMNS = [
    "year",
    "connector_iso3",
    "connector_baci_iso3",
    "hs6",
    "has_china_to_connector",
    "has_connector_to_usa",
    "has_both_legs",
    "china_to_connector_value_usd",
    "connector_to_usa_value_usd",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def configured_years(time_windows: dict[str, Any], baci_config: dict[str, Any]) -> list[int]:
    required = baci_config.get("batch1_usage", {}).get("required_years", {})
    start = required.get("start", time_windows["pre_period"]["start"])
    end = required.get("end", time_windows["post_period"]["end"])
    return list(range(int(start), int(end) + 1))


def connector_iso3s(country_groups: dict[str, Any]) -> list[str]:
    return unique_preserve_order(
        list(country_groups.get("core_connectors", []))
        + list(country_groups.get("asian_comparators", []))
        + list(country_groups.get("other_candidates", []))
    )


def configured_country_tokens(country_groups: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for group in country_groups.get("source_bloc", {}).values():
        tokens.extend(group)
    for group in country_groups.get("destination_bloc", {}).values():
        tokens.extend(group)
    tokens.extend(connector_iso3s(country_groups))
    return unique_preserve_order([token for token in tokens if token != "EU27"])


def load_country_mapping(raw_dir: Path, metadata_name: str) -> tuple[dict[int, str], set[str], pd.DataFrame]:
    country_path = raw_dir / metadata_name
    countries = pd.read_csv(country_path)
    required_columns = {"country_code", "country_iso3", "country_name"}
    missing = required_columns - set(countries.columns)
    if missing:
        raise ValueError(f"{country_path} is missing columns: {sorted(missing)}")
    if countries["country_iso3"].isna().any():
        bad = countries.loc[countries["country_iso3"].isna(), "country_code"].tolist()
        raise ValueError(f"{country_path} has missing country_iso3 values for country_code={bad}")
    code_to_iso = {
        int(row.country_code): str(row.country_iso3)
        for row in countries.itertuples(index=False)
    }
    return code_to_iso, set(code_to_iso.values()), countries


def load_overrides(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = load_yaml(path)
    overrides = data.get("country_code_overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError(f"{path} country_code_overrides must be a mapping.")
    return overrides


def build_connector_map(
    connectors: list[str],
    direct_iso3s: set[str],
    overrides: dict[str, dict[str, Any]],
    code_to_iso: dict[int, str],
) -> dict[str, str]:
    connector_map: dict[str, str] = {}
    errors: list[str] = []
    for connector in connectors:
        if connector in direct_iso3s:
            connector_map[connector] = connector
            continue
        override = overrides.get(connector)
        if not override:
            errors.append(f"{connector}: no direct BACI ISO3 and no override")
            continue
        baci_iso3 = str(override.get("baci_iso3", ""))
        baci_country_code = int(override.get("baci_country_code", -1))
        mapped_iso3 = code_to_iso.get(baci_country_code)
        if not baci_iso3 or mapped_iso3 != baci_iso3:
            errors.append(
                f"{connector}: override code {baci_country_code} maps to {mapped_iso3}, not {baci_iso3}"
            )
            continue
        connector_map[connector] = baci_iso3
    if errors:
        raise ValueError("Connector country mapping failed: " + "; ".join(errors))
    return connector_map


def validate_configured_countries(
    country_tokens: list[str],
    direct_iso3s: set[str],
    overrides: dict[str, dict[str, Any]],
) -> None:
    missing = [
        token
        for token in country_tokens
        if token not in direct_iso3s and token not in overrides
    ]
    if missing:
        raise ValueError(f"Configured countries not found in BACI metadata or overrides: {missing}")


def raw_csv_path(raw_dir: Path, pattern: str, year: int) -> Path:
    return raw_dir / pattern.format(year=year)


def ensure_inputs(raw_dir: Path, pattern: str, years: list[int], baci_config: dict[str, Any]) -> None:
    required_files = [
        raw_dir / baci_config["country_metadata"],
        raw_dir / baci_config["product_metadata"],
        raw_dir / baci_config["readme"],
    ]
    required_files.extend(raw_csv_path(raw_dir, pattern, year) for year in years)
    missing = [path for path in required_files if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing BACI input files: " + ", ".join(str(path) for path in missing))


def panel_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("exporter_iso3", pa.string()),
            pa.field("importer_iso3", pa.string()),
            pa.field("hs6", pa.string()),
            pa.field("trade_value_usd", pa.float64()),
            pa.field("quantity", pa.float64()),
            pa.field("unit", pa.string()),
            pa.field("source_file", pa.string()),
        ]
    )


def connector_flow_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("connector_iso3", pa.string()),
            pa.field("connector_baci_iso3", pa.string()),
            pa.field("flow_leg", pa.string()),
            pa.field("exporter_iso3", pa.string()),
            pa.field("importer_iso3", pa.string()),
            pa.field("hs6", pa.string()),
            pa.field("trade_value_usd", pa.float64()),
            pa.field("quantity", pa.float64()),
            pa.field("unit", pa.string()),
            pa.field("source_file", pa.string()),
        ]
    )


def flags_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("connector_iso3", pa.string()),
            pa.field("connector_baci_iso3", pa.string()),
            pa.field("hs6", pa.string()),
            pa.field("has_china_to_connector", pa.bool_()),
            pa.field("has_connector_to_usa", pa.bool_()),
            pa.field("has_both_legs", pa.bool_()),
            pa.field("china_to_connector_value_usd", pa.float64()),
            pa.field("connector_to_usa_value_usd", pa.float64()),
        ]
    )


def dataframe_to_table(df: pd.DataFrame, schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pandas(df, schema=schema, preserve_index=False)


def remove_existing_outputs(paths: list[Path], overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Output files already exist. Re-run with --overwrite to replace: "
            + ", ".join(str(path) for path in existing)
        )
    for path in existing:
        path.unlink()


def add_group_sums(target: dict[tuple[int, str, str, str], float], df: pd.DataFrame) -> None:
    if df.empty:
        return
    grouped = (
        df.groupby(["year", "connector_iso3", "connector_baci_iso3", "hs6"], dropna=False)[
            "trade_value_usd"
        ]
        .sum()
        .reset_index()
    )
    for row in grouped.itertuples(index=False):
        key = (int(row.year), str(row.connector_iso3), str(row.connector_baci_iso3), str(row.hs6))
        target[key] += float(row.trade_value_usd)


def prepare_raw_chunk(
    chunk: pd.DataFrame,
    expected_year: int,
    source_file: str,
    code_to_iso: dict[int, str],
) -> pd.DataFrame:
    if set(chunk.columns) != {"t", "i", "j", "k", "v", "q"}:
        raise ValueError(f"{source_file} has unexpected columns: {list(chunk.columns)}")
    years = set(int(x) for x in chunk["t"].dropna().unique())
    if years != {expected_year}:
        raise ValueError(f"{source_file} contains unexpected years: {sorted(years)}")
    if chunk["v"].isna().any():
        raise ValueError(f"{source_file} contains missing trade values in column v.")
    hs6_lengths = set(chunk["k"].dropna().str.len().unique())
    if hs6_lengths != {6}:
        raise ValueError(f"{source_file} contains non-six-digit HS codes: {sorted(hs6_lengths)}")

    exporter_iso3 = chunk["i"].map(code_to_iso)
    importer_iso3 = chunk["j"].map(code_to_iso)
    if exporter_iso3.isna().any() or importer_iso3.isna().any():
        bad_exporters = sorted(set(chunk.loc[exporter_iso3.isna(), "i"].dropna().astype(int).tolist()))
        bad_importers = sorted(set(chunk.loc[importer_iso3.isna(), "j"].dropna().astype(int).tolist()))
        raise ValueError(
            f"{source_file} has unmapped country codes: exporters={bad_exporters}, importers={bad_importers}"
        )

    return pd.DataFrame(
        {
            "year": chunk["t"].astype("int16"),
            "exporter_iso3": exporter_iso3.astype("string"),
            "importer_iso3": importer_iso3.astype("string"),
            "hs6": chunk["k"].astype("string"),
            "trade_value_usd": chunk["v"].astype("float64") * 1000.0,
            "quantity": chunk["q"].astype("float64"),
            "unit": "metric_tons",
            "source_file": source_file,
        },
        columns=PANEL_COLUMNS,
    )


def connector_chunk(
    panel_chunk: pd.DataFrame,
    connector_map: dict[str, str],
) -> pd.DataFrame:
    baci_to_connector = {baci_iso3: connector for connector, baci_iso3 in connector_map.items()}
    connector_baci_iso3s = set(baci_to_connector)

    source_mask = (panel_chunk["exporter_iso3"] == "CHN") & (
        panel_chunk["importer_iso3"].isin(connector_baci_iso3s)
    )
    destination_mask = (panel_chunk["exporter_iso3"].isin(connector_baci_iso3s)) & (
        panel_chunk["importer_iso3"] == "USA"
    )

    frames: list[pd.DataFrame] = []
    if source_mask.any():
        source_df = panel_chunk.loc[source_mask, PANEL_COLUMNS].copy()
        source_df.insert(1, "connector_baci_iso3", source_df["importer_iso3"].astype("string"))
        source_df.insert(1, "connector_iso3", source_df["connector_baci_iso3"].map(baci_to_connector).astype("string"))
        source_df.insert(3, "flow_leg", "source_to_connector")
        frames.append(source_df[CONNECTOR_FLOW_COLUMNS])
    if destination_mask.any():
        destination_df = panel_chunk.loc[destination_mask, PANEL_COLUMNS].copy()
        destination_df.insert(1, "connector_baci_iso3", destination_df["exporter_iso3"].astype("string"))
        destination_df.insert(1, "connector_iso3", destination_df["connector_baci_iso3"].map(baci_to_connector).astype("string"))
        destination_df.insert(3, "flow_leg", "connector_to_destination")
        frames.append(destination_df[CONNECTOR_FLOW_COLUMNS])

    if not frames:
        return pd.DataFrame(columns=CONNECTOR_FLOW_COLUMNS)
    return pd.concat(frames, ignore_index=True)


def flags_dataframe(
    china_to_connector: dict[tuple[int, str, str, str], float],
    connector_to_usa: dict[tuple[int, str, str, str], float],
) -> pd.DataFrame:
    keys = sorted(set(china_to_connector) | set(connector_to_usa))
    rows = []
    for year, connector_iso3, connector_baci_iso3, hs6 in keys:
        china_value = float(china_to_connector.get((year, connector_iso3, connector_baci_iso3, hs6), 0.0))
        usa_value = float(connector_to_usa.get((year, connector_iso3, connector_baci_iso3, hs6), 0.0))
        has_china = china_value > 0
        has_usa = usa_value > 0
        rows.append(
            {
                "year": year,
                "connector_iso3": connector_iso3,
                "connector_baci_iso3": connector_baci_iso3,
                "hs6": hs6,
                "has_china_to_connector": has_china,
                "has_connector_to_usa": has_usa,
                "has_both_legs": has_china and has_usa,
                "china_to_connector_value_usd": china_value,
                "connector_to_usa_value_usd": usa_value,
            }
        )
    return pd.DataFrame(rows, columns=FLAGS_COLUMNS)


def expected_schema_names(path: Path) -> list[str]:
    return pq.ParquetFile(path).schema_arrow.names


def validate_outputs(
    panel_path: Path,
    connector_path: Path,
    flags_path: Path,
    years: list[int],
) -> dict[str, Any]:
    for path in [panel_path, connector_path, flags_path]:
        if not path.exists():
            raise FileNotFoundError(f"Expected output was not created: {path}")

    if expected_schema_names(panel_path) != PANEL_COLUMNS:
        raise ValueError(f"{panel_path} columns do not match expected interface.")
    if expected_schema_names(connector_path) != CONNECTOR_FLOW_COLUMNS:
        raise ValueError(f"{connector_path} columns do not match expected interface.")
    if expected_schema_names(flags_path) != FLAGS_COLUMNS:
        raise ValueError(f"{flags_path} columns do not match expected interface.")

    connector = pq.read_table(
        connector_path,
        columns=["year", "connector_iso3", "flow_leg", "trade_value_usd"],
    ).to_pandas()
    flow_legs = sorted(connector["flow_leg"].dropna().unique().tolist())
    if flow_legs != ["connector_to_destination", "source_to_connector"]:
        raise ValueError(f"{connector_path} has unexpected flow_leg values: {flow_legs}")

    flags = pq.read_table(flags_path).to_pandas()
    if not (
        flags["has_both_legs"]
        == (flags["has_china_to_connector"] & flags["has_connector_to_usa"])
    ).all():
        raise ValueError(f"{flags_path} has inconsistent has_both_legs flags.")

    sample_years = [year for year in [2014, 2018, 2020, 2024] if year in years]
    sample_connectors = ["VNM", "MEX", "CAN"]
    sample = (
        connector[
            connector["year"].isin(sample_years)
            & connector["connector_iso3"].isin(sample_connectors)
        ]
        .groupby(["year", "connector_iso3", "flow_leg"], dropna=False)["trade_value_usd"]
        .sum()
        .reset_index()
    )
    missing_positive: list[str] = []
    for year in sample_years:
        for connector_iso3 in sample_connectors:
            for flow_leg in ["source_to_connector", "connector_to_destination"]:
                value = sample.loc[
                    (sample["year"] == year)
                    & (sample["connector_iso3"] == connector_iso3)
                    & (sample["flow_leg"] == flow_leg),
                    "trade_value_usd",
                ].sum()
                if value <= 0:
                    missing_positive.append(f"{year} {connector_iso3} {flow_leg}")
    if missing_positive:
        raise ValueError("Expected positive sampled flows missing: " + ", ".join(missing_positive))

    panel_meta = pq.ParquetFile(panel_path).metadata
    connector_meta = pq.ParquetFile(connector_path).metadata
    flags_meta = pq.ParquetFile(flags_path).metadata
    return {
        "panel_rows": panel_meta.num_rows,
        "connector_flow_rows": connector_meta.num_rows,
        "flag_rows": flags_meta.num_rows,
        "flow_legs": flow_legs,
        "sample_flow_checks": "positive for 2014, 2018, 2020, 2024 core connector flows",
    }


def build_outputs(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    config_dir = project_root / "configs"
    data_versions = load_yaml(config_dir / "data_versions.yaml")
    country_groups = load_yaml(config_dir / "country_groups.yaml")
    time_windows = load_yaml(config_dir / "time_windows.yaml")
    overrides = load_overrides(config_dir / "country_code_overrides.yaml")

    baci_config = data_versions["baci"]
    raw_dir = (project_root / baci_config["raw_dir"]).resolve()
    output_dir = (project_root / baci_config["batch1_usage"]["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    years = configured_years(time_windows, baci_config)
    pattern = baci_config["csv_pattern"]
    ensure_inputs(raw_dir, pattern, years, baci_config)

    code_to_iso, direct_iso3s, _countries = load_country_mapping(raw_dir, baci_config["country_metadata"])
    validate_configured_countries(configured_country_tokens(country_groups), direct_iso3s, overrides)
    connectors = connector_iso3s(country_groups)
    connector_map = build_connector_map(connectors, direct_iso3s, overrides, code_to_iso)

    panel_path = output_dir / "baci_hs6_panel.parquet"
    connector_path = output_dir / "baci_connector_flows.parquet"
    flags_path = output_dir / "baci_country_product_year_flags.parquet"
    summary_path = output_dir / "baci_batch1_build_summary.json"
    remove_existing_outputs([panel_path, connector_path, flags_path, summary_path], args.overwrite)

    panel_writer = pq.ParquetWriter(panel_path, panel_schema(), compression=args.compression)
    connector_writer = pq.ParquetWriter(connector_path, connector_flow_schema(), compression=args.compression)
    china_to_connector: dict[tuple[int, str, str, str], float] = defaultdict(float)
    connector_to_usa: dict[tuple[int, str, str, str], float] = defaultdict(float)
    raw_row_counts: dict[int, int] = {}
    q_missing: dict[int, int] = {}
    connector_rows_by_year: dict[int, int] = {}

    try:
        for year in years:
            csv_path = raw_csv_path(raw_dir, pattern, year)
            source_file = csv_path.name
            raw_row_counts[year] = 0
            q_missing[year] = 0
            connector_rows_by_year[year] = 0
            print(f"Processing {source_file}", flush=True)
            for chunk in pd.read_csv(
                csv_path,
                usecols=["t", "i", "j", "k", "v", "q"],
                dtype={
                    "t": "int16",
                    "i": "int16",
                    "j": "int16",
                    "k": "string",
                    "v": "float64",
                    "q": "float64",
                },
                chunksize=args.chunk_size,
            ):
                raw_row_counts[year] += len(chunk)
                q_missing[year] += int(chunk["q"].isna().sum())
                panel_chunk = prepare_raw_chunk(chunk, year, source_file, code_to_iso)
                panel_writer.write_table(dataframe_to_table(panel_chunk, panel_schema()))

                conn_chunk = connector_chunk(panel_chunk, connector_map)
                if not conn_chunk.empty:
                    connector_rows_by_year[year] += len(conn_chunk)
                    connector_writer.write_table(
                        dataframe_to_table(conn_chunk, connector_flow_schema())
                    )
                    add_group_sums(
                        china_to_connector,
                        conn_chunk.loc[conn_chunk["flow_leg"] == "source_to_connector"],
                    )
                    add_group_sums(
                        connector_to_usa,
                        conn_chunk.loc[conn_chunk["flow_leg"] == "connector_to_destination"],
                    )
    finally:
        panel_writer.close()
        connector_writer.close()

    flags = flags_dataframe(china_to_connector, connector_to_usa)
    pq.write_table(
        dataframe_to_table(flags, flags_schema()),
        flags_path,
        compression=args.compression,
    )

    validation = validate_outputs(panel_path, connector_path, flags_path, years)
    summary = {
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "years": years,
        "connector_map": connector_map,
        "raw_row_counts": raw_row_counts,
        "quantity_missing_rows": q_missing,
        "connector_rows_by_year": connector_rows_by_year,
        "outputs": {
            "panel": str(panel_path),
            "connector_flows": str(connector_path),
            "country_product_year_flags": str(flags_path),
        },
        "validation": validation,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build BACI 202601 Batch 1 parquet outputs.")
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--chunk-size", type=int, default=1_000_000, help="CSV rows per chunk.")
    parser.add_argument("--compression", default="snappy", help="Parquet compression codec.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing Batch 1 parquet outputs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    summary = build_outputs(args)
    print(json.dumps(summary["validation"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
