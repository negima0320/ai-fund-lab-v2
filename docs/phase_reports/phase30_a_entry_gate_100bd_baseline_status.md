# Phase30-A Entry Gate - Current Canonical Status

## Phase29-L21T-BM Canonical Refresh

Task ID:

`Phase29-L21T-BM`

This section supersedes the operational status in the older AO-era sections
below. The older sections are retained as historical record.

Current status:

| Field | Current Status |
| --- | --- |
| Phase30 migration | `USER_APPROVED` |
| Task ID for this refresh | `Phase29-L21T-BM` |
| Clean Baseline Status | `VALIDATION_IN_PROGRESS` |
| Current clean validation run | `runtime-test-historical-extended-smoke-20260815T030154161245Z` |
| Current run status, read-only | `RUNNING` |
| Current next job, read-only | `2022-08-24:market_refresh` |
| 20BD completion | `NOT_ASSUMED` |
| 4-year clean baseline | `NOT_ESTABLISHED` |
| Phase30 performance tuning | `BLOCKED_UNTIL_CLEAN_BASELINE` |

Post-BL clean validation evidence currently observed:

| Date | Equity | Return | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2022-08-10` | `995,860` | `-0.41%` | `745,820` | `25.11%` | `9` |
| `2022-08-12` | `1,000,700` | `+0.07%` | `696,190` | `30.43%` | `8` |
| `2022-08-15` | `998,660` | `-0.13%` | `678,790` | `32.03%` | `9` |
| `2022-08-16` | `986,500` | `-1.35%` | `819,050` | `16.97%` | `7` |

This is early clean-runtime evidence only. It is not a completed 20BD
validation and not a formal performance baseline.

### Baseline Validity Reset

The prior long Historical run:

```text
runtime-test-historical-extended-smoke-20260814T131647480030Z
```

is invalid as formal Strategy performance evidence. Phase29-L21T-BF classified
it as `CAPITAL_AUTHORITY_CONTAMINATED`:

- earliest contamination: `2022-08-10`
- contaminated symbols: `104`
- contaminated days: `299 / 300`
- false Equity reached capital authority
- sizing equity contaminated
- position weights contaminated

Therefore the following from that run must not be used as a formal Phase30
baseline or tuning authority:

- Equity curve / final return / MDD
- Cash and exposure attribution
- BUY_NEW / ADD / SELL performance
- Regime attribution
- Winner giveback
- Campaign performance
- Deployed-capital quality

The old run is retained only as:

```text
RUNTIME_FORENSIC / DEFECT_DISCOVERY_EVIDENCE
```

### Late Phase29 Contracts Now Active

Do not reopen without new evidence:

- Multi-horizon Momentum Trajectory classification.
- `BUY_WAIT` as temporary BUY_NEW ineligibility without Pending / Human Review.
- BUY_WAIT does not block SELL, BUY_ADD, REENTRY, or existing holdings.
- Market-refresh producer integration for AV features.
- BUY Quality propagation of multi-horizon features.
- Execution `NO_SUBMISSION_REQUIRED` / `AUTHORIZED_NO_ORDER` continuity.
- Current valuation adjusted/raw/economic authority separation.
- Price/quantity adjustment-basis contract.
- Basis mismatch fail-closed.
- Runtime-owned basis metadata persistence through Current projection.

### Research Candidate Reclassification

| Candidate | BM Status | Note |
| --- | --- | --- |
| Deployed-Capital Quality | `ACTIVE_AFTER_CLEAN_BASELINE` | Old evidence invalidated; clean deployed-capital and marginal-capital returns required. |
| Winner continuation / premature exit | `ACTIVE_AFTER_CLEAN_BASELINE` | Keep as hypothesis; contaminated giveback numbers cannot tune SELL. |
| Exit Outcome Separability | `REVALIDATION_REQUIRED` | Recompute only on clean baseline. |
| Recovery Re-entry Quality | `REVALIDATION_REQUIRED` | REENTRY contract remains; blanket ban prohibited. |
| Profit Retention / Peak Giveback | `ACTIVE_AFTER_CLEAN_BASELINE` | Measure MFE, peak-to-exit giveback, and realized retention on clean run. |
| Campaign Capital Efficiency | `REVALIDATION_REQUIRED` | Old campaign performance invalidated by valuation contamination. |
| Formal Expected Edge calibration | `ACTIVE_RESEARCH` | Relative score semantics remain; no future-return runtime input. |
| REDUCE Pullback vs Breakdown separability | `ACTIVE_RESEARCH` | REDUCE discrete-lot semantics resolved in Phase29; quality separability remains research. |
| Multi-Horizon Momentum Trajectory outcome | `NEW_ACTIVE_RESEARCH_AFTER_CLEAN_BASELINE` | Evaluate HEALTHY / FADING / OVERHEAT / MIXED clean forward outcomes. |
| SELL / PM Market Context Authority | `NEW_ACTIVE_RESEARCH_AFTER_CLEAN_BASELINE` | Audit whether SELL is context-aware or only reacts after individual weakness. |

### Updated Phase30 Priority Order

1. Clean Performance Measurement Foundation.
2. Clean Long-Horizon Baseline.
3. Deployed-Capital Quality.
4. Entry Quality / Momentum Trajectory.
5. Winner Continuation / Profit Retention.
6. Market Regime / Regime Transition clean revalidation.
7. SELL / Position Management Market Context Authority.
8. Exit Outcome Separability.
9. ADD Quality.
10. Recovery Re-entry Quality.
11. Formal Expected Edge Calibration.

Immediate Strategy change required: `NO`

Immediate threshold change required: `NO`

Phase30 performance work must start from clean measurement, not from old
contaminated performance attribution.

## Primary Judgment

`PHASE29_L21T_AO_BUY_QUALITY_RELATIVE_SCORE_FORWARD_OUTCOME_ATTRIBUTION_READ_ONLY_AUDIT_COMPLETE_INSUFFICIENT_FOR_IMMEDIATE_GATE_CHANGE`

This document is the canonical current-state register for Phase30 entry.  It is
not Phase30 approval.  Current phase remains `Phase29`.

## A. Current Canonical Entry Status

| Field | Current Status |
| --- | --- |
| Current Phase | `Phase29` |
| Phase30 Full Entry | `NOT YET` |
| Latest Completed Repair | `Phase29-L21T-AM` |
| Latest Read-Only Audit | `Phase29-L21T-AO` |
| AM Primary Judgment | `PHASE29_L21T_AM_RUNTIME_OPPORTUNITY_SEMANTIC_METADATA_PROPAGATION_REPAIRED_ACTUAL_ADAPTER_REGRESSION_PASS` |
| Expected Edge absolute-gate defect | `RESOLVED` |
| PC downstream authority migration gap | `RESOLVED` |
| Runtime adapter semantic metadata gap | `RESOLVED` |
| Post-AM actual runtime behavioral change | `CONFIRMED_EARLY` |
| Post-AM fresh validation | `ACTIVE / PARTIAL` |
| Full 4-year performance baseline | `NOT COMPLETE` |
| Final performance audit | `NOT COMPLETE` |
| Phase29 closure | `NO` |
| Current Active Entry Blocker | `POST_AM_LONG_HORIZON_PERFORMANCE_VALIDATION_NOT_COMPLETE` |

Run-state read-only evidence for the current post-AM validation:

| Field | Value |
| --- | --- |
| Current Post-AM Validation run | `runtime-test-historical-extended-smoke-20260814T054658313415Z` |
| run_state status | `RUNNING` |
| completed business days observed | `55` |
| completed range observed | `2022-08-10` through `2022-10-31` |
| next job snapshot | `2022-11-01:morning` |
| Codex runtime mutation | `NO` |
| Codex fresh-run / resume / replay / recovery / long Historical | `NO` |

Phase30 Full Entry requires:

- post-AM long-horizon validation completion;
- runtime stability confirmation;
- final performance audit;
- final Phase29 handoff refresh;
- explicit Phase29 closure.

AM early behavior evidence is necessary but not sufficient for Phase30 entry.

## B. Post-AM Fresh Validation Evidence

The current post-AM fresh validation is user-operated.  It is the only current
post-AM validation run:

```text
runtime-test-historical-extended-smoke-20260814T054658313415Z
```

Early runtime behavior changed materially after AM.

| Date | Equity | Return | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2022-08-10` | `995,400` | `-0.46%` | `807,480` | `18.88%` | `11` |
| `2022-08-12` | `998,410` | `-0.16%` | `752,750` | `24.61%` | `9` |

