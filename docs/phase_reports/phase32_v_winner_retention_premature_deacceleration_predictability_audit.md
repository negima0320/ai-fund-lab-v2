# Phase32-V — Winner Retention / Premature Deacceleration Predictability Audit

## Scope

Target run:

`runtime-test-historical-extended-smoke-20260830T045550298045Z`

Primary reference:

`docs/phase_reports/phase32_u_acceleration_activation_winner_retention_joint_audit.md`

This was a READ-ONLY predictability audit. No source, config, Strategy
parameter, threshold, weight, Risk Pacing, Cash, PM, PC, PS, Runtime, Safety,
G129, or accepted artifact behavior was changed. Codex did not run fresh-run,
resume, replay, or long Historical.

The target run was still `RUNNING` while evidence was inspected. The audit uses
the completed-business-day snapshot available at read time:

- completed business days audited: 78
- audited range: 2022-10-03 through 2023-01-26
- excluded incomplete daily directory observed: 2023-01-27
- source commit recorded by the run: `4ff63ba05a0012c60fce50741a946eed672f8990`

Future price paths are used only after decision-time evidence analysis, as
`CASE_DISCOVERY_AND_CHARACTERIZATION_ONLY`. They are not used to choose
Production thresholds, weights, parameters, or rules.

## Anti-Leakage Method

Production-candidate predictability was evaluated from contemporaneous Runtime
and J-Quants PIT evidence only:

- PM `position_management.json`
- canonical sell semantic evidence
- market context regime
- portfolio policy Risk Pacing intent
- portfolio construction opportunity/quality fields
- J-Quants PIT `technical_features.json`
- same-day execution fill quantities
- Architecture / SoT contracts

Future labels were applied only after those decision-time classifications were
formed, to test descriptive separation between cohorts.

## Cohort Construction

All PM `REDUCE` / `EXIT` decisions in the completed snapshot:

| Item | Count |
| --- | ---: |
| Total sell-side PM decisions | 216 |
| `REDUCE` | 101 |
| `EXIT` | 115 |

U reported 60 `POTENTIAL_HOLD_RETENTION_MISS` cases at its earlier 72BD
snapshot. At the Phase32-V 78BD snapshot, the same characterization style
produced:

| Future characterization cohort | Count |
| --- | ---: |
| Cohort A: potential retention miss, `continued_strength` or `rebound_or_mild_strength` | 73 |
| Cohort B: adverse defensive sell control, `immediate_or_sustained_adverse` | 37 |
| Cohort C: mixed control, `flat_mixed` | 30 |
| Cohort D: insufficient future characterization | 76 |

The future label is not a Production feature. It is used only to build and
compare research cohorts.

## Matching / Stratification

The comparison was stratified by actual decision context where available:

- action: `REDUCE` vs `EXIT`
- PM reason family
- canonical sell state
- PM severity / persistence state
- regime
- Risk Pacing
- campaign return / giveback evidence
- position quantity and sell quantity
- PC opportunity rank and buy-quality action
- PIT technical trend / momentum fields

This avoids comparing arbitrary winners against unrelated losers.

## Decision-Time Evidence Summary

Canonical state distribution:

| Canonical sell state | Count |
| --- | ---: |
| `WEAKENING_BUT_INTACT` | 101 |
| `EXIT_GRADE` | 70 |
| `PERSISTENT_DETERIORATION` | 45 |

PM severity distribution:

| PM severity | Count |
| --- | ---: |
| `PM_SEVERITY_CAUTION` | 63 |
| `PM_SEVERITY_DEFENSIVE` | 38 |
| `PM_SEVERITY_EXIT_CANDIDATE` | 115 |

Persistence state:

| Persistence state | Count |
| --- | ---: |
| `FIRST_OBSERVATION` | 100 |
| `REPEATED_OBSERVATION` | 1 |
| `PERSISTENT` | 45 |
| `WORSENING` | 70 |

Reason family highlights:

| Reason code | Count |
| --- | ---: |
| `strategy_intelligence_sell_side_evidence_connected` | 216 |
| `risk_increased_but_trend_not_broken` | 123 |
| `pm_discrete_control_persistent_deterioration_exit` | 45 |
| `trend_and_opportunity_broken` | 41 |
| `peak_drawdown_warning` | 39 |
| `hard_stop_current_return` | 17 |
| `profit_retention_break` | 16 |
| `weak_hold_score` | 11 |

All audited sell rows had PIT proof `PASS`; no future-dated technical evidence
was consumed by the sell semantic evidence.

## Sell Evidence Agreement

Decision-time agreement classes used existing evidence dimensions only. The
class names are audit labels, not proposed Production thresholds.

| Agreement class | Count |
| --- | ---: |
| `HIGH_CONVICTION_DETERIORATION` | 48 |
| `SINGLE_SIGNAL_DEFENSIVE` | 24 |
| `MODERATE_DEFENSIVE_RISK` | 57 |
| `CONFLICTED_STRONG_CONTINUATION` | 87 |

`DECISION_TIME_RETENTION_CONFLICT` was counted when sell-side risk evidence
coexisted with multiple contemporaneous continuation dimensions such as:

- canonical continuation quality `PASS`
- downside risk `PASS`
- high/full buy-quality evidence
- competitive opportunity rank
- PIT trend above moving-average evidence
- positive short-horizon momentum evidence

Count:

| Conflict group | Count |
| --- | ---: |
| All `DECISION_TIME_RETENTION_CONFLICT` | 137 |
| `REDUCE` conflicts | 85 |
| `EXIT` conflicts | 52 |

By regime:

| Regime | Conflict count |
| --- | ---: |
| BULL | 44 |
| BEAR | 36 |
| RANGE | 31 |
| RECOVERY | 25 |
| CORRECTION | 1 |

By future characterization:

| Future characterization | Conflict count |
| --- | ---: |
| `continued_strength` | 26 |
| `rebound_or_mild_strength` | 20 |
| `immediate_or_sustained_adverse` | 26 |
| `flat_mixed` | 21 |
| `insufficient_future_artifact` | 44 |

This is the key predictability result: decision-time retention conflicts are
real and observable, but they do not cleanly separate potential misses from
correct defensive sells. The same continuation/risk conflict pattern appears
frequently in the adverse-control cohort.

## REDUCE Predictability

Focus reason:

`risk_increased_but_trend_not_broken`

REDUCE rows with that reason remain canonical `WEAKENING_BUT_INTACT`; the
system does preserve REDUCE as a distinct action from EXIT at the same-day
semantic layer.

REDUCE-risk cohort:

| Item | Value |
| --- | ---: |
| Rows | 85 |
| Median strong-continuation dimension count | 4 |
| Median opportunity rank | 22 |
| Median current campaign return | 0.000000 |
| Median removed percentage where executable | 0.250000 |

The dominant REDUCE case is therefore not a confirmed breakdown. It is a
defensive risk-review action while the campaign often still has continuation
evidence. This supports a performance architecture concern:

`RISK_INCREASED_BUT_TREND_NOT_BROKEN` is predictable at decision time, but it is
not by itself enough to identify which sells will later be misses.

Classification:

`PERFORMANCE_INITIATIVE_CANDIDATE`

## EXIT Predictability

EXIT rows divide into two families:

| EXIT family | Count |
| --- | ---: |
| same-day `EXIT_GRADE` | 70 |
| `PERSISTENT_DETERIORATION` | 45 |

The same-day `EXIT_GRADE` rows include hard stop, trend/opportunity broken,
weak hold score, and profit-retention/risk-review families. Those include more
independent deterioration evidence than ordinary REDUCE.

The `PERSISTENT_DETERIORATION` rows are more important for Phase32-V. They are
created by `pm_discrete_control_persistent_deterioration_exit`, usually after
prior REDUCE evidence was not executable as a meaningful lot-sized partial
sale. This can convert repeated defensive-but-intact evidence into a full EXIT.

Classification:

`ARCHITECTURE_LIMITATION` and `PERFORMANCE_INITIATIVE_CANDIDATE`

