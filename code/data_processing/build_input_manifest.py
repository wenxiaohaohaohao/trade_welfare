from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.compute as pc
import pyarrow.parquet as pq


@dataclass(frozen=True)
class InputSpec:
    input_id: str
    relative_path: str
    source: str
    release: str
    natural_grain: str
    natural_key: tuple[str, ...]
    builder: str
    build_summary: str
    expected_rows: int
    expected_years: tuple[int, ...]


INPUT_SPECS = (
    InputSpec(
        input_id="baci_hs6_panel",
        relative_path="data/interim/trade/baci_hs6_panel.parquet",
        source="CEPII BACI",
        release="HS2012 Version 202601",
        natural_grain="exporter-importer-HS6-year",
        natural_key=("year", "exporter_iso3", "importer_iso3", "hs6"),
        builder="code/data_build/build_baci_batch1.py",
        build_summary="data/interim/trade/baci_batch1_build_summary.json",
        expected_rows=123_313_077,
        expected_years=tuple(range(2014, 2025)),
    ),
    InputSpec(
        input_id="us_census_hs6_monthly",
        relative_path="data/interim/trade/us_imports_hs6_monthly.parquet",
        source="U.S. Census International Trade API",
        release="validated configured-origin batch",
        natural_grain="origin-HS6-month",
        natural_key=("year", "month", "origin_iso3", "hs6"),
        builder="code/data_build/download_us_census_imports.py",
        build_summary="data/interim/trade/us_census_imports_build_summary.json",
        expected_rows=5_017_364,
        expected_years=tuple(range(2014, 2025)),
    ),
    InputSpec(
        input_id="section301_hs6_exposure",
        relative_path="data/interim/policy/section301_hs6_exposure.parquet",
        source="USTR Section 301 public notices with BACI/Census weights",
        release="validated base-list exposure batch",
        natural_grain="HS2017 product-year",
        natural_key=("hs6", "year"),
        builder="code/data_build/build_ustr_section301.py",
        build_summary="data/interim/policy/section301_build_summary.json",
        expected_rows=55_308,
        expected_years=tuple(range(2014, 2025)),
    ),
    InputSpec(
        input_id="oecd_icio_output_va_fd",
        relative_path="data/interim/production/oecd_icio_output_va_fd.parquet",
        source="OECD Inter-Country Input-Output tables",
        release="ICIO 2025 edition regular tables",
        natural_grain="country-OECD-sector-year",
        natural_key=("year", "country_iso3", "sector_oecd"),
        builder="code/data_build/build_oecd_icio_baseline.py",
        build_summary="data/interim/production/oecd_icio_build_summary.json",
        expected_rows=12_150,
        expected_years=(2017, 2018, 2022),
    ),
    InputSpec(
        input_id="oecd_amne_affiliate_activity",
        relative_path="data/interim/mne/oecd_amne_affiliate_activity.parquet",
        source="OECD Analytical AMNE",
        release="2026 release",
        natural_grain="parent-host-OECD-sector-year",
        natural_key=("year", "host_country_iso3", "parent_country_iso3", "sector_oecd"),
        builder="code/data_build/build_oecd_amne.py",
        build_summary="data/interim/mne/oecd_amne_build_summary.json",
        expected_rows=1_260_053,
        expected_years=tuple(range(2008, 2024)),
    ),
    InputSpec(
        input_id="bea_us_mne_affiliate_country_industry",
        relative_path="data/interim/mne/bea_us_mne_affiliate_country_industry.parquet",
        source="BEA Activities of U.S. Multinational Enterprises",
        release="2017-2023 comprehensive country-industry batch",
        natural_grain="affiliate-country-industry-year",
        natural_key=("year", "affiliate_country", "industry"),
        builder="code/data_build/build_bea_us_mne_affiliate_country_industry.py",
        build_summary="data/interim/mne/bea_us_mne_affiliate_country_industry_build_summary.json",
        expected_rows=8_256,
        expected_years=tuple(range(2017, 2024)),
    ),
    InputSpec(
        input_id="bea_direct_investment_country_industry",
        relative_path="data/interim/fdi/bea_direct_investment_country_industry.parquet",
        source="BEA Direct Investment by Country and Industry",
        release="2020-2024 two-direction batch",
        natural_grain="direction-country-industry-year",
        natural_key=("year", "direction", "country", "industry"),
        builder="code/data_build/build_bea_direct_investment_country_industry.py",
        build_summary="data/interim/fdi/bea_direct_investment_country_industry_build_summary.json",
        expected_rows=11_610,
        expected_years=tuple(range(2020, 2025)),
    ),
    InputSpec(
        input_id="mexico_fdi_country_sector_quarterly",
        relative_path="data/interim/fdi/mexico_fdi_country_sector_quarterly.parquet",
        source="Mexico Secretaria de Economia official FDI tables",
        release="national release through 2024Q4; country-sector quarterly input observed through 2024Q2",
        natural_grain="parent-country-SCIAN-sector-quarter",
        natural_key=(
            "year",
            "quarter",
            "parent_country_name",
            "sector_level",
            "sector_code",
        ),
        builder="code/data_build/download_build_mexico_fdi.py",
        build_summary="data/interim/fdi/mexico_fdi_build_summary.json",
        expected_rows=596_366,
        expected_years=tuple(range(2006, 2025)),
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_years(parquet_file: pq.ParquetFile, year_column: str = "year") -> list[int]:
    years: set[int] = set()
    for batch in parquet_file.iter_batches(batch_size=1_000_000, columns=[year_column]):
        unique = pc.unique(batch.column(0))
        years.update(int(value.as_py()) for value in unique if value.as_py() is not None)
    return sorted(years)


def schema_record(parquet_file: pq.ParquetFile) -> list[dict[str, Any]]:
    return [
        {
            "name": field.name,
            "type": str(field.type),
            "nullable": bool(field.nullable),
        }
        for field in parquet_file.schema_arrow
    ]


def git_value(project_root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def inspect_input(project_root: Path, spec: InputSpec) -> dict[str, Any]:
    path = project_root / spec.relative_path
    summary_path = project_root / spec.build_summary
    builder_path = project_root / spec.builder
    if not path.is_file():
        raise FileNotFoundError(f"Missing input: {path}")
    if not summary_path.is_file():
        raise FileNotFoundError(f"Missing build summary: {summary_path}")
    if not builder_path.is_file():
        raise FileNotFoundError(f"Missing builder: {builder_path}")

    parquet_file = pq.ParquetFile(path)
    schema = schema_record(parquet_file)
    schema_names = {field["name"] for field in schema}
    missing_key_fields = [field for field in spec.natural_key if field not in schema_names]
    if missing_key_fields:
        raise ValueError(f"{spec.input_id} is missing natural-key fields: {missing_key_fields}")

    rows = int(parquet_file.metadata.num_rows)
    years = exact_years(parquet_file)
    row_count_matches = rows == spec.expected_rows
    years_match = years == list(spec.expected_years)
    if not row_count_matches:
        raise ValueError(
            f"{spec.input_id} row count changed: expected {spec.expected_rows:,}, found {rows:,}"
        )
    if not years_match:
        raise ValueError(
            f"{spec.input_id} year coverage changed: expected {list(spec.expected_years)}, found {years}"
        )

    return {
        "input_id": spec.input_id,
        "path": spec.relative_path,
        "source": spec.source,
        "release": spec.release,
        "natural_grain": spec.natural_grain,
        "natural_key": list(spec.natural_key),
        "builder": spec.builder,
        "build_summary": spec.build_summary,
        "file_size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "parquet_rows": rows,
        "parquet_row_groups": int(parquet_file.metadata.num_row_groups),
        "year_coverage": years,
        "schema": schema,
        "checks": {
            "file_exists": True,
            "builder_exists": True,
            "build_summary_exists": True,
            "natural_key_fields_present": True,
            "expected_row_count_matches": row_count_matches,
            "expected_year_coverage_matches": years_match,
        },
    }


def build_manifest(project_root: Path) -> dict[str, Any]:
    inputs = [inspect_input(project_root, spec) for spec in INPUT_SPECS]
    return {
        "manifest_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "git": {
            "branch": git_value(project_root, "branch", "--show-current"),
            "commit": git_value(project_root, "rev-parse", "HEAD"),
        },
        "scope": "M0.3 frozen inputs for data merge and variable construction",
        "input_count": len(inputs),
        "total_file_size_bytes": sum(item["file_size_bytes"] for item in inputs),
        "validation_status": "PASS",
        "inputs": inputs,
    }


def markdown_report(manifest: dict[str, Any]) -> str:
    lines = [
        "# Data Merge Input Manifest",
        "",
        f"- Generated at UTC: `{manifest['generated_at_utc']}`",
        f"- Git branch: `{manifest['git']['branch']}`",
        f"- Git commit: `{manifest['git']['commit']}`",
        f"- Input count: `{manifest['input_count']}`",
        f"- Total frozen size: `{manifest['total_file_size_bytes']:,}` bytes",
        f"- Validation status: **{manifest['validation_status']}**",
        "",
        "## Frozen inputs",
        "",
        "| Input | Rows | Years | Size bytes | SHA256 |",
        "|---|---:|---|---:|---|",
    ]
    for item in manifest["inputs"]:
        years = item["year_coverage"]
        contiguous = years == list(range(years[0], years[-1] + 1))
        if len(years) == 1:
            year_text = str(years[0])
        elif contiguous:
            year_text = f"{years[0]}-{years[-1]} ({len(years)} years)"
        else:
            year_text = ", ".join(str(year) for year in years)
        lines.append(
            f"| `{item['input_id']}` | {item['parquet_rows']:,} | {year_text} | "
            f"{item['file_size_bytes']:,} | `{item['sha256']}` |"
        )

    lines.extend(["", "## Interfaces", ""])
    for item in manifest["inputs"]:
        lines.extend(
            [
                f"### `{item['input_id']}`",
                "",
                f"- Path: `{item['path']}`",
                f"- Source/release: {item['source']} — {item['release']}",
                f"- Natural grain: `{item['natural_grain']}`",
                f"- Natural key: `{', '.join(item['natural_key'])}`",
                f"- Builder: `{item['builder']}`",
                f"- Build summary: `{item['build_summary']}`",
                f"- Schema: `{', '.join(field['name'] + ': ' + field['type'] for field in item['schema'])}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Scope of this validation",
            "",
            "This M0.3 manifest verifies file identity, row counts, exact year coverage, schema, natural-key field presence, builder presence, and build-summary presence. It does not yet verify natural-key uniqueness, value ranges, missingness, aggregate geography rows, suppression, confidentiality, or units; those checks belong to M0.4.",
            "",
        ]
    )
    return "\n".join(lines)


def write_text(path: Path, text: str, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Freeze validated data-merge input interfaces.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("data/validation/data_merge_input_manifest.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("data/validation/data_merge_input_manifest.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_json = args.output_json if args.output_json.is_absolute() else project_root / args.output_json
    output_md = args.output_md if args.output_md.is_absolute() else project_root / args.output_md

    manifest = build_manifest(project_root)
    write_text(
        output_json,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        overwrite=args.overwrite,
    )
    write_text(output_md, markdown_report(manifest), overwrite=args.overwrite)
    print(
        json.dumps(
            {
                "validation_status": manifest["validation_status"],
                "input_count": manifest["input_count"],
                "total_file_size_bytes": manifest["total_file_size_bytes"],
                "output_json": str(output_json),
                "output_md": str(output_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
