# Phase31-E1 — Top50-to-Fill BUY Funnel PIT Causal Audit

Status: COMPLETE
Task type: READ-ONLY PIT / ARCHITECTURE AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_E1_BUY_FUNNEL_DOWNSTREAM_PRIORITY_MATERIALIZATION_GAP_IDENTIFIED_PARTIAL
```

E1 compared old/current BUY funnels from existing run artifacts only. No implementation, Strategy/Runtime/PM/PC/PS change, threshold tuning, fresh-run, resume, replay, or long Historical execution was performed.

The audit does not support a primary Candidate AI defect. The same-day candidate universe is mostly stable at the start, and the first large BUY/FILL divergence appears on 2022-08-10 while the candidate set is still identical. Entry and BUY Quality explain some later differences, but the dominant early divergence is after admitted candidates have already passed Entry, BUY Quality, position sizing, and Runtime Planning as BUYs.

The strongest supported cause is a downstream priority/materialization gap: common candidates with similar or identical PIT rank, Entry, BUY Quality, positive quantity, and Runtime BUY intent are materialized differently into Pending/Fill. B10-era marginal-capital priority is implicated as an attribution boundary because current artifacts carry canonical marginal priority evidence while the old run does not, but E1 cannot prove that B10 is itself defective rather than exposing/changing downstream ordering and cash materialization behavior.

## RUNS

```text
OLD_RUN_ID = runtime-test-historical-extended-smoke-20260818T015851711672Z
CURRENT_RUN_ID = runtime-test-historical-extended-smoke-20260820T120909096218Z
COMPARISON_WINDOW = 2022-08-10 through 2022-10-12
```

Target artifacts:

- `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/strategy_intelligence.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/position_sizing.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/morning/pending_generation_evidence.json`
- `reports/runtime_tests/runs/<run_id>/daily/<date>/execution/fills.json`

## FUNNEL_OLD

| Stage | Count |
|---|---:|
| TOTAL_TOP50 | 2,277 |
| TOP50_TO_ENTRY_PASS | 2,082 |
| TOP50_TO_BUY_QUALITY_PASS | 1,187 |
| TOP50_TO_EXPECTED_EDGE_PASS | 2,277 |
| TOP50_TO_PC | 2,277 |
| TOP50_TO_POSITIVE_QUANTITY | 178 |
| TOP50_TO_RUNTIME_BUY | 178 |
| TOP50_TO_FILL | 79 |

Notes:

- `TOP50` here means the daily `symbol_intelligence` candidate/intelligence set. It can exceed exactly 50 because runtime artifacts include retained/open-position intelligence in addition to pure top-rank candidates.
- Expected Edge was `UNCALIBRATED` for all audited symbol-date rows, so the count above means evidence present/non-blocking in this run, not a calibrated positive-edge pass.

## FUNNEL_CURRENT

| Stage | Count |
|---|---:|
| TOTAL_TOP50 | 2,261 |
| TOP50_TO_ENTRY_PASS | 2,067 |
| TOP50_TO_BUY_QUALITY_PASS | 1,185 |
| TOP50_TO_EXPECTED_EDGE_PASS | 2,261 |
| TOP50_TO_PC | 2,261 |
| TOP50_TO_POSITIVE_QUANTITY | 153 |
| TOP50_TO_RUNTIME_BUY | 153 |
| TOP50_TO_FILL | 73 |

Current loses 25 positive-quantity/runtime-BUY rows and 6 BUY fills relative to old. The larger degradation is not candidate discovery volume; it is admitted/sizeable BUYs becoming fewer and being materialized differently.

## TOP_DROP_REASONS_OLD

| Drop reason | Count |
|---|---:|
| BUY_QUALITY:BUY_WAIT | 512 |
| BUY_QUALITY:REJECT | 396 |
| NO_POSITIVE_QUANTITY:membership_intent=ADD_CANDIDATE, pm_action=NEW | 322 |
| NO_POSITIVE_QUANTITY:CAP_CONSTRAINED_LOT_EXECUTABLE | 227 |
| BUY_QUALITY:missing decision | 153 |
| ENTRY:BUY_WAIT:OVERHEATED_DECELERATING_ENTRY | 131 |
| NO_FILL after Runtime/Pending BUY path | 98 |
| FILLED | 78 |
| NO_POSITIVE_QUANTITY:MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX | 78 |
| NO_POSITIVE_QUANTITY:RETAIN/HOLD baseline preserved | 70 |
| ENTRY:NO_ADD:OVERHEATED_DECELERATING_ENTRY | 62 |
| NO_POSITIVE_QUANTITY:REDUCE unrepresentable/discrete lot path | 54 |

The old BUY fill artifact count is 79. The terminal classifier reports 78 `FILLED` rows because one BUY fill was outside the reconstructed Top50/symbol-intelligence terminal path used for drop-reason attribution.

## TOP_DROP_REASONS_CURRENT

| Drop reason | Count |
|---|---:|
| BUY_QUALITY:BUY_WAIT | 512 |
| BUY_QUALITY:REJECT | 396 |
| NO_POSITIVE_QUANTITY:membership_intent=ADD_CANDIDATE, pm_action=NEW | 389 |
| NO_POSITIVE_QUANTITY:CAP_CONSTRAINED_LOT_EXECUTABLE | 170 |
| BUY_QUALITY:missing decision | 138 |
| ENTRY:BUY_WAIT:OVERHEATED_DECELERATING_ENTRY | 134 |
| NO_POSITIVE_QUANTITY:MINIMUM_EXECUTABLE_LOT_EXCEEDS_SAFETY_HARD_MAX | 88 |
| NO_FILL after Runtime/Pending BUY path | 80 |
| NO_POSITIVE_QUANTITY:RETAIN/HOLD baseline preserved | 74 |
| FILLED | 71 |
| ENTRY:NO_ADD:OVERHEATED_DECELERATING_ENTRY | 58 |
| NO_POSITIVE_QUANTITY:REDUCE unrepresentable/discrete lot path | 57 |

The current BUY fill artifact count is 73. The terminal classifier reports 71 `FILLED` rows because two BUY fills were outside the reconstructed Top50/symbol-intelligence terminal path used for drop-reason attribution.

The most visible current-vs-old structural shift is not Entry or BUY Quality. It is the rise in `ADD_CANDIDATE`/`pm_action=NEW` rows with no positive quantity, plus different final materialization among already planned BUYs.

## SAME-DAY CANDIDATE COMPARISON

```text
FIRST_CANDIDATE_DIVERGENCE_DATE = 2022-08-12
CANDIDATE_SET_DIFFERENCE_COUNT = 66
```

On 2022-08-10, old and current candidate/intelligence symbol sets were identical. The portfolio and BUY fill sets already diverged that same day, so the first material BUY/FILL divergence cannot be attributed to candidate-set difference.

On 2022-08-12, the candidate/intelligence sets first diverged. The old run carried additional symbol-intelligence rows including `38410`, `39950`, and `61980`. This is a real candidate evidence difference, but it occurs after the first BUY/FILL divergence.

## COMMON CANDIDATE BUY DIVERGENCE

```text
COMMON_TOP50_BUY_DIVERGENCE_COUNT = 82
```

Representative PIT-only cases:

| Date | Symbol | Old result | Current result | PIT comparison |
|---|---|---|---|---|
| 2022-08-10 | `94340` | NO_FILL | FILLED | same Entry `BUY_NEW_REDUCED_ONLY`, same BUY Quality `REDUCED_ALLOCATION_ONLY`, same quantity 300, Runtime BUY in both |
| 2022-08-10 | `38410` | FILLED | NO_FILL | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `39950` | FILLED | NO_FILL | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `95010` | NO_FILL | FILLED | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `61980` | FILLED | NO_FILL | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `94320` | NO_FILL | FILLED | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `83060` | FILLED | NO_FILL | same Entry, BUY Quality, quantity, and Runtime BUY path |
| 2022-08-10 | `93180` | NO_FILL | FILLED | same Entry, BUY Quality `FULL_ALLOCATION_ELIGIBLE`, quantity 8,300, Runtime BUY in both |
| 2022-08-15 | `94320` | FILLED | NO_FILL | current turns into existing-position/retain no-positive-quantity path |
| 2022-08-16 | `78590` | FILLED | NO_FILL | Entry remains allowed, but current sizing path has no positive quantity |

These cases are not judged with later returns. They are used only to locate PIT internal consistency gaps.

## DIFFERENCE CLASSIFICATION

| Classification | Count |
|---|---:|
| ENTRY_DIFFERENCE_COUNT | 16 |
| BUY_QUALITY_DIFFERENCE_COUNT | 4 |
| EXPECTED_EDGE_DIFFERENCE_COUNT | 0 |
| ELIGIBILITY_DIFFERENCE_COUNT | 0 |
| PC_MEMBERSHIP_DIFFERENCE_COUNT | 0 |
| B10_PRIORITY_DIFFERENCE_COUNT | 55 |
| SIZING_DIFFERENCE_COUNT | 7 |
| CASH_FEASIBILITY_DIFFERENCE_COUNT | 0 |
| RUNTIME_PENDING_DIFFERENCE_COUNT | 0 |
| OTHER_DIFFERENCE_COUNT | 0 |

Interpretation:

- Entry and BUY Quality differences exist, but they are not the dominant common-candidate divergence.
- Expected Edge was not a calibrated differentiator in the audited artifacts.
- PC membership was broad enough that membership itself did not explain the divergence.
- The largest bucket is priority/materialization. In many first-day cases, both runs had the same admitted BUY candidate and planned quantity, yet only one side filled.
- `RUNTIME_PENDING_DIFFERENCE_COUNT = 0` means no separate Runtime Planning intent classifier dominated the common-candidate set after quantity and priority were considered. It does not mean Pending/Fill materialization is irrelevant; `NO_FILL` remains a top terminal reason.

## BUY TIMING

| Metric | Count |
|---|---:|
| old BUY symbols | 74 |
| current BUY symbols | 68 |
| union BUY symbols | 83 |
| common BUY symbols | 59 |
| common symbols with different first BUY date | 26 |
| BUY_TIMING_DIFFERENCE_COUNT including one-sided BUYs | 50 |

One-sided BUY symbols:

| Side | Symbols |
|---|---|
| old-only | `21560`, `27780`, `38410`, `39950`, `41700`, `44410`, `45410`, `45960`, `47770`, `50310`, `61980`, `70640`, `71730`, `77070`, `78780` |
| current-only | `36000`, `47600`, `70780`, `83340`, `88910`, `92710`, `93180`, `93600`, `99840` |

Common first-BUY timing examples:

| Symbol | Old first BUY | Current first BUY |
|---|---|---|
| `40800` | 2022-08-15 | 2022-08-16 |
| `47840` | 2022-08-10 | 2022-08-15 |
| `78590` | 2022-08-16 | 2022-08-15 |
| `83060` | 2022-08-10 | 2022-08-15 |
| `91070` | 2022-08-17 | 2022-08-12 |
| `94320` | 2022-08-15 | 2022-08-10 |
| `94340` | 2022-08-17 | 2022-08-10 |
| `95010` | 2022-09-09 | 2022-08-10 |

## PRIMARY_BUY_FUNNEL_CAUSE

```text
PRIMARY_BUY_FUNNEL_CAUSE = DOWNSTREAM_PRIORITY_AND_PENDING_FILL_MATERIALIZATION_AFTER_CANDIDATE_ENTRY_BUY_QUALITY
```

The first candidate-set difference is 2022-08-12, but the first BUY/FILL divergence is already visible on 2022-08-10. On that date, multiple divergent symbols share the same candidate presence, Entry action, BUY Quality action, positive quantity, and Runtime BUY intent. Therefore the first-order cause is downstream of candidate discovery and basic admission.

## DEFECT SUPPORT

```text
CANDIDATE_AI_DEFECT_SUPPORTED = NO
DOWNSTREAM_BUY_FUNNEL_DEFECT_SUPPORTED = PARTIAL
B10_DEFECT_SUPPORTED = PARTIAL
```

`CANDIDATE_AI_DEFECT_SUPPORTED = NO` because E1 found no evidence that current primarily failed to discover plausible PIT BUY candidates. Candidate set differences exist but are later and smaller than the downstream materialization differences.

`DOWNSTREAM_BUY_FUNNEL_DEFECT_SUPPORTED = PARTIAL` because common candidates can travel through the buy path to positive Runtime BUY intent but diverge at materialization. However, E1 is an audit, not a formal contract proof that the materialization behavior violates the current Runtime design.

`B10_DEFECT_SUPPORTED = PARTIAL` because current has canonical marginal-capital priority fields and old does not; the largest common-candidate classification sits at this priority boundary. E1 does not prove the B10 priority formula is wrong, only that B10-era priority/materialization is where the BUY composition/timing gap is concentrated.

## REPAIR_CANDIDATES

PIT-supported family-wide repair/design candidates for a follow-up task:

1. Add or validate a canonical per-symbol final BUY materialization reason from Runtime Planning through Pending and Fill, especially for positive-quantity BUY candidates that become `NO_FILL`.
2. Audit the B10 marginal-capital priority consumer boundary: confirm whether priority order, reserved cash, and pending selection all consume the same authority and expose comparable evidence.
3. Audit the `ADD_CANDIDATE` + `pm_action=NEW` no-positive-quantity path, because it rose from 322 old rows to 389 current rows and directly reduces current positive BUY quantity.
4. Keep Candidate AI, Entry thresholds, BUY Quality thresholds, and Expected Edge calibration out of E2 unless a new PIT inconsistency is found there.

## REQUIRED FLAGS

```text
FUTURE_INFORMATION_USED_FOR_DECISION_JUDGMENT = NO
OUTCOME_USED_FOR_PARAMETER_SELECTION = NO
IMPLEMENTATION_CHANGED = NO
LONG_HISTORICAL_EXECUTED = NO
```

Later performance from E0 was used only to choose audit cases. It was not used to judge whether a decision-time BUY candidate was correct, and no parameter or threshold selection was made.

## NEXT_TASK_RECOMMENDATION

```text
Phase31-E2 focused repair/design audit for downstream BUY priority/materialization observability and B10 consumer alignment
```

Do not move directly to parameter tuning. The next useful step is to make the positive-quantity Runtime BUY to Pending/Fill boundary explainable and contract-checkable, then validate whether B10 marginal priority is consumed consistently by sizing, reserved cash, pending generation, and fill materialization.

## FINAL QUESTIONS

1. Did current fail to find good PIT BUY candidates?

   No. Candidate discovery is not the primary supported defect. The first BUY/FILL divergence occurs while same-day candidate sets are identical.

2. Were good candidates dropped downstream?

   Partially supported. Multiple common 2022-08-10 candidates had the same Entry, BUY Quality, quantity, and Runtime BUY path but different Fill outcomes.

3. Is degradation due to Candidate ranking or downstream capital/priority/eligibility?

   The supported cause is downstream capital/priority/materialization, not Candidate ranking. Entry and BUY Quality contribute smaller later differences.

4. Is B10 helping, hurting, or not actually active?

   B10 is active in the current run. Its net effect is mixed and cannot be judged as simply helping or hurting from E1 alone. It is implicated as the largest current-vs-old priority/materialization boundary.

5. What should E2 repair or audit next?

   E2 should focus on the Runtime BUY to Pending/Fill materialization contract, reserved-cash/priority consumption, and the `ADD_CANDIDATE` + `pm_action=NEW` no-positive-quantity path.
