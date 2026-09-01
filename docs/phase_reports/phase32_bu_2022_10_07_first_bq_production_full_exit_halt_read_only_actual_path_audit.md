# Phase32-BU — 2022-10-07 First BQ Production FULL EXIT HALT READ-ONLY Actual-Path Audit

## Scope

Target run:

```text
runtime-test-historical-extended-smoke-20260831T231046348584Z
```

Observed:

```text
completed through = 2022-10-06
HALT = 2022-10-07:sell_planning
exit_code = 20
```

This was a READ-ONLY audit. No code, config, runtime state, Pending, Ledger, resume, recover, replay, fresh-run, or repair command was executed.

## Critical Context

Phase32-BR established:

```text
EXPECTED_FIRST_BQ_DIVERGENCE_DATE = 2022-10-07
expected symbol = 45750
old Production outcome = NO_ORDER
BQ expected outcome = SELL_EXIT
```

Phase32-BT repaired the earlier non-promoted BO HOLD / INSUFFICIENT control-path HALT. This target run then completed 2022-10-04 through 2022-10-06 and reached the expected first BQ Production divergence date.

## Run State

`run_state.json`:

```text
status = HALT
next_job = 2022-10-07:sell_planning
completed_business_days = 2022-10-03, 2022-10-04, 2022-10-05, 2022-10-06
halted_at.job = sell_planning
halted_at.exit_code = 20
feature_date_contract_status = PASS
selected_feature_date = 2022-10-07
```

No 2022-10-07 `submit` or `execution` artifact directory exists in the target run evidence.

`sell_planning/external_effect_audit.json`:

```text
status = PASS
broker_order_api_calls = 0
notification_delivery_calls = 0
production_access = false
demo_submit_executed = false
production_order_executed = false
```

Therefore the failure is pre-submit and pre-execution.

## Actual 45750 BQ Trigger

The actual current-run 2022-10-07 evidence confirms the expected BQ trigger.

From `strategy/position_management.json`:

```text
symbol = 45750
action = REDUCE
source_pm_decision_ref = pm-2022-10-07-45750-reduce
position_campaign_id = pc-1c231f87db41dc41-45750-0001
reason_codes = risk_increased_but_trend_not_broken; strategy_intelligence_sell_side_evidence_connected
raw_reduce_quantity = 25.0
rounded_reduce_quantity = 0.0
final_reduce_quantity = 0.0
representability_reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
trading_unit = 100.0
pit_validation_state = PASS
future_information_used = false
```

From `strategy/position_sizing.json`:

```text
pm_action = REDUCE
raw_reduce_quantity = 25.0
rounded_reduce_quantity = 0
reduce_final_sell_quantity = 0
reduce_execution_semantic = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
reduce_intentional_no_order = true
source_pm_decision_ref = pm-2022-10-07-45750-reduce
```

From `strategy/runtime_planning.json`:

```text
symbol = 45750
planning_id = rp-2022-10-07-45750-no_order-439dc3f212b87b71
source_pm_decision_id = pm-2022-10-07-45750-reduce
source_pm_action = REDUCE
planning_intent = NO_ORDER
order_side_intent = NONE
no_order_reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
```

From `strategy/strategy_intelligence.json`:

```text
position_campaign_id = pc-1c231f87db41dc41-45750-0001
campaign_identity_authority_status = COMPLETE
campaign_age_business_days = 1
current_campaign_relative_return = -0.04311543810848406
trend_health_state = MIXED
relative_strength_state = MIXED
participation_quality_state = WEAK
exhaustion_risk_state = ELEVATED_RISK
participation_risk_state = ELEVATED_RISK
future_information_used = false
```

## BQ Reconsideration Evidence

The sell-planning order plan contains one BQ lot-blocked REDUCE reconsideration:

```text
symbol = 45750
status = FAIL_CLOSED
reason = MISSING_CAMPAIGN_ID
source_pm_action = REDUCE
source_pm_decision_id = pm-2022-10-07-45750-reduce
campaign_id = pc-1c231f87db41dc41-45750-0001
lot_block_reason = REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
bo_shadow_binary_authority_status = PASS
bo_shadow_binary_eligibility_status = PASS
bo_shadow_binary_decision = SHADOW_FULL_EXIT
runtime_invented_exit = false
source_status.status = PASS
source_status.reason = run_scoped_strategy_evidence
source_status.run_id = runtime-test-historical-extended-smoke-20260831T231046348584Z
```

The BO rationale is:

```text
multiple current PIT deterioration/risk dimensions agree and no structural HOLD-side continuation evidence is present
```

This confirms:

```text
BO semantic classification = PASS
BO result = SHADOW_FULL_EXIT
PIT source evidence = same-run / same-date / non-future
```

## Canonical HALT Reason

`sell_planning/runtime_manifest.json`:

```text
final_state = REVIEW_REQUIRED
exit_code = 20
reason = sell planning pipeline review required: MISSING_CAMPAIGN_ID
```

