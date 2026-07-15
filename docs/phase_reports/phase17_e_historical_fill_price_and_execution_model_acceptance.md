# Phase17-E Historical Fill Price and Minimal Execution Model Acceptance

## 1. 読み込んだ資料
- `docs/phase_reports/phase17_test_scope_and_readiness_review.md` sha256=`3f7e6ab46c59eb419eb3f8e4aa26d51d1d93c19a527860c0a85e3eb9c7b0139a`
- `reports/phase_reports/phase17_test_scope_and_readiness_review.json` sha256=`a7688c8a788f2d067c7d7108df156afef825866225b7303285c5571d3881ed87`
- `docs/phase_reports/phase17_d_5bd_smoke_minimum_readiness.md` sha256=`f2e4bc3f3366d4cf44485459337e2f58d50ec91825fe9f7df47e0f509277753b`
- `reports/phase_reports/phase17_d_5bd_smoke_minimum_readiness.json` sha256=`a7a659fb9e263c5cb02b5ead1cb8bfffbe262d918d1d2d008ca31acd307821a3`
- `docs/phase_reports/phase17_b1i_a_historical_environment_composition.md` sha256=`9e3db2cc5f5dd3a14026ceeae17779581c8cfb8968ebf987fd94155251f509cc`
- `reports/phase_reports/phase17_b1i_a_historical_environment_composition.json` sha256=`56795ae9ad4ecf7463534fcd0c0c7a724540cac40f7e3ee6e2b2272898e3a149`
- `docs/phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.md` sha256=`e4dece453294816aaa7b8840366fba34bcae920ecee54985934b083f4f4353c9`
- `reports/phase_reports/phase17_b1i_b_pm_adapter_authority_resolution.json` sha256=`09a3343412c02011d02c1d2c06277d0f649406c2e505ef1d0576a74ff895bbb0`
- `docs/phase_reports/phase17_b1i_br_registry_recovery_architecture_review.md` sha256=`a9fa62d563900b18e9729b733169686ba81e74012bf908326989d9f9bf50953a`
- `reports/phase_reports/phase17_b1i_br_registry_recovery_architecture_review.json` sha256=`183bef9bc3f8f07811fdee0d177082109b427aea3a8043adf1ed02bc93cebd9d`
- `docs/02_architecture/historical_runtime_test_contract.md` sha256=`13695d7421533c912a011d5af13c9cf62ea5bd1c14426517a8ba20a3985e4b06`
- `docs/02_architecture/runtime_architecture_v2.md` sha256=`45b6d90a5da40804b118f7a7ae8e045158d57fa3b57066540b94ba603ddf8849`
- `docs/02_architecture/runtime_temporal_freshness_contract.md` sha256=`b3ab425b6714971441836bee7cf210366b2c9a60a2b81603a91e4ffb4577a6b1`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md` sha256=`3ad5e36bca61937e3f28be16e00357695edbc1299a5c6a6829d1f32a23199093`
- `reports/phase17_d_5bd_smoke_minimum_readiness/5bd_window_pit_manifest.json` sha256=`087016b926f3d94d40ed875593785a5c9773790a0b82f6300838d0aebe2bd69e`
- `reports/phase17_d_5bd_smoke_minimum_readiness/calendar_authority.json` sha256=`b0a7720a39c4d70a95c0b43e1f14d34d792365b58d37e1e7ffaf89479d28c76c`
- `reports/phase17_d_5bd_smoke_minimum_readiness/listed_universe_authority.json` sha256=`46d26c5e10e3182cc435d2c8bc9969244ce2bd1ccc1fa700fe33985f75198d0a`
- `reports/phase17_d_5bd_smoke_minimum_readiness/corporate_action_guard.json` sha256=`ac5f4f3b7785bbda08cd9bec101b90b2a0ff985759efe80732ce0952b9094a4a`
- `reports/phase17_d_5bd_smoke_minimum_readiness/historical_fill_price_minimum_contract.json` sha256=`a60528e22265d3f12c2a1cc54719d3cab0655ecc60807a783376727f48bec546`
- `reports/phase17_d_5bd_smoke_minimum_readiness/carryover_scenario.json` sha256=`63119da316b8a13fc4f3818a0510334b79b986508f51cea5d085feef903dcf22`
- `reports/phase17_d_5bd_smoke_minimum_readiness/reset_dry_run_manifest.json` sha256=`9576b47704532236fb39d97bc74c61015e6ea09aaa8da6f87a6dafb547614a68`
- `reports/phase17_d_5bd_smoke_minimum_readiness/entry_gates.json` sha256=`968a25acd7dfd6a510fcea40e5b97e584522fc9fdacd8f76bc6091b9c97a9df8`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py` sha256=`2c7b57af7c3346c49b42e9171d417e757a9c2b7ad99a76ecc0766f0af5fc511c`
- `src/ai_fund_lab_v2/runtime_v2/simulation/broker.py` sha256=`629bcbc55d0aa4c82cb947b5e989d5be21d0cc79f3daa7e6d755cb3e55dbdfea`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py` sha256=`e4e0ae4e9e6c9d5111666eb11838c401e8e68486b06d547b49d043f2f51071c2`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py` sha256=`aabac3752c52576c21f4422675e069990f590865eddfdaefd8a8d74d9a7df387`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` sha256=`fa67407e671ca4b17360d368781a5a23bd78220b42faaef840ad43beacc746f0`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py` sha256=`2a80703b58c25373223e9a9209748bfd37f6f273b63a8d26b00cc8c0c28a819e`
- `src/ai_fund_lab_v2/runtime_v2/execution/models.py` sha256=`695de5f4396d6d4ea9ab24d8e9edfdddbfbac520913a909ad7add52a4e859da0`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` sha256=`e56963ff65488763ee58091028ed29a7a5027d6cc7a390568786cb109b327f0a`

## 2. Fill Price Authority
- 判定: `AUTHORITY_DETERMINED_NOT_RUNTIME_ACCEPTED`
- Source: `J-Quants daily OHLCV normalized parquet, Phase17-D 5BD Window PIT Manifest`
- Physical path: `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`
- Source hash: `c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d`
- Price rule draft: target session Open, no fallback, no future/close substitution.

## 3. Market BUY / SELL rule
- BUY: `DRAFT_RULE_NOT_RUNTIME_ACCEPTED` - BUY market order fills all-or-none at target_session Open only when price, universe, lot/trading unit, cash, duplicate, and source-hash checks pass.
- SELL: `DRAFT_RULE_NOT_RUNTIME_ACCEPTED` - SELL market order fills all-or-none at target_session Open only when price, universe, lot/trading unit, owned quantity, duplicate, and source-hash checks pass.

## 4. Target Session rule
- `target_session_date must equal Submit Pipeline business_date; no alternate target session resolution.`
- ただし runtime acceptance は Submit Guard blocker 解消後。

## 5. Lot / Tick rule
- Lot: `REVIEW_REQUIRED_FOR_EXECUTABLE_ACCEPTANCE`。Listed Issues PITには universe membership はあるが trading unit column がないため、無条件100株固定は採用不可。
- Tick: `REVIEW_REQUIRED_FOR_EXECUTABLE_ACCEPTANCE`。Market Open使用では生成価格roundingなし。LIMIT出現時は未受入ならHALT/REVIEW。

## 6. Missing Price / No Fill rule
- target session Open missing => NO_FILL/HALT
- OHLCV row missing => NO_FILL/HALT
- PIT universe missing => NO_FILL/HALT
- trading unit unknown => NO_FILL/HALT
- price null/invalid => NO_FILL/HALT
- source hash mismatch => HALT
- business date/target session mismatch => HALT

## 7. Cash / Quantity rule
- Cash: BUY cash check must use normal Current/Ledger available cash; Historical Broker must not create independent cash authority.
- Quantity: SELL quantity check must use normal Current/Ledger owned quantity and normal Submit Guard broker/current evidence path; Historical Broker must not create independent position authority.

## 8. Duplicate / Idempotency rule
- same pending item duplicate blocked by normal Submit Guard/Pending lifecycle
- same order identity duplicate blocked by normal Submit Pipeline ledger dedup
- same execution identity duplicate must be blocked by normal Execution Processor ledger dedup
- post-send-unknown auto resubmit remains prohibited

## 9. Fees / Tax / Slippage / Partial Fill assumption
- `smoke_limited_execution_model=true`
- `official_long_term_performance_model=false`
- `fees_model=ZERO_FOR_5BD_SMOKE`
- `tax_model=ZERO_FOR_5BD_SMOKE`
- `slippage_model=ZERO_FOR_5BD_SMOKE`
- `partial_fill_model=ALL_OR_NONE_FOR_5BD_SMOKE`
- 20BD前に高度化が必要。

## 10. Corporate Action Guard
- 判定: `PASS_NO_EVENT_OR_NO_IMPACT_FOR_5BD_WINDOW`
- Evidence: `reports/phase17_d_5bd_smoke_minimum_readiness/corporate_action_guard.json`
- Phase17-EではFull CA対応を実装しない。

## 11. HistoricalSubmitAdapter
- 判定: `NOT_ACCEPTED_DUE_NORMAL_SUBMIT_GUARD_BLOCKER`
- 理由: 通常 Submit Guard が historical Pending を `environment guard failure` で止めるため、adapterまで到達しない。

## 12. HistoricalExecutionSnapshotProvider
- 判定: `NOT_ACCEPTED_DUE_SUBMIT_PATH_BLOCKER`
- Submit evidence が通常経路で作れないため、provider acceptance は未実施。

## 13. 通常Submit Guard使用証拠
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:153` で historical は `HistoricalSubmitAdapter` を要求。
- その後 `run_submit_preflight` を通る。
- ただし `src/ai_fund_lab_v2/runtime_v2/submit/guards.py:120` が `environment != "demo" or pending_plan.environment != "demo"` をブロックする。
- isolated reproduction: `environment guard failure`。

