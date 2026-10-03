"""Independent display and interpretation audit of the fDi reader report.

Compares reviewed summary data with display CSVs, report HTML/Markdown,
figure data and units. Does not reopen the raw Excel or import the producer.
"""
from pathlib import Path
from html.parser import HTMLParser
import base64
import csv
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/fdi_research_baseline_2026_10_03'
OUT = ROOT / 'output/fdi_facts_reader_2026_10_03'
MP = ROOT / 'output/mp_pilot_prepare_2026_10_03'
CN = {'Mexico': '墨西哥', 'Vietnam': '越南', 'Thailand': '泰国'}
STAGES = ('2014-2017', '2018-2019', '2020-2022')
GROUPS = ('china', 'other_east_asia', 'united_states', 'other_parents')
TYPES = ('new', 'expansion', 'co_location')


def csvdict(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def csvrows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.reader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(v):
    return f'{float(v):,.2f}'


def percent(v):
    return number(v) + '%'


def countshare(row, key):
    return f"{int(row[key + '_records']):,}（{percent(row[key + '_share_pct'])}）"


class Node:
    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or []), []

    def text(self):
        return ''.join(x.text() if isinstance(x, Node) else x for x in self.children)

    def findall(self, tag):
        result = [self] if self.tag == tag else []
        for c in self.children:
            if isinstance(c, Node):
                result.extend(c.findall(tag))
        return result


class DOM(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in ('meta', 'img', 'br', 'link', 'input', 'hr', 'source'):
            self.stack.append(n)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, text):
        self.stack[-1].children.append(text)


