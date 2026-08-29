# Phase32-D - ADD Evidence Bridge Shadow Audit

## Executive Summary

`Phase32-D` continued the ADD capitalization audit after `Phase32-C`. The task
was READ-ONLY / SHADOW design audit only. No production behavior was changed.

Canonical plateau ADD remains:

```text
PM ADD = 60
PC ADD considered = 60
PC positive ADD = 5
```

The core question was whether the `54` insufficient-evidence ADD rows truly
lacked decision-time evidence, or whether available evidence was lost,
coarsened, or made incomparable between PM and PC.

Finding: the dominant cause is mixed, but not a simple PM-to-PC propagation
defect. PC received the PM ADD action, PM reason codes, current opportunity
score lineage, campaign identity, and no-loss averaging evidence. The failed
rows generally failed because PC's ADD capital contract requires evidence that
PM does not own: prior same-campaign expected-edge comparison and same-day
opportunity-cost superiority over NEW alternatives.

The `54` insufficient rows decompose as:

| Taxonomy | Count | Share |
| --- | ---: | ---: |
| `TRUE_EVIDENCE_ABSENCE` | 5 | 9.3% |
| `EVIDENCE_NOT_PROPAGATED` | 0 | 0.0% |
| `EVIDENCE_SEMANTIC_LOSS` | 0 | 0.0% |
| `COMPARISON_RESOLUTION_LIMIT` | 24 | 44.4% |
| `CORRECTLY_INSUFFICIENT` | 25 | 46.3% |
| `OTHER / UNRESOLVED` | 0 | 0.0% |

Thus, "証拠がない" is true only for the `5` rows where the required prior
baseline was absent. For the other `49` insufficient rows, evidence exists and
reaches PC, but current semantics either show weakening expected edge (`25`) or
show improving ADD evidence that still loses to stronger same-day NEW by the
current uncalibrated score comparison (`24`).

Recommended next step is an observability-only
`canonical_add_evidence_bridge_shadow.v1` spec. It should not alter ADD
admission, ADD allocation, Risk Pacing, Cash discipline, NEW competition,
Safety, PS quantity authority, or Runtime behavior.

## 60 ADD Canonical Reconciliation

