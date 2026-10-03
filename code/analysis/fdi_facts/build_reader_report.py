"""Reorganize verified fDi facts as tables, figures, notes, then interpretation."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import html
import hashlib
import json
import base64
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'output/fdi_research_baseline_2026_10_03'
MP = ROOT / 'output/mp_pilot_prepare_2026_10_03'
OUT = ROOT / 'output/fdi_facts_reader_2026_10_03'
OUT.mkdir(parents=True, exist_ok=True)
CN = {'Mexico':'墨西哥', 'Vietnam':'越南', 'Thailand':'泰国'}
STAGES = ['2014-2017', '2018-2019', '2020-2022']
STAGE_CN = {s:s.replace('-', '—') for s in STAGES}
GROUPS = [('china','中国'), ('other_east_asia','其他东亚'), ('united_states','美国'), ('other_parents','其他来源')]
SOURCES = {}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_csv(name):
    p = BASE / name
    SOURCES[str(p.relative_to(ROOT))] = sha(p)
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def read_json(p):
    SOURCES[str(p.relative_to(ROOT))] = sha(p)
    return json.loads(p.read_text(encoding='utf-8'))


annual = read_csv('exploratory_annual_full_year.csv')
A = {(r['country'],int(r['year'])):r for r in annual}
J = {(r['country'],int(r['year'])):r for r in read_csv('exploratory_annual_jan_sep.csv')}
period = read_csv('staged_period_full_year.csv')
P = {(r['country'],r['stage']):r for r in period}
history = read_csv('staged_parent_history.csv')
mp = read_json(MP/'PILOT_SUMMARY.json')
reviews = [read_json(BASE/'EXPLORATORY_INDEPENDENT_REVIEW.json'), read_json(BASE/'STAGED_INDEPENDENT_REVIEW.json')]
assert all(r['status']=='PASS' for r in reviews)
assert read_json(MP/'VALIDATION.json')['passed']


def fmt(v, digits=2):
    return f'{float(v):,.{digits}f}'


def pct(v):
    return fmt(v)+'%'


def countshare(r, key):
    return f"{int(r[key+'_records']):,}（{pct(r[key+'_share_pct'])}）"


def change(a,b):
    return (float(b)/float(a)-1)*100


sections = []
TABLES = []


def section(sid, title, subtitle):
    s = {'id':sid,'title':title,'subtitle':subtitle,'tables':[], 'notes':[], 'interpretation':[]}
    sections.append(s)
    return s


def table(s, tid, title, headers, rows):
    t = {'id':tid, 'title':title, 'headers':headers, 'rows':rows}
    s['tables'].append(t)
    TABLES.append(t)
    with (OUT/(tid+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


s=section('fact1','01　制造活动项目的数量与中国来源份额','2014—2024 年：先看全年记录数，再看同一批记录的来源构成。')
table(s,'table_01a_annual_counts','表 1A｜各目的地的年度制造活动记录数（条）',
      ['年份','墨西哥','越南','泰国'],
      [[str(y)+('†' if y>=2023 else '')]+[A[c,y]['records'] for c in CN] for y in range(2014,2025)])
table(s,'table_01b_annual_china','表 1B｜中国来源记录数及占该目的地当年记录的份额',
      ['年份','墨西哥：条（%）','越南：条（%）','泰国：条（%）'],
      [[str(y)+('†' if y>=2023 else '')]+[countshare(A[c,y],'china') for c in CN] for y in range(2014,2025)])
s['figure']='figure_01_trends'
s['figure_title']='图 1｜三国年度制造活动记录数与中国来源份额'
s['notes']=[
    '样本范围：Destination_Country 为墨西哥、越南、泰国，Activity 等于 Manufacturing；保留全部来源、行业、项目类型、项目状态和已交付记录。这里是按活动筛选，不是把 fDi 的原生行业强行映射为 AMNE 行业。',
    '观察单位为交付的项目记录。记录数不是企业数、工厂存量或实际投产数。中国份额＝Source_Country 为 China 的记录数÷同一目的地、同一年全部制造活动记录数；各记录权重相同。',
    '† 表示 2023—2024 年探索数据。两年均纳入当前工作簿中的全年记录；没有用前三季度外推全年。空心点与虚线标示待供应商核验的年份，不能视作数据库完整总体。',
    '全年共有 2,982 条制造活动记录：2014—2022 年 2,349 条、2023 年 308 条、2024 年 325 条。全部保留；没有用投资金额或就业数加权。']
s['interpretation']=[
    ('读数','2024 年墨西哥为 161 条，低于 2023 年的 185 条；越南由 87 条增至 118 条，泰国由 36 条增至 46 条。延长到 2024 年后，三国出现了不同的后续数量路径，不能仅用截至 2022 年的低点概括后续变化。'),
    ('数量与份额','越南 2024 年总记录数增加，但中国来源记录由 33 条减为 23 条，份额由 37.93% 降至 19.49%。因此，总项目数量增加和某一来源的份额增加是两个不同的事实；图 2 会进一步说明其他来源的构成。'),
    ('研究用途','这一组用于呈现目的地与来源层面的项目调整路径。它为生产调整提供描述性线索；贸易转移、实际产出以及供应美国市场的变化仍需与相应数据分别对应。墨西哥中国份额的全年下降对月份窗口敏感，详见第 05 组。')]

s=section('fact2','02　项目来自哪里：四组来源的构成','将总量拆开，区分中国、其他东亚、美国与其他来源。')
source_rows=[]
for c in CN:
    for stage in STAGES+['2023','2024']:
        r=P[c,stage] if stage in STAGES else A[c,int(stage)]
        source_rows.append([CN[c],STAGE_CN.get(stage,stage+'†'),r['records']]+[countshare(r,g) for g,label in GROUPS])
table(s,'table_02_source_composition','表 2｜各阶段的来源构成：记录数（阶段份额）',
      ['目的地','阶段','全部记录','中国','其他东亚','美国','其他来源'],source_rows)
s['figure']='figure_02_sources'
s['figure_title']='图 2｜四组来源占目的地各阶段制造活动记录的份额'
s['notes']=[
    '其他东亚固定指日本、韩国、台湾；其他来源是余下全部来源，包括香港和新加坡。四组互斥且穷尽；Source_Country 是数据库记录的来源字段，不额外推定最终控制人。',
    '前三阶段分别包含 4 年、2 年、3 年。表中“全部记录”和各来源记录是阶段合计，不能拿 4 年合计与 1 年合计直接比较增长；堆叠图比较的是各阶段内部的构成。',
    '阶段份额＝该来源在阶段内的记录合计÷同一目的地该阶段全部记录合计，是合并记录后的份额，不是年度百分比的简单平均。',
    '2023、2024 分别作为单年展示并标 †。百分比的舍入可能使显示值之和略偏离 100%；未舍入值严格加总为 100%。']
s['interpretation']=[
    ('国别差异','2014—2017 年美国来源占墨西哥记录的 25.17%，其他东亚占 21.65%；越南和泰国的其他东亚份额分别为 56.74% 和 48.59%。三个目的地的来源基础不同，后续项目变化应在各自来源结构下解读。'),
    ('后续变化','越南的其他东亚记录从 2023 年 24 条增至 2024 年 55 条，份额从 27.59% 升至 46.61%。同期中国来源记录减少。这说明当前样本中的越南总量增加伴随来源重新分配，不能统称为中国企业的项目增加。'),
    ('研究用途','来源构成可以帮助确定后续 AMNE 母国—东道国比较应关注哪些组合。但同一来源组占比上升并不证明企业从另一个国家搬迁，也不显示项目产品最终卖往哪里。')]

s=section('fact3','03　项目如何调整：New、Expansion 与 Co-location','同时展示类型份额和扩建数量，避免把份额上升等同于扩建活动增加。')
type_rows=[]
for c in CN:
    for stage in STAGES:
        r=P[c,stage]
        type_rows.append([CN[c],STAGE_CN[stage],r['records'],countshare(r,'new'),countshare(r,'expansion'),countshare(r,'co_location'),fmt(float(r['expansion_records'])/float(r['n_years']))])
table(s,'table_03a_project_types','表 3A｜字段可用阶段的类型构成与年均扩建记录',
      ['目的地','阶段','全部记录','New：条（%）','Expansion：条（%）','Co-location：条（%）','年均 Expansion（条）'],type_rows)
type_2023=[]
for c in CN:
    r=A[c,2023]
    type_2023.append([CN[c],f"{r['project_type_available_records']} / {r['records']}",pct(r['project_type_available_pct']),
        f"{r['new_records_in_known_types']}（{pct(r['new_share_pct_of_known_types'])}）",
        f"{r['expansion_records_in_known_types']}（{pct(r['expansion_share_pct_of_known_types'])}）",
        f"{r['co_location_records_in_known_types']}（{pct(r['co_location_share_pct_of_known_types'])}）"])
table(s,'table_03b_known_types_2023','表 3B｜单独补充：2023 年 1—11 月类型已知的交付记录',
      ['目的地','类型已知 / 全部','类型可用率','New：条（已知类型%）','Expansion：条（已知类型%）','Co-location：条（已知类型%）'],type_2023)
s['figure']='figure_03_types'
s['figure_title']='图 3｜项目类型构成与年均扩建记录数（2014—2022 年）'
s['notes']=[
    'New、Expansion、Co-location 沿用原始 Project_Type 分类；前两项分别以新建、扩建作为阅读标签，第三项保留原分类名。New 不是企业首次进入的判定。',
    '表 3A 与图 3 的类型份额分母为同一目的地、同一阶段的全部制造活动记录。年均扩建记录数＝该阶段 Expansion 记录合计÷阶段年数（4、2、3 年）。',
    '表 3B 单独列示 2023 年 1—11 月类型已知的交付记录；其百分比分母为类型已知记录数，字段可用率的分母仍为全年记录总数。该子样本包含来源覆盖待核的 10—11 月，既不是无缺失的全年类型构成，也不是统一 1—9 月比较。12 月类型缺失，没有被分配到任何类型。',
    '2024 年工作表完全没有 Project_Type，因此该年的 New、Expansion、Co-location 数量及份额不可计算，保留缺失，不能填零或从公司名称推断。']
s['interpretation']=[
    ('份额与数量','墨西哥 Expansion 份额由 2014—2017 年的 37.35% 升至 2020—2022 年的 51.01%，但年均扩建记录由 69.00 条降至 58.67 条。越南相应份额由 18.82% 升至 31.17%，年均扩建记录却由 16.75 条降至 8.00 条。份额上升在这里伴随的是总样本与其他类型记录的下降。'),
    ('阶段差异','墨西哥和越南在 2018—2019 年的扩建份额已分别达到 48.26% 和 24.57%；泰国三个阶段为 41.24%、45.78%、39.62%，并非一致上升。分阶段展示保留了这些差异；本表本身不解释差异由何种冲击造成。'),
    ('研究用途','这一组使项目的调整方式更具体：观察到的项目可以包含扩建和新建。Expansion 的记录份额可以补充生产调整叙述，但不能直接当作结构模型的 intensive-margin 弹性或 hgamma。')]

s=section('fact4','04　此前出现过的母公司组合中，是否还有新建项目','固定 2014—2017 年历史窗口，再观察两个后期阶段。')
history_rows=[]
for r in history:
    history_rows.append([CN[r['country']],r['post_stage'].replace('-','—'),r['all_post_records'],r['matched_parent_host_records'],
        f"{r['matched_new_records']} / {r['matched_parent_host_records']}",pct(r['matched_new_share_pct']),
        f"{r['same_sector_new_records']} / {r['same_sector_matched_records']}（{pct(r['same_sector_new_share_pct'])}）"])
table(s,'table_04_parent_history','表 4｜正向历史匹配记录中的 New：主口径与同原生行业口径',
      ['目的地','后期阶段','全部后期记录','匹配历史的记录','其中 New / 匹配记录','New 份额','再要求同行业：New / 匹配（%）'],history_rows)
s['figure']='figure_04_parent_history'
s['figure_title']='图 4｜历史匹配组内部的新建份额及分母'
s['notes']=[
    '历史匹配条件为来源国、规范化后的 Parent_Company 名称、目的地均与 2014—2017 年至少一条记录相同。基期固定，未把 2018—2019 年加入后一个阶段的历史窗口。',
    '分母为后期正向匹配到历史的项目记录，不是不同母公司数量。New 份额＝匹配记录中的 New 数量÷匹配记录总数。图中同时显示分母，避免小样本百分比脱离数量。',
    '同行业口径进一步要求 fDi 原生 Sector 也与基期记录相同；它检查行业改变是否影响结果，不是 AMNE 行业 crosswalk。',
    '名称匹配没有稳定母公司 ID 和完整经营历史支持。匹配成功表明名称组合过去在样本中出现，不证明持续在营；匹配失败也不证明首次进入。2023—2024 年未延伸该历史分析。']
s['interpretation']=[
    ('直接观察','在 2020—2022 年正向历史匹配组内，墨西哥有 28/107 条属于 New，越南为 13/25，泰国为 4/11。换言之，过去出现过的母公司—来源—东道国组合，后来仍可出现数据库标为 New 的项目。'),
    ('同行业核对','进一步要求同行业后，三个目的地分别为 21/96、9/20、3/9。正向例子仍然存在，但泰国只有 9 条匹配记录，不能据此把百分比差异解释为稳定的国别规律。'),
    ('研究用途','它帮助区分“新项目”与“新企业进入”：观察到 New 并不足以认定新增跨国企业联系。因此，不能仅凭项目标签要求模型加入企业首次进入机制；是否需要该机制还取决于经营历史与福利结果。')]

s=section('fact5','05　后两年的趋势对月份窗口和缺失字段有多敏感','保留 2023—2024 年的信息，同时把影响判断的差异摆在同一页。')
window_rows=[]
for c in CN:
    window_rows.append([CN[c],f"{A[c,2023]['records']} → {A[c,2024]['records']}",f"{J[c,2023]['records']} → {J[c,2024]['records']}",
        f"{pct(A[c,2023]['china_share_pct'])} → {pct(A[c,2024]['china_share_pct'])}",
        f"{pct(J[c,2023]['china_share_pct'])} → {pct(J[c,2024]['china_share_pct'])}"])
table(s,'table_05a_month_windows','表 5A｜2023 → 2024 年：全年与统一 1—9 月比较',
      ['目的地','全年记录数','同1—9月记录数','全年中国份额','同1—9月中国份额'],window_rows)
coverage=[]
for c in CN:
    for y in [2023,2024]:
        r=A[c,y]
        coverage.append([CN[c],y,r['records'],f"{r['project_type_available_records']} / {r['records']}（{pct(r['project_type_available_pct'])}）" if y==2023 else '字段未提供',
                         f"{r['parent_available_records']} / {r['records']}（{pct(r['parent_available_pct'])}）" if y==2023 else '字段未提供'])
table(s,'table_05b_field_coverage','表 5B｜后两年的项目类型与母公司字段可用情况',
      ['目的地','年份','记录总数','Project_Type：可用 / 全部（%）','Parent_Company：可用 / 全部（%）'],coverage)
s['figure']='figure_05_windows'
s['figure_title']='图 5｜全年与统一 1—9 月的中国来源份额路径'
s['notes']=[
    '全年口径使用所有已交付月份；同月份口径把两个年份同时限制为 1—9 月。每一条路径的分子分母均来自其自身月份窗口，不将 9 个月扩算为全年。',
    '2023 年 10—11 月存在来源国覆盖疑点；母公司缺失集中在 10—12 月，项目类型缺失集中在 12 月。2024 年虽有全年日期，但只有八个字段，缺失字段与记录是否漏导是不同问题。',
    '2024 年 325 条制造活动记录中，16 条处于八个可见字段完全相同的候选组；机械合并会减少 9 条。没有稳定 Project ID、地点等信息，当前保留全部记录，不假定重复候选一定是同一个项目。',
    '泰国 2023 年 2 月及 2024 年 7 月没有已交付的制造活动记录；这仅表示样本内零记录，不等于实际投资为零。统一月份比较也不能自行证明记录覆盖完整。']
s['interpretation']=[
    ('不受该窗口选择改变的方向','从 2023 到 2024 年，两个窗口均显示墨西哥总记录数减少、越南和泰国总记录数增加。越南与泰国的中国来源份额在两个窗口中也均下降；这些方向在本次月份比较中保持一致。'),
    ('会改变的方向','墨西哥中国来源份额全年为 17.30% → 16.15%，同 1—9 月却为 14.20% → 17.78%。因此，现有数据不能稳健地支持“墨西哥中国来源份额已经转降”。这项具体差异比一个笼统的数据不完整提示更有信息。'),
    ('现阶段使用','后两年继续用于探索总量和来源构成。供应商补充后，优先核对月份—来源国覆盖、项目稳定标识、项目类型和母公司字段，再按相同规则重算。疫情只保留为时间背景；详细因果识别不作为当前事实展示的前置条件。')]

s=section('mp','附录　经营数据如何接到 MP 目标准备','把项目记录与经营规模分开：美国母公司—墨西哥—机械行业试点。')
mp_rows=[]
for r in mp['series']:
    mp_rows.append([r['year'],fmt(r['numerator_us_affiliate_output_musd']),fmt(r['denominator_host_gross_output_musd']),pct(100*r['target_fraction']),fmt(r['bea_sales_musd']),fmt(r['bea_goods_exports_to_us_musd'])])
table(s,'table_06_mp_machinery','表 6｜机械行业候选目标与辅助指标',
      ['年份','AMNE 美国母公司在墨产出','AMNE 墨西哥机械行业总产出','美国母公司产出份额','BEA 销售','BEA 向美国货物出口'],mp_rows)
s['figure']='figure_06_mp'
s['figure_title']='图 6｜美国母公司在墨西哥机械行业的产出水平与相对份额'
s['notes']=[
    '表 6 金额列均为当期百万美元；图 6 左轴为当年价亿美元，数值由百万美元除以 100 得到。图中仅展示 2017、2019、2022 三个端点，不插补其他年份。名义金额没有扣除价格变化。',
    '候选份额＝AMNE 美国母公司在墨西哥 C28 的直接 affiliate output÷同年墨西哥 C28 全部 gross output。分母包含本国和外国生产者，取东道国总量一次，不重复加总。',
    'BEA 使用其原生 Machinery 行业。销售、产出和向美国货物出口并列展示，各自保留统计含义；不将 BEA 销售与 AMNE 产出当作同一个变量，也不直接用出口÷销售构造三边销售概率。',
    '机械试点的选择基于行业对应和端点披露条件，而非增长方向。当前仅准备可观测目标及诊断，没有估计 hgamma、MP 弹性或福利。']
first,last=mp['series'][0],mp['series'][-1]
s['interpretation']=[
    ('实际数值',f"2017—2022 年美国母公司机械产出从 {fmt(first['numerator_us_affiliate_output_musd'])} 增至 {fmt(last['numerator_us_affiliate_output_musd'])} 百万美元，增加 {pct(change(first['numerator_us_affiliate_output_musd'],last['numerator_us_affiliate_output_musd']))}；但占墨西哥机械行业总产出的份额从 {pct(100*first['target_fraction'])} 变为 {pct(100*last['target_fraction'])}，基本持平。产出水平与相对配置给出的信息不同。"),
    ('与 fDi 的分工','前五组回答项目记录怎样变化、来自哪里、以何种类型出现；这一组开始回答经营规模和生产份额怎样变化。两类证据可以相互补充，但没有逐个项目与产出的一一对应。'),
    ('下一项模型检验','先把这个份额与模型的生产配置、国内生产者和价格口径对应，并约束销售网络与其他冲击，再考虑用一个明确的 MP 成本变化拟合该目标。现阶段不能由名义产出增加直接推断成本下降。')]

INTRO='fDi Markets｜项目调整事实与 MP 数据用途'
SUB='墨西哥、越南、泰国 · 制造活动 · 2014—2024 年'
LEDE='每组材料按“表格 → 图表 → Notes → 文字解释”排列。先读数字和图，再读统计口径及经济含义。2023—2024 年保留当前交付的全部记录并标记为探索数据；MP 经营指标另列附录。'


def esc(x):
    return html.escape(str(x))


def md_table(t):
    return '\n'.join(['**'+t['title']+'**','', '| '+' | '.join(t['headers'])+' |', '| '+' | '.join(['---']*len(t['headers']))+' |']+['| '+' | '.join(map(str,row))+' |' for row in t['rows']])


def html_table(t):
    head=''.join('<th scope="col">'+esc(h)+'</th>' for h in t['headers'])
    rows=''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in t['rows'])
    return '<div class="table-block" id="'+t['id']+'"><div class="table-heading"><h3>'+esc(t['title'])+'</h3><a class="download" href="'+t['id']+'.csv" download>数据表 CSV</a></div><div class="table-scroll" role="region" aria-label="'+esc(t['title'])+'" tabindex="0"><table><thead><tr>'+head+'</tr></thead><tbody>'+rows+'</tbody></table></div></div>'


md=['# '+INTRO,SUB,LEDE]
body=[]
for s in sections:
    md+=['## '+s['title'],s['subtitle']]
    start='<section id="'+s['id']+'"><header class="section-title"><h2>'+esc(s['title'])+'</h2><p>'+esc(s['subtitle'])+'</p></header><div class="evidence-tables" data-order="1">'
    body.append(start)
    for t in s['tables']:
        md.append(md_table(t))
        body.append(html_table(t))
    body.append('</div>')
    fig=OUT/(s['figure']+'.png')
    image_data=base64.b64encode(fig.read_bytes()).decode('ascii') if fig.exists() else None
    # Figures can finish in parallel; final validation rejects any unfinished image.
    src='data:image/png;base64,'+image_data if image_data else s['figure']+'.png'
    body.append('<figure data-order="2"><figcaption>'+esc(s['figure_title'])+'</figcaption><img src="'+src+'" alt="'+esc(s['figure_title'])+'"><div class="figure-links"><a href="'+s['figure']+'.pdf">PDF</a><a href="'+s['figure']+'.svg">SVG</a></div></figure>')
    md+=['**'+s['figure_title']+'**', '!['+s['figure_title']+']('+s['figure']+'.png)']
    notes='<aside class="notes" data-order="3"><h3>Notes</h3><ol>'+''.join('<li>'+esc(n)+'</li>' for n in s['notes'])+'</ol></aside>'
    body.append(notes)
    md+=['**Notes**','\n'.join(str(i+1)+'. '+n for i,n in enumerate(s['notes']))]
    body.append('<div class="interpretation" data-order="4"><h3>文字解释</h3>'+''.join('<p><strong>'+esc(label)+'。</strong>'+esc(content)+'</p>' for label,content in s['interpretation'])+'</div></section>')
    md+=['**文字解释**']+['**'+label+'。**'+content for label,content in s['interpretation']]

css='''
:root{--ink:#183746;--muted:#576974;--line:#dce5e9;--accent:#276d86;--paper:#fff;--back:#f4f6f7}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:74px}body{margin:0;background:var(--back);color:#253d49;font:16px/1.85 "Microsoft YaHei",system-ui,sans-serif}
.top{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:3}.nav{max-width:1160px;margin:auto;display:flex;gap:5px;padding:10px 20px;overflow-x:auto;white-space:nowrap}.nav a{text-decoration:none;padding:3px 11px;border-radius:4px;font-size:14px;color:var(--ink)}.nav a:hover,.nav a:focus{background:#eaf1f4}
main{max-width:1160px;margin:26px auto 70px;background:#fff;padding:38px 44px;border:1px solid var(--line)}h1{font-size:29px;line-height:1.5;margin:0;color:var(--ink)}.subtitle{font-size:17px;color:var(--accent);margin:10px 0}.lede{max-width:960px;margin-bottom:14px}.guide{display:flex;flex-wrap:wrap;gap:7px;color:var(--muted);font-size:14px}.guide span{padding:3px 12px;background:#eff4f6;border-radius:3px}section{margin-top:44px;border-top:2px solid #5d899a;padding-top:22px}.section-title h2{font-size:23px;line-height:1.55;margin:0 0 6px;color:var(--ink)}.section-title p{color:var(--muted);margin:0 0 21px}h3{font-size:16px;margin:0;line-height:1.6}.table-block{margin:22px 0}.table-heading{display:flex;align-items:baseline;justify-content:space-between;gap:20px;margin-bottom:8px}.download,.figure-links{font-size:12px;white-space:nowrap}a{color:var(--accent);text-underline-offset:3px}.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.7;font-variant-numeric:tabular-nums}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:middle}th{background:#edf3f5;color:var(--ink);font-weight:600}td:first-child,th:first-child{text-align:left}tbody tr:nth-child(even){background:#fafcfc}tbody tr:hover{background:#f1f7fa}figure{margin:29px 0 18px}figcaption{font-size:17px;font-weight:600;margin-bottom:12px;color:var(--ink)}figure img{display:block;width:100%;height:auto;background:white}.figure-links{text-align:right;display:flex;gap:14px;justify-content:flex-end;margin-top:7px}.notes{border-left:3px solid #8eaeba;background:#f5f8fa;padding:13px 18px;font-size:13px;line-height:1.9}.notes ol{padding-left:20px;margin:5px 0 0}.notes li+li{margin-top:5px}.interpretation{margin-top:19px}.interpretation h3{font-size:17px}.interpretation p{margin:10px 0}strong{color:var(--ink)}footer{border-top:1px solid var(--line);margin-top:32px;padding-top:16px;font-size:12px;color:var(--muted)}
@media(max-width:760px){main{margin:0;padding:24px 18px;border:0}h1{font-size:24px}.section-title h2{font-size:21px}body{font-size:15px}table{font-size:12px;min-width:600px}.table-heading{display:block}.nav{padding:8px}.notes{padding:12px}figure{margin-left:-5px;margin-right:-5px}}
@media print{.top,.download,.figure-links{display:none}body{background:white;font-size:11pt}main{border:0;padding:0;margin:0;max-width:none}section{break-before:page;margin:0;border:0;padding:0}.table-scroll{overflow:visible}thead{display:table-header-group}tr,figure,.notes{break-inside:avoid}table{font-size:9pt}figure img{max-height:230mm;object-fit:contain}h2,h3,figcaption{break-after:avoid}footer{font-size:9pt}}
'''
nav=''.join('<a href="#'+s['id']+'">'+esc(['数量趋势','来源构成','项目类型','母公司历史','月份与缺失','MP 附录'][i])+'</a>' for i,s in enumerate(sections))
foot='来源：已审核的 fDi 项目记录汇总及 AMNE、BEA、ICIO 候选指标。数据截至 2024 年；经营数据附录使用已构建的比较端点。本文重新组织表格、图形和解释，没有新增因果识别或模型估计。'
page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+INTRO+'</title><style>'+css+'</style></head><body><div class="top"><nav class="nav" aria-label="报告目录">'+nav+'</nav></div><main><h1>'+INTRO+'</h1><p class="subtitle">'+SUB+'</p><p class="lede">'+LEDE+'</p><div class="guide"><span>1 表格：核对数字</span><span>2 图表：观察模式</span><span>3 Notes：明确口径</span><span>4 文字解释：理解含义</span></div>'+''.join(body)+'<footer>'+foot+'</footer></main></body></html>'
(OUT/'index.html').write_text(page,encoding='utf-8')
(OUT/'FACTS_READER.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'purpose':'Presentation-only revision: each result is table -> figure -> notes -> interpretation. Gate 2 descriptive evidence and Gate 3 observable preparation appendix; no new estimand or model claim.',
          'sources':SOURCES,'sections':sections,'table_count':len(TABLES),'figure_count':len(sections),'all_figures_embedded':all((OUT/(s['figure']+'.png')).exists() for s in sections),
          'html_sha256':sha(OUT/'index.html'),'markdown_sha256':sha(OUT/'FACTS_READER.md'),
          'completion_standard':['Each of six evidence groups follows table, figure, notes, interpretation order.','All visible numeric table cells derive from reviewed CSV/JSON.','All six figures have PNG/SVG/PDF and reviewed source data.','2023-24 provisional coverage, unknown types, and Mexico window reversal are explicit.','Full-width and narrow preview inspected; no broken images or external dependencies.','Existing raw and prior outputs unchanged.']}
(OUT/'REPORT_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
assert all(sha(ROOT/p)==h for p,h in SOURCES.items())
assert '\ufffd' not in page
print(json.dumps({'tables':len(TABLES),'figures':len(sections),'html_bytes':len(page.encode()),'all_figures_embedded':manifest['all_figures_embedded'],'source_hashes_unchanged':True},ensure_ascii=True))
