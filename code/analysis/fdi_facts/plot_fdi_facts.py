"""Reproduce descriptive fDi figures from the separately validated summary tables.

The unit is a delivered project record, not a verified unique enterprise or plant.
Python/matplotlib is the exclusive drawing and export backend.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "output" / "fdi_facts_2026_10_02"
CACHE = ROOT / "tmp" / "fdi_facts_matplotlib"
CACHE.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(CACHE)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import PercentFormatter

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
    "font.size": 9, "axes.labelsize": 9, "xtick.labelsize": 8.5,
    "ytick.labelsize": 9, "legend.fontsize": 8.5, "legend.frameon": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.linewidth": 0.7, "axes.edgecolor": "#656565",
    "text.color": "#252525", "axes.labelcolor": "#252525",
    "xtick.color": "#555555", "ytick.color": "#252525",
    "svg.fonttype": "none", "pdf.fonttype": 42,
    "savefig.facecolor": "white", "figure.facecolor": "white",
})

COUNTRIES = ["Mexico", "Vietnam", "Thailand"]
COLORS = {"new": "#426885", "expansion": "#58A293", "co_location": "#D5B36A"}
TYPE_LABELS = {"new": "New", "expansion": "Expansion", "co_location": "Co-location"}
PRE, POST = "#6F7C89", "#176A86"
FIGURES = []


def read(name):
    with (OUT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(row, key):
    return float(row[key])


def integer(row, key):
    return int(float(row[key]))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frame(height_mm, title, subtitle):
    fig = plt.figure(figsize=(183 / 25.4, height_mm / 25.4))
    fig.text(.025, .965, title, va="top", fontsize=11, weight="bold")
    fig.text(.025, .906, subtitle, va="top", fontsize=8.5, color="#555555")
    return fig


def export(fig, stem, sources, conclusion, evidence, caption, risks):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    escaped = []
    for item in fig.findobj(matplotlib.text.Text):
        if not item.get_visible() or not item.get_text():
            continue
        box = item.get_window_extent(renderer)
        if box.x0 < -1 or box.y0 < -1 or box.x1 > bounds.x1 + 1 or box.y1 > bounds.y1 + 1:
            escaped.append(item.get_text())
    if escaped:
        raise AssertionError(f"Text outside fixed canvas in {stem}: {escaped}")
    files = []
    for ext in ["png", "svg", "pdf"]:
        path = OUT / f"{stem}.{ext}"
        fig.savefig(path, dpi=300, metadata={"Title": conclusion} if ext == "pdf" else None)
        files.append({"filename": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    svg = (OUT / f"{stem}.svg").read_text(encoding="utf-8")
    assert "<text" in svg and "<image" not in svg
    meta = {
        "id": stem.split("_")[0], "title": conclusion,
        "contract": {"core_conclusion": conclusion, "evidence_chain": evidence,
                     "archetype": "quantitative grid", "backend": "Python / matplotlib",
                     "dimensions_mm": [183, round(fig.get_size_inches()[1] * 25.4, 2)],
                     "export": ["300-dpi PNG", "editable-text SVG", "vector PDF with TrueType text"]},
        "caption": caption, "source_tables": [{"filename": n, "sha256": sha(OUT / n)} for n in sources],
        "unit": "Delivered project record; uniqueness is unverified",
        "sample": "Activity exactly Manufacturing; all sources, sectors, project types and statuses retained",
        "periods": {"pre": "2014-2017", "post": "2020-2022"},
        "statistics": {"n_definition": "Number of delivered records in the stated country, period and subgroup",
                       "center": "Pooled record-count shares; annual count = pooled count / number of calendar years",
                       "intervals": "None: descriptive accounting, no sampling model",
                       "tests": "None", "correction": "Not applicable", "p_values": "Not applicable"},
        "review_risks": risks,
        "qa": {"all_visible_text_inside_fixed_canvas": True, "editable_svg_text": True,
               "no_raster_objects_in_svg": True, "png_dpi": 300,
               "manual_visual_review": "See FIGURE_REVIEW.json; valid only when output hashes match"},
        "outputs": files,
    }
    FIGURES.append(meta)
    plt.close(fig)


types = {r["country"]: r for r in read("FDI01_type_composition.csv")}
china = {r["country"]: r for r in read("FDI02_source_composition.csv") if r["source_group"] == "China"}
history = {r["country"]: r for r in read("FDI03_parent_history.csv") if r["parent_history"] == "observed_in_pre"}

# Contract FDI01: composition distinguishes Mexico/Vietnam from Thailand.
fig = frame(116, "Expansion shares rise in Mexico and Vietnam", "Manufacturing records | 2014-2017 versus 2020-2022 | All source countries and statuses")
ax = fig.add_axes([.24, .24, .59, .59])
ypos = [5.4, 4.65, 3.35, 2.6, 1.3, .55]
labels = []
for i, country in enumerate(COUNTRIES):
    row = types[country]
    for j, period in enumerate(["pre", "post"]):
        y = ypos[2*i+j]
        left = 0
        counts = []
        for typ in COLORS:
            count = integer(row, f"{period}_{typ}_n")
            share = num(row, f"{period}_{typ}_share_pct")
            counts.append(count)
            ax.barh(y, share, left=left, height=.53, color=COLORS[typ], edgecolor="white", linewidth=.5)
            if share >= 9:
                ax.text(left+share/2, y, f"{share:.1f}%", ha="center", va="center", color="white", fontsize=8.5)
            left += share
        assert abs(left-100) < 1e-7
        n = integer(row, f"{period}_n")
        assert sum(counts) == n
        labels.append(f"{country if j == 0 else ''}\n{'2014-2017' if j == 0 else '2020-2022'}  (n = {n})")
        ax.text(103, y, "/".join(map(str, counts)), va="center", fontsize=8.1)
ax.text(103, 6.05, "Counts\nN / E / C", fontsize=8, va="top")
ax.set_yticks(ypos, labels)
ax.set_ylim(-.05, 6.0)
ax.set_xlim(0, 100)
ax.set_xticks([0,25,50,75,100])
ax.xaxis.set_major_formatter(PercentFormatter(100, decimals=0))
ax.set_xlabel("Share of manufacturing records")
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y", length=0, pad=8)
fig.legend([Patch(facecolor=c) for c in COLORS.values()], list(TYPE_LABELS.values()), loc="lower left", bbox_to_anchor=(.23,.10), ncol=3, handlelength=1.2, columnspacing=1.5)
fig.text(.025,.069,"N / E / C = New / Expansion / Co-location. Denominators are delivered records, not verified unique projects.",fontsize=7.5)
fig.text(.025,.028,"Thailand has no robust upward expansion shift across comparison windows. These are descriptive shares.",fontsize=7.5)
export(fig, "FDI01_type_composition", ["FDI01_type_composition.csv", "window_type_comparisons.csv"],
       "Expansion shares rise in Mexico and Vietnam, without a common three-country rise",
       "Six stacked bars compare pooled type shares; adjacent counts expose every numerator and denominator.",
       "Composition of delivered Manufacturing records, 2014-2017 and 2020-2022. New, Expansion and Co-location sum to each row's n. Mexico's expansion share rises from 37.35% to 51.01%; Vietnam's rises from 18.82% to 31.17%. Thailand moves from 41.24% to 39.62% in this window and the direction is window-sensitive. No inferential tests are shown.",
       ["Record counts are not verified unique projects", "New is not first enterprise entry", "Shares do not measure production growth", "Period comparison is not causal", "Thailand direction varies by window"])

# Contract FDI02: a higher China share need not mean a higher annual count.
fig = frame(113, "A higher China share need not mean more annual records", "Manufacturing records sourced from China | The two panels use the same underlying records")
axes = [fig.add_axes([.15,.31,.37,.48]), fig.add_axes([.65,.31,.31,.48])]
for k, ax in enumerate(axes):
    for i,country in enumerate(COUNTRIES):
        row = china[country]
        y = 2-i
        values = [num(row,f"{p}_{'share_pct' if k == 0 else 'annual_mean'}") for p in ["pre","post"]]
        ax.plot(values, [y+.13,y-.13], color="#BEC5C9", lw=1, zorder=1)
        for j,(p,color,marker) in enumerate([("pre",PRE,"o"),("post",POST,"s")]):
            val = values[j]
            yp = y+.13 if j == 0 else y-.13
            ax.scatter([val],[yp], color=color,marker=marker,s=30,zorder=3)
            ax.annotate(f"{val:.2f}" + ("%" if k == 0 else ""), (val,yp), xytext=(5,0), textcoords="offset points", va="center", color=color, fontsize=8.5)
    ax.set_ylim(-.45,2.45)
    ax.set_yticks([2,1,0],COUNTRIES if k == 0 else ["", "", ""])
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y",length=0,pad=9)
    ax.grid(axis="x",color="#E6E6E6",linewidth=.6)
    ax.set_axisbelow(True)
    ax.set_xlim(0,14.3 if k == 0 else 11.7)
    ax.set_xticks([0,5,10] if k == 0 else [0,3,6,9])
    ax.set_title("a  Share among all sources" if k == 0 else "b  Annual mean count", loc="left", fontsize=9, pad=10)
    ax.set_xlabel("China share (%)" if k == 0 else "Records per calendar year")
fig.legend([Line2D([],[],marker="o",color=PRE,lw=0,markersize=5),Line2D([],[],marker="s",color=POST,lw=0,markersize=5)], ["2014-2017 (4 years)","2020-2022 (3 years)"], loc="lower left",bbox_to_anchor=(.16,.16),ncol=2,columnspacing=2)
fig.text(.025,.126,"China / all-source counts, pre → post: Mexico 30/739 → 27/345; Vietnam 18/356 → 8/77;",fontsize=7.5)
fig.text(.025,.089,"Thailand 17/177 → 5/53. Annual means divide China counts by 4 and 3 years, respectively.",fontsize=7.5)
fig.text(.025,.044,"Shares are descriptive; Thailand's share change is window-sensitive. Records are not verified unique projects.",fontsize=7.5)
export(fig,"FDI02_china_share_and_count",["FDI02_source_composition.csv","FDI01_type_composition.csv","window_source_comparisons.csv"],
       "China's share rises in Mexico and Vietnam, but annual record counts rise only in Mexico in this window",
       "Panel a uses China records / all-source Manufacturing records. Panel b annualizes the same China counts to separate composition from volume.",
       "China-sourced Manufacturing records by destination. Shares use all-source records in the same destination and period as denominators. Annual means divide pooled China counts by four pre-period years and three post-period years. Vietnam's China share rises while its annual China record count falls. Thailand's direction of share change is not stable across windows. The descriptive counts do not establish actual capital inflows, production or trade diversion.",
       ["Denominator contraction can raise shares", "Unequal window lengths require annualized counts", "Thailand share is window-sensitive", "Delivery coverage is not independently proven", "No causal or welfare interpretation"])

# Contract FDI03: New projects appear even for previously observed parent-host names.
fig = frame(101, "Previously observed parent-host names also have New records", "2020-2022 Manufacturing records | Same normalized source-country / parent / host observed in 2014-2017")
ax=fig.add_axes([.23,.32,.60,.48])
labels=[]
for i,country in enumerate(COUNTRIES):
    row=history[country]
    y=2-i
    left=0
    counts=[]
    for typ in COLORS:
        share=num(row,f"{typ}_share_pct")
        count=integer(row,f"{typ}_n")
        counts.append(count)
        ax.barh(y,share,left=left,height=.54,color=COLORS[typ],edgecolor="white",linewidth=.5)
        if share>=9:
            ax.text(left+share/2,y,f"{share:.1f}%\n(n = {count})",ha="center",va="center",fontsize=8.5,color="white",linespacing=1.25)
        left+=share
    n=integer(row,"post_n")
    assert sum(counts)==n and abs(left-100)<1e-7
    labels.append(f"{country}\nn = {n}")
    ax.text(103,y,"/".join(map(str,counts)),va="center",fontsize=8.1)
ax.text(103,2.50,"Counts\nN / E / C",fontsize=8,va="top")
ax.set_yticks([2,1,0],labels)
ax.set_ylim(-.45,2.50)
ax.set_xlim(0,100)
ax.set_xticks([0,25,50,75,100])
ax.xaxis.set_major_formatter(PercentFormatter(100,decimals=0))
ax.set_xlabel("Share within the previously observed-name subgroup")
ax.spines["left"].set_visible(False)
ax.tick_params(axis="y",length=0,pad=9)
fig.legend([Patch(facecolor=c) for c in COLORS.values()],list(TYPE_LABELS.values()),loc="lower left",bbox_to_anchor=(.22,.16),ncol=3,handlelength=1.2,columnspacing=1.5)
fig.text(.025,.12,"Subgroup / all post records: Mexico 107/345; Vietnam 25/77; Thailand 11/53. N/E/C = New/Expansion/Co-location.",fontsize=7.5)
fig.text(.025,.075,"Positive matches indicate recorded project history, not proven local operation or enterprise identity.",fontsize=7.5)
fig.text(.025,.03,"New does not mean first enterprise entry. A missing prior name match is not evidence of entry.",fontsize=7.5)
export(fig,"FDI03_previously_observed_parents",["FDI03_parent_history.csv","window_parent_history_comparisons.csv","window_parent_sector_history_comparisons.csv"],
       "New records coexist with Expansion records among previously observed parent-host names",
       "Three stacked bars condition on a positive normalized source-parent-host match in the pre period. New counts are 28/107, 13/25 and 4/11.",
       "Type composition of 2020-2022 Manufacturing records whose normalized source-country, Parent_Company and destination-country combination appears in 2014-2017 Manufacturing records. Normalization uses Unicode NFKC, whitespace and case only, without fuzzy name matching. The matched subgroups contain 107, 25 and 11 records for Mexico, Vietnam and Thailand, respectively; 28, 13 and 4 are New. Exact positive name-history matches do not verify enterprise identity, operation, or first entry. The unmatched group is intentionally omitted because absence of observed project history is not entry evidence. Also requiring the same native sector gives New counts of 21/96, 9/20 and 3/9 in this window. Thailand has zero New records in at least one alternative window; this is not a universal three-country result.",
       ["Observed name history is not verified operating presence", "No fuzzy alias consolidation", "Small subgroup n, especially Thailand", "Unmatched does not mean new entrant", "New facility is not necessarily first enterprise entry", "Thailand has zero New records in an alternative window"])

bundle={"backend":"Python / matplotlib", "versions":{"python":platform.python_version(),"matplotlib":matplotlib.__version__},"figures":FIGURES}
(OUT/"FIGURE_METADATA.json").write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"figures":len(FIGURES),"outputs":[f["outputs"] for f in FIGURES],"qa":"all text within fixed canvas; inspect PNGs before final sign-off"},indent=2))
