# Phase32-S — PC Evidence-Tiered ADD Acceleration Minimum Implementation

## Objective

Implement the Phase32-R design as a minimum production-path change:

- Portfolio Construction owns evidence-tiered ADD acceleration.
- Position Management remains directional ADD intent authority.
- Position Sizing remains discrete executable quantity authority.
- Runtime remains an exact consumer of PS-bound order increments.
- G129 BUY_ADD order-increment semantics remain unchanged.

No fresh-run, resume, replay, or long Historical validation was executed.

## Implementation Summary

Implemented a PC-owned ADD acceleration resolver in
`src/ai_fund_lab_v2/strategy/portfolio_construction.py`.

Canonical emitted fields:

- `add_acceleration_tier`
- `add_acceleration_status`
- `add_acceleration_reason_codes`
- `add_acceleration_authority`
- `add_acceleration_guardrails`
- `pre_acceleration_incremental_weight`
- `tier_bounded_incremental_weight`
- `post_acceleration_target_weight`

Canonical tiers:

- `NO_ACCELERATION`
- `NORMAL_ADD`
- `STRONG_ADD`
- `EXCEPTIONAL_ADD`

The resolver is called from the existing canonical ADD allocation bridge. It
preserves the existing normal ADD increment unless complete stronger evidence
authorizes a larger continuous PC target. Magnitude is derived from the existing
PC incremental unit and bounded by single-name cap, target gross exposure, and
available headroom. No fixed lot multiplier is introduced.

## Authority Contract

Authority boundaries:

- PM: ADD direction only.
- PC: ADD acceleration tier and continuous target-weight increment.
- PS: discrete executable quantity, including zero, one lot, or multiple lots.
- Runtime: exact PS-bound quantity consumer; no Runtime redecision.

The acceleration authority explicitly records:

- `owner=PORTFOLIO_CONSTRUCTION`
- `pm_add_intent_owner=POSITION_MANAGEMENT`
- `position_sizing_quantity_owner=POSITION_SIZING`
- `runtime_order_increment_owner=RUNTIME_CONSUMES_PS_BOUND_INCREMENT`
- `fixed_lot_multiplier_used=False`
- `runtime_quantity_redecision_allowed=False`
- `historical_profitability_used=False`
- `future_information_used=False`
- `parameter_selection_status=PARAMETER_SELECTION_DEFERRED`

## Evidence Bindings

Strong/exceptional acceleration requires all required current/PIT evidence to
pass:

- PM ADD
- campaign provenance / current-position authority
- expected edge improvement
- incremental investment value
- opportunity cost
- no-loss averaging
- Buy Quality eligibility
- cap/headroom
- Risk Pacing compatibility
- Safety
- broker eligibility
- corporate action
- liquidity

Missing, UNKNOWN, conflicting, blocked, or incompatible authority remains
fail-closed. CAUTIOUS / preserve-optionality Risk Pacing down-tiers acceleration
to normal ADD. Unknown Risk Pacing is fail-closed.

`BUY_WAIT` and explicit zero `quality_allocation_adjustment` keep incremental
ADD at zero. Reduced Buy Quality allocation can preserve normal ADD only and
cannot re-expand into strong/exceptional acceleration.

`src/ai_fund_lab_v2/strategy/add_investment_evidence.py` was tightened so an
explicit `incremental_investment_value_state=UNKNOWN` remains UNKNOWN /
FAIL_CLOSED instead of cascading into POSITIVE.

## Competition Preservation

NEW / ADD / Cash competition remains intact. Strong ADD can compete for capital,
but it does not automatically win. Existing Cash optionality behavior remains
observable under cautious Risk Pacing.

BUY_NEW and accepted REENTRY initial sizing are unchanged. REDUCE and EXIT are
unchanged.

## Architecture SoT Update

Updated `docs/02_architecture/strategy_intelligence_architecture_v1.md` with
section 37:

`Phase32-S PC-Owned Evidence-Tiered ADD Acceleration Contract`

This records the durable cross-phase authority boundary for ADD acceleration.

## Files Changed

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py`

## Focused Validation Results

PASS:

```text
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py
16 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews
2 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase26_h_adaptive_buy_quality.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_s_ps_consumes_pc_buy_quality_reason_code_without_rethresholding
25 passed
```

PASS:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py \
  -k "BUY_ADD or buy_add or add or REDUCE or EXIT or reduce or exit or zero"
58 passed, 115 deselected
```

PASS with one actual-runtime-root-dependent case excluded:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py \
  -k "not actual_strategy_entrypoint"
28 passed, 1 deselected
```

Observed unrelated validation caveat:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase29_l21k_prior_exit_materialization.py \
  tests/runtime_v2/test_phase32_c_provenance_campaign_identity.py
```

returned 1 failure in
`test_phase32_p_actual_strategy_entrypoint_materializes_rejected_reentry_prior_context`.
The failure is an actual-runtime-root evidence expectation mismatch:

- expected `prior_campaign_id=pc-878ea6968d1e7574-33700-0001`
- observed `prior_campaign_id=pc-43806796a45a1ad2-33700-0001`

This path reads existing `.runtime` and Phase32-O run evidence, and is not a
Phase32-S ADD acceleration code path. The source-contract provenance tests run
beside it passed.

## Regression Checks

- G129 BUY_ADD order-increment semantics: PASS.
- BUY_WAIT / explicit zero quality allocation: PASS.
- Reduced Buy Quality does not re-expand to strong acceleration: PASS.
- PS remains quantity authority and can materialize multiple lots from PC
  discrete authority: PASS.
- Runtime BUY_ADD consumes PS-bound order increment: PASS.
- REDUCE / EXIT focused runtime and sizing paths: PASS.
- Phase32-C provenance/campaign source-contract tests: PASS.

## Strategy Semantic Change

YES, intentionally and narrowly: user-approved performance initiative changes
only PC ADD capital magnitude when complete current evidence supports stronger
winner capitalization.

NO changes were made to:

- Candidate selection
- BUY_NEW initial sizing
- accepted REENTRY initial sizing
- PM action mapping
- BUY / SELL / ADD thresholds
- weights or ranking rules
- Cash policy
- Risk Pacing policy
- REDUCE / EXIT behavior
- PS quantity ownership
- Runtime order quantity authority
- G129 BUY_ADD semantics

## USER_APPROVED_PERFORMANCE_INITIATIVE

YES. Phase32-S implements the Phase32-R accepted performance design and does
not treat Historical PnL as parameter-selection evidence.

## Exact User Validation Recommendation

After committing/accepting this repair, the next user-operated validation should
be a fresh Historical run using the standard project command for the current
profile, for example:

```bash
python3 scripts/runtime/run_runtime_test.py --profile historical-extended-smoke --start-date 2022-10-03 --business-days 100 --initial-cash 1000000
```

Codex did not run this command.

## Final Judgment

`PHASE32_S_PC_EVIDENCE_TIERED_ADD_ACCELERATION_IMPLEMENTED`
