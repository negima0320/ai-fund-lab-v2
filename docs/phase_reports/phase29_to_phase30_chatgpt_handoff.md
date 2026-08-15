# Phase29 to Phase30 ChatGPT Handoff

## Start Here

Read in this order:

1. `docs/phase_reports/phase29_to_phase30_chatgpt_handoff.md`
2. `docs/phase_reports/phase29_final_summary_and_phase30_handoff.md`
3. `docs/phase_reports/phase30_a_phase29_final_state_clean_baseline_reset_and_research_roadmap.md`
4. `docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md`
5. `docs/01_requirements/phase_roadmap.md`

Latest task:

`Phase29-L21T-BN`

Primary Judgment:

`PHASE29_CLOSED_PHASE30_CLEAN_PERFORMANCE_IMPROVEMENT_HANDOFF_READY`

Phase30 migration is user-approved. Phase30 tuning has not started.

## Current Phase30 First Task

Recommended first task:

`Phase30-A - Post-BL 20BD Clean Baseline Integrity / Close Review / Performance Attribution Audit`

Target run:

`runtime-test-historical-extended-smoke-20260815T030154161245Z`

Known user-provided final evidence:

- 20 business days processed: `2022-08-10` to `2022-09-07`
- Initial Equity: `1,000,000`
- Final Equity: `972,510`
- Return: `-2.75%`
- Final Cash: `431,770`
- Final Exposure: `55.60%`
- Final Positions: `7`
- Final status: `REVIEW_REQUIRED`
- Close returned `REVIEW_REQUIRED`

Do not treat the negative return as a Phase30 blocker. The first Phase30 task
is to understand the clean measurement and close reason, then attribute the
loss.

## Do Not Use As Tuning Authority

Old long run:

`runtime-test-historical-extended-smoke-20260814T131647480030Z`

Status:

`CAPITAL_AUTHORITY_CONTAMINATED`

BF findings:

- earliest contamination: `2022-08-10`
- contaminated symbols: `104`
- contaminated days: `299 / 300`
- false Equity reached capital authority
- sizing equity contaminated
- position weights contaminated

Do not use its Equity curve, final return, MDD, cash/exposure attribution,
regime attribution, winner giveback, BUY_NEW/ADD/SELL performance, campaign
performance, or deployed-capital quality as formal Phase30 evidence. It is
runtime forensic / defect-discovery evidence only.

## Closed Contracts To Preserve

- BUY / SELL independence.
- PM ADD -> Runtime BUY_ADD.
- Incremental Investment semantics.
- Lot-aware allocation.
- Strategy cap / Safety cap separation.
- Residual capital recycling without forced deployment.
- Semantic REENTRY.
- Re-entry cooldown and recovery hurdle.
- Low-price / tick / liquidity protections.
- REDUCE discrete-lot semantics.
- Expected Edge relative semantics.
- Runtime semantic metadata propagation.
- Multi-Horizon Momentum Trajectory.
- `BUY_WAIT` means temporary BUY_NEW ineligibility, no Pending, no Human Review,
  no Runtime halt, next-day reevaluation, SELL independence, BUY_ADD/REENTRY
  unaffected.
- Execution `NO_SUBMISSION_REQUIRED` / `AUTHORIZED_NO_ORDER` continuity.
- Valuation fail-closed.
- Price / quantity adjustment-basis contract.
- Basis metadata persistence.

## Phase29 Retrospective In One Page

Phase29 started as a performance-improvement continuation from Phase28 ADD
work. It repaired capital deployment, lot-aware conversion, residual
reallocation, low-price / REENTRY risk, Expected Edge score semantics,
multi-horizon momentum trajectory, no-order execution continuity, and the
valuation/basis measurement foundation.

The largest discovery was that performance measurement itself was unsafe.
Adjusted analytical prices and raw/economic prices were being consumed without
enough provenance and basis matching. That contaminated old long-run equity,
cash, exposure, sizing, and position-weight authority. Phase29 fixed this by
making valuation fail closed, requiring price/quantity basis compatibility, and
persisting basis metadata across runtime-owned Current transitions.

Recurring engineering failure mode:

```text
producer fixed
but adapter / consumer / persisted state / next-day lifecycle not fully proven
```

Phase30 should use end-to-end authority-path validation for every new semantic
field or measurement.

## Phase30 Roadmap

0. Clean Performance Measurement Foundation.
1. Clean Long-Horizon Baseline.
2. Deployed-Capital Quality.
3. Entry Quality / Multi-Horizon Momentum Trajectory.
4. Winner Continuation / Profit Retention.
5. Market Regime / Regime Transition.
6. SELL / PM Market Context Authority.
7. Exit Outcome Separability.
8. ADD Quality.
9. Recovery Re-entry Quality.
10. Formal Expected Edge Calibration.

## Permanent Rules

- Production / Demo / Historical common contracts only.
- Historical-only Strategy prohibited.
- Production fail-closed weakening prohibited.
- Future data prohibited.
- Paper Ledger / PnL / selected/bought/test result prohibited as runtime
  learning input.
- Long Historical runs are user-operated.
- No fixed BUY count.
- No fixed position count.
- No forced exposure.
- Cash is valid when no opportunity is valid.
- Re-entry blanket ban prohibited.
- Safety cannot be weakened for Strategy convenience.

## First Phase30-A Checklist

Read-only only:

- Identify `REVIEW_REQUIRED` close reason.
- Reconcile 20BD valuation, Equity, Daily PnL, cash, exposure, positions.
- Verify price/quantity basis integrity and basis persistence.
- Check abnormal valuation jumps.
- Attribute total `-27,490` JPY loss.
- Attribute `2022-08-24` `-43,400` loss and `2022-09-07` `+24,040` recovery.
- Summarize BUY_NEW, BUY_WAIT, ADD, REDUCE, EXIT, SELL behavior.
- Decide whether the 20BD candidate is clean enough for user-operated 4-year
  fresh validation.

Do not change Strategy or thresholds before this audit.
