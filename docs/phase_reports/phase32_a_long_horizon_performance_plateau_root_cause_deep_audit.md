# Phase32-A - Long-Horizon Performance Plateau Root-Cause Deep Audit

## Executive Summary

`Phase32-A` performed a READ-ONLY root-cause audit over
`runtime-test-historical-extended-smoke-20260825T235520054579Z`.

The plateau is real. Equity moved from `1,793,320` on `2023-05-31` to
`1,776,560` on `2024-02-26`, a `-0.93%` period return after the spring
acceleration had already lifted equity to roughly the `1.8M` range. The
plateau starts after the `2023-05-30` / `2023-05-31` transition: post-spring
daily equity changes become small and alternating, with no `+50k` daily gain
days in the plateau window.

The primary supported cause is not a single hard defect. The evidence supports
a composite plateau:

1. spring performance was few-winner dominated and unusually convex;
2. plateau campaigns still found some winners, but later winners were usually
   lower notional or offset by similarly sized losers;
3. PM continued to emit many `ADD` decisions, but PC/PS/runtime only converted
   a small number into ADD capital and fills, so winner amplification was weak;
4. explicit Cash / risk-pacing / MCC retained a larger share of equity in Cash
   during many conflicted market-structure days;
5. current architecture does not yet evaluate incumbent HOLD capital against
   NEW / ADD alternatives with high-resolution portfolio-wide opportunity
   cost, which appears material as a performance ceiling but not as a proven
   mandatory Strategy defect.

Measurement integrity passed. No code, config, Strategy, threshold, model,
fresh-run, resume, replay, or long Historical execution was changed or run.

## Measurement Integrity

