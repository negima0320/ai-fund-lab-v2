# Phase32-C - ADD Capitalization Admission / Competition Semantic Audit

## Executive Summary

`Phase32-C` audited the ADD capitalization bottleneck from `Phase32-B` under a
READ-ONLY constraint. No production code, config, threshold, model, Strategy,
PM, PC, MCC, Risk Pacing, PS, Runtime, fresh-run, resume, replay, long
Historical, or full backtest action was executed.

The most important finding is a measurement-definition correction. The
`Phase32-B` statement:

```text
PM ADD = 242 symbol-days
PC ADD considered = 60
PC positive ADD allocation = 5
```

does not reproduce against the canonical plateau artifacts when `PM ADD` is
defined as authoritative `position_management.positions[].action == ADD`, PC
`portfolio_members[].pm_action == ADD`, or PC
`capital_competition.competitors[].competitor_type == ADD`.

The canonical plateau count is:

```text
PM ADD = 60
PC ADD considered = 60
PC positive ADD allocation = 5
```

Therefore the alleged `182` PM-to-PC disappearance is not supported as a
canonical symbol-day loss stage. It is best classified as a Phase32-B
observability / counting-surface mismatch, not as a proven production contract
defect.

The real audited bottleneck is `60 -> 5`. Of the `55` PC ADD competitors that
did not receive positive ADD allocation:

- `47` were annotated `ADD_LOST_TO_NEW_BUY`;
- `8` were annotated `ADD_LOST_TO_CASH`;
- `54` carried `ADD_INSUFFICIENT_EVIDENCE`, `ADD_NOT_AVAILABLE`, and
  `ADD_NO_POSITIVE_DELTA`;
- `1` had positive ADD evidence but still ended with zero executable ADD after
  competition / residual handling.

This means the primary current issue is not Runtime, Submit, Fill, or Position
Sizing. It is the semantic gap between PM's position-level ADD action and PC's
stricter requirement for positive incremental capital evidence that can beat
NEW and Cash and survive executable-lot allocation.

## Phase32-B Inheritance

Accepted inherited findings:

```text
PHASE32_B_MEASUREMENT_INTEGRITY = PASS
PHASE32_B_BULL_WEAKNESS = CONDITIONAL
PHASE32_B_WINNER_CAPITALIZATION_FAILURE = YES
PHASE32_B_ADD_CONVERSION_LIMITATION = YES
PHASE32_B_PC_MCC_BOTTLENECK_MATERIAL = YES
PHASE32_B_MANDATORY_STRATEGY_DEFECT = NO
```

Refined by Phase32-C:

- the `242 -> 60` stage is not reproducible as canonical PM ADD to PC ADD
  admission loss;
- the canonical plateau ADD path is `60 -> 60 -> 5`;
- the meaningful loss stage is PC ADD competitor to positive executable ADD.

## Measurement Reconciliation

