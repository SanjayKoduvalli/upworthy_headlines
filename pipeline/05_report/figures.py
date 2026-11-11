"""Case-study figures, drawn with matplotlib from the result files (R23, R24: no number typed by hand).

Reads build/04_analysis/{confirmatory,exploratory}/*.json; writes assets/figures/*.svg. Every mark carries an id
(gid) and a tooltip text, which build_case_study.py turns into an SVG <title> so the inline chart shows the exact
value on hover; each figure also gets a data table on the page.
Colors (validated with the dataviz palette checker against white): purple #4B3AA8 = causal / confirmatory,
orange #C2671B = descriptive; gray = not significant (always labeled, and in the table).
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.join(ROOT, "build", "04_analysis")
OUT = os.path.join(ROOT, "assets", "figures")
os.makedirs(OUT, exist_ok=True)

PURPLE, ORANGE, GRAY = "#4B3AA8", "#C2671B", "#9A95AB"
INK, MUTED, GRID = "#1E1B2E", "#4A4560", "#E4E1EE"
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Plus Jakarta Sans", "DejaVu Sans"], "svg.fonttype": "none",
    "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "x", "grid.color": GRID, "grid.linewidth": 1, "axes.axisbelow": True,
    "xtick.major.size": 0, "ytick.major.size": 0, "figure.facecolor": "white", "axes.facecolor": "white",
})
TIPS = {}   # figure -> {gid: tooltip}


def load(split, name):
    return json.load(open(os.path.join(RES, split, name)))


def ci_from_phi(z_raw, pct, phi):
    """Main method (R20): interval with the model's own phi."""
    b = np.log1p(pct / 100); se = abs(b / (z_raw / np.sqrt(phi)))
    return 100 * (np.exp(b - 1.96 * se) - 1), 100 * (np.exp(b + 1.96 * se) - 1), 2 * (1 - __import__("scipy").stats.norm.cdf(abs(z_raw / np.sqrt(phi))))


def dot_row(ax, fig_id, y, est, lo, hi, color, label, tip, hollow=False, size=9):
    gid = f"{fig_id}-{len(TIPS.setdefault(fig_id, {}))}"
    TIPS[fig_id][gid] = tip
    if lo is not None:
        ax.plot([lo, hi], [y, y], color=color, lw=2, solid_capstyle="round", zorder=2, gid=gid + "-ci")
    ax.plot([est], [y], "o", ms=size, mfc="white" if hollow else color, mec=color if hollow else "white",
            mew=2, zorder=3, gid=gid)


def save(fig, name):
    fig.savefig(os.path.join(OUT, f"{name}.svg"), bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


# ---------------------------------------------------------------- F1: who is in the headline, and its tone
mc, me = load("confirmatory", "main_results.json"), load("exploratory", "main_results.json")
PHI_C, PHI_E = mc["phi_model_pearson"], me["phi_model_pearson"]
rowsC = {r["term"]: r for r in mc["M1"]}; rowsE = {r["term"]: r for r in me["M1"]}
rowsC["fvm"] = dict(mc["female_vs_male"], term="fvm"); rowsE["fvm"] = dict(me["female_vs_male"], term="fvm")
items = [("female", "A woman"), ("male", "A man"), ("both", "Both a woman and a man"), ("fvm", "A woman, compared with a man"),
         None, ("negative", "Negative tone"), ("positive", "Positive tone")]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
labels, ys = [], []
y = 0
for it in items:
    if it is None:
        y -= 0.6; continue
    term, lab = it
    c, e = rowsC[term], rowsE[term]
    lo, hi, p = ci_from_phi(c["z_raw"], c["pct"], PHI_C)
    sig = p < 0.05 and (term == "fvm" and abs(c["z_raw"]) > mc["crit_b_raw_z"]["female"] or term != "fvm" and c.get("sig_b", False))
    col = PURPLE if sig else GRAY
    dot_row(ax, "f1", y, c["pct"], lo, hi, col, lab, f"{lab}: {c['pct']:+.1f}% (95% interval {lo:+.1f}% to {hi:+.1f}%), confirmatory")
    elo, ehi, _ = ci_from_phi(e["z_raw"], e["pct"], PHI_E)
    dot_row(ax, "f1", y - 0.28, e["pct"], None, None, col, lab, f"{lab}: {e['pct']:+.1f}%, exploratory (replication)", hollow=True, size=7)
    ax.annotate(f"{c['pct']:+.1f}%", (hi, y), xytext=(8, 0), textcoords="offset points", va="center", color=INK, fontsize=11, fontweight="bold")
    labels.append(lab); ys.append(y - 0.1)
    y -= 1
ax.axvline(0, color=MUTED, lw=1, zorder=1)
ax.set_yticks(ys); ax.set_yticklabels(labels)
ax.set_xlabel("Change in click rate vs. a headline with no gendered person (tone: vs. neutral)")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: "0%" if abs(v) < 1e-9 else f"{v:+.0f}%"))
ax.set_xlim(-6, 28)
ax.text(-6, ys[0] + 0.75, "WHO THE HEADLINE CENTERS", fontsize=10, fontweight="bold", color=MUTED)
ax.text(-6, ys[4] + 0.7, "TONE", fontsize=10, fontweight="bold", color=MUTED)
h1, = ax.plot([], [], "o", ms=9, mfc=PURPLE, mec="white", mew=2, label="Confirmatory (95% interval)")
h2, = ax.plot([], [], "o", ms=7, mfc="white", mec=PURPLE, mew=2, label="Exploratory (replication)")
h3, = ax.plot([], [], "o", ms=9, mfc=GRAY, mec="white", mew=2, label="Not significant")
ax.legend(handles=[h1, h2, h3], loc="lower right", frameon=False, fontsize=10)
save(fig, "f1_gender_tone")