Post-AM holdings on `2022-08-10`:

```text
23230(200), 23700(300), 23880(100), 30100(100), 36640(300),
66590(200), 76470(600), 89180(1600), 93180(4000), 94320(100), 94340(100)
```

Post-AM holdings on `2022-08-12`:

```text
23230(200), 23700(300), 30100(100), 36640(300), 89180(1200),
91070(100), 93180(4000), 94320(100), 94340(100)
```

Interpretation:

```text
POST_AM_ACTUAL_RUNTIME_BEHAVIOR_CHANGE_CONFIRMED
PERFORMANCE_ACCEPTANCE_NOT_YET
```

Pre-AM `2022-08-10` behavior was concentrated around roughly one position and
the primary holding `94320`.  Post-AM `2022-08-10` has `11` positions, including
representative candidates previously excluded by stale absolute score semantics:
`23700`, `36640`, `66590`, and `93180`.

Do not infer Strategy performance from two business days.  This evidence proves
runtime reachability / behavior change, not long-horizon performance acceptance.

## B2. Phase29-L21T-AO Read-Only Attribution Update

`Phase29-L21T-AO` joined post-AM actual BUY_NEW evidence with J-Quants adjusted
close forward returns for read-only attribution.  It did not change Runtime,
Strategy, config, models, thresholds, or run state.

