"""Build the inputs for the headline classifier page (codebook v2; NOTES §5.4, R12–R14).

Unit: one distinct reader-facing text = cleaned headline + the excerpt shown under it (R8). Stock excerpts
(the same boilerplate on many tiles, S-rules) say nothing about the story, so they are left out of the text and
packages that differ only by a stock excerpt share one unit. Each unit gets a stable key (first 12 hex characters
of SHA-1 of "headline<US>excerpt"), which is how labels join back to packages.

Writes, into the folder given as the first argument (the classifier page's data folder):
  prompt.json      the fixed instructions, built from codebook.py (one source of truth for the definitions)
  validation.json  Sanjay's 100 blind-labeled headlines with his labels (v1 mapped to v2), to score the classifier
  exploratory.json all exploratory units, in batches
  confirmatory.json  only after the classifier lock in LOCK.md (R15), and only if the prompt is unchanged; text only
and build/03_features/units.csv.gz (key → package rows) for joining the labels back.
"""
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import CLASSIFIER_LOCK_LINE, DOCS, LOCK_FILE, load_table, load_text_for_classifier, save_table  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("codebook", os.path.join(os.path.dirname(__file__), "codebook.py"))
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

BATCH = 60
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)


def key(h, e):
    return hashlib.sha1((h + "\x1f" + e).encode("utf-8")).hexdigest()[:12]


def units(p):
    p = p[~p.headline_missing].copy()
    p["excerpt_used"] = [("" if s or not isinstance(e, str) else e) for e, s in zip(p.excerpt_clean, p.excerpt_is_stock)]
    p["unit_key"] = [key(h, e) for h, e in zip(p.headline_clean, p.excerpt_used)]
    return p


def batches(u):
    rows = u.drop_duplicates("unit_key")[["unit_key", "headline_clean", "excerpt_used"]].values.tolist()
    items = [{"k": k, "h": h, **({"e": e} if e else {})} for k, h, e in rows]
    return {"batch_size": BATCH, "n_units": len(items),
            "batches": [items[i:i + BATCH] for i in range(0, len(items), BATCH)]}


# ---- the prompt (codebook v2) ----
g_codes = {"female": "f", "male": "m", "both": "b", "none": "n"}
s_codes = {"positive": "+", "neutral": "0", "negative": "-"}
prompt = (
    "You are labeling headlines from Upworthy (a US news site, 2013-2015) for a research study. Each numbered item is "
    "what a reader saw on a story tile: the headline (H) and, when there was one, the short excerpt under it (E). "
    "Judge only from that text, the way a typical reader would.\n\n"
    "GENDER: who the headline centers.\n" +
    "".join(f"  {g_codes[k]} = {k}: {v}\n" for k, v in cb.GENDER.items()) +
    "\nSENTIMENT: the overall feeling the headline is built to give.\n" +
    "".join(f"  {s_codes[k]} = {k}: {v}\n" for k, v in cb.SENTIMENT.items()) +
    f"  Rule: {cb.SENTIMENT_RULE}\n"
    "\nTOPICS: tag codes.\n" +
    "".join(f"  {c} = {n}: {d}\n" for c, (n, d) in cb.TOPIC_V2.items()) +
    f"  Rule: {cb.TOPIC_RULE_V2}\n"
    "\nReply with only a JSON array with one object per item, in item order, like "
    '[{"i":1,"g":"f","s":"+","t":["GEN","HUM"]},{"i":2,"g":"n","s":"0","t":[]}]. '
    "Use exactly these codes and nothing else.\n\nITEMS\n"
)
json.dump({"codebook": "v2", "prompt": prompt, "gender_codes": g_codes, "sentiment_codes": s_codes,
           "topics": list(cb.TOPIC_V2)}, open(os.path.join(OUT, "prompt.json"), "w", encoding="utf-8"), ensure_ascii=False)

# ---- exploratory ----
ex = units(load_table("02_clean/packages", split="exploratory"))
json.dump(batches(ex), open(os.path.join(OUT, "exploratory.json"), "w", encoding="utf-8"), ensure_ascii=False)
keep = ["split", "row_id", "clickability_test_id", "variant_id", "unit_key"]
frames = [ex[keep]]

# ---- validation: the 100 headlines Sanjay labeled blind (codebook v1 → v2) ----
V = os.path.join(DOCS, "validation")
sample = {r["sample_id"]: r for r in csv.DictReader(open(os.path.join(V, "label_sample.csv"), encoding="utf-8"))}
by_variant = ex.drop_duplicates("variant_id").set_index("variant_id")
val = []
for r in csv.DictReader(open(os.path.join(V, "human_labels.csv"), encoding="utf-8")):
    s = sample[r["sample_id"]]
    row = by_variant.loc[s["variant_id"]]
    t = cb.V1_TO_V2.get(r["topic"], r["topic"])
    val.append({"k": r["sample_id"], "h": row.headline_clean, **({"e": row.excerpt_used} if row.excerpt_used else {}),
                "human": {"g": g_codes[r["gender"]], "s": s_codes[r["sentiment"]], "t": t or ""}})
json.dump({"batch_size": BATCH, "n_units": len(val), "batches": [val[i:i + BATCH] for i in range(0, len(val), BATCH)]},
          open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8"), ensure_ascii=False)

# ---- confirmatory, only after the lock (L4) ----
locked = not (os.path.exists(LOCK_FILE) and CLASSIFIER_LOCK_LINE in open(LOCK_FILE, encoding="utf-8").read())
if not locked:
    co = units(load_text_for_classifier("confirmatory"))   # text and keys only; outcomes stay locked (R15)
    lock = open(LOCK_FILE, encoding="utf-8").read()
    fp = hashlib.sha256(open(os.path.join(OUT, "prompt.json"), "rb").read()).hexdigest()
    if fp not in lock:
        sys.exit("prompt.json differs from the prompt frozen in LOCK.md; the classifier definitions may not change after the lock")
    json.dump(batches(co), open(os.path.join(OUT, "confirmatory.json"), "w", encoding="utf-8"), ensure_ascii=False)
    frames.append(co[keep])

import pandas as pd  # noqa: E402
save_table(pd.concat(frames, ignore_index=True), "03_features/units")
print(f"classifier inputs: prompt {len(prompt.encode())} bytes; validation {len(val)}; exploratory "
      f"{ex.unit_key.nunique():,} units from {len(ex):,} packages; confirmatory "
      f"{'not written (locked)' if locked else f'{co.unit_key.nunique():,} units'}")
