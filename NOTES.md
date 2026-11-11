# Project Notes — Upworthy Headlines

Working notebook for Project 2: business context, caveats, decisions, profiling definitions, tool selection, validation log and AI log. Rules for working on it are in `AI_CONTEXT.md`. Every decision is also indexed in `docs/decision_register.md`.

**Data source:** The Upworthy Research Archive (J. Nathan Matias, Kevin Munger, Marianne Aubin Le Quere, Charles Ebersole; Cornell University), https://osf.io/jd64p/ · CC BY 4.0.
Paper: Matias et al. (2021), *Scientific Data* 8, 195, https://doi.org/10.1038/s41597-021-00934-7. June 2024 update: https://upworthy.natematias.com/2024-06-upworthy-archive-update.html

**Skills this project showcases (set by Sanjay):** Python, data cleaning and transformation, A/B testing, regression modeling.

---

## 1. Business context (step 0, approved by Sanjay 2026-11-04)

**Upworthy** was a viral news site (2012 onward) that spread social-cause stories through Facebook and Twitter. Its business ran on attention: more clicks meant more traffic, ad and sponsorship revenue, and sharing. Before an article went live, editors wrote many headline versions (often 25 drafts) and the site A/B tested them.

**How a test worked:**
- A **test** (`clickability_test_id`) is one experiment for one article. Its **packages** are the arms: a headline plus an image (`eyecatcher_id`), sometimes an excerpt.
- Each browser session was randomly assigned one package. **Impressions** = sessions shown it; **clicks** = sessions that clicked it. Click rate = clicks ÷ impressions.
- One experiment ran on the site at a time. Editors chose when to stop and which version to publish (not always the best performer).

**The archive:** released by Cornell in 2021. January 24, 2013 – April 30, 2015: 32,487 tests, 150,817 packages, about 538 million impressions and 8.2 million clicks. Split by week into exploratory (4,873 tests, 22,666 packages), confirmatory (22,743 / 105,551) and holdout (4,871 / 22,600), plus a file of undeployed packages.

**Our question:** does centering a woman in a headline change whether people click? And what else about a headline drives clicks?

### Caveats (approved with the context)
**About the experiments**
- **Randomization failure, June 25, 2013 – January 10, 2014.** The 2024 update found about 22% of tests served one arm to everyone (likely a caching error). Not to be used for causal claims.
- `significance` is not a statistical significance measure (its calculation changed over time). `winner` = the editors' pick, not necessarily the best arm. Neither is used as an outcome.
- **Intent-to-treat:** some packages sat below the fold, so not every impression was seen. Click rates are low and noisy.
- **Audiences differ between tests** (social traffic shifts), so comparisons are made within a test.
- **No planned sample sizes;** many single tests are underpowered, so pooling matters.
- **Reruns** are logged as new tests with shared content, so headlines can repeat across tests.

**About the gender question**
- Gender is **inferred from headline text** (there is no gender field). The classification is a calculation and needs approval (rule 2), plus validation against a hand-labeled sample.
- The subject's gender **rarely varies within a test** (all arms describe the same story). Two designs follow, always labeled:
  - **Within-test (causal, fewer cases):** tests where some arms center a woman and others don't. Randomization makes the difference causal.
  - **Across-test (descriptive, more data):** stories about women vs. men. Topic and timing are mixed in, so it's a pattern, not a cause.
- **No reader data:** only counts per package. We can say how headlines about women perform, not who clicked.
- **Images are IDs only,** so the gender of a pictured person is unknown.
- **Particular audience:** socially engaged Facebook users, 2013–15. Findings describe them, not advertising audiences in general.

---

## 2. Decisions log

