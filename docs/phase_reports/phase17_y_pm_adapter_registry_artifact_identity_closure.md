# Phase17-Y Position Management Adapter Registry Artifact Identity Closure

Final judgment: `PHASE17_Y_PM_ADAPTER_REGISTRY_ARTIFACT_IDENTITY_ACCEPTED`

## Summary

Phase17-Y closed the PM Runtime Adapter Registry blocker:

```text
artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER
```

This was not treated as a Historical-only relaxation. The formal Runtime authority remains common for Demo, Production, and Historical:

```text
POSITION_MANAGEMENT_POLICY_SET
  -> RUNTIME_ADAPTER
  -> ACCEPTED_CURRENT_PATH
  -> src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

Runtime continues to fail closed on path/hash mismatch.

## Evidence Classification

Failing command:

```text
python3 -m pytest -q tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py::test_registry_resolver_returns_current_pm_source_authority -vv
```

Failing test:

```text
test_registry_resolver_returns_current_pm_source_authority
```

Pre-closure mismatch:

| Item | Value |
|---|---|
| Registry entry path | `.runtime/artifact_registry/index/registry_index.json` |
| Accepted manifest path | `.runtime/artifact_registry/evidence/manifests/control_position_management_accepted_current_path_v3/artifact_set_manifest.json` |
| Artifact set id | `control.position_management.accepted_set` |
| Artifact member | `RUNTIME_ADAPTER` |
| Registry expected hash | `dc4325e00a68f7d530963c7b64dc0994e6c0f8952f7e09cb4031bb48a1d01c5f` |
| Runtime adapter path | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Actual source hash before closure | `2924fa7e132e9602653cd1033a9b6b6925f8ef419accfafd673b05bdba4e71df` |
| Legacy accepted copy hash | `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b` |
| HEAD source hash | `0e238f497dbc4b558cf4e955450ac0d63feb71d3f656f958b92d222f9086b8e5` |
| Source commit | `abf2d671ad09d5afcd1b8b122a4a5e7700f44b20` |
| Source dirty | `true` |

Root cause classification:

```text
Case C: Source実装だけが変更され、Artifact promotionが未実施
```

Secondary classification:

```text
Case D is intentionally true by contract: Runtime consumer reads source tree because RUNTIME_ADAPTER uses ACCEPTED_CURRENT_PATH.
```

This is not Case E. SHA256 values differ. It is not a path-only mismatch.

## Closure

Used the existing formal PM adapter authority writer path from Phase17-B1I-B through a Phase17-Y wrapper with a new evidence id:

```text
scripts/phase17_y_pm_adapter_registry_artifact_identity_closure.py
```

New evidence id:

```text
control_position_management_accepted_current_path_v4
```

New accepted PM set:

```text
control.position_management.accepted_set@sha256-c5b0524b3c744ecf
```

New accepted `RUNTIME_ADAPTER` hash:

```text
2924fa7e132e9602653cd1033a9b6b6925f8ef419accfafd673b05bdba4e71df
```

Old accepted PM set is now legacy:

```text
control.position_management.accepted_set@sha256-bcfb19410b272e04
```

The older copied adapter artifact remains legacy evidence only and is not Runtime authority:

```text
.runtime/artifacts/control/position_management/runtime_adapter/default/sha256-6ffa7da2b91f5fd5/runtime_adapter.py
```

## Validation

Formal writer gates passed:

- PM artifact set validated
- PM artifact set accepted
- Registry event log passed
- Registry index passed
- Registry checkpoint passed
- Resolver returns new PM set
- PM source hash preflight passed
- PM source hash mismatch remains fail-closed
- Current / Ledger / Pending unchanged
- Demo / Production / Historical use the same authority

Target verification passed:

```text
python3 -m pytest -q tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py::test_registry_resolver_returns_current_pm_source_authority tests/runtime_v2/test_phase15ap_position_management_input_contract.py::test_phase15ap_valid_pm_input_contract_allows_pm_and_sell_planning
```

Result:

```text
2 passed
```

Formal writer regression suites also passed:

- `tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py`
- `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/artifact_registry`

## Contract Notes

No Registry JSON was hand-edited. The closure used append-only Registry events and regenerated index/checkpoint via the formal writer path.

No Historical-only fallback was added. A future change to `producer.py` must again trigger formal PM adapter acceptance, or Runtime must halt before PM inference.
