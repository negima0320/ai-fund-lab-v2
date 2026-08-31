# Phase32-AQ — Graduation Episode Lifecycle / Freshness Boundary Final Falsification Audit

## Scope

Task type: READ-ONLY / SHADOW ONLY falsification audit.

Target trusted run:

`runtime-test-historical-extended-smoke-20260830T081425790243Z`

Audited window:

`2022-10-03` through `2023-10-10`, `252BD`.

Source identity:

`git rev-parse --short HEAD = ff1d231`

No source code, config, runtime state, BUY_NEW sizing, ADD/HOLD, SELL, PC, Cash, Risk Pacing, thresholds, weights, Production feature, new component, Model 2 activation, Graduation implementation, fresh-run, resume, replay, recover, rollback, or long Historical command was executed. No parameter recommendation is made.

## Objective Answer

Question:

```text
Can existing decision-time PIT evidence, without arbitrary new thresholds or hindsight,
represent an explicit Graduation Episode lifecycle that separates persistent strength
from materially renewed incremental opportunity?
```

Answer:

```text
NO_FOR_CANONICAL_PRODUCTION_EPISODE
PARTIAL_FOR_READ_ONLY_SHADOW_DIAGNOSTICS
```

Existing artifacts can reconstruct state strength and some state changes. They cannot canonically prove an episode lifecycle with deterministic open / refresh / close / reopen semantics without inventing new materiality rules. The evidence also shows that existing successful graduation does not require a fresh-event semantic; it is better represented as persistent eligibility plus PC/PS/G129 order-increment authorization.

## A — Deferred Architecture Tracks Preserved

### Model 2

```text
Model 2 — PM Position Lifecycle + PC ADD Consideration
Status: DEFERRED / ON HOLD
Rejected: NO
Production activation: NOT AUTHORIZED
Shadow: PARTIALLY_VALIDATED
```

AQ relevance:

`OPTIONAL_SEMANTIC_CLEANUP / MATERIAL_SUPPORT`, not a core requirement for graduation and not sufficient to solve episode lifecycle or capital comparison.

### Starter-to-Winner Graduation

```text
Status: OPEN / SHADOW_ONLY
Rejected: NO
Production activation: NOT AUTHORIZED
Current contract: PARTIAL
```

Suggested durable SoT location:

`docs/02_architecture/strategy_intelligence_architecture_v1.md`

Reason: this file already records HOLD-vs-ADD semantics, PM/SI/PC/PS boundaries, G129 BUY_ADD authority, Cash preservation, and the high-resolution marginal capital roadmap pointer.

## B — Episode Semantics Inventory

These are audit concepts only. They are not Production rules.

| Concept | Existing PIT evidence | Producer / owner | Consumer | Reconstruction |
|---|---|---|---|---|
| `STARTER` | BUY_NEW fill, campaign open, initial quantity | Runtime / Ledger / campaign authority | PM, SI, PC | `PARTIAL`: no canonical STARTER state field |
| `CONFIRMED_HOLD` | PM HOLD, SI hold-worthiness PASS, continuation quality, downside risk | PM / SI | PC / PS | `DETERMINISTIC_FOR_STATE`, not explicit transition |
| `GRADUATION_CONSIDERATION` | PM ADD plus PC-visible ADD eligibility / ADD investment evidence | PM / SI / PC | PC | `PARTIAL`: conservative AP surface works |
| `PERSISTENT_STRENGTH` | repeated HOLD/ADD, continuation PASS, downside PASS, unchanged sell state | PM / SI | diagnostic only | `PARTIAL`: observable, not canonical episode state |
| `EVIDENCE_REFRESH` | changes in PM action, BQ, SI entry state, expected-edge state, recovery, risk, PC eligibility | multiple | diagnostic only | `OBSERVABLE_ONLY / PARTIAL` |
| `RENEWED_GRADUATION_CONSIDERATION` | post-closure PC ADD eligibility returns | PC plus PM/SI | PC | `PARTIAL`: no canonical materiality boundary |
| `DEPLOYMENT_BLOCKED` | ADD evidence present but Cash/NEW/BQ/target/lot/risk blocks allocation | PC / PS | Runtime planning | `DETERMINISTIC_FOR_REASON`, not episode state |
| `GRADUATED_POSITION` | BUY_ADD fill on same campaign | Runtime / Ledger / campaigns | reports / PM | `DETERMINISTIC_OBSERVED` |
| `EPISODE_CLOSED` | HOLD transition, deployment rejection, REDUCE, EXIT, prior ADD gate, BQ block | multiple | diagnostic only | `PARTIAL`: several closures exist, no single canonical lifecycle |

