# Phase24-IH Historical Resume Failed-Stage Pending and Safety Authority Audit

## 1. Primary Judgment

`PHASE24_IH_HISTORICAL_RESUME_FAILED_STAGE_PENDING_RECOVERY_AND_SAFETY_AUTHORITY_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Scope

対象Runは `runtime-test-historical-extended-smoke-20260801T223117629647Z`、対象Business Date / Jobは `2023-06-14:morning`。

本Auditは、Phase24-IG後にresume Entry Gateを通過したものの、同じ `2023-06-14:morning` で `historical_safety_temporal_authority_missing` により停止した事象を対象にした。Runtime長時間再実行、Historical Extended Smoke再実行、Strategy/PM/Ranking/Eligibility/Position Sizing/Submit Guard変更は実施していない。

## 3. Reviewed Evidence

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-06-14/data_readiness/data_readiness.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/strategy_planning/2023-06-14/order_plan.json`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/writer.py`
- Phase24-ID / IE / IF / IG reports
- Architecture SoT: `runtime_architecture_v2.md`, `autonomous_ai_operations_architecture.md`, `strategy_architecture_v1.md`

## 4. Direct Evidence

Run State:

- `status = HALT`
- `next_job = 2023-06-14:morning`
- `halted_at.exit_code = 20`
- `completed_business_days = 109`

Data Readiness:

- `effective_component_statuses.safety = REVIEW_REQUIRED`
- `effective_component_statuses.pending = READY`
- `final_safety_reason = historical_safety_temporal_authority_missing`
- `missing_evidence = ["historical_safety_temporal_authority"]`
- Safety resolver mismatched field: `pending_lifecycle_state`

Pending:

- `pending_plan_id = pending-strategy-review-2023-06-14`
- `state = BLOCKED`
- `target_session_date = 2023-06-14`
- `items = []`
- `source_order_plan.order_plan_id = strategy-review-2023-06-14`
- `source_order_plan.path = .runtime/runtime_state/strategy_planning/2023-06-14/order_plan.json`
- `safety_context = null`
- `planning_authority_hash/source/version = ""`
- `review_scope = ""`
- `sell_continuation_allowed = false`

## 5. IH-Q1 Artifact Writer

Writer function / module:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py::_write_no_signal_pending`
- `src/ai_fund_lab_v2/runtime_v2/pending/writer.py::write_pending_order_plan`

Write timing:

- Morning planning flow returns early on `BLOCKED` / `REVIEW_REQUIRED` / no-signal style outcomes.
- `_write_no_signal_pending` writes `order_plan.json`, `approval_artifact.json`, then writes `.runtime/pending_order_plan/pending_order_plan.json`.

Classification:

- Failure handling path, not normal approved Pending path.
- Persistent Pending Slot is replaced before the full Runtime job is recorded as successfully completed.
- Writer is direct JSON write to the canonical Current Slot.
- No previous Pending backup/restore was observed in this path.
- No failed-stage rollback was observed in this path.

## 6. IH-Q2 Resume Recovery Semantics

`scripts/runtime_test.py::resume_command` restores the resume position from `run_state.json` and skips completed successful jobs. It correctly targeted `2023-06-14:morning`.

However, before re-running the failed job, it did not rollback or isolate the Persistent Pending Slot written by the previous failed `2023-06-14:morning` attempt. Therefore, Data Readiness for the retry read that same failed-attempt Pending as current input evidence.

Resume start resolution defect: `NO`.

Resume recovery defect: `YES`.

## 7. IH-Q3 Pending Classification

The observed Pending is not a valid previous-day carry Pending, not a valid same-day active Pending, not a valid Human Review Pending, not BUY_ITEM_SCOPED_REVIEW, and not Empty/Consumed terminal Pending.

It should be classified as:

- `FAILED_ATTEMPT_ARTIFACT`
- `RETRY_INPUT_INELIGIBLE`
- `AUTHORITY_INELIGIBLE`

The reason code is:

- `failed_attempt_pending_retry_input_ineligible`

## 8. IH-Q4 Historical Safety Resolution

Before repair, Historical Daily Neutral Safety was blocked when `_pending_allows_daily_neutral_safety` saw `state=BLOCKED` and default active Pending behavior. The resolver lacked a failed-attempt retry eligibility filter.

This was not a case where Safety should be bypassed. The missing distinction was:

- invalid same-day failed-attempt Pending artifact: exclude from retry input authority
- valid active/review/safety Pending: preserve and fail-closed as before

## 9. IH-Q5 Retry / Resume Idempotency

Required retry properties:

- failed-attempt Persistent Pending must not become the retry input authority
- Ledger append must not be duplicated
- Submit must not be repeated
- valid prior Pending must not be removed or overwritten
- Safety Guard must remain active
- failure evidence must remain inspectable

Implemented repair satisfies the input authority classification portion. It does not delete, edit, or rollback existing Pending in-place. Operator resume is still required to prove full historical runtime progression.

## 10. Root Cause

Primary Root Cause:

`failed_stage_persistent_pending_contamination_during_historical_resume`

Secondary Root Cause:

`historical_safety_resolver_lacked_failed_attempt_pending_retry_eligibility_filter`

The previous failed `2023-06-14:morning` attempt wrote an incomplete `BLOCKED` Pending to the persistent Current Slot. On resume, the retry read that artifact before Strategy Pipeline could regenerate the day. The Historical Safety Resolver treated its `BLOCKED` lifecycle as a blocker for Historical Daily Neutral Safety, even though the artifact had no items and no complete Safety/Planning Authority.

## 11. Repair Summary

Updated `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`:

- Added same-day failed-attempt Pending retry eligibility classification.
- Allows Historical Daily Neutral Safety generation only when the Pending is a same-day, item-empty, `BLOCKED`, strategy-review artifact with incomplete safety and planning authority.
- Emits observability:
  - `pending_artifact_retry_eligibility`
  - `pending_artifact_authority_eligibility`
  - `pending_artifact_attempt_status`
  - `pending_artifact_commit_status`
  - `failed_attempt_artifact_quarantined`
  - `historical_neutral_safety_resolution_status`
  - `historical_neutral_safety_resolution_reason`
- Preserves fail-closed behavior for active Pending, approved Pending, ambiguous Review Pending, blocked Pending with items, global safety review, and external effects.

## 12. Contract / Architecture

Architecture Updated: `NO`.

Contract Updated: `NO`.

Reason: the existing architecture already requires retry/resume idempotency, fail-closed Safety, and Current Slot authority validation. Phase24-IH implements the missing eligibility classification in Runtime Data Readiness without changing Strategy, Submit Guard, Safety Guard, or Pending lifecycle authority ownership.

## 13. Regression

Commands executed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase24_ih_pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py
```

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase24_ih_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_g_runtime_planning.py
```

Result:

- `97 passed`
- `60 warnings`
- Runtime executed: `NO`

## 14. Risk

Residual risk remains until Operator runs the actual resume. This Codex task only proved unit/regression behavior and did not mutate runtime by executing resume.

## 15. Recommended Next Task

Operator resume:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py resume \
  --run-id runtime-test-historical-extended-smoke-20260801T223117629647Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
