# Phase32-GB — History-Neutral Fresh Target Portfolio Authority Architecture / Regression Invariant Design Audit

## Scope

This is a READ-ONLY / DESIGN-ONLY architecture audit.

- Starting evidence: Phase32-GA long-vs-fresh actual BUY divergence.
- Core problem: same Current Opportunity universe, materially different actual portfolio capitalization due to current position / PC relationship / campaign state path dependence.
- Production implementation: NOT AUTHORIZED.
- SHADOW implementation: NOT EXECUTED.
- Source/config/schema/runtime state mutation: NO.
- fresh-run/resume/replay/recover: NOT EXECUTED.
- Future return / MFE / MAE / final campaign outcome / Historical PnL used for target, threshold, rank, REENTRY window, ADD count, or SELL parameter selection: NO.

## Required References

Read and used:

- `docs/phase_reports/phase32_ga_long_vs_fresh_actual_buy_divergence_root_cause_decomposition_read_only_audit.md`
- `docs/phase_reports/phase32_fz_june_long_vs_fresh_same_day_portfolio_state_target_weight_legacy_divergence_read_only_audit.md`
- `docs/phase_reports/phase32_fx_buy_opportunity_ranking_vs_pm_hold_sell_evidence_semantic_overlap_read_only_audit.md`
- `docs/phase_reports/phase32_fy_late_top50_outside_hold_loss_portfolio_drag_attribution_read_only_audit.md`
- `docs/phase_reports/phase32_fq_capital_priority_architecture_regression_invariant_design_audit.md`
- `docs/phase_reports/phase32_fr_capital_priority_architecture_adversarial_regression_design_acceptance_review.md`
- `docs/phase_reports/phase32_fs_next_capital_unit_shadow_comparator_detailed_spec_preimplementation_design_review.md`
- `docs/phase_reports/phase32_eu_reentry_recent_exit_guard_replacement_architecture_design.md`
- `docs/phase_reports/phase32_ew_reentry_current_decision_semantic_removal_recent_exit_guard_implementation.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- Current source references in `strategy/portfolio_construction.py`, `strategy/position_management.py`, `strategy/marginal_capital_value.py`, and `strategy/shadow_runtime.py`.

## Executive Architecture Judgment

`FRESH_TARGET_PORTFOLIO_ARCHITECTURALLY_FEASIBLE = YES`

The architecture can separate:

```text
Current PIT Opportunity -> Fresh Target Portfolio Investment Authority
Current Actual / Campaign / Ledger -> Delta Execution, Safety, Accounting, Provenance Authority
```

The correct design response to GA is not state deletion. Current positions, campaign ids, average cost, prior ADDs, exits, fills, cash, and ledger state remain essential. The repairable design concern is authority placement:

- current opportunity should decide the desired target portfolio;
- current state should decide the executable delta from actual to target;
- campaign and prior history should preserve safety, churn, accounting, and provenance;
- long-lived historical ownership should not become a generic current investment penalty or bonus.

Direct Production implementation is not ready. A Fresh Target Portfolio SHADOW layer should be designed and implemented first, with zero Production consumers and strict regression invariants.

## Current Authority Map

`CURRENT_AUTHORITY_MAP_COMPLETE = YES`

| Input / state | Current target membership / weight authority | BUY_NEW | BUY_ADD | HOLD | REDUCE | EXIT | Current issue |
|---|---|---|---|---|---|---|---|
| Current PIT Opportunity / rank | PC evidence, BQ/Entry/MCV input | supports | supports ADD evidence indirectly | supports PM | supports PM | supports PM | Shared universe is stable, but not enough to neutralize portfolio state path dependence. |
| Current position membership | PC membership, PM applicability, PS delta | flat symbols only | held symbols only | held only | held only | held only | Becomes a major investment path split rather than only delta/action context. |
| Current quantity / weight | PC baseline, PS delta, cap/headroom | sizing context | sizing/headroom | retain baseline | release delta | full release | Legitimate current exposure, but should not decide "what is attractive today" by itself. |
| Campaign state / id | PM/SI/PC lifecycle, ADD evidence, Runtime lineage | new campaign on BUY | same campaign | same campaign | same campaign | close same campaign | Necessary for lineage; risky when used as investment selection bias. |
| Prior ownership / prior EXIT | bounded recent-exit guard after EW; audit lineage | guard only if recent/material | not applicable to open ADD | audit | audit | audit | Long-lived penalty should remain removed. |
| ADD history | PM/SI ADD-worthiness, campaign-local cap/safety | no | hard/soft ADD eligibility | context | context | context | Should be campaign-local safety, not Fresh Target investment suppression. |
| Average cost / current return | PM risk/no-loss/profit evidence, accounting | no | no-loss averaging | profit/risk context | risk context | risk context | Required for safety/accounting, not Fresh Target selection. |
| Peak return / giveback | PM profit protection / Winner retention | no | context | winner protection | reduce/exit evidence | exit evidence | Must remain separate Winner Protection, not raw Fresh Target membership. |
| PM action | Existing Position Intent Authority | no new symbol selection | ADD intent only | HOLD | REDUCE | EXIT | PM should provide lifecycle/safety intent; PC owns portfolio target. |
| BQ / Entry | Current opportunity admission and quality | yes | yes with held-specific interpretation | supporting | supporting | supporting | Should feed common target evidence while preserving action-specific hard blocks. |
| MCV / NCU | comparable capital evidence | priority evidence | priority evidence | diagnostic | diagnostic | diagnostic | FQ/FR/FS should be subsumed as the comparator inside Fresh Target SHADOW. |
| Cash / risk / regime | Portfolio Policy / PC cash competitor | budget context | budget context | exposure context | exposure context | exposure context | Cash must remain a real target option, not residual-only and not forced full deployment. |
| Runtime / Pending / Ledger | execution, safety, idempotency, accounting | execute only | execute only | no order | execute sell | execute sell | Must never re-optimize target or infer strategy. |

## State Purpose Classification

`STATE_PURPOSE_CLASSIFICATION_COMPLETE = YES`

| State | Purpose class |
|---|---|
| Current PIT opportunity rank/score | A. INVESTMENT_SELECTION |
| BQ / Entry / continuation / downside | A. INVESTMENT_SELECTION, C. SAFETY where hard facts exist |
| Market regime / risk pacing | A. INVESTMENT_SELECTION context, C. SAFETY/RISK context |
| Current equity / deployable capital / current cash | B. CURRENT_EXPOSURE, F. ACCOUNTING, E. EXECUTION |
| Current quantity / current weight | B. CURRENT_EXPOSURE, E. EXECUTION, F. ACCOUNTING, C. SAFETY |
| Current position membership | B. CURRENT_EXPOSURE, E. EXECUTION, F. ACCOUNTING; should be RESTRICTED for A |
| Average cost / current return | C. SAFETY, F. ACCOUNTING, G. PROVENANCE/AUDIT; REMOVE from A |
| Campaign id | E. EXECUTION, F. ACCOUNTING, G. PROVENANCE/AUDIT; C for open-campaign safety |
| Campaign age | C. SAFETY / lifecycle, G. AUDIT; RESTRICT from A |
| Prior BUY/ADD/REDUCE/EXIT counts | C. SAFETY when campaign-local and bounded; G. AUDIT; REMOVE long-lived security-level A |
| Prior ownership | G. AUDIT; D only if bounded recent-exit guard source |
| Prior EXIT reason/date | D. CHURN_PROTECTION while recent/material; G. AUDIT permanently |
| Realized PnL | F. ACCOUNTING, G. AUDIT; not A |
| Unrealized PnL / MFE / giveback | C. risk/profit protection, G. AUDIT; not raw A |
| Pending/order/fill state | E. EXECUTION, F. ACCOUNTING, G. AUDIT |
| Broker / CA / safety facts | C. SAFETY, E. EXECUTION |
| Shadow diagnostic rows | H. OBSERVABILITY_ONLY |

## Fresh Target Portfolio Authority

Fresh Target Portfolio asks:

```text
If the portfolio were formed today from current deployable capital,
using only decision-time PIT evidence and current risk/cash authority,
what symbols and weights would be desired?
```

Design contract:

```text
Current PIT candidate/opportunity/BQ/Entry/SI evidence
  -> hard eligibility facts and safety blocks
  -> Fresh Target Portfolio membership and target weights
  -> current actual comparison
  -> delta action derivation
  -> PS/Runtime/Pending execution
