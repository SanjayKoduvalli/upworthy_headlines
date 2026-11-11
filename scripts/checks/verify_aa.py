"""Independent re-computation of the A/A check AA1-AA2 (NOTES §8.1) from the RAW exploratory file, standard library only.

Re-derives which tests are A/A (identical headline, excerpt and image across all packages) and usable (outside the
2013-06-25 to 2014-01-10 window and randomization-check p >= 0.001), its own chi-square p-values via gammq, and
compares them with build/04_analysis/aa_results.json and aa_tests.
"""
import csv
import gzip
import json
import math
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_stdlib import gammq  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT = os.environ.get("UPWORTHY_SPLIT", "exploratory")
RAW = os.path.join(ROOT, "data", "raw", "osf_jd64p", "upworthy-archive-datasets",
                   f"upworthy-archive-{SPLIT}-packages-03.12.2020.csv")
OUT = os.path.join(ROOT, "build", "04_analysis", SPLIT)


def norm(s):  # light normalization, enough to decide "identical to the reader"
    s = re.sub(r"<[^>]+>", "", s or "").replace(" ", " ")
    s = re.sub("[​‌‍⁠﻿]", "", s)   # invisible characters readers never saw (added 2026-11-11)
    return re.sub(r"\s+", " ", s).strip()


tests = defaultdict(list)
with open(RAW, encoding="utf-8", newline="") as f:
    for r in csv.DictReader(f):
        tests[r["clickability_test_id"]].append(r)

pvals = {}
for tid, rows in tests.items():
    if len({(norm(r["headline"]), norm(r["excerpt"]), r["eyecatcher_id"]) for r in rows}) != 1 or len(rows) < 2:
        continue
    start = min(r["created_at"][:10] for r in rows)
    if "2013-06-25" <= start <= "2014-01-10":
        continue
    n = [int(r["impressions"]) for r in rows]; c = [int(r["clicks"]) for r in rows]
    srm = sum((x - sum(n) / len(n)) ** 2 / (sum(n) / len(n)) for x in n)
    if gammq((len(n) - 1) / 2, srm / 2) < 0.001:
        continue
    rate = sum(c) / sum(n)
    chi2 = sum((ci - ni * rate) ** 2 / (ni * rate) + ((ni - ci) - ni * (1 - rate)) ** 2 / (ni * (1 - rate)) for ci, ni in zip(c, n))
    pvals[tid] = gammq((len(n) - 1) / 2, chi2 / 2)

res = json.load(open(os.path.join(OUT, "aa_results.json")))
with gzip.open(os.path.join(OUT, "aa_tests.csv.gz"), "rt", encoding="utf-8") as f:
    built = {r["clickability_test_id"]: float(r["p"]) for r in csv.DictReader(f) if r["usable_causal"] == "True"}

problems = []
if set(pvals) != set(built):
    problems.append(f"test sets differ: {len(set(pvals) - set(built))} only here, {len(set(built) - set(pvals))} only in build")
for tid in set(pvals) & set(built):
    if not math.isclose(pvals[tid], built[tid], rel_tol=1e-6, abs_tol=1e-9):
        problems.append(f"{tid}: p {pvals[tid]} vs {built[tid]}")
k = sum(p < 0.05 for p in pvals.values())
if (k, len(pvals)) != (res["AA2"]["n_significant"], res["AA2"]["n_tests"]):
    problems.append(f"AA2 {k}/{len(pvals)} vs {res['AA2']['n_significant']}/{res['AA2']['n_tests']}")
print(f"verify_aa: {len(pvals)} usable A/A tests, {k} significant; " + ("all match" if not problems else f"{len(problems)} problems"))
for p in problems[:10]:
    print("  ", p)
if problems:
    sys.exit(1)

# ---- AA6: independent pooled phi and empirical threshold from the p-value-free statistics ----
cal = json.load(open(os.path.join(OUT, "calibration.json")))
chis, dfs = [], []
for tid, rows in tests.items():
    if tid not in pvals:
        continue
    n = [int(r["impressions"]) for r in rows]; c = [int(r["clicks"]) for r in rows]
    rate = sum(c) / sum(n)
    chis.append(sum((ci - ni * rate) ** 2 / (ni * rate) + ((ni - ci) - ni * (1 - rate)) ** 2 / (ni * (1 - rate)) for ci, ni in zip(c, n)))
    dfs.append(len(n) - 1)
phi = sum(chis) / sum(dfs)
ok = math.isclose(phi, cal["phi"], rel_tol=1e-9)
r = sorted(x / d for x, d in zip(chis, dfs)); k = 0.95 * (len(r) - 1)
q = r[int(k)] + (r[min(int(k) + 1, len(r) - 1)] - r[int(k)]) * (k - int(k))   # same interpolation as numpy's default
ok2 = math.isclose(q, cal["empirical_threshold_chi2_per_df"], rel_tol=1e-9)
print(f"verify_aa AA6: phi {phi:.4f} ({'match' if ok else 'MISMATCH'}); threshold {q:.4f} ({'match' if ok2 else 'MISMATCH'})")
sys.exit(0 if ok and ok2 else 1)
