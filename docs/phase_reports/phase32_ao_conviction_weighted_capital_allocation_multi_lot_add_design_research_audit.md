# Phase32-AO - Conviction-Weighted Capital Allocation / Multi-Lot ADD Design Research Audit

## Executive Summary

Phase32-AO is a READ-ONLY design research audit for run:

```text
runtime-test-historical-extended-smoke-20260827T093649849074Z
```

Latest valuation-ready coverage observed during this audit:

```text
2022-10-03 through 2023-12-19
300 completed valuation-ready business days
```

Primary judgment:

```text
Current behavior is internally consistent, but conviction-to-capital resolution is compressed.
Multi-lot ADD is architecturally valid as a future Portfolio Construction / Capital Value extension.
It is not implementation-ready as a direct production repair.
```

The evidence does not support a fixed-position-count rule. Position count should remain an output of opportunity quality, capital budget, Cash optionality, concentration, lot feasibility, and Safety. The stronger architecture direction is a starter / confirmation / scale model in which:

- valid NEW / REENTRY can start as one-lot or small positions;
- proven campaigns can receive additional capital only when PIT-safe continuation and marginal ADD evidence remain strong;
- each additional ADD lot is a separate marginal capital decision;
- ADD, NEW, REENTRY, and Cash compete on a more comparable marginal-value representation before Position Sizing converts to discrete quantity.

No production code, config, thresholds, schema, model, runtime state, replay, resume, fresh run, or backtest was changed or executed.

## Inputs

Primary inherited reports:

- `docs/phase_reports/phase32_an_conviction_sizing_100_share_dominance_root_cause_audit.md`
- `docs/phase_reports/phase32_am_buy_new_early_failure_vs_winner_pit_divergence_deep_audit.md`
- `docs/phase_reports/phase32_ak_post_ai_long_horizon_early_mid_run_characterization_audit.md`
- `docs/phase_reports/phase32_al_post_ai_sideways_regime_avoidable_loss_and_winner_retention_characterization_audit.md`

Architecture / SoT sources:

- `docs/00_vision/investment_philosophy.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/phase_reports/phase31_g54_capital_budget_envelope_multi_allocation_implementation_planning.md`
- `docs/phase_reports/phase31_g60_lot_aware_market_quality_binding_readiness_audit.md`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `configs/strategy/position_sizing.json`

## Inherited AN / AM / AK / AL Findings

AN established that BUY order sizing is dominated by one-lot or small-lot execution:

| Finding | Inherited value |
| --- | ---: |
| BUY_NEW fill total | 487 |
| BUY_NEW 100-share ratio | 82.3% |
| REENTRY fill total | 13 |
| REENTRY 100-share ratio | 30.8% |
| BUY_ADD fill total | 11 |
| BUY_ADD 100-share ratio | 100.0% |
| Median BUY notional | JPY 57,900 |
| Conviction allocation relationship | WEAK |
| Target-weight compression | YES |
| Sizing implementation defect | NO |

AM / AL established that BUY_NEW early failure is material, but T0 separability is poor and lost-winner risk is high. This argues against a blunt fixed count or hard admission filter. The better research direction is decision-time warning persistence and winner retention control.

AK / AL established that REENTRY repair had positive long-horizon effect and REENTRY is not the main churn driver. Cash underdeployment and PC/MCC optionality remain partial bottlenecks, but no mandatory production defect was established.

## Current Capital Architecture

The current SoT separates authorities:

| Responsibility | Owner |
| --- | --- |
| opportunity / relative score | Opportunity Ranking / Candidate evidence |
| PM action intent | Position Management |
| capital budget / deployment posture | Portfolio Policy |
| scarce capital allocation and Cash competition | Portfolio Construction |
| target-to-quantity conversion | Position Sizing |
| hard constraints | Safety |
| order consumption | Runtime |

`portfolio_construction_and_position_sizing_contract.md` defines `target_weight` as the Portfolio Construction-owned target portfolio ratio, and Position Sizing consumes target weight, portfolio value, reference price, trading unit, current quantity, cap, and minimum-notional policy. Position Sizing must not reinterpret opportunity score as capital authority.

