# Phase32-J — REENTRY Provenance Completion and Safety Classification Separation Repair

## Scope

- Target actual-path evidence: `runtime-test-historical-extended-smoke-20260830T001257154156Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T001257154156Z`
- Source commit observed in target run jobs: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Fresh-run/resume/replay/long Historical: NOT RUN
- Future price/return/regime/MFE/MAE/final campaign outcome/PnL: NOT USED

This repair is limited to REENTRY identity/provenance completion and status classification correctness. It does not tune Re-entry performance.

## KI-001 Remaining Root Cause

Phase32-I showed that actual REENTRY rows preserved prior EXIT reason/class and strict-prior dates, but all 147 observed REENTRY rows still had:

- empty `prior_campaign_id`
- empty `source_pm_decision_id`
- empty `source_decision_id`
- `prior_exit_provenance_status=REVIEW_REQUIRED`

Root cause:

- Canonical PM EXIT artifacts contained the missing authority fields.
- Runtime execution/fill evidence contained `source_pm_decision_id`, `source_decision_id`, and, in run evidence, `position_campaign_id`.
- The persistent ledger SELL rows retained `source_pm_decision_id` and `source_decision_id`, but had empty `position_campaign_id` / `campaign_id`.
- The closed campaign resolver only joined PM EXIT context by campaign id.
- When the ledger SELL row did not carry campaign id, the PM EXIT detail was not promoted into the closed campaign state even though the canonical PM decision id was available.

First provenance-loss boundary:

`persistent_ledger/executions.jsonl` SELL row -> `_resolve_prior_closed_campaigns_from_executions(...)`

The field was not lost because it never existed upstream. It was available upstream, but the resolver had only a campaign-id PM context lookup and lacked a source-id lookup path.

## Canonical Provenance Authority

The selected authority is a strict-prior merge of:

1. Persistent ledger execution history:
   - confirms the campaign was actually closed before REENTRY date,
   - supplies lifecycle execution provenance such as `source_decision_id`.
2. Strict-prior PM EXIT decision artifact:
   - supplies canonical PM EXIT decision context,
   - supplies `prior_campaign_id`, `prior_exit_reason`, reason codes, and `source_pm_decision_id`.

No downstream id guessing is introduced. If neither campaign id nor canonical source id can join to PM EXIT evidence, the existing explicit `REVIEW_REQUIRED` behavior remains.

## KI-001 Repair

Changed `src/ai_fund_lab_v2/strategy/shadow_runtime.py`:

- Added a strict-prior PM EXIT evidence index by `source_pm_decision_id` and `source_decision_id`.
- Kept campaign-id lookup as first choice.
- Added source-id lookup fallback for ledger SELL rows whose campaign id is missing.
- When PM EXIT context is found:
  - `prior_campaign_id` comes from PM EXIT context.
  - `source_pm_decision_id` comes from PM EXIT context or ledger row.
  - `source_decision_id` comes from ledger lifecycle row first, then PM context.
  - `prior_exit_provenance_status=PASS`.
- When PM EXIT context is not found:
  - existing ledger-only `REVIEW_REQUIRED` behavior remains.

This preserves canonical upstream provenance and avoids synthetic ids.

## KI-004 Root Cause

Phase32-I showed concrete classification collapse:

- REENTRY evaluations: 147
- `broker_eligibility_status=PASS`: 147
- `corporate_action_status=NO_EVENT`: 147
- `safety_restriction_status=FAIL_CLOSED`: 147

Root cause:

- `_reentry_safety_status(...)` derived safety status from broad reason text/reason codes.
- Its token list included non-Safety dimensions such as `broker`, `cash`, `buying_power`, and `corporate_action_blocking`.
- Actual REENTRY rows often carried supportive broker reason codes such as `BROKER_PRODUCT_CATEGORY_SUPPORTED`.
- That string alone was enough to mark `safety_restriction_status=FAIL_CLOSED`, even when broker authority was `PASS` and corporate-action authority was `NO_EVENT`.

First safety-classification violation boundary:

`_canonical_reentry_semantic_eligibility(...)` -> `_reentry_safety_status(...)`

## Corrected Classification Contract

REENTRY evidence now keeps these dimensions separate:

- prior EXIT context
- churn protection
- recovery/current-strength evidence
- candidate eligibility
- broker eligibility
- corporate actions
- genuine Safety restriction

Changed `src/ai_fund_lab_v2/strategy/portfolio_construction.py`:

- Added `broker_eligibility_status` and `corporate_action_status` to the REENTRY semantic eligibility result.
- Narrowed `_reentry_safety_status(...)` to:
  - honor explicit Safety-owned blocking statuses,
  - fail-closed for genuine Safety/hard-cap/quarantine reason tokens,
  - avoid treating broker/cash/buying-power/corporate-action text as Safety.
- Broker and corporate-action evidence remain separately visible and are not collapsed into Safety.

Rejected candidates rejected by cooldown, recovery, current evidence, prior-context insufficiency, broker, or corporate-action evidence remain rejected for those dimensions. This repair changes classification, not Re-entry policy.

## Strict-Prior PIT Confirmation

The target run already showed 147 / 147 REENTRY rows with `prior_exit_business_date < REENTRY business_date`.

The repair keeps the existing strict-prior filters:

- PM EXIT evidence is read only from `daily/<prior_date>` where `prior_date < business_date`.
- Ledger executions are consumed only where `execution_business_date < business_date`.
- Same-day/future EXIT rows remain excluded.

No J-Quants market-data validation was required because the defect was lifecycle provenance/classification, not market-data correctness.

## Files Changed

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `docs/phase_reports/phase32_j_reentry_provenance_safety_classification_repair.md`

## PM Re-Acceptance Status

`PM_REACCEPTANCE_REQUIRED = NO`

Reason: Phase32-J did not change `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` or PM accepted artifact source. The repair is in Strategy shadow prior-exit supply and Portfolio Construction REENTRY classification.

## Focused Validation Results

PASS:

- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
  - 23 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_e_portfolio_construction.py -k 'reentry or broker or corporate_action'`
  - 19 passed, 128 deselected
- `PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py`
  - 3 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py`
  - 12 passed
- `PYTHONPATH=src python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_s_ps_consumes_pc_buy_quality_reason_code_without_rethresholding`
  - 25 passed

Function-level actual-path re-resolution using target run evidence confirmed representative cases:

- `2022-10-05` / `83060`
  - `prior_campaign_id=pc-c87e70d86970ac69-83060-0001`
  - `source_pm_decision_id=pm-2022-10-04-83060-exit`
  - `source_decision_id=rp-2022-10-04-83060-sell_exit-a53ae6445098bc4c`
  - `prior_exit_provenance_status=PASS`
  - `broker_eligibility_status=PASS`
  - `corporate_action_status=NO_EVENT`
  - `safety_restriction_status=PASS`
  - REENTRY remains rejected by churn/recovery, not Safety.

- `2022-10-05` / `89180`
  - `prior_campaign_id=pc-95afc29b2233beaf-89180-0001`
  - `source_pm_decision_id=pm-2022-10-04-89180-exit`
  - `source_decision_id=rp-2022-10-04-89180-sell_exit-b60b334e267ea13a`
  - `prior_exit_provenance_status=PASS`
  - `safety_restriction_status=PASS`
  - REENTRY remains rejected by churn/recovery, not Safety.

- `2022-10-06` / `41650`
  - `prior_campaign_id=pc-b333e647de83be86-41650-0001`
  - `source_pm_decision_id=pm-2022-10-05-41650-exit`
  - `source_decision_id=rp-2022-10-05-41650-sell_exit-27df606601c635bf`
  - `prior_exit_provenance_status=PASS`
  - `safety_restriction_status=PASS`
  - REENTRY remains rejected by churn/recovery, not Safety.

## Regression Assessment

- Re-entry policy change: NO
- Safety rule change: NO
- Strategy semantic change: NO
- Phase32-C regression: NO
- Phase32-F regression: NO
- Phase32-H regression: NO
- G129 regression: NO

## Retest Required

Retest required: YES

Reason: focused tests pass and representative actual-path re-resolution passes, but a new Historical fresh-run is required to materialize the repaired REENTRY fields in run artifacts.

Exact user action:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-10-03 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

Codex did not run this command.

## Final Judgment

`PHASE32_J_REENTRY_PROVENANCE_AND_SAFETY_CLASSIFICATION_REPAIRED`

