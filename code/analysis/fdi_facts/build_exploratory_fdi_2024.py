"""Explore the delivered 2014-2024 fDi records, preserving coverage warnings.

Reads both original Excel tables. No deduplication, missing-type zero filling,
amount weighting or full-year extrapolation is applied. Prior outputs are protected.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/fdi_research_baseline_2026_10_03'
TMP=ROOT/'tmp/fdi_exploratory_2024'
RAW=ROOT/'data/raw/fDi_Markets .xlsx'
COUNTRIES=['Mexico','Vietnam','Thailand']
GROUPS={'China':'china','Other East Asia':'other_east_asia','United States':'united_states','Other parents':'other_parents'}
TYPES={'New':'new','Expansion':'expansion','Co-Location':'co_location'}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def missing(v): return v is None or (isinstance(v,str) and v.strip() in ('','NA','N/A'))
def origin(v):
    return 'China' if v=='China' else 'United States' if v=='United States' else 'Other East Asia' if v in ('Japan','South Korea','Taiwan') else 'Other parents'
def table(name,rows):
    with (OUT/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def js(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def summarize(rows,country,year,months,month=None):
    sub=[r for r in rows if r['country']==country and r['year']==year and r['month'] in months]
    n=len(sub)
    d={'country':country,'year':year}
    if month is not None: d['month']=month
    d.update({'months_per_year':len(months),'records':n,'observed_months':len(set(r['month'] for r in sub)),'requested_months':','.join(map(str,months)),'coverage_status':'supplier_followup_required' if year>=2023 else 'historical_schema;coverage_unverified'})
    for group,key in GROUPS.items():
        nn=sum(r['source_group']==group for r in sub)
        d[key+'_records']=nn;d[key+'_share_pct']=100*nn/n if n else None
    for field in ['project_type','parent']:
        nn=sum(not missing(r[field]) for r in sub)
        d[field+'_field_present']=year<=2023
        d[field+'_available_records']=nn
        d[field+'_missing_records']=n-nn
        d[field+'_available_pct']=100*nn/n if n else None
    known=[r for r in sub if not missing(r['project_type'])]
    for typ,key in TYPES.items():
        nn=sum(r['project_type']==typ for r in known)
        d[key+'_records_in_known_types']=nn if known else None
        d[key+'_share_pct_of_known_types']=100*nn/len(known) if known else None
    d['exact_visible_field_duplicate_rows']=sum(r['exact_visible_field_duplicate_size']>1 for r in sub)
    d['exact_visible_field_duplicate_excess']=sum(r['exact_visible_field_duplicate_excess'] for r in sub)
    assert sum(d[k+'_records'] for k in GROUPS.values())==n
    if n: assert math.isclose(sum(d[k+'_share_pct'] for k in GROUPS.values()),100,abs_tol=1e-9)
    assert sum(r['project_type'] in TYPES for r in known)==len(known)
    if known: assert sum(d[k+'_records_in_known_types'] for k in TYPES.values())==len(known)
    return d

def plot(annual):
    # Quantitative grid; the claim is temporal description of delivered records.
    os.environ['MPLCONFIGDIR']=str(TMP/'matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':9,'axes.labelsize':9,'xtick.labelsize':8,'ytick.labelsize':8,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'legend.frameon':False,'svg.fonttype':'none','pdf.fonttype':42,'savefig.facecolor':'white','figure.facecolor':'white'})
    fig,axes=plt.subplots(2,3,figsize=(183/25.4,137/25.4),sharex=True,sharey='row')
    fig.subplots_adjust(left=.11,right=.982,bottom=.26,top=.82,wspace=.16,hspace=.22)
    fig.text(.025,.964,'Delivered manufacturing records: exploratory paths through 2024',fontsize=10.5,weight='bold',va='top')
    fig.text(.025,.912,'Full calendar-year extraction | 2023-2024 coverage and fields remain under supplier review',fontsize=8.5,color='#555555',va='top')
    metrics=[('records','Delivered records',(0,230),[0,50,100,150,200]),('china_share_pct','China share (%)',(0,60),[0,20,40,60])]
    for c,country in enumerate(COUNTRIES):
        data=sorted([r for r in annual if r['country']==country],key=lambda r:r['year'])
        early=[r for r in data if r['year']<=2022]
        late=[r for r in data if r['year']>=2022]
        for r,(metric,label,ylim,ticks) in enumerate(metrics):
            ax=axes[r,c]
            ax.axvspan(2022.5,2024.45,color='#F2F2F2',zorder=0)
            ax.plot([d['year'] for d in early],[d[metric] for d in early],color='#346987',marker='o',ms=3.3,lw=1.2,zorder=3)
            ax.plot([d['year'] for d in late],[d[metric] for d in late],color='#346987',ls='--',lw=1.2,zorder=3)
            ax.plot([d['year'] for d in late if d['year']>=2023],[d[metric] for d in late if d['year']>=2023],color='#346987',marker='o',mfc='white',mew=1.2,ms=4.6,lw=0,zorder=4)
            ax.set_xlim(2013.7,2024.45);ax.set_ylim(ylim);ax.set_yticks(ticks)
            ax.set_xticks([2014,2016,2018,2020,2022,2024]);ax.tick_params(length=3,pad=3)
            ax.grid(axis='y',color='#DFE3E6',lw=.55);ax.set_axisbelow(True)
            if c==0:ax.set_ylabel(label,labelpad=8)
            if r==0:ax.set_title(country,fontsize=10,weight='bold',pad=8)
            if r==1:ax.set_xlabel('Year',labelpad=5)
    handles=[Line2D([],[],color='#346987',marker='o',ms=3.5,lw=1.2),Line2D([],[],color='#346987',marker='o',mfc='white',ms=4.5,lw=1.2,ls='--')]
    fig.legend(handles,['2014-2022 delivered records','2023-2024: supplier follow-up pending'],loc='lower left',bbox_to_anchor=(.095,.153),ncol=2,fontsize=8,columnspacing=1.5,handlelength=2)
    fig.text(.025,.126,'Activity = Manufacturing; all sources and statuses. Counts retain potential duplicate records.',fontsize=7.5)
    fig.text(.025,.090,'China share uses all delivered records in each country-year. 2023 includes all supplied January-December rows.',fontsize=7.5)
    fig.text(.025,.054,'Open markers and dashed lines indicate unresolved delivery coverage; they do not confirm population changes.',fontsize=7.5)
    fig.text(.025,.018,'Project type and parent identity are absent in 2024. A comparable January-September table is provided separately.',fontsize=7.5)
    fig.canvas.draw();renderer=fig.canvas.get_renderer()
    outside=[]
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_visible() and t.get_text():
            b=t.get_window_extent(renderer)
            if b.x0<-.5 or b.y0<-.5 or b.x1>fig.bbox.x1+.5 or b.y1>fig.bbox.y1+.5:outside.append(t.get_text())
    assert not outside,outside
    output=[]
    for ext in ('png','svg','pdf'):
        p=OUT/f'exploratory_annual_paths_2014_2024.{ext}';fig.savefig(p,dpi=300)
        output.append({'file':p.name,'sha256':sha(p)})
    svg=(OUT/'exploratory_annual_paths_2014_2024.svg').read_text(encoding='utf-8')
    assert '<text' in svg and '<image' not in svg
    plt.close(fig)
    return {'contract':{'core_conclusion':'Delivered Manufacturing record counts and China-source shares are shown through 2024 while unresolved delivery periods are visibly distinguished.','evidence_chain':'Columns are destinations; rows are counts and China shares from the same annual universe. 2023-2024 are hollow markers with dashed connecting segments.','archetype':'quantitative grid','backend':'Python / matplotlib','dimensions_mm':[183,137],'png_dpi':300},'caption':'Annual delivered Manufacturing records, 2014-2024. Solid filled markers cover 2014-2022, while open markers and dashed segments identify 2023-2024 records requiring supplier follow-up. All supplied 2023 January-December records and all supplied 2024 months are retained. China shares divide China-source records by all delivered Manufacturing records in the destination-year. These are record-level descriptive paths, not verified population totals, unique projects, or causal changes. Potential duplicate records are retained. Project type and parent names are not available in 2024. January-September comparisons are separately tabulated without annual extrapolation.','source_table':{'file':'exploratory_annual_full_year.csv','sha256':sha(OUT/'exploratory_annual_full_year.csv')},'outputs':output,'qa':{'all_text_inside_canvas':True,'svg_text_editable':True,'no_svg_raster_images':True,'manual_visual_review':'pending'},'matplotlib_version':matplotlib.__version__}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tables-only',action='store_true');args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);TMP.mkdir(parents=True,exist_ok=True)
    os.environ['TMP']=str(TMP);os.environ['TEMP']=str(TMP)
    import openpyxl
    protected=[p for p in (ROOT/'output/fdi_facts_2026_10_02').rglob('*') if p.is_file()]+[p for p in OUT.glob('staged_*') if p.is_file()]+[OUT/'STAGED_METHOD.json']
    protected_hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    expected=json.loads((ROOT/'output/audits/fdi_markets_2026_10_02/validation.json').read_text(encoding='utf-8'))['raw_sha256']
    assert sha(RAW)==expected,'Workbook differs from audited file; re-audit before exploration.'
    wb=openpyxl.load_workbook(RAW,read_only=True,data_only=True)
    rows=[];schema={};sheet_counts={};duplicate_summary={}
    rename={'date':'Project_Date','company':'Investing_company','source':'Source_Country','destination':'Destination_Country','sector':'Sector','activity':'Activity','capex':'Capital_Investment','job':'Jobs_Created'}
    for name in ['2014-2023','2024']:
        it=wb[name].iter_rows(values_only=True);headers=list(next(it));original=list(it)
        schema[name]=headers;sheet_counts[name]=sum(any(v is not None for v in row) for row in original)
        keys=Counter(tuple(row) for row in original if any(v is not None for v in row));seen=Counter()
        for i,values in enumerate(original,start=2):
            if not any(v is not None for v in values):continue
            key=tuple(values);seen[key]+=1
            raw=dict(zip(headers,values));r={rename.get(k,k) if name=='2024' else k:v for k,v in raw.items()}
            if r['Activity']!='Manufacturing':continue
            dt=r['Project_Date'];assert isinstance(dt,datetime)
            assert r['Destination_Country'] in COUNTRIES and not missing(r['Source_Country'])
            typ=r.get('Project_Type');parent=r.get('Parent_Company')
            d={'sheet':name,'excel_row':i,'date':dt.date().isoformat(),'year':dt.year,'month':dt.month,'company':r['Investing_company'],'parent':None if missing(parent) else parent,'country':r['Destination_Country'],'source_country':r['Source_Country'],'source_group':origin(r['Source_Country']),'sector':r['Sector'],'activity':r['Activity'],'project_type':None if missing(typ) else typ,'project_status':None if missing(r.get('Project_Status')) else r['Project_Status'],'project_type_field_present':'Project_Type' in r,'parent_field_present':'Parent_Company' in r,'exact_visible_field_duplicate_size':keys[key],'exact_visible_field_duplicate_excess':int(seen[key]>1)}
            rows.append(d)
        selected=[r for r in rows if r['sheet']==name]
        duplicate_summary[name]={'manufacturing_records':len(selected),'records_in_exact_visible_field_duplicate_groups':sum(r['exact_visible_field_duplicate_size']>1 for r in selected),'exact_visible_field_duplicate_excess':sum(r['exact_visible_field_duplicate_excess'] for r in selected),'key_fields_count':len(headers)}
    wb.close()
    assert len({(r['sheet'],r['excel_row']) for r in rows})==len(rows)
    table('exploratory_manufacturing_records',rows)
    annual=[summarize(rows,c,y,list(range(1,13))) for c in COUNTRIES for y in range(2014,2025)]
    jansep=[summarize(rows,c,y,list(range(1,10))) for c in COUNTRIES for y in range(2014,2025)]
    monthly=[summarize(rows,c,y,[m],m) for c in COUNTRIES for y in [2023,2024] for m in range(1,13)]
    table('exploratory_annual_full_year',annual);table('exploratory_annual_jan_sep',jansep);table('exploratory_monthly_2023_2024',monthly)
    sources=[]
    for c in COUNTRIES:
        for y in [2023,2024]:
            for m in range(1,13):
                sub=[r for r in rows if r['country']==c and r['year']==y and r['month']==m]
                by=Counter(r['source_country'] for r in sub)
                for source,n in sorted(by.items()):sources.append({'country':c,'year':y,'month':m,'source_country':source,'source_group':origin(source),'records':n,'all_source_month_records':len(sub)})
    table('exploratory_monthly_source_country_2023_2024',sources)
    checks={'source_partitions_reconcile':True,'known_type_counts_reconcile':True,'row_provenance_unique':True,'annual_total_matches_selected_rows':sum(r['records'] for r in annual)==len(rows),'2024_absent_type_never_zero_filled':all(r['new_records_in_known_types'] is None and r['expansion_records_in_known_types'] is None for r in annual if r['year']==2024),'2023_all_supplied_months_retained':sum(r['records'] for r in annual if r['year']==2023)==sum(r['year']==2023 for r in rows)}
    assert all(checks.values())
    method={'status':'exploratory computed; numerical review and figure QA recorded separately','gate':'Gate 2 delivered-record descriptive evidence only','raw_sha256':expected,'raw_file':str(RAW.relative_to(ROOT)),'schema':schema,'sheet_total_records':sheet_counts,'unit':'Delivered project record; uniqueness and complete database coverage unverified','sample':'Activity exactly Manufacturing; Mexico/Vietnam/Thailand; all source countries, statuses and supplied rows; full 2014-2024 dates for primary exploratory table','source_group_definition':{'China':['China'],'Other East Asia':['Japan','South Korea','Taiwan'],'United States':['United States'],'Other parents':'All others, including Hong Kong and Singapore'},'coverage_boundary':'2023 includes all supplied 12 months despite suspected October-November source-country omissions and December field losses. 2024 includes all supplied 12 months despite shortened schema and duplicate candidates. Observed zero rows in a month or category do not establish zero economic activity or a complete census.','missingness':'Available-record counts can legitimately be zero with 0% availability, but absent Project_Type yields null New/Expansion/Co-location counts and shares, never zero classifications. Known-type shares in 2023 exclude unknown types and are labelled as such; they are not full-year type shares. Parent is absent in the 2024 schema; company is not silently relabelled as parent.','duplicates':{'policy':'All original rows retained. Identical visible values may represent distinct locations; flagged but not removed. 2024 has only eight fields so visible-field identity is not a true project identity.', 'counts':duplicate_summary},'jan_sep':'All years restricted to January-September, including 2024; no multiplication by 4/3, no mixing nine-month counts with full-year counts.','weights':'None. Capital amounts and jobs are not used as weights or production measures.','interpretation':'Descriptive patterns in delivered records, not confirmed population changes, realized investment, causal policy or pandemic effects, enterprise entry or welfare changes.','statistics':'Counts and shares; no inferential tests or intervals.','checks':checks,'versions':{'python':platform.python_version(),'openpyxl':openpyxl.__version__},'recent_year_summary':[r for r in annual if r['year'] in [2023,2024]]}
    if not args.tables_only:method['figure']=plot(annual)
    method['checks']['prior_facts_and_staged_outputs_unchanged']=all(sha(ROOT/p)==h for p,h in protected_hashes.items())
    method['checks']['raw_workbook_unchanged']=sha(RAW)==expected
    assert method['checks']['prior_facts_and_staged_outputs_unchanged'] and method['checks']['raw_workbook_unchanged']
    method['table_hashes']={p.name:sha(p) for p in OUT.glob('exploratory_*.csv')}
    js('EXPLORATORY_METHOD.json',method)
    print(json.dumps({'recent_year_summary':method['recent_year_summary'],'duplicates':duplicate_summary,'checks':checks},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
