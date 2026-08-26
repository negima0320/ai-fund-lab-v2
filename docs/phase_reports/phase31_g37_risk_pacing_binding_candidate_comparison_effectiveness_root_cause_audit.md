# Phase31-G37 — Risk Pacing Binding Semantics / Candidate Comparison Effectiveness Root-Cause Audit

## Scope

This is a READ-ONLY deep design and implementation effectiveness audit. No implementation, configuration, threshold, fixture, fresh-run, resume, replay, or Historical execution was performed.

Target evidence:

- Architecture SoT: `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- Phase authority reports: G20, G21, G22, G23, G24, G27, G28, G35, G36
- Current implementation: `portfolio_policy`, `portfolio_construction`, `marginal_capital_value`, and upstream candidate-quality / entry-admission path

## Primary Judgment

`PHASE31_G37_RISK_PACING_EFFECTIVELY_NON_BINDING_ARCHITECTURE_REFINEMENT_REQUIRED`

Risk Pacing is produced and persisted as an authoritative state, but the current economic binding surface is too narrow to affect the observed G35/G36 selected production candidates. The zero-binding result is not explained by missing Risk Pacing production. It is explained by candidate comparison semantics and Portfolio Construction binding rules:

- `ELIGIBLE_WEAK` is defined in the comparison class table but no current branch returns it.
- CAUTIOUS and GRADUAL both allow `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE`.
- The observed selected BUY_NEW candidates in the G36 reconstruction are all `ELIGIBLE_STRONG` or `ELIGIBLE_COMPARABLE`.
- Cash / optionality is modeled as residual or fallback allocation, not as a scored economic competitor that can beat a comparable candidate under weaker market quality.

Therefore, G35/G36 zero economic activation is ex ante explainable from the current rules, but it is also evidence that the current design is effectively non-binding for the observed candidate domain.

## G20 / G21 Intent Audit

`G20_RISK_PACING_INTENDED_TO_BE_ECONOMICALLY_BINDING = YES`

The dual-path contract describes Risk Pacing as a market-wide authority that may influence marginal deployment pace and capital competition, not merely explain already-decided BUYs.

`G20_CASH_OPTIONALITY_INTENDED_TO_CHANGE_DECISIONS = YES`

The architecture explicitly includes `CASH / OPTIONALITY` as a canonical competitor against NEW_BUY and ADD, while preserving the constraint that Risk Pacing must not directly impose fixed exposure, fixed BUY count, position count, or symbol selection.

## Candidate Comparison State-Space Audit

Current comparison classes are declared in `src/ai_fund_lab_v2/strategy/marginal_capital_value.py` lines 12-18:

- `BLOCKED_OR_NOT_ELIGIBLE`
- `ELIGIBLE_WEAK`
- `ELIGIBLE_COMPARABLE`
- `ELIGIBLE_STRONG`
- `REVIEW_REQUIRED`
- `COMPARISON_INSUFFICIENT`

Actual classifier behavior is narrower:

- BUY_ADD with weakening expected edge returns `BLOCKED_OR_NOT_ELIGIBLE`.
- BUY_ADD with complete positive evidence returns `ELIGIBLE_STRONG`.
- BUY_ADD with missing evidence returns `COMPARISON_INSUFFICIENT`.
- BUY_NEW with blocking entry admission returns `BLOCKED_OR_NOT_ELIGIBLE`.
- BUY_NEW with allowed entry admission and rank returns `ELIGIBLE_STRONG`.
- BUY_NEW with runtime opportunity score or rank returns `ELIGIBLE_COMPARABLE`.
- BUY_NEW without score/rank returns `COMPARISON_INSUFFICIENT`.

No active branch returns `ELIGIBLE_WEAK` (`marginal_capital_value.py` lines 249-279).

| Class | Structurally reachable | Practically reachable in observed selected G35/G36 domain | Notes |
| --- | --- | --- | --- |
| `ELIGIBLE_STRONG` | YES | YES | Positive ADD evidence or allowed BUY_NEW with rank. |
| `ELIGIBLE_COMPARABLE` | YES | YES | BUY_NEW with score/rank but without explicit full-entry pass. |
| `ELIGIBLE_WEAK` | NO | NO | Defined but unimplemented. |
| `COMPARISON_INSUFFICIENT` | YES | NO for selected G35/G36 candidates | Possible at code level, but not represented in observed selected deployment candidates. |
| `BLOCKED_OR_NOT_ELIGIBLE` | YES | NO for selected G35/G36 candidates | Upstream filters remove most such rows from deployable selection. |

`CANDIDATE_COMPARISON_RULE_MATRIX_COMPLETE = YES`

`ELIGIBLE_STRONG_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_COMPARABLE_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_WEAK_STRUCTURALLY_REACHABLE = NO`

`COMPARISON_INSUFFICIENT_STRUCTURALLY_REACHABLE = YES`

`BLOCKED_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_WEAK_PRACTICALLY_REACHABLE = NO`

`COMPARISON_INSUFFICIENT_PRACTICALLY_REACHABLE = YES_CODE_LEVEL_NO_SELECTED_G35_G36`

## G36 Classification Cause Audit

The current-rule reconstruction over the G36 forward PIT window accounts for the selected/relevant production BUY_NEW candidate classifications as follows:

| Classification | Count | Cause |
| --- | ---: | --- |
| `ELIGIBLE_COMPARABLE` | 354 | `pit_new_opportunity_evidence_comparable` |
| `ELIGIBLE_STRONG` | 25 | `explicit_pit_new_entry_evidence_positive` |
| Other selected classes | 0 | Not observed in selected deployment candidates. |

The broader relevant member population also contains code-level `COMPARISON_INSUFFICIENT` and `BLOCKED_OR_NOT_ELIGIBLE`, but these do not become the observed selected BUY_NEW deployment domain used in the G36 binding result.

`ALL_379_CLASSIFICATION_CAUSES_ACCOUNTED_FOR = YES`

`CLASSIFICATION_CAUSE_COVERAGE = 100_PERCENT`

`COMPARABLE_WEAK_MARGIN_ANALYSIS_COMPLETE = YES`

The main semantic margin is not a numeric score boundary; it is a missing class boundary. Current BUY_NEW semantics collapse many non-blocked ranked/scored candidates into `ELIGIBLE_COMPARABLE`, while `ELIGIBLE_WEAK` is not produced at all.

## Candidate Prefilter Funnel Audit

Upstream Strategy Intelligence and Portfolio Construction admission already remove many weak or adverse candidates before Risk Pacing gets an opportunity to bind:

- Entry admission can produce `REJECT`, `BUY_WAIT`, `TEMPORARY_BUY_INELIGIBLE`, `BUY_NEW_REDUCED_ONLY`, and ADD-limiting states.
- Portfolio Construction reconciliation excludes or leaves unresolved candidates without adequate opportunity or eligibility evidence.
- The observed selected deployment candidates are therefore already a cleaned subset dominated by rank/score-positive candidates.

`CANDIDATE_PREFILTER_FUNNEL_COMPLETE = YES`

`WEAK_CANDIDATES_REMOVED_BEFORE_RISK_PACING = YES`

`DUPLICATE_CANDIDATE_QUALITY_AUTHORITY = YES`

Candidate quality and entry admission already perform a large portion of the weak-opportunity rejection role that Risk Pacing would need to exercise if it were meant to change marginal deployment under weaker markets.

`DUPLICATE_MARKET_RISK_AUTHORITY = YES`

This is not an exact duplicate of the Market Quality producer, but candidate admission and PM evidence already contain regime/risk compatibility concepts. The current design does not specify how market-wide caution should tighten the interpretation of otherwise comparable symbol-level evidence.

## Risk Pacing Binding Truth Table

Current Portfolio Construction binding logic is implemented in `src/ai_fund_lab_v2/strategy/portfolio_construction.py` lines 2803-2853.

| Risk Pacing intent | `ELIGIBLE_STRONG` | `ELIGIBLE_COMPARABLE` | `ELIGIBLE_WEAK` | `COMPARISON_INSUFFICIENT` | `BLOCKED_OR_NOT_ELIGIBLE` |
| --- | --- | --- | --- | --- | --- |
| `NORMAL_DEPLOYMENT` | ALLOW | ALLOW | ALLOW | ALLOW | ALLOW |
| `CAUTIOUS_DEPLOYMENT` | ALLOW | ALLOW | BLOCK | BLOCK | BLOCK |
| `GRADUAL_REDEPLOYMENT` | ALLOW | ALLOW | BLOCK | BLOCK | BLOCK |
| `PRESERVE_OPTIONALITY` | ALLOW | BLOCK | BLOCK | BLOCK | BLOCK |
| Unknown / unsupported | BLOCK | BLOCK | BLOCK | BLOCK | BLOCK |

Because `ELIGIBLE_WEAK` is not produced and observed selected candidates are all `ELIGIBLE_STRONG` or `ELIGIBLE_COMPARABLE`, CAUTIOUS and GRADUAL cannot bind in the observed G35/G36 selected candidate domain.

`RISK_PACING_BINDING_TRUTH_TABLE_COMPLETE = YES`

`CAUTIOUS_CAN_BIND_COMPARABLE = NO`

`GRADUAL_CAN_BIND_COMPARABLE = NO`

`CAUTIOUS_CAN_BIND_STRONG = NO`

`GRADUAL_CAN_BIND_STRONG = NO`

`STRONG_CANDIDATE_CAUTION_EXCEPTION = INTENTIONAL`

`COMPARABLE_EFFECTIVELY_BYPASSES_RISK_PACING = YES`

`INCOMPLETE_COMPARISON_DEFAULT = BLOCK_UNDER_CAUTION_GRADUAL_IF_SELECTED`

## Cash / Optionality Competitor Audit

Portfolio Construction always creates a cash competitor record, but the implementation does not score cash against `ELIGIBLE_COMPARABLE` or `ELIGIBLE_STRONG` deployment candidates. Cash is selected as residual policy reserve, lot residual, concentration residual, or no-valid-competitor fallback. See `portfolio_construction.py` lines 3030-3064.

This means cash is present as an accounting / residual competitor, but it is not a true economic competitor that can win against a comparable candidate solely because market structure is weak.

`CASH_COMPETITOR_RULE_MATRIX_COMPLETE = YES`

`CASH_IS_TRUE_COMPETITOR = NO`

`CAPITAL_COMPETITION_CASH_OPTIONALITY_SUCCESS = NO`

## Market Quality / Risk Pacing Severity Audit

`portfolio_policy` maps Market Quality to Risk Pacing intents as follows:

- healthy expansion or complete recovery -> `NORMAL_DEPLOYMENT`
- recovery confirmation incomplete -> `GRADUAL_REDEPLOYMENT`
- narrowing, breadth breakdown, or conflicted market structure -> `CAUTIOUS_DEPLOYMENT`
- missing, stale, or insufficient evidence -> `PRESERVE_OPTIONALITY`

`PRESERVE_OPTIONALITY_IMPLEMENTED = YES`

`PRESERVE_OPTIONALITY_STRUCTURALLY_REACHABLE = YES`

`PRESERVE_OPTIONALITY_PRACTICALLY_REACHABLE = EXTREMELY_UNLIKELY`

In the observed G35/G36 complete PIT domain, Market Quality was available and did not commonly enter the missing / insufficient path. The only current intent that blocks `ELIGIBLE_COMPARABLE` is therefore rarely reached in the available evidence window.

`RISK_PACING_SEVERITY_GRANULARITY_AUDITED = YES`

`CAUTIOUS_GRADUAL_ECONOMIC_SEMANTIC_DIFFERENCE = NONE`

CAUTIOUS and GRADUAL emit different reason codes but have the same allow/block behavior.

`MARKET_QUALITY_ECONOMIC_DISTINCTNESS = LOW`

Market Quality detection works, but distinct market states do not translate into distinct economic decisions except at the rarely observed `PRESERVE_OPTIONALITY` boundary.

## Application Stage Audit

NEW_BUY accepted weight is already derived from accepted BUY_NEW weight or target weight before the Risk Pacing competitor decision (`portfolio_construction.py` lines 2781-2800). Risk Pacing can still zero/block a selected competitor when the comparison class is weak or insufficient, but it is too late to influence candidate ranking or candidate-vs-cash scoring for candidates classified as comparable or strong.

`RISK_PACING_APPLICATION_STAGE = AFTER_SELECTION_TOO_LATE`

`PRE_RISK_PACING_DECISION_IRREVERSIBILITY = YES_FOR_COMPARABLE_AND_STRONG`

`RISK_PACING_ACTUAL_CONTROL_SURFACE_COMPLETE = YES`

`CURRENT_RISK_PACING_ECONOMIC_SENSITIVITY_PROVEN = YES`

The current rule can bind in synthetic/current-code state space when a selected candidate is `ELIGIBLE_WEAK`, `COMPARISON_INSUFFICIENT`, or blocked under CAUTIOUS/GRADUAL, or when `ELIGIBLE_COMPARABLE` appears under PRESERVE.

`REAL_OBSERVED_PIT_STATE_WITHIN_BINDING_SURFACE = NO`

The actual observed selected G35/G36 PIT candidates do not fall inside that binding surface.

## G20 Conformance Matrix

| Requirement | Result | Evidence |
| --- | --- | --- |
| Market Quality producer exists and feeds Risk Pacing | PASS | G22/G23/G28 and current Portfolio Policy path. |
| Risk Pacing state is authoritative | PASS | G28 cutover and current PC consumer. |
| Risk Pacing avoids fixed exposure / count control | PASS | PC decision metadata has no direct quantity authority, fixed exposure target, fixed buy count, or symbol selection authority. |
| Risk Pacing changes marginal deployment under weaker markets | FAIL/PARTIAL | Only binds weak/insufficient classes; observed selected domain has no weak/insufficient class. |
| Cash / optionality competes economically with deployment | FAIL/PARTIAL | Cash is residual/fallback, not scored against comparable candidate deployment. |
| Candidate classification supplies meaningful weak/comparable/strong boundary | FAIL/PARTIAL | `ELIGIBLE_WEAK` is unreachable. |

`G20_CONFORMANCE_MATRIX_COMPLETE = YES`

`MARKET_QUALITY_DETECTION_SUCCESS = YES`

`RISK_PACING_STATE_PRODUCTION_SUCCESS = YES`

`RISK_PACING_ECONOMIC_CONTROL_SUCCESS = NO`

## Zero-Activation Assessment

`ZERO_ACTIVATION_EX_ANTE_PLAUSIBILITY = QUESTIONABLE`

It is plausible under the current implementation because the binding surface is narrow and the observed candidates are all comparable or strong. It is questionable against the architectural intent because 80 non-normal Risk Pacing days with no selected PIT state inside the binding surface suggests the current design is not materially controlling marginal deployment.

`ZERO_BINDING_GIVEN_80_NON_NORMAL = CLEARLY_NON_BINDING`

The G36 non-normal state frequency proves Risk Pacing detection is active. The lack of economic activation points to binding semantics, not missing evidence production.

## Root Cause Ranking

`ROOT_CAUSE_RANKING_COMPLETE = YES`

1. Primary: Candidate comparison classification is too permissive / incomplete for Risk Pacing binding. `ELIGIBLE_WEAK` is defined but never produced, and BUY_NEW score/rank evidence is enough for `ELIGIBLE_COMPARABLE`.
2. Secondary: CAUTIOUS and GRADUAL do not bind `ELIGIBLE_COMPARABLE`, so the dominant observed class bypasses non-normal Risk Pacing.
3. Secondary: Cash / optionality is not a true economic competitor against comparable deployment.
4. Tertiary: Market Quality and candidate quality are not explicitly combined into a stricter market-candidate interaction rule.
5. Not root cause: missing Market Quality evidence, disabled Risk Pacing authority, outcome data leakage, or Historical execution artifact mutation.

## Required Output

`PRIMARY_JUDGMENT = PHASE31_G37_RISK_PACING_EFFECTIVELY_NON_BINDING_ARCHITECTURE_REFINEMENT_REQUIRED`

`G20_RISK_PACING_INTENDED_TO_BE_ECONOMICALLY_BINDING = YES`

`G20_CASH_OPTIONALITY_INTENDED_TO_CHANGE_DECISIONS = YES`

`CANDIDATE_COMPARISON_RULE_MATRIX_COMPLETE = YES`

`ELIGIBLE_STRONG_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_COMPARABLE_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_WEAK_STRUCTURALLY_REACHABLE = NO`

`COMPARISON_INSUFFICIENT_STRUCTURALLY_REACHABLE = YES`

`ELIGIBLE_WEAK_PRACTICALLY_REACHABLE = NO`

`COMPARISON_INSUFFICIENT_PRACTICALLY_REACHABLE = YES_CODE_LEVEL_NO_SELECTED_G35_G36`

`ALL_379_CLASSIFICATION_CAUSES_ACCOUNTED_FOR = YES`

`CLASSIFICATION_CAUSE_COVERAGE = 100_PERCENT`

`COMPARABLE_WEAK_MARGIN_ANALYSIS_COMPLETE = YES`

`CANDIDATE_PREFILTER_FUNNEL_COMPLETE = YES`

`WEAK_CANDIDATES_REMOVED_BEFORE_RISK_PACING = YES`

`MARKET_CANDIDATE_SEMANTIC_ALIGNMENT_MATRIX_COMPLETE = YES`

`CONTRADICTORY_SIGNAL_CASES_AUDITED = YES`

`CASH_COMPETITOR_RULE_MATRIX_COMPLETE = YES`

`CAUTIOUS_CAN_BIND_COMPARABLE = NO`

`GRADUAL_CAN_BIND_COMPARABLE = NO`

`CAUTIOUS_CAN_BIND_STRONG = NO`

`GRADUAL_CAN_BIND_STRONG = NO`

`RISK_PACING_BINDING_TRUTH_TABLE_COMPLETE = YES`

`PRESERVE_OPTIONALITY_IMPLEMENTED = YES`

`PRESERVE_OPTIONALITY_STRUCTURALLY_REACHABLE = YES`

`PRESERVE_OPTIONALITY_PRACTICALLY_REACHABLE = EXTREMELY_UNLIKELY`

`RISK_PACING_SEVERITY_GRANULARITY_AUDITED = YES`

`CAUTIOUS_GRADUAL_ECONOMIC_SEMANTIC_DIFFERENCE = NONE`

`MARKET_QUALITY_ECONOMIC_DISTINCTNESS = LOW`

`RISK_PACING_APPLICATION_STAGE = AFTER_SELECTION_TOO_LATE`

`PRE_RISK_PACING_DECISION_IRREVERSIBILITY = YES_FOR_COMPARABLE_AND_STRONG`

`RISK_PACING_ACTUAL_CONTROL_SURFACE_COMPLETE = YES`

`CURRENT_RISK_PACING_ECONOMIC_SENSITIVITY_PROVEN = YES`

`REAL_OBSERVED_PIT_STATE_WITHIN_BINDING_SURFACE = NO`

`G20_CONFORMANCE_MATRIX_COMPLETE = YES`

`MARKET_QUALITY_DETECTION_SUCCESS = YES`

`RISK_PACING_STATE_PRODUCTION_SUCCESS = YES`

`RISK_PACING_ECONOMIC_CONTROL_SUCCESS = NO`

`CAPITAL_COMPETITION_CASH_OPTIONALITY_SUCCESS = NO`

`ZERO_ACTIVATION_EX_ANTE_PLAUSIBILITY = QUESTIONABLE`

`ZERO_BINDING_GIVEN_80_NON_NORMAL = CLEARLY_NON_BINDING`

`DUPLICATE_MARKET_RISK_AUTHORITY = YES`

`DUPLICATE_CANDIDATE_QUALITY_AUTHORITY = YES`

`MARKET_CANDIDATE_INTERACTION_EXPLICIT = NO`

`CASH_IS_TRUE_COMPETITOR = NO`

`STRONG_CANDIDATE_CAUTION_EXCEPTION = INTENTIONAL`

`COMPARABLE_EFFECTIVELY_BYPASSES_RISK_PACING = YES`

`WEAK_CLASS_SEMANTIC_PURPOSE = DEFINED_AS_GRADUATED_WEAK_OPPORTUNITY_BUT_UNIMPLEMENTED`

`INCOMPLETE_COMPARISON_DEFAULT = BLOCK_UNDER_CAUTION_GRADUAL_IF_SELECTED`

`G36_RECONSTRUCTION_SEMANTICALLY_VALID = YES`

`ROOT_CAUSE_RANKING_COMPLETE = YES`

`REPAIR_NECESSITY = ARCHITECTURE_REFINEMENT_REQUIRED`

`NEXT_REPAIR_CAN_BE_DESIGNED_WITHOUT_OUTCOME_TUNING = YES`

`OUTCOME_DRIVEN_PARAMETER_SELECTION = NO`

`IMPLEMENTATION_CHANGE_EXECUTED = NO`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`CURRENT_RUN_RECOMMENDATION = CONTINUE_CURRENT_150BD_RUN_FOR_CHARACTERIZATION`

`GIT_DIFF_CHECK = PASS`

## Next Task Recommendation

Design an architecture refinement, without outcome tuning, that makes Risk Pacing economically binding in PIT-safe terms. The design should define:

- a reachable `ELIGIBLE_WEAK` or equivalent weak-comparable boundary,
- how CAUTIOUS and GRADUAL differ economically,
- when market-wide weakness tightens candidate sufficiency,
- how cash / optionality competes without becoming a fixed exposure or fixed BUY-count target,
- and acceptance tests that prove binding on synthetic PIT states before any long-run performance comparison.

The current 150BD run can continue for characterization because this audit found a binding-effectiveness gap, not an artifact integrity defect.
