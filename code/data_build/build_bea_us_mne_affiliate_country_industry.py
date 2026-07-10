from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import xlrd
import yaml


DOWNLOAD_DATE = date.today().isoformat()
BEA_RELEASE = "2017-2023 annual comprehensive tables; 2023 preliminary from 2025-08 release"
MAIN_SOURCE_PAGE = "https://www.bea.gov/news/2025/activities-us-multinational-enterprises-2023"
USDIA_SOURCE_PAGE = "https://www.bea.gov/international/di1usdop"
DEFAULT_YEARS = list(range(2017, 2024))

SOURCE_PAGES = {
    2023: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-preliminary-2023-statistics",
    2022: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2022-statistics",
    2021: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2021-statistics",
    2020: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2020-statistics",
    2019: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2019-statistics",
    2018: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2018-statistics",
    2017: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2017-statistics",
    2016: "https://www.bea.gov/worldwide-activities-us-multinational-enterprises-revised-2016-statistics",
    2015: "https://www.bea.gov/international/usdia2015r",
    2014: "https://www.bea.gov/international/usdia2014r",
    2013: "https://apps.bea.gov/international/usdia2013r.htm",
    2012: "https://apps.bea.gov/international/usdia2012r.htm",
    2011: "https://apps.bea.gov/international/usdia2011r.htm",
    2010: "https://apps.bea.gov/international/usdia2010r.htm",
    2009: "https://apps.bea.gov/international/usdia2009r.htm",
}

AGGREGATE_AREAS = {
    "All countries",
    "Europe",
    "Latin America and Other Western Hemisphere",
    "South America",
    "Central America",
    "Other Western Hemisphere",
    "South and Central America",
    "Africa",
    "Middle East",
    "Asia and Pacific",
    "Other",
}

MINIMUM_COLUMNS = [
    "year",
    "affiliate_country",
    "industry",
    "employment",
    "sales",
    "value_added",
    "capital_expenditures",
    "goods_exports_to_us",
    "goods_imports_from_us",
]


@dataclass(frozen=True)
class TableSpec:
    indicator: str
    group_key: str
    group_pattern: str
    sheet_name: str
    unit: str
    source_definition: str


TABLE_SPECS = [
    TableSpec(
        indicator="capital_expenditures",
        group_key="C",
        group_pattern="partiic",
        sheet_name="Table II.C 4",
        unit="Millions of dollars",
        source_definition="Table II.C 4. Expenditures for Property, Plant, and Equipment by Affiliates, Country by Industry of Affiliate",
    ),
    TableSpec(
        indicator="sales",
        group_key="D",
        group_pattern="partiid",
        sheet_name="Table II.D 3",
        unit="Millions of dollars",
        source_definition="Table II.D 3. Sales by Affiliates, Country by Industry of Affiliate",
    ),
    TableSpec(
        indicator="value_added",
        group_key="F",
        group_pattern="partiif",
        sheet_name="Table II.F 3",
        unit="Millions of dollars",
        source_definition="Table II.F 3. Value Added of Affiliates, Country by Industry of Affiliate",
    ),
    TableSpec(
        indicator="employment",
        group_key="G",
        group_pattern="partiig",
        sheet_name="Table II.G 1",
        unit="Thousands of employees",
        source_definition="Table II.G 1. Employment of Affiliates, Country by Industry of Affiliate",
    ),
    TableSpec(
        indicator="goods_imports_from_us",
        group_key="H",
        group_pattern="partiih",
        sheet_name="Table II.H 3",
        unit="Millions of dollars",
        source_definition="Table II.H 3. U.S. Exports of Goods Shipped to Affiliates, Country by Industry of Affiliate; affiliate-side interpretation: goods imported from the United States",
    ),
    TableSpec(
        indicator="goods_exports_to_us",
        group_key="H",
        group_pattern="partiih",
        sheet_name="Table II.H 11",
        unit="Millions of dollars",
        source_definition="Table II.H 11. U.S. Imports of Goods Shipped by Affiliates, Country by Industry of Affiliate; affiliate-side interpretation: goods exported to the United States",
    ),
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def normalize(value: Any) -> str:
    text = str(value).replace("\xa0", " ").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return re.sub(r"\s+", " ", text)


def compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unquote(value).lower())


