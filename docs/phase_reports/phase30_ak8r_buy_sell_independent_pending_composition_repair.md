# Phase30-AK8R — BUY / SELL Independent Pending Composition Focused Repair

## Scope

Task ID: `Phase30-AK8R`

Type: `FOCUSED_PRODUCTION_COMMON_RUNTIME_REPAIR`

Authorized implementation scope:

```text
Production-common valid BUY pending preservation / BUY+SELL pending composition across Sell Planning
```

No Strategy, Candidate, PM policy, PC ranking, PS sizing semantics, AK7R
promotion thresholds, Strategy/Safety caps, same-day proceeds contract, or
fresh/long Historical run was changed.

## Primary Judgment

```text
BUY_SELL_INDEPENDENT_PENDING_COMPOSITION_REPAIRED = YES
VALID_BUY_PENDING_PRESERVED_ACROSS_SELL_PLANNING = YES
VALID_BUY_PENDING_SILENT_OVERWRITE_PROHIBITED = YES
MIXED_BUY_SELL_PENDING_ACTION_EFFECTIVE = YES
SELL_EXISTENCE_ALONE_CANNOT_DROP_VALID_BUY = YES
MANDATORY_SELL_INDEPENDENCE_PRESERVED = YES
BUY_PENDING_COMPOSITION_EVIDENCE_COMPLETE = YES
```

Phase30-AK8R repairs the AK8 confirmed defect:

```text
SELL_PLANNING_PENDING_COMPOSITION_OVERWRITE
```

Sell Planning now preserves valid pre-sell BUY pending by composing it with
new same-day SELL pending into one canonical mixed Pending authority. A valid
BUY can no longer disappear merely because Sell Planning writes later in the
day. SELL / REDUCE / EXIT authority remains independent and executable.

## Repair Summary

`src/ai_fund_lab_v2/runtime_v2/pending/composition.py` now emits complete
composition evidence for successful `COMPOSITE_PENDING_PLAN` and
`BUY_ITEM_SCOPED_REVIEW_SELL_CONTINUATION_COMPOSITE_PENDING_PLAN` paths:

- pre-sell BUY pending count
- preservable BUY count
- SELL count
- composed BUY count
- composed SELL count
- dropped BUY count
- final canonical pending count
- pending source lineage

`src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py` now writes
`pending_composition_evidence.json` under the Sell Planning artifact directory
whenever Sell Planning evaluates composition. The evidence schema is:

```text
phase30_ak8r_buy_sell_pending_composition_evidence.v1
```

The evidence carries explicit invariants:

```text
valid_buy_pending_silent_overwrite_prohibited = true
sell_existence_alone_cannot_drop_valid_buy = true
```

## BUY / SELL Composition

The canonical production-common path is reused:

```text
existing BUY pending
+ new SELL pending
-> canonical mixed BUY/SELL pending
-> Submit consumes the mixed canonical pending
```

No duplicate BUY authority, re-ranking, re-sizing, or fresh Strategy decision
is introduced. Existing BUY pending remains subject to its own cash, buying
power, Safety, pending validity, and submit feasibility authority.

## Sentinels

New focused sentinel:

```text
test_phase30_ak8r_multiple_buy_multiple_sell_composes_and_reaches_submit
```

Coverage:

- multiple BUY plus multiple SELL in one business date
- valid BUY items are preserved
- SELL items are composed
- dropped BUY count is zero
- final canonical pending contains both BUY and SELL items
- Submit receives and passes the mixed canonical pending
- evidence records BUY/SELL counts and source lineage

The sentinel materializes:

```text
BUY 43550 quantity 100
BUY 76920 quantity 300
SELL 6522 quantity 100
SELL 76010 quantity 100
```

and confirms all four items reach Submit as one canonical pending authority.

## Preservation

```text
AK3R2B_CASH_FEASIBLE_BUY_BATCH_PRESERVED = YES
AK7R_CAPITAL_CONVERSION_PRESERVED = YES
SAME_DAY_SELL_PROCEEDS_CONTRACT_PRESERVED = YES
NO_FORCED_BUY = YES
SELL_SAFETY_WEAKENED = NO
```

AK3R2B reserved-notional-aware BUY batch construction is preserved. AK7R
capital conversion and lot-aware quantity behavior are preserved. Same-day
SELL proceeds are not injected into pre-SELL BUY cash authority.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
```

The repair is contract-level Pending composition logic. It does not use
historical outcomes to tune parameters or alter strategy behavior.

## Tests

```text
compileall runtime pending/planning = PASS
tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py = 25 passed
AK3R2B cash batch + submit feasibility + submit guard = 38 passed
submit guard / mandatory sell / no-action execution regressions = 28 passed
Phase30-S + Phase30-W strategy handoff regressions = 26 passed
pending lifecycle + sell planning integration regressions = 52 passed, 60 warnings
portfolio construction + position sizing regressions = 197 passed
runtime planning + prior exit materialization regressions = 63 passed
```

The 60 warnings are pre-existing `DeprecationWarning` messages from
`position_management/producer.py` about empty ndarray truth-value behavior.

## Historical

```text
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Deliverables

```text
docs/phase_reports/phase30_ak8r_buy_sell_independent_pending_composition_repair.md
reports/phase_reports/phase30_ak8r_buy_sell_independent_pending_composition_repair.json
docs/01_requirements/phase_roadmap.md
```

## Recommended Next Task

```text
Phase30-AK9 — Fresh Validation Readiness / Consolidated Regression Audit
```
