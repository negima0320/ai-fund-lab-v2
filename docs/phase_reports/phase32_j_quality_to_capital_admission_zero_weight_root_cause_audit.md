# Phase32-J — Quality-to-Capital Admission / Zero-Weight Root Cause Audit

## Executive Summary

This audit is read-only. No production code, configuration, thresholds, model logic, PM, PC, MCC, Risk Pacing, PS, Runtime behavior, fresh run, resume, replay, or long/full historical backtest was changed or executed.

Phase32-I found that high Cash on Healthy-BULL focus dates comes from securities failing to become `COMPETITOR_SELECTED + accepted_weight > 0`. Phase32-J narrows that result: the largest producer of zero accepted NEW weight is semantic re-entry blocking, followed by residual reconsideration candidates whose first-pass authoritative accepted weight remains zero.

The code is not a literal blanket re-entry ban. It is a context-dependent PC semantic re-entry authority with a 3-business-day cooldown, prior-exit context checks, current opportunity requalification, entry-admission checks, continuation/downside checks, safety/liquidity checks, and PIT-only provenance. However, in the inspected historical artifact set, semantic re-entry behaves as an effective broad suppressor: all detected semantic `REENTRY` NEW competitors in both Spring and Plateau had zero selected accepted weight.

Key period facts from existing daily artifacts:

| period | days | NEW competitors | selected NEW | selected rate | accepted NEW weight | zero rate | REENTRY_BLOCK | residual reconsideration |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Spring 2023-02-27..2023-05-30 | 63 | 1,273 | 168 | 13.20% | 13.683331 | 86.80% | 834 | 148 |
| Plateau 2023-05-31..2024-02-26 | 182 | 4,058 | 377 | 9.29% | 23.828256 | 90.71% | 3,125 | 417 |

The selected NEW rate falls from 13.20% to 9.29%, while re-entry blocks rise in absolute count and remain the dominant zero-weight cause.

## Zero-Weight Taxonomy

### Period-Level PC Competitor Reasons

| period | zero reason | count | share of zero NEW |
|---|---|---:|---:|
| Spring | REENTRY_BLOCK | 834 | 75.48% |
| Spring | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | 148 | 13.39% |
| Spring | VALID_SAFETY_RESERVE | 57 | 5.16% |
| Spring | LOT_RESIDUAL | 44 | 3.98% |
| Spring | CONCENTRATION_BLOCK | 22 | 1.99% |
| Plateau | REENTRY_BLOCK | 3,125 | 84.89% |
| Plateau | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | 417 | 11.33% |
| Plateau | LOT_RESIDUAL | 64 | 1.74% |
| Plateau | VALID_SAFETY_RESERVE | 56 | 1.52% |
| Plateau | CONCENTRATION_BLOCK | 19 | 0.52% |

### Target-Weight Zero Reasons

| period | zero-weight producer reason | count |
|---|---|---:|
| Spring | `reentry_opportunity_not_requalified` | 696 |
| Spring | `insufficient_prior_exit_context` | 144 |
| Spring | `reentry_minimum_cooldown_not_satisfied` | 93 |
| Spring | `minimum_lot_exceeds_remaining_budget` | 64 |
| Spring | `minimum_lot_exceeds_safety_hard_cap` | 57 |
| Spring | `reentry_repeated_unresolved_churn` | 45 |
| Plateau | `reentry_opportunity_not_requalified` | 2,459 |
| Plateau | `insufficient_prior_exit_context` | 397 |
| Plateau | `reentry_minimum_cooldown_not_satisfied` | 339 |
| Plateau | `reentry_repeated_unresolved_churn` | 327 |
| Plateau | `minimum_lot_exceeds_remaining_budget` | 73 |
| Plateau | `minimum_lot_exceeds_safety_hard_cap` | 55 |

The label `REENTRY_BLOCK` is mostly not cooldown. In Plateau, cooldown explains 339 rows; current-evidence recovery/requalification explains 2,459 rows, insufficient prior context explains 397, and repeated unresolved churn explains 327.

## REENTRY_BLOCK Causality

Producer: `PORTFOLIO_CONSTRUCTION_SEMANTIC_REENTRY_AUTHORITY`.

