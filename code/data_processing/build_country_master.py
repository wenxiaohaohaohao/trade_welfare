from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def repair_mojibake(value: str) -> str:
    if not any(marker in value for marker in ("Ã", "Â")):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def normalize_name(value: str) -> str:
    value = repair_mojibake(str(value)).strip()
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def semicolon(values: Any) -> str:
    cleaned = sorted({str(value).strip() for value in values if pd.notna(value) and str(value).strip()})
    return ";".join(cleaned)


def canonical_reference(
    project_root: Path,
    overrides: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, str], dict[str, str], dict[str, str]]:
    path = project_root / "data" / "raw" / "BACI_HS12_V202601" / "country_codes_V202601.csv"
    reference = pd.read_csv(path, dtype="string")
    reference["country_name"] = reference["country_name"].map(
        lambda value: repair_mojibake(str(value)) if pd.notna(value) else value
    )
    reference = reference.dropna(subset=["country_iso3", "country_name"]).copy()
    reference["historical_name"] = reference["country_name"].str.contains(
        r"\.\.\.|\d{4}|former|nes$",
        case=False,
        regex=True,
        na=False,
    )
    reference["name_length"] = reference["country_name"].str.len()
    preferred = (
        reference.sort_values(
            ["country_iso3", "historical_name", "name_length", "country_code"],
            kind="stable",
        )
        .drop_duplicates("country_iso3", keep="first")
        .copy()
    )
    canonical_names = dict(zip(preferred["country_iso3"], preferred["country_name"]))
    canonical_names.update(overrides.get("canonical_name_overrides", {}))

    name_candidates: dict[str, set[str]] = defaultdict(set)
    for row in reference.itertuples(index=False):
        name_candidates[normalize_name(row.country_name)].add(str(row.country_iso3))
    unique_name_lookup = {
        name: next(iter(iso3s))
        for name, iso3s in name_candidates.items()
        if len(iso3s) == 1
    }
    iso2_by_iso3 = {
        str(row.country_iso3): str(row.country_iso2)
        for row in preferred.itertuples(index=False)
        if pd.notna(row.country_iso2)
    }
    return reference, canonical_names, unique_name_lookup | {
        normalize_name(name): iso3
        for name, iso3 in overrides.get("bea_name_to_iso3", {}).items()
    }, iso2_by_iso3


def role_sets(sample: dict[str, Any]) -> dict[str, set[str]]:
    countries = sample["countries"]
    return {
        "source_core": set(countries["source_core"]),
        "source_extended": set(countries["source_extended_east_asia"]),
        "destination_core": set(countries["destination_core"]),
        "core_connector": set(countries["core_connectors"]),
        "asian_comparator": set(countries["asian_comparators"]),
        "other_candidate": set(countries["other_candidates"]),
    }


def analysis_flags(country_iso3: str | None, groups: dict[str, set[str]]) -> dict[str, bool]:
    return {
        f"is_{name}": bool(country_iso3 and country_iso3 in members)
        for name, members in groups.items()
    }


def record(
    *,
    source_name: str,
    source_country_id: str,
    source_country_name: str,
    source_roles: str,
    source_area_type: str,
    source_parent_areas: str,
    country_iso3: str | None,
    country_iso2: str | None,
    canonical_country_name: str | None,
    mapping_status: str,
    mapping_method: str,
    is_country: bool,
    is_aggregate: bool,
    is_residual: bool,
    is_proxy: bool,
    notes: str,
    groups: dict[str, set[str]],
) -> dict[str, Any]:
    output = {
        "source_name": source_name,
        "source_country_id": source_country_id,
        "source_country_name": source_country_name,
        "source_roles": source_roles,
        "source_area_type": source_area_type,
        "source_parent_areas": source_parent_areas,
        "country_iso3": country_iso3,
        "country_iso2": country_iso2,
        "canonical_country_name": canonical_country_name,
        "mapping_status": mapping_status,
        "mapping_method": mapping_method,
        "is_country": is_country,
        "is_aggregate": is_aggregate,
        "is_residual": is_residual,
        "is_proxy": is_proxy,
        "notes": notes,
    }
    output.update(analysis_flags(country_iso3, groups))
    return output


