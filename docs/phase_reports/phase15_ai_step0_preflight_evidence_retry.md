# Phase15-AI Step0 Preflight Evidence Retry

Date: 2026-07-10

## Objective

Phase15-AI re-runs Step0 Preflight Evidence Review after Phase15-AB through Phase15-AH.

This is not Morning execution. This phase checks only:

```text
Morningを安全に開始できる状態か
```

This phase did not run Morning, Submit, Execution, Broker Write, orders, notification real send, launchd, or Current edits.

## Scope

This retry separates two things that were mixed in Phase15-AA:

- Runtime connection readiness: whether Producer -> Artifact -> Consumer chains are now implemented.
- Operational preflight readiness: whether current Step0 evidence is fresh enough to begin Step1 Morning Review.

## Evidence Checked

- `configs/runtime_v2/capital_deployment.json`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/safety_decision.py`
- `.runtime/persistent_ledger/state.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/broker_readonly/2026-07-09/tachibana_snapshot.json`
- `reports/safety/phase11/`
- `docs/phase_reports/phase15_aa_step0_preflight_evidence_review.md`
- `docs/phase_reports/phase15_ah_decision_producer_consumer_closure_reaudit.md`

## Step0 Retry Evidence Matrix

| Evidence | Exists | Fresh | Runtime Path | Review Result | Gap |
|---|---:|---:|---|---|---|
| Capital Deployment Policy | YES | STATIC VALID | `configs/runtime_v2/capital_deployment.json` | PASS | Policy loads through `load_capital_deployment_policy`; `policy_source=configs/runtime_v2/capital_deployment.json`; validation status is `PASS`. Runtime jobs require explicit `--capital-deployment-policy`. |
| BUY AI Producer / Consumer | IMPLEMENTED | N/A BEFORE MORNING | `produce_buy_ai_decisions()` -> `.runtime/runtime_state/buy_ai/<business_date>/` -> Morning `ai_signals` | PASS FOR CONNECTION | No current-date BUY AI artifact exists yet, but it is generated inside the Morning regular path before Planning. Step1 must verify generated artifact and manifest. |
| SELL AI Producer / Consumer | IMPLEMENTED | N/A BEFORE SELL PLANNING | `produce_position_management_decisions()` -> `.runtime/runtime_state/position_management/<business_date>/` -> SELL Planning | PASS FOR CONNECTION | No current-date PM artifact exists yet. This is not a Step1 Morning blocker, but must be verified before SELL Planning. |
| Runtime Safety Evaluation | IMPLEMENTED | EVIDENCE MISSING | `safety_evaluation` job -> `reports/safety/phase11/<business_date>_safety_report.json` | GAP | Regular path exists, but no `2026-07-10` Phase11 Safety Report exists. Latest found report is `2026-06-29`. |
| Runtime Safety Decision | IMPLEMENTED | EVIDENCE MISSING | `safety_refresh` job -> `.runtime/runtime_state/safety/latest_safety_decision.json` | GAP | Safety producer exists and fails closed on missing/invalid source, but no latest Safety Decision artifact exists under `.runtime/runtime_state/safety/`. |
| Current SoT | YES | STALE / REVIEW_REQUIRED | `.runtime/persistent_ledger/state.json` | REVIEW_REQUIRED | Current exists; `environment=demo`, `source=runtime_v2_runtime_owned_fill_projection`, `as_of=2026-07-09`, `updated_at=2026-07-09`, `cash=140500.0`, `buying_power=140500.0`, positions count `5`. Freshness for 2026-07-10 Step1 is not established. |
| Pending State | YES | STALE / UNRESOLVED | `.runtime/pending_order_plan/pending_order_plan.json` | GAP | Pending is `APPROVED`, `target_session_date=2026-07-09`, item count `5`, and policy/safety context is missing. It must not be silently carried into a new Morning review. |
| Broker ReadOnly Snapshot | YES | STALE / INCOMPLETE | `.runtime/runtime_state/broker_readonly/2026-07-09/tachibana_snapshot.json` | REVIEW_REQUIRED | Snapshot exists, `generated_at=2026-07-09T02:12:50.369763+00:00`, broker mode `demo`, positions count `12`; `production_equivalent` and `review_required` are missing. |
| Runtime Root | YES | PARTIAL | `.runtime` | REVIEW_REQUIRED | Main roots exist for Current, Pending, Manifest, Broker ReadOnly, Feature artifacts, and Ledger. Safety and current-date BUY/SELL AI artifact roots are not yet populated. |
| Launchd | NOT USED | N/A | `tools/launchd/*.plist` | PASS WITH CAUTION | Acceptance remains manual. launchd must not be used for Step0 or Step1. |

## Policy Review

Observed policy:

```text
path=configs/runtime_v2/capital_deployment.json
policy_version=capital_deployment_v1
policy_source=configs/runtime_v2/capital_deployment.json
evaluation_capital=1000000
target_investment_ratio=0.85
cash_buffer=0.05
max_exposure=850000
max_position_weight=0.2
max_positions=5
max_buy_order_amount=null
max_sell_liquidation_amount=null
policy_validation_status=PASS
```

Result:

```text
PASS
```

Important note:

The policy is no longer named as a demo-only policy. This aligns with the Runtime Reality Rule from Phase15-X and the naming correction from Phase15-AB.

## BUY AI Review

Current regular path:

```text
Morning job
↓
produce_buy_ai_decisions()
↓
candidate_decisions.json
↓
opportunity_rankings.json
↓
Morning Planning via ai_signals
```

Manifest fields exist in the producer:

```text
candidate_model_version
candidate_artifact_path
candidate_count
opportunity_model_version
opportunity_artifact_path
opportunity_count
selected_rank_count
buy_ai_generated_at
```

Result:

```text
PASS_FOR_CONNECTION
```

No current-date BUY AI artifact exists before Morning because the regular Morning job is the producer. Therefore, Step1 must verify the generated artifact and manifest before any Morning PASS.

## SELL AI Review

Current regular path:

```text
sell_planning job
↓
produce_position_management_decisions()
↓
position_management_decisions.json
↓
SELL Planning via SellExitDecision
```

Manifest fields exist in the producer:

```text
pm_model_version
pm_inference_version
pm_feature_date
pm_artifact_path
pm_decision_count
pm_exit_count
pm_hold_count
pm_reduce_count
pm_add_count
pm_generated_at
```

Result:

```text
PASS_FOR_CONNECTION
```

No current-date Position Management artifact exists yet. This is not a Step1 Morning blocker, but it remains required before SELL Planning review.

## Safety Review

Implemented chain:

```text
safety_evaluation
↓
reports/safety/phase11/<business_date>_safety_report.json
↓
safety_refresh
↓
.runtime/runtime_state/safety/latest_safety_decision.json
↓
Morning / SELL / Submit
```

Static implementation result:

```text
PASS_FOR_CONNECTION
```

Current operational evidence result:

```text
GAP
```

Observed:

- No `.runtime/runtime_state/safety/latest_safety_decision.json`
- No `reports/safety/phase11/2026-07-10_safety_report.json`
- Latest inspected Safety Report was `reports/safety/phase11/2026-06-29_safety_report.json`

Safety is now connected, but Step1 Morning Review cannot start without fresh Safety Decision evidence or an explicit `REVIEW_REQUIRED` decision generated by the Safety regular path.

## Current Review

Observed:

```text
path=.runtime/persistent_ledger/state.json
asset_state_id=asset-a62d10da209fe038
environment=demo
source=runtime_v2_runtime_owned_fill_projection
as_of=2026-07-09
updated_at=2026-07-09
cash=140500.0
buying_power=140500.0
positions_count=5
review_required=false
```

Result:

```text
REVIEW_REQUIRED
```

Current exists and is in the fixed Current SoT path, but freshness for 2026-07-10 Step1 is not established.

## Pending Review

Observed:

```text
path=.runtime/pending_order_plan/pending_order_plan.json
status=APPROVED
target_session_date=2026-07-09
items_count=5
approval_status=APPROVED
approval_expires_at=2026-07-09T15:00:00+09:00
policy_version=null
policy_hash=null
safety_decision_id=null
```

Result:

```text
GAP
```

This stale Pending must not be silently consumed or carried into 2026-07-10 Step1. It requires explicit operator review and controlled resolution before Morning.

## Broker ReadOnly Review

Observed:

```text
path=.runtime/runtime_state/broker_readonly/2026-07-09/tachibana_snapshot.json
generated_at=2026-07-09T02:12:50.369763+00:00
broker_mode=demo
positions_count=12
production_equivalent=null
review_required=null
```

Result:

```text
REVIEW_REQUIRED
```

Broker ReadOnly snapshot exists, but it is not fresh for 2026-07-10 and lacks explicit Demo / Production boundary evidence fields.

## Runtime Root Review

The `.runtime` root contains:

- Current: `.runtime/persistent_ledger/state.json`
- Pending: `.runtime/pending_order_plan/pending_order_plan.json`
- Manifest: `.runtime/runtime_state/run_manifest/`
- Broker ReadOnly: `.runtime/runtime_state/broker_readonly/`
- Feature artifacts: `.runtime/operations/feature_artifacts/`

Missing or not current-date:

- `.runtime/runtime_state/safety/latest_safety_decision.json`
- `.runtime/runtime_state/buy_ai/2026-07-10/`
- `.runtime/runtime_state/position_management/2026-07-10/`
- `.runtime/runtime_state/broker_readonly/2026-07-10/`

Result:

```text
REVIEW_REQUIRED
```

## Step0 Retry Difference Review

| Evidence | Phase15-AA | Phase15-AI | Changed | Remaining Gap |
|---|---|---|---|---|
| Capital Deployment Policy | GAP: active Phase15 policy not found in acceptance path | PASS: `configs/runtime_v2/capital_deployment.json` loads and validates | Yes | Runtime CLI still requires explicit `--capital-deployment-policy`; omit it and policy becomes REVIEW_REQUIRED. |
| BUY AI | Not part of AA preflight closure | PASS_FOR_CONNECTION: Candidate -> Opportunity -> Morning connected | Yes | Current-date artifact must be verified during Step1 Morning; no pre-Morning artifact is expected. |
| SELL AI | Not part of AA preflight closure | PASS_FOR_CONNECTION: Position Management -> SELL Planning connected | Yes | Must be verified before SELL Planning; not a Step1 Morning blocker. |
| Safety Producer | GAP: `latest_safety_decision.json` missing and producer not accepted as connected | PASS_FOR_CONNECTION, GAP_FOR_EVIDENCE | Yes | Fresh Safety Report and latest Safety Decision are still missing. |
| Safety Evaluation | GAP: not connected to regular path | PASS_FOR_CONNECTION, GAP_FOR_EVIDENCE | Yes | `2026-07-10` Phase11 Safety Report not present. |
| Current | REVIEW_REQUIRED: 2026-07-09 stale | REVIEW_REQUIRED: still 2026-07-09 stale | No | Needs target-date freshness or explicit Safety REVIEW_REQUIRED classification. |
| Pending | GAP: stale APPROVED unconsumed Pending | GAP: same stale APPROVED Pending remains | No | Must be resolved or explicitly blocked before Step1 Morning. |
| Broker ReadOnly | REVIEW_REQUIRED: 2026-07-09 stale/incomplete | REVIEW_REQUIRED: same stale/incomplete evidence remains | No | Needs fresh snapshot or explicit broker evidence REVIEW_REQUIRED. |
| Runtime Root | REVIEW_REQUIRED: active Policy/Safety not connected in root | REVIEW_REQUIRED: root exists but Safety and 2026-07-10 evidence missing | Partial | Needs Safety Decision and fresh evidence roots. |
| Launchd | PASS_WITH_CAUTION | PASS_WITH_CAUTION | No | Continue manual Acceptance only. |

## Acceptance Judgment

```text
STEP0_RETRY_GAPS_FOUND
```

Reason:

- Runtime connection gaps from Phase15-AA are materially improved.
- Policy is now valid and Runtime Reality aligned.
- BUY AI and SELL AI regular-path connections are closed enough for Stepwise Acceptance.
- Safety Evaluation and Safety Producer are implemented, but current Safety evidence is still missing.
- Current is stale for the target review date.
- Pending has stale approved state from 2026-07-09 with no policy/safety context.
- Broker ReadOnly snapshot is stale and lacks explicit boundary evidence fields.

Step1 Morning Review is not ready yet.

## Operator Command Plan

Do not run Morning yet.

Because Safety is now connected but missing current evidence, request only these two commands first:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job safety_evaluation --business-date 2026-07-10 --runtime-root .runtime --capital-deployment-policy configs/runtime_v2/capital_deployment.json --notification-mode payload-only --stop-on-review-required
```

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job safety_refresh --business-date 2026-07-10 --runtime-root .runtime --capital-deployment-policy configs/runtime_v2/capital_deployment.json --notification-mode payload-only --stop-on-review-required
```

Expected outcome:

- If Current / Broker / Market / Runtime State evidence is stale or missing, Safety should produce `REVIEW_REQUIRED`, not `ALLOW`.
- That `REVIEW_REQUIRED` evidence is acceptable for Step0 review, but not for Step1 Morning PASS.

After these two commands, inspect only:

- `.runtime/runtime_state/safety/latest_safety_decision.json`
- `reports/safety/phase11/2026-07-10_safety_report.json`
- latest `safety_evaluation` / `safety_refresh` run manifests

Do not request a large command batch.

## Required Before Step1 Morning Review

Before Step1:

- Runtime Safety Decision must exist for the target business date.
- Safety must be unexpired and either `ALLOW` or explicit `REVIEW_REQUIRED` with reason.
- Stale Pending must be reviewed and must not be silently consumed.
- Current freshness must be accepted or explicitly classified.
- Broker ReadOnly freshness must be accepted or explicitly classified.
- Morning must be run manually, not via launchd.

## Prohibited Actions Confirmation

This phase did not perform:

- Morning execution
- Submit execution
- Execution run
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd use
- Current edit

## Final Judgment

```text
PHASE15AI_STEP0_PREFLIGHT_EVIDENCE_RETRY_COMPLETE
```
