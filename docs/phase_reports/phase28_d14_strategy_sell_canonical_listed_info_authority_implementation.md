# Phase28-D14: Strategy SELL Canonical listed_info Authority Implementation

## Executive Summary

Primary Judgment:

```text
PHASE28_D14_STRATEGY_SELL_CANONICAL_LISTED_INFO_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

Restart Entry Decision:

```text
APPROVED
```

D14 implemented the single approved repair from D13:

```text
Strategy executable SELL pending
-> Canonical PIT Listed Issues lookup through Strategy Source Authority
-> PendingOrderItem.listed_info materialized before pending write
```

No Submit Guard, Broker normalizer, Approval, Pending Composition D8 merge, D12 PM ADD propagation, Phase28-C ADD bridge, config, schema, or threshold code was changed.

## Implemented Repair

Primary file:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

Implementation points:

```text
strategy_authority._strategy_authority_context
  reads strategy/input_manifest.json
  extracts strategy_source_authority

strategy_authority._pending_item_from_strategy_plan
  resolves listed_info before PendingOrderItem creation
  BUY path remains Opportunity-based
  SELL path requires canonical listed_info

strategy_authority._canonical_listed_info_from_strategy_source_authority
  validates Strategy Source Authority
  reads canonical listed_issues parquet
  selects exactly one PIT row for symbol/business_date
  materializes required listed_info fields
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:473-492
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:779-786
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:911-1130
```

## Authority Priority

Implemented priority:

```text
1. Canonical PIT Listed Issues via Strategy Source Authority for SELL
2. Opportunity embedded authority consistency check when present
3. Current / symbol identity check through canonical code == symbol and current_listed == true
4. D8 compatible PM SELL merge unchanged downstream
5. REVIEW_REQUIRED before pending write when canonical authority fails
```

BUY behavior remains unchanged:

```text
BUY continues to use _listed_info_from_opportunity_authority(...)
```

## Canonical Source

Canonical source:

```text
strategy/input_manifest.json
  -> strategy_source_authority
  -> paths.listed_issues or source_records.listed_issues.path
  -> J-Quants listed_issues parquet
```

Required materialized fields:

```text
code
market
product_category
security_type
current_listed
business_date / row_date lineage
source artifact path
source hash
Strategy Source Authority lineage
```

`security_type` uses `SecType` / `Type` when present and otherwise falls back to `product_category`, matching the D13 accepted design for J-Quants listed_issues snapshots that lack explicit `security_type`.

## Fail-Closed Conditions

The Strategy SELL producer now returns REVIEW_REQUIRED before pending write when any of the following is true:

```text
strategy_source_authority missing
strategy_source_authority status not PASS
business_date mismatch
listed_issues source path missing
listed_issues source file missing
listed_issues source record missing
listed_issues PIT status not PASS
source hash mismatch
source unreadable
Code column missing
no symbol row
future-dated row
no PIT row
multiple PIT rows
canonical row validation failed
Opportunity symbol / explicit market / product_category / security_type conflict
```

This prevents the previous failure mode:

```text
listed_info = null
-> Submit Guard
-> listed_info_missing
```

## 30410 Reproduction

Focused fixture:

```text
business_date: 2023-06-14
symbol: 30410
side: SELL
intent: SELL_EXIT
Opportunity Authority: absent
Canonical listed_issues row: present
row: Date=2023-06-14, Code=30410, MktNm=スタンダード, ProdCat=011
```

Result:

```text
Strategy Authority: PASS
Pending item: generated
listed_info_authority: canonical_pit_listed_issues
code: 30410
market: スタンダード
product_category: 011
security_type: 011
current_listed: true
Approval: APPROVED
Broker issue-code normalization: PASS, broker_issue_code=3041
```

Test evidence:

```text
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py:159-273
```

## Short Validation

Commands executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k phase28_d14 --basetemp=/private/tmp/phase28_d14_pytest
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_d_position_management.py -k phase28_d12
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k phase28_c
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k phase28_c
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k 'sell or buy_add or canonical'
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/broker/test_broker_issue_code_normalizer.py
```

Results:

```text
compile: PASS
30410 reproduction: PASS, 1 passed / 15 deselected
Strategy Authority ordinary BUY/SELL-adjacent regression: PASS, 16 passed
D8 SELL merge regression: PASS, 7 passed
D12 PM ADD propagation regression: PASS, 8 passed / 13 deselected
Phase28-C Portfolio Construction ADD regression: PASS, 2 passed / 23 deselected
Phase28-C Position Sizing ADD regression: PASS, 2 passed / 36 deselected
ordinary SELL / BUY_ADD runtime planning regression: PASS, 6 passed / 33 deselected
Broker normalizer regression: PASS, 5 passed
```

JSON validation:

```text
reports/phase_reports/phase28_d14_strategy_sell_canonical_listed_info_authority_implementation.json: PASS
reports/phase28_d14_strategy_sell_canonical_listed_info_authority_implementation/validation_results.json: PASS
```

## Guardrails

Runtime Authority violation:

```text
None found in D14 short validation.
```

Performance change:

```text
None.
```

Config / Schema / Threshold change:

```text
None.
```

Resume executed:

```text
No.
```

Fresh run executed:

```text
No.
```

Long Historical executed:

```text
No.
```

## Final Judgment

```text
Primary Judgment: PHASE28_D14_STRATEGY_SELL_CANONICAL_LISTED_INFO_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
Restart Entry Decision: APPROVED
Implemented repair: Strategy SELL canonical PIT listed_info materialization
Canonical listed-info source: Strategy Source Authority listed_issues parquet
30410 reproduction: PASS
D8 regression: PASS
D12 regression: PASS
Phase28-C regression: PASS
ordinary BUY / SELL regression: PASS
compile: PASS
JSON validation: PASS
Runtime Authority violation: NONE
Performance changed: NO
Config / Schema / Threshold changed: NO
Resume executed: NO
Fresh run executed: NO
Long Historical executed: NO
Open gaps: None for D14 short validation scope
fresh 100BD execution: READY
```
