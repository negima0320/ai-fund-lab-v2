# Phase16-P Read-only Artifact Inventory and Logical Registration Preparation

## Summary

- Prefix: `Phase16-P`
- Work: `Read-only Artifact Inventory and Logical Registration Preparation`
- Judgment: `PHASE16_P_ARTIFACT_INVENTORY_ACCEPTED_WITH_GAPS`
- Scope: existing artifact inventory, logical ID candidates, hash/schema inventory, draft Registry event candidates, artifact set manifest candidates, read-only consumer compatibility validation.
- Runtime behavior change: none.
- Formal Registry path creation: none.

## Outputs

- `reports/phase16_registry_inventory/artifact_inventory.json`
- `reports/phase16_registry_inventory/draft_registry_events.jsonl`
- `reports/phase16_registry_inventory/draft_registry_index.json`
- `reports/phase16_registry_inventory/candidate_artifact_set_manifest_candidate.json`
- `reports/phase16_registry_inventory/opportunity_artifact_set_manifest_candidate.json`
- `reports/phase16_registry_inventory/pm_artifact_set_manifest_candidate.json`
- `reports/phase16_registry_inventory/capital_allocation_policy_manifest_candidate.json`
- `reports/phase16_registry_inventory/inventory_audit.md`
- `reports/phase_reports/phase16_p_read_only_artifact_inventory_and_logical_registration.json`

## Evidence Summary

- Inventoried artifacts: 32
- Draft Registry event candidates: 28
- Event statuses: `VALIDATED` 16, `DRAFT` 12
- `ACCEPTED` event count: 0
- Artifact statuses: `VALIDATED` 16, `DRAFT` 12, `NOT_APPLICABLE` 4
- Protected before/after hash comparisons: 14 `UNCHANGED`
- Formal Registry paths: `.runtime/artifact_registry/` absent, `.runtime/artifacts/` absent

## Artifact Categories

- Raw / Canonical / Calendar / Listed / Corporate Action data artifacts were inventoried.
- Candidate, Opportunity, Position Management, and Capital Allocation feature artifacts were inventoried from the current feature artifact date.
- Candidate model, manifest, training evidence, and validation evidence were inventoried.
- Opportunity model, preferred Phase5-P metrics, legacy Phase5-E fallback metrics, training evidence, and validation evidence were inventoried.
- Position Management code-policy and Runtime adapter artifacts were inventoried as code-policy candidates.
- Runtime authority states for Current, Ledger, Pending, and Runtime State were inventoried only as boundaries and were excluded from draft Registry events.

## Artifact Set Manifest Candidates

- Candidate artifact set candidate: `VALIDATED`
- Opportunity artifact set candidate: `VALIDATED`
- Position Management artifact set candidate: `VALIDATED`
- Capital Allocation policy manifest candidate: `VALIDATED`

All manifest candidates remain candidates. They do not register artifacts, do not write formal Registry state, and do not mark anything as `ACCEPTED`.

## Read-only Guarantees

- Runtime Contract: unchanged
- Runtime Authority: unchanged
- Current / Ledger / Pending: unchanged
- Runtime Mainline: unchanged
- AI model files: unchanged
- Feature schema and feature calculation: unchanged
- Consumer paths: unchanged
- CLI defaults and config defaults: unchanged
- Opportunity fallback behavior: unchanged
- Capital Allocation behavior: unchanged

The inventory tool writes only under `reports/phase16_registry_inventory/`. Active `.runtime` was read as evidence only.

## Consumer Compatibility Findings

- Candidate Model Loader still uses the current physical model and manifest paths.
- Opportunity Model Loader still uses the current Phase5-P model path.
- Opportunity Metrics Loader still has the existing Phase5-P preferred metrics and Phase5-E fallback relationship; fallback removal is not part of this phase.
- Position Management remains code-policy based and does not introduce a model artifact requirement.
- Feature consumers still read existing feature artifact paths.
- Runtime CLI and reporting paths remain unchanged.
- Future Registry adoption would require logical ID resolution and consumer migration in a later phase.

## Gaps

- `data.corporate_actions.canonical`: standalone path `.runtime/data/raw/jquants/corporate_actions/data.parquet` was not found, and producer remains unknown.
- `decision.candidate.daily`: expected Runtime buy AI decision path `.runtime/runtime_state/buy_ai/2026-07-10/candidate_decisions.json` was not found.
- `decision.opportunity.daily`: expected Runtime buy AI decision path `.runtime/runtime_state/buy_ai/2026-07-10/opportunity_rankings.json` was not found.
- Artifact Registry production path and Runtime startup integration are intentionally not implemented in this phase.

## Regression Risk

Low. The change is an independent read-only inventory utility plus generated reports. It does not import into the Runtime mainline, change Runtime contracts, mutate `.runtime`, or alter AI / feature / planning behavior.

## Validation

- `python3 -m pytest -q tests/artifact_registry/test_inventory_helpers.py`: passed, 3 tests.
- JSON and JSONL outputs under `reports/phase16_registry_inventory/`: parsed successfully.
- Before/after hash audit in `inventory_audit.md`: all protected paths remained `UNCHANGED`.

## Next Prefix

`Phase16-Q` should be review/planning only unless the user explicitly authorizes implementation of Registry production paths or consumer migration. Formal Registry creation, acceptance status promotion, Runtime integration, and path migration remain out of scope.
