# Phase32-K - Re-entry Context Materialization / Positive-Control Proof

## Executive Summary

Phase32-K concludes that the zero-capitalization semantic REENTRY plateau is not primarily a PM intent problem and not merely threshold calibration. The immediate PC gate is strict and intentionally fail-closed, but the critical defect is upstream context materialization: concrete PM exit reasons exist on sell decisions, while the prior-exit state supplied into BUY re-entry authority is reconstructed from execution fills that usually preserve only `source_decision_type = EXIT` and omit the PM `decision_reason` / `reason_codes`.

Consequently, PC sees `prior_exit_reason = EXIT` and `previous_exit_reason_class = GENERIC` for every observed semantic REENTRY row in the Spring and Plateau windows. That generic context both prevents reason-specific recovery and turns otherwise plausible renewed-entry rows into review/fail-closed rows.

The success path is reachable in unit tests and code, but no production-observed semantic REENTRY capitalization was found in the audited artifacts. Positive-control-worthy rows exist in the sense of BUY_NEW_ALLOWED, cooldown-passed, continuation/downside-passed, trend/momentum-recovered rows; they are still blocked by rank and/or generic prior-exit context. The repair boundary is therefore materialization-only before calibration work: carry authoritative PM exit reason/code evidence into strict-prior ledger/campaign prior-exit state, then re-audit without changing capital thresholds.

## Prior-Exit Lineage

The prior-exit supply path is:

1. `shadow_runtime._supply_prior_exit_state` reads `runtime_root / persistent_ledger / executions.jsonl`.
2. It calls `_resolve_prior_closed_campaigns_from_executions`.
3. It attaches only derived prior-exit fields to candidate/opportunity summaries.
4. PC consumes those fields via `_previous_exit_reason`, `_previous_exit_reason_class`, `_semantic_reentry_evidence`, and `_reentry_recovery_evidence`.

Relevant code:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1205-1214` reads execution history and attaches prior-exit state to candidate/opportunity summaries.
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1898-1911` chooses the prior-exit reason from execution-row fields, falling back through `source_decision_type`, `decision_type`, `source_decision`, then `"EXIT"`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1915-1920` reads `prior_exit_reason`, `previous_exit_reason`, `last_exit_reason`, `source_decision_type`, or `decision_type`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1923-1940` classifies bare `EXIT` as `GENERIC`.

The lineage is PIT-safe and symbol-local, but it is lossy.

## GENERIC Root Cause

Observed concrete examples show the root cause directly:

- `2022-10-04 / 83060`: `position_management/pm_decisions.json` has `decision_reason = trend_and_opportunity_broken` and `reason_codes = ["trend_and_opportunity_broken"]`; `execution/fills.json` and `execution/realized_slices.json` retain only `source_decision_type = EXIT`.
- `2023-09-25 / 24680`: PM has the same concrete trend/opportunity-broken evidence; execution/realized-slice rows retain only `EXIT`.
- `2023-04-05 / 54010` and `2023-07-18 / 37780`: same pattern.
- `2022-12-29 / 15140`: PM decision is `REDUCE` with `risk_increased_but_trend_not_broken`, while execution source fields are `MISSING`; downstream still materializes generic context rather than a detailed sell/close rationale.

This explains why Phase32-J saw:

- Spring semantic REENTRY rows: `978`, selected `0`, prior class `GENERIC = 978`.
- Plateau semantic REENTRY rows: `3,522`, selected `0`, prior class `GENERIC = 3,522`.

The all-GENERIC result is not because PM never produced detailed reasons. It is because the prior-exit materialization path uses execution rows as the authority and the execution rows do not carry the detailed PM exit reason/codes needed by PC re-entry semantics.

## Shadow Exit Taxonomy Reconstruction

If the PM reason/code evidence had been preserved, examples would classify as:

- `trend_and_opportunity_broken` -> `TREND_MOMENTUM` under PC classifier tokens `TREND`, `MOMENTUM`, `EDGE_BREAK`, `OPPORTUNITY_BROKEN`, `WEAKEN`.
- `risk_increased_but_trend_not_broken` would at minimum not be a bare `EXIT`; the present classifier may still need a controlled mapping decision, but it has semantic content that should not be collapsed before re-entry authority.

The current execution-only bridge reconstructs close events correctly but reconstructs exit taxonomy poorly. Campaign closure exists; reason taxonomy is the missing materialized fact.

## Requalification Failure Decomposition

For Plateau final target-zero rows where the blocker is `reentry_opportunity_not_requalified`, the audited de-duplicated row set is:

- Final target-zero `reentry_opportunity_not_requalified`: `2,459`.
- `opportunity_rank_gt_10`: `2,459 / 2,459`.
- `generic_prior_exit_context`: `2,459 / 2,459`.
- `safety_not_pass`: `2,459 / 2,459`, generally downstream of semantic recovery failure text.
- `capacity_not_pass`: `192 / 2,459`.
- `repeated_generic_churn_condition`: `171 / 2,459`.
- Entry action: `BUY_NEW_REDUCED_ONLY = 2,409`, `BUY_NEW_ALLOWED = 50`.
- Rank buckets: `11-20 = 697`, `>20 = 1,762`.

The primary code-order subcause for the `2,459` final zero rows is rank: `_reentry_recovery_evidence` appends `reentry_opportunity_not_requalified` when `rank > 10`, and returns the first failure. However, the all-GENERIC prior-exit context is a material co-cause because it prevents reason-specific recovery and causes otherwise stronger rows to fail as insufficient context or unresolved churn.

## Positive-Control Analysis

Expected positive-control-like rows exist, but they split into two groups:

1. Rank-blocked but current-evidence-positive rows.
   Examples:
   - `2024-01-11 / 83060`: rank `16`, `BUY_NEW_ALLOWED`, continuation `PASS`, downside `PASS`, trend/momentum recovery `PASS`, prior reason `EXIT`, class `GENERIC`, target `0`.
   - `2024-01-15 / 24680`: rank `26`, `BUY_NEW_ALLOWED`, continuation/downside `PASS`, trend/momentum recovery `PASS`, prior reason `EXIT`, class `GENERIC`, target `0`.
   - `2024-01-23 / 15140`: rank `18`, `BUY_NEW_ALLOWED`, continuation/downside `PASS`, trend/momentum recovery `PASS`, prior reason `EXIT`, class `GENERIC`, target `0`.

2. Rank-passed but prior-context-blocked rows.
   Example:
   - `2024-01-31 / 83060`: rank `8`, `BUY_NEW_ALLOWED`, `FULL_ALLOCATION_ELIGIBLE`, continuation/downside `PASS`, trend/momentum recovery `PASS`, cooldown `PASS`, but prior reason `EXIT`, class `GENERIC`, recovery `insufficient_prior_exit_context`, target `0`.

Thus positive controls are not clean pass rows under the current contract, but they are strong enough to prove that the machinery is blocking rows that current BUY admission would otherwise allow.

## Success-Path Reachability

The success path is reachable in code:

- `_semantic_reentry_evidence` emits `semantic_buy_type = REENTRY` when a prior exit date is strict-prior and the symbol is not currently held.
- `_reentry_recovery_evidence` can return `reentry_recovery_status = PASS`.
- `_canonical_reentry_semantic_eligibility` returns `REENTRY_ELIGIBLE` when temporal, cooldown, recovery, current candidate, and safety gates pass.

Unit tests prove this:

- `tests/strategy/test_phase22_e_portfolio_construction.py:2900-2936` has row `22220` with detailed prior reason `EXIT_BY_TREND_AND_EDGE_BREAK`, cooldown pass, recovery pass, `REENTRY_ELIGIBLE`, and positive target weight.
- `tests/strategy/test_phase22_e_portfolio_construction.py:2957-2980` confirms a normal-capacity REENTRY row can keep positive target weight.

Production observation differs:

- Spring semantic REENTRY selected: `0 / 978`.
- Plateau semantic REENTRY selected: `0 / 3,522`.
- Existing PC artifacts show no selected semantic REENTRY rows.

So success is code-reachable but production-unobserved in the audited windows.

## Spring vs Plateau

Spring:

- Semantic REENTRY: `978`.
- Selected semantic REENTRY: `0`.
- Recovery reasons: `reentry_opportunity_not_requalified = 779`, `insufficient_prior_exit_context = 152`, `reentry_repeated_unresolved_churn = 47`.
- Final target-zero reasons include `reentry_opportunity_not_requalified = 696`, `insufficient_prior_exit_context = 144`, `reentry_minimum_cooldown_not_satisfied = 93`, `reentry_repeated_unresolved_churn = 45`.
- Prior class: `GENERIC = 978`.

Plateau:

- Semantic REENTRY: `3,522`.
- Selected semantic REENTRY: `0`.
- Recovery reasons: `reentry_opportunity_not_requalified = 2,758`, `insufficient_prior_exit_context = 425`, `reentry_repeated_unresolved_churn = 339`.
- Final target-zero reasons include `reentry_opportunity_not_requalified = 2,459`, `insufficient_prior_exit_context = 397`, `reentry_minimum_cooldown_not_satisfied = 339`, `reentry_repeated_unresolved_churn = 327`.
- Prior class: `GENERIC = 3,522`.

The pattern amplifies during Plateau but does not change character. This is systemic, not a single-date anomaly.

## Capital Impact

