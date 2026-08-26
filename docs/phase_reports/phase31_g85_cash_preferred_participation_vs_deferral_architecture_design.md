# Phase31-G85 — CASH_PREFERRED Participation-vs-Deferral Architecture Design

## PRIMARY_JUDGMENT

PHASE31_G85_CASH_PREFERRED_PARTICIPATION_DEFERRAL_ARCHITECTURE_READY_FOR_IMPLEMENTATION

## Scope

Design-only architecture report.

- No code changes.
- No tests added or modified.
- No config, threshold, weight, Market Quality, Risk Pacing, Candidate ranking, BUY filter, PM, SELL, Position Sizing, or Runtime behavior changes.
- No fresh-run, resume, replay, or long Historical execution.
- No future information or Historical outcome parameter selection.

## Design Conclusion

`CASH_PREFERRED` must remain valid security-vs-Cash interaction evidence, but it must no longer be consumed directly as the final allocation action.

The architecture should separate:

```text
interaction_result
from
final participation / deferral action
```

The correct owner for the final distinction is Portfolio Construction, because PC already owns:

- security/Cash incremental capital competition
- final multi-allocation materialization
- target-weight authority
- aggregate portfolio impact
- Cash as a capital destination

Market Quality and Risk Pacing remain context and deployment intensity authorities. Candidate / BUY Quality remain per-security evidence producers. Position Sizing remains quantity owner. Runtime must not re-decide capital priority.

## Core Architecture Statement

A security candidate may be `CASH_PREFERRED` relative to full deployment without being economically worthless for reduced participation.

Therefore:

```text
CASH_PREFERRED -> security = 0
```

is too coarse.

But:

```text
CASH_PREFERRED -> positive security preserved
```

is also too coarse and would reintroduce the G80 weak-tail defect.

The missing design object is an explicit PC-owned participation-vs-deferral semantic derived from existing PIT evidence:

```text
market_candidate_cash_interaction.interaction_result = CASH_PREFERRED
-> PC participation/deferral resolution
-> final multi-allocation action
```

## Proposed Semantic Model

### State 1 — SECURITY_PREFERRED

Meaning:

Security evidence materially beats Cash under the current Risk Pacing / opportunity context.

Expected final action:

- positive security allocation allowed
- Cash may still coexist for residual / optional capital

Existing mappings:

- `DEPLOY_ELIGIBLE`
- `SELECTIVE_COMPETITION`

### State 2 — CASH_PREFERRED_PARTICIPATION_VALID

Meaning:

Cash is preferred over full deployment, but existing same-date PIT evidence supports reduced-risk security participation.

Expected final action:

- positive but reduced security allocation may survive
- Cash receives remaining budget
- no forced participation
- no fixed exposure / count / rank / confidence / score threshold
- aggregate participation must remain controlled

Canonical evidence basis:

- `interaction_result = CASH_PREFERRED`
- row-level opportunity evidence is still credible relative to same-date alternatives
- requested/accepted increment exists
- evidence is PIT-complete
- Portfolio Policy / Risk Pacing does not create a hard BUY gate
- aggregate marginal participation remains economically coherent

### State 3 — CASH_PREFERRED_DEFER

Meaning:

Optional Cash beats this incremental security opportunity.

Expected final action:

- security increment = 0
- requested increment preserved in deferral lineage
- capital returns to explicit Cash
- no hidden residual security fallback

Canonical evidence basis:

- `interaction_result = CASH_PREFERRED`
- row-level evidence is weak relative to same-date opportunity set, or
- aggregate marginal / weak-tail consumption would turn reduced rows into overdeployment, or
- required evidence for reduced participation is missing / malformed / stale

## Authority Separation

| Component | Owns | Must Not Own |
| --- | --- | --- |
| Market Quality | market-level structure and pacing context | individual security admission, final Cash-vs-security winner |
| Risk Pacing / Portfolio Policy | maximum deployable capital, deployment intensity, bootstrap/residual Cash state | forced budget fill, lower-ranked security target fulfillment |
| Candidate / BUY Quality | candidate evidence, rank, score, confidence, quality, entry/continuation semantics | portfolio Cash quantity |
| Market Candidate Cash Interaction | security-vs-Cash interaction evidence before final allocation | final target weight / quantity |
| Portfolio Construction | final participation-vs-deferral resolution, capital competition, target-weight materialization, aggregate marginal exposure | quantity, Runtime order priority redecision |
| Position Sizing | discrete lot quantity from PC allocation | capital priority redecision |
| Runtime | materialize PS/PC-authorized planning | Cash/security winner redecision |

