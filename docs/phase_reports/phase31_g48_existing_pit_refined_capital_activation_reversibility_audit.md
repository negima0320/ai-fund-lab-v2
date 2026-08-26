# Phase31-G48 — Existing PIT Refined Capital Activation / Reversibility Audit

Task type: READ-ONLY EXISTING-PIT REAL-MARKET CHARACTERIZATION.

No production code, Strategy, Market Context, Portfolio Policy, Portfolio Construction, Opportunity Quality, Cash competition, ADD / Re-entry / lot, Runtime, config, threshold, parameter, or fixture changes were made. No fresh-run, resume, replay, Historical rerun, or long Historical was executed.

## Judgment

`PRIMARY_JUDGMENT = PHASE31_G48_REAL_PIT_ACTIVATION_AND_POLICY_REVERSIBILITY_CONFIRMED_FRESH_RUN_READY`

Using only completed business dates from `runtime-test-historical-extended-smoke-20260822T174358377089Z`, the current G40-G47 refined capital competition semantics do bind on real PIT evidence. The old run's old capital decision outputs were used only as a comparison baseline for divergence, not as current policy. The current policy was evaluated from contemporaneous PIT inputs/artifacts.

The first real activation occurs on `2022-10-03`: old planning produced BUY orders, while current refined semantics would prefer Cash over 22 valid `COMPARABLE_MARGINAL` opportunities because Market Quality was `SHORT_TERM_BREADTH_BREAKDOWN` and Risk Pacing was `CAUTIOUS_DEPLOYMENT`.

## Source Window

- Source run: `runtime-test-historical-extended-smoke-20260822T174358377089Z`
- Completed source-run dates used: `2022-10-03` through `2023-07-28`
- Evaluable completed dates: 203
- Missing required PIT dates: 0
- Non-completed `2023-07-31` directory was excluded because it is not in `run_state.json.completed_business_days`.

## Method

For each completed date, the audit read existing PIT artifacts:

- `strategy/market_context.json`
- `strategy/portfolio_policy.json`
- `strategy/portfolio_construction.json`
- `strategy/runtime_planning.json` only for old-policy comparison

Because the source run predates G40-G47, the old `portfolio_construction.json` does not contain `capital_competition`. The audit therefore re-evaluated current semantics read-only from same-date PIT inputs:

1. Recomputed Market Quality from the stored PIT Market Context metrics using current `market_context._market_quality_from_context`.
2. Recomputed authoritative Risk Pacing from that Market Quality using current `portfolio_policy._risk_pacing_from_policy_context`.
3. Recomputed current capital competition from old PIT `portfolio_members` using current `portfolio_construction.build_capital_competition_framework`.
4. Compared the current deploy/no-deploy semantics against old same-date Runtime Planning BUY decisions without simulating later portfolio state.

No later price, return, regime, PnL, paper ledger outcome, audit result, or test result was used as a decision input.

## Real PIT Activation Counts

| Measure | Count |
|---|---:|
| Business days | 203 |
| Valid security competitors | 4,622 |
| Security wins | 77 |
| Cash wins against valid securities | 868 |
| Hard-failure-only Cash-win days | 0 |
| `STRONG` competitors | 66 |
| `COMPARABLE_HIGH` competitors | 150 |
| `COMPARABLE_MARGINAL` competitors | 4,406 |
| `WEAK_VALID` competitors | 0 |
| `INSUFFICIENT` competitors | 15 |
| `BLOCKED` competitors | 33 |

Risk Pacing distribution:

| Risk Pacing | Days |
|---|---:|
| `CAUTIOUS_DEPLOYMENT` | 125 |
| `GRADUAL_REDEPLOYMENT` | 36 |
| `NORMAL_DEPLOYMENT` | 42 |

Market Quality distribution:

| Market Quality | Days |
|---|---:|
| `SHORT_TERM_BREADTH_BREAKDOWN` | 45 |
| `CONFLICTED_MARKET_STRUCTURE` | 69 |
| `RECOVERY_CONFIRMATION_INCOMPLETE` | 36 |
| `HEALTHY_EXPANSION` | 41 |
| `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH` | 11 |
| `HEALTHY_RECOVERY` | 1 |

## Key Event Trace

### First Brake / First Cash Win / First Divergence