Target run:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
completed audited dates = 343
first date = 2022-10-03
last audited date = 2024-02-26
```

Checks:

| Check | Result |
| --- | --- |
| Valuation projection status | `PASS` on audited dates |
| Valuation apply postcondition | `PASS` on audited dates |
| Duplicate execution ids | `0` duplicate days |
| Temporal/future flags in sampled canonical artifacts | `0` positive flags found |
| Projection source market date | same-day on audited dates |
| Known stale-looking field | 11 `existing_valuation_as_of` values lag prior trading day, while projection source and apply postcondition remained same-day/PASS |

The plateau is not explained by observed valuation failure, duplicate
execution, missing same-day projection, or future-information contamination.
`PHASE32_A_MEASUREMENT_INTEGRITY = PASS`.

## Window Definition

| Window | Dates | Start Equity | End Equity | PnL | Return | Avg Exposure | Avg Cash Ratio |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A Pre-Acceleration | 2022-10-03 to 2023-02-28 | 1,012,350 | 1,197,150 | +184,800 | +18.25% | 75.9% | 24.1% |
| B Strong Acceleration | 2023-03-01 to 2023-05-30 | 1,206,160 | 1,806,180 | +600,020 | +49.75% | 72.2% | 27.8% |
| C Plateau | 2023-05-31 to 2024-02-26 | 1,793,320 | 1,776,560 | -16,760 | -0.93% | 62.2% | 37.8% |

Representative plateau month-end shape:

| Month | Last Date | Equity | Return vs 1M | Cash % | Exposure % | Positions |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023-05 | 2023-05-31 | 1,793,320 | +79.33% | 15.4% | 84.6% | 11 |
| 2023-08 | 2023-08-31 | 1,806,380 | +80.64% | 16.0% | 84.0% | 14 |
| 2023-09 | 2023-09-29 | 1,864,450 | +86.44% | 59.1% | 40.9% | 9 |
| 2023-12 | 2023-12-29 | 1,799,230 | +79.92% | 79.0% | 21.0% | 3 |
| 2024-02 | 2024-02-26 | 1,776,560 | +77.66% | 70.6% | 29.4% | 5 |

## Acceleration vs Plateau Comparison

| Metric | Acceleration | Plateau | Interpretation |
| --- | ---: | ---: | --- |
| BUY fills | 92 | 289 | Plateau did not stop buying |
| SELL fills | 96 | 328 | Plateau had heavy turnover / de-risking |
| BUY notional | 9,940,000 | 28,015,300 | Capital was recycled frequently |
| SELL notional | 9,784,600 | 28,942,310 | SELL notional slightly exceeded BUY notional |
| Avg full-eligible candidates | 3.69/day | 5.26/day | Candidate supply did not collapse |
| Avg reduced-eligible candidates | 24.95/day | 25.23/day | Candidate-to-BUY evidence stayed broad |
| Avg high quality band | 6.07/day | 7.52/day | No obvious Candidate discovery degradation |
| Avg top-10 quality score | 0.646 | 0.682 | Entry surface did not weaken by this metric |
| Avg pre-pacing demand weight | 0.289 | 0.202 | Security demand was lower in plateau |
| Avg post-security allocation weight | 0.158 | 0.123 | PC authorized less security capital |
| Avg authorized Cash allocation weight | 0.236 | 0.317 | Explicit Cash allocation rose |
| Avg exposure | 72.2% | 62.2% | Plateau capital was less exposed |
| PM ADD decisions | 73 | 242 | ADD desire existed |
| PC ADD weight | 0.000 | 0.087 total | ADD was only lightly capitalized |

Daily PnL changed more than candidate counts. Acceleration had eight daily
gains above `50k`; plateau had zero. Plateau had many small positive and
negative days (`93` positive, `89` negative), with the largest gain only
`+39,260` and largest loss `-48,480`.

## Candidate Funnel

Candidate width remained fixed at 50 per day. In plateau:

- average full-eligible candidates: `5.26`;
- average reduced-only candidates: `25.23`;
- average `BUY_WAIT`: `10.87`;
- average rejects: `8.64`;
- average high-band candidates: `7.52`;
- average quality score: `0.526`;
- average top-10 quality score: `0.682`.

This does not support a broad Candidate Discovery defect. Candidate-side
opportunity evidence remained available. However, pre-pacing security demand
fell from `0.289` in acceleration to `0.202` in plateau, so the later
opportunity set appears less capital-compelling after PM / PC interpretation
even though raw candidate count and quality-band counts did not deteriorate.

## Capital Funnel

Plateau capital path:

```text
50 candidate rows/day
-> ~30.5 FULL or REDUCED rows/day
-> 0.202 avg pre-pacing demand weight
-> 0.123 avg post-security allocation weight
-> 0.317 avg authorized Cash weight
-> 2.39 avg PS positive BUY rows/day
-> 2.20 avg runtime BUY plans/day
-> 289 BUY fills over 182 days
```

Position Sizing did not look like the dominant blockage. The dominant zero
quantity reason was `NO_POSITIVE_QUANTITY_DELTA`; `STRATEGY_CAP_BOUND` appeared
only 7 times in plateau and the read-only aggregate found no lot-infeasible
dominance. The main capital loss happens before PS: lower PC security
allocation and higher Cash allocation.

## Cash Decomposition

Plateau average Cash was `683,937`, or `37.8%` of equity. The decomposition is
multi-causal:

| Cause | Evidence | Classification |
| --- | --- | --- |
| Genuine no-candidate Cash | Candidate count fixed at 50; ~30 FULL/REDUCED rows/day | Not primary |
| Candidate-quality rejection Cash | Rejections stable vs acceleration; high-band count higher in plateau | Low |
| PC / MCC Cash competition | Avg authorized Cash weight rose to `0.317`; avg post-security weight only `0.123` | High |
| Risk Pacing / Market Quality | `CAUTIOUS_DEPLOYMENT` on 122/182 plateau days | Medium-high |
| SELL after de-risking | SELL notional `28.94M` exceeded BUY notional `28.02M` | Medium |
| Position cap / lot feasibility | `STRATEGY_CAP_BOUND` only 7 plateau rows; no dominant lot-zero pattern | Low |
| Unexplained Cash | Some source-level observability remains insufficient for exact yen attribution | Medium residual |

Representative plateau days with material pre-demand but low final security
allocation:

| Date | Regime | Market Quality | Risk Pacing | Pre | Post | Cash Alloc | Exposure | Deferrals |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2023-06-29 | BULL | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | CAUTIOUS_DEPLOYMENT | 0.393 | 0.030 | 0.306 | 77.7% | 5 |
| 2023-07-18 | CORRECTION | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 0.446 | 0.000 | 0.370 | 75.8% | 10 |
| 2023-07-21 | RANGE | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 0.456 | 0.029 | 0.331 | 87.0% | 7 |
| 2023-09-14 | BULL | CONFLICTED_MARKET_STRUCTURE | CAUTIOUS_DEPLOYMENT | 0.296 | 0.000 | 0.365 | 81.0% | 5 |
| 2024-01-04 | RECOVERY | RECOVERY_CONFIRMATION_INCOMPLETE | GRADUAL_REDEPLOYMENT | 0.267 | 0.019 | 0.794 | 32.2% | 6 |

These examples support material Cash formation from PC/MCC/Risk Pacing, but do
not prove redundant or defective double suppression. Several low-post days
already had high exposure.

## Risk Pacing Analysis

Plateau Risk Pacing distribution:

```text
CAUTIOUS_DEPLOYMENT = 122 days
NORMAL_DEPLOYMENT = 31 days
GRADUAL_REDEPLOYMENT = 29 days
```

Risk Pacing was material to deployment. It is not, however, contradicted by
G140. G140 established architectural necessity: candidate scarcity alone does
not reliably de-risk the portfolio. Phase32-A confirms the separate point that
Risk Pacing materially contributed to Cash / lower exposure during the plateau.
Necessity and calibration/material contribution are different claims.

No evidence from this read-only audit proves that Risk Pacing should be
weakened, removed, or retuned.

## NEW / ADD Analysis

NEW_BUY continued to operate. Plateau had `289` BUY fills and `28.0M` BUY
notional, so this was not a complete entry-pipeline failure.

ADD was different. PM emitted many ADD decisions:

```text
Acceleration PM ADD decisions = 73
Plateau PM ADD decisions = 242
```

Yet plateau PC ADD allocation was only `0.087` total authorized weight across
the whole window, with average PC ADD count `0.03/day`. ADD rows did propagate
on concrete days such as `2023-05-31`, `2023-06-13`, `2023-06-19`,
`2023-06-20`, and `2023-06-22`, and same-symbol BUY fills were present on
those dates. Therefore ADD was functional but economically small.

## G129 Regression Check

G129 report path:

```text
docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md
```

G129 contract:

```text
BUY_ADD order increment authority =
pc_positive_executable_quantity_authority.final_allocated_quantity
```

Post-G129 plateau evidence:

- `2023-05-31`: PC selected `30410` ADD, PS produced `BUY_ADD` quantity delta
  `100`, runtime planned `BUY_ADD`, execution had same-symbol BUY fill
  `30410` for `100` shares / `138,500`.
- `2023-06-13`: PC/PS/runtime ADD for `21340`, same-symbol BUY fill `21340`.
- `2023-06-19` and `2023-06-20`: PC/PS/runtime ADD for `59550`, same-symbol
  BUY fills `59550`.
- `2023-06-22`: PC/PS/runtime ADD for `21340`, same-symbol BUY fill `21340`.

The fill observability field `source_decision_type` often remains generic
`BUY`, so exact ADD-fill counting from `fills.json` alone undercounts. Campaign
history confirms at least one plateau winner with ADD materialization:
`21340` opened `2023-06-05`, had `buy_history_summary.count = 3`,
`add_history_summary.count = 2`, and closed `2023-07-07` with `+61.11%`
campaign relative return.

Conclusion:

```text
PHASE32_A_G129_REGRESSION = NO
```

There is an observability follow-up: fill-level `source_decision_type` should
preserve `BUY_ADD` more explicitly for future audits. That is not evidence of
actual-path regression.

## Winner / Campaign Analysis

Campaigns opened during acceleration:

```text
count = 80
avg campaign return = +4.06%
median campaign return = -0.24%
campaigns >= +20% = 7
MFE >= +20% = 14
approx campaign PnL sum = +473,380
```

Top acceleration contributors were large enough and convex enough to move the
whole portfolio:

| Symbol | Open | Close | Return | Approx PnL | Buy Notional |
| --- | --- | --- | ---: | ---: | ---: |
| 59350 | 2023-03-22 | 2023-04-20 | +104.99% | +193,600 | 184,400 |
| 67310 | 2023-04-21 | 2023-04-27 | +50.00% | +100,000 | 200,000 |
| 44440 | 2023-03-16 | 2023-03-22 | +51.19% | +56,000 | 109,400 |
| 71160 | 2023-05-11 | 2023-06-20 | +26.27% | +43,300 | 164,800 |
| 64240 | 2023-03-16 | 2023-03-23 | +30.58% | +41,400 | 135,400 |

Campaigns opened during plateau:

```text
count = 208
avg campaign return = +1.20%
median campaign return = -0.25%
campaigns >= +20% = 9
MFE >= +20% = 16
approx campaign PnL sum = +94,490
```

Plateau found winners, including `65730` at `+156.64%`, but the largest one
had only about `42,340` buy notional, yielding about `66,320` approximate PnL.
Other winners were frequently offset by similarly sized losers such as
`55740`, `74770`, `95650`, and `69420`.

Thus winner discovery did not disappear, but winner contribution quality
deteriorated materially at the portfolio level.

## Long-Lived Holdings Analysis

Final open long-lived example:

| Symbol | Campaign | Open | Qty | Market Value | Relative Return | MFE | ADD History |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| 94320 | pc-cc034db5d5d0bb59-94320-0002 | 2022-12-15 | 600 | ~109,200 | +17.23% | +23.16% | 5 ADDs, latest 2023-02-24 |

Sample decision-time PM trace for `94320`:

| Date | PM Action | Market Value | Unrealized PnL | Reason evidence |
| --- | --- | ---: | ---: | --- |
| 2023-06-01 | ADD | 94,920 | 1,770 | strong trend continuation, opportunity rank still high, no loss averaging |
| 2023-06-19 | ADD | 97,980 | 4,830 | same |
| 2023-09-27 | ADD | 108,780 | 15,630 | same |
| 2023-12-29 | ADD | 103,140 | 9,990 | same |
| 2024-02-26 | ADD | 108,360 | 15,210 | same |

The HOLD/ADD evidence was not obviously irrational in isolation. The material
question is external opportunity cost: current architecture lacks a
portfolio-wide high-resolution comparison between incumbent HOLD capital and
available NEW / ADD alternatives. That limitation is visible, but this audit
does not use future returns to declare that selling `94320` would have been
better at any date.

## Capital Opportunity Cost Analysis

Decision-time evidence shows repeated coexistence of:

- incumbent capital retained by PM HOLD/ADD evidence;
- fresh NEW_BUY allocation candidates;
- high Cash allocations under cautious or conflicted market structure;
- coarse `COMPARABLE_MARGINAL` capital classes.

This supports a material incumbent-capital mobility limitation. The current
system can decide NEW / ADD / Cash for incremental capital, but it does not yet
evaluate already deployed HOLD capital as an explicit competitor in a
portfolio-wide release/redeploy decision. That matches the documented future
SoT, not a newly discovered Runtime defect.

## Market / Regime Analysis

Acceleration:

```text
BULL 29, RANGE 13, RECOVERY 13, CORRECTION 3, BEAR 3
CAUTIOUS_DEPLOYMENT 33, NORMAL_DEPLOYMENT 16, GRADUAL_REDEPLOYMENT 12
```

Plateau:

```text
BULL 76, RANGE 39, RECOVERY 32, BEAR 21, CORRECTION 14
CAUTIOUS_DEPLOYMENT 122, NORMAL_DEPLOYMENT 31, GRADUAL_REDEPLOYMENT 29
```

Plateau included many BULL days, but Market Quality was often conflicted or
weak:

```text
SHORT_TERM_BREADTH_BREAKDOWN = 56
CONFLICTED_MARKET_STRUCTURE = 53
RECOVERY_CONFIRMATION_INCOMPLETE = 29
HEALTHY_EXPANSION = 28
```

So `BULL` alone does not imply a full-investment defect. The dominant market
interpretation is that the post-spring environment supplied many candidates
but fewer portfolio-moving, large-notional winners under the system's
decision-time evidence and risk posture.

## Hypothesis Matrix

| Hypothesis | Support | Causal Class | Materiality | Evidence |
| --- | --- | --- | --- | --- |
| H1 Genuine Opportunity Scarcity | PARTIALLY_SUPPORTED | SECONDARY_CAUSE | MEDIUM | Candidate counts stayed high, but pre-demand and campaign payoff quality fell |
| H2 Candidate Discovery Failure | NOT_SUPPORTED | NON_CAUSE | LOW | Full/high/top-10 quality metrics did not degrade |
| H3 Candidate-to-BUY Conversion Failure | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM | BUY_WAIT/reject stable; conversion continued, but post-security allocation lower |
| H4 Capital Competition Suppression | SUPPORTED | SECONDARY_CAUSE | HIGH | Post-security allocation 0.123 vs Cash allocation 0.317 |
| H5 Risk Pacing Suppression | SUPPORTED | AMPLIFIER | MEDIUM-HIGH | 122/182 cautious days; low-post-demand examples |
| H6 PS / Lot Resolution Limitation | NOT_SUPPORTED | NON_CAUSE | LOW | Zero reasons dominated by no positive delta, not lot/cap failure |
| H7 BUY_ADD Underdeployment | SUPPORTED | AMPLIFIER | MEDIUM | 242 PM ADD decisions but only 0.087 total PC ADD weight |
| H8 Incumbent Capital Lock / Value Resolution | PARTIALLY_SUPPORTED | SECONDARY_CAUSE | MEDIUM-HIGH | Long-lived HOLD/ADD evidence plus no HOLD-capital opportunity-cost authority |
| H9 Winner Retention Failure | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM | Plateau winners existed but did not become portfolio-moving; no broad PM failure proven |
| H10 Weak Position Retention / Capital Drag | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM | Long-lived capital retained; external opportunity cost unresolved |
| H11 Entry Quality Degradation | PARTIALLY_SUPPORTED | SECONDARY_CAUSE | MEDIUM | Campaign avg/MFE lower; candidate quality metrics not lower |
| H12 Excessive Churn | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM | 56.96M plateau turnover with near-zero net equity progress |
| H13 Market Regime / Opportunity Structure Change | SUPPORTED | PRIMARY_CAUSE component | HIGH | No large daily gain days after spring; more conflicted/cautious market quality |
| H14 Concentrated Winner Dependence | SUPPORTED | PRIMARY_CAUSE component | HIGH | Spring top winners dominated; plateau winners smaller/offset |
| H15 Measurement / Accounting Artifact | NOT_SUPPORTED | NON_CAUSE | LOW | Measurement gate PASS |
| H16 Other | UNRESOLVED | FOLLOWUP | MEDIUM | Need exact symbol-level daily contribution file for yen-perfect decomposition |

## Root Cause Ranking

1. `PRIMARY_CAUSE`: few-winner-dominated momentum payoff did not repeat at
   portfolio-moving notional after spring. Plateau had winners, but their
   aggregate contribution was much smaller and offset by losers.
2. `PRIMARY_CAUSE`: market/opportunity structure changed from a convex spring
   burst to mixed/choppy conditions with no large daily portfolio gain days.
3. `SECONDARY_CAUSE`: PC/MCC/Risk Pacing allocated materially more capital to
   Cash and less to securities in many plateau days.
4. `SECONDARY_CAUSE`: high-resolution marginal value / incumbent capital
   opportunity-cost limitation likely capped capital mobility, especially for
   long-held positions, but remains a limitation rather than a proven defect.
5. `AMPLIFIER`: BUY_ADD underdeployment reduced winner amplification. G129 did
   not regress, but ADD materiality stayed small.
6. `NON_CAUSE`: measurement/accounting artifact, broad Candidate discovery
   failure, and dominant PS/lot infeasibility.

## Defect vs Limitation vs Normal Behavior

The plateau is partly normal for a few-winner momentum strategy: most of the
return came from a small number of strong campaigns, and a long flat period
after a convex burst is plausible.

It is also a real architectural limitation signal. The current system has
coarse marginal capital value and no portfolio-wide rotation authority for
incumbent HOLD capital. This is material enough for future research, but this
audit did not prove a mandatory Strategy defect or a Phase31 reopening
condition.

## Answers To Required Questions

1. Plateau exists: yes.
2. Start point: after `2023-05-30`; audit window starts `2023-05-31`.
3. Biggest structural difference: spring had large, concentrated winners with
   portfolio-moving daily gains; plateau had many small campaigns and high
   turnover with no large daily gain days.
4. Market opportunity scarcity alone: no; opportunity quality/payoff structure
   scarcity is partial.
5. Candidate discovery degraded: no broad evidence.
6. Entry quality degraded: partial at campaign payoff level, not candidate
   quality-score level.
7. Winner discovery/retention degraded: winner contribution degraded; broad
   retention defect not proven.
8. Cash cause: PC/MCC/Risk Pacing plus SELL recycling and lower capital demand.
9. Risk Pacing material: yes, as an amplifier.
10. G140 contradiction: no.
11. PC Capital Competition material: yes.
12. PS/lot material: no.
13. ADD sufficient: no; functional but underdeployed.
14. G129 regression: no.
15. Long HOLD opportunity cost material: partial/yes as limitation.
16. High-resolution value ceiling evidence: partial/yes.
17. Rotation absence material: partial/yes as limitation, not defect.
18. Normal few-winner momentum plateau: partially yes.
19. Mandatory Strategy defect: no.
20. Phase32 repair or future optional: follow-up inventory/research, not
   immediate repair.

## Phase32 Implications

Do not start tuning from this report. Phase32 should remain Demo / Production
readiness, but it should carry a named readiness risk: production operators
must understand that accepted Strategy performance is bursty and may plateau
for many months. If performance work is later approved, the clean next target
is not Risk Pacing removal. It is read-only/shadow observability for:

- daily Cash cause decomposition;
- ADD intent-to-fill materiality;
- high-resolution marginal capital value evidence;
- incumbent HOLD opportunity-cost shadow;
- exact symbol-level daily contribution decomposition.

## Recommended Next Task

```text
Phase32-B - Demo / Production Readiness Operational Gate Inventory
```

Recommended optional sub-audit before implementation:

```text
Phase32-A1 - Plateau Observability Gap Closure Plan
```

This should be documentation / observability only unless the user explicitly
authorizes implementation.

## Files / Artifacts Inspected

- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_g140_candidate_scarcity_vs_risk_pacing_capital_suppression_necessity_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase31_g138_march_april_profit_formation_strategy_causality_audit.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- Run artifacts under
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/`
  including daily `buy_quality_decisions.json`, `market_context.json`,
  `portfolio_policy.json`, `portfolio_construction.json`,
  `position_sizing.json`, `runtime_planning.json`, `planning_evidence.json`,
  `fills.json`, `valuation_projection.json`, `valuation_apply_evidence.json`,
  `pm_decisions.json`, and `position_campaigns.json`.

