# Phase31-C0C — Alternative G Overfit-Safe Validation Design

Status: COMPLETE
Task type: VALIDATION DESIGN ONLY

## PRIMARY_JUDGMENT

```text
PHASE31_C0C_ALTERNATIVE_G_OVERFIT_SAFE_VALIDATION_DESIGN_COMPLETE
```

Alternative G is a valid candidate for overfit-safe validation, but it is not ready for mutating implementation. The next safe step is a non-mutating shadow implementation that records when Alternative G would have selected PM-owned `EXIT`, without changing PM, PC, PS, Runtime Planning, Sell Planning, Pending, Submit, Execution, Current, tests, fixtures, or configuration.

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

LONG_HISTORICAL_BY_CODEX:

```text
NO
```

## DEVELOPMENT_EVIDENCE

Development / mechanism-discovery run:

```text
runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Path:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z
```

Completed usable evidence window:

```text
2022-08-10 through 2022-12-15
```

C0A development findings:

| Metric | Value |
|---|---:|
| Usable business dates | 86 |
| PM REDUCE rows | 344 |
| Executable REDUCE rows | 0 |
| Lot-zeroed REDUCE rows | 344 |
| LOT_ZEROED_REDUCE_RATE | 100% |
| Affected symbols / campaigns | 82 |
| Current quantity <= one lot cases | 309 |
| LIGHT REDUCE rows | 297 |
| MEDIUM REDUCE rows | 23 |
| STRONG REDUCE rows | 24 |

This run may be used only for:

- mechanism discovery;
- architecture formulation;
- semantic candidate family definition;
- regression/control case construction;
- required evidence inventory;
- materiality justification.

It must not be used for:

- persistence-count optimization;
- recent-window optimization;
- representation-error cutoff optimization;
- deterioration threshold selection;
- recovery reset threshold selection;
- winner-protection threshold selection;
- final production parameter selection;
- final validation.

## DEVELOPMENT_ONLY_CASES

61750 is a development/control case only:

```text
100 shares
LIGHT REDUCE
first zeroed REDUCE = 2022-09-13
63 zeroed REDUCE rows through 2022-12-15
```

Representative C0A winner/recovery controls are development controls only:

```text
40800
27670
92270
66330
32050
```

These cases may verify that the validation design can represent known recovery patterns. They must not be used to tune parameter values from later outcomes.

## Candidate Architecture Freeze

CANDIDATE_ARCHITECTURE_FROZEN:

```text
YES
```

Frozen structural candidate:

```text
PRE_PM_LOT_AWARE_RESOLUTION
+
IMMEDIATE_STRONG_CASE
+
PERSISTENT_LIGHT_MEDIUM_CASE
+
CURRENT_PIT_DETERIORATION_CONFIRMATION
+
RECOVERY_RESET
```

Preferred candidate family:

```text
Alternative G Hybrid
```

This candidate must not gain new branches after inspecting profitability. If later validation shows Alternative G is insufficient, the result is an evidence/design gap, not branch patching during holdout.

## PRE_REGISTERED_VARIANTS

Pre-register only a small interpretable set:

### G0 — Baseline

```text
unrepresentable REDUCE
-> intentional NO_ORDER
-> fresh PM reevaluation
```

### G1 — Immediate Strong Case Only

```text
unrepresentable REDUCE
+ STRONG/high-confidence de-risk semantics
+ current PIT severe deterioration confirmation
+ no strong recovery evidence
-> PM-owned EXIT shadow action
```

No persistence branch.

### G2 — Persistent Confirmation Only

```text
repeated fresh unrepresentable REDUCE
+ current PIT deterioration
+ no recovery reset
-> PM-owned EXIT shadow action
```

No immediate branch.

### G3 — Full Alternative G Hybrid

```text
Immediate strong/high-confidence branch
+
persistent LIGHT/MEDIUM branch
+
existing PIT deterioration confirmation
+
recovery reset
```

G3 is the C0B-preferred architecture. If variants are later necessary, they must be pre-registered as semantic variants before outcome evaluation. Do not brute-force arbitrary parameter combinations.

