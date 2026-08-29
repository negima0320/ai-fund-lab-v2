# Phase32-F - Avoidable Loss / Early Failure / Capital-at-Risk Characterization

## Executive Summary

Phase32-F audited the loss side of the Phase32 plateau without changing
production code, configuration, thresholds, weights, model behavior, PM, PC,
MCC, Risk Pacing, Position Sizing, or Runtime.  The audit used ex-post PnL only
to classify campaign groups, then used decision-time artifacts only to judge
whether weakness was visible before loss expansion.

Finding: avoidable-loss candidates are material, but not production-ready.
Plateau losses often showed early decision-time deterioration, and several
large losers kept meaningful capital exposed after first identifiable weakness.
However, the same early-warning surface also appears in many winners, including
major winners.  The current evidence is sufficient for a shadow early-failure /
capital-at-risk bridge, but not sufficient for a live REDUCE/EXIT rule or a
fixed holding-period / blanket early-stop change.

Corrected plateau campaign population:

```text
Target run: runtime-test-historical-extended-smoke-20260825T235520054579Z
Plateau: 2023-05-31 through 2024-02-26
Campaigns opened in plateau: 285
Corrected aggregate campaign PnL: -51,800 JPY
```

The correction matters: open campaigns at `2024-02-26` were valued by final
unrealized PnL, not by raw BUY cashflow.

## Campaign Population

Audit bins below are ex-post analysis labels only.  They are not proposed
production thresholds.

| Ex-post group | Count | PnL |
| --- | ---: | ---: |
| `meaningful_winner` | 9 | +345,730 |
| `small_winner_flat` | 122 | +398,330 |
| `small_loser` | 136 | -343,130 |
| `material_loser` | 14 | -279,430 |
| `large_capital_loser` | 4 | -173,300 |
| Total | 285 | -51,800 |

Analysis bins used:

- `meaningful_winner`: PnL >= +20,000 JPY
- `small_winner_flat`: 0 to +19,999 JPY
- `small_loser`: -1 to -9,999 JPY
- `material_loser`: -10,000 to -29,999 JPY
- `large_capital_loser`: <= -30,000 JPY

## Loss Taxonomy

Descriptive overlapping root classes for plateau loss campaigns:

| Class | Count | Loss PnL | Materiality |
| --- | ---: | ---: | --- |
| `EARLY_FAILURE_DETECTION` | 137 | -769,980 | High signal frequency; not independently actionable. |
| `CHURN` | 104 | -587,800 | High short-horizon realized loss load. |
| `EXIT_TIMING` | 12 | -341,030 | Material post-deterioration loss expansion exists. |
| `CAPITAL_AT_RISK` | 5 | -183,900 | Concentrated in large single-lot losers. |
| `BAD_ADD` | 1 | -6,500 | Not the plateau loss engine. |
| `OTHER` | 17 | -25,880 | Residual small/normal losses. |

These are not exclusive classes.  For example, a large single-lot loser can be
both `CAPITAL_AT_RISK` and `EARLY_FAILURE_DETECTION`.

## Entry-Relative Timeline Comparison

Decision-time weakness was defined for audit only as PM REDUCE/EXIT evidence,
or negative unrealized PnL plus at least two non-PnL weakness flags from current
PIT surfaces such as exhaustion risk, quality rejection / buy-wait, weak
participation, or deteriorating continuation.

| Horizon | Loser n | Loser any weak | Loser strong | Loser neg PnL | Winner n | Winner any weak | Winner strong | Winner neg PnL | Major winner n | Major strong |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| +1BD | 154 | 144 | 96 | 81 | 130 | 117 | 77 | 13 | 9 | 2 |
| +2BD | 116 | 106 | 67 | 72 | 93 | 70 | 45 | 8 | 9 | 2 |
| +3BD | 69 | 63 | 33 | 41 | 55 | 39 | 14 | 6 | 7 | 1 |
| +5BD | 38 | 34 | 18 | 20 | 44 | 32 | 12 | 5 | 6 | 0 |
| +10BD | 9 | 7 | 3 | 3 | 30 | 18 | 5 | 1 | 6 | 0 |

The separation is real but incomplete.  Negative unrealized state is much more
common in losers, but generic weakness flags are also common among winners.

## Winner Control Comparison

Winner-control classification:

| Group | Early identifiable | Late identifiable | Not identifiable |
| --- | ---: | ---: | ---: |
| Losers | 137 | 17 | 0 |
| Winners / flat | 102 | 27 | 2 |
| Meaningful winners | 3 | 6 | 0 |

Major winner false-positive examples:

| Symbol | Final PnL | Entry | Close | First weak evidence |
| --- | ---: | --- | --- | --- |
| 62280 | +57,000 | 2023-12-21 | 2023-12-25 | +1BD PM REDUCE / quality reject while already profitable. |
| 83040 | +33,500 | 2024-02-20 | 2024-02-22 | +1BD PM REDUCE while still positive. |
| 43950 | +26,600 | 2023-06-06 | 2023-06-09 | +3BD PM EXIT with positive PnL. |
| 65730 | +64,730 | 2023-08-14 | 2023-09-04 | Late PM REDUCE after large profit already formed. |

This makes winner-retention risk high.  A naive early-warning-to-exit rule would
likely reduce major winners and would directly violate the Phase32 degradation
guardrail.

## Early Failure Analysis

Decision-time evidence did identify many losers early:

- `EARLY_IDENTIFIABLE`: 137 loser campaigns
- `LATE_IDENTIFIABLE`: 17 loser campaigns
- `NOT_IDENTIFIABLE_WITH_CURRENT_EVIDENCE`: 0 loser campaigns under the audit
  heuristic

This does not mean production evidence is sufficient.  The same heuristic also
flags `102` winners early.  The valid conclusion is narrower: current PIT
evidence is sufficient to build a shadow early-failure trace and study whether
combinations of weakness, capital size, and unrealized deterioration have
economic meaning after winner false-positive accounting.

## Capital-at-Risk Analysis

The largest material loss campaigns were mostly not ADD-expanded.  They were
large initial single-lot deployments that retained capital through the first
weakness observation.

| Symbol | Realized PnL | Entry | Close | Initial notional | Max deployed | First identifiable weakness | Capital at weakness | Post-weakness loss |
| --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: |
| 74770 | -52,400 | 2023-10-02 | 2023-10-05 | 347,500 | 347,500 | 2023-10-03 / +1BD | 340,000 | -44,900 |
| 55740 | -49,500 | 2024-02-06 | 2024-02-09 | 440,000 | 440,000 | 2024-02-08 / +2BD | 426,000 | -35,500 |
| 95650 | -32,500 | 2023-06-20 | 2023-06-27 | 347,500 | 347,500 | 2023-06-26 / +4BD | 321,000 | -6,000 |
| 70330 | -28,000 | 2023-07-04 | 2023-07-07 | 404,000 | 404,000 | 2023-07-06 / +2BD | 400,500 | -24,500 |
| 92460 | -21,500 | 2023-10-06 | 2023-10-11 | 346,500 | 346,500 | 2023-10-10 / +1BD | 335,000 | -10,000 |

`CAPITAL_AT_RISK` is material descriptively.  It is not yet proven excessive in
the production sense, because the same early weakness surface can occur during
normal winner volatility.

## Material Loser Case Studies

### 74770

`74770` bought `100` at `3475` on `2023-10-02`, sold on `2023-10-05`, and
realized `-52,400`.  First identifiable weakness appeared on `2023-10-03`
with unrealized `-7,500`, exhaustion elevated, quality reject, and negative
unrealized PnL.  PM REDUCE followed on `2023-10-04`; close occurred one
business day later.  Most loss expansion happened after weakness was visible,
but the observed PM reaction was not absent.

### 55740

`55740` bought `100` at `4400` on `2024-02-06`, sold on `2024-02-09`, and
realized `-49,500`.  +1BD remained profitable (`+11,500`) with exhaustion risk.
On `2024-02-08`, PM REDUCE, PM weak reasons, quality buy-wait, exhaustion risk,
and unrealized `-14,000` aligned.  Capital at weakness was still `426,000`;
post-weakness loss was about `-35,500`.

### 95650

`95650` bought `100` at `3475` on `2023-06-20`, sold on `2023-06-27`, and
realized `-32,500`.  +1BD to +3BD had elevated exhaustion but remained
profitable (`+21,000`, `+13,000`, `+1,000`).  Strong weakness became
identifiable on `2023-06-26` with PM REDUCE and unrealized `-26,500`.
This is later-identifiable than `74770`, with only about `-6,000` of loss
after strong detection.

### 69420

`69420` bought `100` at `1445` on `2024-02-13`, sold on `2024-02-15`, and
realized `-24,500`.  First weakness was +1BD: PM REDUCE, PM weak reasons,
quality buy-wait, exhaustion elevated, and unrealized `-10,500`.  Close came
one business day later; post-weakness loss was about `-14,000`.

### 92460

