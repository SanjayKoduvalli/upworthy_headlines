"""Build the case-study page (index.html) from the result files (R23). No number on the page is typed by hand (R24):
every figure in the text is a $placeholder filled here from build/04_analysis/*, docs/validation/* and the build tables.
Charts come from figures.py and are inlined as SVG, with a hover title on each mark and a data table under each chart.
Run from the project root after the analysis:  python3 pipeline/05_report/figures.py && python3 pipeline/05_report/build_case_study.py
"""
import json
import os
import re
import sys
from string import Template

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
from common import load_table  # noqa: E402

RES = os.path.join(ROOT, "build", "04_analysis")
FIG = os.path.join(ROOT, "assets", "figures")
GH = "https://github.com/SanjayKoduvalli/upworthy_headlines/blob/main/"
NAMES = {"POL": "Politics & world affairs", "RAC": "Race, religion & immigration", "GEN": "Gender equality & LGBTQ+",
         "HEA": "Health & medicine", "ECO": "Economy, work & inequality", "EDU": "Education", "FAM": "Children & family",
         "ENV": "Environment & climate", "CRI": "Crime, police & justice", "SCI": "Science & technology",
         "ENT": "Entertainment & media", "HUM": "Human interest & kindness"}


def J(split, name):
    return json.load(open(os.path.join(RES, split, name)))


def pct(x, d=1, sign=True):
    return f"{x:+.{d}f}%" if sign else f"{x:.{d}f}%"


def svg(name):
    """Inline a figure: strip the XML prolog, make it responsive, label it, add <title> tooltips to marks with a gid."""
    s = open(os.path.join(FIG, name + ".svg"), encoding="utf-8").read()
    s = re.sub(r"<\?xml[^>]*\?>\s*", "", s); s = re.sub(r"<!DOCTYPE[^>]*>\s*", "", s, flags=re.S)
    s = re.sub(r'<svg ([^>]*?)width="[^"]*" height="[^"]*"', r'<svg \1', s, count=1)
    s = s.replace("<svg ", '<svg role="img" class="chart" ', 1)
    tips = json.load(open(os.path.join(FIG, "tooltips.json")))
    for fig in tips.values():
        for gid, tip in fig.items():
            s = s.replace(f'<g id="{gid}">', f'<g id="{gid}"><title>{tip.replace("&", "&amp;")}</title>', 1)
    s = re.sub(r"<metadata>.*?</metadata>", "", s, flags=re.S)
    return s


