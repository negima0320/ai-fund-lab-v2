# Phase32-EL — 2024-03 Drawdown Market Regime / Risk Response PIT Correctness READ-ONLY Audit

## Scope

- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Focus window: `2024-02-27` through `2024-03-19`
- Primary drawdown window observed in this audit: `2024-03-05` equity `2,061,840` to `2024-03-15` equity `1,795,990`, approximately `-12.89%`.
- Evidence used: target-run daily artifacts only, especially `strategy/market_context.json`, `strategy/portfolio_policy.json`, `strategy/portfolio_construction.json`, `strategy/buy_quality_decisions.json`, `position_management/pm_decisions.json`, `execution/fills.json`, `current_valuation_refresh/valuation_projection.json`, and `positions/position_campaigns.json`.
- No fresh-run, resume, recover, replay, source/config change, Production change, SHADOW change, or runtime-state mutation was executed.

## Current Source / Run Identity

- Run status in `run_state.json`: `RUNNING`
- Current continuation point: `2024-03-26:morning`
- Source baseline after accepted source transition:
  - old source commit: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
  - current source commit: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
  - accepted artifact hash: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`
  - registry hash: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`
- EL target dates are already completed; sampled job `cli_result.json` files for `morning`, `sell_planning`, `submit`, `execution`, and `current_valuation_refresh` on `2024-03-08`, `2024-03-11`, `2024-03-14`, and `2024-03-15` all have exit code `0`.

## REGIME_PIT_DECISION_TABLE

Market Context contract observed from `strategy/market_context.json`:

- Trend metric: `return_20d_equal_weight`
- BULL threshold: `return_20d_equal_weight >= 0.02`
- BEAR threshold: `return_20d_equal_weight <= -0.02`
- Breadth metric: `breadth_20d_positive_ratio`
- Strong breadth threshold: `>= 0.6`; weak breadth threshold: `<= 0.4`
- Volatility metric: `volatility_20d_equal_weight`; high volatility threshold: `>= 0.04`
- PIT contract: `feature_date_lte_business_date=true`, `future_leakage_used=false`, `latest_fallback_used=false`, `previous_day_context_copied=false`

| Date | Regime | 20d Trend | Breadth | Volatility | Confidence | Uncertainty | Regime reason codes | Risk pacing |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- |
| 2024-02-27 | BULL | 0.035818 | NEUTRAL 0.5860 | NORMAL | 0.9933 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-02-28 | BULL | 0.032502 | NEUTRAL 0.5504 | NORMAL | 0.9929 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-02-29 | BULL | 0.032962 | NEUTRAL 0.5613 | NORMAL | 0.9900 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-01 | BULL | 0.027279 | NEUTRAL 0.5321 | NORMAL | 0.9919 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-04 | BULL | 0.032477 | NEUTRAL 0.5416 | NORMAL | 0.9927 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-05 | BULL | 0.032915 | NEUTRAL 0.5372 | NORMAL | 0.9910 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-06 | BULL | 0.034877 | NEUTRAL 0.5458 | NORMAL | 0.9937 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-07 | BULL | 0.034289 | NEUTRAL 0.5555 | NORMAL | 0.9918 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-08 | BULL | 0.036231 | NEUTRAL 0.5724 | NORMAL | 0.9925 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-11 | BULL | 0.020890 | NEUTRAL 0.5186 | NORMAL | 0.9934 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-12 | BULL | 0.032664 | NEUTRAL 0.5865 | NORMAL | 0.9943 | LOW | trend:BULL, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-13 | RANGE | 0.019046 | NEUTRAL 0.5223 | NORMAL | 0.9937 | LOW | trend:RANGE, breadth:NEUTRAL, volatility:NORMAL | CAUTIOUS |
| 2024-03-14 | BULL | 0.033279 | STRONG 0.6219 | NORMAL | 0.9943 | LOW | trend:BULL, breadth:STRONG, volatility:NORMAL | CAUTIOUS |
| 2024-03-15 | BULL | 0.041400 | STRONG 0.7000 | NORMAL | 0.9932 | LOW | trend:BULL, breadth:STRONG, volatility:NORMAL | CAUTIOUS |
| 2024-03-18 | BULL | 0.040389 | STRONG 0.6872 | NORMAL | 0.9940 | LOW | trend:BULL, breadth:STRONG, volatility:NORMAL | NORMAL |
| 2024-03-19 | BULL | 0.033776 | STRONG 0.6640 | NORMAL | 0.9902 | LOW | trend:BULL, breadth:STRONG, volatility:NORMAL | NORMAL |

## MARCH_BULL_CLASSIFICATION_ROOT_CAUSE

Focused dates:

- `2024-03-08`: `PIT_EVIDENCE_SUPPORTS_BULL`. 20d equal-weight return was `0.0362305`, above the BULL threshold, breadth was NEUTRAL, volatility NORMAL, confidence `0.9925`, no future rows used.
- `2024-03-11`: `BORDERLINE_BUT_CONTRACT_VALID`. 20d return was `0.0208895`, barely above the BULL threshold. Short-term 5d breadth was weak (`0.3874`) and Risk Pacing evidence recorded `MARKET_QUALITY_FRAGILE` / `SHORT_TERM_PARTICIPATION_NARROWING`, but final regime remained BULL under the explicit 20d trend contract.
- `2024-03-14`: `PIT_EVIDENCE_SUPPORTS_BULL`. 20d return recovered to `0.0332791`, 20d breadth was STRONG (`0.6219`), volatility NORMAL. Short-term 5d return remained slightly negative and Risk Pacing still recorded narrowing/fragility, so the day is not an all-clear internally, but BULL is contract-supported.
- `2024-03-15`: `PIT_EVIDENCE_SUPPORTS_BULL`. 20d return was `0.0414005`, 20d breadth STRONG (`0.7000`), volatility NORMAL. 5d breadth was weak (`0.3923`) and Risk Pacing still CAUTIOUS, so the evidence contained near-term fragility but not a regime-authority defect.

Finding: BULL was not stale or unsupported. The BULL root cause is the Market Context regime contract privileging the 20d equal-weight return and 20d breadth state; short-term deterioration appears in component evidence and Risk Pacing, but does not override the final BULL label unless the configured trend/volatility thresholds are crossed.

## MARKET_VS_SECURITY_INTERNAL_DIVERGENCE

There was contemporaneous internal deterioration even while the headline regime often remained BULL:

- Risk Pacing component evidence:
  - `2024-03-08`: `CONFLICTED_MARKET_STRUCTURE`
  - `2024-03-11`: `SHORT_TERM_BREADTH_BREAKDOWN`, with `MARKET_QUALITY_FRAGILE` and `SHORT_TERM_PARTICIPATION_NARROWING`
  - `2024-03-14`: `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`
  - `2024-03-15`: `SHORT_TERM_BREADTH_BREAKDOWN`
- PM weakening response was active:
  - `2024-03-05`: `EXIT=2`, `REDUCE=4`
  - `2024-03-08`: `EXIT=1`, `REDUCE=2`
  - `2024-03-11`: `EXIT=1`, `REDUCE=1`
  - `2024-03-14`: `EXIT=1`, `REDUCE=3`
  - `2024-03-15`: `EXIT=4`, `REDUCE=2`
- Candidate quality did not collapse:
  - `2024-03-11`: BQ actions were `FULL=4`, `REDUCED=21`, `BUY_WAIT=18`, `REVIEW_REQUIRED=1`, `REJECT=6`; average quality score about `0.552`.
  - `2024-03-14`: BQ actions were `FULL=4`, `REDUCED=24`, `BUY_WAIT=17`, `REJECT=5`; average quality score about `0.576`.
  - `2024-03-15`: BQ actions were `FULL=3`, `REDUCED=19`, `BUY_WAIT=23`, `REVIEW_REQUIRED=1`, `REJECT=4`; average quality score about `0.578`.

Judgment: internal deterioration was visible in PIT evidence, especially short-term breadth and PM sell/reduce reasons. It was not missing from the system. The remaining gap is representational: final headline Regime stayed BULL because its authority is medium-horizon market trend/breadth/volatility, while short-term fragility lives in Risk Pacing and security-level decisions.

## REGIME_TRANSITION_TIMING_JUDGMENT

`CONSERVATIVE_BUT_VALID`.

The transition to RANGE occurred on `2024-03-13`, exactly when the 20d equal-weight return fell below the BULL threshold (`0.0190457 < 0.02`). The immediate return to BULL on `2024-03-14` was also contract-valid because the 20d return rose back above threshold and 20d breadth became STRONG. The transition was conservative in the sense that 5d breadth weakness was present earlier (`2024-03-11`) and again on `2024-03-15`, but that evidence was not the final regime trigger under the current contract.

No stale data, missing source authority, future leakage, or schema/registry authority defect was found in Market Context for the audited dates.

## MARCH_RISK_PACING_RESPONSE_PROFILE

