# Phase28-D51: Candidate Listed-Info Metadata Propagation Repair

## Primary Judgment

```text
PHASE28_D51_CANDIDATE_LISTED_INFO_METADATA_PROPAGATION_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

D51 implemented the minimal propagation repair identified by D50. No config, formal schema, threshold, resume, fresh run, long historical run, or runtime mutation was executed.

## Implemented Repair

The only functional repair is candidate listed-info metadata propagation through Runtime BUY AI materialization:

```text
candidate_features
↓
candidate_decisions
↓
opportunity_rankings
↓
BUY Quality decisions
↓
Portfolio Construction member
↓
D49 broker eligibility payload
↓
classify_broker_security(...)
```

Changed files:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/strategy/buy_quality.py
tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
tests/strategy/test_phase26_h_adaptive_buy_quality.py
tests/strategy/test_phase22_e_portfolio_construction.py
```

## Code Changes

Runtime BUY AI now preserves canonical listed-info-compatible metadata from the candidate feature row after scoring and before `_candidate_payload` writes `candidate_decisions.json`.

Code references:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:768
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:1472
```

Opportunity ranking materialization now reattaches the candidate listed-info metadata by code.

Code references:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:998
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py:1031
```

BUY Quality decision materialization now preserves listed-info metadata from opportunity first, then candidate.

Code references:

```text
src/ai_fund_lab_v2/strategy/buy_quality.py:446
src/ai_fund_lab_v2/strategy/buy_quality.py:450
```

## Propagated Fields

Minimum propagated fields:

```text
code
market
market_name
product_category
security_type
current_listed
is_current_listed
listed_info
```

When `security_type` is absent, it is derived from `product_category`, matching the D48 listed-info coercion contract. D51 does not duplicate broker classification mapping.

## 93990 Runtime-Equivalent Result

For the D50 target symbol:

```text
symbol = 93990
product_category = 021
security_type = 021
market = スタンダード
```

Runtime-equivalent PC validation now reaches D49 broker eligibility:

```text
broker_security_type = UNSUPPORTED_FOREIGN_LISTED_STOCK
reason = BROKER_PRODUCT_CATEGORY_UNSUPPORTED
membership_intent = EXCLUDE
target_membership = false
target_weight = 0.0
BUY_NEW exposure = 0.0
```

Evidence:

```text
reports/phase28_d51_candidate_listed_info_metadata_propagation_repair/93990_pc_broker_eligibility.json
reports/phase28_d51_candidate_listed_info_metadata_propagation_repair/93990_runtime_equivalent_exclusion.json
```

## Regression Results

```text
focused D51 propagation tests: 3 passed
tests/strategy/test_phase22_e_portfolio_construction.py: 47 passed
tests/strategy/test_phase26_h_adaptive_buy_quality.py: 12 passed
tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py: 8 passed
D48/D49 broker normalization bundle: 19 passed
D44/D46 SELL pending bundle: 19 passed
D39/D42/Phase28-C focused bundles: 62 passed; 15 passed, 32 deselected
py_compile: PASS
git diff --check: PASS
```

## Constraint Confirmation

```text
D48 broker classification changed = false
D49 broker eligibility changed = false
Portfolio Construction changed = false
Position Sizing changed = false
Runtime Planning changed = false
Submit Guard changed = false
Broker normalizer changed = false
Config changed = false
Schema changed = false
Threshold changed = false
Resume executed = false
Fresh run executed = false
Long Historical executed = false
Runtime mutated = false
```

## Next Phase

```text
Phase28-D52
Fresh 100BD runtime conformance run for 2023-05-29 93990 broker eligibility exclusion and overall BUY_ADD/SELL conformance.
```

