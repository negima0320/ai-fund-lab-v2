# Phase28-D71 Final Closure / Phase29 Handoff

Primary Judgment:

```text
PHASE28_CLOSED_PHASE29_PERFORMANCE_HANDOFF_READY
```

## Closure Basis

D71 is read-only consolidation. No Production implementation, config, schema, threshold, model, Accepted Generation, Runtime artifact, Pending artifact, fresh run, resume, long historical, or 100BD rerun was changed or executed.

Latest Phase28 state:

```text
PHASE28_D70B_PHASE23I_STALE_NO_ACTION_FIXTURE_REPAIRED_FULL_RELEVANT_REGRESSION_PASS_RESUME_READY
```

D70B confirmed:

```text
Original failing test = PASS
Phase23-I full regression = PASS
Full relevant regression = 179 passed
Invalid authority fail-closed = PRESERVED
D61 / D63 / D69 preserved = YES
Resume Allowed = YES
Fresh-run Required = NO
D66 Status = READY_FOR_RESUME
```

Resume target:

```text
runtime-test-historical-smoke-20260809T065457596902Z
```

Important closure rule: this post-D61 100BD run is not complete at Phase28 closure. Treat it as continuing performance evidence for Phase29, not as a final Phase28 performance result.

## Inventory

Evidence:

```text
reports/phase28_d71_final_closure_phase29_handoff/phase28_report_inventory.json
```

Inventory found:

```text
docs/phase_reports phase28* reports = 76
reports/phase_reports phase28* summaries = 75
```

Phase28 was read as a full A through D70B sequence, not only D59 onward.

## Starting Problem

Phase27 handed Phase28 this goal:

```text
Move from "winning positions are held correctly" to
"additional capital is allocated correctly to winning positions only when
incremental portfolio Expected Value improves."
```

Phase28-A baseline evidence:

```text
run_id = runtime-test-historical-smoke-20260804T074611098414Z
PM ADD intent = 145
Runtime BUY_ADD = 0
ADD submit = 0
ADD fill = 0
Zero delta = 145
Zero quantity = 145
Rank1 existing position = 86
Rank1 ADD intent = 76
Rank1 BUY_ADD = 0
Average cash ratio = 50.108%
Final cash ratio = 65.965%
Average invested ratio = 49.892%
Final invested ratio = 34.035%
```

This confirmed that strong existing-position ADD intent existed but was not becoming executable capital deployment.

## ADD Architecture

Evidence:

```text
reports/phase28_d71_final_closure_phase29_handoff/phase28_performance_baseline_summary.json
reports/phase28_d71_final_closure_phase29_handoff/phase28_implementation_milestones.json
```

The intended funnel became:

```text
PM ADD
-> D55-A ADD investment evidence
-> Portfolio Construction
-> incremental target / campaign continuation / opportunity cost
-> D55-B lot-aware conversion
-> Position Sizing
-> Runtime Planning BUY_ADD
-> Submit
-> Fill
```

D59 pre-D61 evidence:

```text
PM ADD = 142
D55-A PASS = 69
PC positive existing-position ADD = 11
PS positive BUY_ADD delta = 4
Runtime BUY_ADD = 4
Runtime BUY_ADD fills = 3
```

D59 classification:

```text
A target/current collision request zero = 46
B lot-aware zero or final target not above current = 12
C PC positive but PS zero = 7
D PS positive but Runtime BUY_ADD not formed = 0
E Runtime BUY_ADD but no fill = 1
F Runtime BUY_ADD fill = 3
D55-A fail = 73
```

## Main Repairs

### PM ADD propagation

D10/D11/D12 confirmed PM ADD existed but was lost before Portfolio Construction because Strategy Position Management normalized inbound PM rows incorrectly. D12 repaired inbound PM decision normalization so `decision_type=ADD` and `pm_decision_id` propagate.

### ADD evidence and lot-aware conversion

D54 designed the missing ADD evidence and two-pass PC/PS lot-aware contract. D55-A implemented the unified ADD investment evidence resolver. D55-B implemented Position Sizing lot-feasibility preflight and PC final reallocation. D55-C wired active Runtime baseline supply and two-pass PC/PS. D58 repaired production-common campaign identity/baseline propagation.

