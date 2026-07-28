# Phase22-F Capital Deployment

## Primary Judgment

```text
PHASE22_F_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Capital Deployment foundation was implemented as a production-common, read-only Strategy artifact producer. The artifact is generated as `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` because upstream Portfolio Construction, Portfolio Policy, and Position Management artifacts remain `REVIEW_REQUIRED / NOT_ELIGIBLE`.

Phase22-G entry ready: `YES`, for read-only Capital Deployment foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- Phase22-A / AA / B / C / D / E reports, schemas, code, and evidence

## Existing Capital Deployment Inventory

Machine-readable inventory:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/existing_capital_deployment_inventory.json
```

Current implementation remains in:

- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py`
- `configs/runtime_v2/capital_deployment.json`
- `configs/runtime_v2/capital_deployment_demo.json`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/submit/`

Existing values were inventoried, not changed: `evaluation_capital=1000000`, `target_investment_ratio=0.85`, `cash_buffer=0.05`, `max_exposure=850000`, `max_position_weight=0.2`, `max_positions=5`.

## Current Authority Inventory

Machine-readable inventory:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/current_authority_inventory.json
```

Phase22-F performs no authority migration. Position count, cash reserve, gross exposure, target investment ratio, JPY allocation, share quantity, lot rounding, minimum order, Pending, and Submit remain existing authority or later-phase authority.

## Cash / Exposure Source Inventory

Machine-readable inventory:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/cash_exposure_source_inventory.json
```

Current cash, exposure, portfolio, and Pending reservation are read as shadow summaries. Ledger, Broker Snapshot, Current writer, accepted order reservation, and partial fill handling are not rewritten.

## Allocation / Quantity Boundary

Machine-readable inventory:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/allocation_quantity_boundary_inventory.json
```

Current JPY allocation, quantity calculation, insufficient cash handling, minimum order handling, and lot rounding stay in existing Runtime Planning / ADD / Sell paths. Phase22-F does not calculate notional, quantity, or lots.

## Direct Reference Inventory

Machine-readable inventory:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/direct_reference_inventory.json
```

References were classified across Portfolio Policy, Position Management, Portfolio Construction, Capital Deployment, Runtime Planning, Pending, Submit, Safety, Historical adapter, status/summarize, fixtures, recovery, and scheduler/LaunchAgent. No cutover was performed.

## Capital Deployment Responsibility

Implemented producer:

```text
src/ai_fund_lab_v2/strategy/capital_deployment.py
schemas/strategy/capital_deployment.schema.json
```

Phase22-F responsibility is read-only capital allocation intent and constraint posture. It emits portfolio capital posture, cash reserve posture, exposure posture, member allocation posture, allocation priority, and constraint status references only.

## Input Contract

Implemented inputs:

- `business_date`
- Portfolio Construction artifact metadata
- Portfolio Policy artifact metadata
- Position Management artifact metadata
- current cash summary
- current exposure summary
- current portfolio summary
- Pending reservation summary
- policy config summary
- source lineage and source hashes

Forbidden inputs remain unused: future return, future price, future portfolio value, future regime, future corporate event, backtest result, historical performance, paper ledger PnL as learning input, test result, audit result, and accepted/rejected mimicry.

## Schema / Intent Taxonomy

Schema version:

```text
capital_deployment.v1
```

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/schema_validation.json
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/capital_intent_validation.json
```

Taxonomies:

```text
portfolio_capital_posture: DEPLOY / MAINTAIN / CONSERVE / WITHHOLD / UNRESOLVED
member_allocation_posture: PRIORITIZE / NORMAL / DEPRIORITIZE / WITHHOLD / UNRESOLVED
capital_constraint_status: CAPITAL_SUFFICIENT / CAPITAL_CONSTRAINED / CASH_RESERVE_CONFLICT / EXPOSURE_CONFLICT / ALLOCATION_UNRESOLVED / SOURCE_UNAVAILABLE / PENDING_RESERVATION_CONFLICT
```

## Concrete Value Non-decision

Phase22-F records:

```text
position_count_decided=false
cash_ratio_decided=false
exposure_decided=false
position_sizing_decided=false
allocation_decided=false
quantity_decided=false
lot_rounding_decided=false
```

Dynamic Position Count remains Phase22-H. Dynamic Cash / Exposure remains Phase22-I. Position Sizing remains Phase22-J.

## Insufficient Capital Contract

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/constraint_validation.json
```

The artifact distinguishes capital sufficient, capital constrained, cash reserve conflict, exposure conflict, allocation unresolved, source unavailable, and Pending reservation conflict. It does not shrink quantity, compute affordable shares, round lots, or apply fixed cash/exposure fallback.

