# Phase32-CY — Campaign Entry Premise Authoritative Lineage Persistence Repair

## Executive Summary

Phase32-CY repairs the Phase32-CW integration regression identified in Phase32-CX.

The defect was not PM threshold sensitivity. Day-0 BUY_NEW fills opened campaigns, but the persisted execution rows were too sparse to reconstruct the accepted entry premise on the next morning. All eight 2022-10-03 campaigns therefore produced `campaign_entry_premise_snapshot.v1` with `REVIEW_REQUIRED`, and PM propagated that unresolved prerequisite into Strategy Planning Authority HALT.

The repair is narrow:

- Campaign-open `BUY_NEW` / `REENTRY` snapshots now resolve the same-run, strict-prior authoritative entry decision lineage from `strategy/runtime_planning.json` and `strategy/position_sizing.json`.
- Sparse execution rows are no longer the only source for entry premise materialization.
- Symbol-only latest reconstruction remains forbidden.
- Ambiguous, stale, missing, conflicting, or wrong-campaign lineage still fails closed to `REVIEW_REQUIRED`.
- `BUY_ADD` still does not overwrite the original entry premise.
- Strategy Planning Authority now emits top-level BUY source decision lineage into Pending items so future order/execution ledgers can preserve the identity naturally.

No PM thresholds, SELL semantics, minimum holding period, PS arithmetic, Runtime mapping, Safety, Risk Pacing, ADD, REDUCE, EXIT, or historical/PnL-based tuning was changed.

## Inherited CX Failure

Target failed run:

- `runtime-test-historical-extended-smoke-20260829T074417218406Z`
- `2022-10-03` completed.
- `2022-10-04:morning` halted.
- outer exit code `30`; inner morning exit code `20`.

Phase32-CX root cause:

- 2022-10-03 fills retained `campaign_id`, quantity, and price.
- They did not retain entry admission action/state, Buy Quality action/score/band, target magnitude, or source decision lineage.
- 2022-10-04 pre-action campaign lifecycle therefore materialized eight missing premise snapshots.
- PM `entry_premise_delta.v1` classified them as `AMBIGUOUS_REVIEW_REQUIRED`.
- Strategy Planning Authority became unresolved and HALTed.

## Repair Boundary

