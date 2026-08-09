# Phase28-B Incremental Investment Eligibility and Canonical ADD Allocation Design

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_B_INCREMENTAL_INVESTMENT_ELIGIBILITY_DESIGN_COMPLETE_PHASE28_C_READY
```

Phase28-C Entry Decision:

```text
APPROVED
```

Task type:

```text
DESIGN_ONLY
DESIGNED_NOT_IMPLEMENTED
```

Phase28-B designs the Incremental Investment Eligibility contract, canonical ADD target-weight bridge, positive quantity-delta contract, ADD decision trace, reason codes, failure behavior, and Phase28-D acceptance contract. No Production Runtime, Strategy, PM, Portfolio Construction, Position Sizing, Runtime Planning, Submit, Config, Schema, Legacy, threshold, or performance parameter implementation was changed. Codex did not run fresh-run, resume, 10BD, 20BD, 100BD, 1-year, or long Historical validation.

Phase28-C should implement exactly one performance change:

```text
Connect ADD Expected Edge Improvement + Incremental Investment Value PASS
to Portfolio Construction target_weight increase for existing positions,
so Position Sizing can produce a positive quantity_delta_candidate and
Runtime Planning can emit BUY_ADD through the existing canonical mapping.
```

## 2. Scope

This is a design and contract task. It accepts Phase28-A's baseline findings and designs how a valid PM ADD can become a canonical target allocation increase without giving PM quantity authority, reviving Legacy ADD executable authority, forcing cash deployment, or making Rank1/profit/cash standalone Action Authority.

## 3. Phase28-A Findings Accepted as Inputs

Source run:

```text
runtime-test-historical-smoke-20260804T074611098414Z
2023-01-04 through 2023-05-31
100 business days
```

Accepted facts:

| Metric | Count |
|---|---:|
| Existing-position rows | 364 |
| PM ADD intent | 145 |
| Runtime Planning BUY_ADD | 0 |
| ADD submit | 0 |
| ADD fill | 0 |
| ADD zero delta | 145 |
| ADD zero quantity | 145 |
| Rank1 existing-position rows | 86 |
| Rank1 PM ADD intent rows | 76 |
| Rank1 BUY_ADD rows | 0 |

Final current gap definition:

```text
PM ADD intent exists but is not converted into Portfolio Construction target weight increase,
Position Sizing positive quantity_delta_candidate, or Runtime Planning BUY_ADD in the baseline evidence.
```

## 4. Documents Reviewed

- `docs/phase_reports/phase27_to_phase28_chatgpt_handoff.md`
- `docs/phase_reports/phase27_final_summary_and_phase28_handoff.md`
- `docs/phase_reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review.md`
- `docs/phase_reports/phase28_a_add_baseline_and_incremental_investment_evidence_audit.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis.md`
- `docs/phase_reports/phase27_a8_add_authority_contract_review.md`
- `docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md`
- `docs/phase_reports/phase27_d6a_pm_implementation_gap_audit.md`
- `docs/01_requirements/phase_roadmap.md`

## 5. Existing Runtime / Strategy Contract

Existing canonical ADD chain remains unchanged:

```text
PM ADD
-> Canonical Position Decision / position_intent
-> Portfolio Construction target membership / target_weight
-> Position Sizing target_quantity_candidate / quantity_delta_candidate
-> Runtime Planning BUY_ADD for existing current position + positive delta
-> Strategy Planning Authority / Pending
-> Approval / Safety
-> Submit
-> Execution / Fill / Ledger
```

Runtime Planning remains a pure mapper:

```text
existing position + quantity_delta_candidate > 0 -> BUY_ADD
existing position + quantity_delta_candidate = 0 -> NO_ACTION
```

PM ADD remains directional intent only. Rank1, profit, cash, or PM ADD alone must not become BUY_ADD.

## 6. Current ADD Gap

Why PM ADD 145 rows all became zero delta:

```text
PM ADD was observable as intent.
Strategy PM rows consumed by Portfolio Construction were UNRESOLVED in baseline evidence.
Portfolio Construction did not produce ADD target weight increase for those PM ADD rows.
Position Sizing therefore emitted target_notional / desired_quantity / quantity_delta as zero.
Runtime Planning correctly mapped existing-position zero delta to NO_ACTION.
```

The gap is not fixed by routing PM ADD directly to order generation. It must be solved at the target allocation layer.

## 7. Design Principles

- Expected Edge is forward-looking PIT expected value evidence, not profit/rank/cash alone.
- Incremental Investment Eligibility is evidence and Portfolio Construction input, not a new Action Authority.
- Cash remains a valid residual choice.
- Rank1 is strong evidence, not automatic ADD.
- Profit supports campaign health/no-loss-averaging evidence but is not sufficient for ADD.
- PM does not own target weight, quantity, pending, submit, or fill.
- Portfolio Construction decides target allocation across ADD, new BUY, and cash.
- Position Sizing realizes quantity delta from target allocation.
- Runtime Planning BUY_ADD mapping remains unchanged.
- Missing, stale, invalid, or future-dated evidence fails closed for ADD.

## 8. Authority Responsibility Matrix

| Component | Owns | Does Not Own |
|---|---|---|
| PM | Existing-position ADD intent and Expected Edge reasoning | Target weight, quantity, submit permission |
| Incremental Eligibility evidence | Edge improvement / incremental value / opportunity cost classification | Standalone ADD action |
| Portfolio Construction | Target membership, target weight, ADD/new BUY/cash allocation competition | Broker quantity, Runtime planning intent |
| Position Sizing | Target notional, target quantity, quantity delta, rounding/minimum review | PM action, target membership |
| Runtime Planning | Mapping quantity delta to BUY_ADD / NO_ACTION | Expected Edge, target weight, sizing formula |
| Safety / Approval / Submit | Block/review/approval/submit feasibility | Expected Edge optimization |
| Legacy ADD consumer | Telemetry-only compatibility if retained | Decision, quantity, pending, submit authority |

Machine-readable matrix:

```text
reports/phase28_b_incremental_investment_eligibility_and_canonical_add_allocation_design/authority_responsibility_matrix.json
```

## 9. Expected Edge Improvement Contract

Definition:

```text
Expected Edge Improvement means the same campaign has stronger forward-looking expected value evidence
at the current decision time than its most recent accepted PM decision baseline,
while remaining comparable and PIT-valid.
```

Comparison baseline:

| Priority | Baseline |
|---|---|
| Primary | Most recent accepted PM decision in the same campaign |
| Secondary | Entry decision Expected Edge baseline only when previous PM decision is unavailable and entry evidence is PIT-valid |
| Missing | `UNKNOWN_FAIL_CLOSED` |

Improvement states:

| State | ADD Effect |
|---|---|
| `IMPROVING` | PASS candidate |
| `STABLE_ADEQUATE` | PASS only if opportunity is superior and incremental value is positive |
| `WEAKENING` | FAIL |
| `INSUFFICIENT` | FAIL |
| `UNKNOWN` | FAIL closed |

Required PIT inputs include PM trace, opportunity ranking, Runtime Current, Portfolio Policy, and Market Context. Future performance, ADD-after return, backtest result, paper ledger PnL, future rank, and future market context are prohibited inputs.

## 10. Incremental Investment Value Contract

Definition:

```text
Incremental Investment Value is positive only when adding the proposed incremental notional
to an existing campaign improves portfolio expected value after marginal edge, risk,
opportunity cost, execution feasibility, cash, and concentration constraints.
```

Conceptual representation:

```text
additional_notional * expected_edge_evidence
- added_risk
- opportunity_cost
- execution_constraint_cost
```

This does not have to be implemented as one formula in Phase28-C. It must, however, classify:

```text
POSITIVE
NEUTRAL
NEGATIVE
UNKNOWN
```

ADD eligibility requires `POSITIVE`. `UNKNOWN` fails closed.

## 11. Portfolio Opportunity Cost Contract

Portfolio Opportunity Cost compares:

```text
Existing Position ADD
New Candidate BUY
Cash Retention
```

The comparison happens inside Portfolio Construction on a common PIT portfolio allocation value evidence scale. This scale may combine Expected Edge evidence, rank evidence, BUY Quality, Portfolio Fit, Market Context, concentration, and execution feasibility, but it is not a new external Action Authority.

Rules:

- Existing PM ADD competes with new BUY for the same capital.
- Cash retention remains valid when no candidate has positive incremental value.
- Ties should not force ADD.
- Missing input fails closed.
- ADD-specific separate ranking authority, fixed ADD capital buckets, and ADD count quotas are prohibited.

## 12. Concentration Risk Contract

Concentration is a risk constraint, not Action Authority. Phase28-B does not introduce a new hard concentration threshold. Portfolio Construction and Position Sizing must use existing Strategy / Safety caps and record projected post-ADD weight and concentration evidence.

ADD fails or reviews when post-ADD target weight or derived concentration violates existing policy/Safety evidence.

## 13. Capital Availability Contract

Cash and buying power are availability constraints:

```text
Cash available != ADD required
Cash unavailable -> no executable ADD
```

Capital Availability must distinguish:

- available cash
- required incremental notional
- post-trade cash
- minimum meaningful increment
- new BUY capital demand
- cash retention as valid allocation

## 14. PM ADD Eligibility Contract

PM ADD remains the entry point into ADD review, but PM ADD alone is insufficient for BUY_ADD.

Eligibility PASS requires:

```text
PM action == ADD
AND Expected Edge state is IMPROVING or qualified STABLE_ADEQUATE
AND Incremental Value is POSITIVE
AND Opportunity Cost passes
AND Campaign Continuation passes
AND Concentration passes
AND Capital Availability passes
AND Execution Feasibility is not BLOCK
```

Any required evidence missing, stale, invalid, future-dated, or non-comparable yields `UNKNOWN_FAIL_CLOSED`.

## 15. Portfolio Construction Target Weight Bridge

Bridge:

```text
PM ADD intent
+ Incremental Investment Eligibility PASS
+ Portfolio Opportunity Cost PASS
+ Concentration PASS
+ Capital Availability PASS
-> Portfolio Construction may increase target_weight above current_weight
```

Target weight semantics:

| Field | Meaning |
|---|---|
| `current_weight` | Current position market value / portfolio total equity |
| `desired_incremental_weight` | Portfolio Construction evidence output, bounded by policy/caps |
| `post_add_target_weight` | Current weight plus approved incremental target weight after normalization |
| `unchanged_target_weight` | Current weight when ADD fails or value is non-positive |
| `unknown_target_weight` | Review/fail-closed state, not silent zero success |

No fixed 5 positions, fixed cash 20%, fixed 850,000 JPY deployment, or fixed ADD amount is introduced.

## 16. Position Sizing Positive Delta Contract

Position Sizing receives target weight and current position state, then emits:

```text
target_notional
target_quantity_candidate
quantity_delta_candidate
rounding_result
minimum_executable_notional_result
reason_codes
```

Positive delta requires:

```text
post_add_target_weight > current_weight
AND target_notional - current_notional is meaningful
AND lot rounding preserves quantity_delta_candidate > 0
AND cash / buying power is sufficient
AND post-trade concentration and Safety pass
```

Zero-delta reason codes:

```text
ADD_TARGET_WEIGHT_UNCHANGED
ADD_TARGET_NOTIONAL_DELTA_ZERO
ADD_LOT_ROUNDING_ZERO
ADD_ALREADY_AT_TARGET
ADD_POSITION_SIZING_ZERO_DELTA
ADD_MINIMUM_INCREMENT_NOT_MET
```

## 17. Runtime Planning BUY_ADD Mapping

Runtime Planning contract is unchanged:

```text
existing position AND quantity_delta_candidate > 0 -> BUY_ADD
existing position AND quantity_delta_candidate = 0 -> NO_ACTION
```

Runtime Planning must not recalculate Expected Edge, rank, PM action, target weight, sizing, cash policy, Safety, or Submit.

## 18. Decision Trace

Trace contract:

```text
canonical_add_decision_trace.v1
DESIGNED_NOT_IMPLEMENTED
```

Required fields:

```text
business_date
symbol
campaign_id
current_position
current_weight
rank
PM action
PM reason
Expected Edge state
Expected Edge improvement state
Incremental Investment Value state
Opportunity Cost result
Concentration result
Capital availability result
target membership
current target weight
new target weight
target notional
target quantity
quantity delta
Runtime Planning action
planned quantity
pending item
fill
post-fill campaign state
```

Pre-trade decision trace is PIT-only. Post-fill campaign state is evaluation/ledger evidence only and must not become future input.

## 19. Reason Codes

Eligibility PASS examples:

```text
ADD_EDGE_IMPROVING_INCREMENTAL_VALUE_POSITIVE
ADD_EDGE_STABLE_HIGH_OPPORTUNITY_SUPERIOR
ADD_EXISTING_POSITION_TOP_OPPORTUNITY
ADD_OPPORTUNITY_COST_PASS
ADD_CONCENTRATION_PASS
ADD_CAPITAL_AVAILABLE
```

Eligibility FAIL examples:

```text
ADD_EDGE_NOT_IMPROVING
ADD_INCREMENTAL_VALUE_NON_POSITIVE
ADD_NEW_BUY_OPPORTUNITY_SUPERIOR
ADD_CASH_RETENTION_SUPERIOR
ADD_CONCENTRATION_CONSTRAINT
ADD_CAPITAL_UNAVAILABLE
ADD_MINIMUM_INCREMENT_NOT_MET
ADD_REQUIRED_EVIDENCE_MISSING
ADD_EDGE_UNKNOWN
ADD_CAMPAIGN_CONTINUATION_NOT_CONFIRMED
```

Downstream zero examples:

```text
ADD_TARGET_WEIGHT_UNCHANGED
ADD_TARGET_NOTIONAL_DELTA_ZERO
ADD_LOT_ROUNDING_ZERO
ADD_ALREADY_AT_TARGET
ADD_POSITION_SIZING_ZERO_DELTA
```

## 20. Failure Contract

Principle:

```text
Evidence不足
-> ADD不成立
-> existing layer emits NO_ACTION or REVIEW_REQUIRED according to existing authority
```

Examples:

| Failure | Layer | Behavior |
|---|---|---|
| Missing Expected Edge | PM / Portfolio Construction | `ADD_EDGE_UNKNOWN`, fail closed |
| Stale Expected Edge | PM / Portfolio Construction | `ADD_STALE_EXPECTED_EDGE_INPUT`, review |
| Future-dated input | Any | review or halt per temporal authority |
| Missing current quantity | Position Sizing | review |
| Missing target weight | Position Sizing | review, no silent zero success |
| Runtime Planning mismatch | Runtime Planning | review |
| Legacy/canonical overlap | Planning authority | review or block |

## 21. PIT and Temporal Authority

All ADD eligibility and allocation evidence must be business-date PIT. Prohibited as Action inputs:

- future performance
- ADD-after returns
- backtest / historical result
- paper ledger PnL
- realized PnL outcome
- selected/bought result
- future rank
- future market context
- future price

These may be used only for Phase28-D evaluation.

## 22. Observability Requirements

Phase28-C must expose:

- PM ADD decision id and campaign id
- Expected Edge baseline reference and current reference
- Expected Edge improvement state
- Incremental Value state
- Opportunity Cost result
- target weight before/after
- target notional before/after
- quantity delta and zero reason
- Runtime Planning BUY_ADD / NO_ACTION mapping
- pending/fill references when executable
- post-fill ADD outcome only in evaluation artifacts

## 23. Phase28-C Minimal Implementation Candidate

Primary Recommendation:

```text
Implement one canonical ADD allocation bridge:
when PM ADD has PIT-valid Expected Edge Improvement and Incremental Investment Value PASS,
Portfolio Construction may increase target_weight above current_weight within existing policy/cap constraints,
allowing Position Sizing to emit positive quantity_delta_candidate and Runtime Planning to emit BUY_ADD.
```

Included:

- additive ADD eligibility evidence resolution
- Portfolio Construction target-weight bridge for PM ADD
- Position Sizing trace fields for positive/zero ADD delta reasons
- Runtime Planning trace preservation only if needed to expose the existing mapping

Excluded:

- BUY Quality threshold changes
- Market Context threshold changes
- Portfolio Fit formula redesign
- Corporate Event gate changes
- HOLD / REDUCE / EXIT changes
- cash deployment rule changes
- new concentration cap
- new position-count rule
- fixed exposure rule
- legacy ADD executable revival
- model retraining

## 24. Deferred Improvements

Deferred to later phases:

- BUY Quality input expansion
- Market Context input expansion
- Portfolio Fit formula redesign
- Corporate Event ADD gate
- HOLD / REDUCE / EXIT boundary changes
- new concentration cap calibration
- model retraining
- cash exposure target redesign
- re-entry redesign

## 25. Phase28-D Acceptance Contract

Test owner:

```text
User/operator runs 100BD Historical.
Codex may run only short regression / read-only analysis.
```

Baseline preference:

```text
runtime-test-historical-smoke-20260804T074611098414Z
```

D6-D After comparability limitations must be disclosed when used.

Primary metrics:

- Return
- Total PnL
- Profit Factor
- Average Winner
- Average Loser
- Win Rate
- Maximum Drawdown
- Turnover

ADD metrics:

- PM ADD intent count
- BUY_ADD count
- ADD submit count
- ADD fill count
- ADD execution rate
- Zero Delta count
- Zero Quantity count
- ADD target weight increase count
- ADD positive quantity delta count
- Rank1 existing-position ADD rate
- Rank top-N existing-position ADD rate
- ADD after 1D / 3D / 5D / 10D outcome
- ADD campaign continuation
- ADD followed by REDUCE / EXIT
- ADD contribution to realized / unrealized PnL

Capital and behavior metrics:

- Average / final cash ratio
- Average / final invested ratio
- Top1 / Top3 concentration
- ADD deployed capital
- New BUY deployed capital
- Capital left unused after eligible ADD
- Holding duration
- Re-entry count
- Campaign attribution
- Position turnover
- Number of holdings

Adoption judgments:

```text
ADOPT
ADOPT_WITH_LIMITATIONS
REJECT_NO_MEANINGFUL_IMPROVEMENT
REJECT_RISK_REGRESSION
REJECT_ARCHITECTURE_VIOLATION
REVIEW_REQUIRED_COMPARABILITY_LIMITATION
```

Return improvement alone must not automatically adopt. Minimum adoption requires executable BUY_ADD, rational reduction in zero delta/zero quantity, Capital Efficiency improvement, no severe risk regression, no canonical authority violation, and traceable ADD contribution.

## 26. Risks

- If PM ADD is directly converted to orders, quantity authority is duplicated.
- If Rank1 becomes automatic ADD, Expected Edge SoT is violated.
- If cash availability becomes deployment pressure, Strategy SoT is violated.
- If multiple gates or thresholds change in Phase28-C, attribution becomes non-comparable.
- If Legacy ADD consumer regains executable behavior, canonical authority is violated.

## 27. Architecture Conformance Review

The design conforms because:

- PM remains existing-position intent authority only.
- Portfolio Construction owns target allocation.
- Position Sizing owns quantity delta.
- Runtime Planning mapping is unchanged.
- Safety / Approval / Submit remain downstream constraints.
- Legacy ADD executable authority is not revived.
- Production / Demo / Historical common Runtime is preserved.
- Missing evidence fails closed.
- Historical-only logic and test-only fallback are prohibited.

## 28. Final Judgment

Primary Judgment:

```text
PHASE28_B_INCREMENTAL_INVESTMENT_ELIGIBILITY_DESIGN_COMPLETE_PHASE28_C_READY
```

Secondary Judgments:

```text
DESIGNED_NOT_IMPLEMENTED
PHASE28_C_SINGLE_PERFORMANCE_CHANGE_SELECTED
PM_REMAINS_INTENT_AUTHORITY_NO_QUANTITY_AUTHORITY
PORTFOLIO_CONSTRUCTION_OWNS_ADD_TARGET_WEIGHT_BRIDGE
POSITION_SIZING_OWNS_POSITIVE_DELTA_REALIZATION
RUNTIME_PLANNING_BUY_ADD_MAPPING_UNCHANGED
```

## 29. Phase28-C Entry Decision

```text
APPROVED
```

Phase28-C is approved for implementation of the single recommended change only. It must not combine BUY Quality, Market Context, Portfolio Fit, Corporate Event, HOLD / REDUCE / EXIT, cash deployment, concentration cap, position count, model retraining, or Legacy ADD changes into the same performance experiment.
