# Phase32-CS One-Lot Representability vs Final Competition Semantic Repair

## Executive Summary

Phase32-CS repaired the responsibility overlap identified in Phase32-CR. The one-lot authority no longer treats `COMPARABLE_MARGINAL` as a categorical hard block. Instead, it decides whether a reduced-quality sub-lot target is representable as exactly one minimum-lot candidate. Final deployment remains owned by the common marginal capital frontier.

No fresh-run, resume, replay, backtest, historical outcome tuning, rank cutoff, quality threshold tuning, opportunity policy tuning, PS arithmetic change, Runtime change, ADD change, REDUCE/EXIT change, or legacy fallback restoration was performed.

The new split is:

```text
one-lot authority:
  hard-block invalid / rejected / missing / cap / Safety / Risk / Cash / lot infeasible evidence
  decide whether sub-lot target may be represented as one candidate

common frontier:
  decide whether the one-lot candidate beats other NEW / REENTRY / ADD / Cash
```

For `COMPARABLE_MARGINAL`, the candidate is no longer blocked solely because the opportunity class is marginal. It may be represented when hard guards pass and the one-lot expression does not exceed the original pre-quality/base PC target. If one lot exceeds the PC base target, the block is now explicit:

```text
minimum_one_lot_exceeds_pre_quality_base_target
```

This uses an existing PC semantic boundary, not a new historical-performance threshold.

## Sources Reviewed

- `docs/phase_reports/phase32_cr_one_lot_admission_evidence_policy_semantic_audit.md`
- `docs/phase_reports/phase32_cq_one_lot_authority_pre_zero_materialization_narrow_repair.md`
- `docs/phase_reports/phase32_co_bounded_minimum_executable_one_lot_authority_migration_implementation.md`
- `docs/phase_reports/phase32_cm_bounded_minimum_executable_one_lot_authority_design.md`
- `docs/phase_reports/phase32_cn_existing_one_lot_authority_policy_reuse_audit.md`
- `docs/phase_reports/phase30_v_entry_intelligence_overheated_momentum_one_lot_capital_concentration_repair_design.md`
- `docs/phase_reports/phase30_ak1u_minimum_executable_one_lot_admission_contract_audit.md`
- `docs/phase_reports/phase30_ak2_minimum_executable_one_lot_admission_repair_implementation.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

## Implementation

Changed files:

- `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `docs/phase_reports/phase32_cs_one_lot_representability_vs_final_competition_semantic_repair.md`

### Policy Change

Before:

```text
opportunity_class not in {STRONG, COMPARABLE_HIGH}
-> BLOCK
```

After:

```text
INSUFFICIENT / BLOCKED / missing opportunity quality
-> REVIEW_REQUIRED

unsupported non-valid classes
-> BLOCK

COMPARABLE_MARGINAL
-> not categorical BLOCK
-> representability evaluation
```

For `COMPARABLE_MARGINAL`, CS adds an existing-authority representability guard:

```text
if one_lot_weight > pre_quality_base_target_weight:
    BLOCK minimum_one_lot_exceeds_pre_quality_base_target
else:
    ADMIT_ONE_LOT and defer final superiority to common frontier
```

Rationale:

- The quality-adjusted target remains binding against silent re-expansion.
- A one-lot exception may exceed the reduced quality target only through explicit authority.
- For marginal opportunities, one-lot representation should not exceed the PC's original base target. That would require stronger evidence than `COMPARABLE_MARGINAL`.
- `STRONG` / `COMPARABLE_HIGH` preserve the previous positive admission behavior if hard guards pass.

### Preserved Hard Blocks

Still blocked or reviewed before common frontier:

- invalid semantic type,
- current position / non-first-lot case,
- non-positive quality target,
- Entry reject / wait / review,
- Buy Quality reject / wait / review,
- overheated / reversal-risk entry,
- missing effective cap authority,
- Strategy/effective cap breach,
- Safety cap breach,
- Safety blocked,
- Risk Pacing hard block,
- missing Cash evidence,
- insufficient Cash for one lot,
- missing/insufficient opportunity-quality evidence,
- one lot exceeding pre-quality/base PC target for `COMPARABLE_MARGINAL`.

### Common Frontier Ownership

When `ADMIT_ONE_LOT` is emitted:

- exactly one candidate is generated,
- no second lot is authorized,
- candidate may lose to Cash,
- candidate may lose to stronger securities,
- BF/PS target appears only after frontier acceptance.

## Focused Tests

Added / updated coverage:

| Case | Expected result |
| --- | --- |
| `COMPARABLE_MARGINAL` no longer automatically blocks | `ADMIT_ONE_LOT` when representability guard passes |
| representable `COMPARABLE_MARGINAL` | one candidate reaches frontier and BF if accepted |
| admitted one-lot can lose to Cash | no BF/PS target when Cash wins |
| excessive representability mismatch | `BLOCK`, reason `minimum_one_lot_exceeds_pre_quality_base_target` |
| Strategy cap breach | `BLOCK` |
| Safety cap breach | `BLOCK` |
| missing Cash evidence | `REVIEW_REQUIRED` |
| `STRONG` / `COMPARABLE_HIGH` | previous admission behavior preserved |
| second lot | forbidden by one-lot target quantity |
| ADD | unaffected by one-lot authority |
| BF/PS | only after frontier acceptance |

