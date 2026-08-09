# Phase28-D17: Fresh 100BD Canonical BUY_ADD Acceptance and Runtime Conformance Audit

## Primary Judgment

```text
PHASE28_D17_PHASE28_C_RUNTIME_CONVERSION_GAP_REMAINS
```

Phase28-D17 did not execute implementation, resume, fresh run, long historical, or runtime mutation. The audit used only the existing run root:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T053322547871Z
```

## Run Completion

- Run state: `COMPLETED`
- Runtime status: `COMPLETED`
- Completed business days: `100/100`
- Halt status: `NOT_HALTED`
- Runtime judgment: `PASS` / final `PASS`
- Close result: `REVIEW_REQUIRED`

## Close REVIEW_REQUIRED

Direct reason:

```text
strategy_shadow_review_required_non_blocking
```

The close REVIEW_REQUIRED is non-blocking for runtime execution. `block_rule` is `NO_BLOCKING_CLOSE_RULE_TRIGGERED`; runtime execution, accounting, and trading judgments are PASS. The two audit findings are:

1. `strategy_shadow_review_required_non_blocking` on `59` dates.
2. `buy_fill_lineage_validation` reports `112` existing buy fills with missing lineage fields `['pending_item_id', 'order_plan_item_id', 'quality_decision_id', 'position_campaign_id']` and status `REVIEW_REQUIRED_PRE_REPAIR_ARTIFACT`.

## Canonical ADD Runtime Chain

| Stage | Count | Judgment |
|---|---:|---|
| PM ADD decisions | 51 | Present |
| Strategy PM ADD actions | 0 | Missing |
| Portfolio target_weight increase | 272 | Present, but mostly opportunity/new candidate path |
| Positive quantity_delta | 183 | Present, but `pm_action=NEW` path |
| BUY_ADD runtime plans | 0 | Missing |
| BUY_ADD pending | 0 | Missing |
| BUY_ADD approval | 0 | Missing |
| BUY_ADD submit | 0 | Missing |
| BUY_ADD fills | 0 | Missing |

First stop:

```text
Strategy Position Management action materialization
```

Evidence: PM decisions contain `51` `ADD` rows, but Strategy Position Management action counts are `{'UNRESOLVED': 198}`. Runtime Planning intent counts are `{'BUY_NEW': 183, 'NO_ORDER': 89, 'SELL_EXIT': 198}`. There is no `BUY_ADD` plan, pending item, submit item, or fill.

## Campaign Integrity

- Campaign count: `112`
- Duplicate campaign id count: `0`
- Campaigns with ADD event: `0`
- Re-entry count: `93`

Because BUY_ADD count is zero, ADD campaign integrity is not confirmed for this run.

## Performance

Performance is positive at run level, but not adoptable as BUY_ADD performance.

| Metric | Value | Authority |
|---|---:|---|
| Initial equity | 1000000 | CANONICAL_RUNTIME_AUTHORITY |
| Final equity | 1058200 | CANONICAL_RUNTIME_AUTHORITY |
| Total return | 58200 | DERIVED_DIAGNOSTIC |
| Return rate | 5.8200% | DERIVED_DIAGNOSTIC |
| First half return | 91420.0 | DERIVED_DIAGNOSTIC |
| Second half return | -33220.0 | DERIVED_DIAGNOSTIC |
| Max drawdown | 0.164358 | DERIVED_DIAGNOSTIC |
| Profit factor | 1.115969 | DERIVED_DIAGNOSTIC |
| Avg winner | 10182.909091 | DERIVED_DIAGNOSTIC |
| Avg loser | -11405.909091 | DERIVED_DIAGNOSTIC |
| Avg cash ratio | 0.733801 | DERIVED_DIAGNOSTIC |
| Avg invested ratio | 0.266199 | DERIVED_DIAGNOSTIC |
| Turnover | 28.528213 | DERIVED_DIAGNOSTIC |

BUY_ADD PnL attribution status:

```text
NOT_DERIVABLE_FOR_BUY_ADD
```

Reason: no BUY_ADD fill exists. The 112 BUY executions are `source_decision_type=BUY`, not canonical `BUY_ADD`.

## Phase28-C Acceptance

```text
NOT_ACCEPTED_FOR_THIS_RUN_BUY_ADD_RUNTIME_CHAIN_ZERO
```

Phase28-C is not accepted for this run because the canonical BUY_ADD runtime chain has zero plans, pending items, submits, and fills. The Phase28-C ADD bridge was therefore not reached by PM ADD decisions in this evidence root.

## Performance Adoption

```text
NOT_ADOPTED_FOR_BUY_ADD_PERFORMANCE_BECAUSE_BUY_ADD_COUNT_ZERO
```

The run-level +5.82% result is real for the runtime run, but it cannot be adopted as evidence that canonical BUY_ADD improved performance.

## Open Gaps

1. Runtime/Strategy: PM ADD does not materialize as Strategy PM ADD in this run.
2. Runtime Planning: zero BUY_ADD plans/pending/submits/fills.
3. Observability: buy fill artifacts still miss pending/order-plan/quality lineage in existing run evidence.
4. Close Review: strategy shadow non-blocking REVIEW_REQUIRED remains.

## Next Phase

```text
Phase28-D18: PM ADD Strategy PM propagation runtime-run mismatch root cause diagnosis
```

D18 should first confirm why the D12 repair is not reflected in this fresh run's Strategy PM artifacts, then identify the exact producer/runtime path before any repair.

## Evidence

- `reports/phase28_d17_fresh_100bd_canonical_buy_add_acceptance_and_runtime_conformance_audit/`
- `reports/phase_reports/phase28_d17_fresh_100bd_canonical_buy_add_acceptance_and_runtime_conformance_audit.json`

## Mutation Statement

Implementation changed: `false`
Config changed: `false`
Schema changed: `false`
Threshold changed: `false`
Resume executed: `false`
Fresh run executed by D17: `false`
Long historical executed: `false`
Runtime mutated by D17: `false`
