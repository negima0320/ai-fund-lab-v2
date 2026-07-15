# Phase17-O Historical 5BD Feature Artifact Point-in-time Regeneration

Prefix: `Phase17-O`  
Work Name: `Historical 5BD Feature Artifact Point-in-time Regeneration`  
Final Judgement: `PHASE17_O_REGISTRY_ARCHITECTURE_REVIEW_REQUIRED`

## 1. Summary

2026-07-06 and 2026-07-07 Feature Artifacts were regenerated with:

- Historical as-of J-Quants-derived inputs
- Current formal Feature Producer
- Accepted Feature Schema `runtime_v2_feature_contract_v1`
- No AI retraining
- No Trading State mutation
- No overwrite of existing `.runtime/operations/feature_artifacts/2026-07-06` or `2026-07-07`

Candidate and Opportunity validation passed for both dates. PM / Capital artifacts were generated as part of each date-level artifact set.

Phase17-O cannot be fully accepted because daily Feature Artifact Registry active-set architecture is not implemented in the current repository. The current contracts classify daily Feature Artifacts as `ACCEPTED_WITH_REGISTRY_GAP` / `ACCEPTED_CURRENT_PATH + MIGRATION_REQUIRED`, and no existing formal workflow was found for registering regenerated day-level Feature Artifact Sets as active Runtime resolver authority.

5BD Feature Date Contract readiness is also incomplete because 2026-07-09 is expected to carry over to 2026-07-08, but a READY regenerated / accepted 2026-07-08 artifact was not part of the explicit Phase17-O regeneration target.

## 2. PIT Source Authority

Normalized OHLCV physical authority:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Hash:

```text
c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d
```

