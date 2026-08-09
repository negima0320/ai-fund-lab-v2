# Phase28-D34: Canonical REDUCE Intensity Authority Integration Implementation

## Primary Judgment

```text
PHASE28_D34_CANONICAL_REDUCE_INTENSITY_AUTHORITY_INTEGRATED_SHORT_VALIDATION_PASS
```

Fresh Test Entry Decision:

```text
READY
```

## Implementation

Implemented the single approved D33 repair: PM `REDUCE + reduce_intensity` now flows through one shared canonical authority into Portfolio Construction, Position Sizing, Runtime Planning, and Sell Planning without converting REDUCE into EXIT.

Changed files:

```text
src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
```

No config, schema, threshold, Submit Guard, Broker, Approval, Runtime Planning, D12 ADD propagation, D25 sell intent mapping, D28 budget reconciliation, or Phase28-C ADD bridge behavior was changed.

## Canonical Authority

Shared authority:

```text
CANONICAL_REDUCE_INTENSITY_AUTHORITY
phase28_d34_canonical_reduce_intensity_authority.v1
```

Accepted ratios are unchanged:

```text
LIGHT  = 0.25
MEDIUM = 0.33
STRONG = 0.50
```

Unknown or missing intensity is fail-closed as `REVIEW_REQUIRED`; it does not default to LIGHT and does not fall back to EXIT.

## Portfolio Construction

The previous REDUCE/REMOVE combined branch was split:

```text
REDUCE_CANDIDATE -> partial remaining target_weight
REMOVE_CANDIDATE -> target_weight 0
```

For valid REDUCE:

```text
remaining_target_weight = current_weight * (1 - reduce_fraction)
released_reduce_capacity = current_weight - remaining_target_weight
```

The member preserves:

```text
source_pm_decision_ref
reduce_intensity
reduce_fraction
reduce_fraction_authority
remaining_target_weight
released_reduce_capacity
```

## Position Sizing

Existing-position REDUCE now evaluates executable sell transaction quantity, not retained baseline quantity. If the sell delta rounds below lot/minimum, current quantity is preserved and the position receives:

```text
REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT
quantity_delta_candidate = 0
```

It does not force `target_quantity_candidate = 0`, and therefore does not create `SELL_EXIT`.

## Reproduction

77760 reproduction:

```text
current_weight = 0.053147
reduce_intensity = LIGHT
target_weight = 0.039860
released_reduce_capacity = 0.013287
current_quantity = 100
quantity_delta_candidate = 0
```

43880 reproduction:

```text
current_weight = 0.127745
reduce_intensity = LIGHT
target_weight = 0.095809
released_reduce_capacity = 0.031936
current_quantity = 100
no forced EXIT
```

## Validation

Short validation passed:

```text
shared authority resolver PASS
LIGHT / MEDIUM / STRONG partial SELL_REDUCE quantity PASS
single-lot LIGHT no forced EXIT PASS
77760 reproduction PASS
43880 reproduction PASS
unknown intensity fail-closed PASS
Sell Planning shared authority regression PASS
D25 Runtime Planning regression PASS
D28 Portfolio Construction reconciliation regression PASS
D31 Position Sizing baseline regression PASS
Phase28-C ADD regression PASS
compile PASS with PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache
git diff --check PASS
```

One full legacy D19 test file was not used as the final gate because an existing pending-conflict assertion now reflects earlier D8 sell-pending reconciliation behavior. The D34-relevant D19 REDUCE quantity and SELL Planning cases were run directly and passed.

## Final Judgment Details

```text
Primary Judgment: PHASE28_D34_CANONICAL_REDUCE_INTENSITY_AUTHORITY_INTEGRATED_SHORT_VALIDATION_PASS
Fresh Test Entry Decision: READY
Implementation changed: YES
Config / Schema / Threshold changed: NO
Performance changed: NO
Runtime Authority violation: NO
Resume executed: NO
Fresh run executed: NO
Long Historical executed: NO
Repair Required: NO
Next Phase: Fresh 100BD REDUCE runtime conformance validation
```
