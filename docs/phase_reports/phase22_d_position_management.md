# Phase22-D Position Management

## Primary Judgment

```text
PHASE22_D_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Position Management foundation was implemented as a production-common, read-only Strategy artifact producer. The artifact is generated as `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` because upstream Market Context, Corporate Event, and Portfolio Policy artifacts remain `REVIEW_REQUIRED / NOT_ELIGIBLE`.

Phase22-E entry ready: `YES`, for read-only Position Management foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## 1. Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- Phase22-A / AA / B / C reports, schemas, code, and evidence

## 2. Existing PM Producer Inventory

Machine-readable inventory:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/existing_pm_inventory.json
```

Current active Position Management behavior remains in existing runtime PM and planning paths. Phase22-D does not replace the existing producer, adapter, Pending, Submit, Sell Planning, ADD Planning, or broker-facing logic.

## 3. Current Authority Inventory

Machine-readable inventory:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/current_authority_inventory.json
```

Current authority remains:

- position-level PM intent: existing runtime Position Management
- REDUCE / EXIT quantity: Sell Planning and downstream order authority
- ADD quantity / sizing: ADD Planning, Capital Deployment, and downstream authority
- Pending / Submit / execution: existing runtime v2 pipelines

Phase22-D only emits a read-only Strategy artifact and keeps `production_consumer_connected=false`.

## 4. PM Feature Contract Inventory

Machine-readable inventory:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/pm_feature_contract_inventory.json
```

The artifact records PM technical feature metadata and source hashes. It does not introduce a new model, scaler, generation, feature selection, or unscaled fallback.

## 5. PM Lifecycle / Distribution Inventory

Machine-readable inventory:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/pm_lifecycle_distribution_inventory.json
```

Lifecycle evidence is included as a referenced source summary. Phase22-D does not decide minimum holding periods, cooldowns, forced hold behavior, or campaign lifecycle policy.

## 6. Direct Reference Inventory

Machine-readable inventory:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/direct_reference_inventory.json
```

Direct references were inventoried across Position Management, ADD / Sell Planning, runtime authority, Strategy artifacts, and tests. No runtime consumer wiring was changed.

## 7. Position Management Responsibility

Implemented producer:

```text
src/ai_fund_lab_v2/strategy/position_management.py
schemas/strategy/position_management.schema.json
```

Phase22-D responsibility is position-level intent only:

```text
HOLD / ADD / REDUCE / EXIT
```

The artifact also carries intensity, confidence, reason codes, uncertainty, lifecycle references, upstream references, Accepted Generation references, model/scaler references, and hash lineage.

## 8. Input Contract

Implemented producer inputs:

- `business_date`
- position identity and current PM shadow decision rows
- current price / return and technical feature metadata through source summaries
- Opportunity summary reference
- Market Context artifact metadata
- Corporate Event artifact metadata
- Portfolio Policy artifact metadata
- position lifecycle evidence
- Accepted Generation / model / scaler references
- source paths and source hashes

Forbidden inputs remain unused: future return, future regime, future event, backtest result, test pass/fail, accepted/rejected mimicry, broker quantity, order quantity, and runtime execution result.

## 9. Schema

Schema version:

```text
position_management.v1
```

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/schema_validation.json
```

The schema enforces `DRAFT`, `NOT_ELIGIBLE`, no production consumer connection, no runtime switch, legacy authority still active, and no quantity fields in position rows.

## 10. Action / Intensity Taxonomy

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/action_intensity_validation.json
```

Action taxonomy is exactly:

```text
HOLD
ADD
REDUCE
EXIT
```

Intensity is separate from action:

```text
NONE
LIGHT
MEDIUM
STRONG
UNRESOLVED
```

`REDUCE` expresses intent and intensity only. `EXIT` expresses full-exit intent only.

## 11. Minimum Holding / Cooldown Non-decision

Phase22-D records:

```text
minimum_holding_decided=false
cooldown_decided=false
```

Minimum holding and cooldown policy remain deferred to Phase22-K.

## 12. Upstream Status Handling

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/upstream_status_validation.json
```

Observed status:

```text
Market Context: SOURCE_NOT_ELIGIBLE
Corporate Event: SOURCE_NOT_ELIGIBLE
Portfolio Policy: SOURCE_NOT_ELIGIBLE
Position Management producer_result_status: REVIEW_REQUIRED
runtime_consumer_eligibility: NOT_ELIGIBLE
```

Upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` is read as shadow evidence only and is propagated to `REVIEW_REQUIRED`. It is not promoted to `PASS`.

