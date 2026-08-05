# Phase27-D6-D PM HOLD / EXIT Boundary Minimal Performance Implementation

## 1. Scope

Phase27-D6-D implements the first minimal PM performance improvement: Expected Edge adequate positions are not exited solely because of profit-retention / peak-drawdown risk review.

```text
Runtime Change: false
BUY_NEW Change: false
ADD Change: false
Position Sizing Change: false
Runtime Planning / Pending / Submit Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D6D_PM_HOLD_EXIT_MINIMAL_IMPLEMENTATION_COMPLETE_READY_FOR_100BD
```

Supporting:

```json
{
  "performance_change": "YES",
  "single_change": "CONFIRMED",
  "regression": "PASS",
  "degression": "PASS",
  "100bd": "READY"
}
```

## 3. Implementation

The single implemented boundary is:

```text
profit_retention_break only
AND expected_edge_score > 0 under the existing PM Expected Edge evidence
AND high downside risk is absent
AND existing exit_score high condition is absent
-> HOLD
```

No new threshold, magic number, holding-day rule, profit target, stop loss, or cooldown was added. Existing hard stop, broken trend plus insufficient Expected Edge, risk guard, high downside risk, and exit-score evidence still produce EXIT.

## 4. Before / After

Changed fixture count: `1`

```text
EXIT -> HOLD: 1
```

The changed fixture has positive Expected Edge remaining and no severe full-close risk evidence.

## 5. Regression

```text
PM Unit: 6 passed
Runtime PM Boundary: 1 passed
Targeted Regression: 108 passed
```

## 6. Evidence

```text
reports/phase27_d6d_pm_hold_exit_boundary_minimal_performance_implementation
```

No fresh-run, resume, 100BD, 1-year Historical, or long regression was executed. 100BD is ready for user execution.

