# Runtime Temporal / Freshness Contract

作成日: 2026-07-10

## 1. 目的

本書は AI Fund Lab v2 Runtime v2 の日時、鮮度、営業日、市場データ更新、Broker evidence、Current 評価基準を定義する正式設計契約である。

本書は Phase15 専用資料ではない。Phase15 Runtime Acceptance で判明した freshness 問題を契機に作成するが、Phase16 以降および Production 運用を含む Runtime v2 全体の恒久 Source of Truth とする。

Runtime v2 は、単一の `as_of` や `artifact_date == runtime_business_date` だけで freshness を判定してはならない。すべての主要 artifact は、何の日付を表すのか、何と比較するのか、正当な carryover なのか、外部データ待ちなのか、本当に stale なのかを明示する。

## 2. Core Principles

- Runtime の正式 Time Zone は `Asia/Tokyo` とする。
- 営業日、取引セッション、JST 日付境界は JST で判定する。
- `generated_at` などの絶対時刻は UTC または timezone-aware timestamp として保持してよいが、営業日判定を UTC 日付で行ってはならない。
- `runtime_business_date`、`trading_session_date`、`market_data_as_of`、`feature_date`、`position_state_as_of`、`valuation_as_of` は別概念である。
- `latest_expected_trading_date` と `latest_available_market_date` を必ず分離する。
- Current は Position State と Valuation State を分離する。
- Broker Snapshot は Broker Evidence であり、Runtime-owned Current ではない。
- Demo 環境差異は Runtime Core 分岐ではなく `broker_environment` / `broker_capability` / `evidence_production_equivalent` として扱う。
- Current / Pending / Artifact の日付だけを書き換えて freshness を満たしてはならない。

## 3. Temporal Dimensions

| Field | Meaning | Source | Time Zone | Used By | Freshness Comparison Target |
|---|---|---|---|---|---|
| `runtime_business_date` | Operator / Runtime が処理対象とする業務日 | CLI `--business-date` or scheduler | JST date | All Runtime jobs | Calendar contract |
| `calendar_date` | 実カレンダー日 | System clock | JST date | Calendar resolution | JST now |
| `trading_session_date` | 市場取引セッション日 | Trading calendar | JST date | Market, Broker, Submit | Market calendar |
| `latest_expected_trading_date` | カレンダー上、データが存在するはずの最新営業日 | Calendar resolver | JST date | Market freshness, feature date, current valuation | `runtime_business_date`, current time, publication window |
| `latest_available_market_date` | 現在取得済み市場データの最新日 | Market data producer | JST date | Feature Refresh, Market Evidence, Data Readiness | `latest_expected_trading_date` |
| `market_data_as_of` | Market Evidence のデータ基準日 | Market evidence producer | JST date | Safety, valuation, features | `latest_expected_trading_date` or valid carryover date |
| `feature_date` | AI feature artifact が表す市場データ日 | Feature Refresh / Feature Date Contract | JST date | Candidate, Opportunity, PM AI, Morning | accepted market evidence date |
| `broker_snapshot_at` | Broker snapshot を取得した時刻 | Broker ReadOnly producer | timezone-aware timestamp | Safety, Submit SELL guard, Reconcile | max broker snapshot age |
| `broker_business_date` | Broker snapshot の営業日 | Broker adapter / snapshot payload | JST date | Broker freshness, Safety | `runtime_business_date` or broker session date |
| `position_state_as_of` | Runtime-owned position quantity / ownership の最終基準日 | Current projection | JST date | Planning, SELL Planning, Current | last accepted Runtime-owned execution or correction |
| `valuation_as_of` | Current valuation price / market value の評価基準日 | Valuation projection | JST date | Report, Safety, Capital Allocation | latest accepted market date |
| `last_execution_date` | Runtime-owned execution が最後に反映された日 | Execution / Ledger | JST date | Current freshness | latest Runtime-owned fill |
| `last_reconciled_at` | Reconcile が最後に完了した時刻 | Reconcile | timezone-aware timestamp | Safety, Report, Operator | reconciliation freshness policy |
| `safety_generated_at` | Safety Decision 生成時刻 | Safety Refresh | timezone-aware timestamp | Submit, Morning, Data Readiness | now / evidence dependency version |
| `safety_expires_at` | Safety Decision 有効期限 | Safety Refresh | timezone-aware timestamp | Submit, Morning, Data Readiness | now |
| `pending_target_session_date` | Pending が対象とする取引セッション日 | Pending writer | JST date | Approval, Submit | submit target session |
| `artifact_generated_at` | Artifact 生成時刻 | Each producer | timezone-aware timestamp | Audit, freshness, retry | producer-specific freshness |