## Actual-Shaped Reproduction

A non-fresh reproduction was run against the existing Phase32-CP Day-0 artifacts:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260829T050706122946Z/daily/2022-10-03
```

Result after CS:

| Metric | Result |
| --- | ---: |
| Materialized one-lot authorities | 16 |
| `ADMIT_ONE_LOT` | 2 |
| `BLOCK` | 14 |
| `REVIEW_REQUIRED` | 0 |
| Accepted one-lot BF targets | 2 |
| `INFEASIBLE_LOT` | 13 |
| `INFEASIBLE_CAP_BLOCKED` | 1 |

Representative outcomes:

| Symbol | Decision | Disposition | One-lot / quality target | Reason |
| --- | --- | --- | ---: | --- |
| `33700` | `BLOCK` | `INFEASIBLE_LOT` | 1.57x | `minimum_one_lot_exceeds_pre_quality_base_target` |
| `83060` | `BLOCK` | `INFEASIBLE_LOT` | 3.14x | `minimum_one_lot_exceeds_pre_quality_base_target` |
| `92420` | `BLOCK` | `INFEASIBLE_LOT` | 6.65x | `minimum_one_lot_exceeds_pre_quality_base_target` |
| `93600` | `BLOCK` | `INFEASIBLE_CAP_BLOCKED` | 8.23x | `minimum_one_lot_exceeds_effective_single_name_cap`; `minimum_one_lot_exceeds_pre_quality_base_target` |
| `58200` | `BLOCK` | `INFEASIBLE_LOT` | 8.68x | `minimum_one_lot_exceeds_pre_quality_base_target` |
| `96100` | `ADMIT_ONE_LOT` | `ACCEPTED_INCREMENTAL_TARGET` | 1.25x | `comparable_marginal_one_lot_representable_deferred_to_common_frontier` |
| `82540` | `ADMIT_ONE_LOT` | `ACCEPTED_INCREMENTAL_TARGET` | 1.75x | `comparable_marginal_one_lot_representable_deferred_to_common_frontier` |

BF target symbols after the actual-shaped reproduction:

```text
33500, 37820, 67860, 76470, 82540, 89180, 94340, 96100
```

The new one-lot BF targets are:

```text
82540: +100
96100: +100
```

This is the desired semantic shape: `COMPARABLE_MARGINAL` is not automatically blocked, but large representability mismatches and cap breaches remain blocked before final competition.

## Verification

Focused CS/CQ/CO/CH/CC tests:

```text
python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  -k 'phase32_cs or phase32_cq or phase32_co_sub_lot or phase32_ch_named or phase32_cc_reentry_target_magnitude'
```

Result:

```text
11 passed, 42 deselected
```

Full marginal frontier authority suite:

```text
python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
53 passed
```

Nearby PC lot-aware regression subset:

```text
python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py \
  -k 'phase32_cj or phase29_l21s_one_lot or phase32_ch'
```

Result:

```text
5 passed, 119 deselected
```

Submit-feasibility one-lot compatibility subset:

```text
python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -k 'phase32_co or minimum_executable_one_lot or pc_discrete_quantity_authority_future_information_flag_invalid'
```

Result:

```text
2 passed, 41 deselected
```

Compile:

```text
PYTHONPYCACHEPREFIX=/tmp/phase32_cs_pycache python3 -m py_compile \
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

## Preservation

Preserved:

- CQ pre-zero one-lot materialization,
- CH/CJ Buy Quality target reduction semantics,
- CO explicit `ADMIT_ONE_LOT` / `BLOCK` / `REVIEW_REQUIRED` authority,
- exactly one-lot only,
- no second-lot one-lot authority,
- common frontier final competition,
- BZ ADD PASS-only / BF-only authority,
- Strategy 18% / Safety 25% cap semantics,
- Cash optionality,
- Risk Pacing hard blocks,
- PS arithmetic,
- Runtime mapping,
- REDUCE / EXIT,
- legacy fallback zero,
- PIT-only / no historical outcome fields.

No Architecture SoT update was required because CS implements the CR interpretation of existing SoT responsibility boundaries.

## Final Judgments

PHASE32_CS_COMPARABLE_MARGINAL_CATEGORICAL_BLOCK_REMOVED = YES

PHASE32_CS_ONE_LOT_REPRESENTABILITY_SEPARATED = YES

PHASE32_CS_FINAL_BUY_OWNED_BY_COMMON_FRONTIER = YES

PHASE32_CS_HARD_GUARDS_PRESERVED = YES

PHASE32_CS_EXTREME_OVERSHOOT_STILL_BLOCKABLE = YES

PHASE32_CS_CQ_CH_CJ_GUARDRAILS_PRESERVED = YES

PHASE32_CS_ADD_NON_REGRESSION = PASS

PHASE32_CS_REGRESSION_STATUS = PASS

PHASE32_CS_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_CS_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm actual artifacts materialize `COMPARABLE_MARGINAL` one-lot representability, keep 93600-style cap breaches blocked, and route only accepted one-lot candidates through BF/PS.