```

Fresh Target must not consume old ownership, old campaign PnL, prior ADD count, old EXIT count, average cost, or campaign age as direct investment selection authority. Those states may remain visible as safety/accounting/provenance and may constrain execution or churn where explicitly bounded.

## Allowed Current-State Inputs

History-neutral does not mean state-blind. These current-state inputs are allowed:

| Input | Allowed in Fresh Target? | Justification |
|---|---|---|
| Current equity | KEEP | Defines portfolio denominator and capital scale; not historical bias. |
| Deployable cash / buying power | KEEP | Cash conservation and feasible allocation. |
| Current market/regime/risk | KEEP | Current PIT investment context. |
| Current safety/broker/CA facts | KEEP | Hard eligibility and fail-closed contract. |
| Current position weight | RESTRICT | Needed for concentration/headroom and later delta; not raw membership preference. |
| Current quantity | RESTRICT | Needed for action delta and lot feasibility; not selection. |
| Current open campaign id | RESTRICT | Needed for ADD/REDUCE/EXIT lineage and safety; not target preference. |
| Pending/order state | RESTRICT | Idempotency and no duplicate side effects; not investment preference. |

## Historical State Exclusion Matrix

| State | Fresh Target Investment Authority |
|---|---|
| current quantity | RESTRICT |
| current position membership | RESTRICT |
| average cost | REMOVE |
| holding days | RESTRICT |
| campaign ID | RESTRICT |
| campaign age | RESTRICT |
| prior BUY count | REMOVE unless current open-campaign safety bookkeeping |
| prior ADD count | RESTRICT to current open-campaign safety / headroom |
| prior EXIT count | REMOVE except bounded recent-exit guard |
| prior REDUCE | RESTRICT to current open-campaign deterioration/safety episode |
| prior ownership | REMOVE from investment authority; KEEP as audit lineage |
| realized PnL | REMOVE |
| unrealized PnL | REMOVE from selection; KEEP for risk/accounting |
| peak return | REMOVE from selection; KEEP for Winner Protection |
| giveback | REMOVE from selection; KEEP for Winner Protection / deterioration |
| prior deterioration | RESTRICT to active campaign-local episode |
| prior recovery | RESTRICT to active campaign-local episode |
| REENTRY history | REMOVE from current investment authority; bounded recent-exit guard only |

Required answers:

- `CURRENT_POSITION_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `CURRENT_POSITION_AS_DELTA_EXECUTION_AUTHORITY_KEEP = YES`
- `CAMPAIGN_HISTORY_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `CAMPAIGN_HISTORY_AS_PROVENANCE_AUTHORITY_KEEP = YES`
- `PRIOR_EXIT_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `RECENT_EXIT_AS_CHURN_AUTHORITY_KEEP = YES`
- `PRIOR_ADD_COUNT_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `PRIOR_ADD_COUNT_AS_SAFETY_AUTHORITY_KEEP = YES, but campaign-local and bounded`
- `AVERAGE_COST_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `AVERAGE_COST_AS_RISK_ACCOUNTING_AUTHORITY_KEEP = YES`

