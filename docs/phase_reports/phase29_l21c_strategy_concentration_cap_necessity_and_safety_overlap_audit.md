# Phase29-L21C - Strategy Concentration Cap Necessity / Safety Hard Cap Overlap Audit

Task ID: `Phase29-L21C`

Mode:

```text
READ-ONLY ARCHITECTURE / POLICY NECESSITY AUDIT
NO IMPLEMENTATION
NO CURRENT RUN MUTATION
NO RESUME / FRESH-RUN / RUN / PENDING_LIFECYCLE / REPAIR
NO LONG HISTORICAL EXECUTION
```

## 1. Primary Judgment

```text
PHASE29_L21C_STRATEGY_CAP_SOFT_BOUNDARY_HARD_ENFORCEMENT_MISMATCH_CONFIRMED
```

Additional classification:

```text
SOFT_BOUNDARY_IMPLEMENTED_AS_HARD
PARTIAL_ARCHITECTURE_DRIFT
SAFETY_ROLE_DUPLICATION
INTENTIONAL_BUT_NOW_REDUNDANT_AS_HARD_PROHIBITION
```

The 18% Strategy concentration cap was intentionally introduced in Phase22 as a Strategy sizing / diversification boundary distinct from the 25% Safety hard cap. That original separation is valid:

```text
Strategy cap = desired allocation discipline
Safety hard cap = final non-negotiable risk boundary
```

The current L21B evidence shows that this Strategy boundary is now functioning as a hard prohibition at the discrete-lot boundary:

```text
PM ADD passes economic eligibility
pre-lot target/increment increases
minimum executable ADD crosses 18% Strategy cap
post-lot weight remains <= 25% Safety hard cap
final target increase = 0
Runtime Planning = NO_ACTION
```

This is too hard for the current momentum-following / ADD strategy. The Strategy cap remains useful as a target or soft boundary, but the evidence does not support keeping it as a hard zero-share prohibition when the lot overshoot remains within Safety hard cap and other Safety / Submit / Broker controls remain active.

Primary recommendation:

```text
B. Make Strategy cap soft / lot-aware overshoot
```

Do not remove all Strategy concentration semantics as a first move. Preserve the 18% cap as desired target / attribution boundary, but allow lot-aware overshoot for economically accepted ADD when the resulting post-trade weight remains within independent Safety hard cap.

## 2. Strategy Cap Origin

Origin:

| Field | Finding |
|---|---|
| introduced_phase | Phase22-J |
| introduced_commit | `55a7c63 phase22 FIX` |
| config | `configs/strategy/position_sizing.json#strategy_maximum_position_weight = 0.18` |
| implementation | `src/ai_fund_lab_v2/strategy/position_sizing.py` |
| test lineage | `tests/strategy/test_phase22_j_position_sizing.py` |
| original owner component | Strategy / Position Sizing |

Phase22-J explicitly states:

```text
Strategy sizing cap is separate:
configs/strategy/position_sizing.json
strategy_maximum_position_weight = 0.18
```

It also defined the independent Safety concentration hard limit:

```text
configs/safety/portfolio_limits.json#concentration.maximum_position_weight = 0.25
authority_owner = Safety Layer
override_allowed = false
scope = production / demo / historical
```

Git blame confirms both were introduced by `55a7c63`:

```text
configs/strategy/position_sizing.json:37 strategy_maximum_position_weight = 0.18
configs/safety/portfolio_limits.json:45 concentration.maximum_position_weight = 0.25
```

## 3. Original Design Intent

Original intent:

```text
Separate Strategy target from Safety hard limit and execution feasibility.
```

Phase22-J selected method:

```text
capped_quality_volatility_hybrid
```

Stages included:

```text
Base allocation
Opportunity quality multiplier
Volatility inverse multiplier
PM / membership adjustment
Strategy and Safety concentration cap
Portfolio total normalization
Minimum meaningful notional validation
Residual cash preservation
```

The Strategy cap therefore began as a normal sizing discipline for target construction. It was not introduced as a broker, Runtime, Pending, Submit, or Safety authority.

## 4. Current Runtime Semantics

Current semantics are harder than the original target discipline:

```text
effective_cap = min(strategy_maximum_position_weight, safety_maximum_position_weight)
```

