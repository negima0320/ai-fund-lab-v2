# Phase31-G26 - Re-entry Semantic Eligibility Migration

## Primary Judgment

PRIMARY_JUDGMENT = PHASE31_G26_REENTRY_SEMANTIC_ELIGIBILITY_MIGRATION_IMPLEMENTED_ACCEPTED

G26 migrated the existing Portfolio Construction re-entry gate composition into a canonical PC-owned semantic eligibility result. The implementation preserves the existing cooldown duration and existing PIT recovery inputs, does not create a second authority, and keeps the old observable zero-weight/review reason compatibility while making PC consume a single explicit `reentry_semantic_eligibility` contract.

## Canonical Authority

REENTRY_ELIGIBILITY_OWNER = PORTFOLIO_CONSTRUCTION

CANONICAL_REENTRY_SEMANTIC_RESULT_IMPLEMENTED = YES

REENTRY_STATES_IMPLEMENTED =

- REENTRY_NOT_APPLICABLE
- REENTRY_ELIGIBLE
- REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION
- REENTRY_NOT_ELIGIBLE_PRIOR_EXIT_CONTEXT
- REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE
- REENTRY_NOT_ELIGIBLE_SAFETY
- REENTRY_INSUFFICIENT_EVIDENCE

Canonical fields now emitted per PC member:

- `reentry_semantic_eligibility`
- `reentry_semantic_eligibility_schema_version`
- `reentry_semantic_state`
- `reentry_semantic_status`
- `reentry_reason_codes`
- `reentry_renewed_current_evidence_status`
- `reentry_candidate_eligibility_status`
- `reentry_safety_restriction_status`
- `reentry_constraint_scope`

The existing `semantic_reentry_authority` now embeds the canonical `semantic_result`.

## Current Re-entry Gate Inventory

| Gate | Location | Owner | Inputs | Decision | Current reason code | PIT status | Temporal scope | Duplicates another gate | Can compose into overbroad rejection |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prior holding identity | `portfolio_construction._semantic_reentry_evidence` | PC | `current_position`, PM action, membership intent | BUY_ADD / BUY_NEW / REENTRY | n/a | PASS | decision date row state | NO | NO |
| Prior EXIT state | `portfolio_construction._prior_exit_business_date`; `shadow_runtime._supply_prior_exit_state` materializes PIT source | PC consumes PIT evidence | prior/last/previous exit date | same-symbol re-entry identity | n/a | PASS when date < current business date | prior execution date only | NO | PARTIAL |
| Cooldown | `portfolio_construction._semantic_reentry_evidence` | PC | prior exit date, current business date, existing `REENTRY_COOLDOWN_BUSINESS_DAYS` | PASS / FAIL_CLOSED | `reentry_minimum_cooldown_not_satisfied` | PASS | completed business days before decision date | NO | YES |
| Renewed opportunity qualification | `portfolio_construction._reentry_recovery_evidence` | PC | canonical opportunity rank | PASS / FAIL / UNKNOWN | `reentry_opportunity_not_requalified`, `reentry_rank_missing` | PASS | current opportunity artifact | NO | YES |
| BUY quality requalification | `portfolio_construction._reentry_recovery_evidence` | PC consumer of BUY Quality | quality action | pass or block re-entry | `reentry_buy_quality_not_requalified`, `reentry_buy_quality_action_missing` | PASS | current BUY Quality artifact | NO | YES |
| Corporate-action current status | `portfolio_construction._corporate_action_evidence` | PC consumer of CA evidence | current CA status/source | pass/block/review | `reentry_corporate_action_blocking`, `reentry_corporate_action_source_missing` | PASS | current corporate-action artifact | NO | YES |
| Capacity/liquidity | `portfolio_construction._reentry_recovery_evidence` and low-price guard | PC | proposed notional, rolling median value | pass/block/review/cap | `reentry_capacity_unavailable`, low-price cap reasons | PASS | current PIT row fields | PARTIAL | YES |
| Prior exit reason class | `portfolio_construction._previous_exit_reason_class` | PC | prior exit reason/codes | context-sensitive recovery hurdle | prior-exit/current evidence reason codes | PASS | persisted prior PM/ledger context only | NO | YES |
| Repeated churn evidence | `portfolio_construction._reentry_recovery_evidence` | PC | prior same-symbol exit count, trend/momentum/admission | block unresolved repeated churn | `reentry_repeated_unresolved_churn` | PASS | current row plus prior count | NO | YES |
| Technical recovery | `portfolio_construction._reentry_recovery_evidence` | PC | trend over MA, momentum | pass/block/review | technical recovery reason codes | PASS | current technical evidence | NO | YES |
| Portfolio Construction admission | `portfolio_construction._resolve_target_weights` and G26 canonical contract | PC | selection, target weight, review/zero reason | participate or symbol-local reject | existing PC reasons plus canonical reason codes | PASS | current decision date | NO | YES before G26; normalized after G26 |
| Runtime Pending/review | Runtime planning/submit consumers | Runtime/Submit | PC target artifact | downstream only | n/a | PASS | after PC artifact | NO | NO |
| Same-symbol blacklist | searched current PC/PM implementation | none found as authoritative blacklist | n/a | n/a | n/a | n/a | n/a | NO | NO |

