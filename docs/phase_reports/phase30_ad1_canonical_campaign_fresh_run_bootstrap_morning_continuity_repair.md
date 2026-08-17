# Phase30-AD1 - Canonical Campaign Fresh-Run Bootstrap / Morning Continuity Repair

Task ID: `Phase30-AD1`

## Primary Judgment

```text
PHASE30_AD1_CANONICAL_CAMPAIGN_FRESH_RUN_BOOTSTRAP_REPAIRED
REPAIR_STATUS = REPAIRED
USER_OPERATED_FRESH_20BD_RERUN_READY
```

Phase30-AD1 repairs the Phase30-AD0 regression:

```text
PHASE30_AC_CANONICAL_CAMPAIGN_FIRST_DAY_BOOTSTRAP_GAP
```

The repair is Production-common and scoped only to canonical campaign bootstrap
and morning carry-forward. It does not restore legacy campaign fallback,
symbol-only fallback, HOLD/ADD legacy heuristics, Strategy tuning, threshold
changes, Entry Admission changes, REENTRY changes, SELL/REDUCE/EXIT redesign,
Safety changes, or Historical outcome fitting.

## Root Cause

Phase30-AC materialized the pre-action canonical campaign snapshot before first
fresh-run BUY fills, so the first day artifact could contain zero campaigns.
After BUY fills, Ledger, Current, and valuation were consistent, but no
canonical campaign state was available for the next morning's pre-action
Strategy Intelligence input.

Result:

```text
2022-08-10 BUY fills exist
-> Current positions exist
-> prior canonical campaign snapshot remains empty
-> 2022-08-12 pre-action held positions have missing campaign identity
-> PM / PC / PS REVIEW_REQUIRED
-> Runtime Planning unresolved
-> morning HALT
```

## Repair Status

```text
REPAIRED
```

The pre-action materializer now carries canonical campaign state from:

```text
latest prior positions/position_campaigns.json
+ strict-prior completed persistent_ledger/executions.jsonl
+ decision-time Current
-> positions/position_campaigns.json
```

For a decision-time Current position that is missing from the prior canonical
snapshot, a campaign is bootstrapped only when strict-prior Ledger executions
prove an open BUY campaign before the decision business date. If Ledger cannot
prove the campaign, the held position remains explicit missing campaign
authority and downstream consumers fail closed.

## Fresh BUY Bootstrap

Fresh `BUY_NEW` now creates one deterministic canonical campaign identity from
the first strict-prior BUY execution:

```text
BUY_NEW fill
-> persistent Ledger execution
-> deterministic position_campaign_id
-> canonical OPEN campaign in positions/position_campaigns.json
-> next morning Strategy Intelligence campaign identity COMPLETE
```

Focused regression covers multi-symbol first BUY bootstrap and verifies that
same-day future executions are not used.

## Next-Morning Continuity

The repaired pre-action artifact records:

- prior canonical campaign artifact path/hash
- strict-prior Ledger executions path/hash
- Current path/hash
- `bootstrap_open_campaign_count`
- `bootstrap_open_campaign_symbols`
- `missing_current_campaign_symbols`
- temporal safety flags

The next morning no longer depends on post-runtime EOD reconstruction to recover
first-day BUY campaign identity.

## Accounting / Current / Campaign Reconciliation

The repaired contract expects:

```text
Accounting positions = Current positions = canonical OPEN campaigns
```

for all Ledger-proven open positions. Missing canonical authority without
strict-prior Ledger proof remains fail-closed and is reported explicitly.

## Campaign Lifecycle

`BUY_NEW`:

Creates a new deterministic `position_campaign_id` when Ledger proves a new BUY
from zero prior quantity.

`ADD`:

Keeps the existing campaign open. Additional BUY executions while quantity is
already open increment ADD history; they do not create a duplicate campaign.

`REDUCE`:

Keeps the same campaign open and records REDUCE / SELL history.

`EXIT`:

Closes the same campaign when strict-prior SELL executions reduce quantity to
zero and Current no longer holds the position.

`REENTRY`:

After a ledger-proven full EXIT, a later BUY starts a new deterministic campaign
identity under the same canonical `positions/position_campaigns.json` owner.

## Idempotency

Re-running materialization over the same prior canonical artifact, Ledger
executions, and Current produces the same campaign identities. The repair does
not write Ledger records, cash records, orders, or execution records, and it
does not duplicate BUY events in the persistent Ledger.

## Legacy Retirement Integrity

```text
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
DUPLICATE_CAMPAIGN_AUTHORITY = NO
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

The canonical owner remains:

```text
positions/position_campaigns.json
```

No legacy fallback or second campaign authority was introduced.

## Production Integrity

```text
PHASE30_AC_HOLD_ADD_REPAIR_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_SEMANTICS_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
PHASE30_S_HANDOFF_PRESERVED = YES
```

The repair is limited to campaign identity materialization before Strategy
Intelligence. Entry Admission, Position Sizing handoff, one-lot admission,
REENTRY evidence, and PM/PC/PS authority boundaries are unchanged.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

The bootstrap source selection rule is strict-prior Ledger execution history
plus decision-time Current. Same-day future executions and same-day EOD campaign
reconstruction are explicitly rejected.

## Tests

Compile:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
```

Result:

```text
PASS
```

Focused regression:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py -k 'phase30_ad1 or phase30_ac_pre_action_campaign_materialization'
```

Result:

```text
4 passed, 17 deselected
```

Preservation regression:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m pytest -q tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py
```

Result:

```text
26 passed
20 passed
```

Legacy search:

```text
retired fallback / obsolete HOLD-ADD reference search = 0 matches
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

Codex did not run fresh 20BD, 100BD, long Historical, target-run resume, or
target-run replay.

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_20BD_RERUN_READY
```

## Recommended Next Task

```text
Phase30-AD2 - Fresh 20BD Post-AC Bootstrap Validation
```
