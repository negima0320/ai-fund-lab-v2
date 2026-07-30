# Phase23-BQ Current Position Membership Temporal Authority Carry-forward Repair

## Primary Judgment

`PHASE23_BQ_CURRENT_POSITION_MEMBERSHIP_TEMPORAL_AUTHORITY_SHORT_VALIDATION_PASS`

## Root Cause

Phase23-BPで確定したRoot Causeは、Runtime PlanningのCurrent Position Membership validatorが、runtime-owned current positionの`as_of`を`business_date`と完全一致させていたこと。

Production Runtimeでは、前営業日・数日前・長期保有のPositionが通常存在するため、`position_state_as_of == business_date`をmembership条件にしてはいけない。

## Repair

修正対象はCurrent Position Membership Temporal Authorityのみ。

Runtime Planningのmembership判定を以下のProduction-common contractへ変更した。

- `position_state_as_of` は必須、かつ `<= business_date`
- `acquisition_date` は存在する場合 `<= business_date`
- `fill_date` は存在する場合 `<= business_date`
- `valuation_as_of` は存在または導出される場合 `<= business_date`
- `source_market_date` は存在または導出される場合 `<= business_date`
- `previous_trading_date` は存在する場合 `<= business_date`
- runtime-owned ownership sourceが必要
- quantityはpositive
- supplied symbol identities must match

Membership mapping:

- same-day fill: `NEWLY_FILLED_PORTFOLIO_MEMBER`
- carry-forward: `CURRENT_PORTFOLIO_MEMBER`

Historical専用分岐、latest fallback、runtime/current lookup、Current Position生成ロジック変更、Persistent Ledger rewriteは行っていない。

## Canonical Reproduction

既存Runを変更せず、`/private/tmp/phase23_bq_canonical_repro` で`2022-07-12`のBP入力を使ったisolated reproductionを実施した。

Before:

- `current_position_business_date_mismatch`
- `strategy_plan_order_side_unresolved`
- Strategy Authority: `REVIEW_REQUIRED`

After:

- Runtime Planning: `PASS`
- Runtime Planning decision resolution: `RESOLVED`
- `23880`: `CURRENT_PORTFOLIO_MEMBER`, `NO_ACTION`
- `94320`: `CURRENT_PORTFOLIO_MEMBER`, `NO_ACTION`
- `94340`: `CURRENT_PORTFOLIO_MEMBER`, `NO_ACTION`
- Strategy Authority: `NO_ORDER_AUTHORIZED`
- Pending valid: `true`
- Pending item count: `0`
- `current_position_business_date_mismatch`: absent

## Required Cases

Covered:

- previous trading day position: PASS
- multi-day position: PASS
- long-held position: PASS
- same-day fill position: PASS
- empty current position path: preserved

Negative fail-closed preserved:

- ownership missing
- non-runtime-owned source
- future position state date
- future acquisition date
- future fill date
- future valuation date
- future market PIT date
- future previous trading date
- symbol mismatch
- quantity mismatch

## Modified Files

- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `tests/strategy/test_phase22_g_runtime_planning.py`
- `tests/runtime_v2/test_phase23_i_strategy_planning_authority.py`

## Evidence

Evidence directory:

`reports/phase23_bq_current_position_membership_temporal_authority_carry_forward_repair/`

Files:

- `root_cause.json`
- `validator_contract.json`
- `temporal_contract_matrix.json`
- `carry_forward_trace.json`
- `authority_trace.json`
- `runtime_planning_trace.json`
- `strategy_authority_trace.json`
- `negative_cases.json`
- `canonical_reproduction.json`
- `previous_regression_check.json`
- `modified_files.json`
- `test_results.json`
- `existing_run_hash_preservation.json`

Machine report:

`reports/phase_reports/phase23_bq_current_position_membership_temporal_authority_carry_forward_repair.json`

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
pytest tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
```

Combined result:

```text
82 passed
```

## Existing Run Preservation

The required existing runs were not mutated.

- `runtime-test-historical-smoke-20260730T094530274138Z`
- `runtime-test-historical-smoke-20260730T090527721192Z`
- `runtime-test-historical-smoke-20260730T082859880393Z`
- `runtime-test-historical-smoke-20260730T080901510234Z`

## Not Executed

- Runtime rerun
- fresh-run
- resume
- Broker Write
- J-Quants fetch
- Persistent Ledger rewrite

## Final Readiness

`READY_FOR_2022_10BD_RUNTIME_RERUN = YES`

Operatorによる2022年10BD Historical Runtime rerunへ進行可能。
