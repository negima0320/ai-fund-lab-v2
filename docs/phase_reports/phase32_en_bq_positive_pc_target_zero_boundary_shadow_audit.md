# Phase32-EN — BQ-Positive → PC Target-Zero Boundary SHADOW Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Requested period: `2024-03-18` through latest available May-2024 evidence.
- Evidence coverage used at extraction time: `2024-03-18` through `2024-05-28`, 48 PC-complete business-date artifacts.
- Evidence used:
  - `strategy/portfolio_construction.json`
  - `strategy/buy_quality_decisions.json`
  - `strategy/market_context.json`
  - `strategy/portfolio_policy.json`
  - adjacent existing SHADOW/authority fields already materialized in PC members, including rank authority, Entry/REENTRY fields, no-buy reason classification, marginal capital fields, and reason codes.
- No new SHADOW artifact was required. No Production/SHADOW/source/config/runtime-state/Pending/Ledger mutation was executed.
- No future price, future return, later winner/loser outcome, campaign PnL, or Historical profitability was used.

## Method

Population filter:

- `quality_action in {FULL_ALLOCATION_ELIGIBLE, REDUCED_ALLOCATION_ONLY}`
- candidate/rank evidence present in PC member fields (`opportunity_buy_rank`, `opportunity_rank_preserved`, `rank_authority_status=PASS` where materialized)
- `target_weight <= 0`

Reason classification used only decision-time fields:

- Market/Risk: `regime_state`, `risk_pacing_intent`, `final_no_deployable_opportunity`
- Entry/BQ: `entry_admission_action`, `quality_action`, `reason_codes`
- Opportunity: `no_buy_reason_classification.no_buy_reason`, `hard_blocking_reasons`, `soft_relative_reasons`
- REENTRY: `reentry_*` fields and `reentry_*` reason codes
- Held/ADD: `current_position`, `membership_intent`, `pm_action`, `current_weight`, `target_weight`
- Lot/cap/headroom: `lot_first_feasibility_classification`, `allocation_cap_reason`, current vs target weight

## BQ_POSITIVE_PC_TARGET_ZERO_POPULATION

Total target-zero population:

- `1730` rows
- PC-complete period: `2024-03-18` through `2024-05-28`
- All rows were materialized in PC as `REDUCED_ALLOCATION_ONLY`.
- `119` of those rows carried upstream reason-code evidence that the pre-PC/BQ source had been `buy_quality_full_allocation_eligible` before later Entry/PC reduction or zeroing.

Relationship split:

| Relationship | Rows |
| --- | ---: |
| `REENTRY_LIKE` | 1697 |
| `HELD_POSITION` | 33 |
| Clean NEW-only unrelated-to-prior-position rows | 0 observed |

Membership split:

| Membership intent | Rows |
| --- | ---: |
| `ADD_CANDIDATE` | 925 |
| `EXCLUDE` | 772 |
| `REMOVE_CANDIDATE` | 33 |

Important interpretation:

- The target-zero boundary is overwhelmingly a prior-relationship / REENTRY-like boundary, not a generic fresh NEW candidate selection defect.
- The 33 held-position rows were not clean ADD capitalization misses; they were current/held rows with PM/PC membership such as `REMOVE_CANDIDATE` and target not greater than current weight.

## Zero Reason Decomposition

Primary reason counts:

| Primary reason | Rows |
| --- | ---: |
| `RISK_SUPPRESSED` | 809 |
| `NEGATIVE_EXPECTED_EDGE` | 503 |
| `ENTRY_BLOCKED` | 227 |
| `REENTRY_STRENGTH_NOT_REESTABLISHED` | 78 |
| `REENTRY_CHURN_PROTECTION` | 45 |
| `DOWNSIDE_RISK_BLOCKED` | 45 |
| `ADD_NOT_INCREMENTALLY_JUSTIFIED` | 23 |
| `LOT_INFEASIBLE` | 0 |
| `CAP_CONSTRAINED` | 0 primary; 1 secondary |
| `NO_INCREMENTAL_HEADROOM` | represented through `ADD_NOT_INCREMENTALLY_JUSTIFIED` for held rows |
| `NEW_SUPERIOR_IN_CAPITAL_COMPETITION` | 0 as primary after hard/relationship explanations |
| `OTHER_EXPLAINED` | 0 |
| `CLEAN_UNEXPLAINED_TARGET_ZERO` | 0 |