def request_bytes(url: str, timeout: int = 90) -> bytes:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    request = Request(url, headers={"User-Agent": "trade-welfare-data-build/1.0"})
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=timeout, context=context) as response:
                return response.read()
        except (URLError, TimeoutError, ssl.SSLError) as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to fetch {url} after 3 attempts: {last_error}") from last_error


def fetch_html(url: str) -> str:
    return request_bytes(url, timeout=60).decode("utf-8", errors="replace")


def extract_links(page_url: str) -> list[str]:
    html = fetch_html(page_url)
    links = re.findall(r"href=[\"']([^\"']+)[\"']", html, flags=re.IGNORECASE)
    return [urljoin(page_url, link) for link in links]


def select_group_urls(year: int, page_url: str) -> dict[str, str]:
    urls = [url for url in extract_links(page_url) if urlparse(url).path.lower().endswith(".xls")]
    selected: dict[str, str] = {}
    for url in urls:
        name = compact_text(Path(urlparse(url).path).name)
        if "partii" not in name:
            continue
        for spec in TABLE_SPECS:
            if spec.group_key in selected:
                continue
            if spec.group_pattern in name:
                selected[spec.group_key] = url
    missing = sorted({spec.group_key for spec in TABLE_SPECS} - set(selected))
    if missing:
        raise ValueError(
            f"Could not locate BEA Part II group files for year {year}: {missing}; page={page_url}"
        )
    return selected


def safe_filename(url: str, year: int) -> str:
    name = unquote(Path(urlparse(url).path).name)
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return f"{year}_{name}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, path: Path, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0 and not overwrite:
        return
    path.write_bytes(request_bytes(url))


def find_sheet(workbook: xlrd.book.Book, requested_name: str) -> xlrd.sheet.Sheet:
    if requested_name in workbook.sheet_names():
        return workbook.sheet_by_name(requested_name)
    requested_compact = compact_text(requested_name)
    for sheet_name in workbook.sheet_names():
        if compact_text(sheet_name) == requested_compact:
            return workbook.sheet_by_name(sheet_name)
    for sheet_name in workbook.sheet_names():
        sheet = workbook.sheet_by_name(sheet_name)
        for row_idx in range(min(sheet.nrows, 8)):
            if requested_name in normalize(sheet.cell_value(row_idx, 0)):
                return sheet
    raise ValueError(f"Missing sheet {requested_name}; available={workbook.sheet_names()}")


def column_number_row(sheet: xlrd.sheet.Sheet) -> int:
    for row_idx in range(min(sheet.nrows, 20)):
        values = [normalize(sheet.cell_value(row_idx, col_idx)) for col_idx in range(1, sheet.ncols)]
        matches = sum(1 for value in values if re.fullmatch(r"\(\d+\)", value))
        if matches >= 3:
            return row_idx
    raise ValueError(f"Could not find column-number row in sheet {sheet.name}.")


def industry_columns(sheet: xlrd.sheet.Sheet, number_row: int) -> list[tuple[str, int]]:
    labels: list[tuple[str, int]] = []
    header_start = max(0, number_row - 4)
    for col_idx in range(1, sheet.ncols):
        parts: list[str] = []
        for row_idx in range(header_start, number_row):
            value = normalize(sheet.cell_value(row_idx, col_idx))
            if not value or value == "Of which:":
                continue
            parts.append(value)
        if not parts:
            continue
        if parts[-1] == "Total" and len(parts) >= 2:
            label = f"{parts[-2]} total"
        else:
            label = parts[-1]
        labels.append((label, col_idx))
    return labels


def classify_area(label: str, in_addendum: bool) -> str:
    if in_addendum:
        return "addendum"
    if label in AGGREGATE_AREAS:
        return "aggregate"
    return "country_or_area"


def should_skip_label(label: str) -> bool:
    upper = label.upper()
    return (
        upper.startswith("NOTE.")
        or upper.startswith("NOTES:")
        or upper.startswith("SOURCE:")
        or upper.startswith("ADDENDA")
        or upper.startswith("ADDENDUM")
    )


