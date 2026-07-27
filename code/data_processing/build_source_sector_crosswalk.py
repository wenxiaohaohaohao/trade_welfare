from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from build_hs_revision_bridge import load_yaml, sha256


def mapping_record(
    analysis_sector: str | None,
    mapping_status: str,
    mapping_rule: str,
    first_round_exclusion: str | None = None,
    proxy_analysis_sector: str | None = None,
    source_granularity_note: str | None = None,
) -> dict[str, Any]:
    eligible = analysis_sector is not None
    return {
        "analysis_sector": analysis_sector,
        "mapping_status": mapping_status,
        "mapping_rule": mapping_rule,
        "first_round_exclusion": first_round_exclusion,
        "proxy_analysis_sector": proxy_analysis_sector,
        "is_main_join_eligible": eligible,
        "mapping_weight": 1.0 if eligible else None,
        "source_granularity_note": source_granularity_note,
    }


def classify_oecd(code: str, config: dict[str, Any]) -> dict[str, Any]:
    rules = config["oecd_rules"]
    if code in rules["priority_exact"]:
        note = None
        if code in rules["medical_device_container_codes"]:
            note = rules["interpretation"]
        return mapping_record(
            rules["priority_exact"][code],
            "mapped_priority_sector",
            "oecd_exact_priority",
            source_granularity_note=note,
        )
    if code in rules["excluded_exact"]:
        return mapping_record(
            None,
            "first_round_excluded",
            "oecd_exact_exclusion",
            first_round_exclusion=rules["excluded_exact"][code],
        )
    for prefix, exclusion in rules["excluded_prefixes"].items():
        if code.startswith(prefix):
            return mapping_record(
                None,
                "first_round_excluded",
                "oecd_prefix_exclusion",
                first_round_exclusion=exclusion,
            )
    if code.startswith(rules["other_manufacturing_prefix"]):
        note = rules["interpretation"] if code in rules["medical_device_container_codes"] else None
        return mapping_record(
            "other_manufacturing",
            "mapped_other_manufacturing",
            "oecd_manufacturing_catch_all",
            source_granularity_note=note,
        )
    return mapping_record(None, "outside_manufacturing", "oecd_nonmanufacturing")


def classify_bea(label: str, config: dict[str, Any]) -> dict[str, Any]:
    rules = config["bea_rules"]
    if label in rules["priority_exact"]:
        note = rules["medical_device_limitation"] if label == "Computers and electronic products" else None
        return mapping_record(
            rules["priority_exact"][label],
            "mapped_priority_sector",
            "bea_exact_priority",
            source_granularity_note=note,
        )
    if label in rules["other_manufacturing_exact"]:
        return mapping_record(
            "other_manufacturing",
            "mapped_other_manufacturing",
            "bea_exact_other_manufacturing",
        )
    if label in rules["first_round_excluded_exact"]:
        return mapping_record(
            None,
            "first_round_excluded",
            "bea_exact_exclusion",
            first_round_exclusion=rules["first_round_excluded_exact"][label],
        )
    if label in rules["aggregate_or_residual_exact"]:
        return mapping_record(
            None,
            "aggregate_or_residual_not_join_eligible",
            "bea_aggregate_or_residual",
            source_granularity_note="Published aggregate or residual industry would duplicate or mix detailed industries.",
        )
    if label in rules["ambiguous_exact"]:
        details = rules["ambiguous_exact"][label]
        return mapping_record(
            None,
            "ambiguous_mixed_sector_no_weight",
            "bea_mixed_industry",
            proxy_analysis_sector=details.get("proxy_analysis_sector"),
            source_granularity_note=details["interpretation"],
        )
    return mapping_record(None, "outside_manufacturing", "bea_nonmanufacturing")


