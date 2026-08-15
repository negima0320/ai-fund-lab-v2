# Phase29-L21R - Re-entry Recovery Contract Simplification / Source Evidence Wiring Repair

## Executive Summary

L21R production-common Strategy repair is complete at focused-regression scope.

Primary judgment:

`PHASE29_L21R_REENTRY_RECOVERY_CONTRACT_SIMPLIFIED_SOURCE_WIRING_REPAIRED_FOCUSED_REGRESSION_PASS`

Implemented repairs:

- Removed the absolute `runtime_opportunity_score >= 0.10` hard eligibility gate from REENTRY recovery.
- Kept `runtime_opportunity_score` as diagnostic / relative-strength evidence.
- Preserved relative Opportunity qualification through existing rank authority.
- Preserved BQ requalification.
- Preserved 3 completed-business-day cooldown.
- Wired same-day Corporate Event `known_no_event_symbols` into opportunity rows as `corporate_action_status=NO_EVENT`.
- Wired same-day technical trend/momentum fields into opportunity rows.
- Preserved capacity/liquidity fail-closed semantics when capacity evidence is unavailable or severe.
- Added previous EXIT reason observability and reason-class-aware recovery requirements.

No fresh-run, resume, long Historical run, current run mutation, Pending mutation, model/training/Accepted Generation change, schema breaking change, fixed BUY count, cash-forcing, or Historical-only branch was introduced.

## L21Q Confirmed Gaps

L21Q confirmed:

- REENTRY protection is required because Phase28-D20/D21 found short-cycle re-entry churn and loss concentration.
- The absolute `0.10` threshold is not semantically justified for L21I's uncalibrated `runtime_opportunity_score`.
- L21O's 193 CA missing rows were `EXPLICIT_NO_EVENT_NOT_PROPAGATED`, not actual corporate-action risk.
- Current L16 did not consume previous EXIT reason, although D21 design required state-change awareness.

## Repair Boundary

Traced authority chain:

```text
persistent ledger executions
-> L21K prior EXIT materialization
-> Opportunity rows
-> L21R source evidence enrichment
-> PC member reconciliation
-> REENTRY classification
-> REENTRY recovery qualification
-> target allocation
-> Position Sizing
-> Runtime Planning
```

L21R changes are limited to:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- focused tests in `tests/strategy/test_phase29_l21k_prior_exit_materialization.py`
- one existing PC expectation update in `tests/strategy/test_phase22_e_portfolio_construction.py`

The worktree also contains pre-existing Phase diffs unrelated to L21R; they were not reverted.

## Before Contract

Previous REENTRY recovery required:

```text
rank <= 10
runtime_opportunity_score >= 0.10
BQ action in REDUCED/FULL
row-level CA status resolved / no event
capacity_ratio <= 0.03
trend >= 1.0 OR momentum >= 0
```

Weaknesses:

- `0.10` was a hard raw-score gate.
- CA source `NO_EVENT` did not reach PC row.
- Technical source fields did not always reach PC row.
- Missing evidence could be confused with risk.
- Previous EXIT reason was not consumed.

## After Contract

Current L21R REENTRY recovery:

```text
prior EXIT PIT-valid
cooldown >= 3 completed business days
relative Opportunity rank requalified
BQ action requalified
previous EXIT reason observed/classified
reason-relevant technical recovery satisfied
current CA has no blocking event
capacity/liquidity evidence valid
normal PC / PS / Safety / Cash / Gross / Broker decide final quantity
```

`runtime_opportunity_score` remains emitted as `reentry_expected_edge`, but `reentry_score_gate_status=DIAGNOSTIC_ONLY`.

## Absolute Score Gate Repair

Removed as hard gate:

```text
if score < 0.10: reject
```

Focused test confirms:

- `runtime_opportunity_score=0.05`
- rank valid
- BQ valid
- trend/momentum recovery valid
- CA `NO_EVENT`
- capacity valid

Result:

```text
reentry_recovery_status = PASS
```

## Relative Opportunity Qualification

Relative qualification uses existing rank authority:

- rank missing -> `REVIEW_REQUIRED / reentry_rank_missing`
- rank `>10` -> `FAIL_CLOSED / reentry_opportunity_not_requalified`
- rank `<=10` -> opportunity requalification PASS

No new magic rank threshold was introduced; L16's existing rank boundary was retained.

## Corporate Action Wiring

`shadow_runtime._supply_reentry_source_evidence` now enriches opportunity rows from same-day `corporate_event.json`:

- symbol in `known_no_event_symbols` -> `corporate_action_status=NO_EVENT`
- symbol in `known_event_symbols` -> event status, defaulting to `EVENT_PRESENT`
- same-day source present but symbol unknown -> `SOURCE_PRESENT_SYMBOL_STATUS_UNKNOWN`
- source missing/invalid -> `SOURCE_MISSING`

PC now records:

- `reentry_corporate_action_status`
- `reentry_corporate_action_source_status`
- `reentry_corporate_action_source`

Actual blocking event remains fail-closed:

```text
reentry_corporate_action_blocking
```

Genuine source missing remains fail-closed/review:

```text
reentry_corporate_action_source_missing
```

## Technical Recovery Wiring

`shadow_runtime._supply_reentry_source_evidence` also enriches opportunity rows from same-day `technical_features.json`:

- `trend_close_over_ma_20d`
- `price_momentum_return_20d`
- related source status fields

PC now exposes:

- `reentry_trend_recovery_status`
- `reentry_momentum_recovery_status`

No new technical indicator was added.

## Capacity Wiring

PC continues to compute:

```text
capacity_ratio = proposed_target_notional / rolling_median_traded_value_20
```

L21R does not delete this gate and does not add a looser threshold.

If capacity evidence is unavailable:

```text
REVIEW_REQUIRED / reentry_capacity_unavailable
```

If capacity is severe or `capacity_ratio > 0.03`:

```text
FAIL_CLOSED / reentry_capacity_unavailable
```

## Previous EXIT Reason Awareness

PC now records:

- `previous_exit_reason`
- `previous_exit_reason_class`

Supported classes:

- `CORPORATE_ACTION`
- `HARD_STOP`
- `TREND_MOMENTUM`
- `PORTFOLIO_COMPETITION`
- `ADMINISTRATIVE`
- `GENERIC`

Reason-class behavior:

- trend/momentum, hard-stop, corporate-action, and generic exits require technical recovery;
- portfolio-competition / administrative exits do not add an unrelated hard-stop technical penalty;
- corporate-action exits still require no current blocking CA.

No realized PnL is consumed as a Strategy input.

## D21 Conformance

Improved:

- prior EXIT awareness retained;
- short-cycle cooldown retained;
- state/recovery evidence now reason-aware;
- current BQ and relative Opportunity requalification retained;
- missing source remains fail-closed/review;
- no normal BUY_NEW fallback for failed REENTRY.

Still intentionally minimal:

- no richer campaign context store beyond existing prior EXIT fields and reason text;
- no PnL gate;
- no fresh-run performance claim.

## Focused Regression Results

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q
```

Result:

```text
14 passed in 1.37s
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k phase29_l16 -q
```

Result:

```text
7 passed, 67 deselected in 0.28s
```

PASS:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py \
  tests/strategy/test_phase26_h_adaptive_buy_quality.py \
  tests/strategy/test_phase22_aa_corporate_event.py \
  -q
```

Result:

```text
160 passed in 2.74s
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache-l21r PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Result: PASS.

Note: the first compile attempt without `PYTHONPYCACHEPREFIX` failed because Python tried to write pycache under `/Users/negishi/Library/Caches`, outside the sandbox. The tmp-prefixed compile passed.

## BUY_NEW Regression Assessment

PASS.

Existing normal BUY_NEW fixture remains `BUY_NEW` with `reentry_cooldown_status=NOT_APPLICABLE`.

## BUY_ADD Regression Assessment

PASS.

Existing-position ADD remains `BUY_ADD`, and prior EXIT materialization is skipped for currently held symbols.

## Temporal Safety Assessment

PASS.

L21K prior EXIT still uses:

```text
execution.business_date < decision.business_date
```

Existing future/same-day EXIT regression remains PASS. L21R source evidence wiring uses same-day Strategy artifacts only and records `future_source_used=false`.

## Remaining Gaps

- User fresh-run validation is still required.
- Capacity source availability still depends on existing traded-value materialization; L21R preserves fail-closed if the evidence is genuinely absent.
- Previous EXIT reason quality depends on reason fields available in ledger/execution/row context. No PnL or post-hoc performance signal was added.
- Capital cap / one-lot / concentration / gross deployment issues are intentionally out of scope.

## User Fresh-run Command

Codex did not run this.

Recommended short user validation window containing the 23880 sequence:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-08-23 \
  --date-to 2022-09-16 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Post-run Audit Commands

After the user fresh-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --json
```

Read-only aggregate extraction can then inspect the new run's daily Strategy artifacts for:

- total PC candidates
- normal BUY_NEW candidates
- REENTRY candidates
- cooldown fails
- REENTRY policy eligible
- REENTRY positive/zero targets
- CA `NO_EVENT` pass count
- CA source missing count
- blocking CA count
- relative Opportunity fail count
- technical recovery fail count
- capacity fail count
- final positive allocation count
- BUY_NEW / BUY_ADD / REENTRY planning count
- 23880 prior EXIT, reason, cooldown, BQ, opportunity, technical, CA, capacity, final PC target, PS quantity, and Runtime Planning intent

## Primary Judgment

`PHASE29_L21R_REENTRY_RECOVERY_CONTRACT_SIMPLIFIED_SOURCE_WIRING_REPAIRED_FOCUSED_REGRESSION_PASS`

Required final answers:

1. Absolute `runtime_opportunity_score >=0.10` hard gate removed: YES.
2. Raw score `<0.10` alone no longer rejects REENTRY: YES.
3. Relative Opportunity qualification substituted: YES, via existing rank authority.
4. BQ requalification maintained: YES.
5. 3BD cooldown maintained: YES.
6. `known_no_event_symbols` authority reaches PC: YES, via opportunity row enrichment.
7. Actual blocking CA still stops REENTRY: YES.
8. Genuine CA source missing fail-closed/review: YES.
9. Trend/momentum evidence reaches PC: YES, via same-day technical features when source exists.
10. Capacity evidence works when present and fails closed when unavailable: YES.
11. Previous EXIT reason consumed: YES.
12. EXIT reason-specific recovery semantics implemented: YES, minimal reason-class behavior.
13. D21 conformance improved: YES.
14. Normal BUY_NEW regression: PASS.
15. BUYADD regression: PASS.
16. Future-data leakage: not introduced; focused tests PASS.
17. Production repair complete: YES at focused-regression scope.
18. User fresh-run validation can proceed: YES.
