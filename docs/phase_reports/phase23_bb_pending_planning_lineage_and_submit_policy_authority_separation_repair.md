# Phase23-BB Pending Planning Lineage and Submit Policy Authority Separation Repair

## Primary Judgment

```text
PHASE23_BB_PENDING_POLICY_AUTHORITY_SEPARATION_SHORT_VALIDATION_PASS
```

## Root Cause Repaired

Phase23-BAで確定したsemantic collisionを修正した。

```text
Planning Lineage Authority
!=
Submit Guard / Capital Deployment Policy Authority
```

旧来の `policy_version` / `policy_source` / `pending_policy_hash` は互換・非canonical fieldとして残し、Submit Guardの比較対象はcanonicalな以下へ分離した。

```text
submit_policy_version
submit_policy_source
submit_policy_hash
```

Planning lineageは以下へ分離した。

```text
planning_authority_version
planning_authority_source
planning_authority_hash
planning_lineage_context
```

## Producer / Consumer Boundary

```text
run_daily_operation
  -> explicit capital deployment policy resolution
  -> submit_policy_authority_payload
  -> activate_strategy_planning_authority
  -> promote_order_plan_to_pending
  -> pending serialization / reader
  -> submit.pipeline._policy_consistency_evidence
```

Submit Guardは `submit_policy_*` だけをactive Capital Deployment policyと比較する。Planning lineageとは相互比較しない。

## Fail-closed Preserved

- missing submit policy authority: `missing_submit_policy_evidence`
- missing approval submit policy authority: `missing_approval_submit_policy_evidence`
- submit policy mismatch: `policy_mismatch:pending_submit_policy_*`
- planning lineage missing: `missing_planning_lineage_evidence`

Submit Guard bypass、policy consistency無効化、expected policyのpending値への寄せ、Historical専用branchはいずれも未実施。

## Canonical Reproduction

BA相当の9件BUY pendingを一時rootで再生成し、以下を確認した。

```text
pending state = APPROVED
item count = 9
planning lineage present = true
submit policy authority present = true
planning lineage version != submit policy version
Submit Guard plan-level consistency = PASS
policy_mismatch = absent
```

## Validation

- py_compile: PASS
- `test_phase23_i_strategy_planning_authority.py -k phase23_bb`: 1 passed
- pending promotion: 5 passed
- submit guard policy regression: 10 passed
- strategy planning authority full file: 9 passed
- submit/data readiness temporal subset: 10 passed, 3 deselected
- data readiness pending/safety subset: 1 passed, 9 deselected
- historical submit targeted excluding non-BB adapter fixture gap: 8 passed, 1 deselected

Known non-BB gap: `test_phase17_g_historical_adapter_prefers_run_scoped_asof_hash_over_stale_manifest` fails with `historical logical source manifest missing`; this is unrelated to BB policy authority comparison.

## Existing Run Preservation

```text
existing_run_hash_preservation = True
```

Protected runs:

- `runtime-test-historical-smoke-20260730T042431441297Z`
- `runtime-test-historical-smoke-20260730T033913848127Z`
- `runtime-test-historical-smoke-20260730T030213466506Z`

## Deliverables

- Human: `docs/phase_reports/phase23_bb_pending_planning_lineage_and_submit_policy_authority_separation_repair.md`
- Machine: `reports/phase_reports/phase23_bb_pending_planning_lineage_and_submit_policy_authority_separation_repair.json`
- Evidence: `reports/phase23_bb_pending_planning_lineage_and_submit_policy_authority_separation_repair/`

## Final Gate

```text
READY_FOR_1BD_RUNTIME_RERUN = YES
```

Runtime rerunは未実施。Operatorが実施する。
