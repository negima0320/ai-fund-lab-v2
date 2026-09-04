# Phase32-FF - CAUTIOUS / GRADUAL Marginal-Capital Quality Discrimination READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit period: `2023-03-01` through `2023-05-08`
- Focus dates: `2023-03-22`, `2023-03-24` to `2023-03-27`, `2023-04-10` to `2023-04-13`, `2023-04-21` to `2023-05-08`
- Evidence used: target-run Portfolio Construction, Market Context, Buy Quality, technical feature, Strategy Intelligence, PM, fills, and current valuation artifacts; Phase32-FD/FE/FC reports; current Risk Pacing / Market-Candidate-Cash Architecture SoT; current BUY Quality / Entry / PC / MCV implementation.
- Production changed: NO
- SHADOW changed: NO
- Config/schema changed: NO
- Target run mutated: NO
- Runtime state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Future return/PnL/MFE/MAE used for Production judgment: NO

## Executive Summary

The current artifacts contain enough same-date PIT evidence to distinguish materially different `COMPARABLE_MARGINAL` candidates. Within the same canonical class, momentum, tick-normalized trend, confidence, 20-day price momentum, entry state, BQ state, relative strength, lot feasibility, and cash-competition context vary materially.

However, actual CAUTIOUS/GRADUAL deployment still allows many `COMPARABLE_MARGINAL` rows to receive positive PC weight and BUY fills. The most important boundary is not candidate admission or BQ. It is the compression from canonical opportunity quality into legacy MCV comparison class, then the Risk Pacing production gate using only:

```text
ELIGIBLE_STRONG or ELIGIBLE_COMPARABLE => sufficient
```

That means `COMPARABLE_MARGINAL` becomes `ELIGIBLE_COMPARABLE`, and `ELIGIBLE_COMPARABLE` is sufficient for both `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`.

Cash competitor evidence is present and often explicitly says `COMPARABLE_MARGINAL` lost to Cash. But final positive allocations/fills still occur for many of those rows, through the participation/lot-aware allocation path. This is not a data readiness or Runtime correctness defect; it is a design-level semantic gap between the intended cautious/gradual meaning and the effective production deployment binding.

Selected judgment: `H. MIXED`, with primary cause `C. MARGINAL_EVIDENCE_INFORMATION_LOSS_DESIGN_REFINEMENT_JUSTIFIED` and secondary cause `D. CASH_COMPETITOR_SEMANTIC_GAP`.

## COMPARABLE_MARGINAL Population

Population reconstructed from PC members whose Risk Pacing intent was `CAUTIOUS_DEPLOYMENT` or `GRADUAL_REDEPLOYMENT` and whose canonical opportunity quality was `COMPARABLE_MARGINAL`.

| Intent | Population | PC Selected | BUY Fill | Fill Notional |
| --- | ---: | ---: | ---: | ---: |
| `CAUTIOUS_DEPLOYMENT` | 353 | 168 | 36 | 2,839,530 |
| `GRADUAL_REDEPLOYMENT` | 165 | 72 | 12 | 1,351,330 |
| Total | 518 | 240 | 48 | 4,190,860 |

Stage interpretation:

- Candidate present in PC: 518.
- BQ pass/valid: 518; nearly all are `REDUCED_ALLOCATION_ONLY`.
- Entry pass/valid: 518; all are `CONTINUATION_WITH_CAUTION`.
- PC selected with positive accepted weight: 240.
- Actual BUY fill: 48.
- Cash interaction says `CASH_PREFERRED`: 125 rows.
- `CASH_PREFERRED` rows that still had positive selected weight: 125 rows.
- `CASH_PREFERRED` rows that still produced BUY fills: 48 rows.

This confirms the FE observation: CAUTIOUS/GRADUAL recapitlization is not caused by weak or invalid candidates. It is caused by valid-but-marginal candidates being allowed to participate positively despite cash-preferred interaction evidence.

## Existing PIT Evidence Inventory

Observed same-date evidence fields available for `COMPARABLE_MARGINAL` discrimination:

- Market/risk context: `regime_state`, `market_quality_state`, `breadth_state`, `breadth_value`, `volatility_regime`, `risk_pacing_intent`, `deployment_capacity_semantic`, target gross, cash reserve.
- Candidate/score evidence: `input_score`, `runtime_opportunity_score`, `input_opportunity_rank`, `opportunity_buy_rank`, `construction_priority`, `confidence`.
- BQ evidence: `quality_action`, `quality_band`, `quality_score`, `quality_reason_codes`, BQ component scores/statuses.
- Entry evidence: `entry_admission_state`, `entry_admission_action`, `entry_admission_evidence_sufficiency`.
- Momentum/trend evidence: `momentum_trajectory_classification`, `momentum_trajectory_component_score`, `momentum_confidence_state`, `tick_normalized_trend_state`, `trend_close_over_ma_20d`, `price_momentum_return_20d`, technical feature rows.
- Fragility/downside evidence: `strategy_intelligence_downside_risk_status`, `close_level_diversity_state`, tick quantization/low-price confidence.
- PC/MCV evidence: `canonical_opportunity_quality_class`, `marginal_capital_value_class`, `canonical_marginal_capital_priority_index`, `marginal_capital_value_authority`, `risk_pacing_competition_decision`.
- Cash evidence: `canonical_cash_competitor_evidence`, `market_candidate_cash_interaction`, `cash_preference_semantic`, `cash_preferred_security_deferrals`, `authorized_cash_allocation`.
- ADD-specific evidence: `strategy_intelligence_add_worthiness_state`, `strategy_intelligence_continuation_quality_status`, `strategy_intelligence_downside_risk_status`, `strategy_intelligence_relative_strength_state`, campaign/headroom evidence.

No future outcome fields were used.

## Evidence Variance Within COMPARABLE_MARGINAL

### CAUTIOUS

| Field | Min | Q25 | Median | Q75 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `quality_score` | 0.461854 | 0.535802 | 0.589170 | 0.657142 | 0.805297 |
| `input_score` / `runtime_opportunity_score` | -0.561058 | -0.449285 | -0.382420 | -0.251570 | 0.319212 |
| `momentum_trajectory_component_score` | 0.500000 | 0.500000 | 0.500000 | 1.000000 | 1.000000 |
| `trend_close_over_ma_20d` | 0.677966 | 0.963265 | 1.019858 | 1.112264 | 1.883489 |
| `price_momentum_return_20d` | -0.560850 | -0.014925 | 0.136430 | 0.500000 | 3.087719 |

Categorical variance:

- Momentum: 90 `HEALTHY_CONTINUATION`, 263 `MIXED_OR_UNRESOLVED`.
- Tick trend: 162 `ROBUST`, 155 `ACCEPTABLE`, 36 `QUANTIZED_CAUTION`.
- Momentum confidence: 164 `HIGH_CONFIDENCE`, 153 `MODERATE_CONFIDENCE`, 36 `LOW_CONFIDENCE_QUANTIZED`.

### GRADUAL

| Field | Min | Q25 | Median | Q75 | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| `quality_score` | 0.483528 | 0.533783 | 0.576627 | 0.632189 | 0.788048 |
| `input_score` / `runtime_opportunity_score` | -0.582340 | -0.490870 | -0.452081 | -0.353561 | 0.167973 |
| `momentum_trajectory_component_score` | 0.500000 | 0.500000 | 0.500000 | 0.500000 | 1.000000 |
| `trend_close_over_ma_20d` | 0.826122 | 0.959660 | 1.011236 | 1.093649 | 1.824908 |
| `price_momentum_return_20d` | -0.366864 | 0.000000 | 0.123556 | 0.380023 | 2.082960 |

Categorical variance:

- Momentum: 34 `HEALTHY_CONTINUATION`, 131 `MIXED_OR_UNRESOLVED`.
- Tick trend: 68 `ROBUST`, 88 `ACCEPTABLE`, 9 `QUANTIZED_CAUTION`.
- Momentum confidence: 87 `HIGH_CONFIDENCE`, 69 `MODERATE_CONFIDENCE`, 9 `LOW_CONFIDENCE_QUANTIZED`.

