# Phase22-J Position Sizing

## Primary Judgment

```text
PHASE22_J_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Position Sizing foundation was implemented as a production/demo/historical common, read-only Strategy artifact producer. It decides symbol-level target weight and target notional intent only. It does not decide share quantity, lot rounding, order price, Pending, Submit, Approval, Execution, Fill, Ledger, or Current mutation.

Phase22-K entry ready: `YES_READ_ONLY_FOUNDATION`.
Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

Reviewed and reconciled the Phase21 design freeze, Strategy Architecture v1, Runtime Architecture v2, Artifact Acceptance Contract, Capital Deployment Design, Portfolio Policy / PM / Market Context / Corporate Event designs, Phase21-I/J gate and retirement reports, and Phase22-C through Phase22-I implementation reports and code.

## Existing Sizing Inventory

Evidence: `reports/phase22_j_position_sizing/phase22_j_evidence_20260727/existing_sizing_inventory.json`

Current executable sizing remains in existing Runtime paths:

- Morning BUY: `runtime_v2/planning/morning_pipeline.py`
- ADD: `runtime_v2/planning/add_consumer.py`
- REDUCE / EXIT quantity: `runtime_v2/planning/sell_pipeline.py`
- Order plan quantity rounding: `runtime_v2/planning/planner.py`

Phase22-J does not modify those paths.

## Authority Separation

Position Sizing target weight / target notional intent is Strategy authority. Runtime executable quantity, 100-share lot rounding, minimum order handling, Pending, Submit, and broker request remain downstream Runtime / Broker authority.

The current `max_position_weight=0.20` is classified as legacy active Runtime Capital Deployment policy, not Safety hard limit.

## Safety Concentration Contract

Added independent Safety concentration hard limit:

```text
configs/safety/portfolio_limits.json#concentration.maximum_position_weight = 0.25
authority_owner = Safety Layer
override_allowed = false
scope = production / demo / historical
```

Strategy sizing cap is separate:

```text
configs/strategy/position_sizing.json
strategy_maximum_position_weight = 0.18
```

The implementation blocks implicit reuse of legacy `0.20` as Safety concentration authority.

## Selected Sizing Method

Selected method:

```text
capped_quality_volatility_hybrid
```

Stages:

1. Base allocation from `target_gross_exposure_ratio / target_position_count`
2. Opportunity quality multiplier
3. Single-name volatility inverse multiplier
4. PM / membership adjustment
5. Strategy and Safety concentration cap
6. Portfolio total normalization
7. Minimum meaningful notional validation
8. Residual cash preservation

No PnL, backtest return, historical run result, future price, future return, selected/bought result, test result, or audit result is used.

## Minimum Meaningful Notional

Initial contract:

```text
max(50,000 JPY, reference_price * 100 shares * 1.02)
```

This validates whether a target notional is practically meaningful under a 100-share unit assumption. It does not produce an executable quantity.

## Schema / Failure Contract

Implemented:

- `schemas/strategy/position_sizing.schema.json`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

The validator enforces `DRAFT`, `NOT_ELIGIBLE`, source lineage, PIT dates, weight hierarchy, `sum(target_weights) <= target_gross_exposure_ratio`, target weight <= Safety cap, no quantity fields, no lot fields, no runtime switch, and no production consumer.

Failure behavior:

- upstream `REVIEW_REQUIRED` -> `REVIEW_REQUIRED`
- Dynamic Position Count unresolved -> `REVIEW_REQUIRED`
- Dynamic Cash / Exposure unresolved -> `REVIEW_REQUIRED`
- Safety concentration unresolved -> `REVIEW_REQUIRED`
- config missing -> `REVIEW_REQUIRED`
- date/hash/future leakage/invalid weight -> `BLOCK`
- missing quality or volatility -> fail-closed review/member withheld
- minimum notional unmet -> withheld/review-required

Bootstrap does not use equal weight fallback, fixed 100,000 JPY fallback, previous-day copy, legacy 20% copy, or quantity-zero fallback.

## Runtime Preservation

Runtime behavior remains unchanged:

```text
max_positions = 5
target_investment_ratio = 0.85
max_exposure = 850000
max_position_weight = 0.20
```

Morning Planning allocation, ADD allocation, Sell quantity, affordability, quantity calculation, lot rounding, Pending, Submit, Approval, Execution, Ledger, and Current were not connected to the new artifact.

## Tests

Executed short tests only:

```text
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py
python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase22j python3 -m compileall src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2/safety tests/strategy tests/runtime_v2/test_phase15h_capital_deployment_policy.py
jq empty configs/strategy/position_sizing.json schemas/strategy/position_sizing.schema.json configs/safety/portfolio_limits.json schemas/safety/portfolio_limits.schema.json
```

Results:

```text
Phase22-J targeted: 7 passed
Selected Phase22/Runtime regression: 126 passed
compileall: PASS
JSON validation: PASS
Long tests executed: NO
```

## Gaps And Next Gate

Blocking gaps: none for the read-only foundation.

Non-blocking gaps: upstream Phase22 artifacts remain `REVIEW_REQUIRED / NOT_ELIGIBLE`, and the broader Market Context volatility open decisions remain unresolved upstream.

Next gate: Phase22-K Regime / Event-aware HOLD ADD REDUCE EXIT.
