# Phase31-F1G — PM SELL Escalation Production Acceptance / Clean Validation Readiness

## PRIMARY_JUDGMENT

PHASE31_F1G_PM_SELL_ESCALATION_PRODUCTION_ACCEPTED_CLEAN_VALIDATION_READY

## Required Output

F1F_SCOPE_CONFORMANCE = PASS

EXIT_ESCALATION_MUTATION_POINT = PM

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

DUPLICATE_PRODUCTION_SELL_AUTHORITY_COUNT = 0

PM_ACTION_CONTRACT_ACCEPTANCE = PASS

61750_END_TO_END_STRUCTURAL_ACCEPTANCE = PASS

RECOVERY_PROTECTION_ACCEPTANCE = PASS

MINIMUM_NOTIONAL_ISOLATION = PASS

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO

EXISTING_EXIT_AUTHORITY_ACCEPTANCE = PASS

FAIL_CLOSED_ACCEPTANCE = PASS

PIT_CONTRACT_ACCEPTANCE = PASS

MARKET_CONTEXT_LOGIC_CHANGED = NO

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO

OUTCOME_USED_FOR_PARAMETER_SELECTION = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 126 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

CLEAN_VALIDATION_READINESS = READY

VALIDATION_WINDOW_SELECTION_BASIS = STRUCTURAL_COVERAGE_NOT_PERFORMANCE

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

NEXT_TASK_RECOMMENDATION = User-operated clean validation. After validation, audit SELL behavior structurally before judging profitability.

## Documents Read

- `docs/phase_reports/phase31_f1e_pm_canonical_sell_semantic_integration_alternative_g_mutation_design.md`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`

F1E is treated as the design authority. F1F is treated as the implemented contract.

## F1G-1 Diff Scope Audit

F1F implementation scope conforms to F1E.

F1F touched:

- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`

Conformance:

- BUY変更なし
- Candidate変更なし
- B10変更なし
- ADD変更なし
- Safety cap変更なし
- Market Context変更なし
- minimum-notional policy変更なし
- Runtime execution semantic変更なし
- Pending/Submit変更なし

Existing unrelated dirty working-tree files from prior phases were not reverted and are not treated as F1F scope.

## F1G-2 Production Authority Trace

| Layer | Producer | Consumer | Authority | Mutation Point |
|---|---|---|---|---|
| PIT Strategy Intelligence evidence | `strategy_intelligence` | PM / `sell_semantic_state` | PIT evidence only, not action authority | none |
| Canonical SELL semantic | `strategy.sell_semantic_state` | PM only | canonical SELL state and escalation evidence | none by itself |
| PM baseline action | `position_management` | PM canonical gate / PS / Runtime Planning | HOLD / ADD / REDUCE / EXIT action authority | baseline PM action |
| PM discrete-control gate | `position_management._apply_canonical_sell_semantics` | PM output | PM-owned REDUCE -> EXIT escalation | PM |
| Final PM action | `position_management` | PS / Runtime Planning | final PM action authority | PM |
| PS | `position_sizing` | Runtime Planning / SELL planning | quantity, lot representation, minimum-notional semantics | quantity only |
| Runtime Planning | `runtime_planning` | SELL planning | maps PM action faithfully | none |
| SELL Planning | `runtime_v2.planning.sell_pipeline` | Pending / execution path | sell order planning from PM/Runtime intent | no EXIT invention |
| Pending / execution | Runtime v2 Pending / Submit | broker path | carries accepted SELL plan | no SELL authority creation |

EXIT_ESCALATION_MUTATION_POINT = PM

## F1G-3 No Shadow Production Dependency

Repository search terms:

- `canonical_sell_semantic_shadow`
- `unrepresentable_reduce_exit_shadow`
- `diagnostic_shadow`

Findings:

- Production PM consumes `strategy.sell_semantic_state`, not `canonical_sell_semantic_shadow`.
- F1D/C0D shadow modules remain diagnostic materializers.
- Tests and reports reference shadow artifacts.
- Production PM / PC / PS / Runtime / Pending / Submit / Execution do not consume SELL shadow artifacts.

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

