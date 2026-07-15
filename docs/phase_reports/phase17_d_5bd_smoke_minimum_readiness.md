# Phase17-D 5BD Historical Runtime Smoke Test Minimum Readiness

## 1. 読み込んだ資料
- `docs/phase_reports/phase17_test_scope_and_readiness_review.md`
- `reports/phase_reports/phase17_test_scope_and_readiness_review.json`
- `docs/phase_reports/phase17_b1i_c_canonical_historical_data_gap_analysis.md`
- `reports/phase_reports/phase17_b1i_c_canonical_historical_data_gap_analysis.json`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- `docs/02_architecture/operational_data_architecture.md`
- `docs/phase_reports/phase17_b1i_a_historical_environment_composition.md`
- `docs/phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.md`
- `docs/phase_reports/phase17_b1i_br_registry_recovery_architecture_review.md`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/baseline.py`

## 2. 5BD Window Manifest
- 対象: `2026-07-06` から `2026-07-10`
- Manifest: `reports/phase17_d_5bd_smoke_minimum_readiness/5bd_window_pit_manifest.json`
- Manifest hash: `087016b926f3d94d40ed875593785a5c9773790a0b82f6300838d0aebe2bd69e`
- 状態: `PASS_CREATED`
- 含有項目: `business_date`, `calendar_as_of`, `listed_issues_as_of`, `universe_as_of`, `feature_cutoff`, `decision_cutoff`, `valuation_as_of`, `fill_cutoff`, `source_hashes`, `manifest`

## 3. Calendar
- Authority: `J-Quants trading_calendar raw parquet`
- Weekday fallback: `false`
- Source: `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet`
- Hash: `83dae980628a28c7592c07d4ab8c6c74271491d420b01578fa8a6ccafd6043ec`
- 判定: `PASS_5BD_CALENDAR_AUTHORIZED`

## 4. Listed Issues
- Authority: `J-Quants listed_issues raw parquet as-of <= business_date`
- Current Listed Issues の過去流用: `false`
- Source: `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet`
- Hash: `a02f4afd0f2bd31f2fdd1512c0e74e8251e6ce497d28a31c867efd12f31ed733`
- 判定: `PASS_5BD_LISTED_UNIVERSE_AUTHORIZED`
- 注記: `2026-07-08` は exact row がなく、`2026-07-07` as-of の PIT universe として確定。

## 5. PIT
- Window 限定 PIT Manifest を作成済み。
- `calendar_as_of`, `listed_issues_as_of`, `universe_as_of`, `selected_feature_as_of` を各営業日で明示。
- 2021年以降の全期間 PIT 完備は今回対象外。

## 6. Corporate Action Guard
- Method: 5BD window の raw OHLCV `AdjFactor` が全て `1.0` であることを no-impact として確認。
- Source: `.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet`
- Hash: `b9f67ae5e67d0764d011e6530ef88842d9b891f964a49325960535f4b103f6bd`
- 判定: `PASS_NO_EVENT_OR_NO_IMPACT_FOR_5BD_WINDOW`

## 7. Historical Fill Price
- 最小仕様は `reports/phase17_d_5bd_smoke_minimum_readiness/historical_fill_price_minimum_contract.json` に定義。
- 価格Source、Fill日時、Fill Price、Market/Limit、Lot、Tick、Duplicate防止、Insufficient cash/quantity を定義済み。
- ただし現行 `HistoricalSubmitAdapter` は fill model 未受理として `NOT_IMPLEMENTED_BLOCKING` で fail-closed するため、5BD開始前の残ブロッカー。

## 8. Carryover採用可否
- 判定: `2026-07-09` を正式 Smoke Test の `Carryover Scenario` として採用可能。
- Evidence: `.runtime/operations/feature_date_contract/2026-07-09.json` / `.runtime/operations/feature_refresh/2026-07-09/latest_features.json`
- Policy: 2026-07-09 の穴埋め Feature 生成は行わない。

## 9. Reset Dry Run
- Dry Run manifest: `reports/phase17_d_5bd_smoke_minimum_readiness/reset_dry_run_manifest.json`
- Reset executed: `false`
- Current / Ledger / Pending / Runtime State の hash と reset plan / validation を記録。
- 判定: `PASS_DRY_RUN_ONLY`

## 10. Entry Gate一覧
- `Runtime Mainline`: `PASS_BY_CONTRACT`
- `Historical Composition`: `PASS_BY_CONTRACT`
- `PM Authority`: `PASS_BY_PHASE17_B1I_B_BR`
- `Registry`: `PASS_BY_PHASE17_B1I_BR`
- `OHLCV`: `PASS_5BD_WINDOW_AVAILABLE`
- `Trading Calendar`: `PASS_5BD_CALENDAR_AUTHORIZED`
- `Listed Issues`: `PASS_5BD_LISTED_UNIVERSE_AUTHORIZED`
- `PIT Manifest`: `PASS_CREATED`
- `Corporate Action Guard`: `PASS_NO_EVENT_OR_NO_IMPACT_FOR_5BD_WINDOW`
- `Historical Fill Price`: `BLOCK_SPECIFIED_BUT_NOT_ACCEPTED_BY_RUNTIME`
- `Reset Dry Run`: `PASS_DRY_RUN_ONLY`
- `Regression Baseline`: `PASS_COLLECTED`

## 11. Blocking
- `historical_fill_price_runtime_acceptance`: Minimum fill price contract is documented, but the current HistoricalSubmitAdapter still fails closed with NOT_IMPLEMENTED_BLOCKING until a historical fill model is accepted/executable.

## 12. Non-blocking
- `2026_07_08_feature_marker_review`: 2026-07-08 has exact feature artifact files, while its feature_date_contract/latest marker records carryover from 2026-07-07. Phase17-D does not regenerate features; 5BD should respect existing runtime markers unless explicitly re-planned.
- `full_corporate_action_support`: 5BD window passes no-impact guard via AdjFactor=1.0; full CA modeling remains outside this smoke scope.
- `fees_tax_slippage_partial_fill`: Minimum smoke contract uses zero-fee, zero-tax, zero-slippage, all-or-none fills.

## 13. 作成・更新ファイル
- `docs/phase_reports/phase17_d_5bd_smoke_minimum_readiness.md`
- `reports/phase_reports/phase17_d_5bd_smoke_minimum_readiness.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/5bd_window_pit_manifest.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/calendar_authority.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/listed_universe_authority.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/corporate_action_guard.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/historical_fill_price_minimum_contract.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/carryover_scenario.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/reset_dry_run_manifest.json`
- `reports/phase17_d_5bd_smoke_minimum_readiness/entry_gates.json`

## 14. 実行した検証
- Read-only parquet/date/hash inspection for 2026-07-06..2026-07-10
- Reset plan build + validate dry run only
- Regression baseline collection only
- JSON report serialization and re-read validation

## 15. 実行していない操作
- `5BD execution`
- `Trading State Reset`
- `Current mutation`
- `Ledger mutation`
- `Pending mutation`
- `Runtime State mutation`
- `Feature generation`
- `Canonical update`
- `Historical Runtime execution`
- `Submit`
- `Execution`
- `J-Quants fetch`
- `Demo`
- `Production`

## 16. 最終判定
`PHASE17_D_FILL_CONTRACT_REQUIRED`

理由: 5BD window の PIT、Calendar、Listed Issues、Corporate Action Guard、Carryover Scenario、Reset Dry Run、Regression Baseline は最低限の形で揃った。一方で、Historical Fill Price は仕様を定義しただけで、現行 runtime の historical submit/execution はまだ accepted fill model として通らない。

## 17. Recommended Next Prefix
- PASS 条件を満たした場合の次 Prefix: `Phase17-E`
- Work Name: `Historical Runtime 5BD Smoke Test`
- 現時点の推奨: `Phase17-E` へ進まず、先に Historical Fill Price の runtime acceptance を解消する。
