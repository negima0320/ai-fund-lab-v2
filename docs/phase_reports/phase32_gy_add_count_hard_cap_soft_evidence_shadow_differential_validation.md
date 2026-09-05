# Phase32-GY - ADD Count Hard-Cap to Soft Risk Evidence SHADOW / Differential Validation

## Executive Judgment

OPTION_B_SHADOW_IMPLEMENTED: `YES_TEST_LOCAL_SHADOW`

Production PM/PC semantics were not changed. A focused test-local SHADOW model validates the proposed rule:

```text
ADD count >= 5
-> keep observable count evidence
-> remove count-only hard block
-> require all existing Current-PIT ADD Safety / MCV / NCU / Cash / cap / lot / G129 gates
```

The shadow result is safe only if count becomes observability/audit context. No accepted existing semantic was found for using count as a hidden risk weight, rank penalty, threshold, or score.

## Production Boundary Reconfirmed

Current Production chain remains:

```text
current open campaign add_history_summary.event_count >= 5
-> prior_add_history_limits_incremental_add
-> PM structured ADD worthiness = NO_ADD
-> PM ADD action downgraded to HOLD
```

Primary authority:

- `src/ai_fund_lab_v2/strategy/position_management.py`
- `_structured_add_worthiness_evidence()`

Secondary PC mirror:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `_campaign_aware_add_worthiness_state()`

This phase did not edit those Production paths.

## Focused Shadow Tests

