# Phase19-AD-U2-D Corporate Action Policy Approval

## Final Judgment

```text
PHASE19_AD_U2_D_CORPORATE_ACTION_POLICY_APPROVED_WITH_FORMAL_LIMITATION
PHASE19_AD_U2_NOT_COMPLETE
PHASE19_AD_U3_NOT_READY
```

Corporate Action policy was materialized from the user Human Review decision as `APPROVE_WITH_FORMAL_LIMITATION`. Rolling Split remains `HUMAN_REVIEW_REQUIRED`; no split thresholds were decided and no versioned split was generated.

## Human Review Decision

Decision: `APPROVE_WITH_FORMAL_LIMITATION`

Reviewer: `user:negishi`

Codex is not the reviewer. The Human Review artifact binds `reviewed_hash` to the policy hash.

## Corporate Action Policy

Corporate Action event handling is a Common PIT Dataset quality-layer responsibility. AI layers may use only formal dataset features and label-safe targets. AI layers must not directly ingest Corporate Action events or future adjustment information.

Current Corporate Action sufficiency result: `PASS_WITH_FORMAL_LIMITATION`.

## Dataset / AI Responsibility Boundary

Dataset layer preserves PIT, prevents future leakage, guarantees label-safe rows, records source cutoff/revision/policy hash, and excludes or blocks corporate-action-corrupted rows. AI layer consumes only formal dataset features and does not train on test, audit, runtime, paper, broker, or PnL results.

## Formal Limitations

- Standalone accepted Corporate Action Event SoT: `NOT_AVAILABLE`
- Adjustment Factor dedicated SoT: `NOT_FORMALLY_ACCEPTED`
- Code Change mapping: `NOT_FORMALLY_ACCEPTED`
- Merger / Stock Transfer mapping: `NOT_FORMALLY_ACCEPTED`
- Restatement lifecycle: `NOT_FORMALLY_ACCEPTED`

These limitations no longer automatically block the current dataset while hard block conditions are false and current features/labels do not require standalone event inputs.

## Hard Block Conditions

Future corporate action leakage, future adjustment leakage, PIT authority gaps, security identity collision, historical universe silent removal, feature/label corruption, source revision unbound, and policy hash mismatch all remain BLOCK conditions.

## Training Prohibited Input Audit

Actual Candidate/Opportunity materialized dataset columns contain no prohibited backtest/runtime/paper/broker/test/audit/corporate-action/adjustment field as training input or target. Future-return columns are label-safe targets, not inference features or Corporate Action event inputs.

## Future Leakage Guard

Future Corporate Action and future adjustment inputs are prohibited. Re-evaluation found no active hard block flag in the current dataset evidence.

## Dataset Revision Policy Binding

Candidate and Opportunity received append-only policy-amended revisions under `.runtime/ai_lifecycle/dataset_revisions/phase19_ad_u2_d_corporate_action_policy_approval/`. Existing U2-B revisions were not overwritten.

## Label-Safe Authority Result

Label-safe authority remains computed cutoff plus formal trading calendar plus target horizon plus per-symbol label availability. Computed cutoff is `2026-05-29`; dataset max is `2026-05-15`; row-level label-safe remains `PASS`. Legacy metadata alone is not authority.

## Rolling Split Status

Rolling Split remains `HUMAN_REVIEW_REQUIRED` with `split_id = NONE` and `versioned_split_generated = false`.

## AD-U2 Closure Status

AD-U2 is not complete because Rolling Split policy remains unapproved.

## AD-U3 Readiness

AD-U3 is not ready. No Candidate training, Opportunity training, calibration, Unified Generation, Accepted Decision, Runtime pointer, BUY restart, or Broker write was performed.

## Non-Mutation

Runtime/trading state was not mutated. Broker write count is 0.

## Failure Injection

FI-1 through FI-11 passed, including future leakage BLOCK, prohibited training input BLOCK, reviewed-hash mismatch, missing reviewer invalidation, rolling split runtime override rejection, and non-mutation.

## Regression

```text
py_compile: PASS
pytest U2-D/U2-C/U2-B/U2-A: 37 passed
```

## Evidence Paths

Evidence root: `reports/phase19_ad_u2_d_corporate_action_policy_approval/`

Summary: `reports/phase_reports/phase19_ad_u2_d_corporate_action_policy_approval.json`

## Remaining Work

Rolling Split policy Human Review remains the only AD-U2 blocker carried forward from U2-D.