The capital impact is material because semantic REENTRY became a large fraction of NEW-like deployment supply and none was capitalized. In Plateau, PC carried `3,125` `REENTRY_BLOCK` rows at the PC zero-reason level, while Phase32-J also observed excess cash and NEW deployment suppression. The blocked rows include current-admitted opportunities with normal target weights around `3%` to `4%` on focus dates; once blocked, Cash commonly remains the final winner.

This report does not estimate counterfactual PnL or run a replay. It only establishes that eligible-looking capital candidates were systematically converted to zero by the re-entry bridge/gate.

## Residual Interaction

Residual reconsideration remains only partially integrated. Some rows were marked `AUTHORITATIVE_PC_RESIDUAL_RECONSIDERATION_BOUND` and `authorized_for_position_sizing = true`, while `authorized_for_runtime_order = false` and the artifact-level multi-allocation status remained shadow/non-authoritative with single-path trading still authoritative.

This is not the primary root cause of all-GENERIC re-entry context, but it is material because blocked REENTRY and residual allocation can both suppress deployable NEW capital while still failing to create authoritative trading orders.

## Defect / Limitation Classification

Classification:

- Context materialization defect: YES.
- Calibration limitation: PARTIAL.
- Intended fail-closed behavior: PARTIAL.

The fail-closed PC gate is defensible when prior-exit context is genuinely unknown. It is not defensible as a final production state when detailed PM evidence exists upstream and is dropped before re-entry authority. Rank `>10` is a real strictness/calibration question, but `2024-01-31 / 83060` proves there are rank-passed, current-evidence-positive rows blocked specifically by generic prior context.

## Repair Readiness

Production repair is justified, but implementation should be bounded:

1. Materialize detailed prior-exit reason and reason codes from authoritative strict-prior PM / SELL decision evidence into ledger-derived closed-campaign state.
2. Preserve PIT selection and symbol-local contract.
3. Keep PC re-entry thresholds unchanged for the first repair.
4. Add positive-control tests where PM reason codes survive into `previous_exit_reason_class = TREND_MOMENTUM` and a rank-passed renewed row reaches `REENTRY_ELIGIBLE`.
5. Re-audit Spring/Plateau artifacts only after the bridge is repaired.

Do not start by loosening rank thresholds or converting Runtime into a re-decision owner.

## Next Step

Implement a minimal re-entry context bridge repair: strict-prior PM decision evidence should be joined to execution-derived campaign closure by `source_decision_id`, `position_campaign_id`, `symbol`, and business date, then supplied to candidate/opportunity summaries as detailed `prior_exit_reason` and `prior_exit_reason_codes`. After that, run a narrow positive-control verification, then a fresh artifact audit.

## Final Judgments

```text
PHASE32_K_GENERIC_EXIT_REASON_ROOT_CAUSE = execution-derived prior-exit state falls back to bare source_decision_type/EXIT because detailed PM decision_reason and reason_codes are not carried into fills/realized-slices or joined back during prior-exit materialization
PHASE32_K_DETAILED_EXIT_EVIDENCE_EXISTS_UPSTREAM = YES
PHASE32_K_EXIT_CONTEXT_LOST_BEFORE_REENTRY = YES
PHASE32_K_REENTRY_NOT_REQUALIFIED_PRIMARY_SUBCAUSE = opportunity_rank_gt_10 for the 2459 final target-zero rows, with generic_prior_exit_context as a material co-cause
PHASE32_K_EXPECTED_POSITIVE_CONTROLS_FOUND = YES
PHASE32_K_EXPECTED_POSITIVE_CONTROLS_BLOCKED = YES
PHASE32_K_REENTRY_SUCCESS_PATH_CODE_REACHABLE = YES
PHASE32_K_REENTRY_SUCCESS_PATH_PRODUCTION_OBSERVED = NO
PHASE32_K_PRIOR_EXIT_CONTEXT_MATERIALIZATION_DEFECT = YES
PHASE32_K_REENTRY_CALIBRATION_LIMITATION = PARTIAL
PHASE32_K_REENTRY_CONTRACT_TOO_STRICT = PARTIAL
PHASE32_K_RESIDUAL_AUTHORITY_GAP_MATERIAL = PARTIAL
PHASE32_K_PRIMARY_ROOT_CAUSE = detailed PM exit taxonomy is not materialized into strict-prior re-entry authority, causing all production semantic REENTRY rows to arrive at PC as GENERIC prior exits and fail closed
PHASE32_K_MANDATORY_DEFECT = YES
PHASE32_K_PRODUCTION_REPAIR_JUSTIFIED = YES
PHASE32_K_IMPLEMENTATION_READY = NO
PHASE32_K_MINIMAL_REPAIR_BOUNDARY = prior-exit context materialization bridge only; no threshold, capital competition, PM, PC, PS, Risk Pacing, or Runtime authority change
PHASE32_K_NEXT_STEP = add a PIT-safe PM/SELL reason-code bridge into prior-exit state, prove with positive-control unit tests, then re-audit production artifacts
```
