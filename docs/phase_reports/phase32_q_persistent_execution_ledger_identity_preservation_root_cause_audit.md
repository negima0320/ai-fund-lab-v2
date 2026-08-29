# Phase32-Q Persistent Execution Ledger Identity Preservation Root-Cause Audit

## Executive Summary

Phase32-Q found a mandatory actual-path provenance defect: the Post-L run preserves PM decision and campaign identity through the daily execution artifacts, but the persistent execution ledger drops that identity before Phase32-L's strict prior-exit bridge reads it.

For the primary trace, 83060 on 2022-10-04:

- PM produced a detailed EXIT decision: `pm-2022-10-04-83060-exit`, reason `trend_and_opportunity_broken`, campaign `pc-37f3e1e990212b6a-83060-0001`.
- Runtime planning carried `source_pm_decision_id = pm-2022-10-04-83060-exit`.
- Daily execution artifacts carried `source_decision_id`, `source_decision_type = EXIT`, and `position_campaign_id`.
- `.runtime/persistent_ledger/executions.jsonl` carried the accounting execution row, order hash, execution hash, side, symbol, quantity, price/cash effect, and dedupe key, but did not carry `source_decision_id`, `source_pm_decision_id`, `source_decision_type`, or `position_campaign_id`.

The exact observed drop boundary for the historical actual path is the projection from normalized broker/order evidence into `LedgerExecutionRecord` in `runtime_v2/execution/readonly_pipeline.py::_execution_equivalent_records`. The broader schema boundary is `runtime_v2/ledger/models.py::LedgerExecutionRecord`, which has no fields for source decision or campaign identity. The generic broker detail execution projection in `runtime_v2/execution/ledger_projection.py::project_execution_to_ledger_record` has the same limitation, so this is not just a 650BD historical artifact quirk.

Phase32-L did not choose a wrong canonical source for execution-proven prior closes. It chose the persistent execution ledger, which architecture treats as execution history/current state authority. The defect is that the ledger execution schema/writer path is accounting-preserving but not provenance-preserving enough for Phase32-L's strict PM reason join.

Recommended action: do not accept the current 650BD run as Phase32-L semantic validation. Implement a narrow, additive provenance-preservation repair at the execution ledger boundary, keep execution dedupe keys unchanged, add actual-pipeline regression tests, then restart fresh validation.

## Run Identity

| Role | Run |
| --- | --- |
| Post-L current run | `runtime-test-historical-extended-smoke-20260827T005331941551Z` |
| Primary date | `2022-10-04` |
| Primary symbol | `83060` |
| Audit mode | READ-ONLY artifact/code audit, no runtime mutation |

## 83060 End-to-End Lineage

| Stage | Artifact / Source | Observed Identity |
| --- | --- | --- |
| PM decision | `daily/2022-10-04/position_management/pm_decisions.json` | `pm_decision_id = pm-2022-10-04-83060-exit`; `decision_type = EXIT`; `decision_reason = trend_and_opportunity_broken`; `reason_codes = ["trend_and_opportunity_broken"]`; `position_campaign_id = pc-37f3e1e990212b6a-83060-0001` |
| Runtime planning | `daily/2022-10-04/strategy/runtime_planning.json` | 83060 plan has `source_pm_decision_id = pm-2022-10-04-83060-exit`; SELL/EXIT sizing reason codes are present |
| Daily fill | `daily/2022-10-04/execution/fills.json` | `source_decision_id = pm-2022-10-04-83060-exit`; `source_decision_type = EXIT`; `position_campaign_id = pc-37f3e1e990212b6a-83060-0001`; `side = SELL`; `quantity = 100.0`; `execution_id = execution-equivalent:sha256:d384bd...` |
| Realized slice | `daily/2022-10-04/execution/realized_slices.json` | Same PM decision and campaign identity preserved |
| Persistent execution ledger | `.runtime/persistent_ledger/executions.jsonl` | 83060 SELL row exists with `business_date = 2022-10-04`, `side = SELL`, `quantity = 100.0`, `cash_effect = 66120.0`, same order/execution hash, but no source decision/campaign identity fields |
| Phase32-L bridge reader | `strategy/shadow_runtime.py::_supply_prior_exit_state` | Reads `.runtime/persistent_ledger/executions.jsonl` and attempts strict join on `execution.source_decision_id == pm.pm_decision_id/decision_id` |
| Re-entry context | Later 83060 semantic path | Join cannot match; bridge falls back to bare `EXIT` and `EXECUTION_ROW_FALLBACK`, leaving previous exit class generic |

## Identity Field Matrix

