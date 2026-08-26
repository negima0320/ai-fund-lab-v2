# Phase31-G107 - 2022-11-28 Morning HALT Root Cause Audit

## PRIMARY_JUDGMENT

`G107_MORNING_HALT_DEFECT_CONFIRMED_READY_FOR_REPAIR`

READ-ONLY audit of:

```text
runtime-test-historical-extended-smoke-20260825T045610960730Z
2022-11-28:morning
```

No code/config/run-state mutation, fresh-run, resume, replay, or long Historical execution was performed.

The HALT is not caused by Data Readiness, temporal/PIT authority, Historical Safety, corporate-action quarantine, or stale Pending carry-over. The first failing authority is the 2022-11-28 Position Management / Strategy Intelligence lifecycle identity check for an actual held 93180 position created by a valid 2022-11-25 BUY fill.

Root cause:

```text
2022-11-25 93180 BUY 700 filled
-> 2022-11-28 Runtime current position has 93180 quantity 700
-> positions/position_campaigns.json contains OPEN campaign pc-93bafcd34c4af64c-93180-0002
-> Strategy Intelligence lifecycle_context sees campaign_identity_authority_status = MISSING
-> Position Management HOLD is converted to UNRESOLVED
-> PM artifact becomes REVIEW_REQUIRED / DRAFT
-> PC and PS inherit SOURCE_REVIEW_REQUIRED
-> Runtime Planning emits quantity unresolved rows
-> Strategy Planning Authority has no Pending items but has reason_codes
-> phase23_i_strategy_planning_authority_pipeline returns REVIEW_REQUIRED
-> CLI maps REVIEW_REQUIRED to exit_code 20
```

## Required Output

```text
HALT_STAGE = morning
HALT_COMPONENT = Position Management / Strategy Intelligence lifecycle campaign identity, surfaced by phase23_i_strategy_planning_authority_pipeline
HALT_ARTIFACT = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T045610960730Z/daily/2022-11-28/strategy/position_management.json
HALT_REASON = 93180 structured_hold_worthiness_review_required caused by canonical_campaign_identity_missing
EXIT_CODE_20_PRODUCER = ai_fund_lab_v2.runtime_v2.cli.run_daily_operation, morning_result.status == REVIEW_REQUIRED branch for phase23_i_strategy_planning_authority_pipeline
HALT_ROOT_CAUSE_CLASS = H
REPAIR_REQUIRED = YES
RESUME_SAFE_AFTER_REPAIR = YES
```

Class H = other confirmed implementation defect. The defect boundary is the filled-position/campaign identity propagation into PM/Strategy Intelligence current-position lifecycle evidence.

## Direct Evidence

### CLI / Runtime Manifest

`daily/2022-11-28/morning/cli_result.json`:

```text
exit_code = 20
stdout manifest = .runtime/runtime_state/run_manifest/2022-11-28/runtime-v2-morning-2022-11-28-20260825T055544.209653+0000.json
```

`daily/2022-11-28/morning/runtime_manifest.json`:

```text
exit_code = 20
final_state = REVIEW_REQUIRED
reason = morning pipeline review required: strategy_planning_authority_unresolved
strategy_planning_authority = REVIEW_REQUIRED
pending_slot_status = CONSUMED
pending_lifecycle_status = NOOP
safety_status = PASS
data_readiness_status = READY
review_guard_count = 0
errors = []
```

