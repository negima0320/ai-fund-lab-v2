# Phase32-K — Integrated Correctness Acceptance Audit

## Current Run Identity And Evidence Coverage

- Target run: `runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T010004222332Z`
- Profile: `historical-extended-smoke`
- Source commit recorded by completed jobs: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- `run_state.json` status: `RUNNING`
- Completed business days: 73, from `2022-10-03` through `2023-01-19`
- Strategy artifacts generated: 74 days, from `2022-10-03` through `2023-01-20`
- Completed jobs inspected: 666
- Non-zero job exits: 0
- HALT count: 0

This is a READ-ONLY acceptance audit. No fresh-run, resume, replay, or long Historical was run. No future price, future return, future regime, MFE/MAE, later SELL outcome, final campaign outcome, Historical profitability, or hindsight winner/loser reasoning was used.

## Phase32-C Acceptance — Provenance / Campaign Identity

Classification: `FAIL`

Positive evidence:

- Execution fills consistently carry `source_decision_id`, `pending_item_id`, `order_plan_item_id`, and `position_campaign_id`.
- Across 277 fills, no fill-level missing fields were observed for:
  - `source_decision_id`
  - `pending_item_id`
  - `order_plan_item_id`
  - `position_campaign_id`
- Fill type coverage:
  - `BUY_NEW`: 130
  - `SELL_EXIT`: 116
  - `BUY_ADD`: 16
  - `REDUCE`: 15
- Runtime planning shows no runtime quantity redecision flags:
  - `ps_authorized_quantity_reoptimized_by_runtime`: 0 observed true
  - `runtime_capital_priority_redecision`: 0 observed true

Blocking evidence:

- Campaign identity continuity is still broken on actual path.
- Example 83060:
  - `2022-10-26` BUY fill campaign: `pc-1533c2a55c4c8bf5-83060-0001`
  - `2022-10-27` `positions/position_campaigns.json` campaign: `pc-d8c9ed4a368c8b8d-83060-0002`
  - `2022-10-27` PC current-position campaign: `pc-d8c9ed4a368c8b8d-83060-0002`
  - `2022-10-27` PM HOLD decision campaign: `pc-1533c2a55c4c8bf5-83060-0001`
- Example 76470:
  - `2022-11-11` BUY_NEW fill campaign: `pc-77ed2705efa03f62-76470-0001`
  - `2022-11-24` PM ADD campaign: `pc-77ed2705efa03f62-76470-0001`
  - `2022-11-24` PC/current-position campaign: `pc-08ec9eef313ee674-76470-0002`
  - `2022-11-25` BUY_ADD fill campaign: `pc-08ec9eef313ee674-76470-0002`

The same open position can therefore have different campaign authorities across PM, PC/current-position observability, and fills. This is a concrete current-baseline campaign identity split, not an insufficient-evidence case.

## Audit 2 — Representative REENTRY Case 83060

Classification: `FAIL`

Actual path:

- `2022-10-03`: 83060 BUY_NEW fill
  - source decision: `rp-2022-10-03-83060-buy_new-a1e4c3343d5177dc`
  - campaign: `pc-2109759b35be4a73-83060-0001`
- `2022-10-04`: 83060 PM EXIT
  - PM decision: `pm-2022-10-04-83060-exit`
  - PM campaign: `pc-2109759b35be4a73-83060-0001`
  - reason: `trend_and_opportunity_broken`
  - reason codes: `trend_and_opportunity_broken`
- `2022-10-04`: 83060 SELL_EXIT fill
  - source decision: `rp-2022-10-04-83060-sell_exit-2310c155634662da`
  - campaign: `pc-2109759b35be4a73-83060-0001`
- `2022-10-26`: 83060 PC REENTRY evaluation
  - `semantic_buy_type=REENTRY`
  - `reentry_semantic_status=PASS`
  - `prior_exit_business_date=2022-10-04`
  - `prior_exit_reason=trend_and_opportunity_broken`
  - `prior_exit_reason_codes=[trend_and_opportunity_broken]`
  - `prior_exit_reason_class=TREND_MOMENTUM`
  - `prior_campaign_id=""`
  - `source_pm_decision_id=""`
  - `source_decision_id=""`
  - `prior_exit_provenance_status=REVIEW_REQUIRED`
  - `broker_eligibility_status=PASS`
  - `corporate_action_status=NO_EVENT`
  - `safety_restriction_status=PASS`
- `2022-10-26`: 83060 BUY_NEW fill
  - source decision: `rp-2022-10-26-83060-buy_new-e7156d336f465694`
  - campaign: `pc-1533c2a55c4c8bf5-83060-0001`
- `2022-10-27`: 83060 observed as held again, but PC/current campaign is `pc-d8c9ed4a368c8b8d-83060-0002`, while PM HOLD keeps `pc-1533c2a55c4c8bf5-83060-0001`.

Acceptance checks:

- strict-prior prior EXIT date: PASS
- prior EXIT reason/reason_codes/class: PASS
- broker/corporate-action/safety separation: PASS
- new campaign differs from prior closed campaign: PASS
- `prior_campaign_id` present: FAIL
- `source_pm_decision_id` present: FAIL
- `source_decision_id` present: FAIL
- `prior_exit_provenance_status=PASS` when canonical evidence exists: FAIL
- no campaign authority split after REENTRY fill: FAIL

