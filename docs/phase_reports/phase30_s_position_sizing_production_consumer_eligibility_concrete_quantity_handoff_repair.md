# Phase30-S - Position Sizing Production Consumer Eligibility / Concrete Quantity Handoff Repair

## Primary Judgment

`PHASE30_S_POSITION_SIZING_PRODUCTION_CONSUMER_ELIGIBILITY_CONCRETE_QUANTITY_HANDOFF_REPAIRED`

The Phase30-R zero-buy condition was not justified by Strategy filtering. The repaired path now allows final Portfolio Construction positive allocation to reach Position Sizing as production-consumable input, allows Position Sizing to decide lot-aware share quantities, and allows Runtime Planning to map positive quantity deltas to BUY intents.

## Root Cause

Two production handoff defects combined:

1. Final lot-aware Portfolio Construction artifacts were still emitted with Phase22 shadow-only metadata:
   - `artifact_lifecycle_status = DRAFT`
   - `runtime_consumer_eligibility = NOT_ELIGIBLE`
   - `allocation_decided = false`
   - `production_consumer_connected = false`

2. Position Sizing was hard-coded to remain non-production-consumable:
   - `runtime_consumer_eligibility = NOT_ELIGIBLE`
   - `share_quantity_decided = false`
   - `lot_rounding_decided = false`

Additionally, production PC rows carried the actionable BUY quality decision in `legacy_buy_quality_action` / `buy_quality_authority.quality_action`, while `quality_action` could contain Strategy Intelligence continuation semantics such as `SI_EVIDENCE_ELIGIBLE`. PS interpreted that as invalid BUY quality authority and withheld positive PC rows.

## Repair Status

`REPAIRED`

Implemented:

- Final lot-aware PC promotion only when `producer_result_status == PASS` and `lot_aware_final_reallocation.status == PASS`.
- Production-ready PC final artifacts become `ACCEPTED / ELIGIBLE`, with `allocation_decided = true`.
- PC still preserves PS quantity authority: `quantity_decided = false`.
- Final PS artifacts can become `ACCEPTED / ELIGIBLE` only when PS itself is `PASS` and the caller explicitly requests production handoff.
- PS sets `share_quantity_decided = true` and `lot_rounding_decided = true` only in the production-ready PASS path.
- Review/block inputs remain fail-closed and not production-consumable.
- PS now consumes canonical BUY quality authority from `legacy_buy_quality_action` or `buy_quality_authority.quality_action` when PC target rows carry SI continuation semantics in `quality_action`.

## PC -> PS Handoff

`PASS`

The final production route is:

`Strategy Intelligence -> Portfolio Construction draft -> PS preflight -> final lot-aware Portfolio Construction -> production Position Sizing -> Runtime Planning`

Draft/preflight artifacts remain non-production decision surfaces. Only the final PC artifact is promoted.

## Runtime Consumer Eligibility Before / After

Before:

- PC final: `NOT_ELIGIBLE`, `allocation_decided = false`
- PS final: `NOT_ELIGIBLE`, `share_quantity_decided = false`, `lot_rounding_decided = false`
- Runtime Planning: BUY intent count 0

After:

- PC final: `ELIGIBLE`, `allocation_decided = true`
- PS final: `ELIGIBLE`, `share_quantity_decided = true`, `lot_rounding_decided = true`
- Runtime Planning maps positive PS quantity deltas to `BUY_NEW`

## Concrete Quantity for Required Dates

Read-only target run:

`runtime-test-historical-extended-smoke-20260816T011219035058Z`

Target run artifacts were not mutated. Recalculation was performed under:

`/private/tmp/phase30_s_recalc`

| Date | PC Positive ADD Count | Before PS Positive Quantity Count | After PS Positive Quantity Count | Before Runtime BUY Intent Count | After Runtime BUY Intent Count |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-08-10 | 18 | 0 | 9 | 0 | 9 |
| 2022-08-12 | 19 | 0 | 10 | 0 | 10 |
| 2022-08-15 | 19 | 0 | 11 | 0 | 11 |

After Runtime Planning status:

- 2022-08-10: `PASS`
- 2022-08-12: `PASS`
- 2022-08-15: `PASS`

## Phase29 Capital Flag

`NO`

No Phase29 capital conversion recurrence was found or introduced. This repair does not alter basis, valuation, capital authority, safety cap math, lot cap policy, or historical fit logic.

## Strategy Integrity Flags

- Candidate Quality thresholds changed: `NO`
- Risk thresholds changed: `NO`
- BUY Quality thresholds changed: `NO`
- Expected Edge calibration changed: `NO`
- Portfolio Construction performance allocation logic changed: `NO`
- Lot/cap policy changed: `NO`
- Safety changed: `NO`
- Strategy model changed: `NO`
- Historical fit changed: `NO`
- Phase30-P SI migration preserved: `YES`

## BUY / SELL Independence

`PASS`

Regression coverage confirms:

- Positive new-exposure quantity maps to `BUY_NEW`.
- Review-required PC remains fail-closed.
- Lot-too-expensive cases keep quantity at 0 without forced BUY.
- Safety BLOCK remains not production-consumable.
- SELL / REDUCE and NO_ACTION semantics remain independent of the BUY handoff repair.
- Idempotency is preserved for repeated production PS builds.

## Regression / Compile

```text
compileall src/ai_fund_lab_v2/strategy = PASS
focused + related pytest = 288 passed, 60 warnings
```

The warnings are pre-existing `DeprecationWarning` messages in `runtime_v2/position_management/producer.py` around empty-array truth evaluation.

## Long Historical

`NO`

No 10BD or long Historical run was executed by Codex. The target run was not resumed, stopped, mutated, or repaired in place.

## Fresh 10BD Gate

`USER_OPERATED_FRESH_10BD_RERUN_READY`

## Recommended Next Task

`Phase30-T - Fresh 10BD Post-Repair Validation`

