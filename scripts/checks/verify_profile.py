"""Independent check of the step-2 profile (Python standard library only: no pandas, numpy or scipy).

Re-derives the headline profiling numbers straight from the raw CSVs and compares them with
build/profile_results.json, written by pipeline/00_profile/profile.py:
  P1 row counts · P4 tests and packages per split · P6 total impressions and clicks ·
  P10 chi-square flags (statistic computed by hand; p-value from our own regularized-gamma code) ·
  P13 female / male term shares (exploratory).
Usage (from the project root): python3 scripts/checks/verify_profile.py     Exit code 1 on any mismatch.
"""
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_stdlib import gammq  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DS = os.path.join(ROOT, "data", "raw", "osf_jd64p", "upworthy-archive-datasets")
SPLITS = {"exploratory": "upworthy-archive-exploratory-packages-03.12.2020.csv",
          "confirmatory": "upworthy-archive-confirmatory-packages-03.12.2020.csv",
          "holdout": "upworthy-archive-holdout-packages-03.12.2020.csv"}
R = json.load(open(os.path.join(ROOT, "build", "profile_results.json"), encoding="utf-8"))
W0, W1 = datetime(2013, 6, 25), datetime(2014, 1, 10, 23, 59, 59)
fails = []


def check(name, got, want):
    ok = got == want if not isinstance(want, float) else abs(got - want) < 1e-9
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {got} vs {want}")
    if not ok:
        fails.append(name)


FEM = re.compile(r"\b(?:woman|women|she|her|hers|herself|girl|girls|mom|moms|mother|mothers|daughter|daughters|wife|wives|sister|sisters|lady|ladies)\b", re.I)
MAL = re.compile(r"\b(?:man|men|he|him|his|himself|boy|boys|dad|dads|father|fathers|son|sons|husband|husbands|brother|brothers|guy|guys)\b", re.I)

for split, fn in SPLITS.items():
    with open(os.path.join(DS, fn), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    check(f"P1 {split} rows", len(rows), R["P1"][split]["csv_module"])
    tests = defaultdict(list)
    for r in rows:
        tests[r["clickability_test_id"]].append(r)
    check(f"P4 {split} tests", len(tests), R["P4"]["counts"][split]["tests"])
    check(f"P6 {split} impressions", sum(int(r["impressions"]) for r in rows), R["P6"][split]["total_impressions"])
    check(f"P6 {split} clicks", sum(int(r["clicks"]) for r in rows), R["P6"][split]["total_clicks"])
    flagged = flagged_in = tested_in = 0
    for g in tests.values():
        if len(g) < 2:
            continue
        imp = [int(r["impressions"]) for r in g]
        e = sum(imp) / len(imp)
        chi2 = sum((o - e) ** 2 / e for o in imp)
        p = gammq((len(imp) - 1) / 2, chi2 / 2)          # chi-square survival = Q(df/2, x/2)
        start = min(datetime.strptime(r["created_at"][:19], "%Y-%m-%d %H:%M:%S") for r in g)
        inw = W0 <= start <= W1
        tested_in += inw
        if p < 0.001:
            flagged += 1
            flagged_in += inw
    check(f"P10 {split} flagged", flagged, R["P10"][split]["flagged"])
    check(f"P10 {split} flagged in window", flagged_in, R["P10"][split]["in_window"]["flagged"])
    check(f"P10 {split} tested in window", tested_in, R["P10"][split]["in_window"]["tested"])
    if split == "exploratory":
        n = len(rows)
        check("P13 % female term", round(100 * sum(bool(FEM.search(r["headline"])) for r in rows) / n, 9),
              round(R["P13"]["pct_female_term"], 9))
        check("P13 % male term", round(100 * sum(bool(MAL.search(r["headline"])) for r in rows) / n, 9),
              round(R["P13"]["pct_male_term"], 9))

print(f"\nverify_profile: {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
