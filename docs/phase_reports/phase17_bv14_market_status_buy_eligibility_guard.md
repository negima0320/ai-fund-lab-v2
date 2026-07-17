# Phase17-BV14 Market Status BUY Eligibility Guard

## Executive Summary

Phase17-BV13 confirmed that runtime symbol `36810` / V-cube had no 2026-07-01 quote because the issue was delisted effective 2026-07-01. Phase17-BV14 implemented a deterministic Runtime v2 BUY eligibility guard so new BUY orders are not allowed for symbols that are not listed as of the point-in-time market status authority, or that carry explicit delisting / special-supervision / BUY-ineligible status fields.

Final judgment:

```text
PHASE17_BV14_MARKET_STATUS_BUY_ELIGIBILITY_GUARD_ACCEPTED
```

## Root Cause Boundary

The immediate BV13 failure was not a price fallback problem. It exposed a missing upstream lifecycle guard: a symbol can remain BUY-selectable before or around a delisting lifecycle unless Runtime has a point-in-time market status authority and a final submit defense.

Local J-Quants `/v2/equities/master` snapshots available in Runtime v2 contain listing membership fields such as `Date`, `Code`, `MktNm`, and `ProdCat`. They do not contain an explicit special-supervision or scheduled-delisting field for `36810` on 2026-06-29 / 2026-06-30. Therefore Runtime can deterministically block:

- symbols absent from the latest snapshot not after `business_date`;
- symbols with explicit embedded `current_listed=false`;
- symbols with explicit `market_status`, `listing_status`, `special_supervision_status`, `delisting_status`, `scheduled_delisting_date`, or `buy_eligible=false` authority.

Runtime must not infer a 2026-06-29 BUY block from a future 2026-07-01 absence. That would be look-ahead leakage.

## Implemented Contract

Added a shared resolver:

- `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py`

The resolver emits:

- `status`
- `buy_eligibility`
- `reason_code`
- `authority_source`
- `authority_path`
- `authority_hash`
- `authority_as_of`
- `current_listed`
- `market_status`
- `listing_status`
- `special_supervision_status`
- `delisting_date`
- `point_in_time`
- `future_authority_used`

The resolver is common Runtime logic, not Historical-smoke-specific. Historical uses the PIT listed-issues snapshot store when available. Demo / Production can use embedded listed authority carried on Pending items and remain fail-closed at Submit when BUY listed authority is ineligible or missing.

## Runtime Integration

### Morning / Candidate Selection

`src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py` now evaluates BUY eligibility when a Historical listed-issues snapshot index exists. Ineligible candidates are excluded before order sizing / Pending creation, and the order plan records `buy_eligibility_contract`.

Evidence fields added to `MorningPipelineResult`:

- `buy_eligibility_status`
- `buy_eligibility_authority_source`
- `buy_eligibility_authority_path`
- `buy_eligibility_filtered_count`
- `buy_eligibility_review_count`
- `buy_eligibility_evidence`

### Pending / Listed Info Propagation

Selected Pending BUY items now carry BUY eligibility evidence in `listed_info`, including market-status authority source/path/hash/as-of and status fields.

### Submit Final Guard

`src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py` now evaluates BUY eligibility before broker preflight. If a BUY item is ineligible or review-required, Submit blocks before broker boundary with:

- `violated_policy=buy_market_status_eligibility`
- `should_have_been_blocked_at_planning=true`
- `submitted_count=0`

SELL items do not run the BUY eligibility guard.

## Safety / Fail-Closed Conditions

The implementation preserves fail-closed behavior for:

- missing or unreadable BUY authority;
- symbol mismatch between Pending symbol and listed authority code;
- explicit `current_listed=false`;
- explicit delisted / delisting-scheduled / special-supervision status;
- explicit scheduled delisting date;
- unknown / halted / suspended statuses requiring review.

It does not add stale price, average cost, or cost-basis fallback.

## 36810 / V-cube Authority Note

BV13 established by external issuer / exchange evidence that V-cube was delisted effective 2026-07-01. Runtime BV14 does not hard-code V-cube or `36810`. It enforces the formal authority available to Runtime:

- absent from PIT listed snapshot on or after delisting date: BLOCKED;
- explicit scheduled-delisting / special-supervision fields if provided: BLOCKED;
- pre-delisting date with only ordinary listed snapshot membership and no status field: not blocked by future knowledge.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/market_status/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/artifact_registry/technical_blocker_evidence.py`
- `tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py`

## Verification

Passed:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py -q
5 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_bv3_historical_listed_issues_snapshot_store.py tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py -q
30 passed

PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase17_bv9_historical_sell_quantity_authority.py tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase17_bv11_runtime_test_plan_persistence.py tests/runtime_v2/test_phase17_bv12_current_valuation_symbol_identity.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py -q
30 passed

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile ...
PASS

git diff --check
PASS
```

Full Runtime v2 regression:

```text
PYTHONPATH=src python3 -m pytest tests/runtime_v2 -q
936 passed, 5 failed
```

The 5 failures are the pre-existing PM sell-planning CLI/report failures observed before BV14 and are not in the BV14 BUY eligibility dependency path.

## Prohibited Operations Confirmation

Not executed:

- `runtime_test.py run`
- `runtime_test.py resume`
- `runtime_test.py reset`
- `runtime_test.py rollback`
- `runtime_test.py close`
- Frozen Run edit
- `.runtime` manual edit
- Persistent Ledger / Pending manual edit
- broker write
- Tachibana order
- J-Quants API fetch
- external notification
- AI retraining
- model / feature / label contract changes

## Fresh Rerun Readiness

Fresh rerun is safer after BV14 because new BUY candidates that are absent from PIT listed authority or explicitly market-status-ineligible will be excluded at Morning and blocked at Submit. However, BV13 position lifecycle work remains required for already-held positions whose quote disappears because of delisting / corporate action. BV14 intentionally does not solve existing-position settlement or corporate-action transition.
