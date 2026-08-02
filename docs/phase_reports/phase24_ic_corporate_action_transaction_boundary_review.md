# Phase24-IC Corporate Action Guard Transaction Boundary Design Review

## Primary Judgment

`PHASE24_IC_CONTRACT_GAP_CONFIRMED_PARTIAL_SUBMIT_OCCURRED_CORPORATE_ACTION_GUARD_EXPECTED_FAIL_CLOSED`

## Runtime Evidence

Run:

```text
runtime-test-historical-extended-smoke-20260801T103359617234Z
```

Requested run id omitted the trailing `Z`; repository evidence exists under the `Z`-suffixed run directory.

Business date:

```text
2022-10-28
```

Run-level result:

```text
fresh_run_summary.status = HALT
fresh_run_summary.exit_code = 30
run_state.halted_at.business_date = 2022-10-28
run_state.halted_at.job = submit
run_state.halted_at.exit_code = 20
```

Submit job result:

```text
daily submit final_state = REVIEW_REQUIRED
submit pipeline status = REVIEW_REQUIRED
reason = submit completed with rejected/unknown/blocked items
pending_item_count = 2
accepted_count = 1
blocked_count = 1
submitted_count = 1
halt_required = false
```

## IC-1 Corporate Action Type

Evidence source:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T103359617234Z/daily/2022-10-28/market_refresh/inputs/historical_asof/2022-10-28/raw/jquants/equities_bars_daily/data.parquet
```

Relevant raw OHLCV row:

| Date | Code | AdjFactor | O | H | L | C | AdjO | AdjH | AdjL | AdjC | Vo | AdjVo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-10-28 | 76920 | 0.3333333333333333 | 1614.0 | 2007.0 | 1562.0 | 1760.0 | 134.5 | 167.3 | 130.2 | 146.7 | 3305000.0 | 39660000.0 |

Guard implementation:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py
_corporate_action_status(...)
returns IMPACT_DETECTED when target-date target-symbol AdjFactor != 1.0
```

Judgment:

```text
Corporate Action Type = ADJFACTOR_ADJUSTMENT_EVENT
Exact legal event type = NOT_DETERMINABLE_FROM_ACCEPTED_RUNTIME_EVIDENCE
```

The available Runtime evidence proves an adjustment-factor impact. It does not prove whether the underlying corporate action was a stock split, reverse split, merger, TOB, or other legal event. Inferring a stock split from `AdjFactor=1/3` is intentionally not used as the final judgment because the task prohibits inference.

## IC-2 Current Pipeline Behavior

Pending contained:

| Symbol | Side | Pending Item | Estimated Amount | Approval |
|---|---|---|---:|---|
| 93180 | BUY | `strategy-ed0c35cbfe8a2397f032` | 153200.0 | APPROVED |
| 76920 | SELL | `opi-sell-reduce-pm-76920-001` | 66950.0 | APPROVED |

Submit results:

| Symbol | Side | Submit Guard | Adapter / Broker Classification | Final Item Result |
|---|---|---|---|---|
| 93180 | BUY | PASS | `HISTORICAL_FILL_ACCEPTED` | ACCEPTED |
| 76920 | SELL | PASS | `corporate_action_status=IMPACT_DETECTED`, reason `corporate action guard failed`, status `HALT` | NOT_SUBMITTED / BLOCKED |

Current code behavior:

```text
SubmitPipeline iterates approved_item_ids item by item.
If one item is accepted, a ledger order record is written for that item.
If a later item is blocked, Pending state becomes REVIEW_REQUIRED.
Top-level submit status becomes REVIEW_REQUIRED when submitted_count > 0 and blocked_count > 0.
```

This is current implementation behavior, not a fully frozen Production transaction contract.

## IC-3 Option Recommendation

Reviewed options:

| Option | Judgment |
|---|---|
| Option A: all preflight, all PASS, then all Submit | Recommended target for CA-sensitive submit transaction boundary |
| Option B: BUY independent / SELL independent | Not sufficient alone; would allow partial execution without lifecycle contract |
| Option C: formal Partial Submit contract | Correct long-term if partial execution is intentionally supported, but currently deferred |
| Option D: other | Option A now, Option C as separate future design if wanted |