Position Sizing currently uses:

```text
max_weight = min(config.strategy_maximum_position_weight, safety_cap)
```

L19 lot preflight uses:

```text
concentration_cap = config.strategy_maximum_position_weight
concentration_headroom = strategy_cap - current_weight
maximum_strategy_feasible_lots = floor(strategy_headroom / one_lot_weight)
```

Portfolio Construction lot-aware final reallocation then blocks when:

```text
required_weight > single_name_cap - baseline_weight
=> minimum_lot_exceeds_concentration_cap
```

Thus the Strategy cap is currently both:

```text
target allocation cap
and
hard executable-lot prohibition
```

## 5. Safety Hard Cap Semantics

Safety cap:

| Field | Value |
|---|---|
| source | `configs/safety/portfolio_limits.json#concentration.maximum_position_weight` |
| value | 0.25 |
| owner | Safety Layer |
| scope | production / demo / historical |
| override_allowed | false |
| semantics | hard final single-name concentration ceiling |

Phase22-QA repaired the Safety authority wiring and confirmed:

```text
strategy_maximum_position_weight = 0.18
safety_maximum_position_weight = 0.25
effective_maximum_position_weight = 0.18
```

Safety hard cap remains the correct final defense against unacceptable concentration.

## 6. Strategy vs Safety Overlap

| Dimension | Strategy concentration cap | Safety hard cap |
|---|---|---|
| Purpose | Desired allocation discipline / diversification | Final hard risk boundary |
| Producer | Strategy config / Portfolio Policy / Position Sizing | Safety config / Safety authority |
| Consumer | Portfolio Construction, Position Sizing, Buy Quality fit, observability | Position Sizing, Runtime safety/submit evidence, Safety loaders |
| Config | 0.18 | 0.25 |
| Hard / soft in design | Strategy target boundary | Hard limit |
| Hard / soft in current code | Hard executable blocker | Hard limit |
| Failure behavior | target increase becomes 0 / cash retained | block/review if breached |
| Production/Demo/Historical | common Strategy evidence | common Safety authority |

Overlap assessment:

```text
There is valid conceptual separation.
There is current hard-enforcement overlap.
```

The problem is not the existence of a Strategy cap. The problem is that a Strategy target cap is being enforced as if it were the final Safety hard cap at the discrete-lot boundary.

## 7. L21B 23-Case Quantification

Evidence window:

```text
completed_business_days = 50
first = 2022-08-10
last = 2022-10-24
run_status = HALT
next_job = 2022-10-25:submit
```

L21B blocked ADD cases:

```text
count = 23
symbols = 94320 x 22, 37820 x 1
boundary = DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX
Safety hard breach count = 0
```

Aggregate:

| Metric | Min | Median | Max | Average |
|---|---:|---:|---:|---:|
| current weight | 13.4514% | 13.9324% | 15.6688% | 14.0481% |
| Strategy headroom | 2.3312% | 4.0676% | 4.5486% | 3.9519% |
| Safety headroom | 9.3312% | 11.0676% | 11.5486% | 10.9519% |
| one-lot weight | 0.9318% | 1.5394% | 1.6114% | 1.5230% |
| minimum policy lots | 4 | 4 | 6 | 4.09 |

The cases are not Safety-near. Even after strict minimum-policy-lot overshoot, median remaining Safety margin is about 4.90 percentage points.

## 8. Lot Overshoot Magnitude

Strict minimum-policy-lot interpretation:

| Metric | Min | Median | Max | Average |
|---|---:|---:|---:|---:|
| post-lot weight | 19.4658% | 20.1008% | 21.2596% | 20.2211% |
| Strategy cap overshoot | 1.4658% | 2.1008% | 3.2596% | 2.2211% |
| Safety margin after lot | 3.7404% | 4.8992% | 5.5342% | 4.7789% |
| blocked minimum quantity | 400 | 400 | 600 | 408.70 |
| blocked minimum notional | 55,200 JPY | 61,560 JPY | 64,560 JPY | 61,417 JPY |

Under a current-code-like soft simulation that accepts required ADD weight and then lets Position Sizing lot conversion materialize quantity, the recovered quantity is mostly 300 shares:

```text
soft simulated quantity range = 300 to 500
soft simulated post weight range = 17.9622% to 20.3278%
soft simulated Safety breach count = 0
```

