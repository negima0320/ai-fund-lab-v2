# Phase28-D24: PM HOLD / ADD / REDUCE / EXIT Authority-Preserving SELL Repair Design

## Executive Summary

Primary Judgment:

```text
PHASE28_D24_PM_INTENT_PRESERVING_SELL_AUTHORITY_REPAIR_DESIGN_COMPLETE_D25_READY
```

Implementation Entry Decision:

```text
READY
```

D24 was design-only and read-only. No implementation, config change, schema change, threshold change, resume, fresh run, long historical run, or runtime mutation was performed.

The repair design does not create a new EXIT strategy and does not introduce:

```text
STRONG_EXIT
WEAK_EXIT
EXIT_SCORE
EXIT_CONFIRMATION
new thresholds
hysteresis implementation
re-entry gate implementation
```

The single design contract is:

```text
FULL_LIQUIDATION_ALLOWED =
PM_EXIT
OR
EXPLICIT_HIGHER_PRIORITY_LIQUIDATION_AUTHORITY
```

`target_quantity = 0` is a derived quantity. It is not, by itself, full liquidation authority.

## Accepted D23 Facts

Target run:

```text
runtime-test-historical-smoke-20260806T053322547871Z
```

D23 confirmed:

| Exit-day PM action | Runtime `SELL_EXIT` count |
|---|---:|
| HOLD | 61 |
| ADD | 22 |
| REDUCE | 3 |
| EXIT | 7 |

First divergence:

| Divergence | Count |
|---|---:|
| Strategy PM action loss / `UNRESOLVED` | 86 |
| PM direct EXIT | 7 |

Final observed `SELL_EXIT` producer:

```text
Strategy Runtime Planning
```

D17 active mapping:

```text
negative quantity delta
+
target_quantity == 0
↓
SELL_EXIT
```

## D19 Separation

D17/D22/D23 evidence is pre-D19. D19 repaired the same-day PM decision handoff into Formal Strategy PM.

D19 focused validation confirmed:

```text
PM ADD
→ Strategy PM ADD
→ Portfolio Construction INCREASE
→ positive quantity delta
→ BUY_ADD
```

Therefore D24 does not treat the pre-D19:

```text
PM ADD -> SELL_EXIT = 22
```

as a current unrepaired ADD-specific defect. D24 still protects the post-D19 SELL chain against the broader authority issue:

```text
target zero without full-liquidation authority
```

## Docs Reviewed

