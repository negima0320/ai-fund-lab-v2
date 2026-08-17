# Phase30-V - Entry Intelligence / Overheated Momentum / One-Lot Capital Concentration Repair Design

## Primary Judgment

```text
PHASE30_V_ENTRY_INTELLIGENCE_AND_QUALITY_ADJUSTED_ONE_LOT_ADMISSION_DESIGNED_PHASE30_W_IMPLEMENTATION_READY
```

Phase30-V is design-only. No Strategy, Runtime, threshold, config, model,
Accepted Generation, Safety, target run artifact, or Historical outcome was
changed.

The repair target is Production-common and general. It is not a 78780-specific
ban and does not use 10BD outcomes as Runtime input or production parameter
selection.

## Evidence Basis

Mandatory sources reviewed:

- `docs/phase_reports/phase30_u_10bd_entry_quality_large_loss_capital_reinvestment_audit.md`
- `docs/phase_reports/phase30_t_5bd_early_strategy_behavior_capital_concentration_audit.md`
- `docs/phase_reports/phase30_h_continuation_quality_downside_risk_offline_research.md`
- `docs/phase_reports/phase30_i_continuation_quality_downside_risk_strategy_design.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
- `docs/02_architecture/strategy_intelligence_production_migration_contract_v1.md`
- current Phase28/29 lot-aware final reallocation, one-lot authority, soft-cap
  overshoot, and residual recycling tests / implementation
- `docs/01_requirements/phase_roadmap.md`

Phase30-U identified two coupled defects:

```text
Entry Intelligence Gap
One-Lot Capital Concentration Gap
```

78780 is evidence for a class, not a rule answer:

```text
CQ PASS
Trend SUPPORTIVE
Relative SUPPORTIVE
Acceleration DECELERATING
Exhaustion Risk ELEVATED_RISK
Reversal Risk ELEVATED_RISK
Volatility Risk ELEVATED_RISK
20D momentum +228%
1D momentum -15.8%
BUY Quality FULL_ALLOCATION_ELIGIBLE
PC continuous target weight 3.57%
one-lot fallback final exposure about 24.5%
```

## Entry Intelligence Root Cause

The current Production path can observe the dangerous ingredients, but the BUY
consumer does not yet interpret them as an entry-timing state.

Current distinction:

```text
strong trend evidence
```

is too easily treated as:

```text
healthy forward continuation entry
```

The missing layer is an Entry-specific semantic interpretation of existing
Strategy Intelligence evidence. CQ and Downside Risk remain shared evidence;
Entry Admission is the BUY-side consumer interpretation of that evidence.

## Proposed Entry Semantic

Add an Entry Admission semantic contract for BUY-side consumers. Conceptual
schema:

```text
entry_admission:
  schema_version
  as_of_business_date
  symbol
  lifecycle_intent: BUY_NEW | REENTRY | BUY_ADD
  entry_state
  admission_action
  allocation_quality_bias
  buy_wait_eligible
  evidence_sufficiency
  reason_codes
  consumed_evidence:
    eligibility
    continuation_quality
    downside_risk
    expected_edge
    relative_strength
    regime_compatibility
    participation_quality
  leakage_firewall:
    future_information_used: false
