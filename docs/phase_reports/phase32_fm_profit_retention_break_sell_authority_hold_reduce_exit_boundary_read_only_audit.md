# Phase32-FM Profit-Retention-Break SELL Authority / HOLD-REDUCE-EXIT Boundary READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit snapshot: `194` completed business days, `2022-10-03` through `2023-07-14`.
- Starting point: Phase32-FL found `SELL_PROFIT_PROTECTION_GENERAL_GAP = YES`, `GIVEBACK_PROBLEM_ADD_SPECIFIC = NO`, and `profit_retention_break` winner cases split as HOLD 18 / REDUCE 0 / EXIT 18.
- Evidence sources: current source, Architecture SoT, Phase27-D6-D/E reports, Phase32-FL/FJ/FK, daily `position_management/pm_decisions.json`, daily `strategy/position_management.json`, daily `positions/position_campaigns.json`, and daily `strategy/market_context.json`.

This was READ-ONLY. No Production, SHADOW, config, schema, runtime state, Pending, Ledger, fresh-run, resume, recover, or replay mutation was executed.

Historical later outcomes were used only to locate and characterize giveback cases. They were not used to choose Production rules, thresholds, weights, ranks, or parameters.

## Canonical Semantic Reconstruction

`profit_retention_break` is a legacy reason alias whose canonical meaning is peak-drawdown / profit-retention risk-review evidence. It is not simple profit-taking authority.

Relevant SoT / history:

- `docs/02_architecture/position_management_decision_trace_contract.md` defines `profit_retention_break` as `peak_drawdown_profit_retention_risk`, compatibility `LEGACY_ALIAS`, action effect `NONE`.
- The same contract states that profit-related reason codes must be interpreted as Risk Review evidence; profit alone must not create `EXIT` or `REDUCE`.
- Phase27-D6-D implemented the minimum HOLD/EXIT boundary:

```text
profit_retention_break only
AND expected_edge_score > 0
AND high downside risk is absent
AND existing exit_score high condition is absent
-> HOLD
```

- `tests/position_management_ai/test_phase6a_position_management_baseline.py` still asserts this exact behavior: a row with adequate expected edge and `profit_retention_break` remains `HOLD` with `action_reason = positive_expected_edge|profit_retention_break`.

Therefore the current canonical semantic is:

```text
profit_retention_break
-> risk-review / profit-protection evidence
-> may contribute to EXIT when recovery/continuation is not sufficient
-> may coexist with HOLD when current Expected Edge / continuation remains adequate
-> not standalone REDUCE or EXIT authority
```

## Producer / Consumer Reference Graph

| Stage | Producer / source | Consumer | Decision authority effect |
|---|---|---|---|
| Campaign valuation | `positions/position_campaigns.json` | Strategy PM / PM evidence | Provides current return, MFE, observed giveback, quantity, campaign id. |
| PM scoring | `position_management_ai/inference.py` | PM decision row | Calculates hold/exit/add/reduce scores, drawdown from peak, trend, expected edge, downside risk. |
| Reason assignment | `classify_position_action` | PM action selection | Adds `profit_retention_break` when drawdown from peak <= existing profit-retention condition. |
| D6-D override | `classify_position_action` | PM action selection | If `profit_retention_break` is the only exit reason and expected edge remains positive with no high downside / exit-score high condition, output remains `HOLD`. |
| EXIT branch | `classify_position_action` | PM action selection | If exit reasons remain or exit score is high, output `EXIT`; actual rows use `EXIT_BY_PEAK_DRAWDOWN`. |
| REDUCE branch | `classify_position_action` | PM action selection | Runs after EXIT/HOLD branch; consumes `peak_drawdown_warning`, downside risk, reduce score, weak hold. |
| Strategy PM integration | `strategy/position_management.json` | PC / PS / Runtime | Preserves PM-owned action; reason metadata does not create independent Runtime action. |
| Runtime | Planning / Pending / Submit / Execution | Order lifecycle | Consumes PM-owned REDUCE/EXIT through PC/PS; does not reinterpret `profit_retention_break` into SELL quantity. |

