# Confirmatory lock (rule L4, in two stages: R15)

The confirmatory split is opened in two stages, each only on Sanjay's approval, so nothing that compares click rates by headline content touches confirmatory data before its definitions are fixed (R2).

## Stage 1: the headline classifier
Classifier lock approved by Sanjay on 2026-11-10 ("Lock in the classifier"), after the 100-headline check (NOTES §5.3, §6).

Frozen from here on, for both splits:
- Codebook v2 (`pipeline/03_features/codebook.py`): gender (female / male / both / none); sentiment (positive / neutral / negative, judged by the note the headline ends on, confirmed by Sanjay, R16); 12 topic tags as 0/1 columns, none = unclear.
- The exact prompt, `prompt.json`, SHA-256 `a8055c513afc2e7ac8443cb783bcf7d96398b77d7fcd5fd56e47015bb55015e8`. `make_classifier_inputs.py` refuses to write confirmatory inputs if the prompt changes.
- The model tier: default. The unit: distinct headline plus non-stock excerpt. Batches of 60.

What this opens: the confirmatory headline **text** (no impressions, clicks or test results), through `load_text_for_classifier`, so it can be labeled.

## Stage 2: the analysis
Approved by Sanjay: 2026-11-11 00:11 ET ("I approve stage 2 lock, and move forward with the plan"), after reviewing the exploratory results (R22).

Frozen from here on, and run **once** on confirmatory:
- A/A check AA1–AA5 and calibration AA6 (NOTES §8.1), recomputed on confirmatory's own A/A tests.
- Main model M1 with sensitivity S1, S2 and gender × topic M2 (NOTES §8.2); topic models T1 (framing, causal) and T2 (story topic, descriptive) (NOTES §8.3).
- Significance: quasi-binomial with φ estimated from each model (R20) as the main method; A/A φ (a) and the A/A placebo threshold (b) reported alongside; robust = holds under the main method and (b); Holm across topics; at least 30 informative tests per topic.
- The code below, by SHA-256. The confirmatory results are whatever this code produces; no definition changes after seeing them.

| File | SHA-256 |
|---|---|
| `pipeline/common.py` | `e12a32ff88f3237e28155067d1a45adca97abb2ccf1cffc239c9c23e43f19019` |
| `pipeline/04_analysis/felogit.py` | `779898222d2e91b6ec87f86a1148f351dafbbefc7c51a1576c6d73218c4793ec` |
| `pipeline/04_analysis/aa_check.py` | `0c26a0e1082983dbd29e7b1f9399134b0256810fedd921c48c371646d1d5717c` |
| `pipeline/04_analysis/aa_calibrate.py` | `24b5a095bcafb9e28a915d92a40b2bc83d9f4a7feadaf043d7715dcd7823db9a` |
| `pipeline/04_analysis/main_effects.py` | `05d8e62a5c9aa7dfe08e1ad40a189533437ba2abb2dd57f0679ee954cb16b139` |
| `pipeline/04_analysis/topic_effects.py` | `8d2b0dd6eaa7f857ff60653ebec64a370d38f96b138cf3e4b162808b2b6f15ea` |
| `pipeline/03_features/codebook.py` | `ef452e65eb0cef768c51c706615905ea7babb9d05227059a086e1c8de341007c` |

(Fixed 2026-11-11 before this approval: the lock check used to accept the phrase "Approved by Sanjay:" anywhere in this file, so the stage-1 sentence describing this line opened stage 2 from 21:38 to 00:11. An audit of every data read in that window found no confirmatory outcome read; see NOTES §6.)
