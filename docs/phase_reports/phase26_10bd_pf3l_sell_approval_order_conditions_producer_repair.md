# Phase26-10BD-PF3L SELL Approval Order Conditions Producer Repair

## Primary Judgment

PHASE26_10BD_PF3L_SELL_APPROVAL_ORDER_CONDITIONS_PRODUCER_REPAIR_COMPLETE

## Primary Root Cause

The PM-derived SELL Planning producer approved a REDUCE/EXIT pending order without materializing `approval.approved_order_conditions`.

The failing runtime evidence was:

- Run: `runtime-test-historical-smoke-20260803T214213553894Z`
- Date/job: `2023-01-18:submit`
- Pending item: `opi-sell-reduce-pm-76470-001`
- Side/symbol: `SELL 76470`
- Quantity/amount: `2100.0 / 54600.0`
- Upstream quantity contract: `PASS`, `reduce_quantity_contract_pass`
- Pending approval status: `APPROVED`
- Direct defect: `approval.approved_order_conditions = null`
- Accepted generation binding statuses on pending/item/approval link: empty

## Broken Producer To Consumer Edge

Producer:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `run_sell_planning_pending_pipeline`
- `_write_add_pending`
- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `compose_with_existing_buy_pending`

Consumer:

- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`
- `run_submit_preflight`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

The SELL producer created `ApprovalDecision(status=APPROVED)` without `approved_order_conditions`. `build_approval_artifact` and `link_approval_to_pending` could only propagate the absent value, so Submit correctly blocked the order.

## Why PF3K Covered BUY But Not SELL

PF3K repaired the BUY Strategy Planning auto-approval path in `strategy_authority.py`. The failing PF3L path is PM-derived SELL Planning, which builds approval artifacts in `sell_pipeline.py` and can also regenerate approval during pending composition. Those producer paths were separate and did not reuse the BUY-only helper.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/approval/policy.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`

## Approval Artifact Changes

`build_approved_order_conditions` is now a common approval policy helper. BUY Strategy, SELL REDUCE/EXIT, PM ADD, and composed pending approvals all use the same condition payload shape.

`build_approval_artifact` already carries `decision.approved_order_conditions`; PF3L ensures SELL producers provide it.

## Authority Context Changes

SELL Planning now accepts canonical `accepted_generation_binding` and materializes it on:

- pending plan
- pending item
- pending approval link

The daily operation CLI resolves accepted generation through the existing resolver and passes binding evidence to SELL Planning. No Submit-side fabrication was added.

## Guard And Runtime Boundary

- Submit Guard changed: false
- Submit Guard weakened: false
- Fallback added: false
- Historical-only branch added: false
- Runtime decision behavior changed: false
- Strategy behavior changed: false

The change only repairs Producer -> ApprovalArtifact -> PendingLink -> SubmitGuard evidence wiring. It does not change Candidate, Opportunity, Strategy scoring, PM decisions, quantity selection, Safety, Submit feasibility, or broker write behavior.

## Regression

- Compile: PASS
- REDUCE/EXIT regression: PASS
- Pending composition regression: PASS
- PF3K non-regression: PASS
- PF3J/PF3I accepted generation non-regression: PASS

Commands:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/approval/policy.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py tests/runtime_v2/test_phase26_step8_accepted_generation_temporal_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
```

Result: `65 passed in 2.20s`.

## Direct Validation Against 2023-01-18 Shape

Added `test_phase26_pf3l_exit_sell_planning_materializes_approval_conditions_and_context`, which uses:

- business date `2023-01-18`
- mode `historical`
- symbol `76470`
- side `SELL`
- quantity `2100`
- PM source decision `EXIT`

It asserts that approval artifact and pending approval link both contain `approved_order_conditions`, and that pending/item/approval accepted generation IDs are aligned.

## User Resume Readiness

READY

User resume command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260803T214213553894Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
