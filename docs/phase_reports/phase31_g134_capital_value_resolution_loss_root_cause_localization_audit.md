# Phase31-G134 — Capital Value Resolution Loss Root-Cause Localization Audit

## Final Decision

`G134_VALUE_RESOLUTION_ARCHITECTURE_LIMITATION_LOCALIZED_READY_FOR_NEXT_PHASE_DESIGN`

## Scope

Task type: READ-ONLY root-cause audit.

Primary run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Completed immutable artifacts audited:

`2022-10-03` through `2023-03-03`

Primary windows:

- A: `2022-11-21` through `2022-12-12`
- B: `2023-01-23` through latest completed BULL date, `2023-03-03`

No code, config, threshold, weight, model, fresh-run, resume, replay, long Historical, or run mutation was performed.

FUTURE_INFORMATION_USED_FOR_ROOT_CAUSE_JUDGMENT = `NO`

## Source Basis

Required reports read:

- `docs/phase_reports/phase31_g133_bull_internal_opportunity_quality_capital_allocation_behavior_audit.md`
- `docs/phase_reports/phase31_g132_unified_capital_frontier_decision_time_value_quality_characterization.md`
- `docs/phase_reports/phase31_g131_unified_add_new_cash_marginal_capital_authority_design_acceptance.md`
- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`

Relevant G112-G128 reports and Architecture SoT under `docs/02_architecture/` were inspected for the accepted contracts around Strategy Intelligence, Candidate AI, PM, PC, PS, Market Quality, Risk Pacing, Market-Candidate-Cash, G115 staged ADD, and PIT safety.

Key SoT constraints:

- `COMPARABLE_MARGINAL` is intentionally valid but marginal.
- `CASH_PREFERRED_PARTICIPATION_VALID` is not proof that a security strictly beats Cash.
- G115 is staged one-increment ADD authority, not full-block ADD authority.
- PC owns capital allocation; PS owns quantity; Runtime must not re-decide priority.
- Current SoT permits shoulder participation and does not require a calibrated strict single marginal-winner scale.

## Executive Root Cause

WHERE_IS_OPPORTUNITY_VALUE_RESOLUTION_LOST =

`MULTI_CAUSAL`

Dominant components:

1. `TRANSFORMATION_COARSE`: rich upstream NEW_BUY evidence is transformed into coarse `STRONG` / `COMPARABLE_HIGH` / `COMPARABLE_MARGINAL` / `BLOCKED` / `INSUFFICIENT` classes.
2. `MISSING_MARGINAL_DIMENSION`: ADD `incremental_investment_value` is a PIT-safe pass/fail state, but not a numeric next-lot marginal value.
3. `CROSS_TYPE_SEMANTIC_LIMITATION`: NEW_BUY and ADD both have opportunity scores, but NEW_BUY is entry attractiveness while ADD is continuation / no-loss / expected-edge / campaign increment evidence.
4. `G115_FINAL_CLASSIFICATION_COMPRESSION`: PC/G115 final states intentionally collapse many rows into deployment, residual, lot/cap, re-entry, Cash, or one-increment shoulder buckets.

Primary requested classification:

`E = MULTI_CAUSAL`

The current implementation matches the intentionally coarse Phase31 SoT. No existing authoritative contract was found that requires the implementation to preserve a calibrated, high-resolution common marginal value unit across ADD / NEW_BUY / Cash.

MANDATORY_REPAIR_FOUND = `NO`

## Stage Resolution Accounting

Stage definitions used:

| Stage | Read-only state tuple |
| --- | --- |
| STAGE_1_UPSTREAM | competitor type, runtime score, opportunity rank, entry action/state, selection tier, expected-edge state, PM action |
| STAGE_2_INCREMENTAL_VALUE | ADD incremental value state/status; NEW_BUY mapped to current opportunity quality class |
| STAGE_3_OPPORTUNITY_COST | ADD candidate score vs best NEW score; NEW_BUY runtime score |
| STAGE_4_PC_PRE_G115 | opportunity class, interaction result, marginal priority index, quality class order, lot preflight |
| STAGE_5_G115_FINAL | ADD G115 reason tuple or non-ADD quality class plus final PC state |
| PS | lot/quantity compatibility plus final state |

This uses exact artifact fields only. No optimized metric or performance label was created.

### Window A

`2022-11-21` through `2022-12-12`

| Stage | Competitors | Distinct states | Largest identical group |
| --- | ---: | ---: | --- |
| STAGE_1_UPSTREAM | 349 | 349 | `1 / 0.29%` |
| STAGE_2_INCREMENTAL_VALUE | 349 | 5 | `NEW_BUY_NO_IIV + COMPARABLE_MARGINAL / 297 / 85.10%` |
| STAGE_3_OPPORTUNITY_COST | 349 | 349 | `1 / 0.29%` |
| STAGE_4_PC_PRE_G115 | 349 | 61 | `COMPARABLE_MARGINAL + UNKNOWN + class_order 2 / 124 / 35.53%` |
| STAGE_5_G115_FINAL | 349 | 20 | `COMPARABLE_MARGINAL + incremental_budget_zero_allocation / 122 / 34.96%` |
| PS / final | 349 | 8 | `incremental_budget_zero_allocation / 122 / 34.96%` |

Opportunity classes:

| Class | Count |
| --- | ---: |
| COMPARABLE_MARGINAL | 304 |
| COMPARABLE_HIGH | 27 |
| STRONG | 12 |
| BLOCKED | 5 |
| INSUFFICIENT | 1 |

### Window B

`2023-01-23` through `2023-03-03` completed BULL dates.

| Stage | Competitors | Distinct states | Largest identical group |
| --- | ---: | ---: | --- |
| STAGE_1_UPSTREAM | 588 | 588 | `1 / 0.17%` |
| STAGE_2_INCREMENTAL_VALUE | 588 | 5 | `NEW_BUY_NO_IIV + COMPARABLE_MARGINAL / 530 / 90.14%` |
| STAGE_3_OPPORTUNITY_COST | 588 | 588 | `1 / 0.17%` |
| STAGE_4_PC_PRE_G115 | 588 | 57 | `COMPARABLE_MARGINAL + UNKNOWN + class_order 2 / 347 / 59.01%` |
| STAGE_5_G115_FINAL | 588 | 18 | `COMPARABLE_MARGINAL + reentry_opportunity_not_requalified / 206 / 35.03%` |
| PS / final | 588 | 9 | `reentry_opportunity_not_requalified / 210 / 35.71%` |

Opportunity classes:

| Class | Count |
| --- | ---: |
| COMPARABLE_MARGINAL | 534 |
| COMPARABLE_HIGH | 23 |
| BLOCKED | 16 |
| STRONG | 11 |
| INSUFFICIENT | 4 |

PRIMARY_RESOLUTION_LOSS_STAGE = `MULTIPLE`

Interpretation:

- Stage 1 and Stage 3 preserve high cardinality because score/rank and score comparison remain distinct.
- Stage 2 immediately compresses because the common incremental-value representation is categorical and because NEW_BUY has no true next-lot incremental value object.
- Stage 4 and Stage 5 further compress by design into PC opportunity classes, re-entry eligibility, lot/cap/budget reasons, and G115 shoulder / Cash semantics.

## Pairwise Collapse Audit

Clear upstream-different pairs were defined as same-date pairs with competitor type difference, rank gap >= 5, score gap >= 0.10, or different entry/action state. This uses only contemporaneous artifact fields.

| Window | UPSTREAM_DIFFERENT_PAIRS | COLLAPSED_AT_INCREMENTAL_VALUE | COLLAPSED_AT_OPPORTUNITY_COST | COLLAPSED_AT_PC | COLLAPSED_AT_G115 | Signal survival by G115 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A `2022-11-21` to `2022-12-12` | 3,525 | 2,423 | 0 | 403 | 574 | 83.7% |
| B `2023-01-23` to `2023-03-03` BULL | 5,538 | 4,341 | 0 | 1,855 | 812 | 85.3% |
| All BULL | 10,094 | 7,665 | 0 | 2,440 | 1,496 | 85.2% |
| BEAR | 6,887 | 6,291 | 0 | 997 | 1,134 | 83.5% |
| RANGE | 4,260 | 3,410 | 0 | 572 | 657 | 84.6% |
| RECOVERY | 2,693 | 1,993 | 0 | 455 | 308 | 88.6% |

UPSTREAM_SIGNAL_SURVIVAL_RATE_BY_STAGE =

| Stage | Finding |
| --- | --- |
| Incremental value | Weak: large collapse because output is categorical. |
| Opportunity cost | Strong cardinality: score values remain distinct. |
| PC pre-G115 | Partial: many distinct scores/classes collapse into fewer priority states. |
| G115/final | Partial: final action classes collapse heterogeneous rows. |

The high Stage 3 cardinality is important: upstream numeric resolution still exists in artifacts. It is not absent. It is not converted into a common high-resolution capital value scale.

## Candidate-Side Sufficiency

NEW_UPSTREAM_DIFFERENTIATION_SUFFICIENT = `PARTIAL`

Evidence:

- NEW_BUY rows enter PC with runtime opportunity score, opportunity rank, BUY Quality action, quality band/score, entry admission state/action, momentum trajectory evidence, and lineage.
- Stage 1 exact upstream signatures are unique in both primary windows.
- Stage 3 exact score states remain unique for NEW_BUY rows.

Limitation:

- PC opportunity quality converts many materially different NEW_BUY rows into `COMPARABLE_MARGINAL`.
- For example, same-day NEW_BUY rows with materially different rank/score can share final `SELECTED` or the same re-entry / budget / lot state.
- NEW_BUY does not carry an explicit "next executable lot marginal value vs Cash and all current alternatives" object.

Candidate-side evidence is decision-useful, but only partially sufficient for the target high-resolution capital value question.

## ADD-Side Sufficiency

ADD_UPSTREAM_DIFFERENTIATION_SUFFICIENT = `PARTIAL`

Evidence:

- ADD rows include PM action/reasons, campaign state, same-campaign identity, continuation state, expected-edge state, no-loss averaging, incremental investment value, opportunity cost, pre/post quantity and headroom, and lot context.
- Accepted ADD rows are not stale or blindly repeated. They refresh same-date candidate score and best NEW score.

Limitation:

- `incremental_investment_value` is mainly `POSITIVE/PASS` vs `UNKNOWN/FAIL_CLOSED`, not a numeric next-lot value.
- Many non-selected ADD rows with different scores collapse into `ADD_INSUFFICIENT_EVIDENCE` / `ADD_NO_POSITIVE_DELTA`.
- Accepted ADD rows often remain `COMPARABLE_MARGINAL`, not `STRONG` or a calibrated next-lot value.

Existing position / campaign richness creates more evidence dimensions than NEW_BUY, but those dimensions still collapse to a small number of categorical states.

## Cross-Type Normalization

NEW_ADD_VALUE_SEMANTICS_COMMON_UNIT = `PARTIAL`

Exact mismatch:

| Type | Existing semantic |
| --- | --- |
| NEW_BUY | entry attractiveness / candidate rank / runtime opportunity score / BUY Quality |
| ADD | continuation quality / same-campaign state / no-loss averaging / expected edge / opportunity-cost PASS |
| Cash | optionality / residual / market-candidate-cash interaction / participation-vs-deferral |

Both ADD and NEW_BUY can use `runtime_opportunity_score`, but this is not by itself a unified marginal capital value unit. ADD's `opportunity_cost` compares ADD candidate score against best NEW_BUY score, while Cash is handled through composite participation / deferral semantics rather than a numeric Cash delta.

## Incremental Investment Value Decomposition

INCREMENTAL_VALUE_COMPRESSION_SOURCE = `MULTIPLE`

Components:

- `CATEGORICAL_BUCKETING`: ADD incremental value is `POSITIVE`, `UNKNOWN`, or fail-closed shaped in the artifacts.
- `MISSING_MARGINAL_DIMENSION`: The field does not encode a numeric value for "this exact next 100 shares" after the previous lot is consumed.
- `TRANSFORMATION_COARSE`: `marginal_capital_value.py` maps rich row evidence into coarse opportunity classes.

Representative construction:

```text
PM ADD / BUY_NEW origin
+ entry admission action/state
+ selection tier / allocation bias
+ expected-edge / campaign continuation
+ rank and score
+ ADD incremental value and opportunity cost if ADD
-> opportunity_quality_class
```

For ADD:

```text
expected_edge in {IMPROVING, STABLE_ADEQUATE, PASS}
and incremental_value == POSITIVE
and opportunity_cost == PASS
and campaign continuation PASS
-> STRONG / COMPARABLE_HIGH / COMPARABLE_MARGINAL depending mostly on add-worthiness and expected-edge class
```

For NEW_BUY:

```text
entry admission, selection tier, allocation bias, rank/score
-> STRONG / COMPARABLE_HIGH / COMPARABLE_MARGINAL / WEAK_VALID / BLOCKED
```

Does "incremental" change from ADD 1200->1300, 1300->1400, 1600->1700 because next-lot economics changed?

`PARTIAL`

The same-date score, best NEW score, PM state, current quantity, one-lot weight, and cap/headroom refresh. But the accepted repeated ADD rows generally retain the same categorical `POSITIVE/PASS`, `opportunity_cost PASS`, and `COMPARABLE_MARGINAL` classification. The system recomputes the boundary, but the output is not a high-resolution marginal value curve.

## Opportunity Cost Decomposition

OPPORTUNITY_COST_SEMANTIC_TYPE = `MIXED`

It contains:

- ADD candidate score;
- best same-date NEW_BUY score;
- comparison result such as `PASS` or `NEW_BUY_SUPERIOR`;
- source authority `portfolio_construction_same_day_score_competition`.

It is not:

- a numeric economic delta against Cash;
- a full ADD-vs-ADD frontier value;
- a residual optionality value;
- a calibrated expected-return value.

Resolution survives as numeric score values, but the consumer largely uses categorical comparison state and opportunity class.

## G115 Classification Audit

G115_IS_PRIMARY_INFORMATION_BOTTLENECK = `PARTIAL`

G115 is not the first bottleneck: compression is already visible at opportunity-quality / incremental-value transformation. But G115 and PC final classification are major final bottlenecks because they intentionally convert rows into one-increment, shoulder, Cash, re-entry, budget, lot, and cap outcomes.

COMPARABLE_MARGINAL_DOMINANT_CAUSE =

`BUY_NEW_REDUCED_OR_CAUTION_CONTINUATION_BUCKETING_PLUS_ADD_REDUCED_BUT_VALID_BUCKETING`

Reason frequency among `COMPARABLE_MARGINAL` rows:

| Reason | All regimes | BULL |
| --- | ---: | ---: |
| `opportunity_quality_buy_new_mixed_or_reduced_but_valid` | 2,214 | 920 |
| `REENTRY_BLOCK` | 844 | 425 |
| `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` | 511 | 219 |
| `COMPETITOR_SELECTED` | 330 | 124 |
| `RISK_PACING_CAUTION_STRONG_COMPETITOR_ALLOWED` | 259 | 93 |
| `VALID_SAFETY_RESERVE` | 213 | 74 |
| `LOT_RESIDUAL` | 276 | 63 |
| `opportunity_quality_add_reduced_but_valid` | 27 | 13 |
| `ADD_SELECTED` | 21 | 10 |

This is mostly designed categorical bucket compression, not evidence disappearance.

## Contrasting Examples

Same-date examples where differentiation is preserved or lost:

| Type | Date | Competitor A | Competitor B | Differentiation fate |
| --- | --- | --- | --- | --- |
| A upstream different -> same final | 2022-11-21 | 78860 NEW rank 9 score 0.0111 | 79010 NEW rank 23 score -0.5009 | Both `COMPARABLE_MARGINAL + incremental_budget_zero_allocation`; lost by PC/final budget bucket. |
| A upstream different -> same final | 2022-11-21 | 78860 NEW rank 9 score 0.0111 | 92640 NEW rank 26 score -0.5204 | Same `COMPARABLE_MARGINAL + incremental_budget_zero_allocation`. |
| A upstream different -> same final | 2023-01-23 | 59860 NEW rank 11 score -0.3702 | 72730 NEW rank 33 score -0.6009 | Both `COMPARABLE_MARGINAL + reentry_opportunity_not_requalified`. |
| A upstream different -> same final | 2023-01-23 | 59860 NEW rank 11 score -0.3702 | 91070 NEW rank 34 score -0.6116 | Both re-entry not requalified. |
| B similar upstream -> different final | 2022-11-29 | 76920 NEW `COMPARABLE_HIGH` | 76470 ADD `COMPARABLE_MARGINAL` | Both selected, but different allocation rank and type; differentiation survives enough for multi-allocation. |
| C ADD vs NEW | 2022-11-29 | 76470 ADD score 0.3190, opp-cost PASS | 76920 NEW selected | ADD and NEW coexist; score comparison exists, but final common value unit remains partial. |
| C ADD vs NEW | 2022-12-01 | 76470 ADD score 0.3784, best NEW 0.2311 | 45910 NEW selected | ADD passes NEW comparison but both become PC-selected security increments. |
| D NEW vs NEW | 2022-10-27 | 76920 NEW rank 6 score -0.0078 | 60480 NEW rank 24 score -0.4868 | Both selected despite score gap; multi-allocation preserves broad participation, not strict rank-only ordering. |
| E ADD vs ADD | 2022-10-12 | 94320 ADD score 0.4255 | 94340 ADD score 0.2858 | ADD order followed score; ADD-vs-ADD resolution exists but is sparse. |
| F Security vs Cash | 2022-11-30 | 76470 ADD selected | Cash remains preferred/co-allocated | `CASH_PREFERRED_PARTICIPATION_VALID` permits shoulder participation; not ADD-beats-Cash proof. |

These examples support multi-causal resolution loss rather than an isolated dropped field.

## 76470 Deep Trace

| Date | Regime | Final | Score | Rank | IIV | Opportunity Cost | Accepted Weight | Pre -> Post Target Weight |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | --- |
| 2022-11-28 | BULL | ADD_TARGET_WEIGHT_UNCHANGED | 0.30267929 | 2 | UNKNOWN / FAIL_CLOSED | PASS vs 0.18902895 | 0.000000 | 0.029918 -> 0.029918 |
| 2022-11-29 | BULL | SELECTED | 0.31899310 | 3 | POSITIVE / PASS | PASS vs 0.16297291 | 0.002494 | 0.029929 -> 0.032423 |
| 2022-11-30 | BULL | SELECTED | 0.34505777 | 2 | POSITIVE / PASS | PASS vs 0.21260248 | 0.002491 | 0.032380 -> 0.034871 |
| 2022-12-01 | BULL | SELECTED | 0.37835760 | 2 | POSITIVE / PASS | PASS vs 0.23108714 | 0.002499 | 0.034980 -> 0.037479 |
| 2022-12-02 | BULL | SELECTED | 0.40651062 | 2 | POSITIVE / PASS | PASS vs 0.25983442 | 0.002409 | 0.035023 -> 0.037432 |
| 2022-12-06 | RANGE | SELECTED | 0.42251035 | 2 | POSITIVE / PASS | PASS vs 0.27563508 | 0.002524 | 0.037861 -> 0.040385 |
| 2022-12-08 | RANGE | SELECTED | 0.41972718 | 2 | POSITIVE / PASS | PASS vs 0.25153989 | 0.002500 | 0.040001 -> 0.042501 |

76470_NEXT_LOT_RESOLUTION = `MODERATE`

76470_REPEATED_ADD_USES_DISTINCT_MARGINAL_VALUE = `PARTIAL`

Relative advantage changes numerically by score and best NEW score, but categorical marginal value remains `POSITIVE/PASS` and `COMPARABLE_MARGINAL`. Distinct next-lot economics are not expressed beyond refreshed quantity/headroom and one-lot staged authorization.

## 94320 Deep Trace

94320 alternates between blocked/unchanged and selected ADD:

| Date | Regime | Final | Score | Rank | IIV | Opportunity Cost | Accepted Weight |
| --- | --- | --- | ---: | ---: | --- | --- | ---: |
| 2022-10-12 | BEAR | SELECTED | 0.42547970 | 1 | POSITIVE / PASS | PASS vs 0.15602367 | 0.015146 |
| 2022-10-21 | RANGE | g43_binding_blocked | 0.40629465 | 1 | POSITIVE / PASS | PASS vs 0.08364030 | 0.000000 |
| 2022-10-28 | RECOVERY | SELECTED | 0.39706695 | 1 | POSITIVE / PASS | PASS vs 0.09652459 | 0.015539 |
| 2022-11-01 | BULL | SELECTED | 0.38607446 | 1 | POSITIVE / PASS | PASS vs 0.13592963 | 0.015397 |
| 2022-11-04 | CORRECTION | SELECTED | 0.40385899 | 1 | POSITIVE / PASS | PASS vs 0.18448267 | 0.014931 |
| 2022-11-09 | BULL | SELECTED | 0.39720057 | 1 | POSITIVE / PASS | PASS vs 0.25034036 | 0.014398 |
| 2023-01-24 | BULL | ADD_TARGET_WEIGHT_UNCHANGED | 0.16370874 | 2 | UNKNOWN / FAIL_CLOSED | NEW_BUY_SUPERIOR vs 0.25197074 | 0.000000 |
| 2023-01-31 | BULL | SELECTED | 0.28370353 | 1 | POSITIVE / PASS | PASS vs 0.28342238 | 0.012732 |
| 2023-02-24 | BULL | SELECTED | 0.18215026 | 1 | POSITIVE / PASS | PASS vs 0.02524522 | 0.013017 |

94320_CAPITAL_VALUE_RESOLUTION = `MODERATE`

The system detects some meaningful changes through IIV `UNKNOWN/FAIL_CLOSED`, `NEW_BUY_SUPERIOR`, and selected vs blocked states. But selected ADD rows remain coarse `COMPARABLE_MARGINAL` next-lot authorizations, not high-resolution marginal value estimates.

## Regime Comparison

| Regime | Competitors | Stage 1 distinct | Stage 2 distinct | Stage 4 distinct | Stage 5 distinct | Largest final group |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| BULL | 1,034 | 1,034 | 5 | 78 | 22 | `reentry_opportunity_not_requalified / 320 / 30.95%` |
| BEAR | 649 | 649 | 4 | 79 | 13 | `reentry_opportunity_not_requalified / 139 / 21.42%` |
| RANGE | 419 | 419 | 5 | 72 | 18 | `incremental_budget_zero_allocation / 100 / 23.87%` |
| RECOVERY | 275 | 275 | 5 | 65 | 17 | `reentry_opportunity_not_requalified / 70 / 25.45%` |

RESOLUTION_LOSS_MECHANISM_IS_REGIME_SPECIFIC = `NO`

BULL_AMPLIFIES_GENERAL_RESOLUTION_LIMIT = `YES`

The same compression mechanism appears in BEAR, RANGE, and RECOVERY. BULL amplifies it because more opportunities reach the frontier and more valid-but-marginal rows coexist.

## Hypothesis Tests

H1: Candidate/PM upstream evidence is already too coarse.

`PARTIAL`

Upstream evidence has distinct score/rank/action signatures, but the semantic evidence before PC does not already contain a calibrated common marginal capital value.

H2: Upstream evidence is sufficiently differentiated, but incremental value / opportunity cost loses information.

`PARTIAL`

Opportunity cost preserves numeric score resolution, but incremental value and opportunity quality compress into categorical buckets.

H3: Resolution survives until G115, then final categorical classification collapses it.

`PARTIAL`

Some resolution survives to PC, but compression begins before G115. G115/PC final classification adds another coarse categorical layer.

H4: ADD and NEW use semantically different value scales, forcing coarse comparison.

`SUPPORTED`

ADD = continuation / campaign increment / no-loss / expected-edge semantics. NEW = entry attractiveness / candidate rank / BUY Quality. Cash = optionality / residual. They share some score evidence but not a common marginal-value unit.

H5: Cash shoulder semantics are the dominant source of compression.

`PARTIAL`

Cash shoulder semantics explain selected comparable-marginal security participation, especially ADD rows. But many collapsed rows are driven by opportunity-quality class, re-entry, lot, budget, or cap states. Cash shoulder is important but not the only cause.

## Existing Evidence Recovery Potential

EXISTING_EVIDENCE_CONTAINS_UNUSED_RESOLUTION = `YES`

Potentially recoverable PIT evidence already present upstream:

- `runtime_opportunity_score`
- `opportunity_buy_rank`
- `quality_score`
- `quality_band`
- `quality_action`
- `entry_admission_state`
- `entry_admission_action`
- `selection_quality_tier`
- `relative_priority_source_fields`
- `within_class_priority_sort_key`
- ADD candidate score
- ADD best NEW score
- ADD current / post target weight
- one-lot weight
- cap/headroom
- expected-edge state
- no-loss averaging state
- campaign continuation state
- Cash / participation-deferral state

This does not mean these fields should be mechanically tuned or turned into a performance-fitted score. It means the artifacts retain more ordering evidence than the current coarse capital-value classes express.

## Defect Vs Limitation

Final root-cause classification:

- `EXISTING_EVIDENCE_RESOLUTION_LOSS`
- `CROSS_TYPE_SEMANTIC_LIMITATION`
- `INTENTIONAL_COARSE_CONTRACT`

Not proven:

- `ARCHITECTURE_CONTRACT_DEFECT`
- `IMPLEMENTATION_CONSUMER_DEFECT`
- `OBSERVABILITY_GAP`
- `INSUFFICIENT_EVIDENCE`

Mandatory repair rule result:

MANDATORY_REPAIR_FOUND = `NO`

Reason:

The accepted Phase31 SoT intentionally defines coarse opportunity-quality classes, Cash shoulder participation, and staged one-increment ADD authority. The implementation is not proven to discard a differentiation field that the current authoritative contract requires it to preserve as a high-resolution common marginal value.

## Next-Phase Design Implication

HIGH_RESOLUTION_MARGINAL_VALUE_NEXT_PHASE_JUSTIFIED = `YES`

PORTFOLIO_ROTATION_DEPENDS_ON_HIGH_RESOLUTION_VALUE = `PARTIAL`

Evidence supports a future design task for:

```text
HIGH_RESOLUTION_MARGINAL_CAPITAL_VALUE
```

The candidate boundary is:

```text
PRODUCER = Portfolio Construction / capital value evidence bridge
CONSUMERS = G115 ADD authority, canonical multi-allocation deployment set, PS-bound final PC quantity authority
MISSING_SEMANTIC = common ordinal or numeric next-executable-lot marginal value across NEW_BUY / ADD / Cash
REQUIRED_INVARIANT = use existing PIT evidence first; no future/PnL/MFE/MAE tuning; preserve Cash as first-class; preserve G131 shoulder participation unless superseded by explicit design
```

Portfolio-wide capital rotation likely depends on higher-resolution value, because rotating capital out of existing holdings into new or ADD opportunities requires comparing existing HOLD capital, ADD increments, NEW entries, and Cash on a more common marginal basis than current coarse classes provide. G134 does not design or implement that rotation.

## Required Final Judgments

END_TO_END_VALUE_LINEAGE_RECONSTRUCTED = `YES`

PRIMARY_RESOLUTION_LOSS_STAGE = `MULTIPLE`

NEW_UPSTREAM_DIFFERENTIATION_SUFFICIENT = `PARTIAL`

ADD_UPSTREAM_DIFFERENTIATION_SUFFICIENT = `PARTIAL`

NEW_ADD_VALUE_SEMANTICS_COMMON_UNIT = `PARTIAL`

INCREMENTAL_VALUE_COMPRESSION_SOURCE = `MULTIPLE`

OPPORTUNITY_COST_SEMANTIC_TYPE = `MIXED`

G115_IS_PRIMARY_INFORMATION_BOTTLENECK = `PARTIAL`

EXISTING_EVIDENCE_CONTAINS_UNUSED_RESOLUTION = `YES`

RESOLUTION_LOSS_MECHANISM_IS_REGIME_SPECIFIC = `NO`

BULL_AMPLIFIES_GENERAL_RESOLUTION_LIMIT = `YES`

MANDATORY_REPAIR_FOUND = `NO`

FUTURE_INFORMATION_USED_FOR_ROOT_CAUSE_JUDGMENT = `NO`

## Required Flags

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

THRESHOLD_CHANGED = `NO`

WEIGHT_CHANGED = `NO`

MODEL_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

PHASE_ADVANCED = `NO`
