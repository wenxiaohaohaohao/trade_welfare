"""Build staged descriptive fDi accounting without changing previous results.

Input is the audited, row-addressable Manufacturing extract. Both the raw
workbook fingerprint and the extract's previously recorded fingerprint must match.
Use --tables-only to make the numerical hand-off before figure generation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "output/fdi_facts_2026_10_02"
OUT = ROOT / "output/fdi_research_baseline_2026_10_03"
TMP = ROOT / "tmp/fdi_staged_2026_10_03"
RAW = ROOT / "data/raw/fDi_Markets .xlsx"
EXTRACT = OLD / "manufacturing_records_with_audit_flags.csv"
COUNTRIES = ["Mexico", "Vietnam", "Thailand"]
TYPES = {"New": "new", "Expansion": "expansion", "Co-Location": "co_location"}
GROUPS = {"China": "china", "Other East Asia": "other_east_asia", "United States": "united_states", "Other parents": "other_parents"}
STAGES = {"2014-2017": list(range(2014,2018)), "2018-2019": [2018,2019], "2020-2022": [2020,2021,2022]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def write_json(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")


def save_table(name,rows):
    path=OUT/(name+".csv")
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    return path


def summarize(rows,country,years,max_month,stage):
    sub=[r for r in rows if r["Destination_Country"]==country and r["year"] in years and r["month"]<=max_month]
    n=len(sub)
    d={"country":country,"stage":stage,"first_year":min(years),"last_year":max(years),"n_years":len(years),"months_per_year":max_month,"records":n,"mean_records_per_year_in_month_window":n/len(years)}
    for native,key in TYPES.items():
        count=sum(r["Project_Type"]==native for r in sub)
        d[f"{key}_records"]=count
        d[f"{key}_share_pct"]=100*count/n if n else None
    for native,key in GROUPS.items():
        count=sum(r["source_group"]==native for r in sub)
        d[f"{key}_records"]=count
        d[f"{key}_share_pct"]=100*count/n if n else None
    assert sum(d[f"{key}_records"] for key in TYPES.values())==n
    assert sum(d[f"{key}_records"] for key in GROUPS.values())==n
    if n:
        assert math.isclose(sum(d[f"{key}_share_pct"] for key in TYPES.values()),100,abs_tol=1e-9)
        assert math.isclose(sum(d[f"{key}_share_pct"] for key in GROUPS.values()),100,abs_tol=1e-9)
    return d


def graph(annual):
    # Figure contract: a quantitative grid shows annual levels and composition.
    # It does not identify any policy/pandemic effect or compare 2023 with full years.
    os.environ["MPLCONFIGDIR"]=str(TMP/"matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams.update({"font.family":"sans-serif","font.sans-serif":["Arial","DejaVu Sans"],"font.size":9,"axes.labelsize":9,"xtick.labelsize":8,"ytick.labelsize":8,"axes.spines.right":False,"axes.spines.top":False,"axes.linewidth":.7,"legend.frameon":False,"svg.fonttype":"none","pdf.fonttype":42,"savefig.facecolor":"white","figure.facecolor":"white"})
    fig,axes=plt.subplots(3,3,figsize=(183/25.4,163/25.4),sharex=True,sharey="row")
    fig.subplots_adjust(left=.115,right=.978,bottom=.20,top=.845,hspace=.24,wspace=.16)
    fig.text(.025,.967,"Annual manufacturing project records and composition",weight="bold",fontsize=11,va="top")
    fig.text(.025,.92,"Mexico, Vietnam and Thailand | Full calendar years, 2014-2022",fontsize=9,color="#555555",va="top")
    metrics=[("records","Records",(0,220),[0,50,100,150,200]),("expansion_share_pct","Expansion share (%)",(0,60),[0,20,40,60]),("china_share_pct","China share (%)",(0,40),[0,10,20,30,40])]
    for c,country in enumerate(COUNTRIES):
        data=sorted([r for r in annual if r["country"]==country],key=lambda x:x["year"])
        years=[r["year"] for r in data]
        for r,(metric,label,ylim,ticks) in enumerate(metrics):
            ax=axes[r,c]
            ax.axvspan(2019.5,2022.5,color="#EEEEEE",zorder=0)
            ax.plot(years,[z[metric] for z in data],color="#346987",marker="o",ms=3.5,lw=1.25,zorder=3)
            ax.set_xlim(2013.7,2022.35)
            ax.set_ylim(ylim)
            ax.set_yticks(ticks)
            ax.set_xticks([2014,2016,2018,2020,2022])
            ax.grid(axis="y",color="#DFE3E6",lw=.55,zorder=1)
            ax.set_axisbelow(True)
            ax.tick_params(length=3,pad=3)
            if c==0: ax.set_ylabel(label,labelpad=8)
            if r==0: ax.set_title(country,fontsize=10,weight="bold",pad=9)
            if r==2: ax.set_xlabel("Year",labelpad=5)
    fig.legend([Patch(facecolor="#EEEEEE",edgecolor="#C8C8C8")],["2020-2022 (descriptive period marker)"],loc="lower left",bbox_to_anchor=(.10,.112),fontsize=8.3,handlelength=1.3)
    fig.text(.025,.091,"Sample: Activity = Manufacturing; all source countries, project types and statuses. No amount weighting.",fontsize=7.5)
    fig.text(.025,.059,"Shares use all delivered manufacturing records in the same country and year as their denominator.",fontsize=7.5)
    fig.text(.025,.027,"Records are not verified unique projects. 2023 is reported separately using January-September in every year.",fontsize=7.5)
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    outside=[]
    for t in fig.findobj(matplotlib.text.Text):
        if t.get_visible() and t.get_text():
            b=t.get_window_extent(renderer)
            if b.x0<-.5 or b.y0<-.5 or b.x1>fig.bbox.x1+.5 or b.y1>fig.bbox.y1+.5: outside.append(t.get_text())
    assert not outside,outside
    output=[]
    for ext in ["png","svg","pdf"]:
        path=OUT/f"staged_annual_paths.{ext}"
        fig.savefig(path,dpi=300)
        output.append({"file":path.name,"sha256":sha(path)})
    svg=(OUT/"staged_annual_paths.svg").read_text(encoding="utf-8")
    assert "<text" in svg and "<image" not in svg
    plt.close(fig)
    return {"contract":{"core_conclusion":"Annual record counts and composition vary across the three destinations and over time; staged comparisons should preserve these paths.","evidence_chain":"Columns identify destinations; rows show count, Expansion share and China share from the same annual record universe.","archetype":"quantitative grid","backend":"Python / matplotlib","size_mm":[183,163],"body_font_pt":9,"png_dpi":300,"editable_vector_text":True},"caption":"Annual Manufacturing records for Mexico, Vietnam and Thailand, 2014-2022. Every source country, project type and project status is retained. Each percentage uses the destination-year record count as denominator; amounts and jobs are not weights. The pale grey region marks 2020-2022 descriptively and estimates no policy or pandemic effect. Counts refer to delivered records, with unverified uniqueness and coverage. The January-September-only extension through 2023 is tabulated separately.","source_table":{"file":"staged_annual_full_year.csv","sha256":sha(OUT/"staged_annual_full_year.csv")},"outputs":output,"qa":{"all_visible_text_inside_canvas":True,"svg_text_editable":True,"no_svg_raster_images":True,"manual_visual_review":"pending"},"matplotlib_version":matplotlib.__version__}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--tables-only",action="store_true")
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    TMP.mkdir(parents=True,exist_ok=True)
    os.environ["TMP"]=str(TMP);os.environ["TEMP"]=str(TMP)
    old_hashes={str(p.relative_to(ROOT)):sha(p) for p in OLD.rglob("*") if p.is_file()}
    old_method=json.loads((OLD/"METHOD_AND_VALIDATION.json").read_text(encoding="utf-8"))
    old_manifest=json.loads((OLD/"TABLE_MANIFEST.json").read_text(encoding="utf-8"))
    assert sha(RAW)==old_method["raw_sha256"],"Raw workbook changed: re-audit before using this extract."
    assert sha(EXTRACT)==old_manifest[EXTRACT.name],"Extract differs from the approved provenance manifest."
    protected_raw=sha(RAW)
    rows=read(EXTRACT)
    for r in rows:
        r["year"]=int(r["year"]);r["month"]=int(r["month"]);r["excel_row"]=int(r["excel_row"])
        assert r["Activity"]=="Manufacturing" and r["Destination_Country"] in COUNTRIES
        assert r["Project_Type"] in TYPES and r["source_group"] in GROUPS
        assert 2014<=r["year"]<=2023 and 1<=r["month"]<=12
        assert r["year"]<2023 or r["month"]<=9
        country=r["Source_Country"]
        expected="China" if country=="China" else "United States" if country=="United States" else "Other East Asia" if country in ["Japan","South Korea","Taiwan"] else "Other parents"
        assert expected==r["source_group"]
        parent=re.sub(r"\s+"," ",unicodedata.normalize("NFKC",r["Parent_Company"])).strip().casefold()
        assert parent and parent==r["parent_normalized"]
        assert r["parent_host_key"]=="|".join([r["Source_Country"],parent,r["Destination_Country"]])
    assert len({r["excel_row"] for r in rows})==len(rows),"Repeated original row provenance."
    annual=[];annual9=[];periods=[];periods9=[]
    for c in COUNTRIES:
        for y in range(2014,2023):
            d=summarize(rows,c,[y],12,str(y));d={"country":c,"year":y,**{k:v for k,v in d.items() if k!="country"}}
            annual.append(d)
        for y in range(2014,2024):
            d=summarize(rows,c,[y],9,str(y));d={"country":c,"year":y,**{k:v for k,v in d.items() if k!="country"}}
            annual9.append(d)
        periods.extend(summarize(rows,c,ys,12,st) for st,ys in STAGES.items())
        periods9.extend(summarize(rows,c,ys,9,st) for st,ys in {**STAGES,"2023":[2023]}.items())
    tables={"staged_annual_full_year":annual,"staged_period_full_year":periods,"staged_annual_jan_sep":annual9,"staged_period_jan_sep":periods9}
    for name,table in tables.items(): save_table(name,table)
    changes=[]
    for c in COUNTRIES:
        pp=[r for r in periods if r["country"]==c]
        for a,b in [(pp[0],pp[1]),(pp[1],pp[2]),(pp[0],pp[2])]:
            d={"country":c,"from_stage":a["stage"],"to_stage":b["stage"],"from_mean_records_per_year":a["mean_records_per_year_in_month_window"],"to_mean_records_per_year":b["mean_records_per_year_in_month_window"],"mean_records_change_pct":100*(b["mean_records_per_year_in_month_window"]/a["mean_records_per_year_in_month_window"]-1)}
            d.update({key+"_change_pp":b[key]-a[key] for key in a if key.endswith("_share_pct")})
            changes.append(d)
    save_table("staged_period_changes_full_year",changes)
    baseline=[r for r in rows if r["year"] in STAGES["2014-2017"]]
    known_parents={r["parent_host_key"] for r in baseline}
    known_sectors={(r["parent_host_key"],r["Sector"]) for r in baseline}
    history=[]
    for c in COUNTRIES:
        for stage in ["2018-2019","2020-2022"]:
            post=[r for r in rows if r["Destination_Country"]==c and r["year"] in STAGES[stage]]
            matched=[r for r in post if r["parent_host_key"] in known_parents]
            sector=[r for r in post if (r["parent_host_key"],r["Sector"]) in known_sectors]
            nn=sum(r["Project_Type"]=="New" for r in matched)
            sn=sum(r["Project_Type"]=="New" for r in sector)
            h={"country":c,"baseline_stage":"2014-2017","post_stage":stage,"all_post_records":len(post),"matched_parent_host_records":len(matched),"matched_new_records":nn,"matched_expansion_records":sum(r["Project_Type"]=="Expansion" for r in matched),"matched_co_location_records":sum(r["Project_Type"]=="Co-Location" for r in matched),"matched_new_share_pct":100*nn/len(matched) if matched else None,"same_sector_matched_records":len(sector),"same_sector_new_records":sn,"same_sector_new_share_pct":100*sn/len(sector) if sector else None}
            assert h["matched_new_records"]+h["matched_expansion_records"]+h["matched_co_location_records"]==h["matched_parent_host_records"]
            assert len(sector)<=len(matched)<=len(post)
            history.append(h)
    save_table("staged_parent_history",history)
    previous=read(OLD/"annual_country_type_source.csv")
    previous_counts=Counter()
    for r in previous: previous_counts[(r["country"],int(r["year"]))]+=int(r["records"])
    checks={"annual_counts_match_prior_joint_table":all(r["records"]==previous_counts[(r["country"],r["year"])] for r in annual),"full_year_total_records":sum(r["records"] for r in annual),"full_year_periods_reconcile":sum(r["records"] for r in periods)==sum(r["year"]<=2022 for r in rows),"jan_sep_periods_reconcile":sum(r["records"] for r in periods9)==sum(r["month"]<=9 for r in rows),"all_type_and_source_partitions_exact":True,"row_provenance_unique":True,"raw_fingerprint_matches_prior_audit":True,"extract_fingerprint_matches_prior_manifest":True}
    assert checks["annual_counts_match_prior_joint_table"] and checks["full_year_periods_reconcile"] and checks["jan_sep_periods_reconcile"]
    method={"status":"computed; numerical review and visual sign-off recorded separately","scope":"Gate 2 descriptive project evidence; no causal or welfare identification","sample":"Activity exactly Manufacturing; Mexico, Vietnam, Thailand; all origins, types and statuses; delivered records retained without deduplication","unit":"Delivered project record, not verified unique firm, plant or realized project","input":{"raw_workbook_sha256":protected_raw,"row_addressable_extract":str(EXTRACT.relative_to(ROOT)),"extract_sha256":sha(EXTRACT),"original_sheet":"2014-2023","original_row_column":"excel_row","extract_records":len(rows)},"full_year_periods":STAGES,"jan_sep_periods":{**STAGES,"2023":[2023]},"period_means":"Period total divided by the fixed number of calendar years. January-September means are 9-month record counts per calendar year, never multiplied by 4/3 and never called full-year annualized totals.","shares":"Pooled within destination and period, count numerator divided by all Manufacturing records in that destination-period. Period shares are not unweighted averages of annual percentages.","zero_cells":"A category absent from the delivered sample is counted as zero; this does not verify zero economic activity or full database coverage. A wholly empty denominator would yield null share.","source_groups":{"China":["China"],"Other East Asia":["Japan","South Korea","Taiwan"],"United States":["United States"],"Other parents":"All others, including Hong Kong and Singapore"},"sector_scope":"All native sectors with Manufacturing activity; no equivalence to existing F03 ISIC sectors asserted","quality_boundary":"2023 Q4 and 2024 excluded. No deduplication, missing-value imputation, amount or employment weighting, first-entry inference or operating-presence inference. Known prior data-delivery concerns remain unresolved.","pandemic_boundary":"2020-2022 is a descriptive period. No pandemic adjustment, policy attribution or identification model is estimated.","statistics":"Descriptive counts and shares; no tests or confidence intervals","checks":checks,"versions":{"python":platform.python_version()}}
    method["parent_history"]={"baseline":"Fixed 2014-2017 Manufacturing records","post_stages":["2018-2019","2020-2022"],"match":"Exact Source_Country + NFKC/whitespace/case-normalized Parent_Company + Destination_Country; second version also requires same native Sector","meaning":"Positive match is recorded project history, not proven operation or verified firm identity. No prior match is not entry. New is not first enterprise entry.","unit":"Post-period records in matched subgroup, not number of unique parents or continuing plants"}
    method["checks"]["parent_subgroup_partitions_exact"]=True
    if not args.tables_only: method["figure"]=graph(annual)
    method["checks"]["previous_output_directory_unchanged"]=all(sha(ROOT/p)==h for p,h in old_hashes.items())
    method["checks"]["raw_workbook_unchanged"]=sha(RAW)==protected_raw
    assert method["checks"]["previous_output_directory_unchanged"] and method["checks"]["raw_workbook_unchanged"]
    method["output_tables"]={p.name:sha(p) for p in OUT.glob("staged_*.csv")}
    write_json("STAGED_METHOD.json",method)
    print(json.dumps({"records_2014_2022":checks["full_year_total_records"],"full_year_periods":[{k:r[k] for k in ["country","stage","records","mean_records_per_year_in_month_window","expansion_share_pct","china_share_pct"]} for r in periods],"jan_sep_2023":[r for r in periods9 if r["stage"]=="2023"],"checks":checks},ensure_ascii=False,indent=2))


if __name__=="__main__":main()
