# Phase32-H - KI-001 Prior EXIT / REENTRY Context Preservation Repair

Repair type: narrow correctness repair.  
Target evidence run: `runtime-test-historical-extended-smoke-20260829T205402869666Z`  
Known issue: `P31-KI-001 Prior EXIT semantic information loss`.

## Scope Controls

Phase32-H did not change Re-entry thresholds, cooldown, recovery conditions, MA thresholds, momentum thresholds, Strategy parameters, weights, ranks, Cash policy, Risk Pacing, G129 BUY_ADD semantics, or PM decision semantics.

Codex did not run fresh-run, resume, replay, or long Historical. No future price, future return, future regime, future MFE/MAE, later SELL outcome, campaign final outcome, Historical PnL, or hindsight winner/loser classification was used.

## Root Cause

Detailed PM EXIT semantics existed at decision time, but the prior-exit materialization path used by later REENTRY evaluation reconstructed prior exit context from persistent ledger executions alone.

For the confirmed `83060` case:

- `2022-10-04 position_management/pm_decisions.json`
  - `decision_type=EXIT`
  - `decision_reason=trend_and_opportunity_broken`
  - `reason_codes=["trend_and_opportunity_broken"]`
  - `position_campaign_id=pc-f0fa7678e714f74f-83060-0001`
- `2022-10-04 execution/fills.json`
  - sell exit fill retained runtime-level SELL identity, but not the detailed PM reason in the prior-exit fields consumed by Strategy shadow.
- `2022-10-05 portfolio_construction.json`
  - `semantic_buy_type=REENTRY`
  - `prior_exit_business_date=2022-10-04`
  - `prior_exit_reason=SELL_EXIT`
  - `prior_exit_reason_codes=[]`
  - `prior_exit_reason_class=GENERIC`
  - `prior_exit_context_status=REVIEW_REQUIRED`
  - `recovery_reason=insufficient_prior_exit_context`

The direct cause was:

```text
strict-prior PM EXIT decision detail
  existed in daily position_management/pm_decisions.json
  but was not joined into _supply_prior_exit_state()
  before Portfolio Construction REENTRY recovery consumed prior_exit_reason.
```

## First Semantic-Loss Boundary

First semantic-loss boundary:

```text
persistent ledger / execution-derived prior exit state
  -> Strategy shadow _supply_prior_exit_state()
```

The ledger-derived path preserved strict-prior exit date and flat-symbol identity, but it fell back to `source_decision_type` / `SELL_EXIT` / `EXIT` when PM decision reason was absent from the execution row. Portfolio Construction then correctly classified that generic reason as insufficient prior-exit context.

## Canonical Prior-Exit Authority

The canonical prior-exit authority after Phase32-H is a strict-prior join of:

- persistent ledger execution history for proof that a prior campaign fully closed before the REENTRY decision date;
- strict-prior PM EXIT decision evidence for the semantic reason/context of that closure;
- campaign identity from the prior execution/campaign chain, preserved by Phase32-C provenance/campaign repair.

The repair does not infer EXIT reason from symbol text, later campaign outcome, later prices, or REENTRY result. If PM EXIT detail is genuinely unavailable, the path remains `REVIEW_REQUIRED` and fails safe.

## Strict-Prior PIT Contract

For REENTRY decision date `D`, Phase32-H reads only:

```text
business_date < D
```

for both ledger executions and PM EXIT decision artifacts.

Same-day exits, later exits, same-day future stages, later price movement, later SELL result, and future campaign outcome remain prohibited. Focused tests verify same-day/future exits are not consumed.

## Repair Design

Implemented changes:

1. `shadow_runtime._supply_prior_exit_state(...)`
   - now accepts `run_dir`;
   - reads strict-prior PM EXIT decision artifacts from `daily/<date>/position_management/pm_decisions.json` and `daily/<date>/strategy/position_management.json`;
   - joins PM EXIT context by `position_campaign_id`, not by symbol-only reconstruction;
   - emits canonical `prior_exit_context` fields when a ledger-proven prior campaign closes.
2. `shadow_runtime._resolve_prior_closed_campaigns_from_executions(...)`
   - preserves explicit campaign identity from BUY executions when present;
   - merges matching PM EXIT context into the closed campaign prior-exit state;
   - falls back to `REVIEW_REQUIRED` when no PM detail exists.
3. `portfolio_construction._semantic_reentry_evidence(...)`
   - carries `prior_campaign_id`, `prior_exit_decision_type`, `prior_exit_reason`, `prior_exit_reason_codes`, `source_pm_decision_id`, `source_decision_id`, and `prior_exit_context`.
4. `portfolio_construction._reentry_semantic_result(...)`
   - preserves the same prior-exit context in the final REENTRY semantic eligibility artifact.

No downstream stage re-guesses EXIT reason.

## Files Changed

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- `docs/phase_reports/phase32_h_ki001_prior_exit_reentry_context_preservation_repair.md`

