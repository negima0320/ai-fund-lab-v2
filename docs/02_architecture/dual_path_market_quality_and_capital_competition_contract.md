# Dual-Path Market Quality and Capital Competition Contract

Status: DESIGN-ONLY CONTRACT

Applies to: Production, Demo, Historical

Primary SoT:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`

This document is a Production architecture contract. It does not implement code,
change configuration, select thresholds, tune parameters, run Historical, or
authorize a production behavior change by itself.

## 1. Design Problem

Phase31-G14 through G19 identify a dual failure mode:

```text
Path A:
PREMATURE_RE_RISK under fragile or internally inconsistent market structure

Path B:
PARTIAL_BULL_OPPORTUNITY_CAPTURE_FAILURE from composition of otherwise valid
Portfolio Construction, Position Sizing, ADD, re-entry, lot, concentration, and
cash-residual constraints
```

The design goal is better adaptation to market structure and better capital
competition semantics without:

- creating a second Regime classifier
- weakening Safety hard caps
- using future returns or later outcomes as Production inputs
- tuning to a Historical window
- imposing fixed exposure targets, fixed BUY counts, or fixed position counts
- creating blanket re-entry permission or blanket re-entry prohibition
- coupling BUY and SELL
- introducing implicit fallback
- duplicating business-decision authority

## 2. Authority Separation

The existing Market Regime remains the sole canonical owner of medium-horizon
market-direction classification.

```text
Market Direction:
  Owner: Market Context
  Purpose: medium-horizon directional environment
  Examples: BULL, RECOVERY, RANGE, CORRECTION, BEAR

Market Quality:
  Owner: Market Context
  Purpose: short/medium agreement, participation quality, breadth persistence,
  internal consistency, recovery confirmation, and fragility evidence
```

Required invariants:

```text
MARKET_REGIME_AUTHORITY_CHANGED = NO
SECOND_REGIME_CLASSIFIER_CREATED = NO
MARKET_DIRECTION_AND_MARKET_QUALITY_SEPARATED = YES
```

Market Quality is evidence. It is not a BUY decision, SELL decision, position
count decision, exposure target, quantity, cash target, Submit permission, or
Safety override.

Canonical decision chain:

```text
J-Quants PIT data
  -> Market Context evidence
  -> Market Quality semantic state
  -> Portfolio Policy risk-pacing intent
  -> Portfolio Construction competition / allocation
  -> Position Sizing discrete quantity
  -> Submit / Execution
```

Runtime boundary lineage:

```text
Strategy authority evidence
  -> Runtime Planning immutable authority lineage envelope
  -> Pending preserved lineage
  -> Submit preserved lineage
  -> Execution / Ledger audit linkage
```

The Runtime lineage envelope is provenance, not a downstream decision input.
Runtime Planning, Pending, Submit, and Execution may preserve, hash, reload, and
bind this lineage to order/fill/state identities, but they must not reinterpret
Market Quality, Risk Pacing, Capital Competition, Re-entry, ADD, final
NO_DEPLOYABLE, Safety, or quantity semantics from it. Executable mechanics
remain carried by the established order fields: side, quantity, price,
reservation, safety, approval, and broker feasibility evidence.

```text
RUNTIME_AUTHORITY_LINEAGE_ENVELOPE_REQUIRED = YES
DOWNSTREAM_STRATEGY_REDECISION_FROM_LINEAGE_ALLOWED = NO
FULL_UPSTREAM_ARTIFACT_DUPLICATION_ALLOWED = NO
```

```text
MARKET_CONTEXT_DIRECTLY_SETS_QUANTITY = NO
MARKET_CONTEXT_DIRECTLY_SETS_EXPOSURE_TARGET = NO
```

## 3. Market Quality Semantic Contract

Canonical owner:

```text
MARKET_QUALITY_OWNER = MARKET_CONTEXT
```

Canonical producer:

```text
Production-common Market Context Engine
```

Canonical artifact target:

```text
market_context.v1 / strategy.market_context
```

Market Quality may be materialized as a sibling semantic field to Market
Direction. It must not replace or rename Market Regime.

### 3.1 Semantic States

| State | Meaning | Producer | Consumers | May influence | Must not influence directly | Fail-closed behavior |
| --- | --- | --- | --- | --- | --- | --- |
| `HEALTHY_EXPANSION` | Medium direction, short-term continuation, breadth, and participation are internally consistent and constructive. | Market Context | Portfolio Policy, PC, BUY Quality, PM evidence consumers | confidence in normal deployment and opportunity competition | fixed exposure, fixed BUY count, SELL suppression, Safety cap | if evidence incomplete, downgrade to explicit insufficiency |
| `HEALTHY_RECOVERY` | Recovery evidence is broad enough and internally confirmed for normalizing deployment posture. | Market Context | Portfolio Policy, PC, BUY Quality | risk-pacing intent, replacement urgency | bottom prediction, mandatory re-risk | if confirmation inputs missing, use confirmation-incomplete state |
| `RECOVERY_CONFIRMATION_INCOMPLETE` | Recovery or regime improvement exists, but confirmation breadth, persistence, or internal agreement is incomplete. | Market Context | Portfolio Policy, PC, BUY Quality | gradual redeployment, optionality preservation | blanket BUY ban, mandatory cash target | fail to cautious/gradual semantics |
| `FRAGILE_RECOVERY` | Recovery label or medium trend is present, but evidence indicates fragility, churn, or weak confirmation. | Market Context | Portfolio Policy, PC, BUY Quality | cautious deployment, stronger competition for marginal capital | SELL blocking, Safety weakening | fail closed to cautious semantics |
| `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH` | Medium direction remains constructive while short-term breadth or return participation narrows. | Market Context | Portfolio Policy, PC, BUY Quality | slower incremental redeployment, stricter marginal competition | reclassifying BULL, fixed max BUY count | fail closed to conflicted/insufficient evidence |
| `SHORT_TERM_BREADTH_BREAKDOWN` | Short-term participation weakens materially relative to available PIT breadth evidence. | Market Context | Portfolio Policy, PC, BUY Quality | risk pacing caution and reason evidence | automatic all-BUY rejection | fail closed to cautious semantics |
| `SECTOR_PARTICIPATION_NARROWING` | Market participation is concentrated in fewer sectors or sector dispersion indicates narrow leadership. | Market Context | Portfolio Policy, PC, BUY Quality | portfolio-fit and replacement competition evidence | hard sector cap unless separately authorized | design-only unless lineage is fixed |
| `CONFLICTED_MARKET_STRUCTURE` | Short/medium horizons, breadth, volatility, confidence, or transition evidence disagree. | Market Context | Portfolio Policy, PC, BUY Quality | preserve optionality, gradual deployment | second regime classifier | fail closed to cautious semantics |
| `INSUFFICIENT_EVIDENCE` | Required PIT inputs for Market Quality are unavailable, stale, contradictory, or not lineage-safe. | Market Context | Portfolio Policy, PC, BUY Quality | explicit conservative consumption | healthy fallback, BULL fallback | Portfolio Policy consumes safely |

### 3.2 Input Classes

Allowed Production input classes, subject to existing lineage and PIT authority:

- existing 5D return evidence
- existing 20D return evidence
- existing 5D breadth
- existing 20D breadth
- short/medium direction disagreement
- regime transition path
- days since transition, if PIT materialized
- recent transition/churn evidence, if PIT materialized
- existing volatility / downside-risk evidence
- existing Market Context confidence / uncertainty / coverage evidence
- sector participation evidence only after semantic definition and lineage are
  fixed in Market Context

Input classification:

| Input | Classification |
| --- | --- |
| 5D return / 20D return | `EXISTING_PRODUCTION_EVIDENCE` |
| 5D breadth / 20D breadth | `EXISTING_PRODUCTION_EVIDENCE` |
| short/medium disagreement | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| regime transition path / days since transition | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| transition churn | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| volatility / downside-risk evidence | `EXISTING_PRODUCTION_EVIDENCE` |
| confidence / uncertainty / coverage | `EXISTING_PRODUCTION_EVIDENCE` |
| sector participation | `DERIVABLE_PIT_EVIDENCE_REQUIRING_DESIGN` |
| G17/G18 diagnostic cohorts | `DIAGNOSTIC_ONLY_NOT_PRODUCTION_READY` |
| future return / later PnL / later campaign label | `OUT_OF_SCOPE` |

Forbidden input classes:

```text
future price
future return
future PnL
fill outcome
Paper Ledger result
Historical test outcome
later market movement
post-hoc recovery success/failure label
current-snapshot-only source for Historical decisions
```

```text
FUTURE_DATA_ALLOWED = NO
HISTORICAL_OUTCOME_ALLOWED_AS_RUNTIME_INPUT = NO
```

## 4. Market Internal Agreement Model

The Market Quality producer represents internal agreement semantically, not as a
Historical-optimized composite score.

Examples:

```text
medium horizon constructive
+ short horizon constructive
+ broad participation
+ stable transition context
= HEALTHY_EXPANSION or HEALTHY_RECOVERY

