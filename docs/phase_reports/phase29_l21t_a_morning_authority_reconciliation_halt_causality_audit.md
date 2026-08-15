# Phase29-L21T-A - Morning Authority Reconciliation HALT Causality Audit

Task ID: `Phase29-L21T-A`  
Mode: READ-ONLY causality audit. No implementation, config, threshold, schema, Runtime, Pending, Accepted Generation, Model, fresh-run, resume-run, repair-run, or long Historical run was performed.

## 1. Executive Summary

Primary judgment:

```text
PHASE29_L21T_A_L21S_REGRESSION_CONFIRMED_WITH_NON_DIRECT_HISTORICAL_SAFETY_CONSUMER_SPLIT_GAP
```

The short fresh validation run stopped at `2022-08-24:morning` because Strategy Planning Authority could not create an executable pending item from the `2022-08-24` Strategy artifacts. The direct unresolved item was `78780`, whose Runtime Planning row was `BUY_NEW` but had `planned_quantity=0` and `quantity_status=REVIEW_REQUIRED_AUTHORITY_UNRESOLVED`.

The root authority chain is:

```text
L21S PC one-lot fallback
-> 78780 target_weight 0.243189
-> above Strategy maximum_position_weight 0.18, still below Safety hard cap 0.25
-> Position Sizing artifact BLOCK: target_weight_above_position_cap:3
-> Runtime Planning REVIEW_REQUIRED with quantity_not_produced_due_to_upstream_block
-> Strategy Planning Authority reason strategy_plan_quantity_unresolved:78780
-> Morning final_state REVIEW_REQUIRED / exit_code 20
-> Runtime Test HALT / exit_code 30
```

The observed `safety_operation_guard` `SAFETY_MISSING` is real as a legacy latest-path checkpoint, but it is not the direct halt cause in this run. Both `2022-08-23` and `2022-08-24` show the same checkpoint-level `SAFETY_MISSING`; `2022-08-23` still completed successfully because Data Readiness historical temporal authority superseded it for downstream planning. On `2022-08-24`, the top-level and downstream Strategy Planning safety authority were also the historical neutral authority, not latest safety.

## 2. Primary Judgment

`PHASE29_L21T_A_L21S_REGRESSION_CONFIRMED_WITH_NON_DIRECT_HISTORICAL_SAFETY_CONSUMER_SPLIT_GAP`

This is not primarily a Morning Safety halt. It is a L21S PC/PS/RP authority integration regression: Portfolio Construction authorized a one-lot Strategy soft-cap overshoot, but the Position Sizing/runtime planning authority chain used by the target run did not produce an executable quantity and surfaced the row as unresolved.

Secondary confirmed gap:

```text
HISTORICAL_SAFETY_AUTHORITY_CONSUMER_SPLIT_GAP_NON_DIRECT
```

`safety_operation_guard` still reads `.runtime/runtime_state/safety/latest_safety_decision.json` and emits fail-closed blocks even when Data Readiness has explicitly materialized `ignored_latest_safety_decision` and historical temporal safety authority. In this run that split is misleading observability, not the direct final-state producer.

## 3. Run / Halt Facts

