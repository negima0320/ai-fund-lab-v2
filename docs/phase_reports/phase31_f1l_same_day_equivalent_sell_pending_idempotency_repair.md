# Phase31-F1L — Same-Day Equivalent SELL Pending Idempotency / Reconciliation Repair

## PRIMARY_JUDGMENT

PHASE31_F1L_SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY_REPAIRED_REGRESSION_PASS

The F1K root cause is repaired in the SELL Planning / Pending integration layer. A same-day, single-item, approved, full-position SELL_EXIT-equivalent pending plan is now accepted idempotently instead of being treated as an active pending conflict.

## Required Output

ROOT_CAUSE = PENDING_SELL_CONFLICT

IMPLEMENTATION_STATUS = IMPLEMENTED

EQUIVALENT_PENDING_CONTRACT = same-day active pending may be reused only when plan state is APPROVED, the plan date and target session match the current business date, it is unconsumed, contains exactly one approved SELL item and no BUY items, the item state is CREATED / READY / APPROVED, symbol matches a current open position, side is SELL, quantity equals current position quantity, and SELL action family resolves to EXIT.

SELL_ACTION_EQUIVALENCE_CONTRACT = generic SELL pending can be equivalent to SELL_EXIT only when lineage/intent evidence resolves to EXIT through `quantity_contract.source_decision`, `quantity_contract.planning_intent`, `quantity_contract.source_planning_id`, `source_decision_type`, `planning_authority_source`, `policy_source`, or pending item id, and quantity equals full current position quantity. SELL_REDUCE is not equivalent to SELL_EXIT when economic exposure differs.

EQUIVALENT_PENDING_RESULT = PASS / IDEMPOTENT_EXISTING_PENDING / REUSE_EXISTING_PENDING

GENUINE_CONFLICT_RESULT = REVIEW_REQUIRED / ORIGINAL_PENDING_PRESERVED

93600_EQUIVALENT_PENDING_REGRESSION = PASS

DUPLICATE_PENDING_CREATED = NO

ORIGINAL_PENDING_PRESERVED = YES

ACTIVE_PENDING_SAFETY_GUARD_WEAKENED = NO

F1F_ESCALATION_SEMANTICS_CHANGED = NO

F1I_HISTORY_BRIDGE_CHANGED = NO

CAMPAIGN_OBSERVABILITY_GAP = SEPARATE

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 82 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

RESUME_AFTER_REPAIR = CONDITIONAL

FRESH_RUN_REQUIRED_AFTER_REPAIR = CONDITIONAL

NEXT_TASK_RECOMMENDATION = Phase31-F1M acceptance + resume readiness

