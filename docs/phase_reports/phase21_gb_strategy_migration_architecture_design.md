# Phase21-GB Strategy Migration Architecture Design

## 1. Primary Judgment

```text
PHASE21_GB_STRATEGY_MIGRATION_ARCHITECTURE_COMPLETE
```

Supporting judgments:

```text
MIGRATION_PLAN_DEFINED
BOOTSTRAP_DEFINED
DEPENDENCY_GRAPH_DEFINED
IMPLEMENTATION_SEQUENCE_DEFINED
DATASET_DESIGN_DEFINED
```

Phase21-GBでは、Phase22実装開始前にStrategy Architecture v1への移行方法、Artifact依存関係、Bootstrap、Empty Artifact Contract、Producer completion order、Runtime migration、Compatibility、Initial Dataset、Implementation readiness checklistを定義した。

Productionコード、Runtimeコード、Strategyコード、Config、PM threshold、Position Sizing式、Historical Run、Backtest、Training、Calibrationは変更していない。

## 2. Migration Principles

- ProducerをConsumerより先に実装する
- Artifact schemaをProducerより先に固定する
- Empty / NOT_GENERATED / STALE / INVALID / BLOCK / REVIEW_REQUIREDを曖昧にしない
- Consumer-only実装を禁止する
- Runtime switchは新Artifactと新ConsumerのAcceptance後に行う
- Old path removalはRuntime switch後のRegression完了まで行わない
- Production / Demo / Historicalで別実装にしない
- Historical専用profit logic、event logic、fallbackを禁止する
- fail-openを禁止する

## 3. Component Dependency Graph

Formal graph:

```text
J-Quants PIT / Current / Runtime Authorities
  -> Market Context Producer
  -> Corporate Event Producer
  -> Candidate Producer
  -> Opportunity Producer
  -> Portfolio Policy Producer
  -> Position Management Producer
  -> Portfolio Construction Producer
  -> Capital Deployment Producer
  -> Runtime Planning Producer
  -> Safety
  -> Runtime
  -> Broker / Execution
```

Detailed dependency table:

| Component | Producer | Consumer | Depends on | Produces | Circular dependency risk | Rule |
|---|---|---|---|---|---|---|
| Market Context | Market Context Engine | Portfolio Policy, PM, Portfolio Construction, Performance | J-Quants PIT price/volume/calendar/features | Market Context Artifact | Low | no Candidate/PM dependency |
| Corporate Event | Corporate Event Authority | Candidate, Opportunity, Portfolio Policy, PM, Portfolio Construction, Safety | J-Quants PIT listed/event/corporate action sources, calendar | Corporate Event Artifact | Low | no Strategy output dependency |
| Candidate | Candidate AI Producer | Opportunity, Portfolio Construction | J-Quants PIT features, Corporate Event facts, Accepted Generation | Candidate Artifact | Medium | must not consume Opportunity/Portfolio Construction |
| Opportunity | Opportunity AI Producer | Portfolio Construction, PM reference | Candidate Artifact, Opportunity features, Corporate Event facts, Accepted Generation | Opportunity Artifact | Medium | must not consume Target Portfolio |
| Portfolio Policy | Portfolio Policy Engine | PM, Portfolio Construction, Capital Deployment | Market Context, Corporate Event aggregate risk, Current summary, Opportunity breadth | Portfolio Policy Artifact | Medium | may consume breadth summary, not final target portfolio |
| Position Management | PM Producer | Portfolio Construction, Sell Planning compatibility | Current positions, PM features, Market Context, Corporate Event facts, Portfolio Policy refs, Opportunity refs | PM Artifact | Medium | must not decide new BUY universe |
| Portfolio Construction | Construction Producer | Capital Deployment | Candidate, Opportunity, PM, Portfolio Policy, Corporate Event, Current, Pending | Target Portfolio Artifact, Strategy Intent Artifact | High | must not consume Allocation/Runtime Execution Intent |
| Capital Deployment | Capital Deployment Producer | Runtime Planning, Safety | Strategy Intent, Current, cash, Pending, price/lot evidence, policy | Allocation Artifact | Medium | must not rewrite Target Portfolio |
| Runtime Planning | Runtime Planning Producer | Safety, Approval, Pending, Submit | Allocation Artifact, Current, Pending, order condition authority | Execution Intent Artifact / Pending Candidate | Medium | must not calculate Strategy ranking/weight |
| Safety | Safety Producer | Runtime / Submit | Runtime Execution Intent, Current, policy, Broker evidence, Corporate Event hard-stop evidence | Safety Decision | Low | may block/review, not optimize Strategy |
| Runtime | Runtime controller | Broker, Ledger, Current, Reports | accepted authorities, pending, safety, broker state | ordered operations | Low | no Strategy calculation |
| Broker | Broker adapter | Runtime Ledger / Current | approved Runtime order | order / execution result | Low | no investment decision |

