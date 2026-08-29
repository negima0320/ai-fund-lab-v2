# Phase32-DC — Mid-February Capital Deployment Collapse / Bull-Market Underdeployment Audit

## Executive Summary

This audit was performed READ-ONLY against:

- Run: `runtime-test-historical-extended-smoke-20260829T104242842079Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T104242842079Z`
- High-deployment control: `2023-01-24` through `2023-02-10`
- Collapse transition: `2023-02-13` through `2023-02-28`
- Persistent underdeployment: `2023-03-01` through `2023-05-29`

The mid-February exposure collapse is real and decomposes into two linked phases:

1. `2023-02-13` through `2023-02-28`: exposure collapsed primarily because PM generated a material REDUCE/EXIT wave while replacement BUY_NEW capital was much smaller. This was not a BF/PS/runtime disappearance: BUY targets that reached BF generally reached runtime.
2. `2023-03-01` through `2023-05-29`: exposure stayed low primarily because the production-deployable NEW/REENTRY funnel and ADD capitalization funnel were too sparse relative to available cash/budget. Cash became the residual allocation because few security lots survived admission, lot feasibility, cap, and capital-value gates.

Display `BULL` should not be read as a full-deploy signal. The decision artifacts repeatedly show conflicted or narrowing market quality plus `CAUTIOUS_DEPLOYMENT` / `MAINTAIN` posture. However, the portfolio policy still carried large available budget and `target_gross_exposure = 1.0`, so Risk Pacing was not the direct hard blocker. The main defect candidates are upstream semantic/materialization gaps: production-deployable NEW scarcity after quality/lot/cap gates, and PM ADD intent not becoming ADD investment evidence PASS.

No production code, config, thresholds, model, runtime state, replay, resume, backtest, or fresh-run was changed or executed.

## Run Identity

The target run directory exists and contains daily artifacts through at least `2023-05-31`. Exposure was computed from decision-time valuation evidence as:

`new_total_market_value / (cash + new_total_market_value)`

This matches the observed cash/security valuation shape in `current_valuation_refresh/valuation_projection.json`.

## Window Summary

| Window | Days | Avg Exposure | Avg Cash | Avg Equity | Avg Positions | BUY Notional | SELL Notional | Runtime BUY Count | Runtime SELL Count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| High-deployment control | 14 | 68.41% | 348,528 | 1,103,430 | 12.79 | 1,902,500 | 1,576,920 | 30 | 28 |
| Collapse transition | 11 | 35.69% | 732,455 | 1,138,956 | 7.55 | 436,060 | 977,550 | 12 | 20 |
| Persistent underdeployment | 60 | 16.91% | 944,035 | 1,136,610 | 3.83 | 1,691,510 | 1,490,780 | 38 | 36 |
| Oct-Dec control | 62 | 68.17% | 326,386 | 1,042,015 | 7.39 | 3,373,270 | 2,759,790 | 74 | 67 |

The structural break begins immediately after `2023-02-10`: exposure was `69.82%` on `2023-02-10`, then `54.91%` on `2023-02-13`, `30.59%` on `2023-02-16`, and `22.41%` on `2023-02-28`.

## Daily Capital Funnel

| Window | Avg PC NEW Positive / Candidate | Avg PC ADD Positive / Candidate | Avg Frontier NEW / REENTRY / ADD Candidates | Avg Accepted NEW / REENTRY / ADD | Avg BF NEW / REENTRY / ADD | Avg Security Allocation | Avg Budget Notional | Avg Authorized Cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| High-deployment control | 0.29 / 31.00 | 0.00 / 1.00 | 31.00 / 13.36 / 3.00 | 2.29 / 0.00 / 0.00 | 2.29 / 0.00 / 0.00 | 164,234 | 371,784 | 207,550 |
| Collapse transition | 0.45 / 29.82 | 0.00 / 1.00 | 30.18 / 15.55 / 3.00 | 1.45 / 0.00 / 0.00 | 1.09 / 0.00 / 0.00 | 39,337 | 683,228 | 643,891 |
| Persistent underdeployment | 0.23 / 30.58 | 0.00 / 0.95 | 31.05 / 16.10 / 2.85 | 1.13 / 0.02 / 0.00 | 0.67 / 0.02 / 0.00 | 31,338 | 925,554 | 894,215 |

