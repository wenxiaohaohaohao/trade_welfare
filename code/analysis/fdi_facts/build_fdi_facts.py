"""Reproducible, descriptive project-record facts; never modify the raw workbook."""
from pathlib import Path
import hashlib
import json
import os
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fdi_facts_2026_10_02'
TMP = ROOT / 'tmp/fdi_facts_2026_10_02'
OUT.mkdir(parents=True, exist_ok=True)
TMP.mkdir(parents=True, exist_ok=True)
os.environ['TMP'] = str(TMP)
os.environ['TEMP'] = str(TMP)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd
import openpyxl

RAW = ROOT / 'data/raw/fDi_Markets .xlsx'
COUNTRIES = ['Mexico', 'Vietnam', 'Thailand']
TYPES = ['New', 'Expansion', 'Co-Location']
GROUPS = ['China', 'Other East Asia', 'United States', 'Other parents']
WINDOWS = {
    'main_2014_17_vs_2020_22': (list(range(2014, 2018)), list(range(2020, 2023)), 12),
    'equal_2015_17_vs_2020_22': (list(range(2015, 2018)), list(range(2020, 2023)), 12),
    'without_2020_2014_17_vs_2021_22': (list(range(2014, 2018)), [2021, 2022], 12),
    'jan_sep_2014_17_vs_2020_23': (list(range(2014, 2018)), list(range(2020, 2024)), 9),
}

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(name, obj):
    (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def table(name, obj):
    df = pd.DataFrame(obj)
    df.to_csv(OUT / (name + '.csv'), index=False, encoding='utf-8-sig', float_format='%.17g')
    return df

def norm(v):
    if pd.isna(v):
        return ''
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', str(v))).strip().casefold()

def origin(v):
    if v == 'China': return 'China'
    if v in ['Japan', 'South Korea', 'Taiwan']: return 'Other East Asia'
    if v == 'United States': return 'United States'
    return 'Other parents'

def load():
    expected = json.loads((ROOT / 'output/audits/fdi_markets_2026_10_02/validation.json').read_text(encoding='utf-8'))['raw_sha256']
    assert sha(RAW) == expected, 'Input differs from the audited workbook; re-audit before rebuilding.'
    wb = openpyxl.load_workbook(RAW, read_only=True, data_only=True)
    ws = wb['2014-2023']
    it = ws.iter_rows(values_only=True)
    headers = list(next(it))
    df = pd.DataFrame(it, columns=headers)
    wb.close()
    df.insert(0, 'excel_row', np.arange(2, len(df) + 2))
    df = df.replace({'NA': None, 'N/A': None, '': None})
    df['date'] = pd.to_datetime(df.Project_Date)
    df['year'] = df.date.dt.year
    df['month'] = df.date.dt.month
    df['source_group'] = df.Source_Country.map(origin)
    df['parent_normalized'] = df.Parent_Company.map(norm)
    df['parent_host_key'] = df.Source_Country.astype(str) + '|' + df.parent_normalized + '|' + df.Destination_Country
    # No fuzzy entity matching, historical ownership imputation or unknown-to-zero conversion.
    df['parent_key_valid'] = df.Parent_Company.notna() & df.parent_normalized.ne('')
    protected = [RAW, ROOT / 'output/stylized_facts_2026_09_12/F03/fact.json', ROOT / 'output/stylized_facts_2026_09_12/F04/fact.json', ROOT / 'output/stylized_facts_2026_09_12/F03/parent_contributions.csv', ROOT / 'output/stylized_facts_2026_09_12/F04/country_components.csv']
    protected_hashes = {str(p.relative_to(ROOT)): sha(p) for p in protected}
    return df, headers, protected_hashes

def variants(df, headers):
    # Only contact fields are excluded. Profile figures remain in the conservative key.
    noncontact = [h for h in headers if h not in ['Company_Email', 'Company_Telephone'] and not re.match(r'^(Contactname|Position|Email|Telephone)\d', h)]
    core = ['date', 'Investing_company', 'Parent_Company', 'Source_Country', 'Destination_Country', 'Sector', 'Activity', 'Project_Type', 'Capital_Investment', 'Jobs_Created']
    df['noncontact_candidate_group'] = df.groupby(noncontact, dropna=False, sort=False).ngroup()
    df['core_stress_group'] = df.groupby(core, dropna=False, sort=False).ngroup()
    return {'raw_records': df, 'noncontact_collapsed': df.drop_duplicates(noncontact), 'core_type_parent_collapsed_stress': df.drop_duplicates(core)}

def analyze_window(df, window, variant):
    pre, post, month_max = WINDOWS[window]
    sample = df.loc[df.year.isin(pre + post) & df.month.le(month_max)]
    if not sample.parent_key_valid.all(): raise AssertionError('Parent matching cannot treat missing names as entities.')
    result, src, cohort, joint = [], [], [], []
    for country in COUNTRIES:
        a = sample[sample.Destination_Country.eq(country)]
        b = a[a.year.isin(pre)]
        p = a[a.year.isin(post)]
        d = {'window': window, 'variant': variant, 'country': country, 'months_per_year': month_max, 'pre_years': len(pre), 'post_years': len(post), 'pre_n': len(b), 'post_n': len(p), 'pre_annual_mean': len(b) / len(pre), 'post_annual_mean': len(p) / len(post)}
        d['annual_count_change_percent'] = 100 * (d['post_annual_mean'] / d['pre_annual_mean'] - 1)
        for t in TYPES:
            k = t.lower().replace('-', '_')
            nb, np_ = int(b.Project_Type.eq(t).sum()), int(p.Project_Type.eq(t).sum())
            d.update({f'pre_{k}_n': nb, f'post_{k}_n': np_, f'pre_{k}_share_pct': 100 * nb / len(b), f'post_{k}_share_pct': 100 * np_ / len(p), f'{k}_share_change_pp': 100 * (np_ / len(p) - nb / len(b))})
        result.append(d)
        for g in GROUPS:
            bg, pg = b[b.source_group.eq(g)], p[p.source_group.eq(g)]
            nb, np_ = len(bg), len(pg)
            sr = {'window': window, 'variant': variant, 'country': country, 'source_group': g, 'pre_n': nb, 'post_n': np_, 'pre_annual_mean': nb / len(pre), 'post_annual_mean': np_ / len(post), 'pre_share_pct': 100 * nb / len(b), 'post_share_pct': 100 * np_ / len(p)}
            sr['share_change_pp'] = sr['post_share_pct'] - sr['pre_share_pct']
            sr['contribution_to_total_count_change_pp'] = 100 * (sr['post_annual_mean'] - sr['pre_annual_mean']) / d['pre_annual_mean']
            src.append(sr)
            for t in TYPES:
                nbt, npt = int(bg.Project_Type.eq(t).sum()), int(pg.Project_Type.eq(t).sum())
                joint.append({'window': window, 'variant': variant, 'country': country, 'source_group': g, 'project_type': t, 'pre_n': nbt, 'post_n': npt, 'pre_annual_mean': nbt / len(pre), 'post_annual_mean': npt / len(post), 'contribution_to_total_count_change_pp': 100 * (npt / len(post) - nbt / len(pre)) / d['pre_annual_mean']})
        keys = set(b.parent_host_key)
        for label, sub in [('observed_in_pre', p[p.parent_host_key.isin(keys)]), ('not_matched_in_pre', p[~p.parent_host_key.isin(keys)])]:
            c = {'window': window, 'variant': variant, 'country': country, 'parent_history': label, 'post_n': len(sub), 'post_parent_host_names': sub.parent_host_key.nunique(), 'all_post_n': len(p), 'share_of_post_records_pct': 100 * len(sub) / len(p)}
            for t in TYPES:
                k = t.lower().replace('-', '_')
                n = int(sub.Project_Type.eq(t).sum())
                c[f'{k}_n'] = n
                c[f'{k}_share_pct'] = 100 * n / len(sub) if len(sub) else None
            cohort.append(c)
    return result, src, cohort, joint

def main():
    all_rows, headers, protected = load()
    eligible = all_rows[all_rows.date.le('2023-09-01') & all_rows.Activity.eq('Manufacturing')].copy()
    assert eligible.Destination_Country.isin(COUNTRIES).all()
    assert eligible.Project_Type.isin(TYPES).all()
    variants_ = variants(eligible, headers)
    main_sample = variants_['raw_records'][variants_['raw_records'].year.le(2022)]
    main_cols = ['excel_row', 'date', 'year', 'month', 'Investing_company', 'Parent_Company', 'parent_normalized', 'parent_host_key', 'Source_Country', 'source_group', 'Destination_Country', 'Sector', 'Activity', 'Project_Type', 'Project_Status', 'Capital_Investment', 'Estimated2', 'Jobs_Created', 'Estimated1', 'Inf_Source', 'noncontact_candidate_group', 'core_stress_group']
    table('manufacturing_records_with_audit_flags', eligible[main_cols])
    blocks = [[], [], [], []]
    for name, df in variants_.items():
        for window in WINDOWS:
            for dest, records in zip(blocks, analyze_window(df, window, name)):
                dest.extend(records)
    comp, src, cohort, joint = [table(n, b) for n, b in zip(['window_type_comparisons', 'window_source_comparisons', 'window_parent_history_comparisons', 'window_source_type_contributions'], blocks)]
    primary = lambda x: x[x.window.eq('main_2014_17_vs_2020_22') & x.variant.eq('raw_records')]
    table('FDI01_type_composition', primary(comp))
    table('FDI02_source_composition', primary(src))
    table('FDI03_parent_history', primary(cohort))
    table('FDI02_source_type_contributions', primary(joint))
    ix = pd.MultiIndex.from_product([COUNTRIES, range(2014, 2023), TYPES, GROUPS], names=['country', 'year', 'project_type', 'source_group'])
    annual = main_sample.groupby(['Destination_Country', 'year', 'Project_Type', 'source_group']).size()
    annual.index.names = ix.names
    annual = annual.reindex(ix, fill_value=0).rename('records').reset_index()
    table('annual_country_type_source', annual)
    pooled = []
    for country in COUNTRIES:
        a = main_sample[main_sample.Destination_Country.eq(country)]
        for t in TYPES:
            n = int(a.Project_Type.eq(t).sum())
            pooled.append({'country': country, 'type': t, 'n': n, 'total_n': len(a), 'share_pct': 100 * n / len(a)})
    table('pooled_type_2014_2022', pooled)
    sector = []
    for (country, sec), a in main_sample.groupby(['Destination_Country', 'Sector']):
        for period, years in [('pre', list(range(2014, 2018))), ('post', [2020, 2021, 2022])]:
            z = a[a.year.isin(years)]
            sector.append({'country': country, 'sector': sec, 'period': period, 'n': len(z), 'annual_mean': len(z) / len(years), **{t: int(z.Project_Type.eq(t).sum()) for t in TYPES}, 'expansion_share_pct': 100 * z.Project_Type.eq('Expansion').mean() if len(z) else None})
    table('native_sector_type', sector)
    # Fixed sector weights on sectors observed in all three countries in both periods.
    secdf = pd.DataFrame(sector)
    common = secdf.groupby('sector').filter(lambda x: len(x) == 6 and x.n.gt(0).all()).sector.unique()
    pre_weights = secdf[secdf.sector.isin(common) & secdf.period.eq('pre')].groupby('sector').n.sum()
    pre_weights = pre_weights / pre_weights.sum()
    adjusted = []
    for (country, period), a in secdf[secdf.sector.isin(common)].groupby(['country', 'period']):
        adjusted.append({'country': country, 'period': period, 'common_sectors': len(common), 'covered_records': int(a.n.sum()), 'fixed_sector_weight_expansion_share_pct': float((a.set_index('sector').expansion_share_pct * pre_weights).sum())})
    table('common_sector_weight_sensitivity', adjusted)
    table('common_sector_weights', pre_weights.rename('fixed_pre_weight').reset_index())
    # Illustrative positive matches only: no claims about actual entry or operation.
    pre = main_sample[main_sample.year.between(2014, 2017)]
    post = main_sample[main_sample.year.between(2020, 2022)]
    positive = post[post.parent_host_key.isin(set(pre.parent_host_key)) & post.Project_Type.eq('New')]
    table('FDI03_positive_match_records', positive[main_cols])
    sector_history = []
    for variant, df in variants_.items():
        for window, (pre_years, post_years, max_month) in WINDOWS.items():
            z = df[df.month.le(max_month)]
            pre_z = z[z.year.isin(pre_years)]
            known = set(zip(pre_z.parent_host_key, pre_z.Sector))
            post_z = z[z.year.isin(post_years)].copy()
            observed = post_z.apply(lambda r: (r.parent_host_key, r.Sector) in known, axis=1)
            for country in COUNTRIES:
                a = post_z[observed & post_z.Destination_Country.eq(country)]
                sector_history.append({'variant':variant, 'window':window, 'country':country, 'same_parent_host_sector_post_n':len(a), 'new_n':int(a.Project_Type.eq('New').sum()), 'new_share_pct':100*a.Project_Type.eq('New').mean() if len(a) else None})
    table('window_parent_sector_history_comparisons', sector_history)
    quality = []
    for country in COUNTRIES:
        a = main_sample[main_sample.Destination_Country.eq(country)]
        quality.append({'country': country, 'main_rows': len(a), 'new_n': int(a.Project_Type.eq('New').sum()), 'expansion_n': int(a.Project_Type.eq('Expansion').sum()), 'co_location_n': int(a.Project_Type.eq('Co-Location').sum()), 'jobs_estimated_yes_pct': 100 * a.Estimated1.eq('Yes').mean(), 'capex_estimated_yes_pct': 100 * a.Estimated2.eq('Yes').mean(), 'source_missing_pct': 100 * a.Inf_Source.isna().mean(), 'noncontact_collapsed_rows': len(variants_['noncontact_collapsed'].query('year<=2022').loc[lambda x:x.Destination_Country.eq(country)]), 'core_stress_rows': len(variants_['core_type_parent_collapsed_stress'].query('year<=2022').loc[lambda x:x.Destination_Country.eq(country)])})
    table('sample_quality', quality)
    sums = src.groupby(['window', 'variant', 'country']).agg(contribution=('contribution_to_total_count_change_pp','sum'), pre_share=('pre_share_pct','sum'), post_share=('post_share_pct','sum')).reset_index()
    rec = comp.merge(sums, on=['window', 'variant', 'country'])
    checks = {'source_contributions_add_to_total_change': bool(np.allclose(rec.annual_count_change_percent, rec.contribution, atol=1e-10)), 'source_shares_sum_to_100': bool(np.allclose(rec.pre_share, 100) and np.allclose(rec.post_share, 100)), 'type_counts_add_to_total': bool((comp[[f'pre_{t}_n' for t in ['new','expansion','co_location']]].sum(axis=1) == comp.pre_n).all() and (comp[[f'post_{t}_n' for t in ['new','expansion','co_location']]].sum(axis=1) == comp.post_n).all()), 'parent_history_partition_exact': bool(cohort.groupby(['window','variant','country']).post_n.sum().reset_index().merge(comp, on=['window','variant','country'], suffixes=('_cohort','_all')).eval('post_n_cohort==post_n_all').all()), 'annual_grid_includes_observed_zero_cells': len(annual)==3*9*3*4, 'annual_grid_reconciles': int(annual.records.sum())==len(main_sample), 'all_protected_files_unchanged': all(sha(ROOT/p)==h for p,h in protected.items())}
    assert all(checks.values()), checks
    contract = {'status':'computed_pending_independent_review', 'gate':'Gate 2 supplementary project evidence; Gate 3 claim boundary only', 'raw_sha256':sha(RAW), 'unit':'project record, not verified unique plant or enterprise', 'primary_sample':'Activity exactly Manufacturing; destinations Mexico/Vietnam/Thailand; 2014-2022; all origins/types/statuses retained', 'windows':{k:{'pre':p,'post':s,'max_month':m} for k,(p,s,m) in WINDOWS.items()}, 'counts':'annual means use all fixed calendar years, including zero-count years; shares are pooled record-count shares within each period', 'deduplication':'All records retained in primary. Noncontact exact collapse is sensitivity; type-and-parent-preserving core collapse is deliberately aggressive stress, not a true deduplicated series or bound.', 'parent_matching':'NFKC plus whitespace and case normalization; exact Source_Country + Parent_Company + Destination_Country; no fuzzy aliases; positive history is observed project history, not proof of operation. Unmatched is not entry.', 'sector_scope':'All native fDi sectors with Manufacturing activity. No claim of matching F03 six-sector ISIC universe.', 'source_groups':{'China':['China'], 'Other East Asia':['Japan','South Korea','Taiwan'], 'United States':['United States'], 'Other parents':'all others, including Hong Kong and Singapore'}, 'amount_and_jobs':'Not headline weights or production proxies. Vendor units unconfirmed; estimates frequent.', 'stats':'Descriptive delivered-sample accounting, no tests, confidence intervals, causality or welfare estimates.', 'protected_hashes':protected, 'checks':checks, 'versions':{'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,'openpyxl':openpyxl.__version__}}
    write_json('METHOD_AND_VALIDATION.json', contract)
    summary={'sample_quality':quality,'FDI01':primary(comp).to_dict('records'),'FDI02':primary(src).to_dict('records'),'FDI03':primary(cohort).to_dict('records'),'common_sector_adjustment':adjusted,'checks':checks}
    write_json('RESULTS.json', summary)
    manifest = {p.name:sha(p) for p in OUT.glob('*.csv')}
    write_json('TABLE_MANIFEST.json', manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
