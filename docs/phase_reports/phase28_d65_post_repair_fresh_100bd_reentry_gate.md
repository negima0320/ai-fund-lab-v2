# Phase28-D65 Post-Repair Fresh 100BD Re-entry Gate

## Primary Judgment

```text
PHASE28_D65_POST_REPAIR_FRESH_100BD_REENTRY_APPROVED_D66_MEASUREMENT_CONTRACT_FROZEN
```

Secondary judgments:

```text
D61_IMPLEMENTATION_PRESENT
D63_PENDING_SAFETY_REPAIR_PRESENT
D64_EVALUATION_SHADOW_DEFECT_ISOLATED
FRESH_100BD_COMPARISON_CONDITIONS_FROZEN
D66_POST_RUN_EFFECT_ATTRIBUTION_READY
```

Fresh 100BD Re-entry Gate:

```text
APPROVED
```

This approval is for a user-executed fresh 100BD Historical Runtime Test only. Resume is not valid for D61 effect measurement.

## Scope

D65 is a read-only gate and measurement-contract phase.

Executed by Codex:

```text
Evidence / implementation / contract review
Short targeted pytest regression
Report / summary / evidence generation
Roadmap update
```

Not executed:

```text
fresh-run
resume
100BD historical
long historical
runtime mutation
paper trading
demo trading
production trading
```

No implementation, Strategy, Runtime, PM, PC/PS, D55-A, threshold, config, schema, model, Accepted Generation, or AI lifecycle comparator change was made in D65.

## D61 Implementation Presence

Judgment:

```text
D61_IMPLEMENTATION_PRESENT
```

Current code confirms the D61 repair is present.

Portfolio Construction:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py::_resolve_canonical_add_allocation_bridge
```

Confirmed:

```text
PM ADD + D55-A PASS forms ADD incremental request on top of current baseline.
base_target - current_weight collision has not been restored as the accepted ADD request basis.
D55-B lot-aware final reallocation remains the shared primitive.
No forced one-lot / unconditional forced ADD path was introduced.
Runtime Planning mapping was not changed by D61.
```

Position Sizing:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py::_resolved_lot_aware_add_increment
src/ai_fund_lab_v2/strategy/position_sizing.py::_raw_position
```

Confirmed:

```text
For existing-position PM ADD, Position Sizing prefers
lot_aware_accepted_incremental_weight before pre-lot accepted_incremental_weight
when computing transaction_delta_weight.
```

D61 existing validation:

```text
Focused PC/PS regression = 8 passed
Full PC/PS regression = 117 passed
Runtime mapping regression = 2 passed
py_compile = PASS
git diff --check = PASS
```

D65 targeted regression:

```text
8 passed in 1.83s
```

Evidence:

```text
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/d61_implementation_presence.json
```

## D63 Repair Presence

Judgment:

```text
D63_PENDING_SAFETY_REPAIR_PRESENT
```

Current code confirms the D63 repair is present.

Repair location:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py::_historical_pending_safety_authority
src/ai_fund_lab_v2/runtime_v2/data_readiness.py::_historical_no_action_terminal_without_safety_binding_required
```

Only this narrow case becomes READY before active safety binding comparison:

```text
state = EMPTY
active_pending = false
items = []
consumed = false
SELL continuation = false
failed/incomplete retry-ineligible attempt = false
daily-neutral pending safety eligible = true
```

READY reason:

```text
historical_no_action_pending_safety_authority_ready
EMPTY_NO_ACTION_TERMINAL_NO_SAFETY_BINDING_REQUIRED
```

Fail-closed preservation remains present for:

```text
Active Pending
consumed / carry-forward Pending
failed / incomplete attempt
SELL continuation
wrong runtime run id
wrong profile id
wrong evidence root
future target/session evidence
```

D63 existing validation:

```text
Focused pending safety regression = 52 passed
JSON validation = PASS
py_compile = PASS
git diff --check = PASS
```

D65 targeted regression:

```text
8 passed in 1.83s
```

Evidence:

```text
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/d63_repair_presence.json
```

## D64 Isolation Confirmation

Judgment:

```text
D64_EVALUATION_SHADOW_DEFECT_ISOLATED
```

D64 confirmed:

```text
Mismatch classification = EVALUATION_SHADOW_DEFECT
Production Strategy affected = NO
Candidate Ranking affected = NO
PM decision affected = NO
D61 ADD repair affected = NO
```

D65 reconfirmed producer/consumer boundary:

```text
ai_lifecycle_gates.py:
  produces BASELINE_CURRENT_SEMANTICS_MISMATCH inside drift / observability gate.

