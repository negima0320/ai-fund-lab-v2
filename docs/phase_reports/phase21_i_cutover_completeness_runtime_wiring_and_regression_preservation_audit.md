# Phase21-I Cutover Completeness, Runtime Wiring & Regression Preservation Audit

## 1. Primary Judgment

```text
PHASE21_I_CUTOVER_AND_REGRESSION_AUDIT_PASS_WITH_STEP_GATES
```

Phase22開始前に必要な実コード上の主要Cutover Surface、Runtime Wiring、Legacy Path、Regression Contract、State Transition、Rollback条件は棚卸しできた。

Blocking Gapは確認されなかった。ただし、新Strategy Artifactは現行実装では未実装または旧Artifact経路に吸収されているため、Phase22の各StepでConsumer有効化、Runtime switch、Report/Status/Summarize更新、State cutoverを個別Gateとして止める必要がある。

## 2. Review Position

本監査は、Independent Cutover and Regression Auditorとして実施した。

目的は新Architecture提案ではなく、次を確認することだった。

```text
現行実装のどこが新設計の移行対象か
移行計画に含まれていない実コード経路がないか
既存Contractを何によって保存するか
切替・Rollback時にStateが破壊されないか
```

Productionコード、Runtimeコード、Strategyコード、Config、Schema、Artifact Registry、Accepted Generation、Threshold、Position Sizing式は変更していない。Historical Run、Backtest、Training、Calibration、Phase22実装開始も行っていない。

## 3. Reviewed Sources

