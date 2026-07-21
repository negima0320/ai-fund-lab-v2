# Phase19-AD-U2-F Rolling Split Policy Human Review Approval

## Final Judgment

```text
PHASE19_AD_U2_ROLLING_SPLIT_POLICY_APPROVED
PHASE19_AD_U2_COMPLETE
PHASE19_AD_U3_READY
```

禁止された `BUY_READY`、`PRODUCTION_READY`、`ACCEPTED_GENERATION_CREATED`、`RUNTIME_TRANSITION_COMPLETE` は宣言していません。

## Human Review Decision

Reviewer: `user:negishi`

Decision: `APPROVE`

Policy Decision: `OPTION_C_CAPPED_EXPANDING_HYBRID`

`reviewed_hash` は承認済み `policy_hash` と一致します。

## Approved Rolling Split Policy

Window typeは `CAPPED_EXPANDING_HYBRID`。利用可能履歴を利用しつつ、最大履歴はプロジェクト全体の「約5年間学習」方針を基本とします。実営業日数への変換は固定値ではなく正式Trading Calendarを使います。

Validation、Test、Recent Holdoutは独立期間として維持します。Validation営業日数等はU2-Fでは固定せず、既存Evidence境界を維持します。

## Deferred Model Quality Items

以下は今回承認していません。

```text
minimum_training_rows
minimum_validation_rows
minimum_positive_labels
minimum_negative_labels
maximum_missing_ratio
```

これらは後続Model Quality Policyで決定します。Codexは推測値を入れていません。

## Versioned Split Generation

CandidateとOpportunityのversioned splitを生成しました。両方ともGeneration input artifactであり、Runtimeは直接利用しません。

Candidate split: `split_2edb9f39d8008b10`

Opportunity split: `split_61b5c8077880a82e`

## Split Validation

Split validationはPASSです。Embargoはtarget horizonと等しく20BD、Trading Calendar identityとpolicy hashを保持し、recent holdout endはlabel-safe dataset max内です。

## AD-U3 Dataset Input Contract

AD-U3 dataset input contractを更新しました。Candidate/Opportunity dataset revision、split_id、policy hash、Corporate Action policy、label-safe authorityを束縛しています。Unified GenerationやAccepted Generationはまだ作成していません。

## Bootstrap / Retraining Boundary

Bootstrapではprevious revisionとの差分を必須にしません。Retrainingではincremental label-safe business days、incremental rows、schema continuity、lineage continuityを判定します。

## Non-Mutation

Runtime/Trading Stateは不変。Broker writeは0。Candidate training、Opportunity training、Unified Generation、Accepted Decision、Runtime pointer、BUY restartは実行していません。

## Failure Injection

Draft policyからのsplit生成拒否、reviewed hash mismatch、embargo不足、calendar identity欠落、label-safe範囲超過、Deferred値の推測禁止、Runtime直接消費禁止、non-mutationを確認しました。

## Regression

```text
py_compile: PASS
pytest U2-F/U2-D/U2-C/U2-B/U2-A: 43 passed
```

## Evidence Paths

Evidence root: `reports/phase19_ad_u2_f_rolling_split_policy_approval/`

Summary: `reports/phase_reports/phase19_ad_u2_f_rolling_split_policy_approval.json`

## Remaining Work

AD-U2としての残作業はありません。次はAD-U3で、このdataset input contractを使ったCandidate/Opportunity training以降に進めます。Model Quality PolicyではDeferred項目を別途Evidenceに基づいて決定します。
