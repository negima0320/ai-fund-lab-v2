# Phase31-G7 — PIT-Safe PM Severity Action-Mapping Design

## Scope

Task type: READ-ONLY architecture / PM action-mapping design.

No implementation, Strategy mutation, PM mutation, SELL rule mutation, threshold tuning, weight tuning, config change, feature addition, model retraining, fresh-run, resume, replay, or Historical rerun was performed.

Read:

- `docs/phase_reports/phase31_g6_g4_same_window_100bd_behavioral_activation_no_delta_audit.md`
- `docs/phase_reports/phase31_g5_g4_pm_severity_production_acceptance_same_window_100bd_readiness.md`
- `docs/phase_reports/phase31_g4_pm_severity_persistence_contract_focused_implementation.md`
- `docs/phase_reports/phase31_g3_pit_safe_pm_severity_persistence_contract_design.md`
- `docs/phase_reports/phase31_g2_pit_safe_pm_severity_persistence_hold_regret_audit.md`
- `docs/phase_reports/phase31_g1_pit_safe_pm_failure_winner_retention_separability_audit.md`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G7_PM_SEVERITY_ACTION_MAPPING_DESIGN_READY`

G7 supports a smallest-safe PM-owned action-mapping implementation. The mapping should connect `pm_severity` to final PM action only after canonical SELL state is produced, while preserving G3/G4 authority separation:

```text
canonical SELL state
+ campaign economics
+ strict-prior persistence
+ recovery
+ regime modifier
-> PM_SEVERITY
-> PM-owned action mapping
-> final_pm_action
```

This is not a second SELL classifier. It is a PM action-strength mapping over existing canonical evidence.

## Ownership

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER = NO`

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`PS_RUNTIME_ACTION_INVENTION = NO`

Canonical SELL condition remains owned by `strategy.sell_semantic_state`. PM action mutation should remain in the PM materialization path, currently `position_management._apply_canonical_sell_semantics`, or an immediately adjacent PM-owned helper invoked there. PS and Runtime consume PM action and handle quantity / feasibility only.

## Action Mapping Contract

| Severity | Action mapping |
| --- | --- |
| `PM_SEVERITY_NORMAL` | Preserve baseline PM action. No new sell pressure. |
| `PM_SEVERITY_CAUTION` | Preserve HOLD/REDUCE optionality. Never auto-upgrade to EXIT. Recovery may return to NORMAL. |
| `PM_SEVERITY_DEFENSIVE` | Conditional PM-owned risk reduction. May upgrade HOLD to REDUCE when canonical deterioration, negative campaign economics, PIT/campaign validity, and no recovery all hold. Does not upgrade first-observation REDUCE to EXIT. |
| `PM_SEVERITY_EXIT_CANDIDATE` | Hybrid. Observability for already-authorized `EXIT_GRADE`; PM escalation input only when strict canonical gates are satisfied. |
| `PM_SEVERITY_UNRESOLVED` | Preserve/review. No silent EXIT. |

`NORMAL_ACTION_DELTA = NONE`

`CAUTION_AUTO_EXIT = NO`

`CAUTION_WINNER_OPTIONALITY = PRESERVED`

## DEFENSIVE Semantics

`DEFENSIVE_ACTION_MAPPING = CONDITIONAL_HOLD_TO_REDUCE; FIRST_OBSERVATION_REDUCE_PRESERVED; PERSISTENT_FAILURE_MAY_ESCALATE_ONLY_THROUGH_PM_GATE`

`CAN_DEFENSIVE_MUTATE_HOLD_TO_REDUCE = CONDITIONAL`

Allowed only when all are true:

- `pm_severity = PM_SEVERITY_DEFENSIVE`
- canonical state is compatible with deterioration, not `HEALTHY_OR_RECOVERING`
- campaign return side is `FAILING`
- PIT proof passes
- campaign identity is complete
- recovery evidence is absent
- state/recovery evidence is not conflicting
- minimum-notional / unresolved execution policy does not require fail-closed preservation

`CAN_DEFENSIVE_MUTATE_REDUCE_TO_EXIT = CONDITIONAL`

Allowed only when all are true:

- `pm_severity = PM_SEVERITY_DEFENSIVE` or stronger
- persistence is `PERSISTENT` or `WORSENING`, not `FIRST_OBSERVATION`
- campaign economics remain failing
- recovery evidence is absent
- canonical state is `PERSISTENT_DETERIORATION` or `EXIT_GRADE`
- PIT proof and campaign identity are complete
- the PM-owned canonical gate authorizes EXIT

FIRST_OBSERVATION defensive rows should normally remain REDUCE, not EXIT.

## EXIT_CANDIDATE Semantics