Root graph conclusion: `profit_retention_break` lives in the EXIT/HOLD branch, not in the REDUCE branch. REDUCE is intentionally owned by separate weakening/risk-review evidence such as `peak_drawdown_warning`, high downside risk, reduce score, and weak hold while trend/opportunity remains alive.

## Source Boundary

Current implementation evidence in `src/ai_fund_lab_v2/position_management_ai/inference.py`:

- `drawdown_from_peak <= -0.12` appends `profit_retention_break` to `exit_reasons`.
- `drawdown_from_peak <= -0.07` appends `peak_drawdown_warning` to `risk_reasons`.
- D6-D then preserves HOLD when `exit_reasons == ["profit_retention_break"]`, expected edge is positive, high downside risk is absent, and `exit_score < 0.80`.
- REDUCE is evaluated after EXIT/HOLD resolution and is driven by downside risk, peak drawdown warning, reduce score, or weak hold with continuation optionality.

This branch ordering explains why `profit_retention_break` produced HOLD or EXIT, but not REDUCE.

## All 36 Profit-Retention-Break Winner Cases

All rows below are PM decision rows on final-positive winner campaigns through the audit snapshot.

| Date | Symbol | Action | CurRet | MFE | Giveback | GiveRatio | Continuation | Downside | Recovery / severity | Regime | Next SELL |
|---|---|---:|---:|---:|---:|---:|---|---|---|---|---|
| 2022-10-21 | 66190 | EXIT | 2.0% | 2.0% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RANGE | None |
| 2022-11-07 | 92270 | EXIT | 27.5% | 28.1% | 2.5% | 0.09 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RANGE | None |
| 2022-11-14 | 78590 | EXIT | 2.2% | 8.5% | 6.2% | 0.74 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RECOVERY | None |
| 2022-11-18 | 67210 | EXIT | 14.0% | 14.0% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2022-12-01 | 45910 | EXIT | 1.3% | 1.3% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2022-12-15 | 17570 | EXIT | 12.5% | 21.9% | 9.4% | 0.43 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RECOVERY | None |
| 2023-01-13 | 36640 | EXIT | 8.3% | 14.3% | 6.0% | 0.42 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BEAR | None |
| 2023-01-23 | 45940 | EXIT | 12.8% | 12.8% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-01-26 | 72730 | EXIT | 10.2% | 13.7% | 4.1% | 0.30 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-02-01 | 53370 | EXIT | 4.5% | 4.5% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-03-20 | 59350 | HOLD | 18.8% | 18.8% | 0.0% | 0.00 | PASS | PASS | RECOVERY_PRESENT / NORMAL | CORRECTION | 2023-04-20 EXIT |
| 2023-03-27 | 59350 | HOLD | 27.5% | 34.2% | 10.8% | 0.32 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RECOVERY | 2023-04-20 EXIT |
| 2023-03-27 | 43880 | HOLD | 6.9% | 7.3% | 0.4% | 0.06 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RECOVERY | 2023-04-07 REDUCE |
| 2023-03-28 | 59350 | HOLD | 65.1% | 65.1% | 10.8% | 0.17 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RANGE | 2023-04-20 EXIT |
| 2023-03-30 | 59350 | HOLD | 64.2% | 102.6% | 38.4% | 0.37 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RANGE | 2023-04-20 EXIT |
| 2023-03-31 | 59350 | HOLD | 93.7% | 102.6% | 38.4% | 0.37 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RECOVERY | 2023-04-20 EXIT |
| 2023-04-03 | 59350 | HOLD | 137.5% | 137.5% | 38.4% | 0.28 | PASS | PASS | RECOVERY_PRESENT / NORMAL | RECOVERY | 2023-04-20 EXIT |
| 2023-04-05 | 59350 | HOLD | 155.9% | 181.3% | 38.4% | 0.21 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BEAR | 2023-04-20 EXIT |
| 2023-04-06 | 59350 | HOLD | 199.7% | 199.7% | 38.4% | 0.19 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BEAR | 2023-04-20 EXIT |
| 2023-04-17 | 59350 | HOLD | 129.7% | 243.6% | 113.9% | 0.47 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-04-20 EXIT |
| 2023-04-20 | 59350 | EXIT | 136.5% | 243.6% | 113.9% | 0.47 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-04-27 | 76010 | EXIT | 10.1% | 10.1% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RANGE | None |
| 2023-04-27 | 92520 | EXIT | 8.9% | 8.9% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RANGE | None |
| 2023-05-30 | 42640 | EXIT | 5.6% | 10.4% | 5.9% | 0.57 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-06-02 | 72140 | EXIT | 5.3% | 5.3% | 1.9% | 0.35 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RECOVERY | None |
| 2023-06-12 | 21340 | HOLD | 29.4% | 29.4% | 0.0% | 0.00 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-07 EXIT |
| 2023-06-12 | 30410 | HOLD | 6.0% | 6.0% | 0.0% | 0.00 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-06-13 REDUCE |
| 2023-06-14 | 21340 | HOLD | 44.3% | 47.1% | 2.7% | 0.06 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-07 EXIT |
| 2023-06-15 | 21340 | HOLD | 79.0% | 79.0% | 2.7% | 0.03 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-07 EXIT |
| 2023-06-16 | 40520 | HOLD | 9.4% | 9.4% | 0.0% | 0.00 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-05 REDUCE |
| 2023-06-19 | 21340 | HOLD | 84.8% | 107.9% | 23.1% | 0.21 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-07 EXIT |
| 2023-06-19 | 40520 | HOLD | 34.0% | 34.0% | 0.0% | 0.00 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-05 REDUCE |
| 2023-06-20 | 50250 | EXIT | 7.4% | 7.4% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-06-23 | 21340 | HOLD | 79.0% | 119.4% | 40.4% | 0.34 | PASS | PASS | RECOVERY_PRESENT / NORMAL | BULL | 2023-07-07 EXIT |
| 2023-07-04 | 69270 | EXIT | 17.3% | 17.3% | 0.0% | 0.00 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | BULL | None |
| 2023-07-13 | 39290 | EXIT | 7.6% | 12.6% | 5.0% | 0.40 | PASS | PASS | NO_RECOVERY / EXIT_CANDIDATE | RANGE | None |

