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

**Locked 2026-11-10 (R15, R16).** Sanjay approved the classifier lock after the check: default model; sentiment keeps "label the note it ends on" (he had labeled the setup on 6 such headlines and chose the codebook rule). `LOCK.md` stage 1 freezes the codebook, the prompt (by SHA-256) and the unit, and opens only the confirmatory headline text, through `load_text_for_classifier`, which removes every outcome column. Confirmatory: 58,613 units, 977 calls. Clicks in confirmatory stay locked until stage 2 (the analysis definitions).

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

| 2026-11-10 | features | **Classifier (codebook v2) vs. Sanjay's 100 blind labels**, both model tiers (`docs/validation/classifier_validation.md`) | ✅ default chosen: gender 96% (κ 0.94); sentiment 71% (κ 0.56); Sanjay's topic among the tags 80%; 1.5 tags per headline | Quick was slightly worse on every measure. 6 of the 8 positive-vs-negative flips are "bad setup, good ending" headlines, where the classifier followed the codebook's "label the note it ends on" rule and Sanjay labeled the setup: a definition question for Sanjay, not a classifier error |
| 2026-11-10 | features | Exploratory run, default model: 242 of 242 calls, 14,465 units; every answer passed the page's checks; imported by `scripts/import_classifier_labels.py` (keys match the inputs in order, one label per unit, all 22,666 packages join to a label) | ✅ pass | Shares: gender none 52%, male 23%, female 20%, both 5%; sentiment positive 44%, negative 31%, neutral 26%; most common tags GEN 24%, ENT 21%, HUM 16%; 7% no topic |

| 2026-11-10 | analysis | **A/A check AA1–AA5** (`pipeline/04_analysis/aa_check.py`); independent re-computation from the raw file (`scripts/checks/verify_aa.py`); simulation of the test on fake A/A data | ❌ check fails: 26.1% false positives vs. 5% expected. ✅ code verified: 326 of 326 p-values match independently; simulated null 4.6%, simulated +50% effect detected 56% | Real overdispersion (φ ≈ 2), not a bug; calibration AA6 proposed (§8.1) |

| 2026-11-10 | analysis | **AA6 calibration**: φ and the empirical threshold re-derived independently from the raw file | ✅ φ 1.9636, threshold 5.3635 match; held-out false positives 5.5% / 8.6% | Close to 5% but somewhat over; dual reporting (a)+(b) |
| 2026-11-10 | features | Confirmatory labels imported: 977 of 977 calls, 58,613 units, keys match the inputs in order | ✅ pass | Confirmatory outcomes still locked (stage 2) |

| 2026-11-10 | analysis | **Main model M1/M2** (`felogit.py`, `main_effects.py`) validated: brute-force dummy fit, Mantel–Haenszel, planted effect, placebo (`verify_models.py`) | ✅ all pass | M1-φ cross-check 3.83 vs. expected ~2: flagged for Sanjay (§8.2) |

| 2026-11-10 | analysis | **Topic effects T1/T2** (`topic_effects.py`): Mantel–Haenszel check of the largest T1 effect; T2 with year instead of month fixed effects | ✅ MH −16.3% vs. model −17.0%; T2 direction stable for 10 of 12 topics, significance changes for politics and science | |

| 2026-11-11 | lock | **Bug found by the AI before the stage-2 run:** `require_lock` accepted "Approved by Sanjay:" anywhere in LOCK.md, so the stage-1 sentence describing the future line opened stage 2 from 21:38 to 00:11. Audit of every `load_table` call in that window (code and session log): only exploratory packages/tests and confirmatory headline text/labels were read; no confirmatory outcome | ✅ no confirmatory outcome read; fixed (line must start with "Approved by Sanjay: YYYY-MM-DD"); regression test `test_lock__only_a_dated_line_opens_stage_2` | 17 tests pass |
| 2026-11-11 | analysis | Confirmatory run; independent checks (`UPWORTHY_SPLIT=confirmatory`) | ✅ all pass after a checker fix | The independent A/A checker didn't strip zero-width characters, so one test whose excerpts differ only by an invisible character looked non-A/A to it; checker fixed, frozen analysis code unchanged |

