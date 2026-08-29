# Phase32-AR - Shadow Common Marginal Capital Value / ADD Next-Lot Architecture Design

## Executive Summary

Scope: shadow-only architecture design for:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

This design responds to the locked AQ finding:

```text
PM ADD intent = 340
ADD fill = 11
intent-to-fill = 3.24%
first major dropoff = PM ADD intent -> positive accepted incremental target weight / target gap
```

AR defines a non-authoritative Portfolio Construction-owned shadow artifact:

```text
canonical_marginal_capital_frontier.v1
```

Its job is to compare the next executable unit of scarce capital across:

```text
NEW first executable lot
REENTRY first executable lot
ADD next executable lot #1
ADD next executable lot #2
ADD next executable lot #N
Cash / optionality
```

The design explicitly does not create a fixed 200/300-share ADD rule, fixed ADD multiplier, fixed target position count, fixed rank-to-weight rule, or historical-return optimized threshold. It creates the shadow structure needed to ask:

```text
Is the next executable unit of capital better deployed here than in the strongest available alternative?
```

Primary design judgment:

```text
PHASE32_AR_SHADOW_COMMON_MARGINAL_CAPITAL_FRONTIER_DESIGN_COMPLETE_READY_FOR_NON_AUTHORITATIVE_IMPLEMENTATION
```

No production code, config, threshold, schema, model, target weight, order, fill, Cash behavior, Risk Pacing, MCC authority, Position Sizing behavior, Runtime behavior, Safety behavior, fresh run, resume, replay, backtest, or run stop was changed or executed.

## Inherited Findings

Locked Phase32-AQ findings:

| Finding | Value |
| --- | --- |
| PM ADD intent | 340 |
| ADD fills | 11 |
| ADD intent-to-fill rate | 3.24% |
| ADD rows with `target_minus_current = 0` | 97.06% |
| ADD rows with `accepted_incremental_weight = 0` | 96.47% |
| First major dropoff | PM ADD intent -> positive accepted incremental target weight / target gap |
| Root diagnosis | `G_MULTI_STAGE_COMBINATION` |
| Minimal architecture boundary | `PORTFOLIO_CONSTRUCTION_OWNED_CAPITAL_VALUE_AUTHORITY_AND_TARGET_GAP_AUTHORITY` |
| Shadow readiness | `READY_FOR_SHADOW_SPEC` |

AQ secondary causes:

- `CROSS_TYPE_VALUE_SEMANTIC_GAP`
- `CONVICTION_TO_TARGET_COMPRESSION`
- `NEXT_LOT_COMPETITION_MISSING`
- `ADD_VALUE_RESOLUTION_LOSS`

Locked keep boundaries:

| Layer | AR stance |
| --- | --- |
| PM | Keep. PM ADD remains directional existing-position intent. |
| Position Sizing | Keep. No shadow result flows into production PS. |
| Runtime | Keep. Runtime must not recompute capital priority. |
| Safety | Keep. Safety remains hard authority. |
| REDUCE | Keep. No redesign of defensive quantity behavior. |
| EXIT | Keep. No redesign of exit behavior. |

Inherited AO/AP/AN/AM principles:

- Multi-lot ADD is architecturally valid only when each lot is independently justified.
- Current ADD behavior is conservative transitional design, not a narrow PS arithmetic defect.
- Share count alone is misleading; price, target weight, lot size, and capital availability matter.
- BUY_NEW early failures are not cleanly separable from winners at T0 using current PIT fields.
- Position count should emerge from opportunity quality, capital budget, concentration, Cash optionality, lot feasibility, and Safety.

## Design Principles

### Position Count Is An Output

Position count must not be a target.

Expected behavior:

| Opportunity set | Capital allocation implication |
| --- | --- |
| Few superior opportunities | fewer / larger positions may emerge |
| Many similarly strong opportunities | broader diversification may emerge |
| Weak opportunity set | Cash may win |
| Strong incumbent winner | additional ADD lots may emerge only if each next lot wins |

No fixed 5/8/10 position rule is introduced.

### Starter / Confirmation / Scale

Initial uncertainty may justify a small starter allocation. Later PIT-safe evidence can confirm whether a campaign deserves more capital.

Contract:

| Stage | Meaning |
| --- | --- |
| Starter | NEW / REENTRY first lot may be small while uncertainty is high. |
| Confirmation | PM continuation, trend/momentum, quality, market context, and campaign evidence confirm or weaken the position. |
| Scale | Every additional ADD lot competes independently against NEW, REENTRY, other ADD lots, and Cash. |

