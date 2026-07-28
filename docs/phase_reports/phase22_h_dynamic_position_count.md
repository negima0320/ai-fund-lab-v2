# Phase22-H Dynamic Position Count

## Primary Judgment

```text
PHASE22_H_COMPLETE_WITH_UPSTREAM_REVIEW_REQUIRED
```

Dynamic Position Count foundation was implemented as a production-common, read-only Strategy artifact producer. It decides only position count fields and remains `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` for the production-style sample because upstream Market Context threshold/source decisions remain unresolved.

Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- Phase22-A / B / C / E / F / G / GR reports, schemas, code, and evidence

## Current Fixed Position Count Inventory

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/current_position_count_inventory.json
```

Current active position-count authority remains:

```text
src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py::CapitalDeploymentPolicy.max_positions
configs/runtime_v2/capital_deployment.json
configs/runtime_v2/capital_deployment_demo.json
```

Current value:

```text
Production max_positions = 5
Demo max_positions = 5
```

Morning Planning uses `policy.max_positions - current_position_count` to derive available BUY slots. ADD Planning receives the same explicit Runtime policy. Sell Planning records the policy in output metadata but does not use Dynamic Position Count. Pending, Submit, Safety, Status, and Summarize behavior were inventoried and not changed.

## Current Authority Inventory

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/current_authority_inventory.json
```

Authority separation:

- current hard max authority: Runtime v2 Capital Deployment Policy
- current target count authority: fixed active Runtime policy
- current available-slot calculation: Morning Planning
- current candidate Top-N authority: Candidate / Opportunity producers and Accepted Generation configs
- current safety cap: Runtime / Safety hard limit
- future Dynamic Position Count authority: Strategy Dynamic Position Count artifact

Phase22-HR later split the Strategy maximum and Safety hard maximum authority. Phase22-H itself remains a read-only foundation and does not let Strategy target override a resolved independent Safety hard maximum.

## Market Context Availability

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/market_context_availability.json
```

Phase22-A remains `PHASE22_A_REVIEW_REQUIRED` because the formal Market Context open decisions are still unresolved:

```text
trend threshold
volatility window
breadth threshold
benchmark source
sector source
```

Therefore Phase22-H uses Case B for production-style artifact generation: the producer foundation exists, but the artifact result remains `REVIEW_REQUIRED` until upstream Market Context taxonomy authority is formally closed.

## PIT Distribution Analysis

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/pit_distribution_analysis.json
```

No backtest PnL, historical run PnL, future return, paper ledger PnL, selected/bought result, or test result was used. Allowed distribution dimensions were inventoried only:

```text
eligible candidate count distribution
valid opportunity count distribution
market context metric distribution
breadth distribution
volatility distribution
trend strength distribution
```

Formal PIT percentile thresholds were not decided in this task because the upstream Market Context source/threshold decisions are still review-required.

## Threshold / Rule Rationale

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/threshold_rule_rationale.json
```

Implemented explicit count policy config:

```text
configs/strategy/dynamic_position_count.json
```

The config defines deterministic capacity rules for resolved inputs. Phase22-HR updated the Strategy maximum to be separable from the legacy active `max_positions=5`; production-style output remains `REVIEW_REQUIRED` while upstream Market Context taxonomy and independent Safety hard maximum authority are unresolved.

## Dynamic Position Count Responsibility

Implemented producer:

```text
src/ai_fund_lab_v2/strategy/dynamic_position_count.py
schemas/strategy/dynamic_position_count.schema.json
```

The artifact owns only:

```text
minimum_position_count
target_position_count
maximum_position_count
available_candidate_count
available_opportunity_count
current_position_count
position_count_posture
capacity_constraint_status
confidence
uncertainty
reason_codes
```

It does not decide symbols, weights, cash ratio, gross exposure, JPY allocation, share quantity, lot rounding, Pending, Submit, Execution, or Safety override.

## Input Contract

Inputs:

- Market Context summary
- Portfolio Policy summary
- Candidate availability summary
- Opportunity availability summary
- Current Portfolio summary
- independent Safety hard maximum, when formally defined
- explicit Dynamic Position Count config
- source refs and source hashes

Forbidden inputs remain unused: backtest result, future return, historical PnL, paper ledger PnL, current PnL, previous trade result, recent win rate, selected/bought result, audit result, and test result.

## Config Contract

Config schema:

```text
dynamic_position_count_config.v1
```

Required config families:

```text
minimum_position_count
maximum_position_count
safety_hard_maximum_reference
regime_rules
breadth_rules
volatility_rules
portfolio_policy_rules
opportunity_capacity_rules
uncertainty_rules
```

No implicit default is used. Config hash is recorded in the artifact.

## Schema

Artifact schema:

```text
dynamic_position_count.v1
```

The schema and validator enforce `DRAFT`, `NOT_ELIGIBLE`, source lineage, temporal safety, count hierarchy, Safety cap, capacity limits, no runtime switch, and legacy authority active.

## Count Hierarchy

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/count_hierarchy_validation.json
```