- Date: `2022-10-03`
- Regime: `BEAR`
- Market Quality: `SHORT_TERM_BREADTH_BREAKDOWN`
- Market Quality reasons: `MARKET_QUALITY_FRAGILE`, `SHORT_TERM_PARTICIPATION_NARROWING`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Valid opportunities: 22 `COMPARABLE_MARGINAL`
- Current winner: `CASH_OPTIONALITY`
- Current reason codes: `CASH_PRE_FINAL_INTERACTION_WINNER`, `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`, `MARGINAL_OPPORTUNITY_SET`, `VALID_POLICY_RESERVE`
- Old BUY symbols on same date: `94340`, `37820`, `93600`, `33700`, `83060`, `92420`, `58200`, `89180`, `76470`
- Ex-ante rationality: `SUPPORTED`

### First Policy Release

- Date: `2022-10-25`
- Release from: `2022-10-24` `CAUTIOUS_DEPLOYMENT` / `CONFLICTED_MARKET_STRUCTURE` / `RANGE`
- Release to: `2022-10-25` `GRADUAL_REDEPLOYMENT` / `RECOVERY_CONFIRMATION_INCOMPLETE` / `RECOVERY`
- Ex-ante rationality: `SUPPORTED`

### First Redeployment Eligibility

- Date: `2022-10-25`
- Opportunity type: `NEW_BUY`
- Symbol: `69730`
- Opportunity Quality distribution: `COMPARABLE_HIGH:1`, `COMPARABLE_MARGINAL:25`, `BLOCKED:1`
- Risk Pacing: `GRADUAL_REDEPLOYMENT`
- Current winner: `NEW_BUY 69730`
- Reason codes: `GRADUAL_COMPARABLE_HIGH_SELECTIVE`, `GRADUAL_SELECTIVE_REDEPLOY`, `SECURITY_PRE_FINAL_INTERACTION_WINNER`
- Ex-ante rationality: `SUPPORTED`

### First Re-brake

- Date: `2022-10-27`
- Regime: `BULL`
- Market Quality: `CONFLICTED_MARKET_STRUCTURE`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Valid opportunities: 18 `COMPARABLE_MARGINAL`
- Current winner: `CASH_OPTIONALITY`
- Reason codes: `CASH_PRE_FINAL_INTERACTION_WINNER`, `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`, `MARGINAL_OPPORTUNITY_SET`, `VALID_POLICY_RESERVE`
- Ex-ante rationality: `SUPPORTED`

### First Strong Exception

