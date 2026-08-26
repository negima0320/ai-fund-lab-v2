# Phase31-G49 - G48 Expected Activation vs Fresh-Run Actual Decision-Path Causality Audit

Task type: READ-ONLY RUNTIME DECISION-PATH CAUSALITY AUDIT.

No implementation, Strategy, Runtime, config, threshold, parameter, or fixture
changes were made. No fresh-run, resume, replay, Historical rerun, or long
Historical was executed by this audit. The user-operated fresh-run may continue
independently; this report uses the completed-date evidence available at
inspection time.

## Judgment

`PRIMARY_JUDGMENT = PHASE31_G49_FRESH_RUN_RUNTIME_BINDING_CONNECTIVITY_DEFECT_FOUND`

The G48 expectation for `2022-10-03` was correct at the authoritative
Portfolio Construction decision level: the fresh-run produced canonical Cash
competitor evidence, executed the G43 market-candidate-cash interaction matrix,
and selected `CASH_OPTIONALITY` over 22 valid `COMPARABLE_MARGINAL` security
competitors under `SHORT_TERM_BREADTH_BREAKDOWN` and
`CAUTIOUS_DEPLOYMENT`.

However, that canonical final capital winner did not bind the downstream
Position Sizing / Runtime Planning / Submit / Execution path. The same
`2022-10-03` fresh-run still generated nine BUY plans and seven BUY fills,
matching the old run's filled BUY symbol set. The first authoritative decision
divergence is therefore `2022-10-03`, but the first order-intent divergence is
`2022-11-09`, and the first filled/end-of-day holding divergence is
`2022-10-28`.

This is not a profitability conclusion. PnL and later outcomes were not used as
connectivity evidence.

## Evidence Scope

- Fresh run: `runtime-test-historical-extended-smoke-20260823T092537838492Z`
- Comparison run: `runtime-test-historical-extended-smoke-20260822T174358377089Z`
- Fresh completed dates inspected at snapshot: 50
- Snapshot date range: `2022-10-03` through `2022-12-14`
- Common completed comparison dates: 50
- Required minimum window `2022-10-03` through `2022-10-31`: covered

Primary artifacts inspected:

- `strategy/market_context.json`
- `strategy/portfolio_policy.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `submit/submitted_order_authority.json`
- `execution/current_apply_evidence.json`
- `current_valuation_refresh/current_valuation_manifest.json`
- `day_completion/day_completion_evidence.json`
- `positions/position_campaigns.json`
- `run_state.json`

## G48 vs Fresh-Run Input Equality

The fresh-run `2022-10-03` Market Context artifact contains newer fields, so
the whole-file artifact hash differs from the old run. The decision-relevant PIT
input subset used by G48 is identical: comparable Market Context input hash
`c5aa402233331b6304f45981ae527cb0daad8cd4ce43ef5d6ccd8c99a3a31dbd` in both
runs.

The Portfolio Construction portfolio member context is also identical for the
decision-relevant subset: 50 members in both runs, comparable hash
`4833b6e17510450143be393cd6137c115f18b295d4ad82c8db05dedb677e7c59`.

The old and fresh `2022-10-03` Runtime Planning BUY plans are identical for the
simple executable intent fields, with hash
`aae0f5ff97f3d70b074cf24e15a5d547aac5fef8f69ea58db8e61cf5a2ea843f`.

Therefore the mismatch is not explained by Market Context input drift,
Portfolio Context drift, competitor-set drift, or Opportunity Quality drift.

## 2022-10-03 Full Decision Trace

Fresh-run `2022-10-03` canonical decision evidence:

- Regime state: `BEAR`
- Market Quality: `SHORT_TERM_BREADTH_BREAKDOWN`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Portfolio Policy reason codes: `RISK_PACING_CAUTIOUS`
- Cash competitor preference: `OPTIONALITY_ELEVATED`
- Valid deployable competitors: 22
- Opportunity Quality distribution: `COMPARABLE_MARGINAL:22`
- Canonical cash evidence consumed: `true`
- Canonical opportunity quality consumed: `true`
- Authoritative risk pacing consumed: `true`
- Legacy late risk-pacing authority count: 0
- Legacy cash winner override count: 0
- Canonical final capital winner: `CASH_OPTIONALITY`
- Winner reason codes:
  `CASH_PRE_FINAL_INTERACTION_WINNER`,
  `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`,
  `MARGINAL_OPPORTUNITY_SET`,
  `VALID_POLICY_RESERVE`

Every valid security competitor lost to Cash through
`market_candidate_cash_interaction.v1` with `interaction_result =
CASH_PREFERRED`. The binding matrix therefore executed and chose the expected
Cash winner.

Downstream evidence diverges from that winner:

- Position Sizing reported `positions_sized = 50`, `positions_withheld = 0`,
  and `total_target_weight = 0.479513`.
- Runtime Planning generated nine BUY plans:
  `94340 BUY_NEW 200`, `37820 BUY_NEW 400`, `93600 BUY_NEW 100`,
  `33700 BUY_NEW 100`, `83060 BUY_NEW 100`, `92420 BUY_NEW 100`,
  `58200 BUY_NEW 100`, `89180 BUY_NEW 3700`, `76470 BUY_NEW 1200`.
- Submit accepted seven BUY orders.
- Execution filled seven BUY orders:
  `93600 100`, `83060 100`, `94340 200`, `33700 100`, `89180 3700`,
  `37820 400`, `92420 100`.

Old-run `2022-10-03` filled the same seven BUY symbols and quantities. The
canonical PC decision changed, but the same-day order/fill surface did not.

## Holdings and Timing

The daily performance table is an end-of-day, post-fill current valuation view.
The `current_valuation_manifest.json` uses the runtime-owned execution ledger,
same-date valuation quotes, and a `last_execution_date` of the current business
date where fills occurred. It does not display a start-of-day pre-decision
holding set.

On `2022-10-03`, the visible holdings did not come from pre-existing open
campaigns: pre-action open campaign count was 0. The seven visible holdings
were same-day incremental BUY fills, so the lack of visible divergence on
`2022-10-03` is not explained by legacy holdings masking a correct Cash winner.

The first visible end-of-day holding divergence appears on `2022-10-28`:

- Fresh holdings include `94320` with 300 shares.
- Old holdings include `94320` with 500 shares.
- Other first-divergence holdings are otherwise aligned:
  `45760 100`, `60480 200`, `69730 100`, `69930 300`, `73680 100`,
  `92270 100`, `94340 400`, `99840 100`.

## Subsequent G48 Checkpoints

### 2022-10-20 Strong Exception

- Market Quality: `CONFLICTED_MARKET_STRUCTURE`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Canonical PC winner: `NEW_BUY 44490`
- Opportunity distribution: `STRONG:2`, `COMPARABLE_MARGINAL:21`,
  `BLOCKED:1`
- Reason codes:
  `CAUTIOUS_STRONG_SELECTIVE`,
  `SECURITY_PRE_FINAL_INTERACTION_WINNER`,
  `STRONG_CAN_OVERRIDE_CAUTION`
- Actual BUY fills: `69930 BUY 400`, `66630 BUY 100`

The strong exception executed at the PC interaction layer, but the PC winner was
not the actual filled BUY winner.

### 2022-10-25 Release and Redeployment

- Market Quality: `RECOVERY_CONFIRMATION_INCOMPLETE`
- Risk Pacing: `GRADUAL_REDEPLOYMENT`
- Canonical PC winner: `NEW_BUY 69730`
- Opportunity distribution: `COMPARABLE_HIGH:1`, `COMPARABLE_MARGINAL:25`,
  `BLOCKED:1`
- Reason codes:
  `GRADUAL_COMPARABLE_HIGH_SELECTIVE`,
  `GRADUAL_SELECTIVE_REDEPLOY`,
  `SECURITY_PRE_FINAL_INTERACTION_WINNER`
- Actual BUY fills: `69730 BUY 100`, `93180 BUY 6500`

The release and redeployment condition is confirmed. The fill of `69730`
matches the PC winner, but the additional `93180` fill shows the downstream path
is not winner-exclusive.

### 2022-10-27 Re-Brake

- Market Quality: `CONFLICTED_MARKET_STRUCTURE`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Canonical PC winner: `CASH_OPTIONALITY`
- Valid opportunity distribution: `COMPARABLE_MARGINAL:18`, `BLOCKED:1`
- Actual BUY fills: `27210 BUY 100`, `60480 BUY 200`

The re-brake is confirmed at the PC decision layer but again did not suppress
downstream BUY fills.

## Common-Date Fresh-Run Binding Counts

Across the 50 common completed dates inspected:

- Fresh canonical PC Cash wins against valid securities: 368
- Fresh canonical PC security wins: 25
- Fresh caution strong security wins: 9
- Fresh PC winner-day distribution:
  `CASH_OPTIONALITY:25`, `NEW_BUY:25`
- Old BUY plan count: 198
- Fresh BUY plan count: 196
- Old BUY fill count: 83
- Fresh BUY fill count: 77

The fresh canonical PC policy is active and non-sticky: it both brakes to Cash
and later releases to security winners. But actual order/fill suppression is
not a clean consequence of the canonical final winner because `2022-10-03`,
`2022-10-20`, and `2022-10-27` all show PC winner decisions not binding the
actual BUY order/fill set.

## Prediction Classification

- First brake `2022-10-03`: `SEMANTICALLY_CORRECT_BUT_VISIBLE_LATER`
- First release `2022-10-25`: `EXACT`
- First redeployment `2022-10-25`: `EXACT`
- First re-brake `2022-10-27`: `EXACT`

The classifications are exact at the PC authority layer. The first brake is
marked semantically correct but visible later because the immediate visible
portfolio path did not honor the Cash winner.

## Root Cause

`PRIMARY_MISMATCH_ROOT_CAUSE = RUNTIME_CONNECTIVITY_DEFECT`

Secondary explanations:

- `DAILY_OUTPUT_TIMING_MISINTERPRETATION` explains why a user-visible daily row
  can lag a decision-path analysis, but it does not explain same-day BUY fills
  after a Cash winner.
- `G48_DECISION_LOCAL_RECONSTRUCTION_LIMITATION` is not the primary cause here:
  G48 reconstructed the `2022-10-03` current-policy PC decision correctly from
  equivalent PIT inputs.

The current defect is narrower and more concrete: canonical PC final winner
lineage is present, but the executable Position Sizing / Runtime Planning
intent path still admits BUY quantities that should have lost to Cash.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G49_FRESH_RUN_RUNTIME_BINDING_CONNECTIVITY_DEFECT_FOUND`