`high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md` confirms the current system already performs capital competition among `NEW_BUY`, `BUY_ADD`, and Cash. The documented limitation is semantic resolution: more PIT-safe upstream differentiation exists than survives into final capital classification, and NEW/ADD/Cash do not yet share a common high-resolution marginal capital value unit.

## One-Lot ADD Origin

The current one-lot ADD result is not a simple stray constant in Position Sizing. It emerges from this chain:

```text
PM ADD intent
-> PC capital / lot-aware discrete executable authority
-> accepted incremental weight
-> Position Sizing ADD branch
-> runtime planning quantity
```

The ADD branch in `position_sizing.py` consumes `accepted_incremental_weight` / `lot_aware_accepted_incremental_weight`, then defers to PC discrete executable authority when present. In the current run, ADD rows with positive authority all resolved to 100 shares. Rows without positive ADD increment preserved the existing baseline and emitted zero delta.

AO classification:

```text
PHASE32_AO_ONE_LOT_ADD_ORIGIN = CONSERVATIVE_TRANSITIONAL_DESIGN
```

Reason: Phase31 architecture migrated from single-winner capital competition toward multi-allocation and lot-aware authority, but the active ADD path remains conservative: PC can admit ADD, yet observed ADD increments are one-lot only. This is not a mandatory defect, but it is also not a permanent architecture principle.

## Existing Capital-Value Authority

Existing SoT already recognizes marginal capital value as a Portfolio Construction-owned concept. It is currently limited in resolution, and the future SoT explicitly says high-resolution marginal value is a deferred capability, not an implemented production authority.

Important SoT principles:

- ADD should be evaluated as executable marginal increments.
- Repeated ADD increments must be independently evaluable.
- PM `ADD` is directional intent and does not prove the ADD increment beats NEW, another ADD, or Cash.
- Marginal desirability and executable feasibility must remain separate.
- Runtime must not recompute capital priority.
- Historical outcome, future return, and fill outcome must not be scoring inputs.

## Compression Analysis

Observed AO extension through 2023-12-19:

| Metric | Value |
| --- | ---: |
| ADD Position Sizing rows | 334 |
| ADD rows selected / positive PC quantity | 12 |
| ADD rows with PC/final quantity 100 | 12 |
| ADD rows with PC/final quantity >= 200 | 0 |
| ADD rows with requested target gap < 1 lot | 330 |
| ADD rows with requested target gap 1-2 lots | 4 |
| ADD rows with requested target gap >= 2 lots | 0 |

Positive target-weight distribution:

| Type | Positive rows | Median target weight | p25 / p75 |
| --- | ---: | ---: | ---: |
| NEW_BUY | 894 | 3.14% | 1.88% / 5.43% |
| ADD | 334 | 2.12% | 2.04% / 2.58% |

Authorized quantity distribution:

| Type | Dominant result |
| --- | --- |
| NEW_BUY | Many 0, many 100, with observed 200+ share rows |
| ADD | 322 zero rows, 12 one-lot rows, 0 multi-lot rows |
| REENTRY | observed zero in this PS aggregate pass; REENTRY fills were characterized in AK/AN |

The key AO finding is that current ADD target gaps are already compressed before final execution. Multi-lot ADD cannot be achieved safely by only changing the final lot consumer. The upstream capital-value and target-gap mapping must first justify a larger accepted incremental weight or a sequence of independently justified ADD lot increments.

## Representative ADD Target-Gap Evidence

Rows with requested ADD gap barely above one lot:

| Date | Symbol | Rank | Quality | Target wt | Current wt | Increment wt | Price | Requested lots | PC qty |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-06 | 94340 | 2 | 0.7839 | 2.77% | 2.77% | 1.38% | 147.3 | 1.00 | 100 |
| 2022-11-01 | 94320 | 1 | 0.7930 | 7.79% | 6.24% | 1.55% | 162.5 | 1.02 | 100 |
| 2022-11-04 | 94320 | 1 | 0.7615 | 9.08% | 7.58% | 1.50% | 160.2 | 1.01 | 100 |
| 2023-02-15 | 54010 | 3 | 0.7764 | 9.62% | 4.76% | 4.87% | 591.2 | 1.02 | 100 |

