# Phase27-D5 PM Expected Edge Reasoning Contract and Action Boundary Design

## 1. Scope

Phase27-D5 freezes the PM reasoning contract that converts Expected Edge into Strategy action.

```text
Implementation Change: false
PM Logic Change: false
Strategy Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D5_PM_REASONING_CONTRACT_FROZEN_COMMON_SOT_UPDATED
```

Supporting:

```json
{
  "pm_reason_contract": "FROZEN",
  "action_boundary": "FROZEN",
  "reason_contract": "UPDATED",
  "implementation_entry": "READY_FOR_PM_IMPLEMENTATION"
}
```

## 3. PM Reason Contract

PM evaluates Expected Edge only.

Trend, Rank, Profit, Market Context, and BUY Quality are Expected Edge evidence. They are not direct action producers.

```text
Expected Edge Evidence
  -> PM Expected Edge Reasoning
  -> BUY_NEW / ADD / HOLD / REDUCE / EXIT
```

Reason codes explain PM Expected Edge reasoning. They do not create separate Action Authority.

## 4. Action Boundaries

- `BUY_NEW`: no-position Expected Edge is sufficiently high and entry evidence is coherent.
- `HOLD`: Expected Edge remains adequate; slight deterioration remains HOLD unless risk/reward meaningfully weakens.
- `ADD`: Expected Edge improves, the existing holding remains a strongest opportunity, and incremental investment value exists.
- `REDUCE`: Expected Edge or risk/reward weakens enough to trim exposure while preserving campaign optionality.
- `EXIT`: Expected Edge becomes insufficient, continuation breaks, or risk/Safety requires full close.

No numeric threshold is fixed.

## 5. Reason Code Review

| Reason code | Classification | Interpretation |
|---|---|---|
| `trend_continuation` | KEEP | Continuation evidence. |
| `positive_expected_edge` | REVIEW | Compatibility positive-edge code; should become more explicit in future reasoning. |
| `downside_risk_contained` | KEEP | Risk-contained evidence. |
| `risk_increased_but_trend_not_broken` | RENAME | Broad REDUCE fallback; should split into explicit causes. |
| `peak_drawdown_warning` | KEEP | Risk Review / weakening evidence. |
| `trend_and_opportunity_broken` | KEEP | Expected Edge deterioration and continuation break. |
| `profit_retention_break` | RENAME | Peak-drawdown/profit-retention risk, not simple profit-taking. |
| `hard_stop_current_return` | KEEP | Loss-containment / severe risk evidence. |

## 6. Profit Review

Profit is not a Primary Expected Edge decision input and does not directly produce action.

Profit may be Supporting Evidence and Risk Review evidence for embedded gain risk, drawdown-from-peak, changed risk/reward, or concentration after profit expansion.

## 7. HOLD / REDUCE / EXIT Boundary

If Expected Edge slightly declines, default design is not immediate EXIT. HOLD remains valid while the campaign is still attractive enough. REDUCE is the intermediate action when risk/reward weakens enough to trim exposure but campaign optionality remains. EXIT is for insufficient Expected Edge, broken continuation, full-close risk, or Safety.

## 8. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
```

## 9. Evidence

```text
reports/phase27_d5_pm_expected_edge_reasoning_contract_design
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d5_generate_pm_expected_edge_reasoning_contract.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Position Sizing, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.

