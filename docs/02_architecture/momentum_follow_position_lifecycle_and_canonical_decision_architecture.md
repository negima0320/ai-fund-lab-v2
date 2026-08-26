# Momentum Follow Position Lifecycle and Canonical Decision Architecture

## 1. Status

This document is the Phase27-D1 design source of truth for Momentum Follow / Momentum Rotation position lifecycle and canonical decision architecture.

- Phase: Phase27
- Task ID: Phase27-D1
- Primary judgment: `PHASE27_D1_MOMENTUM_FOLLOW_CANONICAL_DECISION_DESIGN_COMPLETE_WITH_OPEN_GATES`
- Implementation changed: `false`
- Historical execution: `PROHIBITED_NOT_EXECUTED`

The design is complete enough to guide implementation, but entry is step-gated: BUY_ADD authority repair and targeted contract proof must happen before performance experiments or long historical validation.

## 2. Evidence Base

This design reflects Phase27-A1 through A9, Phase27-AR1, Phase26 closure, and the architecture SoT documents listed below.

- docs/phase_reports/phase27_a1_100bd_evidence_inventory_and_attribution_readiness_audit.md
- docs/phase_reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction.md
- docs/phase_reports/phase27_a3_reentry_causality_and_selection_validity_diagnosis.md
- docs/phase_reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis.md
- docs/phase_reports/phase27_a5_higher_ranked_candidate_ineligibility_and_quality_component_diagnosis.md
- docs/phase_reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis.md
- docs/phase_reports/phase27_a7_existing_position_position_management_decision_authority_audit.md
- docs/phase_reports/phase27_a8_add_authority_contract_review.md
- docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md
- docs/phase_reports/phase27_ar1_phase27a_review_pack.md
- docs/phase_reports/phase26_k_final_architecture_conformance_responsibility_fulfillment_and_closure_review.md
- docs/phase_reports/phase26_l_final_closure_consolidation_and_phase27_execution_handoff.md
- docs/phase_reports/phase26_final_summary_and_phase27_handoff.md
- docs/phase_reports/phase26_to_phase27_chatgpt_handoff.md
- docs/02_architecture/autonomous_ai_operations_architecture.md
- docs/02_architecture/strategy_architecture_v1.md
- docs/02_architecture/runtime_architecture_v2.md
- docs/02_architecture/adaptive_buy_quality_authority.md
- docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
- docs/01_requirements/phase_roadmap.md

Key facts carried forward:

- No forced BUY count observed.
- No fixed slot-fill behavior observed.
- No forced cash deployment observed.
- No-BUY and cash retention are valid Strategy results.
- Clear disregard of stronger executable candidates was not observed.
- Re-entry losses were material, but Re-entry alone was not proven as root cause.
- Higher-ranked candidate dropout was dominated by existing-holding zero-delta cases.
- 7 of 25 BUYs were WEAK or RELATIVE_ONLY under incremental eligibility diagnosis.
- BUY Quality is allocation eligibility/scaling authority, not explicit BUY-versus-cash authority.
- PM emitted ADD/HOLD/REDUCE/EXIT, including 145 ADD decisions.
- Executable BUY_ADD was not observed.
- Runtime PM ADD did not resolve into canonical Portfolio Construction in the observed run.
- Legacy add_consumer/sell_pipeline ADD path remains active.
- Canonical BUY_ADD authority and legacy ADD authority are split.

## 3. Investment Philosophy

AI Fund Lab v2 is designed for Momentum Follow / Momentum Rotation with a long-term annual return goal of +50%. The starting capital assumption is 1,000,000 JPY and the posture is aggressive/high-risk, but this does not disable Safety, force full deployment, introduce a fixed cash ratio, permit unlimited concentration, reject loss cuts, or weaken architecture integrity.

The lifecycle philosophy is:

- Enter symbols with strong forward-looking opportunity evidence.
- Hold while momentum continuation remains valid.
- Add only when continuation/strengthening and incremental investment eligibility are sufficient.
- Reduce when momentum weakens or exposure should be trimmed.
- Exit when momentum or expected edge materially deteriorates.
- Rotate capital to materially stronger opportunities within portfolio and safety constraints.

Profit alone is not an EXIT reason. EXIT must be justified by momentum failure, opportunity deterioration, signal reliability deterioration, materially stronger replacement, risk deterioration, or Safety. Fast loss control remains required; repeated Exit -> 1BD BUY_NEW must be explainable through evidence and diagnosed as possible whipsaw after the fact.

Cash is residual. High cash is neither automatically success nor automatically failure.

## 3.1 Phase27-D3 PM Performance Philosophy Freeze

Phase27-D3 freezes the Position Management performance philosophy as common SoT for AI Fund Lab v2. This is a design and documentation freeze only; it does not change PM logic, Strategy logic, Runtime, Safety, Submit, Execution, Position Sizing, Opportunity, Quality, Market Context, or Portfolio Construction.

Position Management is the single Strategy Action Authority for existing-position directional decisions:

```text
BUY_NEW / ADD / HOLD / REDUCE / EXIT
```

Other components may generate evidence, constraints, candidates, scores, rankings, modifiers, or quantities, but they must not independently produce BUY/HOLD/SELL action decisions.

Core performance principles:

- Do not sell merely because profit exists.
- HOLD while the upward trend and expected value remain valid.
- EXIT only when upward trend continuation fails, expected value deteriorates, signal structure breaks, or risk/Safety materially worsens.
- ADD is not fallback buying because no new candidate exists; ADD is considered only when the held symbol remains a strongest opportunity and incremental value exists.
- REDUCE is a risk/weakening/partial-rotation tool, not a profit-taking philosophy.
- Cash is an outcome of opportunity, quality, risk, sizing, and safety evidence; cash is not a target to force away.
- The 1,000,000 JPY starting capital assumption is expectation-maximization capital, not a fixed full-deployment mandate.
- Performance improvement must not add another action authority.

Action philosophy:

| Action | PM philosophy | Explicit non-goal |
|---|---|---|
| `BUY_NEW` | Enter a no-position symbol that is entering an upward trend or has sufficient forward expected value. | Do not buy merely because rank is high or cash exists. |
| `HOLD` | Actively continue an open campaign while continuation evidence remains valid. | HOLD is not "nothing happened" and profit alone does not cancel HOLD. |
| `ADD` | Consider increasing an existing position only when it is still among the strongest opportunities, trend continues, and incremental value exists. | Do not ADD because no new candidate is available. |
| `REDUCE` | Preserve campaign optionality while reducing exposure when weakening, risk, concentration, or partial rotation evidence supports it. | Do not REDUCE as simple profit taking. |
| `EXIT` | Close a campaign when continuation is broken, expected value deteriorates, signals invalidate, or risk/Safety requires full close. | Do not EXIT only because a profit is available. |

Minimum ADD philosophy, without numeric thresholds:

```text
Still Rank1 or materially strongest among available opportunities
AND Trend Continuing
AND Incremental Value Exists
AND portfolio/risk/safety feasibility remains acceptable
```

Phase27-D3 does not decide numeric definitions for Still Rank1, Trend Continuing, Incremental Value, Weakening, Broken, or REDUCE/EXIT boundaries. Those remain open design questions for controlled PM improvement review.

## 3.2 Evidence Producer vs Action Producer

Evidence producers support PM but do not replace PM:

| Component | Evaluates | Does not decide |
|---|---|---|
| Opportunity | Relative and absolute expected-edge evidence and rank. | BUY, ADD, HOLD, REDUCE, EXIT. |
| BUY Quality | Allocation eligibility, reliability, and scaling evidence. | BUY-versus-cash or SELL action. |
| Market Context | Market regime, breadth, volatility, and posture evidence. | Symbol-level action. |
| Momentum Evidence | Continuation, weakening, broken-state evidence. | Final action unless explicitly integrated as PM input. |
| Incremental Eligibility | Whether additional capital is justified now. | Direct BUY_NEW or ADD order authority. |
| Portfolio Construction | Target portfolio membership and target weight resolution after consuming PM/evidence. | Broker quantity, PM action, Submit authorization. |
| Position Sizing | Target quantity and quantity delta. | PM action or action reason. |
| Runtime Planning | Quantity-delta-to-runtime-action mapping. | Strategy judgment, ranking, PM decision, target weight, sizing formula. |

PM may consume these evidence products. If a future Momentum Evidence artifact is added, the preferred authority mode is evidence-only or PM-input evidence. A separate action-producing Momentum component is rejected unless a later common SoT revision strongly proves it is unavoidable.

## 3.3 Phase27-D4 Expected Edge Decision Contract

Phase27-D4 freezes Expected Edge as the PM decision concept for AI Fund Lab v2. The PM must be understood as an AI that integrates Point-in-Time evidence to estimate forward-looking Expected Edge, not as an AI that mechanically follows Trend, Rank, Quality, current profit, or cash.

Expected Edge answers:

```text
Is the forward-looking expected value still sufficiently attractive?
```

It is not:

```text
profit rate alone
trend alone
rank alone
quality score alone
market context alone
cash availability
```

Expected Edge is supported by evidence:

| Evidence | Relationship to Expected Edge | Action boundary |
|---|---|---|
| Trend / Momentum | Evidence of continuation, weakening, or break. | Does not alone decide HOLD/ADD/REDUCE/EXIT. |
| Opportunity | Relative and absolute expected-edge evidence, including rank. | Rank alone is not BUY/ADD/EXIT. |
| BUY Quality | Reliability, eligibility, and scaling evidence. | Quality alone is not Action Authority. |
| Market Context | Regime, breadth, volatility, and risk posture evidence. | Does not mechanically override symbol-level PM. |
| Portfolio Fit | Concentration, exposure, replacement, and compatibility evidence. | Does not create Action outside PM/Portfolio Construction contract. |
| Execution Feasibility | Orderability, lot, liquidity, and operational feasibility evidence. | Feasibility is not investment desirability. |
| Profit / Unrealized PnL | Risk-review evidence when embedded gain, volatility, drawdown, or concentration becomes material. | Profit alone is not EXIT or REDUCE. |

PM evaluates Expected Edge and emits the canonical action. Evidence components must not independently emit `BUY_NEW`, `ADD`, `HOLD`, `REDUCE`, or `EXIT`.

Action interpretation under Expected Edge:

| Action | Expected Edge interpretation |
|---|---|
| `BUY_NEW` | No-position symbol has sufficiently attractive forward Expected Edge and entry evidence. |
| `HOLD` | Open position still has sufficient forward Expected Edge; profit alone does not cancel HOLD. |
| `ADD` | Existing position remains among the strongest Expected Edge opportunities and incremental value exists. |
| `REDUCE` | Expected Edge or risk/reward has weakened enough to trim exposure, but full exit is not yet required. |
| `EXIT` | Forward Expected Edge is no longer sufficient, continuation has broken, or risk/Safety requires full close. |

Open items remain unfrozen: Expected Edge numeric score, thresholds, Trend formula, Profit Review conditions, ADD boundary, REDUCE boundary, and EXIT boundary.

## 3.4 Phase27-D5 PM Expected Edge Reasoning Contract

Phase27-D5 freezes the PM reasoning contract that converts Expected Edge into canonical action. It is a design contract only; it does not define numeric thresholds or change implementation.

Canonical reasoning path:

```text
PIT evidence
  -> Expected Edge evidence bundle
  -> PM Expected Edge reasoning
  -> canonical PM action
  -> downstream target / quantity / runtime mapping
```

PM evaluates Expected Edge, not isolated indicators:

| Isolated input | PM interpretation |
|---|---|
| Trend alone | Evidence of continuation/weakening/break, not final action. |
| Rank alone | Relative opportunity evidence, not BUY/ADD/EXIT authority. |
| Profit alone | Risk Review evidence at most, not EXIT/REDUCE authority. |
| Market Context alone | Regime/risk evidence, not symbol action authority. |
| BUY Quality alone | Reliability/eligibility evidence, not action authority. |

Action boundary philosophy:

| Action | Boundary design |
|---|---|
| `BUY_NEW` | No-position Expected Edge is sufficiently high and evidence is coherent. Rank/cash alone is insufficient. |
| `HOLD` | Expected Edge remains adequate. Slight weakening stays HOLD unless the weakening changes risk/reward enough for REDUCE or invalidates the campaign enough for EXIT. |
| `ADD` | Expected Edge improves, the held symbol remains a strongest opportunity, and incremental investment value exists. |
| `REDUCE` | Expected Edge or risk/reward weakens enough to trim exposure while retaining campaign optionality. This remains a distinct action from HOLD and EXIT. |
| `EXIT` | Expected Edge becomes insufficient, trend/opportunity/signal breaks, or risk/Safety requires full close. Profit alone is insufficient. |

