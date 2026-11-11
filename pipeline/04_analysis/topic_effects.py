"""Which topics get more clicks: T1 (headline framing, causal) and T2 (story topic, descriptive).
NOTES §8.3, approved by Sanjay 2026-11-10 23:59 (R21). Exploratory only (R2). Significance: quasi-binomial with phi
estimated from each model itself (R20); Holm across the 12 topics.

T1: the within-test model M1 (gender, sentiment, test fixed effects) plus all 12 topic tags.
T2: one row per usable test; tags = tags on at least half of the test's packages; month fixed effects.
Checks: Mantel-Haenszel estimate for the largest T1 effect; T2 with year instead of month fixed effects.
Writes build/04_analysis/topic_results.json and docs/results/topic_effects.md.
"""
import json
import os
import sys

import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from common import BUILD, DOCS, SPLIT, load_table  # noqa: E402
from felogit import fit, pct_change  # noqa: E402
from main_effects import M1_TERMS, TOPICS  # noqa: E402

NAMES = {"POL": "Politics & world affairs", "RAC": "Race, religion & immigration", "GEN": "Gender equality & LGBTQ+",
         "HEA": "Health & medicine", "ECO": "Economy, work & inequality", "EDU": "Education", "FAM": "Children & family",
         "ENV": "Environment & climate", "CRI": "Crime, police & justice", "SCI": "Science & technology",
         "ENT": "Entertainment & media", "HUM": "Human interest & kindness"}


def summarize(res, terms, phi):
    out = []
    for t in terms:
        i = res["names"].index(t)
        b, se = res["beta"][i], res["se_raw"][i] * np.sqrt(phi)
        out.append({"topic": t.replace("topic_", ""), "pct": float(pct_change(b)), "lo": float(pct_change(b - 1.96 * se)),
                    "hi": float(pct_change(b + 1.96 * se)), "z": float(b / se), "p": float(2 * stats.norm.sf(abs(b / se)))})
    order = np.argsort([r["p"] for r in out]); stop = False
    for rank, i in enumerate(order):
        out[i]["holm_threshold"] = 0.05 / (len(out) - rank)
        out[i]["sig_holm"] = (not stop) and out[i]["p"] < out[i]["holm_threshold"]
        stop = stop or not out[i]["sig_holm"]
    return out


def holm_fit(X, y, n, g, terms):
    r0 = fit(X, y, n, g, terms)
    return r0, summarize(r0, [t for t in terms if t.startswith("topic_")], r0["phi_pearson"])


