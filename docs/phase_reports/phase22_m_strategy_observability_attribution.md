# Phase22-M Strategy Observability / Attribution

## Primary Judgment

`PHASE22_M_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED`

Strategy Observability / Attribution foundation is implemented as a read-only Strategy Decision Trace, with per-symbol attribution, portfolio attribution, status propagation, reason-code aggregation, readiness, lineage, outcome boundary, legacy comparison, and `runtime_test.py summarize --scope strategy*` integration.

The remaining review item is an existing shared-state `system-status` regression expectation mismatch observed during the requested broader regression pass. The Phase22-M implementation itself does not change System Status producers or Runtime behavior.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- Phase22-A through Phase22-L reports, using actual repository paths.

## Existing Observability Inventory

Existing observability is centered on `scripts/runtime_test.py` with `run-status`, `status`, `summarize`, `ai-status`, and `system-status`. Runtime and AI status producers live in `src/ai_fund_lab_v2/runtime_v2/system_status.py` and `src/ai_fund_lab_v2/runtime_v2/ai_status.py`. Existing summarize scopes were `overview`, `performance`, `positions`, `lifecycle`, and `full`; Phase22-M adds explicit Strategy scopes without changing the legacy-compatible full scope.

## Artifact Inventory

The Strategy trace expects:

- Market Context
- Corporate Event
- Portfolio Policy
- Dynamic Position Count
- Dynamic Cash / Exposure
- Portfolio Construction
- Position Sizing
- Position Management
- Runtime Planning

Each artifact is summarized by schema version, producer, business date, status, consumer eligibility, source artifacts, source hashes, config hash, reason codes, confidence, and uncertainty.

## Dependency Graph

The trace records read-only dependencies from Market Context and Corporate Event into Portfolio Policy, through Dynamic Position Count, Dynamic Cash / Exposure, Portfolio Construction, Position Sizing, Position Management, and Runtime Planning. It does not recalculate any upstream decision.

## Strategy Decision Trace

Implemented `strategy_decision_trace.v1` in `src/ai_fund_lab_v2/strategy/observability.py` and `schemas/strategy/strategy_decision_trace.schema.json`.

The trace is deterministic and includes:

- overall status
- artifact inventory
- source/hash/config lineage
- status propagation
- decision path
- blocking and review reasons
- runtime preservation flags

## Per-symbol Attribution

Per-symbol rows join observed artifact fields only:

- candidate / opportunity rank fields from Portfolio Construction
- membership intent
- target weight / notional from Position Sizing
- PM action / intensity
- Runtime Planning intent
- reason codes, confidence, uncertainty

The trace explicitly keeps `share_quantity_decided=false` and `order_price_decided=false`.

## Portfolio Attribution

Portfolio-level attribution covers market regime, trend, breadth, volatility, policy posture, target count, cash/exposure, member count, total target weight, and PM action counts.

## Status Propagation

Status propagation is recorded edge-by-edge with source artifact, source status, consumer artifact, consumer status, and propagation reason.

## Reason-code Aggregation

Reason codes are aggregated into Market, Event, Candidate, Opportunity, Portfolio, Capital, Sizing, PM, Runtime Planning, Safety, PIT, Lineage, Config, and Unclassified buckets while retaining original source artifact and reason code.

## Legacy vs Dynamic Comparison

Read-only comparison supports `SAME`, `DIFFERENT`, `NOT_COMPARABLE`, and `SOURCE_UNAVAILABLE`. Differences are not evaluated as good/bad or profitable/unprofitable.

## Readiness / Eligibility Summary

Each artifact reports lifecycle status, producer result status, source authority status, runtime consumer eligibility, blocking gaps, and review gaps. Phase22-M does not change consumer eligibility.

## Outcome Boundary

Outcome attribution is post-decision only. The schema and validator require:

- `strategy_input_allowed=false`
- `learning_input_allowed=false`

## CLI / Summarize Contract

`scripts/runtime_test.py summarize` now accepts:

- `strategy`
- `strategy-trace`
- `strategy-attribution`
- `strategy-readiness`
- `strategy-shadow`

Existing scopes remain compatible.

## Output Contract

Human-readable Strategy summary and machine-readable JSON are available through the new scopes. The JSON references artifacts and compact summaries; it does not embed giant source artifacts.

## Determinism

The trace uses explicit artifact paths and the run business date. It does not select latest artifacts, use current time, randomize order, infer missing artifacts, or copy previous-day context.

## Date / Hash / Lineage

The trace checks business date alignment, artifact hash, source lineage presence, source hashes, config hashes, and cross-date artifacts. It reports gaps without rewriting Strategy results.

## Failure / Bootstrap Contract

Missing required artifacts produce `INCOMPLETE_ATTRIBUTION`. Hash mismatch, cross-date artifacts, unsupported schema, and outcome-as-input violations block. Partial Strategy artifact sets remain observable without fake PASS.

## Runtime Preservation

No Strategy producer authority, Runtime consumer, Pending, Submit, Execution, Ledger, Current, Safety, or Broker path was changed. Runtime switch was not performed.

## Tests

- Phase22-M unit and CLI scope: 5 passed.
- Phase22-A through M plus existing summarize scopes: 132 passed.
- Runtime/AI status short preservation: 22 passed.
- Compileall: PASS.
- JSON schema validation: PASS.
- `run-status --json`: PASS with `PYTHONPATH=src`.
- Broader system-status regression attempt: 4 failed in `tests/runtime_v2/test_phase19_ax_system_status.py` due existing shared runtime state returning exit code 10 instead of stale expected 0/20.

## Long Tests Not Executed

5BD, 20BD, 200BD, 1-year, 3-year, and long runtime smoke were not executed.

## Blocking Gaps

None in the Phase22-M Strategy Observability implementation.

## Non-blocking Gaps

Existing `system-status` shared-state regression requires review before Phase22-N closure.

## Next Gate

Phase22-N: Implementation Closure / Step Gate / Runtime Switch Readiness.

Phase22-N entry ready: YES.
Runtime switch ready: REVIEW_REQUIRED.
Legacy retirement ready: NO.