No correctness defect is proven, because the current SoT permits defensive sell
authority and the future path was not used to relabel specific sells as wrong.

## REDUCE vs EXIT Separation

Current system does distinguish:

```text
WEAKENING_BUT_INTACT -> REDUCE
EXIT_GRADE -> EXIT
PERSISTENT_DETERIORATION -> EXIT
```

The separation exists, but it is not fully aligned with the winner-retention
performance goal because `PERSISTENT_DETERIORATION` can be reached from
repeated or unrepresentable defensive evidence even when continuation fields
remain `PASS`.

This is not a collapsed same-day REDUCE/EXIT classifier. It is a persistence /
discrete-lot escalation pressure.

## Deacceleration Magnitude

REDUCE decisions:

| Item | Count |
| --- | ---: |
| REDUCE PM decisions | 101 |
| REDUCE with zero executable sell quantity | 88 |
| REDUCE with 100-share sell quantity | 9 |
| REDUCE with 200-share sell quantity | 4 |

REDUCE removed-percentage distribution:

| Bucket | Count |
| --- | ---: |
| `<25% or missing/zero` | 94 |
| `25%-50%` | 6 |
| `50%-75%` | 1 |
| `>=75%` | 0 |

Median executable REDUCE percentage: 25%.

Therefore the main magnitude problem is not that the first executable REDUCE is
usually oversized. The main pressure is:

```text
many REDUCE intents are discrete-lot unrepresentable
-> persistence accumulates
-> full EXIT becomes available
```

## Persistence / Reset Behavior

Campaigns with REDUCE followed by later EXIT:

| Item | Count |
| --- | ---: |
| REDUCE -> EXIT paths | 76 |
| Persistent EXIT after REDUCE | 44 |
| Persistent EXIT after REDUCE with intervening recovery/HOLD/ADD evidence | 7 |

Representative persistent EXIT cases with intervening recovery:

| Campaign | Symbol | First REDUCE | EXIT | Intervening recovery count | Notes |
| --- | --- | --- | --- | ---: | --- |
| `pc-15956d4633e944d7-65500-0001` | 65500 | 2022-10-11 | 2022-10-25 | 7 | HOLD recovery evidence appeared after initial `peak_drawdown_warning`; later persistent exit fired on `risk_increased_but_trend_not_broken`. |
| `pc-167804f56dafc5b6-91070-0001` | 91070 | 2022-10-17 | 2022-10-24 | 3 | HOLD recovery appeared before persistent exit. |
| `pc-a0077709b11d934c-45840-0001` | 45840 | 2022-11-15 | 2022-12-01 | 9 | Multiple HOLD recovery days before persistent exit. |
| `pc-215f187deb3d07f6-15180-0001` | 15180 | 2022-11-15 | 2022-11-22 | 3 | Recovery evidence preceded persistent exit. |
| `pc-17ef4bcc61a6bedb-61440-0001` | 61440 | 2022-12-21 | 2023-01-11 | 10 | Long recovery interval before persistent exit. |

Current code has a recovery de-escalation concept for same-day `HOLD` / `ADD`,
and same-day recovery rows report `persistence_state=RECOVERED`. Actual
Runtime evidence nevertheless shows that earlier unrepresentable REDUCE
history can still contribute to later persistent EXIT after intervening
recovery days.

Answer:

`DOES_RENEWED_STRENGTH_RESET_DETERIORATION_SUFFICIENTLY`: NO, not sufficiently
for the winner-retention performance objective. This is a performance
architecture issue, not a correctness repair requirement.

## BULL Retention

BULL sell-side decisions:

| Item | Count |
| --- | ---: |
| BULL sell-side PM decisions | 54 |
| BULL `REDUCE` | 30 |
| BULL `EXIT` | 24 |
| BULL decision-time retention conflicts | 44 |

BULL reason highlights:

| Reason code | Count |
| --- | ---: |
| `risk_increased_but_trend_not_broken` | 31 |
| `pm_discrete_control_persistent_deterioration_exit` | 12 |
| `peak_drawdown_warning` | 11 |
| `profit_retention_break` | 6 |
| `trend_and_opportunity_broken` | 5 |
| `hard_stop_current_return` | 3 |
| `weak_hold_score` | 1 |

BULL is not being ignored by evidence, but the system remains highly defensive
inside BULL. The correct performance framing is not `BULL -> HOLD`; it is:

`when individual-campaign continuation evidence is strong, should defensive
risk evidence require more confirmation before REDUCE-to-EXIT escalation?`

Classification:

`PERFORMANCE_INITIATIVE_CANDIDATE`

## Counterfactual Separation Characterization

After decision-time classifications were fixed, future characterization was
used only to test descriptive separation.

| Dimension | Cohort A potential miss | Cohort B adverse control |
| --- | ---: | ---: |
| Rows | 73 | 37 |
| `REDUCE` / `EXIT` | 40 / 33 | 18 / 19 |
| Median strong-continuation dimensions | 4 | 5 |
| Median opportunity rank | 20.5 | 12.5 |
| Median current campaign return | 0.008772 | 0.000000 |
| `CONFLICTED_STRONG_CONTINUATION` | 31 | 19 |
| Decision-time conflict count | 46 | 26 |
| `risk_increased_but_trend_not_broken` count | 42 | 19 |
| hard deterioration evidence rate | 24.66% | 18.92% |
| moderate risk evidence rate | 68.49% | 72.97% |

Interpretation:

- Cohort A does show many decision-time retention conflicts.
- Cohort B also shows many of the same conflicts.
- The adverse control cohort is not clearly weaker on opportunity rank,
  positive 5D momentum, or strong-continuation dimension count.

Therefore, the current evidence supports a safe research direction but does
not support a simple deterministic HOLD override based only on the observed
dimensions.

## Existing Evidence Sufficiency

Classification:

`EXISTING_EVIDENCE_PARTIAL`

Existing evidence is sufficient to identify:

- defensive risk while trend is not broken,
- unrepresentable REDUCE persistence,
- same-day continuation quality `PASS`,
- downside risk `PASS`,
- opportunity rank / quality context,
- recovery/HOLD/ADD days after REDUCE,
- BULL-specific defensive sell pressure.

Existing evidence is not yet sufficient to reliably distinguish all potential
retention misses from correct defensive sells at decision time. The overlap
between Cohort A and Cohort B is too large for a threshold-style rule to be
accepted from this audit.

## Potential Performance Design Candidates

Ranked conceptually, without thresholds or implementation:

| Rank | Candidate | Rationale | Risk |
| ---: | --- | --- | --- |
| 1 | Persistent-deterioration reset on renewed strength | Directly targets the observed REDUCE -> recovery -> persistent EXIT path; fits existing recovery evidence and SoT. | Must not reset hard stop, genuine breakdown, or severe risk. |
| 2 | EXIT requiring stronger agreement than REDUCE | Keeps REDUCE defensive optionality while making full close require broader confirmation when continuation remains strong. | Needs careful exception paths for hard stop / Safety / broken trend. |
| 3 | REDUCE persistence confirmation requirement | Prevents isolated transient risk warnings from becoming durable EXIT pressure. | May retain weakening names longer in adverse regimes. |
| 4 | REDUCE magnitude throttling | First executable REDUCE is usually not large, so this is secondary. | Lower impact than persistence reset. |
| 5 | Strong-continuation HOLD override | Evidence overlap with adverse controls makes a broad override risky. | Highest false-retention risk. |
| 6 | Winner-retention state distinct from ADD state | Architecturally clean long-term design, but larger scope than the observed narrow blocker. | More complexity and regression surface. |

Best expected risk/reward:

`PERSISTENT_DETERIORATION_RESET_ON_RENEWED_STRENGTH`, paired with stricter
EXIT agreement only for non-hard-stop, non-Safety, non-genuine-breakdown cases.

## Correctness vs Performance Classification

