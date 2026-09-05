# Phase32-GK - BUY-Only History-Neutral Current Opportunity Priority / Existing Sizing Preservation Architecture Design

Scope: DESIGN / READ-ONLY.

No Production implementation, source/config/schema change, fresh run, replay, resume, recover, SELL/REDUCE/EXIT semantic change, or Production/SHADOW authority change was performed. This design does not select a new rank cutoff, quality cutoff, Cash percent, BUY count, weight formula, or threshold from historical outcomes.

## Executive Judgment

Yes: the GJ-accepted history-neutral BUY Current Opportunity priority can be cut out as a Production-candidate architecture while preserving current BUY_NEW/BUY_ADD sizing, ADD Safety, Cash semantics, SELL/PM/Winner Protection, and runtime execution boundaries.

The recommended architecture is **Option B: add a Fresh BUY Priority layer and bridge only its ordered BUY subset into existing PC/PS sizing**. It has the cleanest long-term boundary and the smallest acceptable blast radius: priority changes in a BUY-only artifact/PC bridge, while existing Position Sizing, lot/cap/liquidity, ADD safety, G129, Runtime Planning, Submit, Execution, PM SELL/HOLD/REDUCE/EXIT, and Winner Protection remain owners of their current responsibilities.

Option C, full Fresh Target Portfolio Productionization, is rejected for now because GI showed equal-ish weight, weak selectivity, Cash optionality, churn, and winner-conflict risks. Those are portfolio-target risks, not reasons to block the BUY-only priority extraction.

## Current Production BUY Pipeline

Actual pipeline and source boundaries:

| Stage | Current source / function | Role | History/path-dependence risk |
|---|---|---|---|
| Candidate / Opportunity | runtime BUY AI artifacts consumed by `PortfolioConstructionSourceSummary` | Current PIT candidates, rank, score | Low if PIT source is valid |
| BQ / Entry | `src/ai_fund_lab_v2/strategy/buy_quality.py`; attached in `portfolio_construction._attach_buy_quality()` | BUY quality/action, wait/reject/reduced allocation | Intended current evidence gate |
| PM relationship | `src/ai_fund_lab_v2/strategy/position_management.py`; `portfolio_construction.validate_position_management_compatibility()` | Current HOLD/ADD/REDUCE/EXIT lifecycle state | High if used before investment priority |
| PC member reconciliation | `portfolio_construction._reconcile_members()` | Merges current positions first, then opportunity rows; maps flat eligible rows to `ADD_CANDIDATE`; maps held rows by PM action | First structural point where current position/campaign state changes membership path |
| Target weight contract | `portfolio_construction._resolve_target_weight_contract()` | Equal-weight target, quality adjustment, reentry/low-price guards, ADD bridge | History/path can affect selected members and increment availability |
| Capital competition / MCV | `portfolio_construction.build_capital_competition_framework()` and `marginal_capital_value.apply_marginal_capital_priority()` | Compares `NEW_BUY`, `ADD`, `CASH`; builds canonical deployment set and shadows | Existing MCV only sees rows with positive accepted increment, so priority is downstream of current state-shaped sizing intent |
| Lot-aware PC finalization | `portfolio_construction.apply_lot_aware_final_reallocation()` | Preserves baseline, determines remaining capital, applies lot-aware allocation | Calls MCV after baseline/current-state preparation |
| Position Sizing | `src/ai_fund_lab_v2/strategy/position_sizing.py` | Target notional, quantity candidate, lot, cap, liquidity, quality, safety cap | Should remain sizing authority |
| Runtime Planning | `src/ai_fund_lab_v2/strategy/runtime_planning.py` | Consumes PC/PS/PM/current cash/current positions into plans | Should not recompute priority |
| Pending / Submit / Execution | `runtime_v2` pending/submit/execution paths | Order lifecycle and simulated/historical fills | Out of scope for priority |

- `CURRENT_PRODUCTION_BUY_PIPELINE_MAPPED = YES`
- `FIRST_HISTORY_DEPENDENT_BUY_PRIORITY_BOUNDARY = portfolio_construction._reconcile_members() / _resolve_target_weight_contract(), amplified by apply_lot_aware_final_reallocation() calling marginal_capital_value.apply_marginal_capital_priority() only after accepted increments/current-position state have already shaped rows`

