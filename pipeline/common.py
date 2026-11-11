"""Shared paths, table I/O and the confirmatory lock (rule L4) for every pipeline step.

Build tables are written as gzip-compressed CSV plus a JSON manifest of column types, so they reload with exactly
the same types and can be opened by anyone (Parquet was planned; see NOTES §4.2 for why CSV was used).
"""
import gzip
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "osf_jd64p", "upworthy-archive-datasets")
BUILD = os.path.join(ROOT, "build")
DOCS = os.path.join(ROOT, "docs")
LOCK_FILE = os.path.join(ROOT, "LOCK.md")

RAW_FILES = {  # L3: the holdout file is deliberately absent, so it can never be loaded (R2)
    "exploratory": "upworthy-archive-exploratory-packages-03.12.2020.csv",
    "confirmatory": "upworthy-archive-confirmatory-packages-03.12.2020.csv",
}


def save_table(df, name):
    """Write build/<name>.csv.gz and build/<name>.types.json (column -> pandas dtype)."""
    path = os.path.join(BUILD, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path + ".csv.gz", "wt", encoding="utf-8", newline="") as f:
        df.to_csv(f, index=False, date_format="%Y-%m-%d %H:%M:%S.%f")
    with open(path + ".types.json", "w", encoding="utf-8") as f:
        json.dump({c: str(t) for c, t in df.dtypes.items()}, f, indent=1)


def load_table(name, split=None, content_blind=False):
    """Read a build table with its saved types. Reading confirmatory rows is subject to the lock (L4),
    unless the caller is a content-blind step (load, clean, their tests) and says so with content_blind=True."""
    path = os.path.join(BUILD, name)
    types = json.load(open(path + ".types.json", encoding="utf-8"))
    dates = [c for c, t in types.items() if t.startswith("datetime")]
    plain = {c: ("string" if t in ("object", "string", "str") else t) for c, t in types.items() if c not in dates}
    df = pd.read_csv(path + ".csv.gz", dtype=plain, parse_dates=dates, keep_default_na=False, na_values=[""])
    if split is not None:
        df = df[df["split"] == split]
    if not content_blind and (df["split"] == "confirmatory").any():
        require_lock()
    return df


def require_lock():
    """L4: feature and analysis code may read confirmatory rows only after Sanjay has approved the final
    definitions, recorded in LOCK.md with a line 'Approved by Sanjay: <date>'. Cleaning does not call this:
    its rules never look at clicks or headline content."""
    ok = os.path.exists(LOCK_FILE) and "Approved by Sanjay:" in open(LOCK_FILE, encoding="utf-8").read()
    if not ok:
        raise PermissionError("Confirmatory data is locked (rule L4). Use split='exploratory' until LOCK.md "
                              "records Sanjay's approval of the final definitions.")
