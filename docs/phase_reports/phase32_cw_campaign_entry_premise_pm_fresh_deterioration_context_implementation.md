# Phase32-CW — Campaign Entry Premise / PM Fresh-Deterioration Context Implementation

## Executive Summary

Phase32-CW implements the Phase32-CV design for the `ENTRY_PM_CONTEXT_MIGRATION_GAP`.

The repair is narrow:

- `campaign_entry_premise_snapshot.v1` is materialized when a ledger-proven `BUY_NEW` / `REENTRY` opens a new campaign.
- The snapshot is campaign-scoped, persisted in `positions/position_campaigns.json`, and not overwritten by later `BUY_ADD`.
- Strategy Intelligence forwards the campaign-owned snapshot through `lifecycle_context`.
- PM materializes `entry_premise_delta.v1` and separates `KNOWN_AT_ENTRY` caution from `FRESH_DETERIORATION`, `PERSISTENT_DETERIORATION`, `HARD_FAILURE`, `TRUE_BREAKDOWN`, `IMPROVEMENT`, and `AMBIGUOUS_REVIEW_REQUIRED`.
- `KNOWN_AT_ENTRY` evidence alone cannot create a fresh REDUCE / EXIT escalation.
- Hard stop, true breakdown, persistent deterioration, Safety/Risk hard blocks, ADD semantics, REDUCE/EXIT ownership, and PIT flags are preserved.

No minimum holding period was added. No threshold, SELL rule, PM scoring, PS, Runtime, Safety, ADD, or REDUCE/EXIT arithmetic was changed.

## Scope

Changed implementation files:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`

Changed tests:

- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py`

Architecture SoT updated:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

## Entry Snapshot

`_new_campaign_from_execution()` now attaches `entry_premise_snapshot` and `entry_premise_snapshot_status` to newly opened campaigns.

When execution rows carry entry premise fields, the snapshot records:

- campaign id / symbol / entry business date
- entry admission action/state
- rank / opportunity
- Buy Quality action/score/band
- base target and quality-authorized target
- accepted quantity/notional
- accepted caution reasons
- trend/momentum, relative strength, participation, persistence, downside/risk, regime/context
- source lineage
- `future_information_used = false`
- `historical_outcome_used = false`

When strict-prior execution evidence is too sparse, the campaign still materializes an explicit `REVIEW_REQUIRED` snapshot with `silent_reconstruction_used = false`. This prevents silent symbol-only reconstruction.

`BUY_ADD` keeps the original snapshot and updates only campaign event/history fields.

## PM Delta

PM now emits `entry_premise_delta.v1` on each position row and inside `canonical_sell_semantic_evidence`.

The delta records:

- known-at-entry risk
- current risk
- new risk dimensions
- improved dimensions
- persistent weakness dimensions
- true-breakdown dimensions
- hard-failure status
- fresh-deterioration status
- entry-known-only status
- comparison confidence
- reason codes
- recommended PM context class

Action behavior:

- `HARD_FAILURE`: preserves immediate EXIT.
- `TRUE_BREAKDOWN`: preserves existing REDUCE/EXIT authority.
- `FRESH_DETERIORATION`: remains actionable.
- `PERSISTENT_DETERIORATION`: remains actionable.
- `KNOWN_AT_ENTRY`: suppresses REDUCE/EXIT when the current weakness is only the entry-known caution.
- `IMPROVEMENT`: does not block HOLD/ADD.
- `AMBIGUOUS_REVIEW_REQUIRED`: fail-closed to `UNRESOLVED` when a premise is required.

## Focused Verification

Commands run:

```bash
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py -q
env PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase32_cw python3 -m py_compile src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Result:

```text
23 passed
py_compile PASS
```

Covered cases:

- known-at-entry caution suppresses generic EXIT escalation
- hard-stop EXIT is preserved
- missing required entry premise fails closed
- entry premise snapshot persists across daily campaign materialization
- ADD does not overwrite the initial entry premise
- sparse legacy execution evidence creates explicit `REVIEW_REQUIRED`

## Preserve / Non-Changes

Preserved:

- PM action ownership
- hard stop
- true breakdown
- Safety/Risk Pacing semantics
- canonical SELL semantics
- ADD semantics
- Entry / Buy Quality authority
- Production/Demo/Historical common PIT contract
- no future information
- no historical outcome use

Not changed:

- PM thresholds
- SELL thresholds
- minimum holding period
- PS quantity arithmetic
- Runtime/Pending/Orders/Execution
- REDUCE/EXIT arithmetic
- ADD admission/value semantics

## Repair Readiness

This is ready for user-operated short fresh validation. Expected acceptance signal is not performance. It is actual-path materialization of:

- campaign `entry_premise_snapshot`
- Strategy Intelligence lifecycle propagation
- PM `entry_premise_delta`
- hard-failure preservation
- known-entry-only non-escalation
- missing-premise `AMBIGUOUS_REVIEW_REQUIRED`

## Final Judgments

PHASE32_CW_ENTRY_PREMISE_SNAPSHOT_IMPLEMENTED = YES

PHASE32_CW_CAMPAIGN_SCOPED_PERSISTENCE = YES

PHASE32_CW_PM_DELTA_IMPLEMENTED = YES

PHASE32_CW_KNOWN_AT_ENTRY_NON_ESCALATION = YES

PHASE32_CW_FRESH_DETERIORATION_ACTIONABLE = YES

PHASE32_CW_HARD_FAILURE_PRESERVED = YES

PHASE32_CW_PERSISTENT_DETERIORATION_PRESERVED = YES

PHASE32_CW_REENTRY_NEW_PREMISE = YES

PHASE32_CW_RESUME_SAFE = PARTIAL

PHASE32_CW_REGRESSION_STATUS = PASS

PHASE32_CW_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_CW_NEXT_STEP = User-operated short fresh validation from 2022-10-03 through at least 2022-10-07 to confirm actual artifacts materialize `campaign_entry_premise_snapshot.v1` and `entry_premise_delta.v1`, with 89180 hard-stop EXIT preserved and known-at-entry-only caution no longer reused as fresh REDUCE/EXIT evidence.