## Current Position Role and Unified Action Derivation

Current position should move from:

```text
already held -> separate investment universe
```

to:

```text
fresh target - current actual -> action delta
```

Canonical semantic:

```text
target_weight > current_weight -> acquire capital
target_weight ~= current_weight -> retain
target_weight < current_weight -> release capital
target_weight = 0 and current_weight > 0 -> exit candidate
target_weight = 0 and current_weight = 0 -> no action
```

No new fixed threshold is selected in GB. Approximate equality must be delegated to existing precision/lot/materiality contracts. Position Sizing remains quantity owner; Runtime remains pure mapper.

Required answers:

- `BUY_NEW_ADD_COMMON_TARGET_SEMANTIC_FEASIBLE = YES`
- `HOLD_REDUCE_EXIT_TARGET_DELTA_SEMANTIC_FEASIBLE = YES`

Boundary:

- BUY_NEW and BUY_ADD can share Fresh Target membership/weight semantics.
- BUY_ADD remains subject to extra current-open-campaign safety: concentration, headroom, no-loss averaging, liquidity, current campaign id, G129 order-increment scope, and lot feasibility.
- REDUCE/EXIT from target delta must remain distinguishable from PM thesis breakdown EXIT, safety full-close, and profit protection REDUCE/EXIT.

## REENTRY / Recent Exit Exception

`REENTRY_BOUNDED_EXCEPTION_FEASIBLE = YES`

EW already establishes:

```text
PRIOR OWNERSHIP IS AUDIT LINEAGE, NOT PERMANENT CURRENT BUY AUTHORITY
RECENT EXIT CHURN PROTECTION MUST BE BOUNDED
```