```

Allowed first-generation `entry_state` vocabulary:

| State | Meaning | BUY-side interpretation |
| --- | --- | --- |
| `HEALTHY_CONTINUATION_ENTRY` | Trend / persistence / relative opportunity are supportive and risk is contained enough for current entry | BUY_NEW or ADD may proceed to PC comparison |
| `CONTINUATION_WITH_CAUTION` | Thesis is still plausible, but one or more timing/risk dimensions reduce confidence | reduced allocation, lower PC priority, or BUY_WAIT |
| `OVERHEATED_DECELERATING_ENTRY` | Medium-term move is strong but short-term structure, acceleration, exhaustion, or volatility suggests late-stage risk | BUY_WAIT or reduced allocation; one-lot overshoot should normally fail admission unless exceptional positive evidence exists |
| `REVERSAL_RISK_ENTRY` | Strong prior move plus negative short structure / reversal risk dominates entry timing | BUY_WAIT or reject depending on evidence sufficiency and opportunity context |
| `INSUFFICIENT_ENTRY_EVIDENCE` | Required PIT evidence is missing, stale, malformed, or non-authoritative | fail closed through BUY_WAIT / no BUY / review according to existing consumer semantics |

Allowed `admission_action` vocabulary:

```text
BUY_NEW_ALLOWED
BUY_NEW_REDUCED_ONLY
BUY_WAIT
REJECT_BUY_NEW
NO_ADD
ADD_ALLOWED
ADD_REDUCED_ONLY
REVIEW_REQUIRED
```

This design does not freeze numeric thresholds. It requires the implementation
to preserve raw evidence and reason codes so future calibration can be audited
without smuggling fitted parameters into Runtime.

## Healthy vs Overheated Separation

Healthy continuation requires positive agreement across evidence families, not
raw momentum alone:

- supportive trend health,
- persistence that is not a one-day spike,
- acceleration that is stable or improving,
- exhaustion / reversal risk not dominant,
- participation confirmation or explicit confidence downgrade,
- relative strength against PIT market evidence where available,
- regime compatibility or explicit regime uncertainty,
- Expected Edge still `UNCALIBRATED` but directionally supportive as relative
  opportunity evidence.

Overheated / decelerating continuation is identified by interaction, not a
single feature:

- extreme medium-term momentum,
- negative or sharply weaker short-term momentum,
- deceleration,
- elevated exhaustion,
- elevated reversal risk,
- volatility expansion,
- weak or missing participation,
- regime incompatibility or transition stress.

The important failure signature is:

```text
strong trend + short-term reversal + deceleration + elevated volatility/risk
```

That signature should become explicit `OVERHEATED_DECELERATING_ENTRY` or
`REVERSAL_RISK_ENTRY` evidence before BUY Quality can call a candidate full
allocation eligible.

## BUY_WAIT Role

BUY_WAIT is the correct first-class tool when:

```text
continuation thesis not invalid,
but current entry timing or evidence sufficiency is not good enough today
```

BUY_WAIT must remain:

- temporary,
- non-Pending,
- automatically re-evaluated on the next PIT business date,
- independent from SELL / REDUCE / EXIT,
- not a Runtime halt,
- not an implicit future commitment to buy.

For overheated but not invalid continuation, the expected action should be:

```text
OVERHEATED_DECELERATING_ENTRY -> BUY_WAIT or BUY_NEW_REDUCED_ONLY
REVERSAL_RISK_ENTRY -> BUY_WAIT or REJECT_BUY_NEW
```

The choice depends on evidence sufficiency, opportunity cost, participation,
relative strength, and regime context. It must not be driven by later outcome.

## One-Lot Root Cause

Current lot-aware logic correctly separates Strategy soft cap and Safety hard
cap, preserves residual recycling, and propagates one-lot quantity authority.
However, it can authorize a one-lot BUY_NEW when:

```text
continuous Strategy target is small
minimum executable lot is large
resulting effective exposure greatly exceeds Strategy target
Safety hard cap remains preserved
```

Phase30-U showed that Safety feasibility is not the same as Strategy desire.
The missing design is:

```text
quality-adjusted one-lot admission
```

## Strategy Target vs Safety Hard Cap

The implementation phase must keep these quantities separate:

| Concept | Meaning | Authority |
| --- | --- | --- |
| Strategy desired allocation | Continuous target weight before discrete lot expansion | Portfolio Construction |
| Minimum executable lot | Smallest broker-executable trading unit and notional | Position Sizing / broker metadata |
| Effective one-lot weight | Post-trade weight caused by buying one lot | Position Sizing evidence |
| Strategy concentration tolerance | Whether Strategy accepts the overshoot as economically justified | Portfolio Construction using Entry / ADD evidence |
| Safety hard cap | Final guardrail maximum exposure | Safety / Safety-derived cap evidence |

Safety hard cap must not become Strategy target. A trade may be safe enough to
allow operationally and still be unattractive as Strategy capital deployment.

## Quality-Adjusted One-Lot Design

Add a one-lot admission layer in PC/PS evidence handoff:

```text
one_lot_admission:
  status: PASS | DEFER | FAIL_CLOSED | REVIEW_REQUIRED
  lifecycle_intent: BUY_NEW | BUY_ADD | REENTRY
  continuous_target_weight
  minimum_executable_weight
  effective_post_trade_weight
  overshoot_weight
  overshoot_ratio_to_target
  strategy_concentration_tolerance
  safety_hard_cap_preserved
  entry_state
  add_worthiness_state
  relative_opportunity_state
  opportunity_cost_state
  residual_destination_if_skipped
  reason_codes
  future_information_used: false
```

Admission rules are semantic, not fitted thresholds:

- If one lot is within Strategy target/headroom, existing lot-aware flow can
  proceed.
- If one lot modestly exceeds Strategy target, admission may pass when entry
  state is healthy, risk is contained, relative opportunity is supportive, and
  opportunity cost is acceptable.
- If one lot extremely exceeds Strategy target, admission requires much stronger
  quality evidence than ordinary BUY_NEW. Safety pass alone is insufficient.
- If entry state is `OVERHEATED_DECELERATING_ENTRY` or `REVERSAL_RISK_ENTRY`,
  one-lot overshoot should normally be `DEFER` or `FAIL_CLOSED`, preserving
  Cash or recycling to a better executable candidate.
- If evidence is insufficient, do not treat missing evidence as safe.

No broad risk veto is introduced. High risk may reduce allocation, cause
BUY_WAIT, prevent ADD, or fail one-lot overshoot admission depending on the
evidence interaction.

## Residual Reallocation

Phase29 residual recycling should be preserved. The new requirement is to make
the queue quality-adjusted:

```text
skip/defer overlarge one-lot candidate
  -> recycle residual capital to next executable candidate
  -> compare BUY_NEW, BUY_ADD, REENTRY, and Cash by Production evidence
  -> keep Cash if no quality-adjusted executable candidate exists
