# Phase32-CM — Bounded Minimum Executable One-Lot Authority Design

## Executive Summary

This is a Design-only report. No Production code, config, thresholds, weights, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

Phase32-CM defines `minimum_executable_one_lot_authority.v1` for NEW/REENTRY reduced-quality sub-lot targets. The authority is PC-owned and PIT-only. It preserves CH/CJ Buy Quality target semantics by default while allowing a bounded, explicit one-lot candidate only when decision-time evidence justifies expressing positive PC allocation intent as the minimum executable Japanese trading unit.

Core design:

```text
one_lot_weight <= quality_authorized_target_weight
  -> normal quality-bounded CC multi-lot path

one_lot_weight > quality_authorized_target_weight > 0
  -> explicit minimum executable one-lot authority evaluation
  -> ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED
```

`ADMIT_ONE_LOT` does not mean “buy.” It only authorizes one explicit `NEW_FIRST_LOT` / `REENTRY_FIRST_LOT` candidate to enter common frontier competition. The one-lot candidate can still lose to other NEW, REENTRY, ADD, or Cash.

## Design Lineage

Reviewed sources:

- `phase32_cl_adaptive_buy_quality_allocation_semantics_lot_granularity_authority_audit.md`
- `phase32_ck_old_vs_post_cj_day0_capital_deployment_delta_audit.md`
- `phase32_ch_adaptive_buy_quality_target_authority_preservation_implementation.md`
- `phase32_cj_quality_deployable_lot_aware_boundary_narrow_repair.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `phase30_v_entry_intelligence_overheated_momentum_one_lot_capital_concentration_repair_design.md`
- `phase30_ak1u_minimum_executable_one_lot_admission_contract_audit.md`
- `phase30_ak2_minimum_executable_one_lot_admission_repair_implementation.md`

Key inherited design facts:

- Adaptive Buy Quality is individual BUY admission and allocation strength authority.
- `quality_allocation_adjustment` is a multiplicative sizing modifier producing a quality-authorized reduced target.
- Silent re-expansion from quality target to base target is forbidden.
- Phase30 already intended a PC-owned `minimum_executable_one_lot_authority` for BUY_NEW / REENTRY `0 -> 1lot`.
- Safety hard cap pass alone is not proof that Strategy wants the concentration.
- PS may consume one-lot authority only after PC explicitly materializes it.

## Authority Scope

Applies only to:

- `BUY_NEW` / `NEW_FIRST_LOT`
- `REENTRY` / `REENTRY_FIRST_LOT`
- current quantity = 0
- quality-authorized target weight > 0
- one executable trading lot exceeds the quality-authorized target

Does not apply to:

- ADD
- second-lot-plus expansion
- REDUCE / EXIT
- rejected / review-required / buy-wait rows
- rows missing required PIT evidence
- rows where PS or Runtime wants to round up independently

## Required Input Contract

The authority consumes existing PIT evidence only.

Required inputs:

| Input | Source / owner | Use |
| --- | --- | --- |
| Candidate eligibility | Candidate / Opportunity authorities | proves row is real PIT candidate |
| Production deployability | Portfolio Construction | separates candidate from deployable capital row |
| Buy Quality action / score / band | Adaptive Buy Quality | proves allocation capability |
| Quality-authorized target | Portfolio Construction consuming Buy Quality | base target after Quality reduction |
| Rank / opportunity evidence | Opportunity Ranking / PC | opportunity strength and opportunity-cost evidence |
| Entry state | Strategy Intelligence / Buy Quality trajectory | blocks overheated, reversal, buy-wait states |
| Market/regime context | Market Context / Risk Pacing | contextual risk, deployment posture |
| One-lot weight / notional / trading unit | Position Sizing preflight / broker metadata | minimum executable unit |
| Overshoot weight and ratio | derived by PC from Quality target and one-lot facts | concentration and sizing mismatch |
| Projected post-trade weight | PC using PS lot facts | one-lot resulting position weight |
| Strategy cap | PC / Portfolio policy | normal concentration boundary |
| Safety cap | Safety / Safety-derived cap evidence | final hard cap |
| Risk Pacing | Risk Pacing / Portfolio Policy | deployment intensity and budget status |
| Cash / allocation budget | Portfolio Policy / PC budget authority | proves budget is finite and Cash is valid |
| Common alternatives / Cash optionality | Common marginal frontier | final competition after one-lot candidate is admitted |

Missing, stale, ambiguous, or conflicting required evidence produces `REVIEW_REQUIRED`.

## Authority Output

Canonical artifact fragment:

```text
minimum_executable_one_lot_authority.v1:
  schema_version: minimum_executable_one_lot_authority.v1
  authority_type: PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION
  owner: PORTFOLIO_CONSTRUCTION
  decision: ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED
  semantic_type: BUY_NEW | REENTRY
  symbol
  business_date
  current_quantity: 0
  quality_authorized_target_weight
  pre_quality_base_target_weight
  quality_allocation_adjustment
  one_lot_weight
  one_lot_notional
  trading_unit
  overshoot_weight
  target_to_one_lot_ratio
  projected_post_trade_weight
  buy_quality_evidence
  opportunity_rank_evidence
  entry_state_evidence
  regime_risk_evidence
  strategy_cap_status
  safety_cap_status
  risk_pacing_status
  cash_budget_status
  common_frontier_candidate_status
  source_lineage
  reason_codes
  future_information_used: false
  historical_outcome_used: false