Audited target:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
plateau window: 2023-05-31 through 2024-02-26
```

Canonical counts:

| Surface | Plateau ADD Count |
| --- | ---: |
| `position_management.positions[].action == ADD` | 60 |
| `portfolio_construction.portfolio_members[].pm_action == ADD` | 60 |
| `capital_competition.competitors[].competitor_type == ADD` | 60 |
| PC positive ADD allocation | 5 |
| Full audited range PM ADD | 153 |
| Spring PM ADD | 16 |

Broader non-authoritative surfaces do not reconcile to 242 either:

| Surface | Count |
| --- | ---: |
| Strategy Intelligence `ADD_ALLOWED` / `ADD_REDUCED_ONLY` held-position admission signals | 1,542 |
| Unique date-symbol ADD-like artifact occurrences across PC/draft/PS/runtime-planning paths | 115 |

Judgment: `242` should not be treated as canonical PM ADD until its exact
counting surface is supplied. The 182-loss taxonomy requested by Phase32-C is
therefore not fully explainable as real production behavior.

## PM ADD 242 Decomposition

Because the canonical artifacts do not contain `242` authoritative PM ADD
symbol-days in the plateau window, a literal 242-row decomposition would be
misleading. The correct decomposition is:

| Bucket | Count | Share of 242 | Interpretation |
| --- | ---: | ---: | --- |
| Canonical PM ADD represented in PC ADD consideration | 60 | 24.8% | Real ADD path, audited below |
| Not reproducible as canonical PM ADD | 182 | 75.2% | Measurement / observability surface mismatch |

This does not prove that 182 valid PM ADDs were dropped by PC. It proves the
opposite: using canonical authority artifacts, there is no PM-to-PC admission
loss for actual PM ADD rows in this window.

## PM-to-PC Admission Loss Taxonomy

For canonical ADD:

| Bucket | Count | Share |
| --- | ---: | ---: |
| PM ADD admitted as PC ADD competitor | 60 | 100.0% |
| PM ADD not admitted to PC | 0 | 0.0% |
| PC admission contract mismatch | 0 | 0.0% |
| Missing/stale evidence before PC admission | 0 | 0.0% |
| Duplicate/same-symbol normalization loss before PC | 0 | 0.0% |
| Observability gap in Phase32-B 242 count | 182 diagnostic rows | unresolved |

The PM-to-PC bridge for canonical ADD is present. What fails is later: the ADD
competitor often has zero positive incremental demand because PC's evidence
bridge fails closed on incremental value and opportunity cost.

## PC 60-to-5 Competition Loss Taxonomy

Canonical PC ADD competitor results:

| Result | Count | Share |
| --- | ---: | ---: |
| Positive ADD allocation | 5 | 8.3% |
| Lost to NEW | 47 | 78.3% |
| Lost to Cash | 8 | 13.3% |

Evidence-state decomposition of the `55` non-positive ADD competitors:

| Primary diagnostic reason | Count | Share of 55 |
| --- | ---: | ---: |
| Expected edge not improving or unknown | 30 | 54.5% |
| Incremental value not positive | 24 | 43.6% |
| Eligible positive evidence but zero final executable ADD | 1 | 1.8% |

Common reason codes:

| Reason Code | Count |
| --- | ---: |
| `ADD_NO_POSITIVE_DELTA` | 55 |
| `ADD_INSUFFICIENT_EVIDENCE` | 54 |
| `ADD_NOT_AVAILABLE` | 54 |
| `ADD_LOST_TO_NEW_BUY` | 47 |
| `ADD_LOST_TO_CASH` | 8 |
| `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` | 1 |

This means `ADD_LOST_TO_NEW_BUY` and `ADD_LOST_TO_CASH` are outcome labels, but
the deeper cause is generally insufficient positive incremental ADD evidence.

## Positive Controls

Requested positive ADD controls:

| Date | Symbol | PC Status | Requested Weight | Accepted Weight | Risk Pacing |
| --- | --- | --- | ---: | ---: | --- |
| 2023-05-31 | 30410 | `COMPETITOR_SELECTED` | 0.072806 | 0.072806 | cautious strong allowed |
| 2023-06-13 | 21340 | `COMPETITOR_SELECTED` | 0.033333 | 0.001375 | cautious strong allowed |
| 2023-06-19 | 59550 | `COMPETITOR_SELECTED` | 0.029412 | 0.005884 | normal allowed |
| 2023-06-20 | 59550 | `COMPETITOR_SELECTED` | 0.030303 | 0.005506 | normal allowed |
| 2023-06-22 | 21340 | `COMPETITOR_SELECTED` | 0.052632 | 0.001709 | normal allowed |

The shared pass pattern:

- PM action is `ADD`;
- current position exists;
- expected edge is `IMPROVING`;
- incremental investment value is `POSITIVE`;
- opportunity cost is `PASS`;
- no-loss averaging is `PASS`;
- PC emits `ADD_COMPETITOR_ELIGIBLE`;
- PC emits `ADD_SELECTED`;
- executable-lot authority emits a positive quantity.

## Negative Controls

Representative negative controls:

| Date | Symbol | PC Outcome | Main Evidence |
| --- | --- | --- | --- |
| 2023-05-31 | 59550 | lost to NEW | expected edge improving, but incremental value unknown and opportunity cost failed |
| 2023-06-01 | 59550 | lost to Cash | expected edge weakening, incremental value unknown, opportunity cost failed |
| 2023-06-06 | 21340 | lost to NEW | expected edge unknown, incremental value unknown, opportunity cost failed |
| 2023-06-16 | 21340 | lost to NEW | expected edge weakening, incremental value unknown |
| 2023-06-20 | 21340 | lost to NEW | positive bridge evidence, but no final positive executable ADD; residual/reconsideration label present |
| 2023-06-21 | 21340 | lost to Cash | expected edge weakening, incremental value unknown |
| 2023-06-21 | 40520 | lost to Cash | expected edge weakening, incremental value unknown, opportunity cost failed |
| 2023-06-26 | 40520 | lost to Cash | expected edge improving, but incremental value unknown and opportunity cost failed |

What makes ADD pass:

```text
PM ADD
+ current position
+ positive incremental value
+ opportunity-cost pass versus same-day NEW alternatives
+ no-loss averaging / campaign continuity pass
+ executable lot can be allocated
+ NEW/Cash do not dominate the capital frontier
```

What makes ADD stop:

```text
PM ADD
+ current position
- missing/weak expected-edge improvement
- incremental value unknown
- opportunity cost fail or NEW superior
- no positive executable delta after PC/lot reconciliation
```

## Semantic Contract Audit

`PM ADD` means a Position Management action on an existing held position. It is
a position-action authority, not a capital-allocation mandate.

`PC ADD candidate` means PC has admitted that PM ADD row into capital
competition as an ADD competitor with a requested incremental weight.

`positive incremental capital value` means PC can prove that incremental
capital for the existing position has positive value using current, point-in-
time evidence. In current code this depends heavily on expected-edge
improvement and opportunity-cost checks.

`executable quantity delta` means the accepted ADD weight survives lot sizing
and discrete quantity authority as a positive BUY_ADD quantity. PC may bind the
positive quantity authority, but PS remains the discrete sizing owner and
Runtime remains a consumer.

Important distinctions:

| Concept | Current Meaning |
| --- | --- |
| HOLD value | Existing position remains worth holding; no incremental capital implied |
| ADD intent | PM action says the position merits add consideration |
| ADD eligibility | PC bridge checks current position, PM ADD, incremental value, opportunity cost |
| ADD marginal value | ADD's incremental lot compared against NEW and Cash |
| ADD beats NEW | no superior selected NEW competitor dominates the frontier |
| ADD beats Cash | deployable security beats explicit residual/Cash preference |
| Executable ADD quantity | lot-aware final reallocation emits positive quantity/weight |

No Runtime Strategy redecision was found. The semantic issue is narrower:
`PM ADD` is sometimes easy to read as "buy more", while PC correctly requires
incremental capital evidence before buying more.

## Authority Boundary Audit

The authority boundary is preserved:

| Layer | Observed Role |
| --- | --- |
| PM | owns `HOLD / ADD / REDUCE / EXIT` position action |
| PC | owns `NEW / ADD / Cash` capital allocation and marginal frontier |
| PS | owns discrete executable quantity |
| Runtime | consumes executable decisions; no priority redecision |

The legacy runtime ADD consumer is explicitly telemetry-only:

```text
LEGACY_ADD_MIGRATION_STATE = NON_DECISION_COMPATIBILITY
LEGACY_ADD_AUTHORITY_MODE = COMPATIBILITY_TELEMETRY_ONLY
LEGACY_ADD_DECISION_EFFECT = NONE
```

This protects the G129 contract: legacy PM ADD does not create a second
quantity, pending, approval, submit, or execution authority.

## Winner-Specific Examples

Ex-post winner labels are diagnostic grouping only; they were not used as
decision-time inputs.

`21340` is the cleanest winner-specific ADD path:

- 2023-06-13: PM ADD, expected edge improved from prior same-campaign
  evidence, incremental value positive, opportunity cost pass versus best NEW
  score, and one-lot BUY_ADD was allocated.
- 2023-06-20: PM ADD and positive bridge evidence existed, but the ADD did not
  receive final positive executable allocation; the row carried
  `ADD_LOST_TO_NEW_BUY`, `ADD_NO_POSITIVE_DELTA`, and
  `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`.
- 2023-06-22: PM ADD again passed and one-lot BUY_ADD was allocated.

This is not a "winner went up later, therefore buy more" claim. It shows that
when decision-time PM and PC evidence aligned, ADD could pass; when capital
frontier / residual handling did not align, it stopped.

`59550` is the contrast:

- 2023-05-31 had PM ADD, but lost to NEW because incremental value was unknown
  and opportunity cost failed.
- 2023-06-19 and 2023-06-20 later passed when expected edge, incremental value,
  opportunity cost, and lot feasibility all aligned.

## High-Resolution Relevance Assessment

High-resolution marginal capital value is relevant, but not strictly proven as
the only repair needed.

Evidence supporting relevance:

- `54 / 55` non-positive PC ADD competitors collapsed into coarse
  insufficient-evidence / no-delta states;
- many final labels tell who won (`NEW` or `Cash`) but not the calibrated
  economic distance by which ADD lost;
- the current system can distinguish `ADD_MARGINAL_PREFERRED`,
  `COMPARABLE_MARGINAL`, `CASH_MARGINAL_PREFERRED`, and
  `INSUFFICIENT_EVIDENCE`, but it cannot express a richer marginal payoff
  curve or add-size response.

Evidence against making high-resolution architecture the immediate mandatory
repair:

- the canonical PM-to-PC admission path is intact for actual PM ADD;
- most failed ADDs have direct current reasons: expected edge not improving or
  unknown, incremental value unknown, or opportunity cost fail;
- only one canonical row shows positive ADD evidence that still failed to
  become executable ADD.

Judgment: high-resolution value is useful for future shadow work, but a minimal
next repair should first be an observability and evidence-bridge specification,
not production high-resolution allocation.

## Defect vs Limitation Classification

| Class | Judgment | Reason |
| --- | --- | --- |
| `NO_DEFECT` | partial | canonical PM ADD admission to PC is complete |
| `SEMANTIC_CONTRACT_DEFECT` | no for runtime; partial for reporting | Phase32-B used a non-reproducible 242 surface |
| `ADMISSION_DEFECT` | no | `60 / 60` canonical PM ADDs reached PC ADD competition |
| `EVIDENCE_PROPAGATION_DEFECT` | unresolved / partial | many rows fail closed on unknown incremental value; needs shadow audit |
| `CAPITAL_COMPETITION_LIMITATION` | yes | ADD usually loses to NEW/Cash |
| `MARGINAL_VALUE_RESOLUTION_LIMITATION` | partial | current labels are coarse, but not sole explanation |
| `CALIBRATION_QUESTION` | yes | Cash/NEW/ADD relative scoring is uncalibrated |
| `OBSERVABILITY_GAP` | yes | 242 count is not traceable to canonical PM ADD |

## Minimal Repair Candidates

No repair is authorized in this task. If later approved, the minimal boundaries
are:

1. Observability-only: record canonical ADD funnel surfaces and prevent mixed
   counting of PM action, SI add-worthiness, PC competitors, and duplicated
   downstream lineage.
2. PM-to-PC evidence bridge shadow: preserve why PM emitted ADD and whether PC
   saw each required evidence field, without changing allocation.
3. PC ADD admission semantics shadow: make `PM ADD`, `ADD_ALLOWED`,
   `ADD_REDUCED_ONLY`, `incremental_value`, `opportunity_cost`, and
   `executable_delta` explicit in one row.
4. Marginal evidence preservation shadow: add richer non-authoritative
   diagnostics for ADD vs NEW vs Cash distance.

Avoid broad changes to Risk Pacing, Cash, NEW competition, Safety, PM action
authority, PS quantity authority, or Runtime consumption.

## Degradation Risk Matrix

| Candidate | Possible Improvement | Possible Breakage | Regression Gates | Rollback | Shadow First |
| --- | --- | --- | --- | --- | --- |
| Observability-only funnel | removes 242/60 ambiguity | none expected except artifact churn | canonical runtime alignment, future leakage scan | easy | yes |
| PM-to-PC evidence bridge | explains why PM ADD fails PC evidence | accidental authority leak from PM into PC | G129, PM/PC authority boundary, no Runtime redecision | easy | yes |
| PC admission semantics | cleaner ADD eligibility reasons | ADD becomes too easy if admission changes behavior | Cash first-class, Safety caps, Risk Pacing independent value | medium | yes |
| Marginal evidence preservation | better NEW/ADD/Cash comparison | pseudo-calibration may be mistaken for authority | future leakage, no model/threshold change, Demo/Historical alignment | medium | yes |
| Production ADD loosening | more winner capitalization | loser over-ADD, concentration, Cash discipline loss, NEW starvation, Risk Pacing bypass | full contract regression suite required | harder | mandatory |

## Required Regression Gates

Any later implementation must protect:

- G129 BUY_ADD actual path and no duplicate ADD authority;
- G140 Risk Pacing independent value;
- Cash as a first-class alternative;
- BUY / SELL independence;
- no Runtime Strategy redecision;
- Production / Demo / Historical canonical Runtime alignment;
- valuation / quantity basis integrity;
- future leakage prohibition;
- Safety hard-cap and strategy concentration constraints;
- PS discrete executable quantity authority;
- NEW opportunity starvation guard.

## Primary Questions Answered

1. The 182 missing rows are not canonical PM ADD rows. They are a measurement
   definition / observability mismatch unless the Phase32-B counting surface is
   supplied.
2. For canonical PM ADD, there is no PM-to-PC exclusion. For the alleged 182,
   classification is `OBSERVABILITY_GAP`, not proven contract exclusion.
3. The 55 PC competitors failed mostly because ADD evidence was insufficient or
   zero-delta, then the rows were annotated as losing to NEW (`47`) or Cash
   (`8`).
4. ADD vs NEW vs Cash competition is directionally design-intent conformant:
   PM ADD is not entitled to capital, Cash remains first-class, and NEW can win.
5. PM ADD and PC incremental capital opportunity are partially semantically
   connected: actual PM ADD reaches PC, but PM's ADD meaning is broader than
   PC's positive incremental capital requirement.
6. Winner capital not increasing is primarily evidence resolution /
   competition, not canonical admission.
7. Normal behavior explains all canonical PM-to-PC flow and most 60-to-5 loss.
8. If repair is later needed, start with observability and PM-to-PC evidence
   bridge shadow, not production ADD loosening.

## Files Inspected

- `docs/phase_reports/phase32_b_capital_conversion_bull_winner_capitalization_deep_audit.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `src/ai_fund_lab_v2/runtime_v2/planning/add_consumer.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/runtime_v2/position_sizing_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- daily artifacts under
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/`

