"""Build docs/validation/label_review.xlsx: the AI's draft labels for Sanjay to review and correct.

Inputs: docs/validation/label_sample.csv (the 200-headline sample) and docs/validation/ai_draft_labels.csv
(labels drafted by the AI from the codebook). Sanjay edits only the yellow "Final" columns, which start as a copy of
the AI draft; "Changed?" is a formula, so the share of AI labels he corrected is measured, not estimated.
"""
import os
import sys

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from codebook import GENDER, SENTIMENT, SENTIMENT_RULE, TOPIC, TOPIC_RULE  # noqa: E402
from common import DOCS  # noqa: E402

V = os.path.join(DOCS, "validation")
s = pd.read_csv(os.path.join(V, "label_sample.csv"), keep_default_na=False)
a = pd.read_csv(os.path.join(V, "ai_draft_labels.csv"), keep_default_na=False)
d = s.merge(a, on="sample_id", validate="1:1")
assert len(d) == 200

F = "Arial"
bold, norm = Font(name=F, bold=True), Font(name=F)
yellow = PatternFill("solid", fgColor="FFF2CC")
grey = PatternFill("solid", fgColor="F2F2F2")
wrap = Alignment(wrap_text=True, vertical="top")

wb = Workbook()
ws = wb.active
ws.title = "Labels"
ws["A1"] = "Hand-label review: 200 Upworthy headlines (exploratory sample)"
ws["A1"].font = Font(name=F, bold=True, size=13)
ws["A2"] = ("How to use: the yellow Final columns start as a copy of the AI's draft. Change any you disagree with using "
            "the dropdowns; leave correct ones alone. Rows marked 'yes' under 'AI unsure' are the ones worth a closer look. "
            "Definitions are on the Codebook tab. Judge only what a reader saw on the tile: the headline (and excerpt).")
ws["A2"].font = norm
ws["A2"].alignment = wrap
ws.merge_cells("A2:L2")
ws.row_dimensions[2].height = 45
head = ["Sample ID", "Headline", "Excerpt shown", "AI gender", "AI sentiment", "AI topic", "AI unsure",
        "Final gender", "Final sentiment", "Final topic", "Changed?", "Your notes"]
for j, h in enumerate(head, 1):
    c = ws.cell(row=4, column=j, value=h)
    c.font = bold
    c.fill = yellow if h.startswith("Final") or h == "Your notes" else grey
    c.alignment = wrap
for i, r in enumerate(d.itertuples(), start=5):
    vals = [r.sample_id, r.headline_clean, r.excerpt_clean, r.gender, r.sentiment, r.topic,
            "yes" if r.unsure == "yes" else "", r.gender, r.sentiment, r.topic, None, ""]
    for j, v in enumerate(vals, 1):
        c = ws.cell(row=i, column=j, value=v)
        c.font = norm
        c.alignment = wrap
        if j in (8, 9, 10, 12):
            c.fill = yellow
    ws.cell(row=i, column=11, value=f'=IF(OR(H{i}<>D{i},I{i}<>E{i},J{i}<>F{i}),"changed","")').font = norm
last = 4 + len(d)
for col, w in zip("ABCDEFGHIJKL", [9, 62, 24, 11, 12, 9, 9, 12, 13, 10, 10, 30]):
    ws.column_dimensions[col].width = w
ws.freeze_panes = "C5"
ws.auto_filter.ref = f"A4:L{last}"
ws.conditional_formatting.add(f"A5:L{last}", FormulaRule(formula=[f'$K5="changed"'], font=Font(name=F, color="9C0006", bold=True)))

for col, opts in [("H", GENDER), ("I", SENTIMENT), ("J", TOPIC)]:
    dv = DataValidation(type="list", formula1='"' + ",".join(opts) + '"', allow_blank=False, showErrorMessage=True,
                        errorTitle="Pick from the list", error="See the Codebook tab for the allowed values.")
    ws.add_data_validation(dv)
    dv.add(f"{col}5:{col}{last}")

ws.cell(row=last + 2, column=2, value="Labels you changed").font = bold
ws.cell(row=last + 2, column=4, value=f'=COUNTIF(K5:K{last},"changed")').font = bold
ws.cell(row=last + 3, column=2, value="Share of AI draft rows changed").font = bold
c = ws.cell(row=last + 3, column=4, value=f"=D{last + 2}/COUNTA(A5:A{last})")
c.font, c.number_format = bold, "0.0%"

cb = wb.create_sheet("Codebook")
cb["A1"] = "Codebook (DRAFT for Sanjay's approval). Judge only what the reader saw: headline and excerpt."
cb["A1"].font = Font(name=F, bold=True, size=12)
row = 3
for title, items, rule in [("Gender focus", GENDER, None), ("Sentiment", SENTIMENT, SENTIMENT_RULE),
                           ("Perceived topic", {k: f"{v[0]}: {v[1]}" for k, v in TOPIC.items()}, TOPIC_RULE)]:
    cb.cell(row=row, column=1, value=title).font = bold
    row += 1
    for k, v in items.items():
        cb.cell(row=row, column=1, value=k).font = norm
        x = cb.cell(row=row, column=2, value=v)
        x.font, x.alignment = norm, wrap
        row += 1
    if rule:
        x = cb.cell(row=row, column=2, value="Rule: " + rule)
        x.font, x.alignment = Font(name=F, italic=True), wrap
        row += 1
    row += 1
cb.column_dimensions["A"].width = 12
cb.column_dimensions["B"].width = 100

out = os.path.join(V, "label_review.xlsx")
wb.save(out)
print("wrote", out)
