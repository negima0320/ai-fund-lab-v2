# Phase28-D16: D8 listed_info Authority Precedence Implementation

## Executive Summary

Primary Judgment:

```text
PHASE28_D16_LISTED_INFO_AUTHORITY_PRECEDENCE_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

Restart Entry:

```text
APPROVED
```

D16 implemented the single D15 recommendation:

```text
D8 compatible SELL listed_info conflict evaluator now recognizes:
CANONICAL_PIT_LISTED_ISSUE_AUTHORITY > PM_BASIC_EXECUTION_METADATA
```

The 43880 case now preserves the existing canonical listed_info:

```text
existing canonical market = グロース
new PM basic market = 東証
core identity match = PASS
-> PRESERVE_EXISTING_CANONICAL
-> no REVIEW_REQUIRED
```

No D14 Strategy SELL producer, D12 PM ADD propagation, Phase28-C, Portfolio Construction, Position Sizing, Runtime Planning, Submit Guard, Broker normalizer, Approval, pending identity, config, schema, or threshold behavior was changed.

## Implemented Repair

Changed primary file:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py
```

Implementation points:

```text
_merge_required_authority_for_preserved_sell_item(...)
  records existing/new listed_info authority types and market semantic evidence
  evaluates exact equivalence first
  then applies authority precedence before declaring conflict

_listed_info_authority_precedence_resolution(...)
  requires core identity exact match:
    code / product_category / security_type / current_listed
  allows only:
    existing canonical + new PM basic + market-only semantic granularity difference
  returns PASS only for canonical preservation

_listed_info_authority_type(...)
  classifies:
    canonical_pit_listed_issues -> CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
    PM basic 東証 metadata without canonical lineage -> PM_BASIC_EXECUTION_METADATA
    otherwise -> UNKNOWN_AUTHORITY
```

Code evidence:

```text
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:505-550
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:652-686
src/ai_fund_lab_v2/runtime_v2/pending/composition.py:760-829
```

## Authority Precedence

Implemented precedence:

```text
CANONICAL_PIT_LISTED_ISSUE_AUTHORITY
>
PM_BASIC_EXECUTION_METADATA
```

D16 does not make `market mismatch` globally safe. It only handles this case:

```text
existing canonical listed_info
new PM basic metadata
core identity exact-match
market is the only difference
```

Everything else remains fail-closed.

## 43880 Result

Focused fixture:

```text
existing:
  pending_item_id: strategy-48c2f0737936a341d096
  symbol: 43880
  listed_info_authority: canonical_pit_listed_issues
  market: グロース

new:
  pending_item_id: opi-sell-exit-pm-43880-001
  symbol: 43880
  authority: PM_BASIC_EXECUTION_METADATA
  market: 東証
```

Expected and observed:

```text
status: PASS
pending_item_id: preserved
listed_info: existing canonical preserved
merge_action: PRESERVE_EXISTING_CANONICAL
conflict_status: NO_CONFLICT_AUTHORITY_PRECEDENCE
reason_code: PENDING_SELL_CANONICAL_LISTED_INFO_PRESERVED_OVER_BASIC_MARKET_METADATA
canonical_authority_preserved: true
```

Test evidence:

```text
tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py:94-137
```

## True Conflict Maintained

Canonical-vs-canonical market mismatch remains REVIEW_REQUIRED:

```text
existing canonical market = グロース
new canonical market = スタンダード
-> CONFLICTING_LISTED_INFO
-> PENDING_SELL_LISTED_INFO_AUTHORITY_CONFLICT
```

Test evidence:

```text
tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py:140-176
```

Existing D8 cases remain:

```text
existing null + new valid -> FILL_MISSING_FROM_NEW
existing valid + new null -> PRESERVE_EXISTING
both valid equivalent -> PRESERVE_EXISTING
both null -> REVIEW_REQUIRED
submitted existing -> REVIEW_REQUIRED
BUY items are not authority-merged
unknown/unsupported market authority conflict -> REVIEW_REQUIRED
```

## Short Validation

Commands executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/composition.py tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase28_d8_sell_pending_authority_merge.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -k phase28_d14
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_d_position_management.py -k phase28_d12
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k phase28_c
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k phase28_c
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k 'sell or buy_add or canonical'
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

Results:

```text
compile: PASS
43880 / D8 regression: PASS, 9 passed
D14 regression: PASS, 1 passed / 15 deselected
D12 regression: PASS, 8 passed / 13 deselected
Phase28-C portfolio construction regression: PASS, 2 passed / 23 deselected
Phase28-C position sizing regression: PASS, 2 passed / 36 deselected
ordinary BUY/SELL runtime planning regression: PASS, 6 passed / 33 deselected
D3 sell pending reconciliation regression: PASS, 5 passed
Strategy Authority ordinary regression: PASS, 16 passed
```

JSON validation:

```text
reports/phase_reports/phase28_d16_d8_listed_info_authority_precedence_implementation.json: PASS
reports/phase28_d16_d8_listed_info_authority_precedence_implementation/validation_results.json: PASS
```

## Guardrails

Runtime Authority violation:

```text
None found in short validation.
```

Performance change:

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
Primary Judgment: PHASE28_D16_LISTED_INFO_AUTHORITY_PRECEDENCE_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
Restart Entry: APPROVED
Implemented repair: D8 listed_info Authority precedence evaluator
Authority precedence: CANONICAL_PIT_LISTED_ISSUE_AUTHORITY > PM_BASIC_EXECUTION_METADATA
43880 result: PASS, canonical preserved
D14 regression: PASS
D12 regression: PASS
D8 regression: PASS
Phase28-C regression: PASS
compile: PASS
JSON validation: PASS
Runtime Authority violation: NONE
Performance changed: NO
Resume executed: NO
Fresh run executed: NO
Long Historical executed: NO
Open gaps: None for D16 short validation scope
fresh100BD execution: READY
```
