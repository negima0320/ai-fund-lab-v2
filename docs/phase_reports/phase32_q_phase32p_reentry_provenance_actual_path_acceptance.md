# Phase32-Q - Phase32-P REENTRY Provenance Actual-Path Acceptance

Target run: `runtime-test-historical-extended-smoke-20260830T040609131559Z`

This is a READ-ONLY acceptance audit of Phase32-P. No source code, config, Strategy parameter, threshold, weight, Cash policy, Risk Pacing, PM semantics, BUY_ADD semantics, or G129 semantics were changed. Codex did not run fresh-run, resume, replay, or long Historical.

No future price, future return, future regime, future MFE/MAE, later SELL outcome, final campaign outcome, Historical profitability, or hindsight evidence was used.

## Target Run / Evidence Coverage

- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T040609131559Z`
- Profile: `historical-extended-smoke`
- Source commit recorded by run: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Source dirty recorded by run subprocess traces: `true`
- Run status at audit snapshot: `RUNNING`
- Completed business days at audit snapshot:
  - `2022-10-03`
  - `2022-10-04`
  - `2022-10-05`
  - `2022-10-06`
  - `2022-10-07`
  - `2022-10-11`
  - `2022-10-12`
  - `2022-10-13`
  - `2022-10-14`
  - `2022-10-17`
  - `2022-10-18`
  - `2022-10-19`
- Completed Runtime job exit codes: all observed completed jobs exit code `0`
- Strategy shadow manifest:
  - `active_runtime_consumer_eligibility=YES`
  - `strategy_planning_authority_active=true`
  - `strategy_planning_authority_consumer_called=true`
  - `runtime_mutation_performed=false`
  - `runtime_switch_performed=false`
  - `future_row_rejection_count=0`
  - `pit_valid_dates` covers all completed dates above

## 76470 End-to-End Trace

Mandatory representative case:

`2022-10-12 BUY_NEW -> campaign creation -> 2022-10-14 EXIT -> closed campaign -> 2022-10-17 REENTRY evaluation`

### 2022-10-12 BUY_NEW

Actual artifacts:

- `daily/2022-10-12/strategy/portfolio_construction.json`
  - `security_code=76470`
  - `current_position=false`
  - `membership_intent=ADD_CANDIDATE`
  - `semantic_buy_type=BUY_NEW`
  - `reentry_semantic_status=NOT_APPLICABLE`
- `daily/2022-10-12/strategy/runtime_planning.json`
  - `planning_id=rp-2022-10-12-76470-buy_new-6483f6cd0abe1ac9`
- `daily/2022-10-12/execution/fills.json`
  - `business_date=2022-10-12`
  - `symbol=76470`
  - `side=BUY`
  - `quantity=800`
  - `position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `source_decision_id=rp-2022-10-12-76470-buy_new-6483f6cd0abe1ac9`
  - `source_decision_type=BUY_NEW`

Campaign creation authority is therefore the BUY fill execution artifact, with explicit campaign ID:

`pc-745f53c2c0e1b87a-76470-0001`

### 2022-10-14 EXIT

Actual artifacts:

- `daily/2022-10-14/strategy/position_management.json`
  - `security_code=76470`
  - `action=EXIT`
  - `position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
- `daily/2022-10-14/strategy/portfolio_construction.json`
  - `security_code=76470`
  - `current_position=true`
  - `membership_intent=REMOVE_CANDIDATE`
  - `pm_action=EXIT`
  - `current_position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `pm_position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
- `daily/2022-10-14/strategy/runtime_planning.json`
  - `planning_id=rp-2022-10-14-76470-sell_exit-27569e3e4c410679`
  - `source_pm_decision_id=pm-2022-10-14-76470-exit`
- `daily/2022-10-14/execution/fills.json`
  - `business_date=2022-10-14`
  - `symbol=76470`
  - `side=SELL`
  - `quantity=800`
  - `position_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `source_decision_id=rp-2022-10-14-76470-sell_exit-27569e3e4c410679`
  - `source_decision_type=SELL_EXIT`

The SELL fill closes the same campaign created by BUY_NEW. No campaign split is observed.

