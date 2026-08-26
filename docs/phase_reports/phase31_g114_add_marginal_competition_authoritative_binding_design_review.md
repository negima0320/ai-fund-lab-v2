# Phase31-G114 — ADD Marginal Competition Authoritative Binding Design Review

## Judgment

PRIMARY_JUDGMENT = G114_ADD_MARGINAL_BINDING_DESIGN_READY_FOR_IMPLEMENTATION

G114 is READ-ONLY. No implementation, config change, run mutation, fresh-run, resume, replay, or Historical execution was performed.

The recommended binding is a staged authoritative binding of G113's PC-owned marginal ADD competition, with sequential one-increment authorization. It should bind only Portfolio Construction ADD incremental allocation and should not change PM ADD intent, normal BUY, SELL/REDUCE/EXIT, Safety, PS quantity ownership, Runtime priority, Submit, or Execution.

## Source Basis

Reviewed required sources:

- `docs/phase_reports/phase31_g112_repeated_add_marginal_capital_competition_contract_audit.md`
- `docs/phase_reports/phase31_g113_add_marginal_capital_competition_shadow_implementation.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Key SoT constraints:

- PC owns target portfolio, capital competition, and canonical deployment set.
- PS owns discrete executable quantity only.
- Runtime maps already-bound PS output and must not redecide capital priority.
- Cash is a legitimate alternative; no forced full deployment.
- HOLD-worthy and ADD-worthy are distinct.
- ADD requires incremental continuation quality, downside risk, opportunity cost, existing exposure, lot feasibility, and no-loss-averaging evidence.
- Safety and hard caps are terminal guardrails.

## Core Decision

AUTHORITATIVE_MARGINAL_CAPITAL_DECISION_DEFINED = YES

Authoritative binding must answer:

```text
For the next executable ADD increment, should Portfolio Construction commit
this marginal capital here versus other ADD increments, eligible NEW_BUY,
Cash, and residual optionality?
```

It must not answer the weaker question:

```text
Is this campaign generally good enough to ADD?
```

WINNER_RETENTION_PRESERVED_BY_DESIGN = YES

BLANKET_ADD_SUPPRESSION_INTRODUCED = NO

## Class Semantics

| CLASS | AUTHORITATIVE_STATUS | CAPITAL_ALLOWED | REDUCED_PARTICIPATION_ALLOWED | CONTINUE_NEXT_INCREMENT | TERMINAL | RATIONALE |
|---|---|---|---|---|---|---|
| ADD_MARGINAL_PREFERRED | PASS_FOR_NEXT_INCREMENT | YES, exactly one executable increment | Not needed for that increment | YES, after recomputation | NO | This increment is the best current marginal use within the same-date frontier. |
| COMPARABLE_MARGINAL | CONDITIONAL_RESIDUAL_PARTICIPATION | YES only under residual/shoulder participation after strictly preferred alternatives and Cash semantics are respected | YES | YES, but every next lot must recompute | NO | Comparable means not enough evidence for full block deployment, but enough for controlled reduced participation if PC proves no superior use is displaced. |
| CASH_MARGINAL_PREFERRED | CASH_WINS | NO | NO | NO for this ADD path unless new upstream evidence appears on a later date | YES for current date/increment | Cash/optionality is preferred for this marginal capital. |
| SAFETY_TERMINAL | TERMINAL_FAIL_CLOSED | NO | NO | NO | YES | Safety/cap terminality is not Strategy preference and cannot be overridden by marginal score. |
| LOT_INFEASIBLE | TERMINAL_FOR_INCREMENT | NO for this increment | NO, unless a later PC residual/lot reconsideration produces a different executable increment | NO for this increment | YES row-scoped | Non-executable capital must not become synthetic quantity. Residual may go to Cash or other valid increments. |
| INSUFFICIENT_EVIDENCE | FAIL_CLOSED_TO_CASH_OR_RESIDUAL | NO | NO | NO for this increment | YES for current evidence | Missing marginal proof must not silently become PASS. Existing HOLD is preserved; only the new ADD increment is blocked. |

COMPARABLE_MARGINAL_AUTHORITATIVE_SEMANTIC =

```text
COMPARABLE_MARGINAL is non-terminal and may receive only controlled residual /
shoulder participation. It is not full requested-block authorization. It must
remain in the frontier after each prior increment is applied hypothetically,
and it may receive a next executable lot only when PC proves that no strictly
preferred security increment or Cash/optionality claim is displaced.
```

INSUFFICIENT_EVIDENCE_AUTHORITATIVE_SEMANTIC =

```text
FAIL_CLOSED_TO_CASH_OR_RESIDUAL for the ADD increment only.
The existing position remains governed by HOLD/REDUCE/EXIT authorities.
```

This does not become a Winner-killing rule because it blocks only additional marginal capital. It does not force exit, reduce, or remove existing holdings.

## Sequential Binding

PREFERRED_AUTHORIZES_SINGLE_INCREMENT_ONLY = YES

AUTHORITATIVE_FRONTIER_RECOMPUTED_AFTER_EACH_INCREMENT = YES

Required authoritative loop:

```text
build frontier
-> select one best marginal capital use
-> allocate one executable increment
-> update hypothetical cash, quantity, weight, headroom, residual budget
-> rebuild/re-evaluate frontier
-> continue or terminate
```

Deterministic termination conditions:

- no remaining executable lot can be funded;
- Cash/optionality wins the current marginal frontier;
- all remaining security increments are terminal;
- evidence is insufficient for all remaining increments;
- Safety/cap/headroom terminality is reached;
- available incremental budget is exhausted;
- PC residual/shoulder rule declines remaining comparable increments.

## Frontier Membership

AUTHORITATIVE_FRONTIER_MEMBERS =

```text
1. ADD increments:
   PM ADD intent PASS, ADD investment evidence PASS, no-loss/campaign/expected
   edge/opportunity-cost requirements PASS, executable lot context available,
   and not Safety/cap terminal.

