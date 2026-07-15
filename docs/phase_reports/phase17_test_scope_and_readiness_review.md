# Phase17-TR Phase17 Test Scope and Readiness Review

## Final Judgment

Final judgment: `PHASE17_TEST_SCOPE_REPLAN_REQUIRED`

Phase17 の契約と方向性は維持する。ただし、5BD Historical Runtime Smoke Test の開始条件に Full / 1-Year 相当の PIT 完全性を要求しすぎていたため、段階的テスト戦略へ再計画する。

## Current Progress

| Target | Progress | Status | Basis |
| --- | ---: | --- | --- |
| `to_5bd_smoke` | 68% | `REPLAN_REQUIRED` | Historical composition, PM authority, Registry recovery, OHLCV source, normal Feature Producer/schema understanding are substantially ready; remaining 5BD blockers are reset execution, minimal window PIT acceptance, fill price/execution assumption, and explicit carryover/window decision. |
| `to_20bd_continuity` | 38% | `NOT_READY` | Needs continuity-grade calendar/listed coverage, corporate-action/no-event policy, fees/slippage/partial-fill assumptions, and attribution. |
| `to_1_year` | 24% | `NOT_READY` | Requires historical calendar/listed/corporate-action coverage and tax/performance attribution over a meaningful horizon. |
| `to_full_historical` | 18% | `NOT_READY` | Requires full-period PIT data and robust execution assumptions from 2021 onward. |
| `to_production` | 12% | `NOT_READY` | Requires Historical/Demo evidence, Production broker reconciliation, production capability evidence, and release acceptance. |

## Scope Matrix