medium horizon constructive
+ short horizon weak
+ narrow participation
= SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH

recent recovery direction
+ incomplete breadth / churn / low confidence
= RECOVERY_CONFIRMATION_INCOMPLETE or FRAGILE_RECOVERY

signals disagree or coverage is insufficient
= CONFLICTED_MARKET_STRUCTURE or INSUFFICIENT_EVIDENCE
```

No weights, cutoffs, or scores may be selected from G17/G18 outcomes in this
contract.

```text
OUTCOME_OPTIMIZED_COMPOSITE_SCORE_CREATED = NO
MARKET_INTERNAL_AGREEMENT_SEMANTIC_DEFINED = YES
```

## 5. Risk Pacing Contract

Risk pacing is a consumer-side semantic contract.

Owner:

```text
RISK_PACING_OWNER = PORTFOLIO_POLICY
```

Primary consumers:

```text
RISK_PACING_CONSUMER = PORTFOLIO_CONSTRUCTION / BUY_QUALITY / POSITION_SIZING_AS_CONSUMER_OF_PC_TARGETS
```

Risk pacing expresses how willing the Strategy is to deploy marginal capital. It
does not prescribe fixed exposure.

Allowed intents:

| Intent | Meaning |
| --- | --- |
| `NORMAL_DEPLOYMENT` | Market Quality and opportunity evidence support ordinary capital competition. |
| `CAUTIOUS_DEPLOYMENT` | Marginal deployment requires stronger contemporaneous evidence; Safety and SELL independence remain unchanged. |
| `GRADUAL_REDEPLOYMENT` | After risk reduction or recovery transition, redeployment may occur through confirmed competitors rather than abrupt forced exposure. |
| `PRESERVE_OPTIONALITY` | Cash may remain valid when opportunity quality, market quality, or constraint composition does not support deployment. |

May influence:

- pace of incremental deployment
- competition between `NEW_BUY`, `ADD`, and `CASH / OPTIONALITY`
- replacement urgency
- acceptance of gradual re-risk
- reason evidence for residual cash

Must not encode:

- fixed exposure percentage
- fixed daily BUY count
- fixed position count
- fixed cooldown days
- fixed maximum cash level

```text
FIXED_EXPOSURE_TARGET_DEFINED = NO
FIXED_BUY_COUNT_DEFINED = NO
FIXED_POSITION_COUNT_DEFINED = NO
```

## 6. Gradual Re-Risk Semantics

Gradual re-risk is a semantic process:

```text
risk reduced
  -> initial recovery evidence
  -> confirmation incomplete / conflicted structure
  -> confirmed healthier participation
  -> normal deployment
```

Component ownership:

| Transition evidence | Owner |
| --- | --- |
| market recovery / fragility / participation quality | Market Context |
| risk-pacing intent | Portfolio Policy |
| candidate / ADD / Cash competition | Portfolio Construction |
| discrete quantity and lot feasibility | Position Sizing |
| execution readiness | Runtime Planning / Strategy Planning Authority / Submit |
| hard protection | Safety |

```text
GRADUAL_RERISK_CONTRACT_DEFINED = YES
BOTTOM_PREDICTION_REQUIRED = NO
```

## 7. Constraint Composition Contract

Path B requires explicit composition semantics. The system must not weaken valid
constraints merely because they leave Cash idle.

Owner:

```text
CONSTRAINT_COMPOSITION_OWNER = PORTFOLIO_CONSTRUCTION
FINAL_NO_DEPLOYABLE_OPPORTUNITY_AUTHORITY = PORTFOLIO_CONSTRUCTION_TARGET_PORTFOLIO_DECISION_AUTHORITY
```

Portfolio Construction owns the final Strategy judgment that no deployable
opportunity exists after consuming:

- Strategy concentration cap
- Safety hard concentration cap as a boundary, not an optimizer
- Strategy max position policy
- Safety hard max positions, if any, as boundary only
- discrete lot feasibility evidence from Position Sizing / lot preflight
- residual capital evidence
- re-entry semantic eligibility
- ADD incremental competitiveness
- candidate competition
- BUY replacement
- broker / cash feasibility evidence

Unused capital must be represented explicitly:

| Residual class | Meaning |
| --- | --- |
| `UNAVOIDABLE_LOT_RESIDUAL` | No executable lot can safely use the cash. |
| `POLICY_RESERVE` | Strategy policy or risk pacing chooses optionality over deployment. |
| `SAFETY_RESERVE` | Safety boundary prevents use. |
| `REALLOCATABLE_RESIDUAL` | Capital appears usable by another valid competitor and must trigger reconsideration. |
| `NO_VALID_COMPETITOR` | No candidate, ADD, or replacement competitor remains eligible. |

Next-best valid competitors may be reconsidered only through PC-owned
competition. Downstream layers must not bypass Strategy membership, target
weight, Safety, or Submit authority.

Phase31-G97 binding clarification:

`REALLOCATABLE_RESIDUAL` / `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`
is non-terminal. It must re-enter PC-owned canonical capital competition, but
the re-entry itself is not a security allocation. The reconsidered row must
compete with existing positive security allocations, valid ADD competitors,
optional Cash, lot feasibility, concentration/cap constraints, and Safety
terminal boundaries. Existing G90 security/Cash participation-vs-deferral
semantics remain the resolver for marginal Cash-preferred rows.

```text
REALLOCATABLE_RESIDUAL_REENTERS_PC_COMPETITION = YES
RECONSIDERATION_AUTO_AUTHORIZATION = NO
G90_REUSED_FOR_RECONSIDERATION = YES
OPTIONAL_CASH_FIRST_CLASS_AFTER_RECONSIDERATION = YES
SAFETY_TERMINAL_RECONSIDERATION_ALLOWED = NO
```

```text
CONSTRAINT_COMPOSITION_CONTRACT_DEFINED = YES
```

## 8. Strategy Cap vs Safety Hard Cap

Strategy constraint is not a Safety hard limit.

```text
Strategy cap:
  Owner: Portfolio Policy / Portfolio Construction / Position Sizing consumer
  Purpose: desired allocation and diversification

Safety hard cap:
  Owner: Safety
  Purpose: non-negotiable protection boundary
```

The two must not be merged, and downstream consumers must not recreate the
Strategy decision.

```text
STRATEGY_SAFETY_CAP_SEPARATION_PRESERVED = YES
SECOND_CAP_DECISION_CREATED = NO
```

## 9. Lot / Residual Reallocation Contract

The Phase28/29 lot-aware architecture remains in force.

```text
target allocation
  -> discrete quantity
  -> unallocatable residual
  -> next competitor / ADD reconsideration
  -> legitimate residual Cash