| Date | Regime | Equity | Exposure | Cash | Positions | Risk pacing | PM ADD/HOLD/REDUCE/EXIT | Fills BUY/SELL notional |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 2024-03-04 | BULL | 2,027,640 | 90.12% | 200,410 | 13 | CAUTIOUS | 1/10/2/0 | 0 / 0 |
| 2024-03-05 | BULL | 2,061,840 | 55.73% | 912,710 | 11 | CAUTIOUS | 1/6/4/2 | 132,500 / 844,800 |
| 2024-03-07 | BULL | 2,045,030 | 81.52% | 378,010 | 13 | CAUTIOUS | 1/7/4/1 | 417,000 / 113,800 |
| 2024-03-08 | BULL | 1,975,590 | 79.01% | 414,710 | 11 | CAUTIOUS | 1/9/2/1 | 260,100 / 296,800 |
| 2024-03-11 | BULL | 1,887,810 | 65.40% | 653,210 | 11 | CAUTIOUS | 1/8/1/1 | 92,000 / 330,500 |
| 2024-03-12 | BULL | 1,908,720 | 81.47% | 353,610 | 14 | CAUTIOUS | 2/5/3/1 | 512,900 / 213,300 |
| 2024-03-13 | RANGE | 1,931,330 | 81.02% | 366,640 | 13 | CAUTIOUS | 2/7/3/2 | 327,000 / 340,030 |
| 2024-03-14 | BULL | 1,826,290 | 82.84% | 313,440 | 15 | CAUTIOUS | 2/7/3/1 | 234,000 / 180,800 |
| 2024-03-15 | BULL | 1,795,990 | 63.74% | 651,190 | 11 | CAUTIOUS | 2/7/2/4 | 176,600 / 514,350 |
| 2024-03-18 | BULL | 1,865,640 | 76.36% | 440,990 | 12 | NORMAL | 3/4/3/1 | 527,700 / 317,500 |
| 2024-03-19 | BULL | 1,892,200 | 93.53% | 122,430 | 18 | NORMAL | 2/8/2/0 | 346,360 / 27,800 |

Risk response explanation:

- `2024-03-05` exposure fell from about `90%` to `56%` because sell notional (`844,800`) far exceeded buy notional (`132,500`). PM issued two EXITs and four REDUCE intents, including `55740 EXIT` for `profit_retention_break` and `76890 EXIT` for `weak_hold_score`.
- `2024-03-07` exposure rose back to about `82%` because the system bought `55950` for `417,000` while still selling `43760` and reducing `97040`. Risk Pacing remained CAUTIOUS; it did not prohibit re-risking when eligible BUY authority existed.
- `2024-03-11` exposure fell to about `65%` after `55950 EXIT` with `hard_stop_current_return`, sell notional `330,500`, and only `92,000` buy notional.
- `2024-03-14` exposure rose again to about `83%` through multiple BUY_NEW fills while regime returned to BULL and 20d breadth was STRONG; Risk Pacing still stayed CAUTIOUS due short-term narrowing.
- `2024-03-15` exposure fell again to about `64%` with five SELL fills and PM issuing four EXITs.

## RE_RISK_TIMING_CORRECTNESS

Judgment: `BORDERLINE_BUT_CONTRACT_VALID`.

- `2024-03-05 -> 2024-03-07`: The system re-risked while Market Context remained BULL, volatility NORMAL, confidence high, and candidate/BQ evidence still had deployable opportunities. Risk Pacing stayed CAUTIOUS but did not encode a hard exposure cap; under current architecture, it allowed buys if item-level authority passed. This was valid by contract, but borderline because the same window contained several PM REDUCE/EXIT signals.
- `2024-03-11 -> 2024-03-14`: The system re-risked after `2024-03-11` short-term breadth breakdown. On `2024-03-14`, 20d return and breadth supported BULL/STRONG, while short-term narrowing was still explicitly present. This again is contract-valid but exposes a design sensitivity: CAUTIOUS Risk Pacing is advisory/semantic rather than a strict gross-exposure brake.

No evidence shows future outcome, later drawdown, or post-hoc profitability was used in these re-risk decisions.

## SELL_REDUCE_DRAWDOWN_RESPONSE

PM and execution did respond to drawdown-period deterioration:

- `hard_stop_current_return`: `55740` on `2024-03-11`, `70030` on `2024-03-12`, `43440` on `2024-03-13`, `55860` and `62320` on `2024-03-15`, `44250` on `2024-03-18`.
- `profit_retention_break`: `55740` on `2024-03-05`, `70030` on `2024-03-12`, `55860` on `2024-03-15`, `44250` on `2024-03-18`.
- `trend_and_opportunity_broken`: `43760` on `2024-03-07`, `36340` on `2024-03-14`, `47550` on `2024-03-15`.
- `weak_hold_score`: `76890` on `2024-03-05`, `69420` on `2024-03-08`, `99840` and `99780` around `2024-03-13`/`2024-03-15`.
- `risk_increased_but_trend_not_broken` and `peak_drawdown_warning` generated REDUCE intents throughout the period.