lifecycle_evidence.py:
  builds baseline/current monitoring contracts.

Opportunity Ranking:
  emits runtime_opportunity_score from Accepted Generation COMMITTED binding.

BUY Quality:
  consumes current Opportunity artifact; calibration_applied=false is existing
  conservative signal reliability behavior, not D61 contamination.

Portfolio Construction:
  validates runtime_opportunity_score_authority.prediction_semantics ==
  runtime_opportunity_score.

Position Sizing:
  fail-closes semantic conflict and consumes PC target/lot lineage.

PM:
  independent existing-position action authority.

Runtime Planning:
  pure mapper of Strategy/PS execution intent; not a baseline drift consumer.
```

Production blocking defect:

```text
NO
```

D61 measurement contaminant:

```text
NO
```

Known observability noise separable:

```text
YES
```

D64 repair required before fresh 100BD:

```text
NO
```

If `BASELINE_CURRENT_SEMANTICS_MISMATCH` reappears in the next run, it must be separated from active Runtime PASS/BLOCK judgment. New unknown REVIEW_REQUIRED reasons must not be ignored.

Evidence:

```text
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/d64_isolation_confirmation.json
```

## Production Regression Check

D65 did not change production code.

Config / schema / model drift inspection:

```text
No D65 config/schema/model change detected.
```

Working tree note:

```text
The repository still contains existing uncommitted Phase28 production/report changes
from prior phases. D65 introduced no production code/config/schema/model changes.
Do not add further production changes before the user fresh-run.
```

Targeted D65 regression command:

```bash
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d61_add_current_above_base_target_still_requests_increment_when_eligible \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_d61_ps_prefers_pc_lot_aware_add_increment_over_pre_lot_increment \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase28_d63_empty_no_action_terminal_without_safety_binding_is_ready \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase17_bj_active_pending_safety_date_mismatch_remains_review_required \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase24_ih_same_day_failed_attempt_pending_does_not_block_daily_neutral_safety \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase24_ij_same_day_empty_unscoped_review_pending_is_retry_ineligible \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase24_ih_blocked_pending_with_items_remains_fail_closed \
  tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py::test_phase28_d63_future_empty_terminal_evidence_remains_fail_closed
