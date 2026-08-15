# Phase29-L21T-AF - Expected Edge / Opportunity Gate Forward-Return Attribution Audit

## Primary Judgment

`PHASE29_L21T_AF_EXPECTED_EDGE_GATE_FORWARD_RETURN_ATTRIBUTION_COMPLETE_REPAIR_DESIGN_REQUIRED`

Current Phase remains `Phase29`.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AF` |
| Target Run | `runtime-test-historical-extended-smoke-20260814T005603520480Z` |
| Target run status during audit | `RUNNING` |
| Runtime mutation | `NO` |
| Strategy code changed | `NO` |
| Config changed | `NO` |
| Model changed | `NO` |
| Long Historical executed by Codex | `NO` |

This audit used already-materialized evidence only.  It did not stop, resume,
replay, recover, fresh-run, approve, or manually edit the target run.

## Evidence Artifacts

Machine-readable output:

```text
reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit/summary.json
reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit/per_symbol.csv
reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit/per_symbol.json
reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit/cohort_summary.json
```

Audit utility:

```text
scripts/audits/phase29_l21t_af_expected_edge_audit.py
```

The audit utility is standalone and does not import `ai_fund_lab_v2`.

## Audit Dates

Selection rule:

```text
completed days with exposure_ratio < 0.50, cash_ratio > 0.50, and required candidate artifacts available; preferred representative dates used when eligible
```

Selected dates:

| Date | Regime | Breadth | Exposure | Cash | Target Gross | Cash Reserve | Positions |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2022-08-12` | `BULL` | `STRONG` | `13.33%` | `86.67%` | `100.00%` | `0.00%` | `1` |
| `2022-08-18` | `BULL` | `STRONG` | `13.45%` | `86.55%` | `100.00%` | `0.00%` | `1` |
| `2022-09-30` | `BEAR` | `WEAK` | `36.91%` | `63.09%` | `74.00%` | `26.00%` | `2` |
| `2022-10-05` | `RANGE` | `WEAK` | `37.39%` | `62.61%` | `92.00%` | `8.00%` | `2` |
| `2022-10-12` | `BEAR` | `WEAK` | `37.21%` | `62.79%` | `74.00%` | `26.00%` | `2` |
| `2022-10-27` | `BULL` | `STRONG` | `37.38%` | `62.62%` | `100.00%` | `0.00%` | `2` |
| `2022-11-01` | `BULL` | `STRONG` | `37.54%` | `62.46%` | `100.00%` | `0.00%` | `2` |

High exposure comparison status: `NOT_YET_AVAILABLE`.  The fresh target run had
not reached 2023-06 high-exposure comparison dates in the inspected evidence.

## Price Basis

Forward returns are post-hoc attribution only:

```text
J-Quants adjusted close: decision-date AdjC -> symbol-specific +N trading-row future AdjC
```