| Field | PM Decision | Runtime Planning | Daily Fill | Realized Slice | Persistent Execution Ledger |
| --- | --- | --- | --- | --- | --- |
| `pm_decision_id` | YES: `pm-2022-10-04-83060-exit` | via `source_pm_decision_id` | via `source_decision_id` | via `source_decision_id` | NO |
| `source_decision_id` | N/A | PARTIAL alias source PM id | YES | YES | NO |
| `source_pm_decision_id` | N/A | YES | NO alias not needed | NO alias not needed | NO |
| `source_decision_type` | `decision_type = EXIT` | implied by plan reason | YES: `EXIT` | YES: `EXIT` | NO |
| `position_campaign_id` | YES | not present in extracted plan row | YES | YES | NO |
| `symbol` | YES | YES as `security_code` | YES | YES | YES |
| `business_date` | YES | plan date | YES | YES | YES |
| `side` | N/A | SELL plan | YES | slice close direction implied | YES |
| `quantity` | N/A | planned quantity | YES | realized quantity context | YES |
| `order_id` / `execution_id` | N/A | downstream | YES | downstream | YES |

Ledger-wide text scan found zero occurrences of `source_decision_id`, `source_pm_decision_id`, and `position_campaign_id` in `.runtime/persistent_ledger/executions.jsonl`.

## Exact Drop Boundary

The historical actual-path drop occurs here:

1. `run_execution_readonly_pipeline` creates `equivalent_executions = _execution_equivalent_records(...)`.
2. `_execution_equivalent_records` iterates filled orders and constructs `LedgerExecutionRecord(...)`.
3. The constructed `LedgerExecutionRecord` includes accounting fields and evidence refs, but no source decision or campaign identity fields.
4. `_append_ledger_records(.../executions.jsonl, ledger_executions)` serializes the dataclass with `ledger_record_to_payload(record)`.
5. `ledger_record_to_payload` uses `dataclasses.asdict(record)`, so it serializes only fields that survived the dataclass boundary.

Therefore the writer append function is not independently filtering the fields. The loss happens before append: the `LedgerExecutionRecord` schema and projection do not support the fields.

The broader path has the same problem:

- `ledger_projection.py::project_execution_to_ledger_record` converts `BrokerExecutionSnapshot` to `LedgerExecutionRecord` without source decision/campaign fields.
- `broker_readonly/models.py::BrokerExecutionSnapshot` also has no source decision/campaign fields.
- `broker_readonly/normalizer.py::_normalize_execution` only preserves execution/order refs, symbol, side, quantity, price, and timestamp.

For the concrete 83060 historical trace, daily artifacts prove the identity existed outside the ledger. The persistent ledger lost it at the ledger execution model/projection boundary.

## Schema Audit

`LedgerOrderRecord` supports partial planning provenance:

- `pending_plan_id`
- `pending_item_id`
- `source_decision_type`
- `source_pm_decision_id`
- `source_pm_business_date`
- `source_position_symbol`
- `strategy_authority_lineage`
- `strategy_authority_lineage_hash`

`LedgerExecutionRecord` does not support:

- `source_decision_id`
- `source_pm_decision_id`
- `source_decision_type`
- `pm_decision_id`
- `position_campaign_id`
- `campaign_id`

Result: execution ledger schema support is PARTIAL at the ledger family level and NO at the execution-record level.

## Writer / Reader Inventory

Writer path:

- `runtime_v2/execution/readonly_pipeline.py::run_execution_readonly_pipeline`
- `runtime_v2/execution/readonly_pipeline.py::_execution_equivalent_records`
- `runtime_v2/execution/ledger_projection.py::project_execution_to_ledger_record`
- `runtime_v2/ledger/writer.py::ledger_record_to_payload`
- `runtime_v2/execution/readonly_pipeline.py::_append_ledger_records`

Readers/consumers observed or architecturally declared:

- `strategy/shadow_runtime.py::_supply_prior_exit_state`, Phase32-L strict prior-exit materialization.
- Asset/current projection after execution commit.
- Reconciliation Runtime, Report Builder, and Audit Runtime per Runtime v2 architecture.
- Campaign/current-state reconstruction paths that depend on persistent execution history.

The important reader for Phase32-Q is `_supply_prior_exit_state`. It explicitly documents the join identity as:

`execution.source_decision_id == pm.pm_decision_id/decision_id with symbol/date/campaign validation`

But the execution ledger never supplies `source_decision_id`, so `pm_exit_reason_matched_close_count` remains zero.

## Authority Semantic

Persistent execution ledger authority is MIXED.

It is authoritative for minimal execution/accounting state: date, symbol, side, quantity, price, cash effect, execution id, order id, dedupe key, and evidence refs.

