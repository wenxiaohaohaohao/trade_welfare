"""Package already computed and independently checked fDi facts; raw inputs stay read-only."""
from pathlib import Path
import csv
import hashlib
import html
import json
import re
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'output/fdi_facts_2026_10_02'
CN = {'Mexico': '墨西哥', 'Vietnam': '越南', 'Thailand': '泰国'}
MAIN = 'main_2014_17_vs_2020_22'


def read_json(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def rows(name):
    with (OUT / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


result = read_json('RESULTS.json')
method = read_json('METHOD_AND_VALIDATION.json')
review = read_json('INDEPENDENT_REVIEW.json')
fig_review = read_json('FIGURE_REVIEW.json')
assert review['status'] == 'PASS' and not review['errors']
assert review['additional_sector_checks']['status'] == 'PASS'
assert fig_review['status'] == 'passed'
assert all(result['checks'].values())
for name, expected in read_json('TABLE_MANIFEST.json').items():
    assert sha(OUT / name) == expected, name
for name, expected in method['protected_hashes'].items():
    assert sha(ROOT / name) == expected, name
for item in fig_review['figure_outputs']:
    assert sha(OUT / item['filename']) == item['sha256'], item['filename']
method['status'] = 'descriptive_computation_independently_verified_coverage_pending'
method['independent_review'] = 'INDEPENDENT_REVIEW.json'
method['figure_review'] = 'FIGURE_REVIEW.json'
write_json('METHOD_AND_VALIDATION.json', method)

types = {r['country']: r for r in result['FDI01']}
china = {r['country']: r for r in result['FDI02'] if r['source_group'] == 'China'}
matched = {r['country']: r for r in result['FDI03'] if r['parent_history'] == 'observed_in_pre'}
unmatched = {r['country']: r for r in result['FDI03'] if r['parent_history'] == 'not_matched_in_pre'}
same_sector = {r['country']: r for r in rows('window_parent_sector_history_comparisons.csv') if r['window'] == MAIN and r['variant'] == 'raw_records'}
ranges = {(r['country'], r['metric']): r for r in review['sensitivity_ranges']}
quality = {r['country']: r for r in result['sample_quality']}


def f(value):
    return f'{float(value):,.2f}'


def pair(a, b, suffix=''):
    return f'{f(a)}{suffix} → {f(b)}{suffix}'


def span(country, metric):
    r = ranges[country, metric]
    return f"{r['min']:+.2f} 至 {r['max']:+.2f}"


md, webpage = [], []
links = []


def inline(value):
    value = html.escape(str(value))
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    def link(m):
        label, target = m.groups()
        links.append(html.unescape(target))
        return f'<a href="{target}">{label}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, value)


def heading(value):
    md.append(f'**{value}**')
    webpage.append(f'<h2>{html.escape(value)}</h2>')


def p(value):
    md.append(value)
    webpage.append(f'<p>{inline(value)}</p>')


def table(headers, values):
    md.append('\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(map(str, r)) + ' |' for r in values]))
    webpage.append('<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{inline(v)}</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(v)}</td>' for v in r) + '</tr>' for r in values) + '</tbody></table></div>')


def figure(stem, caption):
    assert (OUT / f'{stem}.png').exists()
    md.append(f'![{caption}]({stem}.png)')
    webpage.append(f'<figure><img src="{stem}.svg" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>')
    links.append(f'{stem}.svg')
    p(f'[图形 PDF]({stem}.pdf) · [可编辑 SVG]({stem}.svg) · [PNG]({stem}.png)')


p('**现有 fDi Markets 数据的使用方法与三条补充 facts**')
p('数据审核批次：2026-10-02；说明完成于 2026-10-03。研究对象：墨西哥、越南、泰国作为目的地的跨国制造活动项目记录。本文使用当前交付的 Excel 计算，尚未把供应商后续补充视为已完成。')
p('**这份数据现在可以用来描述项目的调整方式、来源构成以及母公司历史记录，最适合作为 F03/F04 的项目层补充。** 已生成三条 facts：墨西哥和越南扩建记录份额上升；两国中国来源份额上升，但数量变化不同；基期已观察到的母公司—东道国组合中，后期仍包含新建项目。第三条对解释 F04 的 continuing links 最有价值。')
p('这些结果服务于 JIE Gate 2 的机制证据，并限定 Gate 3 的解释。它们尚不能识别 MP 弹性，也不能量化 trade-network flexibility 与 multinational-production flexibility 分别或共同提供多少 fragmentation insurance。')

heading('先按以下规则使用现有文件')
table(['项目', '本次实际采用的规则', '用途与理由'], [
    ['国家及方向', 'Destination_Country 为 Mexico、Vietnam、Thailand；保留所有来源国', '研究进入三个东道国的生产项目，不能只筛中国来源后再计算来源构成'],
    ['活动', 'Activity = Manufacturing；保留全部原生 Sector', '直接对应生产活动；不将销售、总部、物流、研发等混入制造活动主样本'],
    ['主样本', '2014—2022 年，共 2,349 条记录', '墨西哥 1,428；越南 608；泰国 313。年度表保留 2018—2019 年'],
    ['主比较', '2014—2017 年与 2020—2022 年', '数量分别除以 4 年、3 年；份额为各期合计记录数的比例，并非逐年份额的简单平均'],
    ['2023 年使用', '只在敏感性中使用 1—9 月；比较的每一年都限制在相同 9 个月', '同时取 2014—2017 与 2020—2023 各年 1—9 月；不乘以 4/3，不当作全年'],
    ['暂不进入主 facts', '2023 年第四季度和 2024 年', '第四季度存在覆盖与字段问题；2024 年缺 Project_Type、Parent_Company 等关键字段'],
    ['类型和状态', '保留 New、Expansion、Co-Location 和全部状态', '不把 Opened 筛选或只保留非估计记录误当为质量改进；状态不等于各年持续在营'],
    ['统计单位', '项目记录，主结果保留原始行', '没有 Project_ID，暂不能把每行确认成唯一项目、工厂或企业'],
    ['主要权重', '记录数', '金额和就业包含大量估计；单位尚待供应商确认，不用作实际投资、产出或生产率的替代指标'],
])
p('2023 年 10—11 月来源国的异常截断使其覆盖完整性存疑；12 月又缺失项目类型和母公司等字段。2024 年只有 8 列，虽可机械统计来源和活动，却无法做与前三条 facts 一致的类型与历史匹配分析。待补充后，再扩展时间窗口；不要在当前图表中补零或外推这些缺失信息。2014—2022 年的关键字段足够完成本次计算，但这不等于已经独立证明供应商交付覆盖了数据库全部历史项目。')
p('来源分组沿用 F03 的可比定义：中国仅为 Source_Country = China；Other East Asia 为 Japan、South Korea、Taiwan；美国单列；其余归 Other parents，其中包括 Hong Kong 和 Singapore。当前不把香港合入中国，也不凭空构造 Unallocated ROW。该分组按交付字段计算，正式口径仍需供应商数据字典确认。')

heading('FDI01：墨西哥、越南扩建份额上升，但扩建年均记录数下降')
table(['目的地', '总记录数：基期 / 后期', 'Expansion 份额：基期 → 后期', '份额变化（百分点）', 'Expansion 年均记录数：基期 → 后期'], [
    [CN[c], f"{types[c]['pre_n']} / {types[c]['post_n']}", pair(types[c]['pre_expansion_share_pct'], types[c]['post_expansion_share_pct'], '%'), f"{types[c]['expansion_share_change_pp']:+.2f}", pair(types[c]['pre_expansion_n']/4, types[c]['post_expansion_n']/3)] for c in CN
])
p('**可采用的 fact 表述：在当前制造活动项目记录中，与 2014—2017 年相比，2020—2022 年墨西哥和越南的 Expansion 份额分别增加 13.67 和 12.35 个百分点；该方向在全部预设窗口与记录处理检查中保持。** 泰国的变化对窗口敏感，不应写成三国共同发生的结构变化。')
p('份额上升不能写成“扩建投资增长”。墨西哥 Expansion 年均记录由 69.00 降至 58.67，越南由 16.75 降至 8.00；两国 New 年均记录分别由 113.25 降至 55.33、由 70.50 降至 17.67，下降更快。该 fact 描述的是交付样本内项目类型构成变化，尚不能证明实际生产能力增长或实际 FDI 下降。')
figure('FDI01_type_composition', 'FDI01：2014—2017 与 2020—2022 年制造活动记录的新建、扩建和 Co-Location 构成。')
p('[主结果表](FDI01_type_composition.csv) · [全部时间窗口和记录处理方案](window_type_comparisons.csv) · [年度来源与类型明细](annual_country_type_source.csv)')

heading('FDI02：中国来源份额在墨西哥、越南均上升，但数量含义不同')
table(['目的地', 'China / 全部来源：基期 → 后期', '中国来源份额', '中国来源年均记录数'], [
    [CN[c], f"{china[c]['pre_n']}/{types[c]['pre_n']} → {china[c]['post_n']}/{types[c]['post_n']}", pair(china[c]['pre_share_pct'], china[c]['post_share_pct'], '%'), pair(china[c]['pre_annual_mean'], china[c]['post_annual_mean'])] for c in CN
])
p('**可采用的 fact 表述：中国来源在墨西哥和越南制造活动记录中的份额分别由 4.06% 升至 7.83%、由 5.06% 升至 10.39%，两个国家的份额增加方向在全部预设检查中保持；中国来源记录数量的变化却存在国家差异。** 墨西哥的中国来源年均记录数增加，越南主窗口内减少。')
p('越南的中国来源份额上升，与全部来源记录的分母下降更快有关。加入 2023 年的同月比较后，中国来源每年 1—9 月平均记录数由 4.00 增至 7.00，方向不同于主窗口。因此可写“来源构成转变”，不能把现有结果统一写成“中国对三国投资增加”，也不能把这份额当成中国来源的产出份额或资本份额。泰国中国来源份额方向同样随窗口变化。')
p('全部四个来源组的数量和贡献已保留；贡献分母统一使用基期全部来源的年均记录数：100 ×（后期某来源年均记录数 − 基期同来源年均记录数）/ 基期全部来源年均记录数。各来源贡献精确加总为总记录数变化率；这与“来源份额变化”是不同指标。')
figure('FDI02_china_share_and_count', 'FDI02：同一批中国来源记录的份额与年均数量并列，避免把份额变化误读为数量增长。')
p('[全部来源主结果](FDI02_source_composition.csv) · [来源 × 项目类型贡献](FDI02_source_type_contributions.csv) · [全部来源敏感性](window_source_comparisons.csv)')

heading('FDI03：基期已观察到的母公司组合中，后期仍有新建项目')
p('以来源国、规范化后的 Parent_Company 名称、东道国进行精确匹配。仅统一 Unicode、空白和大小写，不做模糊企业合并。先查该组合是否在 2014—2017 年的 Manufacturing 记录出现，再查看其 2020—2022 年的项目类型。')
table(['目的地', '基期匹配组的后期记录数', '其中 New', 'New 比例', '再要求同一原生 Sector：New / 匹配记录'], [
    [CN[c], matched[c]['post_n'], matched[c]['new_n'], f(matched[c]['new_share_pct'])+'%', f"{same_sector[c]['new_n']} / {same_sector[c]['same_parent_host_sector_post_n']}（{f(same_sector[c]['new_share_pct'])}%）"] for c in CN
])
p('**可采用的 fact 表述：在基期已观察到的母公司—东道国组合中，墨西哥后期 107 条记录中有 28 条 New，越南 25 条中有 13 条 New。进一步要求同一原生行业，New 仍分别占 21/96 和 9/20。已有母公司组合内部的调整可以包含新建项目，不能全部归为扩建。** 泰国主窗口也有正例，但匹配样本仅 11 条，替代窗口可为零，不据此提出稳健的三国共同结论。')
p('这是对 F04 最直接的解释补充：国家—行业联系持续存在，并不意味着其中所有调整都来自旧厂扩张。不过，New 是项目类型，不等于企业首次进入；正向名称匹配证明的是已有项目记录，不证明当时已投产、仍在营或唯一法律实体。即使加上同一原生行业，仍未完成与 AMNE 行业的跨库对应。')
p('基期未匹配组也不能称为“新进入企业”。其后期仍有 Expansion：墨西哥 '+str(unmatched['Mexico']['expansion_n'])+' 条、越南 '+str(unmatched['Vietnam']['expansion_n'])+' 条、泰国 '+str(unmatched['Thailand']['expansion_n'])+' 条。未匹配可能来自 2014 年以前的投资、名称变化、其他活动类别或观察遗漏。本文只利用正向历史匹配的证据，不把未匹配数量解释为进入率。')
figure('FDI03_previously_observed_parents', 'FDI03：基期已出现的母公司—东道国名称组合中，后期 New、Expansion 和 Co-Location 的构成。')
p('[母公司历史匹配主结果](FDI03_parent_history.csv) · [New 正向匹配记录及原表行号](FDI03_positive_match_records.csv) · [同一原生行业的全部敏感性](window_parent_sector_history_comparisons.csv)')

heading('结果对窗口和疑似重复记录是否敏感')
p('计算了四个时间窗口与三种记录处理方式，共 12 个方案：主窗口；等长的 2015—2017 对 2020—2022；剔除后期 2020 年的 2014—2017 对 2021—2022；两期都仅取 1—9 月的 2014—2017 对 2020—2023。三种记录处理是保留全部记录、折叠非联系字段完全相同记录，以及保留项目类型和母公司后按较少字段合并的压力检查。最后一种可能合并真实的异地项目，不是已经清洗出的唯一项目数，也不是统计上下界。')
table(['目的地', 'Expansion 份额变化范围（百分点）', 'China 份额变化范围（百分点）', '解释'], [
    [CN[c], span(c, 'expansion_share_change_pp'), span(c, 'china_share_change_pp'), '两项方向均保持为正' if c != 'Thailand' else '两项方向均可能翻转'] for c in CN
])
p('这些范围是设定变化产生的结果范围，不是置信区间。相同来源—母公司—东道国的 New 正例在墨西哥和越南保持，泰国不保持。全部方案中总年均记录数仍下降，但历史覆盖尚未独立核实，因此不把这一现象直接解释成东道国实际 FDI 收缩。')
adjusted = {(r['country'], r['period']): r for r in result['common_sector_adjustment']}
table(['目的地', '固定共同原生行业权重后的 Expansion 份额：基期 → 后期', '共同支持样本：基期 / 后期'], [
    [CN[c], pair(adjusted[c,'pre']['fixed_sector_weight_expansion_share_pct'], adjusted[c,'post']['fixed_sector_weight_expansion_share_pct'], '%'), f"{adjusted[c,'pre']['covered_records']} / {adjusted[c,'post']['covered_records']}"] for c in CN
])
p('上述补充检查限制在三个国家、两期均有记录的 13 个原生 Sector，并固定使用三国合计的基期行业记录权重。墨西哥和越南扩建份额的上升方向仍在，说明在这一受限样本中，变化不完全由所保留行业之间的权重变化驱动。该计算不是因果控制，也不是 AMNE 六部门结果，不能据此排除全样本的一切行业构成影响。')
p('[共同原生行业权重](common_sector_weights.csv) · [固定权重结果](common_sector_weight_sensitivity.csv) · [独立审核结果](INDEPENDENT_REVIEW.json)')

heading('如何放回当前项目')
table(['用途', '建议', '与现有事实的关系'], [
    ['机制证据', '推荐：将 FDI01—FDI03 作为单独补充包', 'FDI02 补充 F03 的来源构成；FDI01 和 FDI03 约束对 F04 持续联系的解释'],
    ['论文动机', '可使用带样本限定的描述句，优先 FDI03', '说明 aggregate continuing links 内部仍可能有新建项目，避免将国家—行业 intensive margin 直接等同企业或工厂 intensive margin'],
    ['金额加权/资本存量/产出增长', '暂不推荐', '金额单位、估计属性、投产与退出信息不足；项目公告记录不等同实际产出'],
    ['首次企业进入率/在营企业数量', '目前不可识别', '没有完整历史实体与运营状态；New 标签和基期未匹配都不能直接识别首次进入'],
    ['贸易战因果效应/MP 弹性/福利保险', '目前不能据此估计', '没有识别设计、实际经营结果与结构参数映射；不能据 New 占比直接设置 hgamma 或自动加入 endogenous entry'],
])
p('原有 F03/F04 的正式比较窗口是 2014—2017 与 2020—2023，并使用六个映射后的 AMNE 制造业部门；本次主窗口的后期止于 2022 年，活动口径也是全部 fDi Manufacturing。原有六部门实际上为 autos、electrical_equipment、electronics、machinery、textiles_apparel、other_manufacturing，medical_devices 没有单列进入正式六部门。缺少 Sub-sector/NAICS 等细项时，不能声称当前 fDi 已与其严格匹配。因此，不能把“AMNE 产出增长”和“fDi 记录下降”写成同一对象的矛盾或据此计算项目生产率。')
p('建议保留当前三条作为独立的描述性事实版本。补齐数据后，先重跑相同规则，再扩至 2023—2024 全年与可比行业；只有新增信息足以约束关键 MP margin 并改变经济结论时，再讨论模型扩展。本次未改写原有 facts。')

heading('资料、复核与复现')
p('原始文件：`data/raw/fDi_Markets .xlsx`。本次输出：`output/fdi_facts_2026_10_02/`。逐条派生表保留 Excel 行号、原始项目类型和母公司名称，方便追溯；不导出个人联系人字段。')
p('独立审核从原始工作簿另写算法重算，四个窗口 × 三种记录处理 × 三个国家共 36 个单元的 4,860 个主结果数值一致；来源和类型加总、年均分母、零值年份处理均通过。同原生行业匹配与固定行业权重的追加 139 个数值也全部一致。三张图的数值、文字和导出已检查；图形同时提供 PNG、SVG 和 PDF。原 Excel 及受保护的既有 F03/F04 结果 SHA256 未改变。')
p('这里的“通过”指计算与图文一致，并不等于已证明供应商数据完整、项目唯一、真实投产或因果识别成立。')
p('[完整派生记录与审核标识](manufacturing_records_with_audit_flags.csv) · [方法和样本规则](METHOD_AND_VALIDATION.json) · [原始 Excel 审核资料](../audits/fdi_markets_2026_10_02/validation.json) · [图形审核](FIGURE_REVIEW.json)')
p('复现顺序：运行 `code/analysis/fdi_facts/build_fdi_facts.py` 计算；运行 `validate_fdi_facts.py` 独立验证，再用其 `--extensions-only` 参数核对追加行业检查；用已安装 matplotlib 的 Python 运行 `plot_fdi_facts.py` 生成图形；检查图形后运行 `write_fdi_report.py` 打包说明。计算与独立验证使用已配置的 bundled Python；绘图使用 `C:/Python314/python.exe`。任何原始数据或表格发生变化，都需要重新完成数值和图形审核，不应沿用旧审核状态。')

report = '\n\n'.join(md) + '\n'
(OUT / 'FACTS_AND_USAGE.md').write_text(report, encoding='utf-8')
css = '''body{font-family:system-ui,"Microsoft YaHei",sans-serif;line-height:1.8;color:#203139;background:#fafbfc;margin:0}main{max-width:1120px;margin:32px auto;padding:28px 40px;background:white}h1{font-size:28px;line-height:1.4}h2{font-size:22px;margin-top:40px;border-bottom:2px solid #e0e9ed;padding-bottom:8px}p{margin:16px 0}strong{color:#123d52}a{color:#156582;text-underline-offset:3px}code{background:#eef2f4;padding:2px 4px;font-size:.92em;overflow-wrap:anywhere}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;margin:18px 0}td,th{padding:12px 14px;border-bottom:1px solid #dce3e7;text-align:left;vertical-align:top}th{background:#eef4f6;font-weight:650}tr:nth-child(even){background:#fafcfd}figure{margin:24px 0}img{width:100%;height:auto}figcaption{color:#596b75;font-size:13px}footer{margin-top:32px;border-top:1px solid #dde5e9;padding-top:15px;font-size:13px;color:#596b75}@media(max-width:700px){main{margin:0;padding:18px}table{min-width:650px}}@media print{body{background:white}main{margin:0;padding:0;max-width:none}figure,table{break-inside:avoid}a{color:inherit}}'''
(OUT / 'index.html').write_text('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>fDi Markets：现有数据的使用与 facts</title><style>'+css+'</style></head><body><main><h1>fDi Markets：现有数据的使用与 facts</h1>'+''.join(webpage)+'<footer>本地可复核研究说明 · 2026-10-02 · 不依赖外部资源</footer></main></body></html>', encoding='utf-8')

cards = []
for fact_id, title, files, boundaries in [
    ('FDI01', '墨西哥和越南扩建记录份额上升，年均扩建记录数下降', ['FDI01_type_composition.csv','window_type_comparisons.csv'], ['样本构成变化，不等于扩建投资或产出增长', '泰国方向不稳健']),
    ('FDI02', '中国来源份额在墨西哥与越南上升，数量变化不同', ['FDI02_source_composition.csv','FDI02_source_type_contributions.csv','window_source_comparisons.csv'], ['来源份额不是产出或资本份额', '越南数量变化依赖窗口，泰国份额方向不稳健']),
    ('FDI03', '已有母公司名称组合中仍观察到 New 项目', ['FDI03_parent_history.csv','FDI03_positive_match_records.csv','window_parent_sector_history_comparisons.csv'], ['New 不等于首次进入', '正向历史匹配不证明在营或唯一实体', '基期未匹配不等于新企业', '泰国小样本不稳健'])
]:
    cards.append({'id':fact_id,'title_cn':title,'status':'descriptive_computation_verified_coverage_pending','gate':method['gate'],'raw_sha256':method['raw_sha256'],'method':method,'values':result[fact_id],'tables':files,'limitations':boundaries,'figure_metadata':'FIGURE_METADATA.json'})
write_json('FACT_CARDS.json', cards)

bad_links = [x for x in set(links) if not (OUT / x).exists()]
assert not bad_links, bad_links
assert '\ufffd' not in report
assert len(re.findall(r'!\[', report)) == 3
for country in CN:
    assert f(matched[country]['new_share_pct'])+'%' in report
    assert f(same_sector[country]['new_share_pct'])+'%' in report
validation = {
    'status':'PASS',
    'generated_at_utc':datetime.now(timezone.utc).isoformat(),
    'scope':'Current delivered sample; descriptive facts only. Coverage completeness remains unverified.',
    'checks':{'tables_hashes_match':True,'protected_files_unchanged':True,'independent_numeric_review_passed':True,'figure_review_passed':True,'all_report_links_exist':True,'three_figures_in_report':True,'utf8_has_no_replacement_character':True,'parent_history_values_rendered':True},
    'numeric_review_sha256':sha(OUT/'INDEPENDENT_REVIEW.json'),
    'figure_review_sha256':sha(OUT/'FIGURE_REVIEW.json'),
    'report_sha256':sha(OUT/'FACTS_AND_USAGE.md'),
    'html_sha256':sha(OUT/'index.html'),
    'fact_cards_sha256':sha(OUT/'FACT_CARDS.json'),
    'raw_sha256':method['raw_sha256'],
    'files_checked':len(read_json('TABLE_MANIFEST.json'))+len(fig_review['figure_outputs'])+len(method['protected_hashes']),
}
write_json('DELIVERY_VALIDATION.json', validation)
print(json.dumps({'status':validation['status'],'report':str(OUT/'FACTS_AND_USAGE.md'),'html':str(OUT/'index.html'),'report_characters':len(report),'local_links':len(set(links))}, ensure_ascii=True))
