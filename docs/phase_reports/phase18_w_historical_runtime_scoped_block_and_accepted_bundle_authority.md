# Phase18-W Historical Runtime Scoped Block and Accepted Bundle Authority

## Final Judgment

`PHASE18_W_AUTHORITY_APPROVAL_REQUIRED`

The Runtime Test Runner remediation is complete for BUY-only scoped `REVIEW_REQUIRED` / `BLOCK` continuation. The target run also proves that Runtime accepted Atomic BUY AI Bundle authority is still missing, so Runtime must remain fail-closed until Authority approval materializes an accepted bundle. No Promotion Candidate was adopted directly.

## Target Run

| Item | Evidence |
|---|---|
| Run | `runtime-test-historical-extended-smoke-20260717T092848373656Z` |
| Business date / job | `2026-06-29` / `morning` |
| Runtime CLI exit | `20` |
| Runner behavior before Phase18-W | `HALT` after morning |
| Lifecycle decision | `REVIEW_REQUIRED` |
| Classification | `INSUFFICIENT_EVIDENCE` |
| Scope | BUY planning/submission blocked; SELL planning/submission authorization allowed |

Target evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260717T092848373656Z/daily/2026-06-29/morning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260717T092848373656Z/daily/2026-06-29/morning/buy_lifecycle_sell_continuity.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260717T092848373656Z/daily/2026-06-29/morning/sell_authorization_continuity.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260717T092848373656Z/run_state.json`

## Investigation Results

| Question | Finding | Decision |
|---|---|---|
| Should Historical Test continue on BUY-only `REVIEW_REQUIRED` / `BLOCK`? | Phase18-T contract says BUY planning/submit may be blocked while Current, Valuation, PM, Safety, SELL planning, and SELL authorization remain reachable when scope evidence proves SELL is not blocked. | Continue only for evidence-proven BUY-only scope. |
| Can `run_daily_operation` exit code `20` distinguish scoped BUY block and global block? | No. Exit code alone only tells the caller the Runtime CLI ended non-zero. The runtime manifest contains the scope fields and continuity stages. | Do not continue from exit code alone. |
| Should `scripts/runtime_test.py` inspect Morning Evidence or should Runtime CLI return `0`? | Returning `0` would hide the lifecycle gate state. The runner is the orchestrator and already collects the manifest. | Runner reads copied morning manifest and continues only when all scoped evidence checks pass. |
| What is the formal Historical Runtime Accepted Atomic BUY AI Bundle Authority? | `src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py` resolves `.runtime/runtime_state/accepted_buy_ai_bundle.json`, which must point to one accepted Atomic BUY AI Bundle. Promotion candidates, latest directories, and manual Production paths are forbidden. | Missing accepted state remains fail-closed. |
| How do Phase18 Promotion Candidate, Registry accepted state, `.runtime/artifact_registry`, and Runtime consumer resolver relate? | Phase18-I created a Promotion Candidate transaction under `.runtime/artifact_registry/promotion_candidates/...`. Registry also has legacy accepted Candidate/Opportunity artifact sets. Runtime lifecycle authority requires the accepted Atomic BUY AI Bundle state, not the Promotion Candidate transaction. | Promotion Candidate is review evidence only until an accepted state is written by Authority workflow. |
| Why are Candidate/Opportunity READY via old path while Lifecycle Gate reports accepted state missing? | Legacy model resolvers still resolve registered model paths and schema readiness independently. Lifecycle Gate uses accepted-only Atomic BUY AI Bundle authority and rejects missing accepted state. | Authority duality confirmed; do not mask by fallback. |

## Implementation

Changed `scripts/runtime_test.py`:

- Added strict scoped continuation classification for non-zero `morning` Runtime CLI results.
- The runner now records `REVIEW_REQUIRED_BUY_ONLY` or `BLOCKED_BUY_ONLY` only when all of these are true:
  - lifecycle decision is `REVIEW_REQUIRED` or `BLOCK`
  - classification is not `CRITICAL_AUTHORITY_VIOLATION`
  - BUY planning and BUY submit are blocked
  - SELL planning and SELL submit authorization are not blocked
  - SELL permissions are `PASS`
  - `buy_lifecycle_sell_continuity` is `PASS`
  - `buy_lifecycle_sell_authorization_continuity` is `PASS`
  - call graph reached SELL continuation
  - no Broker write occurred
- Scope evidence is persisted as `scoped_block_continuation.json`.
- `resume` treats scoped BUY-only jobs as completed, while failed jobs without scoped evidence are not skipped.
- Global blocks, SELL dependency blocks, `CRITICAL_AUTHORITY_VIOLATION`, missing manifest, or insufficient scope evidence still `HALT`.

Added `tests/runtime_v2/test_phase18w_historical_scoped_block.py`:

- BUY-only `REVIEW_REQUIRED` with continuity evidence continues through all jobs.
- Critical authority violation with the same non-zero exit remains `HALT`.

## Accepted Bundle Authority Status

| Authority item | Status | Evidence |
|---|---|---|
| Accepted Atomic BUY AI Bundle state | Missing | `.runtime/runtime_state/accepted_buy_ai_bundle.json` does not exist |
| Promotion Candidate | Present | `.runtime/artifact_registry/promotion_candidates/transactions/promotion-tx-phase18i-1081babc49b5d26b/atomic_buy_ai_bundle.json` |
| Promotion Candidate direct runtime use | Forbidden / not used | Runtime accepted resolver forbids promotion candidate fallback |
| Legacy Candidate accepted set | Present | `.runtime/artifact_registry/index/registry_index.json` / transaction previous reference |
| Legacy Opportunity accepted set | Present | `.runtime/artifact_registry/index/registry_index.json` / transaction previous reference |
| Runtime lifecycle authority | Missing accepted state, fail-closed | `accepted_state_missing`, `missing_accepted_bundle_ref` |

Because the accepted Atomic BUY AI Bundle state is absent, Phase18-W did not create or update Registry accepted state. Authority approval is required before Runtime can use the Phase18 Promotion Candidate as accepted Runtime input.

## Validation

Commands run:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18w_pycache python3 -m pytest tests/runtime_v2/test_phase18w_historical_scoped_block.py tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase18w_pycache python3 -m py_compile scripts/runtime_test.py
```

Results:

- `24 passed`
- `py_compile` PASS

## Non-Implementation Confirmation

| Prohibited action | Status |
|---|---|
| Promotion Candidate direct Runtime adoption | NOT_PERFORMED |
| latest fallback | NOT_PERFORMED |
| manual path fallback | NOT_PERFORMED |
| unconditional exit code 20 continuation | NOT_PERFORMED |
| ignoring accepted evidence insufficiency | NOT_PERFORMED |
| Registry accepted state unauthorized change | NOT_PERFORMED |
| BV15 relaxation | NOT_PERFORMED |
| forced BUY | NOT_PERFORMED |
| BUY restart | NOT_PERFORMED |
| Broker write | NOT_PERFORMED |

## Conclusion

The Production contract mismatch in Runtime Test Runner is remediated: BUY-only scoped lifecycle blocks can continue to SELL jobs only when manifest evidence proves the block scope. The accepted Atomic BUY AI Bundle is still not materialized as accepted Runtime authority, so the correct Phase18-W outcome is:

`PHASE18_W_AUTHORITY_APPROVAL_REQUIRED`