Cycle prohibition:

```text
Candidate -> Opportunity -> Portfolio Construction -> Capital Deployment -> Runtime Planning
```

は一方向のみ。下流Artifactは上流AIの当日入力に戻さない。

## 4. Artifact Dependency Matrix

| Artifact | Producer | Consumer | Generation timing | Required input | Optional input | Hash target | Authority | Empty state | Failure state |
|---|---|---|---|---|---|---|---|---|---|
| Market Context Artifact | Market Context Engine | Portfolio Policy, PM, Construction | after Feature Refresh | PIT price/volume/calendar/features | sector breadth | schema, source refs, source hashes, producer version | Market Context Evidence | `EMPTY_REVIEW_REQUIRED` | missing source `REVIEW_REQUIRED`, invalid/hash `BLOCK` |
| Corporate Event Artifact | Corporate Event Authority | Candidate, Opportunity, Policy, PM, Construction, Safety | after PIT source refresh | Listed Issues/event/corporate action sources, calendar | earnings time source, TOB source | schema, event source refs, source hashes, producer version | Corporate Event Fact | `EMPTY_REVIEW_REQUIRED` | missing/coverage `REVIEW_REQUIRED`, invalid/hash/final-trading-date exceeded `BLOCK` |
| Candidate Artifact | Candidate AI Producer | Opportunity, Construction | after Market/Corporate facts available | Accepted Generation, PIT features, Corporate Event facts | Market Context refs | model hash, feature schema, source refs, inference code hash | Candidate Universe | `EMPTY_PASS_NO_CANDIDATES` only when producer ran and found zero valid candidates | not generated `REVIEW_REQUIRED`, invalid/hash `BLOCK` |
| Opportunity Artifact | Opportunity AI Producer | Construction, PM reference | after Candidate | Candidate Artifact, Accepted Generation, opportunity features | Corporate Event risk refs | model hash, feature schema, candidate artifact hash, source refs | Opportunity Ranking | `EMPTY_PASS_NO_OPPORTUNITIES` only when Candidate empty/pass | not generated `REVIEW_REQUIRED`, invalid/hash `BLOCK` |
| Portfolio Policy Artifact | Portfolio Policy Engine | PM, Construction, Capital Deployment | after Market/Corporate/Current summaries | Market Context, Corporate Event aggregate risk, Current summary | Opportunity breadth | schema, source artifact hashes, producer version | Portfolio-level Target / Permission / Posture | `EMPTY_REVIEW_REQUIRED` | invalid target `BLOCK`, missing required source `REVIEW_REQUIRED` |
| PM Artifact | Position Management Producer | Construction, Sell Planning compatibility | after Policy and Current positions | Current positions, PM features, Policy refs, Market/Corporate facts | Opportunity refs | accepted PM source hash, policy hash, source refs | Existing Position Intent | `EMPTY_PASS_NO_POSITIONS` when Current has no positions | missing Current/Policy `REVIEW_REQUIRED`, invalid/hash `BLOCK` |
| Target Portfolio Artifact | Portfolio Construction | Capital Deployment | after Candidate/Opportunity/Policy/PM | Policy, Candidate/Opportunity, PM, Current, Pending, Corporate Event | sector/benchmark refs | schema, all input artifact hashes, construction version | Target Portfolio Decision | `EMPTY_PASS_NO_TARGET_POSITIONS` only when no qualified candidates and no positions | conflict `REVIEW_REQUIRED`, weights invalid `BLOCK` |
| Allocation Artifact | Capital Deployment | Runtime Planning, Safety | after Target Portfolio | Strategy Intent, Current, cash, Pending, price/lot evidence | liquidity/risk evidence | schema, target portfolio hash, policy hash, price refs | Allocation Candidate | `EMPTY_PASS_NO_ALLOCATIONS` only when Target Portfolio has no deltas | infeasible items recorded; global invalid/hash `BLOCK` |
| Execution Intent Artifact | Runtime Planning | Safety, Approval, Pending, Submit | after Allocation | Allocation Artifact, Current, Pending, order condition authority | broker availability snapshot | schema, allocation hash, current/pending refs | Runtime Planning / Pending Authority | `EMPTY_PASS_NO_PENDING_CANDIDATES` only when no allocations | missing allocation `REVIEW_REQUIRED`, invalid/hash `BLOCK` |

