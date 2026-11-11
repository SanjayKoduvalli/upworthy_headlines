"""Validation tests for the load (L1–L5) and cleaning (S1–S12) steps.

Convention (same as Project 1): each test returns the FAILING rows as a DataFrame (empty = pass) and has a
docstring that becomes its description in docs/validation_report.md. Run all with scripts/build.py.
These tests only look at structure and flags, never at click rates by content, so they may read confirmatory (L4).
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline"))
from common import RAW, RAW_FILES, ROOT, load_table  # noqa: E402

import json  # noqa: E402

PROFILE = json.load(open(os.path.join(ROOT, "build", "profile_results.json"), encoding="utf-8"))
_cache = {}


def raw(split):
    if split not in _cache:
        _cache[split] = pd.read_csv(os.path.join(RAW, RAW_FILES[split]), dtype=str, keep_default_na=False)
    return _cache[split]


L = load_table("01_load/packages", content_blind=True)
P = load_table("02_clean/packages", content_blind=True)
T = load_table("02_clean/tests", content_blind=True)
SPLITS = list(RAW_FILES)


def fail(rows, **cols):
    return pd.DataFrame(rows, columns=list(cols) or None)


# ------------------------------------------------------------------------------------------- load
def test_load__row_counts_match_raw_files():
    """L1/L3: every raw row is loaded once per split, and the holdout is absent."""
    bad = [(s, (L.split == s).sum(), len(raw(s))) for s in SPLITS if (L.split == s).sum() != len(raw(s))]
    bad += [("holdout present", int((L.split == "holdout").sum()), 0)] if (L.split == "holdout").any() else []
    return pd.DataFrame(bad, columns=["split", "loaded", "raw"])


def test_load__counts_and_dates_typed_without_loss():
    """L1/L2: impressions, clicks and test_week equal the raw text exactly; every created_at parsed (none blank)."""
    bad = []
    for s in SPLITS:
        r, l_ = raw(s), L[L.split == s].sort_values("row_id")
        r = r.assign(row_id=r["Unnamed: 0"].astype(int)).sort_values("row_id")
        for c in ["impressions", "clicks", "test_week"]:
            n = int((r[c].astype("int64").to_numpy() != l_[c].to_numpy()).sum())
            if n:
                bad.append((s, c, n))
        n = int(l_["created_at"].isna().sum())
        if n:
            bad.append((s, "created_at unparsed", n))
    return pd.DataFrame(bad, columns=["split", "column", "mismatches"])


def test_load__raw_headline_unchanged():
    """L1/S3: the raw `headline` column survives load and cleaning byte for byte (empty text -> missing only)."""
    bad = []
    for s in SPLITS:
        r = raw(s).assign(row_id=lambda d: d["Unnamed: 0"].astype(int)).set_index("row_id")["headline"]
        p = P[P.split == s].set_index("row_id")["headline"].fillna("")
        n = int((r.loc[p.index] != p).sum())
        if n:
            bad.append((s, n))
    return pd.DataFrame(bad, columns=["split", "changed"])


# ------------------------------------------------------------------------------------------- clean
def test_clean__no_rows_deleted():
    """Flag, don't delete: the clean table has exactly the loaded rows."""
    a, b = set(zip(L.split, L.row_id)), set(zip(P.split, P.row_id))
    return pd.DataFrame([("missing", len(a - b)), ("extra", len(b - a)), ("duplicated", int(P.duplicated(["split", "row_id"]).sum()))],
                        columns=["problem", "n"]).query("n > 0")


def test_clean__headline_clean_is_clean():
    """S3: headline_clean has no HTML tags or entities, zero-width chars, nbsp, curly quotes, double or edge spaces."""
    h = P["headline_clean"].dropna()
    checks = {"tag": r"<[^>]+>", "entity": r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);", "zero-width": "[​‌‍⁠﻿]",
              "nbsp": " ", "curly quote": "[‘’“”]", "double space": r"\s{2,}", "edge space": r"^\s|\s$"}
    return pd.DataFrame([(k, int(h.str.contains(rx).sum())) for k, rx in checks.items()], columns=["problem", "n"]).query("n > 0")


def test_clean__headline_clean_keeps_wording():
    """S3: cleaning only removes markup and normalizes spacing/quotes: the letters and digits are unchanged
    once tags are dropped (checks that no word was altered or lost)."""
    alnum = lambda s: re.sub(r"[^0-9A-Za-z]", "", s)
    raw_h = P["headline"].fillna("").map(lambda s: re.sub(r"<[^>]+>", " ", __import__("html").unescape(s)))
    bad = P[raw_h.map(alnum) != P["headline_clean"].fillna("").map(alnum)]
    return bad[["split", "row_id", "headline", "headline_clean"]]


def test_clean__s1_window_matches_profile():
    """S1: tests flagged in the window = the profile's independent count (P10, tests with 2+ arms) for each split."""
    bad = []
    for s in SPLITS:
        got = int(T[(T.split == s) & (T.n_packages > 1)].in_problem_window.sum())
        want = PROFILE["P10"][s]["in_window"]["tested"]
        if got != want:
            bad.append((s, got, want))
    return pd.DataFrame(bad, columns=["split", "clean", "profile"])


