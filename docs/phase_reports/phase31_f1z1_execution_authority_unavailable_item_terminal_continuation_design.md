# Phase31-F1Z1 - Execution Authority Unavailable Item Terminal Continuation Design

## PRIMARY_JUDGMENT

PHASE31_F1Z1_EXECUTION_AUTHORITY_UNAVAILABLE_ITEM_TERMINAL_CONTINUATION_DESIGNED

F1Z1 defines a Production-common Submit / execution-feasibility boundary contract for a valid order intent that cannot be executed because canonical execution authority is unavailable. The SELL or BUY decision remains intact; Runtime does not fabricate price, order, fill, cash, position, or PnL. The affected item becomes a known non-executable terminal item, while unrelated independently valid items may continue.

## REQUIRED_READING

Read and incorporated:

- `docs/phase_reports/phase31_f1z0_34940_2022_12_08_ohlcv_missing_root_cause_audit.md`
- `docs/phase_reports/phase31_f1y_submit_retry_ordering_existing_sell_reconciliation_repair.md`
- `docs/phase_reports/phase31_f1x_post_f1w_actual_resume_submit_terminalization_audit.md`
- `docs/phase_reports/phase31_f1v_2022_12_08_submit_halt_actual_artifact_root_cause_audit.md`
- `docs/phase_reports/phase31_f1w_item_scoped_review_partial_submit_terminalization_idempotency_repair.md`
- `docs/phase_reports/phase31_f1t_canonical_sell_authority_buy_sell_composite_pending_continuation_repair.md`
- `docs/phase_reports/phase31_f1l_same_day_equivalent_sell_pending_idempotency_repair.md`
- `docs/phase_reports/phase31_c0a_discrete_lot_reduce_persistence_exit_escalation_audit.md`
- `docs/03_operations/runtime_test_command_guide.md`
- current `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- current `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- current `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- focused Submit/Pending lifecycle tests in `tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py` and non-executable REDUCE summarize tests.

## DECISION_AUTHORITY_VS_EXECUTION_FEASIBILITY

Strategy / PM decision authority answers:

```text
SHOULD_WE_SELL?
```

Execution feasibility answers:

```text
CAN_THIS_ORDER_BE_EXECUTED_NOW_WITH_VALID_AUTHORITY?
```

For 34940 on 2022-12-08:

- PM / Runtime intent remains `SELL_EXIT`.
- Current position is 100 shares.
- F1Z0 found zero canonical normalized 2022-12-08 OHLCV rows, one raw all-NaN J-Quants row, no approved same-day alternate execution price authority, and no authorized previous-close fallback.
- Therefore execution feasibility is `NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE`.

## CANONICAL_TERMINAL_STATUS

NOT_EXECUTABLE

This reuses the existing generic non-executable lifecycle family already used by REDUCE below minimum tradable quantity. It does not require a new item terminal status name.

## CANONICAL_TERMINAL_REASON

EXECUTION_AUTHORITY_UNAVAILABLE

Recommended detailed field:

```text
execution_feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE
```

## NEW_SCHEMA_REQUIRED

NO

No new high-level terminal status schema is required if implementation reuses:

- generic item state/status `NOT_EXECUTABLE`;
- a new reason code `EXECUTION_AUTHORITY_UNAVAILABLE`;
- a new execution feasibility detail `NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE`;
- existing string-valued Pending item state / feasibility fields and Submit guard evidence payloads.

Implementation may add optional observability fields to existing artifacts, but F1Z1 does not require a new Strategy, PM, or Pending plan state enum.

## SELL_DECISION_PRESERVED

YES

The SELL_EXIT decision is preserved as the decision-time PM/Runtime intent. It is not rewritten to HOLD and is not deleted. The terminal outcome belongs to the execution feasibility layer, not the decision layer.

## NON_EXECUTABLE_CONTRACT_REUSE

PARTIAL

Reusable REDUCE lifecycle structure:

- terminal item status `NOT_EXECUTABLE`;
- explicit reason code;
- explicit `execution_feasibility_status`;
- `intentional_no_order = true`;
- `pending_order_generated = false`;
- no broker/order side effect;
- no position mutation;
- same-day retry prevention;
- next-day fresh re-evaluation;
- Runtime continuation when state is known and no integrity ambiguity remains.

Not reusable as-is:

- REDUCE below-minimum is decided in Position Sizing / Sell Planning before Pending order creation.
- 34940 is an otherwise approved Submit item whose same-day execution price authority is unavailable at Submit / execution-feasibility preflight.
- The owner therefore changes from quantity materialization to Submit boundary terminalization, while the terminal non-executable lifecycle shape is reused.

## ITEM_STATE_TRANSITION

Target transition:

```text
APPROVED executable intent
  -> Submit reconciles any existing accepted side effects first
  -> Submit preflight resolves execution authority unavailable
  -> no adapter submit
  -> no broker side effect
  -> no ledger order
  -> item.state = NOT_EXECUTABLE
  -> item.feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE
  -> item terminal evidence records retry_eligible_same_day = false
