# Phase17-P Daily Feature Artifact Runtime Authority Audit

## Summary

Final judgment:

```text
PHASE17_P_OPERATIONAL_PROMOTION_PATH_CONFIRMED
```

Phase17-P was a read-only audit. No Runtime code, resolver, Registry, Feature Date Contract, Feature Artifact, trading state, reset, submit, execution, J-Quants fetch, or 5BD Runtime execution was changed.

The current Runtime v2 authority for daily Feature Artifact selection is not Registry active set. It is a combined path:

```text
Feature Date Contract
  -> selected_feature_date
  -> --feature-date passed by scripts/runtime_test.py
  -> run_daily_operation.py keeps explicit feature_date unchanged
  -> buy_ai.producer reads <feature_root>/<feature_date>/<fixed parquet name>
```

With the default Runtime CLI feature root, the effective read paths are:

```text
.runtime/operations/feature_artifacts/<selected_feature_date>/candidate_features.parquet
.runtime/operations/feature_artifacts/<selected_feature_date>/opportunity_feature_input.parquet
```

## Read Materials

- Phase17-K: `docs/phase_reports/phase17_k_runtime_test_command_runner.md`
- Phase17-L: `docs/phase_reports/phase17_l_historical_asof_and_evidence_isolation_closure.md`
- Phase17-M: `docs/phase_reports/phase17_m_historical_consumer_wiring_and_feature_temporal_authority_closure.md`
- Phase17-N: `docs/phase_reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review.md`
- Phase17-O: `docs/phase_reports/phase17_o_historical_5bd_feature_artifact_point_in_time_regeneration.md`
- Runtime Architecture / temporal contract: `docs/02_architecture/runtime_temporal_freshness_contract.md`
- Artifact path migration contract: `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`
- AI I/O artifact contract: `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- Runtime code: `scripts/runtime_test.py`, `run_daily_operation.py`, `buy_ai/producer.py`, `market_refresh/feature_date_contract.py`, `market_refresh/consumer_readiness.py`, `market_refresh/pipeline.py`, `planning/morning_pipeline.py`, `storage/path_resolver.py`

## Authority Classification

| Candidate | Current role | Judgment | Evidence |
|---|---:|---|---|
| A. Registry active set | No daily feature instance path selection | Not current authority | Registry index has `features.shared.accepted_set`, but no 5BD daily feature instance entries. `buy_ai` uses Registry for model/control/schema sets, then reads feature parquet by path. |
| B. Feature Date Contract | Selects `selected_feature_date` | Date authority | `scripts/runtime_test.py` loads/resolves `.runtime/operations/feature_date_contract/<business_date>.json`. |
| C. `latest_features.json` | Fallback latest marker only | Not direct Runtime read authority | `feature_date_contract._latest_available_from_markers()` reads it only when needed to resolve latest available market date. |
| D. Fixed date directory | Resolves actual parquet paths | Artifact path authority | `produce_buy_ai_decisions()` builds `feature_dir = feature_root / feature_date`. |
| E. Runtime/market manifests | Evidence/producer outputs | Not consumer authority | Manifests record refresh evidence; they do not redirect Candidate/Opportunity input paths. |
| F. Combination | B + D, with C as fallback | Current authority | This is the observed Runtime v2 path. |

## Runtime Call Graph

5BD Runtime Test path:

```text
scripts/runtime_test.py build_plan
  -> resolve_feature_date()
  -> selected_feature_date
  -> runtime_cli_command(... --feature-date selected_feature_date)
  -> run_daily_operation.py
  -> _resolve_buy_ai_feature_date() returns explicit --feature-date unchanged
  -> produce_buy_ai_decisions()
  -> <feature_root>/<feature_date>/candidate_features.parquet
  -> <feature_root>/<feature_date>/opportunity_feature_input.parquet
