# Phase31-G135 - High-Resolution Marginal Value / Portfolio Rotation Design Readiness Audit

## Final Decision

`G135_CAPITAL_VALUE_AND_ROTATION_ARCHITECTURE_DESIGN_READY`

G135 is a READ-ONLY design readiness audit. It does not implement G136, tune thresholds, change Market Quality / Risk Pacing, alter Strategy behavior, mutate the target run, or use future outcomes as design evidence.

Primary run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Completed immutable artifacts inspected:

`2022-10-03` through `2023-03-13`

Accepted G134 findings were preserved:

- root cause = `MULTI_CAUSAL`
- upstream score/rank differentiation exists
- Stage 2 incremental value / quality bucketing loses resolution
- Stage 4/5 PC/G115 classification loses additional resolution
- ADD / NEW_BUY / Cash do not yet share a common high-resolution marginal-value unit
- unused PIT-safe resolution exists upstream
- current SoT violation = `NO`
- mandatory repair = `NO`

## Executive Judgment

EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_HIGH_RESOLUTION_MARGINAL_VALUE = `PARTIAL`

Existing PIT evidence covers most raw dimensions needed to ask:

```text
What is the value of placing the next executable lot of scarce capital here?
```

The limitation is not raw observability. The limitation is semantic integration. Current artifacts preserve score, rank, entry quality, ADD continuation, expected-edge, opportunity cost, Cash optionality, Risk Pacing, cap, headroom, and lot feasibility, but they do not currently combine those fields into a common high-resolution marginal value unit across NEW_BUY, ADD, Cash, and existing HOLD capital.

HIGH_RESOLUTION_VALUE_REQUIRES_NEW_FEATURES = `PARTIAL`

Most inputs can be reused. New semantics / authority are required, but a new raw feature family is not proven necessary for the first design pass.

NEXT_LOT_MARGINALITY_CAN_BE_DERIVED_FROM_EXISTING_EVIDENCE = `PARTIAL`

Lot feasibility, current weight, one-lot weight, budget, cap, and ADD state are already present. True diminishing next-lot value after each consumed increment is only partial because the current ADD value often reuses same-date campaign / score evidence while staging one increment at a time.

## Source Basis

Reports read and used:

- `docs/phase_reports/phase31_g134_capital_value_resolution_loss_root_cause_localization_audit.md`
- `docs/phase_reports/phase31_g133_bull_internal_opportunity_quality_capital_allocation_behavior_audit.md`
- `docs/phase_reports/phase31_g132_unified_capital_frontier_decision_time_value_quality_characterization.md`
- `docs/phase_reports/phase31_g131_unified_add_new_cash_marginal_capital_authority_design_acceptance.md`
- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- Relevant G112-G128 reports for ADD marginal competition, campaign identity, BUY_ADD materialization, and prior value-resolution findings.

Architecture SoT inspected:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Source inspected read-only:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/add_investment_evidence.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

No future PnL, later return, campaign outcome, MFE/MAE, or selected/bought outcome was used as design-readiness authority.

## Current Artifact Coverage

Target run completed-date scope:

| Metric | Value |
| --- | ---: |
| Completed dates inspected | 109 |
| First completed date | `2022-10-03` |
| Latest completed date | `2023-03-13` |
| Days with PM HOLD and ADD-capable PC rows | 108 |
| Days with Cash competitor evidence and security competitors | 109 |
| Cash competitor status `COMPETITOR_SELECTED` | 109 |
| Cash optionality states | `OPTIONALITY_ELEVATED` 64, `OPTIONALITY_NEUTRAL` 39, `OPTIONALITY_LOW` 6 |

Representative simultaneous evidence:

- `2022-11-29`: PM HOLD positions, PM ADD on `76470`, NEW-style security allocations, Cash competitor, Risk Pacing budget, and lot-aware final reallocation all exist in the same PC artifact.
- `2023-01-31`: BULL dense-candidate / ADD-relevant frontier with PM HOLD positions and Cash competitor evidence.
- `2023-03-07` to `2023-03-13`: high-Cash / cautious deployment evidence with security allocations, PM HOLD, ADD candidate rows, and Cash optionality.