## Implementation

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`

No Strategy, PM SELL semantic, F1F canonical SELL state, F1I history bridge, threshold, BUY/B10/ADD, fixture, fresh-run, resume, replay, or long Historical change was made.

## Equivalent Pending Contract

F1L defines the safe idempotent branch only for this state:

- existing pending plan state = APPROVED
- existing pending plan_created_date = current business date
- existing pending target_session_date = current target session
- existing pending not consumed
- exactly one pending item
- exactly one approved SELL item
- no BUY items
- item state in CREATED, READY, APPROVED
- no partial-fill markers
- symbol matches a current position
- existing SELL quantity equals current position quantity
- SELL action family resolves to EXIT

For 93600:

- current holding = 100
- existing pending = SELL 93600 quantity 100
- planning authority source contains `sell_exit`
- source decision type = SELL_EXIT
- target session = 2022-09-07

This is equivalent to the already materialized SELL_EXIT 93600 quantity 100 state.

## Idempotent Result

When the contract passes, SELL Planning:

- returns PASS
- does not overwrite the pending file
- preserves the original pending plan id
- preserves the original pending item id
- does not create a duplicate pending item
- writes explicit evidence:
  - `pending_equivalence_status = EQUIVALENT`
  - `resolution_action = REUSE_EXISTING_PENDING`
  - `original_pending_preserved = true`
  - `duplicate_pending_created = false`
  - `future_information_used = false`

Evidence artifact:

- `.runtime/runtime_state/sell_pipeline/<date>/same_day_sell_pending_equivalence_evidence.json`

The stage result uses:

- `pending_composition_model = SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY`
- `pending_composition_status = PASS`

## Genuine Conflict Preservation

The active pending guard remains fail-closed for:

- different quantity
- multiple active SELL items
- stale prior-session pending
- BUY pending
- non-EXIT action family
- missing current position
- partial-fill markers
- unsupported pending state

The stale prior-session case now explicitly preserves original pending and returns REVIEW_REQUIRED instead of allowing no-signal empty pending overwrite.

## Action-Family Semantics

SELL_ACTION_EQUIVALENCE_CONTRACT:

`SELL` and `SELL_EXIT` may be equivalent only when available lineage/intent evidence resolves to EXIT and the sell quantity equals the full current position quantity.

`SELL_REDUCE` and `SELL_EXIT` are not equivalent when their economic exposure differs. A REDUCE quantity 50 against a current position 100 remains REVIEW_REQUIRED rather than being reused as a full EXIT.

## 93600 Regression

Test:

`test_phase31_f1l_93600_equivalent_same_day_sell_exit_pending_reused`

Scenario:

- current holding = 100
- existing pending item id = `strategy-c8537cd09201c855e2b4`
- symbol = 93600
- side = SELL
- quantity = 100
- item state = CREATED
- source decision type = SELL_EXIT
- planning authority source = `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`

Result:

- status = PASS
- original pending plan id preserved
- original pending item id preserved
- pending file content unchanged
- duplicate pending count = 0

93600_EQUIVALENT_PENDING_REGRESSION = PASS

## Campaign Observability

CAMPAIGN_OBSERVABILITY_GAP = SEPARATE

F1K identified a copied 2022-09-07 `position_campaigns.json` campaign-id discrepancy for 93600. It was not the HALT cause and is not needed for safe F1L equivalence detection. F1L does not repair or reinterpret that observability gap.

## Resume Safety

RESUME_AFTER_REPAIR = CONDITIONAL

The halted run's 2022-09-07 pending plan is structurally valid for the F1L repaired branch:

- same-day pending
- SELL 93600
- quantity 100
- active approved pending
- no corrupt fill/state evidence in F1K
- upstream 9/7 PM/PS/Runtime artifacts already showed full SELL_EXIT materialization

Resume is conditionally safe if the next task accepts the existing 2022-09-07 pending artifact as the canonical state to be interpreted by the repaired sell_planning logic. A clean fresh-run is still conditionally required if acceptance wants all copied run evidence regenerated from the repaired source state.

FRESH_RUN_REQUIRED_AFTER_REPAIR = CONDITIONAL

## Focused Regression

Commands run:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q
python3 -m pytest tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q
```

Results:

- F1L same-day SELL pending idempotency: 8 passed
- Existing SELL pending reconciliation: 10 passed
- Existing BUY/Pending composition safety: 28 passed
- SELL quantity/materialization: 22 passed
- F1F/F1I strategy regressions: 14 passed

FOCUSED_TEST_RESULTS = PASS; 82 passed

## Compile / Diff

PY_COMPILE = PASS

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py
```

GIT_DIFF_CHECK = PASS

Command:

```bash
git diff --check -- src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/composition.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py
```

## Final Questions

1. 93600の既存pendingは新SELL_EXIT要求と本当に同等か？ YES, same-day SELL quantity 100 equals current position quantity 100 and action family resolves to EXIT.
2. 同等pendingを安全にreuseできるか？ YES, under the strict F1L contract only.
3. duplicate pendingを作らないか？ YES, original pending file and item identity are preserved.
4. 本物のconflictは従来どおり止められるか？ YES, quantity mismatch, ambiguous items, stale session, and reduce/exposure mismatch regressions pass.
5. SELL_REDUCEとSELL_EXITを誤って同一視しないか？ YES, different economic exposure remains REVIEW_REQUIRED.
6. Pending safetyを弱めていないか？ NO, stale active pending is now more explicitly fail-closed.
7. F1F/F1IのSELL判断を一切変更せず直せるか？ YES.
8. 修理後、今回のHALT runをresumeできるか？ CONDITIONAL; likely safe for a focused repaired sell_planning interpretation, but F1M should accept resume readiness explicitly.
