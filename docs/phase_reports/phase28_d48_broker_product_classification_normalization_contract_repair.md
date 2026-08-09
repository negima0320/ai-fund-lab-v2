# Phase28-D48: Broker Product Classification / Issue-Code Normalization Contract Repair

## Judgment

Primary Judgment:

```text
PHASE28_D48_BROKER_PRODUCT_CLASSIFICATION_CONTRACT_REPAIRED_SHORT_VALIDATION_PASS
```

Supporting Judgments:

```text
PHASE28_D48_BROKER_SUPPORT_AUTHORITY_CONFIRMS_93990_UNSUPPORTED_FAIL_CLOSED
PHASE28_D48_SHORT_REGRESSION_PASS
```

Fresh Test Entry Decision:

```text
BLOCKED
```

D48 implemented one bounded repair: broker issue-code normalization now consumes an explicit broker product classification contract instead of using J-Quants PIT `product_category` directly as broker eligibility.

No config, schema, threshold, Submit Guard policy, broker available quantity bypass, historical-only exception, resume, fresh run, long historical run, runtime mutation, or broker write was performed.

## Authority Resolution

Canonical listed-info authority:

```text
J-Quants PIT Listed Issues
Purpose = security identity / listing classification
```

Broker classification authority:

```text
Tachibana / e-shiten cash equity product contract
Purpose = broker trading eligibility and issue-code normalization permission
```

Repo architecture confirms `CLMKabuNewOrder` cash order fields use:

```text
sIssueCode
sSizyouC
sBaibaiKubun
sOrderSuryou
sGenkinShinyouKubun
```

and do not send J-Quants `ProdCat` as a broker request field:

```text
docs/02_architecture/tachibana_demo_order_api_design.md:54-72
```

External broker product authority checked during D48:

```text
https://www.e-shiten.co.jp/serviceitem/
```

This states e-shiten cash stock trading covers TSE-listed issues excluding foreign stocks and duplicate-listed issues whose priority market is elsewhere.

Additional online order rule:

```text
https://t-stockhouse.jp/product/stock/rule.php
```

This states some domestic-exchange-listed foreign stocks are not handled online, and trading domestic-exchange-listed foreign stocks requires foreign securities account paperwork.

Therefore `021` cannot be treated as supported merely because the issue is current-listed in J-Quants.

## Implemented Contract

Changed file:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
```

New internal helper:

```text
classify_broker_security(...)
```

Mapping:

```text
011
→ TACHIBANA_CASH_EQUITY_LISTED_STOCK
→ tradable = true
→ reason = BROKER_PRODUCT_CATEGORY_SUPPORTED

021
→ UNSUPPORTED_FOREIGN_LISTED_STOCK
→ tradable = false
→ reason = BROKER_PRODUCT_CATEGORY_UNSUPPORTED

other / unknown
→ UNKNOWN
→ tradable = false
→ reason = BROKER_PRODUCT_CATEGORY_UNKNOWN
```

The legacy constant remains as compatibility alias:

```text
ORDINARY_STOCK_PRODUCT_CATEGORIES = BROKER_CASH_EQUITY_PRODUCT_CATEGORIES
```

## 93990 Result

Canonical identity:

```text
symbol = 93990
market = スタンダード
product_category = 021
security_type = 021
current_listed = true
```

Broker classification:

```text
broker_support = UNSUPPORTED
broker_security_type = UNSUPPORTED_FOREIGN_LISTED_STOCK
normalization_mode = FAIL_CLOSED
reason = BROKER_PRODUCT_CATEGORY_UNSUPPORTED
```

Historical submit focused reproduction:

```text
symbol = 93990
side = SELL
owned_quantity = 700
sell_quantity = 100
broker_available_quantity = null
broker_available_quantity_source = historical_simulated_broker_authority
broker_available_quantity_reason = BROKER_PRODUCT_CATEGORY_UNSUPPORTED
submitted_count = 0
```

The quantity contract itself remains valid. The fail-closed reason is now explicit broker classification unsupported, not generic `product_category_not_allowed`.

## Common Runtime Path

Historical path:

```text
_historical_available_quantity_evidence
↓
_broker_issue_code_for_item
↓
normalize_broker_issue_code
↓
classify_broker_security
```

Production/demo broker request path:

```text
TachibanaCashStockOrderRequest.from_runtime_v2_submit_command
↓
normalize_broker_issue_code
↓
classify_broker_security
```

Non-historical readonly available quantity path:

```text
_broker_available_quantity_evidence
↓
_broker_issue_code_for_item
↓
normalize_broker_issue_code
↓
classify_broker_security
```

Historical-only logic:

```text
NO
```

## Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/broker/test_broker_issue_code_normalizer.py \
  tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py \
  tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py -q

19 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py \
  tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py -q

19 passed
```

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase23_i_strategy_planning_authority.py::test_phase28_d14_strategy_sell_30410_uses_canonical_listed_info_without_opportunity \
  tests/strategy/test_phase22_d_position_management.py::test_phase28_d12_runtime_current_adapter_reads_runtime_pm_decision_type \
  tests/strategy/test_phase22_d_position_management.py::test_phase28_d12_runtime_current_adapter_preserves_action_decision_priority_and_conflict_evidence \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_c_canonical_add_bridge_increases_existing_target_weight_when_incremental_evidence_passes \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta -q

