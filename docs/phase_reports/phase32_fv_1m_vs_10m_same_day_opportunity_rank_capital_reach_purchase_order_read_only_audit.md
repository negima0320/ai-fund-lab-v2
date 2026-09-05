# Phase32-FV — 1M vs 10M Same-Day Opportunity Rank Capital-Reach / Purchase-Order READ-ONLY Audit

## Scope

- 1M baseline run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- 10M comparison run: `runtime-test-historical-extended-smoke-20260904T080740515158Z`
- Requested baseline window: first 100 completed 1M business days.
- Actual comparable window: 71 same completed business days, `2022-10-03` through `2023-01-17`.

The 10M run was still `RUNNING` with `next_job = 2023-01-18:market_refresh`; therefore the audit does not extrapolate to the full 100BD request.

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Target runtime state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- future return / PnL / MFE / MAE / later campaign outcome used for Production judgment: NO

## Evidence Sources

- `run_state.json` for both runs.
- Daily `strategy/portfolio_construction.json`.
- Daily `execution/fills.json`.
- Source contracts:
  - `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - `src/ai_fund_lab_v2/strategy/runtime_planning.py`
  - `docs/02_architecture/strategy_architecture_v1.md`
  - `docs/02_architecture/runtime_architecture_v2.md`

## Current BUY Process Order

`CURRENT_BUY_PROCESS_ORDER_CONFIRMED = YES`

The current architecture does not buy by raw opportunity rank alone.

Observed source path:

1. Opportunity Ranking owns canonical `opportunity_buy_rank`.
2. Portfolio Construction copies it into `input_opportunity_rank`.
3. `marginal_capital_value.apply_marginal_capital_priority` builds `canonical_marginal_capital_priority_index`.
4. Priority sort is:
   - `marginal_capital_value_class`
   - opportunity rank
   - sufficiency fallback flag
   - symbol
5. Portfolio Construction allocates incremental budget by that priority, with `competitor_ordering = marginal_capital_value_then_quality_then_construction_priority_then_symbol`.
6. Runtime Planning propagates `canonical_marginal_capital_priority_index`, `marginal_capital_value_class`, and `opportunity_buy_rank`; Runtime does not re-rank capital.

`OPPORTUNITY_RANK_TO_FINAL_PRIORITY_MAPPING = opportunity_buy_rank is preserved inside the same marginal-capital class, but final capital priority is class-first, then rank.`

Same-class rank order preservation:

| Run | Same-class ordered pairs | Preserved | Rate |
|---|---:|---:|---:|
| 1M | 3,071 | 3,071 | 100.0% |
| 10M | 4,191 | 4,191 | 100.0% |

`SAME_CLASS_RANK_ORDER_PRESERVED_RATE = 100.0% for both 1M and 10M comparable evidence`

## Daily Capital Reach Frontier

| Date | 1M buys | 1M deepest rank | 1M deepest priority | 10M buys | 10M deepest rank | 10M deepest priority |
|---|---:|---:|---:|---:|---:|---:|
| 2022-10-03 | 7 | 25 | 9 | 19 | 38 | 20 |
| 2022-10-04 | 3 | 20 | 6 | 9 | 35 | 9 |
| 2022-10-05 | 2 | 14 | 4 | 6 | 43 | 7 |
| 2022-10-06 | 4 | 15 | 4 | 8 | 43 | 8 |
| 2022-10-07 | 1 | 21 | 4 | 2 | 33 | 3 |
| 2022-10-11 | 0 | - | - | 4 | 22 | 5 |
| 2022-10-12 | 2 | 15 | 6 | 8 | 39 | 11 |
| 2022-10-13 | 2 | 21 | 8 | 5 | 36 | 7 |
| 2022-10-14 | 5 | 16 | 8 | 8 | 38 | 8 |
| 2022-10-17 | 1 | 18 | 5 | 6 | 43 | 6 |
| 2022-10-18 | 1 | 16 | 4 | 7 | 44 | 8 |
| 2022-10-19 | 3 | 23 | 9 | 9 | 42 | 10 |
| 2022-10-20 | 3 | 42 | 6 | 7 | 42 | 8 |
| 2022-10-21 | 1 | 25 | 10 | 9 | 44 | 12 |
| 2022-10-24 | 2 | 20 | 3 | 5 | 32 | 7 |
| 2022-10-25 | 2 | 34 | 2 | 8 | 45 | 11 |
| 2022-10-26 | 3 | 35 | 10 | 7 | 41 | 9 |
| 2022-10-27 | 2 | 19 | 4 | 4 | 24 | 6 |
| 2022-10-28 | 2 | 9 | 7 | 8 | 43 | 11 |
| 2022-10-31 | 2 | 43 | 4 | 8 | 43 | 10 |
| 2022-11-01 | 3 | 11 | 5 | 6 | 38 | 8 |
| 2022-11-02 | 0 | - | - | 1 | 39 | 2 |
| 2022-11-04 | 2 | 17 | 4 | 6 | 39 | 8 |
| 2022-11-07 | 2 | 22 | 4 | 6 | 42 | 6 |
| 2022-11-08 | 4 | 42 | 7 | 8 | 43 | 10 |
| 2022-11-09 | 4 | 26 | 9 | 6 | 43 | 8 |
| 2022-11-10 | 2 | 42 | 5 | 5 | 43 | 7 |
| 2022-11-11 | 2 | 43 | 2 | 3 | 43 | 8 |
| 2022-11-14 | 1 | 8 | 2 | 3 | 27 | 6 |
| 2022-11-15 | 2 | 19 | 7 | 5 | 45 | 6 |
| 2022-11-16 | 1 | 21 | 1 | 5 | 45 | 7 |
| 2022-11-17 | 2 | 26 | 7 | 4 | 26 | 6 |
| 2022-11-18 | 2 | 34 | 3 | 2 | 34 | 5 |
| 2022-11-21 | 1 | 38 | 2 | 8 | 44 | 9 |
| 2022-11-22 | 1 | 39 | 1 | 3 | 44 | 8 |
| 2022-11-24 | 1 | 12 | 3 | 6 | 24 | 6 |
| 2022-11-25 | 1 | 2 | 3 | 2 | 39 | 2 |
| 2022-11-28 | 3 | 10 | 4 | 5 | 30 | 7 |
| 2022-11-29 | 2 | 21 | 7 | 8 | 42 | 11 |
| 2022-11-30 | 2 | 5 | 2 | 2 | 39 | 3 |
| 2022-12-01 | 2 | 4 | 2 | 4 | 36 | 7 |
| 2022-12-02 | 1 | 34 | 1 | 8 | 43 | 11 |
| 2022-12-05 | 0 | - | - | 7 | 44 | 9 |
| 2022-12-06 | 1 | 16 | 1 | 6 | 43 | 10 |
| 2022-12-07 | 3 | 39 | 8 | 7 | 41 | 8 |
| 2022-12-08 | 3 | 37 | 13 | 5 | 45 | 6 |
| 2022-12-09 | 1 | 33 | 2 | 10 | 44 | 11 |
| 2022-12-12 | 1 | 41 | 4 | 4 | 40 | 9 |
| 2022-12-13 | 2 | 37 | 3 | 6 | 41 | 10 |
| 2022-12-14 | 0 | - | - | 6 | 43 | 7 |
| 2022-12-15 | 3 | 42 | 5 | 4 | 43 | 8 |
| 2022-12-16 | 3 | 32 | 5 | 5 | 42 | 5 |
| 2022-12-19 | 3 | 9 | 4 | 0 | - | - |
| 2022-12-20 | 0 | - | - | 1 | 29 | 7 |
| 2022-12-21 | 5 | 14 | 5 | 11 | 33 | 14 |
| 2022-12-22 | 1 | 12 | 1 | 4 | 23 | 4 |
| 2022-12-23 | 1 | 2 | 3 | 11 | 40 | 11 |
| 2022-12-26 | 2 | 33 | 4 | 7 | 43 | 7 |
| 2022-12-27 | 1 | 41 | 1 | 5 | 43 | 5 |
| 2022-12-28 | 0 | - | - | 6 | 45 | 15 |
| 2022-12-29 | 4 | 15 | 4 | 8 | 38 | 14 |
| 2022-12-30 | 2 | 35 | 3 | 5 | 44 | 8 |
| 2023-01-04 | 5 | 23 | 10 | 2 | 21 | 5 |
| 2023-01-05 | 4 | 11 | 8 | 5 | 38 | 9 |
| 2023-01-06 | 4 | 23 | 9 | 2 | 9 | 3 |
| 2023-01-10 | 2 | 28 | 12 | 3 | 19 | 6 |
| 2023-01-11 | 3 | 20 | 7 | 7 | 23 | 8 |
| 2023-01-12 | 1 | 6 | 1 | 4 | 26 | 7 |
| 2023-01-13 | 2 | 23 | 8 | 5 | 37 | 9 |
| 2023-01-16 | 1 | 25 | 9 | 4 | 44 | 13 |
| 2023-01-17 | 2 | 8 | 3 | 4 | 36 | 8 |

`DAILY_CAPITAL_REACH_FRONTIER_1M = median deepest purchased rank 21, median deepest purchased priority 4`

`DAILY_CAPITAL_REACH_FRONTIER_10M = median deepest purchased rank 41, median deepest purchased priority 8`

## Aggregate Purchase Metrics

| Metric | 1M | 10M |
|---|---:|---:|
| Comparable completed days | 71 | 71 |
| Total BUY fills | 149 | 407 |
| BUY_NEW fills | 132 | 390 |
| BUY_ADD fills | 17 | 17 |
| Total BUY notional | 7,013,430 | 84,374,880 |
| Average funded BUY count / day | 2.099 | 5.732 |
| Median deepest purchased rank | 21 | 41 |
| Median deepest priority index | 4 | 8 |

`MEDIAN_DEEPEST_PURCHASED_RANK_1M = 21`

`MEDIAN_DEEPEST_PURCHASED_RANK_10M = 41`

`MEDIAN_DEEPEST_PRIORITY_INDEX_1M = 4`

`MEDIAN_DEEPEST_PRIORITY_INDEX_10M = 8`

`AVG_FUNDED_BUY_COUNT_1M = 2.099`

`AVG_FUNDED_BUY_COUNT_10M = 5.732`

## 10M-Only Additional BUY Cohort

Definition: same date and same `symbol + source_decision_type` was bought in 10M but not bought in 1M.

- `TEN_M_ONLY_ADDITIONAL_BUY_COUNT = 330`
- `TEN_M_ONLY_ADDITIONAL_BUY_NOTIONAL = 70,821,760`
- Type distribution: `BUY_NEW = 325`, `BUY_ADD = 5`
- All 330 appeared in 1M PC evidence on the same date.
- 70 / 330 had positive 1M PC target weight but did not become a 1M BUY fill.

Rank distribution:

| Rank bucket | Count |
|---|---:|
| 1-5 | 11 |
| 6-10 | 16 |
| 11-20 | 54 |
| 21+ | 249 |

Priority distribution:

| Priority bucket | Count |
|---|---:|
| 1-5 | 171 |
| 6-10 | 134 |
| 11-20 | 25 |

Quality distribution:

| Quality | Count |
|---|---:|
| `COMPARABLE_MARGINAL` | 275 |
| `COMPARABLE_HIGH` | 40 |
| `STRONG` | 15 |

Marginal capital class distribution:

| Class | Count |
|---|---:|
| `ELIGIBLE_COMPARABLE` | 275 |
| `ELIGIBLE_STRONG` | 55 |

Target weight distribution:

- Median: `0.0202335`
- Average: `0.022660`
- Maximum: `0.090045`

`TEN_M_ONLY_ADDITIONAL_BUY_RANK_DISTRIBUTION = 249/330 are rank 21+`

`TEN_M_ONLY_ADDITIONAL_BUY_QUALITY_DISTRIBUTION = mostly COMPARABLE_MARGINAL`

`TEN_M_ONLY_ADDITIONAL_BUY_TARGET_WEIGHT_DISTRIBUTION = median 2.02%, average 2.27%, max 9.00%`

## Capital Scale Frontier

The 10M run expands breadth and reaches deeper ranks/priorities. This is not primarily a high-price minimum-lot unlock.

- 187 / 330 10M-only additional buys had deeper priority than the 1M same-day deepest filled priority, or occurred on a day where 1M had no BUY.
- 228 / 330 had deeper opportunity rank than the 1M same-day deepest filled rank, or occurred on a day where 1M had no BUY.
- The scan found no reliable same-day 1M PC reason-code evidence that these 10M-only buys were primarily high-price / minimum-lot newly feasible cases.
- Average same-day symbol overlap between 1M and 10M BUY sets was low: Jaccard average `0.167`.

`HIGH_PRICE_NEWLY_FEASIBLE_SHARE = 0.0 by observed 1M reason-code evidence; high-price lot feasibility is not the primary explanation`

`LOWER_PRIORITY_CAPITAL_REACH_SHARE = 0.567 by priority, 0.691 by opportunity rank`

`CORE_SECURITY_OVERLAP_1M_10M = LOW, average same-day BUY symbol Jaccard 0.167`

`ONE_M_IMPLICIT_CAPITAL_CUTOFF_EXISTS = YES`

`TEN_M_CAPITAL_FRONTIER_EXPANDS = YES`

## Fixed Top-N Sensitivity

Using 10M actual BUY fills as the scale-expanded same-day purchase set:

| Fixed rank cap | 10M actual buys excluded |
|---|---:|
| Top 10 only | 347 / 407, 85.3% |
| Top 15 only | 313 / 407, 76.9% |
| Top 20 only | 271 / 407, 66.6% |

This does not prove all lower-rank purchases are desirable. It does prove a fixed raw opportunity-rank cap would be a major architecture change, because current Production intentionally allows class-first marginal-capital competition to fund deeper-ranked `ELIGIBLE_COMPARABLE` names when capital scale permits.

`FIXED_TOP_N_ARCHITECTURALLY_JUSTIFIED = NO as a hard Production rule based on current evidence`

## Interpretation

The strongest observed fact is scale-dependent capital reach:

- 1M tends to stop around priority `4` and rank `21`.
- 10M tends to reach priority `8` and rank `41`.
- 10M additional buying is mostly deeper-rank, lower-priority, `COMPARABLE_MARGINAL` BUY_NEW.
- Same-class ordering itself is preserved, so this is not a rank propagation defect.

This means the 1M run has an implicit capital frontier, while the 10M run crosses that frontier and buys a substantially wider set of candidates. The widened set is not explained by Runtime re-ranking or by a campaign/provenance failure in the inspected evidence.

The evidence supports a capital-scale sensitivity rather than a correctness defect:

- With more capital, the system funds more same-day opportunities.
- Those opportunities are often lower raw opportunity rank and lower marginal priority.
- The current architecture does not contain an explicit scale-aware capital conviction floor that says, for example, "beyond this priority/rank/quality boundary, keep cash instead of funding another comparable candidate."

`EXISTING_CAPITAL_CONVICTION_SIGNAL_SUFFICIENT = PARTIAL`

There is a signal stack: BQ, marginal capital value class, opportunity rank, PC target, Entry, and risk controls. However, the evidence does not show a distinct scale-aware "next capital unit conviction floor" strong enough to preserve the 1M purchase frontier when capital increases 10x.

## Root Cause Classification

`CAPITAL_SCALE_INVARIANCE_CLASS = NOT_SCALE_INVARIANT_BY_BREADTH`

`ROOT_CAUSE_CLASSIFICATION = CAPITAL_FRONTIER_EXPANSION_WITHOUT_EXPLICIT_SCALE_AWARE_CONVICTION_FLOOR`

This is not a proven Architecture/SoT/PIT correctness defect. It is a design property: current Production treats additional capital as permission to keep funding eligible comparable opportunities deeper in the priority queue.

## Review Justification

- `INVESTMENT_ELIGIBILITY_REVIEW_JUSTIFIED = YES`
- `CAPITAL_PRIORITY_REVIEW_JUSTIFIED = YES`
- `CAPITAL_CONVICTION_FLOOR_REVIEW_JUSTIFIED = YES`
- `ADD_NEW_UNIFICATION_REVIEW_JUSTIFIED = YES, but as design research only`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`

