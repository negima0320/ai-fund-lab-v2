# Phase12-L Feature / Candidate Path Audit & Daily Report Stale Artifact Fix

## Status

`PHASE12L_FEATURE_CANDIDATE_PATH_AND_REPORT_STALE_FIX_COMPLETE`

Phase12-Kで残った以下2点を、Demo Order Wire Executionを解禁せずに調査し、必要最小修正した。

- Daily Reportが同日過去artifactの`submit_status=BLOCK`を当日最新状態として扱う問題
- BUY=0 / `candidate_no_universe_eligible_rows`の原因分解

## Prohibited Actions

以下は実施していない。

- Demo Order Wire Execution
- Demo注文
- Production注文
- Production Unlock
- LINE実送信
- AI再学習
- Backtest再実行
- raw broker response保存
- secrets保存
- Phase9 artifact / launchd / CLI / moduleの破壊的変更

Phase12-L中にJ-Quants APIおよびBroker Demo read-only APIは呼び出していない。既存のPhase12-K artifactを用いて軽量確認した。

## Daily Report Stale Artifact

### Cause

`.runtime/operations/daily_manifest/2026-06-29/daily_manifest.json`に、同日内の過去runで生成された`submit_status=BLOCK`が履歴として残っていた。

`run_daily_report.py`は同日のmanifest / artifactを集約する際、古い`submitted_orders` artifactの`BLOCK`を現在状態として扱っていた。そのため、最新の`order_plan`ではDemo Submitが実行対象ではないにもかかわらず、Daily Reportが`BLOCK`へ寄っていた。

確認した時系列は以下。

- 最新`order_plan.created_at`が存在する
- 既存`submitted_orders.created_at`はそれより古い
- 古い`submit_status=BLOCK`が履歴として残存
- Daily Reportが履歴BLOCKと現在run状態を分離できていなかった

### Fix

`run_daily_report`にcurrent-run viewを追加した。

- `_collect_operation_statuses(...)`は履歴を含む従来の参照として保持
- `_current_operation_statuses(...)`を追加し、`submitted_orders.created_at < order_plan.created_at`の場合は`submit=STALE_IGNORED`へ分類
- Daily Report refsに`current_operation_statuses`と`stale_artifact_policy`を保存
- daily manifestの現在状態では、古い`submit_status=BLOCK`を`STALE_IGNORED`として扱う

古いBLOCK artifactは履歴として削除せず、当日最新状態として誤表示しないようにした。

### Result

- Daily Report status: `PASS`
- Current submit status: `STALE_IGNORED`
- Stale submit policy: `submitted_orders.created_at older than order_plan.created_at is history, not current run state`

## Feature / Candidate Path Audit

### Current Feature Path

`run_daily_plan.py`相当のOperations daily planは、以下のfeature artifactを参照している。

- Candidate feature path: `.runtime/operations/feature_artifacts/2026-06-26/candidate_features.parquet`
- Opportunity feature path: `.runtime/operations/feature_artifacts/2026-06-26/opportunity_feature_input.parquet`
- Feature data until: `2026-06-26`

Feature artifact自体は存在し、daily planから読めている。

### Counts

| Item | Count |
| --- | ---: |
| J-Quants raw rows | 88,930 |
| canonical normalized rows | 84,307 |
| feature rows | 4,280 |
| universe rows before hard gate | 4,280 |
| universe rows after hard gate | 0 |
| candidate count | 0 |
| opportunity count | 4,280 |
| BUY order plan count | 0 |

### BUY Zero Reason

`BUY=0`の直接理由は以下。

`candidate_no_universe_eligible_rows`

Feature artifact欠落やdaily planの参照パス不一致ではなく、candidate universe hard gate後にeligible rowが0件になっている。

除外理由の内訳は以下。

| Exclusion reason | Count |
| --- | ---: |
| insufficient_lookback | 3,687 |
| insufficient_lookback,disallowed_product | 514 |
| insufficient_lookback,stale_price | 33 |
| insufficient_lookback,stale_price,disallowed_product | 25 |
| insufficient_lookback,not_current_listed,missing_name,stale_price,disallowed_product | 17 |
| insufficient_lookback,not_current_listed,missing_name,disallowed_product | 4 |

既存artifactでは、hard gateの主要原因が`insufficient_lookback`に偏っている。

## Fixes

必要最小修正として以下を実施した。

- Daily Reportでcurrent runのstatus viewを明示
- staleなsubmit artifactを履歴として残しつつ、現在状態から除外
- Feature / candidate path診断を`feature_candidate_audit`として保存
- Daily Plan artifactに`feature_candidate_audit`を追加
- Operation Auditにfeature / candidate診断を追加
- BUY zero reasonを詳細化
- OperationsのJ-Quants default lookbackを45日から140 calendar daysへ拡張

140日にした理由は、candidate hard gateが十分なlookbackを要求している一方、既存の45日相当のrefreshでは`insufficient_lookback`により候補が全滅していたため。AI再学習やBacktest再実行は行っていない。

## Smoke Results

既存artifactを用いて軽量smokeを実施した。

```bash
python3 scripts/run_daily_plan.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_daily_report.py --trade-date 2026-06-29 --root .runtime/operations
python3 scripts/run_operation_audit.py --root .runtime/operations
```

結果:

- `run_daily_plan.py`: PASS
- `run_daily_report.py`: PASS
- `run_operation_audit.py`: PASS

`run_market_refresh.py`はPhase12-Lではネットワークrefreshを再実行していない。次フェーズでread-only refreshとして実施する。

## Tests

```bash
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=.runtime/operations/pycache_phase12l python3 -m py_compile scripts/run_daily_report.py scripts/run_daily_plan.py scripts/run_operation_audit.py src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/market_refresh.py
python3 -m json.tool reports/phase_reports/phase12l_feature_candidate_path_and_report_stale_fix.json
```

結果:

- `tests/phase12`: 33 passed
- `py_compile`: PASS
- JSON validation: PASS

## Remaining Gaps

- 既存artifact上ではBUYはまだ0件
- 原因はcandidate hard gate後のeligible rowsが0件で、主因は`insufficient_lookback`
- default lookbackは140日に修正済みだが、Phase12-LではJ-Quants refreshを再実行していない
- Demo Wire Unlock前に、140日lookbackでread-only refreshを行い、candidate hard gate後のeligible rowsが復元するか確認する必要がある

## Next Phase

`PHASE12-M_LONGER_LOOKBACK_READONLY_REFRESH_AND_BUY_SIGNAL_CONFIRMATION`

推奨する次タスク:

1. Demo / Production注文なしで`run_market_refresh.py`をread-only再実行する
2. `feature_data_until=2026-06-26`以降のfeature artifactを140日lookbackで再生成する
3. candidate universe hard gate後のeligible rowsを確認する
4. BUY candidate / opportunity / BUY order plan countを再確認する
5. Daily Reportがstale submit BLOCKを現在状態として扱わないことを再確認する
6. 条件PASS後にDemo Wire Unlock設計レビューへ進む
