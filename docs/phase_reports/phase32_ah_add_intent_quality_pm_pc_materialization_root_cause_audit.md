# Phase32-AH — ADD Intent Quality + PM→PC Materialization Root-Cause Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Evidence window: `2022-10-03` through `2023-10-10`
- Business days used: `252`
- Mode: READ-ONLY root-cause audit

No code, config, runtime state, Strategy parameter, threshold, weight, ADD tier, Cash policy, BQ, Risk Pacing, PC, PS, Runtime, comparator design, resume, recover, replay, fresh-run, or long Historical action was performed.

No future return, future price, final campaign outcome, or Historical profitability was used to decide whether any ADD should have occurred.

## Primary Findings

Phase32-AG framed the 19 missing `76470` cases as PM ADD decisions that did not materialize as PC ADD competitors. AH refines the first boundary:

```text
Runtime PM decision artifact: ADD
-> Strategy PM artifact: HOLD + structured_add_worthiness_no_add
-> PC member: pm_action=HOLD, membership_intent=RETAIN
-> PC ADD competitor: absent
-> PS: existing_position_baseline_preserved_no_transaction_delta
```

The 19 cases are one repeated mechanism, not 19 independent PC failures. The shared cause is:

```text
prior_add_history_limits_incremental_add
```

`76470` had already accumulated 5 ADD events by `2022-12-06`. From `2022-12-07` onward, Strategy Intelligence / Strategy PM blocked further incremental ADD worthiness and converted the runtime PM ADD signal into HOLD for downstream PC/PS.

The more fundamental finding is that current PM `ADD` is a mixed signal. It strongly indicates:

```text
existing campaign remains strong / no loss averaging / rank remains high
```

but it does not by itself prove:

```text
another executable lot has positive incremental investment value now
```

Current source explicitly states this. The PM trace records partial compatibility, but says incremental investment value is not separately proven.

## Source Contract Evidence

Runtime PM trigger booleans define ADD-like evidence as:

- `strong_trend_continuation`: `add_score >= 0.72`
- `opportunity_rank_still_high`: `buy_rank <= 5`
- `no_loss_averaging`: `current_return > 0.0`
- `add_downside_risk_contained`: `downside < 0.50`

Runtime PM expected-edge trace for ADD states:

```text
Legacy ADD branch indicates strong continuation/rank/risk evidence,
but incremental investment value is not separately proven.
```

ADD investment evidence then requires all of:

- campaign continuation PASS
- expected edge PASS
- incremental value PASS
- opportunity cost PASS
- no-loss averaging PASS

Only when expected edge, campaign, opportunity cost, and no-loss all pass does incremental value become `POSITIVE`.

Strategy PM applies Strategy Intelligence ADD worthiness before PC. If a position has action `ADD` but structured ADD worthiness is not PASS, it converts action to `HOLD` and adds:

```text
structured_add_worthiness_no_add
```

Structured ADD worthiness fails when any of these applies:

- campaign identity incomplete
- continuation quality not PASS
- downside risk blocks ADD
- prior ADD history event count >= 5
- prior REDUCE history requires ADD review

## A — Audit of the 19 Missing `76470` ADDs

All 19 cases share the same campaign:

```text
pc-8b52b4c89fd002ad-76470-0001
```

All 19 have:

- runtime PM action: `ADD`
- PM reasons: `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`
- PM `quantity_requested`: `0.0`
- Strategy Intelligence ADD worthiness failure reason: `prior_add_history_limits_incremental_add`
- Strategy PM output action: `HOLD`
- PC member `pm_action`: `HOLD`
- PC ADD competitor presence: `NO`
- PS result: existing position baseline retained, no transaction delta

Per-date evidence:

| Date | PM Action | BQ Action / Band | PM Qty | Current Qty | SI Reason | Strategy PM / PC Member | PS Result | Classification |
| --- | --- | --- | ---: | ---: | --- | --- | --- | --- |
| `2022-12-07` | ADD | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `0.0` | `1800` | `prior_add_history_limits_incremental_add` | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-08` | ADD | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-09` | ADD | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-16` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-21` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-22` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-23` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-27` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-28` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-29` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2022-12-30` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-04` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-05` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-06` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-10` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-11` | ADD | `REDUCED_ALLOCATION_ONLY / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-12` | ADD | `BUY_WAIT / BUY_WAIT` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-13` | ADD | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |
| `2023-01-16` | ADD | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `0.0` | `1800` | same | HOLD | no transaction delta | `EXPECTED_PC_ELIGIBILITY_REJECTION` |

Why PM ADD became PS HOLD/no-transaction-delta:

```text
Runtime PM ADD
-> Strategy PM structured_add_worthiness rejects incremental ADD because prior ADD count >= 5
-> action rewritten to HOLD
-> PC sees only HOLD/RETAIN
-> PS preserves baseline existing position with zero transaction delta
```

This is not a PC competitor-construction disappearance. The ADD semantics disappear before PC capital competition.

## B — One Repeated Mechanism or 19 Independent Cases

Classification:

```text
ONE_REPEATED_STRUCTURAL_MECHANISM
```

The first date is:

```text
2022-12-07
```

Repeated conditions:

| Field | Value |
| --- | --- |
| campaign | `pc-8b52b4c89fd002ad-76470-0001` |
| prior ADD history count | `5` |
| last ADD date | `2022-12-06` |
| reduce history count | `0` |
| campaign identity | `COMPLETE` |
| current position authority | `COMPLETE` |
| continuation quality | `PASS` |
| downside risk | `PASS` |
| structured ADD worthiness blocker | `prior_add_history_limits_incremental_add` |

The mechanism is persistent campaign-state gating. It is not stale idempotency, campaign identity split, missing PC state, or 19 separate independent decisions.

## C — Positive Evidence -> Final BLOCKED Cases

AG referred to 3 rows where lower-level PASS/POSITIVE evidence became final `BLOCKED`. AH re-ran the strict condition:

```text
eligibility = PASS
incremental_value = POSITIVE/PASS
opportunity_cost = PASS
final interaction = BLOCKED
```

This strict query found 6 rows. They split into two groups.

### Original Quality-BLOCKED Compression Group

| Date | Symbol | Quality | Interaction | Lower Evidence | Late Evidence | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| `2022-10-21` | `94320` | `BLOCKED` | `BLOCKED` | eligibility PASS, incremental POSITIVE, opportunity-cost PASS | `entry_admission_action=NO_ADD`, `OVERHEATED_DECELERATING_ENTRY`, `ADD_NO_POSITIVE_DELTA` | `DEPLOYMENT_SUPPRESSION` |
| `2022-11-10` | `99840` | `BLOCKED` | `BLOCKED` | eligibility PASS, incremental POSITIVE, opportunity-cost PASS | safety-cap terminal / executable quantity zero | `JUSTIFIED_LATE_GATE` |
| `2023-06-20` | `21340` | `BLOCKED` | `BLOCKED` | eligibility PASS, incremental POSITIVE, opportunity-cost PASS | `entry_admission_action=NO_ADD`, `OVERHEATED_DECELERATING_ENTRY`, `ADD_NO_POSITIVE_DELTA` despite executable lot evidence | `DEPLOYMENT_SUPPRESSION` |

### Additional Interaction-BLOCKED Terminal Group

| Date | Symbol | Quality | Interaction | Lower Evidence | Late Evidence | Classification |
| --- | --- | --- | --- | --- | --- | --- |
| `2022-11-15` | `99840` | `COMPARABLE_MARGINAL` | `BLOCKED` | eligibility PASS, incremental POSITIVE, opportunity-cost PASS | `ADD_SAFETY_CAP_BOUND`, terminal for current capital authority | `JUSTIFIED_LATE_GATE` |
| `2022-11-16` | `99840` | `COMPARABLE_MARGINAL` | `BLOCKED` | same | `ADD_SAFETY_CAP_BOUND`, terminal for current capital authority | `JUSTIFIED_LATE_GATE` |
| `2022-11-21` | `99840` | `COMPARABLE_MARGINAL` | `BLOCKED` | same | `ADD_SAFETY_CAP_BOUND`, terminal for current capital authority | `JUSTIFIED_LATE_GATE` |