| 2026-11-11 | report | Case-study page rendered in a headless browser at 1280 px and 390 px: no sideways scroll, 72 hover titles on chart marks, every placeholder filled; notebook executed end to end and reproduces the page's numbers | ✅ pass | Fixed after looking: two legend overlaps, a target label over a bar, "+0%" ticks, two coinciding dots in the framing chart |

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


---

## 8. Analysis (exploratory first; confirmatory only after LOCK.md stage 2)

### 8.1 A/A check: approved by Sanjay 2026-11-10 21:49 (AA1–AA5); run the same day
**Question:** when readers saw identical tiles, how often does our test call a difference "significant"? If our method is sound, about 5% of the time at the 5% level. More than that means our later A/B results would overstate real effects.
**Data:** the 326 A/A tests in exploratory that are `usable_causal` (336 A/A tests minus 10 in the problem window or failing the randomization check). Arms = the individual packages (S5: identical versions are separate rows for checks like this one); 2–9 arms per test, most 4–6, about 3,300 impressions and 50 clicks per arm.

| # | Calculation | Formula and grain | Pass rule |
|---|---|---|---|
| AA1 | Per-test p-value | Chi-square test of homogeneity on the arms × (clicked, didn't click) table; df = arms − 1. One p-value per test | Flag any test with an expected click count below 5 in an arm (counted, kept) |
| AA2 | False-positive rate | Share of the 326 tests with p < 0.05, with a 95% Wilson interval | The interval includes 5% |
| AA3 | Shape of the p-values | Share of p-values in each tenth (0–0.1, …, 0.9–1); a Kolmogorov–Smirnov test against uniform | Roughly 10% per tenth; KS p ≥ 0.05 |
| AA4 | Sensitivity | AA2 on all 336 A/A tests, including the 10 excluded ones | Reported, not a pass rule |
| AA5 | *(optional, descriptive)* Upworthy's own dashboard in A/A tests | Share of A/A tests where some arm's editor-facing `significance` score reached 95, and where editors picked a `winner` | Reported only; that score isn't a p-value (NOTES §1), so this is "what editors saw", not a statistical result |

**Validation:** an independent standard-library re-computation of AA1–AA2 (own chi-square code, as in `stats_stdlib.py`); a simulation check that the code finds about 5% on fake A/A tests built with identical click rates, and close to 100% when one arm's rate is raised by 50% (test the tests).

**Results (exploratory; `docs/results/aa_check.md`):** the check **fails**. 85 of 326 identical-tile tests come out "significant" at the 5% level: **26.1%** (95% interval 21.6–31.1%), about five times the 5% a sound test should give. The p-values pile up near zero (34% below 0.1, KS p < 0.001). Including the 10 excluded tests changes nothing (25.9%). Upworthy's own editor dashboard: some version scored 95+ in 97.9% of these identical tests, and editors picked a "winner" in 43.9%.

**Is it our code?** No. (1) The independent standard-library re-computation from the raw file matches all 326 p-values (`scripts/checks/verify_aa.py`). (2) On simulated A/A tests built with the real arm sizes and identical click rates, the same code finds 4.6% significant; with one arm 50% better it finds 56%.

**What it means:** click rates of identical tiles vary about twice as much as the simple coin-flip (binomial) model assumes. On average the chi-square statistic is 2.0 times its degrees of freedom (median 1.4; pooled 1.96). This is called *overdispersion*. Likely reasons, which the data can't separate: impressions aren't independent (the same readers see a tile repeatedly; traffic arrives in bursts from social shares), so each arm's click rate is noisier than its impression count suggests.
**Ruled out (quick diagnostics, exploratory):** the unseen lede differing (28% vs. 26% false positives); arms created at different times (94% within an hour); arm order (each arm's relative click rate 0.99–1.01 for the first six); uneven impressions (correlation with click rate 0.04); test size. `share_text` (social sharing text, not on the tile) differs in 315 of 326 tests, so it can't be tested.
**Consequence:** a naive A/B test on this archive would overstate how often headline changes matter. Any test we use for the gender analysis must be calibrated to these A/A tests first. Calibration AA6 below (approved).

**AA6, calibrate the test (approved by Sanjay 2026-11-10 23:33, after a walkthrough of quasi-binomial):**
- (a) *Recommended:* inflate the variance by the dispersion factor φ estimated from the A/A tests (pooled chi-square ÷ degrees of freedom = 1.96), the standard "quasi-binomial" correction, used in every later test and regression. Check: split the A/A tests in half at random, estimate φ on one half and measure the false-positive rate on the other, both ways. A preview gave 6.1% and 8.0%: close to 5% but a little over, because a few tests vary a lot more than the rest.
- (b) *Robustness:* an empirical threshold, the 95th percentile of the A/A tests' chi-square ÷ degrees of freedom, which gives exactly 5% on A/A by construction. Reported alongside (a).

**AA6 results** (`pipeline/04_analysis/aa_calibrate.py` → `build/04_analysis/calibration.json`, `docs/results/aa_check.md`): φ = **1.96** (uncertainty × 1.40). Split-half check: 5.5% and 8.6% false positives on held-out halves (φ 2.08 and 1.84 from the other half); 6.7% on all A/A tests. Empirical threshold (b): chi-square ÷ df > **5.36**. Independently re-derived (`verify_aa.py`: φ and threshold match). **Conclusion:** the correction brings false positives from 26% to roughly 5–9%; still somewhat above 5%, so findings count as robust only if they hold under both (a) and (b).

**How quasi-binomial works here (for the write-up):** each impression is treated as a coin flip (binomial), but A/A tests show identical tiles' click rates vary about twice as much as coin flips would, because impressions aren't independent (repeat viewers, bursts of shared traffic). Quasi-binomial keeps every estimate unchanged and multiplies the variance by φ, so standard errors grow by √φ; for chi-square tests the statistic is divided by φ. Example: an A/A test with chi-square 10 on 4 df has p = 0.04 uncorrected (a false alarm) but 10 ÷ 1.96 = 5.1, p = 0.28, corrected. φ is measured on A/A tests because there the true difference is zero, so all variation is noise. Limits: one φ for every test, while a few tests are much noisier; hence check (b). Heavier alternatives (beta-binomial, mixed models) are the fallback if (a) and (b) disagree.

### 8.2 Main analysis, headline effects within tests: approved by Sanjay 2026-11-10 23:42; run on exploratory the same night
**Questions:** H1, does centering a woman in a headline change its click rate compared with otherwise-competing headlines for the same story? H3, does sentiment? H2, does the gender effect differ by topic?
**Why within tests:** inside one test, the same story was shown to randomly split readers, so differences between versions are causal (rule: causal vs. descriptive). Topic belongs to the story, so it rarely varies inside a test: the design can test whether the gender effect *differs* by topic (H2), not whether some topics get more clicks (that is the descriptive, across-test analysis, later).
**Data (exploratory):** the 2,046 usable tests where the headline varies (1,623 headline only, 232 headline + image, 191 headline + excerpt), 9,575 variants (S5: identical versions summed). Gender varies in 915 tests (424 contain a female-centered version and a different one); sentiment varies in 1,190.

| # | Calculation | Detail |
|---|---|---|
| M1 | Logistic regression (binomial GLM) with **test fixed effects** | One row per variant; outcome clicks out of impressions; predictors gender (female, male, both; reference none), sentiment (positive, negative; reference neutral); one intercept per test, so versions are only compared within their test. Tests where nothing labeled varies drop out automatically |
| M1-H1 | The answer to H1 | Female vs. none, and female vs. male, as a relative change in click rate with a 95% interval (at ~1.5% click rates the odds ratio ≈ the rate ratio) |
| M1-a | Significance, method (a) | Quasi-binomial: variance × φ = 1.96 from the A/A tests |
| M1-b | Significance, method (b) | Placebo version of the A/A threshold: in the 326 A/A tests, give the arms fake gender and sentiment labels at random (1,000 times), fit M1 each time, and use the 97.5th percentile of the fake effects' |z| as the critical value. (The chi-square ÷ df threshold applies to whole-test tests, so for a regression the placebo is its equivalent) |
| M1-φ | Cross-check | φ estimated from M1's own residuals (Pearson chi-square ÷ residual df); expected near 2 |
| M2 | H2, gender × topic | M1 plus female × topic-tag interactions (12) and topic main effects. Holm correction across the 12; topics with fewer than 30 informative tests reported as "too few to say" |
| S1 | Sensitivity: headline-only tests | M1 on the 1,623 tests where nothing else varies (images or excerpts can't confound) |
| S2 | Sensitivity: label uncertainty | M1 with "both" merged into "female"; with "neutral" sentiment dropped |

**Validation:** (1) an independent estimate of H1 with a different method: stratified Mantel–Haenszel odds ratio of female vs. none within tests, standard library only; (2) planted-effect simulation: copy the data, give female-centered versions 10% more clicks by resampling, and check M1 recovers about +10%; (3) M1 on the A/A tests with fake labels shows nothing (part of M1-b).

**Tooling (decided 23:48, R19: option B):** the standard Python package for this (statsmodels) can't be installed here (PyPI is blocked, §5.2). Options: (A) Sanjay allows pypi.org and files.pythonhosted.org in claude.ai Settings › Capabilities, and we use statsmodels (established tool, R3); (B) the AI writes the fixed-effects logistic fit with scipy (profile the per-test intercepts, Newton steps on the few effects), validated against statsmodels run once on Sanjay's Mac.

**Tooling as built (R19):** `pipeline/04_analysis/felogit.py`, a fixed-effects logistic fit with numpy/scipy (per-test intercepts profiled out; Newton steps on the effects). Checked against a brute-force fit with one dummy column per test (largest coefficient difference 1.4e-06 on 150 tests; 1e-08 on simulated data with known effects). Reference check with statsmodels for Sanjay to run on his Mac: `scripts/checks/statsmodels_check.py`.

**Validation (`scripts/checks/verify_models.py`):** ✅ Mantel–Haenszel female vs. none +13.5% (M1, adjusted for sentiment: +12.4%); ✅ planted +10% recovered as +10.4% on average (8.3 to 12.1 over 20 runs); ✅ brute-force fit agrees. Placebo (M1-b): 1,000 fake-label fits on the A/A tests; critical |z| 3.19–3.53 (method (a) implies 2.75).

**Results (exploratory; `docs/results/main_effects.md`):**
- **Any person in the headline lifts clicks:** a woman +12.4% (95% interval 9.8 to 15.0), a man +13.2%, both +20.7%, all vs. headlines with no gendered person. Robust under (a), (b) and (c), headline-only tests and label variants.
- **H1, woman vs. man: no difference.** −0.7% (−3.6 to +2.3), p = 0.63. Centering a woman rather than a man neither helped nor hurt clicks.
- **H3, sentiment:** negative +4.7% vs. neutral (robust); positive −2.2% (significant under (a) and (b), not under (c), p = 0.07).
- **H2, gender × topic:** the woman effect is the same across topics except possibly education (+25.0% vs. about +11% elsewhere; passes Holm under (a), p = 0.001, but not under (c), p = 0.023). Environment: too few tests (25).

**⚠️ M1-φ cross-check did not land near 2:** the model's own dispersion is **3.83**. A/A tests contain only noise; real A/B tests also contain genuine headline-to-headline differences that our three labels don't capture, and those add variance. For claims about headlines *in general* (a woman-centered headline vs. a typical other one), that extra variation is real uncertainty, so (c) is the cautious choice. **Decision for Sanjay:** keep (a) as the main method as approved, or switch to (c) (φ from the model), with (a) and (b) reported alongside. Results that change: positive sentiment and the education interaction lose significance under (c); everything else is unchanged.

**Decision (R20, 2026-11-10 23:55):** Sanjay chose (c), φ estimated from the model itself (3.83), as the **main method** for every headline-effect result; (a) and (b) are reported alongside. A result is called robust only if it holds under (c) and (b). Under this rule: woman, man, both and negative tone are robust; positive tone (p = 0.07) and the education interaction (p = 0.023, Holm threshold 0.0045) are not.

### 8.3 Which topics get more clicks: approved by Sanjay 2026-11-10 23:59 (R21); run on exploratory
Sanjay asked whether some topics outperform others. Two different questions, answered two ways:

| # | Question | Design | Causal? |
|---|---|---|---|
| T1 | Does **framing** a story's headline around a topic get more clicks than other headlines for the same story? | M1 plus all 12 topic tags (0/1) in the within-test model; each tag's effect = headlines carrying it vs. versions of the same story that don't. Tags vary within tests often (123 tests for education to 392 for human interest). Holm across the 12; φ from the model (R20) | Yes (random split within tests) |
| T2 | Do stories **about** some topics get more clicks than stories about others? | One row per usable test (3,805): the test's total clicks out of impressions; topic tags = tags on the majority of its versions; logistic regression with one term per topic plus month fixed effects (click rates drifted over time); quasi-binomial φ from the model; Holm across 12 | No, descriptive: topics differ in promotion, traffic sources, timing and story quality |

Reported as % change in click rate vs. headlines/stories without that tag. Validation: Mantel–Haenszel cross-check for the largest T1 effect; T2 re-run with year instead of month fixed effects.

**Results (exploratory; `docs/results/topic_effects.md`):**
- **T1, framing (causal):** for the same story, a headline framed around **gender equality & LGBTQ+ gets +6.4% more clicks** (Holm-significant); framings around **environment (−17.0%), politics (−11.4%) and economy (−8.3%) get fewer** (all Holm-significant). Health −5.7% (p = 0.008, misses the Holm bar). Mantel–Haenszel check for environment: −16.3% vs. the model's −17.0%. Model φ = 3.79, close to M1's.
- **T2, story topic (descriptive):** stories about gender equality (+21%), entertainment (+15%), race/religion (+13%) and family (+12%) drew higher click rates; environment (−26%), economy (−21%), politics (−14%) and science (−12%) lower. Gender equality, entertainment, race, family, economy and environment hold with year instead of month fixed effects; politics and science don't. φ = 76.6: whole stories differ in click rate far more than coin flips, as expected for story-level comparisons; quasi-binomial accounts for it.
- **The two agree in direction:** gender-equality framing wins and environment/politics/economy framing loses both within stories (causal) and across stories (descriptive). The within-story result is the one that supports a recommendation to editors.

### 8.4 Confirmatory run (stage-2 lock approved by Sanjay 2026-11-11 00:11, R22): the results of record
Run once with the frozen code (`LOCK.md` lists its SHA-256 fingerprints), `UPWORTHY_SPLIT=confirmatory`. Outputs: `docs/results/confirmatory/`; exploratory outputs moved to `docs/results/exploratory/` (re-run after the move: identical numbers). Confirmatory is about 4–5× larger: 9,814 usable headline tests, 45,961 headline versions, 1,386 usable A/A tests.

| Result | Exploratory | **Confirmatory** | Replicates? |
|---|---|---|---|
| A/A false positives, uncorrected | 26.1% | **25.9%** | ✅ |
| A/A noise factor φ | 1.96 | **1.92** | ✅ |
| False positives after correction (held-out halves) | 5.5% / 8.6% | **6.8% / 6.3%** | ✅ |
| Upworthy dashboard: identical tests with a 95+ score | 97.9% | **97.0%** | ✅ |
| Woman-centered vs. no gendered person | +12.4% | **+8.9%** (7.2 to 10.6) | ✅ |
| Man-centered vs. none | +13.2% | **+7.4%** (6.0 to 8.8) | ✅ |
| Both vs. none | +20.7% | **+21.5%** (19.0 to 24.1) | ✅ |
| **H1: woman vs. man** | −0.7% (n.s.) | **+1.4%** (−0.5 to +3.3), p = 0.16 | ✅ no significant difference; any difference is at most about 3% |
| Negative vs. neutral | +4.7% | **+3.1%** (1.9 to 4.3) | ✅ |
| Positive vs. neutral | −2.2% (not robust) | **−1.6%** (−2.6 to −0.5), p = 0.005, passes (b) | ✅ now robust |
| H2: woman effect differs by topic | education only, not robust | **none robust** (science passes Holm under (a) only) | ✅ "same across topics"; education did not replicate |
| T1 framing: environment / economy / politics | −17.0% / −8.3% / −11.4% | **−16.2% / −9.6% / −7.6%** | ✅ |
| T1 framing: gender equality & LGBTQ+ | +6.4% | **−0.1%** | ❌ did not replicate |
| T1 framing: human interest | −0.7% | **−2.5%** (Holm-significant) | new |
| T2 story topic (descriptive) | gender equality, entertainment, race, family high; environment, economy, politics, science low | **same pattern** | ✅ |

**Validation on confirmatory:** ✅ independent A/A re-computation matches all 1,386 p-values, φ and the threshold; ✅ Mantel–Haenszel woman vs. none +9.4% (model +8.9%); ✅ planted +10% recovered +10.1%; ✅ brute-force fit agrees (6e-07); ✅ MH for environment framing −15.3% (model −16.2%).
**Notes:** AA4 counts 2 one-arm "A/A tests" (single version, so not real tests) as not significant; with them removed it is 365 of 1,484 = 24.6%, unchanged. The statsmodels reference check is run on exploratory only: confirmatory's 9,814 test dummies would need about 3.6 GB of memory as a dense matrix, and the implementation itself is what the check verifies.

**What this means for the write-up:** the confirmatory results are the findings. The exploratory gender-equality framing boost (+6.4%) is the classic example of why a held-out split matters: it looked significant after correction for 12 topics and vanished on fresh data.

---

## 9. Case study (R23, built 2026-11-11)

**What's in it:** `index.html` (the case-study page, generated) with four Python-made charts inlined as SVG, a hover tooltip on every mark and a data table under each chart; `notebooks/walkthrough.ipynb`, a companion notebook that reruns the core analysis on confirmatory (A/A check → calibration → main model → two checks).
**How it's built (no hand-typed numbers, R24):** `pipeline/05_report/figures.py` (matplotlib → `assets/figures/*.svg`, tooltips) → `pipeline/05_report/build_case_study.py` fills `case_study_template.html` from the result files and refuses to write the page if a placeholder is left unfilled → `pipeline/05_report/make_notebook.py` writes and executes the notebook (Jupyter isn't installed here, so the script runs each cell and stores its output). Page styles: the shared `assets/site.css` plus `assets/case-study.css`.
**Chart colors:** purple #4B3AA8 (causal/confirmatory) and orange #C2671B (descriptive), validated with the dataviz palette checker against white (all checks pass); gray = not significant, always labeled and in the tables.
**Structure (Sanjay's edit, R26):** 1 The question → 2 What we found (2.1 key findings & actions: people beat abstractions, framing costs, A/B tests need calibrating, gender last; 2.2 women vs. men; 2.3 topic framing) → 3 How the analysis was done (data & design, cleaning, the A/A check, labeling, model, validation, limitations, AI use).

**Corrections made while building:**
- **The dashboard "significance" hook was dropped.** The archive paper (Matias et al. 2021, Table 1) says the field is "NOT an estimate of statistical significance": a custom comparison with earlier tests whose meaning changed over time, with no documented threshold. The 97% "scored 95+" figure therefore says nothing about false positives and is not used on the page (AA5 stays in the results files, labeled descriptive). The paper also confirms Upworthy tested every article it published from Jan 2013 to Apr 2015 (32,487 experiments) and that the data came via Good, Inc.
- **Test counts on the page are the ones the model used:** one confirmatory test had zero clicks and drops out of the fit (9,813 tests / 45,957 versions used, of 9,814 / 45,961).
- **The gender × topic sentence uses the main method:** under the A/A φ, science passes Holm; under the model's φ (R20) no topic does, so the page says no topic differed.
- **An unsourced claim about Upworthy's audience** was replaced with a neutral limitation.
**Interactive labeler (R27):** §3.4 embeds `assets/labeler-demo.js`, a browser-only copy of the Headline Labeler: the 100 validation headlines (shuffled per visit), blind three-step questions, then the reader's answers next to the classifier's (default model) and Sanjay's blind labels, with a running agreement score. Data: `docs/validation/classifier_validation_items.json`, written by `scripts/import_classifier_labels.py`. The median labeling time on the page (28 seconds) is computed from `human_labels.csv`. Tested in a headless browser: click and keyboard paths, reveal, next card, phone width.

