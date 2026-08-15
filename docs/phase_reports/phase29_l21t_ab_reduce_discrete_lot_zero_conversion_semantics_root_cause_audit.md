# Phase29-L21T-AB - REDUCE Discrete-Lot Zero Conversion Semantics Root Cause Audit

Task ID: Phase29-L21T-AB

Mode:

```text
READ_ONLY ROOT CAUSE / ARCHITECTURE / LIFECYCLE AUDIT
```

Primary Judgment:

```text
PHASE29_L21T_AB_REDUCE_DISCRETE_LOT_ZERO_CONVERSION_SEMANTIC_GAP_CONFIRMED_NO_RUNTIME_CHANGE
```

## Scope

Audited run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Audited evidence range present in run artifacts:

```text
2022-08-10 through 2023-08-08 complete enough for Strategy/PM evidence
2023-08-09 contains only market_refresh partial artifacts
```

Task ID uniqueness check:

```text
Phase29-L21T-AB was not found in docs, reports, src, or tests before this report.
```

No implementation, runtime mutation, resume, replay, recovery, fresh-run, Pending edit, Ledger edit, Current edit, or configuration change was performed.

## Evidence Sources

Read:

- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase22_f_capital_deployment.md`
- `docs/phase_reports/phase22_pr_dynamic_portfolio_capacity_and_asset_proportional_capital_authority_review_and_repair.md`
- `docs/phase_reports/phase28_c_canonical_add_allocation_bridge_implementation.md`
- `docs/phase_reports/phase28_d54_buy_add_evidence_and_lot_aware_capital_conversion_design.md`
- `docs/phase_reports/phase28_d55_a_buy_add_investment_evidence_resolver_implementation.md`
- `docs/phase_reports/phase29_l18_lot_concentration_feasibility_capital_deployment_bottleneck_audit_and_repair_design.md`
- `docs/phase_reports/phase29_l19_cap_constrained_lot_floor_iterative_residual_reallocation_implementation.md`
- `docs/phase_reports/phase29_l19r_lot_sizing_repair_lineage_and_regression_audit.md`
- `docs/phase_reports/phase28_d25_pm_intent_preserving_sell_authority_implementation.md`
- `docs/phase_reports/phase28_d32_portfolio_construction_reduce_partial_target_semantics_root_cause.md`
- `docs/phase_reports/phase28_d34_canonical_reduce_intensity_authority_integration_implementation.md`

Inspected code:

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

Inspected run artifacts:

- `daily/*/position_management/pm_decisions.json`
- `daily/*/strategy/position_management.json`
- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/runtime_planning.json`
- `daily/*/positions/position_campaigns.json`
- `daily/*/submit/*.json`
- `daily/*/execution/fills.json`

## REDUCE Architecture / Authority Chain

Current authority chain:

```text
Position Management
  -> emits REDUCE intent and reduce_intensity
  -> canonical reduce intensity authority resolves LIGHT/MEDIUM/STRONG
  -> Portfolio Construction converts REDUCE_CANDIDATE to reduced target weight
  -> Position Sizing materializes negative quantity_delta_candidate if executable
  -> Runtime Planning emits SELL_REDUCE only when quantity is non-zero executable
  -> Sell Planning / shared order planner preserves final SELL quantity contract
  -> Pending
  -> Submit
  -> Execution
```

Key code evidence:

- PM explicitly says quantity belongs to Sell Planning authority: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:635`.
- Canonical fractions are `LIGHT=0.25`, `MEDIUM=0.33`, `STRONG=0.50`: `src/ai_fund_lab_v2/strategy/reduce_intensity_authority.py:9`.
- Position Sizing floors REDUCE raw quantity to tradable unit and zeros the row when the result is below lot or minimum notional: `src/ai_fund_lab_v2/strategy/position_sizing.py:871`.
- Runtime Planning maps zero quantity_delta to `RESOLVED_ZERO_DELTA` / no order: `src/ai_fund_lab_v2/strategy/runtime_planning.py:1203`.
- Sell Planning has a sharper contract for non-executable REDUCE: `REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`, `NO_SELL_ORDER`, `runtime_continuation_status=PASS`: `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:1728`.

## Formal REDUCE Funnel

Observed run funnel:

```text
PM REDUCE decisions:                         72
Position Sizing raw REDUCE rows:             72
Deduped semantic REDUCE decisions:           72
Valid quantity materialization rows:         72
Executable non-zero REDUCE decisions:         4
Zero due to minimum tradable quantity:       27
Zero due to minimum notional / other policy: 41
Zero for other reasons:                       0
Unresolved / missing materialization:         0
Actual SELL_REDUCE runtime plans:             4
Submit SELL generated for those plans:        4
Execution/fill generated for those plans:     4
```

Zero conversion rates:

```text
Lot-zero only: 27 / 72 = 37.50%
All zero REDUCE materializations: 68 / 72 = 94.44%
```

## Raw vs Deduped Counts

Operator-provided extraction referenced raw matching records of 112 and executable 82 / zero 30. This audit does not accept that raw figure as semantic truth because broad artifact search can match nested support rows, shadow artifacts, and repeated observability copies.

Canonical READ-ONLY extraction over the listed source artifacts produced:

```text
Raw PM REDUCE records:                    72
Raw Position Sizing REDUCE rows:          72
Deduped semantic REDUCE decisions:        72
Deduped lot-zero decisions:               27
Duplicate materialized evidence count:     0 in canonical PM/Position Sizing sources
```

The discrepancy is therefore classified as an observability / extraction-scope risk, not as a confirmed runtime duplicate-materialization defect.

## Lot-Zero Root Cause

For true lot-zero cases, the immediate arithmetic is:

```text
raw_reduce_quantity = current_quantity * reduce_fraction
rounded_reduce_quantity = floor(raw_reduce_quantity / tradable_unit) * tradable_unit
final executable quantity = 0 when rounded_reduce_quantity < 100
```

Representative cases:

```text
99840: quantity=100, MEDIUM/0.33, raw=33, rounded=0
83060: quantity=200, LIGHT/0.25, raw=50, rounded=0
43880: quantity=100, LIGHT/0.25, raw=25, rounded=0
76010: quantity=300, LIGHT/0.25, raw=75, rounded=0
67310: quantity=100, LIGHT/0.25, raw=25, rounded=0
```

The root cause is not a Submit or Execution loss. The REDUCE intent is converted to a zero quantity before order planning because the selected REDUCE fraction is not lot-aware for small holdings.

## Repeated Zero Semantics

Repeated lot-zero cases by symbol:

```text
67310: 7 total, max consecutive 3
83060: 6 total, max consecutive 2
99840: 6 total, max consecutive 5
40520: 2 total, max consecutive 1
76010: 2 total, max consecutive 2
30410 / 41650 / 43880 / 78860: 1 each
```

This is daily new PM decision behavior, not stale Pending carry-forward. Each observed 67310 row has a fresh daily PM decision id such as `pm-2023-07-20-67310-reduce`, `pm-2023-07-26-67310-reduce`, and so on.

## 67310 Timeline

67310 evidence:

```text
2023-07-19: BUY entered, quantity 100, reference price 2000.0
2023-07-20: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-07-26: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-07-27: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-07-28: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-08-01: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-08-04: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
2023-08-08: REDUCE, quantity 100, fraction 0.25, raw 25, rounded 0, no SELL plan
```

At latest complete inspected campaign artifact (`2023-08-08`), 67310 remains OPEN with current_quantity 100. The run-scoped campaign artifact reports realized/unrealized PnL as 0.0 for this open campaign; any future outcome label for 67310 must remain post-hoc and must not feed decision-time strategy inputs.

## Other Representative Cases

Lot-zero cases:

```text
99840: six 100-share MEDIUM REDUCE decisions in 2022-11, raw 33, rounded 0.
83060: six 200-share LIGHT REDUCE decisions in 2023-03/04, raw 50, rounded 0.
76010: two 300-share REDUCE decisions in 2023-05, raw 75/99, rounded 0.
40520: two 100-share REDUCE decisions in 2023-07, raw 33/50, rounded 0.
```

Minimum-notional zero cases are separate from lot-zero:

```text
37820: 11 cases where rounded lots exist but notional is below 50,000 JPY.
93180: 10 cases where rounded lots exist but very low price keeps notional below 50,000 JPY.
```

## Lifecycle Consistency Impact

No evidence shows Pending / Submit / Execution dropping an executable REDUCE. The four executable non-zero REDUCE decisions generated SELL_REDUCE runtime plans and matching SELL fills:

```text
2023-02-13 45940 quantity 300
2023-02-15 45940 quantity 300
2023-04-25 77190 quantity 300
2023-05-17 76010 quantity 200
```

For lot-zero REDUCE, lifecycle consistency currently treats the event as no-order continuation rather than a terminal SELL lifecycle. That is internally consistent, but it hides repeated unrealized REDUCE intent as successful continuation.

## BUY-Side Lot Architecture Comparison

BUY / ADD architecture has received explicit lot-boundary repairs:

```text
Phase22: Strategy cap / Safety hard-cap separation.
Phase28: ADD allocation bridge and lot-aware conversion.
Phase29-L18/L19: discrete-lot cap boundary and residual reallocation.
```

REDUCE has canonical intensity and quantity contracts, but it lacks an equivalent semantic policy for repeated below-lot REDUCE intent. The current design floors to zero to avoid oversell, preserves safety, and records no-order. It does not answer whether repeated REDUCE intent on a one-lot holding should escalate, reclassify, accumulate reduce debt, or be made lot-aware in PM.

## Performance Outcome Attribution

Post-hoc outcome labels for the 27 lot-zero semantic decisions:

```text
ZERO followed by later SELL/EXIT, campaign gain: 18
ZERO followed by later SELL/EXIT, campaign loss:  2
Continued HOLD at latest inspected artifact:      7
Insufficient evidence:                            0
```

This does not prove that lot-zero behavior is beneficial or harmful. It proves only that repeated REDUCE-to-zero is performance-relevant and should be represented as a strategy semantic, not merely as a mechanical no-order side effect.

## Architecture Gap Judgment

Classification:

```text
E_MULTI_CAUSAL
```

Components:

```text
C_STRATEGY_TO_EXECUTION_SEMANTIC_GAP:
  PM can repeatedly express REDUCE on one-lot/small-lot holdings while executable quantity remains zero.