## Commands Executed

```text
sed -n ... Phase32-C pasted request
git status --short
rg -n ... ADD / BUY_ADD / marginal / competition source search
jq ... artifact shape and positive/negative controls
python3 - <<'PY' ... canonical PM/PC ADD count reconciliation
python3 - <<'PY' ... PC 60-to-5 taxonomy aggregation
python3 - <<'PY' ... ADD marginal shadow / authority aggregation
nl -ba ... source line inspection
```

No tests, fresh-run, resume, replay, long Historical, full backtest,
production command, model training, or production implementation command was
executed.

## Final Judgments

`PHASE32_C_PM_ADD_TOTAL = 60_CANONICAL; 242_PHASE32_B_COUNT_NOT_REPRODUCED`

`PHASE32_C_PC_ADD_CONSIDERED = 60`

`PHASE32_C_PC_POSITIVE_ADD = 5`

`PHASE32_C_PM_TO_PC_LOSS_FULLY_EXPLAINED = PARTIAL`

`PHASE32_C_PRIMARY_PM_TO_PC_LOSS_REASON = PHASE32_B_COUNTING_SURFACE_OBSERVABILITY_GAP_NOT_CANONICAL_ADMISSION_LOSS`

`PHASE32_C_PC_COMPETITION_LOSS_FULLY_EXPLAINED = YES`