## 4. Time Zone Contract

Runtime の正式 Time Zone は `Asia/Tokyo` とする。

| Concept | Contract |
|---|---|
| Business date | JST calendar date. CLI / scheduler が明示する。 |
| Market session date | JPX / trading calendar based JST date. |
| UTC timestamp | Artifact generation / audit timestamp may use UTC. |
| JST timestamp | Broker timestamp / operator-facing time may use JST with offset. |
| Broker timestamp | Must preserve raw broker time and normalized timezone-aware timestamp when available. |
| `generated_at` | Must include timezone or be explicitly UTC. |

UTC 保存は許可する。ただし `2026-07-10T00:30:00+09:00` を UTC 変換した結果の日付だけを使って `business_date=2026-07-09` と誤判定してはならない。

## 5. Trading Calendar Contract

Runtime は以下を明示する。

```text
business_date
trading_day
non_trading_day
latest_expected_trading_date
next_expected_trading_date
```

Calendar Source priority:

1. J-Quants calendar, when available and fresh.
2. JPX calendar, when available and fresh.
3. Repository canonical calendar.
4. Fallback weekday calendar.

Fallback calendar is allowed for local review, but Production Acceptance evidence level is lowered.

Manifest must include:

```text
calendar_source
calendar_status
trading_day
latest_expected_trading_date
next_expected_trading_date
fallback_used
production_equivalent
```

## 6. Latest Expected vs Latest Available

`latest_expected_trading_date` is calendar-derived. `latest_available_market_date` is producer-derived.

Example:

```text
runtime_business_date=2026-07-10
latest_expected_trading_date=2026-07-10
latest_available_market_date=2026-07-09
```

This is not automatically stale. It may be:

- `DATA_NOT_YET_AVAILABLE` before expected publication window.
- `VALID_CARRYOVER` when the Runtime job explicitly permits previous trading-day evidence.
- `STALE` after expected publication window plus grace period.
- `REVIEW_REQUIRED` when policy cannot classify the delay.

## 7. Freshness Status Contract

| Status | Meaning |
|---|---|
| `READY` | Expected date, time, schema, and dependency contract are satisfied. |
| `VALID_CARRYOVER` | Previous evidence is explicitly valid due to non-trading day, publication wait, or defined carryover contract. |
| `DATA_NOT_YET_AVAILABLE` | External data is legitimately not yet published; producer is not considered broken. |
| `STALE` | Expected publication / refresh window has passed and evidence is still old. |
| `MISSING` | Required artifact does not exist. |
| `DATE_MISMATCH` | Evidence from incompatible business/session dates is mixed. |
| `EXPIRED` | Time-limited artifact, such as Safety Decision or Approval, exceeded its validity. |
| `REVIEW_REQUIRED` | Operator review is required before progressing. |
| `HALT` | Runtime must stop due to safety or integrity risk. |
| `NOT_REQUIRED` | Component evidence is not required for this job/scope. |

Status precedence:

```text
HALT > REVIEW_REQUIRED > EXPIRED > STALE > DATE_MISMATCH > MISSING > DATA_NOT_YET_AVAILABLE > VALID_CARRYOVER > READY > NOT_REQUIRED
```

`DATA_NOT_YET_AVAILABLE` is not `READY`, but it is also not a producer defect. It usually leads to WAIT / REVIEW_REQUIRED for trading actions.

## 8. Current Contract

Current must not be represented by a single ambiguous `as_of`.

Minimum Current temporal fields:

```text
position_state_as_of
valuation_as_of
last_execution_date
last_reconciled_at
source_market_date
updated_at
```

### Position State

Position State means Runtime-owned quantity, average price, and ownership.

Valid update triggers:

- accepted Runtime-owned execution
- reconcile correction with explicit authority
- corporate action handling

No-fill day does not require `position_state_as_of == runtime_business_date`.

### Valuation State

Valuation State means current price, market value, unrealized PnL, and valuation confidence.

Valid update triggers:

- latest available market evidence
- fresh Broker valuation evidence, if explicitly accepted as valuation source
- valuation-only projection job

No-fill day may update valuation without changing quantity or average price.

`position_state_as_of` and `valuation_as_of` do not need to be the same date.

## 9. Current Freshness Contract

The old rule is retired:

```text
Current.as_of == business_date
```

Replacement:

```text
current_position_status
current_valuation_status
```

