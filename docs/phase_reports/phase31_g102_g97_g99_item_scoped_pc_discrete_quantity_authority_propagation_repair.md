# Phase31-G102 - G97/G99 Item-Scoped PC Discrete Quantity Authority Propagation Repair

## PRIMARY_JUDGMENT

`PHASE31_G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY_REPAIRED_ACCEPTED`

G101で確定したproducer gapだけを修理した。

```text
G97/G99 positive reconsideration
-> G61 LOT_EXECUTABLE_COMPATIBLE
-> canonical executable quantity materialized by PC
-> item-scoped PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY = PASS
-> Position Sizing consumes exactly that quantity
-> Runtime/Pending can preserve the same authority lineage
-> Submit validates through existing canonical_discrete_quantity_submit_authority
```

Submitは変更していない。SubmitがPS数量、Runtime数量、G97 provenance、aggregate allocationからauthorityを推論する経路は作っていない。

## Files Changed

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Repair Summary

Portfolio Construction now attaches G102 item-scoped PC discrete quantity authority only when all of the following are true:

```text
residual_reconsideration_authoritative_binding = true
G61 compatibility_state = LOT_EXECUTABLE_COMPATIBLE
projected_quantity_delta_evidence_only > 0
quantity is a multiple of canonical trading unit
authorized_allocation_weight > 0
minimum executable lot weight exists
```

The emitted authority is:

```text
authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
status = PASS
final_allocated_quantity = G61 projected executable quantity
ps_must_consume_canonical_quantity = true
future_information_used = false
```

Position Sizing now copies this G102 `phase29_l19_lot_resolution` from the selected multi-allocation row into the sizing row before quantity calculation. This lets the existing PS `pc_discrete_quantity_authority_consumed` path consume the authority. PS still owns discrete quantity conversion and does not re-decide capital priority.

No PASS authority is created for lot-infeasible, Cash-deferred, or Safety-terminal reconsideration rows.

## Primary Anchor

Actual producer-equivalent evaluation on:

```text
runtime-test-historical-extended-smoke-20260824T203644021876Z
2023-03-22 / 94320
```

Result after G102:

```text
G97 positive = YES
G61 = LOT_EXECUTABLE_COMPATIBLE
G61 projected quantity = 200
PC discrete authority = PASS
final_allocated_quantity = 200
ps_must_consume_canonical_quantity = true
future_information_used = false
semantic_type = BUY_NEW
```

Focused PS regression confirms:

```text
PS pc_discrete_quantity_authority_consumed = true
PS pc_discrete_authorized_quantity = 200
PS quantity_delta_candidate = 200
canonical_sizing_evidence.quantity_delta = 200
position_sizing_recomputes_capital_priority = false
lower_priority_implicit_promotion_allowed = false
```

Submit PASS is covered by the unchanged existing Submit feasibility contract: when the Pending item embeds this authority and item quantity equals `final_allocated_quantity`, `canonical_discrete_quantity_submit_authority` resolves to `PASS`.

## False-Pass Preservation

The G99 lot-infeasible anchors remain non-PASS:

```text
2023-04-07 / 83060 = LOT_INFEASIBLE_RESIDUAL_REQUIRED / authority != PASS
2023-04-07 / 77760 = LOT_INFEASIBLE_RESIDUAL_REQUIRED / authority != PASS
2023-04-07 / 44440 = LOT_INFEASIBLE_RESIDUAL_REQUIRED / authority != PASS
```

Cash/Safety semantics are unchanged by the repair. G102 does not alter G90/G97/G99 participation semantics.

## Population Reconciliation

Using existing run artifacts read-only, then applying G102 producer-equivalent PC evaluation:

```text
G97_RUNTIME_BUY_ROWS = 26
PC_DISCRETE_AUTHORITY_PASS = 26
PENDING_ITEM_PRESENT in existing pre-G102 artifacts = 9
SUBMIT_AUTHORITY_PASS in existing pre-G102 artifacts = 0
LEGITIMATE_NON_PASS = 0 among the 26 Runtime-visible executable rows
UNEXPLAINED_RUNTIME_TO_PENDING_ROWS = 17
```

Important separation:

The 17 missing Runtime-to-Pending rows from G101 are still a separate visibility/materialization issue in existing pre-G102 artifacts. G102 does not silently fold them into this repair. It fixes the PC authority producer and PS consumption boundary for rows that do materialize.

Some existing pre-G102 Runtime quantities differ from the newly materialized G102 producer-equivalent PC quantity. Those artifacts were produced before G102 and must not be treated as post-G102 reconciliation evidence. Post-G102 reconciliation must be evaluated through the regenerated PC -> PS -> Runtime -> Pending path.

## Normal BUY Preservation

Normal BUY_NEW and BUY_ADD paths are unchanged. Existing successful BUY paths still rely on the same item-scoped PC discrete authority:

```text
2022-10-03 / 33700 BUY_NEW
2022-10-03 / 89180 BUY_NEW
2023-03-22 / 67750 BUY_NEW
2023-03-22 / 58200 BUY_NEW
2022-10-12 / 94320 BUY_ADD
2022-11-04 / 94320 BUY_ADD
```

G102 only adds the same authority shape to G97/G99 executable reconsideration rows.

## SoT Update

Updated `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` with the permanent G102 contract:

```text
G97/G99 LOT_EXECUTABLE_COMPATIBLE
-> PC item-scoped discrete executable quantity authority PASS
-> PS consumes
-> Runtime/Pending preserve
-> Submit validates
```

It also states explicitly that Submit must not infer authority from PS quantity, Runtime quantity, G97 provenance, or aggregate allocation alone.

## Focused Tests

Command:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
```

Result:

```text
302 passed
```

Additional:

```text
tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py = 3 passed
PY_COMPILE = PASS
GIT_DIFF_CHECK = PASS
```

Note: the pre-existing G99 test file references `runtime-test-historical-extended-smoke-20260824T121719329586Z`, which is not present in this workspace. G102 adds available-run anchor coverage instead of relying on that absent artifact.

## Required Acceptance

```text
G97_G99_PC_DISCRETE_QUANTITY_AUTHORITY_REPAIRED = YES
SUBMIT_FAIL_CLOSED_CHANGED = NO
PS_QUANTITY_AUTHORITY_CHANGED = NO
RUNTIME_PRIORITY_CHANGED = NO
SAFETY_CHANGED = NO
NORMAL_BUY_DISCRETE_AUTHORITY_CHANGED = NO
LOT_INFEASIBLE_FALSE_PASS_COUNT = 0
CASH_DEFER_FALSE_PASS_COUNT = 0
SAFETY_TERMINAL_FALSE_PASS_COUNT = 0
20230322_94320_PC_AUTHORITY_PASS = YES
20230322_94320_SUBMIT_AUTHORITY_PASS = YES in focused producer-equivalent Pending/Submit contract
AUTHORITATIVE_QUANTITY_RECONCILIATION = PASS in focused PC -> PS path
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
G102_ACCEPTED = YES
```

## Run Handling

```text
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
RUN_STATE_MUTATED = NO
MARKET_QUALITY_CHANGED = NO
RISK_PACING_CHANGED = NO
CANDIDATE_RANKING_CHANGED = NO
ADD_COMPETITION_CHANGED = NO
G90_CHANGED = NO
G97_SEMANTICS_CHANGED = NO
G99_LOT_CONTEXT_SEMANTICS_CHANGED = NO
SUBMIT_WEAKENED = NO
```

## Next

User-operated validation may proceed with a fresh/resume path only when desired. If another halt appears, audit that exact next boundary; do not redesign G90/G97/G99, Market Quality, Risk Pacing, Safety, PS ownership, or Runtime priority from this repair.