8 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_d48 python3 -m py_compile \
  src/ai_fund_lab_v2/broker/issue_code_normalizer.py \
  src/ai_fund_lab_v2/broker/tachibana_order_request.py \
  src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py

PASS
```

Note: the first compile attempt without `PYTHONPYCACHEPREFIX` failed because the macOS Python cache path under `~/Library/Caches` was not writable in the sandbox. Re-running with tmp pycache passed.

## Fresh Entry

Fresh 100BD entry is not approved by D48:

```text
Fresh Test Entry Decision = BLOCKED
```

Reason:

```text
93990 is now explicitly unsupported for current Tachibana/e-shiten cash equity handling.
Fresh 100BD would still stop unless unsupported broker classes are excluded upstream before Pending / Submit.
```

Next minimal phase should move broker eligibility into planning/universe gating so unsupported securities do not reach Submit as executable SELL orders.

## Evidence

```text
reports/phase28_d48_broker_product_classification_normalization_contract_repair/broker_product_classification_contract.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/93990_broker_support_authority.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/canonical_to_broker_mapping.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/issue_code_normalizer_before_after.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/011_regression.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/unsupported_category_negative.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/unknown_category_negative.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/historical_production_common_path.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/93990_submit_guard_reproduction.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/sell_reduce_quantity_regression.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/d44_d46_regression.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/short_regression_results.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/compile_validation.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/architecture_conformance.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/fresh_test_contract.json
reports/phase28_d48_broker_product_classification_normalization_contract_repair/open_gap_inventory.json
reports/phase_reports/phase28_d48_broker_product_classification_normalization_contract_repair.json
```

## Final Fields

```text
Primary Judgment = PHASE28_D48_BROKER_PRODUCT_CLASSIFICATION_CONTRACT_REPAIRED_SHORT_VALIDATION_PASS
Supporting Judgments = PHASE28_D48_BROKER_SUPPORT_AUTHORITY_CONFIRMS_93990_UNSUPPORTED_FAIL_CLOSED; PHASE28_D48_SHORT_REGRESSION_PASS
Fresh Test Entry Decision = BLOCKED
93990 broker support = UNSUPPORTED
Evidence authority = Tachibana/e-shiten cash equity product contract
Canonical category = 021
Broker classification result = UNSUPPORTED_FOREIGN_LISTED_STOCK / BROKER_PRODUCT_CATEGORY_UNSUPPORTED
011 regression result = PASS
Unsupported category result = PASS
Unknown category result = PASS
Historical path result = PASS_FAIL_CLOSED_COMMON_CONTRACT
Production path result = PASS_FAIL_CLOSED_COMMON_CONTRACT
93990 Submit Guard reproduction = PASS_FAIL_CLOSED
D44/D46 regression = PASS
Historical-only logic = NO
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime Authority violation = NO
Resume executed = NO
Fresh executed = NO
Long Historical executed = NO
Open Gaps = account-specific foreign securities account status not modeled; exhaustive ProdCat table not stored
Next Phase = Phase28-D49 broker eligibility planning/universe exclusion
```
