# Phase32-BS Multi-Lot ADD Concentration Cap Boundary Audit

## Executive Summary

Phase32-BS audited the post-BR multi-lot ADD path for:

```text
runtime-test-historical-extended-smoke-20260828T161503510098Z
2022-10-11
94340
```

BR quantity progression is correct:

```text
700 -> 900 -> 1100 -> 1300
```

However, the concentration-cap boundary is not fully safe for resume. The
frontier correctly recalculates weight/headroom lot by lot, and it correctly
blocks cap-crossing lots when the candidate row carries the effective cap. But
the actual `2022-10-11` PC/PS artifact path does not propagate the effective
Strategy cap `0.18` into the marginal frontier candidate row. The frontier
therefore falls back to `0.25`, matching the Safety hard cap, and accepts lot
#3 even though the post-lot weight is above the Strategy cap:

```text
lot #3 post_weight = 0.1875299199
strategy cap = 0.18
safety hard cap = 0.25
frontier cap used = 0.25
```

Result:

```text
Safety hard cap is preserved.
Strategy cap is not enforced per lot on the actual 94340 path.
```

No production code/config/state changes, fresh-run, resume, replay, or backtest
were executed for BS.

## Required Inputs

Read:

- `docs/phase_reports/phase32_br_add_repeated_lot_quantity_consistency_narrow_repair.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

Relevant SoT points:

```text
Portfolio Construction remains allocation and Strategy concentration authority.
Position Sizing remains executable quantity authority.
Safety remains hard guardrail authority.
Strategy target and Safety hard limit are separate authorities.
```

## Artifact Evidence

`strategy/portfolio_construction.json`:

```text
single_name_weight_cap = 0.18
94340 current_quantity = 700
94340 current_weight = 0.101296
94340 reference_price = 145.8
94340 position_campaign_id = pc-4635fa0a129b87ad-94340-0001
```

`strategy/position_sizing_preflight.json`:

```text
strategy_maximum_position_weight = 0.18
safety_maximum_position_weight = 0.25
effective_maximum_position_weight = 0.18
effective_maximum_position_weight_derivation =
  min(strategy_maximum_position_weight, safety_maximum_position_weight)
safety_authority_status = PASS
94340 trading_unit = 100
94340 transaction_quantity_candidate = 200
94340 final_quantity_delta = 200
```

The BR in-memory reproduction of the marginal frontier and authority produces:

```text
authority_result.status = PASS
accepted_target_count = 7
pc_to_ps_consumer_switch_boundary.status = PASS
aggregated_ps_target_count = 5
```

## 94340 Lot-by-Lot Concentration Trace

BR-repaired `94340` ADD candidates:

| Lot | Pre qty | Post qty | Pre weight | Post weight | Increment weight | Strategy cap | Safety cap | Frontier cap used | Strategy headroom after | Safety headroom after | Frontier status |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 700 | 900 | 0.101296 | 0.1300406400 | 0.0287446400 | 0.18 | 0.25 | 0.25 | 0.0499593600 | 0.1199593600 | `PASS` / accepted |
| 2 | 900 | 1100 | 0.1300406400 | 0.1587852799 | 0.0287446400 | 0.18 | 0.25 | 0.25 | 0.0212147201 | 0.0912147201 | `PASS` / accepted |
| 3 | 1100 | 1300 | 0.1587852799 | 0.1875299199 | 0.0287446400 | 0.18 | 0.25 | 0.25 | -0.0075299199 | 0.0624700801 | `PASS` / accepted |

The cap predicate is recalculated lot by lot, but it is using the wrong cap
authority on the actual path:

```text
frontier feasibility.single_name_cap = 0.25
expected effective cap = 0.18
```

Therefore lot #3 is accepted under Safety hard cap but should not be accepted
under the Strategy concentration boundary.

## Focused Synthetic Checks

### Row-Level Effective Cap Present

Synthetic ADD:

```text
current_quantity = 700
current_weight = 0.101296
transaction_quantity_candidate = 200
single_name_cap = 0.18
```

Result:

| Lot | Pre weight | Post weight | Cap used | Status | Disposition |
| ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0.101296 | 0.13004064 | 0.18 | `PASS` | accepted |
| 2 | 0.13004064 | 0.15878528 | 0.18 | `PASS` | accepted |
| 3 | 0.15878528 | 0.18752992 | 0.18 | `FAIL` | `INFEASIBLE_CAP_BLOCKED` |

This proves the lot-by-lot cap predicate itself blocks a +200 lot that crosses
18%, when the effective cap reaches the candidate row.

### Actual-Shape Top-Level Cap Only

Synthetic ADD with only PC top-level `single_name_weight_cap=0.18`, matching
the actual 10/11 shape where the member row lacks `single_name_cap`:

| Lot | Pre weight | Post weight | Cap used | Status | Disposition |
| ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0.101296 | 0.13004064 | 0.25 | `PASS` | accepted |
| 2 | 0.13004064 | 0.15878528 | 0.25 | `PASS` | accepted |
| 3 | 0.15878528 | 0.18752992 | 0.25 | `PASS` | accepted |

This reproduces the actual propagation gap.

### Safety Hard Cap Crossing

Synthetic ADD with `single_name_cap=0.25` and +200-share lots:

| Lot | Pre weight | Post weight | Cap used | Status | Disposition |
| ---: | ---: | ---: | ---: | --- | --- |
| 1 | 0.22 | 0.24 | 0.25 | `PASS` | winner |
| 2 | 0.24 | 0.26 | 0.25 | `FAIL` | `INFEASIBLE_CAP_BLOCKED` |
| 3 | 0.26 | 0.28 | 0.25 | `FAIL` | `INFEASIBLE_CAP_BLOCKED` |

This proves Safety-style hard cap enforcement remains active when the cap is
present as the candidate cap.

## Focused Regression Command

The existing focused BR/BG regression suite remains passing after the audit:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

46 passed
```

