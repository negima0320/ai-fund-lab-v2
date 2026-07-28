# Phase22-P - Runtime Test Command Strategy Shadow Wiring

## Primary Judgment

`PHASE22_P_RUNTIME_TEST_COMMAND_STRATEGY_SHADOW_WIRING_COMPLETE`

Runtime Test commands now expose and orchestrate Phase22 Strategy artifact generation as shadow-only run evidence. The runner does not implement Strategy judgment logic; it calls the production-common Phase22 Strategy producers and stores draft, non-production-consumable artifacts under `reports/runtime_tests/runs/<RUN_ID>/`.

## Command Reachability

Before this task, `plan`, `run`, `fresh-run`, `resume`, `validate`, `close`, `run-status`, `system-status`, `ai-status`, `summarize`, and `show` had no run-scoped Phase22 Strategy generation path. Strategy summarize scopes existed, but they resolved `.runtime/strategy_artifacts` instead of actual run evidence.

After this task:

- `plan` shows a per-day `strategy_shadow_job`.
- `run` and `resume` execute Strategy shadow generation after each daily Runtime job sequence.
- `fresh-run` inherits the same plan/run contract and dry-run displays Strategy shadow.
- `validate` checks Strategy shadow structural evidence separately from policy acceptance.
- `close` adds Strategy shadow judgment, dates, completeness, lineage, and eligibility fields.
- `run-status` reports Strategy shadow progress.
- `system-status --scope strategy` reports Strategy shadow readiness without changing production readiness.
- `ai-status` includes read-only latest Strategy AI input binding when an active run has Strategy evidence.
- `summarize --scope strategy` reads run-scoped Strategy evidence.
- `show --artifact strategy` inspects run-level or date-level Strategy evidence.

## Strategy Chain

The shadow chain writes:

`input_manifest.json`, `market_context.json`, `corporate_event.json`, `portfolio_policy.json`, `dynamic_position_count.json`, `dynamic_cash_exposure.json`, `portfolio_construction.json`, `position_sizing.json`, `position_management.json`, `capital_deployment.json`, `runtime_planning.json`, `strategy_decision_trace.json`, `legacy_shadow_comparison.json`, and `strategy_shadow_summary.json`.

Run-level indexes are `strategy_shadow_manifest.json` and `strategy_shadow_summary.json`.

## AI Binding

The Strategy input manifest uses the COMMITTED Accepted Generation resolver. It records accepted generation id, Candidate and Opportunity model references and hashes, scaler references and hashes, calibration references and hashes, feature schema references and hashes, Candidate output artifact reference/hash, and Opportunity output artifact reference/hash.

No latest model selection, fixture fallback, arbitrary model discovery, or AI-status reverse generation is used.

## Daily Hook

Strategy shadow generation runs after the normal daily Runtime job sequence. This ensures Candidate / Opportunity outputs and Current / Pending snapshots are available while preserving the fact that Strategy shadow cannot influence Morning BUY, ADD quantity, Sell Planning quantity, Pending, Submit, Approval, Execution, Ledger, Current, or Broker behavior for that same day.

## Isolation

The shadow job records before/after hashes for Pending, Ledger files, Current, Runtime State, Accepted Generation pointer, and Registry checkpoint. Mutation detection is a HALT condition. Broker connection, broker write, and external delivery flags are recorded as false.

## Consumer Eligibility

`shadow_consumer_eligibility` is reported separately from `active_runtime_consumer_eligibility`. This task does not promote active Runtime consumers, does not perform Runtime switch, and keeps legacy authority active.

## Tests

- `python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -q`: PASS, 2 passed
- `python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase22_m_strategy_summarize_scope.py tests/runtime_v2/test_phase19_ax_system_status.py -q`: PASS, 8 passed
- `python3 -m pytest tests/strategy -q`: PASS, 113 passed
- `python3 -m compileall -q scripts/runtime_test.py src/ai_fund_lab_v2/strategy src/ai_fund_lab_v2/runtime_v2/safety`: PASS
- `runtime_test.py plan --profile historical-smoke --start-date 2026-07-06 --business-days 1 --json`: PASS
- `runtime_test.py fresh-run --profile historical-smoke --start-date 2026-07-06 --business-days 1 --initial-cash 1000000 --dry-run --json`: PASS
- `runtime_test.py system-status --scope strategy --json`: REVIEW_REQUIRED, expected existing system-status exit 10
- Probe `show --artifact strategy`, `validate`, and `summarize --scope strategy`: PASS/REVIEW_REQUIRED as expected for incomplete probe run evidence

The single-day probe generated all required Strategy files. Its Strategy judgment was `BLOCK` because the probe intentionally used an old business date against current `.runtime` source data, causing producer PIT/source checks such as future source row detection. This is evidence that shadow status is not hidden behind active Runtime success.

## Long Tests

Long tests were not executed. 5BD, 20BD, 200BD, 1-year, 3-year, and long runtime smoke runs remain user/operator execution.

User 5BD command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Gaps

Blocking gaps: none for command wiring.

Non-blocking gaps:

- Existing historical source freshness can make Strategy shadow produce `BLOCK` for old dates.
- Corporate Event full source coverage and Market Context historical sector PIT remain Runtime switch review conditions from Phase22-O.
- Long 5BD+ operator validation is not executed by Codex.

## Phase22 Closure Gate

Phase22-P wiring is complete, but Phase22 Closure still requires explicit user approval. Runtime switch, active consumer eligibility promotion, and legacy retirement remain not approved.

## Final Gate

Runtime Test Commands Connected to Phase22 Strategy: YES
AI Accepted Generation Binding: PASS
Run-scoped Strategy Evidence: PASS
Strategy Summarize Availability: PASS
Shadow Consumer Eligibility: REVIEW_REQUIRED
Active Runtime Consumer Eligibility: NO
Runtime Switch Performed: NO
Legacy Authority Active: YES
Phase22 Closure Recommendation: REVIEW_REQUIRED
