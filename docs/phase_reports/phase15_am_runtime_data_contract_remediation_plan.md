# Phase15-AM Runtime Data Contract Remediation Plan

Date: 2026-07-10

## Objective

Phase15-AM defines the remediation plan for the Runtime Data Contract gaps found in Phase15-AL.

This phase does not change Runtime implementation and does not execute Feature generation, Morning, Submit, Execution, Broker Write, orders, notification send, launchd, or Current edits.

The purpose is:

```text
Feature Refresh
↓
AI schema validation
↓
Runtime Data Readiness
↓
Morning / SELL Planning
```

を同じ契約体系で修正し、missing / mismatch / stale data が Runtime 内で hidden default 化されず、理由付き `REVIEW_REQUIRED` として止まる状態へ戻すこと。

## Final Judgment

```text
PHASE15AM_RUNTIME_DATA_CONTRACT_REMEDIATION_PLAN_COMPLETE
```

## Executive Summary

Phase15-ALで判明した主因は、Decision ChainではなくData Contractでした。

- Candidate AI: formal model required 13 columns, Runtime feature artifact had only 6 required columns.
- Opportunity AI: feature artifact prefix convention and consumer prefixing were inconsistent, and missing model features could be filled with `NaN`.
- Position Management AI: Current positions existed while PM feature input had 0 rows, and derived/defaulted holding fields were not fully evidenced.
- Feature Refresh: artifact existence was treated as readiness, but consumer-specific schema readiness was not verified.
- Runtime: Morning前にMarket / Feature / Candidate / Opportunity / PM / Safety / Pendingを統合判定するData Readiness Gateがない。

Remediation must follow this rule:

```text
missing column
↓
default / zero / false / mean / NaN
↓
continue
```

は禁止。

Missing / mismatch / stale evidence は `REVIEW_REQUIRED` に分類し、manifest / report / notification に理由を伝播させる。

## 1. Canonical Schema Matrix

