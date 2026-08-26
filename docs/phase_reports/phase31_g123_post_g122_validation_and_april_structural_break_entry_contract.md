# Phase31-G123 — Post-G122 Fresh Validation Entry / April Structural-Break Audit Contract

## PRIMARY_JUDGMENT

PHASE31_G123_POST_G122_VALIDATION_ENTRY_CONTRACT_READY

## Scope

- Task type: READ-ONLY ENTRY CONTRACT
- Phase: Phase31
- Implementation changed: NO
- Config / threshold / weight changed: NO
- Fresh-run executed by Codex: NO
- Resume / replay / long Historical executed by Codex: NO
- Run state mutated: NO

G122 repaired canonical campaign ADD event/history materialization consumed by
downstream Strategy Intelligence. Therefore the pre-G122 long run remains useful
as historical characterization and defect evidence, but it is not current-system
performance authority.

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g120_post_g119_long_horizon_performance_capital_characterization.md`
- `docs/phase_reports/phase31_g121_campaign_level_add_identity_winner_scaling_audit.md`
- `docs/phase_reports/phase31_g122_campaign_lifecycle_add_event_history_materialization_repair.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase30_final_summary_and_phase31_handoff.md`

## Current Authority Map

| Area | Current SoT / Owner | G123 interpretation |
|---|---|---|
| Candidate production / ranking | Candidate / Opportunity path, Opportunity Ranking Authority | `runtime_opportunity_score` is relative opportunity evidence, not direct BUY authority, target weight, notional, or quantity. |
| Strategy Intelligence | `strategy_intelligence_architecture_v1.md` | PIT evidence layer for eligibility, continuation, risk, expected-edge evidence, campaign context, and action-specific consumers. |
| Campaign lifecycle | `positions/position_campaigns.json`, G122 SoT amendment | Additional BUY while campaign remains open is BUY_ADD on the same campaign; flat-after-exit BUY is re-entry / new campaign. |
| PM ADD / HOLD / REDUCE / EXIT | Strategy Architecture PM action contract | PM is existing-position directional Action Authority; ADD is intent / candidate, not direct order. |
| Market Quality | Market Context | Capital pacing context evidence only; not BUY/SELL/quantity/cash target authority. |
| Risk Pacing | Portfolio Policy | Deployment intensity / marginal capital willingness authority; not fixed exposure or hard security admission. |
| Capital budget envelope | Portfolio Policy | Maximum deployable incremental capital authority; not symbol, weight, or quantity selector. |
| Portfolio Construction | Portfolio Construction | Target membership, target weight, multi-security allocation, ADD/NEW shared capital competition, residual/Cash participation resolution. |
| Position Sizing | Position Sizing | Discrete quantity owner; does not reinterpret opportunity score or capital priority. |
| Runtime Planning | Runtime Planning / Strategy Planning Authority | Pure mapper / validator of upstream Strategy authority; no downstream capital priority redecision. |
| Temporal / PIT data authority | Runtime temporal contract, Historical Safety Temporal Authority | Business date, feature date, market date, current position state, valuation date, and safety freshness remain distinct PIT-bound authorities. |

## Validation Principle

```text
PRE_G122_LONG_RUN_IS_CURRENT_PERFORMANCE_AUTHORITY = NO
POST_HOC_OUTCOME_USED_AS_PARAMETER_AUTHORITY = NO
```

The next performance authority for the current Strategy behavior must be a clean
Post-G122 fresh validation run operated by the user. Historical outcome must not
select thresholds, weights, features, filters, score cutoffs, allocation
percentages, regime preferences, or Market Quality parameters.

G120 and G121 remain valid as:

- pre-G122 performance characterization
- campaign lifecycle defect discovery evidence
- anchor definitions for Post-G122 validation gates

They must not be reused as current-system ADD funnel counts or current-system
performance truth.

## Operator-Run Contract

Codex must not execute this command. The operator/user runs exactly this command
when ready:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 650 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

```text
USER_OPERATED_COMMAND_PROVIDED = YES
CODEX_EXECUTES_COMMAND = NO
COMMAND_PROFILE = historical-extended-smoke
COMMAND_START_DATE = 2022-10-03
COMMAND_BUSINESS_DAYS = 650
COMMAND_INITIAL_CASH = 1000000
COMMAND_JSON_MODE = NO
```

## Early Actual-Path Acceptance Anchors

Before the Post-G122 run is used for performance judgment, completed artifacts
must prove G122 is active in the actual runtime path.

Required anchors:

| Anchor | Expected actual-path semantics | Gate |
|---|---|---|
| 2022-10-12 / 94320 | Initial BUY plus true ADD, same campaign identity, BUY history count 2, ADD history count 1 | `POST_G122_94320_ACTUAL_GATE = PASS/FAIL` |
| 2022-10-12 / 94340 and 2022-10-13 / 94340 | Initial BUY plus two true ADDs, same campaign identity, BUY history count 3, ADD history count 2 | `POST_G122_94340_ACTUAL_GATE = PASS/FAIL` |

Do not require performance divergence from the pre-G122 run. The gate verifies
campaign lifecycle correctness, not return.

## Re-Entry Control

At least one later repeated BUY after the symbol was flat must remain a new
campaign, not merged into a prior closed campaign.

Suggested controls:

- `76470`
- `93180`
- `21340`
- `59550`

Required:

```text
POST_G122_REENTRY_SEPARATION_GATE = PASS/FAIL
```

## ADD Funnel Recapture

Once enough Post-G122 completed dates exist, recompute the ADD funnel from the
new run only.

Required stages:

```text
held-position evaluations
PM ADD intents
ADD_MARGINAL_PREFERRED
COMPARABLE_MARGINAL
CASH_MARGINAL_PREFERRED
INSUFFICIENT_EVIDENCE
authorized increment
PS BUY_ADD
Runtime BUY_ADD
Fill
```

G121's `202` PM ADD intents and `190` `INSUFFICIENT_EVIDENCE` outcomes are not
current-system truth after G122. They are only comparison anchors.

```text
POST_G122_ADD_FUNNEL_RECOMPUTED = NO
```

The value is `NO` at G123 entry time because the new Post-G122 run has not been
operator-executed and audited yet.

## April Structural-Break Trigger

Do not assume old April stagnation reproduces.

Descriptive windows for the next audit:

| Window | Dates | Purpose |
|---|---|---|
| PRE | 2022-10-03 through 2023-03-31 | Profit-engine build-up / pre-break behavior |
| TRANSITION | 2023-04-03 through 2023-04-28 | April structural-change candidate window |
| POST | 2023-05-01 onward | Persistence or recovery after transition |

Compare only when the Post-G122 run reaches sufficient completed artifacts:

- equity accumulation
- market regime
- Market Quality
- exposure
- Cash
- BUY_NEW
- PM ADD
- actual BUY_ADD
- REDUCE
- EXIT

```text
POST_G122_APRIL_STAGNATION_REPRODUCED = NOT_REACHED
APRIL_STRUCTURAL_AUDIT_READY = YES_AFTER_NEW_RUN_REACHES_WINDOW
```

## If April Stagnation Reproduces

Run the next audit READ-ONLY in this exact direction:

```text
DATA
-> EVIDENCE
-> STRATEGY DECISION
-> CAPITAL ALLOCATION
-> EXECUTION
```

Required subsystems:

| Layer | Required audit |
|---|---|
| A. Raw data completeness | Coverage, missing dates/symbols, NULL, NaN, stale, insufficient history, invalid rows, fallback, fail-closed, schema/version. |
| B. PIT / temporal continuity | Business date, feature date, market data date, current position state date, valuation date, accepted generation, and safety temporal authority. |
| C. Feature availability | Candidate / Opportunity / Strategy Intelligence input coverage and freshness. |
| D. Candidate universe / score dispersion | Count, rank, confidence, score distribution, quality class, and whether opportunity differentiation collapsed. |
| E. Market Quality evidence | State, transition, breadth/participation inputs, missing/fail-closed evidence. |
| F. Risk Pacing evidence | Portfolio Policy intent, budget envelope state, and capital deployment intensity. |
| G. PM action distribution | HOLD / ADD / REDUCE / EXIT counts and reasons by campaign/date. |
| H. ADD evidence completeness | Campaign context, lot context, position-size context, NEW_BUY comparison, other ADD comparison, Cash/residual, headroom/cap, Market/Candidate context. |
| I. Winner recognition | Whether true Winners are identified from PIT campaign evidence and whether ADD/HOLD follows canonical philosophy. |
| J. Capital competition | PC allocation, Cash partition, residual reconsideration, ADD/NEW competition, G97/G99/G102/G115/G119 lineage. |
| K. BUY_NEW behavior | Entry quality, participation, marginal expansion, and Runtime materialization. |
| L. HOLD / REDUCE / EXIT behavior | Continuation, deterioration, preservation, giveback, churn, and SELL independence. |
| M. Authority / consumer propagation | PC -> PS -> Runtime -> Pending -> Submit -> Execution binding without redecision. |

## Data Completeness Gate

For every production-used input family, compare PRE / TRANSITION / POST:

```text
coverage
missing dates
missing symbols
NULL
NaN
STALE
INSUFFICIENT_HISTORY
INVALID
fallback
fail-closed
schema/version
```

Required:

```text
MATERIAL_DATA_COVERAGE_BREAK_FOUND = YES/NO
```

The next audit must stop Strategy causality claims if a material measurement or
input-coverage break is found.

## ADD Evidence Priority

Because G121 observed many `INSUFFICIENT_EVIDENCE` outcomes, the Post-G122
audit must trace each insufficient ADD result to producer availability, not just
copy the status string.

Required table:

```text
POST_G122_ADD_INSUFFICIENT_REASON_COUNTS =
campaign context
lot context
position-size context
NEW_BUY comparison
other ADD comparison
Cash/residual
headroom/cap
Market/Candidate context
other canonical evidence
```

At G123 entry time:

```text
POST_G122_ADD_INSUFFICIENT_REASON_COUNTS = NOT_AVAILABLE_UNTIL_POST_G122_RUN
```

## Regime Study Constraint

If April stagnation survives G122, regime characterization may compare:

- BULL winning episodes
- BULL losing / stagnant episodes
- RANGE winning episodes

Decision-time comparison may include candidate differentiation, Market Quality,
exposure, Cash, BUY_NEW, ADD intent, actual ADD, and Winner concentration.

Forbidden:

- BULL filter
- RANGE preference
- regime-specific thresholds
- outcome-derived parameter tuning

```text
REGIME_PERFORMANCE_USED_AS_PARAMETER_AUTHORITY = NO
```

## Philosophy Conformance Frame

The next audit's primary question is whether the system continued to act
according to the investment philosophy:

- BUY confirmed strength
- identify true Winners
- ADD when the next increment deserves capital
- preserve strong Winner
- REDUCE / EXIT when momentum or expected edge deteriorates
- hold Cash when no worthwhile opportunity exists
- Runtime follows Strategy authority

At G123 entry time, before the Post-G122 run:

```text
PRE_BREAK_PHILOSOPHY_CONFORMANCE = NOT_EVALUATED_UNTIL_POST_G122_RUN
POST_BREAK_PHILOSOPHY_CONFORMANCE = NOT_EVALUATED_UNTIL_POST_G122_RUN
```

## Defect Versus Market Reality

Any observed structural shift in the Post-G122 run must be classified as one or
more of:

| Class | Meaning |
|---|---|
| A | genuine market / opportunity shift |
| B | raw data defect |
| C | evidence availability defect |
| D | temporal / PIT defect |
| E | Strategy semantic defect |
| F | authority / consumer defect |
| G | campaign lifecycle defect |
| H | normal variation |
| I | mixed |

Do not repair class `A` or `H` merely because return is lower.

## Required Sequencing Judgment

```text
READY_FOR_POST_G122_FRESH_VALIDATION = YES
POST_G122_LONG_RUN_REQUIRED = YES
OLD_RUN_VALID_FOR_CURRENT_PERFORMANCE_JUDGMENT = NO
APRIL_STRUCTURAL_AUDIT_READY = YES_AFTER_NEW_RUN_REACHES_WINDOW
```

## Required Outputs

```text
PRIMARY_JUDGMENT = PHASE31_G123_POST_G122_VALIDATION_ENTRY_CONTRACT_READY
PRE_G122_LONG_RUN_IS_CURRENT_PERFORMANCE_AUTHORITY = NO
POST_HOC_OUTCOME_USED_AS_PARAMETER_AUTHORITY = NO
READY_FOR_POST_G122_FRESH_VALIDATION = YES
POST_G122_LONG_RUN_REQUIRED = YES
OLD_RUN_VALID_FOR_CURRENT_PERFORMANCE_JUDGMENT = NO
APRIL_STRUCTURAL_AUDIT_READY = YES_AFTER_NEW_RUN_REACHES_WINDOW
POST_G122_94320_ACTUAL_GATE = PENDING_OPERATOR_RUN
POST_G122_94340_ACTUAL_GATE = PENDING_OPERATOR_RUN
POST_G122_REENTRY_SEPARATION_GATE = PENDING_OPERATOR_RUN
POST_G122_ADD_FUNNEL_RECOMPUTED = NO
POST_G122_APRIL_STAGNATION_REPRODUCED = NOT_REACHED
MATERIAL_DATA_COVERAGE_BREAK_FOUND = NOT_EVALUATED_UNTIL_POST_G122_RUN
REGIME_PERFORMANCE_USED_AS_PARAMETER_AUTHORITY = NO
PRE_BREAK_PHILOSOPHY_CONFORMANCE = NOT_EVALUATED_UNTIL_POST_G122_RUN
POST_BREAK_PHILOSOPHY_CONFORMANCE = NOT_EVALUATED_UNTIL_POST_G122_RUN
CODE_CHANGED = NO
CONFIG_CHANGED = NO
FRESH_RUN_EXECUTED_BY_CODEX = NO
RESUME_EXECUTED_BY_CODEX = NO
REPLAY_EXECUTED_BY_CODEX = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
RUN_MUTATED_BY_CODEX = NO
```

## Next

The operator should run the single command above. After the run completes enough
early dates, first audit the G122 actual-path anchors. Only after the run
reaches April / post-April evidence should a structural-break root-cause audit
start.