```

Residual recycling order should use:

- Portfolio Construction priority,
- Entry Admission state,
- ADD worthiness,
- relative opportunity,
- downside risk,
- evidence sufficiency,
- lot feasibility,
- current exposure and Strategy concentration tolerance.

It should not use final PnL, later winner/loser labels, or 10BD audit outcome.

Cash is valid:

```text
Cash < bad concentration
```

No forced investment, forced BUY count, or forced exposure target is introduced.

## ADD / Winner Concentration

The repair must not only reduce BUY_NEW. It must also improve where skipped
capital can go.

ADD remains distinct from HOLD:

```text
HOLD-worthy != ADD-worthy
```

ADD requires incremental evidence:

- current CQ remains supportive,
- downside risk is contained or compensated by strong relative opportunity,
- incremental Expected Edge remains supportive though uncalibrated,
- existing exposure is not already too large,
- lot increment is Strategy-tolerable,
- no loss-averaging violation,
- opportunity cost versus BUY_NEW and Cash is acceptable.

94320-type behavior should not become "survived, therefore add." ADD must be a
positive incremental capital decision.

## Authority Boundaries

The repair preserves existing authority:

| Layer | Owns | Does not own |
| --- | --- | --- |
| Strategy Intelligence | CQ / risk / entry interpretation evidence | target weight, broker quantity, Runtime order |
| BUY Quality / BUY consumer | entry admission semantics | target portfolio allocation, Safety override |
| Portfolio Construction | target membership, allocation, opportunity comparison, Strategy concentration tolerance | broker quantity |
| Position Sizing | executable quantity, lot conversion, one-lot feasibility evidence | Entry Quality creation |
| Runtime Planning | mapping authorized upstream decisions to plan items | re-optimization |
| Safety | hard guardrail / review authority | performance optimization or Strategy target |
| PM | existing-position HOLD / ADD / REDUCE / EXIT authority | BUY_NEW universe membership |

SI must not decide quantity. Sizing must not invent entry quality. Safety hard
cap must not be used as Strategy allocation desire.

## SELL / REDUCE Preservation

Phase30-U classified SELL / REDUCE as improving. Phase30-V does not redesign
SELL / REDUCE.

Required preservation:

```text
BUY-side evidence failure cannot stop SELL / REDUCE / EXIT
BUY_WAIT cannot create Pending
Entry repair cannot suppress PM action authority
SELL independence regression must pass
```

## Regression / Evaluation Design

Minimum implementation-phase regression cases:

| Case | Required result |
| --- | --- |
| Healthy continuation | strong trend + contained risk can still produce BUY_NEW |
| Overheated/decelerating | strong medium momentum + short reversal + deceleration + elevated risk becomes BUY_WAIT / reduced / reject |
| High risk but genuine recovery | broad downside veto does not remove all optionality |
| One-lot modest overshoot | can pass if Strategy quality evidence is strong |
| One-lot extreme overshoot | fails/defer despite Safety pass when Strategy concentration is not justified |
| Residual recycle | skipped capital moves to next quality-adjusted executable candidate or Cash |
| ADD winner | high-quality existing winner receives incremental capital |
| Weak survivor | HOLD can remain while ADD is blocked |
| SELL independence | BUY-side repair does not stop SELL / REDUCE / EXIT |

Winner Preservation Gate must report:

- severe losers avoided,
- healthy Winners removed,
- BUY_WAIT later re-entry behavior,
- missed opportunity,
- winner HOLD,
- winner ADD,
- exposure,
- Cash,
- concentration.

Avoided 78780-type losses alone are not sufficient approval evidence.

## Leakage

Required flags:

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

78780 and the 10BD result are design evidence only. They must not become a
symbol/date rule, fitted threshold, or Runtime input.

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

The design uses existing Strategy Intelligence evidence and semantic consumer
interpretation. Expected Edge remains:

```text
UNCALIBRATED
economic_units_available = false
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-V
```

## Implementation Readiness

```text
PHASE30_W_IMPLEMENTATION_READY = YES
```

Readiness is limited to a scoped implementation task. Phase30-W should implement
Entry Admission and Quality-Adjusted One-Lot Admission with tests. It must not
perform threshold tuning, model retraining, Safety weakening, SELL redesign, or
Historical outcome fitting.

## Recommended Next Task

```text
Phase30-W - Entry Intelligence / One-Lot Capital Concentration Repair Implementation
```
