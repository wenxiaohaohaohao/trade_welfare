from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


FD_CATEGORIES = ["HFCE", "NPISH", "GGFC", "GFCF", "INVNT", "DPABR"]
TARGET_YEARS = [2017, 2018, 2022]
OUTPUT_VA_FD_COLUMNS = [
    "year",
    "country_iso3",
    "sector_oecd",
    "gross_output",
    "gross_output_sales",
    "value_added",
    "final_demand",
    "intermediate_inputs",
    "taxes_less_subsidies",
    "exports",
    "imports",
    "intermediate_sales",
    "domestic_absorption",
    "source_file",
]
IO_SHARE_COLUMNS = [
    "year",
    "source_country_iso3",
    "source_sector_oecd",
    "destination_country_iso3",
    "destination_sector_oecd",
    "intermediate_input",
    "destination_gross_output",
    "input_share",
    "source_file",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def output_va_fd_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("country_iso3", pa.string()),
            pa.field("sector_oecd", pa.string()),
            pa.field("gross_output", pa.float64()),
            pa.field("gross_output_sales", pa.float64()),
            pa.field("value_added", pa.float64()),
            pa.field("final_demand", pa.float64()),
            pa.field("intermediate_inputs", pa.float64()),
            pa.field("taxes_less_subsidies", pa.float64()),
            pa.field("exports", pa.float64()),
            pa.field("imports", pa.float64()),
            pa.field("intermediate_sales", pa.float64()),
            pa.field("domestic_absorption", pa.float64()),
            pa.field("source_file", pa.string()),
        ]
    )


def io_share_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("source_country_iso3", pa.string()),
            pa.field("source_sector_oecd", pa.string()),
            pa.field("destination_country_iso3", pa.string()),
            pa.field("destination_sector_oecd", pa.string()),
            pa.field("intermediate_input", pa.float64()),
            pa.field("destination_gross_output", pa.float64()),
            pa.field("input_share", pa.float64()),
            pa.field("source_file", pa.string()),
        ]
    )