The persistent period has abundant nominal budget but very little accepted security allocation. This is the clearest evidence that the underdeployment is not a downstream PS/runtime quantity disappearance. It is mostly a pre-BF authority/admission/feasibility problem.

## Structural Break Dates

| Date | Exposure | Cash | Positions | BUY Notional | SELL Notional | BF NEW / REENTRY / ADD | Security Allocation | Cash Disposition |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 2023-02-03 | 83.40% | 181,750 | 16 | 189,600 | 76,100 | 3 / 0 / 0 | 203,700 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |
| 2023-02-08 | 70.98% | 330,960 | 14 | 214,370 | 123,280 | 3 / 0 / 0 | 219,670 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |
| 2023-02-10 | 69.82% | 339,960 | 13 | 75,000 | 50,300 | 2 / 0 / 0 | 68,250 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |
| 2023-02-13 | 54.91% | 513,560 | 9 | 46,600 | 220,200 | 1 / 0 / 0 | 46,600 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |
| 2023-02-16 | 30.59% | 793,590 | 6 | 19,600 | 155,180 | 1 / 0 / 0 | 19,200 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |
| 2023-02-28 | 22.41% | 881,450 | 6 | 0 | 74,400 | 0 / 0 / 0 | 0 | ACCEPTED_OPTIONALITY |
| 2023-03-03 | 24.16% | 867,170 | 4 | 0 | 0 | 0 / 0 / 0 | 0 | ACCEPTED_OPTIONALITY |
| 2023-05-16 | 4.99% | 1,074,580 | 2 | 0 | 35,200 | 0 / 0 / 0 | 0 | ACCEPTED_OPTIONALITY |
| 2023-05-29 | 39.72% | 680,720 | 8 | 98,540 | 20,400 | 5 / 0 / 0 | 98,540 | REJECTED_BY_ACCEPTED_SECURITY_TARGETS |

## NEW Breadth And Target Magnitude

Raw NEW candidate breadth did not disappear: all three windows retained about 30 NEW frontier candidates per day. Production-deployable NEW breadth was scarce:

- High-deployment control: BF NEW targets averaged `2.29` per day.
- Collapse transition: BF NEW targets averaged `1.09` per day.
- Persistent underdeployment: BF NEW targets averaged `0.67` per day.

The dominant NEW drop reasons in the persistent window were:

- `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED`: 1,211 NEW reason occurrences.
- `pc_first_lot_zero_weight_reason_lot_minimum_exceeds_quality_authorized_target`: 584 occurrences.
- `cap_blocked`: 545 occurrences.
- `INFEASIBLE_LOT`: 495 occurrences.
- `desirability.status = REVIEW_REQUIRED` / blocked value class: 220 occurrences.
- `pc_first_lot_zero_weight_reason_buy_quality_wait`: 220 occurrences.
- `minimum_lot_exceeds_safety_hard_cap`: 156 occurrences.

This is not normal raw opportunity scarcity. It is scarcity after production deployability, Buy Quality, lot granularity, cap/headroom, and marginal-capital eligibility are applied.

## ADD Breadth And Winner Capitalization

ADD intent existed, but it did not become accepted ADD capital.

Representative 94320 observations on `2023-02-03`, `2023-02-08`, `2023-02-16`, `2023-03-03`, and `2023-05-16`:

- PM action: `ADD`
- PM reasons include `no_loss_averaging`, `opportunity_rank_still_high`, `strong_trend_continuation`
- Frontier generated three ADD lots for campaign `pc-74bc4041e9b6ef75-94320-0002`
- Each ADD lot disposition: `INELIGIBLE_ADD_ADMISSION_BLOCKED`
- `comparison_class = INSUFFICIENT`
- `capital_value_status = NOT_COMPARABLE`
- `desirability.status = REVIEW_REQUIRED`
- reasons include `missing_or_non_pass_add_evidence:expected_edge`, `missing_or_non_pass_add_evidence:incremental_value`, `pm_add_next_lot_candidate`, `feasible`