def main():
    manifest = json.loads((OUT / 'REPORT_MANIFEST.json').read_text(encoding='utf-8'))
    reviewed = {name: json.loads((BASE / name).read_text(encoding='utf-8')) for name in ('STAGED_INDEPENDENT_REVIEW.json', 'EXPLORATORY_INDEPENDENT_REVIEW.json')}
    assert all(r['status'] == 'PASS' for r in reviewed.values())
    annual = {(r['country'], int(r['year'])): r for r in csvdict(BASE / 'exploratory_annual_full_year.csv')}
    jansep = {(r['country'], int(r['year'])): r for r in csvdict(BASE / 'exploratory_annual_jan_sep.csv')}
    period = {(r['country'], r['stage']): r for r in csvdict(BASE / 'staged_period_full_year.csv')}
    history = {(r['country'], r['post_stage']): r for r in csvdict(BASE / 'staged_parent_history.csv')}
    mp = json.loads((MP / 'PILOT_SUMMARY.json').read_text(encoding='utf-8'))
    mpseries = {int(r['year']): r for r in mp['series']}
    errors, checks, table_counts = [], 0, {}
    def equal(scope, key, field, got, expected):
        nonlocal checks
        checks += 1
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            valid = math.isclose(float(got), float(expected), abs_tol=1e-10, rel_tol=1e-12)
        else:
            valid = got == expected
        if not valid:
            errors.append({'scope': scope, 'key': key, 'field': field, 'actual': got, 'expected': expected})

    tables = {}
    tables['table_01a_annual_counts'] = [[str(y) + ('†' if y >= 2023 else '')] + [annual[c, y]['records'] for c in CN] for y in range(2014, 2025)]
    tables['table_01b_annual_china'] = [[str(y) + ('†' if y >= 2023 else '')] + [countshare(annual[c, y], 'china') for c in CN] for y in range(2014, 2025)]
    table2 = []
    for country in CN:
        for stage in (*STAGES, '2023', '2024'):
            r = period[country, stage] if stage in STAGES else annual[country, int(stage)]
            label = stage.replace('-', '—') + ('†' if stage in ('2023', '2024') else '')
            table2.append([CN[country], label, r['records']] + [countshare(r, g) for g in GROUPS])
    tables['table_02_source_composition'] = table2
    tables['table_03a_project_types'] = [[CN[c], s.replace('-', '—'), period[c, s]['records']] + [countshare(period[c, s], t) for t in TYPES] + [number(int(period[c, s]['expansion_records']) / int(period[c, s]['n_years']))] for c in CN for s in STAGES]
    tables['table_03b_known_types_2023'] = [[CN[c], f"{annual[c, 2023]['project_type_available_records']} / {annual[c, 2023]['records']}", percent(annual[c, 2023]['project_type_available_pct'])] + [f"{annual[c, 2023][t + '_records_in_known_types']}（{percent(annual[c, 2023][t + '_share_pct_of_known_types'])}）" for t in TYPES] for c in CN]
    table4 = []
    for c in CN:
        for s in ('2018-2019', '2020-2022'):
            r = history[c, s]
            table4.append([CN[c], s.replace('-', '—'), r['all_post_records'], r['matched_parent_host_records'], f"{r['matched_new_records']} / {r['matched_parent_host_records']}", percent(r['matched_new_share_pct']), f"{r['same_sector_new_records']} / {r['same_sector_matched_records']}（{percent(r['same_sector_new_share_pct'])}）"])
    tables['table_04_parent_history'] = table4
    tables['table_05a_month_windows'] = [[CN[c], f"{annual[c, 2023]['records']} → {annual[c, 2024]['records']}", f"{jansep[c, 2023]['records']} → {jansep[c, 2024]['records']}", f"{percent(annual[c, 2023]['china_share_pct'])} → {percent(annual[c, 2024]['china_share_pct'])}", f"{percent(jansep[c, 2023]['china_share_pct'])} → {percent(jansep[c, 2024]['china_share_pct'])}"] for c in CN]
    table5b = []
    for c in CN:
        for y in (2023, 2024):
            r = annual[c, y]
            cells = [f"{r[f + '_available_records']} / {r['records']}（{percent(r[f + '_available_pct'])}）" if y == 2023 else '字段未提供' for f in ('project_type', 'parent')]
            table5b.append([CN[c], str(y), r['records']] + cells)
    tables['table_05b_field_coverage'] = table5b
    tables['table_06_mp_machinery'] = [[str(y), number(r['numerator_us_affiliate_output_musd']), number(r['denominator_host_gross_output_musd']), percent(r['target_fraction'] * 100), number(r['bea_sales_musd']), number(r['bea_goods_exports_to_us_musd'])] for y, r in sorted(mpseries.items())]

    displayed = {}
    for table, expected in tables.items():
        actual = csvrows(OUT / (table + '.csv'))
        displayed[table] = actual
        table_counts[table] = len(actual) - 1
        equal('table_size', table, 'rows', len(actual) - 1, len(expected))
        for i, (got, exp) in enumerate(zip(actual[1:], expected), 1):
            equal('table_width', table, str(i), len(got), len(exp))
            for j, (a, b) in enumerate(zip(got, exp)):
                equal('display_table_cell', table, f'{i}:{j}', a, str(b))

    # Figure data are presentation transforms of the already reviewed summaries.
    fig_checks = {}
    before_fig_checks = checks
    fig1 = csvdict(OUT / 'figure_01_trends_plot_data.csv')
    equal('figure_rows', '1', 'rows', len(fig1), 33)
    for r in fig1:
        key = r['country'], int(r['year'])
        for f in ('records', 'china_records', 'china_share_pct'):
            equal('figure1', key, f, r[f], float(annual[key][f]))
    fig_checks['figure_01'] = checks - before_fig_checks
    prior = checks
    fig2 = csvdict(OUT / 'figure_02_sources_plot_data.csv')
    equal('figure_rows', '2', 'rows', len(fig2), 15)
    for r in fig2:
        c, s = r['country'], r['stage']
        ref = period[c, s] if s in STAGES else annual[c, int(s)]
        for f in ['records'] + [g + e for g in GROUPS for e in ('_records', '_share_pct')]:
            equal('figure2', (c, s), f, r[f], float(ref[f]))
        equal('figure2', (c, s), 'provisional', r['provisional'], str(s not in STAGES))
    fig_checks['figure_02'] = checks - prior
    prior = checks
    fig3 = csvdict(OUT / 'figure_03_types_plot_data.csv')
    equal('figure_rows', '3', 'rows', len(fig3), 9)
    for r in fig3:
        key = r['country'], r['stage']
        ref = period[key]
        for f in ['records', 'n_years'] + [t + e for t in TYPES for e in ('_records', '_share_pct')]:
            equal('figure3', key, f, r[f], float(ref[f]))
        equal('figure3', key, 'expansion_annual_mean', r['expansion_annual_mean'], int(ref['expansion_records']) / int(ref['n_years']))
    fig_checks['figure_03'] = checks - prior
    prior = checks
    fig4 = csvdict(OUT / 'figure_04_parent_history_plot_data.csv')
    equal('figure_rows', '4', 'rows', len(fig4), 12)
    for r in fig4:
        key = r['country'], r['post_stage']
        ref = history[key]
        sourcefields = ('matched_new_records', 'matched_parent_host_records', 'matched_new_share_pct') if r['match'] == 'parent_host' else ('same_sector_new_records', 'same_sector_matched_records', 'same_sector_new_share_pct')
        equal('figure4', key, 'baseline_stage', r['baseline_stage'], '2014-2017')
        for field, sf in zip(('new_records', 'matched_records', 'new_share_pct'), sourcefields):
            equal('figure4', key, field, r[field], float(ref[sf]))
    fig_checks['figure_04'] = checks - prior
    prior = checks
    fig5 = csvdict(OUT / 'figure_05_windows_plot_data.csv')
    equal('figure_rows', '5', 'rows', len(fig5), 12)
    for r in fig5:
        key = r['country'], int(r['year'])
        ref = annual[key] if r['window'] == 'full_year' else jansep[key]
        for f, sf in (('china_records', 'china_records'), ('all_records', 'records'), ('china_share_pct', 'china_share_pct')):
            equal('figure5', (key, r['window']), f, r[f], float(ref[sf]))
    fig_checks['figure_05'] = checks - prior
    prior = checks
    fig6 = csvdict(OUT / 'figure_06_mp_plot_data.csv')
    equal('figure_rows', '6', 'rows', len(fig6), 3)
    for r in fig6:
        year = int(r['year'])
        for field, value in mpseries[year].items():
            equal('figure6', year, field, r[field], value)
        equal('figure6', year, 'output_hundred_million_current_usd', r['output_hundred_million_current_usd'], mpseries[year]['numerator_us_affiliate_output_musd'] / 100)
        equal('figure6', year, 'share_pct', r['share_pct'], mpseries[year]['target_fraction'] * 100)
    fig_checks['figure_06'] = checks - prior

    markdown = (OUT / 'FACTS_READER.md').read_text(encoding='utf-8')
    page = (OUT / 'index.html').read_text(encoding='utf-8')
    dom = DOM()
    dom.feed(page)
    sections = dom.root.findall('section')
    equal('HTML', 'sections', 'count', len(sections), 6)
    section_checks = []
    manifest_tables = {t['id']: t for s in manifest['sections'] for t in s['tables']}
    for sec in sections:
        sid = sec.attrs['id']
        spec = next(s for s in manifest['sections'] if s['id'] == sid)
        order = [c.attrs['data-order'] for c in sec.children if isinstance(c, Node) and 'data-order' in c.attrs]
        equal('HTML_order', sid, 'ordered_blocks', order, ['1', '2', '3', '4'])
        tables_html = sec.findall('table')
        equal('HTML_tables', sid, 'count', len(tables_html), len(spec['tables']))
        for ht, tab in zip(tables_html, spec['tables']):
            cells = [[cell.text() for cell in tr.children if isinstance(cell, Node) and cell.tag in ('td', 'th')] for tr in ht.findall('tr')]
            equal('HTML_table', tab['id'], 'all_cells', cells, displayed[tab['id']])
            manifest_cells = [tab['headers']] + [[str(v) for v in r] for r in tab['rows']]
            equal('manifest_table', tab['id'], 'all_cells', manifest_cells, displayed[tab['id']])
            md_grid = '\n'.join('| ' + ' | '.join(r) + ' |' for r in displayed[tab['id']][1:])
            equal('Markdown_table', tab['id'], 'grid_present', md_grid in markdown, True)
        figures = sec.findall('figure')
        equal('HTML_figure', sid, 'count', len(figures), 1)
        imgs = sec.findall('img')
        equal('HTML_image', sid, 'count', len(imgs), 1)
        image_source = imgs[0].attrs['src']
        equal('HTML_image', sid, 'embedded', image_source.startswith('data:image/png;base64,'), True)
        data = base64.b64decode(image_source.split(',', 1)[1])
        equal('HTML_image', sid, 'matches_current_PNG', hashlib.sha256(data).hexdigest(), sha(OUT / (spec['figure'] + '.png')))
        for ext in ('png', 'svg', 'pdf'):
            equal('figure_file', spec['figure'], ext, (OUT / (spec['figure'] + '.' + ext)).is_file(), True)
        section_text = sec.text()
        for note in spec['notes']:
            equal('HTML_note', sid, 'note_present', note in section_text, True)
        for label, text in spec['interpretation']:
            equal('HTML_interpretation', sid, label, text in section_text, True)
        section_checks.append({'section': sid, 'order': order, 'tables': len(spec['tables']), 'figure': spec['figure'], 'notes': len(spec['notes']), 'interpretation_paragraphs': len(spec['interpretation'])})

    # Explicit content constraints, alongside manual sentence-level review.
    narrative = {
        'Mexico_window_reversal_explicit': all(v in markdown for v in ('17.30% → 16.15%', '14.20% → 17.78%', '不能稳健地支持')),
        '2023_known_type_denominator_explicit': '其百分比分母为类型已知记录数' in markdown and '12 月类型缺失' in markdown,
        '2023_known_types_are_Jan_Nov_not_Jan_Sep': '1—11 月' in markdown and '10—11 月' in markdown,
        '2024_missing_type_not_zero_filled': '完全没有 Project_Type' in markdown and '不能填零' in markdown,
        '2024_parent_field_not_supplied': all(row[-2:] == ['字段未提供', '字段未提供'] for row in tables['table_05b_field_coverage'] if row[1] == '2024'),
        'source_not_unverified_ultimate_control': 'Source_Country 是数据库记录的来源字段，不额外推定最终控制人' in markdown,
        'parent_denominator_records_not_unique_parents': '不是不同母公司数量' in markdown and '匹配记录中的 New 数量÷匹配记录总数' in markdown,
        'parent_matching_neither_operation_nor_entry': '不证明持续在营' in markdown and '匹配失败也不证明首次进入' in markdown,
        'same_native_sector_not_AMNE_crosswalk': '不是 AMNE 行业 crosswalk' in markdown,
        'MP_denominator_C28_all_origin_output': '墨西哥机械行业总产出' in displayed['table_06_mp_machinery'][0][2] and '墨西哥 C28 全部 gross output' in markdown,
        'MP_nominal_million_USD_table_units': '当期百万美元' in markdown and '名义金额没有扣除价格变化' in markdown,
        'no_direct_export_sales_probability': '不直接用出口÷销售构造三边销售概率' in markdown,
        'no_claimed_hgamma_estimate': '没有估计 hgamma' in markdown,
        'equal_month_comparison_no_annualization': '不将 9 个月扩算为全年' in markdown,
    }
    for key, valid in narrative.items():
        equal('narrative_boundaries', key, 'satisfied', valid, True)
    output_change = 100 * (mpseries[2022]['numerator_us_affiliate_output_musd'] / mpseries[2017]['numerator_us_affiliate_output_musd'] - 1)
    equal('narrative_number', 'MP_output_change', 'formatted_present', ('增加 ' + percent(output_change)) in markdown, True)
    totals = {y: sum(int(annual[c, y]['records']) for c in CN) for y in range(2014, 2025)}
    equal('narrative_number', 'sample_counts', '2014_2022', sum(v for y, v in totals.items() if y <= 2022), 2349)
    equal('narrative_number', 'sample_counts', '2023', totals[2023], 308)
    equal('narrative_number', 'sample_counts', '2024', totals[2024], 325)
    equal('narrative_number', 'sample_counts', 'all', sum(totals.values()), 2982)
    equal('encoding', 'HTML', 'no_replacement_char', '\ufffd' not in page, True)
    equal('encoding', 'Markdown', 'no_replacement_char', '\ufffd' not in markdown, True)
    equal('manifest', 'HTML', 'hash', sha(OUT / 'index.html'), manifest['html_sha256'])
    equal('manifest', 'Markdown', 'hash', sha(OUT / 'FACTS_READER.md'), manifest['markdown_sha256'])
    source_hashes = {p: sha(ROOT / p) == digest for p, digest in manifest['sources'].items()}
    for p, match in source_hashes.items():
        equal('source_preservation', p, 'hash_unchanged', match, True)
    recommendations = []
    if '亿美元' not in markdown:
        recommendations.append('Notes may additionally spell out figure 6 uses current hundred-million USD while table 6 uses current million USD; figure axis and numeric conversion are already correct.')
    if '连接端点的线' in markdown:
        recommendations.append('Figure 6 is a bar chart. Replace the note about connecting endpoint lines with a statement that only the three endpoints are displayed and no intervening years are interpolated.')
    result = {'status': 'PASS' if not errors else 'FAIL', 'review_type': 'Independent summary-to-presentation audit; no repeated raw-workbook audit or model estimation.', 'checks_completed': checks, 'errors': errors, 'display_tables': table_counts, 'all_nine_display_tables_match_reviewed_sources': not any(e['scope'].startswith('table') or e['scope'] == 'display_table_cell' for e in errors), 'figure_data_checks': fig_checks, 'six_HTML_sections_table_figure_notes_interpretation': section_checks, 'narrative_boundaries': narrative, 'manual_numeric_and_interpretation_review': 'All six explanation blocks reviewed; no causal, entry, realized-production or hgamma inference asserted from fDi counts. Mexico month-window reversal, 2023 known-type subsample and 2024 absent fields explicitly distinguished.', 'resolved_issue': 'AMNE table denominator and text now explicitly refer to Mexico machinery-sector total output, not all industries.', 'recommendations': recommendations, 'source_hash_matches': source_hashes, 'reviewed_report_sha256': {'index.html': sha(OUT / 'index.html'), 'FACTS_READER.md': sha(OUT / 'FACTS_READER.md'), 'REPORT_MANIFEST.json': sha(OUT / 'REPORT_MANIFEST.json')}, 'checked_display_and_figure_sha256': {p.name: sha(p) for p in sorted(OUT.glob('table_*.csv')) + sorted(OUT.glob('figure_*_plot_data.csv'))}, 'scope_limit': 'Numerical and semantic display consistency plus HTML DOM/order and image-byte checks. Browser layout QA remains in the separate visual review.'}
    (OUT / 'READER_INDEPENDENT_REVIEW.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    prose = '# Reader report independent review\n\nStatus: ' + result['status'] + '\n\n' + f'{checks} checks completed. Nine displayed tables and six figure data files were compared with already reviewed staged/exploratory summaries and the MP summary. HTML table cells, embedded PNG bytes, six section block orders, notes and interpretations were checked. No raw-workbook audit was repeated.\n\n' + 'Source definitions and interpretation boundaries: ' + ('all satisfied' if all(narrative.values()) else 'see JSON failures') + '.\n\n' + 'Recommendations:\n' + ('\n'.join('- ' + x for x in recommendations) if recommendations else '- None outstanding.') + '\n\nFull evidence and hashes: READER_INDEPENDENT_REVIEW.json.\n'
    (OUT / 'READER_INDEPENDENT_REVIEW.md').write_text(prose, encoding='utf-8')
    print(json.dumps({'status': result['status'], 'checks_completed': checks, 'errors': errors, 'table_rows': table_counts, 'recommendations': recommendations}, ensure_ascii=True, indent=2))
    assert not errors


if __name__ == '__main__':
    main()
