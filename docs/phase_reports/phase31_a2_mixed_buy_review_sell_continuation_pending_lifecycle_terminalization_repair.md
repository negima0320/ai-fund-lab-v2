# Phase31-A2 - Mixed BUY_ITEM_SCOPED_REVIEW / SELL Continuation Pending Lifecycle Terminalization Repair

## PRIMARY_JUDGMENT

`PHASE31_A2_MIXED_BUY_REVIEW_SELL_CONTINUATION_PENDING_TERMINALIZATION_REPAIRED`

Phase31-A1 confirmed a focused Pending lifecycle consumer gap where a valid
mixed `BUY_ITEM_SCOPED_REVIEW` + executable SELL continuation Pending survived
SELL execution and blocked the next session at pre-Data-Readiness lifecycle.

Phase31-A2 repairs that lifecycle path with a Production-common terminalization
authority for the narrow case where canonical Pending Review Scope Authority
allows SELL continuation, reviewed BUY remains unsubmitted/unfilled, executable
SELL reached terminal/reconciled execution, and no post-send or execution
ambiguity remains.

## ROOT_CAUSE

Reproduced by focused tests: YES.

The reproduced shape is:

```text
target session = T
next session = T+1
pending state = REVIEW_REQUIRED
review_scope = BUY_ITEM_SCOPED_REVIEW
reviewed BUY items present
reviewed SELL items absent
approved/executable SELL item present
SELL submitted and filled on T
Pending still non-terminal before T+1 Data Readiness
```

Before repair, this shape could fall into
`buy_item_scoped_review_pending_shape_invalid` because the no-submission
terminalization path required all items to be BUY and approved item ids to be
empty. Those predicates are not valid for SELL-continuation mixed Pending.

## IMPLEMENTED_SEMANTICS

Added a focused lifecycle authority in:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
```

New authority:

```text
mixed_buy_review_sell_continuation_terminalization_authority
contract_version = phase31_a2_v1
```

It applies only when:

- Pending Review Scope Authority is structurally valid;
- `review_scope = BUY_ITEM_SCOPED_REVIEW`;
- target session has elapsed;
- reviewed BUY items exist;
- reviewed SELL items are absent;
- executable SELL items exist;
- executable BUY items are absent for this focused path;
- sell continuation is allowed by canonical authority;
- reviewed BUY items remain `REVIEW_REQUIRED`, unapproved, unsubmitted, and unfilled;
- Submit evidence for the target session exists and is not `POST_SEND_UNKNOWN`;
- Submit submitted enough SELL items;
- Execution evidence for the target session exists;
- Execution reached `CURRENT_STATE_LOADED`;
- execution stage, reconciliation, ledger/current apply, or transaction evidence is terminal/pass;
- fill count is sufficient for the executable SELL item count;
- no broker-write uncertainty is present.

When all checks pass:

```text
new pending state = EXPIRED
pending slot = EMPTY
transition_reason = MIXED_BUY_REVIEW_SELL_CONTINUATION_RESIDUAL_BUY_REVIEW_EXPIRED
```

Reviewed BUY residuals expire as stale reviewed BUY authority. They are not
submitted, filled, auto-approved, or carried as new-day BUY authority.

When checks do not pass, lifecycle remains fail-closed as `REVIEW_REQUIRED`.

## CANONICAL_AUTHORITY_USED

YES.

The repair consumes:

```text
build_pending_review_scope_authority(...)
```

from:

```text
src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py
```

It does not reconstruct review scope from diagnostic reason strings.

## REVIEWED_BUY_AUTO_APPROVED

NO.

The new authority explicitly records:

```text
reviewed_buy_auto_approved = false
reviewed_buy_submitted = false
reviewed_buy_filled = false
new_day_buy_requires_fresh_authority = true
```

## VALID_SELL_CONTINUATION_PRESERVED

YES.

The repair is specifically for the case where canonical Pending Review Scope
Authority already allowed executable SELL continuation while BUY items remained
item-scoped review. It does not block SELL because BUY is reviewed.

## FAIL_CLOSED_PRESERVED

YES.

Missing execution evidence, `POST_SEND_UNKNOWN`, reviewed SELL presence,
reviewed BUY submit/fill evidence, or unresolved execution ambiguity all remain
`REVIEW_REQUIRED`.

## TYPED_GUARD_NORMALIZATION

Implemented.

Pending lifecycle `REVIEW_REQUIRED` transitions now materialize AK9R29-style
typed guard fields in the lifecycle manifest/history:

```text
review_guard_results
review_guard_summary
review_guard_classes
review_guard_codes
```

For unresolved lifecycle/authority handoff cases, the guard class normalizes to:

```text
INTERNAL_SYSTEM_CONSISTENCY
```

Fail-closed behavior was not weakened to avoid review.

## PRODUCTION_COMMON

YES.

The lifecycle authority is implemented in common Runtime/Pending lifecycle
code. It is not Historical-only.

## HISTORICAL_ONLY_LOGIC_ADDED

NO.

## PHASE30_ARCHITECTURE_CONTRACT_PRESERVED

YES.

Preserved contracts:

- canonical Pending Review Scope Authority;
- BUY / SELL independence;
- reviewed BUY fail-closed;
- reviewed SELL fail-closed;
- no auto-approval of reviewed BUY;
- no duplicate quantity authority;
- no cash semantic collapse;
- no Strategy, Candidate, PM, PC, PS, threshold, exposure, ADD, SELL timing, or Re-entry change;
- typed Runtime guard taxonomy;
- real pre-Data-Readiness lifecycle ordering.

## TEST_RESULTS

Focused A2 lifecycle tests:

```text
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'phase31_a2' -q
4 passed, 37 deselected
```

Focused A2 real CLI ordering test:

```text
python3 -m pytest tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -k 'phase31_a2' -q
1 passed, 2 deselected
```

Pending lifecycle regression:

```text
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
41 passed
```

Real pre-Data-Readiness orchestration regression:

```text
python3 -m pytest tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py -q
3 passed
```

Pending Review Scope Authority and Runtime Guard Taxonomy regression:

```text
python3 -m pytest tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r29_runtime_guard_taxonomy.py -q
19 passed
```

Historical Safety Temporal Authority regression:

```text
python3 -m pytest tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py -q
12 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=.pytest_cache/pycache python3 -m compileall -q \
  src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py \
  tests/runtime_v2/test_phase30_ak9r12_pre_data_readiness_pending_lifecycle_orchestration.py
PASS
```

Initial compile without `PYTHONPYCACHEPREFIX` failed because Python attempted to
write pyc files under `/Users/negishi/Library/Caches/...`, which is outside the
sandbox. Re-running with workspace-local pycache passed.

## LONG_HISTORICAL_RUN_EXECUTED

NO.

No fresh-run, replay, resume, 25BD, 100BD, 500BD, or long Historical run was
executed by Codex.

## USER_RUN_READINESS

YES.

The user may start a fresh long Historical validation after this repair. The
recommended validation owner remains the user. Codex did not execute the long
run.
