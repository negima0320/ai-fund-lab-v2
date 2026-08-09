# Phase28-D58: Production-Common BUY_ADD Campaign Identity Baseline Supply Repair

## Primary Judgment

```text
PHASE28_D58_PRODUCTION_COMMON_ADD_CAMPAIGN_BASELINE_SUPPLY_REPAIRED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

D58 accepted the D57 root cause and implemented the minimal Production-common repair in Strategy Runtime campaign identity propagation. No fresh run, resume, long historical run, runtime mutation, config change, threshold change, broker semantic change, SELL semantic change, Submit Guard change, D55-A semantic change, D55-B lot-feasibility semantic change, D55-C orchestration order change, or D55-D zero-weight reason semantic change was executed.

## Implemented Repair

Changed files:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
```

D55-C baseline supplier now consumes Strategy Position Management current-position lifecycle/reference authority after PM artifact generation. It still prefers any canonical campaign id present in current summary, but when current summary lacks it, it can align with the same PM current-position authority that D55-A already recognizes.

```text
D55-C campaign authority after repair:
strategy_position_management_current_position_lifecycle_reference

D55-A campaign authority:
current_position_campaign_id / pm_position_campaign_id / position_campaign_id
plus opportunity_position_campaign_id for opportunity side

Authority alignment status:
PASS
```

This does not create a symbol-only fallback. It consumes existing PM current-position authority and still requires prior same-campaign Strategy PC evidence.

## Representative Evidence

Read-only target-run reproduction against `runtime-test-historical-smoke-20260808T232727106824Z`:

```text
Before D58:
supplied_count total = 0
missing_count total = 0

After D58 representative 2023-05-02:
current_campaign_count = 3
supplied_count = 2
missing_count = 1

After D58 representative 2023-05-08:
current_campaign_count = 3
supplied_count = 3
missing_count = 0
```

First ADD behavior remains fail-closed when no prior same-campaign current-position baseline exists:

```text
76010 / 2023-05-02
classification = FIRST_ADD_BOOTSTRAP_FAIL_CLOSED_WHEN_NO_PRIOR_CURRENT_POSITION_BASELINE
```

Subsequent ADD baseline supply is repaired:

```text
76470 / 2023-05-08
baseline_business_date = 2023-05-02
baseline_campaign_id = runtime-current-76470
baseline_score = 0.16913658
current campaign id = runtime-current-76470
future_evidence_used = false
symbol_only_fallback_used = false
```

D55-A representative result:

```text
symbol = 76470
business_date = 2023-05-08
campaign_continuation = PASS
expected_edge = PASS
expected_edge_state = IMPROVING
incremental_value = PASS
final_add_eligibility = PASS
```

## Contract Preservation

```text
PM ADD remains intent-only.
Portfolio Construction remains target-weight authority.
Position Sizing remains quantity authority.
Runtime Planning remains final Position Sizing consumer.
D55-C two-pass order is unchanged.
Missing baseline remains UNKNOWN_FAIL_CLOSED.
Future evidence used = NO.
Symbol-only fallback used = NO.
Training leakage = NONE.
```

## Validation

```text
py_compile = PASS
D55-A / D55-B / D55-C / D58 core regression = 132 passed
PM / Runtime Planning / SELL / broker representative regression = 88 passed
Candidate / Buy Quality representative regression = 20 passed
JSON validation = PASS
git diff --check = PASS
```

## Fresh Gate

```text
Fresh 100BD Entry = READY
Recommended Next Phase = Phase28-D59 Fresh 100BD Runtime Conformance Run
```

User-run command when ready:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2023-04-03 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Codex did not execute this command.

## Execution Flags

```text
Implementation changed = YES
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime Authority violation = NO
Fresh run executed = NO
Resume executed = NO
Long Historical executed = NO
Runtime mutated = NO
```

## Deliverables

```text
docs/phase_reports/phase28_d58_production_common_add_campaign_baseline_supply_repair.md
reports/phase_reports/phase28_d58_production_common_add_campaign_baseline_supply_repair.json
reports/phase28_d58_production_common_add_campaign_baseline_supply_repair/
```
