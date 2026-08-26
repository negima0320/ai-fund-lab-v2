# Phase31-G119 — PC Final Discrete Authority / Deployment-Set / PS Consistency Repair

## PRIMARY_JUDGMENT

G119_PC_FINAL_AUTHORITY_PS_CONSISTENCY_REPAIR_ACCEPTED

## Scope

- Phase: Phase31
- Repair owner: Position Sizing consumer boundary
- Target defect: PC final positive executable quantity authority was zeroed by stale deployment-set Cash-winner evidence.
- Fresh-run/resume/replay/long Historical executed: NO
- Strategy parameter / Market Quality / Risk Pacing / ranking changes: NO
- G115 ADD staged marginal semantics changed: NO
- G117 normal NEW_BUY scope repair changed: NO
- Safety / Submit / Runtime priority changed: NO

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g115_add_marginal_competition_staged_authoritative_binding.md`
- `docs/phase_reports/phase31_g116_post_g115_normal_buy_collapse_actual_path_audit.md`
- `docs/phase_reports/phase31_g117_g115_normal_buy_scope_narrow_repair.md`
- `docs/phase_reports/phase31_g118_post_g117_early_actual_allocation_completeness_audit.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

## Root Cause

The contradictory binding was produced in:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
_apply_canonical_deployment_set_to_sizing_rows()
```

When `canonical_deployment_set.cash_winner = True` and no G61 multi-selection was found, the Position Sizing preprocessor applied `_zero_incremental_deployment_row()` to normal `NEW_BUY` rows even when the same PC final row already carried:

```text
phase29_l19_lot_resolution.final_allocated_quantity > 0
pc_positive_executable_quantity_authority.status = PASS
ps_must_consume_canonical_quantity = True
```

This was a stale/pre-final deployment-set interpretation being revived after PC final lot-aware selection.

- `CONTRADICTORY_BINDING_PRODUCER = position_sizing._apply_canonical_deployment_set_to_sizing_rows`
- `CONTRADICTORY_BINDING_TIMING = D`

Timing `D` means separate consumer normalization after PC final allocation.

## Repair

Added a narrow PS consumer reconciliation:

- Detect final PC discrete executable authority on normal `NEW_BUY` / `REENTRY` rows.
- If authority is valid and final quantity is positive, keep the row selected for sizing.
- Rewrite the row-local deployment binding to `SELECTED_BY_PC_FINAL_DISCRETE_AUTHORITY`.
- Prevent stale `cash_winner=true` / `DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION` from zeroing that final PC-selected row.
- Leave true final Cash losers, invalid authority, missing authority, and zero final quantity unchanged.

This repair does not let PS re-rank Strategy competition. PS consumes the final PC authority and still applies its existing quantity, lot, cap, and safety checks.

Changed:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`

Added:

- `tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py`

Updated SoT:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

## Authority Precedence

Permanent rule added to SoT:

```text
PC final lot-aware allocation
-> PC final positive executable quantity authority
-> PS consumes final PC quantity authority
```

Earlier/preliminary deployment-set Cash evidence is input/context after PC final selection and must not zero a final PC-selected positive row.

This precedence does not override Safety, valid hard-cap failure, malformed authority, genuine lot infeasibility, Submit feasibility, or execution availability.

`FINAL_AUTHORITY_PRECEDENCE_DEFINED = YES`

## Actual-Shape Gates

READ-ONLY producer-equivalent evaluation was performed against existing G118 artifacts from:

```text
runtime-test-historical-extended-smoke-20260825T131857659091Z
```

No run artifact was modified.

### Gate A — 2022-10-03

The seven baseline normal BUY anchors remain positive:

| Symbol | PS quantity after G119 evaluation |
|---|---:|
| 33700 | 100 |
| 37820 | 400 |
| 83060 | 100 |
| 89180 | 3700 |
| 92420 | 100 |
| 93600 | 100 |
| 94340 | 200 |

`20221003_NORMAL_BUY_GATE = PASS`

### Gate B — 2022-10-12 / 65500

After G119 evaluation:

```text
PC final qty = 100
PC authority = PASS
PS qty = 100
Runtime-compatible BUY_NEW qty = 100
```

The stale `cash_winner=true` binding is no longer used to zero the row.

`20221012_65500_GATE = PASS`

### Gate C — 2022-10-12 ADD

The G115 ADD one-increment rows remain positive:

| Symbol | PM action | PS quantity | PC authority consumed |
|---|---|---:|---|
| 94320 | ADD | 100 | YES |
| 94340 | ADD | 100 | YES |

`20221012_ADD_GATE = PASS`

### Gate D — True Cash Winner

The new regression confirms a final Cash loser with zero/invalid PC final authority remains zero.

