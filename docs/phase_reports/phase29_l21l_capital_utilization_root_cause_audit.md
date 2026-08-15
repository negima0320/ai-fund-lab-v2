# Phase29-L21L — Capital Utilization Root Cause Audit

Task ID: `Phase29-L21L`  
Target run: `runtime-test-historical-smoke-20260811T152905733571Z`  
Mode: read-only audit. No implementation, configuration, threshold, model, runtime, pending, accepted-generation, resume, abort, or historical-run mutation was performed.

## Executive Summary

The low capital utilization in the target 4-year historical validation run is primarily explained by Portfolio Construction allocation selectivity and lot/concentration feasibility, not by a lack of raw BUY candidates and not by Buy Quality rejection.

The target run averages roughly 50% invested, with a median just above 52% and 64 days below 40% invested. The strongest bottleneck is after Buy Quality: Buy Quality passes most rows, but Portfolio Construction converts only a small subset into positive target weight. Across the run, PC had 548 BUY_NEW/add-candidate members and only 72 positive allocations. At the day level, PC recorded 180 zero-increment days versus 72 positive-increment days; residual cash reasons were led by `CONCENTRATION_LIMIT` on 147 days and `NO_ELIGIBLE_OPPORTUNITY` on 71 days.

There is also a secondary realized-deployment drag from 76920. Runtime Planning repeatedly generated BUY_NEW plans for 76920, but the symbol was quarantined by historical corporate-action continuation and never produced a 76920 BUY fill. That makes BUY_NEW planning counts look healthier than executable capital deployment. This is not evidence of 32 successful new entries; it is repeated planning against a quarantined symbol.

## Evidence

Audited sources:

- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T152905733571Z`
- `docs/phase_reports/phase29_l21g_buy_new_funnel_regression_and_capital_deployment_audit.md`
- `docs/phase_reports/phase29_l21h_opportunity_buy_quality_semantics_entry_supply_root_cause_audit.md`
- `docs/phase_reports/phase29_l21i_opportunity_score_semantic_contract_repair.md`
- `docs/phase_reports/phase29_l21j_23880_immediate_reentry_authority_regression_audit.md`
- `docs/phase_reports/phase29_l21k_prior_exit_state_materialization_design.md`
- `docs/phase_reports/phase29_l21k_campaign_derived_prior_exit_state_materialization_repair.md`

Key target-run facts:

- Daily artifact range inspected: `2022-08-10` through `2023-08-17` for capital/runtime evidence.
- Capital days with current portfolio evidence: 251.
- Average invested ratio: approximately 50.4%.
- Median invested ratio: approximately 52.9%.
- Max invested ratio: approximately 88.4%.
- Days below 40% invested: 64.
- BUY fills: 47.
- SELL fills: 68.

## BUY Funnel

The run does not show a raw opportunity or Buy Quality supply collapse:

- Candidate/opportunity rows: 12,600.
- Buy Quality decisions: 12,600.
- Buy Quality actions: 1,181 `FULL_ALLOCATION_ELIGIBLE`, 9,432 `REDUCED_ALLOCATION_ONLY`, 1,987 `REJECT`.
- Effective BQ pass/non-reject rate: about 84%.
- The old negative-score rejection pattern from L21H is not the dominant behavior in this run. L21I's semantic repair is visible through repeated `calibration_not_applied_raw_score_not_expected_return` and relative-score reason codes rather than fixed rejection of uncalibrated raw scores.

The major drop is later:

- PC BUY_NEW/add-candidate members: 548.
- PC positive BUY_NEW allocations: 72.
- Runtime Planning positive BUY_NEW plans: 71.
- Runtime Planning positive BUY_ADD plans: 8.
- BUY fills: 47.

So the principal narrowing is not BQ to candidate existence; it is PC allocation feasibility and realized executable conversion.

## Capital Utilization

The utilization pattern is consistent with cash being intentionally left undeployed by PC/lot feasibility rather than blocked by market-wide policy:

- PC positive-increment days: 72.
- PC zero-increment days: 180.
- Residual cash reasons:
  - `CONCENTRATION_LIMIT`: 147 days.
  - `NO_ELIGIBLE_OPPORTUNITY`: 71 days.
  - `COMPETITION_EXHAUSTED`: 28 days.
  - `NO_LOT_FEASIBLE_OPPORTUNITY`: 4 days.
  - `CAPITAL_BELOW_NEXT_LOT`: 2 days.
- PC skipped allocation reasons:
  - `minimum_lot_exceeds_concentration_cap`: 185 instances.
  - `lot_or_broker_infeasible`: 12 instances.
  - `minimum_lot_exceeds_remaining_budget`: 2 instances.

This points to a PC/lot/concentration feasibility bottleneck, with Strategy preserving caps and leaving residual cash when the next candidate cannot be expressed in executable lots within concentration constraints.

## Recent Cash Build-up

The late-run cash build-up is directly traceable to SELL exits followed by insufficient redeployment:

- `2023-07-18`: SELL `37780`, quantity 100, price 1,161, cash effect +116,100.
- `2023-07-24`: SELL `77090`, quantity 300, price 317, cash effect +95,100.
- `2023-07-25`: invested ratio fell to about 22.0%, with only one position and no BUY execution that day.
- `2023-08-14`: PC had available incremental budget around 78.4%, but final target sum remained about 38.2%; residual cash reason was `CONCENTRATION_LIMIT`.
- `2023-08-14`: PC did allocate one BUY_NEW, 65730, and execution filled it; utilization improved but remained far below full target exposure.

Recent policy did not force defensive cash in the key trough:

- `2023-07-19`, `2023-07-24`, `2023-07-25`, `2023-08-14`, and `2023-08-15` all had `target_gross_exposure: 1.0` and `cash_reserve: 0.0`.

## BUY_NEW Analysis

BUY_NEW is supply-constrained at the executable PC-positive layer, not at the raw candidate/BQ layer.

The repeated 76920 BUY_NEW sequence is material:

- Runtime Planning generated 32 BUY_NEW plans for 76920.
- No 76920 BUY fill was found.
- Planned 76920 dates included `2022-09-28` through `2022-10-12`, later `2022-10-21` through `2022-10-26`, and `2023-02-24` through `2023-03-24`.
- Submit evidence on no-BUY planned days showed `final_state=REVIEW_REQUIRED` with `historical_symbol_scoped_corporate_action_quarantine_continuation`.
- The quarantine evidence identified 76920 as `QUARANTINED` with `corporate_action_event_not_resolved` and production applicability `NEVER`.

Therefore, repeated 76920 BUY_NEW is not normal as capital deployment evidence. It is repeated plan generation for a symbol that remained unfilled under historical corporate-action quarantine.

## BUY_ADD Analysis

BUY_ADD is not the main cause of low utilization in this run.

- Runtime Planning produced 8 positive BUY_ADD plans.
- All 8 mapped to same-day BUY fills:
  - `2022-08-19` 94320, 400 shares.
  - `2022-09-07` 37820, 500 shares.
  - `2022-09-21` 94340, 300 shares.
  - `2022-12-01` 72730, 500 shares.
  - `2023-01-04` 76470, 4,400 shares.
  - `2023-01-05` 76470, 1,800 shares.
  - `2023-05-31` 21340, 2,500 shares.
  - `2023-06-08` 21340, 3,000 shares.

The problem is scarcity of ADD occasions, not ADD materialization failure.

## Root Cause Classification

Primary root cause:

`PORTFOLIO_CONSTRUCTION_LOT_CONCENTRATION_FEASIBILITY_SELECTIVITY`

Secondary root cause:

`HISTORICAL_CORPORATE_ACTION_QUARANTINE_REALIZED_BUY_CONVERSION_DRAG_76920`

Not primary:

- Buy Quality rejection.
- Raw opportunity generation.
- Market Context or portfolio policy defensive cash.
- BUY_ADD quantity conversion.
- Position Sizing propagation after PC positive allocation.
- Global execution failure.
- Safety hard cap regression.

## Regression Assessment

Regression is not confirmed.

L21G found no BUY_NEW regression in the earlier examined path when PC positive allocation existed. L21H identified the old Buy Quality opportunity-score semantic problem, and L21I repaired that contract. The target run now shows a high BQ non-reject rate, so the former BQ semantic bottleneck is not the principal current cause.

L21K repaired campaign-derived prior EXIT materialization, but that repair occurred after the target run was already produced. The present run therefore cannot be used to reject or confirm L21K's effect.

The remaining low-utilization behavior is better classified as a current architecture/strategy feasibility bottleneck plus a known historical quarantine conversion drag, not as a proven new regression.

## Architecture Conformance

Architecture conformance is mostly preserved:

- BQ is advisory/quality-gating and no longer acts as a fixed raw-score rejection wall.
- PC remains the authority for target membership and target weights.
- PS/RP generally propagate positive PC allocations into executable plans.
- Submit/execution preserve historical corporate-action quarantine constraints instead of fabricating fills.
- Safety and strategy concentration caps are preserved in the inspected allocation evidence.

The architecture concern is semantic observability and feedback, not authority inversion: repeated quarantined BUY_NEW planning can inflate perceived entry supply unless quarantine/pending status is fed back into utilization analysis.

## Recommended Next Task

Recommended next task:

`Phase29-L21M — Portfolio Construction Residual Cash / Lot-Concentration Allocation Selectivity Audit`

Scope:

- Decompose PC residual cash reasons by symbol, price, round lot, strategy cap, safety cap, and target-member selection.
- Determine whether `minimum_lot_exceeds_concentration_cap` and `CONCENTRATION_LIMIT` are expected Strategy behavior or overly conservative PC expression under the current capital size.
- Separately track 76920 quarantine feedback so repeated BUY_NEW plans against historical CA quarantine are not treated as executable entry supply.

Forbidden direction:

- Do not relax BUY Quality, raw opportunity thresholds, safety hard caps, or market policy simply to increase utilization.

## Primary Judgment

Answers to the required L21L questions:

1. Biggest factor: PC allocation selectivity under lot/concentration feasibility.
2. Normal Strategy judgment or implementation gap: mostly Strategy/PC feasibility behavior, with a secondary integration/feedback issue around 76920 quarantine; not a broad execution defect.
3. BUY_NEW supply shortage: yes at PC-positive/executable supply; no at raw candidate or BQ-pass supply.
4. Buy Quality main cause: no.
5. PC/PS materialization main cause: PC yes; PS no. PC-positive allocations mostly reach RP.
6. BUY_ADD shortage main cause: no. BUY_ADD was rare, but the 8 positive ADD plans all filled.
7. Safety cap main cause: no. Safety caps are preserved; the active block is lot/concentration feasibility as expressed by PC.
8. Market Context main cause: no. Several late low-utilization dates had 100% target gross exposure and 0% cash reserve.
9. Execution/pending main cause: secondary only, centered on 76920 historical corporate-action quarantine.
10. 76920 repeated BUY_NEW normal: not normal as deployment evidence; it is repeated planning for an unfilled quarantined symbol.
11. Regression confirmed: no, not proven.
12. Fix needed: yes, but not threshold relaxation. The next fix/audit should target PC residual-cash allocation selectivity and quarantine-aware planning feedback.
13. Next component if fix needed: Portfolio Construction residual cash / lot-concentration allocation selection, with 76920 quarantine feedback tracked separately.

Primary judgment:

`PHASE29_L21L_CAPITAL_UNDERUTILIZATION_ROOT_CAUSE_PC_LOT_CONCENTRATION_SELECTIVITY_WITH_SECONDARY_76920_CA_QUARANTINE_DRAG_CONFIRMED`
