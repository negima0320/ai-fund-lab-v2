# Phase32-GE Fresh Target Portfolio Dynamic SHADOW Validation Readiness / Acceptance Contract

## Objective

Define whether the Phase32-GD `fresh_target_portfolio_shadow.v1` implementation
is ready for real Historical decision-time dynamic SHADOW validation.

This phase did not promote Fresh Target to Production and did not change
Production Strategy, thresholds, weights, PM, PC target authority, Position
Sizing, Runtime, Pending, Submit, Execution, Safety, or broker behavior.

## Read-Only Confirmation

No fresh-run, resume, replay, recover, long Historical, runtime state mutation,
Pending mutation, Ledger mutation, accepted registry mutation, or Production
promotion was executed in GE.

GE created this readiness report only.

## Required Prior Reports Read

- `docs/phase_reports/phase32_fz_june_long_vs_fresh_same_day_portfolio_state_target_weight_legacy_divergence_read_only_audit.md`
- `docs/phase_reports/phase32_ga_long_vs_fresh_actual_buy_divergence_root_cause_decomposition_read_only_audit.md`
- `docs/phase_reports/phase32_gb_history_neutral_fresh_target_portfolio_authority_architecture_regression_invariant_design_audit.md`
- `docs/phase_reports/phase32_gc_fresh_target_portfolio_architecture_adversarial_regression_design_acceptance_review.md`
- `docs/phase_reports/phase32_gd_fresh_target_portfolio_non_authoritative_shadow_implementation_focused_acceptance.md`
- `docs/phase_reports/phase32_fq_capital_priority_architecture_regression_invariant_design_audit.md`
- `docs/phase_reports/phase32_fr_capital_priority_architecture_adversarial_regression_design_acceptance_review.md`
- `docs/phase_reports/phase32_fs_next_capital_unit_shadow_comparator_detailed_spec_preimplementation_design_review.md`

## Current Source / Authority Snapshot

Current source baseline read from `scripts/runtime_test.py`:

```text
source_commit = a8af2dacfb3c81015a069b40d53ff182cccb2542
source_dirty = True
registry_hash = 4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba
accepted_artifact_hash = 5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5
```

Current source hashes inspected:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py = 828f0fd88f885eddf8a12a735ac5b05e519bdef46f3f57e8c2e9b7e9166bca82
src/ai_fund_lab_v2/strategy/marginal_capital_value.py = 0fb86eb015070827d26f3a7920a9b4cd1d11cd3fcc0f1c5589d6c3f4cacaa28e
src/ai_fund_lab_v2/strategy/position_management.py = 1ff87fa136bc289db3c7c3b8e36e22d855eca68935598db4d07d0e3a3939ed23
```

The accepted registry hash is unchanged from the active baseline runs. GD is
non-authoritative SHADOW and does not require PM accepted-generation promotion.

## GD Runtime Materialization Readiness

Static/focused path confirms:

- `fresh_target_portfolio_shadow.v1` is embedded under PC capital competition;
- `authoritative_consumer_count = 0`;
- `action_authority = false`;
- `quantity_authority = false`;
- `order_authority = false`;
- Production PC competitors and winners remain unchanged in focused tests;
- Fresh Target rows contain `BUY_NEW_CONTEXT`, `BUY_ADD_CONTEXT`, and `CASH`;
- old ownership, closed campaign, prior ADD count, prior EXIT count, and average
  cost are not target inputs in focused fixtures;
- winner-protection conflict and terminal PM/Safety precedence are observable.

However, the current GD implementation does not yet materialize a real
run-scoped top-level `run_id` into the Fresh Target artifact. The builder
currently emits the `run_id` field, but its value is empty in the static source
path. This is a blocker for dynamic acceptance because GE explicitly requires
run-scoped evidence to prove:

- stale cross-run evidence is rejected;
- current run binding is present;
- long/fresh Fresh Target comparison is not accidentally mixing artifact roots.

Therefore:

```text
GD_RUNTIME_MATERIALIZATION_STATIC_PATH = PASS
GD_RUNTIME_RUN_SCOPED_BINDING = FAIL
DYNAMIC_SHADOW_VALIDATION_READY = NO
BLOCKING_GAP = fresh_target_portfolio_shadow.run_id_not_materialized
```

## Existing Active Run Compatibility

Observed Historical run states:

```text
runtime-test-historical-extended-smoke-20260904T112908488385Z
status = RUNNING
next_job = 2023-08-01:market_refresh
completed_count = 42
last_completed = 2023-07-31
baseline_source_commit = a8af2dacfb3c81015a069b40d53ff182cccb2542
baseline_source_dirty = True
registry_hash = 4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba
```

The run predates GD materialization. Sample existing PC artifacts contain
`unified_marginal_capital_shadow` but not `fresh_target_portfolio_shadow`.

Although the resume entry gate checks `source_commit`, `source_dirty`, and
`registry_hash`, the current run and current workspace are both
`source_dirty=True`; a dirty boolean alone is not sufficient to prove identical
source content across the pre-GD and post-GD dirty states. Resuming this active
run would mix pre-GD artifacts with post-GD source and would not create a clean
Fresh Target validation baseline.

```text
EXISTING_ACTIVE_RUN_RESUME_SAFE = NO_FOR_GE_VALIDATION
EXISTING_ACTIVE_RUN_OPERATOR_POLICY = DO_NOT_RESUME_EXISTING_RUN_FOR_FRESH_TARGET_DYNAMIC_ACCEPTANCE
```

## Baseline Comparison Contract

Dynamic validation may compare against:

```text
Long baseline:
runtime-test-historical-extended-smoke-20260903T213011268067Z