No fixed holding-day confirmation rule is introduced. AM's T+2 observation remains descriptive research evidence only.

### PM ADD Is Evidence, Not Capital Authority

PM ADD means:

- existing-position continuation is favorable enough for ADD consideration;
- adding is permissible from PM's perspective;
- the position is not automatically broken.

PM ADD does not mean:

- target weight must increase;
- one or more lots must be bought;
- ADD beats NEW / REENTRY / Cash;
- the position should receive a fixed number of shares.

### Desirability And Feasibility Are Separate

The shadow artifact must preserve:

```text
marginal desirability != executable feasibility
```

Examples that must remain distinguishable:

| State | Meaning |
| --- | --- |
| High desirability + cap blocked | Economically attractive, but concentration prevents execution. |
| High desirability + insufficient Cash | Attractive, but unavailable buying power blocks execution. |
| Low desirability + lot feasible | Executable, but not worth scarce capital. |
| Cash wins | Securities may be feasible, but optionality is more valuable. |

No artifact may collapse infeasibility into “low value.”

## Artifact Schema

Canonical shadow artifact:

```text
canonical_marginal_capital_frontier.v1
```

Status:

```text
SHADOW
NON_AUTHORITATIVE
PIT_SAFE
DETERMINISTIC
EXPLAINABLE
REPLAYABLE
MODE_COMPATIBLE
```

Artifact-level fields:

| Field | Purpose |
| --- | --- |
| `schema_name` | fixed value `canonical_marginal_capital_frontier` |
| `schema_version` | fixed value `v1` |
| `artifact_mode` | `SHADOW_NON_AUTHORITATIVE` |
| `business_date` | decision date |
| `session` | e.g. `morning` |
| `run_id` | producing run identity where applicable |
| `as_of` | decision-time timestamp / feature boundary |
| `portfolio_state_ref` | reference to current portfolio snapshot used |
| `candidate_artifact_refs` | Candidate / Opportunity / Ranking evidence refs |
| `pm_artifact_refs` | PM decision refs |
| `pc_artifact_refs` | Portfolio Construction evidence refs |
| `market_artifact_refs` | market quality / context refs |
| `risk_pacing_refs` | Risk Pacing / deployment posture refs |
| `safety_refs` | Safety evidence refs |
| `cash_state_ref` | buying power / Cash evidence ref |
| `frontier_candidates` | list of marginal candidate objects |
| `frontier_result` | shadow comparison result |
| `shadow_target_projection` | non-authoritative target-gap projection |
| `released_capital_observation` | REDUCE/EXIT released-capital frontier attribution |
| `metrics` | shadow characterization metrics |
| `determinism_key` | stable input identity key |
| `producer_version` | shadow producer version |
| `non_authoritative_contract` | hard assertion that artifact cannot feed production orders |

Hard non-authoritative assertion:

```text
canonical_marginal_capital_frontier.v1 MUST NOT be consumed by Position Sizing, Runtime Planning, Pending, Order, Execution, Submit, or Safety as production authority.
```

## Marginal Candidate Object

One object represents one executable capital increment.

Required semantic types:

```text
NEW_FIRST_LOT
REENTRY_FIRST_LOT
ADD_NEXT_LOT
CASH_OPTIONALITY
```

Required identity fields:

| Field | Meaning |
| --- | --- |
| `business_date` | decision date |
| `symbol` | security symbol, nullable only for Cash |
| `position_campaign_id` | campaign id where applicable |
| `semantic_type` | one of the required semantic types |
| `candidate_id` | deterministic stable candidate id |
| `increment_index` | `1` for first lot; `2`, `3`, ... for repeated ADD lots; `0` for Cash |
| `pre_quantity` | quantity before this marginal increment |
| `post_quantity` | hypothetical quantity after this increment |
| `increment_quantity` | executable lot quantity represented by this object |
| `pre_weight` | portfolio weight before this increment |
| `post_weight` | hypothetical post-lot weight |
| `increment_weight` | marginal weight consumed |
| `reference_price` | PIT-safe reference price |
| `increment_notional` | reference price x increment quantity |
| `source_pm_decision_id` | PM decision id where applicable |
| `source_candidate_id` | Candidate / Opportunity / Ranking id where applicable |
| `source_pc_evidence_ids` | upstream PC evidence refs where applicable |

Required semantic sections:

| Section | Purpose |
| --- | --- |
| `desirability` | structured economic attractiveness evidence |
| `risk_modifiers` | non-hard risk adjustments / context |
| `feasibility` | executable feasibility checks |
| `constraints` | hard limits and block states |
| `observability` | missing/stale/evidence quality flags |
| `lineage` | source artifact ids / hashes / producer refs |
| `shadow_disposition` | candidate result in shadow frontier |

Stable candidate id:

```text
sha256(
  schema_version,
  business_date,
  session,
  semantic_type,
  symbol_or_CASH,
  position_campaign_id_or_NONE,
  increment_index,
  pre_quantity,
  post_quantity,
  reference_price,
  source_identity_refs
)
```

Stable ordering:

1. `business_date`
2. `semantic_type` order: `ADD_NEXT_LOT`, `REENTRY_FIRST_LOT`, `NEW_FIRST_LOT`, `CASH_OPTIONALITY`
3. `symbol`
4. `position_campaign_id`
5. `increment_index`
6. `candidate_id`

The ordering is deterministic. It is not a priority rule.

## Evidence Taxonomy

Every field consumed by the shadow frontier must be classified.

| Category | Examples | Meaning |
| --- | --- | --- |
| `DESIRABILITY` | opportunity score/rank, BUY quality, entry quality, PM continuation, campaign strength, trend persistence, momentum persistence, incremental investment value, opportunity-cost evidence, Cash optionality | Evidence for economic attractiveness. |
| `RISK_MODIFIER` | market quality, downside evidence, current weight, post-lot weight, concentration pressure, deployment posture | Evidence that modifies attractiveness but may not hard-block alone. |
| `FEASIBILITY` | buying power, lot feasibility, reference price, trading unit, post-lot notional, current holdings | Evidence for whether the increment can execute. |
| `CONSTRAINT` | Safety hard block, single-name cap, forbidden averaging-down, Risk Pacing block, insufficient Cash hard block | Hard authority that can make a candidate infeasible or ineligible. |
| `OBSERVABILITY` | missing/stale identity, missing PIT evidence, schema mismatch, source artifact missing | Evidence quality and lineage state. |

Fail-open is forbidden. Missing required PIT evidence must produce:

```text
REVIEW_REQUIRED
```

or:

```text
INELIGIBLE_MISSING_REQUIRED_EVIDENCE
```

## Common Economic Meaning

All frontier candidates share this semantic:

```text
Decision-time attractiveness of deploying the next executable unit of scarce portfolio capital into this alternative, conditional on current portfolio state, current evidence, constraints, and strongest available alternatives.
```

This is not future realized return. It is not Paper PnL. It is not “the asset later became a winner.” It is a PIT-safe decision-time capital comparison.

The representation does not require a scalar score in v1. The recommended v1 representation is structured:

| Component | Meaning |
| --- | --- |
| `opportunity` | security opportunity strength where applicable |
| `quality` | BUY / entry / security quality where applicable |
| `continuation` | PM continuation and campaign evidence for existing positions |
| `recovery` | prior-exit recovery evidence for REENTRY |
| `incremental_value` | value of this specific increment, not whole symbol quality |
| `risk_adjustment` | current/post-lot risk and market context |
| `cash_opportunity_cost` | opportunity cost of spending Cash |
| `competition_context` | strongest alternatives on the same date |

Future scalarization may be considered only after shadow characterization and acceptance. AR does not define coefficients, weights, thresholds, or formulas.

## NEW First-Lot Semantics

`NEW_FIRST_LOT` represents the first executable lot of a not-currently-held opportunity.

Candidate existence requirements:

- valid same-date Candidate / Opportunity / Ranking evidence;
- BUY Quality / entry state evidence where available;
- PIT-safe reference price;
- trading unit / lot feasibility evidence;
- buying-power observability;
- Safety observability.

Desirability evidence may include:

- opportunity score/rank;
- BUY quality;
- entry quality;
- trend / momentum state;
- expected edge if available;
- market quality;
- risk pacing context.

Feasibility and constraints:

- lot feasible;
- sufficient Cash / buying power;
- single-name cap/headroom;
- Risk Pacing;
- Safety;
- no stale/missing candidate identity.

NEW must not receive automatic priority merely because it has first-lot semantics. It must compete on the same marginal frontier as ADD, REENTRY, and Cash.

## REENTRY First-Lot Semantics