def baci_records(
    project_root: Path,
    reference: pd.DataFrame,
    canonical_names: dict[str, str],
    iso2_by_iso3: dict[str, str],
    groups: dict[str, set[str]],
) -> list[dict[str, Any]]:
    path = project_root / "data" / "interim" / "trade" / "baci_hs6_panel.parquet"
    table = pq.read_table(path, columns=["exporter_iso3", "importer_iso3"])
    observed = set(pc.unique(table.column(0)).to_pylist()) | set(pc.unique(table.column(1)).to_pylist())
    preferred = (
        reference.sort_values(["country_iso3", "historical_name", "name_length", "country_code"])
        .drop_duplicates("country_iso3", keep="first")
        .set_index("country_iso3")
    )
    rows: list[dict[str, Any]] = []
    for source_id in sorted(observed):
        source_name = (
            repair_mojibake(str(preferred.loc[source_id, "country_name"]))
            if source_id in preferred.index
            else source_id
        )
        if source_id == "S19":
            rows.append(
                record(
                    source_name="baci",
                    source_country_id="S19",
                    source_country_name=source_name,
                    source_roles="exporter;importer",
                    source_area_type="proxy_area",
                    source_parent_areas="",
                    country_iso3="TWN",
                    country_iso2=None,
                    canonical_country_name="Taiwan",
                    mapping_status="proxy",
                    mapping_method="configured_baci_proxy",
                    is_country=False,
                    is_aggregate=False,
                    is_residual=False,
                    is_proxy=True,
                    notes="Other Asia, nes is the project proxy for TWN and is not a direct Taiwan-only observation.",
                    groups=groups,
                )
            )
            continue
        rows.append(
            record(
                source_name="baci",
                source_country_id=source_id,
                source_country_name=source_name,
                source_roles="exporter;importer",
                source_area_type="country_or_area",
                source_parent_areas="",
                country_iso3=source_id,
                country_iso2=iso2_by_iso3.get(source_id),
                canonical_country_name=canonical_names.get(source_id, source_name),
                mapping_status="mapped_country",
                mapping_method="native_iso3",
                is_country=True,
                is_aggregate=False,
                is_residual=False,
                is_proxy=False,
                notes="",
                groups=groups,
            )
        )
    return rows


def census_records(
    project_root: Path,
    canonical_names: dict[str, str],
    iso2_by_iso3: dict[str, str],
    groups: dict[str, set[str]],
) -> list[dict[str, Any]]:
    path = project_root / "data" / "interim" / "trade" / "us_imports_hs6_monthly.parquet"
    frame = (
        pq.read_table(
            path,
            columns=["origin_iso3", "origin_census_code", "origin_name"],
        )
        .to_pandas()
        .drop_duplicates()
        .sort_values("origin_iso3")
    )
    return [
        record(
            source_name="us_census",
            source_country_id=str(row.origin_census_code),
            source_country_name=str(row.origin_name),
            source_roles="origin",
            source_area_type="country_or_area",
            source_parent_areas="",
            country_iso3=str(row.origin_iso3),
            country_iso2=iso2_by_iso3.get(str(row.origin_iso3)),
            canonical_country_name=canonical_names.get(str(row.origin_iso3), str(row.origin_name).title()),
            mapping_status="mapped_country",
            mapping_method="source_iso3_and_configured_census_code",
            is_country=True,
            is_aggregate=False,
            is_residual=False,
            is_proxy=False,
            notes="Configured 15-origin Census validation scope.",
            groups=groups,
        )
        for row in frame.itertuples(index=False)
    ]


