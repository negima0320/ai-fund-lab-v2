# Phase29-L21Q - Re-entry Recovery Policy Necessity / Threshold / Corporate-Action Gate Audit

## Executive Summary

L21Q is a read-only policy and architecture audit. No production implementation, config, threshold, schema, model, Accepted Generation, Runtime, Pending, fresh-run, resume, or historical run mutation was performed.

Primary result: REENTRY protection is necessary, but the current L16 recovery contract is overconstrained and partially under-justified for the current post-L21I score semantics. The strongest evidence supports campaign-aware re-entry protection, cooldown/state-change awareness, Buy Quality requalification, and trend/momentum recovery. The weakest evidence supports the fixed absolute `runtime_opportunity_score >= 0.10` threshold and the unconditional requirement that every REENTRY row carry row-level corporate action status.

Primary classification:

`REENTRY_POLICY_REQUIRED_BUT_OVERCONSTRAINED`

Secondary classifications:

- `ABSOLUTE_SCORE_THRESHOLD_SEMANTICALLY_UNJUSTIFIED`
- `CORPORATE_ACTION_GATE_OVERBROAD`
- `CORPORATE_ACTION_SOURCE_MATERIALIZATION_GAP`
- `REENTRY_POLICY_SIMPLIFICATION_RECOMMENDED`

Primary judgment:

`PHASE29_L21Q_REENTRY_POLICY_REQUIRED_BUT_CURRENT_CONTRACT_OVERCONSTRAINED_SIMPLIFICATION_DESIGN_REQUIRED`

## L21P Baseline

L21P confirmed that L21K prior EXIT materialization reaches Portfolio Construction (PC):

- 23880 / 2022-09-01 receives `prior_exit_business_date=2022-08-30`.
- PC classifies it as `semantic_buy_type=REENTRY`.
- `business_days_since_exit=1`.
- Existing recovery hurdle is evaluated.
- The row fails current policy with `reentry_expected_edge_below_threshold`.

L21P also confirmed:

- `runtime_opportunity_score` is the canonical score consumed by REENTRY recovery.
- `runtime_opportunity_score=0.20` can PASS.
- `runtime_opportunity_score=0.01` fails the current `0.10` threshold.
- Corporate action evidence present as `NO_EVENT` can PASS.
- Corporate action evidence absent produces `REVIEW_REQUIRED / reentry_corporate_action_status_missing`.

## REENTRY Policy Origin

Origin chain:

| Phase | Evidence |
| --- | --- |
| Phase28-D20 | Re-entry loss concentration confirmed. 93 re-entry campaigns, 68 within 1BD, re-entry PnL `-105,800`, non-re-entry PnL `+164,000`, `loss -> <=5BD re-entry -> loss` count 16 and PnL `-181,240`. Root cause: BUY_NEW path did not consume previous campaign close date, exit reason, recent-loss state, or cooldown/state-change evidence. |
| Phase28-D21 | Designed campaign-aware state-change gated re-entry. Required previous campaign context, previous exit reason, recent-loss state, state-change evidence, and fail-closed behavior when context is missing. Time was supporting evidence, not primary authority. |
| Phase29-L13 | Recommended semantic REENTRY plus recovery hurdle as part of low-price / re-entry allocation guard design. Threshold calibration still required. |
| Phase29-L14 | REENTRY semantic READY, but cooldown calibration and recovery hurdle calibration NOT_READY. Observed fill re-entry cases: 4, across 2 symbols. |
| Phase29-L15 | Moved to `READY_WITH_CANDIDATE_RANGE`, with rank `<=5..10`, score `0.10..0.20`, BQ REDUCED/FULL, trend/momentum recovered, CA resolved, capacity non-severe. |
| Phase29-L16 | Implemented `3` completed-BD cooldown and recovery hurdle: rank `<=10`, expected edge `>=0.10`, BQ REDUCED/FULL, CA resolved/no event, capacity `<=0.03`, trend or momentum recovered. |

Origin findings:

| Item | Finding |
| --- | --- |
| Why REENTRY policy exists | Evidence-backed. D20 found concentrated short-cycle re-entry losses and missing campaign-aware BUY_NEW protection. |
| Cooldown origin | D20 immediate churn evidence, D21 state-change design, L15 candidate range `1BD..5BD`; L16 selected `3BD`. |
| Recovery hurdle origin | D21 state-change design, L13-L15 recovery candidate formula, L16 implementation. |
| `0.10` threshold origin | L15 candidate range lower bound `0.10..0.20`, adopted by L16. |
| `0.10` empirical SoT | `RATIONALE_NOT_FOUND` for a calibrated absolute economic threshold. Evidence supports a candidate range, not a proven absolute boundary. |
| Corporate action requirement origin | L13-L16 recovery candidate lists and preservation of Corporate Action fail-closed behavior. |
| All-REENTRY corporate action requirement rationale | `RATIONALE_NOT_FOUND` for requiring explicit row-level CA status even when source has authoritative `NO_EVENT`. |
| Previous EXIT reason usage origin | D21 requires it; current L16 implementation does not consume it. |

## Current Recovery Contract

Current PC REENTRY target path:

1. BUY side row reaches PC as an ADD candidate.
2. Current position must be absent.
3. Prior same-symbol EXIT field must exist and be before the decision date.
4. PC classifies semantic `REENTRY`.
5. Cooldown must pass: `business_days_since_exit >= 3`.
6. Recovery must pass:
   - rank `<=10`
   - `runtime_opportunity_score >= 0.10`
   - BQ action in `REDUCED_ALLOCATION_ONLY` or `FULL_ALLOCATION_ELIGIBLE`
   - corporate action status in `PASS`, `RESOLVED`, `NO_BLOCKING_EVENT`, `NO_EVENT`
   - capacity evidence present and not severe: `capacity_ratio <=0.03`
   - `trend_close_over_ma_20d >=1.0` OR `price_momentum_return_20d >=0`
7. Then normal low-price / liquidity caps still apply.
8. Then lot-aware allocation, Safety, cash, gross exposure, broker feasibility, and downstream planning still apply.

Contract table:

| Condition | Field | Producer | Consumer | Required | PASS | FAIL | REVIEW_REQUIRED | Purpose |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Prior EXIT | `prior_exit_business_date` | L21K ledger materialization or explicit row authority | PC | Yes for REENTRY | prior date `< D` | not REENTRY if absent | n/a | Identify closed-campaign re-entry |
| Cooldown | `business_days_since_exit` | PC | PC | Yes | `>=3` | `<3` | n/a | Short churn protection |
| Score | `runtime_opportunity_score` | Runtime BUY AI / Opportunity | PC | Yes | `>=0.10` | `<0.10` | missing | Current opportunity strength |
| Rank | `opportunity_buy_rank` / `reentry_rank` | Opportunity / PC | PC | Yes | `<=10` | `>10` | missing | Relative opportunity position |
| Buy Quality | `quality_action` | Buy Quality | PC | Yes | REDUCED/FULL | other action | missing | Current BUY requalification |
| Corporate Action | CA status row field | Corporate Event if propagated | PC | Yes | resolved/no event | unresolved | missing | Avoid unresolved event re-buy |
| Liquidity | `capacity_ratio` | PC from target notional and rolling traded value | PC | Yes | `<=0.03` and non-severe | severe or `>0.03` | missing | Avoid excessive participation |
| Trend/momentum | technical fields | Technical features if propagated | PC | Yes | trend `>=1` OR momentum `>=0` | both present and weak | both missing | Evidence of recovery |

## Normal BUY_NEW vs REENTRY

| Dimension | Normal BUY_NEW | REENTRY additional requirement |
| --- | --- | --- |
| Prior EXIT | Not required | Required to classify REENTRY |
| Cooldown | None | `>=3` completed business days |
| Score | Subject to Opportunity / BQ semantics, but no PC absolute `0.10` gate | PC requires `runtime_opportunity_score >=0.10` |
| Rank | Used in ranking/priority | PC hard recovery gate `rank <=10` |
| Buy Quality | Must pass/non-reject for allocation | Must be REDUCED/FULL again |
| Trend/momentum | Not a universal PC BUY_NEW gate | Must show recovery or non-negative momentum |
| Liquidity | Normal low-price/liquidity caps may apply | Capacity evidence mandatory for recovery |
| Corporate Action | Corporate Event authority exists, but normal BUY_NEW is not universally blocked by missing row-level CA status in the same way | Explicit CA status mandatory for every REENTRY |
| Previous EXIT reason | n/a | Not currently used, despite D21 design |
| Target allocation | Can receive final target after PC fit | Zeroed before final target if cooldown/recovery non-PASS |

REENTRY is therefore materially stricter than normal BUY_NEW. In the L21O baseline, BUY_NEW positive allocation was 72 / 239, while REENTRY positive allocation was 0 / 309.

## 0.10 Threshold Origin

Current threshold:

```text
runtime_opportunity_score >= 0.10
```