CURRENT_REENTRY_GATE_INVENTORY_COMPLETE = YES

## Blanket-like Composition

BLANKET_REENTRY_BAN_PRESENT = NO

BLANKET_LIKE_COMPOSITION_PRESENT = PARTIAL

No explicit same-symbol permanent blacklist was found. The pre-G26 behavior did, however, compose cooldown, prior exit context, current opportunity, BUY Quality, corporate-action, capacity, entry-admission, and recovery evidence into direct zero-weight decisions without one canonical semantic result naming whether PC had decided `REENTRY_NOT_ELIGIBLE` versus `REENTRY_INSUFFICIENT_EVIDENCE`. G26 keeps those PIT inputs but routes them through a single PC-owned eligibility result.

## Legacy Migration Matrix

| Legacy gate | G26 disposition |
| --- | --- |
| Prior holding identity | KEEP |
| Prior EXIT date identity | MIGRATE |
| Existing cooldown threshold | KEEP as input |
| Recovery hurdle | MIGRATE |
| BUY Quality requalification | MIGRATE as current evidence input |
| Corporate-action re-entry block/review | MIGRATE as safety/current evidence input |
| Capacity/liquidity re-entry block/review | MIGRATE as current evidence input |
| Low-price allocation cap | KEEP, separate PC risk allocation authority |
| Existing member fields | KEEP for compatibility |
| Old direct cooldown/recovery branch as authority | DEPRECATE as authority; PC now consumes canonical semantic result |

REENTRY_LEGACY_MIGRATION_MATRIX_COMPLETE = YES

PERMANENT_REENTRY_LEGACY_FALLBACK_COUNT = 0

## Acceptance Results

RENEWED_EVIDENCE_PATH_IMPLEMENTED = YES

PRIOR_EXIT_PERMANENT_BAN = NO

FUTURE_REENTRY_INPUT_COUNT = 0

HISTORICAL_OUTCOME_REENTRY_INPUT_COUNT = 0

PAPER_LEDGER_REENTRY_INPUT_COUNT = 0

NEW_REENTRY_COOLDOWN_SELECTED = NO

EXISTING_COOLDOWN_RETUNED = NO

PRIOR_EXIT_CONTEXT_PIT_ONLY = YES

REENTRY_BYPASSES_CURRENT_CANDIDATE_ELIGIBILITY = NO

MARKET_QUALITY_DIRECTLY_SETS_REENTRY_QUANTITY = NO

RISK_PACING_AUTHORITATIVE_IN_G26 = NO

CHURN_PROTECTION_PRESERVED = YES

BLIND_IMMEDIATE_REENTRY_ENABLED = NO

PC_CONSUMES_CANONICAL_REENTRY_EVIDENCE = YES

POSITION_SIZING_DECIDES_REENTRY = NO

REENTRY_REJECTION_SCOPE = SYMBOL_LOCAL

GLOBAL_BUY_BLOCK_FROM_SINGLE_REENTRY_REJECTION = NO

ADD_BEHAVIOR_CHANGED = NO

REENTRY_BLOCKS_UNRELATED_ADD = NO

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_QUANTITY_AUTHORITY_CREATED = NO

LOT_FIRST_CONTRACT = PASS

SAFETY_AUTHORITY_CHANGED = NO

REENTRY_BYPASSES_SAFETY = NO

REENTRY_REASON_CODE_CONTRACT = PASS

REENTRY_TEMPORAL_CONTRACT = PASS

AS_OF_VIOLATION_COUNT = 0

DUPLICATE_REENTRY_AUTHORITY_COUNT = 0

DUPLICATE_AUTHORITY_COUNT = 0

