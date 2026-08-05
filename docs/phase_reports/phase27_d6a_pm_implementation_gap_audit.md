# Phase27-D6-A PM Implementation Gap Audit

## 1. Scope

Phase27-D6-A audits the current PM implementation against the Phase27-D5 Expected Edge reasoning contract.

```text
Implementation Change: false
PM Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D6A_PM_IMPLEMENTATION_GAP_CONFIRMED_READY_FOR_MINIMAL_IMPLEMENTATION
```

Supporting:

```json
{
  "current_pm": "ASSESSED",
  "expected_edge": "MAPPED",
  "gap": "CONFIRMED",
  "implementation_scope": "MINIMAL",
  "degression_risk": "ASSESSED",
  "next": "D6-B_APPROVED"
}
```

## 3. Current PM Flow

Current regular PM flow is:

```text
Runtime Current / Opportunity / Feature input
  -> current_holdings_snapshot + PM opportunity context
  -> build_position_feature_frame
  -> score components
  -> classify_position_action
  -> Runtime PM decision artifact and decision trace
  -> Sell Planning / position_intent shadow consumers
```

The existing PM implementation primarily produces existing-position `ADD`, `HOLD`, `REDUCE`, and `EXIT`. `BUY_NEW` is not produced by the PM regular path; BUY_NEW candidates remain shadow unresolved in `position_intent`.

## 4. Expected Edge Mapping

Used:

- Trend
- Rank
- Risk
- Profit
- Current position state

Not explicitly used in the current PM regular path:

- BUY Quality
- Market Context
- Portfolio Fit
- Corporate Event

The largest D5 gaps are semantic rather than threshold-based: isolated indicators are used directly in reason/action branches, while D5 wants them framed as Expected Edge evidence.

## 5. Reason Code Gaps

| Reason code | Gap classification | D6-A judgment |
|---|---|---|
| `trend_continuation` | `NO_CHANGE` | Aligned as continuation evidence. |
| `positive_expected_edge` | `REASON_UPDATE` | Raw positive score wording is too broad for D5 Expected Edge adequacy. |
| `downside_risk_contained` | `NO_CHANGE` | Aligned as risk-contained evidence. |
| `risk_increased_but_trend_not_broken` | `RENAME` | Broad fallback should split actual risk/weakening cause. |
| `peak_drawdown_warning` | `NO_CHANGE` | Aligned as risk/weakening evidence. |
| `trend_and_opportunity_broken` | `NO_CHANGE` | Aligned as Expected Edge deterioration evidence. |
| `profit_retention_break` | `RENAME` | Should be peak-drawdown/profit-retention risk, not profit-taking. |
| `hard_stop_current_return` | `NO_CHANGE` | Aligned as loss-containment evidence. |

## 6. Action Gaps

- `BUY_NEW`: outside current PM regular path; no PM implementation change unit for D6-B unless BUY_NEW PM scope is explicitly opened later.
- `ADD`: partial D5 gap. Current trigger uses `add_score`, `current_return > 0`, `buy_rank <= 5`, and low downside risk, but does not explicitly prove Expected Edge improvement or incremental investment value.
- `HOLD`: mostly compatible, but reason language should express Expected Edge adequacy instead of isolated positive score.
- `REDUCE`: conceptually aligned as risk/weakening while campaign remains alive; broad fallback reason needs splitting.
- `EXIT`: partly aligned; `profit_retention_break` naming and some exit summary wording need D5-compatible risk/Expected Edge semantics.

## 7. Minimal Implementation Units

1. Reason rename / alias compatibility for `profit_retention_break` and `risk_increased_but_trend_not_broken`.
2. Reason summary update so PM trace explains Expected Edge adequacy/deterioration.
3. ADD evidence input update for Expected Edge improvement and incremental investment value.
4. Evidence-first input expansion for Quality, Market, Portfolio Fit, and Corporate Event.

The first two are the minimal D6-B-safe units because they can preserve thresholds and action outcomes.

## 8. Impact

Primary files:

```text
src/ai_fund_lab_v2/position_management_ai/inference.py
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
src/ai_fund_lab_v2/strategy/position_intent.py
```

Main consumers:

```text
position_management_decisions.json
position_management_decision_trace.json
Sell Planning
position_intent shadow producer
target_portfolio_decision / position_sizing_plan downstream contracts
```

## 9. Evidence

```text
reports/phase27_d6a_pm_implementation_gap_audit
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d6a_generate_pm_implementation_gap_audit.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Position Sizing, Historical, fresh-run, resume, 100BD, or long regression was executed.

