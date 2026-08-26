# Phase31-C0F — Alternative G Validation-Period Parameter / Performance Evaluation Preparation

Status: COMPLETE
Task type: VALIDATION PREPARATION / PARAMETER PRE-REGISTRATION / EVALUATION DESIGN

## PRIMARY_JUDGMENT

```text
PHASE31_C0F_ALTERNATIVE_G_VALIDATION_PREPARATION_COMPLETE
```

Alternative G is ready for a user-operated, chronologically separate validation run and later C0G shadow performance evaluation. C0F does not execute that run, does not evaluate validation profitability, does not tune parameters, and does not authorize mutating Strategy implementation.

## Evidence Roles

DEVELOPMENT_RUN:

```text
runtime-test-historical-extended-smoke-20260818T015851711672Z
```

DEVELOPMENT_FROZEN:

```text
YES
```

Development window:

```text
2022-08-10 through 2022-12-15
```

Development evidence role:

```text
MECHANISM_DISCOVERY_ONLY
```

It must not be used to choose persistence count, recent-window size, deterioration sufficiency, recovery reset strength, representation-error cutoff, or final production parameters.

Validation role:

```text
chronologically separate evidence for selecting among pre-registered semantic candidates
```

Holdout role:

```text
one-time untouched evaluation after validation-selected parameters are frozen
```

Final clean confirmation role:

```text
optional later fresh clean validation after explicit mutating implementation authorization
```

## Existing Validation Run Reuse

EXISTING_VALIDATION_RUN_REUSABLE:

```text
NO
```

Only the C0A/C0E development run exists locally under:

```text
reports/runtime_tests/runs
```

No separate untouched local run with the required current artifacts is available for C0F validation reuse. A user-operated fresh validation run is required.

## Validation Period

VALIDATION_PERIOD:

```text
2023-01-04 start, 100 business days
```

VALIDATION_PERIOD_SELECTION_RULE:

```text
Use the first clean chronological 100BD window after the frozen development window,
starting at the first regular 2023 Tokyo Stock Exchange business date, without
inspecting Alternative G profitability.
```

Rationale:

- outside the 2022-08-10 through 2022-12-15 development window;
- chronological, not outcome-selected;
- avoids reusing 61750 as a parameter source;
- long enough to observe PM REDUCE, recovery, re-entry, regime, and campaign diversity;
- compatible with current Production-common architecture rather than trying to recreate pre-B10 trades.

If the user-operated run halts for data-readiness or corporate-action reasons, C0G should treat that as validation evidence availability failure and report the explicit halt, not silently shift the period for profitability.

## Holdout Period

HOLDOUT_PERIOD:

```text
UNSET
```

HOLDOUT_PERIOD_SELECTION_RULE:

```text
After validation analysis selects and freezes one Alternative G semantic candidate,
choose the next non-overlapping chronological 100BD window after the validation
period's final completed business date. Do not inspect Alternative G results in
that period before parameter freeze.
```

HOLDOUT_RETUNING_ALLOWED:

```text
NO
```

If holdout fails, allowed outcomes are reject Alternative G, return to design, or reserve a new future untouched holdout for a materially revised candidate. The failed holdout must not become a tuning set.

## Current Architecture / B10

CURRENT_ARCHITECTURE_VALIDATION_REQUIRED:

```text
YES
```

B10_CONFOUNDING_ASSESSMENT:

```text
BUY_NEW / BUY_ADD marginal-capital priority can change portfolio composition and
therefore the naturally occurring REDUCE campaigns. This is acceptable and should
be documented, because validation should measure Alternative G on current
Production-common architecture rather than recreating the pre-B10 development run.
```

Alternative G concerns existing-position SELL semantics. B10 is a BUY capital-priority change. C0F must not couple Alternative G parameters to B10 business semantics, but the validation run should include current B10 behavior if that is now the active Production-common code path.

## Pre-Registered Candidate Matrix

PRE_REGISTERED_PARAMETER_CANDIDATE_COUNT:

```text
8
```

Candidate set:

| Candidate | Description |
|---|---|
| G0 | Baseline current behavior. |
| G1 | Immediate strong/high-confidence branch only. |
| G2-A | Persistent branch with short persistence semantics. |
| G2-B | Persistent branch with moderate persistence semantics. |
| G2-C | Persistent branch with strong persistence semantics. |
| G3-A | Hybrid = G1 + G2-A. |
| G3-B | Hybrid = G1 + G2-B. |
| G3-C | Hybrid = G1 + G2-C. |

The candidate count is intentionally small and semantic. It is not a large grid search.

## Persistence Candidates

PERSISTENCE_CANDIDATES:

| ID | Semantic role | Validation-resolved meaning |
|---|---|---|
| P0 | No persistence escalation | Only G1 immediate branch active. |
| P1 | Short persistence confirmation | More than isolated caution; repeated fresh PM REDUCE over a very recent window. |
| P2 | Moderate persistence confirmation | Repeated fresh PM REDUCE across a broader short-to-medium campaign interval. |
| P3 | Strong persistence confirmation | Clearly sustained PM de-risk pressure across a campaign interval. |

C0F does not assign production counts from the development run. C0G may evaluate a small pre-registered set, but selection must use validation evidence only and multi-objective criteria.

## Recent Window Candidates

RECENT_WINDOW_CANDIDATES:

| ID | Semantic role |
|---|---|
| W1 | Very recent de-risk pressure |
| W2 | Short-horizon persistent pressure |
| W3 | Medium-horizon persistent pressure |

These windows should be resolved in validation as named semantic horizons, not as a dense numerical search.

## Deterioration Semantics

DETERIORATION_SEMANTICS:

Use existing Production-visible PIT semantics only:

- PM reason codes / dominant cause indicating risk, weak hold, downside, trend/opportunity weakening, or reduce pressure;
- `expected_edge` semantic status from Strategy Intelligence where available;
- continuation quality status and states such as trend health, persistence, participation quality, and relative strength;
- downside risk status and risk states;
- campaign state including age, giveback, current campaign relative return, and reduce history where canonical;
- canonical Market Context / regime as a modifier, not as a standalone EXIT rule.

Candidate semantic categories:

| Category | Meaning |
|---|---|
| D0 | Deterioration not confirmed |
| D1 | Weak / caution deterioration |
| D2 | Deterioration confirmed |
| D3 | Severe deterioration / full-close compatible |

No raw-score weighted deterioration model is introduced in C0F.

## Recovery Reset Semantics

RECOVERY_RESET_SEMANTICS:

Use existing PIT PM / Strategy Intelligence evidence:

- same-row recovery: PM remains REDUCE but current PIT evidence shows healthy continuation or ADD-allowed recovery;
- subsequent PM recovery: prior REDUCE pressure is followed by fresh PM HOLD/ADD and current PIT evidence supports recovery;
- insufficient recovery: PM changes to HOLD but continuation / downside evidence remains weak or incomplete.

Candidate recovery states:

| State | Meaning |
|---|---|
| R0 | No recovery |
| R1 | Recovery insufficient / caution only |
| R2 | Healthy HOLD recovery |
| R3 | Valid ADD recovery |

Persistence must reset or decay only from fresh PIT evidence. A stale REDUCE history must not force EXIT after legitimate recovery.

## Representation Error Role

REPRESENTATION_ERROR_ROLE:

```text
Deterministic evidence only.
```

Formula:

```text
desired_reduction_fraction = target_reduce_ratio
actual_reduction_fraction = final_reduce_sell_quantity / current_quantity
representation_error = desired_reduction_fraction - actual_reduction_fraction
```

Representation error is used to describe semantic distortion between PM intent and executable REDUCE quantity. It is not an alpha feature and must not be optimized from development outcomes.

## Immediate Branch Parameterization

IMMEDIATE_BRANCH_PARAMETERIZATION:

```text
unrepresentable REDUCE
+ canonical STRONG/high-confidence de-risk semantics
+ D3 severe deterioration / full-close-compatible PIT evidence
+ no R2/R3 recovery contradiction
-> G1/G3 shadow EXIT candidate
```

