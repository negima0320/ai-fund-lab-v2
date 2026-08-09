# Phase28-D47: Broker Available Quantity Product-Category Authority Root Cause

## Judgment

Primary Judgment:

```text
PHASE28_D47_BROKER_PRODUCT_CATEGORY_NORMALIZATION_GAP_CONFIRMED
```

Root scope:

```text
BROKER_PRODUCT_CATEGORY_NORMALIZATION_GAP
CANONICAL_LISTED_INFO_TO_BROKER_CLASSIFICATION_CONTRACT_GAP
LEGACY_PRODUCT_CATEGORY_ASSUMPTION
```

Repair Required:

```text
YES
```

D47 was read-only diagnosis. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, runtime mutation, broker write, or runtime replay was performed.

## Target

```text
run_id = runtime-test-historical-smoke-20260807T181131555434Z
business_date = 2023-06-01
halt_stage = submit
exit_code = 20
symbol = 93990
side = SELL
pending_item_id = opi-sell-reduce-pm-93990-001
decision_id = pm-2023-06-01-93990-reduce
```

Direct Submit Guard evidence:

```text
guard_decision = BLOCKED
submit_item_status = REVIEW_REQUIRED
guard_reason = sell broker available quantity missing
violated_policy = broker_available_quantity
violated_policy_source = historical_simulated_broker_authority
broker_available_quantity = null
broker_available_quantity_source = historical_simulated_broker_authority
broker_available_quantity_reason = product_category_not_allowed
sell_quantity_guard_status = BROKER_AVAILABLE_MISSING
```

Artifact:

```text
.runtime/runtime_state/run_manifest/2023-06-01/runtime-v2-submit-2023-06-01-20260807T195123.242947+0000.json
```

## Code Trace

Submit selects historical broker available quantity evidence for historical SELL items:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:381-392
```

The historical authority calls broker issue-code normalization first:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1401-1414
```

The first rejecting producer is:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py:50-68
normalize_broker_issue_code(...)
```

Allowed category set:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py:35
ORDINARY_STOCK_PRODUCT_CATEGORIES = frozenset({"011"})
```

Direct reject condition:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py:67-68
if info.product_category not in ORDINARY_STOCK_PRODUCT_CATEGORIES:
    raise BrokerIssueCodeNormalizationError("product_category_not_allowed")
```

Submit Guard then converts `broker_available_quantity = None` into the blocking guard evidence:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:2270-2310
```

## 93990 Category

Pending item listed-info:

```text
authority = canonical_pit_listed_issues
code = 93990
market = スタンダード
product_category = 021
security_type = 021
current_listed = true
business_date = 2023-06-01
source = reports/runtime_tests/runs/runtime-test-historical-smoke-20260807T181131555434Z/daily/2023-06-01/market_refresh/inputs/historical_asof/2023-06-01/raw/jquants/listed_issues/data.parquet
source_hash = 2013358d2f6097c85e14ff4cac89c6b6139fe9853366d9913f366bd1b8df443b
```

The same listed-issues file contains 6 `ProdCat=021` rows on 2023-06-01, including:

```text
17730 YTL Corporation Berhad
48750 MediciNova,Inc.
66970 Techpoint,Inc.
76990 OMNI-PLUS SYSTEM LIMITED
92570 YCP Holdings (Global) Limited
93990 Beat Holdings Limited
```

This is not evidence that the symbol is unlisted. It is evidence that 93990 is a current listed issue whose J-Quants listed-issues product category is not the normalizer's only allowed category `011`.

J-Quants listed-info documentation confirms the listed-info API is a listed issue information authority and explicitly notes that foreign stocks / foreign ETFs can appear in that data. The fetched public docs did not expose the legacy `ProdCat` code table, so the exact label of `021` remains an open documentation authority gap in this repo. The local PIT data strongly indicates `021` is the foreign-stock class for these rows.

## Production Path

This is not historical-only in code.

For non-historical SELL available quantity, the path is:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:384-386
_broker_available_quantity_evidence(...)

