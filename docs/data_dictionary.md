# Data Dictionary: Upworthy Research Archive

Source: The Upworthy Research Archive (Matias, Munger, Aubin Le Quere & Ebersole, Cornell University), https://osf.io/jd64p/, CC BY 4.0; *Scientific Data* 8, 195 (2021). Files: March 2020 release, as downloaded 2026-11-04 (checksums in `docs/raw_checksums.txt`). Counts below are from `docs/data_profile.md`.

## How the files connect

```
one test (clickability_test_id) ──< many packages (one row each)
   one article's headline experiment      headline + image + excerpt, with impressions and clicks

exploratory ∪ confirmatory ∪ holdout = every fielded test, split by test (never by package), stratified by test_week
undeployed = packages not fielded in a test (impressions mostly empty); 98.5% created May 2015 – May 2019
```

- **Grain:** one row = one package (arm) in one test.
- **Join key between packages of the same test:** `clickability_test_id`. Tests never cross splits (verified: 0 overlap).
- **Packages sharing an image:** `eyecatcher_id` (the image file itself isn't included).
- **Valid joins:** within a split, group by `clickability_test_id`. Across splits, only stack (union); never join packages from different splits. The undeployed file shares 6 test ids with the splits; it is not used for A/B analysis (no impressions).

## Package files (exploratory, confirmatory, holdout)

| File | Rows | Tests | Purpose |
|---|---|---|---|
| `upworthy-archive-exploratory-packages-03.12.2020.csv` | 22,666 | 4,873 | Develop and validate every definition and analysis |
| `upworthy-archive-confirmatory-packages-03.12.2020.csv` | 105,551 | 22,743 | Run once, with locked definitions, for the headline results |
| `upworthy-archive-holdout-packages-03.12.2020.csv` | 22,600 | 4,871 | Not used (kept untouched, per the archive design) |

| Column | Type | Meaning | Profile notes | Use |
|---|---|---|---|---|
| `Unnamed: 0` | integer | Row number from the authors' export | Unique within and across the three splits | Row id |
| `created_at` | timestamp | When the package was created (timezone unknown) | Jan 24, 2013 – Apr 30, 2015. Two formats: with fractional seconds (most) and without (896 exploratory rows), so parse as ISO 8601 | Test start = earliest package; randomization window |
| `updated_at` | timestamp | Last database update | All April–December 2016: a system migration, not a test date | Not used |
| `clickability_test_id` | text | The test (experiment) this package belongs to | Never empty in the splits | **Test key** |
| `excerpt` | text | Short text shown with the headline | Empty in 11%; 50% are the stock phrase "Things that matter. Pass 'em on." (plus a variant with a trailing space) | Possible control; varies in some tests |
| `headline` | text | The headline tested | 1 empty (holdout); median 84 characters / 15 words; curly quotes, em dashes, zero-width and non-breaking spaces, HTML tags in 49 (exploratory) | **Main text input** |
| `lede` | text | Opening paragraph of the article (HTML) | Varies within 501 of 4,873 exploratory tests | Mostly constant; checked as a factor |
| `slug` | text | URL slug for the package | Not unique (22,334 distinct in 22,666 rows) | Not used |
| `eyecatcher_id` | text | Id of the image shown | Empty in 22 (exploratory) | Image arm; controls for image |
| `impressions` | integer | Browser sessions assigned this package | ≥ 1; median 3,122 | **Denominator** |
| `clicks` | integer | Sessions that clicked it | ≥ 0, never above impressions | **Outcome numerator** |
| `significance` | decimal | Score shown to editors | 0–100, calculation changed over time; **not** a p-value | Not used |
| `first_place` | True/False | Shown to editors; meaning undocumented | | Not used |
| `winner` | True/False | Package the editors chose to publish | 1,150 of 4,873 exploratory tests have one; not necessarily the best performer | Not used as outcome |
| `share_text` | text | Social-sharing text | Mostly empty | Not used |
| `square` | text | Square image variant | Mostly empty | Not used |
| `test_week` | integer | Year and week of the test, `YYYYWW` (e.g. 201303) | 2013 week 03 – 2015 week 17; 26 exploratory tests span two weeks | Split stratum; time control |

## Undeployed packages

`upworthy-archive-undeployed-packages.01.12.2021.csv`: 78,232 rows. Same columns as the splits plus `_id` (unique) and without `Unnamed: 0` and `test_week`. `impressions` and `clicks` are empty in 54,211 rows. Not used for A/B analysis; may serve as extra headline text for validating text tools.

## Google Analytics files (context only)

| File | Grain | Notes |
|---|---|---|
| `2013.01.01-2015.04.30-daily-users-info.csv` | Day (850 days) | Users, new users, sessions, duration, bounce rate, pageviews. Numbers have thousands commas, percents, h:mm:ss; Sessions and Pageviews are "N/A" on 304 days |
| `2013.01.01-2015.04.30-daily-pageviews.csv` | Day (850 days) | Pageviews, complete |
| `2013.01.01-2015.04.30-aggregate-country-data.csv` | Country (206) | Site-wide totals by country, whole period |

The authors note these are raw pulls, less vetted than the main files. They describe the whole site, not individual tests.

## Other files in the download
- `02.2021-create-research.samples.py`: the authors' script that created the three splits (15% / 70% / 15% of tests, sampled within each week).
- `Matias-Munger-Upworthy-Research-Archive-09.2019.pdf`, `Upworthy-Research-Archive-Announcement-CODE-MIT-11.02.2019.pdf`: papers and slides describing the archive.
- `upworthy-timestamped-screenshots/`: archive.is screenshots of article pages (tests ran mostly in the sidebar and below articles).
