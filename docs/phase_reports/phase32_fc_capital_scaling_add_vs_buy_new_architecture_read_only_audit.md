# Phase32-FC - Capital Scaling / ADD vs BUY_NEW Architecture READ-ONLY Audit

## Scope

- Audit type: READ-ONLY architecture/source/config audit.
- Target context: current AI Fund Lab v2 Production source/config/Architecture SoT, plus existing Phase32 FB/EW/EZ/FA and marginal-capital reports.
- Source commit inspected: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`.
- Production/source/config/runtime state changed: NO.
- SHADOW changed: NO.
- fresh-run/resume/replay/recover executed: NO.
- Historical return/PnL/future outcome used for Production judgment: NO.

This audit asks whether capital sizing can scale with Portfolio Equity and whether ADD is structurally weaker than BUY_NEW because of fixed yen or fixed 100-share lot mechanics. It does not tune performance.

## Evidence Sources

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `configs/strategy/position_sizing.json`
- `configs/strategy/dynamic_cash_exposure.json`
- `configs/strategy/dynamic_position_count.json`
- `configs/safety/portfolio_limits.json`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `docs/phase_reports/phase32_fb_post_ez_extended_actual_path_semantic_capital_allocation_acceptance_audit.md`
- `docs/phase_reports/phase32_dp_winner_capitalization_unified_marginal_capital_allocation_deep_dive_shadow_audit.md`
- `docs/phase_reports/phase32_dq_unified_marginal_capital_authority_shadow_implementation.md`
- `docs/phase_reports/phase32_dr_production_vs_unified_marginal_capital_shadow_divergence_read_only_audit.md`
- `docs/phase_reports/phase32_ep_next_capital_unit_opportunity_evidence_shadow_audit.md`
- `docs/phase_reports/phase32_ew_reentry_current_decision_semantic_removal_recent_exit_guard_implementation.md`
- `docs/phase_reports/phase32_ez_bounded_recent_exit_guard_materialization_connectivity_repair.md`
- `docs/phase_reports/phase32_fa_ez_first_legitimate_divergence_recent_exit_guard_expiry_actual_path_acceptance_audit.md`

## Capital Flow Reference Graph

| Stage | Input | Output | Unit | Equity dependency | Rounding | Cap / gate |
| --- | --- | --- | --- | --- | --- | --- |
| Portfolio Equity | Current position summary `portfolio_total_equity` / `portfolio_value` | authoritative portfolio value | JPY | source of all notional scaling | none | fail-closed if invalid |
| Available Cash | current cash + Pending reservations | deployable cash evidence | JPY / ratio | cash amount scales with equity and realized state | none | no leverage, reservation, Pending gates |
| Risk / Exposure budget | market/regime/breadth/risk evidence | `target_gross_exposure_ratio` | ratio | percentage budget, not fixed yen | none | 0.0 to 1.0 exposure hard boundary |
| Dynamic position capacity | candidate/opportunity/liquidity counts, regime/risk posture | `target_position_count` | count | count is not directly equity-scaled | integer count | no routine fixed hard position-count cap |
| PC target allocation | eligible members, target exposure, count, single-name cap | `target_weight` | ratio | target notional later scales as `target_weight * equity` | target-weight precision | single-name cap / risk / BQ / Entry / opportunity |
| ADD target bridge | PM ADD, current weight, ADD evidence, headroom | post-ADD target / incremental weight | ratio | incremental notional later scales with equity | target-weight precision | expected edge, no-loss averaging, cap/headroom, risk |
| MCV competition | NEW/ADD competitors, accepted increments, quality/rank | marginal priority / accepted increment | ratio | comparable in weight space; not JPY-fixed | target-weight precision | Cash remains competitor; incomplete evidence may use stable order |
| Lot-aware PC reallocation | accepted weight, price, trading unit, portfolio value | executable compatibility and PC-positive quantity authority where applicable | ratio + shares | one-lot weight = price * unit / equity, so lot friction decreases as equity grows | floor to lots | cap headroom, safety hard cap, broker eligibility |
| Position Sizing | PC target weight, equity, reference price, trading unit | `target_notional`, `incremental_target_notional`, quantity candidate | JPY + shares | `target_notional = target_weight * equity`; ADD increment = increment_weight * equity | floor by `price * trading_unit` | minimum lot / price authority / cap |
| Runtime Planning / Pending | PS-bound quantity and provenance | Pending order item | shares / JPY reservation | consumes PS output, no rescale | none | G129 BUY_ADD order-increment validation |
| Submit / Execution | Pending order | broker/historical execution | shares | exact submitted quantity | broker/exchange | safety, CA, stale authority, duplicate/idempotency |

## Formula Classification

| Formula / parameter | Classification | Scaling reading |
| --- | --- | --- |
| `target_notional = target_weight * portfolio_value` | A. Portfolio Equity proportional | Core BUY_NEW and ADD notional scaling path. |
| `incremental_target_notional = increment_weight * portfolio_value` | A. Portfolio Equity proportional | Core BUY_ADD scaling path. |
| `transaction_quantity = floor(notional / (price * trading_unit)) * trading_unit` | F + nonlinear rounding | Uses fixed trading unit but accepts multiple lots; relative friction falls with equity. |
| `one_lot_weight = price * unit / portfolio_value` | A inverse + F | Fixed lot is converted to portfolio-relative weight. Larger equity reduces one-lot weight. |
| `target_gross_exposure_ratio` | D. fixed percentage / dynamic ratio | Ratio-driven, no fixed yen ceiling. |
| `strategy_maximum_position_weight = 0.18` | D. fixed percentage | Absolute position capacity scales with equity. |
| `safety.maximum_position_weight = 0.25` | D. fixed percentage | Safety hard cap scales with equity. |
| `minimum_meaningful_notional.base_jpy = 50000` | E. fixed yen, diagnostic | Source marks minimum meaningful notional as diagnostic in PS evidence; not a hard large-equity bottleneck. |
| `tradable_unit = 100` | F. fixed shares/lots | External lot constraint; not capped to one lot. |
| dynamic position count regime rules | H. count policy | Bounded by opportunity/risk, not directly equity-scaled. |
| cash/exposure safety limit | D. fixed percentage | No fixed cash reserve; cash is first-class optionality. |
| ADD acceleration tier | G. nonlinear ratio logic | Strong/exceptional tiers can increase incremental weight, bounded by headroom/risk/caps. |
| liquidity participation cap | D / market-capacity ratio | Can become a real large-capacity constraint for illiquid names, but is a safety/liquidity constraint rather than a fixed-yen bug. |

## BUY_NEW Initial Sizing

BUY_NEW target weight is resolved in PC from target gross exposure, eligible target member count, BQ/Entry/Opportunity evidence, capital competition, and single-name cap. Position Sizing then computes:

```text
target_notional = target_weight * portfolio_value
target_quantity_candidate = floor(target_notional / (reference_price * trading_unit)) * trading_unit
```

Therefore, with identical decision-time evidence and unchanged target weight, 10x equity gives approximately 10x target yen and, subject to lot rounding/caps/liquidity, approximately 10x shares. For small portfolios, a single lot can overshoot the continuous target; for larger portfolios, this friction decreases.

Answer: `BUY_NEW_SCALES_WITH_EQUITY = YES_WITH_LOT_AND_CAP_CONSTRAINTS`.

## BUY_ADD Scaling

BUY_ADD is not authorized by PM quantity. PM owns the directional ADD intent; PC owns incremental target weight; PS owns executable quantity; Runtime consumes the PS-bound order increment. The ADD bridge computes incremental weight from current weight, selected target, PM ADD evidence, expected-edge/incremental-value/opportunity-cost/no-loss-averaging evidence, cap/headroom, risk pacing, broker/safety/CA gates, and ADD acceleration tier.

Position Sizing then computes:

```text
transaction_target_notional = transaction_delta_weight * portfolio_value
transaction_quantity_candidate = floor(transaction_target_notional / (price * trading_unit)) * trading_unit
```

This means ADD can scale with equity when the same Winner evidence produces the same positive incremental weight and headroom remains available. Phase32-FB actual evidence confirmed valid BUY_ADD fills and G129-safe order increments for `76470`, `94340`, `94320`, and `45940`, with no unauthorized residual fallback.

Answer: `BUY_ADD_SCALES_WITH_EQUITY = YES_WITH_STRONGER_SEMANTIC_GATES_THAN_BUY_NEW`.

## ADD vs BUY_NEW Competition

ADD and BUY_NEW meet in PC as capital competitors in weight space:

- flat `ADD_CANDIDATE` rows are treated as `BUY_NEW`;
- current-position PM `ADD` rows are treated as `ADD`;
- MCV accepted increment compares `lot_aware_accepted_incremental_weight` / `accepted_incremental_weight` for ADD against `lot_aware_accepted_buy_new_weight` / `accepted_buy_new_weight` for BUY_NEW;
- lot-aware reallocation sorts candidates by capital binding, MCV priority, quality order, construction priority, and symbol;
- Cash remains a first-class competitor.

The comparison is not a fully calibrated single marginal-JPY utility function. Phase32-DP/DQ/DR/EP establish that a higher-resolution unified marginal-capital contract remains SHADOW/design territory, and Production promotion was not justified from those audits alone.

Answer: `MCV_ADD_NEW_COMPARABLE = YES_IN_WEIGHT_AND_PRIORITY_SPACE; NOT_FULLY_UNIFIED_MARGINAL_JPY`.

Answer: `MARGINAL_CAPITAL_SEMANTIC_GAP_REMAINS = PARTIAL`.

## Lot Size Scaling Risk

The current code does not impose "one lot only" as a general ADD or BUY_NEW ceiling.

- PC compatibility computes `lots = floor(allocation_weight / one_lot_weight)` and `projected_quantity_delta = lots * trading_unit`.
- PS computes floor quantity from notional and trading unit.
- G129 validates BUY_ADD submit quantity against the canonical order increment, not cumulative position size.
- Phase32-S architecture explicitly allows PS to convert PC continuous target into zero, one, or multiple 100-share lots.

Important nuance: the final lot-aware ADD competition has a staged one-increment path (`G115_STAGED_ADD_MARGINAL_ONE_INCREMENT`) so one decision may allocate the next marginal ADD step rather than the whole desired ADD in one shot. That is a marginal-capital pacing design, not proof of a fixed-lot scaling bottleneck. Static formula inspection shows that if an accepted incremental weight is larger than one-lot weight, PS can materialize multiple lots.

## Position Cap Scaling

Strategy cap and Safety cap are percentages:

- Strategy maximum position weight: `0.18`.
- Safety hard maximum position weight: `0.25`.

Thus absolute cap capacity scales with equity:

| Equity | 18% Strategy cap | 25% Safety cap |
| ---: | ---: | ---: |
| 1,000,000 | 180,000 | 250,000 |
| 3,000,000 | 540,000 | 750,000 |
| 10,000,000 | 1,800,000 | 2,500,000 |
| 30,000,000 | 5,400,000 | 7,500,000 |

Answer: a sufficiently strong Winner with valid ADD evidence can increase absolute position value as equity grows, until percentage cap, safety, risk pacing, liquidity, or current evidence blocks it.

## Position Count Expansion Risk

The current system does not use the runtime `max_positions=5` as a routine Production Strategy hard cap. Safety explicitly says there is no routine fixed position-count safety cap. Dynamic position count is driven by regime, breadth, volatility, portfolio policy, and available opportunity capacity.

There is still a conditional breadth risk: if ADD evidence is scarce or ADD competitors fail BQ/Entry/headroom/opportunity-cost gates while many NEW candidates are valid, capital can be deployed laterally into BUY_NEW. That is not a fixed-lot scaling defect; it is the intended consequence of current Production semantics plus opportunity/cap/risk gates.

Answer: `POSITION_COUNT_EXPANSION_RISK = CONDITIONAL_NOT_PROVEN_AS_ADD_SCALING_DEFECT`.

## Cash Utilization At Large Equity

The design distinguishes:

- cash because no valid opportunity / risk suppression / Cash optionality wins;
- cash because lot/cap/liquidity prevents executable deployment;
- cash because authority is missing or fail-closed.

At larger equity, 100-share lot friction becomes easier, not harder. The more realistic large-equity cash risk is market capacity/liquidity participation and percentage cap exhaustion for small/illiquid names. That is a real scaling validation topic, but source inspection did not reveal an artificial fixed-yen or fixed-one-lot bottleneck.

Answer: `CASH_ACCUMULATION_SCALING_RISK = CONDITIONAL_AT_LARGE_EQUITY_FROM_LIQUIDITY_CAPS_OR_VALID_OPPORTUNITY_SCARCITY`.

## Static Scenario Analysis

Assumptions for formula-only illustration:

- reference price: `1000`
- trading unit: `100`
- one lot notional: `100,000`
- BUY_NEW target weight: `5%`
- BUY_ADD current weight: `3%`
- BUY_ADD accepted incremental weight: `2%`
- strategy cap: `18%`
- no cash/risk/liquidity/broker/CA block

| Equity | One-lot weight | BUY_NEW target yen | BUY_NEW floor shares | BUY_ADD target yen | BUY_ADD floor shares | 18% cap yen | Reading |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1,000,000 | 10.00% | 50,000 | 0 unless one-lot admission | 20,000 | 0 | 180,000 | small-account lot friction dominates |
| 3,000,000 | 3.33% | 150,000 | 100 | 60,000 | 0 unless one-lot admission | 540,000 | BUY_NEW executable; ADD may need staged one-lot admission |
| 10,000,000 | 1.00% | 500,000 | 500 | 200,000 | 200 | 1,800,000 | both BUY_NEW and ADD scale materially |
| 30,000,000 | 0.33% | 1,500,000 | 1,500 | 600,000 | 600 | 5,400,000 | lot friction is small; caps/liquidity dominate |

Static result:

- 10M equity has structural headroom for multi-lot BUY_NEW and BUY_ADD if evidence/caps pass.
- 30M equity also has structural headroom, with liquidity/cap validation becoming more important.
- A fixed 100-share lot is not a large-equity bottleneck; it is mainly a small-equity granularity problem.

## Scaling Invariance Judgment

Classification: `B. MOSTLY_SCALE_INVARIANT_WITH_LOT_EFFECTS`.

Secondary flags:

- `E. POSITION_COUNT_EXPANSION_RISK`: conditional, if valid NEW candidates outnumber valid ADD competitors.
- `F. CASH_ACCUMULATION_SCALING_RISK`: conditional, mainly from liquidity/cap/opportunity scarcity at larger capital.
- `G. MATERIAL_CAPITAL_SCALING_GAP`: not proven.

## Repair Necessity

`PRODUCTION_REPAIR_JUSTIFIED = NO`

Reason:

- No artificial fixed-yen cap was found in the active scaling path.
- No fixed one-lot-only ceiling was found for BUY_NEW or BUY_ADD quantity materialization.
- BUY_NEW and BUY_ADD both convert ratio-based target/increment weights into equity-proportional notional.
- Position caps are percentage-based and absolute capacity scales with equity.
- Remaining marginal-capital comparability questions are already known SHADOW/design questions, not a newly proven capital-scaling correctness defect.

Recommended validation, not repair:

- run a future non-mutating/static or isolated fixture validation over 1M/3M/10M/30M synthetic current-portfolio states;
- include high-priced, low-priced, and liquidity-constrained names;
- assert multi-lot ADD/BUY_NEW quantities, cap boundaries, cash reason classification, and G129 order-increment scope.

## Required Final Answers

- `PORTFOLIO_EQUITY_PROPAGATES_TO_TARGET_VALUE = YES`
- `BUY_NEW_SCALES_WITH_EQUITY = YES_WITH_LOT_AND_CAP_CONSTRAINTS`
- `BUY_ADD_SCALES_WITH_EQUITY = YES_WITH_STRONGER_SEMANTIC_GATES_THAN_BUY_NEW`
- `ADD_TARGET_QUANTITY_CAN_GROW_MATERIALLY = YES`
- `MULTI_LOT_ADD_SUPPORTED = YES`
- `MCV_ADD_NEW_COMPARABLE = YES_IN_WEIGHT_AND_PRIORITY_SPACE; NOT_FULLY_UNIFIED_MARGINAL_JPY`
- `MARGINAL_CAPITAL_SEMANTIC_GAP_REMAINS = PARTIAL`
- `FIXED_YEN_SCALING_BOTTLENECK_FOUND = NO`
- `FIXED_LOT_SCALING_BOTTLENECK_FOUND = NO_FOR_LARGE_EQUITY; SMALL_EQUITY_LOT_GRANULARITY_EXISTS`
- `POSITION_CAP_SCALES_WITH_EQUITY = YES`
- `POSITION_COUNT_EXPANSION_RISK = CONDITIONAL_NOT_PROVEN_AS_ADD_SCALING_DEFECT`
- `CASH_ACCUMULATION_SCALING_RISK = CONDITIONAL_AT_LARGE_EQUITY_FROM_LIQUIDITY_CAPS_OR_VALID_OPPORTUNITY_SCARCITY`
- `10M_EQUITY_STRUCTURAL_HEADROOM = YES_WITH_CAP_LIQUIDITY_RISK_GATES`
- `30M_EQUITY_STRUCTURAL_HEADROOM = YES_WITH_LIQUIDITY_CAP_VALIDATION_REQUIRED`
- `CAPITAL_SCALING_DEFECT_PROVEN = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `DYNAMIC_CAPITAL_SCALING_VALIDATION_RECOMMENDED = YES`

## Final Judgment

`PHASE32_FC_CAPITAL_SCALING_ARCHITECTURE_MOSTLY_SCALE_INVARIANT_ADD_AND_BUY_NEW_REMAIN_COMPARABLE_NO_STRUCTURAL_10M_30M_HEADROOM_DEFECT_FOUND_DYNAMIC_VALIDATION_RECOMMENDED`