The 83060 testcase blocks Phase32-H/J integrated acceptance.

## Phase32-F Acceptance — Buy Quality ADD Preservation

Classification: `PASS`

Actual existing-position PM ADD cases with `quality_action=BUY_WAIT` or explicit `quality_allocation_adjustment=0.0`:

- Observed cases: 13
- PC accepted incremental weight: 0 in all 13
- lot-aware accepted incremental weight: 0 in all 13
- PS positive delta resurrection violations: 0
- Runtime BUY_ADD resurrection violations: 0
- BUY_ADD fills emitted from those zero-authority cases: 0

Representative examples:

- `2022-10-12` / `94320`: `BUY_WAIT`, `quality_allocation_adjustment=0.0`, PC increment 0, lot-aware increment 0, no BUY_ADD.
- `2022-11-01` / `99840`: `BUY_WAIT`, `quality_allocation_adjustment=0.0`, PC increment 0, lot-aware increment 0, no BUY_ADD.

Positive-quality ADD still works:

- Positive PC ADD cases observed: 21
- Positive PS/runtime BUY_ADD cases observed: 18
- Representative positive cases:
  - `2022-11-25` / `76470`: PC positive ADD, PS delta 100, Runtime BUY_ADD 100, fill 100.
  - `2022-12-01` / `76470`: PC positive ADD, PS delta 100, Runtime BUY_ADD 100, fill 100.
  - `2023-01-05` / `76470`: PC positive ADD, PS delta 100, Runtime BUY_ADD 100, fill 100.

The remaining positive PC cases without fills are explained by downstream discrete/runtime feasibility and are not evidence of BUY_WAIT resurrection.

## Progressive ADD / G129 / Phase32-G Contract

Classification: `PARTIAL`

Positive evidence for G129 and Phase32-G:

- 76470 repeated positive ADD sequence is present.
- BUY_ADD fills for 76470 include:
  - `2022-11-25`: +100
  - `2022-11-28`: +100
  - `2022-11-30`: +100
  - `2022-12-01`: +100
  - `2022-12-06`: +100
  - `2022-12-16`: +100
  - `2022-12-21`: +100
  - `2022-12-23`: +100
  - `2022-12-28`: +100
  - `2023-01-04`: +100
  - `2023-01-05`: +100
- Repeated 76470 BUY_ADD fills use the same fill-side campaign after ADD begins:
  - `pc-08ec9eef313ee674-76470-0002`
- Runtime planning uses PS quantity and does not re-rank/redecide:
  - runtime redecision flags: 0
- PM ADD alone does not force capital:
  - `2022-11-24` / 76470 PM ADD, PC increment 0, PS delta 0, Runtime `NO_ACTION`.

Blocking/partial evidence:

- The 76470 open campaign identity is split:
  - `2022-11-11` BUY_NEW fill campaign: `pc-77ed2705efa03f62-76470-0001`
  - PM ADD campaign on `2022-11-24` and `2022-11-25`: `pc-77ed2705efa03f62-76470-0001`
  - PC/current campaign and BUY_ADD fill campaign from `2022-11-25`: `pc-08ec9eef313ee674-76470-0002`

Therefore:

- G129 BUY_ADD quantity semantics: PASS
- Phase32-G PM ADD directional intent and PC-owned magnitude: PASS
- Campaign identity continuity across the same open position: FAIL

The combined progressive ADD audit is `PARTIAL`, blocked only by the campaign identity split.

## Re-entry Safety Classification Summary

Classification: `PASS`

Across 983 REENTRY evaluations:

- `safety_restriction_status=PASS`: 983
- `safety_restriction_status=FAIL_CLOSED`: 0
- `broker_eligibility_status=PASS`: 983
- `corporate_action_status=NO_EVENT`: 983
- `recovery_status`
  - `FAIL_CLOSED`: 892
  - `REVIEW_REQUIRED`: 89
  - `PASS`: 2
- `prior_exit_context_status`
  - represented through REENTRY semantic result; strict-prior date violations: 0

The Phase32-I pattern:

`broker PASS + corporate NO_EVENT + recovery/prior-context failure -> safety FAIL_CLOSED`

is no longer systematically present in the current run. No remaining `safety_restriction_status=FAIL_CLOSED` rows were observed.

## REENTRY Provenance Summary

Classification: `FAIL`

Across 983 REENTRY evaluations:

- `prior_exit_provenance_status=REVIEW_REQUIRED`: 983
- non-empty `prior_campaign_id`: 0
- non-empty `source_pm_decision_id`: 0
- non-empty `source_decision_id`: 0
- strict-prior date violations: 0
- reason/class preservation:
  - `TREND_MOMENTUM`: 251
  - `HARD_STOP`: 279
  - `GENERIC`: 453

This confirms the actual run still lacks Phase32-J provenance completion. This is a concrete evidence failure, not `INSUFFICIENT_EVIDENCE`.

