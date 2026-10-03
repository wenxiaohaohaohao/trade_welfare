"""Independent review of exploratory 2023/2024 delivery records.

Reads both original workbook sheets, retaining every Manufacturing record.
Does not import the producer or change staged/old facts.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import csv
import hashlib
import json
import math
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'data/raw/fDi_Markets .xlsx'
OUT = ROOT / 'output/fdi_research_baseline_2026_10_03'
HOSTS = ('Mexico', 'Vietnam', 'Thailand')
GROUPS = {'China': 'china', 'Other East Asia': 'other_east_asia', 'United States': 'united_states', 'Other parents': 'other_parents'}
TYPES = {'New': 'new', 'Expansion': 'expansion', 'Co-Location': 'co_location'}


def read_csv(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def missing(v):
    return v is None or isinstance(v, str) and v.strip() in ('', 'NA', 'N/A')


def percentage(n, d):
    return Fraction(n * 100, d) if d else None


def origin(v):
    if v in ('China', 'United States'):
        return v
    return 'Other East Asia' if v in ('Japan', 'South Korea', 'Taiwan') else 'Other parents'


def independently_load():
    workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    rows, schemas = [], {}
    names = {'Project_Date': 'date', 'Investing_company': 'company', 'Source_Country': 'source', 'Destination_Country': 'destination', 'Sector': 'sector', 'Activity': 'activity'}
    for sheet in ('2014-2023', '2024'):
        iterator = workbook[sheet].iter_rows(values_only=True)
        header = next(iterator)
        schemas[sheet] = list(header)
        values = list(iterator)
        duplicates = Counter(tuple(v) for v in values if any(x is not None for x in v))
        seen = Counter()
        for row_index, v in enumerate(values, 2):
            if not any(x is not None for x in v):
                continue
            seen[tuple(v)] += 1
            record = dict(zip(header, v))
            def get(field):
                return record.get(names.get(field, field) if sheet == '2024' else field)
            if get('Activity') != 'Manufacturing':
                continue
            date = get('Project_Date')
            assert 2014 <= date.year <= 2024
            assert get('Destination_Country') in HOSTS
            assert not missing(get('Source_Country'))
            row = {'sheet': sheet, 'excel_row': row_index, 'date': date.date().isoformat(), 'year': date.year, 'month': date.month, 'company': get('Investing_company'), 'parent': None if missing(get('Parent_Company')) else get('Parent_Company'), 'country': get('Destination_Country'), 'source_country': get('Source_Country'), 'source_group': origin(get('Source_Country')), 'sector': get('Sector'), 'activity': 'Manufacturing', 'project_type': None if missing(get('Project_Type')) else get('Project_Type'), 'project_status': None if missing(get('Project_Status')) else get('Project_Status'), 'project_type_field_present': 'Project_Type' in header, 'parent_field_present': 'Parent_Company' in header, 'exact_visible_field_duplicate_size': duplicates[tuple(v)], 'exact_visible_field_duplicate_excess': int(seen[tuple(v)] > 1)}
            rows.append(row)
    workbook.close()
    return rows, schemas


class Audit:
    def __init__(self):
        self.counts, self.errors = Counter(), []

    def equal(self, table, key, field, got, expected):
        self.counts[table] += 1
        if expected is None:
            good = got in ('', None)
        elif isinstance(expected, bool):
            good = got == str(expected)
        elif isinstance(expected, (int, float, Fraction)):
            good = math.isclose(float(got), float(expected), rel_tol=1e-12, abs_tol=1e-10)
        else:
            good = got == expected
        if not good:
            self.errors.append({'table': table, 'key': key, 'field': field, 'expected': str(expected), 'actual': got})


def summary(rows, host, year, months, schemas):
    sample = [r for r in rows if r['country'] == host and r['year'] == year and r['month'] in months]
    n = len(sample)
    sheet = '2024' if year == 2024 else '2014-2023'
    result = {'months_per_year': len(months), 'records': n, 'observed_months': len({r['month'] for r in sample}), 'requested_months': ','.join(map(str, months)), 'coverage_status': 'supplier_followup_required' if year >= 2023 else 'historical_schema;coverage_unverified'}
    for value, prefix in GROUPS.items():
        k = sum(r['source_group'] == value for r in sample)
        result[prefix + '_records'] = k
        result[prefix + '_share_pct'] = percentage(k, n)
    for prefix, native in (('project_type', 'Project_Type'), ('parent', 'Parent_Company')):
        available = sum(r[prefix] is not None for r in sample)
        result[prefix + '_field_present'] = native in schemas[sheet]
        result[prefix + '_available_records'] = available
        result[prefix + '_missing_records'] = n - available
        result[prefix + '_available_pct'] = percentage(available, n)
    known = [r for r in sample if r['project_type'] is not None]
    assert all(r['project_type'] in TYPES for r in known)
    for value, prefix in TYPES.items():
        k = sum(r['project_type'] == value for r in known)
        result[prefix + '_records_in_known_types'] = k if known else None
        result[prefix + '_share_pct_of_known_types'] = percentage(k, len(known))
    result['exact_visible_field_duplicate_rows'] = sum(r['exact_visible_field_duplicate_size'] > 1 for r in sample)
    result['exact_visible_field_duplicate_excess'] = sum(r['exact_visible_field_duplicate_excess'] for r in sample)
    assert sum(result[g + '_records'] for g in GROUPS.values()) == n
    if n:
        assert sum(result[g + '_share_pct'] for g in GROUPS.values()) == 100
    return result


def main():
    before = hashlib.sha256(RAW.read_bytes()).hexdigest()
    rows, schemas = independently_load()
    audit = Audit()
    paths, sizes = [], {}
    main_summaries = []
    for name, months in (('exploratory_annual_full_year.csv', tuple(range(1, 13))), ('exploratory_annual_jan_sep.csv', tuple(range(1, 10)))):
        table = read_csv(name)
        paths.append(OUT / name)
        sizes[name] = len(table)
        keys = {(r['country'], int(r['year'])) for r in table}
        assert len(table) == 33 and keys == {(h, y) for h in HOSTS for y in range(2014, 2025)}
        for r in table:
            host, year = r['country'], int(r['year'])
            expected = summary(rows, host, year, months, schemas)
            for field, number in expected.items():
                audit.equal(name, (host, year), field, r[field], number)
            if year >= 2023 and len(months) == 12:
                main_summaries.append({'country': host, 'year': year, **{k: float(v) if isinstance(v, Fraction) else v for k, v in expected.items()}})
        # Explicit reconciliation to verified old-year/staged annual accounting.
        staged = read_csv('staged_annual_full_year.csv' if len(months) == 12 else 'staged_annual_jan_sep.csv')
        lookup = {(r['country'], int(r['year'])): r for r in table}
        for old in staged:
            key = old['country'], int(old['year'])
            new = lookup[key]
            for field in ['records'] + [g + suffix for g in GROUPS.values() for suffix in ('_records', '_share_pct')]:
                audit.equal('staged_reconciliation_' + name, key, field, new[field], float(old[field]))

    name = 'exploratory_monthly_2023_2024.csv'
    table = read_csv(name)
    paths.append(OUT / name)
    sizes[name] = len(table)
    assert len(table) == 72
    assert {(r['country'], int(r['year']), int(r['month'])) for r in table} == {(h, y, m) for h in HOSTS for y in (2023, 2024) for m in range(1, 13)}
    monthly = []
    for r in table:
        host, year, month = r['country'], int(r['year']), int(r['month'])
        expected = summary(rows, host, year, (month,), schemas)
        for field, number in expected.items():
            audit.equal(name, (host, year, month), field, r[field], number)
        monthly.append({'country': host, 'year': year, 'month': month, 'records': expected['records']})

    name = 'exploratory_monthly_source_country_2023_2024.csv'
    table = read_csv(name)
    paths.append(OUT / name)
    sizes[name] = len(table)
    expected_sources = Counter((r['country'], r['year'], r['month'], r['source_country']) for r in rows if r['year'] >= 2023)
    expected_months = Counter((r['country'], r['year'], r['month']) for r in rows if r['year'] >= 2023)
    assert len(table) == len(expected_sources)
    assert {(r['country'], int(r['year']), int(r['month']), r['source_country']) for r in table} == set(expected_sources)
    for r in table:
        key = r['country'], int(r['year']), int(r['month']), r['source_country']
        audit.equal(name, key, 'records', r['records'], expected_sources[key])
        audit.equal(name, key, 'all_source_month_records', r['all_source_month_records'], expected_months[key[:3]])
        audit.equal(name, key, 'source_group', r['source_group'], origin(key[3]))

    name = 'exploratory_manufacturing_records.csv'
    table = read_csv(name)
    paths.append(OUT / name)
    sizes[name] = len(table)
    lookup = {(r['sheet'], r['excel_row']): r for r in rows}
    assert len(table) == len(lookup) == len(rows) == 2982
    assert {(r['sheet'], int(r['excel_row'])) for r in table} == set(lookup)
    for r in table:
        key = r['sheet'], int(r['excel_row'])
        expected = lookup[key]
        if expected['year'] >= 2023:
            for field, value in expected.items():
                audit.equal(name, key, field, r[field], value)
    duplicate_2024 = [r for r in rows if r['year'] == 2024]
    assert len(duplicate_2024) == 325
    assert sum(r['exact_visible_field_duplicate_excess'] for r in duplicate_2024) == 9
    assert sum(r['exact_visible_field_duplicate_size'] > 1 for r in duplicate_2024) == 16
    assert all(r['parent'] is None and r['project_type'] is None for r in duplicate_2024)
    staged_review = json.loads((OUT / 'STAGED_INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
    staged_unchanged = {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() == digest for name, digest in staged_review['checked_staged_sha256'].items()}
    raw_unchanged = before == hashlib.sha256(RAW.read_bytes()).hexdigest()
    report = {'status': 'PASS' if not audit.errors and raw_unchanged and all(staged_unchanged.values()) else 'FAIL', 'method': 'Independent openpyxl read_only parse of both raw sheets; native-schema checks, stdlib Counter/Fraction; no producer import.', 'raw_sha256': before, 'raw_unchanged': raw_unchanged, 'staged_tables_unchanged': staged_unchanged, 'table_rows_checked': sizes, 'checks_by_table': dict(audit.counts), 'total_value_checks': sum(audit.counts.values()), 'errors': audit.errors, 'all_2982_selected_raw_rows_retained_by_exact_sheet_row_provenance': True, 'manufacturing_2024_rows': 325, 'manufacturing_2024_duplicate_candidate_rows': 16, 'manufacturing_2024_duplicate_excess_retained': 9, '2024_type_and_parent_absent_in_raw_schema': True, '2024_unknown_type_counts_and_shares_remain_null': True, 'observed_empty_manufacturing_months': [r for r in monthly if r['records'] == 0], 'annual_2023_2024_independent_results': main_summaries, 'monthly_2023_2024_independent_counts': monthly, 'monthly_source_counter_cells_checked': len(expected_sources), 'limitations': ['The verification establishes delivered-record arithmetic and preservation, not coverage of all economic projects.', '2023 full-year type shares are explicitly shares among known-type records; missing December types are not classified as zero.', '2024 company is never substituted for Parent_Company; missing fields do not become zero projects of any type.', 'No observed records in a Manufacturing month is not proof of zero population activity.', 'Exact duplicates of the eight visible 2024 fields are retained; site information may distinguish projects.', 'All Jan-Sep comparisons use the same month range; no extrapolation to annual totals.'], 'checked_exploratory_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (OUT / 'EXPLORATORY_INDEPENDENT_REVIEW.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('annual_2023_2024_independent_results', 'monthly_2023_2024_independent_counts')}, ensure_ascii=False, indent=2))
    assert report['status'] == 'PASS'


if __name__ == '__main__':
    main()
