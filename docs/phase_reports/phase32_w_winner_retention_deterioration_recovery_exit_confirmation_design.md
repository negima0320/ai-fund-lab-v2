# Phase32-W — Winner Retention / Deterioration Recovery and EXIT Confirmation Design

## Scope

Target evidence run:

`runtime-test-historical-extended-smoke-20260830T045550298045Z`

Primary inputs:

- `docs/phase_reports/phase32_u_acceleration_activation_winner_retention_joint_audit.md`
- `docs/phase_reports/phase32_v_winner_retention_premature_deacceleration_predictability_audit.md`
- current PM / sell-side source
- current PM Architecture / SoT
- current run actual artifacts

This is a USER-APPROVED PERFORMANCE DESIGN TASK. It is not a Production
implementation. No source, config, PM behavior, sell threshold, Strategy
parameter, Strategy weight, Runtime behavior, Safety behavior, or Phase32-S ADD
tier rule was changed. Codex did not run fresh-run, resume, replay, or long
Historical.

The target run was still `RUNNING` during inspection. The design evidence uses
the Phase32-V completed snapshot:

- completed business days audited: 78
- audited range: 2022-10-03 through 2023-01-26
- incomplete daily directory excluded from the audit snapshot: 2023-01-27
- sell-side PM decisions: 216
- `REDUCE`: 101
- `EXIT`: 115
- `PERSISTENT_DETERIORATION` EXIT: 45
- REDUCE -> EXIT paths: 76
- persistent EXIT after REDUCE: 44
- persistent EXIT after REDUCE despite intervening recovery/HOLD/ADD evidence:
  7

Future price, future return, future regime, future MFE/MAE, later SELL outcome,
and final campaign outcome were not used to choose this design. Phase32-V
future characterization is used only to justify that winner retention deserves
research, not to select Production thresholds or rules.

## Current PM State Machine

Current SoT boundary:

```text
Expected Edge sufficient
  -> HOLD

Expected Edge or risk/reward weakening while campaign optionality remains
  -> REDUCE candidate

Expected Edge insufficient, continuation broken, severe risk, or Safety full-close requirement
  -> EXIT
```

Current sell semantic state mapping:

| Current condition | Current canonical state | Current severity / persistence | Current action effect |
| --- | --- | --- | --- |
| PM `HOLD` or `ADD` with recovery reasons | `HEALTHY_OR_RECOVERING` | `PM_SEVERITY_NORMAL` / `RECOVERED` | Preserve baseline action |
| PM `REDUCE` with current soft deterioration and executable partial sell | `WEAKENING_BUT_INTACT` | `PM_SEVERITY_CAUTION` or `PM_SEVERITY_DEFENSIVE` / `FIRST_OBSERVATION` | Preserve REDUCE |
| PM `REDUCE` with discrete-lot zero sell, no recovery, prior unrepresentable REDUCE count > 0 | `PERSISTENT_DETERIORATION` | `PM_SEVERITY_EXIT_CANDIDATE` / `PERSISTENT` | eligible to become full EXIT |
| PM `EXIT` or exit-grade reason family | `EXIT_GRADE` | `PM_SEVERITY_EXIT_CANDIDATE` / `WORSENING` | Preserve EXIT |
| PIT/campaign identity failure or unresolved deterioration | `UNRESOLVED` | `PM_SEVERITY_UNRESOLVED` | Review/unresolved semantics |

Current transition diagram:

```text
HEALTHY_OR_RECOVERING
  -> soft warning
  -> WEAKENING_BUT_INTACT
  -> executable REDUCE, or zero-lot REDUCE intent
  -> strict-prior unrepresentable REDUCE evidence
  -> later soft warning with no same-day recovery
  -> PERSISTENT_DETERIORATION
  -> PM_EXIT through discrete-control persistence
```

Current recovery path:

```text
REDUCE
  -> later HOLD / ADD with recovery reasons
  -> same-day canonical state HEALTHY_OR_RECOVERING
  -> same-day persistence state RECOVERED
```

Current limitation:

The same-day row can be `RECOVERED`, but the deterioration history is not
modeled as a closeable episode. Later soft deterioration can start a new warning
while still being interpreted through campaign-level prior unrepresentable
REDUCE history.

## Root Architecture Limitation

The narrow root limitation is:

`soft defensive deterioration history is campaign-scoped, not episode-scoped`.

Consequences:

- a zero-lot REDUCE intent can become persistence evidence even though no
  exposure changed;
- later HOLD/ADD recovery is visible in same-day evidence but does not
  canonically close the earlier deterioration episode;
- a later soft warning can be treated as persistent deterioration rather than a
  new first observation after recovery;
- full EXIT can become available before a fresh hard/terminal breakdown is
  present.

Classification:

`ARCHITECTURE_LIMITATION` and `PERFORMANCE_INITIATIVE_CANDIDATE`

Correctness defect: NO.

## Deterioration Episode Design

Recommended model:

`SOFT_DETERIORATION_EPISODE`

Conceptual lifecycle:

| Episode state | Meaning |
| --- | --- |
| `NO_ACTIVE_SOFT_DETERIORATION` | Campaign is healthy/recovered; stale soft warnings are audit history only. |
| `SOFT_DETERIORATION_ACTIVE` | Current PIT evidence shows moderate/temporary deterioration; REDUCE may be justified. |
| `SOFT_DETERIORATION_PERSISTENT` | Soft deterioration remains unresolved across valid decision observations. |
| `SOFT_DETERIORATION_DEESCALATED` | Renewed strength is observed; episode no longer contributes to EXIT escalation. |
| `TERMINAL_DETERIORATION` | Hard stop, genuine breakdown, Safety full-close, or other terminal authority exists. |

Episode identity should be per campaign:

```text
campaign_id + soft_deterioration_episode_sequence
```

An episode starts when PM observes soft deterioration such as:

- `risk_increased_but_trend_not_broken`
- `peak_drawdown_warning`
- `expected_edge_risk_deterioration`
- non-terminal continuation/risk deterioration states

An episode closes or de-escalates when renewed strength evidence is confirmed.
If later weakness appears after closure, it starts a new episode and does not
inherit the closed episode's persistence count.

Hard or terminal deterioration does not need a soft episode to EXIT.

## Renewed Strength Evidence Classification

Use existing decision-time evidence only.

| Evidence | Classification | Rationale |
| --- | --- | --- |
| PM `ADD` decision | `REQUIRED_RECOVERY_EVIDENCE` candidate | PM has already judged the campaign strong enough for incremental capital; PC/PS allocation is not required. |
| PM `HOLD` with `structured_hold_worthiness_pass` | `REQUIRED_RECOVERY_EVIDENCE` candidate | HOLD is an active continuation decision under SoT. |
| `canonical_sell_state=HEALTHY_OR_RECOVERING` | `REQUIRED_RECOVERY_EVIDENCE` candidate | Existing sell semantic already encodes recovery state. |
| `recovery_state=RECOVERY_PRESENT` | `REQUIRED_RECOVERY_EVIDENCE` candidate | Existing PM evidence explicitly says recovery is present. |
| `strong_trend_continuation` | `SUPPORTIVE_RECOVERY_EVIDENCE` | Strong but trend alone is not action authority. |
| `trend_continuation` | `SUPPORTIVE_RECOVERY_EVIDENCE` | Useful only with PM HOLD/ADD or expected-edge evidence. |
| `opportunity_rank_still_high` | `SUPPORTIVE_RECOVERY_EVIDENCE` | Confirms competitiveness, but rank alone cannot decide action. |
| `positive_expected_edge` / expected edge adequate | `SUPPORTIVE_RECOVERY_EVIDENCE` | Central SoT input, but should be paired with PM action or recovery state. |
| buy-quality `FULL_ALLOCATION_ELIGIBLE` / high quality | `SUPPORTIVE_RECOVERY_EVIDENCE` | Supports continuation but belongs to buy/PC evidence, not sole PM recovery authority. |
| PIT trend / MA positive state | `SUPPORTIVE_RECOVERY_EVIDENCE` | Useful technical evidence, not standalone action authority. |
| downside risk `PASS` / contained | `SUPPORTIVE_RECOVERY_EVIDENCE` | Confirms risk is not blocking; not sufficient alone. |
| BULL regime | `NOT_APPROPRIATE` as primary evidence | Regime is context, not direct campaign recovery authority. |
| PC/PS actual BUY_ADD fill | `SUPPORTIVE_RECOVERY_EVIDENCE`, not required | PM recovery must not depend on downstream capital allocation. |
| hard stop / genuine breakdown / Safety full-close | `HARD_BLOCK_TO_RESET` | Must remain immediate defensive authority. |
| broker block / corporate-action block / severe liquidity failure | `HARD_BLOCK_TO_RESET` | Not a recoverable PM soft deterioration signal. |