## 14. 通常Execution Processor使用証拠
- `run_execution_readonly_pipeline` は historical で `HistoricalExecutionSnapshotProvider` を要求し、通常 normalize / ledger projection / current apply 経路に入る設計。
- ただし Submit Guard blocker により accepted historical submission evidence がまだ作れない。

## 15. External Effects
- 判定: `PASS_BY_COMPOSITION_CONTRACT`
- historical flags: `tachibana_readonly=false`, `tachibana_demo_write=false`, `tachibana_production_write=false`, `external_delivery=false`, `broker_write=false`

## 16. Demo / Production Regression
- Demo: `PASS_NO_PHASE17_E_CODE_CHANGE`
- Production: `PASS_NO_PHASE17_E_CODE_CHANGE`
- Phase17-EではRuntime code変更なし。

## 17. Runtime Core diff
- 判定: `NO_PHASE17_E_CODE_CHANGE_APPLIED`
- Phase17-Eでは Runtime Core 変更を適用していない。
- 既存worktreeにはPhase17以前/別作業の差分が残っているため、diff一覧はJSONの `runtime_core_diff` に記録。

## 18. Acceptance Gate一覧
- `FILL_PRICE_AUTHORITY_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `MARKET_BUY_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `MARKET_SELL_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `TARGET_SESSION_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `NO_FILL_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `LOT_TRADING_UNIT_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `CASH_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `QUANTITY_RULE_ACCEPTED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `DUPLICATE_SUBMIT_BLOCKED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `DUPLICATE_EXECUTION_BLOCKED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `FUTURE_PRICE_BLOCKED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `SOURCE_HASH_MISMATCH_BLOCKED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `HISTORICAL_SUBMIT_ADAPTER_READY`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `HISTORICAL_EXECUTION_PROVIDER_READY`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `NORMAL_SUBMIT_GUARD_USED`: `BLOCKED_BY_RUNTIME_CORE_REVIEW_REQUIRED`
- `NORMAL_EXECUTION_PROCESSOR_USED`: `NOT_EVALUATED`
- `NO_EXTERNAL_EFFECT`: `PASS`
- `DEMO_UNCHANGED`: `PASS`
- `PRODUCTION_UNCHANGED`: `PASS`
- `NO_RUNTIME_CORE_SEMANTIC_CHANGE`: `PASS_NO_PHASE17_E_CODE_CHANGE_BUT_REVIEW_REQUIRED_TO_PROCEED`
- `NO_ALTERNATE_RUNTIME`: `PASS`

