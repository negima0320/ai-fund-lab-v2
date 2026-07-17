# Phase17-BH Current Valuation Refresh Temporal Contract Fix

## 判定

`PHASE17_BH_CURRENT_VALUATION_REFRESH_TEMPORAL_CONTRACT_ACCEPTED`

本PhaseではFrozen Run `runtime-test-historical-smoke-20260715T111433056797Z` に対して `runtime_test.py run/resume/reset/rollback/backup/close` は実行していない。`.runtime` のLedger / Current / Pendingは手動変更していない。修正と検証はコード、およびpytestの隔離runtime rootで実施した。

## Root Cause

Day2 `2026-07-07 current_valuation_refresh` は、producer実行前のData Readiness Gateで停止していた。Run Evidenceでは `execution_reached=false`、`blocking_stage=runtime_data_readiness_gate`、`blocking_reason=current_valuation_not_ready` で、Current Valuation producer本体には到達していない。

停止時のLedgerは以下の正常なpre-refresh状態だった。

```text
ledger.business_date = 2026-07-06
ledger.valuation_as_of = 2026-07-06
ledger.source_market_date = 2026-07-06
ledger.current_valuation_status = READY
```

しかし `readiness_scope=current_valuation` のGateが、当日評価を作るproducerの実行前に、既存Ledgerがすでに `2026-07-07` 終値評価済みであることを要求していた。

```text
current_valuation_expected_date_policy = business_date_close
current_valuation_temporal_authority = stale_current_valuation
current_valuation_temporal_reason = current_valuation_not_business_date_close
```

これは「当日評価を生成するジョブが、実行前に当日評価済みであることを要求する」循環依存だった。

## Day1では通りDay2で停止した理由

Day1 `2026-07-06` は初回のexecution / valuation refreshにより、同日評価が作成され、その後のruntime_state_refreshまで通過した。

Day2 `2026-07-07` のrefresh直前では、前営業日 `2026-07-06` のvaluationが正式な既存Currentであり、当日Quote authorityはREADYだった。この状態はCurrent Valuation producerの正常な入力だが、修正前Gateはこれをstale扱いしたためDay2で露出した。

## 修正前の循環依存

修正前:

```text
readiness_scope=current_valuation
  -> existing valuation_as_of must equal business_date
  -> previous close valuation is REVIEW_REQUIRED
  -> producer never reaches projection/apply
```

修正後:

```text
readiness_scope=current_valuation
  -> existing valuation_as_of == previous_trading_date is READY precondition
  -> target quote/market authority remains required
  -> producer projects business_date valuation
  -> apply requestedならpostconditionでbusiness_date valuationを厳格検証
```

## 共通Runtime Contract

Production / Demo / Historical共通で、`current_valuation_refresh` scopeはpreconditionとpostconditionを分離する。

Precondition:

- 既存Current valuationが `business_date` ならREADY
- 既存Current valuationが `previous_trading_date` なら `current_valuation_previous_close_ready_for_refresh` としてREADY
- 前営業日より古いvaluationはREVIEW_REQUIRED
- future valuationはHALT
- `source_market_date != valuation_as_of` はREVIEW_REQUIRED
- valuation evidence欠落はREVIEW_REQUIRED

Producer / Projection:

- 当日market/quote authorityがREADYであることを要求
- 保有銘柄Quote欠落、Quote date不一致、price不正、source欠落はREVIEW_REQUIRED
- Historical as-of viewは対応schemaと `normalized_ohlcv` authorityから同一business dateのQuoteだけを使用する

Apply / Postcondition:

- `--apply-current-valuation` 指定時のみCurrentへ適用
- 適用後に `business_date`、`valuation_as_of`、`source_market_date`、position別valuation date / price / market_value、total market value、total equityを検証
- postcondition不一致は `current_valuation_postcondition_failed` としてfail-closed

## Evidence Fields

Current Valuation manifest / Run Evidenceへ次を追加または伝播した。

