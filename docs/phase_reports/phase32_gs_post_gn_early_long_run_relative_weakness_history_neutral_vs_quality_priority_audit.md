# Phase32-GS — Post-GN Early Long-Run Relative Weakness Attribution / History-Neutral vs Quality-Priority Audit

Date: 2026-09-05 JST

Scope: READ-ONLY audit of existing runtime artifacts only.

- Post-GN run: `runtime-test-historical-extended-smoke-20260905T002804721163Z`
- Post-GN status: `RUNNING`
- Requested start: `2022-10-03`
- Completed business-day window used: `2022-10-03` through `2022-11-07`, 24 completed days
- No source/config/schema/runtime state mutation was performed.
- No fresh-run/resume/replay/recover was performed.
- Historical return, realized PnL, MFE/MAE, and future outcome were not used to judge BUY quality.

## Comparator Selection

PRE_GN_COMPARISON_RUN_ID: `runtime-test-historical-extended-smoke-20260902T060955933565Z`

Evidence for selecting it:

- `run_state.json` and `historical_evaluation_authority.json` explicitly reference requested start `2022-10-03`.
- `run_state.json` records `556` completed business days from `2022-10-03` through `2025-01-08`.
- `source_baseline.source_commit = 1f64f49ee9a8dd48280007e4df656e5f03e231ca`, while the post-GN run uses `a8af2dacfb3c81015a069b40d53ff182cccb2542`.

Critical evidence limitation:

- The selected pre-GN run has no retained `daily/<date>/execution/fills.json`, `strategy/portfolio_construction.json`, `strategy/position_sizing.json`, or `strategy/runtime_planning.json` directories.
- Its `final_summary.json` is `ABANDONED`, and it preserves only final snapshots plus run metadata.
- Therefore exact pre-vs-post symbol-date BUY divergence, direct GN divergence, and paired PIT comparison cannot be proven from current artifacts.

This report does not guess missing pre-GN daily evidence.

## Comparable Window

- COMPARABLE_WINDOW_START: `2022-10-03`
- COMPARABLE_WINDOW_END: `2022-11-07`
- Post-GN completed days used: `24`
- Pre-GN same-window daily execution/strategy artifacts: `MISSING`

The post-GN run already has a `2022-11-08` directory, but `run_state.json` still lists completed days only through `2022-11-07`; `2022-11-08` was excluded to avoid reading an in-flight day as completed.

## Equity / Exposure Context

Post-GN context from completed-day `current_valuation_refresh/current_valuation_manifest.json` and strategy artifacts:

- start equity: `1,012,350 JPY` on `2022-10-03`
- end equity: `1,086,500 JPY` on `2022-11-07`
- POST_GN_RETURN: `8.65%` vs initial 1,000,000 JPY
- window return from first completed valuation: `7.3245%`
- max equity: `1,086,500 JPY`
- min equity: `1,012,350 JPY`
- POST_GN_AVG_EXPOSURE: `0.774388`
- POST_GN_AVG_CASH: `0.225612`
- average positions from valuation manifests: `9.67`

Pre-GN comparable equity metrics are blocked by missing daily valuation artifacts:

- PRE_GN_RETURN: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- PRE_GN_AVG_EXPOSURE: `UNRESOLVED_ARTIFACT_DEPENDENCY`

Equity context is recorded only as context, not as a BUY-quality design signal.

## Post-GN BUY Quality Observations

Post-GN actual BUYs from completed-day `execution/fills.json`:

- post-GN BUY count: `60`
- post-GN BUY notional: `3,540,850 JPY`
- BUY_NEW: `55`
- BUY_ADD: `5`
- weighted average purchased Current Opportunity rank: `15.4620`
- median purchased rank: `15`
- deepest purchased rank: `31`

MCV priority consistency inside post-GN artifacts:

- rank/priority pair comparisons: `6,142`
- rank-priority inversions: `0`

This confirms that the post-GN actual path is rank-first and history-neutral in the completed early long-run window.

## Actual BUY Difference

Exact differential counts require same-window pre-GN daily fill artifacts. Those artifacts are not present.

- BOTH_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- PRE_GN_ONLY_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- GN_ONLY_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`

Because exact pre-GN actual BUY evidence is absent, this report cannot prove the first direct GN divergence or paired replacements for the 2022-10-03 long-run start.

- FIRST_DIRECT_GN_DIVERGENCE_DATE: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- FIRST_DIRECT_GN_DIVERGENCE_SYMBOL: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- DIRECT_GN_PRIORITY_EFFECT_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- DOWNSTREAM_PATH_EFFECT_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`

## Direct Root-Cause Counts

The requested direct-effect decomposition cannot be completed without pre-GN same-day PC/MCV/runtime evidence:

- HISTORY_NEUTRAL_DIRECT_BENEFIT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- QUALITY_CLASS_FIRST_REMOVAL_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- ACCEPTED_INCREMENT_REMOVAL_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- OTHER_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`

No missing-evidence gap is treated as zero.

## Rank vs Quality Conflict

Post-GN artifacts do show Current Opportunity rank and MCV quality class pointing in opposite directions.

- RANK_QUALITY_CONFLICT_CASE_COUNT: `219`
- Example `2022-10-05`: rank-1 `94320` was `ELIGIBLE_COMPARABLE`, while rank-3 `39060` was `ELIGIBLE_STRONG`; post-GN bought `94320` and did not buy `39060`.
- Example `2022-10-20`: multiple higher-ranked `ELIGIBLE_COMPARABLE` names outranked lower-ranked `ELIGIBLE_STRONG` names such as `44490` and `69930`; several higher-ranked comparable names received capital.

Interpretation:

- GN is definitely rank-dominant in the completed post-GN artifacts.
- This is intended for history-neutrality and NEW/ADD parity.
- However, the artifacts also show that Current-PIT quality class is no longer able to override rank in conflict cases.

GN_TOO_RANK_DOMINANT_JUDGMENT: `MIXED`

Rationale: rank-first is working as designed and removes history/relationship/accepted-increment priority channels, but there is credible design risk that the implementation also demoted useful Current-PIT quality-class evidence too far. The current artifact set cannot prove whether that risk caused relative weakness because the pre-GN daily comparator evidence is missing.

## Could History Neutrality Preserve Quality?

HISTORY_NEUTRAL_PLUS_QUALITY_PRESERVATION_FEASIBLE: `YES`

Read-only design assessment within the existing PC/MCV/NCU architecture:

- History-neutrality can remain enforced by keeping old ownership, campaign, held/flat relationship, prior ADD, prior EXIT outside recent guard, realized PnL, and accepted-increment fields out of the priority comparator.
- NEW/ADD parity can remain enforced by computing BUY priority before relationship materialization and before accepted quantity.
- Current-PIT quality evidence could still participate as a non-history MCV/NCU input, provided it is explicitly restricted to same-day BQ/Entry/momentum/trend/eligibility evidence.
- No new authority is required in principle; this is a comparator design question inside existing MCV/PC authority boundaries.

QUALITY_CLASS_CURRENT_PIT_AUTHORITY_MATERIALLY_LOST: `YES, as a design property of the post-GN comparator; causal performance impact is unresolved without pre-GN daily evidence.`

## No-Regression Check

Completed-window post-GN artifacts show no new semantic regression in the checked domains:

- SELL_REGRESSION_FOUND: `NO`
- WINNER_REGRESSION_FOUND: `NO`
- SIZING_REGRESSION_FOUND: `NO`
- CASH_REGRESSION_FOUND: `NO`
- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- REENTRY_GUARD_REGRESSION_FOUND: `NO`
- Runtime regression found: `NO`

Evidence basis:

- `runtime_capital_priority_redecision` remains false in runtime planning evidence.
- `position_sizing_recomputes_capital_priority` remains false in position sizing rows.
- G61/G63 compatibility keeps priority binding in PS/runtime.
- Fresh target shadow zero-tolerance diagnostics report `add_safety_bypass_count = 0`.
- Recent Exit Guard block evidence is present; bypass count is zero.

## Churn / Guard

Post-GN completed-window fill-sequence metrics:

- BUY->EXIT->BUY cycle count: `15`
- EXIT->BUY count: `17`
- repeated same-symbol cycle count: `13`
- recent-exit guard block evidence count: `319`
- recent-exit guard bypass count: `0`

CHURN_REGRESSION_FOUND: `UNRESOLVED_ARTIFACT_DEPENDENCY`

Reason: post-GN churn is measurable, but pre-GN same-window daily fills are missing, so increase/decrease vs pre-GN cannot be proven.

## Regime Characterization

BEAR_BUY_CHARACTERIZATION_COMPLETE: `PARTIAL`

The completed post-GN window can be characterized for BUY behavior, but a comparable pre-GN BEAR/RANGE/RECOVERY/BULL split cannot be completed from missing daily artifacts. The inspected post-GN artifacts do not show unjustified BEAR buy expansion evidence; BUYs remain gated by BQ/Entry, MCV, PS, lot feasibility, and runtime planning.

- BEAR_UNJUSTIFIED_BUY_EXPANSION_FOUND: `NO in post-GN artifacts; pre-GN differential unresolved.`

## Early Weakness Attribution

EARLY_RELATIVE_WEAKNESS_PRIMARY_ATTRIBUTION: `UNRESOLVED_ARTIFACT_DEPENDENCY_WITH_DESIGN_RISK`

Attribution decomposition:

- HISTORY_NEUTRAL_PATH_EFFECT: `plausible, but not provable without pre-GN daily BUY/portfolio path evidence`
- QUALITY_PRIORITY_REMOVAL_EFFECT: `plausible design risk; post-GN rank-vs-quality conflicts are directly observed`
- CASH/LOT/PATH_EFFECT: `post-GN artifacts show ordinary cash/lot/path mechanics; differential magnitude unresolved`
- SELL/HOLDING_PATH_EFFECT: `no SELL semantic regression observed; differential unresolved`
- MARKET_NOISE_NOT_ATTRIBUTABLE: `not used as design evidence`
- OTHER: `missing pre-GN daily artifacts prevent exact causal split`

This report explicitly does not tune rank, quality-class, cash, sizing, or guard thresholds based on early relative return.

## Decisions

A. History-neutrality remains justified?

- HISTORY_NEUTRALITY_STILL_JUSTIFIED: `YES`
- Reason: post-GN artifacts show zero rank-priority inversions and no history/relationship/accepted-increment priority reintroduction.

B. Rank-first priority remains justified as currently implemented?

- Judgment: `MIXED`
- Reason: it is semantically clean and functioning, but it appears to subordinate Current-PIT quality class completely in observed conflict cases.

C. Quality-class Current PIT authority was over-removed?

- QUALITY_CLASS_CURRENT_PIT_AUTHORITY_MATERIALLY_LOST: `YES`
- Production impact: `UNRESOLVED`

D. 650BD run should continue unchanged?

- CONTINUE_650BD_RUN_UNCHANGED: `YES`
- Reason: no zero-tolerance regression was found, and stopping/changing the run based on early PnL or incomplete differential evidence would violate the audit constraint.

## Required Answers

- PRE_GN_COMPARISON_RUN_ID: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- COMPARABLE_WINDOW_START: `2022-10-03`
- COMPARABLE_WINDOW_END: `2022-11-07`
- PRE_GN_RETURN: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- POST_GN_RETURN: `8.65% vs initial 1,000,000 JPY`
- PRE_GN_AVG_EXPOSURE: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- POST_GN_AVG_EXPOSURE: `0.774388`
- BOTH_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- PRE_GN_ONLY_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- GN_ONLY_BUY_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- FIRST_DIRECT_GN_DIVERGENCE_DATE: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- FIRST_DIRECT_GN_DIVERGENCE_SYMBOL: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- DIRECT_GN_PRIORITY_EFFECT_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- DOWNSTREAM_PATH_EFFECT_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- HISTORY_NEUTRAL_DIRECT_BENEFIT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- QUALITY_CLASS_FIRST_REMOVAL_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- ACCEPTED_INCREMENT_REMOVAL_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- OTHER_DIRECT_CASE_COUNT: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- RANK_QUALITY_CONFLICT_CASE_COUNT: `219`
- GN_TOO_RANK_DOMINANT_JUDGMENT: `MIXED`
- HISTORY_NEUTRALITY_STILL_JUSTIFIED: `YES`
- QUALITY_CLASS_CURRENT_PIT_AUTHORITY_MATERIALLY_LOST: `YES`
- HISTORY_NEUTRAL_PLUS_QUALITY_PRESERVATION_FEASIBLE: `YES`
- SELL_REGRESSION_FOUND: `NO`
- WINNER_REGRESSION_FOUND: `NO`
- SIZING_REGRESSION_FOUND: `NO`
- CASH_REGRESSION_FOUND: `NO`
- ADD_SAFETY_BYPASS_COUNT: `0`
- G129_REGRESSION_COUNT: `0`
- REENTRY_GUARD_REGRESSION_FOUND: `NO`
- CHURN_REGRESSION_FOUND: `UNRESOLVED_ARTIFACT_DEPENDENCY`
- BEAR_BUY_CHARACTERIZATION_COMPLETE: `PARTIAL`
- BEAR_UNJUSTIFIED_BUY_EXPANSION_FOUND: `NO in post-GN artifacts; pre-GN differential unresolved`
- EARLY_RELATIVE_WEAKNESS_PRIMARY_ATTRIBUTION: `UNRESOLVED_ARTIFACT_DEPENDENCY_WITH_DESIGN_RISK`
- CONTINUE_650BD_RUN_UNCHANGED: `YES`
- DESIGN_REVIEW_REQUIRED_NOW: `YES`
- PRODUCTION_CHANGE_JUSTIFIED_NOW: `NO`
- NEXT_STEP: `Continue the 650BD run unchanged, preserve completed post-GN artifacts, and perform a narrow MCV/PC design review on whether same-day Current-PIT quality class should be retained as a history-neutral comparator input. Exact pre-vs-GN early weakness attribution requires restoring or regenerating a same-start pre-GN daily artifact set under a separately approved, non-read-only phase.`

Final Judgment: Post-GN long-run序盤のrelative weaknessは現存artifactだけではhistory-neutral path effectかquality-class authority過剰除去かを断定できないが、GNはhistory-neutralには正常動作しており、同時にCurrent-PIT quality-class authorityをrank-firstで実質的に弱めた設計リスクが確認されたため、650BD runは止めずにdesign reviewを開始する。