# ---------------------------------------------------------------- F2: the A/A check
ac, cc = load("confirmatory", "aa_results.json"), load("confirmatory", "calibration.json")
fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.4), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.45})
shares = np.array(ac["AA3"]["share_per_tenth"]) * 100
x = np.arange(10)
for i, v in enumerate(shares):
    gid = f"f2-{i}"; TIPS.setdefault("f2", {})[gid] = f"p-values from {i / 10:.1f} to {(i + 1) / 10:.1f}: {v:.1f}% of identical-version tests"
    a1.bar(i, v, width=0.72, color=PURPLE if i == 0 else "#B9B2DE", gid=gid)
a1.axhline(10, color=INK, lw=1, ls=(0, (4, 3)))
a1.text(9.4, 11, "10% expected\nif the test were sound", ha="right", va="bottom", fontsize=9, color=INK)
a1.set_xticks(x); a1.set_xticklabels([f"{i / 10:.1f}" for i in x], fontsize=9)
a1.set_xlabel("p-value of the identical-version test"); a1.grid(axis="y"); a1.grid(axis="x", visible=False)
a1.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
a1.tick_params(axis="y", colors=MUTED)
a1.set_title(f"{ac['AA1']['tests']:,} tests where every version was identical", fontsize=10, color=MUTED, loc="left")
fp_before = 100 * ac["AA2"]["rate"]
fp_after = 100 * np.mean([cc["split_half"]["fp_on_b_using_phi_a"], cc["split_half"]["fp_on_a_using_phi_b"]])
for i, (lab, v) in enumerate([("Standard test", fp_before), ("Calibrated\n(held-out)", fp_after)]):
    gid = f"f2-b{i}"; TIPS["f2"][gid] = f"{lab.replace(chr(10), ' ')}: {v:.1f}% of identical-version tests called significant"
    a2.bar(i, v, width=0.5, color=GRAY if i == 0 else PURPLE, gid=gid)
    a2.text(i, v + 0.8, f"{v:.1f}%", ha="center", fontsize=11, fontweight="bold", color=INK)
a2.axhline(5, color=INK, lw=1, ls=(0, (4, 3)))
a2.set_xticks([0, 1]); a2.set_xticklabels(["Standard test", "Calibrated\n(held-out)"], fontsize=9.5)
a2.grid(axis="y"); a2.grid(axis="x", visible=False); a2.set_ylim(0, max(fp_before * 1.18, 10))
a2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%")); a2.tick_params(axis="y", colors=MUTED)
a2.set_title("False alarms (dashed line: 5% target)", fontsize=10, color=MUTED, loc="left")
save(fig, "f2_aa_check")