## HOLD 18 vs EXIT 18 Discriminator

The discriminator is not market regime, current return, MFE, or raw giveback alone. The clean discriminator in actual artifacts is recovery/severity:

| Evidence | HOLD 18 | EXIT 18 |
|---|---:|---:|
| `strategy_intelligence_continuation_quality_status = PASS` | 18 | 18 |
| `strategy_intelligence_downside_risk_status = PASS` | 18 | 18 |
| `exit_confirmation_state = DEFENSIVE_ONLY` | 18 | 18 |
| `recovery_state = RECOVERY_PRESENT` | 18 | 0 |
| `recovery_state = NO_RECOVERY` | 0 | 18 |
| `pm_severity = PM_SEVERITY_NORMAL` | 18 | 0 |
| `pm_severity = PM_SEVERITY_EXIT_CANDIDATE` | 0 | 18 |

Summary statistics:

| Metric | HOLD 18 | EXIT 18 |
|---|---:|---:|
| Median current return | 64.6% | 8.6% |
| Median MFE | 72.0% | 11.5% |
| Median giveback | 10.8% | 0.9% |
| Median giveback / MFE | 0.18 | 0.04 |
| Median market value | 163,300 | 39,700 |
| Dominant cause | 17 strong continuation / 1 partial continuation | 18 peak drawdown |

Interpretation:

- HOLD rows are not weak/unknown rows. They are high-profit, continuation-positive, recovery-present rows.
- EXIT rows are lower-return on median and are classified as no-recovery / exit-candidate despite continuation/downside PASS fields also being present.
- The current branch is opportunity-first: profit-risk review does not override positive current continuation/recovery evidence.

## Why REDUCE Equals Zero

`WHY_REDUCE_ZERO_EXPLAINED`: YES.

Root cause:

```text
profit_retention_break is assigned to exit_reasons
-> D6-D may convert profit_retention_break-only rows to HOLD
-> remaining rows go to EXIT
-> REDUCE branch is evaluated later and is fed by risk_reasons / reduce_score / weak-hold logic
```

Classification:

- A. Architecture intentional: YES, partly. Reason codes are not standalone action authority.
- B. REDUCE authority delegated to separate signal: YES. `peak_drawdown_warning` and related weak/risk signals own the REDUCE lane.
- C. Branch ordering prevents REDUCE from receiving `profit_retention_break`: YES.
- D. Semantic compression: PARTIAL. Downstream sees `profit_retention_break` mostly as HOLD-compatible risk review or EXIT-grade reason, not as a distinct moderate profit-protection stage.
- E. Legacy design artifact: PARTIAL. The name survives as a legacy alias.
- F. Missing consumer: NO for Runtime; Runtime correctly consumes PM action, not reason label.
- G. Population coincidence: NO. Source structure explains the zero.

## Peak-Drawdown-Warning Comparison

| Signal | Trigger / role | Actual action mapping in FL/FM population | Canonical meaning |
|---|---|---|---|
| `peak_drawdown_warning` | Earlier / softer drawdown-risk warning | 49 REDUCE, 0 HOLD, 0 EXIT in FL primary warning count | Weakening/risk-review evidence for REDUCE or EXIT review. |
| `profit_retention_break` | Deeper peak drawdown / profit-retention risk | 18 HOLD, 0 REDUCE, 18 EXIT | Legacy alias for peak-drawdown/profit-retention risk; not simple profit-taking authority. |

The role split is internally consistent but coarse:

- `peak_drawdown_warning` is the current REDUCE lane.
- `profit_retention_break` is the current HOLD-or-EXIT lane.
- There is no explicit "profit-protective REDUCE" lane keyed by `profit_retention_break` when continuation remains good but concentration/giveback risk is material.

`PEAK_DRAWDOWN_WARNING_ROLE_DISTINCT`: YES.

## HOLD Case Classification

Using current PIT evidence only:

| Classification | Count |
|---|---:|
| `HOLD_STRONGLY_JUSTIFIED` | 18 |
| `HOLD_REASONABLE_BUT_BORDERLINE` | 0 |
| `PROFIT_PROTECTION_ACTION_SEEMS_WARRANTED` | 0 by existing PM contract |
| `UNKNOWN` | 0 |

Important nuance: by current contract, all 18 HOLD cases are justified because continuation/downside PASS and recovery are present. By design-review intuition, high notional / high MFE / large giveback rows such as 59350 are exactly where a future concentration-aware profit-protection stage could be useful. That is a design refinement candidate, not a correctness defect.

## 59350 Deep Dive

### 2023-04-06 PIT Evidence

- PM row: `decision_type = HOLD`
- Reason codes: `positive_expected_edge`, `profit_retention_break`
- Dominant cause: `HOLD_BY_STRONG_CONTINUATION`
- Current price in PM artifact: 4,790
- Average cost: 1,598
- Current return in strategy PM evidence: about +199.7%
- Observed MFE: about +199.7% in strategy PM evidence on the decision path; campaign snapshot showed even higher pre-action current valuation at 5,490.
- Observed giveback: about +38.4%
- Canonical sell state: `EXIT_GRADE`
- Continuation quality: PASS
- Downside risk: PASS
- Recovery state: `RECOVERY_PRESENT`
- Exit confirmation: `DEFENSIVE_ONLY`, reason `soft_deterioration_not_terminal`
- PM severity: `PM_SEVERITY_NORMAL`
- Market regime: BEAR
- Quantity: 100 shares
- Market value: high notional, approximately 479,000 in PM row.

### Judgment

`59350_HOLD_ARCHITECTURALLY_JUSTIFIED`: YES, under the current Phase27-D6-D / Phase32-X contract.

Why HOLD:

```text
profit_retention_break present
+ positive expected edge / structured hold worthiness
+ continuation quality PASS
+ downside risk PASS
+ recovery present
+ no terminal hard deterioration
-> HOLD / no sell order
```

Why not EXIT on 2023-04-06:

- `profit_retention_break` alone is not terminal authority.
- Exit confirmation classified the state as defensive-only, not terminal.
- PM severity mapping preserved baseline HOLD.

Why not REDUCE:

- `profit_retention_break` does not feed the REDUCE branch.
- REDUCE requires the separate REDUCE lane (`peak_drawdown_warning`, high downside risk, reduce score, weak hold) or current PM REDUCE action.

