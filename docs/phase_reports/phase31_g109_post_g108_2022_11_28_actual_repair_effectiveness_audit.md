# Phase31-G109 — Post-G108 2022-11-28 Actual Campaign Identity Repair Effectiveness Audit

## Primary Decision

G109_G108_ACTUAL_PATH_DEFECT_CONFIRMED_READY_FOR_REPAIR

G109 is READ-ONLY. No code, config, threshold, weight, Strategy semantics, run state, fresh-run, resume, replay, or long Historical execution was performed.

## Target

TARGET_RUN = runtime-test-historical-extended-smoke-20260825T072702567342Z

TARGET_BOUNDARY = 2022-11-28:morning

OBSERVED_STATUS = HALT

OBSERVED_EXIT_CODE = 20

COMPLETED_THROUGH = 2022-11-25

## Root Cause Comparison

POST_G108_HALT_COMPONENT = Position Management / Strategy Intelligence lifecycle campaign identity, surfaced through Runtime Strategy Planning Authority

POST_G108_HALT_REASON = 93180 PM HOLD became UNRESOLVED because Strategy Intelligence lifecycle had `campaign_identity_authority_status = MISSING` and Position Management emitted `structured_hold_worthiness_review_required` / `canonical_campaign_identity_missing`

POST_G108_FIRST_FAILING_AUTHORITY = Strategy Intelligence lifecycle campaign identity consumed by Position Management structured HOLD-worthiness

POST_G108_FAILING_SYMBOL = 93180

SAME_ROOT_CAUSE_AS_G107 = YES

The external boundary is the same as G107 and the actual causal chain is also the same:

```text
2022-11-25 93180 BUY fill 700
-> 2022-11-28 current position HELD quantity 700
-> canonical position_campaigns contains matching OPEN campaign
-> Strategy Intelligence lifecycle_context materializes campaign identity as MISSING
-> Position Management HOLD becomes UNRESOLVED
-> Portfolio Construction / Position Sizing / Runtime Planning become REVIEW_REQUIRED
-> Strategy Planning Authority returns REVIEW_REQUIRED
-> morning exit_code 20
```

## 93180 Actual Trace

### Current Position

current_position_state = HELD

current_quantity = 700

average_price = 4.0

market_value = 2,800

quantity_basis = ADJUSTED

valuation_price_basis = ADJUSTED

source = `.runtime/persistent_ledger/state.json` via Strategy Intelligence current source evidence

### Canonical Campaign

POST_G108_93180_CANONICAL_OPEN_CAMPAIGN_EXISTS = YES

CANONICAL_CAMPAIGN_ARTIFACT_PATH = `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-11-28/positions/position_campaigns.json`

Matching 93180 campaigns:

| campaign_id | status | opened_date | current_quantity |
|---|---:|---:|---:|
| pc-03ca91a459c078c1-93180-0001 | CLOSED | 2022-10-25 | 0 |
| pc-03ca91a459c078c1-93180-0002 | OPEN | 2022-11-25 | 700 |

matching OPEN campaign count = 1

required identity fields = PRESENT

symbol match = YES

current quantity reconciliation = PASS

campaign quantity reconciliation = PASS

campaign status = OPEN

### Strategy Intelligence

STRATEGY_INTELLIGENCE_CONSUMED_CAMPAIGN_ARTIFACT_PATH = `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-11-28/positions/position_campaigns.json`

SAME_ARTIFACT = YES

Strategy Intelligence source evidence for `position_campaigns`:

- status = PASS
- sha256 = `5b58cd24084d2a52435e4944dd961ebdf3f68e44c9b9f236b87818906ecf1093`

Actual 93180 lifecycle:

- position_campaign_id = null
- campaign_opened_date = null
- campaign_status = null
- campaign_identity_authority_status = MISSING
- missing_campaign_authority_fields = `position_campaign_id`, `campaign_opened_date`, `campaign_status`
- current_position_authority_status = PARTIAL
- missing_current_authority_fields = []

POST_G108_93180_CAMPAIGN_IDENTITY_STATUS = MISSING

