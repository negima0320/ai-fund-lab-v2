# Phase19-AY Manual Multi-day Runtime Validation Preflight

## Final Judgment

```text
PHASE19_AY_PREFLIGHT_COMPLETE
PHASE19_AY_DAY1_MANUAL_RUN_READY
```

Forbidden declarations were not made:

```text
BUY_READY
PRODUCTION_READY
AUTONOMOUS_OPERATION_COMPLETE
```

## Safety Artifact Contract

The formal latest Runtime Safety Decision artifact is:

```text
.runtime/runtime_state/safety/latest_safety_decision.json
```

The formal contract is defined by:

```text
src/ai_fund_lab_v2/runtime_v2/safety_decision.py::SAFETY_DECISION_RELATIVE_PATH
src/ai_fund_lab_v2/runtime_v2/safety_decision.py::RuntimeSafetyDecision
```

The formal writer is:

```text
src/ai_fund_lab_v2/runtime_v2/safety/producer.py::produce_runtime_safety_decision
```

The writer also appends history under:

```text
.runtime/runtime_state/safety/history/<business_date>/<safety_decision_id>.json
```

`system-status` was not using an old path. The issue was the missing-state semantics: a pre-run missing Safety Decision was being surfaced too coarsely.

## Safety Execution Timing

The Runtime Safety call graph is:

```text
runtime_test.py
→ ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
→ market_refresh
→ data_readiness
→ safety_evaluation
→ safety_refresh
→ load_runtime_safety_decision
→ safety_operation_guard
→ morning BUY planning
→ sell_planning dependency evaluation
```

`safety_evaluation` writes the authoritative Phase11 report. `safety_refresh` materializes the latest Runtime Safety Decision from that report. `system-status` is read-only and never creates the Safety Decision artifact.

Historical runtime has an additional replay-specific neutral safety authority from Data Readiness for downstream Planning. That does not replace the formal latest Safety Decision writer.

## Missing State Classification

`system-status` now distinguishes:

```text
PRE_RUN_NOT_MATERIALIZED
MATERIALIZED
ARTIFACT_DATE_MISMATCH
POST_RUN_MATERIALIZATION_MISSING
```

Current `.runtime` state for expected business date `2026-07-06`:

```text
Safety Artifact Status: NOT_YET_APPLICABLE
Missing Classification: PRE_RUN_NOT_MATERIALIZED
Materialization Stage: PRE_RUN
```

This is a normal pre-run state and does not block Day1 start by itself.

If target-date Safety or Morning route evidence exists and latest Safety Decision is still missing, `system-status` classifies it as:

```text
POST_RUN_MATERIALIZATION_MISSING
BLOCK
```

## Safety Materialization Test

An isolated historical Runtime root was used:

```text
reports/phase19_ay_manual_multi_day_runtime_preflight/isolated_safety_runtime/.runtime
```

The test ran the formal route:

```text
run_runtime_safety_evaluation
→ produce_runtime_safety_decision
→ inspect_safety_artifact
```

No handwritten Safety Decision JSON was used. No production Broker access or Broker write occurred.

Result:

```text
Safety evaluation: REVIEW_REQUIRED
Safety producer: REVIEW_REQUIRED
Latest Safety Decision materialized: YES
system-status recognition: READY
```

The REVIEW_REQUIRED result is expected for the isolated fixture because required live-equivalent safety evidence is intentionally incomplete. The materialization contract itself passed.

## system-status Safety Result

Current command result:

```text
PYTHONPATH=src:. python3 scripts/runtime_test.py system-status --json
```

Result:

```text
Overall: REVIEW_REQUIRED
Runtime State: PASS
Safety: NOT_YET_APPLICABLE
Runtime lifecycle: STATISTICAL_DRIFT_REVIEW_REQUIRED
```

The remaining REVIEW_REQUIRED is statistical drift monitoring only. Approved policy says statistical drift alone does not automatically stop BUY planning.

## BUY / SELL Boundary

BUY and SELL remain separated:

```text
BUY planning: PASS
SELL continuity: PASS
Broker write: 0
```

Pre-run Safety latest missing does not stop Day1 start. Post-run target-date Safety latest missing does block.

## Manual Run Preflight

Approved manual profile:

```text
Profile: historical-smoke
Runtime root: .runtime
Business dates: 2026-07-06 to 2026-07-10
Broker environment: historical_simulated
Broker write: false
Notification mode: payload-only
J-Quants fetch: false
```

Day1 manual run is ready.

## Regression

```text
py_compile: PASS
pytest: 8 passed
```

Commands:

```text
PYTHONPYCACHEPREFIX=.tmp_pycache PYTHONPATH=src:. python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/system_status.py
PYTHONPYCACHEPREFIX=.tmp_pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase19_ay_safety_preflight.py tests/runtime_v2/test_phase19_ax_system_status.py
```

## Non-mutation

```text
Training rerun: 0
Calibration refit: 0
Validation rerun: 0
Unified Generation created: 0
Accepted Generation created: 0
Runtime pointer write: 0
Trading state mutation by Step0: 0
BUY restart: 0
Broker access: NOT_PERFORMED
Broker write: 0
```

## Evidence

```text
reports/phase_reports/phase19_ay_manual_multi_day_runtime_preflight.json
reports/phase19_ay_manual_multi_day_runtime_preflight/safety_artifact_contract_audit.json
reports/phase19_ay_manual_multi_day_runtime_preflight/safety_execution_call_graph.json
reports/phase19_ay_manual_multi_day_runtime_preflight/safety_missing_state_classification.json
reports/phase19_ay_manual_multi_day_runtime_preflight/safety_materialization_validation.json
reports/phase19_ay_manual_multi_day_runtime_preflight/system_status_safety_validation.json
reports/phase19_ay_manual_multi_day_runtime_preflight/buy_sell_boundary_validation.json
reports/phase19_ay_manual_multi_day_runtime_preflight/manual_run_preflight.json
reports/phase19_ay_manual_multi_day_runtime_preflight/manual_run_commands.md
reports/phase19_ay_manual_multi_day_runtime_preflight/evidence_collection_commands.md
reports/phase19_ay_manual_multi_day_runtime_preflight/regression_results.json
reports/phase19_ay_manual_multi_day_runtime_preflight/non_mutation.json
reports/phase19_ay_manual_multi_day_runtime_preflight/final_judgment.json
```

## Next Step

Proceed to AY Step 1 / Step 2 manually on the local Mac:

```text
PHASE19_AY_DAY1_MANUAL_RUN_READY
```
