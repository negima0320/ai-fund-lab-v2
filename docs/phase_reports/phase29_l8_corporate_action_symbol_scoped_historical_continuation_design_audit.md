# Phase29-L8 Corporate Action Symbol-Scoped Historical Continuation Design Audit

## Status

COMPLETE

READ_ONLY DESIGN AUDIT

NO PRODUCTION CODE CHANGE

NO CONFIG CHANGE

NO SCHEMA CHANGE

NO RUNTIME / PENDING / LEDGER MUTATION

NO HISTORICAL / FRESH-RUN / RESUME EXECUTION

## Primary Judgment

PHASE29_L8_SYMBOL_SCOPED_HISTORICAL_CORPORATE_ACTION_QUARANTINE_DESIGN_READY

## Direct HALT Cause

Historical run:

```text
run_id = runtime-test-historical-smoke-20260810T210535954893Z
completed_business_days = 53
halt = 2022-10-28:submit
runtime_cli_exit_code = 20
runtime_cli_final_state = REVIEW_REQUIRED
runtime_test_status = HALT
root reason = corporate_action_event_not_resolved
```

The submit job had three approved items. Two BUY items passed and were submitted
in Historical simulation. The impacted item was:

```text
symbol = 76920
side = SELL
quantity = 700
submit_item_status = REVIEW_REQUIRED
guard_decision = BLOCKED
submit_status = NOT_SUBMITTED
corporate_action_event_status = IMPACT_DETECTED
corporate_action_event_type = UNKNOWN_ADJFACTOR_IMPACT
corporate_action_adjustment_factor = 0.3333333333333333
corporate_action_adjustment_authority_status = REVIEW_REQUIRED
```

Corporate Action detection was correct. The current problem is that a
symbol-scoped unresolved event becomes submit `REVIEW_REQUIRED`, the Runtime CLI
returns a nonzero exit code, and Runtime Test converts that nonzero submit job
into run-level `HALT`.

## Contract Trace

Detection producer:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py
HistoricalSubmitAdapter._corporate_action_evidence
```

It reads PIT raw OHLCV for the target date and target symbol. `AdjFactor != 1`
is an impact signal only:

```text
corporate_action_status = IMPACT_DETECTED
corporate_action_type = UNKNOWN_ADJFACTOR_IMPACT
corporate_action_type_authority = not_available_from_adjfactor_only
```

Adjustment authority producer:

```text
src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py
materialize_corporate_action_adjustment_authority
```

Submit Guard consumer:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
_submit_guard_item_evidence
evaluate_corporate_action_adjustment_authority
```

Run-level HALT producer:

```text
scripts/runtime_test.py
fresh/run loop and resume loop
```

Runtime Test already has a narrow scoped continuation exception for BUY-only
review/block statuses. There is no equivalent Corporate Action symbol-scoped
continuation classifier today.

## Production Safety

Production / Demo fail-closed must be preserved.

Unresolved Corporate Action for an impacted symbol must remain:

```text
TRADE_BLOCKED
REVIEW_REQUIRED
NOT_SUBMITTED
operator-visible
```

Forbidden:

```text
auto submit
silent skip
warning-only downgrade
AdjFactor-only split inference
automatic normalization without authority
Production run continuation that hides the event
```

The Phase24-IL architecture is explicit: `AdjFactor != 1` is not sufficient to
pass. The event type, effective date, source hash, no-future-data status,
ledger/current/pending/submit quantity basis, and already-applied status must be
proved by Runtime-owned authority.

## 76920 Classification

The 2022-10-28 `76920` event cannot be formally classified as a stock split
from existing authority.

```text
AdjFactor = 0.3333333333333333
implied ratio = 3, but inference is not authority
event type authority = not_available_from_adjfactor_only
formal split authority = NOT AVAILABLE
authoritative ratio = NOT AVAILABLE
```

Therefore the safe current classification is Category B:

```text
IMPACT_DETECTED_BUT_UNRESOLVED
```

Historical should quarantine the symbol; Production should remain
`REVIEW_REQUIRED`.

## Historical State Gap

Existing Historical Broker supports accepted submission evidence, cash effect,
position quantity projection for normal BUY/SELL fills, and isolated no-broker
write behavior.

It does not currently provide formal Corporate Action mechanics for:

```text
quantity adjustment
average acquisition price adjustment
valuation continuity
open pending order adjustment
realized/unrealized PnL continuity
lot-size consistency
split effective-date semantics
already-applied idempotency across replay/resume
```

For a 1-to-3 split example, 700 shares may need to become 2100 shares, but that
must be a Historical Broker / Ledger state transition, not Strategy logic and
not AdjFactor-only inference.

## Recommended Design

Implement a Historical-only two-axis continuation contract:

```text
HISTORICAL_SYMBOL_SCOPED_CORPORATE_ACTION_QUARANTINE
```

Semantics:

```text
symbol status = REVIEW_REQUIRED / QUARANTINED
impacted symbol order = NOT_SUBMITTED
run continuation eligibility = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
Production applicability = NEVER
```

This is not:

```text
REVIEW_REQUIRED -> PASS
```

It is:

```text
item/symbol remains REVIEW_REQUIRED
Runtime Test may continue only because the blocked item is isolated,
historical-only, non-submitted, broker-write=false, and evidence-retained
```

The future implementation should add:

- Submit evidence fields for symbol quarantine eligibility.
- Runtime Test classifier for historical corporate-action scoped continuation.
- Persistent quarantine evidence so the symbol remains blocked on later days.
- Historical Broker state-transition support only for Category A confirmed
  split/reverse-split events with PIT-safe event type, effective date, ratio,
  ledger/current/pending quantity reconciliation, and already-applied proof.
- Portfolio/performance limitation evidence when unresolved symbols remain in
  the portfolio without confirmed adjustment mechanics.

Strategy, PM, BUY, SELL, ADD, Position Sizing, and Production Submit Guard
semantics must not change.

## Regression Design

Production:

- unresolved split impact -> `REVIEW_REQUIRED`, `NOT_SUBMITTED`,
  operator-visible
- confirmed split -> no Strategy auto-submit without adjustment authority
- unsupported corporate event -> fail-closed
- BUY impacted symbol -> fail-closed unless authority PASS
- SELL impacted symbol -> fail-closed unless authority PASS
- existing position / no existing position variants

Historical:

- unresolved one-symbol event -> symbol `QUARANTINED`, run continuation allowed
  only for Historical replay
- other BUY and SELL symbols continue
- unresolved symbol remains blocked until resolved
- no future leakage
- no silent PASS
- evidence preserved
- portfolio valuation integrity preserved or explicitly limited
- no cross-symbol contamination

Preserve:

```text
D61, D69, Phase29-E, Phase29-G, J1, J2, L4-A, L4-B, L5, L7,
BUY/SELL independence, Compound Capital, No-leverage, ADD semantics,
Pending lifecycle, Sell quantity authority
```

## Read-Only Validation

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
```

```text
21 passed in 1.94s
```

## Resume / Fresh Decision

This L8 audit made no production source change, so L8 itself does not create a
new fresh-run requirement. A future implementation of the quarantine
continuation contract will change Runtime Test / Historical behavior after a
HALT, so that future implementation should use a fresh run.

```text
L8 audit resume allowed = NO ACTION / NOT APPLICABLE
After future implementation resume allowed = NO
After future implementation fresh-run required = YES
```

## Evidence

```text
reports/phase29_l8_corporate_action_symbol_scoped_historical_continuation_design_audit/
```
