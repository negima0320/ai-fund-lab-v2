# Phase30-AG - Selection Coverage / Risk Caution / Capital Utilization Design Audit

Task ID: `Phase30-AG`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T061732506648Z
```

Boundary:

```text
READ_ONLY_DESIGN_AUDIT
NO_STRATEGY_CHANGE
NO_RUNTIME_CHANGE
NO_CONFIG_OR_THRESHOLD_CHANGE
NO_MODEL_RETRAINING
NO_HISTORICAL_OUTCOME_FIT
NO_TARGET_RUN_MUTATION
NO_FORCED_INVESTMENT
```

Analysis window:

```text
2022-08-10 -> 2022-11-16
66 completed business days
```

This window is fixed to the Phase30-AF audit window for comparability. The
target run may continue independently; partial later run state is not used here.

Evidence files:

```text
reports/phase_reports/phase30_ag_selection_coverage_capital_utilization_design_audit.json
reports/phase_reports/phase30_ag/full_selection_funnel.json
reports/phase_reports/phase30_ag/market_opportunity_capture.json
reports/phase_reports/phase30_ag/low_vs_high_position_days.json
reports/phase_reports/phase30_ag/risk_caution_cash.json
reports/phase_reports/phase30_ag/unused_opportunity_cash.json
reports/phase_reports/phase30_ag/selection_quality_comparator.json
reports/phase_reports/phase30_ag/winner_source_analysis.json
```

## Primary Judgment

```text
MARKET_OPPORTUNITY_CAPTURE = PARTIAL
SELECTION_RANKING_EFFECTIVENESS = PARTIAL
RISK_CAUTION_CALIBRATION = MIXED
LOW_POSITION_CAUSE = MULTI_CAUSAL
UNUSED_OPPORTUNITY_CASH_REPAIRABLE_WITH_EXISTING_DATA = YES
SELECTION_IMPROVEMENT_AVAILABLE_WITH_EXISTING_DATA = YES
```

The current chain is not broken at Runtime authority. The confirmed design gap
is earlier: existing PIT feature/SI evidence is available, but market-wide
healthy structures are only weakly captured by Candidate/Ranking and are then
further narrowed by PC opportunity score rules and PS zero-quantity conversion.

## Full Selection Funnel

Average daily funnel:

| Stage | Input avg | Pass avg | Drop avg | Authority | Consumer |
|---|---:|---:|---:|---|---|
| Market Universe | 4,186.64 | 3,630.68 | 555.95 | PIT feature / J-Quants derived universe | Candidate AI |
| Candidate Generation | 3,630.68 | 50.00 | 3,580.68 | Candidate AI `candidate_decisions.json` | Opportunity Ranking |
| Ranking | 50.00 | 50.00 | 0.00 | Opportunity `buy_rank` / uncalibrated score | BUY Quality / PC |
| Strategy Intelligence | 50.00 | 50.50 | n/a | SI shared evidence, not action authority | Entry Admission / PC / PM |
| Entry Admission | 50.50 | 46.05 | 4.45 | SI Entry Admission evidence | PC / PM ADD |
| Portfolio Construction | 50.50 | 10.95 | 39.55 | Target Portfolio Decision Authority | Position Sizing |
| Position Sizing | 10.95 | 1.14 | 9.82 | Quantity authority | Runtime Planning |
| Runtime BUY | 1.14 | 1.14 intent / 0.79 fill | n/a | Pure mapper / execution evidence | Pending / execution |

Dominant PC drop reasons:

```text
below_opportunity_top20|non_positive_expected_edge_score = 1,623
non_positive_expected_edge_score = 658
opportunity_score_contract_pass_no_target = 194
high_downside_risk_score|non_positive_expected_edge_score = 61
below_opportunity_top20|non_positive_expected_edge_score|high_downside_risk_score = 46
high_downside_risk_score = 28
```

Dominant PS zero-quantity reasons:

```text
RESOLVED_ZERO_DELTA = 3,216
RESOLVED_CANDIDATE = 42
```

Therefore, the main narrowing is:

```text
Market healthy structure -> Candidate Top50: very narrow capture
Candidate/SI 50 -> PC positive 10.95: opportunity rank/score dominated narrowing
PC positive 10.95 -> PS positive 1.14: zero-delta / lot conversion narrowing
```

Runtime mapped PS-positive BUYs. Runtime is not the main drop point.

## Existing Selection Evidence

| Evidence | Classification | Reason |
|---|---|---|
| 5D / 20D trend structure | SECONDARY | Present in features and PC fields, but not primary ranking authority. |
| MA5 / MA20 relationship | SECONDARY | Present and auditable; not dominant in ordering. |
| Momentum acceleration / deceleration | VETO | Effective through BUY_WAIT / NO_ADD / reduced-only states. |
| Continuation Quality | SECONDARY | Connected, but not very discriminating in this window. |
| Relative Strength | DIAGNOSTIC_ONLY | Present in SI/PC, limited action effect and not market-wide for non-selected names. |
| Downside Risk | SECONDARY | Connected; becomes stronger when high downside score appears. |
| Volatility | SECONDARY | Used in risk/quality/execution evidence but not primary. |
| Participation / volume | DIAGNOSTIC_ONLY | Feature exists; weak action effect relative to rank/score. |
| Regime compatibility | SECONDARY | Market Context modifies posture; should not be blanket suppression. |
| Entry Admission | VETO | BUY_WAIT / NO_ADD semantics are effective and should be preserved. |
| BUY Quality | PRIMARY | First major allocation-strength evidence consumed by PC/PS. |
| Opportunity rank / score | PRIMARY | Dominant current ordering evidence; score remains uncalibrated. |

AG confirms the concern from AA/AF: legacy opportunity rank/score remains more
action-effective than CQ / RS / Risk in selection and allocation ordering.

## Market Opportunity Capture

The AF healthy proxy is used only as a PIT audit benchmark:

```text
eligible allowed fresh rows
5D momentum > 0
20D momentum > 0
close > MA20
MA5 > MA20
5D-vs-20D delta >= -0.02
```

Average capture:

```text
healthy_proxy_count = 416.545/day
selected_healthy_proxy_count = 3.076/day
top10_healthy_proxy_count = 0.712/day
pc_positive_healthy_proxy_count = 0.803/day
ps_positive_healthy_proxy_count = 0.121/day
buy_healthy_proxy_count = 0.091/day
selected_capture_ratio = 0.7384%
ps_capture_ratio = 0.0291%
```

```text
MARKET_OPPORTUNITY_CAPTURE = PARTIAL
```

This does not mean the system should buy more. It means existing PIT structures
that look healthy by audit proxy are rarely surfaced into effective PS-positive
deployment.

## Low vs High Position Days

LOW POSITION is `positions <= 3`; HIGH POSITION is `positions >= 7`.

| Cohort | Days | Avg positions | Avg cash | Avg exposure | Healthy proxy | Candidate | PC positive | PS positive | BUY fills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LOW | 32 | 2.94 | 73.00% | 27.00% | 375.78 | 50.00 | 9.59 | 0.72 | 0.34 |
| HIGH | 10 | 7.50 | 64.50% | 35.50% | 514.00 | 50.00 | 14.80 | 2.20 | 2.10 |

LOW days were not pure opportunity scarcity: the market proxy still averaged
375.78 healthy rows and Candidate stayed at 50. The cause is multi-causal:
market/risk caution, PC rank/score narrowing, and PS conversion all contribute.

```text
LOW_POSITION_CAUSE = MULTI_CAUSAL
```

## Risk Caution Cash

AF had 54 `RISK_CAUTION_CASH` days. AG decomposes these as non-exclusive
evidence proxies:

```text
Entry Admission caution / reduced-only or BUY_WAIT present = 54
Position Sizing zero-delta / lot conversion pressure = 54
Runtime no-order after zero quantity = 54
Market Regime BEAR/RISK_OFF contribution = 13
strong_individual_opportunity_days = 50
```

```text
RISK_CAUTION_CALIBRATION = MIXED
```

Risk caution is often legitimate, but there is a design smell: strong individual
PIT structures existed on most risk-caution days. Market-level caution should
remain a brake, but should not automatically suppress individually strong,
risk-contained opportunities.

## Unused Opportunity Cash

AF had 12 `UNUSED_OPPORTUNITY_CASH` days. All 12 classify as:

```text
PS_CONVERSION_DROP
```

This is repairable with existing data because the artifacts already contain:

- PC positive / zero target evidence,
- PS `RESOLVED_ZERO_DELTA`,
- lot feasibility / minimum meaningful notional evidence,
- Runtime `zero_quantity_delta` no-order evidence,
- Entry Admission / BUY Quality / rank evidence.

```text
UNUSED_OPPORTUNITY_CASH_REPAIRABLE_WITH_EXISTING_DATA = YES
```

The repair should improve evidence and conversion semantics. It must not bypass
lot constraints or force exposure.

## Selection Ranking

Current selected candidates and non-selected healthy proxy rows cannot be fully
compared on CQ / RS / Risk / Entry Admission because those SI fields are only
materialized for selected Strategy candidates. That is itself a coverage gap.

What can be compared today:

- trend structure,
- acceleration/deceleration,
- volatility,
- participation,
- rank/score behavior,
- BUY Quality and Entry Admission for selected rows.

Diagnosis:

```text
SELECTION_RANKING_EFFECTIVENESS = PARTIAL
```

Ranking is not empty or disconnected, but it remains too dominated by
uncalibrated opportunity rank/score. A high priority improvement is to introduce
a Selection quality comparator that uses existing PIT trend/CQ/RS/Risk evidence
before final opportunity-rank dominance, without creating a new parallel
Strategy path.

## Winner Source

Top winners were not sourced from a single explicit CQ/RS primary rule. Their
selection was usually mediated by opportunity rank / BUY Quality, with Entry
Admission deciding BUY_WAIT / reduced-only semantics.

The current winner source therefore suggests:

```text
Better Selection = HIGH priority
Better loss avoidance = HIGH priority
Better winner concentration = MEDIUM priority
Better capital allocation = MEDIUM priority
Regime multiplier change = LOW priority
```

Do not use future PnL to tune production parameters. Winner/loser analysis is
diagnostic only.

## Payoff Improvement Levers

Priority levers:

1. Better Selection - HIGH
   Market healthy proxy capture is partial and rank/score dominance is visible.

2. Better loss avoidance - HIGH
   Payoff ratio is below 1.0; average loser magnitude exceeds average winner.

3. Better capital allocation - MEDIUM
   PC -> PS conversion leaves 12 unused opportunity cash days.

4. Better winner concentration - MEDIUM
   94320 ADD worked, but the winner pool stayed narrow.

5. Regime policy - LOW
   AF did not support BEAR conviction inversion.

6. Insufficient existing data - LOW for this repair
   Most required evidence exists; sector-relative strength remains a separate
   data foundation item.

## Regime Policy

AF found:

```text
BEAR_CONVICTION_HYPOTHESIS = NOT_SUPPORTED
```

AG does not recommend BULL/BEAR multiplier inversion. The design issue is more
specific:

```text
Market Regime brake vs Individual Opportunity Quality
```

Market Context should remain posture/risk evidence. However, a BEAR or
risk-off regime should not uniformly overpower names with strong/supportive RS,
healthy CQ, contained individual risk, and healthy Entry Admission. This is a
design review target, not a multiplier change.

## No Forced Investment

AG explicitly rejects:

```text
minimum 2 / 5 / 8 positions
cash cap
minimum exposure
buying when no valid opportunity exists
buying because regime is BEAR
Runtime override to create BUY
```

Correct zero BUY / high cash days must remain valid.

## Improvement Candidate Ranking

| Rank | Candidate | Impact | Evidence | Existing data | Impl risk | Regression risk |
|---:|---|---|---|---|---|---|
| 1 | Selection quality comparator using existing PIT trend/CQ/RS/Risk before final opportunity-rank dominance | HIGH | HIGH | HIGH | MEDIUM | MEDIUM |
| 2 | Capital utilization reason taxonomy and PC->PS zero-quantity diagnostics | MEDIUM | HIGH | HIGH | LOW | LOW |
| 3 | Risk caution calibration by individual opportunity exception evidence | MEDIUM | MEDIUM | HIGH | MEDIUM | MEDIUM |
| 4 | Winner concentration comparator across BUY_NEW / ADD / Cash using lifecycle evidence | MEDIUM | MEDIUM | HIGH | MEDIUM | MEDIUM |
| 5 | Sector-relative strength data foundation | MEDIUM | LOW | LOW | HIGH | MEDIUM |

```text
SELECTION_IMPROVEMENT_AVAILABLE_WITH_EXISTING_DATA = YES
```

There is a HIGH candidate using existing data: the Selection quality comparator.
It should be designed as a modification to existing ranking / PC evidence
consumption, not a new parallel Selection path.

## Existing Logic Retirement

| Logic | Classification | Reason |
|---|---|---|
| Opportunity buy_rank / runtime_opportunity_score | MODIFY | Keep as evidence; prevent dominance when PIT structure is weak. |
| Candidate AI Top50 | MODIFY | Keep authority; add coverage diagnostics and quality comparison. |
| Entry Admission BUY_WAIT / NO_ADD | KEEP | Effective veto/reduced semantics. |
| Adaptive BUY Quality | MODIFY | Improve existing CQ/RS/trend/participation consumption. |
| Portfolio Construction target authority | KEEP | Correct target authority boundary. |
| Position Sizing lot/quantity authority | KEEP | Correct quantity authority; improve diagnostics, do not bypass. |
| Market Regime policy/brake | MODIFY | Preserve brake; add individual-quality exception evidence. |
| Forced minimum positions/exposure/cash cap | RETIRE_IF_REPLACED | Do not introduce. |

## Production Integrity

```text
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AG
```

## Recommended Next Task

```text
Phase30-AH - Selection Quality / Opportunity Capture Repair Design
```

Scope should be design-only unless separately authorized. It should use existing
PIT feature, SI, Entry Admission, BUY Quality, PC, and PS evidence to specify
how Selection quality and opportunity capture can be improved without forced
investment, threshold fitting, multiplier changes, model retraining, or Runtime
authority changes.
