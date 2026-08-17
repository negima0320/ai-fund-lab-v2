# Phase30-AK1R - QUALITY_DEFERRED_TO_CASH Decision Evidence Root-Cause Audit

## Scope

Task ID: `Phase30-AK1R`

Task type: `READ_ONLY_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T121454359538Z
```

The run was not stopped, resumed, replayed, repaired, or mutated. No Strategy,
Runtime, config, threshold, cap, lot, Candidate, Accepted Generation, or model
change was made.

Audit freeze from run state at AK1R audit start:

```text
AUDIT_CUTOFF_DATE = 2023-10-04
COMPLETED_BUSINESS_DAYS = 284
```

The run had advanced beyond the Phase30-AK1 cutoff. AK1R uses this AK1R freeze
only.

## Primary Judgment

```text
CASH_DEFERRAL_PRIMARY_CLASS = MULTI_CAUSAL
CASH_DEFERRAL_SECONDARY_CLASSES =
  JUSTIFIED_QUALITY_REJECTION
  OVER_CONSERVATIVE_POLICY
  RESIDUAL_CAPITAL_RECYCLING_GAP
  OBSERVABILITY_GAP
```

Strict `VALID_OPPORTUNITY_BUT_CASH` was not found. Under decision-time evidence,
there was no symbol-day satisfying all of:

- investable semantic hybrid class,
- STRONG / VALID surface,
- Buy Quality not reject,
- Entry acceptable,
- Downside Risk acceptable,
- PC positive target,
- one-lot executable,
- cash sufficient,
- Strategy and Safety cap clear,
- no pending/lifecycle conflict,
- PS final quantity still zero.

Therefore this audit does not justify forced investment, fixed exposure, fixed
position count, or Quality / Entry threshold relaxation.

However, `QUALITY_DEFERRED_TO_CASH` is too coarse. It mixes weak/caution
candidate deferral, PC no-positive-increment, one-lot overshoot versus small PC
target, and quality-adjusted cash preference into one label.

## Population

Canonical all-PS `QUALITY_DEFERRED_TO_CASH` population through cutoff:

```text
QUALITY_DEFERRED_POPULATION_COUNT = 13,923
```

Detailed AK1R candidate-cash audit population:

```text
BUY_NEW / REENTRY new-candidate QUALITY_DEFERRED rows = 11,471
```

Semantic distribution:

| Semantic / PM / Position / Intent | Count |
| --- | ---: |
| BUY_NEW / HOLD / NEW_POSITION / EXCLUDE | 4,964 |
| BUY_NEW / NEW / NEW_POSITION / ADD_CANDIDATE | 4,089 |
| REENTRY / NEW / NEW_POSITION / ADD_CANDIDATE | 2,418 |
| REENTRY / HOLD / NEW_POSITION / EXCLUDE | 1,472 |
| NOT_APPLICABLE / HOLD / EXISTING_POSITION / RETAIN | 445 |
| NOT_APPLICABLE / REDUCE / EXISTING_POSITION / REDUCE_CANDIDATE | 270 |
| BUY_ADD / ADD / EXISTING_POSITION / RETAIN | 265 |

## Candidate / Quality Distribution

Within the detailed BUY_NEW / REENTRY audit population:

```text
QUALITY_WEAK_DEFERRED_COUNT = 8,253
QUALITY_ACCEPTABLE_BUT_CASH_COUNT = 3,218
CAUTION_EXPLAINS_CASH_DEFERRAL_RATE = 1.0000
```

This means every audited `QUALITY_DEFERRED_TO_CASH` case carried caution in
selection quality, entry state, or candidate surface evidence. Some candidates
were acceptable enough to reach PC-positive competition, but none met the full
strict valid/executable/no-conflict cash-suspicion definition.

## Entry / Risk Distribution

```text
ENTRY_PASS_BUT_CASH_COUNT = 10,581
RISK_PASS_BUT_CASH_COUNT = 11,471
ENTRY_AND_RISK_PASS_BUT_CASH_COUNT = 10,581
```

Entry/Risk PASS alone is not sufficient BUY authority. Many rows still had
caution quality semantics, small target weights, one-lot concentration friction,
or residual cash preference.

## VALID_OPPORTUNITY_BUT_CASH

```text
VALID_OPPORTUNITY_BUT_CASH_COUNT = 0
VALID_OPPORTUNITY_BUT_CASH_RATE = 0.0000
VALID_OPPORTUNITY_CASH_DOMINANT_REASON = NONE
```