def classify_mexico(level: str, code: str, config: dict[str, Any]) -> dict[str, Any]:
    source = config["sources"]["mexico_fdi"]
    rules = config["mexico_rules"]
    if level in set(source["aggregate_levels"]):
        return mapping_record(
            None,
            "aggregate_sector_not_join_eligible",
            "mexico_aggregate_level",
            source_granularity_note=rules["interpretation"],
        )
    if level != source["canonical_join_level"]:
        return mapping_record(
            None,
            "unrecognized_sector_level",
            "mexico_unrecognized_level",
            source_granularity_note=f"Unrecognized Mexico sector level: {level}",
        )
    if code in rules["ambiguous_exact"]:
        return mapping_record(
            None,
            "ambiguous_mixed_sector_no_weight",
            "mexico_mixed_industry_group",
            source_granularity_note=rules["ambiguous_exact"][code]["interpretation"],
        )
    if code in rules["first_round_excluded_exact"]:
        return mapping_record(
            None,
            "first_round_excluded",
            "mexico_exact_exclusion",
            first_round_exclusion=rules["first_round_excluded_exact"][code],
        )
    for prefix, exclusion in rules["first_round_excluded_prefixes"].items():
        if code.startswith(prefix):
            return mapping_record(
                None,
                "first_round_excluded",
                "mexico_prefix_exclusion",
                first_round_exclusion=exclusion,
            )
    if code in rules["priority_exact"]:
        return mapping_record(
            rules["priority_exact"][code],
            "mapped_priority_sector",
            "mexico_exact_priority",
        )
    for prefix, sector in rules["priority_prefixes"].items():
        if code.startswith(prefix):
            return mapping_record(
                sector,
                "mapped_priority_sector",
                "mexico_prefix_priority",
            )
    if any(code.startswith(prefix) for prefix in rules["other_manufacturing_prefixes"]):
        return mapping_record(
            "other_manufacturing",
            "mapped_other_manufacturing",
            "mexico_manufacturing_catch_all",
        )
    return mapping_record(None, "outside_manufacturing", "mexico_nonmanufacturing")


def extract_source_sectors(project_root: Path, source: dict[str, Any]) -> pd.DataFrame:
    columns = [source["sector_code_field"]]
    for key in ["sector_label_field", "sector_level_field"]:
        if key in source:
            columns.append(source[key])
    frame = pq.read_table(project_root / source["path"], columns=columns).to_pandas()
    frame = frame.drop_duplicates().copy()
    code_field = source["sector_code_field"]
    frame["source_sector_code"] = frame[code_field].astype("string").str.strip()
    if "sector_label_field" in source:
        frame["source_sector_label"] = frame[source["sector_label_field"]].astype("string").str.strip()
    else:
        frame["source_sector_label"] = frame["source_sector_code"]
    if "sector_level_field" in source:
        frame["source_sector_level"] = frame[source["sector_level_field"]].astype("string").str.strip()
    else:
        frame["source_sector_level"] = source["sector_level"]
    return frame[["source_sector_level", "source_sector_code", "source_sector_label"]]


def build_crosswalk(project_root: Path, config: dict[str, Any]) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for source_id, source in config["sources"].items():
        sectors = extract_source_sectors(project_root, source)
        if source_id.startswith("oecd_"):
            mapped = sectors.apply(
                lambda row: classify_oecd(str(row["source_sector_code"]), config),
                axis=1,
                result_type="expand",
            )
        elif source_id.startswith("bea_"):
            mapped = sectors.apply(
                lambda row: classify_bea(str(row["source_sector_label"]), config),
                axis=1,
                result_type="expand",
            )
        elif source_id == "mexico_fdi":
            mapped = sectors.apply(
                lambda row: classify_mexico(
                    str(row["source_sector_level"]), str(row["source_sector_code"]), config
                ),
                axis=1,
                result_type="expand",
            )
        else:
            raise ValueError(f"No source-sector classifier for {source_id}")
        output = pd.concat([sectors, mapped], axis=1)
        output.insert(0, "source_name", source["source_name"])
        output["source_code_family"] = source["code_family"]
        output["mapping_version"] = config["version"]
        records.append(output)

    output = pd.concat(records, ignore_index=True)
    string_columns = [
        column
        for column in output.columns
        if column not in {"is_main_join_eligible", "mapping_weight"}
    ]
    for column in string_columns:
        output[column] = output[column].astype("string")
    output["is_main_join_eligible"] = output["is_main_join_eligible"].astype("bool")
    return output.sort_values(
        ["source_name", "source_sector_level", "source_sector_code"]
    ).reset_index(drop=True)


def safe_counts(series: pd.Series) -> dict[str, int]:
    return {
        "<NA>" if pd.isna(label) else str(label): int(count)
        for label, count in series.value_counts(dropna=False).sort_index().items()
    }


