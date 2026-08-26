# Phase31-F1J — F1I Production Acceptance / Clean Fresh-Run Readiness

## PRIMARY_JUDGMENT

CLEAN_FRESH_RUN_READY

F1I is accepted for Production readiness. The F1F + F1I path is structurally connected before PM escalation, preserves PM-only EXIT authority, does not create fake execution events, and passes focused regression.

## Required Output

F1I_SCOPE_CONFORMANCE = PASS

PRIOR_REDUCE_HISTORY_CANONICAL_OWNER = `positions/position_campaigns.json` pre-action lifecycle via `pm_decision_evidence_events`

PRIOR_HISTORY_AVAILABLE_BEFORE_PM_ESCALATION = YES

SAME_DAY_SELF_COUNT_PROTECTED = YES

CAMPAIGN_HISTORY_ISOLATION = PASS

RECOVERY_RESET_HISTORY_CONTRACT = PASS

83060_END_TO_END_ACCEPTANCE = PASS

54010_RECOVERY_END_TO_END_ACCEPTANCE = PASS

61750_END_TO_END_ACCEPTANCE = PASS

MINIMUM_NOTIONAL_ISOLATION = PASS

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO

REDUCE_COUNT_ONLY_EXIT = NO

EXISTING_PM_SELL_CONTRACT_ACCEPTANCE = PASS

EXIT_ESCALATION_MUTATION_POINT = PM

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

DUPLICATE_PRODUCTION_SELL_AUTHORITY_COUNT = 0

FAKE_EXECUTION_EVENT_CREATED = NO

FUTURE_INFORMATION_USED = NO

OUTCOME_USED_FOR_PARAMETER_SELECTION = NO

BROKEN_RUN_ID = runtime-test-historical-extended-smoke-20260821T002814288741Z

BROKEN_RUN_CLASSIFICATION = PRE_F1I_BROKEN_HISTORY_BRIDGE

BROKEN_RUN_REUSE_ALLOWED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 142 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

CLEAN_FRESH_RUN_READINESS = READY

VALIDATION_WINDOW_SELECTION_BASIS = STRUCTURAL_ACTIVATION_COVERAGE_NOT_PERFORMANCE

USER_OPERATED_FRESH_RUN_COMMAND =

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 40 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

NEXT_TASK_RECOMMENDATION = User-operated clean fresh-run. Then immediately audit actual fresh-run activation structurally before judging profitability: 83060, 54010, 61750, escalation reason occurrences, PM EXIT -> Runtime SELL_EXIT, and recovery protection.

## Authority Read

Read:

- `docs/phase_reports/phase31_f1h_fresh_historical_pm_sell_escalation_runtime_activation_audit.md`
- `docs/phase_reports/phase31_f1i_prior_unrepresentable_reduce_campaign_evidence_bridge_production_repair.md`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`
- `docs/phase_reports/phase31_f1e_pm_canonical_sell_semantic_integration_alternative_g_mutation_design.md`

Authority:

- F1E = SELL mutation design
- F1F = PM SELL implementation
- F1H = fresh-run integration defect evidence
- F1I = evidence bridge repair

## F1J-1 Scope Acceptance

F1I_SCOPE_CONFORMANCE = PASS

F1I changes are limited to:

- strict-prior PM decision evidence extraction from prior `strategy/position_management.json`
- campaign-scoped pre-action evidence bridge in `positions/position_campaigns.json`
- Strategy Intelligence `prior_unrepresentable_reduce_summary`
- PM attachment/consumption of the new summary
- existing F1F semantic support
- focused evidence lineage/tests

No SELL threshold, REDUCE-count tuning, canonical state expansion, BUY/Candidate/B10/ADD, Market Context, or minimum-notional policy change was found.

## F1J-2 Canonical History Authority

PRIOR_REDUCE_HISTORY_CANONICAL_OWNER = `positions/position_campaigns.json` pre-action lifecycle via `pm_decision_evidence_events`

This is:

- PIT
- run-scoped
- campaign-scoped
- decision evidence
- not economic execution history

`pm_decision_evidence_events` are not appended to the campaign economic `events` list.

FAKE_EXECUTION_EVENT_CREATED = NO

## F1J-3 Temporal Ordering Acceptance

Static common path:

```text
strict-prior previous PM evidence
-> pre-action position_campaigns
-> Strategy Intelligence
-> Position Management
-> canonical SELL semantic
-> Position Sizing
-> Runtime Planning
```

`shadow_runtime._materialize_pre_action_position_campaigns` attaches strict-prior PM decision evidence before Strategy Intelligence is produced; Strategy Intelligence then passes `prior_unrepresentable_reduce_summary` to PM evidence before `_apply_canonical_sell_semantics`.

PRIOR_HISTORY_AVAILABLE_BEFORE_PM_ESCALATION = YES

Only prior PM artifacts with `business_date < current_business_date` are scanned.

SAME_DAY_SELF_COUNT_PROTECTED = YES

Future evidence is not consumed.

## F1J-4 Campaign Isolation Acceptance

CAMPAIGN_HISTORY_ISOLATION = PASS

F1I tests verify that an old campaign id for the same symbol does not attach to a new campaign. Full EXIT / campaign close / re-entry therefore creates a fresh history boundary.

## F1J-5 Recovery Reset Acceptance

RECOVERY_RESET_HISTORY_CONTRACT = PASS

F1I records recovery boundary evidence separately and resets active prior unrepresentable REDUCE pressure. Old REDUCE history does not survive as hidden deterioration debt after RESET/DECAY.

## F1J-6 83060 End-to-End Acceptance

83060_END_TO_END_ACCEPTANCE = PASS

Focused PIT regression confirms:

- 2022-08-16 first unrepresentable REDUCE gives prior = 0, `WEAKENING_BUT_INTACT`, PM REDUCE / no EXIT.
- 2022-08-17 strict-prior same-campaign unrepresentable REDUCE evidence is available.
- Current REDUCE is discrete-lot zero, recovery absent, PIT proof complete.
- Existing F1F gate maps to `PERSISTENT_DETERIORATION` and PM EXIT.

Runtime SELL_EXIT is accepted structurally because Runtime Planning maps PM EXIT to SELL_EXIT and does not invent EXIT.

## F1J-7 54010 Recovery Acceptance

54010_RECOVERY_END_TO_END_ACCEPTANCE = PASS

Focused PIT regression confirms:

- REDUCE sequence can accumulate prior evidence.
- HOLD recovery boundary resets prior pressure.
- Later REDUCE sequence starts fresh.
- Old REDUCE history does not create immediate stale EXIT after recovery.

## F1J-8 61750 End-to-End Acceptance

61750_END_TO_END_ACCEPTANCE = PASS

Focused PIT regression confirms:

- 2022-09-13 prior = 0, `WEAKENING_BUT_INTACT`, no EXIT.
- 2022-09-14 prior = 1, current discrete-lot zero REDUCE, recovery absent, PIT proof complete.
- Existing F1F PM-owned gate escalates to PM EXIT.

No later delisting, later price, later PnL, MFE/MAE, or campaign outcome was used.

## F1J-9 Minimum-Notional Isolation

MINIMUM_NOTIONAL_ISOLATION = PASS

Minimum-notional evidence is excluded from the discrete-lot persistence summary and cannot enter the F1F escalation path.

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO

## F1J-10 Count-Only Protection

REDUCE_COUNT_ONLY_EXIT = NO

Focused tests verify that prior unrepresentable REDUCE history does not create EXIT without the current full F1F gate. A representable current REDUCE remains REDUCE / `WEAKENING_BUT_INTACT`.

## F1J-11 Existing PM Behavior Regression

EXISTING_PM_SELL_CONTRACT_ACCEPTANCE = PASS

Accepted unchanged:

- HOLD
- ADD
- representable REDUCE
- first one-lot WEAKENING REDUCE
- direct EXIT_GRADE
- existing PM EXIT
- fail-closed UNRESOLVED

## F1J-12 PS / Runtime Authority

EXIT_ESCALATION_MUTATION_POINT = PM

PS remains quantity / representability authority only.

Runtime remains a faithful PM action mapper only.

No PS-created EXIT or Runtime-created EXIT is accepted.

## F1J-13 Shadow / Legacy Dependency

Production consumer search for:

- `canonical_sell_semantic_shadow`
- `unrepresentable_reduce_exit_shadow`
- `diagnostic_shadow`

in the Production path found no consumers.

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

DUPLICATE_PRODUCTION_SELL_AUTHORITY_COUNT = 0

No legacy fallback EXIT authority is used.

## F1J-14 Focused Regression

Commands:

```bash
python3 -m pytest tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py -q
python3 -m pytest tests/strategy/test_phase22_d_position_management.py -q
python3 -m pytest tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py -q
python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q -k "reduce or minimum_notional"
python3 -m pytest tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py -q
```

Results:

- F1I bridge tests: 7 passed
- F1F canonical SELL tests: 7 passed
- PM tests: 22 passed
- Strategy Intelligence campaign/history tests: 9 passed
- Runtime Planning SELL + SELL quantity/materialization tests: 70 passed
- PS REDUCE/minimum-notional tests: 8 passed, 94 deselected
- F1D/C0D diagnostic shadow tests: 19 passed

FOCUSED_TEST_RESULTS = PASS; 142 passed

## F1J-15 Compile / Diff

PY_COMPILE = PASS

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py
```

