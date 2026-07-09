# Phase14-E53 BUY/SELL Submit Guard Regression Audit

## Summary

Phase14-E53 audited the regression that allowed Runtime v2 Submit to keep a fixed `max_order_amount=100000` default while Planning / Capital Allocation moved toward real price and 100万円 evaluation-capital sizing.

Final judgment: **PHASE14E53_SUBMIT_GUARD_REGRESSION_IDENTIFIED**

This phase was audit-only.

No code was changed. No Submit, Broker Write, Production order, Notification real send, launchd change, or Current direct edit was performed.

## Finding

The regular Runtime v2 submit path currently has:

```text
run_submit_pipeline(..., max_order_amount=100000.0)
```

and the submit preflight applies it to both BUY and SELL:

```text
if item.estimated_amount > max_order_amount:
    BLOCKED: estimated amount exceeds max order amount
```

This means:

- BUY orders above 100,000円 are blocked even if Capital Allocation intentionally sizes them above 100,000円.
- SELL liquidation orders above 100,000円 are also blocked even if they reduce Runtime-owned exposure.
- The regular CLI has no `--max-order-amount` argument, so operation cannot adjust the guard from the normal entry.

## 1. When Was `max_order_amount=100000` Introduced?

Exact commit attribution is unavailable because `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` and `src/ai_fund_lab_v2/runtime_v2/submit/guards.py` are not tracked in the current `HEAD`.

Evidence:

```text
git blame -L 88,105 -- src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
fatal: no such path ... in HEAD
```

Filesystem timestamps:

| File | Timestamp |
|---|---|
| `src/ai_fund_lab_v2/runtime_v2/submit/guards.py` | 2026-07-08 14:52 |
| `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py` | 2026-07-09 07:10 |
| `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` | 2026-07-09 10:02 |
| `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py` | 2026-07-09 10:01 |

Design lineage:

- Phase14-D3 introduced a side-agnostic guard phrase: `estimated amount does not exceed max order amount`.
- Phase14-E17 connected the regular Submit pipeline.
- Current `run_submit_pipeline(...)` default is `100000.0`.

Audit conclusion:

```text
The side-agnostic max order amount guard was introduced during the Runtime v2 pure submit path work.
The specific regular-pipeline default of 100,000円 is present in the current Phase14 submit pipeline, but cannot be commit-blamed because the file is untracked in HEAD.
```

## 2. Designed BUY Order Amount

The design documents do not support a fixed 100,000円 per-order limit as the final Runtime / Capital Allocation contract.

### Phase7 / Capital Allocation Direction

`docs/phase_reports/phase12ar_approval_max_notional_design_verification.md` summarizes the Capital Allocation design:

- initial assets: 1,000,000円
- max positions: 5
- max position weight: 20%
- equal-weight guide: 1,000,000 * 0.20 = 200,000円 per position
- cash buffer: 5%

Thus, a natural per-position BUY size is around:

```text
200,000円
```

not 100,000円.

### Phase11 MAX_EXPOSURE

The same audit records:

```text
max_allowed_exposure = base_equity * max_total_exposure_ratio
max_total_exposure_ratio = 0.85
```

For a 1,000,000円 evaluation basis:

```text
total exposure cap = 850,000円
```

### Phase14-E15 Morning Pipeline

E15 connected Morning Planning using:

```text
Runtime評価資金100万円を基準にCapital allocationを作る
```

The first connected Pending used five 100,000円 BUYs, but this was a connection milestone, not a final allocation ceiling.

### Phase14-E28 Price Source Fix

E28 removed fake fallback price sizing and made real price / 100-share lot sizing mandatory.

Its sample real-price sizing produced BUY amounts such as:

```text
66,900
98,000
71,400
85,300
92,700
```

Those happened to fit under 100,000円, but E28 did not define 100,000円 as a permanent cap.

Audit conclusion:

```text
The designed BUY order amount should be derived from Capital Allocation, buying power, exposure, price, and lot size.
Fixed 100,000円 is not the final BUY order amount contract.
```

## 3. Capital Allocation Output vs Submit Guard Contract

Current flow:

```text
Planning / Capital Allocation -> Pending.estimated_amount -> Submit max_order_amount guard
```

Contract mismatch:

| Layer | Current / Designed Meaning |
|---|---|
| Capital Allocation | Decides intended order amount based on equity, exposure, cash, ranking, price, and lot size |
| Pending | Carries executable intent and estimated amount |
| Submit Guard | Should verify operational safety without silently replacing Capital Allocation policy |
| Current implementation | Blocks any amount above 100,000円 regardless of Capital Allocation intent |

This creates a hidden cap after Planning.

Risk:

- Planning may correctly generate a 180,000円 or 200,000円 BUY.
- Approval may approve it.
- Submit will still block it.
- Operator sees a Submit failure rather than an earlier Planning / Approval policy decision.

For SELL:

- Planning may correctly generate liquidation of Runtime-owned position value 300,000円 to 500,000円.
- Current quantity and available quantity may be safe.
- Submit still blocks because the notional is above a BUY-sized cap.

Audit conclusion:

```text
Capital Allocation and Submit Guard are not contract-aligned.
```

## 4. BUY and SELL Same Notional Guard: Design Basis

Evidence for same guard:

- Phase14-D3 lists max order amount as a generic Runtime v2 Submit guard.
- Current `run_submit_preflight(...)` is side-agnostic for notional cap.