### D61 capital conversion

D60 designed and D61 implemented the key capital conversion repair:

```text
target/current collision repair
ADD incremental request on top of current baseline
D55-B two-pass lot-aware primitive reused
PC final lot-aware accepted increment propagated to PS
Runtime Planning mapping unchanged
D55-A resolver unchanged
```

D61 did not mean "buy every ADD". It means eligible strong existing positions can receive additional capital after portfolio competition, lot feasibility, cash, concentration, broker eligibility, and safety constraints.

### D67-D69 signed-delta repair

Post-D61 run exposed a 2023-05-09 / 76470 defect:

```text
PM ADD
current_weight = 0.182409
post_add_target_weight = 0.18
target_weight_change = -0.002409
```

Portfolio Construction correctly emitted signed target delta as observability, but Position Sizing consumed `target_weight_change` through non-negative `_ratio()` as executable ADD authority and blocked. D68 kept `target_weight_change` signed and moved executable ADD quantity to positive-only transaction-delta authority. D69 implemented that repair:

```text
signed observability preserved
positive-only ADD transaction lineage used
positive BUY_ADD preserved
above-cap ADD = valid zero / NO_ACTION
REDUCE / EXIT / BUY_NEW preserved
D61 / D63 preserved
fail-closed preserved
```

D70A then classified the remaining SPA regression as stale test fixture, and D70B repaired only the test fixture. Full relevant regression passed.

## Runtime / Safety Defects

Phase28 also repaired Runtime defects exposed while measuring performance:

```text
SELL pending reconciliation / listed_info / broker eligibility propagation
Pending Safety EMPTY no-action false-positive
Corporate action / submit / broker classification authority gaps
```

D62 root cause:

```text
_historical_pending_safety_authority compared normal EMPTY/no-action terminal
pending slots against active/carry-forward safety binding fields.
```

D63 repair:

```text
Normal EMPTY/no-action terminal slots now return READY before active/carry-forward
safety comparisons, while active pending, failed attempts, SELL continuation,
wrong safety authority, and future evidence remain fail-closed.
```

This is not the same as performance improvement, but it was required to keep 100BD evidence clean and trustworthy.

## Evaluation Shadow

D64 classification:

```text
EVALUATION_SHADOW_DEFECT
```

It compared unlike contracts:

```text
Phase19 validation-window aggregate baseline:
standardized_score / runtime_baseline_expected_output_schema / calibration_applied=true

Daily Runtime Opportunity artifact:
runtime_opportunity_score / accepted_generation_bound_imputer_scaler_model / calibration_applied=false
```

D64 found:

```text
Production Strategy affected = NO
Candidate Ranking affected = NO
PM decision affected = NO
D61 ADD repair affected = NO
```

Carry this to Phase29 as separate observability cleanup, not as a production performance defect.

## 100BD Evidence

Earlier Phase28 completed run with BUY_ADD still zero:

```text
run_id = runtime-test-historical-smoke-20260806T053322547871Z
completed business days = 100
final_runtime_judgment = PASS
close/fresh summary = REVIEW_REQUIRED due non-blocking strategy shadow review
initial_equity = 1,000,000
final_equity = 1,058,200
return_rate = +5.82%
BUY_ADD fill = 0
average cash ratio = 73.380%
```

D61 pre-repair baseline selected by D65:

```text
run_id = runtime-test-historical-smoke-20260809T010010445473Z
initial_equity = 1,000,000
final_equity = 1,123,400
total_return = +123,400
return_rate = +12.34%
BUY executions = 24
SELL executions = 35
PM HOLD = 185
PM ADD = 190
PM REDUCE = 29
PM EXIT = 17
final current positions = 4
```

Use it as D66 comparison baseline with D64 evaluation-shadow noise separated from production Runtime PASS/BLOCK judgment.

Post-D61 run:

```text
run_id = runtime-test-historical-smoke-20260809T065457596902Z
status at Phase28 closure = resume-ready, not complete
halt exposed D67 signed-delta contract mismatch
D69 repaired root cause
D70B opened resume gate
```