Listed Issues physical authority used:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
```

The Phase17-N candidate `.runtime/operations/feature_refresh/2026-07-06/.../listed_info_for_feature.parquet` was not usable as the direct 2026-07-06 logical input because its `target_date` / `Date` was 2026-07-10. The regeneration used the J-Quants operational raw listed source and materialized per-date logical inputs with future rows excluded.

PIT manifests:

- `reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/pit_source_manifest_2026-07-06.json`
- `reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/pit_source_manifest_2026-07-07.json`

| Date | OHLCV logical rows | OHLCV future rows excluded | Listed logical rows | Listed future rows excluded |
|---|---:|---:|---:|---:|
| 2026-07-06 | 401497 | 16784 | 4437 | 13313 |
| 2026-07-07 | 405703 | 12578 | 8874 | 8876 |

## 3. Producer Authority

Formal Producer:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

Producer hash:

```text
8d0f22f8cde3d4eac76f329e9bb3fc6bdf2f75fe651cee818107d8cac1cb787f
```

The hash matches the Phase17-N accepted producer authority. Feature formulas, missing-history policy, producer code, consumer schema, and accepted schema were not changed.

## 4. Accepted Schema Authority

Accepted schema:

```text
.runtime/artifacts/features/shared/schema/2026-07-10/sha256-83f34c493f00cd17/feature_schema.json
```

Schema hash:

```text
83f34c493f00cd17e5bd36b4650dc245673da90dc287704cf423cd03628bc818
```

Schema ID:

```text
runtime_v2_feature_contract_v1
```

## 5. 2026-07-06 Regeneration

Artifact Set:

```text
phase17-o-historical-feature-set-2026-07-06-attempt002
```

Manifest hash:

```text
1b63120f8d9bac63136b7198ff8bfc1211967fb90cb104748b790d4ecc2ca426
```

| Artifact | Rows | Hash |
|---|---:|---|
| `candidate_features.parquet` | 4370 | `278dc623afb0690841d58949d344ef190caa3776f9e53ea520cd2bd964e50c3d` |
| `opportunity_feature_input.parquet` | 4370 | `44bd9e6295d3fde5f5dfe3eac03faf457e5b13e3bdd60d76a33357278cbb6a2c` |
| `position_feature_input.parquet` | 0 | `769c8a7002ead551f472f20e13b192841159047317658a0055375801bd300979` |
| `capital_policy_input.parquet` | 1 | `025a5f27c569aacf7e8364ca2c23e1035dcc183d243a9d94991d7ce759c1f12c` |

Candidate status: `PASS`  
Opportunity status: `PASS`  
Consumer readiness: `READY`

## 6. 2026-07-07 Regeneration

Artifact Set:

```text
phase17-o-historical-feature-set-2026-07-07-attempt002
```

Manifest hash:

```text
62a5991d5551f46529093330067caf75666abc3617170443590939d6b816fc9c
```

| Artifact | Rows | Hash |
|---|---:|---|
| `candidate_features.parquet` | 4370 | `ae1948afc081d036e6e2ebbac37d86ce766c1e768bd3ca32934d884dd7f8801d` |
| `opportunity_feature_input.parquet` | 4370 | `ac61f57cb113360a2c5033a493a3f73daa3569b48518d81c49178d49d928d935` |
| `position_feature_input.parquet` | 0 | `88f0e514de42a7ff1b405a667e73639ae6a9cf72d1b78452d6ac24b8b2df5a7b` |
| `capital_policy_input.parquet` | 1 | `b03196793a256a2cd1dfa645445556424dfee808545cce815a41bdedeac6094e` |

Candidate status: `PASS`  
Opportunity status: `PASS`  
Consumer readiness: `READY`

## 7. Validation

Validation outputs:

- `candidate_validation_2026-07-06.json`: `PASS`
- `candidate_validation_2026-07-07.json`: `PASS`
- `opportunity_validation_2026-07-06.json`: `PASS`
- `opportunity_validation_2026-07-07.json`: `PASS`
- `future_data_audit.json`: `PASS`
- `forbidden_source_audit.json`: `PASS`
- `determinism_validation.json`: `PASS`

Candidate and Opportunity artifacts have:

- Required columns complete
- No `feature__` prefixed artifact columns
- No duplicate `code`
- Correct `target_date`
- Consumer readiness `READY`
- Nulls only under the formal missing-history / missing-price / missing-volume policy

## 8. Artifact Set / Path

New immutable artifact roots:

```text
.runtime/artifacts/features/historical_regenerated/2026-07-06/phase17-o-historical-feature-set-2026-07-06-attempt002/
.runtime/artifacts/features/historical_regenerated/2026-07-07/phase17-o-historical-feature-set-2026-07-07-attempt002/
```

Existing operational artifacts were retained and not overwritten.

Attempt note:

- `attempt001` failed closed because as-of inputs were materialized under `reports/...`; the formal producer rejected those paths as not J-Quants-derived.
- `attempt002` materialized inputs under `.runtime/artifacts/features/historical_regenerated/.../inputs/jquants/...` and passed the producer source gate.

## 9. Acceptance / Registry

Acceptance evidence:

```text
reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/acceptance_evidence.json
```

Status: `INCOMPLETE`

Registry validation:

```text
reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/registry_validation.json
```

Status: `REVIEW_REQUIRED`

Reason:

- Existing contracts identify daily Feature Artifacts as Runtime inputs, but current implementation does not provide a formal daily Feature Artifact active-set Registry workflow.
- Registry event log, materialized index, and checkpoint were not mutated.
- New logical identities were not invented.

## 10. Runtime Resolver / Feature Date Contract

Regenerated 2026-07-06 and 2026-07-07 artifacts resolve in isolated evidence roots.

5BD audit:

```text
reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/five_bd_feature_date_contract_audit.json
```

| Business Date | Status | Selected Feature Date | Schema Ready | Reason |
|---|---|---:|---:|---|
| 2026-07-06 | `PASS` | 2026-07-06 | true | requested artifacts available |
| 2026-07-07 | `PASS` | 2026-07-07 | true | requested artifacts available |
| 2026-07-08 | `PASS` | 2026-07-07 | true | carryover to regenerated 2026-07-07 |
| 2026-07-09 | `REVIEW_REQUIRED` | 2026-07-08 | false | 2026-07-08 READY artifact missing |
| 2026-07-10 | `PASS` | 2026-07-10 | true | existing formal 2026-07-10 artifact |

Blocking: Phase17-O regenerated only 2026-07-06 and 2026-07-07 as explicitly requested. 2026-07-09 requires a READY 2026-07-08 artifact. Existing 2026-07-08 artifact is old schema and was not selected.

## 11. Trading State Invariance

Pre/post state hash comparison:

```text
reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration/state_hash_comparison.json
```

Status: `PASS`

Unchanged:

- Current
- Ledger
- Pending
- Runtime State
- Approval state
- Execution state
- Idempotency state
- Broker transient state
- Artifact Registry

## 12. Demo / Production Non-regression

No Demo / Production submit or access was executed.

No Runtime Core, Consumer, Producer, AI model, PM policy, Capital policy, accepted schema, Registry event, Registry index, or checkpoint code/path was changed.

Historical regenerated artifacts are under `.runtime/artifacts/features/historical_regenerated/...` and were not promoted to Demo / Production latest authority.

## 13. Tests

Passed:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_o_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py \
  tests/runtime_v2/test_phase17_m_consumer_wiring_and_feature_temporal_authority.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase15an_feature_consumer_readiness.py
```