Target run:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T011634720410Z
```

Observed facts:

- Intended period: `2022-08-23` through `2022-09-16`.
- Completed days: `['2022-08-23']`.
- Runtime Test status: `HALT`, exit code `30`.
- Morning CLI on `2022-08-24`: exit code `20`.
- Morning final state: `REVIEW_REQUIRED`.
- Morning reason: `morning pipeline review required: strategy_planning_authority_unresolved`.
- Morning subprocess trace: source commit `54f91f8edb8562a40ba1d4681babf9adbfa3dec4`, `source_dirty=true`.

## 4. Historical Safety Authority

`2022-08-24/data_readiness/data_readiness.json` and the morning manifest show:

```text
data_readiness_status = READY
data_readiness_safety_status = READY
safety_authority = historical_initial_no_external_effect
safety_authority_source = data_readiness_historical_temporal_authority
safety_authority_type = HISTORICAL_PENDING_SAFETY_CONTEXT
safety_decision = NEUTRAL
safety_status = PASS
safety_block_buy = false
safety_block_sell = false
safety_block_submit = false
ignored_latest_safety_decision = .runtime/runtime_state/safety/latest_safety_decision.json
```

Code confirms the intended historical propagation path in `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`:

- Lines 512-523 append `historical_safety_authority` after Data Readiness when effective safety differs from latest-path safety.
- Lines 680-692 pass `_strategy_planning_safety_authority_payload(...)` into `activate_strategy_planning_authority`.
- Lines 1917-1928 overwrite the Strategy Planning safety payload from Data Readiness historical authority in historical mode.
- Lines 1951-1968 build a `RuntimeSafetyDecision` with `safety_source=data_readiness_historical_temporal_authority`, `decision=NEUTRAL`, and replay permissions.

Therefore the expected downstream Strategy Planning safety authority for historical replay is:

```text
data_readiness_historical_temporal_authority
```

## 5. Safety Operation Guard Authority

The legacy Safety Operation Guard path is still latest-path based.

Code evidence:

- `run_daily_operation.py` lines 299-309 calls `load_runtime_safety_decision(runtime_root, business_date, mode)` and records the result as stage `safety_operation_guard`.
- `runtime_v2/safety_decision.py` lines 58-65 always resolves the path as `Path(runtime_root) / SAFETY_DECISION_RELATIVE_PATH`.
- `runtime_v2/safety_decision.py` lines 175-190 returns `REVIEW_REQUIRED`, `SAFETY_MISSING`, `block_buy=true`, `block_sell=true`, and `block_submit=true` when that latest-path file is absent.

Artifact evidence:

- `2022-08-23/morning/morning_manifest.json` stage `safety_operation_guard`: `SAFETY_MISSING`, latest path, all side blocks true.
- `2022-08-24/morning/morning_manifest.json` stage `safety_operation_guard`: same `SAFETY_MISSING`, latest path, all side blocks true.
- Both days also have a later `historical_safety_authority` stage with `PASS`, `NEUTRAL`, `data_readiness_historical_temporal_authority`, all side blocks false.
- `2022-08-23` passed despite the same guard marker.

Q1 classification:

```text
legacy consumer / stale latest-path dependency / partial authority migration
```

It is not an intended dual-authority design for historical downstream planning. Prior Phase28-D26 already documented that `safety_operation_guard` still consumes latest safety, while downstream planning should consume Data Readiness historical authority.

## 6. Authority Conflict

Q2 answer:

```text
YES, at the safety_operation_guard component boundary.
```

If a downstream or checkpoint consumer emits authoritative side blocks from `.runtime/runtime_state/safety/latest_safety_decision.json` after Data Readiness has explicitly marked that path as `ignored_latest_safety_decision`, that component violates the historical authority contract.

However, in this target run the final Morning safety fields and Strategy Planning safety lineage consumed the expected historical authority. The conflict is therefore:

```text
AUTHORITY_CONTRACT_VIOLATION_AS_OBSERVABILITY_AND_CHECKPOINT_SEMANTICS
NOT_DIRECT_FINAL_HALT_CAUSE
```

Q3 classification:

```text
WRONG_AUTHORITY_SOURCE_SELECTED
```

It was not real absence of historical Safety evidence. Historical temporal Safety evidence existed and was READY. The missing evidence was only the latest runtime Safety artifact requested by the legacy guard.

## 7. Strategy Planning Authority Resolution

Producer:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
function: activate_strategy_planning_authority
```

Final-state aggregation path:

- `run_daily_operation.py` lines 680-696 invokes `activate_strategy_planning_authority`.
- Lines 703-709 appends stage `phase23_i_strategy_planning_authority_pipeline`.
- Lines 713-716 set `exit_code=EXIT_REVIEW_REQUIRED`, `final_state=REVIEW_REQUIRED`, and warning `morning pipeline review required: {morning_result.reason}`.

Reason generation path:

- `strategy_authority.py` lines 436-448 rejects any BUY/SELL plan with `planned_quantity <= 0` as `strategy_plan_quantity_unresolved:{symbol}`.
- Lines 364-370 write review approval evidence with `reason=strategy_planning_authority_unresolved` when `reason_codes` exist but no pending items exist.
- Lines 386-388 return `status=REVIEW_REQUIRED` and `reason=strategy_planning_authority_unresolved`.

Artifact evidence:

```text
2022-08-24/morning/strategy_planning_authority_evidence.json
status = REVIEW_REQUIRED
reason = strategy_planning_authority_unresolved
reason_codes = ['strategy_plan_quantity_unresolved:78780']
pending_item_count = 0
pending_commit_status = NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED
pending_authority_eligibility = AUTHORITY_INELIGIBLE
pending_retry_eligibility = RETRY_INPUT_INELIGIBLE
```