`FRESH_RUN_ID = runtime-test-historical-extended-smoke-20260823T092537838492Z`

`COMPARISON_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`FRESH_RUN_EVIDENCE_COVERAGE_COMPLETE = YES`

`ACTUAL_FIRST_AUTHORITATIVE_DECISION_DIVERGENCE_DATE = 2022-10-03`

`ACTUAL_FIRST_ORDER_INTENT_DIVERGENCE_DATE = 2022-11-09`

`ACTUAL_FIRST_FILLED_PORTFOLIO_DIVERGENCE_DATE = 2022-10-28`

`FRESH_2022_10_03_TRACE_COMPLETE = YES`

`G48_FRESH_MARKET_INPUT_EQUIVALENCE = IDENTICAL`

`G48_FRESH_PORTFOLIO_CONTEXT_EQUIVALENCE = IDENTICAL`

`G48_FRESH_COMPETITOR_SET_EQUIVALENCE = IDENTICAL`

`G48_FRESH_OPPORTUNITY_QUALITY_EQUIVALENCE = IDENTICAL`

`G48_RECONSTRUCTION_FIDELITY = HIGH`

`FRESH_2022_10_03_CASH_COMPETITOR_PRESENT = YES`

`FRESH_2022_10_03_CASH_PREFERENCE = OPTIONALITY_ELEVATED`

`FRESH_2022_10_03_CANONICAL_WINNER = CASH_OPTIONALITY`

`FRESH_G43_BINDING_MATRIX_EXECUTED = YES`

`LEGACY_LATE_RISK_PACING_USED_AS_AUTHORITY = NO`

`FRESH_2022_10_03_VALID_SECURITY_COMPETITOR_COUNT = 22`

`FRESH_2022_10_03_SECURITIES_LOST_TO_CASH_COUNT = 22`

`FRESH_2022_10_03_VISIBLE_HOLDINGS_FROM_PREEXISTING_POSITIONS_COUNT = 0`

`FRESH_2022_10_03_NEW_INCREMENTAL_BUY_FILL_COUNT = 7`

`OLD_2022_10_03_INCREMENTAL_BUY_FILL_COUNT = 7`

`DAILY_TABLE_HOLDINGS_TIMING = END_OF_DAY_POST_FILL_CURRENT_VALUATION`

`FIRST_VISIBLE_HOLDING_DIVERGENCE_DATE = 2022-10-28`

`FIRST_VISIBLE_HOLDING_DIVERGENCE_DETAILS = 94320 fresh 300 shares vs old 500 shares`

`FRESH_2022_10_20_RISK_PACING = CAUTIOUS_DEPLOYMENT`

`FRESH_2022_10_20_STRONG_OPPORTUNITY_PRESENT = YES`

`FRESH_2022_10_20_SECURITY_WINNER = 44490`

`FRESH_2022_10_20_STRONG_EXCEPTION_EXECUTED = YES`

`FRESH_2022_10_25_POLICY_RELEASE_CONFIRMED = YES`

`FRESH_2022_10_25_REDEPLOYMENT_CONFIRMED = YES`

`FRESH_2022_10_27_REBRAKE_CONFIRMED = YES`

`FRESH_2022_10_27_CANONICAL_WINNER = CASH_OPTIONALITY`

`G48_FIRST_BRAKE_PREDICTION_CLASS = SEMANTICALLY_CORRECT_BUT_VISIBLE_LATER`

`G48_FIRST_RELEASE_PREDICTION_CLASS = EXACT`

`G48_FIRST_REDEPLOYMENT_PREDICTION_CLASS = EXACT`

`G48_FIRST_REBRAKE_PREDICTION_CLASS = EXACT`

`REFINED_POLICY_CONNECTED_BUT_G48_APPROXIMATION_DIFFERED = NO`

`REFINED_POLICY_RUNTIME_CONNECTIVITY_DEFECT = YES`

`FRESH_RUN_CASH_WIN_AGAINST_VALID_SECURITY_COUNT = 368`

`FRESH_RUN_SECURITY_WIN_COUNT = 25`

`FRESH_RUN_STRONG_EXCEPTION_COUNT = 9`

`OLD_INCREMENTAL_SECURITY_WIN_COUNT = 198`

`FRESH_INCREMENTAL_SECURITY_WIN_COUNT = 196`

`REFINED_POLICY_ACTUALLY_SUPPRESSES_INCREMENTAL_DEPLOYMENT = NO`

`FRESH_RUN_ACTUAL_CASH_TO_SECURITY_RELEASE_OBSERVED = YES`

`FIRST_FRESH_ACTUAL_RELEASED_SECURITY_WIN_DATE = 2022-10-25`

`FRESH_RUN_ACTUAL_REBRAKE_OBSERVED = YES`

`FIRST_FRESH_ACTUAL_REBRAKE_DATE = 2022-10-27`

`FRESH_RUN_PERMANENT_CASH_TRAP = NO`

`FRESH_CAUTION_STRONG_SECURITY_WIN_COUNT = 9`

`FRESH_BLANKET_MARKET_SHUTDOWN = NO`

`FRESH_POLICY_CHANGES_CASH_EXPOSURE_PATH = YES`

`FIRST_CASH_EXPOSURE_DIVERGENCE_DATE = 2022-10-28`

`PNL_USED_AS_CONNECTIVITY_EVIDENCE = NO`

`OUTCOME_USED_FOR_CAUSALITY = NO`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_DECISION_INPUT_COUNT = 0`

`PAPER_LEDGER_DECISION_INPUT_COUNT = 0`

`AUDIT_RESULT_DECISION_INPUT_COUNT = 0`

`EVIDENCE_ARTIFACT_AS_STRATEGY_DATA_SOURCE_COUNT = 0`

`PRIMARY_MISMATCH_ROOT_CAUSE = RUNTIME_CONNECTIVITY_DEFECT`

`FRESH_RUN_POLICY_INTEGRITY_JUDGMENT = FRESH_RUN_REFINED_POLICY_CONNECTIVITY_DEFECT_FOUND`

`CURRENT_FRESH_RUN_RECOMMENDATION = STOP_CURRENT_FRESH_RUN_FOR_CONNECTIVITY_REPAIR`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION = PHASE31_G50_FINAL_CAPITAL_WINNER_TO_POSITION_SIZING_RUNTIME_PLANNING_CONNECTIVITY_REPAIR`