| Review item | Judgment | Reason |
| --- | --- | --- |
| Runtime Mainline | `5BD必須` | 5BD smoke の主目的は通常 Runtime v2 mainline を Historical composition で通すこと。別 harness や historical-only mainline は契約違反。 |
| Historical Environment Composition | `5BD必須` | Phase17-B1I-A で formal historical mode は PASS。5BD はこれを使う最初の実行検証。 |
| Trading State Reset | `5BD必須` | 通常 .runtime を使うため、Current/Ledger/Pending/Runtime State の backup/reset/restore がないまま実行すると Demo/Production への状態混入リスクがある。 |
| Historical Broker | `5BD必須` | Submit/Execution を含む smoke では broker boundary replacement が必須。通常 Submit Guard/Execution Processor を保ったまま Historical adapter/provider を使う必要がある。 |
| Canonical OHLCV | `5BD必須` | Feature/valuation/fill の source。5BD では full 2021+ 完全性ではなく対象 window の accepted OHLCV と hash/manifest が必要。 |
| Trading Calendar | `5BD必須` | 対象5営業日の business-day 判定、carryover lag、market_date/feature_date 解決に必要。full historical calendar は20BD以降でよいが、5BD window calendar は必須。 |
| Listed Issues | `5BD必須` | Feature Producer の universe hard gate が listed snapshot を読む。5BD window の listed snapshot/as_of は必須。全期間履歴は1-Year/Fullでよい。 |
| Point-in-time Universe | `5BD必須` | Candidate/Opportunity 入力の future listed status leakage を避ける最低条件。5BDでは window PIT manifest で足りる。 |
| Corporate Action | `20BD必須` | Full PIT corporate action table は5BD smokeの絶対条件ではない。ただし5BD前に対象windowで split/delist 等が無い、または adjusted OHLCV policyで影響なし、という no-event/no-impact guard は必要。 |
| Historical Fill Price | `5BD必須` | Lifecycle contract は fill model 未受入なら Historical Submit/Execution を NOT_IMPLEMENTED_BLOCKING とする。Submit/Execution smoke には最小 fill price authority が必須。 |
| Feature Producer | `5BD必須` | Production/Demo/Historical で同じ normal Feature Producer を使うことが契約。5BDでは既存 artifacts/carryover を使う場合も producer lineage と source refs が必要。 |
| Feature Schema | `5BD必須` | Candidate/Opportunity/PM/Capital の入力互換性を守るため5BD前に schema hash/readiness が必要。 |
| Candidate AI | `5BD必須` | 5BD smoke の mainline に buy candidate decision が含まれるため accepted artifact set と no retraining が必要。 |
| Opportunity AI | `5BD必須` | Candidate 後段として planning に入るため accepted set/metrics/consumer compatibility が必要。 |
| PM | `5BD必須` | Sell/hold/position feature path と Current 連携を通すため必要。Phase17-B1I-B で authority は accepted。 |
| Capital Allocation | `5BD必須` | Planning/Submit Guard が sizing/policyを必要とする。最小 policy freeze と manifest が必要。 |
| Registry | `5BD必須` | Artifact identity and runtime eligibility authority。5BDでも unaccepted artifact fallback を禁止するため必要。 |
| Acceptance | `5BD必須` | 5BDで読む model/schema/PM/policy/data refs は accepted または明示された smoke-limited validated authority が必要。 |
| PM Authority | `5BD必須` | PM producer は Runtime mainline の一部。Phase17-B1I-B/BR で解決済みのため5BD gateとして保持。 |
| Historical Clock | `5BD必須` | business_date/evaluation_time 明示が contract requirement。5BDは clock injection の最初の実行検証。 |
| External Effect Blocking | `5BD必須` | Historical mode は tachibana/API/notification/blog 等を出してはならない。5BD前に fail-closed evidence が必要。 |
| Regression Baseline | `5BD必須` | 5BD前後の Current/Ledger/Pending/Registry/source hash 比較が smoke の安全弁。 |
| Performance Attribution | `20BD必須` | 5BDでは Runtime integrity と state transition を見る。性能評価として意味を持つには20BD以上の連続性と attribution が必要。 |
| Fees | `20BD必須` | 5BDは gross/zero-fee smokeでもよいが、20BD以降の実行性能評価では手数料モデルが必要。 |
| Tax | `1-Year必須` | 短期 smoke/20BD continuity では税務評価は主目的ではない。年次成績・Production判断には必要。 |
| Slippage | `20BD必須` | 5BDでは固定/zero slippage assumption を明示すれば開始可能。20BD以降は execution realism と成績解釈に必要。 |
| Partial Fill | `20BD必須` | 5BD は all-or-none/minimal fill assumption で smoke 可能。連続実行では未約定/部分約定の Pending/Ledger 継続性が必要。 |
| Execution Assumption | `5BD必須` | Fill date, price source, market/limit rule, lot/tick, insufficient cash/quantity, duplicate submit の最小契約がなければ Submit/Execution smoke が成立しない。 |
| Environment Transition | `20BD必須` | 5BD前は reset/restore が必要。Historical→Demo transition closure は20BD以降の継続テスト後に必須。 |
| Production Reconciliation | `Production必須` | Production initial Current は broker evidence/reconciliation が SoT。Historical/Demo state を継承しないため Production gate。 |

## PIT Items Re-evaluation

### Trading Calendar
- 5BD before-start judgment: 必要。ただし full historical calendar ではなく、対象5営業日の calendar_as_of/business-day/carryover lag を証明する window-level accepted manifest で足りる。
- Later-stage judgment: 20BD以降は連続性、1-Year/Fullでは historical coverage が必要。

### Listed Issues
- 5BD before-start judgment: 必要。Feature Producer の universe hard gate と future listed status 防止に、対象windowの listed snapshot/as_of が必要。
- Later-stage judgment: 1-Year/Full では上場/廃止履歴を再構成できる PIT listed history が必要。

### Corporate Action
- 5BD before-start judgment: 絶対的な full table は不要。ただし対象windowで corporate action の影響が無い、または adjusted OHLCV policy で影響を吸収するという no-event/no-impact guard は必要。
- Later-stage judgment: 20BD以降、特に1-Year/Fullでは standalone table または正式な adjusted-only policy が必須。

### Historical Fill Price
- 5BD before-start judgment: 必要。Submit/Execution を含むなら fill source/rule が未受入のままでは契約上 NOT_IMPLEMENTED_BLOCKING。
- Later-stage judgment: 20BD以降は fees/slippage/partial fill を追加して realism を上げる。

