# Phase15-F AI / Component Interface Blind Spot Audit

## Summary

Phase15-F audits AI / Runtime Component / Broker / Report / Notification boundaries before implementation fixes.

Purpose:

```text
AI・Component間のInput / Output / Consumer連携漏れを洗い出し、
Runtime v2がシステム全体の制御中枢として成立しているか確認する。
```

This is a static, evidence-first audit. It did not perform implementation fixes, gap fixes, Submit execution, Broker Write, Demo order, Production order, Notification real send, launchd/plist changes, or Current direct edits.

Final judgment: **PHASE15F_AI_COMPONENT_INTERFACE_BLIND_SPOT_AUDIT_COMPLETE**

## Evidence Checked

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase15_c_runtime_architecture_design_implementation_gap_audit.md`
- `docs/phase_reports/phase15_d_historical_regression_coverage_audit.md`
- `docs/phase_reports/phase15_e_blocker_fix_and_regression_plan.md`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/report/*`
- `src/ai_fund_lab_v2/runtime_v2/notification/*`
- `src/ai_fund_lab_v2/runtime_v2/audit/*`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/*`
- `src/ai_fund_lab_v2/candidate_ai/*`
- `src/ai_fund_lab_v2/opportunity_ai/*`
- `src/ai_fund_lab_v2/position_management_ai/*`
- `src/ai_fund_lab_v2/capital_allocation_ai/*`
- `src/ai_fund_lab_v2/safety/*`

## Key Blind Spots

1. Runtime v2 does not directly call Candidate AI / Opportunity AI modules in the regular morning path; it reads feature artifacts and constructs `AIPlanningSignal` internally.
2. Position Management AI is not directly connected to SELL Planning; `sell_planning` builds `SellExitDecision` from Current positions in the CLI path.
3. Capital Allocation is represented as `CapitalAllocationSignal`, but the current morning implementation derives it inside Runtime from per-order budget logic rather than reading an explicit Capital Deployment / Capital Allocation contract.
4. Safety is represented as `SafetySignal`, but current BUY/SELL planning uses generated/placeholder allow signals rather than a connected Safety decision source.
5. Submit Guard needs Broker available quantity for SELL, but the regular submit pipeline currently supplies available quantity from Current quantity, not Broker ReadOnly evidence.
6. Report and Notification can only explain policy decisions that are present upstream; active policy source / guard decision is still missing from Submit outputs.
7. Audit component exists, but CLI regular path records an `audit` stage without clearly invoking the Audit Runtime aggregator.
8. Operator Review / Recovery is designed architecturally, but no regular Runtime v2 component was found that applies an operator review decision back into Runtime state.

## Interface Matrix

| Component | Input | Output | Consumer | Current Read | Current Write | Missing Link Risk | Evidence Checked | Gap | Severity |
|---|---|---|---|---|---|---|---|---|---|
| Candidate AI | Market/features/history in `candidate_ai` modules | Candidate feature/candidate artifacts | Runtime Morning via feature artifacts, not direct AI call | No Runtime Current read in AI module evidence | None in Runtime v2 | Runtime may treat feature rows as AI output without proving Candidate AI inference contract | `candidate_ai/*`, `morning_pipeline.py` | AI output to Runtime is indirect / artifact-based; source_ai provenance is generated in Runtime | `HIGH` |
| Opportunity AI | Candidate Top50 / opportunity dataset/model artifacts | Ranking / opportunity inference reports | Runtime Morning via candidate rows, not direct Opportunity AI output | No Runtime Current read in AI module evidence | None in Runtime v2 | Opportunity score/ranking may not be the actual source of selected Runtime candidates | `opportunity_ai/*`, `morning_pipeline.py` | Regular Runtime path does not call Opportunity AI; consumer contract is weak | `HIGH` |
| Position Management AI | Holdings, opportunity, features | Exit / hold decisions | Intended SELL Planning | Current-like holdings in AI reports, not Runtime SoT | None in Runtime v2 | SELL decisions can be cleanup-style Current liquidation, not AI exit decision | `position_management_ai/*`, `sell_pipeline.py`, `run_daily_operation.py` | Position Management AI -> `SellExitDecision` -> SELL Planning not connected | `HIGH` |
| Capital Allocation | AI signal, capital policy, risk constraints | Allocation amount / max amount / cash required | Planning, Pending, Submit Guard | Current asset state needed | No Current write | Runtime-generated allocation can replace actual Capital Allocation contract | `planning/models.py`, `morning_pipeline.py`, `planner.py`, Phase15-E | Explicit Capital Deployment / Capital Allocation input missing | `BLOCKER` |
| Safety | Current, policy, broker/risk state, emergency locks | allow / block / review decision | Planning, Approval, Submit, Report, Notification | Should read Current / Safety state | May write events/locks outside Runtime v2 | Placeholder allow can make Planning/Submit look safe without Safety evidence | `planner.py`, `sell_pipeline.py`, `morning_pipeline.py`, `safety/*` | Safety result not consistently connected to regular Runtime path | `HIGH` |
| Market Refresh | business date, operations root, optional API fetch | Feature artifacts, feature date contract | Morning Planning | No Current read | Feature artifacts / contract | `market_refresh` exists, but `feature_refresh` is folded and API/network evidence can be overread | `market_refresh/pipeline.py`, CLI | Separate Feature Refresh job absent; feature freshness contract is consumer-facing but indirect | `MEDIUM` |
| Feature Refresh | Market refresh outputs / operation artifacts | candidate/opportunity/position/capital feature artifacts | Morning Planning | No Current read | Feature artifact directory | Feature files may exist but lack AI-specific consumer proof | `market_refresh/pipeline.py`, `feature_date_contract.py`, `morning_pipeline.py` | Folded into Market Refresh; no standalone Runtime job | `MEDIUM` |
| Morning Planning | Feature artifacts, Current asset state, broker capability, generated AI/Allocation/Safety signals | OrderPlan, Approval, Pending | Submit, Report, Notification, Next Runtime | Reads `persistent_ledger/state.json` | Writes `pending_order_plan/pending_order_plan.json`; artifacts | AI/Capital/Safety semantics can be collapsed into Runtime-generated placeholders | `morning_pipeline.py`, `planner.py` | Hidden caps plus indirect AI/Allocation/Safety links | `BLOCKER` |
| SELL Planning | Current positions, CLI-built `SellExitDecision` | SELL OrderPlan, Approval, Pending | Submit, Report, Notification | Reads `persistent_ledger/state.json` | Writes `pending_order_plan/pending_order_plan.json`; artifacts | Position Management AI not the source; SELL may be cleanup liquidation only | `sell_pipeline.py`, `run_daily_operation.py` | PM AI connection missing; safety placeholder allow | `HIGH` |
| Pending | OrderPlan items and approval linkage | Current pending plan | Submit, Report, Notification | Reads/writes pending Current | Writes pending Current | Pending can preserve amount/price/source, but not Capital policy source | `pending/models.py`, `pending/promotion.py`, `pending/reader.py` | Policy source fields absent | `HIGH` |
| Approval | Pending plan, approval decision | Approval artifact and pending approval linkage | Submit | Reads pending | Writes approval linkage into pending | Auto-approval can be mistaken for operator or policy approval | `approval/policy.py`, `approval/linkage.py`, `morning_pipeline.py`, `sell_pipeline.py` | Human / policy approval boundary weak for operational acceptance | `MEDIUM` |
| Submit Guard | Pending, approval, dedup, environment, broker capability, current-derived SELL quantity | Submit command or block reason | Broker Adapter, Ledger, Report/Audit via manifest | Reads pending and Current positions in pipeline | Writes orders ledger after submit | Side-neutral amount guard; SELL broker available not true Broker ReadOnly; active policy absent | `submit/guards.py`, `submit/pipeline.py` | Known BLOCKER and interface blind spot | `BLOCKER` |
| Broker Adapter | Submit command | Broker result / preflight diagnostics | Submit pipeline / Ledger | No Current read | External broker write only when submit enabled | Fake/demo adapter can pass while real broker schema/availability differs | `broker_adapter/*`, `submit/pipeline.py` | Broker boundary evidence not enough for Full Runtime PASS | `HIGH` |
| Execution / Fill | Broker ReadOnly snapshot | Normalized orders/executions/positions/cash, acceptance | Ledger, Reconcile, Current Projection | Reads pending and Current asset state | Appends ledger; calls Current projection on PASS | Optional detail and execution-equivalent policy can be overclassified | `execution/readonly_pipeline.py`, `execution/fill_classifier.py` | Fill evidence semantics require Level3 proof | `HIGH` |
| Ledger | Submit records, broker readonly records, execution equivalent, events | `persistent_ledger/*.jsonl` | Current Projection, Reconcile, Report, Audit | Reads existing ledger for dedup | Writes orders/executions/positions/cash/events | Ledger rows can exist without Current update if projection fails | `ledger/*`, `execution/readonly_pipeline.py` | Ledger PASS is not Current PASS | `MEDIUM` |
| Current Projection | Accepted Runtime submit orders, execution/position ledger, previous Current | Updated `persistent_ledger/state.json` | Report, Notification, Next Planning, Reconcile | Reads ledger and Current | Writes `persistent_ledger/state.json` | Ownership depends on submit records; broken Submit evidence corrupts Current scope | `asset/runtime_owned_fill_projection.py` | Strong dependency on Submit source quality; SELL full path not proven | `HIGH` |
| Reconcile | Pending, ledger, broker readonly, asset state | Findings / review_required | Execution pipeline, Report, Audit, Operator Review | Reads asset state | No Current write | Reconcile finds gaps but does not itself repair or feed operator action path | `reconcile/reconciler.py`, `reconcile/checks.py` | Review Required consumer path incomplete | `MEDIUM` |
| Report | Fixed Current paths, ledger, pending, events, runtime state | Runtime/public Markdown, summary | Operator, Notification | Reads fixed Current paths | Writes report artifacts only | Report can explain only data present upstream; policy/guard reasons absent | `report/markdown_writer.py`, `report/public_report_writer.py` | "Why buy/sell/stop" incomplete until policy evidence exists | `HIGH` |
| Notification | Report summary or Report artifact | Payload, queue/delivery components | Operator / delivery ledger | No direct Current read; via Report | Payload/queue/delivery artifacts | Payload-only can be mistaken for delivered notification; urgency depends on Report scope | `notification/payload.py`, `notification/*`, CLI | Delivery not connected in regular CLI; send status fixed false | `MEDIUM` |
| Audit | Report, notification payload/delivery, reconciliation, asset state | AuditResult / findings | Operator Review, Report, Runtime acceptance | Reads supplied objects only | No Current write | CLI records audit stage but may not run `run_audit`; audit cannot stop Submit if not connected | `audit/auditor.py`, `audit/checks.py`, CLI | Audit Runtime aggregator not regular CLI-connected | `MEDIUM` |
| Operator Review | Review events, reconciliation, manual decisions | Review decision / recovery action | Recovery / Runtime state / migration | Should read review queue/events | Apply path may write migration/safety state | No clear Runtime v2 regular path to apply Operator decision back to pending/state | architecture, `safety/manual_unlock*`, runtime_v2 search | Designed but not implemented as Runtime v2 regular component | `HIGH` |

## Cross-Component Blind Spot Findings

### 1. AI output is not yet a Runtime-verified AI execution contract

Morning Planning creates `AIPlanningSignal` from selected feature rows. This is useful as a Runtime planning adapter, but it does not prove that Candidate AI / Opportunity AI inference outputs were produced and consumed as designed.

Required follow-up:

- Define the Runtime AI Execution Contract.
- Emit AI source artifact refs, model/version, score/rank source, feature date, and confidence.
- Add regression proving AI output -> Planning -> Pending consumer continuity.

### 2. Position Management AI is not connected to SELL Planning

SELL Planning receives `SellExitDecision`, but the CLI builds it from Current positions rather than from Position Management AI inference output.

Required follow-up:

- Define Position Management AI output schema for SELL.
- Connect PM AI output to `SellExitDecision`.
- Mark cleanup liquidation separately from normal AI-driven SELL.

### 3. Capital Allocation semantics are weakened before Submit

`CapitalAllocationSignal` exists, and Pending carries amount/quantity/price_source. However, the current implementation derives allocation from Runtime budget logic and lacks an explicit Capital Deployment Policy source.

Required follow-up:

- Introduce explicit Capital Deployment / Capital Allocation input.
- Preserve `capital_allocation_amount` and policy source through Pending and Submit Guard.
- Emit this in manifest/report/audit.

### 4. Safety is represented but not connected as an authoritative input

Planning receives `SafetySignal`, but BUY/SELL pipelines generate local allow decisions. SELL specifically uses a placeholder allow reason.

Required follow-up:

- Connect Safety / Operation Guard output before Planning and Submit.
- Preserve safety decision IDs through OrderPlan, Pending, Submit, Report, and Notification.
- Regression: Safety block/review prevents Pending or Submit and appears in report/notification.

### 5. Broker available quantity is not truly Broker evidence in Submit

Submit Guard requires SELL available quantity, but the regular submit pipeline passes Current quantity as both broker position and broker available quantity.

Required follow-up:

- Connect Broker ReadOnly available quantity or explicitly require review if not available.
- Regression: Current quantity > Broker available quantity must block/review.

### 6. Report / Notification cannot yet explain policy decisions

Report reads fixed Current and ledger paths, and Notification reads Report summary. This is correct for Current discipline. But policy source, guard decision, and violated policy fields are missing upstream, so Report/Notification cannot explain why a BUY/SELL was allowed or stopped.

Required follow-up:

- Add Submit Guard Active Policy Manifest first.
- Thread policy evidence to Report and Notification.
- Add semantic tests for "why buy/sell/stop" visibility.

### 7. Audit and Operator Review are not closed-loop Runtime controls

Audit component exists, and architecture defines Recovery / Review Runtime, but the regular CLI path only records an audit stage. A clear operator decision -> Runtime state transition path was not found in Runtime v2.

Required follow-up:

- Define Review Required queue/state.
- Define operator decision artifact and allowed transitions.
- Ensure Audit result is never Submit source, only control/evidence.

## Required Follow-up Matrix

| Follow-up | Reason | Severity |
|---|---|---|
| AI Execution Contract for Candidate/Opportunity -> Morning Planning | Avoid treating feature rows as proven AI output | `HIGH` |
| Position Management AI -> SELL Planning contract | Normal SELL must not be confused with cleanup liquidation | `HIGH` |
| Capital Deployment / Capital Allocation source preservation | Prevent Runtime-generated allocation from replacing policy | `BLOCKER` |
| Safety / Operation Guard regular-path connection | Prevent placeholder allow from reaching Submit | `HIGH` |
| Broker available quantity evidence for SELL Submit | Prevent Current quantity from masquerading as Broker availability | `HIGH` |
| Submit Guard Active Policy Manifest | Required for Report/Notification/Audit explanation | `HIGH` |
| Report/Notification semantic reason propagation | Operator must see why buy/sell/stop happened | `MEDIUM` |
| Audit Runtime regular CLI connection | Avoid audit-stage-only acceptance | `MEDIUM` |
| Operator Review apply path | Review Required must have controlled return path | `HIGH` |

## Final Judgment

```text
PHASE15F_AI_COMPONENT_INTERFACE_BLIND_SPOT_AUDIT_COMPLETE
```