```

Result:

```text
8 passed in 1.83s
```

Note:

```text
The bare pytest command was unavailable. python3 -m pytest was used.
One mistyped test id produced a no-test collection error before the corrected rerun.
```

## Fresh 100BD Re-entry Gate

Required gate checks:

```text
D61 implementation present = YES
D61 focused regression valid = YES
D63 implementation present = YES
D63 fail-closed regression valid = YES
D64 evaluation-shadow only = YES
Production Strategy unchanged outside approved D61 repair = YES, no D65 production edits
No D65 config/schema/threshold/model drift = YES
Target comparison conditions fixed = YES
Same start date / same 100BD / same initial cash available = YES
fresh-run required = YES
resume allowed = NO
```

Gate:

```text
APPROVED
```

## Baseline Run Definition

Before baseline:

```text
run_id = runtime-test-historical-smoke-20260809T010010445473Z
profile = historical-smoke
start_date = 2023-04-03
business_days = 100
initial_cash = 1000000
```

Baseline result:

```text
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
BUY execution notional = 2,413,150
SELL execution notional = 1,987,490
TOTAL execution notional = 4,400,640
realized_slice_gross_pnl = 55,840
```

Baseline ADD funnel from D59:

```text
PM ADD rows in active PC = 142
D55-A PASS = 69
PC positive existing-position ADD = 11
PS positive BUY_ADD delta = 4
Runtime BUY_ADD = 4
Runtime BUY_ADD fills = 3
```

D59 gap classification:

```text
A_TARGET_CURRENT_COLLISION_REQUEST_ZERO = 46
B_LOT_AWARE_ZERO_OR_FINAL_NOT_ABOVE_CURRENT = 12
C_PS_ZERO_AFTER_PC_POSITIVE = 7
D_PS_POSITIVE_BUT_RUNTIME_BUY_ADD_NOT_FORMED = 0
E_RUNTIME_BUY_ADD_NO_FILL = 1
F_RUNTIME_BUY_ADD_FILL = 3
D55A_FAIL = 73
```

Evidence:

```text
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/baseline_run_and_before_metrics.json
```

## Before/After Measurement Contract

D66 priority:

```text
Priority 1: ADD conversion funnel Before/After
Priority 2: Exposure / Cash utilization Before/After
Priority 3: Capital deployment and regression attribution
```

Comparison conditions:

```text
profile = historical-smoke
start_date = 2023-04-03
business_days = 100
initial_cash = 1000000
baseline_run_id = runtime-test-historical-smoke-20260809T010010445473Z
post_repair_run = new fresh-run only
resume = forbidden
```

Evidence:

```text
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/d66_measurement_contract.json
```

## ADD Conversion Funnel Metrics

D66 must count with the same definitions where possible:

```text
PM ADD
D55-A evaluated
D55-A PASS
ADD incremental request positive
PC accepted increment positive
PC final lot-aware increment positive
PS positive BUY_ADD delta
Runtime BUY_ADD formed
BUY_ADD submit accepted
BUY_ADD fills
```

Required conversion rates:

```text
D55-A PASS -> PC positive
PC positive -> PS positive
PS positive -> Runtime BUY_ADD
Runtime BUY_ADD -> Fill
```

## D59 Gap Classification Metrics

D66 must reuse the D59 categories:

```text
A: target/current collision request 0
B: lot-aware zero / final target not above current
C: PC positive but PS zero
D: PS positive but Runtime BUY_ADD not formed
E: Runtime BUY_ADD but no fill
F: Runtime BUY_ADD fill
```

D61 should primarily reduce:

```text
A
B
C
```

D is not a D61 target but must be regression-checked.

## Exposure / Cash Metrics

D66 must measure from available summary or targeted daily artifacts:

```text
average cash
average cash ratio
final cash
final cash ratio
average invested capital
average invested ratio
final invested capital
final invested ratio
average gross exposure
final gross exposure
max gross exposure
```

If a summarize scope returns `NOT_AVAILABLE`, D66 should derive from targeted daily current valuation / portfolio snapshots, not from unbounded recursive grep.

## Capital Deployment Metrics

D66 must compare:

```text
BUY execution count
SELL execution count
BUY execution notional
SELL execution notional
total execution notional
BUY_NEW count
BUY_NEW notional
BUY_ADD count
BUY_ADD notional
BUY_ADD fills
rejected / review-required capital attempts
dynamic cash capacity rejection count
lot-size zero conversion count
```

BUY_NEW and BUY_ADD must remain separate.

## Portfolio Breadth Metrics

D66 should capture when available:

```text
average position count
final position count
max position count
position entry count
position exit count
single-name concentration
largest position weight
```

The goal is not simple position-count growth. The primary question is whether strong existing positions receive ADD capital and whether exposure/cash utilization improves.

## PM Distribution Metrics

D66 must compare:

```text
HOLD
ADD
REDUCE
EXIT
```

D61 is not a PM change. A large PM distribution shift should be treated as a possible confounder.

## Performance Metrics

D66 must compare at minimum:

```text
initial equity
final equity
total return
return rate
realized PnL
unrealized PnL if available
maximum drawdown if derivable
turnover if derivable
```

Performance alone must not decide D61 success. The first acceptance axis is ADD conversion and exposure utilization.

## Re-entry / EXIT Watch Metrics

D65 does not repair re-entry / EXIT behavior. D66 should still observe:

```text
same-symbol SELL -> short-window BUY re-entry count
EXIT -> BUY_NEW re-entry
EXIT -> BUY_ADD classification
days between exit and re-entry
repeated exit/re-entry campaigns
PM EXIT count
SELL_EXIT count
```

This is diagnostic, not the primary D61 acceptance criterion.

## Success / Failure Criteria

D61 effect confirmed requires evidence that:

```text
D59 category A materially reduced or structurally resolved
D59 category C reduced by shared lot lineage repair
D55-A PASS -> PC/PS/Runtime BUY_ADD conversion improved
BUY_ADD fills materially increased above baseline 3
Exposure / invested ratio improved directionally
Safety / SELL / Pending / Runtime Planning did not regress
```

D61 effect not confirmed must be classified by cause:

```text
PM ADD不足
D55-A PASS不足
incremental request remains zero
portfolio competition rejects ADD
lot-aware zero remains
PC->PS zero remains
Runtime mapping failure
Submit Guard rejection
cash capacity rejection
broker/fill failure
another downstream bottleneck
```

## Known Review Noise Handling

Known D64 review family:

```text
BASELINE_CURRENT_SEMANTICS_MISMATCH
```

Handling:

```text
Do not fail the D61 production-effect test solely because this known family reappears.
Separate Production Runtime judgment, Planning judgment, Execution judgment,
Safety judgment, Strategy active consumer status, and Evaluation Shadow /
AI lifecycle observability judgment.
```

New unknown `REVIEW_REQUIRED` reasons must be classified separately and must not be ignored.

## User Fresh-run Command

The user may execute:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2023-04-03 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Codex must not execute this command.

Resume is forbidden for D61 effect comparison.

## Post-run Summary Commands

After the fresh 100BD completes, set:

```bash
RUN_ID="<NEW_RUN_ID>"
```

Performance:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --profile historical-smoke \
  --run-id "$RUN_ID" \
  --scope performance
```