### 2022-10-17 REENTRY Evaluation

Actual artifact:

- `daily/2022-10-17/strategy/portfolio_construction.json`
  - `security_code=76470`
  - `current_position=false`
  - `membership_intent=ADD_CANDIDATE`
  - `target_membership=false`
  - `prior_exit_business_date=2022-10-14`
  - `prior_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `prior_exit_campaign_id=pc-745f53c2c0e1b87a-76470-0001`
  - `source_pm_decision_id=pm-2022-10-14-76470-exit`
  - `source_decision_id=rp-2022-10-14-76470-sell_exit-27569e3e4c410679`
  - `prior_exit_reason=EXIT`
  - `prior_exit_reason_codes=["strategy_intelligence_sell_side_evidence_connected", "weak_hold_score"]`
  - `prior_exit_provenance_status=PASS`
  - `prior_exit_context.provenance_status=PASS`
  - `prior_exit_context.authority=STRICT_PRIOR_PM_EXIT_DECISION_CONTEXT`
  - `prior_exit_context.future_information_used=false`
  - `reentry_semantic_status=FAIL_CLOSED`
  - `reentry_semantic_state=REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION`
  - `reentry_recovery_status=FAIL_CLOSED`
  - `reentry_recovery_reason=reentry_opportunity_not_requalified`
  - `reentry_safety_restriction_status=PASS`
  - `broker_eligibility_status=PASS`
  - `corporate_action_status=NO_EVENT`

Strict-prior ordering is preserved:

`prior_exit_business_date=2022-10-14 < REENTRY evaluation date=2022-10-17`

REENTRY remains rejected, but provenance is accepted. This satisfies the Phase32-P requirement that provenance acceptance must not depend on REENTRY semantic PASS.

## All REENTRY Provenance Statistics

Scope: completed days with canonical PC artifacts through `2022-10-19`.

- Total REENTRY rows: `66`
- `prior_exit_provenance_status=PASS`: `66`
- `prior_exit_provenance_status=REVIEW_REQUIRED`: `0`
- Non-empty `prior_campaign_id`: `66`
- Non-empty `source_pm_decision_id`: `66`
- Non-empty `source_decision_id`: `66`
- Strict-prior violations: `0`

REENTRY symbols observed:

- `83060`: 10
- `89180`: 10
- `41650`: 9
- `33700`: 9
- `44220`: 7
- `45750`: 6
- `93600`: 3
- `73590`: 3
- `76470`: 3
- `44870`: 3
- `48330`: 1
- `96100`: 1
- `59860`: 1

## Remaining REVIEW_REQUIRED Explanation

No REENTRY prior provenance row remains `REVIEW_REQUIRED` in the audited canonical PC artifacts.

Classification:

- canonical prior provenance genuinely unavailable: `0`
- remaining materialization defect: `0`
- insufficient evidence: `0`

## Phase32-P Provenance Acceptance

Classification: `PASS`

Evidence:

- The mandatory 76470 case preserves prior campaign ID, source PM decision ID, source decision ID, prior EXIT business date, reason, reason codes, and `prior_exit_provenance_status=PASS`.
- All 66 observed REENTRY rows preserve the required IDs.
- No strict-prior violation was found.
- REENTRY rejection did not erase provenance.

## Campaign Identity Regression

Phase32-L campaign identity classification: `PASS`

Actual artifact checks:

- Fill rows with explicit campaign IDs: `51`
- PC current-position rows checked: `89`
- PC current-position rows missing current campaign ID: `0`
- PC current-position campaign vs PM campaign mismatches: `0`
- PM action rows checked:
  - `HOLD`: 50
  - `EXIT`: 18
  - `REDUCE`: 12
  - `ADD`: 9
- PM rows missing campaign ID: `0`

Representative 76470 confirms:

- BUY fill campaign ID becomes current-position campaign authority.
- PM and PC use the same campaign on EXIT.
- SELL fill closes the same campaign.
- Later REENTRY prior context references the closed campaign.
- No downstream deterministic replacement is observed where explicit campaign exists.

## KI-004 Regression

Classification: `NOT_REPRODUCED`

Actual REENTRY artifacts:

- Broad false `reentry_safety_restriction_status=FAIL_CLOSED`: `0`
- Mandatory 76470 REENTRY:
  - `reentry_safety_restriction_status=PASS`
  - `broker_eligibility_status=PASS`
  - `corporate_action_status=NO_EVENT`
  - `reentry_recovery_status=FAIL_CLOSED`
  - `prior_exit_provenance_status=PASS`

Safety, broker, corporate action, recovery, and prior-context statuses remain separated. The label `FAIL_CLOSED` appears for recovery/churn conditions where applicable, not as a false Safety block.

## KI-006 Regression

Classification: `NOT_REPRODUCED`

Actual artifact checks:

- BUY_WAIT / explicit zero quality allocation ADD cases observed: `1`
- Positive Runtime BUY_ADD resurrected from that case: `0`

Observed case:

- `2022-10-12`, `94320`
  - `quality_action=BUY_WAIT`
  - `quality_allocation_adjustment=0.0`
  - PC target remained non-incremental for executable ADD purposes
  - Runtime positive BUY_ADD quantity: `0`

BUY_WAIT / explicit zero quality allocation did not resurrect a positive ADD through PC/PS/Runtime.

## G129 Regression

Classification: `NO_ACTUAL_VIOLATION_OBSERVED`

Actual Runtime Planning through audited coverage:

- Positive Runtime BUY_ADD rows observed: `0`
- BUY_ADD rows missing source/order-increment authority: `0`

Because no positive valid Runtime BUY_ADD occurred in this run window, the positive BUY_ADD actual-path subcase is not directly re-demonstrated here. The current artifacts contain no G129 violation and no evidence that Phase32-P affected BUY_ADD order-increment authority.

## Strategy Behavior Comparison

Compared current run with immediately preceding post-L run:

`runtime-test-historical-extended-smoke-20260830T032332732107Z`

Common completed dates compared through `2022-10-17`:

- `2022-10-03`
- `2022-10-04`
- `2022-10-05`
- `2022-10-06`
- `2022-10-07`
- `2022-10-11`
- `2022-10-12`
- `2022-10-13`
- `2022-10-14`
- `2022-10-17`

Decision/action comparison:

- Runtime Planning signature including campaign IDs: identical through common covered dates.
- Runtime Planning signature excluding campaign IDs: identical through common covered dates.
- Execution fills BUY/SELL side and quantities excluding campaign IDs: identical through common covered dates.
- PM action signature excluding campaign IDs: identical through common covered dates.

Observed differences:

- Execution fill campaign IDs differ from `2022-10-03`.
- PM campaign IDs differ from `2022-10-04`.

Classification of differences:

These are campaign identity values from independent fresh-run materialization, not Strategy behavior differences. No BUY/SELL/action/quantity decision difference was found through `2022-10-17`.

No profitability or later outcome was used for this comparison.

## Repair Required

NO.

No canonical upstream IDs are available-but-missing from PC REENTRY result in the audited current run.

## Correctness Track Closure Readiness

Overall correctness track: `READY_TO_CLOSE`

Reason:

- Phase32-P provenance actual-path acceptance: `PASS`
- Phase32-L campaign identity regression: `PASS`
- KI-004 regression: `NOT_REPRODUCED`
- KI-006 regression: `NOT_REPRODUCED`
- G129 actual artifacts: no violation observed
- Runtime stability: completed jobs observed with exit code `0`; no HALT in audited snapshot

The only G129 limitation is event coverage: no positive Runtime BUY_ADD occurred in this specific window. That does not block Phase32-P provenance acceptance or correctness-track closure because no G129 violation is present and Phase32-P did not modify BUY_ADD semantics.

## NO CODE CHANGE

Confirmed. Phase32-Q created only this report. It did not modify source or config.

## NO Future-Information Use

Confirmed. This audit used current-run artifacts, current source identity, and strict-prior checks only.

## Final Judgment

`PHASE32_Q_REENTRY_PROVENANCE_ACTUAL_PATH_ACCEPTED_CORRECTNESS_TRACK_READY_TO_CLOSE`