GB preserves that:

- old prior ownership is not Fresh Target investment authority;
- a recent full EXIT may activate a bounded churn guard;
- the guard may require current PIT re-strength confirmation;
- after expiry/requalification, the symbol returns to ordinary current BUY_NEW evaluation;
- no Historical outcome or old campaign PnL may determine the guard.

## ADD History and Average Cost Authority

Prior ADD count:

- KEEP as current open-campaign safety and bookkeeping.
- RESTRICT from Fresh Target investment selection.
- It can block incremental ADD only when the current open-campaign safety/headroom/no-loss contract says so.
- It must not reduce the symbol's current opportunity score or target membership merely because prior ADDs occurred.

Average cost / current return:

- REMOVE from Fresh Target selection.
- KEEP for no-loss averaging, embedded-risk review, profit protection, accounting, and audit.
- Do not use average cost to decide whether the symbol is attractive today.
- Do use it to prevent unsafe averaging-down or to evaluate current campaign risk.

## Profit Retention and Winner Retention

`PROFIT_RETENTION_SEPARATE_AUTHORITY_REQUIRED = YES`

Fresh Target must not mechanically destroy winners due to daily rank noise. Profit retention / peak / giveback belongs in a separate Winner Protection authority:

```text
Fresh Target says what current PIT opportunity would like to own.
Winner Protection says whether an existing strong campaign should be protected from churn, noise, or premature target collapse.
Safety says what cannot be executed.
```

`WINNER_RETENTION_INVARIANT_DEFINED = YES`

Invariant:

```text
strong Winner remains HOLD while current continuation / Expected Edge / risk evidence remains adequate,
even if daily rank, Top50 boundary, or transient target weight fluctuates.
```

This invariant forbids:

- daily rank-noise forced EXIT;
- transient target shrink causing blind churn;
- automatic rotation out of winners without current deterioration or superior Fresh Target plus valid release semantics;
- replacing PM profit protection with raw target delta.

## SELL / Rotation Semantic

Fresh Target can support a broader release-capital semantic:

```text
actual_weight > fresh_target_weight -> capital release candidate
```

But it must preserve distinct SELL causes:

| SELL semantic | Owner | Meaning |
|---|---|---|
| Thesis breakdown EXIT | PM / Safety | Current campaign no longer valid. |
| Opportunity rotation REDUCE | PC + PM evidence | Better current opportunity/cash target justifies partial capital release. |
| Profit protection REDUCE/EXIT | PM Winner Protection | Embedded gain/giveback/risk evidence requires protection. |
| Safety full close | Safety / CA / Broker | Hard constraint. |

GB does not redesign SELL thresholds or action rules.

## Cash Semantic

`CASH_OPTIONALITY_PRESERVED = YES`

Cash remains a first-class valid target:

- no forced exposure maximization;
- no fixed BUY count;
- no fixed target exposure chosen from Historical return;
- Cash can win when current PIT opportunity evidence is insufficient or risk/cash authority supports deferral;
- Cash cannot become a blanket default winner that suppresses strong valid opportunities.

## FQ/FR/FS Relationship

`FQ_FS_RELATIONSHIP_TO_FRESH_TARGET_ARCHITECTURE = SUBSUME_AND_EXTEND`

The Next-Capital-Unit SHADOW comparator is not replaced. It becomes the per-option comparison engine inside Fresh Target Portfolio SHADOW:

```text
FQ/FR/FS NCU comparator
  -> evidence grouping and non-authority comparison
  -> Fresh Target Portfolio SHADOW
  -> target membership/weight diagnostic
  -> Production-vs-shadow divergence explanation
```

NCU remains:

- non-authoritative;
- `authoritative_consumer_count=0`;
- no order, quantity, action, or Pending authority;
- no hidden single score;
- no hard rank gate;
- no ADD label bonus;
- no Cash default winner.

## PC Responsibility Redesign

Minimum blast-radius option:

- Keep current PC Production target authority unchanged.
- Add Fresh Target Portfolio SHADOW next to PC/MCV.
- Emit diagnostic fields without changing `target_weight`, `accepted_buy_new_weight`, `accepted_incremental_weight`, PS, Runtime, Pending, or Ledger.
- Use NCU comparator as evidence grouping.

Clean architecture option:

- Split PC into two explicit sub-authorities:
  - `FreshTargetFormationAuthority`: current opportunity / risk / cash / safety hard eligibility.
  - `DeltaActionBridgeAuthority`: current actual, campaign id, PM lifecycle, PS delta, Runtime execution lineage.
- Later Production promotion can replace current relationship-driven target formation only after shadow acceptance.

GB recommendation: implement the minimum SHADOW version first, design the clean split as target architecture.

## PM Responsibility Redesign

PM should remain:

- Existing Position Intent Authority;
- lifecycle evidence provider;
- Winner Protection / deterioration / ADD intent authority;
- safety-context provider for current open campaigns.

PM should not become:

- BUY_NEW universe owner;
- Fresh Target Portfolio optimizer;
- cross-symbol capital allocator;
- Runtime/order/quantity owner.

PM outputs should be consumed as typed evidence by Fresh Target / Delta Bridge, not as a second portfolio optimizer.

## Campaign and Current Position Preservation

Campaign identity is preserved:

- campaign ids remain canonical lineage, accounting, execution, attribution, and provenance authority;
- ADD/REDUCE/EXIT keep current campaign id;
- new flat BUY after full EXIT starts a new campaign;
- prior campaign id remains audit lineage;
- closed campaign state must not leak into new campaign investment selection.

Current position is preserved:

- it is the source of actual exposure and delta;
- it is required for cash/equity/current weight/quantity;
- it is not a reason by itself to privilege or penalize the security's current opportunity.

## Safety Invariants

Fresh Target architecture must preserve:

- cash conservation;
- no overspend;
- max exposure and hard cash/buying-power constraints;
- hard max position/concentration;
- no-loss averaging for ADD;
- liquidity and lot-aware execution;
- price/minimum tick authority;
- corporate action and broker eligibility fail-closed;
- no negative quantity;
- duplicate/idempotency guards;
- Broker/Ledger SoT;
- Pending authority;
- Historical/Demo/Production common runtime contract;
- accepted artifact / registry / source authority validation.

Safety remains a block/review authority, not a portfolio optimizer.

## Philosophy Invariants

Preserved:

- current PIT only;
- no future information;
- momentum-oriented swing investment;
- Winner retention;
- rapid response to genuine deterioration;
- Cash optionality;
- BUY/SELL action independence where semantically required;
- no permanent REENTRY ban;
- no fixed profit-taking percent;
- no fixed stop-loss percent derived from Historical;
- no fixed holding-day rule;
- no fixed BUY count;
- no exposure maximization mandate.

## Golden Cases

`GOLDEN_CASES_DEFINED = YES`

| Case | Invariant |
|---|---|
| Fresh strong BUY_NEW | Strong current PIT opportunity remains eligible and fast-deployable. |
| Existing strong Winner HOLD | Winner is not sold due to rank noise or transient target drift. |
| Existing strong Winner ADD | ADD can be represented when PM ADD, no-loss, headroom, cap, liquidity, and G129 pass. |
| Temporary rank/dropout noise but thesis intact | No forced churn from transient displacement. |
| Genuine deterioration EXIT | PM/Safety full-close authority remains immediate. |
| Partial conviction decline REDUCE | REDUCE remains distinct from EXIT and HOLD. |
| Recent EXIT without re-strength | bounded churn guard can block/review. |
| Recent EXIT with clear re-strength | guard can release to ordinary BUY_NEW. |
| No sufficient opportunity | Cash can be the valid target. |
| High-price / lot constrained candidate | PS/PC feasibility remains hard. |
| Concentration hard-cap protection | cap/headroom cannot be bypassed by Fresh Target. |

## Problem Cases

`PROBLEM_CASES_DEFINED = YES`

| Case | Fresh Target diagnostic question |
|---|---|
| GA same-rank different capitalization | Would Fresh Target produce aligned desired holdings before current-state delta? |
| 67310 repeated BUY_NEW/EXIT | Does current PIT target remain independent from old cycles while churn guard stays bounded? |
| Incumbent NEW-vs-ADD asymmetry | Does the same security evidence receive comparable investment treatment before ADD safety? |
| Prior ADD history suppression | Is prior ADD count acting only as campaign-local safety, not target suppression? |
| Old campaign context overriding current opportunity | Is closed campaign state kept out of Fresh Target selection? |
| Top50-OUT + deterioration + stronger alternatives | Can target delta express valid rotation without simplistic dropout SELL? |
| Current target shrink but capital retained | Is Winner Protection or delta materiality explicitly explaining retention? |
| Capital scale expanding into marginal opportunities | Does Cash remain a valid target instead of forced marginal deployment? |

