# Phase32-FQ Capital Priority Architecture / Regression-Invariant Design Audit

## Scope

- Audit type: Architecture / Design / READ-ONLY.
- Target evidence context: Phase32-FO / FP on `runtime-test-historical-extended-smoke-20260903T213011268067Z`, freeze `2023-08-03`.
- Required references read: Phase32-FO, FP, FC, FG/FH, FJ, FK, FL, FM/FN, Strategy Architecture, Runtime Architecture, Portfolio Construction / Position Sizing contract, Market-Candidate-Cash contract, current `portfolio_construction.py`, `marginal_capital_value.py`, `position_management.py`, and `position_sizing.py`.

No Production, SHADOW, source, config, schema, runtime state, Pending, or Ledger mutation was performed. No fresh-run, resume, recover, or replay was executed.

This report does not choose Production thresholds, weights, ranks, or parameters from Historical performance.

## Current Capital Priority Authority Graph

`CURRENT_CAPITAL_PRIORITY_AUTHORITY_GRAPH_COMPLETE`: YES.

| Stage | Producer | Consumer | Authoritative field / class | Hard gate | Soft evidence / metadata | Decision owner |
|---|---|---|---|---|---|---|
| Candidate / Opportunity | Runtime BUY AI / Opportunity Ranking | BQ, PC | `opportunity_buy_rank` / `buy_rank`, copied as `input_opportunity_rank` | missing/conflicting rank => review/reject | rank, score, candidate order | Opportunity producer |
| BUY Quality | `strategy.buy_quality` | PC / PS lineage | `quality_band`, `quality_action`, `quality_score` | reject/review/wait | component scores, relative opportunity, signal, market, execution, portfolio fit | BQ |
| Entry | Strategy Intelligence | PC / MCV | `entry_admission_action`, `entry_admission_state`, sufficiency | invalid/review/wait blocks admission | continuation, downside, tick trend, momentum | Entry / Strategy Intelligence |
| PM current position | Runtime/Strategy PM | PC | `HOLD` / `ADD` / `REDUCE` / `EXIT`, campaign id, PM decision id | SELL/EXIT independent, invalid campaign fails closed | confidence, reason codes, current return | PM |
| ADD worthiness | Strategy Intelligence / PM / PC bridge | MCV / PC | `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, `NO_ADD` | campaign missing, CQ fail, risk block, add/reduce history caps | continuation, no-loss averaging, expected edge, headroom | PM for intent, PC for capital integration |
| Cash evidence | Portfolio Policy / PC Cash competitor | PC | `market_candidate_cash_interaction`, `CASH_PREFERRED`, `CASH_PREFERRED_DEFER/PARTICIPATION_VALID` | insufficient/stale cash authority fail closed | market/risk/portfolio/cash optionality | PC |
| MCV | `strategy.marginal_capital_value` | PC | `marginal_capital_value_class`, `canonical_marginal_capital_priority_index`, `opportunity_quality_class` | insufficient comparison => review/blocked or stable order | rank, score, BQ, Entry, ADD value/cost/headroom | MCV under PC ownership |
| PC | `strategy.portfolio_construction` | PS / Runtime | `target_weight`, `accepted_buy_new_weight`, `accepted_incremental_weight`, deployment set | risk/cap/broker/cash/eligibility | membership, capital competition, residual budget | PC |
| PS | `strategy.position_sizing` | Runtime Planning | quantity, target notional, lot/cap authorization | lot, price, cap, current quantity, G129 ADD economics | rounding evidence | PS |
| Runtime / Pending | Runtime Planning / Submit | Broker/Historical execution | Pending order identity, source decision, campaign, quantity | safety, duplicate, CA, stale authority | lineage | Runtime |

## Where Comparability Breaks

`BUY_NEW_ADD_CASH_COMPARABILITY_BREAK_IDENTIFIED`: YES.

| Boundary | BUY_NEW | BUY_ADD | CASH | Break |
|---|---|---|---|---|
| Pre-admission | Candidate/BQ/Entry driven | PM ADD intent plus current-position lifecycle | portfolio/risk optionality | Different producers and eligibility semantics are correct. |
| MCV entry | Already-eligible BUY_NEW reaches MCV | Already-positive or ADD-worthy incumbent reaches MCV | Cash enters as competitor evidence | ADD has more pre-MCV gates, especially campaign-local history/no-loss/headroom. |
| MCV class | `STRONG/COMPARABLE_*` from BQ/Entry/rank | `STRONG/COMPARABLE_*` from ADD edge/cost/worthiness | Cash preference from market/risk/cash | Comparable but coarse; numeric rank/score and ADD depth are not fully symmetric. |
| PC final | accepted weights / target portfolio | accepted incremental weight | deferral or participation | PC owns final decision; Cash is not blanket hard winner. |
| PS quantity | BUY_NEW target delta from zero | BUY_ADD increment over current quantity | no quantity | Feasibility is intentionally asymmetric. |

Comparability is therefore feasible after hard eligibility, but current Production compresses priority before final allocation.

## Priority Information Compression Map

`PRIORITY_INFORMATION_COMPRESSION_IDENTIFIED`: YES.

| Evidence | Compression point | Current representation | Classification |
|---|---|---|---|
| Numeric opportunity rank | BQ/MCV/PC | preserved as `input_opportunity_rank`; not fixed top-N | D. still available but non-binding |
| Raw opportunity score | BQ/MCV | uncalibrated support, not expected return | A. intentionally replaced |
| BQ band/action | MCV | `STRONG` / `COMPARABLE_*` and legacy `ELIGIBLE_*` | B/C. represented but coarsened |
| Entry state | MCV | `BUY_NEW_ALLOWED` can lift lower-rank rows | B. represented |
| Expected edge | ADD MCV path | explicit ADD evidence where available; economic units often unavailable | D. available but incomplete |
| ADD worthiness | PM/SI/PC | `ADD_ALLOWED`, `ADD_REDUCED_ONLY`, `NO_ADD` | B/C. represented but hard-gated early |
| Cash optionality | PC cash interaction | `CASH_PREFERRED` then participation/deferral | D. available but not always binding |
| Lot/headroom | PC/PS | accepted weight then discrete quantity | A. intentionally separated |

The material compression is not that rank disappears. The issue is that rank and current evidence are reduced into broad classes where rank 1 and rank 39 can both compete through coarse `ELIGIBLE_*` semantics when other evidence differs.

## Unified Next-Capital-Unit Feasibility

`UNIFIED_NEXT_CAPITAL_UNIT_FEASIBLE`: YES.

`EXISTING_EVIDENCE_SUFFICIENT`: YES_FOR_SHADOW / PARTIAL_FOR_PRODUCTION.

Existing PIT evidence is sufficient to build a SHADOW comparator without new model features:

- opportunity rank and uncalibrated score
- BQ band/action/component status
- Entry admission state/action/sufficiency
- MCV class and source evidence
- current position/campaign/headroom/current weight
- ADD worthiness, no-loss-averaging, continuation, downside
- lot/cap/liquidity feasibility
- market/regime/risk pacing intent
- cash optionality and `CASH_PREFERRED` participation-vs-deferral evidence

Production promotion should wait for shadow acceptance because current evidence is heterogeneous and not calibrated into one economic unit.

`NEW_MODEL_REQUIRED`: NO.

`NEW_THRESHOLD_REQUIRED`: NO for design/shadow. Production may later need policy values, but FQ does not select them.

`FIXED_TOP_N_REQUIRED`: NO.

## Eligibility vs Priority Contract

Architecture must split:

```text
hard eligibility
-> comparable capital option materialization
-> next-capital-unit priority
-> PC accepted increment
-> PS executable quantity
```

Hard eligibility remains owned by existing producers:

- BUY_NEW: candidate/BQ/Entry/risk/broker/CA/recent-exit guard.
- BUY_ADD: PM ADD intent, campaign identity, no-loss-averaging, continuation, downside, cap/headroom/liquidity.
- Cash: valid run/date/risk/cash authority.

Capital priority should only compare options that have passed the relevant hard eligibility gates. It must not resurrect rejected BUY_NEW, blocked ADD, stale REENTRY, reviewed CA, or invalid cash authority.

## Preservation Invariants

`G129_PRESERVABLE`: YES. BUY_ADD quantity remains PC/PS order-increment scoped; PM ADD does not directly create a positive quantity.

`REENTRY_EW_EZ_PRESERVABLE`: YES. Do not revive `semantic_buy_type=REENTRY`; former REENTRY-like flat symbols remain BUY_NEW subject to bounded recent-exit guard.

`FAST_RISK_ON_PRESERVABLE`: YES. Strong BUY_NEW remains immediately deployable when current PIT evidence is strong.

`SELL_PM_PRESERVABLE`: YES. PM SELL/REDUCE/EXIT/profit-retention semantics are out of scope; capital priority is BUY-side PC/MCV only.

`CAMPAIGN_IDENTITY_PRESERVABLE`: YES. Current campaign identity remains PM/PC/PS/Runtime lineage, not recomputed by comparator.

`LONG_LIVED_HISTORY_BIAS_AVOIDABLE`: YES. Comparator must consume current campaign state and bounded recent-exit guard only; old ownership history must not become priority penalty.

## MCV / PC / PM / Sizing Boundary

`MCV_KEEP_EXTEND_REPLACE`: EXTEND.

Reason:

- KEEP unchanged leaves FP's priority compression unresolved.
- REPLACE is too large and risks G129/REENTRY/Runtime regressions.
- EXTEND can reuse existing MCV fields and add a SHADOW `next_capital_unit_comparison` layer with finer priority evidence.

`PC_RESPONSIBILITY_BOUNDARY_CLEAR`: YES. PC owns membership, capital competition, Cash participation/deferral, accepted weight/increment, and final deployment set.

`PM_RESPONSIBILITY_BOUNDARY_CLEAR`: YES. PM owns current-position lifecycle intent and ADD materialization inputs. PM must not consume BUY_NEW candidates or cross-option capital competition.

`SIZING_RESPONSIBILITY_BOUNDARY_CLEAR`: YES. PS owns quantity/notional/lot/cap materialization after PC priority. PS must not reinterpret rank, Cash, or marginal priority.

Five-ADD cap isolation: `prior_add_history_limits_incremental_add` remains unchanged in FQ. It is a known campaign-local ADD cap and a separate future design boundary.

Profit-retention isolation: no SELL/HOLD/REDUCE/EXIT semantics are changed by this design.

## Golden Case Set

`GOLDEN_CASE_SET_DEFINED`: YES.

These cases should be frozen as regression fixtures before shadow or Production work:

### Strong BUY_NEW

| Date | Symbol | Invariant |
|---|---|---|
| 2023-03-22 | 67750 | Strong/healthy BUY_NEW remains eligible under cautious/recovery conditions. |
| 2023-04-11 | 27210 | Comparable-high healthy BUY_NEW remains deployable. |
| 2023-04-11 | 45980 | Comparable-high healthy BUY_NEW remains deployable. |
| 2023-04-24 | 69270 | Strong BUY_NEW remains fast risk-on deployable. |
| 2023-07-25 | 67310 | High-rank BUY_NEW remains eligible; comparator may reprioritize only with explicit same-date evidence. |

### Strong BUY_ADD / G129

| Date | Symbol | Invariant |
|---|---|---|
| 2023-03-30 | 43880 | Post-deterioration re-ADD with current PASS evidence remains eligible. |
| 2023-04-04 | 83060 | ADD remains order-increment scoped and campaign-bound. |
| 2023-06-13 | 21340 | Positive ADD remains G129-safe and no-loss-averaging compliant. |
| 2023-06-13 | 76470 | If ADD is cap-blocked, comparator must not bypass cap. |
| 2023-07-25 | 94320 | Higher-ranked incumbent with no accepted increment remains lineage-preserved, not silently converted to BUY_NEW. |

### Cash / no-buy

| Case | Invariant |
|---|---|
| CAUTIOUS `CASH_PREFERRED_DEFER` rows | Remain zero-weight deferrals. |
| CAUTIOUS `CASH_PREFERRED_PARTICIPATION_VALID` rows | May retain reduced participation only with explicit PC lineage. |
| Missing cash authority | Fail closed / review, no synthetic Cash score. |
| Residual optionality state | Cash is a real option, not only leftover. |
| Near-empty bootstrap | Reduced participation may remain valid only under bootstrap contract. |

### Recent-exit / hard-risk / lot-cap

| Case | Invariant |
|---|---|
| 83060 recent-exit guard | Bounded guard remains active when applicable; no REENTRY semantic revival. |
| Hard downside/risk block | Remains block, not priority downgrade. |
| Corporate action review | Remains non-submittable until resolved. |
| Lot-infeasible target | Remains PS/PC zero or review. |
| Safety cap / liquidity cap | Remains hard feasibility boundary. |

`GOLDEN_CASE_REGRESSION_RISK`: MEDIUM. Risk is manageable if implemented shadow-first inside PC/MCV without touching producers or Runtime.

## Problem Case Set

`PROBLEM_CASE_SET_DEFINED`: YES.

| Date | Case | Desired semantic in future shadow |
|---|---|---|
| 2023-06-05 | 31920 rank23 BUY_NEW | Compare against higher-ranked incumbents and zero-increment ADD rows without losing rank/current evidence. |
| 2023-06-05 | 75380 rank24 BUY_NEW | Same-day breadth case with many higher-ranked rows. |
| 2023-06-07 | 65570 rank35 BUY_NEW | Deep rank allocation under high exposure. |
| 2023-06-12 | 37470 rank41 BUY_NEW | Deep rank BUY_NEW with top candidates above. |
| 2023-07-25 | 72770 rank39 BUY_NEW | LOW BQ but healthy Entry/MCV STRONG; inspect rank-vs-entry tradeoff. |
| 2023-07-25 | 94320 / 76470 | Higher-ranked incumbents with ADD-like evidence but zero accepted increment. |
| 2023-06-27 | 67310 rank2 large starter | Loss-containment/sizing golden-problem hybrid; not a deep-rank issue. |

Problem cases must not be judged by later PnL. The question is whether current PIT evidence can expose the priority tradeoff more precisely.

## Regression Risk Classification

| Area | Risk | Guard |
|---|---|---|
| Candidate | LOW | Read-only inputs, no rank producer change. |
| BQ | LOW | Consume existing fields only. |
| Entry | LOW-MEDIUM | Preserve hard blocks; use state as evidence only. |
| PM | MEDIUM | Do not push BUY_NEW into PM; ADD intent unchanged. |
| PC | HIGH | Final allocation owner; shadow-first required. |
| MCV | HIGH | Comparator lives here/near here; class mapping changes are risky. |
| Cash | MEDIUM-HIGH | Must avoid new blanket cash bias. |
| Sizing | MEDIUM | No priority reinterpretation; quantity-only boundary. |
| Runtime | MEDIUM | Should be unaffected until Production promotion. |
| Campaign identity | MEDIUM | Must keep lineage and campaign id unchanged. |
| Recent-exit guard | MEDIUM | Must not revive REENTRY. |
| Risk Pacing | MEDIUM | Keep fast strong deployment. |
| ADD | HIGH | G129, no-loss, cap/headroom must hold. |
| SELL/PM sell | LOW | Out of scope and must remain untouched. |

## Semantic Blast Radius

Future Production promotion could affect:

- PC `portfolio_members`
- PC `capital_competition`
- MCV `marginal_capital_value_authority`
- accepted `target_weight`
- accepted `accepted_buy_new_weight`
- accepted `accepted_incremental_weight`
- Cash `participation_valid` vs `defer`
- PS positive quantity rows due changed PC weights
- Runtime Planning BUY_NEW/BUY_ADD order presence and quantity
- Pending BUY items
- fills/ledger/campaign trajectories downstream
- Historical, Demo, and Production paths because this is common Strategy/Runtime contract
- tests and SoT documents for PC/MCV/Cash/G129/recent-exit/Runtime planning

Shadow implementation should add observability first without changing these Production outputs.

## No-Regression Acceptance Contract

`SHADOW_ACCEPTANCE_CONTRACT_DEFINED`: YES.

Before any Production promotion:

1. PIT-only evidence preserved; no future/PnL/outcome feature.
2. Strong BUY_NEW golden cases unchanged.
3. BUY_ADD G129 tests and actual-path fixtures pass.
4. EW/EZ/FA/FB recent-exit/REENTRY acceptance preserved.
5. Hard risk, CA, broker, lot, cap, liquidity blocks remain hard.
6. SELL/PM SELL output unchanged.
7. Campaign identity/provenance unchanged.
8. Cash participates as option, but no blanket cash-wins bias.
9. No fixed top-N gate.
10. No fixed exposure target or cooldown.
11. No new long-lived history penalty.
12. Shadow problem cases expose priority tradeoffs with explicit same-date evidence.
13. Golden Case regressions = 0.
14. Correctness regression = 0.
15. Priority inversion explanations are complete and auditable.

## Shadow-First Design

`SHADOW_FIRST_FEASIBLE`: YES.

Recommended shadow artifact:

```text
next_capital_unit_comparison.v1
```

Proposed row fields:

```text
business_date
candidate_type                 # BUY_NEW / BUY_ADD / CASH
symbol
campaign_id
hard_eligibility_status
hard_eligibility_reason_codes
current_priority_evidence
capital_value_class            # STRONG / COMPARABLE_HIGH / COMPARABLE_MARGINAL / WEAK_VALID / CASH_OPTIONALITY / BLOCKED / INSUFFICIENT
rank_evidence
bq_evidence
entry_evidence
add_evidence
headroom_evidence
cash_competitor_evidence
current_production_result
shadow_priority_rank
shadow_priority_reason_codes
would_change_production_if_promoted
future_information_used=false
historical_outcome_used=false
authoritative_consumer_count=0
```

Shadow metrics:

- rank20+ BUY_NEW selected count/share
- higher-ranked incumbent ADD competitor exists
- stronger ADD vs weaker BUY_NEW priority inversion count
- Cash preferred positive-security participation count
- Cash deferral candidate count
- hard-eligibility blocked but priority-positive attempted count
- unexplained priority inversion count
- G129-sensitive ADD rows touched by shadow
- recent-exit guard rows touched by shadow
- golden case regression count

## Minimal Production Slice

`MINIMAL_PRODUCTION_SLICE_IDENTIFIED`: YES.

Recommended after shadow acceptance:

```text
A+B hybrid:
Extend MCV with finer next-capital-unit evidence
inside PC's existing capital competition boundary.
```

Do not change Candidate, BQ, Entry, PM, PS, Runtime, SELL, recent-exit guard, or accepted artifact validation in the first Production slice.

Avoid:

- full rewrite of PC
- new alpha model
- fixed rank cutoff
- fixed exposure ramp
- permanent legacy fallback
- BUY_ADD preferential bonus
- Cash blanket winner rule

`ROLLBACK_BOUNDARY_DEFINED`: YES. Keep the future implementation isolated behind one PC/MCV comparator call and one artifact field family. Revert should restore previous PC accepted weights and MCV class consumption without touching upstream producers or Runtime state. Legacy fallback may exist only during validation; accepted implementation should not keep dual Production consumers indefinitely.

## Architecture SoT Update Plan

`ARCHITECTURE_SOT_UPDATE_PLAN_COMPLETE`: YES.

If design is accepted, update:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- Runtime Architecture only if Pending/Runtime lineage fields change after Production promotion
- Focused test contract docs for G129, recent-exit guard, Cash, PC/MCV, and PS no-priority-reinterpretation

## Implementation Sequence

Recommended sequence:

```text
Design acceptance
-> Shadow implementation only
-> Focused regression
-> Shadow actual-path inspection on FO/FP problem windows
-> User/ChatGPT review
-> Production implementation approval
-> Focused Production regression
-> User fresh-run / long validation
```

No Production implementation should begin from FQ alone.

## Go / No-Go

`ARCHITECTURE_DESIGN_SOUND`: YES.

`REGRESSION_RISK_ACCEPTABLE`: YES_FOR_SHADOW / NO_FOR_DIRECT_PRODUCTION.

`SHADOW_IMPLEMENTATION_READY`: YES.

`PRODUCTION_IMPLEMENTATION_READY`: NO.

Reason: the architecture is sound as a shadow-first refinement, but direct Production promotion would touch high-risk PC/MCV/Cash/ADD allocation behavior before golden-case invariants and problem-case comparability are proven.

## Required Answer Summary

- `CURRENT_CAPITAL_PRIORITY_AUTHORITY_GRAPH_COMPLETE`: `YES`
- `BUY_NEW_ADD_CASH_COMPARABILITY_BREAK_IDENTIFIED`: `YES`
- `PRIORITY_INFORMATION_COMPRESSION_IDENTIFIED`: `YES`
- `UNIFIED_NEXT_CAPITAL_UNIT_FEASIBLE`: `YES`
- `EXISTING_EVIDENCE_SUFFICIENT`: `YES_FOR_SHADOW_PARTIAL_FOR_PRODUCTION`
- `NEW_MODEL_REQUIRED`: `NO`
- `NEW_THRESHOLD_REQUIRED`: `NO`
- `FIXED_TOP_N_REQUIRED`: `NO`
- `CASH_CAN_BE_REAL_CAPITAL_COMPETITOR`: `YES`
- `BUY_ADD_CAN_COMPETE_WITH_BUY_NEW_SYMMETRICALLY`: `YES_AFTER_HARD_ELIGIBILITY_NOT_AS_LABEL_BONUS`
- `MCV_KEEP_EXTEND_REPLACE`: `EXTEND`
- `PC_RESPONSIBILITY_BOUNDARY_CLEAR`: `YES`
- `PM_RESPONSIBILITY_BOUNDARY_CLEAR`: `YES`
- `SIZING_RESPONSIBILITY_BOUNDARY_CLEAR`: `YES`
- `GOLDEN_CASE_SET_DEFINED`: `YES`
- `PROBLEM_CASE_SET_DEFINED`: `YES`
- `GOLDEN_CASE_REGRESSION_RISK`: `MEDIUM`
- `G129_PRESERVABLE`: `YES`
- `REENTRY_EW_EZ_PRESERVABLE`: `YES`
- `FAST_RISK_ON_PRESERVABLE`: `YES`
- `SELL_PM_PRESERVABLE`: `YES`
- `CAMPAIGN_IDENTITY_PRESERVABLE`: `YES`
- `LONG_LIVED_HISTORY_BIAS_AVOIDABLE`: `YES`
- `SHADOW_FIRST_FEASIBLE`: `YES`
- `SHADOW_ACCEPTANCE_CONTRACT_DEFINED`: `YES`
- `MINIMAL_PRODUCTION_SLICE_IDENTIFIED`: `YES`
- `ROLLBACK_BOUNDARY_DEFINED`: `YES`
- `ARCHITECTURE_SOT_UPDATE_PLAN_COMPLETE`: `YES`
- `ARCHITECTURE_DESIGN_SOUND`: `YES`
- `REGRESSION_RISK_ACCEPTABLE`: `YES_FOR_SHADOW / NO_FOR_DIRECT_PRODUCTION`
- `SHADOW_IMPLEMENTATION_READY`: `YES`
- `PRODUCTION_IMPLEMENTATION_READY`: `NO`

PRODUCTION_CHANGED: NO
SHADOW_CHANGED: NO
SOURCE_CHANGED: NO
CONFIG_CHANGED: NO
SCHEMA_CHANGED: NO
TARGET_RUN_MUTATED: NO
RUNTIME_STATE_MUTATED: NO
FRESH_RUN_EXECUTED: NO
RESUME_REPLAY_RECOVER_EXECUTED: NO
FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO

Final Judgment: `PHASE32_FQ_CAPITAL_PRIORITY_ARCHITECTURE_SOUND_SHADOW_FIRST_READY_DIRECT_PRODUCTION_NOT_READY_REGRESSION_INVARIANTS_DEFINED`