## Minimal Replacement Boundary

The minimal boundary is **not** Fresh Target weights. It is a BUY-only ordered priority list:

```text
Current PIT Opportunity -> Fresh BUY Priority -> Action Relationship -> Existing PC/PS sizing
```

Priority answers: which BUY opportunity receives available capital first?

Sizing answers: how much, if any, can the selected opportunity receive under existing target sizing, lot, cap, liquidity, cash, and ADD safety?

- `PRIORITY_SIZING_AUTHORITY_SEPARABLE = YES`

## Implementation Options

### Option A - Replace history-dependent priority inside existing PC

Description: modify `portfolio_construction.py` so current PC member ordering / capital competition uses history-neutral BUY priority when choosing BUY_NEW/BUY_ADD capital order.

Pros:

- Smallest file count.
- Directly near current target/deployment code.
- Can reuse existing PC source summaries.

Cons:

- High risk of blurring priority with target weight resolution.
- Easy to accidentally affect SELL/REDUCE/EXIT rows because PC is portfolio-wide.
- Harder to prove Fresh Priority is not another hidden target-weight formula.

Verdict: viable but not recommended as first Production bridge.

### Option B - Add Fresh BUY Priority layer and bridge into existing PC/PS

Description: create a BUY-only priority artifact/producer that consumes current PIT Opportunity/BQ/NCU evidence, excludes forbidden history inputs, emits ordered BUY candidates plus action relationship metadata, and exposes a narrow bridge that existing PC can consume before deployment selection. Existing PC/PS still decide target availability, lot, cap, liquidity, cash, and quantity.

Pros:

- Clean authority separation.
- Best auditability for history-neutral priority.
- Avoids importing Fresh Target equal-ish weights.
- Lets PS, G129, ADD safety, runtime planning, PM SELL/HOLD/REDUCE/EXIT remain unchanged.
- Can stay SHADOW first, then be connected as an explicit BUY-priority consumer.

Cons:

- New artifact/contract and focused integration tests are needed before Production use.
- PC needs a bridge point to consume the ordered BUY subset.

Verdict: recommended.

### Option C - Full Fresh Target Portfolio Productionization

Description: promote current Fresh Target Portfolio target membership/weight/deltas into Production.

Pros:

- Uses the artifact already proven clean on run binding/history-neutrality.
- Would maximize divergence from old path-dependent portfolio state.

Cons:

- GI found 138 winner conflicts, high churn, too-low Cash optionality, broad rank depth, and equal-ish weak weight differentiation.
- Would risk SELL/Winner authority leakage if interpreted naively.
- Would replace sizing/target behavior instead of only replacing priority.

Verdict: rejected for now.

- `RECOMMENDED_ARCHITECTURE_OPTION = Option B`
- `PRODUCTION_BLAST_RADIUS = LOW_TO_MEDIUM_FOR_OPTION_B; HIGH_FOR_OPTION_C`

## Recommended Architecture

### 1. Fresh BUY Priority Producer

Create a future SHADOW-first artifact conceptually named `fresh_buy_priority.v1`.

Inputs:

- Candidate/opportunity rank and score.
- BQ/Entry current PIT evidence.
- NCU comparator output, once.
- Broker/current hard eligibility evidence.
- Risk evidence required for BUY hard gates.
- Current business date, source hashes, run/date binding.

Forbidden priority inputs:

- old ownership
- closed campaign
- prior EXIT outside recent guard
- prior ADD count outside open-campaign safety
- average cost
- realized PnL
- old campaign PnL
- old campaign age

Output:

- Ordered BUY opportunity rows.
- `fresh_buy_priority_index`.
- `input_opportunity_rank`.
- BQ/NCU class.
- hard eligibility status.
- current-position relationship display fields only.
- no quantity, target weight, order, submit, SELL, REDUCE, EXIT, or Winner authority.

### 2. Action Relationship Materializer

After priority is fixed, current position is consulted only to materialize action relationship:

- flat -> `BUY_NEW`
- held -> `BUY_ADD`

