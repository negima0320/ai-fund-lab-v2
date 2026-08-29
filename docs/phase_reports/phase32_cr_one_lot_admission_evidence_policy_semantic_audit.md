# Phase32-CR One-Lot Admission Evidence Policy Semantic Audit

## Executive Summary

This is a READ-ONLY semantic audit. No Production code, config, thresholds, rank/quality policy, model, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

Phase32-CQ fixed materialization: the 16 Day-0 reduced-quality sub-lot candidates now receive explicit `minimum_executable_one_lot_authority.v1` decisions. The non-fresh actual-shaped reproduction produced:

```text
ADMIT_ONE_LOT = 0
BLOCK = 16
REVIEW_REQUIRED = 0
```

Primary blocker:

```text
minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL
```

Audit conclusion: the current CO requirement:

```text
ADMIT_ONE_LOT requires opportunity-quality class in {STRONG, COMPARABLE_HIGH}
```

is not directly inherited from the Phase30 implemented one-lot authority. It is a Phase32-CO semantic strengthening derived from the CM/CL concern that reduced-quality one-lot overshoot must not be authorized by Safety/Cash/cap pass alone.

That strengthening is directionally valid as a fail-closed guard, but it is too coarse as the final policy because broader capital-competition architecture explicitly defines `COMPARABLE_MARGINAL` as a valid but marginal deployment candidate, not as invalid or rejected. Therefore the current policy partially overlaps with the common frontier's responsibility: it blocks `COMPARABLE_MARGINAL` before the candidate can compete against Cash and other securities.

Primary judgment:

```text
MIXED = current 0/16 is defensible as interim fail-closed behavior, but the categorical COMPARABLE_MARGINAL block is overstrict relative to Phase30 and duplicates common frontier comparison semantics.
```

## Sources Reviewed

