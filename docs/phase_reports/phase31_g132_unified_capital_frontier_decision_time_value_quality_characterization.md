# Phase31-G132 — Unified Capital Frontier Decision-Time Value Quality Characterization

## Final Decision

`G132_UNIFIED_FRONTIER_VALUE_QUALITY_PARTIAL_EVIDENCE_FOLLOWUP_REQUIRED`

## Scope

Task type: READ-ONLY characterization audit.

Primary run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Primary diagnostic window:

`2022-11-21` through `2022-12-12`

Earlier completed dates were used only to reconstruct campaign state and prior ADD history. No later return, next-day return, final campaign PnL, future rank, MFE/MAE, Paper Ledger outcome, or Historical performance was used to judge production decision quality.

No code, config, threshold, weight, model, fresh-run, resume, replay, long Historical, or run mutation was performed.

## Source Basis

Required reports read:

- `docs/phase_reports/phase31_g131_unified_add_new_cash_marginal_capital_authority_design_acceptance.md`
- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase31_g115_add_marginal_competition_staged_authoritative_binding.md`
- `docs/phase_reports/phase31_g114_add_marginal_competition_authoritative_binding_design_review.md`
- `docs/phase_reports/phase31_g113_add_marginal_capital_competition_shadow_implementation.md`
- `docs/phase_reports/phase31_g112_repeated_add_marginal_capital_competition_contract_audit.md`
- relevant G120 / G126 characterization reports

Architecture SoT read:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

G131 remains authoritative:

- Cash = first-class alternative.
- ADD and NEW_BUY = peer capital competitors.
- Unified frontier = required.
- Multi-allocation / shoulder participation = permitted.
- Strict single-winner = not required.

## Executive Judgment

UNIFIED_FRONTIER_VALUE_EVIDENCE_IS_DECISION_USEFUL = `PARTIAL`

The current frontier evidence is useful enough to distinguish broad categories:

- executable vs terminal / fail-closed;
- selected vs rejected;
- ADD vs best NEW_BUY score pass/fail;
- Cash-preferred reduced participation vs deployment-eligible participation;
- lot/cap feasible vs infeasible;
- PM ADD vs HOLD/REDUCE/EXIT.

But it is only partially useful for fine-grained scarce-capital ordering. The artifacts are rich, yet many heterogeneous competitors collapse into the same final states. In the focus window, 349 competitors collapsed into only 3 effective final states, and the largest group was `FAIL_CLOSED` with 289 rows. Among selected securities, many materially different opportunities share `COMPARABLE_MARGINAL` / shoulder participation semantics.

The largest remaining value-quality gap is not wiring. It is semantic resolution:

`incremental_investment_value` and `opportunity_cost` are PIT-safe and consumed, but they do not fully express "expected value of this exact next executable lot versus every current alternative including Cash." They are closer to campaign / opportunity / continuation quality plus ADD-vs-best-NEW proxy evidence, then PC applies G115 staged shoulder participation.

## Frontier Reconstruction

Focus dates audited:

`2022-11-21, 2022-11-22, 2022-11-24, 2022-11-25, 2022-11-28, 2022-11-29, 2022-11-30, 2022-12-01, 2022-12-02, 2022-12-05, 2022-12-06, 2022-12-07, 2022-12-08, 2022-12-09, 2022-12-12`

Frontier population:

| Metric | Count |
| --- | ---: |
| FRONTIER_COMPETITOR_COUNT | 349 |
| NEW_BUY competitors | 336 |
| ADD competitors | 13 |
| selected NEW_BUY rows | 25 |
| selected ADD rows | 6 |
| canonical ADD authority rows authorized | 6 |

Opportunity quality distribution:

| Quality class | Count |
| --- | ---: |
| COMPARABLE_MARGINAL | 304 |
| COMPARABLE_HIGH | 27 |
| STRONG | 12 |
| BLOCKED | 5 |
| INSUFFICIENT | 1 |

Market-Candidate-Cash interaction distribution:

| Interaction | Count |
| --- | ---: |
| FAIL_CLOSED | 289 |
| BLOCKED | 29 |
| CASH_PREFERRED | 17 |
| DEPLOY_ELIGIBLE | 7 |
| SELECTIVE_COMPETITION | 7 |

Final effective state compression:

| Final effective state | Count |
| --- | ---: |
| FAIL_CLOSED | 289 |
| SELECTED | 31 |
| BLOCKED | 29 |

DISTINCT_FINAL_PRIORITY_STATES = `3`

LARGEST_IDENTICAL_PRIORITY_GROUP = `FAIL_CLOSED / 289`

FRONTIER_VALUE_COMPRESSION_PRESENT = `YES`

Compression occurs mainly at:

1. coarse opportunity quality classes, especially `COMPARABLE_MARGINAL`;
2. Market-Candidate-Cash interaction collapsing many heterogeneous rows to `FAIL_CLOSED` / `CASH_PREFERRED`;
3. G115 `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED`, which permits one increment but does not rank many comparable increments with high resolution.

## Evidence Lineage

VALUE_EVIDENCE_LINEAGE_COMPLETE = `PARTIAL`

| Evidence | Producer | Artifact | Field | PIT validity | Consumer | Decision effect | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Candidate score / rank | BUY AI / opportunity authority | `.runtime/runtime_state/buy_ai/<date>/opportunity_rankings.json`; referenced in PC/PS artifacts | `runtime_opportunity_score`, `buy_rank` | PIT-valid same-date | PC, PS, Runtime lineage | differentiates NEW and ADD opportunity-cost comparison | ACTIVE_DIFFERENTIATOR |
| Entry Quality | BUY Quality / Entry Admission | `strategy/buy_quality_decisions.json`, embedded PC rows | `quality_action`, `entry_state`, `quality_score` | PIT-valid same-date | PC / opportunity quality | quality context and allocation bias | ACTIVE_DIFFERENTIATOR |
| PM ADD action | Position Management | `strategy/position_management.json` | `action = ADD`, reason codes | PIT-valid same-date | PC ADD competitor | ADD admission / intent | GATE_ONLY plus ACTIVE_DIFFERENTIATOR |
| ADD incremental investment value | ADD evidence bridge | embedded in `strategy/portfolio_construction.json` | `incremental_investment_value.state/status` | PIT-valid same-date | G115 ADD authority | ADD eligibility / PASS | ACTIVE_BUT_NON_DIFFERENTIATING |
| ADD opportunity cost | ADD evidence bridge / PC | embedded in PC ADD competitor / G115 row | `best_new_buy_score`, `candidate_score`, `comparison_result` | PIT-valid same-date | G115 ADD authority | ADD-vs-NEW PASS | ACTIVE_DIFFERENTIATOR |
| Market Quality | Market Context | `strategy/market_context.json` | market quality state | PIT-valid same-date | Portfolio Policy / PC | pacing context | ACTIVE_DIFFERENTIATOR at budget/interaction level |
| Risk Pacing | Portfolio Policy | `strategy/portfolio_policy.json`, embedded PC risk pacing evidence | risk pacing intent / budget envelope | PIT-valid same-date | PC | budget and deployment intensity | ACTIVE_BUT_NON_DIFFERENTIATING for security ordering |
| Market-Candidate-Cash | PC | `strategy/portfolio_construction.json` | `interaction_result` | PIT-valid same-date | PC final allocation | security/Cash partition | ACTIVE_DIFFERENTIATOR |
| Lot / cap feasibility | PC / PS | `strategy/portfolio_construction.json`, `strategy/position_sizing.json` | lot state, cap/headroom, quantity | PIT-valid same-date | PS / Runtime | executable quantity | GATE_ONLY plus ACTIVE_DIFFERENTIATOR |
| Runtime semantic | Runtime Planning | `strategy/runtime_planning.json` | `planning_intent` | same-date consumer evidence | Pending / Submit | order semantic | OBSERVABILITY_ONLY for value ranking |

Lineage is strong for observability and broad gating. It is partial for true fine-grained value ranking because several active fields collapse to PASS/class labels rather than preserving an ordered marginal value scale.

## Cross-Sectional Differentiation

ADD_NEW_VALUE_DIFFERENTIATION = `MODERATE`

Reason:

ADD rows contain explicit `opportunity_cost` comparing ADD candidate score against best NEW_BUY score. In the focus-window filled ADD rows, candidate scores exceeded best NEW_BUY scores. NEW_BUY frontiers were present and selected NEW_BUYs coexisted with ADD. However, the cross-type comparison primarily uses opportunity score semantics, while ADD also has campaign/continuation evidence; the evidence richness is asymmetric.

NEW_NEW_VALUE_DIFFERENTIATION = `MODERATE`

Reason:

NEW_BUY rows preserve rank, score, quality class, entry admission, Market-Candidate-Cash state, and lot feasibility. Strong / COMPARABLE_HIGH / COMPARABLE_MARGINAL distinctions exist, and selected NEW_BUYs include STRONG and COMPARABLE_HIGH rows. But many NEW_BUYs still compress into `COMPARABLE_MARGINAL` or `FAIL_CLOSED`, so fine ordering resolution is limited.

ADD_ADD_VALUE_DIFFERENTIATION = `WEAK`

Reason:

Same-date ADD-vs-ADD frontier exists, and `2022-10-12` ordered 94320 before 94340 consistently with candidate score. But in the primary focus window, only 76470 has authorized ADD rows, so cross-sectional ADD-vs-ADD evidence is sparse. Multiple hypothetical increments for the same symbol often carry identical candidate score / opportunity-cost evidence across different post-increment quantities.

SECURITY_CASH_VALUE_DIFFERENTIATION = `MODERATE`

Reason:

Cash is explicit and distinguishes `CASH_PREFERRED`, `DEPLOY_ELIGIBLE`, and `SELECTIVE_COMPETITION`. However, `CASH_PREFERRED_PARTICIPATION_VALID` is intentionally not an ADD-beats-Cash proof, so the evidence separates participation/deferral better than it ranks exact marginal value versus Cash.

## Marginal-Value Semantics

INCREMENTAL_INVESTMENT_VALUE_IS_TRUE_NEXT_LOT_VALUE = `PARTIAL`

Evidence:

- It is PIT-safe and ADD-specific.
- It consumes campaign continuation, expected edge, no-loss averaging, and opportunity cost.
- It changes across business dates for 76470 as candidate score and best NEW_BUY score change.

Limitations:

- On a given date, many hypothetical repeated increments for 76470 carry identical `candidate_score`, `best_new_buy_score`, `incremental_investment_value = POSITIVE/PASS`, and classification even as `pre_increment_quantity` / `post_increment_quantity` changes.
- It does not appear to express per-lot diminishing marginal value after each hypothetical increment except through staged one-increment authorization and headroom/budget context.
- It is materially inherited from same-campaign quality, continuation, expected-edge cascade, and candidate score rather than a fully independent next-lot expected value.

Answer to "WHAT MAKES ADD_1700 DIFFERENT FROM ADD_1600?":

In the artifacts, mostly quantity/weight/headroom state and recomputed same-date authority. The underlying candidate score and opportunity-cost comparison often remain the same for the date. Thus ADD_1700 differs operationally by staged one-lot state, not by a separately measured next-lot alpha signal.

## Opportunity Cost Semantics

OPPORTUNITY_COST_COVERS_FULL_FRONTIER = `PARTIAL`

The embedded `opportunity_cost` object explicitly covers:

```text
ADD candidate score vs best same-date NEW_BUY score
```

It does not itself explicitly encode:

- ADD next lot vs other ADD next lot;
- ADD next lot vs Cash;
- ADD next lot vs residual optionality;
- exact post-prior-ADD marginal decay.

G115/PC frontier evidence surrounds it with ADD-vs-ADD, Cash, residual, and lot/headroom context. Therefore the overall PC authority is broader than the `opportunity_cost` field, but the named opportunity-cost evidence remains partial.

## Deep Anchor: 76470

Verified filled focus-window sequence:

`1200 -> 1300 -> 1400 -> 1500 -> 1600 -> 1700`

| Date | Pre -> Post | Candidate Score | Best NEW Score | Cash / Frontier Reason | Information Quality |
| --- | --- | ---: | ---: | --- | --- |
| 2022-11-29 | 1200 -> 1300 | 0.3189931 | 0.16297291 | `SECURITY_FRONTIER_COMPARABLE_WITH_STRONGER_OR_EQUAL_ALTERNATIVE` | MODERATE_INFORMATION_MARGINAL_DECISION |
| 2022-11-30 | 1300 -> 1400 | 0.34505777 | 0.21260248 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | MODERATE_INFORMATION_MARGINAL_DECISION |
| 2022-12-02 | 1400 -> 1500 | 0.40651062 | 0.25983442 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | MODERATE_INFORMATION_MARGINAL_DECISION |
| 2022-12-06 | 1500 -> 1600 | 0.42251035 | 0.27563508 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | MODERATE_INFORMATION_MARGINAL_DECISION |
| 2022-12-08 | 1600 -> 1700 | 0.41972718 | 0.25153989 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | MODERATE_INFORMATION_MARGINAL_DECISION |

What justifies ADD:

- PM ADD with `no_loss_averaging`, `opportunity_rank_still_high`, `strong_trend_continuation`;
- incremental investment value `POSITIVE / PASS`;
- opportunity cost PASS versus best NEW_BUY;
- lot/cap feasible one executable increment;
- G115 staged one-increment authority.

What changed since previous ADD:

- same-date candidate score and best NEW_BUY score refreshed;
- Market Quality / Risk Pacing moved from normal BULL/healthy expansion into cautious / breadth-breakdown context;
- current quantity / weight / headroom updated.

What remains weak:

- repeated same-date hypothetical increments often reuse the same opportunity-cost values;
- Cash comparison is participation shoulder rather than strict ADD-over-Cash proof;
- the evidence is campaign-continuation-rich but not a high-resolution per-next-lot alpha estimate.

76470_REPEATED_ADD_INFORMATION_QUALITY = `MODERATE`

## Deep Anchor: 94320

Verified Post-G129 ADD sequence:

`200 -> 300 -> 400 -> 500 -> 600 -> 700`

ADD evidence:

| Date | Pre -> Post | Candidate Score | Best NEW Score | Frontier Reason | Fill |
| --- | --- | ---: | ---: | --- | --- |
| 2022-10-12 | 200 -> 300 | 0.4254797 | 0.15602367 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | YES |
| 2022-10-28 | 300 -> 400 | 0.39706695 | 0.09652459 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | YES |
| 2022-11-01 | 400 -> 500 | 0.38607446 | 0.13592963 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | YES |
| 2022-11-04 | 500 -> 600 | 0.40385899 | 0.18448267 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | YES |
| 2022-11-09 | 600 -> 700 | 0.39720057 | 0.25034036 | `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH` | YES |

94320_LATE_ADD_INFORMATION_QUALITY = `MODERATE`

The sequence shows refreshed same-date opportunity-cost evidence and positive incremental investment evidence. But the late increments remain shoulder participation, not explicit Cash dominance, and the semantic distinction between 600->700 and 700->800 is mostly staged one-lot state rather than a separate marginal value measurement.

## Control: 94340

94340 path:

- 2022-10-13: PM ADD, campaign age 10, continuation PASS, G115 row authorized with `CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH`.
- 2022-10-14: PM HOLD, continuation PASS, no ADD authority row.
- 2022-10-17: PM HOLD, continuation PASS, no ADD authority row.
- Later: PM remains HOLD until 2022-12-07 EXIT on `weak_hold_score`.

WHAT_VALUE_EVIDENCE_CHANGED_ENOUGH_TO_STOP_THE_NEXT_INCREMENT =
`PM action changed from ADD to HOLD; PC did not receive an ADD competitor. Continuation remained PASS, so the stop demonstrates PM ADD-vs-HOLD sensitivity, but not necessarily a high-resolution PC marginal capital value change.`

94340_STOP_DEMONSTRATES_MARGINAL_SENSITIVITY = `PARTIAL`

The control disproves unbounded ADD, but the stop is primarily upstream PM action boundary rather than a PC frontier value ranking boundary.

## BUY_NEW Quality Preservation

CROSS_TYPE_VALUE_SCALE_COMPARABLE = `PARTIAL`

Evidence that BUY_NEW can still receive capital:

| Date | ADD selected | NEW_BUY selected |
| --- | --- | --- |
| 2022-11-29 | 76470 | 76920 |
| 2022-11-30 | 76470 | 21200 |
| 2022-12-01 | 76470 | 45910 |
| 2022-12-02 | 76470 | 64880 |
| 2022-12-06 | 76470 | 79010, 54710 |
| 2022-12-08 | 76470 | 37790, 82560, 61440 |

Strong BUY_NEW opportunities retain enough information to receive capital alongside ADD. However, exact cross-type scale comparability is partial because ADD has campaign/continuation/no-loss context while NEW_BUY has entry/rank/quality context. The common bridge is mainly `runtime_opportunity_score` / opportunity-cost comparison plus PC classification, not a unified calibrated expected return.

ADD_NEW_EVIDENCE_RICHNESS_ASYMMETRY = `YES`

ASYMMETRY_IS_INTENTIONAL_AND_COMPARABLE = `PARTIAL`

The asymmetry is intentional because ADD is an existing-position increment and NEW_BUY is a new campaign. It is only partially comparable because there is no fully calibrated common marginal value unit.

## HOLD Interaction Boundary

HOLD_STATUS_CREATES_UNINTENDED_ADD_PRIORITY = `UNPROVEN`

Existing HOLD capital does not directly create ADD priority. PM must emit ADD and PC must receive ADD evidence. The 94340 control shows an existing position can remain HOLD without further ADD despite continuation PASS. However, incumbent positions have richer campaign evidence and can re-enter ADD consideration repeatedly when PM emits ADD, so structural informational advantage is possible but not proven unintended in this window.

## Cash Semantics Quality

CASH_FRONTIER_EVIDENCE_DIFFERENTIATION = `MODERATE`

The system differentiates:

- `DEPLOY_ELIGIBLE`
- `SELECTIVE_COMPETITION`
- `CASH_PREFERRED`
- `FAIL_CLOSED`
- `BLOCKED`
- `CASH_PREFERRED_PARTICIPATION_VALID`
- `CASH_PREFERRED_DEFER`

But many rows collapse into `FAIL_CLOSED` or participation shoulder. Cash evidence is decision-useful for deployment/deferral, but weaker for fine-grained "Cash vs this exact next 100 shares" value comparison.

## Observability vs Discrimination

EVIDENCE_OBSERVABILITY_QUALITY = `HIGH`

Artifacts preserve rich lineage:

- PM action and reasons;
- candidate score/rank;
- entry/quality context;
- ADD investment evidence;
- opportunity-cost comparison;
- Market Quality / Risk Pacing;
- Market-Candidate-Cash interaction;
- lot/cap feasibility;
- PC classification and PS quantity;
- Runtime semantic.

EVIDENCE_CAPITAL_DISCRIMINATION_QUALITY = `MODERATE`

Reason:

The evidence changes real decisions and prevents many rows from receiving capital. However, it compresses many heterogeneous competitors into the same classes, and the ADD next-lot value is not a fully independent marginal value signal.

## Weakness Classification

| Class | Finding |
| --- | --- |
| A existing evidence not consumed | Not primary; major evidence is consumed. |
| B existing evidence consumed but loses resolution | YES, broad compression to COMPARABLE_MARGINAL / FAIL_CLOSED. |
| C cross-type semantic mismatch | PARTIAL, ADD and NEW evidence are asymmetric. |
| D opportunity-cost incomplete | YES/PARTIAL, named field covers ADD-vs-best-NEW but not full Cash/ADD frontier by itself. |
| E incremental value is not truly marginal | PARTIAL, same-date repeated hypothetical increments reuse core score/evidence. |
| F Cash comparison resolution weak | PARTIAL, participation shoulder is informative but not exact Cash dominance. |
| G observability only | NO, evidence changes decisions. |
| H existing architecture fully sufficient | PARTIAL only. |
| I insufficient evidence | NO for the audited artifacts; lineage exists. |

## Required Aggregate Judgments

UNIFIED_FRONTIER_VALUE_EVIDENCE_IS_DECISION_USEFUL = `PARTIAL`

VALUE_EVIDENCE_LINEAGE_COMPLETE = `PARTIAL`

INCREMENTAL_INVESTMENT_VALUE_IS_TRUE_NEXT_LOT_VALUE = `PARTIAL`

OPPORTUNITY_COST_COVERS_FULL_FRONTIER = `PARTIAL`

CROSS_TYPE_VALUE_SCALE_COMPARABLE = `PARTIAL`

FRONTIER_VALUE_COMPRESSION_PRESENT = `YES`

ADD_NEW_EVIDENCE_RICHNESS_ASYMMETRY = `YES`

HOLD_STATUS_CREATES_UNINTENDED_ADD_PRIORITY = `UNPROVEN`

CASH_FRONTIER_EVIDENCE_DIFFERENTIATION = `MODERATE`

EVIDENCE_OBSERVABILITY_QUALITY = `HIGH`

EVIDENCE_CAPITAL_DISCRIMINATION_QUALITY = `MODERATE`

76470_REPEATED_ADD_INFORMATION_QUALITY = `MODERATE`

94320_LATE_ADD_INFORMATION_QUALITY = `MODERATE`

94340_STOP_DEMONSTRATES_MARGINAL_SENSITIVITY = `PARTIAL`

FUTURE_INFORMATION_USED_FOR_VALUE_QUALITY_JUDGMENT = `NO`

## Mandatory Repair Decision

MANDATORY_REPAIR_FOUND = `NO`

No current implementation violation of accepted G131 SoT was proven. The evidence quality is partial, but partial value resolution is not by itself a mandatory repair.

If a future task chooses to improve discrimination, the narrowest design boundary to study is:

```text
PRODUCER = Portfolio Construction / ADD investment evidence bridge and G115 authority
CONSUMER = canonical_add_marginal_capital_competition_authority
MISSING_OR_LOST_SEMANTIC = calibrated or ordinal next-executable-lot marginal value across ADD / NEW_BUY / Cash, without performance fitting
NARROWEST_BOUNDARY = PC-owned value semantics before PS quantity consumption
REQUIRED_INVARIANT = richer discrimination must use existing PIT evidence first, preserve G131 shoulder participation, preserve Cash as first-class, and avoid future/Historical outcome tuning
```

This is a characterization follow-up candidate, not a G132 repair.

## Required Flags

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

THRESHOLD_CHANGED = `NO`

WEIGHT_CHANGED = `NO`

MODEL_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

PHASE_ADVANCED = `NO`
