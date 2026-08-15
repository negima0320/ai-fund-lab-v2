# Phase29-L21T-BB Post-AV Day1 BUY Funnel / Trajectory Distribution Audit

## Task

Phase29-L21T-BB

Mode: READ-ONLY audit.

Phase30 was not entered. Strategy, Runtime, Config, Model, and Threshold were not changed. No fresh-run, resume, replay, or recovery command was executed. The target run was not mutated.

## Target

- Run: `runtime-test-historical-extended-smoke-20260814T121822798037Z`
- Business date: `2022-08-10`

## Primary Judgment

`POST_AV_DAY1_ZERO_BUY_PRIMARY_CAUSE_MIXED_UNRESOLVED_FEATURE_PROPAGATION_GAP_PARTIAL_AV_CAUSAL`

The Day1 zero-BUY result is primarily explained by BUY Quality trajectory classification falling to `MIXED_OR_UNRESOLVED` for every BUY_NEW candidate. This was not because the classifier found actual `FADING_PRIOR_WINNER` or `RECENT_ACCELERATION_OVERHEAT`; both counts were zero. The evidence points to a feature propagation gap between generated runtime feature artifacts and the rows consumed by BUY Quality.

## Funnel Counts

| Metric | Count |
| --- | ---: |
| Universe rows | 4,165 |
| Universe eligible rows | 3,260 |
| Candidate count | 50 |
| Opportunity count | 50 |
| BUY_NEW considered | 50 |
| `HEALTHY_CONTINUATION` | 0 |
| `FADING_PRIOR_WINNER` | 0 |
| `RECENT_ACCELERATION_OVERHEAT` | 0 |
| `MIXED_OR_UNRESOLVED` | 50 |
| BUY_WAIT | 41 |
| BUY_ELIGIBLE | 0 |
| Adaptive Buy Quality passed | 0 |
| Portfolio Construction passed | 0 |
| Position Sizing positive quantity | 0 |
| Runtime Planning BUY_NEW | 0 |
| Submitted BUY | 0 |

Runtime outcome:

- `morning/planning_evidence.json`: `NO_ORDER_AUTHORIZED`
- `selected_symbols`: `[]`
- `plan_count`: `0`
- `submit_action`: `NO_SUBMISSION_REQUIRED`
- `submitted_count`: `0`

## Trajectory Distribution

All 50 BUY Quality decisions have:

```text
momentum_trajectory_classification = MIXED_OR_UNRESOLVED
```

No candidate reached a positive trajectory class:

- `HEALTHY_CONTINUATION`: 0
- `FADING_PRIOR_WINNER`: 0
- `RECENT_ACCELERATION_OVERHEAT`: 0

Therefore the zero-BUY day was not caused by successfully identifying and blocking only FADING or OVERHEAT names.

## BUY Quality Loss

BUY Quality action distribution:

```text
BUY_WAIT = 41
REJECT   = 9
```

Loss bucket distribution:

```text
trajectory BUY_WAIT: MIXED_OR_UNRESOLVED missing feature = 41
Buy Quality other rejection = 8
Expected Edge / Opportunity = 1
```

The 41 BUY_WAIT candidates all had non-momentum component statuses PASS:

- `execution_feasibility = PASS`
- `market_context_quality_modifier = PASS`
- `portfolio_fit = PASS`
- `relative_opportunity_quality = PASS`
- `signal_reliability = PASS`

This makes 41 the evidence-supported upper bound for "AV aside, otherwise BUY Quality component-pass candidates." It is not proof that all 41 would necessarily have submitted, because downstream PC/PS quantities were never reached with positive BUY eligibility.

## Feature Propagation Evidence

The actual runtime feature producer did materialize the AV columns into feature artifacts:

- `.runtime/operations/feature_artifacts/2022-08-10/candidate_features.parquet`
  - shape: `(4165, 40)`
  - all AV columns present
- `.runtime/operations/feature_artifacts/2022-08-10/opportunity_feature_input.parquet`
  - shape: `(4165, 42)`
  - all AV columns present

However, the row artifacts consumed by BUY Quality did not carry these raw feature fields:

| Artifact | Rows | AV / trajectory raw fields present in rows |
| --- | ---: | ---: |
| `.runtime/runtime_state/buy_ai/2022-08-10/candidate_decisions.json` | 50 | 0 |
| `.runtime/runtime_state/buy_ai/2022-08-10/opportunity_rankings.json` | 50 | 0 |
| `strategy/buy_quality_decisions.json` | 50 | 0 |

The missing fields observed by BUY Quality were:

- `momentum_trajectory_required_feature_missing:price_momentum_return_1d`
- `momentum_trajectory_required_feature_missing:price_momentum_return_3d`
- `momentum_trajectory_required_feature_missing:price_momentum_return_5d`
- `momentum_trajectory_required_feature_missing:volatility_return_std_20d`

This evidence supports a propagation gap from feature artifacts into BUY Quality input rows, not a market-refresh producer absence.

## Downstream Stages

Portfolio Construction:

- members: 50
- positive accepted BUY_NEW weight: 0
- pass count: 0

Position Sizing:

- positions: 50
- positive quantity: 0
- pass count: 0

Runtime Planning:

- `producer_result_status`: `PASS`
- `reason_codes`: `["portfolio_exclude_maps_to_no_plan"]`
- `plan_count`: 0

Submit:

- `submit_action`: `NO_SUBMISSION_REQUIRED`
- `submitted_count`: 0

## Required Questions

1. HEALTHY_CONTINUATION count:
   - 0.

2. HEALTHY candidates lost downstream:
   - 0, because no candidate was classified as `HEALTHY_CONTINUATION`.

3. MIXED_OR_UNRESOLVED that became BUY_WAIT:
   - 41.

4. FADING / OVERHEAT only blocking caused zero BUY:
   - NO. FADING and OVERHEAT counts were both 0.

5. MIXED_OR_UNRESOLVED conservative WAIT was the main zero-BUY cause:
   - YES. 41 candidates were blocked by MIXED/required-feature-missing BUY_WAIT before PC/PS could produce positive BUY_NEW.

6. AV aside, BUY possible candidates:
   - Evidence-supported upper bound: 41. These had non-momentum BUY Quality components PASS, but were stopped by trajectory BUY_WAIT.

## Interpretation

AV over-filtering is `PARTIAL`.

The AV WAIT contract did filter the BUY funnel to zero positive BUY eligibility, but not because the trajectory rules were too strict against real FADING or OVERHEAT names. The observed issue is that required trajectory inputs were missing at BUY Quality consumption time, forcing all 50 candidates into `MIXED_OR_UNRESOLVED`. The next repair should focus on feature propagation from candidate/opportunity feature artifacts into BUY Quality input rows, while preserving fail-closed semantics for truly missing features.

## Artifacts

- `reports/phase29_l21t_bb_post_av_day1_buy_funnel_trajectory_distribution_audit/summary.json`
- `reports/phase29_l21t_bb_post_av_day1_buy_funnel_trajectory_distribution_audit/per_candidate.csv`

## Validation

- Read-only artifact trace: PASS
- `summary.json` parse: PASS
- `git diff --check`: PASS
- Runtime mutated by Codex: NO
- Strategy changed by Codex: NO
- Phase30 entered: NO

## Next Step

Recommended next task:

`Phase29-L21T-BC - BUY Quality Multi-Horizon Feature Propagation Repair`

Scope: ensure BUY Quality receives PIT multi-horizon feature fields from production-common runtime artifacts, then rerun focused regression proving HEALTHY/FADING/OVERHEAT/MIXED classifications are produced from real inputs instead of missing-field fallback.
