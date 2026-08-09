# Phase28-D23: Current SELL / EXIT Decision Authority End-to-End Audit

## Executive Summary

Primary Judgment:

```text
PHASE28_D23_CURRENT_SELL_EXIT_AUTHORITY_AUDIT_COMPLETE_D21_MODIFY_REQUIRED
```

Phase28-D23 was read-only. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

Target run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

The audited 93 D17/D22 exit-reentry pairs show that observed Runtime `SELL_EXIT` is not equivalent to PM `EXIT`. In the D17 pre-D19 run, Runtime `SELL_EXIT` was produced from PM actions as follows:

| PM action on exit day | Runtime `SELL_EXIT` count |
|---|---:|
| ADD | 22 |
| HOLD | 61 |
| EXIT | 7 |
| REDUCE | 3 |

First divergence distribution:

| First divergence | Count |
|---|---:|
| Strategy PM action loss / `UNRESOLVED` | 86 |
| PM direct EXIT | 7 |

Therefore the current evidence cannot support a re-entry-only repair. D21 should remain `MODIFY/HOLD` until SELL/EXIT authority is separated in the next design phase.

## Scope

In scope:

- Current SELL / EXIT authority architecture.
- PM `HOLD` / `ADD` / `REDUCE` / `EXIT` semantics.
- Portfolio Construction, Position Sizing, Runtime Planning, and Sell Planning mappings.
- All 93 D17/D22 exit-reentry pairs.
- `RISK=61` and valid loss-cut `7` authority separation.
- Existing hard/immediate exit, HOLD persistence, strong/weak exit, and hysteresis feasibility.

Out of scope:

- Implementation.
- Threshold, config, or schema changes.
- New EXIT taxonomy design.
- Fresh or resumed runtime execution.

## Docs Reviewed

- `docs/phase_reports/phase28_d17_fresh_100bd_canonical_buy_add_acceptance_and_runtime_conformance_audit.md`
- `docs/phase_reports/phase28_d18_pm_add_strategy_pm_runtime_run_mismatch_root_cause_diagnosis.md`
- `docs/phase_reports/phase28_d19_pm_add_actual_runtime_path_minimal_repair.md`
- `docs/phase_reports/phase28_d20_reentry_root_cause_and_pnl_impact_audit.md`
- `docs/phase_reports/phase28_d21_campaign_aware_state_change_gated_reentry_repair_design.md`
- `docs/phase_reports/phase28_d22_premature_exit_and_exit_reentry_oscillation_audit.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/strategy_architecture_v1.md`

## Current SELL Architecture

The current SELL architecture is layered:

```text
Position Management AI
↓
Strategy Position Management
↓
Portfolio Construction
↓
Position Sizing
↓
Runtime Planning
↓
Pending / Approval / Submit / Broker
```

The final `SELL_EXIT` producer in Strategy artifacts is Runtime Planning, not PM. PM produces action intent; Portfolio Construction and Position Sizing translate that intent plus opportunity and portfolio fit into target membership, target weight, target quantity, and quantity delta; Runtime Planning maps negative quantity deltas to `SELL_EXIT` or `SELL_REDUCE`.

Code evidence:

- `src/ai_fund_lab_v2/position_management_ai/inference.py:320-430`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:708-729`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1501-1510`
- `src/ai_fund_lab_v2/strategy/position_sizing.py:653-733`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py:1149-1205`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:337-356`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1237-1306`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1450-1468`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:430-512`

## PM Inputs

PM uses decision-time current-position and opportunity context. The active inputs include:

- current return
- peak return
- drawdown from peak
- downside risk score
- expected edge score
- buy rank
- position size
- holding days
- technical trend features
- opportunity continuation score
- risk guard status

Evidence: `reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit/pm_input_and_decision_contract.json`.

## PM Action Semantics

Current PM semantics:

| PM action | Semantics |
|---|---|
| HOLD | Retain position; no sell order by PM itself. |
| ADD | Increase/add to existing position; explicitly outside Sell Planning scope in PM artifacts. |
| REDUCE | Partial sell intent when risk/drawdown/weak hold exists but some continuation evidence remains. |
| EXIT | Full exit intent for hard stop, profit-retention break, broken trend/opportunity, high downside risk, bad risk guard, or weak hold with no continuation. |
| UNRESOLVED | Not a PM AI output; downstream adapter/strategy unresolved state. |

PM `EXIT` and Runtime Planning `SELL_EXIT` do not have the same meaning in D17 evidence. PM `EXIT` is one possible upstream authority; Runtime `SELL_EXIT` can also be produced by target quantity going to zero after downstream translation.

## Portfolio Construction Mapping

Code mapping:

| PM action | membership_intent | weight_intent |
|---|---|---|
| HOLD | RETAIN | MAINTAIN |
| ADD | RETAIN | INCREASE |
| REDUCE | REDUCE_CANDIDATE | DECREASE |
| EXIT | REMOVE_CANDIDATE | REMOVE |
| Other | UNRESOLVED | UNRESOLVED |

Existing position membership itself is preserved as a current-position member. Portfolio Construction exclusion or non-selection does not directly produce `SELL_EXIT`; it produces membership/weight state that Position Sizing and Runtime Planning later translate.

## Position Sizing Mapping

Position Sizing computes `target_quantity_candidate` and `quantity_delta_candidate`.

Full-exit-producing condition:

```text
current_quantity > 0
target_quantity_candidate == 0
quantity_delta_candidate < 0
```

This can arise from PM `EXIT`, membership removal/exclusion, target weight unavailable fail-close, target weight zero, minimum meaningful notional, or rounding. PM `REDUCE` is designed as partial, but can become non-executable/review if quantity constraints are violated.

## Runtime Planning Taxonomy

Runtime Planning `SELL_EXIT` branches:

| Branch | Condition |
|---|---|
| canonical quantity delta negative, target zero | canonical source and `quantity_delta < 0` and `target_quantity == 0` |
| legacy quantity delta negative, target zero | legacy source and `quantity_delta < 0` and `target_quantity == 0` |
| legacy PM EXIT fallback | no quantity delta and `pm_action == EXIT` |

D17 active branch for the 93 audited pairs was the negative-delta target-zero path.

## Sell Planning / Execution

The legacy Sell Planning pipeline only selects `source_decision in {"EXIT", "REDUCE"}`. `ADD` and `HOLD` are not valid sell source decisions there. `EXIT` quantity contract sells requested/current full sellable quantity; `REDUCE` uses a reduce quantity contract and can be non-executable or review-required when constraints fail.

Strategy Runtime Planning and Strategy Pending Authority can still create `SELL_EXIT` pending from strategy plans, which is the relevant path for the D17/D22 evidence.

## SELL_EXIT Producer Enumeration

Final observed producer:

```text
Strategy Runtime Planning
```

Observed D17 reason pattern:

```text
position_sizing_negative_quantity_delta_maps_to_sell_exit
position_sizing_quantity_candidate_resolved
```

Pending materialization is downstream; it does not decide strategic `SELL_EXIT`.

## 93-Pair Trace

All 93 D22 exit-reentry pairs were traced through same-day PM, Strategy PM, Portfolio Construction, Position Sizing, and Runtime Planning artifacts.

Evidence:

```text
reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit/exit_pair_end_to_end_trace.json
```

## PM vs Runtime SELL Matrix

| PM action | Runtime `SELL_EXIT` |
|---|---:|
| ADD | 22 |
| HOLD | 61 |
| EXIT | 7 |
| REDUCE | 3 |

No audited D17 pair had PM `UNRESOLVED`; `UNRESOLVED` was introduced downstream by Strategy PM.

## First Divergence

| Classification | Count |
|---|---:|
| Strategy PM action loss / `UNRESOLVED` | 86 |
| PM direct EXIT | 7 |

This confirms that most D17 `SELL_EXIT` evidence was contaminated by the pre-D19 PM propagation defect. D19 is expected to repair the PM `ADD -> UNRESOLVED -> SELL_EXIT` part, but D23 did not run fresh evidence to prove post-D19 behavior.

## RISK61

D22 counted 61 exits in diagnostic `RISK` category. D23 authority audit separates them:

| Authority class | Count |
|---|---:|
| Diagnostic risk category but PM was not EXIT | 53 |
| PM EXIT risk authority | 7 |
| PM REDUCE risk authority, not full EXIT | 1 |

Therefore `RISK=61` must not be treated as 61 valid hard exits. The directly supported PM full-exit risk authority count in D17 evidence is 7.

## Valid Loss-Cut7

Valid loss-cut count remains:

```text
7
```

The valid loss-cut group aligns with PM `EXIT` risk authority. These should remain protected by any future repair.

## Immediate-Exit Authority

Judgment:

```text
PARTIAL
```

PM has hard/urgent-style rules such as `hard_stop_current_return`, bad risk guard, high downside risk, and broken trend/opportunity. Runtime Planning, however, has no formal immediate-vs-normal `SELL_EXIT` taxonomy. Safety and corporate-event guards are separate guard authorities, not Strategy PM EXIT authority.

## HOLD Persistence

Judgment:

```text
NO
```

There is no active general HOLD/EXIT hysteresis or multi-day confirmation guard. A narrow profit-retention-only override can preserve HOLD when expected edge is adequate, downside risk is not high, and exit score is below the boundary, but that is not a general persistence policy.

## Sell Philosophy

Current AI SELL behavior is best described as layered de-risking/rebalancing:

- PM evaluates position lifecycle intent.
- Opportunity rank and expected edge influence continuation, ADD, and portfolio selection.
- Portfolio Construction decides membership and target weight.
- Position Sizing decides target quantity and delta.
- Runtime Planning maps full negative delta to `SELL_EXIT`.

This is not a single AI liquidation decision, and D17 evidence shows final `SELL_EXIT` can disagree with PM action.

## Authority Consistency

Judgment:

```text
INCONSISTENT_FOR_D17_RUN_EVIDENCE
```

Observed `SELL_EXIT` frequently came from downstream quantity/target translation after Strategy PM action loss, not from PM `EXIT`. A re-entry-only guard would treat downstream symptoms without separating legitimate full exits from accidental or weak exits.

## D19 Effect

D17 was pre-D19. D19 is expected to resolve:

```text
PM ADD -> Strategy PM UNRESOLVED -> target zero -> Runtime SELL_EXIT
```

Expected directly resolved count:

```text
22
```

Remaining SELL defects after D19 are expected to include HOLD/REDUCE/EXIT strength semantics, target-membership zeroing behavior, re-entry hysteresis, and lack of immediate-vs-normal exit taxonomy. A post-D19 fresh run is still required, but was not executed in D23.

## Strong / Weak Exit

Existing definition:

```text
NO
```

Evidence distinguishability:

```text
PARTIAL
```

PM reason codes can identify hard-stop/risk-like exits, but Runtime Planning does not carry a formal strong/weak or immediate/normal `SELL_EXIT` class, and D17 is contaminated by the pre-D19 action propagation gap.

## Hysteresis

Feasibility:

```text
FEASIBLE_WITH_EXISTING_AUTHORITY_SOURCES_BUT_REQUIRES_DESIGN
```

Available sources include PM action/reason, position campaign ids, last exit date/reason, Runtime Planning intent, execution fills, closed campaign state, and business-day calendar. The blocking gap is semantic, not data availability: exit strength and authority separation must be designed first.

## D21 Status

D21 implementation decision:

```text
MODIFY / HOLD
```

Reason:

```text
Re-entry defect is real, but D17/D22 proves EXIT-side authority is also too sensitive or contaminated.
Implementing only a re-entry gate risks preserving accidental exits while blocking later corrections.
```

## Risks

- Treating all Runtime `SELL_EXIT` as PM `EXIT` would overcount valid exits.
- Treating D22 `RISK=61` as hard risk authority would preserve many non-PM-EXIT cases.
- Implementing D21 alone before SELL authority separation could mask the true boundary defect.
- Post-D19 behavior remains unproven without a fresh run.

## Open Gaps

- No post-D19 fresh 100BD evidence.
- No formal Runtime `SELL_EXIT` strength taxonomy.
- No active general HOLD/EXIT hysteresis guard.
- No unified repair contract separating valid hard exits from weak/accidental exits.

## Next Phase

Recommended next phase:

```text
Phase28-D24 SELL/EXIT Authority Repair Design
```

Recommended D24 scope:

- Separate PM hard/valid EXIT from downstream target-zero `SELL_EXIT`.
- Define whether strong/immediate vs normal/weak EXIT is required.
- Preserve valid loss-cut authority.
- Decide how D21 re-entry gating should compose with repaired SELL authority.

## Final Judgment

```text
Primary Judgment:
PHASE28_D23_CURRENT_SELL_EXIT_AUTHORITY_AUDIT_COMPLETE_D21_MODIFY_REQUIRED

