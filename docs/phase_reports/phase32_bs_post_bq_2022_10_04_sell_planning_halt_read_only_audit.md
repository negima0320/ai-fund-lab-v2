# Phase32-BS — Post-BQ 2022-10-04 sell_planning HALT READ-ONLY Root Cause Audit

## Scope

Target run:

```text
runtime-test-historical-extended-smoke-20260831T224727109611Z
```

Observed state:

```text
fresh-run start = 2022-10-03
completed_days = [2022-10-03]
halt = 2022-10-04:sell_planning
sell_planning exit_code = 20
runtime_test final status = HALT
```

This was a READ-ONLY audit. No source, config, runtime state, Pending, Ledger, fresh-run, resume, recover, or replay mutation was performed.

## Primary Evidence

Inspected evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/sell_planning/cli_result.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/sell_planning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/sell_planning/data_readiness_authority.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/strategy/position_management.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/strategy/strategy_intelligence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T224727109611Z/daily/2022-10-04/strategy/market_context.json`
- `.runtime/runtime_state/sell_pipeline/2022-10-04/order_plan.json`
- `.runtime/runtime_state/sell_pipeline/2022-10-04/approval_artifact.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `docs/phase_reports/phase32_bq_lot_blocked_reduce_reconsidered_full_exit_production_implementation.md`
- `docs/phase_reports/phase32_br_bq_expected_first_divergence_date_read_only_check.md`

The BO/BQ shadow classification for 2022-10-04 was additionally reconstructed in memory from existing artifacts only. No shadow artifact was written.

## Run / Authority State

`run_state.json` shows the run completed only 2022-10-03 and stopped with the next job at:

```text
2022-10-04:sell_planning
```

The run-level historical evaluation authority was valid:

```text
historical_evaluation_authority_validation.status = PASS
historical_evaluation_authority.status = PASS
```

The sell planning subprocess evidence records:

```text
source_commit observed by subprocess = cf0a00b0271d170094aa0ce2bfbedc203c364406
source_dirty = true
runtime_test source commit argument = ff1d23157cced619c5820898f8317a7440e6092c
```

This source identity difference is observable, but the first canonical HALT reason is not an accepted-generation or adapter hash mismatch. The inspected runtime evidence reaches sell planning and fails on a sell-planning contract reason.

## HALT Canonical Reason

The first canonical failure is in the sell planning Pending pipeline:

```text
final_state = REVIEW_REQUIRED
exit_code = 20
reason = sell planning pipeline review required: MISSING_CAMPAIGN_ID;MISSING_CAMPAIGN_ID
```

The `sell_planning_pending_pipeline` stage reports:

```text
status = REVIEW_REQUIRED
reason = MISSING_CAMPAIGN_ID;MISSING_CAMPAIGN_ID
```

The sell pipeline order plan confirms the affected lot-blocked REDUCE reconsideration items:

| symbol | PM action | PM decision id | status | reason | campaign_id in failing BQ handoff |
|---|---|---|---|---|---|
| 92420 | REDUCE | `pm-2022-10-04-92420-reduce` | FAIL_CLOSED | MISSING_CAMPAIGN_ID | empty |
| 33700 | REDUCE | `pm-2022-10-04-33700-reduce` | FAIL_CLOSED | MISSING_CAMPAIGN_ID | empty |

Both were light REDUCE decisions whose executable reduce quantity rounded to zero:

```text
raw_reduce_quantity = 25.0
rounded_reduce_quantity = 0.0
final_sell_quantity = 0.0
reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
```

## Failure Path

The path to the HALT is:

```text
PM REDUCE for 92420 / 33700
-> PS materializes REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT with final_sell_quantity = 0
-> runtime_planning materializes NO_ORDER for both REDUCEs
-> BQ lot-blocked REDUCE reconsideration runs inside sell_planning
-> BQ reconsideration reads SellExitDecision / quantity_contract without campaign_id
-> _lot_blocked_reduce_full_exit_reconsideration marks both items FAIL_CLOSED: MISSING_CAMPAIGN_ID
-> sell_planning_pending_pipeline aggregates both failures
-> sell_planning returns REVIEW_REQUIRED exit_code 20
-> runtime_test reports HALT
```

The first bad boundary is:

```text
strategy/runtime planning no-order REDUCE
-> sell_planning BQ lot-blocked REDUCE reconsideration handoff
```

At that boundary, PM still has canonical campaign ids, but the BQ sell-planning handoff receives the lot-blocked REDUCE decisions with an empty `position_campaign_id` / `campaign_id`.

PM campaign ids in the source artifacts:

| symbol | PM campaign id |
|---|---|
| 92420 | `pc-ce2847e3c5043ecb-92420-0001` |
| 33700 | `pc-d6a2ff4b21cd321c-33700-0001` |