## C — Evidence Change Inventory

| Transition source | Current semantic meaning | Classification |
|---|---|---|
| PM action transition | action authority / lifecycle intent | `CANONICAL_TRANSITION` |
| PM sell state / severity transition | PM sell-side state and deterioration/recovery context | `CANONICAL_TRANSITION` |
| SI hold-worthiness / ADD-worthiness status | HOLD vs ADD evidence, not action authority | `CANONICAL_TRANSITION` for state, `PARTIAL` for episode |
| BQ action/band transition | allocation quality / BUY_WAIT / reduction evidence | `CANONICAL_TRANSITION` for allocation |
| PC ADD eligibility transition | PC-visible ADD consideration / block state | `CANONICAL_TRANSITION` for PC allocation |
| expected-edge state change | existing ADD evidence state: IMPROVING / WEAKENING / UNKNOWN | `CANONICAL_TRANSITION` inside ADD evidence |
| incremental value transition | POSITIVE / UNKNOWN / BQ-blocked | `CANONICAL_TRANSITION` inside ADD evidence |
| opportunity-cost transition | PASS / NEW_BUY_SUPERIOR | `CANONICAL_TRANSITION` inside PC evidence |
| continuation/downside status | SI/PM health evidence | `CANONICAL_TRANSITION` for state |
| recovery from deterioration | PM severity / Phase32-X recovery semantics | `CANONICAL_TRANSITION` for sell/retention |
| opportunity-rank change | observable rank/score movement | `OBSERVABLE_ONLY` unless consumed by existing PM/PC field |
| runtime opportunity score change | uncalibrated relative model score | `OBSERVABLE_ONLY` for episode materiality |
| raw momentum / acceleration change | SI feature evidence | `EXISTING_BUT_NONCANONICAL` for episode materiality |
| exposure/headroom change | PC/PS cap and feasibility evidence | `CANONICAL_TRANSITION` for allocation, not freshness |
| elapsed time / age alone | campaign context | `OBSERVABLE_ONLY`; no arbitrary cooldown permitted |

Conclusion: many transitions are canonical for their local authority, but none is a complete canonical `fresh graduation episode` boundary.

## D — State Vs Episode Answers

1. `CAN_STATE_STRENGTH_BE_RECONSTRUCTED`

   `YES`. PM/SI/PC artifacts expose HOLD/ADD state, continuation, downside, BQ, expected edge, opportunity cost, and current campaign context.

2. `CAN_STATE_CHANGE_BE_RECONSTRUCTED`

   `PARTIAL`. Field changes can be reconstructed day by day, but materiality across heterogeneous signals is not canonically defined.

3. `CAN_RENEWED_STRENGTH_AFTER_WEAKENING_BE_RECONSTRUCTED`

   `PARTIAL`. Phase32-X recovery semantics can identify recovery from deterioration for retention, but not automatically renewed incremental ADD entitlement.

4. `CAN_A_CANONICAL_EPISODE_BOUNDARY_BE_RECONSTRUCTED`

   `NO`. Existing evidence lacks a single accepted open/refresh/close/reopen contract for graduation episodes.

## E — Temporal Reconstruction Summary

Method:

- Used only artifacts with business date at or before the evaluated date.
- Compared consecutive observed campaign-days using existing categorical fields:
  PM action, PM sell state, persistence/recovery, SI hold/ADD status, PC ADD eligibility, expected-edge state, incremental value, opportunity cost, BQ action/band, SI entry state, Risk Pacing intent, and PC weight reason.
- No future returns, final outcomes, MFE/MAE after the decision, or Historical PnL were used to set labels.

Critical observation:

The target run has many categorical evidence changes, including in weak/non-growing campaigns. Among the 387 negative controls, `302` campaigns have some observable evidence refresh if "refresh" means any categorical field change. Therefore "any change" is far too broad and cannot be a safe episode rule.

## F — 94340 Positive Episode Control

Main campaign:

`pc-f3bd989f40c52bdf-94340-0001`

Observed path:

| Date | State |
|---|---|
| 2022-10-03 | BUY_NEW 200 |
| 2022-10-04 | HOLD / confirmed state |
| 2022-10-05 | PM ADD, but PC ADD eligibility fail-closed / target unchanged |
| 2022-10-06 | PC ADD eligibility PASS; expected edge IMPROVING; incremental value POSITIVE; BUY_ADD fill 100 |
| 2022-10-07 | PM ADD persists but PC ADD eligibility fail-closed |
| 2022-10-11 | PC ADD eligibility PASS again |
| 2022-10-12 | PC ADD eligibility PASS again; BUY_ADD fill 100 |
| 2022-10-13 | PC ADD eligibility PASS again; BUY_ADD fill 100 |
| 2022-10-14 | PM HOLD; PC ADD consideration ends |
| 2022-12-07 | EXIT |

Interpretation:

94340 can be represented as either one graduation episode with repeated deployment, or persistent strength with repeated valid lot deployment. It does not require proving multiple fresh independent episodes.

`WHAT_DOES_94340_REVEAL_ABOUT_FRESHNESS_REQUIREMENTS`

```text
Successful existing graduation does not require a fresh-event semantic.
Persistent eligibility plus PC/PS/G129 per-order authority is sufficient to explain the actual path.
```

This falsifies a mandatory "freshness required for each ADD" assumption.

## G — 76470 Gate-Blocked Control

Main campaign:

`pc-8b52b4c89fd002ad-76470-0001`

Observed path:

| Date | State |
|---|---|
| 2022-11-25 | BUY_NEW 1300 |
| 2022-11-28 | PM ADD, PC ADD fail-closed / target unchanged |
| 2022-11-29 | PC ADD eligibility PASS, BUY_ADD fill 100 |
| 2022-11-30 | PC ADD eligibility PASS, BUY_ADD fill 100 |
| 2022-12-01 | PC ADD eligibility PASS, BUY_ADD fill 100 |
| 2022-12-02 | PC ADD eligibility PASS, BUY_ADD fill 100 |
| 2022-12-05 | PM HOLD; consideration closed observationally |
| 2022-12-06 | PC ADD eligibility PASS, BUY_ADD fill 100 |
| 2022-12-07 onward | ADD status becomes `NO_ADD` / HOLD; later strong state persists |
| 2023-01-24 | EXIT |

`DID_76470_SHOW_A_CANONICAL_NEW_EPISODE_AFTER_THE_PRIOR_ADD_GATE`

```text
NO.
```

After the prior ADD gate / `NO_ADD` state, later evidence is best classified as persistent strength or HOLD-worthy state, not a canonical new graduation episode. There is no PIT-safe accepted field that proves a new post-gate episode without adding interpretation.

## H — Four Main Challenge Winners

| Symbol | Campaign | Refresh classification | AQ finding |
|---|---|---|---|
| `54010` | `pc-3aaff341fad7ae34-54010-0001` | `PERSISTENT_STRENGTH` with `PLAUSIBLE_NONCANONICAL_RENEWAL` | Many BQ/entry-state changes and PM ADD bursts, but PC ADD eligibility remains fail-closed / target unchanged or NEW superior. Surfacing as renewed graduation would require relaxing AP. |
| `43880` | `pc-df47de7d57274254-43880-0001` | `PERSISTENT_STRENGTH` with weak/noncanonical refresh | Repeated PM ADD and some expected-edge IMPROVING, but incremental value stays UNKNOWN or BQ-blocked and PC eligibility fail-closed; later REDUCE/EXIT. |
| `40520` | `pc-21eead760e37aeb3-40520-0001` | `PLAUSIBLE_NONCANONICAL_RENEWAL` / `PERSISTENT_STRENGTH` | PM ADD appears with opportunity-cost PASS on one day and later IMPROVING states, but PC eligibility remains fail-closed; no canonical renewed episode. |
| `77760` | `pc-9d71e709a18ea961-77760-0001` | `PERSISTENT_STRENGTH` / `INSUFFICIENT_FOR_RENEWAL` | Confirmed HOLD exists; no conservative PC ADD consideration. Any surfacing would require new semantics. |