- Date: `2022-10-20`
- Regime: `RANGE`
- Market Quality: `CONFLICTED_MARKET_STRUCTURE`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`
- Current winner: `NEW_BUY 44490`
- Opportunity Quality distribution: `STRONG:2`, `COMPARABLE_MARGINAL:21`, `BLOCKED:1`
- Reason codes: `CAUTIOUS_STRONG_SELECTIVE`, `SECURITY_PRE_FINAL_INTERACTION_WINNER`, `STRONG_CAN_OVERRIDE_CAUTION`
- Strong exception count: 22 days
- Ex-ante rationality: `SUPPORTED`

## Activation Characteristics

- Real PIT binding surface reached: `YES`
- First real Cash win date: `2022-10-03`
- First expected economic divergence date: `2022-10-03`
- First divergence type: `CASH_INSTEAD_OF_NEW_BUY`
- Brake -> release -> redeployment eligibility sequence: `PASS`
- Re-brake sequence: `PASS`
- BULL weak-internals brake count: 39
- First BULL weak-internals brake: `2022-10-27`
- BEAR strong opportunity deploy count: 0
- GRADUAL vs CAUTIOUS binding difference observed: `YES`

The GRADUAL/CAUTIOUS difference is visible in real PIT competitors: `COMPARABLE_HIGH` is `SELECTIVE_COMPETITION` under `GRADUAL_REDEPLOYMENT` but often Cash-preferred under `CAUTIOUS_DEPLOYMENT`; `STRONG` remains eligible under restrictive conditions, confirming this is not a blanket shutdown.

## NEW / ADD / Re-entry / Lot

| Path | Cash wins | Security wins | Limitation |
|---|---:|---:|---|
| NEW_BUY | 2,823 | 77 | Decision-local; no full counterfactual portfolio path claimed |
| ADD | 11 | 0 | ADD source evidence exists but becomes less reliable after divergence because the true new portfolio would differ |
| Re-entry | 0 | 0 | No explicit re-entry competitor type is represented by the current PC competitor taxonomy in this old run |
| Lot reconsideration cases | 183 | 73 to security / 110 to Cash | Decision-local only |

## Monthly Characterization

| Month | BD | Non-normal Risk Days | Top Opportunity Classes | Cash Wins vs Valid | Security Wins | Strong Exceptions | Brake Days | Releases |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| 2022-10 | 20 | 19 | `COMPARABLE_MARGINAL:454`, `BLOCKED:12`, `STRONG:9`, `COMPARABLE_HIGH:8` | 169 | 6 | 2 | 14 | 3 |
| 2022-11 | 20 | 13 | `COMPARABLE_MARGINAL:406`, `COMPARABLE_HIGH:22`, `BLOCKED:13`, `STRONG:11` | 68 | 11 | 2 | 9 | 4 |
| 2022-12 | 22 | 22 | `COMPARABLE_MARGINAL:505`, `COMPARABLE_HIGH:38`, `STRONG:12`, `INSUFFICIENT:1` | 131 | 10 | 6 | 12 | 1 |
| 2023-01 | 19 | 13 | `COMPARABLE_MARGINAL:450`, `COMPARABLE_HIGH:15`, `STRONG:3` | 141 | 7 | 1 | 12 | 2 |
| 2023-02 | 19 | 17 | `COMPARABLE_MARGINAL:381`, `COMPARABLE_HIGH:14`, `STRONG:8`, `INSUFFICIENT:3` | 72 | 8 | 6 | 11 | 1 |
| 2023-03 | 22 | 16 | `COMPARABLE_MARGINAL:478`, `COMPARABLE_HIGH:4`, `INSUFFICIENT:1`, `STRONG:1` | 72 | 7 | 1 | 15 | 4 |
| 2023-04 | 20 | 13 | `COMPARABLE_MARGINAL:415`, `COMPARABLE_HIGH:6`, `STRONG:1` | 53 | 7 | 0 | 12 | 3 |
| 2023-05 | 20 | 17 | `COMPARABLE_MARGINAL:401`, `COMPARABLE_HIGH:9`, `STRONG:5`, `INSUFFICIENT:1` | 45 | 3 | 0 | 16 | 3 |
| 2023-06 | 22 | 14 | `COMPARABLE_MARGINAL:518`, `COMPARABLE_HIGH:14`, `BLOCKED:6`, `STRONG:3` | 49 | 9 | 0 | 12 | 3 |
| 2023-07 | 19 | 17 | `COMPARABLE_MARGINAL:398`, `COMPARABLE_HIGH:20`, `STRONG:13` | 68 | 9 | 4 | 10 | 2 |

## Pre/Post March Characterization

| Period | BD | Risk Pacing | Market Quality | Cash Wins vs Valid | Security Wins | Strong Exception Days |
|---|---:|---|---|---:|---:|---:|
| 2022-10-03 through 2023-02-28 | 100 | `CAUTIOUS:72`, `GRADUAL:12`, `NORMAL:16` | `CONFLICTED:49`, `SHORT_TERM_BREADTH_BREAKDOWN:19`, `HEALTHY_EXPANSION:16`, `RECOVERY_INCOMPLETE:12`, `SHORT_TERM_NARROWING:4` | 581 | 42 | 17 |
| 2023-03-01 through 2023-07-28 | 103 | `CAUTIOUS:53`, `GRADUAL:24`, `NORMAL:26` | `SHORT_TERM_BREADTH_BREAKDOWN:26`, `HEALTHY_EXPANSION:25`, `RECOVERY_INCOMPLETE:24`, `CONFLICTED:20`, `SHORT_TERM_NARROWING:7`, `HEALTHY_RECOVERY:1` | 287 | 35 | 5 |

This comparison is decision-local only. It does not use monthly profitability and does not tune semantics.

## Ex-Ante Judgment Freeze

Before any later outcome review:

- First brake judgment: `SUPPORTED`
- First release judgment: `SUPPORTED`
- First redeployment eligibility judgment: `SUPPORTED`
- First re-brake judgment: `SUPPORTED`
- Strong exception judgment: `SUPPORTED`

Secondary outcome description: `NOT_EVALUATED`. Outcome was not used for parameter or threshold selection.

## Fresh-Run Expectations

Pre-registered, non-profitability expectations for a same-condition fresh-run:

- Expected first activation: around `2022-10-03`, with Cash preferred over marginal NEW_BUY opportunities under restrictive Risk Pacing.
- Expected first policy release: around `2022-10-25`, `CAUTIOUS_DEPLOYMENT` to `GRADUAL_REDEPLOYMENT`.
- Expected redeployment-eligible window: around `2022-10-25`, with `COMPARABLE_HIGH`/better securities able to beat Cash.
- Expected re-brake: around `2022-10-27`, when BULL regime remains internally conflicted and marginal opportunities lose to Cash.
- Expected incremental Cash behavior: materially higher Cash optionality versus the old run, especially for `COMPARABLE_MARGINAL` opportunities in `CAUTIOUS_DEPLOYMENT` or `GRADUAL_REDEPLOYMENT`.

The subsequent fresh-run comparison must compare first actual divergence date, Cash winner count, security winner count, Opportunity Quality distribution, Risk Pacing distribution, exposure/Cash trajectory, ADD/Re-entry behavior, lot reconsideration, brake/release/redeployment/re-brake, avoidable-loss characteristics, winner retention, and final performance. Profitability remains an evaluation result, not a retroactive parameter-selection source.

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G48_REAL_PIT_ACTIVATION_AND_POLICY_REVERSIBILITY_CONFIRMED_FRESH_RUN_READY`