Current AO judgment:

```text
PHASE29_L21T_AO_BUY_QUALITY_RELATIVE_SCORE_FORWARD_OUTCOME_ATTRIBUTION_READ_ONLY_AUDIT_COMPLETE_INSUFFICIENT_FOR_IMMEDIATE_GATE_CHANGE
```

AO observed `99` actual BUY_NEW samples across the available `55` completed
business days.  Current evidence does not justify restoring an absolute
`runtime_opportunity_score < 0` BUY reject gate.  REDUCED and REDUCED x negative
score groups are mixed: the `2022-08-10` anchor supports a design-review
hypothesis, while the available equal-weight multi-day sample does not show
consistent underperformance.

Carry-forward:

```text
PHASE30_RESEARCH_CANDIDATE_DEPLOYED_CAPITAL_QUALITY_BUY_QUALITY_X_RELATIVE_SCORE
NO_IMMEDIATE_RUNTIME_GATE_CHANGE
CURRENT_POST_AM_RUN_SHOULD_CONTINUE_ABSENT_RUNTIME_DEFECT
```

AO also found a separate follow-up candidate: PC incremental accepted BUY_NEW
weight versus actual EOD exposure semantics / lot execution reconciliation.
This is not treated as an AO Runtime defect.

## C. Phase29 Confirmed / Repaired Contracts

### BUY / SELL Independence

Confirmed:

- BUY Pending or BUY Review must not stop valid SELL authority.
- BUY and SELL are independent authorities.
- HOLD / REDUCE / EXIT / mandatory SELL authority must not be blocked by BUY
  item-scoped review.
- Production-common behavior is preserved.

### ADD

Confirmed and repaired:

- PM ADD to Runtime BUY_ADD connection;
- incremental investment semantics;
- target-weight increase path;
- opportunity-cost comparison;
- no-loss-averaging protection;
- ADD lot realization;
- BUY_ADD execution path.

Do not reopen “ADD is not connected to Runtime” as an active defect without new
evidence.

### Lot / Capital Conversion

Confirmed and repaired:

- Japanese equity 100-share lot constraint;
- Strategy single-name cap `18%`;
- Safety hard cap `25%`;
- Strategy cap and Safety hard cap are separate authorities;
- lot-first capital allocation;
- cap-constrained lot resolution;
- iterative residual capital reallocation;
- lot / minimum notional zero observability;
- one lot over Safety hard cap remains fail-closed.

### Capital Deployment

Confirmed:

- High cash has multiple causes: Opportunity availability, eligibility, score
  semantics, lot constraints, concentration, minimum executable notional,
  residual capital, and Safety.
- Some periods can reach over `90%` exposure, so Runtime is not structurally
  incapable of deployment.
- Cash reduction itself is not a valid objective.
- Forced `80%`, `90%`, or `100%` exposure is not approved.

### Re-entry

Confirmed and implemented:

- no blanket re-entry ban;
- semantic REENTRY;
- cooldown;
- recovery hurdle;
- low-price risk;
- tick risk;
- liquidity capacity.

Phase30 may study Re-entry quality, but must not treat Re-entry itself as
categorically bad.

### REDUCE

Confirmed and implemented:

- sub-lot REDUCE is not forcibly ceiled;
- REDUCE does not automatically escalate to EXIT;
- `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`;
- `REDUCE_UNEXECUTABLE_DUE_TO_MINIMUM_NOTIONAL`;
- next-day fresh PM reevaluation;
- no persistent reduce debt.

