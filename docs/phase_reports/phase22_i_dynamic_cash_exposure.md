# Phase22-I Dynamic Cash / Exposure

## Primary Judgment

```text
PHASE22_I_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Dynamic Cash / Exposure foundation was implemented as a production/demo/historical common, read-only Strategy artifact producer. It owns only minimum/target/maximum cash ratio and gross exposure ratio fields. It remains `DRAFT / NOT_ELIGIBLE` and is not connected to Runtime consumers.

Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.
Phase22-J entry ready: `YES_READ_ONLY_FOUNDATION`.

## Implemented Scope

- Added explicit Strategy config: `configs/strategy/dynamic_cash_exposure.json`
- Added artifact schema: `schemas/strategy/dynamic_cash_exposure.schema.json`
- Added producer/validator: `src/ai_fund_lab_v2/strategy/dynamic_cash_exposure.py`
- Added targeted tests: `tests/strategy/test_phase22_i_dynamic_cash_exposure.py`
- Added evidence package: `reports/phase22_i_dynamic_cash_exposure/phase22_i_evidence_20260727/`

## Runtime Preservation

Current Runtime active values were inventoried and preserved:

```text
configs/runtime_v2/capital_deployment.json
target_investment_ratio = 0.85
cash_buffer = 0.05
max_exposure = 850000
```

Phase22-I did not change Morning Planning, Submit, Pending, Runtime policy consumption, or active capital deployment behavior.

## Safety Limits

Independent Safety cash/exposure hard limits were added to `configs/safety/portfolio_limits.json`:

```text
minimum_cash_ratio = 0.10
maximum_gross_exposure_ratio = 0.90
authority = Safety hard limit
scope = production/demo/historical
override_allowed = false
```

These limits do not reuse `target_investment_ratio=0.85`, `max_exposure=850000`, or fixed `20/80` as Safety authority.

## Strategy Policy

The Strategy baseline is:

```text
target_cash_ratio = 0.20
target_gross_exposure_ratio = 0.80
```

The implementation is not fixed 20/80. Regime, breadth, volatility, portfolio risk posture, opportunity capacity, and uncertainty rules move targets dynamically:

- risk-on: lower cash, higher exposure
- balanced: baseline behavior
- defensive: higher cash, lower exposure
- risk-off: materially higher cash, materially lower exposure
- high uncertainty: higher cash, lower exposure

The Strategy artifact removes the fixed JPY `850000` cap from Strategy authority. Runtime still keeps the active legacy cap until a later Runtime switch phase.

## Input Discipline

Allowed inputs are Market Context, Portfolio Policy, Dynamic Position Count, candidate/opportunity availability, current cash/exposure/current portfolio value summaries, pending reservation summaries, Safety hard limits, explicit Strategy config, and PIT J-Quants metrics when supplied by upstream artifacts.

Forbidden inputs were not used: backtest return/PnL, historical PnL, future return, paper ledger PnL, current PnL, selected/bought result, test result, or order outcome.

## Validation

Evidence files cover current inventory, authority separation, Safety limits, Market Context availability, policy rationale, config/schema checks, ratio hierarchy, regime relationships, position count alignment, status propagation, PIT/date discipline, hash lineage, bootstrap behavior, shadow comparison, Runtime preservation, regression, and scope preservation.

Validation commands:

```text
python3 -m pytest tests/strategy/test_phase22_i_dynamic_cash_exposure.py
python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase22i python3 -m compileall src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2/safety tests/strategy
```

Results:

```text
Phase22-I targeted: 6 passed
Selected Phase22/Runtime regression: 119 passed
compileall: PASS
Long tests executed: NO
```