- `docs/phase_reports/phase32_cq_one_lot_authority_pre_zero_materialization_narrow_repair.md`
- `docs/phase_reports/phase32_co_bounded_minimum_executable_one_lot_authority_migration_implementation.md`
- `docs/phase_reports/phase32_cn_existing_one_lot_authority_policy_reuse_audit.md`
- `docs/phase_reports/phase32_cm_bounded_minimum_executable_one_lot_authority_design.md`
- `docs/phase_reports/phase32_cl_adaptive_buy_quality_allocation_semantics_lot_granularity_authority_audit.md`
- `docs/phase_reports/phase30_v_entry_intelligence_overheated_momentum_one_lot_capital_concentration_repair_design.md`
- `docs/phase_reports/phase30_ak1u_minimum_executable_one_lot_admission_contract_audit.md`
- `docs/phase_reports/phase30_ak2_minimum_executable_one_lot_admission_repair_implementation.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- Current implementation in `src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py`

## Current CO Policy

Current one-lot authority logic performs these checks:

```text
semantic_type in NEW_FIRST_LOT / REENTRY_FIRST_LOT
current quantity = 0
quality_authorized_target_weight > 0
entry action not reject/wait/review
Buy Quality action not reject/wait/review
entry state not overheated/reversal
effective cap evidence PASS
Safety not blocked
Risk Pacing not blocked
Cash source PASS and enough Cash for one lot
one lot <= effective Strategy/Safety cap
opportunity_quality in {STRONG, COMPARABLE_HIGH}
```

If the opportunity class is `COMPARABLE_MARGINAL`, current CO emits:

```text
decision = BLOCK
reason = minimum_one_lot_opportunity_quality_not_supportive:COMPARABLE_MARGINAL
```

## Origin Of STRONG / COMPARABLE_HIGH Requirement

### Phase30

Phase30 did not define a categorical `STRONG` / `COMPARABLE_HIGH` allow-list for minimum executable one-lot admission.

Phase30-AK2 implemented an explicit PC one-lot authority for guarded `BUY_NEW` / `REENTRY` `0 -> 1lot` cases. It required:

- positive PC target below one lot,
- current quantity zero,
- Entry / one-lot admission pass,
- Strategy cap preserved,
- Safety hard cap preserved,
- broker / lot feasibility pass,
- remaining budget sufficient,
- no PS-side independent round-up.

Phase30-V and the Strategy Intelligence SoT said one-lot overshoot may pass only when quality and opportunity evidence justify the overshoot, and Safety hard cap pass alone must not authorize concentration. But they did not encode the exact rule:

```text
COMPARABLE_MARGINAL => categorical BLOCK
```

### Phase32-CM / CO

Phase32-CM required a bounded, explicit authority and said `ADMIT_ONE_LOT` must prove that holding the minimum executable lot is worth exceeding the quality target. It also said Cash availability, Safety pass, or low position count alone must not admit one lot.

Phase32-CO translated that into a concrete deterministic policy by requiring `STRONG` or `COMPARABLE_HIGH`.

Therefore:

```text
STRONG / COMPARABLE_HIGH requirement origin = Phase32-CO implementation of CM/CL semantic repair, not original Phase30 implemented authority.
```

## Meaning Of COMPARABLE_MARGINAL

The broader capital-competition SoT defines:

| Class | Meaning | Valid deployment candidate |
| --- | --- | --- |
| `STRONG` | Exceptional or high-conviction incremental deployment evidence | YES |
| `COMPARABLE_HIGH` | Valid opportunity with above-normal marginal evidence | YES |
| `COMPARABLE_MARGINAL` | Valid opportunity, close enough to Cash optionality that market weakness can make Cash preferable | YES |
| `WEAK_VALID` | Still strategically eligible but marginal | YES, conditionally |
| `INSUFFICIENT` | Missing/stale/contradictory evidence | NO |
| `BLOCKED` | Candidate/Safety/eligibility/PM semantics block deployment | NO |

The SoT also says:

```text
COMPARABLE_MARGINAL must not mean invalid, rejected, missing data, or hard blocked.
NORMAL_DEPLOYMENT + COMPARABLE_MARGINAL may deploy.
CAUTIOUS + COMPARABLE_MARGINAL does not automatically mean zero.
```

Thus `COMPARABLE_MARGINAL` means:

```text
valid but marginal; must compete with Cash and alternatives
```

It does not inherently mean:

```text
Production BUY ineligible
```

## Authority Ownership Assessment

The one-lot authority should decide:

```text
A. whether a sub-lot quality target is allowed to become exactly one minimum-lot candidate for common competition
```

It should not decide:

```text
B. final opportunity superiority among all candidates
C. final BUY
```

The common frontier owns cross-candidate and Cash competition. PS owns quantity conversion. Runtime owns planning from accepted PS-compatible targets.

Current CO uses opportunity-quality to decide whether a candidate can enter competition at all. That is necessary for hard blocks such as missing evidence, cap breach, rejected Quality, BUY_WAIT, overheated/reversal, insufficient Cash, or Safety/Risk block. But a blanket `COMPARABLE_MARGINAL` block overlaps with the frontier because marginal-but-valid candidates are precisely the candidates the frontier is designed to compare against Cash and stronger alternatives.

## Overshoot Risk Assessment

One-lot overshoot cannot be admitted from opportunity class alone. Required PIT dimensions include:

- Buy Quality action/score/band,
- overshoot magnitude and ratio,
- projected post-trade weight,
- Strategy cap,
- Safety cap,
- regime,
- Risk Pacing,
- Cash/budget,
- portfolio fit,
- common alternatives and Cash optionality.

Current CO uses several of these as hard guards, but the final positive admission test collapses to:

```text
opportunity_quality in {STRONG, COMPARABLE_HIGH}
```

This is safe, deterministic, and fail-closed, but it is incomplete. It does not distinguish:

- `33700`: 1.57x overshoot, 3.41% one-lot weight, Strategy cap pass,
- `92420`: 6.65x overshoot, 13.75% one-lot weight, Strategy cap pass,
- `93600`: 8.23x overshoot, 19.11% one-lot weight, Strategy cap fail.

The first and third are not semantically equivalent. A final policy should materialize overshoot severity and cap/Cash/regime context as first-class evidence, then decide whether to create a one-lot competitor. No new numeric threshold should be selected from historical outcome.

## Phase30 vs CO Semantic Delta

Phase30 conceptual behavior for actual Day-0 rows:

- `BUY_NEW_REDUCED_ONLY` was allowed if one-lot admission passed.
- Cap/Safety/Cash/budget/entry guards were hard.
- No categorical `COMPARABLE_MARGINAL` hard block existed.

Current CO behavior:

- `COMPARABLE_MARGINAL` is categorical BLOCK even when cap/Safety/Cash/budget pass.
- This prevents common frontier competition from seeing the one-lot candidate.

Therefore:

```text
PHASE30_POLICY_DELTA = YES
```

The delta is not performance-derived in the artifacts reviewed; it is a conservative semantic repair introduced during Phase32-CO.

## Representative Decision Matrix

The matrix below uses the Phase32-CQ non-fresh actual-shaped reproduction over CP Day-0 artifacts. It does not use future outcome or PnL.

| Symbol | Rank | Quality score | Quality target | One-lot weight | Ratio | Current CO decision | Exact blocker | Phase30 conceptual decision | Frontier qualification if not categorically blocked | Strategy/Safety status |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `93600` | 10 | 0.690580 | 0.023228 | 0.19110 | 8.23x | `BLOCK` | `minimum_one_lot_exceeds_effective_single_name_cap`; `COMPARABLE_MARGINAL` | `BLOCK_STRATEGY_CAP` | NO | Strategy cap block; Safety cap pass |
| `33700` | 17 | 0.644242 | 0.021670 | 0.03410 | 1.57x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `83060` | 20 | 0.612652 | 0.020607 | 0.06480 | 3.14x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `92420` | 21 | 0.615140 | 0.020691 | 0.13750 | 6.65x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `58200` | 23 | 0.598170 | 0.020120 | 0.17467 | 8.68x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `41920` | 24 | 0.594423 | 0.019994 | 0.07880 | 3.94x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `45750` | 27 | 0.574196 | 0.019314 | 0.06760 | 3.50x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `91070` | 30 | 0.545394 | 0.018345 | 0.07100 | 3.87x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `70780` | 31 | 0.545825 | 0.018359 | 0.11080 | 6.04x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `99840` | 32 | 0.537210 | 0.018070 | 0.12453 | 6.89x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `50250` | 34 | 0.520304 | 0.017501 | 0.09970 | 5.70x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `82540` | 35 | 0.513128 | 0.017260 | 0.03020 | 1.75x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `45410` | 36 | 0.506916 | 0.017051 | 0.04360 | 2.56x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `70690` | 38 | 0.499821 | 0.016812 | 0.06325 | 3.76x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `96100` | 41 | 0.471220 | 0.015850 | 0.01980 | 1.25x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |
| `44170` | 44 | 0.457028 | 0.015373 | 0.17200 | 11.19x | `BLOCK` | `COMPARABLE_MARGINAL` | likely `ADMIT` if cap/Safety/Cash/budget/entry pass | YES, subject to common frontier | PASS |

Summary:

```text
Current CO: 16 BLOCK
Phase30 conceptual: 15 likely ADMIT, 1 Strategy-cap BLOCK
```

The Phase30 conceptual column means only that the row would likely become a one-lot candidate under the older cap/Safety/budget/entry guard chain. It does not mean final BUY was guaranteed, and it does not use historical outcome.

## Interpretation Of 0/16 ADMIT

### Semantically Justified Parts

The following are justified:

- `93600` is a valid explicit BLOCK because one lot breaches the 18% effective Strategy cap.
- All rows are reduced/caution and should not receive implicit one-lot rescue.
- A fail-closed interim policy is safer than allowing Safety/Cash pass alone to admit extreme one-lot overshoot.

### Overstrict / Overlapping Parts

The following are not fully justified:

- `COMPARABLE_MARGINAL` is not an invalid class.
- Under normal deployment, `COMPARABLE_MARGINAL` may still deploy if it beats alternatives/Cash.
- Blocking every `COMPARABLE_MARGINAL` one-lot candidate before common frontier means the one-lot authority is partly deciding final opportunity superiority.
- It treats 1.25x, 1.57x, 3.14x, 6.65x, and 11.19x overshoot mostly the same unless cap is breached.

## Defect / Repair Judgment

Production repair is justified, but not as a threshold/rank tuning task.

The repair should be a design/semantic repair to the one-lot admission contract:

- Keep explicit authority.
- Keep CH/CJ quality target preservation.
- Keep CQ pre-zero materialization.
- Keep cap/Safety/Risk/Cash fail-closed guards.
- Do not restore implicit Phase30 one-lot rescue.
- Do not treat `COMPARABLE_MARGINAL` as automatically admitted.
- Do not treat `COMPARABLE_MARGINAL` as categorically invalid.
- Define an authority split where one-lot admission decides whether the overshoot is representable as a candidate, then common frontier decides whether that candidate beats Cash and alternatives.

No short fresh validation is needed before that repair because CQ reproduction already gives the exact policy-level reason for 0/16. A fresh run before repair would only confirm the same explicit BLOCK behavior.

## Final Judgments

PHASE32_CR_STRONG_HIGH_REQUIREMENT_ORIGIN = Phase32-CO semantic strengthening of the CM/CL bounded one-lot design; not directly inherited from Phase30 implemented authority

PHASE32_CR_COMPARABLE_MARGINAL_SEMANTIC = valid but marginal deployment candidate that should normally compete with Cash/alternatives; not inherently invalid or Production BUY-ineligible

PHASE32_CR_PHASE30_POLICY_DELTA = YES

PHASE32_CR_ONE_LOT_COMMON_FRONTIER_RESPONSIBILITY_OVERLAP = YES

PHASE32_CR_ZERO_OF_16_ADMIT_SEMANTICALLY_JUSTIFIED = PARTIAL

PHASE32_CR_CURRENT_POLICY_OVERSTRICT = PARTIAL

PHASE32_CR_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_CR_SHORT_FRESH_VALIDATION_NEEDED_BEFORE_REPAIR = NO

PHASE32_CR_NEXT_STEP = Design/implement a narrow one-lot admission policy split: hard-block missing/rejected/cap/Safety/Risk/Cash/overheated evidence, materialize overshoot severity, and allow valid `COMPARABLE_MARGINAL` sub-lot rows to become one-lot competitors only when bounded PIT evidence supports representability; final deployment must remain with common frontier competition.
