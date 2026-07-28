# Phase22-G Runtime Planning Implementation

## Primary Judgment

`PHASE22_G_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED`

Runtime Planning Artifact Foundation was added as a production-common, read-only Strategy artifact. It is produced, schema-valid, and shadow-readable, but remains `DRAFT` / `REVIEW_REQUIRED` / `NOT_ELIGIBLE`. It is not connected to Production Runtime, Pending, Approval, Submit, Execution, scheduler, recovery, or any legacy retirement path.

## Reviewed SoT

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase22_a_market_context.md`
- `docs/phase_reports/phase22_aa_corporate_event.md`
- `docs/phase_reports/phase22_b_candidate_opportunity_compatibility.md`
- `docs/phase_reports/phase22_c_portfolio_policy.md`
- `docs/phase_reports/phase22_d_position_management.md`
- `docs/phase_reports/phase22_e_portfolio_construction.md`
- `docs/phase_reports/phase22_f_capital_deployment.md`
- Runtime source inventory under `src/ai_fund_lab_v2/runtime_v2/planning/`, `pending/`, `submit/`, `approval/`, and `execution/`.

## Existing Runtime Planning Inventory

- Morning BUY planning remains in `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`.
- PM ADD planning remains in `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`.
- REDUCE / EXIT sell planning remains in `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`.
- Pending write and composition remain in `src/ai_fund_lab_v2/runtime_v2/pending/`.
- Submit remains in `src/ai_fund_lab_v2/runtime_v2/submit/`.

## Planning Stage Inventory

Expected historical stage names include `morning_ai_planning_pending_pipeline`, `runtime_data_readiness_gate`, `capital_deployment_policy`, and `sell_planning_pending_pipeline`. The known carryover regression still misses `morning_ai_planning_pending_pipeline` in the manifest and raises `StopIteration`; Phase22-G does not fix or alter it.

## Current Authority Inventory

BUY intent, ADD intent, REDUCE intent, EXIT intent, allocation, quantity, lot rounding, Pending composition, Approval, Submit, and Execution authorities remain with the existing runtime modules. Phase22-G only produces shadow planning intent evidence and downstream quantity references.

## Current Mapping Inventory

- Candidate / Opportunity -> existing BUY Planning.
- PM ADD -> ADD Planning, shadow `BUY_ADD`.
- PM REDUCE -> Sell Planning, shadow `SELL_REDUCE`.
- PM EXIT -> Sell Planning full exit, shadow `SELL_EXIT`.
- Capital Deployment -> affordability / allocation posture reference only.
- Current / Ledger -> available position / cash authority.
- Pending -> duplicate / reservation authority.

## Pending Contract Inventory

Phase22-G expresses a future pending-candidate contract with `planning_id`, `security_code`, `planning_intent`, `order_side_intent`, `quantity_required`, `quantity_authority`, `pending_eligibility`, source references, and reason codes. It does not issue `pending_id`, call the Pending writer, mutate lifecycle, cancel duplicates, or replace Pending.

## Submit Boundary Inventory

Submit command, broker request, broker quantity, order price, accepted order evidence, and submit guards remain under `runtime_v2/submit/`. Phase22-G sets `submit_generated=false` and has no Submit or broker request path.

## Direct Reference Inventory

Direct reference categories were inventoried for Portfolio Construction, Capital Deployment, Position Management, Runtime Planning, Pending, Approval, Submit, Execution, Historical adapter, status / summarize, fixtures, recovery, and scheduler / LaunchAgent. Phase22-G adds only Strategy-side runtime planning files and evidence.

## Runtime Planning Responsibility

The new producer interprets Strategy member intent, Capital Deployment posture, and Position Management intent; generates read-only `BUY_NEW`, `BUY_ADD`, `SELL_REDUCE`, `SELL_EXIT`, `NO_ACTION`, or `UNRESOLVED`; references downstream quantity authority; and emits evidence before runtime execution. It does not add new Strategy judgment.

## Input Contract

Inputs are business date, Portfolio Construction, Capital Deployment, Position Management, Portfolio Policy, current portfolio / cash / position summaries, Pending summary, planning config summary, source lineage, and source hashes. Future dates, implicit latest fallback, previous-day copy, missing lineage, and cross-date mismatch fail closed.

## Schema

Added `schemas/strategy/runtime_planning.schema.json` and `runtime_planning.v1`. Required statuses are separated as `artifact_lifecycle_status`, `source_authority_status`, `producer_result_status`, `runtime_consumer_eligibility`, `pending_eligibility`, and `quantity_status`.

## Planning Intent Taxonomy

`BUY_NEW`, `BUY_ADD`, `SELL_REDUCE`, `SELL_EXIT`, `NO_ACTION`, and `UNRESOLVED`.

## Strategy-to-Planning Mapping

- PM `HOLD` -> `NO_ACTION`.
- PM `ADD` -> `BUY_ADD`.
- PM `REDUCE` -> `SELL_REDUCE`.
- PM `EXIT` -> `SELL_EXIT`.
- Portfolio `ADD_CANDIDATE` -> `BUY_NEW`.
- Portfolio `EXCLUDE` -> no plan.
- Portfolio `UNRESOLVED` -> `UNRESOLVED` / review required.
- Portfolio sell membership alone does not generate SELL; SELL requires PM REDUCE / EXIT alignment.

## Quantity Authority Contract

Phase22-G never decides concrete allocation, share quantity, lot rounding, order price, minimum order adjustment, or broker quantity. Quantity-bearing intents set `quantity_required=true`, `quantity_authority=PHASE22_J_OR_DOWNSTREAM`, and `quantity_status=UNRESOLVED`.

## Planning Identity / Deduplication

`planning_id` is deterministic from business date, security code, planning intent, PM position reference, Portfolio Construction membership reference, and source hash seed. Timestamp-only and row-order-dependent identity are not used.

## Planning Conflict Contract

Conflicts such as BUY_NEW + BUY_ADD, BUY + SELL, SELL_REDUCE + SELL_EXIT, missing current position for SELL, ADD without current position, Portfolio membership / PM intent mismatch, and existing Pending conflict are fail-closed as `REVIEW_REQUIRED` or `BLOCK`.

## Upstream Status Handling

Upstream `REVIEW_REQUIRED` and `NOT_ELIGIBLE` propagate to Runtime Planning `REVIEW_REQUIRED` / `NOT_ELIGIBLE`. Upstream `BLOCK`, schema mismatch, date mismatch, hash mismatch, or missing required upstream produce `BLOCK`.

## Date / PIT

Runtime Planning business date must match all upstream artifacts and summaries. `feature_date <= business_date`; current and Pending snapshots cannot be future dated. Implicit latest fallback and previous-day Planning copy are explicitly false.

## Hash / Lineage

Portfolio Construction, Capital Deployment, Position Management, Portfolio Policy, Current Portfolio, Current Cash, Current Position, Pending, and planning config hashes are recorded. Hash mismatch blocks validation.

## Failure Contract

Input absence does not produce fixed `NO_ACTION PASS`, all-HOLD fallback, zero quantity fallback, fixed lot fallback, or Pending reuse. `NO_ACTION` is only a normal mapped planning result.

## Bootstrap Contract

Initial absence or missing upstream yields `DRAFT` / `REVIEW_REQUIRED` or `BLOCK` / `NOT_ELIGIBLE`; previous-day copy, latest fallback, fixed BUY / SELL, and quantity-zero fallback are forbidden.

## Existing Planning Behavior Preservation

Existing morning BUY Planning, ADD Planning, Sell Planning, Pending composition, Approval, Submit, and Execution remain unchanged. Phase22-G artifact is not mixed into existing runtime output.

## REDUCE / EXIT Preservation

PM REDUCE remains intent / intensity only; Sell Planning remains REDUCE quantity authority. PM EXIT remains full-exit intent; downstream Sell Planning remains full-position quantity authority. Phase22-G generates no SELL quantity.

## Pending / Submit Authority Preservation

Pending writer, Pending composition, Pending identity, Pending dedup, Approval, Submit guard, Corporate Action guard, Broker request, and Execution were preserved. Evidence records all connection flags false.

## Fixture / Shadow Consumer

Fixture consumer can read schema and planning intent, validate mapping, conflict, date, hash, lineage, and reject Production use. It cannot generate Pending, Submit, Approval, quantity, lot rounding, or Broker request.

## Produced-but-not-consumed Evidence

Machine-readable evidence exists at `reports/phase22_g_runtime_planning/phase22_g_evidence_20260727/`. The produced artifact is `.runtime/strategy_artifacts/runtime_planning/2026-07-15/runtime_planning.json`.

## Known Regression Analysis

`known_regression_analysis.json` records:

- `phase14e36` expected `morning_ai_planning_pending_pipeline`, actual manifest missing, `StopIteration`, CLI `exit_code=20`.
- `phase15h` sell planning CLI still returns `exit_code=20`.
- No fix attempted in Phase22-G.
- Phase22-G shadow path is unrelated and not connected to manifest generation.

## Tests

Short tests executed:

- `python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py`
- Known regression confirmations for `phase14e36` and `phase15h`

Long tests were not executed.

## Design Freeze Compliance

No Runtime switch, no Production Runtime connection, no Pending / Submit / Approval / Execution changes, no concrete sizing, no lifecycle promotion, no legacy revoke / quarantine / delete.

## Legacy Preservation

Legacy Authority remains active. Old paths and producers remain untouched.

## Blocking Gaps

None for Phase22-G foundation.

## Non-blocking Gaps

- Upstream Phase22 artifacts remain `REVIEW_REQUIRED` / `NOT_ELIGIBLE` by design.
- Existing known Runtime regressions remain separate and require an independent fix task before depending on affected runtime paths.

## Next Gate

Phase22-H Entry: `YES_WITH_SEPARATE_REGRESSION_AWARENESS`.

Regression Fix Task required: `YES`.

Runtime switch ready: `NO`.

Legacy retirement ready: `NO`.
