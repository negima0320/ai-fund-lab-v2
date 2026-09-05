# Phase32-GJ - Fresh Target BUY-Side Current Opportunity Priority / Capital Reach READ-ONLY Audit

Target run: `runtime-test-historical-extended-smoke-20260904T204012180628Z`

Window: 2023-06-01 through 2023-06-28, 20 business days.

This audit is read-only. No source, config, schema, Production authority, SHADOW authority, SELL/REDUCE/EXIT semantic, resume, recover, replay, or fresh run action was performed. No rank cutoff, quality threshold, minimum Cash percent, BUY count, target breadth cap, or weight formula is selected from historical outcomes.

## Executive Judgment

Fresh Target preserves BUY-side Current Opportunity order. The target-member sequence is exactly rank-monotonic, both overall and within same BQ/NCU comparison classes, and no hidden re-ranking was found in the final top-level Fresh Target SHADOW rows.

The important distinction from Phase32-GI is this: BUY-side priority is working, while weight/selectivity remains weak. GI's winner/cash/breadth/stability concerns are real, but this GJ audit does not find that lower-priority BUY candidates are displacing higher-priority BUY candidates because of old position/campaign history. All observed higher-skipped/lower-targeted reach expansions are explained by hard eligibility blocks or bounded recent EXIT guard.

## Method

Canonical Current Opportunity order was reconstructed per business date from:

- `daily/<date>/strategy/portfolio_construction.json`
- `capital_competition.fresh_target_portfolio_shadow.rows`
- `current_opportunity_evidence.input_opportunity_rank`

The audit kept symbol, rank, runtime opportunity score, BQ class, MCV/NCU comparison state, hard eligibility, current position relationship target-use flag, Fresh Target membership, Fresh Target weight, recent-exit guard state, and Production BUY quantity/action where present.

## Priority Order Preservation

Target-member pair checks:

- Overall target-member ordered pairs checked: 8,019.
- Overall rank-preserving pairs: 8,019.
- Same comparison-class target-member pairs checked: 2,653.
- Same comparison-class rank-preserving pairs: 2,653.

Results:

- `BUY_SIDE_PRIORITY_ORDER_PRESERVATION_RATE = 100.00% overall; 100.00% within same BQ/NCU comparison class`
- `HIDDEN_RERANKING_FOUND = NO`
- `CURRENT_OPPORTUNITY_ORDER_ACCEPTED = YES`

Final Fresh Target row order matched ascending `input_opportunity_rank` on all 20 business dates. Target weights are weakly differentiated, but target membership order itself does not invert the canonical Current Opportunity order.

## Higher-Priority Skipped / Lower-Priority Targeted

Definition used: one event per higher-ranked non-member candidate that had at least one lower-ranked Fresh Target member on the same day. Pair count is also recorded to expose breadth.

- Event count: 429.
- Pair count: 8,807.
- `PRIORITY_INVERSION_COUNT = 429 events; 8,807 higher-skipped/lower-targeted pairs`

First reason distribution:

- `hard eligibility`: 336 events.
- `recent EXIT guard`: 93 events.
- `lot infeasible`: 0 events.
- `cap/headroom`: 0 events.
- `risk`: 0 events as first reason.
- `Cash/capital exhaustion`: 0 events as first reason.
- `current-position relationship`: 0 events.
- `campaign/history`: 0 events.
- `NCU comparison`: 0 events as first reason after hard/recent classification.
- `other`: 0 events.

Interpretation: the raw inversion count is high because the target reaches deep into the rank surface, but the skips above lower-ranked targets are not unexplained priority violations. They are from candidates that are not investable under current hard eligibility or are temporarily blocked by bounded recent EXIT guard.

## History-Caused Priority Inversion

Checked causes:

- old ownership
- closed campaign
- prior ADD
- prior EXIT outside recent guard
- average cost
- campaign age/history

Result:

- `HISTORY_CAUSED_PRIORITY_INVERSION_COUNT = 0`
- `CURRENT_POSITION_BUY_PATH_DEPENDENCE_COUNT = 0`

The Fresh Target rows also declare `current_position_relationship_used_for_target = false` for audited BUY rows. No priority skip was attributed to old ownership or campaign history.

## Held vs Flat / NEW vs ADD

BUY contexts:

- `BUY_NEW_CONTEXT` rows: 759.
- `BUY_ADD_CONTEXT` rows: 252.
- Fresh Target members from `BUY_NEW_CONTEXT`: 561.
- Fresh Target members from `BUY_ADD_CONTEXT`: 8.
- BUY_ADD rows with hard eligibility `PASS` but non-member: 0.