### Position Management

POST_G108_93180_PM_ACTION = UNRESOLVED

PM evidence:

- action = UNRESOLVED
- position_campaign_id = empty
- strategy_intelligence_campaign_id = empty
- structured_hold_worthiness_evidence.status = REVIEW_REQUIRED
- structured_hold_worthiness_evidence.campaign_identity_authority_status = MISSING
- canonical_campaign_identity_missing present = YES
- action becomes UNRESOLVED = YES

## G108 Code Activity

G108_CHANGED_FUNCTION_CALLED_IN_ACTUAL_RUN = NO

G108_CHANGED_BRANCH_REACHED_FOR_93180 = NO

Reason: using the actual Post-G108 campaign artifact and actual 93180 current-position facts, the current G108 code path maps the OPEN campaign and recomputes:

```text
position_campaign_id = pc-03ca91a459c078c1-93180-0002
campaign_opened_date = 2022-11-25
campaign_status = OPEN
campaign_identity_authority_status = COMPLETE
missing_campaign_authority_fields = []
```

The actual run artifact instead contains `campaign_identity_authority_status = MISSING`. Therefore the G108 completion predicates do not fail on the actual input; the repaired branch was not active in the artifact-producing execution, or an unrepaired production artifact generation path was used.

G108_ACTUAL_PREDICATE_FAILURE = NONE

The target run reports:

- source_commit = `a54eeda6c8cb14fd1dddeaad0a61436fb404fdf5`
- source_dirty = true
- command used `PYTHONPATH=src`

Because `source_dirty = true`, the commit alone cannot prove whether the G108 uncommitted repair was present at execution time. The artifact-level recomputation proves the result is inconsistent with the current repaired G108 path.

## Fixture vs Actual Artifact Comparison

G108_FIXTURE_MATCHES_ACTUAL_SCHEMA = PARTIAL

The G108 unit fixture matches the essential canonical campaign schema fields:

- `schema_version = position_campaign_observability.v1`
- `position_campaigns[]`
- `symbol`
- `position_campaign_id`
- `campaign_status`
- `opened_business_date`
- `current_quantity`
- prior CLOSED campaign plus current OPEN campaign

Fixture/actual differences:

- campaign id prefix differs by run-specific deterministic namespace.
- fixture uses synthetic current summary; actual uses `.runtime/persistent_ledger/state.json`.
- fixture exercises `build_strategy_intelligence_payload` directly; actual uses `runtime_test.py -> run_daily_operation -> shadow_runtime.run_strategy_shadow -> produce_strategy_intelligence_artifact`.
- fixture does not prove the actual production orchestration code was running with the repaired dirty workspace.

This is an actual-path coverage gap, not a core field-name mismatch.

## Canonical Artifact Source and Timing

CAMPAIGN_PERSISTED_ON_2022_11_25 = YES

Evidence:

- 2022-11-25 execution fill exists for 93180 BUY 700 with `position_campaign_id = pc-03ca91a459c078c1-93180-0002`.
- 2022-11-25 pre-action `positions/position_campaigns.json` has only the prior CLOSED campaign, which is expected because the new BUY fill occurs after pre-action strategy evidence.

CAMPAIGN_PRESENT_AT_2022_11_28_MORNING_LOAD = YES

Evidence:

- 2022-11-28 `positions/position_campaigns.json` contains OPEN `pc-03ca91a459c078c1-93180-0002`.

CAMPAIGN_PRESENT_IN_STRATEGY_INTELLIGENCE_INPUT = YES

Evidence:

- 2022-11-28 Strategy Intelligence `source_evidence.position_campaigns.status = PASS`.
- Strategy Intelligence consumed path equals canonical campaign artifact path.

Timing gap = NO

Source/path mismatch = NO

## Downstream Causality

First failing authority:

```text
Strategy Intelligence lifecycle campaign identity for 93180
```

Downstream propagation:

```text
SI campaign_identity_authority_status = MISSING
-> PM structured_hold_worthiness_evidence.status = REVIEW_REQUIRED
-> PM 93180 action = UNRESOLVED
-> PC 93180 membership_intent = UNRESOLVED, reason pm_action:UNRESOLVED
-> Position Sizing status = REVIEW_REQUIRED from position_management_review_required / portfolio_construction_review_required
-> Runtime Planning status = REVIEW_REQUIRED
-> Strategy Planning Authority status = REVIEW_REQUIRED
-> morning exit_code = 20
```

SECOND_INDEPENDENT_BLOCKER_PRESENT = NO

The Strategy Planning Authority also lists 22 `strategy_plan_quantity_unresolved:*` rows. However, Position Sizing reports the common reason `upstream_review_required`, and top-level reason codes include `position_management_review_required:REVIEW_REQUIRED` and `portfolio_construction_review_required:REVIEW_REQUIRED`. Position Management has only one actual UNRESOLVED position: 93180. The quantity unresolved rows are downstream fan-out from the upstream PM/PC REVIEW_REQUIRED state, not an independently proven second same-day root cause.

## Defect Class

POST_G108_DEFECT_CLASS = A

A = G108 code not active on actual production path.

More precisely: the actual production path produced an artifact inconsistent with the repaired G108 function behavior on the same input. The next repair must target the actual runtime_test / shadow_runtime production path and prove the G108 branch is active in that path, not only in unit fixtures.

## Required Final Judgments

SAME_ROOT_CAUSE_AS_G107 = YES

POST_G108_93180_CANONICAL_OPEN_CAMPAIGN_EXISTS = YES

POST_G108_93180_CAMPAIGN_IDENTITY_STATUS = MISSING

POST_G108_93180_PM_ACTION = UNRESOLVED

G108_CHANGED_FUNCTION_CALLED_IN_ACTUAL_RUN = NO

G108_CHANGED_BRANCH_REACHED_FOR_93180 = NO

G108_ACTUAL_PREDICATE_FAILURE = NONE

G108_FIXTURE_MATCHES_ACTUAL_SCHEMA = PARTIAL

CAMPAIGN_PERSISTED_ON_2022_11_25 = YES

CAMPAIGN_PRESENT_AT_2022_11_28_MORNING_LOAD = YES

CAMPAIGN_PRESENT_IN_STRATEGY_INTELLIGENCE_INPUT = YES

POST_G108_DEFECT_CLASS = A

SECOND_INDEPENDENT_BLOCKER_PRESENT = NO

G108_ACTUAL_REPAIR_EFFECTIVE = NO

REPAIR_REQUIRED = YES

ACTUAL_PATH_SHORT_GATE_DEFINED = YES

## Required G110 Acceptance Gate

The next repair must not be accepted by unit/fixture evidence alone. It must run a short actual-path gate that exercises the same production code path as `runtime_test.py`:

```text
2022-11-25 accepted BUY fill 93180:700
-> persisted canonical campaign
-> 2022-11-28 morning actual state load
-> Strategy Intelligence campaign identity COMPLETE
-> PM not REVIEW_REQUIRED from canonical_campaign_identity_missing
-> PC
-> PS
-> Runtime Planning
-> Strategy Planning Authority
-> morning command exits successfully beyond the prior 2022-11-28:morning failure boundary
```

The gate must explicitly assert:

- actual production Strategy Intelligence artifact for 2022-11-28 / 93180 has campaign identity COMPLETE.
- PM 93180 action is not UNRESOLVED due to `canonical_campaign_identity_missing`.
- Strategy Planning Authority has no `strategy_plan_order_side_unresolved` for 93180.
- no second independent 2022-11-28 blocker is present after the 93180 cause is cleared.

## Constraints Confirmation

CODE_CHANGED = NO

CONFIG_CHANGED = NO

FRESH_RUN_EXECUTED_BY_CODEX = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED_BY_CODEX = NO

LONG_HISTORICAL_EXECUTED_BY_CODEX = NO

FUTURE_PNL_OR_OUTCOME_USED = NO

GIT_DIFF_CHECK = PASS
