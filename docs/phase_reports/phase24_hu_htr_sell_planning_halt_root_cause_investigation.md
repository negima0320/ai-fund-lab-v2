# Phase24-HU HTR Sell Planning HALT Root Cause Investigation

## 1. Primary Judgment

```text
PHASE24_HU_MULTI_CAUSAL_ROOT_CAUSE_CONFIRMED
```

Phase24-HT Planning Submit Feasibility was invoked, failed as expected, and was materialized. The 2022-07-25 Sell Planning HALT is not a Submit Guard regression and not a Phase24-HT evidence materialization defect.

The root cause is multi-causal:

```text
EXPECTED_FAIL_CLOSED_BEHAVIOR
+
PRE_EXISTING_BUY_REVIEW_SELL_PLANNING_COUPLING_GAP
+
PRE_EXISTING_HISTORICAL_SAFETY_AUTHORITY_CONSUMER_MISMATCH
```

## 2. Root Cause

Phase24-HT correctly moved the deterministic exposure block upstream:

```text
current_exposure = 685,510
planned BUY 66590 = 166,400
post_buy_exposure = 851,910
max_exposure = 850,000
overage = 1,910
```

Therefore `attach_approval_link` kept the BUY item non-submittable and set the Pending plan to:

```text
state = REVIEW_REQUIRED
approved_item_ids = []
planning_submit_feasibility.status = REVIEW_REQUIRED
violated_policy = max_exposure
```

Sell Planning then failed before Position Management because Data Readiness treated the `REVIEW_REQUIRED` Pending slot as both:

```text
pending_review_required
historical_safety_temporal_authority_missing
```

## 3. Phase24-HT Causality

Phase24-HT is causal as the upstream behavior change, but the implementation is correct under the frozen HT contract.

Not confirmed:

- `PHASE24_HT_IMPLEMENTATION_DEFECT`
- `PHASE24_HT_EVIDENCE_MATERIALIZATION_DEFECT`
- Submit Guard degradation

Confirmed:

- HT Preflight prevented a deterministic Submit-blocked BUY from becoming `APPROVED Pending`.
- Downstream Historical Safety / Sell Planning did not have a contract for continuing SELL/PM when BUY Pending is `REVIEW_REQUIRED`.

## 4. Planning Preflight Trace

Planning Preflight Invoked:

```text
YES
```

Call path:

```text
strategy_authority.activate_strategy_planning_authority
  -> link_approval_to_pending
  -> pending.promotion.attach_approval_link
  -> planning_submit_feasibility.evaluate_planning_submit_feasibility
```

Result:

```text
FAIL / REVIEW_REQUIRED
```

Materialization path:

```text
.runtime/pending_order_plan/pending_order_plan.json
planning_submit_feasibility
```

The `planning_submit_feasibility = null` observed in the Morning manifest belongs to the pre-morning EMPTY pending read during Data Readiness, not the newly written strategy Pending plan. The final Pending plan contains the Preflight evidence.

## 5. Pending REVIEW_REQUIRED Direct Cause

Direct writer:

```text
src/ai_fund_lab_v2/runtime_v2/pending/promotion.py
attach_approval_link
```

Direct cause:

```text
Planning Submit Feasibility FAIL
violated_policy = max_exposure
```

Not the direct cause:

- Safety / AI Lifecycle Review
- existing Runtime State `BUY_REVIEW_REQUIRED`
- Sell Planning-side re-evaluation

## 6. Historical Safety Authority

Morning Safety Authority:

```text
status = READY
safety_authority = historical_initial_no_external_effect
safety_authority_type = HISTORICAL_DAILY_NEUTRAL
safety_authority_source = data_readiness_historical_temporal_authority
safety_business_date = 2022-07-25
safety_policy_version = historical_replay_neutral_safety_v1
safety_decision = NEUTRAL
```

Producer:

```text
data_readiness._historical_daily_neutral_safety_authority
```

Sell Planning resolver:

```text
data_readiness._safety_readiness_payload
```

Sell Planning failed because the Pending slot was active `REVIEW_REQUIRED`. The resolver could not use `HISTORICAL_PENDING_SAFETY_CONTEXT` because the pending lifecycle was not `APPROVED`, and could not use `HISTORICAL_DAILY_NEUTRAL` because active/review pending is not eligible for daily neutral safety.

Morning/Sell Planning Authority Match:

```text
PARTIAL
```

They share historical-neutral concepts, business date, and policy version, but they are not the same resolved lifecycle authority.

## 7. Runtime State BUY_REVIEW_REQUIRED

Writer:

```text
run_daily_operation.py runtime_state_refresh
  -> produce_runtime_operation_state
```

Mapping:

```text
_runtime_safety_state_for_operation_state
```

maps `RuntimeSafetyDecision` `REVIEW_REQUIRED` to:

```text
BUY_REVIEW_REQUIRED
```

This was not the direct HALT cause. The previous run also had `runtime_state_safety_state = BUY_REVIEW_REQUIRED`, but Sell Planning completed and Submit was reached.

## 8. BUY Review -> SELL Block Contract

Judgment:

```text
DESIGN_GAP
```

The observed block is not simply a BUY review stopping SELL. It is a Pending/Safety lifecycle coupling:

```text
BUY Pending REVIEW_REQUIRED
  -> pending_review_required
  -> historical safety temporal authority unavailable
  -> Sell Planning entry gate REVIEW_REQUIRED
  -> Position Management NOT_EXECUTED
```

The current contract does not clearly define whether a non-submittable BUY Pending may coexist with SELL Planning/PM continuation under historical neutral safety.

## 9. Previous Run Comparison

Previous run:

```text
runtime-test-historical-extended-smoke-20260731T052507224758Z
```

Comparison:

| Item | Previous Run | Target Run |
|---|---|---|
| Morning Planning | PASS | PASS |
| 66590 BUY amount | 166,400 | 166,400 |
| current exposure | 685,510 | 685,510 |
| max exposure | 850,000 | 850,000 |
| Pending | APPROVED | REVIEW_REQUIRED |
| Sell Planning | PASS | REVIEW_REQUIRED / exit 20 |
| Submit | reached | not reached |
| Submit Guard | BUY BLOCK max_exposure, SELL PASS | not reached |

## 10. Submit Guard Status

```text
NOT_REACHED
```

Submit Guard is unchanged and not degraded in this run. The target run stopped at Sell Planning before Submit.

## 11. Required Next Work

Implementation Required:

```text
YES
```

Architecture or Contract Change Required:

```text
YES
```

Required layer:

```text
Pending / Data Readiness / Historical Safety Authority / Sell Planning Continuation Contract
```

Do not weaken Submit Guard. Do not bypass Safety. The next task should first freeze the contract for BUY `REVIEW_REQUIRED` Pending coexistence with Position Management / Sell Planning / SELL Submit.

## 12. Recommended Next Task

```text
Phase24-HV BUY REVIEW_REQUIRED Pending vs SELL Planning Continuation Contract and Implementation Gate
```

## 13. Evidence

Evidence root:

```text
reports/phase24_hu_htr_sell_planning_halt_root_cause_investigation/
```

Files:

- `evidence_inventory.json`
- `authority_lineage.json`
- `planning_preflight_trace.json`
- `pending_state_transition_trace.json`
- `historical_safety_authority_trace.json`
- `runtime_state_safety_trace.json`
- `previous_run_comparison.json`
- `root_cause_matrix.json`
- `phase24_hu_evidence.json`
