# Phase31-F1M — F1L Production Acceptance / Resume vs Fresh-Run Readiness

## PRIMARY_JUDGMENT

PHASE31_F1M_F1L_ACCEPTED_RESUME_SAFE

## Required Output

F1L_SCOPE_CONFORMANCE = PASS

EQUIVALENT_PENDING_CONTRACT_ACCEPTANCE = PASS

GENUINE_CONFLICT_FAIL_CLOSED_ACCEPTANCE = PASS

93600_F1L_ACCEPTANCE = PASS

PENDING_IDENTITY_PRESERVATION = PASS

F1F_F1I_SEMANTICS_PRESERVED = YES

HALTED_RUN_ID = runtime-test-historical-extended-smoke-20260821T014643273280Z

HALTED_RUN_STATE_INTEGRITY = PASS

CAMPAIGN_OBSERVABILITY_GAP = NON_BLOCKING

RESUME_DECISION = RESUME_SAFE

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 82 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

USER_OPERATED_NEXT_COMMAND =

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume --run-id runtime-test-historical-extended-smoke-20260821T014643273280Z --confirm --yes-i-understand-this-mutates-trading-state
```

NEXT_TASK_RECOMMENDATION = Run the user-operated resume command. If resume validation completes successfully, continue long clean Historical validation. After completion, perform structural SELL audit first, then long-horizon performance evaluation.

## Authority Read

Read:

- `docs/phase_reports/phase31_f1k_post_f1i_fresh_run_sell_planning_halt_root_cause_audit.md`
- `docs/phase_reports/phase31_f1l_same_day_equivalent_sell_pending_idempotency_repair.md`
- `docs/phase_reports/phase31_f1i_prior_unrepresentable_reduce_campaign_evidence_bridge_production_repair.md`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`

F1K remains the root-cause authority. It classified the halt as a newly exposed same-day active pending SELL conflict at 2022-09-07 `sell_planning`, not as stale REDUCE quantity, F1F/F1I side effect, or campaign-history bridge corruption.

F1L remains the repair authority. It accepts only same-day equivalent SELL pending reuse and preserves genuine conflicts as `REVIEW_REQUIRED`.

## F1L Scope Acceptance

Accepted.

F1L changed the narrow runtime planning surface needed for same-day SELL pending idempotency:

- `runtime_v2/planning/sell_pipeline.py` recognizes an already-active same-day equivalent SELL pending and returns `PASS` / `IDEMPOTENT_EXISTING_PENDING`.
- `runtime_v2/pending/composition.py` recognizes additional existing lineage fields that prove EXIT intent.
- Focused tests were added for equivalent reuse, duplicate prevention, and conflict preservation.

F1L did not alter PM SELL semantics, F1F escalation gates, F1I prior-history bridge semantics, BUY, B10, ADD, minimum-notional policy, Market Context, or Runtime SELL action authority.

F1L_SCOPE_CONFORMANCE = PASS

## Equivalent Pending Contract Acceptance

Accepted.

The F1L equivalence contract requires all of:

- same business/session date
- approved active pending
- unconsumed pending item
- exactly one approved SELL item
- no BUY items
- same symbol as the current open position
- quantity equal to the full current position quantity
- EXIT-equivalent lineage
- supported pending state

Generic `SELL` is equivalent to `SELL_EXIT` only when lineage evidence resolves to EXIT through canonical pending/planning fields. `SELL_REDUCE` with different exposure is not equivalent to `SELL_EXIT`.

EQUIVALENT_PENDING_CONTRACT_ACCEPTANCE = PASS

## Genuine Conflict Preservation

Accepted.

Focused F1L regression keeps these fail-closed:

- different quantity
- ambiguous or multiple active SELL items
- different session/date
- existing BUY pending semantics
- REDUCE vs EXIT exposure mismatch
- stale active pending with a different date
- malformed or unsupported pending shape
- partial-fill unresolved evidence

The genuine-conflict result remains `REVIEW_REQUIRED` with the original pending preserved.

GENUINE_CONFLICT_FAIL_CLOSED_ACCEPTANCE = PASS

## 93600 Production Acceptance

Accepted.

The halted run stopped at:

- business date: `2022-09-07`
- failed job: `sell_planning`
- exit code: `20`
- next resume job: `2022-09-07:sell_planning`

The pre-HALT 2022-09-07 evidence reconstructs the intended path:

```text
PM EXIT 100
-> PS EXIT 100
-> Runtime SELL_EXIT 100
-> Morning pending SELL 100 exists
-> Later sell_planning encountered same active pending
```

The active pending item is:

- pending item id: `strategy-c8537cd09201c855e2b4`
- symbol: `93600`
- side: `SELL`
- quantity: `100.0`
- state: `CREATED`
- approved: `true`
- source decision type: `SELL_EXIT`
- temporal authority business date: `2022-09-07`
- quantity contract planning intent: `SELL_EXIT`
- quantity contract source planning id: `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`

The current position state immediately before 2022-09-07 has `93600` quantity `100.0` as of `2022-09-06`, so the pending quantity matches the full current position quantity.

Under F1L, this is an equivalent same-day SELL_EXIT pending and should resolve as:

- status: `PASS`
- pending equivalence: `EQUIVALENT`
- resolution: `REUSE_EXISTING_PENDING`
- duplicate pending: `0`
- original pending preserved: yes

93600_F1L_ACCEPTANCE = PASS

## Pending Identity Preservation

The halted run already contains the original 2022-09-07 morning pending item, and no 2022-09-07 submit or execution directory exists.

Ledger inspection found no 2022-09-07 order, execution, event, or position mutation for the failed sell-planning stage. Existing `93600` ledger entries are prior BUY/fill/position evidence from 2022-09-05 and 2022-09-06, not post-HALT duplicate side effects.

Resume re-enters at `2022-09-07:sell_planning`. F1L reuses the original same-day pending instead of writing a duplicate pending, fake order, or fake fill.

PENDING_IDENTITY_PRESERVATION = PASS

## F1F / F1I Preservation

F1L does not change:

- canonical SELL states
- `PERSISTENT_DETERIORATION`
- PM-owned EXIT gate
- prior unrepresentable REDUCE history bridge
- recovery reset
- minimum-notional exclusion

Focused F1F/F1I regression passed after F1L.

F1F_F1I_SEMANTICS_PRESERVED = YES

## Resume Safety Audit

The halted run state is usable:

- `fresh_run_summary.json` reports `resume_possible = true`.
- `run_state.json` is `HALT` and points to `2022-09-07:sell_planning`.
- completed business days end at `2022-09-06`.
- 2022-09-07 data readiness, market refresh, morning, strategy, PM, PS, runtime planning, and sell-planning inputs exist.
- 2022-09-07 submit/execution artifacts do not exist.
- `.runtime/persistent_ledger/state.json` still has `93600` quantity `100.0` as of `2022-09-06`.
- source baseline comparison passes for `source_commit`, `source_dirty`, and `registry_hash`.

The resume CLI baseline guard compares `source_commit`, `source_dirty`, and `registry_hash`; all match the halted run's recorded `source_baseline`. Therefore the user-operated resume command should pass the precondition gate before re-entering the failed job.

HALTED_RUN_STATE_INTEGRITY = PASS

## Resume Decision

RESUME_DECISION = RESUME_SAFE

Exact resume boundary:

```text
2022-09-07:sell_planning
```

Reason:

The run halted before submit/execution. The same 93600 pending item remains active and is equivalent under F1L. F1L does not require regenerating upstream PM/PS/Runtime planning artifacts because the upstream decision evidence already resolves to `SELL_EXIT 100`; the repair changes only the sell-planning handling of an already-existing equivalent pending. Resume therefore reprocesses the failed stage and should reuse the original pending without duplicate submit/fill risk.

Fresh-run is not required by artifact/state integrity. It remains useful only as a later clean validation after the repaired resume succeeds.

## Campaign Observability Gap

F1K/F1L retained a separate 93600 campaign-id observability discrepancy. This gap does not block the F1L resume decision because the 2022-09-07 executable SELL path is proven by PM EXIT, PS full EXIT quantity, Runtime `SELL_EXIT`, active pending lineage, and current position quantity.

CAMPAIGN_OBSERVABILITY_GAP = NON_BLOCKING

Keep this as later observability cleanup; do not repair it in F1M.

## Focused Regression

Executed short focused regression only. No Historical fresh-run, resume, replay, or long validation was executed.

Commands:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q
python3 -m pytest tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q
```

Results:

- F1L idempotency: 8 passed
- previous SELL pending reconciliation: 10 passed
- BUY/Pending safety: 28 passed
- Runtime SELL quantity/materialization: 22 passed
- F1F/F1I preservation: 14 passed

FOCUSED_TEST_RESULTS = PASS; 82 passed

## Compile / Diff

Compile command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py
```

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

## Final Questions

1. F1LはPending idempotencyだけを直しているか？
   - Yes. F1L scope is limited to same-day equivalent SELL pending reuse and supporting pending intent recognition.
2. 本物のpending conflictは引き続きfail-closedか？
   - Yes. Genuine conflicts remain `REVIEW_REQUIRED` and preserve the original pending.
3. 93600 equivalent pendingは安全にreuseできるか？
   - Yes. The active pending is same-day `SELL_EXIT` lineage for 93600, quantity `100.0`, matching the current full position quantity.
4. duplicate pending/order/fill riskはないか？
   - No duplicate submit/fill risk was found. The run halted before submit/execution, and F1L reuses the existing pending.
5. F1F/F1I SELL semanticsを壊していないか？
   - No. Focused F1F/F1I regression passed and F1L does not touch PM semantics.
6. halted runのstateは正常か？
   - Yes. Completed state is valid through 2022-09-06; 2022-09-07 halted at sell_planning before submit/execution.
7. 9/7からresumeして安全か？
   - Yes. Resume should re-enter `2022-09-07:sell_planning`.
8. campaign observability discrepancyはblockingか？
   - Non-blocking for resume and SELL execution correctness.
9. resumeかfresh-runか、どちらが正しいか？
   - Resume is correct. Fresh-run is not required for artifact/state reasons.
10. 長期validationへ進める状態か？
   - Yes, after the user-operated resume command completes successfully.