## 5BD開始条件

- Use normal Runtime v2 CLI/mainline with --mode historical, runtime_root=.runtime, explicit business_date/evaluation_time.
- Backup/reset/restore plan must be executable and hash-validated for resettable Trading State; no reset-excluded foundation touched.
- HistoricalSubmitAdapter and HistoricalExecutionSnapshotProvider must be selected by formal composition; external delivery and broker writes fail closed.
- Accepted Registry/Acceptance/PM authority checkpoint must be frozen before run.
- Target 5BD window must have either complete normal Feature artifacts or an explicitly accepted Runtime carryover case; 2026-07-09 may be a deliberate carryover smoke scenario only if recorded as such.
- Window-level Canonical OHLCV, Trading Calendar, Listed Issues, PIT Universe refs/hashes/manifests must be present.
- Corporate-action no-event/no-impact guard for the 5BD window, or accepted adjusted-OHLCV policy, must be recorded.
- Historical Fill Price and minimal Execution Assumption contract must be accepted before creating fills/current/ledger changes.
- Regression baseline hashes must be captured before first mutation and compared after restore/close.

## 20BD開始条件

- All 5BD conditions pass and 5BD runtime integrity has no HALT-class defect.
- 20BD calendar/listed/universe manifests prepared; no silent weekday/listed fallback.
- Corporate-action policy/table or no-event guard supports the full 20BD window.
- Fees, slippage, and partial-fill assumptions are accepted at least as review-grade execution assumptions.
- Performance attribution report template is ready, separating Runtime defects from strategy outcomes.

## 1年開始条件

- 20BD continuity passes without state drift, duplicate submit/execution, or restore failure.
- Historical PIT calendar/listed/corporate-action coverage supports the selected 1-year span.
- Tax treatment and annualized performance attribution are defined.
- Data gaps have explicit exclusion/no-trade rules rather than silent filling.

## Full開始条件

- 1-year run passes or defects are classified and fixed/accepted.
- Full period from effective historical start has PIT data coverage or explicit excluded dates.
- Corporate actions, delistings, suspensions, no quote, price limits, and missing data behavior are accepted.
- Performance attribution and reproducibility evidence scale to full period.

## Production開始条件

- Historical and Demo evidence are closed and cannot become Production authority.
- Production Current initialized from broker evidence and reconciliation only.
- Production broker capability, safety, policy, capital allocation, notification, and submit authority are separately accepted.
- Production release approval freezes Registry checkpoint, model/policy/schema versions, and rollback plan.

## 今すぐやるべきこと

- Reclassify 5BD as scoped smoke, not full PIT performance test.
- Choose either existing 2026-07-06..10 window with 2026-07-09 carryover as an explicit carryover scenario, or choose another 5BD window with complete normal feature artifacts.
- Accept minimal 5BD window PIT manifest for OHLCV/calendar/listed/universe and corporate-action no-impact guard.
- Accept minimal Historical Fill Price and Execution Assumption contract before Submit/Execution mutation.
- Execute backup/reset/restore dry-run validation and freeze regression baseline immediately before 5BD.

## 後回しでよいこと

- Full historical trading calendar/listed/corporate-action reconstruction beyond the 5BD window.
- Fees/tax/slippage/partial-fill realism beyond minimal documented assumptions.
- Performance attribution beyond smoke-level integrity checks.
- Production reconciliation and production broker enablement.

## Phase17 Overall Review

Previous Phase17 gates were correct for full Historical Runtime, but too broad for starting 5BD smoke. Keep the contracts, narrow the 5BD scope, and move full PIT/performance realism into 20BD/1-Year/Full gates.

## Evidence Basis

- Phase17-A
- Phase17-B
- Phase17-B1
- Phase17-B1R
- Phase17-B1I-A
- Phase17-B1I-B
- Phase17-B1I-BR
- Phase17-B1I-C
- Historical Runtime Contract
- Runtime Architecture v2
- Operational Lifecycle Contract
- Operational Data Architecture

No implementation, data fetch, feature generation, canonical update, Trading State reset, submit, execution, or external effect was performed in this review.