| Contract | Schema Name | Schema Version | Producer | Artifact | Consumer | Required Columns | Optional Columns | Prefix Convention | Column Alias Policy | Severity |
|---|---|---|---|---|---|---|---|---|---|---|
| Candidate Feature | `runtime_v2_candidate_feature_input` | `v1` | Feature Refresh | `.runtime/operations/feature_artifacts/<date>/candidate_features.parquet` | Candidate AI | `target_date`, `code`, 13 formal Candidate model features without `feature__` prefix | eligibility / metadata columns, if explicitly documented | Artifact columns are unprefixed; Candidate model matrix adds / maps to `feature__` internally | No silent alias in Candidate adapter. Legacy alias may be normalized only inside Feature Refresh with explicit evidence. | BLOCKER |
| Candidate Decision | `runtime_v2_candidate_decision` | `v1` | Candidate AI | `.runtime/runtime_state/buy_ai/<date>/candidate_decisions.json` | Opportunity AI | `business_date`, `feature_date`, `runtime_id`, `model_version`, `generated_at`, `symbol`, `candidate_score`, `candidate_rank`, `reason`, `confidence`, schema status | diagnostic fields | JSON field names are not `feature__` prefixed | No rename without schema version bump | HIGH |
| Opportunity Feature | `runtime_v2_opportunity_feature_input` | `v1` | Feature Refresh + Candidate AI | `.runtime/operations/feature_artifacts/<date>/opportunity_feature_input.parquet` | Opportunity AI | unprefixed J-Quants feature columns needed by Opportunity model after internal prefixing; Candidate columns from Candidate Decision | explicitly nullable diagnostics only | Artifact columns are unprefixed; Opportunity consumer adds `feature__` exactly once internally | Existing `feature__...` artifact columns must be rejected or converted by Feature Refresh with explicit migration evidence, not silently double-prefixed | HIGH |
| Opportunity Ranking | `runtime_v2_opportunity_ranking` | `v1` | Opportunity AI | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json` | Morning Planning | `business_date`, `runtime_id`, `model_version`, `feature_date`, `symbol`, `opportunity_score`, `rank`, `expected_return`, `confidence`, `generated_at`, reason | model diagnostics | JSON reason fields unprefixed | No Runtime-side ranking recomputation | HIGH |
| PM Input | `runtime_v2_pm_input` | `v1` | Current Projection + Feature Refresh + Opportunity AI | `current_holdings_snapshot.csv` / PM feature input / Opportunity artifact | Position Management AI | Current positions: `symbol`, `quantity`, `average_price` or valuation source, `as_of`; PM feature rows for held positions unless Current has no positions | `holding_days`, `peak_return`, feature diagnostics if evidence-backed | No `feature__` prefix in PM input artifact unless PM model explicitly requires it | Derived/defaulted fields must be manifested; silent defaulting is forbidden for acceptance | HIGH |
| Runtime Data Readiness | `runtime_v2_data_readiness` | `v1` | Data Readiness Gate | `.runtime/runtime_state/data_readiness/<business_date>/data_readiness.json` | Morning / SELL Planning / Operator | market, candidate, opportunity, PM, current, broker, safety, pending statuses | per-component diagnostics | N/A | No hidden fallback; only `READY`, `REVIEW_REQUIRED`, `HALT` | BLOCKER |

## 2. Prefix Convention Decision

Decision:

```text
Option A
Artifact columns are canonical and unprefixed.
Consumers add or map to model-level `feature__` columns internally exactly once.
```

Reason:

- Candidate Runtime already strips `feature__` from formal model features before indexing.
- Existing Phase4 long-history builders produce the required unprefixed runtime columns.
- Artifact readability is better for Feature Refresh, schema validation, and Operator review.
- Double-prefix risk in Opportunity AI is removed by making prefixed model columns a consumer-internal matrix concern, not an artifact contract.

Consequences:

- `candidate_features.parquet` and `opportunity_feature_input.parquet` must not contain `feature__feature__...`.
- A `feature__...` column in an artifact is either a schema mismatch or an explicit Feature Refresh migration output with evidence.
- Opportunity AI must not add missing model columns as `NaN` and continue.

## 3. Feature Column Producer Matrix

| Column | Canonical Name | Required By | Expected Producer | CLI Job / Stage | Artifact | Current Finding | Required Remediation |
|---|---|---|---|---|---|---|---|
| `liquidity_avg_volume_20d` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Present in inspected candidate artifact | Lock as required schema column |
| `missing_flags_insufficient_history` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing; legacy `missing_flags_insufficient_lookback` exists elsewhere | Canonicalize to `missing_flags_insufficient_history`; any alias conversion must happen in Feature Refresh with evidence |
| `missing_flags_price` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh; do not synthesize in AI adapter |
| `missing_flags_volume` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh; do not synthesize in AI adapter |
| `price_momentum_return_20d` | same | Candidate, Opportunity | Feature Refresh | `feature_refresh` | candidate / opportunity feature input | Present | Lock |
| `price_momentum_return_5d` | same | Candidate, Opportunity | Feature Refresh | `feature_refresh` | candidate / opportunity feature input | Present | Lock |
| `price_momentum_return_60d` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh |
| `trend_close_over_ma_20d` | same | Candidate, Opportunity | Feature Refresh | `feature_refresh` | candidate / opportunity feature input | Present | Lock |
| `trend_ma_20_60_ratio` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh |
| `trend_ma_5_20_ratio` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh |
| `volatility_return_std_20d` | same | Candidate, Opportunity | Feature Refresh | `feature_refresh` | candidate / opportunity feature input | Present | Lock |
| `volume_momentum_ratio_1d_20d` | same | Candidate, Opportunity | Feature Refresh long-history builder | `feature_refresh` | candidate / opportunity feature input | Missing | Generate in Feature Refresh |
| `volume_momentum_ratio_5d` | same | Candidate, Opportunity | Feature Refresh | `feature_refresh` | candidate / opportunity feature input | Present | Lock |

Producer evidence already exists in the codebase for the missing long-history columns in `scripts/build_phase4ak_real_runtime_features.py` and `scripts/build_phase4bc_long_history_features.py`. The remediation must connect the Runtime Feature Refresh path to the canonical producer rather than allowing Runtime AI adapters to invent missing values.

## 4. Candidate Validation Plan

### Contract

The formal Candidate model feature list is the source of truth:

```text
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Runtime artifact columns are the stripped names. The Candidate adapter may map from artifact columns to model matrix columns, but must not fill or alias missing required features.

### Controlled Failure Flow

When Candidate required schema does not match:

```text
read model required columns
↓
strip model prefix for artifact schema check
↓
compare artifact columns
↓
enumerate missing / unexpected / alias-risk columns
↓
write Candidate REVIEW_REQUIRED artifact
↓
write Opportunity dependency REVIEW_REQUIRED
↓
stop before Morning Planning
```

Raw `KeyError` / uncontrolled `HALT` must be replaced by controlled `REVIEW_REQUIRED` when the issue is a data contract mismatch.

### Manifest Fields

Candidate producer and Data Readiness manifest must include:

```text
candidate_schema_status
candidate_required_columns
candidate_present_columns
candidate_missing_columns
candidate_unexpected_columns
candidate_alias_risks
candidate_schema_version
candidate_artifact_schema_version
candidate_model_version
candidate_feature_date
candidate_artifact_path
candidate_review_required
candidate_review_reason
```

### Prohibited

```text
missing column -> default
missing flag -> false
missing numeric -> 0
missing numeric -> mean
missing numeric -> NaN
legacy alias -> silent continue
```

## 5. Opportunity Validation Plan

### Prefix Contract

Opportunity artifact columns are unprefixed. Opportunity model matrix columns are prefixed internally exactly once.

Required behavior:

- If artifact has unprefixed features, map to model features.
- If artifact already has `feature__...`, classify according to schema:
  - Accept only if the artifact schema version explicitly declares prefixed columns.
  - Otherwise `REVIEW_REQUIRED`.
- If mapping would create `feature__feature__...`, stop with `REVIEW_REQUIRED`.

### Missing Feature Policy

The current hidden fallback pattern:

```text
missing model feature
↓
add column as NaN
↓
continue inference
```

must be removed from the regular Runtime acceptance path.

New contract:

```text
missing required feature
↓
Opportunity REVIEW_REQUIRED artifact
↓
Morning stops
```

Optional feature fill is allowed only if:

- the feature is explicitly listed as optional in the schema registry,
- the fill policy is explicit,
- the fill value and source are recorded in manifest,
- it does not change required model feature semantics.

### Manifest Fields

```text
opportunity_schema_status
opportunity_required_columns
opportunity_present_columns
opportunity_missing_columns
opportunity_unexpected_columns
opportunity_prefix_policy
opportunity_double_prefix_detected
opportunity_candidate_dependency_status
opportunity_model_version
opportunity_feature_date
opportunity_artifact_path
opportunity_review_required
opportunity_review_reason
```

## 6. Position Management Input Contract Plan

### Current Required Fields

PM may consume Current positions, but Current is position state only. SELL judgment must come from PM AI.

Required Current fields for held positions:

```text
symbol
quantity
as_of
average_price or market_value with quantity
source
```

Required freshness:

```text
as_of == business_date or accepted carryover policy
updated_at within accepted window
```

### PM Feature / Opportunity Requirements

When Current has positions:

- PM feature input must have rows for the held symbols, or an explicit `REVIEW_REQUIRED`.
- Opportunity dependency must be present when PM scoring uses Opportunity-derived fields.
- `position_feature_input.parquet` with 0 rows is valid only when Current has no positions and the artifact explicitly states `no_position_reason`.

### Derived / Defaulted Fields

Allowed only with evidence:

| Field | Allowed Derivation | Evidence Required | Hidden Default Allowed? |
|---|---|---|---|
| `code` | from `symbol` normalization | source symbol and normalized code | No |
| `position_size` | from Current `quantity` | Current path, quantity | No |
| `entry_price` | from `average_price` | Current path, average price | No |
| `current_price` | from `market_value / quantity` or broker/market quote | source path and formula | No |
| `holding_days` | from entry date / ledger history | source entry date / ledger event | No default `0` without evidence |
| `peak_return` | from ledger / history | source history window | No default to current return without evidence |

### Manifest Fields

```text
pm_input_schema_status
pm_current_source
pm_current_as_of
pm_feature_source
pm_feature_row_count
pm_opportunity_source
pm_derived_fields
pm_defaulted_fields
pm_missing_fields
pm_no_position_reason
pm_review_required
pm_review_reason
```

## 7. Runtime Data Readiness Gate Plan

Add an explicit Runtime Data Readiness Gate before Morning and SELL Planning.

