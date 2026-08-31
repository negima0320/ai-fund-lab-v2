# Phase32-BK - Lot-Blocked REDUCE Harmful vs Beneficial PIT Semantic Separability READ-ONLY Audit

## Scope

Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`

Fixed evidence cutoff: `2024-05-01`, matching Phase32-BJ.

This audit is READ-ONLY. No source, config, model, threshold, Pending, Ledger, runtime state, recover, replay, resume, or fresh-run action was performed. The ongoing Historical validation was not interrupted.

Question audited:

When PM already emits REDUCE but discrete lot prevents partial execution, does existing decision-time PIT evidence contain a principled semantic distinction between deterioration that should progress toward Full EXIT and controlled weakening where HOLD remains justified?

## BJ Population Reproduction

The BJ Policy-A population was reproduced without changing methodology.

| Population | Count |
|---|---:|
| Total PM REDUCE rows | 904 |
| Lot-blocked REDUCE rows | 847 |
| Executable REDUCE rows | 57 |
| First lot-blocked REDUCE campaigns | 343 |
| Full EXIT would have helped | 138 |
| HOLD/current path was better | 62 |
| Neutral | 143 |
| Policy-A avoided loss | 863,980 |
| Policy-A forfeited gain | 518,140 |
| Policy-A net | +345,840 |

Classification terms:

- `HARMFUL`: immediate Full EXIT would have helped by more than `1,000`.
- `BENEFICIAL`: actual HOLD/recovery path was better by more than `1,000`.
- `NEUTRAL`: absolute difference <= `1,000`.

## Existing PM Semantics

All first lot-blocked REDUCE cases shared the same high-level PM sell semantic:

| Field | Harmful | Beneficial | Neutral |
|---|---:|---:|---:|
| `canonical_sell_state = WEAKENING_BUT_INTACT` | 138 | 62 | 143 |
| `continuation_quality_status = PASS` | 138 | 62 | 143 |
| `downside_risk_status = PASS` | 138 | 62 | 143 |
| `profit_protection_status = OBSERVED` | 138 | 62 | 143 |
| `persistence_state = FIRST_OBSERVATION` | 138 | 62 | 143 |
| `exit_confirmation_state = DEFENSIVE_ONLY` | 138 | 62 | 143 |
| `exit_confirmation_reason = soft_deterioration_not_terminal` | 138 | 62 | 143 |
| `hard_deterioration_present = false` | 138 | 62 | 143 |

This is crucial: current PM did not classify these cases as existing EXIT. It classified them as soft deterioration where partial de-risking is appropriate, but PS/lot constraints made partial de-risking unrepresentable.

Therefore the architectural question is not whether PM already wanted EXIT. It did not. The question is whether the materialization layer needs a conditional adapter for:

`PM REDUCE + partial REDUCE impossible`

so that some cases remain HOLD while others progress to Full EXIT-side reconsideration.

## Reason-Family Result

BJ's reason-family split was semantically meaningful, but not deterministic.

| PIT family | Cases | Helped | Beneficial | Neutral | Avoided | Forfeited | Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| `risk_increased_but_trend_not_broken` | 288 | 122 | 32 | 134 | 680,430 | 209,460 | +470,970 |
| `peak_drawdown_warning` | 55 | 16 | 30 | 9 | 183,550 | 308,680 | -125,130 |

Interpretation:

- `risk_increased_but_trend_not_broken` often means the trend has not formally broken, but existing intelligence has already marked weak participation, elevated exhaustion risk, or mixed relative strength. It is frequently a capital-release candidate when partial REDUCE cannot execute.
- `peak_drawdown_warning` is often a winner-protection warning rather than terminal deterioration. These cases more often retain supportive relative strength, manageable exhaustion, or strong medium-term structure.
- Neither family is sufficient as a production rule. Both contain important counterexamples.

## Harmful vs Beneficial PIT Comparison

Decision-time semantic distributions:

| PIT evidence | Harmful | Beneficial | Read |
|---|---:|---:|---|
| `trend_health = SUPPORTIVE` | 109 / 138 | 45 / 62 | Weak separator; both groups often retain supportive trend. |
| `relative_strength = SUPPORTIVE` | 31 / 138 | 36 / 62 | Stronger HOLD-side signal. |
| `exhaustion_risk = ELEVATED_RISK` | 100 / 138 | 18 / 62 | Stronger EXIT-side signal. |
| `exhaustion_risk = MANAGEABLE` | 24 / 138 | 38 / 62 | Stronger HOLD-side signal. |
| `strong_medium_term_structure = true` | 23 / 138 | 25 / 62 | HOLD-side signal, but imperfect. |
| `risk_vote_count >= 3` | 82 / 138 | 15 / 62 | EXIT-side signal. |
| `participation_quality = WEAK` | 92 / 138 | 43 / 62 | Weak separator; common in both groups. |

Numeric PIT descriptors:

| Metric | Harmful avg / median | Beneficial avg / median | Read |
|---|---:|---:|---|
| `action_score` | 0.393 / 0.354 | 0.505 / 0.475 | Lower scores skew harmful; usable as semantic evidence, not a threshold. |
| current return | 1.98% / 0.72% | 4.71% / 2.60% | Beneficial cases carry more profit cushion on average. |
| unrealized PnL | 1,142 / 500 | 3,624 / 1,450 | Beneficial cases carry more cushion, with large overlap. |
| observed MFE | 4.26% / 1.51% | 7.38% / 4.02% | Winner/recovery cases are more established. |
| observed giveback | 2.61% / 0.00% | 3.68% / 0.00% | Not reliable alone. |
| consecutive lot-blocked REDUCE | 1.80 / 2 | 1.58 / 1 | Persistence at first episode is weakly informative only. |
| total lot-blocked REDUCE after first | 2.24 / 2 | 2.37 / 2 | Future persistence is descriptive, not first-date authority. |

Combination checks:

| Existing PIT combination | Cases | Harmful | Beneficial | Neutral | Net |
|---|---:|---:|---:|---:|---:|
| `exhaustion_risk=ELEVATED_RISK` and no strong medium-term structure | 185 | 88 | 15 | 82 | +349,230 |
| `relative_strength=SUPPORTIVE` and `exhaustion_risk=MANAGEABLE` | 61 | 15 | 29 | 17 | -192,160 |
| `strong_medium_term_structure=true` | 71 | 23 | 25 | 23 | -80,330 |
| weak/mixed trend and weak/mixed relative strength | 57 | 24 | 11 | 22 | +142,400 |
| `risk_vote_count >= 3` | 173 | 82 | 15 | 76 | +336,750 |

Separability classification: `PARTIALLY_SEPARABLE`.

The evidence supports semantic directionality, not a fitted rule. There is enough existing PIT structure for a shadow design, but not enough for direct Production activation.

## REDUCE Persistence / Escalation

At the first lot-blocked REDUCE, all cases are `FIRST_OBSERVATION`, so first-date persistence is not available as a primary discriminator.

Post-first descriptive trajectory:

| Group | EXIT within 1BD | EXIT within 5BD | Any later PM EXIT | Avg days to PM EXIT where present |
|---|---:|---:|---:|---:|
| Harmful | 28 / 138 | 43 / 138 | 52 / 138 | 4.21 |
| Beneficial | 6 / 62 | 14 / 62 | 40 / 62 | 12.78 |
| Neutral | 19 / 143 | 28 / 143 | 38 / 143 | 5.76 |

Persistent REDUCE is informative as an escalation concept, but not enough by itself at the first lot-blocked boundary. The more meaningful signal is whether the existing PIT state already resembles the current EXIT path:

- elevated exhaustion / multiple risk votes / weak or mixed continuation,
- little HOLD-side evidence,
- rapid progression toward existing `PERSISTENT_DETERIORATION` or `EXIT_GRADE`.

## Existing EXIT Boundary

Current PM EXIT semantics over the same cutoff:

| EXIT semantic | Count |
|---|---:|
| `EXIT_GRADE` | 353 |
| `PERSISTENT_DETERIORATION` | 215 |
| `PM_SEVERITY_EXIT_CANDIDATE` | 568 |
| `exit_confirmation_state = TERMINAL_BREAKDOWN` | 217 |
| `exit_confirmation_state = CONFIRMED_DETERIORATION` | 215 |
| `exit_confirmation_state = DEFENSIVE_ONLY` | 136 |

Common EXIT reasons:

- `trend_and_opportunity_broken`
- `hard_stop_current_return`
- `profit_retention_break`
- `pm_discrete_control_persistent_deterioration_exit`
- `risk_increased_but_trend_not_broken`

This shows an existing escalation channel already exists. Harmful lot-blocked REDUCE cases were often on a path toward it, but at the first blocked REDUCE they were still semantically `WEAKENING_BUT_INTACT`.

Answer to the critical question:

Yes, the missing design is best characterized as an intermediate adapter between existing REDUCE and existing EXIT semantics when partial REDUCE cannot be represented. It should not bypass existing EXIT semantics; it should ask whether the lot-blocked REDUCE state is closer to HOLD-side controlled weakening or EXIT-side deterioration.

## Mandatory Case Studies

### Harmful Cases

| Symbol | First blocked REDUCE | Full EXIT effect | Decision-time state | Why PM chose REDUCE | Separability read |
|---|---:|---:|---|---|---|
| 67310 | 2023-04-24 | +100,000 | weak trend, weak persistence, weak relative strength, mixed exhaustion, action_score 0.305, return +50.0% | Soft deterioration, trend not formally broken, hard deterioration false; PM chose light REDUCE. | Strong harmful signal despite large profit cushion; later repeated blocked REDUCE confirms it, but first-date evidence already had weak continuation. |
| 62310 | 2023-05-01 | +35,600 | supportive trend, mixed persistence/relative strength, manageable exhaustion, action_score 0.371, return +1.4% | Weakening but intact; no hard/terminal evidence. | Mixed; low score and weak participation support caution, but HOLD-side evidence remains. |
| 74770 | 2023-10-04 | +29,900 | supportive trend/relative strength, elevated exhaustion, decelerating, risk_vote_count 4, return -6.5% | Defensive REDUCE, not EXIT, because trend/relative strength still supportive. | More separable via loss state + elevated exhaustion + rapid next-day EXIT. |
| 34160 | 2024-03-05 | +25,300 | supportive trend/persistence/relative strength, manageable exhaustion, strong medium-term structure, action_score 0.690, return +7.7% | Strong peak-drawdown warning, but soft not terminal. | Weakly separable; looks like a beneficial-control profile but later harmed. |
| 36670 | 2023-06-16 | +25,000 | mixed trend/persistence/relative strength, elevated exhaustion, risk_vote_count 3, return -3.1% | Light REDUCE because deterioration was present but not hard. | Fairly separable toward EXIT-side reconsideration. |
| 51890 | 2023-04-14 | +24,250 | supportive trend, mixed persistence/relative strength, elevated exhaustion, giveback 18.4%, return -7.9% | Strong peak-drawdown warning, but confirmation remained defensive. | Fairly separable via loss state, elevated exhaustion, and next-day EXIT. |

### Beneficial Controls

| Symbol | First blocked REDUCE | Full EXIT forfeiture | Decision-time state | Why PM chose REDUCE | Protection read |
|---|---:|---:|---|---|---|
| 62280 | 2023-12-22 | -54,660 | supportive trend/persistence/relative strength, manageable exhaustion, strong medium-term structure, action_score 0.755, return +9.5% | Strong peak-drawdown warning but not terminal. | Protectable: multiple HOLD-side signals survived. |
| 74270 | 2023-08-14 | -41,100 | weak trend, mixed persistence/relative strength, mixed exhaustion, action_score 0.293, return +2.6% | Light REDUCE from weak hold score. | Hard to protect from first-date evidence; this is a major counterexample. |
| 92270 | 2022-10-24 | -30,000 | supportive trend/relative strength, elevated exhaustion, risk_vote_count 3, return -3.3% | Medium REDUCE; soft deterioration only. | Hard to protect if using exhaustion/risk votes alone; supportive relative strength helps. |
| 72140 | 2023-05-25 | -24,000 | mixed trend, supportive relative strength, manageable exhaustion, return +12.0% | Strong peak-drawdown warning, but still weakening-but-intact. | Protectable via profit cushion + manageable exhaustion + supportive relative strength. |
| 83040 | 2024-02-21 | -23,050 | weak trend, mixed relative strength, mixed exhaustion, supportive participation, return +3.0% | Medium peak-drawdown warning; no hard deterioration. | Partially protectable; not clean. |
| 69730 | 2022-11-04 | -19,900 | supportive trend/persistence/relative strength, manageable exhaustion, strong medium-term structure, return +5.7% | Strong peak-drawdown warning but HOLD-side evidence was intact. | Protectable. |

## Action Score

BJ observed:

- `action_score < 0.4`: net `+419,890`
- `action_score >= 0.4`: net `-74,050`

BK interpretation:

- The split is semantically meaningful because lower scores coincide with weaker continuation/relative evidence and elevated risk clusters.
- It is not a production threshold. The score is a model-derived selected-action score and not calibrated as a probability.
- It is usable in a future shadow contract as one evidence dimension, especially when paired with reason family and HOLD-side evidence.
- `0.4` must remain a descriptive split from BJ/BK, not a parameter selection.

Classification: `SEMANTICALLY_USABLE_FOR_SHADOW`, `NOT_A_PRODUCTION_THRESHOLD`.

## False-Exit Protection

Major false exits are partially protectable with existing PIT evidence:

- Strongest protection pattern: supportive relative strength + manageable exhaustion + strong medium-term structure + meaningful profit cushion.
- This protects `62280`, `72140`, and `69730` reasonably well.
- It partially protects `83040`.
- It does not cleanly protect `74270` or `92270`, which are the hard counterexamples.

Therefore:

- Existing PIT evidence can reduce false-exit risk.
- Existing PIT evidence cannot eliminate false-exit risk without also preserving some harmful cases.
- A production rule needs shadow validation of both avoided loss and forfeited winner gain.

## Candidate Binary Materialization Semantics

Existing semantics support a conceptual, non-fitted shadow decision:

`PM REDUCE + DISCRETE_LOT blocked`

can be interpreted as:

- HOLD-side controlled weakening when continuation/relative strength remains supportive, exhaustion is manageable/mixed, profit cushion is meaningful, hard deterioration is absent, and exit confirmation remains defensive.
- EXIT-side reconsideration when exhaustion is elevated, risk votes accumulate, relative/continuation evidence is weak or mixed, profit cushion is small or already eroding, and later PM trajectory resembles existing `PERSISTENT_DETERIORATION` / `EXIT_GRADE` semantics.

This should be framed as materialization of existing Strategy intelligence at an execution granularity boundary, not a new Strategy signal.

## Required Final Answers

1. `BJ_POLICY_A_POPULATION_REPRODUCED`: YES. `343` first lot-blocked REDUCE campaigns; `138` helped, `62` beneficial, `143` neutral; net `+345,840`.
2. `HARMFUL_VS_BENEFICIAL_SEPARABILITY`: `PARTIALLY_SEPARABLE`.
3. `REASON_FAMILY_SEMANTICALLY_MEANINGFUL`: YES, but not deterministic.
4. `RISK_INCREASED_TREND_NOT_BROKEN_INTERPRETATION`: often an EXIT-side materialization candidate when partial REDUCE is impossible, especially with elevated exhaustion / weak relative evidence / low action score.
5. `PEAK_DRAWDOWN_WARNING_INTERPRETATION`: often winner-protection / temporary drawdown, with stronger HOLD-side evidence, but it also contains harmful cases.
6. `REDUCE_PERSISTENCE_MATERIALLY_INFORMATIVE`: YES for escalation design, but first-date persistence is not available because first blocked REDUCE is `FIRST_OBSERVATION`.
7. `EXPECTED_EDGE_SEPARABILITY`: `WEAK_TO_PARTIAL`; explicit expected-edge calibration is unavailable/uncalibrated, but continuation/relative/exhaustion proxies carry signal.
8. `TREND_CONTINUATION_SEPARABILITY`: `WEAK`; trend_health is supportive in both groups.
9. `DOWNSIDE_RISK_SEPARABILITY`: `PARTIAL`; top-level downside status is PASS in both groups, but exhaustion/risk-vote dimensions separate materially.
10. `PROFIT_RETENTION_SEPARABILITY`: `PARTIAL`; profit cushion and MFE are higher in beneficial cases, but giveback alone is not reliable.
11. `ACTION_SCORE_SEMANTICALLY_USABLE`: YES, for shadow evidence only.
12. `ACTION_SCORE_0_4_IS_PRODUCTION_THRESHOLD`: NO.
13. `HARMFUL_CASES_ALREADY_APPROACH_EXISTING_EXIT_SEMANTICS`: PARTIAL. Many move to EXIT quickly or share deterioration dimensions, but first blocked REDUCE remains `DEFENSIVE_ONLY`.
14. `BENEFICIAL_CASES_RETAIN_HOLD_SIDE_EVIDENCE`: YES, especially supportive relative strength, manageable exhaustion, strong medium-term structure, and profit cushion.
15. `MAJOR_FALSE_EXITS_PROTECTABLE_WITH_EXISTING_PIT_EVIDENCE`: PARTIAL. `62280`, `72140`, and `69730` are protectable; `74270` and `92270` remain difficult.
16. `IS_NEW_FEATURE_REQUIRED`: NO for initial shadow design; existing PIT evidence is enough to test semantics. Additional features may be useful later.
17. `IS_NEW_MODEL_REQUIRED`: NO for initial shadow design.
18. `IS_EXISTING_PIT_EVIDENCE_SUFFICIENT_FOR_SHADOW_DESIGN`: YES.
19. `IS_LOT_BLOCKED_BINARY_MATERIALIZATION_ARCHITECTURALLY_JUSTIFIED`: YES.
20. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
21. `NEXT_RECOMMENDED_STEP`: create a READ-ONLY shadow contract for lot-blocked REDUCE binary materialization using existing PIT evidence, with explicit false-exit accounting and no fitted threshold adoption.
22. `FINAL_JUDGMENT`: `PHASE32_BK_LOT_BLOCKED_REDUCE_PIT_SEMANTIC_SEPARABILITY_PARTIALLY_SUPPORTED_SHADOW_BINARY_MATERIALIZATION_JUSTIFIED_PRODUCTION_CHANGE_NOT_YET_ACCEPTED`

## NO CHANGE Confirmation

- NO code change, except this phase report artifact.
- NO config / model / parameter / threshold / weight change.
- NO implementation of shadow or Production logic.
- NO recover / replay / resume / fresh-run.
- NO runtime / Pending / Ledger mutation.
- NO future information used as decision-time input.
- Historical outcomes used only as post-decision characterization labels.

