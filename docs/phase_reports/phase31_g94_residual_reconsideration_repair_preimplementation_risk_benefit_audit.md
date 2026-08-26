# Phase31-G94 -- Residual Reconsideration Repair Pre-Implementation Risk / Benefit Audit

## PRIMARY_JUDGMENT

PHASE31_G94_RESIDUAL_RECONSIDERATION_REPAIR_SHADOW_FIRST_RECOMMENDED

## Scope

READ-ONLY audit only.

Target run:

```text
runtime-test-historical-extended-smoke-20260824T055234719725Z
```

Evidence used:

```text
docs/phase_reports/phase31_g93_pc_residual_reconsideration_strong_candidate_competition_connectivity_audit.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260824T055234719725Z/daily/*/strategy/portfolio_construction.json
```

No code, config, threshold, weight, SoT, run state, fresh-run, resume, replay, or Historical execution was changed or executed. Future PnL, later winner status, MFE/MAE, and reference-run outcomes were not used as production decision labels.

## Executive Conclusion

G94 confirms that the G93 defect is a material canonical competition defect, not cosmetic evidence noise.

Architecture defines `REALLOCATABLE_RESIDUAL` as usable residual capital that must trigger PC-owned reconsideration. The current Post-G90 artifacts instead show `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` rows becoming:

```text
status = COMPETITOR_REJECTED_RECONSIDERABLE
accepted_weight = 0
requested_weight = 0
not in canonical security_allocations[]
not in cash_preferred_security_deferrals[]
not consumed by PS / Runtime
```

The affected population is broad: `545` rows across `167` business dates. The row population is not uniformly strong, but it is not weak tail only: `391 / 545` rows have `MIXED` or `SUPPORTIVE` same-date relative strength, rank is always within `1..10`, confidence is always at least `0.82`, and `13` rows are `COMPARABLE_HIGH` or `STRONG`.

Therefore repair is architecturally required, but direct authoritative binding is not yet justified. The correct next step is a shadow-first repair/evidence path that proves reconsidered rows re-enter canonical PC competition while still passing through G90 participation-vs-deferral, Cash competition, Safety terminality, lot feasibility, and PS quantity ownership.

## Required Final Judgments

```text
DEFECT_MATERIALITY = HIGH
REPAIR_ARCHITECTURALLY_REQUIRED = YES

RECONSIDERABLE_POPULATION_QUALITY = MIXED
RECONSIDERATION_ELIGIBLE_SHARE = 388 / 545 = 71.19% same-date plausibly reconsiderable; 154 / 545 = 28.26% likely Cash-dominated; 3 / 545 = 0.55% ambiguous
EXPECTED_COMPETITION_EXPANSION = MEDIUM

G80_STYLE_OVERDEPLOYMENT_RISK = MEDIUM
OPTIONAL_CASH_EROSION_RISK = MEDIUM
SAFETY_BYPASS_RISK = LOW
NORMAL_BEHAVIOR_DISRUPTION_RISK = MEDIUM

PLAUSIBLE_IMPROVEMENT_MECHANISM = YES

EXPECTED_LONG_RUN_PERFORMANCE_DIRECTION = POSITIVE_BIAS
CONFIDENCE = MEDIUM

CURRENT_G90_BEHAVIOR_CAN_BE_PRESERVED_BY_DESIGN = YES

RECOMMENDED_NEXT_STEP = SHADOW_FIRST
```

## Defect Necessity Audit

Architecture SoT:

```text
PC owns canonical capital allocation.
PS owns discrete quantity conversion only for PC-authorized rows.
REALLOCATABLE_RESIDUAL means capital appears usable by another valid competitor and must trigger reconsideration.
Residual / infeasible allocation reconsideration is PC-owned.
Remaining capital returns to Cash only after canonical reconsideration.
```

