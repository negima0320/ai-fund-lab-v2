# Phase16-AQ Opportunity Phase5-E Fallback Removal

## Final Judgment

`PHASE16_AQ_PHASE5E_FALLBACK_REMOVED`

Phase16-APで残っていた技術BlockerであるOpportunity Phase5-E metrics fallbackは、Runtime v2のOpportunity producerから除去した。Metrics未指定、Phase5-E metrics明示、Model/Metrics不整合は推論前に`HALT`する。

Formal Approvalは人間承認のため引き続き未実施だが、今回対象の技術Blockerには含めない。

## Scope

実施したもの:

- Phase5-E metrics fallback除去
- Opportunity metrics未指定時のfail-closed
- Phase5-E metrics pathの明示Reject
- Model/Metrics pair validation
- Runtime CLIのBuy AI `HALT`伝播
- Runtime regression
- Artifact Registry preflight evidence更新

実施していないもの:

- Registry Lookup
- Formal Artifact Registration
- Artifact Copy
- Registry Event
- Acceptance
- Index
- Checkpoint
- Consumer Cutover
- Historical Runtime Test
- Demo/Paper Runtime実行

## Fallback Investigation

Runtime全体でPhase5-E関連参照を再調査した。

| Area | Evidence | Classification | Result |
| --- | --- | --- | --- |
| Runtime Opportunity Producer | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` | REMOVED | `training_metrics_path=... or reports/opportunity_ai/phase5e/...` fallbackを削除 |
| Runtime CLI | `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` | ACTIVE runtime input, no default | `--opportunity-training-metrics-path`は明示入力のみ |
| Opportunity inference helper | `src/ai_fund_lab_v2/opportunity_ai/inference.py` | READABLE legacy/default | Standalone Phase5-F inference default。Runtime producerは必ず明示metricsを渡す |
| Opportunity training | `src/ai_fund_lab_v2/opportunity_ai/training.py` | UNUSED by Runtime | Phase5-E training artifact generation only |
| Phase5-E train script | `scripts/train_phase5e_opportunity_model.py` | UNUSED by Runtime | Training script only |
| Artifact inventory docs/code | `src/ai_fund_lab_v2/artifact_registry/inventory.py` | Evidence/legacy metadata | Runtime inputではない |

Generated evidence:

- `reports/phase16_formal_registration_preparation/opportunity/phase5e_fallback_inventory.json`
- Classification: `REMOVED`
- Overall result: `READY`
- ACTIVE findings: `[]`

## Runtime Change

Primary change:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`

Behavior:

- `opportunity_training_metrics_path is None` -> `HALT`
- Phase5-E metrics path -> `HALT`
- Missing metrics artifact -> `HALT`
- Invalid JSON -> `HALT`
- Model/Metrics artifact set mismatch -> `HALT`
- Metrics model path mismatch -> `HALT`
- Metrics model hash mismatch -> `HALT`
- Feature schema mismatch between model and metrics, when metrics declares feature columns -> `HALT`

The Opportunity inference call now receives only the supplied metrics path. There is no automatic Phase5-E fallback path.

Runtime CLI change:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- Buy AI `HALT` now maps to `EXIT_HALT` and `final_state=HALT`.

## Model / Metrics Same Set

Without adding Registry Lookup, Runtime now performs local pair checks before inference:

- Model hash is computed.
- Metrics hash is computed.
- If both artifacts declare `artifact_set_id` or `opportunity_artifact_set_id`, they must match.
- If metrics declares `model_artifact_path`, it must reference the supplied model.
- If metrics declares `model_artifact_hash`, it must match the supplied model hash.
- If metrics declares `feature_columns`, it must match the model feature columns.

This enforces fail-closed behavior while keeping formal Registry integration out of scope.

## Regression

Executed tests:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py tests/artifact_registry/test_phase16ao_formal_registration_blocker_resolution.py
```

Result:

```text
17 passed
```

Additional note:

```text
python3 -m pytest -q tests/runtime_v2/phase15by_buy_origin_e2e.py
```

Result:

```text
no tests ran
```

That file is an executable E2E helper rather than a pytest test module; its fixture was updated to supply explicit Opportunity metrics.

Regression coverage added/updated:

- Phase5-P style metrics supplied -> PASS
- Metrics missing -> HALT
- Phase5-E metrics path supplied -> Reject/HALT
- Wrong model hash -> Reject/HALT
- Wrong Artifact Set -> Reject/HALT
- Schema failure still stops before inference
- CLI normal morning path supplies explicit metrics in tests
- Preflight no longer reports active Phase5-E fallback

## Formal Preflight

Executed:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.artifact_registry.formal_registration_preflight --output reports/phase16_formal_registration_preparation
```

Result:

- `formal_registration_ready`: `BLOCKED`
- `formal_registry_changed`: `false`
- `protected_hashes_unchanged`: `true`
- Opportunity `regression_ready`: `READY`
- Opportunity blockers: `formal approval required`

The remaining block is expected because Formal Approval is explicitly outside Phase16-AQ.

## Protected State Impact

Formal Registry and Runtime state hashes after AQ:

| Path | SHA256 |
| --- | --- |
| `.runtime/artifact_registry/events/registry_events.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `.runtime/artifact_registry/index/registry_index.json` | `4e23d629401d6656d9ba01104c802638fdbcec8902468f1aee8e10efb170cb42` |
| `.runtime/artifact_registry/checkpoints/latest.json` | `70f3375fb9ddd48d2501b372d67f0d34160179cc2e7161be2e92165e7523ca3e` |
| `.runtime/runtime_state/current_state.json` | `4eddb45f782fa5feb028d617acfcbfc9ffda9e53be11ffeb3f990d67d610be03` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |

Impact:

- Formal Registry: unchanged
- Current: unchanged
- Ledger: unchanged
- Pending: unchanged
- Runtime state protected root: unchanged

## Remaining Blockers

Technical blockers:

- None for Phase16-AQ scope.

Non-technical blocker:

- Formal Approval remains required before formal registration.

## Next Prefix

`Phase16-AR`

Recommended next action: Formal Approval preparation/collection or formal registration preflight closure, without starting Registry Lookup or Consumer Cutover unless explicitly requested.