Findings:

- Evidence is not simply lost.
- In the two non-safety cases, a coarse entry-admission / opportunity-quality block overrides lower-level positive ADD evidence and prevents deployment.
- In the four safety/cap-bound cases, late blocking is justified by executable quantity or safety-cap authority.

Classification:

```text
MIXED: DEPLOYMENT_SUPPRESSION for 2 rows, JUSTIFIED_LATE_GATE for 4 rows
```

Correctness defect:

```text
UNCONFIRMED
```

Performance architecture concern:

```text
YES
```

## D — PM ADD Semantic Contract

Current PM ADD means a mixture:

```text
C — existing position remains strong and may be eligible for ADD consideration,
but PM ADD alone does not prove positive incremental investment value.
```

Trigger interpretation:

| Trigger | Meaning |
| --- | --- |
| `strong_trend_continuation` | `HOLD_VALUE` plus possible incremental support |
| `opportunity_rank_still_high` | `BOTH`, but rank alone is uncalibrated and not marginal capital value |
| `no_loss_averaging` | `GATE_ONLY`; prevents averaging down, does not prove next-lot value |
| `add_downside_risk_contained` | `GATE_ONLY / HOLD_VALUE`; risk permits exposure, not necessarily another lot |
| campaign health | `HOLD_VALUE` |
| renewed strength / acceleration | `INCREMENTAL_ADD_VALUE` if explicitly present, but often not decisive in PM output |

Every PM ADD in the 252BD window used the same reason combination:

```text
strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging
```

This supports the conclusion that PM ADD is currently a persistent continuation/rank/no-loss signal more than a distinct next-lot expected-value signal.

## E — HOLD Strength vs ADD Strength

Current PM can partially distinguish ADD from HOLD, but not with a fully separate incremental-add value contract.

PM ADD vs HOLD decision-time summary:

| Field | PM ADD Average | PM HOLD Average |
| --- | ---: | ---: |
| action score | `0.811` | `0.521` |
| BQ score | `0.740` | `0.637` |
| BQ rank | `2.59` | `16.36` |
| unrealized return | `20.1%` | `11.4%` |
| 5D momentum | `7.6%` | `3.5%` |
| 20D momentum | `42.0%` | `29.3%` |
| trend close / MA20 | `1.108` | `1.090` |

So ADD is clearly stronger than average HOLD on the legacy PM score/rank/return axes.

But the separation is not enough to prove next-lot value:

- all PM ADDs have `quantity_requested = 0.0`;
- PM expected-edge trace says incremental value is not separately proven;
- ADD investment evidence and Strategy Intelligence can still reject incremental ADD;
- PM ADD can persist for many consecutive days without a fresh event trigger.

Classification:

```text
PARTIAL_SEPARATION
```

First semantic boundary:

```text
PM action scoring labels continuation/rank/no-loss as ADD, before incremental next-lot value is independently established.
```

## F — PM ADD vs PM HOLD at Decision Time

PM ADD is not random relative to HOLD. It selects stronger, higher-ranked, profitable, better momentum positions.

However, HOLD and ADD share many concepts:

- trend continuation
- positive expected edge
- downside containment
- campaign health
- no exit/reduce reason

PM ADD differs mainly by higher action score, high opportunity rank, and no-loss state. It does not consistently require fresh acceleration, new breakout, improving expected edge versus prior baseline, or explicit marginal-lot opportunity.

Classification:

```text
PARTIAL_SEPARATION
```

## G — Repeated ADD Persistence

PM emitted `118` ADD decisions across `11` campaigns.

Campaign ADD counts:

| Campaign | Symbol | ADD Count | Max Consecutive BD Streak |
| --- | --- | ---: | ---: |
| `pc-8b52b4c89fd002ad-76470-0001` | `76470` | `25` | `12` |
| `pc-925de11083435873-99840-0001` | `99840` | `18` | `18` |
| `pc-f6f650ff3364b80b-94320-0001` | `94320` | `15` | `12` |
| `pc-47f89bc0fb3b790c-67310-0001` | `67310` | `15` | `3` |
| `pc-df47de7d57274254-43880-0001` | `43880` | `12` | `8` |
| `pc-f3186b6520780cea-21340-0001` | `21340` | `9` | `4` |
| `pc-21eead760e37aeb3-40520-0001` | `40520` | `7` | `5` |
| `pc-f3bd989f40c52bdf-94340-0001` | `94340` | `6` | `6` |
| `pc-3aaff341fad7ae34-54010-0001` | `54010` | `6` | `5` |
| `pc-fc24211759c14527-59350-0001` | `59350` | `3` | `2` |
| `pc-c22becf8dd898cd9-59550-0001` | `59550` | `2` | `2` |

Critical conclusion:

```text
PM ADD can remain persistently true like HOLD.
```

It is not necessarily an event-like renewed marginal opportunity signal.

## H — 9 Filled ADDs: Decision-Time Quality Audit

Classification uses only decision-time evidence.

| Date | Symbol | PM Score | BQ Action / Band | PC Quality | PC Interaction | Accepted Weight | Classification |
| --- | --- | ---: | --- | --- | --- | ---: | --- |
| `2022-10-06` | `94340` | `0.783` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.013786` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-10-12` | `94340` | `0.767` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.014072` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-10-13` | `94340` | `0.760` | `REDUCED_ALLOCATION_ONLY / MEDIUM` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.014062` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-11-01` | `94320` | `0.829` | `REDUCED_ALLOCATION_ONLY / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.015304` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-11-29` | `76470` | `0.803` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `DEPLOY_ELIGIBLE` | `0.002405` | `STRONG_INCREMENTAL_ADD_CASE` |
| `2022-11-30` | `76470` | `0.811` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.002417` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-12-01` | `76470` | `0.810` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.002414` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-12-02` | `76470` | `0.774` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.002321` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |
| `2022-12-06` | `76470` | `0.812` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `COMPARABLE_MARGINAL` | `CASH_PREFERRED` | `0.002403` | `PLAUSIBLE_INCREMENTAL_ADD_CASE` |

Summary:

| Filled ADD Classification | Count |
| --- | ---: |
| `STRONG_INCREMENTAL_ADD_CASE` | `1` |
| `PLAUSIBLE_INCREMENTAL_ADD_CASE` | `8` |
| `HOLD_LIKE_ADD_CASE` | `0` |
| `WEAK_OR_AMBIGUOUS_ADD_CASE` | `0` |

The 9 filled ADDs were not pure HOLD-like cases once PC evidence is considered. But only one reached a strong deploy-eligible interaction at decision time.

## I — 118 ADD Intent Quality Distribution

Decision-time classification across all PM ADD decisions:

| Intent Quality | Count |
| --- | ---: |
| `CLEAR_INCREMENTAL_OPPORTUNITY` | `1` |
| `PLAUSIBLE_INCREMENTAL_OPPORTUNITY` | `10` |
| `HOLD_STRENGTH_ONLY` | `107` |
| `INSUFFICIENT_INCREMENTAL_EVIDENCE` | `0` |
| `UNKNOWN` | `0` |

Interpretation:

- PM ADD quality is high relative to HOLD.
- But most PM ADDs are not clear incremental opportunities under downstream ADD evidence.
- The major gap is semantic specificity: PM ADD frequently means “strong enough to keep/add-consider” rather than “deploy another lot now.”

## J — Root-Cause Separation

| Problem Class | Evidence | Count / Impact | Judgment |
| --- | --- | ---: | --- |
| `PM_PROBLEM` | PM ADD always same continuation/rank/no-loss reasons; PM source says incremental value not separately proven; ADD persists in long streaks | `107 / 118` HOLD-strength-only | `YES`, performance semantics |
| `PM_PC_BRIDGE_PROBLEM` | 19 runtime PM ADDs converted to Strategy PM HOLD due structured ADD worthiness | `19` | `YES`, but largely intentional gate |
| `PC_COMPRESSION_PROBLEM` | lower-level PASS/POSITIVE evidence can become coarse `BLOCKED` or zero accepted weight | `2` material non-safety suppressions; `4` justified cap blocks | `YES`, limited |
| `EXPECTED_FILTERING` | PC/Strategy Intelligence correctly blocks repeated ADD after 5 prior ADDs and safety cap conditions | material | `YES` |
| `MIXED` | PM signal, bridge gate, PC compression, and expected filtering all contribute | global | `PRIMARY` |