| Date | Decision | Why |
|---|---|---|
| 2026-11-04 | Project 2 dataset = **Upworthy Research Archive**. Rejected: Hillstrom email test, Criteo uplift, fast-food promotions (Sanjay: none fit); voice-gender ad data (no public raw data exists); Kline–Rose–Walters hiring audit (application-level access unconfirmed); ACS pay gap (no A/B test) | Real marketing experiments at scale, a meaningful gender question, and real work for every showcase skill |
| 2026-11-04 | **Gender angle:** does centering a woman in a headline change clicks; report the within-test (causal) and across-test (descriptive) designs separately | Randomization only covers within-test comparisons |
| 2026-11-04 | **Data split:** develop every definition and analysis on the **exploratory** set; lock it; run once on the **confirmatory** set for the headline results; never touch the **holdout** | The archive's intended use; protects results from being tuned to the data. Profiling of data *quality* (counts, keys, randomization) may cover all splits; nothing that compares click rates by headline content touches confirmatory until definitions are locked |
| 2026-11-04 | Raw data = Sanjay's OSF download, copied untouched to `data/raw/osf_jd64p/`; SHA-256 of every file in `docs/raw_checksums.txt` | Prove the raw files never change (rule 5) |
| 2026-11-04 | **The package files are the March 2020 release** and lack the 2024 randomization flag; Sanjay checked OSF and found no newer package files. We detect broken randomization ourselves (P10) and compare with the authors' published window | The flag column the paper describes isn't in the files available |
| 2026-11-04 | **Text features come from established, citable tools where possible** (Sanjay), not a word list we invent; our own list is the fallback. Every tool is validated against a hand-labeled exploratory sample before use | Credibility and reproducibility; see §5 |
| 2026-11-04 | **Python 3.11+ for this project** (Sanjay approved installing a newer Python on his Mac). Olist stays on 3.7 | spaCy and other text tools no longer support 3.7 (end of life 2023) |
| 2026-11-04 | **Document the process as we go, including how tools were chosen** (Sanjay) | Rule 6; the case study's "how it was done" section |
| 2026-11-10 | **Topics are yes/no tags (several per headline), LGBTQ+ merges with women & gender equality, gender and sentiment definitions kept** (Sanjay, after labeling 100 headlines; §5.3) | Many headlines genuinely span two topics; single-choice labels forced arbitrary picks |
| 2026-11-04 | **Headline variables to build (Sanjay):** sentiment as positive / neutral / negative, and a topic variable. **Hypothesis H2:** readers respond to *combinations* of gender and topic differently than to gender alone. Definitions, tools and thresholds to be proposed for approval (rule 2) | Effects may be hidden or reversed when averaged across topics |
| 2026-11-04 | **Reader-facing variables use only what the reader saw before clicking** (Sanjay): the headline, plus the excerpt where shown. The article's opening paragraph (`lede`) is not used for them. Verified on the archive's screenshots: the tested units are tiles in the sidebar and under articles showing an image, the headline and sometimes the excerpt; the lede appears only after the click. Topic is therefore measured from each headline ("perceived topic"), so it can differ between versions in the same test | A reader can only react to what's on the tile |

---

## 3. Profiling (step 2)

### 3.1 Approved profiling definitions (approved by Sanjay 2026-11-04 22:53)
| # | Check | Definition | Files |
|---|---|---|---|
| P1 | Row counts | Rows per file, two independent ways: pandas and Python's `csv` module (text fields contain line breaks, so line counts are wrong) | 4 package files |
| P2 | Columns and types | Names, inferred types, differences between files | 4 |
| P3 | Keys and duplicates | Unique row id (unnamed column / `_id`); exact duplicate rows; packages identical in every content field within one test | 4 |
| P4 | Split integrity | Each test id in exactly one split; test and package counts vs. published figures | 3 splits |
| P5 | Missing values | Missing or empty per column, incl. empty headlines | 4 |
| P6 | Ranges | Impressions and clicks are integers ≥ 0; clicks ≤ impressions; zero-impression packages; click rate min / median / max | 3 splits |
| P7 | Dates | `created_at` and `test_week` range; `test_week` coding; `updated_at` = 2016 system update, not a test date | 3 splits |
| P8 | Test structure | Packages per test; single-package tests; impressions per test | 3 splits |
| P9 | What each test varies | Per test: headlines differ, images differ, or both | 3 splits |
| P10 | Randomization (sample ratio mismatch) | Per test, chi-square goodness-of-fit of impressions against an equal split; flagged if p < 0.001; report the imbalance size too; compare flag rate inside vs. outside June 25, 2013 – January 10, 2014. If the data shows deliberate unequal allocation, stop and ask | 3 splits |
| P11 | Repeated headlines | Same headline text in more than one test | 3 splits |
| P12 | Text quality | Headline length (characters, words); HTML entities, curly quotes, odd characters, non-English text | 3 splits |
| P13 | Gender feasibility preview | Rough draft word list; share of headlines with female / male terms; number of tests where some arms use female terms and others don't. Counts only, no click rates. Not the final classifier | **Exploratory only** |
| P14 | Google Analytics files | Date coverage, missing values ("N/A"), number formats | 3 GA files |
| P15 | Fields not analyzed | Distributions of `significance`, `first_place`, `winner`, `square`, `share_text` for the data dictionary | 3 splits |

