from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests


SOURCE_URL = "https://www.cepii.fr/DATA_DOWNLOAD/baci/data/BACI_HS17_V202601.zip"
ARCHIVE_NAME = "BACI_HS17_V202601.zip"
FLOW_NAME = "BACI_HS17_Y2017_V202601.csv"
COUNTRY_NAME = "country_codes_V202601.csv"
PRODUCT_NAME = "product_codes_HS17_V202601.csv"
README_NAME = "Readme.txt"


def download_archive(raw_dir: Path, verify: bool) -> Path:
    path = raw_dir / ARCHIVE_NAME
    if path.exists() and zipfile.is_zipfile(path):
        return path

    expected_size: int | None = None
    for attempt in range(1, 11):
        current_size = path.stat().st_size if path.exists() else 0
        headers = {"Range": f"bytes={current_size}-"} if current_size else {}
        try:
            with requests.get(
                SOURCE_URL,
                headers=headers,
                stream=True,
                timeout=300,
                verify=verify,
            ) as response:
                response.raise_for_status()
                if current_size and response.status_code != 206:
                    raise RuntimeError("CEPII server did not honor the BACI Range request")
                content_range = response.headers.get("Content-Range", "")
                if "/" in content_range:
                    expected_size = int(content_range.rsplit("/", 1)[1])
                elif response.headers.get("Content-Length"):
                    expected_size = current_size + int(response.headers["Content-Length"])
                mode = "ab" if current_size else "wb"
                with path.open(mode) as handle:
                    for block in response.iter_content(1024 * 1024):
                        if block:
                            handle.write(block)
        except (requests.RequestException, OSError) as error:
            if attempt == 10:
                raise RuntimeError(f"BACI download failed after {attempt} attempts") from error
            time.sleep(min(attempt * 2, 15))
            continue
        if expected_size is not None and path.stat().st_size == expected_size:
            return path
        if expected_size is not None and path.stat().st_size > expected_size:
            raise ValueError(f"BACI archive exceeds expected size {expected_size}")
    raise RuntimeError(f"BACI archive is incomplete: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_member(names: list[str], basename: str) -> str:
    matches = [name for name in names if Path(name).name.casefold() == basename.casefold()]
    if len(matches) != 1:
        raise ValueError(f"Expected one {basename} member, found {matches}")
    return matches[0]


def extract_required_inputs(raw_dir: Path, overwrite: bool) -> dict[str, Path]:
    archive = raw_dir / ARCHIVE_NAME
    if not archive.exists():
        raise FileNotFoundError(f"Missing BACI archive: {archive}")

    with zipfile.ZipFile(archive) as bundle:
        bad_member = bundle.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupt BACI archive member: {bad_member}")
        names = bundle.namelist()
        requested = [FLOW_NAME, COUNTRY_NAME, PRODUCT_NAME, README_NAME]
        extracted: dict[str, Path] = {}
        for basename in requested:
            member = find_member(names, basename)
            target = raw_dir / basename
            if overwrite or not target.exists():
                with bundle.open(member) as source, target.open("wb") as destination:
                    shutil.copyfileobj(source, destination, length=8 * 1024 * 1024)
            extracted[basename] = target
    return extracted


def country_codes(path: Path) -> tuple[int, int]:
    countries = pd.read_csv(path, dtype="string")
    required = {"country_code", "country_iso3"}
    missing = required - set(countries.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    lookup = countries.set_index("country_iso3")["country_code"]
    for iso3 in ("CHN", "USA"):
        if iso3 not in lookup.index:
            raise ValueError(f"{path} does not contain {iso3}")
    return int(lookup.loc["CHN"]), int(lookup.loc["USA"])


def product_codes(path: Path) -> pd.Series:
    products = pd.read_csv(path, dtype="string")
    if "code" not in products.columns:
        raise ValueError(f"{path} is missing the code column")
    codes = products["code"].str.replace(r"\D", "", regex=True).str.zfill(6)
    codes = codes[codes.str.len() == 6].drop_duplicates().sort_values().reset_index(drop=True)
    if len(codes) < 5_000:
        raise ValueError(f"{path} contains only {len(codes)} distinct HS6 codes")
    return codes


def build_stats(flow_path: Path, products: pd.Series, china_code: int, usa_code: int) -> pd.DataFrame:
    totals: list[pd.DataFrame] = []
    china: list[pd.DataFrame] = []
    source_rows = 0
    usa_rows = 0

    for chunk in pd.read_csv(
        flow_path,
        usecols=["i", "j", "k", "v"],
        dtype={"i": "int32", "j": "int32", "k": "string", "v": "float64"},
        chunksize=1_000_000,
    ):
        source_rows += len(chunk)
        us = chunk[chunk["j"] == usa_code].copy()
        if us.empty:
            continue
        usa_rows += len(us)
        us["hs6"] = us["k"].str.zfill(6)
        us["trade_value_usd"] = us["v"] * 1000.0
        totals.append(us.groupby("hs6", as_index=False)["trade_value_usd"].sum())
        china.append(
            us[us["i"] == china_code]
            .groupby("hs6", as_index=False)["trade_value_usd"]
            .sum()
        )

    if not totals:
        raise RuntimeError(f"{flow_path} contains no USA imports")
    total = (
        pd.concat(totals, ignore_index=True)
        .groupby("hs6", as_index=False)["trade_value_usd"]
        .sum()
        .rename(columns={"trade_value_usd": "baci_total_us_import_value_2017"})
    )
    china_total = (
        pd.concat(china, ignore_index=True)
        .groupby("hs6", as_index=False)["trade_value_usd"]
        .sum()
        .rename(columns={"trade_value_usd": "baci_china_import_value_2017"})
    )
    stats = pd.DataFrame({"hs6": products}).merge(total, on="hs6", how="left")
    stats = stats.merge(china_total, on="hs6", how="left")
    value_columns = [
        "baci_total_us_import_value_2017",
        "baci_china_import_value_2017",
    ]
    stats[value_columns] = stats[value_columns].fillna(0.0)
    stats["china_import_share_2017"] = 0.0
    positive = stats["baci_total_us_import_value_2017"] > 0
    stats.loc[positive, "china_import_share_2017"] = (
        stats.loc[positive, "baci_china_import_value_2017"]
        / stats.loc[positive, "baci_total_us_import_value_2017"]
    )
    stats.attrs.update(source_rows=source_rows, usa_rows=usa_rows)
    return stats


def validate(stats: pd.DataFrame) -> None:
    if stats["hs6"].duplicated().any():
        raise ValueError("BACI HS2017 output contains duplicate HS6 codes")
    if not stats["china_import_share_2017"].between(0, 1).all():
        raise ValueError("BACI HS2017 output contains an invalid China import share")
    if (stats["baci_china_import_value_2017"] > stats["baci_total_us_import_value_2017"] + 0.01).any():
        raise ValueError("China imports exceed total USA imports for at least one HS6 code")
    if float(stats["baci_total_us_import_value_2017"].sum()) <= 2e12:
        raise ValueError("BACI 2017 USA import total is implausibly small")


def write_outputs(stats: pd.DataFrame, output: Path, overwrite: bool) -> None:
    if output.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {output}; pass --overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(stats, preserve_index=False)
    pq.write_table(table, output, compression="zstd")


def run(
    project_root: Path,
    overwrite: bool,
    download_requested: bool,
    insecure: bool,
) -> dict[str, Any]:
    raw_dir = project_root / "data" / "raw" / "BACI_HS17_V202601"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if download_requested:
        download_archive(raw_dir, verify=not insecure)
    inputs = extract_required_inputs(raw_dir, overwrite)
    china_code, usa_code = country_codes(inputs[COUNTRY_NAME])
    products = product_codes(inputs[PRODUCT_NAME])
    stats = build_stats(inputs[FLOW_NAME], products, china_code, usa_code)
    source_rows = int(stats.attrs["source_rows"])
    usa_rows = int(stats.attrs["usa_rows"])
    validate(stats)

    output = project_root / "data" / "interim" / "trade" / "baci_hs17_us_imports_2017.parquet"
    write_outputs(stats, output, overwrite)
    summary = {
        "source": "CEPII BACI HS2017 V202601",
        "source_url": SOURCE_URL,
        "archive": str((raw_dir / ARCHIVE_NAME).relative_to(project_root)),
        "archive_sha256": sha256(raw_dir / ARCHIVE_NAME),
        "archive_zip_test": "passed",
        "flow_file": str(inputs[FLOW_NAME].relative_to(project_root)),
        "flow_file_sha256": sha256(inputs[FLOW_NAME]),
        "country_metadata_sha256": sha256(inputs[COUNTRY_NAME]),
        "product_metadata_sha256": sha256(inputs[PRODUCT_NAME]),
        "year": 2017,
        "nomenclature": "HS2017",
        "china_country_code": china_code,
        "usa_country_code": usa_code,
        "source_rows": source_rows,
        "usa_import_rows": usa_rows,
        "output_rows": int(len(stats)),
        "baci_total_us_imports_2017": float(stats["baci_total_us_import_value_2017"].sum()),
        "baci_china_imports_2017": float(stats["baci_china_import_value_2017"].sum()),
        "output": str(output.relative_to(project_root)),
        "output_sha256": sha256(output),
        "validation": "passed",
    }
    summary_path = output.with_name("baci_hs17_us_imports_2017_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact 2017 USA import denominator from BACI HS2017.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--download", action="store_true", help="Download or resume the official CEPII archive.")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS verification when an intercepting proxy prevents certificate validation.",
    )
    args = parser.parse_args()
    summary = run(args.project_root.resolve(), args.overwrite, args.download, args.insecure)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
