from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


DEFAULT_SOURCE_PAGES = {
    "master": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/tariff-actions",
    "list1": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/34-billion-trade-action",
    "list2": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/16-billion-trade-action",
    "list3": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/200-billion-trade-action",
    "list4": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china/300-billion-trade-action",
    "four_year_review": "https://ustr.gov/trade-topics/enforcement/section-301-investigations/section-301-china-technology-transfer/china-section-301-tariff-actions-and-exclusion-process/four-year-review",
    "machinery_exclusions": "https://ustr.gov/issue-areas/enforcement/section-301-investigations/section-301-china-technology-transfer/china-section-301-tariff-actions-and-exclusion-process/machinery-exclusions-process",
}

RAW_SUBDIRS = {
    "list1": "list1",
    "list2": "list2",
    "list3": "list3",
    "list4": "list4",
    "exclusions": "exclusions",
    "machinery_exclusions": "exclusions/machinery",
    "four_year_review": "four_year_review",
    "metadata": "metadata",
}

OFFICIAL_DOMAINS = {
    "ustr.gov",
    "www.ustr.gov",
    "site.ustr.gov",
    "federalregister.gov",
    "www.federalregister.gov",
    "govinfo.gov",
    "www.govinfo.gov",
    "cbp.gov",
    "www.cbp.gov",
    "csms.cbp.gov",
    "content.govdelivery.com",
    "comments.ustr.gov",
    "exclusions.ustr.gov",
}

RELEVANT_LINK_TERMS = {
    "action",
    "amendment",
    "cbp",
    "china",
    "continuation",
    "docket",
    "exclusion",
    "extension",
    "four-year",
    "guidance",
    "htsus",
    "list",
    "machinery",
    "modification",
    "notice",
    "product",
    "section-301",
    "tariff",
}

PANEL_COLUMNS = [
    "hts10",
    "hs6",
    "list_id",
    "effective_date",
    "additional_tariff_rate",
    "exclusion_flag",
    "exclusion_start",
    "exclusion_end",
    "source_notice",
    "source_url",
    "source_file",
    "notice_date",
    "source_code",
    "source_code_level",
    "rate_adjustment_applied",
]

EXPOSURE_COLUMNS = [
    "hs6",
    "year",
    "origin_iso3",
    "destination_iso3",
    "tariffed_product",
    "list_id",
    "tariff_rate",
    "china_import_share_2017",
    "tariff_exposure",
]

MANUAL_CODE_COLUMNS = [
    "source_code",
    "list_id",
    "effective_date",
    "additional_tariff_rate",
    "source_notice",
    "source_url",
    "source_file",
    "notice_date",
    "exclusion_flag",
    "exclusion_start",
    "exclusion_end",
]

FULL_ORIGIN_MIN_ORIGINS = 100


@dataclass(frozen=True)
class ActionSpec:
    group: str
    list_id: str
    effective_date: str
    additional_tariff_rate: float
    source_notice: str
    required_terms: tuple[str, ...]
    excluded_terms: tuple[str, ...] = ()


ACTION_SPECS = [
    ActionSpec(
        group="list1",
        list_id="list1",
        effective_date="2018-07-06",
        additional_tariff_rate=0.25,
        source_notice="List 1 Notice of Action",
        required_terms=("notice of action",),
    ),
    ActionSpec(
        group="list2",
        list_id="list2",
        effective_date="2018-08-23",
        additional_tariff_rate=0.25,
        source_notice="List 2 Notice of Action",
        required_terms=("notice of action",),
    ),
    ActionSpec(
        group="list3",
        list_id="list3",
        effective_date="2018-09-24",
        additional_tariff_rate=0.10,
        source_notice="List 3 Initial Additional Duty of 10 Percent",
        required_terms=("initial additional duty", "10 percent"),
    ),
]

DERIVED_EVENT_SPECS = [
    {
        "base_list_id": "list3",
        "list_id": "list3",
        "effective_date": "2019-05-10",
        "additional_tariff_rate": 0.25,
        "source_notice": "List 3 Modification to Increase Duty from 10 Percent to 25 Percent",
        "source_url": "https://www.govinfo.gov/content/pkg/FR-2019-05-09/pdf/2019-09681.pdf",
        "source_file": "data/raw/ustr_section301/list3/list3_007_84_FR_20459.pdf",
        "notice_date": "2019-05-09",
    },
    {
        "base_list_id": "list4a",
        "list_id": "list4a",
        "effective_date": "2020-02-14",
        "additional_tariff_rate": 0.075,
        "source_notice": "List 4A Phase One Reduction from 15 Percent to 7.5 Percent",
        "source_url": "https://www.govinfo.gov/content/pkg/FR-2020-01-22/pdf/2020-00904.pdf",
        "source_file": "data/raw/ustr_section301/list4/list4_006_Notice_of_Modification-January_2020.pdf",
        "notice_date": "2020-01-22",
    },
]

# BACI V202601 publishes petroleum heading 2710 as one HS6 aggregate. The wood
# aliases implement the 38 successor subheadings in 83 FR 49153 at HS6 level.
HS6_BACI_ALIASES = {
    "271012": ["271000"],
    "271019": ["271000"],
    "271020": ["271000"],
    "271091": ["271000"],
    "271099": ["271000"],
    "440110": ["440111", "440112"],
    "440310": ["440311", "440312"],
    "440320": ["440321", "440322", "440323", "440324", "440325", "440326"],
    "440392": ["440393", "440394"],
    "440399": ["440395", "440396", "440397", "440398", "440399"],
    "440610": ["440611", "440612"],
    "440690": ["440691", "440692"],
    "440710": ["440711", "440712", "440719"],
    "440799": ["440796", "440797", "440799"],
    "441232": ["441233", "441234"],
}


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.links: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        href = None
        for key, value in attrs:
            if key.lower() == "href":
                href = value
                break
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = " ".join(part.strip() for part in self._current_text if part.strip())
        self.links.append({"href": self._current_href, "text": " ".join(text.split())})
        self._current_href = None
        self._current_text = []


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} did not contain a YAML mapping.")
    return data


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def normalize_url(url: str, base_url: str) -> str:
    parsed = urlparse(urljoin(base_url, url.strip()))
    return parsed._replace(fragment="").geturl()


def domain_allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in OFFICIAL_DOMAINS


def relevant_link(text: str, url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.casefold()
    suffix = Path(path).suffix.casefold()
    haystack = f"{text} {url}".casefold()
    if not text.strip() and suffix not in {".pdf", ".csv", ".xlsx", ".xls"}:
        return False
    if parsed.netloc.lower() in {"ustr.gov", "www.ustr.gov", "site.ustr.gov"}:
        if "/sites/default/files/" in path and suffix in {".pdf", ".csv", ".xlsx", ".xls"}:
            return True
        return False
    if any(term in haystack for term in RELEVANT_LINK_TERMS):
        return True
    return suffix in {".pdf", ".csv", ".xlsx", ".xls"}


def safe_filename(url: str, label: str, suffix_hint: str | None = None) -> str:
    parsed = urlparse(url)
    raw_name = Path(parsed.path).name
    suffix = Path(raw_name).suffix.lower()
    if not suffix and suffix_hint:
        suffix = suffix_hint
    if not suffix:
        suffix = ".html"
    stem_source = raw_name[:-len(suffix)] if raw_name.endswith(suffix) else raw_name
    if not stem_source:
        stem_source = label
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem_source).strip("._-")
    if not stem:
        stem = "source"
    return f"{stem[:120]}{suffix}"