Evidence against settled same-guard design:

- Phase14-B places `max order amount guard` under BUY checks.
- Phase14-B / D14 describe SELL as position / available quantity driven.
- Phase11 max exposure guard is exposure-increasing BUY oriented; SELL exposure-reduction is not the same risk.
- Phase14-D23 leaves max order amount / position / cash / buying power / kill switch / halt conditions as Production readiness review items.

Audit conclusion:

```text
There is implementation evidence for BUY/SELL sharing the same notional guard.
There is not enough design evidence that SELL liquidation should use the same 100,000円 cap as BUY.
```

## 5. Why Regression Checks Missed This

The existing tests checked component behavior, but not cross-layer budget contract consistency.

### E17 Submit Pipeline Tests

`tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`

The main submit-all test used Pending items that fit the default cap:

```text
estimated_amount = 100,000
```

It verified:

- all approved Pending items submitted
- 9000-series Demo block
- ledger order records
- CLI stage connection

It did not verify:

- BUY > 100,000 from Capital Allocation
- CLI behavior when Planning produces 200,000 per-position target
- whether 100,000 was intended as a cap or just fixture data

### E19 Submit Normalization Tests

`tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py`

The normalization tests focus on issue code conversion and response metadata. The approved Pending fixture reused the E17 small order pattern.

It did not verify amount/capital allocation alignment.

### E28 Price Source Tests

E28 fixed price source and missing-price behavior. The sample selected orders happened to be below 100,000円.

It did not include a fixture where real price and 100-share lot produced a valid Capital Allocation amount above 100,000円.

### E32 SELL Component Tests

`tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

The SELL component path used:

```text
6522 SELL 100 at 102円 = 10,200円
```

This was far below 100,000円.

It validated:

- SELL source is Current position
- SELL quantity overrun blocks
- fake adapter submit/execution/current/report path

It did not validate:

- real Runtime-owned SELL liquidation amount above 100,000円
- full CLI path for SELL submit
- max_order_amount interaction with SELL cleanup

### D14 / D15 Single SELL Tests

D14/D15 used a higher max amount in the test harness:

```text
max_order_amount = 500,000
```

This allowed `7203 SELL 100` with estimated amount around 294,100円 to pass.

However:

- it was not the regular `run_daily_operation.py --job submit` path.
- it did not catch the regular pipeline default of 100,000円.

## 6. Regression Test Gaps

Missing tests:

1. BUY Capital Allocation amount above 100,000円 should either:
   - be accepted if within configured BUY policy, or
   - be blocked earlier with an explicit Planning/Approval policy reason.

2. SELL Runtime-owned liquidation above 100,000円 should be covered by a side-specific contract:
   - pass under SELL liquidation policy, or
   - become REVIEW_REQUIRED with an operator-visible reason, or
   - split/reduce quantity by a defined policy.

3. Regular CLI submit path should be tested, not only direct `run_submit_pipeline(...)` with small fixtures.

4. Submit guard should expose active policy:
   - max_buy_order_amount
   - max_sell_order_amount or liquidation threshold
   - source of configuration
   - side-specific decision

5. Tests should assert that Capital Allocation output and Submit guard are contract-aligned.

## 7. Recommended Regression Tests

Add tests in a later fix phase:

### Test A: BUY Over 100,000 But Within Capital Allocation Contract

Fixture:

- Current cash: 1,000,000
- Capital Allocation target: 200,000
- Pending BUY estimated_amount: 180,000 or 200,000

Expected:

- If configured BUY max allows 200,000, Submit preflight PASS.
- If configured BUY max is 100,000, Planning/Approval must mark it BLOCKED/REVIEW_REQUIRED before Submit.

### Test B: SELL Runtime-owned Position Above 100,000

Fixture:

- Current position market_value: 300,000
- Pending SELL quantity <= Current quantity
- Broker available quantity >= SELL quantity

Expected depends on selected contract:

- PASS if liquidation threshold allows it.
- REVIEW_REQUIRED if manual review is required.
- BLOCKED only if explicitly configured as same-cap policy.

### Test C: SELL Broker-only Position Exclusion

Fixture:

- Broker evidence includes `6501` / `6502` / `9984`.
- Current SoT does not contain those symbols.

Expected:

- SELL Planning and Submit never target those broker-only positions.

### Test D: CLI Path Regression

Run:

```text
run_daily_operation --job sell_planning
run_daily_operation --job submit
```

Expected:

- The same amount policy is applied as direct submit pipeline tests.
- Manifest records active notional guard policy.

### Test E: Guard Policy Manifest

Expected manifest fields:

- guard_policy_version
- max_buy_order_amount
- max_sell_order_amount
- side
- estimated_amount
- guard_decision
- guard_reason

## 8. Classification

| Item | Classification |
|---|---|
| `max_order_amount=100000` default | Regression / hidden fixed cap |
| BUY/SELL shared notional guard | Contract gap |
| E51 SELL BLOCK | Expected under current implementation |
| Capital Allocation vs Submit alignment | GAP |
| Existing tests | Insufficient cross-layer regression coverage |
| Broker / Tachibana cause | No |
| Production readiness | Not ready until contract fixed |

## Final Judgment

**PHASE14E53_SUBMIT_GUARD_REGRESSION_IDENTIFIED**

