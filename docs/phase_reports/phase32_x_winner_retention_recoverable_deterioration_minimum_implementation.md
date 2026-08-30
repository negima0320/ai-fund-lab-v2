# Phase32-X — Winner Retention Recoverable Deterioration Minimum Implementation

## Scope

This phase implemented the Phase32-W accepted design:

`PHASE32_W_WINNER_RETENTION_RECOVERABLE_DETERIORATION_DESIGN_READY`

This is a USER-APPROVED PERFORMANCE INITIATIVE, not a correctness repair.

No fresh-run, resume, replay, or long Historical was executed by Codex. No
future price, future return, future regime, future MFE/MAE, later SELL, final
campaign outcome, or Historical profitability was used to select Production
behavior.

## Root Limitation

The root limitation from Phase32-V/W was:

`soft defensive deterioration history was effectively campaign-scoped rather
than recoverable episode-scoped`.

That made a zero-lot REDUCE intent capable of remaining active as later
persistent EXIT pressure even after PM had observed renewed strength.

## Implementation Summary

Implemented PM-owned soft deterioration episode semantics in
`strategy.sell_semantic_state`:

- `NO_ACTIVE_SOFT_DETERIORATION`
- `SOFT_DETERIORATION_ACTIVE`
- `SOFT_DETERIORATION_PERSISTENT`
- `SOFT_DETERIORATION_CLOSED`
- `TERMINAL_DETERIORATION`

Implemented non-emergency EXIT confirmation states:

- `DEFENSIVE_ONLY`
- `CONFIRMED_DETERIORATION`
- `TERMINAL_BREAKDOWN`

The PM artifact now materializes observability fields for episode identity,
episode state, persistence scope, recovery/de-escalation evidence, hard
deterioration, and EXIT confirmation.

## Episode State Machine

```text
healthy / recovered campaign
  -> REDUCE with non-terminal deterioration
  -> SOFT_DETERIORATION_ACTIVE
  -> later zero-lot REDUCE within the same unrecovered episode
  -> SOFT_DETERIORATION_PERSISTENT
  -> if independent deterioration confirms weakness
       CONFIRMED_DETERIORATION -> persistent EXIT may proceed
     else
       DEFENSIVE_ONLY -> REDUCE/review preserved, no full EXIT
  -> HOLD / ADD with renewed strength
  -> SOFT_DETERIORATION_CLOSED
  -> later soft weakness starts a new episode
```

Terminal deterioration bypasses this soft episode flow:

```text
hard stop / genuine breakdown / Safety / broker / CA / severe risk
  -> TERMINAL_BREAKDOWN
  -> immediate EXIT remains allowed
```

## Renewed-Strength Closure

An active soft deterioration episode closes/de-escalates when PM decision-time
evidence shows:

- PM action is `HOLD` or `ADD`
- canonical sell state is `HEALTHY_OR_RECOVERING`
- recovery state is `RECOVERY_PRESENT`
- PIT proof is `PASS`
- no hard/terminal non-reset condition is present

PM decision-time recovery is authoritative. PC approval, PS positive quantity,
Runtime `BUY_ADD`, or actual fill is not required to recognize recovery.

## Zero-Lot Semantics

Zero-lot REDUCE now has explicit scope:

`ACTIVE_SOFT_EPISODE_ONLY`

It may record PM defensive intent inside the current active episode, but it
does not:

- become terminal evidence by itself;
- survive confirmed recovery as active EXIT debt;
- combine across closed/recovered episodes;
- let PS lot infeasibility redefine PM severity.

## EXIT Confirmation

Non-emergency persistent EXIT now requires:

- active unrecovered soft deterioration episode;
- current contemporaneous deterioration;
- `CONFIRMED_DETERIORATION` or `TERMINAL_BREAKDOWN`;
- PIT `PASS`;
- valid campaign identity;
- no recovery conflict.

`DEFENSIVE_ONLY` preserves REDUCE/review authority but does not authorize full
EXIT from stale/closed soft persistence.

## Immediate EXIT Bypass

Immediate terminal EXIT remains preserved for:

- `hard_stop_current_return`
- genuine `trend_and_opportunity_broken`
- `trend_and_expected_edge_broken`
- Safety hard constraint / full close
- broker block
- corporate-action block
- severe liquidity/risk failure
- explicit canonical Runtime/Safety full-close authority

## ADD / HOLD Recovery

PM `ADD` or `HOLD` can close/de-escalate a soft deterioration episode when the
recovery contract passes. Downstream BQ, PC, PS, Runtime, and fill outcomes do
not control PM lifecycle recovery.

## Phase32-S Compatibility

Preserved:

- Phase32-S ADD acceleration tier semantics
- PC ADD capital magnitude
- NEW/ADD/Cash competition
- Risk Pacing
- PS lot conversion
- G129 BUY_ADD order-increment semantics
- Runtime `BUY_ADD`
- Phase32-F Buy Quality explicit zero preservation
- Phase32-L campaign identity continuity
- Phase32-P/Q REENTRY provenance
- KI-004 Safety separation

## Observability

PM sell semantic evidence now includes:

- `soft_deterioration_episode_id`
- `soft_deterioration_episode_state`
- `episode_start_business_date`
- `episode_last_deterioration_business_date`
- `episode_persistence_severity`
- `episode_increment_evidence`
- `episode_recovery_evidence`
- `episode_deescalation_reason`
- `hard_deterioration_present`
- `exit_confirmation_state`
- `exit_confirmation_evidence`
- `prior_soft_deterioration_cleared`
- `zero_lot_reduce_persistence_scope`
- `future_information_used=false`
- `outcome_used_for_parameter_selection=false`

These fields are also surfaced on PM position rows for actual-path audit.

## Files Changed

- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py`
- `tests/strategy/test_phase32_x_recoverable_deterioration_episode.py`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/phase_reports/phase32_x_winner_retention_recoverable_deterioration_minimum_implementation.md`

Existing unrelated Phase32-S files in the worktree were not reverted or
rewritten by this task.

## Architecture SoT Update

Updated `docs/02_architecture/strategy_architecture_v1.md` to make Phase32-X
recoverable soft deterioration episode semantics durable common SoT, not merely
a phase-report-only design.

## Focused Validation

Passed:

```text
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase32_x_recoverable_deterioration_episode.py \
  tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py \
  tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py \
  tests/strategy/test_phase31_g8_pm_severity_action_mapping.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py \
  tests/strategy/test_phase30_z_reentry_genuine_recovery.py \
  tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py \
  -q
```

Result:

`88 passed in 1.84s`

## Representative Cases

Covered by focused tests:

- 65500-shaped: old soft episode closes after HOLD recovery; later REDUCE starts
  active new episode and does not inherit old EXIT debt.
- 91070-shaped: new REDUCE after recovery remains `DEFENSIVE_ONLY` unless fresh
  confirmation exists.
- 45840-shaped: long HOLD recovery keeps old soft episode inactive.
- 15180-shaped: later soft deterioration gets a different episode identity.
- 61440-shaped: December episode does not authorize January EXIT after recovery.

## Adverse Controls

Covered by focused tests:

- 89180 hard-stop-shaped: `hard_stop_current_return` remains immediate
  `TERMINAL_BREAKDOWN` EXIT.
- 33580-shaped: no-recovery persistent deterioration with independent current
  deterioration can still EXIT.
- 59860-shaped: REDUCE -> EXIT without recovery remains possible when
  confirmation exists.
- Safety / broker / corporate-action / severe liquidity terminal reasons bypass
  recovery logic.

## Regressions

Observed focused regression status:

| Area | Result |
| --- | --- |
| Phase32-S ADD acceleration | PASS |
| G129 BUY_ADD order-increment semantics | PASS |
| Phase32-F Buy Quality explicit zero preservation | PASS through Phase32-S regression tests |
| Phase32-L campaign identity | Not modified; PM tests preserve campaign-id scoping |
| Phase32-P/Q REENTRY provenance | PASS through REENTRY-focused regression |
| KI-004 Safety separation | PASS for terminal bypass; no Safety collapse introduced |
| Hard-stop behavior | PASS |
| Genuine breakdown EXIT | PASS |
| REDUCE authority | PASS |
| EXIT authority | PASS |
| PM / PC / PS / Runtime separation | PASS |

## Strategy Semantic Change

Strategy semantic change: YES.

Changed:

- SELL lifecycle semantics for non-emergency soft deterioration persistence.
- Closed/recovered soft deterioration episodes no longer act as active full
  EXIT authority.
- Repeated zero-lot REDUCE intent alone no longer authorizes full EXIT.
- Non-emergency persistent EXIT now requires active episode confirmation.

Not changed:

- BUY_NEW selection
- ADD acceleration tiers
- ADD magnitude rules
- PC capital competition
- PS lot conversion
- Runtime Planning / Pending / Submit / Execution
- Safety hard constraints
- Cash / Risk Pacing
- G129 BUY_ADD semantics
- hard-stop or genuine-breakdown immediate EXIT

This is an intentional user-approved performance semantic change, not a
correctness repair.

## Parameter-Selection Status

`PARAMETER_SELECTION_DEFERRED`

No recovery-day count, warning count, momentum threshold, return threshold, or
EXIT voting threshold was selected from Historical outcomes. The implementation
uses existing semantic states and PIT evidence.

## Expected Actual-Path Effect

Expected semantic effects:

- some prior persistent EXITs become HOLD/REDUCE instead;
- campaign duration may increase;
- turnover may decrease;
- renewed winner campaigns may survive long enough for later ADD;
- hard/terminal EXIT behavior remains unchanged.

Do not judge this implementation by return in the first actual-path validation.
Judge first by episode closure, changed persistent EXIT, campaign continuation,
hard-stop preservation, and no correctness regression.

## User Validation Recommendation

Recommended user-operated validation:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 30 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Primary early actual-path checks:

- 91070 around 2022-10-24
- 65500 around 2022-10-25
- hard-stop preservation
- no new HALT caused by PM authority
- no Phase32-S/G129 regression

## NO Future-Information Use

Confirmed. Production behavior was selected from current source, Architecture /
SoT, existing PM semantic state, contemporaneous Runtime evidence, and
decision-time PIT concepts. Future outcomes were not used for parameter or rule
selection.

## Final Judgment

`PHASE32_X_WINNER_RETENTION_RECOVERABLE_DETERIORATION_IMPLEMENTED`