### 3.2 The chi-square check, explained (P10; taught to and approved by Sanjay 2026-11-04)
- **Question:** are the observed impressions per arm too far from an equal split to be luck? A large gap means randomization broke, and the test can't be used causally.
- **Statistic:** χ² = Σ (O − E)² ÷ E, with E = test impressions ÷ arms. Squaring stops positive and negative gaps cancelling and weights big gaps; dividing by E scales each gap to what is normal at that size.
- **p-value:** from the chi-square distribution with df = arms − 1: the chance of a χ² at least this large if assignment were fair.
- **Worked examples (3 arms, 10,000 impressions):** 3,400 / 3,350 / 3,250 gives χ² = 3.50, p ≈ 0.17 (normal wobble). 5,000 / 2,500 / 2,500 gives χ² = 1,250, p ≈ 0 (broken).
- **Why p < 0.001, not 0.05:** across 4,873 exploratory tests, 0.05 would falsely flag about 244 fine tests; 0.001 about 5. Large samples make trivial imbalances "significant", so the imbalance size is reported beside every flag.
- **Assumptions:** independent sessions; equal intended split (checked, not assumed); expected count ≥ 5 per arm (smaller tests are noted, not tested).
- **Used again later** for the A/B question itself (headline × clicked tables).

### 3.3 Findings (profile run 2026-11-04; full results in `docs/data_profile.md`)
1. **The files are complete.** Row, test and package counts match the published figures exactly in all three splits; no test appears in two splits; row ids are unique; no exact duplicate rows.
2. **Our randomization check independently reproduces the authors' 2024 finding.** 70% of tests starting June 25, 2013 – January 10, 2014 fail the chi-square check, vs. 0.2–0.5% outside it (close to the ~0.1% expected by chance). By month the failures start in June 2013, peak in November (87%) and stop in January 2014. The window holds 22% of tests, matching the authors' "about 22%", so their flag appears to cover the whole window. A handful of tests outside it also fail (18 exploratory). Flagged tests are only mildly uneven (median largest arm 1.07× its fair share), so this is a systematic skew, not one arm getting everything.
3. **What tests vary decides what they can tell us.** Of 4,873 exploratory tests: headline only 2,307; image only 1,426; both 300; neither 840. Of the "neither" tests, 302 are identical in every content field: effectively **A/A tests**, a free check of our A/B method's false-positive rate. Only tests where headlines vary can say anything about headline wording.
4. **Typical test:** 4 arms (2–14), ~14,400 impressions in total, ~3,100 per arm; median click rate 1.25%. No zero-impression arms; 12 arms with zero clicks.
5. **Duplicates and reruns:** 1,491 exploratory packages repeat another package's content within the same test; 872 headline texts appear in 2+ tests (reruns).
6. **Text needs cleaning:** curly quotes and em dashes (common), zero-width spaces (68), non-breaking spaces, HTML tags in 49 headlines (`<strong>`, `<br>`, `<span>`), 400 with leading or trailing spaces, 103 with double spaces. One holdout headline is empty. 22 exploratory packages have no image id. No headlines in a non-Latin script (checking for other languages comes with the text tools).
7. **Timestamps come in two formats** (with and without fractional seconds). See §6: this caught a parsing bug.
8. **The gender design is feasible.** With a rough draft word list (exploratory only, counts only): 21.5% of headlines have a female term and 20.7% a male term. **571 tests** have female terms in some arms but not others, the cases the causal within-test design needs (before removing the broken-randomization window). The final classifier comes from the tools in §5.
9. **Columns not used** behave as documented: `significance` runs 0–100 and isn't a p-value; editors picked a `winner` in only 1,150 of 4,873 tests.
10. **Google Analytics:** 850 days, complete for pageviews; sessions and pageviews are "N/A" on 304 days in the users file. Context only.

