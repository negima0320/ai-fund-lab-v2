# Phase31-B2 — Winner Amplification / Marginal Capital Priority Contract Design

## PRIMARY_JUDGMENT

`DESIGN_MARGINAL_CAPITAL_VALUE_AUTHORITY_WITH_LIFECYCLE_AWARE_ADD_AND_CONTROLLED_WINNER_HEADROOM`

The recommended design is a Strategy-side marginal capital competition contract owned by Portfolio Construction. BUY_NEW and BUY_ADD should compete in one canonical marginal-capital ordering based on decision-time evidence of the next deployable unit's value. BUY_ADD must not receive unconditional priority, but current lifecycle/winner-continuation evidence may legitimately contribute to its marginal value when Expected Edge, Incremental Investment Value, Opportunity Cost, Market Context, concentration, lot feasibility, and Safety preservation all remain valid.

The design should be staged: first define and validate canonical marginal-capital ordering; then, if validation supports it, add a controlled winner-amplification region between the normal Strategy cap and the Safety hard cap. The Safety hard cap remains separate and hard. No implementation or parameter change is authorized.

## Required Fields

| Field | Value |
| --- | --- |
| `RECOMMENDED_ARCHITECTURE` | Alternative C as the core, staged toward Alternative E after validation: PC-owned `MARGINAL_CAPITAL_VALUE_AUTHORITY` ranks executable BUY_NEW and BUY_ADD increments in one PIT order; PS materializes quantities; Runtime Planning consumes the canonical order for reserved-notional feasibility. A controlled winner-amplification region may be introduced only as a separately governed Strategy region below Safety hard cap. |
| `MARGINAL_CAPITAL_AUTHORITY_OWNER` | Portfolio Construction. |
| `BUY_ADD_UNCONDITIONAL_PRIORITY` | `NO` |
| `BUY_NEW_UNCONDITIONAL_PRIORITY` | `NO` |
| `LIFECYCLE_AWARE_ADD_PRIORITY_SUPPORTED` | `CONDITIONAL` |
| `PROCESSING_ORDER_AS_INVESTMENT_AUTHORITY` | `NO` |
| `NORMAL_STRATEGY_CAP_SEMANTIC` | Current SoT: Strategy cap is the normal allocation/target ceiling and attribution boundary, not the Safety hard cap. Current configured/evidenced normal cap is `0.18` via `configs/strategy/portfolio_policy.json#single_name_weight_cap` and `configs/strategy/position_sizing.json#strategy_maximum_position_weight`. It already permits narrow explicit lot-aware overshoot only with coherent PC authority and Safety hard-cap preservation. |
| `WINNER_AMPLIFICATION_REGION_RECOMMENDED` | `YES`, as a design concept requiring validation before implementation. |
| `SAFETY_HARD_CAP_SEPARATE` | `YES`. Current Safety hard cap is `0.25` via `configs/safety/portfolio_limits.json#concentration.maximum_position_weight`; it must not become a winner target or Strategy target. |
| `EXPECTED_EDGE_WEAKENING_STILL_BLOCKS_ADD` | `YES`. B1 found 35 Expected Edge weakening first drops. Weakening versus the PIT same-campaign baseline means incremental ADD value is not proven; existing winner status alone must not override it. |
| `FIXED_ADD_RESERVE_RECOMMENDED` | `NO` |
| `EXISTING_FEATURES_SUFFICIENT` | `MOSTLY`. Existing evidence is sufficient for the contract concept: Expected Edge, Incremental Investment Value, Opportunity Cost, rank/score, ADD-worthiness, momentum/trend, Market Context, current/target weight, campaign state, and lot/Safety evidence. A new feature may be needed only to materialize a normalized auditable `marginal_capital_value_class` / order key, not to add a new predictor. |
| `PERFORMANCE_IMPLEMENTATION_AUTHORIZED` | `NO` |
| `VALIDATION_DESIGN_REQUIRED_BEFORE_IMPLEMENTATION` | `YES`. Validation must pre-register PIT-only metrics, compare candidate order/funnel changes without using future outcomes as thresholds, verify no Safety/cap regression, and test discrete-lot and cash-order behavior before any Strategy/Runtime change. |

## Recommended Architecture

Add a canonical Portfolio Construction contract:

```text
MARGINAL_CAPITAL_VALUE_AUTHORITY
```