def fetch_url(url: str, retries: int = 3, sleep_seconds: float = 1.5) -> tuple[bytes, str, str]:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers={"User-Agent": "trade-welfare-codex/1.0"})
            with urlopen(request, timeout=90) as response:
                content = response.read()
                content_type = response.headers.get("Content-Type", "")
                final_url = response.geturl()
            return content, content_type, final_url
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(sleep_seconds * attempt)
    raise RuntimeError(f"Download failed after {retries} attempts for {url}: {last_error}") from last_error


def source_pages_from_config(config: dict[str, Any]) -> dict[str, str]:
    section = config.get("ustr_section301", {})
    pages = section.get("source_pages") or DEFAULT_SOURCE_PAGES
    if not isinstance(pages, dict):
        raise ValueError("ustr_section301.source_pages must be a mapping.")
    merged = dict(DEFAULT_SOURCE_PAGES)
    merged.update({str(key): str(value) for key, value in pages.items()})
    return merged


def ensure_dirs(raw_dir: Path, output_dir: Path | None = None) -> dict[str, Path]:
    raw_dirs = raw_dir_paths(raw_dir)
    for directory in raw_dirs.values():
        directory.mkdir(parents=True, exist_ok=True)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
    return raw_dirs


def raw_dir_paths(raw_dir: Path) -> dict[str, Path]:
    return {key: raw_dir / rel for key, rel in RAW_SUBDIRS.items()}


def category_for_link(source_key: str, text: str, url: str) -> str:
    haystack = f"{text} {url}".casefold()
    if source_key == "machinery_exclusions":
        return "machinery_exclusions"
    if "machinery" in haystack:
        return "machinery_exclusions"
    if "exclusion" in haystack or "extension" in haystack:
        return "exclusions"
    if source_key == "four_year_review" or "four-year" in haystack:
        return "four_year_review"
    if source_key in {"list1", "list2", "list3", "list4"}:
        return source_key
    return "metadata"


def discover_links(html: str, base_url: str) -> list[dict[str, str]]:
    parser = LinkCollector()
    parser.feed(html)
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in parser.links:
        url = normalize_url(link["href"], base_url)
        if url in seen or not domain_allowed(url) or not relevant_link(link["text"], url):
            continue
        seen.add(url)
        links.append({"url": url, "text": link["text"]})
    return links


def write_manifest(manifest_path: Path, entries: list[dict[str, Any]]) -> None:
    manifest_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def load_manifest(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.exists():
        return []
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{manifest_path} must contain a JSON list.")
    return [entry for entry in data if isinstance(entry, dict)]


def download_sources(
    raw_dirs: dict[str, Path],
    source_pages: dict[str, str],
    max_links_per_page: int,
) -> list[dict[str, Any]]:
    manifest_name = (
        "section301_source_manifest_diagnostic.json"
        if max_links_per_page > 0
        else "section301_source_manifest.json"
    )
    manifest_path = raw_dirs["metadata"] / manifest_name
    by_key: dict[str, dict[str, Any]] = {}
    downloaded_at = dt.datetime.now(dt.timezone.utc).isoformat()

    entries: list[dict[str, Any]] = []
    manifest_mode = "diagnostic_partial" if max_links_per_page > 0 else "complete_requested"

    def add_or_refresh_entry(entry: dict[str, Any]) -> None:
        key = f"{entry.get('source_key')}|{entry.get('source_url')}|{entry.get('link_text')}"
        old = by_key.get(key)
        if old:
            old.update(entry)
        else:
            entries.append(entry)
            by_key[key] = entry

    for source_key, url in source_pages.items():
        target_dir = raw_dirs.get(source_key, raw_dirs["metadata"])
        target_path = target_dir / f"{source_key}_source_page.html"
        if target_path.exists():
            content = target_path.read_bytes()
            content_type = "text/html"
            final_url = url
        else:
            content, content_type, final_url = fetch_url(url)
            target_path.write_bytes(content)
        add_or_refresh_entry(
            {
                "source_key": source_key,
                "category": source_key if source_key in RAW_SUBDIRS else "metadata",
                "source_url": final_url,
                "source_page_url": url,
                "link_text": f"{source_key} source page",
                "local_path": str(target_path.as_posix()),
                "downloaded_at_utc": downloaded_at,
                "sha256": sha256_bytes(content),
                "content_type": content_type,
                "bytes": len(content),
                "status": "downloaded" if target_path.exists() else "cached",
                "manifest_mode": manifest_mode,
            }
        )
        print(f"Archived source page {source_key}: {target_path}", flush=True)
        write_manifest(manifest_path, entries)

        html = content.decode("utf-8", errors="replace")
        links = discover_links(html, final_url)
        if max_links_per_page > 0:
            links = links[:max_links_per_page]
        for idx, link in enumerate(links, start=1):
            category = category_for_link(source_key, link["text"], link["url"])
            link_dir = raw_dirs[category]
            filename = f"{source_key}_{idx:03d}_{safe_filename(link['url'], link['text'])}"
            path = link_dir / filename
            if path.exists():
                link_content = path.read_bytes()
                link_content_type = ""
                final_link_url = link["url"]
            else:
                try:
                    link_content, link_content_type, final_link_url = fetch_url(link["url"])
                    path.write_bytes(link_content)
                except RuntimeError as exc:
                    add_or_refresh_entry(
                        {
                            "source_key": source_key,
                            "category": category,
                            "source_url": link["url"],
                            "source_page_url": final_url,
                            "link_text": link["text"],
                            "local_path": None,
                            "downloaded_at_utc": downloaded_at,
                            "sha256": None,
                            "content_type": None,
                            "bytes": None,
                            "status": f"download_failed: {exc}",
                            "manifest_mode": manifest_mode,
                        }
                    )
                    write_manifest(manifest_path, entries)
                    continue
            add_or_refresh_entry(
                {
                    "source_key": source_key,
                    "category": category,
                    "source_url": final_link_url,
                    "source_page_url": final_url,
                    "link_text": link["text"],
                    "local_path": str(path.as_posix()),
                    "downloaded_at_utc": downloaded_at,
                    "sha256": sha256_bytes(link_content),
                    "content_type": link_content_type,
                    "bytes": len(link_content),
                    "status": "downloaded",
                    "manifest_mode": manifest_mode,
                }
            )
            print(f"Archived linked source {source_key} #{idx}: {path}", flush=True)
            write_manifest(manifest_path, entries)

    write_manifest(manifest_path, entries)
    return entries


def parse_date(value: Any) -> dt.date | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    return dt.date.fromisoformat(text)


def hts_digits(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text:
        return None
    digits = re.sub(r"\D", "", text)
    if len(digits) in {6, 8, 10} and not digits.startswith(("98", "99")):
        return digits
    return None


def source_code_level(code: str) -> int:
    return len(code)


def extract_hts_codes_from_text(text: str) -> list[str]:
    dotted = re.findall(r"\b([0-9]{4}\.[0-9]{2}\.[0-9]{2}(?:[0-9]{2})?)\b", text)
    compact = re.findall(r"(?<![0-9])([0-9]{8}|[0-9]{10})(?![0-9])", text)
    codes = []
    for raw in [*dotted, *compact]:
        code = hts_digits(raw)
        if code:
            codes.append(code)
    return sorted(set(codes))


def read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF parsing requires pypdf. Install code/data_build/requirements-ustr-section301.txt."
        ) from exc
    reader = PdfReader(str(path))
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)
    return "\n".join(text_parts)


