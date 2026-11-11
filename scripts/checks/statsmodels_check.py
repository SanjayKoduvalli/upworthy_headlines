"""Reference check of the main model M1 with statsmodels, run on Sanjay's Mac (R19).

The project's fit (pipeline/04_analysis/felogit.py) is hand-written because statsmodels can't be installed where the AI
works. This script refits M1 with statsmodels, the standard Python package, using one dummy column per test, and
compares the coefficients, standard errors and the model's own dispersion estimate with the project's results.

On the Mac, from the project folder:
    pip3 install statsmodels
    python3 scripts/checks/statsmodels_check.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPLIT = sys.argv[1] if len(sys.argv) > 1 else "exploratory"   # python3 scripts/checks/statsmodels_check.py confirmatory
TERMS = ["female", "male", "both", "positive", "negative"]

v = pd.read_csv(os.path.join(ROOT, "build", "04_analysis", SPLIT, "m1_input.csv.gz"))
res = json.load(open(os.path.join(ROOT, "build", "04_analysis", SPLIT, "main_results.json")))
dummies = pd.get_dummies(v.clickability_test_id, prefix="t", drop_first=True, dtype=float)
X = sm.add_constant(pd.concat([v[TERMS].astype(float), dummies], axis=1))
endog = np.column_stack([v.clicks, v.impressions - v.clicks])
m = sm.GLM(endog, X, family=sm.families.Binomial()).fit()
phi_sm = m.pearson_chi2 / m.df_resid

ok = True
print("term        statsmodels   project     difference")
for r in res["M1"]:
    b_sm, b_pr = m.params[r["term"]], r["beta"]
    z_sm = m.params[r["term"]] / m.bse[r["term"]]
    print(f"{r['term']:<10}  {b_sm:+.6f}    {b_pr:+.6f}   {b_sm - b_pr:+.1e}   (z {z_sm:.3f} vs {r['z_raw']:.3f})")
    ok = ok and abs(b_sm - b_pr) < 1e-5 and abs(z_sm - r["z_raw"]) < 1e-3
print(f"model dispersion (Pearson chi-square / df): statsmodels {phi_sm:.4f}, project {res['phi_model_pearson']:.4f}")
ok = ok and abs(phi_sm - res["phi_model_pearson"]) < 1e-3
print("RESULT:", "MATCH - the project's fit agrees with statsmodels" if ok else "MISMATCH - send this output to Claude")
sys.exit(0 if ok else 1)
