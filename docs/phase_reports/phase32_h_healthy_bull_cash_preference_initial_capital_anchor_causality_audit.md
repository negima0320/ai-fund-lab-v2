# Phase32-H - Healthy-BULL Cash Preference / Initial-Capital Anchor Causality Audit

## Executive Summary

Phase32-H continues the Phase32-G cash frontier audit and asks whether high
Cash in healthy BULL conditions was caused by a hidden `1,000,000 JPY` initial
capital anchor.  The audit was read-only.  No production code, configuration,
threshold, model, PM, PC, MCC, Risk Pacing, PS, Runtime, Cash reserve, NEW/ADD
priority, High-Resolution Value, or Portfolio Rotation behavior was changed.

Final finding: the `1,000,000 JPY` anchor hypothesis is not supported for the
inspected run.  The repository contains many legitimate `1,000,000` references,
but the active lineage for the January 2024 focus dates uses current equity /
current cash surfaces, not initial cash as a deployment ceiling.  The direct
cause of high Cash in healthy BULL is the PC/MCC capital frontier: NEW supply
exists, but many NEW rows are marginal, Cash remains first-class optionality,
and PC/MCC often leaves large residual Cash even under `NORMAL_DEPLOYMENT`.

The result is a limitation, not a mandatory defect.  It justifies a shadow
capital-frontier trace, not production changes.

## Healthy-BULL Case Studies

Focus dates from Phase32-G: `2024-01-11`, `2024-01-15`, `2024-01-23`,
`2024-01-24`, `2024-01-31`.

| Date | Equity | Actual Cash | Cash ratio | Exposure | Positions | Market Quality | Risk Pacing | NEW competitors | PC NEW accepted | ADD competitors | Authorized Cash | Security allocation | MCC winner | BUY fills |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 2024-01-11 | 1,821,740 | 1,248,800 | 0.685 | 0.315 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 25 | 0.000000 | 0 | 0.593286 | 0.148148 | CASH_OPTIONALITY | 0 |
| 2024-01-15 | 1,843,390 | 1,107,600 | 0.601 | 0.399 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 24 | 0.000000 | 0 | 0.692474 | 0.000000 | CASH_OPTIONALITY | 0 |
| 2024-01-23 | 1,863,070 | 1,331,700 | 0.715 | 0.285 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 21 | 0.000000 | 0 | 0.622517 | 0.130434 | CASH_OPTIONALITY | 0 |
| 2024-01-24 | 1,849,330 | 1,331,700 | 0.720 | 0.280 | 5 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 22 | 0.041667 | 0 | 0.804532 | 0.065351 | NEW_BUY | 2 |
| 2024-01-31 | 1,809,150 | 1,175,340 | 0.650 | 0.350 | 4 | HEALTHY_EXPANSION | NORMAL_DEPLOYMENT | 29 | 0.026696 | 0 | 0.469605 | 0.202108 | NEW_BUY | 1 |

The focus dates do not show a missing candidate supply problem.  They show a
capital conversion problem: healthy BULL and normal Risk Pacing do not force
full deployment when the MCC surface classifies the opportunity set as marginal
or exhausted versus Cash.

## Cash Preference Causal Chain

The recurring focus-date causal chain is:

```text
Current equity and cash are visible
-> PC computes large available incremental budget from current portfolio state
-> BUY-quality and NEW competitor supply exist
-> ADD is absent on the five focus dates
-> MCC classifies NEW frontier as marginal / no valid deployable competitor
-> Cash competitor remains valid optionality
-> canonical multi-allocation may allow a small security subset
-> authorized Cash absorbs the residual
-> PS sizes only the PC-authorized securities
-> Runtime consumes PS/PC plans; it does not redecide Cash vs NEW
```

Focus-date reason evidence:

| Date | Cash preference evidence | Interpretation |
| --- | --- | --- |
| 2024-01-11 | `HEALTHY_MARKET_OPTIONALITY_LOW`, `MARGINAL_OPPORTUNITY_SET`, `NO_VALID_COMPETITOR`; best class `COMPARABLE_HIGH`, but no selected deployable symbol in cash evidence | Conservative frontier resolution despite healthy market. |
| 2024-01-15 | Same reason set; `COMPARABLE_HIGH=3`, `COMPARABLE_MARGINAL=21`; security allocation count `0` | Strongest possibly-overconservative case. |
| 2024-01-23 | `HEALTHY_MARKET_OPTIONALITY_LOW`, `NO_VALID_COMPETITOR`, `STRONG_OPPORTUNITY_PRESENT`; security allocations still only `0.130434` | Strong evidence can coexist with residual Cash. |
| 2024-01-24 | NEW wins single capital interaction, but authorized Cash remains `0.804532` | Deployment occurs, but frontier still preserves large Cash. |
| 2024-01-31 | NEW wins single capital interaction, security allocation `0.202108`, authorized Cash `0.469605` | Positive control within high-Cash healthy BULL. |

