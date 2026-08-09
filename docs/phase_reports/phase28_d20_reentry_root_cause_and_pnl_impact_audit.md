# Phase28-D20: Re-entry Root Cause and PnL Impact Audit

## Primary Judgment

```text
PHASE28_D20_REENTRY_LOSS_CONCENTRATION_CONFIRMED_D21_READY
```

D21 Entry Decision:

```text
READY
```

D20 was read-only. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

Target run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

## Re-entry Definition

Primary definition fixed for D20:

```text
previous campaign for the same symbol CLOSED
↓
subsequent BUY_NEW opens a new campaign
```

Excluded:

```text
REDUCE followed by ADD
partial SELL followed by BUY_ADD
pending cancellation
no-fill
same-campaign ADD
```

The reconstructed count is exactly:

```text
93
```

This matches D17. Derivation:

```text
112 final position campaigns - 19 first symbol campaigns = 93 re-entry campaigns
```

## Delay Distribution

| Delay | Count |
|---|---:|
| same day | 0 |
| 1 business day | 68 |
| 2 business days | 8 |
| 3 business days | 2 |
| 4-5 business days | 5 |
| 6-10 business days | 6 |
| 11-20 business days | 2 |
| >20 business days | 2 |

Threshold counts:

| Threshold | Count |
|---|---:|
| <=1BD | 68 |
| <=3BD | 78 |
| <=5BD | 83 |
| <=10BD | 89 |

The dominant pattern is immediate same-symbol re-entry on the next business day.

## Re-entry PnL

| Metric | Value |
|---|---:|
| Re-entry campaigns | 93 |
| Winners | 44 |
| Losers | 37 |
| Flat | 12 |
| Win rate, excluding flat | 54.3210% |
| Gross profit | 232,090 |
| Gross loss | -337,890 |
| Net PnL | -105,800 |
| Profit factor | 0.686880 |
| Average winner | 5,274.77 |
| Average loser | -9,132.16 |
| Median PnL | 0 |
| Largest winner | 48,000 |
| Largest loser | -100,000 |

Contribution:

| Segment | PnL |
|---|---:|
| Total run PnL | +58,200 |
| Re-entry PnL | -105,800 |
| Non-re-entry PnL | +164,000 |

Campaign-level authority is sufficient here because the final run has no open positions.

## First Half / Second Half

Split policy from D17:

```text
first 50 completed business days vs last 50
mid_business_date = 2023-06-14
```

By close date:

| Half | Count | Re-entry PnL |
|---|---:|---:|
| First half | 42 | +7,830 |
| Second half | 51 | -113,630 |

By re-entry date:

| Half | Count | Re-entry PnL |
|---|---:|---:|
| First half | 46 | +18,540 |
| Second half | 47 | -124,340 |

D17 second-half return was `-33,220`. Re-entry close-date PnL in the second half was `-113,630`, so re-entry loss concentration more than explains the second-half deterioration before offsetting non-re-entry gains.

## Repeat Loss

| Pattern | Count | Re-entry PnL |
|---|---:|---:|
| loss -> re-entry -> loss | 19 | -208,340 |
| loss -> re-entry -> profit | 12 | +47,620 |
| loss -> re-entry -> flat | 3 | 0 |
| profit -> re-entry -> loss | 15 | -105,850 |
| profit -> re-entry -> profit | 28 | +158,870 |
| profit -> re-entry -> flat | 3 | 0 |
| flat -> re-entry -> loss | 3 | -23,700 |
| flat -> re-entry -> profit | 4 | +25,600 |
| flat -> re-entry -> flat | 6 | 0 |

Key repeat-loss finding:

```text
loss -> <=5BD re-entry -> loss count = 16
loss -> <=5BD re-entry -> loss PnL = -181,240
```

This is the strongest D21 repair driver.

## Momentum Validity

Diagnostic classification from entry/exit opportunity rank and available score evidence:

| Classification | Count |
|---|---:|
| MOMENTUM_REACCELERATION_CONFIRMED | 33 |
| NO_MEANINGFUL_SIGNAL_CHANGE | 36 |
| WEAK_REENTRY_SIGNAL | 24 |