def validate_crosswalk(project_root: Path, config: dict[str, Any], output: pd.DataFrame) -> dict[str, Any]:
    failures: list[str] = []
    keys = ["source_name", "source_sector_level", "source_sector_code"]
    duplicate_keys = int(output.duplicated(keys).sum())
    if duplicate_keys:
        failures.append(f"source-sector crosswalk has {duplicate_keys} duplicate natural keys")
    missing_status = int(output["mapping_status"].isna().sum())
    if missing_status:
        failures.append(f"source-sector crosswalk has {missing_status} codes without explicit status")
    weight_rules_ok = bool(
        (output.loc[output["is_main_join_eligible"], "mapping_weight"] == 1.0).all()
        and output.loc[~output["is_main_join_eligible"], "mapping_weight"].isna().all()
    )
    if not weight_rules_ok:
        failures.append("eligible source-sector mappings do not have weight 1 or ineligible rows have a weight")
    eligibility_rules_ok = bool(
        (output["is_main_join_eligible"] == output["analysis_sector"].notna()).all()
    )
    if not eligibility_rules_ok:
        failures.append("main-join eligibility disagrees with analysis_sector missingness")
    ambiguous_weight_count = int(
        output.loc[
            output["mapping_status"].str.contains("ambiguous", na=False), "mapping_weight"
        ].notna().sum()
    )
    if ambiguous_weight_count:
        failures.append("ambiguous source-sector mappings received a numeric weight")

    observed_source_counts = safe_counts(output["source_name"])
    expected_source_counts: dict[str, int] = {}
    source_code_coverage: dict[str, dict[str, Any]] = {}
    for source_id, source in config["sources"].items():
        actual = extract_source_sectors(project_root, source)
        expected_source_counts[source["source_name"]] = len(actual)
        mapped = output[output["source_name"] == source["source_name"]]
        actual_keys = set(zip(actual["source_sector_level"], actual["source_sector_code"]))
        mapped_keys = set(zip(mapped["source_sector_level"], mapped["source_sector_code"]))
        missing = sorted(actual_keys - mapped_keys)
        extra = sorted(mapped_keys - actual_keys)
        source_code_coverage[source["source_name"]] = {
            "observed_code_count": len(actual_keys),
            "crosswalk_code_count": len(mapped_keys),
            "missing_codes": [list(item) for item in missing],
            "extra_codes": [list(item) for item in extra],
            "explicit_status_code_coverage_rate": (
                float(mapped["mapping_status"].notna().sum() / len(actual_keys)) if actual_keys else None
            ),
        }
        if missing or extra:
            failures.append(f"{source_id} observed sector universe differs from its crosswalk rows")

    support_matrix: dict[str, dict[str, bool]] = {}
    required_support = config["validation_rules"]["required_priority_support"]
    for source_name, required in required_support.items():
        observed = set(
            output.loc[
                (output["source_name"] == source_name)
                & (output["mapping_status"] == "mapped_priority_sector"),
                "analysis_sector",
            ].dropna()
        )
        support_matrix[source_name] = {
            sector: sector in observed for sector in required
        }
        missing_required = sorted(set(required) - observed)
        if missing_required:
            failures.append(f"{source_name} lacks required priority-sector support: {missing_required}")

    mexico = output[output["source_name"] == "mexico_fdi"]
    mexico_aggregate_safe = bool(
        (~mexico.loc[mexico["source_sector_level"].isin(["sector", "subsector"]), "is_main_join_eligible"]).all()
    )
    if not mexico_aggregate_safe:
        failures.append("Mexico sector/subsector aggregate rows are incorrectly join-eligible")
    bea_transport = output[
        output["source_name"].isin(["bea_mne", "bea_fdi"])
        & (output["source_sector_label"] == "Transportation equipment")
    ]
    bea_transport_safe = bool(
        len(bea_transport) == 2
        and (~bea_transport["is_main_join_eligible"]).all()
        and (bea_transport["proxy_analysis_sector"] == "autos").all()
        and bea_transport["mapping_weight"].isna().all()
    )
    if not bea_transport_safe:
        failures.append("BEA transportation equipment is not safely isolated as an unweighted autos proxy")
    mexico_3345 = mexico[mexico["source_sector_code"] == "3345"]
    mexico_3345_safe = bool(
        len(mexico_3345) == 1
        and mexico_3345.iloc[0]["mapping_status"] == "ambiguous_mixed_sector_no_weight"
        and not mexico_3345.iloc[0]["is_main_join_eligible"]
        and pd.isna(mexico_3345.iloc[0]["mapping_weight"])
    )
    if not mexico_3345_safe:
        failures.append("Mexico SCIAN 3345 is not safely isolated as an unweighted mixed sector")

    return {
        "validation_status": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "output_row_count": len(output),
        "duplicate_natural_key_count": duplicate_keys,
        "missing_explicit_status_count": missing_status,
        "mapping_weight_rules_pass": weight_rules_ok,
        "eligibility_rules_pass": eligibility_rules_ok,
        "ambiguous_numeric_weight_count": ambiguous_weight_count,
        "source_row_counts": observed_source_counts,
        "expected_source_row_counts": expected_source_counts,
        "source_code_coverage": source_code_coverage,
        "mapping_status_counts": safe_counts(output["mapping_status"]),
        "analysis_sector_counts": safe_counts(output["analysis_sector"]),
        "priority_support_matrix": support_matrix,
        "mexico_aggregate_levels_not_join_eligible": mexico_aggregate_safe,
        "bea_transportation_equipment_proxy_safe": bea_transport_safe,
        "mexico_3345_ambiguity_safe": mexico_3345_safe,
    }