The artifacts are sufficient for design readiness. They are not sufficient to claim the current architecture already has a high-resolution common marginal value authority.

## Marginal-Value Dimension Matrix

| Semantic dimension | Existing producer | Existing fields / artifacts | PIT-safe | Used currently | Resolution | Sufficient for marginal value |
| --- | --- | --- | --- | --- | --- | --- |
| A. Opportunity attractiveness | Candidate / Opportunity / BUY Quality | `runtime_opportunity_score`, rank, `quality_action`, `quality_score`, entry state/action in PC rows | YES | YES | HIGH upstream, MODERATE after PC classing | PARTIAL |
| B. Continuation / durability | PM / Strategy Intelligence / campaign lifecycle | PM action/reasons, continuation state, same-campaign identity, expected-edge state | YES | YES | MODERATE | PARTIAL |
| C. Downside / failure risk | PM / SI / SELL semantic evidence | downside risk, weakening, REDUCE/EXIT evidence, safety references | YES | YES | MODERATE | PARTIAL |
| D. Incremental concentration cost | PC / PS / Safety caps | current weight, target weight, headroom, single-name cap, safety hard cap | YES | YES | MODERATE | PARTIAL |
| E. Remaining position headroom | PC / lot-aware final reallocation / PS | `current_weight`, `target_weight`, `remaining_strategy_headroom`, one-lot weight context | YES | YES | HIGH for feasibility | YES for feasibility, PARTIAL for value |
| F. Market quality | Market Context / Market Quality | market quality state, breadth / recovery / conflicted structure evidence | YES | YES | MODERATE | PARTIAL |
| G. Risk pacing | Portfolio Policy | `incremental_capital_budget_envelope`, risk pacing intent, deployment posture | YES | YES | MODERATE | PARTIAL |
| H. Competing NEW value | Candidate / PC capital competition | same-date NEW frontier, score, rank, construction priority | YES | YES | HIGH as raw ordering | PARTIAL |
| I. Competing ADD value | ADD evidence bridge / PC G115 | PM ADD, incremental investment value, opportunity cost, ADD-vs-ADD frontier | YES | YES | MODERATE | PARTIAL |
| J. Cash optionality | PC market-candidate-cash / Portfolio Policy | Cash competitor, `CASH_PREFERRED`, optionality state, residual Cash reason | YES | YES | MODERATE as participation state | PARTIAL |
| K. Lot / execution feasibility | PC / PS | trading unit, reference price, one-lot weight, projected executable quantity, cap feasibility | YES | YES | HIGH | YES for feasibility, PARTIAL for economic value |
| L. Existing-position marginal saturation | PM / PC / PS | current quantity, ADD history, pre/post increment quantity, current weight, headroom | YES | PARTIAL | LOW to MODERATE | PARTIAL |

## Unused Existing Resolution vs Missing Semantics

EXISTING_BUT_UNDERUSED_DIMENSIONS = `10`

Underused but PIT-safe dimensions:

1. Candidate score and rank remain high-cardinality upstream.
2. BUY Quality score / action / entry state preserve more than PC final classes.
3. PM HOLD / ADD structured reasons distinguish continuation from incremental ADD.
4. ADD opportunity-cost score comparison preserves same-date candidate-vs-best-NEW resolution.
5. ADD-vs-ADD frontier evidence exists after G115/G129.
6. Lot-aware final reallocation preserves executable unit and residual context.
7. Cap / headroom context exists but is mostly treated as constraint, not marginal cost.
8. Cash optionality reason codes distinguish elevated / neutral / low optionality.
9. Market Quality and Risk Pacing distinguish pacing context without mutating ranking.
10. Runtime/PS quantity lineage preserves executable consequences of PC selection.

