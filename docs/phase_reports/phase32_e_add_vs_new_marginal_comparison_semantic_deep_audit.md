# Phase32-E - ADD vs NEW Marginal Comparison Semantic Deep Audit

## Executive Summary

Phase32-E audited the `24` plateau rows classified in Phase32-D as
`COMPARISON_RESOLUTION_LIMIT`.  The rows are canonical PC ADD competitors where
PM requested ADD semantics, expected edge improved versus the same-campaign
baseline, current PIT score evidence was present, but PC opportunity-cost
resolution failed because the same-day best NEW candidate had a higher
`runtime_opportunity_score`.

The current comparison is semantically valid as an ordinal, same-day opportunity
ranking proxy.  It is not a fully valid economic next-lot marginal-capital
comparison.  Both ADD and NEW scores are carried under
`OPPORTUNITY_RANKING_AUTHORITY` with semantic role
`uncalibrated_relative_model_score`, `calibration_applied=false`, and
`economic_units_available=false`; see
`src/ai_fund_lab_v2/strategy/portfolio_construction.py:9143` and
`docs/02_architecture/strategy_intelligence_architecture_v1.md:249`.
`NEW_BUY_SUPERIOR` is produced when best same-day NEW score exceeds the ADD
score; see `src/ai_fund_lab_v2/strategy/add_investment_evidence.py:270`.

Final classification: `MATERIAL_MARGINAL_VALUE_SEMANTIC_GAP`.  This does not
justify production allocation changes now.  It does justify a shadow-only
bridge/spec that records ADD score, NEW score, producer semantics, comparison
class, raw score gap, comparability status, opportunity-cost reason, Cash, Risk
Pacing, and final capital outcome in one row.

## Scope And Sources