Price source:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/equities_bars_daily/data.parquet
```

Future data used by Runtime: `NO`  
Forward return used only for audit: `YES`

## 2022-10-05 Funnel

For `2022-10-05`, all 50 symbols materialized through PC/PS:

| Metric | Count |
| --- | ---: |
| Total symbols | `50` |
| Buy Quality PASS | `38` |
| Positive Expected Edge | `5` |
| BUY allocated | `1` |
| non_positive_expected_edge zero allocation | `34` |
| lot/safety impossible | `1` |
| Quality rejected | `12` |

This confirms the corrected funnel:

```text
50 Candidates
-> 38 Quality PASS
-> 50 materialized in PC/PS
-> many BUY_NEW requested/accepted weight = 0
-> few actual capital allocation candidates
```

## Overall Counts

Across 7 low-exposure dates:

| Metric | Count |
| --- | ---: |
| Total Candidates | `350` |
| Quality PASS count | `286` |
| Positive Expected Edge count | `27` |
| non_positive_expected_edge_score count | `323` |
| ranking/top20 exclusion count | `158` |
| lot/safety blocked count | `5` |
| BUY allocated count | `10` |
| false negative count | `87` |
| false positive count | `7` |

The ranking/top20 exclusion count overlaps heavily with
`non_positive_expected_edge_score`; pure ranking-only cohort was not dominant in
this sample.

## Cohort Statistics

Average / median / positive-return ratio:

| Cohort | Count | 5BD | 10BD | 20BD |
| --- | ---: | ---: | ---: | ---: |
| `A_QUALITY_PASS_POSITIVE_EDGE_BUY_ALLOCATED` | `10` | `-5.32% / 0.00% / 30.0%` | `-11.63% / -6.49% / 10.0%` | `-1.30% / 0.00% / 40.0%` |
| `B_QUALITY_PASS_NON_POSITIVE_EXPECTED_EDGE_ZERO_BUY` | `261` | `0.46% / -0.13% / 45.0%` | `1.14% / 0.00% / 47.1%` | `3.28% / 0.00% / 49.2%` |
| `D_QUALITY_PASS_BUY_ELIGIBLE_BUT_LOT_SAFETY_IMPOSSIBLE` | `5` | `-5.92% / 0.11% / 60.0%` | `-11.63% / -0.22% / 40.0%` | `-9.95% / 0.00% / 40.0%` |
| `E_QUALITY_REJECTED` | `64` | `-0.86% / 0.59% / 54.0%` | `0.18% / 1.39% / 53.2%` | `5.05% / 1.06% / 56.5%` |
| `QUALITY_PASS_ZERO_OTHER` | `10` | `-0.15% / 0.05% / 50.0%` | `-0.26% / 0.34% / 70.0%` | `0.58% / 0.75% / 60.0%` |

Interpretation: rejected / zero-allocation cohorts were not clearly worse than
allocated BUYs.  The allocated BUY cohort was weak on 5BD and 10BD, while the
large non-positive Expected Edge cohort had positive average 20BD returns.

## Separability

Expected Edge score separability:

| Check | Result |
| --- | --- |
| score > 0 vs score <= 0 | Non-positive cohort outperformed positive cohort on average at 5BD, 10BD, and 20BD. |
| top20 vs excluded | `NOT_TOP20` had higher average 5BD, 10BD, and 20BD returns than `TOP20`. |
| BUY allocated vs zero allocation | Zero allocation outperformed allocated BUYs on average at 5BD, 10BD, and 20BD. |
| Spearman score vs 5BD return | `0.0495` |
| Spearman score vs 10BD return | `-0.0611` |
| Spearman score vs 20BD return | `-0.1205` |

Assessment:

```text
EXPECTED_EDGE_SCORE_POORLY_CALIBRATED_OR_NON_SEPARATING
```

Ranking separability assessment:

```text
RANKING_NOT_PROVEN_USEFUL_FOR_FORWARD_RETURN_SEPARATION_IN_LOW_EXPOSURE_SAMPLE
```

## False Negatives

False negative definition:

```text
Quality PASS + non_positive_expected_edge_score + zero BUY allocation
with at least one of +5BD/+10BD/+20BD return >= +10%
```

Count: `87`

Largest 20BD examples:

| Date | Symbol | Rank | Expected Edge | 20BD Return | Reason |
| --- | --- | ---: | ---: | ---: | --- |
| `2022-10-27` | `21950` | `42` | `-0.62738000` | `110.83%` | `below_opportunity_top20|non_positive_expected_edge_score` |
| `2022-11-01` | `92270` | `14` | `-0.26645731` | `105.27%` | `non_positive_expected_edge_score` |
| `2022-08-18` | `68980` | `35` | `-0.60891522` | `103.94%` | `below_opportunity_top20|non_positive_expected_edge_score` |
| `2022-10-27` | `92270` | `14` | `-0.27003642` | `92.53%` | `non_positive_expected_edge_score` |
| `2022-10-27` | `17570` | `38` | `-0.60100572` | `58.33%` | `below_opportunity_top20|non_positive_expected_edge_score` |

This is too large to classify the gate as functioning as intended.

## False Positives

False positive definition:

```text
BUY allocated with at least one of +5BD/+10BD/+20BD return <= -5%
```

Count: `7`

Worst 20BD examples:

| Date | Symbol | Rank | Expected Edge | 20BD Return |
| --- | --- | ---: | ---: | ---: |
| `2022-10-12` | `65500` | `5` | `0.02445178` | `-15.90%` |
| `2022-11-01` | `78860` | `5` | `0.05170455` | `-14.97%` |
| `2022-10-05` | `76920` | `4` | `0.11891258` | `-14.44%` |
| `2022-11-01` | `99840` | `4` | `0.09058132` | `-8.01%` |

## Market Context Interaction

Market Context does explain part of some dates:

- `2022-09-30` and `2022-10-12` had `BEAR` / `WEAK` states and target gross
  exposure `74%`.
- `2022-10-05` was `RANGE` / `WEAK` and target gross exposure was still `92%`.
- `2022-08-12`, `2022-08-18`, `2022-10-27`, and `2022-11-01` were `BULL` /
  `STRONG` with target gross exposure `100%`, yet cash remained above `62%` to
  `86%`.

Classification by interaction:

```text
B. Exposure target is high but Expected Edge candidates are scarce
```

with secondary:

```text
C. Some Expected Edge candidates exist but lot/safety blocks a small subset
```

Lot/safety was not dominant in this sample: only `5` of `350` rows were
classified as lot/safety blocked.

## Lineage / Regression Audit

Implementation lineage:

- `src/ai_fund_lab_v2/opportunity_ai/inference.py` assigns raw predictions to
  `expected_edge_score`, ranks descending by that score, and adds
  `non_positive_expected_edge_score` when score is `<= 0`.
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` declares
  `canonical_score_field=runtime_opportunity_score`,
  `score_semantic_role=uncalibrated_relative_model_score`,
  `economic_units_available=false`, and `calibration_applied=false`.
