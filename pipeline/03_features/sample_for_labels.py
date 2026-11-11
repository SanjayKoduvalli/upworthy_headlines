"""Draw the hand-label validation sample: 200 distinct exploratory headlines (NOTES §5, tool selection rule).

Unit: one distinct cleaned headline (S3), from exploratory variants with a headline (S4). Exploratory only (R2, L4).
Stratified so the rarer gender cases are well represented, using the profile's rough draft word list (P13):
  70 with a female term · 50 with a male term but no female term · 80 with neither.
Fixed random seed, so the same sample is drawn every time. Writes docs/validation/label_sample.csv.
Because strata are over-sampled on purpose, accuracy estimates later re-weight by each stratum's share (written here).
"""
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import DOCS, load_table  # noqa: E402

SEED = 20261104
SIZES = {"female term": 70, "male term only": 50, "neither": 80}
FEMALE = r"\b(?:woman|women|she|her|hers|herself|girl|girls|mom|moms|mother|mothers|daughter|daughters|wife|wives|sister|sisters|lady|ladies)\b"
MALE = r"\b(?:man|men|he|him|his|himself|boy|boys|dad|dads|father|fathers|son|sons|husband|husbands|brother|brothers|guy|guys)\b"

p = load_table("02_clean/packages", split="exploratory")
p = p[~p.headline_missing].drop_duplicates("headline_clean")[["headline_clean", "excerpt_clean", "clickability_test_id", "variant_id"]]
fem = p.headline_clean.str.contains(FEMALE, flags=re.I, regex=True)
mal = p.headline_clean.str.contains(MALE, flags=re.I, regex=True)
p["stratum"] = ["female term" if f else "male term only" if m else "neither" for f, m in zip(fem, mal)]
share = p.stratum.value_counts(normalize=True)
parts = [p[p.stratum == s].sample(n, random_state=SEED) for s, n in SIZES.items()]
out = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)   # shuffle so strata aren't in blocks
out.insert(0, "sample_id", [f"L{i + 1:03d}" for i in range(len(out))])
out["stratum_share_in_population"] = out.stratum.map(share).round(6)
os.makedirs(os.path.join(DOCS, "validation"), exist_ok=True)
out.to_csv(os.path.join(DOCS, "validation", "label_sample.csv"), index=False)
print(f"sample: {len(out)} headlines from {len(p):,} distinct; population shares: " +
      ", ".join(f"{k} {v:.1%}" for k, v in share.items()))