## Phase32-C Provenance / Campaign Integration

Phase32-H uses the campaign identity continuity repaired in Phase32-C:

- prior EXIT context joins by `position_campaign_id` / `campaign_id`;
- REENTRY receives `prior_campaign_id`;
- current REENTRY still starts a new campaign when accepted later;
- the prior closed campaign is not treated as a current holding;
- symbol-only reason reconstruction is not used.

The focused Phase32-C provenance/campaign tests still pass.

## Multiple-Campaign Handling

For multiple same-symbol campaigns, the resolver keeps an execution-ordered per-symbol campaign state and selects the latest ledger-proven closed campaign strictly before the REENTRY date. PM EXIT context is joined only when the PM decision campaign ID matches that closed campaign.

Focused test coverage verifies that an older same-symbol campaign reason, such as `hard_stop_current_return`, is not mixed into the latest prior campaign when the latest campaign's EXIT reason is `trend_and_opportunity_broken`.

## Missing-Context Handling

When detailed PM EXIT context does not exist, Phase32-H does not fabricate acceptance:

- `prior_exit_provenance_status=REVIEW_REQUIRED`
- `prior_exit_context.authority=PIT_LEDGER_EXECUTION_HISTORY_WITHOUT_PM_EXIT_DETAIL`
- prior reason can remain `SELL_EXIT` / `EXIT`
- Portfolio Construction continues to classify it as `GENERIC`
- REENTRY recovery remains `REVIEW_REQUIRED` with `insufficient_prior_exit_context`

This preserves the Phase30-Z fail-safe rule that generic EXIT is not sufficient genuine recovery evidence.

## Re-entry Policy Check

Re-entry policy change: `NO`.

The current source does not impose a permanent ban merely because a symbol had a prior EXIT. It requires:

- prior campaign identity and EXIT cause;
- cooldown satisfaction;
- current recovery evidence;
- current candidate eligibility;
- safety/corporate-action/capacity evidence.

After Phase32-H, actual prior EXIT semantics can reach those existing gates. The gates themselves are unchanged.

`SEPARATE_REENTRY_POLICY_DEFECT_FOUND = NO`

## KI-004 Observations

KI-004 is not repaired in Phase32-H.

Observation: when prior EXIT context is generic/missing, REENTRY can still surface broad `REVIEW_REQUIRED` / fail-closed states. Phase32-H makes the prior-exit context dimension more explicit, which should make future KI-004 safety-classification review cleaner. No new concrete broker/corporate-action misclassification was repaired here.

## PM Re-Acceptance Status

`PM_REACCEPTANCE_REQUIRED = NO`

Phase32-H did not change `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` or accepted-current-path PM source. It changes Strategy shadow prior-exit materialization and PC REENTRY context propagation only.

## Focused Validation

Targeted prior EXIT / REENTRY materialization:

```text
python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py
```

Result: `18 passed`.

REENTRY focused Portfolio Construction regression:

```text
python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_first_time_buy_new_has_non_reentry_semantic_contract \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase31_g26_reentry_rejection_is_symbol_local_and_next_competitor_survives \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_canonical_add_is_not_reentry_and_remains_positive_when_low_price_capped
```

Result: `6 passed`.

Phase32-C and G129 focused regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
```

Result: `5 passed`.

Additional nearby regression:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result: `34 passed`.

Campaign/provenance nearby regression:

```text
python3 -m pytest \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py \
  tests/strategy/test_phase31_g110_actual_path_campaign_activation.py \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py
```

Result: `20 passed, 1 skipped`.

Read-only target example re-resolution:

```text
2022-10-05 83060
prior_exit_business_date=2022-10-04
prior_campaign_id=pc-f0fa7678e714f74f-83060-0001
prior_exit_decision_type=EXIT
prior_exit_reason=trend_and_opportunity_broken
prior_exit_reason_codes=["trend_and_opportunity_broken"]
source_pm_decision_id=pm-2022-10-04-83060-exit
prior_exit_provenance_status=PASS
previous_exit_reason_class=TREND_MOMENTUM
reentry_recovery_reason != insufficient_prior_exit_context
future_or_same_day_exit_used=False
post_hoc_pnl_input_used=False
```

## Regression Judgments

- Phase32-C regression: `NO`
- G129 regression: `NO`
- Re-entry policy change: `NO`
- Strategy semantic change: `NO`
- PM semantic change: `NO`
- Parameter/threshold/weight change: `NO`

## Retest Required

Retest required: `YES`.

Reason: Phase32-H changes Strategy shadow / Portfolio Construction REENTRY evidence production. A user-operated Historical fresh-run is needed to confirm real run artifacts no longer degrade prior EXIT context across the full lifecycle.

Exact user command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 300 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Codex did not run this command.

## Final Judgment

`PHASE32_H_KI001_PRIOR_EXIT_REENTRY_CONTEXT_PRESERVATION_REPAIRED`