def test_clean__s2_flags_match_profile():
    """S2: chi-square failures (all, and outside the window) = the profile's counts for each split."""
    bad = []
    for s in SPLITS:
        q = T[T.split == s]
        for got, want, lab in [(int(q.srm_fail.sum()), PROFILE["P10"][s]["flagged"], "all"),
                               (int(q.srm_fail_outside_window.sum()), PROFILE["P10"][s]["outside_window"]["flagged"], "outside")]:
            if got != want:
                bad.append((s, lab, got, want))
    return pd.DataFrame(bad, columns=["split", "which", "clean", "profile"])


def test_clean__usable_causal_definition():
    """S1+S2: usable_causal is true exactly when a test is outside the window and passes the randomization check."""
    bad = T[T.usable_causal != (~T.in_problem_window & ~T.srm_fail)]
    return bad[["clickability_test_id", "in_problem_window", "srm_fail", "usable_causal"]]


def test_clean__variants_are_identical_inside():
    """S5: packages sharing a variant_id have identical headline_clean, image and excerpt_clean, and belong to one test;
    packages in different variants of the same test differ in at least one of them."""
    k = P.assign(h=P.headline_clean.fillna("\x00"), i=P.eyecatcher_id.fillna("\x00"), e=P.excerpt_clean.fillna("\x00"))
    inside = k.groupby("variant_id").agg(h=("h", "nunique"), i=("i", "nunique"), e=("e", "nunique"), t=("clickability_test_id", "nunique"))
    bad_in = inside[(inside > 1).any(axis=1)].reset_index()
    per = k.drop_duplicates("variant_id").groupby("clickability_test_id").apply(lambda d: d.duplicated(["h", "i", "e"]).sum(), include_groups=False)
    bad_out = per[per > 0].reset_index()
    return pd.concat([bad_in.assign(problem="variant not uniform"), bad_out.assign(problem="two variants identical")])


def test_clean__every_test_has_one_s6_label():
    """S6: each test gets exactly one `varies` label; A/A tests are exactly the tests with a single variant."""
    labels = {"headline only", "headline+image", "headline+excerpt", "image (no headline change)", "excerpt only", "nothing (A/A)"}
    bad = T[~T.varies.isin(labels) | (T.is_aa_test != (T.varies == "nothing (A/A)")) | T.clickability_test_id.duplicated()]
    return bad[["clickability_test_id", "varies", "is_aa_test"]]


def test_clean__test_totals_tie_to_packages():
    """Tests table: impressions and clicks per test equal the sum of its packages; package counts match."""
    s = P.groupby("clickability_test_id").agg(i=("impressions", "sum"), c=("clicks", "sum"), n=("row_id", "size"))
    m = T.set_index("clickability_test_id").join(s)
    return m[(m.impressions != m.i) | (m.clicks != m.c) | (m.n_packages != m.n)].reset_index()


def test_clean__flags_copied_to_packages():
    """Every package carries its test's S1/S2/S6 flags unchanged."""
    m = P[["clickability_test_id", "in_problem_window", "srm_fail", "usable_causal", "is_aa_test"]].merge(
        T[["clickability_test_id", "in_problem_window", "srm_fail", "usable_causal", "is_aa_test"]], on="clickability_test_id", suffixes=("", "_t"))
    return m[(m.in_problem_window != m.in_problem_window_t) | (m.srm_fail != m.srm_fail_t) |
             (m.usable_causal != m.usable_causal_t) | (m.is_aa_test != m.is_aa_test_t)]


def test_clean__stock_excerpt_and_missing_flags():
    """S8/S9: image_missing = no eyecatcher_id; excerpt_is_stock = cleaned excerpt equals the stock phrase."""
    bad = P[(P.image_missing != P.eyecatcher_id.isna()) |
            (P.excerpt_is_stock != (P.excerpt_clean.fillna("") == "Things that matter. Pass 'em on."))]
    return bad[["row_id", "eyecatcher_id", "image_missing", "excerpt_clean", "excerpt_is_stock"]]


def test_lock__confirmatory_blocked_without_approval():
    """L4: without LOCK.md, reading confirmatory rows from a build table raises an error, while exploratory reads work."""
    import common
    bad = []
    if os.path.exists(common.LOCK_FILE) and "Approved by Sanjay:" in open(common.LOCK_FILE, encoding="utf-8").read():
        return pd.DataFrame(columns=["problem"])          # lock already approved: nothing to enforce
    for split in (None, "confirmatory"):
        try:
            load_table("02_clean/tests", split=split)
            bad.append(f"split={split} was readable without approval")
        except PermissionError:
            pass
    try:
        load_table("02_clean/tests", split="exploratory")
    except PermissionError:
        bad.append("exploratory was blocked")
    return pd.DataFrame({"problem": bad})
