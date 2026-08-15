# Phase29-L21M — Portfolio Construction Lot / Concentration Root Cause Audit

Task ID: `Phase29-L21M`  
Target run: `runtime-test-historical-smoke-20260811T152905733571Z`  
Mode: read-only audit. No implementation, configuration, threshold, model, accepted-generation, runtime, pending, resume, abort, repair, fresh run, or historical-run mutation was performed.

## Executive Summary

The 185 `minimum_lot_exceeds_concentration_cap` instances are not primarily a case where Strategy soft cap is exceeded only slightly while Safety hard cap still has ample room. Using the artifact's official minimum executable policy lot, all 185 instances exceed the 25% Safety hard cap. The direct classification is therefore `EXPECTED_SAFETY_HARD_CAP_BLOCK` under the current minimum meaningful notional policy, with a broader structural `LOT_DISCRETIZATION_LIMITATION` for a roughly 1M JPY portfolio trading high-price round-lot equities.

The PC label is somewhat misleading: the skip reason is `minimum_lot_exceeds_concentration_cap`, but the nested L19 lot evidence has `boundary_classification = MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX` for these blocked rows. PC is following the current cap/lot contract rather than losing a valid Strategy-soft-cap authorization.

There is still a design issue. If the analysis-only counterfactual permits exactly one 100-share round lot instead of the artifact's minimum policy lot, 40 / 185 instances fit within Safety hard cap, and 38 instances also fit available cash and gross exposure budget. A sequential daily counterfactual would deploy about 5.91M JPY more notional across the audited period and raise PC-stage average gross exposure from about 47.87% to about 50.33%. This is a capital deployment mechanics improvement, not a PnL claim, and it does not close the whole utilization gap by itself.

## L21L Baseline

L21L established the following baseline:

- Candidate / Opportunity rows: 12,600.
- Buy Quality non-reject: about 84%.
- PC BUY_NEW / BUY_ADD candidate members: 548.
- PC positive allocations: 72.
- PC positive-increment days: 72.
- PC zero-increment days: 180.
- Residual cash reasons:
  - `CONCENTRATION_LIMIT`: 147.
  - `NO_ELIGIBLE_OPPORTUNITY`: 71.
  - `COMPETITION_EXHAUSTED`: 28.
  - `NO_LOT_FEASIBLE_OPPORTUNITY`: 4.
  - `CAPITAL_BELOW_NEXT_LOT`: 2.
- Skipped allocation:
  - `minimum_lot_exceeds_concentration_cap`: 185.
  - `lot_or_broker_infeasible`: 12.
  - `minimum_lot_exceeds_remaining_budget`: 2.

This L21M audit uses the fixed L21L baseline window ending `2023-08-18`, which matches the 185 blocked instances. Later visible target-run daily artifacts were not mixed into this baseline.

## Lot / Concentration Evidence

All 185 blocked rows had:

- `skipped_reason = minimum_lot_exceeds_concentration_cap`
- nested `lot_resolution.authority_type = PHASE29_L19_CAP_CONSTRAINED_LOT_RESOLUTION`
- nested `boundary_classification = MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX`
- `participant_type`: 153 `BUY_NEW`, 32 `BUY_ADD`
- 76920 instances: 0

The official artifact minimum is not always one round lot. It is `minimum_policy_lots * 100 shares`, driven by the minimum meaningful notional policy. That matters because many official blocked rows require two policy lots and therefore exceed the 25% Safety hard cap even when a single 100-share round lot would fit.

Official blocked minimum-lot notional:

- Total repeated daily blocked notional: 146,655,960 JPY.
- Average: 792,735 JPY.
- Median: 600,000 JPY.
- Min / max: 118,240 JPY / 1,896,000 JPY.

One-round-lot notional for the same rows:

- Total repeated daily one-lot notional: 73,327,980 JPY.
- Average: 396,367 JPY.
- Median: 300,000 JPY.
- Min / max: 59,120 JPY / 948,000 JPY.

## Overshoot Distribution

Official overshoot is calculated as:

`minimum_lot_resulting_weight - strategy_maximum_position_weight`

Using the artifact's official minimum policy lot:

| Overshoot band | Count | Share |
|---|---:|---:|
| <= 0.5pp | 0 | 0.0% |
| 0.5-1.0pp | 0 | 0.0% |
| 1.0-2.0pp | 0 | 0.0% |
| 2.0-5.0pp | 0 | 0.0% |
| > 5.0pp | 185 | 100.0% |

Safety hard cap result:

- Official minimum policy lot within Safety hard cap: 0 / 185, 0.0%.
- Official minimum policy lot also exceeds Safety hard cap: 185 / 185, 100.0%.

Analysis-only one-round-lot counterfactual:

| One-lot overshoot band | Count |
|---|---:|
| <= 0.5pp | 2 |
| 0.5-1.0pp | 6 |
| 1.0-2.0pp | 4 |
| 2.0-5.0pp | 26 |
| > 5.0pp | 147 |

One-round-lot Safety result:

- One round lot within Safety hard cap: 40 / 185, 21.6%.
- One round lot within Safety hard cap, cash, and gross exposure budget: 38 / 185, 20.5%.

Answer to the key question: using official minimum policy lots, there are 0 cases where the Strategy soft cap is only slightly exceeded while Safety hard cap still contains the trade. Using a one-round-lot counterfactual, there are 40 Safety-contained cases, but only 12 are within 2pp of the Strategy cap.

## Counterfactual Capital Deployment

Counterfactual rule:

- Do not mutate runtime or pending.
- Exclude 76920 as a separate corporate-action quarantine issue. It had 0 instances here.
- Preserve Safety hard cap.
- Preserve target gross exposure.
- Preserve available cash.
- For each blocked candidate, analyze a one-round-lot buy.
- For daily aggregate impact, apply at most feasible sequential one-lot additions in opportunity-rank order.

Results:

- Feasible one-lot instances after Safety/cash/gross checks: 38.
- Impacted days: 38.
- Theoretical additional deployed capital: 5,914,400 JPY.
- PC-stage actual average gross exposure: 47.87%.
- PC-stage theoretical average gross exposure: 50.33%.

This counterfactual shows a real but limited capital deployment improvement. It does not explain the full L21L average invested-ratio gap alone, and it is not a performance or return estimate.

## Candidate Competition

Day-level competition classification across days with `minimum_lot_exceeds_concentration_cap`:

| Classification | Days |
|---|---:|
| top candidate infeasible -> lower candidate allocated | 31 |
| top candidate infeasible -> lower candidates also infeasible | 101 |
| top candidate infeasible -> competition unexpectedly stopped | 0 confirmed |
| legitimate opportunity exhaustion -> residual Cash | 4 |
| evidence insufficient | 18 |

PC does not appear to stop after the first infeasible candidate as a broad defect. There are 31 days where lower-ranked candidates were allocated after higher-ranked infeasible candidates. Most non-allocation days instead show the lower candidates also failing lot/Safety feasibility, though 18 days lack enough evidence for a stronger claim.

## BUY_NEW vs BUY_ADD Semantics

BUY_ADD:

- L21D/L21F intentionally allow a narrow Strategy soft-cap overshoot only for existing-position `BUY_ADD`.
- Position Sizing consumes that authorization only when the row is an existing position, `pm_action = ADD`, `membership_intent = RETAIN`, semantic type `BUY_ADD`, ADD economics pass, the post-trade weight remains within Safety hard cap, and L19/L21D overshoot evidence is present.

BUY_NEW:

- BUY_NEW has the same discrete lot boundary in the sense that a new position's minimum lot may exceed Strategy cap and/or Safety cap.
- BUY_NEW does not currently have the L21D/L21F lot-aware Strategy soft-cap authorization contract.
- PC currently blocks BUY_NEW when required lot weight exceeds the Strategy single-name cap and no BUY_ADD-only overshoot authorization applies.
- In the 185 official blocked rows, however, the official minimum policy lot also exceeds Safety hard cap, so merely extending BUY_ADD soft-cap semantics to BUY_NEW would not solve these cases.

Conclusion: a BUY_NEW lot-aware integration gap exists only for the one-round-lot counterfactual subset, not for the official minimum-policy-lot blocked set. Any BUY_NEW change would need independent new-entry risk semantics and must not inherit BUY_ADD behavior automatically.

## Cap Authority