Code path:

- `_phase29_l16_observable_fields` carries prior-exit and corporate-action fields into portfolio members: `portfolio_construction.py:1141` through `portfolio_construction.py:1175`.
- `_resolve_low_price_reentry_allocation_guard` calls semantic re-entry, recovery, and eligibility checks before final target weight is persisted: `portfolio_construction.py:1178` through `portfolio_construction.py:1251`.
- If a non-current `ADD_CANDIDATE` is semantic `REENTRY` and eligibility does not pass, final target weight becomes zero: `portfolio_construction.py:1263` through `portfolio_construction.py:1278`.
- `_semantic_reentry_evidence` classifies re-entry from same-symbol prior exit before current business date and applies a 3BD cooldown: `portfolio_construction.py:1394` through `portfolio_construction.py:1421`.
- `_reentry_recovery_evidence` checks rank, buy quality action, corporate-action status, capacity, entry admission, continuation quality, downside risk, repeated churn, and prior-exit class: `portfolio_construction.py:1424` through `portfolio_construction.py:1544`.
- `_canonical_reentry_semantic_eligibility` then gates prior-exit temporal validity, cooldown, recovery, current candidate eligibility, and safety: `portfolio_construction.py:1547` through `portfolio_construction.py:1695`.
- `_capital_constraint_reason_code` maps reentry text in the target-weight reason/zero reason to the final competitor reason `REENTRY_BLOCK`: `portfolio_construction.py:6088` through `portfolio_construction.py:6105`.

Field chain:

`prior_exit_business_date < business_date` -> `semantic_buy_type = REENTRY` -> cooldown/recovery/current/safety checks -> failing status or review-required status -> `target_weight = 0` -> `requested_buy_new_weight = 0` -> `accepted_buy_new_weight = 0` -> `lot_aware_accepted_buy_new_weight = 0` -> `competitor.status = COMPETITOR_REJECTED_RECONSIDERABLE` -> `reason_codes = [REENTRY_BLOCK]`.

## Re-Entry Contract Audit

The source code is context-dependent, not an unconditional fixed ban:

- Cooldown is fixed at 3 business days, but cooldown alone is not the only gate.
- Re-entry requires same-symbol prior exit context and current positive candidate evidence.
- Rows can pass cooldown yet still fail recovery, prior context, safety, or current candidate eligibility.
- The constraint scope emitted by successful/failing semantic re-entry is `SYMBOL_LOCAL`, not portfolio-wide.
- `BUY_NEW_ALLOWED` is an entry-admission signal, not a re-entry override. It can coexist with `REENTRY_BLOCK` when prior-exit/recovery context fails.

The artifact behavior is still material. In the inspected run:

| period | semantic REENTRY rows | selected semantic REENTRY | cooldown pass | cooldown fail | prior-exit class |
|---|---:|---:|---:|---:|---|
| Spring | 978 | 0 | 885 | 93 | GENERIC 978 |
| Plateau | 3,522 | 0 | 3,183 | 339 | GENERIC 3,522 |

This is not a code-level blanket ban, but it is a practical suppression pattern in the current artifacts. The dominant issue is that prior exits are represented as generic `EXIT`, which leaves the re-entry authority unable to establish a differentiated “genuine recovery” state. The result is often `reentry_opportunity_not_requalified`, `insufficient_prior_exit_context`, or `reentry_repeated_unresolved_churn`.

## Blocked vs Successful Re-Entry Comparison

No successful semantic `REENTRY` competitor with `COMPETITOR_SELECTED` was found in the inspected historical artifact set. That absence is itself a material positive-control failure.

Blocked examples on focus dates:

| date | symbol | class | rank | score | entry | prior exit | days since exit | prior reason class | cooldown | recovery | zero reason | final |
|---|---|---|---:|---:|---|---|---:|---|---|---|---|---|
| 2024-01-11 | 83060 | COMPARABLE_HIGH | 16 | -0.277717 | BUY_NEW_ALLOWED | 2022-10-04 | 331 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-15 | 83060 | COMPARABLE_HIGH | 17 | -0.246007 | BUY_NEW_ALLOWED | 2022-10-04 | 333 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-15 | 24680 | COMPARABLE_HIGH | 26 | -0.427445 | BUY_NEW_ALLOWED | 2023-09-25 | 79 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-15 | 54010 | COMPARABLE_HIGH | 34 | -0.502588 | BUY_NEW_ALLOWED | 2023-04-05 | 202 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-23 | 15140 | STRONG | 18 | -0.230007 | BUY_NEW_ALLOWED | 2022-12-29 | 277 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-23 | 37780 | COMPARABLE_HIGH | 20 | -0.266984 | BUY_NEW_ALLOWED | 2023-07-18 | 134 | GENERIC | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | Cash wins |
| 2024-01-31 | 83060 | COMPARABLE_HIGH | 8 | -0.078285 | BUY_NEW_ALLOWED | 2022-10-04 | 345 | GENERIC | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | NEW 92490 wins; 83060 zero |

Successful controls are available for NEW deployment generally, but not for semantic REENTRY. Low-cash positive-control NEW deployment dates show that PC/MCC can select NEW when accepted weight survives:

| date | selected NEW | selected symbols | PC/MCC winner | executed BUY notional |
|---|---:|---|---|---:|
| 2023-06-14 | 4 | 24020, 38450, 95650, 40150 | NEW_BUY 95650 | 172,700 |
| 2023-06-15 | 4 | 40520, 76920, 33230, 92630 | NEW_BUY 40520 | 290,900 |
| 2023-06-16 | 3 | 68360, 36240, 40730 | NEW_BUY 40730 | 108,170 |
| 2023-06-19 | 3 | 76920, 70460, 39090 | NEW_BUY 70460 | 49,900 |
| 2023-09-01 | 2 | 66770, 48240 | NEW_BUY 66770 | 31,600 |
| 2023-09-05 | 4 | 98120, 75240, 39250, 70930 | NEW_BUY 39250 | 59,100 |

The missing control is narrower: “same-symbol semantic re-entry can pass.” That should be treated as an observability and calibration gap before any production change.

## Residual Reconsideration Causality

Producer: `PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION` plus `canonical_residual_reconsideration_shadow.v1` / `canonical_residual_reconsideration_authoritative_binding.v1`.

Why first-pass accepted weight is zero:

- For many residual rows, semantic re-entry already made `target_weight = 0`, `requested_buy_new_weight = 0`, and `accepted_buy_new_weight = 0`.
- Competitor accepted weight uses `lot_aware_accepted_buy_new_weight` when lot reallocation evidence exists: `portfolio_construction.py:5859` through `portfolio_construction.py:5878`.
- If that lot-aware accepted value is zero, PC marks the competitor rejected/reconsiderable.

Residual capital source:

- Residual cash comes from available incremental budget not consumed by selected securities, plus lot/executability constraints.
- Lot-aware reallocation scans participants, checks pre-lot MCC binding, feasibility, one-lot admission, concentration, and remaining budget: `portfolio_construction.py:6668` through `portfolio_construction.py:7035`.
- Final member target and lot-aware accepted BUY_NEW weight are then persisted from `accepted_by_index`: `portfolio_construction.py:7095` through `portfolio_construction.py:7228`.

Reconsideration behavior:

- Residual reconsideration only admits rows with `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`, not arbitrary re-entry blocked rows: `portfolio_construction.py:4729` through `portfolio_construction.py:4743`.
- It reconstructs a shadow request from member fields such as normal target weight, final risk-adjusted target weight, target weight, and competitor requested/accepted weights: `portfolio_construction.py:4768` through `portfolio_construction.py:4810`.
- It can bind positive PC residual allocations while preserving optional Cash and disallowing runtime priority redecision: `portfolio_construction.py:4700` through `portfolio_construction.py:4724`.
- Multi-allocation remains globally `SHADOW_NON_AUTHORITATIVE`, `authoritative_consumer_count = 0`, `trading_consumer_connected = false`, and `single_path_remains_only_authoritative_trading_path = true`, even when residual rows carry `AUTHORITATIVE_PC_RESIDUAL_RECONSIDERATION_BOUND`.

