"""Prepare an observable-only MP pilot from existing, read-only processed data.

No solver, MP cost shock, elasticity, causal estimate, or welfare result is
constructed. All writes stay in output/mp_pilot_prepare_2026_10_03.
Run with a Python environment containing pandas, numpy, and pyarrow.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output/mp_pilot_prepare_2026_10_03"
YEARS = list(range(2017, 2024))
ENDPOINTS = [2019, 2022]
SECTORS = {
    "autos": ("C29", "Transportation equipment", "汽车"),
    "electronics": ("C26", "Computers and electronic products", "电子"),
    "machinery": ("C28", "Machinery", "机械"),
}
HARM = "data/processed/harmonized/"
FILES = {
    "amne_parent": HARM + "production_amne_parent_host_sector_long.parquet",
    "amne_host": HARM + "production_validation_amne_host_sector_long.parquet",
    "amne_interim": "data/interim/mne/oecd_amne_mp_shares.parquet",
    "bea": HARM + "production_bea_mne_source_industry_long.parquet",
    "bea_interim": "data/interim/mne/bea_us_mne_affiliate_country_industry.parquet",
    "icio": HARM + "production_icio_source_sector_long.parquet",
    "crosswalk": "data/processed/concordances/source_sector_crosswalk.parquet",
    "momentbank": "data/processed/moments/structural_moments.parquet",
    "F03": "output/stylized_facts_2026_09_12/F03/parent_group_year.csv",
    "F04": "output/stylized_facts_2026_09_12/F04/native_link_windows.csv",
}
BEA_METRICS = ["sales", "value_added", "employment", "capital_expenditures",
               "goods_exports_to_us", "goods_imports_from_us"]
checks: list[dict] = []


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require(label: str, condition: bool, detail: str = "") -> None:
    checks.append({"check": label, "passed": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{label}: {detail}")


def close(label: str, actual: float, expected: float, atol: float = 1e-7) -> None:
    require(label, bool(np.isclose(actual, expected, rtol=1e-10, atol=atol,
                                  equal_nan=True)), f"actual={actual}; expected={expected}")


def get1(frame: pd.DataFrame, **keys) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for name, value in keys.items():
        mask &= frame[name].eq(value)
    selected = frame.loc[mask]
    if len(selected) != 1:
        raise AssertionError(f"Expected one row for {keys}, found {len(selected)}")
    return selected.iloc[0]


def csv(name: str, data: pd.DataFrame) -> None:
    data.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.17g")


def write_json(name: str, value) -> None:
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                      allow_nan=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    hashes = {name: sha(ROOT / path) for name, path in FILES.items()}
    common = [("year", "in", YEARS)]
    sector_names = list(SECTORS)
    a = pd.read_parquet(ROOT / FILES["amne_parent"], filters=common + [
        ("host_country_iso3", "==", "MEX"), ("parent_country_iso3", "==", "USA"),
        ("analysis_sector", "in", sector_names), ("metric_name", "==", "affiliate_output")])
    ah = pd.read_parquet(ROOT / FILES["amne_host"], filters=common + [
        ("country_iso3", "==", "MEX"), ("analysis_sector", "in", sector_names)])
    ai = pd.read_parquet(ROOT / FILES["amne_interim"], filters=common + [
        ("host_country_iso3", "==", "MEX"),
        ("sector_oecd", "in", [x[0] for x in SECTORS.values()])])
    b = pd.read_parquet(ROOT / FILES["bea"], filters=common + [
        ("country_iso3", "==", "MEX"),
        ("model_sector", "in", [x[1] for x in SECTORS.values()])])
    bi = pd.read_parquet(ROOT / FILES["bea_interim"], filters=common + [
        ("affiliate_country", "==", "Mexico"),
        ("industry", "in", [x[1] for x in SECTORS.values()])])
    ic = pd.read_parquet(ROOT / FILES["icio"], filters=common + [
        ("country_iso3", "==", "MEX"), ("analysis_sector", "in", sector_names),
        ("metric_name", "in", ["gross_output", "value_added"])])
    crosswalk = pd.read_parquet(ROOT / FILES["crosswalk"])
    f03 = pd.read_csv(ROOT / FILES["F03"])
    f03 = f03[(f03.connector_iso3 == "MEX") & (f03.parent_group == "USA") &
              f03.analysis_sector.isin(sector_names) & f03.year.isin(YEARS)]
    f04 = pd.read_csv(ROOT / FILES["F04"])
    f04 = f04[(f04.connector_iso3 == "MEX") & (f04.parent_country_iso3 == "USA") &
              f04.analysis_sector.isin(sector_names)].copy()
    f04["interpretation"] = "aggregate parent-host-native-sector link; not incumbent firms"
    csv("existing_F04_link_context.csv", f04)

    require("amne_three_sectors_seven_years", len(a) == 21)
    require("amne_direct_only", a.direct_or_allocated.eq("direct_bilateral").all())
    require("amne_foreign_parents_only", ai.parent_country_iso3.ne("MEX").all())
    require("amne_native_keys_unique", not ai.duplicated(["year", "sector_oecd", "parent_country_iso3"]).any())
    require("bea_three_sectors_six_metrics_seven_years", len(b) == 126)
    require("bea_parent_is_USA", b.parent_country_iso3.eq("USA").all())
    require("no_geographic_aggregates", not b.aggregate_geography_flag.any())

    target_rows, denominator_rows, mapping_rows, bea_ratio_rows = [], [], [], []

    def target(source, sector, year, metric, value, unit, role, native, *,
               disclosure="available", native_metric=None, denominator="none_level",
               denominator_value=None, denominator_unit="not_applicable",
               denominator_file="not_applicable", numerator_metric=None,
               ownership="", provenance="", mapping="", exclusion="", raw_code="",
               small=False, identity_family="", full_sector=True):
        val = float(value) if pd.notna(value) else np.nan
        target_rows.append({
            "target_id": f"{source}:MEX:{sector}:{year}:{metric}",
            "host_country_iso3": "MEX", "parent_country_iso3": "USA" if "us_" in metric or source == "BEA" else "ALL",
            "source": source, "candidate_sector": sector, "year": year,
            "native_sector": native, "metric": metric, "source_metric": native_metric or metric,
            "value": val, "unit": unit, "role": role, "ownership_scope": ownership,
            "disclosure_status": disclosure, "value_available": math.isfinite(val),
            "raw_code": raw_code, "small_value_flag": small,
            "denominator_definition": denominator, "denominator_value": denominator_value,
            "denominator_unit": denominator_unit, "denominator_source_file": denominator_file,
            "numerator_metric": numerator_metric or native_metric or metric,
            "mapping_status": mapping, "full_candidate_sector_coverage": full_sector,
            "restriction_or_exclusion": exclusion, "source_file": provenance,
            "identity_family": identity_family, "can_enter_model_directly": False,
            "causal_effect_identified": False, "hgamma_observed": False,
            "is_primary_fit_target": source == "AMNE" and sector == "machinery" and metric == "us_share_host_gross_output",
        })

    for sec, (native, bea_native, label_cn) in SECTORS.items():
        for source_name, native_code in [("oecd_amne", native), ("oecd_icio", native), ("bea_mne", bea_native)]:
            sx = get1(crosswalk, source_name=source_name, source_sector_code=native_code)
            mapping_rows.append({"candidate_sector": sec, "label_cn": label_cn,
                                 "source": source_name, "native_sector": native_code,
                                 "existing_analysis_sector": sx.analysis_sector,
                                 "mapping_status": sx.mapping_status,
                                 "mapping_rule": sx.mapping_rule,
                                 "existing_main_join_eligible": bool(sx.is_main_join_eligible),
                                 "pilot_use": "native_reference_only_not_C29" if sec == "autos" and source_name == "bea_mne" else "mapped_candidate_keep_native_definition",
                                 "cross_source_values_interchangeable": False,
                                 "reason": "Transportation equipment includes non-auto industries; no allocation weight" if sec == "autos" and source_name == "bea_mne" else "Mapped for project analysis; sales/output and ownership populations still differ across sources"})
        for year in YEARS:
            ar = get1(a, analysis_sector=sec, year=year)
            air = get1(ai, sector_oecd=native, parent_country_iso3="USA", year=year)
            yr = ai[(ai.sector_oecd == native) & (ai.year == year)]
            us = float(ar.value)
            total = float(yr.affiliate_output.sum())
            hr = {m: get1(ah, analysis_sector=sec, year=year, metric_name=m)
                  for m in ["bilateral_affiliate_output_sum", "foreign_affiliate_output_total",
                            "gross_output", "foreign_affiliate_output_share"]}
            foreign_xvem = float(hr["foreign_affiliate_output_total"].value)
            gross = float(hr["gross_output"].value)
            close(f"amne_direct_vs_interim_{sec}_{year}", us, air.affiliate_output)
            close(f"amne_parent_sum_vs_canonical_{sec}_{year}", total, hr["bilateral_affiliate_output_sum"].value)
            close(f"amne_vs_existing_F03_{sec}_{year}", us, get1(f03, analysis_sector=sec, year=year).output_musd)
            close(f"amne_foreign_share_identity_{sec}_{year}", foreign_xvem / gross, hr["foreign_affiliate_output_share"].value)
            close(f"amne_parent_share_interim_{sec}_{year}", us / total, air.parent_affiliate_output_share)
            require(f"amne_valid_denominators_{sec}_{year}", 0 <= us <= total <= gross and 0 <= foreign_xvem <= gross)
            require(f"amne_repeated_host_total_constant_{sec}_{year}", yr.gross_output.nunique() == 1 and yr.foreign_affiliate_output_total.nunique() == 1)
            denominator_rows.append({"candidate_sector": sec, "year": year, "native_sector": native,
                                     "us_output": us, "foreign_bilateral_sum": total,
                                     "foreign_xvem_total": foreign_xvem, "host_gross_output": gross,
                                     "bilateral_minus_xvem_musd": total - foreign_xvem,
                                     "us_share_foreign_denominator": "sum direct bilateral output, all foreign origins incl residual",
                                     "us_share_host_denominator": "AMNE host gross output once, not sum repeated parent rows",
                                     "foreign_share_host_denominator": "AMNE XVEM foreign output / AMNE host gross output",
                                     "number_foreign_origin_rows": len(yr),
                                     "positive_foreign_origin_rows": int(yr.affiliate_output.gt(0).sum()),
                                     "residual_ROW_output": float(yr.loc[yr.parent_country_iso3.eq("ROW"), "affiliate_output"].sum()),
                                     "denominator_same_year_native_sector": True,
                                     "no_cross_source_division": True,
                                     "source_file": FILES["amne_interim"], "canonical_host_file": FILES["amne_host"]})
            base = {"disclosure": "available_analytical_amne_not_raw_firm_measurement",
                    "ownership": "OECD foreign-affiliate framework; direct parent output, aggregate not firm incumbent",
                    "mapping": str(ar.sector_mapping_status),
                    "identity_family": f"AMNE_MEX_{native}_{year}",
                    "exclusion": "Alternative or joint moments require dependency-aware weighting; no allocated parent VA/exports/imports used"}
            target("AMNE", sec, year, "us_affiliate_output", us, "current_million_usd", "validation_diagnostic", native,
                   native_metric="affiliate_output", provenance=FILES["amne_parent"], **base)
            for metric, val, role, source_metric in [
                ("all_foreign_bilateral_output_sum", total, "denominator_context", "bilateral_affiliate_output_sum"),
                ("foreign_xvem_output_total", foreign_xvem, "validation_context", "foreign_affiliate_output_total"),
                ("host_gross_output", gross, "denominator_context", "gross_output")]:
                target("AMNE", sec, year, metric, val, "current_million_usd", role, native,
                       native_metric=source_metric, provenance=FILES["amne_host"], **base)
            for metric, val, denominator, den_val, numerator, role in [
                ("us_share_all_foreign_output", us / total, "all_foreign_bilateral_output_sum", total, "us_affiliate_output", "validation_diagnostic"),
                ("us_share_host_gross_output", us / gross, "host_gross_output", gross, "us_affiliate_output", "calibration_candidate"),
                ("foreign_share_host_gross_output", foreign_xvem / gross, "host_gross_output", gross, "foreign_xvem_output_total", "validation_context")]:
                target("AMNE", sec, year, metric, val, "fraction", role, native,
                       denominator=denominator, denominator_value=den_val,
                       denominator_unit="current_million_usd", denominator_file=FILES["amne_host"],
                       numerator_metric=numerator, provenance=FILES["amne_parent"] + " + " + FILES["amne_host"], **base)

            bir = get1(bi, year=year, industry=bea_native)
            for metric in BEA_METRICS:
                br = get1(b, year=year, model_sector=bea_native, metric_name=metric)
                close(f"bea_vs_interim_{sec}_{year}_{metric}", br.value, bir[metric])
                require(f"bea_disclosure_vs_interim_{sec}_{year}_{metric}", bool(br.suppressed_flag) == bool(bir[metric + "_suppressed"]))
                disclosure = "suppressed_D" if br.suppressed_flag else "small_value_not_exact_zero" if br.small_value_flag else "available" if pd.notna(br.value) else "missing"
                role = "network_restriction_candidate" if metric == "goods_exports_to_us" else "validation"
                if sec == "autos":
                    role = "native_reference_only"
                target("BEA", sec, year, metric, br.value, str(br.unit), role, bea_native,
                       disclosure=disclosure, provenance=FILES["bea"], raw_code=str(br.raw_code),
                       mapping=str(br.sector_mapping_status), small=bool(br.small_value_flag),
                       ownership=str(br.ownership_scope), full_sector=sec != "autos",
                       identity_family=f"BEA_MEX_{bea_native}_{year}",
                       exclusion=("Transportation equipment is not autos C29; no direct cross-source ratio or level equality" if sec == "autos" else
                                  "US-parent MOFA population; BEA sales not AMNE output. Exports to US are not a validated sales-destination probability"))

            export = get1(b, year=year, model_sector=bea_native, metric_name="goods_exports_to_us")
            sales = get1(b, year=year, model_sector=bea_native, metric_name="sales")
            available = pd.notna(export.value) and pd.notna(sales.value) and sales.value > 0 and not export.small_value_flag and not sales.small_value_flag
            ratio = float(export.value / sales.value) if available else np.nan
            bea_ratio_rows.append({"candidate_sector": sec, "year": year, "native_sector": bea_native,
                                   "exports_to_us_musd": export.value, "sales_musd": sales.value,
                                   "exports_disclosure": "suppressed_D" if export.suppressed_flag else "available",
                                   "mechanical_exports_divided_by_sales": ratio,
                                   "exceeds_one": bool(ratio > 1) if pd.notna(ratio) else False,
                                   "valid_destination_probability": False,
                                   "diagnostic": "numerator_denominator_definition_needs_source_note_review" if pd.notna(ratio) else "suppression_or_missing_prevents_ratio",
                                   "specific_cause_verified": False,
                                   "source_file": FILES["bea"]})

            for metric in ["gross_output", "value_added"]:
                present = ic[(ic.analysis_sector == sec) & (ic.year == year) & (ic.metric_name == metric)]
                require(f"icio_unique_or_missing_{sec}_{year}_{metric}", len(present) <= 1)
                val = float(present.iloc[0].value) if len(present) else np.nan
                target("ICIO", sec, year, metric, val, "current_million_usd", "baseline_and_broad_production_context", native,
                       disclosure="available" if len(present) else "year_not_built_in_existing_baseline",
                       ownership="all producers; not ownership tagged", provenance=FILES["icio"],
                       mapping="oecd_exact_priority", exclusion="Not US-parent activity; no AMNE/BEA ratio and no interpolation",
                       identity_family=f"ICIO_MEX_{native}_{year}")
                if len(present):
                    input_name = "X_baseline.csv" if metric == "gross_output" else "va_baseline.csv"
                    source_path = f"data/model_inputs/icio_baseline_{year}/{input_name}"
                    source_data = pd.read_csv(ROOT / source_path)
                    cell = get1(source_data, country_iso3="MEX", sector_oecd=native, year=year)
                    close(f"icio_vs_model_input_{sec}_{year}_{metric}", val, cell[metric])
                    if source_path not in hashes:
                        hashes[source_path] = sha(ROOT / source_path)

    targets = pd.DataFrame(target_rows)
    mapping = pd.DataFrame(mapping_rows)
    denominators = pd.DataFrame(denominator_rows)
    ratios = pd.DataFrame(bea_ratio_rows)
    require("target_ids_unique", not targets.target_id.duplicated().any())
    require("all_candidate_source_metric_year_cells_retained", len(targets) == 315)
    require("no_model_parameters_reported", not targets.can_enter_model_directly.any() and not targets.hgamma_observed.any())
    require("suppressed_targets_are_missing_not_zero", targets.loc[targets.disclosure_status.eq("suppressed_D"), "value"].isna().all())
    require("all_nonmissing_values_finite", np.isfinite(targets.value.dropna()).all())
    require("three_candidates_preserved", set(targets.candidate_sector) == set(SECTORS))
    require("exactly_one_primary_metric_for_one_sector_all_seven_years", targets.is_primary_fit_target.sum() == 7)
    csv("observable_targets.csv", targets)
    csv("denominator_audit.csv", denominators)
    csv("sector_mapping_audit.csv", mapping)
    csv("bea_network_ratio_diagnostics.csv", ratios)

    changes = []
    for (source, sec, metric), block in targets.groupby(["source", "candidate_sector", "metric"], sort=True):
        baseline = get1(block, year=2017)
        for end in ENDPOINTS:
            post = get1(block, year=end)
            valid = bool(baseline.value_available and post.value_available and
                         not baseline.small_value_flag and not post.small_value_flag)
            level = baseline.unit != "fraction"
            diff = float(post.value - baseline.value) if valid else np.nan
            percent = float(100 * (post.value / baseline.value - 1)) if valid and level and baseline.value > 0 else np.nan
            log_change = float(math.log(post.value / baseline.value)) if valid and level and min(baseline.value, post.value) > 0 else np.nan
            pp = float(diff * 100) if valid and not level else np.nan
            changes.append({"source": source, "candidate_sector": sec, "native_sector": baseline.native_sector,
                            "metric": metric, "baseline_year": 2017, "end_year": end,
                            "baseline_value": baseline.value, "end_value": post.value,
                            "value_unit": baseline.unit, "difference": diff,
                            "growth_percent": percent, "log_change": log_change,
                            "share_change_percentage_points": pp, "change_available": valid,
                            "baseline_disclosure": baseline.disclosure_status, "end_disclosure": post.disclosure_status,
                            "role": baseline.role, "full_candidate_sector_coverage": baseline.full_candidate_sector_coverage,
                            "is_primary_fit_target": baseline.is_primary_fit_target,
                            "causal_or_structural_interpretation": "none; same-source nominal endpoint change only",
                            "reason_if_not_computable": "" if valid else f"baseline={baseline.disclosure_status}; end={post.disclosure_status}"})
    changes = pd.DataFrame(changes)
    csv("same_source_endpoint_changes.csv", changes)

    # Independent arithmetic check uses source-native tables, not exported targets.
    for row in changes.itertuples():
        native, bea_native, _ = SECTORS[row.candidate_sector]
        if row.source == "AMNE":
            def av(year):
                block = ai[(ai.year == year) & (ai.sector_oecd == native)]
                usa = block.loc[block.parent_country_iso3 == "USA"].iloc[0]
                nums = {"us_affiliate_output": usa.affiliate_output,
                        "all_foreign_bilateral_output_sum": math.fsum(block.affiliate_output),
                        "foreign_xvem_output_total": usa.foreign_affiliate_output_total,
                        "host_gross_output": usa.gross_output,
                        "us_share_all_foreign_output": usa.affiliate_output / math.fsum(block.affiliate_output),
                        "us_share_host_gross_output": usa.affiliate_output / usa.gross_output,
                        "foreign_share_host_gross_output": usa.foreign_affiliate_output_total / usa.gross_output}
                return float(nums[row.metric])
            p, q = av(2017), av(row.end_year)
        elif row.source == "BEA":
            p = get1(bi, year=2017, industry=bea_native)[row.metric]
            q = get1(bi, year=row.end_year, industry=bea_native)[row.metric]
        else:
            file = "X_baseline.csv" if row.metric == "gross_output" else "va_baseline.csv"
            p = get1(pd.read_csv(ROOT / f"data/model_inputs/icio_baseline_2017/{file}"),
                     year=2017, country_iso3="MEX", sector_oecd=native)[row.metric]
            qpath = ROOT / f"data/model_inputs/icio_baseline_{row.end_year}/{file}"
            q = get1(pd.read_csv(qpath), year=row.end_year, country_iso3="MEX", sector_oecd=native)[row.metric] if qpath.exists() else np.nan
        close(f"change_source_baseline_{row.source}_{row.candidate_sector}_{row.metric}_{row.end_year}", row.baseline_value, p)
        close(f"change_source_endpoint_{row.source}_{row.candidate_sector}_{row.metric}_{row.end_year}", row.end_value, q)
        if row.change_available:
            expected = 100 * (q - p) if row.value_unit == "fraction" else 100 * (q - p) / p
            actual = row.share_change_percentage_points if row.value_unit == "fraction" else row.growth_percent
            close(f"change_arithmetic_{row.source}_{row.candidate_sector}_{row.metric}_{row.end_year}", actual, expected)

    # Selection uses support only: disclosed six-metric BEA endpoint cells and an
    # existing non-proxy source-industry mapping. It never reads change signs.
    eligibility = []
    for sec, (native, bea_native, cn) in SECTORS.items():
        bb = targets[(targets.source == "BEA") & (targets.candidate_sector == sec)]
        selected = bb[bb.year.isin([2017, 2019, 2022])]
        mapping_ok = sec != "autos"
        available = int(selected.value_available.sum())
        suppressed = int(selected.disclosure_status.eq("suppressed_D").sum())
        ratio_flag = int(ratios[(ratios.candidate_sector == sec)].exceeds_one.sum())
        support_ok = mapping_ok and available == 18 and not selected.small_value_flag.any()
        eligibility.append({"candidate_sector": sec, "label_cn": cn, "amne_native_sector": native,
                            "bea_native_sector": bea_native, "existing_mapping_eligible": mapping_ok,
                            "required_bea_endpoint_cells": 18, "available_bea_endpoint_cells": available,
                            "suppressed_bea_endpoint_cells": suppressed,
                            "bea_ratio_above_one_year_count": ratio_flag,
                            "recommended_first_data_pilot": support_ok,
                            "selection_uses_outcome_sign": False,
                            "decision": "first_data_pilot_not_calibration_ready" if support_ok else "retain_comparator_with_specific_limits",
                            "reason": "All six native BEA metrics disclosed at selected endpoints; project mapping eligible. Cross-source measurement contract still required" if support_ok else
                            "Transportation equipment cannot be equated with C29; US export endpoint suppressed" if not mapping_ok else
                            "Capital expenditure suppressed at every year; exports/sales diagnostic exceeds one in 2018; do not fill zeros"})
    eligible = pd.DataFrame(eligibility)
    require("mechanical_support_rule_selects_one_candidate", eligible.recommended_first_data_pilot.sum() == 1)
    require("support_rule_selects_machinery", eligible.loc[eligible.recommended_first_data_pilot, "candidate_sector"].tolist() == ["machinery"])
    csv("candidate_readiness.csv", eligible)

    moments = pd.read_parquet(ROOT / FILES["momentbank"])
    moments = moments[(moments.connector_iso3 == "MEX") & moments.analysis_sector.isin(sector_names) &
                      moments.source_table.isin(["amne_host_sector", "bea_mne_analysis", "icio_analysis"])].copy()
    require("existing_momentbank_not_parameter_file", not moments.can_enter_model_directly_flag.any())
    moments["pilot_role_note"] = "existing registry only; original windows retained; this pilot treats BEA as validation and ICIO as context"
    csv("existing_momentbank_context.csv", moments)

    # Direction disagreement is retained as a diagnostic, never reconciled by scaling.
    comparisons = []
    for sec in SECTORS:
        for end in ENDPOINTS:
            am = get1(changes, source="AMNE", candidate_sector=sec, metric="us_affiliate_output", end_year=end)
            be = get1(changes, source="BEA", candidate_sector=sec, metric="sales", end_year=end)
            comparisons.append({"candidate_sector": sec, "baseline_year": 2017, "end_year": end,
                                "amne_us_output_growth_pct": am.growth_percent,
                                "bea_native_sales_growth_pct": be.growth_percent,
                                "same_sign": bool(np.sign(am.growth_percent) == np.sign(be.growth_percent)),
                                "same_estimand": False,
                                "native_sector_mapping_eligible": sec != "autos",
                                "cross_source_division_or_pooling_performed": False,
                                "interpretation": "descriptive sign comparison, not equality validation; transport reference broader than autos" if sec == "autos" else
                                "descriptive sign comparison; sales vs output and affiliate populations differ; agreement does not establish equivalence"})
    comparisons = pd.DataFrame(comparisons)
    csv("cross_source_direction_diagnostic.csv", comparisons)

    for name, digest in hashes.items():
        path = ROOT / FILES.get(name, name)
        require(f"protected_input_hash_unchanged_{name}", sha(path) == digest)
    manifest = {"date": "2026-10-03", "script": str(Path(__file__).relative_to(ROOT)),
                "scope": "Mexico, US parent, autos/electronics/machinery; observed targets only",
                "years": YEARS, "baseline_year": 2017, "endpoint_years": ENDPOINTS,
                "versions": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__, "pyarrow": pyarrow.__version__},
                "source_files": FILES, "input_sha256": hashes,
                "rows": {"observable_targets": len(targets), "endpoint_changes": len(changes),
                         "retained_suppressed_observations": int(targets.disclosure_status.eq("suppressed_D").sum()),
                         "retained_icio_year_not_built": int(targets.disclosure_status.eq("year_not_built_in_existing_baseline").sum()),
                         "existing_momentbank_context": len(moments)},
                "computed": ["source-native levels", "AMNE explicitly defined same-source shares",
                             "2017 to 2019 and 2022 same-source changes", "disclosure and denominator audits",
                             "mechanical BEA ratio diagnostics, never network probabilities"],
                "not_computed": ["hgamma", "MP elasticity", "causal effect", "welfare", "trilateral network imputation", "pandemic model"],
                "selection_rule": "retain all 3 candidates; recommend first data pilot by mapping eligibility and all 18 BEA endpoint cells available, not change direction",
                "data_preparation_passed": True, "Gate3_passed": False,
                "cross_source_measurement_contract_complete": False,
                "material_passport": {"mode": "run and validate", "data_access": "read existing interim/harmonized; write new outputs only", "verification": "source-native extraction and arithmetic reconciled; economic identification not claimed"}}
    write_json("MANIFEST.json", manifest)
    write_json("VALIDATION.json", {"passed": all(c["passed"] for c in checks), "number_of_checks": len(checks), "checks": checks,
                                  "meaning": "numerical provenance and accounting validation, not independent source coverage or identification"})

    def rowval(source, sec, metric, year):
        return get1(targets, source=source, candidate_sector=sec, metric=metric, year=year).value
    def fmt(value):
        return f"{value:,.2f}" if pd.notna(value) else "未披露/未构建"
    pilot_target = "us_share_host_gross_output"
    pilot_series = []
    for year in [2017, 2019, 2022]:
        pilot_series.append({"year": year,
                             "target_fraction": float(rowval("AMNE", "machinery", pilot_target, year)),
                             "numerator_us_affiliate_output_musd": float(rowval("AMNE", "machinery", "us_affiliate_output", year)),
                             "denominator_host_gross_output_musd": float(rowval("AMNE", "machinery", "host_gross_output", year)),
                             "bea_sales_musd": float(rowval("BEA", "machinery", "sales", year)),
                             "bea_goods_exports_to_us_musd": float(rowval("BEA", "machinery", "goods_exports_to_us", year))})
    write_json("PILOT_SUMMARY.json", {
        "date": "2026-10-03", "recommended_object": "USA parent -> MEX host -> C28 machinery",
        "selection": "Existing mapping plus 18/18 disclosed BEA endpoint cells; growth signs not used",
        "target_name": pilot_target,
        "target_definition": "Direct USA-parent affiliate output divided by AMNE host gross output, MEX C28 in the same year",
        "denominator": "All-origin Mexican C28 gross output, domestic and foreign; AMNE XVEM host total taken once",
        "denominator_source": FILES["amne_host"], "numerator_source": FILES["amne_parent"],
        "series": pilot_series, "executed_checks": len(checks),
        "computed": manifest["computed"], "not_computed": manifest["not_computed"],
        "major_findings": [
            "Automotive BEA Transportation equipment is broader than AMNE C29 and has suppressed US-export endpoints",
            "Electronics BEA capex is suppressed in all 2017-2023 years and is retained missing",
            "Electronics 2018 BEA exports-to-US 4426 / sales 4254 exceeds one; cause not verified; no sales probability imposed",
            "ICIO 2019 is not built; no interpolation or endpoint change fabricated",
            "AMNE direct bilateral sum and XVEM foreign total kept separate; no cross-source division or pooling"],
        "next_test_ready": False, "Gate3_passed": False,
        "next_test_ready_conditions": [
            "Define model aggregation corresponding to US-parent share of host output; reconcile sales/output valuation, tariffs and domestic-origin denominator",
            "Freeze source-verified elasticity/curvature values and other shocks; do not freely fit elasticity with one MP-cost parameter",
            "Choose a defended trilateral-network restriction or range; do not directly use BEA exports/sales as probability",
            "Verify BEA Machinery Table II.D 3/II.H 11 definitions and population against intended validation role",
            "Audit common underlying source information before treating AMNE and BEA as statistically independent targets",
            "Only then execute a one-direction MP-cost sensitivity test, followed by fit to one AMNE share and held-out levels/BEA diagnostics"],
        "suggested_parameter_not_estimated": "One log effective MP cost change for USA->MEX C28 per tested endpoint; no value assigned",
        "primary_fit_target": "AMNE us_share_host_gross_output only",
        "extra_diagnostics": "AMNE output level and foreign-parent share, BEA native Machinery activity, ICIO broad production",
        "warning": "Observed output or share changes are not hgamma; no log-share-ratio inversion performed"})
    rows_text = []
    for sec, (_, bea_native, cn) in SECTORS.items():
        for source, metric, label in [("AMNE", "us_affiliate_output", "美国母国外资产出"),
                                      ("AMNE", "us_share_all_foreign_output", "美国在全部外国产出中的份额"),
                                      ("BEA", "sales", "美国 MOFA 销售"),
                                      ("BEA", "goods_exports_to_us", "美国 MOFA 向美国货物出口")]:
            vals = [rowval(source, sec, metric, y) for y in [2017, 2019, 2022]]
            vals_fmt = [f"{v * 100:.2f}%" if metric.endswith("share_all_foreign_output") and pd.notna(v) else fmt(v) for v in vals]
            rows_text.append(f"| {cn} | {source} {label} | " + " | ".join(vals_fmt) + " |")
    ready = f"""# Mexico–U.S. MP 校准准备包

