# Phase30-AK9R27A - Pending Review Scope Contract / Consumer Interface Compatibility Audit

## Primary Judgment

`CENTRAL_CONTRACT_INTERFACE_COMPATIBLE_WITH_ADAPTERS_AND_SHADOW_FIRST_MIGRATION`

AK9R26で確認した `BUY_ITEM_SCOPED_REVIEW` / executable subset / item-vs-batch semantics の重複について、中央contract実装前のREAD-ONLY互換性監査を行った。

結論として、中央contract化は可能。ただし、いきなり置換してよい状態ではない。Data Readiness、Historical Safety、Execution、Current Valuation / next-day lifecycle は、Pending scopeだけでは足りず、consumer固有のtemporal / submit / execution evidenceを合成するthin adapterが必要。

## Current Pending Field Inventory

`CURRENT_PENDING_FIELD_INVENTORY_COMPLETE = YES`

作成:

```text
reports/phase_reports/phase30_ak9r27a/current_pending_field_inventory.json
```

Inventory対象は、`PendingOrderPlan` / `PendingOrderItem` / approval / consume / safety_context の現行field。中央contractに入れるべきfieldは、item setとreview scopeの意味に限定する。`reserved_notional`、`estimated_amount`、`quantity` は参照はされるが、Pending review-scope contractの所有物ではない。

## Consumer Interface Matrix

`CONSUMER_INTERFACE_MATRIX_COMPLETE = YES`

作成:

```text
reports/phase_reports/phase30_ak9r27a/consumer_interface_matrix.json
```

監査対象consumer:

```text
Data Readiness
Historical Safety
Sell Planning
Pending composition
Pending consume
Submit Data Readiness
Submit pipeline
Submit guard
Execution
Current Valuation
Current State
next-day lifecycle/orchestration
```

現在のlocal recomputationの中心は以下:

```text
data_readiness._pending_buy_item_scoped_sell_continuation_ready
data_readiness._pending_post_submit_residual_buy_review_current_valuation_ready
pending.consume._buy_item_scoped_review_executable_subset_authorized
submit.pipeline._buy_item_scoped_review_executable_subset_authorized
submit.guards._buy_item_scoped_review_executable_subset_authorized
pending.composition._is_buy_item_scoped_review_sell_continuation_pending
pending.lifecycle_runner._stale_partial_submitted_buy_review_expiration_authority
execution.readonly_pipeline._load_submit_no_action_authority
```

## Field Dependency Classification

作成:

```text
reports/phase_reports/phase30_ak9r27a/field_dependency_classification.json
```

```text
DUPLICATE_SEMANTIC_FIELD_DEPENDENCY_COUNT = 12
LEGACY_COMPATIBILITY_FIELD_DEPENDENCY_COUNT = 5
```

重複semantic dependencyは、approved/review set derivation、reviewed SELL fail-closed、aggregate cash batch escalation、cash-like reason class、post-submit residual reviewed BUY shapeなど。

Legacy compatibility dependencyは、`plan_overall_status`、`batch_submit_status`、`review_scope_reason`、`item_review_reason`、`submit_constraints.expires_at`。中央contract移行中は診断互換として残すべき。

## Proposed Contract

作成:

```text
reports/phase_reports/phase30_ak9r27a/proposed_pending_review_scope_contract.json
```

`CONTRACT_FIELD_COUNT = 22`

Minimal contract:

```text
contract_id
contract_version
source_pending_plan_id
authority_provenance
structural_validity
malformed_reasons
lifecycle_state
review_scope
target_session_date
plan_created_date
executable_item_ids
executable_buy_item_ids
executable_sell_item_ids
reviewed_item_ids
reviewed_buy_item_ids
reviewed_sell_item_ids
terminal_item_ids
expired_item_ids
approved_review_sets_disjoint
batch_blocked
batch_block_reason
partial_submit_allowed
sell_continuation_allowed
reviewed_items_must_not_submit
```

非authority:

```text
cash arithmetic
reserved-notional arithmetic
quantity recomputation
Strategy cap recomputation
broker feasibility
valuation price
```

## Consumer Coverage

作成:

```text
reports/phase_reports/phase30_ak9r27a/contract_consumer_coverage_matrix.json
```

```text
CONSUMER_FULL_COVERAGE_COUNT = 8
CONSUMER_PARTIAL_COVERAGE_COUNT = 4
CONSUMER_INSUFFICIENT_COVERAGE_COUNT = 0
```

Partial coverage consumers:

```text
Data Readiness
Historical Safety
Submit Data Readiness
Current Valuation
```

これらは中央contractでPending scopeを受け取れるが、Historical Safety binding、cash authority、submit/execution terminal evidenceはconsumer固有inputとして残す。

## Local Migration Feasibility

作成:

```text
reports/phase_reports/phase30_ak9r27a/local_semantic_migration_inventory.json
```

```text
SAFE_DIRECT_REPLACEMENT_COUNT = 4
ADAPTER_REQUIRED_COUNT = 4
LEGITIMATE_VALIDATION_KEEP_COUNT = 3
SCHEMA_PAYLOAD_BLOCKER_COUNT = 0
```

