# Phase32-FD - Post-EZ 100BD+ Capital Deployment / Breadth / ADD / Risk Acceptance Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Requested audit window: `2022-10-03` through `2023-04-10`
- Evidence used: target-run daily Runtime artifacts, Portfolio Construction artifacts, Position Sizing artifacts, fills/execution artifacts, current valuation artifacts, recent-exit guard materialization artifacts, and prior Phase32 FA/FB/FC/EW/EZ reports.
- Runtime observation at audit time: the run had already advanced beyond the requested window to `2023-04-12`, with `next_job = 2023-04-13:morning`. This report intentionally caps conclusions to the requested `2023-04-10` window.
- Production changed: NO
- SHADOW changed: NO
- Target run mutated: NO
- Runtime state mutated: NO
- fresh-run/resume/replay/recover executed by Codex: NO
- Future return/PnL used for Production judgment: NO

## Evidence Coverage

The requested window contains 128 completed business days from `2022-10-03` through `2023-04-10`.

Summary counts observed from actual artifacts:

| Measure | Value |
| --- | ---: |
| Completed business days audited | 128 |
| BUY_NEW fills | 222 |
| BUY_ADD fills | 21 |
| SELL_EXIT fills | 202 |
| SELL REDUCE fills | 55 |
| SELL EXIT fills | 14 |
| Unique traded symbols | 130 |
| PM ADD decisions | 124 |
| PC `semantic_buy_type=BUY_ADD` rows | 124 |
| PC `semantic_buy_type=REENTRY` rows | 0 |
| Recent-exit guard materialized rows | 806 |
| Recent-exit guard emitted total | 216 |
| Recent-exit guard expired total | 212 |
| Missing/stale/cross-run guard rows | 0 |
| Expired-guard suppression rows | 0 |
| Post-expiry BUY_NEW rows | 118 |

## Extended REENTRY / Guard Correctness

`semantic_buy_type=REENTRY` was not found in Portfolio Construction artifacts in the audited window. Formerly held symbols return through ordinary `BUY_NEW` after bounded guard expiry, not through legacy long-lived REENTRY current-decision authority.

Recent-exit guard evidence remained run-scoped and bounded:

- Guard states observed: `ACTIVE_RECENT_EXIT_GUARD`.
- Guard statuses observed: `FAIL_CLOSED` while active.
- Missing guard: 0.
- Stale guard: 0.
- Cross-run guard: 0.
- Expired guard suppression: 0.
- Maximum retained guard rows in a daily artifact: 10.
- Maximum recent-exit guard artifact rows observed: 12.

Conclusion: EW/EZ history-neutrality and bounded-guard lifecycle remain intact over the 100BD+ path.

## Portfolio Breadth

Period-level deployment and breadth:

| Period | Days | Avg POS | Avg Exposure | Avg Cash | BUY_NEW Count | BUY_ADD Count | BUY_NEW Notional | BUY_ADD Notional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10 to 2022-11 | 40 | 11.70 | 78.7% | 21.3% | 75 | 11 | 4,260,480 | 115,410 |
| 2022-12 | 22 | 11.68 | 73.7% | 26.3% | 35 | 4 | 1,857,980 | 46,340 |
| 2023-01 | 19 | 13.95 | 69.4% | 30.6% | 50 | 3 | 2,286,320 | 45,870 |
| 2023-02 | 19 | 15.58 | 85.1% | 14.9% | 31 | 1 | 1,867,610 | 58,640 |
| 2023-03 to 2023-04-10 | 28 | 11.21 | 83.4% | 16.6% | 31 | 2 | 2,264,030 | 208,700 |

Breadth increased relative to the pre-EW long-lived REENTRY-penalty architecture because post-expiry symbols can compete as ordinary BUY_NEW again. The observed breadth is explained by valid current opportunity competition and bounded guard expiry. There is no evidence that removing REENTRY history penalty weakened BQ/Entry/PC quality gates.

## ADD vs BUY_NEW Capital Deployment

Observed new buy capital:

| Type | Count | Shares | Notional | Capital Share |
| --- | ---: | ---: | ---: | ---: |
| BUY_NEW | 222 | 94,300 | 12,536,420 | 96.35% |
| BUY_ADD | 21 | 2,100 | 474,960 | 3.65% |

BUY_ADD is active, but selective. ADD count is highest in the early window, then lower in January/February; however the March-to-April ADD notional is materially larger than the early months despite only two ADD fills. The evidence does not prove structural run-age weakening of ADD. The better characterization is: ADD is functional, but BUY_NEW remains the dominant marginal deployment path.

## Winner Capitalization Cases

Representative traces:

| Symbol | Observed Lifecycle | ADD Evidence | Max Weight / Notes |
| --- | --- | --- | --- |
| `76470` | BUY_NEW `2022-10-12`, EXIT `2022-10-14`; later BUY_NEW after guard expiry; second campaign receives repeated ADDs `2022-11-25` through `2022-12-01`; later REDUCE/EXIT | 5 BUY_ADD fills, 6 ADD rows | Max current weight about 5.2%; demonstrates post-expiry BUY_NEW plus vertical ADD can both occur |
| `94320` | BUY_NEW `2022-10-05`; ADDs in Oct/Nov; REDUCE/EXIT Dec; later BUY_NEW and additional ADDs | 7 BUY_ADD fills, 31 ADD rows | Max current weight about 9.3%; clean evidence of selective winner capitalization |
| `87890` | Repeated BUY_NEW/REDUCE/EXIT behavior | No ADD fill observed | Max weight about 3.1%; not a vertical winner-capitalization case |
| `93180` | Repeated BUY_NEW/EXIT behavior | No ADD fill observed | Max weight about 3.0%; not a vertical winner-capitalization case |
| `89180` | Repeated BUY_NEW/REDUCE/EXIT behavior | No ADD fill observed | Max weight about 3.7%; not a vertical winner-capitalization case |
| `43880` | Material incumbent capitalization | 1 BUY_ADD fill | ADD notional 122,900 |
| `83060` | Material incumbent capitalization | 1 BUY_ADD fill | ADD notional 85,800 |
| `94340` / `45940` | Multiple smaller ADD sequences | 3 BUY_ADD fills each | Selective incremental capitalization |

Conclusion: winner capitalization is functional on actual path, but sparse. The sparse ADD share is an architecture/performance design observation, not a correctness defect in this 100BD window.

## Breadth Without Quality Dilution

All BUY fills that could be matched back to PC/BQ/Entry evidence fell into:

- A. strong valid opportunity: 184 fills.
- B. marginal but valid opportunity: 59 fills.

No fill was classified as:

- C. weak opportunity admitted only because capital remained,
- D. history-neutral but quality-neutralization side effect,
- E. unexplained/defect admission.

This supports that REENTRY penalty removal did not spill over into quality-gate removal.

## Regime / Risk Defensiveness

Regime-level actual deployment:

| Regime | Days | Avg Exposure | Avg Cash | Avg POS | BUY_NEW | BUY_ADD | SELL/REDUCE/EXIT |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 28 | 59.8% | 40.2% | 9.46 | 53 | 5 | 57 |
| CORRECTION | 4 | 73.3% | 26.7% | 10.25 | 7 | 0 | 6 |
| RANGE | 26 | 79.2% | 20.8% | 10.81 | 50 | 4 | 60 |
| RECOVERY | 17 | 81.7% | 18.3% | 11.71 | 25 | 1 | 32 |
| BULL | 53 | 87.2% | 12.8% | 15.36 | 87 | 11 | 116 |

BEAR defensiveness is preserved: exposure is materially lower and cash materially higher than BULL. CORRECTION defensiveness is also preserved in the limited sample, with no BUY_ADD and lower exposure than BULL.

Important windows:

- `2022-12-20` through `2023-01-13` BEAR: exposure generally stayed around 50%-70%, cash around 30%-50%, with active SELL/EXIT/REDUCE turnover.
- `2023-03-14` through `2023-03-24`: BULL to RANGE/CORRECTION/RECOVERY transition reduced exposure from the high 80% range toward the high 60% range, then recapitalized under RECOVERY evidence.
- `2023-04-05` through `2023-04-10` BEAR/CORRECTION: exposure declined from about 86% to about 62%, POS fell to 6, and cash rose to about 38%.

Conclusion: no risk-defensiveness regression was found.

## Recovery Re-Capitalization

The March recovery path shows Risk解除, BUY_NEW, selective ADD, post-expiry symbol return to competition, and exposure recovery occurring through ordinary current PIT evidence:

| Date | Regime | Exposure | Cash | POS |
| --- | --- | ---: | ---: | ---: |
| `2023-03-17` | RANGE | 68.0% | 32.0% | 9 |
| `2023-03-27` | RECOVERY | 91.4% | 8.6% | 11 |
| `2023-03-31` | RECOVERY | 85.7% | 14.3% | 8 |
| `2023-04-03` | RECOVERY | 89.1% | 10.9% | 9 |
| `2023-04-06` | BEAR | 77.4% | 22.6% | 6 |
| `2023-04-10` | CORRECTION | 62.0% | 38.0% | 6 |

This is consistent with the intended contract: weak market suppresses broad exposure, but valid current PIT opportunity can recapitalize without old ownership history acting as a permanent blocker.

## Concentration / Horizontal Expansion

Aggregate concentration over the audited window:

| Measure | Value |
| --- | ---: |
| Average largest position weight | 15.9% |
| Average top-3 weight | 38.3% |
| Average top-5 weight | 52.8% |
| Average 100-share position count | 8.28 |
| Average positions >5% | 6.44 |
| Average positions >10% | 2.35 |