- Target run: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z`
- Plateau window: `2023-05-31` through `2024-02-26`
- Canonical artifacts: daily `strategy/portfolio_construction.json`,
  `strategy/buy_quality_decisions.json`, `strategy/strategy_intelligence.json`,
  and `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json`
- Code contracts:
  - Score authority payload:
    `src/ai_fund_lab_v2/strategy/portfolio_construction.py:9143`
  - ADD competitor and final outcome labels:
    `src/ai_fund_lab_v2/strategy/portfolio_construction.py:5960`
  - ADD opportunity-cost resolution:
    `src/ai_fund_lab_v2/strategy/add_investment_evidence.py:270`
  - Expected Edge semantic contract:
    `docs/02_architecture/strategy_intelligence_architecture_v1.md:249`

No production code, configuration, threshold, weight, model, PM, PC, MCC, Risk
Pacing, Position Sizing, or Runtime behavior was changed.

## 24-Row Reconciliation

All `24` rows share this canonical predicate:

- `current_position=true`
- `pm_action=ADD`
- PM reason includes `no_loss_averaging`, `opportunity_rank_still_high`, and
  `strong_trend_continuation`
- expected-edge state is `IMPROVING`
- ADD `runtime_opportunity_score` is present
- same-day best NEW `runtime_opportunity_score` is higher
- opportunity cost resolves to `NEW_BUY_SUPERIOR`
- incremental investment value remains `UNKNOWN`
- canonical final ADD allocation is zero

| date | ADD | campaign | ADD score | prior | delta | current weight | notional | requested ADD | best NEW | NEW score | NEW-ADD | score semantic | opportunity cost | Cash | Risk Pacing | PC class | final |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-05-31 | 59550 | pc-0ffe77e55ab8d380-59550-0001 | 0.232356 | 0.224132 | 0.008224 | 0.043462 | 71000 | 0 | 21340 | 0.341822 | 0.109466 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-07 | 21340 | pc-b7bae0e666a47a59-21340-0002 | 0.206406 | 0.202715 | 0.003692 | 0.027046 | 50600 | 0 | 30410 | 0.308823 | 0.102417 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_NEUTRAL | GRADUAL_REDEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-08 | 21340 | pc-b7bae0e666a47a59-21340-0002 | 0.224666 | 0.206406 | 0.018260 | 0.028199 | 50600 | 0 | 30410 | 0.312707 | 0.088041 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_NEUTRAL | GRADUAL_REDEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-09 | 21340 | pc-b7bae0e666a47a59-21340-0002 | 0.243002 | 0.224666 | 0.018335 | 0.028666 | 50600 | 0 | 30410 | 0.316079 | 0.073078 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | GRADUAL_REDEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-23 | 40520 | pc-6b32e34313c6a821-40520-0001 | 0.178177 | 0.125522 | 0.052655 | 0.079509 | 145100 | 0 | 76470 | 0.206826 | 0.028649 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-26 | 40520 | pc-6b32e34313c6a821-40520-0001 | 0.208133 | 0.178177 | 0.029956 | 0.083263 | 141000 | 0 | 76470 | 0.247763 | 0.039630 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-06-27 | 40520 | pc-6b32e34313c6a821-40520-0001 | 0.228142 | 0.208133 | 0.020009 | 0.081615 | 144200 | 0 | 67310 | 0.287613 | 0.059471 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-09-26 | 94340 | pc-2be36cc756570767-94340-0002 | 0.140302 | 0.113930 | 0.026372 | 0.028479 | 52830 | 0 | 76470 | 0.399808 | 0.259506 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-09-27 | 94340 | pc-2be36cc756570767-94340-0002 | 0.145943 | 0.140302 | 0.005641 | 0.028386 | 53310 | 0 | 76470 | 0.372074 | 0.226131 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-09-28 | 94340 | pc-2be36cc756570767-94340-0002 | 0.199677 | 0.145943 | 0.053735 | 0.028457 | 51180 | 0 | 76470 | 0.367018 | 0.167341 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | GRADUAL_REDEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-09-29 | 94340 | pc-2be36cc756570767-94340-0002 | 0.222475 | 0.199677 | 0.022798 | 0.027455 | 50730 | 0 | 76470 | 0.390168 | 0.167692 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-10-02 | 94340 | pc-2be36cc756570767-94340-0002 | 0.276714 | 0.222475 | 0.054238 | 0.027209 | 50370 | 0 | 76470 | 0.435758 | 0.159045 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-10-03 | 94340 | pc-2be36cc756570767-94340-0002 | 0.324145 | 0.276714 | 0.047432 | 0.027249 | 50370 | 0 | 76470 | 0.471282 | 0.147137 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-10-04 | 94340 | pc-2be36cc756570767-94340-0002 | 0.397167 | 0.324145 | 0.073022 | 0.026887 | 50070 | 0 | 76470 | 0.540190 | 0.143023 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-10-13 | 94340 | pc-2be36cc756570767-94340-0002 | 0.209594 | 0.144397 | 0.065197 | 0.027548 | 50460 | 0 | 76470 | 0.428728 | 0.219134 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-10-16 | 94340 | pc-2be36cc756570767-94340-0002 | 0.233457 | 0.209594 | 0.023863 | 0.027705 | 50040 | 0 | 76470 | 0.487575 | 0.254119 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-12-13 | 60720 | pc-1473130d6350d6e4-60720-0002 | 0.234121 | 0.212623 | 0.021499 | 0.035103 | 63200 | 0 | 76470 | 0.511767 | 0.277646 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2023-12-18 | 60720 | pc-1473130d6350d6e4-60720-0002 | 0.209388 | 0.186188 | 0.023200 | 0.035720 | 64400 | 0 | 76470 | 0.506272 | 0.296884 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-05 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.223730 | 0.223076 | 0.000653 | 0.076985 | 141170 | 0 | 76470 | 0.397018 | 0.173289 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-06 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.226197 | 0.223730 | 0.002468 | 0.076835 | 141500 | 0 | 76470 | 0.402918 | 0.176721 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-07 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.232567 | 0.226197 | 0.006370 | 0.076818 | 140000 | 0 | 76470 | 0.415788 | 0.183220 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-09 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.238853 | 0.218715 | 0.020138 | 0.079034 | 139830 | 0 | 76470 | 0.434422 | 0.195569 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-14 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.239669 | 0.233736 | 0.005932 | 0.078919 | 138170 | 0 | 76470 | 0.460465 | 0.220797 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_NEUTRAL | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |
| 2024-02-15 | 92490 | pc-d138c398c3604d78-92490-0001 | 0.254830 | 0.239669 | 0.015162 | 0.078663 | 136000 | 0 | 76470 | 0.480555 | 0.225725 | uncalibrated relative | NEW_BUY_SUPERIOR | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | FAIL_CLOSED | ADD_ZERO |

Observed distribution:

- ADD symbols: `94340=9`, `92490=6`, `21340=3`, `40520=3`,
  `60720=2`, `59550=1`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT=20`, `GRADUAL_REDEPLOYMENT=4`