```

`storage/path_resolver.py` is not the daily Feature Artifact resolver. It resolves Current/history/derived Runtime paths.

## 5BD Resolution Trace

| Business date | Selected feature date | Contract source | Contract status | Runtime Candidate hash | Runtime Opportunity hash |
|---|---:|---|---|---|---|
| 2026-07-06 | 2026-07-06 | materialized contract | REVIEW_REQUIRED | `7c71b58db665861eb9dee6d63e734ccf5f47073a8ee5578a0b8c0fc7e8bc2432` | `8337a87f3137b2d89d278d87ccde5273162e7a5e4ec03c031baa464c47016fa2` |
| 2026-07-07 | 2026-07-07 | audit reconstructed, contract missing | RECONSTRUCTED_NO_MATERIALIZED_CONTRACT | `f791c72e02856ff2b21c4536b7659a4c93d4071424909d86724dc7bb4bf3708e` | `864e1b7e7507841b4e5ebb884957a9b2d4179c24b3afbc0ce24b9ab39cefa95e` |
| 2026-07-08 | 2026-07-07 | materialized contract | PASS | `f791c72e02856ff2b21c4536b7659a4c93d4071424909d86724dc7bb4bf3708e` | `864e1b7e7507841b4e5ebb884957a9b2d4179c24b3afbc0ce24b9ab39cefa95e` |
| 2026-07-09 | 2026-07-08 | materialized contract | PASS | `a85637b77a54586f4ca9c74c6478bf13f5d68bd44021443d89e032f5403a6e3d` | `2a7d53e41aa9af2ebed2601ac75e70a71bb10d609249723d2d1068d12bf236ce` |
| 2026-07-10 | 2026-07-10 | materialized contract | PASS | `2fcda90a6bf124db6ff77b96bd1905be875ae717659ddaa27ab7ce93d3790567` | `ca1e7b31105206625f6a3ab6b44686ca088348c9d59b5aa4a203e49f8a13719e` |

Current Runtime will not read Phase17-O regenerated artifacts under `.runtime/artifacts/features/historical_regenerated/...` unless they are promoted into the operational path or the authority contract/resolver is changed.

## Phase17-O Regenerated Artifacts

| Feature date | Candidate hash | Opportunity hash | Current Runtime selection |
|---|---|---|---|
| 2026-07-06 | `278dc623afb0690841d58949d344ef190caa3776f9e53ea520cd2bd964e50c3d` | `44bd9e6295d3fde5f5dfe3eac03faf457e5b13e3bdd60d76a33357278cbb6a2c` | Not selected without promotion |
| 2026-07-07 | `ae1948afc081d036e6e2ebbac37d86ce766c1e768bd3ca32934d884dd7f8801d` | `ac61f57cb113360a2c5033a493a3f73daa3569b48518d81c49178d49d928d935` | Not selected without promotion |

The regenerated files exist under:

```text
.runtime/artifacts/features/historical_regenerated/<date>/phase17-o-historical-feature-set-<date>-attempt002/runtime_like/feature_artifacts/<date>/
```

## 2026-07-09 Requirement

`2026-07-09` is not solved by reusing the regenerated `2026-07-07` artifact. Its materialized Feature Date Contract selects:

```text
selected_feature_date = 2026-07-08
carryover_reason = requested_feature_date_missing_latest_available_within_freshness_limit
```

Therefore, for 5BD without changing Runtime semantics, `2026-07-08` needs a consumer-ready artifact set at the operational authority path:

```text
.runtime/operations/feature_artifacts/2026-07-08/
```

Changing 2026-07-09 to read 2026-07-07 would be a Feature Date Contract / freshness-policy change, not a promotion of existing Runtime authority.

## Registry Role

The current Registry index contains five runtime eligible accepted sets:

- `ai.candidate.accepted_set`
- `ai.opportunity.accepted_set`
- `control.capital_allocation.accepted_set`
- `control.position_management.accepted_set`
- `features.shared.accepted_set`

No Registry entry currently selects daily feature artifact instances for `2026-07-06` through `2026-07-10`. `features.shared.accepted_set` is schema authority, not daily parquet instance authority.

## Latest Marker Role

`latest_features.json` exists as feature refresh evidence and as fallback input for `_latest_available_from_markers()`. It is not the direct Candidate/Opportunity read authority in the 5BD Runtime Test path because `scripts/runtime_test.py` passes explicit `--feature-date`, and `run_daily_operation.py` returns explicit `args.feature_date` unchanged.

## Same Artifact / Dedup Behavior

Current behavior is path-based:

- Same bytes at the selected operational path are read as-is.
- Same bytes at a different path are not discovered by content hash.
- There is no current daily-feature Registry deduplication or active-set switch.
- A regenerated artifact under `.runtime/artifacts/features/historical_regenerated/...` remains unused until operationally promoted or the authority/resolver is changed.

## Adoption Options

| Option | Runtime code change | 5BD fit | Judgment |
|---|---:|---|---|
| Operational promotion into `.runtime/operations/feature_artifacts/<date>/` | No | Best minimal path | Recommended |
| Feature Date Contract path references immutable regenerated paths | Yes | Not minimal | Defer |
| Daily feature Registry active set | Yes | Architecture change | Not needed for 5BD |
| `latest_features.json` switch | No | Insufficient | Not enough |
| Test runner path override | Yes | Prohibited | Reject |

Minimal next action:

1. Regenerate and accept `2026-07-08` with the same formal PIT/consumer-ready discipline used for Phase17-O.
2. Perform formal operational promotion for `2026-07-06`, `2026-07-07`, and `2026-07-08` into `.runtime/operations/feature_artifacts/<date>/`.
3. Include backup, hash manifest, pre/post evidence, and no Runtime resolver change.

## Blocking

- `2026-07-08` regenerated/consumer-ready artifact set is still required for `2026-07-09`.
- Existing regenerated `2026-07-06` and `2026-07-07` artifacts are not adopted by current Runtime authority until promoted.
- Formal operational promotion runbook/manifest is required before replacing operational feature artifacts.

## Non-Blocking

- New daily feature Registry active-set architecture is not necessary for 5BD.
- `latest_features.json` does not need to become a pointer authority for 5BD.
- `storage/path_resolver.py` does not need Feature Artifact support for the current 5BD path.

## Acceptance Gates

| Gate | Result |
|---|---|
| RUNTIME_CALL_GRAPH_COMPLETE | PASS |
| FEATURE_DATE_RESPONSIBILITY_IDENTIFIED | PASS |
| ARTIFACT_PATH_RESOLVER_IDENTIFIED | PASS |
| REGISTRY_ROLE_IDENTIFIED | PASS |
| LATEST_MARKER_ROLE_IDENTIFIED | PASS |
| 2026_07_06_RESOLUTION_TRACED | PASS |
| 2026_07_09_RESOLUTION_TRACED | PASS |
| SAME_ARTIFACT_BEHAVIOR_IDENTIFIED | PASS |
| REGENERATED_ARTIFACT_ADOPTION_PATH_IDENTIFIED | PASS |
| 2026_07_08_REQUIREMENT_IDENTIFIED | PASS |
| NO_IMPLEMENTATION_CHANGE | PASS |
| NO_TRADING_STATE_MUTATION | PASS |

## Evidence Files

- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/read_audit.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/runtime_call_graph.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/feature_date_authority_trace.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/candidate_resolution_trace.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/opportunity_resolution_trace.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/registry_role_audit.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/latest_marker_audit.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/same_artifact_deduplication_audit.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/regenerated_artifact_adoption_options.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/five_bd_resolution_trace.json`
- `reports/phase17_p_daily_feature_artifact_runtime_authority_audit/minimal_change_recommendation.json`

## Recommended Next Prefix

```text
Phase17-Q
```

Recommended work name:

```text
Daily Feature Artifact Operational Promotion
```