日期：2026-10-03。服务 Gate 2/3。已完成可观测目标提取及同来源端点比较，尚未校准参数、求解均衡或计算福利。

**建议先用墨西哥—美国母公司—机械部门做最小数据试点，同时保留汽车和电子全部候选记录。** 选择依据是已有行业映射与披露完整性：机械在 2017、2019、2022 三个端点的 6 个 BEA 指标共 18 个单元均可得。选择没有使用增长正负。汽车的 BEA 行业是 Transportation equipment，不能当作 AMNE C29。电子的 capex 全期受抑制，不补零。

## 已实际计算的内容

`observable_targets.csv` 包含 {len(targets)} 行，覆盖三个候选部门、2017—2023 年以及 AMNE、BEA、ICIO 的原生指标。表中逐行保留指标、值、单位、年份、原生行业、分母、来源文件、披露状态、角色和限制。`same_source_endpoint_changes.csv` 包含 {len(changes)} 行，计算 2017→2019 和 2017→2022 的同来源变化，无法计算的单元保留原因。金额均为当期百万美元，就业为千人，份额为 0—1。

| 候选部门 | 指标 | 2017 | 2019 | 2022 |
| --- | --- | ---: | ---: | ---: |
{chr(10).join(rows_text)}

表中汽车 BEA 项目仍指整个运输设备，只作为更宽原生行业参考。美国 MOFA 销售不等于 AMNE 外资产出，二者没有交叉相除或合并成一个目标。