```

Position Sizing owns discrete quantity evidence. Portfolio Construction owns
the decision to reconsider another competitor or preserve Cash after consuming
that evidence.

```text
LOT_FIRST_CONTRACT_PRESERVED = YES
RESIDUAL_REALLOCATION_CONTRACT_DEFINED = YES
LOT_AWARE_ARCHITECTURE_REPLACED = NO
```

## 10. Re-Entry Contract

Re-entry is a semantic eligibility contract, not a blanket rule.

It must distinguish:

- prior EXIT identity
- prior exit reason/context when legitimately available at decision time
- renewed current eligibility
- churn protection
- same-symbol renewed evidence
- current Market Quality
- explicit Safety restrictions

No fixed cooldown duration is selected by this design. Existing configured
cooldowns remain existing implementation details until a later implementation
task changes them through normal review.

```text
BLANKET_REENTRY_BAN = NO
BLANKET_REENTRY_PERMISSION = NO
REENTRY_SEMANTIC_CONTRACT_DEFINED = YES
FIXED_REENTRY_COOLDOWN_SELECTED = NO
```

## 11. ADD as Capital Competitor

PM ADD is directional intent, not an order. ADD competes for marginal capital
inside Portfolio Construction.

ADD pipeline semantics:

```text
ADD_INTENT
  -> ADD_ELIGIBILITY
  -> ADD_INCREMENTAL_INVESTMENT_VALUE
  -> ADD_OPPORTUNITY_COST
  -> ADD_TARGET_WEIGHT_CHANGE
  -> ADD_DISCRETE_QUANTITY_DELTA
  -> ADD_SUBMIT
```

ADD may compete against:

- `NEW_BUY`
- another `ADD`
- `CASH / OPTIONALITY`

ADD must not be automatically superior to NEW BUY and must not be
automatically rejected. Incremental value must be based on contemporaneous PIT
evidence, not later PnL.

```text
ADD_CAPITAL_COMPETITION_CONTRACT_DEFINED = YES
ADD_AUTOMATIC_PRIORITY = NO
ADD_AUTOMATIC_REJECTION = NO
```

## 12. BUY / ADD / Cash Competition

Canonical capital competitors:

```text
NEW_BUY
ADD
CASH / OPTIONALITY
```

Cash remains a valid allocation when deployment is not justified or not safely
executable.

Market Quality may alter willingness to deploy through Portfolio Policy risk
pacing. It must not alter Candidate alpha semantics or raw Opportunity Ranking
meaning.

```text
CASH_REMAINS_VALID_ALLOCATION = YES
FIXED_MINIMUM_INVESTMENT = NO
FIXED_TARGET_POSITION_COUNT = NO
```

### 12.1 Economically Binding Market-Candidate-Cash Interaction

Phase31-G37 found that the first Risk Pacing implementation produced
authoritative market-wide pacing states but was effectively non-binding in the
observed selected candidate domain. This contract refines the permanent
architecture: Risk Pacing must interact with candidate quality and Cash
optionality before final incremental capital winner selection becomes
economically irreversible.

The interaction stage is:

```text
Market Context Market Quality
  -> Portfolio Policy Risk Pacing
  -> Portfolio Construction pre-final capital interaction
  -> final NEW_BUY / ADD / CASH winner selection
  -> Position Sizing discrete quantity
```

```text
MARKET_CANDIDATE_INTERACTION_STAGE = BEFORE_FINAL_CAPITAL_WINNER
```

Portfolio Construction consumes authoritative evidence only. It must not
produce Market Quality, redefine Risk Pacing, or create candidate admission
features. Candidate admission remains the legal / strategic eligibility gate.
Risk Pacing is not a second candidate filter; it changes marginal capital
preference among already valid competitors.

```text
RISK_PACING_IS_SECOND_CANDIDATE_FILTER = NO
```

#### 12.1.1 Opportunity Quality Continuum

Capital competition requires a graduated opportunity quality continuum that is
separate from hard eligibility:

| Class | Meaning | Valid deployment candidate | Missing / blocked evidence |
| --- | --- | --- | --- |
| `STRONG` | Explicit PIT evidence supports exceptional or high-conviction incremental deployment. | YES | NO |
| `COMPARABLE_HIGH` | Valid opportunity with above-normal but not exceptional marginal evidence. | YES | NO |
| `COMPARABLE_MARGINAL` | Valid opportunity, but close enough to Cash optionality that market weakness can make Cash preferable. | YES | NO |
| `WEAK_VALID` | Still strategically eligible and not rejected, but marginal enough that only normal or very supportive conditions should deploy it. | YES | NO |
| `INSUFFICIENT` | Required comparison evidence is missing, stale, contradictory, or lineage-incomplete. | NO for incremental deployment until resolved | YES |
| `BLOCKED` | Candidate admission, Safety, eligibility, or PM/ADD semantics block deployment. | NO | YES |

`WEAK_VALID` and `COMPARABLE_MARGINAL` must not mean invalid, rejected, missing
data, or hard blocked. They mean valid but marginal investment opportunities.
The class boundary must be structurally reachable from PIT evidence and must
not be selected from later PnL or single-window performance optimization.

Existing PIT features are reused first:

- runtime opportunity score / rank / expected-edge evidence
- entry admission action, state, sufficiency, and quality bias
- BUY quality action and hard/soft reason families
- ADD expected-edge improvement, incremental value, opportunity cost, and
  add-worthiness evidence
- re-entry eligibility evidence once the symbol is currently eligible
- portfolio concentration, current holdings, residual capital, and lot
  feasibility as Portfolio Construction context

If later implementation proves these fields cannot separate
`COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, and `WEAK_VALID` without duplicating a
producer, a new PIT feature may be proposed in a later design task. G38 does
not define a new production feature or select numeric thresholds.

```text
GRADUATED_WEAK_OPPORTUNITY_CLASS_DEFINED = YES
GRADUATED_WEAK_CLASS_STRUCTURALLY_REACHABLE = YES
EXISTING_PIT_FEATURES_REUSED_FIRST = YES
PRODUCTION_THRESHOLD_VALUES_SELECTED_IN_THIS_CONTRACT = NO
```

#### 12.1.2 Market x Candidate Interaction Matrix

The refined semantic matrix is:

| Risk Pacing intent | `STRONG` | `COMPARABLE_HIGH` | `COMPARABLE_MARGINAL` | `WEAK_VALID` | `INSUFFICIENT` | `BLOCKED` |
| --- | --- | --- | --- | --- | --- | --- |
| `NORMAL_DEPLOYMENT` | Deployment may win | Deployment may win | Deployment may win | Deployment may win if other competitors do not dominate | Fail closed | Blocked |
| `GRADUAL_REDEPLOYMENT` | Deployment may win | Selective deployment may win | Cash may win unless portfolio fit / ADD value is confirmed | Cash preferred | Fail closed | Blocked |
| `CAUTIOUS_DEPLOYMENT` | Deployment may win with explicit symbol-specific evidence | Cash may win unless evidence is strong enough for caution | Cash preferred | Cash preferred | Fail closed | Blocked |
| `PRESERVE_OPTIONALITY` | Deployment may win only if exceptional and lineage-complete | Cash preferred | Cash preferred | Cash preferred | Fail closed | Blocked |

This matrix is semantic. It does not set exposure targets, BUY counts, fixed
daily quotas, position counts, score thresholds, or cooldown days. Exposure
remains emergent from the daily competitor set, existing holdings, Safety,
lot feasibility, cash availability, and Position Sizing quantity output.

```text
MARKET_CANDIDATE_INTERACTION_MATRIX_DEFINED = YES
CAUTIOUS_GRADUAL_ECONOMIC_DIFFERENCE_DESIGNED = YES
STRONG_OPPORTUNITY_CAN_OVERRIDE_CAUTION = YES
BLANKET_MARKET_BUY_BAN = NO
FIXED_EXPOSURE_TARGET_INTRODUCED = NO
```

