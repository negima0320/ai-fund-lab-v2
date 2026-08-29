# Phase32-CO Bounded Minimum Executable One-Lot Authority Migration Implementation

## Executive Summary

Phase32-CO migrated the Phase30 PC-owned minimum executable one-lot authority into the current CH/CJ/CC/BF marginal capital frontier path.

The repaired path now separates three cases:

```text
normal:
one_lot_weight <= quality_authorized_target_weight
-> existing quality-bounded CC NEW/REENTRY multi-lot path

sub-lot:
one_lot_weight > quality_authorized_target_weight > 0
-> minimum_executable_one_lot_authority.v1
-> ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED

ADMIT_ONE_LOT:
-> exactly one NEW_FIRST_LOT / REENTRY_FIRST_LOT candidate
-> common NEW / REENTRY / ADD / Cash frontier
-> BF aggregate only if accepted
-> PS quantity conversion
```

`ADMIT_ONE_LOT` does not force deployment. It only permits one candidate to enter common capital competition. Cash can still win, budget can still stop deployment, and cap/Safety/Risk constraints remain authoritative.

No fresh-run, resume, replay, backtest, threshold tuning, historical PnL selection, PM change, PS arithmetic change, Runtime mapping change, REDUCE/EXIT change, ADD semantic change, Cash policy change, or Risk Pacing change was performed.

## Design Inputs

Reviewed:

- `docs/phase_reports/phase32_cm_bounded_minimum_executable_one_lot_authority_design.md`
- `docs/phase_reports/phase32_cn_existing_one_lot_authority_policy_reuse_audit.md`
- `docs/phase_reports/phase32_cl_adaptive_buy_quality_allocation_semantics_lot_granularity_authority_audit.md`
- `docs/phase_reports/phase32_cj_quality_deployable_lot_aware_boundary_narrow_repair.md`
- `docs/phase_reports/phase32_ch_adaptive_buy_quality_target_authority_preservation_implementation.md`
- Phase30 one-lot authority design / implementation reports
- PC / Buy Quality / CC / BF / PS / Safety / Risk Pacing architecture contracts

Permanent SoT updated:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