| Authority | Producer / artifact | Consumer | Role | Soft / hard | Value |
|---|---|---|---|---|---:|
| Portfolio Policy single-name cap | `configs/strategy/portfolio_policy.json#single_name_weight_cap`; `strategy/portfolio_policy.json` | PC, BQ portfolio fit | Strategy diversification target | Strategy soft/target boundary | 0.18 |
| Strategy maximum position weight | `configs/strategy/position_sizing.json#strategy_maximum_position_weight`; `strategy/position_sizing.json` | Position Sizing, L19 lot feasibility | Strategy sizing cap | Strategy target boundary, hard except authorized BUY_ADD | 0.18 |
| Portfolio Construction cap | `strategy/portfolio_construction.json#single_name_weight_cap` | PC lot-aware final reallocation | Target membership / target weight authority | Enforced Strategy cap unless eligible BUY_ADD overshoot | 0.18 |
| Position Sizing effective cap | `strategy/position_sizing.json#effective_maximum_position_weight` | PS final validation | Quantity validation cap | `min(strategy, safety)` with BUY_ADD exception | 0.18 |
| Safety hard max | `configs/safety/portfolio_limits.json#concentration.maximum_position_weight`; `strategy/position_sizing.json#safety_maximum_position_weight` | PC/PS/Safety evidence | Final single-name hard limit | Hard | 0.25 |

Strategy and Safety are semantically separated in evidence. The duplication risk remains that 0.18 appears in Portfolio Policy, PC, and PS, but L21F added an explicit BUY_ADD exception consumer so PS no longer treats the Strategy cap as an unconditional hard boundary for that narrow path. BUY_NEW remains fail-closed at the Strategy cap and Safety cap boundaries.

## Symbol / Price Distribution

Blocked counts by symbol:

| Symbol | Count |
|---|---:|
| 67310 | 62 |
| 59350 | 29 |
| 58070 | 20 |
| 39060 | 18 |
| 83060 | 14 |
| 43930 | 8 |
| 30410 | 8 |
| 70180 | 8 |
| 78780 | 7 |
| 99840 | 7 |
| 43880 | 2 |
| 54010 | 1 |
| 44440 | 1 |

Price bands:

| Price band | Count |
|---|---:|
| <500 | 0 |
| 500-999 | 15 |
| 1,000-1,999 | 26 |
| 2,000-4,999 | 86 |
| >=5,000 | 58 |

Official minimum-lot notional bands:

| Notional band | Count |
|---|---:|
| <50k | 0 |
| 50-100k | 0 |
| 100-180k | 4 |
| 180-250k | 14 |
| 250-500k | 39 |
| >=500k | 128 |

Opportunity rank bands:

| Rank band | Count |
|---|---:|
| 1 | 10 |
| 2-5 | 149 |
| 6-10 | 26 |
| 11-20 | 0 |
| >20 | 0 |

This is broader than one isolated symbol, but it is concentrated in high-price/high-notional candidates. It is a structural small-portfolio round-lot expression problem, with 67310 especially dominant.

## Root Cause Classification

Required classification:

| Classification | Count / judgment |
|---|---|
| `EXPECTED_STRATEGY_CONCENTRATION_CONTROL` | Secondary for PC skip label, but not primary because nested evidence shows Safety breach |
| `EXPECTED_SAFETY_HARD_CAP_BLOCK` | 185 / 185 official minimum policy lot rows |
| `LOT_DISCRETIZATION_LIMITATION` | Confirmed structural contributor |
| `STRATEGY_SOFT_CAP_EXPRESSION_GAP` | Not confirmed for official minimum policy lots; partial one-lot counterfactual subset only |
| `PORTFOLIO_CONSTRUCTION_COMPETITION_GAP` | Not confirmed; 0 broad unexpected-stop cases, 18 insufficient |
| `CAPITAL_BUDGET_EXHAUSTION` | Not primary; only 2 separate `minimum_lot_exceeds_remaining_budget` skips |
| `BROKER_LOT_INFEASIBILITY` | Not primary; 12 separate `lot_or_broker_infeasible` skips |
| `OTHER` | PC skip reason naming/observability mismatch |

Primary root cause:

`EXPECTED_SAFETY_HARD_CAP_BLOCK_WITH_STRUCTURAL_LOT_DISCRETIZATION_LIMITATION`

