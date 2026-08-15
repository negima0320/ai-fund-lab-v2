# Phase29-L21H - Opportunity / Buy Quality Semantics and Entry Supply Root Cause Audit

## Primary Judgment

`PHASE29_L21H_OPPORTUNITY_CALIBRATION_CONTRACT_GAP_AND_RAW_SCORE_SEMANTICS_AMBIGUITY_CONFIRMED_REPAIR_REQUIRED`

The 49/50 daily Buy Quality rejects are not caused by missing opportunity scores. They are mostly negative runtime opportunity scores produced by the Runtime v2 BUY AI opportunity model, then consumed by Opportunity eligibility and Buy Quality as a positive-edge gate. The architecture concern is that the same uncalibrated value is materialized as `expected_edge_score`, `expected_return`, `opportunity_score`, and downstream `runtime_opportunity_score` while the artifact says `calibration_applied = false` and Buy Quality emits `calibration_not_applied_raw_score_not_expected_return`.

This is pre-existing behavior, not a confirmed Phase27-29 regression.

## Target Run

- Run: `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T130548490709Z`
- Strategy dates: `2022-08-10`, `2022-08-12`, `2022-08-15`, `2022-08-16`, `2022-08-17`, `2022-08-18`, `2022-08-19`
- Evidence used: existing strategy artifacts, `.runtime/runtime_state/buy_ai/<date>` artifacts, code inspection, git log, and existing Phase reports only.

## Candidate Count

| Date | Candidate rows | Opportunity rows | Positive | Zero | Negative | Missing |
|---|---:|---:|---:|---:|---:|---:|
| 2022-08-10 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-12 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-15 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-16 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-17 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-18 | 50 | 50 | 1 | 0 | 49 | 0 |
| 2022-08-19 | 50 | 50 | 2 | 0 | 48 | 0 |
| Total | 350 | 350 | 8 | 0 | 342 | 0 |

## Buy Quality PASS Rate

Buy Quality PASS was 7 / 350 = 2.0%. There were 343 rejects.

## Distinct PASS Symbols

Only `94320` passed Buy Quality on all seven inspected dates. On 2022-08-19, rank 2 `37820` had a positive raw score, but was still rejected because `no_buy_reason = high_downside_risk_score`.

## Raw Opportunity Score Producer

| Stage | Evidence |
|---|---|
| Producer | `Runtime v2 BUY AI Producer` |
| Source file/function | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`, opportunity artifact materialization |
| Model source | `.runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/opportunity/model.pkl` |
| Accepted generation | `phase19_aq_accepted_generation_641e6e313543f013` |
| Feature input | `.runtime/operations/feature_artifacts/<date>/opportunity_feature_input.parquet` |
| Runtime artifact | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json` |
| Output fields | `expected_edge_score`, `opportunity_score`, `expected_return`, later `runtime_opportunity_score` |
| Sort authority | `expected_edge_score DESC`, then `code ASC` |
| Consumer | Opportunity eligibility, Buy Quality, Portfolio Construction, Position Sizing, Runtime Planning |

Code path:

```text
opportunity_ai.inference.build_inference_output()
  model.predict(...) -> expected_edge_score
  sort by expected_edge_score DESC
  build_no_buy_reason(): expected_edge_score <= 0 -> non_positive_expected_edge_score

runtime_v2.buy_ai.producer
  expected_edge_score = row["expected_edge_score"]
  opportunity_score = expected_edge_score
  expected_return = expected_edge_score
  prediction_semantics = runtime_opportunity_score
  calibration_applied = false

strategy.buy_quality
  score = opportunity.expected_edge_score fallback runtime_opportunity_score
  score <= 0 -> non_positive_or_missing_raw_opportunity_score
  no_buy_reason present -> critical relative opportunity failure
```

## Raw Opportunity Score Semantics

Current runtime artifact semantics are ambiguous:

- Artifact metadata says `prediction_semantics = runtime_opportunity_score`.
- Runtime materialization labels the same scalar as `expected_edge_score`, `expected_return`, and `opportunity_score`.
- Phase19 runtime baseline expected output schema names Opportunity output as `standardized_score`.
- Phase26-G says `calibration_applied=false` prohibits treating raw score as expected return.
- Buy Quality itself emits `calibration_not_applied_raw_score_not_expected_return`.

Therefore the field is not safely proven to be an economically calibrated expected return. It is best treated as an uncalibrated model score / runtime opportunity score whose sign is being consumed as if it were economic edge.