Phase30 future research candidate: Pullback vs Breakdown separability.

### Expected Edge / Opportunity Score

Confirmed:

```text
runtime_opportunity_score = uncalibrated_relative_model_score
```

It is not currently an economic expected-return unit.  Therefore:

- raw score `<= 0` is not an absolute BUY reject;
- `non_positive_expected_edge_score` is not an absolute hard gate under
  complete uncalibrated metadata;
- standalone `below_opportunity_top20` is not an absolute hard gate;
- the score is a relative competition signal.

Formal economic calibration remains a future research candidate.

### Authority Migration / Adapter Contract

Confirmed:

- repairing core code is not enough if actual Runtime adapters strip authority
  metadata;
- actual Production-common adapters must preserve semantic metadata into
  consumer-visible source summaries;
- `canonical_score_field`, `score_semantic_role`, `calibration_applied`, and
  `economic_units_available` are mandatory metadata for the PC source-summary
  contract when present in the Opportunity source artifact;
- source-present metadata must not be stripped;
- truly missing or malformed metadata remains fail-closed.

### Runtime Test Operator Lifecycle

Confirmed and repaired:

- runtime-test stop command exists;
- `RUNNING` can transition to `HALT` through operator stop;
- stopped runs can be abandoned;
- stale `RUNNING` lifecycle issue is repaired.

## D. Phase30 Carry-Forward Research Topics

Resolved Phase29 defects, not active Phase30 blockers:

- absolute `non_positive_expected_edge_score` gate;
- raw negative score target-member gate;
- standalone `below_opportunity_top20` gate;
- PC semantic authority migration gap;
- Runtime adapter metadata propagation gap.

Phase30 Future Research Candidates:

1. Deployed-Capital Quality
2. Winner continuation / premature exit
3. Exit Outcome Separability
4. Recovery Re-entry Quality
5. Profit Retention / Peak Giveback
6. Campaign Capital Efficiency
7. Formal Expected Edge calibration
8. REDUCE Pullback vs Breakdown separability

Priority remains provisional until post-AM long-horizon final evidence is
available.

Expected Edge distinction:

| Category | Status |
| --- | --- |
| uncalibrated score used as absolute zero gate | `SOLVED_IN_PHASE29` |
| relative score predictive separation / calibration capability | `FUTURE_RESEARCH` |

Phase30 may ask whether `runtime_opportunity_score` can be formally calibrated
into economically meaningful expected-return units.  It must not use AF
forward-return evidence as Runtime input.

### Do Not Reopen Without New Evidence

Do not reintroduce these as default Phase30 changes without new evidence:

- fixed BUY count;
- fixed target position count;
- forced `80%`, `90%`, or `100%` exposure;
- Rank1 auto-BUY;
- Top-N auto-BUY;
- negative score auto-reject;
- negative score auto-BUY;
- blanket re-entry ban;
- REDUCE ceil-to-one-lot;
- automatic REDUCE to EXIT;
- Historical-specific Strategy;
- Production fail-closed weakening;
- BUY / SELL coupling;
- future return as Runtime input.

## E. Pre-AM Partial Performance Research Evidence

The following run evidence is retained only as:

```text
PRE-AM / PARTIAL HISTORICAL RESEARCH EVIDENCE
```

It is useful for hypothesis formation but must not be used as formal post-AM
Strategy performance acceptance.

Important retained research contexts:

- Exit forward return audit;
- Good Cut vs Premature Exit;
- Recovery Re-entry examples;
- large winner `59350`;
- long HOLD `94320`;
- peak giveback evidence;
- symbol contribution;
- REDUCE lot-zero evidence;
- partial long-horizon capital deployment and exit-outcome evidence.

Pre-AM partial long-horizon research run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Partial state observed in prior read-only evidence:

| Metric | Value |
| --- | ---: |
| Initial cash | `1,000,000 JPY` |
| Cash | `129,890 JPY` |
| Buying power | `129,890 JPY` |
| Market value | `947,170 JPY` |
| Total equity | `1,077,060 JPY` |
| Observed partial return | `+7.706%` |
| Final cash ratio | `12.0597%` |
| Final gross exposure ratio | `87.9403%` |
| Average cash ratio, carried-ledger estimate | `43.4813%` |
| Average gross exposure ratio, carried-ledger estimate | `56.5187%` |

Interpretation retained:

```text
Capital utilization improved, especially by final observed exposure.
Return was not enough.
Phase30 must distinguish capital deployment from deployed-capital quality.
```

This evidence predates AM behavior changes and is not a current formal
post-AM baseline.

## F. Superseded / Historical Timeline

Superseded runs:

| Run | Current Label |
| --- | --- |
| `runtime-test-historical-smoke-20260812T212155604711Z` | `PRE-AM / PARTIAL HISTORICAL RESEARCH EVIDENCE` |
| `runtime-test-historical-extended-smoke-20260814T005603520480Z` | `pre-AH / historical debugging evidence` |
| `runtime-test-historical-extended-smoke-20260814T032532992929Z` | `pre-AK evidence` |
| `runtime-test-historical-extended-smoke-20260814T041426689731Z` | `pre-AM evidence` |
| `runtime-test-historical-extended-smoke-20260814T054658313415Z` | `CURRENT POST-AM VALIDATION` |

Resolved blocker statuses:

| Former Blocker | Current Status |
| --- | --- |
| `BLOCKED_BY_PHASE29_L21T_AJ_PC_AUTHORITY_MIGRATION_GAP` | `RESOLVED_BY_AK` |
| `BLOCKED_PENDING_POST_AK_FRESH_BASELINE_VALIDATION` | `SUPERSEDED_BY_AL_FINDING_AND_AM_REPAIR` |
| `BLOCKED_BY_PHASE29_L21T_AL_RUNTIME_METADATA_PROPAGATION_GAP` | `RESOLVED_BY_AM` |
| `BLOCKED_PENDING_POST_AM_FRESH_EARLY_GATE_VALIDATION` | `EARLY_GATE_PASS` |

Compressed repair timeline:

| Task | Current Interpretation |
| --- | --- |
| L21T-AF | showed poor low-exposure forward-return separability for the old absolute Expected Edge gate |
| L21T-AG | designed relative-first semantics for uncalibrated Opportunity score |
| L21T-AH | moved Runtime Opportunity eligibility to relative semantics |
| L21T-AJ | confirmed stale absolute authority still existed in PC |
| L21T-AK | repaired PC and Runtime Planning semantic authority |
| L21T-AL | confirmed actual Runtime adapter dropped canonical semantic metadata |
| L21T-AM | repaired actual Production-common adapter propagation and added actual-adapter regression |
| Post-AM validation | confirmed material runtime behavior change in early actual holdings |

Detailed reports:

```text
docs/phase_reports/phase29_l21t_af_expected_edge_opportunity_gate_forward_return_attribution_audit.md
docs/phase_reports/phase29_l21t_ag_expected_edge_gate_calibration_allocation_semantics_design.md
docs/phase_reports/phase29_l21t_ah_expected_edge_relative_allocation_semantics_implementation.md
docs/phase_reports/phase29_l21t_aj_post_ah_portfolio_construction_zero_weight_root_cause_audit.md
docs/phase_reports/phase29_l21t_ak_post_ah_downstream_portfolio_construction_relative_allocation_authority_completion.md
docs/phase_reports/phase29_l21t_al_post_ak_runtime_authority_path_mismatch_root_cause_audit.md
docs/phase_reports/phase29_l21t_am_runtime_opportunity_semantic_metadata_propagation_repair.md
```

## Current Next Operator Action

Continue the user-operated post-AM fresh long-horizon validation.  Codex must
not run long Historical, fresh-run, resume, replay, or recovery from this
document.

Next major gate:

```text
Post-AM long-horizon runtime stability and performance completion
```

After completion:

```text
Phase29 Final Long-Horizon Performance Audit
-> Phase29 Closure / Phase30 Handoff Refresh
-> Phase30 Entry Decision
```

## Current Next Codex Work

Do not start Phase30-A yet.

Recommended next Codex work:

```text
Observe / audit post-AM fresh validation as Phase29 evidence.
```

## Final Gate Answer

Is Phase30 currently blocked by unrepaired Expected Edge / PC / adapter defects?

```text
NO
```

Evidence: AH/AJ/AK/AL/AM resolved the absolute Expected Edge gate, PC authority
migration gap, and Runtime adapter metadata propagation gap; post-AM actual
holdings reached previously excluded candidates.

Is the current main blocker that post-AM fresh long-horizon performance
validation is not complete?

```text
YES
```

Evidence: the current post-AM validation run is still `RUNNING`; full
long-horizon completion, runtime stability review, final performance audit,
handoff refresh, and Phase29 closure remain incomplete.
