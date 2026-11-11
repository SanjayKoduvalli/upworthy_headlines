# AI Context Guide — Project 2: Upworthy Headlines

> Purpose: give any AI assistant (or person) what's needed to continue or recreate this project. Read fully before doing any work; keep it updated. The portfolio-wide rules began in Project 1 (repo `olist_marketing_and_sales_dashboard`, `AI_CONTEXT.md`); the ones that apply here are restated below.

Last updated: 2026-11-10

## 1. The portfolio
AI-assisted analyses of public datasets by Sanjay Koduvalli (marketing analytics, IBM; previously Macy's), each a case study with reproducible code, validation at every layer, and a dashboard or code output. Home page: https://sanjaykoduvalli.github.io/ (repo `sanjaykoduvalli.github.io`). One repo per project, served at `https://sanjaykoduvalli.github.io/<repo>/`. This project: https://github.com/SanjayKoduvalli/upworthy_headlines

## 2. Rules (non-negotiable)
1. **One step at a time, with approval.** Present each step's deliverable and wait for Sanjay's explicit approval.
2. **Approve every calculation before running it:** name, meaning, formula, grain, filters, edge cases. Approved definitions go in NOTES and are reused verbatim. This includes text classifications (e.g. gender of a headline) and test thresholds.
3. **Original sources only:** the Upworthy Research Archive from OSF (https://osf.io/jd64p/), never a third-party copy.
4. **Always cite:** Matias et al., Upworthy Research Archive, Cornell University, CC BY 4.0; *Scientific Data* 8, 195 (2021).
5. **Never modify raw files.** They live untouched in `data/raw/osf_jd64p/` (not committed); `docs/raw_checksums.txt` holds their SHA-256.
6. **Log everything** in NOTES: decisions, tool selection (how and why each tool was chosen), validation log, AI log (what the AI drafted vs. what Sanjay decided). Sanjay asked to document the process actively as we go.
7. **State limitations honestly.** Label causal (within-test) vs. descriptive (across-test) results every time.
8. **Reproducible by one command** (`scripts/build.py`, once the pipeline exists).
9. **Validate meticulously as you go:** tests per layer, an independent re-derivation (standard library, no pandas) of headline numbers, and mutation tests ("test the tests").
10. **Keep the decision register** (`docs/decision_register.md`): a row whenever Sanjay asks to document something.
11. **Data split (R2):** develop on exploratory; lock definitions; run once on confirmatory for headline results; never touch holdout. Quality profiling may cover all splits; nothing comparing click rates by headline content touches confirmatory before definitions are locked.
12. **Text features come from one fixed, validated method.** The plan was established packages (R3), but they can't be installed here; since Nov 10 the classifier is Claude with the fixed codebook-v2 prompt (R14), validated against Sanjay's 100 blind labels. Never change the prompt after the lock.
13. **Python 3.11+** for this project.
14. **Teach when asked, but keep it out of the logs:** Sanjay wants to understand the statistics. Explain both the math and the application before asking for approval of a statistical method. These explanations are for his own learning, not evidence of the project work, so don't record them in the AI log, the decision register or NOTES.

## 3. Stack
Python 3.11+ with pandas, numpy, scipy (later statsmodels for regression; text tools per NOTES §5). Dashboard/output: ECharts HTML like Project 1, opening from disk, with the shared site header and `assets/site.css`. Hosting: GitHub Pages.

## 4. Layout
```
upworthy_headlines/
├── AI_CONTEXT.md, README.md, NOTES.md, LICENSE (MIT), requirements.txt, .gitignore
├── data/raw/osf_jd64p/        ← the OSF download, untouched (not committed)
├── pipeline/common.py         ← paths, table I/O, the confirmatory lock (L4)
├── pipeline/00_profile/       ← profile.py → docs/data_profile.md, build/profile_results.json
├── pipeline/01_load/, 02_clean/   ← load rules L1–L5, cleaning rules S1–S12 → build/ tables + docs/cleaning_log.md
├── pipeline/03_features/      ← codebook.py (v1, v2), label sample, make_classifier_inputs.py
├── pipeline/04_analysis/      ← aa_check, aa_calibrate, felogit (FE logit), main_effects, topic_effects; UPWORTHY_SPLIT=exploratory|confirmatory
├── LOCK.md                    ← two-stage lock: stage 1 classifier (R15, Nov 10); stage 2 analysis (R22, Nov 11, code fingerprints)
├── scripts/checks/            ← independent checks (verify_profile.py)
├── tests/                     ← validation tests per layer
├── docs/                      ← data_profile, data_dictionary, decision_register, raw_checksums
└── build/                     ← generated (not committed)
```

## 5. Status
- Step 0 (business context and caveats): ✅ approved 2026-11-04
- Step 1 (setup): ✅ folder, raw copy, checksums, license
- Step 2 (profiling): ✅ approved (with R7 sentiment/topic variables and R8 reader-facing text only)
- Steps 4–5 (load + cleaning): 🔍 built; 15/15 tests, independent check and mutation test pass; awaiting review
- Step 6 (text features): 🔁 hand labels done (100 headlines, blind; NOTES §5.3). Codebook v2: gender (4), sentiment (3), 12 topic tags as 0/1 columns, LGBTQ+ merged into gender equality (R12–R13). Classifier = Claude with a fixed prompt, run from the Headline Classifier artifact (https://claude.ai/artifact/Vw1wA4fVjuhi8yww7d1nta; results in its `results` database collection) (R14). Default model chosen and exploratory labeled (14,465 units). Classifier locked (stage 1, R15); confirmatory labeling (977 calls) run by Sanjay from the page; import with `scripts/import_classifier_labels.py <export> default`
- Portfolio-wide to-do list: `~/projects/sanjaykoduvalli.github.io/TODO.md`; start there, and update it at the end of each session.
- ✅ Done since: labels exported and joined; LOCK.md stages 1–2 approved; A/A check, calibration, main and topic models run on exploratory then once on confirmatory (see Step 7)

## 6. How to resume
1. Read this file, NOTES.md and docs/decision_register.md.
2. Download the archive from https://osf.io/jd64p/ into `data/raw/osf_jd64p/` and check `docs/raw_checksums.txt`.
3. `pip install -r requirements.txt`; `python3 scripts/build.py` (profile, load, clean, tests, independent checks).
4. Continue with the next step under the rules above.
- Step 7 (analysis): ✅ A/A check + calibration, main model, topic models; run on exploratory, then once on confirmatory (results of record: docs/results/confirmatory/, NOTES §8.4)
- Step 8 (case study, R23): 🔍 draft built 2026-11-11: index.html (generated), assets/figures, notebooks/walkthrough.ipynb. Rebuild: `python3 pipeline/05_report/figures.py && python3 pipeline/05_report/build_case_study.py && python3 pipeline/05_report/make_notebook.py`
- Next: Sanjay's review of the page; statsmodels check on his Mac; push; turn on GitHub Pages; add the Upworthy card and skills column to the home site