STRONG alone is insufficient. Market Context alone is insufficient. No new threshold is selected in C0F.

## Persistent Branch Parameterization

PERSISTENT_BRANCH_PARAMETERIZATION:

```text
unrepresentable REDUCE
+ P1/P2/P3 fresh PM persistence semantics
+ D2/D3 current PIT deterioration confirmation
+ no R2/R3 recovery reset
+ representation error remains material under validation-selected semantics
-> G2/G3 shadow EXIT candidate
```

No hidden reduce debt is allowed. Persistence is evidence for a fresh PM decision, not accumulated sell quantity.

## Evaluation Metrics

WINNER_DAMAGE_METRICS:

- winner campaigns exited early;
- winner profit lost;
- Top 1 / Top 3 / Top 5 winner damage;
- successful long-HOLD damage;
- successful ADD campaign damage;
- recovery-after-REDUCE damage;
- campaign duration reduction;
- winner contribution concentration affected.

AVOIDABLE_LOSS_METRICS:

- avoided loss;
- lost winner profit;
- Net Performance Opportunity = `AVOIDED_LOSS - LOST_WINNER_PROFIT`;
- branch attribution: immediate vs persistent;
- one-lot vs multi-lot attribution;
- minimum-notional family reported separately.

MDD_METRICS:

- final return delta;
- MDD delta;
- drawdown duration;
- recovery duration;
- worst daily loss;
- downside-tail days;
- contribution to large loss days;
- gain-to-giveback behavior;
- profit retention ratio as descriptive evaluation only.

CHURN_METRICS:

- additional EXIT count;
- additional SELL notional;
- turnover / equity;
- EXIT -> BUY within 1BD;
- EXIT -> BUY within 2-5BD;
- EXIT -> BUY within 6-10BD;
- churn PnL;
- legitimate recovery re-entry;
- repeated EXIT/re-entry loop count.

REGIME_METRICS:

For each canonical regime:

- trigger count;
- shadow EXIT count;
- avoided loss;
- winner damage;
- net opportunity;
- MDD effect;
- churn;
- sample size.

Regimes:

```text
BULL
RANGE
BEAR
RECOVERY
CORRECTION
```

## Counterfactual Evaluation Rules

Shadow EXIT timing:

```text
Use the date Alternative G shadow chooses EXIT.
Do not use best later date or eventual baseline EXIT date with hindsight.
```

Hypothetical execution price authority:

Prefer canonical Historical execution / reference-price authority if available in the validation run. If a full execution simulator is not available in read-only analysis, use conservative labeled evaluation:

```text
EVALUATION_LABEL_ONLY
price_authority = decision-time canonical reference / next executable historical price authority
fill_certainty = NOT_ASSUMED
```

The evaluator must check:

- order feasibility;
- trading unit;
- corporate-action restrictions;
- current quantity;
- Safety blocks;
- trading halt / data readiness;
- broker/sellability evidence where available.

No hindsight capital redeployment:

```text
capital released and days released earlier are measured separately.
released cash is not assumed to buy later winners.
```

## Validation Artifact Design

VALIDATION_ARTIFACT_DESIGN:

Produce at least:

1. Decision-level shadow evaluation table.
2. Candidate-family aggregate table.
3. Regime aggregate table.
4. Winner-damage table.
5. Churn/re-entry table.
6. Tail-dependence table.
7. PIT proof / leakage audit table.

Decision-level artifact fields:

- date;
- symbol;
- campaign_id;
- baseline PM action;
- baseline quantity;
- lot;
- reduce_intensity;
- representation error;
- persistence evidence;
- deterioration state;
- recovery state;
- candidate variant;
- candidate parameter id;
- shadow action;
- branch;
- PIT proof;
- hypothetical execution feasibility;
- hypothetical exit price authority;
- decision-input fields;
- later evaluation-only outcome fields.

Decision inputs and later outcome fields must be physically/logically separated.

## Sample / Robustness Rules

SAMPLE_SUFFICIENCY_RULE:

Track:

- total unrepresentable REDUCE count;
- one-lot count;
- multi-lot count;
- G1 eligible count;
- G2 eligible count;
- recovery cases;
- winner controls;
- loser controls;
- regime diversity;
- re-entry cases.

