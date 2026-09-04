# Phase32-FE - 2023 Mar-May Drawdown / Risk-Off / Re-Capitalization Pacing READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Primary audit period: `2023-03-01` through `2023-05-08`
- Runtime observation at audit time: run was `RUNNING`, completed through `2023-05-12`, `next_job = 2023-05-15:market_refresh`.
- Evidence used: target-run daily artifacts, `strategy/market_context.json`, `strategy/portfolio_construction.json`, `strategy/position_sizing.json`, `execution/fills.json`, `current_valuation_refresh/valuation_projection.json`, PM decisions, Phase32-FD report, and current Risk Pacing / Market-Candidate-Cash Architecture SoT.
- Production changed: NO
- SHADOW changed: NO
- Config/schema changed: NO
- Target run mutated: NO
- Runtime state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Future return/PnL used for Production judgment: NO

## Executive Summary

Risk-off response is functional: when market quality moved to `CONFLICTED_MARKET_STRUCTURE`, `SHORT_TERM_BREADTH_BREAKDOWN`, `BEAR`, or `CORRECTION`, the artifacts show elevated SELL/REDUCE/EXIT activity, higher cash, and lower exposure.

The re-capitalization side is more aggressive. The 2023-04-10 to 2023-04-12 ramp from 62.0% to 93.3% exposure is mechanically explained by same-day/current PIT artifacts: 4/11 had `CAUTIOUS_DEPLOYMENT` with target gross 0.90, and 4/12 had `NORMAL_DEPLOYMENT` with target gross 1.00. The ramp did not exceed target gross exposure. However, the capital actually deployed during CAUTIOUS/GRADUAL states is often `COMPARABLE_MARGINAL`, and the current implementation treats `ELIGIBLE_COMPARABLE` as sufficient for deployment under `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`.

That is not a Runtime correctness defect: authority is complete, PIT-bound, and current-source-consistent. But it is a Risk-on pacing semantic concern: false-recovery protection exists as a concept, yet it does not impose a hard multi-day confirmation/ramp ceiling and does not distinguish enough between `COMPARABLE_HIGH` and `COMPARABLE_MARGINAL` in the effective deployment gate.

Selected judgment: `C. RISK_ON_PACING_CONCERN`.

## Architecture / Implementation Contract Check

The current Architecture SoT states:

- `RISK_PACING_OWNER = PORTFOLIO_POLICY`
- `RISK_PACING_CONSUMER = PORTFOLIO_CONSTRUCTION / BUY_QUALITY / POSITION_SIZING_AS_CONSUMER_OF_PC_TARGETS`
- Risk pacing expresses willingness to deploy marginal capital; it does not prescribe fixed exposure.
- `CAUTIOUS_DEPLOYMENT`: marginal deployment requires stronger contemporaneous evidence.
- `GRADUAL_REDEPLOYMENT`: redeployment may occur through confirmed competitors rather than abrupt forced exposure.
- Risk pacing is not a second candidate filter.

The implementation path in `strategy/portfolio_construction.py` preserves that broad architecture: `NORMAL_DEPLOYMENT` allows ordinary competition, while `CAUTIOUS_DEPLOYMENT`, `GRADUAL_REDEPLOYMENT`, and `PRESERVE_OPTIONALITY` apply risk-pacing reason codes to selected `NEW_BUY`/`ADD` competitors.

Important boundary found:

- Current implementation treats `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE` as sufficient for `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`.
- Actual artifacts show many `COMPARABLE_MARGINAL` candidates classified as `ELIGIBLE_COMPARABLE`, and therefore eligible to deploy during cautious/gradual states.
- This explains fast re-risking without requiring a bypass or future-data leak.

## Daily Risk State Trace

Condensed trace:

| Date | Regime | Market Quality | Breadth | Risk Intent | Target Gross | Cash Reserve | Exposure | Cash | POS | BUY_NEW | BUY_ADD | SELL | Added | Removed |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2023-03-08` | BULL | HEALTHY_EXPANSION | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 93.7% | 82,100 | 17 | 1 | 0 | 1 | 43,200 | 4,900 |
| `2023-03-10` | BULL | CONFLICTED_MARKET_STRUCTURE | STRONG | CAUTIOUS_DEPLOYMENT | 1.00 | 0.00 | 73.3% | 342,400 | 11 | 1 | 0 | 5 | 48,000 | 174,500 |
| `2023-03-17` | RANGE | SHORT_TERM_BREADTH_BREAKDOWN | NEUTRAL | CAUTIOUS_DEPLOYMENT | 1.00 | 0.00 | 68.0% | 397,060 | 9 | 1 | 0 | 5 | 159,800 | 304,750 |
| `2023-03-20` | CORRECTION | SHORT_TERM_BREADTH_BREAKDOWN | WEAK | CAUTIOUS_DEPLOYMENT | 0.82 | 0.18 | 67.3% | 411,660 | 9 | 1 | 0 | 1 | 20,500 | 35,100 |
| `2023-03-22` | RANGE | CONFLICTED_MARKET_STRUCTURE | NEUTRAL | CAUTIOUS_DEPLOYMENT | 1.00 | 0.00 | 91.8% | 103,160 | 12 | 3 | 0 | 0 | 308,500 | 0 |
| `2023-03-24` | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | NEUTRAL | GRADUAL_REDEPLOYMENT | 1.00 | 0.00 | 77.0% | 293,780 | 10 | 0 | 0 | 1 | 0 | 161,000 |
| `2023-03-27` | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | NEUTRAL | GRADUAL_REDEPLOYMENT | 1.00 | 0.00 | 91.4% | 115,380 | 11 | 1 | 0 | 0 | 178,400 | 0 |
| `2023-04-04` | RANGE | CONFLICTED_MARKET_STRUCTURE | NEUTRAL | CAUTIOUS_DEPLOYMENT | 1.00 | 0.00 | 94.7% | 77,100 | 9 | 0 | 1 | 0 | 85,800 | 0 |
| `2023-04-05` | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | WEAK | CAUTIOUS_DEPLOYMENT | 0.74 | 0.26 | 86.0% | 212,290 | 7 | 0 | 0 | 2 | 0 | 135,190 |
| `2023-04-06` | BEAR | SHORT_TERM_BREADTH_BREAKDOWN | WEAK | CAUTIOUS_DEPLOYMENT | 0.74 | 0.26 | 77.4% | 357,040 | 6 | 0 | 0 | 1 | 0 | 144,750 |
| `2023-04-10` | CORRECTION | SHORT_TERM_BREADTH_BREAKDOWN | WEAK | CAUTIOUS_DEPLOYMENT | 0.82 | 0.18 | 62.0% | 563,640 | 6 | 1 | 0 | 1 | 53,600 | 260,200 |
| `2023-04-11` | CORRECTION | SHORT_TERM_BREADTH_BREAKDOWN | NEUTRAL | CAUTIOUS_DEPLOYMENT | 0.90 | 0.10 | 79.9% | 294,810 | 11 | 6 | 0 | 1 | 323,630 | 54,800 |
| `2023-04-12` | BULL | HEALTHY_EXPANSION | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 93.3% | 97,910 | 13 | 2 | 0 | 0 | 196,900 | 0 |
| `2023-04-18` | BULL | HEALTHY_EXPANSION | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 96.0% | 58,830 | 9 | 1 | 0 | 0 | 239,500 | 0 |
| `2023-04-20` | BULL | HEALTHY_EXPANSION | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 67.0% | 467,530 | 9 | 1 | 0 | 2 | 80,100 | 382,200 |
| `2023-04-24` | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | STRONG | GRADUAL_REDEPLOYMENT | 1.00 | 0.00 | 56.0% | 653,830 | 9 | 4 | 0 | 2 | 304,000 | 521,300 |
| `2023-04-28` | RECOVERY | HEALTHY_RECOVERY | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 74.7% | 394,970 | 12 | 5 | 0 | 3 | 423,580 | 217,800 |
| `2023-05-01` | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | NEUTRAL | GRADUAL_REDEPLOYMENT | 1.00 | 0.00 | 90.7% | 146,190 | 12 | 2 | 0 | 2 | 370,400 | 121,620 |
| `2023-05-08` | BULL | HEALTHY_EXPANSION | STRONG | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 89.2% | 173,630 | 13 | 2 | 0 | 2 | 326,980 | 74,600 |

Window aggregates:

| Window | Dates | Exposure Start -> End | Avg Exposure | BUY_NEW | BUY_ADD | BUY_NEW Notional | BUY_ADD Notional | Sell Notional |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | `2023-03-08` to `2023-03-17` | 93.7% -> 68.0% | 81.0% | 12 | 0 | 905,000 | 0 | 1,181,660 |
| B | `2023-03-17` to `2023-04-10` | 68.0% -> 62.0% | 81.8% | 11 | 2 | 999,160 | 208,700 | 1,519,390 |
| C | `2023-04-10` to `2023-04-20` | 62.0% -> 67.0% | 82.9% | 14 | 0 | 1,013,730 | 0 | 1,124,220 |
| D | `2023-04-21` to `2023-05-08` | 70.5% -> 89.2% | 74.5% | 29 | 0 | 2,837,260 | 0 | 2,543,360 |

## Risk-Off Detection Speed

### Window A

- `RISK_OFF_SIGNAL_DATE = 2023-03-10`
- Evidence: market quality changed to `CONFLICTED_MARKET_STRUCTURE`, risk intent changed to `CAUTIOUS_DEPLOYMENT`.
- `FIRST_CAPITAL_REDUCTION_DATE = 2023-03-09`
- Evidence: 4 SELLs and 185,000 removed, before the explicit market-quality downgrade. This appears security/PM driven rather than market-regime driven.
- `MATERIAL_EXPOSURE_REDUCTION_DATE = 2023-03-10`
- Exposure moved from 93.7% on 3/8 to 73.3% on 3/10.
- `RISK_OFF_RESPONSE_LAG_BD = 0` from first explicit market-quality downgrade to material exposure reduction.

### April Weakening Into 2023-04-10

- `RISK_OFF_SIGNAL_DATE = 2023-04-05`
- Evidence: `BEAR`, `SHORT_TERM_BREADTH_BREAKDOWN`, `WEAK`, target gross 0.74, cash reserve 0.26.
- `FIRST_CAPITAL_REDUCTION_DATE = 2023-04-05`
- `MATERIAL_EXPOSURE_REDUCTION_DATE = 2023-04-06`
- Exposure moved from 94.7% on 4/4 to 77.4% on 4/6, then 62.0% on 4/10.
- `RISK_OFF_RESPONSE_LAG_BD = 1` to material <80% exposure, 3 business days to 62.0%.

### 2023-04-18 to 2023-04-20

- Market-context risk-off signal was not present: 4/20 remained `BULL / HEALTHY_EXPANSION / STRONG / NORMAL_DEPLOYMENT`.
- Exposure dropped from 96.0% to 67.0% because of security-level SELLs: `59350` SELL_EXIT 373,000 and `67400` REDUCE 9,200, partially offset by 80,100 BUY_NEW.
- This is not delayed market-risk detection; it is PM/security-driven de-risking inside a BULL market context.

## Risk-On Re-Entry Speed

### After 2023-03-20 CORRECTION

- `RISK_ON_SIGNAL_DATE = 2023-03-24` if requiring `RECOVERY`.
- But exposure had already reached 91.8% on `2023-03-22` while regime was `RANGE`, market quality `CONFLICTED_MARKET_STRUCTURE`, and risk intent `CAUTIOUS_DEPLOYMENT`.
- `EXPOSURE_70_DATE = 2023-03-22`
- `EXPOSURE_80_DATE = 2023-03-22`
- `EXPOSURE_90_DATE = 2023-03-22`
- `RECAPITALIZATION_LAG_BD = pre-confirmation / aggressive`

### 2023-04-10 to 2023-04-12

- `RISK_ON_SIGNAL_DATE = 2023-04-12` if requiring `BULL / HEALTHY_EXPANSION / STRONG / NORMAL_DEPLOYMENT`.
- `EXPOSURE_70_DATE = 2023-04-11`
- `EXPOSURE_80_DATE = 2023-04-12` because 4/11 finished just below 80% at 79.9%.
- `EXPOSURE_90_DATE = 2023-04-12`
- `RECAPITALIZATION_LAG_BD = 0` from full BULL/NORMAL signal to >90%, but the BUY_NEW ramp started one business day earlier under `CORRECTION / CAUTIOUS_DEPLOYMENT`.

## 2023-04-10 to 2023-04-12 Deep Dive

EOD state:

| Date | Regime | Market Quality | Risk Intent | Target Gross | Cash Reserve | Exposure | Cash | POS |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `2023-04-10` | CORRECTION | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 0.82 | 0.18 | 62.0% | 563,640 | 6 |
| `2023-04-11` | CORRECTION | SHORT_TERM_BREADTH_BREAKDOWN | CAUTIOUS_DEPLOYMENT | 0.90 | 0.10 | 79.9% | 294,810 | 11 |
| `2023-04-12` | BULL | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 1.00 | 0.00 | 93.3% | 97,910 | 13 |

Notional decomposition:

| Transition | Market Value Delta | BUY Notional | SELL Notional | Implied Existing-Holding Price Change | Cash Delta | Equity Delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 4/10 -> 4/11 | +256,110 | 323,630 | 54,800 | -12,720 | -268,830 | -12,720 |
| 4/11 -> 4/12 | +178,700 | 196,900 | 0 | -18,200 | -196,900 | -18,200 |
| Combined | +434,810 | 520,530 | 54,800 | -30,920 | -465,730 | -30,920 |

The 4/10 -> 4/12 exposure ramp is primarily BUY_NEW deployment:

- 4/11 BUY_NEW: 6 items, 323,630 notional.
- 4/12 BUY_NEW: 2 items, 196,900 notional.
- BUY_ADD: 0 in the ramp.
- Existing-holding valuation effect: negative, not the ramp driver.
- SELL reduction did not drive the ramp; SELLs removed 54,800 on 4/11 and none on 4/12.

PC / MCV evidence:

- 4/11 selected 12 PC members: 2 `ELIGIBLE_STRONG`, 10 `ELIGIBLE_COMPARABLE`, mostly `COMPARABLE_MARGINAL`.
- 4/12 selected 7 PC members: 1 `ELIGIBLE_STRONG`, 6 `ELIGIBLE_COMPARABLE`, again mostly `COMPARABLE_MARGINAL`.
- Artifacts explicitly record `future_information_used = false` and `historical_outcome_used = false` in the relevant opportunity/risk authority evidence.

Answer to the central question:

`2023_04_10_TO_04_12_RAMP_EXPLAINED = PARTIAL`

Mechanically and contractually, the ramp is explained by current artifacts and does not exceed target gross exposure. Semantically, it is aggressive because the ramp relies heavily on `COMPARABLE_MARGINAL` deployment under cautious/normal states and lacks multi-day false-recovery confirmation.

## False-Recovery Protection

False-recovery protection exists in concept:

- `CAUTIOUS_DEPLOYMENT`
- `GRADUAL_REDEPLOYMENT`
- cash competitor / optionality competitor
- market quality states such as `RECOVERY_CONFIRMATION_INCOMPLETE`
- target gross / cash reserve adjustments on some weak-market days

But the protection is not a hard ramp governor:

- It does not enforce a multi-day confirmation wait before returning to >90%.
- It does not enforce a per-day deployment ceiling.
- It does not consistently keep target gross below 1.0 under `CAUTIOUS_DEPLOYMENT`.
- It allows `ELIGIBLE_COMPARABLE`, including `COMPARABLE_MARGINAL`, to deploy during `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`.

Therefore:

- `FALSE_RECOVERY_PROTECTION_EXISTS = YES`
- `FALSE_RECOVERY_PROTECTION_ACTIVE = PARTIAL`

## Existing Holdings vs New Capital

For the most important 4/10 -> 4/12 ramp:

- Primary source: BUY_NEW.
- BUY_ADD contribution: none.
- Existing holding appreciation: not a contributor; implied existing-holding price change was negative.
- Retention / reduced selling: secondary, because 4/12 had no SELL removal, but the market value increase still came from new buys.

`EXPOSURE_RAMP_PRIMARY_SOURCE = BUY_NEW`

## Large Position Trace

### `76470`

The requested share path is explained by repeated ordinary BUY_NEW campaign transitions, not BUY_ADD:

| Date | Quantity After Fill / State | Action Evidence | PC / MCV |
| --- | ---: | --- | --- |
| `2023-03-28` | 2,000 | BUY_NEW 2,000, notional 52,000 | `semantic_buy_type=BUY_NEW`, `ELIGIBLE_COMPARABLE`, priority 6 |
| `2023-03-30` | 0 | SELL_EXIT 2,000 | PM EXIT / REMOVE |
| `2023-04-12` | 2,000 | BUY_NEW 2,000, notional 52,000 | `semantic_buy_type=BUY_NEW`, `ELIGIBLE_COMPARABLE`, priority 4 |
| `2023-04-14` | 1,500 | REDUCE 500 | PM REDUCE |
| `2023-04-17` | 0 | SELL_EXIT 1,500 | PM EXIT / REMOVE |
| `2023-04-21` | 3,800 | BUY_NEW 3,800, notional 98,800 | `semantic_buy_type=BUY_NEW`, `ELIGIBLE_COMPARABLE`, priority 2, target weight 7.14% |
| `2023-04-24` onward | 3,800 | HOLD / RETAIN | retained as current position |

`76470_04_21_3800_SHARES_EXPLAINED = YES_BY_ORDINARY_BUY_NEW_AFTER_PRIOR_EXIT_AND_NEW_CAMPAIGN_MATERIALIZATION`

### `67400`

- No position through 4/12.
- 4/13 BUY_NEW 1,100, notional 50,600, `ELIGIBLE_STRONG`, priority 2.
- 4/20 REDUCE 200.
- 4/21 SELL_EXIT remaining 900.

### `83060`

- Existing position retained into March/April.
- 4/04 BUY_ADD 100, notional 85,800, `ELIGIBLE_COMPARABLE`, ADD priority 1.
- Retained through 4/24, then SELL_EXIT 200 on 4/26.
- This is a genuine BUY_ADD winner-capitalization case, but not a driver of the 4/10 -> 4/12 ramp.

### `94320`

- Existing 700 shares retained through the period.
- PM ADD appears on several days, but no additional BUY_ADD fill in this window.
- PC target generally stayed at current weight; no ramp contribution.

## Exposure Ramp Concentration

Window C (`2023-04-10` to `2023-04-20`):

- Total added notional: 1,013,730.
- BUY_NEW added notional: 1,013,730.
- BUY_ADD added notional: 0.
- New symbols: 14.
- Top1 added: `60220` 239,500, 23.6% of added capital.
- Top3 added: 515,200, 50.8%.
- Top5 added: 655,200, 64.6%.

Window D (`2023-04-21` to `2023-05-08`):

- Total added notional: 2,837,260.
- BUY_NEW added notional: 2,837,260.
- BUY_ADD added notional: 0.
- New symbols: 24.
- Top1 added: `67310` 800,000, 28.2% of added capital.
- Top3 added: 1,274,720, 44.9%.
- Top5 added: 1,565,120, 55.2%.

Conclusion: re-risking is BUY_NEW-driven and moderately concentrated. It is not winner-ADD-driven. There is concentration amplification concern, especially when rapid BUY_NEW deployment coincides with high gross exposure, but not an execution or history-neutrality defect.

## Capital Deployment Quality

Selected/fill evidence by risk intent and opportunity quality:

| Risk Intent | Opportunity Class | Selected Count | Filled BUY Count | Filled Notional |
| --- | --- | ---: | ---: | ---: |
| CAUTIOUS_DEPLOYMENT | COMPARABLE_HIGH | 2 | 2 | 174,300 |
| CAUTIOUS_DEPLOYMENT | COMPARABLE_MARGINAL | 168 | 36 | 2,839,530 |
| CAUTIOUS_DEPLOYMENT | STRONG | 1 | 1 | 24,300 |
| GRADUAL_REDEPLOYMENT | COMPARABLE_HIGH | 2 | 2 | 91,930 |
| GRADUAL_REDEPLOYMENT | COMPARABLE_MARGINAL | 72 | 12 | 1,351,330 |
| GRADUAL_REDEPLOYMENT | STRONG | 2 | 1 | 57,000 |
| NORMAL_DEPLOYMENT | COMPARABLE_HIGH | 1 | 1 | 144,900 |
| NORMAL_DEPLOYMENT | COMPARABLE_MARGINAL | 93 | 20 | 1,586,830 |

No weak-quality or blocked deployment was found. The issue is not weak candidates bypassing quality gates. The issue is that cautious/gradual risk-on allows many marginal-comparable opportunities to deploy when cash also could be a valid competitor.

## REENTRY Regression Recheck

Within the FE window:

- `semantic_buy_type=REENTRY`: 0.
- stale prior-exit current authority: not found.
- expired guard suppression: not found.
- cross-run guard: not found.

This FE pacing issue should not be confused with the old long-lived REENTRY history penalty.

## Drawdown Amplification Mechanics

Mechanism classification:

- A. high gross exposure at market reversal: YES
- B. concentration in correlated/high-impact positions: YES_CONCERN
- C. delayed Risk-off: NO_MATERIAL_DELAY_FOUND
- D. too-fast Risk-on re-entry: YES_CONCERN
- E. weak BUY_NEW quality: NO
- F. excessive ADD: NO
- G. stale history / REENTRY issue: NO
- H. execution defect: NO
- I. normal market exposure cost: YES
- J. mixed: YES

This is a portfolio mechanics characterization, not a parameter-tuning conclusion.

## Repair Necessity

`PRODUCTION_REPAIR_JUSTIFIED = NOT_YET`

Reason:

- A correctness defect was not proven.
- No authority mismatch, stale data, future leakage, REENTRY regression, execution defect, or target-gross breach was found.
- Risk-off response is functional.
- Re-risking is aggressive and may be semantically under-confirmed, but deciding whether to change it requires an explicit Production design phase for false-recovery/ramp pacing. It should not be inferred from later drawdown alone.

Potential follow-up design boundary:

- Distinguish `COMPARABLE_HIGH` vs `COMPARABLE_MARGINAL` under `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`.
- Decide whether recovery from `CORRECTION`/`BEAR` requires bounded multi-day confirmation or a per-day deployment/ramp ceiling.
- Keep Risk Pacing as deployment-intensity authority, not a hidden candidate selector.

## Required Answers

- `RISK_OFF_RESPONSE_FUNCTIONAL = YES`
- `RISK_OFF_RESPONSE_LAG_MATERIAL = NO`
- `RISK_ON_RECAPITALIZATION_FUNCTIONAL = YES`
- `RISK_ON_RECAPITALIZATION_TOO_FAST = YES_CONCERN`
- `2023_04_10_TO_04_12_RAMP_EXPLAINED = PARTIAL`
- `FALSE_RECOVERY_PROTECTION_EXISTS = YES`
- `FALSE_RECOVERY_PROTECTION_ACTIVE = PARTIAL`
- `EXPOSURE_RAMP_PRIMARY_SOURCE = BUY_NEW`
- `BUY_NEW_DRIVES_RAMP = YES`
- `BUY_ADD_DRIVES_RAMP = NO`
- `EXISTING_HOLDINGS_DRIVE_RAMP = NO_PRIMARY`
- `76470_04_21_3800_SHARES_EXPLAINED = YES_BY_ORDINARY_BUY_NEW_NEW_CAMPAIGN`
- `HIGH_EXPOSURE_REVERSAL_COST_CONFIRMED = YES_AS_PORTFOLIO_MECHANICS_NOT_TUNING_BASIS`
- `CORRELATED_CONCENTRATION_CONCERN = YES_MODERATE`
- `WEAK_QUALITY_DEPLOYMENT_FOUND = NO`
- `REENTRY_REGRESSION_FOUND = NO`
- `RISK_PACING_SEMANTIC_GAP_FOUND = YES_DESIGN_CONCERN_NOT_RUNTIME_DEFECT`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NOT_YET`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Judgment Classification

Selected classification:

`C. RISK_ON_PACING_CONCERN`

This is not a HALT/root-cause correctness defect. It is a confirmed actual-path semantic concern: the system can re-risk very quickly through BUY_NEW after risk-off, especially because cautious/gradual deployment accepts many marginal-comparable competitors and has no hard false-recovery ramp governor.

## Final Judgment

`PHASE32_FE_RISK_OFF_FUNCTIONAL_RECAPITALIZATION_FUNCTIONAL_BUT_RISK_ON_PACING_CONCERN_FOUND_NO_CORRECTNESS_DEFECT_PRODUCTION_REPAIR_NOT_YET_LONG_HORIZON_SAFE_TO_CONTINUE`