`REENTRY_FIRST_LOT` represents the first executable lot of a symbol with prior exit history and current re-entry eligibility evidence.

Candidate existence requirements:

- prior exit context materialized;
- prior exit reason class and authority where applicable;
- cooldown / recovery / requalification evidence;
- valid current opportunity evidence;
- BUY quality / continuation / downside evidence;
- PIT-safe price and lot feasibility;
- Safety observability.

Desirability evidence may include:

- current opportunity score/rank;
- trend recovery;
- momentum recovery;
- prior exit reason class;
- recovery quality;
- continuation;
- buy quality;
- market context.

Feasibility and constraints:

- cooldown pass where required;
- recovery/requalification pass where required;
- Safety hard constraints;
- lot feasibility;
- sufficient Cash;
- cap/headroom;
- Risk Pacing.

AR preserves existing Phase32 REENTRY repairs and Safety. It does not weaken cooldown, recovery, or re-entry safety gates.

## ADD Next-Lot Semantics

`ADD_NEXT_LOT` represents one additional executable lot for an existing position.

Candidate existence requirements:

- valid existing position;
- stable `position_campaign_id`;
- PM state compatible with ADD consideration;
- current quantity and weight;
- post-lot quantity and weight;
- PIT-safe reference price;
- cap/headroom evidence;
- no forbidden averaging-down semantics;
- Cash / buying power observability;
- Safety observability.

Desirability evidence may include:

- PM ADD intent;
- PM continuation;
- campaign state;
- opportunity score/rank;
- BUY quality;
- trend persistence;
- momentum persistence;
- incremental investment value;
- opportunity-cost evidence;
- current/post-lot concentration context;
- market quality.

Critical contract:

```text
PM ADD is evidence.
Portfolio Construction Capital Value is the shadow comparison authority.
```

An ADD candidate can exist and still lose to NEW, REENTRY, another ADD, or Cash.

## Repeated ADD Next-Lot Design

ADD quantity must be represented internally as sequential marginal candidates, never as a single pre-decided block.

Example current state:

```text
current quantity = 100
trading unit = 100
```

Shadow candidate sequence:

| Candidate | Pre quantity | Post quantity | Meaning |
| --- | ---: | ---: | --- |
| ADD lot #1 | 100 | 200 | First additional executable lot. |
| ADD lot #2 | 200 | 300 | Evaluated only after hypothetical lot #1 acceptance. |
| ADD lot #3 | 300 | 400 | Evaluated only after hypothetical lot #2 acceptance. |

State recomputation after each shadow-accepted lot:

- hypothetical quantity;
- hypothetical notional;
- hypothetical weight;
- remaining Cash;
- remaining single-name headroom;
- concentration pressure;
- strongest competing alternatives;
- feasibility flags.

No future price movement is allowed. The same decision-time reference price is used unless an existing PIT-safe source provides a more precise same-date execution reference.

Stopping rule:

```text
Stop generating or accepting further ADD next-lot objects when the next lot loses the frontier, becomes infeasible, violates a constraint, exhausts budget/headroom, or reaches an explicit shadow generation cap documented as an engineering safety bound rather than investment policy.
```

AR does not define an investment maximum number of ADD lots.

## Diminishing Marginal Value

Diminishing marginal value is represented structurally, not by fixed penalty coefficients.

Potential mechanisms:

| Mechanism | Directional effect |
| --- | --- |
| increased post-lot weight | more concentration pressure |
| reduced remaining headroom | less capacity for further ADD |
| reduced Cash | higher opportunity cost / lower optionality |
| stronger competing NEW / REENTRY | higher opportunity cost of ADD |
| market/risk posture deterioration | reduced marginal attractiveness |
| Safety or cap pressure | hard feasibility/constraint block |

Each later ADD lot must be evaluated using the hypothetical post-state from earlier accepted lots. Therefore lot #2 can have lower relative value than lot #1, and lot #3 can lose even when lot #1 and #2 win.

No numeric penalty coefficient is selected in AR.

## Cash Semantics

`CASH_OPTIONALITY` is a first-class frontier candidate.

Cash is not:

```text
whatever is left after securities are chosen
```

Cash candidate evidence may include:

- weak opportunity set;
- near-comparable securities where deferral is preferred;
- Risk Pacing / market posture;
- downside / volatility context;
- future deployment flexibility;
- insufficient conviction spread between alternatives;
- capital preservation / operational liquidity.

Cash can win:

- before security selection;
- against NEW;
- against REENTRY;
- against ADD lot #1;
- against ADD lot #2 or later;
- after released capital from REDUCE/EXIT.

Cash candidate identity:

| Field | Value |
| --- | --- |
| `semantic_type` | `CASH_OPTIONALITY` |
| `symbol` | `null` or `CASH` |
| `increment_index` | `0` |
| `increment_quantity` | `0` |
| `increment_notional` | capital block under comparison, if defined; otherwise `null` with explicit explanation |

## Common Frontier

The shadow frontier is the same-date set of marginal candidates available for scarce capital comparison.

Frontier result fields:

| Field | Purpose |
| --- | --- |
| `frontier_id` | deterministic date/session frontier id |
| `candidate_count_total` | all candidates considered |
| `candidate_count_by_type` | NEW / REENTRY / ADD / Cash counts |
| `eligible_candidate_count` | candidates not blocked by hard constraints |
| `infeasible_candidate_count` | infeasible but value-preserved candidates |
| `winner_candidate_id` | shadow winner, nullable if no deployable winner |
| `runner_up_candidate_id` | strongest rejected alternative |
| `strongest_rejected_alternative_id` | explicit opportunity-cost reference |
| `cash_candidate_id` | Cash position in comparison |
| `cash_frontier_disposition` | won / lost / near-comparable / review |
| `comparison_representation` | structured partial-order / dominance / future scalar |
| `winner_reason_codes` | why winner beat runner-up |
| `loser_reason_codes` | why rejected alternatives lost |
| `constraint_reason_codes` | hard blocks |
| `review_reason_codes` | ambiguity / missing evidence |

Allowed v1 comparison representation:

```text
STRUCTURED_PARTIAL_ORDER
```

This avoids fake precision. If candidates cannot be strictly ordered from existing evidence, the shadow artifact should record:

```text
NEAR_COMPARABLE
AMBIGUOUS_REVIEW_REQUIRED
CASH_PREFERRED_BY_OPTIONALITY
SECURITY_PREFERRED_BY_DOMINANCE
```

## Shadow Target-Gap Projection

The frontier can emit a non-authoritative target-gap projection.

Fields:

| Field | Purpose |
| --- | --- |
| `shadow_target_quantity` | hypothetical final quantity after accepted shadow increments |
| `shadow_target_weight` | hypothetical final weight |
| `shadow_incremental_quantity` | total shadow ADD / NEW / REENTRY quantity increment |
| `shadow_incremental_weight` | total shadow weight increment |
| `accepted_shadow_candidate_ids` | ordered list of accepted candidates |
| `stopping_candidate_id` | first candidate that lost or blocked further ADD sequence |
| `stopping_reason` | why projection stopped |
| `production_target_weight_unchanged` | always true for AR implementation scope |
| `production_order_unchanged` | always true for AR implementation scope |

Example projection:

```text
current 100 shares
ADD lot #1 wins -> shadow quantity 200
ADD lot #2 wins -> shadow quantity 300
ADD lot #3 loses to NEW A -> stop
shadow ADD increment = 200 shares
production ADD increment = unchanged
```

## Released-Capital Recycling

The shadow artifact records what the frontier would prefer when REDUCE or EXIT releases capital.

It must not automatically assign released capital to ADD.

Released-capital fields:

| Field | Purpose |
| --- | --- |
| `released_capital_source` | `REDUCE`, `EXIT`, `NONE`, or mixed |
| `released_symbol` | source symbol |
| `released_position_campaign_id` | source campaign |
| `released_notional` | PIT-known released capital estimate where available |
| `frontier_destination` | ADD / NEW / REENTRY / Cash / mixed / review |
| `destination_candidate_id` | winning shadow candidate |
| `strongest_add_candidate_id` | best ADD candidate if not winner |
| `strongest_new_candidate_id` | best NEW candidate if not winner |
| `cash_disposition` | Cash result |
| `reason_released_capital_not_to_add` | explicit if ADD loses |

This directly addresses AP's finding that released capital currently recycles more to NEW than ADD. In AR, that becomes observable rather than assumed wrong.

## Concentration / Safety

Guardrails preserved:

- strategy single-name cap;
- Safety hard cap;
- Risk Pacing;
- buying power;
- Cash constraints;
- lot feasibility;
- no-loss-averaging rejection;
- downside and concentration warnings;
- stale/missing evidence review.

Post-lot checks:

| Check | Category |
| --- | --- |
| current weight | `RISK_MODIFIER` / context |
| post-lot weight | `RISK_MODIFIER` / possible `CONSTRAINT` if cap exceeded |
| concentration headroom | `FEASIBILITY` / `CONSTRAINT` |
| Safety block | `CONSTRAINT` |
| Risk Pacing block | `CONSTRAINT` where existing policy makes it hard; otherwise `RISK_MODIFIER` |
| insufficient Cash | `FEASIBILITY` / `CONSTRAINT` |
| lot infeasible | `FEASIBILITY` |
| no-loss-averaging violation | `CONSTRAINT` |

Stronger ADD architecture cannot silently bypass guardrails. High desirability plus a hard block remains blocked.

## Required Failure Modes

The shadow artifact must explicitly represent these outcomes:

| Failure mode | Shadow disposition |
| --- | --- |
| PM ADD without capital value | `ADD_INTENT_PRESENT_VALUE_NOT_DOMINANT` or `REVIEW_REQUIRED` |
| high desirability but cap blocked | `INFEASIBLE_CAP_BLOCKED` |
| high desirability but insufficient Cash | `INFEASIBLE_INSUFFICIENT_CASH` |
| lot infeasible | `INFEASIBLE_LOT` |
| Risk Pacing blocked | `INELIGIBLE_RISK_PACING_BLOCKED` |
| Safety blocked | `INELIGIBLE_SAFETY_BLOCKED` |
| concentration headroom exhausted | `INFEASIBLE_CONCENTRATION_HEADROOM_EXHAUSTED` |
| Cash wins | `REJECTED_CASH_PREFERRED` |
| ambiguous evidence | `REVIEW_REQUIRED_AMBIGUOUS_EVIDENCE` |
| stale/missing campaign identity | `REVIEW_REQUIRED_STALE_OR_MISSING_CAMPAIGN_IDENTITY` |
| missing required PIT evidence | `INELIGIBLE_MISSING_REQUIRED_PIT_EVIDENCE` |

Fail-open is forbidden.

## Metrics

Future shadow characterization metrics:

| Metric | Purpose |
| --- | --- |
| frontier candidate counts | breadth of comparison |
| candidate counts by semantic type | NEW / REENTRY / ADD / Cash mix |
| NEW / REENTRY / ADD / Cash win rates | destination of marginal capital |
| ADD next-lot candidate counts | ADD scaling opportunity surface |
| ADD lot #1 / #2 / #3+ consideration counts | repeated ADD depth |
| shadow multi-lot ADD count | how often multiple lots would be considered |
| shadow target-gap distribution | projected target gap resolution |
| production vs shadow allocation divergence | non-authoritative comparison to current behavior |
| Cash win rate | optionality behavior |
| concentration distribution | post-lot risk characterization |
| post-lot cap/headroom | guardrail pressure |
| one-lot portfolio count | starter-like behavior tracking |
| top3/top5 capital share | concentration outcome |
| capital released -> frontier destination | REDUCE/EXIT capital recycling |

Safety metrics:

| Metric | Purpose |
| --- | --- |
| cap blocked | concentration hard limits |
| Safety blocked | hard safety limits |
| Risk Pacing blocked | deployment posture constraints |
| insufficient Cash | buying power feasibility |
| lot infeasible | tradable-unit feasibility |
| concentration warning | non-hard concentration pressure |
| no-loss-averaging rejection | ADD semantic guardrail |
| stale/missing identity | lineage safety |
| REVIEW_REQUIRED count | ambiguity / incomplete evidence |

No performance thresholds are set in AR.

## Determinism

Deterministic contract:

```text
same business_date
same session
same portfolio state
same candidate evidence
same PM state
same market evidence
same risk/safety/cash evidence
same producer version
-> same shadow frontier
```

Requirements:

- stable candidate id generation;
- stable input artifact refs;
- stable candidate ordering;
- no wall-clock randomness;
- no external network lookup;
- no historical outcome input;
- no fill outcome input;
- no Paper PnL input;
- same behavior in Historical, Demo, and Production.

Mode parity:

```text
Historical, Demo, and Production must use only decision-time available inputs.
Historical-only fields are forbidden.
```

## Explainability

Every candidate must explain:

- why it exists;
- why it is desirable;
- why it is feasible or infeasible;
- why it won or lost;
- which guardrail limited it;
- which alternative beat it;
- whether Cash was preferred;
- whether evidence was missing, stale, or ambiguous.

Required lineage:

- source artifact ids;
- source artifact hashes where available;
- producer identity;
- PM decision id where applicable;
- candidate/ranking id where applicable;
- PC evidence id where applicable;
- portfolio snapshot identity;
- Safety / Risk Pacing / Cash refs.

Opaque final scores are forbidden in v1. If a future scalar is introduced, raw evidence lineage must remain visible.

## Example Walkthroughs

### Example A - Winner Gets Multiple Lots

Initial state:

```text
current shares = 100
trading unit = 100
```

Frontier round 1:

```text
ADD lot #1 > NEW A > Cash
shadow accept ADD lot #1
```

Recompute hypothetical state:

```text
shares = 200
weight increases
Cash decreases
headroom decreases
```

Frontier round 2:

```text
ADD lot #2 > NEW A > Cash
shadow accept ADD lot #2
```

Recompute hypothetical state:

```text
shares = 300
weight increases again
Cash decreases again
headroom decreases again
```

Frontier round 3:

```text
NEW A > ADD lot #3 > Cash
stop ADD sequence
shadow result = ADD +200, NEW +100
```

The quantities are explanatory only. They do not create production rules.

### Example B - Diversification Legitimately Wins

Initial state:

```text
Existing winner has PM ADD and strong continuation.
NEW A and NEW B are also high quality.
```

Frontier:

```text
NEW A ~= NEW B > ADD lot #1 > Cash
```

Concentration and headroom make NEW slightly preferable to adding more to the incumbent.

Shadow result:

```text
portfolio broadens
ADD loses explicitly
```

This is normal. ADD should not automatically win because it is an existing winner.

### Example C - Cash Wins

Initial state:

```text
ADD continuation exists.
NEW candidates exist.
Market / risk / Cash optionality is unfavorable for deployment.
```

Frontier:

```text
Cash > ADD lot #1 > NEW A > REENTRY A
```

Shadow result:

```text
no deployment
Cash wins before security allocation
```

This is normal. High-resolution marginal value must not mean forced full investment.

## Authority Ownership

| Responsibility | Owner | AR change |
| --- | --- | --- |
| Existing-position directional intent | PM | No production change |
| Candidate / opportunity evidence | Candidate / Opportunity / BUY Quality | No production change |
| Common marginal comparison | Portfolio Construction Capital Value | New shadow design only |
| Shadow target-gap projection | Portfolio Construction | New shadow design only |
| Production target weight | Current Portfolio Construction path | No production change in AR |
| Discrete quantity | Position Sizing | No change |
| Pending / orders / fills | Runtime / Submit / Execution | No change |
| Hard constraints | Safety | No change |
| Registry identity / eligibility | Artifact Registry | Future shadow registration only if implemented |

## SoT Update Plan

AR does not modify source-of-truth documents. If the shadow design is later accepted, permanent updates should be prepared for:

| Document | Future update |
| --- | --- |
| `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md` | Materialize `canonical_marginal_capital_frontier.v1`, candidate object, repeated ADD next-lot semantics, Cash candidate, determinism, and shadow status. |
| `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` | Add shadow capital-value boundary and clarify that production PS remains unchanged until explicit authority migration. |
| `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md` | Add future shadow artifact registry identity / runtime ineligibility contract if a shadow producer is implemented. |
| `docs/00_vision/investment_philosophy.md` | Update only if the position-count-as-output and starter/confirmation/scale principles are not already sufficiently explicit. |

## Implementation Roadmap

AR is a design task only. Recommended future monotonic tasks:

| Task | Scope |
| --- | --- |
| AR1 | Schema/design finalization for `canonical_marginal_capital_frontier.v1`. |
| AR2 | Shadow producer implementation with no production consumers. |
| AR3 | Deterministic/unit tests for candidate identity, repeated ADD lots, Cash candidate, feasibility/desirability separation, and fail-closed missing evidence. |
| AR4 | Historical artifact-only characterization; no production authority. |
| AR5 | Demo/Production mode parity validation using decision-time inputs only. |
| AR6 | Acceptance decision based on semantic correctness and guardrail preservation. |
| AR7 | Production authority migration only if separately approved. |

Migration sequence:

```text
shadow
-> characterized
-> accepted
-> authority migration
```

Do not immediately delete the current capital allocation path. If production migration is later accepted, classify each old/current authority as:

```text
KEEP
MIGRATE
DEPRECATE
REMOVE
```

Do not keep old authority as a permanent fallback after accepted migration unless a separate operational safety contract explicitly requires it.

