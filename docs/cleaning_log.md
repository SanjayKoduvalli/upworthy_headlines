# Cleaning Log

Generated 2026-11-04 23:39 by `scripts/build.py` from `build/02_clean/cleaning_audit` (computed in `pipeline/02_clean/clean.py`). Every number is measured from the data on each build.

**Principle: flag, don't delete.** Every package row is kept; problems become flag columns, raw text stays beside cleaned text, and each analysis states which flags it excludes. Rules approved by Sanjay 2026-11-04 (NOTES §4.2).

## Confirmatory

| Rule | What | Table | Action | Affected | Of | Why |
|---|---|---|---|---|---|---|
| S1 | Test starts in the broken-randomization window (2013-06-25 – 2014-01-10) | tests | flagged | 4,907 | 22,743 | Archive 2024 update; excluded from causal results |
| S2 | Fails the chi-square randomization check (p < 0.001) | tests | flagged | 3,530 | 22,743 | Unequal assignment; excluded from causal results |
| S2 | …of which outside the window | tests | flagged | 92 | 22,743 | <NA> |
| S1+S2 | Tests usable for causal results | tests | flagged | 17,744 | 22,743 | <NA> |
| S3 | Headline changed by cleaning | packages | cleaned copy | 11,268 | 105,551 | Raw headline kept unchanged |
| S3 | …HTML tags removed | packages | cleaned copy | 132 | 105,551 | <NA> |
| S3 | …zero-width characters removed | packages | cleaned copy | 202 | 105,551 | <NA> |
| S3 | …curly quotes straightened | packages | cleaned copy | 8,885 | 105,551 | <NA> |
| S3 | …extra or untrimmed spaces fixed | packages | cleaned copy | 2,441 | 105,551 | Rows can count twice |
| S4 | Headline empty after cleaning | packages | flagged | 0 | 105,551 | Excluded from text features |
| S5 | Packages sharing a variant with another package | packages | flagged | 8,988 | 105,551 | Summed into one variant for headline effects |
| S5 | Variants | packages | none | 98,704 | 105,551 | Distinct reader-facing versions |
| S6 | Test varies: headline only | tests | flagged | 9,933 | 22,743 | <NA> |
| S6 | Test varies: headline+image | tests | flagged | 1,402 | 22,743 | <NA> |
| S6 | Test varies: headline+excerpt | tests | flagged | 1,098 | 22,743 | <NA> |
| S6 | Test varies: image (no headline change) | tests | flagged | 6,573 | 22,743 | <NA> |
| S6 | Test varies: excerpt only | tests | flagged | 2,251 | 22,743 | <NA> |
| S6 | Test varies: nothing (A/A) | tests | flagged | 1,486 | 22,743 | <NA> |
| S7 | Packages whose headline is used in 2+ tests | packages | flagged | 61,212 | 105,551 | Kept; reruns are separate experiments |
| S8 | Missing image id | packages | flagged | 131 | 105,551 | Kept; 'unknown image' |
| S9 | Excerpt is the stock phrase | packages | flagged | 53,463 | 105,551 | <NA> |
| S9 | Excerpt empty | packages | flagged | 11,278 | 105,551 | <NA> |
| S10 | Zero-click packages (kept) | packages | none | 68 | 105,551 | Valid results |
| S11 | Tests whose packages span 2 test weeks | tests | none | 117 | 22,743 | Week = week of first package |

## Exploratory

| Rule | What | Table | Action | Affected | Of | Why |
|---|---|---|---|---|---|---|
| S1 | Test starts in the broken-randomization window (2013-06-25 – 2014-01-10) | tests | flagged | 1,050 | 4,873 | Archive 2024 update; excluded from causal results |
| S2 | Fails the chi-square randomization check (p < 0.001) | tests | flagged | 753 | 4,873 | Unequal assignment; excluded from causal results |
| S2 | …of which outside the window | tests | flagged | 18 | 4,873 | <NA> |
| S1+S2 | Tests usable for causal results | tests | flagged | 3,805 | 4,873 | <NA> |
| S3 | Headline changed by cleaning | packages | cleaned copy | 2,474 | 22,666 | Raw headline kept unchanged |
| S3 | …HTML tags removed | packages | cleaned copy | 49 | 22,666 | <NA> |
| S3 | …zero-width characters removed | packages | cleaned copy | 50 | 22,666 | <NA> |
| S3 | …curly quotes straightened | packages | cleaned copy | 1,954 | 22,666 | <NA> |
| S3 | …extra or untrimmed spaces fixed | packages | cleaned copy | 536 | 22,666 | Rows can count twice |
| S4 | Headline empty after cleaning | packages | flagged | 0 | 22,666 | Excluded from text features |
| S5 | Packages sharing a variant with another package | packages | flagged | 2,019 | 22,666 | Summed into one variant for headline effects |
| S5 | Variants | packages | none | 21,122 | 22,666 | Distinct reader-facing versions |
| S6 | Test varies: headline only | tests | flagged | 2,053 | 4,873 | <NA> |
| S6 | Test varies: headline+image | tests | flagged | 295 | 4,873 | <NA> |
| S6 | Test varies: headline+excerpt | tests | flagged | 250 | 4,873 | <NA> |
| S6 | Test varies: image (no headline change) | tests | flagged | 1,431 | 4,873 | <NA> |
| S6 | Test varies: excerpt only | tests | flagged | 508 | 4,873 | <NA> |
| S6 | Test varies: nothing (A/A) | tests | flagged | 336 | 4,873 | <NA> |
| S7 | Packages whose headline is used in 2+ tests | packages | flagged | 5,382 | 22,666 | Kept; reruns are separate experiments |
| S8 | Missing image id | packages | flagged | 22 | 22,666 | Kept; 'unknown image' |
| S9 | Excerpt is the stock phrase | packages | flagged | 11,490 | 22,666 | <NA> |
| S9 | Excerpt empty | packages | flagged | 2,442 | 22,666 | <NA> |
| S10 | Zero-click packages (kept) | packages | none | 12 | 22,666 | Valid results |
| S11 | Tests whose packages span 2 test weeks | tests | none | 26 | 4,873 | Week = week of first package |