def parse_bea_value(value: Any) -> dict[str, Any]:
    text = normalize(value)
    upper = text.upper()
    if text == "":
        return {"value": None, "raw_code": "", "suppressed": False, "small_value": False}
    if upper in {"(D)", "D", "A", "F", "G", "H", "I", "J", "K", "L", "M"}:
        return {"value": None, "raw_code": text, "suppressed": True, "small_value": False}
    if upper in {"(*)", "*"}:
        return {"value": 0.0, "raw_code": text, "suppressed": False, "small_value": True}
    try:
        return {
            "value": float(text.replace(",", "")),
            "raw_code": text,
            "suppressed": False,
            "small_value": False,
        }
    except ValueError:
        return {"value": None, "raw_code": text, "suppressed": False, "small_value": False}


def extract_indicator_rows(
    year: int,
    spec: TableSpec,
    xls_path: Path,
    source_url: str,
    source_page: str,
    include_addenda: bool,
) -> list[dict[str, Any]]:
    workbook = xlrd.open_workbook(xls_path)
    sheet = find_sheet(workbook, spec.sheet_name)
    number_row = column_number_row(sheet)
    columns = industry_columns(sheet, number_row)
    rows: list[dict[str, Any]] = []
    in_addendum = False
    parent_area = ""
    for row_idx in range(number_row + 1, sheet.nrows):
        label = normalize(sheet.cell_value(row_idx, 0))
        if not label:
            continue
        if label.rstrip(":") in {"Addendum", "Addenda"}:
            in_addendum = True
            continue
        if should_skip_label(label):
            continue
        if in_addendum and not include_addenda:
            continue
        area_type = classify_area(label, in_addendum)
        output_label = label
        if label == "Other" and parent_area:
            output_label = f"{parent_area}: Other"
        if area_type == "aggregate" and label != "Other":
            parent_area = label
        for industry, col_idx in columns:
            parsed = parse_bea_value(sheet.cell_value(row_idx, col_idx))
            rows.append(
                {
                    "year": year,
                    "affiliate_country": output_label,
                    "bea_parent_area": parent_area,
                    "bea_area_type": area_type,
                    "industry": industry,
                    "indicator": spec.indicator,
                    "value": parsed["value"],
                    "raw_code": parsed["raw_code"],
                    "suppressed": parsed["suppressed"],
                    "small_value": parsed["small_value"],
                    "unit": spec.unit,
                    "source_file": xls_path.as_posix(),
                    "source_url": source_url,
                    "source_page": source_page,
                }
            )
    return rows


def schema() -> pa.Schema:
    fields = [
        pa.field("year", pa.int16()),
        pa.field("affiliate_country", pa.string()),
        pa.field("industry", pa.string()),
        pa.field("employment", pa.float64()),
        pa.field("sales", pa.float64()),
        pa.field("value_added", pa.float64()),
        pa.field("capital_expenditures", pa.float64()),
        pa.field("goods_exports_to_us", pa.float64()),
        pa.field("goods_imports_from_us", pa.float64()),
        pa.field("bea_area_type", pa.string()),
        pa.field("bea_parent_area", pa.string()),
    ]
    for spec in TABLE_SPECS:
        fields.extend(
            [
                pa.field(f"{spec.indicator}_raw_code", pa.string()),
                pa.field(f"{spec.indicator}_suppressed", pa.bool_()),
                pa.field(f"{spec.indicator}_small_value", pa.bool_()),
                pa.field(f"{spec.indicator}_source_file", pa.string()),
            ]
        )
    fields.extend(
        [
            pa.field("release_vintage", pa.string()),
            pa.field("download_date", pa.string()),
            pa.field("source_page", pa.string()),
        ]
    )
    return pa.schema(fields)