## 核心检验与参数建议

核心检验是：给定已有基准生产与贸易结构，一个明确的、低维的美国—墨西哥机械 MP 成本变化，是否能解释 AMNE 美国母国外资产出及份额的变化，并与 BEA 同原生机械行业的销售、增加值、就业与对美货物出口方向相容。这里先准备证据，不预设必然存在这样的成本变化。

建议下一阶段从每个待检验端点一个 `g_t = log(gamma_USA,MEX,C28,t / gamma_USA,MEX,C28,2017)` 开始。这只是参数化提案，本包没有给 g_t 或 hgamma 赋值。两个端点分别检验，不将两期变化硬当同一个冲击；其他来源成本、贸易冲击及生产率处理必须先写清。弹性或曲率参数应来自另行核验的公开来源及已登记模型输入，先固定并声明范围，不能同时用同一组份额变化自由拟合成本与弹性。

首个拟合目标明确为 `us_share_host_gross_output`：美国母公司在墨西哥 C28 的直接外资产出 / AMNE 墨西哥 C28 的全部 gross output（包括本国与外国来源）。2017、2019、2022 分别为 {rowval('AMNE', 'machinery', pilot_target, 2017):.8f}、{rowval('AMNE', 'machinery', pilot_target, 2019):.8f}、{rowval('AMNE', 'machinery', pilot_target, 2022):.8f}。AMNE 产出水平、美国占全部外国产出的份额只作额外诊断，不当作三个独立拟合目标。BEA 销售、VA、就业、capex 作为留出验证；现有 moment bank 曾允许更广用途，本包保留原登记但不自动沿用全部角色。ICIO 只提供全体生产者的基准和宽口径生产检验，不视为美国母公司产出。