Conclusion:

`MARGINAL_EVIDENCE_VARIANCE_EXISTS = YES`

The class is not homogeneous. The current evidence can separate stronger, ordinary, and fragile/unconfirmed variants without using future outcomes.

## Stronger-Within-Marginal Identification

A threshold-free separation is feasible from existing PIT evidence:

- Stronger-current-confirmation candidates: `COMPARABLE_MARGINAL` rows with healthy momentum continuation, robust tick-normalized trend, high confidence, supportive relative strength, clean downside, and credible same-day priority evidence.
- Ordinary marginal candidates: valid reduced-allocation candidates with continuation caution and mixed/unresolved momentum, but no hard fragility.
- Fragile/unconfirmed marginal candidates: valid but caution-heavy rows with `MIXED_OR_UNRESOLVED`, `ACCEPTABLE` or `QUANTIZED_CAUTION`, weak/insufficient same-day relative support, or Cash-preferred aggregate deferral evidence.

No new Production threshold is selected here. The audit only confirms separability.

`STRONGER_WITHIN_MARGINAL_IDENTIFIABLE_FROM_PIT = YES`

## Recovery / Re-Acceleration Evidence

Existing evidence includes:

- `momentum_trajectory_classification`
- `momentum_trajectory_component_score`
- `momentum_confidence_state`
- `tick_normalized_trend_state`
- `trend_close_over_ma_20d`
- `price_momentum_return_20d`
- `breadth_state` / `breadth_value`
- `market_quality_state`
- `entry_admission_state`
- `selection_quality_tier`
- `relative_strength_state`

But it does not yet expose a single canonical "risk-off recovery re-acceleration confirmation" authority that binds candidate-level deployment against Cash during CAUTIOUS/GRADUAL.

`RECOVERY_REACCELERATION_EVIDENCE_EXISTS = PARTIAL`

The raw ingredients exist; the binding concept is incomplete.

## 2023-04-11 Six BUY_NEW Deep Dive

Context:

- Regime: `CORRECTION`
- Market quality: `SHORT_TERM_BREADTH_BREAKDOWN`
- Breadth: `NEUTRAL`
- Risk intent: `CAUTIOUS_DEPLOYMENT`
- Target gross: 0.90
- Cash reserve: 0.10
- Exposure moved toward 79.9%
- BUY_NEW fills: 6
- Added notional: 323,630

| Symbol | Notional | Opportunity Quality | MCV | PC Priority | Entry | BQ | Momentum | Tick | Ret20 | Cash Interaction |
| --- | ---: | --- | --- | ---: | --- | --- | --- | --- | ---: | --- |
| `27210` | 43,500 | COMPARABLE_HIGH | ELIGIBLE_STRONG | 1 | HEALTHY_CONTINUATION_ENTRY | REDUCED_ALLOCATION_ONLY | HEALTHY_CONTINUATION / 1.0 | ROBUST | 0.396 | CASH_PREFERRED |
| `45980` | 130,800 | COMPARABLE_HIGH | ELIGIBLE_STRONG | 2 | HEALTHY_CONTINUATION_ENTRY | REDUCED_ALLOCATION_ONLY | HEALTHY_CONTINUATION / 1.0 | ROBUST | 0.095 | CASH_PREFERRED |
| `94340` | 30,060 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 3 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | MIXED_OR_UNRESOLVED / 0.5 | ACCEPTABLE | -0.023 | CASH_PREFERRED |
| `54010` | 59,900 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 4 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | MIXED_OR_UNRESOLVED / 0.5 | ACCEPTABLE | -0.064 | CASH_PREFERRED |
| `45860` | 33,400 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 6 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | MIXED_OR_UNRESOLVED / 0.5 | ROBUST | 0.111 | CASH_PREFERRED |
| `44920` | 25,970 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 9 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | MIXED_OR_UNRESOLVED / 0.5 | ROBUST | 0.591 | CASH_PREFERRED |

Answer:

`2023_04_11_ALL_BUYS_STRONGLY_CONFIRMED = NO`

Two rows had strong current confirmation. Four rows were valid but marginal/cautionary, and their Cash interaction evidence explicitly preferred Cash.