## Evidence Model

G85 should not introduce a new score, model, or fitted threshold. The implementation should reuse existing PIT evidence.

### Row-Level Evidence

Used as candidate-local participation evidence:

- candidate rank
- runtime opportunity score
- confidence
- quality score
- canonical opportunity quality class
- entry state/action
- momentum
- relative strength
- construction priority
- requested / accepted weight
- expected edge / incremental investment evidence where available
- lot and cap feasibility evidence

Role:

Rows with credible same-date evidence may be eligible for `CASH_PREFERRED_PARTICIPATION_VALID`. Rows with weak / insufficient evidence should resolve to `CASH_PREFERRED_DEFER`.

This role is semantic, not a threshold formula.

### Opportunity-Set Context

Used to decide whether row evidence is meaningful in the current day's opportunity landscape:

- top1 / top3 / top10 opportunity quality
- median candidate quality
- top-vs-tail spread
- count of stronger candidates
- valid competitor count
- candidate-set richness / scarcity evidence already present

Role:

Identical row-level evidence may receive different capital intensity when same-date opportunity-set context differs. In a rich set, reduced participation may be acceptable for credible marginal candidates. In a weak/thin set, optional Cash should gain preference as marginal candidates accumulate.

### Aggregate Context

Used to prevent G80 recurrence:

- number of simultaneous `CASH_PREFERRED` rows
- aggregate requested `CASH_PREFERRED` weight
- aggregate marginal / weak-tail exposure
- security sleeve composition
- Cash coexistence
- portfolio occupancy / concentration

Role:

Per-row reduced participation is insufficient. PC final partition must reason about aggregate marginal capital consumption. A row may be participation-valid in isolation but still require deferral or further reduction when aggregate marginal allocation would consume too much of the capital budget relative to stronger opportunities and optional Cash.

This must not be a fixed aggregate percentage cap. It should derive from the same capital budget / Cash competition evidence and same-day opportunity-set composition.

### Portfolio Policy Context

Used as deployment context, not security admission:

- bootstrap state
- residual optionality state
- deployment capacity
- Risk Pacing
- Profit Engine preservation / exploration evidence

Role:

Bootstrap participation remains a special context already repaired by G83. Non-bootstrap participation must be resolved separately and must not borrow bootstrap semantics.

## Canonical Flow

| Stage | Producer | Consumer | Authority | Canonical Evidence | Fail-Closed Behavior | Fallback Prohibited |
| --- | --- | --- | --- | --- | --- | --- |
| Market Context / Market Quality | Market Context / MQ producer | Portfolio Policy, PC evidence consumers | Market evidence authority | market quality state, breadth, participation, recovery quality | incomplete evidence downgrades to cautious/insufficient context | hard BUY gate |
| Risk Pacing / Capital Budget MAX | Portfolio Policy | PC | Portfolio-level deployment intensity / maximum capital authority | `incremental_capital_budget_envelope.v1`, deployment capacity, Cash state | missing/stale/malformed envelope blocks deployment authority | forced capital deployment |
| Candidate / BUY Quality | Candidate / BUY Quality / Opportunity evidence producers | PC | per-security evidence authority | rank, score, confidence, quality, entry, continuation | missing candidate evidence cannot create participation-valid state | PC inventing rank/score |
| Market Candidate Cash Interaction | PC pre-final interaction builder | PC final partition | security-vs-Cash interaction evidence | `DEPLOY_ELIGIBLE`, `SELECTIVE_COMPETITION`, `CASH_PREFERRED`, reason codes | missing interaction fail-closed to no security allocation | treating Cash as residual only |
| Participation-vs-Deferral Resolution | PC final partition | PC multi-allocation | final capital allocation authority | row, opportunity-set, aggregate, Cash, budget evidence | explicit Cash unless reduced participation evidence is complete; no full deployment | universal zero-security or universal positive preservation |
| Final Multi-Allocation | PC | lot compatibility / PS | target-weight authority | security allocations, Cash allocation, deferrals, lineage | malformed final payload fail-closed downstream | downstream capital redecision |
| Lot Compatibility | PC evidence, PS later quantity owner | PS | compatibility evidence only in PC; quantity in PS | lot context, headroom, residual | unexecutable row scoped; no implicit promotion | PC quantity ownership |
| Position Sizing | PS | Runtime | discrete quantity authority | target quantity / quantity delta | missing/malformed PC lineage fail-closed | PS capital priority redecision |
| Runtime Planning | Runtime | Pending / Submit | planning materialization | PS quantity and PC lineage | missing/malformed authority no order / review as contracted | Runtime Cash/security winner redecision |