这个目标尚未就绪为模型输入。参考模型 `mpshare_sim` 按生产地和行业，将母国相关流量除以全部母国流量；在使用前仍须确认目的地加总、国内母国成分，以及含税/生产者价格的计价口径与 AMNE gross output 的对应，建立共同的基准与受约束网络。未经这一步不能用两个份额的对数比直接反推 gamma。本包没有运行这种反推。

## 分母和跨来源限制

1. AMNE 美国在外国产出中的份额 = 直接美国母国产出 / 同年同原生行业全部外国母国产出之和，包括未分配残余。主分母保留 direct bilateral sum，不把它强行缩放成 XVEM 总量。
2. AMNE 美国在东道国产出中的份额 = 同一美国母国产出 / AMNE 同年同原生行业 host gross output。gross output 在 parent 表重复出现，只取一次。
3. 全国外资份额 = AMNE XVEM foreign output / AMNE host gross output。`denominator_audit.csv` 单列 direct-sum 与 XVEM 的小差额，不用差额“修正”来源。
4. BEA 为美国母公司多数持股海外 affiliates。AMNE 母国输出定义与 BEA MOFA 人群、销售/产出测量可能不同。已有 electronics/machinery crosswalk 支持项目层行业对应，不意味着统计总体和指标完全相等。两套统计原始信息的独立性尚未核验，BEA 的“留出验证”仅指不进入本试点拟合目标，不宣称独立数据生成过程，也不得重复计权为独立样本。
5. `goods_exports_to_us` 是已存在的美国母公司网络局部信息，不可外推中国、日韩台等母国。仅把它列为网络约束候选，尚未将其变成三边销售概率。
6. 电子 2018 年 exports-to-US 为 {fmt(rowval('BEA', 'electronics', 'goods_exports_to_us', 2018))}，sales 为 {fmt(rowval('BEA', 'electronics', 'sales', 2018))}，直接相除得到的比值大于 1。该诊断说明必须核对两张 BEA 表的分子分母定义；本次没有查明具体原因，不断言是海关、覆盖或数据错误。机械部门的这一比值即便位于 0—1 也不能免去同一口径核验。
7. ICIO 当前只构建了 2017、2018、2022 的基准，本包未把 2019 或其余缺失年插值。2017→2019 的 ICIO 变化明确保留为不可算。