## 13. Accepted Generation / Model / Scaler Contract

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/generation_binding_validation.json
```

Validated:

- model and scaler share the same accepted generation
- model hash matches referenced model file
- scaler hash matches referenced scaler file
- generation status is explicit
- unscaled fallback is forbidden
- no new generation, model, or scaler is created

## 14. Date / PIT

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/date_pit_validation.json
```

Validated:

- requested `business_date=2026-07-15`
- generated `feature_date=2026-06-26`
- `feature_date <= business_date`
- no future leakage
- no implicit latest fallback
- no previous-day PM artifact copy

## 15. Hash / Lineage

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/hash_lineage_validation.json
```

The artifact records source hashes for lifecycle, technical features, Opportunity summary, Accepted Generation, model, and scaler. The output artifact hash is stable and excludes its own `artifact_hash` field from hash calculation.

## 16. Failure Contract

Failure behavior:

- upstream `REVIEW_REQUIRED / NOT_ELIGIBLE` -> Position Management `REVIEW_REQUIRED`
- upstream schema/date/hash/missing/block -> Position Management `BLOCK`
- generation mismatch, model hash mismatch, scaler hash mismatch, or unscaled fallback -> `BLOCK`
- future feature or lifecycle date -> `BLOCK`
- missing PM shadow positions -> no fixed HOLD/PASS fallback

## 17. Bootstrap Contract

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/bootstrap_validation.json
```

Bootstrap does not emit fixed `HOLD` / `PASS`, does not copy previous-day PM artifacts, and does not use implicit latest fallback.

## 18. Existing PM Behavior Preservation

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/pm_behavior_preservation.json
```

Existing PM shadow rows are preserved into the Strategy artifact as read-only evidence. Phase22-D does not change PM action, PM intensity, PM confidence, PM reason code, PM feature vector, model, scaler, Pending, Submit, ADD Planning, or Sell Planning behavior.

## 19. REDUCE / EXIT Quantity Authority Preservation

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/quantity_authority_preservation.json
```

The artifact records:

```text
quantity_decided=false
```

Forbidden quantity fields are rejected. `REDUCE` remains intent/intensity only, and `EXIT` remains full-exit intent only. Actual sell quantity remains downstream Sell Planning / order authority.

## 20. Fixture / Shadow Consumer

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/fixture_shadow_validation.json
```

Fixture loading allows DRAFT artifacts for schema/status/hash/lineage checks only. Production use raises `PositionManagementConsumerError`.

## 21. Produced But Not Consumed

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/produced_not_consumed_validation.json
```

Generated artifact:

```text
.runtime/strategy_artifacts/position_management/2026-07-15/position_management.json
```

The artifact is produced but not consumed by runtime decision-making, Pending, Submit, order sizing, execution, fill, ledger, or current-state authority.

## 22. Known Regressions / Tests

Machine-readable validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/regression_validation.json
reports/phase22_d_position_management/phase22_d_position_management.json
```

Executed short tests:

- `python3 -m pytest tests/strategy/test_phase22_d_position_management.py` -> `11 passed`
- Phase22-A / AA / B / C / D + PM adapter + PM generation short suite -> `53 passed`
- `PYTHONPYCACHEPREFIX=.runtime/pycache_phase22d python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy` -> `PASS`

Known unchanged regressions:

- carryover policy short check -> `10 passed, 1 failed`; same `StopIteration` while finding `morning_ai_planning_pending_pipeline`
- capital deployment policy short check -> `8 passed, 1 failed`; same existing sell planning CLI `exit_code=20`

Long Historical tests were not executed.

## 23. Design Freeze / Next Gate

Machine-readable scope validation:

```text
reports/phase22_d_position_management/phase22_d_evidence_20260727/scope_preservation_validation.json
```

Design Freeze compliance:

- no runtime switch
- no production consumer connection
- no `ACCEPTED` or `ELIGIBLE` promotion
- no legacy removal, revoke, quarantine, or authority reassignment
- no new model, scaler, generation, or unscaled fallback
- no quantity decision in Position Management artifact
- no minimum holding or cooldown decision

Blocking gaps: none for Phase22-D read-only foundation.

Non-blocking gaps:

- Market Context remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Corporate Event remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- Portfolio Policy remains `REVIEW_REQUIRED / NOT_ELIGIBLE`
- regime/event-aware PM behavior, minimum holding, and cooldown remain deferred to Phase22-K

Phase22-E entry ready: `YES`, for read-only PM foundation only.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.