These rows support the existence of ADD/winner capitalization, but they do not prove current accepted target gaps already demand two or more lots. The evidence supports research into why accepted ADD target gaps remain this low, not an immediate multi-lot production switch.

## Starter / Confirmation / Scale Model

AO accepts the principle:

```text
starter -> confirmation -> scale
```

Interpretation:

- Starter: one-lot / small NEW or REENTRY entries are legitimate when evidence is valid but not yet confirmed.
- Confirmation: PM continuation, trend/momentum durability, buy quality, and campaign evidence should determine whether the campaign is still strong.
- Scale: additional ADD lots should be allowed only when each next lot has superior marginal capital value versus NEW, other ADD, and Cash.

This fits the stated investment philosophy: capture swing momentum in good companies where the market has started to recognize strength, while avoiding day trading, blind averaging, and long unattended holds.

## ADD vs NEW Competition

ADD and NEW are not currently on a fully common cardinal value scale.

Evidence:

- The architecture documents acknowledge that NEW_BUY, BUY_ADD, and Cash lack a common high-resolution marginal value unit.
- ADD rows have type-specific PM continuation, incremental investment, opportunity-cost, current weight, and campaign evidence.
- NEW rows have opportunity rank / score, buy quality, entry context, market quality, and lot feasibility.
- Position Sizing receives PC authority and converts quantity; it does not own cross-type value comparison.

AO classification:

```text
PHASE32_AO_ADD_NEW_COMMON_VALUE_SCALE = PARTIALLY_COMPARABLE
```

They are comparable enough for current PC capital competition and audit lineage, but not enough to support immediate high-resolution multi-lot ADD without a dedicated common marginal-value design.

## Common-Scale Audit

A future common scale should compare the next executable increment, not the whole symbol:

```text
NEW first lot
vs REENTRY first lot
vs ADD next lot
vs another ADD next lot
vs Cash / optionality
```

Required dimensions should reuse PIT-safe evidence already identified in SoT:

- opportunity rank / score, with calibration metadata preserved;
- buy quality and entry quality;
- PM continuation / campaign state;
- incremental investment value and opportunity-cost state for ADD;
- current weight and remaining headroom;
- concentration and cap constraints;
- market quality and risk pacing;
- Cash optionality;
- lot feasibility and residual capital state.

No historical PnL, future return, MFE/MAE, or fill success may be used to tune the representation.

## One-Lot Position Characterization

Position concentration remains mixed. Through the audited coverage, typical open position count remains around 10, with many one-lot positions. A representative high-count day:

| Date | Open positions | One-lot positions | Median position weight | Top-3 share |
| --- | ---: | ---: | ---: | ---: |
| 2023-09-07 | 19 | 16 | 2.94% | 28.47% |

2023-09-07 shows many one-lot names, but not all one-lot positions are economically tiny. Several 100-share high-price positions had weights above 5%, including `66780` at 12.72%, `46210` at 8.31%, and `73200` at 7.44%. Therefore one-lot posture is a mixture of:

- justified diversification / starter lots;
- high-price one-lot positions that are already meaningful exposure;
- low-price / low-weight residual positions;
- capital-value flattening when many symbols receive similar small weights.

AO classification:

```text
PHASE32_AO_MANY_ONE_LOT_POSTURE = MIXED
```

## Concentration Analysis

Existing guardrails include strategy maximum position weight, Safety concentration cap, cash/no-leverage boundaries, lot feasibility, pending reservation, and explicit Safety gates. These prevent many obvious concentration failures.

However, stronger multi-lot ADD would increase the importance of:

- post-ADD single-name weight;
- campaign-level concentration;
- sector / correlation exposure if available;
- repeated ADD cadence;
- Cash optionality retained after scaling;
- false confirmation during sideways regimes.

AO classification:

```text
PHASE32_AO_EXISTING_GUARDRAILS_FOR_CONCENTRATION = PARTIAL
```

Current guardrails are enough for the observed conservative ADD behavior. They are not yet sufficient proof for unrestricted multi-lot ADD.

