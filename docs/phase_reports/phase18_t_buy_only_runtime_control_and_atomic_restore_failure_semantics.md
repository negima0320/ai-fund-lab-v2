# Phase18-T BUY-only Runtime Control and Atomic Restore Failure Semantics

Run ID: `phase18t-buy-only-control-atomic-restore-20260717T000000Z`

Final Judgement: `PHASE18_T_BUY_ONLY_CONTROL_AND_ATOMIC_RESTORE_COMPLETE`

Secondary Judgements: `RU4_COMPLETE`, `RU5_COMPLETE`, `PHASE18_READY_FOR_FINAL_REVIEW`, `PHASE19_NOT_READY`

## Scope

- Included: RU4, RU5, Q-GAP-007, Q-GAP-008
- Excluded: RU1, RU2, RU3, Phase19, Runtime Switch, Historical Runtime Full Path, Broker Write, Production BUY

## RU4

Status: `COMPLETE`

BUY lifecycle gate blocks BUY planning and BUY submit only; SELL continuity permissions remain independent.

## RU5

Status: `COMPLETE`

Restore failure is RESTORE_FAILED -> CRITICAL with accepted state and registry hash invariance evidence.

## Acceptance Matrix

| Category | Status | Evidence |
|---|---:|---|
| BUY-only MODEL_UNHEALTHY | PASS | BUY planning/submit BLOCK; Current, Valuation, PM, Safety, SELL planning, SELL authorization allowed |
| BUY-only INSUFFICIENT_EVIDENCE | PASS | BUY fail-closed; SELL continuity permissions remain PASS when SELL dependency is normal |
| BUY-only MARKET_NO_OPPORTUNITY | PASS | No forced BUY; SELL continuity remains PASS |
| BUY REVIEW_REQUIRED | PASS | BUY review blocks BUY planning/submit; SELL continuity authorization stage reached |
| run_daily_operation Call Graph | PASS | buy_lifecycle_sell_authorization_continuity stage added to morning entrypoint path |
| restore event failure | PASS | RESTORE_FAILED -> CRITICAL; accepted state and registry hashes unchanged |
| restore index failure | PASS | RESTORE_FAILED -> CRITICAL; no partial index |
| restore checkpoint failure | PASS | RESTORE_FAILED -> CRITICAL; no partial checkpoint |
| temporary cleanup failure | PASS | RESTORE_FAILED -> CRITICAL; manual recovery required |
| restore validation failure | PASS | RESTORE_FAILED -> CRITICAL; audit evidence generated |
| Registry Accepted Update | NOT_MODIFIED | No production registry accepted state mutation performed |
| Runtime Switch | NOT_MODIFIED | No Runtime accepted set switch performed |
| BUY Restart | NOT_MODIFIED | No BUY restart or broker write invoked |

## Verification

- `targeted`: `21 passed`
- `phase18`: `28 passed, 2 sklearn convergence warnings`
- `cross_contract`: `96 passed, 2 sklearn convergence warnings`
- `compile`: `PASS`

## Runtime Safety

Registry accepted変更、Runtime switch、BUY restart、Broker write、Production BUY、Historical Runtime Full Pathはいずれも未実施です。

## Final

`PHASE18_T_BUY_ONLY_CONTROL_AND_ATOMIC_RESTORE_COMPLETE`

`RU4_COMPLETE` / `RU5_COMPLETE` / `PHASE18_READY_FOR_FINAL_REVIEW` / `PHASE19_NOT_READY`