Previous fresh baseline:
runtime-test-historical-extended-smoke-20260904T112908488385Z
```

But those runs were produced before GD. Their PC artifacts must be treated as
Production/legacy comparison evidence only. They must not be treated as Fresh
Target artifacts.

Comparison rules:

- compare only identical business dates;
- do not compare a GD Fresh Target artifact to a pre-GD missing artifact as a
  Fresh Target failure;
- use pre-GD runs for candidate overlap, Production target, Production buy/fill,
  current holdings, campaign path dependence, and GA/FZ reproduction context;
- use only a new post-GD run for actual Fresh Target dynamic metrics.

## Recommended Validation Run Contract

Recommended after the run-scoped Fresh Target `run_id` binding is repaired:

```text
profile = historical-extended-smoke
start-date = 2023-06-01
business-days = 40
initial-cash = 1000000
```

Rationale:

- covers the GA/FZ June same-market divergence window;
- observes multiple weeks of winner/churn/stability behavior;
- is short enough to avoid long Historical optimization;
- does not select length from return/PnL outcome.

## Dynamic Metrics Contract

Per business date, materialize and evaluate:

- fresh target symbol count;
- Fresh Target weights;
- current Production target weights;
- overlap;
- target membership differences;
- target weight differences;
- current actual weights;
- semantic deltas;
- Production actions;
- SHADOW conflicts.

Primary long/fresh metric:

```text
LONG_FRESH_FRESH_TARGET_OVERLAP
```

If candidate overlap remains high but Fresh Target overlap is low, the Fresh
Target architecture has not sufficiently removed long/fresh path dependence.

## History Neutrality Metrics

Zero-tolerance actual dynamic metrics:

```text
old_ownership_target_penalty = 0
closed_campaign_target_leakage = 0
prior_add_count_target_suppression = 0
prior_exit_count_target_suppression = 0
average_cost_target_influence = 0
```

Recent EXIT guard is separated:

```text
recent_exit_guard_active_count
recent_exit_guard_released_count
recent_exit_guard_blocked_count
fresh_target_attractiveness_when_guarded
```

## Required Problem Case Coverage

The dynamic validation must include or explicitly report insufficient evidence
for:

- GA same-rank capitalization divergence;
- `67310` cycle;
- held-vs-flat asymmetry;
- target shrink plus PM HOLD / Winner Protection;
- prior ADD context;
- old campaign context;
- recent EXIT;
- Cash/marginal frontier.

For `67310`, trace:

- current PIT evidence;
- Production target;
- Fresh Target;
- current position state;
- campaign history display;
- recent exit guard;
- final SHADOW delta/conflict;
- proof that old BUY_NEW/EXIT cycles do not directly affect Fresh Target target.

## Winner Preservation Metrics

Required:

```text
WINNER_PREMATURE_EXIT_SIGNAL_COUNT
```

Definition: count Fresh Target rows where `fresh_target_weight <
current_actual_weight` while PM / Winner Protection has strong HOLD semantics.

This remains diagnostic only. No REDUCE/EXIT authority is created.

## Stability / Turnover Metrics

Required daily metrics:

- target enter count;
- target leave count;
- membership flip count;
- weight direction flip count;
- same-symbol target oscillation;
- target breadth delta.

Required turnover-pressure counts:

- `ACQUIRE`;
- `RETAIN`;
- `RELEASE`;
- `EXIT_CANDIDATE`;
- `BUY -> RELEASE -> BUY`;
- `RELEASE -> ACQUIRE`;
- repeated target flip.

## ADD / G129 / Safety Metrics

Required:

```text
ADD_SAFETY_BYPASS_COUNT = 0
G129_REGRESSION_COUNT = 0
```

For held securities where `fresh_target_weight > current_actual_weight`, classify
ADD safety as:

- ADD safety pass;
- ADD safety blocked;
- evidence incomplete;
- lot/headroom/concentration blocked.

The Fresh Target artifact must not treat a position-scope delta as Runtime
BUY_ADD order-increment authority.

## Cash Behavior Metrics

Daily Cash row validation:

- Cash Fresh Target status;
- cash target share;
- strong opportunity present;
- opportunity scarcity;
- risk context.

Detect:

- `CASH_BLANKET_DOMINANCE`;
- `CASH_COLLAPSE`.

Fresh Target must not become an exposure-maximization mechanism. Breadth,
marginal quality share, rank depth, and Cash target share must remain diagnostic.

## Production-vs-SHADOW Divergence Classes

Dynamic comparison must classify at least:

- `SAME`;
- `CURRENT_POSITION_PATH_DEPENDENCE`;
- `CAMPAIGN_HISTORY_SUPPRESSION`;
- `PC_TARGET_RELATIONSHIP`;
- `WINNER_PROTECTION_CONFLICT`;
- `ADD_SAFETY`;
- `RECENT_EXIT_GUARD`;
- `CASH_DIFFERENCE`;
- `OTHER`.

## Zero-Tolerance Acceptance Blockers

Any nonzero count blocks dynamic acceptance:

```text
runtime_authority_leak > 0
future_information_used > 0
stale_cross_run_evidence_accepted > 0
closed_campaign_target_leak > 0
permanent_history_penalty > 0
ADD_safety_bypass > 0
G129_regression > 0
campaign_identity_mismatch > 0
provenance_missing > 0
```

## Acceptance Classification

Dynamic SHADOW validation must classify:

- `ACCEPT`: all zero-tolerance blockers are zero, long/fresh Fresh Target overlap
  improves materially, winner/safety/cash contracts remain clean, and stability
  / turnover pressure is acceptable.
- `ACCEPT_WITH_DESIGN_FOLLOWUP`: zero-tolerance blockers are zero but target
  oscillation, winner conflicts, Cash behavior, or overlap metrics require more
  SHADOW design before Production consideration.
- `REVISE_SHADOW`: artifact schema/materialization is incomplete, metrics are
  missing, run binding is absent, or diagnostics cannot distinguish history,
  winner, ADD, safety, and cash reasons.
- `REJECT_ARCHITECTURE`: Fresh Target itself introduces persistent path
  dependence, authority leakage, future/outcome usage, or unacceptable
  unresolvable winner/churn/safety conflict.

PnL is not the primary acceptance criterion.

## Focused Validation Already Available

Focused validation from GD / GE working tree:

```text
tests/strategy/test_phase32_gd_fresh_target_portfolio_shadow.py = 7 passed
tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py
tests/strategy/test_phase32_ew_reentry_semantic_removal_recent_exit_guard.py
tests/runtime_v2/test_phase32_ez_recent_exit_guard_materialization.py
combined = 30 passed
G129 focused tests = 2 passed
```

These prove static/focused non-authoritative behavior but do not prove dynamic
actual runtime materialization because run-scoped Fresh Target `run_id` binding
is still missing.

## Legacy Artifact-Dependent Test Technical Debt

GD found an existing old-run artifact-dependent test:

```text
tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py::test_phase31_g113_actual_76470_add_shadow_is_lot_level_and_non_authoritative
```

It depends on:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-12-06/strategy/portfolio_construction.json
```