- `docs/phase_reports/phase28_d23_current_sell_exit_decision_authority_end_to_end_audit.md`
- `docs/phase_reports/phase28_d22_premature_exit_and_exit_reentry_oscillation_audit.md`
- `docs/phase_reports/phase28_d21_campaign_aware_state_change_gated_reentry_repair_design.md`
- `docs/phase_reports/phase28_d20_reentry_root_cause_and_pnl_impact_audit.md`
- `docs/phase_reports/phase28_d19_pm_add_actual_runtime_path_minimal_repair.md`
- `docs/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## Current Authority Contract

Architecture states:

- PM is the Strategy Action Authority for existing-position directional actions.
- Portfolio Construction owns target portfolio and target weight.
- Position Sizing owns target notional, target quantity candidate, and quantity delta candidate.
- Runtime Planning is a pure execution-intent mapper.
- Safety blocks or reviews dangerous intent; it does not optimize Strategy target.
- Corporate Event Authority provides facts; it does not decide BUY/SELL.
- Broker / Execution handles executable order constraints; it does not decide investment intent.

Key evidence:

- `docs/02_architecture/strategy_architecture_v1.md:59`
- `docs/02_architecture/strategy_architecture_v1.md:74`
- `docs/02_architecture/strategy_architecture_v1.md:96-125`
- `docs/02_architecture/strategy_architecture_v1.md:195-199`
- `docs/02_architecture/strategy_architecture_v1.md:231-239`
- `docs/02_architecture/runtime_architecture_v2.md:2748-2825`

## Desired PM Runtime Mapping

| PM action | Desired path | Runtime result |
|---|---|---|
| HOLD | Strategy PM HOLD -> PC RETAIN/MAINTAIN -> preserve positive existing quantity | No `SELL_EXIT` |
| ADD | Strategy PM ADD -> PC RETAIN/INCREASE -> positive delta when eligible | `BUY_ADD` or no executable add; no `SELL_EXIT` |
| REDUCE | Strategy PM REDUCE -> PC REDUCE_CANDIDATE/DECREASE -> partial remaining quantity | `SELL_REDUCE` or review/no-order |
| EXIT | Strategy PM EXIT -> PC REMOVE -> target quantity zero | `SELL_EXIT` |
| UNRESOLVED | downstream unresolved state, not PM decision | Review/no-order/preserve; no implicit `SELL_EXIT` |

## Override Authority Inventory

Allowed full liquidation authorities:

- PM `EXIT`.
- Explicit Safety/Emergency/Human full-liquidation authority, if an existing artifact explicitly requires liquidation.

Not full liquidation authorities:

- ordinary portfolio fit
- ordinary rank change
- ordinary sizing output
- target quantity zero alone
- missing target weight
- unresolved target weight
- PM action missing or `UNRESOLVED`
- minimum meaningful notional
- lot rounding
- Broker infeasibility
- Corporate Event fact by itself

Safety, Corporate Event, Broker, and Human Review remain separate authorities. D24 does not convert them into a new Strategy EXIT taxonomy.

## Full Liquidation Authority Contract

Design contract:

```text
negative delta
+
target_quantity = 0
+
full-liquidation authority present
→ SELL_EXIT
```

```text
negative delta
+
target_quantity > 0
→ SELL_REDUCE
```

```text
target_quantity = 0
but full-liquidation authority absent
→ REVIEW_REQUIRED / NO_ORDER
```

```text
missing authority
→ REVIEW_REQUIRED
```

This preserves valid PM `EXIT` while preventing accidental full liquidation from downstream zeroing.

## Target-Zero Semantics

| Producer / case | Correct classification |
|---|---|
| PM EXIT | `SELL_EXIT` allowed |
| membership REMOVE from PM EXIT | `SELL_EXIT` allowed |
| explicit target zero with higher-priority liquidation authority | `SELL_EXIT` allowed |
| explicit target zero from ordinary existing-position non-selection | `REVIEW_REQUIRED` or preserve existing; no implicit `SELL_EXIT` |
| target weight missing | `REVIEW_REQUIRED` |
| target weight unresolved | `REVIEW_REQUIRED` |
| capital infeasible | no BUY / review; not full liquidation |
| position count conflict | review unless explicit full liquidation authority exists |
| minimum meaningful notional | `NO_ORDER` / review; not full liquidation |
| lot rounding | `NO_ORDER` / review; not full liquidation |
| portfolio exclusion for non-current candidate | `NO_ACTION` |
| portfolio exclusion for current position without PM EXIT | review/preserve; not full liquidation |
| legacy PM EXIT fallback | `SELL_EXIT` allowed only in legacy compatibility scope |
| legacy PM HOLD/ADD/UNRESOLVED fallback | no `SELL_EXIT` |

## Missing Authority vs Zero Authority

D24 separates:

```text
explicit zero with reason evidence
```

from:

```text
missing / unresolved authority
```

Rules:

- `target_weight = 0` can be valid only with explicit reason evidence and lineage.
- `target_weight missing` is not zero.
- `target_weight unresolved` is not zero.
- PM action missing or `UNRESOLVED` is not PM `EXIT`.
- Quantity candidate zero is not strategy full-close authority.

## UNRESOLVED Fail-Closed Contract

Correct fail-closed behavior for an existing position with `UNRESOLVED` strategy state:

```text
preserve / no-order / REVIEW_REQUIRED
```

Forbidden fail-closed behavior:

```text
UNRESOLVED
↓
target zero
↓
SELL_EXIT
```

Existing holdings must not be liquidated just because upstream authority is missing.

## Existing Position Preservation

Existing positions are active campaigns. Without PM `EXIT` or explicit higher-priority liquidation authority:

- PM `HOLD` preserves position continuity.
- PM `ADD` preserves position continuity and may increase exposure through D19 + Phase28-C.
- PM `REDUCE` preserves partial remaining quantity when executable.
- PM `UNRESOLVED` must review/no-order/preserve, not full close.

## Portfolio Construction Responsibility

Portfolio Construction may decide target membership and target weight, but must not destroy PM intent lineage.

For existing positions:

- PM `HOLD` maps to `RETAIN / MAINTAIN`.
- PM `ADD` maps to `RETAIN / INCREASE`.
- PM `REDUCE` maps to `REDUCE_CANDIDATE / DECREASE`.
- PM `EXIT` maps to `REMOVE_CANDIDATE / REMOVE`.
- `UNRESOLVED` remains unresolved and cannot be treated as `EXIT`.

Ordinary candidate ranking competition can exclude non-current candidates. It must not silently full-liquidate existing PM `HOLD` / `ADD` / `REDUCE` positions.

## Position Sizing Responsibility

Position Sizing converts target allocation into target quantity and quantity delta. It does not own full liquidation authority.

D24 design requires Position Sizing to preserve the distinction between:

- explicit PM `EXIT` target zero
- REDUCE partial target
- non-executable reduce
- target weight missing/unresolved
- rounding/min-notional zero

REDUCE rounding to zero should become `NO_ORDER` or `REVIEW_REQUIRED`, not `SELL_EXIT`.

## Runtime Planning Responsibility

Runtime Planning remains a mapper. It must not infer a new PM `EXIT`.

Desired Runtime Planning guard:

```text
SELL_EXIT requires full_liquidation_authority
```

This can be implemented using existing PM action/provenance and higher-priority authority provenance, without introducing a new exit strategy.

## REDUCE Protection

D23 found:

```text
PM REDUCE -> SELL_EXIT = 3
```

The three cases were:

| Date | Symbol | PM reason | D17 path |
|---|---|---|---|
| 2023-06-08 | 37820 | `risk_increased_but_trend_not_broken` | Strategy PM `UNRESOLVED` -> target zero -> `SELL_EXIT` |
| 2023-08-17 | 65730 | `peak_drawdown_warning` | Strategy PM `UNRESOLVED` -> target zero -> `SELL_EXIT` |
| 2023-04-25 | 77190 | `peak_drawdown_warning` | Strategy PM `UNRESOLVED` -> target zero -> `SELL_EXIT` |

These are not valid evidence that PM `REDUCE` intended full close. D24 contract protects REDUCE as partial sell intent.

## Valid PM EXIT Preservation

D23 confirmed:

```text
PM EXIT -> SELL_EXIT = 7
valid loss-cut = 7
```

D24 design must not turn valid PM `EXIT` into `HOLD`, `NO_ACTION`, or accidental review. PM EXIT with preserved reason/provenance remains the canonical full liquidation path unless downstream Safety/Submit/Broker blocks.

## Existing Hard / Immediate Authority

D23 judgment remains:

```text
PARTIAL
```

PM already has hard-risk-style reasons:

- `hard_stop_current_return`
- bad risk guard
- high downside risk
- broken trend/opportunity

D24 does not create a new strong/weak taxonomy. It preserves existing PM EXIT reason/provenance so later hysteresis work can distinguish hard exits from normal exits if needed.

## D21 Re-entry Gate Status

D21 remains:

```text
HOLD / MODIFY
```

Reason:

```text
First repair the SELL authority chain.
Then evaluate re-entry on fresh post-repair evidence.
```

D24 does not change re-entry.

## Hysteresis Status

Status:

```text
DEFER
```

D17/D22 contained pre-D19 action-loss contamination. D24 first preserves PM intent through SELL mapping. Hysteresis should be reconsidered only after a fresh post-D25 run proves whether genuine PM `EXIT` remains too sensitive.

## D19 + D24 Expected Lifecycle

Expected post-D19 + post-D24 lifecycle:

```text
PM ADD
→ BUY_ADD