```

The item must not remain `APPROVED_AND_RETRYABLE` unless a separate explicit retry contract exists. For F1Z1, no same-day retry contract exists because the same decision-time execution authority is unavailable.

## ITEM_TERMINALIZATION_PREVENTS_SAME_DAY_RETRY

YES

## POSITION_STATE

For 34940:

- no order submitted;
- no fill;
- no execution;
- no position mutation.

## POSITION_QUANTITY_AFTER_TERMINALIZATION

100

## POSITION_STATE_MUTATED

NO

The position remains open and must be re-evaluated normally on the next business day.

## CASH_AND_EXPOSURE_STATE

For SELL execution-authority-unavailable:

- no sale proceeds;
- no fake realized PnL;
- no cash increase;
- position remains exposed.

## FAKE_CASH_MUTATION

NO

## FAKE_REALIZED_PNL

NO

## FAKE_EXECUTION_EVENT

NO

## NEXT_BUSINESS_DAY_REEVALUATION

The terminal non-executable item is same-day terminal only. It is not an automatic carry-forward order.

On the next business day:

- refresh PIT evidence;
- PM re-evaluates the still-open position;
- if PM again decides EXIT, build a new current-day SELL intent;
- use current-day execution authority;
- if PM changes decision, follow the current-day decision.

## STALE_SELL_INTENT_CARRY_FORWARD

NO

## EXECUTION_AUTHORITY_UNAVAILABLE_RUNTIME_DISPOSITION

CONTINUE_ALLOWED

Continuation is allowed only when all of the following are true:

- Strategy/PM intent is valid;
- current position and quantity authority are known;
- Pending identity is unambiguous;
- existing accepted side-effect reconciliation has already run;
- no matching accepted order exists for the item;
- canonical same-day execution authority is unavailable;
- no future or fallback price authority is used;
- no order, broker side effect, ledger order, fill, cash mutation, or position mutation occurred;
- explicit `NOT_EXECUTABLE` terminal evidence is persisted;
- all other items are either submitted/reconciled, item-scoped reviewed, or independently terminal.

This does not preserve HALT merely because current code currently reports `blocked` / `HALT` for the preflight failure. The design separates a known no-side-effect non-executable item from an unknown execution state.

## FAIL_CLOSED_HALTS_PRESERVED

YES

HALT or REVIEW_REQUIRED must remain for genuine unknown execution states, including:

- cannot determine whether an order was already submitted;
- duplicate side-effect ambiguity;
- Pending / Ledger contradiction;
- current position unknown;
- quantity authority unknown;
- conflicting execution price authorities;
- only future price authority available;
- malformed source artifact;
- execution side effect exists but identity cannot be reconciled;
- state mutation may have partially occurred;
- any missing evidence that prevents proving no order / no fill / no mutation.

Known non-executable is not the same as unknown execution state.

## BUY_APPLICABILITY

CONDITIONAL

The same terminal family should apply to BUY only when the same invariants hold:

- BUY intent is valid;
- quantity and capital authority are known;
- no adapter submit is called;
- no order or broker side effect exists;
- no ledger order exists;
- no cash reservation is consumed as a fake execution;
- no position is created;
- same-day retry is prevented;
- next day uses fresh PIT decision authority.

If BUY-side cash reservation, order state, or side-effect identity is ambiguous, fail-closed HALT / REVIEW_REQUIRED remains required.

## HISTORICAL_ONLY_STRATEGY_LOGIC_CREATED

NO

The semantic belongs at Submit / execution-feasibility boundary. Historical may encounter the concrete reason `canonical simulated execution price unavailable`; Production-common equivalent is `execution authority unavailable` or broker/execution quote authority unavailable. Strategy, PM, Candidate, Opportunity, BUY ranking, and SELL semantic decisions do not change.

## COMPOSITE_PENDING_PLAN_FINAL_STATE

REVIEW_REQUIRED_WITH_ITEM_SCOPED_TERMINALS

For the 2022-12-08 composite plan, the intended final item map is:

| Symbol | Side | Intended final item outcome |
| --- | --- | --- |
| 61440 | BUY | SUBMITTED / reconciled |
| 82560 | SELL | SUBMITTED / reconciled |
| 37790 | SELL | SUBMITTED / reconciled |
| 45910 | SELL | SUBMITTED / reconciled |
| 76920 | BUY | REVIEW_REQUIRED / NOT_SUBMITTED / `corporate_action_event_not_resolved` |
| 34940 | SELL | NOT_EXECUTABLE / NOT_SUBMITTED / `EXECUTION_AUTHORITY_UNAVAILABLE` |

The plan-level evidence should keep 76920 visible as reviewed. The plan may remain `REVIEW_REQUIRED` as a residual item-scoped review container while all executable and terminal items are no longer retryable.

## COMPOSITE_PENDING_RUNTIME_STATUS

PASS_WITH_ITEM_SCOPED_TERMINALS

Runtime continuation is allowed because:

- all accepted executable items are submitted or reconciled;
- 34940 is terminally known not executable and not submitted;
- 76920 remains a reviewed BUY and is not submitted;
- no unknown side effect remains.

## 76920_REVIEW_PRESERVED

YES

76920 remains:

- `REVIEW_REQUIRED`;
- `NOT_SUBMITTED`;
- reason `corporate_action_event_not_resolved`.

## CORPORATE_ACTION_SAFETY_CHANGED

NO

F1Z1 does not weaken corporate-action quarantine and does not mark reviewed / unknown BUY items as safe.

## OBSERVABILITY_CONTRACT

Minimum evidence fields for each `NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE` item:

- `pending_item_id`
- `symbol`
- `side`
- `planned_quantity`
- `strategy_runtime_planning_intent`
- `source_decision_type`
- `execution_feasibility_status`
- `terminal_reason`
- `execution_authority_source`
- `authority_resolution_status`
- `order_created`
- `adapter_submit_called`
- `broker_side_effect_created`
- `ledger_order_created`
- `position_mutated`
- `cash_mutated`
- `realized_pnl_mutated`
- `retry_eligible_same_day`
- `next_day_re_evaluation_required`
- `future_information_used`

For 34940, expected values include:

```text
execution_feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE
terminal_reason = EXECUTION_AUTHORITY_UNAVAILABLE
execution_authority_source = canonical run-scoped normalized J-Quants OHLCV
authority_resolution_status = UNAVAILABLE
order_created = false
adapter_submit_called = false
broker_side_effect_created = false
ledger_order_created = false
position_mutated = false
cash_mutated = false
realized_pnl_mutated = false
retry_eligible_same_day = false
next_day_re_evaluation_required = true
future_information_used = false
```

## TERMINAL_OUTCOME_OWNER

Submit / execution-feasibility boundary

Not owners:

- Strategy
- PM SELL semantics
- Candidate
- Opportunity
- BUY ranking
- Portfolio Construction
- Position Sizing, except for the existing quantity non-executable family

## RECOVERY_PATH_RECOMMENDATION

NORMAL_RESUME_AFTER_IMPLEMENTATION

After F1Z2 implements this Submit-boundary terminalization and operator acceptance passes, the existing halted 2022-12-08 run can be handled by the formal `resume` path because the run is halted at submit and the required behavior is idempotent Submit reconciliation plus item-scoped terminalization:

- preserve existing accepted 61440, 82560, 37790, and 45910 orders;
- reconcile them before any submit attempt;
- terminalize 34940 as `NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE` without fake order;
- preserve 76920 as item-scoped `REVIEW_REQUIRED`;
- continue only if no side-effect ambiguity remains.

Do not use `recover-stale-pending`, because target-date ledger rows exist. Do not use `recover-failed-execution`, because this is a Submit-boundary terminalization case, not an execution-job failed-fill recovery.

## FUTURE_INFORMATION_USED

NO

## IMPLEMENTATION_CHANGED

NO

## FRESH_RUN_EXECUTED

NO

## RESUME_EXECUTED

NO

## REPLAY_EXECUTED

NO

## LONG_HISTORICAL_EXECUTED

NO

## GIT_DIFF_CHECK

PASS

## NEXT_TASK_RECOMMENDATION

Phase31-F1Z2 focused Production-common implementation at the Submit / execution-feasibility boundary.

F1Z2 should add focused regression coverage for the 2022-12-08 composite shape:

- four existing accepted side effects reconcile;
- 34940 becomes `NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE`;
- adapter submit is not called for 34940;
- no duplicate order is created;
- 76920 remains reviewed / not submitted;
- Runtime result is continuation PASS when no blocked/unknown side-effect state remains.

## FINAL_QUESTIONS

1. SELL判断とExecution feasibilityを明確に分離できるか？

YES. SELL_EXIT is preserved; execution authority unavailable is an execution-feasibility terminal.

2. price authorityなしを「既知の実行不能」としてterminalizeできるか？

YES, when no side effect exists and authority unavailability is proven.

3. その1銘柄だけ注文せずRuntimeを継続できるか？

YES, conditionally on all other items being submitted/reconciled/reviewed/terminal and no unknown side effect remaining.

4. Position/Cash/PnLを一切捏造しないか？

YES. No fake order, fill, position mutation, cash mutation, or realized PnL is allowed.

5. 翌日は新しいPIT判断から再評価できるか？

YES. Same-day terminalization does not carry forward the stale SELL order.

6. UNKNOWN execution stateは引き続きHALTできるか？

YES. Unknown side effects, conflicting authorities, malformed artifacts, and mutation ambiguity remain fail-closed.

7. BUYにも同じterminal familyを安全に適用できるか？

CONDITIONAL. It applies only when no cash consumption, no position creation, and no side-effect ambiguity are proven.

8. Historical専用Strategy logicになっていないか？

YES. No Historical-only Strategy logic is introduced; owner is Submit / execution feasibility.

9. 2022-12-08 composite Pendingを正しく表現できるか？

YES. Four items submitted/reconciled, 34940 not executable/not submitted, and 76920 reviewed/not submitted.

10. 実装後、既存HALT runをどう安全に回復するか？

Use normal resume after F1Z2 implementation acceptance, because the halted submit job can reconcile existing side effects and terminalize 34940 idempotently without scoped recovery commands.