## Calibration Applied

NO. Every inspected opportunity artifact reports:

```text
calibration_applied = false
transformation_stage = accepted_generation_bound_imputer_scaler_model
prediction_metric_name = opportunity_score
prediction_semantics = runtime_opportunity_score
```

Buy Quality applies only a reliability haircut when calibration is absent:

```text
calibration_factor = 0.85
reason = calibration_not_applied_raw_score_not_expected_return
```

It does not convert raw model output into a calibrated expected return before applying the `score <= 0` critical gate.

## Calibration Expected

PARTIAL / CONTRACT GAP.

Phase19 produced Opportunity calibration artifacts and Phase19/roadmap baseline metadata expects Opportunity `standardized_score` / calibration semantics in lifecycle monitoring. But current Runtime BUY AI producer materializes generation-bound model output with `calibration_applied=false`. Phase28-D64 already classified baseline/current semantics mismatch as an evaluation-shadow defect, not direct Production Strategy impact. L21H confirms the same mismatch is relevant to interpreting entry supply: current Buy Quality is making admission decisions on a raw score that it simultaneously says is not expected return.

## Positive Score Count

8 / 350 opportunity rows were positive. Seven became Buy Quality PASS. The eighth was 2022-08-19 rank 2 `37820`, rejected for high downside risk.

## Zero Score Count

0 / 350.

## Negative Score Count

342 / 350.

## Missing Score Count

0 / 350.

`non_positive_or_missing_raw_opportunity_score` is therefore materially negative-score rejection, not missing-data rejection.

## Raw Score Distribution

| Metric | Value |
|---|---:|
| n | 350 |
| min | -0.70950885 |
| p10 | -0.639254917 |
| p25 | -0.5739615125 |
| median | -0.473533885 |
| p75 | -0.289285525 |
| p90 | -0.137856528 |
| max | 0.19132343 |
| positive | 8 |
| zero | 0 |
| negative | 342 |
| missing | 0 |

Daily medians stayed negative, from roughly -0.436 to -0.526.

## Top Reject Reasons

| Reject reason | Count |
|---|---:|
| `calibration_not_applied_raw_score_not_expected_return` | 343 |
| `execution_feasibility_available` | 343 |
| `market_context_symbol_quality_modifier_no_exposure_duplication` | 343 |
| `portfolio_fit_not_position_count_gate` | 343 |
| `rank_not_used_as_fixed_n_gate` | 343 |
| `relative_quality_uses_percentile_robust_z_population_strength` | 343 |
| `non_positive_or_missing_raw_opportunity_score` | 342 |
| `opportunity_no_buy_reason_present:below_opportunity_top20|non_positive_expected_edge_score` | 200 |
| `opportunity_no_buy_reason_present:non_positive_expected_edge_score` | 122 |
| `opportunity_no_buy_reason_present:high_downside_risk_score|non_positive_expected_edge_score` | 10 |

The first six are broad component/trace reasons. The material exclusion reasons are negative score and propagated opportunity `no_buy_reason`.

## 94320 Dominance Explanation

`94320` is consistently the only rank-1 positive score in the inspected window:

| Date | Rank 1 score | Rank 2 score | Median score | Rank 50 score |
|---|---:|---:|---:|---:|
| 2022-08-10 | 0.16908343 | -0.07228975 | -0.442619085 | -0.65296597 |
| 2022-08-12 | 0.17946130 | -0.10868016 | -0.475661970 | -0.69458836 |
| 2022-08-15 | 0.19132343 | -0.00016243 | -0.453975580 | -0.61834779 |
| 2022-08-16 | 0.15712628 | -0.03688415 | -0.435825900 | -0.69148537 |
| 2022-08-17 | 0.14478793 | -0.02270449 | -0.486551860 | -0.69856909 |
| 2022-08-18 | 0.12765185 | -0.03626304 | -0.525761910 | -0.70950885 |
| 2022-08-19 | 0.16353315 | 0.01843331 | -0.493718290 | -0.67908958 |

The model output does isolate `94320` as the only repeated positive edge. Whether this is economically rational cannot be proven from the uncalibrated score alone. It is internally consistent as ranking output, but the economic interpretation is not contract-clean.

## Candidate Rank / PASS Relationship

| Rank bucket | BQ PASS | Total | PASS rate |
|---|---:|---:|---:|
| Rank 1 | 7 | 7 | 100.0% |
| Rank 2-5 | 0 | 28 | 0.0% |
| Rank 6-10 | 0 | 35 | 0.0% |
| Rank 11-20 | 0 | 70 | 0.0% |
| Rank 21-50 | 0 | 210 | 0.0% |