Design / Migration / Governance:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/01_requirements/strategy_performance_acceptance_contract.md`
- `docs/01_requirements/strategy_experiment_contract.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase21_f_strategy_responsibility_and_authority_boundary_review.md`
- `docs/phase_reports/phase21_fa_corporate_event_authority_design.md`
- `docs/phase_reports/phase21_gb_strategy_migration_architecture_design.md`
- `docs/phase_reports/phase21_gc_implementation_governance_and_phase22_entry_gate.md`
- `docs/phase_reports/phase21_h_phase22_implementation_readiness_independent_review.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`

Primary code areas:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/*`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/current_state/*`
- `src/ai_fund_lab_v2/runtime_v2/asset/*`
- `src/ai_fund_lab_v2/runtime_v2/ledger/*`
- `src/ai_fund_lab_v2/runtime_v2/system_status.py`
- `src/ai_fund_lab_v2/runtime_v2/ai_status.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/*`
- `tools/launchd/com.aifundlab.runtime_v2.*.plist`
- `tests/runtime_v2/*`

## 4. Audit Summary

| Item | Result |
|---|---|
| Phase22開始可能か | YES、Phase21-G Entry Gate後、Step Gate付き |
| Blocking Gap数 | 0 |
| Pre-Phase22 Required Fix数 | 0 |
| Step Gate Required数 | 6 |
| Non-blocking Gap数 | 3 |
| 実コード上のCutover Surface数 | 17 |
| Runtime Wiring Edge数 | 18 |
| MISSING_EDGE数 | 0 |
| Legacy Path数 | 13 |
| Regression Contract数 | 26 |
| Regression未Coverage数 | 6 |
| State Object数 | 16 |
| Rollback Unsafe Step数 | 0 |
| Production / Demo / Historical Parity判定 | PASS_WITH_ADAPTER_DIFFERENCES |
| Pending / Approval / Current / Ledger移行安全性 | PASS_WITH_CUTOVER_CONDITIONS |
| Old Path Removal安全性 | PASS_WITH_POST_SWITCH_ACCEPTANCE |
| Design Freeze維持可否 | YES |
| Phase21-Gへ進めるか | YES |

## 5. I-1 Cutover Surface Inventory

機械可読棚卸し:

```text
reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/cutover_surface_inventory.json
```

High-risk surfaces:

| Surface | Current File / Module | New Architecture Target | Migration Step | Risk |
|---|---|---|---|---|
| Market Context | `runtime_v2/market_refresh/*`, `data_readiness.py` | `strategy_market_context.v1` | Phase22-A | produced-but-not-consumed detection absent until new producer gate |
| Corporate Event | `market_status/buy_eligibility.py`, historical listed issue snapshots | `corporate_event_authority.v1` | Phase22-AA | source authority / coverage open decisions |
| Candidate / Opportunity | `runtime_v2/buy_ai/producer.py` | Candidate / Opportunity artifacts with Market/Corporate refs | Phase22-B | ranking drift if refs alter scoring |
| Portfolio Policy | `runtime_v2/policy/capital_deployment.py` | Portfolio Policy Artifact | Phase22-C | current capital policy mixes target and hard limit |
| Position Management | `runtime_v2/position_management/producer.py` | PM Artifact with refs | Phase22-D / K | PM reason refs must not add new actions |
| Portfolio Construction | action-based planning in `morning_pipeline.py` / `sell_pipeline.py` | Target Portfolio / Strategy Intent | Phase22-E | no current code artifact yet |
| Capital Deployment | `planning` + `policy/capital_deployment.py` + `add_consumer.py` | Allocation Artifact | Phase22-F / J | target rewrite vs feasibility separation |
| Runtime Planning | `planning/planner.py`, Pending builder | Execution Intent Artifact / Pending Candidate | Phase22-G | canonical Pending compatibility required |
| Submit / Execution | `submit/pipeline.py`, `execution/readonly_pipeline.py` | consume canonical Pending only | Phase22-G switch gate | old/new Pending mismatch would block |
| Status / Summarize / Reports | `system_status.py`, `ai_status.py`, `scripts/runtime_test.py`, `report/*` | observe new artifacts and old path use | Phase22-M / N | reporting-only consumers can stay on old schema unnoticed |

## 6. I-2 Direct / Indirect Consumer Discovery

Consumer discovery used file inventory, targeted `rg`, import tracing, runtime CLI dispatch review, artifact read/write path review, and test mapping.

Summary:

| Artifact | Current Consumer Classification |
|---|---|
| Market Context Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED`; current indirect consumers read market refresh / data readiness evidence |
| Corporate Event Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED`; current partial equivalent is listed issues / market status eligibility |
| Candidate Artifact | Direct: Opportunity producer and status/report readers |
| Opportunity Artifact | Direct: Morning Planning signal loader, PM adapter reference, status/report readers |
| Portfolio Policy Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED`; current equivalent is capital deployment policy config/registry |
| PM Artifact | Direct: Sell Planning; Derived: summarize/performance observability |
| Target Portfolio Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED` |
| Strategy Intent Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED` |
| Allocation Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED`; current equivalent is `CapitalAllocationSignal` passed into planner |
| Execution Intent Artifact | `DESIGN_ONLY_NOT_IMPLEMENTED`; current equivalent is canonical Pending Order Plan |
| Pending Candidate | Compatibility/Review: promotion/apply candidate modules |
| Safety Decision | Direct: planning, pending apply, submit, data readiness, runtime state |
| Current | Direct: PM producer, planning, submit guard, execution projection, reports, summarize |
| Ledger | Direct: submit, execution, performance, summarize, current projection |
| Broker Snapshot | Direct: execution, broker readonly refresh, pending apply review |

## 7. I-3 Runtime Wiring Proof

機械可読Edge:

```text
reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/runtime_wiring_edges.json
```

Current Runtime E2E:

```text
market_refresh
-> data_readiness
-> buy_ai producer
-> morning planning
-> order plan
-> approval
-> pending current
-> submit guard
-> broker adapter
-> ledger orders
-> execution readonly
-> ledger executions/positions/cash
-> runtime-owned current projection
-> runtime state
-> report/status/summarize
```

New Strategy E2E:

```text
Market Context
Corporate Event
Target Portfolio
Allocation
Execution Intent
```

は現時点では `DESIGN_ONLY_NOT_IMPLEMENTED` であり、Phase22予定として許容される。現行Runtimeの重要Edgeに `MISSING_EDGE` は確認されなかった。

## 8. I-4 Legacy Path Inventory

機械可読棚卸し:

```text
reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/legacy_path_inventory.json
```

主要Legacy Path:

- 旧action-based BUY planning
- 旧SELL Planning direct PM-to-Pending path
- 旧Capital Deployment policy-as-target path
- 旧ADD Consumer composition
- canonical Pending direct Submit path
- report/status/summarize old artifact readers
- Historical adapter / as-of view support path
- runtime_test runner run/resume/reset/rollback/summarize path
- LaunchAgent job wrappers

削除予定だが呼び出し元不明のPathは確認されなかった。ただしOld Path RemovalはPhase21-GCどおり、Runtime Switch、Regression PASS、User Acceptance PASS、Rollback不要確認後のみ許可する。

## 9. I-5 Regression Preservation Matrix

機械可読Matrix:

```text
reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/regression_preservation_matrix.json
```

Existing Contractは26件を列挙した。これは`regression_preservation_matrix.json`の実row数であり、Audit Summary / Final Reportの`Regression Contract数 = 26`と一致する。Phase21-Jでは、`regression_contract_groups = 26`、`regression_contract_rows = 26`として扱う。

`NO_CURRENT_REGRESSION_COVERAGE` は6件:

- Market Context Artifact producer / consumer detection
- Corporate Event Artifact producer / consumer detection
- Target Portfolio Artifact schema / consumer
- Strategy Intent Artifact schema / consumer
- Allocation Artifact schema / consumer
- Execution Intent Artifact schema / Pending compatibility

これらはPhase22新規導入対象であり、Phase22開始前のBlockingではない。ただし該当StepのAcceptance Gateでは必須テストを追加する。

## 10. I-6 State Transition Audit

機械可読Matrix:

```text
reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit/state_transition_matrix.json
```

Cutover state rules:

| Condition | Rule |
|---|---|
| Pendingがある場合 | Runtime switch禁止。Pending lifecycleまたはSubmit/Cancel/Expireでterminal化してから切替 |
| Approval待ちがある場合 | Pending/Approval pairを維持。新Execution Intentへ暗黙移行しない |
| Partial Fillがある場合 | Broker-side irreversibilityとしてManual Review。Code rollbackだけで完了扱いしない |
| Runtime途中 | 切替禁止。Last Successful Stepとrun manifestを確認し、日次境界で切替 |
| 営業日途中 | 原則切替禁止。Read-only producerのみ可 |
| 旧Artifactと新Artifactが同business_dateに存在 | Accepted authorityとruntime_consumer_eligibilityで一意化。latest fallback禁止 |

Pending / Approval / Current / Ledgerは `PRESERVE_AS_IS` が基本であり、Strategy rollbackで直接編集しない。

## 11. I-7 Rollback Completeness Audit

Rollback result:

```text
ROLLBACK_SAFE_WITH_CONDITIONS
```

各Phase22 StepはCode rollback、Artifact authority rollback、Consumer rollback、Runtime path rollbackのいずれかで戻せる。ただしSubmit後、Broker accepted order、Fill、Ledger append、Current projectionはBroker-side / Runtime state reconciliationが必要であり、単純なCode rollback対象ではない。

Rollback unsafe step:

```text
なし
```

Broker-side irreversible condition:

```text
送信済み注文
約定
Partial Fill
外部Broker state変化
```

## 12. I-8 Entry Point and Environment Parity Audit

Entry Point summary:

| Entry Point | Runtime Pipeline | Divergence |
|---|---|---|
| Production | `run_daily_operation.py --mode production` guarded; submit prohibited unless accepted | Strategy path common, external write guarded |
| Demo | `run_daily_operation.py --mode demo` | common Runtime with demo broker adapter |
| Historical | `scripts/runtime_test.py` -> `run_daily_operation.py --mode historical` | common Runtime core with historical adapter/as-of source |
| CLI manual run | `python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation` | common Runtime |
| Scheduler / LaunchAgent | `tools/launchd/com.aifundlab.runtime_v2.*.plist` | starts same CLI |
| Resume / Retry / Recovery | `scripts/runtime_test.py resume/reset/rollback/abandon` | historical test lifecycle only |
| Status / report-only | `runtime_test.py status/system-status/ai-status/summarize` | read-only consumers |

Production / Demo / HistoricalのStrategy判断経路分岐は確認されなかった。差分はAdapter、source、execution mode、external write policyに限定されている。

## 13. I-9 Schema and Serialization Compatibility Audit

Risk summary:

| Risk | Current Status | Required Gate |
|---|---|---|
| Optional field追加 | current dataclass readers tolerate many optional Pending fields, but new artifacts need fixture | Step Gate |
| Required field追加 | canonical Pending reader is strict | Runtime switch gate |
| Enum追加 | PendingPlanState / ApprovalStatus branches can block unknowns | Schema test |
| Status名変更 | CLI/Report/Summarize rely on status names | Report compatibility test |
| Hash対象変更 | Accepted Artifact / Pending source hash can invalidate existing evidence | Artifact refresh gate |
| Artifact version mismatch | Candidate/Opportunity loader blocks mismatched schema | Schema/compatibility test |

JSON serialization contract is guarded by `JsonSerializationContractError` in Runtime CLI. New artifacts must be included in the same serialization failure path before Runtime authority switch.

## 14. I-10 Observability and Failure Detection Audit

Detection exists for current Runtime:

- pending missing / invalid / empty
- policy missing / hash mismatch
- safety missing / stale / blocked
- feature date mismatch
- accepted generation unresolved
- schema mismatch for Candidate / Opportunity
- historical source hash mismatch
- runtime root mode-rooted path
- submit guard and pending dedup
- status / ai-status / system-status / summarize read-only views

Detection gaps requiring Step Gates:

| Failure | Gap |
|---|---|
| new artifact produced but never consumed | no current detector until Phase22-A/AA/M |
| old path used after switch | no current detector until switch manifest records active path |
| compatibility path active unexpectedly | needs explicit compatibility_active field in Phase22 evidence |
| new path bypassed | needs Runtime manifest field after switch |
| Market/Corporate artifact stale | new artifact-specific freshness status required |

## 15. I-11 Test Coverage Mapping

Existing coverage is broad for Runtime v2 current path:

- Candidate / Opportunity runtime connection
- PM runtime connection
- Pending models / reader / writer / lifecycle / no fallback
- Planning to Pending integration
- ADD consumer and Pending Composition
- Submit guard BUY / SELL
- Historical submit and fill model
- Current / Ledger / Fill projection
- System-status / ai-status / summarize
- LaunchAgent CLI startup
- Safety producer/evaluation

New tests required by Phase22:

- Market Context schema/hash/PIT/consumer detection
- Corporate Event schema/hash/PIT/coverage/failure
- Portfolio Policy artifact consumer compatibility
- Target Portfolio no-op and duplicate prevention
- Allocation artifact infeasible item evidence
- Execution Intent to canonical Pending parity
- Report/status/summarize new artifact visibility
- Old path usage detection after switch

## 16. Findings

### BLOCKING_GAP

```text
なし
```

### PRE_PHASE22_REQUIRED_FIX

```text
なし
```

### STEP_GATE_REQUIRED

| ID | Finding | Gate |
|---|---|---|
| I-SG-01 | Market Context / Corporate Event produced-but-not-consumed detection is not current code | Phase22-A / AA acceptance |
| I-SG-02 | Corporate Event source authority open decisions must close before active consumer use | Phase22-AA consumer gate |
| I-SG-03 | Target Portfolio / Strategy Intent / Allocation / Execution Intent are design-only artifacts | Phase22-E/F/G schema and fixture gates |
| I-SG-04 | Status / AI Status / System Status / Summarize currently read old artifacts | Phase22-M/N report compatibility gate |
| I-SG-05 | Runtime switch must be blocked when active Pending / Approval / open order / partial fill exists | Runtime switch gate |
| I-SG-06 | Execution Intent must prove canonical Pending parity before Submit consumes it | Phase22-G switch gate |

### NON_BLOCKING_GAP

| ID | Finding | Handling |
|---|---|---|
| I-NBG-01 | Phase22 plan Task Breakdown physical order can be misread | Use dependency graph order |
| I-NBG-02 | Legacy capital allocation AI package exists outside current Runtime v2 path | Keep as legacy/non-runtime unless explicitly migrated |
| I-NBG-03 | Older Phase9/operations LaunchAgents remain in tools | Confirm disabled/non-authoritative before production scheduling |

### RECOMMENDATION

| ID | Recommendation |
|---|---|
| I-R01 | Phase22 first implementation ticket should import this Cutover Surface Inventory as required evidence |
| I-R02 | Add a Runtime manifest field for `strategy_authority_path_active` during switch |
| I-R03 | Add report-only detector for `new_artifact_produced_but_not_consumed` before old path removal |

### ALREADY_COVERED

- Common Runtime CLI entrypoint
- mode-rooted runtime root rejection
- Historical adapter isolation
- canonical Pending reader/writer
- Pending empty no-action contract
- Submit guard
- policy hash consistency
- Safety block/review propagation
- Ledger append and Current projection separation
- runtime_test run-scoped evidence and summarize authority

### FALSE_ALARM

- New Corporate Event plus old PM is not a cycle
- Historical mode is not a separate Strategy implementation
- Empty Pending is not fail-open when classified by the canonical contract
- Code rollback and Broker state rollback are intentionally separate concepts

## 17. Final Report Requirements

| Required Item | Result |
|---|---|
| Phase22開始可能か | YES、Step Gate付き |
| Blocking Gap数 | 0 |
| Pre-Phase22 Required Fix数 | 0 |
| Step Gate Required数 | 6 |
| Non-blocking Gap数 | 3 |
| 実コード上のCutover Surface数 | 17 |
| Runtime Wiring Edge数 | 18 |
| MISSING_EDGE数 | 0 |
| Legacy Path数 | 13 |
| Regression Contract数 | 26 |
| Regression未Coverage数 | 6 |
| State Object数 | 16 |
| Rollback Unsafe Step数 | 0 |
| Production / Demo / Historical Parity判定 | PASS_WITH_ADAPTER_DIFFERENCES |
| Pending / Approval / Current / Ledger移行安全性 | PASS_WITH_CUTOVER_CONDITIONS |
| Old Path Removal安全性 | PASS_WITH_POST_SWITCH_ACCEPTANCE |
| Design Freeze維持可否 | YES |
| Phase21-Gへ進めるか | YES |

## 18. Prohibited Operations Confirmation

| Operation | Status |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| Schema Changed | NO |
| Artifact Registry Changed | NO |
| Accepted Generation Changed | NO |
| Historical Run Executed | NO |
| Backtest Executed | NO |
| Training Executed | NO |
| Calibration Executed | NO |
| Phase22 Implementation Started | NO |
