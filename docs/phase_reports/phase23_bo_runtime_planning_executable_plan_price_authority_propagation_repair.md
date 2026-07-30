# Phase23-BO Runtime Planning Executable Plan Price Authority Propagation Repair

## Primary Judgment

`PHASE23_BO_EXECUTABLE_PLAN_PRICE_AUTHORITY_PROPAGATION_SHORT_VALIDATION_PASS`

## Secondary Judgment

- `POSITION_SIZING_PRICE_AUTHORITY_IDENTIFIED`
- `RUNTIME_PLANNING_PRESERVES_PRICE_AUTHORITY`
- `STRATEGY_AUTHORITY_RESOLVES_PLAN_PRICE`
- `EXECUTABLE_BUY_PRICE_CONTRACT_PASS`
- `EXECUTABLE_SELL_PRICE_CONTRACT_PASS`
- `NO_ORDER_PRICE_OPTIONAL_PRESERVED`
- `NEGATIVE_FAIL_CLOSED_PRESERVED`
- `READY_FOR_2022_10BD_RUNTIME_RERUN`

## Root Cause

Phase23-BNで確認された `2022-07-08` / `94320` のHALTは、Position Sizingが保持していたReference Price AuthorityをRuntime Planning executable planが保持せず、Strategy Planning AuthorityがPending生成時に `strategy_plan_price_missing:94320` でfail-closedしたことが原因である。

BN Evidenceでは以下が成立していた。

- Position Sizing: `reference_price = 153.2`
- Position Sizing: `reference_price_resolution.status = PASS`
- Position Sizing: `reference_price_authority.PIT_status = PASS`
- Runtime Planning: `planning_intent = BUY_NEW`
- Runtime Planning: `planned_quantity = 1100`
- Runtime Planning: price authority fields absent
- Strategy Authority: `strategy_plan_price_missing:94320`

## Repair

Runtime Planningのexecutable plan contractを拡張し、Position Sizing rowから以下を明示伝播するようにした。

- `reference_price`
- `reference_price_authority`
- `reference_price_resolution`
- `reference_price_type`
- `reference_price_date`

Strategy Planning Authorityは、Pending item生成時にRuntime Planning plan上のprice authorityだけをcanonical sourceとして読む。旧current/runtime market lookupは削除し、`price_by_symbol` fallbackも使用しない。

## Executable Price Contract

Price authorityが必須となるのは以下のexecutable planのみ。

- `planning_intent in BUY_NEW / BUY_ADD / SELL_REDUCE / SELL_EXIT`
- `planned_quantity > 0`
- `quantity_status = RESOLVED_EXECUTABLE`

`NO_ORDER` は価格不要のまま維持した。

## Fail-Closed Rules

以下はfail-closedする。

- price missing / invalid
- price authority missing
- symbol mismatch
- business date mismatch
- future price date
- `PIT_status != PASS`
- `reference_price_resolution.status != PASS`

Silent default、zero fill、latest fallback、current snapshot lookupは使用しない。

## Canonical 2022 Day-6 Reproduction

既存Runは変更せず、`/private/tmp/phase23_bo_canonical_repro` に複製入力を作成して確認した。

- business date: `2022-07-08`
- symbol: `94320`
- reference price: `153.2`
- planned quantity: `1100`
- Strategy Authority status: `PASS`
- pending item count: `1`
- pending item: `BUY / 94320 / 1100 / estimated_price=153.2`
- Pending lineage: `reference_price_authority.PIT_status = PASS`

## Modified Files

- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`

## Evidence

Evidence directory:

`reports/phase23_bo_runtime_planning_executable_plan_price_authority_propagation_repair/`

Key files:

- `root_cause.json`
- `position_sizing_price_trace.json`
- `runtime_planning_price_trace.json`
- `strategy_authority_price_trace.json`
- `pending_price_lineage.json`
- `buy_sell_contract_matrix.json`
- `negative_fail_closed_cases.json`
- `canonical_2022_day6_reproduction.json`
- `previous_blocker_regression_check.json`
- `existing_run_hash_preservation.json`
- `modified_files.json`
- `test_results.json`

Machine report:

`reports/phase_reports/phase23_bo_runtime_planning_executable_plan_price_authority_propagation_repair.json`

## Short Validation

Executed:

```text
py_compile
```

PASS.

Executed:

```text
pytest tests/strategy/test_phase22_g_runtime_planning.py
pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
pytest tests/runtime_v2/test_phase23_bi_buy_ai_import_boundary.py
pytest tests/runtime_v2/test_phase23_ab_no_order_submit_guard.py
```

Combined result:

```text
60 passed
```

## Existing Run Preservation

The required existing runs were not mutated.

- `runtime-test-historical-smoke-20260730T090527721192Z`
- `runtime-test-historical-smoke-20260730T082859880393Z`
- `runtime-test-historical-smoke-20260730T080901510234Z`

BO reproduction wrote only under `/private/tmp/phase23_bo_canonical_repro`.

## Not Executed

- fresh-run
- 1BD
- 10BD
- 20BD
- Broker Write
- J-Quants fetch
- Runtime Switch

## Next Operator Action

ChatGPT Evidence Review後、Operatorによる2022年10BD historical runtime rerunへ進行可能。