Purpose:

```text
Rank the next deployable units of capital across BUY_NEW and BUY_ADD using
only decision-time Strategy evidence, before Runtime Planning reserves cash.
```

Canonical output should be evidence, not a broker order:

```text
marginal_capital_competition = {
  authority_type,
  business_date,
  candidate_units[],
  canonical_order[],
  order_reason,
  pit_status,
  no_future_information_used
}

candidate_units[] = {
  symbol,
  lifecycle_intent: BUY_NEW | BUY_ADD,
  marginal_capital_value_class,
  canonical_marginal_priority_index,
  requested_incremental_weight,
  accepted_incremental_weight,
  lot_aware_quantity_requirement,
  concentration_region,
  expected_edge_state,
  incremental_investment_value_state,
  opportunity_cost_state,
  market_context_state,
  add_lifecycle_evidence_if_any,
  blocking_or_reduction_reasons
}
```

This order should feed existing PC budget reconciliation and lot-aware final reallocation. PS then consumes PC target/discrete quantity authority. Runtime Planning must preserve `canonical_marginal_priority_index` when building the reserved-notional cash-feasible BUY batch. Runtime may prune for cash or review, but it must not invent NEW-vs-ADD investment preference from iteration order.

## Marginal Capital Competition

The competition question is:

```text
Where does the next lot-sized, Safety-valid, PIT-justified unit of capital have
the highest marginal value today?
```

BUY_NEW evidence can include:

- runtime opportunity score / rank under the uncalibrated relative score contract;
- Buy Quality and entry admission;
- Market Context compatibility;
- concentration, lot, broker, and cash feasibility;
- no hard no-buy or review guard.

BUY_ADD evidence can include all comparable evidence plus existing-position lifecycle evidence:

- PM ADD intent and ADD-worthiness;
- same-campaign Expected Edge trajectory;
- Incremental Investment Value;
- Opportunity Cost against BUY_NEW / REENTRY / Cash;
- current campaign state, observed PIT MFE/giveback, ADD spacing/history;
- no-loss-averaging;
- current weight, target weight, normal cap region, passive drift state.

Lifecycle-aware ADD priority is conditional: when BUY_ADD and BUY_NEW are otherwise comparable, a strong ADD may rank higher because it has current same-campaign continuation evidence and has already survived entry/holding validation. That is a legitimate investment signal, not a side label premium. If Expected Edge weakens, Opportunity Cost fails, Market Context deteriorates, or concentration headroom is not authorized, the lifecycle component should not rescue the ADD.

## Cap And Winner Region

Current confirmed values:

```text
normal Strategy cap ~= 0.18
Safety hard cap ~= 0.25
```

The normal Strategy cap should be treated as:

```text
NORMAL_POSITION_REGION target ceiling
```

not as the Safety boundary. Existing SoT already allows narrow explicit lot-aware overshoot when PC proves the overshoot is coherent and Safety hard cap is preserved.

B2 recommends validating a conceptual three-region model:

```text
NORMAL_POSITION_REGION
-> WINNER_AMPLIFICATION_REGION
-> SAFETY_HARD_CAP
```

The winner-amplification region must not define a numeric cap in this design. It is a semantic region where additional ADD can be considered only if PC proves:

- PM ADD and ADD-worthiness are present;
- Expected Edge is PASS, not weakening;
- Incremental Investment Value is POSITIVE;
- Opportunity Cost does not prefer available NEW / REENTRY / Cash;
- Market Context does not materially worsen;
- trend / momentum / campaign evidence remains supportive;
- current position is not being profit-protected, REDUCE, or EXIT;
- lot/discrete post-trade quantity is coherent;
- Strategy winner-headroom authority is explicit;
- Safety hard cap margin remains positive.

Exit/de-amplification semantics remain owned by PM/PC/REDUCE/EXIT and Safety. Passive drift alone should not force sell unless existing Strategy/Safety contracts require it. Deterioration or regime worsening should block further ADD and may trigger profit protection, REDUCE, or EXIT through existing authorities.

## Passive Cap Drift Cases

