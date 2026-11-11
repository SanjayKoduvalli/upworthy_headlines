"""Step 2: profile the raw Upworthy archive files (checks P1–P15, approved 2026-11-04; NOTES §3.1).

Run from the project root:  python3 pipeline/00_profile/profile.py
Writes docs/data_profile.md (human-readable) and build/profile_results.json (every number, for the checks).
Reads the raw files only; changes nothing. Profiling is about data QUALITY: nothing here compares click
rates by headline content, and the gender preview (P13) reads the exploratory split only (NOTES §2).
"""
import json
import os
import re
import csv
import sys
from collections import Counter

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw", "osf_jd64p")
DS = os.path.join(RAW, "upworthy-archive-datasets")
GA = os.path.join(RAW, "google-analytics-data")
SPLITS = {
    "exploratory": "upworthy-archive-exploratory-packages-03.12.2020.csv",
    "confirmatory": "upworthy-archive-confirmatory-packages-03.12.2020.csv",
    "holdout": "upworthy-archive-holdout-packages-03.12.2020.csv",
}
UNDEPLOYED = "upworthy-archive-undeployed-packages.01.12.2021.csv"
# Published figures (Matias et al. 2021, Scientific Data), for P4
PUBLISHED = {"exploratory": (4873, 22666), "confirmatory": (22743, 105551), "holdout": (4871, 22600)}
PROBLEM_START, PROBLEM_END = pd.Timestamp("2013-06-25"), pd.Timestamp("2014-01-10 23:59:59")  # 2024 update
P10_ALPHA = 0.001          # approved cutoff
P10_MIN_EXPECTED = 5       # chi-square needs expected count >= 5 per arm
CONTENT = ["headline", "eyecatcher_id", "excerpt", "lede"]   # P3c: same package content
# P13 rough draft word list, for feasibility counts only (NOT the final classifier; NOTES §3.1)
FEMALE = ["woman", "women", "she", "her", "hers", "herself", "girl", "girls", "mom", "moms", "mother",
          "mothers", "daughter", "daughters", "wife", "wives", "sister", "sisters", "lady", "ladies"]
MALE = ["man", "men", "he", "him", "his", "himself", "boy", "boys", "dad", "dads", "father", "fathers",
        "son", "sons", "husband", "husbands", "brother", "brothers", "guy", "guys"]

R = {}          # every result, keyed by check id
md = []         # report lines


def read(path):
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")


def csv_count(path):
    """P1 independent count with the standard-library csv module (handles quoted line breaks)."""
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        next(rdr)
        return sum(1 for _ in rdr)


def word_re(words):
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.IGNORECASE)


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def fmt(x, d=0):
    if isinstance(x, float) and not x.is_integer() or d:
        return f"{x:,.{d or 2}f}"
    return f"{int(x):,}"


# ---------------------------------------------------------------------------------------- load
raw = {s: read(os.path.join(DS, f)) for s, f in SPLITS.items()}
und = read(os.path.join(DS, UNDEPLOYED))
files = dict(raw, undeployed=und)

# ---------------------------------------------------------------------------------------- P1
R["P1"] = {s: {"pandas": len(df), "csv_module": csv_count(os.path.join(DS, SPLITS.get(s, UNDEPLOYED)))}
           for s, df in files.items()}
md += ["## P1. Row counts", ""] + table(["File", "pandas", "csv module", "Match"],
        [[s, fmt(v["pandas"]), fmt(v["csv_module"]), "✅" if v["pandas"] == v["csv_module"] else "❌"]
         for s, v in R["P1"].items()]) + [""]

# ---------------------------------------------------------------------------------------- P2
cols = {s: list(df.columns) for s, df in files.items()}
base = cols["exploratory"]
R["P2"] = {"columns": cols,
           "splits_identical": all(cols[s] == base for s in SPLITS),
           "undeployed_only": [c for c in cols["undeployed"] if c not in base],
           "undeployed_missing": [c for c in base if c not in cols["undeployed"]]}