The large later giveback makes 59350 the best design-review case, but it does not prove the 2023-04-06 HOLD violated the accepted contract.

## Other Large HOLD Giveback Cases

### 21340

- `profit_retention_break` HOLD rows: 2023-06-12, 06-14, 06-15, 06-19, 06-23.
- Current return rose from about +29.4% to +84.8%; MFE reached about +119.4%.
- All rows show continuation/downside PASS and recovery-present semantics.
- Later SELL: 2023-07-07 EXIT with `trend_and_opportunity_broken`.

Judgment: not 59350-specific. The pattern recurs: profit-risk review can coexist with strong continuation and delay EXIT until trend/opportunity break appears.

### 30410

- 2023-06-12 HOLD with `profit_retention_break`, current return/MFE about +6.0%.
- Next SELL: 2023-06-13 REDUCE with `risk_increased_but_trend_not_broken`.

Judgment: HOLD -> REDUCE path exists, but the REDUCE is triggered by later separate risk/weakening evidence, not by `profit_retention_break` itself.

## HOLD to Later EXIT / REDUCE Progression

For the 18 HOLD rows:

- Next SELL action EXIT: 14 rows.
- Next SELL action REDUCE: 4 rows.
- HOLD -> REDUCE exists in actual path, but only after a subsequent PM row authors REDUCE via distinct risk/weakening evidence.
- The typical progression is:

```text
profit_retention_break + positive expected edge / recovery
-> HOLD
later deterioration or trend/opportunity break
-> REDUCE or EXIT
```

`HOLD_TO_EXIT_PROGRESSION_EXPLAINED`: YES.

`HOLD_TO_REDUCE_PATH_EXISTS`: YES, but not as a direct `profit_retention_break -> REDUCE` consumer.

## Profit Protection Escalation Model

The actual binding is mixed:

```text
no issue
-> HOLD
-> REDUCE via peak_drawdown_warning / risk_increased / weak-hold lane
-> EXIT via terminal exit reasons
```

But for `profit_retention_break` specifically, the binding is:

```text
profit_retention_break + recovery / positive edge
-> HOLD

profit_retention_break + no recovery / exit-candidate severity
-> EXIT
```

So the general PM model has a REDUCE stage, but the `profit_retention_break` sub-model is effectively HOLD-or-EXIT.

## Same-Day Information Boundary

This audit does not treat same-day or later price movement as evidence that the morning decision was wrong. The relevant decision-time artifacts carry PIT flags such as `future_information_used = false`, and 59350's decision path uses evidence dates at or before the business date.

Same-day information boundary does not fully explain the profit-retention issue, because repeated HOLD rows exist across many business days. It does prevent declaring any single same-day drop "avoidable" from morning evidence alone.

## Opportunity-First Conflict

The current architecture explicitly favors continuing a winner when current evidence still supports continuation:

- Expected edge adequate
- continuation quality PASS
- downside risk PASS
- recovery present
- no hard stop / terminal trend-and-edge break

This is aligned with the investment philosophy:

```text
Winner is held while it continues
normal volatility is tolerated
clear PIT deterioration leads to REDUCE / EXIT
```

The conflict is that `profit_retention_break` can signal material profit-at-risk while continuation remains PASS. Today, continuation/recovery wins that conflict. That is intentional under current contract but may be too weakly binding for future profit-protection design.

## Information Loss / Semantic Compression

`SEMANTIC_INFORMATION_LOSS_FOUND`: PARTIAL.

The artifacts do preserve detailed inputs:

- current return
- observed campaign MFE
- observed giveback
- continuation quality
- downside status
- recovery state
- canonical sell state
- PM severity
- campaign id and quantity

So the information is not lost at the artifact level.

The compression is semantic/action-level: `profit_retention_break` has no explicit middle action state. It is interpreted as either HOLD-compatible risk review or EXIT-grade evidence. A future design could consume the existing fields without introducing a fixed trailing stop.

## Concentration Awareness

`CONCENTRATION_AWARENESS_GAP_FOUND`: YES_AS_DESIGN_GAP.