| Case | Design behavior |
| --- | --- |
| A. Above normal target, winner evidence weak | Retain baseline if no sell authority exists, but no new ADD. Cash/NEW may compete normally. |
| B. Above normal target, winner evidence strong | Do not automatically ADD. PC may consider winner-amplification region only through explicit marginal-capital and winner-headroom authority. |
| C. Above normal target, momentum deteriorates | No ADD. Existing PM/profit-protection/REDUCE/EXIT evidence should govern risk reduction. |
| D. Above normal target, Market Context worsens | No automatic ADD; require stricter pass or fail closed to retain-only / reduce-review depending on existing Market/Policy evidence. |

## Lot And Runtime Ordering

Ranking must occur before Runtime Planning cash reservation, but it must be lot-aware enough to survive PS:

```text
PC marginal value order
-> PC budget / lot-aware final reallocation / discrete quantity authority
-> PS target-to-quantity consumption
-> Runtime Planning canonical order preservation
-> reserved-notional cash-feasible batch
```

The marginal unit should be a feasible lot-sized increment or an explicitly pending/reviewed candidate. The design must not rank fractional theoretical capital that later disappears due to lot rounding. If lot feasibility changes the executable unit, PC must re-evaluate the marginal order or record that the item is skipped/reduced for lot reasons.

## Owner Boundaries

| Component | Owns | Does not own |
| --- | --- | --- |
| PM | Existing-position intent; ADD eligibility and lifecycle evidence | Final capital allocation; quantity; Runtime order |
| Portfolio Construction | Marginal capital competition; target weights; Strategy concentration/headroom; NEW vs ADD capital ordering; discrete executable quantity authority after lot-aware reallocation | Runtime cash state mutation; broker submit; Safety hard boundary |
| Position Sizing | Target-to-notional/quantity materialization; quantity delta; lot rounding consumption of PC authority | Investment priority policy |
| Runtime Planning | Consumption of canonical Strategy order; pending item construction; reserved-notional feasibility in canonical order | NEW vs ADD investment preference; target weights; position sizing |
| Safety | Hard safety boundary and fail-closed safety review | Winner target allocation; marginal investment priority |

## Opportunity Scarcity Rules

- Strong ADD, weak NEW: capital can flow primarily to ADD if ADD passes marginal-capital, headroom, lot, and Safety evidence.
- Strong NEW, weak ADD: capital can flow primarily to NEW; ADD label receives no rescue.
- Strong ADD and strong NEW: canonical marginal-capital comparison decides and preserves evidence.
- No strong opportunities: Cash is valid; no forced deployment.

## ALTERNATIVE_COMPARISON

| Alternative | Judgment |
| --- | --- |
| A. Status Quo | Reject as final design. It is PIT-correct in many cases but lets processing order become accidental capital priority, as B0 showed. |
| B. Fixed ADD Priority | Reject. It violates opportunity-following philosophy, can starve NEW, over-amplify weak survivors, and ignores B1 Expected Edge weakening cases. |
| C. Marginal Capital Value with Lifecycle-Aware ADD Evidence | Recommend as core. It aligns with momentum-swing philosophy, preserves PIT correctness, avoids unconditional side priority, and makes Runtime order a consumer of Strategy order. |
| D. Separate Winner Amplification Budget | Defer/reject as default. It is auditable but risks fixed reserves, forced ADD, and unused capital when ADD is weak. |
| E. Marginal Capital Competition + Controlled Winner Headroom | Recommend as staged target after validation. It extends C to handle strong winners above normal cap without converting Safety hard cap into a target. |

Decision criteria summary:

| Criterion | Best fit |
| --- | --- |
| Momentum-swing philosophy | C/E |
| PIT correctness | C/E |
| Winner amplification ability | E |
| Diversification preservation | C/E if bounded; A if conservative |
| Concentration control | C/E with explicit region; A conservative |
| NEW opportunity preservation | C |
| Cash efficiency | C/E |
| Lot/discrete compatibility | C/E if PC-owned |
| Architecture clarity | C |
| Regression risk | C lower than E; B/D higher |
| Overfit risk | C lower; E requires validation |
| Implementation complexity | A lowest, C moderate, E higher |

## 94320_SEMANTIC_WALKTHROUGH

Early 94320: below normal cap, strong ADD evidence, competing BUY_NEW.

Under the proposed contract, PC would form lot-sized BUY_ADD and BUY_NEW marginal units. 94320's Expected Edge `IMPROVING`, Incremental Investment Value `POSITIVE`, Opportunity Cost `PASS`, rank 1, no-loss averaging, and current headroom would allow it to compete directly against BUY_NEW. If it outranks the NEW units, Runtime Planning receives 94320 earlier in the canonical order, reducing accidental cash starvation. If a NEW unit has stronger marginal value, NEW still ranks first.

