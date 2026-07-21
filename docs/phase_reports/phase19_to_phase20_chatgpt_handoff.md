# Phase19 to Phase20 ChatGPT Handoff

## Current Phase

Current phase:

```text
Phase20 Performance Improvement Phase
```

Phase19 is formally closed.

Final Phase19 judgment:

```text
PHASE19_CLOSURE_COMPLETE_WITH_NON_BLOCKING_GAPS
```

Supporting:

```text
PHASE19_IMPLEMENTATION_COMPLETE_WITH_NON_BLOCKING_GAPS
PHASE19_RUNTIME_ACCEPTANCE_PASS
PHASE19_BY_SUMMARIZE_RUN_AUTHORITY_CORRECTION_PASS
PHASE20_PERFORMANCE_IMPROVEMENT_READY_WITH_GAPS
```

## Project Objective

AI Fund Lab v2 aims to use J-Quants-derived Japanese equity data and the Tachibana Securities e-branch API to operate a safe, reproducible, cash-equity-only automated investment system.

Targets:

```text
Initial capital: 1,000,000 yen
Trade type: cash equity only
Target annual return: +50%
Target operation rate: 80%
Broker: Tachibana Securities e-branch API
```

The +50% annual target has not been proven. Phase20 is where performance is measured and improved.

## What Phase19 Completed

Phase19 implemented and validated the Production Runtime foundation defined by Phase18 Architecture SoT.

Completed:

- Dataset -> AI -> Accepted Generation -> Runtime authority chain
- Accepted Generation materialization
- COMMITTED Runtime pointer
- Accepted Generation-bound Candidate / Opportunity Runtime inference
- Dataset, Training, Calibration, Validation separation
- BUY lifecycle and SELL lifecycle separation
- Position Management integration
- REDUCE / EXIT SELL route and quantity contract
- Persistent Ledger and Current consistency
- Historical Runtime safety
- fresh-run/reset correctness
- Runtime Test summarize and trade attribution
- system-status truthfulness and scoped output
- Phase19-BY summarize Run Authority correction

Current COMMITTED Accepted Generation:

```text
phase19_aq_accepted_generation_641e6e313543f013
```

Pointer:

```text
.runtime/runtime_state/accepted_buy_ai_bundle.json
transaction_state = COMMITTED
```

## Absolute Authority Rules

Runtime BUY AI authority is the current COMMITTED Accepted Generation only.

Forbidden as Runtime BUY authority:

- latest directory or symlink
- filesystem mtime
- max date
- accepted_at maximum
- manual model path
- config direct model path
- legacy component fallback
- Promotion Candidate fallback
- test fallback outside isolated tests

BUY AI lifecycle failure may block BUY planning or BUY submit. It must not automatically block SELL unless SELL dependencies are unhealthy.

Generation owns Dataset, Split, Candidate, Opportunity, Calibration, Validation, Baseline/Freshness, hashes, and authority decision.

Runtime owns Current, Pending, Persistent Ledger, Position Management, Safety, Broker boundary, cash, positions, approval, submit, execution, report, and notification.

## Phase19-BY Must-Carry Rule

`runtime_test.py summarize --run-id <RUN_ID>` must aggregate only the requested Run's evidence.

Authority:

```text
reports/runtime_tests/runs/<RUN_ID>/
run_state.json
completed_business_days
Run-scoped evidence
```

Shared `.runtime` may be used only as final state/details authority when final hashes match. It must not be scanned across all dates for PM/SELL/submit/execution event counts.

The old `SELL Plan = 7` for the 1BD run was a summarize aggregation defect, not Runtime SELL behavior.

## Confirmed Evidence

### BY 1BD Run

Run:

```text
runtime-test-historical-smoke-20260721T224645728185Z
```

Summary:

```text
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T224645728185Z-20260721T230200658392Z/summary.json
```

Confirmed:

```text
completed_business_days = ["2026-07-14"]
PM decisions = 0
BUY Plan / Submit / Execution = 5 / 5 / 5
SELL Plan / Submit / Execution = 0 / 0 / 0
Current Positions = 5
Final Equity = 1,011,400
Return = +11,400 (+1.14%)
Runtime judgment = PASS
Performance judgment = NOT_EVALUATED
Strategy judgment = NOT_EVALUATED
Lifecycle consistency = PASS
```

The 1BD result is too short for strategy evaluation.

### 20BD Runtime Evidence

Run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Summary:

```text
reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json
```

Confirmed:

```text
business_days = 20
Runtime judgment = PASS
Final equity = 955,100
Total return = -44,900 (-4.49%)
Realized PnL = -51,300
Unrealized PnL = +6,400
PM distribution = HOLD 30, ADD 9, REDUCE 4, EXIT 3
Execution distribution = BUY 5, SELL 7
Lifecycle consistency = PASS
```

This is a Runtime PASS with negative performance. Do not treat it as a Runtime failure without evidence.

## Phase20 Purpose

Phase20 is Performance Improvement.

Purpose:

```text
Assuming the Runtime foundation is correct, explain quantitatively why profit or loss occurred and identify whether improvement should target AI selection, Opportunity ranking, Position Management, Risk/Capital Allocation, evidence/observability, test profile, or a real Runtime defect.
```

Do not start by changing AI, PM, Risk, or Runtime logic.

## Phase20 Initial Work

Recommended first task:

```text
Phase20-A: Performance Baseline and Attribution Evidence Inventory
```

Phase20-A should inventory:

- available Runtime Test runs
- 20BD target run
- trade history
- position history
- Opportunity candidates
- AI score / confidence / calibration evidence
- PM decisions
- market data
- performance metrics
- existing analysis artifacts
- missing evidence
- future-information leakage risk

Deliverable should be analysis readiness and missing evidence, not strategy modification.

## Initial Analysis Scope

Phase20 should analyze:

- Performance Baseline
- Performance Attribution
- Error Attribution
- Opportunity Quality
- BUY Quality
- HOLD Quality
- REDUCE / EXIT Quality
- Position Management Quality
- Market Regime
- Risk and Concentration

Do not invent missing metrics. Mark unavailable metrics as missing or derivable.

## Known Non-blocking Gaps

Carry these from BX:

- BX-F01: Performance metric, benchmark, and experiment comparison contracts are not formalized.
- BX-F02: Production broker connectivity/write path remains unverified and intentionally prohibited.
- BX-F03: Full autonomous scheduler/retraining/recovery loop is not proven.
- BX-F04: Model Health remains REVIEW_REQUIRED, Runtime impact is separated.
- BX-F05: Legacy/fallback terminology remains as non-blocking cleanup/documentation noise.

BY fixed summarize Run Authority. It did not remove the BX gaps.

## Must Read First

Read in this order:

1. `docs/02_architecture/autonomous_ai_operations_architecture.md`
2. `docs/02_architecture/runtime_architecture_v2.md`
3. `docs/02_architecture/ai_training_and_generation_lifecycle.md`
4. `docs/02_architecture/ai_generation_artifact_contract.md`
5. `docs/01_requirements/phase_roadmap.md`
6. `docs/phase_reports/phase18_final_summary_and_phase19_handoff.md`
7. `docs/phase_reports/phase18_to_phase19_chatgpt_handoff.md`
8. `docs/phase_reports/phase19_bx_final_independent_implementation_review.md`
9. `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
10. `docs/phase_reports/phase19_final_summary_and_phase20_handoff.md`

## Must Check Evidence First

Check:

1. `.runtime/runtime_state/accepted_buy_ai_bundle.json`
2. `.runtime/ai_lifecycle/generations/phase19_aq_accepted_generation_641e6e313543f013/accepted_generation_manifest.json`
3. `reports/phase_reports/phase19_bx_final_independent_implementation_review.json`
4. `reports/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.json`
5. `reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T213848054826Z-20260721T221640818568Z/summary.json`
6. `reports/runtime_tests/summaries/runtime-test-summary-runtime-test-historical-smoke-20260721T224645728185Z-20260721T230200658392Z/summary.json`

## Do Not Do

Do not:

- rerun long Historical Smoke unless explicitly requested
- run training
- run calibration
- rerun validation
- connect to broker
- place orders
- mutate Runtime State
- create a new Accepted Generation
- use performance results as training/validation authority
- change Runtime Architecture for performance convenience
- change AI/PM/Risk logic before attribution evidence supports it
- treat the 1BD +1.14% as strategy proof
- treat the 20BD -4.49% as Runtime failure without evidence

## Codex Work Rules

For Phase20 work:

- Read required docs before acting.
- Use repository evidence, not memory.
- Keep Runtime correctness separate from Strategy Performance.
- Classify findings as Strategy Performance, Runtime implementation, Test Profile, Evidence/Observability, AI Policy, or Contract mismatch.
- Prefer short, targeted validation commands.
- Avoid long-running tests unless requested.
- Update phase reports and JSON evidence for each Phase20 subtask.