## Adversarial Risks

`ADVERSARIAL_RISKS_DEFINED = YES`

| Risk | Guard |
|---|---|
| Daily churn explosion | Winner retention, target stability/materiality, lot/turnover diagnostics before Production. |
| Winner premature exit | separate Winner Protection authority; PM deterioration still required. |
| REDUCE/BUY cycling | bounded recent-exit guard and delta materiality; no blind target-chasing. |
| Ignoring meaningful campaign risk | campaign-local safety remains hard evidence. |
| Loss averaging | no-loss averaging remains hard ADD safety. |
| Concentration increase | cap/headroom/liquidity stay hard. |
| Target instability | SHADOW must emit stability/churn diagnostics before Production. |
| Rank noise sensitivity | rank is supporting, not fixed gate. |
| Excessive transaction costs | no Production promotion without turnover/churn acceptance. |
| REENTRY churn | bounded guard remains. |
| Safety weakened | hard eligibility before target and before delta. |
| Campaign/provenance breakage | campaign id remains canonical lineage and delta bridge input. |

## No-Regression Contract

`NO_REGRESSION_CONTRACT_DEFINED = YES`

Zero-tolerance before Production consideration:

- Candidate AI outputs unchanged unless explicitly redesigned.
- PIT contract unchanged.
- Winner retention preserved.
- Safety gates preserved.
- no permanent history penalty.
- no uncontrolled churn.
- no provenance loss.
- no runtime correctness regression.
- no forced full-investment behavior.
- no G129 regression.
- no REENTRY semantic revival.
- no Cash blanket dominance.
- no ADD label bonus.
- no hard rank cutoff.
- no SHADOW authority leak.
- no stale/cross-run evidence accepted.
- no future/outcome-derived parameter.

## Fresh Target Portfolio SHADOW Architecture

`SHADOW_FRESH_TARGET_ARCHITECTURE_DEFINED = YES`

Minimum artifact:

```text
schema_version
run_id
business_date
feature_date
producer
source_artifact_paths/hashes
pit_status
authoritative_consumer_count = 0
future_information_used = false
historical_outcome_used = false

rows:
  symbol
  option_type                         # BUY_NEW / BUY_ADD / CURRENT_HOLDING / CASH
  current_opportunity_evidence
  hard_eligibility_status
  hard_eligibility_reason_codes
  fresh_target_membership
  fresh_target_weight
  fresh_target_weight_reason_codes
  current_actual_weight
  delta_weight
  proposed_semantic_delta             # diagnostic only
  history_safety_adjustment
  winner_protection_adjustment
  recent_exit_guard_state
  final_shadow_action                 # diagnostic only
  current_production_action
  current_production_target_weight
  current_production_quantity
  divergence_class
  divergence_reason_codes
  action_authority = false
  quantity_authority = false
  order_authority = false
```

GA reproduction metrics supported:

- current opportunity -> target path dependence;
- long/fresh shadow target overlap;
- current Production vs shadow divergence;
- campaign/history suppression share;
- incumbent-vs-flat asymmetry;
- cash optionality preservation.

## Architecture Options

| Option | Description | Blast radius | Correctness risk | Philosophy fit | Complexity | Regression risk | Judgment |
|---|---|---:|---:|---:|---:|---:|---|
| A | Minimal PC history-authority restriction | LOW-MEDIUM | MEDIUM | PARTIAL | MEDIUM | MEDIUM | Too narrow; may miss target-vs-delta separation. |
| B | Fresh Target Portfolio SHADOW layer + existing PC execution bridge | MEDIUM | LOW-MEDIUM in SHADOW | HIGH | MEDIUM-HIGH | MEDIUM | Recommended next architecture. |
| C | Full current-opportunity-to-capital Production architecture unifying NEW/ADD/HOLD/REDUCE/EXIT | HIGH | HIGH | HIGH if done well | HIGH | HIGH | Long-term target only; not ready. |

`RECOMMENDED_ARCHITECTURE_OPTION = B`

Rationale:

- It directly addresses GA's path dependence.
- It subsumes FQ/FR/FS rather than duplicating them.
- It preserves current Production behavior while evidence accumulates.
- It gives a clean migration path to Option C later.
- It avoids premature Strategy/SELL/PM/Runtime blast radius.

