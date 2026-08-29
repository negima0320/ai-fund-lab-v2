# Phase32-BG Explicit Production Consumer Switch Implementation

## Executive Summary

Phase32-BG explicitly switched the accepted BC/BF marginal-capital authority to
the production PC-to-PS target boundary.

Production path after BG:

```text
PM / candidate evidence
-> canonical_marginal_capital_frontier_authority.v1
-> pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]
-> Position Sizing
-> Runtime
```

The switch is explicit and narrow:

```text
pc_to_ps_production_consumer_switch.v1
target_authority_source = BF_AGGREGATED_PS_BOUNDARY_ONLY
production_consumers = [strategy.position_sizing]
production_consumer_count = 1
shadow_frontier_production_consumer_count = 0
```

No PM, PS quantity arithmetic, Runtime, Safety, REDUCE, or EXIT logic was
changed. Production behavior changes because Position Sizing now consumes the
new PC authority when it is present and valid.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bf_pc_to_ps_consumer_switch_boundary_validator.md`
- `docs/phase_reports/phase32_bc_budget_bounded_frontier_acceptance_implementation.md`
- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

## Implementation

Changed files:

| File | Change |
| --- | --- |
| `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py` | Added explicit activation helper for `pc_to_ps_production_consumer_switch.v1`. |
| `src/ai_fund_lab_v2/strategy/position_sizing.py` | Added PS consumer adapter for active BF aggregated boundary rows. |
| `src/ai_fund_lab_v2/strategy/shadow_runtime.py` | Materializes active authority during final PC construction and embeds it into final PC before final PS. |
| `tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py` | Added focused BG switch regressions. |
| Architecture SoT files | Added BG consumer-switch contract and old-path classification. |

## Authority Activation

`activate_pc_to_ps_production_consumer_switch()` converts a valid disabled
BC/BF authority payload into an active PC-to-PS authority only when:

- `authority_result.status = PASS`
- `capital_conservation.status = PASS`
- `pc_to_ps_consumer_switch_boundary.status = PASS`
- BF boundary fallback flags are false
- shadow frontier remains non-authoritative
- no prior production consumer is already active

Invalid authority remains fail-closed `REVIEW_REQUIRED`.

## PS Consumer Switch

Position Sizing now checks for:

```text
portfolio_construction.canonical_marginal_capital_frontier_authority
```

or the same object under `capital_competition`.

When present, the active BG authority supersedes old canonical deployment-set
selection for incremental BUY rows. Position Sizing consumes only:

```text
pc_to_ps_consumer_switch_boundary.aggregated_ps_targets[]
```

Selected target rows are converted into existing PS-compatible fields:

- `target_weight`
- `accepted_incremental_weight`
- `accepted_buy_new_weight`
- `lot_aware_accepted_incremental_weight`
- `phase29_l19_lot_resolution`
- `pc_positive_executable_quantity_authority`
- `semantic_buy_type`
- campaign and candidate lineage

ADD #1/#2/#N is connected as one net quantity delta through the BF aggregated
target row.

## No-Fallback Boundary

For switched rows:

```text
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
position_sizing_recomputes_capital_priority = false
ordinary_lot_feasibility_priority_redecision_allowed = false
```

Missing or invalid active authority sets the Position Sizing artifact to
`REVIEW_REQUIRED`; it does not consume the old target-gap or ADD zero path.

## Runtime Generator Hook

The strategy generation pipeline now materializes:

```text
strategy/marginal_capital_frontier_authority.json
```

during final Portfolio Construction. The active authority is embedded into:

```text
strategy/portfolio_construction.json#canonical_marginal_capital_frontier_authority
```

before final Position Sizing runs.

## Path Classification

| Path | Classification |
| --- | --- |
| PM intent/evidence | KEEP |
| Candidate/opportunity/buy-quality evidence | KEEP |
| BC marginal capital value authority | MIGRATE |
| BF aggregated PC-to-PS boundary rows | MIGRATE |
| Existing PS target-to-quantity conversion | KEEP |
| Runtime/Pending/Orders/Execution mapping | KEEP |
| Safety / Risk Pacing / cap guardrails | KEEP |
| REDUCE / EXIT | KEEP |
| Legacy target-gap source for switched rows | REMOVE |
| Legacy ADD zero fallback for switched rows | REMOVE |
| Shadow frontier production consumption | FORBIDDEN |

## Focused Verification

Executed:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result:

```text
7 passed
```

Executed:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py
```

Result:

```text
151 passed
```

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
```

Result:

```text
PASS
```

One broader exploratory command also included
`tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py`;
two tests in that file failed because their referenced historical artifact
runs are absent locally. The remaining tests in that command passed.

## Regression Coverage

Focused BG regressions cover:

- NEW switched target
- REENTRY switched target
- ADD 3 lots -> net +300 shares
- Cash/no-deployment path
- missing/invalid authority fail-closed
- legacy fallback impossible
- PS final quantity delta correctness
- Runtime/Pending lineage preservation fields
- deterministic output
- consumer ownership
- shadow consumer count = 0

## Guardrails

Preserved:

- cap and safety checks in existing PS authority
- Cash and allocation budget conservation from BC/BF authority
- no-loss-averaging evidence from ADD authority
- Risk Pacing evidence carried by the source authority
- PIT-only / deterministic payload construction
- future/outcome parameter selection prohibition

Not changed:

- PM logic
- PS quantity arithmetic
- Runtime logic
- Pending / Order / Execution logic
- Safety authority
- REDUCE / EXIT logic

## Final Judgments

```text
PHASE32_BG_PRODUCTION_CONSUMER_SWITCHED = YES
PHASE32_BG_BF_ONLY_TARGET_AUTHORITY = YES
PHASE32_BG_MULTI_LOT_ADD_CONNECTED = YES
PHASE32_BG_LEGACY_FALLBACK_ZERO = NO
PHASE32_BG_PS_QUANTITY_LOGIC_CHANGED = NO
PHASE32_BG_RUNTIME_LOGIC_CHANGED = NO
PHASE32_BG_GUARDRAILS_PRESERVED = YES
PHASE32_BG_REGRESSION_STATUS = PASS
PHASE32_BG_SHORT_FRESH_VALIDATION_READY = YES
PHASE32_BG_PRODUCTION_BEHAVIOR_CHANGED = YES
PHASE32_BG_NEXT_STEP = Run a short user-operated fresh validation to verify first-day authority materialization, PS consumption, runtime mapping, and no legacy fallback on actual production artifacts.
```