def table_from_frame(df: pd.DataFrame, schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pandas(df, schema=schema, preserve_index=False)


def read_items(readme_path: Path, sheet_name: str) -> pd.DataFrame:
    workbook = openpyxl.load_workbook(readme_path, data_only=True, read_only=True)
    worksheet = workbook[sheet_name]
    rows: list[dict[str, Any]] = []
    for excel_row in worksheet.iter_rows(min_row=4, values_only=True):
        item_id = excel_row[1]
        code = excel_row[2]
        country = excel_row[3]
        item = excel_row[4]
        if item_id is None or code is None:
            continue
        rows.append(
            {
                "id": int(item_id),
                "code": str(code),
                "country_iso3": None if country is None else str(country),
                "item": None if item is None else str(item),
            }
        )
    return pd.DataFrame(rows)


def read_sector_metadata(readme_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    row_items = read_items(readme_path, "RowItems")
    col_items = read_items(readme_path, "ColItems")

    sectors = row_items[row_items["country_iso3"].notna()].copy()
    sectors = sectors.rename(columns={"code": "country_sector", "item": "sector_oecd"})
    sectors = sectors[["country_sector", "country_iso3", "sector_oecd"]]

    industry_columns = col_items[
        col_items["country_iso3"].notna()
        & (~col_items["item"].isin(FD_CATEGORIES))
        & (col_items["code"] != "OUT")
    ].copy()
    industry_columns = industry_columns.rename(columns={"code": "country_sector", "item": "sector_oecd"})
    industry_columns = industry_columns[["country_sector", "country_iso3", "sector_oecd"]]

    if sectors["country_sector"].tolist() != industry_columns["country_sector"].tolist():
        raise ValueError("ReadMe row and industry-column sector order differs.")
    return sectors.reset_index(drop=True), col_items


def final_demand_columns(col_items: pd.DataFrame) -> pd.DataFrame:
    out = col_items[col_items["item"].isin(FD_CATEGORIES)].copy()
    return out.rename(columns={"code": "fd_column", "item": "fd_category"})[
        ["fd_column", "country_iso3", "fd_category"]
    ].reset_index(drop=True)


def locate_regular_readme(raw_dir: Path) -> Path:
    candidates = [
        raw_dir / "2025_regular" / "ReadMe_ICIO_small.xlsx",
        raw_dir / "readme" / "ReadMe_ICIO_small.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Missing ReadMe_ICIO_small.xlsx under data/raw/oecd_icio.")


def locate_regular_member(raw_dir: Path, year: int) -> tuple[Path, str]:
    regular_dir = raw_dir / "2025_regular"
    member_name = f"{year}_SML.csv"
    for zip_path in sorted(regular_dir.glob("*_SML.zip")):
        with zipfile.ZipFile(zip_path) as archive:
            if member_name in archive.namelist():
                return zip_path, member_name
    raise FileNotFoundError(f"Could not find {member_name} in {regular_dir}.")


def read_year_matrix(zip_path: Path, member_name: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member_name) as handle:
            df = pd.read_csv(handle, index_col=0, na_values=["na", "NA", ""])
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)
    return df


def remove_if_exists(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"{path} exists. Re-run with --overwrite to replace it.")
        path.unlink()


def validate_matrix(
    matrix: pd.DataFrame,
    sectors: pd.DataFrame,
    fd_cols: pd.DataFrame,
    source_file: str,
) -> None:
    sector_codes = sectors["country_sector"].tolist()
    missing_rows = sorted(set(sector_codes + ["VA", "OUT"]) - set(matrix.index))
    missing_cols = sorted(set(sector_codes + fd_cols["fd_column"].tolist() + ["OUT"]) - set(matrix.columns))
    if missing_rows:
        raise ValueError(f"{source_file} is missing rows: {missing_rows[:20]}")
    if missing_cols:
        raise ValueError(f"{source_file} is missing columns: {missing_cols[:20]}")


def country_column_map(meta: pd.DataFrame, column_name: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for country, group in meta.groupby("country_iso3", sort=False):
        out[str(country)] = group[column_name].astype(str).tolist()
    return out


def build_trade_flows(
    year: int,
    matrix: pd.DataFrame,
    sectors: pd.DataFrame,
    fd_cols: pd.DataFrame,
) -> pd.DataFrame:
    sector_codes = sectors["country_sector"].tolist()
    industry_by_country = country_column_map(sectors, "country_sector")
    fd_by_country = country_column_map(fd_cols, "fd_column")
    blocks: list[pd.DataFrame] = []
    for destination_country in sectors["country_iso3"].drop_duplicates().tolist():
        industry_cols = industry_by_country[destination_country]
        demand_cols = fd_by_country[destination_country]
        values = matrix.loc[sector_codes, industry_cols].sum(axis=1)
        values = values + matrix.loc[sector_codes, demand_cols].sum(axis=1)
        block = sectors.copy()
        block["year"] = np.int16(year)
        block["destination_country_iso3"] = destination_country
        block["trade_value"] = values.to_numpy(dtype="float64")
        blocks.append(
            block.rename(
                columns={
                    "country_iso3": "origin_country_iso3",
                    "sector_oecd": "sector_oecd",
                }
            )[
                [
                    "year",
                    "origin_country_iso3",
                    "destination_country_iso3",
                    "sector_oecd",
                    "trade_value",
                ]
            ]
        )
    trade = pd.concat(blocks, ignore_index=True)
    denominator = trade.groupby(["destination_country_iso3", "sector_oecd"], sort=False)[
        "trade_value"
    ].transform("sum")
    trade["trade_share"] = np.divide(
        trade["trade_value"],
        denominator,
        out=np.zeros(len(trade), dtype="float64"),
        where=denominator.to_numpy() != 0,
    )
    return trade


def build_output_va_fd(
    year: int,
    matrix: pd.DataFrame,
    sectors: pd.DataFrame,
    fd_cols: pd.DataFrame,
    trade: pd.DataFrame,
    source_file: str,
) -> pd.DataFrame:
    sector_codes = sectors["country_sector"].tolist()
    industry_cols = sector_codes
    fd_columns = fd_cols["fd_column"].tolist()

    out = sectors.rename(columns={"country_sector": "_country_sector"}).copy()
    out["year"] = np.int16(year)
    out["gross_output"] = matrix.loc["OUT", industry_cols].to_numpy(dtype="float64")
    out["gross_output_sales"] = matrix.loc[sector_codes, "OUT"].to_numpy(dtype="float64")
    out["value_added"] = matrix.loc["VA", industry_cols].to_numpy(dtype="float64")
    out["final_demand"] = matrix.loc[sector_codes, fd_columns].sum(axis=1).to_numpy(dtype="float64")
    out["intermediate_inputs"] = matrix.loc[sector_codes, industry_cols].sum(axis=0).to_numpy(dtype="float64")
    out["taxes_less_subsidies"] = matrix.loc["TLS", industry_cols].to_numpy(dtype="float64")
    out["intermediate_sales"] = matrix.loc[sector_codes, industry_cols].sum(axis=1).to_numpy(dtype="float64")

    exports = (
        trade[trade["origin_country_iso3"] != trade["destination_country_iso3"]]
        .groupby(["origin_country_iso3", "sector_oecd"], sort=False)["trade_value"]
        .sum()
        .rename("exports")
    )
    imports = (
        trade[trade["origin_country_iso3"] != trade["destination_country_iso3"]]
        .groupby(["destination_country_iso3", "sector_oecd"], sort=False)["trade_value"]
        .sum()
        .rename("imports")
    )
    domestic = (
        trade[trade["origin_country_iso3"] == trade["destination_country_iso3"]]
        .groupby(["origin_country_iso3", "sector_oecd"], sort=False)["trade_value"]
        .sum()
        .rename("domestic_absorption")
    )

    out = out.join(exports, on=["country_iso3", "sector_oecd"])
    out = out.join(imports, on=["country_iso3", "sector_oecd"])
    out = out.join(domestic, on=["country_iso3", "sector_oecd"])
    out[["exports", "imports", "domestic_absorption"]] = out[
        ["exports", "imports", "domestic_absorption"]
    ].fillna(0.0)
    out["source_file"] = source_file
    return out[OUTPUT_VA_FD_COLUMNS]


def write_io_share_chunks(
    writer: pq.ParquetWriter,
    year_writer: pq.ParquetWriter | None,
    year: int,
    matrix: pd.DataFrame,
    sectors: pd.DataFrame,
    source_file: str,
    chunk_rows: int,
    min_value: float,
) -> int:
    sector_codes = sectors["country_sector"].tolist()
    dest_meta = sectors.rename(
        columns={
            "country_iso3": "destination_country_iso3",
            "sector_oecd": "destination_sector_oecd",
        }
    )
    dest_country = dest_meta["destination_country_iso3"].to_numpy(dtype=object)
    dest_sector = dest_meta["destination_sector_oecd"].to_numpy(dtype=object)
    dest_output = matrix.loc["OUT", sector_codes].to_numpy(dtype="float64")
    row_count = 0

    for start in range(0, len(sector_codes), chunk_rows):
        stop = min(start + chunk_rows, len(sector_codes))
        row_labels = sector_codes[start:stop]
        block = matrix.loc[row_labels, sector_codes].to_numpy(dtype="float64", copy=False)
        source_meta = sectors.iloc[start:stop]
        row_idx, col_idx = np.nonzero(block > min_value)
        if len(row_idx) == 0:
            continue
        values = block[row_idx, col_idx]
        destination_gross_output = dest_output[col_idx]
        shares = np.divide(
            values,
            destination_gross_output,
            out=np.zeros(len(values), dtype="float64"),
            where=destination_gross_output != 0,
        )
        frame = pd.DataFrame(
            {
                "year": np.full(len(values), year, dtype="int16"),
                "source_country_iso3": source_meta.iloc[row_idx]["country_iso3"].to_numpy(dtype=object),
                "source_sector_oecd": source_meta.iloc[row_idx]["sector_oecd"].to_numpy(dtype=object),
                "destination_country_iso3": dest_country[col_idx],
                "destination_sector_oecd": dest_sector[col_idx],
                "intermediate_input": values,
                "destination_gross_output": destination_gross_output,
                "input_share": shares,
                "source_file": source_file,
            },
            columns=IO_SHARE_COLUMNS,
        )
        table = table_from_frame(frame, io_share_schema())
        writer.write_table(table)
        if year_writer is not None:
            year_writer.write_table(table)
        row_count += len(frame)
    return row_count


def write_model_inputs(
    out_dir: Path,
    output_va_fd: pd.DataFrame,
    io_share_year_path: Path,
    trade: pd.DataFrame,
    matrix: pd.DataFrame,
    sectors: pd.DataFrame,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_va_fd[["year", "country_iso3", "sector_oecd", "gross_output"]].to_csv(
        out_dir / "X_baseline.csv", index=False
    )
    output_va_fd[["year", "country_iso3", "sector_oecd", "value_added"]].to_csv(
        out_dir / "va_baseline.csv", index=False
    )
    trade.to_csv(out_dir / "trshare_baseline.csv", index=False)

    sector_codes = sectors["country_sector"].tolist()
    io_matrix = matrix.loc[sector_codes, sector_codes].copy()
    destination_output = matrix.loc["OUT", sector_codes].astype("float64")
    io_share_matrix = io_matrix.divide(destination_output, axis=1).fillna(0.0)
    io_share_matrix = pd.concat(
        [
            pd.Series(sector_codes, name="source_country_sector"),
            io_share_matrix.reset_index(drop=True),
        ],
        axis=1,
    )
    io_share_matrix.to_csv(out_dir / "IO_baseline.csv", index=False)

    manifest = {
        "files": {
            "X_baseline": str(out_dir / "X_baseline.csv"),
            "va_baseline": str(out_dir / "va_baseline.csv"),
            "IO_baseline": str(out_dir / "IO_baseline.csv"),
            "trshare_baseline": str(out_dir / "trshare_baseline.csv"),
        },
        "schemas": {
            "X_baseline.csv": ["year", "country_iso3", "sector_oecd", "gross_output"],
            "va_baseline.csv": ["year", "country_iso3", "sector_oecd", "value_added"],
            "IO_baseline.csv": ["source_country_sector"] + sector_codes,
            "trshare_baseline.csv": [
                "year",
                "origin_country_iso3",
                "destination_country_iso3",
                "sector_oecd",
                "trade_value",
                "trade_share",
            ],
        },
        "io_share_long_parquet": str(io_share_year_path),
        "units": "current million USD for levels; shares are fractions",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def validate_outputs(
    output_path: Path,
    io_path: Path,
    years: list[int],
    expected_sector_rows: int,
) -> dict[str, Any]:
    output_table = pq.read_table(output_path)
    output_df = output_table.to_pandas()
    if output_table.schema.names != OUTPUT_VA_FD_COLUMNS:
        raise ValueError(f"{output_path} columns do not match expected schema.")
    expected_rows = expected_sector_rows * len(years)
    if len(output_df) != expected_rows:
        raise ValueError(f"{output_path} has {len(output_df)} rows, expected {expected_rows}.")
    if sorted(output_df["year"].unique().tolist()) != years:
        raise ValueError(f"{output_path} does not contain the requested years.")
    required = [
        "gross_output",
        "value_added",
        "final_demand",
        "intermediate_inputs",
        "taxes_less_subsidies",
        "exports",
        "imports",
    ]
    if output_df[required].isna().any().any():
        raise ValueError(f"{output_path} contains missing values in required numeric fields.")

    io_file = pq.ParquetFile(io_path)
    if io_file.schema_arrow.names != IO_SHARE_COLUMNS:
        raise ValueError(f"{io_path} columns do not match expected schema.")

    sales_residual = output_df["gross_output_sales"] - (
        output_df["intermediate_sales"] + output_df["final_demand"]
    )
    production_residual = output_df["gross_output"] - (
        output_df["intermediate_inputs"]
        + output_df["taxes_less_subsidies"]
        + output_df["value_added"]
    )
    return {
        "output_va_fd_rows": int(len(output_df)),
        "io_share_rows": int(io_file.metadata.num_rows),
        "years": years,
        "countries": int(output_df["country_iso3"].nunique()),
        "sectors": int(output_df["sector_oecd"].nunique()),
        "max_abs_sales_identity_residual": float(sales_residual.abs().max()),
        "max_abs_production_identity_residual": float(production_residual.abs().max()),
        "required_columns_present": required,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    tmp_dir = project_root / "tmp" / "oecd_icio"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(tmp_dir)
    os.environ["TEMP"] = str(tmp_dir)

    data_versions = load_yaml(project_root / "configs" / "data_versions.yaml")
    raw_dir = (project_root / data_versions["oecd_icio"]["raw_dir"]).resolve()
    readme_path = locate_regular_readme(raw_dir)
    sectors, col_items = read_sector_metadata(readme_path)
    fd_cols = final_demand_columns(col_items)
    years = args.years

    output_dir = project_root / "data" / "interim" / "production"
    output_dir.mkdir(parents=True, exist_ok=True)
    model_root = project_root / "data" / "model_inputs"
    output_path = output_dir / "oecd_icio_output_va_fd.parquet"
    io_path = output_dir / "oecd_icio_io_shares.parquet"
    summary_path = output_dir / "oecd_icio_build_summary.json"
    remove_if_exists(output_path, args.overwrite)
    remove_if_exists(io_path, args.overwrite)
    remove_if_exists(summary_path, args.overwrite)

    output_writer = pq.ParquetWriter(output_path, output_va_fd_schema(), compression=args.compression)
    io_writer = pq.ParquetWriter(io_path, io_share_schema(), compression=args.compression)
    year_summaries: dict[int, Any] = {}
    try:
        for year in years:
            zip_path, member_name = locate_regular_member(raw_dir, year)
            source_file = f"{zip_path.relative_to(project_root).as_posix()}::{member_name}"
            print(f"Processing OECD ICIO {year} from {source_file}", flush=True)
            matrix = read_year_matrix(zip_path, member_name)
            validate_matrix(matrix, sectors, fd_cols, source_file)

            trade = build_trade_flows(year, matrix, sectors, fd_cols)
            output_va_fd = build_output_va_fd(year, matrix, sectors, fd_cols, trade, source_file)
            output_writer.write_table(table_from_frame(output_va_fd, output_va_fd_schema()))
            year_io_path = output_dir / f"oecd_icio_io_shares_{year}.parquet"
            remove_if_exists(year_io_path, args.overwrite)
            year_io_writer = pq.ParquetWriter(
                year_io_path, io_share_schema(), compression=args.compression
            )
            try:
                io_rows_written = write_io_share_chunks(
                    io_writer,
                    year_io_writer,
                    year,
                    matrix,
                    sectors,
                    source_file,
                    chunk_rows=args.io_chunk_rows,
                    min_value=args.min_io_value,
                )
            finally:
                year_io_writer.close()
            model_dir = model_root / f"icio_baseline_{year}"
            manifest = write_model_inputs(model_dir, output_va_fd, year_io_path, trade, matrix, sectors)
            year_summaries[year] = {
                "source_file": source_file,
                "output_rows": int(len(output_va_fd)),
                "trade_rows": int(len(trade)),
                "io_rows_written": int(io_rows_written),
                "model_inputs": manifest["files"],
            }
    finally:
        output_writer.close()
        io_writer.close()

    validation = validate_outputs(output_path, io_path, years, len(sectors))
    summary = {
        "source": "OECD ICIO 2025 edition, regular ICIO, current million USD",
        "readme": str(readme_path),
        "raw_dir": str(raw_dir),
        "years": years,
        "outputs": {
            "output_va_fd": str(output_path),
            "io_shares": str(io_path),
            "model_inputs_root": str(model_root),
        },
        "year_summaries": year_summaries,
        "validation": validation,
        "notes": {
            "regular_vs_extended": "Regular ICIO is used for baseline country-sector objects. Extended ICIO files are archived for later China/Mexico split work.",
            "exports": "For each origin country-sector, exports equal intermediate plus final demand absorbed by all foreign destination countries.",
            "imports": "For each destination country-sector product, imports equal absorption from all foreign origin countries in the same OECD sector.",
            "gross_output": "gross_output uses the production-side OUT row. gross_output_sales preserves the sales-side OUT column for row-balance checks.",
            "intermediate_inputs": "For each country-sector, intermediate_inputs equal the column sum of global intermediate inputs used by that producing sector. OECD TLS is reported separately as taxes_less_subsidies.",
            "IO_baseline.csv": "Wide matrix of intermediate-input shares: rows are source country-sector, columns are destination country-sector, values are divided by destination gross output.",
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(validation, indent=2), flush=True)
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OECD ICIO baseline parquet and MATLAB-ready inputs.")
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--years", nargs="+", type=int, default=TARGET_YEARS)
    parser.add_argument("--overwrite", action="store_true", help="Replace existing OECD ICIO outputs.")
    parser.add_argument("--compression", default="snappy", help="Parquet compression codec.")
    parser.add_argument("--io-chunk-rows", type=int, default=100, help="Source rows per IO-share parquet chunk.")
    parser.add_argument("--min-io-value", type=float, default=0.0, help="Drop IO values at or below this threshold.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