The ADD label remains different, as intended, but it is not used as a priority penalty once current BUY-side hard eligibility passes. Every hard-eligible BUY_ADD row reached Fresh Target membership.

- `HELD_FLAT_BUY_PRIORITY_SYMMETRY = PASS`
- `NEW_ADD_CURRENT_OPPORTUNITY_PARITY = PASS`
- `NEW_ADD_PARITY_ACCEPTED = YES`

## Capital Reach

Per-day final top-level Fresh Target non-cash target reach:

- `TARGET_COUNT_MIN_MAX_AVG = 21 / 43 / 28.45`
- `DEEPEST_RANK_MIN_MAX_AVG = 49.0 / 50.0 / 49.9`
- Highest rank targeted min/max/avg: 1.0 / 6.0 / 2.9.
- Cumulative non-cash Fresh Target weight min/max/avg: 0.820010 / 1.000012 / 0.991000.
- Cash target share min/max/avg: 0.000000 / 0.180000 / 0.009003.

- `CAPITAL_REACH_ORDER_PRESERVED = YES`
- `CAPITAL_REACH_ACCEPTED = YES_FOR_BUY_PRIORITY_ORDER; DESIGN_FOLLOWUP_STILL_REQUIRED_FOR_SELECTIVITY_AND_CASH_OPTIONALITY`

Fresh Target capital reaches broadly, but it reaches in rank order after excluding hard-blocked and recent-exit-blocked rows. This audit does not judge deep reach itself as bad.

## Capital Exhaustion Boundary

No evidence was found that finite capital caused a lower-ranked BUY member to displace a higher-ranked hard-eligible BUY candidate. When Cash remained positive, there were no otherwise-eligible non-member BUY opportunities left by the audit's definition.

- `ELIGIBLE_OPPORTUNITY_LEFT_UNCAPITALIZED_WITH_CASH_COUNT = 0`
- `CASH_UNJUSTIFIED_PRIORITY_DOMINANCE_COUNT = 0`
- `CASH_PRIORITY_SEMANTIC_ACCEPTED = YES`

Cash did not arbitrarily dominate buyable higher-priority opportunities in this 20BD window. This is distinct from GI's finding that Cash optionality is generally too low after day 1.

## Lot / Hard Block / Recent EXIT Reach

- `LOT_DRIVEN_PRIORITY_SKIP_COUNT = 0`
- `HARD_BLOCK_PRIORITY_SKIP_COUNT = 336`
- `RECENT_EXIT_PRIORITY_SKIP_COUNT = 93`

Hard block examples include BQ quality not positive, `BUY_WAIT`, and `ENTRY_BLOCK` states. Recent EXIT examples use `ACTIVE_RECENT_EXIT_GUARD` / `FAIL_CLOSED` with membership not allowed. These are legitimate reach expansions rather than investment-priority defects.

## NCU Comparator Effectiveness

- `NCU_COMPARATOR_INSTANCE_COUNT = 1` on each of the 20 final Fresh Target SHADOW objects.

BUY-side NCU/MCV state distribution:

- All BUY rows: `POSITIVE` 108, `INSUFFICIENT` 227, `BLOCKED` 59, blank/unclassified 617.
- Targeted BUY rows: `POSITIVE` 108, `INSUFFICIENT` 165, `BLOCKED` 33, blank/unclassified 263.

- `NCU_PRIORITY_EFFECTIVE = PARTIAL`

NCU participates, and all positive NCU rows are targeted, but it is not yet producing strong capital selectivity. Many `INSUFFICIENT`, `BLOCKED`, or blank MCV/NCU rows still receive target membership because the current Fresh Target behavior is broad and equal-ish after hard eligibility.

## Rank vs NCU Priority

Opportunity rank is the visible final ordering authority in the Fresh Target row sequence. NCU/MCV appears as current opportunity evidence and eligibility/comparison context, not as a hidden re-ranking authority.

Rank and NCU sometimes point in different directions: lower-ranked `POSITIVE` rows can be targeted after higher-ranked blocked/insufficient rows are skipped. That behavior is acceptable when the higher-ranked row fails hard eligibility or recent EXIT guard. No hidden order mutation was found.

## Equal Weight / Weight Differentiation

- `PRIORITY_CORRECT_WEIGHT_DIFFERENTIATION_WEAK = YES`

`WEIGHT_DIFFERENTIATION_CHARACTERIZATION`:

Fresh Target priority is rank-correct, but weight differentiation is weak. Targeted rows cluster around an equal-ish allocation level, with only modest day-level variation from target count, Cash residual, lot-aware finalization, and current ADD constraints. Rank preserves order, BQ/NCU affects hard eligibility and inclusion, and Cash is represented as a first-class row, but the final target weights do not strongly scale by rank, BQ, MCV, NCU, or risk conviction.

This is not a BUY-side priority failure; it is a future SHADOW design issue for selectivity and capital intensity.

## Actual Production BUY Comparison

Definition used:

- `Fresh Target top priority but Production not bought`: targeted Fresh Target rows whose rank is at or above the same-day deepest actual Production BUY rank, but whose Production quantity/fill was zero.
- `Production bought Fresh Target low priority`: actual Production BUY that was not a Fresh Target member, or was below the same-day Production BUY boundary.

Results:

- `FRESH_TARGET_TOP_PRIORITY_PRODUCTION_NOT_BOUGHT_COUNT = 140`
- `PRODUCTION_BOUGHT_FRESH_TARGET_LOW_PRIORITY_COUNT = 0`

Interpretation: Fresh Target exposes many high-priority current BUY opportunities that Production did not capitalize, matching the GA/FZ diagnosis that downstream PC/portfolio state caused actual BUY divergence. It does not show Production buying lower-priority candidates while Fresh Target higher-priority BUY candidates are ignored on the same rank surface.

## GA Divergence Revisit

Phase32-GA reported actual BUY overlap of 20.19% even where FZ showed the same current opportunity/rank universe. GJ's Fresh Target evidence supports the intended reduction mechanism:

- Same current opportunity order is preserved.
- `current_position_relationship_used_for_target = false`.
- BUY_ADD rows with hard eligibility PASS all become Fresh Target members.
- 67310 is targeted on the problem dates despite Production/fresh final target being zero.

- `GA_BUY_DIVERGENCE_REDUCTION_EVIDENCE = POSITIVE_FOR_PRIORITY_SURFACE; NOT_PROVEN_FOR_EXECUTABLE_PRODUCTION_FILLS_BECAUSE_SHADOW_IS_NON_AUTHORITATIVE`

Fresh Target would reduce the priority-surface divergence GA identified, but this run cannot prove actual fill convergence because SHADOW is intentionally not consumed by Production.

## 67310 Trace

`67310_BUY_PRIORITY_TRACE_COMPLETE = YES`

2023-06-05:

- Fresh Target priority index: 5.
- Opportunity rank: 5.
- BQ: `COMPARABLE_MARGINAL`.
- NCU/MCV: `BLOCKED`.
- Fresh Target membership/weight: true / 0.032258.
- Production action/quantity: `BUY_NEW` / 0.0.
- Hard eligibility: `PASS`, `CURRENT_PIT_HARD_ELIGIBILITY_PASS`.
- Skip/block reason: none in Fresh Target; Production did not buy.

2023-06-27:

- Fresh Target priority index: 2.
- Opportunity rank: 2.
- BQ: `COMPARABLE_MARGINAL`.
- NCU/MCV: `BLOCKED`.
- Fresh Target membership/weight: true / 0.032258.
- Production action/quantity: `BUY_NEW` / 0.0.
- Hard eligibility: `PASS`, `CURRENT_PIT_HARD_ELIGIBILITY_PASS`.
- Skip/block reason: none in Fresh Target; Production did not buy.

67310 is not judged using later outcome. The current-date evidence says the Fresh Target BUY-side surface correctly kept it in priority order and assigned target membership.

## Candidate Exhaustion With Cash

Cash target was positive on several days, but the audit found no otherwise eligible non-member BUY candidate left uncapitalized while Cash displaced it. Positive Cash was either day-1 residual policy context or lot/residual optionality, not arbitrary priority dominance over buyable Current Opportunity rows.

## BUY-Side Core Judgment

- History-neutral BUY priority established: YES.
- Current Opportunity order preserved: YES.
- NEW/ADD relationship asymmetry removed: YES for priority and membership after hard eligibility.
- Capital reach respects priority: YES, within the scope of hard eligibility and recent EXIT guard.
- Cash does not arbitrarily dominate eligible higher-priority BUYs: YES.

Required acceptance flags:

- `HISTORY_NEUTRAL_BUY_PRIORITY_ACCEPTED = YES`
- `CURRENT_OPPORTUNITY_ORDER_ACCEPTED = YES`
- `NEW_ADD_PARITY_ACCEPTED = YES`
- `CAPITAL_REACH_ACCEPTED = YES`
- `CASH_PRIORITY_SEMANTIC_ACCEPTED = YES`

## Production Change Judgment