`92460` bought `100` at `3465` on `2023-10-06`, sold on `2023-10-11`, and
realized `-21,500`.  First weakness was +1BD in the next available trading
date: PM REDUCE, weak reasons, quality buy-wait, exhaustion elevated, and
unrealized `-11,500`.  Capital at weakness was `335,000`; post-weakness loss
was about `-10,000`.  The realized slice / fill source decision link was less
complete than the PM snapshot, so this also belongs in observability.

## ADD And Loss Expansion

ADD was not the primary loss expansion mechanism in the plateau.

```text
Plateau loser campaigns with buy_count > 1: 1
ADD loser PnL: -6,500
Material ADD losers: 0
```

The only loser with multiple BUY fills in this population was `59550`, with
three buys, entry `2023-06-15`, close `2023-06-23`, and `-6,500` PnL.  The
named material losers (`55740`, `74770`, `95650`, `69420`, `92460`) were
single-buy campaigns.  This keeps G129 / ADD capitalization separate from the
loss-side repair question.

## Exit Timing

The exit-timing issue is partial, not cleanly a PM delay defect.

Top material losers usually had PM REDUCE/EXIT evidence on the first strong
weakness date, or by the next decision day.  Loss expansion then occurred before
final SELL / close, often within one business day.  The meaningful distinction
is:

- detection late: present in cases like `95650`, where early days were still
  profitable and only exhaustion-risk caution was visible;
- PM action late: not generally supported for top losers, because PM REDUCE or
  EXIT often appears at first strong weakness;
- capital reduction late: partially supported, because capital remained exposed
  after weakness and final realized loss worsened;
- Runtime/execution late: not established; Runtime remains a consumer, not a
  redecision authority.

## Avoidable-Loss Candidates

Avoidable-loss candidates are analysis-only rows where first identifiable
weakness precedes close and loss expands afterward.

Examples:

| Symbol | First weak unrealized | Final PnL | Approx loss after weakness | Weakness-to-close lag |
| --- | ---: | ---: | ---: | ---: |
| 74770 | -7,500 | -52,400 | -44,900 | 2BD |
| 55740 | -14,000 | -49,500 | -35,500 | 1BD |
| 30410 | -9,500 | -38,900 | -29,400 | 1BD |
| 70330 | -3,500 | -28,000 | -24,500 | 1BD |
| 36670 | -2,900 | -27,800 | -24,900 | 6BD |
| 40750 | -2,800 | -21,000 | -18,200 | 1BD |
| 69420 | -10,500 | -24,500 | -14,000 | 1BD |
| 92460 | -11,500 | -21,500 | -10,000 | 1BD |

This is enough to call avoidable-loss materiality `PARTIAL`: the loss-after-
weakness mass is real, but the counterfactual requires a rule that does not cut
normal winners.

## Winner False-Positive Risk

Winner false-positive risk is `HIGH`.

Reasons:

- `102` winner / flat campaigns were early-identifiable by the same audit
  weakness surface.
- `3` of `9` meaningful winners were early-identifiable.
- Major winners frequently carried PM REDUCE/EXIT or quality weakness as part
  of normal lifecycle management, not necessarily as evidence that capital
  should have been removed earlier.
- Spring winners show the same problem more strongly: `9` of `10` meaningful
  spring winners were early-identifiable, yet spring produced the major
  positive control gains.

Therefore an early-loss feature must begin as shadow attribution and must not
be converted directly into PM action, PC allocation, PS quantity, Risk Pacing,
or Runtime behavior.

## Spring Vs Plateau

Spring positive control:

```text
Spring campaigns: 95
Spring aggregate campaign PnL: +498,480
Spring meaningful winners: 10 / +626,900
Spring material+large losers: 10 / -197,500
```

Plateau:

```text
Plateau campaigns: 285
Plateau aggregate campaign PnL: -51,800
Plateau meaningful winners: 9 / +345,730
Plateau material+large losers: 18 / -452,730
```

The plateau differs partly because loss frequency and loser notional are much
higher, while major winners are smaller and do not offset the churn.  It does
not differ because losers uniquely expose an easy early-warning signature;
spring winners also carried early warning signals.  The mechanism is therefore
`PARTIAL`: plateau has more loss load and capital-at-risk pressure, but the
evidence surface is not uniquely loser-specific.

## Root-Cause Ranking