## Risks / Open Questions

| Risk / question | AR stance |
| --- | --- |
| Structured partial order may leave many ties / reviews | Acceptable in shadow v1; do not fake precision. |
| Common scalar score may be tempting | Forbidden in AR unless later SoT mathematically justifies it. |
| ADD could over-concentrate if guardrails are weak | Preserve cap/headroom/Safety/Risk Pacing and post-lot checks. |
| Cash could be demoted to residual | Forbidden; Cash is first-class. |
| Historical winner outcomes could leak into design | Forbidden for parameter selection. Outcomes may be used later only for characterization. |
| Missing campaign identity | fail closed to review/ineligible. |
| Production consumers might accidentally read shadow output | Must enforce non-authoritative schema naming, pathing, registry status, and tests. |

## Explicit Non-Goals

AR does not solve or define:

- optimal ADD count;
- optimal ADD share quantity;
- optimal position count;
- optimal single-name weight;
- annualized return maximization;
- drawdown minimization;
- MA200 introduction;
- Entry redesign;
- Exit redesign;
- REENTRY redesign;
- REDUCE redesign;
- production ADD quantity changes;
- production target-weight changes;
- fixed ADD multiplier;
- historical-return tuned thresholds.

## Final Recommendation

Recommend exactly one next task:

```text
Phase32-AS - Shadow Marginal Capital Frontier Implementation
```

Scope for AS should be non-authoritative only:

- implement `canonical_marginal_capital_frontier.v1` shadow artifact;
- create one object per marginal increment;
- support NEW / REENTRY / ADD / Cash candidates;
- support repeated ADD next-lot generation;
- preserve desirability vs feasibility;
- preserve lineages and fail-closed review states;
- add deterministic tests;
- do not connect output to Position Sizing, Runtime Planning, Pending, Orders, Execution, or Safety authority.

## Final Judgments

```text
PHASE32_AR_DESIGN_SCOPE = SHADOW_ONLY

PHASE32_AR_COMMON_MARGINAL_VALUE_OBJECT_DEFINED = YES
PHASE32_AR_NEW_FIRST_LOT_DEFINED = YES
PHASE32_AR_REENTRY_FIRST_LOT_DEFINED = YES
PHASE32_AR_ADD_NEXT_LOT_DEFINED = YES
PHASE32_AR_REPEATED_ADD_NEXT_LOT_DEFINED = YES
PHASE32_AR_CASH_CANDIDATE_DEFINED = YES

PHASE32_AR_DESIRABILITY_FEASIBILITY_SEPARATED = YES
PHASE32_AR_DIMINISHING_MARGINAL_VALUE_DEFINED = YES
PHASE32_AR_COMMON_FRONTIER_DEFINED = YES
PHASE32_AR_SHADOW_TARGET_GAP_DEFINED = YES

PHASE32_AR_POSITION_COUNT_AS_OUTPUT_PRESERVED = YES
PHASE32_AR_STARTER_CONFIRMATION_SCALE_PRESERVED = YES

PHASE32_AR_REDuce_KEEP = YES
PHASE32_AR_REDUCE_KEEP = YES
PHASE32_AR_EXIT_KEEP = YES

PHASE32_AR_POSITION_SIZING_CHANGED = NO
PHASE32_AR_RUNTIME_CHANGED = NO
PHASE32_AR_SAFETY_CHANGED = NO

PHASE32_AR_PIT_SAFE_BY_DESIGN = YES
PHASE32_AR_MODE_PARITY_DESIGN = YES
PHASE32_AR_DETERMINISTIC_DESIGN = YES
PHASE32_AR_EXPLAINABILITY_COMPLETE = YES
PHASE32_AR_HISTORICAL_OUTCOME_SELECTION_FORBIDDEN = YES

PHASE32_AR_READY_FOR_SHADOW_IMPLEMENTATION = YES
PHASE32_AR_PRODUCTION_ACTIVATION_READY = NO
PHASE32_AR_LONG_RUN_CONTINUE = YES
PHASE32_AR_NEXT_STEP = Phase32-AS - Shadow Marginal Capital Frontier Implementation

PHASE32_AR_PRIMARY_JUDGMENT = PHASE32_AR_SHADOW_COMMON_MARGINAL_CAPITAL_FRONTIER_DESIGN_COMPLETE_READY_FOR_NON_AUTHORITATIVE_IMPLEMENTATION
```