- The runtime artifact marks `expected_edge_score` and `expected_return` as
  deprecated aliases of uncalibrated runtime opportunity score, not calibrated
  economic return.
- Prior Phase17-BV16 documentation records the same contract and warns not to
  relax the `expected_edge_score > 0` rule without formal validation,
  recalibration, or retraining.

Regression confirmed:

```text
NOT_PROVEN
```

No single recent regression was proven in AF.  The evidence instead shows a
known design/semantic weakness: an uncalibrated relative score is still acting
as an absolute positive/negative Expected Edge gate.

Calibration applied status:

```text
False
```

## Root Cause Classification

Low Exposure root cause classification:

```text
MULTI_CAUSAL
```

Dominant detail:

```text
Expected Edge non-separability / excessive false negatives, with ranking overlap
and secondary lot/safety blocks.
```

Answer to the central question:

```text
2022 autumn high cash was not proven to be the result of correctly excluding bad
opportunities.  The post-hoc J-Quants forward-return evidence shows the current
Expected Edge / ranking semantics missed many subsequent winners and did not
separate forward returns reliably in the inspected low-exposure sample.
```

## Required Status Fields

| Field | Value |
| --- | --- |
| Future data used by Runtime | `NO` |
| Forward return used only for audit | `YES` |
| Strategy code changed | `NO` |
| Config changed | `NO` |
| Model changed | `NO` |
| Target run mutated | `NO` |
| Long Historical executed by Codex | `NO` |
| Phase30 entered | `NO` |

## Validation

```text
python3 scripts/audits/phase29_l21t_af_expected_edge_audit.py
```

Result: `PASS`, generated `350` rows across `7` audit dates.

Additional validation is recorded with the implementation turn:

```text
PYTHONPATH=. python3 -m pytest -q tests/audits/test_phase29_l21t_af_expected_edge_audit.py
python3 -m py_compile scripts/audits/phase29_l21t_af_expected_edge_audit.py tests/audits/test_phase29_l21t_af_expected_edge_audit.py
git diff --check
```

## Recommended Next Task

```text
Phase29-L21T-AG — Expected Edge Gate Calibration / Allocation Semantics Design
```

AG should be design-only first.  It must not force cash deployment, fixed
position counts, top-N buying, or future-return-tuned thresholds.  The goal is
Opportunity discrimination quality, with future data kept in validation only.