Opportunity rank 1 fully explains PASS in this window. Candidate rank does not: `94320` had candidate rank 2 or 3, while candidate rank 1 symbols such as `21910` were repeatedly rejected due to negative opportunity score and sometimes high downside risk.

## Sample Symbol Trace

| Date | Rank | Symbol | Candidate rank | Candidate score | Raw score | No-buy reason | BQ band/action |
|---|---:|---:|---:|---:|---:|---|---|
| 2022-08-10 | 1 | 94320 | 2 | 0.86228036 | 0.16908343 |  | HIGH / REDUCED |
| 2022-08-10 | 2 | 66590 | 3 | 0.83830262 | -0.07228975 | non_positive_expected_edge_score | UNUSABLE / REJECT |
| 2022-08-10 | 3 | 21910 | 1 | 0.86892429 | -0.08496023 | high_downside_risk_score; non_positive_expected_edge_score | UNUSABLE / REJECT |
| 2022-08-10 | 10 | 76470 | 13 | 0.67996722 | -0.22552953 | non_positive_expected_edge_score | UNUSABLE / REJECT |
| 2022-08-10 | 50 | 45920 | 49 | 0.48075479 | -0.65296597 | below_top20; non_positive_expected_edge_score | UNUSABLE / REJECT |
| 2022-08-19 | 1 | 94320 | 3 | 0.88632543 | 0.16353315 |  | HIGH / REDUCED |
| 2022-08-19 | 2 | 37820 | 2 | 0.90567741 | 0.01843331 | high_downside_risk_score | UNUSABLE / REJECT |
| 2022-08-19 | 3 | 21910 | 1 | 0.95359118 | -0.00757706 | high_downside_risk_score; non_positive_expected_edge_score | UNUSABLE / REJECT |

## Compounded Gate Chain

Observed gate chain:

| Gate | Condition | Rows entering | Rows rejected | Rows passing |
|---|---|---:|---:|---:|
| Candidate Top50 | Candidate producer emits Top50 | 350 | 0 | 350 |
| Opportunity model/rank | Model score, rank by `expected_edge_score DESC` | 350 | 0 | 350 |
| Opportunity score positivity | `expected_edge_score > 0` | 350 | 342 | 8 |
| Opportunity no-buy reason | no blocking no-buy reason | 8 | 1 | 7 |
| Buy Quality raw score gate | score exists and `> 0` | 350 | 342 | 8 |
| Buy Quality no-buy propagation | `no_buy_reason` empty | 8 | 1 | 7 |
| Buy Quality composite | weighted quality if no critical review | 7 | 0 | 7 reduced-allocation PASS |

This is not a broad independent AND-stack where many unrelated gates each remove large counts. It is mostly one semantic gate, `expected_edge_score > 0`, applied at Opportunity and again propagated into Buy Quality. The high-downside gate rejects one otherwise positive row.

## Primary Bottleneck

`SCORE_SEMANTICS_AND_CALIBRATION_CONTRACT_GAP`

The primary bottleneck is not missing data, PC, PS, Runtime Planning, or Submit/Fill. It is that entry supply is determined by the sign of an uncalibrated opportunity model output whose runtime artifact aliases blur expected edge, expected return, opportunity score, and runtime opportunity score.

## Secondary Bottleneck

`GENUINE_MODEL_OUTPUT_THINNESS_POSSIBLE_BUT_NOT_PROVEN_ECONOMICALLY`

The model genuinely produced mostly negative numeric values in this window. If those values are valid expected-edge units, then 94320-only selection is rational. But current evidence does not prove that the raw sign is economically calibrated enough to justify treating all negative rows as economically non-positive.

## Opportunity Scoring Regression Confirmed

NO. Phase27-A4/A5/A6, Phase29-L17, L21A, and L21G all show sparse opportunity/BQ supply as existing behavior. Git history did not identify a Phase27-29 opportunity-scoring change causing this specific early-window collapse.

## Buy Quality Regression Confirmed

NO. Buy Quality behavior matches its current implementation and prior L21A/L21G observations. The concern is architectural semantics, not a newly introduced regression.

## Recent Phase27-29 Causality

NO direct causality found.

