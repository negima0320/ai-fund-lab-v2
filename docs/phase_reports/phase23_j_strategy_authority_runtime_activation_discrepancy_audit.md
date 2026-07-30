# Phase23-J: Strategy Authority Runtime Activation Discrepancy Audit

## Primary Judgment

`PHASE23_J_STRATEGY_AUTHORITY_RUNTIME_ALIGNMENT_REPAIRED_SHORT_VALIDATION_PASS`

## Secondary Judgments

- `FRESH_RUN_TARGET_EVIDENCE_CONSUMER_NOT_CALLED_CONFIRMED`
- `LEGACY_AUTHORITY_OBSERVABILITY_SEMANTICS_REPAIRED`
- `ACCEPTANCE_GATE_STRATEGY_BLOCK_PASS_DEFECT_REPAIRED`
- `STRATEGY_RUNTIME_BLOCKERS_REMAIN`
- `LONG_RUNTIME_VALIDATION_NOT_RUN`
- `RUNTIME_SWITCH_NOT_PERFORMED`
- `BROKER_WRITE_NOT_PERFORMED`

## Phase23-I Report vs Runtime Evidence

Phase23-Iのcontrolled integrationでは `strategy_authority` consumerがPendingへ到達したが、対象10BD run `runtime-test-historical-extended-smoke-20260728T204430498459Z` のdaily morning evidenceには `phase23_i_strategy_planning_authority_pipeline` が存在しなかった。対象runではFresh Runがdaily jobs後にStrategy Shadowを生成し、Strategy artifactは全日BLOCKしたまま、final close gateがStrategy結果をAcceptanceへ入れていなかった。

## Fresh Run Call Graph

対象runの実call graph:

```text
scripts/runtime_test.py run/fresh-run
→ daily runtime CLI jobs
→ run_daily_operation morning evidence
→ daily jobs完了後 generate_strategy_shadow_for_day
→ close_command
→ final_summary acceptance_gate_judgment = runtime validation status
```

Phase23-I consumerは対象runでは未到達。全10日 `called=false`。

## Legacy Authority実態

`legacy_authority_active=true` はPhase22 shadow preservation markerとしてhardcodedされており、legacy comparison artifactの存在とformal planning authorityが混同されていた。対象runではPhase23-I formal consumer evidenceがないため、実Runtime pathもPhase23-I authorityではない。修正後は `legacy_formal_planning_authority_active` と `legacy_authority_active_semantics` を分離した。

## Strategy BLOCK Root Cause

日別root blockerはEvidenceに記録済み。概要:

- 2026-06-29〜2026-07-03: `corporate_event`, `dynamic_position_count`, `position_management`
- 2026-07-06〜2026-07-10: `position_management`
- 共通reason: accepted generation id/status missing, model/scaler mismatch, source lineage hash required, technical features review, unscaled fallback forbidden, corporate event source incompleteなど

これらは未修復。BLOCKをPASSへ書き換えていない。

## Pending EMPTY原因

対象10BDの最終Pending EMPTYは、正当なno-action acceptanceではない。Phase23-I consumer未到達、Strategy runtime_planning/position_sizing BLOCK、Phase23-I Pending lineageなし、という組み合わせによる。

## Acceptance Gate PASS原因と修正

原因: `close_command` がruntime validation/run completion/PM fatalのみでPASSを決め、Strategy BLOCK・Strategy Authority missingをAcceptance Gateへ含めていなかった。

修正: `scripts/runtime_test.py` にStrategy Planning Authority run summaryとStrategy acceptance gateを追加。対象run evidenceを修正後ロジックへ再評価すると:

```text
authority_status = REVIEW_REQUIRED
called = 0
missing = 10
shadow = BLOCK
gate = BLOCK
```

## 修正内容

- final summaryに `strategy_planning_authority_*` fieldsを追加
- Strategy Authority missing / Strategy Shadow BLOCKをAcceptance Gateに反映
- morning evidenceに `strategy_planning_authority_evidence.json` を生成
- legacy comparison markerとformal legacy authorityを分離
- J用regressionを追加

## 修正ファイル

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/runtime_v2/test_phase23_j_strategy_authority_gate.py`

## 短時間テスト

- J/I focused: `6 passed in 1.71s`
- Targeted regression: `119 passed in 6.87s`
- Compile: PASS
- Target run evidence re-evaluation: PASS, repaired gate returns `BLOCK`

## 10BD Rerun Gate

`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

理由: alignment/gateは修正済みだが、Strategy downstream BLOCK root causesは未修復で、修正後コードによる実Fresh Runは未実施。Broker WriteとRuntime Switchは未実施。

## Evidence

- Human: `docs/phase_reports/phase23_j_strategy_authority_runtime_activation_discrepancy_audit.md`
- Machine: `reports/phase_reports/phase23_j_strategy_authority_runtime_activation_discrepancy_audit.json`
- Evidence: `reports/phase23_j_strategy_authority_runtime_activation_discrepancy_audit/`
