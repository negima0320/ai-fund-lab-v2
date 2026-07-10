# Phase15-C Runtime Architecture v2 Design / Implementation Gap Audit

## Summary

Phase15-C audited the gap between `docs/02_architecture/runtime_architecture_v2.md` and the current Runtime v2 implementation.

Purpose:

```text
設計契約と実装の差分を、Runtime Evidence Firstで明確化すること
```

This audit is static and evidence-based. It reviewed source code, CLI wiring, manifests/report output code, and regression test files. It did not run Runtime, Submit, Broker Write, Demo order, Production order, Notification real send, launchd/plist, or Current direct edit.

Final judgment: **PHASE15C_RUNTIME_DESIGN_IMPLEMENTATION_GAP_AUDIT_COMPLETE**

## Reviewed Evidence

Primary design:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase15_a_purpose_goal_definition.md`
- `docs/phase_reports/phase15_b_runtime_architecture_v2_purpose_based_design_review.md`

Primary implementation evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/*`
- `src/ai_fund_lab_v2/runtime_v2/audit/*`
- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/reader.py`

Regression evidence:

- `tests/runtime_v2/test_phase13_l_path_resolver.py`
- `tests/runtime_v2/test_phase13_m_current_state_no_history_fallback.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`
- `tests/runtime_v2/test_phase14e34_notification_component_completion.py`
- `tests/runtime_v2/test_phase14e35_market_refresh_actual_feature_generation.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`
- `tests/runtime_v2/test_phase13_t_delivery_ledger.py`

## Key Findings

### 1. Submit Guard hidden cap is still present in implementation

`run_submit_pipeline(...)` still has:

```text
max_order_amount: float | None = 100_000.0
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:90-100`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:139-152`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py:162-163`

This is a direct Phase15-B contract mismatch. The cap is not emitted as active policy and applies after Pending/Approval. It is also side-neutral in `run_submit_preflight`.

Classification: `CONTRACT_MISMATCH / HIDDEN_POLICY_RISK`

Severity: `BLOCKER`

### 2. Morning Planning has hidden position count and order amount limits

`run_morning_ai_planning_pending_pipeline(...)` still defaults:

```text
max_orders: int = 5
```

and derives:

```text
per_order_budget = min(float(planning_budget) / max(max_orders, 1), 100_000.0)
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:97-105`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:213`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:343`

This conflicts with the Phase15-B Purpose-Based Runtime Control Contract unless these values are converted into explicit Capital Deployment Contract / Risk Policy inputs and emitted to manifest/report/audit.

Classification: `CONTRACT_MISMATCH / HIDDEN_POLICY_RISK`

Severity: `BLOCKER`

### 3. Submit Guard Active Policy Manifest is not implemented

The design requires fields such as:

```text
guard_policy_version
active_amount_policy
capital_allocation_amount
max_buy_order_amount
max_sell_liquidation_amount
target_investment_ratio
cash_buffer
max_position_weight
max_positions
notional_guard_source
quantity_guard_source
current_position_source
broker_available_quantity_checked
guard_decision
manual_review_required
```

The current submit result/stage details include item status and counts, but no active guard policy object.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:36-80`
- `src/ai_fund_lab_v2/runtime_v2/submit/models.py:21-44`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:283-316`

Classification: `EVIDENCE_MISSING / PARTIAL`

Severity: `HIGH`

### 4. CLI regular path is partial

The Runtime v2 CLI accepts only:

```text
daily_rehearsal
morning
sell_planning
submit
execution
market_refresh
```

It does not expose separate `feature_refresh`, `report`, `notification`, or `audit` jobs even though Phase15-C requested them as review targets.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:42-49`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:260-265`

Report/notification/audit artifacts are generated as tail stages of every CLI run, not as independently reviewable regular jobs.

Classification: `PARTIAL / NOT_CONNECTED`

Severity: `MEDIUM`

### 5. Current / History / Derived contract is mostly implemented and tested

Current fixed paths are implemented through `resolve_current_path(...)` and `read_current_state(...)`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/storage/path_resolver.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/reader.py`
- `tests/runtime_v2/test_phase13_l_path_resolver.py:23-72`
- `tests/runtime_v2/test_phase13_m_current_state_no_history_fallback.py:7-107`

Report loader reads fixed Current paths and rejects mode-rooted current sources.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py:13-26`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py:87-106`

Classification: `IMPLEMENTED / REGRESSION_PRESENT`

Severity: `LOW`

### 6. SELL source Current-only is implemented in planning, but Submit Broker quantity evidence is not true Broker ReadOnly evidence

SELL Planning reads from `persistent_ledger/state.json` and tests exclude broker-only ledger position evidence.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:142-152`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py:7-68`