No high-interest case satisfied all required quality, entry, risk, cash, cap,
one-lot, PC-positive, and no-conflict conditions while remaining PS final zero.

## Exact Cash Deferral Reasons

For the full detailed population, cash decisions were explainable by
machine-readable evidence:

```text
CASH_DECISION_EXPLAINABLE_RATE = 1.0000
UNEXPLAINED_CASH_DECISION_COUNT = 0
```

Dominant reason themes:

- selection or entry caution,
- PC no positive increment,
- one-lot overshoot versus small target,
- quality-adjusted policy preference for Cash,
- residual capital not force-deployed.

Because `VALID_OPPORTUNITY_BUT_CASH_COUNT = 0`, there is no exact dominant
reason for a strict valid-but-cash subset.

## Taxonomy Quality

```text
QUALITY_DEFERRED_TO_CASH_TAXONOMY = TOO_COARSE
```

The label is not false, but it is too broad for root-cause work. It should be
split in a future observability repair into labels such as:

- `SELECTION_OR_ENTRY_CAUTION_DEFERRED_TO_CASH`,
- `PC_NO_POSITIVE_INCREMENT_DEFERRED_TO_CASH`,
- `ONE_LOT_OVERSHOOT_DEFERRED_TO_CASH`,
- `QUALITY_ADJUSTED_RESIDUAL_CASH`,
- `RESIDUAL_RECYCLING_EXHAUSTED_TO_CASH`.

No Strategy behavior change is implied by this taxonomy finding.

## PC Positive but Final Zero

```text
PC_POSITIVE_BUT_FINAL_ZERO_COUNT = 3,948
```

This is the most important actionable observation. PC-positive does not
guarantee PS executable quantity. The distinguishing friction is usually small
PC target/increment versus one-lot notional, plus quality-adjusted cash
preference.

## One-Lot Executable but Cash

```text
POLICY_AND_SAFETY_ONE_LOT_EXECUTABLE_BUT_CASH_COUNT = 3,319
```

This confirms that some zero outcomes are not physical lot impossibility.
However, they still did not satisfy the full strict valid-opportunity definition
because caution, target size, lifecycle/pending, or policy preference evidence
remained.

## Cash Availability

```text
CASH_SUFFICIENT_BUT_DEFERRED_COUNT = 11,097
```

Cash insufficiency is not the dominant explanation. Cash may be available while
Strategy still chooses not to deploy it when marginal quality / target / one-lot
evidence is insufficient.

## Strategy / Safety Cap Headroom

```text
BOTH_CAPS_CLEAR_BUT_DEFERRED_COUNT = 3,319
STRATEGY_CONCENTRATION_CAP_PRESERVED = YES
SAFETY_HARD_CAP_PRESERVED = YES
WINNER_CONCENTRATION_POLICY_CHANGE_PROPOSED = NO
```

Safety/Strategy cap clear is necessary but not sufficient. Phase30-W's contract
is preserved: Safety pass alone must not force one-lot concentration.

## Opportunity Cost

```text
OPPORTUNITY_COST_PASS_BUT_CASH_COUNT = 0
OPPORTUNITY_COST_IS_DOMINANT_CASH_REASON = NO
```

In the audited BUY_NEW / REENTRY cash-deferred rows, Opportunity Cost PASS did
not explain a strict valid-cash population because that population was empty.

## Residual Capital Recycling

```text
RESIDUAL_RECYCLING_ATTEMPTED_FOR_VALID_CASH_CASES = PARTIAL
RESIDUAL_RECYCLING_EXHAUSTION_REASON =
quality_adjusted_lot_aware_rebatch can allocate to other candidates, but valid
PC-positive zero rows often return residual to Cash when one-lot
overshoot/quality-adjusted priority is not strong enough
```

Residual recycling is visible, but row-level destination remains only partially
explainable. This supports an observability repair before any Strategy behavior
repair.

## Portfolio Competition

```text
CASH_AFTER_COMPETITION_WITHOUT_ALTERNATIVE_ALLOCATION_COUNT = 0
COMPETITION_LOSS_WITHOUT_WINNER_ALLOCATION_COUNT = 0
```

No low/high interest day showed strict valid unused opportunity with zero actual
BUY. Portfolio competition did not produce an unexplained valid-candidate cash
case under the strict definition.

## Cash Competitor Contract

