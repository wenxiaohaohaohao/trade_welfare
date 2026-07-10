from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


ID_COLUMNS = ["year", "host_country_iso3", "parent_country_iso3", "sector_oecd"]
MINIMUM_ACTIVITY_COLUMNS = [
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
]
ACTIVITY_COLUMNS = MINIMUM_ACTIVITY_COLUMNS + [
    "foreign_affiliate_output_total",
    "gross_output",
    "parent_affiliate_output_share",
    "allocation_method",
    "source_file",
]
MP_SHARE_COLUMNS = MINIMUM_ACTIVITY_COLUMNS + [
    "gross_output",
    "foreign_affiliate_output_total",
    "foreign_affiliate_output_lag",
    "mpe_expansion",
    "mpe_expansion_pct",
    "parent_affiliate_output_share",
    "mp_output_share",
    "foreign_affiliate_share",
    "source_file",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def activity_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("host_country_iso3", pa.string()),
            pa.field("parent_country_iso3", pa.string()),
            pa.field("sector_oecd", pa.string()),
            pa.field("affiliate_output", pa.float64()),
            pa.field("affiliate_value_added", pa.float64()),
            pa.field("affiliate_employment", pa.float64()),
            pa.field("affiliate_exports", pa.float64()),
            pa.field("affiliate_imports", pa.float64()),
            pa.field("ownership_type", pa.string()),
            pa.field("foreign_affiliate_output_total", pa.float64()),
            pa.field("gross_output", pa.float64()),
            pa.field("parent_affiliate_output_share", pa.float64()),
            pa.field("allocation_method", pa.string()),
            pa.field("source_file", pa.string()),
        ]
    )


def mp_share_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("host_country_iso3", pa.string()),
            pa.field("parent_country_iso3", pa.string()),
            pa.field("sector_oecd", pa.string()),
            pa.field("affiliate_output", pa.float64()),
            pa.field("affiliate_value_added", pa.float64()),
            pa.field("affiliate_employment", pa.float64()),
            pa.field("affiliate_exports", pa.float64()),
            pa.field("affiliate_imports", pa.float64()),
            pa.field("ownership_type", pa.string()),
            pa.field("gross_output", pa.float64()),
            pa.field("foreign_affiliate_output_total", pa.float64()),
            pa.field("foreign_affiliate_output_lag", pa.float64()),
            pa.field("mpe_expansion", pa.float64()),
            pa.field("mpe_expansion_pct", pa.float64()),
            pa.field("parent_affiliate_output_share", pa.float64()),
            pa.field("mp_output_share", pa.float64()),
            pa.field("foreign_affiliate_share", pa.float64()),
            pa.field("source_file", pa.string()),
        ]
    )


def table_from_frame(df: pd.DataFrame, schema: pa.Schema) -> pa.Table:
    return pa.Table.from_pandas(df, schema=schema, preserve_index=False)


def remove_if_exists(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"{path} exists. Re-run with --overwrite to replace it.")
        path.unlink()