That file is no longer present after old artifact cleanup. This is separate from
Fresh Target acceptance. Technical debt recorded:

- convert the test to a self-contained fixture;
- eliminate dependency on archived mutable runtime artifacts.

## Required Answers

```text
DYNAMIC_SHADOW_VALIDATION_READY = NO
EXISTING_ACTIVE_RUN_RESUME_SAFE = NO_FOR_GE_VALIDATION
NEW_FRESH_RUN_REQUIRED = YES_AFTER_RUN_ID_BINDING_REPAIR

RECOMMENDED_VALIDATION_START_DATE = 2023-06-01
RECOMMENDED_VALIDATION_BUSINESS_DAYS = 40
RECOMMENDED_INITIAL_CASH = 1000000

GA_REPRODUCTION_METRICS_READY = CONTRACT_DEFINED
LONG_FRESH_FRESH_TARGET_OVERLAP_METRIC_READY = CONTRACT_DEFINED_BUT_NEEDS_POST_GD_RUN
CURRENT_POSITION_SYMMETRY_METRIC_READY = CONTRACT_DEFINED

WINNER_PRESERVATION_METRICS_READY = CONTRACT_DEFINED
TARGET_STABILITY_METRICS_READY = CONTRACT_DEFINED
TURNOVER_METRICS_READY = CONTRACT_DEFINED

ADD_SAFETY_DYNAMIC_METRIC_READY = CONTRACT_DEFINED
G129_DYNAMIC_METRIC_READY = CONTRACT_DEFINED
REENTRY_GUARD_METRIC_READY = CONTRACT_DEFINED
CASH_BEHAVIOR_METRIC_READY = CONTRACT_DEFINED

ZERO_TOLERANCE_ASSERTIONS_DEFINED = YES
DYNAMIC_ACCEPTANCE_CLASSIFICATION_DEFINED = YES

OLD_ARTIFACT_DEPENDENT_TEST_TECH_DEBT_RECORDED = YES

PRODUCTION_CHANGED = NO
SHADOW_AUTHORITY_CHANGED = NO
DIRECT_PRODUCTION_PROMOTION_READY = NO
```

## User Execution Command

Do not execute the dynamic fresh-run yet. The current Fresh Target artifact must
first materialize a non-empty run-scoped `run_id`.

After that narrow SHADOW materialization repair is completed and focused tests
pass, the intended user command is:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2023-06-01 \
  --business-days 40 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Current safe command:

```text
DO_NOT_RUN_FRESH_TARGET_DYNAMIC_VALIDATION_YET
```

## Next Step

Perform a narrow SHADOW-only materialization repair so
`fresh_target_portfolio_shadow.v1` receives the current runtime-test `run_id`
and can prove current run/evidence-root binding without becoming Production
authority.

## Final Judgment

PHASE32_GE_DYNAMIC_SHADOW_VALIDATION_CONTRACT_DEFINED_BUT_BLOCKED_BY_FRESH_TARGET_RUN_ID_BINDING_GAP