## 2023-03-22 Deep Dive

Context:

- Regime: `RANGE`
- Market quality: `CONFLICTED_MARKET_STRUCTURE`
- Breadth: `NEUTRAL`
- Risk intent: `CAUTIOUS_DEPLOYMENT`
- BUY_NEW fills: 3
- Added notional: 308,500

| Symbol | Notional | Opportunity Quality | MCV | PC Priority | Entry | BQ | Momentum | Tick | Ret20 | Cash Interaction |
| --- | ---: | --- | --- | ---: | --- | --- | --- | --- | ---: | --- |
| `67750` | 24,300 | STRONG | ELIGIBLE_STRONG | 1 | HEALTHY_CONTINUATION_ENTRY | REDUCED_ALLOCATION_ONLY | HEALTHY_CONTINUATION / 1.0 | ROBUST | 0.384 | SELECTIVE_COMPETITION |
| `43880` | 119,200 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 2 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | MIXED_OR_UNRESOLVED / 0.5 | ROBUST | 1.002 | CASH_PREFERRED |
| `64240` | 165,000 | COMPARABLE_MARGINAL | ELIGIBLE_COMPARABLE | 7 | CONTINUATION_WITH_CAUTION | REDUCED_ALLOCATION_ONLY | HEALTHY_CONTINUATION / 1.0 | ROBUST | 0.964 | CASH_PREFERRED |

`2023_03_22_SAME_PACING_BOUNDARY_REPRODUCED = YES`

This is the same boundary as 4/11: at least one strong/selective row is present, but additional COMPARABLE_MARGINAL rows also receive positive allocation/fill despite Cash-preferred interaction.

## GRADUAL_REDEPLOYMENT Deep Dive

### 2023-03-27

- Market quality: `RECOVERY_CONFIRMATION_INCOMPLETE`
- Risk intent: `GRADUAL_REDEPLOYMENT`
- BUY_NEW fill: `57810`, 178,400
- Opportunity quality: `COMPARABLE_MARGINAL`
- Momentum: `MIXED_OR_UNRESOLVED`
- Cash interaction: `CASH_PREFERRED`

### 2023-04-24

- Market quality: `RECOVERY_CONFIRMATION_INCOMPLETE`
- Risk intent: `GRADUAL_REDEPLOYMENT`
- BUY_NEW fills: 4, notional 304,000
- One `STRONG` row: `69270`
- Three `COMPARABLE_MARGINAL` rows: `45860`, `77930`, `60160`
- COMPARABLE_MARGINAL rows had `CASH_PREFERRED` interaction.

### 2023-05-01

- Market quality: `RECOVERY_CONFIRMATION_INCOMPLETE`
- Risk intent: `GRADUAL_REDEPLOYMENT`
- BUY_NEW fills: `69270` and `67310`, total 370,400
- Both were `COMPARABLE_MARGINAL`
- Cash interaction: `CASH_PREFERRED`
- Cash competitor was `OPTIONALITY_ELEVATED`.

`GRADUAL_SEMANTICS_MATCH_ACTUAL_INTENSITY = PARTIAL`

The label and SoT imply selective redeployment through confirmed competitors. Actual deployment often includes marginal/cautionary rows that Cash interaction says should prefer Cash, so the effective intensity is more aggressive than the semantic name suggests.

## Cash Competitor Semantics

Cash evidence is present:

- `canonical_cash_competitor_evidence` exists.
- `cash_preference_semantic` becomes `OPTIONALITY_ELEVATED` in weak/recovery-incomplete contexts.
- `market_candidate_cash_interaction` consumes risk pacing, cash evidence, and opportunity quality.
- Examples show `CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED`, `GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED`, and `*_MARGINAL_LOST_TO_CASH`.

But final effectiveness is partial:

- 125 `COMPARABLE_MARGINAL` rows had `CASH_PREFERRED` interaction and still had positive PC selected weight.
- 48 `COMPARABLE_MARGINAL` rows had `CASH_PREFERRED` interaction and still produced BUY fills.
- Some artifacts also show canonical deployment set / multi-allocation evidence preserving Cash, but the production fill path still follows positive accepted member weights.