Recommendation:

```text
Option A for current Production Runtime safety.
Option C only after a dedicated Partial Submit lifecycle design/implementation task.
```

Rationale:

- Corporate Action Guard is a hard fail-closed authority.
- Current accepted HS contract says `Partial Submit = fail-closed review state, not automatic continuation`.
- Existing code already produced a partial outcome, but Production Contract does not yet define resume, pending item terminalization, ledger reconciliation, idempotency, or dependency rules for that outcome.
- Therefore the safest Production boundary is batch-level preflight of all approved items before any item crosses the broker/execution boundary.

## IC-4 BUY / SELL Dependency

Evidence:

```text
planning_submit_feasibility.status = PASS
cash = 179100.0
buying_power = 179100.0
current_exposure = 673840.0
remaining_exposure = 176160.0
BUY 93180 estimated_amount = 153200.0
BUY item status = PASS
SELL 76920 reason = sell_exposure_reducing_submit_feasibility_not_blocked_by_buy_max_exposure
```

Judgment:

```text
BUY単独でも成立
```

The BUY did not require the SELL to create cash or exposure room. `153200.0 <= cash 179100.0` and `673840.0 + 153200.0 = 827040.0 <= max_exposure 850000.0`.

## IC-5 Corporate Action Guard Scope

Current Corporate Action Guard is target-symbol scoped:

```text
Only the submitted target symbol is checked against target-date raw OHLCV AdjFactor.
Unrelated symbols do not trigger the target item.
```

For the affected item, the guard must remain hard fail-closed. It should stop the SELL item from crossing the execution boundary. Whether it stops the whole Runtime depends on the accepted transaction contract:

- Current long-run validation profile stops on submit REVIEW_REQUIRED, so run-level HALT is consistent with the validation profile.
- Production Runtime currently lacks an accepted formal Partial Submit lifecycle for continuing after a mixed accepted/blocked outcome.
- Therefore whole-run review/HALT after this partial outcome is consistent as fail-closed behavior, even though the direct CA impact is symbol/item scoped.

## Current Design / Architecture Consistency

Consistent:

- Corporate Action Guard detected target-symbol `AdjFactor != 1.0`.
- SELL item was not submitted.
- Pending was not consumed as a full success.
- Long-run validation stopped rather than silently continuing.
- BUY/SELL guard separation and SELL quantity guard passed independently.

Contract gap:

- SubmitPipeline currently submits item-by-item and can accept one item before a later item fails.
- Phase24-HS froze Partial Submit as fail-closed review state and deferred formal Partial Submit support.
- Production transaction semantics for batch atomicity vs formal partial lifecycle are not yet explicit for Corporate Action Guard after one accepted item.

## Direct Root Cause

```text
Target-symbol Corporate Action Guard detected raw J-Quants AdjFactor=0.3333333333333333 for 76920 on 2022-10-28.
SubmitPipeline item iteration had already accepted BUY 93180 before SELL 76920 reached adapter Corporate Action Guard.
```

## Implementation Required

```text
YES, but not in Phase24-IC.
```

Needed next task should be design/implementation, not a silent patch:

```text
Production Submit Transaction Boundary Contract and Implementation
```

Minimum scope:

- all-approved-item adapter preflight before any submit, or
- formal Partial Submit lifecycle with item terminal states, pending preservation, resume semantics, ledger reconciliation, duplicate prevention, and reporting.

## Prohibited Changes Check

No code, Contract, Architecture, Runtime rerun, Historical-only handling, or Corporate Action Guard relaxation was performed in this task.

## Recommended Next Task

```text
Phase24-ID Production Submit Transaction Boundary Contract
```

Decision to freeze:

```text
Option A batch preflight atomic submit
```

or

```text
Option C formal partial submit lifecycle
```

Until that is frozen, treat the observed mixed accepted/blocked outcome as a Contract Gap requiring review, not as Production-ready automatic continuation.
