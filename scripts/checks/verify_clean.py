"""Independent check of the cleaning step (Python standard library only: no pandas, numpy or scipy).

Re-implements rules S1, S2, S3, S5 and S6 from the RAW files and compares the counts with
build/02_clean/cleaning_audit.csv.gz (written by pipeline/02_clean/clean.py):
  S1 tests in the window · S2 randomization failures · S1+S2 usable tests · S3 headlines changed ·
  S5 variants and packages sharing a variant · S6 every 'varies' label, including A/A tests.
Usage (from the project root): python3 scripts/checks/verify_clean.py     Exit code 1 on any mismatch.
"""
import csv
import gzip
import html
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stats_stdlib import gammq  # noqa: E402  (our own chi-square p-value, also standard library)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DS = os.path.join(ROOT, "data", "raw", "osf_jd64p", "upworthy-archive-datasets")
FILES = {"exploratory": "upworthy-archive-exploratory-packages-03.12.2020.csv",
         "confirmatory": "upworthy-archive-confirmatory-packages-03.12.2020.csv"}
W0, W1 = datetime(2013, 6, 25), datetime(2014, 1, 10, 23, 59, 59, 999999)


def clean(s):
    if s == "":
        return None
    s = re.sub(r"<[^>]+>", " ", html.unescape(s))
    for ch in "​‌‍⁠﻿":
        s = s.replace(ch, "")
    s = s.replace(" ", " ").replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(s.split()) or None


def parse(ts):
    return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f" if "." in ts else "%Y-%m-%d %H:%M:%S")


with gzip.open(os.path.join(ROOT, "build", "02_clean", "cleaning_audit.csv.gz"), "rt", encoding="utf-8") as f:
    AUDIT = {(r["split"], r["rule"], r["what"]): int(r["affected"]) for r in csv.DictReader(f)}
fails = []


def check(split, rule, what, got):
    want = AUDIT[(split, rule, what)]
    ok = got == want
    print(f"{'OK  ' if ok else 'FAIL'} {split} {rule} {what}: {got} vs {want}")
    if not ok:
        fails.append((split, rule, what))


for split, fn in FILES.items():
    with open(os.path.join(DS, fn), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    tests = defaultdict(list)
    for r in rows:
        tests[r["clickability_test_id"]].append(r)
    in_win = srm = usable = 0
    labels = defaultdict(int)
    n_variants = shared = 0
    for g in tests.values():
        start = min(parse(r["created_at"]) for r in g)
        w = W0 <= start <= W1
        in_win += w
        imp = [int(r["impressions"]) for r in g]
        fail = False
        if len(imp) >= 2 and sum(imp) / len(imp) >= 5:
            e = sum(imp) / len(imp)
            fail = gammq((len(imp) - 1) / 2, sum((o - e) ** 2 / e for o in imp) / 2) < 0.001
        srm += fail
        usable += (not w) and (not fail)
        keys = [(clean(r["headline"]), r["eyecatcher_id"] or None, clean(r["excerpt"])) for r in g]
        counts = defaultdict(int)
        for k in keys:
            counts[k] += 1
        n_variants += len(counts)
        shared += sum(c for c in counts.values() if c > 1)
        h = len({k[0] for k in keys}) > 1
        i = len({k[1] for k in keys}) > 1
        x = len({k[2] for k in keys}) > 1
        lab = ("headline+image" if h and i else "headline+excerpt" if h and x else "headline only" if h else
               "image (no headline change)" if i else "excerpt only" if x else "nothing (A/A)")
        labels[lab] += 1
    check(split, "S1", "Test starts in the broken-randomization window (2013-06-25 – 2014-01-10)", in_win)
    check(split, "S2", "Fails the chi-square randomization check (p < 0.001)", srm)
    check(split, "S1+S2", "Tests usable for causal results", usable)
    check(split, "S3", "Headline changed by cleaning", sum(clean(r["headline"]) != r["headline"] for r in rows if r["headline"]))
    check(split, "S5", "Variants", n_variants)
    check(split, "S5", "Packages sharing a variant with another package", shared)
    for lab in ["headline only", "headline+image", "headline+excerpt", "image (no headline change)", "excerpt only", "nothing (A/A)"]:
        check(split, "S6", f"Test varies: {lab}", labels[lab])

print(f"\nverify_clean: {len(fails)} failure(s)")
sys.exit(1 if fails else 0)