This relationship must not change the priority index. It can affect downstream hard eligibility and sizing because ADD has legitimate no-loss, headroom, campaign-local safety, and G129 constraints.

- `BUY_NEW_ADD_COMMON_PRIORITY_FEASIBLE = YES`
- `BUY_ONLY_FRESH_PRIORITY_FEASIBLE = YES`

### 3. Existing PC/PS Bridge

The bridge should pass only:

- ordered symbol/action list
- priority index
- current PIT evidence lineage
- hard eligibility reason display
- NCU comparator evidence hash/class

The bridge must not pass:

- Fresh Target target weights
- Fresh Target semantic deltas
- Fresh Target `EXIT_CANDIDATE` / `RELEASE`
- Cash target share
- winner conflict suggestions
- quantity
- order authority

Existing PC may use the priority list to choose which BUY candidates enter existing deployment/sizing consideration first. Existing PS remains the quantity owner.

- `SHADOW_BRIDGE_DESIGN_DEFINED = YES`

## Existing Sizing Preservation

BUY_NEW sizing can be preserved because `position_sizing._raw_position()` already resolves target weight, quality, volatility, cap, reference price, lot feasibility, target notional, quantity candidate, and minimum meaningful notional from existing PC/PS inputs. The Fresh Priority bridge should influence order/admission into the existing sizing queue, not target-weight math.

BUY_ADD sizing can be preserved because existing sizing already distinguishes existing positions, applies incremental transaction scope, preserves baseline quantity for HOLD/ADD/UNRESOLVED, blocks incremental ADD when BQ says so, and resolves G129/order-increment scoped authority downstream.

Preserved authorities:

- no-loss averaging
- open-campaign ADD safety
- G129 order increment
- strategy/safety cap
- headroom
- liquidity
- buying power/cash availability
- lot feasibility
- minimum executable lot rules

Required invariants:

- Fresh Priority never emits target weight.
- Fresh Priority never emits quantity.
- Fresh Priority never overrides `position_sizing_authority`.
- Position Sizing does not recompute capital priority.
- Runtime Planning does not recompute capital priority.

- `EXISTING_BUY_NEW_SIZING_PRESERVABLE = YES`
- `EXISTING_BUY_ADD_SIZING_PRESERVABLE = YES`
- `ADD_SAFETY_PRESERVABLE = YES`
- `G129_PRESERVABLE = YES`

## SELL / PM / Winner Isolation

Fresh BUY Priority must be BUY-only:

- no HOLD authority
- no REDUCE authority
- no EXIT authority
- no Winner Protection authority
- no Profit Retention authority
- no PM lifecycle authority
- no order authority

PM remains owner of HOLD/ADD/REDUCE/EXIT lifecycle semantics. Fresh Priority can observe current position only after priority is fixed, and only to label `BUY_NEW` vs `BUY_ADD` for downstream sizing.

- `SELL_PRODUCTION_SEMANTIC_CHANGED = NO`
- `PM_PRODUCTION_AUTHORITY_CHANGED = NO`
- `WINNER_PROTECTION_CHANGED = NO`

## Cash Semantics

Fresh Priority should not create a new Cash threshold or force cash deployment. Cash remains an available-capital constraint and optionality result from existing policy/PC/PS/runtime state.

Fresh Priority answers: if Cash is available for BUY, which current opportunity should be tried first?

It does not answer: how much Cash must be spent?

- `CASH_FORCED_DEPLOYMENT_REQUIRED = NO`
- `CURRENT_CASH_SEMANTIC_PRESERVABLE = YES`

## Capital Exhaustion

When cash is limited:

1. Iterate current BUY opportunities in `fresh_buy_priority_index` order.
2. For each row, materialize action relationship as BUY_NEW or BUY_ADD.
3. Apply existing hard eligibility, recent EXIT guard, ADD safety, lot, cap, liquidity, and buying power.
4. If blocked or infeasible, record skip reason and continue.
5. If sizeable, let existing PC/PS decide target/notional/quantity.
6. Stop when existing cash/buying-power authority is exhausted.

History/held relationship alone must not skip an opportunity.

## Recent EXIT

Recent EXIT guard remains a bounded exception. Preferred architecture:

- Fresh Priority records the current opportunity and priority index.
- Execution/sizing eligibility blocks it while the bounded guard is active.
- Expiry releases the guard without creating a permanent history penalty.

- `RECENT_EXIT_GUARD_PRESERVABLE = YES`

## NCU Integration

Use the NCU comparator exactly once in the Fresh BUY Priority producer. Do not add a second comparator inside PC, PS, Runtime Planning, or the bridge.

- `NCU_COMPARATOR_INSTANCE_COUNT = 1`

NCU should be evidence for priority class/hard eligibility, not a hidden score layered after rank. If NCU and rank conflict, the emitted row must expose both and name the tie/order authority. No hidden re-ranking.

- `HISTORY_PRIORITY_INPUTS_REMOVED = YES`

## Golden Cases

`GOLDEN_CASES_DEFINED = YES`

1. High-priority NEW: flat strong/current opportunity gets early priority, existing BUY_NEW sizing decides amount.
2. High-priority ADD: held current opportunity gets early priority, ADD label only after priority, existing ADD safety decides amount.
3. NEW > ADD: higher-priority NEW before lower-priority ADD, no action-label bonus.
4. ADD > NEW: higher-priority ADD before lower-priority NEW, no action-label penalty.
5. High-priority blocked -> next candidate: hard block recorded, next priority tried.
6. High-price lot infeasible -> next candidate: lot infeasibility recorded, no priority defect.
7. Recent EXIT guard: priority recorded, eligibility blocks while active, no permanent penalty.
8. Cash exhaustion: earlier sizeable opportunities consume available cash first, later rows remain unfilled by cash authority.
9. Existing Winner HOLD unaffected: no Fresh BUY authority emitted for HOLD/winner retention.
10. PM EXIT unaffected: PM/Safety terminal EXIT remains owner.
11. No-loss ADD block: ADD priority may exist, but existing ADD safety blocks increment.
12. Concentration hard cap: priority may exist, but existing cap/headroom blocks or caps sizing.

## GA/GJ Problem Cases

`PROBLEM_CASES_COVERED = YES`

- Held-vs-flat asymmetry: common priority before action relationship removes priority penalty from held state.
- NEW-vs-ADD path divergence: BUY_NEW and BUY_ADD share priority ordering; action label is sizing context only.
- Old campaign suppression: forbidden from Fresh BUY Priority inputs.
- Prior ADD suppression: forbidden outside open-campaign ADD safety.
- Same-rank capitalization divergence: stable PIT priority emitted before current-position target shaping.
- 67310: would remain high-priority BUY_NEW on 2023-06-05 and 2023-06-27; existing sizing/cash/lot decide executable quantity, later outcome not used.
- Priority inversion: only hard eligibility, recent EXIT guard, lot/cap/safety infeasibility, or cash exhaustion may justify lower-priority reach.

## Production Blast Radius

Likely future modules/functions touched under Option B:

- Add a new BUY-only priority producer module, likely near `src/ai_fund_lab_v2/strategy/marginal_capital_value.py` or as a new `fresh_buy_priority.py`.
- Add PC bridge consumption in `src/ai_fund_lab_v2/strategy/portfolio_construction.py`, before deployment selection / capital competition.
- Add tests around `portfolio_construction._reconcile_members()`, `_resolve_target_weight_contract()`, `build_capital_competition_framework()`, and `apply_lot_aware_final_reallocation()` to prove priority is consumed without importing Fresh Target weights.
- Add shadow-runtime materialization only if needed for acceptance.

Must not be touched for first bridge:

- `position_sizing._raw_position()` quantity math, except tests asserting no priority reinterpretation.
- Runtime Planning plan mapping.
- Pending promotion.
- Submit/execution.
- PM SELL/HOLD/REDUCE/EXIT logic.
- Winner Protection / Profit Retention.

## Adversarial Risks

`ADVERSARIAL_RISKS_DEFINED = YES`