Note: the run id `runtime-test-historical-smoke-20260805T204551337825Z` is present in D4 as a 2023-03-15 submit HALT run, and no local run directory/final summary was available in this workspace. D71 does not treat it as successful final 100BD performance evidence.

## Position Count

Phase28 closure does not establish a final post-D61 dynamic position-count result because D66 is run-incomplete:

```text
dynamic_position_count = INSUFFICIENT_EVIDENCE_RUN_INCOMPLETE
```

The goal is not a fixed five-name portfolio. Position count should be dynamically determined by Market Context, Portfolio Policy, Candidate eligibility, existing holdings, Opportunity Cost, capital allocation, safety, broker eligibility, and lot constraints. Zero positions can be valid in risk-off/opportunity-shortage states, and five positions is not a hard target unless a current authority explicitly says so.

Phase29 must measure average/median/min/max current positions, final count, concentration, and whether legacy `max_positions=5` is merely compatibility metadata or an effective constraint.

## Phase29 Handoff

Evidence:

```text
reports/phase28_d71_final_closure_phase29_handoff/phase29_backlog.json
```

Phase29 must remain a performance-improvement phase. Target:

```text
annual return goal = +50%
initial capital = 1,000,000 JPY
cash equities only
momentum-oriented swing strategy
```

Investment philosophy:

```text
Hold strong positions while momentum persists.
ADD to existing positions only when incremental value and evidence justify it.
REDUCE / EXIT when expected edge, risk, or momentum deteriorates.
Suppress unnecessary short-term re-entry.
Deploy capital aggressively in risk-on environments with sufficient opportunity,
but do not force investment, fixed position count, or full cash usage.
Cash is valid under risk-off, opportunity shortage, or safety constraints.
```

Phase29 first action:

```text
User resumes runtime-test-historical-smoke-20260809T065457596902Z.
After completion, run D66-style post-D61 effect attribution.
```

Approved user resume command:

```text
PYTHONPATH=src python3 scripts/runtime_test.py resume --profile historical-smoke --run-id runtime-test-historical-smoke-20260809T065457596902Z --confirm --yes-i-understand-this-mutates-trading-state
```

Do not run a fresh 100BD unless the resumed run becomes invalid or unrecoverable.

## Phase29 Backlog

Priority A:

```text
D61 post-repair effect attribution after the resumed 100BD completes.
Compare PM ADD, D55-A PASS, PC positive ADD, PS positive BUY_ADD,
Runtime BUY_ADD, fills, notional, exposure, cash, position count,
concentration, total return, realized PnL, and turnover.
```

Priority B:

```text
Cash / exposure utilization.
Architecture repair is complete, but final effect is unmeasured.
```

Priority C:

```text
Dynamic position count / diversification / concentration.
```

Priority D:

```text
BUY_NEW capital allocation and lot/min-notional conversion.
```

Priority E:

```text
Re-entry / excessive EXIT / exit-buy oscillation.
D20/D22 confirmed this remains material.
```

Priority F:

```text
HOLD quality: whether winners are held while momentum persists and whether ADD/HOLD conflict.
```

Priority G:

```text
Market Context and defensive behavior: aggressive deployment without forced buying.
```

Separate track:

```text
D64 evaluation-shadow baseline/current semantics cleanup for cleaner acceptance evidence.
```

## Final Judgment

```text
Phase28 Closed = YES
Phase29 Entry = APPROVED
Latest Gate = D70B resume-ready
Post-D61 100BD Completed = NO
Resume Target = runtime-test-historical-smoke-20260809T065457596902Z
Resume Allowed = YES
Fresh-run Required = NO
D66 Status = READY_FOR_RESUME
Primary Phase29 Task = Complete/resume post-D61 100BD and perform effect attribution
Production implementation changed in D71 = NO
Config changed = NO
Schema changed = NO
Threshold changed = NO
Model changed = NO
Accepted Generation changed = NO
Runtime artifact mutated = NO
Pending artifact mutated = NO
Fresh-run executed = NO
Resume executed = NO
Long Historical executed = NO
100BD rerun executed = NO
```