GIT_DIFF_CHECK = PASS

Command:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py docs/phase_reports/phase31_f1i_prior_unrepresentable_reduce_campaign_evidence_bridge_production_repair.md
```

## F1J-16 Broken Run Quarantine

BROKEN_RUN_ID = runtime-test-historical-extended-smoke-20260821T002814288741Z

BROKEN_RUN_CLASSIFICATION = PRE_F1I_BROKEN_HISTORY_BRIDGE

BROKEN_RUN_REUSE_ALLOWED = NO

This run must not be used as F1I validation, F1I performance baseline, or acceptance evidence for repaired behavior. It was generated before the F1I bridge repair and is quarantined.

Codex did not mutate or reinterpret this run.

## F1J-17 Clean Fresh-Run Readiness

CLEAN_FRESH_RUN_READINESS = READY

All readiness gates are PASS:

- F1I scope
- history authority
- temporal ordering
- campaign isolation
- recovery reset
- 83060
- 54010
- 61750
- minimum-notional isolation
- count-only protection
- existing PM contract
- PM-only EXIT authority
- shadow consumer count 0
- focused regression

## F1J-18 User Validation Command

VALIDATION_WINDOW_SELECTION_BASIS = STRUCTURAL_ACTIVATION_COVERAGE_NOT_PERFORMANCE

Rationale:

- 2022-08-10 is the established structural window start for the early SELL family.
- 40BD is sufficient to cover early 83060/54010 activation and 61750 2022-09-13/2022-09-14 behavior.
- The window is not selected from profitability, return, PnL, later price, MFE/MAE, or outcome.

User-operated command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 40 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Codex did not execute this command.

## Final Questions

1. F1IはF1H root causeだけを修理しているか？ YES.
2. prior REDUCE evidenceはPM判断前に届くか？ YES.
3. fake SELL/FILLを作っていないか？ YES, no fake execution event is created.
4. same-day/future evidenceを数えていないか？ YES, protected.
5. recoveryで古いpressureを解除できるか？ YES.
6. campaignを跨いで履歴が漏れないか？ YES.
7. 83060/54010/61750がend-to-endで期待どおりか？ YES, focused PIT regression PASS.
8. countだけでEXITしないか？ YES, count-only EXIT is blocked.
9. minimum-notionalはscope外か？ YES.
10. 新しいclean fresh-runを開始してよいか？ YES.