Primary classification:

```text
MIXED
```

No correctness repair is proven mandatory in AH. Performance design work is justified, but the next work should start by separating PM ADD intent semantics from executable incremental capital authority, not by tuning thresholds or designing a full comparator immediately.

## Final Judgment

1. `WHY_DID_THE_19_76470_PM_ADDS_NOT_REACH_PC`: They were converted from runtime PM `ADD` to Strategy PM `HOLD` before PC because structured ADD worthiness failed on `prior_add_history_limits_incremental_add` after 5 prior ADD events.
2. `IS_THIS_ONE_REPEATED_MECHANISM_OR_19_INDEPENDENT_CASES`: `ONE_REPEATED_STRUCTURAL_MECHANISM`, beginning `2022-12-07`.
3. `ARE_THE_3_POSITIVE_TO_BLOCKED_CASES_ACTUAL_DEPLOYMENT_SUPPRESSION`: `MIXED`; strict query found 6 interaction-BLOCKED rows. Two are actual non-safety deployment suppression/compression cases, four are justified late gates dominated by safety/cap/executable quantity.
4. `WHAT_DOES_PM_ADD_SEMANTICALLY_MEAN_TODAY`: `C`, a mixture; primarily strong continuation / high rank / no-loss ADD consideration, not standalone proof of positive next-lot incremental value.
5. `DOES_PM_DISTINGUISH_HOLD_VALUE_FROM_INCREMENTAL_ADD_VALUE`: `PARTIALLY`; ADD is stronger than HOLD on PM/BQ/rank/momentum axes, but incremental next-lot value is not independently proven in PM.
6. `IS_THERE_CLEAR_DECISION_TIME_SEPARATION_BETWEEN_PM_ADD_AND_HOLD`: `PARTIAL_SEPARATION`.
7. `IS_PM_ADD_PERSISTENT_WITHOUT_FRESH_EVIDENCE`: `YES`; 118 ADDs across 11 campaigns include long consecutive streaks up to 18BD, and all share the same reason-code pattern.
8. `HOW_MANY_OF_118_ADDS_HAVE_CLEAR_INCREMENTAL_OPPORTUNITY_EVIDENCE`: `1` clear, `10` plausible, `107` HOLD-strength-only under downstream evidence.
9. `HOW_MANY_OF_THE_9_FILLED_ADDS_WERE_STRONG_INCREMENTAL_CASES_AT_DECISION_TIME`: `1`; the other `8` were plausible incremental ADD cases.
10. `IS_THE_PRIMARY_PROBLEM_PM_ADD_QUALITY, PM_PC_BRIDGE, PC_COMPRESSION, EXPECTED_FILTERING, OR MIXED`: `MIXED`, led by PM ADD semantic overbreadth plus expected Strategy Intelligence/PC filtering.
11. `IS_A_CORRECTNESS_REPAIR_REQUIRED`: `UNCONFIRMED / NO_MANDATORY_REPAIR_FROM_AH`; no fail-closed or provenance correctness defect is proven.
12. `IS_PERFORMANCE_DESIGN_WORK_JUSTIFIED`: `YES`; the design should first separate HOLD-strength PM ADD from executable incremental ADD authority.
13. `WHAT_SHOULD_BE_DONE_NEXT`: Audit/design a read-only PM ADD intent taxonomy that distinguishes `HOLD_STRENGTH`, `ADD_CONSIDERATION`, and `EXECUTABLE_INCREMENTAL_ADD_CANDIDATE`, then re-run artifact-only classification before any comparator or parameter change.

Final classification:

```text
MIXED
```