Examples:

| Condition | Expected Status |
|---|---|
| `position_state_as_of=2026-07-09`, `last_execution_date=2026-07-09`, no Runtime-owned execution on 2026-07-10 | `current_position_status=READY` |
| `valuation_as_of=2026-07-10`, `source_market_date=2026-07-10` | `current_valuation_status=READY` |
| Non-trading day 2026-07-11, latest expected trading date 2026-07-10, valuation date 2026-07-10 | `current_valuation_status=VALID_CARRYOVER` |
| Expected market date 2026-07-10 but valuation date 2026-07-09 after publication grace period | `current_valuation_status=STALE` |
| Broker-only position appears but Runtime-owned Current does not own it | Current position does not absorb Broker-only position; Reconcile may REVIEW_REQUIRED |

## 10. No-Fill / Valuation-Only Contract

Runtime requires a regular no-fill valuation-only path.

Proposed flow:

```text
Market / Quote Evidence
↓
Runtime-owned Current positions
↓
Valuation-only projection
↓
Current valuation fields update
↓
History / Manifest
```

Required producer responsibilities:

- Use Runtime-owned positions only.
- Do not add Broker-only positions to Current.
- Do not change quantity.
- Do not change average price except through explicit corporate action or correction.
- Update `current_price`, `market_value`, `unrealized_pnl`.
- Update `valuation_as_of` and `source_market_date`.
- Preserve `position_state_as_of`.
- Record `no_fill=true`.
- Record `valuation_source`.
- Write manifest and ledger/audit evidence.
- Never edit JSON directly.

CLI job candidate:

```text
--job current_valuation_refresh
```

This is a design requirement. This document does not implement the job.

## 11. Market Evidence Contract

Canonical artifact:

```text
.runtime/runtime_state/market/<market_date>/market_evidence.json
```

Minimum schema:

```text
schema_version
runtime_business_date
market_date
latest_expected_trading_date
latest_available_market_date
generated_at
calendar_source
calendar_status
trading_day
market_status
quote_status
market_summary
quotes
data_provider
provider_status
data_not_yet_available
stale
fallback_used
production_equivalent
```

`market_date` is the accepted market evidence date, not necessarily `runtime_business_date`.

## 12. Quote Evidence Contract

Quote evidence is used by Safety and Current valuation. Each quote must include:

```text
symbol
price
price_type
market_date
observed_at
source
freshness_status
adjusted
```

Supported price types:

```text
daily_close
intraday_quote
broker_valuation_price
jquants_daily_quote
```

Safety may require wall-clock quote freshness for risk monitoring. Valuation may accept daily close or valid carryover, depending on trading calendar and publication window.

## 13. J-Quants Availability Contract

`latest_available_market_date < latest_expected_trading_date` must be classified, not automatically failed.

Distinguish:

```text
API_ERROR
AUTHENTICATION_ERROR
RATE_LIMIT
MAINTENANCE
DATA_NOT_YET_PUBLISHED
LEGITIMATE_PREVIOUS_TRADING_DATE
STALE_CACHE
```

Runtime configuration must define:

```text
expected_publication_window
grace_period
retry_policy
operator_action
```

If a fixed publication time is configured, the source must be documented and the time must remain configurable. Hard-coded publication assumptions are forbidden.

## 14. Feature Date Contract

Feature date should follow accepted market evidence date:

```text
feature_date == accepted_market_evidence_date
```

Candidate AI, Opportunity AI, and Position Management AI must use the same feature date for the same Runtime decision flow.

Carryover must be explicit in manifest:

```text
feature_date
runtime_business_date
carryover_reason
carryover_status
production_equivalent
latest_expected_trading_date
latest_available_market_date
```

## 15. Broker Snapshot Freshness

Broker Snapshot freshness is wall-clock based and date based.

Minimum fields:

```text
snapshot_at
broker_business_date
broker_environment
connection_status
account_reset_detected
capability_status
production_equivalent
```

Demo reset means Broker Snapshot and Runtime-owned Current can differ legitimately. Runtime must not convert Broker positions into Runtime-owned Current without explicit Runtime-owned fill or authorized correction.

## 16. Safety Temporal Contract

Safety must evaluate dependency freshness:

```text
market_evidence_date
quote_freshness
broker_snapshot_age
current_position_date
current_valuation_date
orders_date
executions_date
runtime_state_date
safety_generated_at
safety_expires_at
```

Safety Decision must record dependency hashes:

```text
evidence_hash
dependency_version
dependency_generated_at
dependency_artifact_path
```