59350 and 67310 show that high-notional / high-weight winner exposure can dominate portfolio impact. Current PM evidence includes quantity and market value, and campaign artifacts include current market value, but the accepted `profit_retention_break` HOLD/EXIT boundary does not appear to use concentration or absolute portfolio risk contribution as a first-class discriminator.

This is not a correctness defect because no SoT currently requires concentration-aware profit-retention SELL authority. It is a reasonable design-refinement axis.

## 100-Share Binary Interaction

The zero REDUCE count for `profit_retention_break` is not mainly caused by 100-share binary positions. It is caused by source branch ownership: `profit_retention_break` is an exit-reason / risk-review alias, while REDUCE is driven by separate REDUCE evidence.

However, for high-price 100-share positions, a future profit-protective REDUCE may be effectively binary and become a full EXIT unless a partial-lot policy exists. This matters for blast radius.

## Early vs Later HOLD Shift

Primary final-winner basis from FL:

| Period | Winners | `profit_retention_break` rows | HOLD rows | EXIT rows | Post-deterioration giveback |
|---|---:|---:|---:|---:|---:|
| Opened 2022-10-03 to 2023-02-28 | 68 | 8 | 0 | 8 | 102,650 |
| Opened 2023-03-01 to 2023-07-14 | 59 | 9 | 4 | 5 | 264,300 |

FM row-level count includes repeated same-campaign warning rows, especially 59350 and 21340, which is why the all-row `profit_retention_break` count is 36. On a campaign-period basis, later opened campaigns show a clearer shift toward HOLD at profit-retention warning and larger post-deterioration giveback.

`EARLY_LATE_PROFIT_RETENTION_SHIFT`: YES, as characterization.

## Existing PIT Three-Stage Feasibility

`EXISTING_PIT_EVIDENCE_SUPPORTS_THREE_STAGE_PROTECTION`: YES.

Existing fields are sufficient for a future design-only model that separates:

- `HOLD_CONTINUATION`: recovery present, continuation PASS, downside PASS, low concentration impact.
- `PROFIT_PROTECT_REDUCE`: profit-at-risk / giveback evidence material, continuation not broken, but exposure or deterioration risk warrants trimming.
- `EXIT`: trend/edge broken, hard stop, no recovery, or terminal PM severity.

No new threshold is proposed here. The finding is only that the necessary current PIT evidence is already materialized.

`FIXED_TRAILING_STOP_REQUIRED`: NO. A fixed trailing stop or fixed holding-day rule is not required by this audit and would be inconsistent with the "do not sell winners just because they are off peak" principle unless separately justified.

## Blast-Radius Preview

Future changes to `profit_retention_break` semantics could affect:

- PM HOLD/REDUCE/EXIT action mix.
- PC membership and target weight for existing positions.
- PS negative quantity deltas.
- Runtime `SELL_REDUCE` vs `SELL_EXIT` planning.
- Pending review and submit paths for mixed BUY/SELL days.
- Campaign closure timing.
- Recent-exit guard materialization after new EXITs.
- Later BUY_NEW / recent-exit churn guard behavior.
- Capital competition and cash recycling.
- ADD, because earlier REDUCE/EXIT changes current position size and later ADD eligibility.

Therefore any Production change should be introduced through a focused design and shadow/actual-path validation, not by directly remapping the reason label.

## SELL Authority Gap Judgment

| Classification | Judgment |
|---|---|
| `SIGNAL_IS_OBSERVABILITY_ONLY_AND_BEHAVIOR_INTENDED` | PARTIAL |
| `HOLD_EXIT_BOUNDARY_REASONABLE` | YES_UNDER_CURRENT_CONTRACT |
| `REDUCE_AUTHORITY_GAP` | YES_FOR_PROFIT_RETENTION_SUBMODEL |
| `PROFIT_RETENTION_SIGNAL_TOO_WEAKLY_BINDING` | YES_AS_DESIGN_GAP |
| `EXIT_CONFIRMATION_TOO_STRICT` | PARTIAL / DESIGN_REVIEW |
| `SEMANTIC_INFORMATION_LOSS` | PARTIAL |
| `CONCENTRATION_AWARENESS_GAP` | YES_AS_DESIGN_GAP |
| `CORRECTNESS_DEFECT` | NO |
| `MIXED` | YES |