Interpretation:

`CASH_PREFERRED` is not supposed to be an automatic hard zero after Phase31-G81/G86/G90, so this is not a simple contract breach. But the reduced participation resolver appears too permissive for CAUTIOUS/GRADUAL marginal rows, and Cash is not strong enough as a final binding competitor in the observed actual path.

`CASH_COMPETITOR_EFFECTIVE = PARTIAL`

`CASH_COMPETITOR_TOO_WEAK = YES_AT_FINAL_PRODUCTION_BINDING`

## COMPARABLE_HIGH vs COMPARABLE_MARGINAL Reference Graph

```text
BUY Quality / Entry / technical / SI current PIT evidence
  -> MCV canonical opportunity quality
       STRONG
       COMPARABLE_HIGH
       COMPARABLE_MARGINAL
       WEAK_VALID
       BLOCKED / INSUFFICIENT
  -> MCV legacy comparison class
       STRONG + COMPARABLE_HIGH -> ELIGIBLE_STRONG
       COMPARABLE_MARGINAL + WEAK_VALID -> ELIGIBLE_COMPARABLE
  -> PC member evidence
       canonical_opportunity_quality_class preserved in marginal_capital_value_authority
       marginal_capital_value_class = ELIGIBLE_COMPARABLE
  -> risk_pacing_competitor_decision
       sufficient = ELIGIBLE_STRONG or ELIGIBLE_COMPARABLE
  -> accepted PC weights / lot-aware reallocations
  -> Position Sizing / Runtime BUY fills
```

Source references:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`: canonical classes are defined separately; `COMPARABLE_MARGINAL` maps to `ELIGIBLE_COMPARABLE` in compatibility comparison class.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: Risk Pacing decision treats `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE` as sufficient for CAUTIOUS/GRADUAL.
- Architecture SoT: `COMPARABLE_MARGINAL` means valid but close enough to Cash optionality that market weakness can make Cash preferable.

Judgment:

- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_EXISTS_UPSTREAM = YES`
- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_PRESERVED_IN_PC = YES_AS_EVIDENCE`
- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_PRESERVED_IN_MCV = PARTIAL`
- `MATERIAL_DECISION_INFORMATION_LOSS = YES_AT_EFFECTIVE_RISK_PACING_BINDING`

The distinction is not fully lost from artifacts, but it is materially compressed for the effective deployment gate.

## ADD Comparison

ADD shares the same concern, though the observed ramp is BUY_NEW-driven.

Within CAUTIOUS/GRADUAL and `COMPARABLE_MARGINAL`:

- ADD comparable-marginal rows: 5.
- Selected ADD rows: 5.
- Filled ADD rows: 2.
- Filled ADD notional: 208,700.
- Both filled ADD rows were under `CAUTIOUS_DEPLOYMENT`.
- Both filled ADD rows had `CASH_PREFERRED` interaction and `CAUTIOUS_MARGINAL_LOST_TO_CASH`.

Examples:

- `2023-03-30` `43880` BUY_ADD 122,900, ADD reduced-only, continuation PASS, downside PASS, relative strength MIXED, Cash preferred.
- `2023-04-04` `83060` BUY_ADD 85,800, ADD reduced-only, continuation PASS, downside PASS, relative strength MIXED, Cash preferred.

`BUY_ADD_HAS_SAME_PACING_CONCERN = YES_BUT_SMALLER_SAMPLE`

Future design should be common to BUY_NEW and ADD where possible. BUY_NEW is larger in notional, but the semantic boundary is shared.

## Candidate-Level Pacing vs Exposure Ceiling

Architecture-consistent options:

| Option | Assessment |
| --- | --- |
| Fixed multi-day cooldown | Not necessary yet. It risks delaying genuine recovery and would introduce a coarse calendar rule. |
| Fixed daily exposure ramp ceiling | Not necessary yet. It may be useful as a portfolio-level guard, but it is less aligned with the existing opportunity-first design. |
| Candidate-level stronger evidence requirement | Most aligned. Existing PIT evidence can separate stronger marginal rows from fragile/unconfirmed marginal rows without future outcomes. |
| Stronger Cash competitor | Also aligned. Cash already exists as first-class competitor, but the final binding/participation resolver should better preserve Cash preference during CAUTIOUS/GRADUAL. |
| Combination | Best candidate for design study: candidate-level confirmation plus stronger Cash final binding, without fixed performance-tuned thresholds. |