Minimum semantic recovery definition for implementation:

```text
current PM action is HOLD or ADD
AND canonical sell state is HEALTHY_OR_RECOVERING
AND recovery_state is RECOVERY_PRESENT
AND PIT proof is PASS
AND no hard/terminal non-reset condition is present
```

Supportive dimensions may be recorded for audit and confidence, but should not
be turned into new numeric thresholds in Phase32-W.

## Reset / Decay / De-Escalation Comparison

| Option | Fit | Pros | Risks | Recommendation |
| --- | --- | --- | --- | --- |
| Full Reset | Medium | Simple and decisive. | One noisy HOLD could erase useful soft risk memory. | Not first choice. |
| Persistence Decay | Medium | Conservative; avoids abrupt resets. | Requires selecting decay rate/count, which is not justified yet. | Defer. |
| Episode Closure | High | Semantically clean; old soft episode becomes audit history; later weakness starts new episode. | Needs new episode observability fields. | Implement next. |
| State De-Escalation | High | Keeps audit history while preventing stale soft persistence from forcing EXIT. | Needs clear distinction between audit history and active persistence. | Implement with episode closure. |

Recommended design:

`EPISODE_CLOSURE_WITH_STATE_DEESCALATION`

Meaning:

- confirmed renewed strength closes the active soft deterioration episode;
- closed episode remains in audit history;
- closed episode does not count toward later full EXIT escalation;
- later soft deterioration starts a new episode;
- hard/terminal evidence bypasses soft episode handling.

## Recovery Confirmation

Avoid one-day noise. Do not select a fixed number of recovery days from
Historical outcomes.

Recommended semantic confirmation:

```text
RENEWED_STRENGTH_CONFIRMED
when PM emits HOLD or ADD
and canonical sell state is HEALTHY_OR_RECOVERING
and recovery_state is RECOVERY_PRESENT
and at least one independent supportive dimension is present
and no hard non-reset condition is present
and PIT proof is PASS
```

Independent supportive dimensions may include:

- `structured_hold_worthiness_pass`
- `positive_expected_edge`
- `trend_continuation` or `strong_trend_continuation`
- `downside_risk_contained`
- `opportunity_rank_still_high`
- existing continuation quality `PASS`

If a stricter observation count is needed later:

`PARAMETER_SELECTION_DEFERRED`

Do not derive the count from future return or PnL.

## Hard Non-Reset Conditions

Hard / terminal deterioration must never be suppressed, reset, or delayed by
winner-retention logic:

- `hard_stop_current_return`
- genuine `trend_and_opportunity_broken`
- `trend_and_expected_edge_broken`
- Safety hard constraint
- broker block
- corporate-action block
- severe liquidity failure
- high downside risk that is canonical full-close evidence
- any explicit Runtime/Safety full-close requirement

Only `SOFT/DEFENSIVE DETERIORATION` may recover:

- `risk_increased_but_trend_not_broken`
- `peak_drawdown_warning`
- `expected_edge_risk_deterioration`
- non-terminal risk-review/profit-retention warning where expected edge remains
  adequate

## EXIT Confirmation Design