```

Compatibility aliases may be emitted for existing consumers:

```text
decision_alias = ADMIT when decision == ADMIT_ONE_LOT
reason = MINIMUM_EXECUTABLE_ONE_LOT_ADMITTED when decision == ADMIT_ONE_LOT
ps_final_quantity = trading_unit
final_promoted_target_weight = one_lot_weight
```

## Decision Semantics

### ADMIT_ONE_LOT

`ADMIT_ONE_LOT` means:

```text
PC authorizes a single minimum-executable one-lot candidate to enter common capital competition.
```

It does not mean:

- forced BUY
- fixed exposure
- target re-expansion to base target
- second-lot permission
- ADD permission
- PS-side rounding permission

Required conditions:

- candidate exists and is PIT valid
- `production_deployable_new` or `production_deployable_reentry` is true before lot granularity
- Buy Quality action is `FULL_ALLOCATION_ELIGIBLE` or `REDUCED_ALLOCATION_ONLY`
- Buy Quality is not `REJECT`, `REVIEW_REQUIRED`, or `BUY_WAIT`
- quality-authorized target is positive
- one lot exceeds quality target but stays within hard Safety cap
- Strategy cap status is PASS or an explicit Strategy soft-overshoot authority exists
- entry state is not overheated, reversal-risk, or buy-wait
- opportunity/rank evidence is supportive enough under existing PC evidence to justify one-lot expression
- overshoot evidence is materialized and not classified as disproportionate
- Risk Pacing budget is valid
- Cash/budget evidence is valid
- no pending/campaign/broker/corporate-action conflict exists

After `ADMIT_ONE_LOT`, common frontier still decides whether this one-lot candidate beats alternatives and Cash.

### BLOCK

`BLOCK` means:

```text
PC has enough evidence to decide that one-lot concentration is not justified.
```

Examples:

- one lot is disproportionate to Quality target and opportunity evidence
- entry state is `BUY_WAIT`, overheated, reversal-risk, or otherwise weak for overshoot
- projected post-trade weight breaches Strategy cap without explicit soft-overshoot authority
- Safety cap fails
- Cash optionality is preferable and no one-lot candidate should be generated
- candidate is only candidate-eligible but not production-deployable

Blocked capital remains Cash or re-enters the existing residual/common-frontier process for other valid candidates.

### REVIEW_REQUIRED

`REVIEW_REQUIRED` means:

```text
PC cannot safely decide ADMIT_ONE_LOT or BLOCK because required authority evidence is missing, stale, ambiguous, or conflicting.
```

Examples:

- missing Buy Quality decision
- missing quality-authorized target
- missing one-lot weight / price / trading unit
- conflicting Strategy cap / Safety cap
- ambiguous production deployability
- missing Cash/budget source
- inconsistent source lineage

Fail-open is forbidden.

## Overshoot Semantics

Overshoot is not a single fixed threshold selected from historical outcome.

The authority must materialize:

```text
overshoot_weight = one_lot_weight - quality_authorized_target_weight
target_to_one_lot_ratio = quality_authorized_target_weight / one_lot_weight
one_lot_to_target_ratio = one_lot_weight / quality_authorized_target_weight
projected_post_trade_weight
```

Then PC classifies the overshoot using existing decision-time semantics:

- Buy Quality strength
- opportunity/rank support
- entry state
- market/regime posture
- portfolio fit
- Strategy cap/headroom
- Safety cap
- Risk Pacing budget
- Cash optionality and common alternatives

No new historical-performance-selected numeric threshold is allowed in CM. If a later implementation needs concrete cut points, they must be architecture/config decisions justified without future PnL and must be emitted as policy authority, not hidden constants.

## Common Frontier Integration

The one-lot authority sits before common frontier candidate generation.

Flow:

```text
PC production admission
-> Adaptive Buy Quality target
-> lot granularity check
-> minimum_executable_one_lot_authority.v1
-> if ADMIT_ONE_LOT: create one NEW_FIRST_LOT / REENTRY_FIRST_LOT candidate
-> common NEW / REENTRY / ADD / Cash frontier
-> BF aggregate if accepted
-> PS quantity conversion
-> Runtime mapping
```

Rules:

- `ADMIT_ONE_LOT` creates eligibility to compete, not final purchase authority.
- The candidate is exactly one lot.
- Lot #2 and beyond are absent unless the normal quality-bounded target supports them.
- Cash remains first-class.
- The one-lot candidate can lose to stronger NEW/REENTRY/ADD or Cash.
- BF may aggregate the accepted one lot only if the candidate wins frontier competition.
- PS must not independently infer or round up absent authority.

## Representative Design Cases

These examples use Phase32-CK Day-0 PIT artifact observations. No future PnL or return is used.

| Symbol | Quality target | One-lot weight | One-lot / quality | Authority expression |
| --- | ---: | ---: | ---: | --- |
| 33700 | about 2.17% | about 3.41% | 1.57x | Eligible for explicit one-lot evaluation. Overshoot is material but potentially bounded; decision depends on Buy Quality/opportunity/entry/risk/Cash evidence. |
| 83060 | about 2.06% | about 6.48% | 3.14x | Requires stronger evidence than ordinary reduced allocation; likely BLOCK unless opportunity/entry/portfolio evidence explicitly justifies concentration. |
| 92420 | about 2.07% | about 13.75% | 6.65x | Extreme overshoot. Safety pass alone is insufficient; default BLOCK or REVIEW_REQUIRED absent exceptional PIT authority. |
| 93600 | about 2.32% | about 19.11% | 8.23x | Extreme near-Strategy-cap exposure from one lot. Default BLOCK/REVIEW_REQUIRED; must not be admitted by cash availability or low position count alone. |

Important: CM does not label any of these symbols as good or bad from future outcome. It defines how the authority should represent the decision-time question.

## Guardrail Preservation

Preserved by design:

- CH/CJ quality semantics: reduced target remains binding unless this explicit authority authorizes one lot.
- CC NEW/REENTRY multi-lot: normal path unchanged when target supports lots.
- BZ ADD PASS-only and BF-only authority: unchanged; one-lot authority does not apply to ADD.
- Strategy 18% cap and Safety 25% hard cap: separated and both observed.
- Common capital competition: preserved after one-lot admission.
- Cash optionality: preserved and can defeat the one-lot candidate.
- PS/Runtime: unchanged; PS consumes only PC/BF authority and remains quantity authority.
- REDUCE/EXIT: unchanged.
- Legacy fallback: forbidden.
- PIT-only: required.

## Implementation Readiness

Implementation-ready boundary:

1. Extend PC one-lot admission output to `decision = ADMIT_ONE_LOT | BLOCK | REVIEW_REQUIRED`.
2. Add source fields for quality target, overshoot, opportunity/rank, entry state, cap, Safety, Risk Pacing, Cash/budget, and lineage.
3. Modify common frontier candidate generation so sub-lot NEW/REENTRY rows create a one-lot candidate only when this authority is `ADMIT_ONE_LOT`.
4. Keep CH/CJ default block when authority is missing or `BLOCK`.
5. Keep PS consumption constrained to BF aggregated target rows / explicit one-lot authority.
6. Add tests for ADMIT/BLOCK/REVIEW_REQUIRED and representative 33700/83060/92420/93600 shapes.

Implementation is ready at the contract level. It is PARTIAL only because any later implementation must choose a deterministic non-PnL policy method for classifying overshoot acceptability from existing evidence.

## Acceptance Tests To Require Later

- normal quality target >= one lot bypasses one-lot authority and uses CC multi-lot path
- reduced sub-lot target with missing one-lot evidence -> REVIEW_REQUIRED
- reduced sub-lot target with missing Buy Quality -> REVIEW_REQUIRED
- `REJECT` / `REVIEW_REQUIRED` / `BUY_WAIT` -> no one-lot candidate
- modest overshoot with supportive PIT evidence -> `ADMIT_ONE_LOT`
- extreme overshoot with weak/reduced evidence -> `BLOCK`
- Strategy cap breach without explicit soft-overshoot authority -> `BLOCK`
- Safety cap breach -> `BLOCK`
- Cash/budget missing -> `REVIEW_REQUIRED`
- `ADMIT_ONE_LOT` can still lose to Cash in common frontier
- no second-lot-plus admission from this authority
- ADD unaffected
- BF aggregation only after frontier acceptance
- PS cannot round up without authority
- deterministic rerun
- future/outcome field injection fail-closed

## Final Judgments

PHASE32_CM_ONE_LOT_AUTHORITY_DEFINED = YES

PHASE32_CM_PC_OWNED = YES

PHASE32_CM_QUALITY_SEMANTICS_PRESERVED = YES

PHASE32_CM_OVERSHOOT_RISK_EXPLICIT = YES

PHASE32_CM_COMMON_COMPETITION_PRESERVED = YES

PHASE32_CM_IMPLICIT_RESCUE_FORBIDDEN = YES

PHASE32_CM_HISTORICAL_THRESHOLD_SELECTION_USED = NO

PHASE32_CM_IMPLEMENTATION_READY = PARTIAL

PHASE32_CM_PRODUCTION_CHANGE_THIS_TASK = NO

PHASE32_CM_NEXT_STEP = Implement the PC-owned bounded one-lot authority with fail-closed ADMIT_ONE_LOT/BLOCK/REVIEW_REQUIRED materialization, then run focused non-fresh reproductions for normal multi-lot, modest overshoot, extreme overshoot, Cash defeat, BF aggregation, PS no-round-up, and PIT/determinism.
