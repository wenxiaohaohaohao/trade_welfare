from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def column_index(cell_reference: str) -> int:
    letters = re.match(r"[A-Z]+", cell_reference).group(0)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value - 1


def workbook_sheets(archive: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        element.attrib["Id"]: element.attrib["Target"]
        for element in relationships.findall(f"{{{PKG_REL_NS}}}Relationship")
    }
    output: dict[str, str] = {}
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        rel_id = sheet.attrib[f"{{{DOC_REL_NS}}}id"]
        target = rel_targets[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = f"xl/{target}"
        output[sheet.attrib["name"]] = target
    return output


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def read_simple_xlsx_sheet(path: Path, name_contains: str) -> list[list[str | None]]:
    with zipfile.ZipFile(path) as archive:
        sheets = workbook_sheets(archive)
        matches = [name for name in sheets if name_contains.casefold() in name.casefold()]
        if len(matches) != 1:
            raise ValueError(f"Expected one sheet containing {name_contains!r} in {path}, found {matches}")
        strings = shared_strings(archive)
        root = ET.fromstring(archive.read(sheets[matches[0]]))
        rows: list[list[str | None]] = []
        for row in root.findall(f".//{{{MAIN_NS}}}row"):
            cells: dict[int, str | None] = {}
            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                index = column_index(cell.attrib["r"])
                cell_type = cell.attrib.get("t")
                value_node = cell.find(f"{{{MAIN_NS}}}v")
                if cell_type == "inlineStr":
                    text_nodes = cell.findall(f".//{{{MAIN_NS}}}t")
                    value = "".join(node.text or "" for node in text_nodes)
                elif value_node is None:
                    value = None
                elif cell_type == "s":
                    value = strings[int(value_node.text)]
                else:
                    value = value_node.text
                cells[index] = value
            if cells:
                rows.append([cells.get(index) for index in range(max(cells) + 1)])
        return rows


def normalize_hs6(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    text = re.sub(r"\D", "", text)
    if not text:
        raise ValueError(f"Empty HS6 value from {value!r}")
    return text.zfill(6)


def read_unsd_workbook(path: Path, source_revision: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    conversion_rows = read_simple_xlsx_sheet(path, "conversion")
    conversion_header = [str(value or "").strip() for value in conversion_rows[0]]
    if len(conversion_header) < 2 or "from" not in conversion_header[0].casefold():
        raise ValueError(f"Unexpected conversion header in {path}: {conversion_header}")
    conversion = pd.DataFrame(
        [
            {
                "source_revision": source_revision,
                "source_hs6": normalize_hs6(row[0]),
                "target_revision": "HS2012",
                "target_hs6": normalize_hs6(row[1]),
                "mapping_method": "official_unsd_conversion",
                "mapping_weight": 1.0,
            }
            for row in conversion_rows[1:]
            if len(row) >= 2 and row[0] is not None and row[1] is not None
        ]
    )

    correlation_rows = read_simple_xlsx_sheet(path, "correlation")
    header_index = next(
        index
        for index, row in enumerate(correlation_rows)
        if any(str(value or "").strip().casefold() == "relationship" for value in row)
    )
    header = [str(value or "").strip() for value in correlation_rows[header_index]]
    relationship_index = next(
        index for index, value in enumerate(header) if value.casefold() == "relationship"
    )
    revision_digits = source_revision.replace("HS", "")
    source_index = next(
        index for index, value in enumerate(header) if revision_digits in value.replace(" ", "")
    )
    target_index = next(
        index for index, value in enumerate(header) if "2012" in value.replace(" ", "")
    )
    correlation_records: list[dict[str, Any]] = []
    for row in correlation_rows[header_index + 1 :]:
        if len(row) <= max(source_index, target_index, relationship_index):
            continue
        if row[source_index] is None or row[target_index] is None:
            continue
        between = row[source_index + 1 : target_index]
        correlation_records.append(
            {
                "source_revision": source_revision,
                "source_hs6": normalize_hs6(row[source_index]),
                "target_revision": "HS2012",
                "target_hs6": normalize_hs6(row[target_index]),
                "relationship": str(row[relationship_index]).strip(),
                "partial_scope_flag": any(str(value or "").strip().casefold() == "ex" for value in between),
                "mapping_method": "official_unsd_correlation",
            }
        )
    correlation = pd.DataFrame(correlation_records)
    return conversion, correlation


def product_reference(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype="string")
    frame["code"] = frame["code"].map(normalize_hs6).astype("string")
    return frame.drop_duplicates("code")


def build_bridges(project_root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    hs12 = product_reference(project_root / "data/raw/BACI_HS12_V202601/product_codes_HS12_V202601.csv")
    hs17 = product_reference(project_root / "data/raw/BACI_HS17_V202601/product_codes_HS17_V202601.csv")
    hs12_names = dict(zip(hs12["code"], hs12["description"]))
    hs17_names = dict(zip(hs17["code"], hs17["description"]))

    official_conversions: list[pd.DataFrame] = []
    official_correlations: list[pd.DataFrame] = []
    for revision, source_key in (("HS2017", "unsd_hs2017_to_hs2012"), ("HS2022", "unsd_hs2022_to_hs2012")):
        path = project_root / config["official_sources"][source_key]["path"]
        conversion, correlation = read_unsd_workbook(path, revision)
        official_conversions.append(conversion)
        official_correlations.append(correlation)

    official_hs2012_codes = set(hs12["code"])
    for frame in official_conversions:
        official_hs2012_codes.update(frame["target_hs6"])
    identity_codes = pd.Series(sorted(official_hs2012_codes), dtype="string")
    identity_conversion = pd.DataFrame(
        {
            "source_revision": "HS2012",
            "source_hs6": identity_codes,
            "target_revision": "HS2012",
            "target_hs6": identity_codes,
            "mapping_method": "identity",
            "mapping_weight": 1.0,
        }
    )
    identity_correlation = identity_conversion.drop(columns="mapping_weight").copy()
    identity_correlation["relationship"] = "1:1"
    identity_correlation["partial_scope_flag"] = False

    conversions = [identity_conversion, *official_conversions]
    correlations = [identity_correlation, *official_correlations]
    for revision, overrides in config.get("source_code_overrides", {}).items():
        for raw_source_hs6, details in overrides.items():
            source_hs6 = normalize_hs6(raw_source_hs6)
            target_hs6 = normalize_hs6(details["target_hs2012"])
            conversions.append(
                pd.DataFrame(
                    [
                        {
                            "source_revision": revision,
                            "source_hs6": source_hs6,
                            "target_revision": "HS2012",
                            "target_hs6": target_hs6,
                            "mapping_method": details["method"],
                            "mapping_weight": 1.0,
                        }
                    ]
                )
            )
            correlations.append(
                pd.DataFrame(
                    [
                        {
                            "source_revision": revision,
                            "source_hs6": source_hs6,
                            "target_revision": "HS2012",
                            "target_hs6": target_hs6,
                            "relationship": "project_override",
                            "partial_scope_flag": False,
                            "mapping_method": details["method"],
                        }
                    ]
                )
            )

    conversion = pd.concat(conversions, ignore_index=True)
    correlation = pd.concat(correlations, ignore_index=True)
    analysis_overrides = {
        normalize_hs6(source): normalize_hs6(target)
        for source, target in config.get("analysis_hs2012_overrides", {}).items()
        if str(source) != "note"
    }
    for frame in (conversion, correlation):
        frame["analysis_revision"] = "HS2012_CEPII"
        frame["analysis_hs6"] = frame["target_hs6"].map(
            lambda code: analysis_overrides.get(code, code)
        )
        frame["analysis_mapping_method"] = frame["target_hs6"].map(
            lambda code: "configured_cepii_many_to_one_collapse"
            if code in analysis_overrides
            else "direct_hs2012_code"
        )
    conversion_pairs = set(zip(conversion["source_revision"], conversion["source_hs6"], conversion["target_hs6"]))
    correlation["is_official_conversion_pair"] = [
        (revision, source, target) in conversion_pairs
        for revision, source, target in zip(
            correlation["source_revision"], correlation["source_hs6"], correlation["target_hs6"]
        )
    ]
    correlation["target_count_per_source"] = correlation.groupby(
        ["source_revision", "source_hs6"]
    )["target_hs6"].transform("nunique")
    correlation["source_count_per_target"] = correlation.groupby(
        ["source_revision", "target_hs6"]
    )["source_hs6"].transform("nunique")
    correlation["mapping_weight"] = correlation["target_count_per_source"].map(
        lambda count: 1.0 if count == 1 else None
    )
    correlation["weight_status"] = correlation["target_count_per_source"].map(
        lambda count: "single_target_weight_1" if count == 1 else "requires_value_based_weight"
    )

    for frame in (conversion, correlation):
        frame["source_description"] = frame.apply(
            lambda row: (
                hs12_names.get(row["source_hs6"])
                if row["source_revision"] == "HS2012"
                else hs17_names.get(row["source_hs6"])
                if row["source_revision"] == "HS2017"
                else None
            ),
            axis=1,
        )
        frame["target_description"] = frame["target_hs6"].map(hs12_names)
        frame["analysis_description"] = frame["analysis_hs6"].map(hs12_names)
        frame["bridge_version"] = config["version"]

    for frame in (conversion, correlation):
        for column in [column for column in frame if column not in {"mapping_weight", "partial_scope_flag", "is_official_conversion_pair", "target_count_per_source", "source_count_per_target"}]:
            frame[column] = frame[column].astype("string")
    correlation["partial_scope_flag"] = correlation["partial_scope_flag"].astype("bool")
    correlation["is_official_conversion_pair"] = correlation["is_official_conversion_pair"].astype("bool")
    correlation["target_count_per_source"] = correlation["target_count_per_source"].astype("int16")
    correlation["source_count_per_target"] = correlation["source_count_per_target"].astype("int16")
    return (
        conversion.sort_values(["source_revision", "source_hs6"]).reset_index(drop=True),
        correlation.sort_values(["source_revision", "source_hs6", "target_hs6"]).reset_index(drop=True),
    )


def build_census_year_crosswalk(
    project_root: Path,
    config: dict[str, Any],
    conversion: pd.DataFrame,
) -> pd.DataFrame:
    path = project_root / "data/interim/trade/us_imports_hs6_monthly.parquet"
    census = pq.read_table(path, columns=["year", "hs6", "import_value_usd"]).to_pandas()
    census["source_hs6"] = census["hs6"].astype("string").str.zfill(6)
    annual_codes = (
        census.groupby(["year", "source_hs6"], as_index=False)
        .agg(source_row_count=("hs6", "size"), source_import_value_usd=("import_value_usd", "sum"))
    )
    year_bands = config["source_revision_rules"]["us_census_hs6_monthly"]["year_bands"]
    revision_by_year = {
        year: band["revision"]
        for band in year_bands
        for year in range(int(band["start"]), int(band["end"]) + 1)
    }
    annual_codes["source_revision"] = annual_codes["year"].map(revision_by_year).astype("string")
    if annual_codes["source_revision"].isna().any():
        missing_years = sorted(annual_codes.loc[annual_codes["source_revision"].isna(), "year"].unique())
        raise ValueError(f"Census years lack HS revision rules: {missing_years}")

    bridge_columns = [
        "source_revision",
        "source_hs6",
        "target_revision",
        "target_hs6",
        "analysis_revision",
        "analysis_hs6",
        "mapping_method",
        "analysis_mapping_method",
        "mapping_weight",
    ]
    output = annual_codes.merge(conversion[bridge_columns], on=["source_revision", "source_hs6"], how="left", validate="many_to_one")
    output["mapping_status"] = output["analysis_hs6"].notna().map(
        {True: "mapped_assigned_revision", False: "pending"}
    )

    fallback = conversion[conversion["source_revision"] == "HS2012"].set_index("source_hs6")
    fallback_rule = config["census_unmatched_rules"]
    excluded_prefixes = tuple(str(value) for value in fallback_rule["excluded_prefixes"])
    pending_indices = output.index[output["mapping_status"] == "pending"]
    for index in pending_indices:
        code = output.at[index, "source_hs6"]
        if code.startswith(excluded_prefixes):
            output.at[index, "mapping_status"] = "excluded_national_special_code"
            output.at[index, "mapping_method"] = "configured_national_special_exclusion"
        elif bool(fallback_rule["exact_hs2012_fallback"]) and code in fallback.index:
            row = fallback.loc[code]
            for column in ["target_revision", "target_hs6", "analysis_revision", "analysis_hs6", "analysis_mapping_method", "mapping_weight"]:
                output.at[index, column] = row[column]
            output.at[index, "mapping_status"] = "mapped_exact_hs2012_fallback"
            output.at[index, "mapping_method"] = "exact_hs2012_identity_fallback"
        else:
            output.at[index, "mapping_status"] = "unresolved_nonstandard_code"
            output.at[index, "mapping_method"] = "unresolved_no_forced_match"

    output["is_analysis_eligible"] = output["analysis_hs6"].notna()
    output["hts10_rule"] = "retain_year_specific_hts10; harmonize_only_first_six_digits"
    output["bridge_version"] = config["version"]
    string_columns = [
        "source_hs6",
        "source_revision",
        "target_revision",
        "target_hs6",
        "analysis_revision",
        "analysis_hs6",
        "mapping_method",
        "analysis_mapping_method",
        "mapping_status",
        "hts10_rule",
        "bridge_version",
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["year"] = output["year"].astype("int16")
    output["source_row_count"] = output["source_row_count"].astype("int32")
    output["is_analysis_eligible"] = output["is_analysis_eligible"].astype("bool")
    return output.sort_values(["year", "source_hs6"]).reset_index(drop=True)


def coverage_record(
    input_id: str,
    revision: str,
    codes: pd.Series,
    values: pd.Series,
    mapped_codes: set[str],
) -> dict[str, Any]:
    normalized = codes.astype("string").str.zfill(6)
    mapped = normalized.isin(mapped_codes)
    unique_codes = set(normalized.dropna())
    unmapped_codes = sorted(unique_codes - mapped_codes)
    total_value = float(values.sum())
    mapped_value = float(values[mapped].sum())
    top_unmapped = (
        pd.DataFrame({"hs6": normalized[~mapped], "value": values[~mapped]})
        .groupby("hs6", as_index=False)["value"]
        .sum()
        .sort_values("value", ascending=False)
        .head(20)
        .to_dict(orient="records")
    )
    return {
        "input_id": input_id,
        "source_revision": revision,
        "row_count": len(codes),
        "unique_code_count": len(unique_codes),
        "mapped_unique_code_count": len(unique_codes & mapped_codes),
        "unmapped_unique_code_count": len(unmapped_codes),
        "code_coverage_rate": len(unique_codes & mapped_codes) / len(unique_codes) if unique_codes else None,
        "row_coverage_rate": float(mapped.mean()) if len(mapped) else None,
        "total_value": total_value,
        "mapped_value": mapped_value,
        "value_coverage_rate": mapped_value / total_value if total_value else None,
        "unmapped_codes": unmapped_codes,
        "top_unmapped_by_value": top_unmapped,
    }


def validate_bridges(
    project_root: Path,
    config: dict[str, Any],
    conversion: pd.DataFrame,
    correlation: pd.DataFrame,
    census_crosswalk: pd.DataFrame,
) -> dict[str, Any]:
    failures: list[str] = []
    source_hash_checks: dict[str, bool] = {}
    for source_name, source in config["official_sources"].items():
        path = project_root / source["path"]
        source_hash_checks[source_name] = path.exists() and sha256(path) == source["sha256"]
    if not all(source_hash_checks.values()):
        failures.append("one or more official HS source files fail their configured SHA256 check")

    conversion_duplicates = int(conversion.duplicated(["source_revision", "source_hs6"]).sum())
    correlation_duplicates = int(
        correlation.duplicated(["source_revision", "source_hs6", "target_hs6"]).sum()
    )
    if conversion_duplicates:
        failures.append(f"conversion bridge has {conversion_duplicates} duplicate source keys")
    if correlation_duplicates:
        failures.append(f"correlation bridge has {correlation_duplicates} duplicate source-target keys")
    invalid_codes = int(
        (~conversion["source_hs6"].str.fullmatch(r"\d{6}")).sum()
        + (~conversion["target_hs6"].str.fullmatch(r"\d{6}")).sum()
        + (~correlation["source_hs6"].str.fullmatch(r"\d{6}")).sum()
        + (~correlation["target_hs6"].str.fullmatch(r"\d{6}")).sum()
    )
    if invalid_codes:
        failures.append(f"bridge has {invalid_codes} invalid six-digit codes")
    conversion_weight_ok = bool((conversion["mapping_weight"] == 1.0).all())
    if not conversion_weight_ok:
        failures.append("canonical conversion bridge contains a weight other than 1")
    conversion_pair_missing = int((~correlation["is_official_conversion_pair"]).groupby(
        [correlation["source_revision"], correlation["source_hs6"]]
    ).all().sum())
    if conversion_pair_missing:
        failures.append(f"{conversion_pair_missing} source codes lack their official conversion pair in full correlation")

    expected_relationship_counts = {
        "HS2017": {"1:1": 4744, "1:n": 44, "n:1": 578, "n:n": 775},
        "HS2022": {"1:1": 3714, "1:n": 70, "n:1": 1718, "n:n": 10875},
    }
    official_correlation = correlation[
        correlation["mapping_method"] == "official_unsd_correlation"
    ]
    actual_relationship_counts = {
        revision: group["relationship"].value_counts().sort_index().to_dict()
        for revision, group in official_correlation.groupby("source_revision", sort=True)
    }
    relationship_counts_ok = actual_relationship_counts == expected_relationship_counts
    if not relationship_counts_ok:
        failures.append("UNSD correlation relationship counts differ from the inspected official workbooks")

    hs17_pairs = set(
        zip(
            correlation.loc[correlation["source_revision"] == "HS2017", "source_hs6"],
            correlation.loc[correlation["source_revision"] == "HS2017", "target_hs6"],
        )
    )
    corrigendum_pairs = {
        ("440139", "440139"),
        ("440140", "440139"),
        ("847330", "847330"),
        ("847340", "847310"),
        ("847340", "847340"),
        ("847340", "847350"),
        ("847350", "847350"),
    }
    corrigenda_ok = corrigendum_pairs.issubset(hs17_pairs) and ("440132", "440139") not in hs17_pairs
    if not corrigenda_ok:
        failures.append("HS2017-HS2012 correlation does not reflect the checked WCO corrigenda")

    mapped_by_revision = {
        revision: set(group["source_hs6"])
        for revision, group in conversion.groupby("source_revision", sort=True)
    }
    hs12_reference = product_reference(
        project_root / "data/raw/BACI_HS12_V202601/product_codes_HS12_V202601.csv"
    )
    hs12_reference_coverage = set(hs12_reference["code"]).issubset(mapped_by_revision["HS2012"])
    if not hs12_reference_coverage:
        failures.append("HS2012 BACI product reference is not fully covered by identity mapping")

    coverage: list[dict[str, Any]] = []
    hs17_baci = pq.read_table(
        project_root / "data/interim/trade/baci_hs17_us_imports_2017.parquet",
        columns=["hs6", "baci_total_us_import_value_2017"],
    ).to_pandas()
    coverage.append(
        coverage_record(
            "baci_hs17_us_imports_2017",
            "HS2017",
            hs17_baci["hs6"],
            hs17_baci["baci_total_us_import_value_2017"],
            mapped_by_revision["HS2017"],
        )
    )
    section301 = pq.read_table(
        project_root / "data/interim/policy/section301_hs6_exposure.parquet",
        columns=["hs6", "year", "tariff_exposure"],
    ).to_pandas()
    coverage.append(
        coverage_record(
            "section301_hs6_exposure",
            "HS2017",
            section301["hs6"],
            section301["tariff_exposure"],
            mapped_by_revision["HS2017"],
        )
    )
    for start, end, revision in ((2014, 2016, "HS2012"), (2017, 2021, "HS2017"), (2022, 2024, "HS2022")):
        subset = census_crosswalk[census_crosswalk["year"].between(start, end)].copy()
        mapped = subset["is_analysis_eligible"]
        excluded = subset["mapping_status"] == "excluded_national_special_code"
        total_value = float(subset["source_import_value_usd"].sum())
        mapped_value = float(subset.loc[mapped, "source_import_value_usd"].sum())
        excluded_value = float(subset.loc[excluded, "source_import_value_usd"].sum())
        eligible_denominator = total_value - excluded_value
        unmapped = subset[~mapped & ~excluded]
        coverage.append(
            {
                "input_id": f"us_census_hs6_monthly_{start}_{end}",
                "source_revision": revision,
                "row_count": int(subset["source_row_count"].sum()),
                "unique_code_count": int(subset["source_hs6"].nunique()),
                "mapped_unique_code_count": int(subset.loc[mapped, "source_hs6"].nunique()),
                "unmapped_unique_code_count": int(subset.loc[~mapped, "source_hs6"].nunique()),
                "excluded_special_code_count": int(subset.loc[excluded, "source_hs6"].nunique()),
                "code_coverage_rate": float(subset.loc[mapped, "source_hs6"].nunique() / subset["source_hs6"].nunique()),
                "row_coverage_rate": float(subset.loc[mapped, "source_row_count"].sum() / subset["source_row_count"].sum()),
                "total_value": total_value,
                "mapped_value": mapped_value,
                "excluded_special_value": excluded_value,
                "value_coverage_rate": mapped_value / total_value if total_value else None,
                "eligible_value_coverage_rate": mapped_value / eligible_denominator if eligible_denominator else None,
                "unmapped_codes": sorted(unmapped["source_hs6"].unique().tolist()),
                "top_unmapped_by_value": (
                    unmapped.groupby("source_hs6", as_index=False)["source_import_value_usd"]
                    .sum()
                    .sort_values("source_import_value_usd", ascending=False)
                    .head(20)
                    .rename(columns={"source_hs6": "hs6", "source_import_value_usd": "value"})
                    .to_dict(orient="records")
                ),
            }
        )
    minimum_value_coverage = min(record["value_coverage_rate"] for record in coverage)
    minimum_eligible_value_coverage = min(
        record.get("eligible_value_coverage_rate", record["value_coverage_rate"])
        for record in coverage
    )
    coverage_threshold_ok = minimum_value_coverage >= 0.95 and minimum_eligible_value_coverage >= 0.95
    if not coverage_threshold_ok:
        failures.append(
            "HS conversion coverage is below 0.95: "
            f"gross minimum={minimum_value_coverage:.6f}, eligible minimum={minimum_eligible_value_coverage:.6f}"
        )

    missing_multi_weights = int(
        (
            (correlation["target_count_per_source"] > 1)
            & correlation["mapping_weight"].notna()
        ).sum()
    )
    if missing_multi_weights:
        failures.append("one or more multi-target correlation rows received an unvalidated numeric weight")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "source_hash_checks": source_hash_checks,
        "conversion_row_count": len(conversion),
        "conversion_source_counts": conversion["source_revision"].value_counts().sort_index().to_dict(),
        "conversion_duplicate_source_keys": conversion_duplicates,
        "conversion_weights_all_one": conversion_weight_ok,
        "correlation_row_count": len(correlation),
        "correlation_duplicate_source_target_keys": correlation_duplicates,
        "relationship_counts_by_revision": actual_relationship_counts,
        "relationship_counts_match_inspected_workbooks": relationship_counts_ok,
        "invalid_hs6_count": invalid_codes,
        "official_conversion_pair_missing_count": conversion_pair_missing,
        "wco_corrigenda_checks_pass": corrigenda_ok,
        "hs2012_reference_fully_covered": hs12_reference_coverage,
        "unvalidated_multi_target_weight_count": missing_multi_weights,
        "observed_input_coverage": coverage,
        "minimum_observed_value_coverage_rate": minimum_value_coverage,
        "minimum_eligible_value_coverage_rate": minimum_eligible_value_coverage,
        "coverage_threshold_95pct_pass": coverage_threshold_ok,
        "census_crosswalk_row_count": len(census_crosswalk),
        "census_crosswalk_duplicate_keys": int(census_crosswalk.duplicated(["year", "source_hs6"]).sum()),
        "census_mapping_status_counts": census_crosswalk["mapping_status"].value_counts().sort_index().to_dict(),
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# HS Revision Bridge Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Canonical conversion: `{validation['conversion_output_path']}`",
        f"- Full correlation: `{validation['correlation_output_path']}`",
        f"- Census year-code crosswalk: `{validation['census_output_path']}`",
        f"- Conversion rows: `{validation['conversion_row_count']}`",
        f"- Correlation rows: `{validation['correlation_row_count']}`",
        f"- Validation status: **{validation['validation_status']}**",
        "",
        "## Conversion coverage",
        "",
        "| Input | Revision | Unique codes | Unmapped codes | Row coverage | Gross value coverage | Eligible value coverage |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in validation["observed_input_coverage"]:
        lines.append(
            f"| `{record['input_id']}` | `{record['source_revision']}` | {record['unique_code_count']} | {record['unmapped_unique_code_count']} | {record['row_coverage_rate']:.6%} | {record['value_coverage_rate']:.6%} | {record.get('eligible_value_coverage_rate', record['value_coverage_rate']):.6%} |"
        )
    lines.extend(
        [
            "",
            "## Required checks",
            "",
            f"- Official source SHA256 checks: `{'yes' if all(validation['source_hash_checks'].values()) else 'no'}`",
            f"- One canonical conversion per source code: `{'yes' if validation['conversion_duplicate_source_keys'] == 0 else 'no'}`",
            f"- Official conversion weights all equal 1: `{'yes' if validation['conversion_weights_all_one'] else 'no'}`",
            f"- WCO corrigenda reflected in HS2017-HS2012 pairs: `{'yes' if validation['wco_corrigenda_checks_pass'] else 'no'}`",
            f"- Multi-target correlation rows kept without unvalidated weights: `{'yes' if validation['unvalidated_multi_target_weight_count'] == 0 else 'no'}`",
            f"- Minimum observed-value coverage at least 95%: `{'yes' if validation['coverage_threshold_95pct_pass'] else 'no'}`",
            "",
            "## Interpretation",
            "",
            "The canonical conversion table uses the official UNSD one-target conversion and weight 1, so product values do not expand during revision harmonization. The full UNSD correlations are retained separately for audit and robustness. Multi-target correlation rows deliberately have no numeric mapping weight until a value-based weighting design is constructed and validated. Census HS6 is treated as HS2012 in 2014-2016, HS2017 in 2017-2021, and HS2022 in 2022-2024; HTS10 remains year-specific.",
            "",
        ]
    )
    return "\n".join(lines)


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build HS2012/2017/2022 bridges to HS2012.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--conversion-output",
        type=Path,
        default=Path("data/processed/concordances/hs_to_hs2012_conversion.parquet"),
    )
    parser.add_argument(
        "--correlation-output",
        type=Path,
        default=Path("data/processed/concordances/hs_revision_correlations.parquet"),
    )
    parser.add_argument(
        "--census-output",
        type=Path,
        default=Path("data/processed/concordances/census_hs6_year_to_hs2012.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/hs_revision_bridge_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/hs_revision_bridge_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    paths = [
        path if path.is_absolute() else project_root / path
        for path in (
            args.conversion_output,
            args.correlation_output,
            args.census_output,
            args.validation_json,
            args.validation_md,
        )
    ]
    conversion_output, correlation_output, census_output, validation_json, validation_md = paths
    for path in paths:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/hs_revision_rules.yaml")
    conversion, correlation = build_bridges(project_root, config)
    census_crosswalk = build_census_year_crosswalk(project_root, config, conversion)
    validation = validate_bridges(
        project_root,
        config,
        conversion,
        correlation,
        census_crosswalk,
    )
    conversion_table = write_parquet(conversion, conversion_output)
    correlation_table = write_parquet(correlation, correlation_output)
    census_table = write_parquet(census_crosswalk, census_output)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "conversion_output_path": conversion_output.relative_to(project_root).as_posix(),
            "conversion_output_sha256": sha256(conversion_output),
            "correlation_output_path": correlation_output.relative_to(project_root).as_posix(),
            "correlation_output_sha256": sha256(correlation_output),
            "census_output_path": census_output.relative_to(project_root).as_posix(),
            "census_output_sha256": sha256(census_output),
            "conversion_schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in conversion_table.schema
            ],
            "correlation_schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in correlation_table.schema
            ],
            "census_schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in census_table.schema
            ],
        }
    )
    validation_json.parent.mkdir(parents=True, exist_ok=True)
    validation_json.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    validation_md.write_text(markdown_report(validation), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "validation_status": validation["validation_status"],
                "conversion_rows": validation["conversion_row_count"],
                "correlation_rows": validation["correlation_row_count"],
                "minimum_value_coverage": validation["minimum_observed_value_coverage_rate"],
                "minimum_eligible_value_coverage": validation["minimum_eligible_value_coverage_rate"],
                "validation_json": str(validation_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if validation["validation_status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
