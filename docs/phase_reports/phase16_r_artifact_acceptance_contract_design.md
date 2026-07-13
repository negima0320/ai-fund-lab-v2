# Phase16-R Artifact Acceptance Contract Design

## Summary

- Prefix: `Phase16-R`
- Work: `Artifact Acceptance Contract and Promotion Workflow Design`
- Final judgment: `PHASE16_R_ARTIFACT_ACCEPTANCE_CONTRACT_ACCEPTED`
- Implementation: not performed
- Registry production: not performed
- Artifact promotion: not performed
- Runtime / Consumer change: not performed
- Simulation / Historical Test / Reset: not performed

This phase defines the formal `VALIDATED -> ACCEPTED` contract required before Registry production implementation or Runtime consumer migration.

## Deliverables

- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase16_r_artifact_acceptance_contract_design.md`
- `reports/phase_reports/phase16_r_artifact_acceptance_contract_design.json`

## Artifact Lifecycle

Formal lifecycle:

```text
DRAFT
↓
VALIDATED
↓
REVIEW_REQUIRED
↓
ACCEPTED
↓
LEGACY
↓
REVOKED
```

The lifecycle is not strictly linear. `VALIDATED` may become `ACCEPTED`, `REVIEW_REQUIRED`, or `REJECTED`; `ACCEPTED` may become `LEGACY` or `REVOKED`; `LEGACY` may be re-accepted only through rollback acceptance.

Runtime use is allowed only for:

```text
accepted_status=ACCEPTED
runtime_use_eligible=true
hash/schema/consumer checks pass
```

All other statuses are Runtime-ineligible.

## Acceptance Authority

Only the combined acceptance authority may promote to `ACCEPTED`:

- Human Review
- Architecture Acceptance
- Regression Acceptance
- Release Approval

The following are explicitly prohibited from self-promotion:

- Runtime
- AI
- Registry
- CLI
- Feature generators
- Simulation / backtest tools
- Report generators

## Acceptance Criteria

Common criteria:

- hash verified
- schema verified
- artifact instance stable
- artifact set hash stable when applicable
- producer identified
- consumer identified
- source refs and hashes recorded
- evidence exists
- point-in-time contract reviewed
- regression passes
- review passes
- rollback/replacement/revoke plan exists

Component-specific criteria:

- Candidate: model, manifest, training evidence, validation evidence, Candidate inference regression, point-in-time feature review.
- Opportunity: model, metrics, model/metrics pair binding, training/validation evidence, ranking regression, Phase5-E fallback resolution.
- PM: code-policy hash, adapter hash, decision output contract, PM decision parity, no hidden liquidation/cleanup authority.
- Capital Allocation: policy hash/schema, owner approval, Planning/Pending/Submit Guard regression, standalone decision artifact decision recorded.

## Regression

Minimum gates:

- Semantic Equality
- Current unchanged
- Ledger unchanged
- Pending unchanged
- Planning unchanged
- Runtime state machine unchanged
- Feature schema/calculation unchanged unless explicitly accepted
- AI inference unchanged for Registry/path-only migration
- Report additions must not alter Runtime authority

Model replacement may intentionally change model output, but still requires fixed validation evidence, approved performance deltas, safety review, and Runtime integration regression.

## Review Workflow

Formal workflow:

```text
Artifact generation
↓
Read-only inventory
↓
DRAFT Registry event candidate
↓
Validation
↓
VALIDATED
↓
Human and architecture review
↓
Regression gate
↓
Acceptance report
↓
ACCEPTED event
↓
Runtime-use eligibility enabled for named consumers
```

Inventory and validation alone do not allow Runtime use.

## Promotion

Promotion is an append-only Registry event, not a file mutation. The acceptance event must reference an immutable acceptance report with reviewer, timestamp, hash, schema, artifact set, Regression result, Runtime version, Git commit, environment scope, rollback plan, and revoke conditions.

## Rollback

Rollback is represented by new events:

```text
current ACCEPTED -> LEGACY or REVOKED
previous LEGACY -> ACCEPTED through rollback acceptance event
```

Rollback requires reviewer approval, hash re-verification, schema compatibility, consumer compatibility, minimal regression, and impact report.

## Revoke

Artifacts must move to `REVOKED` for hash mismatch, schema mismatch, wrong producer/consumer, look-ahead leakage, future listed/corporate-action misuse, incorrect model/metrics pair, silent fallback to unaccepted artifact, corruption, secret exposure, unsafe behavior, or falsified/incomplete evidence.

Runtime must never use `REVOKED` artifacts.

## Replacement

New version flow:

```text
new artifact -> DRAFT -> VALIDATED -> ACCEPTED
old artifact -> LEGACY
```

Old artifacts are retained for evidence. They are not Runtime-eligible unless a rollback acceptance event re-accepts a specific previous instance.

## Runtime Impact

The contract changes no Runtime behavior and does not modify:

- Runtime Authority
- Current
- Ledger
- Pending
- State Machine
- Feature
- AI

The contract only defines when future Runtime consumers may be allowed to use registered artifacts.

## Unresolved Items

- Registry production implementation.
- Acceptance event JSON schema.
- Acceptance report template.
- Corporate Action source-of-truth decision.
- Opportunity Phase5-E fallback resolution.
- Historical Runtime canonical feature source acceptance.

## Next Prefix

Recommended next prefix: `Phase16-S`

Recommended scope: Registry production implementation design or acceptance schema/template design. Do not begin Registry implementation until the next instruction explicitly authorizes it.