#### 12.1.3 Cash as a True Economic Competitor

Cash / Optionality must be represented as an actual capital competitor before
candidate failure, not merely as residual bookkeeping after deployment has
already lost for other reasons.

Cash may win when contemporaneous evidence says optionality has higher marginal
value than deploying into a valid but marginal opportunity. Cash value may be
derived from:

- Market Quality and Risk Pacing intent
- breadth / recovery confirmation / conflicted market structure evidence
- portfolio concentration and existing exposure composition
- availability of stronger NEW_BUY or ADD alternatives
- opportunity quality class and evidence completeness
- lot and residual feasibility from Position Sizing evidence

Cash must not be assigned a performance-optimized score or a fixed exposure
target. Cash selection must materialize reason evidence such as
`POLICY_RESERVE`, `OPTIONALITY_PREFERRED_TO_MARGINAL_COMPETITOR`,
`GRADUAL_REDEPLOYMENT_WAIT_FOR_CONFIRMATION`, or
`CAUTIOUS_MARKET_CASH_BEATS_MARGINAL_OPPORTUNITY`.

```text
CASH_IS_TRUE_ECONOMIC_COMPETITOR_DESIGNED = YES
CASH_CAN_WIN_BEFORE_CANDIDATE_FAILURE = YES
```

#### 12.1.4 ADD, Re-entry, and Existing Holdings

Risk Pacing primarily governs new incremental deployment. It must not
automatically liquidate existing winners. HOLD / REDUCE / EXIT remain PM-owned,
and SELL independence is unchanged.

ADD participates in the same capital competition as NEW_BUY and Cash. A strong
existing winner may still receive ADD during caution when ADD evidence is
explicitly strong. A marginal ADD may lose to Cash. Neither ADD nor NEW_BUY has
automatic priority.

Re-entry remains symbol-local eligibility. Once a symbol is eligible for
re-entry, it enters the same current capital competition with no permanent
discount or bonus merely because it is a re-entry.

Phase32-CW narrows the meaning of eligibility: residual REENTRY protection
checks lineage, prior EXIT context, short churn, repeated unresolved churn,
prior-cause recovery, HARD_STOP recovery, and conservative UNKNOWN-prior-context
independence. Current rank, Buy Quality, Entry Admission, Continuation Quality,
downside, capacity, Safety, broker, corporate-action, PC, PS, and Runtime
feasibility are ordinary current BUY authorities and must not be duplicated as
broad REENTRY-only penalties. `REENTRY_UNKNOWN_PRIOR_CONTEXT` preserves
prior-owned lineage and never becomes fake BUY_NEW.

```text
RISK_PACING_FORCES_EXISTING_POSITION_EXIT = NO
ADD_MARKET_CANDIDATE_INTERACTION_DEFINED = YES
ADD_AUTOMATIC_PRIORITY = NO
NEW_BUY_AUTOMATIC_PRIORITY = NO
REENTRY_CAPITAL_COMPETITION_CONSISTENT = YES
```

#### 12.1.5 Progressive Re-risking

Progressive re-risking is expressed through changing marginal capital
preference, not fixed waiting rules:

```text
PRESERVE_OPTIONALITY:
  Cash defeats most marginal deployment unless opportunity evidence is
  exceptional and complete.

GRADUAL_REDEPLOYMENT:
  selective deployment can resume for strong or high-quality comparable
  candidates; marginal comparable opportunities may defer to Cash.

NORMAL_DEPLOYMENT:
  ordinary competition may deploy valid comparable and weak-valid candidates
  when they are the best available use of capital.
```

`RECOVERY_CONFIRMATION_INCOMPLETE` must differ economically from
`HEALTHY_RECOVERY`: the same marginal candidate may lose to Cash under
incomplete recovery and deploy under healthy recovery. A BULL market direction
with weak internals may reduce marginal deployment, while a BEAR direction with
exceptional symbol-level evidence may still permit selective deployment.

```text
PROGRESSIVE_RERISKING_WITHOUT_FIXED_HOLD_PERIOD = YES
RECOVERY_QUALITY_ECONOMIC_DIFFERENCE_DESIGNED = YES
BULL_WEAK_INTERNALS_CAN_REDUCE_DEPLOYMENT = YES
BEAR_STRONG_OPPORTUNITY_CAN_DEPLOY = YES
```

#### 12.1.6 Fail-Closed and Downstream Boundary

Missing Market Quality, missing comparison evidence, contradictory side-effect
evidence, stale lineage, or unresolved admission evidence must fail closed for
incremental deployment. It must not silently default to comparable or healthy.

Portfolio Construction selects the semantic capital winner. Position Sizing
remains the only discrete quantity owner. Runtime Planning, Pending, Submit,
Execution, and Ledger preserve and consume lineage but may not redo capital
competition.

The Portfolio Construction final capital winner must be materialized as a
canonical deployment set before discrete sizing. Position Sizing consumes that
set as an input boundary: if Cash wins, no defeated incremental `NEW_BUY`, ADD,
or re-entry security may create a positive sizing delta; if a security wins,
only the selected deployment security or explicitly selected deployment set may
enter incremental sizing. Existing holdings remain governed by PM/HOLD/REDUCE/
EXIT authority and are not sold merely because incremental Cash wins.

Runtime lineage persistence is not sufficient evidence of decision binding.
Lineage proves provenance; binding requires the canonical deployment set to
shape the executable Position Sizing input set before Runtime Planning can map
quantity deltas into order intents.

```text
INCOMPLETE_EVIDENCE_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED = YES
SECOND_DISCRETE_QUANTITY_AUTHORITY = NO
POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES
DOWNSTREAM_CAPITAL_REDECISION_ALLOWED = NO
FINAL_CAPITAL_WINNER_BINDS_BEFORE_DISCRETE_SIZING = YES
LINEAGE_PERSISTENCE_IS_NOT_DECISION_BINDING = YES
```

#### 12.1.7 Synthetic Binding Acceptance Contract

A later implementation must prove binding with PIT-safe synthetic cases before
any long Historical comparison:

| Case | Held constant | Changed input | Expected semantic result |
| --- | --- | --- | --- |
| A | candidate evidence | `NORMAL_DEPLOYMENT + COMPARABLE_MARGINAL` | deployment may win |
| B | same candidate as A | `CAUTIOUS_DEPLOYMENT` | Cash may win |
| C | market state | high-quality comparable candidate | selective deployment may win |
| D | marginal opportunity | `PRESERVE_OPTIONALITY` | Cash wins |
| E | caution market | `STRONG` candidate evidence | deployment may still win |
| F | same marginal candidate | `RECOVERY_CONFIRMATION_INCOMPLETE` / gradual | slower or Cash-preferred deployment |
| G | same marginal candidate | `HEALTHY_RECOVERY` / normal | stronger deployment preference |
| H | candidate otherwise valid | Market Quality missing | incremental fail-closed |

```text
ECONOMIC_BINDING_STATE_SPACE_COMPLETE = YES
SYNTHETIC_BINDING_ACCEPTANCE_MATRIX_DEFINED = YES
SAME_CANDIDATE_DIFFERENT_MARKET_CAN_CHANGE_DECISION = YES
SAME_MARKET_DIFFERENT_CANDIDATE_CAN_CHANGE_DECISION = YES
```

### 12.2 Phase31-G53 Multi-Allocation Capital Pacing Contract

Phase31-G52 found that the G42-G51 single-winner implementation correctly made
Cash and Risk Pacing binding, but over-compressed capital allocation into a
binary result: Cash winner meant zero incremental security deployment, and a
security winner meant only one selected deployment could proceed. Phase31-G53
replaces that general semantic with a multi-allocation capital pacing contract.

