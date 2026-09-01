# Phase32-CO — Prior EXIT Semantic Provenance Production Repair

## Scope

This phase repairs only the semantic provenance defect confirmed by Phase32-CN:

`authoritative PM / closed-campaign EXIT semantics exist upstream, but REENTRY receives generic scalar EXIT`

No REENTRY cooldown, churn, rank, requalification, BQ, continuation/downside, hard-stop, BUY_NEW, BUY_ADD, PC/PS, model, feature, threshold, or capital allocation semantics were changed.

No target run, Pending, Ledger, replay, resume, recover, fresh-run, or runtime state was mutated.

## Root Cause Confirmation

`EXACT_COLLAPSE_SITE_IDENTIFIED = YES`

Collapse site:

- file: `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- function: `_resolve_prior_closed_campaigns_from_executions`
- prior behavior: scalar `prior_exit_reason` was selected from `pm_context.prior_exit_reason`, then ledger row fields such as `source_decision_type`, `decision_type`, and `source_decision`, falling back to `EXIT`.
- defect: when the semantic authority had meaningful reason codes but scalar reason was action-level `EXIT`, REENTRY consumed generic `EXIT` as the scalar prior reason.
- consumer impact: `portfolio_construction._reentry_recovery_evidence` treats scalar `previous_exit_reason in {"", "UNKNOWN", "EXIT", "SELL"}` as insufficient prior context. Therefore non-generic `prior_exit_reason_codes` could survive but still be overridden by generic scalar `EXIT`.

The earlier materialization function `_pm_exit_decision_context_event` also used `decision_reason or dominant_cause or decision_type`, which allowed `decision_type=EXIT` to become the scalar semantic reason even when reason codes contained the actual PM semantics.

## Repair

The repair adds a small canonical helper:

- `_semantic_prior_exit_reason(*candidates)`

It selects the first non-generic authoritative semantic string from:

- PM `decision_reason`
- PM `dominant_cause`
- PM / closed-campaign reason codes
- ledger semantic fields only as fallback

Generic action labels remain generic when no non-generic semantic authority exists:

- `EXIT`
- `SELL`
- `SELL_EXIT`
- `UNKNOWN`
- empty

Repaired propagation:

- `_pm_exit_decision_context_event` now uses the helper when materializing strict-prior PM EXIT context.
- `_resolve_prior_closed_campaigns_from_executions` now uses the helper with PM context and reason codes before ledger action labels.
- materialized prior context now exposes both scalar aliases:
  - `prior_exit_reason`
  - `previous_exit_reason`
- reason-code aliases are also preserved:
  - `prior_exit_reason_codes`
  - `previous_exit_reason_codes`
- PM source identity remains attached:
  - `source_pm_decision_id`
  - `source_decision_id`

This is a provenance repair, not a REENTRY gate relaxation. The existing REENTRY consumer, taxonomy, rank logic, cooldown, BQ, hard-stop thesis requirement, and fail-closed handling remain unchanged.

## Files Changed

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `docs/phase_reports/phase32_co_prior_exit_semantic_provenance_production_repair.md`

## Validation

Focused validation executed:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result:

```text
53 passed, 1 skipped
```

Compile validation executed with sandbox-safe pycache:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase32co_pycache PYTHONPATH=src python3 -m compileall -q \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py
```

Result: PASS.

Focused coverage added:

- TREND_MOMENTUM: non-generic PM reason code prevents generic `EXIT` scalar collapse and REENTRY recovery can consume the restored reason.
- CN representative cases: 73590, 59860, 65500, 67310, 65730 preserve recovered prior EXIT semantics and produce recovery PASS in the focused fixture.
- HARD_STOP: hard-stop semantic is retained, and stricter hard-stop new-thesis requirement remains active.
- GENERIC: genuinely generic prior EXIT remains generic and `REVIEW_REQUIRED`.
- Active churn: cooldown remains fail-closed.
- Weak current opportunity: rank/requalification failure remains blocked.
- CK/G129 adjacent regressions: PASS.

## Target Run Read-Only Assessment

The target run `runtime-test-historical-extended-smoke-20260831T234344371102Z` was inspected only as immutable historical evidence.

Old artifacts remain unchanged and still show pre-repair generic scalar evidence. Representative rows still contain:

- `prior_exit_reason = EXIT`
- `previous_exit_reason = EXIT`
- `reentry_recovery_status = REVIEW_REQUIRED`
- `reentry_recovery_reason = insufficient_prior_exit_context`