## 通过与失败标准

本次数据准备通过标准：315 个候选单元完整保留；AMNE 原生提取与 canonical 分母、现有 F03 数值一致；BEA 原生提取与 interim 值及披露标识一致；ICIO 与已保存模型基准一致；源文件哈希不变；抑制值没有被改成零。共执行 {len(checks)} 个数值与来源检查，结果见 VALIDATION.json。这不是 Gate 3 通过。

下一阶段先通过测量合同：明确同原生机械部门的 AMNE 产出和 BEA 各指标如何进入可比目标，核查 goods_exports_to_us 与 sales 的表注，并明确无法同义比较的部分。若无法支持销售目的地概率，保留出口水平验证或缩小为 host-level MP，不把机械比值直接放入网络。

未来机制试验的通过标准是：固定可辩护弹性与其他冲击设定后，目标对所建议 g_t 有可分辨的响应；用主目标约束出的可行区间不只是任意边界；BEA 留出证据和可辩护网络限制不否定其经济解释。接受偏差应在看拟合结果前，依据源间口径和测量不确定性定义，不能为通过试验临时设阈值。

失败条件：目标对 g_t 不敏感或成本与弹性不可区分；同一低维设定只能解释一个目标而与其他可信目标冲突；需要把明显不兼容销售比率当概率；或者只能通过把全部观察变化归于 MP 成本来获得结果。失败时缩窄对象或调整映射，不增加参数掩盖冲突。

