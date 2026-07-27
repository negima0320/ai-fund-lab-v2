# Phase21-E Phase22 Implementation Plan and Acceptance

## 1. Primary Judgment

```text
PHASE21_E_PLAN_COMPLETE_WITH_EVIDENCE_REQUESTS
```

Phase22実装計画、Evidence Requirement Matrix、共通Acceptance Checklist、Roadmap更新を作成した。

Phase21-EではProductionコード、Runtimeコード、Strategyコード、Config、Accepted Generationを変更していない。長時間Historical Runも実行していない。

## 2. Scope

Phase21-Eの目的は、Phase22に入る前に以下を固定することである。

- Phase22-A〜Lの実装順序
- 各TaskのObjective、Authority、Data Provenance、PIT、Failure Mode、Test、Artifact Refresh、User-run Validation、Acceptance、Reject、Rollback、Next Gate
- Phase22全体の共通Acceptance Checklist
- Evidence Requirement Matrix
- Phase21-F / Phase21-G / Phase22へのRoadmap接続

## 3. Created Documents

| File | Purpose |
|---|---|
| `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md` | Phase22-A〜Lの実装計画とEvidence Matrix |
| `docs/01_requirements/phase22_strategy_implementation_acceptance_checklist.md` | Phase22共通Acceptance Checklist |
| `docs/phase_reports/phase21_e_phase22_implementation_plan_and_acceptance.md` | Phase21-E完了報告 |
| `reports/phase21_e_phase22_implementation_plan_and_acceptance/phase21_e_evidence.json` | Phase21-E Evidence |

## 4. Updated Documents

| File | Update |
|---|---|
| `docs/01_requirements/phase_roadmap.md` | Phase21-E/F/GとPhase22-A〜Lの接続を追加 |

## 5. Phase22 Plan Summary

Phase22は以下の12タスクで進める。

| Task | Title |
|---|---|
| Phase22-A | Market Context Artifact Foundation |
| Phase22-B | Portfolio Policy Artifact Foundation |
| Phase22-C | Capital Deployment Responsibility Refactor |
| Phase22-D | Dynamic Position Count |
| Phase22-E | Dynamic Target Cash Ratio / Exposure Target |
| Phase22-F | Position Sizing Foundation |
| Phase22-G | PM Market Context Integration |
| Phase22-H | Regime-aware HOLD / ADD / REDUCE / EXIT |
| Phase22-I | Target Portfolio and Portfolio Construction |
| Phase22-J | Benchmark / Sector Authority Integration |
| Phase22-K | Performance Observability Completion |
| Phase22-L | Strategy Architecture Implementation Closure |

## 6. Dependency Graph

```text
Phase21-D
  -> Phase21-E
  -> Phase21-F
  -> Phase21-G
  -> Phase22-A
  -> Phase22-B
  -> Phase22-C
  -> Phase22-D
  -> Phase22-E
  -> Phase22-F
  -> Phase22-G
  -> Phase22-H
  -> Phase22-I
  -> Phase22-J
  -> Phase22-K
  -> Phase22-L
  -> Phase23
```

Phase22-JはBenchmark / Sector authorityのため、Phase22-A以降に並行調査可能だが、正式AcceptanceはPhase22-K/L前に必要である。

## 7. Evidence Requirement Summary

Phase22開始時点でAuthorityは設計済みだが、以下の数値・式・閾値は未確定である。

| Open Decision | Phase21-E handling | Later gate |
|---|---|---|
| Position Sizing formula | Authorityのみ固定。式は未採用 | Phase22-F / Phase23 |
| Benchmark Authority | integration taskを設定 | Phase22-J |
| Sector Authority | integration taskを設定 | Phase22-J |
| Market Context thresholds | schema / provenance優先 | Phase22-A / Phase23 |
| volatility window | provenance要件化 | Phase22-A/F |
| minimum holding period | policy reasonとして設計 | Phase22-H / Phase23 |
| cooldown | policy reasonとして設計 | Phase22-H / Phase23 |
| Safety absolute cash floor | Safety Authorityに分離 | Phase22-E / Phase23 |

## 8. User Commands Required Now

```text
None
```

Phase21-E完了時点では、ユーザーに新規Historical Runを要求しない。

Phase22の実装タスク完了後、5BD / 20BD / 245BDなどのUser-run Validationが必要になる。

## 9. Prohibited Operations Confirmation

| Item | Result |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| Accepted Generation Changed | NO |
| Long Historical Run Executed | NO |
| Training / Calibration Executed | NO |

## 10. Phase21-F Readiness

```text
READY
```

Phase21-Fでは、Phase21-D/Eで作成したArchitecture、Requirements、AI Design、Roadmap、Acceptance Checklistのcross-document consistency reviewを行う。

推奨次Task:

```text
Phase21-F Independent Cross-document Architecture Consistency Review
```

