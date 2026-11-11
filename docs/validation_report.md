# Validation Report

Generated 2026-11-04 23:39 by `scripts/build.py`. Each test returns zero failing rows when it passes.

| File | Test | Result | Failing rows |
|---|---|---|---|
| test_01_02_load_clean.py | `test_clean__every_test_has_one_s6_label` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__flags_copied_to_packages` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__headline_clean_is_clean` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__headline_clean_keeps_wording` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__no_rows_deleted` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__s1_window_matches_profile` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__s2_flags_match_profile` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__stock_excerpt_and_missing_flags` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__test_totals_tie_to_packages` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__usable_causal_definition` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_clean__variants_are_identical_inside` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_load__counts_and_dates_typed_without_loss` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_load__raw_headline_unchanged` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_load__row_counts_match_raw_files` | ✅ pass | 0 |
| test_01_02_load_clean.py | `test_lock__confirmatory_blocked_without_approval` | ✅ pass | 0 |

**`test_clean__every_test_has_one_s6_label`**: S6: each test gets exactly one `varies` label; A/A tests are exactly the tests with a single variant.

**`test_clean__flags_copied_to_packages`**: Every package carries its test's S1/S2/S6 flags unchanged.

**`test_clean__headline_clean_is_clean`**: S3: headline_clean has no HTML tags or entities, zero-width chars, nbsp, curly quotes, double or edge spaces.

**`test_clean__headline_clean_keeps_wording`**: S3: cleaning only removes markup and normalizes spacing/quotes: the letters and digits are unchanged
once tags are dropped (checks that no word was altered or lost).

**`test_clean__no_rows_deleted`**: Flag, don't delete: the clean table has exactly the loaded rows.

**`test_clean__s1_window_matches_profile`**: S1: tests flagged in the window = the profile's independent count (P10, tests with 2+ arms) for each split.

**`test_clean__s2_flags_match_profile`**: S2: chi-square failures (all, and outside the window) = the profile's counts for each split.

**`test_clean__stock_excerpt_and_missing_flags`**: S8/S9: image_missing = no eyecatcher_id; excerpt_is_stock = cleaned excerpt equals the stock phrase.

**`test_clean__test_totals_tie_to_packages`**: Tests table: impressions and clicks per test equal the sum of its packages; package counts match.

**`test_clean__usable_causal_definition`**: S1+S2: usable_causal is true exactly when a test is outside the window and passes the randomization check.

**`test_clean__variants_are_identical_inside`**: S5: packages sharing a variant_id have identical headline_clean, image and excerpt_clean, and belong to one test;
packages in different variants of the same test differ in at least one of them.

**`test_load__counts_and_dates_typed_without_loss`**: L1/L2: impressions, clicks and test_week equal the raw text exactly; every created_at parsed (none blank).

**`test_load__raw_headline_unchanged`**: L1/S3: the raw `headline` column survives load and cleaning byte for byte (empty text -> missing only).

**`test_load__row_counts_match_raw_files`**: L1/L3: every raw row is loaded once per split, and the holdout is absent.

**`test_lock__confirmatory_blocked_without_approval`**: L4: without LOCK.md, reading confirmatory rows from a build table raises an error, while exploratory reads work.