Safe direct replacement:

```text
Pending consume executable-subset predicate
Submit pipeline executable-subset predicate
Submit guard executable-subset predicate
Pending composition sell-continuation predicate
```

Adapter required:

```text
Data Readiness pending readiness
Historical Safety temporal authority
Execution no-submission authority
Current Valuation / next-day lifecycle residual reviewed BUY
```

## Reason Code Coupling

作成:

```text
reports/phase_reports/phase30_ak9r27a/reason_code_consumer_dependency_matrix.json
```

`FRAGILE_REASON_STRING_COUPLING_COUNT = 9`

Critical migration riskは、exact stringでsemanticを推測している箇所。中央contractでは、`aggregate_cash` や `*_missing` のような文字列そのものではなく、typed reason classを渡す必要がある。

## Lifecycle / Item Set / Temporal

```text
TOP_LEVEL_STATE_ONLY_CONSUMER_COUNT = 2
TOP_LEVEL_STATE_WITH_SCOPE_CONSUMER_COUNT = 8
TOP_LEVEL_STATE_MISINTERPRETATION_RISK_COUNT = 5
ITEM_SET_DERIVATION_CONFORMANCE_GAP_COUNT = 4
TEMPORAL_FIELD_SEMANTIC_AMBIGUITY_COUNT = 3
```

Top-level `REVIEW_REQUIRED` は単独では意味が不足している。合法なpartial submit、batch failure、reviewed SELL fail-closed、post-submit residual reviewが同じtop-level stateを共有するため、central contractは必ず `review_scope` と side-specific item sets を同時に返す必要がある。

Temporal ownership:

```text
target_session_date = Pending scope contractに含める
plan_created_date = Pending scope contractに含める
business_date = stage consumer input
safety_business_date = Historical Safety owner
execution date = Submit / Execution owner
approval_expires_at = Pending lifecycle owner
```

## Cash / Quantity Boundary

```text
PENDING_SCOPE_VS_CASH_AUTHORITY_BOUNDARY =
Pending review scope contract may expose item membership and typed cash-like review class,
but must not compute cash capacity, buying power, or reserved-notional feasibility.

CASH_SEMANTIC_LEAKAGE_INTO_PENDING_SCOPE_COUNT = 3
```

```text
PENDING_SCOPE_VS_QUANTITY_AUTHORITY_BOUNDARY =
Pending review scope contract may identify executable item ids,
but must not compute quantity; PC/PS/Pending item quantity remains canonical.

QUANTITY_RECOMPUTATION_REQUIRED_BY_CENTRAL_CONTRACT = NO
```

## Side Combination Coverage

```text
SIDE_COMBINATION_UNREPRESENTABLE_COUNT = 0
```

Covered combinations:

| Case | Representation |
| --- | --- |
| reviewed BUY + approved SELL | `executable_sell_item_ids` + `reviewed_buy_item_ids` |
| approved BUY + reviewed BUY | `executable_buy_item_ids` + `reviewed_buy_item_ids` |
| reviewed SELL | `reviewed_sell_item_ids` + `batch_blocked=true` |
| approved BUY + approved SELL + reviewed BUY | executable BUY/SELL ids + reviewed BUY ids |
| no BUY / SELL-only | executable SELL ids only |
| BUY-only | executable BUY ids or reviewed BUY ids only |

## Post-Submit Consumers

```text
POST_SUBMIT_CONSUMER_INTERFACE_COMPLETE = YES
POST_SUBMIT_CONSUMER_GAP_COUNT = 2
```

Gaps:

1. Current Valuation / readiness needs terminal executable item evidence outside Pending scope.
2. next-day lifecycle expiration needs submit/execution no-fill evidence before expiring residual reviewed BUY.

These are adapter requirements, not contract blockers.

## Real Runtime Payload Evidence

作成:

```text
reports/phase_reports/phase30_ak9r27a/real_runtime_payload_matrix.json
```

Inspected existing artifacts from:

```text
runtime-test-historical-extended-smoke-20260817T131147580500Z
2022-09-07
```

Observed shapes:

```text
morning: pending_slot_status = CONSUMED, data_readiness_status = READY
sell_planning: pending_slot_status = REVIEW_REQUIRED, data_readiness_status = READY
submit: pending_slot_status = REVIEW_REQUIRED, data_readiness_status = REVIEW_REQUIRED, exit_code = 20
AK9R24 shape: approved BUY + approved SELL + reviewed BUY, reviewed SELL = 0
```

The run evidence confirms that consumer interfaces do not all receive a fully materialized pending payload in their own manifest; some receive path references or summarized status. The central contract therefore needs to be attached either to Pending artifacts or emitted as an evidence artifact that consumers can load consistently.

## Shadow Compatibility

作成:

```text
reports/phase_reports/phase30_ak9r27a/shadow_compatibility_results.json
```

```text
SHADOW_COMPATIBILITY_CASE_COUNT = 8
SHADOW_COMPATIBILITY_MATCH_COUNT = 7
SHADOW_COMPATIBILITY_MISMATCH_COUNT = 1
```