# ---------------------------------------------------------------- F3: topic framing (T1)
tc, te = load("confirmatory", "topic_results.json"), load("exploratory", "topic_results.json")
NAMES = {"POL": "Politics & world affairs", "RAC": "Race, religion & immigration", "GEN": "Gender equality & LGBTQ+",
         "HEA": "Health & medicine", "ECO": "Economy, work & inequality", "EDU": "Education", "FAM": "Children & family",
         "ENV": "Environment & climate", "CRI": "Crime, police & justice", "SCI": "Science & technology",
         "ENT": "Entertainment & media", "HUM": "Human interest & kindness"}
T1c = sorted(tc["T1"]["rows"], key=lambda r: r["pct"]); T1e = {r["topic"]: r for r in te["T1"]["rows"]}
fig, ax = plt.subplots(figsize=(8.2, 5.2))
for i, r in enumerate(T1c):
    col = PURPLE if r["sig_holm"] else GRAY
    dot_row(ax, "f3", i, r["pct"], r["lo"], r["hi"], col, NAMES[r["topic"]],
            f"{NAMES[r['topic']]}: {r['pct']:+.1f}% ({r['lo']:+.1f}% to {r['hi']:+.1f}%), confirmatory" + ("" if r["sig_holm"] else ", not significant"))
    e = T1e[r["topic"]]
    dot_row(ax, "f3", i - 0.3, e["pct"], None, None, col, "", f"{NAMES[r['topic']]}: {e['pct']:+.1f}%, exploratory", hollow=True, size=6)
ax.axvline(0, color=MUTED, lw=1, zorder=1)
ax.set_yticks(range(len(T1c))); ax.set_yticklabels([NAMES[r["topic"]] for r in T1c])
ax.set_xlabel("Change in click rate: headline framed around the topic vs. other headlines for the same story")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: "0%" if abs(v) < 1e-9 else f"{v:+.0f}%"))
h1, = ax.plot([], [], "o", ms=9, mfc=PURPLE, mec="white", mew=2, label="Significant (Holm-corrected)")
h2, = ax.plot([], [], "o", ms=9, mfc=GRAY, mec="white", mew=2, label="Not significant")
h3, = ax.plot([], [], "o", ms=6, mfc="white", mec=MUTED, mew=2, label="Exploratory estimate")
ax.legend(handles=[h1, h2, h3], loc="upper left", frameon=False, fontsize=10)
save(fig, "f3_topic_framing")

# ---------------------------------------------------------------- F4: framing (causal) vs. story topic (descriptive)
T2c = {r["topic"]: r for r in tc["T2"]["rows"]}
order = sorted(T2c, key=lambda t: T2c[t]["pct"])
fig, ax = plt.subplots(figsize=(8.2, 5.2))
T1map = {r["topic"]: r for r in T1c}
for i, t in enumerate(order):
    d, c = T2c[t], T1map[t]
    close = abs(c["pct"] - d["pct"]) < 1.5          # nearly equal: nudge apart vertically so both dots show
    yo, yc = (i + 0.14, i - 0.14) if close else (i, i)
    ax.plot([d["pct"], c["pct"]], [yo, yc], color=GRID, lw=2, zorder=1)
    dot_row(ax, "f4", yo, d["pct"], None, None, ORANGE, "", f"{NAMES[t]}: stories about it {d['pct']:+.1f}% (descriptive)")
    dot_row(ax, "f4", yc, c["pct"], None, None, PURPLE, "", f"{NAMES[t]}: headline framed around it {c['pct']:+.1f}% (causal)")
ax.axvline(0, color=MUTED, lw=1, zorder=1)
ax.set_yticks(range(len(order))); ax.set_yticklabels([NAMES[t] for t in order])
ax.set_xlabel("Change in click rate")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: "0%" if abs(v) < 1e-9 else f"{v:+.0f}%"))
h1, = ax.plot([], [], "o", ms=9, mfc=ORANGE, mec="white", mew=2, label="Stories about the topic, across stories (descriptive)")
h2, = ax.plot([], [], "o", ms=9, mfc=PURPLE, mec="white", mew=2, label="Headline framed around it, same story (causal)")
ax.legend(handles=[h1, h2], loc="lower left", bbox_to_anchor=(-0.02, 1.0), ncol=1, frameon=False, fontsize=10)
save(fig, "f4_framing_vs_story")

json.dump(TIPS, open(os.path.join(OUT, "tooltips.json"), "w"), indent=1)
print("figures:", sorted(os.listdir(OUT)))