src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:1317-1329
_broker_issue_code_for_item(...) before readonly snapshot matching
```

For Tachibana request construction, the path is:

```text
src/ai_fund_lab_v2/broker/tachibana_order_request.py:84-92
TachibanaCashStockOrderRequest.from_runtime_v2_submit_command(...)
```

Both paths call the same normalizer. Therefore the current local code would block 93990 / `021` before production broker write as well. However, no local artifact proves Tachibana itself rejects such a SELL. The confirmed defect is our broker product-category normalization/eligibility contract, not a confirmed true unsupported security.

## Why 011 Passes And 021 Fails

`011` passes because the broker normalizer hard-codes:

```text
ORDINARY_STOCK_PRODUCT_CATEGORIES = {"011"}
```

`021` fails because the current contract uses the J-Quants canonical listed-info `product_category` directly as a broker ordinary-stock eligibility allowlist. There is no separate broker product classification, no mapping, and no explicit production-supported category contract.

## Quantity And Safety

The SELL quantity contract is not the cause:

```text
current_quantity = 700
sell_quantity = 100
expected_remaining_quantity = 600
quantity_reconciliation_status = PASS
submit_aggregate_status = PASS
safety_guard_status = PASS
```

The failure occurs only after broker available quantity authority tries to normalize the issue category.

## Causality

D44:

```text
EXPOSURE_ONLY
```

D46:

```text
EXPOSURE_ONLY
```

D44/D46 correctly propagated canonical 93990 listed-info as `021/021`. That exposed the downstream broker normalizer's legacy `011` assumption.

D34:

```text
NO_CAUSE
```

REDUCE quantity semantics passed.

D39:

```text
NO_CAUSE
```

Submit feasibility passed.

D42:

```text
NO_CAUSE
```

Aggregate/passive validation is not the blocking producer.

## Minimal Repair Scope

D48 should define and implement one bounded broker product-category classification/normalization contract:

```text
Canonical PIT Listed Issues product_category
↓
explicit broker category eligibility / mapping
↓
normalize_broker_issue_code
↓
historical and production available quantity paths
```

D48 must not blindly add `021`, blindly convert `021` to `011`, bypass broker available quantity, substitute ledger quantity unconditionally, or add a historical-only special case.

Expected minimal files:

```text
src/ai_fund_lab_v2/broker/issue_code_normalizer.py
focused tests for 021 eligibility/mapping and unchanged 011 behavior
```

Out of scope:

```text
D44/D46 listed-info authority
PM REDUCE quantity contract
Portfolio Construction
Position Sizing
Submit Guard policy
Safety
```

## Evidence

```text
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/93990_submit_guard_trace.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/product_category_contract_inventory.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/historical_simulated_broker_allowlist.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/production_broker_category_path.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/canonical_vs_broker_category_authority.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/security_category_coverage_inventory.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/d44_d46_causality.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/historical_vs_production_scope.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/root_cause.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/minimal_repair_scope.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/next_phase_contract.json
reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause/open_gap_inventory.json
reports/phase_reports/phase28_d47_broker_available_quantity_product_category_authority_root_cause.json
```

## Final Fields

```text
Primary Judgment = PHASE28_D47_BROKER_PRODUCT_CATEGORY_NORMALIZATION_GAP_CONFIRMED
Direct HALT Producer = Submit Guard / _sell_guard_evidence
First Rejecting Producer = broker.issue_code_normalizer.normalize_broker_issue_code
Direct Reason = product_category_not_allowed -> sell broker available quantity missing
93990 canonical category = 021
Historical broker input category = 021
Allowed category set = {"011"}
Why 021 rejected = hard-coded ordinary-stock allowlist accepts only 011
Production path behavior = same normalizer blocks before broker boundary in current code
Historical-only defect = NO
True unsupported security = NOT_CONFIRMED
D44/D46 causality = EXPOSURE_ONLY
Root Cause = broker product-category normalization / classification contract gap
Repair Required = YES
Minimal D48 Scope = broker product-category classification/normalization contract
Implementation changed = false
Config / Schema / Threshold changed = false / false / false
Resume / Fresh / Long Historical executed = false / false / false
Runtime mutated = false
Next Phase = Phase28-D48
```