Reason code semantics:

| Reason code | D5 classification | Expected Edge interpretation |
|---|---|---|
| `trend_continuation` | KEEP | Continuation evidence supporting HOLD/ADD. |
| `positive_expected_edge` | REVIEW | Keep as compatibility language, but future PM reasoning should prefer a more explicit Expected Edge adequacy reason. |
| `downside_risk_contained` | KEEP | Risk evidence supporting HOLD/ADD. |
| `risk_increased_but_trend_not_broken` | RENAME | Broad fallback; future contract should split into explicit weakening/risk causes. |
| `peak_drawdown_warning` | KEEP | Risk Review / weakening evidence for REDUCE or EXIT review. |
| `trend_and_opportunity_broken` | KEEP | Expected Edge deterioration evidence for EXIT. |
| `profit_retention_break` | RENAME | Should mean peak-drawdown/profit-retention risk, not simple profit taking. |
| `hard_stop_current_return` | KEEP | Loss-containment / severe risk evidence for EXIT. |

Open threshold items remain out of scope: Expected Edge score, Expected Edge threshold, Trend formula, Profit Review threshold, ADD/REDUCE/EXIT numeric boundaries.

## 3.5 Phase27-D6-B PM Reason Semantics Compatibility Repair

Phase27-D6-B connects D5 reason semantics to the current PM implementation through additive observability metadata only. It preserves legacy reason readability and does not change PM action, score, threshold, quantity, Runtime Planning, Pending, Submit, Safety, Execution, or Ledger behavior.

The canonical contract is:

```text
legacy PM reason
  -> canonical reason metadata / alias contract
  -> Expected Edge trace semantics
  -> no action effect
```

Key mappings:

- `profit_retention_break` becomes canonical `peak_drawdown_profit_retention_risk`; it is risk-review evidence, not profit-taking authority.
- `risk_increased_but_trend_not_broken` becomes canonical `expected_edge_risk_deterioration` unless an already-present trigger proves a more specific risk cause.
- `positive_expected_edge` remains legacy-readable and is explained as `expected_edge_adequate`.

Trace metadata may classify Expected Edge status as `ADEQUATE`, `IMPROVED`, `DETERIORATING`, `INSUFFICIENT`, `RISK_OVERRIDE`, or `NOT_ASSESSED`. These statuses explain the existing branch result and must not recalculate action.

## 3.6 Phase27-D6-C HOLD / REDUCE / EXIT Boundary Design

Phase27-D6-C freezes the PM HOLD / REDUCE / EXIT boundary design as common Position Management Strategy. This is not a Phase27-only rule and does not define thresholds or change implementation.

Boundary model:

| Expected Edge state | PM boundary | Design meaning |
|---|---|---|
| Sufficient / adequate | `HOLD` | Continue the campaign actively; do not exit merely because edge softened slightly or profit exists. |
| Improved | `ADD` candidate | Existing position may become an ADD candidate only when the held symbol remains strongest and incremental value exists. |
| Weakening / deteriorating with optionality | `REDUCE` candidate | Reduce exposure for risk review or edge/risk-reward weakening while preserving the campaign. |
| Insufficient / broken / full-close risk | `EXIT` | Close the campaign when Expected Edge is no longer adequate, continuation is broken, or Safety/risk requires full close. |

HOLD boundary:

```text
Expected Edge remains adequate
AND no full-close risk or Safety requirement
-> HOLD
```

HOLD is active. It means the PM still accepts the campaign's forward Expected Edge. Slight deterioration is not enough for EXIT. HOLD reasons should be explainable through `expected_edge_adequate`, continuation evidence, contained downside risk, or equivalent Expected Edge evidence.

REDUCE boundary:

```text
Expected Edge / risk-reward weakens
AND campaign optionality remains
AND full EXIT is not yet required
-> REDUCE candidate
```

REDUCE is retained as a distinct action concept because it can represent Risk Review, exposure trimming, or partial rotation before EXIT is justified. D6-C does not decide whether REDUCE should later be removed, merged, or threshold-adjusted.

EXIT boundary:

```text
Expected Edge becomes insufficient
OR continuation / signal structure breaks
OR severe risk or Safety requires full close
-> EXIT
```

Trend alone does not decide EXIT. Profit alone does not decide EXIT. `trend_and_expected_edge_broken`, `peak_drawdown_profit_retention_risk`, and `hard_stop_current_return` are evidence classes for Expected Edge deterioration, Risk Review, or severe risk, not independent action authorities.

Risk Review contract:

- `Profit alone -> Action` is prohibited.
- Large embedded gain plus drawdown, concentration, volatility, or changed risk/reward may influence Expected Edge as supporting Risk Review evidence.
- Safety full-close responsibility is separate from PM Expected Edge optimization.

Open items remain: Expected Edge numeric representation, HOLD/REDUCE/EXIT thresholds, Risk Review threshold, Profit Review threshold, REDUCE necessity, and ADD boundary.

## 3.7 Phase27-D6-D Minimal HOLD / EXIT Boundary Implementation

Phase27-D6-D implements the first minimal PM boundary improvement from the D6-C design. The implemented rule is:

```text
Expected Edge adequate
AND profit-retention / peak-drawdown risk is the only EXIT evidence
AND severe full-close risk is absent
-> HOLD
```

The implementation uses existing PM evidence only. It does not add thresholds, magic numbers, fixed holding days, fixed profit rates, stop-loss rules, re-entry cooldown, BUY_NEW changes, ADD changes, Position Sizing changes, Runtime Planning changes, Pending changes, Submit changes, Safety changes, or Execution changes.

Preserved EXIT evidence includes:

- `hard_stop_current_return`
- `trend_and_expected_edge_broken`
- explicit risk guard bad status
- high downside risk evidence
- high exit-score evidence

This implementation converts only the targeted unnecessary early EXIT class into active HOLD. Return improvement is not the D6-D success criterion; the success criterion is that positions with adequate Expected Edge are not exited solely because of profit-retention / peak-drawdown risk review.

## 3.8 Phase27-D6-E 100BD Adoption Status

Phase27-D6-E reviews the D6-D boundary against existing 100 business-day Baseline / After run evidence. The D6-D HOLD / EXIT boundary is adopted with limitations:

```text
Adoption: ADOPTED_WITH_LIMITATIONS
Target EXIT -> HOLD: OBSERVED
Direct causal benefit: PARTIAL
Single-change integrity: PATH_DEPENDENT
Risk regression: NOT_OBSERVED
```

The adoption means the narrow D6-D HOLD boundary remains valid PM behavior. It does not mean the full 100BD return delta is D6-D profit. Later portfolio path differences, ADD/HOLD/REDUCE count changes, execution sequence differences, and open-position valuation differences must be treated as path-dependent effects unless separately proven.

D6-E known limitations:

- The compared runs differ by profile and source commit.
- The After run lacks the Baseline-style `performance_report` directory.
- PM comparison uses `business_date + symbol + position-state equality`; run-scoped `position_campaign_id` values are not cross-run equality keys.
- After close is `REVIEW_REQUIRED` due non-mutating Strategy Shadow review, classified as non-blocking but adoption-limiting.

## 4. Canonical Position Lifecycle

```text
NO_POSITION
  -> BUY_NEW
  -> OPEN_POSITION
  -> HOLD / ADD / REDUCE
  -> EXIT
  -> NO_POSITION
  -> Optional future BUY_NEW as Re-entry
```

Re-entry is not a separate Strategy action. It is a new BUY_NEW after a prior campaign has fully exited. It must not receive preferential treatment, and prior campaign PnL must not become a Strategy input. Execution and campaign identity still need to record the prior exit and new campaign boundary.

## 5. Canonical Position Decision