def pivot_long(long: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["year", "affiliate_country", "industry"]
    duplicate_rows = int(long.duplicated(key_cols + ["indicator"]).sum())
    if duplicate_rows:
        raise ValueError(f"Duplicate BEA year/country/industry/indicator rows: {duplicate_rows}")

    values = long.pivot(index=key_cols, columns="indicator", values="value").reset_index()
    area = long[key_cols + ["bea_area_type"]].drop_duplicates(key_cols)
    out = values.merge(area, on=key_cols, how="left", validate="one_to_one")
    parent_area = long[key_cols + ["bea_parent_area"]].drop_duplicates(key_cols)
    out = out.merge(parent_area, on=key_cols, how="left", validate="one_to_one")

    for spec in TABLE_SPECS:
        subset = long[long["indicator"] == spec.indicator].copy()
        subset = subset.rename(
            columns={
                "raw_code": f"{spec.indicator}_raw_code",
                "suppressed": f"{spec.indicator}_suppressed",
                "small_value": f"{spec.indicator}_small_value",
                "source_file": f"{spec.indicator}_source_file",
            }
        )
        keep = key_cols + [
            f"{spec.indicator}_raw_code",
            f"{spec.indicator}_suppressed",
            f"{spec.indicator}_small_value",
            f"{spec.indicator}_source_file",
        ]
        out = out.merge(subset[keep], on=key_cols, how="left", validate="one_to_one")

    for column in MINIMUM_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    out["release_vintage"] = BEA_RELEASE
    out["download_date"] = DOWNLOAD_DATE
    out["source_page"] = USDIA_SOURCE_PAGE
    ordered = schema().names
    return out[ordered].sort_values(["year", "affiliate_country", "industry"]).reset_index(drop=True)


def remove_if_exists(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"{path} exists. Re-run with --overwrite to replace it.")
        path.unlink()


def validate_output(path: Path, years: list[int], include_addenda: bool) -> dict[str, Any]:
    table = pq.read_table(path)
    if table.schema.names != schema().names:
        raise ValueError(f"{path} columns do not match expected schema.")
    df = table.to_pandas()
    missing_cols = sorted(set(MINIMUM_COLUMNS) - set(df.columns))
    if missing_cols:
        raise ValueError(f"Missing minimum columns: {missing_cols}")
    if sorted(int(x) for x in df["year"].unique()) != years:
        raise ValueError(f"{path} does not contain exactly the requested years.")
    duplicate_keys = int(df.duplicated(["year", "affiliate_country", "industry"]).sum())
    if duplicate_keys:
        raise ValueError(f"{path} contains duplicate year/country/industry rows: {duplicate_keys}")

    connector_rows = df[
        df["affiliate_country"].isin(["Canada", "Mexico", "Vietnam"])
        & (df["industry"] == "Transportation equipment")
    ].copy()
    return {
        "rows": int(len(df)),
        "years": years,
        "affiliate_country_rows": int(df["affiliate_country"].nunique()),
        "industries": int(df["industry"].nunique()),
        "area_types": sorted(df["bea_area_type"].dropna().unique().tolist()),
        "include_addenda": include_addenda,
        "minimum_fields_present": True,
        "suppressed_cells_by_indicator": {
            spec.indicator: int(df[f"{spec.indicator}_suppressed"].sum()) for spec in TABLE_SPECS
        },
        "small_value_cells_by_indicator": {
            spec.indicator: int(df[f"{spec.indicator}_small_value"].sum()) for spec in TABLE_SPECS
        },
        "connector_transportation_equipment_rows": int(len(connector_rows)),
        "connector_transportation_equipment_suppressed_cells": {
            spec.indicator: int(connector_rows[f"{spec.indicator}_suppressed"].sum())
            for spec in TABLE_SPECS
        },
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    tmp_dir = project_root / "tmp" / "bea_mne"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    os.environ["TMP"] = str(tmp_dir)
    os.environ["TEMP"] = str(tmp_dir)

    data_versions = load_yaml(project_root / "configs" / "data_versions.yaml")
    raw_root = project_root / data_versions["bea_mne"]["raw_dir"]
    raw_dir = raw_root / "activities_us_mnes"
    metadata_dir = raw_root / "metadata"
    output_dir = project_root / "data" / "interim" / "mne"
    raw_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    years = sorted(args.years)
    unsupported = sorted(set(years) - set(SOURCE_PAGES))
    if unsupported:
        raise ValueError(f"Unsupported years for this build script: {unsupported}")

    output_path = output_dir / "bea_us_mne_affiliate_country_industry.parquet"
    summary_path = output_dir / "bea_us_mne_affiliate_country_industry_build_summary.json"
    manifest_path = metadata_dir / "bea_us_mne_activities_manifest.json"
    remove_if_exists(output_path, args.overwrite)
    remove_if_exists(summary_path, args.overwrite)
    remove_if_exists(manifest_path, args.overwrite)

    long_rows: list[dict[str, Any]] = []
    manifest_files: list[dict[str, Any]] = []
    pages: dict[int, str] = {}
    for year in years:
        page_url = SOURCE_PAGES[year]
        print(f"Processing BEA U.S. MNE activities {year}", flush=True)
        group_urls = select_group_urls(year, page_url)
        pages[year] = page_url
        for group_key, url in sorted(group_urls.items()):
            local_path = raw_dir / str(year) / safe_filename(url, year)
            download_file(url, local_path, overwrite=args.overwrite_raw)
            manifest_files.append(
                {
                    "year": year,
                    "group": group_key,
                    "source_url": url,
                    "local_path": local_path.relative_to(project_root).as_posix(),
                    "bytes": local_path.stat().st_size,
                    "sha256": sha256_file(local_path),
                }
            )
            for spec in [item for item in TABLE_SPECS if item.group_key == group_key]:
                long_rows.extend(
                    extract_indicator_rows(
                        year=year,
                        spec=spec,
                        xls_path=local_path,
                        source_url=url,
                        source_page=page_url,
                        include_addenda=args.include_addenda,
                    )
                )

    long = pd.DataFrame(long_rows)
    output = pivot_long(long)
    table = pa.Table.from_pandas(output, schema=schema(), preserve_index=False)
    pq.write_table(table, output_path, compression=args.compression)

    manifest = {
        "source": "BEA Activities of U.S. Multinational Enterprises, Majority-Owned Foreign Affiliates",
        "main_source_page": MAIN_SOURCE_PAGE,
        "usd_direct_investment_abroad_page": USDIA_SOURCE_PAGE,
        "release_vintage": BEA_RELEASE,
        "download_date": DOWNLOAD_DATE,
        "raw_dir": raw_dir.relative_to(project_root).as_posix(),
        "metadata_dir": metadata_dir.relative_to(project_root).as_posix(),
        "years": years,
        "source_pages": pages,
        "table_definitions": [spec.__dict__ for spec in TABLE_SPECS],
        "files": manifest_files,
        "value_rules": {
            "(D)": "Disclosure suppression; output numeric value is missing and *_suppressed is true.",
            "employment_size_range_codes": "Employment cells can use A/F/G/H/I/J/K/L/M size-range codes for suppressed cells; output numeric value is missing and *_suppressed is true.",
            "(*)": "Rounds to less than half the reporting unit; output numeric value is 0.0 and *_small_value is true.",
            "other_non_numeric": "Preserved in *_raw_code; output numeric value is missing.",
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    validation = validate_output(output_path, years, args.include_addenda)
    summary = {
        "source": manifest["source"],
        "release_vintage": BEA_RELEASE,
        "download_date": DOWNLOAD_DATE,
        "raw_dir": manifest["raw_dir"],
        "manifest": manifest_path.relative_to(project_root).as_posix(),
        "output": output_path.relative_to(project_root).as_posix(),
        "coverage": {
            "years": years,
            "ownership_scope": "majority-owned foreign affiliates of U.S. MNEs",
            "geography": "BEA affiliate country or area rows; use bea_area_type to filter aggregates",
            "industry": "BEA industry of affiliate columns from country-by-industry tables",
            "units": {
                "employment": "thousands of employees",
                "sales": "millions of dollars",
                "value_added": "millions of dollars",
                "capital_expenditures": "millions of dollars",
                "goods_exports_to_us": "millions of dollars",
                "goods_imports_from_us": "millions of dollars",
            },
        },
        "validation": validation,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(validation, indent=2), flush=True)
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build BEA U.S. MNE majority-owned foreign affiliate country-industry panel."
    )
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--years", nargs="+", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--overwrite", action="store_true", help="Replace existing parquet and metadata outputs.")
    parser.add_argument("--overwrite-raw", action="store_true", help="Redownload existing BEA raw XLS files.")
    parser.add_argument("--include-addenda", action="store_true", help="Include BEA addendum rows such as EU aggregates.")
    parser.add_argument("--compression", default="snappy", help="Parquet compression codec.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