The next design work should not start by hard-capping raw rank. A better follow-up is a SHADOW scale-aware next-capital-unit conviction frontier that compares cash, NEW, ADD, and REENTRY/relationship candidates under the same decision-time evidence, then characterizes whether deeper 10M-funded opportunities have enough marginal conviction to justify deployment.

`NEXT_DESIGN_DIRECTION = SHADOW scale-aware next-capital-unit conviction frontier; do not promote a hard top-N Production rule from FV alone`

## Final Required Answers

- `CURRENT_BUY_PROCESS_ORDER_CONFIRMED = YES`
- `OPPORTUNITY_RANK_TO_FINAL_PRIORITY_MAPPING = class-first marginal-capital priority; opportunity rank preserved within class`
- `SAME_CLASS_RANK_ORDER_PRESERVED_RATE = 100.0%`
- `DAILY_CAPITAL_REACH_FRONTIER_1M = median deepest rank 21 / priority 4`
- `DAILY_CAPITAL_REACH_FRONTIER_10M = median deepest rank 41 / priority 8`
- `MEDIAN_DEEPEST_PURCHASED_RANK_1M = 21`
- `MEDIAN_DEEPEST_PURCHASED_RANK_10M = 41`
- `MEDIAN_DEEPEST_PRIORITY_INDEX_1M = 4`
- `MEDIAN_DEEPEST_PRIORITY_INDEX_10M = 8`
- `AVG_FUNDED_BUY_COUNT_1M = 2.099`
- `AVG_FUNDED_BUY_COUNT_10M = 5.732`
- `TEN_M_ONLY_ADDITIONAL_BUY_COUNT = 330`
- `TEN_M_ONLY_ADDITIONAL_BUY_NOTIONAL = 70,821,760`
- `TEN_M_ONLY_ADDITIONAL_BUY_RANK_DISTRIBUTION = 1-5:11, 6-10:16, 11-20:54, 21+:249`
- `TEN_M_ONLY_ADDITIONAL_BUY_QUALITY_DISTRIBUTION = COMPARABLE_MARGINAL:275, COMPARABLE_HIGH:40, STRONG:15`
- `TEN_M_ONLY_ADDITIONAL_BUY_TARGET_WEIGHT_DISTRIBUTION = median 0.0202335, average 0.022660, max 0.090045`
- `HIGH_PRICE_NEWLY_FEASIBLE_SHARE = 0.0 by observed same-day 1M reason-code evidence`
- `LOWER_PRIORITY_CAPITAL_REACH_SHARE = 0.567 priority / 0.691 opportunity rank`
- `CORE_SECURITY_OVERLAP_1M_10M = LOW, average Jaccard 0.167`
- `EXISTING_CAPITAL_CONVICTION_SIGNAL_SUFFICIENT = PARTIAL`
- `ONE_M_IMPLICIT_CAPITAL_CUTOFF_EXISTS = YES`
- `TEN_M_CAPITAL_FRONTIER_EXPANDS = YES`
- `CAPITAL_SCALE_INVARIANCE_CLASS = NOT_SCALE_INVARIANT_BY_BREADTH`
- `ROOT_CAUSE_CLASSIFICATION = CAPITAL_FRONTIER_EXPANSION_WITHOUT_EXPLICIT_SCALE_AWARE_CONVICTION_FLOOR`
- `FIXED_TOP_N_ARCHITECTURALLY_JUSTIFIED = NO`
- `INVESTMENT_ELIGIBILITY_REVIEW_JUSTIFIED = YES`
- `CAPITAL_PRIORITY_REVIEW_JUSTIFIED = YES`
- `CAPITAL_CONVICTION_FLOOR_REVIEW_JUSTIFIED = YES`
- `ADD_NEW_UNIFICATION_REVIEW_JUSTIFIED = YES_DESIGN_ONLY`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `NEXT_DESIGN_DIRECTION = SHADOW scale-aware next-capital-unit conviction frontier`

Final Judgment: `PHASE32_FV_1M_VS_10M_CAPITAL_REACH_AUDIT_ACCEPTED_SCALE_FRONTIER_EXPANDS_NO_CORRECTNESS_DEFECT`