Market Quality is contextual evidence for capital pacing. Risk Pacing answers
how aggressively incremental capital should be deployed. Neither authority is
a binary security admission owner. Candidate admission, Safety, special-risk,
corporate-action, missing-evidence, and explicit invalidity authorities remain
the hard gates.

```text
MARKET_QUALITY_ROLE = CAPITAL_PACING_CONTEXT
MARKET_QUALITY_HARD_BUY_GATE = NO
RISK_PACING_ROLE = CAPITAL_DEPLOYMENT_INTENSITY_AUTHORITY
RISK_PACING_BINARY_SECURITY_ADMISSION_OWNER = NO
```

The canonical capital allocation problem is:

```text
valid opportunity universe
-> Portfolio Policy incremental capital budget envelope
-> candidate-local allocation evidence preservation
-> Portfolio Construction multi-security + Cash allocation
-> Position Sizing lot materialization
-> Portfolio Construction residual / infeasible allocation reconsideration
-> remaining capital returns to Cash
```

The general capital winner cardinality is no longer `SINGLE`. The permanent
semantic is multi-allocation: multiple valid securities and Cash may receive
authorized portions of the same day's incremental capital budget. Cash remains
a true economic competitor, but Cash is not required to win all available
capital.

```text
GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION
CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION
CASH_PARTIAL_ALLOCATION_SUPPORTED = YES
CASH_WINNER_TAKES_ALL_REQUIRED = NO
```

Portfolio Policy owns a canonical `incremental_capital_budget_envelope`.
The envelope expresses deployment intensity / available marginal capital
capacity. It may consume Market Quality, Risk Pacing, portfolio state, current
exposure, Cash state, and existing holdings. It must not select symbols,
weights, or quantities.

Budget envelope states are semantic and not Historical-return-tuned numeric
percentages. The initial canonical state family is:

```text
FULL_DEPLOYMENT_CAPACITY
ELEVATED_DEPLOYMENT_CAPACITY
SELECTIVE_DEPLOYMENT_CAPACITY
DEFENSIVE_DEPLOYMENT_CAPACITY
PRESERVE_MOST_OPTIONALITY
```

These states describe relative deployment intensity only. They do not define
fixed exposure targets such as BEAR=20%, RANGE=50%, or BULL=90%; they do not
define fixed BUY counts, fixed daily quotas, score thresholds, cooldown days,
or holding periods.

```text
CAPITAL_BUDGET_ENVELOPE_OWNER = PORTFOLIO_POLICY
CAPITAL_BUDGET_SEMANTICS_DEFINED = YES
FIXED_MARKET_EXPOSURE_TARGET_CREATED = NO
HISTORICAL_RETURN_DERIVED_ALLOCATION_PERCENTAGE_COUNT = 0
```

Portfolio Construction owns allocation of the authorized marginal capital
budget across `NEW_BUY`, `ADD`, eligible re-entry-as-`NEW_BUY`, and Cash.
Portfolio Construction must preserve enough candidate-local evidence for
within-class allocation, including PIT-safe rank / rank tier, relative
strength, continuation quality, early recovery / improving evidence,
stock-specific strength against weak market context, evidence completeness,
fragility / overheat where authoritative, and Expected Edge evidence where
authoritative. Opportunity Quality may remain a canonical summary, but it must
not be the only allocation signal when many different candidates share the same
coarse class.

Phase31-G81 binds the final security/Cash partition to the canonical
`market_candidate_cash_interaction` result. After Phase31-G86, interaction
result is explicitly separated from final allocation action. Rows whose
interaction result is `CASH_PREFERRED` must pass through Portfolio
Construction's participation-vs-deferral resolution before final
multi-allocation publication:

```text
CASH_PREFERRED
-> PC final participation-vs-deferral resolution
-> reduced security participation OR zero-weight Cash deferral
```

Rows resolved to `CASH_PREFERRED_DEFER` are recorded as zero-weight security
deferrals and returned to optional Cash; they are not positive security
allocations. Rows resolved to `CASH_PREFERRED_PARTICIPATION_VALID` may retain
reduced security allocation with explicit lineage. This preserves Cash as a
first-class economic competitor while keeping `DEPLOY_ELIGIBLE` and
`SELECTIVE_COMPETITION` rows eligible for multi-security allocation.

Phase31-G83 refines bootstrap binding by Cash state. `CASH_PREFERRED` in
`EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP` may preserve reduced-risk initial
participation when existing Portfolio Policy evidence explicitly carries
`EXPLORATION_PARTICIPATION_RISK_PRESERVED` and
`PROFIT_ENGINE_PRESERVATION_CONTEXT`, and selected valid opportunities exist.
The reduced participation uses existing accepted security increments; it does
not create fixed exposure, fixed BUY count, thresholds, or a new score.
Phase31-G86 adds the non-bootstrap resolution: already-deployed / residual
optionality `CASH_PREFERRED` rows are not automatically positive and not
automatically zero. PC resolves participation-valid reduced security versus
weak-tail Cash deferral from existing row-level, same-date opportunity-set,
aggregate, Cash, and capital budget evidence.

Phase31-G90 makes the aggregate resolver plural-participation aware. The
same-quality-class frontier remains useful priority evidence, but it is not an
exclusive admission gate. `NOT_ON_FRONTIER` alone must not imply
`CASH_PREFERRED_DEFER`; multiple credible `CASH_PREFERRED` rows may retain
reduced security allocation when same-date PIT evidence supports participation.
The aggregate resolver still prevents G80 weak-tail overdeployment by returning
weaker / contextually dominated marginal increments to optional Cash, without
creating fixed rank, confidence, score, exposure, position-count, aggregate
percentage, or Historical-outcome-tuned thresholds.

```text
MULTI_ASSET_CAPITAL_ALLOCATION_OWNER = PORTFOLIO_CONSTRUCTION
OPPORTUNITY_INFORMATION_PRESERVATION_REFINED = YES
OPPORTUNITY_QUALITY_REMAINS_CANONICAL_SUMMARY = YES
WITHIN_CLASS_ALLOCATION_EVIDENCE_AVAILABLE = YES
BOOTSTRAP_CASH_PREFERRED_CAN_PRESERVE_REDUCED_PARTICIPATION = YES
CASH_PREFERRED_INTERACTION_ACTION_SEPARATED = YES
PC_PARTICIPATION_DEFERRAL_AUTHORITY = YES
RESIDUAL_CASH_PREFERRED_WEAK_TAIL_SECURITY_WEIGHT = 0 after CASH_PREFERRED_DEFER
```

Weak market context plus strong stock-specific evidence may produce reduced
allocation rather than automatic zero allocation. CAUTIOUS +
`COMPARABLE_MARGINAL` does not automatically mean zero; Cash may receive the
marginal capital, or a reduced allocation may proceed, depending on preserved
comparative evidence. NORMAL / healthy conditions must preserve broad
opportunity capture subject to normal Portfolio Construction, lot,
concentration, Safety, and evidence-completeness constraints.

```text
WEAK_MARKET_STRONG_STOCK_PARTICIPATION_SUPPORTED = YES
CAUTIOUS_MARGINAL_AUTOMATIC_ZERO = NO
NORMAL_MULTI_OPPORTUNITY_CAPTURE_SUPPORTED = YES
```

Cash semantics distinguish `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP` from
`RESIDUAL_OPTIONALITY_CASH`. Empty-portfolio bootstrap must not become a
permanent optionality trap when valid PIT opportunities exist. The architecture
therefore allows reduced-risk initial entry concepts such as
`REDUCED_RISK_INITIAL_ENTRY` / `INITIAL_EXPLORATION_ALLOCATION`, while still
preserving 100% Cash when no valid opportunities exist, evidence is incomplete,
all opportunities are blocked, or market and candidate evidence jointly make
deployment unjustified.

