# Phase23-K: Strategy Downstream Root Blocker Repair

## Primary Judgment

`PHASE23_K_PARTIAL_REPAIR_SHORT_VALIDATION_PASS_10BD_GATE_NOT_READY`

Phase23-Jで確認されたStrategy downstream root blockerのうち、Position ManagementがRuntime Current接続済みの空Portfolioを`position_management_shadow_positions_required`として扱う契約不整合を修正した。

ただし、対象10BD runではAccepted Generationが各business dateより未来日であり、PIT契約上は引き続き正しく停止する。このため10BD再実行Gateは`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`とする。

## Secondary Judgment

- Runtime Current接続済み・保有0は、欠損ではなく`EMPTY_PORTFOLIO`として明示する。
- Runtime Current未接続、Artifact欠損、PM未実行、空Portfolioを区別する。
- Accepted Generation未解決、future accepted/effective、model/scaler binding欠損はPASSへ変換しない。
- Historical専用分岐、latest fallback、fixed positions、missing-to-empty no-actionは追加していない。

## Repair Scope

修正対象はPM入力契約に限定した。

- `runtime_current_positions is not None`をRuntime Current接続済みAuthorityとして扱う。
- 接続済みで有効Positionが0件、かつadapter変換エラーがない場合は`authoritative_empty_portfolio=true`にする。
- 空Portfolio時はPM holdings評価に不要な`position_lifecycle` / `technical_features` / `opportunity_summary`をPM内ではrequiredにしない。
- Accepted Generation / model / scalerは引き続きrequired。
- Runtime Current未接続でpositionsが空の場合は従来どおり`position_management_shadow_positions_required`を維持する。

## Evidence-First Audit

Evidence directory:

`reports/phase23_k_strategy_downstream_root_blocker_repair/`

作成した事前audit evidence:

- `root_blocker_dependency_graph.json`
- `accepted_generation_resolution_audit.json`
- `model_scaler_binding_audit.json`
- `source_lineage_and_features_audit.json`
- `corporate_event_eligibility_audit.json`
- `position_management_input_audit.json`
- `dynamic_position_count_input_audit.json`
- `downstream_block_propagation_matrix.json`

対象run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260728T204430498459Z`

主な確認結果:

- 2026-06-29から2026-07-10までAccepted Generationは`REVIEW_REQUIRED`。
- 理由は`accepted_generation_accepted_at_after_business_date`および`accepted_generation_effective_from_after_business_date`。
- PMはAccepted Generation未解決に起因してmodel/scaler bindingもBLOCK。
- 追加で、保有0が`position_management_shadow_positions_required`へ落ちる構造的ブロッカーを確認した。

## Post-Fix Evidence

作成した修正後evidence:

- `strategy_runtime_reachability.json`
- `fresh_run_entrypoint_validation.json`
- `strategy_authority_daily_evidence.json`
- `pending_generation_validation.json`
- `acceptance_gate_validation.json`
- `production_commonality_matrix.json`
- `silent_fallback_audit.json`
- `modified_files.json`
- `test_results.json`
- `remaining_gaps.json`
- `ten_bd_rerun_gate.json`

## Acceptance Check

| Check | Result |
| --- | --- |
| Strategy Downstream Root Blocker修正 | PARTIAL PASS |
| Empty Current vs abnormal empty分離 | PASS |
| PM safe zero-action semantics | PASS |
| Accepted Generation future参照禁止 | PASS |
| latest fallbackなし | PASS |
| fixed candidates/buys/positionsなし | PASS |
| Historical専用分岐なし | PASS |
| Broker Writeなし | PASS |
| Fresh Run entrypoint検証 | NOT EXECUTED |
| 10BD/20BD/1y/3y | NOT EXECUTED |

## Short Tests

実施:

```text
python3 -m pytest tests/strategy/test_phase22_d_position_management.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/position_management.py
python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_j_strategy_authority_gate.py -q
```

結果:

```text
13 passed
compile PASS
6 passed
```

## Remaining Gaps

- 対象10BD runのAccepted GenerationはPIT上未解決のため、Strategy Authority/Pending到達は確認できない。
- Fresh-run-like daily entrypoint validationは未実施。
- Corporate Event coverageはpartial/reviewまたはfuture row blockを保持しており、PASSへは変換していない。

## 10BD Rerun Gate

`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

理由:

- 対象10BDのAccepted Generationがbusiness dateより未来。
- Fresh-run-like daily entrypoint validationが未実施。
- Strategy planning/pendingの到達は対象run上では未確認。

10BDは実施していない。