It is not currently provenance-preserving authority for strategy/PM identity. The order ledger has partial strategy provenance, but execution ledger rows do not preserve the source decision or position campaign identity needed to bridge executed closes back to PM reasons.

## Alternative Canonical Source Comparison

| Source | Identity Availability | Strength | Weakness |
| --- | --- | --- | --- |
| Persistent execution ledger | Missing source PM/campaign identity | Canonical current execution history; resume/recovery friendly | Current schema loses Phase32-L join fields |
| Daily `execution/fills.json` | Present for 83060 | Execution-proven and run-scoped; best existing positive evidence | Not fixed-path current SoT; less suitable for production resume/current recovery unless promoted |
| Daily `execution/realized_slices.json` | Present for 83060 | Strong close attribution evidence | Derived run artifact; not the persistent execution ledger |
| Runtime planning | `source_pm_decision_id` present | Good source of intent | Not execution-proven by itself |
| Orders ledger | Partial strategy lineage | Persistent and deduped | Execution rows do not carry the identity forward; order record model projection currently does not populate the dedicated PM fields from observed planning identity |

Conclusion: an alternative canonical source exists only PARTIAL. Daily fill/realized-slice artifacts prove the data exists and could support a narrow bridge, but the correct long-term source for executed prior-close state remains the persistent execution ledger.

## Partial REDUCE / Final EXIT Analysis

Phase32-L's resolver already uses quantity state and only records prior-exit state when a SELL fully closes a position. The existing tests include partial REDUCE and final close cases using ledger rows that contain source identity.

A safe repair is possible if each execution row preserves its own source decision and campaign identity while leaving the close-state algorithm unchanged:

- partial REDUCE rows remain intermediate unless position quantity reaches zero;
- final close row supplies the PM identity used for strict reason matching;
- campaign validation remains exact when both PM evidence and execution row provide campaign ids;
- dedupe keys remain based on existing execution/order refs, not on new provenance fields.

## Idempotency / Recovery Impact

Idempotency risk is LOW for a narrow additive repair because current execution dedupe uses stable execution/order hashes such as `runtime_v2_execution_equivalent:{order.order_ref_hash}`. Adding optional provenance fields should not change dedupe behavior if those fields are not included in dedupe keys.

Recovery impact is positive: current/future runs would be able to reconstruct prior-close semantic context from the fixed persistent path rather than needing run-scoped daily artifacts.

Backward compatibility requirement: readers must tolerate legacy ledger rows without the new optional fields and continue to use the existing `EXECUTION_ROW_FALLBACK` behavior.

## Mode Parity

Mode parity is PARTIAL.

The same high-level read-only execution pipeline writes persistent ledger executions across historical/demo/production-like modes, and the shared `LedgerExecutionRecord` schema lacks the provenance fields everywhere.

However, the input paths differ:

- historical uses execution-equivalent records from orders and positions;
- demo/production can include broker detail executions projected through `project_execution_to_ledger_record`;
- generic broker execution snapshots also lack the identity fields at normalizer/model level.

So the defect class is cross-mode at schema/projection level, while the concrete observed 83060 boundary is the historical equivalent-execution projection.

## Broader Impact

Broader identity loss is material.

Observed direct impact:

- Phase32-L strict prior PM reason matching cannot materialize from the actual persistent execution ledger.
- Later semantic REENTRY context remains generic despite PM detailed EXIT evidence existing in run artifacts.

Likely adjacent impact:

- campaign-aware close/re-entry attribution becomes weaker after persistent-ledger recovery;
- BUY/ADD lifecycle distinctions are more fragile when execution rows cannot retain originating strategy authority;
- report/audit/reconcile consumers can see execution accounting but not the strategy decision that caused the execution.

This does not imply PnL/equity/holding calculations are wrong. It means semantic/provenance reconstruction is underpowered.

## Why Existing Tests Missed It

The Phase32-L unit tests validated the bridge with synthetic ledger execution rows that already contained `source_decision_id` and `position_campaign_id`. That proves the bridge logic works if the ledger has identity, but it does not prove the production writer preserves identity.

Missing coverage:

- actual read-only execution pipeline test from PM EXIT -> runtime planning -> fills -> persistent execution ledger;
- assertion that `source_decision_id` survives into `.runtime/persistent_ledger/executions.jsonl`;
- assertion that `position_campaign_id` survives into execution ledger rows;
- assertion that daily fill identity and persistent ledger identity agree;
- broker detail execution projection provenance preservation test;
- historical equivalent execution projection provenance preservation test;
- resume/recovery test that uses only persistent ledger and PM artifacts;
- negative legacy-row fallback test for rows without optional identity fields after schema expansion.