Overview:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --profile historical-smoke \
  --run-id "$RUN_ID" \
  --scope overview
```

D66 should prefer targeted artifact reads from:

```text
final_summary.json
daily/<date>/strategy/portfolio_construction.json
daily/<date>/strategy/position_sizing.json
daily/<date>/strategy/runtime_planning.json
daily/<date>/submit/runtime_manifest.json
daily/<date>/execution/fills.json
daily/<date>/execution/realized_slices.json
daily/<date>/current_valuation_refresh/current_valuation_manifest.json
```

Avoid unbounded recursive grep over the full 100BD evidence root.

## D66 Entry Contract

D66 starts only after the user supplies the new fresh-run id.

D66 task:

```text
POST-D61 100BD EFFECT ATTRIBUTION
```

D66 priority:

```text
1. ADD conversion funnel Before/After
2. Exposure / Cash utilization Before/After
3. Capital deployment / regression attribution
```

Primary baseline:

```text
runtime-test-historical-smoke-20260809T010010445473Z
```

After run:

```text
new user-executed fresh-run with same profile/start/business-days/initial-cash
```

## Changed Files

D65 changed only reports and roadmap:

```text
docs/phase_reports/phase28_d65_post_repair_fresh_100bd_reentry_gate.md
reports/phase_reports/phase28_d65_post_repair_fresh_100bd_reentry_gate.json
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/
docs/01_requirements/phase_roadmap.md
```

## Validation Results

```text
Targeted pytest = 8 passed in 1.83s
JSON validation = PASS
git diff --check for D65 paths = PASS
Report / JSON / Evidence consistency = PASS
```

## Explicit Non-Actions

```text
Production implementation change = NO
Strategy change = NO
Runtime change = NO
PM change = NO
PC/PS change = NO
D55-A change = NO
threshold change = NO
config change = NO
schema change = NO
model change = NO
Accepted Generation mutation = NO
AI lifecycle comparator repair = NO
Runtime artifact mutation = NO
fresh-run = NO
resume = NO
100BD historical = NO
long historical = NO
Paper trading = NO
Demo trading = NO
Production trading = NO
```

## Deliverables

```text
docs/phase_reports/phase28_d65_post_repair_fresh_100bd_reentry_gate.md
reports/phase_reports/phase28_d65_post_repair_fresh_100bd_reentry_gate.json
reports/phase28_d65_post_repair_fresh_100bd_reentry_gate/
docs/01_requirements/phase_roadmap.md
```