| Finding | Classification |
| --- | --- |
| U-style potential retention misses remain observable | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| Decision-time retention conflicts exist | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| Cohort A vs B separation is weak | `NOT_PREDICTABLE_AT_DECISION_TIME` for a simple HOLD override |
| REDUCE as `WEAKENING_BUT_INTACT` is preserved | `INTENDED_DEFENSIVE_BEHAVIOR` |
| Persistent EXIT after unrepresentable REDUCE | `ARCHITECTURE_LIMITATION` |
| Recovery evidence not fully clearing later persistent EXIT pressure | `ARCHITECTURE_LIMITATION` |
| BULL sell pressure remains high | `PERFORMANCE_INITIATIVE_CANDIDATE` |
| Hard stop / genuine breakdown / Safety exceptions | must remain unsuppressed |

Correctness defect found: NO.

Repair required before Phase32 integration acceptance: NO.

User approval required for next performance initiative: YES.

## Safety Constraint

Any later winner-retention initiative must never suppress:

- `hard_stop_current_return`
- genuine `trend_and_opportunity_broken`
- Safety hard constraints
- broker or corporate-action blocks
- severe liquidity or risk failures

Winner retention must not become loss denial.

## NO CODE CHANGE

Confirmed. Phase32-V did not modify source or config. The only created artifact
is this READ-ONLY phase report.

## Future Information Separation

Decision-time conflict classifications use only PIT and contemporaneous
Runtime evidence. Future price movement is used only as
`CASE_DISCOVERY_AND_CHARACTERIZATION_ONLY` after decision-time features are
fixed, and is not used to infer Production thresholds, weights, tiers, or
parameter changes.

## Final Judgment

1. `CAN_PREMATURE_LOOKING_SELLS_BE_IDENTIFIED_USING_ONLY_DECISION_TIME_PIT_EVIDENCE`:
   PARTIALLY. Decision-time retention conflicts can be identified, but current
   evidence does not reliably distinguish future retention misses from correct
   defensive sells.
2. `HOW_MANY_DECISION_TIME_RETENTION_CONFLICTS_EXIST`: 137 in the 78BD
   completed snapshot.
3. `WHAT_DISTINGUISHES_RETENTION_MISSES_FROM_CORRECT_DEFENSIVE_SELLS`: no
   stable single distinction was proven. Potential misses and adverse controls
   both show continuation `PASS`, downside `PASS`, defensive risk evidence, and
   frequent opportunity/trend support.
4. `IS_REDuce_persistence_or_EXIT_ESCALATION_TOO_AGGRESSIVE`: YES as a
   performance architecture finding, especially for unrepresentable REDUCE
   persistence escalating to full EXIT.
5. `DOES_RENEWED_STRENGTH_RESET_DETERIORATION_SUFFICIENTLY`: NO for the
   winner-retention performance objective; 7 persistent EXIT paths had
   intervening recovery/HOLD/ADD evidence.
6. `IS_BULL_WINNER_RETENTION_TOO_DEFENSIVE`: YES as a performance initiative
   candidate; BULL had 54 sell-side decisions and 44 decision-time retention
   conflicts.
7. `CAN_EXISTING_EVIDENCE_SUPPORT_A_SAFE_WINNER_RETENTION_IMPROVEMENT`: YES,
   partially. Existing evidence supports a narrow persistence/reset and
   exit-confirmation design, not a broad HOLD override.
8. `WHICH_PERFORMANCE_DESIGN_HAS_THE_BEST_EXPECTED_RISK_REWARD`:
   persistent-deterioration reset on renewed strength, with stronger EXIT
   agreement for non-hard-stop, non-Safety, non-genuine-breakdown cases.
9. `IS_ANY_CORRECTNESS_REPAIR_REQUIRED`: NO.
10. `SHOULD_WINNER_RETENTION_BE_THE_NEXT_USER_APPROVED_PERFORMANCE_INITIATIVE`:
    YES.

Final classification:

`PHASE32_V_WINNER_RETENTION_PREDICTABILITY_PARTIAL_EXISTING_EVIDENCE_SUPPORTS_NARROW_PERFORMANCE_DESIGN`