## Runtime Stability / Integration

Runtime stability: `PASS_WITH_CORRECTNESS_BLOCKERS`

- Completed business days: 73
- Completed jobs: 666
- Non-zero job exits: 0
- CLI result bad statuses: 0
- Ledger append evidence: `PASS`
- Pending terminalization evidence:
  - `NOT_REQUIRED`: 72
  - `ALREADY_TERMINAL`: 2
- Strategy shadow manifest:
  - artifact count: 876
  - blocked dates: 0
  - active runtime consumer eligibility: `YES`

The run is operationally stable through the inspected window, but correctness acceptance is blocked by campaign/provenance defects.

## Known-Issue Closure Matrix

| Issue | Status | Evidence |
|---|---|---|
| KI-001 Prior EXIT semantic/provenance loss | `PARTIAL` | Strict-prior and reason/class preservation are visible, but all 983 REENTRY rows lack prior campaign/source provenance. |
| KI-002 source decision/campaign provenance loss | `OPEN_DEFECT` | Fill-level ids are present, but REENTRY prior provenance is absent and source/campaign authority does not survive into REENTRY evidence. |
| KI-003 campaign identity authority split | `OPEN_DEFECT` | Concrete campaign split observed for 83060 and 76470 across PM, PC/current-position observability, and fills. |
| KI-004 REENTRY safety classification ambiguity | `CLOSED_ACCEPTED` | Safety/broker/corporate-action/recovery are separated; no safety fail-closed collapse observed across 983 REENTRY rows. |
| KI-005 BUY_ADD authority ambiguity | `CLOSED_ACCEPTED` | Positive PS ADD deltas produce BUY_ADD; Runtime redecision flags are 0; no PM ADD direct-to-order conversion observed. |
| KI-006 Buy Quality re-expansion | `CLOSED_ACCEPTED` | 13 BUY_WAIT/explicit-zero ADD cases had no PC/PS/Runtime BUY_ADD resurrection. |
| KI-007 lot resolution gap | `CLOSED_NO_REPAIR` | No new concrete evidence that discrete lot conversion silently overrides PC investment meaning. |

## Open Defects

1. REENTRY prior provenance completion is not accepted on actual runtime evidence.
   - Severity: mandatory correctness blocker.
   - Violated contract: canonical strict-prior PM/lifecycle provenance must survive into REENTRY prior context when available.
   - Recommended next task: root-cause why target run still materializes all REENTRY provenance as `REVIEW_REQUIRED` despite Phase32-J source-level repair.

2. Campaign identity authority split remains present.
   - Severity: mandatory correctness blocker.
   - Violated contract: one open campaign must have one campaign identity across PM, PC/current position, pending/order/execution/fill/ledger.
   - Recommended next task: repair current-position/campaign observability so it preserves fill/ledger campaign authority instead of regenerating a different campaign family.

No repair was implemented in Phase32-K.

## Baseline Freeze Readiness

Baseline freeze readiness: `NO`

Reason:

- Mandatory Phase32-C/H/J correctness acceptance is blocked on actual evidence.
- KI-002 and KI-003 remain open concrete defects.
- KI-001 remains partial because semantic preservation is accepted but provenance completion is not.

## 3-Year Historical Readiness

3-year Historical readiness: `NO`

Reason:

- Operational stability is promising, but correctness acceptance is blocked.
- Running a 3-year Historical now would produce larger evidence over known campaign/provenance defects.

Additional evidence is not required to prove the blockers. The target run already contains:

- 983 REENTRY evaluations,
- concrete 83060 REENTRY acceptance path,
- concrete 76470 progressive ADD path,
- concrete campaign identity splits.

## Confirmations

- NO CODE CHANGE in Phase32-K: YES
- NO config change in Phase32-K: YES
- NO fresh-run/resume/replay/long Historical by Codex: YES
- NO future-information use: YES
- NO Historical profitability use: YES
- Phase32-only performance tuning imported: NO

## Final Judgment

1. `ARE_PHASE32_CORRECTNESS_REPAIRS_ACCEPTED_ON_ACTUAL_RUNTIME_EVIDENCE`
   - `NO`
   - Phase32-F, KI-004, G129 quantity semantics, and Phase32-G directional/magnitude split are accepted.
   - Phase32-C campaign identity continuity and Phase32-H/J REENTRY provenance completion are not accepted.

2. `ARE_ALL_MANDATORY_PHASE31_LATENT_DEFECTS_CLOSED_OR_EXPLICITLY_NO_REPAIR`
   - `NO`
   - KI-002 and KI-003 remain `OPEN_DEFECT`.
   - KI-001 remains `PARTIAL`.

3. `IS_THE_CURRENT_BASELINE_READY_TO_FREEZE_FOR_LONG_HISTORICAL_VALIDATION`
   - `NO`

4. `IS_ANY_REPAIR_REQUIRED_BEFORE_THE_3_YEAR_HISTORICAL_RUN`
   - `YES`
   - Repair REENTRY provenance materialization and campaign identity continuity first.

Final Judgment:

`PHASE32_K_INTEGRATED_ACCEPTANCE_BLOCKED`