Thus residual reconsideration is partially complete: the PC residual binding exists, but the final trading path remains single-winner and runtime-disconnected.

## Authoritative vs Shadow Comparison

Focus rows where authoritative competitor accepted weight is zero but residual/shadow allocation is positive:

| date | symbol | class | rank | score | PC reason | zero reason | residual allocation | lot status | runtime order |
|---|---|---|---:|---:|---|---|---:|---|---|
| 2024-01-11 | 67310 | CM | 2 | 0.427934 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.037037 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-11 | 95010 | CM | 4 | 0.223461 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.037037 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-11 | 24590 | CM | 7 | -0.047466 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.037037 | LOT_EXECUTABLE_COMPATIBLE | false |
| 2024-01-11 | 91070 | CM | 8 | -0.073152 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.037037 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-23 | 67310 | CM | 3 | 0.135433 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.043478 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-23 | 24020 | CM | 7 | 0.078074 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.043478 | LOT_EXECUTABLE_COMPATIBLE | false |
| 2024-01-23 | 48910 | CM | 10 | -0.110305 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.043478 | LOT_EXECUTABLE_COMPATIBLE | false |
| 2024-01-24 | 24020 | CM | 8 | 0.043803 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.041667 | LOT_EXECUTABLE_COMPATIBLE | false |
| 2024-01-31 | 83060 | CH | 8 | -0.078285 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.031250 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-31 | 67310 | CM | 4 | 0.194672 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.031250 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-31 | 91070 | CM | 9 | -0.134898 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.031250 | LOT_INFEASIBLE_RESIDUAL_REQUIRED | false |
| 2024-01-31 | 48910 | CM | 10 | -0.175354 | REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION | insufficient_prior_exit_context | 0.031250 | LOT_EXECUTABLE_COMPATIBLE | false |

The divergence is not that shadow has better alpha evidence. It uses different authority semantics: residual reconsideration re-enters specific reconsiderable rows as bounded residual participants. It preserves Cash and does not authorize runtime orders. The authoritative single MCC path still requires the original competitor to have positive accepted weight before it can defeat Cash or become the single deployment winner.

## Spring vs Plateau

Spring worked better not because re-entry was healthy, but because more non-reentry NEW deployment survived despite the same re-entry suppressor.

| metric | Spring | Plateau | interpretation |
|---|---:|---:|---|
| NEW selected rate | 13.20% | 9.29% | Plateau admits fewer NEW competitors into capital |
| zero-weight rate | 86.80% | 90.71% | Plateau zero-weight pressure rises |
| REENTRY_BLOCK share of zero NEW | 75.48% | 84.89% | Re-entry suppressor becomes more dominant |
| residual reconsideration share of zero NEW | 13.39% | 11.33% | residual issue remains material but secondary |
| semantic REENTRY pass count | 0 | 0 | no positive semantic re-entry control in either period |
| BUY_NEW_ALLOWED high/strong zero rows | 19 | 87 | high-quality/admitted zero rows increase materially |

The time-series explanation for later Cash preference is therefore:

1. Candidate supply remains material.
2. Many repeated same-symbol candidates are classified as semantic `REENTRY`.
3. Prior-exit context is often generic and current requalification is often insufficient.
4. Those rows become target-weight zero before capital competition.
5. Residual reconsideration can expose bounded allocations, but does not fully replace the single authoritative trading path.
6. Fewer selected NEW competitors survive; Cash remains the first-class residual winner.

## Root-Cause Ranking

| rank | cause | judgment | evidence |
|---:|---|---|---|
| 1 | REENTRY_BLOCK materiality | YES | 3,125 Plateau zero NEW rows, 84.89% of zero NEW. |
| 2 | Capital admission limitation | YES | Quality/admission-positive candidates can still have `target_weight = 0`, requested/accepted zero. |
| 3 | Prior-exit context observability gap | YES | All semantic reentries have `previous_exit_reason_class = GENERIC`; no selected semantic reentry controls found. |
| 4 | Residual realallocation limitation | YES | Residual rows can bind PC residual participation but do not fully connect to runtime orders. |
| 5 | Authoritative/shadow gap | YES | `authorized_for_position_sizing = true` appears on residual-bound rows while `authorized_for_runtime_order = false` and top-level multi allocation remains non-authoritative. |
| 6 | Blanket re-entry suppression | PARTIAL | Not literal in code; practical artifact result is zero selected semantic reentry. |
| 7 | Mandatory production defect | UNRESOLVED | Behavior is highly material but could reflect conservative contract plus missing context rather than an implementation bug. |