For non-hard-stop, non-Safety, non-broker, non-corporate-action,
non-genuine-breakdown EXIT, introduce an explicit semantic confirmation layer.

Suggested states:

| EXIT confirmation state | Meaning |
| --- | --- |
| `DEFENSIVE_ONLY` | Soft warning exists but continuation/expected-edge evidence is not terminal. REDUCE or HOLD review may be valid; full EXIT not confirmed. |
| `CONFIRMED_DETERIORATION` | Multiple independent contemporaneous dimensions confirm weakening and no renewed-strength episode closure is active. EXIT may be considered if PM authority agrees. |
| `TERMINAL_BREAKDOWN` | Hard stop, genuine trend/expected-edge breakdown, Safety, broker, corporate action, or severe risk. Immediate EXIT remains allowed. |

Independent confirmation dimensions should be semantic, not a new numerical
voting threshold:

- current PM reason family
- continuation deterioration
- expected-edge deterioration
- momentum/trend deterioration
- opportunity degradation
- persistent downside risk
- failed recovery
- profit-retention risk review with expected edge no longer adequate
- campaign health deterioration

`DEFENSIVE_ONLY` must not become automatic HOLD. It should prevent soft stale
persistence from being treated as terminal full-close authority.

## REDUCE vs EXIT Boundary

Preserve:

```text
REDUCE:
  risk increased, but campaign not yet genuinely broken

EXIT:
  campaign genuinely broken, Safety/hard-stop requires full close,
  or deterioration is sufficiently confirmed
```

Repeated identical weak evidence should not be treated as independent
confirmation by itself. Persistence can contribute to confirmation only while
the same soft deterioration episode remains active and unrecovered.

Answer:

`SHOULD_REPEATED_UNREPRESENTABLE_REDUCE_INTENTS_ALONE_BE_SUFFICIENT_FOR_FULL_EXIT`:
NO.

Repeated unrepresentable REDUCE intents may raise review severity, but full
EXIT should require either hard/terminal evidence or a still-active soft
episode with independent non-recovered confirmation.

## Zero-Lot Interaction

Phase32-V observed:

- `REDUCE` PM decisions: 101
- zero executable sell quantity: 88

Design principle:

```text
Strategy deterioration evidence is PM authority.
Execution representability is PS / Runtime feasibility authority.
```

Zero-lot REDUCE should not accumulate the same severity as an executed REDUCE.
It may record that PM wanted less exposure but could not express a meaningful
partial sale. That record should be:

- episode-scoped,
- auditable,
- non-terminal by itself,
- blocked from causing full EXIT after confirmed renewed strength,
- unable to override hard/terminal evidence.

Current behavior does not prove a correctness violation because the existing
contract explicitly modeled discrete-control persistence. It does stress the
authority boundary and should be changed as a performance architecture
improvement.

## ADD / Recovery Interaction

PM ADD after a defensive episode should be strong renewed-strength evidence.

Authority rule:

```text
PM decision-time ADD evidence is sufficient to close/de-escalate a soft deterioration episode.
Successful PC/PS/Runtime BUY_ADD fill is not required.
```

Rationale:

- PM owns lifecycle/action semantics.
- PC owns capital competition.
- PS owns discrete quantity.
- Runtime consumes authoritative plans.
- If BQ/Risk Pacing prevents actual ADD, that is capital allocation context,
  not evidence that PM recovery did not exist.

Therefore:

- PM `ADD` + `HEALTHY_OR_RECOVERING` + `RECOVERY_PRESENT` should close or
  de-escalate the soft episode.
- PC/PS BUY_ADD success may be recorded as supportive, but must not be required.

## BULL Interaction

Do not implement:

`BULL -> HOLD`

Do not implement a BULL multiplier.

BULL should remain context only. However, when individual campaign PIT evidence
shows renewed strength during BULL, stale soft deterioration should not remain
active indefinitely. The same episode closure rule should apply in BULL,
RANGE, BEAR, RECOVERY, and CORRECTION.

Regime can be a confirmation modifier, not primary recovery authority.

## Phase32-S Interaction

The winner-retention design complements Phase32-S ADD acceleration:

```text
healthy
-> ADD
-> temporary deterioration
-> REDUCE
-> renewed strength
-> episode closure / de-escalation
-> HOLD or later ADD
-> genuine breakdown
-> EXIT
```

Avoid:

```text
ADD acceleration
-> one soft warning
-> stale zero-lot persistence
-> full EXIT despite renewed strength
```

Phase32-W does not modify Phase32-S ADD tier rules. Future implementation must
preserve G129 BUY_ADD authority and PC/PS/Runtime separation.

## Observability Schema

Future implementation should materialize at least:

| Field | Purpose |
| --- | --- |
| `soft_deterioration_episode_id` | Stable per-campaign episode identity. |
| `soft_deterioration_episode_state` | Active, persistent, de-escalated, closed, terminal. |
| `episode_start_business_date` | First date in current active soft episode. |
| `episode_last_deterioration_business_date` | Latest soft deterioration observation. |
| `episode_persistence_severity` | Semantic severity, not raw hidden debt. |
| `episode_increment_evidence` | PM reason and PIT evidence that increased persistence. |
| `episode_recovery_evidence` | PM HOLD/ADD and supportive recovery dimensions. |
| `episode_deescalation_reason` | Why the episode closed or de-escalated. |
| `hard_deterioration_present` | Explicit terminal bypass flag. |
| `exit_confirmation_state` | `DEFENSIVE_ONLY`, `CONFIRMED_DETERIORATION`, `TERMINAL_BREAKDOWN`. |
| `prior_soft_deterioration_cleared` | Whether old soft persistence is inactive for escalation. |
| `zero_lot_reduce_persistence_scope` | Whether zero-lot history is active in current episode only. |
| `future_information_used` | Must be false. |
| `outcome_used_for_parameter_selection` | Must be false. |

No opaque reset is acceptable.

## Representative Actual-Case Design Traces

These are decision-time design simulations. Later price outcome is not used.

### 65500

Observed path:

| Date | PM action | Current state | Evidence |
| --- | --- | --- | --- |
| 2022-10-11 | `REDUCE` | `WEAKENING_BUT_INTACT` | `peak_drawdown_warning`, zero-lot, no recovery |
| 2022-10-12 to 2022-10-13 | `HOLD` | `HEALTHY_OR_RECOVERING` | `RECOVERY_PRESENT`, positive expected edge / downside contained |
| 2022-10-17 to 2022-10-21 | `HOLD` | `HEALTHY_OR_RECOVERING` | repeated recovery / trend continuation evidence |
| 2022-10-24 | `REDUCE` | `WEAKENING_BUT_INTACT` | new soft warning, zero-lot |
| 2022-10-25 | `EXIT` | `PERSISTENT_DETERIORATION` | persistent discrete-control exit |

Proposed design would close/de-escalate the 2022-10-11 soft episode during the
subsequent HOLD recovery. The 2022-10-24 warning would start a new episode, so
2022-10-25 would require fresh confirmation rather than old-episode
persistence.

### 91070

Observed path:

| Date | PM action | Current state | Evidence |
| --- | --- | --- | --- |
| 2022-10-17 | `REDUCE` | `WEAKENING_BUT_INTACT` | `risk_increased_but_trend_not_broken`, zero-lot |
| 2022-10-18 to 2022-10-20 | `HOLD` | `HEALTHY_OR_RECOVERING` | downside contained / hold worthiness |
| 2022-10-21 | `REDUCE` | `WEAKENING_BUT_INTACT` | new soft warning |
| 2022-10-24 | `EXIT` | `PERSISTENT_DETERIORATION` | persistent discrete-control exit |

Proposed design would close the first episode after the HOLD recovery days and
treat 2022-10-21 as a new soft episode.

### 45840

Observed path:

| Date | PM action | Current state | Evidence |
| --- | --- | --- | --- |
| 2022-11-15 | `REDUCE` | `WEAKENING_BUT_INTACT` | soft risk warning, zero-lot |
| 2022-11-16 to 2022-11-29 | `HOLD` | `HEALTHY_OR_RECOVERING` | many recovery days, positive campaign return later in the interval |
| 2022-11-30 | `REDUCE` | `WEAKENING_BUT_INTACT` | new soft warning |
| 2022-12-01 | `EXIT` | `PERSISTENT_DETERIORATION` | persistent discrete-control exit |

Proposed design would not let the 2022-11-15 soft warning remain active across
the long recovery interval.

### 15180

Observed path:

| Date | PM action | Current state | Evidence |
| --- | --- | --- | --- |
| 2022-11-15 | `REDUCE` | `WEAKENING_BUT_INTACT` | soft risk warning, zero-lot |
| 2022-11-16 to 2022-11-18 | `HOLD` | `HEALTHY_OR_RECOVERING` | recovery / trend continuation |
| 2022-11-21 | `REDUCE` | `WEAKENING_BUT_INTACT` | new soft warning |
| 2022-11-22 | `EXIT` | `PERSISTENT_DETERIORATION` | persistent discrete-control exit |

Proposed design would require the second episode to earn its own non-emergency
EXIT confirmation.

### 61440

Observed path:

| Date | PM action | Current state | Evidence |
| --- | --- | --- | --- |
| 2022-12-09 to 2022-12-20 | `HOLD` | `HEALTHY_OR_RECOVERING` | continued hold worthiness |
| 2022-12-21 | `REDUCE` | `WEAKENING_BUT_INTACT` | soft risk warning, zero-lot |
| 2022-12-22 to 2023-01-06 | `HOLD` | `HEALTHY_OR_RECOVERING` | repeated recovery / hold-score evidence |
| 2023-01-10 | `REDUCE` | `WEAKENING_BUT_INTACT` | new soft warning |
| 2023-01-11 | `EXIT` | `PERSISTENT_DETERIORATION` | persistent discrete-control exit |

Proposed design would close the December episode and treat the January warning
as a new episode.

## Adverse-Control Checks

Adverse-control examples show why a broad HOLD override is unsafe:

| Symbol | Date | PM action | State | Evidence |
| --- | --- | --- | --- | --- |
| 89180 | 2022-10-04 | `EXIT` | `EXIT_GRADE` | `hard_stop_current_return`; immediate EXIT must remain allowed. |
| 33580 | 2022-10-17 to 2022-10-19 | `REDUCE` -> `REDUCE` -> `EXIT` | `PERSISTENT_DETERIORATION` | no intervening recovery before persistent EXIT. |
| 59860 | 2022-10-17 to 2022-10-18 | `REDUCE` -> `EXIT` | `PERSISTENT_DETERIORATION` | no intervening recovery before persistent EXIT. |

The design must not retain these mechanically. It should only de-escalate
active soft episodes when actual contemporaneous renewed-strength evidence is
present.

## Minimum-Change Recommendation

Minimum safe design:

```text
SOFT_DETERIORATION_EPISODE
+ RENEWED_STRENGTH_EPISODE_CLOSURE
+ STRONGER_NON_EMERGENCY_EXIT_CONFIRMATION
+ ZERO_LOT_PERSISTENCE_SCOPED_TO_ACTIVE_EPISODE
```

Implementation scope proposal for the next task:

1. Add episode-scoped state materialization inside PM sell semantic state.
2. Record soft deterioration episode start/increment evidence.
3. Close/de-escalate soft episodes on PM `HOLD`/`ADD` with
   `HEALTHY_OR_RECOVERING` and `RECOVERY_PRESENT`.
4. Ensure closed soft episode history does not count toward later full EXIT.
5. Require non-emergency persistent EXIT to have active, unrecovered episode
   confirmation.
6. Preserve immediate EXIT for hard stop, Safety, broker/corporate action,
   severe risk, and genuine trend/expected-edge breakdown.
7. Add focused tests for 65500/91070/45840/15180/61440-style paths and
   adverse controls.

Do not change ADD tier rules, BUY_NEW selection, PC capital competition, PS lot
rounding, Runtime Planning, Pending, Submit, Safety, Execution, ledger, G129, or
accepted artifact validation semantics.