- NEW starvation: ADD incumbents consume all cash despite lower priority.
- ADD starvation: held high-priority current opportunities get deprioritized because they are not flat.
- Action-label bias: BUY_NEW/BUY_ADD label acts as bonus or penalty.
- Cash forced deployment: priority layer becomes spend mandate.
- Sizing regression: Fresh Target equal-ish weights leak into Production.
- ADD safety bypass: priority causes ADD despite no-loss/headroom/campaign-local block.
- G129 regression: priority emits quantity or changes order-increment scope.
- Winner/SELL authority leak: Fresh Target `EXIT_CANDIDATE` or `RELEASE` contaminates PM.
- Churn increase: priority bridge causes daily rewrite without sizing/cash discipline.
- History penalty revival: old ownership/campaign/prior exits creep back as priority inputs.
- NCU double counting: second comparator hidden in PC or PS.
- Runtime redecision: Runtime Planning reorders or resizes after PS.

## Acceptance Invariants

- Priority is generated before action relationship.
- Current position may label action relationship after priority, but must not change priority index.
- BUY_ADD hard/safety checks remain downstream and campaign-local.
- Recent EXIT is the only bounded history exception.
- Fresh Priority emits no target weight, quantity, order, SELL, REDUCE, EXIT, or Winner directive.
- Existing PC/PS remain sizing and feasibility authorities.
- Runtime consumes existing plan/quantity authority only.

## Required Answers

- `CURRENT_PRODUCTION_BUY_PIPELINE_MAPPED = YES`
- `FIRST_HISTORY_DEPENDENT_BUY_PRIORITY_BOUNDARY = portfolio_construction._reconcile_members() / _resolve_target_weight_contract(); existing apply_lot_aware_final_reallocation() later calls marginal_capital_value.apply_marginal_capital_priority() after current-state accepted increments have already shaped BUY rows`
- `BUY_ONLY_FRESH_PRIORITY_FEASIBLE = YES`
- `BUY_NEW_ADD_COMMON_PRIORITY_FEASIBLE = YES`
- `EXISTING_BUY_NEW_SIZING_PRESERVABLE = YES`
- `EXISTING_BUY_ADD_SIZING_PRESERVABLE = YES`
- `PRIORITY_SIZING_AUTHORITY_SEPARABLE = YES`
- `SELL_PRODUCTION_SEMANTIC_CHANGED = NO`
- `PM_PRODUCTION_AUTHORITY_CHANGED = NO`
- `WINNER_PROTECTION_CHANGED = NO`
- `CASH_FORCED_DEPLOYMENT_REQUIRED = NO`
- `CURRENT_CASH_SEMANTIC_PRESERVABLE = YES`
- `ADD_SAFETY_PRESERVABLE = YES`
- `G129_PRESERVABLE = YES`
- `RECENT_EXIT_GUARD_PRESERVABLE = YES`
- `HISTORY_PRIORITY_INPUTS_REMOVED = YES`
- `NCU_COMPARATOR_INSTANCE_COUNT = 1`
- `GOLDEN_CASES_DEFINED = YES`
- `PROBLEM_CASES_COVERED = YES`
- `ADVERSARIAL_RISKS_DEFINED = YES`
- `RECOMMENDED_ARCHITECTURE_OPTION = Option B - Fresh BUY Priority layer plus narrow existing PC/PS bridge`
- `PRODUCTION_BLAST_RADIUS = LOW_TO_MEDIUM; primarily new BUY-priority producer and PC bridge/tests; PS/Runtime/PM/SELL/Submit/Execution unchanged`
- `SHADOW_BRIDGE_DESIGN_DEFINED = YES`
- `DIRECT_PRODUCTION_IMPLEMENTATION_READY = NO`
- `ADDITIONAL_REVIEW_REQUIRED = YES`
- `NEXT_STEP = Phase32-GL SHADOW-first implementation spec/test plan for Option B: define fresh_buy_priority.v1 schema, PC bridge contract, no-weight/no-quantity invariants, and golden/adversarial fixtures before any Production consumer is connected.`

## Final Judgment

GJでacceptedされたhistory-neutral BUY Current Opportunity priorityだけをProduction候補として切り出し、現行BUY_NEW/BUY_ADD sizing・ADD Safety・Cash semantics・SELL/PM/Winner Protectionを維持したまま、最小変更で導入できるArchitectureは設計可能であり、推奨はOption Bだが、直接Production実装はまだ不可。