## Upstream Status Handling

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/upstream_status_validation.json
```

Observed status:

```text
Portfolio Construction: SOURCE_NOT_ELIGIBLE
Portfolio Policy: SOURCE_NOT_ELIGIBLE
Position Management: SOURCE_NOT_ELIGIBLE
Capital Deployment producer_result_status: REVIEW_REQUIRED
runtime_consumer_eligibility: NOT_ELIGIBLE
```

Upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` is propagated to `REVIEW_REQUIRED`, not promoted to `PASS`.

## Date / PIT / Hash / Lineage

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/date_pit_validation.json
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/hash_lineage_validation.json
```

Validated:

- `business_date=2026-07-15`
- generated `feature_date=2026-06-26`
- current cash / exposure / portfolio / pending reservation dates are point-in-time
- no future leakage
- no implicit latest fallback
- no previous-day Capital Deployment copy
- output artifact hash and source hashes

## Failure / Bootstrap

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/bootstrap_validation.json
```

Failure behavior:

- upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` -> `REVIEW_REQUIRED`
- upstream BLOCK/schema/date/hash/missing -> `BLOCK`
- current cash/exposure/portfolio/pending date mismatch -> `BLOCK`
- current cash or exposure unavailable -> `REVIEW_REQUIRED`
- Pending reservation conflict -> `REVIEW_REQUIRED`
- future leakage -> `BLOCK`

Bootstrap does not use previous-day copy, latest fallback, fixed `MAINTAIN PASS`, fixed `CONSERVE PASS`, fixed 20% cash, fixed 80% exposure, or equal allocation fallback.

## Existing Behavior Preservation

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/behavior_preservation.json
```

Preserved:

- existing `max_positions`
- existing `target_investment_ratio`
- existing `cash_buffer`
- existing `max_exposure`
- existing per-position allocation
- existing affordability behavior
- existing lot rounding
- existing quantity calculation
- existing Planning output
- existing Pending output
- existing Submit output

## Runtime Planning Authority Preservation

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/runtime_planning_authority_preservation.json
```

Share quantity, lot rounding, minimum order, order creation, Pending composition, and Submit remain downstream authority. Planning code and config were not changed.

## Fixture / Shadow Consumer

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/fixture_shadow_validation.json
```

Fixture loading allows DRAFT artifacts for schema, posture, constraint, date, hash, and lineage checks only. Production use raises `CapitalDeploymentConsumerError`.

## Produced But Not Consumed

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/produced_not_consumed_validation.json
```

Generated artifact:

```text
.runtime/strategy_artifacts/capital_deployment/2026-07-15/capital_deployment.json
```

The artifact is produced but not consumed by Runtime Planning, Pending, Submit, Approval, Execution, Fill, Ledger, or Current.

## Known Regressions

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/regression_validation.json
```

Known unchanged regressions:

- carryover policy short check -> `10 passed, 1 failed`; same `StopIteration` while finding `morning_ai_planning_pending_pipeline`
- capital deployment policy short check -> same existing sell planning CLI `exit_code=20`

Phase22-F code path is not involved.

## Tests

Executed short tests:

- `python3 -m pytest tests/strategy/test_phase22_f_capital_deployment.py` -> `10 passed`
- Phase22-A / AA / B / C / D / E / F + Capital / Planning / Pending / Submit short suite -> `97 passed, 1 failed known`
- known carryover regression check -> `10 passed, 1 failed unchanged`
- `PYTHONPYCACHEPREFIX=.runtime/pycache_phase22f python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy` -> `PASS`

Long Historical tests were not executed.

## Design Freeze Compliance

Machine-readable validation:

```text
reports/phase22_f_capital_deployment/phase22_f_evidence_20260727/scope_preservation_validation.json
```

Compliant:

- no Production Consumer connection
- no Runtime switch
- no `ACCEPTED` / `ELIGIBLE` promotion
- no Portfolio Construction / Portfolio Policy / Position Management change
- no Planning / Pending / Submit change
- no Dynamic Position Count / Cash / Exposure / Position Sizing implementation
- no concrete target position count, cash ratio, exposure, target weight, JPY allocation, share quantity, lot size, or lot rounding

## Legacy Preservation

Existing Capital Deployment authority, existing policy/config, Planning, Pending, Submit, Historical adapter, status/summarize, scheduler/LaunchAgent, and recovery remain active. No path was removed, revoked, quarantined, or marked delete-ready.

## Blocking Gaps

None for Phase22-F read-only foundation.

## Non-blocking Gaps

- Portfolio Construction remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Portfolio Policy remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Position Management remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Dynamic position count, dynamic cash/exposure, position sizing, concrete allocation, quantity, and lot rounding remain deferred

## Next Gate

Phase22-G entry ready: `YES`, for read-only Capital Deployment foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.
