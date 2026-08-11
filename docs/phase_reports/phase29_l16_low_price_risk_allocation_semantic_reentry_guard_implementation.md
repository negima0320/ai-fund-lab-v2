# Phase29-L16 - Low-Price Risk Allocation / Semantic REENTRY Guard Implementation

## 0. Task ID

Phase29-L16

## 1. Primary Judgment

```text
PHASE29_L16_LOW_PRICE_RISK_ALLOCATION_AND_SEMANTIC_REENTRY_GUARD_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_HISTORICAL_VALIDATION_READY
```

L16 implements the L13-L15 approved Production-common Strategy repair for
low-price / single-tick risk allocation, liquidity capacity capping, semantic
REENTRY, a 3 completed-business-day REENTRY cooldown, and the REENTRY recovery
hurdle. It does not implement a price-only hard exclusion, 93180-specific logic,
Historical-only Strategy logic, or PnL/backtest-result Strategy inputs.

## 2. Implementation Summary

Changed:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
src/ai_fund_lab_v2/candidate_ai/feature_builder.py
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
src/ai_fund_lab_v2/paper_trading/unified_daily_runner.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/test_feature_builder.py
```

Portfolio Construction remains the economic allocation authority. The new L16
authority is applied after existing BUY_NEW / BUY_ADD target-weight resolution
and before incremental budget reconciliation, so capital released by caps stays
inside normal PC competition and can flow to ADD, other BUY_NEW opportunities,
other eligible Strategy opportunities, or Cash.

Position Sizing only carries the new evidence fields forward and continues to
materialize target weights into quantities. SELL / REDUCE / EXIT quantity
authority remains unchanged.

Candidate feature generation now emits `rolling_median_traded_value_20` only
when PIT traded-value input is present. No missing traded-value replacement or
fixed evaluation capital was introduced.

## 3. Authority Details

Tick risk authority:

```text
single_tick_pct = minimum_tick / reference_price
NORMAL   < 0.01
WATCH    >= 0.01 and < 0.02; cap 0.12
ELEVATED >= 0.02 and < 0.05; cap 0.10
SEVERE   >= 0.05 and < 0.10; cap 0.08
EXTREME  >= 0.10; cap 0.05
```

Liquidity capacity authority:

```text
capacity_ratio = proposed_target_notional / rolling_median_traded_value_20
liquidity_capacity_cap_weight =
  rolling_median_traded_value_20 * 0.01 / current_authoritative_portfolio_equity
```

The equity input is from `current_portfolio_summary` (`portfolio_total_equity` /
`portfolio_value`), not a fixed 1,000,000 JPY assumption.

Semantic REENTRY:

```text
current_position == false
AND current_quantity is zero/absent
AND prior same-symbol EXIT business date is explicitly present
AND prior EXIT date is before the current business date
```

ADD, BUY_ADD, continuing positions, REDUCE, and EXIT are not classified as
REENTRY.

REENTRY cooldown:

```text
3 completed business days
reason = reentry_minimum_cooldown_not_satisfied
```

REENTRY recovery hurdle:

```text
rank <= 10
expected_edge >= 0.10
BQ action in {REDUCED_ALLOCATION_ONLY, FULL_ALLOCATION_ELIGIBLE}
Corporate Action resolved / no unresolved blocking event
capacity_ratio <= 0.03
trend_close_over_ma_20d >= 1.0 OR price_momentum_return_20d >= 0
```

Missing mandatory REENTRY recovery evidence fails closed as
`REVIEW_REQUIRED` / `FAIL_CLOSED` evidence. A passing REENTRY still receives
normal tick/liquidity caps.

## 4. Evidence / Observability

PC and PS expose the L16 evidence fields, including:

```text
semantic_buy_type
prior_exit_business_date
business_days_since_exit
reentry_cooldown_threshold_bd
reentry_cooldown_status
reentry_recovery_status
reentry_recovery_reason
reentry_rank
reentry_expected_edge
reentry_buy_quality_action
reentry_trend_close_over_ma_20d
reentry_price_momentum_return_20d
reentry_corporate_action_status
single_tick_pct
price_tick_risk_tier
rolling_median_traded_value_20
capacity_ratio
liquidity_capacity_status
normal_target_weight
price_tick_cap_weight
liquidity_capacity_cap_weight
final_risk_adjusted_target_weight
allocation_cap_reason
```

## 5. Regression Mapping

Short regression coverage:

```text
Normal-price BUY_NEW unchanged: PASS
Strong normal BUY_NEW unchanged: PASS
Low-price liquid BUY_NEW remains eligible: PASS
WATCH/ELEVATED/SEVERE/EXTREME caps: PASS
Liquidity cap tightening: PASS
Liquidity-only blanket rejection not introduced: PASS
Semantic REENTRY detection: PASS
First BUY_NEW not REENTRY: PASS
Existing ADD not REENTRY: PASS
REENTRY <3BD blocked: PASS
REENTRY >=3BD recovery PASS allowed and capped: PASS
REENTRY rank fail blocked: PASS
Missing PIT liquidity evidence fail closed: PASS
Strong canonical ADD preserved with positive increment: PASS
SELL / REDUCE / EXIT unaffected: PASS
L7 SELL quantity contract preserved: PASS
Opportunity Cost / PC / PS preserved: PASS
Dynamic Capital current-equity cap: PASS
Cash Exposure Authority preserved: PASS
Production/Demo/Historical common Strategy path: PASS by no mode-specific branch
No Historical-only branch / no 93180-specific branch / no future/PnL/backtest input: PASS by code search and test scope
```

Focused regression commands executed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k phase29_l16 tests/test_feature_builder.py -k phase29_l16
```

