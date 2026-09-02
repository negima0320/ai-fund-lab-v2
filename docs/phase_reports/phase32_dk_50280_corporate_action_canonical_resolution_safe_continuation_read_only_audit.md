# Phase32-DK — 50280 Corporate Action Canonical Resolution / Safe Continuation READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Current continuation boundary: `2023-10-11:sell_planning`
- Execution in this phase: READ-ONLY audit plus this report only.

No resume, recovery, replay, fresh-run, source/config change, Pending mutation, Ledger mutation, Runtime state mutation, or Corporate Action resolution mutation was executed.

## Mandatory References Read

- `docs/phase_reports/phase32_dj_20231011_sell_planning_halt_root_cause_read_only_audit.md`
- Prior Corporate Action / 2023-10-11 reports:
  - `docs/phase_reports/phase32_z_20231011_submit_halt_root_cause_audit.md`
  - `docs/phase_reports/phase32_aa_corporate_action_planning_pending_submit_authority_alignment_repair.md`
  - `docs/phase_reports/phase32_aw_2023_10_11_fresh_run_recurrent_sell_planning_halt_root_cause_audit.md`
  - `docs/phase_reports/phase32_ax_mixed_sell_review_fresh_run_contract_repair.md`
  - `docs/phase_reports/phase32_ba_post_partial_execution_current_valuation_authority_repair.md`
  - `docs/phase_reports/phase32_bb_2023_10_12_data_readiness_halt_read_only_audit.md`
  - `docs/phase_reports/phase32_bc_mixed_review_pending_day_rollover_lifecycle_repair.md`
- Runtime Test Command Guide / Specification.
- Corporate Action authority architecture:
  - `docs/02_architecture/autonomous_ai_operations_architecture.md`
  - `docs/phase_reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_design.md`
- Current source:
  - `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
  - `src/ai_fund_lab_v2/runtime_v2/executable_membership_guard.py`
  - `src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py`
  - `src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py`
  - `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
  - `scripts/runtime_test.py`

## Current 50280 State

`50280_CURRENT_STATE_REVALIDATED = YES`

Runtime-owned position state as of `2023-10-10`:

- held quantity: `100`
- average price: `438.0`
- current price / valuation close: `463.7`
- market value: `46370.0`
- cost basis: `43800.0`
- unrealized PnL: `2569.999999999999`
- quantity basis: `ADJUSTED`
- valuation price basis: `ADJUSTED`
- valuation source: run-scoped `2023-10-10` J-Quants normalized adjusted quote.

Campaign evidence:

- `position_campaign_id = pc-d468aca3b9d6da8f-50280-0001`
- opened business date: `2023-10-04`
- buy quantity: `100`
- buy price: `438.0`
- campaign status: `OPEN`
- campaign identity authority status: `COMPLETE`

PM / Runtime Planning:

- PM decision id: `pm-2023-10-11-50280-reduce`
- PM decision type: `REDUCE`
- Strategy PM action: `EXIT`
- PM reason codes include:
  - `pm_discrete_control_persistent_deterioration_exit`
  - `risk_increased_but_trend_not_broken`
  - `strategy_intelligence_sell_side_evidence_connected`
- Runtime Planning intent: `SELL_EXIT`
- source decision id: `rp-2023-10-11-50280-sell_exit-ef85562eee72162f`
- planned / pending quantity: `100`

Pending item:

- pending item id: `strategy-b5086c01c378aa03084d`
- side: `SELL`
- quantity: `100`
- state: `REVIEW_REQUIRED`
- approved: `false`
- batch submit status: `ITEM_REVIEW_REQUIRED`
- item review reason: `corporate_action_event_not_resolved`
- `source_decision_id`, `source_decision_type`, `source_pm_decision_id`, and `order_plan_item_id` are present.
- `position_campaign_id` and `campaign_id` are empty in the Pending / order-plan materialization.

Corporate Action authority:

- artifact: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`
- schema: `runtime_v2_corporate_action_adjustment_authority_v1`
- status: `REVIEW_REQUIRED`
- event status: `IMPACT_DETECTED`
- event type: `UNKNOWN_ADJFACTOR_IMPACT`
- event type authority: `not_available_from_adjfactor_only`
- effective date: `2023-10-11`
- adjustment factor: `0.3333333333333333`
- PIT validation: `PASS`
- future data used: `false`
- current quantity / broker available / pending / submit quantity: `100`
- already applied status: `UNKNOWN`
- quantity reconciliation status: `REVIEW_REQUIRED`
- price reconciliation status: `REVIEW_REQUIRED`
- ledger/current/pending adjustment status: `UNKNOWN`
- pre/post adjustment quantity: `null`
- reason: `corporate_action_event_type_or_adjustment_application_unresolved`
- reason codes include:
  - `corporate_action_type_unresolved`
  - `corporate_action_ledger_adjustment_missing`
  - `corporate_action_current_adjustment_missing`
  - `corporate_action_pending_quantity_stale`
  - `corporate_action_already_applied_not_confirmed`
  - `corporate_action_adjusted_quantity_missing`

## PIT Market Evidence

Run-scoped J-Quants raw OHLCV for `50280`:

| Date | O | H | L | C | AdjO | AdjH | AdjL | AdjC | AdjFactor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `2023-10-10` | `1360.0` | `1435.0` | `1360.0` | `1391.0` | `453.3` | `478.3` | `453.3` | `463.7` | `1.0` |
| `2023-10-11` | `456.0` | `474.0` | `455.0` | `461.0` | `456.0` | `474.0` | `455.0` | `461.0` | `0.3333333333333333` |

Run-scoped normalized quote uses adjusted price basis for both dates:

- `2023-10-10 Close = 463.7`
- `2023-10-11 Close = 461.0`

This proves that the market data stream contains an adjustment impact signal at `2023-10-11`. It does not, by itself, prove event type, share quantity transformation, odd-lot semantics, or whether the Runtime-owned position quantity has already been adjusted.

The same-day Strategy `corporate_event.json` reports `50280` as `KNOWN_NO_EVENT`, but that artifact is not sufficient to override the raw `AdjFactor` impact detector. The architecture explicitly states that `AdjFactor` is an impact signal, not an event-type authority, and that unknown corporate-action type remains fail-closed until accepted PIT authority resolves the event and proves idempotent Ledger/Current/Pending lineage.

## Corporate Action Semantics

`50280_CORPORATE_ACTION_TYPE = UNKNOWN`

Evidence supports `UNKNOWN_ADJFACTOR_IMPACT`, not a formally confirmed split, reverse split, consolidation, rights/allocation event, or other concrete event type.

Reason:

- The direct authority source is `jquants_raw_equities_bars_daily_adjfactor`.
- The authority payload itself says `event_type_authority = not_available_from_adjfactor_only`.
- The event evidence carries no old/new quantity, record date, or standalone event taxonomy authority.
- The accepted architecture prohibits inferring the event type solely from `AdjFactor`.

## Quantity Transformation

`50280_CANONICAL_QUANTITY_TRANSFORMATION = INSUFFICIENT_EVIDENCE`

Known:

- pre-HALT Runtime-owned quantity: `100`
- proposed submit quantity: `100`
- broker-equivalent available quantity in feasibility evidence: `100`
- factor: `0.3333333333333333`
- effective date: `2023-10-11`

Not proven:

- event type
- pre-event share quantity
- post-event share quantity
- adjustment direction
- rounding and odd-lot handling
- whether Runtime Current/Ledger have already applied the event

Therefore the canonical post-CA executable quantity is not derivable from current accepted evidence.

## Price Transformation

`50280_CANONICAL_PRICE_TRANSFORMATION = INSUFFICIENT_EVIDENCE`

Known:

- `2023-10-10` raw close `1391.0` and adjusted close `463.7`.
- `2023-10-11` raw close and adjusted close are both `461.0`.
- Current valuation is already on adjusted price basis.

Not proven:

- whether the `2023-10-11` price is the mechanically adjusted post-event quote, an actual market move on a post-event basis, or both.
- whether the Runtime-owned quantity basis is synchronized to the same post-event basis as the adjusted price.

Price evidence is enough to identify a basis transition risk, not enough to authorize quantity-bearing SELL.

## Already-Applied State

`50280_CORPORATE_ACTION_ALREADY_APPLIED_STATUS = UNKNOWN`

The authority artifact explicitly says:

- `already_applied_status = UNKNOWN`
- `ledger_adjustment_status = UNKNOWN`
- `current_adjustment_status = UNKNOWN`
- `pending_adjustment_status = UNKNOWN`
- `double_adjustment_detected = false`

`double_adjustment_detected = false` only means the current artifact did not detect a known double application. It does not prove that the event has been applied, not applied, or applied exactly once.

## Broker / Ledger / Position Reconciliation

`50280_POST_CA_POSITION_RECONCILIATION = REVIEW_REQUIRED`

Ordinary position quantities agree:

- Runtime position: `100`
- campaign quantity: `100`
- pending SELL quantity: `100`
- broker-equivalent available quantity: `100`

Corporate Action basis reconciliation does not agree to PASS:

- adjusted post-event quantity is missing.
- ledger/current/pending adjustment statuses are unknown.
- already-applied status is unknown.
- event type is unknown.

So ordinary position authority is internally consistent, but post-CA adjusted-basis authority is not resolved.

## Can SELL 100 Be Proven Safe?

`50280_EXIT_100_SAFE = NOT_DETERMINED`

SELL 100 may ultimately be the right disposition, but the current canonical evidence does not prove it. The missing proof is not PM intent. PM and Runtime Planning already want `SELL_EXIT`. The missing proof is Corporate Action quantity authority.

Plain reasoning such as "held quantity is 100" is insufficient because the same run also proves an unresolved adjustment impact at the exact sell date.

## Disposition

`50280_CANONICAL_DISPOSITION_ACTION = NOT_DETERMINED_PENDING_CA_RESOLUTION`

The preferred canonical disposition remains existing `SELL_EXIT` if a future resolution proves:

- resolved event type;
- effective date `2023-10-11`;
- factor `0.3333333333333333`;
- adjusted Runtime-owned quantity;
- Runtime Ledger/Current/Pending are on the same adjusted basis;
- already-applied status is confirmed;
- no double adjustment risk;
- submit quantity `100` is less than or equal to adjusted owned and broker-available quantity.

Without that proof, neither `SELL_EXIT` nor `EXIT_ADJUSTED_QUANTITY` can be safely materialized.

## Required CA Resolution Artifact

`50280_REQUIRED_CA_RESOLUTION_ARTIFACT = .runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`

The existing canonical artifact path is correct, but its content is unresolved. A valid resolving artifact must remain under the existing schema and must prove at minimum:

- `status = PASS`
- `business_date = 2023-10-11`
- `symbol = 50280`
- resolved `event_type`
- `event_type_authority` from an accepted PIT source or operator-reviewed evidence contract, not from numeric factor inference alone
- `effective_date = 2023-10-11`
- `source_artifact_path` and `source_artifact_hash` bound to run-scoped PIT evidence
- `pit_validation_status = PASS`
- `future_data_used = false`
- `adjustment_factor = 0.3333333333333333`
- pre/post quantity fields, especially `post_adjustment_quantity` or `adjusted_runtime_owned_quantity`
- price/basis reconciliation fields
- `ledger_adjustment_status = PASS`
- `current_adjustment_status = PASS`
- `pending_adjustment_status = PASS`
- `already_applied_status = CONFIRMED`
- `double_adjustment_detected = false`
- lineage proving that the Ledger, Current, Pending, and submit quantities are all on the same basis
- reviewer/operator identity if human confirmation is part of the contract.

## Human Review / Historical Resolution Path

`CANONICAL_HUMAN_REVIEW_PATH_FOUND = NO`

I found a dataset-policy human-review contract in `ai_lifecycle`, but it is for approving dataset policy with formal limitations. It is not a Runtime-owned per-symbol CA quantity-resolution command and does not mutate or materialize `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`.

The `runtime_test.py repair-ca-quarantine-continuation` command is also not a 50280 resolution path:

- It is scoped to Historical symbol quarantine continuation.
- Its classifier requires a `submit` job shape.
- It does not resolve event type, adjusted quantity, price basis, or already-applied status.
- It writes quarantine-continuation evidence and run-state continuation for eligible historical symbol quarantine cases.
- It is not applicable to the current halt at `2023-10-11:sell_planning` for a per-symbol Corporate Action adjustment authority artifact.

`HISTORICAL_CA_RESOLUTION_PATH = NOT_FOUND_FOR_50280_ADJUSTMENT_AUTHORITY`

There is a canonical artifact schema and validator, but no supported operator command was found that can resolve this exact 50280 adjustment authority safely and generically.

## Plain Pending Approval

`PLAIN_PENDING_APPROVAL_SAFE = NO`

Approving the Pending SELL alone would bypass the unresolved quantity/basis authority. The blocker is not merely approval state; it is Corporate Action adjustment reconciliation. A Pending-only approval would still leave Submit Guard with the same unresolved event type, missing adjusted quantity, unknown already-applied status, and stale pending-quantity risk.

## 76920 Quarantine Lifecycle

`76920_QUARANTINE_LIFECYCLE_STATUS = NEEDS_FURTHER_AUDIT`

Current facts:

- `76920` BUY is blocked by `.runtime/runtime_state/corporate_action_quarantine/historical_symbol_registry.json`.
- Registry entry:
  - first detected date: `2022-10-28`
  - latest checked date: `2022-10-19`
  - resolution status: `UNRESOLVED`
  - quarantine status: `QUARANTINED`
  - production applicability: `NEVER`
  - continuation eligibility: `ALLOWED_FOR_HISTORICAL_REPLAY_ONLY`
- Same-day `2023-10-11` Strategy corporate-event evidence says `KNOWN_NO_EVENT` for `76920`.

The current quarantine implementation is intentionally symbol-persistent until formally resolved; it does not decay based on later clean same-day corporate-event evidence. Whether that persistence is too strong is analogous to previous long-lived penalty lifecycle problems, but it is secondary to 50280 and should be audited separately before changing it.

## 50280 Campaign ID Loss

`50280_PENDING_CAMPAIGN_ID_LOSS_STATUS = CONFIRMED_DEFECT_NEEDS_REPAIR_BEFORE_SAFE_SUBMIT`

PM and position-campaign evidence retain:

- `pc-d468aca3b9d6da8f-50280-0001`

Runtime Planning / Pending preserve source decision and PM decision lineage, but `position_campaign_id` and `campaign_id` are empty on the `50280` SELL item.

This is not the first HALT reason, because the run stops on Corporate Action safety authority before Submit/Execution. It is still a correctness defect for any future resolved SELL/EXIT path: if 50280 becomes executable, campaign identity must be restored before safe Submit/Execution so the exit closes the intended open campaign.

## Resume Preconditions

`RESUME_PRECONDITIONS`

Before same-run continuation can be considered safe:

- 50280 Corporate Action authority is resolved to `PASS` under `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`.
- The resolving evidence proves event type, effective date, factor, adjusted quantity, price/basis reconciliation, already-applied status, and no double adjustment.
- Source artifact path/hash remain run-scoped to `runtime-test-historical-extended-smoke-20260902T060955933565Z`.
- No future data is used.
- Pending/safety authority is consistent after resolution.
- 50280 Pending/Runtime Planning campaign identity is restored to `pc-d468aca3b9d6da8f-50280-0001` before any executable SELL crosses Submit/Execution.
- Reviewed 76920 BUY remains non-submittable unless independently resolved by its own canonical authority.
- No target-date Submit artifact, Execution artifact, broker side effect, Ledger order, fill, position transition, or cash mutation exists for `2023-10-11`.
- Resume/recovery entry gate is checked under current source baseline without stale cross-run authority.

Current side-effect audit:

- `2023-10-11` morning external-effect audit: `PASS`
- `2023-10-11` sell_planning external-effect audit: `PASS`
- broker order API calls: `0`
- production order executed: `false`
- demo submit executed: `false`
- no submit/execution job was reached in the current run.

## Resume vs Fresh-Run

`POST_RESOLUTION_CONTINUATION_MODE = NOT_DETERMINED`

Same-run continuation is plausible because the halt occurred before Submit/Execution and completed evidence through `2023-10-10` remains valid. However, DK cannot classify `RESUME_SAFE` because the required CA resolution artifact and campaign-id repair are not currently materialized.

Fresh-run is not proven required by DK. The safer current classification is:

- same-run continuation: blocked pending canonical resolution/repair;
- fresh-run required: not proven;
- continuation point after future repair: `2023-10-11:sell_planning`, or a formally supported regeneration boundary if the repair explicitly requires regenerating Pending.

## Production Repair Decision

`STRATEGY_CHANGE_REQUIRED = NO`

The Strategy decision is not the defect. PM/Runtime Planning correctly express a desire to exit 50280. The unresolved layer is Runtime Corporate Action authority and campaign identity materialization.

`PRODUCTION_REPAIR_REQUIRED = YES`

Required repair is not a Strategy repair. It is a Runtime authority/tooling repair:

1. Add or expose a canonical Corporate Action adjustment resolution path for per-symbol impacted orders, including explicit human/operator-reviewed evidence when standalone PIT event type is not available.
2. Ensure the resolved artifact is validated through the existing `runtime_v2_corporate_action_adjustment_authority_v1` contract and consumed by Planning/Pending/Submit without weakening fail-closed behavior.
3. Repair 50280 SELL campaign-id propagation before any resolved SELL/EXIT becomes executable.
4. Defer 76920 quarantine lifecycle decay/resolution to a separate audit/repair unless it becomes the next direct blocker.

`REPAIR_SCOPE = RUNTIME_CORPORATE_ACTION_RESOLUTION_TOOLING_PLUS_SELL_CAMPAIGN_ID_PROPAGATION`

No candidate selection, BQ, Entry, tick semantics, SELL thresholds, PM philosophy, REENTRY, ADD/G129, or Winner Retention change is indicated.

## No Mutation

- `PRODUCTION_CHANGE_EXECUTED = NO`
- `TARGET_RUN_MUTATED = NO`

## Required Final Answers

1. `TARGET_RUN`: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
2. `50280_CURRENT_STATE_REVALIDATED`: YES; held `100`, campaign `pc-d468aca3b9d6da8f-50280-0001`, PM `EXIT`/Runtime `SELL_EXIT`, Pending SELL `100`, CA authority unresolved.
3. `50280_CORPORATE_ACTION_TYPE`: `UNKNOWN`
4. `50280_CANONICAL_QUANTITY_TRANSFORMATION`: `INSUFFICIENT_EVIDENCE`
5. `50280_CANONICAL_PRICE_TRANSFORMATION`: `INSUFFICIENT_EVIDENCE`
6. `50280_CORPORATE_ACTION_ALREADY_APPLIED_STATUS`: `UNKNOWN`
7. `50280_POST_CA_POSITION_RECONCILIATION`: `REVIEW_REQUIRED`
8. `50280_EXIT_100_SAFE`: `NOT_DETERMINED`
9. `50280_CANONICAL_DISPOSITION_ACTION`: `NOT_DETERMINED_PENDING_CA_RESOLUTION`; preferred eventual action remains `SELL_EXIT` only if CA authority proves quantity/basis safety.
10. `50280_REQUIRED_CA_RESOLUTION_ARTIFACT`: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json` with PASS event type, quantity, price/basis, already-applied, and idempotency lineage.
11. `CANONICAL_HUMAN_REVIEW_PATH_FOUND`: NO
12. `PLAIN_PENDING_APPROVAL_SAFE`: NO
13. `HISTORICAL_CA_RESOLUTION_PATH`: `NOT_FOUND_FOR_50280_ADJUSTMENT_AUTHORITY`
14. `76920_QUARANTINE_LIFECYCLE_STATUS`: `NEEDS_FURTHER_AUDIT`
15. `50280_PENDING_CAMPAIGN_ID_LOSS_STATUS`: `CONFIRMED_DEFECT_NEEDS_REPAIR_BEFORE_SAFE_SUBMIT`
16. `RESUME_PRECONDITIONS`: CA authority PASS, campaign id restored, Pending/safety consistent, no stale review artifact, no double adjustment, no target-date side effects, reviewed 76920 still blocked unless independently resolved.
17. `POST_RESOLUTION_CONTINUATION_MODE`: `NOT_DETERMINED`
18. `STRATEGY_CHANGE_REQUIRED`: NO
19. `PRODUCTION_REPAIR_REQUIRED`: YES
20. `REPAIR_SCOPE`: Runtime CA resolution tooling / artifact materialization plus SELL campaign-id propagation; no Strategy semantic change.
21. `PRODUCTION_CHANGE_EXECUTED`: NO
22. `TARGET_RUN_MUTATED`: NO
23. `NEXT_RECOMMENDED_STEP`: Implement a narrow canonical Runtime Corporate Action resolution/operator-review artifact path for impacted SELL quantity authority, plus focused campaign-id propagation validation for resolved SELL_EXIT. Do not manually approve Pending or resume this run before that repair is accepted.
24. `FINAL_JUDGMENT`: `PHASE32_DK_50280_CA_RESOLUTION_REQUIRED_SELL_100_NOT_CANONICALLY_PROVEN_SAFE`

## Final Judgment

`PHASE32_DK_50280_CA_RESOLUTION_REQUIRED_SELL_100_NOT_CANONICALLY_PROVEN_SAFE`

The user policy permits disposing of 50280 if canonical evidence supports it. Current evidence does not yet support it. The correct next move is not Strategy change and not manual Pending approval; it is a narrow Runtime Corporate Action resolution path that can prove the adjusted executable quantity and already-applied state, then allow the existing SELL/EXIT semantics to proceed if the resolved authority passes.