`EXIT_CANDIDATE_ACTION_AUTHORITY = HYBRID`

`PM_SEVERITY_EXIT_CANDIDATE` has two roles:

1. Observability for already-authorized PM EXIT, especially `EXIT_GRADE`.
2. PM escalation input for persistent failure only through exact canonical gates.

Exact gate:

- Direct PM EXIT remains allowed when canonical state is `EXIT_GRADE`.
- F1F/F1I PM escalation remains allowed when canonical state is `PERSISTENT_DETERIORATION`, strict-prior same-campaign persistence exists, recovery is absent, PIT proof passes, campaign identity is complete, and the existing representability / unrepresentable REDUCE gate authorizes PM EXIT.
- A severity label alone cannot create EXIT.

## Persistence vs First Observation

`FIRST_OBSERVATION_FULL_EXIT = NO`

`PERSISTENT_FAILURE_CAN_STRENGTHEN_ACTION = YES`

`FIRST_OBSERVATION` may trigger HOLD -> REDUCE under `DEFENSIVE`, but not full EXIT. `PERSISTENT` / `WORSENING` may strengthen REDUCE -> EXIT only through PM-owned canonical gates. No exact historical day count is selected.

## Campaign Economics

`POSITIVE_RETURN_WINNER_BIAS = YES`

`NEGATIVE_RETURN_CAPITAL_RECOVERY_BIAS = YES`

`NEGATIVE_RETURN_DIRECT_EXIT = NO`

Positive-return weakening has winner-preservation bias: preserve HOLD/REDUCE optionality and avoid premature full EXIT. Negative return is a capital-recovery modifier only when paired with canonical deterioration and PIT-valid evidence.

## Recovery Override

`RECOVERY_PRE_ACTION_DEESCALATION = YES`

`STALE_EXIT_AFTER_RECOVERY = NO`

Fresh recovery evidence must be checked before action mutation. Recovery should de-escalate `DEFENSIVE` / `EXIT_CANDIDATE` to `CAUTION` or `NORMAL` before materialization. Prior deterioration debt cannot survive a canonical recovery boundary as hidden EXIT pressure.

## Profitable REDUCE Chains

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

`REDUCE_COUNT_USED_AS_EXIT_AUTHORITY = NO`

Profitable weakening may follow:

```text
WEAKENING_BUT_INTACT
-> REDUCE
-> recovery evidence
-> HOLD / NORMAL
```

Repeated REDUCE count may be evidence lineage, but it cannot be a standalone EXIT authority.

## Failed-Campaign Capital Recovery Path

`FAILED_CAMPAIGN_CAPITAL_RECOVERY_PATH = canonical deterioration + negative campaign economics + strict-prior persistence/worsening + no recovery + PIT/campaign validity -> PM severity DEFENSIVE/EXIT_CANDIDATE -> HOLD may become REDUCE; REDUCE may become EXIT only through PM-owned canonical/F1F gate`

The intended path is generally:

```text
HOLD -> REDUCE -> EXIT
```

Sequential passage through every action is not mandatory for `EXIT_GRADE`, but non-EXIT-grade deterioration should not jump to full EXIT on first observation.

## Minimum-Lot / Unrepresentable REDUCE

`F1F_F1I_UNREPRESENTABLE_PATH_PRESERVED = YES`

If PM wants REDUCE but the quantity is unrepresentable:

- PM intent/history remains preserved.
- Strict-prior unrepresentable deterioration may support PM-owned EXIT escalation under existing F1F/F1I authority.
- Minimum-notional unresolved paths remain fail-closed / preserve.
- PS and Runtime cannot invent EXIT.

## Regime Role

`REGIME_ACTION_AUTHORITY = NONE`

`REGIME_SEVERITY_MODIFIER_ONLY = YES`

Adverse regime may support confidence for persistent negative-return deterioration. It cannot mutate action alone and cannot force EXIT for a healthy or profitable winner.

## Healthy Winner Control Design Check

`HEALTHY_WINNER_CONTROL_DESIGN_CHECK = PASS`

Future outcome is used only to identify these G2 control cases, not as production input.

| Symbol | PIT weakness evidence | G7 action result |
| --- | --- | --- |
| 62490 | Positive-return `WEAKENING_BUT_INTACT`, continuation/downside PASS. | `CAUTION`; preserve REDUCE/HOLD optionality; no EXIT. |
| 69730 | Positive-return weakening, later recovery. | `CAUTION`; REDUCE allowed, recovery de-escalates to NORMAL; no stale EXIT. |
| 27670 | Positive-return first weakness. | `CAUTION`; no full EXIT from first observation. |
| 27880 | Profitable repeated REDUCE chain before later persistent state. | REDUCE count alone cannot EXIT; only canonical persistent/PM gate may act. |
| 97310 | Positive-return weakening and recovery sequence. | `CAUTION` on weakness, `NORMAL/RECOVERED` on recovery; no premature EXIT. |