2. NEW_BUY increments/securities:
   final eligible PC NEW_BUY frontier represented at a granularity compatible
   with ADD increments.

3. Cash:
   first-class capital destination from canonical Cash evidence and budget
   envelope.

4. Residual optionality:
   explicit future-opportunity-capacity state for unused budget, represented
   without double-counting Cash.
```

Incumbent HOLD capital is not an active marginal competitor. It is existing allocated state. It must not be implicitly liquidated to fund a marginal BUY/ADD unless PM/SELL/REDUCE authorities produce such capacity.

## NEW_BUY Granularity

NEW_BUY_MARGINAL_GRANULARITY_COMPATIBLE = PARTIAL

G113 makes ADD lot increments explicit, while NEW_BUY is still primarily represented as selected security allocation/block evidence. Authoritative binding should normalize NEW_BUY into comparable executable increments before PC uses G113 as a binding allocation authority.

Required normalization contract:

- NEW_BUY must expose first executable lot and any additional executable increments using the same lot context fields as ADD;
- PC may still preserve existing NEW_BUY priority/order evidence;
- no new score, threshold, or performance-fitted tie-breaker may be introduced;
- PS remains final quantity owner after PC selects the authorized increment set.

This is the only reason the recommendation is staged rather than direct.

## ADD vs ADD Fairness

AUTHORITATIVE_ADD_VS_ADD_ORDER_INDEPENDENT = YES

TIE_BREAK_CONTRACT =

```text
existing multi-allocation priority sort key,
then competitor type,
then symbol,
with explicit reason lineage and no performance-derived tie breaker.
```

The deterministic tie-break may be used only after canonical priority evidence cannot distinguish candidates. It must not create first-campaign, list-order, or symbol-iteration advantage.

## Cash and Residual Optionality

CASH_FIRST_CLASS_PRESERVED = YES

CASH_CAN_WIN_MARGINAL_FRONTIER = YES

`CASH_PREFERRED_PARTICIPATION_VALID` must remain distinct from `ADD_MARGINAL_CAPITAL_BEATS_CASH`.

`ADD_MARGINAL_PREFERRED` may beat Cash for exactly the next executable increment. `COMPARABLE_MARGINAL` does not automatically beat Cash; it may participate only under residual/shoulder participation.

RESIDUAL_OPTIONALITY_SEMANTIC_DEFINED = YES

Residual optionality is not a second Cash balance. It is a PC semantic for preserving unused capital capacity for later opportunities when same-date marginal security evidence does not justify deployment. It should materialize as Cash allocation/unallocated residual in the deployment set, without double-counting.

## Position Size Awareness

POSITION_SIZE_AWARENESS_SUFFICIENT_FOR_BINDING = PARTIAL

G113 carries the minimum required state:

- pre/post quantity
- pre/post weight
- remaining strategy headroom
- remaining safety headroom
- lot size / one-lot weight

Missing contract before binding:

```text
NEW_BUY must be represented at compatible executable-increment granularity,
and COMPARABLE_MARGINAL residual/shoulder participation must define how many
comparable increments may be admitted before Cash/optionality wins.
```

No arbitrary concentration penalty, decay coefficient, numeric threshold, or tuned weight should be added.

## Risk Pacing / Market Quality

MARKET_QUALITY_REUSED_NOT_REIMPLEMENTED = YES

RISK_PACING_REUSED_NOT_REIMPLEMENTED = YES

Market Quality remains capital pacing context, and Risk Pacing remains deployment intensity authority via Portfolio Policy / budget envelope. G114 does not create new Market Quality or Risk Pacing thresholds.

## Safety Boundary

SAFETY_TERMINAL = YES

SAFETY_CAN_BE_OVERRIDDEN_BY_MARGINAL_SCORE = NO

Hard cap, invalid authority, and genuinely lot-infeasible increments remain terminal/fail-closed at their current boundaries.

## PC / PS / Runtime / Submit Binding

PC_REMAINS_CAPITAL_COMPETITION_OWNER = YES

PS_REMAINS_DISCRETE_QUANTITY_OWNER = YES

Expected binding fields from PC to PS:

```text
canonical_add_marginal_capital_competition_hash
authorized_marginal_increment_ids[]
symbol
competitor_type = ADD
authorized_increment_weight
pre_increment_quantity
post_increment_quantity
pre_increment_weight
post_increment_weight
one_lot_weight
executable_lot_size
remaining_headroom_after_increment
classification
classification_reason
cash_or_residual_destination_for_rejected_increment
future_information_used = false
historical_outcome_used = false
```

PS must consume this as PC capital authority and convert to final executable quantity. PS must not re-run opportunity competition.

RUNTIME_MARGINAL_AUTHORITY = NO

SUBMIT_MARGINAL_AUTHORITY = NO

Runtime consumes PS output. Submit remains feasibility/fail-closed authority only.

## Actual Shadow Evidence Consistency

G113 actual shadow distribution:

| Class | Count |
|---|---:|
| SHADOW_INCREMENT_COUNT | 205 |
| ADD_MARGINAL_PREFERRED | 13 |
| COMPARABLE_MARGINAL | 125 |
| CASH_MARGINAL_PREFERRED | 0 |
| INSUFFICIENT_EVIDENCE | 67 |

76470:

| Date | Shadow increments | Class |
|---|---:|---|
| 2022-12-06 | 13 | COMPARABLE_MARGINAL |
| 2022-12-21 | 10 | COMPARABLE_MARGINAL |
| 2023-01-04 | 9 | COMPARABLE_MARGINAL |

Other available symbols:

- 94320: COMPARABLE_MARGINAL and INSUFFICIENT_EVIDENCE
- 94340: COMPARABLE_MARGINAL
- 45940: INSUFFICIENT_EVIDENCE
- 99840: LOT_INFEASIBLE in `strategy_eod_shadow`

ACTUAL_SHADOW_SEMANTIC_CONSISTENCY = YES

The proposed policy interprets these states consistently with decision-time evidence. It does not call later losers bad or later winners good.

## Winner Protection

STRONG_WINNER_CAN_RECEIVE_MULTIPLE_ADDS = YES

Design condition:

```text
Multiple consecutive ADD increments remain allowed when each recomputed next
increment remains ADD_MARGINAL_PREFERRED, executable, within cap/headroom,
and superior or sufficiently preferred against Cash and the full frontier.
```

This preserves strong Winner continuation without allowing a prior ADD to authorize the rest of the block.

## Stop Conditions

MARGINAL_STOP_CONDITIONS_DEFINED = YES

Stop repeated ADD when:

- ADD no longer beats the frontier;
- Cash or residual optionality wins;
- evidence becomes INSUFFICIENT_EVIDENCE;
- Safety/cap/headroom closes;
- lot feasibility fails for the current increment;
- COMPARABLE_MARGINAL reaches the residual/shoulder boundary;
- remaining budget cannot fund the next executable lot;
- a superior NEW_BUY or other ADD increment consumes the marginal budget.

## Authoritative Policy Options

| Option | Description | Philosophy alignment | Winner retention | Cash preservation | Complexity | Fail-closed | Risk |
|---|---|---|---|---|---|---|---|
| A | Only ADD_MARGINAL_PREFERRED gets capital; all COMPARABLE goes Cash | Medium | Weak for normal reduced ADD | Strong | Low | Strong | Over-suppresses valid Winner continuation |
| B | ADD_MARGINAL_PREFERRED gets one increment; COMPARABLE gets limited residual/shoulder participation; others Cash/fail-closed | High | Strong if recomputed | Strong | Medium | Strong | Needs precise shoulder/residual contract |
| C | Ranked frontier admits COMPARABLE only when no strictly superior security/Cash alternative remains and residual budget exists | High | Medium/Strong | Strong | Medium/High | Strong | Needs NEW_BUY increment normalization |
| D | Keep G113 shadow-only, no binding | Low | Existing behavior preserved | Weak against G112 defect | Low | Weak | Reproduces repeated block ADD defect |

RECOMMENDED_AUTHORITATIVE_POLICY = OPTION_B_WITH_OPTION_C_FRONTIER_GUARD

RECOMMENDATION_BASIS = architecture/SoT/decision-time evidence only

Recommended contract:

```text
ADD_MARGINAL_PREFERRED:
  authorize exactly one increment, then recompute.