## Fixed Canonical Inputs

FIXED_CANONICAL_INPUTS:

- `LIGHT = 0.25`;
- `MEDIUM = 0.33`;
- `STRONG = 0.50`;
- canonical tradable unit evidence;
- `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`;
- PM owns `HOLD / ADD / REDUCE / EXIT`;
- PM owns REDUCE versus EXIT escalation;
- PS / Sell Planning own discrete quantity materialization;
- Runtime Planning maps Strategy quantity/action evidence and must not re-decide PM intent;
- lot rounding remains floor-to-tradable-unit;
- no ceil-to-one-lot behavior;
- no hidden reduce debt;
- BUY / SELL independence;
- Production / Demo / Historical common semantics.

NEW_MARKET_FEATURE_REQUIRED:

```text
NO
```

Alternative G validation must use existing Production-visible PIT evidence only.

## TUNABLE_PARAMETERS

TUNABLE_PARAMETERS:

- persistence evidence requirement;
- recent-window length;
- days-since-first-unrepresentable role;
- representation-error materiality role;
- immediate escalation eligibility;
- deterioration confirmation sufficiency;
- recovery reset semantics;
- recovery decay semantics;
- winner-protection blocking conditions;
- Market Context modifier role;
- campaign-age role;
- evidence sufficiency rule;
- sample sufficiency minimums;
- regime robustness interpretation;
- churn acceptance interpretation.

C0C assigns no values to these parameters unless already canonical.

## Validation Period Selection Rule

VALIDATION_PERIOD_SELECTION_RULE:

```text
Choose a chronological period after development evidence is frozen and before holdout,
using pre-declared calendar/business-day boundaries and data-readiness criteria,
not profitability.
```

Rule requirements:

- non-overlapping with the C0A development run where feasible;
- Production-common Historical artifacts only;
- sufficient current-position, PM, PC/PS, Runtime Planning, Market Context, Strategy Intelligence, execution/fill, and Current valuation evidence;
- no selection based on known profitability, 61750 behavior, winner/loser concentration, or regime convenience;
- record excluded dates and exclusion reasons before outcome analysis.

If exact clean ranges cannot yet be proven, C0C defines the selection rule and leaves concrete dates for the user-operated validation setup.

## Holdout Selection Rule

HOLDOUT_SELECTION_RULE:

```text
Choose a later or otherwise untouched chronological period only after candidate
semantics and parameter values are frozen from validation.
```

Holdout requirements:

- non-overlapping with development and validation;
- not inspected for tuning;
- not used to choose parameters;
- evaluated once after freeze;
- if holdout fails, report failure or return to a new design cycle with a new future holdout, not retuning against the used holdout.

HOLDOUT_RETUNING_ALLOWED:

```text
NO
```

## Parameter Selection Method

PARAMETER_SELECTION_METHOD:

1. Pre-register the small semantic variant set.
2. Materialize a non-mutating shadow artifact.
3. Run structural gate before any profitability analysis.
4. Evaluate only the validation period for parameter semantics.
5. Select using multi-objective criteria, not maximum return alone.
6. Freeze selected semantics/parameters.
7. Run untouched holdout once.
8. Do not retune after holdout.

Selection dimensions:

- Net Performance Opportunity;
- winner damage;
- MDD;
- churn;
- sample size;
- regime robustness;
- tail dependence;
- architecture risk;
- explainability;
- PIT proof completeness.

## Shadow-First Requirement

SHADOW_FIRST_REQUIRED:

```text
YES
```

Before mutating PM behavior, Alternative G must be implemented as a non-mutating shadow. The shadow answers:

- when would Alternative G choose EXIT;
- when would baseline preserve REDUCE/no-order;
- which branch triggered;
- which PIT evidence supported the decision;
- whether recovery blocked escalation;
- whether all PIT proof fields are complete.

Actual trading behavior must remain unchanged during shadow validation.

## Future Shadow Artifact Design