```text
BOOTSTRAP_AND_RESIDUAL_CASH_DISTINGUISHED = YES
BOOTSTRAP_PARTICIPATION_PATH_DEFINED = YES
REDUCED_RISK_INITIAL_ENTRY_DEFINED = YES
LEGITIMATE_100_PERCENT_CASH_SUPPORTED = YES
```

ADD competes within the same budget envelope. It has no automatic priority and
no automatic rejection. Eligible re-entry behaves as a normal `NEW_BUY`
capital competitor without permanent special penalty. Existing strong holdings
and SELL decisions remain independent of incremental BUY/ADD pacing.

Eligibility here means residual REENTRY protection has passed; it does not mean
historical ownership was erased. Recoverable prior EXIT provenance defects still
fail closed, and genuinely unrecoverable old prior context must remain auditable
as UNKNOWN lineage.

```text
ADD_MULTI_ALLOCATION_SUPPORTED = YES
ADD_AUTOMATIC_PRIORITY = NO
REENTRY_MULTI_ALLOCATION_SUPPORTED = YES
REENTRY_SPECIAL_PENALTY = NO
WINNER_RETENTION_INDEPENDENCE_PRESERVED = YES
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SAFETY_AUTHORITY_CHANGED = NO
```

Lot infeasibility must not collapse the entire day's allocation. Position
Sizing materializes PC-authorized allocations into discrete lots. Portfolio
Construction residual / lot reconsideration may reallocate infeasible or
residual capital among remaining valid opportunities and Cash. Remaining
capital returns to Cash.

```text
CANONICAL_MULTI_ALLOCATION_SEQUENCE_DEFINED = YES
MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES
```

The G50 executable-binding lesson remains permanent: lineage persistence is
not executable decision binding, and downstream consumers must not re-decide
capital allocation. What migrates is the shape of the binding object: from a
single selected deployment to a canonical multi-allocation deployment set.
Position Sizing receives already-authorized allocations and converts them to
lots; it does not select economic winners.

```text
G43_BINDING_MATRIX_MIGRATION_CLASS = MIGRATE
SINGLE_DEPLOYMENT_SET_MIGRATION_CLASS = MIGRATE
G50_EXECUTABLE_BINDING_PRINCIPLE_PRESERVED = YES
LINEAGE_BINDING_DISTINCTION_PRESERVED = YES
POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES
POSITION_SIZING_SELECTS_ECONOMIC_WINNERS = NO
```

Future implementation acceptance must evaluate, separately and without
Historical-return-tuned thresholds:

- avoidable low-quality loss prevented
- legitimate exploration / participation losses incurred
- winner opportunities captured
- winner opportunities missed
- valid multi-security opportunity capture
- weak-market reduced deployment
- strong-stock participation under weak market context
- partial Cash allocation
- legitimate all-Cash decisions
- pre/post-March PIT selectivity without optimizing to March outcomes

```text
EXPLORATION_VS_AVOIDABLE_LOSS_EVALUATION_CONTRACT_DEFINED = YES
PROFIT_ENGINE_PRESERVATION_ACCEPTANCE_DEFINED = YES
MARKET_PACING_SELECTIVITY_REQUIREMENT_DEFINED = YES
```

Implementation must be staged, not big-bang:

```text
A. permanent SoT update
B. capital budget envelope producer
C. multi-security allocation framework
D. Opportunity information preservation
E. bootstrap / reduced-risk entry semantics
F. Position Sizing consumption migration
G. lot / residual reconsideration
H. Runtime lineage migration
I. synthetic acceptance
J. existing-PIT activation / suppression characterization
K. fresh Historical
```

```text
STAGED_MIGRATION_PLAN_DEFINED = YES
BIG_BANG_IMPLEMENTATION_ALLOWED = NO
FUTURE_INPUT_COUNT = 0
HISTORICAL_OUTCOME_DESIGN_INPUT_COUNT = 0
PAPER_LEDGER_DESIGN_INPUT_COUNT = 0
MFE_MAE_DESIGN_INPUT_COUNT = 0
```

## 13. BUY / SELL Independence

BUY and SELL are independent business decisions.

Market Quality and Risk Pacing may affect BUY/ADD deployment behavior, but must
not prevent legitimate SELL, REDUCE, or EXIT. SELL must remain able to reduce
risk when BUY is blocked, review-required, absent, zero quantity, or no-action.

```text
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SELL_AUTHORITY_CHANGED = NO
```

Winner-retention philosophy is unchanged:

- strong winners continue while evidence remains strong
- partial REDUCE remains available
- EXIT remains available on meaningful deterioration
- no fixed holding period
- no mandatory profit taking
- no outcome-trained MFE target

```text
WINNER_RETENTION_PHILOSOPHY_CHANGED = NO
FIXED_HOLDING_PERIOD_CREATED = NO
```

## 14. Missing Evidence and Fail-Closed Behavior

If required Market Quality evidence is unavailable:

- do not fabricate a healthy state
- do not silently fall back to BULL
- do not use Historical evidence
- materialize `INSUFFICIENT_EVIDENCE` or architecture-equivalent missing state

Portfolio Policy consumes unknown quality conservatively through cautious or
optionality-preserving semantics. It must not convert missing Market Quality
into normal deployment.

```text
MARKET_QUALITY_FAIL_CLOSED = YES
IMPLICIT_HEALTHY_FALLBACK = NO
IMPLICIT_BULL_FALLBACK = NO
```

## 15. Temporal Authority Contract

Every Market Quality input must be decision-time PIT.

Required temporal semantics:

- `as_of_business_date` must be explicit
- input market dates must be `<= business_date`
- publication or availability must be known by decision time when applicable
- quote cutoffs must follow the existing Runtime temporal freshness contract
- sector membership must be as-of and effective-date safe
- financial/event data must satisfy known-at or effective-date constraints
- current-snapshot-only sources must not become Historical decision inputs

```text
TEMPORAL_CONTRACT_EXPLICIT = YES
CURRENT_SNAPSHOT_NON_PIT_SOURCE_ALLOWED_FOR_HISTORICAL_DECISION = NO
```

## 16. Evidence Materialization and Reason Codes

Canonical artifacts should materialize:

- Market Direction
- Market Quality
- component evidence
- semantic reasons
- confidence / evidence completeness
- Risk Pacing intent
- allocation outcome
- blocked reasons
- residual Cash reason

These are evidence outputs. They must not become a feedback data source for
later Strategy decisions.

```text
EVIDENCE_ARTIFACT_FEEDBACK_LOOP_ALLOWED = NO
```

Reason families:

| Family | Examples |
| --- | --- |
| Market Quality | `MARKET_QUALITY_HEALTHY`, `MARKET_QUALITY_FRAGILE`, `MARKET_STRUCTURE_CONFLICTED` |
| Participation | `SHORT_TERM_PARTICIPATION_NARROWING`, `SECTOR_PARTICIPATION_NARROWING`, `RECOVERY_CONFIRMATION_INCOMPLETE` |
| Risk pacing | `RISK_PACING_CAUTION`, `GRADUAL_REDEPLOYMENT`, `PRESERVE_OPTIONALITY` |
| Residual cash | `VALID_POLICY_RESERVE`, `VALID_SAFETY_RESERVE`, `LOT_RESIDUAL`, `NO_VALID_COMPETITOR`, `REALLOCATABLE_RESIDUAL` |
| Re-entry | `REENTRY_NOT_ELIGIBLE`, `REENTRY_RENEWED_EVIDENCE_INSUFFICIENT`, `REENTRY_CHURN_PROTECTION` |
| ADD | `ADD_NOT_INCREMENTALLY_COMPETITIVE`, `ADD_OPPORTUNITY_COST_FAIL`, `ADD_INCREMENTAL_VALUE_INSUFFICIENT` |