Primary answer: Cash wins partly because opportunity quality is not compelling
enough in the current MCC semantics, and partly because several conservative
authorities align.  The evidence does not show a hidden fixed yen ceiling.

## Capital Base Lineage

Active architecture states that `target_notional_candidate =
target_weight_candidate * canonical_capital_base`, and that
`canonical_capital_base` is Current Total Equity; see
[portfolio_construction_and_position_sizing_contract.md](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/portfolio_construction_and_position_sizing_contract.md:844)
and line `849`.

The active Runtime planning evidence also labels the capital winner as
`current_total_equity`, with `legacy_capital_config_used=false` and
`capital_fallback_used=false`; see
[morning_pipeline.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1414).

For available BUY cash, the fallback default is used only when Current has no
cash / buying-power evidence and must not reset continuity; see
[morning_pipeline.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1636).

Focus-date lineage:

| Date | Actual equity denominator | Available cash | PC available incremental weight | PC base | MCC base | Authorized security notional | Authorized Cash notional | PS base | BUY fill notional |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | ---: |
| 2024-01-11 | 1,821,740 | 1,248,800 | 0.741434 | Current equity / current portfolio state | PC weights over current equity | 269,887 | 1,080,768 | `portfolio_total_equity=1,821,740` | 0 |
| 2024-01-15 | 1,843,390 | 1,107,600 | 0.692474 | Current equity / current portfolio state | PC weights over current equity | 0 | 1,276,530 | `portfolio_total_equity=1,843,390` | 0 |
| 2024-01-23 | 1,863,070 | 1,331,700 | 0.752951 | Current equity / current portfolio state | PC weights over current equity | 243,010 | 1,159,930 | `portfolio_total_equity=1,863,070` | 0 |
| 2024-01-24 | 1,849,330 | 1,331,700 | 0.869883 | Current equity / current portfolio state | PC weights over current equity | 120,879 | 1,487,861 | `portfolio_total_equity=1,849,330` | 138,350 |
| 2024-01-31 | 1,809,150 | 1,175,340 | 0.671713 | Current equity / current portfolio state | PC weights over current equity | 365,716 | 849,656 | `portfolio_total_equity=1,809,150` | 137,670 |

The notional values are incompatible with a hard `1,000,000 JPY` deployment
ceiling.  Authorized Cash alone exceeds `1,000,000` on four of the five focus
dates, proving the retained Cash amount is not capped at initial cash.

## Initial-Capital Literal / Semantic Search Inventory

Search terms included `initial_cash`, `initial_capital`, `starting_cash`,
`starting_equity`, `base_capital`, `capital_base`, `deployable_capital`,
`investment_budget`, `buying_power`, `cash_budget`, `reserve_base`,
`portfolio_budget`, `notional_budget`, `max_deployment`, `exposure_budget`,
`capital_authority`, `nav_base`, `equity_base`, `1000000`, `1_000_000`,
`1e6`, and related display forms.

Representative classification:

| Hit family | Example | Classification | Defect relevance |
| --- | --- | --- | --- |
| Historical profile initial state | [historical_extended_smoke_10bd.json](/Users/negishi/work/ai-fund-lab-v2/config/runtime_tests/historical_extended_smoke_10bd.json:17) | `HISTORICAL_PROFILE` | Legitimate bootstrap input. |
| Runtime reset override | [scripts/runtime_test.py](/Users/negishi/work/ai-fund-lab-v2/scripts/runtime_test.py:4105) | `RUNTIME_INPUT` | Sets reset initial state only. |
| Historical reset plan defaults | [reset_plan.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py:17) | `HISTORICAL_PROFILE` | Reset/bootstrap plan support. |
| Capital deployment config metadata | [capital_deployment.json](/Users/negishi/work/ai-fund-lab-v2/configs/runtime_v2/capital_deployment.json:4) | `DEAD/LEGACY` / metadata | Active lineage marks legacy capital config unused. |
| Current capital authority | [morning_pipeline.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1414) | `PRODUCTION_AUTHORITY` | Uses current total equity, not initial cash. |
| Current available cash | [morning_pipeline.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1641) | `PRODUCTION_AUTHORITY` | Uses current cash / buying power before fallback. |
| Paper trading initial ledger | `src/ai_fund_lab_v2/paper_trading/initial_ledger.py` | `RUNTIME_INPUT` / bootstrap | Creates ledger starting cash; not a continuing ceiling. |
| Backtest Phase7 modules | `src/ai_fund_lab_v2/capital_allocation_ai/phase7*.py` | `DEAD/LEGACY` | Older backtest code, not active Runtime v2 PC/PS authority for this run. |
| Tests / fixtures | `tests/**`, `scripts/audit_*` | `TEST_FIXTURE` | Not production defects. |
| Documentation / phase reports | `docs/**` | `DOCUMENTATION` | Historical context only. |