## Aggregate-Risk Design

G80 proved that many individually reduced `CASH_PREFERRED` rows can accumulate into excessive weak-tail exposure. G85 therefore requires a portfolio-level final partition step.

Design requirements:

- PC must evaluate the total requested weight of `CASH_PREFERRED` rows before publication.
- PC must preserve explicit Cash as a first-class competitor as marginal rows accumulate.
- PC may materialize reduced participation for credible rows while deferring weaker rows to Cash.
- PC must preserve deferral lineage for rows that lose to Cash.
- PC must not use a fixed aggregate percent cap in G85/G86.
- PC must not treat capital budget as a target that must be filled.

The intended semantic is:

```text
capital budget = maximum deployable capital
optional Cash = valid capital destination
aggregate marginal participation = PC-owned final allocation judgment
```

## Opportunity-Set Interaction

Identical row-level evidence can reasonably receive different capital intensity depending on the day's opportunity set.

This is permitted because PC is not changing Candidate ranking or inventing a new signal; PC is evaluating allocation quality under the current same-date capital competition.

Allowed behavior:

- rich opportunity set: credible marginal rows may retain reduced exploratory participation after stronger rows and Cash are considered
- weak / thin opportunity set: optional Cash gains preference as marginal rows accumulate
- mixed day: strong rows, participation-valid marginal rows, weak-tail marginal rows, and Cash can all coexist in one final allocation

Prohibited behavior:

- date-specific rule
- rank cutoff
- confidence cutoff
- score cutoff
- Historical outcome-fitted threshold
- blanket `COMPARABLE_MARGINAL` exclusion

## Bootstrap Preservation

G83 remains intact:

```text
EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP
+ valid opportunity
+ EXPLORATION_PARTICIPATION_RISK_PRESERVED
+ PROFIT_ENGINE_PRESERVATION_CONTEXT
-> reduced-risk participation may materialize
```

Bootstrap must not become a 100% Cash trap.

Bootstrap semantics must not leak into already-deployed weak-tail contexts. Non-bootstrap `CASH_PREFERRED_PARTICIPATION_VALID` requires its own PC final partition evidence and cannot be justified merely by bootstrap preservation.

## ADD Interaction

G74 ADD repair remains intact.

ADD, NEW_BUY, re-entry, and Cash must compete in the same incremental capital framework:

```text
best economically justified destination wins marginal capital
```

Design requirements:

- no ADD privilege merely because it is ADD
- no NEW_BUY privilege merely because it is NEW_BUY
- strong Winner ADD can beat weak NEW_BUY and Cash when same-date evidence supports it
- weak ADD can lose to credible NEW_BUY or Cash
- optional Cash can beat both when evidence does not justify deployment
- PM ADD intent remains directional intent; PC owns allocation; PS owns quantity; Runtime does not re-decide

## Strong-Period Preservation

The design is invalid if it suppresses the Profit Engine by broadly converting cautious marginal opportunities to Cash.

Must preserve:

- high-ranked / high-confidence marginal opportunity participation
- Profit Burst-style `COMPARABLE_MARGINAL` participation
- reduced participation under cautious market context
- multi-security allocation
- Cash + security coexistence
- weak-market / strong-stock participation

G84 evidence shows post-G83 suppressed rows were materially closer to normal participation than plateau weak-tail. The implementation must therefore be able to preserve those normal participation rows while still deferring G80 weak-tail rows.

## Fail-Closed Semantics

The design must avoid both bad extremes.

Bad fail-open:

```text
missing evidence -> buy weak security
```

Bad over-defense:

```text
missing evidence -> everything Cash forever
```

Required fail-closed behavior:

- Missing/stale/malformed budget envelope: no deployment authority.
- Missing/stale/malformed market/candidate/Cash interaction evidence: affected security row cannot be participation-valid.
- Missing row-level participation evidence: row defers to Cash, not full deployment.
- Missing opportunity-set / aggregate context: PC may preserve only already-authorized strong/selective rows; `CASH_PREFERRED` participation-valid resolution is unavailable.
- Bootstrap evidence complete under G83: reduced bootstrap participation may proceed.
- Non-bootstrap evidence incomplete: `CASH_PREFERRED_DEFER`, with lineage preserved.