- `BUY_SIDE_ARCHITECTURE_DIRECTION_JUSTIFIED = YES`
- `SELL_INTEGRATION_NEEDED_NOW = NO`
- `ADDITIONAL_SHADOW_DESIGN_REQUIRED = YES`
- `DIRECT_PRODUCTION_PROMOTION_READY = NO`

Additional SHADOW design remains required because GI-level findings still stand for winner retention, Cash optionality, breadth/selectivity, and stability. Those are not BUY priority-order defects and should not be solved by SELL/REDUCE/EXIT integration in this step.

## Required Answers

- `BUY_SIDE_PRIORITY_ORDER_PRESERVATION_RATE = 100.00% overall; 100.00% within same BQ/NCU comparison class`
- `PRIORITY_INVERSION_COUNT = 429 events; 8,807 pairs`
- `HISTORY_CAUSED_PRIORITY_INVERSION_COUNT = 0`
- `HELD_FLAT_BUY_PRIORITY_SYMMETRY = PASS`
- `NEW_ADD_CURRENT_OPPORTUNITY_PARITY = PASS`
- `TARGET_COUNT_MIN_MAX_AVG = 21 / 43 / 28.45`
- `DEEPEST_RANK_MIN_MAX_AVG = 49.0 / 50.0 / 49.9`
- `CAPITAL_REACH_ORDER_PRESERVED = YES`
- `LOT_DRIVEN_PRIORITY_SKIP_COUNT = 0`
- `HARD_BLOCK_PRIORITY_SKIP_COUNT = 336`
- `RECENT_EXIT_PRIORITY_SKIP_COUNT = 93`
- `CURRENT_POSITION_BUY_PATH_DEPENDENCE_COUNT = 0`
- `NCU_COMPARATOR_INSTANCE_COUNT = 1`
- `NCU_PRIORITY_EFFECTIVE = PARTIAL`
- `HIDDEN_RERANKING_FOUND = NO`
- `PRIORITY_CORRECT_WEIGHT_DIFFERENTIATION_WEAK = YES`
- `WEIGHT_DIFFERENTIATION_CHARACTERIZATION = rank/order preserved; BQ/NCU mainly inclusion or hard-eligibility context; final targeted weights remain equal-ish with weak rank/BQ/MCV/risk intensity differentiation`
- `FRESH_TARGET_TOP_PRIORITY_PRODUCTION_NOT_BOUGHT_COUNT = 140`
- `PRODUCTION_BOUGHT_FRESH_TARGET_LOW_PRIORITY_COUNT = 0`
- `GA_BUY_DIVERGENCE_REDUCTION_EVIDENCE = POSITIVE_FOR_PRIORITY_SURFACE; NOT_PROVEN_FOR_EXECUTABLE_PRODUCTION_FILLS_BECAUSE_SHADOW_IS_NON_AUTHORITATIVE`
- `67310_BUY_PRIORITY_TRACE_COMPLETE = YES`
- `CASH_UNJUSTIFIED_PRIORITY_DOMINANCE_COUNT = 0`
- `ELIGIBLE_OPPORTUNITY_LEFT_UNCAPITALIZED_WITH_CASH_COUNT = 0`
- `HISTORY_NEUTRAL_BUY_PRIORITY_ACCEPTED = YES`
- `CURRENT_OPPORTUNITY_ORDER_ACCEPTED = YES`
- `NEW_ADD_PARITY_ACCEPTED = YES`
- `CAPITAL_REACH_ACCEPTED = YES`
- `CASH_PRIORITY_SEMANTIC_ACCEPTED = YES`
- `BUY_SIDE_ARCHITECTURE_DIRECTION_JUSTIFIED = YES`
- `SELL_INTEGRATION_NEEDED_NOW = NO`
- `ADDITIONAL_SHADOW_DESIGN_REQUIRED = YES`
- `DIRECT_PRODUCTION_PROMOTION_READY = NO`
- `NEXT_STEP = Phase32-GK or equivalent SHADOW-only design follow-up for weight differentiation/selectivity, Cash optionality, breadth, and stability while preserving the GJ-accepted BUY-side priority order and NEW/ADD parity.`

## Final Judgment

Fresh Targetは、過去のposition/campaign historyをInvestment Authorityから外した上で、BUY側のCurrent Opportunity priorityを保ち、NEW/ADDを同じ投資価値として扱い、資金・lot・Safety制約の範囲で上位Opportunityから順に正しく資本化できている。ただしweight differentiation/selectivity/Cash/stabilityは追加SHADOW設計が必要で、直接Production昇格は不可。