```text
8 passed, 63 deselected in 0.34s
```

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
```

```text
153 passed in 3.53s
```

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_aa_corporate_event.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_i_dynamic_cash_exposure.py tests/test_feature_builder.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py
```

```text
53 passed in 2.40s
```

Combined rerun:

```bash
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py tests/strategy/test_phase22_aa_corporate_event.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_i_dynamic_cash_exposure.py tests/test_feature_builder.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py
```

```text
206 passed in 4.33s
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/candidate_ai/feature_builder.py src/ai_fund_lab_v2/paper_trading/feature_refresh.py src/ai_fund_lab_v2/paper_trading/unified_daily_runner.py
```

```text
PASS
```

Code search:

```bash
rg -n "93180|2022-|1_000_000|1000000|historical-only|backtest" src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/candidate_ai/feature_builder.py src/ai_fund_lab_v2/paper_trading/feature_refresh.py src/ai_fund_lab_v2/paper_trading/unified_daily_runner.py
```

```text
No Strategy 93180 / 2022 / fixed-1M authority hits. One pre-existing report flag in unified_daily_runner.py.
```

## 6. Long Historical Policy

No long Historical validation was executed by Codex.

Because Strategy behavior changed:

```text
Fresh-run Required: YES
Resume old run allowed: NO
```

Do not resume a pre-L16 halted run as post-L16 performance evidence.

Recommended operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-08-10 --date-to 2026-08-09 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

## 7. Mandatory Final Report

Primary Judgment:

```text
PHASE29_L16_LOW_PRICE_RISK_ALLOCATION_AND_SEMANTIC_REENTRY_GUARD_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_HISTORICAL_VALIDATION_READY
```

Production-common Strategy implementation:
YES

Historical-only Strategy introduced:
NO

Price-only hard exclusion introduced:
NO

Single-tick risk authority implemented:
YES

Risk tiers implemented:
NORMAL / WATCH / ELEVATED / SEVERE / EXTREME

WATCH cap:
0.12

ELEVATED cap:
0.10

SEVERE cap:
0.08

EXTREME cap:
0.05

Liquidity capacity authority implemented:
YES

rolling_median_traded_value_20 authority:
YES; PIT feature when traded-value input exists, PC fail-closed/review evidence when required and missing

capacity_ratio authority:
YES

liquidity notional cap:
rolling_median_traded_value_20 * 0.01

liquidity-only hard rejection introduced:
NO

Semantic REENTRY implemented:
YES

REENTRY source authority:
Explicit prior same-symbol EXIT business date already present in Strategy input; not inferred from Opportunity appearance or PnL

Cooldown implemented:
YES

Cooldown threshold:
3 completed business days

Recovery hurdle implemented:
YES

Rank threshold:
rank <= 10

Expected-edge threshold:
expected_edge >= 0.10

BQ requirement:
REDUCED_ALLOCATION_ONLY or FULL_ALLOCATION_ELIGIBLE

Momentum/trend requirement:
trend_close_over_ma_20d >= 1.0 OR price_momentum_return_20d >= 0

Corporate Action requirement:
resolved / no unresolved blocking event

Liquidity requirement:
capacity_ratio <= 0.03

Normal BUY_NEW preserved:
YES

Low-price BUY_NEW still conditionally possible:
YES

ADD semantics weakened:
NO

Canonical ADD preserved:
YES

BUY_ADD preserved:
YES

SELL semantics changed:
NO

REDUCE semantics changed:
NO

EXIT semantics changed:
NO

L7 quantity contract preserved:
YES

Opportunity Cost preserved:
YES

Dynamic Capital preserved:
YES

Cash Exposure Authority preserved:
YES

Capital reallocation preserved:
YES

Current-equity compounding preserved:
YES

Legacy fixed 1M authority reintroduced:
NO

Corporate Action authority preserved:
YES

Production unresolved CA fail-closed preserved:
YES

Demo unresolved CA fail-closed preserved:
YES

Future leakage:
NO

PnL used as Strategy input:
NO

Backtest result used as Strategy input:
NO

93180-specific logic:
NO

Production code changed:
YES

Strategy code changed:
YES

Config changed:
NO

Existing schema changed:
NO

Runtime mutated:
NO

Pending mutated:
NO

Ledger mutated:
NO

Historical executed:
NO

Fresh-run executed:
NO

Resume executed:
NO

Focused regression result:
PASS; 206 focused tests passed plus py_compile PASS

Fresh-run required:
YES

Resume old run allowed:
NO

Recommended operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-08-10 --date-to 2026-08-09 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

Recommended next task:
Operator-run fresh Historical validation, then read-only Phase29-L17 effect attribution and structural correctness audit.