def locate_inputs(raw_dir: Path) -> dict[str, Path]:
    analytical_dir = raw_dir / "analytical_amne"
    metadata_dir = raw_dir / "metadata"
    inputs = {
        "bilateral_output": analytical_dir / "aamne-bilateral-output.csv",
        "mne_xvem": analytical_dir / "aamne-mne-xvem.csv",
        "readme": metadata_dir / "readme-aamne.xlsx",
    }
    missing = [path for path in inputs.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing OECD AMNE input files: " + ", ".join(str(path) for path in missing))
    return inputs


def read_xvem(path: Path) -> pd.DataFrame:
    expected = {
        "year",
        "cou",
        "own",
        "isic",
        "GO",
        "flag_go",
        "GVA",
        "flag_gva",
        "EXGR",
        "flag_exgr",
        "IMGR",
        "flag_imgr",
    }
    df = pd.read_csv(path)
    missing = sorted(expected - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    df["year"] = df["year"].astype("int16")
    for col in ["cou", "own", "isic"]:
        df[col] = df[col].astype("string")
    for col in ["GO", "GVA", "EXGR", "IMGR"]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("float64")
    duplicate_keys = int(df.duplicated(["year", "cou", "own", "isic"]).sum())
    if duplicate_keys:
        raise ValueError(f"{path} has duplicate year/cou/own/isic rows: {duplicate_keys}")
    return df


def build_xvem_totals(xvem: pd.DataFrame) -> pd.DataFrame:
    gross = (
        xvem.groupby(["year", "cou", "isic"], sort=False)["GO"]
        .sum()
        .rename("gross_output")
        .reset_index()
    )
    foreign = xvem[xvem["own"] == "F"].copy()
    foreign = foreign.rename(
        columns={
            "cou": "host_country_iso3",
            "isic": "sector_oecd",
            "GO": "foreign_affiliate_output_total",
            "GVA": "foreign_affiliate_value_added_total",
            "EXGR": "foreign_affiliate_exports_total",
            "IMGR": "foreign_affiliate_imports_total",
        }
    )
    gross = gross.rename(columns={"cou": "host_country_iso3", "isic": "sector_oecd"})
    totals = foreign[
        [
            "year",
            "host_country_iso3",
            "sector_oecd",
            "foreign_affiliate_output_total",
            "foreign_affiliate_value_added_total",
            "foreign_affiliate_exports_total",
            "foreign_affiliate_imports_total",
        ]
    ].merge(gross, on=["year", "host_country_iso3", "sector_oecd"], how="left", validate="one_to_one")
    if totals["gross_output"].isna().any():
        raise ValueError("Could not merge gross output totals onto foreign-owned XVEM rows.")
    return totals


def read_bilateral_output(path: Path) -> tuple[pd.DataFrame, list[str]]:
    df = pd.read_csv(path)
    required = {"year", "cou", "isic"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing columns: {missing}")
    parent_cols = [col for col in df.columns if col not in {"year", "cou", "isic"}]
    if not parent_cols:
        raise ValueError(f"{path} has no parent-country columns.")
    df["year"] = df["year"].astype("int16")
    df["cou"] = df["cou"].astype("string")
    df["isic"] = df["isic"].astype("string")
    duplicate_keys = int(df.duplicated(["year", "cou", "isic"]).sum())
    if duplicate_keys:
        raise ValueError(f"{path} has duplicate year/cou/isic rows: {duplicate_keys}")
    for col in parent_cols:
        df[col] = pd.to_numeric(df[col], errors="raise").astype("float64")
    return df, parent_cols


def requested_years(
    bilateral: pd.DataFrame,
    totals: pd.DataFrame,
    years_arg: list[int] | None,
) -> list[int]:
    common = sorted(set(int(x) for x in bilateral["year"].unique()) & set(int(x) for x in totals["year"].unique()))
    if years_arg is None:
        return common
    missing = sorted(set(years_arg) - set(common))
    if missing:
        raise ValueError(
            "Requested years are not available in both bilateral output and XVEM activity data: "
            + ", ".join(str(year) for year in missing)
        )
    return sorted(years_arg)


def foreign_links_for_year(
    year: int,
    bilateral: pd.DataFrame,
    parent_cols: list[str],
    totals: pd.DataFrame,
    min_affiliate_output: float,
    include_zero_output: bool,
) -> pd.DataFrame:
    year_rows = bilateral[bilateral["year"] == year].copy()
    long = year_rows.melt(
        id_vars=["year", "cou", "isic"],
        value_vars=parent_cols,
        var_name="parent_country_iso3",
        value_name="affiliate_output",
    )
    long = long.rename(columns={"cou": "host_country_iso3", "isic": "sector_oecd"})
    long["parent_country_iso3"] = long["parent_country_iso3"].astype("string")
    long = long[long["parent_country_iso3"] != long["host_country_iso3"]].copy()
    if include_zero_output:
        long = long[long["affiliate_output"] >= min_affiliate_output].copy()
    else:
        long = long[long["affiliate_output"] > min_affiliate_output].copy()
    long["foreign_parent_output_total"] = long.groupby(
        ["year", "host_country_iso3", "sector_oecd"], sort=False
    )["affiliate_output"].transform("sum")
    long["parent_affiliate_output_share"] = np.divide(
        long["affiliate_output"].to_numpy(dtype="float64"),
        long["foreign_parent_output_total"].to_numpy(dtype="float64"),
        out=np.zeros(len(long), dtype="float64"),
        where=long["foreign_parent_output_total"].to_numpy(dtype="float64") != 0,
    )
    year_totals = totals[totals["year"] == year]
    long = long.merge(
        year_totals,
        on=["year", "host_country_iso3", "sector_oecd"],
        how="left",
        validate="many_to_one",
    )
    required = [
        "foreign_affiliate_output_total",
        "foreign_affiliate_value_added_total",
        "foreign_affiliate_exports_total",
        "foreign_affiliate_imports_total",
        "gross_output",
    ]
    if long[required].isna().any().any():
        raise ValueError(f"Missing XVEM totals after merge for year {year}.")
    long["affiliate_value_added"] = (
        long["foreign_affiliate_value_added_total"] * long["parent_affiliate_output_share"]
    )
    long["affiliate_exports"] = (
        long["foreign_affiliate_exports_total"] * long["parent_affiliate_output_share"]
    )
    long["affiliate_imports"] = (
        long["foreign_affiliate_imports_total"] * long["parent_affiliate_output_share"]
    )
    long["affiliate_employment"] = np.nan
    long["ownership_type"] = "F"
    long["allocation_method"] = "allocated_by_parent_affiliate_output_share"
    long["source_file"] = "aamne-bilateral-output.csv + aamne-mne-xvem.csv"
    return long


def build_lags(totals: pd.DataFrame) -> pd.DataFrame:
    lagged = totals[
        [
            "year",
            "host_country_iso3",
            "sector_oecd",
            "foreign_affiliate_output_total",
        ]
    ].copy()
    lagged = lagged.sort_values(["host_country_iso3", "sector_oecd", "year"])
    group_cols = ["host_country_iso3", "sector_oecd"]
    lagged["foreign_affiliate_output_lag"] = lagged.groupby(group_cols, sort=False)[
        "foreign_affiliate_output_total"
    ].shift(1)
    lagged["mpe_expansion"] = (
        lagged["foreign_affiliate_output_total"] - lagged["foreign_affiliate_output_lag"]
    )
    lagged["mpe_expansion_pct"] = np.divide(
        lagged["mpe_expansion"].to_numpy(dtype="float64"),
        lagged["foreign_affiliate_output_lag"].to_numpy(dtype="float64"),
        out=np.full(len(lagged), np.nan, dtype="float64"),
        where=lagged["foreign_affiliate_output_lag"].to_numpy(dtype="float64") != 0,
    )
    return lagged


def validate_outputs(
    activity_path: Path,
    mp_share_path: Path,
    summary_context: dict[str, Any],
) -> dict[str, Any]:
    activity_file = pq.ParquetFile(activity_path)
    mp_share_file = pq.ParquetFile(mp_share_path)
    if activity_file.schema_arrow.names != ACTIVITY_COLUMNS:
        raise ValueError(f"{activity_path} columns do not match expected schema.")
    if mp_share_file.schema_arrow.names != MP_SHARE_COLUMNS:
        raise ValueError(f"{mp_share_path} columns do not match expected schema.")

    activity = pq.read_table(activity_path).to_pandas()
    mp_share = pq.read_table(mp_share_path).to_pandas()
    missing_activity_cols = sorted(set(MINIMUM_ACTIVITY_COLUMNS) - set(activity.columns))
    missing_share_cols = sorted(set(MINIMUM_ACTIVITY_COLUMNS) - set(mp_share.columns))
    if missing_activity_cols or missing_share_cols:
        raise ValueError(
            f"Minimum fields missing: activity={missing_activity_cols}; mp_share={missing_share_cols}"
        )
    for frame_name, frame in [("activity", activity), ("mp_share", mp_share)]:
        if frame[ID_COLUMNS].isna().any().any():
            raise ValueError(f"{frame_name} output contains missing ID values.")
        duplicate_keys = int(frame.duplicated(ID_COLUMNS).sum())
        if duplicate_keys:
            raise ValueError(f"{frame_name} output contains duplicate ID keys: {duplicate_keys}")
    if not (activity["affiliate_output"] > 0).all():
        raise ValueError("activity output contains non-positive affiliate_output rows.")
    if not (mp_share["affiliate_output"] >= 0).all():
        raise ValueError("mp_share output contains negative affiliate_output rows.")

    share_formula = np.divide(
        mp_share["foreign_affiliate_output_total"].to_numpy(dtype="float64"),
        mp_share["gross_output"].to_numpy(dtype="float64"),
        out=np.full(len(mp_share), np.nan, dtype="float64"),
        where=mp_share["gross_output"].to_numpy(dtype="float64") != 0,
    )
    foreign_share_residual = np.nanmax(np.abs(share_formula - mp_share["foreign_affiliate_share"].to_numpy()))
    parent_share_formula = np.divide(
        mp_share["affiliate_output"].to_numpy(dtype="float64"),
        mp_share["gross_output"].to_numpy(dtype="float64"),
        out=np.full(len(mp_share), np.nan, dtype="float64"),
        where=mp_share["gross_output"].to_numpy(dtype="float64") != 0,
    )
    parent_share_residual = np.nanmax(np.abs(parent_share_formula - mp_share["mp_output_share"].to_numpy()))
    employment_null_rows = int(activity["affiliate_employment"].isna().sum())

    return {
        "activity_rows": int(activity_file.metadata.num_rows),
        "mp_share_rows": int(mp_share_file.metadata.num_rows),
        "years": sorted(int(x) for x in activity["year"].unique()),
        "host_countries": int(activity["host_country_iso3"].nunique()),
        "parent_countries": int(activity["parent_country_iso3"].nunique()),
        "activity_sectors_with_positive_affiliate_output": int(activity["sector_oecd"].nunique()),
        "mp_share_sectors": int(mp_share["sector_oecd"].nunique()),
        "ownership_types": sorted(activity["ownership_type"].dropna().unique().tolist()),
        "minimum_fields_present": True,
        "affiliate_employment_available_in_source": False,
        "affiliate_employment_null_rows": employment_null_rows,
        "affiliate_output_min": float(activity["affiliate_output"].min()),
        "affiliate_output_max": float(activity["affiliate_output"].max()),
        "mp_share_zero_affiliate_output_rows": int((mp_share["affiliate_output"] == 0).sum()),
        "max_abs_foreign_affiliate_share_formula_residual": float(foreign_share_residual),
        "max_abs_parent_mp_output_share_formula_residual": float(parent_share_residual),
        **summary_context,
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    tmp_dir = project_root / "tmp" / "oecd_amne"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(tmp_dir)
    os.environ["TEMP"] = str(tmp_dir)

    data_versions = load_yaml(project_root / "configs" / "data_versions.yaml")
    raw_dir = (project_root / data_versions["oecd_amne"]["raw_dir"]).resolve()
    inputs = locate_inputs(raw_dir)
    output_dir = project_root / "data" / "interim" / "mne"
    output_dir.mkdir(parents=True, exist_ok=True)

    activity_path = output_dir / "oecd_amne_affiliate_activity.parquet"
    mp_share_path = output_dir / "oecd_amne_mp_shares.parquet"
    summary_path = output_dir / "oecd_amne_build_summary.json"
    remove_if_exists(activity_path, args.overwrite)
    remove_if_exists(mp_share_path, args.overwrite)
    remove_if_exists(summary_path, args.overwrite)

    xvem = read_xvem(inputs["mne_xvem"])
    totals = build_xvem_totals(xvem)
    bilateral, parent_cols = read_bilateral_output(inputs["bilateral_output"])
    years = requested_years(bilateral, totals, args.years)
    totals = totals[totals["year"].isin(years)].copy()
    lagged = build_lags(totals)

    activity_writer = pq.ParquetWriter(activity_path, activity_schema(), compression=args.compression)
    mp_writer = pq.ParquetWriter(mp_share_path, mp_share_schema(), compression=args.compression)
    year_summaries: dict[int, dict[str, Any]] = {}
    try:
        for year in years:
            print(f"Processing OECD Analytical AMNE {year}", flush=True)
            links = foreign_links_for_year(
                year,
                bilateral,
                parent_cols,
                totals,
                min_affiliate_output=args.min_affiliate_output,
                include_zero_output=False,
            )
            activity = links[ACTIVITY_COLUMNS].copy()
            activity_writer.write_table(table_from_frame(activity, activity_schema()))

            share_links = foreign_links_for_year(
                year,
                bilateral,
                parent_cols,
                totals,
                min_affiliate_output=0.0,
                include_zero_output=True,
            )
            share = share_links.merge(
                lagged[
                    [
                        "year",
                        "host_country_iso3",
                        "sector_oecd",
                        "foreign_affiliate_output_lag",
                        "mpe_expansion",
                        "mpe_expansion_pct",
                    ]
                ],
                on=["year", "host_country_iso3", "sector_oecd"],
                how="left",
                validate="many_to_one",
            )
            share["mp_output_share"] = np.divide(
                share["affiliate_output"].to_numpy(dtype="float64"),
                share["gross_output"].to_numpy(dtype="float64"),
                out=np.full(len(share), np.nan, dtype="float64"),
                where=share["gross_output"].to_numpy(dtype="float64") != 0,
            )
            share["foreign_affiliate_share"] = np.divide(
                share["foreign_affiliate_output_total"].to_numpy(dtype="float64"),
                share["gross_output"].to_numpy(dtype="float64"),
                out=np.full(len(share), np.nan, dtype="float64"),
                where=share["gross_output"].to_numpy(dtype="float64") != 0,
            )
            mp_writer.write_table(table_from_frame(share[MP_SHARE_COLUMNS], mp_share_schema()))
            year_summaries[year] = {
                "positive_parent_host_sector_links": int(len(links)),
                "all_foreign_parent_host_sector_links_in_mp_share": int(len(share_links)),
                "host_countries": int(links["host_country_iso3"].nunique()),
                "parent_countries": int(links["parent_country_iso3"].nunique()),
                "sectors": int(links["sector_oecd"].nunique()),
                "mp_share_sectors": int(share_links["sector_oecd"].nunique()),
            }
    finally:
        activity_writer.close()
        mp_writer.close()

    consistency = bilateral_xvem_consistency(bilateral, parent_cols, totals, years)
    validation = validate_outputs(activity_path, mp_share_path, consistency)
    summary = {
        "source": "OECD Analytical AMNE, 2026 release",
        "raw_dir": str(raw_dir),
        "inputs": {name: str(path) for name, path in inputs.items()},
        "outputs": {
            "affiliate_activity": str(activity_path),
            "mp_shares": str(mp_share_path),
            "summary": str(summary_path),
        },
        "coverage": {
            "years": years,
            "year_rule": "intersection of aamne-bilateral-output.csv and aamne-mne-xvem.csv",
            "ownership_scope": "foreign-owned affiliate links only; domestic owner diagonal excluded",
            "mp_share_zero_rows": "oecd_amne_mp_shares.parquet retains zero-output foreign parent-host-sector links to preserve the full country-sector universe",
            "unit": "current million USD for value variables; shares are fractions",
        },
        "construction": {
            "affiliate_output": "parent-host-sector-year value from off-diagonal cells of aamne-bilateral-output.csv",
            "affiliate_value_added_exports_imports": "foreign-owned XVEM aggregate allocated to parent countries using parent affiliate output shares within host-sector-year",
            "affiliate_employment": "not provided by the OECD Analytical AMNE files downloaded here; column retained as null",
            "gross_output": "sum of GO across F, D_MNE, and D_OTH in aamne-mne-xvem.csv for each host-sector-year",
            "foreign_affiliate_share": "foreign_affiliate_output_total / gross_output",
            "mpe_expansion": "year-over-year change in total foreign affiliate output by host country and OECD sector",
        },
        "year_summaries": year_summaries,
        "validation": validation,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(validation, indent=2), flush=True)
    return summary


def bilateral_xvem_consistency(
    bilateral: pd.DataFrame,
    parent_cols: list[str],
    totals: pd.DataFrame,
    years: list[int],
) -> dict[str, Any]:
    rows = bilateral[bilateral["year"].isin(years)].copy()
    values = rows[parent_cols].to_numpy(dtype="float64")
    host = rows["cou"].to_numpy(dtype=object)
    parent = np.array(parent_cols, dtype=object)
    domestic_mask = host[:, None] == parent[None, :]
    rows["bilateral_foreign_output_total"] = np.where(domestic_mask, 0.0, values).sum(axis=1)
    check = rows.rename(columns={"cou": "host_country_iso3", "isic": "sector_oecd"})[
        ["year", "host_country_iso3", "sector_oecd", "bilateral_foreign_output_total"]
    ].merge(
        totals[
            [
                "year",
                "host_country_iso3",
                "sector_oecd",
                "foreign_affiliate_output_total",
                "gross_output",
            ]
        ],
        on=["year", "host_country_iso3", "sector_oecd"],
        how="inner",
        validate="one_to_one",
    )
    check["absdiff"] = (
        check["bilateral_foreign_output_total"] - check["foreign_affiliate_output_total"]
    ).abs()
    denom = check[["bilateral_foreign_output_total", "foreign_affiliate_output_total"]].abs().max(axis=1)
    check["reldiff"] = np.divide(
        check["absdiff"].to_numpy(dtype="float64"),
        denom.to_numpy(dtype="float64"),
        out=np.zeros(len(check), dtype="float64"),
        where=denom.to_numpy(dtype="float64") != 0,
    )
    return {
        "xvem_rows_used": int(len(totals)),
        "bilateral_host_sector_rows_used": int(len(rows)),
        "max_abs_bilateral_vs_xvem_foreign_output_diff": float(check["absdiff"].max()),
        "p99_abs_bilateral_vs_xvem_foreign_output_diff": float(check["absdiff"].quantile(0.99)),
        "max_rel_bilateral_vs_xvem_foreign_output_diff": float(check["reldiff"].max()),
        "p99_rel_bilateral_vs_xvem_foreign_output_diff": float(check["reldiff"].quantile(0.99)),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build OECD Analytical AMNE affiliate activity and MP-share parquet outputs.")
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--years", nargs="+", type=int, default=None, help="Optional year subset.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing OECD AMNE outputs.")
    parser.add_argument("--compression", default="snappy", help="Parquet compression codec.")
    parser.add_argument(
        "--min-affiliate-output",
        type=float,
        default=0.0,
        help="Drop parent-host-sector links at or below this affiliate output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