MISSING_MARGINAL_VALUE_DIMENSIONS = `6`

Missing or only partially represented semantics:

1. Common marginal value unit across NEW_BUY, ADD, Cash, and residual optionality.
2. Cash comparable marginal value, beyond participation / deferral classification.
3. Existing HOLD capital external opportunity cost versus superior NEW / ADD.
4. Portfolio-wide rotation authority that can release deployed capital through PM-safe REDUCE/EXIT semantics.
5. Per-lot diminishing marginal value after prior ADD increments, beyond staged one-increment recomputation.
6. Switching / churn / campaign-disruption cost for replacing an existing HOLD with another opportunity.

## NEW / ADD / Cash / HOLD Boundary Audit

NEW_BUY_VALUE_IS_ALREADY_MARGINAL = `PARTIAL`

NEW_BUY score/rank and BUY Quality are decision-time and useful, but they describe entry opportunity attractiveness. They are not already a full "next executable lot versus ADD / Cash / existing HOLD capital" value object.

CASH_HAS_COMPARABLE_MARGINAL_VALUE_SEMANTIC = `PARTIAL`

Cash is a first-class competitor and may win before candidate failure. However, current Cash evidence is a policy / optionality / participation semantic. It is not a calibrated common marginal value comparable to a specific 100-share NEW or ADD increment.

COMMON_MARGINAL_VALUE_UNIT_FEASIBLE = `YES`

A common unit is feasible because the required PIT inputs already exist in artifacts: opportunity score/rank, quality, continuation, Risk Pacing, Cash optionality, cap/headroom, and lot context. Feasible does not mean already implemented or formula-ready.

HOLD_CAPITAL_HAS_EXTERNAL_OPPORTUNITY_COST = `NO`

Current architecture treats incumbent HOLD capital as existing allocated state. PM can emit HOLD, ADD, REDUCE, or EXIT, and PC can consume those actions. But no active authority was found that compares capital locked in a HOLD position against superior same-date NEW / ADD alternatives and then recommends a PM-safe partial rotation.

PORTFOLIO_ROTATION_AUTHORITY_EXISTS = `PARTIAL`

Adjacent pieces exist:

- REDUCE may conceptually represent partial rotation.
- EXIT may conceptually occur when portfolio replacement by a materially stronger opportunity is justified.
- PC owns marginal allocation of incremental capital.

But there is no complete portfolio-wide rotation authority that turns relative value of HOLD capital vs NEW / ADD / Cash into PM-owned REDUCE/EXIT evidence.

HOLD_NEW_RELATIVE_VALUE_COMPARISON = `NO`

HOLD_ADD_RELATIVE_VALUE_COMPARISON = `NO`

ROTATION_SAFETY_SEMANTICS_AVAILABLE = `PARTIAL`

Safety, PM lifecycle, REDUCE/EXIT, cap/headroom, campaign identity, and lot semantics exist. Missing pieces are the portfolio-wide opportunity-cost proof, switching-cost semantics, and action conversion boundary.

## Current Boundary Finding

The current canonical frontier primarily handles:

```text
available incremental budget
-> NEW / ADD / Cash competition
-> PC allocation
-> PS discrete quantity
-> Runtime planning
```

It does not fully handle:

```text
capital already deployed in HOLD
-> external opportunity-cost comparison
-> PM-safe REDUCE / EXIT / rotation evidence
-> released capital
-> redeployment
```

This is not a bug in the current Phase31 implementation. It is a missing architecture layer for a stricter portfolio-wide rotation design.

## Recommended Responsibility Boundary

HIGH_RESOLUTION_VALUE_RECOMMENDED_OWNER =

`PORTFOLIO_CONSTRUCTION owned Capital Value Authority`

Rationale:

- PC already owns capital allocation and Cash/security competition.
- Candidate AI, BUY Quality, PM, Market Quality, Risk Pacing, Safety, and PS should remain evidence / constraint producers.
- Runtime must remain a consumer and must not re-decide priority.

