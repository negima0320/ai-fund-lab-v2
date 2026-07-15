# Phase17-AJ BUY Opportunity to Position Management Contract Integration

## Final Judgment

`PHASE17_AJ_BUY_OPPORTUNITY_PM_CONTRACT_INTEGRATION_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T060024376440Z` was not modified, resumed, reset, rolled back, backed up, closed, or rerun.

## Scope

Phase17-AJ investigated and closed the Day2 `2026-07-07:sell_planning` blocker:

```text
pm_opportunity_contract_mismatch
```

This was implemented as a Production / Demo / Historical common Runtime contract between:

```text
BUY Opportunity Producer
  -> Runtime BUY Opportunity Ranking Artifact
  -> Position Management Consumer
```

No Historical-only, Runtime-Test-only, Phase17-only, date-specific, or symbol-specific branch was added.

## Frozen Evidence

Frozen Day2 SELL Planning stopped before PM execution:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T060024376440Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T060024376440Z/daily/2026-07-07/sell_planning/data_readiness_authority.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T060024376440Z/daily/2026-07-07/sell_planning/position_management_evidence.json`

Observed reason:

```json
{
  "status": "NOT_EXECUTED",
  "reason": "pm_opportunity_contract_mismatch"
}
```

The candidate Opportunity source existed:

```text
.runtime/runtime_state/buy_ai/2026-07-07/opportunity_rankings.json
```

Frozen artifact observations:

- `schema_version`: `runtime_v2_opportunity_ranking_v1`
- `business_date`: `2026-07-07`
- `feature_date`: `2026-07-07`
- `ranking_count`: `50`
- Row fields before AJ: `symbol`, `rank`, `opportunity_score`, `downside_risk_score`, candidate fields, and metadata.
- PM canonical fields before AJ were absent from rows: `target_date`, `code`, `expected_edge_score`, `buy_rank`.
- Held-symbol coverage was not full: `36670` and `66590` were ranked; `45640`, `67400`, and `81050` were not ranked.

## Root Cause

Classification: **Runtime Contract Bug**.

The issue was not only a field alias mismatch. The deeper mismatch was row-universe semantics:

1. Runtime BUY Opportunity emitted a ranked BUY-candidate artifact, not a full PM context artifact.
2. The JSON row shape was planner/display-oriented: `symbol`, `rank`, and `opportunity_score`.
3. PM validation expected canonical PM context fields: `target_date`, `code`, `expected_edge_score`, and `buy_rank`.
4. PM validation also treated held symbols absent from the ranked BUY artifact as missing symbols.
5. PM inference already formally handles not-ranked holdings via left join and neutral model semantics; the gate stopped before that model contract could run.

This was not a path-string-only mismatch, not a hash mismatch, and not a missing physical artifact.

## Formal Runtime Contract

BUY Opportunity artifact:

```json
{
  "schema_name": "runtime_v2_buy_opportunity_ranking",
  "schema_version": "runtime_v2_opportunity_ranking_v1",
  "artifact_role": "BUY_OPPORTUNITY_RANKING",
  "producer": "Runtime v2 BUY AI Producer",
  "row_universe": "ranked_buy_candidates_only"
}
```

Required PM-readable row fields:

- `target_date`
- `code`
- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`

Compatibility aliases accepted by the PM resolver:

- `symbol` -> `code`
- `rank` -> `buy_rank`
- `opportunity_score` -> `expected_edge_score`
- `feature_date` -> `target_date` for current legacy `runtime_v2_opportunity_ranking_v1` payloads

Symbol identity:

- Canonical PM field: `code`
- Runtime BUY alias: `symbol`
- Normalization: uppercase alphanumeric 4 or 5 characters

Temporal authority:

- Envelope `business_date` must match the PM feature date when present.
- Envelope `feature_date` must match the PM feature date.
- Row `target_date` must match the PM feature date.
- Wrong-date or future-date artifacts fail closed.

## Empty and Missing Semantics

The contract separates states that were previously collapsed into "missing":

- Artifact missing: `REVIEW_REQUIRED`.
- Artifact corrupt: `pm_opportunity_contract_mismatch`.
- Confirmed empty PASS/READY ranking: READY with `no_buy_signal_confirmed_empty`.
- No BUY signal: valid empty PM opportunity context.
- Held symbol not ranked: READY with `pm_opportunity_unranked_symbols`.
- Field missing: `pm_opportunity_contract_mismatch`.
- Unsupported schema, wrong role, producer mismatch, duplicate symbol, invalid rank, non-finite score, or date mismatch: fail closed.

Not-ranked held symbols are represented as:

```json
{
  "pm_opportunity_missing_symbol_semantics": "symbol_not_ranked_is_valid_pm_context_default"
}
```

The neutral values applied later by PM inference are model semantics for a left-joined not-ranked position, not gate-side default injection to hide missing evidence.

## Implementation

Changed producer:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`

The BUY producer now emits formal schema identity, artifact role, producer identity, and canonical PM-readable row fields. Required Opportunity output fields are converted fail-closed; missing or invalid `expected_edge_score`, `buy_rank`, or `downside_risk_score` raises instead of silently defaulting.

Changed consumer:

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`

The PM producer now resolves BUY Opportunity artifacts through a contract helper, validates schema/role/producer/date/symbol/score/rank, writes a PM opportunity context file for inference, and records explicit row-universe and unranked-symbol evidence in the PM input contract.

Added tests:

- `tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py`

The tests cover unranked holdings, no-signal empty artifacts, context mapping, unknown schema, duplicate symbol, invalid score/rank, wrong target date, and wrong artifact role.

## PM Adapter Registry

Because `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` changed, the formal PM Adapter Registry accepted-current authority was refreshed.

- Accepted set: `control.position_management.accepted_set@sha256-8c87f91911b03e75`
- Runtime adapter hash: `d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b`
- Accepted current path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Validation: PASS

Evidence:

- `reports/phase17_aj_buy_opportunity_pm_contract_integration/pm_adapter_registry_acceptance/pm_adapter_registry_acceptance.json`
- `reports/phase17_aj_buy_opportunity_pm_contract_integration/pm_adapter_registry_acceptance/protected_state_hashes.json`

Protected trading state remained unchanged:

- Current: unchanged
- Ledger: unchanged
- Pending: unchanged
- Runtime run manifests: unchanged
- Demo PM state: unchanged
- Production PM state: unchanged

## Production Impact

Production Runtime receives the same formal contract as Demo and Historical:

- BUY rankings are authoritative ranked BUY candidates only.
- PM may consume ranked BUY artifacts as opportunity context after schema and temporal validation.
- Held symbols absent from the ranked BUY artifact are not missing evidence; they are not-ranked context.
- Unknown schemas, wrong roles, producer mismatch, duplicate symbols, invalid symbols, invalid scores, invalid ranks, and date mismatches remain fail-closed.

Historical-only portions added: none.

Demo-only portions added: none.

External-effect differences remain outside this contract: broker writes, broker environment, simulation fill, external notification delivery, and Production-equivalent evaluation.

Runtime Test identity is not a trading permission, readiness permission, or contract bypass condition.

Remaining pre-production checks:

- Full 5BD Historical clean rerun after AJ.
- Live Production broker/ledger reconciliation before real-money operation.
- Operational alerting for BUY Opportunity schema rejection.

## Verification

Focused AJ regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py
7 passed
```

Broad Runtime regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_w_historical_morning_capability.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
93 passed
```

## Evidence

- `reports/phase17_aj_buy_opportunity_pm_contract_integration/contract_evidence.json`
- `reports/phase_reports/phase17_aj_buy_opportunity_pm_contract_integration.json`