The downstream PS/runtime planning rows for these same no-order REDUCEs do not preserve `position_campaign_id` / `campaign_id`, and the BQ helper fail-closes before the BO semantic result can be classified as non-promoted.

## BQ Eligibility and Full-Exit Check

Phase32-BR established:

```text
EXPECTED_FIRST_BQ_DIVERGENCE_DATE = 2022-10-07
```

The 2022-10-04 lot-blocked REDUCE rows are structurally eligible for BO/BQ reconsideration inspection because they are:

```text
PM action = REDUCE
final executable reduce quantity = 0
reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
PIT source evidence available
```

However, in-memory reconstruction from the canonical current-run Strategy artifacts classified both 92420 and 33700 as:

```text
shadow_binary_authority_status = PASS
shadow_binary_eligibility_status = PASS
shadow_binary_decision = SHADOW_INSUFFICIENT_EVIDENCE
production_actual_action = NO_ORDER
production_actual_quantity = 0.0
pit_validation_state = PASS
```

Therefore:

```text
BQ promotion eligibility = NO
BQ FULL_EXIT expected on 2022-10-04 = NO
BQ FULL_EXIT attempted/materialized = NO
expected old Production outcome = NO_ORDER
```

The failure occurs before a non-promoted BO result can be allowed to remain an ordinary no-order REDUCE.

## Source Code Boundary

The relevant current source path is `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`.

`_apply_lot_blocked_reduce_full_exit_reconsiderations` applies `_lot_blocked_reduce_full_exit_reconsideration` to every non-executable REDUCE quantity contract.

Inside `_lot_blocked_reduce_full_exit_reconsideration`, the current order is:

```text
derive campaign_id from SellExitDecision / quantity_contract
validate required fields
if campaign_id is empty, return FAIL_CLOSED: MISSING_CAMPAIGN_ID
only after that build BO shadow payload
only after that inspect SHADOW_FULL_EXIT vs non-promoted decisions
```

This ordering is correct for materializing a promoted FULL EXIT, but too broad for non-promoted BO outcomes. It turns a promote-ineligible lot-blocked REDUCE into a sell-planning HALT solely because the BQ handoff lacked a campaign id, even though the canonical PM artifact can resolve the campaign and the BO result is not `SHADOW_FULL_EXIT`.

## Pending / Review Context

Morning created an active same-date Pending:

```text
pending_plan_id = pending-strategy-plan-historical-2022-10-04-2cf4449e0ba7acba
state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
```

The Pending contained approved SELL_EXIT items and reviewed BUY items. This was not the first failing invariant. The HALT reason came from BQ lot-blocked REDUCE reconsideration failures:

```text
MISSING_CAMPAIGN_ID;MISSING_CAMPAIGN_ID
```

There is no evidence that the reviewed BUY Pending contract itself caused the sell_planning HALT.

## Safety / Temporal / Data Readiness Context

The data readiness and safety authorities did not fail:

```text
data_readiness_status = READY
safety_status = PASS
safety_decision = NEUTRAL
data_readiness_historical_neutral_authority_generated_or_resolved = true
```

No stale Corporate Action, stale safety, feature-date, future-date, or broker safety failure is the first canonical cause.

## Classification

| Question | Answer |
|---|---|
| caused by BQ source/authority/registry/adapter changes despite no BQ action expected yet | YES, caused by BQ sell-planning code path / authority handling, not by registry/hash |
| caused by pre-existing sell_planning safety/contract defect | PARTIAL, a pre-existing campaign materialization gap is exposed, but the post-BQ fail-closed scope is the immediate defect |
| caused by accepted-generation/hash/source synchronization | NO concrete evidence |
| caused by evidence/provenance/schema mismatch introduced by BQ | YES, BQ requires campaign id at the wrong point for non-promoted no-order REDUCE cases |
| unrelated to BQ | NO |

Detailed root-cause class:

```text
POST_BQ_GLOBAL_SELL_PLANNING_RECONSIDERATION_FAIL_CLOSED_SCOPE_DEFECT
```

This is earlier than the expected first BQ production divergence and therefore is a BQ regression in the sell-planning control path, not an intended Strategy behavior change.

## Required Answers

1. `HALT_CANONICAL_REASON`

```text
sell planning pipeline review required: MISSING_CAMPAIGN_ID;MISSING_CAMPAIGN_ID
```

2. `FAILING_CONTRACT`

```text
BQ PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT sell-planning handoff requires campaign_id before determining that a lot-blocked REDUCE is not promotable to FULL_EXIT.
```

3. `BQ_RECONSIDERATION_ELIGIBLE_ON_2022_10_04`