## Commands Executed

READ-ONLY commands:

```text
sed -n ... pasted Phase32-A request
find reports .runtime -path '*runtime-test-historical-extended-smoke-20260825T235520054579Z*' ...
find scripts tools -maxdepth 3 -type f | rg 'performance|historical|runtime|summary|campaign|equity|plateau|cash|funnel|attribution'
find docs/phase_reports -maxdepth 1 -type f | rg 'phase31_g129|phase31_g138|phase31_g140|phase31_final|phase31_to_phase32'
sed -n ... required Phase31 / architecture SoT files
python3 - <<'PY' ... JSON shape inspection
python3 - <<'PY' ... aggregate window and funnel analysis
python3 - <<'PY' ... campaign and long-lived holding analysis
rg -n ... current source authority touchpoint
git status --short
```

No long Historical, fresh-run, resume, replay, tests, or production command was
executed.

## Final Judgments

`PHASE32_A_MEASUREMENT_INTEGRITY = PASS`

`PHASE32_A_PLATEAU_CONFIRMED = YES`

`PHASE32_A_PRIMARY_ROOT_CAUSE = FEW_WINNER_DOMINATED_MOMENTUM_PAYOFF_DID_NOT_REPEAT_AT_PORTFOLIO_MOVING_NOTIONAL_PLUS_CHOPPIER_MARKET_OPPORTUNITY_STRUCTURE`

