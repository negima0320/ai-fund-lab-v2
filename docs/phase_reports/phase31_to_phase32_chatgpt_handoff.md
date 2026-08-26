# Phase31 to Phase32 ChatGPT Handoff

## System Purpose

AI Fund Lab v2 is a Japanese-equity automated trading system. The current
project objective is to move from accepted Strategy performance improvement
work into Demo / Production operational readiness without reopening performance
tuning by default.

## Current Project Objective

```text
NEXT_PRIMARY_OBJECTIVE = DEMO_AND_PRODUCTION_READINESS
PHASE32_PURPOSE = PHASE32_DEMO_AND_PRODUCTION_READINESS
```

Phase32 should prepare and validate Demo / production-equivalent operation:
broker connectivity, account/cash/position authority, order planning, submit /
cancel / fill lifecycle, reconciliation, corporate actions, restart/resume
idempotency, pending-order safety, observability, daily workflow, alerts,
manual intervention boundaries, production configuration separation, secrets,
audit trail, rollback, and migration gates.

Do not start Phase32 implementation without a new explicit task.

## Phase31 Purpose and Result

Phase31 purpose:

```text
LONG_HORIZON_STRATEGY_PERFORMANCE_CHARACTERIZATION_AND_IMPROVEMENT
```

Phase31 result:

```text
PHASE31_CLOSED = YES
PERFORMANCE_IMPROVEMENT_TRACK_STATUS = COMPLETED_FOR_CURRENT_RELEASE_BASELINE
CURRENT_STRATEGY_BASELINE_ACCEPTED = YES
UNRESOLVED_MANDATORY_PERFORMANCE_DEFECT = NO
```

Phase31 repaired actual-path Runtime / Pending / Submit / Execution /
valuation / campaign identity defects, refined Market Quality / Risk Pacing /
capital competition, repaired BUY_ADD actual-path behavior, characterized BULL
and post-peak behavior, documented future high-resolution capital-value and
portfolio-rotation architecture, and validated March-April profit causality.

## Current Accepted Strategy Behavior

Accepted baseline:

- momentum-follow swing orientation;
- enter after decision-time strength becomes credible;
- no bottom-catching requirement;
- retain strong winners while continuation remains valid;
- ADD selectively when incremental opportunity is valid;
- REDUCE / EXIT when momentum or continuation deteriorates;
- cut genuine failures;
- Cash is first-class;
- no forced full investment;
- BUY and SELL remain independent;
- PC owns capital allocation;
- PS owns discrete quantity;
- Runtime consumes executable decisions and must not re-decide Strategy;
- no future information.

## Current Run Authority

Primary current run:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
```

At G139:

```text
run_state = RUNNING
completed_artifacts = 2022-10-03 through 2023-07-27
next_job = 2023-07-28:market_refresh
```

Phase31 closure authority remains the accepted G138 causality evidence, with
primary window `2023-03-01` through `2023-04-28`. The continuing run is useful
observation but does not keep Phase31 open. Future run results must not be used
to silently retune the accepted baseline.

## Major Recent Outcomes

- G129: BUY_ADD actual-path narrow repair accepted. Submit order-increment
  authority, campaign identity materialization, and ADD MCC consumer behavior
  were repaired without changing PM thresholds or BUY_NEW semantics.
- G130: ADD vs NEW_BUY capital competition evidence remained partial, but no
  mandatory repair was found.
- G131: Unified ADD / NEW_BUY / Cash marginal capital authority design was
  confirmed; Cash remains first-class and shoulder participation is permitted.
- G132: Unified frontier value quality was partial; evidence-resolution
  follow-up was justified, not mandatory repair.
- G133: Blanket BULL weakness was not supported; BULL limitation was a general
  capital-value resolution issue.
- G134: Capital value resolution loss was localized as multi-causal and
  architecture-level, not a mandatory current implementation defect.
- G135: High-resolution marginal value / rotation design readiness was
  accepted as future architecture; no guaranteed return improvement.
- G136: Permanent SoT for high-resolution marginal value and portfolio rotation
  was materialized.
- G137: Architecture ambiguity was hardened: no mandatory single scalar;
  desirability and feasibility separated; HOLD retention and ADD next-lot value
  separated; rotation funding feasibility must be explicit.
- G138: March-April profit was measured as real, explainable, and
  Strategy-causal, while fine-grained value causality remained partial.
- G139: Phase31 closed and Phase32 Demo / Production readiness handoff created.

## Mandatory SoT Documents

Read these before Phase32 work:

- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_data_contract_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_g139_phase31_final_closure_performance_improvement_completion.md`

## Must Not Reopen Automatically

Do not automatically reopen:

- performance optimization;
- threshold / weight tuning;
- High-Resolution Marginal Value implementation;
- Portfolio Rotation implementation;
- BULL weakness investigation;
- April structural-break repair;
- G129 material PnL attribution;
- long-run performance research.

Open new Strategy work only if there is a concrete new defect, explicit
user-approved performance initiative, or evidence that invalidates the accepted
baseline.

## Future Optional Architecture

Future optional items:

```text
canonical_high_resolution_marginal_capital_value.v1 = SHADOW_RESEARCH_CANDIDATE / FUTURE_OPTIONAL
canonical_portfolio_rotation_opportunity_cost.v1 = FUTURE_OPTIONAL
```

These are preserved in:

`docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Do not remove, weaken, or implement them without a new explicit task.

## Roles

- User operates long Historical and external/demo/production commands.
- Codex performs audits, documentation, focused implementation, compile/unit
  tests, and short regressions when explicitly instructed.
- ChatGPT coordinates phase intent, prioritizes tasks, writes Codex
  instructions, reviews handoff context, and governs phase transitions.

## Long-Run Execution Rule

Long Historical, fresh-run, resume, and replay are user-operated unless a future
task explicitly authorizes otherwise. Do not run them by default.

Do not add `--json` to user-facing shell commands unless explicitly requested.

## Phase / Task Numbering Rule

G139 is the final Phase31 closure task. Do not create G139 rollback or retry
suffixes. If new Phase32 work begins, use Phase32 numbering according to the
roadmap and do not reuse Phase31 identifiers.

## Production Safety Constraints

Strong Historical performance does not authorize production trading.

```text
STRATEGY_ACCEPTANCE != PRODUCTION_OPERATIONAL_ACCEPTANCE
```

No production activation, real broker write path, or real order submission is
allowed without an explicit operational gate and user approval. Demo /
production-equivalent readiness must separately validate broker integration,
account/cash/position authority, reconciliation, order lifecycle, failure
modes, idempotency, manual intervention, observability, secrets, audit trail,
rollback, and recovery.