types = {}
for c in base:
    v = raw["exploratory"][c]
    nonempty = v[v != ""]
    if nonempty.str.fullmatch(r"-?\d+").all():
        t = "integer"
    elif nonempty.str.fullmatch(r"-?\d+(\.\d+)?").all():
        t = "decimal"
    elif nonempty.isin(["True", "False"]).all():
        t = "boolean (True/False)"
    elif nonempty.str.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?").all():
        t = "timestamp"
    else:
        t = "text"
    types[c] = t
R["P2"]["inferred_types_exploratory"] = types
md += ["## P2. Columns and types", "",
       f"The three splits have identical columns: **{R['P2']['splits_identical']}**. "
       f"Undeployed adds {R['P2']['undeployed_only']} and lacks {R['P2']['undeployed_missing']}.", ""]
md += table(["Column", "Inferred type (exploratory)"], [[f"`{c or '(unnamed)'}`", t] for c, t in types.items()]) + [""]

# ---------------------------------------------------------------------------------------- P3
P3 = {}
for s, df in files.items():
    idc = "_id" if s == "undeployed" else base[0]
    P3[s] = {"id_column": idc or "(unnamed)", "id_unique": bool(df[idc].is_unique),
             "exact_duplicate_rows": int(df.drop(columns=[idc]).duplicated().sum()),
             "same_content_within_test": int(df.duplicated(["clickability_test_id"] + CONTENT).sum())}
allids = pd.concat([raw[s][base[0]] for s in SPLITS])
R["P3"] = {"by_file": P3, "unnamed_id_unique_across_splits": bool(allids.is_unique)}
md += ["## P3. Keys and duplicates", ""] + table(
    ["File", "Row id", "Id unique", "Exact duplicate rows (excl. id)", "Same content within a test"],
    [[s, f"`{v['id_column']}`", "✅" if v["id_unique"] else "❌", fmt(v["exact_duplicate_rows"]),
      fmt(v["same_content_within_test"])] for s, v in P3.items()]) + [
    "", f"Unnamed row id unique across all three splits: **{R['P3']['unnamed_id_unique_across_splits']}**.", ""]

# ---------------------------------------------------------------------------------------- P4
tests = {s: set(df["clickability_test_id"]) for s, df in raw.items()}
overlap = {f"{a}∩{b}": len(tests[a] & tests[b]) for a, b in
           [("exploratory", "confirmatory"), ("exploratory", "holdout"), ("confirmatory", "holdout")]}
R["P4"] = {"overlap": overlap,
           "counts": {s: {"tests": len(tests[s]), "packages": len(raw[s]),
                          "published_tests": PUBLISHED[s][0], "published_packages": PUBLISHED[s][1]} for s in SPLITS},
           "undeployed_tests_also_in_splits": len(set(und["clickability_test_id"]) & set().union(*tests.values()))}
md += ["## P4. Split integrity", "", "Tests shared between splits: " +
       ", ".join(f"{k} = {v}" for k, v in overlap.items()) + ".", ""]
md += table(["Split", "Tests", "Published", "Packages", "Published"],
            [[s, fmt(v["tests"]), fmt(v["published_tests"]), fmt(v["packages"]), fmt(v["published_packages"])]
             for s, v in R["P4"]["counts"].items()]) + [
    "", f"Undeployed packages whose test id also appears in a split: {fmt(R['P4']['undeployed_tests_also_in_splits'])}.", ""]

# ---------------------------------------------------------------------------------------- P5
R["P5"] = {s: {c: int((df[c].str.strip() == "").sum()) for c in df.columns if c} for s, df in files.items()}
md += ["## P5. Missing or empty values", ""] + table(
    ["Column"] + list(files), [[f"`{c}`"] + [fmt(R["P5"][s].get(c, 0)) if c in files[s].columns else "n/a" for s in files]
                               for c in cols["undeployed"] + [c for c in base if c and c not in cols["undeployed"]]]) + [""]