Observed implementation behavior:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION is produced.
The row remains visible in capital_competition.competitors[].
The row is not reconsidered into a positive final selected allocation.
The row is not represented as an explicit G90 Cash-preferred deferral.
Downstream PS and Runtime correctly do not resurrect it.
```

This is not merely a label problem. It removes rows from the canonical allocation/deferral decision surface before final PC competition is complete. That makes the input set incomplete for the PC-owned security/Cash decision.

## Reconsiderable Population Characterization

Artifact scan:

```text
TOTAL_DATES_WITH_REALLOCATABLE_ROWS = 167
TOTAL_REALLOCATABLE_ROWS = 545
ROWS_PER_DATE_MIN_Q1_MEDIAN_Q3_MAX = 1 / 2 / 3 / 4 / 7
```

Quality class distribution:

```text
COMPARABLE_MARGINAL = 532
COMPARABLE_HIGH = 10
STRONG = 3
```

Status distribution:

```text
COMPETITOR_REJECTED_RECONSIDERABLE = 545
```

Rank distribution:

```text
min = 1
q1 = 2
median = 5
q3 = 8
max = 10
```

Confidence distribution:

```text
min = 0.82
q1 = 0.86
median = 0.92
q3 = 0.98
max = 1.00
```

Runtime opportunity score distribution:

```text
min = -0.328253
q1 = -0.088465
median = +0.107210
q3 = +0.232471
max = +0.498250
```

Momentum distribution:

```text
MIXED_OR_UNRESOLVED = 370
HEALTHY_CONTINUATION = 175
```

Relative-strength distribution:

```text
MIXED = 208
SUPPORTIVE = 183
WEAK = 154
```

Entry state/action:

```text
CONTINUATION_WITH_CAUTION / BUY_NEW_REDUCED_ONLY = 532
HEALTHY_CONTINUATION_ENTRY / BUY_NEW_ALLOWED = 13
```

Quality status:

```text
PASS = 545
```

Lot / sizing context:

```text
reference_price min/q1/median/q3/max = 2.0 / 27.0 / 161.0 / 839.6 / 5490.0
accepted_weight = 0 for all 545 rows
requested_weight = 0 for all 545 rows
explicit lot feasibility class = not populated on the rejected row surface
explicit safety terminal state = not populated on the rejected row surface
```

Capital-budget context:

```text
available_incremental_budget min/q1/median/q3/max = 0.0 / 0.267265 / 0.393172 / 0.572872 / 0.885408
```

Cash / residual reason context observed on dates with these rows:

```text
UNAVOIDABLE_LOT_RESIDUAL = 315 row-weighted occurrences
VALID_POLICY_RESERVE = 145 row-weighted occurrences
CONCENTRATION_BLOCK = 140 row-weighted occurrences
NO_VALID_COMPETITOR = 85 row-weighted occurrences
```

Interpretation:

```text
RECONSIDERABLE_POPULATION_QUALITY = MIXED
```

Most rows are `COMPARABLE_MARGINAL`, so the population is not a clean strong-only missed-winner set. But the same rows also have high confidence, high rank, complete quality evidence, and many `MIXED`/`SUPPORTIVE` relative-strength states. Treating the entire population as weak tail would be inconsistent with same-date evidence.

## Estimated Re-entry Pressure

This classification is a READ-ONLY characterization, not a production rule.

Classification method used only existing same-date row evidence:

```text
clearly eligible for reconsideration:
  class in STRONG / COMPARABLE_HIGH / COMPARABLE_MARGINAL
  rank <= 20
  confidence >= 0.70
  score >= -0.30 when available
  relative_strength in SUPPORTIVE / MIXED

likely Cash-dominated:
  relative_strength = WEAK
  or very low score / rank / confidence if present

ambiguous:
  insufficient distinction after the above checks
```

Results:

```text
clearly_eligible_for_reconsideration = 388
likely_Cash_dominated = 154
Safety_or_lot_terminal = 0 directly proven on this row surface
evidence_insufficient = 0
ambiguous = 3

