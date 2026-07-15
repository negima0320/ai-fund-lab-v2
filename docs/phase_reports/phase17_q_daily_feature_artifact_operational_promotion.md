# Phase17-Q Daily Feature Artifact Operational Promotion

Prefix: `Phase17-Q`  
Work Name: `Daily Feature Artifact Operational Promotion`

Final Judgment:

```text
PHASE17_Q_DAILY_FEATURE_OPERATIONAL_PROMOTION_ACCEPTED
```

## 1. Summary

Phase17-Q completed the minimum operational promotion needed for the Historical 5BD smoke rerun:

1. `2026-07-08` Feature Artifact was regenerated with PIT J-Quants-derived inputs.
2. Existing operational Feature Artifact sets for `2026-07-06`, `2026-07-07`, and `2026-07-08` were backed up.
3. Regenerated artifacts were promoted into the normal Runtime authority path:

```text
.runtime/operations/feature_artifacts/<selected_feature_date>/
```

No Runtime resolver, Registry architecture, accepted schema, feature semantics, model, Current, Ledger, Pending, Runtime State, Submit, Execution, J-Quants fetch, Canonical data, Demo submit, or Production access was changed.

Promotion transaction:

```text
phase17-q-feature-promotion-20260714T092840877883Z
```

## 2. Current Authority

Confirmed authority remains:

```text
Feature Date Contract
    ↓
selected_feature_date
    ↓
.runtime/operations/feature_artifacts/<selected_feature_date>/
    ↓
candidate_features.parquet
opportunity_feature_input.parquet
```

`latest_features.json` was kept consistent as evidence/fallback marker, but it was not made a new pointer authority. Registry `features.shared.accepted_set` remains schema authority, not daily parquet instance authority.

## 3. 2026-07-08 PIT Source

PIT source manifest:

```text
reports/phase17_q_daily_feature_artifact_operational_promotion/pit_source_manifest_2026-07-08.json
```

Inputs were cut off at:

```text
date <= 2026-07-08
```

Physical authorities:

