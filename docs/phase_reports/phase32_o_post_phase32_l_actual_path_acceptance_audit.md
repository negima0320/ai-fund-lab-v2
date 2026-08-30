# Phase32-O — Post-Phase32-L Actual-Path Acceptance Audit

## Scope

This is a READ-ONLY actual-path acceptance audit for Phase32-L.

NO CODE CHANGE: confirmed. The only Phase32-O workspace change is this phase
report.

NO future-information use: confirmed. This audit used target run artifacts,
current source identity, and Architecture/SoT only. It did not use future price,
future return, future regime, future MFE/MAE, later outcome, Historical
profitability, or hindsight.

Codex did not run fresh-run, resume, replay, or long Historical.

## Target Run Identity

- Run: `runtime-test-historical-extended-smoke-20260830T032332732107Z`
- Profile: `historical-extended-smoke`
- Source commit recorded by run: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current HEAD: `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Source dirty: `true`
- Historical evaluation authority: `PASS`
- Accepted artifact hash: `d2352977bf6feaea22e7c4e5d00980d775eefe1622126fbbde4bd22d3ee6e0e0`
- Registry hash: `ac108fcfadb01f613263fa2ea00ba37fc7a0ded0ad224387d18222bfb73c3ec2`

Audit snapshot:

- Run status: `RUNNING`
- Completed business days: 16, `2022-10-03` through `2022-10-25`
- Latest daily directory observed: `2022-10-26`
- Next job at snapshot: `2022-10-26:market_refresh`
- Completed jobs: 144
- Non-zero completed job exits: 0

Because the run is active and user-operated, this report treats the above as the
Phase32-O evidence snapshot.

## Evidence Coverage

Artifacts inspected:

- `run_state.json`
- `historical_evaluation_authority.json`
- `strategy_shadow_manifest.json`
- daily `positions/position_campaigns.json`
- daily `position_management/pm_decisions.json`
- daily `strategy/portfolio_construction.json`
- daily `strategy/position_sizing.json`
- daily `strategy/runtime_planning.json`
- daily `morning/planning_evidence.json`
- daily `execution/fills.json`
- daily `execution/submitted_order_authority.json`
- daily `execution/ledger_append_evidence.json`

Observed counts at snapshot:

- fills: 65
  - `BUY_NEW`: 36
  - `BUY_ADD`: 3
  - `SELL_EXIT`: 24
  - `REDUCE`: 2
- PM decisions: 133
  - `HOLD`: 75
  - `REDUCE`: 29
  - `EXIT`: 16
  - `ADD`: 13
- PC rows: 806
- Runtime Planning rows:
  - `NO_ORDER`: 327
  - `NO_ACTION`: 84
  - `BUY_NEW`: 74
  - `SELL_EXIT`: 24
  - `BUY_ADD`: 4
- Position campaign rows inspected: 248
- Campaign event rows inspected: 312
- PM decision evidence events inspected: 704

## Campaign Continuity Summary

Campaign identity continuity is accepted for the observed actual path.

Checks:

- position campaign row ID vs contained execution event campaign ID:
  - rows/events inspected: 248 rows / 312 execution events
  - split count: 0
- position campaign row ID vs contained PM evidence event campaign ID:
  - PM evidence events inspected: 704
  - split count: 0
- PM decision campaign ID vs same-day PC current campaign ID:
  - matched: 133 / 133
  - mismatches: 0

This confirms the key Phase32-L campaign identity repair behavior for observed
open/current lifecycle:

- BUY fill campaign ID becomes the current-position campaign authority when
  materialized.
- PM and PC refer to the same open campaign ID.
- ADD inherits the same campaign ID.
- REDUCE/EXIT inherit the same campaign ID in observed PM/PC/fill paths.
- No event-inside-row campaign split like the pre-L `pc-1533...` vs
  `pc-d8c9...` family split was reproduced.

Classification:

```text
Campaign identity: PASS
```

## Representative Campaign Traces

### 94340 — BUY_NEW -> HOLD/ADD -> BUY_ADD

- `2022-10-03`: BUY_NEW fill creates
  `pc-42839ae1d0febbbc-94340-0001`.
- `2022-10-04` onward: position campaign row remains
  `pc-42839ae1d0febbbc-94340-0001`.
- PM/PC same-day decisions for `HOLD` / `ADD` use the same campaign ID.
- BUY_ADD fills on `2022-10-06`, `2022-10-11`, and `2022-10-12` preserve the
  same campaign family in the materialized campaign row/events.
- Latest inspected position row:
  - symbol `94340`
  - campaign `pc-42839ae1d0febbbc-94340-0001`
  - status `OPEN`
  - quantity `500`

Judgment: PASS.

### 94320 — BUY_NEW -> current position

- `2022-10-05`: BUY_NEW path materializes
  `pc-3f24ce63eeaff2d1-94320-0001`.
- Latest inspected position row:
  - symbol `94320`
  - campaign `pc-3f24ce63eeaff2d1-94320-0001`
  - status `OPEN`
  - quantity `200`
- Row events and PM evidence events carry the same campaign ID.

Judgment: PASS.

### 99840 — BUY_NEW -> current position near cap

- `2022-10-05`: BUY_NEW path materializes
  `pc-beab102a0ca858eb-99840-0001`.
- Latest inspected position row:
  - symbol `99840`
  - campaign `pc-beab102a0ca858eb-99840-0001`
  - status `OPEN`
  - quantity `100`
- Row events and PM evidence events carry the same campaign ID.

Judgment: PASS.

### 76470 — BUY_NEW -> EXIT -> later REENTRY evaluations

- `2022-10-12`: BUY_NEW fill campaign
  `pc-ec3672c4e51adeca-76470-0001`.
- `2022-10-14`: SELL_EXIT fill uses
  `pc-ec3672c4e51adeca-76470-0001`.
- Later REENTRY evaluations exist for `76470`, but prior provenance fields are
  not fully materialized; see next section.

Campaign identity judgment for the closed campaign path: PASS for observed
fill/PM/PC identity continuity. REENTRY provenance judgment: FAIL.

## Prior EXIT Provenance Summary

REENTRY evaluations were observed, but Phase32-L prior provenance acceptance is
not confirmed. It fails on actual artifacts.

Observed REENTRY semantic rows:

- total: 119
- `FAIL_CLOSED`: 114
- `REVIEW_REQUIRED`: 5
- `PASS`: 0

Prior provenance fields:

- non-empty `prior_campaign_id`: 0 / 119
- non-empty `source_pm_decision_id`: 0 / 119
- non-empty `source_decision_id`: 0 / 119
- `prior_exit_provenance_status=REVIEW_REQUIRED`: 119 / 119
- strict-prior date violations: 0

Safety separation fields:

- `reentry_safety_restriction_status=PASS`: all observed REENTRY rows
- broker eligibility: `PASS` for all observed REENTRY rows
- corporate action: `NO_EVENT` for all observed REENTRY rows

Representative actual rows:

- `2022-10-06` `33700`
  - `prior_exit_business_date=2022-10-05`
  - `prior_exit_decision_type=EXIT`
  - prior reason codes include
    `pm_discrete_control_persistent_deterioration_exit`,
    `risk_increased_but_trend_not_broken`,
    `strategy_intelligence_sell_side_evidence_connected`
  - `prior_campaign_id=""`
  - `source_pm_decision_id=""`
  - `source_decision_id=""`
  - `prior_exit_provenance_status=REVIEW_REQUIRED`

- `2022-10-17` `76470`
  - `prior_exit_business_date=2022-10-14`
  - `prior_exit_decision_type=EXIT`
  - prior reason code includes `weak_hold_score`
  - `prior_campaign_id=""`
  - `source_pm_decision_id=""`
  - `source_decision_id=""`
  - `prior_exit_provenance_status=REVIEW_REQUIRED`

This is not merely "accepted REENTRY event not yet observed." The contract says
prior provenance can be accepted on rejected REENTRY evaluations when canonical
strict-prior context exists. Actual artifacts show prior EXIT date/type/reason
codes reaching REENTRY rows, but the canonical identity/source fields remain
empty and provenance status remains `REVIEW_REQUIRED`.

Classification:

```text
REENTRY provenance: FAIL
```

## Accepted REENTRY Cases

No accepted REENTRY case was observed in the Phase32-O evidence snapshot:

- `reentry_semantic_status=PASS`: 0
- REENTRY BUY/fill lifecycle: 0
- new campaign after accepted REENTRY: not observed
- next-day current/PM/PC continuity after accepted REENTRY: not observed
- later ADD after accepted REENTRY: not observed

This subcase is event-limited and should not by itself fail campaign identity.
However, because rejected REENTRY evaluations already show provenance failure,
continuing the run alone is not sufficient to accept the prior provenance
repair.

Classification:

```text
Accepted REENTRY lifecycle: INSUFFICIENT_EVIDENCE
```

Additional evidence needed for this subcase:

- at least one `reentry_semantic_status=PASS` row,
- a resulting REENTRY/BUY fill,
- next-day current position campaign materialization,
- at least one subsequent PM/PC lifecycle decision for the new campaign,
- ideally one subsequent ADD/REDUCE/EXIT event.

The existing user-operated run can continue to seek this event; Codex should not
start a new fresh-run.

## KI-004 Regression

KI-004 safety classification separation is not regressed in the observed
artifacts.

Evidence:

- REENTRY rows: 119
- `reentry_safety_restriction_status=PASS`: all observed rows
- broker eligibility: `PASS`: all observed rows
- corporate-action status: `NO_EVENT`: all observed rows
- REENTRY failures are expressed as churn/current-evidence/recovery/prior
  context states, not as false Safety/Broker/Corporate-action blocks.

Classification:

```text
KI-004 regression: NO
```

## KI-006 Regression

KI-006 BUY_WAIT / explicit zero ADD resurrection was not reproduced.

Evidence:

- Runtime BUY_ADD planning rows: 4
- BUY_ADD fills: 3
- BUY_ADD rows with `quality_action=BUY_WAIT` or explicit zero quality
  allocation adjustment: 0

Classification:

```text
KI-006 regression: NO
```

## G129 Regression

G129 BUY_ADD quantity semantics are not regressed in the observed actual path.

Evidence:

- BUY_ADD Runtime Planning rows: 4
- BUY_ADD fills: 3
- Runtime G63 binding reports no Runtime capital priority redecision.
- Runtime plans consume PS-bound quantity (`planned_quantity=100`) rather than
  recomputing ADD priority.
- BUY_ADD fills observed for `94340` are one-order-increment, not cumulative
  position-scope submissions.

Classification:

```text
G129 regression: NO
```

## Runtime Stability

No Runtime lifecycle instability attributable to Phase32-L was observed.

Evidence:

- Run status at snapshot: `RUNNING`
- Completed jobs: 144
- Non-zero completed job exits: 0
- Completed business days: 16
- No HALT in completed jobs.

Classification:

```text
Runtime stability: PASS
```

## Acceptance Classifications

| Target | Classification | Evidence |
|---|---|---|
| Campaign identity | `PASS` | 0 campaign event/row splits; PM-PC 133/133 matched |
| REENTRY prior provenance | `FAIL` | 119/119 REENTRY rows remain `REVIEW_REQUIRED`; all prior/source ids empty |
| Accepted REENTRY lifecycle | `INSUFFICIENT_EVIDENCE` | no accepted REENTRY observed |
| Overall | `BLOCKED` | primary prior provenance acceptance failed despite campaign identity PASS |

## Repair Required

Repair required: `YES`.

Reason: Phase32-L campaign identity continuity is confirmed, but Phase32-L
REENTRY prior provenance materialization is not accepted on actual artifacts.
Rejected REENTRY evaluations already provide enough evidence to test the
contract, and they still lack `prior_campaign_id`, `source_pm_decision_id`, and
`source_decision_id`.

No repair was performed in Phase32-O.

## Continue Current Run Required

Continue current run required: `YES`, but only for the accepted REENTRY lifecycle
subcase.

Continuing the run is not sufficient to close the REENTRY provenance failure
unless a subsequent repair or additional investigation shows why actual
provenance fields remain empty despite prior EXIT context reaching REENTRY rows.

## Final Judgment

1. `IS_PHASE32_L_CAMPAIGN_IDENTITY_REPAIR_CONFIRMED_ON_ACTUAL_PATH`

   YES. Observed campaign identity continuity passes for open/current campaign
   lifecycle, PM/PC consistency, ADD inheritance, and event-row identity
   preservation.

2. `IS_PHASE32_L_REENTRY_PROVENANCE_REPAIR_CONFIRMED_ON_ACTUAL_PATH`

   NO. Actual REENTRY rows preserve strict-prior dates and reason codes, but
   `prior_campaign_id`, `source_pm_decision_id`, and `source_decision_id` remain
   empty, and `prior_exit_provenance_status` remains `REVIEW_REQUIRED` for all
   observed REENTRY rows.

3. `IS_AN_ACCEPTED_REENTRY_NEW_CAMPAIGN_LIFECYCLE_CONFIRMED`

   INSUFFICIENT_EVIDENCE. No accepted REENTRY has occurred yet in the audited
   snapshot.

4. `IS_ANY_CORRECTNESS_REPAIR_STILL_REQUIRED`

   YES. A narrow follow-up is required for actual-path REENTRY prior provenance
   materialization. Phase32-O did not perform that repair.

5. `IS_THE_BASELINE_READY_FOR_THE_NEXT_PERFORMANCE_DESIGN_STEP`

   NO. Campaign identity is accepted, but REENTRY prior provenance is still
   failing on actual post-L artifacts and should be resolved before moving to
   the next performance design step.

Final classification:

`PHASE32_O_POST_L_ACTUAL_PATH_BLOCKED_REENTRY_PROVENANCE_NOT_ACCEPTED`

