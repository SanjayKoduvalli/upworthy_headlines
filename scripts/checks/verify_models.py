"""Validation of the main analysis (NOTES §8.2):
(1) independent estimate of H1 with a different method: Mantel-Haenszel odds ratio, female vs. none, stratified by test,
    standard library only, read straight from the model input file;
(2) planted-effect simulation: rebuild the clicks as coin flips at each variant's observed rate, once as-is and once with
    female-centered variants' rates raised 10%; the fitted female effect must move by about +10%;
(3) the fixed-effects fit against a brute-force fit with one dummy column per test, on a random 150-test subset.
"""
import csv
import gzip
import json
import math
import os
import sys

import numpy as np
from scipy import optimize, special

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT = os.environ.get("UPWORTHY_SPLIT", "exploratory")
sys.path.insert(0, os.path.join(ROOT, "pipeline", "04_analysis"))
from felogit import fit  # noqa: E402

res = json.load(open(os.path.join(ROOT, "build", "04_analysis", SPLIT, "main_results.json")))
rows = list(csv.DictReader(gzip.open(os.path.join(ROOT, "build", "04_analysis", SPLIT, "m1_input.csv.gz"), "rt", encoding="utf-8")))
problems = []

# (1) Mantel-Haenszel, female vs none, within tests
strata = {}
for r in rows:
    if r["gender"] in ("female", "none"):
        s = strata.setdefault(r["clickability_test_id"], {"female": [0, 0], "none": [0, 0]})
        s[r["gender"]][0] += int(r["clicks"]); s[r["gender"]][1] += int(r["impressions"]) - int(r["clicks"])
num = den = 0.0
for s in strata.values():
    a, b = s["female"]; c, d = s["none"]
    n = a + b + c + d
    if (a + b) and (c + d):
        num += a * d / n; den += b * c / n
mh = 100 * (num / den - 1)
m1_f = next(x for x in res["M1"] if x["term"] == "female")["pct"]
print(f"(1) Mantel-Haenszel female vs none: {mh:+.1f}%  (M1, adjusted for sentiment and other genders: {m1_f:+.1f}%)")
if abs(mh - m1_f) > 3:
    problems.append("MH and M1 female effects differ by more than 3 points")

# (2) planted effect
X = np.array([[int(r[t]) for t in ("female", "male", "both", "positive", "negative")] for r in rows], float)
n = np.array([int(r["impressions"]) for r in rows]); y = np.array([int(r["clicks"]) for r in rows])
g = np.array([r["clickability_test_id"] for r in rows])
rate = y / n
rng = np.random.default_rng(20261110)
shifts = []
for _ in range(20):
    base = fit(X, rng.binomial(n, rate), n, g, ["female", "male", "both", "positive", "negative"])["beta"][0]
    plant = fit(X, rng.binomial(n, np.where(X[:, 0] == 1, rate * 1.10, rate)), n, g,
                ["female", "male", "both", "positive", "negative"])["beta"][0]
    shifts.append(100 * (math.exp(plant - base) - 1))
print(f"(2) planted +10%: recovered {np.mean(shifts):+.1f}% on average (range {min(shifts):+.1f} to {max(shifts):+.1f}) over 20 runs")
if not 8 <= np.mean(shifts) <= 12:
    problems.append("planted effect not recovered")

# (3) brute force on a subset
tests = sorted(set(g)); pick = set(rng.choice(tests, 150, replace=False))
m = np.array([t in pick for t in g])
Xs, ys, ns, gs = X[m], y[m], n[m], g[m]
fe = fit(Xs, ys, ns, gs, ["female", "male", "both", "positive", "negative"])
codes, gi = np.unique(gs, return_inverse=True)
D = np.zeros((len(gi), len(codes))); D[np.arange(len(gi)), gi] = 1; Z = np.hstack([Xs, D])
th0 = np.r_[np.zeros(5), np.log(np.bincount(gi, weights=ys) / np.bincount(gi, weights=ns))]
nll = lambda th: -(ys * (Z @ th) - ns * np.logaddexp(0, Z @ th)).sum()  # noqa: E731
jac = lambda th: -Z.T @ (ys - ns * special.expit(Z @ th))  # noqa: E731
o = optimize.minimize(nll, th0, jac=jac, method="L-BFGS-B", options={"maxiter": 20000, "ftol": 1e-15, "gtol": 1e-9})
diff = np.max(np.abs(o.x[:5] - fe["beta"]))
print(f"(3) brute-force dummy fit on 150 tests: largest coefficient difference {diff:.2e}")
if diff > 1e-4:
    problems.append("brute-force fit disagrees")

print("verify_models:", "all checks pass" if not problems else problems)
sys.exit(1 if problems else 0)