| Rank | Class | Judgment | Rationale |
| ---: | --- | --- | --- |
| 1 | `CHURN` | Material | Many short-horizon losses; `104` loss campaigns closed within three business days. |
| 2 | `EARLY_FAILURE_DETECTION` | Material but unsafe alone | Early evidence exists in most losers, but also many winners. |
| 3 | `CAPITAL_AT_RISK` | Material / partial | Five material losers had >=300k deployed or exposed at weakness. |
| 4 | `EXIT_TIMING` | Partial | Post-weakness loss exists; PM action delay is not the dominant proof. |
| 5 | `ENTRY_QUALITY` | Partial | Many losers show overheated / caution / quality weakness soon after entry, but winners can too. |
| 6 | `BAD_ADD` | Low | Only one non-material ADD loser in plateau-open campaigns. |
| 7 | `OBSERVABILITY` | Localized | `92460` has less complete realized/fill source linkage versus PM evidence. |
| 8 | `NORMAL_STRATEGY_LOSS` | Residual | Some losses are normal cost of exploration / rotation. |

## Improvement Feasibility

| Candidate | Feasibility | Notes |
| --- | --- | --- |
| Shadow early-failure trace | `CURRENT_EVIDENCE_SUFFICIENT` | Existing PM, PC, Strategy Intelligence, fills, and realized slices are enough. |
| Shadow capital-at-risk-at-weakness trace | `CURRENT_EVIDENCE_SUFFICIENT` | Current market value / unrealized PnL are available in PM snapshots. |
| Production REDUCE/EXIT rule | `SHADOW_RESEARCH_REQUIRED` | Winner false-positive cost is high. |
| Fixed holding period / blanket early stop | `NOT_SUPPORTED` | Would likely cut winners and violates Phase32 guardrails. |
| New calibrated loser/winner discriminator | `NEW_EVIDENCE_REQUIRED` | Current evidence is ordinal and lifecycle-specific, not calibrated economic proof. |

## Recommended Next Task

Phase32-G should be a shadow-only specification:

```text
canonical_early_failure_capital_at_risk_shadow.v1
```

Minimum row fields:

- `business_date`, `symbol`, `position_campaign_id`, `age_business_days`
- `ex_post_group` only for offline labels, never production authority
- PM action, PM reason codes, unrealized PnL, current market value
- entry notional, max deployed, current weight / notional
- Strategy Intelligence continuation states and evidence sufficiency
- PC quality action, entry admission state, Risk Pacing, Cash state
- first weakness date, capital at weakness, PM REDUCE/EXIT date, close date
- post-weakness loss, winner false-positive bucket, final campaign outcome
- explicit flags: `future_information_used=false`,
  `shadow_only=true`, `not_action_authority=true`

No production behavior should change before this shadow trace is reviewed
against winner retention and spring positive-control preservation.

## Final Judgments

```text
PHASE32_F_AVOIDABLE_LOSS_MATERIAL = PARTIAL
PHASE32_F_EARLY_FAILURE_IDENTIFIABLE = PARTIAL
PHASE32_F_CURRENT_PIT_EVIDENCE_SUFFICIENT = PARTIAL
PHASE32_F_CAPITAL_AT_RISK_EXCESS_MATERIAL = PARTIAL
PHASE32_F_BAD_ADD_LOSS_MATERIAL = NO
PHASE32_F_EXIT_TIMING_LOSS_MATERIAL = PARTIAL
PHASE32_F_CHURN_LOSS_MATERIAL = YES
PHASE32_F_WINNER_FALSE_POSITIVE_RISK = HIGH
PHASE32_F_PLATEAU_LOSS_MECHANISM_DIFFERS_FROM_SPRING = PARTIAL
PHASE32_F_PRIMARY_AVOIDABLE_LOSS_CLASS = CAPITAL_AT_RISK / CHURN
PHASE32_F_SECONDARY_AVOIDABLE_LOSS_CLASSES = EARLY_FAILURE_DETECTION, EXIT_TIMING, ENTRY_QUALITY, OBSERVABILITY
PHASE32_F_PRODUCTION_REPAIR_JUSTIFIED = NO
PHASE32_F_IMPLEMENTATION_READY = NO
PHASE32_F_MINIMAL_NEXT_CHANGE = SHADOW_ONLY canonical_early_failure_capital_at_risk_shadow.v1 spec/trace
PHASE32_F_NEXT_STEP = Phase32-G shadow observability spec with winner false-positive accounting
```

## Files / Commands Inspected

Files and artifact families inspected:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/execution/realized_slices.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/positions/position_campaigns.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/position_management/pm_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/strategy_intelligence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/daily/*/strategy/portfolio_construction.json`
- `docs/phase_reports/phase32_d_add_evidence_bridge_shadow_audit.md`
- `docs/phase_reports/phase32_e_add_vs_new_marginal_comparison_semantic_deep_audit.md`

Commands used:

- `git status --short`
- `find reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z -maxdepth ...`
- `rg --files ...`
- ad hoc read-only Python extraction over daily JSON artifacts