If a dependency changes after Safety Decision generation, Safety must be re-evaluated before Morning / Submit can be considered READY.

## 17. Runtime State Contract

`.runtime/runtime_state/current_state.json` must be classified as one of two roles.

Decision:

```text
AUTHORITATIVE_RUNTIME_OPERATION_STATE
```

`.runtime/runtime_state/current_state.json` is authoritative for Runtime operation state only.

It is not authoritative for:

- positions
- cash
- buying power
- total equity
- pending submit target
- approval source

Those remain owned by:

```text
persistent_ledger/state.json
pending_order_plan/pending_order_plan.json
runtime_state/safety/latest_safety_decision.json
```

Minimum schema:

```text
schema_version=runtime_v2_operation_state_v1
role=authoritative_runtime_operation_state
business_date
generated_at
updated_at
environment
runtime_mode
state
safety_state
current_safety_state
source
asset_state_source
pending_state_source
asset_state_is_authoritative_here=false
pending_state_is_authoritative_here=false
production_equivalent
```

Producer:

```text
runtime_state_refresh
```

Producer responsibilities:

- write only `.runtime/runtime_state/current_state.json`
- use atomic publish
- record Runtime state machine state and Safety state
- never copy asset values from `persistent_ledger/state.json`
- never copy active pending items from `pending_order_plan/pending_order_plan.json`
- set `asset_state_is_authoritative_here=false`
- set `pending_state_is_authoritative_here=false`

Consumers:

```text
Safety Evaluation
Data Readiness
Runtime Orchestrator
Report
Audit
Recovery / Review
```

Freshness:

```text
business_date == runtime_business_date
environment == runtime mode
schema_version == runtime_v2_operation_state_v1
role == authoritative_runtime_operation_state
state is a valid RuntimeState
generated_at is timezone-aware producer timestamp
```

Missing / stale behavior:

| Condition | Status |
|---|---|
| Missing file | `REVIEW_REQUIRED` |
| Invalid JSON / non-object | `HALT` |
| Missing required fields | `REVIEW_REQUIRED` |
| Stale business date | `REVIEW_REQUIRED` |
| Legacy / advisory role | `REVIEW_REQUIRED` |
| Invalid RuntimeState | `REVIEW_REQUIRED` |

Design decision:

```text
RUNTIME_STATE_CONTRACT_COMPLETE
```

## 18. Non-Trading-Day Contract

Production:

```text
no trading operation
```

Demo Acceptance override:

```text
Runtime Core verification only
latest_expected_trading_date evidence may be used
production_equivalent=false
```

Non-trading day statuses:

| Case | Status |
|---|---|
| Previous trading-day evidence matches latest expected trading date | `VALID_CARRYOVER` |
| Market data not expected because market closed | `VALID_CARRYOVER` or `NOT_REQUIRED`, by job scope |
| Runtime tries trading action without override | `REVIEW_REQUIRED` / `BLOCKED` |
| Demo override active | `DEMO_ACCEPTANCE_OVERRIDE`, `production_equivalent=false` |

## 19. Demo Reset Contract

Tachibana Demo may have:

- cash reset
- holdings reset
- 9000-series execution restrictions
- API time-window restrictions

Represent these as:

```text
broker_environment
broker_capability
demo_reset_detected
evidence_production_equivalent
review_required
```

Do not create demo-only Runtime, demo-only Current, demo-only Ledger, or demo-only Policy.

## 20. Data Readiness Integration

Data Readiness must emit expected date, actual date, status, reason, and comparison contract per component.

Minimum fields:

```text
market_freshness_status
feature_freshness_status
current_position_status
current_valuation_status
broker_snapshot_status
safety_temporal_status
pending_temporal_status
```

Each component must include:

```text
expected_date
actual_date
generated_at
expires_at
comparison_target
freshness_status
reason
source_artifact
```

## 21. Temporal Consistency Matrix

