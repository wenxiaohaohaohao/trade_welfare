from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests


SNAPSHOT_DATE = "2026-07-18"

PORTAL_DATASETS = {
    "state_country_quarterly": {
        "filename": "ied_entidad_pais_de_origen.csv",
        "url": "https://repodatos.atdt.gob.mx/s_economia/inversion_ext_directa/ied_entidad_pais_de_origen.csv",
    },
    "state_sector_quarterly": {
        "filename": "ied_entidad_sector.csv",
        "url": "https://repodatos.atdt.gob.mx/all_data/secretaria_economia/6477759b-adbb-47fb-bf49-326f9c856627/ied_entidad_sector.csv",
    },
    "state_investment_type_quarterly": {
        "filename": "ied_entidad_tipo_de_inversion.csv",
        "url": "https://www.datos.gob.mx/dataset/6477759b-adbb-47fb-bf49-326f9c856627/resource/be4aa7e1-d8b3-4663-b939-23bbb6970ac9/download/ied_entidad_tipo_de_inversion.csv",
    },
    "country_investment_type_quarterly": {
        "filename": "ied_pais_de_origen_tipo.csv",
        "url": "https://www.datos.gob.mx/dataset/6477759b-adbb-47fb-bf49-326f9c856627/resource/8e373c4f-38f3-4cd6-a260-9c3d9fccf607/download/ied_pais_de_origen_tipo.csv",
    },
    "country_sector_quarterly": {
        "filename": "ied_pais_de_origen_sector.csv",
        "url": "https://repodatos.atdt.gob.mx/all_data/secretaria_economia/6477759b-adbb-47fb-bf49-326f9c856627/ied_pais_de_origen_sector.csv",
    },
}

API_URL = "https://www.economia.gob.mx/datamexico/api/data"
API_DATASETS = {
    "national_quarterly": {
        "cube": "fdi_9_quarter",
        "drilldowns": "Quarter",
        "locale": "es",
    },
    "national_investment_type_quarterly": {
        "cube": "fdi_9_quarter_investment",
        "drilldowns": "Quarter,Investment Type",
        "locale": "es",
    },
    "parent_country_annual": {
        "cube": "fdi_10_year_country",
        "drilldowns": "Year,Country",
        "locale": "es",
    },
    "sector_annual": {
        "cube": "fdi_year_investment_industry",
        "drilldowns": "Year,Sector",
        "locale": "es",
    },
}

