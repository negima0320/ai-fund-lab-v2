# Phase23 to Phase24 ChatGPT Handoff

## Current Status

Project:

```text
AI Fund Lab v2
```

Current phase status:

```text
Phase23 FORMALLY CLOSED WITH NON-BLOCKING GAPS
Phase24 READY WITH ENTRY GATE
```

Primary Closure Judgment:

```text
PHASE23_FORMALLY_CLOSED_WITH_NON_BLOCKING_GAPS
```

Phase24 Entry Judgment:

```text
PHASE24_PERFORMANCE_VALIDATION_READY_WITH_ENTRY_GATE
```

## Project Objective

AI Fund Lab v2 aims to build a safe, reproducible, auditable autonomous Japanese equity AI fund. The investment target is annual return +50%, but this is a target, not a guarantee.

Phase24 must evaluate and improve Strategy performance. It must not reinterpret Phase23 Runtime correctness as performance success.

## Permanent Rules

- Prevent regression first.
- Do not implement Historical-only logic to pass Historical tests.
- Production / Demo / Historical share the same Production Runtime / Strategy Contract.
- Do not add year, date, symbol, run_id, or profile-specific implementation.
- Do not use Runtime PnL, Paper Ledger, selected / bought results, Cash, Portfolio Value, Broker Snapshot, Test Result, Audit Result, or future price/return as learning inputs.
- Learning inputs are limited to approved J-Quants-derived data.
- Preserve PIT.
- Prohibit fail-open, silent fallback, latest fallback, zero fill, and forced PASS.
- Long Runtime tests are Operator-owned.
- Codex handles implementation, investigation, short tests, and evidence generation.
- ChatGPT handles phase management, Evidence Review, and task design.

## Current Architecture

The Strategy / Runtime authority chain is:

```text
J-Quants PIT Data
  -> Feature Layer
  -> Corporate Event Authority
  -> Market Context Engine
  -> Candidate AI
  -> Opportunity AI
  -> Portfolio Policy
  -> Position Management
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Pending / Approval
  -> Submit Guard
  -> Execution / Fill
  -> Ledger / Current
  -> Current Valuation
  -> Close / Strategy Shadow
```

Runtime does not recalculate Strategy decisions. Strategy Shadow is non-mutating and does not drive Production execution.

## Phase21 Design Intent

Phase21 froze these boundaries:

```text
Ranking上位 = BUYではない
Portfolio Policy ALLOWED = BUYではない
PM ADD = BUYではない
Runtime Planning feasible = Submit許可ではない
Strategy Shadow = Production executionではない
Operational completionとStrategy reviewは別軸
```

Phase23-BV accepted Phase21 design conformance with non-blocking gaps.

## Phase23 Final State

Accepted judgments:

```text
Phase21 Design Conformance = PASS_WITH_NON_BLOCKING_GAP
Phase23 Closure Blocker Count = 0
Production-common Contract = PASS
Historical PIT Contract = PASS_WITH_NON_BLOCKING_GAP
Phase23 Closure Ready = YES
Phase24 Performance Validation Ready = YES_WITH_ENTRY_GATE_CLOSE_REVALIDATION
```

## Verified Lifecycle

Verified through final 10BD and repair evidence:

```text
Historical As-of source resolution
Market Context
Portfolio Policy
Portfolio Construction
Position Sizing
BUY_NEW
Reference Price Authority
Runtime Planning
Strategy Planning Authority
Pending
Approval
Submit Policy
Submit Guard
Historical BUY Fill
Cash debit
Ledger append
Position creation
Position carry-forward
Current Position Membership
PM ADD
BUY_ADD Submit / Fill
SELL_EXIT
SELL Submit / Fill
Cash credit
Position close
Realized PnL
Current Valuation
10BD completion
Close arrival
```

## Final 10BD Runtime Evidence

Run:

```text
runtime-test-historical-smoke-20260730T211110605880Z
```

Completed business days:

```text
2022-07-01
2022-07-04
2022-07-05
2022-07-06
2022-07-07
2022-07-08
2022-07-11
2022-07-12
2022-07-13
2022-07-14
```

Trades:

```text
2022-07-08 BUY 94320 1100 @ 153.3
2022-07-11 BUY 23880 1400 @ 132.0
2022-07-11 BUY 94340 1100 @ 153.9
2022-07-12 BUY ADD 94320 100 @ 158.0
2022-07-13 BUY 66590 1000 @ 145.0
2022-07-14 SELL_EXIT 23880 1400 @ 113.0
```

Final state:

```text
cash = 474,680
market_value = 478,950
total_equity = 953,630
realized_pnl = -26,600
unrealized_pnl = -19,300
```