This is not a decision-time authority. PM-specific momentum score at exit is not consistently materialized for every pair, so D20 uses Runtime Planning opportunity/rank/quality evidence as diagnostic evidence only.

## EXIT / Re-entry Contradiction

| Classification | Count |
|---|---:|
| VALID_MOMENTUM_RECOVERY | 33 |
| VALID_STATE_CHANGE | 14 |
| CONTRADICTORY_EXIT_REENTRY | 31 |
| INSUFFICIENT_EVIDENCE | 15 |

Contradictory EXIT/Re-entry cases are concentrated in short-delay re-entry and loss sequences.

## Producer Trace

Direct re-entry producer:

```text
Candidate
↓
Opportunity
↓
Portfolio Construction
↓
Position Sizing
↓
Runtime Planning BUY_NEW
```

For the 93 re-entry BUY_NEW rows, the active chain did not consume:

```text
previous campaign history
last exit date
last exit reason
cooldown state
recent-loss state
```

Root cause:

```text
BUY_NEW chain treats same-symbol closed campaigns as ordinary new candidates once Opportunity / BUY Quality / Portfolio Construction / Position Sizing / Runtime Planning pass.
```

## Existing Guard Audit

Existing status:

```text
NO_ACTIVE_RUNTIME_REENTRY_GUARD
```

Architecture and non-active code evidence:

- `docs/02_architecture/strategy_architecture_v1.md` defines re-entry cooldown as Portfolio Construction conflict policy.
- `src/ai_fund_lab_v2/strategy/position_management.py` contains Phase22-K cooldown/re-entry helper logic.
- D17 runtime BUY_NEW artifacts did not expose or consume last-exit, last-exit-reason, cooldown, or recent-loss authority fields.

Therefore a re-entry guard exists as architecture/deferred design, but not as active formal runtime BUY_NEW eligibility in this run.

## BUY_ADD Zero Relation

Judgment:

```text
PARTIAL_RELATION_SUPPORTED
```

Evidence:

```text
previous close-date PM ADD count = 22
previous close-date PM ADD + Strategy PM UNRESOLVED count = 22
net PnL of those subsequent re-entry campaigns = +30,710
```

Interpretation:

Some previous campaigns had PM ADD intent on the close date, but D17/D18 Strategy PM did not propagate ADD. These cases support an indirect/partial relation between BUY_ADD zero and later BUY_NEW re-entry. It does not prove that every re-entry would have been BUY_ADD.

The larger Re-entry loss concentration is not explained by BUY_ADD zero alone. It requires a dedicated re-entry eligibility repair.

## D21 Decision

Repair required:

```text
true
```

Primary Recommendation:

```text
Option B: state-change gated re-entry
```

Required mechanism:

```text
Option D: campaign-aware re-entry eligibility context
```

Minimal D21 repair scope:

```text
Campaign-aware state-change gated re-entry eligibility in Strategy / Portfolio Construction conflict policy only.
```

D21 must not change:

```text
Cash reserve
Target exposure
BUY_ADD allocation
ADD thresholds
Exit thresholds
Position count
BUY Quality thresholds
```

After D21, D22 must re-audit cash utilization because suppressing re-entry can reduce BUY count and increase cash.

## Deliverables

```text
docs/phase_reports/phase28_d20_reentry_root_cause_and_pnl_impact_audit.md
reports/phase_reports/phase28_d20_reentry_root_cause_and_pnl_impact_audit.json
reports/phase28_d20_reentry_root_cause_and_pnl_impact_audit/
```

## Final Judgment

```text
Primary Judgment: PHASE28_D20_REENTRY_LOSS_CONCENTRATION_CONFIRMED_D21_READY
D21 Entry Decision: READY
Re-entry definition: same-symbol CLOSED campaign followed by BUY_NEW new campaign
Re-entry count: 93
Re-entry direct root cause: BUY_NEW path lacks campaign-aware last-exit/recent-loss/state-change gate
Existing guard status: NO_ACTIVE_RUNTIME_REENTRY_GUARD
BUY_ADD zero relation: PARTIAL_RELATION_SUPPORTED
Minimal Repair Scope: campaign-aware state-change gated re-entry eligibility only
Primary Recommendation: Option B via Option D mechanism
Next Phase: Phase28-D21
```