Command:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_gy_add_count_soft_evidence_shadow.py \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_99840_equivalent_si_no_add_does_not_hard_block_positive_add_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g74_40520_equivalent_expected_edge_weakening_still_blocks_add \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py::test_phase32_s_missing_campaign_or_no_loss_failure_blocks_acceleration \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py::test_phase32_s_headroom_and_cautious_risk_pacing_bound_magnitude
```

Result:

```text
11 passed in 1.75s
```

Coverage:

- current Production still hard-blocks count `>=5`;
- shadow removes only the count hard block;
- missing evidence becomes review, not PASS;
- no-loss, continuation/deterioration, downside risk, headroom, liquidity, lot, Cash, MCV, NCU, and G129 still block;
- runaway pyramiding adversarial cases pass;
- campaign identity, SELL, Winner, REENTRY, and Recent Exit Guard remain unchanged.

## GX 57 Re-Evaluation

Read-only artifact join:

- PM `prior_add_history_limits_incremental_add` rows were deduped by run/date/symbol/campaign.
- Same-day `portfolio_construction.json` was joined when present.
- Missing downstream evidence was not treated as PASS.
- Future outcome / Historical PnL / MFE / MAE / final campaign outcome were not used.

GX_57_CASES_REEVALUATED: `YES`

Classification:

```text
STILL_BLOCKED_BY_CURRENT_SAFETY_COUNT = 4
REVIEW_REQUIRED_BY_CURRENT_EVIDENCE_COUNT = 11
ADD_WORTHY_BEFORE_CAPITAL_COMPETITION_COUNT = 42
CAPITAL_COMPETITION_ELIGIBLE_COUNT = 0_PROVEN_FROM_EXISTING_ARTIFACTS
```

Interpretation:

- `42` cases have enough current evidence in the existing artifacts to pass ADD worthiness once the count-only block is ignored.
- `4` cases still show current safety block evidence, mainly `NO_ADD` entry/admission state.
- `11` cases lack enough same-day downstream evidence after dedupe or have incomplete join context, so they remain review-required.
- `0` cases are proven to have reached capital competition in existing Production artifacts because PM had already downgraded the ADD to HOLD. Shadow tests show the intended path can preserve capital competition, but existing artifacts cannot prove downstream PC/MCV/NCU eligibility after a Production path that never let the row proceed.

## Strong Winner 46 Re-Evaluation

GX_STRONG_WINNER_46_CASES_REEVALUATED: `YES`

STRONG_WINNER_CAPITAL_COMPETITION_RESTORED_COUNT: `42_ADD_WORTHY_BEFORE_CAPITAL_COMPETITION`

The 42 restored cases had current PIT strength evidence sufficient for ADD-worthiness after removing the count-only hard block. The report does not claim actual order generation or actual capital competition eligibility from existing artifacts, because Production stopped those rows at PM HOLD.

## Safety Matrix

Unsafe release checks:

```text
UNSAFE_ADD_RELEASE_COUNT = 0
INSUFFICIENT_EVIDENCE_FALSE_RELEASE_COUNT = 0
NO_LOSS_AVERAGING_BYPASS_COUNT = 0
DETERIORATION_BYPASS_COUNT = 0
CONCENTRATION_HEADROOM_BYPASS_COUNT = 0
LIQUIDITY_BYPASS_COUNT = 0
LOT_BYPASS_COUNT = 0
```

The shadow gate requires all non-count Current-PIT safety evidence to pass. Missing evidence is `REVIEW_REQUIRED_BY_CURRENT_EVIDENCE`; failed evidence remains `STILL_BLOCKED_BY_CURRENT_SAFETY`.

## Competition And Isolation

NEW_ADD_COMPETITION_PRESERVED: `YES`

GW's history-neutral MCV class-first / rank-second comparator remains the intended capital priority comparator. The shadow does not give ADD a type bonus and does not let repeated ADD outrank stronger BUY_NEW by action label.

CASH_COMPETITION_PRESERVED: `YES`

An ADD-worthy row is not an order. It must still pass:

```text
ADD worthy -> PC / MCV / NCU -> BUY_NEW / ADD / Cash competition -> sizing -> safety -> order
```

G129_REGRESSION_COUNT: `0`

G129 remains order-increment correctness, not count policy.

Boundary flags:

```text
CAMPAIGN_IDENTITY_CHANGED = NO
SELL_CHANGED = NO
WINNER_CHANGED = NO
REENTRY_CHANGED = NO
RECENT_EXIT_GUARD_CHANGED = NO
```

## Runaway Pyramiding

RUNAWAY_PYRAMIDING_ADVERSARIAL_CASES_PASS: `YES`

Adversarial outcomes:

| Case | Shadow result |
|---|---|
| ADD count 8, position near cap | blocked by headroom/concentration |
| ADD count 8, small position, deteriorating | blocked by current safety |
| ADD count 8, small position, strong, all safety pass | allowed to proceed to capital competition |

This proves the shadow is not "count unlimited means ADD." It is "count alone is not a hard block."

## Option B vs C

ADD_COUNT_SOFT_EVIDENCE_HAS_VALID_DECISION_ROLE: `NO_NOT_YET`

No existing accepted semantic was found for turning count into a calibrated risk score, penalty, rank adjustment, or hidden threshold. Keeping count as audit context is valid; using it as a decision input needs a separate accepted design.

OBSERVABILITY_ONLY_PREFERRED: `YES`

OPTION_B_JUDGMENT: `ACCEPT_ONLY_AS_OBSERVABILITY_SOFT_CONTEXT`

OPTION_C_JUDGMENT: `PREFERRED_FOR_DECISION_PATH`

RECOMMENDED_OPTION_AFTER_SHADOW: `Option C for decision semantics, with count retained as observability/audit metadata`

## Required Answers

- OPTION_B_SHADOW_IMPLEMENTED: `YES_TEST_LOCAL_SHADOW`
- GX_57_CASES_REEVALUATED: `YES`

- STILL_BLOCKED_BY_CURRENT_SAFETY_COUNT: `4`
- REVIEW_REQUIRED_BY_CURRENT_EVIDENCE_COUNT: `11`
- ADD_WORTHY_BEFORE_CAPITAL_COMPETITION_COUNT: `42`
- CAPITAL_COMPETITION_ELIGIBLE_COUNT: `0_PROVEN_FROM_EXISTING_ARTIFACTS`

- GX_STRONG_WINNER_46_CASES_REEVALUATED: `YES`
- STRONG_WINNER_CAPITAL_COMPETITION_RESTORED_COUNT: `42_ADD_WORTHY_BEFORE_CAPITAL_COMPETITION`

- UNSAFE_ADD_RELEASE_COUNT: `0`
- INSUFFICIENT_EVIDENCE_FALSE_RELEASE_COUNT: `0`

- NO_LOSS_AVERAGING_BYPASS_COUNT: `0`
- DETERIORATION_BYPASS_COUNT: `0`
- CONCENTRATION_HEADROOM_BYPASS_COUNT: `0`
- LIQUIDITY_BYPASS_COUNT: `0`
- LOT_BYPASS_COUNT: `0`

- NEW_ADD_COMPETITION_PRESERVED: `YES`
- CASH_COMPETITION_PRESERVED: `YES`
- G129_REGRESSION_COUNT: `0`

- CAMPAIGN_IDENTITY_CHANGED: `NO`
- SELL_CHANGED: `NO`
- WINNER_CHANGED: `NO`
- REENTRY_CHANGED: `NO`
- RECENT_EXIT_GUARD_CHANGED: `NO`

- RUNAWAY_PYRAMIDING_ADVERSARIAL_CASES_PASS: `YES`

- ADD_COUNT_SOFT_EVIDENCE_HAS_VALID_DECISION_ROLE: `NO_NOT_YET`
- OBSERVABILITY_ONLY_PREFERRED: `YES`

- OPTION_B_JUDGMENT: `ACCEPT_ONLY_AS_OBSERVABILITY_SOFT_CONTEXT`
- OPTION_C_JUDGMENT: `PREFERRED_FOR_DECISION_PATH`
- RECOMMENDED_OPTION_AFTER_SHADOW: `Option C decision path; retain count as observability/audit metadata`

- NEW_MODULE_REQUIRED: `NO`
- NEW_AUTHORITY_REQUIRED: `NO`
- NEW_THRESHOLD_REQUIRED: `NO`
- NEW_NUMERIC_WEIGHT_REQUIRED: `NO`

- PRODUCTION_MINIMAL_REPAIR_READY: `YES_FOR_NEXT_PHASE_WITH_FOCUSED_PRODUCTION_DIFF`
- DIRECT_PRODUCTION_PROMOTION_READY: `NO_PRODUCTION_CHANGE_FORBIDDEN_IN_GY`

- NEXT_STEP: `Implement a minimal production repair in the existing PM/PC ADD-worthiness path that removes prior_add_history_limits_incremental_add as a hard block, retains current campaign ADD count as observability/audit metadata, and proves with focused tests that no-loss, deterioration, concentration/headroom, liquidity, lot, Cash, G129, SELL/Winner, and REENTRY boundaries remain unchanged.`

## Gate

Production change is not authorized in GY. The SHADOW validation supports a next-phase minimal production repair, but only with count retained as observability/audit metadata and no new threshold, weight, penalty score, or authority.

Final Judgment: current campaign ADD count >=5をhard blockから外しても、既存Current-PIT Safety / MCV / NCU / Cash / cap / lot / G129は危険な追加投資を止められ、countだけで抑制されていた強いWinnerは安全にADD-worthy段階へ戻せるが、既存artifactだけではcapital competition到達までは証明できない。