Representative high-weight symbols include `59350`, `70640`, `79010`, `92270`, `93600`, `43880`, and `92540`. The portfolio is not merely a flat expansion into many tiny positions; it often contains a few large positions plus smaller lots. POS expansion is therefore better described as expected breadth shift plus ordinary capital competition, not unexplained weak-quality horizontal expansion.

## Run-Age Accumulation Recheck

EW/EZ removed the long-lived REENTRY current-decision hot path. In this 128BD audit window:

- `semantic_buy_type=REENTRY`: 0.
- Guard retained rows remained bounded, max 10 retained rows per day.
- Guard artifact rows remained bounded, max 12 rows per day.
- No stale or cross-run guard evidence was found.
- No expired guard continued to suppress a current BUY decision.

Artifact/time trend from sampled daily artifacts:

| Measure | Early Window | Late Window | Interpretation |
| --- | ---: | ---: | --- |
| Daily artifact size sample | about 114 MB/day | about 151 MB/day | Moderate growth, not old 250MB+/day late-run scaling in this 100BD window |
| Daily elapsed sample | about 93 sec/day | about 121 sec/day | Moderate growth, materially below old observed 6 min/day late-run slowdown |

Conclusion: no renewed unbounded run-age decision-state growth was found. Runtime scaling appears improved versus the old run, within the limited 100BD+ scope.

## Performance Difference Classification

Any difference from old runs is not judged from later PnL. Based on actual decision-path evidence, the current classification is:

- A. legitimate portfolio path divergence: YES
- B. intended history-neutrality effect: YES
- C. risk/regime difference caused by portfolio state: YES
- D. ADD/NEW capital competition difference: YES
- E. correctness defect: NO
- F. unknown: NO for the audited contracts, PARTIAL for long-horizon capital productivity questions outside this 100BD window

The observed path is consistent with EW/EZ making formerly held symbols eligible as ordinary BUY_NEW after bounded guard expiry while preserving BQ/Entry/PC/Risk controls.

## Required Answers

- `EXTENDED_HISTORY_NEUTRALITY_CONFIRMED = YES`
- `LEGACY_REENTRY_AUTHORITY_FOUND = NO`
- `GUARD_LIFECYCLE_STILL_CORRECT = YES`
- `PORTFOLIO_BREADTH_INCREASED = YES_EXPECTED_HISTORY_NEUTRALITY_SHIFT`
- `BREADTH_INCREASE_EXPLAINED_BY_VALID_OPPORTUNITY = YES`
- `WEAK_QUALITY_HORIZONTAL_EXPANSION_FOUND = NO`
- `BUY_ADD_ACTIVE = YES`
- `BUY_ADD_CAPITAL_SHARE = 3.65%`
- `BUY_NEW_CAPITAL_SHARE = 96.35%`
- `ADD_WEAKENS_WITH_RUN_AGE = NO_STRUCTURAL_RUN_AGE_WEAKENING_PROVEN`
- `WINNER_CAPITALIZATION_FUNCTIONAL = YES_SELECTIVE`
- `BEAR_DEFENSIVENESS_PRESERVED = YES`
- `CORRECTION_DEFENSIVENESS_PRESERVED = YES_LIMITED_SAMPLE`
- `RECOVERY_RECAPITALIZATION_FUNCTIONAL = YES`
- `HISTORY_RELATED_REVERSE_BIAS_FOUND = NO`
- `RUN_AGE_DECISION_STATE_GROWTH_BOUNDED = YES`
- `DAILY_ARTIFACT_GROWTH_BOUNDED = YES_IN_100BD_WINDOW`
- `RUNTIME_SCALING_IMPROVED_VS_OLD_RUN = YES_WITH_LIMITED_100BD_SCOPE`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## 100BD+ Acceptance Judgment

Selected classification:

`B. CLEAN_WITH_EXPECTED_PORTFOLIO_BREADTH_SHIFT`

Rationale: the portfolio path is broader than the old REENTRY-penalized architecture, but the breadth is explained by bounded guard expiry and current PIT opportunity competition. ADD is active and winner capitalization works selectively. BEAR/CORRECTION defensiveness remains intact. No renewed history-neutrality regression, unbounded run-age decision bias, or correctness defect was found in the requested window.

## Next Recommended Step

Continue the existing long-horizon validation to observe whether the clean 100BD+ behavior remains stable over later 2023/2024 windows, especially:

- whether BUY_ADD remains selective but available,
- whether post-expiry BUY_NEW continues to avoid stale history bias,
- whether artifact size/runtime remain bounded beyond the early 128BD window.

Do not infer Production repair from short-window PnL differences.

## Final Judgment

`PHASE32_FD_POST_EZ_100BD_ACCEPTED_CLEAN_WITH_EXPECTED_PORTFOLIO_BREADTH_SHIFT_HISTORY_NEUTRALITY_AND_RISK_DEFENSIVENESS_PRESERVED_LONG_HORIZON_SAFE_TO_CONTINUE`