## Changed Files

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase32_co_bounded_minimum_executable_one_lot_authority_migration_implementation.md`

## Implementation

### PC-Owned One-Lot Authority

Added bounded one-lot evaluation inside entry target magnitude resolution for `NEW_FIRST_LOT` / `REENTRY_FIRST_LOT`.

For quality-enforced rows where the quality-authorized target floors to zero trading units, PC now materializes:

```text
minimum_executable_one_lot_authority.v1
```

The authority emits:

- `decision = ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED`
- compatibility alias `decision_alias = ADMIT` when admitted
- `quality_authorized_target_weight`
- `pre_quality_base_target_weight`
- `quality_allocation_adjustment`
- `one_lot_weight`
- `one_lot_notional`
- `trading_unit`
- `overshoot_weight`
- `target_to_one_lot_ratio`
- `one_lot_to_target_ratio`
- `projected_post_trade_weight`
- Buy Quality action / score / band
- opportunity / rank evidence
- entry state evidence
- regime / risk evidence
- Strategy cap status
- Safety cap status
- Risk Pacing status
- Cash / budget status
- source lineage
- reason codes
- `future_information_used = false`
- `historical_outcome_used = false`

### Decision Semantics

`ADMIT_ONE_LOT` requires all of:

- NEW/REENTRY first-lot semantic
- current quantity zero
- positive quality-authorized target
- valid one-lot weight/notional
- entry action not reject / wait / review
- Buy Quality action not reject / wait / review
- entry state not overheated or reversal-risk
- effective Strategy/Safety cap evidence pass
- one lot within effective cap
- Cash evidence pass and sufficient for one lot
- Risk Pacing not blocked
- existing opportunity-quality class supportive: `STRONG` or `COMPARABLE_HIGH`

`BLOCK` is emitted for evidence-supported non-admission, including:

- entry / quality hard block
- overheated or reversal entry
- cap or Safety breach
- Risk Pacing block
- insufficient Cash
- opportunity quality not supportive, for example `COMPARABLE_MARGINAL`

`REVIEW_REQUIRED` is emitted for missing or ambiguous required evidence, including:

- missing one-lot price/weight/notional
- missing or invalid effective cap authority
- missing Cash source
- insufficient opportunity-quality evidence

No new historical-performance-derived numeric overshoot threshold was introduced. The policy reuses existing categorical PIT evidence and existing cap/Safety/Cash/Risk guardrails.

### CC/BF Integration

When `ADMIT_ONE_LOT` is emitted:

- `pc_target_executable_quantity` becomes exactly one trading unit
- `_entry_target_lot_candidates` creates exactly one candidate
- the candidate enters common frontier competition
- the candidate can lose to Cash
- BF aggregates only accepted targets

When `BLOCK` or `REVIEW_REQUIRED` is emitted:

- no deployable BF/PS target is produced
- the diagnostic candidate remains visible for explainability
- fail-closed behavior is preserved

Second-lot-plus expansion remains forbidden for the minimum one-lot authority because the executable quantity is exactly one trading unit.

### Submit / PS Compatibility

Existing legacy consumers accepted `decision = ADMIT`. They now also accept `decision = ADMIT_ONE_LOT` for the same authority while preserving all existing checks:

- symbol / intent match
- reason `MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED`
- one-lot quantity and notional match
- Strategy cap preserved
- Safety hard cap preserved
- no independent PS round-up

This is a schema compatibility shim, not a fallback path.

## Representative Focused Cases

Covered by focused regression:

- supportive sub-lot `33700`-style case emits `ADMIT_ONE_LOT`, creates one candidate, and BF aggregates one lot when it wins.
- reduced/marginal `92420`-style case emits `BLOCK`, with explicit non-supportive opportunity-quality reason.
- missing Cash evidence emits `REVIEW_REQUIRED` and produces no accepted target.
- admitted one-lot candidate can lose to Cash and produces no BF/PS target.
- normal target at/above one lot continues through existing CC multi-lot path.
- ADD PASS-only and BF-only behavior remains covered by existing BZ/BF tests.
- Phase30 legacy one-lot authority tests continue to pass.
- submit-feasibility accepts the new `ADMIT_ONE_LOT` decision only through the validated authority surface.

## Verification

Focused regression:

```text
python3 -m pytest -q \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase30_ak3r1_submit_feasibility_accepts_authorized_minimum_executable_one_lot \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase32_co_submit_feasibility_accepts_admit_one_lot_decision
```

Result:

```text
65 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py \
  src/ai_fund_lab_v2/strategy/portfolio_construction.py \
  src/ai_fund_lab_v2/strategy/position_sizing.py \
  src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py \
  src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py
```

Result:

```text
PASS
```

The first compile attempt without `PYTHONPYCACHEPREFIX` failed because Python attempted to write bytecode under `~/Library/Caches`, which is outside the sandbox write permissions. The sandbox-safe compile passed.

## Preservation

Preserved:

- CH/CJ Buy Quality reduced target semantics
- CC NEW/REENTRY multi-lot for normal one-lot-or-larger targets
- BZ ADD PASS-only / BF-only authority
- BR ADD quantity progression
- BT effective Strategy/Safety cap enforcement
- common NEW/REENTRY/ADD/Cash frontier competition
- Cash optionality
- Risk Pacing block behavior
- PS arithmetic ownership
- Runtime mapping
- REDUCE / EXIT
- legacy fallback zero
- PIT-only / no future outcome fields

## Final Judgments

PHASE32_CO_PHASE30_ONE_LOT_AUTHORITY_REUSED = YES

PHASE32_CO_ADMIT_BLOCK_REVIEW_IMPLEMENTED = YES

PHASE32_CO_QUALITY_SEMANTICS_PRESERVED = YES

PHASE32_CO_OVERSHOOT_EVIDENCE_EXPLICIT = YES

PHASE32_CO_COMMON_FRONTIER_CONNECTED = YES

PHASE32_CO_EXTREME_OVERSHOOT_NOT_CAP_ONLY = YES

PHASE32_CO_SECOND_LOT_FORBIDDEN = YES

PHASE32_CO_ADD_NON_REGRESSION = PASS

PHASE32_CO_LEGACY_FALLBACK_ZERO = YES

PHASE32_CO_REGRESSION_STATUS = PASS

PHASE32_CO_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_CO_NEXT_STEP = User-operated short fresh validation to confirm Day-0 high-price reduced-quality one-lot candidates materialize as `ADMIT_ONE_LOT` / `BLOCK` / `REVIEW_REQUIRED` on actual artifacts and only reach PS through BF accepted targets.
