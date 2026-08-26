# Phase31-F1I — Prior Unrepresentable REDUCE Campaign Evidence Bridge Production Repair

## PRIMARY_JUDGMENT

PHASE31_F1I_PRIOR_UNREPRESENTABLE_REDUCE_EVIDENCE_BRIDGE_IMPLEMENTED_REGRESSION_PASS

## Required Output

ROOT_CAUSE = PM_MISSING_CAMPAIGN_HISTORY

PRIOR_REDUCE_HISTORY_CANONICAL_OWNER = `positions/position_campaigns.json` pre-action lifecycle, extended with strict-prior `strategy.position_management` decision evidence as `pm_decision_evidence_events`

IMPLEMENTATION_STATUS = IMPLEMENTED

PRIOR_HISTORY_AVAILABLE_BEFORE_PM_ESCALATION = YES

COMMON_RUNTIME_HISTORY_BRIDGE_CONNECTED = YES

SAME_DAY_SELF_COUNT_PROTECTED = YES

CAMPAIGN_HISTORY_ISOLATION = PASS

RECOVERY_RESET_HISTORY_CONTRACT = PASS

83060_HISTORY_BRIDGE_REGRESSION = PASS

54010_RECOVERY_HISTORY_RESET_REGRESSION = PASS

61750_HISTORY_BRIDGE_REGRESSION = PASS

MINIMUM_NOTIONAL_HISTORY_ESCALATION_EXCLUDED = YES

REDUCE_COUNT_ONLY_EXIT = NO

EXISTING_F1F_ESCALATION_SEMANTICS_CHANGED = NO

FAKE_EXECUTION_EVENT_CREATED = NO

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

FUTURE_INFORMATION_USED = NO

OUTCOME_USED_FOR_PARAMETER_SELECTION = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 142 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

CLEAN_REVALIDATION_REQUIRED = YES

NEXT_TASK_RECOMMENDATION = Phase31-F1J Production acceptance / new clean fresh-run readiness. Do not reuse `runtime-test-historical-extended-smoke-20260821T002814288741Z` for F1I validation.

## Root Cause Authority

Read:

- `docs/phase_reports/phase31_f1h_fresh_historical_pm_sell_escalation_runtime_activation_audit.md`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`
- `docs/phase_reports/phase31_f1e_pm_canonical_sell_semantic_integration_alternative_g_mutation_design.md`

F1H confirmed that F1F production code was connected and materialized, but prior same-campaign unrepresentable REDUCE history was missing from PM evidence. Repeated one-lot REDUCE rows therefore remained `WEAKENING_BUT_INTACT` instead of reaching `PERSISTENT_DETERIORATION`.

## Implementation

Changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py`

Architecture:

```text
strict-prior strategy/position_management.json
-> positions/position_campaigns.json pm_decision_evidence_events
-> strategy_intelligence.lifecycle_context.prior_unrepresentable_reduce_summary
-> PM attached Strategy Intelligence evidence
-> sell_semantic_state._prior_reduce_count
-> existing F1F PM-owned gate
```

This preserves F1F escalation semantics. The repair only supplies missing PIT persistence evidence.

## Canonical Owner

The canonical owner is:

`positions/position_campaigns.json`

Reason:

- It is already materialized before Strategy Intelligence and PM.
- It is the current pre-action campaign lifecycle authority.
- It is PIT-scoped and run-scoped.
- It can carry campaign-isolated prior decision evidence without pretending the decision was an execution.

The added field is:

`pm_decision_evidence_events`

These events are decision / intent / representability evidence only. They are not appended to the economic `events` list.

## Evidence Model

For strict-prior unrepresentable REDUCE decisions, F1I records:

- business_date
- symbol
- campaign_id
- event_kind = `UNREPRESENTABLE_REDUCE_DECISION`
- PM action / final PM action
- PM reason codes
- canonical SELL state
- representability family
- current quantity
- trading unit
- raw / rounded / final REDUCE quantity
- minimum-notional flag
- recovery state
- PIT proof
- source artifact path / hash
- source contract version
- `decision_evidence_not_execution = true`
- `fake_execution_event_created = false`
- `future_information_used = false`

