# Phase31-B1 — ADD Intent → Positive Increment Funnel / Winner Amplification Root-Cause Audit

## PRIMARY_JUDGMENT

`ADD_INTENT_MATERIALIZATION_IS_NARROW_AND_CAP_DRIFT_SUPPRESSES_STRONG_94320_ADD_AFTER_INITIAL_WINNER_AMPLIFICATION`

PM `ADD` is not a direct instruction to buy more shares. The current canonical contract is conditional: PM marks an existing position as ADD-worthy candidate evidence, Portfolio Construction decides whether that ADD can increase `target_weight`, Position Sizing converts only a positive target/current delta into quantity, and Runtime Planning maps only positive existing-position quantity delta to `BUY_ADD`.

In the current completed-day evidence, the larger numeric bottleneck is upstream materialization from PM ADD to positive PC increment: only 9 of 63 PM ADD intents became positive increments. The primary first-drop reason is Expected Edge weakening versus the same-campaign baseline. A second material pattern is baseline/cap drift: after 94320 had already been amplified, current position weight sat above the active `maximum_position_weight`/strategy cap, so the existing baseline was retained with no further increment. B0 remains material because the 9 positive ADDs were not all filled: three were reserved-cash-pruned and one was dynamic-cash review-required.

Performance implementation remains unauthorized.

## Required Fields

| Field | Value |
| --- | --- |
| `TARGET_RUN` | `runtime-test-historical-extended-smoke-20260818T015851711672Z` |
| `COMPLETED_DAY_SCOPE` | 74 completed business days in `run_state.json`, `2022-08-10` through `2022-11-29`; run status at audit: `RUNNING`. |
| `PM_ADD_SEMANTIC` | PM `ADD` means: existing position remains eligible for possible incremental investment if downstream marginal-value, opportunity-cost, concentration/headroom, lot, safety, and cash conditions justify it. It does not mean "increase target capital now" and is not sufficient to require a positive increment. |
| `PM_ADD_COUNT` | 63 PM ADD intents. |
| `PC_POSITIVE_INCREMENT_COUNT` | 9. |
| `INTENT_TO_POSITIVE_INCREMENT_RATE` | 14.3% (`9 / 63`). |
| `PS_POSITIVE_BUY_ADD_COUNT` | 9. |
| `BUY_ADD_FILL_COUNT` | 5 inferred same-day BUY_ADD fills, gross notional `152,130`. |
| `POSITIVE_INCREMENT_TO_FILL_RATE` | 55.6% (`5 / 9`). |
| `ADD_TARGET_WEIGHT_UNCHANGED_COUNT` | 54 zero-positive-increment ADD intents. |
| `ADD_TARGET_WEIGHT_UNCHANGED_BREAKDOWN` | Expected Edge weakening: 35; baseline/cap drift first blocker: 16; current weight already at/above target after ADD-worthiness/entry-admission no-add: 2; baseline missing / Expected Edge unknown: 1. |
| `BASELINE_CAP_DRIFT_NO_INCREMENT_COUNT` | 43 PS reason-code occurrences; 16 primary first-drop cases. The 43 includes downstream annotations on rows whose earlier first-drop was Expected Edge weakening. |
| `BASELINE_CAP_DRIFT_SEMANTIC` | Baseline is the authoritative existing-position current weight/quantity preserved for HOLD/ADD when no positive increment is accepted. Cap drift is passive current-weight drift above the active `maximum_position_weight`/strategy cap, usually from price/portfolio movement or prior fills, where no new risk-increasing quantity is added. PS accepts the retained baseline with `EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT`; this is legitimate no-risk-increase behavior, but it can suppress a strong winner ADD once the position is already above cap. |
| `STRONG_PIT_ADD_ZERO_INCREMENT_COUNT` | 18 relatively strong PIT ADD zero-increment cases using Production-visible evidence: opportunity rank <= 3, Expected Edge PASS, Incremental Investment Value POSITIVE, Opportunity Cost PASS, No-loss averaging PASS, but zero target/quantity increment. All observed cases were 94320. |
| `STRONG_PIT_ADD_ZERO_INCREMENT_EXAMPLES` | 94320 on `2022-09-21`: rank 1, score `0.42951161`, Expected Edge `IMPROVING`, Incremental Value `POSITIVE`, Opportunity Cost `PASS`, current/target `0.191583`, normal target `0.18`, max weight `0.18`, PS reason `EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT`. 94320 on `2022-10-12`: current/target `0.190100`, normal target `0.18`, max weight `0.18`, same PASS evidence and cap-drift no-increment. 94320 on `2022-11-15`: current/target `0.183720`, normal target `0.18`, max weight `0.18`, same PASS evidence and cap-drift no-increment. |
| `94320_WITHIN_SYMBOL_CONTROL` | 94320 became positive ADD when Expected Edge was `IMPROVING`, Incremental Value `POSITIVE`, Opportunity Cost `PASS`, and current weight was still below the effective target/cap headroom (`2022-08-19` through `2022-09-20`, 9 cases). It stayed zero when the baseline was missing (`2022-08-16`), when Expected Edge weakened versus baseline (`35` later zero rows), when ADD-worthiness/entry-admission no-add preserved target at current weight (`2022-08-31`, `2022-09-14`), or when current weight drifted above the `0.18` cap and baseline retention prevented more risk (`16` primary cap-drift rows from `2022-09-21` onward). |
| `OTHER_REPEATED_STRONG_ADD_SUPPRESSION` | `NO` in current completed-day evidence. 94320 is the only repeated strong-PIT zero-increment ADD suppression pattern observed. |
| `PRIMARY_ADD_BOTTLENECK` | `BOTH`. Numerically, the larger loss is `INTENT_TO_INCREMENT`; architecturally, B0 also confirmed `INCREMENT_TO_EXECUTION` loss after positive ADD. |
| `RELATIONSHIP_TO_B0` | Scenario C. Upstream ADD materialization is narrow, and some positive ADDs are later cash-starved by BUY_NEW processing order. |
| `ARCHITECTURE_DEFECT` | `PARTIAL`. PM ADD's conditional semantics are expected and legitimate; Expected Edge weakening and cap/no-headroom are not automatically defects. The defect/gap is that winner-amplification philosophy has no explicit marginal-capital contract that reconciles ADD materialization with cap drift and BUY_NEW/ADD priority. |
| `WINNER_AMPLIFICATION_GAP` | `YES`. The system can identify a recurring winner-like ADD candidate, amplify it early, then stop further increment because of cap drift, and B0 shows that even positive ADDs can lose reserved cash to BUY_NEW processing order. |
| `PERFORMANCE_IMPLEMENTATION_AUTHORIZED` | `NO` |
| `NEXT_RECOMMENDATION` | `jointly design ADD materialization + BUY_NEW/ADD priority` |

