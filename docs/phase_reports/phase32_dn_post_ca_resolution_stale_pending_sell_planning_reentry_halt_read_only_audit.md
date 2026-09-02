# Phase32-DN Post-CA-Resolution Stale Pending / Sell-Planning Re-entry HALT READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Current continuation boundary: `2023-10-11:sell_planning`
- Current source commit: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- Execution mode: READ-ONLY audit plus this report only
- Resume / recover / replay / fresh-run executed in DN: NO
- Code / config / Pending / Ledger / Runtime state mutation in DN: NO

Mandatory references read:

- `docs/phase_reports/phase32_dj_20231011_sell_planning_halt_root_cause_read_only_audit.md`
- `docs/phase_reports/phase32_dk_50280_corporate_action_canonical_resolution_safe_continuation_read_only_audit.md`
- `docs/phase_reports/phase32_dl_corporate_action_operator_resolution_sell_campaign_identity_production_repair.md`
- `docs/phase_reports/phase32_dm_50280_adjusted_price_quantity_basis_canonical_resolution_read_only_audit.md`
- `docs/03_operations/runtime_test_command_guide.md`
- current Pending, CA authority, sell-planning evidence, review-scope code, historical safety code, CA adjustment code, and stale Pending recovery code

## CA Authority Revalidation

`50280_CA_AUTHORITY_POST_RESOLUTION_STATUS`: PASS.

Current artifact:

- path: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`
- schema: `runtime_v2_corporate_action_adjustment_authority_v1`
- status: `PASS`
- business date: `2023-10-11`
- symbol: `50280`
- event status: `PASS`
- event type: `STOCK_SPLIT`
- event type authority: `operator_reviewed_pit_corporate_action_resolution`
- effective date: `2023-10-11`
- adjustment factor: `0.3333333333333333`
- PIT validation: `PASS`
- future data used: `false`
- pre-adjustment quantity: `100.0`
- post-adjustment quantity: `100.0`
- current quantity: `100.0`
- broker available quantity: `100.0`
- pending quantity: `100.0`
- submit quantity: `100.0`
- already applied status: `CONFIRMED`
- ledger/current/pending adjustment statuses: `PASS`
- quantity reconciliation status: `PASS`
- price reconciliation status: `PASS`
- source artifact hash: `7d0bd0659b76385687e5664d553ae789b606ec4425ddac9debb6a41f0c3d2a7c`
- current resolved authority hash: `fd17c5723e569e84b4cdd7912a9c712c7f6334d1d05e6615a396828bb54609f4`
- operator audit id: `phase32-dm-50280-stock-split-review`
- reviewer: `negishi`

A read-only evaluator check using the same relative Runtime source path returns:

- `corporate_action_adjustment_authority_status = PASS`
- `corporate_action_adjustment_authority_reason = corporate_action_adjustment_authority_confirmed`
- `corporate_action_event_type = STOCK_SPLIT`
- `quantity_reconciliation_status = PASS`
- `price_reconciliation_status = PASS`
- `reason_codes = []`

Important path note: passing the event source as an absolute path causes a string-level `corporate_action_source_artifact_mismatch` against the authority's relative source path. The actual Runtime evidence and stored CA authority are relative-path bound, and that relative-path evaluation passes.

## Current Pending State

`CURRENT_PENDING_STATE`: stale same-day `REVIEW_REQUIRED` Pending.

Current active Pending:

- path: `.runtime/pending_order_plan/pending_order_plan.json`
- hash at audit time: `232aec02c7b62b35c27083a1a9bec6cf612ac68c9fec9cdd7a5bebd7f30021a9`
- pending plan id: `pending-strategy-plan-historical-2023-10-11-8c70c193d8520032`
- source order plan id: `strategy-plan-historical-2023-10-11-8c70c193d8520032`
- source order plan hash: `de1d581b0527ece139ef0cb25b38e7472ed03480bdd6af1d1a9aec25602c6d4f`
- created at / plan created date: `2023-10-11`
- updated at: `2023-10-11T15:00:00+09:00`
- intended submit date: `2023-10-11`
- target session date: `2023-10-11`
- state: `REVIEW_REQUIRED`
- plan overall status: `REVIEW_REQUIRED`
- review scope: `AUTHORITY_UNKNOWN_REVIEW`
- review scope source: `phase24_ht_planning_submit_feasibility_v1`
- review scope reason: `corporate_action_event_not_resolved;corporate_action_event_not_resolved`
- sell continuation allowed: `false`
- approved item ids: `[]`
- approved sell item ids: `[]`
- approved buy item ids: `[]`
- review required sell item ids: `["strategy-b5086c01c378aa03084d"]`
- review required buy item ids: `["strategy-8f204937cd52348d3712"]`
- consume: `consumed = false`, no submitted order ids

Items:

| Symbol | Side | Pending item id | Source decision | PM decision | Qty | State | Reason | Campaign id |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |
| `50280` | SELL | `strategy-b5086c01c378aa03084d` | `rp-2023-10-11-50280-sell_exit-ef85562eee72162f` | `pm-2023-10-11-50280-reduce` | `100` | `REVIEW_REQUIRED` | `corporate_action_event_not_resolved` | empty in stale Pending |
| `76920` | BUY | `strategy-8f204937cd52348d3712` | `rp-2023-10-11-76920-buy_new-43f426e3f06332a5` | empty | `400` | `REVIEW_REQUIRED` | `corporate_action_event_not_resolved` | `pc-78a2cbc4de31dcec-76920-0001` |

The 50280 item embeds the old unresolved CA authority:

- embedded status: `REVIEW_REQUIRED`
- embedded reason: `corporate_action_event_not_resolved`
- embedded event type: `UNKNOWN_ADJFACTOR_IMPACT`
- embedded already applied status: `UNKNOWN`
- embedded quantity/price reconciliation: `REVIEW_REQUIRED`
- embedded authority hash: `327b4aef125cd5ffd64fc4d4a6046d5d280d3cf0802f879560238b8b520c60bd`

That embedded hash differs from the current resolved artifact hash:

- current resolved authority hash: `fd17c5723e569e84b4cdd7912a9c712c7f6334d1d05e6615a396828bb54609f4`

Therefore the active Pending predates the CA authority resolution and remains bound to stale decision-material evidence.

## Stale Pending Determination

`PENDING_STALE_AFTER_CA_RESOLUTION`: YES.

The Pending is stale because it still represents 50280 as an unresolved CA SELL item even though the canonical CA authority now passes for the same run/date/symbol/quantity. The stale Pending continues to carry the old unresolved CA authority hash and old `UNKNOWN_ADJFACTOR_IMPACT` payload.

This is not a Strategy change. It is a dependent Runtime artifact whose materialized feasibility/review-scope state was frozen before a downstream operator authority changed from `REVIEW_REQUIRED` to `PASS`.

## Post-Resolution Resume First Failure

`POST_RESOLUTION_RESUME_FIRST_FAILURE`: stale Pending review scope at the sell-planning entry/readiness gate.

Post-resolution resume-produced evidence:

- run state remains `HALT`
- `next_job = 2023-10-11:sell_planning`
- `halted_at.business_date = 2023-10-11`
- `halted_at.job = sell_planning`
- resumed subprocess return code: `20`
- sell-planning runtime manifest:
  - `exit_code = 20`
  - `final_state = REVIEW_REQUIRED`
  - `reason = historical_safety_temporal_authority_missing`
  - `final_safety_reason = historical_safety_temporal_authority_missing`
  - `data_readiness_status = REVIEW_REQUIRED`
  - `data_readiness_review_reasons = ["historical_safety_temporal_authority_missing", "pending_review_required"]`
  - pending component reason: `pending_review_required`
  - safety component reason: `historical_safety_temporal_authority_missing`
  - guard codes: `PENDING_BATCH_REVIEW_REQUIRED`, `TEMPORAL_MISMATCH`

The sell-planning body was not reached:

- `sell_planning/pending_continuity_evidence.json`: `status = NOT_EXECUTED`, reason `historical_safety_temporal_authority_missing`
- `sell_planning/position_management_evidence.json`: `status = NOT_EXECUTED`, reason `historical_safety_temporal_authority_missing`

Classification:

- stale Pending review scope: YES
- historical safety temporal authority: secondary symptom caused by stale Pending not allowing sell continuation
- stale embedded CA authority hash: YES, concrete stale dependency
- 76920 unresolved BUY only: not by itself fatal if 50280 is regenerated to PASS
- campaign-id mismatch: stale Pending still has empty 50280 campaign id, but this is not the first re-HALT boundary
- other new boundary: NO evidence

## 50280 Re-evaluation

`50280_REEVALUATED_ITEM_STATE`: expected PASS / approved executable `SELL_EXIT 100` if Planning/Pending are regenerated from current accepted authorities.

Evidence:

- Current CA evaluator with relative run-scoped event evidence returns PASS for `side=SELL`, `submit_quantity=100`, `pending_quantity=100`, `current_quantity=100`, `broker_available_quantity=100`.
- DM established the canonical Runtime-owned post-CA quantity as `100`, and the current CA artifact confirms `post_adjustment_quantity = 100`.
- Strategy Runtime Planning already carries `SELL_EXIT` for 50280:
  - `rp-2023-10-11-50280-sell_exit-ef85562eee72162f`
  - quantity `100`
  - PM source `pm-2023-10-11-50280-reduce`
- The historical CA quarantine registry currently contains 76920 only; no unresolved 50280 quarantine entry was found.
- Current `strategy_authority.py` materializes CA authority before Pending membership and would attach the current PASS CA authority.

Expected regenerated 50280 fields:

- side/action: `SELL_EXIT`
- quantity: `100`
- CA authority status: `PASS`
- item state: `APPROVED`
- batch submit status: `PASS_ITEM_SUBMITTABLE`
- item review reason: empty
- campaign id: `pc-d468aca3b9d6da8f-50280-0001`

This conclusion is based on current source/evidence. It was not materialized in DN.

## 76920 Interaction

`76920_POST_CA_RESOLUTION_ROLE`: remaining BUY-only review candidate.

The historical corporate action quarantine registry currently includes 76920 and not 50280. For 76920:

- side: BUY
- quantity: `400`
- current Pending state: `REVIEW_REQUIRED`
- reason: `corporate_action_event_not_resolved`
- quarantine status: `QUARANTINED`
- resolution status: `UNRESOLVED`
- production applicability: `NEVER`

Once 50280 is regenerated to PASS, 76920 should remain a blocked BUY item. Under the current review-scope contract, a Pending with only blocked BUY items and no blocked SELL items becomes `BUY_ITEM_SCOPED_REVIEW`, allowing SELL continuation.

## Expected Recalculated Review Scope

`EXPECTED_RECALCULATED_REVIEW_SCOPE`: `BUY_ITEM_SCOPED_REVIEW`.

`EXPECTED_SELL_CONTINUATION_ALLOWED`: YES.

Reason:

- 50280 SELL is expected to pass after consuming current resolved CA authority.
- 76920 remains BUY-only `REVIEW_REQUIRED`.
- `_review_scope_for_submit_feasibility()` classifies blocked BUY only, with no blocked SELL and no unknown authority, as `BUY_ITEM_SCOPED_REVIEW`.
- Historical safety temporal authority has a sell-continuation adapter for this scope.

If a regenerated 50280 item unexpectedly remains blocked, the scope would remain `AUTHORITY_UNKNOWN_REVIEW`; however the current CA evaluator and registry state do not support that outcome.

## DL SELL Campaign Repair Readiness

`DL_SELL_CAMPAIGN_REPAIR_ACTUAL_PATH_READY`: YES.

Current source path:

- `_runtime_planning_position_campaign_id()` uses explicit campaign id first.
- For `SELL_EXIT` / `SELL_REDUCE`, if explicit id is absent, it reads run-scoped `daily/<date>/positions/position_campaigns.json`.
- `_run_scoped_open_position_campaign_id()` supports both `position_campaigns` and `campaigns` payload keys.
- Target evidence contains exactly one open 50280 campaign with positive quantity:
  - `pc-d468aca3b9d6da8f-50280-0001`

Therefore regenerated 50280 SELL Pending should inherit `pc-d468aca3b9d6da8f-50280-0001`. The current empty campaign id is a stale artifact symptom, not evidence that DL is unavailable.

## Correct Continuation Mechanism

`POST_AUTHORITY_CHANGE_CONTINUATION_MECHANISM`: `recover-stale-pending` followed by scoped `replay-recovered-day`.

Direct `resume` is not the correct next action after changing a decision-material authority that an active Pending already embedded. Direct resume reuses the stale Pending and stops before Planning/Pending can re-materialize.

Existing canonical path:

- `recover-stale-pending` is documented in `docs/03_operations/runtime_test_command_guide.md`.
- It is designed for a same-day `REVIEW_REQUIRED` Pending generated under stale semantics.
- It preserves stale Pending/daily evidence, retires the current Pending slot to `EMPTY`, and rewinds the run to the requested replay boundary.
- It does not edit Ledger or Current.
- Then `replay-recovered-day` re-executes the allowed day jobs from the recovered boundary.

Target-run precondition assessment from code/state:

| Precondition | Status | Evidence |
| --- | --- | --- |
| `run_state.status = HALT` | PASS | run_state status `HALT` |
| `run_state.next_job = 2023-10-11:sell_planning` | PASS | current next_job |
| `halted_at.business_date = 2023-10-11` | PASS | current halted_at |
| `halted_at.job = sell_planning` | PASS | current halted_at |
| current Pending state `REVIEW_REQUIRED` | PASS | active Pending |
| Pending target session date `2023-10-11` | PASS | active Pending |
| Pending plan created date `2023-10-11` | PASS | active Pending |
| Pending has items | PASS | two items |
| persistent state at previous completed boundary | PASS | `.runtime/persistent_ledger/state.json` as of `2023-10-10` |
| target-date Ledger rows absent | PASS | orders/executions/positions/cash/events all have zero `2023-10-11` rows |

DN did not execute the command or dry-run.

## Dependent Pending Invalidation Contract

`DEPENDENT_PENDING_INVALIDATION_CONTRACT`: PARTIAL / OPERATOR-SCOPED.

There is an existing canonical recovery mechanism for this lifecycle shape: `recover-stale-pending`. That means the system is not missing a safe path.

However, direct `resume` does not automatically detect that a resolved authority hash has invalidated an already-active Pending's embedded review state. The generic automatic contract:

```text
decision-material authority changes
-> dependent Pending becomes stale
-> Pending is automatically regenerated/revalidated before resume entry
```

is not present as a direct resume behavior. The current contract is operator-mediated: after authority resolution, the operator must use stale Pending recovery to retire and regenerate the dependent Pending.

`PRODUCTION_REPAIR_REQUIRED`: NO for the target run continuation, because an existing canonical recovery path is available and its preconditions match. Conditional future improvement: add a non-mutating resume diagnostic that reports `STALE_DEPENDENT_PENDING_REQUIRES_RECOVER_STALE_PENDING` instead of presenting the same safety reason repeatedly.

`REPAIR_SCOPE`: no Strategy/PM/PC/PS repair. If pursued later, narrow runtime_test orchestration/documentation improvement only: detect stale embedded authority hash versus current authority hash and recommend `recover-stale-pending`; do not auto-approve or bypass Pending.

`STRATEGY_CHANGE_REQUIRED`: NO.

## Side Effects

`POST_RESOLUTION_RESUME_SIDE_EFFECTS`: none found.

Checks:

- target-date Ledger orders rows: `0`
- target-date Ledger executions rows: `0`
- target-date Ledger positions rows: `0`
- target-date Ledger cash rows: `0`
- target-date Ledger events rows: `0`
- target-date daily directories present only through `sell_planning`; no `submit` or `execution` directory exists
- `.runtime/runtime_state/historical_broker/2023-10-11` has no files
- Pending consume remains `consumed = false`, no submitted order ids
- persistent ledger state remains as of `2023-10-10`

`TARGET_RUN_MUTATED`: NO in DN.

The operator's pre-DN CA resolution did mutate only the CA authority artifact; DN did not mutate anything except this report.

## Next Safe Continuation Action

`NEXT_SAFE_CONTINUATION_ACTION`: run `recover-stale-pending --dry-run` first. Do not run direct `resume` again before stale Pending recovery.

Recommended first command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-stale-pending \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260902T060955933565Z \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-10-11-8c70c193d8520032 \
  --dry-run \
  --json
```