## Implementation Surface Forecast

`IMPLEMENTATION_BLAST_RADIUS = MEDIUM_FOR_SHADOW_HIGH_FOR_PRODUCTION`

Likely future SHADOW implementation touch points:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- potentially `src/ai_fund_lab_v2/strategy/strategy_intelligence.py` only as evidence consumer/source, not authority redesign
- tests under `tests/strategy/`
- architecture docs:
  - `docs/02_architecture/strategy_architecture_v1.md`
  - `docs/02_architecture/strategy_intelligence_architecture_v1.md`
  - possibly `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- future phase reports and acceptance fixtures

Avoid touching for SHADOW:

- Candidate / Opportunity producer;
- BQ producer;
- PM action semantics;
- Position Sizing authority;
- Runtime Planning / Pending / Ledger;
- Submit / Execution;
- Safety hard gates;
- accepted registry/hash validation.

## Stop Conditions

Implementation must not start or must stop if:

- Fresh Target loses current risk/cash authority.
- Winner retention cannot be explained.
- bounded recent-exit authority is ambiguous.
- current position delta action is ambiguous.
- PC/PM authority overlap remains unresolved.
- campaign provenance would break.
- Safety gates weaken.
- FQ/FS NCU responsibilities conflict with Fresh Target responsibilities.
- SHADOW artifact would have Production consumer authority.
- historical outcome would be needed to choose any threshold.

## Required Answer Summary

- `CURRENT_AUTHORITY_MAP_COMPLETE = YES`
- `STATE_PURPOSE_CLASSIFICATION_COMPLETE = YES`
- `FRESH_TARGET_PORTFOLIO_ARCHITECTURALLY_FEASIBLE = YES`
- `CURRENT_POSITION_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `CURRENT_POSITION_AS_DELTA_EXECUTION_AUTHORITY_KEEP = YES`
- `CAMPAIGN_HISTORY_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `CAMPAIGN_HISTORY_AS_PROVENANCE_AUTHORITY_KEEP = YES`
- `PRIOR_EXIT_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `RECENT_EXIT_AS_CHURN_AUTHORITY_KEEP = YES`
- `PRIOR_ADD_COUNT_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `PRIOR_ADD_COUNT_AS_SAFETY_AUTHORITY_KEEP = YES_CAMPAIGN_LOCAL_BOUNDED`
- `AVERAGE_COST_AS_INVESTMENT_AUTHORITY_KEEP = NO`
- `AVERAGE_COST_AS_RISK_ACCOUNTING_AUTHORITY_KEEP = YES`
- `PROFIT_RETENTION_SEPARATE_AUTHORITY_REQUIRED = YES`
- `BUY_NEW_ADD_COMMON_TARGET_SEMANTIC_FEASIBLE = YES`
- `HOLD_REDUCE_EXIT_TARGET_DELTA_SEMANTIC_FEASIBLE = YES`
- `REENTRY_BOUNDED_EXCEPTION_FEASIBLE = YES`
- `WINNER_RETENTION_INVARIANT_DEFINED = YES`
- `CASH_OPTIONALITY_PRESERVED = YES`
- `FQ_FS_RELATIONSHIP_TO_FRESH_TARGET_ARCHITECTURE = SUBSUME_AND_EXTEND`
- `GOLDEN_CASES_DEFINED = YES`
- `PROBLEM_CASES_DEFINED = YES`
- `ADVERSARIAL_RISKS_DEFINED = YES`
- `NO_REGRESSION_CONTRACT_DEFINED = YES`
- `SHADOW_FRESH_TARGET_ARCHITECTURE_DEFINED = YES`
- `RECOMMENDED_ARCHITECTURE_OPTION = B`
- `IMPLEMENTATION_BLAST_RADIUS = MEDIUM_FOR_SHADOW_HIGH_FOR_PRODUCTION`
- `DIRECT_PRODUCTION_IMPLEMENTATION_READY = NO`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `NEXT_STEP = implement Fresh Target Portfolio SHADOW non-authoritative artifact and GA reproduction metrics`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Final Judgment

`PHASE32_GB_HISTORY_NEUTRAL_FRESH_TARGET_PORTFOLIO_ARCHITECTURE_DEFINED_OPTION_B_SHADOW_FIRST_DIRECT_PRODUCTION_NOT_READY`