def table(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tbl"><table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


# ------------------------------------------------------------------ numbers
mc, me = J("confirmatory", "main_results.json"), J("exploratory", "main_results.json")
ac, cc, ae = J("confirmatory", "aa_results.json"), J("confirmatory", "calibration.json"), J("exploratory", "aa_results.json")
tc, te = J("confirmatory", "topic_results.json"), J("exploratory", "topic_results.json")
val = json.load(open(os.path.join(ROOT, "docs", "validation", "classifier_validation.json")))["default"]
M = {r["term"]: r for r in mc["M1"]}; ME = {r["term"]: r for r in me["M1"]}
T1 = {r["topic"]: r for r in tc["T1"]["rows"]}; T1E = {r["topic"]: r for r in te["T1"]["rows"]}
T2 = {r["topic"]: r for r in tc["T2"]["rows"]}
sys.path.insert(0, os.path.join(ROOT, "pipeline", "05_report"))
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402


def main_ci(r, phi):
    b = np.log1p(r["pct"] / 100); z = r["z_raw"] / np.sqrt(phi); se = abs(b / z)
    return 100 * (np.exp(b - 1.96 * se) - 1), 100 * (np.exp(b + 1.96 * se) - 1), 2 * stats.norm.sf(abs(z))


PC = mc["phi_model_pearson"]
fvm = mc["female_vs_male"]; fvm_lo, fvm_hi, fvm_p = main_ci(fvm, PC)
f_lo, f_hi, _ = main_ci(M["female"], PC); m_lo, m_hi, _ = main_ci(M["male"], PC)
tests = load_table("02_clean/tests", content_blind=True)
tests = tests[tests.split.isin(["exploratory", "confirmatory"])]
labels = load_table("03_features/headline_labels", split="confirmatory")
labels_e = load_table("03_features/headline_labels", split="exploratory")
fp_after = 100 * (cc["split_half"]["fp_on_b_using_phi_a"] + cc["split_half"]["fp_on_a_using_phi_b"]) / 2
# M2 under the main method (R20: phi from the model), with Holm across the estimated topics
_m2 = sorted(((2 * stats.norm.sf(abs(r["z_raw"] / np.sqrt(PC))), r["topic"]) for r in mc["M2"]["interactions"]))
m2_main_sig, _stop = [], False
for _i, (_p, _t) in enumerate(_m2):
    if not _stop and _p < 0.05 / (len(_m2) - _i):
        m2_main_sig.append(_t)
    else:
        _stop = True
sig_neg = [t for t, r in sorted(T1.items(), key=lambda kv: kv[1]["pct"]) if r["sig_holm"] and r["pct"] < 0]

N = dict(
    n_tests_all=f"{len(tests):,}", n_tests_conf=f"{(tests.split == 'confirmatory').sum():,}",
    n_tests_expl=f"{(tests.split == 'exploratory').sum():,}", n_pk=f"{int(tests.n_packages.sum()):,}",
    n_window=f"{int(tests.in_problem_window.sum()):,}", n_srm=f"{int(tests.srm_fail.sum()):,}",
    n_usable=f"{int(tests.usable_causal.sum()):,}",
    n_head_tests=f"{mc['data']['tests_used']:,}", n_versions=f"{mc['data']['rows_used']:,}",   # what the model used (tests with zero clicks drop out)
    n_head_tests_e=f"{me['data']['tests']:,}",
    n_aa=f"{ac['AA1']['tests']:,}", aa_fp=pct(100 * ac["AA2"]["rate"], sign=False), aa_fp_e=pct(100 * ae["AA2"]["rate"], sign=False),
    aa_first=pct(100 * ac["AA3"]["share_per_tenth"][0], sign=False), aa_after=pct(fp_after, sign=False),
    phi_aa=f"{cc['phi']:.2f}", phi_model=f"{PC:.2f}", sqrt_phi=f"{PC ** 0.5:.1f}",
    n_labels=f"{len(labels) + len(labels_e):,}", n_labels_conf=f"{len(labels):,}",
    woman=pct(M["female"]["pct"]), woman_lo=pct(f_lo), woman_hi=pct(f_hi), woman_e=pct(ME["female"]["pct"]),
    man=pct(M["male"]["pct"]), man_lo=pct(m_lo), man_hi=pct(m_hi), both=pct(M["both"]["pct"]),
    fvm=pct(fvm["pct"]), fvm_lo=pct(fvm_lo), fvm_hi=pct(fvm_hi), fvm_p=f"{fvm_p:.2f}", fvm_e=pct(me["female_vs_male"]["pct"]),
    neg=pct(M["negative"]["pct"]), pos=pct(M["positive"]["pct"]),
    env=pct(T1["ENV"]["pct"]), eco=pct(T1["ECO"]["pct"]), pol=pct(T1["POL"]["pct"]), hum=pct(T1["HUM"]["pct"]),
    gen_e=pct(T1E["GEN"]["pct"]), gen_c=pct(T1["GEN"]["pct"]),
    t2_gen=pct(T2["GEN"]["pct"]), t2_env=pct(T2["ENV"]["pct"]), t2_eco=pct(T2["ECO"]["pct"]),
    n_neg_topics=str(len(sig_neg)),
    v_gender=val["Gender agreement"], v_gender_k=val["Gender kappa"], v_sent=val["Sentiment agreement"],
    v_sent_k=val["Sentiment kappa"], v_topic=val["Sanjay's topic among the tags"],
    m2_none="no topic" if not m2_main_sig else ", ".join(NAMES[t] for t in m2_main_sig),
)

# ------------------------------------------------------------------ tables under the charts
f1_rows = []
for term, lab in [("female", "A woman"), ("male", "A man"), ("both", "Both"), ("fvm", "A woman vs. a man"),
                  ("negative", "Negative tone"), ("positive", "Positive tone")]:
    r = fvm if term == "fvm" else M[term]; e = me["female_vs_male"] if term == "fvm" else ME[term]
    lo, hi, p = main_ci(r, PC)
    f1_rows.append([lab, pct(r["pct"]), f"{pct(lo)} to {pct(hi)}", "&lt; 0.001" if p < 0.001 else f"{p:.3f}", pct(e["pct"])])
f1_table = table(["Headline", "Confirmatory", "95% interval", "p", "Exploratory"], f1_rows)
f2_table = table(["p-value range", "Share of identical-version tests"],
                 [[f"{i / 10:.1f}–{(i + 1) / 10:.1f}", pct(100 * v, sign=False)] for i, v in enumerate(ac["AA3"]["share_per_tenth"])])
f3_table = table(["Headline framed around", "Confirmatory", "95% interval", "Holm-significant", "Exploratory"],
                 [[NAMES[t], pct(r["pct"]), f"{pct(r['lo'])} to {pct(r['hi'])}", "yes" if r["sig_holm"] else "no", pct(T1E[t]["pct"])]
                  for t, r in sorted(T1.items(), key=lambda kv: kv[1]["pct"])])
f4_table = table(["Topic", "Stories about it (descriptive)", "Headline framed around it (causal)"],
                 [[NAMES[t], pct(T2[t]["pct"]), pct(T1[t]["pct"])] for t in sorted(T2, key=lambda t: -T2[t]["pct"])])
N.update(f1=svg("f1_gender_tone"), f2=svg("f2_aa_check"), f3=svg("f3_topic_framing"), f4=svg("f4_framing_vs_story"),
         f1_table=f1_table, f2_table=f2_table, f3_table=f3_table, f4_table=f4_table,
         neg_topics=", ".join(NAMES[t].split(" &")[0].split(",")[0].lower() for t in sig_neg), gh=GH)

demo = json.load(open(os.path.join(ROOT, "docs", "validation", "classifier_validation_items.json"), encoding="utf-8"))
N["demo_data"] = json.dumps(demo, ensure_ascii=False).replace("</", "<\\/")      # safe inside <script>
import csv  # noqa: E402
secs = sorted(float(r["seconds"]) for r in csv.DictReader(open(os.path.join(ROOT, "docs", "validation", "human_labels.csv"))) if r["seconds"])
N["median_secs"] = f"{(secs[len(secs) // 2 - 1] + secs[len(secs) // 2]) / 2 if len(secs) % 2 == 0 else secs[len(secs) // 2]:.0f}"

page = Template(open(os.path.join(os.path.dirname(__file__), "case_study_template.html"), encoding="utf-8").read())
out = page.substitute(N)
assert not re.search(r"\$\{?[A-Za-z_]", re.sub(r'<script type="application/json".*?</script>|<svg.*?</svg>', "", out, flags=re.S)), \
    "an unfilled placeholder is left on the page"
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)
print("index.html written:", len(out), "bytes")