## Failed Campaign Design Case Table

`FAILED_CAMPAIGN_DESIGN_CASE_TABLE = SEE_TABLE`

| Symbol | PIT evidence | Severity/action mapping |
| --- | --- | --- |
| 21380 | 2022-10-05 `WEAKENING_BUT_INTACT`, `DEFENSIVE`, `FIRST_OBSERVATION`, negative return. | Preserve REDUCE or mutate HOLD -> REDUCE; no first-observation EXIT. 2022-10-06 `EXIT_GRADE` may EXIT. |
| 65790 | 2022-11-01 `WEAKENING_BUT_INTACT`, `DEFENSIVE`, negative return; 2022-11-02 `PERSISTENT_DETERIORATION`. | First row REDUCE; persistent row may EXIT through PM/F1F gate. |
| 44220 | 2022-09-28 `WEAKENING_BUT_INTACT`, `DEFENSIVE`, negative return; 2022-09-29 `EXIT_GRADE`. | First row REDUCE; next EXIT-grade may EXIT. |
| 92420 | 2022-10-12 positive-return weakening, then 2022-10-13 negative EXIT-grade. | First row `CAUTION` preserves optionality; EXIT only when canonical EXIT-grade arrives. |
| 37790 | 2022-12-08 `EXIT_GRADE`, negative return. | Existing PM EXIT preserved; severity is observability and confirmation. |

## Intended PM Action Delta Classes

`INTENDED_PM_ACTION_DELTA_CLASSES = OLD_HOLD_TO_NEW_REDUCE_FOR_DEFENSIVE_CANONICAL_DETERIORATION; OLD_REDUCE_TO_NEW_EXIT_FOR_PERSISTENT_FAILING_PM_GATE; OLD_REDUCE_TO_NEW_REDUCE_UNCHANGED_FOR_FIRST_OBSERVATION_OR_CAUTION; OLD_EXIT_TO_NEW_EXIT_UNCHANGED_FOR_EXIT_GRADE`

Explicit classes:

- `OLD HOLD -> NEW REDUCE`: intended only for `DEFENSIVE` with canonical deterioration, failing campaign economics, complete PIT/campaign identity, and no recovery.
- `OLD REDUCE -> NEW EXIT`: intended only for persistent/worsening failure where canonical PM/F1F gate authorizes EXIT.
- `OLD REDUCE -> NEW REDUCE`: intended for `CAUTION`, profitable weakening, and `DEFENSIVE FIRST_OBSERVATION`.
- `OLD EXIT -> NEW EXIT`: unchanged for existing `EXIT_GRADE` or already-authorized F1F/F1I escalation.
- `OLD HOLD -> NEW HOLD`: unchanged for `NORMAL`, `UNRESOLVED`, recovery, or positive-return healthy pullback.

## Prohibited PM Action Delta Classes

`PROHIBITED_ACTION_DELTA_CLASSES = CAUTION_TO_EXIT; REGIME_ONLY_TO_EXIT; REDUCE_COUNT_ONLY_TO_EXIT; NEGATIVE_RETURN_ONLY_TO_EXIT; MISSING_HISTORY_TO_EXIT; RECOVERED_CAMPAIGN_TO_STALE_EXIT; STATE_ONLY_WEAKENING_TO_EXIT`

Explicit prohibitions:

- `CAUTION -> EXIT` solely from severity.
- Healthy profitable winner -> EXIT solely due adverse regime.
- REDUCE chain -> EXIT solely due count.
- Negative current return -> EXIT without canonical deterioration.
- Missing history -> EXIT.
- Recovered campaign -> stale EXIT.
- `WEAKENING_BUT_INTACT -> EXIT` on state alone.

## Threshold / Future-Information Contract