## 19. Blocking findings
- `NORMAL_SUBMIT_GUARD_HISTORICAL_ENVIRONMENT_BLOCKER`: Submit Guardがdemo-onlyで、historical Pendingを通常経路でcommand化できない。これを直すにはSubmit Guard semantic changeが必要。

## 20. Non-blocking findings
- `fill_price_authority_determined`: Fill Price Authority can be described from Phase17-D evidence but cannot be runtime-accepted yet.
- `limit_order_scope`: Current planning paths generate MARKET; LIMIT remains HALT/REVIEW if encountered.

## 21. 作成・更新ファイル
- `docs/phase_reports/phase17_e_historical_fill_price_and_execution_model_acceptance.md`
- `reports/phase_reports/phase17_e_historical_fill_price_and_execution_model_acceptance.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/fill_price_authority_manifest.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/submit_guard_historical_blocker_evidence.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/acceptance_gates.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/no_external_effect_evidence.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/runtime_core_diff.json`
- `reports/phase17_e_historical_fill_price_and_execution_model_acceptance/historical_broker_capability_manifest.json`

## 22. 実行したテスト
- reviewed material hash collection
- isolated historical submit preflight reproduction: `environment guard failure`
- existing historical support regression tests: `21 passed in 3.91s`

## 23. 実行していない操作
- `5BD Historical Runtime execution`
- `Trading State Reset`
- `Current/Ledger/Pending/Runtime State mutation`
- `Feature generation`
- `Canonical update`
- `J-Quants fetch`
- `Tachibana API`
- `Demo submit`
- `Production access`
- `AI retraining`
- `Policy/Safety/Capital Allocation semantic change`

## 24. 最終判定
`PHASE17_E_RUNTIME_CORE_REVIEW_REQUIRED`

Fill Price Authorityは確定可能だが、正式acceptanceには通常Submit Guardをhistorical環境で通す必要がある。これはRuntime Core保護条件に抵触するため、Phase17-E内では実装せず停止する。

## 25. Recommended Next Prefix
- Runtime Core review: `Phase17-E2` 相当
- 正常完了後の次Prefix: `Phase17-F`
- Work Name: `Historical Runtime 5BD Final Entry Gate and Execution Preparation`