## Repair Option Comparison

| Option | Description | Pros | Cons | Judgment |
| --- | --- | --- | --- | --- |
| A | Add optional provenance fields to execution ledger model/projections and persist them from order/fill lineage | Keeps persistent ledger as canonical execution history; resume-safe; narrow and additive | Requires careful mapping from planning/order lineage to execution rows | Preferred |
| B | Change Phase32-L bridge to read daily fills/realized slices as canonical close source | Uses already-present artifacts for historical run | Run-scoped, weaker for current recovery, less aligned with architecture | Fallback only |
| C | Introduce a new execution provenance ledger/index | Clean separation of accounting and provenance | Larger schema/reader surface, more migration burden | Too broad for immediate repair |

Preferred repair option: A.

Minimal repair boundary:

- Add optional fields to `LedgerExecutionRecord`: `source_decision_id`, `source_pm_decision_id`, `source_decision_type`, `source_pm_business_date`, `source_position_symbol`, `position_campaign_id`.
- Preserve those fields in historical `_execution_equivalent_records` from filled order / strategy authority lineage / source plan identity.
- Preserve equivalent fields in broker detail execution projection where the broker execution/order payload has or can join them.
- Keep existing dedupe keys unchanged.
- Keep Phase32-L bridge fallback behavior for legacy rows.
- Add actual-pipeline regression tests before accepting semantic validation.

## Defect Classification

Primary defect class:

`PERSISTENT_EXECUTION_LEDGER_PROVENANCE_SCHEMA_AND_PROJECTION_FIELD_DROP`

Secondary classes:

- `LEDGER_EXECUTION_RECORD_SCHEMA_GAP`
- `HISTORICAL_EXECUTION_EQUIVALENT_PROJECTION_OMISSION`
- `BROKER_DETAIL_EXECUTION_PROJECTION_PARITY_GAP`
- `PHASE32_L_ACTUAL_PATH_SOURCE_CONTRACT_MISMATCH`

This is not primarily a Phase32-L semantic algorithm bug. The bridge's selected source is architecturally reasonable, but the selected source lacks the identity fields that Phase32-L's strict join requires.

## Repair Readiness

Implementation readiness is YES. The exact boundary, fields, source artifacts, expected behavior, and regression-test shape are known. The repair should still be performed as a narrow production change in a separate phase, not during this audit.

Current 650BD run recommendation: do not continue using the current run as Phase32-L acceptance evidence. It may continue only if the purpose is unrelated observation, but it should not be treated as resolving prior-exit semantic validation.

## Final Judgments

PHASE32_Q_IDENTITY_DROP_EXACT_BOUNDARY = `runtime_v2/execution/readonly_pipeline.py::_execution_equivalent_records` constructs `LedgerExecutionRecord` without source decision/campaign fields; broader schema boundary is `runtime_v2/ledger/models.py::LedgerExecutionRecord`

PHASE32_Q_SOURCE_DECISION_ID_DROPPED = YES

PHASE32_Q_POSITION_CAMPAIGN_ID_DROPPED = YES

PHASE32_Q_LEDGER_SCHEMA_SUPPORTS_IDENTITY = PARTIAL

PHASE32_Q_LEDGER_WRITER_DEFECT = YES

PHASE32_Q_PHASE32_L_WRONG_SOURCE_SELECTION = NO

PHASE32_Q_ALTERNATIVE_CANONICAL_SOURCE_EXISTS = PARTIAL

PHASE32_Q_EXECUTION_LEDGER_AUTHORITY_SEMANTIC = MIXED

PHASE32_Q_PARTIAL_REDUCE_SAFE_REPAIR_POSSIBLE = YES

PHASE32_Q_IDEMPOTENCY_RISK = LOW

PHASE32_Q_MODE_PARITY = PARTIAL

PHASE32_Q_BROADER_IDENTITY_LOSS_MATERIAL = YES

PHASE32_Q_PRIMARY_DEFECT_CLASS = PERSISTENT_EXECUTION_LEDGER_PROVENANCE_SCHEMA_AND_PROJECTION_FIELD_DROP

PHASE32_Q_MANDATORY_DEFECT = YES

PHASE32_Q_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_Q_IMPLEMENTATION_READY = YES

PHASE32_Q_PREFERRED_REPAIR_OPTION = A

PHASE32_Q_MINIMAL_REPAIR_BOUNDARY = additive optional provenance fields on persistent execution ledger records plus historical/detail execution projections, with unchanged dedupe keys and legacy fallback readers

PHASE32_Q_NEXT_STEP = implement narrow execution-ledger provenance preservation repair with actual-pipeline regression tests, then restart fresh semantic validation