Only mismatch:

```text
next-day residual reviewed BUY
```

Reason: central Pending scope can identify residual reviewed BUY, but must not infer submit/fill absence. This requires a lifecycle/current-valuation adapter that combines central scope with Submit and Execution evidence.

## Migration Risks

作成:

```text
reports/phase_reports/phase30_ak9r27a/migration_risk_inventory.json
```

```text
MIGRATION_CRITICAL_RISK_COUNT = 1
MIGRATION_HIGH_RISK_COUNT = 6
MIGRATION_MEDIUM_RISK_COUNT = 6
MIGRATION_LOW_RISK_COUNT = 3
```

Critical risk:

```text
reviewed BUY accidentally submitted
```

Mitigation: `reviewed_items_must_not_submit` invariant, old-vs-new shadow parity, and real Submit orchestration sentinel before removing duplicate predicates.

## Recommended Migration Sequence

```text
RECOMMENDED_MIGRATION_SEQUENCE = [
  "Define central contract producer without replacing existing consumers",
  "Add shadow evaluation for all eight compatibility cases",
  "Compare old/local predicates vs canonical result in evidence only",
  "Add adapters for Data Readiness, Historical Safety, Execution, Current Valuation / next-day lifecycle",
  "Migrate low-risk direct consumers: Pending consume, Submit guard, Submit pipeline evidence",
  "Migrate Pending composition and Sell Planning",
  "Migrate Data Readiness / Submit Data Readiness with Historical Safety adapter",
  "Add real-orchestration regression spanning Submit -> Execution -> Consume -> next-day Current Valuation",
  "Remove duplicate local predicates last after parity evidence passes"
]
```

## Contract Readiness Gate

```text
CENTRAL_CONTRACT_IMPLEMENTATION_READY = YES
CENTRAL_CONTRACT_IMPLEMENTATION_BLOCKERS = []
KNOWN_INTERFACE_OR_CONTRACT_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = NO
```

Implementation is ready only under the audited migration sequence. The first implementation task must be shadow-first and adapter-aware; direct wholesale replacement is not authorized by this audit.

## Required Final Judgments

```text
CURRENT_PENDING_FIELD_INVENTORY_COMPLETE = YES
CONSUMER_INTERFACE_MATRIX_COMPLETE = YES
DUPLICATE_SEMANTIC_FIELD_DEPENDENCY_COUNT = 12
LEGACY_COMPATIBILITY_FIELD_DEPENDENCY_COUNT = 5
CONTRACT_FIELD_COUNT = 22

CONSUMER_FULL_COVERAGE_COUNT = 8
CONSUMER_PARTIAL_COVERAGE_COUNT = 4
CONSUMER_INSUFFICIENT_COVERAGE_COUNT = 0

SAFE_DIRECT_REPLACEMENT_COUNT = 4
ADAPTER_REQUIRED_COUNT = 4
LEGITIMATE_VALIDATION_KEEP_COUNT = 3
SCHEMA_PAYLOAD_BLOCKER_COUNT = 0

FRAGILE_REASON_STRING_COUPLING_COUNT = 9
TOP_LEVEL_STATE_ONLY_CONSUMER_COUNT = 2
TOP_LEVEL_STATE_WITH_SCOPE_CONSUMER_COUNT = 8
TOP_LEVEL_STATE_MISINTERPRETATION_RISK_COUNT = 5

ITEM_SET_DERIVATION_CONFORMANCE_GAP_COUNT = 4
TEMPORAL_FIELD_SEMANTIC_AMBIGUITY_COUNT = 3
CASH_SEMANTIC_LEAKAGE_INTO_PENDING_SCOPE_COUNT = 3
QUANTITY_RECOMPUTATION_REQUIRED_BY_CENTRAL_CONTRACT = NO
SIDE_COMBINATION_UNREPRESENTABLE_COUNT = 0

POST_SUBMIT_CONSUMER_INTERFACE_COMPLETE = YES
POST_SUBMIT_CONSUMER_GAP_COUNT = 2

SHADOW_COMPATIBILITY_CASE_COUNT = 8
SHADOW_COMPATIBILITY_MATCH_COUNT = 7
SHADOW_COMPATIBILITY_MISMATCH_COUNT = 1

MIGRATION_CRITICAL_RISK_COUNT = 1
MIGRATION_HIGH_RISK_COUNT = 6
MIGRATION_MEDIUM_RISK_COUNT = 6
MIGRATION_LOW_RISK_COUNT = 3

CENTRAL_CONTRACT_IMPLEMENTATION_READY = YES
CENTRAL_CONTRACT_IMPLEMENTATION_BLOCKERS = []
KNOWN_INTERFACE_OR_CONTRACT_DEFECT = YES
IMPLEMENTATION_REPAIR_REQUIRED = NO
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
FRESH_HISTORICAL_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Implementation Authorization

`NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK9R27A`

## Recommended Next Task

`Phase30-AK9R27 - Central Pending Review Scope Authority Contract Repair`
