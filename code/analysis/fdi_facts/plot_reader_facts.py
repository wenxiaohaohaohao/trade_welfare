"""Reader-facing figures from the already reviewed fDi/MP summary tables.

No raw-data re-estimation. Exports are separate from all earlier results.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import platform

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'output/fdi_research_baseline_2026_10_03'
MP=ROOT/'output/mp_pilot_prepare_2026_10_03'
OUT=ROOT/'output/fdi_facts_reader_2026_10_03'
TMP=ROOT/'tmp/fdi_reader_2026_10_03'
OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
os.environ['MPLCONFIGDIR']=str(TMP/'matplotlib')
os.environ['TMP']=str(TMP);os.environ['TEMP']=str(TMP)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

FONT='Microsoft YaHei'
FONT_PATH=font_manager.findfont(FONT,fallback_to_default=False)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':[FONT,'SimHei'],'font.size':9,'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.right':False,'axes.spines.top':False,'axes.linewidth':.7,'legend.frameon':False,'legend.fontsize':8.5,'axes.unicode_minus':False,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white','figure.facecolor':'white'})

COUNTRIES=['Mexico','Vietnam','Thailand']
CN={'Mexico':'墨西哥','Vietnam':'越南','Thailand':'泰国'}
STAGES=['2014-2017','2018-2019','2020-2022']
SHORT={'2014-2017':'2014–17','2018-2019':'2018–19','2020-2022':'2020–22'}
SOURCE_KEYS=['china','other_east_asia','united_states','other_parents']
SOURCE_LABELS=['中国','其他东亚（日、韩、台）','美国','其他来源']
SOURCE_COLORS=['#3C6D8D','#72A898','#B59969','#D7DEE3']
TYPE_KEYS=['new','expansion','co_location']
TYPE_LABELS=['New（新建）','Expansion（扩建）','Co-location']
TYPE_COLORS=['#426885','#58A293','#D5B36A']
BLUE='#346987';TEAL='#58A293';GREY='#78858F'
CONTRACTS=[];REVIEWS=[];SOURCE_HASHES={}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rd(p):
    SOURCE_HASHES[str(p.relative_to(ROOT))]=sha(p)
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def val(r,k):return float(r[k])
def nv(r,k):return int(float(r[k]))
def dat(name,rows):
    p=OUT/f'{name}_plot_data.csv'
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    return p
def title(fig,text):fig.text(.025,.963,text,fontsize=11,weight='bold',va='top')
def layout(nrows,ncols,height,title_text,**kwargs):
    fig,axes=plt.subplots(nrows,ncols,figsize=(183/25.4,height/25.4),squeeze=False,**kwargs)
    title(fig,title_text)
    return fig,axes
def tidy(ax,grid='y'):
    ax.grid(axis=grid,color='#E2E6E9',lw=.55);ax.set_axisbelow(True);ax.tick_params(length=3,pad=3)
def save(fig,name,data,sources,conclusion,evidence,notes):
    path=dat(name,data)
    fig.canvas.draw();ren=fig.canvas.get_renderer();outside=[]
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_visible() and t.get_text():
            b=t.get_window_extent(ren)
            if b.x0<-.5 or b.y0<-.5 or b.x1>fig.bbox.x1+.5 or b.y1>fig.bbox.y1+.5:outside.append(t.get_text())
    assert not outside,(name,outside)
    exports=[]
    for ext in ['png','svg','pdf']:
        p=OUT/f'{name}.{ext}';fig.savefig(p,dpi=300);exports.append({'file':p.name,'sha256':sha(p)})
    svg=(OUT/f'{name}.svg').read_text(encoding='utf-8')
    assert '<text' in svg and '<image' not in svg
    CONTRACTS.append({'figure':name,'core_conclusion':conclusion,'evidence_chain':evidence,'archetype':'quantitative grid','backend':'Python / matplotlib','dimensions_mm':[183,round(fig.get_size_inches()[1]*25.4,2)],'sources':sources,'plot_data':{'file':path.name,'sha256':sha(path),'rows':len(data)},'notes_for_report':notes,'statistics':'Descriptive accounting only; no tests, confidence intervals, causal attribution or welfare calculation','exports':exports})
    REVIEWS.append({'figure':name,'all_visible_text_inside_canvas':True,'svg_text_editable':True,'svg_no_raster_objects':True,'font_family':FONT,'font_file':FONT_PATH,'outputs':exports,'manual_visual_review':'pending'})
    plt.close(fig)

annual=rd(BASE/'exploratory_annual_full_year.csv')
jansep=rd(BASE/'exploratory_annual_jan_sep.csv')
period=rd(BASE/'staged_period_full_year.csv')
parents=rd(BASE/'staged_parent_history.csv')
mp_summary_path=MP/'PILOT_SUMMARY.json'
SOURCE_HASHES[str(mp_summary_path.relative_to(ROOT))]=sha(mp_summary_path)
mp=json.loads(mp_summary_path.read_text(encoding='utf-8'))

# Fig. 1: preserve the temporal evidence while removing in-image report notes.
fig,axes=layout(2,3,117,'图1  项目记录数与中国来源份额：2014—2024年',sharex=True,sharey='row')
fig.subplots_adjust(left=.105,right=.98,bottom=.16,top=.84,hspace=.23,wspace=.18)
for c,country in enumerate(COUNTRIES):
    allc=sorted([r for r in annual if r['country']==country],key=lambda r:int(r['year']))
    for rr,(key,label,ylim,ticks) in enumerate([('records','项目记录数',(0,230),[0,50,100,150,200]),('china_share_pct','中国来源份额（%）',(0,60),[0,20,40,60])]):
        ax=axes[rr,c];old=[r for r in allc if int(r['year'])<=2022];new=[r for r in allc if int(r['year'])>=2022]
        ax.axvspan(2022.5,2024.5,color='#F2F2F2',zorder=0)
        ax.plot([int(r['year']) for r in old],[val(r,key) for r in old],color=BLUE,marker='o',ms=3.2,lw=1.2)
        ax.plot([int(r['year']) for r in new],[val(r,key) for r in new],color=BLUE,ls='--',lw=1.2)
        ax.plot([int(r['year']) for r in new if int(r['year'])>2022],[val(r,key) for r in new if int(r['year'])>2022],color=BLUE,marker='o',mfc='white',mew=1.2,ms=4.4,lw=0)
        ax.set_xlim(2013.7,2024.45);ax.set_ylim(ylim);ax.set_yticks(ticks);ax.set_xticks([2014,2016,2018,2020,2022,2024]);tidy(ax)
        if c==0:ax.set_ylabel(label,labelpad=9)
        if rr==0:ax.set_title(CN[country],weight='bold',pad=10)
        if rr==1:ax.set_xlabel('年份')
fig.legend([Line2D([],[],color=BLUE,marker='o',ms=3.5),Line2D([],[],color=BLUE,marker='o',mfc='white',ls='--',ms=4.5)],['2014—2022年记录','2023—2024年记录（待补核）'],loc='lower center',bbox_to_anchor=(.52,.027),ncol=2)
save(fig,'figure_01_trends',annual,['exploratory_annual_full_year.csv'],'三国项目记录数与中国来源份额的年度轨迹不同；2023—2024年暂定数据单独标记。','三列为国家，两行为项目数和中国份额，数据范围完整延伸到2024年。',['全部为Manufacturing活动记录，保留所有来源和项目状态。','中国份额分母为当年该国全部交付Manufacturing记录。','2023—2024年空心点/虚线为待补核记录，不能视为已确认总体变化；潜在重复不删除。'])

# Fig. 2: five periods, all four source groups, same denominator in each bar.
source_data=[]
for c in COUNTRIES:
    for stage in STAGES+['2023','2024']:
        r=next(r for r in (period if stage in STAGES else annual) if r['country']==c and r.get('stage',r.get('year'))==stage)
        source_data.append({'country':c,'stage':stage,'records':nv(r,'records'),'provisional':stage in ['2023','2024'],**{k+'_records':nv(r,k+'_records') for k in SOURCE_KEYS},**{k+'_share_pct':val(r,k+'_share_pct') for k in SOURCE_KEYS}})
fig,axes=layout(1,3,110,'图2  不同阶段的投资来源构成',sharey=True)
fig.subplots_adjust(left=.155,right=.979,bottom=.25,top=.82,wspace=.18)
for c,country in enumerate(COUNTRIES):
    ax=axes[0,c];sub=[r for r in source_data if r['country']==country]
    for y,r in enumerate(reversed(sub)):
        left=0
        for k,color in zip(SOURCE_KEYS,SOURCE_COLORS):
            v=r[k+'_share_pct'];ax.barh(y,v,left=left,height=.57,color=color,edgecolor='white',lw=.6)
            if v>=13:ax.text(left+v/2,y,f'{v:.0f}%',ha='center',va='center',fontsize=7.5,color='white' if k=='china' else '#26333D')
            left+=v
        assert math.isclose(left,100,abs_tol=1e-8)
        ax.text(102,y,str(r['records']),va='center',fontsize=7.7)
    ax.set_yticks(range(5),['2024（待补）','2023（待补）','2020—22','2018—19','2014—17'])
    ax.set_xlim(0,119);ax.set_ylim(-.6,4.7);ax.set_xticks([0,50,100]);ax.set_xlabel('来源份额（%）');ax.set_title(CN[country],weight='bold',pad=9)
    ax.text(102,4.65,'n',fontsize=8,va='center');ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0,pad=5)
fig.legend([Patch(facecolor=c) for c in SOURCE_COLORS],SOURCE_LABELS,loc='lower center',bbox_to_anchor=(.56,.054),ncol=2,columnspacing=1.6)
save(fig,'figure_02_sources',source_data,['staged_period_full_year.csv','exploratory_annual_full_year.csv'],'来源构成显示中国、其他东亚、美国和其他来源的不同变化路径。','三国五阶段100%堆叠条形，右侧n为全部来源记录总数。',['前三期按阶段记录数合并计算，不是年度份额简单平均。','Other East Asia仅包括Japan、South Korea、Taiwan，Hong Kong和Singapore在其他来源。','2023与2024为待补核全年交付记录，后期来源份额受覆盖和重复风险影响。'])

# Fig. 3: composition versus number of Expansion records per calendar year.
type_data=[]
for r in period:
    d={k:r[k] for k in ['country','stage','records','n_years']}
    d.update({k+'_records':nv(r,k+'_records') for k in TYPE_KEYS});d.update({k+'_share_pct':val(r,k+'_share_pct') for k in TYPE_KEYS})
    d['expansion_annual_mean']=nv(r,'expansion_records')/nv(r,'n_years');type_data.append(d)
fig,axes=layout(2,3,133,'图3  扩建份额与扩建记录年均数量',sharey='row')
fig.subplots_adjust(left=.15,right=.979,bottom=.17,top=.845,hspace=.48,wspace=.18)
for c,country in enumerate(COUNTRIES):
    sub=[next(r for r in type_data if r['country']==country and r['stage']==st) for st in STAGES]
    ax=axes[0,c]
    for y,r in enumerate(reversed(sub)):
        left=0
        for k,color in zip(TYPE_KEYS,TYPE_COLORS):
            v=r[k+'_share_pct'];ax.barh(y,v,left=left,height=.52,color=color,edgecolor='white',lw=.6)
            if v>=10:ax.text(left+v/2,y,f'{v:.1f}%',ha='center',va='center',color='white',fontsize=7.7)
            left+=v
    ax.set_yticks([0,1,2],[SHORT[s] for s in reversed(STAGES)]);ax.set_xlim(0,100);ax.set_xticks([0,50,100]);ax.set_xlabel('项目类型份额（%）');ax.set_title(CN[country],weight='bold',pad=9);ax.spines['left'].set_visible(False);ax.tick_params(axis='y',length=0)
    if c>0:ax.tick_params(labelleft=False)
    ax=axes[1,c];v=[r['expansion_annual_mean'] for r in sub]
    ax.bar(range(3),v,width=.56,color=TYPE_COLORS[1]);ax.set_xticks(range(3),[SHORT[s] for s in STAGES]);ax.set_ylim(0,99);ax.set_yticks([0,25,50,75]);tidy(ax)
    for i,n in enumerate(v):ax.text(i,n+2,f'{n:.2f}',ha='center',va='bottom',fontsize=8.2)
    if c==0:ax.set_ylabel('扩建记录年均数')
fig.legend([Patch(facecolor=c) for c in TYPE_COLORS],TYPE_LABELS,loc='lower center',bbox_to_anchor=(.54,.025),ncol=3,columnspacing=1.1,fontsize=8)
save(fig,'figure_03_types',type_data,['staged_period_full_year.csv'],'扩建份额上升不等于扩建记录数量持续增加。','上排显示新建/扩建/增设活动份额，下排将同一扩建记录数除以阶段年数，分开显示结构与数量。',['只比较2014—17、2018—19、2020—22三个完整年度阶段。','2023类型已知子样本与全年口径不同，未混入此图；2024类型缺失，不能画成零。','New不是首次企业进入，Expansion也不是实际产出增长。'])

# Fig. 4: New among positive name-history matches, and a stricter sector match.
parent_data=[]
for r in parents:
    for mode in ['parent_host','same_sector']:
        num=nv(r,'matched_new_records' if mode=='parent_host' else 'same_sector_new_records')
        den=nv(r,'matched_parent_host_records' if mode=='parent_host' else 'same_sector_matched_records')
        parent_data.append({'country':r['country'],'baseline_stage':r['baseline_stage'],'post_stage':r['post_stage'],'match':mode,'new_records':num,'matched_records':den,'new_share_pct':100*num/den})
fig,axes=layout(2,3,136,'图4  有既往项目记录的母公司组中，仍存在新建项目',sharey=True)
fig.subplots_adjust(left=.15,right=.982,bottom=.115,top=.845,hspace=.44,wspace=.18)
for c,country in enumerate(COUNTRIES):
    for rr,mode in enumerate(['parent_host','same_sector']):
        ax=axes[rr,c];sub=[next(r for r in parent_data if r['country']==country and r['match']==mode and r['post_stage']==st) for st in ['2018-2019','2020-2022']]
        ax.bar([0,1],[r['new_share_pct'] for r in sub],width=.55,color=BLUE if rr==0 else TEAL)
        for i,r in enumerate(sub):ax.text(i,r['new_share_pct']+2,f"{r['new_share_pct']:.1f}%\n{r['new_records']}/{r['matched_records']}",ha='center',va='bottom',fontsize=8,linespacing=1.35)
        ax.set_ylim(0,73);ax.set_yticks([0,20,40,60]);ax.set_xticks([0,1],['2018—19','2020—22']);ax.set_xlim(-.6,1.6);tidy(ax)
        if rr==0:ax.set_title(CN[country],weight='bold',pad=10)
        if c==0:ax.set_ylabel(('同母公司—目的国' if rr==0 else '再要求同一原生行业')+'\nNew份额（%）',labelpad=8)
save(fig,'figure_04_parent_history',parent_data,['staged_parent_history.csv'],'既往项目历史与后期新建项目可以共存，不能把既有联系直接等同于原有工厂扩张。','两行分别使用母国+规范母公司名称+目的国、再加同一原生行业匹配。柱上显示New数/匹配组总数。',['固定基期2014—2017年，分别查看两个后期。','母公司名称作NFKC、空格、大小写标准化，不模糊匹配。','正向历史匹配不证明实际在营；未匹配不等于新进入；泰国分母尤其小。'])

# Fig. 5: changing the common month window changes the Mexico direction.
window_data=[]
for c in COUNTRIES:
    for label,data in [('full_year',annual),('jan_sep',jansep)]:
        for yr in ['2023','2024']:
            r=next(r for r in data if r['country']==c and r['year']==yr)
            window_data.append({'country':c,'window':label,'year':int(yr),'china_records':nv(r,'china_records'),'all_records':nv(r,'records'),'china_share_pct':val(r,'china_share_pct')})
fig,axes=layout(1,3,95,'图5  中国来源份额：全年与同1—9月的比较',sharey=True)
fig.subplots_adjust(left=.095,right=.98,bottom=.25,top=.80,wspace=.23)
for c,country in enumerate(COUNTRIES):
    ax=axes[0,c]
    for label,color,marker,offset in [('full_year',GREY,'o',7),('jan_sep',BLUE,'s',-13)]:
        sub=sorted([r for r in window_data if r['country']==country and r['window']==label],key=lambda r:r['year'])
        ax.plot([r['year'] for r in sub],[r['china_share_pct'] for r in sub],color=color,marker=marker,mfc='white',ms=5,ls='--',lw=1.2)
        for r in sub:
            other=next(z for z in window_data if z['country']==country and z['year']==r['year'] and z['window']!=label)
            dy=8 if r['china_share_pct']>other['china_share_pct'] else -14
            ax.annotate(f"{r['china_share_pct']:.2f}%",(r['year'],r['china_share_pct']),xytext=(0,dy),textcoords='offset points',ha='center',fontsize=8,color=color)
    ax.set_xlim(2022.7,2024.3);ax.set_ylim(0,60);ax.set_yticks([0,20,40,60]);ax.set_xticks([2023,2024]);ax.set_title(CN[country],weight='bold',pad=10);tidy(ax)
    if c==0:ax.set_ylabel('中国来源份额（%）')
fig.legend([Line2D([],[],color=GREY,marker='o',mfc='white',ls='--'),Line2D([],[],color=BLUE,marker='s',mfc='white',ls='--')],['全年交付记录（待补核）','同1—9月记录（待补核）'],loc='lower center',bbox_to_anchor=(.55,.055),ncol=2,fontsize=8.4)
save(fig,'figure_05_windows',window_data,['exploratory_annual_full_year.csv','exploratory_annual_jan_sep.csv'],'墨西哥2023—2024中国份额的变化方向依赖全年还是同1—9月窗口。','两个窗口都使用对应时期中国记录/所有来源记录，并列画出两年变化。',['不是稳健性识别检验，只是相同月份口径核查。','两个窗口仍有2024字段/重复及覆盖问题；同1—9月没有证明完整总体变化。','没有将九个月乘4/3，也没有把九个月直接与全年比较。'])

# Fig. 6: separate level/share panels; no interpolation of missing annual years.
mpdata=[]
for r in mp['series']:
    share=100*r['numerator_us_affiliate_output_musd']/r['denominator_host_gross_output_musd']
    assert math.isclose(share,100*r['target_fraction'],abs_tol=1e-10)
    mpdata.append({**r,'output_hundred_million_current_usd':r['numerator_us_affiliate_output_musd']/100,'share_pct':share})
fig,axes=layout(1,2,99,'图6  美国母公司在墨西哥机械业（C28）的产出与份额')
fig.subplots_adjust(left=.11,right=.978,bottom=.17,top=.78,wspace=.31)
for i,(key,yt,label,ylim) in enumerate([('output_hundred_million_current_usd',[0,25,50,75,100],'产出（亿美元，当年价）',(0,105)),('share_pct',[0,5,10,15,20,25],'占墨西哥该行业总产出（%）',(0,27))]):
    ax=axes[0,i];xs=[r['year'] for r in mpdata];ys=[r[key] for r in mpdata]
    ax.bar(xs,ys,width=.65,color=BLUE if i==0 else TEAL)
    for x,y in zip(xs,ys):ax.text(x,y+(.9 if i==1 else 3),f'{y:.2f}'+('%' if i==1 else ''),ha='center',va='bottom',fontsize=9)
    ax.set_xticks(xs);ax.set_xlim(2016.2,2022.8);ax.set_yticks(yt);ax.set_ylim(ylim);ax.set_ylabel(label);ax.set_xlabel('年份');tidy(ax)
save(fig,'figure_06_mp',mpdata,['mp_pilot_prepare_2026_10_03/PILOT_SUMMARY.json'],'美国母公司机械业产出水平与其占东道国总产出份额呈现不同幅度的变化。','两个独立坐标面板分别展示AMNE产出及同源分子/分母份额，只画2017、2019、2022三个实际端点。',['产出为当年价百万美元除100转换为亿美元，未作价格调整。','分母为墨西哥C28全部母国及本土产出，不是仅外资企业总产出。','未插值年份、未双轴、未把观察到的份额变化反推hgamma或福利。'])

assert all(sha(ROOT/k)==v for k,v in SOURCE_HASHES.items()),'Source summaries changed during plotting.'
(OUT/'PLOT_CONTRACT.json').write_text(json.dumps({'backend':'Python / matplotlib','font':FONT,'source_hashes':SOURCE_HASHES,'figures':CONTRACTS,'previous_sources_unchanged':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'FIGURE_VALIDATION.json').write_text(json.dumps({'status':'automated_checks_passed_visual_review_pending','versions':{'python':platform.python_version(),'matplotlib':matplotlib.__version__},'font_family':FONT,'font_file':FONT_PATH,'figures':REVIEWS},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'figures':len(CONTRACTS),'names':[r['figure'] for r in CONTRACTS],'source_files_unchanged':True},ensure_ascii=False))