Code mapping:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
phase23_i_strategy_planning_authority_pipeline
morning_result.status == REVIEW_REQUIRED
-> exit_code = EXIT_REVIEW_REQUIRED
-> final_state = REVIEW_REQUIRED
```

### Strategy Planning Authority

`daily/2022-11-28/morning/strategy_planning_authority_evidence.json`:

```text
status = REVIEW_REQUIRED
reason = strategy_planning_authority_unresolved
pending_item_count = 0
pending_commit_status = NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED
atomic_commit_decision = SKIP_CURRENT_PENDING_COMMIT
planning_consumer_eligibility = REVIEW_REQUIRED
pending_authority_eligibility = AUTHORITY_INELIGIBLE
```

Reason codes:

```text
strategy_plan_order_side_unresolved
strategy_plan_quantity_unresolved:15180
strategy_plan_quantity_unresolved:21340
strategy_plan_quantity_unresolved:32050
strategy_plan_quantity_unresolved:35210
strategy_plan_quantity_unresolved:39660
strategy_plan_quantity_unresolved:41650
strategy_plan_quantity_unresolved:43930
strategy_plan_quantity_unresolved:44220
strategy_plan_quantity_unresolved:45940
strategy_plan_quantity_unresolved:46890
strategy_plan_quantity_unresolved:59690
strategy_plan_quantity_unresolved:67210
strategy_plan_quantity_unresolved:68380
strategy_plan_quantity_unresolved:76470
strategy_plan_quantity_unresolved:78090
strategy_plan_quantity_unresolved:79010
strategy_plan_quantity_unresolved:87890
strategy_plan_quantity_unresolved:89180
strategy_plan_quantity_unresolved:91070
strategy_plan_quantity_unresolved:92270
strategy_plan_quantity_unresolved:92540
strategy_plan_quantity_unresolved:99840
```

The quantity unresolved rows are downstream symptoms. Runtime Planning shows they came from `position_sizing_status_unresolved:UPSTREAM_REVIEW_REQUIRED`.

## First Failing Authority

### Position Management

`daily/2022-11-28/strategy/position_management.json`:

```text
producer_result_status = REVIEW_REQUIRED
validation_status = REVIEW_REQUIRED
artifact_lifecycle_status = DRAFT
human_review_status = REQUIRED
position_count = 16
```

The item-level failing position:

```text
symbol = 93180
action = UNRESOLVED
uncertainty = UPSTREAM_REVIEW_REQUIRED
reason_codes =
  - downside_risk_contained
  - positive_expected_edge
  - structured_hold_worthiness_review_required
  - trend_continuation
```

Embedded hold-worthiness evidence:

```text
status = REVIEW_REQUIRED
reason_codes = canonical_campaign_identity_missing
campaign_identity_authority_status = MISSING
continuation_quality_status = PASS
downside_risk_status = PASS
profit_protection_status = OBSERVED
future_information_used = false
```

The code path in `src/ai_fund_lab_v2/strategy/position_management.py` requires `campaign_identity_authority_status == COMPLETE`; otherwise `_structured_hold_worthiness_evidence()` emits `canonical_campaign_identity_missing`, and a HOLD becomes `UNRESOLVED`.

### Strategy Intelligence

`daily/2022-11-28/strategy/strategy_intelligence.json` for 93180:

```text
current_position_state = HELD
current_quantity = 700
current_market_value = 2,800
campaign_identity_authority_status = MISSING
missing_campaign_authority_fields =
  - position_campaign_id
  - campaign_opened_date
  - campaign_status
