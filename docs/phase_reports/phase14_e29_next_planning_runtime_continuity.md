# Phase14-E29 Next Planning Reset & Runtime Continuity Fix

## Summary

Phase14-E29 fixed the Next Planning continuity gap found in E27 after the E25 runtime-owned Current projection and E28 Planning Price Source fix.

Final judgment: `PHASE14E29_RUNTIME_CONTINUITY_COMPLETE`

Implemented:

1. Morning Planning now uses Runtime-owned Current SoT cash / buying_power as the planning budget.
2. Demo capability default evaluation capital no longer resets new BUY budget every morning once Current cash exists.
3. Current exposure and current position symbols are read from `.runtime/persistent_ledger/state.json`.
4. Existing held symbols are excluded from new BUY candidates before OrderPlan / Pending generation.
5. Morning manifest now records continuity fields:
   - `available_cash`
   - `planning_budget`
   - `current_exposure`
   - `current_position_symbols`
   - `existing_position_excluded_count`
6. Runtime v2 report / public report remains sourced from fixed Current SoT.

No additional Submit was executed. No Production order, Notification actual send, launchd change, Phase9 Runtime, Phase9 writer, Current initialization, or Demo Broker 20M cash copy was performed.

## Current Continuity Contract

Runtime v2 Next Planning must start from canonical Current SoT:

- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/*.jsonl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/current_state.json`

It must not use:

- `.runtime/demo/...` as Current
- phase artifacts as Current
- Demo Broker reset cash as Runtime capital
- report / public report / audit as Submit or Current source

## Planning Budget Rule

Before E29, Morning Planning could use `BrokerCapability.default_evaluation_capital=1,000,000` as the operative BUY budget even when Current already held positions.

After E29:

| Field | Rule |
| --- | --- |
| `evaluation_capital` | Runtime operation capital reference, still 1,000,000 in demo |
| `available_cash` | `min(Current.cash, Current.buying_power)` when both are known |
| `planning_budget` | equals `available_cash` for new BUY sizing |
| `current_exposure` | sum of positive Current position market values |
| `per_order_budget` | `min(planning_budget / max_orders, 100,000)` |

If `available_cash` is missing or non-positive, Morning creates no executable Pending and records:

`NO_SIGNAL:available_cash_missing_or_zero`

## Existing Position Rule

Morning Planning now derives current held symbols from Current SoT positions with positive quantity.

Candidate symbols are compared against Current holdings using a Planning-local comparison key:

- `72030` compares to `7203`
- `65010` compares to `6501`
- already 4-character symbols remain unchanged

This comparison is only for Current continuity and duplicate BUY avoidance. Broker request issue-code normalization remains isolated to the Submit / Broker Adapter boundary.

## Validation Scenario

A new E29 regression test creates a temporary fixed Current state:

| Current Field | Value |
| --- | ---: |
| cash | 700,000 |
| buying_power | 700,000 |
| market_value | 300,000 |
| total_equity | 1,000,000 |
| position | `7203` x 100 |

Feature candidates include:

- `72030` existing holding
- `65010`
- `67580`
- `99840`

Expected result:

- `72030` is excluded from new Pending.
- Planning uses `700,000` as `planning_budget`.
- Total new order estimated amount is below `1,000,000`.
- Price source metadata is preserved from E28.
- Public report still displays Current cash / position state.

## Code Changes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`

Key implementation details:

- Added `_available_cash(...)`.
- Added `_current_exposure(...)`.
- Added `_current_position_symbols(...)`.
- Added candidate exclusion for existing Current positions.
- Preserved runtime_v2 Planning import boundaries; Planning does not import broker API / Submit / Phase9 modules.

## Flow Matrix Update

| Flow | E29 Result |
| --- | --- |
| Current SoT -> Morning Planning | CONNECTED |
| Current positions -> Candidate exclusion | CONNECTED |
| Current cash / buying_power -> Capital Allocation | CONNECTED |
| Runtime evaluation capital -> Planning budget | NO LONGER USED AS DAILY RESET |
| Feature price source -> Order sizing | CONNECTED from E28 |
| Planning -> Pending | CONNECTED |
| Current SoT -> Runtime/Public Report | CONNECTED |
| Next Planning -> Submit | Submit not executed in E29 |

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| Production order | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime | Not used |
| Phase9 writer | Not used |
| Current initialization | Not executed |
| Demo Broker 20M cash copy | Not executed |

## Verification

Targeted test:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e29_pycache python3 -m pytest tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
```

Result:

```text
5 passed
```

Runtime v2 full tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e29_pycache python3 -m pytest tests/runtime_v2
```

Result:

```text
329 passed
```

Note:

`PYTHONPYCACHEPREFIX` was used because default macOS pycache can attempt to write outside the workspace sandbox.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Runtime-owned CurrentだけでNext Planningが成立する | PASS |
| 現在保有を認識する | PASS |
| Cashを正しく使う | PASS |
| 100万円フル再投資しない | PASS |
| Report一致 | PASS |
| Current一致 | PASS |
| Flow Matrix更新 | PASS |
| 追加Submitなし | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |
| launchd変更なし | PASS |

## Final Judgment

`PHASE14E29_RUNTIME_CONTINUITY_COMPLETE`