```text
YES for structural BO inspection: 92420 and 33700 are PM REDUCE decisions blocked by discrete-lot zero executable quantity.
NO for Production promotion: both classify as SHADOW_INSUFFICIENT_EVIDENCE, not SHADOW_FULL_EXIT.
```

4. `BQ_FULL_EXIT_ATTEMPTED`

```text
NO. No FULL_EXIT was promoted/materialized. The path fail-closed before non-promoted BO decisions could remain NO_ORDER.
```

5. `BQ_DIRECT_CAUSE`

```text
YES. The newly introduced BQ reconsideration path produced the sell_planning REVIEW_REQUIRED failure.
```

6. `BQ_INDIRECT_SOURCE_AUTHORITY_CAUSE`

```text
YES/PARTIAL. The BQ path exposed missing campaign materialization in the PS/runtime_planning/SellExitDecision handoff, although PM artifacts contain canonical campaign ids.
```

7. `ACCEPTED_GENERATION_OR_HASH_MISMATCH`

```text
NO. The first canonical failure is not a registry, accepted-generation, adapter, or artifact hash mismatch.
```

8. `PENDING_OR_REVIEW_CONTRACT_CAUSE`

```text
NO as root cause. Pending review state exists, but the first failing invariant is BQ MISSING_CAMPAIGN_ID on lot-blocked REDUCE reconsideration.
```

9. `PROVENANCE_OR_CAMPAIGN_IDENTITY_CAUSE`

```text
YES as the immediate missing field, but the correctness defect is the BQ fail-closed scope/order that makes this fatal for non-promoted no-order REDUCE rows.
```

10. `TEMPORAL_AUTHORITY_CAUSE`

```text
NO. Data readiness, neutral historical safety, PIT source evidence, and feature-date authority are PASS/READY for the inspected boundary.
```

11. `ROOT_CAUSE`

```text
Phase32-BQ applied the lot-blocked REDUCE FULL_EXIT reconsideration fail-closed campaign-id requirement to all non-executable REDUCE rows before determining whether BO semantics actually promote the row to SHADOW_FULL_EXIT. On 2022-10-04, 92420 and 33700 should remain non-promoted NO_ORDER rows, but the BQ handoff lacks campaign_id and therefore halts sell_planning with MISSING_CAMPAIGN_ID.
```

12. `IS_CORRECTNESS_DEFECT`

```text
YES. A promote-ineligible no-order REDUCE should not halt the fresh-run before the accepted first BQ divergence date.
```

13. `MINIMAL_REPAIR_BOUNDARY`

```text
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py

Narrowly repair the BQ lot-blocked REDUCE reconsideration boundary so:
- canonical campaign identity is resolved from current-run PM/source artifacts when available;
- missing/mismatched campaign remains fail-closed for actual SHADOW_FULL_EXIT promotion;
- BO HOLD / BO INSUFFICIENT / non-promoted outcomes preserve the pre-BQ NO_ORDER semantics instead of escalating to sell_planning HALT solely due to the promotion-only campaign requirement;
- stale, cross-run, future-dated, or mismatched evidence remains fail-closed.
```

14. `SAME_RUN_CONTINUATION_POSSIBLE_AFTER_REPAIR`

```text
YES, expected. The run is halted at 2022-10-04:sell_planning before submit/execution side effects for that date. Continuation should be possible from the same safe boundary after a future repair and focused validation.
```

15. `FRESH_RUN_REQUIRED`

```text
NO by current evidence. No completed-day contamination or 2022-10-04 submit/execution side effect was found.
```

16. `SAFE_CONTINUATION_POINT`

```text
2022-10-04:sell_planning
```

17. `NEXT_RECOMMENDED_STEP`

```text
Implement a narrow Phase32-BT repair at the BQ sell-planning reconsideration boundary, add focused tests for 2022-10-04-like BO_INSUFFICIENT no-order preservation and genuine FULL_EXIT missing-campaign fail-closed behavior, then have the operator resume/retry the same run from 2022-10-04:sell_planning if validation passes.
```

18. `FINAL_JUDGMENT`

```text
PHASE32_BS_POST_BQ_2022_10_04_SELL_PLANNING_HALT_ROOT_CAUSE_IDENTIFIED
```

## No Strategy / PnL Use

No Historical profitability, future price, future return, future regime, future MFE/MAE, later outcome, or campaign final outcome was used to classify the defect.

No Strategy parameter, threshold, weight, ranking, model, or BQ semantic threshold change is recommended by this audit.

## Final Judgment

`PHASE32_BS_POST_BQ_2022_10_04_SELL_PLANNING_HALT_ROOT_CAUSE_IDENTIFIED`