def iso3_source_records(
    path: Path,
    source_name: str,
    role_columns: dict[str, str],
    canonical_names: dict[str, str],
    iso2_by_iso3: dict[str, str],
    groups: dict[str, set[str]],
) -> list[dict[str, Any]]:
    table = pq.read_table(path, columns=list(role_columns))
    roles_by_id: dict[str, set[str]] = defaultdict(set)
    for column, role in role_columns.items():
        index = table.schema.get_field_index(column)
        for source_id in pc.unique(table.column(index)).to_pylist():
            if source_id is not None:
                roles_by_id[str(source_id)].add(role)
    rows: list[dict[str, Any]] = []
    for source_id, roles in sorted(roles_by_id.items()):
        if source_id == "ROW":
            rows.append(
                record(
                    source_name=source_name,
                    source_country_id=source_id,
                    source_country_name="Rest of world",
                    source_roles=semicolon(roles),
                    source_area_type="aggregate",
                    source_parent_areas="",
                    country_iso3=None,
                    country_iso2=None,
                    canonical_country_name=None,
                    mapping_status="aggregate",
                    mapping_method="native_aggregate_code",
                    is_country=False,
                    is_aggregate=True,
                    is_residual=False,
                    is_proxy=False,
                    notes="ROW is excluded from country-level joins and retained only as an aggregate.",
                    groups=groups,
                )
            )
            continue
        rows.append(
            record(
                source_name=source_name,
                source_country_id=source_id,
                source_country_name=canonical_names.get(source_id, source_id),
                source_roles=semicolon(roles),
                source_area_type="country_or_area",
                source_parent_areas="",
                country_iso3=source_id,
                country_iso2=iso2_by_iso3.get(source_id),
                canonical_country_name=canonical_names.get(source_id, source_id),
                mapping_status="mapped_country",
                mapping_method="native_iso3",
                is_country=True,
                is_aggregate=False,
                is_residual=False,
                is_proxy=False,
                notes="",
                groups=groups,
            )
        )
    return rows


def bea_records(
    path: Path,
    source_name: str,
    country_column: str,
    name_lookup: dict[str, str],
    canonical_names: dict[str, str],
    iso2_by_iso3: dict[str, str],
    force_aggregates: set[str],
    groups: dict[str, set[str]],
) -> list[dict[str, Any]]:
    frame = (
        pq.read_table(
            path,
            columns=[country_column, "bea_area_type", "bea_parent_area"],
        )
        .to_pandas()
        .drop_duplicates()
    )
    rows: list[dict[str, Any]] = []
    for source_id, group in frame.groupby(country_column, dropna=False, sort=True):
        label = str(source_id)
        area_types = set(group["bea_area_type"].dropna().astype(str))
        parent_areas = semicolon(group["bea_parent_area"])
        forced_aggregate = label in force_aggregates
        source_aggregate = area_types == {"aggregate"}
        mixed_area_type = len(area_types) > 1
        if forced_aggregate or source_aggregate:
            rows.append(
                record(
                    source_name=source_name,
                    source_country_id=label,
                    source_country_name=label,
                    source_roles="affiliate_host" if source_name == "bea_mne" else "investment_counterparty",
                    source_area_type=semicolon(area_types),
                    source_parent_areas=parent_areas,
                    country_iso3=None,
                    country_iso2=None,
                    canonical_country_name=None,
                    mapping_status="aggregate",
                    mapping_method="forced_aggregate_override" if forced_aggregate else "source_area_type",
                    is_country=False,
                    is_aggregate=True,
                    is_residual=False,
                    is_proxy=False,
                    notes=(
                        "Source country_or_area label overridden because this is a regional/addendum aggregate."
                        if forced_aggregate
                        else "BEA aggregate geography row; exclude from country-level joins."
                    ),
                    groups=groups,
                )
            )
            continue

        mapped_iso3 = name_lookup.get(normalize_name(label))
        status = "mapped_country" if mapped_iso3 else "unresolved"
        rows.append(
            record(
                source_name=source_name,
                source_country_id=label,
                source_country_name=label,
                source_roles="affiliate_host" if source_name == "bea_mne" else "investment_counterparty",
                source_area_type=semicolon(area_types),
                source_parent_areas=parent_areas,
                country_iso3=mapped_iso3,
                country_iso2=iso2_by_iso3.get(mapped_iso3) if mapped_iso3 else None,
                canonical_country_name=canonical_names.get(mapped_iso3, label) if mapped_iso3 else None,
                mapping_status=status,
                mapping_method="name_lookup_or_override" if mapped_iso3 else "unresolved",
                is_country=bool(mapped_iso3),
                is_aggregate=False,
                is_residual=False,
                is_proxy=False,
                notes="Multiple source area types observed." if mixed_area_type else "",
                groups=groups,
            )
        )
    return rows


