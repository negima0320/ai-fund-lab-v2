# Phase19-AD-U2-C Dataset Policy Blocker Closure and Rolling Split Policy Finalization

## Final Judgment

```text
PHASE19_AD_U2_C_HUMAN_REVIEW_REQUIRED
PHASE19_AD_U2_NOT_COMPLETE
PHASE19_AD_U3_NOT_READY
```

U2-C closed the ambiguity class by separating policy evidence from policy approval. It did not auto-approve corporate action limitations, did not select a rolling split policy without SoT-backed thresholds, and did not generate versioned splits.

## Corporate Action Source Inventory

Current lineage has J-Quants normalized quotes, listed issues, and trading calendar evidence. No standalone accepted corporate action event source, adjustment factor source, code-change source, merger/stock-transfer source, or restatement source is present as a formal policy authority.

## Corporate Action Policy Decision

Corporate action policy remains `HUMAN_REVIEW_REQUIRED`. Unknown or partial event classes are not implicit PASS. Future corporate action leakage remains a hard BLOCK condition.

## Label-Safe Field Semantics

U2-C separates `computed_label_safe_cutoff`, `dataset_target_date_max`, and legacy metadata `label_safe_cutoff`. The formal cutoff authority is the AI Lifecycle cutoff resolver using the formal trading calendar.

## Cutoff Mismatch Root Cause

The legacy metadata cutoff is `2026-06-04`, while the calendar-derived 20BD cutoff from latest source market date `2026-06-26` is `2026-05-29`. The materialized dataset max target date is `2026-05-15`, so included rows are label-safe, but the metadata mismatch is recorded and not silently accepted.

## Label-Safe Final Result

Formal row-level label-safe revalidation is `PASS` for Candidate and Opportunity under the clarified authority. Metadata semantics still require follow-up cleanup before this field is used as a sole authority elsewhere.

## Existing Split Evidence

Existing Phase18 training splits use time-series split with 20BD embargo and 20BD target horizon. Candidate train has 852 business dates; Opportunity train has 793; validation has 222; test has 39; recent holdout has 29. These are evidence only, not an approved U2-C policy.

## Rolling Split Policy Decision

Rolling split policy remains `HUMAN_REVIEW_REQUIRED` because SoT-backed `training_window_business_days`, `minimum_training_rows`, and complete component-specific thresholds are not formally approved. Split policy version changes require Human Review.

## Bootstrap vs Retraining Sufficiency Decision

U2-C separates first bootstrap generation input sufficiency from retraining trigger sufficiency. Retraining remains `INSUFFICIENT` with `NO_RETRAIN_INSUFFICIENT_NEW_DATA`. Bootstrap input sufficiency is `HUMAN_REVIEW_REQUIRED` due corporate action and split policy review.

## Generated Split Result

No versioned split was generated. `generated_versioned_splits.json` records `REVIEW_REQUIRED` outputs without `split_id`.

## AD-U2 Closure Decision

AD-U2 is not complete. Dataset revision exists and label-safe row revalidation is clarified, but corporate action and rolling split policy require Human Review before AD-U2 can close.

## AD-U3 Readiness

AD-U3 is not ready. No Candidate training, Opportunity training, calibration, accepted decision, runtime pointer, BUY restart, or broker write was performed.

## Non-Mutation

Trading state was not mutated, runtime pointer was not written, accepted decision was not written, BUY/SELL state was unchanged, and broker write count is 0.

## Failure Injection

Failure injection covers unknown corporate action handling, future corporate action leakage, label-safe cutoff mismatch, dataset max after computed cutoff, missing split policy thresholds, runtime split threshold override, policy hash mismatch after review, and bootstrap-vs-retraining sufficiency separation.

## Regression

```text
py_compile: PASS
pytest U2-C/U2-B/U2-A: 27 passed
```

## Changed Files

Primary U2-C implementation files:

- `src/ai_fund_lab_v2/ai_lifecycle/dataset_revision_materialization.py`
- `tests/ai_lifecycle/test_phase19_ad_u2_c_dataset_policy_blocker_closure.py`
- `docs/phase_reports/phase19_ad_u2_c_dataset_policy_blocker_closure.md`
- `reports/phase19_ad_u2_c_dataset_policy_blocker_closure/`
- `reports/phase_reports/phase19_ad_u2_c_dataset_policy_blocker_closure.json`

## Evidence Paths

Evidence root: `reports/phase19_ad_u2_c_dataset_policy_blocker_closure/`

Summary: `reports/phase_reports/phase19_ad_u2_c_dataset_policy_blocker_closure.json`

## Remaining Work

Human Review must decide the corporate action formal limitation/source policy and approve a concrete rolling split policy hash. Only after that may U2 generate versioned splits and produce an AD-U3 dataset generation input manifest.