For each decision-scope symbol and business date, the system should materialize one canonical position decision row. Allowed actions are:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
NO_ACTION
```

Required fields:

- schema_version
- run_id
- business_date
- accepted_generation
- symbol
- position_campaign_id
- current_position_state
- current_quantity
- current_notional
- current_weight
- candidate_id
- opportunity_id
- opportunity_rank
- opportunity_score
- quality_decision_id
- quality_score
- quality_action
- momentum_continuation_state
- momentum_strength
- momentum_change
- signal_reliability
- market_context
- portfolio_fit
- incremental_investment_eligibility
- position_decision
- decision_reason_codes
- decision_summary
- target_membership
- target_weight_candidate
- target_notional_candidate
- target_quantity_candidate
- quantity_delta_candidate
- order_required
- planned_order_side
- planning_intent
- safety_status
- lineage

Action semantics:

- BUY_NEW: Open a new campaign in a symbol with no current position when incremental investment is justified and downstream feasibility is positive.
- ADD: Increase an existing open position when momentum/eligibility/portfolio/sizing produce a positive quantity delta.
- HOLD: Active Strategy/PM decision to keep the position open with approximately unchanged quantity.
- REDUCE: Keep the campaign open while reducing quantity.
- EXIT: Close the position campaign.
- NO_ACTION: No executable order result for the symbol/date; not equivalent to HOLD unless linked to an explicit HOLD decision.

HOLD is an active Strategy/PM decision. NO_ACTION is the downstream no-order result. They must remain separate in artifacts even when HOLD maps to zero quantity delta and Runtime Planning NO_ACTION.

## 6. Decision Authority Matrix

| Decision | Producer | Consumer | Executable | Judgment |
|---|---|---|---|---|
| BUY_NEW | Canonical Position Decision / Portfolio Construction | Runtime Planning -> Formal Planning -> Pending -> Approval -> Submit | True | DEFINED |
| ADD | PM directional intent plus Canonical Position Decision / Portfolio Construction / Position Sizing | Runtime Planning BUY_ADD path | True | REPAIR_REQUIRED_BEFORE_PERFORMANCE_DESIGN |
| HOLD | Position Management AI / Canonical Position Decision | Portfolio Construction and Position Sizing | False | DEFINED_WITH_OBSERVABILITY_GAP |
| REDUCE | PM directional intent plus Portfolio Construction / Position Sizing | Runtime Planning sell intent -> Formal Planning -> Pending -> Approval -> Submit | True | DEFINED |
| EXIT | PM directional intent plus Portfolio Construction / Safety | Runtime Planning sell intent -> Formal Planning -> Pending -> Approval -> Submit | True | DEFINED |
| NO_ACTION | Runtime Planning / Strategy Planning result after zero/no executable delta | Submit as no-order/no-action completion | False | DEFINED_AS_EXECUTION_RESULT |

Responsibility separation is mandatory:

- PM owns existing-position directional intent.
- Portfolio Construction owns target membership and target weight.
- Position Sizing owns target notional, target quantity, and quantity delta.
- Runtime Planning maps quantity deltas to BUY_NEW, BUY_ADD, NO_ACTION, REDUCE, or EXIT execution intent.
- Safety remains independent.
- Pending, Approval, and Submit own order authorization and broker boundary.

## 7. BUY_NEW

BUY_NEW opens a new campaign in a symbol with no current position. It requires candidate eligibility, sufficient opportunity, BUY Quality eligibility, sufficient incremental investment eligibility, acceptable portfolio fit, and capital/safety feasibility. Relative rank alone is not sufficient: best remaining candidate does not automatically mean BUY_NEW.

No numeric score threshold or weight is fixed by this design.

## 8. HOLD

HOLD means the current position should remain open, current quantity should remain approximately unchanged, momentum continuation remains valid, exit conditions are not met, and ADD evidence is not sufficient.

Formal mapping:

```text
HOLD
-> target position remains
-> quantity delta = 0
-> Runtime Planning NO_ACTION
```

The HOLD reason must be preserved in the canonical decision artifact.

## 9. ADD and BUY_ADD Repair

PM ADD is directional intent, not an order.

Canonical ADD chain:

```text
PM ADD
-> Canonical Position Decision
-> Portfolio Construction
-> Position Sizing
-> positive quantity delta
-> Runtime Planning BUY_ADD
-> Formal Planning
-> Pending
-> Approval
-> Submit
-> Execution
```

ADD requires momentum continuation or strengthening, existing position validity, incremental investment eligibility, portfolio concentration acceptance, positive target quantity delta, and Safety acceptance. Rank1 alone and PM ADD alone are never automatic ADD.

Legacy ADD disposition:

- Legacy path: `runtime_v2/planning/sell_pipeline.py -> runtime_v2/planning/add_consumer.py -> pm_add_order_plan -> pending`
- A9 classification: `DEPRECATED_BUT_ACTIVE`
- Recommended final disposition: `RETIRE`
- Migration bridge: `COMPATIBILITY_ADAPTER_NON_DECISION`

The legacy path should become a compatibility adapter that cannot produce decisions or quantities during migration, then be retired. The migration must prevent double authority, duplicate Pending generation, and quantity double counting across Production, Demo, and Historical.

## 10. REDUCE

REDUCE keeps the campaign open while shrinking quantity. Valid conceptual reasons include momentum weakening, risk deterioration, concentration adjustment, opportunity deterioration, or partial rotation to a stronger opportunity. REDUCE is not simple profit taking, and Position Sizing owns the partial quantity.

## 11. EXIT

EXIT closes a campaign. Valid conceptual reasons include momentum continuation failure, signal invalidation, material opportunity deterioration, risk or Safety requirement, or portfolio replacement by materially stronger opportunity.

Prohibited EXIT designs include fixed holding-period exit, simple profit-taking exit, symbol-specific exit, and test-period-specific exit. HOLD improvements must not weaken fast loss control.

## 12. Momentum Continuation Contract

Momentum Continuation is a separate PIT-only evaluation contract. Phase27-D1 does not fix thresholds.

Inputs:

- trend_state
- trend_strength
- trend_slope
- relative_strength
- price_structure
- volume_confirmation
- volatility_adjusted_momentum
- momentum_persistence
- momentum_acceleration
- momentum_deterioration
- signal_reliability
- market_context_alignment

Outputs:

- STRONG_CONTINUATION
- CONTINUATION
- WEAKENING
- BROKEN
- INSUFFICIENT_EVIDENCE

Available or expected PIT sources include J-Quants daily OHLCV, listed issues/corporate-event facts, accepted Candidate/Opportunity/Market Context/BUY Quality/PM/Portfolio Policy artifacts, and Current position/valuation artifacts. Missing or unconfirmed sources include intraday/tick/order-book evidence, complete sector/benchmark relative-strength coverage where not already materialized, calibrated thresholds, and accepted component provenance schema.

## 13. Incremental Investment Eligibility

Incremental Investment Eligibility asks whether a symbol deserves additional capital now. It is separate from relative ranking and separate from BUY Quality.

Inputs:

- Absolute Opportunity Strength
- Momentum Continuation / Strength
- Signal Reliability
- Market Context Alignment
- Portfolio Fit
- Execution Feasibility
- Concentration / Existing Exposure

Outputs:

- STRONG
- SUFFICIENT
- LIMITED
- INSUFFICIENT
- REVIEW_REQUIRED

BUY Quality remains allocation eligibility and adjustment authority. Incremental Investment Eligibility supports BUY_NEW/ADD versus no incremental capital. Thresholds must be calibrated later through controlled experiments.

## 14. Portfolio Construction

Portfolio Construction generates the target portfolio by integrating BUY_NEW candidates, existing positions, PM intent, Opportunity, BUY Quality, Portfolio Policy, Market Context, Corporate Events, Current, Cash, and Pending.

It must:

- Daily reevaluate existing positions.
- Consume PM ADD/HOLD/REDUCE/EXIT through canonical Position Decision lineage.
- Compare existing positions, BUY_NEW candidates, opportunity evidence, market context, policy, current, cash, and pending.
- Represent existing-position zero-delta as justified HOLD when evidence supports it.
- Represent ADD as target membership retained with target weight increase.
- Represent REDUCE as target membership retained with target weight decrease.
- Represent EXIT as target membership removal.

It must not revive fixed Top-N, fixed slot filling, hidden fallback BUY, broker quantity authority, or Submit authority.

## 15. Position Sizing

Position Sizing must distinguish Total Desired Quantity, Current Quantity, Quantity Delta, and Order Quantity.

Contract formulas:

- `target_notional_candidate = target_weight_candidate * canonical_capital_base`
- `target_quantity_candidate = lot-rounded quantity derived from target_notional_candidate and PIT reference_price`
- `quantity_delta_candidate = target_quantity_candidate - current_quantity`

Mapping:

- no_current_position_positive_delta: BUY_NEW
- current_position_positive_delta: BUY_ADD
- current_position_zero_delta: NO_ACTION after explicit HOLD/retain decision
- current_position_negative_partial_delta: REDUCE
- current_position_full_negative_delta: EXIT

Current Total Equity is the canonical capital base. Quality adjustment must not be double-applied.

## 16. Cash and No-BUY

No fixed cash ratio target is introduced. No-BUY remains a valid Strategy result when no sufficiently attractive incremental opportunity exists.

Required non-deployment evidence:

- eligible_opportunity_count
- strong_incremental_eligibility_count
- planned_buy_notional
- executed_buy_notional
- unallocated_capital
- explicit_non_deployment_reasons

## 17. Re-entry and Whipsaw Boundary

Re-entry remains allowed and is processed as normal BUY_NEW. Required explanation evidence:

- prior_campaign_exit_date
- new_entry_date
- business_day_interval
- current_opportunity
- current_momentum_state
- current_quality
- current_incremental_eligibility
- market_context

Prior realized PnL, future price path, and post-hoc whipsaw labels are prohibited Strategy inputs. Whipsaw is a human-review diagnostic supported by observability.

## 18. Observability

The design requires:

- Full candidate universe and dropout-stage evidence.
- Direct BUY lineage IDs through fills.
- PM reasoning and decision components.
- Exit/holding diagnostics such as MFE, MAE, winner giveback, peak unrealized PnL, exit-to-re-entry interval, and holding-period path.
- Immutable morning canonical Position Decision artifact, separate from EOD shadow.

## 19. Safety and Architecture Boundaries

Safety is not Strategy. Submit Guard is not Strategy. PM Intent is not Quantity Authority. Runtime Planning is not Ranking Authority. Historical Result is not Strategy Input.

ADD repair must not bypass Safety, Approval, Submit Guard, temporal authority, accepted generation, Current/Ledger/Broker authority, BUY Quality lineage, or Morning/EOD shadow separation.

## 20. Implementation Workstreams

- WS1 - BUY_ADD Architecture Repair: Canonical PM artifact resolution, PM -> Portfolio Construction wiring, Legacy add_consumer disposition, Double-authority guard, Mode parity
- WS2 - Canonical Position Decision Artifact: BUY_NEW/ADD/HOLD/REDUCE/EXIT/NO_ACTION, Reason and lineage, Immutable morning artifact
- WS3 - Momentum Continuation Foundation: Schema, Producer, PIT source, Observability, Shadow evaluation first
- WS4 - Existing Position Target Portfolio Integration: ADD/HOLD/REDUCE/EXIT, Target weight/membership, Positive and negative delta
- WS5 - Incremental Investment Eligibility: Shadow-only diagnostic first, No immediate decision authority, Calibration/experiment contract
- WS6 - Exit / Holding Observability: MFE/MAE, Giveback, Exit reason, Re-entry interaction
- WS7 - Controlled Performance Experiments: One performance change at a time

## 21. Required Sequence

1. Architecture / Contract Repair Design Freeze
2. BUY_ADD Authority Repair
3. Targeted Unit / Regression
4. Canonical BUY_ADD Contract Proof
5. Position Decision Artifact
6. Momentum Continuation Shadow Foundation
7. Existing Position Integration
8. Exit / Holding Observability
9. Incremental Eligibility Shadow
10. Controlled Performance Experiment
11. User-run Long Historical Test
12. Baseline Comparison
13. Adopt / Reject / Rollback

ADD conditions, Exit conditions, Momentum thresholds, Quality weights, Position Sizing policy, and cash behavior must not be changed during BUY_ADD architecture repair.

## 22. Validation Plan

Codex may run short and targeted validations only:

- py_compile
- unit tests
- targeted regression
- short non-mutating contract validation
- short synthetic fixture
- schema validation
- producer-consumer lineage validation

User-owned long validations:

- fresh-run
- resume
- 10BD
- 100BD
- 1-year Historical
- long smoke

## 23. Controlled Experiments

Performance changes must happen one at a time. Each experiment must include:

- Experiment ID
- Hypothesis
- Evidence
- Changed Component
- Unchanged Components
- Expected Effect
- Risk
- Success Metrics
- Failure Metrics
- Rollback Condition
- Baseline Run
- Test Command

Minimum metrics:

- Return
- PF
- Maximum Drawdown
- Win Rate
- Average Winner
- Average Loser
- Payoff Ratio
- Holding Period
- Re-entry Count
- Winner Giveback
- Cash / Exposure
- BUY_NEW / ADD / HOLD / REDUCE / EXIT distribution

Cash ratio alone is not a success condition.

## 24. Degression Prevention

Must preserve:

- Phase26 Authority
- Accepted Generation binding
- Temporal Authority
- Current / Ledger / Broker Authority
- BUY Quality lineage
- Morning / EOD Shadow separation
- Formal Planning Authority
- Submit Guard responsibility
- Safety

Prohibited:

- Historical-only implementation
- Specific symbol exception
- Specific date exception
- Post-hoc condition fitted to results
- Multiple simultaneous performance changes
- Submit Guard as Strategy producer
- PM as quantity authority

## 25. Open Questions

No numeric thresholds are fixed in Phase27-D1. Open items are:

- Which momentum continuation components receive decision authority?
- What is sufficient ADD evidence?
- Where is the HOLD vs ADD boundary?
- Where is the REDUCE vs EXIT boundary?
- How should absolute opportunity strength be calibrated?
- What threshold separates SUFFICIENT from LIMITED incremental eligibility?
- How should concentration control interact with aggressive capital posture?
- How should market context moderate BUY_NEW/ADD/REDUCE/EXIT?
- What winner giveback tolerance is acceptable?
- How should repeated Exit -> 1BD BUY_NEW be diagnosed?

## 26. Phase27-D1R Design Consistency Revision

Phase27-D1R refines this SoT before implementation entry. The D1 design remains the investment-philosophy foundation, but the implementation contract is amended as follows.

### 26.1 Canonical Artifact State Model

Canonical Position Decision is not a mutable single artifact that is rewritten by every stage. It is a staged contract:

```text
position_intent.v1
  -> target_portfolio_decision.v1
  -> position_sizing_plan.v1
  -> runtime_position_plan.v1
  -> safety_evaluation.v1
  -> pending_order_plan / approval
  -> order / fill / ledger projection