Validator-enforced relationship:

```text
0 <= minimum <= target <= maximum <= safety_hard_maximum
target <= available_candidate_count
target <= available_opportunity_count
```

Opportunity shortage and Candidate shortage lower the target; missing opportunities are not invented.

## Taxonomy

Implemented:

```text
position_count_posture:
INCREASE / MAINTAIN / DECREASE / PAUSE_NEW_ENTRY / UNRESOLVED

capacity_constraint_status:
SUFFICIENT / CANDIDATE_CONSTRAINED / OPPORTUNITY_CONSTRAINED /
MARKET_RISK_CONSTRAINED / UNCERTAINTY_CONSTRAINED /
SAFETY_CAP_CONSTRAINED / SOURCE_UNAVAILABLE
```

## Determinism

The producer uses only supplied inputs, explicit config, and business date. It uses no randomness, no current-time branch, no row-order-sensitive tie break, no latest fallback, and no previous-day target copy.

## Date / PIT / Hash / Lineage

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/date_pit_validation.json
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/hash_lineage_validation.json
```

Implemented checks:

- business date alignment
- `feature_date <= business_date`
- future source date -> `BLOCK`
- source hashes
- config hash
- artifact hash
- no implicit latest fallback
- no previous-day target copy

## Failure Contract

Implemented:

| Case | Result |
|---|---|
| required source missing | `REVIEW_REQUIRED` or `BLOCK` depending source status |
| Market Context unresolved | `REVIEW_REQUIRED` |
| config missing | `REVIEW_REQUIRED` |
| config invalid | config error / `BLOCK` |
| date mismatch | `BLOCK` |
| hash mismatch | `BLOCK` |
| Candidate count unavailable | `REVIEW_REQUIRED` |
| Opportunity count unavailable | `REVIEW_REQUIRED` |
| safety cap conflict | `BLOCK` |
| impossible count relationship | schema error / `BLOCK` |
| future leakage | `BLOCK` |

Fixed `5`, previous-day copy, and zero-position PASS fallbacks are not implemented.

## Bootstrap Contract

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/bootstrap_validation.json
```

Initial missing or unresolved inputs produce `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE`. The producer does not copy existing `max_positions`, previous-day target, or current count as a PASS fallback.

## Shadow Comparison

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/shadow_comparison.json
```

The artifact records:

```text
existing_active_max_positions
dynamic_minimum
dynamic_target
dynamic_maximum
difference_from_existing
would_change_available_slots
runtime_behavior_changed=false
```

This comparison is not consumed by Runtime.

## Runtime Preservation

Machine-readable evidence:

```text
reports/phase22_h_dynamic_position_count/phase22_h_evidence_20260727/runtime_preservation.json
```

Unchanged:

- `runtime_v2 CapitalDeploymentPolicy.max_positions`
- Morning Planning available-slot behavior
- ADD Planning
- Sell Planning
- Pending
- Submit
- Approval
- Execution
- Safety hard limit

Dynamic Position Count is read-only / shadow-only.

## Tests

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_h_dynamic_position_count.py
```

Result:

```text
8 passed
```

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py \
  tests/strategy/test_phase22_b_candidate_opportunity_compatibility.py \
  tests/strategy/test_phase22_c_portfolio_policy.py \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_f_capital_deployment.py \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/strategy/test_phase22_h_dynamic_position_count.py \
  tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py \
  tests/runtime_v2/test_phase15h_capital_deployment_policy.py \
  tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py \
  tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
92 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase22h \
python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy tests/runtime_v2
```

## Long Tests Not Executed

Not executed by Codex:

- 5BD
- 20BD
- 200BD
- 1-year
- 3-year
- long runtime smoke

## Design Freeze Compliance

Phase22-H preserves Phase21 Design Freeze boundaries:

- Production / Demo / Historical common producer
- no Historical-only position count logic
- no PnL optimization
- no Runtime switch
- no consumer eligibility promotion
- no legacy retirement
- no Pending / Submit / Execution mutation

## Blocking Gaps

None for the Phase22-H foundation.

## Non-blocking Gaps

Market Context formal threshold/source decisions remain upstream `REVIEW_REQUIRED`. This prevents declaring the production-style daily target as fully accepted, but it does not block the read-only Dynamic Position Count foundation.

## Next Gate

Phase22-I Dynamic Cash / Exposure may proceed as a read-only foundation only after preserving the same Runtime boundary. Runtime switch remains `NO`; legacy retirement remains `NO`.