`CAN_THESE_CHALLENGE_CASES_BE_SURFACED_WITHOUT_RELAXING_AP_USING_ARBITRARY_INTERPRETATION`

```text
NO.
```

The challenge cases contain plausible refresh-like evidence, but not a canonical, low-false-positive, Production-safe episode boundary.

## I — 21340 Allocation-Rejection Control

Main campaign:

`pc-f3186b6520780cea-21340-0001`

Observed path:

| Date | State |
|---|---|
| 2023-06-05 | BUY_NEW 2200 |
| 2023-06-06 | PM ADD / strong state, PC ADD fail-closed |
| 2023-06-20 | PC ADD eligibility PASS, expected edge IMPROVING, incremental value POSITIVE, opportunity cost PASS |
| 2023-06-21 | PC ADD eligibility fail-closed, NEW superior |
| 2023-07-07 | EXIT |

`DOES_21340_HAVE_AN_EPISODE_PROBLEM_OR_CAPITAL_ALLOCATION_PROBLEM`

```text
CAPITAL_ALLOCATION_PROBLEM / LOT_OR_FINAL_DEPLOYMENT_PROBLEM, not episode recognition.
```

21340 already reaches conservative graduation consideration. A richer episode label would mostly improve observability; the bottleneck remains PC/NEW/Cash/lot/final deployment.

## J — Negative Controls Re-test

AP negative-control set:

```text
392 non-growing campaigns
- 5 durable no-growth challenge campaigns
= 387 negative controls
```

AQ retest:

| Metric | Count |
|---|---:|
| Negative controls | `387` |
| Campaigns with any observable categorical evidence refresh | `302` |
| Campaigns with renewed conservative graduation consideration | `2` |
| False surfaced campaigns | `2` |
| False surface rate | `2 / 387 = 0.5168%` |

False surfaced campaigns:

| Symbol | Campaign | Note |
|---|---|---|
| `67310` | `pc-47f89bc0fb3b790c-67310-0001` | Recovery-like transitions into ADD/PC evidence on 2023-05-10 and 2023-05-29, but no growth |
| `99840` | `pc-925de11083435873-99840-0001` | repeated ADD/PC evidence oscillations in November 2022, but no growth |

Comparison with AP:

The conservative AP false surface remains unchanged at `2 / 387`. However, if AQ treated any BQ/SI/rank/PM-state change as `EVIDENCE_REFRESH`, the false surface would explode. This is the strongest falsification evidence against a broad freshness rule.

## K — Persistent Strength Churn Test

Long or recurring strong-state / ADD-like campaigns inspected:

- `99840`
- `67310`
- `94320`
- `76470`
- `94340`
- `54010`
- `43880`
- `40520`

Findings:

- `99840` repeatedly toggles BQ, expected-edge, incremental-value, and PC eligibility states while never growing.
- `94320` has repeated PC ADD surfaces, some zero/blocked, one actual BUY_ADD, then recurring non-final ADD-like states.
- `76470` has a successful repeated ADD sequence followed by HOLD/NO_ADD and later strong state, but no canonical new post-gate episode.
- `54010`, `43880`, and `40520` show PM ADD and evidence oscillation without PC-positive graduation under the conservative AP contract.

`CAN_PERSISTENT_STRENGTH_BE_PREVENTED_FROM_REOPENING_EPISODES`

```text
NO_FOR_PRODUCTION_WITH_EXISTING_SEMANTICS.
```

It can be prevented only by adding an extra episode lifecycle rule, cooldown, materiality threshold, or freshness interpretation. Those are explicitly outside AQ.

Required property:

```text
PERSISTENT_STRENGTH != NEW_EPISODE
```

This property is not guaranteed by existing artifacts alone.

## L — Episode Closure

Closure candidates:

| Closure event | Existing support | AQ classification |
|---|---|---|
| successful BUY_ADD | actual observed deployment | `PARTIAL`: closes order increment, not necessarily episode |
| deployment rejection / PC fail-closed | PC reason evidence | `PARTIAL`: blocks deployment, not formal episode close |
| PM HOLD transition | PM action state | `PARTIAL`: plausible close, but not canonical episode close |
| deterioration / REDUCE | PM sell-side state | `CANONICAL` for sell/retention, `PARTIAL` for episode |
| EXIT | campaign close | `CANONICAL` for campaign, sufficient to close any episode |
| prior ADD gate / `NO_ADD` | SI/PC gate | `PARTIAL`: blocks ADD, not formal episode close |
| time alone | no accepted threshold | `UNAVAILABLE` |

`CAN_EPISODE_CLOSE_BE_DEFINED_WITH_EXISTING_SEMANTICS`

```text
PARTIAL.
```

EXIT can close a campaign-level episode. Other closures require interpretive mapping.

## M — Episode Reopening

Possible reopening evidence:

| Reopening event | Existing support | AQ classification |
|---|---|---|
| recovery from deterioration | Phase32-X / PM recovery semantics | `PARTIAL`: retention recovery, not ADD episode |
| BQ restoration | BQ action change | `OBSERVABLE_ONLY` for episode |
| SI restoration | SI entry/continuation label change | `OBSERVABLE_ONLY / PARTIAL` |
| renewed continuation | continuation stays PASS often; not enough | `PARTIAL` |
| rank recovery | uncalibrated rank movement | `OBSERVABLE_ONLY` |
| expected-edge support returns to IMPROVING | ADD evidence state | `PARTIAL`, but not sufficient alone |
| PC ADD eligibility returns to PASS | PC allocation evidence | `PARTIAL`, consideration only |
| elapsed time alone | no accepted semantics | `UNAVAILABLE` |

`CAN_EPISODE_REOPEN_BE_DEFINED_WITH_EXISTING_SEMANTICS`

```text
NO_FOR_CANONICAL_PRODUCTION / PARTIAL_FOR_SHADOW.
```

Reopening cannot be safely defined without adding materiality semantics.

## N — Does Graduation Need Freshness?

Compared concepts:

### Concept 1 — Freshness Required

A Winner may enter graduation consideration only after a new/renewed evidence event.

### Concept 2 — Persistent Eligibility

A Winner may remain eligible for PC incremental-capital competition while strength remains valid; PC/ADD evidence/lot/risk/Cash determine whether another lot is justified.

Finding:

```text
Concept 2 better matches current Architecture and actual evidence.
```

Reasons:

- 94340 succeeds without needing a distinct fresh event before every BUY_ADD.
- 76470's repeated adds are coherent as persistent eligibility plus per-order PC/PS/G129 authorization.
- G129 already prevents Runtime from turning state strength into arbitrary cumulative BUY_ADD quantity; each submitted BUY_ADD must match PC-positive executable order increment.
- No-loss averaging, prior ADD safeguards, Cash, Risk Pacing, and PC gates are better guards than a fabricated freshness threshold.
- Current Architecture emphasizes ADD-worthiness, opportunity cost, lot feasibility, and PC authority, not explicit freshness episodes.

`DOES_GRADUATION_ACTUALLY_REQUIRE_FRESHNESS`

```text
NO, not as a mandatory current-system specification.
```

Freshness may be useful as future research, but it is not required to accept current behavior.

## O — Model 2 Re-evaluation

`WHAT_IS_MODEL2_STATUS_AND_RELEVANCE`

```text
Status: DEFERRED / ON HOLD
Rejected: NO
Production activation: NOT AUTHORIZED
Shadow: PARTIALLY_VALIDATED
Relevance: OPTIONAL_SEMANTIC_CLEANUP / MATERIAL_SUPPORT
```

Model 2 solves:

| Area | Does Model 2 solve it? |
|---|---|
| lifecycle semantics | `PARTIAL / YES_FOR_CLARITY` |
| consideration routing | `YES_FOR_SHADOW_CLARITY` |
| episode lifecycle | `NO` |
| capital comparison | `NO` |

Model 2 should not be activated as a substitute for a missing episode contract or high-resolution NEW/ADD/Cash comparator.