RECONSIDERATION_ELIGIBLE_SHARE = 388 / 545 = 71.19%
EXPECTED_COMPETITION_EXPANSION = MEDIUM
```

The expected expansion is not `HIGH` because per-date counts are bounded (`median = 3`, `max = 7`) and all rows still need PC-owned downstream resolution. It is not `LOW` because the issue appears on `167` dates and affects hundreds of rows.

## Overdeployment Risk

```text
G80_STYLE_OVERDEPLOYMENT_RISK = MEDIUM
```

Risk drivers:

```text
COMPARABLE_MARGINAL dominates the population: 532 / 545 rows.
154 rows have WEAK same-date relative strength.
Many rows are reduced-only / caution-continuation rather than full healthy entry.
If a repair directly authorizes all reconsiderable rows, it could recreate weak-tail deployment pressure.
```

Risk controls that must be preserved:

```text
Reconsidered rows must still pass G90 participation-vs-deferral.
Cash remains a first-class economic competitor.
Capital budget remains a maximum, not a forced spend target.
Rows resolved to CASH_PREFERRED_DEFER must stay zero security weight.
Safety terminal rows must not re-enter reconsideration.
PS must not independently revive defeated rows.
Runtime must not redo capital priority.
```

With those controls, the repair expands the canonical competition surface without necessarily expanding actual deployment.

## Cash Preservation Risk

```text
OPTIONAL_CASH_EROSION_RISK = MEDIUM
```

Cash erosion risk is medium before implementation because the affected population is broad. A careless repair could treat `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` as automatic security authorization and thereby erode optional Cash.

A correct design can preserve current G90 behavior:

```text
REALLOCATABLE row -> PC reconsideration candidate
PC reconsideration -> same canonical security/Cash partition
G90 resolver -> PARTICIPATION_VALID or DEFER
DEFER -> authorized_cash_allocation / explicit Cash
```

The repair must not bypass Cash competition and must not force exposure, position count, or budget exhaustion.

## Safety Risk

```text
SAFETY_BYPASS_RISK = LOW
```

G93 already separated `VALID_SAFETY_RESERVE` from `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`. `VALID_SAFETY_RESERVE` is terminal and correct. No repair should weaken it.

Required preservation:

```text
VALID_SAFETY_RESERVE remains terminal.
SAFETY_CAP_BOUND remains terminal.
Malformed / missing safety evidence remains fail-closed.
Reconsideration only applies to non-terminal reallocatable residual semantics.
```

If an implementation requires weakening Safety, it should be rejected.

## Normal-Behavior Disruption Risk

```text
NORMAL_BEHAVIOR_DISRUPTION_RISK = MEDIUM
```

The current Post-G90 behavior is strong enough to be a preservation target. Reconnecting `545` rows across `167` dates can materially change:

```text
security count
cash balance
exposure
BUY_NEW frequency
ADD / NEW_BUY competition
same-day deployment breadth
```

The disruption risk is not `HIGH` because the repair can be constrained to shadow first and then to canonical competition rather than direct order generation. It is not `LOW` because the affected set is broad and includes many high-rank rows.

## Plausible Improvement Mechanism

```text
PLAUSIBLE_IMPROVEMENT_MECHANISM = YES
```

The improvement mechanism is process correctness, not hindsight return:

```text
stronger or credible rows receive canonical PC competition instead of silent exclusion
post-SELL or residual budget can be reconsidered against credible alternatives
Cash can still win when alternatives are weak
weak-tail deferrals remain possible through G90
opportunity-set breadth becomes visible to the authoritative PC decision
PS and Runtime remain bound to PC output instead of resurrecting rows
```

This mechanism could improve long-run deployment quality because it closes a missing-competition boundary while preserving Cash and Safety. It does not prove any historical return uplift.

## Performance Direction Confidence

```text
EXPECTED_LONG_RUN_PERFORMANCE_DIRECTION = POSITIVE_BIAS
CONFIDENCE = MEDIUM
```

Reasoning:

```text
Positive bias:
  The defect excludes same-date credible competitors before canonical competition completes.
  Restoring reconsideration improves architecture conformance and opportunity-set completeness.

Uncertainty:
  Most rows are COMPARABLE_MARGINAL, not STRONG.
  154 rows are WEAK relative-strength rows that should often remain Cash-dominated.
  Current Post-G90 baseline is strong and must not be disrupted.
  Performance direction cannot be inferred from later PnL or winner status.
```

Therefore the expected direction is positive-biased at the decision-process level, with medium confidence and no return-percentage forecast.

## Current G90 Behavior Preservation

```text
CURRENT_G90_BEHAVIOR_CAN_BE_PRESERVED_BY_DESIGN = YES
```

A safe design can preserve G90 by requiring:

```text
existing selected G90 allocations remain valid
reconsideration adds missing canonical competition only
Cash remains first-class and can win
Safety remains terminal
no forced exposure increase
no forced position-count increase
no new threshold / score / fixed cutoff
capital budget remains maximum deployable capital
reconsidered rows still pass G90 participation-vs-deferral before final publication
```

This means G90 should not be rolled back or weakened to repair G93/G94. The repair boundary is PC residual reconsideration connectivity.

## Shadow-First Decision

```text
RECOMMENDED_NEXT_STEP = SHADOW_FIRST
```

`NO_REPAIR` is not appropriate because the defect violates the canonical residual reconsideration contract and affects many dates.

`DIRECT_BINDING` is not appropriate yet because the population is broad, mostly `COMPARABLE_MARGINAL`, and includes a material `WEAK` relative-strength subset. Direct binding would risk turning a missing-competition repair into forced deployment.

The next task should implement or produce a non-authoritative shadow path that demonstrates:

```text
REALLOCATABLE rows re-enter PC-owned reconsideration
G90 still resolves participation vs deferral
Cash remains explicit and first-class
Safety terminality is untouched
authorized security allocations change only after canonical competition
PS quantity ownership is preserved
Runtime priority redecision remains NO
```

## Integrity

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
SOT_CHANGED = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_STRATEGY_INPUT_USED = NO
```