The persistent window retained about `0.95` PM ADD intents per day and `2.85` ADD frontier candidates per day, but accepted ADD was `0.00` per day. That is a material ADD authority suppression path: PM ADD intent is necessary candidate evidence, but the ADD investment evidence required by the frontier is not materializing as PASS.

## PM Retention And Collapse Transition

The collapse transition is sell-led.

On `2023-02-13`, PM produced:

- ADD 94320 with `KNOWN_AT_ENTRY` context.
- REDUCE 86220 and 45750 on fresh deterioration / peak drawdown evidence.
- EXIT 65390 and 43970 on persistent deterioration.
- EXIT 65570 and 23880 on `hard_stop_current_return`.
- Runtime fills included only one BUY notional around `46,600`, against SELL notional around `220,200`.

On `2023-02-16`, PM produced:

- EXIT 77760, 78410, and 39740 on persistent deterioration.
- ADD 94320 intent.
- Only one NEW BUY, 51030, `400` shares / about `19,600` notional.
- SELL notional around `155,180`.

This shows the exposure collapse itself is primarily PM retention and replacement-capital insufficiency, not a single-day Cash preference.

## Cash Competition

Cash became first-class and often accepted, but mostly as residual optionality.

Cash disposition counts:

- High-deployment control: `13` days rejected by accepted security targets, `1` day accepted optionality.
- Collapse transition: `8` days rejected by accepted security targets, `3` days accepted optionality.
- Persistent underdeployment: `30` days rejected by security targets, `30` days accepted optionality.

In the persistent window, average budget notional was `925,554`, average security allocation was only `31,338`, and average authorized cash was `894,215`. This means Cash did not consistently defeat a rich set of valid security alternatives; the pool of accepted security alternatives was often too small.

## Regime And Risk Pacing Context

The display regime frequently showed `BULL`, but the decision context was more cautious:

- `2023-02-08`, `2023-02-16`, `2023-02-28`: `regime_state = BULL`, `market_quality_state = CONFLICTED_MARKET_STRUCTURE`, `risk_pacing_intent = CAUTIOUS_DEPLOYMENT`, `entry_posture = MAINTAIN`.
- `2023-05-16`: `regime_state = BULL`, `market_quality_state = SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`, `risk_pacing_intent = CAUTIOUS_DEPLOYMENT`, `entry_posture = MAINTAIN`.

This is a real display-vs-decision mismatch if the UI/summary treats BULL as an instruction to deploy capital. It is only partial as a direct root cause because the artifacts still expose large available budget and `target_gross_exposure = 1.0`.

## Post-BF / PS / Runtime Suppression

No material systematic post-BF suppression was observed in the audited aggregate. In the persistent window, BF NEW/REENTRY targets averaged about `0.69` per day and runtime BUY count averaged about `0.63` per day. The larger collapse happens before BF:

- production admission
- Buy Quality / wait / reduced-only state
- lot granularity against quality-authorized targets
- cap/headroom
- ADD investment evidence non-PASS
- marginal-capital desirability/review-required gating

## Representative Symbol Traces

### 94320

94320 is the clearest winner-capitalization control. PM repeatedly emitted ADD intent with strong continuation reasons, but the capital frontier did not accept ADD lots because ADD investment evidence was insufficient or non-PASS. This is not a PM intent absence; it is an ADD evidence/admission bridge problem.

### 51030

On `2023-02-16`, 51030 received a NEW BF target of `400` shares and filled about `19,600` notional. It was then reduced on `2023-02-17` and exited by `2023-02-21` under deterioration evidence. This illustrates the second half of the issue: even when NEW is deployed, early PM exits can rapidly return capital to Cash.

### 94340

94340 was not a material active capital path in the Jan-May sample inspected for this run. It does not explain the mid-February underdeployment.