def mexico_records(
    project_root: Path,
    canonical_names: dict[str, str],
    iso2_by_iso3: dict[str, str],
    groups: dict[str, set[str]],
) -> list[dict[str, Any]]:
    path = project_root / "data" / "interim" / "fdi" / "mexico_fdi_country_sector_quarterly.parquet"
    frame = (
        pq.read_table(
            path,
            columns=[
                "parent_country_iso3",
                "parent_country_name",
                "parent_country_total_flag",
                "parent_country_residual_flag",
            ],
        )
        .to_pandas()
        .drop_duplicates()
        .sort_values("parent_country_name")
    )
    rows: list[dict[str, Any]] = []
    for row in frame.itertuples(index=False):
        label = str(row.parent_country_name)
        if bool(row.parent_country_total_flag):
            rows.append(
                record(
                    source_name="mexico_fdi",
                    source_country_id=label,
                    source_country_name=label,
                    source_roles="parent_country",
                    source_area_type="aggregate",
                    source_parent_areas="",
                    country_iso3=None,
                    country_iso2=None,
                    canonical_country_name=None,
                    mapping_status="aggregate",
                    mapping_method="source_total_flag",
                    is_country=False,
                    is_aggregate=True,
                    is_residual=False,
                    is_proxy=False,
                    notes="Mexico official total row; exclude from country-level joins.",
                    groups=groups,
                )
            )
        elif bool(row.parent_country_residual_flag):
            rows.append(
                record(
                    source_name="mexico_fdi",
                    source_country_id=label,
                    source_country_name=label,
                    source_roles="parent_country",
                    source_area_type="residual",
                    source_parent_areas="",
                    country_iso3=None,
                    country_iso2=None,
                    canonical_country_name=None,
                    mapping_status="residual",
                    mapping_method="source_residual_flag",
                    is_country=False,
                    is_aggregate=False,
                    is_residual=True,
                    is_proxy=False,
                    notes="Otros paises has no ISO3 and must not be joined or summed as an ordinary country.",
                    groups=groups,
                )
            )
        else:
            iso3 = str(row.parent_country_iso3)
            rows.append(
                record(
                    source_name="mexico_fdi",
                    source_country_id=label,
                    source_country_name=label,
                    source_roles="parent_country",
                    source_area_type="country_or_area",
                    source_parent_areas="",
                    country_iso3=iso3,
                    country_iso2=iso2_by_iso3.get(iso3),
                    canonical_country_name=canonical_names.get(iso3, label),
                    mapping_status="mapped_country",
                    mapping_method="source_iso3",
                    is_country=True,
                    is_aggregate=False,
                    is_residual=False,
                    is_proxy=False,
                    notes="",
                    groups=groups,
                )
            )
    return rows


def build_country_master(project_root: Path) -> pd.DataFrame:
    overrides = load_yaml(project_root / "configs" / "country_concordance_overrides.yaml")
    sample = load_yaml(project_root / "configs" / "analysis_sample_v1.yaml")
    groups = role_sets(sample)
    reference, canonical_names, name_lookup, iso2_by_iso3 = canonical_reference(
        project_root,
        overrides,
    )
    force_aggregates = set(overrides["bea_force_aggregate_labels"])

    rows: list[dict[str, Any]] = []
    rows.extend(baci_records(project_root, reference, canonical_names, iso2_by_iso3, groups))
    rows.extend(census_records(project_root, canonical_names, iso2_by_iso3, groups))
    rows.extend(
        iso3_source_records(
            project_root / "data" / "interim" / "policy" / "section301_hs6_exposure.parquet",
            "section301",
            {"origin_iso3": "origin", "destination_iso3": "destination"},
            canonical_names,
            iso2_by_iso3,
            groups,
        )
    )
    rows.extend(
        iso3_source_records(
            project_root / "data" / "interim" / "production" / "oecd_icio_output_va_fd.parquet",
            "oecd_icio",
            {"country_iso3": "country"},
            canonical_names,
            iso2_by_iso3,
            groups,
        )
    )
    rows.extend(
        iso3_source_records(
            project_root / "data" / "interim" / "mne" / "oecd_amne_affiliate_activity.parquet",
            "oecd_amne",
            {"host_country_iso3": "host", "parent_country_iso3": "parent"},
            canonical_names,
            iso2_by_iso3,
            groups,
        )
    )
    rows.extend(
        bea_records(
            project_root / "data" / "interim" / "mne" / "bea_us_mne_affiliate_country_industry.parquet",
            "bea_mne",
            "affiliate_country",
            name_lookup,
            canonical_names,
            iso2_by_iso3,
            force_aggregates,
            groups,
        )
    )
    rows.extend(
        bea_records(
            project_root / "data" / "interim" / "fdi" / "bea_direct_investment_country_industry.parquet",
            "bea_fdi",
            "country",
            name_lookup,
            canonical_names,
            iso2_by_iso3,
            force_aggregates,
            groups,
        )
    )
    rows.extend(mexico_records(project_root, canonical_names, iso2_by_iso3, groups))
    frame = pd.DataFrame(rows)
    string_columns = [
        "source_name",
        "source_country_id",
        "source_country_name",
        "source_roles",
        "source_area_type",
        "source_parent_areas",
        "country_iso3",
        "country_iso2",
        "canonical_country_name",
        "mapping_status",
        "mapping_method",
        "notes",
    ]
    for column in string_columns:
        frame[column] = frame[column].astype("string")
    bool_columns = [column for column in frame if column.startswith("is_")]
    for column in bool_columns:
        frame[column] = frame[column].astype("bool")
    return frame.sort_values(["source_name", "source_country_id"], kind="stable").reset_index(drop=True)


