# Phase32-GQ1 — Post-GN In-Flight 7BD BUY Priority Sanity Audit

Status: READ-ONLY IN-FLIGHT AUDIT

Target GN run: `runtime-test-historical-extended-smoke-20260904T231555544129Z`

Pre-GN comparison run: `runtime-test-historical-extended-smoke-20260904T204012180628Z`

Audited window: 2023-06-01 through 2023-06-09, 7 business days

Runtime state / Pending / Ledger mutation performed: NO

fresh-run / resume / replay / recover performed: NO

Source/config/schema changes performed: NO

## Executive Judgment

GN BUY-only history-neutral priority is behaving as designed in the audited
in-flight actual runtime path.

Across 1442 comparable Current Opportunity rank pairs in 144 BUY-priority
candidates, post-GN MCV/PC priority preserved Current Opportunity order with
zero rank inversions. No history, relationship, accepted-increment, or hidden
reranking priority distortion was found. The actual BUY set matched the pre-GN
comparison run on every audited date.

SELL/PM, Position Sizing, semantic Cash values, Fresh Target SHADOW
non-authority, and Recent Exit Guard behavior remained stable in the 7BD window.

## Scope Note

The target run directory already contains dates after 2023-06-09, but this
audit intentionally inspected only the requested completed 7BD window:

- 2023-06-01
- 2023-06-02
- 2023-06-05
- 2023-06-06
- 2023-06-07
- 2023-06-08
- 2023-06-09

## Aggregate Metrics

BUY_PRIORITY_ORDER_PRESERVATION_RATE: 100%

HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: 0

ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT: 0

RELATIONSHIP_BEFORE_PRIORITY_COUNT: 0

NEW_ADD_PARITY_VIOLATION_COUNT: 0

HIDDEN_RERANKING_COUNT: 0

HIGHER_PRIORITY_SKIP_COUNT: 0

HIGHER_PRIORITY_SKIP_REASON_DISTRIBUTION: `{}`

UNJUSTIFIED_PRIORITY_SKIP_COUNT: 0

GN_PRIORITY_DIFFERENCE_FROM_PRE_GN_COUNT: 62

FIRST_GN_PRIORITY_DIFFERENCE_DATE: 2023-06-05

FIRST_GN_PRIORITY_DIFFERENCE_SYMBOL: `59550`

FIRST_GN_PRIORITY_DIFFERENCE_REASON: pre-GN priority was quality-class-first; post-GN priority is Current Opportunity rank-first. On 2023-06-05, pre-GN lifted lower-ranked `76920` ahead because it was `ELIGIBLE_STRONG`; post-GN preserved rank order and moved `59550` from priority 3 to 4 while `76920` moved from priority 1 to 8.

ACTUAL_BUY_DIFFERENCE_FROM_PRE_GN_COUNT: 0

PORTFOLIO_DIFFERENCE_FROM_PRE_GN_FOUND: NO

SELL_REGRESSION_FOUND: NO

SIZING_REGRESSION_FOUND: NO

CASH_REGRESSION_FOUND: NO

ADD_SAFETY_BYPASS_COUNT: 0

G129_REGRESSION_COUNT: 0

RECENT_EXIT_GUARD_BYPASS_COUNT: 0

GN_ACTUAL_PATH_WORKING_AS_DESIGNED: YES

CONTINUE_CURRENT_RUN_SAFE: YES

## Daily Sanity Matrix

| Date | BUY candidates | Rank pairs | Inversions | Preservation | Priority diffs vs pre-GN | Actual BUY diff | SELL/PM semantic diff | Sizing diff | Cash semantic diff | Guard bypass |
|---|---:|---:|---:|---:|---:|---|---|---|---|---:|
| 2023-06-01 | 23 | 253 | 0 | 100% | 0 | NO | NO | NO | NO | 0 |
| 2023-06-02 | 20 | 190 | 0 | 100% | 0 | NO | NO | NO | NO | 0 |
| 2023-06-05 | 21 | 210 | 0 | 100% | 17 | NO | NO | NO | NO | 0 |
| 2023-06-06 | 25 | 300 | 0 | 100% | 17 | NO | NO | NO | NO | 0 |
| 2023-06-07 | 22 | 231 | 0 | 100% | 14 | NO | NO | NO | NO | 0 |
| 2023-06-08 | 15 | 105 | 0 | 100% | 6 | NO | NO | NO | NO | 0 |
| 2023-06-09 | 18 | 153 | 0 | 100% | 8 | NO | NO | NO | NO | 0 |

## Accepted-Increment Independence

Post-GN priority did not depend on positive accepted increment.

Evidence:

- `ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT = 0`
- 26 rows had canonical priority despite zero accepted/requested deployment,
  which is expected under GN because priority is assigned before executable
  allocation and sizing filters.

Daily zero-accepted/requested rows with priority:

- 2023-06-01: 0
- 2023-06-02: 0
- 2023-06-05: 3
- 2023-06-06: 7
- 2023-06-07: 8
- 2023-06-08: 5
- 2023-06-09: 3

## Relationship / History Neutrality

Relationship and history checks passed:

- current-position relationship used before priority: 0
- old ownership used for priority: 0
- closed campaign used for priority: 0
- prior ADD count used for priority: 0
- prior EXIT used for priority outside bounded guard: 0
- average cost / realized PnL used for priority: 0
- hidden reranking count: 0

BUY_NEW / BUY_ADD relationship materialization remained downstream of canonical
priority. No flat/held priority asymmetry was detected in this 7BD actual path.

## PC Allocation / Skip Sanity