Open positions:

```text
94320 quantity 1200
94340 quantity 1100
66590 quantity 1000
```

Runtime correctness and accounting correctness are PASS. Strategy performance is negative and statistically insufficient.

## Known Gaps

Phase23 Closure blockers:

```text
0
```

Phase24 entry gate:

```text
BU post-repair Close classification should be revalidated by Operator on 1BD or same 10BD.
```

Non-blocking carryover:

- SELL_REDUCE partial sell runtime not verified.
- Multiple ADD / REDUCE, re-entry, partial fill, rejected order, cash scarcity, simultaneous BUY / SELL, long-held position, month/year boundary, alternate periods, and Production Broker execution remain future coverage.
- Early zero deployment / NO_ORDER requires performance attribution.
- `sell_pipeline` handles PM ADD; legacy naming overlap, not current blocker.
- 5 obsolete runner fixtures lack Historical Evaluation Authority precondition.
- Historical earnings calendar PIT has documented current-snapshot-only exception.

## Phase24 Entry Gate

Recommended first gate:

```text
Phase24-A0 BU Post-repair Close Runtime Revalidation
```

Purpose:

```text
Verify BU's two-axis Close contract with Operator-run 1BD or same 10BD:
operational completion = PASS
trading/accounting = PASS
strategy_review_status is preserved independently
non-mutating shadow review does not overwrite operational status
```

This is acceptance evidence, not a Runtime repair task.

## Performance Investigation Backlog

Priority backlog:

- P24-GAP-01 Zero Deployment / NO_ORDER
- P24-GAP-02 Cash Utilization
- P24-GAP-03 Entry Quality
- P24-GAP-04 PM ADD Quality
- P24-GAP-05 SELL / Profit Capture
- P24-GAP-06 Drawdown / Loss Attribution
- P24-GAP-07 Strategy Profile / Risk Appetite

## Recommended Phase24 Roadmap

1. Phase24-A0 BU Post-repair Close Runtime Revalidation
2. Phase24-A Performance Evidence and Evaluation Contract Review
3. Phase24-B Entry Gate Close Revalidation
4. Phase24-C Alternate-period 10BD Matrix
5. Phase24-D 20BD / 60BD Runtime Stability
6. Phase24-E 200BD Baseline
7. Phase24-F Benchmark and Regime Attribution
8. Phase24-G Zero Deployment / NO_ORDER Analysis
9. Phase24-H Entry Quality Analysis
10. Phase24-I Position Sizing Analysis
11. Phase24-J PM Analysis
12. Phase24-K Loss and Drawdown Attribution
13. Phase24-L Improvement Hypothesis Design
14. Phase24-M Controlled Strategy Change
15. Phase24-N Regression and Runtime Revalidation

## Roles

Operator:

```text
10BD / 20BD / 60BD / 200BD / 1年 / 3年 Runtime execution
```

Codex:

```text
commands, evidence checks, short tests, analysis, implementation repair
```

ChatGPT:

```text
Phase Gate, Task design, Evidence Review, improvement priority management
```

## Must-read Documents

Priority 1:

- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/01_requirements/phase_roadmap.md`

Priority 2:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Priority 3:

- `docs/phase_reports/phase21_d_strategy_architecture_v1_design.md`
- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/phase_reports/phase21_final_summary_and_phase22_chatgpt_handoff.md`
- `docs/02_architecture/strategy_architecture_v1.md`

Priority 4:

- `docs/phase_reports/phase23_bm_historical_asof_strategy_source_authority_binding_repair.md`
- `docs/phase_reports/phase23_bo_runtime_planning_executable_plan_price_authority_propagation_repair.md`
- `docs/phase_reports/phase23_bq_current_position_membership_temporal_authority_carry_forward_repair.md`
- `docs/phase_reports/phase23_bs_pm_add_pending_submit_policy_authority_binding_repair.md`
- `docs/phase_reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit.md`
- `docs/phase_reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair.md`

## Do Not Do

- Do not treat the negative 10BD return as a Phase23 Runtime failure.
- Do not treat Phase23 Runtime correctness as Strategy performance PASS.
- Do not guarantee annual return +50%.
- Do not optimize to one period.
- Do not feed Runtime result or future outcome into training.
- Do not begin Phase24 by changing thresholds.
- Do not run long Runtime from Codex.
- Do not enable Broker Write or Runtime Switch without a separate human-approved gate.

## Recommended First Task

```text
Phase24-A0 BU Post-repair Close Runtime Revalidation
```

Then:

```text
Phase24-A Performance Evidence and Evaluation Contract Review
```