The first canonical failure is:

```text
BQ FULL_EXIT promotion authority validation
-> missing explicit sell-planning handoff campaign_id
-> FAIL_CLOSED: MISSING_CAMPAIGN_ID
```

`approval_artifact.json`:

```text
status = NO_SIGNAL
reason = MISSING_CAMPAIGN_ID
```

No ordinary SELL_EXIT order-plan item was created:

```text
order_plan.items = []
```

## Failure Boundary

The failure boundary is:

```text
Runtime PM producer / no-order REDUCE materialization
-> SellExitDecision / reduce quantity contract
-> BQ FULL_EXIT promotion authority validation
```

The canonical Strategy artifacts have campaign identity:

```text
strategy/position_management.json position_campaign_id = pc-1c231f87db41dc41-45750-0001
strategy/strategy_intelligence.json lifecycle_context.position_campaign_id = pc-1c231f87db41dc41-45750-0001
```

But the actual `.runtime` PM producer artifact used by sell planning lacks it:

```text
.runtime/runtime_state/position_management/2022-10-07/position_management_decisions.json
symbol = 45750
decision = REDUCE
runtime_sell_quantity = 0.0
position_campaign_id = null
campaign_id = null
```

The downstream runtime planning artifact also lacks campaign identity on the no-order REDUCE row:

```text
strategy/runtime_planning.json
symbol = 45750
planning_intent = NO_ORDER
source_pm_decision_id = pm-2022-10-07-45750-reduce
position_campaign_id = null
campaign_id = null
```

BT correctly allows non-promoted BO outcomes to use same-run Strategy Intelligence campaign identity for classification, but still requires explicit handoff campaign identity for actual FULL_EXIT promotion. The actual path reaches that safety gate and stops.

## Boundary Classification

| Boundary | Classification |
|---|---|
| BO semantic classification | PASS |
| campaign/provenance validation | FAIL |
| Strategy reconsideration authority creation | PARTIAL: BO result authored, promotion authority rejected |
| conversion to ordinary SELL_EXIT | NOT_REACHED |
| order-plan materialization | NOT_REACHED for 45750 SELL_EXIT |
| Pending publication | Existing same-date Pending preserved; no 45750 SELL_EXIT item published |
| mixed review | NOT root cause |
| historical temporal authority | PASS |
| duplicate/idempotency guard | NO evidence of duplicate/idempotency failure |

## Strategy Semantics Judgment

45750 is legitimately a BQ FULL_EXIT candidate under unchanged BO/BQ PIT semantics:

```text
PM REDUCE
lot-blocked executable quantity = 0
BO = SHADOW_FULL_EXIT
expected BQ Production outcome = SELL_EXIT
```

This should not be repaired by weakening the SELL decision or changing BO/BQ semantics. The defect is Production materialization / authority propagation, not Strategy decision correctness.

## Pending / Review Interaction

The same-date Pending before sell planning was active and `REVIEW_REQUIRED` with `BUY_ITEM_SCOPED_REVIEW`:

```text
pending_plan_id = pending-strategy-plan-historical-2022-10-07-8760ff9d8cd30765
items:
- 76920 BUY REVIEW_REQUIRED
- 33500 BUY APPROVED
- 44220 SELL APPROVED
```

The sell planning pipeline reports:

```text
pending_composition_model = PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL
pending_composition_status = REVIEW_REQUIRED
selected_count = 0
reason = MISSING_CAMPAIGN_ID
```

Pending review was present, but it is not the first failing invariant. The first violated boundary is BQ FULL_EXIT promotion authority missing explicit campaign handoff for 45750.

## Why Focused 45750 Test Missed The Actual Failure

The BT focused 45750 regression fixture passed because it directly constructed:

```text
SellExitDecision(position_campaign_id = "pc-bq-45750")
```

The real fresh-run path did not directly construct a complete `SellExitDecision`. It flowed through Runtime PM producer / runtime no-order materialization where the `.runtime` PM decision artifact for 45750 had:

```text
position_campaign_id = null
campaign_id = null
```

Therefore the focused test covered:

```text
complete campaign handoff + SHADOW_FULL_EXIT -> SELL_EXIT
```

but did not cover:

```text
canonical PM/source artifacts contain campaign
runtime SellExitDecision handoff lacks campaign
SHADOW_FULL_EXIT requires Production promotion
```

Missing coverage classification:

```text
actual artifact schema difference
provenance/campaign propagation difference
integration path gap
```

Future repair validation must add an actual-path fixture where:

```text
PM/source artifact campaign exists
runtime PM producer / SellExitDecision handoff initially lacks campaign
BO = SHADOW_FULL_EXIT
repair must propagate canonical campaign into promotion authority
SELL_EXIT materializes with campaign/provenance intact
```

and a negative fixture where canonical PM/source campaign is genuinely unavailable or mismatched, which must still fail closed.

## Side-Effect State

For 2022-10-07:

```text
submit artifact directory = absent
execution artifact directory = absent
broker_order_api_calls = 0
notification_delivery_calls = 0
production_access = false
order_plan.items = []
45750 SELL_EXIT submitted = NO
45750 fill/position/cash mutation = NO
```

The run is stopped before submit/execution side effects for the failing date.

## Minimal Repair Boundary

Narrowest future repair boundary:

```text
Runtime PM producer / sell-planning BQ handoff campaign authority propagation
```

The repair should ensure that a genuine BQ `SHADOW_FULL_EXIT` promotion can consume canonical same-run PM/source campaign identity when it exists and matches Strategy Intelligence/current-position authority.

Required constraints for future repair:

- do not change BO/BQ semantic classification
- do not change SELL/REDUCE thresholds
- do not convert missing evidence into permissive authority
- do not generate campaign ids downstream
- do not use symbol-only joins as identity authority
- fail closed on genuine missing/mismatched campaign authority
- materialize ordinary `SELL_EXIT` only after campaign/provenance authority is complete

## Required Final Answers

1. `2022_10_07_45750_BQ_TRIGGER_CONFIRMED`

```text
YES
```

2. `BO_FULL_EXIT_CONFIRMED`

```text
YES
```

3. `PRODUCTION_RECONSIDERED_FULL_EXIT_AUTHORED`

```text
PARTIAL. The BQ reconsideration evidence authored BO=SHADOW_FULL_EXIT, but Production FULL_EXIT promotion was rejected before ordinary SELL_EXIT materialization.
```

4. `ORDINARY_SELL_EXIT_ATTEMPTED`

```text
YES conceptually at the BQ promotion boundary, but NOT materialized. order_plan.items remained empty for 45750.
```

5. `HALT_CANONICAL_REASON`

```text
sell planning pipeline review required: MISSING_CAMPAIGN_ID
```

6. `FAILING_CONTRACT`

```text
BQ FULL_EXIT Production promotion requires explicit campaign_id / position_campaign_id in the sell-planning handoff, but the actual Runtime PM producer / SellExitDecision handoff for 45750 lacked it.
```

7. `FAILURE_BOUNDARY`

```text
Runtime PM producer / no-order REDUCE materialization -> SellExitDecision / BQ FULL_EXIT promotion authority validation
```

8. `STRATEGY_DECISION_CORRECT`

```text
YES. 45750 is a legitimate SHADOW_FULL_EXIT candidate under current PIT BO/BQ semantics.
```

9. `BQ_PRODUCTION_MATERIALIZATION_DEFECT`

```text
YES
```

10. `CAMPAIGN_PROVENANCE_CAUSE`

```text
YES. Canonical source artifacts contain campaign identity, but the runtime handoff used for FULL_EXIT promotion lacks explicit campaign authority.
```

11. `PENDING_REVIEW_CAUSE`

```text
NO. Same-date Pending review exists, but it is not the first violated invariant.
```

12. `TEMPORAL_AUTHORITY_CAUSE`

```text
NO. Feature-date and run-scoped PIT source evidence are PASS/current.
```

13. `DUPLICATE_IDEMPOTENCY_CAUSE`

```text
NO concrete evidence.
```

14. `SUBMIT_EXECUTION_SIDE_EFFECTS_PRESENT`

```text
NO
```

15. `SAFE_CONTINUATION_POINT`

```text
2022-10-07:sell_planning
```

16. `SAME_RUN_CONTINUATION_POSSIBLE_AFTER_REPAIR`

```text
YES, expected. The run halted before submit/execution side effects on 2022-10-07.
```

17. `FRESH_RUN_REQUIRED`

```text
NO by current evidence.
```

18. `WHY_FOCUSED_45750_TEST_MISSED_ACTUAL_FAILURE`

```text
The focused test supplied a complete SellExitDecision.position_campaign_id directly. The actual fresh-run path used Runtime PM producer / no-order REDUCE materialization, where the .runtime PM decision / SellExitDecision handoff lacked campaign_id despite canonical Strategy artifacts containing it.
```

19. `MINIMAL_REPAIR_BOUNDARY`

```text
Runtime PM producer / sell-planning BQ handoff campaign authority propagation for genuine SHADOW_FULL_EXIT promotion.
```

20. `NEXT_RECOMMENDED_STEP`

```text
Implement a narrow Phase32-BV repair that propagates canonical same-run PM/source campaign identity into the BQ FULL_EXIT promotion handoff, with focused actual-path fixtures for 45750 positive promotion and missing/mismatched campaign fail-closed behavior. Then have the operator continue the same run from 2022-10-07:sell_planning after validation.
```

21. `FINAL_JUDGMENT`

```text
PHASE32_BU_FIRST_BQ_FULL_EXIT_ACTUAL_PATH_MATERIALIZATION_DEFECT_IDENTIFIED
```

## Final Judgment

`PHASE32_BU_FIRST_BQ_FULL_EXIT_ACTUAL_PATH_MATERIALIZATION_DEFECT_IDENTIFIED`
