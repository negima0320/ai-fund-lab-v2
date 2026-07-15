# Phase17-H 5BD Final Entry Gate

## Final Judgment

`PHASE17_H_5BD_READY`

Recommended next prefix: `Phase17-I`

Recommended next work name: `Historical Runtime 5BD Smoke Test`

## 1. 読み込んだ資料

- Phase17-A / B / B1 / B1R / B1I-A / B1I-B / B1I-BR / B1I-C
- Phase17-D / E / F / G
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/operational_lifecycle_state_reset_and_environment_transition_contract.md`
- Operational Data Architecture related contracts

## 2. Entry Gate一覧

| Gate | 判定 | Evidence |
|---|---|---|
| Historical Environment | PASS | Phase17-B1I-A / Phase17-G |
| Registry | PASS | Phase17-B1I-BR、registry baseline hash |
| PM Authority | PASS | Phase17-B1I-B / B1I-BR |
| Runtime Mainline | PASS | Phase17-G mainline preservation |
| Submit Guard | PASS | Phase17-G Environment Matrix |
| Execution Processor | PASS | Phase17-G fixture regression |
| Historical Fill Model | PASS | `PHASE17_G_HISTORICAL_SUBMIT_AND_FILL_MODEL_ACCEPTED` |
| Canonical OHLCV | PASS | Phase17-D PIT hash |
| Trading Calendar | PASS | Phase17-D calendar authority |
| Listed Issues | PASS | Phase17-D listed issues hash |
| Window PIT | PASS | `reports/phase17_d_5bd_smoke_minimum_readiness/5bd_window_pit_manifest.json` |
| Corporate Action Guard | PASS | no-impact for 5BD window |
| Historical Clock | PASS | CLI requires explicit business date / evaluation time |
| Reset | PASS_RUNBOOK_READY | Reset not executed |
| Regression Baseline | PASS | read-only hashes captured |
| External Effect Blocking | PASS | payload-only / historical_simulated / broker_write=false |

Acceptance Gate:

- `ALL_ENTRY_GATES_PASS`: PASS
- `RESET_READY`: PASS, runbook ready and reset not executed
- `ROLLBACK_READY`: PASS
- `BASELINE_READY`: PASS
- `WINDOW_READY`: PASS
- `COMMAND_READY`: PASS
- `NO_RUNTIME_DEGRADED`: PASS by contract/regression
- `NO_ALTERNATE_RUNTIME`: PASS
- `NO_EXTERNAL_EFFECT`: PASS

## 3. 5BD実行コマンド

CLI:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

Common args:

```text
--mode historical
--broker-environment historical_simulated
--runtime-root .runtime
--notification-mode payload-only
--market-refresh-allow-api-fetch false
--stop-on-review-required
--stop-on-blocked
```

Per business date, run in this order:

```text
--job market_refresh --submit-enabled false --evaluation-time <D>T08:00:00+09:00
--job data_readiness --submit-enabled false --evaluation-time <D>T08:05:00+09:00
--job morning --submit-enabled false --feature-date <PIT_SELECTED_FEATURE_DATE> --evaluation-time <D>T08:30:00+09:00
--job sell_planning --submit-enabled false --feature-date <PIT_SELECTED_FEATURE_DATE> --evaluation-time <D>T08:40:00+09:00
--job submit --submit-enabled true --feature-date <PIT_SELECTED_FEATURE_DATE> --evaluation-time <D>T08:45:00+09:00
--job execution --submit-enabled false --evaluation-time <D>T15:30:00+09:00
--job current_valuation_refresh --submit-enabled false --apply-current-valuation --evaluation-time <D>T15:35:00+09:00
--job runtime_state_refresh --submit-enabled false --evaluation-time <D>T15:40:00+09:00
```

Concrete window:

| business_date | feature_date | carryover |
|---|---|---|
| 2026-07-06 | 2026-07-06 | no |
| 2026-07-07 | 2026-07-07 | no |
| 2026-07-08 | 2026-07-07 | yes |
| 2026-07-09 | 2026-07-08 | yes |
| 2026-07-10 | 2026-07-10 | no |

Carryover は正式 smoke scenario として採用する。Feature を穴埋め生成しない。

## 4. Runtime Manifest

- Runtime root: `.runtime`
- Mode: `historical`
- Broker environment: `historical_simulated`
- Runtime: Runtime v2 normal CLI / normal fixed paths
- Historical-only Runtime: prohibited / not created
- Mode-rooted Current path: prohibited
- External delivery: false
- Notification: `payload-only`
- J-Quants fetch: disabled

Manifest: `reports/phase17_h_5bd_final_entry_gate/runtime_manifest.json`

## 5. Window

5BD window は `2026-07-06` から `2026-07-10` で確定。

Phase17-D の PIT manifest、Trading Calendar、Listed Issues、OHLCV、Corporate Action Guard が揃っている。`2026-07-08` と `2026-07-09` は carryover scenario として採用する。

## 6. Reset

Phase17-H では Reset は実行していない。

Phase17-I 開始直前に実施する順序:

1. Source state freeze と baseline 再採取。
2. Trading State Backup を作成。
3. Backup manifest hash を検証。
4. Reset excluded prefix が含まれていないことを確認。
5. `.runtime` の resettable Trading State を all-or-nothing reset。
6. Initial state を検証: cash 1,000,000 JPY、positions 0、pending 0、open orders 0、executions 0。
7. 検証失敗なら 5BD を開始せず HALT。

Reset excluded:

- `artifact_registry`
- `artifacts`
- `operations/jquants`
- `phase9/canonical_data`
- `data/raw`
- `candidate_ai`
- `opportunity_ai`
- `configs`

## 7. Rollback

HALT、Runtime Error、State Error、Data Error、partial reset、baseline mismatch、unexpected external effect があれば停止する。

Rollback は Phase17-I 直前 backup へ戻す。Current だけ、Ledger だけ、Pending だけの部分 restore は禁止。Operational Foundation は restore / mutate しない。

Runbook: `reports/phase17_h_5bd_final_entry_gate/rollback_runbook.json`

## 8. Baseline

Read-only で取得した baseline:

| Item | Hash |
|---|---|
| Current | `3f85a8fe3ec4a3ba55a3d2c884afe893b5e687f9bbb0527d2d85f2636f7c9f51` |
| Ledger | `1f12ac5f8a2106e23148ccc39e5c74e76c10306005e18dbf7d574aea73414f9b` |
| Pending | `5de802ad379c8313c11e5987b6e76a570de83a1a184435120fa5d0654a84845a` |
| Runtime State | `a35ef6bb7b25c2b7c00e806b921d8ab56dc5c1d9d20bb42464d18167b97570ed` |
| Registry | `6bd765a8dc6c2433aed86234884eaf40e0ec4946dd60a5d1d0f2f292ffe12479` |
| Accepted Artifacts | `aefcfa1c00e8f961358123eddae91aa50d898b841f48ae2702b094d64659ea61` |

Manifest: `reports/phase17_h_5bd_final_entry_gate/regression_baseline_manifest.json`

## 9. Blocking

なし。

## 10. Non-blocking

- fees / tax / slippage / partial fill は 20BD 以降。
- limit order execution rule は別 acceptance。
- full official performance execution model は 1-Year / Full 前に別途必要。
- Current Runtime State は現時点で Demo 由来の状態を含むため、Phase17-I 直前 Reset は必須。

## 11. 作成・更新ファイル

- `docs/phase_reports/phase17_h_5bd_final_entry_gate.md`
- `reports/phase_reports/phase17_h_5bd_final_entry_gate.json`
- `reports/phase17_h_5bd_final_entry_gate/entry_gate_manifest.json`
- `reports/phase17_h_5bd_final_entry_gate/runtime_manifest.json`
- `reports/phase17_h_5bd_final_entry_gate/regression_baseline_manifest.json`
- `reports/phase17_h_5bd_final_entry_gate/5bd_runbook.json`
- `reports/phase17_h_5bd_final_entry_gate/rollback_runbook.json`

## 12. 実行した検証

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_h_pycache PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --help
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase17_h_pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py
```

Result:

```text
18 passed in 1.68s
```

## 13. 実行していない操作

- 5BD Runtime
- Trading State Reset
- Current / Ledger / Pending / Runtime State mutation
- Feature generation
- Canonical update
- Submit
- Execution
- Demo access
- Production access

## 14. 最終判定

`PHASE17_H_5BD_READY`

## 15. Recommended Next Prefix

`Phase17-I`

Work Name:

`Historical Runtime 5BD Smoke Test`
