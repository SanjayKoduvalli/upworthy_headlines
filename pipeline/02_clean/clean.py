"""Step 5: cleaning rules S1–S12 (approved by Sanjay 2026-11-04; NOTES §4.2). Principle: flag, don't delete.

Every package row is kept. Problems become flag columns, raw text stays beside cleaned text, and each analysis
states which flags it excludes. These rules never look at clicks or headline meaning, so they may run on the
confirmatory split (rule L4 governs the feature and analysis steps).

  S1  tests starting 2013-06-25 .. 2014-01-10 (broken randomization, archive 2024 update) -> in_problem_window
  S2  chi-square sample-ratio check per test, p < 0.001 -> srm_fail; srm_fail_outside_window
  S3  headline -> headline_clean: decode entities, drop HTML tags, zero-width chars, nbsp -> space,
      curly quotes -> straight, collapse whitespace, trim (wording and case unchanged)
  S4  empty cleaned headline -> headline_missing
  S5  same reader-facing content (headline_clean, eyecatcher_id, excerpt_clean) in one test -> shared variant_id
  S6  what a test varies (headline / image / excerpt); identical reader-facing content in every arm = A/A test
  S7  headline_n_tests = tests using the same cleaned headline (reruns), within the split
  S8  missing eyecatcher_id -> image_missing
  S9  excerpt -> excerpt_clean (S3 rules); excerpt_is_stock for "Things that matter. Pass 'em on."
  S10 zero-click packages kept (documented)          S11 a test's week = week of its first package
  S12 kept, not used: significance, first_place, winner, square, share_text, slug, updated_at, lede (R8)
Writes build/02_clean/packages.csv.gz, build/02_clean/tests.csv.gz and build/02_clean/cleaning_audit.csv.gz.
"""
import html
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import load_table, save_table  # noqa: E402

PROBLEM_START = pd.Timestamp("2013-06-25 00:00:00")
PROBLEM_END = pd.Timestamp("2014-01-10 23:59:59.999999")
SRM_ALPHA = 0.001
STOCK_EXCERPT = "Things that matter. Pass 'em on."
TAG = re.compile(r"<[^>]+>")
ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
SPACES = re.compile(r"\s+")


def clean_text(s):
    """S3 / S9 text cleaning. Returns None for missing input."""
    if s is None or s is pd.NA or (isinstance(s, float) and np.isnan(s)):
        return None
    s = html.unescape(s)                 # &amp; -> &
    s = TAG.sub(" ", s)                  # <strong>x</strong> -> x (space so words never fuse)
    s = ZERO_WIDTH.sub("", s)
    s = s.replace(" ", " ")         # non-breaking space
    s = s.translate(QUOTES)              # ’ -> '
    return SPACES.sub(" ", s).strip()


def clean(pk):
    pk = pk.copy()
    # S3, S4, S8, S9
    pk["headline_clean"] = pk["headline"].map(clean_text).astype("string")
    pk["headline_missing"] = pk["headline_clean"].isna() | (pk["headline_clean"] == "")
    pk["excerpt_clean"] = pk["excerpt"].map(clean_text).replace("", None).astype("string")
    pk["excerpt_is_stock"] = pk["excerpt_clean"] == STOCK_EXCERPT
    pk["excerpt_is_stock"] = pk["excerpt_is_stock"].fillna(False).astype(bool)
    pk["image_missing"] = pk["eyecatcher_id"].isna()

    # S5: variant = identical reader-facing content within a test (missing values compared as equal)
    key = ["clickability_test_id", pk["headline_clean"].fillna("\x00"), pk["eyecatcher_id"].fillna("\x00"),
           pk["excerpt_clean"].fillna("\x00")]
    g = pk.groupby([pk["split"], pk["clickability_test_id"], key[1], key[2], key[3]], sort=True)
    pk["variant_n"] = g.ngroup()
    pk["variant_id"] = pk["clickability_test_id"] + "-" + (
        pk.groupby("clickability_test_id")["variant_n"].rank(method="dense").astype(int).astype(str))
    pk = pk.drop(columns="variant_n")
    pk["variant_size"] = pk.groupby("variant_id")["row_id"].transform("size")

    # S7: reruns of the same cleaned headline, counted within the split
    pk["headline_n_tests"] = pk.groupby(["split", "headline_clean"])["clickability_test_id"].transform("nunique")
    pk.loc[pk["headline_missing"], "headline_n_tests"] = pd.NA
    pk["headline_n_tests"] = pk["headline_n_tests"].astype("Int64")

    # tests table: S1, S2, S6, S11
    first = pk.sort_values(["created_at", "row_id"]).groupby("clickability_test_id").head(1).set_index("clickability_test_id")
    t = pk.groupby("clickability_test_id").agg(
        split=("split", "first"), n_packages=("row_id", "size"), n_variants=("variant_id", "nunique"),
        impressions=("impressions", "sum"), clicks=("clicks", "sum"),
        n_headlines=("headline_clean", "nunique"), n_images=("eyecatcher_id", lambda x: x.fillna("\x00").nunique()),
        n_excerpts=("excerpt_clean", lambda x: x.fillna("\x00").nunique()))
    t["start"] = first["created_at"]
    t["test_week"] = first["test_week"]                                                     # S11
    t["in_problem_window"] = t["start"].between(PROBLEM_START, PROBLEM_END)               # S1

    def srm(x):                                                                             # S2 (rows, not variants)
        imp = x.to_numpy(dtype=float)
        if len(imp) < 2 or imp.sum() / len(imp) < 5:
            return pd.Series({"srm_chi2": np.nan, "srm_p": np.nan})
        chi2, p = stats.chisquare(imp)
        return pd.Series({"srm_chi2": chi2, "srm_p": p})
    t = t.join(pk.groupby("clickability_test_id")["impressions"].apply(srm).unstack())
    t["srm_fail"] = t["srm_p"] < SRM_ALPHA
    t["srm_fail_outside_window"] = t["srm_fail"] & ~t["in_problem_window"]
    t["usable_causal"] = ~t["in_problem_window"] & ~t["srm_fail"]

    h, i, e = t["n_headlines"] > 1, t["n_images"] > 1, t["n_excerpts"] > 1                 # S6
    t["varies"] = np.select(
        [h & i, h & ~i & e, h & ~i & ~e, ~h & i, ~h & ~i & e],
        ["headline+image", "headline+excerpt", "headline only", "image (no headline change)", "excerpt only"],
        "nothing (A/A)")
    t["varies_headline"] = h
    t["is_aa_test"] = t["n_variants"] == 1
    t = t.reset_index()

    pk = pk.merge(t[["clickability_test_id", "in_problem_window", "srm_fail", "usable_causal", "is_aa_test",
                     "varies_headline"]], on="clickability_test_id", how="left")
    return pk, t


