from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.client import IncompleteRead, RemoteDisconnected
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


API_BASE = "https://api.census.gov/data/timeseries/intltrade/imports/hs"
API_FIELDS = [
    "YEAR",
    "MONTH",
    "CTY_CODE",
    "CTY_NAME",
    "I_COMMODITY",
    "I_COMMODITY_SDESC",
    "GEN_VAL_MO",
    "GEN_QY1_MO",
    "UNIT_QY1",
    "CON_VAL_MO",
    "CAL_DUT_MO",
    "DUT_VAL_MO",
]
OUTPUT_COLUMNS = [
    "year",
    "month",
    "origin_iso3",
    "origin_census_code",
    "origin_name",
    "hts10",
    "hs6",
    "import_value_usd",
    "quantity",
    "quantity_unit",
    "customs_value",
    "duties",
    "dutiable_value_usd",
    "commodity_description",
    "source_file",
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


def configured_origins(country_groups: dict[str, Any]) -> list[str]:
    origins: list[str] = []
    for group in country_groups.get("source_bloc", {}).values():
        origins.extend(group)
    origins.extend(country_groups.get("core_connectors", []))
    origins.extend(country_groups.get("asian_comparators", []))
    origins.extend(country_groups.get("other_candidates", []))
    return unique_preserve_order([origin for origin in origins if origin != "EU27"])


def configured_years(time_windows: dict[str, Any], data_versions: dict[str, Any]) -> list[int]:
    usage = data_versions["us_census"].get("batch2_usage", {})
    required = usage.get("required_years", {})
    start = int(required.get("start", time_windows["pre_period"]["start"]))
    end = int(required.get("end", time_windows["post_period"]["end"]))
    return list(range(start, end + 1))


def months_for_years(years: list[int]) -> list[str]:
    return [f"{year}-{month:02d}" for year in years for month in range(1, 13)]


def api_key_from_env(data_versions: dict[str, Any], explicit_key: str | None) -> str:
    if explicit_key:
        return explicit_key
    env_name = data_versions["us_census"].get("api_key_env", "CENSUS_API_KEY")
    key = os.environ.get(env_name)
    if not key:
        raise RuntimeError(
            f"Missing Census API key. Set {env_name} in the environment or pass --api-key."
        )
    return key


def census_get(params: dict[str, str], api_key: str, retries: int = 8, sleep_seconds: float = 2.0) -> list[list[str]]:
    query = dict(params)
    query["key"] = api_key
    url = f"{API_BASE}?{urlencode(query)}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "trade-welfare-codex/1.0"})
            with urlopen(request, timeout=90) as response:
                content_type = response.headers.get("Content-Type", "")
                body = response.read().decode("utf-8")
            if not body.strip():
                return [str(params["get"]).split(",")]
            if "html" in content_type.lower() and ("Missing Key" in body or "Invalid Key" in body):
                if "Invalid Key" in body:
                    raise RuntimeError("Census API rejected the request because the API key is invalid.")
                raise RuntimeError("Census API rejected the request because the API key is missing.")
            parsed = json.loads(body)
            if not isinstance(parsed, list):
                raise RuntimeError(f"Unexpected Census API response: {body[:500]}")
            return parsed
        except (
            HTTPError,
            URLError,
            TimeoutError,
            IncompleteRead,
            RemoteDisconnected,
            ConnectionError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(sleep_seconds * attempt)
    raise RuntimeError(f"Census API request failed after {retries} attempts: {last_error}") from last_error


def api_rows_to_frame(rows: list[list[str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    header = rows[0]
    df = pd.DataFrame(rows[1:], columns=header)
    return df.loc[:, ~df.columns.duplicated()].copy()


def ensure_dirs(raw_dir: Path) -> dict[str, Path]:
    dirs = {
        "hs10": raw_dir / "hs10_monthly_imports",
        "hs6": raw_dir / "hs6_monthly_imports",
        "metadata": raw_dir / "metadata",
    }
    for directory in dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    return dirs


def build_country_lookup(
    api_key: str,
    raw_dirs: dict[str, Path],
    target_month: str,
    target_commodity: str,
    name_matches: dict[str, Any],
    overwrite: bool,
) -> pd.DataFrame:
    lookup_path = raw_dirs["metadata"] / f"us_census_country_lookup_{target_month}.json"
    if lookup_path.exists() and not overwrite:
        rows = json.loads(lookup_path.read_text(encoding="utf-8"))
    else:
        rows = census_get(
            {
                "get": "CTY_CODE,CTY_NAME",
                "time": target_month,
                "I_COMMODITY": target_commodity,
            },
            api_key=api_key,
        )
        lookup_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    lookup = api_rows_to_frame(rows)
    if lookup.empty:
        raise RuntimeError(f"Census country lookup returned no rows for {target_month}.")
    lookup = lookup[["CTY_CODE", "CTY_NAME"]].drop_duplicates().copy()
    lookup["CTY_NAME_NORMALIZED"] = lookup["CTY_NAME"].str.casefold()

    matched_rows = []
    for iso3, spec in name_matches["country_name_matches"].items():
        candidates = [name.casefold() for name in spec["census_names"]]
        matched = lookup[lookup["CTY_NAME_NORMALIZED"].isin(candidates)]
        if matched.empty:
            raise RuntimeError(f"Could not match {iso3} to any Census country names: {spec['census_names']}")
        if len(matched) > 1:
            raise RuntimeError(f"Multiple Census country matches for {iso3}: {matched[['CTY_CODE', 'CTY_NAME']].to_dict('records')}")
        row = matched.iloc[0]
        matched_rows.append(
            {
                "origin_iso3": iso3,
                "cty_code": str(row["CTY_CODE"]),
                "cty_name": str(row["CTY_NAME"]),
            }
        )
    matched_df = pd.DataFrame(matched_rows).sort_values("origin_iso3")
    matched_df.to_csv(raw_dirs["metadata"] / "us_census_country_code_matches.csv", index=False)
    return matched_df


def build_country_lookup_from_static(
    country_codes: dict[str, Any],
    origins: list[str],
    raw_dirs: dict[str, Path],
) -> pd.DataFrame:
    codes = country_codes.get("country_codes", {})
    missing = [origin for origin in origins if origin not in codes]
    if missing:
        raise RuntimeError(f"Missing static Census country codes for origins: {missing}")
    rows = []
    for origin in origins:
        spec = codes[origin]
        rows.append(
            {
                "origin_iso3": origin,
                "cty_code": str(spec["cty_code"]),
                "cty_name": str(spec["cty_name"]),
            }
        )
    matched_df = pd.DataFrame(rows).sort_values("origin_iso3")
    raw_dirs["metadata"].mkdir(parents=True, exist_ok=True)
    matched_df.to_csv(raw_dirs["metadata"] / "us_census_country_code_matches.csv", index=False)
    return matched_df


def raw_file_for(raw_dirs: dict[str, Path], level: str, month: str, origin_iso3: str, cty_code: str) -> Path:
    subdir = raw_dirs["hs10"] if level == "HS10" else raw_dirs["hs6"]
    safe_month = month.replace("-", "_")
    return subdir / f"us_census_imports_{level}_{safe_month}_{origin_iso3}_{cty_code}.json"


def download_raw(
    api_key: str,
    raw_dirs: dict[str, Path],
    months: list[str],
    countries: pd.DataFrame,
    levels: list[str],
    overwrite: bool,
    workers: int,
) -> list[Path]:
    tasks: list[tuple[str, str, str, str]] = []
    for level in levels:
        for month in months:
            for row in countries.itertuples(index=False):
                tasks.append((level, month, str(row.origin_iso3), str(row.cty_code)))

    def download_one(task: tuple[str, str, str, str]) -> Path:
        level, month, origin_iso3, cty_code = task
        path = raw_file_for(raw_dirs, level, month, origin_iso3, cty_code)
        if path.exists() and not overwrite:
            return path
        rows = census_get(
            {
                "get": ",".join(API_FIELDS),
                "time": month,
                "COMM_LVL": level,
                "CTY_CODE": cty_code,
            },
            api_key=api_key,
        )
        path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        return path

    downloaded: list[Path] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(download_one, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            path = future.result()
            downloaded.append(path)
            completed += 1
            if completed == 1 or completed % 25 == 0 or completed == len(tasks):
                print(f"Downloaded {completed}/{len(tasks)} Census files; latest={path.name}", flush=True)
    return downloaded


def parse_raw_file(
    path: Path,
    level: str,
    origin_iso3: str,
    source_file_path: Path | None = None,
) -> pd.DataFrame:
    rows = json.loads(path.read_text(encoding="utf-8"))
    df = api_rows_to_frame(rows)
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    missing = set(API_FIELDS) - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing API fields: {sorted(missing)}")

    commodity = df["I_COMMODITY"].astype("string")
    if level == "HS10":
        hts10 = commodity.str.zfill(10)
        hs6 = hts10.str.slice(0, 6)
    else:
        hs6 = commodity.str.zfill(6)
        hts10 = pd.Series([pd.NA] * len(df), dtype="string")

    out = pd.DataFrame(
        {
            "year": pd.to_numeric(df["YEAR"], errors="raise").astype("int16"),
            "month": pd.to_numeric(df["MONTH"], errors="raise").astype("int8"),
            "origin_iso3": origin_iso3,
            "origin_census_code": df["CTY_CODE"].astype("string"),
            "origin_name": df["CTY_NAME"].astype("string"),
            "hts10": hts10,
            "hs6": hs6,
            "import_value_usd": pd.to_numeric(df["GEN_VAL_MO"], errors="coerce"),
            "quantity": pd.to_numeric(df["GEN_QY1_MO"], errors="coerce"),
            "quantity_unit": df["UNIT_QY1"].astype("string"),
            "customs_value": pd.to_numeric(df["CON_VAL_MO"], errors="coerce"),
            "duties": pd.to_numeric(df["CAL_DUT_MO"], errors="coerce"),
            "dutiable_value_usd": pd.to_numeric(df["DUT_VAL_MO"], errors="coerce"),
            "commodity_description": df["I_COMMODITY_SDESC"].astype("string"),
            "source_file": str((source_file_path or path).as_posix()),
        },
        columns=OUTPUT_COLUMNS,
    )
    if out["import_value_usd"].isna().any():
        raise ValueError(f"{path} has missing or nonnumeric GEN_VAL_MO values.")
    if level == "HS10" and set(out["hts10"].str.len().dropna().unique()) != {10}:
        raise ValueError(f"{path} has non-10-digit HTS codes after padding.")
    if set(out["hs6"].str.len().dropna().unique()) != {6}:
        raise ValueError(f"{path} has non-6-digit HS codes after padding.")
    return out


def output_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("month", pa.int8()),
            pa.field("origin_iso3", pa.string()),
            pa.field("origin_census_code", pa.string()),
            pa.field("origin_name", pa.string()),
            pa.field("hts10", pa.string()),
            pa.field("hs6", pa.string()),
            pa.field("import_value_usd", pa.float64()),
            pa.field("quantity", pa.float64()),
            pa.field("quantity_unit", pa.string()),
            pa.field("customs_value", pa.float64()),
            pa.field("duties", pa.float64()),
            pa.field("dutiable_value_usd", pa.float64()),
            pa.field("commodity_description", pa.string()),
            pa.field("source_file", pa.string()),
        ]
    )


def write_level_parquet(
    raw_dirs: dict[str, Path],
    output_dir: Path,
    countries: pd.DataFrame,
    level: str,
    months: list[str],
    overwrite: bool,
    source_raw_dirs: dict[str, Path] | None = None,
) -> Path:
    output_name = "us_imports_hs10_monthly.parquet" if level == "HS10" else "us_imports_hs6_monthly.parquet"
    output_path = output_dir / output_name
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(f"{output_path} exists. Re-run with --overwrite to replace it.")
        output_path.unlink()
    writer = pq.ParquetWriter(output_path, output_schema(), compression="snappy")
    rows_written = 0
    try:
        for month in months:
            for row in countries.itertuples(index=False):
                path = raw_file_for(raw_dirs, level, month, row.origin_iso3, row.cty_code)
                if not path.exists():
                    raise FileNotFoundError(f"Missing raw Census API response: {path}")
                source_file_path = raw_file_for(source_raw_dirs or raw_dirs, level, month, row.origin_iso3, row.cty_code)
                df = parse_raw_file(
                    path,
                    level=level,
                    origin_iso3=row.origin_iso3,
                    source_file_path=source_file_path,
                )
                if df.empty:
                    continue
                writer.write_table(pa.Table.from_pandas(df, schema=output_schema(), preserve_index=False))
                rows_written += len(df)
    finally:
        writer.close()
    print(f"Wrote {output_path} with {rows_written} rows", flush=True)
    return output_path


def validate_outputs(paths: list[Path], years: list[int], expected_origins: list[str] | None = None) -> dict[str, Any]:
    results: dict[str, Any] = {}
    expected_columns = OUTPUT_COLUMNS
    for path in paths:
        parquet_file = pq.ParquetFile(path)
        if parquet_file.schema_arrow.names != expected_columns:
            raise ValueError(f"{path} columns differ from expected schema.")
        table = pq.read_table(path, columns=["year", "month", "origin_iso3", "hs6", "import_value_usd"])
        df = table.to_pandas()
        if not set(df["year"].unique()).issubset(set(years)):
            raise ValueError(f"{path} contains years outside requested range.")
        if df["import_value_usd"].isna().any():
            raise ValueError(f"{path} contains missing import_value_usd values.")
        origins = sorted(df["origin_iso3"].dropna().unique().tolist())
        if expected_origins is not None:
            missing_origins = sorted(set(expected_origins) - set(origins))
            if missing_origins:
                raise ValueError(f"{path} is missing expected origins: {missing_origins}")
        results[path.name] = {
            "rows": parquet_file.metadata.num_rows,
            "year_min": int(df["year"].min()) if len(df) else None,
            "year_max": int(df["year"].max()) if len(df) else None,
            "origins": origins,
            "positive_value_rows": int((df["import_value_usd"] > 0).sum()),
        }
    return results


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def remove_files(paths: list[Path]) -> None:
    for path in paths:
        if path.exists():
            path.unlink()


def publish_raw_files(stage_raw_dir: Path, final_raw_dir: Path) -> None:
    final_dirs = ensure_dirs(final_raw_dir)
    stage_dirs = {
        "hs10": stage_raw_dir / "hs10_monthly_imports",
        "hs6": stage_raw_dir / "hs6_monthly_imports",
        "metadata": stage_raw_dir / "metadata",
    }
    for key, final_dir in final_dirs.items():
        final_dir.mkdir(parents=True, exist_ok=True)
        for old_file in final_dir.glob("*"):
            if old_file.is_file():
                old_file.unlink()
        for staged_file in stage_dirs[key].glob("*"):
            if staged_file.is_file():
                staged_file.replace(final_dir / staged_file.name)


def publish_output_files(stage_output_dir: Path, final_output_dir: Path, levels: list[str]) -> list[Path]:
    final_output_dir.mkdir(parents=True, exist_ok=True)
    output_names: list[str] = []
    if "HS10" in levels:
        output_names.append("us_imports_hs10_monthly.parquet")
    if "HS6" in levels:
        output_names.append("us_imports_hs6_monthly.parquet")
    output_names.append("us_census_imports_build_summary.json")
    remove_files([final_output_dir / name for name in output_names])
    moved: list[Path] = []
    for name in output_names:
        staged = stage_output_dir / name
        if staged.exists():
            final = final_output_dir / name
            staged.replace(final)
            moved.append(final)
    return [path for path in moved if path.suffix == ".parquet"]


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    config_dir = project_root / "configs"
    data_versions = load_yaml(config_dir / "data_versions.yaml")
    country_groups = load_yaml(config_dir / "country_groups.yaml")
    time_windows = load_yaml(config_dir / "time_windows.yaml")
    name_matches = load_yaml(config_dir / "us_census_country_name_matches.yaml")
    static_country_codes_path = config_dir / "us_census_country_codes.yaml"
    static_country_codes = load_yaml(static_country_codes_path) if static_country_codes_path.exists() else None

    us_config = data_versions["us_census"]
    final_raw_dir = (project_root / us_config["raw_dir"]).resolve()
    final_output_dir = (project_root / us_config["batch2_usage"]["output_dir"]).resolve()
    final_output_dir.mkdir(parents=True, exist_ok=True)
    years = configured_years(time_windows, data_versions)
    months = months_for_years(years)
    levels = args.levels
    use_staging = not args.no_staging
    stage_raw_dir = final_raw_dir / "_staging_us_census_full"
    stage_output_dir = final_output_dir / "_staging_us_census_full"
    raw_dir = stage_raw_dir if use_staging and not args.process_only else final_raw_dir
    output_dir = stage_output_dir if use_staging and not args.download_only else final_output_dir
    if use_staging:
        remove_tree(stage_raw_dir)
        remove_tree(stage_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dirs = ensure_dirs(raw_dir)

    origins = args.origins or configured_origins(country_groups)
    name_matches = {
        "country_name_matches": {
            iso3: name_matches["country_name_matches"][iso3]
            for iso3 in origins
        }
    }

    if args.check_config:
        return {
            "raw_dir": str(final_raw_dir),
            "output_dir": str(final_output_dir),
            "years": years,
            "month_count": len(months),
            "origins": origins,
            "levels": levels,
            "api_key_env": us_config.get("api_key_env", "CENSUS_API_KEY"),
        }

    try:
        api_key: str | None = None
        if not args.process_only or static_country_codes is None:
            api_key = api_key_from_env(data_versions, args.api_key)
        if static_country_codes is not None:
            countries = build_country_lookup_from_static(static_country_codes, origins, raw_dirs)
        else:
            if api_key is None:
                raise RuntimeError("A Census API key is required to build the country lookup dynamically.")
            countries = build_country_lookup(
                api_key=api_key,
                raw_dirs=raw_dirs,
                target_month=args.country_lookup_month,
                target_commodity=args.country_lookup_commodity,
                name_matches=name_matches,
                overwrite=args.overwrite,
            )

        if not args.process_only:
            if api_key is None:
                raise RuntimeError("A Census API key is required to download raw Census data.")
            download_raw(
                api_key=api_key,
                raw_dirs=raw_dirs,
                months=months,
                countries=countries,
                levels=levels,
                overwrite=args.overwrite,
                workers=args.workers,
            )

        output_paths: list[Path] = []
        if not args.download_only:
            for level in levels:
                output_paths.append(
                    write_level_parquet(
                        raw_dirs=raw_dirs,
                        output_dir=output_dir,
                        countries=countries,
                        level=level,
                        months=months,
                        overwrite=args.overwrite,
                        source_raw_dirs=ensure_dirs(final_raw_dir) if use_staging else raw_dirs,
                    )
                )

        validation = validate_outputs(output_paths, years, origins) if output_paths else {}
        summary = {
            "raw_dir": str(final_raw_dir if use_staging else raw_dir),
            "output_dir": str(final_output_dir if use_staging else output_dir),
            "years": years,
            "months": months,
            "levels": levels,
            "origins": countries.to_dict("records"),
            "outputs": [str(path) for path in output_paths],
            "validation": validation,
            "staging_used": use_staging,
        }
        summary_path = output_dir / "us_census_imports_build_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        if use_staging:
            final_output_paths: list[Path] = []
            if not args.process_only:
                publish_raw_files(stage_raw_dir, final_raw_dir)
            if not args.download_only:
                final_output_paths = publish_output_files(stage_output_dir, final_output_dir, levels)
                validation = validate_outputs(final_output_paths, years, origins)
            summary["outputs"] = [str(path) for path in final_output_paths]
            summary["validation"] = validation
            (final_output_dir / "us_census_imports_build_summary.json").write_text(
                json.dumps(summary, indent=2),
                encoding="utf-8",
            )
            remove_tree(stage_raw_dir)
            remove_tree(stage_output_dir)
        return summary
    except Exception:
        if use_staging:
            remove_tree(stage_raw_dir)
            remove_tree(stage_output_dir)
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and process U.S. Census monthly HS import data.")
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--api-key", default=None, help="Census API key. Prefer CENSUS_API_KEY environment variable.")
    parser.add_argument("--levels", nargs="+", choices=["HS10", "HS6"], default=["HS10", "HS6"])
    parser.add_argument("--origins", nargs="+", default=None, help="Optional ISO3 origins to process.")
    parser.add_argument("--country-lookup-month", default="2024-01", help="Month used to fetch Census country code lookup.")
    parser.add_argument("--country-lookup-commodity", default="01", help="Commodity used to fetch Census country code lookup.")
    parser.add_argument("--download-only", action="store_true", help="Download raw API responses but do not write parquet.")
    parser.add_argument("--process-only", action="store_true", help="Process existing raw API responses without downloading.")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing raw responses and parquet outputs.")
    parser.add_argument("--check-config", action="store_true", help="Validate local config and print planned scope without API calls.")
    parser.add_argument("--workers", type=int, default=4, help="Parallel API download workers.")
    parser.add_argument("--no-staging", action="store_true", help="Write directly to final directories instead of staging first.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    summary = build(args)
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
