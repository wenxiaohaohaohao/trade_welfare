from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import pdfplumber
import pyarrow as pa
import pyarrow.parquet as pq


NOTICE_URL = "https://www.federalregister.gov/documents/2024/09/18/2024-21217/notice-of-modification-chinas-acts-policies-and-practices-related-to-technology-transfer"
EFFECTIVE_DATE = "2024-09-27"
CODE_PATTERN = re.compile(r"^\d{4}\.\d{2}\.\d{2,4}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def notice_path(project_root: Path) -> Path:
    matches = sorted(
        (project_root / "data" / "raw" / "ustr_section301" / "four_year_review").glob("*76581*")
    )
    if len(matches) != 1:
        raise FileNotFoundError(f"Expected one 89 FR 76581 PDF, found {matches}")
    return matches[0]


def extract_description(words: list[dict[str, Any]], start: float, end: float) -> str:
    selected = [
        word["text"]
        for word in words
        if start - 0.5 <= float(word["top"]) < end - 0.5
        and 140 <= float(word["x0"]) < 490
        and not set(word["text"]) <= {"."}
    ]
    return " ".join(selected).strip()


def extract_rows(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with pdfplumber.open(path) as pdf:
        for page_index in range(9, 20):
            words = pdf.pages[page_index].extract_words()
            code_words = [
                word
                for word in words
                if float(word["x0"]) < 110 and CODE_PATTERN.fullmatch(word["text"])
            ]
            code_words.sort(key=lambda word: float(word["top"]))
            for index, code_word in enumerate(code_words):
                start = float(code_word["top"])
                end = (
                    float(code_words[index + 1]["top"])
                    if index + 1 < len(code_words)
                    else float(pdf.pages[page_index].height) - 35
                )
                rates = [
                    word
                    for word in words
                    if start - 0.5 <= float(word["top"]) < end - 0.5
                    and 490 <= float(word["x0"]) <= 525
                    and word["text"] in {"25", "50", "100"}
                ]
                years = [
                    word
                    for word in words
                    if start - 0.5 <= float(word["top"]) < end - 0.5
                    and 535 <= float(word["x0"]) <= 580
                    and word["text"] in {"2024", "2025", "2026"}
                ]
                pairs: list[tuple[int, int]] = []
                for rate_word in rates:
                    candidates = sorted(
                        years,
                        key=lambda year_word: abs(float(year_word["top"]) - float(rate_word["top"])),
                    )
                    if candidates and abs(float(candidates[0]["top"]) - float(rate_word["top"])) < 1.5:
                        pairs.append((int(candidates[0]["text"]), int(rate_word["text"])))
                rates_2024 = [rate for year, rate in pairs if year == 2024]
                if not rates_2024:
                    continue
                if len(set(rates_2024)) != 1:
                    raise ValueError(f"Ambiguous 2024 rate for {code_word['text']}: {rates_2024}")
                hts = code_word["text"].replace(".", "")
                rows.append(
                    {
                        "hts_code": hts,
                        "hts_code_level": len(hts),
                        "section301_rate": rates_2024[0] / 100.0,
                        "effective_date": EFFECTIVE_DATE,
                        "timing_year": 2024,
                        "whole_code_applicable": hts != "90183100",
                        "scope_note": (
                            "excludes enteral syringes described in 9018310080 before 2026"
                            if hts == "90183100"
                            else "whole published HTS subheading/statistical reporting number"
                        ),
                        "product_description": extract_description(words, start, end),
                        "source_notice": path.name,
                        "source_page": page_index + 1,
                        "source_url": NOTICE_URL,
                    }
                )

    rows.append(
        {
            "hts_code": "84261900",
            "hts_code_level": 8,
            "section301_rate": 0.25,
            "effective_date": EFFECTIVE_DATE,
            "timing_year": 2024,
            "whole_code_applicable": False,
            "scope_note": "ship-to-shore gantry cranes only; contract exception in Annex A applies",
            "product_description": "Ship-to-shore gantry cranes provided for in HTSUS 8426.19.00",
            "source_notice": path.name,
            "source_page": 12,
            "source_url": NOTICE_URL,
        }
    )
    frame = pd.DataFrame(rows).drop_duplicates("hts_code", keep="last")
    frame = frame.sort_values("hts_code").reset_index(drop=True)
    return frame


def validate(frame: pd.DataFrame) -> None:
    if len(frame) < 300:
        raise ValueError(f"Only {len(frame)} 2024 review HTS rows were extracted")
    if frame["hts_code"].duplicated().any():
        raise ValueError("2024 review table contains duplicate HTS codes")
    known = {
        "85079040": 0.25,
        "87038000": 1.00,
        "85414200": 0.50,
        "90183100": 1.00,
        "84261900": 0.25,
    }
    lookup = frame.set_index("hts_code")["section301_rate"].to_dict()
    mismatches = {code: (lookup.get(code), rate) for code, rate in known.items() if lookup.get(code) != rate}
    if mismatches:
        raise ValueError(f"Known 2024 tariff rows failed validation: {mismatches}")
    if not frame["section301_rate"].isin([0.25, 0.50, 1.00]).all():
        raise ValueError("2024 review table contains an unexpected tariff rate")


def run(project_root: Path, overwrite: bool) -> dict[str, Any]:
    source = notice_path(project_root)
    frame = extract_rows(source)
    validate(frame)
    raw_csv = project_root / "data" / "raw" / "ustr_section301" / "metadata" / "section301_2024_review_codes.csv"
    output = project_root / "data" / "interim" / "policy" / "section301_2024_review_codes.parquet"
    for path in [raw_csv, output]:
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")
        path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(raw_csv, index=False)
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), output, compression="zstd")
    summary = {
        "source_notice": str(source.relative_to(project_root)),
        "source_sha256": sha256(source),
        "source_url": NOTICE_URL,
        "effective_date": EFFECTIVE_DATE,
        "rows": len(frame),
        "whole_code_rows": int(frame["whole_code_applicable"].sum()),
        "description_scoped_rows": int((~frame["whole_code_applicable"]).sum()),
        "rates": frame["section301_rate"].value_counts().sort_index().to_dict(),
        "raw_csv": str(raw_csv.relative_to(project_root)),
        "raw_csv_sha256": sha256(raw_csv),
        "output": str(output.relative_to(project_root)),
        "output_sha256": sha256(output),
        "validation": "passed",
        "usage_rule": "Do not merge by HS6 to the 2017 exposure panel without an explicit nomenclature and scope treatment.",
    }
    summary_path = output.with_name("section301_2024_review_codes_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract the exact 2024 Section 301 review rate table from 89 FR 76581.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    summary = run(args.project_root.resolve(), args.overwrite)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