- Cash: `OPTIONALITY_ELEVATED=21`, `OPTIONALITY_NEUTRAL=3`
- Score gap range: min `0.028649`, max `0.296884`, average `0.166405`

## ADD Score Semantic

The ADD score is the existing-position row's `runtime_opportunity_score`.
Producer metadata is:

- authority: `OPPORTUNITY_RANKING_AUTHORITY`
- canonical field: `runtime_opportunity_score`
- source artifact class: `opportunity`
- transformation stage: `accepted_generation_bound_imputer_scaler_model`
- semantic role: `uncalibrated_relative_model_score`
- calibration: `false`
- economic units: `false`
- population scope: `CandidateTopN_single_business_day`

It is not a direct expected-return forecast, not a JPY value, and not explicitly
a next-lot marginal value.  In ADD rows, it is used as current PIT opportunity
evidence and as the current side of the same-campaign expected-edge comparison.

## NEW Score Semantic

The NEW score is the non-current-position candidate row's
`runtime_opportunity_score` under the same producer metadata and same daily
candidate population scope.  It is a relative opportunity ranking signal for
initial entry admission and portfolio construction ordering.  It is not a
calibrated initial-lot expected return or JPY marginal value.

## Direct Comparability Judgment

Comparability gate: `ORDINAL_ONLY`.

Both scores are produced by the same score authority, same canonical field, and
same daily population scope, so a same-day rank comparison is coherent as a
relative ordering heuristic.  However, the scores lack calibration and economic
units.  They also represent different lifecycle questions:

- ADD: continuation plus no-loss/current-campaign evidence for an existing
  position's next increment.
- NEW: entry attractiveness for a candidate's initial lot.

Therefore `NEW score > ADD score => NEW_BUY_SUPERIOR` is semantically valid only
as a conservative ordinal opportunity-cost judgment.  It is not proof that the
next yen deployed to NEW has higher expected economic value than the next yen
deployed to the ADD incumbent.

## Marginal Capital Semantic Audit

The current code separates several ideas, but the 24 rows show that final ADD
opportunity cost still relies on a raw score ordering when explicit
opportunity-cost evidence is absent.

| concept | current semantic status |
| --- | --- |
| `SECURITY_QUALITY` | Present through quality/buy-quality and eligibility signals. |
| `ENTRY_ATTRACTIVENESS` | Present for NEW through entry admission, quality action, and opportunity ranking. |
| `HOLD_VALUE` | Present through PM continuation/retain decisions. |
| `ADD_WORTHINESS` | Present, but often reduced/no-add and not always converted to positive marginal capital. |
| `NEXT_LOT_MARGINAL_VALUE` | Not explicitly calibrated or economic. |
| `PORTFOLIO_OPPORTUNITY_COST` | Present as PC comparison, but in these rows depends on uncalibrated same-day score ordering. |

