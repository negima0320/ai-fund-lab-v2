# Phase23-AP Phase21-23 Strategy Architecture Consolidation and Simplification Audit

## Primary Judgment

```text
PHASE23_AP_STRATEGY_ARCHITECTURE_CONSOLIDATION_AUDIT_COMPLETE
```

## Audit Scope

Phase21からPhase23-AOまでに追加・変更されたStrategy layer、Strategy Runtime wiring、artifact、authority、resolver、adapter、shadow path、legacy pathをread-onlyで監査した。

Production code、test、Runtime wiring、既存Run artifactは変更していない。fresh-run、resume、1BD、10BD、20BD、Runtime Switch、Broker Write、J-Quants取得、reclassificationは実施していない。

## Phase21-23 Component Count

棚卸し対象:

```text
17 components
```

分類:

```text
KEEP: 7
MODIFY: 5
MERGE: 3
REMOVE_CANDIDATE: 3
```

詳細:

```text
reports/phase23_ap_phase21_23_strategy_architecture_consolidation_and_simplification_audit/phase21_23_component_inventory.json
reports/phase23_ap_phase21_23_strategy_architecture_consolidation_and_simplification_audit/keep_modify_merge_remove_matrix.json
```

## Current Effective Runtime Path

現状の実Runtime経路は、設計上のStrategy component chainと、実行上のShadow/Consumer activationが分かれている。

```text
run_daily_operation.py morning
  -> generate_strategy_shadow_for_day()
  -> market_context
  -> corporate_event
  -> portfolio_policy
  -> dynamic_position_count
  -> dynamic_cash_exposure
  -> position_management
  -> portfolio_construction
  -> position_sizing
  -> capital_deployment
  -> runtime_planning
  -> activate_strategy_planning_authority()
  -> order_plan / pending_order_plan
```

`scripts/runtime_test.py`もStrategy Shadow生成を呼ぶが、既存2026-07-29 RunはPhase23-AO後のfresh Runtime validationではない。

## Canonical Authority Owners

Phase23-AO後の主要Authorityは以下。

| Value | Current owner | AP classification |
| --- | --- | --- |
| market regime | Market Context | KEEP |
| corporate event facts | Corporate Event Authority | KEEP |
| opportunity ranking | Buy AI / Opportunity producer | KEEP |
| target position count | Dynamic Position Count | MERGE |
| target gross exposure | Dynamic Cash / Exposure | MERGE |
| target membership | Portfolio Construction | KEEP |
| target weight | Portfolio Construction | KEEP |
| target notional | Position Sizing | KEEP |
| target quantity candidate | Position Sizing | KEEP |
| quantity delta candidate | Position Sizing | KEEP |
| planning intent | Runtime Planning | MODIFY |
| pending materialization | Strategy Planning Authority | MODIFY |

## Responsibility Overlaps

確認された重複:

- Portfolio Policy vs Dynamic Position Count: target position count posture / concrete countが分離しすぎている。
- Portfolio Policy vs Dynamic Cash / Exposure: cash/exposure posture / concrete target exposureが分離しすぎている。
- Dynamic Cash / Exposure vs Capital Deployment: cash/exposure/deployabilityの境界が重なる。
- Capital Deployment vs Position Sizing: Position Sizingが先に生成され、Capital Deploymentは後段生成されるため、Sizing側にdownstream placeholderが存在する。
- Runtime Planning vs Strategy Planning Authority: no-action、quantity unresolved、pending materialization判断が二段で行われる。
- Position Management base producer vs regime/event-aware producer: 同一PM schema上にproducer modeが併存する。

## Artifact / Authority Proliferation

Strategy判断1回に対して、現状はMarket Context、Corporate Event、Portfolio Policy、Dynamic Count、Dynamic Cash/Exposure、PM、Portfolio Construction、Position Sizing、Capital Deployment、Runtime Planning、Decision Trace、Input Materializationなど、多数のDRAFT/NOT_ELIGIBLE artifactが生成される。

Foundationとしては妥当だったが、Production-active pathでは以下が過剰。

- Dynamic Position Count standalone artifact
- Dynamic Cash / Exposure standalone artifact
- Capital Deployment standalone artifact
- Candidate / Opportunity Compatibility standalone layer
- legacy quality / score decision aliases

## Legacy / Superseded Paths

Phase23-AO後:

```text
target_weight
resolve_target_weight()
```

のみがPosition Sizingのdecision path。

以下は非正準。

```text
quality_score
allocation_quality_score
resolve_quality_score()
resolve_allocation_quality_score()
quality_adjustment
input_score quality alias
opportunity_score quality alias
```

分類は `NON_CANONICAL_OBSERVABILITY` または `REMOVE_CANDIDATE`。

## Review-required Propagation

APでは、すべての`REVIEW_REQUIRED`をMorning HALTへ昇格させる設計は過剰と判断した。

維持すべきfail-closed:

- schema invalid
- hash mismatch
- required source missing
- target_weight_authority missing
- safety block

HALT不要またはNO_ORDER十分:

- valid zero candidates
- valid zero target count
- valid zero target weight
- minimum notional unmet
- legacy quality missing when target_weight authority is valid