current_position_authority_status = PARTIAL
eligibility.status = PASS
special_risk_coverage_state = KNOWN
special_risk_eligibility = BUY_ALLOWED
event_status = KNOWN_NO_EVENT
continuation_quality.status = PASS
downside_risk.status = PASS
```

This proves the first failing authority is campaign identity propagation for a held position, not market/data/safety/corporate-action evidence.

## 2022-11-25 Carry-Over / Pending Audit

2022-11-25 produced the 93180 position via real accepted side effects:

```text
execution/fills.json:
symbol = 93180
side = BUY
quantity = 700
order_id = sha256:b3be8b9e3f85816626b96b59ef492170271009ddc3549cd71e757a00076b1fee
```

The active Pending after 2022-11-25:

```text
state = CONSUMED
item_count = 1
symbol = 93180
side = BUY
quantity = 700
consume.consumed = true
consume.submitted_order_ids = 5370e463eaec8a4a2d4dc63746d729d8cdb1aca94f47e74cf38ec9e7f4dd2520
consume.ledger_order_record_ids = ledger-order-submit-9dc6ae3600983158
```

`daily/2022-11-25/day_completion/day_completion_evidence.json`:

```text
status = PASS
pending_post_state.state = CONSUMED
pending_post_state.target_session_date = 2022-11-25
pending_lifecycle_requirement.status = NOT_REQUIRED
```

Therefore the 2022-11-28 HALT is not a stale active Pending, duplicate submit, unresolved execution, or carry-over lifecycle defect.

## 2022-11-28 Readiness / Safety Audit

`daily/2022-11-28/data_readiness/data_readiness.json` and `data_readiness/runtime_manifest.json` show:

```text
data_readiness_status = READY
data_readiness_halt_reasons = []
data_readiness_review_reasons = []
feature.status = READY
candidate.status = PRE_INFERENCE_READY
current_position.status = READY
current_position.position_state_as_of = 2022-11-25
current_valuation.status = READY
current_valuation.source_market_date = 2022-11-25
trading_calendar.status = READY
safety.status = READY
safety.reason = historical_neutral_no_event_safety_ready
```

Morning manifest also shows:

```text
safety_status = PASS
safety_halt_runtime = false
human_review_status = NOT_REQUIRED
review_guard_summary.review_guard_count = 0
errors = []
```

## G97 / G99 / G102 / G104 Relationship

```text
G104_RELATED = PARTIAL
G102_RELATED = PARTIAL
G99_RELATED = NO
G97_RELATED = NO
```

Rationale:

- 2022-11-25 93180 BUY_NEW used resolved Position Sizing quantity 700 and Submit recognized `PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY`.
- That means the post-G102/G104 quantity/submit path allowed the actual 93180 fill that later became the held position.
- The 2022-11-28 failure is not in discrete quantity recognition, Submit, or Runtime-to-Pending materialization.
- 2022-11-25 Runtime Planning for 93180 shows `canonical_quantity_source = LEGACY_POSITION_SIZING`, `quantity_status = RESOLVED_EXECUTABLE`, and no G97 residual reconsideration lineage. G97/G99 are therefore not causally implicated.

Exact causal relation:

```text
G102/G104 path enabled valid 93180 BUY fill
-> filled current position exists
-> current/campaign identity propagation fails by 2022-11-28
-> PM review-required cascade
```

The repair target is not G102/G104 semantics; it is campaign identity propagation for runtime-owned filled positions.

## First Post-G104 Holding Divergence

```text
FIRST_POST_G104_ACTUAL_HOLDING_DIVERGENCE = 2022-11-21 / 76470:400
POST_G104_ACTUAL_TRADING_DIVERGENCE_CONFIRMED = YES
```

Evidence:

```text
daily/2022-11-21/execution/fills.json
symbol = 76470
side = BUY
quantity = 400
order_id = sha256:9abd1e8c04df4af0ab2d4a229e26b5b2aeedb4b7213dac2d87cdea8144491c26
```

Current ledger at the halted state includes:

```text
symbol = 76470
quantity = 400
average_price = 26.0
market_value = 10,800
source = runtime_v2_runtime_owned_fill_projection
```

This difference is valid actual fill/holding evidence and is not the direct cause of the 2022-11-28 HALT. The HALT item is 93180.

## Classification

```text
A_legitimate_fail_closed_data_unavailable = NO
B_stale_or_invalid_pending_lifecycle_carryover = NO
C_morning_data_readiness_defect = NO
D_temporal_pit_authority_defect = NO
E_accounting_state_reconciliation_defect = NO
F_corporate_action_basis_defect = NO
G_g97_g99_g102_g104_path_interaction_defect = NO
H_other_confirmed_implementation_defect = YES
```

The implementation defect is narrow:

```text
Runtime-owned filled position / position campaign evidence exists,
but Strategy Intelligence PM lifecycle_context receives campaign_identity_authority_status = MISSING.
```

## Next Task Recommendation

Repair only the filled-position campaign identity propagation boundary:

```text
runtime-owned fill/current position
-> positions/position_campaigns canonical open campaign
-> Strategy Intelligence lifecycle_context
-> Position Management structured HOLD/ADD evidence
```

Do not change Market Quality, Risk Pacing, G97/G99/G102/G104 quantity semantics, Submit, Pending lifecycle, or Strategy parameters.
