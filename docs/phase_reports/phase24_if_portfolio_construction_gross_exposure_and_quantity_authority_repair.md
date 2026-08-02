# Phase24-IF Portfolio Construction Gross Exposure and Quantity Authority Repair

## 1. Primary Judgment

`PHASE24_IF_PORTFOLIO_CONSTRUCTION_GROSS_EXPOSURE_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED`

## 2. Implementation Summary

Portfolio Construction now evaluates six-decimal rounded target-weight sums with a selected-member-count-scaled rounding tolerance.

```text
tolerance = max(0.000001, selected_member_count * 0.000001 / 2)
```

For the target case:

```text
selected_member_count = 6
tolerance = 0.000003
overflow = 0.000002
```

Therefore the rounding-only overflow is not classified as `total_target_weight_above_target_gross_exposure`.

Runtime Planning now distinguishes quantity absence caused by upstream Portfolio Construction BLOCK:

```text
quantity_not_produced_due_to_upstream_block
```

It does not emit top-level `review_required_quantity_authority:*` for this upstream-only condition.

## 3. Preserved Boundaries

No Strategy performance policy was changed. No candidate was removed. No target gross exposure, max exposure, max positions, cash buffer, Ranking, Eligibility, PM, Position Sizing policy, Submit Guard, or Safety Guard was changed.

Genuine gross exposure overflow beyond the rounding tolerance remains fail-closed.

## 4. Regression

Short validation passed:

```text
114 passed in 3.43s
```

Runtime fresh-run, resume, and long historical test were not executed.

## 5. Operator Rerun

Operator Runtime rerun is required to confirm the historical `2023-06-14` path.