- `valuation_refresh_precondition_status`
- `existing_valuation_as_of`
- `previous_trading_date`
- `target_valuation_date`
- `valuation_refresh_action`
- `projection_status`
- `projection_source_market_date`
- `apply_status`
- `post_apply_valuation_as_of`
- `post_apply_source_market_date`
- `postcondition_status`
- `postcondition_reason`
- `temporal_authority`
- `temporal_reason`

## 15:35 / 15:40時刻契約

結論: Historical smokeの `15:35 current_valuation_refresh` は維持する。

理由:

- Historical replayでは、同日の `market_refresh` がrun-scoped historical as-of viewを生成済みであり、Current Valuation producerはそのPIT/as-of authorityから当日business dateのQuoteだけを読む。
- `15:40 runtime_state_refresh` はvaluation適用後の状態公開チェックポイントであり、Historical replayのQuote利用可能性を初めて成立させるGateではない。
- 修正後は `current_valuation_close_confirmed` を時刻ベースで表現し、15:35ではfalseになる。一方、refresh scopeではclose confirmationそのものではなく、明示されたmarket/quote/as-of authorityがprojection authorityになる。

これにより、15:35時点で将来情報を無条件に読むのではなく、Historical market_refreshが作ったrun-scoped PIT/as-of evidenceを正式Authorityとして読む契約に分離した。

## 変更ファイル

- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py`
- `tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`
- `tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py`

## fail-closed維持

以下は引き続きPASSしない。

- 前営業日より古いvaluation
- business_dateよりfuture-datedなvaluation
- `valuation_as_of` と `source_market_date` の不一致
- 当日Quote欠落
- 一部保有銘柄Quote欠落
- Quote date mismatch
- Projection不完全
- apply要求時にLedgerが更新されない
- apply後も `valuation_as_of` / `source_market_date` がbusiness_dateにならない
- position market value / total equity不整合

## Production / Demo / Historical影響

今回の修正はHistorical専用分岐ではない。Current Valuation producerの共通時間契約として、前営業日valuationをrefresh前の正常preconditionとして扱い、当日評価の成立はproducer projection/apply/postconditionで検証する。

環境差はbroker write、external delivery、Historical as-of authorityなど外部作用と入力authorityに限定される。Safety、Current、Temporal policy、postcondition fail-closedはProduction / Demo / Historical共通で維持される。

## 既存Runのresume可否

既存RunはDay2 `current_valuation_refresh` のGateで停止しており、Day2 submit / executionはresumeでPASS済み、PendingはEMPTY/no-action terminal、Ledgerは `2026-07-06` valuationのままだった。修正後の契約では、このLedger状態はDay2 refreshの正常preconditionである。

したがってコード上は同Runの `current_valuation_refresh` からresume可能と判断する。ただし本Phaseではresumeは実行していない。

参考Operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --run-id runtime-test-historical-smoke-20260715T111433056797Z \
  --confirm
```

## 実行テスト

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py \
  tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py \
  tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py \
  tests/runtime_v2/test_phase15az_current_valuation_no_fill_producer.py \
  tests/runtime_v2/test_phase17_aa_historical_current_valuation_authority.py \
  -q

38 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_bf_empty_pending_submit_contract.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py \
  -q

26 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_bh_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/data_readiness.py \
  src/ai_fund_lab_v2/runtime_v2/current_state/valuation.py \
  src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py \
  tests/runtime_v2/test_phase17_bh_current_valuation_refresh_temporal_contract.py \
  tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py \
  tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py
```

PASS:

```text
git diff --check
```

## 禁止操作未実施

未実施:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py backup`
- `runtime_test.py close`
- `.runtime` の手動編集
- Frozen Run Evidenceの手動編集
- Broker write
- Tachibana API write
- 外部通知送信
- J-Quants API fetch

## 最終判定

`PHASE17_BH_CURRENT_VALUATION_REFRESH_TEMPORAL_CONTRACT_ACCEPTED`
