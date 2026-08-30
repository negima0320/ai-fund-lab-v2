# Phase32-AE — Partial Submit Replay Orchestration Repair

## Objective

Repair the Phase32-AD replay gap for target run
`runtime-test-historical-extended-smoke-20260830T081425790243Z` without changing
Strategy semantics and without executing any mutating command against the real
target run.

## Root Cause

Phase32-AC recovery correctly preserved the already accepted 92460 submit
evidence, but the follow-up scoped replay attempted the full
`morning -> sell_planning -> submit -> execution` path. Replay stopped at
`2023-10-11:sell_planning` after regenerating a same-day `REVIEW_REQUIRED`
Pending. That shape is valid after Phase32-AA because 50280 remains blocked by
corporate-action authority and BUY items remain item-scoped review, but
`replay-recovered-day` treated the expected review state as fatal before the
preserved accepted 92460 order could be reconciled through execution.

The first bad orchestration boundary was:

`recover-partial-submit preserved accepted submit evidence`
-> `scoped replay regenerated review-only same-day Pending`
-> `replay halted before accepted-item execution reconciliation`

## Repair Selected

Selected option: `Accepted-Items-Only Partial-Day Finalization`.

Reason: it is narrower than a full scoped replay repair. It does not rerun
Strategy, Planning, Pending production, or Submit. It validates the applied
partial-submit recovery state, preserved accepted order rows, matching
historical broker accepted evidence, same-day Historical safety authority, no
target-date execution rows, and the regenerated review-only Pending. It then
executes only the preserved accepted broker evidence through the existing
historical execution readonly projection, terminalizes Pending, writes day
completion evidence, and makes the run resume-ready.

## Files Changed

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/phase32_ae_partial_submit_replay_orchestration_repair.md`

## Canonical Behavior

New command:

`finalize-partial-submit-day`

It requires:

- `run_state.status = HALT`
- `scoped_partial_submit_recovery.status = RECOVERY_APPLIED`
- preserved accepted order ids and item ids
- matching historical broker accepted evidence
- target-date Ledger executions absent
- regenerated same-day Pending in `REVIEW_REQUIRED`
- no unexpected approved regenerated items
- same-day Historical safety temporal authority `READY`

It forbids resubmitting preserved orders. Reviewed regenerated items remain not
submitted and not executed.

Execution uses the existing historical execution readonly pipeline. A
reconciliation-only `REVIEW_REQUIRED` after a successful persistent commit is
accepted inside this finalization path because Pending is terminalized
immediately afterward and day completion must pass. Pre-commit, projection,
Ledger, Current, broker evidence, safety authority, or mismatch failures still
fail closed.

## Validation

Focused tests:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'phase32_ae or phase32_ac_partial_submit'
7 passed, 44 deselected

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'phase32_ae or phase32_ac_partial_submit or g129 or buy_add or phase32_s'
19 passed, 48 deselected

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py
51 passed
```

Validated:

- dry-run is read-only
- preserved 92460 order is not resubmitted
- one accepted 92460 execution equivalent is reflected
- current Pending is terminalized to `CONSUMED`
- reviewed 50280/BUY items remain not executed
- missing Historical safety authority fails closed
- Phase32-AC recovery tests still pass
- Phase32-S/G129 BUY_ADD focused tests still pass

## Strategy Semantic Change

NO.

No Candidate selection, Opportunity, PM, PC, PS, Risk Pacing, Cash policy,
threshold, weight, BUY_ADD, or Winner Retention rule was changed.

## G129 Regression

NO.

Focused BUY_ADD/G129-adjacent regression tests passed.

## Real Target Run Mutation

NO.

Codex did not run recovery, replay, finalize, resume, fresh-run, or long
Historical against the target run.

## Exact Next User Action

First dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py finalize-partial-submit-day \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260830T081425790243Z \
  --business-date 2023-10-11 \
  --dry-run \
  --json
```

If dry-run returns `DRY_RUN`, apply:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py finalize-partial-submit-day \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260830T081425790243Z \
  --business-date 2023-10-11 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Then verify resume readiness:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260830T081425790243Z \
  --dry-run \
  --json
```

## Final Judgment

`PHASE32_AE_PARTIAL_SUBMIT_REPLAY_ORCHESTRATION_REPAIRED`