This is expected because CO does not rewrite historical artifacts. A new user-operated fresh Historical run is required to observe repaired actual-path runtime artifacts.

## Strategy Semantics

Strategy semantic change: NO.

This repair does not:

- loosen REENTRY eligibility;
- alter rank thresholds;
- alter cooldown;
- alter BQ;
- alter hard-stop recovery semantics;
- alter BUY_NEW or BUY_ADD;
- create a new component/model/feature;
- create symbol-only or cross-campaign provenance reconstruction.

## Required Final Answers

1. `EXACT_COLLAPSE_SITE_IDENTIFIED`: `YES`
2. `COLLAPSE_SITE_FILE`: `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
3. `COLLAPSE_SITE_FUNCTION`: `_resolve_prior_closed_campaigns_from_executions`; contributing materialization site `_pm_exit_decision_context_event`
4. `ROOT_CAUSE_CONFIRMED`: `YES`
5. `AUTHORITATIVE_PM_EXIT_REASON_PROPAGATED`: `YES`
6. `AUTHORITATIVE_REASON_CODES_PROPAGATED`: `YES`
7. `PM_SOURCE_DECISION_ID_PROPAGATED`: `YES`
8. `GENERIC_ACTION_EXIT_NO_LONGER_OVERRIDES_NON_GENERIC_SEMANTICS`: `YES`
9. `TREND_MOMENTUM_CASE_PASS`: `YES`
10. `HARD_STOP_CASE_PASS`: `YES`
11. `GENERIC_CASE_REMAINS_FAIL_CLOSED`: `YES`
12. `73590_REGRESSION_PASS`: `YES`
13. `59860_REGRESSION_PASS`: `YES`
14. `65500_REGRESSION_PASS`: `YES`
15. `67310_REGRESSION_PASS`: `YES`
16. `65730_REGRESSION_PASS`: `YES`
17. `ACTIVE_CHURN_PROTECTION_PRESERVED`: `YES`
18. `WEAK_CURRENT_OPPORTUNITY_REMAINS_BLOCKED`: `YES`
19. `CURRENT_REQUALIFICATION_FAILURE_REMAINS_BLOCKED`: `YES`
20. `HARD_STOP_NEW_THESIS_REQUIREMENT_PRESERVED`: `YES`
21. `GENUINE_BUY_NEW_UNCHANGED`: `YES`
22. `BUY_ADD_G129_UNCHANGED`: `YES`
23. `STRICT_PRIOR_CAMPAIGN_LINEAGE_PRESERVED`: `YES`
24. `SYMBOL_ONLY_JOIN_ADDED`: `NO`
25. `CAMPAIGN_REGENERATION_WORKAROUND_ADDED`: `NO`
26. `REENTRY_GATE_WEAKENED`: `NO`
27. `REENTRY_RANK_LOGIC_CHANGED`: `NO`
28. `REENTRY_COOLDOWN_CHANGED`: `NO`
29. `NEW_EQUIVALENT_RESET_SEMANTICS_ADDED`: `NO`
30. `NEW_COMPONENT_ADDED`: `NO`
31. `NEW_MODEL_ADDED`: `NO`
32. `NEW_FEATURE_ADDED`: `NO`
33. `TARGET_RUN_MUTATED`: `NO`
34. `RESUME_EXECUTED`: `NO`
35. `REPLAY_EXECUTED`: `NO`
36. `FRESH_RUN_EXECUTED`: `NO`
37. `FOCUSED_VALIDATION_PASS`: `YES`
38. `FUTURE_FRESH_VALIDATION_REQUIRED`: `YES`
39. `NEXT_RECOMMENDED_STEP`: user-operated fresh Historical validation to confirm actual-path artifacts now materialize non-generic prior EXIT scalar semantics; do not tune requalification gates until that evidence is accepted.
40. `FINAL_JUDGMENT`: `PHASE32_CO_PRIOR_EXIT_SEMANTIC_PROVENANCE_PRODUCTION_REPAIR_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_ACTUAL_PATH_VALIDATION_REQUIRED`

## Final Judgment

`PHASE32_CO_PRIOR_EXIT_SEMANTIC_PROVENANCE_PRODUCTION_REPAIR_ACCEPTED_FOCUSED_VALIDATION_PASS_FRESH_ACTUAL_PATH_VALIDATION_REQUIRED`
