# Phase32-AR — Accepted Baseline / Deferred Research Durable SoT Recording

## Scope

Task type: DOCUMENTATION / SoT ONLY.

Source material read:

- `docs/phase_reports/phase32_aq_graduation_episode_lifecycle_freshness_boundary_final_falsification_audit.md`
- `docs/phase_reports/phase32_ap_starter_to_winner_graduation_shadow_contract_feasibility_audit.md`
- `docs/phase_reports/phase32_ao_initial_sizing_position_graduation_architecture_root_cause_audit.md`
- `docs/phase_reports/phase32_an_durable_winner_capital_competition_deep_root_cause_audit.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

No Strategy logic, Runtime logic, PM/SI/BQ/PC/PS behavior, BUY_NEW sizing,
ADD/HOLD/REDUCE/EXIT, Cash, Risk Pacing, thresholds, weights, caps, Model 2
activation, Graduation semantics, comparator, accepted artifact, runtime state,
fresh-run, resume, replay, recover, or long Historical command was changed or
executed.

## Files Changed

| File | Change |
|---|---|
| `docs/02_architecture/strategy_intelligence_architecture_v1.md` | Added Section 38: Phase32-AR accepted graduation baseline and deferred research tracks |
| `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` | Added Section 21: current ADD graduation execution baseline and preservation constraints |
| `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md` | Added Section 26: deferred NEW/ADD/Cash marginal comparator and accepted current spec |
| `docs/phase_reports/phase32_ar_accepted_baseline_deferred_research_durable_sot_recording.md` | This report |

## Durable SoT Entries Added

### Current Accepted Baseline

Recorded as:

```text
CURRENT_SPEC_ACCEPTED_WITH_DEFERRED_IMPROVEMENT_RESEARCH
persistent eligibility + PC/PS/G129 per-order authority
```

Meaning:

- ADD does not require a mandatory fresh-event / Graduation Episode semantic.
- Persistent valid eligibility may remain observable.
- Each actual BUY_ADD still requires PC allocation authority, PS discrete
  quantity authority, and G129 order-increment Runtime / Submit authority.
- Graduation consideration is not capital entitlement.
- Cash, NEW, Risk Pacing, BQ, no-loss averaging, concentration / headroom, lot
  feasibility, prior ADD safeguards, Safety, broker, and corporate-action gates
  remain authoritative.

No new Production state named Graduation Episode was introduced.

### Known Limitation

Recorded as:

```text
REPLACE_HEAVY_HYBRID / WEAK_WINNER_GRADUATION / STARTER_SATURATION
NO_CORRECTNESS_DEFECT_CONFIRMED
```

This is explicitly a performance architecture limitation, not a correctness
defect.

Evidence summary durably recorded:

- many one-lot starter positions;
- weak/non-durable starters mostly correctly remain small;
- durable winner sample is small in the 252BD evidence;
- durable winners rarely grow materially;
- existing system can graduate winners under valid conditions, including
  `94340` and `76470`;
- current evidence does not justify Production behavior changes.

## Deferred Tracks

### Model 2

```text
Model 2 - PM Position Lifecycle + PC ADD Consideration
Status: DEFERRED / ON HOLD
Rejected: NO
Production activation: NOT AUTHORIZED
Shadow: PARTIALLY_VALIDATED
```

Scope:

- semantic / lifecycle clarity;
- PM/SI/PC ADD consideration routing.

Not proven to solve:

- Graduation Episode lifecycle;
- NEW/ADD/Cash marginal capital comparison;
- Winner capitalization by itself.

### Starter-to-Winner Graduation

```text
Starter-to-Winner Graduation Contract
Status: OPEN / SHADOW_ONLY
Rejected: NO
Production activation: NOT AUTHORIZED
Current conservative contract: PARTIAL
```

Accepted finding:

- safe shadow Graduation consideration is partially reconstructable;
- deterministic Production-ready fresh / renewed episode boundary is not
  available from current PIT evidence;
- mandatory freshness requirement is rejected for the current baseline;
- weak-starter protection must remain preserved.

### NEW / ADD / Cash Marginal Capital Comparison

```text
High-resolution NEW / ADD / Cash marginal capital comparison
Status: DEFERRED
Production comparator change: NOT AUTHORIZED
```

Known concern:

- current NEW / ADD / Cash comparison is not fully expressed in one calibrated
  marginal-JPY value unit;
- direct comparable durable-winner NEW / ADD competitions were rare;
- current evidence is insufficient to justify redesign.

## Preservation Constraints Recorded

Non-negotiable preservation constraints:

- weak starters staying small;
- no-loss averaging protection;
- Cash optionality;
- Risk Pacing;
- BUY_NEW quality gates;
- Winner retention improvements;
- SELL independence;
- concentration / headroom controls;
- lot feasibility;
- fail-closed behavior;
- PC final capital allocation authority;
- PS discrete quantity authority;
- Runtime exact consumption;
- G129 BUY_ADD order-increment semantics;
- broker / corporate-action / Safety boundaries.

## Revisit Conditions Recorded

Deferred Winner Graduation, Model 2, and marginal-comparator work should be
revisited only if new independent evidence materially strengthens the case:

- longer Historical window;
- multiple years;
- multiple regimes;
- larger durable-winner sample;
- repeated weak graduation across independent periods;
- repeated high fragmentation / starter saturation;
- repeated Cash / NEW capital destination while valid incumbents remain
  undercapitalized.

A single Historical window must not be used to tune Production rules.

## Long Historical Next Step

Recorded next operational step:

```text
LONG_HISTORICAL_EVIDENCE_ACCUMULATION_WITH_CURRENT_ACCEPTED_SPEC
```

No Strategy changes are authorized before that validation.

The long Historical should test whether:

- weak Winner graduation persists;
- 100-share fragmentation persists;
- durable Winner supply changes by regime / year;
- existing architecture naturally graduates winners in other environments;
- plateau behavior repeats outside the current 252BD window.

Performance outcome alone must not retroactively redefine Production logic.

## Required Final Answers

1. `IS_CURRENT_SPEC_DURABLY_RECORDED_AS_ACCEPTED`

   `YES`.

2. `IS_PERSISTENT_ELIGIBILITY_PLUS_PC_PS_G129_RECORDED_AS_CURRENT_BASELINE`

   `YES`.

3. `IS_WEAK_WINNER_GRADUATION_RECORDED_AS_PERFORMANCE_LIMITATION_NOT_CORRECTNESS_DEFECT`

   `YES`.

4. `IS_MODEL2_EXPLICITLY_DEFERRED_AND_NOT_REJECTED`

   `YES`.

5. `IS_STARTER_TO_WINNER_GRADUATION_EXPLICITLY_OPEN_SHADOW_ONLY`

   `YES`.

6. `IS_NEW_ADD_CASH_MARGINAL_COMPARATOR_EXPLICITLY_DEFERRED`

   `YES`.

7. `ARE_EXISTING_STRENGTHS_TO_PRESERVE_RECORDED`

   `YES`.

8. `ARE_REVISIT_CONDITIONS_RECORDED`

   `YES`.

9. `IS_LONG_HISTORICAL_EVIDENCE_ACCUMULATION_RECORDED_AS_NEXT_STEP`

   `YES`.

10. `WAS_ANY_PRODUCTION_BEHAVIOR_CHANGED`

    `NO`.

## Final Judgment

```text
PHASE32_AR_ACCEPTED_BASELINE_AND_DEFERRED_RESEARCH_DURABLY_RECORDED_LONG_HISTORICAL_READY
```
