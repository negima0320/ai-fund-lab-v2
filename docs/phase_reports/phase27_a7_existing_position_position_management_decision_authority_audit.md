# Phase27-A7 — Existing Position Position Management Decision Authority Audit

## Scope

This is a read-only audit of run-scoped evidence from `runtime-test-historical-smoke-20260804T074611098414Z`. No Strategy, BUY Quality, Portfolio Construction, Position Sizing, Planning, PM, Exit, Re-entry, Submit, Safety, or Runtime logic was modified. No fresh-run, resume, historical run, 100BD run, or long regression was executed.

## Primary Judgment

`PHASE27_A7_POSITION_MANAGEMENT_AUTHORITY_CONFIRMED`

Position Management authority is confirmed for the observed run: Runtime PM explicitly emitted ADD, HOLD, REDUCE, and EXIT decisions for existing positions. However, executable ADD did not occur in this run. PM ADD existed as a decision signal, but was marked `NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE` with `quantity_requested = 0`; Strategy Planning then represented existing positions as `NO_ACTION` / `NONE` rather than executable `BUY_ADD`.

## Evidence Counts

- Business days audited: 100
- Existing position decision rows: 364
- Rank1 existing-position cases: 86
- PM decisions: {'ADD': 145, 'HOLD': 162, 'REDUCE': 34, 'EXIT': 23}
- Planning intents: {'NO_ACTION': 364}
- Final actions: {'NO_ACTION': 319, 'REDUCE': 22, 'EXIT': 23}
- Quantity deltas: {'ZERO_DELTA': 364}

## Why Rank1 Becomes NO_ACTION

Rank1 existing-position cases were observed 86 times. In those cases, the deciding evidence is not rank alone:

- PM can emit `ADD` when it sees continuation evidence, but observed ADD rows state that ADD is outside SELL Planning scope and request zero quantity.
- Strategy Planning maps current-position zero delta to `NO_ACTION`, with reason codes such as `current_position_membership_resolved:current_portfolio_member` and `current_position_zero_delta_maps_to_no_action`.
- Therefore Rank1 can become `NO_ACTION` when the symbol is already held and no positive executable quantity delta is produced.

This is evidence from observed artifacts, not a recommendation.

## Who Determines Desired Quantity

For the audit table, desired quantity is taken first from `strategy/runtime_planning.json` `target_quantity_candidate`, then from `strategy/position_sizing.json` when planning evidence is absent. In observed existing-position planning rows, quantity delta is zero and Planning records `NO_ACTION` / `NONE`.

Important quantity semantics:

- `position_sizing.py` computes `target_quantity_candidate` from target notional, reference price, trading unit, then computes `quantity_delta_candidate = target_quantity_candidate - current_quantity`.
- `runtime_planning.py` consumes the sizing delta. If the intent is not a buy/sell order, it returns planned quantity `0` with `NOT_REQUIRED`.
- In observed existing-position rows, Planning's `target_quantity_candidate = 0` and `quantity_delta_candidate = 0` should not be interpreted as a reconciled total desired holding equal to PM's actual held quantity. It is Planning's no-order representation.
- Therefore A7 does not infer that desired total holdings equal current holdings arithmetically across all producers. It confirms that Runtime Planning made the order decision from current-position membership plus zero executable delta.

Relevant code evidence:

- `src/ai_fund_lab_v2/strategy/position_sizing.py:697` to `src/ai_fund_lab_v2/strategy/position_sizing.py:754` computes target quantity and quantity delta.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py:1054` to `src/ai_fund_lab_v2/strategy/runtime_planning.py:1065` maps non-order intents and zero quantity delta to no-order quantity.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py:1100` to `src/ai_fund_lab_v2/strategy/runtime_planning.py:1124` maps positive deltas to `BUY_ADD`, sell deltas to sell intents, and current-position zero delta to `NO_ACTION`.
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:580` to `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py:597` maps PM `EXIT`/`REDUCE` to sell-side runtime actions and PM `ADD` to `NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE`.

## Can ADD Occur Today?

Evidence-based answer: PM can request ADD, and did so 145 times. Planning can represent `BUY_ADD` in its taxonomy and code path. But in this run:

- PM ADD observed count: 145
- PM ADD runtime status: {'NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE': 145}
- Planning `BUY_ADD` observed count: 0
- Final executable ADD observed count: 0

So ADD exists as a PM decision signal, but executable additional BUY for existing holdings was not observed in the run-scoped evidence.

## HOLD vs NO_ACTION

HOLD and NO_ACTION are not identical terms.

- `HOLD` is produced by Runtime PM and means a position-level decision to keep the current holding.
- `NO_ACTION` is produced by Strategy Planning / runtime order planning and means no order is required.

Observed runtime meaning overlaps because PM `HOLD` and PM `ADD` can both consume into no sell order / no executable order. The producer, artifact, and authority are different.

## Exit Interaction

For every observed EXIT or REDUCE followed later by a BUY of the same symbol, A7 records the PM decision and later re-entry in `exit_hold_interaction.json`. The system had HOLD in the PM action taxonomy, so HOLD was representable, but the observed PM decision was REDUCE or EXIT. Counterfactual performance under HOLD is not observable from this evidence.

## Existing Position Philosophy

Observed implementation philosophy is best classified as:

`IMPLICIT_HOLD_WITH_PM_SELL_AND_NON_EXECUTED_ADD_SIGNALS`

The PM layer emits momentum-like ADD signals, but the run's executable order behavior is closer to maintaining current size unless PM emits sell-side REDUCE/EXIT. The current evidence does not prove an intended Strategy philosophy; it proves the observed runtime behavior.

## Deliverables

- `summary.json`
- `existing_position_daily_audit.csv`
- `existing_position_daily_audit.json`
- `rank1_existing_position_cases.json`
- `desired_quantity_trace.json`
- `pm_decision_trace.json`
- `hold_vs_no_action.json`
- `add_authority_audit.json`
- `exit_hold_interaction.json`
- `position_management_philosophy.json`
- `test_results.json`

## Limitations

- Runtime PM decisions are direct in `daily/<date>/position_management/pm_decisions.json`; Strategy PM artifact rows are adapter-style `UNRESOLVED` rows and are preserved separately.
- Full counterfactual HOLD-vs-EXIT outcomes are not available.
- Current quantity has multiple producers. A7 records PM quantity, Planning quantity, and Sizing quantity evidence without reconciling by inference.