Audited target:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
plateau window: 2023-05-31 through 2024-02-26
```

Canonical surfaces reconcile:

| Surface | Count |
| --- | ---: |
| `position_management.positions[].action == ADD` | 60 |
| `portfolio_construction.portfolio_members[].pm_action == ADD` | 60 |
| `capital_competition.competitors[].competitor_type == ADD` | 60 |
| PC positive ADD allocation | 5 |
| PC ADD rejected / zero allocation | 55 |
| PC ADD insufficient-evidence rows | 54 |

There is no canonical PM-to-PC ADD admission loss in this window.

## 60 Row Compact Trace

Columns:

- `Delta` = current expected-edge score minus prior same-campaign baseline.
- `Req` / `Acc` = requested / accepted ADD weight from PC capital competition.
- `Bucket` = Phase32-D diagnostic classification.

| Date | Symbol | Edge | Delta | Increment | Opp Cost | Best NEW | Add Worth | Cur W | Req | Acc | Outcome | Bucket |
| --- | --- | --- | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- |
| 2023-05-31 | 30410 | IMPROVING | +0.031960 | POSITIVE | PASS | 0.341822 | ADD_REDUCED_ONLY | 0.075186 | 0.072806 | 0.072806 | SELECTED | POSITIVE_ADD |
| 2023-05-31 | 59550 | IMPROVING | +0.008224 | UNKNOWN | NEW_BUY_SUPERIOR | 0.341822 | ADD_REDUCED_ONLY | 0.043462 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-01 | 59550 | WEAKENING | -0.057997 | UNKNOWN | NEW_BUY_SUPERIOR | 0.342168 | NO_ADD | 0.039591 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-06 | 21340 | UNKNOWN | n/a | UNKNOWN | NEW_BUY_SUPERIOR | 0.334280 | ADD_REDUCED_ONLY | 0.031063 | 0 | 0 | REJECTED | TRUE_EVIDENCE_ABSENCE |
| 2023-06-07 | 21340 | IMPROVING | +0.003692 | UNKNOWN | NEW_BUY_SUPERIOR | 0.308823 | ADD_REDUCED_ONLY | 0.027046 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-08 | 21340 | IMPROVING | +0.018260 | UNKNOWN | NEW_BUY_SUPERIOR | 0.312707 | NO_ADD | 0.028199 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-09 | 21340 | IMPROVING | +0.018335 | UNKNOWN | NEW_BUY_SUPERIOR | 0.316079 | ADD_REDUCED_ONLY | 0.028666 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-13 | 21340 | IMPROVING | +0.003596 | POSITIVE | PASS | 0.180045 | ADD_REDUCED_ONLY | 0.031623 | 0.033333 | 0.001375 | SELECTED | POSITIVE_ADD |
| 2023-06-16 | 21340 | WEAKENING | -0.027984 | UNKNOWN | PASS | 0.130122 | NO_ADD | 0.048899 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-16 | 59550 | UNKNOWN | n/a | UNKNOWN | PASS | 0.130122 | ADD_REDUCED_ONLY | 0.034637 | 0 | 0 | REJECTED | TRUE_EVIDENCE_ABSENCE |
| 2023-06-19 | 59550 | IMPROVING | +0.007505 | POSITIVE | PASS | 0.143161 | ADD_REDUCED_ONLY | 0.035301 | 0.029412 | 0.005884 | SELECTED | POSITIVE_ADD |
| 2023-06-20 | 21340 | IMPROVING | +0.008451 | POSITIVE | PASS | 0.102968 | NO_ADD | 0.049716 | 0.030303 | 0 | REJECTED | POSITIVE_EVIDENCE_ZERO_DELTA |
| 2023-06-20 | 40520 | WEAKENING | -0.000452 | UNKNOWN | PASS | 0.102968 | NO_ADD | 0.081443 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-20 | 59550 | IMPROVING | +0.003212 | POSITIVE | PASS | 0.102968 | ADD_REDUCED_ONLY | 0.040449 | 0.030303 | 0.005506 | SELECTED | POSITIVE_ADD |
| 2023-06-21 | 21340 | WEAKENING | -0.040654 | UNKNOWN | PASS | 0.142132 | NO_ADD | 0.047326 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-21 | 40520 | WEAKENING | -0.016756 | UNKNOWN | NEW_BUY_SUPERIOR | 0.142132 | ADD_REDUCED_ONLY | 0.080629 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-22 | 21340 | IMPROVING | +0.003064 | POSITIVE | PASS | 0.164106 | ADD_REDUCED_ONLY | 0.044973 | 0.052632 | 0.001709 | SELECTED | POSITIVE_ADD |
| 2023-06-23 | 40520 | IMPROVING | +0.052655 | UNKNOWN | NEW_BUY_SUPERIOR | 0.206826 | NO_ADD | 0.079509 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-26 | 40520 | IMPROVING | +0.029956 | UNKNOWN | NEW_BUY_SUPERIOR | 0.247763 | ADD_REDUCED_ONLY | 0.083263 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-27 | 40520 | IMPROVING | +0.020009 | UNKNOWN | NEW_BUY_SUPERIOR | 0.287613 | ADD_REDUCED_ONLY | 0.081615 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-06-28 | 40520 | WEAKENING | -0.017757 | UNKNOWN | NEW_BUY_SUPERIOR | 0.256945 | ADD_REDUCED_ONLY | 0.083716 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-06-29 | 40520 | WEAKENING | -0.017979 | UNKNOWN | NEW_BUY_SUPERIOR | 0.251292 | ADD_REDUCED_ONLY | 0.081286 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-08-23 | 65730 | WEAKENING | -0.219076 | UNKNOWN | NEW_BUY_SUPERIOR | 0.291244 | NO_ADD | 0.063884 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-08-24 | 65730 | WEAKENING | -0.101274 | UNKNOWN | NEW_BUY_SUPERIOR | 0.282002 | NO_ADD | 0.055485 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-08-28 | 65730 | WEAKENING | -0.058087 | UNKNOWN | NEW_BUY_SUPERIOR | 0.260482 | ADD_REDUCED_ONLY | 0.053415 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-09-26 | 94340 | IMPROVING | +0.026372 | UNKNOWN | NEW_BUY_SUPERIOR | 0.399808 | NO_ADD | 0.028479 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-09-27 | 94340 | IMPROVING | +0.005641 | UNKNOWN | NEW_BUY_SUPERIOR | 0.372074 | ADD_REDUCED_ONLY | 0.028386 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-09-28 | 94340 | IMPROVING | +0.053735 | UNKNOWN | NEW_BUY_SUPERIOR | 0.367018 | ADD_REDUCED_ONLY | 0.028457 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-09-29 | 94340 | IMPROVING | +0.022798 | UNKNOWN | NEW_BUY_SUPERIOR | 0.390168 | ADD_REDUCED_ONLY | 0.027455 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-02 | 94340 | IMPROVING | +0.054238 | UNKNOWN | NEW_BUY_SUPERIOR | 0.435758 | ADD_REDUCED_ONLY | 0.027209 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-03 | 94340 | IMPROVING | +0.047432 | UNKNOWN | NEW_BUY_SUPERIOR | 0.471282 | ADD_REDUCED_ONLY | 0.027249 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-04 | 94340 | IMPROVING | +0.073022 | UNKNOWN | NEW_BUY_SUPERIOR | 0.540190 | ADD_REDUCED_ONLY | 0.026887 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-05 | 94340 | WEAKENING | -0.045662 | UNKNOWN | NEW_BUY_SUPERIOR | 0.487562 | ADD_REDUCED_ONLY | 0.027436 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-10-06 | 94340 | WEAKENING | -0.035353 | UNKNOWN | NEW_BUY_SUPERIOR | 0.473355 | ADD_REDUCED_ONLY | 0.027038 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-10-10 | 94340 | WEAKENING | -0.061105 | UNKNOWN | NEW_BUY_SUPERIOR | 0.435207 | ADD_REDUCED_ONLY | 0.027486 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-10-11 | 94340 | WEAKENING | -0.029895 | UNKNOWN | NEW_BUY_SUPERIOR | 0.409102 | ADD_REDUCED_ONLY | 0.027774 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-10-13 | 94340 | IMPROVING | +0.065197 | UNKNOWN | NEW_BUY_SUPERIOR | 0.428728 | ADD_REDUCED_ONLY | 0.027548 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-16 | 94340 | IMPROVING | +0.023863 | UNKNOWN | NEW_BUY_SUPERIOR | 0.487575 | ADD_REDUCED_ONLY | 0.027705 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-10-17 | 94340 | WEAKENING | -0.030397 | UNKNOWN | NEW_BUY_SUPERIOR | 0.504267 | ADD_REDUCED_ONLY | 0.027496 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-11-21 | 87830 | UNKNOWN | n/a | UNKNOWN | NEW_BUY_SUPERIOR | 0.371669 | ADD_REDUCED_ONLY | 0.030764 | 0 | 0 | REJECTED | TRUE_EVIDENCE_ABSENCE |
| 2023-11-24 | 87830 | WEAKENING | -0.033965 | UNKNOWN | NEW_BUY_SUPERIOR | 0.354385 | NO_ADD | 0.035720 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-11-27 | 87830 | WEAKENING | -0.011043 | UNKNOWN | NEW_BUY_SUPERIOR | 0.377857 | NO_ADD | 0.034605 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-12-11 | 60720 | UNKNOWN | n/a | UNKNOWN | NEW_BUY_SUPERIOR | 0.495352 | ADD_REDUCED_ONLY | 0.034365 | 0 | 0 | REJECTED | TRUE_EVIDENCE_ABSENCE |
| 2023-12-12 | 60720 | WEAKENING | -0.003511 | UNKNOWN | NEW_BUY_SUPERIOR | 0.486616 | ADD_REDUCED_ONLY | 0.034072 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-12-13 | 60720 | IMPROVING | +0.021499 | UNKNOWN | NEW_BUY_SUPERIOR | 0.511767 | ADD_REDUCED_ONLY | 0.035103 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-12-14 | 60720 | WEAKENING | -0.004438 | UNKNOWN | NEW_BUY_SUPERIOR | 0.518660 | ADD_REDUCED_ONLY | 0.034966 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-12-18 | 60720 | IMPROVING | +0.023200 | UNKNOWN | NEW_BUY_SUPERIOR | 0.506272 | ADD_REDUCED_ONLY | 0.035720 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2023-12-19 | 60720 | WEAKENING | -0.005432 | UNKNOWN | NEW_BUY_SUPERIOR | 0.500083 | ADD_REDUCED_ONLY | 0.035958 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-12-20 | 60720 | WEAKENING | -0.014317 | UNKNOWN | NEW_BUY_SUPERIOR | 0.505281 | ADD_REDUCED_ONLY | 0.037545 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2023-12-21 | 60720 | WEAKENING | -0.003697 | UNKNOWN | NEW_BUY_SUPERIOR | 0.519226 | ADD_REDUCED_ONLY | 0.036275 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2024-02-01 | 92490 | UNKNOWN | n/a | UNKNOWN | NEW_BUY_SUPERIOR | 0.401068 | ADD_REDUCED_ONLY | 0.076605 | 0 | 0 | REJECTED | TRUE_EVIDENCE_ABSENCE |
| 2024-02-02 | 92490 | WEAKENING | -0.015586 | UNKNOWN | NEW_BUY_SUPERIOR | 0.382497 | ADD_REDUCED_ONLY | 0.076782 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2024-02-05 | 92490 | IMPROVING | +0.000653 | UNKNOWN | NEW_BUY_SUPERIOR | 0.397018 | NO_ADD | 0.076985 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2024-02-06 | 92490 | IMPROVING | +0.002468 | UNKNOWN | NEW_BUY_SUPERIOR | 0.402918 | ADD_REDUCED_ONLY | 0.076835 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2024-02-07 | 92490 | IMPROVING | +0.006370 | UNKNOWN | NEW_BUY_SUPERIOR | 0.415788 | ADD_REDUCED_ONLY | 0.076818 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2024-02-08 | 92490 | WEAKENING | -0.013853 | UNKNOWN | NEW_BUY_SUPERIOR | 0.409975 | ADD_REDUCED_ONLY | 0.077208 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2024-02-09 | 92490 | IMPROVING | +0.020138 | UNKNOWN | NEW_BUY_SUPERIOR | 0.434422 | ADD_REDUCED_ONLY | 0.079034 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2024-02-13 | 92490 | WEAKENING | -0.005116 | UNKNOWN | PASS | 0.141490 | ADD_REDUCED_ONLY | 0.079345 | 0 | 0 | REJECTED | CORRECTLY_INSUFFICIENT |
| 2024-02-14 | 92490 | IMPROVING | +0.005932 | UNKNOWN | NEW_BUY_SUPERIOR | 0.460465 | ADD_REDUCED_ONLY | 0.078919 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |
| 2024-02-15 | 92490 | IMPROVING | +0.015162 | UNKNOWN | NEW_BUY_SUPERIOR | 0.480555 | ADD_REDUCED_ONLY | 0.078663 | 0 | 0 | REJECTED | COMPARISON_RESOLUTION_LIMIT |

All rows carried PM reason evidence consistent with:

```text
no_loss_averaging
opportunity_rank_still_high
strong_trend_continuation
```

This PM evidence reached PC as source reason evidence. It did not, by itself,
satisfy PC's incremental capital evidence contract.

## 54 Insufficient-Evidence Taxonomy

| Taxonomy | Count | Explanation |
| --- | ---: | --- |
| `TRUE_EVIDENCE_ABSENCE` | 5 | current score existed, but prior same-campaign baseline score/date was absent, so expected-edge comparison became UNKNOWN |
| `EVIDENCE_NOT_PROPAGATED` | 0 | PM ADD, PM reason codes, campaign, current score lineage, and no-loss evidence were present at PC |
| `EVIDENCE_SEMANTIC_LOSS` | 0 | no direct loss of PM evidence was observed; the mismatch is contract strictness, not field loss |
| `COMPARISON_RESOLUTION_LIMIT` | 24 | expected edge improved, but same-day NEW score was higher, making opportunity cost fail and incremental value UNKNOWN |
| `CORRECTLY_INSUFFICIENT` | 25 | expected edge weakened by current-vs-prior same-campaign comparison |
| `OTHER / UNRESOLVED` | 0 | no row required an unclassified bucket |

The remaining non-positive row, `2023-06-20 / 21340`, was not counted in the
54 insufficient rows. It had positive bridge evidence but ended at zero
accepted ADD with `ADD_LOST_TO_NEW_BUY`, `ADD_NO_POSITIVE_DELTA`, and
`REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`.

## Positive 5 vs Negative 54

The positive five shared:

```text
expected_edge.status = PASS
expected_edge.state = IMPROVING
incremental_value.status = PASS
incremental_value.state = POSITIVE
opportunity_cost.status = PASS
campaign_continuation.status = PASS
no_loss_averaging.status = PASS
```

The negative 54 did not fail because PM reason evidence disappeared. They
failed because one of PC's required capital tests failed:

- `5` had no prior baseline for expected-edge comparison;
- `25` had prior baseline and current score, but the score delta was negative;
- `24` had improving expected edge, but a same-day NEW alternative had higher
  score, so opportunity cost failed and incremental value remained UNKNOWN.

Therefore the five were not merely lucky. They were the cases where all PC
capital evidence predicates aligned.

## Expected Edge Lineage

Producer:

```text
ai_fund_lab_v2.strategy.add_investment_evidence
producer_version = phase28_d55_a_add_investment_evidence_resolver.v1
```

Expected edge is resolved from:

```text
current_score = expected_edge_current_score or runtime_opportunity_score
baseline_score = expected_edge_baseline_score
              or previous_expected_edge_score
              or entry_expected_edge_baseline_score