Reason codes must not encode future performance.

```text
CANONICAL_REASON_CODES_DEFINED = YES
REASON_CODE_CONTRACT_DEFINED = YES
```

## 17. No Duplicate Authority

Owner map:

| Semantic / decision | Owner |
| --- | --- |
| Market Quality | Market Context |
| Risk Pacing | Portfolio Policy |
| Re-entry eligibility integration | Portfolio Construction |
| ADD competitiveness | Portfolio Construction |
| Discrete quantity | Position Sizing |
| Safety cap | Safety |
| Submit feasibility | Submit / Broker Capability / Strategy Planning Authority as applicable |

```text
NEW_DUPLICATE_AUTHORITY_COUNT = 0
```

## 18. Legacy Compatibility / Migration Plan

| Producer / consumer | Current state | Target state | Migration required | Final consumer | Legacy consumer to remove |
| --- | --- | --- | --- | --- | --- |
| Market Context | Direction, breadth, volatility, confidence exist; Market Quality not explicit | Materialize Market Quality as separate evidence | YES | Portfolio Policy, BUY Quality, PC | none; do not replace direction |
| Portfolio Policy | Uses Market Context for posture | Produces Risk Pacing intent from Direction + Quality | YES | PC, BUY Quality | any legacy exposure-only shortcut |
| Portfolio Construction | Owns target portfolio; composition reasons exist but not a unified contract | Owns capital competition and final no-deployable-opportunity authority | YES | Position Sizing, Runtime Planning | legacy capital-deployment membership decisions |
| Position Sizing | Owns quantity / lot feasibility | Emits residual and lot evidence consumable by PC competition loop | YES | PC and Runtime Planning | any target-weight recreation |
| ADD bridge | Existing PM ADD to PC bridge | ADD participates as marginal capital competitor | YES | PC / Sizing | automatic ADD priority or automatic rejection |
| Re-entry | Existing semantic gates / cooldowns | Explicit semantic eligibility contract | YES | PC | blanket or unowned re-entry behavior |
| Safety | Independent hard guard | Unchanged hard boundary | NO | Runtime / Submit | n/a |
| Submit / Execution | Execution feasibility and order authority | Unchanged | NO | Ledger / Current | n/a |

```text
PERMANENT_LEGACY_FALLBACK_ALLOWED = NO
```

## 19. Implementation Surface Map

This map is for a later implementation task only.

| File / module | Current responsibility | Target responsibility | Change type | Authority impact | Migration dependencies | Test requirement |
| --- | --- | --- | --- | --- | --- | --- |
| `configs/strategy/market_context.json` | Market Direction config and PIT contract | Add Market Quality schema/config only if implementation chooses config-backed semantics | CONFIG DESIGN | Market Context evidence only | lineage definition | PIT / missing evidence tests |
| `src/ai_fund_lab_v2/strategy/market_context*` | Produce direction and component metrics | Produce Market Quality semantic state | PRODUCER | new evidence field, no new regime | config/schema | direction/quality separation tests |
| `src/ai_fund_lab_v2/strategy/portfolio_policy*` | Portfolio posture | Produce Risk Pacing intent | CONSUMER/PRODUCER | policy intent, no fixed exposure | Market Quality artifact | no fixed exposure/count tests |
| `src/ai_fund_lab_v2/strategy/buy_quality.py` | BUY Quality | Consume Market Quality as evidence only | CONSUMER | no action authority | Market Quality schema | weak opportunity not rescued by quality |
| `src/ai_fund_lab_v2/strategy/portfolio_construction.py` | Target portfolio, ADD bridge, re-entry, competition | Own explicit constraint composition and capital competition | PRODUCER/CONSUMER | final Strategy target authority | risk pacing, lot evidence | residual reallocation, ADD competition, re-entry tests |
| `src/ai_fund_lab_v2/strategy/position_sizing.py` | Quantity and lot feasibility | Preserve quantity authority; expose residual evidence | PRODUCER | no membership authority | PC contract | lot-first / no duplicate quantity tests |
| `src/ai_fund_lab_v2/strategy/runtime_planning.py` | Map quantities to runtime intent | Consume unchanged sizing output | CONSUMER | no Strategy decision | position sizing output | no recomputation tests |
| `src/ai_fund_lab_v2/runtime_v2/safety/*` | Safety hard guards | Unchanged | NONE | hard cap preserved | n/a | safety not weakened tests |
| `src/ai_fund_lab_v2/runtime_v2/submit/*` | Submit feasibility and broker side effects | Unchanged | NONE | submit authority preserved | n/a | submit no implicit fallback tests |

```text
IMPLEMENTATION_SURFACE_MAP_COMPLETE = PASS
```

## 20. Test Contract

Market Quality:

- PIT input boundary
- missing evidence fail-closed
- direction / quality separation
- short/medium conflict semantics
- sector participation lineage before production use

Risk Pacing:

- no fixed exposure assumption
- cautious deployment does not block SELL
- healthy deployment does not bypass Safety

Portfolio Construction / constraints:

- Strategy cap vs Safety hard cap
- lot-first discrete allocation
- residual reallocation
- no duplicate quantity decision
- valid Cash preservation
- candidate replacement competition

Re-entry:

- no blanket ban
- no blanket permission
- renewed eligibility path
- churn protection

ADD:

- PM intent can become nonzero ADD when evidence supports it
- ADD competes rather than automatically wins
- ADD can legitimately lose to BUY or Cash
- no future outcome input

Temporal / evidence:

- no Historical-result feedback
- no Paper Ledger / PnL input
- no future data

```text
TEST_CONTRACT_COMPLETE = PASS
```

## 21. Acceptance Invariants