Submit preflight checks SELL quantity and available quantity, but the regular submit pipeline supplies both `broker_position_quantity` and `broker_available_quantity` from Current positions:

```text
broker_position_quantity=sell_position_quantity
broker_available_quantity=sell_position_quantity
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:131-152`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py:153-161`

This means the design concept exists, but the regular submit path does not yet prove Broker available quantity from Broker ReadOnly evidence.

Classification: `PARTIAL / EVIDENCE_MISSING`

Severity: `HIGH`

### 7. Notification is Level1/partial Level2, not delivery acceptance

Notification payload, queue, sender stubs, delivery ledger dedup, and audit checks exist. CLI output remains payload-only and reports `notification_sent=false`.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/notification/payload.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/queue.py`
- `src/ai_fund_lab_v2/runtime_v2/notification/delivery_ledger.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:260-265`
- `tests/runtime_v2/test_phase14e34_notification_component_completion.py`
- `tests/runtime_v2/test_phase13_t_delivery_ledger.py`

Classification: `PARTIAL / NOT_CONNECTED`

Severity: `MEDIUM`

## Runtime Core Flow Matrix

| Component | Design Responsibility | Implementation Module | CLI Status | Evidence / Manifest Status | Regression Status | Review Level | Gap |
|---|---|---|---|---|---|---|---|
| Market Refresh | Actual market/feature refresh, no checkpoint-only PASS | `runtime_v2/market_refresh/pipeline.py` | `CLI_CONNECTED` as `market_refresh` | Manifest records generated feature artifacts | `REGRESSION_PRESENT` via Phase14-E35 tests | Level2 | No major static gap |
| Feature Refresh | Feature artifact availability for AI inputs | Folded into market refresh / feature artifacts | `PARTIAL`; no separate `feature_refresh` job | Feature artifact dir recorded by market_refresh | `PARTIAL` | Level1/2 | Separate CLI job missing |
| Current State Read | Fixed Current only | `current_state/reader.py`, `storage/path_resolver.py` | Preflight in CLI | Fixed paths validated | `REGRESSION_PRESENT` | Level1/2 | No major static gap |
| AI Execution | AI outputs consumed, AI logic not in Runtime | `planning/morning_pipeline.py` uses feature fixtures/inputs | `CLI_CONNECTED` through `morning` | Stage details emitted | `PARTIAL` | Level2 | Full AI chain is simplified |
| Planning BUY | Build order plan from AI/Capital/Safety/Current | `planning/morning_pipeline.py`, `planner.py` | `CLI_CONNECTED` | Stage details emitted | `PARTIAL` | Level2 | Hidden `max_orders=5` and 100k per-order cap |
| Planning SELL | Use Current-owned positions only | `planning/sell_pipeline.py`, `planner.py` | `CLI_CONNECTED` as `sell_planning` | Stage details emitted | `REGRESSION_PRESENT` | Level2 | Safety is placeholder allow |
| Pending | Fixed pending Current | `pending/*` | Connected through morning/sell planning/submit | Pending path emitted | `REGRESSION_PRESENT` | Level2 | No major static gap |
| Approval | Approval linked to Pending | `approval/*` | Connected through morning/sell planning/submit | Approval path emitted | `REGRESSION_PRESENT` | Level2 | Auto-approval policy needs Phase15 review |
| Submit | Pending-only non-idempotent Broker submit | `submit/pipeline.py`, `submit/guards.py` | `CLI_CONNECTED` as `submit` | Counts and item results emitted | `PARTIAL` | Level2 | Hidden 100k cap, active policy manifest missing |
| Broker | Demo Submit adapter / ReadOnly evidence | `broker/runtime_v2_demo_submit_adapter.py`, `execution/readonly_pipeline.py` | Submit/execution connected | Broker hashes/classification emitted | `PARTIAL` | Level2 | Production not connected, Broker available qty not true ReadOnly in submit |
| Execution / Fill | Broker ReadOnly -> execution acceptance | `execution/readonly_pipeline.py` | `CLI_CONNECTED` as `execution` | Stage details emitted | `REGRESSION_PRESENT` | Level2 | Runtime evidence required for Level3 |
| Ledger | Orders/executions/positions/cash/events append | `ledger/*`, execution/submit pipelines | Connected through submit/execution | Ledger paths emitted | `REGRESSION_PRESENT` | Level2 | No major static gap |
| Asset / Current Projection | Runtime-owned fills -> Current SoT | `asset/runtime_owned_fill_projection.py` | Connected through execution | Projection status emitted | `REGRESSION_PRESENT` | Level2 | Level3 requires operation evidence |
| Reconcile | Compare pending/ledger/broker/current | `reconcile/*` | Connected in execution; checkpoints elsewhere | Reconcile status emitted | `REGRESSION_PRESENT` | Level1/2 | Not independent CLI job |
| Report | Current/Today/Run/Ledger separation | `report/markdown_writer.py` | Tail stage, no `report` job | Runtime/public report artifacts generated | `REGRESSION_PRESENT` | Level2 | Generated != semantic PASS; partial |
| Notification | Payload/queue/delivery/audit separation | `notification/*` | Tail payload-only; no `notification` job | Payload artifact generated, no send | `REGRESSION_PRESENT` for components | Level1/partial2 | Delivery not connected |
| Audit | Evidence-only, not Submit source | `audit/*`; CLI tail stage label | Tail stage, no `audit` job | Audit artifact path generated by report writer path | `REGRESSION_PRESENT` for components | Level1/partial2 | CLI does not call `run_audit` aggregator directly |

