"""Main analysis M1, M2, S1, S2 and the placebo threshold M1-b (NOTES §8.2, approved by Sanjay 2026-11-10 23:42).

Exploratory only (R2). Within-test design: one row per variant (S5: identical versions summed), test fixed effects,
quasi-binomial significance with phi from the A/A tests (AA6), plus the placebo critical value from A/A tests (b).
Writes build/04_analysis/m1_input (also read by the statsmodels check on Sanjay's Mac), main_results.json and
docs/results/main_effects.md.
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from common import BUILD, DOCS, SPLIT, load_table, save_table  # noqa: E402
from felogit import contrast, fit, pct_change  # noqa: E402

SEED, N_PLACEBO, MIN_TESTS = 20261110, 1000, 30
CAL = json.load(open(os.path.join(BUILD, "04_analysis", SPLIT, "calibration.json")))
PHI = CAL["phi"]
TOPICS = ["POL", "RAC", "GEN", "HEA", "ECO", "EDU", "FAM", "ENV", "CRI", "SCI", "ENT", "HUM"]
M1_TERMS = ["female", "male", "both", "positive", "negative"]


def variant_table():
    pk = load_table("02_clean/packages", split=SPLIT)
    tests = load_table("02_clean/tests", split=SPLIT)
    units = load_table("03_features/units", split=SPLIT)
    labels = load_table("03_features/headline_labels", split=SPLIT)
    labels = labels[labels.split == SPLIT]   # a text can appear in both splits; use this split's label row
    pk = pk.merge(units[["row_id", "unit_key"]], on="row_id", how="left", validate="1:1")
    pk = pk.merge(labels.drop(columns="split"), on="unit_key", how="left", validate="m:1")
    keep = tests[tests.usable_causal.astype(bool) & tests.varies_headline.astype(bool)][["clickability_test_id", "varies"]]
    pk = pk.merge(keep, on="clickability_test_id", how="inner")
    assert pk.gender.notna().all(), "a package has no label"
    lab_cols = ["gender", "sentiment"] + [f"topic_{t}" for t in TOPICS]
    per_variant = pk.groupby("variant_id")[lab_cols].nunique()
    assert (per_variant <= 1).all().all(), "a variant has more than one label (S5 says variants are identical)"
    v = pk.groupby(["clickability_test_id", "variant_id"], as_index=False).agg(
        impressions=("impressions", "sum"), clicks=("clicks", "sum"), varies=("varies", "first"),
        **{c: (c, "first") for c in lab_cols})
    v["split"] = SPLIT
    for gname in ("female", "male", "both"):
        v[gname] = (v.gender == gname).astype(int)
    for s in ("positive", "negative"):
        v[s] = (v.sentiment == s).astype(int)
    return v


def table(res, terms):
    out = []
    for t in terms:
        i = res["names"].index(t)
        b, se = res["beta"][i], res["se"][i]
        out.append({"term": t, "beta": float(b), "pct": float(pct_change(b)), "lo": float(pct_change(b - 1.96 * se)),
                    "hi": float(pct_change(b + 1.96 * se)), "p_a": float(res["p"][i]), "z_raw": float(res["z_raw"][i])})
    return out


def has_variation(df, col):
    return df.groupby("clickability_test_id")[col].nunique().gt(1).any()


if __name__ == "__main__":
    v = variant_table()
    save_table(v, f"04_analysis/{SPLIT}/m1_input")
    tests_with = lambda col: int(v.groupby("clickability_test_id")[col].nunique().gt(1).sum())  # noqa: E731

    # ---- M1 ----
    m1 = fit(v[M1_TERMS].values, v.clicks, v.impressions, v.clickability_test_id, M1_TERMS, phi=PHI)
    d_fm, se_fm, p_fm = contrast(m1, "female", "male")

    # ---- M1-b placebo on the A/A tests ----
    pk = load_table("02_clean/packages", split=SPLIT)
    aa = pk[pk.is_aa_test.astype(bool) & pk.usable_causal.astype(bool)]
    rng = np.random.default_rng(SEED)
    g_share = v.gender.value_counts(normalize=True); s_share = v.sentiment.value_counts(normalize=True)
    zs = []
    for _ in range(N_PLACEBO):
        fg = rng.choice(g_share.index, size=len(aa), p=g_share.values)
        fs = rng.choice(s_share.index, size=len(aa), p=s_share.values)
        Xf = np.column_stack([fg == "female", fg == "male", fg == "both", fs == "positive", fs == "negative"]).astype(float)
        try:
            zs.append(fit(Xf, aa.clicks, aa.impressions, aa.clickability_test_id, M1_TERMS)["z_raw"])
        except ValueError:
            continue
    zs = np.abs(np.array(zs))
    crit_b = {t: float(np.quantile(zs[:, j], 0.975)) for j, t in enumerate(M1_TERMS)}
    crit_a = float(1.959963984540054 * np.sqrt(PHI))

    rows = table(m1, M1_TERMS)
    for r in rows:
        r["sig_a"] = r["p_a"] < 0.05
        r["crit_b"] = crit_b[r["term"]]
        r["sig_b"] = abs(r["z_raw"]) > crit_b[r["term"]]
        r["robust"] = r["sig_a"] and r["sig_b"]
        r["tests_varying"] = tests_with(r["term"])

    # ---- S1, S2 ----
    ho = v[v.varies == "headline only"]
    s1 = fit(ho[M1_TERMS].values, ho.clicks, ho.impressions, ho.clickability_test_id, M1_TERMS, phi=PHI)
    v2 = v.assign(female=((v.gender == "female") | (v.gender == "both")).astype(int))
    s2a = fit(v2[["female", "male", "positive", "negative"]].values, v2.clicks, v2.impressions,
              v2.clickability_test_id, ["female", "male", "positive", "negative"], phi=PHI)
    v3 = v[v.sentiment != "neutral"]
    s2b = fit(v3[["female", "male", "both", "positive"]].values, v3.clicks, v3.impressions, v3.clickability_test_id,
              ["female", "male", "both", "positive"], phi=PHI)

    # ---- M2: female x topic ----
    informative = {}
    fem_varies = v.groupby("clickability_test_id").female.nunique().gt(1)
    for t in TOPICS:
        has_t = v.groupby("clickability_test_id")[f"topic_{t}"].max().astype(bool)
        informative[t] = int((fem_varies & has_t).sum())
    use_topics = [t for t in TOPICS if informative[t] >= MIN_TESTS]
    v4 = v.copy()
    terms2 = list(M1_TERMS)
    for t in use_topics:
        v4[f"female_x_{t}"] = v4.female * v4[f"topic_{t}"]
        terms2.append(f"female_x_{t}")
        if has_variation(v4, f"topic_{t}"):
            terms2.append(f"topic_{t}")
    m2 = fit(v4[terms2].values, v4.clicks, v4.impressions, v4.clickability_test_id, terms2, phi=PHI)
    inter = table(m2, [f"female_x_{t}" for t in use_topics])
    # Holm: sort p ascending, compare p_(i) with alpha / (m - i + 1), stop at first failure
    order = np.argsort([r["p_a"] for r in inter]); m = len(inter); stop = False
    for rank, i in enumerate(order):
        thr = 0.05 / (m - rank)
        inter[i]["holm_threshold"] = thr
        inter[i]["sig_holm"] = (not stop) and inter[i]["p_a"] < thr
        stop = stop or not inter[i]["sig_holm"]
    for r in inter:
        r["topic"] = r["term"].split("_x_")[1]; r["informative_tests"] = informative[r["topic"]]
        # female effect within this topic = female main + interaction
        i, j = m2["names"].index("female"), m2["names"].index(r["term"])
        b = m2["beta"][i] + m2["beta"][j]
        se = np.sqrt(m2["cov"][i, i] + m2["cov"][j, j] + 2 * m2["cov"][i, j])
        r["female_effect_in_topic_pct"] = float(pct_change(b))
        r["female_effect_in_topic_lo"] = float(pct_change(b - 1.96 * se)); r["female_effect_in_topic_hi"] = float(pct_change(b + 1.96 * se))

    res = {
        "data": {"tests": int(v.clickability_test_id.nunique()), "variants": len(v), "rows_used": m1["n_rows"],
                 "tests_used": m1["n_groups"], "dropped_zero_click_tests": m1["dropped_zero_click_groups"],
                 "gender_shares": v.gender.value_counts(normalize=True).round(4).to_dict(),
                 "sentiment_shares": v.sentiment.value_counts(normalize=True).round(4).to_dict()},
        "phi_aa": PHI, "phi_model_pearson": m1["phi_pearson"], "crit_a_raw_z": crit_a, "crit_b_raw_z": crit_b,
        "n_placebo_fits": int(len(zs)),
        "M1": rows, "female_vs_male": {"pct": float(pct_change(d_fm)), "lo": float(pct_change(d_fm - 1.96 * se_fm)),
                                       "hi": float(pct_change(d_fm + 1.96 * se_fm)), "p_a": float(p_fm),
                                       "z_raw": float(d_fm / (se_fm / np.sqrt(PHI)))},
        "S1_headline_only": {"tests": s1["n_groups"], "rows": table(s1, M1_TERMS)},
        "S2_both_as_female": table(s2a, ["female", "male", "positive", "negative"]),
        "S2_no_neutral": table(s2b, ["female", "male", "both", "positive"]),
        "M2": {"informative_tests": informative, "estimated": use_topics, "interactions": inter},
    }
    json.dump(res, open(os.path.join(BUILD, "04_analysis", SPLIT, "main_results.json"), "w"), indent=1, default=float)
    print(json.dumps({k: res[k] for k in ("data", "phi_model_pearson", "crit_a_raw_z", "crit_b_raw_z", "M1", "female_vs_male")}, indent=1, default=float))
    print("S1", [(r["term"], round(r["pct"], 1), round(r["p_a"], 3)) for r in res["S1_headline_only"]["rows"]])
    print("S2a", [(r["term"], round(r["pct"], 1), round(r["p_a"], 3)) for r in res["S2_both_as_female"]])
    print("S2b", [(r["term"], round(r["pct"], 1), round(r["p_a"], 3)) for r in res["S2_no_neutral"]])
    print("M2 informative", informative)
    for r in inter:
        print("M2", r["topic"], r["informative_tests"], round(r["pct"], 1), round(r["p_a"], 4), r["sig_holm"],
              "female in topic", round(r["female_effect_in_topic_pct"], 1), (round(r["female_effect_in_topic_lo"], 1), round(r["female_effect_in_topic_hi"], 1)))

    # ---- report ----
    PM = res["phi_model_pearson"]

    def with_phi(z_raw, pct, phi):
        z = z_raw / np.sqrt(phi); b = np.log1p(pct / 100); se = abs(b / z) if z else float("nan")
        return 2 * stats.norm.sf(abs(z)), pct_change(b - 1.96 * se), pct_change(b + 1.96 * se)

    def fmt_p(p):
        return "< 0.001" if p < 0.001 else f"{p:.3f}"

    label = {"female": "Centers a woman (vs. no gendered person)", "male": "Centers a man (vs. none)",
             "both": "Centers both (vs. none)", "positive": "Positive (vs. neutral)", "negative": "Negative (vs. neutral)"}
    lines = [f"# Main analysis: headline effects within tests ({SPLIT})", "",
             "Generated by `pipeline/04_analysis/main_effects.py`. Method: NOTES §8.2 (approved 2026-11-10). Data: Upworthy "
             f"Research Archive, {SPLIT} split (Matias et al., CC BY 4.0). Causal: every comparison is between versions "
             "of the same story shown to randomly split readers.", "",
             f"**Data:** {res['data']['tests']:,} usable tests where the headline varies, {res['data']['variants']:,} headline versions.", "",
             "## M1: effect on click rate", "",
             f"**Main method (R20): column (c), quasi-binomial with φ = {PM:.2f} estimated from the model itself.** Also reported: "
             f"(a) φ = {PHI:.2f} from the A/A tests; (b) placebo threshold from {res['n_placebo_fits']} fake-label fits on the A/A tests. "
             "A result is called robust only if it holds under (c) and (b).", "",
             "| Headline feature | Change in click rate | 95% interval (a) | p (a) | Passes (b) | 95% interval (c) | p (c) | Tests where it varies |",
             "|---|---|---|---|---|---|---|---|"]
    for r in res["M1"]:
        pc, lc, hc = with_phi(r["z_raw"], r["pct"], PM)
        lines.append(f"| {label[r['term']]} | **{r['pct']:+.1f}%** | {r['lo']:+.1f}% to {r['hi']:+.1f}% | {fmt_p(r['p_a'])} | "
                     f"{'yes' if r['sig_b'] else 'no'} | {lc:+.1f}% to {hc:+.1f}% | {fmt_p(pc)} | {r['tests_varying']} |")
    fm = res["female_vs_male"]; pc, lc, hc = with_phi(fm["z_raw"], fm["pct"], PM)
    lines.append(f"| **Woman vs. man** (contrast) | **{fm['pct']:+.1f}%** | {fm['lo']:+.1f}% to {fm['hi']:+.1f}% | {fmt_p(fm['p_a'])} | "
                 f"{'yes' if abs(fm['z_raw']) > res['crit_b_raw_z']['female'] else 'no'} | {lc:+.1f}% to {hc:+.1f}% | {fmt_p(pc)} | |")
    lines += ["", "## Sensitivity (estimates; significance (a))", "", "| Model | Woman | Man | Both | Positive | Negative |", "|---|---|---|---|---|---|"]
    def cell(rows, t):
        x = next((r for r in rows if r["term"] == t), None)
        return "—" if x is None else f"{x['pct']:+.1f}% (p {fmt_p(x['p_a'])})"
    for name, rows_ in [("M1, all headline tests", res["M1"]), (f"S1, headline-only tests ({res['S1_headline_only']['tests']:,})", res["S1_headline_only"]["rows"]),
                        ("S2, 'both' counted as woman", res["S2_both_as_female"]), ("S2, neutral dropped (positive vs. negative)", res["S2_no_neutral"])]:
        lines.append(f"| {name} | " + " | ".join(cell(rows_, t) for t in ("female", "male", "both", "positive", "negative")) + " |")
    lines += ["", "## M2: does the woman effect differ by topic?", "",
              f"Interaction terms, Holm-corrected across the {len(res['M2']['estimated'])} topics with at least {MIN_TESTS} informative tests "
              f"(too few to say: {', '.join(t for t in TOPICS if t not in res['M2']['estimated']) or 'none'}).", "",
              "| Topic | Informative tests | Woman effect in this topic | Difference from other topics | p (a) | Holm (a) | p (c) |", "|---|---|---|---|---|---|---|"]
    for r in sorted(res["M2"]["interactions"], key=lambda r: r["p_a"]):
        pc, _, _ = with_phi(r["z_raw"], r["pct"], PM)
        lines.append(f"| {r['topic']} | {r['informative_tests']} | {r['female_effect_in_topic_pct']:+.1f}% ({r['female_effect_in_topic_lo']:+.1f} to {r['female_effect_in_topic_hi']:+.1f}) | "
                     f"{r['pct']:+.1f}% | {fmt_p(r['p_a'])} | {'significant' if r['sig_holm'] else 'no'} | {fmt_p(pc)} |")
    lines += ["", f"**Note on φ:** the model's own dispersion is {PM:.2f}, about twice the A/A value ({PHI:.2f}). A/A tests measure "
              "pure noise; real A/B tests also contain genuine differences between headlines that our labels don't capture. "
              "Column (c) treats that extra variation as uncertainty too, the more cautious reading; Sanjay chose it as the "
              "main method on 2026-11-10 (R20), because the claims are about headlines in general."]
    open(os.path.join(DOCS, "results", SPLIT, "main_effects.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
