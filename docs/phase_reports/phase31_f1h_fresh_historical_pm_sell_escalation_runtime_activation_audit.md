# Phase31-F1H — Fresh Historical PM SELL Escalation Runtime Activation Audit

## PRIMARY_JUDGMENT

PM_MISSING_CAMPAIGN_HISTORY

F1F production code is connected to the fresh Historical common path and materializes canonical SELL fields in `strategy/position_management.json`. However, the early-window production artifacts show every repeated unrepresentable REDUCE as `prior_unrepresentable_reduce_count = 0`, so canonical state remains `WEAKENING_BUT_INTACT` and the F1F persistent-deterioration gate never becomes eligible.

This is a Production integration defect in the evidence bridge for prior same-campaign unrepresentable REDUCE history. It is not a profitability result and was not judged from later outcome.

## Required Output

BASELINE_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z

NEW_RUN_ID = runtime-test-historical-extended-smoke-20260821T002814288741Z

NEW_RUN_STATUS = ACTIVE_OR_IN_PROGRESS; no `final_summary.json`; `run_state.json` has 36 completed business days, last completed day 2022-10-03; 37 daily directories present.

F1F_PRODUCTION_FIELDS_PRESENT = YES

F1F_COMMON_RUNTIME_PATH_CONNECTED = YES

PM_HAS_REQUIRED_REPRESENTABILITY_EVIDENCE_AT_DECISION_TIME = PARTIAL

CAMPAIGN_HISTORY_AVAILABLE_TO_PM = NO

CAMPAIGN_ID_CONTINUITY = PASS

EARLY_WINDOW_PM_REDUCE_COUNT = 46

EARLY_WINDOW_CANONICAL_PERSISTENT_COUNT = 0

EARLY_WINDOW_DISCRETE_LOT_UNREPRESENTABLE_COUNT = 37

EARLY_WINDOW_FULL_F1F_GATE_ELIGIBLE_COUNT = 0

EARLY_WINDOW_PM_ESCALATED_EXIT_COUNT = 0

EARLY_WINDOW_RUNTIME_SELL_EXIT_FROM_F1F_COUNT = 0

ESCALATION_REASON_OCCURRENCE_COUNT = 0

83060_TRACE_JUDGMENT = DEFECT; repeated discrete-lot REDUCE rows remain WEAKENING_BUT_INTACT because prior unrepresentable REDUCE history is always 0.

83060_FIRST_PERSISTENT_DATE = NONE_IN_NEW_RUN; baseline F1D expected 2022-08-17.

83060_FIRST_F1F_GATE_ELIGIBLE_DATE = NONE

83060_FIRST_PM_ESCALATED_EXIT_DATE = NONE

83060_BLOCKING_GATE_IF_NONE = missing prior same-campaign unrepresentable REDUCE evidence; `prior_unrepresentable_reduce_count = 0` on every 2022-08-16 through 2022-08-26 REDUCE row.

54010_TRACE_JUDGMENT = DEFECT; recovery days are preserved correctly, but repeated discrete-lot REDUCE rows after fresh REDUCE sequences do not accumulate prior unrepresentable REDUCE history.

54010_FIRST_PERSISTENT_DATE = NONE_IN_NEW_RUN; baseline F1D expected 2022-08-17, then 2022-08-22 / 2022-08-25 after recovery resets.

54010_FIRST_F1F_GATE_ELIGIBLE_DATE = NONE

54010_FIRST_PM_ESCALATED_EXIT_DATE = NONE

54010_BLOCKING_GATE_IF_NONE = missing prior same-campaign unrepresentable REDUCE evidence; `reduce_history_summary.event_count = 0` in Strategy Intelligence / PM-attached evidence.

ROOT_CAUSE_CLASSIFICATION = PM_MISSING_CAMPAIGN_HISTORY

INTEGRATION_DEFECT_CONFIRMED = YES

REPAIR_CANDIDATE = YES

FUTURE_INFORMATION_USED_FOR_ACTIVATION_JUDGMENT = NO

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED_BY_CODEX = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

NEXT_TASK_RECOMMENDATION = Phase31-F1I focused Production integration repair: provide PM with PIT prior same-campaign unrepresentable REDUCE evidence before canonical SELL semantic evaluation, without using later outcome or changing thresholds.

## F1H-1 New Run Identification

Latest historical-extended-smoke run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T002814288741Z`

Evidence:

- newest `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-*` directory
- `run_state.json` completed business days = 36
- last completed business day = 2022-10-03
- `final_summary.json` absent
- `fresh_run_summary.json` absent

Codex did not mutate, resume, abort, or replay the run.

## F1H-2 Production Artifact Presence

Primary window:

2022-08-16 through 2022-08-26

For completed days in the window, these artifacts are present:

- `strategy/position_management.json`
- `strategy/strategy_intelligence.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `sell_planning/*`
- `execution/fills.json`

`strategy/position_management.json` rows contain:

- `canonical_sell_semantic_evidence`
- `canonical_sell_state`
- `canonical_sell_semantic_contract_version`
- nested `escalation_considered`
- nested `escalation_decision`
- nested `final_pm_action`
- nested `escalation_reason_code`

F1F_PRODUCTION_FIELDS_PRESENT = YES

The escalation reason string does not occur because no escalation was produced.

## F1H-3 83060 Deep Trace

| Date | Qty | Unit | Baseline PM | Final PM | State | Prior REDUCE Evidence | Rep Family | Final REDUCE Qty | Recovery | PIT | Escalation | Runtime | Fill / Holding Effect |
|---|---:|---:|---|---|---|---:|---|---:|---|---|---|---|---|
| 2022-08-16 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-17 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-18 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-19 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-22 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-23 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-24 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-25 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-26 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |

83060_FIRST_PERSISTENT_DATE = NONE_IN_NEW_RUN

Baseline F1D comparison:

- 2022-08-16 = WEAKENING_BUT_INTACT, prior 0
- 2022-08-17 = PERSISTENT_DETERIORATION, prior 1
- 2022-08-18 through 2022-08-26 = PERSISTENT_DETERIORATION, prior 2 through 8

Failed gate condition:

- canonical state is not `PERSISTENT_DETERIORATION`
- prior same-campaign unrepresentable REDUCE evidence remains 0

## F1H-4 54010 Deep Trace

| Date | Qty | Unit | Baseline PM | Final PM | State | Prior REDUCE Evidence | Rep Family | Final REDUCE Qty | Recovery | PIT | Escalation | Runtime | Fill / Holding Effect |
|---|---:|---:|---|---|---|---:|---|---:|---|---|---|---|---|
| 2022-08-16 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-17 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-18 | 100 | 100 | HOLD | HOLD | HEALTHY_OR_RECOVERING | 0 | NOT_APPLICABLE | n/a | RECOVERY_PRESENT | PASS | PRESERVE_BASELINE | NO_ACTION | no fill, holding unchanged |
| 2022-08-19 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-22 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-23 | 100 | 100 | HOLD | HOLD | HEALTHY_OR_RECOVERING | 0 | NOT_APPLICABLE | n/a | RECOVERY_PRESENT | PASS | PRESERVE_BASELINE | NO_ACTION | no fill, holding unchanged |
| 2022-08-24 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-25 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |
| 2022-08-26 | 100 | 100 | REDUCE | REDUCE | WEAKENING_BUT_INTACT | 0 | DISCRETE_LOT | 0 | NO_RECOVERY | PASS | PRESERVE_BASELINE | NO_ORDER | no fill, holding unchanged |

54010_FIRST_PERSISTENT_DATE = NONE_IN_NEW_RUN

Baseline F1D comparison:

- 2022-08-16 = WEAKENING_BUT_INTACT, prior 0
- 2022-08-17 = PERSISTENT_DETERIORATION, prior 1
- 2022-08-18 = HEALTHY_OR_RECOVERING
- 2022-08-22 = PERSISTENT_DETERIORATION, prior 1 after a fresh REDUCE sequence
- 2022-08-25 and 2022-08-26 = PERSISTENT_DETERIORATION

Failed gate condition:

- canonical state is not `PERSISTENT_DETERIORATION`
- PM-attached Strategy Intelligence `reduce_history_summary.event_count` remains 0

## F1H-5 All Early REDUCE Rows

Early-window PM REDUCE rows:

- PM_REDUCE_COUNT = 46
- CANONICAL_WEAKENING_COUNT = 46
- CANONICAL_PERSISTENT_COUNT = 0
- DISCRETE_LOT_UNREPRESENTABLE_COUNT = 37
- FULL_F1F_GATE_ELIGIBLE_COUNT = 0
- PM_ESCALATED_EXIT_COUNT = 0
- RUNTIME_SELL_EXIT_FROM_F1F_COUNT = 0
- RECOVERY_BLOCKED_COUNT = 0
- MINIMUM_NOTIONAL_EXCLUDED_COUNT = 0
- PIT_PROOF_BLOCKED_COUNT = 0
- CAMPAIGN_ID_BLOCKED_COUNT = 0
- OTHER_GATE_BLOCKED_COUNT = 0

The blocker occurs before the full gate: no row reaches `PERSISTENT_DETERIORATION`.

## F1H-6 Pre-F1F vs Post-F1F Structural Comparison

Baseline F1D early-window persistent candidates:

TOTAL_BASELINE_PERSISTENT_CANDIDATES = 22

Classification against new F1F run:

- A. PM escalates to EXIT = 0
- B. state differs before gate = 22
- C. gate fails for otherwise valid reason = 0
- D. production integration did not activate = 0

All 22 rows differ before the gate because the new production path reports `prior_unrepresentable_reduce_count = 0` and therefore `WEAKENING_BUT_INTACT`.

This is not evidence that early holdings similarity is correct behavior. It is evidence that the intended persistent-state input is not reaching PM.

## F1H-7 Fresh-Run Activation Contract

F1F_COMMON_RUNTIME_PATH_CONNECTED = YES

Evidence:

- Fresh run `strategy/position_management.json` contains F1F canonical SELL fields.
- `position_management.build_position_management_payload` calls `_attach_strategy_intelligence_positions` and then `_apply_canonical_sell_semantics`.
- `shadow_runtime.py` production sequence calls `strategy_intelligence` before `position_management`.
- PM artifact then feeds `position_sizing` and `runtime_planning`.

The common Runtime path is connected. The defect is not a missing call to `_apply_canonical_sell_semantics`.

## F1H-8 Artifact Ordering / Timing

PM_HAS_REQUIRED_REPRESENTABILITY_EVIDENCE_AT_DECISION_TIME = PARTIAL

Production ordering:

```text
strategy_intelligence
-> position_management
-> position_sizing
-> runtime_planning
```

Therefore PM does not have final PS artifact fields at the time `_apply_canonical_sell_semantics` runs.

However, F1F production evidence does contain PM-local representability fields:

- `current_quantity = 100`
- `trading_unit = 100`
- `representability_family = DISCRETE_LOT`
- `final_reduce_quantity = 0`
- `valid_intermediate_exposure_available = false`

So representability is partially available and is not the immediate blocker observed in this audit. The missing input is prior unrepresentable REDUCE history.

## F1H-9 Campaign History Availability

CAMPAIGN_HISTORY_AVAILABLE_TO_PM = NO

CAMPAIGN_ID_CONTINUITY = PASS

Evidence:

- 83060 keeps campaign id `pc-c86073d723344bb5-83060-0001`.
- 54010 keeps campaign id `pc-2c08fdde6d76cff5-54010-0001`.
- Strategy Intelligence lifecycle context reports `campaign_identity_authority_status = COMPLETE`.
- But `reduce_history_summary = {"event_count": 0, "last_reduce_date": None}` even after repeated REDUCE / NO_ORDER days.
- `positions/position_campaigns.json` contains only the original BUY event for 83060 and 54010; no unrepresentable REDUCE / no-order event is recorded into campaign history.

Cause:

`strategy_intelligence._campaign_history_summary` counts campaign events. Since unrepresentable REDUCE no-order rows are not campaign events, PM receives no prior REDUCE evidence.

## F1H-10 Escalation Reason Search

Search term:

`pm_discrete_control_persistent_deterioration_exit`

ESCALATION_REASON_OCCURRENCE_COUNT = 0

No symbol/date occurrences were found in the new run.

Explanation:

No production PM row reaches `PERSISTENT_DETERIORATION`; all early REDUCE rows are `WEAKENING_BUT_INTACT`.

## F1H-11 Root Cause Classification

ROOT_CAUSE_CLASSIFICATION = PM_MISSING_CAMPAIGN_HISTORY

Supporting facts:

- Canonical fields are materialized, so `CANONICAL_SELL_STATE_NOT_MATERIALIZED` is not correct.
- `_apply_canonical_sell_semantics` is connected, so `F1F_COMMON_RUNTIME_PATH_NOT_CONNECTED` is not correct.
- Representability is present enough to identify DISCRETE_LOT zero rows, so pure `PM_MISSING_REPRESENTABILITY_EVIDENCE` is not the primary root cause.
- Campaign id continuity is PASS, but campaign history summary omits unrepresentable REDUCE no-order events.

INTEGRATION_DEFECT_CONFIRMED = YES

## F1H-12 Repair Gate

REPAIR_CANDIDATE = YES

Narrow family-wide repair candidate for F1I:

Provide PM / canonical SELL semantic evaluation with PIT prior same-campaign unrepresentable REDUCE evidence before `_apply_canonical_sell_semantics` runs.

Constraints for repair:

- Do not use later outcome, later PnL, later price, delisting, or profitability.
- Do not tune thresholds.
- Do not make REDUCE-count-only EXIT.
- Preserve recovery reset/decay.
- Preserve minimum-notional exclusion.
- Keep PM as the only EXIT escalation mutation point.

## Final Questions

1. F1F production codeはfresh Historical common pathで本当に呼ばれているか？ YES.
2. PMはF1F gateに必要なPS representability evidenceをその時点で持っているか？ PARTIAL; PM has local representability, not PS artifact fields.
3. prior campaign REDUCE historyはPMへ届いているか？ NO.
4. 83060/54010は本来いつpersistentになったか？ Baseline F1D: 83060 on 2022-08-17; 54010 on 2022-08-17, then again after recovery-reset sequences.
5. その日にfull gateは成立していたか？ In baseline structural evidence, yes for persistent discrete-lot candidates; in new production run, no because persistent state is absent.
6. 成立していたのにEXITしなかったなら何が止めたか？ New production never reaches full gate; missing prior unrepresentable REDUCE history prevents persistent state.
7. `pm_discrete_control_persistent_deterioration_exit`は新runで一度でも出たか？ NO, occurrence count 0.
8. holdingsが旧runと同じなのは正常か、それともintegration defectか？ Integration defect: PM canonical state never becomes persistent, so no F1F EXIT can change holdings.