## 5. Bootstrap Design

Bootstrap states:

| State | Meaning | Consumer behavior | Runtime behavior |
|---|---|---|---|
| `EMPTY` | Producer ran successfully and intentionally produced no entries | consume if contract-specific PASS empty state | continue with no downstream action if downstream accepts empty |
| `NOT_GENERATED` | Producer has not run or artifact does not exist | do not consume as valid | `REVIEW_REQUIRED` before Strategy-dependent Runtime step |
| `STALE` | artifact exists but business_date/as_of/source freshness invalid | do not consume | `REVIEW_REQUIRED` or `BLOCK` by artifact type |
| `INVALID` | schema/content invalid | do not consume | `BLOCK` |
| `BLOCK` | hard contract violation | stop relevant path | halt/block relevant path |
| `REVIEW_REQUIRED` | evidence gap or human decision required | stop promotion to downstream decision | scoped review/block, no fail-open |

Bootstrap scenarios:

| Scenario | Expected result |
|---|---|
| Market Context complete, Corporate Event complete, Candidate not generated | Candidate status `NOT_GENERATED`; Opportunity and downstream Strategy artifacts `REVIEW_REQUIRED`; Runtime keeps old accepted path if not switched |
| Market Context missing, Corporate Event complete | Market Context `REVIEW_REQUIRED`; Portfolio Policy/PM/Construction cannot use Market Context; no new Strategy switch |
| Corporate Event missing, Market Context complete | Corporate Event `REVIEW_REQUIRED`; Candidate/Opportunity/PM/Construction cannot treat event absence as safe |
| Candidate ran and entries empty | Candidate `EMPTY_PASS_NO_CANDIDATES`; Opportunity may produce `EMPTY_PASS_NO_OPPORTUNITIES`; Construction may produce no new BUY if Current/PM allow |
| Current positions empty | PM `EMPTY_PASS_NO_POSITIONS`; Construction may build new BUY target from Candidate/Opportunity/Policy |
| Target Portfolio empty by decision | Allocation `EMPTY_PASS_NO_ALLOCATIONS`; Execution Intent `EMPTY_PASS_NO_PENDING_CANDIDATES`; Runtime no-op for orders |
| Execution Intent invalid | Safety/Runtime `BLOCK`; no Pending promotion |

## 6. Empty Artifact Contract