Current AI HOLD/ADD/REDUCE/EXIT mechanisms:
PM action intent plus downstream portfolio/sizing/runtime translation.

SELL_EXIT final producer:
Strategy Runtime Planning.

PM EXIT/REDUCE/HOLD/ADD/UNRESOLVED -> SELL_EXIT counts:
EXIT=7
REDUCE=3
HOLD=61
ADD=22
UNRESOLVED=0 upstream PM / 86 downstream Strategy PM action-loss cases

93 first divergence distribution:
Strategy PM action loss / UNRESOLVED=86
PM direct EXIT=7

RISK61 actual:
53 diagnostic non-PM-EXIT risk category
7 PM EXIT risk authority
1 PM REDUCE risk authority

Valid loss-cut7 actual:
7 valid PM EXIT risk/loss-cut cases.

Immediate/hard exit authority:
PARTIAL

General HOLD/EXIT hysteresis:
NO

D19 expected resolve count:
22 PM ADD -> SELL_EXIT contamination cases.

D19 remaining SELL defect:
HOLD/REDUCE/EXIT strength semantics, target-zero translation, and hysteresis/re-entry composition remain.

Strong/Weak existing definition:
NO

Existing evidence distinguishability:
PARTIAL

Hysteresis feasibility:
FEASIBLE_WITH_EXISTING_AUTHORITY_SOURCES_BUT_REQUIRES_DESIGN

D21 implementation:
MODIFY / HOLD until SELL authority design completes.

Next Phase:
Phase28-D24 SELL/EXIT Authority Repair Design

Mutation flags:
implementation_changed=false
config_changed=false
schema_changed=false
threshold_changed=false
resume_executed=false
fresh_run_executed=false
long_historical_executed=false
runtime_mutated=false
```

## Deliverables

```text
docs/phase_reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit.md
reports/phase_reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit.json
reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit/
```
