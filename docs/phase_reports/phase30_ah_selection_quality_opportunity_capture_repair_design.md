# Phase30-AH - Selection Quality / Opportunity Capture Repair Design

Task ID: `Phase30-AH`

Boundary:

```text
DESIGN_ONLY
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-AH
NO_HISTORICAL_OUTCOME_FIT
NO_THRESHOLD_OPTIMIZATION
NO_BULL_BEAR_MULTIPLIER_CHANGE
NO_MINIMUM_POSITIONS
NO_MINIMUM_EXPOSURE
NO_CASH_CAP
NO_FORCED_INVESTMENT
NO_MODEL_RETRAINING
NO_NEW_AI
NO_RUNTIME_AUTHORITY_CHANGE
```

Primary evidence:

```text
docs/phase_reports/phase30_ag_selection_coverage_capital_utilization_design_audit.md
docs/phase_reports/phase30_af_60bd_selection_winner_capital_regime_attribution_audit.md
docs/phase_reports/phase30_aa_existing_data_component_utilization_gap_audit.md
docs/02_architecture/strategy_intelligence_architecture_v1.md
reports/phase_reports/phase30_ag/
```

Deliverables:

```text
docs/phase_reports/phase30_ah_selection_quality_opportunity_capture_repair_design.md
reports/phase_reports/phase30_ah_selection_quality_opportunity_capture_repair_design.json
reports/phase_reports/phase30_ah_selection_logic_inventory.json
```

## Primary Judgment

```text
SELECTION_QUALITY_COMPARATOR_DESIGN = COMPLETE
OPPORTUNITY_RANK_ROLE = SUPPORTING
EXPECTED_EDGE_ROLE = UNCALIBRATED_SUPPORTING
MARKET_CAUTION_INDIVIDUAL_QUALITY_DESIGN = COMPLETE
CAPITAL_UTILIZATION_DESIGN = COMPLETE
PARALLEL_SELECTION_PATH_CREATED = NO
ONE_PRODUCTION_SELECTION_PATH = YES
PHASE30_AI_IMPLEMENTATION_READY = YES
```

Phase30-AH designs a Production-common repair using existing PIT data and
existing components. It does not create a new Selection engine. The repair is a
change in how existing Ranking / BUY Quality / Strategy Intelligence /
Portfolio Construction evidence is compared and consumed.

## Current Selection Root Cause

Phase30-AG confirmed:

```text
MARKET_OPPORTUNITY_CAPTURE = PARTIAL
SELECTION_RANKING_EFFECTIVENESS = PARTIAL
SELECTION_IMPROVEMENT_AVAILABLE_WITH_EXISTING_DATA = YES
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
```

The root cause is not Runtime. The current Production path surfaces only a very
small fraction of market-wide PIT healthy structures into PS-positive
deployment:

```text
healthy_proxy_count = 416.545/day
selected_healthy_proxy_count = 3.076/day
ps_positive_healthy_proxy_count = 0.121/day
```

Dominant drop reasons:

```text
PC:
below_opportunity_top20|non_positive_expected_edge_score
non_positive_expected_edge_score

PS:
RESOLVED_ZERO_DELTA
```

The design problem is opportunity rank / uncalibrated score dominance. Good PIT
structure can be under-consumed when it is not high enough by legacy rank/score
or when `expected_edge_score` is treated too much like a rejection authority
despite remaining uncalibrated.

## Selection Quality Comparator

AH introduces a Selection Quality Comparator as an existing-path evidence layer,
not a parallel engine.

Owner and consumers:

```text
Producer surface: Strategy Intelligence / BUY Quality evidence
First allocation consumer: Portfolio Construction
Quantity consumer: Position Sizing only after PC target exists
Runtime: pure mapper, no Selection authority
```

Semantic tiers:

```text
HIGH_QUALITY_CONTINUATION
VALID_CONTINUATION
CAUTION_CONTINUATION
INSUFFICIENT_QUALITY
REJECT
```

Tier meanings:

| Tier | Meaning |
|---|---|
| `HIGH_QUALITY_CONTINUATION` | Trend, persistence, acceleration/participation, CQ, RS, downside risk, entry timing, and regime compatibility are jointly supportive. Eligible for normal PC competition, not guaranteed BUY. |
| `VALID_CONTINUATION` | Most dimensions support continuation but one or more are mixed. Eligible for reduced or normal allocation depending on BUY Quality, PC, PS, and constraints. |
| `CAUTION_CONTINUATION` | Continuation is plausible but timing, risk, participation, or regime evidence is cautious. BUY_WAIT or reduced allocation remains valid. |
| `INSUFFICIENT_QUALITY` | Required evidence is missing, stale, contradictory, or not materialized. Fail closed or review; do not treat as safe. |
| `REJECT` | Disqualifying facts, hard risk, invalid authority, or Entry Admission rejection. No BUY regardless of rank. |