def read_source_text(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        return read_pdf_text(path)
    if suffix in {".html", ".htm", ".txt", ".csv", ".json", ".xml"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".xls", ".xlsx"}:
        frames = pd.read_excel(path, sheet_name=None, dtype="string")
        return "\n".join(frame.to_csv(index=False) for frame in frames.values())
    return path.read_text(encoding="utf-8", errors="replace")


def classify_action(entry: dict[str, Any]) -> ActionSpec | None:
    category = str(entry.get("category") or entry.get("source_key") or "")
    haystack = f"{entry.get('link_text', '')} {entry.get('source_url', '')}".casefold()
    if "exclusion" in haystack or category in {"exclusions", "machinery_exclusions"}:
        return None
    for spec in ACTION_SPECS:
        if category != spec.group and entry.get("source_key") != spec.group:
            continue
        if all(term in haystack for term in spec.required_terms) and not any(
            term in haystack for term in spec.excluded_terms
        ):
            return spec
    return None


def row_from_code(
    code: str,
    list_id: str,
    effective_date: str,
    additional_tariff_rate: float,
    source_notice: str,
    source_url: str,
    source_file: str,
    notice_date: str | None = None,
    exclusion_flag: bool = False,
    exclusion_start: str | None = None,
    exclusion_end: str | None = None,
    rate_adjustment_applied: bool = True,
) -> dict[str, Any]:
    return {
        "source_code": code,
        "source_code_level": source_code_level(code),
        "list_id": list_id,
        "effective_date": effective_date,
        "additional_tariff_rate": additional_tariff_rate,
        "exclusion_flag": exclusion_flag,
        "exclusion_start": exclusion_start,
        "exclusion_end": exclusion_end,
        "source_notice": source_notice,
        "source_url": source_url,
        "source_file": source_file,
        "notice_date": notice_date,
        "rate_adjustment_applied": rate_adjustment_applied,
    }


def manual_code_rows(raw_dirs: dict[str, Path]) -> list[dict[str, Any]]:
    manual_path = raw_dirs["metadata"] / "section301_notice_codes.csv"
    if not manual_path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with manual_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(MANUAL_CODE_COLUMNS[:5]) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{manual_path} is missing columns: {sorted(missing)}")
        for raw in reader:
            code = hts_digits(raw.get("source_code"))
            if not code:
                raise ValueError(f"{manual_path} has invalid source_code: {raw.get('source_code')}")
            rate = float(raw["additional_tariff_rate"])
            rows.append(
                row_from_code(
                    code=code,
                    list_id=str(raw["list_id"]).strip(),
                    effective_date=str(raw["effective_date"]).strip(),
                    additional_tariff_rate=rate,
                    source_notice=str(raw["source_notice"]).strip(),
                    source_url=str(raw.get("source_url") or "").strip(),
                    source_file=str(raw.get("source_file") or manual_path.as_posix()).strip(),
                    notice_date=str(raw.get("notice_date") or "").strip() or None,
                    exclusion_flag=str(raw.get("exclusion_flag") or "").casefold() in {"1", "true", "yes"},
                    exclusion_start=str(raw.get("exclusion_start") or "").strip() or None,
                    exclusion_end=str(raw.get("exclusion_end") or "").strip() or None,
                    rate_adjustment_applied=True,
                )
            )
    return rows


def extracted_code_rows(manifest: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for entry in manifest:
        path_text = entry.get("local_path")
        if not path_text:
            continue
        path = Path(path_text)
        if not path.exists():
            continue
        spec = classify_action(entry)
        if not spec:
            continue
        try:
            text = read_source_text(path)
            codes = extract_hts_codes_from_text(text)
        except Exception as exc:
            audit.append(
                {
                    "source_url": entry.get("source_url"),
                    "source_file": str(path.as_posix()),
                    "issue": f"could_not_extract_codes: {exc}",
                }
            )
            continue
        if not codes:
            audit.append(
                {
                    "source_url": entry.get("source_url"),
                    "source_file": str(path.as_posix()),
                    "issue": "no_hts_codes_extracted",
                }
            )
            continue
        for code in codes:
            rows.append(
                row_from_code(
                    code=code,
                    list_id=spec.list_id,
                    effective_date=spec.effective_date,
                    additional_tariff_rate=spec.additional_tariff_rate,
                    source_notice=spec.source_notice,
                    source_url=str(entry.get("source_url") or ""),
                    source_file=str(path.as_posix()),
                    notice_date=None,
                )
            )
    return rows, audit


def census_status_for_path(census_path: Path, exposure_year: int) -> dict[str, Any]:
    status: dict[str, Any] = {
        "path": str(census_path),
        "exists": census_path.exists(),
        "requires_full_origin_2017_hs10": True,
        "full_origin_min_origins": FULL_ORIGIN_MIN_ORIGINS,
    }
    if not census_path.exists():
        return status
    try:
        parquet = pq.ParquetFile(census_path)
        status["columns"] = parquet.schema_arrow.names
        status["rows"] = parquet.metadata.num_rows
        required = {"year", "origin_iso3", "hts10", "import_value_usd"}
        status["has_required_columns"] = required.issubset(set(status["columns"]))
        if status["has_required_columns"]:
            table = pq.read_table(census_path, columns=["year", "origin_iso3"])
            df = table.to_pandas()
            year_df = df[df["year"] == exposure_year]
            origins = set(year_df["origin_iso3"].dropna().astype(str))
            origin_count = len(origins)
            status["rows_for_exposure_year"] = int(len(year_df))
            status["origin_count_for_exposure_year"] = origin_count
            status["origin_codes_for_exposure_year"] = sorted(origins)
            status["full_origin_mode"] = (
                "world_total_plus_china"
                if {"WLD", "CHN"}.issubset(origins)
                else "country_detail"
            )
            status["full_origin_ready"] = (
                {"WLD", "CHN"}.issubset(origins)
                or origin_count >= FULL_ORIGIN_MIN_ORIGINS
            )
    except Exception as exc:
        status["read_error"] = str(exc)
    return status


def load_census_year_imports(census_path: Path, exposure_year: int) -> pd.DataFrame:
    if not census_path.exists():
        raise FileNotFoundError(
            f"Missing Census HS10 imports parquet: {census_path}. "
            "Build a full-origin 2017 HS10 Census import file before processing Section 301 exposure."
        )
    columns = ["year", "origin_iso3", "hts10", "import_value_usd"]
    table = pq.read_table(census_path, columns=columns)
    df = table.to_pandas()
    df = df[df["year"] == exposure_year].copy()
    if df.empty:
        raise RuntimeError(f"{census_path} has no rows for {exposure_year}.")
    df["hts10"] = df["hts10"].astype("string").str.zfill(10)
    return df


def require_full_origin_census(df: pd.DataFrame, census_path: Path, exposure_year: int, purpose: str) -> None:
    origins = set(df["origin_iso3"].dropna().astype(str))
    origin_count = len(origins)
    has_world_total = {"WLD", "CHN"}.issubset(origins)
    if not has_world_total and origin_count < FULL_ORIGIN_MIN_ORIGINS:
        raise RuntimeError(
            f"{census_path} has only {origin_count} origins for {exposure_year}. "
            f"{purpose} requires either WLD plus CHN annual totals or at least "
            f"{FULL_ORIGIN_MIN_ORIGINS} country origins, not the project comparator subset."
        )


def census_universe_from_imports(df: pd.DataFrame) -> pd.DataFrame:
    world = df[df["origin_iso3"] == "WLD"]
    source = world if not world.empty else df
    universe = source[["hts10"]].drop_duplicates().copy()
    universe["hs6"] = universe["hts10"].str.slice(0, 6)
    universe["hts8"] = universe["hts10"].str.slice(0, 8)
    return universe


def load_census_universe(census_path: Path, exposure_year: int) -> pd.DataFrame:
    df = load_census_year_imports(census_path, exposure_year)
    require_full_origin_census(df, census_path, exposure_year, "HTS8-to-HTS10 expansion")
    return census_universe_from_imports(df)


def census_stats_from_imports(df: pd.DataFrame) -> pd.DataFrame:
    world = df[df["origin_iso3"] == "WLD"]
    if world.empty:
        total = df.groupby("hts10", dropna=False)["import_value_usd"].sum()
    else:
        total = world.groupby("hts10", dropna=False)["import_value_usd"].sum()
    total = total.rename("total_import_value_2017")
    china = (
        df[df["origin_iso3"] == "CHN"]
        .groupby("hts10", dropna=False)["import_value_usd"]
        .sum()
        .rename("china_import_value_2017")
    )
    stats = pd.concat([total, china], axis=1).reset_index()
    stats["china_import_value_2017"] = stats["china_import_value_2017"].fillna(0.0)
    stats["china_import_share_2017"] = stats["china_import_value_2017"] / stats["total_import_value_2017"]
    stats.loc[stats["total_import_value_2017"] <= 0, "china_import_share_2017"] = pd.NA
    stats["hs6"] = stats["hts10"].str.slice(0, 6)
    stats["hts8"] = stats["hts10"].str.slice(0, 8)
    return stats


def load_census_stats(census_path: Path, exposure_year: int) -> pd.DataFrame:
    df = load_census_year_imports(census_path, exposure_year)
    require_full_origin_census(df, census_path, exposure_year, "Section 301 exposure")
    return census_stats_from_imports(df)


def load_census_china_hts10(census_path: Path, exposure_year: int) -> pd.DataFrame:
    df = load_census_year_imports(census_path, exposure_year)
    china = df[df["origin_iso3"] == "CHN"].copy()
    if china.empty:
        raise RuntimeError(f"{census_path} has no CHN rows for {exposure_year}.")
    china = (
        china.groupby("hts10", as_index=False, dropna=False)["import_value_usd"]
        .sum()
        .rename(columns={"import_value_usd": "census_china_import_value_2017"})
    )
    china["hs6"] = china["hts10"].str.slice(0, 6)
    china = china[pd.to_numeric(china["hs6"].str.slice(0, 2), errors="coerce") < 98]
    if (china["census_china_import_value_2017"] < 0).any():
        raise ValueError(f"{census_path} contains negative CHN import values.")
    return china


def load_baci_us_hs6_imports(
    baci_path: Path,
    exposure_year: int,
) -> pd.DataFrame:
    if exposure_year != 2017:
        raise ValueError("The configured compact BACI denominator is defined for 2017 only.")
    if not baci_path.exists():
        raise FileNotFoundError(f"Missing BACI HS2017 denominator: {baci_path}")
    required = {
        "hs6",
        "baci_total_us_import_value_2017",
        "baci_china_import_value_2017",
        "china_import_share_2017",
    }
    stats = pq.read_table(baci_path, columns=sorted(required)).to_pandas()
    missing = required - set(stats.columns)
    if missing:
        raise ValueError(f"{baci_path} is missing columns: {sorted(missing)}")
    stats["hs6"] = stats["hs6"].astype("string").str.zfill(6)
    if len(stats) < 5_000 or stats["hs6"].duplicated().any():
        raise ValueError(f"{baci_path} is not a complete unique HS2017 product universe.")
    invalid = (
        (stats["baci_total_us_import_value_2017"] < 0)
        | (stats["baci_china_import_value_2017"] < 0)
        | ~stats["china_import_share_2017"].between(0, 1)
    )
    if invalid.any():
        raise ValueError(f"{baci_path} produced invalid 2017 USA import shares.")
    return stats


def load_usitc_hts_universe(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing USITC HTS universe: {path}. Download the configured 2017 HTS CSV first."
        )
    frame = pd.read_csv(path, dtype="string")
    if "HTS Number" not in frame.columns:
        raise ValueError(f"{path} is missing the HTS Number column.")
    raw_codes = frame["HTS Number"].fillna("").map(hts_digits)
    ten_digit = {
        code
        for code in raw_codes
        if isinstance(code, str) and len(code) == 10 and int(code[:2]) < 98
    }
    eight_digit = {
        code
        for code in raw_codes
        if isinstance(code, str) and len(code) == 8 and int(code[:2]) < 98
    }
    # Some statistical lines terminate at HTS8 in the official schedule. Census
    # represents those commodities in its 10-character field with trailing 00.
    terminal_eight_digit = {
        code for code in eight_digit if not any(item.startswith(code) for item in ten_digit)
    }
    codes = sorted(ten_digit | {f"{code}00" for code in terminal_eight_digit})
    if len(codes) < 15_000:
        raise ValueError(f"{path} has only {len(codes)} product-level HTS10 codes.")
    universe = pd.DataFrame({"hts10": pd.Series(codes, dtype="string")})
    universe["hs6"] = universe["hts10"].str.slice(0, 6)
    return universe


def load_usitc_hts_universes(paths: dict[str, list[Path]]) -> dict[str, pd.DataFrame]:
    if not paths:
        raise ValueError("No USITC HTS universes were configured.")
    universes: dict[str, pd.DataFrame] = {}
    for list_id, list_paths in paths.items():
        frames = [load_usitc_hts_universe(path) for path in list_paths]
        universes[list_id] = pd.concat(frames, ignore_index=True).drop_duplicates("hts10")
    return universes


def expand_to_hts10(
    source_rows: list[dict[str, Any]],
    hts_universes: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    expanded: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    for row in source_rows:
        code = row["source_code"]
        list_id = str(row["list_id"])
        hts_universe = hts_universes.get(list_id)
        if hts_universe is None:
            hts_universe = hts_universes.get("default")
        if hts_universe is None:
            raise RuntimeError(f"No USITC HTS universe configured for {list_id}.")
        if len(code) == 10:
            matches = hts_universe.loc[
                hts_universe["hts10"] == code, ["hts10", "hs6"]
            ].drop_duplicates()
            if matches.empty:
                audit.append({**row, "issue": "hts10_not_in_configured_hts_universe"})
                continue
        else:
            matches = hts_universe.loc[
                hts_universe["hts10"].str.startswith(code), ["hts10", "hs6"]
            ].drop_duplicates()
            if matches.empty:
                audit.append({**row, "issue": "source_prefix_not_expanded_in_hts_universe"})
                continue
        for match in matches.itertuples(index=False):
            expanded.append(
                {
                    "hts10": str(match.hts10),
                    "hs6": str(match.hs6),
                    **row,
                }
            )
    panel = pd.DataFrame(expanded)
    audit_df = pd.DataFrame(audit)
    return panel, audit_df


def add_derived_events(panel: pd.DataFrame) -> pd.DataFrame:
    frames = [panel]
    for spec in DERIVED_EVENT_SPECS:
        base = panel[
            (panel["list_id"] == spec["base_list_id"])
            & (panel["exclusion_flag"] == False)  # noqa: E712
        ].copy()
        if base.empty:
            continue
        base["list_id"] = spec["list_id"]
        base["effective_date"] = spec["effective_date"]
        base["additional_tariff_rate"] = spec["additional_tariff_rate"]
        base["source_notice"] = spec["source_notice"]
        base["source_url"] = spec["source_url"]
        base["source_file"] = spec["source_file"]
        base["notice_date"] = spec["notice_date"]
        base["rate_adjustment_applied"] = True
        frames.append(base)
    return pd.concat(frames, ignore_index=True)


def panel_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("hts10", pa.string()),
            pa.field("hs6", pa.string()),
            pa.field("list_id", pa.string()),
            pa.field("effective_date", pa.date32()),
            pa.field("additional_tariff_rate", pa.float64()),
            pa.field("exclusion_flag", pa.bool_()),
            pa.field("exclusion_start", pa.date32()),
            pa.field("exclusion_end", pa.date32()),
            pa.field("source_notice", pa.string()),
            pa.field("source_url", pa.string()),
            pa.field("source_file", pa.string()),
            pa.field("notice_date", pa.date32()),
            pa.field("source_code", pa.string()),
            pa.field("source_code_level", pa.int8()),
            pa.field("rate_adjustment_applied", pa.bool_()),
        ]
    )


def exposure_schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("hs6", pa.string()),
            pa.field("year", pa.int16()),
            pa.field("origin_iso3", pa.string()),
            pa.field("destination_iso3", pa.string()),
            pa.field("tariffed_product", pa.bool_()),
            pa.field("list_id", pa.string()),
            pa.field("tariff_rate", pa.float64()),
            pa.field("china_import_share_2017", pa.float64()),
            pa.field("tariff_exposure", pa.float64()),
        ]
    )


