# Phase32-GX - ADD Maximum-Count / Repeated-ADD Safety Authority READ-ONLY Audit

## Executive Judgment

ADD_COUNT_CONSTRAINT_FOUND: `YES`

Current Production has an active open-campaign ADD count hard cap:

```text
CURRENT_ADD_MAX_COUNT = 5
```

The cap is campaign-local, not symbol-lifetime, but it is still a hard blocker once the current open campaign reaches five ADD fills. Existing artifacts show material count-only suppression of otherwise healthy ADD candidates. This is not used in BUY Investment Priority after GN/GW, but it remains active later in PM/ADD worthiness and can prevent BUY_ADD before PC/PS/G129 allocation can express current opportunity strength.

## Authority Inventory

| Constraint | File | Function | Producer / Consumer | Production effect |
|---|---|---|---|---|
| ADD count `>= 5` | `src/ai_fund_lab_v2/strategy/position_management.py` | `_structured_add_worthiness_evidence()` | Strategy PM consumes SI lifecycle context | Emits `status=NO_ADD` and reason `prior_add_history_limits_incremental_add` |
| PM ADD downgrade | `src/ai_fund_lab_v2/strategy/position_management.py` | Strategy Intelligence connection path around ADD action patching | PM decision consumer | If PM action is `ADD` and add worthiness is not `PASS`, action is changed to `HOLD`, intensity `NONE` |
| PC lifecycle mirror | `src/ai_fund_lab_v2/strategy/portfolio_construction.py` | `_strategy_intelligence_member_fields()` / `_campaign_aware_add_worthiness_state()` | PC consumes SI lifecycle evidence | Materializes `strategy_intelligence_add_worthiness_state=NO_ADD` when lifecycle add count `>=5`, unless upstream entry action already supplies ADD/NO_ADD |
| ADD history producer | `src/ai_fund_lab_v2/strategy/shadow_runtime.py` | strict-prior ledger/campaign reconstruction and merge | Runtime/strategy campaign state | Additional BUY while campaign is open increments `add_history_summary`; BUY after flat starts a new campaign |

## Count Scope

ADD_COUNT_SCOPE: `successful BUY_ADD fills inside the current open position campaign`

The count is not failed attempts, candidate appearances, PM ADD decisions, or all historical campaigns. It increments only when strict-prior execution/ledger evidence proves an additional BUY while the campaign was already open.

ADD_COUNT_RESET_BOUNDARY: `full EXIT / flat state -> new campaign on later BUY`

ADD_COUNT_IS_CAMPAIGN_LOCAL: `YES`

Evidence:

- initial BUY starts a campaign and increments buy history;
- later BUY while quantity is already positive increments `add_history_summary`;
- full SELL closes the campaign;
- later BUY after flat creates a new campaign identity;
- strict ledger merge refuses to merge a closed/prior campaign into a current open one without open-campaign identity proof.

## Policy Type

ADD_COUNT_POLICY_TYPE: `HARD_BLOCK`

In PM:

```text
if add_history.event_count >= 5:
    reason = prior_add_history_limits_incremental_add
status = NO_ADD
ADD action -> HOLD
```

In PC, the same lifecycle count can materialize `strategy_intelligence_add_worthiness_state=NO_ADD`; however, existing PC tests also show that `SI NO_ADD` alone is not always a hard PC increment gate if PM still authorizes ADD. The active hard blocker is therefore PM-side ADD-to-HOLD downgrading.

## Rationale

ADD_COUNT_ORIGINAL_RATIONALE: `runaway pyramiding prevention / prior ADD safeguard / campaign churn prevention`

Architecture and prior phase reports describe this as a current open-campaign safeguard, adjacent to no-loss averaging, Cash, Risk Pacing, and PC gates. No source, config, or Architecture SoT found a specific derivation for the numeric value `5`.

ADD_COUNT_NUMERIC_VALUE_RATIONALE_FOUND: `NO`

ADD_COUNT_IS_CURRENT_PIT_SAFETY_EVIDENCE: `MIXED_NO_FOR_COUNT_ALONE`

The fact that five ADDs have already occurred is current open-campaign state, so it is bounded and not symbol-lifetime history. But count alone does not directly prove today's next increment is unsafe when current continuation quality, downside risk, no-loss, liquidity, headroom, lot, Cash, and MCV/NCU are all healthy. In artifacts, it acts as a standalone past-action hard stop.

## Existing Independent Safety

EXISTING_ADD_SAFETY_LIST_COMPLETE: `YES`

Current independent ADD / BUY_ADD safety and allocation controls include:

- no-loss averaging;
- continuation / deterioration evidence;
- downside risk;
- campaign identity;
- expected edge / incremental value;
- opportunity cost;
- concentration cap and single-name cap;
- current weight / target weight / headroom;
- liquidity and execution feasibility;
- lot / trading-unit feasibility;
- buying power and Cash competition;
- Risk Pacing;
- MCV/NCU capital comparison;
- BQ / Entry / momentum / trend / continuation;
- G129 order-increment scope at Submit;
- bounded Recent Exit Guard for REENTRY, not ADD.

ADD_COUNT_CAP_SAFETY_REDUNDANCY: `HIGH`

Most risks plausibly represented by a fixed repeated-ADD cap are already covered by current PIT safety, cap/headroom, Cash, lot, no-loss, deterioration, and G129 order-increment controls.

## Strong / Weak Cases

STRONG_WINNER_AT_LIMIT_BEHAVIOR: `BLOCK_TO_HOLD_BY_PM_ADD_COUNT_CAP`

If a current position is strong and all current PIT ADD evidence passes, but open-campaign ADD count is already 5, PM structured add worthiness returns `NO_ADD` with `prior_add_history_limits_incremental_add`; PM converts ADD to HOLD before the downstream allocation path can act.

WEAK_POSITION_BELOW_LIMIT_BEHAVIOR: `NOT_ALLOWED_BY_COUNT_ALONE`

If ADD count is below 5 but continuation quality, downside risk, campaign identity, entry/admission, no-loss, or other current evidence fails, PM/PC can still block or review ADD. Count headroom does not itself authorize ADD.

ADD_COUNT_CAP_CONFLICTS_WITH_HISTORY_NEUTRAL_BUY_PHILOSOPHY: `MIXED`

Reason: the cap is campaign-local and bounded by open campaign lifecycle, so it is not the old symbol-lifetime ownership/history bias removed from BUY priority. But as a hard block based only on past ADD count, it can override current PIT strength and suppress otherwise valid Winner/Opportunity ADD. That conflicts with the current-PIT philosophy at the post-priority ADD safety layer.

## Actual Usage Evidence

Read-only artifact scans:

- `615` canonical `strategy_intelligence.json`, `position_management_evidence.json`, and `portfolio_construction.json` files scanned.
- `296` JSON files contained exact reason code `prior_add_history_limits_incremental_add`.
- `57` deduped run/date/symbol/campaign position-days had PM ADD blocked by count-only reason.
- Raw embedded copies: `113` PM rows and `337` total PM/PS/preflight reason nodes, due repeated strategy/eod and upstream-artifact embedding.

LIMIT_REACHED_CASE_COUNT: `57`

ADD_COUNT_BLOCKED_CASE_COUNT: `57`

STRONG_WINNER_ADD_SUPPRESSION_BY_COUNT_ONLY_COUNT: `46`

Definition used: deduped count-only blocked position-days with positive current campaign return. All 57 count-only rows had continuation quality `PASS`, downside risk `PASS`, PM reasons including `strong_trend_continuation`, `opportunity_rank_still_high`, and `no_loss_averaging`; 46/57 also had positive current campaign return. No future outcome, Historical PnL, MFE, or MAE was used to justify changing the cap.

ADD_COUNT_FIRST_CAUSE_DISTRIBUTION:

```text
prior_add_history_limits_incremental_add: 57
```

ADD_COUNT_CAP_MATERIALITY: `MATERIAL`

It is reached and blocks in existing runtime artifacts, concentrated mainly in `94320` and `76470`. It is not merely a stale comment or unused test expectation.

## G129 And Position Cap Separation

G129_RELATIONSHIP_TO_ADD_COUNT: `SEPARATE`

G129 is order-increment execution correctness: Submit must validate BUY_ADD quantity against PC/PS-bound order increment. It is not an ADD-count policy and does not decide whether a sixth ADD is investment-worthy.

POSITION_CAP_RELATIONSHIP_TO_ADD_COUNT: `OVERLAPPING_BUT_DISTINCT`

Position/concentration/headroom caps block excess size regardless of ADD count. A position can be below cap and still be blocked by ADD count; a position can be below five ADDs and still be blocked by cap/headroom/liquidity/lot/Cash. This weakens the independent safety value of a fixed count cap.

## Options

OPTION_A_JUDGMENT: `REVIEW_NOT_ACCEPT_AS_FINAL`

Keep current ADD count hard cap. This is safest against uncontrolled pyramiding but continues to suppress current PIT-strong campaigns solely because they already used five successful ADD increments. It is active and material.