Recommended artifact:

`canonical_high_resolution_marginal_capital_value.v1`

Recommended status for first implementation:

`SHADOW_NON_AUTHORITATIVE`

PORTFOLIO_ROTATION_RECOMMENDED_OWNER =

`PM action authority plus PC-owned portfolio opportunity-cost evidence`

Rationale:

- PM must remain owner of existing-position directional actions: HOLD / ADD / REDUCE / EXIT.
- PC can produce portfolio-wide external opportunity-cost evidence because it sees NEW / ADD / Cash frontier and capital constraints.
- A later rotation module should not directly sell positions. It should provide evidence that PM can consume to produce REDUCE / EXIT or preserve HOLD.

Recommended artifact:

`canonical_portfolio_rotation_opportunity_cost.v1`

Recommended sequencing:

1. Design high-resolution marginal value first.
2. Validate it as shadow evidence against existing PIT artifacts.
3. Only then design portfolio rotation evidence that consumes the high-resolution value authority.
4. Keep PM as action owner and PS as discrete quantity owner.

## Required Judgments

EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_HIGH_RESOLUTION_MARGINAL_VALUE = `PARTIAL`

HIGH_RESOLUTION_VALUE_REQUIRES_NEW_FEATURES = `PARTIAL`

NEXT_LOT_MARGINALITY_CAN_BE_DERIVED_FROM_EXISTING_EVIDENCE = `PARTIAL`

NEW_BUY_VALUE_IS_ALREADY_MARGINAL = `PARTIAL`

CASH_HAS_COMPARABLE_MARGINAL_VALUE_SEMANTIC = `PARTIAL`

COMMON_MARGINAL_VALUE_UNIT_FEASIBLE = `YES`

HOLD_CAPITAL_HAS_EXTERNAL_OPPORTUNITY_COST = `NO`

PORTFOLIO_ROTATION_AUTHORITY_EXISTS = `PARTIAL`

HOLD_NEW_RELATIVE_VALUE_COMPARISON = `NO`

HOLD_ADD_RELATIVE_VALUE_COMPARISON = `NO`

ROTATION_SAFETY_SEMANTICS_AVAILABLE = `PARTIAL`

HIGH_RESOLUTION_VALUE_REQUIRES_NEW_MODULE = `YES`

PORTFOLIO_ROTATION_REQUIRES_NEW_MODULE = `YES`

PORTFOLIO_ROTATION_DEPENDS_ON_HIGH_RESOLUTION_VALUE = `YES`

HIGH_RESOLUTION_VALUE_ADDRESSES_CONFIRMED_BULL_LIMITATION = `YES`

BULL_RETURN_IMPROVEMENT_GUARANTEED = `NO`

CAPITAL_VALUE_ROOT_CAUSE_RESEARCH_COMPLETE = `YES`

NEXT_PHASE_ARCHITECTURE_DESIGN_READY = `YES`

MANDATORY_REPAIR_FOUND = `NO`

FUTURE_INFORMATION_USED_FOR_DESIGN_READINESS_JUDGMENT = `NO`

## Design Readiness Conclusion

G135 finds enough PIT-safe evidence to begin the next architecture design, but not enough to declare the current architecture already sufficient.

The next design should not be framed as a repair to G134. It should be a new Phase31 continuation architecture design for:

```text
canonical_high_resolution_marginal_capital_value.v1
```

followed by:

```text
canonical_portfolio_rotation_opportunity_cost.v1
```

The high-resolution value authority should reuse existing PIT evidence first, preserve all current owners, remain shadow initially, and avoid performance-derived weights or thresholds. Portfolio rotation should depend on that value authority and must preserve PM ownership of REDUCE / EXIT decisions.

## Validation Flags

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

THRESHOLD_CHANGED = `NO`

WEIGHT_CHANGED = `NO`

MODEL_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

GIT_DIFF_CHECK = `PASS`
