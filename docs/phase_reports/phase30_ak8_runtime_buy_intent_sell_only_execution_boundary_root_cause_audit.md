# Phase30-AK8 — Runtime BUY Intent / Sell-Only Execution Boundary Root-Cause Audit

## Scope

Task ID: `Phase30-AK8`

Type: `READ_ONLY_RUNTIME_EXECUTION_AUTHORITY_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

Primary window:

```text
2022-09-13 through 2022-09-27
```

No implementation, replay, resume, fresh run, target-run mutation, Strategy
change, Candidate change, cap change, Safety relaxation, BUY/SELL sequencing
change, or same-day proceeds rule change was performed.

The target run predates AK7R and AK5R2. It is used only as root-cause evidence
for the Runtime BUY -> SELL-only execution boundary, not as post-repair
performance validation.

## Primary Judgment

```text
SELL_ONLY_BOUNDARY_POPULATION_COUNT = 13
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

AK8 confirms a Runtime/Pending authority boundary defect. The 13 BUY_NEW rows
identified by AK7 all reached PC positive, PS positive, Runtime BUY_NEW, and
morning pending generation. They disappeared after morning pending generation
when sell planning wrote a later SELL-only pending plan to the single canonical
current pending slot. Submit and Execution then consumed only that latest
SELL-only pending authority.

This is not explained by same-day SELL proceeds timing. All 13 audited BUY rows
were individually executable with start-of-day cash. Eight were already in the
cash-feasible BUY batch with `planning_submit_feasibility_pass`; five were not
in the active cash-feasible batch because of dynamic-capacity / reservation
priority, but even those did not require same-day SELL proceeds on an individual
notional basis.

## Canonical Population

`SELL_ONLY_BOUNDARY_POPULATION_COUNT = 13`

Canonical rows are the AK7 `runtime_buy_new_to_fill_rows.json` rows whose
`runtime_to_fill_reason` is `superseded/sell-only execution boundary`.

| Date | BUY symbol | BUY qty | Reserved notional | Morning batch status | Same-day SELL fills |
| --- | ---: | ---: | ---: | --- | --- |
| 2022-09-15 | 43550 | 100 | 28,400 | `planning_submit_feasibility_pass` | 78780 SELL 100 |
| 2022-09-15 | 43870 | 100 | 135,900 | `reserved notional exceeds dynamic cash capacity` | 78780 SELL 100 |
| 2022-09-16 | 47600 | 100 | 190,200 | `reserved notional exceeds dynamic cash capacity` | 71380 SELL 100; 33700 SELL 100; 21640 SELL 300 |
| 2022-09-16 | 33500 | 600 | 47,280 | `planning_submit_feasibility_pass` | 71380 SELL 100; 33700 SELL 100; 21640 SELL 300 |
| 2022-09-16 | 49200 | 100 | 136,500 | `planning_submit_feasibility_pass` | 71380 SELL 100; 33700 SELL 100; 21640 SELL 300 |
| 2022-09-20 | 73590 | 100 | 78,700 | `planning_submit_feasibility_pass` | 44410 SELL 100; 36600 SELL 100 |
| 2022-09-20 | 43870 | 100 | 135,100 | `planning_submit_feasibility_pass` | 44410 SELL 100; 36600 SELL 100 |
| 2022-09-20 | 21380 | 100 | 94,500 | `planning_submit_feasibility_pass` | 44410 SELL 100; 36600 SELL 100 |
| 2022-09-20 | 49200 | 100 | 137,300 | `reserved notional exceeds dynamic cash capacity` | 44410 SELL 100; 36600 SELL 100 |
| 2022-09-22 | 73590 | 100 | 90,000 | `reserved notional exceeds dynamic cash capacity` | 47600 SELL 100; 68360 SELL 100; 60850 SELL 200; 43550 SELL 100; 21380 SELL 100 |
| 2022-09-22 | 76920 | 300 | 24,390 | `planning_submit_feasibility_pass` | 47600 SELL 100; 68360 SELL 100; 60850 SELL 200; 43550 SELL 100; 21380 SELL 100 |
| 2022-09-22 | 41920 | 100 | 85,500 | `reserved notional exceeds dynamic cash capacity` | 47600 SELL 100; 68360 SELL 100; 60850 SELL 200; 43550 SELL 100; 21380 SELL 100 |
| 2022-09-22 | 41700 | 100 | 54,800 | `planning_submit_feasibility_pass` | 47600 SELL 100; 68360 SELL 100; 60850 SELL 200; 43550 SELL 100; 21380 SELL 100 |

## Full BUY Lineage

```text
FIRST_BUY_DISAPPEARANCE_LAYER_DISTRIBUTION = {
  "SELL_PLANNING_PENDING_COMPOSITION_OVERWRITE": 13
}
```

All 13 rows have the same primary lineage:

```text
PC positive
-> PS positive
-> Runtime BUY_NEW
-> Morning Planning
-> Pending Generation
-> sell_planning writes later SELL-only pending
-> Submit sees SELL-only pending
-> Execution fills SELL only
-> no BUY fill
```

Evidence:

- `strategy/runtime_planning.json` contains the audited BUY_NEW plans.
- `morning/planning_evidence.json` contains the BUY lineage and cash-feasible
  batch evidence.
- `morning/pending_generation_evidence.json` reports `pending_path_written=true`.
- `sell_planning/pending_continuity_evidence.json` reports
  `pending_path_written_by_sell_planning=true` on all four affected dates.
- `execution/submitted_order_authority.json` reports submitted order counts that
  equal only the SELL fills.
- `execution/fills.json` contains no audited BUY symbols.

## Same-Day SELL Lineage

```text
SELL_EXECUTION_SUCCESS_COUNT = 11
```

SELL execution succeeded on all affected sell-side items:

| Date | Submitted orders | SELL fills |
| --- | ---: | --- |
| 2022-09-15 | 1 | 78780 SELL 100 |
| 2022-09-16 | 3 | 71380 SELL 100; 33700 SELL 100; 21640 SELL 300 |
| 2022-09-20 | 2 | 44410 SELL 100; 36600 SELL 100 |
| 2022-09-22 | 5 | 47600 SELL 100; 68360 SELL 100; 60850 SELL 200; 43550 SELL 100; 21380 SELL 100 |

The SELL path itself is action-effective. The defect is that SELL-only pending
became the only authority consumed by Submit/Execution after valid BUY intent
had already been produced.

## BUY / SELL Independence

```text
BUY_SELL_INDEPENDENCE_PRESERVED = NO
CURRENT_RUNTIME_SEMANTIC = SELL_ONLY
SELL_ONLY_BEHAVIOR_ARCHITECTURALLY_INTENDED = NO
```

The target run behavior is SELL-only, not SELL-first. SELL-first would preserve
canonical BUY intent and let BUY submit/execution proceed if its own cash,
Safety, authority, and pending constraints pass. Here, SELL planning wrote a
later current pending plan and Submit/Execution never saw the morning BUY items.

SELL liquidation was not weakened; it filled successfully. The broken contract
is item independence across the shared single current Pending authority.

## Cash / Buying Power Authority

```text
BUY_EXECUTABLE_WITH_STARTING_CASH_COUNT = 13
BUY_REQUIRES_SAME_DAY_SELL_PROCEEDS_COUNT = 0
```

Starting cash / buying power used by Runtime Planning:

| Date | Starting cash | Morning final reserved BUY notional | SELL realized proceeds |
| --- | ---: | ---: | ---: |
| 2022-09-15 | 201,450 | 69,420 | 224,500 |
| 2022-09-16 | 425,950 | 224,680 | 83,190 |
| 2022-09-20 | 509,140 | 308,300 | 156,300 |
| 2022-09-22 | 317,090 | 79,190 | 283,190 |

The morning BUY batch evidence uses starting cash, not same-day SELL proceeds.
For the 13 audited BUY rows, no item required same-day proceeds on an individual
reserved-notional basis.

## Same-Day SELL Proceeds Contract

```text
SAME_DAY_SELL_PROCEEDS_REUSE_CONTRACT = CONDITIONAL
```

Architecture history uses SELL-first semantics: SELL can be processed first,
and BUY can proceed after fill only if the common Production/Historical
authority path re-evaluates cash / buying power. The audit found no authority
allowing sell proceeds to be silently injected into the pre-sell morning BUY
batch. AK8 does not change that rule.

## Pending Composition

```text
BUY_PENDING_LOST_OR_OVERWRITTEN_COUNT = 13
MIXED_BUY_SELL_PENDING_SUPPORTED = CONDITIONAL
```

The target run evidence shows:

```text
morning pending generated
sell_planning pending_path_written_by_sell_planning = true
submit submitted SELL-only order list
execution fills SELL-only
```

Mixed BUY/SELL pending is architecturally supported only when the pre-sell BUY
pending is recognized as preservable and composed. Phase29-L21T-F implemented
that intended common-runtime repair after a related earlier audit, but the AK8
target run predates the relevant repairs and still demonstrates the broken
SELL-only boundary.

## Submit Feasibility

```text
BUY_REACHED_SUBMIT_COUNT = 0
BUY_SUBMIT_PASS_COUNT = 0
BUY_SUBMIT_REVIEW_COUNT = 0
```

The audited BUY rows do not reach Submit as BUY items. Submit consumed the
current pending slot after sell planning had written a SELL-only plan. Submit
therefore behaved locally according to the payload it received.

## Execution Boundary

```text
BUY_SUBMITTED_BUT_NOT_EXECUTED_COUNT = 0
EXECUTION_FILTERED_BUY_COUNT = 0
```