No search hit showed active production PC/PS/MCC clipping current equity to
initial cash for the inspected daily artifacts.

## Production Vs Test / Doc Classification

`1,000,000 JPY` is present as:

- `HISTORICAL_PROFILE`: initial cash / buying power for historical smoke reset.
- `RUNTIME_INPUT`: reset/bootstrap state before continuity begins.
- `TEST_FIXTURE`: unit tests, audit scripts, dry runs.
- `DOCUMENTATION`: runbooks and old phase reports.
- `DEAD/LEGACY`: older Phase7 and retired evaluation-capital surfaces.
- `PRODUCTION_AUTHORITY`: current capital authority exists, but it identifies
  the selected capital source as current total equity.

No `PRODUCTION_AUTHORITY` hit was found that makes initial cash a live
deployment ceiling after current state exists.

## Scaling Invariance Analysis

Read-only scaling sample:

| Equity band | Date | Equity | Cash | Cash ratio | PC NEW weight | Security notional | Authorized Cash notional | BUY notional |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ~1.0M | 2022-10-03 | 1,000,000 | 1,000,000 | 1.000 | 0.733506 | 736,714 | 3,286 | 504,470 |
| ~1.2M | 2023-02-28 | 1,200,150 | 274,380 | 0.229 | 0.266664 | 410,350 | 245,779 | 174,800 |
| ~1.5M | 2023-03-28 | 1,493,710 | 324,610 | 0.217 | 0.200373 | 319,630 | 307,630 | 267,500 |
| ~1.8M low cash | 2023-06-19 | 1,801,630 | 346,670 | 0.192 | 0.117648 | 576,170 | 142,275 | 49,900 |
| ~1.8M high cash | 2024-01-04 | 1,799,230 | 1,420,600 | 0.790 | 0.050930 | 34,101 | 1,428,749 | 188,800 |

The sample disproves the simplest scaling-defect pattern.  Deployable security
notional and authorized Cash notional are weight times current equity; they do
not remain fixed near `1,000,000`.  High Cash can exceed `1,000,000`, and
security notional can scale materially above early-run levels when PC weights
authorize it.

## Hard-Coded / Hidden Ceiling Audit

Audit checklist:

| Check | Result |
| --- | --- |
| hard-coded 1M ceiling | Not found in active PC/PS/MCC lineage. |
| config-derived initial capital ceiling | Not supported; config value exists but active artifacts mark current-equity authority. |
| min/max clipping current equity to initial capital | Not found. |
| reserve amount computed from initial cash | Not found for focus dates. |
| buying power capped at start capital | Not found after Current has cash / buying-power evidence. |
| position budget normalized by initial equity | Not supported; PS uses current `portfolio_total_equity`. |
| runtime profile value reused after equity growth | Not supported for focus dates. |
| historical-only capital cap | Bootstrap/reset only, not continuing PC/PS cap. |
| stale snapshot capital authority | Not found in inspected lineage. |
| legacy fallback using initial cash | Exists only as fallback when Current is unknown; not active in focus dates. |

`NO_INITIAL_CAPITAL_ANCHOR_DEFECT_FOUND`

## Redundant Conservatism Audit

G140 remains respected:

```text
REDUNDANT_MARKET_WEAKNESS_MULTIPLICATION = NO
RISK_PACING_ARCHITECTURALLY_NECESSARY = YES
```

For the healthy-BULL focus dates, Market Quality and Risk Pacing are not weak:
all five are `HEALTHY_EXPANSION` plus `NORMAL_DEPLOYMENT`.  The conservatism
therefore does not come from repeated market weakness multiplication.  It comes
later, in MCC / Cash frontier semantics:

- `MARGINAL_OPPORTUNITY_SET`
- `NO_VALID_COMPETITOR`
- `CASH_OPTIONALITY`
- residual Cash authorization

This is redundant conservatism only partially: multiple conservative concepts
align, but not by duplicating the same Market Quality weakness signal.

## Phase32-E Interaction

On the five focus dates:

```text
ADD competitors = 0
ADD_LOST_TO_NEW_BUY rows = 0
```