## ADD Target-Gap Cohort

Current ADD target-gap cohort:

| Target gap cohort | Rows |
| --- | ---: |
| < 1 lot | 330 |
| 1-2 lots | 4 |
| 2-3 lots | 0 |
| 3+ lots | 0 |

This means existing target-gap fields support the mechanics for reasoning about multi-lot ADD, but the current accepted values do not yet supply a large multi-lot cohort.

AO classification:

```text
PHASE32_AO_EXISTING_TARGET_GAP_SUPPORTS_MULTI_LOT = PARTIAL
```

## Winner Capitalization Evidence

Missed capitalization evidence exists, but it is partial:

- AN identified `94320`, `59550`, and `30410` as decision-time ADD/winner-capitalization examples with strong rank/quality or target/current gaps.
- AO confirms selected ADD rows are all one-lot.
- AO also confirms current accepted ADD gaps are rarely above one executable lot.

Therefore the issue is not proven as a final lot truncation defect. It is better described as a possible missed capitalization design opportunity caused by compressed marginal value / target-gap mapping.

```text
PHASE32_AO_MISSED_CAPITALIZATION_EVIDENCE = PARTIAL
```

## Guardrail Analysis

Multi-lot ADD can be valid only if the future design keeps these guardrails:

- PM ADD remains intent, not automatic order authority.
- PC owns common marginal-value comparison and capital allocation.
- PS owns discrete quantity conversion.
- Runtime only consumes the authorized quantity.
- Safety hard constraints remain binding.
- Cash remains a first-class competitor.
- Each next ADD lot is independently evaluated.
- No averaging-down shortcut is introduced.
- No future outcome or historical return tuning is used.

The design must explicitly preserve the distinction:

```text
high marginal desirability + infeasible
```

versus

```text
low marginal desirability + feasible
```

## Equity Scaling

Order notional partially scales with equity because target weights are portfolio-ratio based. But AN and AO show that target-weight compression and lot granularity dominate much of the observed 100-share behavior.

Equity scaling is therefore a related but separate research problem:

```text
PHASE32_AO_EQUITY_SCALING_SEPARATE_PROBLEM = PARTIAL
```

The immediate design question is not simply "larger account -> larger order". It is whether conviction and marginal capital value should produce larger accepted target gaps before PS applies lot conversion.

## Design-Family Comparison

| Option | Description | AO judgment |
| --- | --- | --- |
| A | Fixed position count / concentrate by count | Reject |
| B | Allow multi-lot ADD when current target gap already supports it | Partial |
| C | Redesign conviction-to-target mapping before PS | Accept as research |
| D | Combine C with next-lot ADD marginal competition | Preferred |
| E | No architecture change | Not preferred |

Option A conflicts with the SoT principle that position count is an output, not a primary fixed rule.

Option B alone is insufficient because current accepted ADD target gaps rarely exceed one lot.

Option C addresses the actual compression stage.

Option D is preferred because it combines conviction-weighted target mapping with independently evaluated ADD next-lot competition.

## Preferred Architecture

Preferred design:

```text
PHASE32_AO_PREFERRED_DESIGN = D
```

Conceptual pipeline:

```text
PIT opportunity / PM / quality / market / cash / risk evidence
-> PC-owned high-resolution marginal capital value object
-> common comparison of NEW first lot, REENTRY first lot, ADD next lot(s), Cash
-> accepted target/incremental allocation with reason lineage
-> PS lot conversion and feasibility
-> Runtime consumption only
```

The design must be shadow-first. It should produce evidence such as:

- marginal opportunity type;
- increment number and pre/post quantity;
- pre/post weight;
- marginal desirability class or structured vector;
- feasibility status;
- strongest competing alternative;
- Cash/optionality disposition;
- concentration/headroom evidence;
- final reason codes;
- future-information and historical-outcome exclusion flags.

## SoT Principles

AO recommends preserving these principles:

- Position count is an output: `ACCEPT`.
- Starter / confirmation / scale: `ACCEPT`.
- Multi-lot ADD as independently evaluated next-lot increments: `ACCEPT`.
- Fixed position count: `REJECT`.
- Runtime-side redecision: `REJECT`.
- Performance-selected thresholds: `REJECT`.
- Cash as residual bookkeeping only: `REJECT`.
- ADD as automatic priority over NEW/Cash: `REJECT`.

## MA200 Note

AN found no current MA200 / 200-day moving-average feature in the scanned production source, config, or latest strategy artifacts. AO did not find evidence requiring an MA200-based design. Existing visible trend evidence remains shorter horizon 5/20 and 20/60 style fields.

No MA200 condition should be introduced from AO.

## Implementation Readiness

Implementation readiness:

```text
PARTIAL
```

Ready:

- architecture owner boundary is known: Portfolio Construction-owned Capital Value Authority;
- evidence families are known and mostly already PIT-safe;
- target/current weight and lot feasibility fields exist;
- ADD next-lot semantics already exist in the future SoT;
- report evidence justifies shadow research.

Not ready:

- no accepted common marginal-value representation yet;
- no accepted mapping from conviction to target/incremental weight;
- no accepted multi-lot ADD cadence or concentration guardrail contract;
- no shadow acceptance thresholds or schemas;
- current accepted ADD gaps do not yet prove a simple multi-lot production activation is safe.

## Recommendation

Current 650BD / long user-operated run should continue. AO found no mandatory defect requiring interruption.

Next step should be a read-only / shadow-only design spec for `conviction_weighted_marginal_capital_value.v1` or equivalent, focused on:

- common marginal-value representation;
- target-gap generation before PS;
- independently evaluated ADD next-lot increments;
- concentration and Cash guardrail observability;
- avoided-loss / lost-winner-control preservation from AM/AL.

No production behavior should change in AO.

## Final Judgments

PHASE32_AO_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AO_COVERAGE_END = 2023-12-19

PHASE32_AO_ONE_LOT_ADD_ORIGIN = CONSERVATIVE_TRANSITIONAL_DESIGN

PHASE32_AO_MULTI_LOT_ADD_ARCHITECTURALLY_VALID = YES

PHASE32_AO_EXISTING_TARGET_GAP_SUPPORTS_MULTI_LOT = PARTIAL

PHASE32_AO_CONVICTION_COMPRESSION_PRIMARY_STAGE = PORTFOLIO_CONSTRUCTION_ACCEPTED_INCREMENTAL_WEIGHT_AND_CAPITAL_VALUE_RESOLUTION_BEFORE_POSITION_SIZING

PHASE32_AO_CONVICTION_TO_TARGET_MAPPING_NEEDS_RESEARCH = YES

PHASE32_AO_ADD_NEW_COMMON_VALUE_SCALE = PARTIALLY_COMPARABLE

PHASE32_AO_MANY_ONE_LOT_POSTURE = MIXED

PHASE32_AO_POSITION_COUNT_AS_OUTPUT_PRINCIPLE = ACCEPT

PHASE32_AO_STARTER_CONFIRMATION_SCALE_PRINCIPLE = ACCEPT

PHASE32_AO_MULTI_LOT_ADD_PRINCIPLE = ACCEPT

PHASE32_AO_EXISTING_GUARDRAILS_FOR_CONCENTRATION = PARTIAL

PHASE32_AO_EQUITY_SCALING_SEPARATE_PROBLEM = PARTIAL

PHASE32_AO_MISSED_CAPITALIZATION_EVIDENCE = PARTIAL

PHASE32_AO_FIXED_POSITION_COUNT_RECOMMENDED = NO

PHASE32_AO_PREFERRED_DESIGN = D

PHASE32_AO_ARCHITECTURE_CHANGE_JUSTIFIED = YES

PHASE32_AO_IMPLEMENTATION_READY = PARTIAL

PHASE32_AO_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_AO_LONG_RUN_CONTINUE = YES

PHASE32_AO_NEXT_STEP = Create a shadow-only common marginal-value / target-gap design spec for conviction-weighted NEW/REENTRY/ADD/Cash competition, with independently evaluated ADD next-lot increments and concentration/Cash guardrail observability; do not change production behavior yet.