Comparator dimensions:

```text
5D / 20D trend structure
MA5 / MA20 structure
momentum acceleration / deceleration
Continuation Quality
Relative Strength
Downside Risk
volatility
participation / volume
regime compatibility
Entry Admission
BUY Quality
opportunity rank / score as supporting evidence
```

The comparator must preserve raw evidence and reason codes. It must not become
an opaque historical-result-fitted weighted score.

## Opportunity Rank / Score Role

Opportunity ranking is not removed.

```text
OPPORTUNITY_RANK_ROLE = SUPPORTING
EXPECTED_EDGE_ROLE = UNCALIBRATED_SUPPORTING
```

Required semantics:

- `buy_rank` remains canonical opportunity-rank evidence.
- `runtime_opportunity_score` remains `uncalibrated_relative_model_score`.
- Expected Edge remains `UNCALIBRATED`.
- Rank / score may help compare candidates within the same quality tier.
- Rank / score may explain caution or reduced allocation.
- Rank / score must not be the sole hard rejection for a high-quality PIT
  opportunity unless another real blocker exists.

Replaced behavior:

```text
below_opportunity_top20 as hard rejection authority
non_positive_expected_edge_score as sole rejection authority
```

Target behavior:

```text
below_opportunity_top20 = soft relative evidence
non_positive_expected_edge_score = uncalibrated diagnostic/supporting evidence
quality tier + Entry Admission + Risk + PC constraints decide actionability
```

## Candidate Coverage

Candidate Top50 is preserved. AH does not authorize unlimited candidate
expansion.

Design requirements:

- materialize `market_healthy_proxy_count`;
- materialize `candidate_healthy_proxy_count`;
- materialize Candidate quality-tier distribution;
- materialize Top-ranked quality-tier distribution;
- when feasible, materialize non-selected healthy proxy observability;
- keep Candidate authority, but expose whether top50 missed broad PIT healthy
  structures.

This lets the current Candidate / Ranking chain remain authoritative while
making coverage failure visible and action-reviewable.

## PC Opportunity Selection

Portfolio Construction remains Target Portfolio Authority.

PC must consume the comparator as evidence and preserve all existing gates:

```text
Entry Admission
Downside Risk
concentration
opportunity cost
ADD-worthiness
capital constraints
broker eligibility
corporate action / listing authority
one-lot admission
Safety hard guardrails downstream
```

Design rules:

1. `HIGH_QUALITY_CONTINUATION` and `VALID_CONTINUATION` may pass into PC
   competition even when rank is below top20 or the uncalibrated score is
   non-positive.
2. `CAUTION_CONTINUATION` may remain reduced-only, BUY_WAIT, or Cash depending
   on Entry Admission and PC context.
3. `INSUFFICIENT_QUALITY` fails closed or review.
4. `REJECT` remains no BUY.
5. Cash remains a valid target portfolio choice.

This is not forced buying. It is score-only rejection retirement.

## Risk Caution / Individual Quality

Market caution is preserved.

The design separates:

```text
Market-level caution
Individual opportunity quality
Safety / hard guardrail
```

Market caution may reduce confidence or allocation. It must not automatically
erase a strong individual candidate with:

```text
supportive / strong RS
healthy CQ
contained downside risk
healthy Entry Admission
valid evidence sufficiency
```

This is not a risk bypass. Any hard blocker still wins.

## PS / Lot Boundary

Position Sizing remains quantity authority. Selection and PC do not override
lot constraints.

AH requires better classification of PC-positive -> PS-zero outcomes:

```text
GENUINE_LOT_INFEASIBILITY
MINIMUM_MEANINGFUL_NOTIONAL
CONCENTRATION_HEADROOM_LIMIT
ZERO_INCREMENTAL_TARGET
RESIDUAL_CAPITAL_TOO_SMALL
QUALITY_DEFERRED_TO_CASH
```

Phase29 lot-first and residual recycling remain preserved. The design improves
diagnostics and PC incremental target semantics; it does not force PS to emit a
quantity.

## Capital Utilization

