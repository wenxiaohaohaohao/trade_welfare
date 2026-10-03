"""Independent raw-workbook checks for the 2026-10-03 staged description.

Uses openpyxl and stdlib; never imports the producing program.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import csv
import hashlib
import json
import math
import unicodedata

import openpyxl

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data/raw/fDi_Markets .xlsx'
OLD = ROOT / 'output/fdi_facts_2026_10_02'
OUT = ROOT / 'output/fdi_research_baseline_2026_10_03'
HOSTS = ('Mexico', 'Vietnam', 'Thailand')
TYPES = ('New', 'Expansion', 'Co-Location')
GROUPS = ('China', 'Other East Asia', 'United States', 'Other parents')
PERIODS = {'2014-2017': range(2014, 2018), '2018-2019': range(2018, 2020), '2020-2022': range(2020, 2023), '2023': (2023,)}


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def group(value):
    return value if value in ('China', 'United States') else 'Other East Asia' if value in ('Japan', 'South Korea', 'Taiwan') else 'Other parents'


def identity(row, sector=False):
    name = ' '.join(unicodedata.normalize('NFKC', row['Parent_Company']).split()).casefold()
    key = (row['Source_Country'], name, row['Destination_Country'])
    return key + (row['Sector'],) if sector else key


def percentage(n, d):
    return Fraction(100 * n, d) if d else None


def load_raw():
    workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    iterator = workbook['2014-2023'].iter_rows(values_only=True)
    header = next(iterator)
    rows = []
    for values in iterator:
        row = dict(zip(header, (None if v in ('NA', 'N/A', '') else v for v in values)))
        date = row['Project_Date']
        if row['Activity'] == 'Manufacturing' and 2014 <= date.year <= 2023 and (date.year < 2023 or date.month <= 9):
            assert row['Destination_Country'] in HOSTS
            assert row['Project_Type'] in TYPES
            assert row['Source_Country'] and row['Parent_Company']
            rows.append(row)
    workbook.close()
    return rows


class Audit:
    def __init__(self):
        self.checked = Counter()
        self.errors = []

    def number(self, filename, key, field, actual, expected):
        self.checked[filename] += 1
        good = actual in ('', None) if expected is None else math.isclose(float(actual), float(expected), abs_tol=1e-10, rel_tol=1e-12)
        if not good:
            self.errors.append({'file': filename, 'key': key, 'field': field, 'expected': str(expected), 'actual': actual})

    def fields(self, filename, key, row, expected):
        for field, value in expected.items():
            self.number(filename, key, field, row[field], value)


def expected_summary(rows, host, years, months):
    sample = [r for r in rows if r['Destination_Country'] == host and r['Project_Date'].year in years and r['Project_Date'].month <= months]
    n = len(sample)
    out = {'first_year': min(years), 'last_year': max(years), 'n_years': len(years), 'months_per_year': months, 'records': n, 'mean_records_per_year_in_month_window': Fraction(n, len(years))}
    for typ in TYPES:
        prefix = typ.lower().replace('-', '_')
        count = sum(r['Project_Type'] == typ for r in sample)
        out[f'{prefix}_records'] = count
        out[f'{prefix}_share_pct'] = percentage(count, n)
    for source in GROUPS:
        prefix = source.lower().replace(' ', '_')
        count = sum(group(r['Source_Country']) == source for r in sample)
        out[f'{prefix}_records'] = count
        out[f'{prefix}_share_pct'] = percentage(count, n)
    assert sum(out[t.lower().replace('-', '_') + '_records'] for t in TYPES) == n
    assert sum(out[g.lower().replace(' ', '_') + '_records'] for g in GROUPS) == n
    assert sum(out[t.lower().replace('-', '_') + '_share_pct'] for t in TYPES) == 100
    assert sum(out[g.lower().replace(' ', '_') + '_share_pct'] for g in GROUPS) == 100
    return out


def main():
    before = hashlib.sha256(RAW.read_bytes()).hexdigest()
    rows = load_raw()
    audit = Audit()
    # Check the existing annual grid only, not all old robustness output.
    annual_counts = Counter((r['Destination_Country'], r['Project_Date'].year, r['Project_Type'], group(r['Source_Country'])) for r in rows if r['Project_Date'].year <= 2022)
    historic = read_csv(OLD / 'annual_country_type_source.csv')
    old_keys = {(r['country'], int(r['year']), r['project_type'], r['source_group']) for r in historic}
    assert old_keys == {(h, y, t, g) for h in HOSTS for y in range(2014, 2023) for t in TYPES for g in GROUPS}
    assert len(historic) == 324
    for row in historic:
        key = row['country'], int(row['year']), row['project_type'], row['source_group']
        audit.number('existing_annual_country_type_source.csv', key, 'records', row['records'], annual_counts[key])

    counts_by_table = {}
    staged_paths = []
    cached_summaries = {}
    for frequency, months, label, last_year in (('annual', 12, 'full_year', 2022), ('period', 12, 'full_year', 2022), ('annual', 9, 'jan_sep', 2023), ('period', 9, 'jan_sep', 2023)):
        filename = f'staged_{frequency}_{label}.csv'
        path = OUT / filename
        staged_paths.append(path)
        table = read_csv(path)
        stages = [str(y) for y in range(2014, last_year + 1)] if frequency == 'annual' else [k for k, v in PERIODS.items() if max(v) <= last_year]
        expected_keys = {(host, stage) for host in HOSTS for stage in stages}
        actual_keys = {(r['country'], r['stage']) for r in table}
        assert len(table) == len(expected_keys) and actual_keys == expected_keys, filename
        counts_by_table[filename] = len(table)
        for row in table:
            host, stage = row['country'], row['stage']
            years = (int(stage),) if frequency == 'annual' else PERIODS[stage]
            expected = expected_summary(rows, host, years, months)
            if frequency == 'annual':
                expected['year'] = int(stage)
            audit.fields(filename, (host, stage), row, expected)
            if frequency == 'period':
                cached_summaries[(months, host, stage)] = expected

    filename = 'staged_period_changes_full_year.csv'
    path = OUT / filename
    staged_paths.append(path)
    changes = read_csv(path)
    pairs = [('2014-2017', '2018-2019'), ('2018-2019', '2020-2022'), ('2014-2017', '2020-2022')]
    assert len(changes) == 9
    assert {(r['country'], r['from_stage'], r['to_stage']) for r in changes} == {(h, a, b) for h in HOSTS for a, b in pairs}
    counts_by_table[filename] = len(changes)
    for row in changes:
        host, initial, final = row['country'], row['from_stage'], row['to_stage']
        a, b = cached_summaries[(12, host, initial)], cached_summaries[(12, host, final)]
        first, last = a['mean_records_per_year_in_month_window'], b['mean_records_per_year_in_month_window']
        expected = {'from_mean_records_per_year': first, 'to_mean_records_per_year': last, 'mean_records_change_pct': 100 * (last / first - 1)}
        for field in a:
            if field.endswith('_share_pct'):
                expected[field + '_change_pp'] = b[field] - a[field]
        audit.fields(filename, (host, initial, final), row, expected)

    filename = 'staged_parent_history.csv'
    path = OUT / filename
    staged_paths.append(path)
    history = read_csv(path)
    assert len(history) == 6
    assert {(r['country'], r['baseline_stage'], r['post_stage']) for r in history} == {(h, '2014-2017', p) for h in HOSTS for p in ('2018-2019', '2020-2022')}
    counts_by_table[filename] = len(history)
    parent_results = []
    for row in history:
        host, post = row['country'], row['post_stage']
        base = [r for r in rows if r['Destination_Country'] == host and r['Project_Date'].year in PERIODS['2014-2017']]
        later = [r for r in rows if r['Destination_Country'] == host and r['Project_Date'].year in PERIODS[post]]
        parent_keys, sector_keys = set(map(identity, base)), {identity(r, True) for r in base}
        matched = [r for r in later if identity(r) in parent_keys]
        sector_matched = [r for r in later if identity(r, True) in sector_keys]
        new = sum(r['Project_Type'] == 'New' for r in matched)
        sector_new = sum(r['Project_Type'] == 'New' for r in sector_matched)
        expected = {'all_post_records': len(later), 'matched_parent_host_records': len(matched), 'matched_new_records': new, 'matched_expansion_records': sum(r['Project_Type'] == 'Expansion' for r in matched), 'matched_co_location_records': sum(r['Project_Type'] == 'Co-Location' for r in matched), 'matched_new_share_pct': percentage(new, len(matched)), 'same_sector_matched_records': len(sector_matched), 'same_sector_new_records': sector_new, 'same_sector_new_share_pct': percentage(sector_new, len(sector_matched))}
        audit.fields(filename, (host, post), row, expected)
        parent_results.append({'country': host, 'post_stage': post, **{k: float(v) if isinstance(v, Fraction) else v for k, v in expected.items()}})

    old_meta = json.loads((OLD / 'METHOD_AND_VALIDATION.json').read_text(encoding='utf-8'))
    protected = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in old_meta['protected_hashes'].items()}
    old_manifest = json.loads((OLD / 'TABLE_MANIFEST.json').read_text(encoding='utf-8'))
    stale = [name for name, digest in old_manifest.items() if hashlib.sha256((OLD / name).read_bytes()).hexdigest() != digest]
    raw_unchanged = hashlib.sha256(RAW.read_bytes()).hexdigest() == before
    report = {'status': 'PASS' if not audit.errors and all(protected.values()) and not stale and raw_unchanged else 'FAIL', 'method': 'Independent openpyxl read_only parse of original workbook; stdlib counts, exact Fraction shares and year denominators; no producer import.', 'raw_sha256': before, 'raw_unchanged': raw_unchanged, 'protected_hash_matches': protected, 'existing_csv_manifest_mismatches': stale, 'existing_annual_grid_cells_checked': 324, 'staged_table_row_counts': counts_by_table, 'numeric_checks_by_table': dict(audit.checked), 'total_numeric_checks': sum(audit.checked.values()), 'staged_numeric_checks': sum(n for f, n in audit.checked.items() if f.startswith('staged_')), 'errors': audit.errors, 'parent_history_independent_results': parent_results, 'full_year_sample_records_2014_2022': sum(annual_counts.values()), 'source_country_missing_records': sum(r['Source_Country'] is None for r in rows), 'delivered_record_scope': 'Raw project records; Manufacturing activity; all types and statuses. Full-year results stop in 2022; 2023 only appears in consistently Jan-Sep comparisons.', 'interpretation_boundaries': ['Mean denominators are the complete fixed calendar-year count for the named month window; no Jan-Sep annualization.', 'Shares pool records within each period; they are not unweighted averages of annual shares.', 'Parent matches refer to observed announcement history only; unmatched is not new entry.', '2018-2019 is a descriptive early-trade-conflict period; 2020-2022 is not a causal post-treatment estimand and excluding 2020 does not remove pandemic exposure.', 'Existing sample_quality.csv source_missing_pct means Inf_Source missingness, not Source_Country.'], 'checked_staged_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in staged_paths}}
    (OUT / 'STAGED_INDEPENDENT_REVIEW.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    assert report['status'] == 'PASS'


if __name__ == '__main__':
    main()
