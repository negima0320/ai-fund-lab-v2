# Phase23-BH Opportunity No-Buy Reason Planning-Submit Boundary Alignment Repair

## Primary Judgment

```text
PHASE23_BH_NO_BUY_REASON_PLANNING_SUBMIT_ALIGNMENT_SHORT_VALIDATION_PASS
```

## Secondary Judgment

```text
NO_BUY_REASON_HARD_EXCLUSION_BOUNDARY_ALIGNED
PLANNING_SUBMIT_CONTRACT_ALIGNED
SUBMIT_GUARD_FAIL_CLOSED_PRESERVED
NO_FORCED_BUY
NO_FORCED_REPLACEMENT
PRODUCTION_COMMON_VALIDITY
READY_FOR_1BD_RUNTIME_RERUN
```

## Root Cause

Phase23-BG target run:

```text
runtime-test-historical-smoke-20260730T063001897459Z
business_date = 2026-07-06
symbol = 43780
```

Evidence showed:

```text
Opportunity Ranking
  no_buy_reason = high_downside_risk_score

Portfolio Construction
  membership_intent = ADD_CANDIDATE
  target_weight > 0

Position Sizing
  target_notional > 0
  quantity_delta_candidate = 100

Runtime Planning
  planning_intent = BUY_NEW
  planned_quantity = 100

Pending / Submit
  opportunity_no_buy_reason_present
  Submit HALT
```

Submit Guard was correct. The bug was upstream: Planning allowed an executable BUY item even though the Opportunity Authority had a non-empty `opportunity_no_buy_reason`.

## Contract Decision

`opportunity_no_buy_reason` is a hard buy exclusion.

Production-common contract:

```text
Opportunity Ranking
  opportunity_no_buy_reason non-empty

Portfolio Construction
  EXCLUDE / AVOID
  target_weight = 0

Runtime Planning
  NO_ORDER
  planned_quantity = 0

Pending
  no BUY pending item

Submit Guard
  fail-closed defense-in-depth remains unchanged
```

This is not a forced BUY path, not a minimum-one guarantee, and not a Historical-only branch.

## 修正内容

Implemented a shared no-buy resolver:

```text
opportunity_no_buy_reason_blocks_buy()
```

Portfolio Construction now consumes the same no-buy semantics as Submit Guard. A non-empty `opportunity_no_buy_reason` makes the member `EXCLUDE` / `AVOID`, with `target_weight = 0`.

Runtime Planning also applies the same contract defensively. If an upstream artifact still presents `BUY_NEW` or `BUY_ADD` while the Opportunity Authority has a non-empty no-buy reason, Runtime Planning converts it to `NO_ORDER` with zero planned quantity.

Target member selection was aligned so a no-buy opportunity occupying a ranked buy slot is not silently replaced by a lower-ranked candidate just to fill `target_position_count`.

## 修正対象ファイル

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/runtime_planning.py
tests/strategy/test_phase22_e_portfolio_construction.py
tests/strategy/test_phase22_g_runtime_planning.py
tests/runtime_v2/test_phase23_i_strategy_planning_authority.py
```

## 43780 Execution Trace

Pre-repair evidence:

```text
.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json
  row_index = 8
  no_buy_reason = high_downside_risk_score
  opportunity_row_id = opportunity-2026-07-06-43780-8-9e0dd3a8dd74dd04

reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T063001897459Z/daily/2026-07-06/strategy/runtime_planning.json
  planning_intent = BUY_NEW
  planned_quantity = 100

reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T063001897459Z/daily/2026-07-06/submit/runtime_manifest.json
  guard_reason = opportunity_no_buy_reason_present
```

Post-repair short validation:

```text
Portfolio Construction
  43780 -> EXCLUDE
  target_membership = false
  target_weight = 0

Runtime Planning
  no executable 43780 BUY plan

Canonical integration reproduction
  input BUY candidates = 9
  pending BUY items = 8
  43780 pending item = absent
  submit.status = PASS
  submit.blocked_count = 0
```

## Negative Fail-Closed Cases

Validated:

```text
non-empty no_buy_reason in Portfolio Construction -> EXCLUDE
non-empty no_buy_reason reaching Runtime Planning BUY -> NO_ORDER
Submit Guard no-buy blocking remains fail-closed
policy-driven zero/no-order remains possible
no forced BUY
no forced replacement
```

## Short Validation

```text
py_compile targeted modules/tests: PASS
portfolio construction BH targeted: PASS
runtime planning BH targeted: PASS
portfolio construction full file: 22 passed
runtime planning full file: 17 passed
opportunity eligibility guard regression: 7 passed
strategy planning authority BD regression: 2 passed
BH canonical integration reproduction: 1 passed
strategy planning authority full file: 12 passed
strategy expanded regression: 39 passed
submit/opportunity regression slice: 11 passed
pending/safety/submit regression slice: 12 passed
historical submit guard regression slice: 8 passed
git diff --check scoped files: PASS
```

Not executed:

```text
fresh-run
1BD
10BD
20BD
Broker Write
Runtime Switch
J-Quants fetch
```

## Evidence

Human:

```text
docs/phase_reports/phase23_bh_opportunity_no_buy_reason_planning_submit_boundary_alignment_repair.md
```

Machine:

```text
reports/phase_reports/phase23_bh_opportunity_no_buy_reason_planning_submit_boundary_alignment_repair.json
```

Evidence directory:

```text
reports/phase23_bh_opportunity_no_buy_reason_planning_submit_boundary_alignment_repair/
```

Required evidence files were generated:

```text
no_buy_reason_contract_decision.json
symbol_43780_execution_trace.json
candidate_selection_trace.json
portfolio_construction_trace.json
runtime_planning_trace.json
pending_item_trace.json
submit_guard_trace.json
historical_submission_trace.json
negative_fail_closed_cases.json
canonical_runtime_integration_reproduction.json
previous_blocker_regression_check.json
existing_run_hash_preservation.json
test_results.json
modified_files.json
```

## Existing Run Preservation

The following run directories were not modified by this task. Read-only tree hashes were recorded in `existing_run_hash_preservation.json`.

```text
runtime-test-historical-smoke-20260730T063001897459Z
runtime-test-historical-smoke-20260730T054102824494Z
runtime-test-historical-smoke-20260730T050344341520Z
```

## Remaining Gaps

No BH blocker remains under short validation.

The next runtime-level confirmation is Operator-run 1BD Historical Runtime rerun after Evidence Review.

## Next Operator Action

```text
READY_FOR_1BD_RUNTIME_RERUN = YES
```

Run only after ChatGPT Evidence Review.