`TRUE_CASH_WINNER_GATE = PASS`

## G118 Leakage Rows

G118 identified 15 PC-final-positive / PS-zero normal `NEW_BUY` rows.

After G119 producer-equivalent evaluation:

- Positive PS quantity rows: `15 / 15`
- PC discrete authority directly consumed: `11`
- Existing one-lot discrete authority consumed: `4`
- Remaining unexplained PC-final-positive -> PS-zero rows: `0`

Rows reconciled:

| Date | Symbol | Result |
|---|---|---|
| 2022-10-04 | 41650 | PS positive |
| 2022-10-04 | 76470 | PS positive |
| 2022-10-04 | 59860 | PS positive |
| 2022-10-04 | 44870 | PS positive |
| 2022-10-05 | 33500 | PS positive |
| 2022-10-05 | 41650 | PS positive |
| 2022-10-05 | 76470 | PS positive |
| 2022-10-06 | 65500 | PS positive |
| 2022-10-06 | 44220 | PS positive |
| 2022-10-06 | 45750 | PS positive |
| 2022-10-07 | 36000 | PS positive |
| 2022-10-07 | 33500 | PS positive |
| 2022-10-11 | 76470 | PS positive |
| 2022-10-12 | 65500 | PS positive |
| 2022-10-12 | 76470 | PS positive |

`G118_LEAKAGE_ROWS_RECONCILED = 15/15`

`UNEXPLAINED_PC_FINAL_TO_PS_ZERO_COUNT = 0`

## Regression Results

PASS:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py
4 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py
10 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py
276 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py \
  -k 'not actual'
23 passed, 6 deselected
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py
11 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/safety/test_reconciliation.py \
  tests/safety/test_lock_state_resolver.py
57 passed
```

Artifact-dependent attempted command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py \
  tests/strategy/test_phase31_g117_normal_buy_scope_repair.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g113_add_marginal_competition_shadow.py \
  tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py \
  tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py \
  tests/strategy/test_phase31_g102_item_scoped_pc_discrete_quantity_authority.py \
  tests/strategy/test_phase31_g104_g102_item_scoped_pc_discrete_authority_submit_recognition.py \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py
```

Result:

```text
no tests ran
ERROR: file or directory not found: tests/strategy/test_phase31_g104_g102_item_scoped_pc_discrete_authority_submit_recognition.py
```

The G104 test file is not present in this workspace.

Artifact-dependent actual cases were also attempted without G104:

```text
2 failed, 26 passed, 1 skipped
```

Both failures were `FileNotFoundError` for missing referenced historical run artifacts:

- `runtime-test-historical-extended-smoke-20260825T072702567342Z`
- `runtime-test-historical-extended-smoke-20260824T203644021876Z`

No behavioral assertion failed in those artifact-dependent cases.

## Compile / Hygiene

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py
```

PASS:

```text
git diff --check
```

## Required Judgments

- `G119_PC_FINAL_PS_CONSISTENCY_REPAIRED = YES`
- `CONTRADICTORY_BINDING_PRODUCER = position_sizing._apply_canonical_deployment_set_to_sizing_rows`
- `CONTRADICTORY_BINDING_TIMING = D`
- `PC_FINAL_DISCRETE_AUTHORITY_IS_FINAL_STRATEGY_CAPITAL_AUTHORITY = YES`
- `PC_FINAL_ROW_INTERNAL_CONSISTENCY = YES`
- `PS_STRATEGY_COMPETITION_REDECISION = NO`
- `G118_LEAKAGE_ROWS_RECONCILED = 15/15`
- `UNEXPLAINED_PC_FINAL_TO_PS_ZERO_COUNT = 0`
- `TRUE_FINAL_CASH_WINNER_STILL_ZERO = YES`
- `G115_ADD_BEHAVIOR_PRESERVATION_GATE = PASS`
- `NORMAL_NEW_BUY_CASH_PREFERRED_HARD_SKIP = NO`
- `20221003_NORMAL_BUY_GATE = PASS`
- `20221012_65500_GATE = PASS`
- `20221012_ADD_GATE = PASS`
- `TRUE_CASH_WINNER_GATE = PASS`
- `FINAL_AUTHORITY_PRECEDENCE_DEFINED = YES`
- `SAFETY_CHANGED = NO`
- `SUBMIT_CHANGED = NO`
- `RUNTIME_PRIORITY_CHANGED = NO`
- `FUTURE_INFORMATION_USED = NO`
- `HISTORICAL_OUTCOME_USED = NO`
- `G119_ACCEPTED = YES`

## Final Decision

G119_PC_FINAL_AUTHORITY_PS_CONSISTENCY_REPAIR_ACCEPTED
