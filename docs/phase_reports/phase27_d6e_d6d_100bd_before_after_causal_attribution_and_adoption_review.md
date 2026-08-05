# Phase27-D6-E D6-D 100BD Before/After Causal Attribution and Adoption Review

## 1. Scope

This is a read-only attribution review of existing run-scoped evidence. No PM, Strategy, Runtime, Historical rerun, fresh-run, or resume was executed.

## 2. Primary Judgment

```text
PHASE27_D6E_D6D_100BD_BENEFIT_PARTIALLY_CONFIRMED_ADOPT_WITH_LIMITATIONS
```

Supporting:

```json
{
  "run_comparability": "CONFIRMED_WITH_LIMITATIONS",
  "100bd_completion": "CONFIRMED",
  "close_review": "NON_BLOCKING",
  "target_exit_to_hold": "OBSERVED",
  "single_change_integrity": "PATH_DEPENDENT",
  "causal_benefit": "PARTIAL",
  "risk_regression": "NOT_OBSERVED",
  "d6d_adoption": "APPROVED_WITH_LIMITATIONS",
  "next": "ADD_DESIGN_REVIEW"
}
```

## 3. Run Comparability

```text
COMPARABLE_WITH_LIMITATIONS
```

Both runs cover 100 business days from 2023-01-04 through 2023-05-31 with 1,000,000 JPY initial equity and the same accepted generation / Strategy config hashes. Limitations remain: profile differs (`historical-smoke` vs `historical-extended-smoke`), source commit differs, both historical authority records mark the source dirty, and the After run lacks the baseline-style `performance_report` directory.

## 4. Close REVIEW_REQUIRED

The After close reason is:

```text
strategy_shadow_review_required_non_blocking
NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
```

This is non-blocking for run validity, but it remains an adoption limitation.

## 5. Headline

```json
{
  "final_equity": 81590.0,
  "total_return": 81590.0,
  "return_rate_points": 0.08159,
  "realized_gross_pnl": 52690.00000000001,
  "unrealized_pnl": 28899.999999999996
}
```

The full +81,590 JPY equity delta is not attributed directly to D6-D.

## 6. PM Action Difference

```json
{
  "UNCHANGED": 336,
  "EXIT_TO_HOLD_D6D_TARGET": 2,
  "MISSING_BASELINE": 69,
  "NON_COMPARABLE_CONTEXT": 23,
  "MISSING_AFTER": 3
}
```

Same-context D6-D `EXIT -> HOLD` rows were observed. Broader action differences are classified as path-dependent or non-comparable context, not independent proof of direct rule changes.

## 7. Causal Attribution

```json
{
  "headline_equity_delta": 81590.0,
  "DIRECTLY_TRACEABLE_TO_D6D": 37100.0,
  "DOWNSTREAM_PORTFOLIO_PATH_EFFECT": "PRESENT_BUT_NOT_FULLY_QUANTIFIED",
  "UNRELATED_TRADE_DIFFERENCE": "INSUFFICIENT_EVIDENCE",
  "OPEN_POSITION_VALUATION_DIFFERENCE": 28899.999999999996,
  "EXECUTION_SEQUENCE_DIFFERENCE": "PRESENT",
  "UNEXPLAINED": 44490.0,
  "method": "Direct trace uses same-context EXIT->HOLD rows only; all later cash/selection/campaign changes are path-dependent unless directly tied by run-scoped events."
}
```

Directly traceable benefit is partial. The remaining delta is path-dependent, open-position valuation difference, execution sequence difference, unrelated trade difference, or unexplained under available evidence.

## 8. Adoption

```text
ADOPT_WITH_LIMITATIONS
```

D6-D satisfied the single-change experiment enough for limited adoption: targeted same-context EXIT->HOLD occurred, risk regression was not observed from available run-scoped evidence, and post-hoc outcomes were positive. Adoption is limited because the runs are not fully comparable and the full performance improvement is not isolated to D6-D.

## 9. Evidence

```text
reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review/
```

## 10. Common SoT

D6-D adoption status and known limitations are reflected in:

```text
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
docs/02_architecture/position_management_decision_trace_contract.md
docs/02_architecture/autonomous_ai_operations_architecture.md
```