def validate_country_master(frame: pd.DataFrame, sample: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    key_columns = ["source_name", "source_country_id"]
    duplicate_rows = int(frame.duplicated(key_columns).sum())
    if duplicate_rows:
        failures.append(f"country master has {duplicate_rows} duplicate source keys")
    unresolved = frame.loc[frame["mapping_status"] == "unresolved", key_columns].to_dict(orient="records")
    if unresolved:
        failures.append(f"country master has {len(unresolved)} unresolved source identifiers")
    invalid_iso3 = frame.loc[
        frame["country_iso3"].notna()
        & ~frame["country_iso3"].str.fullmatch(r"[A-Z0-9]{3}", na=False),
        key_columns + ["country_iso3"],
    ].to_dict(orient="records")
    if invalid_iso3:
        failures.append(f"country master has {len(invalid_iso3)} invalid ISO3-like codes")
    aggregate_with_iso3 = int((frame["is_aggregate"] & frame["country_iso3"].notna()).sum())
    residual_with_iso3 = int((frame["is_residual"] & frame["country_iso3"].notna()).sum())
    country_without_iso3 = int((frame["is_country"] & frame["country_iso3"].isna()).sum())
    classification_columns = ["is_country", "is_aggregate", "is_residual", "is_proxy"]
    invalid_classification = int((frame[classification_columns].sum(axis=1) != 1).sum())
    if aggregate_with_iso3:
        failures.append(f"{aggregate_with_iso3} aggregate rows retain country_iso3")
    if residual_with_iso3:
        failures.append(f"{residual_with_iso3} residual rows retain country_iso3")
    if country_without_iso3:
        failures.append(f"{country_without_iso3} country rows lack country_iso3")
    if invalid_classification:
        failures.append(
            f"{invalid_classification} rows do not have exactly one geography classification"
        )
    proxy = frame[(frame["source_name"] == "baci") & (frame["source_country_id"] == "S19")]
    proxy_ok = (
        len(proxy) == 1
        and proxy.iloc[0]["country_iso3"] == "TWN"
        and bool(proxy.iloc[0]["is_proxy"])
        and proxy.iloc[0]["mapping_status"] == "proxy"
    )
    if not proxy_ok:
        failures.append("BACI S19 proxy is not uniquely mapped to TWN with proxy status")

    force_labels = {
        "European Union 2",
        "South and Central America",
        "United Kingdom Islands, Caribbean",
        "United Kingdom Islands, Caribbean 1",
    }
    forced_rows = frame[
        frame["source_name"].isin(["bea_mne", "bea_fdi"])
        & frame["source_country_id"].isin(force_labels)
    ]
    forced_aggregate_ok = (
        set(forced_rows["source_country_id"]) == force_labels
        and bool(forced_rows["is_aggregate"].all())
        and bool(forced_rows["country_iso3"].isna().all())
    )
    if not forced_aggregate_ok:
        failures.append("one or more forced BEA regional labels are not marked aggregate")

    status_counts = {
        source: group["mapping_status"].value_counts(dropna=False).sort_index().to_dict()
        for source, group in frame.groupby("source_name", sort=True)
    }
    analysis_country_set = set(sample["countries"]["core_connectors"])
    analysis_country_set.update(sample["countries"]["asian_comparators"])
    analysis_country_set.update(sample["countries"]["other_candidates"])
    mapped_analysis_countries = set(frame.loc[frame["country_iso3"].isin(analysis_country_set), "country_iso3"])
    missing_analysis_countries = sorted(analysis_country_set - mapped_analysis_countries)
    if missing_analysis_countries:
        failures.append(f"analysis countries missing from country master: {missing_analysis_countries}")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "row_count": len(frame),
        "source_count": int(frame["source_name"].nunique()),
        "duplicate_source_keys": duplicate_rows,
        "unresolved_count": len(unresolved),
        "unresolved_rows": unresolved,
        "invalid_iso3_count": len(invalid_iso3),
        "country_without_iso3_count": country_without_iso3,
        "invalid_classification_count": invalid_classification,
        "aggregate_rows": int(frame["is_aggregate"].sum()),
        "residual_rows": int(frame["is_residual"].sum()),
        "proxy_rows": int(frame["is_proxy"].sum()),
        "mapped_country_rows": int(frame["is_country"].sum()),
        "status_counts_by_source": status_counts,
        "analysis_country_count": len(analysis_country_set),
        "analysis_countries_all_present": not missing_analysis_countries,
        "missing_analysis_countries": missing_analysis_countries,
        "baci_s19_proxy_ok": proxy_ok,
        "forced_bea_aggregates_ok": forced_aggregate_ok,
    }