## Required Classification

| Design item | Classification |
| --- | --- |
| persistence reset | `DEFER` as full reset; too blunt for first implementation |
| persistence decay | `DEFER`; count/rate selection would require later parameter work |
| episode identity | `IMPLEMENT_NEXT` |
| EXIT confirmation | `IMPLEMENT_NEXT` for non-emergency EXIT only |
| zero-lot REDUCE persistence | `IMPLEMENT_NEXT`; scope it to active soft episode, not indefinite campaign history |
| ADD/HOLD recovery evidence | `IMPLEMENT_NEXT`; use PM decision-time evidence, not downstream fill |
| BULL context | `KEEP_CURRENT`; context/modifier only, no BULL -> HOLD rule |

## Parameter-Selection Status

`PARAMETER_SELECTION_DEFERRED`

Do not choose:

- N recovery days
- N warning counts
- numeric momentum threshold
- numeric return threshold
- exact EXIT voting threshold

from Historical outcomes. Use existing semantic states first. If later
calibration is needed, it must be handled in a separate, leakage-controlled
research task.

## Anti-Leakage Statement

This design uses only decision-time PM state, J-Quants PIT technical evidence,
Runtime artifacts, and Architecture / SoT. Future outcome evidence from
Phase32-V was not used to choose rules, thresholds, weights, or parameters.

## NO CODE CHANGE

Confirmed. Phase32-W did not modify source or config. This report is the only
artifact created by this task.

## Final Judgment

1. `SHOULD_SOFT_DETERIORATION_BE_MODELED_AS_A_RECOVERABLE_EPISODE`: YES.
2. `WHAT_DECISION_TIME_EVIDENCE_CAN_CLOSE_OR_DEESCALATE_THE_EPISODE`: PM
   `HOLD` or `ADD` with `canonical_sell_state=HEALTHY_OR_RECOVERING`,
   `recovery_state=RECOVERY_PRESENT`, PIT `PASS`, and no hard non-reset
   condition; supportive evidence includes trend continuation, positive
   expected edge, downside contained, and opportunity-rank-still-high.
3. `SHOULD_RENEWED_STRENGTH_RESET_OR_DECAY_PERSISTENCE`: close/de-escalate the
   active soft episode and keep audit history. Do not use blunt full reset as
   the first design.
4. `SHOULD_ZERO_LOT_REDUCE_INTENTS_ACCUMULATE_TOWARD_FULL_EXIT`: not alone and
   not across closed/recovered episodes. They may count only within an active,
   unrecovered soft deterioration episode.
5. `WHAT_ADDITIONAL_CONFIRMATION_SHOULD_NON_EMERGENCY_EXIT_REQUIRE`: semantic
   `CONFIRMED_DETERIORATION` or `TERMINAL_BREAKDOWN`; `DEFENSIVE_ONLY` soft
   warnings should not by themselves justify full EXIT.
6. `CAN_HARD_STOP_AND_GENUINE_BREAKDOWN_REMAIN_IMMEDIATE`: YES.
7. `DOES_THE_DESIGN_PRESERVE_PM_PC_PS_RUNTIME_AUTHORITY`: YES. PM owns episode
   and lifecycle semantics; PC owns capital competition; PS owns quantities;
   Runtime consumes canonical plans.
8. `WHAT_IS_THE_MINIMUM_SAFE_IMPLEMENTATION_SCOPE`: PM sell semantic
   episode-state materialization, renewed-strength closure, non-emergency EXIT
   confirmation, zero-lot persistence scoping, observability, and focused tests.
9. `IS_PARAMETER_SELECTION_REQUIRED_OR_DEFERRED`: deferred.
10. `IS_WINNER_RETENTION_IMPLEMENTATION_READY_FOR_THE_NEXT_TASK`: YES, as a
    user-approved performance implementation task with the minimum scope above.

Final classification:

`PHASE32_W_WINNER_RETENTION_RECOVERABLE_DETERIORATION_DESIGN_READY`