The semantic gap is not that ADD evidence disappears.  Phase32-D already ruled
out a propagation defect.  The gap is that ADD and NEW are compared as if raw
relative opportunity-score superiority were enough to decide next-lot marginal
capital, while the architecture says expected edge is economic justification
versus alternatives including Cash, and the score metadata explicitly says no
economic units are available.

## Spring vs Plateau Structural Comparison

Spring positive control:

- Spring window `2023-03-01` to `2023-05-30`: PM ADD `16`, positive ADD `0`,
  comparison-resolution pattern `5`.
- Plateau window `2023-05-31` to `2024-02-26`: PM ADD `60`, positive ADD `5`,
  comparison-resolution pattern `24`.

Spring avoided the limitation because the profit engine formed primarily through
NEW initial deployments, not through incumbent ADD capitalization.  Candidate
discovery and initial NEW lot/notional were enough to create concentration in
winners.  ADD candidates were sparse and not required to carry portfolio-level
performance.

The plateau/later state differed structurally:

- incumbent positions already existed, so ADD became a recurring capital
  conversion path rather than an edge case;
- simultaneous NEW candidates were abundant and often had higher daily relative
  scores;
- Cash optionality was frequently elevated and Risk Pacing was mostly cautious
  or gradual;
- current positions often had modest weights/notionals, so raw continuation
  evidence did not automatically become portfolio-moving capital;
- the few-winner spring payoff did not repeat at sufficient notional.

## 24-Row Subtype Classification

Primary subtype classification:

| subtype | count | rationale |
| --- | ---: | --- |
| `NOT_DIRECTLY_COMPARABLE` | 24 | ADD and NEW scores are same-authority ordinal signals, but not calibrated next-lot economic values. |
| `NEW_CLEARLY_SUPERIOR_BY_VALID_SEMANTIC` | 0 | No row has economic-unit evidence proving NEW's next yen dominates ADD's next yen. |
| `ADD_AND_NEW_EFFECTIVELY_TIED` | 0 | Smallest raw gap is `0.028649`; still uncalibrated, but no exact/tiny tie by the inspected score surface. |
| `SCORE_DIFFERENCE_NOT_MEANINGFUL` | 0 as exclusive class | The non-meaningfulness is captured by the broader `NOT_DIRECTLY_COMPARABLE` class. |
| `ADD_VALUE_UNDERREPRESENTED` | 0 proven, 24 possible | Not provable without a next-lot marginal-value producer. |
| `NEW_VALUE_OVERREPRESENTED` | 0 proven, 24 possible | Not provable without a calibrated or lifecycle-normalized producer. |
| `OTHER` | 0 | No residual unexplained row. |

This classification is decision-time only.  It uses no future returns, fills,
MFE/MAE, paper ledger PnL, or hindsight outcome labels.

## Positive 5 Comparison

The five positive ADD controls in the plateau differ cleanly from the 24 rows:
their ADD score exceeded the best same-day NEW score, so opportunity cost passed,
incremental value was `POSITIVE`, and canonical ADD allocation was positive.

| date | ADD | ADD score | prior | delta | current weight | notional | requested ADD | accepted ADD | best NEW | NEW score | NEW-ADD | Cash | Risk Pacing | PC class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023-05-31 | 30410 | 0.453926 | 0.421966 | 0.031960 | 0.075186 | 131500 | 0.072806 | 0.072806 | 21340 | 0.341822 | -0.112104 | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | ELIGIBLE_COMPARABLE |
| 2023-06-13 | 21340 | 0.263256 | 0.259661 | 0.003596 | 0.031623 | 57500 | 0.033333 | 0.001375 | 59550 | 0.180045 | -0.083212 | OPTIONALITY_ELEVATED | CAUTIOUS_DEPLOYMENT | ELIGIBLE_COMPARABLE |
| 2023-06-19 | 59550 | 0.173720 | 0.166215 | 0.007505 | 0.035301 | 63600 | 0.029412 | 0.005884 | 67310 | 0.143161 | -0.030558 | OPTIONALITY_LOW | NORMAL_DEPLOYMENT | ELIGIBLE_COMPARABLE |
| 2023-06-20 | 59550 | 0.176932 | 0.173720 | 0.003212 | 0.040449 | 70700 | 0.030303 | 0.005506 | 99840 | 0.102968 | -0.073964 | OPTIONALITY_NEUTRAL | NORMAL_DEPLOYMENT | ELIGIBLE_COMPARABLE |
| 2023-06-22 | 21340 | 0.296073 | 0.293009 | 0.003064 | 0.044973 | 74400 | 0.052632 | 0.001709 | 67310 | 0.164106 | -0.131967 | OPTIONALITY_NEUTRAL | NORMAL_DEPLOYMENT | ELIGIBLE_COMPARABLE |

