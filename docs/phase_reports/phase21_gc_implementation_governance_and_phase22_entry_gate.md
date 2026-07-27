# Phase21-GC Implementation Governance and Phase22 Entry Gate

## 1. Primary Judgment

```text
PHASE21_GC_IMPLEMENTATION_GOVERNANCE_COMPLETE
```

Supporting judgments:

```text
DESIGN_FREEZE_DECLARED
CHANGE_REQUEST_PROCESS_DEFINED
ROLLBACK_PLAN_DEFINED
IMPLEMENTATION_GOVERNANCE_DEFINED
PHASE22_ENTRY_GATE_DEFINED
```

Phase21-GC defines Implementation Governance for Phase22. It does not change Production code, Runtime code, Strategy code, Config, thresholds, sizing formula, training, calibration, backtest, or Historical Run.

## 2. Design Freeze

Phase21-GC完了時点で、Strategy ArchitectureはDesign Freeze状態とする。

Freeze対象:

- Strategy Architecture v1
- Corporate Event Authority
- Migration Architecture
- Phase22 implementation sequence
- Artifact dependency matrix
- Empty Artifact Contract
- Bootstrap Contract
- Runtime Switch Gate
- Rollback / Old Path Removal rules
- Production / Demo / Historical common contract

Phase22での通常作業は、設計変更ではなく実装である。

## 3. Phase21で設計変更可能な範囲

Phase21-GC完了前:

- 責務Ownerの明確化
- Authority境界の明確化
- Migration順序の明確化
- Bootstrap / Empty / Failure Contractの明確化
- Phase22 Entry Gateの明確化

Phase21-GC完了後:

- 設計変更は原則禁止
- 必要な場合はDesign Change Requestとして扱う

## 4. Phase22で変更禁止の範囲

Phase22中にその場で変更してはならない。

- Strategy component responsibility
- Authority owner
- Artifact schema
- Runtime boundary
- Safety boundary
- Producer / Consumer order
- Empty Artifact Contract
- Bootstrap behavior
- Failure handling
- Runtime Switch Gate
- Old Path Removal Rule
- Production / Demo / Historical common contract
- PM threshold
- Candidate / Opportunity model
- Position Sizing formula
- Market Context threshold
- Corporate Event threshold
- Safety threshold

## 5. Design Change Request Rule

実装中に設計変更が必要になった場合、Implementation patchとして処理しない。

Required flow:

```text
Design Change Request
  -> Impact Analysis
  -> Architecture Review
  -> Approval
  -> Design document update
  -> Evidence update
  -> Implementation
```

Design Change Request must include:

- change id
- reason
- affected documents
- affected artifacts
- affected producers
- affected consumers
- Runtime impact
- Safety impact
- Artifact Acceptance impact
- Bootstrap impact
- Rollback impact
- user-run validation impact
- rejection alternative

禁止:

- その場で設計変更
- その場でContract変更
- その場でSchema変更
- Temporary Runtime Logic
- Review bypass

## 6. Step Acceptance Gate

各Implementation Step終了時に、次を確認する。

| Gate | Required |
|---|---|
| Schema | schema version、required fields、status vocabulary PASS |
| Producer | producer exists, deterministic, PIT-safe |
| Consumer | consumer implemented only after producer artifact exists |
| Authority | owner, source, acceptance boundary clear |
| Hash | source hash, artifact hash, input hash recorded |
| Failure | missing, stale, invalid, hash mismatch tested |
| Bootstrap | EMPTY / NOT_GENERATED / STALE / INVALID behavior tested |
| Compatibility | old/new coexistence reviewed |
| Runtime Connection | trace/fixture before active switch |
| Regression | targeted regression PASS |
| Evidence | machine-readable evidence updated |

PASSしない限り次Stepへ進まない。

## 7. Verification Points

各Stepの最小Verification:

```text
Schema confirmation
  -> Producer confirmation
  -> Hash confirmation
  -> Artifact confirmation
  -> Failure path confirmation
  -> Bootstrap confirmation
  -> Consumer confirmation
  -> Compatibility confirmation
  -> Regression confirmation
  -> Step Acceptance
```

途中PASSなしで次Stepへ進まない。

## 8. Rollback Point

各Step終了時にRollback Pointを定義する。

| Step | Rollback target | Procedure | Delete target | Keep artifact | Compatibility | Runtime impact |
|---|---|---|---|---|---|---|
| Market Context | previous no-context state | disable consumer, keep old Runtime | active consumer wiring only | generated read-only evidence | old path OK | no active switch |
| Corporate Event | previous no-event state | disable consumer, keep old Runtime | active consumer wiring only | source coverage evidence | old path OK | no active switch |
| Candidate / Opportunity compatibility | previous accepted generation path | remove trace refs | compatibility refs | parity evidence | old AI OK | no Runtime change |
| Portfolio Policy | previous no-policy active state | disable policy consumer | active policy binding | policy artifact evidence | old capital OK | no Runtime change |
| PM refs | previous PM accepted set | restore previous accepted PM source set | new refs wiring | PM trace evidence | sell compatibility required | no active switch unless accepted |
| Portfolio Construction | action-based planning | disable construction consumer | active construction binding | target artifact evidence | old planning OK | Runtime switch prohibited |
| Capital Deployment | previous capital policy path | restore previous accepted policy/source | active allocation binding | allocation evidence | old planning OK | no submit impact |
| Runtime Planning | old action-based planning bridge | restore old bridge | active execution intent binding | bridge evidence | pending compatibility required | Runtime switch rollback |
| Safety / Runtime switch | last accepted Runtime path | switch pointer/back to old path | new active pointer only | audit evidence | old path must remain | Runtime recovers |

## 9. Runtime Switch Gate

Runtime Switch is allowed only when all conditions pass.

| Condition | Required |
|---|---|
| Producer complete | PASS |
| Consumer complete | PASS |
| Schema PASS | PASS |
| Bootstrap PASS | PASS |
| Compatibility PASS | PASS |
| Failure path PASS | PASS |
| Artifact Acceptance | complete when source path becomes authority |
| Regression PASS | required targeted + Runtime regression |
| User Validation PASS | required for active Runtime switch |
| Rollback ready | previous path available |
| Old path retained | required |

Runtime Switch前に旧Pathを削除しない。

## 10. Old Path Removal Rule

旧Runtime / old Strategy path removal is prohibited until all conditions pass.

Removal conditions:

- Runtime Switch complete
- Regression PASS
- User Acceptance PASS
- Rollback不要確認
- no unresolved BLOCK / REVIEW_REQUIRED
- accepted artifact / source path updated
- audit evidence retained

Old path removal must be a separate task. It must not be bundled with Runtime Switch.

## 11. Emergency Rollback

Rollback trigger:

- Runtime HALT caused by new artifact/consumer
- Authority mismatch
- hash mismatch
- unexpected Pending / Submit behavior
- duplicate order risk
- Safety conflict
- user-run validation failure
- Production-equivalent regression failure

Rollback scope:

- active Runtime switch pointer
- new consumer binding
- new artifact active eligibility
- new bridge wiring

Rollback procedure:

```text
Stop active switch
  -> restore previous accepted path
  -> block new artifact consumer
  -> retain generated evidence
  -> run targeted regression
  -> confirm Runtime recovery
  -> record rollback evidence
```

Rollback validation:

- Runtime starts with previous path
- Pending canonical authority remains valid
- Submit does not consume invalid/new path
- Ledger / Current unchanged except audited safe state
- Safety no longer receives invalid new intent

## 12. Design Drift Prevention

禁止:

- Temporary Runtime Logic
- Historical専用処理
- Demo専用処理
- Producer未完成Consumer
- Hash bypass
- Review bypass
- Fail-open
- TODOのまま次Step
- test-only fallback
- direct accepted artifact edit
- old path deletion before switch acceptance
- Performance evidenceをRuntime / Training / Calibration入力にする