## Defect / Limitation Classification

| classification | judgment | rationale |
|---|---|---|
| NO_DEFECT | PARTIAL | No direct wrong denominator, stale authority, future leakage, or explicit contract violation found. |
| REENTRY_CONTRACT_DEFECT | UNRESOLVED | Code is context-dependent, but no successful semantic reentry exists in inspected artifacts. |
| REENTRY_CALIBRATION_LIMITATION | YES | Rank/recovery/prior-context gates appear too restrictive or under-informed for repeated candidates. |
| RESIDUAL_REALLOCATION_LIMITATION | YES | Residual pathway is materially useful but not complete as final trading authority. |
| AUTHORITATIVE_SHADOW_GAP | YES | Residual/shadow allocations diverge from single-path competitor accepted weight and runtime order authority. |
| CAPITAL_ADMISSION_LIMITATION | YES | Quality-valid candidates do not have an adequate bridge to small positive accepted capital. |
| OBSERVABILITY_GAP | YES | Competitor summaries hide important re-entry fields; member rows must be joined to explain zero weight. |

## Repair Readiness

Production repair is not implementation-ready from this audit alone. A narrow repair may be justified after one more shadow/spec step if it proves either:

- prior-exit reason/context is unintentionally collapsed to generic `EXIT`;
- semantic re-entry was intended to have successful positive controls but the current pipeline cannot produce any;
- residual reconsideration was intended to reach final trading authority but remains disconnected;
- high-quality `BUY_NEW_ALLOWED` re-entry rows are unintentionally zeroed despite complete re-entry evidence.

The safest next change is not to loosen re-entry or Cash directly. It is to build a shadow-only admission bridge that emits, for every zero-weight NEW/ADD row, a single joined explanation across:

`opportunity quality -> entry admission -> semantic reentry -> target_weight_resolution -> incremental budget -> lot-aware accepted weight -> competitor status -> MCC result -> residual reconsideration -> PS/runtime materialization`.

## Final Judgments

```text
PHASE32_J_ZERO_WEIGHT_PRIMARY_CAUSE = SEMANTIC_REENTRY_CURRENT_EVIDENCE_AND_PRIOR_CONTEXT_FAIL_CLOSED_BEFORE_CAPITAL_COMPETITION

PHASE32_J_REENTRY_BLOCK_MATERIAL = YES
PHASE32_J_REENTRY_BLOCK_CONTRACT_VALID = PARTIAL
PHASE32_J_BLANKET_REENTRY_SUPPRESSION = PARTIAL

PHASE32_J_RESIDUAL_RECONSIDERATION_MATERIAL = YES
PHASE32_J_RESIDUAL_RECONSIDERATION_AUTHORITATIVE_PATH_COMPLETE = PARTIAL

PHASE32_J_AUTHORITATIVE_SHADOW_GAP_MATERIAL = YES

PHASE32_J_STRONG_OR_HIGH_QUALITY_ZERO_WEIGHT_EXPLAINED = YES

PHASE32_J_CAPITAL_ADMISSION_LIMITATION = YES

PHASE32_J_MANDATORY_DEFECT = UNRESOLVED
PHASE32_J_PRODUCTION_REPAIR_JUSTIFIED = UNRESOLVED
PHASE32_J_IMPLEMENTATION_READY = NO

PHASE32_J_MINIMAL_REPAIR_BOUNDARY = SHADOW_ONLY_JOINED_ZERO_WEIGHT_ADMISSION_BRIDGE_AND_SEMANTIC_REENTRY_POSITIVE_CONTROL_VALIDATION
PHASE32_J_NEXT_STEP = PHASE32_K_REENTRY_CONTEXT_MATERIALIZATION_AND_RESIDUAL_AUTHORITY_CONNECTION_SHADOW_SPEC
```