| Scenario | Business Date | Latest Expected | Latest Available | Current Position Date | Valuation Date | Expected Status |
|---|---|---|---|---|---|---|
| 通常営業日・データ更新済み | 2026-07-10 | 2026-07-10 | 2026-07-10 | 2026-07-10 or last execution date | 2026-07-10 | `READY` |
| 営業日・J-Quants配信前 | 2026-07-10 | 2026-07-10 | 2026-07-09 | last execution date | 2026-07-09 | `DATA_NOT_YET_AVAILABLE` / wait |
| 営業日・配信予定時刻超過 | 2026-07-10 | 2026-07-10 | 2026-07-09 | last execution date | 2026-07-09 | `STALE` / `REVIEW_REQUIRED` |
| 土曜日 | 2026-07-11 | 2026-07-10 | 2026-07-10 | last execution date | 2026-07-10 | `VALID_CARRYOVER` |
| 月曜祝日 | 2026-07-13 | 2026-07-10 | 2026-07-10 | last execution date | 2026-07-10 | `VALID_CARRYOVER` |
| 約定なし | 2026-07-10 | 2026-07-10 | 2026-07-10 | 2026-07-09 | 2026-07-10 | Position `READY`, valuation `READY` |
| 当日約定あり | 2026-07-10 | 2026-07-10 | 2026-07-10 | 2026-07-10 | 2026-07-10 | `READY` after execution projection |
| Broker Snapshotのみ当日 | 2026-07-10 | 2026-07-10 | 2026-07-09 | 2026-07-09 | 2026-07-09 | Broker `READY`, market/valuation `DATA_NOT_YET_AVAILABLE` or `STALE` |
| Demo口座リセット | 2026-07-10 | 2026-07-10 | 2026-07-10 | Runtime-owned date | valuation date | Broker diff as evidence, not Current overwrite |
| Market data更新済み・Current valuation未更新 | 2026-07-10 | 2026-07-10 | 2026-07-10 | last execution date | 2026-07-09 | `current_valuation_status=STALE` |
| Current position stateは古いが約定なし | 2026-07-10 | 2026-07-10 | 2026-07-10 | 2026-07-09 | 2026-07-10 | Position `READY`, valuation `READY` |
| Safety Decision期限切れ | 2026-07-10 | 2026-07-10 | 2026-07-10 | any | any | `safety_temporal_status=EXPIRED` |
| Feature date carryover | 2026-07-10 | 2026-07-10 | 2026-07-09 | last execution date | 2026-07-09 | `VALID_CARRYOVER` only before publication/grace |
| Market / Broker date mismatch | 2026-07-10 | 2026-07-10 | 2026-07-10 | any | any | `DATE_MISMATCH` or component REVIEW_REQUIRED |

## 22. Status Decision Examples

### Example A: J-Quants publication window not reached

```text
runtime_business_date=2026-07-10
latest_expected_trading_date=2026-07-10
latest_available_market_date=2026-07-09
current_time=before expected publication window
```

Result:

```text
market_status=DATA_NOT_YET_AVAILABLE
feature_status=VALID_CARRYOVER or REVIEW_REQUIRED by job scope
current_valuation_status=VALID_CARRYOVER
Morning=REVIEW_REQUIRED / WAIT
```

### Example B: Publication grace period passed

```text
runtime_business_date=2026-07-10
latest_expected_trading_date=2026-07-10
latest_available_market_date=2026-07-09
current_time=after publication grace period
```

Result:

```text
market_status=STALE
feature_status=STALE
current_valuation_status=STALE
Morning=REVIEW_REQUIRED
```

### Example C: No-fill day

```text
runtime_business_date=2026-07-10
last_execution_date=2026-07-09
position_state_as_of=2026-07-09
source_market_date=2026-07-10
valuation_as_of=2026-07-10
```

Result:

```text
current_position_status=READY
current_valuation_status=READY
Morning may proceed if Safety and other evidence are READY
```

## 23. Implementation Impact Matrix

| Module | Current Behavior | Required Change | Severity | Dependency |
|---|---|---|---|---|
| `market_refresh` | Generates feature artifacts and feature consumer readiness; market evidence producer not fully confirmed | Produce canonical Market Evidence and Quote Evidence | HIGH | Market provider / calendar |
| `market_evidence producer` | Not confirmed as regular Runtime producer | Add `.runtime/runtime_state/market/<date>/market_evidence.json` producer | BLOCKER | Market Refresh |
| `quote evidence producer` | Not confirmed for Safety / valuation | Add quote schema and accepted price source | BLOCKER | Market Evidence |
| `feature_date_contract` | Uses requested/latest feature dates and consumer readiness | Align `feature_date` with accepted market evidence date and publication/carryover status | HIGH | Market Evidence |
| `current projection` | Runtime-owned fill projection can write Current after execution acceptance | Split position and valuation temporal fields | BLOCKER | Current schema migration |
| `current valuation refresh` | No confirmed no-fill valuation-only job | Add regular no-fill valuation-only producer | BLOCKER | Market / Quote Evidence |
| `safety evaluation` | Reads Current, Broker, Market, Orders, Executions, Runtime State | Use Temporal Contract and dependency hashes; clarify Runtime State role | HIGH | Market/Broker/Current contracts |
| `data_readiness` | Phase15-AS semantic status exists but still uses simplified current freshness | Emit temporal component statuses and expected/actual dates | BLOCKER | Temporal Contract implementation |
| `runtime state` | Role ambiguous | Decide authoritative vs legacy and implement accordingly | HIGH | Safety contract |
| `report` | Derived report can show reason evidence | Add temporal freshness section | MEDIUM | Data Readiness |
| `notification` | Summary payload exists | Add temporal freshness summary and operator action | MEDIUM | Report/Data Readiness |
| `tests` | Cover Phase15-AS semantics | Add temporal matrix regression cases | HIGH | All above |