Design drift finding must result in `REVIEW_REQUIRED` or `BLOCK`.

## 13. Phase22 Entry Gate

Phase22開始条件:

| Requirement | Status |
|---|---|
| Phase21-D PASS | REQUIRED |
| Phase21-E PASS | REQUIRED |
| Phase21-F PASS | REQUIRED |
| Phase21-FA PASS | REQUIRED |
| Phase21-GB PASS | REQUIRED |
| Phase21-GC PASS | REQUIRED |
| Design Freeze declared | REQUIRED |
| Migration Design complete | REQUIRED |
| Dependency Graph complete | REQUIRED |
| Bootstrap complete | REQUIRED |
| Rollback complete | REQUIRED |
| Governance complete | REQUIRED |
| Open Decisions owner-classified | REQUIRED |
| No blocking responsibility gap | REQUIRED |
| No Runtime Contract gap | REQUIRED |
| No Safety Contract gap | REQUIRED |

Phase22開始可否:

```text
CONDITIONALLY_READY_AFTER_PHASE21_G_ENTRY_REVIEW
```

Phase21-GでEntry Gateの最終Acceptanceを行う。Phase21-GC単体ではPhase22実装開始を宣言しない。

## 14. Rollback可能範囲

Rollback可能:

- read-only artifact generation
- trace-only consumer
- compatibility refs
- Runtime switch pointer
- bridge wiring before old path removal
- active artifact eligibility before old path removal

Rollback不能または高リスク:

- accepted artifact direct edit
- old path deletion
- irreversible ledger/current mutation
- broker submit
- production order side effect
- destructive registry event deletion

Rollback不能な変更はPhase22 implementation stepに含めない。必要な場合は独立したReview / Approval taskにする。

## 15. Remaining Open Decisions

Open Decisions are value/source/formula decisions, not owner decisions.

| Decision | Owner | Type |
|---|---|---|
| Position Sizing formula | Portfolio Construction / Capital Deployment | formula |
| Market Context thresholds | Market Context Engine | threshold |
| Corporate Event source coverage | Corporate Event Authority | source |
| earnings release time precision | Corporate Event Authority | source |
| volatility window | Market Context / Capital Deployment | window |
| minimum holding period value | Position Management Policy | value |
| cooldown values | Position Management Policy / Portfolio Construction | value |
| Safety absolute cash floor | Safety | value |
| Benchmark source authority | Performance / Benchmark Authority | source |
| Sector mapping authority | Sector Authority | source |

## 16. Phase22 Design SoT

Phase22開始時点の設計SoT:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/01_requirements/strategy_performance_acceptance_contract.md`
- `docs/01_requirements/strategy_experiment_contract.md`
- `docs/01_requirements/phase22_strategy_implementation_acceptance_checklist.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/phase_reports/phase21_gb_strategy_migration_architecture_design.md`
- `docs/phase_reports/phase21_gc_implementation_governance_and_phase22_entry_gate.md`

## 17. Acceptance Result

| Acceptance | Result |
|---|---|
| Design Freeze定義 | PASS |
| Change Request Rule定義 | PASS |
| Acceptance Gate定義 | PASS |
| Rollback定義 | PASS |
| Verification Point定義 | PASS |
| Runtime Switch Gate定義 | PASS |
| Old Path Removal Rule定義 | PASS |
| Emergency Rollback定義 | PASS |
| Design Drift Prevention定義 | PASS |
| Phase22 Entry Gate定義 | PASS |

## 18. Prohibited Operations Confirmation

| Item | Result |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| Historical Run Executed | NO |
| Backtest Executed | NO |
| Training Executed | NO |
| Calibration Executed | NO |
| Threshold Decided | NO |
| Position Sizing Decided | NO |
| Phase22 Implementation Started | NO |