This preserves Safety and Cash without turning Market Quality into a permanent hard BUY gate.

## Future Regression Design Cases

### Case A — 2022-10-03 Bootstrap

Expected:

- security > 0
- Cash > 0
- reduced-risk participation
- no forced exposure
- G83 bootstrap reason lineage preserved

### Case B — 2022-10-04 through 2022-10-19 Normal Participation

Use actual-producer-equivalent evidence.

Expected:

- high-quality participation-valid `CASH_PREFERRED` rows may remain positive
- weak rows may still defer
- Profit Engine does not collapse to roughly 5% exposure / one position
- no fixed count or fixed exposure assertion

### Case C — 2023-07 Weak-Tail

Expected:

- obvious weak-tail `CASH_PREFERRED` rows do not retain positive security allocation merely because `accepted_weight > 0`
- Cash wins relevant weak-tail increments
- G81 weak-tail protection preserved

### Case D — Mixed Day

Same day contains:

- strong security
- participation-valid marginal security
- weak-tail marginal security
- Cash

Expected:

- strong security allocated
- valid exploratory marginal may receive reduced capital
- weak tail deferred
- Cash remains explicit destination
- aggregate marginal exposure remains coherent

### Case E — ADD

Strong Winner ADD vs weak NEW_BUY vs Cash.

Expected:

- ADD competes using G74-repaired ADD authority
- weak NEW_BUY does not automatically beat ADD
- ADD does not automatically beat Cash
- PS quantity authority and Runtime binding preserved

### Case F — No Valid Opportunity

Expected:

- Cash allowed to receive all incremental capital
- no forced BUY
- no synthetic security fallback

## Architecture SoT To Update During Implementation Acceptance

When the implementation task passes, update the permanent common SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

The current G81/G83 language should be refined from:

```text
non-bootstrap CASH_PREFERRED -> zero-security weak-tail result
```

to:

```text
CASH_PREFERRED interaction evidence requires PC final participation-vs-deferral resolution.
Bootstrap participation, normal reduced participation, and weak-tail Cash deferral are separate final allocation semantics.
```

## Required Judgments

CASH_PREFERRED_SEMANTIC_REDESIGN_REQUIRED = YES

INTERACTION_RESULT_AND_ALLOCATION_ACTION_MUST_BE_SEPARATED = YES

PC_FINAL_PARTITION_AUTHORITY_OWNER_CONFIRMED = YES

ROW_LEVEL_EVIDENCE_ROLE = PARTICIPATION_CREDIBILITY_INPUT_NOT_STANDALONE_THRESHOLD

OPPORTUNITY_SET_CONTEXT_ROLE = SAME_DATE_RELATIVE_CAPITAL_CONTEXT_REQUIRED

AGGREGATE_CONTEXT_ROLE = WEAK_TAIL_ACCUMULATION_CONTROL_REQUIRED

OPTIONAL_CASH_AUTHORITY_ROLE = FIRST_CLASS_INCREMENTAL_CAPITAL_DESTINATION

BOOTSTRAP_SEMANTICS_PRESERVED = YES

G81_WEAK_TAIL_PROTECTION_PRESERVED_BY_DESIGN = YES

NORMAL_REDUCED_PARTICIPATION_PRESERVED_BY_DESIGN = YES

ADD_COMPETITION_PRESERVED = YES

NEW_FEATURE_REQUIRED = NO

NEW_NUMERIC_SCORE_REQUIRED = NO

HISTORICAL_THRESHOLD_REQUIRED = NO

ARCHITECTURE_READY_FOR_IMPLEMENTATION = YES

## Not Executed

CODE_CHANGED = NO

TESTS_CHANGED = NO

CONFIG_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

RISK_PACING_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

BUY_FILTER_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Next

Implement only the confirmed PC final partition boundary:

```text
market_candidate_cash_interaction
-> PC participation-vs-deferral resolution
-> canonical_multi_allocation_deployment_set
```

The implementation should reuse existing row-level, opportunity-set, aggregate, Cash, and budget evidence; preserve G81 and G83; and avoid new thresholds, scores, filters, or Market Quality redesign.
