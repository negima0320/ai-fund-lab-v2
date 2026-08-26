# Phase31-G27 - ADD Capital Competition Integration

## Primary Judgment

PRIMARY_JUDGMENT = PHASE31_G27_ADD_CAPITAL_COMPETITION_INTEGRATION_IMPLEMENTED_ACCEPTED

G27 connected PM ADD intent into the Portfolio Construction capital competition framework as a canonical ADD competitor. Existing `add_investment_evidence.py` remains the source for Incremental Investment Value and Opportunity Cost semantics; G27 did not create a duplicate ADD alpha/value authority.

## Current ADD Pipeline Inventory

| Step | Producer | Artifact / field | Consumer | Authority | Current status | Drop reason | Migration required |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PM ADD intent | Position Management | `pm_action=ADD`, PM reason codes | Portfolio Construction | POSITION_MANAGEMENT | CONNECTED | none | KEEP |
| Existing position identity | Current portfolio + PM merge | `current_position`, `current_weight`, `current_quantity` | PC ADD bridge / Sizing | PC consumes current state | CONNECTED | missing current weight fail-closed | KEEP |
| ADD value semantics | `add_investment_evidence.py` | `incremental_value`, `opportunity_cost`, campaign/no-loss checks | PC ADD bridge and G27 competitor | PORTFOLIO_CONSTRUCTION consumer of canonical evidence | CONNECTED | fail-closed if incomplete | KEEP |
| PC ADD target increment | PC ADD bridge | `requested_incremental_weight`, `accepted_incremental_weight`, `post_add_target_weight` | lot-aware PC, Sizing | PORTFOLIO_CONSTRUCTION | CONNECTED | ADD loses if value/eligibility fails | MIGRATE |
| PC capital competition | PC G24/G27 | `capital_competition.competitors[].canonical_add_competitor` | reports / downstream evidence | PORTFOLIO_CONSTRUCTION | IMPLEMENTED | n/a | MIGRATE COMPLETE |
| Lot/residual feasibility | Position Sizing preflight evidence consumed by PC | `canonical_sizing_evidence`, lot resolution | PC final reallocation | POSITION_SIZING owns quantity evidence; PC owns competition | CONNECTED | reconsiderable/terminal constraints explicit | KEEP |
| Discrete ADD quantity delta | Position Sizing | BUY_ADD quantity delta fields | Runtime Planning | POSITION_SIZING | CONNECTED | zero delta remains explicit | KEEP |
| Runtime BUY_ADD | Runtime Planning | existing BUY_ADD path | Submit | RUNTIME_PLANNING | REUSED | none | NO CHANGE |
| Submit / Execution | Submit / Execution | existing order path | Broker/ledger | SUBMIT / EXECUTION | REUSED | none | NO CHANGE |

CURRENT_ADD_PIPELINE_INVENTORY_COMPLETE = YES

## Existing Value Semantics

EXISTING_INCREMENTAL_INVESTMENT_VALUE_FOUND = YES

EXISTING_OPPORTUNITY_COST_FOUND = YES

Existing canonical implementation:

- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py`
- consumed by `portfolio_construction._resolve_canonical_add_allocation_bridge`
- reused by G27 `canonical_add_competitor`

DUPLICATE_ADD_VALUE_AUTHORITY_CREATED = 0

## Implementation Summary

G27 added canonical ADD competitor evidence to PC capital competition:

- `canonical_add_competitor.schema_version = portfolio_construction.add_capital_competitor.v1`
- `source_pm_intent.owner = POSITION_MANAGEMENT`
- `owner = PORTFOLIO_CONSTRUCTION`
- `constraint_evidence.position_sizing_quantity_owner = POSITION_SIZING`
- `pc_calculates_authoritative_quantity = False`
- PIT-only value evidence and explicit zero future/outcome counters

ADD capital competition now distinguishes:

- `ADD_SELECTED`
- `ADD_LOST_TO_NEW_BUY`
- `ADD_LOST_TO_CASH`
- `ADD_STRATEGY_CAP_BOUND`
- `ADD_SAFETY_CAP_BOUND`
- `ADD_LOT_INFEASIBLE`
- `ADD_NO_POSITIVE_DELTA`
- `ADD_INSUFFICIENT_EVIDENCE`

The lot-aware PC allocation loop now rejects ADD competitors before allocation when canonical ADD eligibility fails, so PM ADD intent no longer implies execution.

## Legacy ADD Migration Matrix

| Legacy path | Disposition |
| --- | --- |
| PM ADD intent | KEEP |
| PC ADD bridge target increment | KEEP as target-weight bridge |
| Existing `add_investment_evidence` incremental value | KEEP |
| Existing opportunity-cost resolver | KEEP |
| Legacy implicit ADD selected by positive request alone | MIGRATE |
| Lot-aware ADD feasibility | KEEP |
| Runtime BUY_ADD order path | KEEP |
| Parallel ADD competition logic | REMOVE / not introduced |

ADD_LEGACY_MIGRATION_MATRIX_COMPLETE = YES

PERMANENT_ADD_LEGACY_FALLBACK_COUNT = 0

## Authority Audit

PM_ADD_INTENT_OWNER = POSITION_MANAGEMENT

ADD_CAPITAL_COMPETITION_OWNER = PORTFOLIO_CONSTRUCTION

ADD_DISCRETE_QUANTITY_OWNER = POSITION_SIZING

SAFETY_HARD_BOUNDARY_OWNER = SAFETY

SUBMIT_OWNER = SUBMIT

EXECUTION_OWNER = EXECUTION

DUPLICATE_AUTHORITY_COUNT = 0

## Acceptance Results

CANONICAL_ADD_COMPETITOR_IMPLEMENTED = YES

ADD_ELIGIBILITY_CONTRACT = PASS

ADD_BYPASSES_CURRENT_EVIDENCE = NO

ADD_INCREMENTAL_VALUE_PIT_ONLY = YES

HISTORICAL_OUTCOME_USED_FOR_ADD_VALUE = NO

ADD_OPPORTUNITY_COST_CONTRACT = PASS

ADD_AUTOMATIC_PRIORITY = NO

PM_ADD_INTENT_IMPLIES_EXECUTION = NO

ADD_CAN_WIN_CAPITAL_COMPETITION = YES

ADD_AUTOMATIC_REJECTION = NO

PC_COMPETES_NEW_BUY_ADD_CASH = YES

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_ADD_QUANTITY_AUTHORITY_CREATED = NO

ADD_SIZING_FAILURE_REENTERS_PC_COMPETITION = YES

RAW_ZERO_ADD_QUANTITY_REINTERPRETATION = NO

ADD_STRATEGY_SAFETY_CAP_SEPARATION = PASS

ADD_BYPASSES_SAFETY = NO

CASH_CAN_BEAT_ADD = YES

FORCED_CAPITAL_DEPLOYMENT = NO

REENTRY_BEHAVIOR_CHANGED = NO

ADD_REENTRY_AUTHORITY_COUPLED = NO

RISK_PACING_AUTHORITATIVE_IN_G27 = NO

RISK_PACING_BEHAVIORAL_EFFECT_COUNT = 0

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

SUBMIT_LOGIC_CHANGED = NO

EXECUTION_LOGIC_CHANGED = NO

ADD_ORDER_TYPE_REUSED = YES

ADD_REASON_CODE_CONTRACT = PASS

G27_PRODUCTION_BEHAVIOR_CHANGE_CLASS = LIMITED_ADD_DECISION_CHANGE

Decision categories changed:

- ADD with failed incremental value / opportunity evidence is no longer allowed to win lot-aware capital allocation solely from positive PM intent/request.
- Canonical ADD competitor records now explicitly classify selected, lost-to-new-buy, lost-to-cash, cap-bound, safety-bound, lot-infeasible, and no-positive-delta outcomes.

No profitability or later outcome evidence was used.

## Test Results

G27_FOCUSED_TESTS = PASS

ADD_REGRESSION = PASS

PC_REGRESSION = PASS

SIZING_REGRESSION = PASS

PM_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

ADD_FUNNEL_CONNECTIVITY = PASS

Focused tests added/covered:

- PM ADD intent reaches PC competitor set.
- Valid ADD can win against weaker NEW_BUY.
- Stronger NEW_BUY can beat ADD.
- Cash can beat weak ADD and weak NEW_BUY.
- Strategy cap, Safety cap, lot infeasible, and no positive delta are explicit.
- Position Sizing remains quantity owner.
- Existing BUY_ADD sizing/runtime boundary remains unchanged.

Commands:

- `python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py` = PASS, 119 passed
- `python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py` = PASS, 403 passed
- `env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py` = PASS
- `git diff --check` = PASS

## Required Summary Output

PRIMARY_JUDGMENT = PHASE31_G27_ADD_CAPITAL_COMPETITION_INTEGRATION_IMPLEMENTED_ACCEPTED

CURRENT_ADD_PIPELINE_INVENTORY_COMPLETE = YES

EXISTING_INCREMENTAL_INVESTMENT_VALUE_FOUND = YES

EXISTING_OPPORTUNITY_COST_FOUND = YES

DUPLICATE_ADD_VALUE_AUTHORITY_CREATED = 0

PM_ADD_INTENT_OWNER = POSITION_MANAGEMENT

ADD_CAPITAL_COMPETITION_OWNER = PORTFOLIO_CONSTRUCTION

ADD_DISCRETE_QUANTITY_OWNER = POSITION_SIZING

CANONICAL_ADD_COMPETITOR_IMPLEMENTED = YES

ADD_ELIGIBILITY_CONTRACT = PASS

ADD_INCREMENTAL_VALUE_PIT_ONLY = YES

HISTORICAL_OUTCOME_USED_FOR_ADD_VALUE = NO

ADD_OPPORTUNITY_COST_CONTRACT = PASS

ADD_AUTOMATIC_PRIORITY = NO

PM_ADD_INTENT_IMPLIES_EXECUTION = NO

ADD_CAN_WIN_CAPITAL_COMPETITION = YES

ADD_AUTOMATIC_REJECTION = NO

PC_COMPETES_NEW_BUY_ADD_CASH = YES

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_ADD_QUANTITY_AUTHORITY_CREATED = NO

ADD_SIZING_FAILURE_REENTERS_PC_COMPETITION = YES

RAW_ZERO_ADD_QUANTITY_REINTERPRETATION = NO

ADD_STRATEGY_SAFETY_CAP_SEPARATION = PASS

ADD_BYPASSES_SAFETY = NO

CASH_CAN_BEAT_ADD = YES

FORCED_CAPITAL_DEPLOYMENT = NO

REENTRY_BEHAVIOR_CHANGED = NO

ADD_REENTRY_AUTHORITY_COUPLED = NO

RISK_PACING_AUTHORITATIVE_IN_G27 = NO

RISK_PACING_BEHAVIORAL_EFFECT_COUNT = 0

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

SUBMIT_LOGIC_CHANGED = NO

EXECUTION_LOGIC_CHANGED = NO

ADD_ORDER_TYPE_REUSED = YES

ADD_LEGACY_MIGRATION_MATRIX_COMPLETE = YES

PERMANENT_ADD_LEGACY_FALLBACK_COUNT = 0

ADD_REASON_CODE_CONTRACT = PASS

G27_PRODUCTION_BEHAVIOR_CHANGE_CLASS = LIMITED_ADD_DECISION_CHANGE

ADD_FUNNEL_CONNECTIVITY = PASS

G27_FOCUSED_TESTS = PASS

ADD_REGRESSION = PASS

PC_REGRESSION = PASS

SIZING_REGRESSION = PASS

PM_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

DUPLICATE_AUTHORITY_COUNT = 0

G27_DIFF_SCOPE = PASS

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

HISTORICAL_RERUN_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION = Proceed to G28 only after accepting the G27 ADD capital competitor contract and its limited ADD decision-change classification.