PM HOLD
→ HOLD / NO_ACTION

PM REDUCE
→ SELL_REDUCE

PM EXIT
→ SELL_EXIT
```

Explicit higher-priority liquidation authority remains separate.

## Architecture Conformance Answers

| Question | Answer |
|---|---|
| PMはLifecycle Intent Authorityか | YES. PM is Existing Position Intent / Strategy Action Authority for `HOLD/ADD/REDUCE/EXIT`. |
| PCはPM intentをoverrideできるか | PARTIAL. PC owns target portfolio, but must integrate and preserve PM intent lineage; ordinary rank/fit must not independently emit EXIT. |
| override可能ならどの条件か | PM EXIT or explicit higher-priority liquidation authority. Ordinary rank/fit/zero/missing is not enough. |
| Sizingはfull liquidation authorityを持つか | NO. Sizing owns quantity candidates only. |
| Runtime Planningはfull liquidation authorityを持つか | NO. Runtime Planning is a pure mapper. |
| target zeroはAuthorityか単なるderived quantityか | Derived quantity. It requires authority to become `SELL_EXIT`. |
| missing targetとexplicit zeroは区別されているか | Architecture says they must be separated; D24 contract makes this mandatory. |
| UNRESOLVED existing positionの正しいfail-closed動作は何か | Preserve/no-order/review; not full liquidation. |
| REDUCEをEXITへ昇格できるAuthorityは何か | Only explicit higher-priority full-liquidation authority. |
| HOLDをEXITへoverrideできるAuthorityは何か | PM EXIT on the same decision path or explicit higher-priority liquidation authority. |

## Repair Option Comparison

| Option | Judgment | Reason |
|---|---|---|
| A: Runtime Planning guard | Necessary but not sufficient alone | Stops final bad `SELL_EXIT`, but upstream target-zero artifacts remain misleading. |
| B: Portfolio Construction existing-position preservation | Necessary | Keeps PM `HOLD/ADD/REDUCE` from ordinary full deletion. |
| C: Position Sizing target-zero protection | Necessary | Separates sizing zero from liquidation authority and protects REDUCE. |
| D: Minimum boundary combination as one Authority Contract | Primary Recommendation | Preserves PM intent across PC/PS/RP while protecting valid PM EXIT and D19 ADD chain. |

Primary Recommendation:

```text
Option D
```

Implement one PM-intent-preserving Full Liquidation Authority Contract across Strategy PM lineage, Portfolio Construction existing-position membership, Position Sizing target-zero protection, and Runtime Planning final `SELL_EXIT` guard.

## Focused Fixture Design

| Fixture | Input | Expected |
|---|---|---|
| 1 | existing position + PM HOLD + normal conditions | target quantity > 0, no `SELL_EXIT` |
| 2 | existing position + PM ADD | `BUY_ADD` when eligible, no `SELL_EXIT` |
| 3 | existing position + PM REDUCE | `0 < target_quantity < current_quantity`, `SELL_REDUCE` |
| 4 | existing position + PM EXIT | `target_quantity = 0`, `SELL_EXIT` |
| 5 | existing position + PM UNRESOLVED | no implicit `SELL_EXIT`; review/no-order/preserve |
| 6 | PM HOLD + explicit Safety liquidation authority | follow existing Safety contract |
| 7 | PM REDUCE + lot rounding would produce zero | no silent `SELL_EXIT`; no-order/review |

## Regression Contract

Must preserve:

- D19 same-day PM ADD -> Formal Strategy PM ADD -> BUY_ADD
- Phase28-C canonical ADD allocation bridge
- D14 Strategy SELL canonical `listed_info`
- D16 `listed_info` authority precedence
- D8 pending merge
- D3 pending reconciliation
- ordinary BUY
- ordinary SELL with PM EXIT
- valid PM EXIT loss-cut7

Must not change:

- PM thresholds
- Expected Edge
- Incremental Investment Value
- Opportunity Cost
- Submit Guard
- Broker normalizer
- Config
- Schema
- Thresholds

## Fresh Test Contract

D24 did not run fresh 100BD. After implementation and short validation, the next fresh run must collect:

```text
PM HOLD -> SELL_EXIT
PM ADD -> SELL_EXIT
PM REDUCE -> SELL_EXIT
PM EXIT -> SELL_EXIT