```

The downstream consolidated explanation may join these artifacts for review, but the upstream authority artifacts remain immutable after morning publication. EOD Shadow remains separate and cannot mutate morning authority.

Artifact states:

```text
INTENT_PROPOSED
TARGET_PORTFOLIO_RESOLVED
SIZED
PLANNED
SAFETY_EVALUATED
AUTHORIZED
EXECUTED
```

### 26.2 Canonical Position Intent

`position_intent.v1` is the upstream Strategy proposed action artifact. It is produced before Portfolio Construction and may express `BUY_NEW`, `ADD`, `HOLD`, `REDUCE`, `EXIT`, or `NO_ACTION` as proposed intent with reason lineage.

BUY_NEW producer chain:

```text
Candidate
  -> Opportunity
  -> BUY Quality
  -> Incremental Investment Eligibility
  -> Canonical Position Intent
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning BUY_NEW
```

Portfolio Construction is not the BUY_NEW candidate producer. It is the authority that adopts or rejects candidate membership in the target portfolio.

### 26.3 Canonical Position Plan

`runtime_position_plan.v1` is the executable planning-action artifact after target portfolio and sizing have resolved. It preserves the upstream intent and records the downstream execution mapping.

Decision resolution:

```text
Strategy Proposed Action
+ Target Portfolio Resolution
+ Quantity Delta
+ Safety / Authority Feasibility
= Executable Action
```

Safety never creates Strategy action. Safety may only return:

```text
ALLOW
LIMIT
BLOCK
REVIEW_REQUIRED
```

### 26.4 Action Conflict Resolution

Inconsistent stage outputs must not be silently collapsed into `NO_ACTION`.

Minimum conflict outcomes:

| Combination | Required outcome | Classification |
|---|---|---|
| PM ADD + accepted positive delta | ADD | VALID |
| PM ADD + zero accepted delta | NO_ACTION_DUE_TO_ZERO_DELTA with ADD_NOT_ACCEPTED reason | VALID_WITH_REASON |
| PM HOLD + target weight unchanged | HOLD -> NO_ACTION | VALID |
| PM HOLD + positive target delta | CONTRACT_REVIEW_REQUIRED unless explicit override exists | REVIEW_REQUIRED |
| PM REDUCE + target weight decrease | REDUCE | VALID |
| PM REDUCE + target weight unchanged | NO_ACTION_DUE_TO_ZERO_DELTA with REDUCE_NOT_ACCEPTED reason | VALID_WITH_REASON |
| PM EXIT + membership removed | EXIT | VALID |
| PM EXIT + membership retained | CONTRACT_VIOLATION or REVIEW_REQUIRED | CONTRACT_VIOLATION |
| Incremental Eligibility INSUFFICIENT + BUY_NEW | NOT_ALLOWED | REJECTED_COMBINATION |

ADD / REDUCE intent must not be implicitly converted to HOLD. Lot rounding no-order results must preserve the original intent:

```text
ADD -> NO_ACTION_DUE_TO_LOT_ROUNDING
REDUCE -> NO_ACTION_DUE_TO_LOT_ROUNDING
```

### 26.5 HOLD Semantics

HOLD means:

```text
Target position remains open
Orderable quantity delta after canonical lot rounding == 0
Exit condition not met
ADD / REDUCE condition not accepted
```

Do not use approximate quantity language for HOLD.

### 26.6 Decision Scope

Daily canonical intent/plan scope is:

```text
Current Holdings
UNION BUY-eligible candidates reaching required Strategy stage
UNION Pending / Open-order symbols
UNION Mandatory Safety Review symbols
UNION Corporate-event affected symbols
```

Full Candidate Universe remains a separate dropout/observability artifact.

Dedup key:

```text
business_date
symbol
accepted_generation
position_campaign_id
```

### 26.7 Feature / Component Responsibility Boundary

Responsibilities:

- Opportunity: cross-sectional relative attractiveness.
- BUY Quality: BUY allocation eligibility and confidence adjustment.
- Momentum Continuation: existing-position continuation / deterioration evaluation.
- Incremental Investment Eligibility: additional capital versus no incremental capital.

Prohibited:

- implicit double weighting of the same feature
- double application of Quality adjustment
- adding Momentum components back into Opportunity without explicit authority
- multiple Market Context modifiers without an inventory entry and consumer contract

### 26.8 Authority Modes

Momentum Continuation and Incremental Investment Eligibility must expose:

```text
authority_mode: SHADOW | ADVISORY | ACTIVE
```

Mode effects:

- `SHADOW`: observability only; no decision effect.
- `ADVISORY`: visible to canonical intent producer; cannot independently change action.
- `ACTIVE`: authorized decision input after calibration and approval.

ACTIVE requires evidence completeness, calibration completion, short regression PASS, controlled experiment PASS, human approval, no PIT violation, and no degression.

### 26.9 EXIT / Replacement and Loss-cut Boundary

EXIT by materially stronger replacement requires evidence for current momentum, current opportunity, replacement strength, strength gap, incremental eligibility, switching/execution feasibility, concentration impact, and current-position deterioration.

Prohibited:

- simple Rank difference EXIT
- near-tie EXIT
- cash-creation EXIT
- fixed rotation EXIT

Loss-cut authority is separated:

- Strategy EXIT: PIT price structure / momentum / signal invalidation.
- Safety REDUCE / EXIT: independent safety or broker-risk requirement.
- Post-hoc Loss Classification: human review only.

Historical PnL, trade outcome, PF, and win rate must not be daily Strategy/PM inputs.

### 26.10 Legacy ADD Migration Acceptance

Legacy path:

```text
sell_pipeline
  -> add_consumer
  -> pm_add_order_plan
  -> pending
