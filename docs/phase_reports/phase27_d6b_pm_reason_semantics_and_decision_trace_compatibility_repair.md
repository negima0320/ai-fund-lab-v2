# Phase27-D6-B PM Reason Semantics and Decision Trace Compatibility Repair

## 1. Scope

Phase27-D6-B repairs PM reason semantics and decision trace observability for the D5 Expected Edge contract.

```text
Performance Logic Change: false
PM Action Change: false
Score / Threshold Change: false
Quantity Change: false
Runtime Planning / Pending / Submit Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D6B_PM_REASON_SEMANTICS_REPAIR_COMPLETE_D6C_READY
```

Supporting:

```json
{
  "reason_inventory": "COMPLETE",
  "canonical_reason_mapping": "COMPLETE",
  "legacy_alias_compatibility": "PASS",
  "decision_trace": "EXPECTED_EDGE_ALIGNED",
  "action": "UNCHANGED_CONFIRMED",
  "score": "UNCHANGED_CONFIRMED",
  "quantity_intent": "UNCHANGED_CONFIRMED",
  "downstream": "UNCHANGED_CONFIRMED",
  "mode_parity": "CONFIRMED",
  "degression": "PASS",
  "next": "D6-C_APPROVED"
}
```

## 3. Implementation

Legacy reason fields remain readable. D6-B adds canonical reason metadata and Expected Edge trace semantics:

```text
canonical_decision_reason_codes
reason_aliases
expected_edge_semantics
expected_edge_status
expected_edge_contract_status
```

Action, score, thresholds, quantity intent, Runtime Planning, Pending, Submit, Safety, Execution, and Ledger are unchanged.

## 4. Canonical Mapping

| Legacy | Canonical | Action effect |
|---|---|---|
| `profit_retention_break` | `peak_drawdown_profit_retention_risk` | `NONE` |
| `risk_increased_but_trend_not_broken` | `expected_edge_risk_deterioration` or evidenced risk-specific code | `NONE` |
| `positive_expected_edge` | `expected_edge_adequate` | `NONE` |

Unknown reasons are preserved as `UNKNOWN:<legacy_reason>` and are not silently inferred.

## 5. Non-change Proof

PM runtime adapter equivalence:

```text
PM_RUNTIME_ADAPTER_BEHAVIORALLY_EQUIVALENT
canonical_match_count = 8
forbidden_difference_count = 0
trace_failure_count = 0
```

Targeted regression:

```text
100 passed
```

PM adapter authority refresh:

```text
PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_ACCEPTED
```

## 6. Common SoT Updated

```text
docs/02_architecture/position_management_decision_trace_contract.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
```

## 7. Evidence

```text
reports/phase27_d6b_pm_reason_semantics_and_decision_trace_compatibility_repair
```

No fresh-run, resume, 10BD Historical, 100BD Historical, 1-year Historical, long smoke, or long regression was executed.