## Zero-state Semantics

Phase23-AO後、target weight / target notional / quantity candidateのzero semanticsは改善されている。

特に、minimum notional unmetでは:

```text
target_weight > 0
target_notional > 0
target_quantity_candidate = 0
```

を保持できる。これは「Strategy targetは解決済みだが執行可能数量はない」という状態であり、BUY強制でもAuthority欠損でもない。

## Production / Demo / Historical Parity

Strategy modulesはProduction / Demo / Historical共通code pathで呼ばれる。Mode差分はRuntime root、入力データ、broker/fill boundary、Historical authorityにある。

注意点:

- test fixtureがProduction contractを隠すリスクがある。
- Existing 2026-07-29 runsはAO前またはAO fresh validation前のRunであり、AO behavior証明ではない。
- Strategy Shadowという名前のままmorning active planningに使われるため、名称/状態の分離が必要。

## KEEP Items

- Market Context
- Corporate Event Authority
- Portfolio Construction after AO
- Position Sizing after AO
- Strategy Runtime Shadow generation
- Strategy Input Materialization
- Strategy Status Contract

## MODIFY Items

- Portfolio Policy
- Position Management
- Runtime Planning
- Strategy Planning Authority
- Strategy Observability / Attribution

## MERGE Items

- Dynamic Position Count -> Portfolio Policy concrete target-count resolver
- Dynamic Cash / Exposure -> Portfolio Policy concrete exposure/cash resolver
- Capital Deployment -> Runtime Planning / Strategy Planning Authority execution feasibility

## REMOVE Items

REMOVE_CANDIDATE:

- Candidate / Opportunity Compatibility standalone layer
- legacy quality / score decision aliases

Delayed retirement:

- Legacy Morning AI Planning path, only after Strategy Planning Authority is accepted and rollback gates pass.

## Recommended Simplified Architecture

```text
Market Context
Corporate Event Authority
  -> Portfolio Policy with target count / exposure resolvers
  -> Candidate / Opportunity Ranking
  -> Position Management
  -> Portfolio Construction target_weight authority
  -> Position Sizing notional / quantity candidate
  -> Runtime Planning pure intent mapper
  -> Strategy Planning Authority pending materializer
```

New component追加は不要。削除・統合・責務の縮退で整理可能。

## Consolidation vs Limited Rebuild Decision

```text
CONSOLIDATE_CURRENT_STRATEGY_ARCHITECTURE
```

Limited rebuildは不要。根拠:

- Phase23-AO後、主要canonical authorityは一意化できている。
- 問題の中心はmodule全面破綻ではなく、artifact proliferation、authority split、legacy path leakage。
- 対象merge / removeのほうが、再構築より小さく安全。

## Implementation Sequence

1. Phase23-AO target weight boundaryをcanonicalとして凍結。
2. Dynamic Position CountをPortfolio Policy内部resolverへ統合。
3. Dynamic Cash / ExposureをPortfolio Policy内部resolverへ統合。
4. Capital Deploymentのexecution feasibilityをRuntime Planning / Strategy Planning Authorityへ統合。
5. Runtime Planningをpure intent mapperへ縮退。
6. Strategy Planning Authorityをvalidation + pending materializationへ縮退。
7. Candidate / Opportunity Compatibilityとlegacy score aliasesを削除候補として退役。

## Architecture Documentation Updates

新規作成:

```text
docs/02_architecture/strategy_architecture_consolidation_review.md
```

`strategy_architecture_v1.md`のContract変更は実施していない。

## Existing Run Preservation

対象:

```text
runtime-test-historical-smoke-20260729T224044624059Z
runtime-test-historical-smoke-20260729T220208972293Z
```

結果:

```text
target_hash_preserved = true
compare_hash_preserved = true
artifact_mutation_detected = false
reclassification_performed = false
```

## Created / Updated Files

Human:

```text
docs/phase_reports/phase23_ap_phase21_23_strategy_architecture_consolidation_and_simplification_audit.md
```

Architecture review:

```text
docs/02_architecture/strategy_architecture_consolidation_review.md
```

Machine:

```text
reports/phase_reports/phase23_ap_phase21_23_strategy_architecture_consolidation_and_simplification_audit.json
```

Evidence:

```text
reports/phase23_ap_phase21_23_strategy_architecture_consolidation_and_simplification_audit/
```

## Remaining Gaps

- APはread-only auditのため、統合・削除・schema変更は未実施。
- AO後fresh Runtime validationは未実施。
- Production-active acceptanceは、AQでの整理後に再判断するべき。

## Implementation Readiness

```text
YES_FOR_PHASE23_AQ_PLANNING
```

## Runtime Rerun Readiness

```text
NO
```

理由: APは監査Taskであり、Dynamic Count / Dynamic Cash / Capital Deployment / Runtime Planning / Strategy Planning Authorityの整理が推奨されている。AO短時間Evidenceをfresh Runtime validationの代替として扱わない。

## Next Recommended Task

```text
Phase23-AQ Strategy Architecture Consolidation Implementation
```

ただし、ChatGPT Evidence Review後に正式決定する。