B_OBSERVABILITY_GAP:
  Position Sizing collapses lot-zero and minimum-notional-zero into REDUCE_NOT_EXECUTABLE_BELOW_MINIMUM_OR_LOT,
  while Sell Planning has a sharper REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY contract.
```

Not classified as:

```text
A_EXPECTED_DESIGN only: NO
D_LIFECYCLE_DEFECT: NO
```

The current behavior is safety-preserving and internally consistent, but it is not a complete production-common semantic contract for repeated REDUCE intent below executable lot size.

## Regression Judgment

Regression confirmed:

```text
NOT_PROVEN
```

Reason:

```text
Existing docs show REDUCE partial quantity authority was added and preserved, but no evidence was found that a previous production-common lot-aware REDUCE escalation/debt/reclassification policy existed and was later removed.
```

## Production-Common Implications

Production-common repair is design-required before implementation:

```text
DESIGN_REQUIRED
```

The repair should not be Historical-specific. It should preserve:

- no oversell
- fail-closed review for malformed quantity authority
- PM / Sell Planning authority separation
- BUY / SELL independence
- Pending / Submit / Execution quantity contract integrity

## Candidate Design Options

Options for a follow-up design task:

```text
A. Keep current floor-to-zero, but improve observability and repeated-zero reporting.
B. Min-lot ceil for REDUCE when PM intent is strong enough, with explicit no-oversell constraints.
C. Reclassify below-lot REDUCE as HOLD_WITH_UNEXECUTABLE_REDUCE_INTENT.
D. Persist reduce debt / accumulated sell intent and execute when debt reaches one tradable unit.
E. Make PM decision lot-aware so one-lot holdings choose HOLD or EXIT instead of non-executable REDUCE.
```

Recommended direction:

```text
Design D/E hybrid for review: make PM aware of lot feasibility and preserve a production-common repeated-zero semantic.
```

Do not implement directly from this audit; first define the authority contract and tests.

## Recommended Next Task

```text
Phase29-L21T-AC - REDUCE Lot-Aware Semantic Contract Design
```

Suggested scope:

- define whether one-lot REDUCE should become HOLD, EXIT review, min-lot partial sell, or reduce-debt
- split observability reason codes for lot-zero vs minimum-notional-zero
- add focused fixtures for 67310 / 99840 / 83060
- prove no SELL over-quantity and no BUY/SELL coupling regression

## No-Change Confirmation

```text
Strategy code changed: NO
Runtime code changed: NO
Config changed: NO
Schema changed: NO
Pending mutated: NO
Ledger mutated: NO
Current mutated: NO
Target Historical run mutated by Codex: NO
Fresh-run executed by Codex: NO
Resume / replay / recovery executed by Codex: NO
Long Historical executed by Codex: NO
Phase30 entered: NO
```

Final status:

```text
RESUME_SAFE_NOW: NO - this task did not assess or repair the run-level halt.
NEXT_STEP_REQUIRED: Phase29-L21T-AC design before any REDUCE semantic implementation.
```