Across the 2024-01-10 to 2024-01-31 BULL sequence, NEW-to-Cash suppression is
visible on `2024-01-16`, `2024-01-17`, `2024-01-18`, `2024-01-19`,
`2024-01-22`, `2024-01-29`, and `2024-01-30`.  But the exact Phase32-E chain
`ADD loses to NEW -> NEW loses to Cash` was not observed in that January
sequence because ADD competitors were absent on the inspected focus dates.

Thus Phase32-E interaction is architecturally material but empirically partial
for Phase32-H's focus dates.

## Root-Cause Ranking

| Rank | Cause | Judgment | Evidence |
| ---: | --- | --- | --- |
| 1 | `PC_MCC_CASH_FRONTIER` | Primary | Cash wins or absorbs residual despite healthy BULL and NEW supply. |
| 2 | `NEW_ENTRY_QUALITY / MARGINAL_CLASS` | Material | `MARGINAL_OPPORTUNITY_SET` and `NO_VALID_COMPETITOR` dominate focus dates. |
| 3 | `NORMAL_CASH_OPTIONALITY` | Material/mixed | Cash remains valid even with BULL; BULL is not a full-investment command. |
| 4 | `RISK_PACING` | Low on focus dates, mixed in sequence | Focus dates are `NORMAL_DEPLOYMENT`; broader sequence includes cautious days. |
| 5 | `INITIAL_CAPITAL_ANCHOR` | Not supported | Active bases scale from current equity/cash. |
| 6 | `LOT / EXECUTABILITY` | Secondary | Present in some artifacts but not the main focus-date cause. |

## Defect Vs Limitation Classification

Classification: `LIMITATION`, not mandatory defect.

The system is behaving according to current contracts: Cash is first-class,
Risk Pacing does not directly set quantity, PC/MCC owns capital competition,
PS owns discrete quantity, and Runtime consumes the output.  The limitation is
observability/economic comparability: the artifacts do not yet present a single
calibrated ADD / NEW / Cash next-yen frontier that can prove whether healthy
BULL residual Cash is optimal or overconservative.

## Recommended Next Step

Create a shadow-only extraction/spec:

```text
capital_frontier_cash_new_add_bridge.v1
```

For each row, include:

- current equity, current cash, cash ratio, exposure, position count
- current capital authority source and denominator
- PC available incremental budget, target gross exposure, total target weight
- NEW candidate supply, NEW marginal class, requested/accepted NEW
- ADD competitor state and requested/accepted ADD
- Cash competitor semantic, authorized Cash, residual reason
- MCC winner, defeated competitors, cash-preferred deferrals
- Risk Pacing intent and Market Quality
- PS sizing base, authorized security notional, executable BUY notional
- Runtime BUY plan/fill linkage
- final outcome labels only for offline audit
- `future_information_used=false`, `shadow_only=true`,
  `not_action_authority=true`

## Final Judgments

```text
PHASE32_H_INITIAL_CAPITAL_ANCHOR_HYPOTHESIS = NOT_SUPPORTED

PHASE32_H_HARD_CODED_1M_PRODUCTION_CEILING = NO

PHASE32_H_INITIAL_CASH_REUSED_AS_DEPLOYMENT_BASE = NO

PHASE32_H_CURRENT_EQUITY_SCALES_CAPITAL_BASE_CORRECTLY = YES

PHASE32_H_HEALTHY_BULL_CASH_PREFERENCE_CAUSE = PC_MCC_CASH_FRONTIER + MARGINAL_NEW_CLASSIFICATION + NORMAL_CASH_OPTIONALITY

PHASE32_H_REDUNDANT_CONSERVATISM_MATERIAL = PARTIAL

PHASE32_H_ADD_LOSES_NEW_THEN_NEW_LOSES_CASH_PATTERN = PARTIAL

PHASE32_H_PC_MCC_CASH_BIAS_MATERIAL = YES

PHASE32_H_RISK_PACING_CONTRIBUTION = LOW

PHASE32_H_CAPITAL_BASE_SCALING_DEFECT = NO

PHASE32_H_MANDATORY_DEFECT = NO

PHASE32_H_PRODUCTION_REPAIR_JUSTIFIED = NO

PHASE32_H_IMPLEMENTATION_READY = NO

PHASE32_H_NEXT_STEP = Phase32-I shadow capital_frontier_cash_new_add_bridge.v1 extraction spec, with no production behavior change
```

## Files / Commands Inspected

Files and artifact families inspected:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/portfolio_policy.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/market_context.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/execution/fills.json`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `config/runtime_tests/historical_extended_smoke_10bd.json`
- `configs/runtime_v2/capital_deployment.json`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`

Commands used:

- `sed -n ... pasted-text.txt`
- `rg -n "initial_cash|initial_capital|..."`
- `rg -n "1000000|1_000_000|1e6|..."`
- read-only Python extraction over daily JSON artifacts
- `nl -ba ...`