If and only if the dry-run returns PASS, the existing canonical sequence is:

1. actual `recover-stale-pending` with the same arguments plus mutation confirmations
2. `replay-recovered-day --business-date 2023-10-11 --jobs morning,sell_planning,submit,execution` dry-run
3. actual scoped replay if dry-run passes
4. inspect regenerated Pending/Submit/Execution evidence before any further resume

DN does not provide a direct resume command because direct resume is the failure mode being audited.

## Required Final Answers

1. `50280_CA_AUTHORITY_POST_RESOLUTION_STATUS`: PASS; current artifact is `STOCK_SPLIT`, `CONFIRMED`, quantity `100`, price/quantity reconciliation `PASS`, source hash correct.
2. `CURRENT_PENDING_STATE`: same-day `REVIEW_REQUIRED`, plan `pending-strategy-plan-historical-2023-10-11-8c70c193d8520032`, `AUTHORITY_UNKNOWN_REVIEW`, `sell_continuation_allowed=false`, 50280 SELL and 76920 BUY both still review-required.
3. `PENDING_STALE_AFTER_CA_RESOLUTION`: YES.
4. `POST_RESOLUTION_RESUME_FIRST_FAILURE`: sell-planning entry/readiness gate rejects stale active Pending, producing `historical_safety_temporal_authority_missing` and `pending_review_required`.
5. `50280_REEVALUATED_ITEM_STATE`: expected regenerated `SELL_EXIT 100`, CA PASS, campaign `pc-d468aca3b9d6da8f-50280-0001`, no CA review.
6. `76920_POST_CA_RESOLUTION_ROLE`: remaining BUY-only review due unresolved historical CA quarantine.
7. `EXPECTED_RECALCULATED_REVIEW_SCOPE`: `BUY_ITEM_SCOPED_REVIEW`.
8. `EXPECTED_SELL_CONTINUATION_ALLOWED`: YES.
9. `DL_SELL_CAMPAIGN_REPAIR_ACTUAL_PATH_READY`: YES.
10. `POST_AUTHORITY_CHANGE_CONTINUATION_MECHANISM`: `recover-stale-pending` then scoped `replay-recovered-day`; not direct resume.
11. `DEPENDENT_PENDING_INVALIDATION_CONTRACT`: PARTIAL / operator-scoped via existing stale Pending recovery; not automatic in direct resume.
12. `PRODUCTION_REPAIR_REQUIRED`: NO for continuation; optional diagnostic improvement only.
13. `REPAIR_SCOPE`: none required before continuation; optional runtime_test diagnostic/documentation improvement, no Strategy change.
14. `STRATEGY_CHANGE_REQUIRED`: NO.
15. `POST_RESOLUTION_RESUME_SIDE_EFFECTS`: none; no target-date submit/execution/fill/cash/position mutation found.
16. `TARGET_RUN_MUTATED`: NO in DN.
17. `NEXT_SAFE_CONTINUATION_ACTION`: execute the `recover-stale-pending --dry-run` command above; proceed only if PASS.
18. `FINAL_JUDGMENT`: `PHASE32_DN_POST_CA_RESOLUTION_STALE_PENDING_CONFIRMED_RECOVER_STALE_PENDING_REQUIRED`

## Final Judgment

`PHASE32_DN_POST_CA_RESOLUTION_STALE_PENDING_CONFIRMED_RECOVER_STALE_PENDING_REQUIRED`

The 50280 CA authority is now resolved and passes under the current Runtime authority contract. The remaining HALT is not caused by unresolved 50280 authority itself; it is caused by an active same-day Pending that still embeds the old unresolved CA authority hash and old `AUTHORITY_UNKNOWN_REVIEW` scope. Direct resume reuses that stale Pending and fails at the sell-planning readiness gate before regenerated Planning/Pending can consume the new PASS authority.

The current run is still clean at the `2023-10-10` Ledger/Current boundary with no `2023-10-11` side effects. The existing canonical next action is `recover-stale-pending --dry-run`, then scoped recovery/replay only if the dry-run passes. Fresh-run is not required by the evidence in DN.
