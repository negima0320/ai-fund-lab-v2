# Phase17-BV15 Opportunity BUY Eligibility Contract Fix

## Executive Summary

Phase17-BV15 fixed the Runtime v2 contract mismatch where Opportunity AI ranking order was treated as BUY permission. Opportunity ranking is now preserved as ranking evidence, but a BUY candidate must also pass Opportunity BUY eligibility:

- `expected_edge_score > 0`
- no `no_buy_reason`
- symbol/date/artifact authority match
- finite numeric score

Final judgment:

```text
PHASE17_BV15_OPPORTUNITY_BUY_ELIGIBILITY_CONTRACT_ACCEPTED
AI_RETRAIN_NOT_REQUIRED
NEGATIVE_EXPECTED_EDGE_BUY_BLOCKED
NO_BUY_REASON_ENFORCED
SELL_PATH_UNCHANGED
BV14_MARKET_STATUS_GUARD_PRESERVED
FRESH_RERUN_SAFE
```

## Root Cause

For `36810`, Opportunity AI produced:

- `expected_edge_score = -0.06934237`
- `expected_return = -0.06934237`
- `no_buy_reason = non_positive_expected_edge_score`
- `buy_rank = 2`
- `is_top5 = true`

The downstream Runtime path used ranking / Top-N membership as if it were BUY eligibility. This mixed two different meanings:

- relative ranking within Opportunity output;
- absolute permission to create a BUY order.

The AI output was already expressing “do not buy”; the execution contract failed to enforce it.

## Implemented Contract

Added a shared resolver:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py`

The resolver returns:

- `status`
- `buy_eligibility`
- `reason_code`
- `expected_edge_score`
- `expected_return`
- `no_buy_reason`
- `buy_rank`
- `opportunity_artifact_path`
- `opportunity_artifact_hash`
- `business_date`
- `feature_date`
- `opportunity_business_date`
- `opportunity_feature_date`

BUY is allowed only when Opportunity eligibility is `PASS / BUY_ELIGIBLE`.

## Morning Fix

`src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` no longer converts rank-only rows into BUY signals. `load_ai_planning_signals_from_opportunity_artifact()` filters out Opportunity rows that fail eligibility while preserving the ranking artifact itself.

`src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py` also evaluates Opportunity eligibility against the authoritative Opportunity artifact path from `buy_ai_context`. Ineligible symbols are excluded before allocation, sizing, order plan, Pending, approval, and Submit.

The Morning result and order plan now record `opportunity_buy_eligibility_contract` and per-symbol eligibility evidence.

## Pending Lineage

Pending BUY items now carry Opportunity lineage in `listed_info`:

- `opportunity_buy_eligibility_status`
- `opportunity_expected_edge_score`
- `opportunity_no_buy_reason`
- `opportunity_buy_rank`
- `opportunity_artifact_path`
- `opportunity_artifact_hash`
- `opportunity_business_date`
- `opportunity_feature_date`
- `opportunity_eligibility_policy_version`
- `opportunity_eligibility_reason`

Submit uses these fields to detect missing, stale, or changed Opportunity authority.

## Submit Guard Fix

`src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` now revalidates Opportunity BUY eligibility for BUY items before broker preflight. If Opportunity evidence is missing, negative, has `no_buy_reason`, date mismatched, symbol mismatched, or hash mismatched, Submit blocks before Demo / Historical / Production broker boundaries.

SELL items do not run this guard.

## BV14 Integration

BUY now requires both:

1. BV14 Market Status BUY eligibility
2. BV15 Opportunity BUY eligibility

Neither guard overwrites the other. Either guard can block or require review.

## AI Retraining

No AI retraining was performed or required. The model already emitted the negative expected edge and `no_buy_reason`. BV15 only corrects Runtime consumption of that output.

## Verification

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py -q
7 passed

PYTHONPATH=src python3 -m pytest ... BV15/BV14/Opportunity/Submit/BV9-BV12 related suite
51 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py -q
34 passed

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile ...
PASS

git diff --check
PASS
```

Full Runtime v2 regression:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2 -q
943 passed, 5 failed
```

The remaining 5 failures are the known PM sell-planning CLI/report failures present before BV15. BV15-specific failures were resolved by updating BUY fixtures to carry formal Opportunity evidence.

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run edit
- `.runtime` manual edit
- Ledger manual edit
- Pending manual edit
- Opportunity artifact manual modification
- AI retraining
- J-Quants API fetch
- Tachibana / Demo / Production broker write
- external notification
- existing HALT Run resume

## Fresh Rerun Readiness

Fresh rerun is safe for this contract. If all Opportunity candidates are non-positive, Runtime now produces zero BUY orders and preserves cash rather than filling position slots with negative-edge symbols.

BV13 existing-position lifecycle remains a separate concern for already-held delisted / corporate-action symbols.
