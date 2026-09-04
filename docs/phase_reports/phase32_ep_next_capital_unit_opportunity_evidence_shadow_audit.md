# Phase32-EP — Next-Capital-Unit Opportunity Evidence SHADOW Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Primary period: `2024-07-01` through `2024-12-18`
- Comparison period: `2023-03-01` through `2023-06-30`
- Run evidence coverage at audit time: `2022-10-03` through `2024-12-18`, `545` completed business days
- Run state inspected read-only: `RUNNING`

This audit asks whether decision-time / PIT evidence can identify candidates with stronger relative next-capital-unit support than the candidates Production actually capitalized. It does not ask whether those candidates later went up, and it does not treat Phase32-EO / EN capitalization findings as a Production defect.

## Evidence Sources

Existing run artifacts only:

- `daily/*/strategy/buy_quality_decisions.json`
- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/market_context.json`
- `daily/*/strategy/runtime_planning.json`
- `daily/*/execution/fills.json`
- `daily/*/positions/position_campaigns.json`
- Prior Phase32 reports EO and EN for already-established context

No new SHADOW artifact was written. The next-capital-unit score below is a report-local diagnostic reconstruction from already-materialized PIT fields.

## Candidate Evidence Available For Next-Capital-Unit Comparison

The current artifacts already contain enough decision-time fields to build a relative next-capital-unit evidence view:

| Evidence family | Representative fields observed |
| --- | --- |
| BQ / rank | `quality_score`, `quality_action`, `quality_band`, `opportunity_buy_rank`, `input_opportunity_rank`, `candidate_rank_tick_reliability` |
| Momentum / continuation | `momentum_confidence_state`, `momentum_trajectory_*`, `tick_normalized_trend_state`, `component_scores`, `component_statuses` |
| Entry | `entry_admission`, `entry_admission_action`, `entry_admission_state`, `entry_admission_evidence_sufficiency` |
| Expected edge | `expected_edge_baseline_score`, `expected_edge_improvement_state`, expected-edge reason codes |
| Downside / risk | `downside_risk_state`, no-buy reason classification, risk reason codes |
| Relationship | `membership_intent`, `opportunity_type`, `competitor_type`, `current_position`, `current_position_campaign_id` |
| ADD / incremental | `add_investment_evidence`, `add_allocation_eligibility_status`, `incremental_investment_value_state`, `desired_incremental_weight` |
| REENTRY | REENTRY reason codes, cooldown / recovery / churn / new-thesis evidence fields |
| Headroom / concentration | `cap_headroom_weight`, `concentration_headroom_weight`, `current_weight`, `current_target_weight`, cap reason fields |
| Market / risk state | `final_regime` / `regime_state`, `risk_pacing_intent`, deployment state |

These fields are all decision-time artifacts. No future price, later return, final campaign PnL, MFE/MAE, or later SELL outcome was used.

## SHADOW Diagnostic Definition

For audit only, a non-persistent `next_capital_unit_score` was reconstructed from:

- BQ quality score
- rank-normalized opportunity position
- FULL vs REDUCED vs WAIT/REJECT action
- Entry state modifiers
- expected-edge evidence
- downside / risk evidence
- relationship / ADD / REENTRY modifiers
- concentration/headroom
- market regime / risk-pacing context

The score intentionally does not use:

- future return
- future price
- campaign outcome
- final PnL
- realized MFE/MAE
- Production target weight as an input to score
- actual BUY/fill result as an input to score

Production target/fill evidence was used only after scoring to compare which candidates were capitalized versus left uncapitalized.

### Not A Production Score Copy

The diagnostic is not a simple copy of Production ranking:

- It combines BQ/rank with Entry/risk/headroom/relationship modifiers.
- It does not use `target_weight` or actual BUY as positive score features.
- It can rank candidates with `target_weight=0` above candidates that Production bought.
- It is report-local and has no Production consumer.

## Period-Level SHADOW Metrics

| Metric | 2023 Mar-Jun strong growth | 2024 Jul-Dec stagnation |
| --- | ---: | ---: |
| PC days analyzed | 84 | 117 |
| Avg candidates per day | 52.821 | 52.735 |
| Avg BQ-positive candidates per day | 42.012 | 42.923 |
| Avg BQ-positive uncapitalized per day | 33.357 | 37.581 |
| Avg PC capitalized members per day | 13.143 | 9.103 |
| Avg top-10 SHADOW candidates absent from Production top-20 capitalized set | 6.583 | 8.205 |
| Days with material top-10 divergence | 72 / 84 | 117 / 117 |
| Avg top-10 capitalized | 3.869 | 2.231 |
| Avg top-10 uncapitalized | 6.131 | 7.769 |
| Avg top-10 actually bought | 0.440 | 0.222 |

Interpretation:

- Strong BQ-positive evidence exists in both periods.
- 2024 Jul-Dec has similar candidate population and BQ-positive availability, but materially fewer candidates receive PC capital and fewer top-10 SHADOW candidates are actually bought.
- Rank divergence is therefore not just a generic artifact of a large universe; it becomes broader in the stagnation period.

## Selected / Bought Opportunity Comparison

Actual BUY fills matched back to same-day PC/BQ evidence:

| Metric | 2023 Mar-Jun | 2024 Jul-Dec |
| --- | ---: | ---: |
| Actual BUY fills | 135 | 156 |
| Days with BUY fills | 71 | 89 |
| Avg bought SHADOW score | 0.514 | 0.432 |
| Avg bought BQ quality | 0.625 | 0.570 |
| Avg bought opportunity rank | 25.356 | 32.667 |
| Days where stronger BQ-positive uncapitalized candidates existed above the weakest bought candidate | 70 / 71 | 87 / 89 |
| Stronger uncapitalized candidates above bought threshold | 977 | 1,840 |

This supports a material Production-vs-SHADOW rank divergence:

- 2024 still bought securities, but bought evidence was weaker by the report-local next-capital-unit diagnostic.
- Stronger uncapitalized rows were more numerous in 2024, averaging about `20.7` per BUY day versus about `13.8` per BUY day in the 2023 strong-growth period.
- This does not prove Production should have bought those rows; it proves current PIT evidence can distinguish a relative opportunity set that Production did not fully capitalize.

## A / B / C Comparison

### A. BQ-Upper / Production-Capitalized

Observed in both periods:

- Retained positions and some new BUY targets with high BQ / rank evidence.
- 2023 had more PC capitalized members per day and more top-10 SHADOW candidates represented in the capitalized set.
- 2024 still had some high-scoring capitalized rows, especially retained positions such as `94320`, but new incremental deployment was thinner.

### B. BQ-Upper / Weakly Capitalized

Observed in both periods, materially more pronounced in 2024:

- 2023 strong uncapitalized score >= 0.56: `780`
- 2024 Jul-Dec strong uncapitalized score >= 0.56: `1,157`

Primary explanations:

| Reason | 2023 Mar-Jun | 2024 Jul-Dec |
| --- | ---: | ---: |
| `CAPITAL_COMPETITION` | 296 | 343 |
| `REENTRY_SUPPRESSION` | 262 | 527 |
| `RELATIONSHIP_SUPPRESSION` | 222 | 287 |

Representative 2024 rows:

- `2024-12-05 58030`: FULL, quality `0.795258`, rank `2`, target zero, `ADD_CANDIDATE`, relationship suppression.
- `2024-12-09 58030`: FULL, quality `0.789056`, rank `3`, target zero, `ADD_CANDIDATE`, relationship suppression.
- `2024-11-12 70130`: FULL, quality `0.763041`, rank `7`, target zero, `ADD_CANDIDATE`, REENTRY suppression.
- `2024-12-13 67400`: REDUCED, quality `0.810186`, rank `1`, target zero, `ADD_CANDIDATE`, relationship suppression.
- `2024-09-05 67400`: REDUCED, quality `0.818665`, rank `2`, target zero, `EXCLUDE`, capital competition.

### C. Actually Bought But Relatively Weaker

Observed more clearly in 2024:

- 2024 average bought quality dropped to `0.570` from `0.625`.
- 2024 average bought opportunity rank weakened to `32.667` from `25.356`.
- 2024 top-10 SHADOW candidates were actually bought less often (`0.222` per day versus `0.440`).

This is a capitalization-character difference, not an execution defect. EO already found no broad post-PC execution loss, and EP found no evidence that Submit/Execution selectively removed higher-scored planned BUYs.

## Uncapitalized Reason Classification

Rows were not labeled clean unexplained merely because they scored highly. Each uncapitalized row retained a contemporaneous reason class.

Reason classes used:

- `VALID_RISK_SUPPRESSION`
- `ENTRY_CAUTION`
- `RELATIONSHIP_SUPPRESSION`
- `REENTRY_SUPPRESSION`
- `INCREMENTAL_JUSTIFICATION_FAILURE`
- `CAP_OR_HEADROOM`
- `CAPITAL_COMPETITION`
- `GENUINELY_WEAK_EVIDENCE`
- `OTHER_EXPLAINED`

For stronger uncapitalized candidates above same-day bought threshold:

| Reason | 2023 Mar-Jun | 2024 Jul-Dec |
| --- | ---: | ---: |
| `VALID_RISK_SUPPRESSION` | 48 | 632 |
| `REENTRY_SUPPRESSION` | 227 | 448 |
| `CAPITAL_COMPETITION` | 415 | 442 |
| `RELATIONSHIP_SUPPRESSION` | 257 | 306 |
| `ENTRY_CAUTION` | 2 | 1 |
| `GENUINELY_WEAK_EVIDENCE` | 4 | 3 |
| `OTHER_EXPLAINED` | 24 | 8 |

Interpretation:

- 2024 divergence is much more risk-mediated and REENTRY-mediated.
- Capital competition and relationship suppression existed in the 2023 growth period too, but 2024 adds a larger defensive/risk layer and a larger REENTRY suppression layer.
- There is no need to invent a clean unexplained category: the rows are explained, but the explanations identify where capital is being withheld.

## ADD-Specific Audit

Known EO facts:

- 2023 Mar-Jun PC positive ADD: `5`
- 2024 Mar18-Dec PC positive ADD: `0`

EP ADD/current-position diagnostic:

| Metric | 2023 Mar-Jun | 2024 Jul-Dec |
| --- | ---: | ---: |
| ADD/current candidate rows | 2,617 | 3,739 |
| Strong ADD/current uncapitalized rows | 739 | 1,029 |
| Top reason: relationship suppression | 416 | 482 |
| Top reason: REENTRY suppression | 262 | 527 |
| Incremental justification failure | 29 | 4 |
| Entry caution | 32 | 16 |

ADD judgment:

- `ADD_OPPORTUNITY_GAP_OBSERVED = YES`
- The gap is not "ADD should be increased"; it is that existing PIT evidence can identify current/relationship candidates with strong next-capital-unit support, while Production ADD remains essentially absent after March.
- The primary suppression is relationship/REENTRY and capital allocation semantics rather than execution or missing evidence.
- No correctness defect is proven because the suppression has contemporaneous reason-code support and EN found zero clean unexplained BQ-positive target-zero cases through the focused post-March window.

## 2023 vs 2024 Interpretation

### 2023 Strong Growth

- Strong BQ-positive evidence existed.
- Production capitalized more PC members and more top-10 diagnostic candidates.
- Average bought rank/quality was stronger.
- Risk posture allowed broader deployment.
- ADD was small but non-zero.

### 2024 Late Stagnation

- BQ-positive and top-quality evidence still existed, so this is not pure opportunity scarcity.
- Risk defensiveness was much more active.
- Top diagnostic opportunities more often remained target-zero or non-bought.
- Actual BUYs skewed toward weaker rank/quality.
- ADD disappeared despite many ADD/current candidate rows with strong diagnostic evidence.
- REENTRY and relationship suppression explain a large part of the uncapitalized stronger set.

## Production Repair Justified

`NO`

Reason:

- EP proves that a useful SHADOW diagnostic signal exists, not that Production violated a contract.
- The uncapitalized higher-score rows are explained by valid contemporaneous Production semantics: risk, Entry, REENTRY, relationship, incremental justification, and capital competition.
- Changing these would be Strategy/PC design work. It is not a correctness repair justified by this audit.

## Recommended Follow-Up

Proceed with a SHADOW-only design for a persisted `next_capital_unit_opportunity_evidence` artifact that:

- remains action-neutral,
- explicitly separates risk suppression from relationship suppression,
- compares NEW / ADD / REENTRY on the next unit of capital,
- records why a stronger diagnostic candidate was not capitalized,
- has `authoritative_consumer_count=0` until separately accepted.

The key follow-up question:

`Can a persisted action-neutral next-capital-unit artifact improve observability of late-2024 capital withholding without changing Production behavior or using future outcomes?`

## Required Final Answers

- `NEXT_CAPITAL_UNIT_SIGNAL_EXISTS = YES`
- `PRODUCTION_VS_SHADOW_RANK_DIVERGENCE = MATERIAL`
- `2024_CAPITALIZATION_GAP_FURTHER_SUPPORTED = YES`
- `ADD_OPPORTUNITY_GAP_OBSERVED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`

## No-Mutation Confirmation

- `PRODUCTION_CHANGED: NO`
- `SHADOW_CHANGED: NO`
- `TARGET_RUN_MUTATED: NO`
- `RUNTIME_STATE_MUTATED: NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO`

## Final Judgment

`PHASE32_EP_NEXT_CAPITAL_UNIT_SIGNAL_EXISTS_PRODUCTION_VS_SHADOW_RANK_DIVERGENCE_MATERIAL_2024_CAPITALIZATION_GAP_SUPPORTED_ADD_OPPORTUNITY_GAP_OBSERVED_NO_PRODUCTION_REPAIR`
