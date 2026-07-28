# Phase22-E Portfolio Construction

## Primary Judgment

```text
PHASE22_E_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Portfolio Construction foundation was implemented as a production-common, read-only Strategy artifact producer. The artifact is generated as `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` because upstream Market Context, Corporate Event, Portfolio Policy, and Position Management artifacts remain `REVIEW_REQUIRED / NOT_ELIGIBLE`.

Phase22-F entry ready: `YES`, for read-only Portfolio Construction foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- Phase22-A / AA / B / C / D reports, schemas, code, and evidence

## Existing Portfolio Assembly Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/existing_portfolio_assembly_inventory.json
```

Current portfolio assembly remains action-based:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`: Opportunity / Current / Capital Deployment Policy to BUY Pending
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`: PM ADD to ADD-derived BUY Pending
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`: PM REDUCE / EXIT to SELL Pending
- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`: canonical Pending composition

Phase22-E does not connect Portfolio Construction to these consumers.

## Current Authority Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/current_authority_inventory.json
```

Authority classification:

- portfolio membership: current Runtime Planning path remains active; future Portfolio Construction
- existing position retention: Position Management AI plus existing Sell Planning path
- new candidate inclusion: Candidate / Opportunity plus Morning Planning path
- rank: Opportunity AI
- weight: future Portfolio Construction / Capital Deployment; Phase22-E emits posture only
- allocation, cash, exposure, quantity, lot rounding: Capital Deployment / Runtime Planning / downstream authority

No authority migration was performed.

## Candidate / Opportunity Consumption Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/candidate_opportunity_consumption_inventory.json
```

Candidate and Opportunity rows are read as shadow inputs. Candidate score, Candidate order, Candidate eligibility, Opportunity score, Opportunity rank, and tie-break evidence are not recalculated or rewritten.

## Current Position Reconciliation Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/current_position_reconciliation_inventory.json
```

Current position identity is represented by `position_id` and `security_code`. Broker Snapshot, Broker accepted order, Fill, Ledger, Current writers, partial fill handling, quantity, and average cost are not rewritten.

## Capital Deployment Boundary Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/capital_deployment_boundary_inventory.json
```

Phase22-E did not change `max_positions`, `target_investment_ratio`, `cash_buffer`, `max_exposure`, per-position allocation, available cash, lot rounding, minimum order, or quantity calculation.

## Direct Reference Inventory

Machine-readable inventory:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/direct_reference_inventory.json
```

References were classified across Candidate, Opportunity, Position Management, Portfolio Policy, Portfolio Construction-equivalent logic, Capital Deployment, Runtime Planning, Pending, Submit, Historical adapter, status/summarize, fixtures, recovery, and scheduler/LaunchAgent. No cutover was performed.

## Portfolio Construction Responsibility

Implemented producer:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
schemas/strategy/portfolio_construction.schema.json
```

Portfolio Construction owns Target Portfolio / Strategy membership intent. Phase22-E implements the read-only foundation only: portfolio membership intent, relative construction priority, weight posture, reconciliation references, source lineage, and failure/status contracts.

## Input Contract

Implemented inputs:

- `business_date`
- Candidate summary / rows / artifact reference
- Opportunity ranking / rows / artifact reference
- Current Portfolio summary and current position identities
- Pending summary reference
- Portfolio Policy Artifact metadata
- Position Management Artifact metadata
- Market Context reference
- Corporate Event reference
- policy config summary
- source lineage and source hashes

Forbidden inputs remain unused: future return, future price, future regime, future corporate event, backtest result, historical performance, paper ledger PnL, test result, audit result, accepted/rejected mimicry, and future portfolio value.

## Schema

Schema version:

```text
portfolio_construction.v1
```

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/schema_validation.json
```

The schema enforces `DRAFT`, `NOT_ELIGIBLE`, no production consumer connection, no runtime switch, legacy authority active, and no concrete target weight, allocation, or quantity fields.

## Membership Intent Taxonomy

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/membership_weight_intent_validation.json
```

Phase22-E uses the minimum Strategy membership taxonomy because the SoT defines Target Portfolio responsibility but not a formal membership enum:

```text
RETAIN
ADD_CANDIDATE
REDUCE_CANDIDATE
REMOVE_CANDIDATE
EXCLUDE
UNRESOLVED
```

This is intentionally separate from Position Management `HOLD / ADD / REDUCE / EXIT`.

## Weight Intent Contract

Concrete target weights are not emitted in Phase22-E. The artifact uses posture only:

```text
INCREASE
MAINTAIN
DECREASE
REMOVE
AVOID
UNRESOLVED
```

`target_weight`, `weight_percentage`, `allocation_jpy`, `quantity`, and related concrete fields are rejected.

## Position Count Non-decision

Phase22-E records:

```text
position_count_decided=false
cash_ratio_decided=false
exposure_decided=false
position_sizing_decided=false
allocation_decided=false
quantity_decided=false
```

Dynamic Position Count remains Phase22-H. Dynamic Cash / Exposure remains Phase22-I. Position Sizing remains Phase22-J.

## Current / Candidate Reconciliation

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/reconciliation_validation.json
```

Existing positions and new candidates are reconciled by `security_code`. A duplicate existing position / candidate security is emitted as one portfolio member with candidate and Opportunity references attached, not as duplicate members.

## Priority Ordering

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/priority_ordering_validation.json
```