`SOURCE_RUN_ID = runtime-test-historical-extended-smoke-20260822T174358377089Z`

`SEARCH_START_DATE = 2022-10-03`

`SEARCH_END_DATE = 2023-07-28`

`PIT_SOURCE_COVERAGE_COMPLETE = YES`

`MISSING_REQUIRED_PIT_DATE_COUNT = 0`

`CURRENT_POLICY_DAILY_TIMELINE_COMPLETE = YES`

`REAL_PIT_STRONG_COUNT = 66`

`REAL_PIT_COMPARABLE_HIGH_COUNT = 150`

`REAL_PIT_COMPARABLE_MARGINAL_COUNT = 4406`

`REAL_PIT_WEAK_VALID_COUNT = 0`

`REAL_PIT_INSUFFICIENT_COUNT = 15`

`REAL_PIT_BLOCKED_COUNT = 33`

`REAL_PIT_BINDING_SURFACE_REACHED = YES`

`FIRST_REAL_PIT_CASH_WIN_DATE = 2022-10-03`

`FIRST_REAL_PIT_CASH_WIN_SYMBOL = CASH_OPTIONALITY`

`FIRST_REAL_PIT_CASH_WIN_OPPORTUNITY_TYPE = NEW_BUY`

`FIRST_REAL_PIT_CASH_WIN_OPPORTUNITY_QUALITY = COMPARABLE_MARGINAL`

`FIRST_REAL_PIT_CASH_WIN_RISK_PACING = CAUTIOUS_DEPLOYMENT`

`FIRST_REAL_PIT_CASH_WIN_MARKET_QUALITY = SHORT_TERM_BREADTH_BREAKDOWN`

`FIRST_REAL_PIT_CASH_WIN_REASON_CODES = CASH_PRE_FINAL_INTERACTION_WINNER; CAUTIOUS_MARKET_OPTIONALITY_ELEVATED; MARGINAL_OPPORTUNITY_SET; VALID_POLICY_RESERVE`

`FIRST_EXPECTED_ECONOMIC_DIVERGENCE_DATE = 2022-10-03`

`FIRST_DIVERGENCE_TYPE = CASH_INSTEAD_OF_NEW_BUY`

`FIRST_BRAKE_DATE = 2022-10-03`

`FIRST_POLICY_RELEASE_DATE = 2022-10-25`

`RELEASE_FROM_STATE = CAUTIOUS_DEPLOYMENT`

`RELEASE_TO_STATE = GRADUAL_REDEPLOYMENT`

`RELEASE_MARKET_QUALITY_CHANGE = CONFLICTED_MARKET_STRUCTURE_TO_RECOVERY_CONFIRMATION_INCOMPLETE`

`FIRST_REDEPLOYMENT_ELIGIBLE_DATE = 2022-10-25`

`REDEPLOYMENT_OPPORTUNITY_TYPE = NEW_BUY`

`REDEPLOYMENT_SYMBOL = 69730`

`REDEPLOYMENT_OPPORTUNITY_QUALITY = COMPARABLE_HIGH`

`REDEPLOYMENT_RISK_PACING = GRADUAL_REDEPLOYMENT`

`FIRST_REBRAKE_DATE = 2022-10-27`

`FIRST_REBRAKE_RISK_PACING = CAUTIOUS_DEPLOYMENT`