## Required Answers

- `HISTORICAL_PROFIT_RETENTION_BREAK_DESIGN_FOUND`: YES
- `PROFIT_RETENTION_BREAK_CANONICAL_SEMANTIC`: peak-drawdown / profit-retention risk-review evidence; legacy alias `peak_drawdown_profit_retention_risk`; not simple profit-taking.
- `PROFIT_RETENTION_BREAK_IS_SELL_EVIDENCE`: YES, risk-review / profit-protection evidence.
- `PROFIT_RETENTION_BREAK_IS_TERMINAL_EXIT_AUTHORITY`: NO, not by itself; terminal only when paired with no-recovery / exit-candidate severity or other hard exit evidence.
- `PROFIT_RETENTION_BREAK_IS_REDUCE_AUTHORITY`: NO under current Production binding.
- `PROFIT_RETENTION_BREAK_CASE_COUNT`: 36
- `HOLD_CASE_COUNT`: 18
- `REDUCE_CASE_COUNT`: 0
- `EXIT_CASE_COUNT`: 18
- `HOLD_EXIT_DISCRIMINATOR_IDENTIFIED`: YES, `RECOVERY_PRESENT + PM_SEVERITY_NORMAL` vs `NO_RECOVERY + PM_SEVERITY_EXIT_CANDIDATE`.
- `HOLD_CASES_WITH_STRONG_CONTINUATION`: 17 strong plus 1 partial continuation; 18 continuation PASS.
- `HOLD_CASES_WITH_WEAK_OR_MIXED_CONTINUATION`: 0
- `HOLD_CASES_WHERE_PROFIT_PROTECTION_ACTION_SEEMS_WARRANTED`: 0 by accepted current contract; design-review candidates exist for high-notional / high-MFE / large-giveback rows such as 59350.
- `WHY_REDUCE_ZERO_EXPLAINED`: YES
- `PEAK_DRAWDOWN_WARNING_ROLE_DISTINCT`: YES
- `59350_HOLD_ARCHITECTURALLY_JUSTIFIED`: YES under current contract.
- `HOLD_TO_EXIT_PROGRESSION_EXPLAINED`: YES
- `HOLD_TO_REDUCE_PATH_EXISTS`: YES, but only through later separate REDUCE evidence, not direct `profit_retention_break` consumption.
- `PROFIT_RETENTION_SIGNAL_TOO_WEAKLY_BINDING`: YES_AS_DESIGN_GAP
- `EXIT_CONFIRMATION_TOO_STRICT`: PARTIAL / DESIGN_REVIEW
- `EXISTING_PIT_EVIDENCE_SUPPORTS_THREE_STAGE_PROTECTION`: YES
- `FIXED_TRAILING_STOP_REQUIRED`: NO
- `SEMANTIC_INFORMATION_LOSS_FOUND`: PARTIAL
- `CONCENTRATION_AWARENESS_GAP_FOUND`: YES_AS_DESIGN_GAP
- `CORRECTNESS_DEFECT_FOUND`: NO
- `PROFIT_RETENTION_SELL_AUTHORITY_REFINEMENT_JUSTIFIED`: YES
- `REDUCE_STAGE_REFINEMENT_JUSTIFIED`: YES
- `EXIT_STAGE_REFINEMENT_JUSTIFIED`: CONDITIONAL
- `PRODUCTION_REPAIR_JUSTIFIED`: NO
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES

## Next Recommended Step

Proceed with a design-only phase for a profit-protection escalation contract that preserves winner retention while separating:

```text
HOLD_CONTINUATION
PROFIT_PROTECT_REDUCE
EXIT
```

The design should use existing current PIT evidence first, include concentration / notional impact as a candidate discriminator, and explicitly avoid fixed trailing stops or immediate `profit_retention_break = EXIT` semantics.

## Final Judgment

`PHASE32_FM_PROFIT_RETENTION_BREAK_IS_RISK_REVIEW_EVIDENCE_WITH_HOLD_EXIT_BOUNDARY_VALID_BUT_PROFIT_PROTECTIVE_REDUCE_DESIGN_GAP_CONFIRMED`
