# Phase23-BS PM ADD Pending Submit Policy Authority Binding Repair

## Primary Judgment

`PHASE23_BS_PM_ADD_PENDING_SUBMIT_POLICY_AUTHORITY_SHORT_VALIDATION_PASS`

Phase23-BRで確定した `PM_ADD_PENDING_SUBMIT_POLICY_AUTHORITY_MISSING` / `missing_submit_policy_evidence` を、Production / Demo / Historical 共通のPending生成契約として修正した。

長時間Runtime、fresh-run、resume、Broker Write、J-Quants取得、既存Run artifact mutationは実施していない。

## Root Cause

2022-07-12のPM ADD経路では、`runtime_v2.planning.sell_pipeline` が `94320 BUY 100 ADD` のPendingを生成していたが、canonical Submit Policy Authorityを order plan / pending payload / approval / pending item へ渡していなかった。

Submit Guardは `runtime_v2.submit.pipeline._missing_policy_evidence_reason()` で `missing_submit_policy_evidence` と判定し、fail-closedした。Guard動作は正しいため、Guard緩和は行っていない。

## 修正内容

- `run_sell_planning_pending_pipeline()` が `submit_policy_context` を受け取り、PM ADD / SELL混在Pendingへ同一のSubmit Policy Authorityを付与するようにした。
- direct caller向けに、producer scopeにある `CapitalDeploymentPolicy` からcanonical `submit_policy_context` をmaterializeできるようにした。latest fallbackではなく、呼び出し時に渡されたpolicy objectから `capital_deployment_policy_hash()` で算出する。
- `_write_add_pending()` が `pm_add_order_plan.json`、`promote_order_plan_to_pending()`、`PendingOrderItem` へ `submit_policy_version/source/hash` を渡すようにした。
- Runtime daily operationのsell planning wiringから、Strategy Planning Authorityと同じSubmit Policy Authority payloadを渡すようにした。
- PM ADD 2022-07-12 isolated reproductionを追加し、order plan / pending / approval / item / Submit Guard observed policy consistencyを検証した。

## Canonical Submit Policy Owner

- Canonical owner: `CapitalDeploymentPolicy`
- Canonical hash: `capital_deployment_policy_hash(policy)`
- Canonical context: `submit_policy_context`
- Canonical fields: `submit_policy_authority`, `submit_policy_schema_version`, `submit_policy_version`, `submit_policy_source`, `submit_policy_hash`
- Canonical consumers: pending promotion, approval request/artifact, pending item, submit policy consistency guard

PM ADD専用schemaや固定hashは作成していない。

## Contract確認結果

`canonical submit policy == PM ADD order plan == pending payload == approval == pending item == Submit Guard observed policy` の version/source/hash 一致を短時間検証で確認した。

Submit Guard strict validationは変更していない。missing / mismatch / planning lineage missing は引き続き `REVIEW_REQUIRED` / `BLOCKED`。

## 2022-07-12再現

Isolated reproduction:

`tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py::test_phase23_bs_pm_add_pending_submit_policy_authority_reaches_submit_guard`

確認結果:

- business_date: `2022-07-12`
- pending_plan_id: `pending-order-plan-pm-add-2022-07-12`
- symbol: `94320`
- side: `BUY`
- quantity: `100`
- source_decision_type: `ADD`
- `submit_policy_hash`: order plan / pending / approval / itemで一致
- `submit.submit_policy_consistency.policy_consistency_status = PASS`
- `missing_submit_policy_evidence = absent`

なお、demo modeでは `94320` が既存の9000番台broker capability preflightにより `symbol not supported by broker capability` で止まる。このpreflightはBS対象外で、Submit Policy Authorityはその前段でPASSしている。Guard緩和やbroker capability変更は行っていない。

## Producer Responsibility

PM ADDは現在 `sell_pipeline` stageで生成される。理由は、Position Management由来のADDとSELL/REDUCE/EXITを、current position lifecycleとactive pending continuityの同じ境界で処理しているため。

分類:

`RESPONSIBILITY_OVERLAP_NON_BLOCKING`

命名はlegacyで誤解を招くが、今回の直接原因ではないためcomponent移動やrenameは行っていない。

## 短時間テスト

PASS:

- `py_compile`
- PM ADD order plan policy binding
- pending payload policy binding
- approval policy propagation
- pending item policy propagation
- Submit Guard PM ADD policy consistency
- missing / mismatch negative fail-closed
- BUY_NEW regression
- BUY_ADD regression
- SELL_REDUCE / SELL_EXIT regression
- BI import boundary regression
- Machine report / 16 evidence JSON validation

代表コマンド:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase23_bs python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_bi_buy_ai_import_boundary.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
```

Result:

`60 passed in 5.44s`

## 修正対象ファイル

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py`

## 成果物

- Human: `docs/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.md`
- Machine: `reports/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.json`
- Evidence: `reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair/`

## Existing Run Preservation

以下の既存Runは読み取りhash evidenceのみ作成し、artifact mutationは行っていない。

- `runtime-test-historical-smoke-20260730T110025619692Z`
- `runtime-test-historical-smoke-20260730T094530274138Z`
- `runtime-test-historical-smoke-20260730T090527721192Z`
- `runtime-test-historical-smoke-20260730T082859880393Z`
- `runtime-test-historical-smoke-20260730T080901510234Z`

## Remaining Gaps

BS範囲内の既知blockerなし。

demo broker capabilityでは9000番台注文がpreflight blockされるが、これはSubmit Policy Authority欠損とは独立の既存制限であり、今回変更していない。

## Next Operator Action

`READY_FOR_2022_10BD_RUNTIME_RERUN = YES`

Operatorによる2022年10BD Runtime rerunへ進める。Codexでは10BDを実施していない。