This is not a silent SELL/REDUCE correctness failure. The system repeatedly exited or reduced deteriorating positions, but also redeployed capital into newly eligible candidates while headline market evidence still supported BULL or only one day of RANGE.

## DRAWDOWN_DECISION_PATH_ATTRIBUTION

- Broad market exposure: material. Exposure was above `79%` on `2024-03-04`, `2024-03-07`, `2024-03-08`, `2024-03-12`, `2024-03-13`, and `2024-03-14`, so the portfolio remained meaningfully exposed during the drawdown.
- Concentrated position contribution: material. Examples include `55740` around `27%` of open market value before its `2024-03-05` EXIT, `55950` around `23-24%` before its `2024-03-11` EXIT, `70030` around `13-17%` after entry before its `2024-03-12` EXIT, and `55860` around `13-14%` before its `2024-03-15` EXIT.
- Re-risk timing: material. Exposure dropped after sell waves, then returned above `80%` on `2024-03-07`, `2024-03-12`, and `2024-03-14`.
- Regime classification: contributing but contract-valid. The final BULL label permitted continued deployment, while short-term narrowing remained in Risk Pacing rather than final regime override.
- Ordinary security-specific loss: material. Several newly or recently held securities triggered hard stops/profit-retention exits shortly after entry.
- Execution/runtime issue: not supported by evidence. Sampled jobs exited `0`, provenance/PIT fields were present, no HALT or duplicated side-effect evidence was found in the audited window.

## MARCH_DRAWDOWN_CLASSIFICATION

`NORMAL_STRATEGY_DRAWDOWN_WITH_OBSERVABILITY_GAP`.

The drawdown is not currently classified as a correctness defect. Regime authority was PIT-clean and contract-valid, Risk Pacing reacted with CAUTIOUS state, and PM SELL/REDUCE was active. However, the run shows an observability/design-expression gap: short-term internal deterioration and fragile participation were visible, but remained a component/risk-pacing fact rather than a stronger final regime or hard exposure-control fact.

This does not justify Production threshold/risk tuning from the March loss. It does justify a future READ-ONLY/SHADOW study of whether short-term breadth breakdown and security-level deterioration should be made more visible in risk dashboards or shadow risk attribution before any Production promotion is considered.

## Required Answers

- `REGIME_PIT_DECISION_TABLE`: included above.
- `MARCH_BULL_CLASSIFICATION_ROOT_CAUSE`: BULL came from PIT-valid 20d equal-weight trend above `0.02`, with 20d breadth NEUTRAL/STRONG, volatility NORMAL, high confidence, no future rows, no latest fallback.
- `MARKET_VS_SECURITY_INTERNAL_DIVERGENCE`: present. Short-term breadth/participation fragility and PM deterioration were visible while final Regime often remained BULL.
- `REGIME_TRANSITION_TIMING_JUDGMENT`: `CONSERVATIVE_BUT_VALID`.
- `MARCH_RISK_PACING_RESPONSE_PROFILE`: included above.
- `RE_RISK_TIMING_CORRECTNESS`: `BORDERLINE_BUT_CONTRACT_VALID`.
- `SELL_REDUCE_DRAWDOWN_RESPONSE`: active, not silent; EXIT/REDUCE fired repeatedly from PIT PM evidence.
- `DRAWDOWN_DECISION_PATH_ATTRIBUTION`: broad exposure + concentration + re-risk timing + ordinary security losses; no Runtime correctness contamination found.
- `MARCH_DRAWDOWN_CLASSIFICATION`: `NORMAL_STRATEGY_DRAWDOWN_WITH_OBSERVABILITY_GAP`.
- `REGIME_REPAIR_JUSTIFIED`: `NO` for Production repair. Future SHADOW observability study is reasonable.
- `RISK_PACING_REPAIR_JUSTIFIED`: `NO` for Production repair from this evidence. Future SHADOW analysis of CAUTIOUS-as-advisory vs enforceable exposure brake may be useful.
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `SHADOW_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `RUNTIME_STATE_MUTATED`: `NO`
- `FUTURE_OUTCOME_USED_FOR_TUNING`: `NO`
- `NEXT_RECOMMENDED_STEP`: close EL as READ-ONLY correctness audit; if desired, open a separate SHADOW-only design study for short-term internal-deterioration observability and risk-pacing enforceability. Do not tune Production from the March drawdown.

## Final Judgment

`PHASE32_EL_2024_03_DRAWDOWN_PIT_CONTRACT_VALID_RISK_RESPONSE_ACTIVE_NORMAL_STRATEGY_DRAWDOWN_WITH_OBSERVABILITY_GAP_NO_PRODUCTION_REPAIR`