Future non-mutating artifact, per PM decision:

- symbol;
- campaign_id;
- business_date;
- preliminary_pm_action;
- reduce_intensity;
- current_quantity;
- tradable_unit;
- raw_reduce_quantity;
- rounded_reduce_quantity;
- final_reduce_sell_quantity;
- desired_reduction_fraction;
- actual_reduction_fraction;
- representation_error;
- prior_unrepresentable_reduce_count;
- recent_unrepresentable_reduce_evidence;
- current_deterioration_evidence;
- recovery_evidence;
- baseline_final_pm_action;
- alternative_g_shadow_action;
- branch: `NONE`, `IMMEDIATE`, or `PERSISTENT`;
- reason_codes;
- PIT provenance;
- `future_information_used = false`;
- `future_regime_used = false`;
- `later_pnl_used = false`;
- `final_campaign_outcome_used = false`.

Outcome evaluation must be attached separately after the shadow decision. Later PnL or final campaign outcome must not appear in decision inputs.

## PIT Proof Required

PIT_PROOF_REQUIRED:

```text
YES
```

Every shadow EXIT candidate must materialize:

- business date;
- feature date;
- source artifact path/hash;
- PM source decision;
- quantity authority;
- lot authority;
- persistence evidence dates;
- deterioration evidence dates;
- recovery evidence dates;
- `future_information_used = false`;
- `future_regime_used = false`;
- `later_pnl_used = false`;
- `final_campaign_outcome_used = false`.

Any candidate that requires future outcome information fails validation.

## Structural Gate

STRUCTURAL_GATE:

Performance evaluation is forbidden until all structural conditions pass:

- PM owns final REDUCE vs EXIT;
- PS does not escalate REDUCE to EXIT;
- Runtime Planning does not escalate REDUCE to EXIT;
- Sell Planning does not escalate REDUCE to EXIT;
- lot rounding unchanged;
- no ceil-to-one-lot behavior;
- no hidden reduce debt;
- normal executable REDUCE preserved;
- current normal EXIT preserved;
- persistence is campaign-scoped;
- persistence comes from fresh PM decisions;
- recovery reset is auditable;
- BUY / SELL independence preserved;
- PIT proof complete;
- no future leakage;
- Production / Demo / Historical common semantics preserved.

If the structural gate fails:

```text
STOP_PERFORMANCE_EVALUATION
```

## Performance Gate

PERFORMANCE_GATE:

Only after structural PASS, evaluate:

- avoided loss;
- lost winner profit;
- Net Performance Opportunity;
- total return delta;
- MDD delta;
- drawdown contribution;
- drawdown duration;
- recovery duration;
- worst daily loss;
- downside-tail distribution;
- turnover delta;
- churn delta;
- capital released;
- regime robustness;
- benefit concentration;
- sample sufficiency.

Return improvement alone cannot authorize mutation.

Net opportunity definition:

```text
NET_PERFORMANCE_OPPORTUNITY = AVOIDED_LOSS - LOST_WINNER_PROFIT
```

These are evaluation metrics only. They must never become Runtime inputs.

## Winner Damage Gate

WINNER_DAMAGE_GATE:

For each candidate family report:

- winner campaigns exited early;
- lost winner profit;
- Top 1 winner damage;
- Top 3 winner damage;
- Top 5 winner damage;
- long-HOLD winner damage;
- successful ADD campaign damage;
- winner contribution concentration affected;
- recovery-reset true protection count;
- recovery-reset false protection count.

Conceptual rejection rule:

```text
A candidate with attractive avoided-loss results but material destruction of
concentrated winners must not pass.
```

No arbitrary numeric threshold is selected in C0C.

## MDD Gate

MDD_GATE:

Report:

- MDD delta;
- drawdown contribution by candidate branch;
- drawdown duration;
- recovery duration;
- worst daily loss;
- downside-tail distribution.

Conceptual rejection rule:

```text
A candidate that improves total return but materially worsens drawdown quality
must not pass.
```

## Churn Gate

CHURN_GATE:

Report:

- additional EXIT count;
- additional SELL notional;
- turnover / equity;
- EXIT -> BUY within 1BD;
- EXIT -> BUY within 2-5BD;
- EXIT -> BUY within 6-10BD;
- churn loss;
- legitimate recovery re-entry count;
- normal new-opportunity re-entry count.

Alternative G must not add a blanket re-entry ban. A candidate that converts avoidable losses into repeated EXIT/re-entry churn may fail.

## Sample Sufficiency Gate

SAMPLE_SUFFICIENCY_GATE:

Before declaring PASS, report:

- total candidate count;
- immediate-branch count;
- persistent-branch count;
- recovery-reset count;
- winner controls;
- loser controls;
- regime representation;
- one-lot cases;
- multi-lot controls;
- validation-period data-readiness coverage.

If evidence is too small:

```text
INSUFFICIENT_EVIDENCE
```

Do not force PASS.

## Regime Robustness Gate

REGIME_ROBUSTNESS_GATE:

Cover canonical regimes where sufficient evidence exists:

```text
BULL
RANGE
BEAR
RECOVERY
CORRECTION
```

For each regime report:

- candidate trigger count;
- escalation count;
- immediate branch count;
- persistent branch count;
- avoided-loss proxy;
- winner damage;
- turnover impact;
- exposure impact;
- capital release;
- re-entry impact.

Do not require equal sample sizes. Do not hide regime dependence.

## Single-Symbol Dependency Gate

SINGLE_SYMBOL_DEPENDENCY_GATE:

Report benefit concentration:

- Top 1 benefit contribution;
- Top 3 benefit contribution;
- Top 5 benefit contribution;
- one-symbol dependency;
- one-campaign dependency;
- one large-day dependency;
- one-regime dependency.

If benefit is overwhelmingly concentrated, confidence must be reduced or the outcome classified as `MIXED`.

61750_DEPENDENCY_CHECK_REQUIRED:

```text
YES
```

Validation reporting must calculate candidate performance:

```text
including 61750
excluding 61750
```

Alternative G must not depend entirely on 61750.

## Normal Path Protection

Protect normal executable REDUCE:

```text
multi-lot position
+ partial REDUCE executable
-> normal REDUCE remains normal REDUCE
```

Required metric:

```text
EXECUTABLE_REDUCE_CHANGED_COUNT
```

Expected architectural value:

```text
0
```

Protect existing EXIT:

- do not delay mandatory EXIT;
- do not weaken EXIT;
- do not change EXIT quantity semantics;
- do not add Runtime-side EXIT authority;
- do not add PS-side EXIT authority.

Alternative G only refines PM action selection when REDUCE is materially unrepresentable.

## BUY / SELL Independence And Re-entry

BUY / SELL independence must be preserved:

```text
valid escalated EXIT must not be blocked by unrelated BUY review state
reviewed BUY must not block valid SELL
valid SELL must not drop valid BUY
```

After escalated EXIT, no blanket re-entry prohibition is added. Validation should classify:

- fast churn re-entry;
- legitimate recovery re-entry;
- normal new opportunity.

REENTRY_BLANKET_BAN_ADDED:

```text
NO
```

## Production Common Contract

PRODUCTION_COMMON_CONTRACT_REQUIRED:

```text
YES
```

Any future implementation must have the same business semantics in:

```text
Production
Demo
Historical
```

No Historical-only EXIT escalation is allowed.

## Acceptance Classification

### PASS_CANDIDATE

Requires:

- structural gate PASS;
- positive Net Performance Opportunity;
- controlled winner damage;
- MDD not materially worse;
- churn not pathologically worse;
- adequate sample;
- multiple-regime support;
- no single-symbol dependence;
- no 61750 dependence;
- no future leakage.

### MIXED

Examples:

- structural PASS but net opportunity uncertain;
- insufficient sample;
- high regime dependence;
- winner damage borderline;
- benefit too concentrated;
- validation and holdout disagree without clear leakage or structural cause.

### FAIL

Examples:

- structural failure;
- future leakage;
- negative net opportunity;
- winner damage dominates;
- excessive churn;
- severe MDD deterioration;
- benefit depends mainly on one symbol/campaign;
- benefit depends mainly on one regime;
- parameter choice requires hindsight.

No arbitrary numeric gates are defined in C0C unless already governed by existing project standards.

## User-Operated Future Validation Sequence

Design-only future sequence:

1. Phase31-C0D non-mutating Alternative G shadow implementation.
2. Focused unit / regression tests.
3. User-operated development shadow materialization.
4. READ-ONLY structural audit.
5. Freeze candidate semantics.
6. User-operated separate validation-period run.
7. Validation analysis.
8. Parameter freeze.
9. User-operated untouched holdout.
10. Holdout analysis.
11. Mutation authorization review.
12. Only after explicit authorization: mutating Production-common implementation.
13. Focused regression.
14. User-operated clean validation.

Long Historical remains user-operated.

## NEXT_TASK_RECOMMENDATION

```text
Phase31-C0D — Non-Mutating Alternative G Shadow Implementation
```

Do not execute C0D in this task.

## Required Output Summary

DEVELOPMENT_EVIDENCE:

```text
runtime-test-historical-extended-smoke-20260818T015851711672Z
2022-08-10 through 2022-12-15
DEVELOPMENT / MECHANISM-DISCOVERY ONLY
```

CANDIDATE_ARCHITECTURE_FROZEN:

```text
YES
```

PREFERRED_CANDIDATE_FAMILY:

```text
Alternative G Hybrid
```

HOLDOUT_RETUNING_ALLOWED:

```text
NO
```

SHADOW_FIRST_REQUIRED:

```text
YES
```

PIT_PROOF_REQUIRED:

```text
YES
```

NEW_MARKET_FEATURE_REQUIRED:

```text
NO
```

PRODUCTION_COMMON_CONTRACT_REQUIRED:

```text
YES
```

LONG_HISTORICAL_BY_CODEX:

```text
NO
```

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

## Final Questions

### 1. Can Alternative G be validated without tuning directly against the C0A 86BD outcome?

```text
YES
```

Use C0A only for mechanism discovery and control-case understanding. Parameter development must occur on a separate validation period, followed by frozen holdout evaluation.

### 2. Should C0A remain development evidence only?

```text
YES
```

### 3. Should Alternative G first be implemented as a non-mutating shadow?

```text
YES
```

### 4. What are the minimum structural conditions before profitability is examined?

Minimum structural conditions:

- PM owns final REDUCE vs EXIT;
- PS / Runtime / Sell Planning do not escalate REDUCE to EXIT;
- lot rounding unchanged;
- no ceil-to-one-lot;
- no hidden reduce debt;
- normal executable REDUCE preserved;
- existing EXIT preserved;
- persistence is campaign-scoped and derived from fresh PM decisions;
- recovery reset is auditable;
- BUY / SELL independence preserved;
- PIT proof complete;
- no future leakage;
- Production / Demo / Historical common semantics preserved.

### 5. What evidence would cause Alternative G to be rejected even if total return improves?

Rejection evidence includes:

- material winner damage;
- concentrated destruction of top winners;
- MDD deterioration;
- drawdown duration or downside-tail deterioration;
- pathological churn or EXIT/re-entry loops;
- future leakage;
- sample insufficiency;
- dependence on one symbol, one campaign, or 61750;
- dependence on one regime;
- benefit from one extreme loss or one day;
- parameter choice requiring hindsight;
- structural authority failure.

### 6. Can parameter selection be separated from holdout evaluation?

```text
YES
```

Parameters are selected/frozen from validation. Holdout is evaluated after freeze and must not be used for retuning.

### 7. Is Alternative G ready for mutating implementation now?

```text
NO
```

It is ready for non-mutating shadow implementation design/execution only after explicit C0D authorization.

### 8. What should the next task be if C0C passes?

```text
Phase31-C0D — Non-Mutating Alternative G Shadow Implementation
```