## P — Capital Competition Residual

`WOULD_SOLVING_EPISODE_RECOGNITION_BE_SUFFICIENT_TO_FIX_WINNER_GRADUATION`

```text
NO.
```

Even with perfect episode recognition, unresolved bottlenecks remain:

- NEW/ADD/Cash marginal comparability is incomplete.
- Cash optionality is active and intentional.
- Risk Pacing can down-tier deployment.
- initial starter sizing creates many small positions.
- starter saturation / position count remains material.
- lot feasibility and G129 order-increment constraints remain binding.
- PC ADD evidence can fail closed.
- prior ADD gate must remain intact.

Therefore episode recognition alone cannot fix winner graduation.

## Q — Current Specification Acceptance Test

Acceptance criteria:

| Criterion | Result |
|---|---|
| no unresolved correctness defect | `PASS` |
| weak-starter protection remains strong | `PASS` |
| Cash/Risk/Safety behavior remains intentional | `PASS` |
| system can graduate positions under valid conditions | `PASS`, e.g. `94340`, `76470` |
| remaining weakness is performance architecture, not correctness | `PASS` |
| further improvement requires new assumptions/features/thresholds/redesign | `PASS` |

Classification:

```text
CURRENT_SPEC_ACCEPTABLE_WITH_DEFERRED_RESEARCH
```

The current system specification is acceptable as a baseline, provided the limitation is durably documented.

## R — Stop / Continue Research Gate

Selected gate:

```text
ACCEPT_CURRENT_SPEC_AND_DEFER
```

Reason:

- A deterministic, PIT-safe, low-false-positive episode/graduation contract is not supported.
- There is no single remaining question that is likely answerable from current evidence without adding assumptions.
- No correctness repair is found.
- Production activation is not justified.

## S — Durable SoT / Handoff Requirements

If current spec is accepted, durably record:

- Current graduation behavior is accepted as baseline:

  ```text
  persistent eligibility + PC/PS/G129 per-order authority,
  not mandatory fresh graduation episodes
  ```

- Known limitation:

  ```text
  REPLACE_HEAVY_HYBRID / weak winner graduation / starter saturation
  ```

- Model 2:

  ```text
  DEFERRED / ON HOLD; rejected NO; activation NOT AUTHORIZED
  ```

- Graduation contract:

  ```text
  OPEN / SHADOW_ONLY; current contract PARTIAL; activation NOT AUTHORIZED
  ```

- NEW/ADD/Cash marginal-value comparison:

  ```text
  DEFERRED; high-resolution comparator remains future research
  ```

- No correctness defect found.
- Future revisit conditions:

  - accepted SoT update authorizes new semantic assumptions;
  - a high-resolution marginal-capital comparator is designed;
  - a non-arbitrary episode materiality contract is defined;
  - weak-starter protection can be proven against the 387 negative controls;
  - G129, Cash, Risk Pacing, SELL independence, and no-loss averaging remain preserved.

## Required Final Answers

1. `CAN_STATE_STRENGTH_BE_RECONSTRUCTED`

   `YES`.

2. `CAN_STATE_CHANGE_BE_RECONSTRUCTED`

   `PARTIAL`.

3. `CAN_RENEWED_STRENGTH_AFTER_WEAKENING_BE_RECONSTRUCTED`

   `PARTIAL`.

4. `CAN_A_CANONICAL_EPISODE_BOUNDARY_BE_RECONSTRUCTED`

   `NO`.

5. `WHAT_DOES_94340_REVEAL_ABOUT_FRESHNESS_REQUIREMENTS`

   94340 shows successful graduation does not require a fresh-event semantic before each BUY_ADD. Persistent eligibility plus PC/PS/G129 order-increment authority explains the path.

6. `DID_76470_SHOW_A_CANONICAL_NEW_EPISODE_AFTER_THE_PRIOR_ADD_GATE`

   `NO`.

7. `HOW_DO_54010_43880_40520_77760_CLASSIFY`

   `54010`: `PERSISTENT_STRENGTH` with plausible noncanonical renewal; `43880`: `PERSISTENT_STRENGTH` / fail-closed ADD evidence; `40520`: `PLAUSIBLE_NONCANONICAL_RENEWAL` but no canonical PC-positive graduation; `77760`: `PERSISTENT_STRENGTH / INSUFFICIENT_FOR_RENEWAL`.