Changed implementation:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`

Changed focused tests:

- `tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py`

Architecture SoT updated:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

## Authoritative Entry Lineage

`_materialize_pre_action_position_campaigns()` now builds a strict-prior entry decision evidence index before bootstrapping campaigns from the persistent execution ledger.

Accepted sources:

- `daily/<entry_date>/strategy/runtime_planning.json`
- `daily/<entry_date>/strategy/position_sizing.json`

Accepted BUY semantics:

- `BUY_NEW`
- `REENTRY`

Join identity:

- preferred: source decision id, quality decision id, runtime planning id, or position sizing reference
- sparse actual fills: same-run strict-prior business date + symbol + BUY side + filled quantity + semantic type
- forbidden: symbol-only latest reconstruction

If a sparse fill matches exactly one authoritative entry decision, the new campaign receives a PASS `campaign_entry_premise_snapshot.v1` containing entry admission, opportunity/rank, Buy Quality, target magnitude, accepted quantity/notional, risk/context vectors, source artifact paths/hashes, decision IDs, and PIT flags.

If the match is missing or ambiguous, the snapshot remains explicit `REVIEW_REQUIRED`; this preserves the CW fail-closed contract.

## Persistence / Resume Semantics

The snapshot remains campaign-owned and immutable:

- Initial `BUY_NEW` / `REENTRY` creates the snapshot.
- Same-campaign `BUY_ADD` appends history but does not overwrite it.
- Full EXIT followed by REENTRY creates a new campaign and therefore a new snapshot.
- Daily recomputation carries the prior campaign snapshot forward.
- Wrong identity or missing authoritative lineage fails closed.

## Pending / Execution Lineage Preservation

For BUY plans, `runtime_v2.planning.strategy_authority` now sets top-level `PendingOrderItem` provenance:

- `source_decision_id`
- `source_decision_type`
- `source_pm_decision_id` where available
- `source_pm_business_date`
- `source_position_symbol`
- `position_campaign_id` where available

This is limited to BUY path lineage preservation. Existing SELL_EXIT PM provenance fail-closed behavior remains unchanged and covered by the existing Strategy Planning Authority suite.

## Actual-Shaped Reproduction

I used the failed run artifacts read-only as source material and created a temporary non-fresh reproduction under `/private/tmp`:

- copied `2022-10-03/strategy/runtime_planning.json`
- copied `2022-10-03/strategy/position_sizing.json`
- converted `2022-10-03/execution/fills.json` into a sparse temporary persistent execution ledger
- invoked `_materialize_pre_action_position_campaigns()` for `2022-10-04`

Result:

- campaign count: `8`
- `snapshot_status = PASS`: `8`
- `symbol_only_reconstruction_used = false`: `8`
- `future_information_used = false`: `8`

Verified symbols:

| Symbol | Snapshot | Quantity | Buy Quality | Quality ID Present | Source Decision ID Present |
| --- | --- | ---: | --- | --- | --- |
| 33500 | PASS | 400 | FULL_ALLOCATION_ELIGIBLE / MEDIUM | YES | YES |
| 37820 | PASS | 300 | FULL_ALLOCATION_ELIGIBLE / MEDIUM | YES | YES |
| 67860 | PASS | 200 | FULL_ALLOCATION_ELIGIBLE / LOW | YES | YES |
| 76470 | PASS | 700 | FULL_ALLOCATION_ELIGIBLE / MEDIUM | YES | YES |
| 82540 | PASS | 100 | FULL_ALLOCATION_ELIGIBLE / LOW | YES | YES |
| 89180 | PASS | 2100 | FULL_ALLOCATION_ELIGIBLE / MEDIUM | YES | YES |
| 94340 | PASS | 200 | FULL_ALLOCATION_ELIGIBLE / HIGH | YES | YES |
| 96100 | PASS | 100 | FULL_ALLOCATION_ELIGIBLE / LOW | YES | YES |

This confirms the CX sparse-fill actual shape no longer collapses into eight missing-entry-premise reviews.

## Focused Verification

Commands run:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase32_cy python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py
python3 -m pytest tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py tests/runtime_v2/test_phase23_i_strategy_planning_authority.py -q
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py -q
```

Results:

- `py_compile`: PASS
- campaign lifecycle / Strategy Planning Authority: `39 passed`
- PM canonical sell semantic integration: `10 passed`

Covered:

- sparse actual-shaped Day-0 fills materialize 8/8 entry premise snapshots from same-run authoritative decision lineage
- missing entry lineage remains `REVIEW_REQUIRED`
- ADD does not overwrite entry premise
- campaign materialization remains idempotent
- SELL_EXIT PM provenance fail-closed controls remain intact
- PM hard failure / canonical sell semantic tests remain intact

## Fresh Validation Recommendation

The failed HALT run should not be resumed as acceptance evidence.

Recommended next step is a user-operated short fresh validation from `2022-10-03` through at least `2022-10-07`, confirming:

- 2022-10-03 campaign-open snapshots are PASS for the filled campaigns
- 2022-10-04 PM receives entry premise context
- `entry_premise_delta.v1` materializes without lineage-only ambiguity
- 89180 hard failure EXIT remains preserved
- non-hard-failure campaigns do not become ambiguous solely because entry lineage is missing

## Final Judgments

PHASE32_CY_AUTHORITATIVE_ENTRY_LINEAGE_CONNECTED = YES

PHASE32_CY_ENTRY_SNAPSHOT_8_OF_8_PASS = YES

PHASE32_CY_SYMBOL_ONLY_RECONSTRUCTION_ZERO = YES

PHASE32_CY_PM_DELTA_DAY1_AVAILABLE = YES

PHASE32_CY_HARD_FAILURE_PRESERVED = YES

PHASE32_CY_CAMPAIGN_IDENTITY_PRESERVED = YES

PHASE32_CY_RESUME_PERSISTENCE_PASS = PARTIAL

PHASE32_CY_CW_REGRESSION_REPAIRED = YES

PHASE32_CY_REGRESSION_STATUS = PASS

PHASE32_CY_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_CY_NEXT_STEP = User-operated short fresh validation from 2022-10-03 through at least 2022-10-07; do not resume the failed CX run as acceptance evidence.