Execution did not filter submitted BUY orders. There were no submitted BUY
orders for the audited rows. Execution consumed the SELL-only submitted order
authority and filled those SELL orders.

## Previous Repairs / Regression

```text
SELL_ONLY_BOUNDARY_RECURRENCE_CLASSIFICATION = CONFIRMED_REGRESSION
ORIGINAL_REPAIR_TASK = Phase29-L21T-F
```

Related lineage:

- Phase29-L21T-E isolated a pending slot continuity break after Strategy
  Planning wrote BUY pending and before Submit consumed pending.
- Phase29-L21T-F implemented valid BUY pending preservation and BUY+SELL
  composition in Production-common pending / sell planning.
- Phase29-L21T-M/U/V/W later focused on BUY item scoped review, SELL
  continuation, batch submit independence, and lifecycle terminal-state edges.

Why the previous repair did not cover this target run:

```text
The target run was produced before the later pending preservation / composition
repairs and before AK7R / AK5R2. It remains valid recurrence evidence for the
pre-repair boundary, but not post-repair performance evidence.
```

## Current Code Residual Vulnerability

```text
CURRENT_CODE_STILL_HAS_SELL_ONLY_BOUNDARY = PARTIAL
```

Current code contains protections that were absent or not action-effective in
the target run:

- `read_active_buy_pending`;
- `compose_with_existing_buy_pending`;
- no-signal active pending preservation;
- run-scoped pre-sell pending snapshot evidence.

However, AK8 found no fresh post-AK7R/AK5R2 validation for the exact 13-row
active BUY + executable SELL path. Therefore the current residual vulnerability
is not proven as fully present, but a focused regression/fresh validation gate
is justified before claiming this boundary closed.

## Correct Architecture

```text
RECOMMENDED_BUY_SELL_EXECUTION_CONTRACT =
SELL safety / mandatory liquidation remains independent, and valid BUY intent
remains independently executable when its own cash, authority, Safety, pending,
submit, and execution constraints pass. SELL Planning may compose with, preserve,
or fail-closed around existing BUY pending, but must not silently replace valid
BUY authority with SELL-only current pending.
```

This does not weaken SELL and does not force BUY. It also does not permit
unapproved same-day sell-proceeds reuse.

## Root-Cause Classification

```text
SELL_ONLY_ROOT_CAUSE_DISTRIBUTION = {
  "BUY_PENDING_OVERWRITTEN": 13
}
```

Secondary facts:

- `BUY_NOT_CASH_FEASIBLE_WITH_STARTING_CASH = 0` on individual reserved notional;
- `BUY_REQUIRES_SELL_PROCEEDS_NOT_AVAILABLE = 0`;
- `SUBMIT_REVIEW = 0`;
- `EXECUTION_BUY_FILTERED = 0`.

## Required Final Judgments

```text
SELL_ONLY_BOUNDARY_POPULATION_COUNT = 13
FIRST_BUY_DISAPPEARANCE_LAYER_DISTRIBUTION = {"SELL_PLANNING_PENDING_COMPOSITION_OVERWRITE": 13}
SELL_EXECUTION_SUCCESS_COUNT = 11
BUY_SELL_INDEPENDENCE_PRESERVED = NO
CURRENT_RUNTIME_SEMANTIC = SELL_ONLY
SELL_ONLY_BEHAVIOR_ARCHITECTURALLY_INTENDED = NO
BUY_EXECUTABLE_WITH_STARTING_CASH_COUNT = 13
BUY_REQUIRES_SAME_DAY_SELL_PROCEEDS_COUNT = 0
SAME_DAY_SELL_PROCEEDS_REUSE_CONTRACT = CONDITIONAL
BUY_PENDING_LOST_OR_OVERWRITTEN_COUNT = 13
MIXED_BUY_SELL_PENDING_SUPPORTED = CONDITIONAL
BUY_REACHED_SUBMIT_COUNT = 0
BUY_SUBMIT_PASS_COUNT = 0
BUY_SUBMIT_REVIEW_COUNT = 0
BUY_SUBMITTED_BUT_NOT_EXECUTED_COUNT = 0
EXECUTION_FILTERED_BUY_COUNT = 0
SELL_ONLY_ROOT_CAUSE_DISTRIBUTION = {"BUY_PENDING_OVERWRITTEN": 13}
SELL_ONLY_BOUNDARY_RECURRENCE_CLASSIFICATION = CONFIRMED_REGRESSION
CURRENT_CODE_STILL_HAS_SELL_ONLY_BOUNDARY = PARTIAL
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = FALSE
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK8
```

## Deliverables

```text
docs/phase_reports/phase30_ak8_runtime_buy_intent_sell_only_execution_boundary_root_cause_audit.md
reports/phase_reports/phase30_ak8_runtime_buy_intent_sell_only_execution_boundary_root_cause_audit.json
```

## Recommended Next Task

```text
Phase30-AK8R — BUY / SELL Independent Execution Focused Repair
```
