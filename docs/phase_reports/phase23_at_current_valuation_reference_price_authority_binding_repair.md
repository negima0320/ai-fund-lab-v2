# Phase23-AT Current Valuation / Reference Price Authority Binding Repair

## Primary Judgment

```text
PHASE23_AT_REFERENCE_PRICE_AUTHORITY_BINDING_REVIEW_REQUIRED
```

価格Authority binding自体は短時間検証で修正成立。ただし、要求されたData Readiness regression subsetで現行worktree由来のout-of-scope failが3件残ったため、Task全体のPrimaryはReview Requiredとする。

## Secondary Judgment

```text
REFERENCE_PRICE_AUTHORITY_BINDING_REPAIRED
TARGETED_AND_STRATEGY_REGRESSION_PASS
DATA_READINESS_REGRESSION_HAS_OUT_OF_SCOPE_FAILURES
RUNTIME_RERUN_NOT_EXECUTED
```

## Root Cause

対象Run:

```text
runtime-test-historical-smoke-20260730T014900699579Z
business_date = 2026-07-06
```

Data Readiness / Market Evidence / Current Valuation authorityはREADYだった。

一方、Position Sizingに渡る `price_volatility` artifactはvolatilityのみをmaterializeし、Position Sizingの正準入力である `reference_price` / `reference_price_authority` / `reference_price_resolution` を提供していなかった。

その結果、Position Sizing rowsは `target_notional=79000` まで解決したが `reference_price=null` のため `quantity_status=PRICE_UNAVAILABLE` となり、Runtime Planningが正しく `REVIEW_REQUIRED_MISSING_PRICE` へfail-closedした。

分類:

```text
PRICE_AUTHORITY_EXISTS_BUT_POSITION_SIZING_INPUT_WIRING_MISSING
```

## Repair

`src/ai_fund_lab_v2/strategy/input_materialization.py`

- 既存PIT market quote sourceから `reference_price` をmaterialize。
- `reference_price_authority` を `REFERENCE_PRICE_AUTHORITY` として出力。
- source authorityは `MARKET_EVIDENCE_AUTHORITY`。
- `latest_fallback_used=false` を明示。
- price typeは `planning_reference_close`。

`src/ai_fund_lab_v2/strategy/position_sizing.py`

- `price_volatility` summaryから `reference_price` 系fieldをPosition Sizing rowへmerge。
- `resolve_reference_price()` を追加。
- `target_notional > 0` のときだけ価格必須。
- valid zero allocationでは価格欠損をReview理由にしない。
- Broker snapshot、new fetcher、historical専用分岐、zero substitutionは追加なし。

`docs/02_architecture/strategy_architecture_v1.md`

- Position Sizingの `reference_price` はPIT検証済みMarket Evidence / Current Valuation authority由来であり、Position Sizingは取得・推定・latest fallbackしないことを追記。

## Contract Confirmation

Canonical fields:

```text
reference_price
reference_price_authority
reference_price_resolution
reference_price_type
reference_price_date
```

価格必須条件:

```text
target_weight > 0
target_notional > 0
quantity calculation required
```

価格不要条件:

```text
target_weight = 0
target_notional = 0
valid zero allocation
no-action / no-order without quantity conversion
```

## Isolated Reproduction

対象Runの既存入力だけを読取専用で使い、一時領域に再materializeした。

```text
price rows = 50
price_missing_count = 0
PRICE_UNAVAILABLE = 0
positive_quantity_count = 9
```

Runtime fresh-run、1BD、10BD、20BDは実施していない。

## Validation

PASS:

```text
py_compile
Position Sizing / input materialization targeted: 41 passed
Strategy / Shadow / Runtime Planning expanded: 82 passed
Strategy Planning Authority / Source / Summary: 19 passed
```

FAIL:

```text
Data Readiness temporal subset: 16 passed, 3 failed
```

Failing subsetは今回変更したStrategy input materialization / Position Sizing経路ではなく、既存dirty worktreeのData Readiness expectationsに属するため、Phase23-ATでは修正しない。

## Modified Files

```text
docs/02_architecture/strategy_architecture_v1.md
src/ai_fund_lab_v2/strategy/input_materialization.py
src/ai_fund_lab_v2/strategy/position_sizing.py
tests/strategy/test_phase22_j_position_sizing.py
tests/strategy/test_phase22_qe_input_materialization.py
```

## Deliverables

Human:

```text
docs/phase_reports/phase23_at_current_valuation_reference_price_authority_binding_repair.md
```

Machine:

```text
reports/phase_reports/phase23_at_current_valuation_reference_price_authority_binding_repair.json
```

Evidence:

```text
reports/phase23_at_current_valuation_reference_price_authority_binding_repair/
```

## Existing Run Preservation

Required historical runs were read-only. Hash preservation evidence was generated. No existing run artifact was mutated.

## Remaining Gaps

- Data Readiness regression subset has 3 out-of-scope failures in current worktree.
- Formal trading unit authority remains read-only / existing config-derived behavior and was not expanded in this task.

## Next Operator Action

ChatGPT Evidence ReviewでData Readiness failをout-of-scopeとして許容するか確認する。許容される場合のみ、Operatorが1BD Runtime Validationへ進む。

```text
READY_FOR_1BD_RUNTIME_VALIDATION = NO
```
