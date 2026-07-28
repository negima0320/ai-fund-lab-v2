# Phase22-AA Corporate Event Artifact Foundation

## Primary Judgment

```text
PHASE22_AA_REVIEW_REQUIRED
```

Corporate Event Artifact foundationは実装済みである。ただし、Corporate Event Authority Designで対象候補になっている earnings schedule、financial statements、standalone corporate actions のProduction共通source pathが現リポジトリ上で未実装または未取得であるため、実J-Quants sourceに対するArtifactは `producer_result_status=REVIEW_REQUIRED` とした。

Design Change Requestは不要である。Blocking gapはない。

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/03_ai_design/corporate_event_authority_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`
- `docs/phase_reports/phase22_a_market_context_artifact_foundation.md`
- `reports/phase22_a_market_context_artifact_foundation/`

## Pre-implementation Investigation

### Existing Source Inventory

確認対象:

- `src/ai_fund_lab_v2/`
- `schemas/`
- `docs/`
- `reports/`
- `.runtime/operations/jquants/`
- `tests/`

確認結果:

| Source | Current path | Status | Use in Phase22-AA |
|---|---|---|---|
| J-Quants Listed Issues | `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | AVAILABLE | listed status / delisting partial foundation |
| J-Quants Trading Calendar | `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | AVAILABLE | lineage / future business-day support |
| Earnings schedule | `.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet` | MISSING | REVIEW_REQUIRED coverage gap |
| Financial statements | `.runtime/operations/jquants/raw/jquants/statements/data.parquet` | MISSING | REVIEW_REQUIRED coverage gap |
| Standalone corporate actions | `.runtime/operations/jquants/raw/jquants/corporate_actions/data.parquet` | MISSING | REVIEW_REQUIRED coverage gap |

Listed Issues columns observed include `Date`, `Code`, `CoName`, `S17`, `S17Nm`, `S33`, `S33Nm`, `Mkt`, `MktNm`, `target_date`, `code`, `source`, `endpoint`, and `fetched_at`.

Existing Phase19 corporate action policy code records that standalone corporate action event SoT, adjustment factor dedicated SoT, code change mapping, merger mapping, and restatement lifecycle are not formally available. Phase22-AA preserves that limitation instead of converting missing source into `NO_EVENT`.

### Existing Consumer Inventory

Current direct/indirect references exist in:

- AI lifecycle corporate action policy and dataset revision materialization
- Historical listed issues snapshot support
- Runtime historical submit/fill corporate action guard using `AdjFactor`
- Runtime market status buy eligibility guard
- Feature refresh listed issues usage
- Opportunity market/sector completion using Listed Issues as sector source

Phase22-AA does not connect the new Corporate Event Artifact to Candidate, Opportunity, PM, Capital, Safety, Runtime Planning, Pending, Submit, status, or summarize.

## Strategy Event vs Runtime Corporate Action Boundary

Phase22-AA implements Strategy Corporate Event Evidence only: PIT facts about listed status / delisting-like facts and coverage gaps.

Runtime corporate action handling remains separate:

- price adjustment
- quantity adjustment
- execution guard
- submit-time guard
- broker-side accepted order handling
- ledger/current reconciliation

The new producer does not change Runtime corporate action guards and does not decide BUY/SELL/HOLD/ADD/REDUCE/EXIT.

## Implemented Files

- `src/ai_fund_lab_v2/strategy/corporate_event.py`
- `schemas/strategy/corporate_event.schema.json`
- `tests/strategy/test_phase22_aa_corporate_event.py`
- `reports/phase22_aa_corporate_event_artifact_foundation/phase22_aa_corporate_event_artifact_foundation.json`
- `reports/phase22_aa_corporate_event_artifact_foundation/phase22_aa_evidence_20260727/*.json`
- `.runtime/strategy_artifacts/corporate_event/2026-07-15/corporate_event.json`

## Schema

Schema version:

```text
corporate_event_authority.v1
```

Artifact-level status fields:

- `artifact_lifecycle_status`
- `source_authority_status`
- `producer_result_status`
- `runtime_consumer_eligibility`
- `coverage_status`

Phase22-AA fixes:

```text
artifact_lifecycle_status = DRAFT
runtime_consumer_eligibility = NOT_ELIGIBLE
```

No `authority_status: ACCEPTED` field was added.

## Event Taxonomy

Implemented taxonomy is aligned to the Corporate Event Authority Design candidates:

- `LISTING_STATUS`
- `DELISTING_PENDING`
- `SUPERVISION_STATUS`
- `LIQUIDATION_STATUS`
- `EARNINGS_ANNOUNCEMENT`
- `FORECAST_REVISION`
- `DIVIDEND_REVISION`
- `TOB`
- `MERGER_ACQUISITION`
- `STOCK_SPLIT`
- `REVERSE_SPLIT`
- `CORPORATE_ACTION`

Phase22-AA only maps available Listed Issues-derived listing/delisting-like facts. Missing earnings, financial statement, and standalone corporate action source coverage remains `REVIEW_REQUIRED`.

## Event Identity

`event_id` is deterministic SHA-256 over:

```text
security_code
event_type
announcement_date
effective_date
availability_date
source_reference
revision_id
```

Event identity is not row-order dependent and does not use current time.

## PIT Contract

The producer validates:

- `feature_date <= business_date`
- future source rows are `BLOCK`
- event `announcement_date <= business_date`
- event `availability_date <= business_date`
- `announcement_date <= effective_date` when both are present

Future effective dates are allowed only when the announcement / availability date is not future.

## Source / Hash Contract

The artifact records `source_artifacts` and `source_hashes`. Source hash mismatch is `BLOCK`, not warning.

Actual generated artifact:

```text
.runtime/strategy_artifacts/corporate_event/2026-07-15/corporate_event.json
```

Generated status:

```text
producer_result_status = REVIEW_REQUIRED
coverage_status = PARTIAL
```

## Failure Contract

Implemented:

- required source missing -> `REVIEW_REQUIRED`
- source dataset not implemented / missing optional full coverage source -> `REVIEW_REQUIRED`
- source hash mismatch -> `BLOCK`
- future leakage -> `BLOCK`
- invalid schema -> schema exception, BLOCK equivalent
- unsupported schema version -> schema exception, BLOCK equivalent
- invalid event date ordering -> schema exception or producer `BLOCK`

The producer does not return fixed `NO_EVENT` PASS when source coverage is unknown.

## Bootstrap Contract

Initial artifact absence, missing source, or source coverage gap is represented as:

```text
DRAFT
REVIEW_REQUIRED
NOT_ELIGIBLE
```

No latest artifact fallback, previous-day copy, fixture fallback, or fixed empty-events PASS fallback is implemented.

## No-event Semantics

The implementation separates:

- valid source + no event -> empty `events` can be `PASS` when coverage is explicitly scoped and available
- missing / partial source -> empty `events` means unknown and remains `REVIEW_REQUIRED`

The actual full-coverage artifact has `event_count=0` but `coverage_status=PARTIAL`, so it is not treated as a normal no-event PASS.

## Fixture Consumer

`load_corporate_event_fixture()` validates schema, reads events, rejects `BLOCK` artifacts, and rejects `NOT_ELIGIBLE` artifacts when `for_production=True`.

It does not perform Candidate filtering, BUY/SELL judgment, PM judgment, Portfolio weight judgment, or Capital allocation.

## Produced-but-not-consumed Evidence

Machine-readable evidence confirms:

- `artifact_produced=true`
- `production_consumer_connected=false`
- `runtime_consumer_eligibility=NOT_ELIGIBLE`
- `legacy_authority_active=true`
- `runtime_switch_performed=false`
- `candidate_behavior_changed=false`
- `opportunity_behavior_changed=false`
- `pm_behavior_changed=false`
- `pending_changed=false`
- `submit_changed=false`

## Regression Preservation

Phase22-AA does not modify existing Runtime, Candidate, Opportunity, PM, Capital, Pending, Submit, Ledger, Current, Registry, status, summarize, recovery, scheduler, or LaunchAgent paths.

The known Phase22-A regression remains unchanged:

```text
consumer_schema_review_required:pm
```

It occurs before Phase22-AA code is imported or consumed.

## Tests

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_aa_corporate_event.py
```

Result:

```text
5 passed
```

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_aa_corporate_event.py tests/ai_lifecycle/test_phase19_ad_u2_b_dataset_revision_materialization.py tests/ai_lifecycle/test_phase19_ad_u2_d_corporate_action_policy_approval.py
```

Result:

```text
27 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=.runtime/pycache_phase22aa python3 -m compileall -q src/ai_fund_lab_v2/strategy
```

REVIEW_REQUIRED:

```text
python3 -m pytest tests/phase12/test_market_calendar.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/artifact_registry/test_inventory_helpers.py
```

Result:

```text
10 passed, 1 failed
```

Failure reason:

```text
consumer_schema_review_required:pm
```

## Long Tests

Codex did not execute long Historical tests:

- 5BD
- 20BD
- 200BD
- 1-year
- 3-year
- long runtime smoke

## Design Freeze Compliance

No changes were made to Component ownership, Corporate Event Authority responsibility, Authority owner, Producer / Consumer ownership, Runtime boundary, Safety boundary, Migration order, Bootstrap taxonomy, Runtime switch sequence, Retirement sequence, Rollback principle, Zombie Detection, or Safe Delete Gate.

## Legacy Preservation

Legacy Runtime Authority remains active. Old consumers, old source paths, runtime_test lifecycle, historical adapters, status/summarize readers, CLI, scheduler, recovery paths, Pending, Submit, Ledger, Current, Accepted Generation history, and Artifact Registry history were not removed or revoked.

## Known Gaps

- Earnings schedule source authority remains unavailable.
- Earnings release time precision remains unavailable.
- Financial statements source path is not implemented as a Corporate Event source.
- Standalone corporate actions source path is not implemented.
- TOB / merger event coverage remains unavailable.
- Phase22-A known regression remains unchanged.

## Blocking Gaps

None.

## Next Gate

```text
Phase22-B entry ready: YES
Runtime switch ready: NO
Legacy retirement ready: NO
```

Phase22-B may proceed only as Candidate / Opportunity Compatibility against DRAFT / NOT_ELIGIBLE Market Context and Corporate Event foundations. Runtime switch remains prohibited.