Recommended CLI job:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job data_readiness
```

or an explicit Morning preflight stage in the regular CLI path.

The gate must not replace consumer-side validation. It is a first stop, not the only stop.

### Gate Inputs

| Area | Required Check | Failure Result |
|---|---|---|
| Market evidence | exists, fresh, business date aligned | `REVIEW_REQUIRED` |
| Feature date | target date / business date / carryover policy aligned | `REVIEW_REQUIRED` |
| Candidate schema | formal model columns match artifact schema | `REVIEW_REQUIRED` |
| Opportunity schema | candidate dependency + feature schema + prefix policy valid | `REVIEW_REQUIRED` |
| PM schema | Current positions and PM feature / Opportunity dependencies consistent | `REVIEW_REQUIRED` |
| Current freshness | Current SoT fresh or explicit accepted carryover | `REVIEW_REQUIRED` |
| Broker freshness | broker readonly snapshot fresh when required | `REVIEW_REQUIRED` |
| Safety prerequisites | Safety inputs ready or Safety already `REVIEW_REQUIRED` with reason | `REVIEW_REQUIRED` |
| Pending lifecycle | no stale approved / unconsumed Pending before Morning | `REVIEW_REQUIRED` |
| Runtime mode | Demo / Production boundary represented as Broker Environment, not Runtime branch | `REVIEW_REQUIRED` if production endpoint or launchd active for acceptance |

### Data Readiness Artifact

Fixed artifact:

```text
.runtime/runtime_state/data_readiness/<business_date>/data_readiness.json
```

Minimum fields:

```text
business_date
generated_at
runtime_mode
overall_status
market_status
candidate_schema_status
opportunity_schema_status
pm_schema_status
current_status
broker_status
safety_input_status
pending_status
missing_columns
stale_artifacts
source_paths
production_equivalent
review_required
review_reasons
next_operator_action
```

Allowed status:

```text
READY
REVIEW_REQUIRED
HALT
```

### Pending Lifecycle Separation

Data Readiness Gate must detect:

```text
stale APPROVED Pending exists
```

as `REVIEW_REQUIRED`.

However, actual Pending expire / cancel / consume remediation must be implemented in a separate phase. Do not mix Data Contract fixes with Pending lifecycle mutation.

## 8. Implementation Order

| Order | Proposed Phase | Scope | Depends On | Why |
|---:|---|---|---|---|
| 1 | Phase15-AM | Remediation Plan | Phase15-AL | Fix order and contract must be explicit before touching Runtime |
| 2 | Phase15-AN | Canonical Schema / Feature Refresh Fix | AM | Candidate and Opportunity cannot be reliable until canonical feature artifacts exist |
| 3 | Phase15-AO | Candidate / Opportunity Controlled Validation | AN | AI adapters must convert schema mismatch into evidence-backed `REVIEW_REQUIRED` |
| 4 | Phase15-AP | Position Management Input Contract | AN / AO | PM depends on Current, Opportunity, and feature inputs; derived/defaulted fields need evidence |
| 5 | Phase15-AQ | Runtime Data Readiness Gate | AN / AO / AP | Gate should aggregate validated component contracts |
| 6 | Phase15-AR | Pending Lifecycle Contract / Stale Pending Handling | AQ | Data readiness can detect stale Pending first; lifecycle mutation should be separate |
| 7 | Phase15-AS | Regression Lock | AN-AQ | Lock no hidden fallback and CLI regular path |
| 8 | Step0 / Step1 Retry | Acceptance Retry | AS | Runtime Acceptance resumes only after schema and readiness gates are proven |

This slightly expands the attachment’s minimum order by separating Regression Lock into its own phase so that data contract fixes are not accepted without durable regression coverage.

## 9. Regression Plan

### Candidate

| Test | Expected |
|---|---|
| 13 required model columns exist | Candidate inference can proceed to candidate artifact generation |
| one required column missing | Candidate `REVIEW_REQUIRED`, missing column enumerated |
| `missing_flags_insufficient_lookback` only | rename mismatch detected; no silent alias in adapter |
| model feature mismatch | no raw `KeyError`; controlled artifact / manifest |
| fake/default feature insertion | rejected |

### Opportunity

| Test | Expected |
|---|---|
| unprefixed artifact + model prefixed columns | internal mapping exactly once |
| prefixed artifact with unprefixed schema | `REVIEW_REQUIRED` |
| double-prefix risk | detected and stopped |
| required model feature missing | `REVIEW_REQUIRED`; no `NaN` continue |
| Candidate dependency missing | Opportunity dependency `REVIEW_REQUIRED`; Morning stops |

### Position Management

| Test | Expected |
|---|---|
| Current has positions + PM feature has 0 rows | `REVIEW_REQUIRED` |
| Current has no positions + explicit no-position artifact | PM no-position PASS |
| holding fields derived | manifest lists source and formula |
| stale Current | `REVIEW_REQUIRED` |
| Opportunity dependency missing when required | `REVIEW_REQUIRED` |

### Data Readiness

| Test | Expected |
|---|---|
| artifact exists + schema mismatch | `REVIEW_REQUIRED`, not READY |
| stale feature / current / broker | `REVIEW_REQUIRED` |
| stale approved Pending | `REVIEW_REQUIRED` |
| all contracts ready | `READY` |
| Demo mode | same Runtime Core path; Demo differences only in Broker Evidence |
| Production endpoint during acceptance | `REVIEW_REQUIRED` |

### Retention

Regression suite must retain:

- Phase15 Safety Runtime
- BUY AI / SELL AI Decision Chain
- Capital Deployment Policy
- Submit Guard BUY / SELL separation
- Policy Hash consistency
- Broker ReadOnly SELL evidence
- Execution / Ledger / Current projection
- Report / Notification reason propagation

## 10. Risk / Rollback Plan

| Risk | Impact | Mitigation | Rollback / Stop Rule |
|---|---|---|---|
| Feature Refresh switched to wrong builder | Candidate schema remains mismatched | Canonical schema validation and required column regression | Stop at Data Readiness `REVIEW_REQUIRED`; do not Morning |
| Prefix convention breaks Opportunity | BUY ranking unavailable | Prefix convention regression and manifest field `opportunity_prefix_policy` | Stop Opportunity and Morning with `REVIEW_REQUIRED` |
| PM rejects valid no-position day | SELL path blocked unnecessarily | Explicit no-position artifact contract | Treat as review gap; do not synthesize PM rows |
| Data Readiness Gate becomes the only validator | Consumer validation gaps reappear | Keep per-consumer validation mandatory | Regression requires both gate and consumer fail-closed behavior |
| Pending lifecycle mixed into Data Contract | Runtime state mutation risk | Separate Phase15-AR for Pending lifecycle | AM-AQ must only detect stale Pending, not mutate it |
| Operator mistakes payload/report for PASS | Hidden PASS risk | Manifest / report / notification must show readiness status and next action | No Step1 acceptance without evidence review |

## 11. Phase15 Acceptance Resume Conditions

Runtime Acceptance may return to Step0 / Step1 only after all conditions below are evidenced:

| Condition | Required Evidence |
|---|---|
| Canonical Candidate schema fixed | `candidate_features.parquet` contains all 13 required unprefixed columns |
| Candidate controlled validation | Missing required column produces Candidate `REVIEW_REQUIRED`, not raw `KeyError` |
| Opportunity prefix fixed | No double-prefix; missing required feature blocks inference |
| PM input contract fixed | Current positions and PM feature rows are consistent, or explicit no-position / review-required evidence exists |
| Data Readiness Gate present | `data_readiness.json` reports READY / REVIEW_REQUIRED / HALT with source paths |
| Pending stale detection | stale approved Pending blocks Morning as `REVIEW_REQUIRED` |
| Safety data prerequisites updated | Broker / Market / Current evidence is fresh or Safety blocks with reason |
| Regression lock complete | Candidate, Opportunity, PM, Data Readiness, retention tests pass |

Until these are satisfied:

```text
STEP1_MORNING_ACCEPTANCE_RETRY_NOT_ALLOWED
```

## Prohibited Actions Confirmation

This phase did not perform:

- Runtime implementation change
- Feature generation
- Morning execution
- Submit
- Execution
- Broker Write
- Demo order
- Production order
- Notification send
- launchd change
- Current edit
- missing feature default supplementation

## Completion String

```text
PHASE15AM_RUNTIME_DATA_CONTRACT_REMEDIATION_PLAN_COMPLETE
```