## Regression Assessment

Regression is not confirmed.

The current behavior is bad for capital deployment, but there is no evidence that BUY_NEW previously had a working lot-aware Strategy soft-cap path that was later lost. L21D/L21F explicitly scoped the overshoot repair to existing-position BUY_ADD and did not change BUY_NEW semantics. The observed BUY_NEW limitation is therefore an architecture/design gap or current strategy expression limitation, not a proven regression.

## Architecture Assessment

PC is mostly behaving according to current design:

- It preserves PC as target-weight authority.
- It preserves PS as quantity authority.
- It preserves Safety hard cap.
- It continues competition to lower-ranked candidates in observed cases.
- It does not fabricate deployment simply because cash is available.

However, the design is not fully aligned with the system's capital deployment goal for a 1M JPY physical-equity portfolio. The combination of:

- 18% Strategy target cap,
- 25% Safety hard cap,
- 100-share round lots,
- minimum meaningful notional policy,
- high-price candidate distribution,

means that many high-quality top-ranked opportunities cannot be expressed at all. The artifact reason `minimum_lot_exceeds_concentration_cap` should also be improved because, for these 185 rows, the deeper reason is usually Safety-hard breach under the official minimum policy lot.

## Recommended Next Task

Recommended next task:

`Phase29-L21N — BUY_NEW Minimum-Lot Expression Policy / Safety-Aware One-Lot Authorization Design`

Scope:

- Design-only first.
- Do not relax Buy Quality, opportunity, market context, or Safety hard cap.
- Separate official minimum meaningful notional from exchange round-lot executability.
- Evaluate whether BUY_NEW may use a narrower one-round-lot expression rule when:
  - BQ action is acceptable,
  - opportunity rank is strong,
  - one lot remains within Safety hard cap,
  - one lot remains within target gross exposure and cash,
  - new-entry risk is explicitly recorded.
- Improve PC skip observability so Strategy-cap, Safety-hard, minimum-notional, and round-lot causes are not collapsed into one label.

## Primary Judgment

Required final answers:

1. Safety hard cap以内だった件数と割合: official minimum policy lotでは 0 / 185, 0.0%。one-round-lot counterfactualでは 40 / 185, 21.6%。
2. Strategy soft cap超過band: officialでは <=0.5pp 0, 0.5-1pp 0, 1-2pp 0, 2-5pp 0, >5pp 185。one-round-lotでは 2, 6, 4, 26, 147。
3. blocked lot notional分布: official median 600,000 JPY, average 792,735 JPY, total 146,655,960 JPY; one-lot median 300,000 JPY, average 396,367 JPY.
4. theoretical additional deployable capital: 5,914,400 JPY in sequential one-lot counterfactual.
5. theoretical average invested ratio: PC-stage gross exposure 47.87% -> 50.33%.
6. 高価格株固有問題か: one symbol onlyではないが、高価格/high-notional銘柄に強く集中する構造問題。
7. lower-ranked candidateへの繰り上げ: broad defectは未確認。31日は下位候補へ配分、101日は下位もinfeasible、18日は証跡不足。
8. Strategy soft capとSafety hard capの分離: 分離されている。ただし0.18の複数consumerがあり、BUY_NEWは例外なしでfail-closed。
9. BUY_NEW側lot-aware integration gap: official 185件ではSafety breachが主因なので未確認。ただしone-lot subsetには設計余地あり。
10. PCは現在設計通り動いているか: 概ねYES。
11. 設計通りでもCapital Deployment目標に不適切か: YES、1M JPY規模ではlot/minimum-notional policyが資金効率を制限する。
12. regression confirmedか: NO。
13. 実装修正が必要か: 直ちに実装ではなく、BUY_NEW one-lot expression policyの設計が必要。
14. 次Taskで修正すべきcomponent: Portfolio Construction and Position Sizing minimum-lot / BUY_NEW authorization contract, plus PC observability.

Primary judgment:

`PHASE29_L21M_OFFICIAL_PC_LOT_BLOCKS_ARE_SAFETY_HARD_CAP_BLOCKS_WITH_STRUCTURAL_ONE_LOT_BUY_NEW_EXPRESSION_GAP_NOT_REGRESSION`
