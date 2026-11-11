"""Step 4: load the raw package files with explicit types (load rules L1–L5, approved 2026-11-04; NOTES §4.1).

  L1  every column read as text, then typed explicitly; empty text -> missing
  L2  timestamps parsed as ISO 8601 (two formats in the data: with and without fractional seconds)
  L3  exploratory + confirmatory get a `split` column; the holdout is never loaded
  L4  (enforced in pipeline/common.py: later steps can't read confirmatory rows until LOCK.md approves)
  L5  the undeployed file is not loaded (no impressions or clicks)
Writes build/01_load/packages.csv.gz. The raw files are read only, never changed.
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import RAW, RAW_FILES, save_table  # noqa: E402

TEXT = ["clickability_test_id", "excerpt", "headline", "lede", "slug", "eyecatcher_id", "share_text", "square"]
INT = ["impressions", "clicks", "test_week"]
BOOL = ["first_place", "winner"]
TIME = ["created_at", "updated_at"]


def load():
    parts = []
    for split, fn in RAW_FILES.items():
        df = pd.read_csv(os.path.join(RAW, fn), dtype=str, keep_default_na=False, encoding="utf-8")   # L1
        df = df.rename(columns={"Unnamed: 0": "row_id"})
        out = pd.DataFrame({"split": split, "row_id": df["row_id"].astype("int64")})
        for c in TEXT:
            out[c] = df[c].replace("", pd.NA).astype("string")                                        # L1
        for c in INT:
            out[c] = pd.to_numeric(df[c], errors="raise").astype("int64")
        for c in BOOL:
            if not df[c].isin(["True", "False"]).all():
                raise ValueError(f"{split}.{c} has values other than True/False")
            out[c] = df[c] == "True"
        out["significance"] = pd.to_numeric(df["significance"], errors="raise")
        for c in TIME:
            out[c] = pd.to_datetime(df[c], format="ISO8601", errors="raise")                           # L2
        parts.append(out)
    return pd.concat(parts, ignore_index=True)


if __name__ == "__main__":
    df = load()
    save_table(df, "01_load/packages")
    print(f"load: {len(df):,} packages ({', '.join(f'{s} {n:,}' for s, n in df['split'].value_counts().items())})")