Origin:

- L14: recovery hurdle threshold NOT_READY.
- L15: candidate range `0.10..0.20`, with operator acceptance required.
- L16: implemented lower bound `0.10`.

Assessment:

- Designed threshold: PARTIAL.
- Empirical threshold: WEAK.
- Calibrated economic threshold: NO.
- Legacy/copied/test-only threshold: not proven.
- SoT for fixed absolute semantic validity: `RATIONALE_NOT_FOUND`.

The best-supported interpretation is that `0.10` is the lower bound of an approved candidate range, not a validated absolute economic boundary.

## Score Semantic Audit

L21I establishes:

```text
runtime_opportunity_score = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

This means:

- The score is usable for relative opportunity strength.
- It is not an economic expected return.
- Raw sign or fixed raw thresholds require special justification.

The current REENTRY code no longer consumes legacy aliases first; it uses canonical `runtime_opportunity_score`. That aligns with L21I field authority. However, treating `0.10` as a fixed absolute threshold across dates, symbols, and model versions is not fully supported by L21I. There is no evidence in L21Q that `0.10` is distribution-normalized, cross-date comparable, cross-symbol calibrated, or model-version stable as an absolute recovery threshold.

Judgment:

`ABSOLUTE_SCORE_THRESHOLD_SEMANTICALLY_UNJUSTIFIED`

This does not mean low scores are good. It means the architecture should prefer relative qualification, rank, BQ, trend/momentum recovery, and previous EXIT context over an uncalibrated absolute number.

## Score Distribution

Read-only L21O baseline scope:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T152905733571Z
daily strategy PC rows through 2023-08-18
membership_intent = ADD_CANDIDATE
```

Reproduced counts:

| Metric | Count |
| --- | ---: |
| PC candidates | 548 |
| Positive allocation | 72 |
| Zero allocation | 476 |
| REENTRY | 309 |
| REENTRY zeros | 309 |
| `reentry_corporate_action_status_missing` | 193 |
| `reentry_expected_edge_below_threshold` | 116 |

`reentry_expected_edge_below_threshold` score bands:

| Band | Count |
| --- | ---: |
| `<0` | 0 |
| `0-0.02` | 27 |
| `0.02-0.05` | 43 |
| `0.05-0.10` | 46 |
| `0.10-0.20` | 0 |
| `>=0.20` | 0 |

Quantiles for the 116:

| Metric | Value |
| --- | ---: |
| min | 0.00024082 |
| p25 | 0.02403066 |
| median | 0.04042907 |
| p75 | 0.06479252 |
| max | 0.09732092 |

Normal BUY_NEW positive allocation score bands:

| Band | Count |
| --- | ---: |
| `<0` | 0 |
| `0-0.02` | 19 |
| `0.02-0.05` | 12 |
| `0.05-0.10` | 11 |
| `0.10-0.20` | 13 |
| `>=0.20` | 17 |

Key finding:

42 / 72 normal BUY_NEW positive allocations had `runtime_opportunity_score <0.10`. Therefore the 116 REENTRY rejects cannot be described as economically weak solely from the raw score; they are weak only under the special REENTRY absolute threshold.

## Corporate Action Gate Audit

The current PC consumer accepts row-level CA status fields:

- `corporate_action_status`
- `corporate_event_status`
- `corporate_action_blocking_status`
- `corporate_event_blocking_status`

L21P confirmed:

- if `NO_EVENT` reaches the row, CA gate can PASS;
- if row-level status is absent, REENTRY becomes `REVIEW_REQUIRED`.

L21Q classification of L21O 193 missing cases:

| Classification | Count |
| --- | ---: |
| `EXPLICIT_NO_EVENT_NOT_PROPAGATED` | 193 |
| `SOURCE_PRESENT_ROW_FIELD_MISSING` | 0 |
| `SOURCE_MISSING` | 0 |
| `CORPORATE_EVENT_EXISTS` | 0 |
| `TEMPORAL_AUTHORITY_FAILURE` | 0 |
| `UNKNOWN` | 0 |

Interpretation:

For these 193 rows, same-day `strategy/corporate_event.json` was present and the symbol was in `known_no_event_symbols`. The PC row nevertheless carried `reentry_corporate_action_status=UNKNOWN`.

Therefore the 193 are not evidence of actual corporate action risk. They are evidence of `NO_EVENT` authority not being propagated into the REENTRY recovery row.

## Corporate Action Missing Classification

Top symbols among the 193:

| Symbol | Count |
| --- | ---: |
| 76470 | 64 |
| 93180 | 58 |
| 72730 | 15 |
| 45940 | 14 |
| 59550 | 13 |
| 40520 | 11 |
| 99840 | 8 |
| 37790 | 5 |
| 45410 | 4 |
| 65500 | 1 |

Finding:

`status missing` must not be interpreted as `corporate action risk exists`. In the audited baseline it means the row-level consumer field is missing despite source-side no-event authority.

## Previous EXIT Reason Awareness

Current L16/L21P policy does not use previous EXIT reason.

It does not distinguish:

- hard stop loss,
- trend/opportunity deterioration,
- risk reduction,
- corporate action exit,
- portfolio competition,
- administrative/forced exit,
- profitable exit followed by new opportunity.

The current contract is:

```text
prior EXIT exists
-> all REENTRY rows share the same cooldown and recovery hurdle
```

This is materially simpler than Phase28-D21, which required previous exit reason, recent-loss state, previous score/rank/market context, and state-change evidence.

## Re-entry Churn Protection

Minimum protection still needed:

- prior EXIT awareness;
- closed-campaign to new BUY_NEW separation;
- minimum business-day separation or equivalent state-change requirement;
- current Opportunity requalification;
- Buy Quality requalification;
- trend/momentum or state-change recovery;
- previous EXIT reason resolution for loss / hard-stop / trend-break exits;
- no current unresolved blocking corporate action.

Less clearly necessary:

- uncalibrated absolute score threshold `>=0.10`;
- unconditional row-level CA status for every REENTRY when same-day source says `NO_EVENT`;
- duplicated gates that already exist in Opportunity / BQ unless they add recovery-specific meaning.

## Policy Simplification Candidates

| Candidate | Assessment |
| --- | --- |
| A. Keep current | Preserves churn protection, but retains overconstraint and source propagation brittleness. |
| B. Remove absolute `0.10` only | Not enough in current artifacts: 0 newly eligible, because all candidates then hit CA/capacity/trend-momentum missing gates. |
| C. Replace absolute score with relative qualification | Architecturally preferable: rank, BQ, relative strength, trend/momentum recovery, and previous EXIT reason match D21 and L21I better than fixed score. |
| D. Corporate Action conditionalization | Recommended: require CA resolution if previous EXIT reason or current source indicates CA relevance; otherwise consume source-level `NO_EVENT`. |
| E. Simplified REENTRY contract | Feasible as design: prior EXIT known + cooldown/state-change + BQ valid + opportunity strong relative to current set + previous weakness recovered + no current blocking CA. |

## Counterfactual Eligibility

Baseline REENTRY rows through 2023-08-18:

| Scenario | Eligible by current row-level evidence |
| --- | ---: |
| Current policy | 0 |
| Remove score `>=0.10` only | 0 |
| Remove CA missing gate only | 0 |
| Remove both score and CA missing gates | 0 |

Why zero? Because current row-level evidence then exposes additional mandatory missing fields:

- removing score only leaves CA missing;
- removing CA only exposes score below threshold and capacity missing;
- removing both exposes capacity missing, then trend/momentum missing.

Source-aware simplified estimate:

If same-day `corporate_event.json` `known_no_event_symbols` and same-day `technical_features.json` trend/momentum are allowed as source authority, and the absolute `0.10` gate is replaced by rank/BQ/current recovery evidence, then 264 / 293 cooldown-PASS REENTRY rows are estimable policy-eligible before lot/Safety/Cash/Gross execution feasibility.

Composition of the 264:

| Current primary reason | Count |
| --- | ---: |
| `reentry_corporate_action_status_missing` | 159 |
| `reentry_expected_edge_below_threshold` | 105 |

Score bands for the 264:

| Band | Count |
| --- | ---: |
| `0-0.02` | 23 |
| `0.02-0.05` | 38 |
| `0.05-0.10` | 44 |
| `0.10-0.20` | 78 |
| `>=0.20` | 81 |

This is not a BUY execution claim. It is policy eligibility before lot/Safety/Cash/Gross constraints.

## Capital Deployment Impact

L21Q does not estimate PnL or future returns.

Mechanics-only finding:

- Current row-level policy eligible REENTRY count: 0.
- Source-aware simplified policy-eligible estimate: 264.
- Theoretical additional REENTRY policy candidates: up to 264.
- One-lot feasible count: not determinable from current PC member rows for these REENTRY zeros; `phase29_l19_lot_resolution` is absent on the inspected zero REENTRY rows.
- Positive final target count: 0 under current artifacts.
- Theoretical deployable notional: not safely estimable without lot-resolution / Safety / cash / gross replay.
- Theoretical gross exposure impact: not safely estimable in L21Q.