## Contract Gap Matrix

| Contract | Design Status | Implementation Status | CLI Status | Evidence Status | Regression Status | Gap Classification | Severity | Required Action |
|---|---|---|---|---|---|---|---|---|
| Runtime purpose: no hidden conservatism | `DESIGNED` | `PARTIAL` | `PARTIAL` | Hidden 100k/5 evidence present | `REGRESSION_MISSING` | `CONTRACT_MISMATCH` | `BLOCKER` | Remove/replace Runtime defaults with explicit policy contract |
| Submit max order amount | `DESIGNED` hidden cap prohibited | `IMPLEMENTED` as default 100k | `CLI_CONNECTED` through submit | `EVIDENCE_MISSING` for policy source | `REGRESSION_MISSING` for >100k regular CLI | `HIDDEN_POLICY_RISK` | `BLOCKER` | Implement BUY/SELL policy source and active manifest |
| Morning max orders | `DESIGNED` no Runtime fixed count | `IMPLEMENTED` default 5 | `CLI_CONNECTED` | Not emitted as Capital Deployment policy | `REGRESSION_MISSING` | `HIDDEN_POLICY_RISK` | `BLOCKER` | Move to explicit Risk Policy / Capital Deployment Contract |
| Morning per-order 100k cap | `DESIGNED` no fixed order cap | `IMPLEMENTED` hidden min(...,100k) | `CLI_CONNECTED` | Not emitted as policy | `REGRESSION_MISSING` | `CONTRACT_MISMATCH` | `BLOCKER` | Derive from policy inputs and emit source/version |
| Capital Deployment Contract | `DESIGNED` | `PARTIAL` | `PARTIAL` | evaluation_capital/planning_budget emitted, full policy absent | `REGRESSION_MISSING` | `PARTIAL` | `HIGH` | Add policy model/read/manifest/report/audit coverage |
| BUY notional policy | `DESIGNED` | `PARTIAL` | `CLI_CONNECTED` | amount and sizing sample emitted, policy source absent | `PARTIAL` | `EVIDENCE_MISSING` | `HIGH` | Emit policy source, version, derivation inputs |
| SELL liquidation policy | `DESIGNED` | `PARTIAL` | `CLI_CONNECTED` | Current source evidence present, Broker available evidence weak | `PARTIAL` | `EVIDENCE_MISSING` | `HIGH` | Connect Broker available quantity evidence before submit |
| BUY / SELL guard separation | `DESIGNED` | `PARTIAL` | `CLI_CONNECTED` | SELL quantity guard exists; shared max amount remains | `PARTIAL` | `CONTRACT_MISMATCH` | `BLOCKER` | Separate amount policies and tests |
| SELL source Current-only | `DESIGNED` | `IMPLEMENTED` | `CLI_CONNECTED` | Pending excludes broker-only fixture | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | Keep; add regular submit evidence after guard fix |
| Broker-only position exclusion | `DESIGNED` | `IMPLEMENTED` for planning | `CLI_CONNECTED` sell_planning | Evidence in test fixture | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | Extend to submit/execution acceptance evidence |
| Submit Guard active policy manifest | `DESIGNED` | `NOT_IMPLEMENTED` | `NOT_CONNECTED` | Fields absent | `REGRESSION_MISSING` | `EVIDENCE_MISSING` | `HIGH` | Add structured guard policy result to submit stage/report/audit |
| Pending-only Submit source | `DESIGNED` | `IMPLEMENTED` | `CLI_CONNECTED` | source_current_path guard | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | No action now |
| Current fixed path | `DESIGNED` | `IMPLEMENTED` | `PARTIAL` | path_resolver/reader | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | No action now |
| History not Current | `DESIGNED` | `IMPLEMENTED` | `PARTIAL` | current reader ignores history dirs | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | No action now |
| Report is Derived | `DESIGNED` | `IMPLEMENTED` | `PARTIAL` tail stage | report loader reads Current | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | Add standalone report CLI only if required |
| Audit not Submit source | `DESIGNED` | `IMPLEMENTED` as models/checks | `PARTIAL` | aggregator exists, CLI tail label only | `PARTIAL` | `PARTIAL` | `MEDIUM` | Wire audit aggregator or clarify report-writer audit artifact |
| Notification payload | `DESIGNED` | `IMPLEMENTED` | `PARTIAL` tail stage | payload generated, no delivery | `REGRESSION_PRESENT` | `PARTIAL` | `MEDIUM` | Separate payload vs delivery acceptance |
| Notification delivery | `DESIGNED` | `PARTIAL` skeleton | `NOT_CONNECTED` | sender stubs/ledger exist | `PARTIAL` | `NOT_CONNECTED` | `MEDIUM` | Define delivery readiness and real send gate |
| CLI regular path jobs | `DESIGNED` broad flow | `PARTIAL` | Missing `feature_refresh`, `report`, `notification`, `audit` jobs | manifest tail stages only | `PARTIAL` | `NOT_CONNECTED` | `MEDIUM` | Add jobs or update contract to tail-stage model |
| No legacy Runtime path | `DESIGNED` | `IMPLEMENTED` guards/tests | `PARTIAL` | no legacy import tests | `REGRESSION_PRESENT` | `IMPLEMENTED` | `LOW` | Continue regression |
| Report scope separation | `DESIGNED` | `IMPLEMENTED` | `PARTIAL` | Current/Today/Run/Ledger summary | `REGRESSION_PRESENT` | `IMPLEMENTED_WITH_REVIEW_LIMIT` | `MEDIUM` | Semantic review with runtime evidence still needed |
| Current Projection regular CLI path | `DESIGNED` | `IMPLEMENTED` | `CLI_CONNECTED` execution | projection status emitted | `REGRESSION_PRESENT` | `IMPLEMENTED_WITH_REVIEW_LIMIT` | `MEDIUM` | Confirm with operation evidence later |

