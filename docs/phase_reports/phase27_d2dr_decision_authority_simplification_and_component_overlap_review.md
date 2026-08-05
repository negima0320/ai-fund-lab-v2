# Phase27-D2-DR Decision Authority Simplification and Component Overlap Review

## 1. Scope

This is a read-only architecture / implementation review before Phase27-D2-E Runtime Planning connection.

```text
Implementation Change: PROHIBITED_NOT_PERFORMED
Strategy Logic Change: PROHIBITED_NOT_PERFORMED
Runtime Change: PROHIBITED_NOT_PERFORMED
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D2DR_DECISION_AUTHORITY_CONFIRMED_WITH_CLARIFICATIONS_D2E_READY
```

Supporting judgments:

```json
{
  "final_action_authority": "PARTIAL",
  "pm_vs_position_intent": "WRAPPER_RELATION",
  "portfolio_decision": "RESOLUTION_ONLY",
  "sizing": "QUANTITY_ONLY",
  "runtime_planning": "PARTIAL",
  "feature_double_weighting": "THEORETICAL",
  "artifact_set": "JUSTIFIED",
  "d2e_entry": "APPROVED"
}
```

## 3. Main Findings

1. Existing-position final directional action authority is PM in the active system. `position_intent.v1` is a canonical wrapper in D2-A, not a second active action authority.
2. `target_portfolio_decision.v1` is resolution-only in D2-B: it maps PM/position intent into membership/direction/effect evidence with `decision_effect = NONE`.
3. `position_sizing_plan.v1` is quantity-only in D2-D: it emits positive/zero/negative/full-exit delta candidates or matching `*_NOT_SIZED`, with `decision_effect = NONE`.
4. Legacy ADD is no longer executable after D2-C; it is `NON_DECISION_COMPATIBILITY` telemetry with no quantity/Pending/Submit authority.
5. Runtime Planning is intended to be a mapper, but existing code still has PM-action fallback mapping when quantity delta is missing. This is compatible only if D2-E makes canonical quantity-delta precedence explicit and prevents same-row PM fallback from becoming a second action authority.
6. Opportunity, BUY Quality, Market Context, Momentum, and Incremental Eligibility are evidence / modifier components, not D2-A-D final action producers. Feature reuse creates theoretical double-weighting risk, not confirmed active duplicate authority.

## 4. D2-E Entry

```text
APPROVED_WITH_CLARIFICATIONS
```

D2-E may proceed if it preserves this rule:

```text
position_sizing_plan.v1 quantity_delta_candidate
  -> Runtime Planning mapping
```

and does not also let PM fallback or legacy ADD authorize the same action.

## 5. Evidence

Evidence directory:

```text
reports/phase27_d2dr_decision_authority_simplification_and_component_overlap_review
```

Required JSON files were generated there, including `final_action_producer_inventory.json`, `decision_authority_matrix.json`, `feature_double_weighting_audit.json`, `design_gap_inventory.json`, and `d2e_entry_decision.json`.

## 6. Validation

Read-only validation only:

```text
code search / static inspection: PERFORMED
py_compile analysis helper: PASS
JSON validation: PASS
Runtime / Historical / fresh-run: NOT_EXECUTED
```