Secondary reason counts, non-exclusive:

| Secondary evidence | Rows |
| --- | ---: |
| `NEGATIVE_EXPECTED_EDGE` | 1429 |
| `REENTRY_STRENGTH_NOT_REESTABLISHED` | 1076 |
| `RISK_SUPPRESSED` | 809 |
| `REENTRY_CHURN_PROTECTION` | 518 |
| `ENTRY_BLOCKED` | 474 |
| `DOWNSIDE_RISK_BLOCKED` | 124 |
| `ADD_NOT_INCREMENTALLY_JUSTIFIED` | 33 |
| `CAP_CONSTRAINED` | 1 |

Common PIT reason codes:

- `selection_quality_caution_continuation`: 1534
- `reentry_repeated_unresolved_churn`: 249
- `reentry_unknown_prior_context_independence_not_established`: 238
- `reentry_hard_stop_new_thesis_not_sufficient`: 153
- `reentry_trend_recovery_not_satisfied`: 135
- `reentry_minimum_cooldown_not_satisfied`: 78
- `reentry_momentum_recovery_not_satisfied`: 20

Common no-buy reasons:

- `below_opportunity_top20|non_positive_expected_edge_score`: 951
- `non_positive_expected_edge_score`: 327
- `below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score`: 78
- `high_downside_risk_score|non_positive_expected_edge_score`: 43
- `high_downside_risk_score`: 3

## Clean Case Test

`CLEAN_UNEXPLAINED_TARGET_ZERO` required all of:

- PIT candidate evidence positive
- BQ positive
- no Entry hard block
- no Risk hard suppression
- positive expected edge
- no downside hard block
- executable lot possible
- position/campaign cap headroom
- cash available
- no churn / REENTRY safety violation
- no rational defeat by stronger available opportunity

Result:

- `CLEAN_TARGET_ZERO_CASE_COUNT = 0`

No row satisfied the clean-case definition. Every BQ-positive target-zero row had at least one contemporaneous explanation: defensive risk state, negative expected edge, downside risk, Entry/BQ wait state, REENTRY churn/strength/recovery constraint, or held-position non-incremental justification.

## Risk Separation

- `VALID_RISK_ZERO_COUNT = 809`
- `NON_RISK_TARGET_ZERO_COUNT = 921`

Risk-zero interpretation:

- `RISK_SUPPRESSED` was assigned only for BEAR/CORRECTION days, or for PC no-deployable-opportunity days under cautious/gradual deployment.
- Plain `CAUTIOUS_DEPLOYMENT` alone was not treated as a hard Risk reason. This avoids conflating defensive posture with an individual PC defect.

Non-risk target-zero interpretation:

- The 921 non-risk rows were still explained.
- Most were explained by expected-edge, REENTRY strength/churn, Entry wait, downside risk, or held-position non-incremental status.
- None became clean unexplained PC target zero.

## ADD_TARGET_ZERO_ROOT_CAUSE

No clean Production ADD capitalization defect was proven.

Held-position target-zero rows:

- Total held-position rows: `33`
- Primary `ADD_NOT_INCREMENTALLY_JUSTIFIED`: `23`
- Primary `RISK_SUPPRESSED`: `10`

Representative held rows:

- `2024-03-18 44250`, `REMOVE_CANDIDATE`, PM `EXIT`, target zero
- `2024-03-18 37440`, `REMOVE_CANDIDATE`, PM `EXIT`, target zero
- `2024-03-21 52160`, `REMOVE_CANDIDATE`, PM `EXIT`, target zero
- `2024-04-10 78150`, held row with `ADD_ALLOWED` Entry text but PM `EXIT` / remove membership, target not above current

Judgment:

- These are not clean "winner ADD was available but PC zeroed it for no reason" cases.
- Existing held-position relationship either had PM EXIT/remove intent, no incremental target above current, or defensive risk context.

## REENTRY_TARGET_ZERO_ROOT_CAUSE

REENTRY-like rows dominate the population:

- `REENTRY_LIKE = 1697 / 1730`

Primary reasons among REENTRY-like rows:

| Primary reason | Rows |
| --- | ---: |
| `RISK_SUPPRESSED` | 799 |
| `NEGATIVE_EXPECTED_EDGE` | 503 |
| `ENTRY_BLOCKED` | 227 |
| `REENTRY_STRENGTH_NOT_REESTABLISHED` | 78 |
| `REENTRY_CHURN_PROTECTION` | 45 |
| `DOWNSIDE_RISK_BLOCKED` | 45 |

Representative non-risk REENTRY-like target-zero rows:

- `2024-03-18 66590`: rank 2, upstream full-allocation reason present, but `reentry_hard_stop_new_thesis_not_sufficient`.
- `2024-03-18 70030`: rank 6, upstream full-allocation reason present, but `reentry_hard_stop_new_thesis_not_sufficient`.
- `2024-03-18 89180`: rank 7, `reentry_trend_recovery_not_satisfied`.
- `2024-03-18 55860`: `reentry_minimum_cooldown_not_satisfied` and new thesis not sufficient.
- `2024-03-18 74260`: `non_positive_expected_edge_score` plus `reentry_unknown_prior_context_independence_not_established`.

Judgment:

- REENTRY target-zero is structurally present, but explained by existing REENTRY safety/strength/expected-edge semantics.
- The audit did not prove that PC silently discarded a clean, risk-allowed, edge-positive REENTRY opportunity.

## RELATIONSHIP_SEMANTIC_SUPPRESSION_GAP

Classification: `STRUCTURALLY_PRESENT_SHADOW_FOLLOWUP_JUSTIFIED`, not `PC_SEMANTIC_DEFECT_PROVEN`.

Evidence:

- Nearly all target-zero rows are prior-relationship rows (`REENTRY_LIKE` or held position).
- Some rows carry strong upstream BQ evidence, including 119 rows with `buy_quality_full_allocation_eligible` in reason codes, yet PC materializes them as zero target after REENTRY/Entry/selection-quality constraints.
- The relationship layer is therefore an important suppressor of capitalization.

Why this is not yet a defect:

- Clean-case count is zero.
- The suppressions are backed by PIT reason codes such as expected-edge weakness, downside risk, churn/cooldown, trend/momentum recovery not satisfied, new thesis not sufficient, or risk-defense state.
- Removing or weakening these would be a Strategy/PC semantic change, not a correctness repair justified by this audit.

## Required Final Answers

- `BQ_POSITIVE_PC_TARGET_ZERO_POPULATION`: `1730` rows across `2024-03-18..2024-05-28`; `1697` REENTRY-like, `33` held-position; all PC materialized as `REDUCED_ALLOCATION_ONLY`; `119` carried upstream full-allocation reason evidence.
- `VALID_RISK_ZERO_COUNT`: `809`
- `NON_RISK_TARGET_ZERO_COUNT`: `921`
- `CLEAN_TARGET_ZERO_CASE_COUNT`: `0`
- `ADD_TARGET_ZERO_ROOT_CAUSE`: no clean ADD defect proven; held-position target-zero rows were PM EXIT/remove, risk-suppressed, or not incrementally justified.
- `REENTRY_TARGET_ZERO_ROOT_CAUSE`: REENTRY-like zeroing is driven by risk suppression, negative expected edge, Entry/BQ wait, churn/cooldown, and strength/recovery not re-established.
- `RELATIONSHIP_SEMANTIC_SUPPRESSION_GAP`: `STRUCTURALLY_PRESENT_SHADOW_FOLLOWUP_JUSTIFIED`
- `PC_SEMANTIC_DEFECT_PROVEN`: `NO`
- `PRODUCTION_REPAIR_JUSTIFIED`: `NO`
- `SHADOW_DESIGN_FOLLOWUP_JUSTIFIED`: `YES`
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `SHADOW_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `RUNTIME_STATE_MUTATED`: `NO`
- `FUTURE_OUTCOME_USED_FOR_JUDGMENT`: `NO`
- `NEXT_RECOMMENDED_STEP`: if continuing this line, run a SHADOW-only design study on whether REENTRY relationship suppression should expose a clearer "renewed clean thesis" graduation state before any Production change is considered. Do not promote from this audit alone.

## Final Judgment

`PHASE32_EN_BQ_POSITIVE_PC_TARGET_ZERO_BOUNDARY_EXPLAINED_NO_CLEAN_UNEXPLAINED_CASE_RELATIONSHIP_SUPPRESSION_SHADOW_FOLLOWUP_JUSTIFIED_NO_PRODUCTION_REPAIR`