## 下一条具体可执行工作

先对 Mexico × Machinery，核对本地 BEA Table II.D 3 与 II.H 11 定义及 AMNE C28 的范围，形成两页以内测量合同，冻结哪些指标为校准、哪些只作验证及网络限制。在这份合同通过后，另开一个仅包含该 MP 成本方向的参数敏感性试验，先检验映射是否可辨认，再决定是否迁移求解器。此次没有迁移 solver，没有 hgamma、弹性、福利或因果估计结果。

疫情本轮只保留描述边界：2017→2019 是疫情前端点对照，2017→2022 混合疫情及其他变化；二者均不是贸易战净效应。不开展专门疫情模型或关税工具变量。

## 文件与复现

- observable_targets.csv：所有值、原生定义、分母、披露与角色。
- same_source_endpoint_changes.csv：端点差值、百分比或百分点及不可算原因。
- candidate_readiness.csv / sector_mapping_audit.csv：按覆盖选机械、保留另外两个候选及限制。
- denominator_audit.csv：AMNE 分母来源、含残余的外国合计及 XVEM 差额。
- bea_network_ratio_diagnostics.csv：出口值除以销售值，仅口径诊断，没有有效销售概率。
- cross_source_direction_diagnostic.csv：源内增长方向并列，不宣称同一 estimand。
- existing_momentbank_context.csv / existing_F04_link_context.csv：保留旧窗口及原登记，仅背景。
- MANIFEST.json / VALIDATION.json：输入哈希、版本、样本、验证及未完成事项。

运行：`C:/Python314/python.exe code/analysis/mp_pilot_prepare_2026_10_03.py`。脚本只读已有 interim/harmonized 和事实表；只写本准备包目录。原有 facts、raw 数据、配置和模型均不修改。
"""
    (OUT / "READY_NEXT_TEST.md").write_text(ready, encoding="utf-8")
    print(json.dumps({"output": str(OUT), "targets": len(targets), "changes": len(changes),
                      "checks": len(checks), "selected": "machinery", "Gate3_passed": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