Priority is deterministic. Existing positions are represented first to preserve PM/current lineage, then new Opportunity rows are ordered by input Opportunity rank, Candidate order, and security code tie-break. Input score and rank are recorded but not recalculated.

## Upstream Status Handling

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/upstream_status_validation.json
```

Observed status:

```text
Market Context: SOURCE_NOT_ELIGIBLE
Corporate Event: SOURCE_NOT_ELIGIBLE
Portfolio Policy: SOURCE_NOT_ELIGIBLE
Position Management: SOURCE_NOT_ELIGIBLE
Portfolio Construction producer_result_status: REVIEW_REQUIRED
runtime_consumer_eligibility: NOT_ELIGIBLE
```

Upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` is propagated to `REVIEW_REQUIRED`, not promoted to `PASS`.

## Date / PIT

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/date_pit_validation.json
```

Validated:

- `business_date=2026-07-15`
- generated `feature_date=2026-06-26`
- `feature_date <= business_date`
- no future leakage
- no implicit latest fallback
- no previous-day Portfolio Construction copy

## Hash / Lineage

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/hash_lineage_validation.json
```

The artifact records source hashes for Candidate, Opportunity, Current Portfolio, Pending, and policy config summaries. Upstream Strategy artifacts are validated for schema/date/hash compatibility. Output artifact hash is stable and excludes its own `artifact_hash`.

## Failure Contract

Failure behavior:

- upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` -> `REVIEW_REQUIRED`
- upstream BLOCK/schema/date/hash/missing -> `BLOCK`
- Candidate / Opportunity / Current / Pending / policy config date mismatch -> `BLOCK`
- duplicate security unresolved -> `BLOCK`
- missing required current position reference -> `REVIEW_REQUIRED`
- conflicting membership intent -> `REVIEW_REQUIRED`
- future leakage -> `BLOCK`

No empty Portfolio `PASS`, all-current RETAIN `PASS`, fixed Top-N fallback, or missing-PM-as-HOLD fallback is used.

## Bootstrap Contract

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/bootstrap_validation.json
```

Initial absence does not copy previous-day artifacts, does not use latest fallback, does not emit empty Portfolio `PASS`, does not retain all current positions as `PASS`, and does not fixed-adopt Top-N candidates.

## Behavior Preservation

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/behavior_preservation.json
```

Preserved:

- Candidate count, codes, order, eligibility, reason codes
- Opportunity count, scores, ranks, tie-break
- PM actions, intensity, reason codes
- Capital Deployment output
- Runtime Planning output
- Pending output
- Submit output

Phase22-E artifact is not mixed into existing Runtime output.

## Capital Deployment Authority Preservation

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/capital_deployment_authority_preservation.json
```

Position count limits, cash limits, exposure limits, JPY allocation, share quantity, and lot rounding remain downstream authority. Capital Deployment config was not changed.

## Fixture / Shadow Consumer

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/fixture_shadow_validation.json
```

Fixture loading allows DRAFT artifacts for schema/status/date/hash/lineage/member/priority/weight-intent checks only. Production use raises `PortfolioConstructionConsumerError`.

## Produced But Not Consumed

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/produced_not_consumed_validation.json
```

Generated artifact:

```text
.runtime/strategy_artifacts/portfolio_construction/2026-07-15/portfolio_construction.json
```

The artifact is produced but not consumed by Capital Deployment, Runtime Planning, Pending, Submit, Approval, Execution, Fill, Ledger, or Current.

## Known Regressions

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/regression_validation.json
```

Known unchanged regressions:

- carryover policy short check -> `10 passed, 1 failed`; same `StopIteration` while finding `morning_ai_planning_pending_pipeline`
- capital deployment policy short check -> same existing sell planning CLI `exit_code=20`

Phase22-E code path is not involved.

## Tests

Executed short tests:

- `python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py` -> `11 passed`
- Phase22-A / AA / B / C / D / E + PM + Capital short suite -> `68 passed, 1 failed known`
- Candidate / Opportunity short tests -> `14 passed`
- known carryover regression check -> `10 passed, 1 failed unchanged`
- `PYTHONPYCACHEPREFIX=.runtime/pycache_phase22e python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy` -> `PASS`

Long Historical tests were not executed.

## Design Freeze Compliance

Machine-readable validation:

```text
reports/phase22_e_portfolio_construction/phase22_e_evidence_20260727/scope_preservation_validation.json
```

Compliant:

- no Production Consumer connection
- no Runtime switch
- no `ACCEPTED` / `ELIGIBLE` promotion
- no Candidate filter change
- no Opportunity score/rank change
- no PM action/intensity change
- no minimum holding / cooldown implementation
- no Capital Deployment / Planning / Pending / Submit change
- no concrete target position count, cash ratio, exposure, sizing, allocation, quantity, or lot rounding

## Legacy Preservation

Legacy authority remains active. No old path was removed, revoked, quarantined, or marked delete-ready.

## Blocking Gaps

None for Phase22-E read-only foundation.

## Non-blocking Gaps

- Market Context remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Corporate Event remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Portfolio Policy remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Position Management remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Concrete Target Weight / Position Count / Cash / Exposure / Position Sizing remain deferred to later phases

## Next Gate

Phase22-F entry ready: `YES`, for read-only Portfolio Construction foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.