`PRODUCTION_NUMERIC_THRESHOLD_SELECTED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

Allowed semantic concepts:

- positive vs negative campaign basis
- first observation
- strict-prior persistence
- worsening
- recovery

Forbidden production thresholds:

- `return < -1%`
- `return < -2%`
- exactly 2 or 3 days
- `giveback > X%`
- `REDUCE count >= N`
- regime score cutoff

G2/G6 outcomes justify design direction only, not numeric parameter selection.

## Future G8 Regression Contract

`G8_REQUIRED_ACTION_MAPPING_TESTS = profitable_weakening_no_full_exit; first_negative_weakening_no_full_exit; defensive_hold_to_reduce_when_canonical_deterioration; persistent_negative_deterioration_can_strengthen_action; recovery_cancels_escalation; same_day_self_count_prohibited; cross_campaign_history_leak_prohibited; regime_alone_no_action_mutation; reduce_count_alone_no_exit; f1f_unrepresentable_path_preserved; exit_grade_existing_exit_unchanged; unresolved_missing_evidence_no_exit`

Minimum future tests:

1. Profitable weakening does not full EXIT.
2. First negative weakening does not automatically full EXIT.
3. `DEFENSIVE` can mutate HOLD -> REDUCE only with canonical deterioration and valid evidence.
4. Persistent negative deterioration can strengthen action through PM gate.
5. Recovery cancels escalation before action materialization.
6. Same-day self-count remains prohibited.
7. Cross-campaign history leak remains prohibited.
8. Regime alone does not mutate action.
9. REDUCE count alone does not EXIT.
10. F1F unrepresentable path remains preserved.
11. `EXIT_GRADE` existing EXIT remains unchanged.
12. Missing / ambiguous evidence does not EXIT.

## Implementation Readiness

`IMPLEMENTATION_READINESS = READY_FOR_FOCUSED_ACTION_MAPPING_IMPLEMENTATION`

Ready because:

- owner is unambiguous: PM / `position_management`
- canonical SELL owner remains unchanged
- winner controls are protected
- persistence semantics are strict-prior
- recovery can cancel escalation
- no Historical numeric threshold is needed
- intended and prohibited action delta classes are explicit

## Required Summary Output

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER = NO`

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`NORMAL_ACTION_DELTA = NONE`

`CAUTION_AUTO_EXIT = NO`

`CAUTION_WINNER_OPTIONALITY = PRESERVED`

`DEFENSIVE_ACTION_MAPPING = CONDITIONAL_HOLD_TO_REDUCE; FIRST_OBSERVATION_REDUCE_PRESERVED; PERSISTENT_FAILURE_MAY_ESCALATE_ONLY_THROUGH_PM_GATE`

`CAN_DEFENSIVE_MUTATE_HOLD_TO_REDUCE = CONDITIONAL`

`CAN_DEFENSIVE_MUTATE_REDUCE_TO_EXIT = CONDITIONAL`

`EXIT_CANDIDATE_ACTION_AUTHORITY = HYBRID`

`FIRST_OBSERVATION_FULL_EXIT = NO`

`PERSISTENT_FAILURE_CAN_STRENGTHEN_ACTION = YES`

`POSITIVE_RETURN_WINNER_BIAS = YES`

`NEGATIVE_RETURN_CAPITAL_RECOVERY_BIAS = YES`

`NEGATIVE_RETURN_DIRECT_EXIT = NO`

`RECOVERY_PRE_ACTION_DEESCALATION = YES`

`STALE_EXIT_AFTER_RECOVERY = NO`

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

`FAILED_CAMPAIGN_CAPITAL_RECOVERY_PATH = canonical deterioration + negative campaign economics + strict-prior persistence/worsening + no recovery + PIT/campaign validity -> PM severity DEFENSIVE/EXIT_CANDIDATE -> HOLD may become REDUCE; REDUCE may become EXIT only through PM-owned canonical/F1F gate`

`F1F_F1I_UNREPRESENTABLE_PATH_PRESERVED = YES`

`REGIME_ACTION_AUTHORITY = NONE`

`HEALTHY_WINNER_CONTROL_DESIGN_CHECK = PASS`

`INTENDED_PM_ACTION_DELTA_CLASSES = OLD_HOLD_TO_NEW_REDUCE_FOR_DEFENSIVE_CANONICAL_DETERIORATION; OLD_REDUCE_TO_NEW_EXIT_FOR_PERSISTENT_FAILING_PM_GATE; OLD_REDUCE_TO_NEW_REDUCE_UNCHANGED_FOR_FIRST_OBSERVATION_OR_CAUTION; OLD_EXIT_TO_NEW_EXIT_UNCHANGED_FOR_EXIT_GRADE`

`PROHIBITED_ACTION_DELTA_CLASSES = CAUTION_TO_EXIT; REGIME_ONLY_TO_EXIT; REDUCE_COUNT_ONLY_TO_EXIT; NEGATIVE_RETURN_ONLY_TO_EXIT; MISSING_HISTORY_TO_EXIT; RECOVERED_CAMPAIGN_TO_STALE_EXIT; STATE_ONLY_WEAKENING_TO_EXIT`

`PRODUCTION_NUMERIC_THRESHOLD_SELECTED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_TASK_RECOMMENDATION = Phase31-G8 focused PM severity action-mapping implementation`
