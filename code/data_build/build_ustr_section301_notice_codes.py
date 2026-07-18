from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader


OUTPUT_COLUMNS = [
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

# The formal Annex A tables govern. Page numbers are one-based Federal Register
# PDF pages, not printed Federal Register page numbers.
BASE_LIST_SPECS = [
    {
        "list_id": "list1",
        "pdf": "list1/list1_002_2018-13248.pdf",
        "pages": range(5, 10),
        "expected_full_codes": 818,
        "hts_universe": "data/raw/usitc_hts/2018/hts_2018_revision_8.csv",
        "hts_universe_url": (
            "https://www.usitc.gov/sites/default/files/tata/hts/"
            "hts_2018_revision_8_1_csv.csv"
        ),
        "effective_date": "2018-07-06",
        "rate": 0.25,
        "notice_date": "2018-06-20",
        "source_notice": "83 FR 28710, List 1 Notice of Action, Annex A",
        "source_url": "https://ustr.gov/sites/default/files/2018-13248.pdf",
    },
    {
        "list_id": "list2",
        "pdf": "list2/list2_002_2018-17709.pdf",
        "pages": range(4, 6),
        "expected_full_codes": 279,
        "hts_universe": "data/raw/usitc_hts/2018/hts_2018_revision_10_data.csv",
        "hts_universe_url": (
            "https://www.usitc.gov/sites/default/files/tata/hts/"
            "hts_2018_revisions_10_data.csv"
        ),
        "effective_date": "2018-08-23",
        "rate": 0.25,
        "notice_date": "2018-08-16",
        "source_notice": "83 FR 40823, List 2 Notice of Action, Annex A",
        "source_url": (
            "https://ustr.gov/sites/default/files/enforcement/301Investigations/"
            "2018-17709.pdf"
        ),
    },
    {
        "list_id": "list3",
        "pdf": "list3/list3_003_83_20FR_2047974.pdf",
        "pages": range(4, 29),
        "expected_full_codes": 5734,
        "hts_universe": "data/raw/usitc_hts/2018/hts_2018_revision_12_data.csv",
        "hts_universe_url": (
            "https://www.usitc.gov/sites/default/files/tata/hts/"
            "hts_2018_revision_12_data.csv"
        ),
        "effective_date": "2018-09-24",
        "rate": 0.10,
        "notice_date": "2018-09-21",
        "source_notice": "83 FR 47974, List 3 Notice of Action, Annex A",
        "source_url": (
            "https://ustr.gov/sites/default/files/enforcement/301Investigations/"
            "83%20FR%2047974.pdf"
        ),
    },
    {
        "list_id": "list4a",
        "pdf": "list4/list4_002_Notice_of_Modification__28List_4A_and_List_4B_29.pdf",
        "pages": range(4, 26),
        "expected_full_codes": 3229,
        "hts_universe": "data/raw/usitc_hts/2019/hts_2019_revision_12_data.csv",
        "hts_universe_url": (
            "https://www.usitc.gov/sites/default/files/tata/hts/htsdata_4.csv"
        ),
        "effective_date": "2019-09-01",
        "rate": 0.15,
        "notice_date": "2019-08-20",
        "source_notice": (
            "84 FR 43304 Annex A, as modified by 84 FR 45821, List 4A"
        ),
        "source_url": (
            "https://ustr.gov/sites/default/files/enforcement/301Investigations/"
            "Notice_of_Modification_%28List_4A_and_List_4B%29.pdf"
        ),
    },
]

# These Annex provisions cover only part of an HTS8 subheading. They are
# expanded against the action-date HTS10 universe and the explicit statistical-
# reporting-number exclusions are removed.
PARTIAL_RULES = {
    "list3": {
        "29319090": {"2931909051"},
        "85176200": {"8517620090"},
        "94016140": {"9401614001"},
        "94016960": {"9401696001"},
        "94017100": {"9401710001", "9401710005", "9401710006", "9401710007"},
        "94017900": {"9401790001", "9401790002", "9401790003", "9401790004"},
        "94018020": {"9401802001"},
        "94018040": {"9401804001"},
        "94018060": {"9401806021", "9401806023"},
        "94037040": {"9403704003"},
        "94037080": {"9403708003"},
    },
    "list4a": {
        "49019900": {"4901990040"},
        "85176200": {"8517620010", "8517620020"},
        "94016960": {"9401696011", "9401696031"},
        "94017100": {
            "9401710001",
            "9401710005",
            "9401710006",
            "9401710008",
            "9401710011",
            "9401710031",
        },
    },
}

# Paragraph C of 83 FR 49153 removed these two Chapter 3 subheadings
# retroactively to the List 3 effective date.
REMOVED_SOURCE_CODES = {"list3": {"03048110", "03048150"}}


@dataclass(frozen=True)
class HtsUniverse:
    codes: tuple[str, ...]
    sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_code(value: Any) -> str:
    return "".join(character for character in str(value) if character.isdigit())


def load_hts_universe(path: Path) -> HtsUniverse:
    frame = pd.read_csv(path, dtype="string")
    if "HTS Number" not in frame.columns:
        raise ValueError(f"{path} is missing the HTS Number column.")
    raw_codes = frame["HTS Number"].fillna("").map(clean_code)
    ten_digit = {
        code
        for code in raw_codes
        if len(code) == 10 and code.isdigit() and int(code[:2]) < 98
    }
    eight_digit = {
        code
        for code in raw_codes
        if len(code) == 8 and code.isdigit() and int(code[:2]) < 98
    }
    terminal_eight_digit = {
        code for code in eight_digit if not any(item.startswith(code) for item in ten_digit)
    }
    codes = sorted(ten_digit | {f"{code}00" for code in terminal_eight_digit})
    if len(codes) < 15_000:
        raise ValueError(f"{path} has only {len(codes)} product-level HTS10 codes.")
    return HtsUniverse(tuple(codes), sha256_file(path))


def pdf_page_text(path: Path, page_numbers: range) -> str:
    reader = PdfReader(path)
    if max(page_numbers) > len(reader.pages):
        raise ValueError(f"{path} has only {len(reader.pages)} pages.")
    return "\n".join(reader.pages[number - 1].extract_text() or "" for number in page_numbers)


def extract_full_codes(list_id: str, text: str) -> list[str]:
    pattern = re.compile(r"(?<!\d)(\d{4}\s*\.\s*\d{2}\s*\.\s*\d{2})(?!\d)")
    codes = [clean_code(match) for match in pattern.findall(text)]
    codes = [code for code in codes if int(code[:2]) < 98]

    if list_id == "list1":
        # The Annex text layer truncates the final 9033.00.90 entry to 9033.00.
        # The notice's product-description table confirms the intended HTS8.
        if "9033.00" not in text:
            raise ValueError("List 1 Annex no longer contains the expected 9033.00 line.")
        codes.append("90330090")

    unique = sorted(set(codes))
    if len(unique) != len(codes):
        raise ValueError(f"{list_id} Annex extraction produced duplicate product codes.")
    return unique


def expand_partial_rules(
    list_id: str,
    universe: HtsUniverse,
) -> tuple[list[str], list[dict[str, Any]]]:
    expanded: list[str] = []
    audit: list[dict[str, Any]] = []
    for prefix, exclusions in PARTIAL_RULES.get(list_id, {}).items():
        universe_codes = [code for code in universe.codes if code.startswith(prefix)]
        if not universe_codes:
            raise ValueError(f"No 2017 HTS10 codes found for partial {list_id} prefix {prefix}.")
        included = [code for code in universe_codes if code not in exclusions]
        if not included:
            raise ValueError(f"Partial {list_id} prefix {prefix} has no included HTS10 codes.")
        expanded.extend(included)
        audit.append(
            {
                "list_id": list_id,
                "source_hts8": prefix,
                "universe_hts10_count": len(universe_codes),
                "included_hts10_count": len(included),
                "excluded_hts10_count_in_action_universe": len(set(universe_codes) & exclusions),
                "notice_exclusions_absent_from_action_universe": ";".join(
                    sorted(exclusions - set(universe_codes))
                ),
            }
        )
    if len(expanded) != len(set(expanded)):
        raise ValueError(f"Partial {list_id} rules produced duplicate HTS10 codes.")
    return sorted(expanded), audit


def output_row(code: str, spec: dict[str, Any], raw_dir: Path) -> dict[str, Any]:
    return {
        "source_code": code,
        "list_id": spec["list_id"],
        "effective_date": spec["effective_date"],
        "additional_tariff_rate": spec["rate"],
        "source_notice": spec["source_notice"],
        "source_url": spec["source_url"],
        "source_file": (raw_dir / spec["pdf"]).resolve().as_posix(),
        "notice_date": spec["notice_date"],
        "exclusion_flag": False,
        "exclusion_start": "",
        "exclusion_end": "",
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    project_root = Path(args.project_root).resolve()
    raw_dir = project_root / "data" / "raw" / "ustr_section301"
    output_path = raw_dir / "metadata" / "section301_notice_codes.csv"
    audit_path = raw_dir / "metadata" / "section301_notice_code_build_audit.json"

    rows: list[dict[str, Any]] = []
    list_summary: dict[str, Any] = {}
    partial_audit: list[dict[str, Any]] = []

    for spec in BASE_LIST_SPECS:
        hts_path = project_root / spec["hts_universe"]
        universe = load_hts_universe(hts_path)
        pdf_path = raw_dir / spec["pdf"]
        if not pdf_path.exists():
            raise FileNotFoundError(pdf_path)
        text = pdf_page_text(pdf_path, spec["pages"])
        full_codes = extract_full_codes(spec["list_id"], text)
        if len(full_codes) != spec["expected_full_codes"]:
            raise ValueError(
                f"{spec['list_id']} produced {len(full_codes)} full codes; "
                f"expected {spec['expected_full_codes']}."
            )
        removed_codes = REMOVED_SOURCE_CODES.get(spec["list_id"], set())
        missing_removed_codes = removed_codes - set(full_codes)
        if missing_removed_codes:
            raise ValueError(
                f"{spec['list_id']} is missing conforming-amendment removals: "
                f"{sorted(missing_removed_codes)}"
            )
        full_codes = [code for code in full_codes if code not in removed_codes]
        partial_codes, partial_detail = expand_partial_rules(spec["list_id"], universe)
        partial_audit.extend(partial_detail)
        source_codes = full_codes + partial_codes
        rows.extend(output_row(code, spec, raw_dir) for code in source_codes)
        list_summary[spec["list_id"]] = {
            "formal_annex_pages": [min(spec["pages"]), max(spec["pages"])],
            "full_source_codes": len(full_codes),
            "source_codes_removed_by_83_fr_49153": sorted(removed_codes),
            "partial_rule_count": len(PARTIAL_RULES.get(spec["list_id"], {})),
            "partial_expanded_hts10_codes": len(partial_codes),
            "output_source_rows": len(source_codes),
            "source_pdf_sha256": sha256_file(pdf_path),
            "hts_universe_path": hts_path.resolve().as_posix(),
            "hts_universe_url": spec["hts_universe_url"],
            "hts_universe_sha256": universe.sha256,
            "hts_universe_product_codes": len(universe.codes),
        }

    keys = [(row["source_code"], row["list_id"], row["effective_date"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Generated notice-code table has duplicate code/list/date keys.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(f"{output_path} exists. Re-run with --overwrite.")
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "source": "Official USTR/Federal Register final action Annex tables",
        "output": output_path.resolve().as_posix(),
        "output_sha256": sha256_file(output_path),
        "rows": len(rows),
        "lists": list_summary,
        "partial_rules": partial_audit,
        "scope_note": (
            "The table defines statutory base-list coverage. Product-description exclusions "
            "are not treated as whole-code exclusions. List 4B is excluded because its duty "
            "was suspended before the scheduled effective date."
        ),
    }
    audit_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the verified Section 301 base-list code table from official Annex pages."
    )
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    summary = build(parse_args())
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