## F1G-4 No Legacy/Fallback Authority

| Component | Classification | Reason |
|---|---|---|
| `strategy.sell_semantic_state` | KEEP | canonical production SELL semantic evidence producer |
| PM `_apply_canonical_sell_semantics` | KEEP | only production REDUCE -> EXIT mutation point |
| `canonical_sell_semantic_shadow.py` | KEEP_DIAGNOSTIC | F1D diagnostic evidence only |
| `unrepresentable_reduce_exit_shadow.py` | KEEP_DIAGNOSTIC | C0D/F1A diagnostic evidence only |
| Runtime Planning PM action mapping | KEEP | faithful PM action consumer |
| SELL Pipeline REDUCE quantity contract | KEEP | quantity/no-order authority, no EXIT fallback |
| Old Alternative G shadow-as-authority | DEPRECATE_AS_PRODUCTION | not used in production |
| Runtime-side fallback EXIT | REMOVE_AS_AUTHORITY | not present |
| PS-side fallback EXIT | REMOVE_AS_AUTHORITY | not present |

DUPLICATE_PRODUCTION_SELL_AUTHORITY_COUNT = 0

## F1G-5 PM Action Contract Acceptance

PM_ACTION_CONTRACT_ACCEPTANCE = PASS

Accepted cases:

- HOLD unchanged.
- ADD unchanged.
- Representable REDUCE unchanged.
- First one-lot WEAKENING remains REDUCE; no EXIT.
- Persistent discrete-lot deterioration with full gate passes becomes PM EXIT.
- EXIT_GRADE / direct PM EXIT remains unchanged.
- UNRESOLVED fail-closed preserve/review; no silent EXIT.

## F1G-6 61750 Structural Acceptance

61750_END_TO_END_STRUCTURAL_ACCEPTANCE = PASS

PIT structural evidence from existing F1D artifacts:

- 2022-09-13 = PM REDUCE / WEAKENING_BUT_INTACT / discrete-lot zero / no EXIT.
- 2022-09-14 = PM REDUCE / PERSISTENT_DETERIORATION / discrete-lot unrepresentable / recovery absent / PIT proof complete / Alternative G candidate.

F1F production mapping:

- 2022-09-13 remains PM REDUCE.
- 2022-09-14 satisfies the F1E/F1F gate and PM materializes final EXIT.
- Runtime Planning maps PM EXIT to SELL_EXIT.
- SELL Pipeline receives SELL_EXIT as action input; it does not invent the EXIT.

No later delisting, later return, later MFE/MAE, later price, or final campaign outcome was used.

## F1G-7 Recovery Protection Acceptance

RECOVERY_PROTECTION_ACCEPTANCE = PASS

Evidence:

- RESET fixture: HOLD + recovery reasons maps to HEALTHY_OR_RECOVERING / RESET / final PM HOLD.
- DECAY fixture: HOLD + PASS recovery evidence without explicit reset reason maps to HEALTHY_OR_RECOVERING / DECAY / final PM HOLD.
- Prior REDUCE history alone does not create hidden EXIT debt.

## F1G-8 Minimum-Notional Isolation

MINIMUM_NOTIONAL_ISOLATION = PASS

`REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL` maps to `UNRESOLVED` / `MINIMUM_NOTIONAL_POLICY_UNRESOLVED` and preserves baseline REDUCE. It cannot enter the F1F discrete-control EXIT mutation path because the gate requires `representability_family == DISCRETE_LOT` and `minimum_notional_flag == false`.

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO

## F1G-9 Existing EXIT Regression

EXISTING_EXIT_AUTHORITY_ACCEPTANCE = PASS

Direct PM EXIT maps to EXIT_GRADE and remains final PM EXIT. Runtime Planning maps PM EXIT to SELL_EXIT without requiring Alternative G history.

## F1G-10 Fail-Closed Acceptance

FAIL_CLOSED_ACCEPTANCE = PASS

Verified fail-closed / preserve conditions:

- Missing PIT proof / future-dated evidence -> no EXIT.
- Ambiguous campaign identity -> no EXIT.
- Minimum-notional -> no EXIT.
- Unknown representability -> no EXIT.
- UNRESOLVED state -> no silent EXIT.
- Conflicting recovery/deterioration is explicitly classified as UNRESOLVED by the canonical state contract.

## F1G-11 PIT / Temporal Audit

PIT_CONTRACT_ACCEPTANCE = PASS

Implementation inspection:

- `sell_semantic_state` uses current PM row, attached SI evidence, current action, current representability, campaign identity, and same-day adapter source dates.
- PIT proof only compares evidence dates to the current business date and fails closed on future dates.
- No next-day lookup, later price lookup, final campaign outcome, Historical performance dependency, or parameter tuning path is present.
- `future_information_used = False` and `outcome_used_for_parameter_selection = False` are emitted in semantic evidence.

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO

OUTCOME_USED_FOR_PARAMETER_SELECTION = NO

## F1G-12 Focused Regression

Focused tests executed:

```bash
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py -q
python3 -m pytest tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py -q
python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py -q
python3 -m pytest tests/strategy/test_phase22_d_position_management.py -q
python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py -q
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py -q -k "reduce or minimum_notional"
```

Results:

- F1F PM canonical SELL semantic integration: 7 passed
- F1D canonical SELL semantic shadow: 10 passed
- C0D representability shadow: 9 passed
- Existing PM tests: 22 passed
- Existing Runtime Planning SELL tests: 48 passed
- SELL pipeline quantity/materialization tests: 22 passed
- PS reduce/minimum-notional focused tests: 8 passed, 94 deselected

Total focused tests = 126 passed

No fresh-run, resume, replay, or long Historical was executed.

## F1G-13 Compile / Diff

PY_COMPILE = PASS

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/sell_semantic_state.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/runtime_planning.py src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py
```

GIT_DIFF_CHECK = PASS

Command:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/sell_semantic_state.py src/ai_fund_lab_v2/strategy/position_management.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md
```

## F1G-14 Validation Readiness

CLEAN_VALIDATION_READINESS = READY

All readiness gates passed:

- F1F_SCOPE_CONFORMANCE = PASS
- PM_ACTION_CONTRACT_ACCEPTANCE = PASS
- 61750_END_TO_END_STRUCTURAL_ACCEPTANCE = PASS
- RECOVERY_PROTECTION_ACCEPTANCE = PASS
- MINIMUM_NOTIONAL_ISOLATION = PASS
- EXISTING_EXIT_AUTHORITY_ACCEPTANCE = PASS
- FAIL_CLOSED_ACCEPTANCE = PASS
- PIT_CONTRACT_ACCEPTANCE = PASS
- PRODUCTION_SHADOW_CONSUMER_COUNT = 0
- focused regression = PASS

## F1G-15 Validation Plan

VALIDATION_WINDOW_SELECTION_BASIS = STRUCTURAL_COVERAGE_NOT_PERFORMANCE

Window rationale:

- Existing Phase31/F1D structural evidence uses the 2022-08-10 regime window.
- 61750 first weakening appears on 2022-09-13, the 24th business date in the inspected run.
- 61750 first persistent deterioration eligibility appears on 2022-09-14, the 25th business date.
- A 40BD window is consistent with existing validation minimum-window conventions and gives several post-escalation business days to inspect SELL_EXIT propagation.
- The window is not selected from later PnL, return, delisting, MFE/MAE, or profitability outcome.

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

1. F1FはF1Eで承認したscopeだけを実装しているか？ YES.
2. EXIT escalation authorityはPMだけか？ YES.
3. shadow/legacy fallbackにProduction依存していないか？ YES.
4. 61750型one-lot persistent deteriorationはend-to-endでSELL_EXITへ進めるか？ YES, structurally via PM EXIT -> Runtime SELL_EXIT.
5. recovery Winnerを守れるか？ YES.
6. minimum-notionalは完全にscope外か？ YES.
7. existing EXITを壊していないか？ YES.
8. fail-closed/PIT contractは維持されているか？ YES.
9. clean fresh validationを安全に開始できるか？ YES.
10. 実行すべきコマンドは何か？ The single command in F1G-15.