def validate_panel(panel: pd.DataFrame) -> None:
    if panel.empty:
        raise RuntimeError("No HTS10 tariff rows were generated from official sources.")
    key = ["hts10", "list_id", "effective_date"]
    if panel.duplicated(key).any():
        sample = panel.loc[panel.duplicated(key, keep=False), key + ["source_code"]].head(20)
        raise ValueError(
            "section301_hts10_list_panel has duplicate hts10/list/date keys: "
            f"{sample.to_dict('records')}"
        )
    if set(panel["hts10"].astype("string").str.len().dropna().unique()) != {10}:
        raise ValueError("section301_hts10_list_panel has non-10-digit hts10 values.")
    if set(panel["hs6"].astype("string").str.len().dropna().unique()) != {6}:
        raise ValueError("section301_hts10_list_panel has non-6-digit hs6 values.")
    if not panel["additional_tariff_rate"].between(0, 1).all():
        raise ValueError("additional_tariff_rate must be in [0, 1].")
    for start_col, end_col in [("exclusion_start", "exclusion_end")]:
        both = panel[start_col].notna() & panel[end_col].notna()
        if both.any() and (panel.loc[both, start_col] > panel.loc[both, end_col]).any():
            raise ValueError("Exclusion date interval is reversed for at least one row.")