Cash remains a legitimate allocation.

When unused opportunity cash appears, PC should compare on a shared quality
vocabulary:

```text
BUY_NEW
BUY_ADD
genuine REENTRY
Cash
```

Design requirement:

- compare quality tier, Entry Admission, ADD-worthiness, REENTRY recovery,
  opportunity cost, no-loss averaging, current exposure, lot feasibility, and
  residual destination;
- deploy only when the marginal JPY is justified;
- keep Cash when opportunity is weak, insufficient, infeasible, or over-risked.

## Low Position Days

No minimum position rule is introduced.

Desired behavior:

```text
Low Position due to true opportunity scarcity = valid
Low Position due to high-quality opportunity dropped by rank/score = repair target
Low Position due to PS infeasibility = valid only if classified and evidenced
```

This preserves the dynamic position-count contract:

```text
good candidates = possible positions
zero good candidates = zero positions
bad candidates must not fill slots
```

## Winner Amplification Interaction

The comparator creates a common vocabulary, not a common action authority.

Preserved:

```text
HOLD-worthy != ADD-worthy
PM = HOLD / ADD / REDUCE / EXIT Action Authority
PC = allocation authority
PS = quantity authority
Runtime = mapper
```

ADD remains valid only when:

```text
PM ADD
same canonical campaign
ADD-worthiness PASS
Entry Admission allows ADD
opportunity cost PASS
no-loss averaging PASS
capital feasible
PS quantity positive
Safety PASS
```

BUY_NEW quality tier does not authorize ADD by itself.

## Authority Boundaries

```text
Strategy Intelligence = evidence / semantic tier / lifecycle context
Candidate AI = candidate authority
Opportunity Ranking = supporting rank evidence
BUY Quality = allocation capability evidence
Portfolio Construction = target portfolio / allocation authority
Position Sizing = executable quantity authority
Runtime Planning = pure mapper
Safety = hard guardrail
Submit / Execution = broker-side materialization
```

No Runtime authority changes are part of AH.

## Legacy Inventory / Retirement

Inventory file:

```text
reports/phase_reports/phase30_ah_selection_logic_inventory.json
```

Summary:

| Logic | Classification | Target |
|---|---|---|
| Market Universe / Eligibility | KEEP | Keep PIT authority; add comparator coverage evidence. |
| Candidate AI Top50 | MODIFY | Preserve authority; materialize quality-tier coverage. |
| Opportunity `buy_rank` | MODIFY | Supporting evidence, not hard dominance. |
| `runtime_opportunity_score` / Expected Edge aliases | MODIFY | `UNCALIBRATED_SUPPORTING`; not expected return. |
| `below_opportunity_top20` hard rejection | DEPRECATE_DURING_MIGRATION | Soft relative reason only. |
| `non_positive_expected_edge_score` hard rejection | DEPRECATE_DURING_MIGRATION | Not sole rejection while Expected Edge is uncalibrated. |
| Adaptive BUY Quality | MODIFY | Consume quality tier / comparator dimensions. |
| Entry Admission | KEEP | Veto/reduced semantics preserved. |
| CQ / Downside Risk / RS fields | MODIFY | Make comparator action-effective. |
| PC target authority | KEEP | Consume comparator, keep allocation authority. |
| PS lot-first / residual recycling | KEEP | Quantity authority unchanged. |
| Runtime Planning | KEEP | No Selection authority. |
| Obsolete ranking fallback / duplicated quality tier logic | REMOVE_AFTER_MIGRATION | Reference count must reach zero. |

Final target:

```text
ONE_PRODUCTION_SELECTION_PATH = YES
```

## Preserved Improvements

```text
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_AD1_BOOTSTRAP_PRESERVED = YES
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
PHASE29_LOT_FIRST_RESIDUAL_RECYCLING_PRESERVED = YES
SAFETY_HARD_GUARDRAILS_PRESERVED = YES
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

Winner / loser outcomes were used only to diagnose behavior gaps in AF/AG. They
are not used to define quality-tier thresholds.

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AH
```

## Implementation Readiness

```text
PHASE30_AI_IMPLEMENTATION_READY = YES
```

The design is ready for an implementation task because the required data exists
in current PIT feature, SI, BUY Quality, PC, and PS artifacts. The
implementation must still be separately authorized and must include legacy
retirement and focused regression tests.

## Recommended Next Task

```text
Phase30-AI - Selection Quality / Opportunity Capture Repair Implementation and Legacy Retirement
```