| Source | Path |
|---|---|
| Normalized OHLCV | `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| Listed Issues | `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` |
| Trading Calendar | `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` |

Logical 2026-07-08 inputs were materialized under:

```text
.runtime/artifacts/features/historical_regenerated/2026-07-08/phase17-q-historical-feature-set-2026-07-08-attempt001/inputs/jquants/historical_asof/
```

## 4. 2026-07-08 Regeneration

Formal producer:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

Producer hash:

```text
8d0f22f8cde3d4eac76f329e9bb3fc6bdf2f75fe651cee818107d8cac1cb787f
```

Accepted schema:

```text
runtime_v2_feature_contract_v1
```

Schema hash:

```text
83f34c493f00cd17e5bd36b4650dc245673da90dc287704cf423cd03628bc818
```

New immutable artifact set:

```text
.runtime/artifacts/features/historical_regenerated/2026-07-08/phase17-q-historical-feature-set-2026-07-08-attempt001/
```

| Artifact | Hash |
|---|---|
| `candidate_features.parquet` | `c7134b48bbc44873de25206ff03fb9695847f32296947224577c204fead02a51` |
| `opportunity_feature_input.parquet` | `9ef93c1c86603eb3f32f8ae6b728a214061bce1229193ebe77f36e77b1732480` |
| `position_feature_input.parquet` | `a218616f3b01a2d6b96f03c3006dd38ac88d62d965409356b4629435d59b7e0f` |
| `capital_policy_input.parquet` | `c4d712874b672d7cb3f42674391bd016cb71dd8773400433327ad432b73dd77b` |

Consumer readiness: `READY`

## 5. Validation

Candidate validation:

```text
PASS
```

Opportunity validation:

```text
PASS
```

PM compatibility:

```text
COMPATIBLE
```

Capital compatibility:

```text
COMPATIBLE
```

Future data audit:

```text
PASS
```

Forbidden source audit:

```text
PASS
```

Determinism:

```text
PASS
```

Note: `capital_policy_input.parquet` exact file hash differs between first and second deterministic runs because the formal producer embeds output artifact path references. Candidate, Opportunity, and Position exact hashes match. This is the same path-reference-only behavior seen in Phase17-O.

## 6. Promotion

Promotion preflight:

```text
PASS
```

Backups were created under:

```text
.runtime/backups/feature_artifact_promotion/phase17-q-feature-promotion-20260714T092840877883Z/
```

Promotion results:

| Date | Result | Candidate hash | Opportunity hash |
|---|---|---|---|
| 2026-07-06 | PASS | `278dc623afb0690841d58949d344ef190caa3776f9e53ea520cd2bd964e50c3d` | `44bd9e6295d3fde5f5dfe3eac03faf457e5b13e3bdd60d76a33357278cbb6a2c` |
| 2026-07-07 | PASS | `ae1948afc081d036e6e2ebbac37d86ce766c1e768bd3ca32934d884dd7f8801d` | `ac61f57cb113360a2c5033a493a3f73daa3569b48518d81c49178d49d928d935` |
| 2026-07-08 | PASS | `c7134b48bbc44873de25206ff03fb9695847f32296947224577c204fead02a51` | `9ef93c1c86603eb3f32f8ae6b728a214061bce1229193ebe77f36e77b1732480` |

Old operational artifacts were retained in backup evidence. Promotion was performed as a feature-artifact-only operation and did not touch Trading State.

## 7. Feature Date Contract

5BD contract audit:

```text
PASS
```

| Business date | Selected feature date | Status | Candidate hash |
|---|---:|---|---|
| 2026-07-06 | 2026-07-06 | PASS | `278dc623afb0690841d58949d344ef190caa3776f9e53ea520cd2bd964e50c3d` |
| 2026-07-07 | 2026-07-07 | PASS | `ae1948afc081d036e6e2ebbac37d86ce766c1e768bd3ca32934d884dd7f8801d` |
| 2026-07-08 | 2026-07-07 | PASS | `ae1948afc081d036e6e2ebbac37d86ce766c1e768bd3ca32934d884dd7f8801d` |
| 2026-07-09 | 2026-07-08 | PASS | `c7134b48bbc44873de25206ff03fb9695847f32296947224577c204fead02a51` |
| 2026-07-10 | 2026-07-10 | PASS | `2fcda90a6bf124db6ff77b96bd1905be875ae717659ddaa27ab7ce93d3790567` |

All selected artifacts are consumer-ready. No old schema artifact is selected.

## 8. Runtime Resolution

Runtime resolution trace:

```text
PASS
```

Important checks:

- `2026-07-06` selects promoted `2026-07-06`.
- `2026-07-07` selects promoted `2026-07-07`.
- `2026-07-08` carryover selects promoted `2026-07-07`.
- `2026-07-09` selects promoted `2026-07-08`.
- `2026-07-10` remains unchanged.

## 9. Runner Plan

Command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2026-07-06 \
  --json
```

Result:

```text
PASS
exit_code=0
```

## 10. State Protection

Trading/protected state hash comparison:

```text
PASS
```

Unchanged:

- Current
- Ledger
- Pending
- Runtime State
- Approval
- Execution
- Idempotency
- Broker transient
- Artifact Registry

Demo / Production non-regression:

```text
PASS
```

`2026-07-10` artifacts remain unchanged, and current Demo / Production operation state was not changed.

## 11. Rollback

Rollback runbook:

```text
reports/phase17_q_daily_feature_artifact_operational_promotion/rollback_runbook.json
```

Rollback scope is Feature Artifact Promotion only. Partial restore is prohibited. Trading State rollback is not part of this rollback.

## 12. Regression

Runtime / consumer subset:

```text
27 passed
```

Runner plan:

```text
PASS
```

Known legacy Phase9J tests:

```text
28 passed, 4 failed
```

The four failures are the same legacy Feature Refresh fixture expectation mismatch documented in Phase17-O. They were not introduced by Phase17-Q promotion.

## 13. Acceptance Gates