## Canonical ADD Contract

Current SoT establishes this authority chain:

```text
Position Management ADD intent
-> Portfolio Construction target membership / target_weight
-> Position Sizing target quantity / quantity_delta_candidate
-> Runtime Planning BUY_ADD only when existing holding has positive quantity_delta_candidate
-> Pending / Submit / Fill
```

The key boundaries are:

- PM owns existing-position HOLD / ADD / REDUCE / EXIT intent evidence; it does not own quantity or submit permission.
- PC owns target portfolio and `target_weight`.
- PS owns `quantity_delta_candidate`.
- Runtime must not recalculate ADD, ranking, or sizing.

The ADD semantic is therefore closest to option B from the task: "position remains eligible for possible incremental investment if downstream marginal-value conditions justify it." It is not option A.

## Complete ADD Funnel

| Stage | Count |
| --- | ---: |
| PM ADD intent | 63 |
| PC receives ADD intent | 63 |
| PC positive ADD increment | 9 |
| PS positive BUY_ADD quantity | 9 |
| Runtime Planning BUY_ADD | 9 |
| Pending included | 5 |
| Pending cash-pruned | 3 |
| Pending review-required | 1 |
| BUY_ADD fill | 5 |

Primary first-drop classification across all 63 PM ADD intents:

| Primary first-drop reason | Count |
| --- | ---: |
| `EXPECTED_EDGE_NOT_SUFFICIENT:WEAKENING` | 35 |
| `BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT` | 16 |
| `FILLED` | 5 |
| `PENDING_RESERVED_CASH_PRUNE` | 3 |
| `CURRENT_WEIGHT_ALREADY_AT_OR_ABOVE_TARGET` | 2 |
| `EXPECTED_EDGE_UNKNOWN_OR_BASELINE_MISSING` | 1 |
| `PENDING_REVIEW_REQUIRED` | 1 |

## ADD_TARGET_WEIGHT_UNCHANGED

`ADD_TARGET_WEIGHT_UNCHANGED` is mostly a PC target-weight result, not a PS bug. PS reports it when ADD has no positive `target_weight - current_weight`, accepted incremental weight, or lot-aware accepted incremental weight to convert into a transaction.

For the 54 zero-increment ADDs:

- 35 failed Expected Edge because current score weakened versus the PIT same-campaign baseline.
- 16 were primary cap-drift no-increment rows after 94320 current weight was already above the `0.18` cap.
- 2 had current weight already at the resolved target after ADD-worthiness / entry-admission no-add preserved baseline.
- 1 lacked the required prior same-campaign baseline on the first ADD day and failed closed as Expected Edge unknown.

This is mostly legitimate conditional ADD behavior. The concerning part is not the existence of zero increments; it is that strong 94320 ADD evidence later has no marginal-capital path once passive cap drift is present.

## Baseline / Cap Drift

In PS, existing positions with PM `HOLD` or `ADD` preserve baseline quantity unless PC supplies a positive increment. If target/current delta is zero, PS emits zero quantity. If the retained target/current baseline is above `maximum_position_weight`, PS adds `EXISTING_BASELINE_CAP_DRIFT_ACCEPTED_NO_INCREMENT` instead of forcing a sell or adding more.

Representative 94320 cap-drift rows:

| Date | Current weight | Target weight | Normal target | Max weight | Excess over cap | Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2022-09-21` | `0.191583` | `0.191583` | `0.180000` | `0.180000` | `0.011583` | `0.42951161` |
| `2022-09-26` | `0.188976` | `0.188976` | `0.180000` | `0.180000` | `0.008976` | `0.47728301` |
| `2022-10-12` | `0.190100` | `0.190100` | `0.180000` | `0.180000` | `0.010100` | `0.42547970` |
| `2022-11-15` | `0.183720` | `0.183720` | `0.180000` | `0.180000` | `0.003720` | `0.37496898` |

Across the 16 primary cap-drift cases, total excess-over-cap weight was `0.167897`, average `0.010494`. Measured headroom was zero in those rows.

## 94320 Within-Symbol Control

Positive-increment 94320 ADD days:

| Date | Current weight | Target weight | Positive increment | Score | Pending / fill |
| --- | ---: | ---: | ---: | ---: | --- |
| `2022-08-19` | `0.043469` | `0.087200` | `0.043731` | `0.16353315` | PRUNE |
| `2022-08-22` | `0.043083` | `0.090702` | `0.047619` | `0.18238572` | fill |
| `2022-08-23` | `0.086446` | `0.118704` | `0.032258` | `0.20726618` | fill |
| `2022-08-24` | `0.114841` | `0.157792` | `0.042951` | `0.23220610` | PRUNE |
| `2022-08-30` | `0.114120` | `0.149834` | `0.035714` | `0.21796380` | fill |
| `2022-09-01` | `0.147752` | `0.180000` | `0.032248` | `0.30359042` | PRUNE |
| `2022-09-15` | `0.143396` | `0.173073` | `0.029677` | `0.31487129` | dynamic-cash review |
| `2022-09-16` | `0.144695` | `0.180000` | `0.035305` | `0.36715033` | fill |
| `2022-09-20` | `0.175226` | `0.190094` | `0.014868` | `0.39363052` | fill |

Zero-increment 94320 groups:

- `2022-08-16`: first ADD day lacked prior same-campaign Expected Edge baseline, so fail-closed.
- `2022-08-25` to `2022-09-13` and many later rows: Expected Edge weakened versus the PIT baseline, so Incremental Value stayed `UNKNOWN`.
- `2022-08-31` and `2022-09-14`: Expected Edge and Incremental Value passed, but ADD-worthiness / entry-admission no-add preserved current target.
- `2022-09-21` onward on selected dates: Expected Edge and Incremental Value passed, but current weight was already above the active `0.18` cap, so baseline cap drift prevented further increment.

## Outcome Labels

Omitted. The target run is still active and this audit did not require future outcome labels. No future returns, future-known winner labels, or later campaign outcomes were used in the causal classification above.

## Final Questions

### 1. Is PM ADD currently being translated into incremental capital often enough to fulfill the intended winner-amplification philosophy?

`NO`.

The intended semantics are conditional, so 100% translation is not expected. But 9 of 63 conversion, combined with 18 strong-PIT zero-increment 94320 cases after early amplification, shows the current materialization path is too narrow to fully express winner amplification.

### 2. When a strong ADD does become executable, can BUY_NEW still consume capital first and prevent the ADD?

`YES`.

B0 showed 94320 BUY_ADD was cash-pruned on `2022-08-19` and `2022-08-24` after prior BUY_NEW reserved-notional includes consumed cash.

### 3. Based on current PIT evidence, should the next design task address:

`C. both together`

The next design should address both ADD intent -> target-weight materialization and BUY_NEW vs BUY_ADD marginal-capital priority. Do not implement the design in B1.