```text
CASH_COMPETITOR_CONTRACT =
Cash is residual competitor/result; no forced exposure/count. Positive
opportunity may lose to Cash when quality, entry, opportunity cost, one-lot
concentration, cap/lot feasibility, or residual recycling evidence does not
support marginal JPY deployment.
```

This conforms to the durable architecture: Cash is valid when opportunity
quality or executable marginal allocation is not strong enough.

## Cash vs Successful BUY

```text
PRIMARY_BUY_VS_CASH_DISCRIMINATOR =
PC_INCREMENTAL_TARGET_AND_LOT_AWARE_PRIORITY

POTENTIAL_POLICY_INCONSISTENCY = NO
```

Successful BUYs share positive PS final quantity and Runtime intent. Cash
deferred cases generally have smaller/less decisive PC increments, caution
semantics, or one-lot/quality-adjusted priority friction.

## Low-Position Days

```text
LOW_POSITION_DAYS_WITH_VALID_UNUSED_OPPORTUNITY = 0
LOW_POSITION_DAYS_EXPLAINED_BY_NO_QUALITY_OPPORTUNITY = 126
```

Low position count days were not explained by ignored strict valid executable
opportunities.

## High-Cash Days

High-cash day counts:

```text
Cash >= 60%: 165
Cash >= 70%: 110
Cash >= 80%: 13
```

Strict valid executable unused opportunity on high-cash days:

```text
HIGH_CASH_DAYS_WITH_VALID_EXECUTABLE_OPPORTUNITY = 0
```

High cash alone is not a failure condition under the Strategy philosophy.

## Zeroed Capital Destination

```text
ZEROED_CAPITAL_DESTINATION_DISTRIBUTION = {
  "remained Cash": 11471,
  "allocated to another BUY_NEW": "PARTIAL_DAY_LEVEL_NOT_ROW_TRACEABLE",
  "allocated to ADD": 0,
  "unknown": 0
}
```

This is a row-level observability limitation. The artifacts explain why the row
did not buy, but do not always preserve a complete row-level residual-capital
destination chain.

## Investment Philosophy Conformance

```text
CASH_POLICY_CONFORMS_TO_INVESTMENT_PHILOSOPHY = PARTIAL
```

The behavior conforms in that no strict valid opportunity was ignored and Cash
is not being treated as a failure. It is only partial because taxonomy and
residual-destination observability are too coarse for confident future repair
design.

## Runtime / Authority Integrity

```text
CASH_DEFERRAL_RUNTIME_DEFECT = NO
CASH_DEFERRAL_AUTHORITY_DEFECT = YES
```

The authority defect is an observability/taxonomy authority gap, not a proven
Runtime execution defect. AK1's submit guard issue is downstream of Runtime BUY
intent and is separate from PC/PS Cash decisions.

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
200BD_RESULT_USED_FOR_PARAMETER_SELECTION = FALSE
FUTURE_RETURN_USED_FOR_CASH_JUDGMENT = FALSE
```

## Run Treatment

```text
200BD_RUN_TREATMENT = 200BD_RUN_CONTINUE_FOR_DIAGNOSTIC_ONLY
```

Codex did not stop the run.

## Deliverables

Summary JSON:

```text
reports/phase_reports/phase30_ak1r_quality_deferred_to_cash_decision_evidence_root_cause_audit.json
```

Evidence directory:

```text
reports/phase_reports/phase30_ak1r/
```

Generated evidence files:

```text
quality_deferred_population.json
cash_defer_quality_cross_tab.json
valid_opportunity_but_cash.json
cash_defer_root_cause_distribution.json
pc_positive_final_zero_analysis.json
one_lot_executable_cash_analysis.json
cash_availability_analysis.json
cap_headroom_analysis.json
opportunity_cost_cash_cross_tab.json
residual_recycling_cash_analysis.json
portfolio_competition_cash_analysis.json
cash_competitor_contract.json
cash_explainability_analysis.json
representative_cash_sentinels.json
cash_vs_successful_buy_comparison.json
low_position_day_analysis.json
high_cash_day_analysis.json
zeroed_capital_destination.json
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK1R
FORCED_INVESTMENT_REQUIRED = NO
FIXED_EXPOSURE_TARGET_REQUIRED = NO
FIXED_POSITION_COUNT_REQUIRED = NO
```

## Recommended Next Task

```text
Phase30-AK2 - Cash Decision Evidence / Taxonomy Observability Repair
```

Do not start with Strategy loosening. The next task should make Cash decisions
more specifically explainable before considering any behavior change.