If validation examples are too sparse:

```text
INSUFFICIENT_EVIDENCE
```

Do not force PASS.

TAIL_DEPENDENCY_RULE:

Report:

- Top 1 contribution;
- Top 3 contribution;
- Top 5 contribution;
- one-symbol dependency;
- one-campaign dependency;
- one-large-loss dependency;
- one-regime dependency;
- one-immediate-candidate dependency.

61750 must not drive validation. It should not be in the proposed validation period.

## Parameter Selection Rule

PARAMETER_SELECTION_RULE:

Do not choose maximum return. Rank candidates using:

- positive Net Performance Opportunity;
- controlled winner damage;
- MDD quality;
- churn quality;
- sample sufficiency;
- regime robustness;
- tail-dependence control;
- explainability;
- architecture simplicity;
- PIT evidence completeness.

Prefer a robust semantic plateau over a sharp optimum.

Parameter freeze event:

```text
After C0G validation analysis selects one candidate family and parameter semantics,
freeze candidate architecture, persistence semantics, recovery semantics,
deterioration semantics, and representation-error role before any holdout run.
```

HOLDOUT_FROZEN:

```text
YES only after validation selection is complete and documented.
```

## User Run

USER_RUN_REQUIRED:

```text
YES
```

USER_RUN_COMMAND:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2023-01-04 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

Do not append `--json`.

After the user captures the new run id, C0G should perform read-only shadow materialization and performance evaluation against that validation run.

## Required Output Summary

EXISTING_VALIDATION_RUN_REUSABLE:

```text
NO
```

VALIDATION_PERIOD:

```text
2023-01-04 start, 100 business days
```

HOLDOUT_PERIOD:

```text
UNSET
```

PRE_REGISTERED_PARAMETER_CANDIDATE_COUNT:

```text
8
```

HOLDOUT_RETUNING_ALLOWED:

```text
NO
```

LONG_HISTORICAL_BY_CODEX:

```text
NO
```

MUTATING_IMPLEMENTATION_AUTHORIZED:

```text
NO
```

## NEXT_TASK_RECOMMENDATION

```text
Phase31-C0G — User-Run Alternative G Validation Execution / Shadow Performance Evaluation
```

Do not execute C0G in this task.

## Final Questions

### 1. Is the development run fully frozen and excluded from parameter optimization?

```text
YES
```

### 2. Can a clean, chronologically separate validation period be defined?

```text
YES
```

The proposed validation starts 2023-01-04 and runs for 100 business days.

### 3. Can persistence candidates be pre-registered without optimizing against C0A/C0E outcomes?

```text
YES
```

They are semantic families P0/P1/P2/P3, not outcome-selected thresholds.

### 4. Can deterioration and recovery semantics be built entirely from existing Production-visible PIT evidence?

```text
YES
```

They can use PM reason semantics, Strategy Intelligence, continuation, downside, campaign state, and Market Context. Validation may still reveal evidence gaps, but no new market feature is required by C0F.

### 5. Is a new market feature required?

```text
NO
```

### 6. Is a user-operated new Historical validation run required?

```text
YES
```

### 7. If YES, what exact single command should the user execute?

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2023-01-04 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

### 8. Does validation need to use the current B10 architecture?

```text
YES
```

Current-architecture validation is Production-representative. B10 may change portfolio composition, but Alternative G should be validated on naturally occurring current-architecture campaigns.

### 9. What exact conditions will freeze the selected Alternative G parameterization before holdout?

Freeze after validation analysis documents:

- selected candidate family;
- persistence semantics;
- recent-window semantics;
- deterioration sufficiency semantics;
- recovery reset semantics;
- representation-error role;
- PIT proof completeness;
- winner damage / MDD / churn / regime / tail-dependence assessment.

After that, holdout retuning is prohibited.

### 10. Is mutating Alternative G implementation authorized after C0F?

```text
NO
```

### 11. What is the next task once validation evidence is available?

```text
Phase31-C0G — Alternative G Validation Performance Evaluation
```