if __name__ == "__main__":
    tcols = [f"topic_{t}" for t in TOPICS]

    # ---- T1 ----
    v = load_table(f"04_analysis/{SPLIT}/m1_input")
    t1_terms = M1_TERMS + tcols
    t1_fit, t1 = holm_fit(v[t1_terms].values, v.clicks, v.impressions, v.clickability_test_id, t1_terms)
    g = v.groupby("clickability_test_id")
    for r in t1:
        r["tests_varying"] = int(g[f"topic_{r['topic']}"].nunique().gt(1).sum())

    # MH check for the largest T1 effect
    top = max(t1, key=lambda r: abs(r["z"]))
    col = f"topic_{top['topic']}"
    num = den = 0.0
    for _, d in v.groupby("clickability_test_id"):
        if d[col].nunique() < 2:
            continue
        a = d.loc[d[col] == 1, "clicks"].sum(); b = d.loc[d[col] == 1, "impressions"].sum() - a
        c = d.loc[d[col] == 0, "clicks"].sum(); e = d.loc[d[col] == 0, "impressions"].sum() - c
        tot = a + b + c + e; num += a * e / tot; den += b * c / tot
    mh = float(100 * (num / den - 1))

    # ---- T2 ----
    pk = load_table("02_clean/packages", split=SPLIT)
    tests = load_table("02_clean/tests", split=SPLIT)
    units = load_table("03_features/units", split=SPLIT)
    labels = load_table("03_features/headline_labels", split=SPLIT)
    pk = pk.merge(units[["row_id", "unit_key"]], on="row_id", validate="1:1").merge(labels[["unit_key"] + tcols], on="unit_key", validate="m:1")
    use = tests[tests.usable_causal.astype(bool)][["clickability_test_id", "start", "impressions", "clicks"]]
    share = pk[pk.clickability_test_id.isin(use.clickability_test_id)].groupby("clickability_test_id")[tcols].mean()
    st = use.set_index("clickability_test_id").join((share >= 0.5).astype(int), how="inner")
    st["month"] = st.start.dt.strftime("%Y-%m"); st["year"] = st.start.dt.year.astype(str)
    t2_fit, t2 = holm_fit(st[tcols].values, st.clicks, st.impressions, st.month, tcols)
    t2y_fit, t2y = holm_fit(st[tcols].values, st.clicks, st.impressions, st.year, tcols)
    for r in t2:
        r["stories"] = int(st[f"topic_{r['topic']}"].sum())

    res = {"T1": {"phi": t1_fit["phi_pearson"], "tests": t1_fit["n_groups"], "rows": t1,
                  "mh_check": {"topic": top["topic"], "mh_pct": mh, "model_pct": top["pct"]}},
           "T2": {"phi": t2_fit["phi_pearson"], "stories": len(st), "months": t2_fit["n_groups"], "rows": t2,
                  "year_fe": [{"topic": r["topic"], "pct": r["pct"], "p": r["p"], "sig_holm": r["sig_holm"]} for r in t2y],
                  "phi_year": t2y_fit["phi_pearson"]}}
    json.dump(res, open(os.path.join(BUILD, "04_analysis", SPLIT, "topic_results.json"), "w"), indent=1, default=float)

    fp = lambda p: "< 0.001" if p < 0.001 else f"{p:.3f}"  # noqa: E731
    L = [f"# Which topics get more clicks ({SPLIT})", "",
         "Generated by `pipeline/04_analysis/topic_effects.py`. Method: NOTES §8.3 (approved 2026-11-10, R21). Data: Upworthy "
         f"Research Archive, {SPLIT} split (Matias et al., CC BY 4.0). Significance: quasi-binomial with φ from each model "
         "(R20); Holm correction across the 12 topics.", "",
         f"## T1: framing a headline around a topic (causal; {res['T1']['tests']:,} tests, φ = {res['T1']['phi']:.2f})", "",
         "Each row compares headlines carrying the tag with other headlines for the same story, holding gender and sentiment fixed.", "",
         "| Topic tag | Change in click rate | 95% interval | p | Holm | Tests where the tag varies |", "|---|---|---|---|---|---|"]
    for r in sorted(t1, key=lambda r: -r["pct"]):
        L.append(f"| {NAMES[r['topic']]} | **{r['pct']:+.1f}%** | {r['lo']:+.1f}% to {r['hi']:+.1f}% | {fp(r['p'])} | "
                 f"{'significant' if r['sig_holm'] else 'no'} | {r['tests_varying']} |")
    L += ["", f"Check: Mantel–Haenszel estimate for the largest effect ({NAMES[top['topic']]}): {mh:+.1f}% (model {top['pct']:+.1f}%).", "",
          f"## T2: stories about a topic (descriptive, not causal; {len(st):,} stories, month fixed effects, φ = {res['T2']['phi']:.2f})", "",
          "Topics differ in how they were promoted, their traffic sources, timing and story quality, so these are associations only.", "",
          "| Story topic | Stories | Change in click rate | 95% interval | p | Holm | With year instead of month |", "|---|---|---|---|---|---|---|"]
    yr = {r["topic"]: r for r in t2y}
    for r in sorted(t2, key=lambda r: -r["pct"]):
        y = yr[r["topic"]]
        L.append(f"| {NAMES[r['topic']]} | {r['stories']:,} | **{r['pct']:+.1f}%** | {r['lo']:+.1f}% to {r['hi']:+.1f}% | {fp(r['p'])} | "
                 f"{'significant' if r['sig_holm'] else 'no'} | {y['pct']:+.1f}% ({'significant' if y['sig_holm'] else 'no'}) |")
    open(os.path.join(DOCS, "results", SPLIT, "topic_effects.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