Phase27 Expected Edge work is primarily PM reasoning architecture. Phase28-D55/L21D/L21F focus on BUY_ADD / lot-aware capital conversion and explicitly preserve BUY_NEW semantics. Phase29-L12/L17 identify opportunity/BQ scarcity or low-price/re-entry issues but do not show a recent shared-path change that narrowed all BUY_NEW entry supply.

## Pre-existing Behavior

YES. L21A observed 2,300 Buy Quality decisions, 2,178 rejects, and only 122 PASS. L21G showed the same first-window sparse BUY_NEW behavior in both target and comparison runs.

## Score Semantics Mismatch Confirmed

YES.

Confirmed mismatch:

- lifecycle baseline / roadmap: Opportunity `standardized_score`, `calibration_applied=true`
- current runtime artifact: `runtime_opportunity_score`, `calibration_applied=false`
- runtime rows: same scalar exposed as `expected_edge_score`, `expected_return`, and `opportunity_score`
- Buy Quality reason: `raw_score_not_expected_return`

This does not prove every rejected symbol was good. It proves the score contract is not clean enough to treat the current 2% pass rate as semantically validated economic selectivity.

## Calibration Mismatch Confirmed

YES.

Opportunity calibration artifacts exist and passed Phase19 review, but the runtime artifact used in this run is explicitly uncalibrated. Buy Quality recognizes that state but still applies a hard sign gate to the raw score.

## Compounded Entry Gate Overfiltering Confirmed

NO as independent multi-gate overfiltering. The observed overfilter shape is primarily duplicated propagation of one gate: non-positive raw opportunity score. The single positive rejected non-94320 row was rejected by high downside risk, which is a separate rational safety/quality gate.

## BUY_NEW/BUY_ADD Shared Coupling

NO unintended recent shared coupling found. Expected Edge / Incremental Investment Value additions in Phase27/28 are PM/BUY_ADD-oriented. The L21H bottleneck sits upstream in shared Opportunity / Buy Quality BUY admission, but no evidence shows L21D/L21F BUY_ADD repairs changed BUY_NEW.

## Design Intent Supports 2% PASS

NO explicit design intent found for exactly 2% PASS.

Design intent supports selective, quality-sensitive buying and rejects fixed purchase counts. It also says low positive opportunity scores may pass raw eligibility but require Adaptive Buy Quality acceptance. It does not document that Top50 should normally collapse to one daily symbol or that 49/50 should be rejected by an uncalibrated raw-score sign gate.

## Classification

| Class | Judgment |
|---|---|
| A. Genuine opportunity scarcity | PARTIAL |
| B. Model produces mostly non-positive economically meaningful scores | NOT PROVEN |
| C. Score semantics misuse | YES, primary architecture concern |
| D. Calibration mismatch | YES |
| E. Missing score lineage/data issue | NO |
| F. Zero/clipping/defaulting issue | NO |
| G. Buy Quality threshold over-filtering | PARTIAL; sign gate is hard, but not a tunable BQ threshold alone |
| H. Compounded gate over-filtering | NO as independent multi-gate stack |
| I. Shared BUY_NEW/BUY_ADD quality coupling | NO recent unintended coupling found |
| J. Recent regression | NO |
| K. Pre-existing architecture issue | YES |
| L. Observability ambiguity only | NO; behavior is observable, semantics are ambiguous |
| M. Multi-causal | YES: raw score sign plus calibration/semantics contract plus one downside-risk rejection |

## Recommended Next Scope

No implementation is authorized in L21H. The next repair/audit scope should be:

- Decide the canonical runtime meaning of Opportunity output: calibrated expected return, standardized score, model margin, utility, or rank-only score.
- Stop aliasing one uncalibrated scalar simultaneously as `expected_edge_score`, `expected_return`, `opportunity_score`, and `runtime_opportunity_score` unless the contract proves those meanings are equivalent.
- If sign is intended to mean economic edge, prove calibration and expected-return units at runtime.
- If sign is only standardized/model-margin direction, move Buy Quality eligibility away from hard `score > 0` economic interpretation and use documented relative/rank/population semantics instead.
- Keep fixed buy counts and forced deployment prohibited.

## New Component Required NO

NO. Existing artifacts were sufficient to trace the producer, score distribution, calibration flag, and Buy Quality consumer behavior. A later repair may add better observability, but L21H does not require a new component.

## Current Run Mutated NO

YES. The current halted run was not resumed, repaired, aborted, rolled back, or mutated.

## Long Historical Executed NO

YES. No fresh run, resume, 100BD, 4-year historical, pending lifecycle, or repair command was executed.