| Artifact | Empty allowed? | Empty status | Entries | Required evidence |
|---|---:|---|---|---|
| Market Context | No | `EMPTY_REVIEW_REQUIRED` | n/a | reason, missing source coverage |
| Corporate Event | No | `EMPTY_REVIEW_REQUIRED` | n/a | coverage report, missing source reason |
| Candidate | Yes, only after producer ran | `EMPTY_PASS_NO_CANDIDATES` | `[]` | producer result PASS, exclusion summary |
| Opportunity | Yes, only if Candidate empty/pass | `EMPTY_PASS_NO_OPPORTUNITIES` | `[]` | candidate artifact ref |
| Portfolio Policy | No | `EMPTY_REVIEW_REQUIRED` | n/a | missing source reason |
| PM | Yes, if Current positions empty | `EMPTY_PASS_NO_POSITIONS` | `[]` | Current ref showing no positions |
| Target Portfolio | Yes, if explicit no-position target | `EMPTY_PASS_NO_TARGET_POSITIONS` | `positions=[]` | construction reason codes |
| Allocation | Yes, if no target deltas | `EMPTY_PASS_NO_ALLOCATIONS` | `allocations=[]` | target portfolio hash |
| Execution Intent | Yes, if no allocations | `EMPTY_PASS_NO_PENDING_CANDIDATES` | `intents=[]` | allocation hash |

Empty is not a fallback. Empty is valid only when the producer ran, source authority passed, and reason evidence exists.

## 7. Producer Completion Order

Phase22 producer-first sequence:

| Step | Producer completion | Consumer completion | Gate |
|---|---|---|---|
| 1 | Market Context schema + producer | read-only fixture consumer only | schema/hash/PIT PASS |
| 2 | Corporate Event schema + producer | read-only fixture consumer only | coverage/failure/PIT PASS |
| 3 | Candidate artifact compatibility update | Opportunity read compatibility | Candidate output unchanged unless accepted |
| 4 | Opportunity artifact compatibility update | Construction read fixture | Opportunity output unchanged unless accepted |
| 5 | Portfolio Policy schema + producer | PM/Capital read fixture | Policy artifact valid; no behavior switch |
| 6 | PM producer refs update | Construction fixture / Sell compatibility | PM adapter acceptance required |
| 7 | Portfolio Construction producer | Capital fixture | Target Portfolio artifact valid |
| 8 | Capital Deployment producer | Runtime Planning fixture | Allocation artifact valid |
| 9 | Runtime Planning producer | Safety/Pending fixture | Execution Intent artifact valid |
| 10 | Runtime switch gate | Runtime consumer active | regression + artifact acceptance |
| 11 | Old path removal | none | only after switch acceptance |

Consumerを先に本番接続しない。Fixture consumerはschema validation目的に限る。

## 8. Runtime Migration Plan

Switch sequence:

```text
Current Runtime
  -> Temporary Compatibility
  -> New Artifact generated read-only
  -> New Consumer fixture validation
  -> Accepted Artifact refresh if source path becomes authority
  -> Runtime Switch behind explicit gate
  -> User-run validation
  -> Old Path Removal after regression
```

Runtime migration stages:

| Stage | Description | Allowed | Prohibited |
|---|---|---|---|
| Current Runtime | existing action-based planning remains authority | docs/schema prep | behavior switch |
| Temporary Compatibility | new artifacts generated read-only | source hashes, parity checks | old path deletion |
| New Artifact | producer emits artifact | validation, registry candidate | consumer behavior dependency before gate |
| New Consumer | downstream reads artifact in fixture/trace mode | lineage checks | order generation change |
| Runtime Switch | active Runtime path consumes new artifact | after acceptance only | partial switch without rollback |
| Old Path Removal | legacy path removed/deprecated | after user-run/regression | removal before successful switch |

## 9. Compatibility Matrix