## 24. Migration Plan

Current schema migration must not be manual.

Existing fields:

```text
as_of
updated_at
```

Target fields:

```text
position_state_as_of
valuation_as_of
source_market_date
last_execution_date
last_reconciled_at
updated_at
```

Migration approach:

1. Add backward-compatible readers that derive missing temporal fields from legacy `as_of` only as `LEGACY_DERIVED`, not as full Production evidence.
2. Add a formal migration/projection job that reads existing Current, Ledger, and Market Evidence and writes upgraded Current schema.
3. Add manifest fields:
   ```text
   current_schema_migration_status
   legacy_as_of_used
   derived_position_state_as_of
   derived_valuation_as_of
   production_equivalent
   ```
4. After migration, Data Readiness must prefer explicit temporal fields over legacy `as_of`.
5. Remove legacy fallback only after regression and Demo Acceptance pass.

Forbidden:

```text
direct Current edit
date-only rewrite
copying old Current to new date
Broker position copy into Runtime-owned Current
```

## 25. Acceptance Criteria

Temporal Contract implementation is accepted only when:

- business date and market date are not mixed.
- no-fill days are handled without false Current stale.
- non-trading days are handled with valid carryover / no trading operation.
- J-Quants update waiting and stale cache are distinct.
- Current position state and valuation state are separate.
- Broker-only positions do not enter Current.
- Safety dependency evidence is temporally consistent.
- Data Readiness uses the shared Temporal Contract.
- Demo restrictions are not Runtime Core branches.
- Producer and Consumer use the same contract definitions.

## 25.1 Broker Snapshot ReadOnly Producer Contract

Broker Snapshot is Broker Evidence. It is not Current Position State, Persistent Ledger, Execution Result, or Approval State.

Producer:

```text
broker_readonly_refresh
```

Canonical artifacts:

```text
.runtime/runtime_state/broker_readonly/<runtime_business_date>/tachibana_snapshot.json
.runtime/runtime_state/broker_readonly/latest.json
```

Required snapshot fields:

```text
schema_version
runtime_schema_version
provider
account_id_redacted
runtime_business_date
business_date
broker_snapshot_as_of
snapshot_at
generated_at
evaluation_time
freshness_status
freshness_reason
positions
cash / account_summary
buying_power
open_orders
executions
read_only=true
review_required
```

Consumer:

- Safety Evaluation
- Data Readiness
- Submit SELL guard where available quantity evidence is required
- Reconcile / operator review

Freshness:

- Compare `broker_snapshot_as_of` / `snapshot_at` against explicit `evaluation_time`.
- Missing snapshot returns `REVIEW_REQUIRED`.
- Invalid or timezone-missing timestamp returns `REVIEW_REQUIRED`.
- Snapshot older than the configured max age returns `REVIEW_REQUIRED` via stale freshness.
- Fresh snapshot returns `READY`.

Source of Truth boundary:

- Broker Snapshot may prove external broker account / position / order / cash evidence.
- Broker Snapshot must not be copied into Runtime-owned Current.
- Runtime-owned Current changes only through explicit Current / Ledger contracts.

Idempotency and side-effect boundary:

- The snapshot-only producer may overwrite the fixed dated snapshot artifact and latest pointer.
- It must not submit or cancel broker orders.
- It must not append persistent ledger records.
- It must not mutate Pending.
- It must not mutate Current Position.
- It must not perform execution classification mutation.

Secret handling:

- Authentication credentials, private keys, passwords, and full account identifiers must not be written to snapshot, report, manifest, or logs.
- Account identity must be redacted or represented only by a non-reversible identifier.

Failure behavior:

- Provider failure writes/returns `REVIEW_REQUIRED` evidence.
- Missing artifact writes/returns `REVIEW_REQUIRED` evidence.
- Stale artifact writes/returns `REVIEW_REQUIRED` evidence.
- Producer implementation exceptions must not be converted to `READY`.

