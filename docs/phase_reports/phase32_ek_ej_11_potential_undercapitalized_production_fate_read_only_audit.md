# Phase32-EK — EJ 11 Potential Undercapitalized Production Fate READ-ONLY Audit

## Scope

This is a READ-ONLY audit of the 11 `POTENTIAL_UNDERCAPITALIZED` rows identified by Phase32-EJ.

No Production code, SHADOW code, active run state, source run artifact, `.runtime`, Pending, Ledger, fresh-run, resume, recover, replay, source transition, or long Historical execution was modified or executed in Phase32-EK.

No future outcome, later return, MFE/MAE, final campaign outcome, or Historical PnL was used to judge whether ADD should have occurred.

## Evidence Used

- EJ report: `docs/phase_reports/phase32_ej_winner_position_size_adequacy_positive_next_lot_shadow_audit.md`
- EI report: `docs/phase_reports/phase32_ei_eh_add_blocked_negative_root_cause_read_only_audit.md`
- EH report: `docs/phase_reports/phase32_eh_pc_security_opportunity_shadow_consumer_production_preservation_audit.md`
- EJ output: `reports/runtime_tests/analysis/phase32_ej_position_size_adequacy_20260903T020000`
- Source run: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260902T060955933565Z`
- G115 / G119 / G129 ADD authority reports:
  - `docs/phase_reports/phase31_g115_add_marginal_competition_staged_authoritative_binding.md`
  - `docs/phase_reports/phase31_g119_pc_final_authority_ps_consistency_repair.md`
  - `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`

## Reference Contract

The applicable ADD authority contracts are:

- G115: PC owns staged ADD marginal increment authorization; PS owns discrete quantity.
- G119: PS must consume final PC discrete executable authority and must not revive stale Cash-winner evidence to zero a PC-final-positive row.
- G129: Submit validates BUY_ADD against the canonical ADD order increment, not cumulative position-scope quantity.

Therefore an EJ `POTENTIAL_UNDERCAPITALIZED` row is correctly handled by Production when:

1. PC materializes positive ADD increment authority.
2. PS materializes executable BUY_ADD quantity from that authority.
3. Runtime plans BUY_ADD without redecision.
4. Pending/Submit preserves order-increment provenance.
5. Submit either accepts and execution fills, or a later item-scoped guard blocks the item with explicit authority.

## EJ_11_PRODUCTION_FATE_TABLE

| Date | Symbol | Campaign | PC target/current | PS / Runtime BUY_ADD | Submit / Execution fate | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| 2022-10-06 | 94340 | `pc-c09afbf08095a527-94340-0001` | 4.1% / 2.8% | 100 shares, `rp-2022-10-06-94340-buy_add-455c991e25a1cb11` | Filled 100, order item `strategy-6417a66bd4204e43b682`; next-day qty 300 | `ACTUAL_ADD_EXECUTED` |
| 2022-10-11 | 94340 | `pc-c09afbf08095a527-94340-0001` | 5.5% / 4.1% | 100 shares, `rp-2022-10-11-94340-buy_add-309f67bd6ec97d6d` | Pending item `strategy-4867762ba2903dcc6c75` became `REVIEW_REQUIRED`: reserved notional exceeds dynamic cash capacity; no fill | `LEGITIMATELY_BLOCKED_LATER` |
| 2022-10-12 | 94340 | `pc-c09afbf08095a527-94340-0001` | 5.6% / 4.2% | 100 shares, `rp-2022-10-12-94340-buy_add-1b06a65af209dc1f` | Filled 100, order item `strategy-0a41eafbb114d97fa05c`; next-day qty 400 | `ACTUAL_ADD_EXECUTED` |
| 2022-10-13 | 94340 | `pc-c09afbf08095a527-94340-0001` | 7.1% / 5.7% | 100 shares, `rp-2022-10-13-94340-buy_add-e04e072f332d1290` | Filled 100, order item `strategy-c1ac91726ffa6f70aa71`; next-day qty 500 | `ACTUAL_ADD_EXECUTED` |
| 2022-11-01 | 94320 | `pc-401763653bc4df1d-94320-0001` | 4.6% / 3.1% | 100 shares, `rp-2022-11-01-94320-buy_add-c6e4f927c483a41f` | Filled 100, order item `strategy-7912f30c16f958cc4315`; next-day qty 300 | `ACTUAL_ADD_EXECUTED` |
| 2023-02-13 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 4.9% / 3.7% | 100 shares, `rp-2023-02-13-94320-buy_add-ef1cf4f990f804d5` | Filled 100, order item `strategy-bd576d402e7c016c0890`; next-day qty 400 | `ACTUAL_ADD_EXECUTED` |
| 2023-02-15 | 54010 | `pc-0972f0d0a80bbd70-54010-0001` | 9.4% / 4.7% | 100 shares, `rp-2023-02-15-54010-buy_add-2da07333250070de` | Filled 100, order item `strategy-bab19d3aafed97f60135`; next-day qty 200 | `ACTUAL_ADD_EXECUTED` |
| 2023-02-22 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 6.6% / 5.3% | 100 shares, `rp-2023-02-22-94320-buy_add-f9fcb6278b970eb6` | Filled 100, order item `strategy-4ad7c49efb7a04d5958f`; next business-day qty 500 | `ACTUAL_ADD_EXECUTED` |
| 2023-02-24 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 7.9% / 6.6% | 100 shares, `rp-2023-02-24-94320-buy_add-e58a3bf559207190` | Filled 100, order item `strategy-9050c6d38a894c168625`; next-day qty 600 | `ACTUAL_ADD_EXECUTED` |
| 2023-03-15 | 94320 | `pc-7c5bd9294d48b016-94320-0001` | 9.1% / 7.8% | 100 shares, `rp-2023-03-15-94320-buy_add-971c6c6062d5dd0b` | Filled 100, order item `strategy-c697f53a1efd7370853f`; next-day qty 700 | `ACTUAL_ADD_EXECUTED` |
| 2023-05-31 | 59550 | `pc-15bcec8077b3dc77-59550-0001` | 4.5% / 3.7% | 100 shares, `rp-2023-05-31-59550-buy_add-5a62700107c14f37` | Filled 100, order item `strategy-00b4609768d48289a5c1`; next-day qty 500 | `ACTUAL_ADD_EXECUTED` |

## ACTUAL_ADD_EXECUTED_COUNT

`10`

Ten of the 11 EJ potential rows produced direct same-day BUY_ADD fill evidence with:

- `source_decision_type = BUY_ADD`
- source runtime planning id preserved in `source_decision_id`
- `order_plan_item_id`
- `pending_item_id`
- `position_campaign_id`
- BUY fill quantity of 100 shares

The one non-filled row, 2022-10-11 94340, did not silently disappear. It reached Pending/Submit with full BUY_ADD provenance and was item-scoped reviewed before submission.

## NON_EXECUTED_POTENTIAL_ADD_ROOT_CAUSE_PROFILE

| Root cause | Count | Case |
| --- | ---: | --- |
| Pending/Submit item-scoped cash capacity review | 1 | 2022-10-11 94340 |

The 2022-10-11 94340 path:

- PM: `ADD`
- PC: positive staged ADD increment
- PS: 100-share BUY_ADD quantity
- Runtime plan: `rp-2022-10-11-94340-buy_add-309f67bd6ec97d6d`
- Pending item: `strategy-4867762ba2903dcc6c75`
- Pending state at Submit: `REVIEW_REQUIRED`
- Review reason: `reserved notional exceeds dynamic cash capacity`
- Submit result: not submitted
- Execution/fill: none

This is not a G129 quantity-scope failure. The submit guard evidence still records canonical discrete quantity authority as `PASS`; the final blocker is cash capacity / reserved-notional review.

## REPEATED_CAMPAIGN_PRODUCTION_FATE

### `94340|pc-c09afbf08095a527-94340-0001`

Potential rows:

- 2022-10-06: executed BUY_ADD 100
- 2022-10-11: reviewed, not submitted, cash capacity
- 2022-10-12: executed BUY_ADD 100 under fresh same-campaign authority
- 2022-10-13: executed BUY_ADD 100

Classification:

`GRADUAL_REAL_ADDS_WITH_ONE_LEGITIMATE_CASH_REVIEW`

The repeated 94340 potential set does not show repeated unexplained suppression. Production added on three of four potential dates; the only skipped row was reviewed at final submit authority, and a fresh same-campaign ADD executed on the next available decision date.

### `94320|pc-7c5bd9294d48b016-94320-0001`

Potential rows:

- 2023-02-13: executed BUY_ADD 100
- 2023-02-22: executed BUY_ADD 100
- 2023-02-24: executed BUY_ADD 100
- 2023-03-15: executed BUY_ADD 100

Classification:

`GRADUAL_REAL_ADDS_CONFIRMED`

No unexplained suppression was found for the repeated 94320 campaign.

## FINAL_ADD_AUTHORITY_CONSISTENCY

`PASS`

For executed rows:

- PM supplied ADD intent and campaign identity.
- PC supplied staged positive ADD increment authority.
- PS produced 100-share executable BUY_ADD quantities.
- Runtime planned BUY_ADD without changing the Strategy decision.
- Pending and Submit preserved `source_decision_id`, `source_pm_decision_id`, `order_plan_item_id`, and `position_campaign_id`.
- Execution/fill persisted `source_decision_type = BUY_ADD` and the same campaign id.

For the one non-executed row:

- PC/PS/Runtime authority was positive and internally consistent.
- The item reached Pending/Submit with provenance intact.
- The final suppressor was explicit item-scoped cash capacity review: `reserved notional exceeds dynamic cash capacity`.
- No silent zeroing, campaign split, quantity mismatch, or G129 order-increment violation was observed.

## Closure Decision

`UNEXPLAINED_MISSED_ADD_COUNT = 0`

The EJ 11 clean potential rows are already handled by current Production:

- 10 rows executed BUY_ADD.
- 1 row was legitimately reviewed by final cash capacity authority and not submitted.

Therefore the current ADD investigation should close with no Production change.

## Required Final Answers

- `EJ_11_PRODUCTION_FATE_TABLE`: included above.
- `ACTUAL_ADD_EXECUTED_COUNT`: `10`
- `NON_EXECUTED_POTENTIAL_ADD_ROOT_CAUSE_PROFILE`: one item-scoped cash capacity review, 2022-10-11 94340.
- `REPEATED_CAMPAIGN_PRODUCTION_FATE`: 94340 gradual real ADDs with one legitimate cash review; 94320 repeated real ADDs confirmed.
- `FINAL_ADD_AUTHORITY_CONSISTENCY`: `PASS`
- `UNEXPLAINED_MISSED_ADD_COUNT`: `0`
- `ADD_INVESTIGATION_CLOSURE_RECOMMENDATION`: `CLOSE_NO_CHANGE`
- `PRODUCTION_REPAIR_JUSTIFIED`: `NO`
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `SHADOW_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `RUNTIME_STATE_MUTATED`: `NO`
- `LONG_RUNTIME_EXECUTED`: `NO`
- `FUTURE_OUTCOME_USED`: `NO`
- `HISTORICAL_PNL_USED_FOR_DECISION`: `NO`
- `NEXT_RECOMMENDED_STEP`: Close the current ADD undercapitalization investigation; preserve current Production ADD authority and move to the next non-ADD Phase32 question.

## Final Judgment

`PHASE32_EK_EJ_11_POTENTIAL_UNDERCAPITALIZED_CASES_PRODUCTION_FATE_ACCEPTED_CLOSE_NO_CHANGE`
