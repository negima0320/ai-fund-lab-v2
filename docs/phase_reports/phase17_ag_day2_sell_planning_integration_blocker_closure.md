# Phase17-AG Day2 Sell Planning Integration Blocker Closure

## 判定

`PHASE17_AG_DAY2_SELL_PLANNING_INTEGRATION_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T033642388389Z` は変更・resume・再実行していない。

## Frozen Evidence

Day2 `2026-07-07:sell_planning` は exit code `20` / `REVIEW_REQUIRED`。表面理由は `pending_order_plan UNKNOWN` だが、Data Readiness authorityの実原因は以下。

- `current_valuation_not_ready`
- `historical_safety_temporal_authority_missing`
- `pm_feature_artifact_missing`

## Root Cause

Morning no-signal Pending生成経路が `environment=demo` を固定し、items 0件でも `PENDING_APPROVAL` を作っていた。Historical replayの正式環境は `historical` / `historical_simulated` であり、このPendingは承認対象を持たないため既存terminal state `EMPTY` として扱うべきだった。

また no-signal Pendingの `safety_context` には `runtime_test_run_id`、`runtime_test_profile_id`、`runtime_test_evidence_root`、`safety_authority`、`safety_business_date` が不足していた。Phase17-AFで確立したfail-closed historical safety authorityをno-signal Pendingにも伝播する必要があった。

PM input resolverはFeature Consumer ReadinessがREADYにした `position_feature_input.parquet` を使わず、空pathから `"."` をsourceとして扱っていた。PM opportunityはPosition Management AI inferenceが必要とするBUY AI `opportunity_rankings.json` を正式sourceとする。

sell_planningは `2026-07-07T08:40:00+09:00` の朝ジョブであり、当日終値は未存在。Current ValuationはMorningと同じく前営業日closeまたは当日refresh済みvaluationをREADYとする。

## 修正

- sell_planning scopeのCurrent Valuation temporal policyを `morning_previous_close_or_same_day` に統一
- PM featureをFeature Date Contractの `generated_feature_artifacts.position_feature_input.parquet` から解決
- PM opportunityをRuntime BUY AI `runtime_state/buy_ai/{feature_date}/opportunity_rankings.json` から解決
- PM producerも明示path未指定時に同じ正式sourceへ解決
- no-signal PendingのenvironmentをRuntime modeから伝播
- no-signal Pendingを既存terminal state `EMPTY` / `active_pending=false` として保存
- no-signal Pendingにもhistorical safety authority fieldsを伝播
- `EMPTY` no-action pendingのhistorical safety authorityをfail-closedで検証

Historical専用の通過例外、Runtime Test専用fallback、cwd fallbackは追加していない。`runtime_test_run_id` / `runtime_test_profile_id` / `runtime_test_evidence_root` はrun-scoped evidence identityであり、売買許可条件ではない。存在する場合は整合性を検証するが、Production Runtime契約はそれらが存在しなくても成立する。Historical capabilityも `historical-smoke` profile名に依存しない。

## Production Impact

Production Runtimeへ適用される共通契約:

- no-signal / no-action Pendingは `EMPTY` / `active_pending=false`
- no-signalは承認不要、Submit不要、Execution不要、自動再送禁止
- sell_planningは朝ジョブとして previous trading day close または same-day refreshed valuation を受け入れる
- PM featureはFeature Date Contractの正式artifact pathから解決
- PM opportunityはRuntime BUY AI `opportunity_rankings.json` から解決
- Pending environment mismatchはREVIEW_REQUIRED

Historical限定部分:

- broker write / external delivery禁止
- historical safety authorityのrun-scoped identityはEvidenceとして保持されるが、READY条件そのものではない

Demo限定部分:

- demo broker capability / demo broker environment
- payload-only notification readiness

外部作用以外に残る環境分岐:

- Historicalの初期空Current authorityは、外部Broker stateを使わないreplay初期状態のための限定contract
- Production/Demo/HistoricalでPending lifecycle、PM feature schema、Current valuation temporal policyは共通

Production事故を防ぐfail-closed条件:

- unknown lifecycle state
- pending environment mismatch
- authority path missing
- artifact hash mismatch
- business date mismatch
- future-dated valuation
- stale valuation
- PM symbol mismatch
- Safety policy mismatch
- 不明なCurrent position state

本番運用開始前に未検証の事項:

- 実Tachibana production broker snapshotとの口座整合
- production submit直前のlive safety decision更新
- accepted PM `RUNTIME_ADAPTER` hashの再acceptance
- 実市場休日カレンダーのproduction source固定

## Verification

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py`
  - `6 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py`
  - `17 passed`
- `PYTHONPYCACHEPREFIX=/private/tmp/phase17ag_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/data_readiness.py src/ai_fund_lab_v2/runtime_v2/position_management/producer.py src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py`
  - PASS

補足: Phase15APの直接PM producer回帰は `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` accepted-current-path hash mismatchでHALTする。これは既存のPM adapter registry identity guardであり、今回のFrozen Day2 sell_planning Data Readiness blockerとは別系統のaccepted artifact identity課題として記録した。
