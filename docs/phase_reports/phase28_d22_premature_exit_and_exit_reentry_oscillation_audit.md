# Phase28-D22: Premature EXIT and EXIT-Reentry Oscillation Audit

## Primary Judgment

```text
PHASE28_D22_EXIT_REENTRY_OSCILLATION_CONFIRMED
```

D22 was read-only. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

Target run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

## Audit Scope

D22 audited all:

```text
93 / 93 re-entry pairs
```

Primary pair:

```text
previous campaign
↓
EXIT / full close
↓
N business days
↓
BUY_NEW re-entry
```

The 68 next-business-day re-entry pairs were重点監査対象.

## Core Finding

D20/D21 correctly found a re-entry defect, but D22 confirms this is not only a re-entry-side issue.

Observed lifecycle shape:

```text
EXIT
↓
<=1BD BUY_NEW: 68
<=3BD BUY_NEW: 78
<=5BD BUY_NEW: 83
```

And after re-entry:

```text
BUY_NEW -> <=1BD EXIT: 77
BUY_NEW -> <=3BD EXIT: 82
BUY_NEW -> <=5BD EXIT: 88
```

Full cycle:

```text
EXIT -> BUY_NEW -> EXIT = 93
```

Repeated oscillation symbols:

```text
9
```

This is an EXIT/Re-entry oscillation pattern.

## Responsibility Classification

| Classification | Count |
|---|---:|
| BOTH_BOUNDARIES_TOO_SENSITIVE | 37 |
| EXIT_PREMATURE_REENTRY_REASONABLE | 33 |
| EXIT_VALID_REENTRY_TOO_AGGRESSIVE | 7 |
| VALID_EXIT_VALID_REENTRY | 2 |
| INSUFFICIENT_EVIDENCE | 14 |

Derived key counts:

```text
EXIT valid count: 9
Premature EXIT count: 70
Both-boundary oscillation count: 37
Re-entry-aggressive-only count: 7
Valid lifecycle count: 2
Insufficient evidence count: 14
```

## 1BD Re-entry Audit

1BD pairs:

```text
68
```

| EXIT audit status | Count | Following re-entry PnL |
|---|---:|---:|
| EXIT_LIKELY_PREMATURE | 61 | +57,460 |
| EXIT_WAS_CLEARLY_JUSTIFIED | 5 | -13,000 |
| EXIT_CONTRADICTORY_WITH_NEXT_BUY | 1 | -15,200 |
| INSUFFICIENT_EVIDENCE | 1 | +13,230 |

The 1BD pattern is dominated by likely premature EXIT, not only aggressive re-entry.

## EXIT Reason Distribution

| EXIT reason category | Count |
|---|---:|
| RISK | 61 |
| RANK_DETERIORATION | 22 |
| EXPECTED_EDGE_MIXED | 7 |
| PORTFOLIO_FIT | 3 |

Important caveat: D17/D18 run evidence often shows PM `ADD` or `HOLD` on the exit day while downstream Runtime Planning produced `SELL_EXIT`. Therefore reason categories are diagnostic and must be read with authority lineage, not as clean PM EXIT reasons.

## HOLD Persistence

Strong-holder premature EXIT candidates:

```text
77
```

The pattern includes cases where exit-day PM evidence still indicated:

```text
ADD
HOLD
high rank
positive expected edge / score
positive unrealized PnL
```

yet the actual runtime action was `SELL_EXIT`, followed quickly by `BUY_NEW`.

This supports:

```text
HOLD_PERSISTENCE_GAP
```

## Loss-cut Separation

Valid loss-cut count:

```text
7
```

D22 does not recommend weakening loss cuts. Valid severe-risk / hard-stop style exits must remain protected.

Classification counts:

```text
LOSS_CUT_VALID = 7
PREMATURE_EXIT = 70
OSCILLATING_EXIT = 77
PROFIT_PROTECTION_VALID = 0
```

## Post-hoc Missed Move

Premature EXIT post-hoc diagnostic:

```text
POST_HOC_DIAGNOSTIC_ONLY
```

Estimated missed move from exit price to re-entry price for premature EXIT candidates:

```text
-45,680
```

This is not a Runtime feature and not a decision input. It only says that the price move between exit and re-entry was mixed and does not by itself justify holding every premature-exit candidate. The stronger finding is oscillation frequency and authority inconsistency, not missed-move profit.

## Existing Hysteresis Guard Audit

Status:

```text
NO_ACTIVE_GENERAL_HOLD_EXIT_HYSTERESIS_GUARD
```

Evidence:

- Phase27-D6-D implemented only a narrow profit-retention-only EXIT to HOLD boundary.
- It explicitly did not add holding-day rules, cooldown, or general hysteresis.
- Architecture defines HOLD/EXIT philosophy, but leaves numeric boundaries and persistence open.
- D22 artifacts did not show active consumption of multi-day confirmation, hold persistence, exit confirmation, or general state persistence in the audited EXIT -> BUY_NEW pairs.

## BUY_ADD Relation

Judgment:

```text
PARTIAL_RELATION_SUPPORTED_PRE_D19
```

Evidence:

```text
previous campaign exit-day PM ADD count = 22
PM ADD vs SELL_EXIT action conflict count = 22
```

Interpretation:

The D17 run predates D19. These cases are authority/propagation conflict evidence, not proof that every case should have become BUY_ADD. D19 remains unchanged.

## Cash Utilization Relation

Judgment:

```text
LIKELY_CONTRIBUTOR
```

Frequent:

```text
EXIT -> cash
↓
next-business-day BUY_NEW
```

creates transient cash cycling. D22 does not change Cash Policy and does not claim independent cash-policy causality.

## D21 Integration Decision

D21 design implementation decision:

```text
MODIFY
```

Reason:

```text
Re-entry defect is real, but previous EXIT side also shows premature / oscillating behavior.
Implementing only the D21 re-entry gate may block symptoms while leaving the sensitive EXIT boundary unresolved.
```

Selected case:

```text
Case C: Both boundaries sensitive
```

Next Phase:

```text
Phase28-D23C EXIT-Re-entry Hysteresis Unified Design
```

## Deliverables

```text
docs/phase_reports/phase28_d22_premature_exit_and_exit_reentry_oscillation_audit.md
reports/phase_reports/phase28_d22_premature_exit_and_exit_reentry_oscillation_audit.json
reports/phase28_d22_premature_exit_and_exit_reentry_oscillation_audit/
```

## Final Judgment

```text
Primary Judgment: PHASE28_D22_EXIT_REENTRY_OSCILLATION_CONFIRMED
93 pair audit status: COMPLETE
1BD re-entry pair count: 68
EXIT valid count: 9
Premature EXIT count: 70
Both-boundary oscillation count: 37
Re-entry-aggressive-only count: 7
Valid lifecycle count: 2
Insufficient evidence count: 14
Existing HOLD/EXIT hysteresis guard: NO_ACTIVE_GENERAL_HOLD_EXIT_HYSTERESIS_GUARD
D21 design implementation decision: MODIFY
Next Phase: Phase28-D23C EXIT-Re-entry Hysteresis Unified Design
```
