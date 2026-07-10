# Phase15-Y Non-Trading-Day Demo Acceptance Override

Date: 2026-07-10

## Objective

Phase15-Y implements an explicit manual Demo Acceptance override that allows Runtime Review evidence collection on non-trading days only in Demo mode.

This phase preserves the Phase15-X Runtime Reality Rule:

```text
Runtime is designed against Production Reality.
Demo differences are Broker Environment / Broker Capability / Broker Evidence.
No demo-only Runtime, phase-only Runtime, or Runtime bypass is created.
```

## Implemented Option

```text
--allow-non-trading-day-demo
```

The option is accepted only through the Runtime v2 regular CLI:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

It is not added to launchd / plist / autonomous operation.

## Behavior Contract

| Case | Result | Evidence |
|---|---|---|
| `--mode production --allow-non-trading-day-demo` | `BLOCKED` | `reason=non_trading_day_demo_override_forbidden_in_production` |
| `--mode demo`, non-trading day, no override | `REVIEW_REQUIRED` | `reason=non_trading_day` |
| `--mode demo`, non-trading day, override | Continue as Demo Acceptance only | `non_trading_day_demo_override=true`, `production_equivalent=false`, `acceptance_scope=demo_acceptance_only` |
| trading day with override | Normal trading-day behavior | `non_trading_day_demo_override=false`, `override_reason=trading_day_override_not_applicable` |

## Evidence Propagation

Runtime Manifest now emits:

```text
trading_day
business_day
market_open
non_trading_day_demo_override
override_source
override_reason
production_equivalent
acceptance_scope
```

Runtime Report now includes:

```text
Non-Trading-Day Demo Override
production_equivalent
acceptance_scope
```

Notification payload now includes:

```text
non_trading_day_demo_override
production_equivalent
acceptance_scope
```

## Static Audit

| Check | Result |
|---|---|
| CLI option exists | PASS |
| Production override is blocked | PASS |
| Demo default remains stopped on non-trading day | PASS |
| Demo explicit override marks `production_equivalent=false` | PASS |
| Report propagation | PASS |
| Notification payload propagation | PASS |
| launchd/plist contains override | PASS: not present |
| Demo-only Runtime created | PASS: not created |
| Runtime bypass created | PASS: not created |

## Regression Tests

Added:

```text
tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py
```

Coverage:

- Production override forbidden
- Demo non-trading day without override stops
- Demo non-trading day with override allowed only as Demo Acceptance
- Trading day with override does not alter normal behavior
- Manifest / Report / Notification propagation
- launchd does not include `--allow-non-trading-day-demo`

Executed:

```text
python3 -m pytest -q tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py
```

Result:

```text
6 passed
```

## Acceptance Notes

Executions using this override are classified as:

```text
DEMO_ACCEPTANCE_OVERRIDE
```

They are not:

- Full Runtime PASS
- Production Equivalent
- Production readiness evidence
- permission to run Production on a non-trading day

## Prohibited Actions Confirmation

This phase did not perform:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current edit
- Runtime bypass
- Demo-only Runtime creation
- Phase-only Runtime creation
- deletion of non-trading-day checks
- Production non-trading-day execution permission

## Final Judgment

```text
PHASE15Y_NON_TRADING_DAY_DEMO_ACCEPTANCE_OVERRIDE_COMPLETE
```
