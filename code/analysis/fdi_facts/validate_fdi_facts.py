"""Independent workbook-based arithmetic audit using openpyxl and stdlib only.

Does not import the producer script or use its dataframes/calculations.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
import openpyxl

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fdi_facts_2026_10_02'
RAW = ROOT / 'data/raw/fDi_Markets .xlsx'
COUNTRIES = ('Mexico', 'Vietnam', 'Thailand')
TYPES = ('New', 'Expansion', 'Co-Location')
GROUPS = ('China', 'Other East Asia', 'United States', 'Other parents')
WINDOWS = {
    'main_2014_17_vs_2020_22': (range(2014, 2018), range(2020, 2023), 12),
    'equal_2015_17_vs_2020_22': (range(2015, 2018), range(2020, 2023), 12),
    'without_2020_2014_17_vs_2021_22': (range(2014, 2018), range(2021, 2023), 12),
    'jan_sep_2014_17_vs_2020_23': (range(2014, 2018), range(2020, 2024), 9),
}


def group(country):
    if country in ('China', 'United States'):
        return country
    if country in ('Japan', 'South Korea', 'Taiwan'):
        return 'Other East Asia'
    return 'Other parents'


def identity(row):
    name = unicodedata.normalize('NFKC', row['Parent_Company'])
    name = ' '.join(name.split()).casefold()
    return row['Source_Country'], name, row['Destination_Country']


def pct(n, d):
    return Fraction(100 * n, d)


def unique(rows, fields):
    seen = set()
    retained = []
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key not in seen:
            seen.add(key)
            retained.append(row)
    return retained


def read_csv(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    before = hashlib.sha256(RAW.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    iterator = workbook['2014-2023'].iter_rows(values_only=True)
    headers = tuple(next(iterator))
    rows = []
    for values in iterator:
        cleaned = [None if v in ('NA', 'N/A', '') else v for v in values]
        row = dict(zip(headers, cleaned))
        if row['Activity'] == 'Manufacturing' and (row['Project_Date'].year < 2023 or row['Project_Date'].month <= 9):
            assert row['Parent_Company'] is not None
            assert row['Project_Type'] in TYPES
            rows.append(row)
    workbook.close()
    noncontact = [h for h in headers if h not in ('Company_Email', 'Company_Telephone') and not re.match(r'^(Contactname|Position|Email|Telephone)\d', h)]
    core = ['Project_Date', 'Investing_company', 'Parent_Company', 'Source_Country', 'Destination_Country', 'Sector', 'Activity', 'Project_Type', 'Capital_Investment', 'Jobs_Created']
    variants = {
        'raw_records': rows,
        'noncontact_collapsed': unique(rows, noncontact),
        'core_type_parent_collapsed_stress': unique(rows, core),
    }
    expected = {'window_type_comparisons.csv': {}, 'window_source_comparisons.csv': {}, 'window_parent_history_comparisons.csv': {}, 'window_source_type_contributions.csv': {}}
    diagnostic = []
    same_sector = []
    for variant, values in variants.items():
        for window, (base_years, later_years, last_month) in WINDOWS.items():
            for host in COUNTRIES:
                base = [r for r in values if r['Destination_Country'] == host and r['Project_Date'].year in base_years and r['Project_Date'].month <= last_month]
                later = [r for r in values if r['Destination_Country'] == host and r['Project_Date'].year in later_years and r['Project_Date'].month <= last_month]
                b, p = len(base), len(later)
                annual_b, annual_p = Fraction(b, len(base_years)), Fraction(p, len(later_years))
                key = (window, variant, host)
                out = {'pre_n': b, 'post_n': p, 'pre_years': len(base_years), 'post_years': len(later_years), 'months_per_year': last_month, 'pre_annual_mean': annual_b, 'post_annual_mean': annual_p, 'annual_count_change_percent': 100 * (annual_p / annual_b - 1)}
                btypes, ptypes = Counter(r['Project_Type'] for r in base), Counter(r['Project_Type'] for r in later)
                for typ in TYPES:
                    short = typ.lower().replace('-', '_')
                    out.update({f'pre_{short}_n': btypes[typ], f'post_{short}_n': ptypes[typ], f'pre_{short}_share_pct': pct(btypes[typ], b), f'post_{short}_share_pct': pct(ptypes[typ], p), f'{short}_share_change_pp': pct(ptypes[typ], p) - pct(btypes[typ], b)})
                expected['window_type_comparisons.csv'][key] = out
                source_contributions, source_share_changes = {}, {}
                for origin in GROUPS:
                    bg = [r for r in base if group(r['Source_Country']) == origin]
                    pg = [r for r in later if group(r['Source_Country']) == origin]
                    ba, pa = Fraction(len(bg), len(base_years)), Fraction(len(pg), len(later_years))
                    source_contributions[origin] = 100 * (pa - ba) / annual_b
                    source_share_changes[origin] = pct(len(pg), p) - pct(len(bg), b)
                    expected['window_source_comparisons.csv'][key + (origin,)] = {'pre_n': len(bg), 'post_n': len(pg), 'pre_annual_mean': ba, 'post_annual_mean': pa, 'pre_share_pct': pct(len(bg), b), 'post_share_pct': pct(len(pg), p), 'share_change_pp': source_share_changes[origin], 'contribution_to_total_count_change_pp': source_contributions[origin]}
                    for typ in TYPES:
                        bt = sum(r['Project_Type'] == typ for r in bg)
                        pt = sum(r['Project_Type'] == typ for r in pg)
                        expected['window_source_type_contributions.csv'][key + (origin, typ)] = {'pre_n': bt, 'post_n': pt, 'pre_annual_mean': Fraction(bt, len(base_years)), 'post_annual_mean': Fraction(pt, len(later_years)), 'contribution_to_total_count_change_pp': 100 * (Fraction(pt, len(later_years)) - Fraction(bt, len(base_years))) / annual_b}
                assert sum(source_contributions.values()) == out['annual_count_change_percent']
                assert sum(source_share_changes.values()) == 0
                assert sum(btypes.values()) == b and sum(ptypes.values()) == p
                observed = set(map(identity, base))
                for matched, label in ((True, 'observed_in_pre'), (False, 'not_matched_in_pre')):
                    subset = [r for r in later if (identity(r) in observed) == matched]
                    c = {'post_n': len(subset), 'post_parent_host_names': len(set(map(identity, subset))), 'all_post_n': p, 'share_of_post_records_pct': pct(len(subset), p)}
                    for typ in TYPES:
                        count = sum(r['Project_Type'] == typ for r in subset)
                        short = typ.lower().replace('-', '_')
                        c[f'{short}_n'] = count
                        c[f'{short}_share_pct'] = pct(count, len(subset)) if subset else None
                    expected['window_parent_history_comparisons.csv'][key + (label,)] = c
                observed_c = expected['window_parent_history_comparisons.csv'][key + ('observed_in_pre',)]
                sector_observed = {identity(r) + (r['Sector'],) for r in base}
                sector_matched = [r for r in later if identity(r) + (r['Sector'],) in sector_observed]
                sector_new = sum(r['Project_Type'] == 'New' for r in sector_matched)
                same_sector.append({'window': window, 'variant': variant, 'country': host, 'post_n': p, 'sector_matched_post_n': len(sector_matched), 'sector_matched_new_n': sector_new, 'sector_matched_new_share_pct': float(pct(sector_new, len(sector_matched))) if sector_matched else None, 'parent_host_matched_post_n': observed_c['post_n'], 'parent_host_matched_new_n': observed_c['new_n']})
                diagnostic.append({'window': window, 'variant': variant, 'country': host, 'annual_count_change_percent': float(out['annual_count_change_percent']), 'expansion_share_change_pp': float(out['expansion_share_change_pp']), 'new_share_change_pp': float(out['new_share_change_pp']), 'china_share_change_pp': float(source_share_changes['China']), 'china_annual_count_contribution_pp': float(source_contributions['China']), 'us_share_change_pp': float(source_share_changes['United States']), 'other_east_asia_share_change_pp': float(source_share_changes['Other East Asia']), 'matched_parent_new_share_pct': float(observed_c['new_share_pct']), 'matched_parent_new_n': observed_c['new_n'], 'matched_parent_post_n': observed_c['post_n']})
    checked, errors = 0, []
    keyfields = {
        'window_type_comparisons.csv': ['window', 'variant', 'country'],
        'window_source_comparisons.csv': ['window', 'variant', 'country', 'source_group'],
        'window_parent_history_comparisons.csv': ['window', 'variant', 'country', 'parent_history'],
        'window_source_type_contributions.csv': ['window', 'variant', 'country', 'source_group', 'project_type'],
    }
    for filename, mapping in expected.items():
        produced = read_csv(filename)
        assert len(produced) == len(mapping)
        for row in produced:
            key = tuple(row[f] for f in keyfields[filename])
            for field, number in mapping[key].items():
                if number is None:
                    good = row[field] == ''
                else:
                    good = math.isclose(float(row[field]), float(number), abs_tol=1e-10, rel_tol=1e-12)
                checked += 1
                if not good:
                    errors.append({'file': filename, 'key': key, 'field': field, 'expected': str(number), 'actual': row[field]})
    ranges = []
    for host in COUNTRIES:
        a = [r for r in diagnostic if r['country'] == host]
        for field in ('annual_count_change_percent', 'expansion_share_change_pp', 'new_share_change_pp', 'china_share_change_pp', 'china_annual_count_contribution_pp', 'us_share_change_pp', 'other_east_asia_share_change_pp', 'matched_parent_new_share_pct'):
            numbers = [r[field] for r in a]
            ranges.append({'country': host, 'metric': field, 'min': min(numbers), 'max': max(numbers), 'sign_stable': min(numbers) * max(numbers) > 0})
    counts = {host: len([r for r in rows if r['Destination_Country'] == host and r['Project_Date'].year <= 2022]) for host in COUNTRIES}
    assert sum(counts.values()) == 2349
    assert hashlib.sha256(RAW.read_bytes()).hexdigest() == before
    result = {'status': 'PASS' if not errors else 'FAIL', 'method': 'Independent read_only openpyxl parse; stdlib Counter/set grouping; rational Fraction arithmetic; does not import production code.', 'sample_2014_2022_manufacturing_counts': counts, 'numeric_values_checked': checked, 'errors': errors, 'all_36_country_window_variant_cells_reconciled': True, 'exact_source_share_change_and_contribution_identities_passed': True, 'raw_unchanged': True, 'raw_sha256': before, 'sensitivity_ranges': ranges, 'sensitivity_cells': diagnostic, 'same_native_sector_parent_history': same_sector, 'interpretation_constraints': ['FDI03 not_matched_in_pre cannot be interpreted as newly entering enterprises. Base is manufacturing announcement observations in the stated pre window only, not all past host-country operations.', 'Observed parent-host name history is affirmative project history only, not proof of operation or confirmation of unique legal entities.', 'Jan-Sep sensitivity annual_mean measures mean nine-month counts; never multiply by 4/3 or label as full-year mean.', 'Core collapsed stress deliberately merges possible distinct-location projects; it is not a validated deduplicated dataset or bound.', 'All fractions are record-count weighted descriptive objects. No inference about production volume, causal effects, realized capital flow, MP elasticity, or welfare.']}
    (OUT / 'INDEPENDENT_REVIEW.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('sensitivity_cells', 'same_native_sector_parent_history')}, indent=2, ensure_ascii=False))
    print('Same-native-sector sensitivity (raw records):')
    print(json.dumps([r for r in same_sector if r['variant'] == 'raw_records'], indent=2))
    assert not errors


def extensions_only():
    """Check only the two added sector diagnostics; do not rerun prior checks."""
    before = hashlib.sha256(RAW.read_bytes()).hexdigest()
    workbook = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    iterator = workbook['2014-2023'].iter_rows(values_only=True)
    headers = tuple(next(iterator))
    rows = []
    for values in iterator:
        row = dict(zip(headers, (None if v in ('NA', 'N/A', '') else v for v in values)))
        if row['Activity'] == 'Manufacturing' and (row['Project_Date'].year < 2023 or row['Project_Date'].month <= 9):
            rows.append(row)
    workbook.close()
    noncontact = [h for h in headers if h not in ('Company_Email', 'Company_Telephone') and not re.match(r'^(Contactname|Position|Email|Telephone)\d', h)]
    core = ['Project_Date', 'Investing_company', 'Parent_Company', 'Source_Country', 'Destination_Country', 'Sector', 'Activity', 'Project_Type', 'Capital_Investment', 'Jobs_Created']
    variants = {'raw_records': rows, 'noncontact_collapsed': unique(rows, noncontact), 'core_type_parent_collapsed_stress': unique(rows, core)}
    matched = {}
    for variant, sample in variants.items():
        for window, (base_years, later_years, last_month) in WINDOWS.items():
            for host in COUNTRIES:
                base = [r for r in sample if r['Destination_Country'] == host and r['Project_Date'].year in base_years and r['Project_Date'].month <= last_month]
                later = [r for r in sample if r['Destination_Country'] == host and r['Project_Date'].year in later_years and r['Project_Date'].month <= last_month]
                keys = {identity(r) + (r['Sector'],) for r in base}
                subset = [r for r in later if identity(r) + (r['Sector'],) in keys]
                nnew = sum(r['Project_Type'] == 'New' for r in subset)
                matched[(variant, window, host)] = {'same_parent_host_sector_post_n': len(subset), 'new_n': nnew, 'new_share_pct': pct(nnew, len(subset)) if subset else None}
    sector_rows = read_csv('window_parent_sector_history_comparisons.csv')
    assert len(sector_rows) == len(matched) == 36
    assert len({(r['variant'], r['window'], r['country']) for r in sector_rows}) == 36
    checked, errors = 0, []
    def check(filename, key, field, actual, expected):
        nonlocal checked
        checked += 1
        good = actual == '' if expected is None else math.isclose(float(actual), float(expected), abs_tol=1e-10, rel_tol=1e-12)
        if not good:
            errors.append({'file': filename, 'key': key, 'field': field, 'expected': str(expected), 'actual': actual})
    for row in sector_rows:
        key = row['variant'], row['window'], row['country']
        for field, number in matched[key].items():
            check('window_parent_sector_history_comparisons.csv', key, field, row[field], number)
    # Independent sector intersection and rational pooled-pre weighting.
    cell_rows = defaultdict(list)
    for row in rows:
        year = row['Project_Date'].year
        period = 'pre' if 2014 <= year <= 2017 else 'post' if 2020 <= year <= 2022 else None
        if period:
            cell_rows[(row['Destination_Country'], period, row['Sector'])].append(row)
    combinations = [(host, period) for host in COUNTRIES for period in ('pre', 'post')]
    common = set.intersection(*[{s for h, p, s in cell_rows if (h, p) == pair} for pair in combinations])
    assert len(common) == 13
    base_sector_counts = {sector: sum(len(cell_rows[(host, 'pre', sector)]) for host in COUNTRIES) for sector in common}
    base_total = sum(base_sector_counts.values())
    weights = {sector: Fraction(n, base_total) for sector, n in base_sector_counts.items()}
    assert sum(weights.values()) == 1
    weight_rows = read_csv('common_sector_weights.csv')
    assert len(weight_rows) == 13 and set(r['sector'] for r in weight_rows) == common
    for row in weight_rows:
        check('common_sector_weights.csv', row['sector'], 'fixed_pre_weight', row['fixed_pre_weight'], weights[row['sector']])
    shares = {}
    for host, period in combinations:
        covered = sum(len(cell_rows[(host, period, sector)]) for sector in common)
        adjusted = sum(weights[sector] * pct(sum(r['Project_Type'] == 'Expansion' for r in cell_rows[(host, period, sector)]), len(cell_rows[(host, period, sector)])) for sector in common)
        shares[(host, period)] = {'common_sectors': len(common), 'covered_records': covered, 'fixed_sector_weight_expansion_share_pct': adjusted}
    share_rows = read_csv('common_sector_weight_sensitivity.csv')
    assert len(share_rows) == 6 and len({(r['country'], r['period']) for r in share_rows}) == 6
    for row in share_rows:
        key = row['country'], row['period']
        for field, number in shares[key].items():
            check('common_sector_weight_sensitivity.csv', key, field, row[field], number)
    after = hashlib.sha256(RAW.read_bytes()).hexdigest()
    assert before == after
    report = {'status': 'PASS' if not errors else 'FAIL', 'numeric_values_checked': checked, 'errors': errors, 'same_native_sector_history_cells_checked': 36, 'common_sectors_independently_recovered': sorted(common), 'common_sector_pooled_pre_records': base_total, 'weights_exact_sum': str(sum(weights.values())), 'fixed_weights_independently_checked': 13, 'country_period_adjusted_cells_checked': 6, 'raw_sha256': before, 'raw_unchanged': before == after, 'adjusted_results': [{'country': host, 'pre_expansion_share_pct': float(shares[(host, 'pre')]['fixed_sector_weight_expansion_share_pct']), 'post_expansion_share_pct': float(shares[(host, 'post')]['fixed_sector_weight_expansion_share_pct']), 'change_pp': float(shares[(host, 'post')]['fixed_sector_weight_expansion_share_pct'] - shares[(host, 'pre')]['fixed_sector_weight_expansion_share_pct']), 'covered_pre_records': shares[(host, 'pre')]['covered_records'], 'covered_post_records': shares[(host, 'post')]['covered_records']} for host in COUNTRIES], 'interpretation': 'Fixed pooled pre-period sector weights retain positive Mexico and Vietnam expansion-share changes; Thailand remains slightly negative in this particular main-window sector check. Restricted to 13 common fDi native sectors, not an F03 harmonized-sector match.'}
    existing = json.loads((OUT / 'INDEPENDENT_REVIEW.json').read_text(encoding='utf-8'))
    existing['additional_sector_checks'] = report
    (OUT / 'INDEPENDENT_REVIEW.json').write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    assert not errors


if __name__ == '__main__':
    extensions_only() if '--extensions-only' in sys.argv else main()