COUNTRY_ALIASES = {
    "china, republica popular de": "CHN",
    "corea, republica de": "KOR",
    "estados unidos de america": "USA",
    "federacion de rusia": "RUS",
    "reino unido de la gran bretana e irlanda del norte": "GBR",
    "republica checa": "CZE",
    "taiwan": "TWN",
    "venezuela, republica bolivariana de": "VEN",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(session: requests.Session, url: str, path: Path, verify: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    with session.get(url, stream=True, timeout=180, verify=verify) as response:
        response.raise_for_status()
        with partial.open("wb") as handle:
            for block in response.iter_content(1024 * 1024):
                if block:
                    handle.write(block)
    if partial.stat().st_size == 0:
        raise RuntimeError(f"Downloaded an empty file from {url}")
    partial.replace(path)


def fetch_api(
    session: requests.Session,
    spec: dict[str, str],
    path: Path,
    verify: bool,
) -> None:
    params = {
        "cube": spec["cube"],
        "drilldowns": spec["drilldowns"],
        "measures": "Investment",
        "parents": "false",
        "locale": spec["locale"],
    }
    response = session.get(API_URL, params=params, timeout=180, verify=verify)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload.get("data"), list) or not payload["data"]:
        raise RuntimeError(f"Data Mexico API returned no data for {spec['cube']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    partial.replace(path)


def normalized_key(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in text if not unicodedata.combining(char)).strip()


def api_country_map(api_path: Path) -> dict[str, str]:
    records = json.loads(api_path.read_text(encoding="utf-8"))["data"]
    result: dict[str, str] = {}
    for row in records:
        name = str(row["Country"])
        code = str(row["Country ID"]).upper()
        result[normalized_key(name)] = code
    result.update(COUNTRY_ALIASES)
    return result


def parse_industry(frame: pd.DataFrame) -> pd.DataFrame:
    extracted = frame["sector_subsector_rama"].str.extract(r"^([\d-]+)\s+(.*)$")
    frame["sector_code"] = extracted[0]
    frame["sector_name"] = extracted[1]
    levels = {2: "sector", 3: "subsector", 4: "industry_group"}
    frame["sector_level"] = frame["sector_code"].str.len().map(levels)
    frame.loc[frame["sector_code"].str.contains("-", na=False), "sector_level"] = "sector"
    if frame[["sector_code", "sector_name", "sector_level"]].isna().any().any():
        raise ValueError("An official Mexico FDI industry label could not be parsed")
    return frame.drop(columns="sector_subsector_rama")


def normalize_portal_csv(path: Path, country_map: dict[str, str]) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype="string")
    required = {"anio", "trimestre", "fecha", "millones_de_dolares"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")

    raw_value = frame["millones_de_dolares"].str.strip()
    frame["confidential_flag"] = raw_value.eq("C")
    frame["fdi_million_usd"] = pd.to_numeric(raw_value, errors="coerce")
    invalid = frame["fdi_million_usd"].isna() & ~frame["confidential_flag"]
    if invalid.any():
        tokens = sorted(raw_value[invalid].dropna().unique().tolist())
        raise ValueError(f"{path} has unknown FDI value tokens: {tokens[:10]}")
    frame["fdi_usd"] = frame["fdi_million_usd"] * 1_000_000.0
    frame["year"] = pd.to_numeric(frame["anio"], errors="raise").astype("int16")
    frame["quarter"] = pd.to_numeric(frame["trimestre"], errors="raise").astype("int8")
    frame["period"] = frame["year"].astype(str) + "Q" + frame["quarter"].astype(str)
    frame["date"] = pd.to_datetime(frame["fecha"], errors="raise")
    frame["source_file"] = path.name

    if "pais_de_origen" in frame.columns:
        frame = frame.rename(columns={"pais_de_origen": "parent_country_name"})
        country_keys = frame["parent_country_name"].map(lambda value: normalized_key(str(value)))
        frame["parent_country_iso3"] = frame["parent_country_name"].map(
            lambda value: country_map.get(normalized_key(str(value)), pd.NA)
        )
        frame["parent_country_total_flag"] = country_keys.eq("total general")
        frame["parent_country_residual_flag"] = country_keys.eq("otros paises")
    if "entidad" in frame.columns:
        frame = frame.rename(columns={"entidad": "host_state_name"})
    if "sector_subsector_rama" in frame.columns:
        frame = parse_industry(frame)
    if "tipo_de_inversion" in frame.columns:
        frame = frame.rename(columns={"tipo_de_inversion": "investment_type"})
    if "tipo" in frame.columns:
        frame = frame.rename(columns={"tipo": "investment_type"})

    drop_columns = [
        column
        for column in ["anio", "trimestre", "fecha", "millones_de_dolares", "fn_millones_de_dolares"]
        if column in frame.columns
    ]
    frame = frame.drop(columns=drop_columns)
    leading = ["year", "quarter", "period", "date"]
    dimensions = [
        column
        for column in [
            "host_state_name",
            "parent_country_iso3",
            "parent_country_name",
            "parent_country_total_flag",
            "parent_country_residual_flag",
            "sector_level",
            "sector_code",
            "sector_name",
            "investment_type",
        ]
        if column in frame.columns
    ]
    trailing = ["fdi_million_usd", "fdi_usd", "confidential_flag", "source_file"]
    frame = frame[leading + dimensions + trailing]
    key = leading[:2] + dimensions
    if frame.duplicated(key).any():
        raise ValueError(f"{path} has duplicate analytical keys")
    if not frame["quarter"].between(1, 4).all():
        raise ValueError(f"{path} has a quarter outside 1-4")
    return frame


def load_api_records(path: Path) -> pd.DataFrame:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return pd.DataFrame(payload["data"])


def normalize_api(name: str, path: Path) -> pd.DataFrame:
    frame = load_api_records(path)
    frame["fdi_million_usd"] = pd.to_numeric(frame.pop("Investment"), errors="raise")
    frame["fdi_usd"] = frame["fdi_million_usd"] * 1_000_000.0
    frame["source_file"] = path.name
    if "Quarter" in frame.columns:
        period = frame.pop("Quarter").astype("string")
        frame["year"] = period.str.slice(0, 4).astype("int16")
        frame["quarter"] = period.str.extract(r"Q([1-4])$")[0].astype("int8")
        frame["period"] = frame["year"].astype(str) + "Q" + frame["quarter"].astype(str)
        frame = frame.drop(columns=[column for column in ["Quarter ID"] if column in frame.columns])
    if "Year" in frame.columns:
        frame["year"] = pd.to_numeric(frame.pop("Year"), errors="raise").astype("int16")
    rename = {
        "Investment Type": "investment_type",
        "Investment Type ID": "investment_type_id",
        "Country": "parent_country_name",
        "Country ID": "parent_country_iso3",
        "Sector": "sector_name",
        "Sector ID": "sector_code",
    }
    frame = frame.rename(columns=rename)
    if "parent_country_iso3" in frame.columns:
        frame["parent_country_iso3"] = frame["parent_country_iso3"].astype("string").str.upper()
    if "sector_code" in frame.columns:
        frame["sector_code"] = frame["sector_code"].astype("string").str.zfill(2)
        frame["sector_level"] = "sector"
    order = [
        column
        for column in [
            "year",
            "quarter",
            "period",
            "parent_country_iso3",
            "parent_country_name",
            "sector_level",
            "sector_code",
            "sector_name",
            "investment_type_id",
            "investment_type",
            "fdi_million_usd",
            "fdi_usd",
            "source_file",
        ]
        if column in frame.columns
    ]
    frame = frame[order]
    if name.startswith("national") and set(frame["year"]) != set(range(1999, 2025)):
        raise ValueError(f"{name} does not cover every year from 1999 through 2024")
    return frame


def write_parquet(frame: pd.DataFrame, path: Path, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), path, compression="zstd")


def validate_api_outputs(outputs: dict[str, pd.DataFrame]) -> dict[str, float]:
    national = outputs["national_quarterly"]
    by_type = outputs["national_investment_type_quarterly"]
    if len(national) != 104 or national[["year", "quarter"]].duplicated().any():
        raise ValueError("National FDI quarter panel is not a complete 1999Q1-2024Q4 panel")
    type_totals = by_type.groupby(["year", "quarter"], as_index=False)["fdi_million_usd"].sum()
    compare = national.merge(type_totals, on=["year", "quarter"], suffixes=("_total", "_types"))
    max_type_gap = float(
        (compare["fdi_million_usd_total"] - compare["fdi_million_usd_types"]).abs().max()
    )
    if max_type_gap > 0.01:
        raise ValueError(f"Investment-type totals disagree with national totals by {max_type_gap}")

    annual = national.groupby("year", as_index=False)["fdi_million_usd"].sum()
    checks: dict[str, float] = {"max_quarter_type_gap_million_usd": max_type_gap}
    for name in ["parent_country_annual", "sector_annual"]:
        grouped = outputs[name].groupby("year", as_index=False)["fdi_million_usd"].sum()
        compared = annual.merge(grouped, on="year", suffixes=("_national", "_detail"))
        gap = float((compared["fdi_million_usd_national"] - compared["fdi_million_usd_detail"]).abs().max())
        checks[f"max_{name}_gap_million_usd"] = gap
        checks[f"{name}_additive_to_national"] = bool(gap <= 0.1)
    checks["national_fdi_2024_million_usd"] = float(
        national.loc[national["year"] == 2024, "fdi_million_usd"].sum()
    )
    return checks


def run(project_root: Path, overwrite: bool, insecure: bool) -> dict[str, Any]:
    raw_dir = project_root / "data" / "raw" / "mexico_fdi"
    api_dir = raw_dir / "datamexico_api"
    output_dir = project_root / "data" / "interim" / "fdi"
    session = requests.Session()
    verify = not insecure

    for spec in PORTAL_DATASETS.values():
        path = raw_dir / spec["filename"]
        if not path.exists():
            download(session, spec["url"], path, verify)
    for name, spec in API_DATASETS.items():
        path = api_dir / f"{name}.json"
        if not path.exists():
            fetch_api(session, spec, path, verify)

    country_map = api_country_map(api_dir / "parent_country_annual.json")
    portal_outputs: dict[str, pd.DataFrame] = {}
    for name, spec in PORTAL_DATASETS.items():
        frame = normalize_portal_csv(raw_dir / spec["filename"], country_map)
        portal_outputs[name] = frame
        write_parquet(frame, output_dir / f"mexico_fdi_{name}.parquet", overwrite)

    api_outputs: dict[str, pd.DataFrame] = {}
    for name in API_DATASETS:
        frame = normalize_api(name, api_dir / f"{name}.json")
        api_outputs[name] = frame
        write_parquet(frame, output_dir / f"mexico_fdi_{name}.parquet", overwrite)
    reconciliation = validate_api_outputs(api_outputs)

    sources: dict[str, Any] = {}
    for name, spec in PORTAL_DATASETS.items():
        path = raw_dir / spec["filename"]
        frame = portal_outputs[name]
        unmapped_country_names: list[str] = []
        aggregate_country_names: list[str] = []
        if "parent_country_name" in frame.columns:
            total_flag = frame["parent_country_total_flag"].fillna(False)
            residual_flag = frame["parent_country_residual_flag"].fillna(False)
            iso_missing = frame["parent_country_iso3"].isna()
            unmapped_country_names = sorted(
                frame.loc[iso_missing & ~total_flag & ~residual_flag, "parent_country_name"]
                .dropna()
                .unique()
                .tolist()
            )
            aggregate_country_names = sorted(
                frame.loc[total_flag | residual_flag, "parent_country_name"].dropna().unique().tolist()
            )
            if unmapped_country_names:
                raise ValueError(f"Unexpected unmapped parent countries in {path}: {unmapped_country_names}")
        sources[name] = {
            "url": spec["url"],
            "path": str(path.relative_to(project_root)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": len(frame),
            "year_min": int(frame["year"].min()),
            "year_max": int(frame["year"].max()),
            "confidential_cells": int(frame["confidential_flag"].sum()),
            "unmapped_country_names": unmapped_country_names,
            "aggregate_country_names": aggregate_country_names,
        }
    for name in API_DATASETS:
        path = api_dir / f"{name}.json"
        frame = api_outputs[name]
        sources[name] = {
            "url": API_URL,
            "query": API_DATASETS[name],
            "path": str(path.relative_to(project_root)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": len(frame),
            "year_min": int(frame["year"].min()),
            "year_max": int(frame["year"].max()),
        }

    output_hashes = {
        path.name: sha256(path)
        for path in sorted(output_dir.glob("mexico_fdi_*.parquet"))
    }
    summary = {
        "source": "Secretaria de Economia, datos.gob.mx and Data Mexico",
        "snapshot_date": SNAPSHOT_DATE,
        "portal_dataset_page": "https://www.datos.gob.mx/dataset/inversion_extranjera_directa",
        "tls_verification": "disabled_by_explicit_flag" if insecure else "enabled",
        "sources": sources,
        "reconciliation": reconciliation,
        "output_hashes": output_hashes,
        "validation": "passed",
        "interpretation": (
            "C denotes a confidential cell and remains null with confidential_flag=true; "
            "published detail therefore must not be treated as a complete additive total."
        ),
    }
    summary_path = output_dir / "mexico_fdi_build_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and normalize official Mexico inward FDI data.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true", help="Overwrite derived parquet outputs.")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification when an intercepting proxy prevents validation.",
    )
    args = parser.parse_args()
    summary = run(args.project_root.resolve(), args.overwrite, args.insecure)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