def date32_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for column in columns:
        out[column] = pd.to_datetime(out[column], errors="coerce").dt.date
    return out


def write_panel(panel: pd.DataFrame, output_path: Path, overwrite: bool) -> None:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} exists. Re-run with --overwrite to replace it.")
    if output_path.exists():
        output_path.unlink()
    panel = panel[PANEL_COLUMNS].copy()
    panel = date32_columns(panel, ["effective_date", "exclusion_start", "exclusion_end", "notice_date"])
    table = pa.Table.from_pandas(panel, schema=panel_schema(), preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")


def annual_weighted_rate(events: pd.DataFrame, year: int) -> tuple[float, str]:
    year_start = dt.date(year, 1, 1)
    year_end = dt.date(year + 1, 1, 1)
    ordered = events.sort_values("effective_date").copy()
    ordered["effective_date"] = pd.to_datetime(ordered["effective_date"]).dt.date
    intervals: list[tuple[dt.date, dt.date, float, str]] = []
    current_rate = 0.0
    current_list_id = ""
    cursor = year_start
    for row in ordered.itertuples(index=False):
        event_date = row.effective_date
        if event_date >= year_end:
            break
        if event_date > cursor:
            intervals.append((cursor, min(event_date, year_end), current_rate, current_list_id))
            cursor = event_date
        current_rate = float(row.additional_tariff_rate)
        current_list_id = str(row.list_id)
    if cursor < year_end:
        intervals.append((cursor, year_end, current_rate, current_list_id))
    days = (year_end - year_start).days
    weighted = sum((end - start).days * rate for start, end, rate, _ in intervals) / days
    active_lists = sorted({list_id for _, _, rate, list_id in intervals if rate > 0 and list_id})
    return weighted, ";".join(active_lists)


def build_hts_year_rates(panel: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    non_exclusions = panel[~panel["exclusion_flag"]].copy()
    non_exclusions["effective_date"] = pd.to_datetime(non_exclusions["effective_date"])
    non_exclusions = non_exclusions.sort_values(["hts10", "effective_date"])
    non_exclusions["next_effective_date"] = non_exclusions.groupby("hts10")[
        "effective_date"
    ].shift(-1)
    universe = non_exclusions[["hts10", "hs6"]].drop_duplicates()
    frames: list[pd.DataFrame] = []

    for year in years:
        year_start = pd.Timestamp(year=year, month=1, day=1)
        year_end = pd.Timestamp(year=year + 1, month=1, day=1)
        active = non_exclusions[
            (non_exclusions["effective_date"] < year_end)
            & (
                non_exclusions["next_effective_date"].isna()
                | (non_exclusions["next_effective_date"] > year_start)
            )
        ].copy()
        active["interval_start"] = active["effective_date"].clip(lower=year_start)
        active["interval_end"] = active["next_effective_date"].fillna(year_end).clip(
            upper=year_end
        )
        active["active_days"] = (
            active["interval_end"] - active["interval_start"]
        ).dt.days.clip(lower=0)
        active = active[active["active_days"] > 0]
        active["rate_days"] = active["additional_tariff_rate"] * active["active_days"]
        days_in_year = (year_end - year_start).days
        rates = (
            active.groupby("hts10", as_index=False)["rate_days"]
            .sum()
            .assign(tariff_rate=lambda frame: frame["rate_days"] / days_in_year)
            .drop(columns="rate_days")
        )
        positive = active[active["additional_tariff_rate"] > 0]
        list_ids = (
            positive.groupby("hts10")["list_id"]
            .agg(lambda values: ";".join(sorted(set(values.astype(str)))))
            .rename("list_id")
            .reset_index()
        )
        year_frame = universe.merge(rates, on="hts10", how="left").merge(
            list_ids, on="hts10", how="left"
        )
        year_frame["tariff_rate"] = year_frame["tariff_rate"].fillna(0.0)
        year_frame["list_id"] = year_frame["list_id"].fillna("")
        year_frame["year"] = year
        frames.append(year_frame)

    return pd.concat(frames, ignore_index=True)


def build_exposure(panel: pd.DataFrame, census_stats: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    hts_year = build_hts_year_rates(panel, years)
    hts_year = hts_year.merge(
        census_stats[
            [
                "hts10",
                "total_import_value_2017",
                "china_import_share_2017",
            ]
        ],
        on="hts10",
        how="left",
    )
    missing = hts_year["total_import_value_2017"].isna() | (hts_year["total_import_value_2017"] <= 0)
    hts_year.loc[missing, ["china_import_share_2017"]] = pd.NA

    grouped_rows: list[dict[str, Any]] = []
    for (hs6, year), group in hts_year.groupby(["hs6", "year"], dropna=False):
        valid = group.dropna(subset=["total_import_value_2017"])
        valid = valid[valid["total_import_value_2017"] > 0]
        if valid.empty:
            tariff_rate = pd.NA
            china_share = pd.NA
        else:
            weights = valid["total_import_value_2017"] / valid["total_import_value_2017"].sum()
            tariff_rate = float((valid["tariff_rate"] * weights).sum())
            china_share = float((valid["china_import_share_2017"] * weights).sum())
        list_ids = sorted({x for x in group["list_id"].dropna().astype(str) if x})
        grouped_rows.append(
            {
                "hs6": hs6,
                "year": int(year),
                "origin_iso3": "CHN",
                "destination_iso3": "USA",
                "tariffed_product": bool((group["tariff_rate"] > 0).any()),
                "list_id": ";".join(list_ids),
                "tariff_rate": tariff_rate,
                "china_import_share_2017": china_share,
                "tariff_exposure": (
                    pd.NA if pd.isna(tariff_rate) or pd.isna(china_share) else float(tariff_rate) * float(china_share)
                ),
            }
        )
    exposure = pd.DataFrame(grouped_rows, columns=EXPOSURE_COLUMNS)
    return exposure


def build_hybrid_exposure(
    panel: pd.DataFrame,
    census_china: pd.DataFrame,
    baci_stats: pd.DataFrame,
    years: list[int],
) -> pd.DataFrame:
    hts_year = build_hts_year_rates(panel, years)
    hts_year["hs6_source"] = hts_year["hs6"]
    hts_year["hs6"] = hts_year["hs6"].map(
        lambda code: HS6_BACI_ALIASES.get(str(code), [str(code)])
    )
    hts_year = hts_year.explode("hs6", ignore_index=True)
    census_china = census_china.copy()
    panel_hs6 = sorted(hts_year["hs6"].unique())
    rows: list[dict[str, Any]] = []

    for year in years:
        rates = hts_year[hts_year["year"] == year].copy()
        china_rates = census_china.merge(
            rates[["hts10", "hs6", "tariff_rate"]].rename(columns={"hs6": "policy_hs6"}),
            on="hts10",
            how="left",
        )
        china_rates["hs6"] = china_rates["policy_hs6"].fillna(china_rates["hs6"])
        china_rates["tariff_rate"] = china_rates["tariff_rate"].fillna(0.0)
        china_rates["weighted_rate_value"] = (
            china_rates["census_china_import_value_2017"] * china_rates["tariff_rate"]
        )
        weighted = china_rates.groupby("hs6", as_index=False).agg(
            census_china_import_value_2017=("census_china_import_value_2017", "sum"),
            weighted_rate_value=("weighted_rate_value", "sum"),
        )
        weighted["tariff_rate"] = (
            weighted["weighted_rate_value"]
            / weighted["census_china_import_value_2017"]
        )

        legal = rates.groupby("hs6", as_index=False).agg(
            legal_rate_mean=("tariff_rate", "mean"),
            tariffed_product=("tariff_rate", lambda values: bool((values > 0).any())),
            list_id=(
                "list_id",
                lambda values: ";".join(
                    sorted({item for value in values for item in str(value).split(";") if item})
                ),
            ),
        )
        year_frame = pd.DataFrame({"hs6": panel_hs6}).merge(
            legal, on="hs6", how="left"
        )
        year_frame = year_frame.merge(
            weighted[["hs6", "census_china_import_value_2017", "tariff_rate"]],
            on="hs6",
            how="left",
        )
        no_china_detail = (
            year_frame["census_china_import_value_2017"].isna()
            | (year_frame["census_china_import_value_2017"] <= 0)
        )
        year_frame.loc[no_china_detail, "tariff_rate"] = year_frame.loc[
            no_china_detail, "legal_rate_mean"
        ]
        year_frame = year_frame.merge(
            baci_stats[["hs6", "china_import_share_2017"]],
            on="hs6",
            how="left",
        )
        missing_baci = year_frame["china_import_share_2017"].isna()
        if missing_baci.any():
            missing_codes = year_frame.loc[missing_baci, "hs6"].tolist()
            raise ValueError(
                "BACI HS2017 has no USA import denominator for Section 301 HS6 codes: "
                f"{missing_codes[:20]}"
            )
        year_frame["year"] = year
        year_frame["origin_iso3"] = "CHN"
        year_frame["destination_iso3"] = "USA"
        year_frame["tariff_exposure"] = (
            year_frame["china_import_share_2017"] * year_frame["tariff_rate"]
        )
        rows.extend(year_frame[EXPOSURE_COLUMNS].to_dict("records"))

    return pd.DataFrame(rows, columns=EXPOSURE_COLUMNS)


def build_configured_exposure(
    panel: pd.DataFrame,
    years: list[int],
    census_path: Path,
    china_census_path: Path,
    baci_path: Path,
    exposure_year: int,
) -> tuple[pd.DataFrame, str, dict[str, Any]]:
    full_status = census_status_for_path(census_path, exposure_year)
    if full_status.get("full_origin_ready"):
        census_stats = load_census_stats(census_path, exposure_year)
        return build_exposure(panel, census_stats, years), "full_census_hs10", full_status

    census_china = load_census_china_hts10(china_census_path, exposure_year)
    baci_stats = load_baci_us_hs6_imports(baci_path, exposure_year)
    exposure = build_hybrid_exposure(panel, census_china, baci_stats, years)
    details = {
        "preferred_full_census": full_status,
        "china_hs10_path": str(china_census_path),
        "baci_hs6_path": str(baci_path),
        "census_china_import_total_2017": float(
            census_china["census_china_import_value_2017"].sum()
        ),
        "baci_china_import_total_2017": float(
            baci_stats["baci_china_import_value_2017"].sum()
        ),
        "baci_total_us_imports_2017": float(
            baci_stats["baci_total_us_import_value_2017"].sum()
        ),
        "hs6_baci_aliases": HS6_BACI_ALIASES,
        "hs6_baci_alias_basis": (
            "CEPII BACI 2710 aggregate plus the chapter 44 successor subheadings "
            "specified in 83 FR 49153"
        ),
        "method": (
            "BACI HS6 China/total-USA import share multiplied by a Census-China-HTS10-"
            "import-weighted statutory tariff rate within HS6; all product codes use HS2017"
        ),
    }
    return exposure, "baci_hs2017_with_census_china_hts10_weights", details


def validate_exposure(exposure: pd.DataFrame) -> None:
    if exposure.empty:
        raise RuntimeError("No HS6 exposure rows were generated.")
    if exposure.duplicated(["hs6", "year"]).any():
        raise ValueError("section301_hs6_exposure has duplicate hs6/year keys.")
    if not exposure["china_import_share_2017"].between(0, 1).all():
        raise ValueError("china_import_share_2017 must be in [0, 1].")
    if not exposure["tariff_rate"].between(0, 1).all():
        raise ValueError("tariff_rate must be in [0, 1].")
    tariff_flag_mismatch = (~exposure["tariffed_product"]) & (
        exposure["tariff_rate"].fillna(0) > 0
    )
    if tariff_flag_mismatch.any():
        sample = exposure.loc[
            tariff_flag_mismatch, ["year", "hs6", "tariffed_product", "tariff_rate"]
        ].head(20)
        raise ValueError(
            "A positive tariff_rate requires tariffed_product=true. Sample mismatches: "
            f"{sample.to_dict('records')}"
        )
    computed = exposure["china_import_share_2017"] * exposure["tariff_rate"]
    mismatch = (computed - exposure["tariff_exposure"]).abs() > 1e-12
    if mismatch.fillna(False).any():
        raise ValueError("tariff_exposure does not equal china_import_share_2017 * tariff_rate.")


def write_exposure(exposure: pd.DataFrame, output_path: Path, overwrite: bool) -> None:
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"{output_path} exists. Re-run with --overwrite to replace it.")
    if output_path.exists():
        output_path.unlink()
    table = pa.Table.from_pandas(exposure[EXPOSURE_COLUMNS], schema=exposure_schema(), preserve_index=False)
    pq.write_table(table, output_path, compression="snappy")


def configured_years(time_windows: dict[str, Any]) -> list[int]:
    start = int(time_windows["pre_period"]["start"])
    end = int(time_windows["post_period"]["end"])
    return list(range(start, end + 1))


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    config_dir = project_root / "configs"
    data_versions = load_yaml(config_dir / "data_versions.yaml")
    time_windows = load_yaml(config_dir / "time_windows.yaml")

    section_config = data_versions.get("ustr_section301", {})
    raw_dir = (project_root / section_config.get("raw_dir", "data/raw/ustr_section301/")).resolve()
    batch_usage = section_config.get("batch2_usage", {})
    output_dir = (project_root / batch_usage.get("output_dir", "data/interim/policy/")).resolve()
    if args.check_config or args.process_only or args.exposure_only:
        raw_dirs = raw_dir_paths(raw_dir)
    else:
        raw_dirs = ensure_dirs(raw_dir, None if args.download_only else output_dir)
    source_pages = source_pages_from_config(data_versions)
    years = configured_years(time_windows)
    census_path = (project_root / batch_usage.get("census_hs10_imports", "data/interim/trade/us_imports_hs10_monthly.parquet")).resolve()
    china_census_path = (
        project_root
        / batch_usage.get(
            "china_hs10_imports",
            "data/interim/trade/us_imports_hs10_monthly.parquet",
        )
    ).resolve()
    baci_path = (
        project_root
        / batch_usage.get(
            "baci_hs6_imports",
            "data/interim/trade/baci_hs17_us_imports_2017.parquet",
        )
    ).resolve()
    configured_universes = batch_usage.get("hts10_universes")
    if isinstance(configured_universes, dict) and configured_universes:
        hts_universe_paths = {}
        for list_id, configured_paths in configured_universes.items():
            relative_paths = configured_paths if isinstance(configured_paths, list) else [configured_paths]
            hts_universe_paths[str(list_id)] = [
                (project_root / relative_path).resolve() for relative_path in relative_paths
            ]
    else:
        hts_universe_paths = {
            "default": [
                (
                    project_root
                    / batch_usage.get(
                        "hts10_universe",
                        "data/raw/usitc_hts/2017/hts_2017_preliminary_csv.csv",
                    )
                ).resolve()
            ]
        }
    exposure_year = int(batch_usage.get("exposure_year", 2017))

    output_paths = {
        "hts10_list_panel": output_dir / "section301_hts10_list_panel.parquet",
        "hs6_exposure": output_dir / "section301_hs6_exposure.parquet",
        "summary": output_dir / "section301_build_summary.json",
        "audit": output_dir / "section301_hts10_expansion_audit.csv",
    }

    census_status = census_status_for_path(census_path, exposure_year)

    if args.check_config:
        summary = {
            "raw_dir": str(raw_dir),
            "raw_subdirs": {key: str(path) for key, path in raw_dirs.items()},
            "output_dir": str(output_dir),
            "source_pages": source_pages,
            "years": years,
            "exposure_year": exposure_year,
            "hts10_universes": {
                list_id: [
                    {"path": str(path), "exists": path.exists()} for path in paths
                ]
                for list_id, paths in hts_universe_paths.items()
            },
            "outputs": {key: str(value) for key, value in output_paths.items()},
            "census_status": census_status,
            "hybrid_exposure_inputs": {
                "china_hs10_imports": {
                    "path": str(china_census_path),
                    "exists": china_census_path.exists(),
                },
                "baci_hs6_imports": {
                    "path": str(baci_path),
                    "exists": baci_path.exists(),
                },
            },
        }
        return summary

    if args.exposure_only:
        if not output_paths["hts10_list_panel"].exists():
            raise FileNotFoundError(
                f"Missing HTS10 panel for exposure-only build: {output_paths['hts10_list_panel']}"
            )
        panel = pq.read_table(output_paths["hts10_list_panel"]).to_pandas()
        validate_panel(panel)
        exposure, exposure_input_mode, exposure_input_details = build_configured_exposure(
            panel,
            years,
            census_path,
            china_census_path,
            baci_path,
            exposure_year,
        )
        validate_exposure(exposure)
        output_dir.mkdir(parents=True, exist_ok=True)
        write_exposure(exposure, output_paths["hs6_exposure"], args.overwrite)
        summary = {
            "raw_dir": str(raw_dir),
            "output_dir": str(output_dir),
            "mode": "exposure_only",
            "panel_rows": int(len(panel)),
            "exposure_rows": int(len(exposure)),
            "exposure_input_mode": exposure_input_mode,
            "exposure_input_details": exposure_input_details,
            "outputs": {key: str(value) for key, value in output_paths.items()},
            "census_status": census_status_for_path(census_path, exposure_year),
            "schedule_scope": {
                "gross_statutory_initial_actions": True,
                "historical_exclusions_applied": False,
                "review_2024_in_hs2017_exposure": False,
            },
        }
        output_paths["summary"].write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary

    manifest = load_manifest(raw_dirs["metadata"] / "section301_source_manifest.json")
    if not args.process_only:
        manifest = download_sources(raw_dirs, source_pages, args.max_links_per_page)

    if args.download_only:
        manifest_name = (
            "section301_source_manifest_diagnostic.json"
            if args.max_links_per_page > 0
            else "section301_source_manifest.json"
        )
        return {
            "raw_dir": str(raw_dir),
            "manifest": str((raw_dirs["metadata"] / manifest_name).as_posix()),
            "manifest_mode": "diagnostic_partial" if args.max_links_per_page > 0 else "complete_requested",
            "manifest_entries": len(manifest),
        }

    if not manifest and not (raw_dirs["metadata"] / "section301_notice_codes.csv").exists():
        raise RuntimeError(
            "No Section 301 raw manifest or manual official code table found. "
            "Run without --process-only to download official source files first."
        )

    manual_rows = manual_code_rows(raw_dirs)
    if args.allow_text_extraction:
        extracted_rows, extraction_audit = extracted_code_rows(manifest)
    else:
        extracted_rows, extraction_audit = [], []
    source_rows = manual_rows + extracted_rows
    if not source_rows:
        if not args.allow_text_extraction:
            raise RuntimeError(
                "No manual official code table was found at "
                f"{(raw_dirs['metadata'] / 'section301_notice_codes.csv').as_posix()}. "
                "Automatic text extraction is disabled by default because it is diagnostic and may be incomplete."
            )
        raise RuntimeError(
            "No tariff code rows were extracted. Add official extracted codes to "
            f"{(raw_dirs['metadata'] / 'section301_notice_codes.csv').as_posix()} or inspect the downloaded notices."
        )

    hts_universes = load_usitc_hts_universes(hts_universe_paths)
    expanded, expansion_audit = expand_to_hts10(source_rows, hts_universes)
    output_dir.mkdir(parents=True, exist_ok=True)
    if not expansion_audit.empty:
        expansion_audit.to_csv(output_paths["audit"], index=False)
    elif output_paths["audit"].exists() and args.overwrite:
        output_paths["audit"].unlink()

    panel = add_derived_events(expanded)
    panel["source_code_level"] = panel["source_code_level"].astype("int8")
    panel["exclusion_flag"] = panel["exclusion_flag"].astype(bool)
    panel["rate_adjustment_applied"] = panel["rate_adjustment_applied"].astype(bool)
    panel = panel.drop_duplicates(PANEL_COLUMNS).sort_values(["hts10", "effective_date", "list_id"])
    validate_panel(panel)
    write_panel(panel, output_paths["hts10_list_panel"], args.overwrite)

    exposure = pd.DataFrame(columns=EXPOSURE_COLUMNS)
    exposure_status = "skipped_by_panel_only"
    exposure_input_mode = "not_requested"
    exposure_input_details: dict[str, Any] = {}
    if not args.panel_only:
        exposure, exposure_input_mode, exposure_input_details = build_configured_exposure(
            panel,
            years,
            census_path,
            china_census_path,
            baci_path,
            exposure_year,
        )
        validate_exposure(exposure)
        write_exposure(exposure, output_paths["hs6_exposure"], args.overwrite)
        exposure_status = "written"

    extraction_audit_path = output_dir / "section301_extraction_audit.csv"
    if extraction_audit:
        pd.DataFrame(extraction_audit).to_csv(extraction_audit_path, index=False)

    summary = {
        "raw_dir": str(raw_dir),
        "output_dir": str(output_dir),
        "mode": "panel_only" if args.panel_only else "panel_and_exposure",
        "manifest_entries": len(manifest),
        "manual_code_rows": len(manual_rows),
        "extracted_code_rows": len(extracted_rows),
        "text_extraction_enabled": bool(args.allow_text_extraction),
        "extraction_audit_rows": len(extraction_audit),
        "expansion_audit_rows": int(len(expansion_audit)),
        "panel_rows": int(len(panel)),
        "exposure_rows": int(len(exposure)),
        "exposure_status": exposure_status,
        "exposure_input_mode": exposure_input_mode,
        "exposure_input_details": exposure_input_details,
        "hts10_universes": {
            list_id: [str(path) for path in paths]
            for list_id, paths in hts_universe_paths.items()
        },
        "outputs": {key: str(value) for key, value in output_paths.items()},
        "census_status": census_status_for_path(census_path, exposure_year),
        "schedule_scope": {
            "gross_statutory_initial_actions": True,
            "historical_exclusions_applied": False,
            "review_2024_in_hs2017_exposure": False,
        },
    }
    if extraction_audit:
        summary["outputs"]["extraction_audit"] = str(extraction_audit_path)
    output_paths["summary"].write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive and process official USTR Section 301 China tariff notices.")
    parser.add_argument("--project-root", default=".", help="Project root containing configs/ and data/.")
    parser.add_argument("--download-only", action="store_true", help="Archive official source files but do not write parquet outputs.")
    parser.add_argument("--process-only", action="store_true", help="Process existing raw archive without downloading.")
    parser.add_argument("--panel-only", action="store_true", help="Write only the HTS10 list panel and skip HS6 exposure.")
    parser.add_argument(
        "--exposure-only",
        action="store_true",
        help="Build HS6 exposure from an existing HTS10 panel and the configured Census/BACI inputs.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace generated interim outputs. Raw downloads are never overwritten.")
    parser.add_argument("--check-config", action="store_true", help="Print planned paths and source URLs without network or processing.")
    parser.add_argument(
        "--allow-text-extraction",
        action="store_true",
        help=(
            "Allow diagnostic HTS code extraction from downloaded notice text. "
            "By default, processing requires metadata/section301_notice_codes.csv."
        ),
    )
    parser.add_argument(
        "--max-links-per-page",
        type=int,
        default=0,
        help=(
            "Diagnostic cap for linked official files per seeded USTR page. "
            "Use 0 for a complete requested archive. Capped runs write a diagnostic manifest only."
        ),
    )
    args = parser.parse_args(argv)
    if args.download_only and (args.panel_only or args.exposure_only):
        parser.error("--download-only cannot be combined with --panel-only or --exposure-only.")
    if args.exposure_only and args.panel_only:
        parser.error("--panel-only and --exposure-only are mutually exclusive.")
    if args.check_config and (args.download_only or args.process_only or args.panel_only or args.exposure_only):
        parser.error("--check-config cannot be combined with processing or download modes.")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = build(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr, flush=True)
        return 1
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