OPTION_B_JUDGMENT: `PREFERRED`

Demote count from hard block to observability / soft risk evidence inside existing PM/PC/ADD Safety. This preserves campaign-local warning value without letting past action count alone override current PIT safety, cap/headroom, no-loss, Cash, lot, MCV/NCU, and G129.

OPTION_C_JUDGMENT: `VIABLE_BUT_NEEDS_FOCUSED_SHADOW`

Remove fixed count cap entirely and rely on existing Current-PIT + Safety controls. This is architecturally clean, but because the cap is active and material, removal should first be validated with focused shadow/differential evidence.

RECOMMENDED_OPTION: `Option B`

## Required Answers

- ADD_COUNT_CONSTRAINT_FOUND: `YES`
- CURRENT_ADD_MAX_COUNT: `5`
- ADD_COUNT_AUTHORITY_FILE: `src/ai_fund_lab_v2/strategy/position_management.py`; secondary mirror in `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- ADD_COUNT_AUTHORITY_FUNCTION: `_structured_add_worthiness_evidence()`; secondary `_campaign_aware_add_worthiness_state()`

- ADD_COUNT_SCOPE: `current open campaign successful BUY_ADD fills`
- ADD_COUNT_RESET_BOUNDARY: `full EXIT / flat close; later BUY starts new campaign`
- ADD_COUNT_IS_CAMPAIGN_LOCAL: `YES`

- ADD_COUNT_POLICY_TYPE: `HARD_BLOCK`
- ADD_COUNT_ORIGINAL_RATIONALE: `runaway pyramiding prevention / prior ADD safeguard / campaign churn prevention`
- ADD_COUNT_NUMERIC_VALUE_RATIONALE_FOUND: `NO`

- ADD_COUNT_IS_CURRENT_PIT_SAFETY_EVIDENCE: `MIXED_NO_FOR_COUNT_ALONE`

- EXISTING_ADD_SAFETY_LIST_COMPLETE: `YES`
- ADD_COUNT_CAP_SAFETY_REDUNDANCY: `HIGH`

- STRONG_WINNER_AT_LIMIT_BEHAVIOR: `PM converts ADD to HOLD via prior_add_history_limits_incremental_add`
- WEAK_POSITION_BELOW_LIMIT_BEHAVIOR: `Still blocked/reviewed by current PIT safety; count headroom is not authorization`

- ADD_COUNT_CAP_CONFLICTS_WITH_HISTORY_NEUTRAL_BUY_PHILOSOPHY: `MIXED`

- LIMIT_REACHED_CASE_COUNT: `57`
- ADD_COUNT_BLOCKED_CASE_COUNT: `57`
- STRONG_WINNER_ADD_SUPPRESSION_BY_COUNT_ONLY_COUNT: `46`

- ADD_COUNT_FIRST_CAUSE_DISTRIBUTION: `{prior_add_history_limits_incremental_add: 57}`
- ADD_COUNT_CAP_MATERIALITY: `MATERIAL`

- G129_RELATIONSHIP_TO_ADD_COUNT: `SEPARATE_ORDER_INCREMENT_CORRECTNESS_NOT_COUNT_POLICY`
- POSITION_CAP_RELATIONSHIP_TO_ADD_COUNT: `OVERLAPPING_BUT_DISTINCT`

- OPTION_A_JUDGMENT: `REVIEW_NOT_ACCEPT_AS_FINAL`
- OPTION_B_JUDGMENT: `PREFERRED`
- OPTION_C_JUDGMENT: `VIABLE_BUT_NEEDS_FOCUSED_SHADOW`
- RECOMMENDED_OPTION: `Option B`

- NEW_MODULE_REQUIRED: `NO`
- NEW_AUTHORITY_REQUIRED: `NO`

- PRODUCTION_CHANGE_JUSTIFIED_NOW: `NO_READ_ONLY_AUDIT`
- NEXT_STEP: `Open a focused shadow/differential design for demoting current open-campaign ADD count from hard block to soft risk evidence/observability while proving no regression in no-loss, deterioration, concentration/headroom, liquidity, lot, Cash, G129 order-increment scope, SELL/Winner protection, and Recent Exit/REENTRY semantics.`

## Gate

Production change is not authorized in GX. The finding is strong enough to justify a next-phase focused design/SHADOW gate, not an immediate source change.

Final Judgment: 現行ADD最大5回制限はcampaign-localでboundedではあるが、Current-PIT Safety単独としては弱く、既存artifact上では過去ADD回数だけで強いOpportunityへの追加資本投入を止めるmaterialなhistory-dependent hard constraintとして機能している。