| Gate | Result |
|---|---|
| PIT_SOURCE_2026_07_08_PASS | PASS |
| CANDIDATE_2026_07_08_READY | PASS |
| OPPORTUNITY_2026_07_08_READY | PASS |
| PM_2026_07_08_COMPATIBLE | PASS |
| CAPITAL_2026_07_08_COMPATIBLE | PASS |
| NO_FUTURE_DATA | PASS |
| NO_FORBIDDEN_SOURCE | PASS |
| DETERMINISTIC_REGENERATION | PASS |
| PROMOTION_PREFLIGHT_PASS | PASS |
| EXISTING_OPERATIONAL_ARTIFACTS_BACKED_UP | PASS |
| PROMOTION_2026_07_06_PASS | PASS |
| PROMOTION_2026_07_07_PASS | PASS |
| PROMOTION_2026_07_08_PASS | PASS |
| PROMOTION_ATOMIC | PASS |
| POST_PROMOTION_HASH_PASS | PASS |
| ACCEPTED_SCHEMA_PASS | PASS |
| OLD_ARTIFACT_RETAINED | PASS |
| NO_OLD_SCHEMA_ARTIFACT_SELECTED | PASS |
| RUNTIME_RESOLUTION_2026_07_06_PASS | PASS |
| RUNTIME_RESOLUTION_2026_07_07_PASS | PASS |
| RUNTIME_RESOLUTION_2026_07_09_PASS | PASS |
| ALL_5BD_FEATURE_DATE_CONTRACTS_PASS | PASS |
| RUNNER_PLAN_PASS | PASS |
| ROLLBACK_RUNBOOK_READY | PASS |
| CURRENT_UNCHANGED | PASS |
| LEDGER_UNCHANGED | PASS |
| PENDING_UNCHANGED | PASS |
| RUNTIME_STATE_UNCHANGED | PASS |
| REGISTRY_UNCHANGED | PASS |
| DEMO_CURRENT_OPERATION_UNCHANGED | PASS |
| PRODUCTION_CURRENT_OPERATION_UNCHANGED | PASS |
| NO_5BD_RUNTIME_EXECUTION | PASS |

## 14. Files

Created / updated:

- `docs/phase_reports/phase17_q_daily_feature_artifact_operational_promotion.md`
- `reports/phase_reports/phase17_q_daily_feature_artifact_operational_promotion.json`
- `reports/phase17_q_daily_feature_artifact_operational_promotion/`
- `.runtime/artifacts/features/historical_regenerated/2026-07-08/phase17-q-historical-feature-set-2026-07-08-attempt001/`
- `.runtime/backups/feature_artifact_promotion/phase17-q-feature-promotion-20260714T092840877883Z/`
- `.runtime/operations/feature_artifacts/2026-07-06/`
- `.runtime/operations/feature_artifacts/2026-07-07/`
- `.runtime/operations/feature_artifacts/2026-07-08/`
- `.runtime/operations/feature_refresh/2026-07-06/`
- `.runtime/operations/feature_refresh/2026-07-07/`
- `.runtime/operations/feature_refresh/2026-07-08/`
- `.runtime/operations/feature_date_contract/2026-07-06.json`
- `.runtime/operations/feature_date_contract/2026-07-07.json`
- `.runtime/operations/feature_date_contract/2026-07-08.json`
- `.runtime/operations/feature_date_contract/2026-07-09.json`
- `.runtime/operations/feature_consumer_readiness/2026-07-06.json`
- `.runtime/operations/feature_consumer_readiness/2026-07-07.json`
- `.runtime/operations/feature_consumer_readiness/2026-07-08.json`

Not executed:

- 5BD Runtime run
- Resume of frozen failed run
- Trading State Reset / Restore / Rollback
- Submit / Execution
- J-Quants fetch
- Canonical update
- Registry event append / Registry architecture change
- Runtime resolver change
- Demo submit / Production access

## 15. Recommended Next Prefix

```text
Phase17-R
```

Work Name:

```text
Historical Runtime 5BD Smoke Test Clean Rerun
```