`FIRST_REBRAKE_MARKET_QUALITY = CONFLICTED_MARKET_STRUCTURE`

`REAL_PIT_BRAKE_RELEASE_REDEPLOY_SEQUENCE = PASS`

`REAL_PIT_REBRAKE_SEQUENCE = PASS`

`REAL_PIT_STRONG_EXCEPTION_COUNT = 22`

`FIRST_REAL_PIT_STRONG_EXCEPTION_DATE = 2022-10-20`

`BULL_WEAK_INTERNALS_REAL_BRAKE_COUNT = 39`

`FIRST_BULL_WEAK_INTERNALS_BRAKE_DATE = 2022-10-27`

`BEAR_STRONG_OPPORTUNITY_DEPLOY_COUNT = 0`

`FIRST_BEAR_STRONG_DEPLOY_DATE = NONE`

`REAL_GRADUAL_CAUTION_BINDING_DIFFERENCE_OBSERVED = YES`

`VALID_SECURITY_COMPETITOR_COUNT = 4622`

`SECURITY_WIN_COUNT = 77`

`CASH_WIN_AGAINST_VALID_SECURITY_COUNT = 868`

`HARD_FAILURE_ONLY_CASH_WIN_COUNT = 0`

`CASH_TRUE_COMPETITOR_REAL_PIT_CONFIRMED = YES`

`NEW_BUY_CASH_WIN_COUNT = 2823`

`NEW_BUY_SECURITY_WIN_COUNT = 77`

`ADD_CASH_WIN_COUNT = 11`

`ADD_SECURITY_WIN_COUNT = 0`

`REENTRY_CASH_WIN_COUNT = 0`

`REENTRY_SECURITY_WIN_COUNT = 0`

`REAL_PIT_LOT_RECONSIDERATION_CASE_COUNT = 183`

`REAL_PIT_LOT_TO_CASH_CASE_COUNT = 110`

`REAL_PIT_LOT_TO_SECURITY_CASE_COUNT = 73`

`MONTHLY_REAL_PIT_CHARACTERIZATION_COMPLETE = YES`

`PRE_POST_MARCH_DECISION_CHARACTERIZATION_COMPLETE = YES`

`FIRST_BRAKE_PIT_TRACE = PASS`

`FIRST_BRAKE_EX_ANTE_RATIONALITY = SUPPORTED`

`FIRST_RELEASE_PIT_TRACE = PASS`

`FIRST_RELEASE_EX_ANTE_RATIONALITY = SUPPORTED`

`FIRST_REDEPLOYMENT_PIT_TRACE = PASS`

`FIRST_REDEPLOYMENT_EX_ANTE_RATIONALITY = SUPPORTED`

`FIRST_REBRAKE_PIT_TRACE = PASS`

`FIRST_REBRAKE_EX_ANTE_RATIONALITY = SUPPORTED`

`EX_ANTE_JUDGMENTS_FROZEN_BEFORE_OUTCOME_REVIEW = YES`

`OUTCOME_USED_FOR_PARAMETER_SELECTION = NO`

`OUTCOME_USED_FOR_THRESHOLD_SELECTION = NO`

`G36_ZERO_ACTIVATION_DEFECT_REAL_PIT_RETESTED = YES`

`REAL_PIT_ECONOMIC_ACTIVATION = YES`

`REAL_PIT_POLICY_REVERSIBILITY = YES`

`REAL_PIT_REDEPLOYMENT_FEASIBILITY = YES`

`FRESH_RUN_BEHAVIOR_EXPECTATIONS_FROZEN = YES`

`SAME_CONDITION_FRESH_RUN_READY = YES`

`POST_G48_FRESH_RUN_COMPARISON_CONTRACT_DEFINED = YES`

`FULL_COUNTERFACTUAL_PORTFOLIO_PATH_CLAIMED = NO`

`OLD_RUN_DECISION_OUTPUT_USED_AS_CURRENT_POLICY = NO`

`CURRENT_G40_G47_SEMANTICS_EVALUATED_FROM_PIT_INPUTS = YES`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_DECISION_INPUT_COUNT = 0`

`PAPER_LEDGER_DECISION_INPUT_COUNT = 0`

`AUDIT_RESULT_DECISION_INPUT_COUNT = 0`

`TEST_RESULT_DECISION_INPUT_COUNT = 0`

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

`NEXT_TASK_RECOMMENDATION = SAME_CONDITION_USER_OPERATED_FRESH_RUN`