`CANDIDATE_LEVEL_EVIDENCE_PACING_FEASIBLE = YES`

`FIXED_COOLDOWN_NECESSARY = NO`

`FIXED_EXPOSURE_RAMP_CEILING_NECESSARY = NO_NOT_YET`

## Production Design Necessity

Classification:

- `CURRENT_SEMANTICS_SUFFICIENT = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NOT_YET`
- `MORE_EVIDENCE_REQUIRED = NO_FOR_DESIGN_REFINEMENT / YES_FOR_PRODUCTION_PARAMETERIZATION`

Rationale:

- Material PIT evidence differences exist inside `COMPARABLE_MARGINAL`.
- That difference is preserved in artifacts but compressed before the effective Risk Pacing decision.
- CAUTIOUS/GRADUAL rows can receive positive allocation/fill even when Cash interaction says Cash is preferred.
- This is repeatable across 3/22, 4/11, 3/27, 4/24, and 5/01.
- No future return/PnL is needed to identify the semantic gap.
- No Production change should be implemented in FF; a design phase should define a non-tuned, PIT-only binding refinement.

## Required Answers

- `CAUTIOUS_MARGINAL_POPULATION = 353`
- `GRADUAL_MARGINAL_POPULATION = 165`
- `MARGINAL_EVIDENCE_VARIANCE_EXISTS = YES`
- `STRONGER_WITHIN_MARGINAL_IDENTIFIABLE_FROM_PIT = YES`
- `RECOVERY_REACCELERATION_EVIDENCE_EXISTS = PARTIAL`
- `2023_04_11_ALL_BUYS_STRONGLY_CONFIRMED = NO`
- `2023_03_22_SAME_PACING_BOUNDARY_REPRODUCED = YES`
- `GRADUAL_SEMANTICS_MATCH_ACTUAL_INTENSITY = PARTIAL`
- `CASH_COMPETITOR_EFFECTIVE = PARTIAL`
- `CASH_COMPETITOR_TOO_WEAK = YES_AT_FINAL_PRODUCTION_BINDING`
- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_EXISTS_UPSTREAM = YES`
- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_PRESERVED_IN_PC = YES_AS_EVIDENCE`
- `COMPARABLE_HIGH_MARGINAL_DISTINCTION_PRESERVED_IN_MCV = PARTIAL_CANONICAL_CLASS_PRESERVED_BUT_LEGACY_COMPARISON_COMPRESSES`
- `MATERIAL_DECISION_INFORMATION_LOSS = YES_AT_EFFECTIVE_RISK_PACING_BINDING`
- `BUY_ADD_HAS_SAME_PACING_CONCERN = YES_BUT_SMALLER_SAMPLE`
- `CANDIDATE_LEVEL_EVIDENCE_PACING_FEASIBLE = YES`
- `FIXED_COOLDOWN_NECESSARY = NO`
- `FIXED_EXPOSURE_RAMP_CEILING_NECESSARY = NO_NOT_YET`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NOT_YET`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Judgment

Selected classification:

`H. MIXED`

Primary component:

`C. MARGINAL_EVIDENCE_INFORMATION_LOSS_DESIGN_REFINEMENT_JUSTIFIED`

Secondary component:

`D. CASH_COMPETITOR_SEMANTIC_GAP`

The evidence supports a design refinement, not an immediate Production repair in this READ-ONLY phase.

## Final Judgment

`PHASE32_FF_MARGINAL_EVIDENCE_INFORMATION_LOSS_AND_CASH_COMPETITOR_BINDING_GAP_FOUND_DESIGN_REFINEMENT_JUSTIFIED_PRODUCTION_REPAIR_NOT_YET_LONG_HORIZON_SAFE_TO_CONTINUE`