def markdown_report(
    validation: dict[str, Any],
    output_path: str,
    output_sha256: str,
) -> str:
    lines = [
        "# Country Master Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Country master: `{output_path}`",
        f"- SHA256: `{output_sha256}`",
        f"- Rows: `{validation['row_count']}`",
        f"- Sources: `{validation['source_count']}`",
        f"- Duplicate source keys: `{validation['duplicate_source_keys']}`",
        f"- Unresolved identifiers: `{validation['unresolved_count']}`",
        f"- Invalid geography classifications: `{validation['invalid_classification_count']}`",
        f"- Aggregate rows: `{validation['aggregate_rows']}`",
        f"- Residual rows: `{validation['residual_rows']}`",
        f"- Proxy rows: `{validation['proxy_rows']}`",
        f"- Validation status: **{validation['validation_status']}**",
        "",
        "## Status by source",
        "",
        "| Source | Mapping statuses |",
        "|---|---|",
    ]
    for source, counts in validation["status_counts_by_source"].items():
        lines.append(f"| `{source}` | `{json.dumps(counts, ensure_ascii=False)}` |")
    lines.extend(
        [
            "",
            "## Required checks",
            "",
            f"- All analysis countries present: `{'yes' if validation['analysis_countries_all_present'] else 'no'}`",
            f"- BACI S19 explicitly marked as TWN proxy: `{'yes' if validation['baci_s19_proxy_ok'] else 'no'}`",
            f"- Forced BEA regional labels marked aggregate: `{'yes' if validation['forced_bea_aggregates_ok'] else 'no'}`",
            "",
            "## Interpretation",
            "",
            "The country master maps only genuine country observations to country_iso3. Aggregate, residual, and proxy records remain explicit. BACI S19 maps to TWN only as a documented project proxy. BEA regional/addendum labels and Mexico Otros paises cannot enter ordinary country joins.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    frame: pd.DataFrame,
    output_path: Path,
    validation_json: Path,
    validation_md: Path,
    project_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    for path in (output_path, validation_json, validation_md):
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, output_path, compression="zstd")
    output_hash = sha256(output_path)
    sample = load_yaml(project_root / "configs" / "analysis_sample_v1.yaml")
    validation = validate_country_master(frame, sample)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": output_hash,
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in table.schema
            ],
        }
    )
    validation_json.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validation_md.write_text(
        markdown_report(validation, validation["output_path"], output_hash),
        encoding="utf-8",
        newline="\n",
    )
    return validation


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the cross-source country master.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/concordances/country_crosswalk.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/country_crosswalk_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/country_crosswalk_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else project_root / args.output
    validation_json = (
        args.validation_json
        if args.validation_json.is_absolute()
        else project_root / args.validation_json
    )
    validation_md = (
        args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    )
    frame = build_country_master(project_root)
    validation = write_outputs(
        frame,
        output,
        validation_json,
        validation_md,
        project_root,
        args.overwrite,
    )
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "row_count": validation["row_count"],
                "unresolved_count": validation["unresolved_count"],
                "output": str(output),
                "validation_json": str(validation_json),
                "validation_md": str(validation_md),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