```

Disposition states:

```text
ACTIVE
NON_DECISION_COMPATIBILITY
RETIRED
REMOVED
```

Migration acceptance requires legacy pending production count, quantity authority count, and submit authority count all to be zero; canonical BUY_ADD lineage complete; canonical/legacy duplicate key count zero; Production/Demo/Historical caller inventory complete; legacy tests migrated or retired; no active imports except compatibility telemetry; and adapter inability to generate order decisions.

Phase27-D2-C implements the retained legacy adapter as `NON_DECISION_COMPATIBILITY`. The adapter may publish `legacy_pm_add_compatibility.v1` observability, but its authority fields are fixed to `decision_effect = NONE`, `quantity_authority = NONE`, `pending_authority = NONE`, `approval_authority = NONE`, `submit_authority = NONE`, and `telemetry_only = true`. ADD-specific cash exposure, position sizing, quantity, Pending, Approval, Submit, Fill Projection, and Ledger authority remain outside the legacy adapter.

### 26.11 Double-authority Prevention

Canonical and legacy ADD authority must be mutually exclusive.

Dedup key:

```text
run_id
business_date
symbol
position_campaign_id
decision_id
```

Prevent duplicate Position Intent, Sized Delta, Pending, Approval, Submit, Fill Projection, and Ledger Application. Conflict behavior is `REVIEW_REQUIRED` or explicit block. Fail-open is prohibited.

D2-C applies the same key to compatibility telemetry. Duplicate legacy keys, lineage mismatch, or any canonical/legacy overlap where both sides claim executable ADD authority must fail closed with `REVIEW_REQUIRED` or `BLOCKED`.

### 26.12 Implementation Completeness Checklist

Every workstream must account for:

```text
Design Contract
Schema
Producer
Consumer
Caller
Production
Demo
Historical
Fixture
Unit Test
Targeted Regression
Artifact Evidence
Observability
Documentation
Legacy Migration
Rollback
Degression Audit
```

Allowed checklist statuses are `REQUIRED`, `NOT_APPLICABLE`, `COMPLETE`, `INCOMPLETE`, and `BLOCKED`. `NOT_APPLICABLE` requires a reason.

### 26.13 Revised Implementation Sequence

1. Design / Schema / Authority Freeze
2. Producer-Consumer / Caller Inventory
3. Minimal Canonical Position Intent Artifact
4. PM Artifact Resolution Repair
5. Portfolio Construction Integration
6. Legacy ADD non-decision conversion
7. Position Sizing positive / zero / negative delta proof
8. Runtime Planning BUY_ADD / HOLD / REDUCE / EXIT proof
9. Canonical Position Plan Artifact
10. Migration Acceptance / Legacy Retirement
11. Full Degression Review
12. Momentum Continuation Shadow
13. Exit / Holding Observability
14. Incremental Eligibility Shadow
15. Controlled Performance Experiment

Architecture repair must not change performance logic, thresholds, weights, exit logic, sizing policy, or cash ratio.

### 26.14 Regression / Degression Contract

Non-change guarantees:

- BUY_NEW unchanged during BUY_ADD repair
- HOLD unchanged
- REDUCE unchanged
- EXIT unchanged
- Safety unchanged
- Submit Guard unchanged
- Accepted Generation unchanged
- Temporal Authority unchanged
- Current / Ledger / Broker Authority unchanged
- Morning / EOD Shadow separation unchanged
- Quality lineage unchanged
- No Historical-only branch

Required negative tests:

- PM ADD cannot directly generate Pending
- Legacy adapter cannot create quantity
- Canonical and Legacy cannot both authorize
- Zero delta cannot become BUY_ADD
- Positive existing-position delta cannot become BUY_NEW
- No current position positive delta cannot become BUY_ADD
- PM HOLD cannot silently become ADD
- PM EXIT cannot retain membership without review

## 27. Phase27-D2-A Schema / Authority Freeze Implementation Note

Phase27-D2-A implements the first foundation artifact from the D1R staged model:

```text
position_intent.v1
```

Implementation boundary:

- `authority_mode = SHADOW`
- `decision_effect = NONE`
- no Portfolio Construction consumer connection
- no Position Sizing change
- no Runtime Planning change
- no Pending / Approval / Submit / Execution change
- no Legacy ADD retirement or behavior change

Schema:

```text
docs/02_architecture/schemas/position_intent.v1.schema.json
```

Producer:

```text
src/ai_fund_lab_v2/strategy/position_intent.py
```

Runtime materialization path:

```text
<runtime_root>/strategy_artifacts/position_intent/<business_date>/position_intent.json
```

The D2-A producer maps Runtime PM decisions to shadow proposed intents without changing their meaning:

```text
PM ADD -> proposed_position_intent ADD
PM HOLD -> proposed_position_intent HOLD
PM REDUCE -> proposed_position_intent REDUCE
PM EXIT -> proposed_position_intent EXIT
```

BUY_NEW candidate rows, when source artifacts are supplied, remain `UNRESOLVED` in D2-A because Incremental Investment Eligibility is not yet an active decision authority.

Missing inputs, business-date mismatch, accepted-generation mismatch, and duplicate dedup keys are explicit review/block evidence. No hidden fallback is allowed.

## 28. Phase27-D2-B PM Intent Resolution Implementation Note

Phase27-D2-B implements the second foundation artifact from the D1R staged model:

```text
target_portfolio_decision.v1
```

Implementation boundary:

- `authority_mode = SHADOW`
- `decision_effect = NONE`
- existing Portfolio Construction output is not replaced
- target weights are not changed
- Position Sizing is not connected
- Runtime Planning is not connected
- BUY_ADD is not generated
- Legacy ADD / add_consumer / sell_pipeline are not changed
- Pending / Approval / Submit / Execution are not changed

Schema:

```text
docs/02_architecture/schemas/target_portfolio_decision.v1.schema.json
```

Shadow resolver:

```text
src/ai_fund_lab_v2/strategy/target_portfolio_decision.py
```

Runtime materialization path:

```text
<runtime_root>/strategy_artifacts/target_portfolio_decision/<business_date>/target_portfolio_decision.json
```

The D2-B resolver consumes `position_intent.v1` as canonical PM directional intent evidence and maps:

```text
position_intent ADD    -> RETAIN / INCREASE / POSITIVE_DELTA_REQUIRED
position_intent HOLD   -> RETAIN / MAINTAIN / ZERO_DELTA_EXPECTED
position_intent REDUCE -> RETAIN / DECREASE / NEGATIVE_DELTA_REQUIRED
position_intent EXIT   -> REMOVE / REMOVE / FULL_REMOVAL_REQUIRED
```

`BUY_NEW`, `UNRESOLVED`, and missing/mismatched evidence remain unresolved or review/block evidence in D2-B. No silent conversion to HOLD or NO_ACTION is allowed.

## 29. Phase27-D2-D Position Sizing Plan Shadow Delta Contract

Phase27-D2-D adds the third staged artifact from the D1R model:

```text
position_sizing_plan.v1
```

Implementation boundary:

- `authority_mode = SHADOW`
- `decision_effect = NONE`
- existing formal `position_sizing.v1` output is not replaced
- target weight formal calculation is not changed
- Runtime Planning is not connected
- BUY_ADD and BUY_NEW are not generated
- Pending / Approval / Submit / Execution are not changed
- Legacy ADD remains `NON_DECISION_COMPATIBILITY`

Runtime materialization path:

```text
<runtime_root>/strategy_artifacts/position_sizing_plan/<business_date>/position_sizing_plan.json
```

The shadow plan consumes `target_portfolio_decision.v1` and maps existing-position direction into quantity delta candidates:

```text
ADD    -> positive delta or ADD_NOT_SIZED
HOLD   -> zero delta or HOLD_NOT_SIZED
REDUCE -> negative partial delta or REDUCE_NOT_SIZED
EXIT   -> full negative delta or EXIT_NOT_SIZED
```

Position Sizing Plan must not rewrite PM intent. A row that starts as PM ADD must not become HOLD/zero delta; a row that starts as PM REDUCE must not become HOLD/zero delta. If evidence is insufficient, the row keeps PM intent and emits the matching `*_NOT_SIZED` status.

`position_sizing_plan.v1` is a quantity delta candidate artifact only. Runtime Planning intent, Pending item, Approval, Submit, Execution, Fill Projection, and Ledger fields are forbidden until a later integration phase explicitly connects them.

## 30. Phase31-G136 Portfolio Rotation Boundary Reference

The permanent architecture SoT for future high-resolution marginal capital value
and portfolio-wide capital rotation is:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

Future portfolio-wide rotation must preserve the momentum-follow lifecycle:

- HOLD remains an active continuation decision.
- REDUCE remains a PM-owned partial shrink action.
- EXIT remains a PM-owned full close action.
- Profit alone is not REDUCE or EXIT authority.
- Rotation evidence may support PM reasoning, but must not directly sell,
  synthesize Runtime rotation, or replace a HOLD merely because another score is
  slightly higher.

Portfolio Rotation must depend on high-resolution marginal capital value and
must preserve campaign identity, anti-churn semantics, Safety, lot granularity,
re-entry correctness, and PIT-only evidence use.