## 25.2 Broker Authenticity and Account Alignment Contract

Broker Snapshot freshness is not Broker Snapshot authenticity.

Runtime v2 Broker Evidence must distinguish:

```text
provider
adapter
transport
environment
account_identity_hash
data_origin
fixture_used
mock_used
read_only
runtime_business_date
broker_snapshot_as_of
generated_at
freshness_status
authenticity_status
account_alignment_status
```

Accepted `data_origin` values:

```text
BROKER_API
FIXTURE
MOCK
CACHED_API_RESPONSE
UNKNOWN
```

Accepted `authenticity_status` values:

```text
READY
REVIEW_REQUIRED
BLOCKED
```

Accepted `account_alignment_status` values:

```text
MATCHED
NOT_APPLICABLE
MISMATCH
UNKNOWN
```

Nested `source="mock"` in normalized Broker payloads is not sufficient for Safety-ready Broker Evidence. If it is a legacy normalizer label, the adapter must replace it with explicit transport and data-origin evidence before the snapshot can be accepted as authentic. Until then, nested `source="mock"` lowers `authenticity_status` to `REVIEW_REQUIRED`.

Runtime Current remains Runtime-owned. Broker positions are not copied into Current and full symbol equality is not a Current update rule. Account alignment evidence must record:

```text
runtime_owned_symbols
broker_symbols
matched_runtime_owned_symbols
runtime_owned_symbols_missing_in_broker
broker_symbols_not_runtime_owned
```

If Runtime-owned positions exist and the Broker Snapshot is fixture, mock, unknown, or account-mismatched, Safety Evidence must not be treated as `READY`.

## 25.3 Safety Action Scope Contract

Safety Decision may remain `REVIEW_REQUIRED` while still allowing specific human-review generation actions.

Runtime Safety Decision preserves legacy booleans:

```text
block_buy
block_sell
block_submit
```

It also exposes action-scope permissions:

```text
buy_inference
buy_planning
sell_hold_inference
sell_planning
buy_submit
sell_submit
auto_sell
human_review
broker_write
```

## 25.4 Human Approval / Promotion Freshness Contract

Human Review freshness and Human Approval freshness are separate.

Human Review validates whether review-only SELL/HOLD evidence may be generated. Human Approval validates whether selected review items may become a Submit Pending promotion candidate. Human Approval must not override Safety, Broker, Current, or Pending freshness.

Human Approval minimum temporal fields:

```text
business_date
approved_at
expires_at
revoked_at
source_human_review_id
source_safety_event_id
review_pending_hash
approved_item_ids
approved_review_item_hashes
policy_hash
safety_decision_id
```

Promotion validation must use a deterministic evaluation time. The following states are not valid for promotion:

```text
expires_at missing
expires_at <= evaluation_time
approved_at > evaluation_time
revoked_at present
approval_status=REVOKED
business_date mismatch
review_pending_hash mismatch
source review/event mismatch
item hash mismatch
Pending slot not EMPTY
```

Promotion Candidate freshness is not Submit freshness. A Candidate may be structurally valid while `Safety Decision` still blocks Submit. In that case the Candidate must record:

```text
promotion_status=READY_BUT_SAFETY_BLOCKED
promotion_allowed=false
apply_requested=false
apply_executed=false
```

Authoritative Submit Pending mutation requires a later explicit Apply scope. Submit itself remains a separate non-idempotent boundary.

## 25.5 Authoritative Pending Apply Candidate Freshness Contract

Authoritative Pending Apply Candidate freshness is separate from Promotion Candidate freshness and Submit freshness.

Apply review may generate:

```text
.runtime/runtime_state/authoritative_pending_apply_candidate/<business_date>/<apply_candidate_id>.json
```

This artifact is no-apply evidence. It must keep:

```text
apply_requested=false
apply_executed=false
authoritative_pending_mutated=false
submit_executed=false
broker_write_performed=false
```

Apply Candidate generation must revalidate the following against deterministic `evaluation_time`:

```text
Human Approval status / expiration / revocation
Promotion Candidate hash
Approval hash
Review Pending hash
Policy hash
Safety Decision id and action scope
Current State id and readiness
Broker Evidence id and freshness
Pending Slot EMPTY
Target Session
Approval consumption / duplicate apply absence
```

If Safety blocks Submit or Broker Write, Apply Candidate may be structurally ready but must record:

```text
apply_status=READY_BUT_SAFETY_BLOCKED
apply_allowed=false
```

Broker available quantity validation may be skipped only when Safety already blocks Apply / Submit. The skip reason must be explicit, for example:

```text
broker_quantity_validation=SKIPPED_DUE_SAFETY_APPLY_BLOCK
```

Order conditions must not be invented by Runtime. If `order_type` or `price_condition` cannot be determined from Policy / Review / Approval evidence, the Apply Candidate must record:

```text
REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY
```

Future real Apply must perform TOCTOU revalidation immediately before mutation. Any change to Approval, Safety, Policy, Current, Broker Evidence, Pending Slot, Target Session, Expiration, or Revocation invalidates the stale Apply Candidate.

## 25.6 Safety-Blocked Submit Path Freshness Contract

Safety-blocked Apply / Submit is a valid safe stop when the latest Safety Decision does not allow Submit or Broker Write.

The blocked result must record:

```text
submit_path_status=BLOCKED_BY_SAFETY
apply_status=BLOCKED_BY_SAFETY
submit_attempted=false
broker_client_called=false
broker_write_performed=false
pending_consumed=false
execution_created=false
current_mutated=false
notification_sent=false
```

Fail-closed applies when Safety evidence is missing, stale, expired, has an id mismatch, lacks the required action scope, or does not explicitly cover `sell_submit` / `broker_write` where action permissions are present. Human Review expiration also keeps Apply and Submit closed.

Retry after a Safety-blocked result requires fresh revalidation. The same Safety Decision must not be retried as if it were new evidence. If Approval expires, Current changes, Broker Evidence changes, Policy changes, Target Session changes, or Safety changes, a fresh Candidate and/or fresh Approval is required according to the changed dependency.

Order condition freshness is separate from Safety freshness. If `order_type` or `price_condition` is unresolved, Submit must remain blocked even if Safety later allows Submit.

Example for `INDIVIDUAL_CRASH / HIGH_RISK_REVIEW`:

```json
{
  "action_permissions": {
    "buy_inference": "BLOCKED",
    "buy_planning": "BLOCKED",
    "sell_hold_inference": "ALLOWED_FOR_REVIEW",
    "sell_planning": "ALLOWED_FOR_REVIEW",
    "buy_submit": "BLOCKED",
    "sell_submit": "BLOCKED",
    "auto_sell": "BLOCKED",
    "human_review": "ALLOWED",
    "broker_write": "BLOCKED"
  }
}
```

The high-risk event itself remains valid. Runtime must not change the threshold, remove the affected symbol, or force the Safety Decision to `SAFE`.

## 25.4 Formal Feature Producer Contract

Runtime Feature Refresh is the formal producer for Candidate, Opportunity, and Position Management feature artifacts.

Candidate artifact:

```text
.runtime/operations/feature_artifacts/<feature_date>/candidate_features.parquet
```

Required formal Candidate columns include:

```text
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_60d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volume_momentum_ratio_1d_20d
```

These values must be generated from market history. Acceptance must not use arbitrary zero-fill to satisfy schema.

Opportunity artifact:

```text
.runtime/operations/feature_artifacts/<feature_date>/opportunity_feature_input.parquet
```

Opportunity feature artifacts are unprefixed. Consumers may map to model-level `feature__...` names exactly once. Producer output containing `feature__...` columns is a schema violation unless a future schema version explicitly changes this rule.

PM artifact:

```text
.runtime/operations/feature_artifacts/<feature_date>/position_feature_input.parquet
```

If Runtime Current has positions, PM input must contain one row per Runtime-owned held symbol. Required PM fields:

```text
target_date
position_state_as_of
entry_date
code
broker_issue_code
holding_days
average_price
current_price
unrealized_return
quantity
feature_version
data_until
created_at
```

If Current has no positions, an empty PM artifact is allowed only when `no_position_reason` is present.

## 26. Formal Design Judgments

```text
CURRENT_FRESHNESS_CONTRACT_REDESIGN_REQUIRED
MARKET_QUOTE_EVIDENCE_CONTRACT_REQUIRED
RUNTIME_STATE_CONTRACT_REQUIRED
READY_FOR_TEMPORAL_CONTRACT_IMPLEMENTATION
```

## 27. Non-Goals

This document does not implement:

- Current schema migration
- Market Evidence producer
- Quote Evidence producer
- Current valuation refresh job
- Data Readiness refactor
- Safety temporal dependency hash
- Broker API call
- Runtime execution

Implementation must happen in later scoped phases.