Result:

```text
27 passed
```

Partial regression with existing Phase9J Feature Refresh tests:

```text
28 passed, 4 failed
```

Failures are in `tests/paper_trading/test_phase9j_feature_refresh.py`. They appear to encode legacy fixture expectations that no longer match the current formal producer's stricter schema / missing-history behavior. No code was changed to make these pass.

## 14. Acceptance Gates

| Gate | Status |
|---|---|
| `PIT_SOURCE_2026_07_06_PASS` | PASS |
| `PIT_SOURCE_2026_07_07_PASS` | PASS |
| `NO_FUTURE_DATA` | PASS |
| `JQUANTS_ONLY` | PASS |
| `FORMAL_PRODUCER_USED` | PASS |
| `PRODUCER_HASH_ACCEPTED` | PASS |
| `ACCEPTED_SCHEMA_USED` | PASS |
| `NO_SCHEMA_CHANGE` | PASS |
| `NO_FEATURE_SEMANTIC_CHANGE` | PASS |
| `CANDIDATE_2026_07_06_READY` | PASS |
| `CANDIDATE_2026_07_07_READY` | PASS |
| `OPPORTUNITY_2026_07_06_READY` | PASS |
| `OPPORTUNITY_2026_07_07_READY` | PASS |
| `PM_INPUT_COMPATIBLE` | PASS |
| `CAPITAL_INPUT_COMPATIBLE` | PASS |
| `DETERMINISTIC_REGENERATION` | PASS |
| `NO_FORBIDDEN_SOURCE` | PASS |
| `NO_AI_RETRAINING` | PASS |
| `OLD_ARTIFACT_RETAINED` | PASS |
| `NEW_ARTIFACT_IMMUTABLE` | PASS |
| `ACCEPTANCE_WORKFLOW_PASS` | BLOCKED |
| `REGISTRY_APPEND_ONLY` | PASS, no registry write |
| `REGISTRY_INDEX_PASS` | BLOCKED, no daily feature active-set workflow |
| `REGISTRY_CHECKPOINT_PASS` | BLOCKED, no daily feature active-set workflow |
| `RUNTIME_RESOLVER_PASS` | REVIEW_REQUIRED |
| `ALL_5BD_FEATURE_DATE_CONTRACTS_PASS` | FAIL, 2026-07-09 incomplete |
| `NO_OLD_SCHEMA_ARTIFACT_SELECTED` | PASS in isolated audit for selected dates; 2026-07-09 blocked instead |
| `CURRENT_UNCHANGED` | PASS |
| `LEDGER_UNCHANGED` | PASS |
| `PENDING_UNCHANGED` | PASS |
| `RUNTIME_STATE_UNCHANGED` | PASS |
| `DEMO_UNCHANGED` | PASS |
| `PRODUCTION_UNCHANGED` | PASS |
| `NO_5BD_RUNTIME_EXECUTION` | PASS |

## 15. Final Judgement

```text
PHASE17_O_REGISTRY_ARCHITECTURE_REVIEW_REQUIRED
```

Secondary blockers:

```text
PHASE17_O_ARTIFACT_ACCEPTANCE_INCOMPLETE
PHASE17_O_FEATURE_DATE_CONTRACT_INCOMPLETE
```

Phase17-P must not start yet.

Recommended next work:

```text
Phase17-O-R
Historical Daily Feature Artifact Registry and 5BD Contract Closure Review
```
