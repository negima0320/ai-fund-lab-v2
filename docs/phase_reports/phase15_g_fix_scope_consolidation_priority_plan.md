# Phase15-G Fix Scope Consolidation / Priority Plan

## Summary

Phase15-G consolidates Phase15-C / D / E / F findings and redefines the Phase15 fix scope, priorities, implementation order, regression order, and acceptance gates.

Purpose:

```text
既知BLOCKERと、Phase15-Fで追加発見されたAI / Component境界漏れを統合し、
Phase15の修正スコープを確定すること
```

This phase is planning-only. It did not perform Runtime implementation changes, gap fixes, Submit execution, Broker Write, Demo order, Production order, Notification real send, launchd/plist changes, Current direct edits, Runtime bypass creation, or fake-adapter Full Runtime PASS declaration.

Final judgment: **PHASE15G_FIX_SCOPE_CONSOLIDATION_PRIORITY_PLAN_COMPLETE**

## Reference Evidence

- `docs/phase_reports/phase15_a_purpose_goal_definition.md`
- `docs/phase_reports/phase15_b_runtime_architecture_v2_purpose_based_design_review.md`
- `docs/phase_reports/phase15_c_runtime_architecture_design_implementation_gap_audit.md`
- `docs/phase_reports/phase15_d_historical_regression_coverage_audit.md`
- `docs/phase_reports/phase15_e_blocker_fix_and_regression_plan.md`
- `docs/phase_reports/phase15_f_ai_component_interface_blind_spot_audit.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## Scope Classification

### A. Must Fix in Phase15

These are required before Phase15 can claim Runtime trust or Demo Operation readiness.

| Item | Reason |
|---|---|
| Capital Deployment Policy / policy source implementation | Runtime cannot remove hidden defaults safely unless the explicit policy source exists. |
| Submit hidden `max_order_amount=100000` removal | Direct hidden policy that breaks BUY sizing and SELL liquidation. |
| Morning hidden `max_orders=5` removal or explicit policy conversion | Runtime must not silently decide order/position count. |
| Morning hidden per-order `100000` cap removal | Runtime must not throttle Capital Allocation with fixture-like cap. |
| BUY / SELL Guard separation | BUY is risk intake; SELL is risk reduction. One notional guard is not acceptable. |
| Submit Guard Active Policy Manifest | Report / Notification / Audit cannot explain decisions without this. |
| SELL Broker available quantity evidence | SELL Submit Acceptance cannot be trusted if Broker availability is actually Current quantity. |
| Capital Allocation source preservation through Pending / Submit | Capital Allocation meaning must survive Planning -> Pending -> Submit Guard. |
| Safety / Operation Guard regular-path connection or explicit REVIEW_REQUIRED behavior | "安心・安全" cannot be claimed if Safety is placeholder allow. |
| Report / Notification policy reason propagation | Operator must see why BUY/SELL/stop happened. |
| Regression suite expansion for hidden policy, BUY/SELL, CLI, manifest, Safety, and SELL evidence | Without regressions, Phase14 failures can recur. |
| Demo Operation rehearsal after blocker fixes | Demo Operation is evidence, but only after blocker fixes and regressions are in place. |

### B. Design in Phase15, Implementation May Follow Later

These cannot be ignored, but they do not all need full implementation before the first Phase15 Runtime trust gate if their limitation is explicitly labeled and isolated.

| Item | Phase15 Treatment |
|---|---|
| Candidate / Opportunity AI direct execution contract | Define Runtime AI Execution Contract and evidence fields; full direct AI invocation may follow later if feature artifact contract is explicit. |
| Position Management AI -> SELL Planning formal connection | Define schema and normal SELL-vs-cleanup distinction; full strategy SELL connection may follow after SELL liquidation safety is fixed. |
| Operator Review / Recovery apply path | Define review queue, decision artifact, and allowed transitions; full apply automation may follow later. |
| Audit aggregator full regular CLI connection | Define whether audit tail artifact is sufficient or standalone `audit` job is required; full connection may follow if Phase15 acceptance clearly labels current level. |
| Feature Refresh standalone job | Clarify folded `market_refresh` contract or design a separate job; not necessarily required if manifest proves feature refresh coverage. |

### C. Production-Before Required, Not Phase15 Implementation

These are mandatory before production but outside Phase15 Demo Runtime trust scope.

| Item | Reason |
|---|---|
| Production Broker Write / Production order | Phase15 is Demo Runtime trust, not production unlock. |
| Production broker capability diff | Needs separate production broker contract. |
| Account mapping / NISA / account type | Production-specific correctness and compliance concern. |
| Fees / taxes / buying-power holds | Required before production sizing acceptance. |
| Production unlock gate | Must remain separate from Demo acceptance. |
| Real notification send | Payload/delivery contract can be tested; real send is a separate operational gate. |
| launchd automatic operation | Scheduler readiness must follow Runtime Level3 evidence. |

### D. Future Enhancement

These are valuable but not required for Phase15 trust re-establishment.

| Item | Reason |
|---|---|
| Advanced replacement AI | Strategy enhancement, not Runtime control trust prerequisite. |
| Sector exposure optimization | Portfolio enhancement after explicit policy foundation. |
| Tax-aware optimization | Production/portfolio sophistication after core Runtime trust. |
| Multi-account support | Future broker/account expansion. |
| Advanced split-order execution | Optional unless explicit broker or SELL liquidation policy requires it. |

## Priority Matrix

| Item | Source Phase | Issue Type | Must Fix in Phase15? | Why | Depends On | Recommended Subphase | Severity |
|---|---|---|---|---|---|---|---|
| Capital Deployment Policy / Policy Source | C / D / E / F | Hidden policy / interface contract | Yes | Submit and Planning cannot remove hidden defaults without an explicit policy source | Architecture contract | Phase15-H | `BLOCKER` |
| Capital Allocation source preservation | E / F | AI-Capital-Runtime boundary | Yes | Runtime-generated allocation cannot replace Capital Allocation intent | Capital Deployment Policy | Phase15-H | `BLOCKER` |
| Submit hidden `max_order_amount=100000` removal | C / D / E | Hidden policy | Yes | Blocks valid BUY and SELL liquidation | Capital Deployment Policy | Phase15-I | `BLOCKER` |
| BUY / SELL Guard separation | B / C / D / E | Guard contract | Yes | BUY risk intake and SELL risk reduction need different controls | Capital Deployment Policy, Submit policy model | Phase15-I | `BLOCKER` |
| Submit Guard Active Policy Manifest | C / D / E / F | Evidence / explainability | Yes | Operator, Report, Notification, Audit need decision source | Submit policy model | Phase15-I | `HIGH` |
| Morning hidden `max_orders=5` removal | C / D / E | Hidden policy | Yes | Runtime cannot silently cap positions/orders | Capital Deployment Policy | Phase15-J | `BLOCKER` |
| Morning hidden per-order `100000` cap removal | C / D / E | Hidden policy | Yes | Blocks designed capital deployment | Capital Deployment Policy | Phase15-J | `BLOCKER` |
| SELL Broker available quantity evidence | C / D / E / F | Broker boundary / SELL contract | Yes | SELL acceptance needs true Broker availability, not Current proxy | BUY/SELL guard separation | Phase15-K | `HIGH` |
| Safety / Operation Guard Runtime connection | B / E / F | Safety boundary | Yes | Safe automated trading cannot rely on placeholder allow | Policy source, Planning/Submit guard model | Phase15-L | `HIGH` |
| Report policy reason propagation | C / D / E / F | Report semantic scope | Yes | Report must explain why buy/sell/stop happened | Submit Active Policy Manifest | Phase15-M | `HIGH` |
| Notification policy reason propagation | C / D / E / F | Notification semantic scope | Yes | Review Required and urgency need clear reason/source | Report reason propagation | Phase15-M | `MEDIUM` |
| Regression suite expansion | C / D / E / F | Regression design | Yes | Prevents Phase14 hidden-default and review-level regressions | H-M implementation slices | Phase15-N | `BLOCKER` |
| Demo Operation rehearsal | A / C / D / E | Runtime trust evidence | Yes, after fixes | Full Runtime PASS needs operation-like evidence | H-N complete | Phase15-O | `BLOCKER` |
| Candidate / Opportunity AI direct execution contract | F | AI boundary | Design yes, full implementation optional | Prevents treating feature rows as proven AI output | Market/Feature contract | Phase15-P design track | `HIGH` |
| Position Management AI -> SELL Planning | F | SELL strategy boundary | Design yes, full implementation optional | Normal SELL must not be confused with cleanup liquidation | SELL policy and Current-only source | Phase15-P design track | `HIGH` |
| Operator Review / Recovery apply path | F | Recovery boundary | Design yes, full implementation optional | Review Required needs controlled return path | Audit/review queue design | Phase15-P design track | `HIGH` |
| Audit aggregator regular CLI connection | C / D / F | Audit boundary | Design yes, full implementation optional | Avoid audit-stage-only PASS | Report/Notification evidence | Phase15-P design track | `MEDIUM` |
| Production Broker Write / unlock | D / E / roadmap | Production readiness | No | Outside Demo Runtime trust scope | Phase15 PASS, production contract | Production phase | `BLOCKER` |
| Real Notification send | A / D / E | Operation readiness | No | Payload/delivery can be tested without real send | Delivery ledger and operator approval | Production/Operation phase | `HIGH` |
| launchd automatic operation | A / D / E | Operation readiness | No | Scheduler must follow Runtime acceptance | Phase15 Level3 evidence | Operation phase | `HIGH` |
| Advanced replacement AI | Roadmap / F | Strategy enhancement | No | Not needed for Runtime control trust | AI roadmap | Future | `INFO` |

## Recommended Implementation Order

The proposed H-O sequence is mostly correct, but Phase15-G adds a design lane for AI/Operator/Audit boundaries and makes Regression partly parallel. Recommended order:

```text
Phase15-H: Capital Deployment Policy / Policy Source Implementation
Phase15-I: Submit Guard BUY/SELL Separation + Active Policy Manifest
Phase15-J: Morning Planning Hidden Policy Removal
Phase15-K: SELL Broker Available Quantity Evidence
Phase15-L: Safety / Operation Guard Runtime Connection
Phase15-M: Report / Notification Policy Reason Propagation
Phase15-N: Regression Suite Expansion and Historical Regression Lock
Phase15-O: Demo Operation Rehearsal
Phase15-P: Deferred Boundary Design Pack
```

### Implementation Notes

- Phase15-H must come first because it defines the explicit policy object that Planning and Submit will consume.
- Phase15-I should implement side-specific Submit decisions and manifest evidence before Report/Notification work.
- Phase15-J removes Morning hidden defaults after the policy source exists.
- Phase15-K is required before SELL Submit Acceptance.
- Phase15-L must occur before Demo Operation because Safety placeholder allow cannot support "安心・安全".
- Phase15-M depends on policy/guard evidence existing upstream.
- Phase15-N should start with tests alongside each implementation slice, then finish as a consolidated regression lock.
- Phase15-O must not start until H-N blocker gates pass.
- Phase15-P can run as design-only if needed before final Phase15 close, but its full implementation can be deferred if limitations are explicit.

## Regression Order

| Order | Regression Area | Depends On | Why |
|---|---|---|---|
| 1 | No hidden policy static scan | None | Catches immediate reintroduction of known bad defaults. |
| 2 | Capital Deployment Policy missing / loaded behavior | Phase15-H | Proves Runtime does not invent fallback policy. |
| 3 | BUY >100k through CLI regular path | Phase15-H/I/J | Proves hidden Submit and Morning caps are gone. |
| 4 | SELL >100k through CLI regular path | Phase15-H/I/K | Proves SELL is not blocked by BUY cap and has quantity evidence. |
| 5 | 6+ candidates / max positions policy | Phase15-H/J | Proves Runtime does not silently cut at five. |
| 6 | Submit Active Policy Manifest fields | Phase15-I | Enables Report/Notification/Audit evidence. |
| 7 | Safety block / review propagation | Phase15-L | Proves Safety controls Planning/Submit. |
| 8 | Report / Notification policy reason propagation | Phase15-M | Proves operator-facing explanation. |
| 9 | POST_SEND_UNKNOWN and rerun idempotency | Phase15-I/N | Prevents duplicate Submit under uncertain state. |
| 10 | Full CLI regular path regression bundle | Phase15-H-N | Prevents direct-pipeline-only confidence. |

## Dependency Rules

- Capital Deployment Policy must exist before Submit Guard fixes can be accepted; otherwise amount policy remains ambiguous.
- Submit Guard Active Policy Manifest must exist before Report / Notification can explain Runtime decisions.
- SELL Broker available quantity evidence must exist before SELL Submit Acceptance.
- Safety / Operation Guard must be connected, or missing Safety must produce `REVIEW_REQUIRED`, before safe automated trading can be claimed.
- Regression must accompany each blocker fix; historical failure classes must be locked before Demo Operation.
- Demo Operation must not run before BLOCKER fixes and blocker regressions pass.
- Production unlock, launchd automation, and real notification send must not be inferred from Demo Operation.

## Acceptance Gate Redefinition

Phase15 Full Runtime PASS requires alignment across:

```text
Design Contract
Implementation
CLI Regular Path
Runtime Manifest
Current SoT
Broker Evidence
Report
Notification
Regression
Demo Operation Evidence
```

Gate requirements:

| Gate | Required Evidence |
|---|---|
| Design Contract | Architecture and Phase15 reports define policy, BUY/SELL, Safety, Evidence, and Review Level. |
| Implementation | Runtime code follows explicit contracts without hidden defaults. |
| CLI Regular Path | `run_daily_operation` regular jobs use the same policy and guard behavior as units. |
| Runtime Manifest | Active policy, guard decision, source, and Review Required reason are emitted. |
| Current SoT | `persistent_ledger/state.json` is updated only by valid Current writers and reflects Runtime-owned evidence. |
| Broker Evidence | Submit/Execution evidence is source-safe and not fake-adapter Full PASS. |
| Report | Report explains Current, Today, Run, History, policy reason, and Review Required scope. |
| Notification | Payload/queue/delivery level is clearly labeled; policy reason and urgency are present. |
| Regression | Hidden policy, BUY/SELL, CLI, manifest, Safety, Current, Report/Notification, idempotency tests pass. |
| Demo Operation Evidence | BUY and SELL demo rehearsals prove end-to-end Runtime behavior after blocker fixes. |

Non-PASS examples:

- `tests pass` alone.
- `Broker Accepted` alone.
- `Report generated` alone.
- `Payload generated` alone.
- Component PASS mistaken for Flow or Full Runtime PASS.
- fake adapter / fixture path declared as Full Runtime PASS.

## Explicitly Out of Phase15 Implementation Scope

These are not ignored; they are intentionally sent to later phases or production gates.

| Item | Relationship to Phase15 | Disposition |
|---|---|---|
| Production注文 / Production Broker Write | Related to final operation but not needed to re-establish Demo Runtime trust | Production unlock phase |
| real notification send | Related to operations; Phase15 may verify payload/queue/delivery contract only | Operation/notification send gate |
| launchd自動運用 | Requires Level3 Runtime evidence first | Operation readiness phase |
| Production broker capability / account mapping / NISA | Production correctness | Production readiness phase |
| fees / taxes / buying-power hold finalization | Production sizing correctness | Production readiness phase |
| tax-aware optimization | Portfolio enhancement | Future Enhancement |
| advanced replacement AI | Strategy enhancement | Future Enhancement |
| sector exposure optimization | Risk/portfolio enhancement | Future Enhancement |
| multi-account support | Product expansion | Future Enhancement |

## Phase15-G Decision

Phase15 scope is expanded from "known Submit/Morning blockers only" to "Runtime trust-critical control boundaries." However, Phase15 should not attempt to fully implement every AI strategy boundary. The required Phase15 implementation scope is:

```text
Explicit policy source
No hidden Runtime policy
BUY / SELL separated controls
SELL broker availability evidence
Safety connected or missing-Safety REVIEW_REQUIRED
Policy evidence propagated to manifest/report/notification
Regression lock
Demo operation evidence
```

AI direct execution contracts, Position Management AI full strategy connection, Operator Review apply automation, and Audit full CLI expansion must be designed in Phase15 and may be implemented later if the Phase15 Demo Runtime acceptance clearly labels their current limitations.

## Final Judgment

```text
PHASE15G_FIX_SCOPE_CONSOLIDATION_PRIORITY_PLAN_COMPLETE
```
