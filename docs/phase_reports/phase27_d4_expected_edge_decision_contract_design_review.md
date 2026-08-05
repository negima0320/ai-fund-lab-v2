# Phase27-D4 Expected Edge Decision Contract Design Review

## 1. Scope

Phase27-D4 freezes the Expected Edge decision contract and integrates it into common Architecture SoT.

```text
Implementation Change: false
PM Logic Change: false
Strategy Logic Change: false
Runtime Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D4_EXPECTED_EDGE_DECISION_CONTRACT_FROZEN_COMMON_SOT_UPDATED
```

Supporting:

```json
{
  "expected_edge_philosophy": "FROZEN",
  "pm_contract": "UPDATED",
  "common_sot": "UPDATED",
  "implementation_entry": "READY_FOR_PM_REASONING_IMPROVEMENT"
}
```

## 3. Expected Edge Definition

Expected Edge means whether forward-looking expected value remains sufficiently attractive from Point-in-Time evidence.

It is not profit rate itself, Trend alone, Rank alone, BUY Quality alone, Market Context alone, or cash availability.

## 4. Evidence Relationship

Trend, Opportunity Rank, BUY Quality, Market Context, Portfolio Fit, Execution Feasibility, and profit/risk evidence are inputs to Expected Edge review.

Trend is evidence, not Expected Edge itself. Rank is evidence, not direct BUY/ADD/EXIT authority. BUY Quality is evidence, not Action Authority.

## 5. PM Contract

PM evaluates Expected Edge and decides:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
```

Other components emit evidence, constraints, target portfolio decisions, quantity deltas, or runtime mappings. They do not emit Strategy action authority.

## 6. Profit Position Review

Profit alone does not create EXIT or REDUCE.

Large embedded gain, concentration after profit expansion, volatility/gap risk, drawdown-from-peak risk, or changed risk/reward may trigger Risk Review. No numeric Profit Review threshold is fixed in D4.

## 7. Common SoT Updated

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```

## 8. Open Questions

Expected Edge numeric representation, threshold, Trend formula, Profit Review conditions, ADD boundary, REDUCE boundary, and EXIT boundary remain open for D5 or later.

## 9. Evidence

```text
reports/phase27_d4_expected_edge_decision_contract_design_review
```

## 10. Validation

```text
python3 -m py_compile tools/phase27_analysis/phase27_d4_generate_expected_edge_contract_review.py
PASS

JSON validation for all generated evidence files
PASS
```

No Runtime, Strategy, PM, Position Sizing, Historical, fresh-run, resume, 10BD, 100BD, or long regression was executed.

