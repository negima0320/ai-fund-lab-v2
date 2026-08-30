# Phase32-I — KI-001 Actual-Path Acceptance + KI-004 Safety Classification Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T001257154156Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T001257154156Z`
- Current source commit: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Audit mode: READ-ONLY correctness audit.
- Fresh-run/resume/replay/long Historical: NOT RUN.
- Future price/return/regime/MFE/MAE/campaign outcome/PnL: NOT USED.

Phase32-I introduced no source code change and no config change. This report is the only Phase32-I artifact added.

## Run Evidence Coverage

`run_state.json` reports:

- `status=RUNNING`
- `completed_business_days`: 19 business days
- coverage: `2022-10-03` through `2022-10-28`
- source commit carried by completed jobs: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`

Daily artifact coverage observed:

- daily directories: 19 (`2022-10-03` through `2022-10-28`)
- `day_completion` directories: 18 (`2022-10-03` through `2022-10-27`)
- `strategy/portfolio_construction.json` days: 19
- `position_management/pm_decisions.json` days: 19

The audit uses already-materialized run evidence only. The final day, `2022-10-28`, has strategy and PM artifacts and is included for REENTRY/PM artifact inspection; it is called out separately where completion state matters.

## EXIT And REENTRY Counts

From canonical PM artifacts at `daily/<date>/position_management/pm_decisions.json`:

- PM `EXIT` decisions: 22
- PM EXIT symbols: `83060`, `37820`, `89180`, `41650`, `44220`, `45750`, `33500`, `70640`, `92420`, `73590`, `76470`, `44870`, `48330`, `96100`, `66190`, `79220`, `62270`, `66630`, `93180`, `58200`, `69930`, `27210`

From execution artifacts:

- SELL/exit-related fills: 34

From `daily/<date>/strategy/portfolio_construction.json`:

- REENTRY portfolio member evaluations: 147
- REENTRY symbols observed: 23
- strict-prior date violations: 0
- missing prior exit date: 0

REENTRY examples were present, so the task is not evidence-insufficient for the main KI-001/KI-004 questions. The narrower multiple-same-symbol-multiple-campaign subcase was not conclusively exercised because each PM EXIT symbol appeared once in the inspected PM EXIT decision set.

## Part A — KI-001 Actual Path Acceptance

### Evidence Summary

Across 147 actual REENTRY portfolio member evaluations:

- `prior_exit_reason_class`
  - `TREND_MOMENTUM`: 55
  - `HARD_STOP`: 38
  - `GENERIC`: 54
- `prior_exit_reason`
  - `trend_and_opportunity_broken`: 55
  - `hard_stop_current_return`: 36
  - `SELL_EXIT`: 39
  - `weak_hold_score`: 10
  - `profit_retention_break`: 5
  - combined hard-stop/profit-retention or hard-stop/trend reasons: 2
- `prior_exit_context_status`
  - `PASS`: 93
  - `REVIEW_REQUIRED`: 54
- `prior_exit_provenance_status`
  - `REVIEW_REQUIRED`: 147
- required canonical provenance fields
  - non-empty `prior_campaign_id`: 0 / 147
  - non-empty `source_pm_decision_id`: 0 / 147
  - non-empty `source_decision_id`: 0 / 147
- `recovery_reason=insufficient_prior_exit_context`: 12 / 147

The Phase32-H failure pattern is not reproduced as a uniform collapse to `GENERIC`, `REVIEW_REQUIRED`, and `insufficient_prior_exit_context`. Actual REENTRY evaluations preserve concrete prior EXIT reason/class for a majority of rows: 93 / 147 have non-generic reason classes and 93 / 147 have `prior_exit_context_status=PASS`.

However, actual runtime evidence does not satisfy full Phase32-H acceptance because all 147 REENTRY rows still lose canonical provenance identifiers:

- `prior_campaign_id`
- `source_pm_decision_id`
- `source_decision_id`
- `prior_exit_provenance_status=PASS`

### Detailed Actual-Path Examples

`2022-10-05`, symbol `83060`:

- prior EXIT date: `2022-10-04`
- prior EXIT decision type: `EXIT`
- prior EXIT reason: `trend_and_opportunity_broken`
- prior EXIT reason codes: `trend_and_opportunity_broken`
- prior EXIT reason class: `TREND_MOMENTUM`
- prior EXIT context status: `PASS`
- recovery status/reason: `FAIL_CLOSED` / `reentry_trend_recovery_not_satisfied`
- missing: `prior_campaign_id`, `source_pm_decision_id`, `source_decision_id`
- provenance: `REVIEW_REQUIRED`

`2022-10-05`, symbol `89180`:

- prior EXIT date: `2022-10-04`
- prior EXIT decision type: `EXIT`
- prior EXIT reason: `hard_stop_current_return`
- prior EXIT reason codes: `hard_stop_current_return`
- prior EXIT reason class: `HARD_STOP`
- prior EXIT context status: `PASS`
- recovery status/reason: `FAIL_CLOSED` / `reentry_opportunity_not_requalified`
- missing: `prior_campaign_id`, `source_pm_decision_id`, `source_decision_id`
- provenance: `REVIEW_REQUIRED`

`2022-10-06`, symbol `33700`:

- prior EXIT date: `2022-10-05`
- prior EXIT decision type: `EXIT`
- prior EXIT reason: `SELL_EXIT`
- prior EXIT reason codes: empty
- prior EXIT reason class: `GENERIC`
- prior EXIT context status: `REVIEW_REQUIRED`
- recovery status/reason: `FAIL_CLOSED` / `reentry_opportunity_not_requalified`
- missing: `prior_campaign_id`, `source_pm_decision_id`, `source_decision_id`
- provenance: `REVIEW_REQUIRED`

`2022-10-13`, symbol `44220`:

- prior EXIT date: `2022-10-07`
- prior EXIT decision type: `EXIT`
- prior EXIT reason: `trend_and_opportunity_broken`
- prior EXIT reason codes: `trend_and_opportunity_broken`
- prior EXIT reason class: `TREND_MOMENTUM`
- prior EXIT context status: `PASS`
- recovery status/reason: `FAIL_CLOSED` / `reentry_opportunity_not_requalified`
- missing: `prior_campaign_id`, `source_pm_decision_id`, `source_decision_id`
- provenance: `REVIEW_REQUIRED`

### Strict-Prior Verification

All 147 observed REENTRY evaluations had `prior_exit_business_date < REENTRY business_date`.

The audit did not observe any row where the REENTRY evaluation used a same-day or future prior EXIT date. Source inspection is consistent with that artifact behavior: `_canonical_reentry_semantic_eligibility(...)` computes a temporal status as `PASS` only when the prior exit date is absent or strictly before the current business date.

This verifies strict-prior date ordering for the observed actual path. It does not fully verify multiple same-symbol campaign disambiguation because the inspected PM EXIT decision set did not contain repeated PM EXIT campaigns for the same symbol.

### Phase32-H Acceptance Judgment

Classification: `PARTIAL`

Reason:

- Accepted on actual path for semantic preservation of prior EXIT reason/class in many rows.
- Accepted on actual path for strict-prior date ordering.
- Not accepted for full canonical provenance preservation because all REENTRY rows still carry `prior_exit_provenance_status=REVIEW_REQUIRED` and have empty `prior_campaign_id`, `source_pm_decision_id`, and `source_decision_id`.

Therefore, Phase32-H KI-001 repair is not fully confirmed on actual Historical Runtime evidence.

## Part B — KI-004 Safety Classification Audit

### Evidence Summary

Across 147 REENTRY evaluations:

- `safety_restriction_status`
  - `FAIL_CLOSED`: 147
- `broker_eligibility_status`
  - `PASS`: 147
- `corporate_action_status`
  - `NO_EVENT`: 147
- `recovery_status`
  - `FAIL_CLOSED`: 133
  - `REVIEW_REQUIRED`: 12
  - `PASS`: 2
- `recovery_reason`
  - `reentry_opportunity_not_requalified`: 116
  - `reentry_trend_recovery_not_satisfied`: 10
  - `reentry_momentum_recovery_not_satisfied`: 5
  - `insufficient_prior_exit_context`: 12
  - `reentry_recovery_qualified`: 2
  - `reentry_buy_quality_not_requalified`: 1
  - `reentry_hard_stop_new_thesis_not_sufficient`: 1

The evidence shows concrete classification collapse: every REENTRY row is marked `safety_restriction_status=FAIL_CLOSED` while broker eligibility is `PASS` and corporate action status is `NO_EVENT`.

This is not judged from the `FAIL_CLOSED` label alone. It is judged from the contradictory separated statuses:

- no broker block is present,
- no corporate-action block is present,
- recovery/current-evidence/prior-context conditions explain the REENTRY denial,
- yet the safety restriction field is still marked fail-closed.

### Concrete Misclassification Examples

`2022-10-05`, symbol `83060`:

- recovery failure: `reentry_trend_recovery_not_satisfied`
- broker eligibility: `PASS`
- corporate action: `NO_EVENT`
- safety restriction: `FAIL_CLOSED`

This is a recovery/churn/current-evidence denial, not an observed broker or corporate-action block.

`2022-10-05`, symbol `89180`:

- recovery failure: `reentry_opportunity_not_requalified`
- broker eligibility: `PASS`
- corporate action: `NO_EVENT`
- safety restriction: `FAIL_CLOSED`

This is a renewed-opportunity failure, not a concrete safety/broker/corporate-action restriction.

`2022-10-06`, symbol `33700`:

- prior context: `REVIEW_REQUIRED`
- recovery failure: `reentry_opportunity_not_requalified`
- broker eligibility: `PASS`
- corporate action: `NO_EVENT`
- safety restriction: `FAIL_CLOSED`

This row demonstrates that prior-context insufficiency/current-evidence failure can still be collapsed into the safety restriction field.

### Source Contract Observation

The current source has distinct fields for:

- prior-exit context status,
- churn protection status,
- renewed current evidence status,
- candidate eligibility status,
- broker eligibility,
- corporate action,
- safety restriction.

But `_reentry_safety_status(...)` derives safety status from broad reason text and reason codes containing tokens such as `safety`, `broker`, `cash`, `buying_power`, and `corporate_action_blocking`. Actual run evidence shows this can mark the safety field as `FAIL_CLOSED` even where the explicit broker and corporate-action statuses are non-blocking and the denial is explained elsewhere.

### KI-004 Classification

Classification: `CONCRETE_DEFECT_REPRODUCED`

Reason:

- The current repaired run contains concrete REENTRY rows where non-safety denial reasons are represented as `safety_restriction_status=FAIL_CLOSED`.
- Broker and corporate-action evidence are separable and non-blocking in the same rows.
- This is a runtime/control classification defect, not a Strategy performance issue.

## Production Correctness And Repair

### KI-001

- Production correctness impact: YES. Prior EXIT semantics partially survive, but canonical provenance cannot be treated as accepted while all source/campaign ids are empty.
- Strategy semantic impact: NO observed parameter/threshold/weight/candidate-selection change.
- Runtime/control impact: YES. Acceptance and auditability remain degraded.
- Repair Required: YES, before Phase32 integration acceptance, unless a later already-materialized run proves the missing provenance fields become populated.

### KI-004

- Production correctness impact: YES. Consumers cannot reliably distinguish genuine safety/broker/corporate-action blocks from recovery/current-evidence/prior-context failures.
- Strategy semantic impact: NO. This is classification and control-plane semantics, not parameter selection.
- Runtime/control impact: YES.
- Repair Required: YES before Phase32 integration acceptance.

## Additional Evidence Needs

No additional Historical days are required to conclude the main Phase32-I findings because 147 REENTRY evaluations already exercise the actual path.

For the narrower multiple same-symbol campaign disambiguation subcase, current evidence is insufficient. To accept that subcase on actual runtime evidence, observe at least 2 symbols with two or more strict-prior closed campaigns and a later REENTRY evaluation for each. A practical next coverage target after repair would be approximately 30 to 60 additional business days, or until those examples appear.

Codex did not run any extension, resume, replay, or fresh-run.

## Confirmations

- NO CODE CHANGE in Phase32-I: YES.
- NO CONFIG CHANGE in Phase32-I: YES.
- NO Strategy/parameter/threshold/weight change in Phase32-I: YES.
- NO future-information use: YES.
- Historical PnL/return/profitability used: NO.
- Phase32-only architecture imported into Phase31 semantics: NO.

## Final Judgment

1. `IS_PHASE32_H_KI001_REPAIR_CONFIRMED_ON_ACTUAL_RUNTIME_EVIDENCE`
   - `PARTIAL`
   - Prior EXIT semantic reason/class preservation and strict-prior ordering are observed.
   - Full acceptance is blocked because campaign/source provenance remains missing in all observed REENTRY rows.

2. `DO_PRIOR_EXIT_SEMANTICS_SURVIVE_TO_REENTRY`
   - `PARTIAL_YES`
   - Prior EXIT reason and reason class survive for many actual rows and are not uniformly degraded to `GENERIC` / `insufficient_prior_exit_context`.
   - Canonical identity/provenance fields do not survive.

3. `IS_KI004_A_CONCRETE_CURRENT_DEFECT`
   - `YES`
   - Classification: `CONCRETE_DEFECT_REPRODUCED`.

4. `IS_ANY_REPAIR_REQUIRED_BEFORE_PHASE32_INTEGRATION_ACCEPTANCE`
   - `YES`
   - KI-001 still requires a narrow actual-path provenance completion repair.
   - KI-004 requires separation of safety/broker/corporate-action blocks from recovery/current-evidence/prior-context failures.

