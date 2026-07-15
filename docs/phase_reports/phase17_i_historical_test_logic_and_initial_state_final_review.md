# Phase17-I Historical Test Logic and Initial State Final Review

## Final Judgment

`PHASE17_I_PREPARATION_UPDATE_REQUIRED`

Recommended next prefix: `Phase17-I-FIX`

Recommended next work name: `Historical Runtime Mode-Rooted Path Guard Closure`

Phase17-I は review-only で実施した。5BD Runtime、Reset、Backup execution、Submit、Execution、Feature生成、Canonical更新、外部 API は実行していない。

## 1. 読み込んだ資料

- Phase17-A / B / B1 / B1R / B1I-A / B1I-B / B1I-BR / B1I-C
- Phase17 Test Scope Review
- Phase17-D / E / F / G / H
- `runtime_architecture_v2.md`
- `historical_runtime_test_contract.md`
- `runtime_temporal_freshness_contract.md`
- `operational_data_architecture.md`
- `operational_lifecycle_state_reset_and_environment_transition_contract.md`
- Registry / materialized index contracts
- 対象 Runtime v2 code: CLI、historical_support、Submit、Execution、BrokerCapability、PathResolver、PM producer

## 2. Runtime Mainline Call Graph

5BD は通常 Runtime v2 CLI から開始する。

```text
run_daily_operation.main
-> resolve_environment_composition
-> market_refresh / data_readiness
-> normal feature date contract / carryover
-> buy_ai / morning planning
-> position_management / sell planning
-> safety / policy / capital allocation
-> normal Pending
-> run_submit_pipeline
-> run_submit_preflight
-> HistoricalSubmitAdapter
-> HistoricalExecutionSnapshotProvider
-> run_execution_readonly_pipeline
-> normal Ledger append
-> normal Current projection/apply
-> normal Runtime State
-> report / audit evidence
```

Evidence: `reports/phase17_i_historical_test_logic_and_initial_state_final_review/runtime_mainline_call_graph.json`

## 3. Historical Logic Inventory

Historical logic は以下に分類した。

- `APPROVED_ENVIRONMENT_COMPOSITION`: `resolve_environment_composition`
- `APPROVED_EXTERNAL_BOUNDARY`: `HistoricalSubmitAdapter`, `HistoricalExecutionSnapshotProvider`, fill price resolver
- `APPROVED_EVIDENCE_ONLY`: PIT reader, baseline collector, legacy gates helper
- `APPROVED_RESET_LIFECYCLE_SUPPORT`: reset plan validator
- `RUNTIME_CORE_LIMITED_AMENDMENT`: `SubmitEnvironmentGuardContext`, historical BrokerCapability

Historical-only AI、Feature Producer、State Authority、profit-only backtest path は検出していない。

## 4. Runtime Core Change Audit

Approval、Policy、Safety、Duplicate、Temporal、Cash / Quantity、Pending lifecycle、Ledger、Current の意味変更は検出していない。

ただし、direct `run_submit_pipeline` の mode-rooted path rejection に gap を検出した。

Finding:

```text
submit_pipeline_mode_rooted_historical_path_not_halt
```

`run_daily_operation` は `.runtime/historical` を拒否する。一方で `submit.pipeline::_reject_mode_rooted_runtime_root` は現状 `/demo` のみを見ており、direct call では `.runtime/historical` が HALT にならず、後段の policy missing まで進む。

これは 5BD が通常 CLI で実行される限り即 alternate runtime ではないが、Acceptance Gate の `ENVIRONMENT_ISOLATION_PASS` を満たさない。

## 5. Demo / Production 非回帰

Phase17-G regression を再実行し、Demo submit guard / safety / policy manifest の既存テストは PASS。

Production は引き続き explicit production acceptance なしでは broker write を許可しない。

## 6. Environment Isolation

PASS:

- Historical + wrong broker env
- Historical + broker_write=true
- Historical + external_delivery=true
- Historical + missing business_date
- Historical + missing evaluation_time
- Historical execution without HistoricalExecutionSnapshotProvider

PREPARATION UPDATE REQUIRED:

- Historical + mode-rooted runtime path via direct submit pipeline

Evidence: `environment_isolation_review.json`

## 7. 5BD Data / PIT / Carryover

Window:

| business_date | feature_date | carryover |
|---|---|---|
| 2026-07-06 | 2026-07-06 | no |
| 2026-07-07 | 2026-07-07 | no |
| 2026-07-08 | 2026-07-07 | yes |
| 2026-07-09 | 2026-07-08 | yes |
| 2026-07-10 | 2026-07-10 | no |

Hashes:

- OHLCV normalized: `c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d`
- OHLCV raw: `b9f67ae5e67d0764d011e6530ef88842d9b891f964a49325960535f4b103f6bd`
- Trading Calendar: `83dae980628a28c7592c07d4ab8c6c74271491d420b01578fa8a6ccafd6043ec`
- Listed Issues: `a02f4afd0f2bd31f2fdd1512c0e74e8251e6ce497d28a31c867efd12f31ed733`

Carryover は通常 Feature Date Contract を使用する。Feature 穴埋め、手動コピー、未来 OHLCV、別日 Open fallback は禁止。

## 8. Fill Model

5BD smoke 限定として妥当。

- Market order only
- target session Open
- all-or-none
- fees=0
- tax=0
- slippage=0
- partial fill disabled
- no fallback

Source hash mismatch、wrong target session、PIT universe outside、Corporate Action guard mismatch は HALT。Duplicate は BLOCK。LIMIT は REVIEW_REQUIRED。

## 9. Initial Trading State

Phase17-I では Reset 未実行。

正式初期状態:

```text
cash=1,000,000 JPY
buying_power=1,000,000 JPY
positions=0
pending=0
open_orders=0
executions=0
realized_pnl=0
unrealized_pnl=0
```

Phase17-J 開始直前に Backup、all-or-nothing Reset、post-reset hash validation が必要。

## 10. Reset Scope

Reset 対象は Trading State のみ。Current、Persistent Ledger、Pending、Runtime State、Approval、Execution、Idempotency、Historical Broker transient state を full unit として扱う。

## 11. Reset Exclusions

Reset excluded:

- Artifact Registry Event Store
- Materialized Registry Index
- Registry Checkpoint
- Accepted Artifact Sets
- Canonical Data
- Raw Data
- Feature Schema
- Candidate / Opportunity / PM Artifact
- Capital Allocation Artifact
- Policy / Safety definitions
- Configs
- Phase / Recovery evidence

Reset plan に含まれたら HALT。

## 12. Backup / Rollback

Backup 実行はしていない。Runbook は有効。

Rollback trigger:

- Reset failure
- Initial state mismatch
- Runtime HALT
- Runtime Error
- State consistency failure
- Data authority failure
- Unexpected external effect
- Baseline mismatch

Current-only、Ledger-only、Pending-only restore は禁止。5BD 完了後は Historical evidence を freeze / close し、Demo/Production へ Historical Trading State を継承しない。

## 13. Baseline Plan

Phase17-H baseline は確認済み。ただし Phase17-G/H/I でコード・成果物が増えているため、Phase17-J 開始直前に以下を再採取する。

- pre-reset source baseline
- post-reset initial state baseline
- daily state baseline
- final 5BD state
- post-close / post-reset baseline

## 14. Daily Job Sequence

現在案は妥当。

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
current_valuation_refresh
runtime_state_refresh
```

Report / Audit は Runtime manifest と stage evidence を freeze する。新しい job は作らない。

## 15. Test Validity Contract

有効条件:

- Normal Runtime v2 Mainline used
- No alternate path
- No external effect
- No future data
- No double submit / execution / ledger
- Current / Ledger / Pending consistency
- Cash / Quantity consistency
- Historical Clock consistency
- Registry / Artifact authority consistency
- Deterministic rerun behavior

Invalid:

- Runtime bypass
- Guard bypass
- Feature manual patch
- Data fallback
- State manual repair
- Partial reset
- Unexpected external API
- Authority mismatch
- Temporal violation

損益が良くても、上記違反があれば Test Invalid。

## 16. Acceptance Gate一覧

| Gate | Result |
|---|---|
| RUNTIME_V2_ACTUALLY_UNDER_TEST | PASS |
| NORMAL_MAINLINE_CONFIRMED | PASS |
| NO_ALTERNATE_RUNTIME | PASS |
| NO_ALTERNATE_MAINLINE | PASS |
| NO_TEST_ONLY_STATE_AUTHORITY | PASS |
| NO_TEST_ONLY_FEATURE_LOGIC | PASS |
| RUNTIME_CORE_CHANGE_SCOPE_ACCEPTABLE | PASS_WITH_PREPARATION_UPDATE |
| DEMO_SEMANTICS_UNCHANGED | PASS |
| PRODUCTION_SEMANTICS_UNCHANGED | PASS |
| ENVIRONMENT_ISOLATION_PASS | PREPARATION_UPDATE_REQUIRED |
| PIT_WINDOW_PASS | PASS |
| CARRYOVER_CONTRACT_PASS | PASS |
| FILL_MODEL_SMOKE_SCOPE_PASS | PASS |
| INITIAL_STATE_DEFINED | PASS |
| RESET_SCOPE_COMPLETE | PASS |
| RESET_EXCLUSIONS_PROTECTED | PASS |
| BACKUP_SCOPE_COMPLETE | PASS_RUNBOOK_VALID |
| ROLLBACK_PROCEDURE_VALID | PASS |
| BASELINE_PLAN_COMPLETE | PASS |
| DAILY_JOB_SEQUENCE_COMPLETE | PASS |
| TEST_VALIDITY_CONTRACT_COMPLETE | PASS |
| NO_EXTERNAL_EFFECT | PASS |
| NO_RUNTIME_DEGRADATION | PASS_WITH_PREPARATION_UPDATE |

## 17. Blocking Findings

`submit_pipeline_mode_rooted_historical_path_not_halt`

Phase17-J 前に、`submit.pipeline::_reject_mode_rooted_runtime_root` を `execution` 側と同等に修正し、`.runtime/{production,demo,historical,simulation,backtest}` を HALT にする必要がある。

## 18. Non-blocking Findings

- `historical_support/gates.py` は古い Phase17-B1 gate helper として evidence-only 扱いにする。
- Phase17-J 直前 baseline 再採取が必要。

## 19. 作成・更新ファイル

- `docs/phase_reports/phase17_i_historical_test_logic_and_initial_state_final_review.md`
- `reports/phase_reports/phase17_i_historical_test_logic_and_initial_state_final_review.json`
- `reports/phase17_i_historical_test_logic_and_initial_state_final_review/*.json`

## 20. 実行した検証

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_i_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
38 passed in 1.73s
```

加えて environment isolation の isolated read-only review を実施。

## 21. 実行していない操作

- Trading State Reset
- Trading State Backup execution
- Trading State Restore
- Current / Ledger / Pending / Runtime State mutation
- 5BD Runtime execution
- Historical Submit / Historical Execution
- Feature generation
- Canonical update
- J-Quants fetch
- Tachibana API
- Demo submit
- Production access
- AI retraining

## 22. 最終判定

`PHASE17_I_PREPARATION_UPDATE_REQUIRED`

## 23. Recommended Next Prefix

`Phase17-I-FIX`

Work Name:

`Historical Runtime Mode-Rooted Path Guard Closure`