```text
MARKET_REGIME_AUTHORITY_CHANGED = NO
SECOND_REGIME_CLASSIFIER_CREATED = NO
MARKET_DIRECTION_AND_MARKET_QUALITY_SEPARATED = YES
MARKET_QUALITY_OWNER = MARKET_CONTEXT
MARKET_CONTEXT_DIRECTLY_SETS_QUANTITY = NO
MARKET_CONTEXT_DIRECTLY_SETS_EXPOSURE_TARGET = NO
FUTURE_DATA_ALLOWED = NO
HISTORICAL_OUTCOME_ALLOWED_AS_RUNTIME_INPUT = NO
OUTCOME_OPTIMIZED_COMPOSITE_SCORE_CREATED = NO
RISK_PACING_OWNER = PORTFOLIO_POLICY
FIXED_EXPOSURE_TARGET_DEFINED = NO
FIXED_BUY_COUNT_DEFINED = NO
FIXED_POSITION_COUNT_DEFINED = NO
GRADUAL_RERISK_CONTRACT_DEFINED = YES
BOTTOM_PREDICTION_REQUIRED = NO
CONSTRAINT_COMPOSITION_OWNER = PORTFOLIO_CONSTRUCTION
FINAL_NO_DEPLOYABLE_OPPORTUNITY_AUTHORITY = PORTFOLIO_CONSTRUCTION_TARGET_PORTFOLIO_DECISION_AUTHORITY
STRATEGY_SAFETY_CAP_SEPARATION_PRESERVED = YES
SECOND_CAP_DECISION_CREATED = NO
LOT_FIRST_CONTRACT_PRESERVED = YES
LOT_AWARE_ARCHITECTURE_REPLACED = NO
BLANKET_REENTRY_BAN = NO
BLANKET_REENTRY_PERMISSION = NO
ADD_AUTOMATIC_PRIORITY = NO
ADD_AUTOMATIC_REJECTION = NO
CASH_REMAINS_VALID_ALLOCATION = YES
FIXED_MINIMUM_INVESTMENT = NO
FIXED_TARGET_POSITION_COUNT = NO
BUY_SELL_INDEPENDENCE_PRESERVED = YES
SELL_AUTHORITY_CHANGED = NO
WINNER_RETENTION_PHILOSOPHY_CHANGED = NO
FIXED_HOLDING_PERIOD_CREATED = NO
MARKET_QUALITY_FAIL_CLOSED = YES
IMPLICIT_HEALTHY_FALLBACK = NO
IMPLICIT_BULL_FALLBACK = NO
TEMPORAL_CONTRACT_EXPLICIT = YES
CURRENT_SNAPSHOT_NON_PIT_SOURCE_ALLOWED_FOR_HISTORICAL_DECISION = NO
EVIDENCE_ARTIFACT_FEEDBACK_LOOP_ALLOWED = NO
NEW_DUPLICATE_AUTHORITY_COUNT = 0
PERMANENT_LEGACY_FALLBACK_ALLOWED = NO
MARKET_CANDIDATE_INTERACTION_STAGE = BEFORE_FINAL_CAPITAL_WINNER
RISK_PACING_IS_SECOND_CANDIDATE_FILTER = NO
GRADUATED_WEAK_OPPORTUNITY_CLASS_DEFINED = YES
GRADUATED_WEAK_CLASS_STRUCTURALLY_REACHABLE = YES
MARKET_CANDIDATE_INTERACTION_MATRIX_DEFINED = YES
CAUTIOUS_GRADUAL_ECONOMIC_DIFFERENCE_DESIGNED = YES
STRONG_OPPORTUNITY_CAN_OVERRIDE_CAUTION = YES
BLANKET_MARKET_BUY_BAN = NO
CASH_IS_TRUE_ECONOMIC_COMPETITOR_DESIGNED = YES
CASH_CAN_WIN_BEFORE_CANDIDATE_FAILURE = YES
FIXED_EXPOSURE_TARGET_INTRODUCED = NO
RISK_PACING_FORCES_EXISTING_POSITION_EXIT = NO
ADD_MARKET_CANDIDATE_INTERACTION_DEFINED = YES
NEW_BUY_AUTOMATIC_PRIORITY = NO
REENTRY_CAPITAL_COMPETITION_CONSISTENT = YES
PROGRESSIVE_RERISKING_WITHOUT_FIXED_HOLD_PERIOD = YES
RECOVERY_QUALITY_ECONOMIC_DIFFERENCE_DESIGNED = YES
BULL_WEAK_INTERNALS_CAN_REDUCE_DEPLOYMENT = YES
BEAR_STRONG_OPPORTUNITY_CAN_DEPLOY = YES
INCOMPLETE_EVIDENCE_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED = YES
SECOND_DISCRETE_QUANTITY_AUTHORITY = NO
POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES
DOWNSTREAM_CAPITAL_REDECISION_ALLOWED = NO
ECONOMIC_BINDING_STATE_SPACE_COMPLETE = YES
SYNTHETIC_BINDING_ACCEPTANCE_MATRIX_DEFINED = YES
SAME_CANDIDATE_DIFFERENT_MARKET_CAN_CHANGE_DECISION = YES
SAME_MARKET_DIFFERENT_CANDIDATE_CAN_CHANGE_DECISION = YES
MARKET_QUALITY_ROLE = CAPITAL_PACING_CONTEXT
MARKET_QUALITY_HARD_BUY_GATE = NO
RISK_PACING_ROLE = CAPITAL_DEPLOYMENT_INTENSITY_AUTHORITY
RISK_PACING_BINARY_SECURITY_ADMISSION_OWNER = NO
GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION
CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION
CASH_PARTIAL_ALLOCATION_SUPPORTED = YES
CASH_WINNER_TAKES_ALL_REQUIRED = NO
CAPITAL_BUDGET_ENVELOPE_OWNER = PORTFOLIO_POLICY
CAPITAL_BUDGET_SEMANTICS_DEFINED = YES
MULTI_ASSET_CAPITAL_ALLOCATION_OWNER = PORTFOLIO_CONSTRUCTION
OPPORTUNITY_INFORMATION_PRESERVATION_REFINED = YES
OPPORTUNITY_QUALITY_REMAINS_CANONICAL_SUMMARY = YES
WITHIN_CLASS_ALLOCATION_EVIDENCE_AVAILABLE = YES
WEAK_MARKET_STRONG_STOCK_PARTICIPATION_SUPPORTED = YES
CAUTIOUS_MARGINAL_AUTOMATIC_ZERO = NO
NORMAL_MULTI_OPPORTUNITY_CAPTURE_SUPPORTED = YES
BOOTSTRAP_AND_RESIDUAL_CASH_DISTINGUISHED = YES
BOOTSTRAP_PARTICIPATION_PATH_DEFINED = YES
REDUCED_RISK_INITIAL_ENTRY_DEFINED = YES
LEGITIMATE_100_PERCENT_CASH_SUPPORTED = YES
FIXED_MARKET_EXPOSURE_TARGET_CREATED = NO
HISTORICAL_RETURN_DERIVED_ALLOCATION_PERCENTAGE_COUNT = 0
CANONICAL_MULTI_ALLOCATION_SEQUENCE_DEFINED = YES
MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES
ADD_MULTI_ALLOCATION_SUPPORTED = YES
REENTRY_MULTI_ALLOCATION_SUPPORTED = YES
REENTRY_SPECIAL_PENALTY = NO
WINNER_RETENTION_INDEPENDENCE_PRESERVED = YES
SAFETY_AUTHORITY_CHANGED = NO
EXPLORATION_VS_AVOIDABLE_LOSS_EVALUATION_CONTRACT_DEFINED = YES
PROFIT_ENGINE_PRESERVATION_ACCEPTANCE_DEFINED = YES
MARKET_PACING_SELECTIVITY_REQUIREMENT_DEFINED = YES
G43_BINDING_MATRIX_MIGRATION_CLASS = MIGRATE
SINGLE_DEPLOYMENT_SET_MIGRATION_CLASS = MIGRATE
G50_EXECUTABLE_BINDING_PRINCIPLE_PRESERVED = YES
LINEAGE_BINDING_DISTINCTION_PRESERVED = YES
STAGED_MIGRATION_PLAN_DEFINED = YES
BIG_BANG_IMPLEMENTATION_ALLOWED = NO
```

## 15. Phase31-G136 High-Resolution Capital Value / Rotation Reference

The enduring architecture for future high-resolution marginal capital value and
portfolio-wide rotation is defined in:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

This reference preserves the dual-path contract:

- Market Quality remains `CAPITAL_PACING_CONTEXT`.
- Risk Pacing remains `CAPITAL_DEPLOYMENT_INTENSITY_AUTHORITY`.
- Cash remains a first-class capital alternative.
- Portfolio Construction remains capital allocation owner.
- Position Sizing remains discrete quantity owner.
- Runtime must not re-decide ranking, Cash preference, target weight, or
  quantity.

High-resolution value must not become a fixed full-investment rule, a BULL
override, a second Candidate filter, or Historical-return-derived weighting.
Portfolio Rotation is a future staged capability and must not force existing
HOLD liquidation through the Risk Pacing or Runtime path.

## 16. Phase32-DG Tick Reliability Boundary

Phase32-DG adds tick-normalized trend and momentum confidence as opportunity
quality evidence before capital allocation.

This does not change the dual-path allocation boundary:

- Candidate/BQ/Strategy Intelligence may qualify whether apparent trend and
  momentum are robust to minimum-tick quantization.
- PC still owns target capital allocation and applies existing caps, budget,
  concentration, Cash, and lot-feasibility semantics.
- PS still owns executable quantity materialization.
- Runtime still consumes explicit upstream decisions without recomputing them.

Tick qualification is not a market-quality exposure dial and not a price bucket
rule. It prevents coarse one/few-tick price series from acting as clean
independent confirmation while preserving legitimate low-price opportunities
with acceptable or robust PIT tick structure.