No permanent production behavior change was made in this BS audit.

## Defect / No-Defect Judgment

| Boundary | Judgment | Evidence |
| --- | --- | --- |
| BR quantity progression | PASS | `700 -> 900 -> 1100 -> 1300`; BF aggregation passes. |
| Lot-by-lot recomputation | PASS | Each ADD candidate has recomputed `pre_weight`, `post_weight`, headroom, Cash. |
| Cap predicate implementation | PASS when candidate cap is present | Synthetic `0.18` row-cap blocks lot #3. |
| Actual Strategy cap propagation | FAIL | Actual frontier uses `0.25` while PC/PS effective Strategy cap is `0.18`. |
| Safety hard cap | PASS | Actual 94340 remains below `0.25`; synthetic 25% crossing is blocked. |
| Legacy fallback | PASS | No legacy target-gap / zero fallback used. |

## Resume Readiness

BR fixed the prior BF quantity inconsistency, but BS found a separate
concentration authority gap. The halted run should not be resumed into
production behavior until the marginal frontier consumes the correct effective
Strategy concentration cap per ADD lot.

The minimal repair boundary is narrow:

```text
Propagate/resolve PC Strategy cap and Safety hard cap into the marginal
frontier candidate feasibility contract, using effective cap = min(strategy,
safety), fail-closed when required cap evidence is missing or ambiguous.
```

This should not alter fixed share size, Cash, budget, marginal value weights,
PM, PS quantity arithmetic, Runtime mapping, REDUCE/EXIT, Risk Pacing, or
legacy fallback policy.

## Final Judgments

```text
PHASE32_BS_STRATEGY_CAP_ENFORCED_PER_LOT = NO
PHASE32_BS_SAFETY_CAP_ENFORCED = YES
PHASE32_BS_94340_POST_ADD_WEIGHT = 0.1875299199
PHASE32_BS_94340_CAP_STATUS = PASS
PHASE32_BS_CAP_CROSSING_ADD_BLOCKED = NO
PHASE32_BS_MULTI_LOT_ADD_SAFE_TO_RESUME = NO
PHASE32_BS_NEXT_STEP = Narrow repair of marginal frontier cap authority propagation so ADD repeated lots consume effective Strategy/Safety concentration cap per lot and fail closed on missing or ambiguous cap evidence.
```
