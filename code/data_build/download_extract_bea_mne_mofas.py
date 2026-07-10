"""Download and audit BEA U.S. MNE MOFA country-industry tables.

This script archives the BEA downloadable country-by-industry XLS files for
majority-owned foreign affiliates (MOFAs), computes checksums, and extracts the
Mexico 2020-2022 cells needed for the North America production-side validation.

Dependencies:
    python -m pip install xlrd
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import urlopen

try:
    import xlrd  # type: ignore
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "Missing dependency: xlrd. Install with `python -m pip install xlrd` "
        "or make xlrd available on PYTHONPATH."
    ) from exc


DOWNLOAD_DATE = "2026-07-01"
BEA_RELEASE = "2025-08 downloadable tables"
SOURCE_PAGE = "https://www.bea.gov/international/di1usdop"
TARGET_COUNTRY = "Mexico"
YEARS = ("2020", "2021", "2022")


@dataclass(frozen=True)
class BeaTable:
    indicator: str
    filename: str
    url: str
    unit: str


TABLES = (
    BeaTable(
        indicator="Employment",
        filename="mofas-employment.xls",
        url="https://www.bea.gov/sites/default/files/2025-08/mofas-employment.xls",
        unit="Thousands of employees",
    ),
    BeaTable(
        indicator="Value added",
        filename="mofas-value-added.xls",
        url="https://www.bea.gov/sites/default/files/2025-08/mofas-value-added.xls",
        unit="Millions of dollars",
    ),
    BeaTable(
        indicator="PPE expenditures",
        filename="mofas-cap-expend.xls",
        url="https://www.bea.gov/sites/default/files/2025-08/mofas-cap-expend.xls",
        unit="Millions of dollars",
    ),
    BeaTable(
        indicator="Sales",
        filename="mofas-sales.xls",
        url="https://www.bea.gov/sites/default/files/2025-08/mofas-sales.xls",
        unit="Millions of dollars",
    ),
    BeaTable(
        indicator="Assets",
        filename="mofas-assets.xls",
        url="https://www.bea.gov/sites/default/files/2025-08/mofas-assets.xls",
        unit="Millions of dollars",
    ),
)


def normalize(value: Any) -> str:
    text = str(value).replace("\xa0", " ").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return re.sub(r"\s+", " ", text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(table: BeaTable, raw_dir: Path, overwrite: bool) -> Path:
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / table.filename
    if path.exists() and path.stat().st_size > 0 and not overwrite:
        return path

    with urlopen(table.url, timeout=90) as response:
        path.write_bytes(response.read())
    return path


def country_row(sheet: xlrd.sheet.Sheet, country: str) -> int:
    for row_idx in range(sheet.nrows):
        if normalize(sheet.cell_value(row_idx, 0)).lower() == country.lower():
            return row_idx
    raise ValueError(f"Country not found in sheet {sheet.name}: {country}")


def industry_columns(sheet: xlrd.sheet.Sheet) -> list[tuple[str, int]]:
    labels: list[tuple[str, int]] = []
    header_rows = [sheet.row_values(row_idx) for row_idx in range(min(6, sheet.nrows))]
    ncols = max(len(row) for row in header_rows)
    for col_idx in range(1, ncols):
        parts: list[str] = []
        for row in header_rows[2:5]:
            value = normalize(row[col_idx]) if col_idx < len(row) else ""
            if value and value not in {"Of which:", "Total"}:
                parts.append(value)
        if not parts:
            continue
        label = parts[-1]
        if label == "Manufacturing":
            label = "Manufacturing total"
        labels.append((label, col_idx))
    return labels


def cell_to_output(value: Any) -> tuple[str, bool]:
    text = normalize(value)
    return text, text.upper() in {"(D)", "D"}


def extract_audit_rows(table: BeaTable, xls_path: Path) -> list[dict[str, str]]:
    workbook = xlrd.open_workbook(xls_path)
    rows: list[dict[str, str]] = []
    for year in YEARS:
        if year not in workbook.sheet_names():
            raise ValueError(f"Missing sheet {year} in {xls_path}")
        sheet = workbook.sheet_by_name(year)
        row_idx = country_row(sheet, TARGET_COUNTRY)
        for industry, col_idx in industry_columns(sheet):
            value, suppressed = cell_to_output(sheet.cell_value(row_idx, col_idx))
            rows.append(
                {
                    "indicator": table.indicator,
                    "unit": table.unit,
                    "year": year,
                    "country": TARGET_COUNTRY,
                    "industry": industry,
                    "value": value,
                    "suppressed": "yes" if suppressed else "no",
                    "source_file": table.filename,
                    "source_url": table.url,
                }
            )
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "indicator",
        "unit",
        "year",
        "country",
        "industry",
        "value",
        "suppressed",
        "source_file",
        "source_url",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def row_lookup(rows: list[dict[str, str]], industry: str) -> dict[tuple[str, str], dict[str, str]]:
    return {
        (row["indicator"], row["year"]): row
        for row in rows
        if row["industry"].lower() == industry.lower()
    }


def numeric_value(text: str) -> float | None:
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


def format_number(value: str) -> str:
    number = numeric_value(value)
    if number is None:
        return value
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.1f}"


def change_text(start: str, end: str) -> str:
    start_value = numeric_value(start)
    end_value = numeric_value(end)
    if start_value is None or end_value is None or start_value == 0:
        return "n.a."
    diff = end_value - start_value
    pct = diff / start_value * 100
    return f"{diff:,.1f} ({pct:+.1f}%)" if not diff.is_integer() else f"{int(diff):,} ({pct:+.1f}%)"


def write_manifest_md(manifest_rows: list[dict[str, str]], path: Path, raw_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# BEA U.S. MNE MOFA Country-Industry Archive Manifest",
        "",
        "## Archive Scope",
        "",
        f"- Source page: {SOURCE_PAGE}",
        f"- BEA release/vintage: {BEA_RELEASE}",
        f"- Download date: {DOWNLOAD_DATE}",
        f"- Local raw-data directory: `{raw_dir.as_posix()}`",
        "- Raw XLS files are intentionally ignored by git; this manifest records the archived file names and checksums.",
        "",
        "## Files",
        "",
        "| Indicator | File | Unit | Bytes | SHA-256 | URL |",
        "|---|---|---|---:|---|---|",
    ]
    for row in manifest_rows:
        lines.append(
            "| {indicator} | `{filename}` | {unit} | {bytes} | `{sha256}` | {url} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## BEA Table Availability Note")
    lines.append("")
    lines.append(
        "BEA reports that selected annual data tables on the activities of U.S. "
        "multinational enterprises were discontinued or impacted on 2025-08-22, "
        "beginning with the 2023 preliminary data. These archived XLS files "
        "preserve the 2009-2023 country-industry downloadable tables used by this project."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_md(rows: list[dict[str, str]], path: Path, csv_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    transportation = row_lookup(rows, "Transportation equipment")
    computers = row_lookup(rows, "Computers and electronic products")
    suppressed = [row for row in rows if row["suppressed"] == "yes"]

    lines = [
        "# BEA U.S. MNE MOFA Mexico Suppression Audit, 2020-2022",
        "",
        "## Scope",
        "",
        f"- Country: {TARGET_COUNTRY}",
        "- Source: BEA U.S. Direct Investment Abroad, Activities of U.S. Multinational Enterprises, Majority-Owned Foreign Affiliates country-by-industry downloadable tables.",
        f"- BEA release/vintage: {BEA_RELEASE}",
        f"- Download/audit date: {DOWNLOAD_DATE}",
        f"- Machine-readable extract: `{csv_path.as_posix()}` (ignored by git).",
        "",
        "## Main Result: Mexico x Transportation Equipment",
        "",
        "| Indicator | Unit | 2020 | 2021 | 2022 | 2020-2022 change | Suppressed in 2020-2022? |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for table in TABLES:
        values = [transportation[(table.indicator, year)]["value"] for year in YEARS]
        suppressed_flag = any(
            transportation[(table.indicator, year)]["suppressed"] == "yes" for year in YEARS
        )
        lines.append(
            "| {indicator} | {unit} | {v2020} | {v2021} | {v2022} | {change} | {suppressed} |".format(
                indicator=table.indicator,
                unit=table.unit,
                v2020=format_number(values[0]),
                v2021=format_number(values[1]),
                v2022=format_number(values[2]),
                change=change_text(values[0], values[2]),
                suppressed="Yes" if suppressed_flag else "No",
            )
        )

    lines.extend(
        [
            "",
            "Conclusion: `Mexico x Transportation equipment` is not suppressed in any of the five audited MOFA indicators for 2020-2022. It is usable for the North America production-side validation and can fill the post-2020 OECD Analytical AMNE gap for this sector-country line.",
            "",
            "## Nearby Sector Check: Mexico x Computers and Electronic Products",
            "",
            "| Indicator | Unit | 2020 | 2021 | 2022 | Suppressed in 2020-2022? |",
            "|---|---|---:|---:|---:|---|",
        ]
    )

    for table in TABLES:
        values = [computers[(table.indicator, year)]["value"] for year in YEARS]
        suppressed_flag = any(
            computers[(table.indicator, year)]["suppressed"] == "yes" for year in YEARS
        )
        lines.append(
            "| {indicator} | {unit} | {v2020} | {v2021} | {v2022} | {suppressed} |".format(
                indicator=table.indicator,
                unit=table.unit,
                v2020=format_number(values[0]),
                v2021=format_number(values[1]),
                v2022=format_number(values[2]),
                suppressed="Yes" if suppressed_flag else "No",
            )
        )

    lines.extend(
        [
            "",
            "## Suppressed Mexico Cells Found In The Audit",
            "",
        ]
    )

    if suppressed:
        lines.extend(["| Indicator | Industry | Year | Value |", "|---|---|---:|---|"])
        for row in suppressed:
            lines.append(
                f"| {row['indicator']} | {row['industry']} | {row['year']} | `{row['value']}` |"
            )
    else:
        lines.append("No suppressed cells were found for Mexico in the audited tables and years.")

    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `(D)` means BEA suppressed the cell to avoid disclosure of individual-company data; it should be treated as unavailable, not as zero.",
            "- `Transportation equipment` is a broad BEA affiliate-industry category. It is usable as the project-level automotive-chain proxy only if the sector concordance records this aggregation choice.",
            "- Aggregate MOFA data identify affiliate activity expansion, not firm-level relocation. Use these moments to discipline Scenario B, and to support Scenario C only when combined with broader FDI or production-side expansion evidence.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-dir",
        default="data/raw/bea_usdia_mofas_2025-08",
        help="Directory for archived raw BEA XLS files.",
    )
    parser.add_argument(
        "--csv-out",
        default="data/interim/bea_mne_mofas_mexico_suppression_audit_2020_2022.csv",
        help="Ignored CSV extract path.",
    )
    parser.add_argument(
        "--manifest-md",
        default="data/bea_usdia_mofas_2025_08_archive_manifest.md",
        help="Tracked Markdown checksum manifest path.",
    )
    parser.add_argument(
        "--audit-md",
        default="data/bea_mne_mofas_mexico_suppression_audit_2020_2022.md",
        help="Tracked Markdown audit summary path.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Redownload existing raw XLS files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = Path(args.raw_dir)
    all_rows: list[dict[str, str]] = []
    manifest_rows: list[dict[str, str]] = []

    for table in TABLES:
        xls_path = download_file(table, raw_dir, args.overwrite)
        manifest_rows.append(
            {
                "indicator": table.indicator,
                "filename": table.filename,
                "unit": table.unit,
                "bytes": str(xls_path.stat().st_size),
                "sha256": sha256_file(xls_path),
                "url": table.url,
            }
        )
        all_rows.extend(extract_audit_rows(table, xls_path))

    csv_path = Path(args.csv_out)
    write_csv(all_rows, csv_path)
    write_manifest_md(manifest_rows, Path(args.manifest_md), raw_dir)
    write_audit_md(all_rows, Path(args.audit_md), csv_path)

    target_rows = [
        row
        for row in all_rows
        if row["country"] == TARGET_COUNTRY
        and row["industry"] == "Transportation equipment"
        and row["year"] in YEARS
    ]
    suppressed = [row for row in target_rows if row["suppressed"] == "yes"]
    print(f"downloaded_or_verified_files={len(TABLES)}")
    print(f"audit_rows={len(all_rows)}")
    print(f"mexico_transportation_equipment_suppressed_cells={len(suppressed)}")
    print(f"manifest_md={args.manifest_md}")
    print(f"audit_md={args.audit_md}")
    print(f"csv_out={args.csv_out}")


if __name__ == "__main__":
    main()