Recovery boundaries are recorded as `RECOVERY_BOUNDARY` decision evidence so old pressure can be reset without fake fills.

## Temporal Contract

Only PM artifacts with `business_date < current business_date` are scanned.

SAME_DAY_SELF_COUNT_PROTECTED = YES

No same-day current REDUCE can count as its own prior evidence.

No future-date evidence is read.

## Recovery / Campaign Boundary

Recovery reset / decay events clear the active prior unrepresentable REDUCE sequence for escalation evidence.

Campaign id is the join boundary. Strict-prior PM decision evidence with a different campaign id is not attached to the current campaign.

CAMPAIGN_HISTORY_ISOLATION = PASS

RECOVERY_RESET_HISTORY_CONTRACT = PASS

## Minimum-Notional Isolation

Minimum-notional REDUCE decisions are excluded from `prior_unrepresentable_reduce_summary`.

MINIMUM_NOTIONAL_HISTORY_ESCALATION_EXCLUDED = YES

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED remains NO.

## Count-Only Protection

Prior count does not create EXIT by itself.

Test coverage verifies that when the current REDUCE is representable, prior unrepresentable REDUCE history alone leaves PM at REDUCE / `WEAKENING_BUT_INTACT`.

REDUCE_COUNT_ONLY_EXIT = NO

## Static Fresh-Run Path Revalidation

Common path ordering remains:

```text
pre-action position_campaigns
-> strategy_intelligence
-> position_management
-> _apply_canonical_sell_semantics
-> position_sizing
-> runtime_planning
```

The bridge is connected before PM escalation because `shadow_runtime._materialize_pre_action_position_campaigns` now attaches strict-prior PM decision evidence before Strategy Intelligence is produced.

COMMON_RUNTIME_HISTORY_BRIDGE_CONNECTED = YES

PRIOR_HISTORY_AVAILABLE_BEFORE_PM_ESCALATION = YES

Read-only probe against the broken active run showed the new helper can detect 2022-08-16 83060 / 54010 unrepresentable REDUCE decision evidence for the 2022-08-17 decision date. The active run itself was not mutated and does not validate F1I.

## Regression Results

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
- Existing PM tests: 22 passed
- Strategy Intelligence focused tests: 9 passed
- Runtime Planning / SELL quantity materialization: 70 passed
- PS reduce / minimum-notional focused: 8 passed, 94 deselected
- F1D / C0D diagnostic shadow tests: 19 passed

Total focused tests = 142 passed

PY_COMPILE = PASS

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py
```

GIT_DIFF_CHECK = PASS

Command:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/shadow_runtime.py src/ai_fund_lab_v2/strategy/strategy_intelligence.py src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py
```

## Existing Active Run

The current active/broken-history run:

`runtime-test-historical-extended-smoke-20260821T002814288741Z`

was not patched, reinterpreted, resumed, replayed, or used as F1I validation.

After F1I acceptance, a new fresh-run is required.

## Safety

- No broker state mutated.
- No position quantity mutated.
- No cash altered.
- No fills created.
- No realized/unrealized PnL altered.
- No fake campaign execution events created.
- No training / learning data path added.
- No performance outcome used.
- No threshold or REDUCE-count tuning.
- No BUY / B10 / ADD behavior changed.
- No diagnostic shadow artifact consumed in Production.

## Final Questions

1. unrepresentable REDUCE decision historyをどのcanonical authorityで保持するのが正しいか？ `positions/position_campaigns.json` pre-action lifecycle, with separate strict-prior PM decision evidence.
2. 実売買eventを偽造せず履歴化できたか？ YES.
3. PM semantic evaluation前にprior historyが届くか？ YES.
4. same-day current REDUCEをpriorとして数えていないか？ YES, protected.
5. recovery RESETで古いpersistent pressureが消えるか？ YES.
6. campaign跨ぎで履歴が漏れないか？ YES.
7. 83060/54010/61750 controlは期待どおりになるか？ YES in focused PIT regression.
8. minimum-notionalはscope外のままか？ YES.
9. F1FのPM-owned EXIT semantics自体は変更していないか？ YES, unchanged.
10. 修正後に新fresh-runへ進める状態か？ YES, after F1J acceptance/readiness.
