"""Copy Sanjay's answers from the Headline Labeler artifact into the project (R11).

The labeler page saves one document per headline in its `answers` collection. Claude exports that collection
as JSON files (one per headline) and runs:
    python3 scripts/sync_labels.py <folder with the exported answer .json files>
This writes docs/validation/human_labels.csv (the reference labels) and fills the Final columns of
docs/validation/label_review.xlsx, so the spreadsheet always matches what was entered in the app.
Headlines not yet answered keep the AI draft in the Final columns and are marked "not yet labeled".
"""
import csv
import glob
import json
import os
import sys

from openpyxl import load_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "docs", "validation")
FIELDS = ("gender", "sentiment", "topic")
ALLOWED = {"gender": {"female", "male", "both", "none"}, "sentiment": {"positive", "neutral", "negative"},
           "topic": {"POL", "RAC", "LGB", "WOM", "HEA", "ECO", "EDU", "FAM", "ENV", "CRI", "SCI", "ENT", "HUM", "UNC"}}

src = sys.argv[1]
answers = {}
for f in glob.glob(os.path.join(src, "**", "*.json"), recursive=True):
    d = json.load(open(f, encoding="utf-8"))
    d = d.get("data", d)                                    # accept either a bare body or {"data": body}
    sid = d.get("sample_id") or os.path.splitext(os.path.basename(f))[0]
    bad = [k for k in FIELDS if d.get(k) not in ALLOWED[k]]
    if bad:
        sys.exit(f"{f}: unexpected value in {bad}")         # the page only offers the allowed values
    answers[sid] = d

sample_ids = [r["sample_id"] for r in csv.DictReader(open(os.path.join(V, "label_sample.csv"), encoding="utf-8"))]
unknown = set(answers) - set(sample_ids)
if unknown:
    sys.exit(f"answers for ids not in the sample: {sorted(unknown)[:5]}")

with open(os.path.join(V, "human_labels.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["sample_id", "gender", "sentiment", "topic", "seconds", "answered_at", "codebook"])
    for sid in sample_ids:
        if sid in answers:
            a = answers[sid]
            w.writerow([sid, a["gender"], a["sentiment"], a["topic"], a.get("seconds"), a.get("answered_at"), a.get("codebook")])

path = os.path.join(V, "label_review.xlsx")
wb = load_workbook(path)
ws = wb["Labels"]
ws["L4"] = "Status"
n = 0
for row in range(5, 5 + len(sample_ids)):
    sid = ws.cell(row=row, column=1).value
    if sid in answers:
        for col, k in zip((8, 9, 10), FIELDS):
            ws.cell(row=row, column=col, value=answers[sid][k])
        ws.cell(row=row, column=12, value="labeled in app " + str(answers[sid].get("answered_at", ""))[:10])
        n += 1
    else:
        ws.cell(row=row, column=12, value="not yet labeled")
wb.save(path)
print(f"sync_labels: {n} of {len(sample_ids)} headlines labeled; wrote human_labels.csv and label_review.xlsx")
