# Phase17-BC Clean Baseline Re-entry Preparation

## Verdict

`PHASE17_BC_CLEAN_BASELINE_REENTRY_PREPARATION_ACCEPTED`

This is a read-only preparation verdict. It is not a baseline restoration verdict, plan verdict, run verdict, or Historical 5BD smoke completion verdict.

## Read-only Scope

Frozen run remained unchanged:

- `runtime-test-historical-smoke-20260715T092642592380Z`

No `runtime_test.py run/resume/rollback/reset/backup/close` command was executed. No Pending, Ledger, Current, broker write, Demo/Production order, external notification, J-Quants fetch, or AI retraining action was performed.

## Git State

- `git rev-parse HEAD`: `31aad0d859e58503dbfe7ebc375836c2e7715941`
- `git diff --check`: PASS
- Working tree contains the expected BA/BB code, test, and phase report changes.
- No secret/raw request/raw response file was identified in the inspected Runtime Test backup candidate.

## Current Runtime State

Current `.runtime` is not a clean baseline for `2026-07-06`:

- Runtime State: `business_date=2026-07-07`
- Persistent Ledger: `business_date=2026-07-06`, positions `5`
- Pending: `state=EMPTY`, `active_pending=false`, `target_session_date=2026-07-07`
- Pending safety context contains foreign/current frozen run identity:
  - `runtime_test_run_id=runtime-test-historical-smoke-20260715T092642592380Z`
  - `safety_business_date=2026-07-07`

Starting a new plan or run from this state would carry Day2/Frozen Run contamination.

## Backup Inventory

Read-only command used:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py list-backups --json
```

Inventory returned 22 backups. Candidate verification focused on the known clean candidate and known incompatible candidates.

## Candidate Classification

### Accepted Candidate

`backup-historical-smoke-20260715T031700494429Z`

- `clean_baseline=true`
- `restorable_for_requested_start_date=true`
- Runtime State business date: empty
- Ledger business date: empty
- Pending: `EMPTY`, `active_pending=false`
- Pending target session date: empty
- Pending runtime-test run id: empty
- Pending safety business date: empty
- Safety artifact business date: empty
- Current Valuation files: none
- Manifest schema: `runtime_test_backup_manifest_v1`
- Scope: `resettable_trading_state_only`
- Bundle hash: `64aed3608dcadd21f2e73acd1c4bcee19766dca0429560ae53badd9e9990e4c4`

Manifest target hashes matched the saved files inspected for core state:

- `persistent_ledger/state.json`: `a0db4fcb099c8b27bf4563353acb79417dfd244ca89bf8ea5284bc61c9d7c8ac`
- `pending_order_plan/pending_order_plan.json`: `10f395481b3cbd367483ec651e35bf15048ed685cd20f563ae75ff1cd9745b47`
- `runtime_state/current_state.json`: `6948d75a38b76f915daeac5431009f02624d665a56ed8f57276d9ded2dec015c`
- empty ledger JSONL files: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

The manifest does not restore Phase9 artifacts as Current authority. It explicitly excludes foundation and data sources such as `artifact_registry`, `artifacts`, `operations/jquants`, `phase9/canonical_data`, `data/raw`, `candidate_ai`, `opportunity_ai`, and `configs`.

### Rejected Candidates

`backup-historical-smoke-20260715T055933965598Z`

- rejected reasons:
  - `current_state_date_future`
  - `pending_target_date_future`
- contains Runtime State business date `2026-07-07`
- contains Pending target session date `2026-07-07`

`backup-historical-smoke-20260715T062952991771Z`

- rejected reasons:
  - `current_state_date_future`
  - `pending_foreign_runtime_test_run_id`
  - `pending_safety_business_date_future`
  - `pending_target_date_future`
- contains foreign run id `runtime-test-historical-smoke-20260715T060024376440Z`

`backup-historical-smoke-20260715T071237940864Z`

- rejected reasons:
  - `current_state_date_future`
  - `pending_foreign_runtime_test_run_id`
  - `pending_safety_business_date_future`
  - `pending_target_date_future`
- contains foreign run id `runtime-test-historical-smoke-20260715T063047874126Z`

## Rollback vs Reset

Rollback is preferred.

Why:

- A validated clean backup exists.
- The backup classifier returns `clean_baseline=true`.
- Manifest and saved core state file hashes are consistent.
- Start-date compatibility for `2026-07-06` is explicit.
- Restore scope is `resettable_trading_state_only`.
- It preserves reproducibility better than generating a new reset state.
- It aligns with Phase17-AL's clean baseline candidate evidence.

Reset is not recommended as the first operator action for BC:

- Reset can generate a confirmed-empty baseline, but it is unnecessary while a verified backup exists.
- Choosing reset would introduce a new baseline artifact rather than restoring the already-classified clean baseline.

## Recommended Operator Sequence

Run exactly this rollback command after user approval:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py rollback \
  --profile historical-smoke \
  --backup-id backup-historical-smoke-20260715T031700494429Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Then verify:

```bash
python3 -m json.tool .runtime/runtime_state/current_state.json
python3 -m json.tool .runtime/pending_order_plan/pending_order_plan.json
python3 -m json.tool .runtime/persistent_ledger/state.json
```

Optional additional checks:

```bash
test ! -e .runtime/runtime_state/safety/latest_safety_decision.json
test ! -d .runtime/runtime_state/current_valuation
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --start-date 2026-07-06 --business-days 5 --write-evidence --json
```

Only after rollback and state verification should Phase17-BD proceed to new plan and new run. Do not resume the Frozen Run.

## Frozen Hashes

- `run_state.json`: `f34453ed80d0958d2d1bc6b7c6adc13faa93621726a623c73f536e4fab4d9014`
- Frozen Day2 submit Data Readiness evidence: `2ac8f2114bcc9f7cf6349c9095146025436ec20636b0918d782fcd4e7f135246`
- Current `.runtime/persistent_ledger/state.json`: `6ff00996e2b78be4efe7d90b339a36c4102d6a2d055db32abdc258e6bc777481`
- Current `.runtime/pending_order_plan/pending_order_plan.json`: `e92aa0a544b30b8bf1f9228ace7278ba52b7baac9f546407bb9578c26a987355`

## Phase17-BD Entry Conditions

Proceed to Phase17-BD only after:

1. The rollback command above is executed by the operator.
2. Current, Pending, Ledger, Safety, and Current Valuation checks confirm clean baseline.
3. A new plan is created.
4. `baseline_compatibility_status=PASS` is confirmed.
5. A new Run ID is issued for the 5BD Historical Smoke.