PM ADD -> BUY_ADD
PM REDUCE -> SELL_REDUCE

Re-entry count
1BD re-entry count

avg cash ratio
avg invested ratio

total return
max drawdown
profit factor
```

## Performance Guardrail

D24 does not optimize the D17/D20 100BD PnL. The design is based only on:

```text
Architecture
Authority semantics
decision-time evidence
```

## Open Gaps

- D24 is design-only; no implementation performed.
- No post-D19 fresh 100BD evidence yet.
- Existing architecture currently allows full negative delta to map to `SELL_EXIT`; D25 must add authority provenance guard without inventing a new exit strategy.
- Safety full-liquidation artifact semantics may need exact existing-code integration audit if D25 touches that path.
- Hysteresis remains deferred until PM-intent-preserving SELL chain is proven.

## Next Phase

Recommended next phase:

```text
Phase28-D25 PM Intent-Preserving SELL Authority Implementation
```

D25 should implement only the D24 authority contract with short validation.

## Final Judgment

```text
Primary Judgment:
PHASE28_D24_PM_INTENT_PRESERVING_SELL_AUTHORITY_REPAIR_DESIGN_COMPLETE_D25_READY

Implementation Entry Decision:
READY

Full Liquidation Contract:
FULL_LIQUIDATION_ALLOWED = PM_EXIT OR EXPLICIT_HIGHER_PRIORITY_LIQUIDATION_AUTHORITY

PM HOLD:
NO implicit SELL_EXIT

PM ADD:
Preserve D19 / Phase28-C BUY_ADD chain; no SELL_EXIT from ADD alone

PM REDUCE:
SELL_REDUCE or review/no-order; no silent EXIT escalation

PM EXIT:
SELL_EXIT preserved

UNRESOLVED:
review/no-order/preserve; not full liquidation

D19 Separation:
pre-D19 ADD->SELL_EXIT=22 is expected D19-resolved contamination, not D24 current ADD defect

Valid PM EXIT Preservation:
valid loss-cut7 protected

Hysteresis:
DEFER

D21:
HOLD / MODIFY

Primary Recommendation:
Option D

Next Phase:
Phase28-D25 PM Intent-Preserving SELL Authority Implementation

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
docs/phase_reports/phase28_d24_pm_intent_preserving_sell_authority_repair_design.md
reports/phase_reports/phase28_d24_pm_intent_preserving_sell_authority_repair_design.json
reports/phase28_d24_pm_intent_preserving_sell_authority_repair_design/
```