`PHASE32_C_PRIMARY_PC_COMPETITION_LOSS_REASON = ADD_INSUFFICIENT_INCREMENTAL_EVIDENCE_AND_NO_POSITIVE_DELTA_WITH_DOWNSTREAM_LOSS_TO_NEW_OR_CASH`

`PHASE32_C_PM_PC_SEMANTIC_MISMATCH = PARTIAL`

`PHASE32_C_ADD_EVIDENCE_PROPAGATION_DEFECT = UNRESOLVED`

`PHASE32_C_ADD_ADMISSION_DEFECT = NO`

`PHASE32_C_CAPITAL_COMPETITION_LIMITATION = YES`

`PHASE32_C_MARGINAL_VALUE_RESOLUTION_LIMITATION = PARTIAL`

`PHASE32_C_HIGH_RESOLUTION_ARCHITECTURE_NEEDED_FOR_REPAIR = NO`

`PHASE32_C_OBSERVABILITY_GAP = YES`

`PHASE32_C_MANDATORY_DEFECT = NO`

`PHASE32_C_MINIMAL_REPAIR_BOUNDARY = OBSERVABILITY_AND_PM_TO_PC_ADD_EVIDENCE_BRIDGE_SHADOW_ONLY`

`PHASE32_C_DEGRADATION_RISK = MEDIUM`

`PHASE32_C_IMPLEMENTATION_READY = NO`

`PHASE32_C_NEXT_STEP = Phase32-D - Canonical ADD Funnel Observability / PM-to-PC Evidence Bridge Shadow Specification`