| Combination | Compatibility | Reason / Required Guard |
|---|---|---|
| New Market Context + Old Candidate | OK read-only | Candidate does not require Market Context yet |
| New Market Context + Old PM | OK trace-only | PM must not change decisions until accepted |
| New Corporate Event + Old Candidate | OK read-only | Candidate ignores event facts until accepted integration |
| New Corporate Event + Old PM | OK trace-only | PM reason refs only after PM acceptance |
| New Portfolio Policy + Old Capital Deployment | OK read-only | Capital ignores Policy target until refactor gate |
| New Portfolio Policy + Old PM | OK trace-only | no PM threshold or action change |
| New PM refs + Old Sell Planning | REVIEW_REQUIRED | Sell compatibility and PM adapter acceptance needed |
| New Portfolio Construction + Old Runtime | REVIEW_REQUIRED | allowed only as artifact; Runtime cannot consume target portfolio until Planning bridge |
| New Capital Deployment + Old Runtime Planning | REVIEW_REQUIRED | Allocation artifact must have compatibility adapter |
| New Execution Intent + Old Submit | BLOCK unless Pending canonical compatibility passes | Submit consumes canonical Pending only |
| New Safety hard-stop + Old Runtime | REVIEW_REQUIRED | Safety output must map to existing block/review semantics |
| Old Candidate + New Opportunity requiring event fields | BLOCK | producer/consumer mismatch |
| Old Corporate Action proxy + New Corporate Event consumer | BLOCK | standalone authority missing |

## 10. Initial Dataset Design

| Dataset | Source | Refresh | Authority | Schema | Producer | Consumer |
|---|---|---|---|---|---|---|
| Market Context inputs | J-Quants prices, volume, calendar, features | daily before Strategy | J-Quants PIT / Feature Authority | market context input schema | Market Context Engine | Policy, PM, Construction |
| Corporate Event inputs | Listed Issues, earnings schedule source, corporate action source candidates | daily before Candidate/PM | Corporate Event Fact Authority | corporate_event_authority.v1 | Corporate Event Authority | Candidate, Opportunity, Policy, PM, Construction, Safety |
| Candidate inputs | J-Quants PIT features, accepted generation, Corporate Event facts | daily inference | Accepted AI Generation + PIT features | candidate artifact schema | Candidate AI | Opportunity, Construction |
| Opportunity inputs | Candidate artifact, opportunity features, accepted generation | daily inference | Accepted AI Generation + Candidate Authority | opportunity artifact schema | Opportunity AI | Construction, PM ref |
| Portfolio Policy inputs | Market Context, Corporate Event aggregate risk, Current summary, Opportunity breadth | daily after upstream artifacts | Portfolio Policy Authority | portfolio_policy.v1 | Portfolio Policy Engine | PM, Construction, Capital |
| Current Positions | persistent ledger/current state | runtime current | Current SoT | current state schema | Runtime Ledger/Current | PM, Construction, Capital, Safety |
| Broker Snapshot | broker read-only state | runtime preflight / sync | Broker Authority | broker snapshot schema | Broker adapter | Safety, Runtime |
| Trading Calendar | J-Quants calendar | daily/source refresh | Trading Calendar Authority | calendar schema | data refresh | Market, Corporate, Runtime |
| Listed Issues | J-Quants listed issues | daily/source refresh | Listed Issues PIT Authority | listed issue schema | data refresh / Corporate Event | Corporate, Candidate, Safety |
| Financial Statements | J-Quants financial statements | source refresh | J-Quants PIT Financial Authority | financial statement schema | feature/candidate producers | Candidate, Opportunity |
| Price History | J-Quants OHLCV | daily/source refresh | J-Quants PIT Price Authority | price history schema | feature producers | Market, Candidate, Opportunity, PM, Capital |

## 11. Implementation Readiness Checklist