baseline_date = expected_edge_baseline_business_date
             or previous_expected_edge_business_date
             or entry_expected_edge_baseline_business_date
             or add_expected_edge_baseline_business_date
```

Pass condition:

```text
IMPROVING
or STABLE_ADEQUATE with stable_adequate_opportunity_cost_superior = PASS
```

UNKNOWN condition:

```text
required prior baseline date / score absent
or invalid temporal baseline
```

In the `5` UNKNOWN rows, PC had a current opportunity score and source lineage,
but no valid prior baseline date/score. This is genuine absence of the specific
PIT baseline evidence required by the current contract.

## Incremental Value Lineage

Incremental value is resolved as:

```text
explicit incremental_investment_value_state if present
else POSITIVE only when expected_edge, campaign_continuation,
     opportunity_cost, and no_loss_averaging all PASS
else UNKNOWN
```

This explains why `54 / 55` non-positive ADD competitors carried
`incremental_value = UNKNOWN`: it is a cascade result, not necessarily absence
of all evidence. In `25` rows, expected edge weakened. In `24` rows,
opportunity cost failed because NEW was superior by current same-day score.

The PM evidence was present, but PM's strong continuation reason is not enough
to satisfy PC's stricter incremental-capital proof.

## Opportunity Cost / NEW / Cash Comparison

Opportunity cost is resolved by comparing the ADD candidate's
`runtime_opportunity_score` against same-day NEW candidate scores.

Observed:

| Result | Count Among 55 Non-positive |
| --- | ---: |
| `NEW_BUY_SUPERIOR` | 49 |
| `PASS` | 6 |

Competition outcome labels:

| Outcome | Count |
| --- | ---: |
| `ADD_LOST_TO_NEW_BUY` | 47 |
| `ADD_LOST_TO_CASH` | 8 |

The `47` NEW losses are mostly not "ADD evidence lost"; they are ADD failing
the current same-day score comparison. The `8` Cash losses mostly occurred
when no deployable security ADD survived and Cash remained first-class. Cash
reason codes included optionality and policy-reserve semantics such as
`OPTIONALITY_ELEVATED`, `MARGINAL_OPPORTUNITY_SET`, `NO_VALID_COMPETITOR`, and
`VALID_POLICY_RESERVE`.

The comparison representation is coarse because scores are uncalibrated
relative model scores rather than economic payoff units. That is why this audit
classifies `24` rows as `COMPARISON_RESOLUTION_LIMIT`, not as a propagation
defect.

## Evidence Propagation Audit

No material evidence-not-propagated defect was found.

Observed at PC for canonical ADD rows:

- PM action `ADD`;
- PM source reason codes;
- current position and campaign identity;
- current opportunity score and score authority lineage;
- prior same-campaign baseline when available;
- no-loss averaging evidence from PM reason codes;
- same-day NEW score comparison;
- Cash/Risk Pacing evidence;
- final PC reason codes.

The missing item in the `5` UNKNOWN rows is the prior same-campaign baseline,
not the current PM ADD evidence.

## Semantic-Loss Audit

Material semantic loss was not proven. The subtle issue is semantic separation:

- PM ADD says the existing position has continuation/add-worthiness evidence.
- PC ADD capital requires incremental capital superiority.

These are intentionally different concepts. Treating PM ADD as automatic
capital would violate the accepted authority boundary.

However, the audit also shows an observability gap: today's artifacts require
multi-artifact reconstruction to see why PM evidence was insufficient for PC.
That is a shadow observability problem worth fixing.

## Shadow Artifact Recommendation

Recommendation:

```text
canonical_add_evidence_bridge_shadow.v1 = YES
```

Authority status:

```text
SHADOW_NON_AUTHORITATIVE
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_submit = false
feeds_execution = false
```

Suggested row fields:

| Field Group | Fields |
| --- | --- |
| Identity | business_date, symbol, position_campaign_id, source_pm_decision_ref |
| PM | pm_action, pm_reason_codes, pm_confidence, pm_intensity |
| Current position | current_quantity, current_weight, current_notional |
| Expected edge | current_score, baseline_score, baseline_date, delta, state, status, unknown_reason |
| Incremental value | source predicates, state, status, reason_codes |
| Opportunity cost | add_score, best_new_score, best_new_symbol, comparison_result |
| Cash/Risk | cash_preference_semantic, cash_reason_codes, risk_pacing_intent |
| PC outcome | requested_add_weight, accepted_add_weight, marginal_classification, final_reason_codes |
| Quantity | one_lot_weight, executable_quantity_delta, final_allocated_quantity |
| Safety | concentration_status, safety_cap_status, future_information_used |

The shadow artifact should exist only to make this lineage auditable:

```text
PM ADD reason
-> PC received evidence
-> evidence transformation
-> incremental value
-> opportunity cost
-> NEW/Cash comparison
-> final ADD outcome
```

## Degradation Risks

No behavior change is recommended from this audit. If later work goes beyond
shadow observability, protect against:

- Cash discipline degradation;
- over-ADD into losers;
- position concentration increase;
- Risk Pacing bypass;
- NEW opportunity starvation;
- PM authority becoming de facto PC capital authority;
- PS quantity authority duplication;
- Runtime redecision.

Required protections:

- G129 BUY_ADD actual path;
- G140 Risk Pacing independent value;
- Cash first-class alternative;
- NEW competition;
- PM / PC authority separation;
- PS quantity authority;
- Runtime no-redecision;
- Safety/concentration caps;
- Production / Demo / Historical canonical alignment;
- future leakage prohibition.

## Next Step Recommendation

Recommended next task:

```text
Phase32-E - canonical_add_evidence_bridge_shadow.v1 Specification
```

Scope:

- documentation/spec only, or shadow artifact implementation only if explicitly
  approved;
- no production behavior change;
- no ADD condition loosening;
- no High-Resolution Value or Rotation implementation.

## Files Inspected

- `docs/phase_reports/phase32_c_add_capitalization_admission_competition_semantic_audit.md`
- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`
- daily artifacts under
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/`

## Commands Executed

```text
sed -n ... Phase32-D pasted request
git status --short
rg -n ... add investment evidence and expected-edge lineage
sed -n ... add_investment_evidence.py
nl -ba ... portfolio_construction.py source inspection
jq ... artifact shape checks
python3 - <<'PY' ... canonical 60 ADD row lineage aggregation
python3 - <<'PY' ... 54 insufficient-evidence taxonomy aggregation
```

No tests, fresh-run, resume, replay, long Historical, full backtest,
production command, model training, or production implementation command was
executed.

## Final Judgments

`PHASE32_D_CANONICAL_ADD_TOTAL = 60`

`PHASE32_D_POSITIVE_ADD = 5`

`PHASE32_D_INSUFFICIENT_EVIDENCE_ROWS = 54`

`PHASE32_D_TRUE_EVIDENCE_ABSENCE = 5`

`PHASE32_D_EVIDENCE_NOT_PROPAGATED = 0`

`PHASE32_D_EVIDENCE_SEMANTIC_LOSS = 0`

`PHASE32_D_COMPARISON_RESOLUTION_LIMIT = 24`

`PHASE32_D_CORRECTLY_INSUFFICIENT = 25`

`PHASE32_D_UNRESOLVED = 0`

`PHASE32_D_EXPECTED_EDGE_UNKNOWN_ROOT_CAUSE = PRIOR_SAME_CAMPAIGN_BASELINE_SCORE_OR_DATE_ABSENT`

`PHASE32_D_INCREMENTAL_VALUE_UNKNOWN_ROOT_CAUSE = CASCADE_FAIL_CLOSED_FROM_EXPECTED_EDGE_WEAK_OR_UNKNOWN_OR_OPPORTUNITY_COST_NEW_BUY_SUPERIOR`

`PHASE32_D_EVIDENCE_PROPAGATION_DEFECT = NO`

`PHASE32_D_EVIDENCE_SEMANTIC_LOSS_MATERIAL = NO`

`PHASE32_D_MARGINAL_COMPARISON_LIMITATION_MATERIAL = PARTIAL`

`PHASE32_D_PRIMARY_ROOT_CAUSE = MIXED`

`PHASE32_D_SHADOW_EVIDENCE_BRIDGE_NEEDED = YES`

`PHASE32_D_PRODUCTION_REPAIR_JUSTIFIED = NO`

`PHASE32_D_IMPLEMENTATION_READY = YES_FOR_SHADOW_SPEC_ONLY; NO_FOR_PRODUCTION_BEHAVIOR`

`PHASE32_D_MINIMAL_NEXT_CHANGE = CANONICAL_ADD_EVIDENCE_BRIDGE_SHADOW_SPEC_ONLY`

`PHASE32_D_NEXT_STEP = Phase32-E - canonical_add_evidence_bridge_shadow.v1 Specification`