### 65740

On `2023-05-29`, 65740 shows that low-priced multi-lot NEW can still be accepted: BF accepted `2600` shares and runtime filled about `17,940` notional. This proves the machinery can deploy multi-lot NEW, but such cases were too sparse to reverse the earlier underdeployment.

## Architecture Conformance And Defect Candidates

The audit does not support a single downstream execution defect. The strongest findings are:

1. PM retention is material in the February transition. The portfolio sells faster than NEW/ADD can replace.
2. NEW raw opportunity breadth remains, but production-deployable NEW breadth is scarce after quality, lot, cap, and marginal-capital filters.
3. ADD capitalization is structurally suppressed: PM ADD intent exists, but ADD investment evidence expected edge / incremental value does not become PASS, leaving accepted ADD at zero.
4. Cash optionality is not obviously too aggressive as a standalone economic winner; it is mostly accepting residual budget after security candidates fail upstream.
5. `BULL` display can mislead unless paired with market quality / risk pacing / entry posture; the decision context was cautious despite BULL regime labels.

The primary diagnosis is therefore `MIXED`: sell-led PM retention plus production-deployable NEW scarcity plus ADD authority suppression.

## Recommendations

Do not tune thresholds, rank cutoffs, Cash preferences, or exposure targets from this outcome.

Recommended next steps:

1. Audit/repair the ADD investment evidence materialization path for PM ADD intent, especially `expected_edge` and `incremental_value` for persistent campaigns such as 94320.
2. Audit NEW/REENTRY production-deployable scarcity under BULL-but-cautious contexts, focusing on quality-authorized target, lot granularity, and cap/headroom interactions rather than raw candidate count.
3. Audit PM retention around `2023-02-13` through `2023-02-21` to confirm which exits were hard failures, true fresh deterioration, persistent deterioration, or entry-premise known caution.
4. Continue the long validation run, because the current evidence is diagnostic and does not show a reason to stop the run.

## Final Judgments

PHASE32_DC_HIGH_DEPLOYMENT_AVG_EXPOSURE = 68.41%

PHASE32_DC_COLLAPSE_WINDOW_AVG_EXPOSURE = 35.69%

PHASE32_DC_UNDERDEPLOYMENT_AVG_EXPOSURE = 16.91%

PHASE32_DC_PRIMARY_UNDERDEPLOYMENT_CAUSE = PM retention / REDUCE-EXIT wave during collapse, followed by persistent production-deployable NEW/REENTRY scarcity

PHASE32_DC_SECONDARY_CAUSE = ADD authority/evidence suppression: PM ADD intent did not become ADD investment evidence PASS, so winner capitalization remained blocked

PHASE32_DC_TERTIARY_CAUSE = Buy Quality / lot granularity / cap-headroom filters left large budget as residual Cash optionality

PHASE32_DC_NEW_BREADTH_SCARCE = PARTIAL

PHASE32_DC_NEW_TARGET_MAGNITUDE_SUPPRESSED = YES

PHASE32_DC_ADD_BREADTH_SCARCE = PARTIAL

PHASE32_DC_ADD_AUTHORITY_SUPPRESSION = YES

PHASE32_DC_PM_RETENTION_MATERIAL = YES

PHASE32_DC_CASH_ECONOMICALLY_WINS = PARTIAL

PHASE32_DC_CAP_HEADROOM_MATERIAL = PARTIAL

PHASE32_DC_RISK_PACING_MATERIAL = PARTIAL

PHASE32_DC_POST_BF_SUPPRESSION = NO

PHASE32_DC_DISPLAY_BULL_VS_DECISION_CONTEXT_MISMATCH = PARTIAL

PHASE32_DC_PRIMARY_DIAGNOSIS = MIXED

PHASE32_DC_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_DC_LONG_VALIDATION_CONTINUE = YES

PHASE32_DC_NEXT_STEP = Targeted ADD evidence/admission bridge audit for persistent PM ADD campaigns, plus NEW deployability and PM retention semantic audits; no threshold or Cash tuning from this historical outcome.
