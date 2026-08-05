# Phase27-D3 PM Momentum Follow Performance Strategy Design Review

## 1. Scope

Phase27-D3 freezes the PM Momentum Follow performance philosophy and integrates it into common Architecture SoT.

```text
Implementation Change: false
PM Logic Change: false
Strategy Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D3_PM_PERFORMANCE_PHILOSOPHY_FROZEN_COMMON_SOT_UPDATED
```

Supporting:

```json
{
  "performance_philosophy": "FROZEN",
  "pm_responsibility": "CONFIRMED",
  "component_responsibility": "CONFIRMED",
  "common_sot": "UPDATED",
  "implementation_entry": "READY_FOR_PM_IMPROVEMENT"
}
```

## 3. Frozen Philosophy

- BUY enters symbols with upward-trend entry or sufficient forward expected value.
- HOLD is active continuation while upward trend and expected value remain valid.
- EXIT is for trend end, expected-value deterioration, signal break, severe risk worsening, or Safety/Portfolio necessity.
- ADD is considered only when the held symbol remains strongest, trend continues, and incremental value exists.
- REDUCE remains a reviewed intermediate risk/weakening/partial-rotation action, not a profit-taking philosophy.
- Profit-taking is not adopted as an independent action philosophy.
- Cash is an outcome, not a forced deployment target.
- Performance improvement must not add duplicate action authority.

## 4. Responsibility

PM is the Strategy Action Authority for existing-position `ADD`, `HOLD`, `REDUCE`, and `EXIT`.

Opportunity, BUY Quality, Market Context, Momentum Evidence, and Incremental Eligibility are Evidence Producers. Portfolio Construction resolves target membership/weight; Position Sizing resolves quantity delta; Runtime Planning maps quantity delta to runtime action.

## 5. Common SoT Updated

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
```

## 6. Open Questions

No numeric thresholds were fixed. Continuation, Weakening, Broken, ADD boundary, REDUCE boundary, EXIT boundary, and Trend evaluation method remain controlled design questions.

## 7. Evidence

```text
reports/phase27_d3_pm_momentum_follow_performance_strategy_design_review
```

## 8. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d3_generate_pm_performance_philosophy_review.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.