Q5 classification:

```text
ACTUALLY_UNRESOLVED
```

The Strategy Planning Authority was actually unresolved at the consumer boundary: there was one BUY_NEW intent but no executable quantity and no pending item. This is not a final aggregator misclassification.

## 8. Pending Carryover Analysis

`2022-08-23`:

- Morning Strategy Planning Authority `PASS`.
- Pending item count `2`.
- Pending plan ID `pending-strategy-plan-historical-2022-08-23-50b0abd12ed0ad97`.
- Generated BUY_NEW pending items for `23880` and `94320`.
- Submit stage `APPROVED`, `submitted_count=2`, `blocked_count=0`.
- Historical safety source for submit: `data_readiness_historical_temporal_authority`.
- Execution produced BUY fills: `94320` quantity `900`, `23880` quantity `1200`.

`2022-08-24`:

- Data Readiness pending status `READY`, pending slot `CONSUMED`.
- Morning Strategy Planning Authority generated no committed pending.
- Pending commit status: `NOT_COMMITTED_REVIEW_REQUIRED_EMPTY_UNSCOPED`.
- Retry eligibility: `RETRY_INPUT_INELIGIBLE`.
- Submit and execution stages for `2022-08-24` were not reached.

Pending is not the direct halt cause. The pending lifecycle carried the prior day into a consumed/ready state; the halt occurred while trying to create a new `2022-08-24` planning/pending authority from Strategy artifacts.

## 9. Model Health Causality

`MODEL_HEALTH_REVIEW_REQUIRED` is present on both `2022-08-23` and `2022-08-24`, including `BASELINE_CURRENT_SEMANTICS_MISMATCH` reasons. The AI lifecycle gate nevertheless reports:

```text
block_buy = false
block_sell = false
block_submit = false
buy_planning_permission = PASS
sell_planning_permission = PASS
```

`2022-08-23` completed with the same category of model health review signal. The `2022-08-24` final reason is not model health; it is `strategy_planning_authority_unresolved`.

Classification:

```text
REVIEW_ONLY_NOT_HALTING
```

## 10. L21S Causality

L21S is causal for the target halt.

Evidence for `78780` in `2022-08-24/strategy/portfolio_construction.json`:

```text
semantic_buy_type = BUY_NEW
normal_target_weight = 0.18
target_weight = 0.243189
one_lot_fallback_applied = true
one_lot_feasibility_status = PASS
one_lot_quantity = 100
one_lot_notional = 242000.0
boundary_classification = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
strategy_cap_weight = 0.18
strategy_cap_overshoot_applied = true
strategy_cap_overshoot_weight = 0.063189
safety_hard_cap_weight = 0.25
safety_margin_after_trade = 0.006811
```

Evidence for `2022-08-24/strategy/position_sizing.json`:

```text
schema_version = position_sizing_shadow_error.v1
producer_result_status = BLOCK
error = target_weight_above_position_cap:3
reason_codes = ['strategy_shadow_generation_error']
```

Evidence for `2022-08-24/strategy/runtime_planning.json`:

```text
producer_result_status = REVIEW_REQUIRED
plan 78780 = BUY_NEW
planned_quantity = 0
planning_reason = portfolio_add_candidate_maps_to_buy_new;quantity_not_produced_due_to_upstream_block
quantity_status = REVIEW_REQUIRED_AUTHORITY_UNRESOLVED
pending_eligibility = CANDIDATE_ONLY
```

The run's base commit `54f91f8...` Position Sizing validation only allowed existing-position drift/reducing exceptions and had no lot-aware Strategy soft-cap overshoot exception. It appended `target_weight_above_position_cap:{index}` when `target > maximum_position_weight`. The current dirty worktree contains additional lot-aware exception code, but the target run itself was produced with `source_dirty=true`; the immutable artifact chain is authoritative for this audit.

Classification:

```text
L21S_CAUSAL
```

The causal mechanism is not the minimum meaningful notional diagnostic itself. It is the L21S one-lot expression allowing a BUY_NEW target above the Strategy soft cap while the target run's downstream Position Sizing / Runtime Planning authority chain still treated that as unresolved/blocking.

## 11. SELL Independence

The legacy `safety_operation_guard` reports:

```text
safety_block_sell = true
```

while the effective historical safety authority reports:

```text
safety_block_sell = false
sell_planning = ALLOWED_FOR_REPLAY
sell_submit = ALLOWED_FOR_REPLAY
```

Because `2022-08-24` halted before sell continuity stages, no actual SELL item was blocked in this run. However, the checkpoint-level semantics are dangerous because a latest-path missing Safety marker still expresses a global sell block inside historical replay evidence.

Classification:

```text
SELL_INDEPENDENCE_AT_RISK
```

Not confirmed as an executed SELL violation in this run, but the guard's side-block fields conflict with the historical BUY/SELL independence contract and should be repaired or demoted for historical mode.

## 12. Regression / Lineage

Historical Safety lineage:

- Phase17-BJ established historical daily neutral Safety authority in Data Readiness, while Production/Demo missing latest Safety remains fail-closed.
- Phase19-BO corrected system-status to consume closed Historical Data Readiness / Submit safety evidence rather than only `.runtime/runtime_state/safety/latest_safety_decision.json`.
- Phase28-D26 explicitly documented that `safety_operation_guard` still consumes latest safety, but downstream planning should use Data Readiness historical authority.

Safety regression classification:

```text
Regression confirmed = NO
Partial migration gap = YES
```

This appears to be a known leftover/partial migration of the guard checkpoint, not a newly reintroduced direct halt path.

L21S regression classification:

```text
Regression confirmed = YES
```

The prior run day `2022-08-23` passed. On `2022-08-24`, the L21S one-lot BUY_NEW expression produced a Strategy soft-cap overshoot within Safety hard cap, and the downstream authority chain halted on unresolved quantity.

## 13. Root Cause Classification

Direct root cause:

```text
PC_PS_ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_AUTHORITY_MISMATCH
```

Direct halt cause:

```text
strategy_planning_authority_unresolved
-> strategy_plan_quantity_unresolved:78780
-> Runtime Planning quantity_not_produced_due_to_upstream_block
-> Position Sizing BLOCK target_weight_above_position_cap:3
-> PC L21S one-lot target_weight 0.243189 above Strategy cap 0.18 but below Safety hard cap 0.25
```

Secondary non-direct gap:

```text
HISTORICAL_SAFETY_LATEST_PATH_GUARD_OBSERVABILITY_SPLIT
```

Not causal:

- Real Safety evidence absence.
- Model Health review.
- Pending carryover.
- Submit/execution.
- Corporate Action quarantine.

## 14. Repair Recommendation

Recommended L21T-B repair scope:

```text
Focused production-common PC/PS/RP authority repair for one-lot Strategy soft-cap overshoot.
```

The repair should make one of these authority contracts explicit and consistent:

1. If PC may authorize `ONE_LOT_STRATEGY_SOFT_CAP_OVERSHOOT_WITHIN_SAFETY_HARD_CAP`, PS validation and Runtime Planning must consume that authorization and produce the corresponding executable one-lot quantity.
2. If PS remains the hard arbiter for Strategy maximum position weight, PC must not emit a positive BUY_NEW target above that cap as runtime-consumable authority.

Repair must preserve:

- Safety hard concentration cap.
- Production/Demo fail-closed latest Safety requirement.
- Historical Data Readiness temporal Safety authority.
- BUY/SELL independence.
- No fixed BUY count, no threshold tuning, no forced deployment.

Secondary repair:

```text
Demote or reconcile historical safety_operation_guard latest-path fields so they cannot appear as authoritative historical side blocks after Data Readiness has emitted ignored_latest_safety_decision.
```

This secondary repair should be observability/authority reconciliation, not a historical-only fail-open.

## 15. L21T-B Entry Decision

```text
L21T_B_READY = YES
```

Gate assessment:

- Direct halt cause identified: YES.
- Responsible producer/consumer/aggregator identified: YES.
- Historical vs Production Safety contract clarified: YES.
- Model Health causality classified: YES.
- L21S causal/non-causal classified: YES, causal.
- Narrow repair scope defined: YES.

Recommended next task:

```text
Phase29-L21T-B - One-Lot Strategy Soft-Cap Authority Integration Repair
```

Primary focus should be production-common PC/PS/RP authority integration. The historical Safety guard split can be repaired as a secondary authority-observability issue, but it is not the direct cause of the `2022-08-24` halt.