| Component | Schema | Producer | Consumer | Authority | Hash | Failure | Bootstrap | Runtime connection |
|---|---|---|---|---|---|---|---|---|
| Market Context | REQUIRED | REQUIRED before consumer | fixture first | REQUIRED | REQUIRED | REQUIRED | REQUIRED | trace before active |
| Corporate Event | REQUIRED | REQUIRED before consumer | fixture first | REQUIRED | REQUIRED | REQUIRED | REQUIRED | trace before active |
| Candidate | existing + compatibility | existing / update after facts | Opportunity | Accepted Generation | REQUIRED | REQUIRED | REQUIRED | existing until switch |
| Opportunity | existing + compatibility | existing / update after Candidate | Construction fixture | Accepted Generation | REQUIRED | REQUIRED | REQUIRED | existing until switch |
| Portfolio Policy | REQUIRED | REQUIRED before PM/Capital behavior | fixture first | REQUIRED | REQUIRED | REQUIRED | REQUIRED | trace before active |
| Position Management | output refs required | REQUIRED before Construction | Sell/Construction | PM accepted set | REQUIRED | REQUIRED | REQUIRED | acceptance before behavior |
| Portfolio Construction | REQUIRED | REQUIRED before Capital | Capital fixture | Target Portfolio Authority | REQUIRED | REQUIRED | REQUIRED | no active Runtime until bridge |
| Capital Deployment | REQUIRED | REQUIRED before Planning | Planning fixture | Allocation Authority | REQUIRED | REQUIRED | REQUIRED | compatibility before active |
| Runtime Planning | REQUIRED | REQUIRED before Safety/Pending | Safety/Pending | Runtime Planning Authority | REQUIRED | REQUIRED | REQUIRED | active switch gate |
| Safety | mapping required | existing/update | Runtime/Submit | Safety Authority | REQUIRED | REQUIRED | REQUIRED | active after regression |

## 12. Migration Acceptance

Phase22へ進む前のGB acceptance:

| Acceptance | Status |
|---|---|
| 全Artifact Schema定義 | PASS as design |
| Dependency Graph完成 | PASS |
| Bootstrap定義 | PASS |
| Migration順序完成 | PASS |
| Compatibility確認 | PASS |
| Implementation順序完成 | PASS |
| Dataset設計完成 | PASS |
| Empty Artifact Contract完成 | PASS |
| Producer→Consumer順序定義 | PASS |
| 循環依存なし | PASS |

## 13. Required Phase22 Plan Amendment

Phase21-FA追加後のPhase22実装順序は、Corporate Event ArtifactをMarket Contextと同じfoundation tierに置く。

Recommended sequence:

```text
Phase22-A Market Context Artifact Foundation
Phase22-AA Corporate Event Artifact Foundation
Phase22-B Candidate / Opportunity compatibility and artifact dependency readiness
Phase22-C Portfolio Policy Artifact Foundation
Phase22-D Position Management refs and compatibility
Phase22-E Portfolio Construction Target Portfolio Foundation
Phase22-F Capital Deployment Responsibility Refactor
Phase22-G Runtime Planning Execution Intent Bridge
Phase22-H Dynamic Position Count
Phase22-I Dynamic Target Cash Ratio / Exposure Target
Phase22-J Position Sizing Foundation
Phase22-K Regime/Event-aware HOLD / ADD / REDUCE / EXIT
Phase22-L Benchmark / Sector Authority Integration
Phase22-M Performance Observability Completion
Phase22-N Strategy Architecture Implementation Closure
```

The existing Phase22-A through L labels may be retained if desired, but the implementation order must preserve the producer-first dependency:

```text
Market Context + Corporate Event
  -> Candidate/Opportunity compatibility
  -> Portfolio Policy
  -> PM refs
  -> Portfolio Construction
  -> Capital Deployment
  -> Runtime Planning
  -> Safety/Runtime switch
```

## 14. Prohibited Operations Confirmation

| Item | Result |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| PM Threshold Changed | NO |
| Position Sizing Formula Decided | NO |
| Historical Run Executed | NO |
| Backtest Executed | NO |
| Training Executed | NO |
| Calibration Executed | NO |
| Phase22 Implementation Started | NO |