8. `DOES_21340_HAVE_AN_EPISODE_PROBLEM_OR_CAPITAL_ALLOCATION_PROBLEM`

   `CAPITAL_ALLOCATION_PROBLEM`.

9. `WHAT_IS_THE_NEGATIVE_CONTROL_FALSE_SURFACE`

   Conservative AP surface remains `2 / 387 = 0.5168%`; broad observable refresh exists in `302 / 387` and is unsafe as an episode rule.

10. `CAN_PERSISTENT_STRENGTH_BE_PREVENTED_FROM_REOPENING_EPISODES`

    `NO_FOR_PRODUCTION_WITH_EXISTING_SEMANTICS`.

11. `CAN_EPISODE_CLOSE_BE_DEFINED_WITH_EXISTING_SEMANTICS`

    `PARTIAL`.

12. `CAN_EPISODE_REOPEN_BE_DEFINED_WITH_EXISTING_SEMANTICS`

    `NO_FOR_CANONICAL_PRODUCTION / PARTIAL_FOR_SHADOW`.

13. `DOES_GRADUATION_ACTUALLY_REQUIRE_FRESHNESS`

    `NO`.

14. `WHAT_IS_MODEL2_STATUS_AND_RELEVANCE`

    `DEFERRED / ON HOLD`; `OPTIONAL_SEMANTIC_CLEANUP / MATERIAL_SUPPORT`; not sufficient for episode lifecycle or capital comparison.

15. `WOULD_SOLVING_EPISODE_RECOGNITION_BE_SUFFICIENT`

    `NO`.

16. `IS_THE_REMAINING_PROBLEM_CORRECTNESS_OR_PERFORMANCE_ARCHITECTURE`

    `PERFORMANCE_ARCHITECTURE`.

17. `IS_CURRENT_SYSTEM_SPEC_ACCEPTABLE`

    `CURRENT_SPEC_ACCEPTABLE_WITH_DEFERRED_RESEARCH`.

18. `SHOULD_RESEARCH_CONTINUE_OR_BE_DEFERRED`

    `ACCEPT_CURRENT_SPEC_AND_DEFER`.

19. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED`

    `NO`.

20. `WHAT_MUST_BE_DURABLY_RECORDED_IF_THE_CURRENT_SPEC_IS_ACCEPTED`

    Current baseline accepts persistent eligibility plus PC/PS/G129 authority; REPLACE_HEAVY_HYBRID / weak graduation is a known performance limitation; Model 2, Graduation contract, and NEW/ADD/Cash marginal comparator remain deferred/open; no correctness defect is found; future revisit needs explicit SoT authorization and low-false-positive proof.

## Final Judgment

```text
CURRENT_SPEC_ACCEPTED_WITH_DEFERRED_IMPROVEMENT_RESEARCH
```

Detailed judgment:

```text
PHASE32_AQ_GRADUATION_EPISODE_FRESHNESS_BOUNDARY_FALSIFIED_CURRENT_SPEC_ACCEPTED_WITH_DEFERRED_RESEARCH
```

Current strengths to preserve:

- weak-starter protection
- no loss averaging
- Cash optionality
- Risk Pacing
- Safety / broker / corporate-action gates
- SELL independence
- PC final allocation authority
- PS discrete quantity authority
- G129 BUY_ADD order-increment authority
- fail-closed behavior

Semantic feasibility:

`PARTIAL_FOR_SHADOW`, `NO_FOR_PRODUCTION_EPISODE`.

Capital-allocation feasibility:

Still incomplete; solving episode recognition would not solve NEW/ADD/Cash marginal comparability, Cash optionality, starter saturation, lot feasibility, or prior ADD gate constraints.

Unresolved ambiguity:

Existing PIT evidence can observe many changes, but cannot distinguish persistent strength from materially renewed incremental opportunity without new materiality semantics.

Deferred architecture tracks:

Model 2 and Starter-to-Winner Graduation remain explicitly open, deferred, not rejected, and not authorized for Production activation.