Therefore capital deployment impact is potentially material but requires a separate read-only replay/design task. It must not be solved by forced buying or threshold loosening alone.

## Regression Assessment

Regression confirmed: NO.

Reason:

There is no evidence that a more appropriate production REENTRY policy existed and then regressed into the current stricter policy. The evidence shows a policy design gap / calibration gap:

- D20 found no active runtime re-entry guard.
- D21 designed richer campaign-aware state-change gating.
- L16 implemented a simpler recovery hurdle with candidate-range thresholds.
- L21I later clarified that the consumed score is uncalibrated relative/model score.

Classification:

`Policy Design Gap / Architecture Overconstraint / Calibration Gap`

## Architecture Assessment

Architecture assessment:

1. REENTRY protection is required and evidence-backed.
2. The current contract is not well calibrated as an absolute-score policy.
3. The current contract is overbroad on corporate action because source-side `NO_EVENT` is not consumed and all REENTRY rows are treated as requiring explicit row status.
4. The current contract is less semantically rich than D21 because it ignores previous EXIT reason and state-change context.
5. The current artifact path has source materialization gaps for CA, trend/momentum, and capacity fields. Removing a single gate does not make rows eligible.
6. Simplification should be design-first, not a one-line threshold relaxation.

## Recommended Next Task

Recommended next task:

`Phase29-L21R - Re-entry Recovery Contract Simplification Design / Source Evidence Wiring Plan`

Scope:

- design a D21-aligned simplified REENTRY contract;
- replace or condition the absolute score threshold with relative qualification;
- consume source-level `NO_EVENT` as CA PASS where temporally valid;
- route technical trend/momentum evidence to PC recovery fields;
- define liquidity/capacity evidence requirement separately from CA/score;
- include previous EXIT reason awareness without using PnL as a Strategy gate;
- produce focused tests only after design approval.

Do not run fresh historical validation before this design repair unless the goal is only to measure the current overconstrained baseline.

## Primary Judgment

`PHASE29_L21Q_REENTRY_POLICY_REQUIRED_BUT_CURRENT_CONTRACT_OVERCONSTRAINED_SIMPLIFICATION_DESIGN_REQUIRED`

Required final answers:

1. Why REENTRY recovery policy exists: to prevent same-symbol closed-campaign BUY_NEW churn after EXIT, especially short-delay repeat losses and contradictory EXIT/re-entry cycles confirmed in D20/D21.
2. Past Re-entry problem evidence: D20 found 93 re-entry campaigns, 68 within 1BD, re-entry PnL `-105,800`, `loss -> <=5BD re-entry -> loss` PnL `-181,240`, and no active runtime re-entry guard.
3. Current `0.10` threshold basis: L15 candidate range lower bound `0.10..0.20`, adopted in L16.
4. Is `0.10` aligned with `runtime_opportunity_score` semantics: only partially. Field authority is aligned, but absolute-threshold semantics are not justified for uncalibrated relative/model score.
5. Is absolute `0.10` necessary: not proven.
6. How much stricter than BUY_NEW: REENTRY adds prior EXIT, cooldown, absolute score, rank, BQ action, CA status, liquidity capacity, and trend/momentum recovery gates.
7. Are 116 expected-edge rejects truly economically weak: NO. They are below the special raw-score threshold; normal BUY_NEW positive allocations include 42 rows below `0.10`.
8. Is there reason to require CA status for all REENTRY: weak / overbroad. Require current blocking CA detection, but all-REENTRY row-level CA status is not justified.
9. Are 193 missing actual CA risk: NO. They are `EXPLICIT_NO_EVENT_NOT_PROPAGATED`.
10. Can CA gate be conditionalized: YES.
11. Does current policy use previous EXIT reason: NO.
12. Minimum churn protection: prior EXIT awareness, cooldown/state-change, current Opportunity/BQ requalification, trend/momentum recovery, previous EXIT reason resolution, no current blocking CA.
13. Is current policy overconstrained: YES.
14. Can policy be simplified: YES, design-first.
15. Regression confirmed: NO.
16. Production repair needed: YES, but not threshold loosening alone; design and source wiring repair first.
17. Next task implementation target: L21R design for simplified REENTRY contract and source evidence wiring.
18. Repair before fresh-run: YES if the fresh-run is intended to validate improved capital deployment; NO if intentionally measuring the current baseline.