---

## 4. Load and cleaning rules (steps 4–5, approved by Sanjay 2026-11-04 23:30)

Principle (as in Project 1): **flag, don't delete.** Every package row is kept; problems become flag columns; raw text stays beside cleaned text; each analysis states which flags it excludes. Counts per split are generated on every build in `docs/cleaning_log.md`; exploratory counts below.

### 4.1 Load rules (`pipeline/01_load/load.py`)
| ID | Rule | Why |
|---|---|---|
| L1 | Read every column as text, then type explicitly (impressions, clicks, test_week integers; winner, first_place True/False); empty text → missing | No silent type guessing |
| L2 | Timestamps parsed as ISO 8601, accepting both formats in the data | The profiling catch: 896 exploratory dates would otherwise go blank |
| L3 | Add `split`; load exploratory and confirmatory; **the holdout file isn't even listed in the code** | Holdout untouched by construction (R2) |
| L4 | **Confirmatory lock, enforced in code:** `pipeline/common.load_table` refuses confirmatory rows unless `LOCK.md` records "Approved by Sanjay: <date>". Load, cleaning and their tests are content-blind (never look at clicks by content or headline meaning) and declare `content_blind=True` | Makes "we didn't peek" provable (Sanjay chose code enforcement) |
| L5 | Undeployed file not loaded | No impressions or clicks |

### 4.2 Cleaning rules (`pipeline/02_clean/clean.py`)
| ID | Rule | Exploratory | Used how |
|---|---|---|---|
| S1 | Test start (earliest `created_at`) in 2013-06-25 – 2014-01-10 → `in_problem_window` | 1,050 tests | Excluded from causal results; kept for descriptive |
| S2 | Chi-square randomization check p < 0.001 → `srm_fail` | 753 (18 outside the window) | Excluded from causal results. `usable_causal` = neither S1 nor S2: **3,805 tests** |
| S3 | `headline_clean`: decode entities, remove HTML tags, zero-width characters, nbsp → space, curly → straight quotes, collapse spaces, trim; wording and case unchanged; raw `headline` kept | 2,474 headlines changed | All text features read `headline_clean` |
| S4 | Empty cleaned headline → `headline_missing` | 0 | Excluded from text features |
| S5 | Same reader-facing content (cleaned headline, image, cleaned excerpt) within a test → shared `variant_id` | 2,019 packages share a variant; 21,122 variants | **Sanjay's choice:** randomization check uses package rows; headline effects sum duplicates into one variant (same treatment, no double counting) |
| S6 | What a test varies → `varies`; one variant only = **A/A test** | headline only 2,053 · headline+image 295 · headline+excerpt 250 · image only 1,431 · excerpt only 508 · A/A 336 | Headline effects only from the 2,598 tests where headlines vary; A/A tests check the false-positive rate |
| S7 | `headline_n_tests` = tests using the same cleaned headline | 5,382 packages in reruns | Kept; accounted for in regression |
| S8 | Missing `eyecatcher_id` → `image_missing` | 22 | Kept as "unknown image" |
| S9 | `excerpt_clean` (S3 rules); `excerpt_is_stock` | 11,490 stock · 2,442 empty | Reader-facing (R8): candidate control |
| S10 | Zero-click packages kept | 12 | Valid results |
| S11 | Test week = week of its first package | 26 tests span 2 weeks | Documented |
| S12 | Kept, not used: significance, first_place, winner, square, share_text, slug, updated_at, lede | | Data dictionary |

