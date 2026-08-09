# Phase28-D19: PM ADD Actual Runtime Path Minimal Repair

## Primary Judgment

```text
PHASE28_D19_PM_ADD_ACTUAL_RUNTIME_PATH_REPAIRED_SHORT_VALIDATION_PASS
```

Chain judgment:

```text
SAME_DAY_PM_ADD_TO_BUY_ADD_CONFIRMED_BY_FOCUSED_CHAIN_VALIDATION
```

Fresh Test Entry Decision:

```text
READY
```

Phase28-D19 implemented only the Runtime path repair needed for same-day PM ADD decisions to reach formal Strategy Position Management before Portfolio Construction. No resume, fresh run, long historical run, config change, schema change, threshold change, Portfolio Construction change, Position Sizing change, Runtime Planning change, Pending change, Approval change, Submit change, or Broker change was performed.

## Pre-Implementation Audit

Phase28-D18 confirmed the actual runtime mismatch:

```text
PM ADD decisions = 51
Strategy PM ADD actions = 0
BUY_ADD = 0
```

The audited runtime path was:

```text
run_daily_operation --job morning
↓
formal Strategy artifact generation
↓
Strategy PM reads _existing_pm_decisions(...)
↓
same-day PM decisions are still absent
↓
D12 helper receives empty decision mapping
↓
Strategy PM emits UNRESOLVED
```

Code positions after D19:

| Boundary | Evidence |
|---|---|
| Morning PM materialization | `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:616-647` |
| Formal Strategy generation | `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:648-665` |
| Strategy PM consumer | `src/ai_fund_lab_v2/strategy/shadow_runtime.py:226-234` |
| Same-day PM lookup | `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1344-1366` |
| Strategy PM source evidence | `src/ai_fund_lab_v2/strategy/position_management.py:377-423` |

The original first loss point was Strategy job input selection, not Portfolio Construction, Position Sizing, Runtime Planning, Phase28-C, or D12 action normalization.

## Repair Option Comparison

| Option | Judgment | Reason |
|---|---|---|
| A: move formal Strategy after sell_planning | Rejected | Too broad; reorders BUY/SELL responsibilities. |
| B: materialize existing Runtime PM producer before formal Strategy | Selected | Minimal wiring repair; preserves existing producer and downstream authorities. |
| C: read later/prior PM artifacts from Strategy | Rejected | Risks stale or future authority. |
| D: synthesize ADD inside Strategy | Rejected | Creates new PM authority and performance semantics. |
| E: infer ADD in Portfolio Construction | Rejected | Masks the producer/consumer defect and changes PC semantics. |

Selected repair: Option B.

## Implemented Repair

Only this runtime repair was implemented:

```text
Morning capability PASS
↓
existing Runtime PM producer materializes same-day PM decisions
↓
formal Strategy artifact generation
↓
Strategy PM consumes same-day PM decisions
↓
D12 normalizer receives actual ADD rows
```

Implementation details:

- `run_daily_operation.py` now runs `produce_position_management_decisions(...)` during `morning` after capability PASS and before formal `generate_strategy_shadow_for_day(...)`.
- `_existing_pm_decisions(...)` now skips a missing first candidate instead of returning empty immediately, then reads the same-day `runtime_state/position_management/<date>/position_management_decisions.json`.
- Strategy PM now records consumed PM decision artifact path, hash, business date, decision ids, and decision types in source evidence.

This does not make PM ADD an order. PM remains intent authority; Phase28-C, Portfolio Construction, Position Sizing, and Runtime Planning remain the canonical BUY_ADD chain.

## Validation

Focused validation:

```text
python3 -m pytest tests/strategy/test_phase22_d_position_management.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q
35 passed
```

Short regression:

```text
Phase28-C / D14 / D16 / D8 / D3 focused regression set
21 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-d19 python3 -m py_compile ...
PASS
```

JSON validation:

```text
PASS
```

The D19 focused fixture confirms:

```text
same-day PM decision artifact
↓
_existing_pm_decisions preserves ADD + source hash
↓
Strategy PM runtime-current adapter emits action=ADD
↓
source_pm_decision_ref and PM artifact lineage are preserved
```

The Phase28-C focused chain remains passing, including Portfolio Construction target-weight increase, Position Sizing positive quantity delta, and Runtime Planning canonical BUY_ADD mapping.

## Regression Results

| Area | Result |
|---|---|
| Same-day PM input lookup | PASS |
| Formal Strategy PM source authority | PASS |
| D12 ADD/HOLD/REDUCE/EXIT propagation | PASS |
| Phase28-C ADD chain | PASS |
| Ordinary BUY | PASS |
| Ordinary SELL | PASS |
| D14 Strategy SELL listed_info | PASS |
| D16/D8 SELL listed_info merge | PASS |
| D3 SELL pending reconciliation | PASS |
| Compile | PASS |
| JSON validation | PASS |

## Architecture Conformance

Runtime Authority violation:

```text
false
```

Performance semantics changed:

```text
false
```

The repair supplies the missing actual runtime input to an already-designed authority chain. It does not alter:

```text
Expected Edge
Incremental Investment Value
Opportunity Cost
cash / exposure / re-entry policy
Portfolio Construction
Position Sizing
Runtime Planning
Pending
Approval
Submit
Broker
Config / Schema / Threshold
```

## Open Gaps

- No fresh 100BD was executed by Codex in D19.
- Performance adoption remains unavailable until a fresh run proves BUY_ADD pending, submit, fill, and attribution.
- Re-entry and cash utilization remain downstream evidence topics if the next fresh run exposes them.

## Deliverables

```text
docs/phase_reports/phase28_d19_pm_add_actual_runtime_path_minimal_repair.md
reports/phase_reports/phase28_d19_pm_add_actual_runtime_path_minimal_repair.json
reports/phase28_d19_pm_add_actual_runtime_path_minimal_repair/
```

## Final Judgment

```text
ADD Producer: Runtime Position Management producer
ADD Consumer: Formal Strategy Position Management
First Previous Loss Point: Strategy job input selection / runtime ordering
Root Cause Repaired: same-day PM decisions are now materialized before formal Strategy generation
Phase28-C Direct Causality: no Phase28-C defect; D19 enables PM ADD to reach Phase28-C
D12 Relation: D12 retained; D19 supplies its missing actual runtime input
Runtime Defect: repaired
Minimal Repair Scope: Strategy job PM input selection / runtime ordering-wiring
Primary Recommendation: proceed to fresh runtime acceptance evidence collection
Next Phase: Phase28-D20 or user-run fresh 100BD acceptance evidence collection
```