COMPARABLE_MARGINAL:
  allow reduced residual/shoulder participation only after strict preferred
  claims and Cash semantics are resolved; never authorize full requested block.

CASH_MARGINAL_PREFERRED / INSUFFICIENT / TERMINAL:
  no ADD capital for that increment; return capital to Cash/residual or other
  valid frontier member.
```

## Blast Radius

BINDING_BLAST_RADIUS_NARROW = YES

Expected changed surface:

```text
Portfolio Construction ADD incremental allocation only
```

Unchanged:

- G90
- G97
- G99
- G102
- G104
- G110
- PM ADD intent
- normal BUY producer
- SELL
- REDUCE
- EXIT
- Safety
- campaign lifecycle
- PS ownership
- Runtime priority
- Submit
- Execution

## Rollout Strategy

ROLLOUT_STRATEGY = STAGED_PARTIAL_BINDING

Rationale:

COMPARABLE_MARGINAL and INSUFFICIENT_EVIDENCE dominate the G113 population. Direct binding would be too blunt unless NEW_BUY increment granularity and COMPARABLE residual/shoulder semantics are pinned down in focused acceptance first.

Recommended stages:

1. Bind terminal classes first: SAFETY_TERMINAL, LOT_INFEASIBLE, INSUFFICIENT_EVIDENCE -> no ADD increment.
2. Bind ADD_MARGINAL_PREFERRED -> one increment only with recomputation.
3. Bind COMPARABLE_MARGINAL residual/shoulder participation after focused acceptance proves Winner continuation is preserved.

READY_FOR_AUTHORITATIVE_BINDING_IMPLEMENTATION = YES

This means ready for a narrow staged implementation, not ready for long Historical.

## Mandatory Post-Binding Gates

SHORT_ACTUAL_PATH_GATE_DEFINED = YES

Before long Historical:

1. Focused deterministic unit tests:
   - each class semantic
   - one-increment-only authorization
   - recomputation after hypothetical increment
   - ADD-vs-ADD order independence
   - Cash wins
   - Safety terminal

2. Producer-equivalent actual artifact reconstruction:
   - 2022-10-12
   - 2022-11-01
   - 2022-12-06
   - 2022-12-21
   - 2023-01-04

3. Short actual-path Runtime gate:
   - PC publishes authoritative increments
   - PS consumes only PC authorized increments
   - Runtime emits only PS-bound ADD
   - Submit/Execution unchanged

4. Normal BUY unaffected proof.

5. Strong Winner multiple ADD survives when every next increment remains preferred.

6. Cash can win and produce no ADD.

7. Safety terminal cannot be overridden.

8. G93 residual dead-end does not return.

9. G110 campaign lifecycle unchanged.

Long Historical must not be recommended until these pass.

## Validation Anchors

| Date | Why this is a binding checkpoint |
|---|---|
| 2022-10-12 | Multiple ADD evidence in G113 actual/shadow path; validates ADD-vs-ADD and NEW_BUY comparability. |
| 2022-11-01 | ADD competition around 94320/99840 in shadow evidence; validates eligible ADD population and insufficient/lot semantics. |
| 2022-12-06 | First primary 76470 repeated ADD anchor; validates COMPARABLE_MARGINAL reduced/residual behavior. |
| 2022-12-21 | Later 76470 repeated ADD with larger incumbent state; validates recomputation after prior ADDs. |
| 2023-01-04 | 76470 high current-weight ADD; validates headroom, residual budget, and no block authorization. |

No return expectation is attached to these anchors.

## Required Judgments

AUTHORITATIVE_MARGINAL_CAPITAL_DECISION_DEFINED = YES

COMPARABLE_MARGINAL_AUTHORITATIVE_SEMANTIC = CONDITIONAL_RESIDUAL_SHOULDER_PARTICIPATION_AFTER_STRICT_FRONTIER_AND_CASH_RESOLUTION

INSUFFICIENT_EVIDENCE_AUTHORITATIVE_SEMANTIC = FAIL_CLOSED_TO_CASH_OR_RESIDUAL_FOR_ADD_INCREMENT_ONLY

PREFERRED_AUTHORIZES_SINGLE_INCREMENT_ONLY = YES

AUTHORITATIVE_FRONTIER_RECOMPUTED_AFTER_EACH_INCREMENT = YES

NEW_BUY_MARGINAL_GRANULARITY_COMPATIBLE = PARTIAL

AUTHORITATIVE_ADD_VS_ADD_ORDER_INDEPENDENT = YES

CASH_FIRST_CLASS_PRESERVED = YES

CASH_CAN_WIN_MARGINAL_FRONTIER = YES

RESIDUAL_OPTIONALITY_SEMANTIC_DEFINED = YES

POSITION_SIZE_AWARENESS_SUFFICIENT_FOR_BINDING = PARTIAL

STRONG_WINNER_CAN_RECEIVE_MULTIPLE_ADDS = YES

MARGINAL_STOP_CONDITIONS_DEFINED = YES

RECOMMENDED_AUTHORITATIVE_POLICY = OPTION_B_WITH_OPTION_C_FRONTIER_GUARD

BINDING_BLAST_RADIUS_NARROW = YES

ROLLOUT_STRATEGY = STAGED_PARTIAL_BINDING

SHORT_ACTUAL_PATH_GATE_DEFINED = YES

FUTURE_INFORMATION_USED = NO

HISTORICAL_OUTCOME_USED = NO

READY_FOR_AUTHORITATIVE_BINDING_IMPLEMENTATION = YES

## Final Decision

G114_ADD_MARGINAL_BINDING_DESIGN_READY_FOR_IMPLEMENTATION