G26_PRODUCTION_BEHAVIOR_CHANGE_CLASS = STRUCTURAL_ONLY_NO_DECISION_CHANGE

CANONICAL_SOT_CHANGED = NO

G26_DIFF_SCOPE = PASS

## Test Results

G26_FOCUSED_TESTS = PASS

REENTRY_REGRESSION = PASS

PC_REGRESSION = PASS

SIZING_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

FOCUSED_TEST_RESULTS =

- `python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py` = PASS, 115 passed
- `python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py` = PASS, 399 passed
- `env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py` = PASS
- `git diff --check` = PASS

Initial plain `python3 -m py_compile ...` failed only because macOS attempted to write bytecode under `/Users/negishi/Library/Caches/com.apple.python/...`, outside the writable sandbox. Re-running with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache` passed.

## Required Summary Output

PRIMARY_JUDGMENT = PHASE31_G26_REENTRY_SEMANTIC_ELIGIBILITY_MIGRATION_IMPLEMENTED_ACCEPTED

CURRENT_REENTRY_GATE_INVENTORY_COMPLETE = YES

BLANKET_REENTRY_BAN_PRESENT = NO

BLANKET_LIKE_COMPOSITION_PRESENT = PARTIAL

REENTRY_ELIGIBILITY_OWNER = PORTFOLIO_CONSTRUCTION

DUPLICATE_REENTRY_AUTHORITY_COUNT = 0

CANONICAL_REENTRY_SEMANTIC_RESULT_IMPLEMENTED = YES

REENTRY_STATES_IMPLEMENTED = REENTRY_NOT_APPLICABLE, REENTRY_ELIGIBLE, REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION, REENTRY_NOT_ELIGIBLE_PRIOR_EXIT_CONTEXT, REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE, REENTRY_NOT_ELIGIBLE_SAFETY, REENTRY_INSUFFICIENT_EVIDENCE

RENEWED_EVIDENCE_PATH_IMPLEMENTED = YES

PRIOR_EXIT_PERMANENT_BAN = NO

FUTURE_REENTRY_INPUT_COUNT = 0

HISTORICAL_OUTCOME_REENTRY_INPUT_COUNT = 0

PAPER_LEDGER_REENTRY_INPUT_COUNT = 0

NEW_REENTRY_COOLDOWN_SELECTED = NO

EXISTING_COOLDOWN_RETUNED = NO

PRIOR_EXIT_CONTEXT_PIT_ONLY = YES

REENTRY_BYPASSES_CURRENT_CANDIDATE_ELIGIBILITY = NO

MARKET_QUALITY_DIRECTLY_SETS_REENTRY_QUANTITY = NO

RISK_PACING_AUTHORITATIVE_IN_G26 = NO

CHURN_PROTECTION_PRESERVED = YES

BLIND_IMMEDIATE_REENTRY_ENABLED = NO

PC_CONSUMES_CANONICAL_REENTRY_EVIDENCE = YES

POSITION_SIZING_DECIDES_REENTRY = NO

REENTRY_REJECTION_SCOPE = SYMBOL_LOCAL

GLOBAL_BUY_BLOCK_FROM_SINGLE_REENTRY_REJECTION = NO

ADD_BEHAVIOR_CHANGED = NO

REENTRY_BLOCKS_UNRELATED_ADD = NO

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_QUANTITY_AUTHORITY_CREATED = NO

LOT_FIRST_CONTRACT = PASS

SAFETY_AUTHORITY_CHANGED = NO

REENTRY_BYPASSES_SAFETY = NO

REENTRY_REASON_CODE_CONTRACT = PASS

REENTRY_TEMPORAL_CONTRACT = PASS

AS_OF_VIOLATION_COUNT = 0

REENTRY_LEGACY_MIGRATION_MATRIX_COMPLETE = YES

PERMANENT_REENTRY_LEGACY_FALLBACK_COUNT = 0

G26_PRODUCTION_BEHAVIOR_CHANGE_CLASS = STRUCTURAL_ONLY_NO_DECISION_CHANGE

G26_FOCUSED_TESTS = PASS

REENTRY_REGRESSION = PASS

PC_REGRESSION = PASS

SIZING_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

DUPLICATE_AUTHORITY_COUNT = 0

CANONICAL_SOT_CHANGED = NO

G26_DIFF_SCOPE = PASS

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

HISTORICAL_RERUN_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION = Proceed to G27 only if the user accepts the G26 PC-owned re-entry semantic eligibility contract and wants to start ADD capital competition integration.