These controls confirm that PC can allocate positive ADD when the same ordinal
score comparison favors ADD and the rest of ADD evidence passes.  They do not
prove that the ordinal comparison is economically complete.

## 2023-06-20 / 21340 Zero-Delta Audit

`2023-06-20 / 21340` is not one of the 24 comparison-resolution rows.
It had:

- ADD score `0.333663`, prior `0.325212`, delta `+0.008451`
- best NEW `99840` score `0.102968`; ADD beat NEW by `0.230695`
- opportunity cost `PASS`
- incremental value `POSITIVE`
- canonical ADD competitor eligibility `PASS`
- current weight `0.049716`, current notional `86400`
- requested ADD `0.030303`
- canonical competitor accepted ADD `0`
- final target weight remained `0.049716`
- reason codes include `ADD_COMPETITOR_ELIGIBLE`, `ADD_LOST_TO_NEW_BUY`,
  `ADD_NO_POSITIVE_DELTA`, and `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`
- lot/PS authority remains preserved; PC does not calculate final quantity

Classification: `NO` production defect from the Phase32-E semantic lens.  It is
a residual/lot-aware final-allocation interaction candidate, not an ADD-vs-NEW
score comparability defect.  The row should remain in the shadow trace because
it exposes a confusing surface: positive ADD evidence existed, but final
executable ADD was zero after downstream canonical allocation/lot treatment.

## High-Resolution Relevance

Current architecture SoT:
`docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`.

Relevance judgment: `HIGH_RESOLUTION_RECONSIDERATION_STRONGLY_JUSTIFIED` for
shadow/spec work, not production behavior.

The evidence supports a future high-resolution marginal-capital value layer that
separates:

- ADD next-lot marginal value
- NEW initial-lot marginal value
- current hold value
- opportunity cost versus Cash
- risk pacing and concentration headroom
- lot/quantity feasibility under PS authority

It does not support direct ADD priority, score threshold changes, or portfolio
rotation implementation now.

## Shadow Spec Implications

A minimal shadow row should include:

- `business_date`
- `add_symbol`
- `add_campaign_id`
- `pm_action`
- `pm_reason_codes`
- `add_score`
- `add_score_authority`
- `add_score_semantic`
- `add_prior_score`
- `add_score_delta`
- `current_position_weight`
- `current_position_notional`
- `requested_add_weight`
- `accepted_add_weight`
- `best_new_symbol`
- `best_new_score`
- `best_new_score_authority`
- `best_new_score_semantic`
- `raw_score_gap`
- `comparison_class`
- `comparability_status`
- `opportunity_cost_result`
- `cash_preference_semantic`
- `risk_pacing_intent`
- `pc_marginal_class`
- `final_capital_outcome`
- `future_information_used=false`
- `authoritative=false`
- `feeds_position_sizing=false`
- `feeds_runtime=false`

Recommended values for the 24 rows:

- `comparison_class=ADD_VS_NEW_SCORE_ORDERING`
- `comparability_status=ORDINAL_ONLY`
- `final_capital_outcome=ADD_ZERO`
- `authoritative=false`

## Defect / Limitation Classification