The exact implementation choice needs design, but both interpretations show the same architecture fact:

```text
0 / 23 cases are Safety hard cap breaches.
```

## 9. Safety Headroom

Safety headroom before ADD:

```text
min = 9.3312 percentage points
median = 11.0676 percentage points
max = 11.5486 percentage points
```

Safety margin after strict minimum-policy-lot ADD:

```text
min = 3.7404 percentage points
median = 4.8992 percentage points
max = 5.5342 percentage points
```

Therefore these are moderate Strategy-cap overshoots, not Safety-limit approaches.

## 10. Hypothetical Policy A Result

Policy A:

```text
Strategy target is soft.
Minimum-lot overshoot is allowed if post-lot exposure <= Safety hard cap.
```

Result:

```text
23 / 23 blocked ADD cases become potentially executable.
Safety hard cap breach count = 0.
post-lot concentration range = 19.4658% to 21.2596% under strict minimum-policy-lot interpretation.
```

Effect:

```text
Recover ADD conversion without weakening final Safety hard cap.
Preserve Strategy cap as desired target / attribution boundary.
```

## 11. Hypothetical Policy B Result

Policy B:

```text
No Strategy concentration hard cap.
Safety hard cap only.
```

Result on the 23 L21B cases:

```text
23 / 23 blocked ADD cases become potentially executable.
Safety hard cap breach count = 0.
post-lot concentration remains below 25%.
```

Policy B has higher architecture blast radius because `single_name_weight_cap` and `strategy_maximum_position_weight` are consumed by Portfolio Policy, Portfolio Construction, Position Sizing, Buy Quality portfolio fit, observability, and tests. It is feasible as a direction, but not the lowest-risk next step.

## 12. Existing Safety Coverage

If the Strategy hard executable cap is softened or removed, these controls remain:

| Safety / guard | Remains? | Notes |
|---|---|---|
| Safety hard single-name concentration | YES | `concentration.maximum_position_weight = 0.25` |
| Gross exposure safety | YES | no-leverage `maximum_gross_exposure_ratio = 1.0` |
| Cash / buying power feasibility | YES | Submit and planning feasibility authorities |
| Lot feasibility | YES | PS lot preflight and quantity conversion remain |
| Liquidity guard | YES | low-price/liquidity allocation authority remains |
| Low-price guard | YES | PC low-price risk authority remains |
| Corporate action quarantine | YES | Submit guard / CA quarantine remains |
| Pending / submit safety | YES | Pending, Safety, Submit item evidence remain |
| Broker boundary safety | YES | broker product / quantity / cash checks remain |

Final defense does not depend on the 18% Strategy cap being hard.

## 13. Hidden Dependencies

Observed dependencies:

```text
configs/strategy/portfolio_policy.json#single_name_weight_cap = 0.18
configs/strategy/position_sizing.json#strategy_maximum_position_weight = 0.18
src/ai_fund_lab_v2/strategy/portfolio_policy.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
src/ai_fund_lab_v2/strategy/buy_quality.py
src/ai_fund_lab_v2/strategy/observability.py
src/ai_fund_lab_v2/strategy/shadow_runtime.py
src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_j_position_sizing.py
```

Hidden dependency assessment:

| Component | Risk if hard cap removed without design |
|---|---|
| Portfolio Construction | HIGH: target contract currently says `target_weight <= single_name_weight_cap` |
| Position Sizing | HIGH: `effective_cap = min(strategy, safety)` is schema/validator evidence |
| Runtime Planning | LOW: maps quantity deltas, not cap policy |
| Pending generation | LOW: consumes planning candidates |
| Submit feasibility | LOW/MEDIUM: revalidates quantities and safety evidence |
| Safety | LOW: independent Safety cap remains |
| Observability | MEDIUM: cap fields are reported and indexed |
| Historical evidence | MEDIUM: comparability changes |
| Production/Demo path | MEDIUM/HIGH if cap semantics are changed without common contract |

Conclusion:

```text
Do not delete fields ad hoc.
First change semantics: Strategy cap target/soft boundary vs Safety hard cap.
```

## 14. Architecture Complexity Assessment

Current stack:

```text
Strategy target_weight
Strategy single-name cap
Position Sizing strategy_maximum_position_weight
Safety maximum_position_weight
Lot feasibility
Portfolio Construction lot-aware final reallocation
Submit/Safety revalidation
```

This is too overlapping at the ADD discrete-lot boundary. A cleaner architecture is:

```text
1. Strategy decides desired target and preferred concentration.
2. Lot-aware sizing materializes executable quantity.
3. Safety enforces only hard final boundaries.
```

The current implementation partially violates that by letting the Strategy preferred concentration become the hard final boundary even when Safety has explicit remaining headroom.

## 15. Architecture Drift Classification

```text
SOFT_BOUNDARY_IMPLEMENTED_AS_HARD = CONFIRMED
PARTIAL_ARCHITECTURE_DRIFT = CONFIRMED
SAFETY_ROLE_DUPLICATION = PARTIAL
LEGACY_CONSTRAINT_REMAINING = PARTIAL
INTENTIONAL_AND_STILL_REQUIRED = YES_AS_TARGET_ONLY
INTENTIONAL_BUT_NOW_REDUNDANT = YES_AS_HARD_PROHIBITION
```

This is not a regression finding. It is an accumulation of valid earlier separations plus later ADD/lot-aware requirements exposing that the Strategy cap is doing more than a target cap should do.

## 16. Recommended Target Architecture

Primary recommendation:

```text
B. Make Strategy cap soft / lot-aware overshoot
```

Recommended semantics:

```text
Strategy cap remains the desired target cap and normal allocation boundary.
For existing-position BUY_ADD only, if ADD eligibility passes and the minimum executable lot crosses Strategy cap but remains within Safety hard cap, allow the lot-aware overshoot with explicit evidence.
Safety hard cap remains non-negotiable.
```

Reasoning:

| Dimension | Assessment |
|---|---|
| Strategy intent | Preserves 18% as desired allocation discipline |
| Risk control | Safety 25% remains final hard boundary |
| Japanese lot structure | Avoids zeroing valid ADD because 100-share/min-notional granularity is coarse |
| Capital utilization | Recovers 23 / 23 L21B blocked ADD cases in read-only simulation |
| Architecture simplicity | Clarifies target vs hard limit without deleting all cap evidence |
| Regression risk | Lower than full Strategy cap removal |

Candidate C, removing Strategy concentration hard cap and relying on Safety hard cap only, is plausible later but should follow a broader contract update because `single_name_weight_cap` is embedded in Strategy contracts and tests.

## 17. Regression Risk

Regression risk for Policy A:

```text
MEDIUM
```

Main risks:

```text
target_weight contract currently requires <= single_name_weight_cap
Position Sizing schema reports effective_maximum_position_weight
Buy Quality portfolio_fit uses single_name_weight_cap
Observability and tests assume 0.18 hard cap in places
```

Risk mitigations for a future implementation:

```text
Add explicit lot_overshoot_authority evidence.
Limit to existing-position BUY_ADD with PM ADD and eligibility PASS.
Require post-trade weight <= Safety hard cap.
Require cash/buying_power/lot/broker/submission feasibility.
Record strategy_cap_overshoot_weight and safety_margin_after_trade.
Keep BUY_NEW under normal Strategy target cap unless separately approved.
```

## 18. Implementation Required YES/NO

For this audit:

```text
NO
```

For the recommended architecture change:

```text
YES
```

The required implementation should be a production/demo/historical common Strategy contract repair, not a historical-only patch.

## 19. Current Run Mutation NO

```text
NO
```

The target run was not resumed, repaired, reset, abandoned, rolled back, or manually edited.

## 20. Long Historical Executed NO

```text
NO
```

Only read-only commands were used.

## 21. Recommended Next Task

```text
Phase29-L21D - Lot-Aware Strategy Cap Soft Boundary Design
```

Proposed scope:

```text
DESIGN ONLY first.
Define a production-common contract for BUY_ADD lot-aware Strategy cap overshoot
inside Safety hard cap, including evidence fields, failure behavior, tests, and
consumer compatibility.
```

Acceptance target for that design:

```text
Strategy desired cap remains observable.
Safety hard cap remains final.
No forced deployment.
No BUY_NEW cap loosening unless separately approved.
No Runtime Planning special case.
No Historical-only behavior.
```