Later 94320: passively above normal Strategy target, strong PIT ADD evidence.

PC would first classify 94320 as above the normal region. Baseline retention remains valid. Further ADD is considered only if a validated winner-amplification region authority exists and all PIT evidence passes. Without that authority, no ADD is allowed even if the current score/rank are strong. With authority, the proposed lot must still remain below Safety hard cap and beat NEW/Cash on Opportunity Cost.

Weakening 94320: Expected Edge weakening.

No ADD. Existing winner status and prior fills do not override weakening. The position may remain held if HOLD-worthy, but ADD-worthiness is separate from HOLD-worthiness.

## ARCHITECTURE_RISKS

1. Concentration risk: mitigate with explicit normal/winner/Safety region separation, per-item headroom evidence, and Safety hard-cap preservation.
2. Winner reversal / momentum crash: require current momentum/trend/Expected Edge pass and block ADD on deterioration.
3. Regime transition risk: Market Context must be an input; materially worse regimes can block or reduce winner amplification.
4. Starving diversification: no unconditional ADD priority; NEW remains in the same marginal competition.
5. Excessive ADD feedback loop: require ADD spacing/history, no-loss averaging, and repeated Opportunity Cost proof.
6. Duplicate authority: PC owns priority; PS and Runtime consume only. Submit validates, not resizes.
7. Cash starvation moving from ADD to NEW: canonical order is opportunity-driven, not side-driven; NEW can outrank weak ADD.
8. Lot-order instability: rank executable lot units, not abstract fractional weights; re-evaluate after lot-aware skips.
9. Overfitting to 94320: no numeric thresholds chosen from 94320; validation must include multiple symbols/windows.
10. Implementation complexity: stage C before E and require focused contract tests before runtime integration.

## IMPLEMENTATION_SCOPE_IF_LATER_AUTHORIZED

Design only. If later authorized, narrow modification surfaces would likely be:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: produce `MARGINAL_CAPITAL_VALUE_AUTHORITY`, canonical priority index, and winner-headroom evidence.
- `src/ai_fund_lab_v2/strategy/position_sizing.py`: consume any PC winner-headroom/discrete authority without inventing priority.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py` and/or `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`: preserve canonical PC order through pending and cash-feasible batch construction.
- Focused tests for PC order, PS quantity consumption, Runtime order preservation, Safety cap separation, lot edge cases, and B0/B1 94320-style controls.

No files above were modified in B2.

## Validation Design Required Before Implementation

Validation must be specified before implementation:

- Use only PIT inputs and pre-register classification rules.
- Validate funnel changes: PM ADD -> positive increment -> PS quantity -> Pending -> Fill.
- Validate NEW preservation: strong NEW should not be starved by weak ADD.
- Validate ADD preservation: strong ADD should not be accidentally starved by arbitrary NEW order.
- Validate cap behavior: normal cap, winner region, and Safety hard cap remain distinct.
- Validate lot behavior with 100-share units and residual reallocation.
- Validate no future outcome labels are used for thresholds.
- Run on user-operated Historical evidence only after contract and tests are ready.

## Final Design Questions

### 1. Should a sufficiently strong BUY_ADD receive priority over a merely comparable BUY_NEW?

`CONDITIONAL`.

Yes when the BUY_ADD has stronger PIT marginal-capital value after lifecycle evidence, Expected Edge, Incremental Investment Value, Opportunity Cost, Market Context, concentration, lot, and Safety checks. No if it is only an ADD by label.

### 2. Should BUY_ADD always receive priority over BUY_NEW?

`NO`.

### 3. Should passive drift above the normal Strategy target automatically prohibit any future ADD regardless of current PIT winner strength?

`CONDITIONAL`.

Under current architecture without winner-headroom authority, it should prohibit further ADD while retaining baseline. In the recommended staged design, future ADD above normal target may be considered only through explicit winner-amplification region authority and Safety-preserving marginal-capital competition.

### 4. Should the Safety hard cap be used as the winner target?

`NO`.

### 5. Which alternative or staged combination should proceed to validation design?

Alternative C should proceed first, staged toward Alternative E. Do not implement it in B2.
