# Phase29-L19R Lot Sizing Repair Lineage and Regression Audit

Task ID: Phase29-L19R

Status:

```text
COMPLETE
READ_ONLY LINEAGE / REGRESSION AUDIT
NO PRODUCTION / STRATEGY / RUNTIME / CONFIG / SCHEMA CHANGE
NO HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L19R_MIXED_PRE_EXISTING_INCOMPLETE_IMPLEMENTATION_AND_PARTIAL_AUTHORITY_MIGRATION_GAP_NO_PROVEN_REGRESSION
```

L19 was still required. The audited issue was not a pure new concept and not a proven regression. It was a mixed gap:

- Phase22 introduced Strategy cap / Safety hard cap separation in Position Sizing evidence.
- Phase28 introduced a partial lot-aware PC/PS capital conversion repair.
- Before L19, those two authorities were not fully joined at the discrete lot boundary. The missing contract was explicit lot-count feasibility and boundary classification when minimum executable lots exceed Strategy cap headroom but may or may not fit under the independent Safety hard cap.

No earlier L19-equivalent implementation was found in the reviewed git lineage, and no later removal of an equivalent implementation was proven.

## Scope and Non-Mutation Assertions

This audit was read-only except for documentation/evidence creation.

The current 4-year Historical run was not touched:

```text
runtime-test-historical-smoke-20260811T055746254454Z
```

No resume, abandon, repair, fresh run, historical run, runtime state mutation, Pending mutation, Ledger mutation, Accepted Generation mutation, or broker-state mutation was performed.

## Lineage Findings

### Phase22

Relation:

```text
Strategy cap / Safety hard cap separation existed.
```

Evidence:

- Commit `55a7c63 phase22 FIX`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

Phase22 materialized:

- `strategy_maximum_position_weight`
- `safety_maximum_position_weight`
- `effective_maximum_position_weight`
- `effective_maximum_position_weight_derivation = min(strategy_maximum_position_weight, safety_maximum_position_weight)`

Limitation:

```text
No lot feasibility preflight, no discrete lot-boundary resolution, and no residual lot reallocation equivalent were found.
```

### Phase26

Relation:

```text
Phase26 preserved the cap authority while repairing Production architecture and legacy consumers.
```

Evidence:

- Commit `d470765 phase26 FIX`
- Same Position Sizing cap fields and effective cap derivation remained present.

Limitation:

```text
No L19-equivalent cap-constrained lot floor or iterative residual reallocation was found.
```

### Phase27

Relation:

```text
Phase27 established canonical PM architecture and performance attribution foundations.
```

Limitation:

```text
No evidence was found that Phase27 implemented lot-boundary resolution or cap-constrained residual reallocation.
```

### Phase28

Relation:

```text
Phase28 introduced the closest prior similar repair, but it was partial.
```

Evidence:

- Commit `1db2ce8 phase28 FIX`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py::apply_lot_aware_final_reallocation`
- `src/ai_fund_lab_v2/strategy/position_sizing.py::build_lot_feasibility_preflight`
- Phase28-D55-B tests in `tests/strategy/test_phase22_e_portfolio_construction.py` and `tests/strategy/test_phase22_j_position_sizing.py`

Phase28 covered:

- PC final lot-aware reallocation after PS preflight.
- Minimum executable lot promotion.
- Remaining budget block evidence.
- Concentration cap block evidence.
- High-rank skip and lower-rank funding.
- ADD lot rounding zero evidence.
- Positive ADD target/delta path preservation where lot-feasible.

Phase28 did not cover:

- `phase29_l19_lot_resolution`
- `maximum_strategy_feasible_lots`
- `maximum_safety_feasible_lots`
- Explicit strategy-vs-safety boundary classification.
- Candidate exhaustion under separated Strategy cap / Safety hard cap lot-count evidence.

## Regression Assessment

Regression is not confirmed.

Reason:

```text
No previous equivalent implementation was found and no subsequent removal of an equivalent implementation was proven.
```

The prior repair was similar only in part. Phase28 had lot-aware conversion authority, but not the L19-specific separated lot-boundary contract. Therefore L19 is best classified as completing an incomplete prior implementation and closing a partial authority migration gap, not restoring a removed equivalent behavior.

## Why Previous Tests Did Not Detect This

Previous tests did not detect the L19 issue because they covered adjacent contracts but not this exact boundary:

- Phase22/Phase26 tests asserted cap metadata and effective cap derivation, not discrete lot-count feasibility.
- Phase28-C tests proved ADD target-weight and quantity-delta propagation when feasible, not minimum-lot crossing of Strategy cap headroom.
- Phase28-D55-B tests proved lot-aware promotion, cash preservation, and high-rank skip/lower-rank funding, but did not classify Strategy cap block vs Safety hard-cap breach.
- Existing tests did not reproduce the 94320/78780 style boundary with current equity, PIT reference price, current quantity, trading unit, minimum executable lot, Strategy cap, and Safety hard cap all interacting.
- Residual reallocation tests did not assert full candidate exhaustion when all recipients are blocked by lot/cap constraints.

## ADD Non-Regression

This audit found no evidence that L19 weakens ADD.

L19R itself changed no Strategy code. The L19 implementation under audit extends the post-Phase28 ADD path by explaining why an economically accepted ADD may still resolve to zero executable quantity at the lot boundary. It does not remove Phase28-C ADD bridge semantics, does not revive legacy ADD execution authority, and does not alter SELL / REDUCE / EXIT behavior.

## Required Final Fields

```text
Primary Judgment:
PHASE29_L19R_MIXED_PRE_EXISTING_INCOMPLETE_IMPLEMENTATION_AND_PARTIAL_AUTHORITY_MIGRATION_GAP_NO_PROVEN_REGRESSION

L19 classification:
MIXED

Similar repair existed before: PARTIAL
Earliest similar implementation:
Phase22 / 55a7c63 / src/ai_fund_lab_v2/strategy/position_sizing.py / strategy-safety cap separation; Phase28 / 1db2ce8 / src/ai_fund_lab_v2/strategy/portfolio_construction.py::apply_lot_aware_final_reallocation and src/ai_fund_lab_v2/strategy/position_sizing.py::build_lot_feasibility_preflight
Phase22 relation:
Strategy cap / Safety hard cap separation existed, but no lot-boundary resolution or residual reallocation equivalent existed.
Phase26 relation:
Cap authority was preserved through Production architecture repair, but no L19-equivalent lot floor or iterative residual reallocation existed.
Phase27 relation:
Canonical PM architecture/performance evaluation lineage existed, but no lot-boundary implementation evidence was found.
Phase28 relation:
Closest partial predecessor. ADD bridge and lot-aware PC/PS capital conversion existed, but Strategy-vs-Safety discrete lot-boundary resolution did not.
Phase28 ADD repair included lot-boundary resolution:
PARTIAL
Cap-constrained lot floor existed before L19:
NO
Iterative residual reallocation existed before L19:
PARTIAL
Strategy cap / Safety hard cap separation existed before L19:
PARTIAL
Previous equivalent implementation later removed:
NOT_PROVEN
Regression confirmed:
NO
Authority migration gap confirmed:
PARTIAL
Why previous tests did not detect this:
They asserted cap metadata, positive ADD propagation, minimum executable promotion, remaining-budget blocks, and lower-rank funding separately, but did not test the discrete lot-count boundary where minimum executable lots exceed Strategy cap headroom while needing separate Safety hard-cap classification, nor full candidate exhaustion under that boundary.
L19 still required:
YES
L19 introduced duplicate/conflicting authority:
NO
Current 4-year Historical run touched:
NO
Production code changed:
NO
Strategy code changed:
NO
Runtime code changed:
NO
Config changed:
NO
Schema changed:
NO
Runtime mutated:
NO
Pending mutated:
NO
Ledger mutated:
NO
Historical executed:
NO
Fresh-run executed:
NO
Resume executed:
NO
Recommended next action:
Do not re-open L19 as a regression rollback. Keep L19 as the required completion of Phase28's partial lot-aware repair, then proceed only through the approved operator-owned long-horizon validation gate; include L19 boundary fixtures in future ADD/BUY_NEW lot-sizing regression suites.
```

## Deliverables

```text
docs/phase_reports/phase29_l19r_lot_sizing_repair_lineage_and_regression_audit.md
reports/phase29_l19r_lot_sizing_repair_lineage_and_regression_audit/
```