**Refinements made while building (within the approved rules):**
- **Excerpt in S6.** The excerpt is reader-facing (R8), so a test where only the excerpt differs is labeled "excerpt only", not A/A. A/A therefore means identical *to the reader*: 336 tests. (The profile's 302 also required identical ledes, which readers never saw.)
- **Table format.** Build tables are saved as gzip CSV with a column-type manifest, not Parquet: the AI workspace can't install the Parquet library. They reload with identical types and open anywhere.

---

## 5. Tool selection (how the text tools were chosen)

Sanjay asked to use established packages for sentiment, word choice and gender rather than a word list we write ourselves, and to document how they were chosen. Candidates found 2026-11-04, before any were tested:

| Need | Candidate | What it does | Status / notes |
|---|---|---|---|
| Gendered words | **Microsoft GenBit word lists** (github.com/microsoft/responsible-ai-toolbox-genbit) | Curated female, male and non-binary gender-definition word lists, built to measure gender bias in text | **Shortlisted.** Its score works on whole corpora (400+ documents), not single headlines, so we use the lists, not the score. Repo archived (read-only) June 2026; license to confirm |
| People's names | **spaCy** named-entity recognition | Finds person names in text | **Shortlisted** |
| Name → gender | **nomquamgender** (pypi.org/project/nomquamgender; arXiv 2208.01714) | Probability a first name is used by women or men, with an uncertainty score, from a published method | **Shortlisted.** Measures how a headline presents someone, not gender identity |
| Name → gender (fallback) | **gender-guesser** | Offline first-name dictionary (male / female / mostly / androgynous / unknown) | Fallback |
| Sentiment | **VADER** (github.com/cjhutto/vaderSentiment) | Sentiment scorer built for short social-media text | **Shortlisted** |
| Emotions | **NRC Emotion Lexicon** | Words tagged with anger, fear, sadness, joy and more | **Shortlisted.** A 2023 *Nature Human Behaviour* study of this archive's confirmatory set used dictionary-based scores and found negative words raise clicks (~2.3% per word); we can reproduce that as validation |
| Word choice | **textstat**, spaCy parts of speech, simple counts | Reading level; questions, numbers, "you", length | **Shortlisted** |
| Backup | Our own word list | Agreed by Sanjay and the AI | Only if the tools fail validation |

**Selection rule:** a tool is adopted only after it is run on a hand-labeled sample of about 200 exploratory headlines and its accuracy, precision and recall are reported and approved. License and maintenance status are recorded for each.

### 5.1 Hand-label validation sample (2026-11-04)
- **Sample** (`pipeline/03_features/sample_for_labels.py` → `docs/validation/label_sample.csv`): 200 distinct cleaned headlines from exploratory variants, fixed seed 20261104, stratified with the P13 draft word list so rarer gender cases are covered: 70 with a female term, 50 with a male term only, 80 with neither (population shares 20.6% / 14.5% / 64.8%, saved so accuracy can be re-weighted).
- **Codebook** (`pipeline/03_features/codebook.py`, **draft for Sanjay's approval**): gender focus (female / male / both / none), sentiment (positive / neutral / negative; judged on the whole headline, a set-up-and-resolve headline labeled by the note it ends on), perceived topic (13 topics + "unclear from the headline"). Judged only from what the reader saw (R8). The topic list was drafted by the AI from reading the sample, because the planned discovery pass (BERTopic) can't run yet (see 5.2).
- **Labels:** Sanjay chose to have the AI draft labels for him to correct (R10). `docs/validation/ai_draft_labels.csv` holds the AI's draft (26 marked unsure); `docs/validation/label_review.xlsx` is the review sheet, where Sanjay's corrected "Final" columns become the reference labels. A formula counts how many AI labels he changed, so the AI-vs-human agreement is itself reported. **Caveat:** reviewing a draft can anchor the reviewer toward it, so the case study will say the labels are AI-drafted and human-corrected.
- **AI draft distribution:** gender none 71 · male 59 · female 57 · both 13; sentiment positive 90 · negative 57 · neutral 53; most common topics: women & gender equality 31, unclear 24, health 20, politics 17, entertainment 17.

- **Labeling app (2026-11-09, R11).** At Sanjay's request the review became a flash-card app (artifact "Headline Labeler"): one headline at a time, gender → sentiment → topic as one-question-at-a-time buttons (keyboard shortcuts too), a green flash when a headline is done, then a side-by-side comparison with the AI draft and running agreement per field, plus a counter of headlines done. Each answer is saved to the app's database as soon as the third question is answered (`answers/<sample_id>`: the three labels, seconds taken, timestamp, codebook version). `scripts/sync_labels.py` copies the saved answers into `docs/validation/human_labels.csv` and the Final columns of `label_review.xlsx`.
- **Method improvement:** the app shows the AI's labels only *after* Sanjay answers, so his labels are now **blind** to the AI draft, which removes the anchoring caveat above. Agreement between his blind labels and the AI draft becomes a reported result in its own right.

### 5.3 Validation results and the change of approach (2026-11-10)
Sanjay labeled the first **100** of the 200 sample headlines in the Labeler, blind to the AI draft, and judged 100 enough to assess quality (median 28 seconds per headline). The sample was shuffled before labeling, so the first 100 are a random half; they contain 32 female-term, 26 male-term-only and 42 neither headlines. Agreement between his labels and the AI draft (Cohen's kappa corrects for agreement expected by chance; 0.6–0.8 is "substantial", above 0.8 "almost perfect"):

| Field | Agreement | Cohen's kappa | Where they differed |
|---|---|---|---|
| Gender focus | 95% | 0.93 | 5 cases, 4 of them involving "both" (e.g. Sanjay "both", AI "none") |
| Sentiment | 72% | 0.58 | 24 of 28 differences involve "neutral" (one says neutral, the other positive or negative); 4 are true polarity flips (positive vs. negative) |
| Topic (single label) | 78% | 0.76 | Mostly headlines that fit two topics (human interest vs. economy or entertainment; unclear vs. human interest or entertainment) |

**Sanjay's conclusions:** he is satisfied with gender and sentiment. For topic, neither label is wrong when they differ: many headlines belong to more than one topic, and a single-choice label forces an arbitrary pick.

**Changes to the approach (decided by Sanjay):**
1. **Topics become yes/no tags (dummy variables), not one category (R12).** Each headline gets a column per topic and can carry several. This also changes the regression design: each topic enters as its own 0/1 term, and gender × topic interactions are estimated per topic tag.
2. **LGBTQ+ and Women & gender equality merge** into one tag, "Gender equality & LGBTQ+" (R13; Sanjay noted this mid-quiz on Nov 9 and asked to apply it afterwards). 12 topic tags; a headline with none is "unclear".
3. **Classify every headline** with the validated method, then proceed to the analysis.
Codebook v2 is in `pipeline/03_features/codebook.py`; v1 is kept as the record of the validation round.

**Noted for the write-up (AI's flags, not changes):** sentiment agreement is moderate. Almost all disagreement is about where "neutral" ends, which is a known difficulty for headlines, and positive-vs-negative flips are rare (4%). Analyses should therefore report sentiment effects as positive vs. negative with neutral as the reference, and say how often the boundary is ambiguous. The multi-tag topic method needs its own check before the full run: Sanjay's single topic should appear among the tags for nearly every headline (see the production validation, to come).

### 5.2 Blocker: the text tools can't be installed here (2026-11-04)
Neither the AI workspace nor the shell on Sanjay's Mac can reach PyPI, GitHub file downloads or Hugging Face (the network allowlist refuses them), so VADER, spaCy, nomquamgender, the GenBit lists, BERTopic and the transformer models can't be installed by the AI. Options: (a) Sanjay allows those domains in claude.ai Settings › Capabilities; (b) Sanjay installs the packages on his Mac in Terminal and runs the feature scripts, which the AI writes. **Outcome (2026-11-10):** superseded by §5.4; the classifier is Claude with fixed instructions.

### 5.4 The production classifier: Claude with fixed instructions (2026-11-10)
**What changed from the plan (R14).** The plan (R3) was to compare established, citable tools (VADER, spaCy, nomquamgender and others) against the hand labels. Those packages still can't be installed here (§5.2), and meanwhile the AI's own labels were tested against Sanjay's blind labels and he judged them good enough (§5.3). So the classifier is Claude, given the same fixed written instructions for every headline. The established tools stay as a possible comparison later, not a requirement.

**Why this is defensible, and its limits:**
- The definitions are written down once (`pipeline/03_features/codebook.py`), turned into one fixed prompt by `make_classifier_inputs.py` (`prompt.json`), and used unchanged for every headline, so the labels are reproducible in method even though a language model can answer slightly differently on a re-run.
- It is validated the same way a package would have been: against Sanjay's 100 blind labels, before any full run (step 1 of the page).
- Limits for the write-up: a language model is not a published, versioned tool; another researcher re-running it may get slightly different labels; and the validation sample is 100 headlines from the exploratory split.

**How it runs.** The Headline Classifier page (an artifact with the `sample` capability, so calls run on Sanjay's Claude account, and a database where each finished call is saved):
1. **Check:** run the prompt on the 100 labeled headlines with the quick and the default model; the page shows agreement with Sanjay next to the v1 numbers. Topic match = his single topic is among the tags (LGB/WOM map to GEN; "unclear" matches no tags).
2. **Exploratory:** 14,465 distinct reader-facing texts (from 22,666 packages), 60 per call → 242 calls.
3. **Confirmatory:** only after `LOCK.md` records Sanjay's approval (L4); the data file isn't even published before that. About 4 times the exploratory volume.

**Unit.** One distinct reader-facing text: cleaned headline plus the excerpt shown under it. Stock (boilerplate) excerpts are left out of the text, so packages that differ only by a stock excerpt share one label. Each unit has a stable key that joins labels back to packages (`build/03_features/units.csv.gz`).

**Checks built into the page:** every answer must have one entry per headline, in order, using only the allowed codes; otherwise the call is skipped (not retried automatically) and a later Run tries it again. A run stops after three failed calls in a row or any usage-limit error.

---

## 6. Validation log

| Date | Step | Check | Result | Detail |
|---|---|---|---|---|
| 2026-11-04 | setup | Raw files copied to the project; SHA-256 recorded; staged copies in the AI workspace re-verified against them | ✅ pass | 7 data files match |
| 2026-11-04 | profile | P1–P15 run by `pipeline/00_profile/profile.py`; independent standard-library re-derivation (`scripts/checks/verify_profile.py`: own chi-square and p-value code, no scipy) of row counts, tests, impression and click totals, randomization flags and gender-term shares for every split | ✅ pass | 23 of 23 numbers match |
| 2026-11-04 | profile | **Test the tests:** three values in the results file changed on purpose (a flag count +1, a click total −1, a term share +0.01) | ✅ caught | All 3 failed as expected |
| 2026-11-04 | profile | **Catch: timestamp parsing.** About 4% of `created_at` values have no fractional seconds, and pandas' default parsing turned them into blanks (896 exploratory rows). Found when a spot check failed on the undeployed file. Fixed by parsing as ISO 8601; the earliest date moved from May 23, 2013 to Jan 24, 2013 (matching the paper). Flags and window counts were unaffected because the independent check had parsed them separately | ✅ fixed | Becomes a cleaning rule |
| 2026-11-04 | load + clean | 15 tests (`tests/test_01_02_load_clean.py`): row counts vs raw; counts and dates typed without loss; raw headline byte-identical; no rows deleted; headline_clean free of tags, entities, zero-width, nbsp, curly quotes and stray spaces; letters and digits unchanged by cleaning; S1 and S2 equal the profile's independent counts; usable_causal definition; variants uniform inside and distinct between; one S6 label per test; test totals tie to packages; flags copied to packages; S8/S9 flags; **L4 lock blocks confirmatory and allows exploratory** | ✅ 15/15 pass | |
| 2026-11-04 | clean | Independent standard-library re-implementation of S1, S2, S3, S5, S6 from the RAW files (`scripts/checks/verify_clean.py`), both splits | ✅ 24/24 match | |
| 2026-11-04 | clean | **Mutation test** on a throwaway copy: (1) window end moved to Jan 31, 2014; (2) zero-width characters kept; (3) variants ignore the image; (4) zero-click rows deleted | ✅ all 4 caught | 6 tests failed (S1/S2 vs profile, clean text, variants, S6 labels, no rows deleted). Copy deleted |
| 2026-11-04 | build | **Catch: the independent cleaning check imported the profile check, which ran its own checks and exited**, so the cleaning check never ran in the first build. Found because its output was missing. Moved the shared chi-square code to `scripts/checks/stats_stdlib.py` | ✅ fixed | Both checks now run in every build |

| 2026-11-10 | features | **Blind agreement, AI draft v1 vs. Sanjay, first 100 of the 200-headline sample** (`docs/validation/human_labels.csv`, computed from the Labeler export via `scripts/sync_labels.py`) | ✅ gender 95% (κ 0.93); sentiment 72% (κ 0.58); topic 78% (κ 0.76) | Sentiment differences are mostly neutral vs. not (24 of 28); topic differences mostly headlines that fit two topics. Led to R12–R14 (§5.3) |
| 2026-11-10 | features | Classifier page tested in a headless browser with a fake Claude: every call saved, validation table scored, resume skips finished calls, no sideways scroll at phone width | ✅ pass | Real agreement numbers come from Sanjay's step-1 run |

---

## 7. AI log

| Date | Step | AI did | Sanjay decided / changed |
|---|---|---|---|
| 2026-11-04 | Dataset search | Proposed Hillstrom, Criteo, fast food; then searched for gender and marketing datasets; found no public voice-gender ad data; proposed Upworthy, the Kline–Rose–Walters audit and ACS | Rejected the first three; asked for gender-related data; chose Upworthy and the women-in-headlines angle |
| 2026-11-04 | Step 0 | Read the archive site, the *Scientific Data* paper and the 2024 update; wrote the business context and caveats; flagged that subject gender rarely varies within a test | Approved; created the GitHub repo; downloaded the archive |
| 2026-11-04 | Step 1–2 | Set up the project folder and checksums; found the files predate the 2024 flag; proposed profiling checks P1–P15 | Asked for a chi-square lesson (math and application) before approving; asked to find established text tools instead of our own word list; approved the data split, the checks and a newer Python |
| 2026-11-04 | Step 2 | Wrote the profile and an independent standard-library check; caught a timestamp-parsing bug; reproduced the authors' randomization finding; found A/A tests; wrote the data dictionary | Approved; added sentiment (3 classes) and topic variables with a gender × topic hypothesis (R7); pointed out readers never saw the opening paragraph (R8) |
| 2026-11-04 | Steps 4–5 | Proposed load rules L1–L5 and cleaning rules S1–S12 with counts; built load, cleaning, 15 tests, an independent check, a generated cleaning log and the confirmatory lock; mutation-tested | Chose to sum duplicate versions for headline effects but keep them separate for the randomization check; chose code enforcement of the confirmatory lock |
| 2026-11-09–10 | Hand labels | Built the gamified Labeler (blind; AI answer shown only after each answer), arrow-key navigation, sync script; computed agreement on the 100 labels | Labeled 100 headlines and judged it enough; accepted gender and sentiment; changed topics to multi-tag dummies (R12); merged LGBTQ+ into gender equality (R13) |
| 2026-11-10 | Classifier | Proposed Claude with a fixed prompt as the production classifier, since the packages can't be installed (R14); wrote codebook v2, the input builder and the Classifier page; flagged moderate sentiment agreement and that the multi-tag method needs its own check | Asked to classify every headline, then move on to the analysis |