def markdown_report(validation: dict[str, Any]) -> str:
    lines = [
        "# Source-Sector Crosswalk Validation",
        "",
        f"- Generated at UTC: `{validation['generated_at_utc']}`",
        f"- Output: `{validation['output_path']}`",
        f"- Validation status: **{validation['validation_status']}**",
        f"- Crosswalk rows: `{validation['output_row_count']}`",
        "",
        "## Source code coverage",
        "",
        "| Source | Observed codes | Crosswalk codes | Explicit-status coverage |",
        "|---|---:|---:|---:|",
    ]
    for source, record in validation["source_code_coverage"].items():
        lines.append(
            f"| `{source}` | {record['observed_code_count']} | {record['crosswalk_code_count']} | {record['explicit_status_code_coverage_rate']:.6%} |"
        )
    lines.extend(
        [
            "",
            "## Required safeguards",
            "",
            f"- Unique source-level-code keys: `{'yes' if validation['duplicate_natural_key_count'] == 0 else 'no'}`",
            f"- Eligible mappings have weight 1; all others have null weight: `{'yes' if validation['mapping_weight_rules_pass'] else 'no'}`",
            f"- Ambiguous mappings have no numeric weight: `{'yes' if validation['ambiguous_numeric_weight_count'] == 0 else 'no'}`",
            f"- Mexico sector/subsector aggregates excluded from the main join: `{'yes' if validation['mexico_aggregate_levels_not_join_eligible'] else 'no'}`",
            f"- BEA transportation equipment retained only as an autos proxy: `{'yes' if validation['bea_transportation_equipment_proxy_safe'] else 'no'}`",
            f"- Mexico SCIAN 3345 retained as an unweighted mixed sector: `{'yes' if validation['mexico_3345_ambiguity_safe'] else 'no'}`",
            "",
            "## Priority-sector support",
            "",
            "| Source | Directly supported priority sectors |",
            "|---|---|",
        ]
    )
    for source, support in validation["priority_support_matrix"].items():
        supported = [sector for sector, is_supported in support.items() if is_supported]
        lines.append(f"| `{source}` | {', '.join(supported)} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This crosswalk records what each published source can support at its actual industry granularity. It does not split coarse sectors with equal weights. OECD C26 and BEA computer/electronics cannot separately identify all medical devices. BEA transportation equipment is broader than autos and is therefore only a documented proxy. Mexico uses industry-group rows for the main join; its coexisting sector and subsector aggregates are isolated to prevent double counting.",
            "",
        ]
    )
    if validation["failures"]:
        lines.extend(["## Failures", ""] + [f"- {item}" for item in validation["failures"]] + [""])
    return "\n".join(lines)


def write_parquet(frame: pd.DataFrame, path: Path) -> pa.Table:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, path, compression="zstd")
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description="Build OECD/BEA/Mexico source-sector concordances.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/concordances/source_sector_crosswalk.parquet"),
    )
    parser.add_argument(
        "--validation-json",
        type=Path,
        default=Path("data/validation/source_sector_crosswalk_validation.json"),
    )
    parser.add_argument(
        "--validation-md",
        type=Path,
        default=Path("data/validation/source_sector_crosswalk_validation.md"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    output_path = args.output if args.output.is_absolute() else project_root / args.output
    validation_json = args.validation_json if args.validation_json.is_absolute() else project_root / args.validation_json
    validation_md = args.validation_md if args.validation_md.is_absolute() else project_root / args.validation_md
    for path in [output_path, validation_json, validation_md]:
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"Refusing to overwrite {path}; pass --overwrite")

    config = load_yaml(project_root / "configs/source_sector_rules.yaml")
    output = build_crosswalk(project_root, config)
    validation = validate_crosswalk(project_root, config, output)
    table = write_parquet(output, output_path)
    validation.update(
        {
            "validation_version": 1,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "output_path": output_path.relative_to(project_root).as_posix(),
            "output_sha256": sha256(output_path),
            "mapping_version": config["version"],
            "schema": [
                {"name": field.name, "type": str(field.type), "nullable": field.nullable}
                for field in table.schema
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
                "output_rows": validation["output_row_count"],
                "source_row_counts": validation["source_row_counts"],
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