## Regression Coverage Audit

| Required Regression | Static Finding | Status |
|---|---|---|
| BUY 10万円超 | No regular CLI test proving >100k BUY allowed by explicit policy | `REGRESSION_MISSING` |
| SELL 10万円超 | Existing E32 flow uses small SELL; E51 showed real larger SELL blocked | `REGRESSION_MISSING` |
| Capital Allocation -> Pending -> Submit Guard | Basic flow exists, no full policy alignment test | `PARTIAL` |
| Capital Deployment Contract -> Submit Guard | No active policy model/source/manifest | `REGRESSION_MISSING` |
| max_positions policy manifest | No manifest fields found | `REGRESSION_MISSING` |
| Submit Guard active policy manifest | No fields found | `REGRESSION_MISSING` |
| SELL source Current-only | Covered in sell planning tests | `REGRESSION_PRESENT` |
| Broker-only position exclusion | Covered in sell planning tests | `REGRESSION_PRESENT` |
| Current Projection regular CLI path | Execution pipeline connects projection; tests cover component/flow | `REGRESSION_PRESENT_WITH_REVIEW_LIMIT` |
| Report scope separation | Public report tests cover sections/scope | `REGRESSION_PRESENT` |
| Notification payload / queue / delivery / audit | Component coverage exists, CLI delivery absent | `PARTIAL` |
| CLI regular path | Some jobs covered; requested job set incomplete | `PARTIAL` |
| No hidden policy | Hidden policy currently present | `CONTRACT_MISMATCH` |
| No legacy Runtime path | Import/path isolation tests exist | `REGRESSION_PRESENT` |

## Operator Evidence Needed Later

This Phase15-C did not request Runtime execution. Before any future PASS/FAIL acceptance for Level3, request only small evidence batches, for example:

```text
ls -t .runtime/runtime_state/run_manifest/*/*.json | head -1
```

Then inspect the single latest manifest before asking for the next artifact.

## Prohibited Actions Check

| Action | Performed |
| --- | --- |
| Runtime implementation change | No |
| Submit execution | No |
| Broker Write | No |
| Demo order | No |
| Production order | No |
| Notification real send | No |
| launchd/plist change | No |
| Current direct edit | No |
| Runtime bypass creation | No |
| fake adapter Full Runtime PASS declaration | No |
| Gap fix applied in same phase | No |

## Final Judgment

```text
PHASE15C_RUNTIME_DESIGN_IMPLEMENTATION_GAP_AUDIT_COMPLETE
```