| question | judgment |
| --- | --- |
| Evidence propagation defect | `NO` |
| Score semantic loss | `NO` for metadata, `PARTIAL` for economic interpretation |
| Direct ADD/NEW comparability | `PARTIAL` |
| Marginal capital semantic gap | `YES` |
| Production repair justified | `NO` |
| Implementation ready | `NO` for behavior, `YES` for shadow-spec-only |

## Degradation Risks

Any future repair must preserve:

- G129 BUY_ADD actual path
- G140 Risk Pacing
- Cash as first-class alternative
- NEW competition
- PM/PC authority separation
- PS quantity authority
- Runtime no-redecision
- Safety and concentration caps
- Production/Demo/Historical alignment
- future leakage prohibition

Forbidden repair shape: simple ADD priority, PM ADD forcing PC allocation,
Runtime redecision, calibrated-return claims from uncalibrated scores, or
replay-derived/hindsight tuning.

## Next-Step Recommendation

Minimal next change:

1. Add a shadow-only comparability trace/spec for ADD-vs-NEW rows.
2. Keep it non-authoritative and disconnected from PS/Runtime/Submit.
3. Re-audit plateau rows with explicit `ORDINAL_ONLY` versus any future
   `NEXT_LOT_MARGINAL_VALUE` producer.
4. Do not modify production allocation until the next-lot semantic is explicit,
   PIT, authority-owned, and regression-protected.

## Final Judgments

```text
PHASE32_E_COMPARISON_ROWS = 24

PHASE32_E_ADD_NEW_SCORE_DIRECTLY_COMPARABLE = PARTIAL

PHASE32_E_ADD_SCORE_SEMANTIC = OPPORTUNITY_RANKING_AUTHORITY.runtime_opportunity_score / uncalibrated_relative_model_score / same-day CandidateTopN ordinal opportunity evidence for an existing-position ADD row; not calibrated expected return, not JPY value, not explicit next-lot marginal value.
PHASE32_E_NEW_SCORE_SEMANTIC = OPPORTUNITY_RANKING_AUTHORITY.runtime_opportunity_score / uncalibrated_relative_model_score / same-day CandidateTopN ordinal opportunity evidence for a non-current-position NEW candidate; not calibrated initial-lot expected return or JPY value.

PHASE32_E_NEW_BUY_SUPERIOR_JUDGMENT_SEMANTICALLY_VALID = PARTIAL

PHASE32_E_MARGINAL_CAPITAL_SEMANTIC_GAP = YES

PHASE32_E_LATER_STATE_STRUCTURAL_TRIGGER = incumbent ADD candidates plus abundant simultaneous NEW candidates, elevated Cash optionality, cautious/gradual Risk Pacing, modest incumbent weights, and winner continuation that required next-lot capitalization rather than only initial NEW entry.

PHASE32_E_SPRING_AVOIDED_LIMITATION_BECAUSE = spring performance was driven by NEW initial allocations and natural concentration; PM ADD volume was low and positive ADD was not needed to create the main winner payoff.

PHASE32_E_COMPARISON_RESOLUTION_LIMITATION_MATERIAL = YES

PHASE32_E_WINNER_CAPITALIZATION_IMPACT_MATERIAL = PARTIAL

PHASE32_E_ZERO_DELTA_CASE_DEFECT = NO

PHASE32_E_HIGH_RESOLUTION_RECONSIDERATION = STRONG

PHASE32_E_PRODUCTION_REPAIR_JUSTIFIED = NO

PHASE32_E_IMPLEMENTATION_READY = NO

PHASE32_E_MINIMAL_NEXT_CHANGE = shadow-only ADD-vs-NEW comparability trace/spec with score authority, score semantics, raw gap, comparability status, opportunity-cost result, Cash, Risk Pacing, PC marginal class, and final capital outcome.

PHASE32_E_NEXT_STEP = Phase32-F shadow spec / observability materialization for ADD-vs-NEW marginal comparability; no production behavior change.
```