def audit(pk, t):
    """Measured impact of every rule, per split -> docs/cleaning_log.md (generated)."""
    rows = []
    for s in sorted(pk["split"].unique()):
        p, q = pk[pk.split == s], t[t.split == s]
        n, m = len(p), len(q)
        add = lambda rid, what, table, action, k, why: rows.append(
            dict(split=s, rule=rid, what=what, table=table, action=action, affected=int(k),
                 total=n if table == "packages" else m, why=why))
        add("S1", "Test starts in the broken-randomization window (2013-06-25 – 2014-01-10)", "tests", "flagged",
            q.in_problem_window.sum(), "Archive 2024 update; excluded from causal results")
        add("S2", "Fails the chi-square randomization check (p < 0.001)", "tests", "flagged", q.srm_fail.sum(),
            "Unequal assignment; excluded from causal results")
        add("S2", "…of which outside the window", "tests", "flagged", q.srm_fail_outside_window.sum(), "")
        add("S1+S2", "Tests usable for causal results", "tests", "flagged", q.usable_causal.sum(), "")
        add("S3", "Headline changed by cleaning", "packages", "cleaned copy", (p.headline_clean != p.headline).sum(),
            "Raw headline kept unchanged")
        for lab, rx in [("HTML tags removed", TAG), ("zero-width characters removed", ZERO_WIDTH)]:
            add("S3", f"…{lab}", "packages", "cleaned copy", p.headline.fillna("").str.contains(rx).sum(), "")
        add("S3", "…curly quotes straightened", "packages", "cleaned copy",
            p.headline.fillna("").str.contains("[‘’“”]").sum(), "")
        add("S3", "…extra or untrimmed spaces fixed", "packages", "cleaned copy",
            (p.headline.fillna("") != p.headline.fillna("").str.strip()).sum() + p.headline.fillna("").str.contains(r"\s{2,}").sum(), "Rows can count twice")
        add("S4", "Headline empty after cleaning", "packages", "flagged", p.headline_missing.sum(), "Excluded from text features")
        add("S5", "Packages sharing a variant with another package", "packages", "flagged",
            (p.variant_size > 1).sum(), "Summed into one variant for headline effects")
        add("S5", "Variants", "packages", "none", p.variant_id.nunique(), "Distinct reader-facing versions")
        for lab in ["headline only", "headline+image", "headline+excerpt", "image (no headline change)", "excerpt only", "nothing (A/A)"]:
            add("S6", f"Test varies: {lab}", "tests", "flagged", (q.varies == lab).sum(), "")
        add("S7", "Packages whose headline is used in 2+ tests", "packages", "flagged", (p.headline_n_tests > 1).sum(),
            "Kept; reruns are separate experiments")
        add("S8", "Missing image id", "packages", "flagged", p.image_missing.sum(), "Kept; 'unknown image'")
        add("S9", "Excerpt is the stock phrase", "packages", "flagged", p.excerpt_is_stock.sum(), "")
        add("S9", "Excerpt empty", "packages", "flagged", p.excerpt_clean.isna().sum(), "")
        add("S10", "Zero-click packages (kept)", "packages", "none", (p.clicks == 0).sum(), "Valid results")
        add("S11", "Tests whose packages span 2 test weeks", "tests", "none",
            (p.groupby("clickability_test_id").test_week.nunique() > 1).sum(), "Week = week of first package")
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pk = load_table("01_load/packages", content_blind=True)   # cleaning never looks at clicks or meaning (L4)
    pk, t = clean(pk)
    a = audit(pk, t)
    save_table(pk, "02_clean/packages")
    save_table(t, "02_clean/tests")
    save_table(a, "02_clean/cleaning_audit")
    print(f"clean: {len(pk):,} packages, {len(t):,} tests, {pk.variant_id.nunique():,} variants")