# ---------------------------------------------------------------------------------------- typed copies
typed = {}
for s, df in raw.items():
    t = df.copy()
    for c in ["impressions", "clicks", "test_week"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")
    # Timestamps come in two formats: with fractional seconds (most) and without (~4%). format="ISO8601"
    # parses both; a fixed format would silently turn the second kind into NaT (caught in profiling, NOTES §6).
    t["created_at"] = pd.to_datetime(t["created_at"], format="ISO8601", errors="coerce")
    t["updated_at"] = pd.to_datetime(t["updated_at"], format="ISO8601", errors="coerce")
    typed[s] = t

# ---------------------------------------------------------------------------------------- P6
P6 = {}
for s, t in typed.items():
    ctr = t["clicks"] / t["impressions"].where(t["impressions"] > 0)
    P6[s] = {"impressions_not_integer": int(t["impressions"].isna().sum() + (t["impressions"] % 1 != 0).sum()),
             "clicks_not_integer": int(t["clicks"].isna().sum() + (t["clicks"] % 1 != 0).sum()),
             "negative": int(((t["impressions"] < 0) | (t["clicks"] < 0)).sum()),
             "clicks_gt_impressions": int((t["clicks"] > t["impressions"]).sum()),
             "zero_impressions": int((t["impressions"] == 0).sum()),
             "zero_clicks": int((t["clicks"] == 0).sum()),
             "total_impressions": int(t["impressions"].sum()), "total_clicks": int(t["clicks"].sum()),
             "impressions_min_median_max": [int(t["impressions"].min()), float(t["impressions"].median()), int(t["impressions"].max())],
             "ctr_min_median_max_pct": [float(100 * ctr.min()), float(100 * ctr.median()), float(100 * ctr.max())]}
R["P6"] = P6
md += ["## P6. Ranges", ""] + table(
    ["Split", "Non-integer counts", "Negative", "Clicks > impressions", "0 impressions", "0 clicks",
     "Impressions min / median / max", "Click rate % min / median / max", "Total impressions", "Total clicks"],
    [[s, v["impressions_not_integer"] + v["clicks_not_integer"], v["negative"], v["clicks_gt_impressions"],
      fmt(v["zero_impressions"]), fmt(v["zero_clicks"]),
      " / ".join(fmt(x) if i != 1 else f"{x:,.0f}" for i, x in enumerate(v["impressions_min_median_max"])),
      " / ".join(f"{x:.2f}" for x in v["ctr_min_median_max_pct"]), fmt(v["total_impressions"]), fmt(v["total_clicks"])]
     for s, v in P6.items()]) + [""]

# ---------------------------------------------------------------------------------------- P7
P7 = {}
for s, t in typed.items():
    tw = t["test_week"].dropna().astype(int)
    P7[s] = {"created_min": str(t["created_at"].min()), "created_max": str(t["created_at"].max()),
             "created_unparsed": int(t["created_at"].isna().sum()),
             "created_without_fraction": int((~raw[s]["created_at"].str.contains(r"\.\d+$")).sum()),
             "test_week_min": int(tw.min()), "test_week_max": int(tw.max()), "test_week_distinct": int(tw.nunique()),
             "test_week_examples": sorted(tw.unique().tolist())[:5],
             "updated_min": str(t["updated_at"].min()), "updated_max": str(t["updated_at"].max()),
             "updated_before_2016": int((t["updated_at"] < "2016-01-01").sum()),
             "tests_spanning_multiple_weeks": int((t.groupby("clickability_test_id")["test_week"].nunique() > 1).sum())}
R["P7"] = P7
md += ["## P7. Dates", ""] + table(
    ["Split", "created_at min", "created_at max", "Unparsed", "Without fractional seconds", "test_week range (distinct)", "Example test_week values",
     "updated_at range", "updated_at before 2016", "Tests spanning >1 test_week"],
    [[s, v["created_min"][:19], v["created_max"][:19], fmt(v["created_unparsed"]), fmt(v["created_without_fraction"]), f"{v['test_week_min']}–{v['test_week_max']} ({v['test_week_distinct']})",
      v["test_week_examples"], f"{v['updated_min'][:10]} – {v['updated_max'][:10]}", fmt(v["updated_before_2016"]),
      fmt(v["tests_spanning_multiple_weeks"])] for s, v in P7.items()]) + [""]

# ---------------------------------------------------------------------------------------- P8
P8 = {}
for s, t in typed.items():
    g = t.groupby("clickability_test_id")
    n = g.size()
    imp = g["impressions"].sum()
    P8[s] = {"packages_per_test": {str(k): int(v) for k, v in n.value_counts().sort_index().items()},
             "single_package_tests": int((n == 1).sum()),
             "packages_min_median_max": [int(n.min()), float(n.median()), int(n.max())],
             "test_impressions_min_median_max": [int(imp.min()), float(imp.median()), int(imp.max())],
             "tests_under_1000_impressions": int((imp < 1000).sum())}
R["P8"] = P8
md += ["## P8. Test structure", ""] + table(
    ["Split", "Single-package tests", "Packages per test min / median / max", "Impressions per test min / median / max",
     "Tests < 1,000 impressions"],
    [[s, fmt(v["single_package_tests"]), " / ".join(f"{x:g}" for x in v["packages_min_median_max"]),
      " / ".join(f"{x:,.0f}" for x in v["test_impressions_min_median_max"]), fmt(v["tests_under_1000_impressions"])]
     for s, v in P8.items()]) + ["", "Packages per test (exploratory): " +
     ", ".join(f"{k}: {v:,}" for k, v in P8["exploratory"]["packages_per_test"].items()), ""]

# ---------------------------------------------------------------------------------------- P9
P9 = {}
for s, t in typed.items():
    g = t.groupby("clickability_test_id").agg(n=("headline", "size"), h=("headline", "nunique"),
                                               i=("eyecatcher_id", "nunique"))
    g = g[g.n > 1]
    kind = np.select([(g.h > 1) & (g.i > 1), g.h > 1, g.i > 1], ["both", "headline only", "image only"], "neither")
    P9[s] = {k: int(v) for k, v in pd.Series(kind).value_counts().items()}
R["P9"] = P9
md += ["## P9. What each test varies (tests with 2+ packages)", ""] + table(
    ["Split", "Headline only", "Image only", "Both", "Neither"],
    [[s, fmt(v.get("headline only", 0)), fmt(v.get("image only", 0)), fmt(v.get("both", 0)), fmt(v.get("neither", 0))]
     for s, v in P9.items()]) + [""]

# ---------------------------------------------------------------------------------------- P10
P10 = {}
srm_rows = {}
for s, t in typed.items():
    rows = []
    for tid, g in t.groupby("clickability_test_id"):
        k, tot = len(g), g["impressions"].sum()
        if k < 2:
            continue
        exp = tot / k
        start = g["created_at"].min()
        in_window = bool(PROBLEM_START <= start <= PROBLEM_END)
        if exp < P10_MIN_EXPECTED:
            rows.append((tid, k, int(tot), None, None, None, in_window, start))
            continue
        chi2, p = stats.chisquare(g["impressions"].to_numpy(dtype=float))
        max_share_ratio = float(g["impressions"].max() / exp)       # largest arm vs. its fair share
        rows.append((tid, k, int(tot), float(chi2), float(p), max_share_ratio, in_window, start))
    d = pd.DataFrame(rows, columns=["test", "arms", "impressions", "chi2", "p", "max_share_ratio", "in_window", "start"])
    tested = d[d.p.notna()]
    flag = tested.p < P10_ALPHA
    P10[s] = {"tests_2plus_arms": len(d), "too_small_to_test": int(d.p.isna().sum()), "tested": len(tested),
              "flagged": int(flag.sum()), "flagged_pct": float(100 * flag.mean()),
              "in_window": {"tested": int(tested.in_window.sum()), "flagged": int((flag & tested.in_window).sum())},
              "outside_window": {"tested": int((~tested.in_window).sum()), "flagged": int((flag & ~tested.in_window).sum())},
              "expected_false_flags_if_all_fair": float(P10_ALPHA * len(tested)),
              "flagged_max_share_ratio_median": float(tested[flag].max_share_ratio.median()) if flag.any() else None,
              "unflagged_max_share_ratio_median": float(tested[~flag].max_share_ratio.median())}
    srm_rows[s] = d
    for w in ("in_window", "outside_window"):
        v = P10[s][w]
        v["flagged_pct"] = float(100 * v["flagged"] / v["tested"]) if v["tested"] else None
R["P10"] = P10
# flag rate by month (exploratory + confirmatory + holdout together): shows where the problem sits in time
alld = pd.concat(srm_rows.values())
alld = alld[alld.p.notna()]
alld["month"] = alld.start.dt.to_period("M").astype(str)
bym = alld.groupby("month").agg(tested=("p", "size"), flagged=("p", lambda x: int((x < P10_ALPHA).sum())))
bym["flagged_pct"] = 100 * bym.flagged / bym.tested
R["P10_by_month"] = {m: {"tested": int(r.tested), "flagged": int(r.flagged), "flagged_pct": float(r.flagged_pct)}
                     for m, r in bym.iterrows()}
md += ["## P10. Randomization check (sample ratio mismatch)", "",
       f"Chi-square goodness-of-fit of each test's impressions against an equal split; flagged if p < {P10_ALPHA}. "
       f"Tests whose expected impressions per arm are below {P10_MIN_EXPECTED} are not tested. "
       "Max-share ratio = largest arm's impressions ÷ its fair share (1.00 = perfectly even).", ""]
md += table(["Split", "Tests (2+ arms)", "Too small", "Tested", "Flagged", "Flagged %", "Flagged % in window",
             "Flagged % outside window", "False flags expected if all fair", "Median max-share ratio: flagged / not"],
            [[s, fmt(v["tests_2plus_arms"]), fmt(v["too_small_to_test"]), fmt(v["tested"]), fmt(v["flagged"]),
              f"{v['flagged_pct']:.1f}%",
              f"{v['in_window']['flagged_pct']:.1f}% ({v['in_window']['flagged']:,} of {v['in_window']['tested']:,})" if v['in_window']['tested'] else "—",
              f"{v['outside_window']['flagged_pct']:.1f}% ({v['outside_window']['flagged']:,} of {v['outside_window']['tested']:,})",
              f"{v['expected_false_flags_if_all_fair']:.1f}",
              f"{v['flagged_max_share_ratio_median']:.2f} / {v['unflagged_max_share_ratio_median']:.2f}"] for s, v in P10.items()]) + [""]
md += ["Flag rate by month of test start (all three splits):", ""] + table(
    ["Month", "Tested", "Flagged", "Flagged %"],
    [[m, fmt(v["tested"]), fmt(v["flagged"]), f"{v['flagged_pct']:.1f}%"] for m, v in R["P10_by_month"].items()]) + [""]

# ---------------------------------------------------------------------------------------- P11
P11 = {}
for s, t in typed.items():
    h = t.groupby("headline")["clickability_test_id"].nunique()
    P11[s] = {"distinct_headlines": int(len(h)), "headlines_in_2plus_tests": int((h > 1).sum()),
              "max_tests_for_one_headline": int(h.max())}
allh = pd.concat([t[["headline", "clickability_test_id"]] for t in typed.values()])
hh = allh.groupby("headline")["clickability_test_id"].nunique()
R["P11"] = {"by_split": P11, "across_splits_headlines_in_2plus_tests": int((hh > 1).sum())}
md += ["## P11. Repeated headlines", ""] + table(
    ["Split", "Distinct headlines", "Headlines in 2+ tests", "Most tests for one headline"],
    [[s, fmt(v["distinct_headlines"]), fmt(v["headlines_in_2plus_tests"]), fmt(v["max_tests_for_one_headline"])]
     for s, v in P11.items()]) + ["", f"Across all three splits: {R['P11']['across_splits_headlines_in_2plus_tests']:,} headline texts appear in 2+ tests.", ""]

# ---------------------------------------------------------------------------------------- P12
P12 = {}
ent = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")
tag = re.compile(r"<[^>]+>")
for s, t in typed.items():
    h = t["headline"]
    chars = h.str.len()
    words = h.str.split().str.len()
    nonascii = Counter(ch for x in h for ch in x if ord(ch) > 127)
    P12[s] = {"chars_min_median_max": [int(chars.min()), float(chars.median()), int(chars.max())],
              "words_min_median_max": [int(words.min()), float(words.median()), int(words.max())],
              "html_entities": int(h.str.contains(ent).sum()), "html_tags": int(h.str.contains(tag).sum()),
              "leading_trailing_space": int((h != h.str.strip()).sum()),
              "double_spaces": int(h.str.contains("  ").sum()),
              "with_non_ascii": int(h.map(lambda x: any(ord(c) > 127 for c in x)).sum()),
              "top_non_ascii": [[c, f"U+{ord(c):04X}", n] for c, n in nonascii.most_common(12)],
              "mostly_non_latin": int(h.map(lambda x: sum(c.isalpha() and ord(c) > 591 for c in x) > 0.3 * max(1, sum(c.isalpha() for c in x))).sum())}
R["P12"] = P12
md += ["## P12. Headline text quality", ""] + table(
    ["Split", "Characters min / median / max", "Words min / median / max", "HTML entities", "HTML tags",
     "Leading/trailing space", "Double spaces", "Any non-ASCII", "Mostly non-Latin script"],
    [[s, " / ".join(f"{x:g}" for x in v["chars_min_median_max"]), " / ".join(f"{x:g}" for x in v["words_min_median_max"]),
      fmt(v["html_entities"]), fmt(v["html_tags"]), fmt(v["leading_trailing_space"]), fmt(v["double_spaces"]),
      fmt(v["with_non_ascii"]), fmt(v["mostly_non_latin"])] for s, v in P12.items()]) + [
    "", "Most common non-ASCII characters (exploratory): " +
    ", ".join(f"{c} ({u}) ×{n:,}" for c, u, n in P12["exploratory"]["top_non_ascii"]), ""]

# ---------------------------------------------------------------------------------------- P13 (exploratory only)
t = typed["exploratory"]
fre, mre = word_re(FEMALE), word_re(MALE)
t = t.assign(fem=t["headline"].str.contains(fre), mal=t["headline"].str.contains(mre))
g = t.groupby("clickability_test_id").agg(n=("fem", "size"), fem_any=("fem", "any"), fem_all=("fem", "all"),
                                           mal_any=("mal", "any"), mal_all=("mal", "all"))
g = g[g.n > 1]
fem_counts = Counter(m.lower() for x in t["headline"] for m in fre.findall(x))
mal_counts = Counter(m.lower() for x in t["headline"] for m in mre.findall(x))
R["P13"] = {"packages": len(t), "pct_female_term": float(100 * t.fem.mean()), "pct_male_term": float(100 * t.mal.mean()),
            "pct_both": float(100 * (t.fem & t.mal).mean()), "pct_neither": float(100 * (~t.fem & ~t.mal).mean()),
            "tests_2plus": len(g),
            "tests_female_varies": int((g.fem_any & ~g.fem_all).sum()),
            "tests_female_in_all": int(g.fem_all.sum()),
            "tests_male_varies": int((g.mal_any & ~g.mal_all).sum()),
            "top_female_terms": fem_counts.most_common(10), "top_male_terms": mal_counts.most_common(10)}
v = R["P13"]
md += ["## P13. Gender feasibility preview (exploratory only, rough draft word list, counts only)", "",
       f"Packages with a female term: {v['pct_female_term']:.1f}% · male term: {v['pct_male_term']:.1f}% · "
       f"both: {v['pct_both']:.1f}% · neither: {v['pct_neither']:.1f}%.", "",
       f"Of {v['tests_2plus']:,} tests with 2+ packages: female terms in **some but not all** arms: **{v['tests_female_varies']:,}**; "
       f"in every arm: {v['tests_female_in_all']:,}. Male terms in some but not all arms: {v['tests_male_varies']:,}.", "",
       "Most common female terms: " + ", ".join(f"{w} ×{n:,}" for w, n in v["top_female_terms"]),
       "", "Most common male terms: " + ", ".join(f"{w} ×{n:,}" for w, n in v["top_male_terms"]), ""]

# ---------------------------------------------------------------------------------------- P14
P14 = {}
for f in sorted(os.listdir(GA)):
    if not f.endswith(".csv"):
        continue
    df = pd.read_csv(os.path.join(GA, f), dtype=str, keep_default_na=False, encoding="utf-8-sig")
    na = {c: int((df[c].isin(["N/A", ""])).sum()) for c in df.columns}
    info = {"rows": len(df), "columns": list(df.columns), "na_or_empty": {k: n for k, n in na.items() if n}}
    if "Day Index" in df.columns:
        d = pd.to_datetime(df["Day Index"], format="%m/%d/%y", errors="coerce")
        info.update(first_day=str(d.min().date()), last_day=str(d.max().date()), unparsed_days=int(d.isna().sum()),
                    expected_days=int((d.max() - d.min()).days + 1))
    info["formats"] = sorted({("thousands commas" if re.fullmatch(r"[\d,]+", x) and "," in x else
                               "percent" if x.endswith("%") else "h:mm:ss" if re.fullmatch(r"\d+:\d\d:\d\d", x) else
                               "decimal" if re.fullmatch(r"\d+\.\d+", x) else None)
                              for c in df.columns[1:] for x in df[c]} - {None})
    P14[f] = info
R["P14"] = P14
md += ["## P14. Google Analytics files", ""] + table(
    ["File", "Rows", "Days covered", "N/A or empty cells", "Number formats"],
    [[f, fmt(v["rows"]), f"{v.get('first_day','—')} – {v.get('last_day','—')} ({v.get('expected_days','—')} expected)" if "first_day" in v else "— (one row per country)",
      ", ".join(f"{k}: {n}" for k, n in v["na_or_empty"].items()) or "none", ", ".join(v["formats"])] for f, v in P14.items()]) + [""]

# ---------------------------------------------------------------------------------------- P15
t = typed["exploratory"]
sig = pd.to_numeric(raw["exploratory"]["significance"], errors="coerce")
R["P15"] = {"significance_min_median_max": [float(sig.min()), float(sig.median()), float(sig.max())],
            "significance_empty": int(sig.isna().sum()),
            "first_place": raw["exploratory"]["first_place"].value_counts().to_dict(),
            "winner": raw["exploratory"]["winner"].value_counts().to_dict(),
            "winners_per_test": {str(k): int(v) for k, v in raw["exploratory"].assign(w=raw["exploratory"]["winner"] == "True")
                                 .groupby("clickability_test_id")["w"].sum().value_counts().sort_index().items()},
            "square_nonempty": int((raw["exploratory"]["square"] != "").sum()),
            "share_text_nonempty": int((raw["exploratory"]["share_text"] != "").sum())}
v = R["P15"]
md += ["## P15. Fields not analyzed (exploratory)", "",
       f"- `significance`: min / median / max = {v['significance_min_median_max'][0]:g} / {v['significance_min_median_max'][1]:g} / {v['significance_min_median_max'][2]:g}; empty {v['significance_empty']:,}. Not a p-value (archive docs).",
       f"- `first_place`: {v['first_place']}", f"- `winner`: {v['winner']}; winners per test: {v['winners_per_test']}",
       f"- `square` non-empty: {v['square_nonempty']:,}; `share_text` non-empty: {v['share_text_nonempty']:,}", ""]

# ---------------------------------------------------------------------------------------- write
os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
with open(os.path.join(ROOT, "build", "profile_results.json"), "w", encoding="utf-8") as f:
    json.dump(R, f, indent=1, default=str, ensure_ascii=False)
head = ["# Data Profile: Upworthy Research Archive", "",
        "Generated by `pipeline/00_profile/profile.py` from the raw OSF files (March 2020 release). Check definitions: NOTES §3.1. "
        "Source: Matias et al., Upworthy Research Archive, https://osf.io/jd64p/ (CC BY 4.0).", ""]
with open(os.path.join(ROOT, "docs", "data_profile.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(head + md))
print("profile written")
