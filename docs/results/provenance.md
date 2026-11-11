# Where every number comes from (provenance audit, 2026-11-11)

Sanjay asked which statistics are clearly derived from code and which could be AI estimates or hallucinations. This file sorts every finding and figure into one of five groups. It was written after checking each number quoted in the conversation against the files the code wrote: all 48 quoted analysis numbers matched (`build/04_analysis/<split>/*.json`).

**Rule for the case study:** every number on the page is read from these result files by the script that builds the page (`pipeline/05_report/build_case_study.py`); none is typed by hand. Exceptions, each cited: the archive's size (32,487 experiments) and dates from the paper, and design constants (12 topics, 100 hand labels, 1,000 placebo fits, the 5% level, the planted +10%).

## 1. Computed by the pipeline and re-derived independently: highest confidence

| What | Computed by | Independent check |
|---|---|---|
| Row counts, test counts, problem-window and randomization (SRM) flags, A/A identification | `pipeline/00–02` | Standard-library re-implementations from the raw files (`verify_profile.py`, `verify_clean.py`, `verify_aa.py`); mutation tests |
| A/A false-positive rate (26.1% / 25.9%), p-value shape, per-test p-values | `aa_check.py` | `verify_aa.py` recomputes every p-value from the raw file (all 326 / 1,386 match) |
| Noise factor φ from A/A tests (1.96 / 1.92), empirical threshold, split-half false positives | `aa_calibrate.py` | `verify_aa.py` (φ and threshold match to 1e-9) |
| Woman vs. none effect (+12.4% / +8.9%) | `main_effects.py` | Mantel–Haenszel, a different method in standard-library code (+13.5% / +9.4%; it doesn't adjust for sentiment, so close rather than equal) |
| Environment framing effect (−17.0% / −16.2%) | `topic_effects.py` | Mantel–Haenszel (−16.3% / −15.3%) |

## 2. Computed by the pipeline, one implementation, validated by tests: high confidence
- **All other model results:** man, both, sentiment, woman vs. man, the gender × topic interactions, every topic-framing (T1) and story-topic (T2) number, the model's own φ (3.83 / 3.92), and the placebo thresholds.
- **How the model code is validated:** it matches a brute-force fit with one column per test (differences around 1e-6); it recovers a planted +10% effect (+10.4% / +10.1%); and placebo labels on A/A tests produce the expected null results.
- **⏳ Still open:** the external check against statsmodels, the standard package (`scripts/checks/statsmodels_check.py`, to run on Sanjay's Mac). Until it passes, the model code has been checked only against code the AI also wrote.

## 3. Produced by AI judgment: the biggest source of uncertainty
- **Every gender, sentiment and topic label** (73,078 headline texts) was assigned by Claude following the fixed codebook. These are judgments, not computations. Every finding in groups 1–2 inherits their errors.
- **What backs them:** a blind comparison with Sanjay's labels on 100 exploratory headlines (gender 96% agreement, κ 0.94; sentiment 71%, κ 0.56; topic 80% "his topic among the tags"), computed by `scripts/import_classifier_labels.py`.
- **What doesn't:** no confirmatory label was checked by a person; 100 headlines is a small sample (gender agreement could plausibly be 90–99%); sentiment agreement is moderate.
- **For the write-up:** say plainly that the labels come from an AI classifier validated on 100 hand-labeled headlines, and that sentiment results carry the most label noise.

## 4. Calculated outside the pipeline, in the conversation: re-checked, but not part of the build
| Number | Status |
|---|---|
| The earlier AI draft's agreement with Sanjay (95% / 72% / 78%, κ 0.93 / 0.58 / 0.76) | Re-derived 2026-11-11 from `human_labels.csv` and `ai_draft_labels.csv`: matches. Not produced by a saved script |
| Diagnostics ruling out causes of the A/A failure (lede differences, creation time, arm order, impressions balance) | Run as one-off code on 2026-11-10; numbers in NOTES §8.1; not in the build. Fine as context, not as headline results |
| "About ±7 clicks per version" (and ±10 corrected), the chi-square worked example (p 0.04 → 0.28), "3.6 GB" | Arithmetic illustrations; re-checked: 6.98, 9.8, 0.040 → 0.277, 3.61 GB |
| "Chance alone gives roughly 2.5–7.5%" for 326 A/A tests | Rough; the exact binomial range is 2.8%–7.4% |
| "About 57,000 confirmatory headlines, 950 calls" | An estimate made before the data was built; the actual count is 58,613 headlines in 977 calls |

## 5. Explanations and facts from the AI's general knowledge or the archive's documentation, not from our data
- **Why identical tiles vary twice as much as coin flips** (repeat viewers, bursts of shared traffic): a plausible explanation, **not tested** and not testable with this data. Present it as a likely reason.
- **What Upworthy's `significance` score and `winner` field mean** (a 0–100 editor-facing score whose calculation changed over time; `winner` = the editors' pick): taken from the archive documentation summarized in `docs/data_dictionary.md`. **⚠️ Treating a score of 95+ as the dashboard "flagging a winner" is the AI's interpretation, not a documented rule.** Before the case study uses the 97% hook, confirm in the archive paper (Matias et al.) how the score was shown to editors, or phrase it neutrally: "some version scored 95 or higher on the dashboard's significance score in 97% of identical tests". (The AI conflated the two fields in one chat summary on 2026-11-11: 97% is the 95+ score, 44% is the editors' winner pick.) **Resolved 2026-11-11 (R25):** the archive paper says the field is "NOT an estimate of statistical significance" (a custom comparison with earlier tests, meaning changed over time, no threshold documented), so the 97% figure is not used in the case study.
- **The problem window (2013-06-25 to 2014-01-10):** from the archive authors' documentation; our profiling reproduced their finding (70% of tests flagged in the window vs. 0.2–0.5% outside).
- **That readers saw headline, image and sometimes excerpt, not the lede:** from the archive's screenshots (R8).
- **Statistical conventions:** "kappa 0.6–0.8 = substantial" (Landis & Koch's scale, cited from memory); the Holm correction, Mantel–Haenszel, quasi-binomial and fixed-effects logit are standard methods, described from general knowledge. Cite a textbook or paper for each in the write-up.