The refined skip audit counts only positive requested deployment candidates
that received zero accepted allocation while lower-priority candidates received
positive allocation.

Result:

- higher-priority positive-request skip count: 0
- unjustified skip count: 0
- skip reason distribution: `{}`

Rows with no requested increment, such as ADD target unchanged, were not counted
as priority skips.

## Pre-GN Comparison

Post-GN priority differs from pre-GN on 62 symbol-date rows, starting on
2023-06-05. The differences are expected and match the GN design:

- pre-GN could order by quality class before Current Opportunity rank;
- post-GN preserves Current Opportunity rank first;
- actual BUY outputs did not differ in the 7BD window.

Actual BUY comparison:

- 2023-06-01: unchanged
- 2023-06-02: unchanged
- 2023-06-05: unchanged
- 2023-06-06: unchanged
- 2023-06-07: unchanged
- 2023-06-08: unchanged
- 2023-06-09: unchanged

ACTUAL_BUY_DIFFERENCE_FROM_PRE_GN_COUNT: 0

PORTFOLIO_DIFFERENCE_FROM_PRE_GN_FOUND: NO

## SELL / PM

SELL and PM semantic surfaces matched pre-GN on every audited date.

Compared semantic surface:

- PM action tuples
- Runtime SELL plan tuples

SELL_REGRESSION_FOUND: NO

Observed SELL plans were identical on dates with sells, including:

- 2023-06-02: `21340`, `54010`
- 2023-06-05: `27620`, `31330`, `70660`, `72140`, `89180`
- 2023-06-06: `31920`, `75380`
- 2023-06-07: `37820`, `47550`
- 2023-06-08: `24040`, `70740`
- 2023-06-09: `43950`, `65780`

## Sizing / Cash / Safety

Position Sizing semantic comparison matched pre-GN on every audited date:

- target weights
- final quantity deltas
- incremental buy notional
- residual cash ratio
- target gross exposure ratio
- total target weight
- portfolio total equity

Cash semantic comparison matched pre-GN on every audited date:

- cash preference semantic
- remaining cash weight
- cash reason codes
- residual cash ratio
- target gross exposure ratio

Full cash evidence hashes differ between runs, but semantic values are equal.
This is evidence lineage/run-hash difference, not Cash semantic regression.

SIZING_REGRESSION_FOUND: NO

CASH_REGRESSION_FOUND: NO

ADD_SAFETY_BYPASS_COUNT: 0

G129_REGRESSION_COUNT: 0

## NCU / Fresh Target SHADOW Authority

NCU_COMPARATOR_INSTANCE_COUNT: 1

Fresh Target SHADOW remained non-authoritative:

- `authoritative_consumer_count = 0` on every audited date
- no Production order authority
- no Production quantity authority
- no Runtime Planning authority
- no Cash/SELL/RELEASE/EXIT authority

## Recent Exit Guard

Recent Exit Guard materialization matched pre-GN on every audited date.

Bypass count:

- 2023-06-01: 0
- 2023-06-02: 0
- 2023-06-05: 0
- 2023-06-06: 0
- 2023-06-07: 0
- 2023-06-08: 0
- 2023-06-09: 0

RECENT_EXIT_GUARD_BYPASS_COUNT: 0

No evidence was found of immediate re-buy increase, guard bypass, old EXIT
priority penalty revival, or blocked REENTRY fallback caused by GN.

## Required Answers

BUY_PRIORITY_ORDER_PRESERVATION_RATE: 100_PERCENT

HISTORY_CAUSED_PRIORITY_INVERSION_COUNT: 0

ACCEPTED_INCREMENT_PRIORITY_DEPENDENCY_COUNT: 0

RELATIONSHIP_BEFORE_PRIORITY_COUNT: 0

NEW_ADD_PARITY_VIOLATION_COUNT: 0

HIDDEN_RERANKING_COUNT: 0

HIGHER_PRIORITY_SKIP_COUNT: 0

HIGHER_PRIORITY_SKIP_REASON_DISTRIBUTION: {}

UNJUSTIFIED_PRIORITY_SKIP_COUNT: 0

GN_PRIORITY_DIFFERENCE_FROM_PRE_GN_COUNT: 62

FIRST_GN_PRIORITY_DIFFERENCE_DATE: 2023-06-05

FIRST_GN_PRIORITY_DIFFERENCE_SYMBOL: 59550

FIRST_GN_PRIORITY_DIFFERENCE_REASON: Current Opportunity rank-first GN priority replaced pre-GN quality-class-first priority ordering

ACTUAL_BUY_DIFFERENCE_FROM_PRE_GN_COUNT: 0

PORTFOLIO_DIFFERENCE_FROM_PRE_GN_FOUND: NO

SELL_REGRESSION_FOUND: NO

SIZING_REGRESSION_FOUND: NO

CASH_REGRESSION_FOUND: NO

ADD_SAFETY_BYPASS_COUNT: 0

G129_REGRESSION_COUNT: 0

RECENT_EXIT_GUARD_BYPASS_COUNT: 0

GN_ACTUAL_PATH_WORKING_AS_DESIGNED: YES

CONTINUE_CURRENT_RUN_SAFE: YES

## Final Judgment

Yes: in the audited 2023-06-01 through 2023-06-09 in-flight actual path, GN's history-neutral BUY priority preserves Current Opportunity order, does not reintroduce history/relationship/accepted-increment priority distortion, and does not break existing SELL, Sizing, Cash, Safety, ADD/G129, NCU, Fresh Target SHADOW, or Recent Exit Guard semantics.