`PHASE32_A_SECONDARY_ROOT_CAUSES = PC_MCC_CASH_ALLOCATION_AND_RISK_PACING_SUPPRESSION; INCUMBENT_CAPITAL_OPPORTUNITY_COST_LIMITATION; BUY_ADD_UNDERDEPLOYMENT`

`PHASE32_A_MARKET_OPPORTUNITY_SCARCITY_MATERIAL = PARTIAL`

`PHASE32_A_CANDIDATE_DISCOVERY_DEFECT = NO`

`PHASE32_A_ENTRY_QUALITY_DEFECT = NO`

`PHASE32_A_RISK_PACING_MATERIAL_SUPPRESSION = YES`

`PHASE32_A_CAPITAL_COMPETITION_LIMITATION_MATERIAL = YES`

`PHASE32_A_POSITION_SIZING_LIMITATION_MATERIAL = NO`

`PHASE32_A_BUY_ADD_DEPLOYMENT_LIMITATION_MATERIAL = YES`

`PHASE32_A_G129_REGRESSION = NO`

`PHASE32_A_INCUMBENT_CAPITAL_LOCK_MATERIAL = PARTIAL`

`PHASE32_A_HIGH_RESOLUTION_VALUE_LIMITATION_MATERIAL = PARTIAL`

`PHASE32_A_ROTATION_LIMITATION_MATERIAL = PARTIAL`

`PHASE32_A_WINNER_SCARCITY_MATERIAL = PARTIAL`

`PHASE32_A_MANDATORY_STRATEGY_DEFECT = NO`

`PHASE32_A_REPAIR_REQUIRED = FOLLOWUP_REQUIRED`

`PHASE32_A_PHASE31_REOPEN_REQUIRED = NO`

`PHASE32_A_PHASE32_NEXT_STEP = Phase32-B - Demo / Production Readiness Operational Gate Inventory`
