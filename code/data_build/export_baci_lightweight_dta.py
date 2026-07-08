from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow.parquet as pq
import pyreadstat


TRADE_DIR = Path("data/interim/trade")

CONNECTOR_COLUMNS = [
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

FLAG_COLUMNS = [
    "has_china_to_connector",
    "has_connector_to_usa",
    "has_both_legs",
]

COLUMN_LABELS = {
    "year": "Calendar year",
    "connector_iso3": "Connector ISO3 in project config",
    "connector_baci_iso3": "Connector ISO3 used in BACI",
    "flow_leg": "Rerouting flow leg",
    "exporter_iso3": "Exporter ISO3",
    "importer_iso3": "Importer ISO3",
    "hs6": "HS 6-digit product code",
    "trade_value_usd": "Trade value, USD",
    "quantity": "Quantity, metric tons",
    "unit": "Quantity unit",
    "source_file": "Source BACI CSV filename",
    "has_china_to_connector": "Flag: China to connector flow exists",
    "has_connector_to_usa": "Flag: connector to USA flow exists",
    "has_both_legs": "Flag: both rerouting legs exist",
    "china_to_connector_value_usd": "China to connector trade value, USD",
    "connector_to_usa_value_usd": "Connector to USA trade value, USD",
}


def validate_columns(path: Path, expected: list[str]) -> None:
    actual = pq.ParquetFile(path).schema_arrow.names
    if actual != expected:
        raise ValueError(f"{path} columns differ from expected schema: {actual}")


def normalize_for_stata(df: pd.DataFrame, flag_table: bool) -> pd.DataFrame:
    out = df.copy()
    for column in out.columns:
        if pd.api.types.is_string_dtype(out[column]):
            out[column] = out[column].astype("object")
    if flag_table:
        for column in FLAG_COLUMNS:
            out[column] = out[column].astype("int8")
    out["year"] = out["year"].astype("int16")
    return out


def write_dta(df: pd.DataFrame, path: Path, file_label: str, flag_table: bool) -> None:
    value_labels = None
    if flag_table:
        value_labels = {column: {0: "no", 1: "yes"} for column in FLAG_COLUMNS}
    pyreadstat.write_dta(
        df,
        path,
        file_label=file_label,
        column_labels={column: COLUMN_LABELS[column] for column in df.columns},
        variable_value_labels=value_labels,
        version=15,
    )


def dta_metadata(path: Path) -> dict[str, Any]:
    _df, meta = pyreadstat.read_dta(path, metadataonly=True)
    return {
        "rows": meta.number_rows,
        "columns": meta.column_names,
        "file_label": meta.file_label,
    }


def export(project_root: Path, overwrite: bool) -> dict[str, Any]:
    trade_dir = project_root / TRADE_DIR
    connector_parquet = trade_dir / "baci_connector_flows.parquet"
    flags_parquet = trade_dir / "baci_country_product_year_flags.parquet"
    connector_dta = trade_dir / "baci_connector_flows.dta"
    flags_dta = trade_dir / "baci_country_product_year_flags.dta"
    summary_path = trade_dir / "baci_lightweight_dta_export_summary.json"

    for path in [connector_parquet, flags_parquet]:
        if not path.exists():
            raise FileNotFoundError(f"Missing input parquet: {path}")
    existing = [path for path in [connector_dta, flags_dta, summary_path] if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "Output files already exist. Re-run with --overwrite to replace: "
            + ", ".join(str(path) for path in existing)
        )
    for path in existing:
        path.unlink()

    validate_columns(connector_parquet, CONNECTOR_COLUMNS)
    validate_columns(flags_parquet, FLAGS_COLUMNS)

    connector_df = normalize_for_stata(pd.read_parquet(connector_parquet), flag_table=False)
    flags_df = normalize_for_stata(pd.read_parquet(flags_parquet), flag_table=True)

    bad_flags = (
        flags_df["has_both_legs"]
        != ((flags_df["has_china_to_connector"] == 1) & (flags_df["has_connector_to_usa"] == 1))
    ).sum()
    if int(bad_flags) != 0:
        raise ValueError(f"Flag logic failed before DTA export: {bad_flags} inconsistent rows.")

    write_dta(
        connector_df,
        connector_dta,
        "BACI 202601 connector flow subset",
        flag_table=False,
    )
    write_dta(
        flags_df,
        flags_dta,
        "BACI 202601 connector product-year flags",
        flag_table=True,
    )

    summary = {
        "inputs": {
            "connector_flows_parquet": str(connector_parquet),
            "country_product_year_flags_parquet": str(flags_parquet),
        },
        "outputs": {
            "connector_flows_dta": str(connector_dta),
            "country_product_year_flags_dta": str(flags_dta),
        },
        "source_rows": {
            "connector_flows": len(connector_df),
            "country_product_year_flags": len(flags_df),
        },
        "dta_metadata": {
            "connector_flows": dta_metadata(connector_dta),
            "country_product_year_flags": dta_metadata(flags_dta),
        },
        "flag_logic_bad_rows": int(bad_flags),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export lightweight BACI Batch 1 parquet files to Stata DTA.")
    parser.add_argument("--project-root", default=".", help="Project root containing data/interim/trade.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing DTA exports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = export(Path(args.project_root).resolve(), overwrite=args.overwrite)
    print(json.dumps(summary["dta_metadata"], indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
