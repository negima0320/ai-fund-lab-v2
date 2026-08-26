# Phase31-G111 — Post-Reconsideration Performance Divergence / Capital Displacement Causal Audit

## Scope

READ-ONLY audit only. No code, config, threshold, weight, run state, fresh-run,
resume, replay, or Historical execution was changed or executed.

Primary post-repair run:

`runtime-test-historical-extended-smoke-20260825T072702567342Z`

Verified baseline run:

`runtime-test-historical-extended-smoke-20260824T055234719725Z`

The baseline identity is confirmed by exact match to the operator-supplied equity path:

| Date | Baseline equity | Post-repair equity | Delta |
|---|---:|---:|---:|
| 2023-01-24 | 1,212,400 | 1,151,650 | -60,750 |
| 2023-02-08 | 1,273,290 | 1,170,210 | -103,080 |
| 2023-03-22 | 1,421,380 | 1,325,090 | -96,290 |
| 2023-04-03 | 1,451,210 | 1,266,230 | -184,980 |

Post-hoc performance deltas were used only to locate and characterize divergence.

POST_HOC_OUTCOME_USED_AS_DECISION_AUTHORITY = NO

## First Actual Portfolio Divergence

The first fill-level divergence is:

- Date: `2022-11-21`
- Symbol: `76470`
- Action: `BUY_NEW`
- Quantity: `400`
- Execution price: `26`
- Notional: `10,400`

Baseline `2022-11-21` fills:

- `35210 BUY 100 @ 188`
- `58030 BUY 100 @ 188`

Post-repair `2022-11-21` fills:

- `35210 BUY 100 @ 188`
- `58030 BUY 100 @ 188`
- `76470 BUY 400 @ 26`

The post-repair PC evidence for `76470` on `2022-11-21` shows a G97 authoritative reconsideration row:

- `allocation_authority_status = AUTHORITATIVE_PC_RESIDUAL_RECONSIDERATION_BOUND`
- `canonical_opportunity_quality_class = COMPARABLE_MARGINAL`
- `interaction_result = DEPLOY_ELIGIBLE`
- `authorized_allocation_weight = 0.009774`
- `lot_materialization_status = LOT_EXECUTABLE_COMPATIBLE`
- `pc_positive_executable_quantity_authority.status = PASS`
- `final_allocated_quantity = 400`
- `future_information_used = false`
- `historical_outcome_used = false`

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_DATE = 2022-11-21

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_SYMBOL = 76470

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_ACTION = BUY_NEW

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_QUANTITY = 400

## Reconsideration-Derived Campaigns

Through `2023-04-03`, G97 authoritative security rows that actually filled were:

| Date | Symbol | Quantity | Notional | Campaign |
|---|---:|---:|---:|---|
| 2022-11-21 | 76470 | 400 | 10,400 | `pc-03ca91a459c078c1-76470-0002` |
| 2022-11-25 | 93180 | 700 | 2,800 | `pc-03ca91a459c078c1-93180-0002` |
| 2023-02-21 | 94320 | 200 | 31,780 | `pc-03ca91a459c078c1-94320-0002` |

Aggregate G97 binding evidence in the completed window:

- G97 binding-active dates: 119
- G97 positive security allocation rows: 28
- G97 cash deferral rows: 155
- G97 security rows that filled: 3
- Filled G97 initial notional: 44,980

RECONSIDERATION_DERIVED_CAMPAIGN_COUNT = 3

## 76470 Entry vs ADD Separation

The 76470 campaign must not be treated as a single G97 effect.

Initial reconsideration entry:

- `2022-11-21 BUY 400 @ 26`
- Initial notional: `10,400`
- Source: G97 residual reconsideration authoritative binding

Later ADDs:

- `2022-12-06 BUY_ADD 1,300 @ 27`, notional `35,100`
- `2022-12-21 BUY_ADD 1,000 @ 27`, notional `27,000`
- `2023-01-04 BUY_ADD 900 @ 28`, notional `25,200`

Exits:

- `2023-01-23 SELL 900 @ 26`, notional `23,400`
- `2023-01-24 SELL 2,700 @ 26`, notional `70,200`

76470 totals:

- INITIAL_RECONSIDERATION_ENTRY_QUANTITY = 400
- INITIAL_RECONSIDERATION_ENTRY_NOTIONAL = 10,400
- ADD_EVENT_COUNT = 3
- TOTAL_ADD_QUANTITY = 3,200
- TOTAL_ADD_NOTIONAL = 87,300
- MAX_QUANTITY = 3,600
- MAX_MARKET_VALUE = 104,400
- 76470_MAX_WEIGHT = 9.57%
- Realized campaign contribution through exit = approximately `-4,100`

76470_INITIAL_ENTRY_CAUSED_BY_RECONSIDERATION = YES

76470_LATER_SCALE_CAUSED_BY_EXISTING_ADD_PATH = YES

76470_STRATEGY_CAP_BREACH = NO

76470_SAFETY_CAP_BREACH = NO

The direct 76470 realized loss is far smaller than the `2023-04-03` equity delta. The material divergence is therefore not explained by 76470 direct PnL alone; it is mainly portfolio path dependence and later capital allocation displacement.

## 76470 Decision-Time Quality

Only same-date evidence was used for decision quality.

| Date | Action | Decision-time evidence | Classification |
|---|---|---|---|
| 2022-11-21 | G97 BUY_NEW | `DEPLOY_ELIGIBLE`, `COMPARABLE_MARGINAL`, lot executable, allocation rank 4, healthy market, normal deployment | VALID_COMPARABLE_MARGINAL |
| 2022-12-06 | BUY_ADD | PM/PC ADD PASS, `ADD_SELECTED`, `STRONG_COMPETITOR_ALLOWED`, `CASH_PREFERRED_PARTICIPATION_VALID`, lot executable | VALID_BUT_REDUCED_RISK_PARTICIPATION |
| 2022-12-21 | BUY_ADD | PM/PC ADD PASS, `ADD_SELECTED`, `COMPARABLE_MARGINAL`, `CASH_PREFERRED_PARTICIPATION_VALID`, lot executable | VALID_BUT_MARGINAL |
| 2023-01-04 | BUY_ADD | PM/PC ADD PASS, `COMPARABLE_MARGINAL`, `CASH_PREFERRED_PARTICIPATION_VALID`, lot executable | VALID_BUT_MARGINAL |

WAS_76470_INCREMENTAL_CAPITAL_DECISION_TIME_VALID = PARTIAL

Reason: same-date evidence supports non-zero participation, but the later ADD path repeatedly allocates marginal incremental capital to the same campaign under defensive/cautious conditions. That is not a cap breach or future-outcome judgment; it is an architecture question about repeated marginal ADD competition.

## Capital Competition Correctness

G97 initial `76470` entry did not receive a special ranking override. The row re-entered canonical competition as:

- `REALLOCATABLE_RESIDUAL_REENTERED_CANONICAL_COMPETITION`
- `G90_REUSED_FOR_RECONSIDERATION`
- `RECONSIDERATION_AUTO_AUTHORIZATION_NO`
- `OPTIONAL_CASH_FIRST_CLASS_PRESERVED`
- `runtime_priority_redecision = false`
- `position_sizing_quantity_owner = POSITION_SIZING`

The post-repair evidence does not show unintended G97 provenance privilege for future priority. After entry, later 76470 scaling is explained by the normal ADD path, not by a persistent G97 privilege flag.

CAPITAL_COMPETITION_DEFECT_COUNT = 0 confirmed G97-specific defects

RECONSIDERATION_PROVENANCE_CHANGES_FUTURE_PRIORITY = NO

UNINTENDED_RECONSIDERATION_PRIVILEGE_CONFIRMED = NO

## ADD / Competition Interaction

The 76470 ADD dates show ADD competition is present, but only partially satisfactory as an architecture guard:

- ADD competes with NEW_BUY candidates in PC competitor evidence.
- ADD competes with Cash through `CASH_PREFERRED_PARTICIPATION_VALID`.
- Same-date competitor sets are present and future/PnL inputs are absent.
- However, repeated ADDs can scale an existing campaign from 400 to 3,600 shares while each individual increment remains under cap and lot feasible.

This suggests the next narrow audit should be the marginal ADD re-evaluation / opportunity-cost contract, not G97 rollback.

ADD_REQUIRES_FULL_INCREMENTAL_CAPITAL_COMPETITION = YES

ACTUAL_ADD_PATH_PERFORMS_FULL_COMPETITION = PARTIAL

ADD_VS_NEW_BUY_COMPETITION_PRESENT = YES

ADD_VS_OTHER_ADD_COMPETITION_PRESENT = PARTIAL

ADD_VS_CASH_COMPETITION_PRESENT = YES

## Capital Displacement

Provable paired BUY displacement events through `2023-04-03`: 26 date-level events.

Representative early displacement candidates:

| Date | Post-repair-only BUY | Baseline-only BUY | Classification |
|---|---|---|---|
| 2022-11-21 | 76470 `400 @ 26` | none; baseline had same 35210/58030 | G97 incremental deployment, not direct same-day displacement |
| 2022-12-07 | 67210 `200 @ 147` | 37790 `100 @ 230` | ASSOCIATED_NOT_PROVEN |
| 2022-12-08 | 37790 `100 @ 163` | 61440 `100 @ 1500` | ASSOCIATED_NOT_PROVEN |
| 2022-12-09 | 75590 `100 @ 1376` | 18260 `100 @ 444` | ASSOCIATED_NOT_PROVEN |
| 2023-01-11 | 94220 `100 @ 1909` | 29980 `100 @ 411.6`, 42630 `100 @ 1247` | ASSOCIATED_NOT_PROVEN |
| 2023-01-24 | 30860 `100 @ 1191` | 36070 `100 @ 347`, 77710 `400 @ 91` | ASSOCIATED_NOT_PROVEN |

These are real path differences, but exact causal displacement cannot always be proven because prior holdings, cash, and pending state diverged before those dates.

PROVABLE_CAPITAL_DISPLACEMENT_EVENT_COUNT = 26

Most are classified as `ASSOCIATED_NOT_PROVEN`, not as invalid displacement.

## Position Path Dependence

Holdings diverged materially after first divergence:

| Date | Baseline notable holdings | Post-repair notable holdings |
|---|---|---|
| 2022-12-06 | includes 67210, no 76470 | includes 76470 1,700, no 67210 |
| 2022-12-21 | includes 35620, 61440 | includes 31500, 76470 2,700 |
| 2023-01-04 | includes 35620, 61440 | includes 76470 3,600 |
| 2023-03-22 | includes 31750, 57810 | includes 43880, 94320 |
| 2023-04-03 | includes 51360, 68980 | includes 43880, 51370, 94320 |

Attribution confidence:

- DIRECT_RECONSIDERATION_POSITION_ATTRIBUTION = DERIVABLE_PARTIAL
- RECONSIDERATION_ADD_ATTRIBUTION = DERIVABLE_PARTIAL
- DISPLACEMENT_ATTRIBUTION = ASSOCIATED_NOT_PROVEN
- PATH_DEPENDENCE_ATTRIBUTION = CONFIRMED
- UNEXPLAINED_ATTRIBUTION = DERIVABLE_PARTIAL

Direct G97 initial fill notional was only `44,980`, while equity divergence reached `-184,980` by `2023-04-03`. The dominant effect is downstream path dependence, not direct reconsideration entry loss.

## Architecture Assessment

G97/G99/G102/G104 repaired real connectivity gaps:

- residual reconsideration row reached canonical competition
- lot context was present
- PC discrete authority was present
- PS/Runtime consumed positive executable quantity
- Submit/fill materialized actual orders

The current evidence does not justify rolling back G97 solely because this window performed worse. The repair is architecturally valid in the sense that previously dead-ended valid residual rows now participate.

However, restored connectivity exposed a second-order issue: repeated ADD capital can accumulate through normal ADD semantics after a reconsideration entry, and the evidence is only partial that each later increment is evaluated against a full portfolio-level opportunity-cost contract robust enough for path-dependent capital displacement.

RECONSIDERATION_CONNECTIVITY_REPAIR_ARCHITECTURALLY_VALID = YES

PRIMARY_DIVERGENCE_ROOT_CAUSE = C

SECONDARY_DIVERGENCE_ROOT_CAUSES = E, D

Interpretation:

- C = ADD bypasses or incompletely performs capital competition, in the repeated marginal ADD sense.
- E = capital displacement/opportunity-cost contract incomplete.
- D = repeated ADD marginal value not re-evaluated canonically enough for path-dependent scaling.

This is not evidence for:

- B: reconsideration candidate receives unintended priority
- F: target-weight/concentration cap breach
- G: Cash competition defect
- H: campaign/re-entry state interaction defect

## Repairability

REPAIR_REQUIRED = PARTIAL

SAFE_NARROW_REPAIR_POSSIBLE = PARTIAL

Narrow next boundary:

- Producer: Portfolio Construction / ADD incremental capital competition evidence
- Consumer: Position Sizing / Runtime Planning only after PC has selected incremental ADD quantity
- Missing contract: repeated ADD marginal-capital opportunity-cost re-evaluation against NEW_BUY, other ADD, Cash, incumbent concentration, and residual budget after prior path divergence
- Affected semantics: ADD incremental capital prioritization only
- Unaffected semantics: G97 participation, optional Cash, weak-tail deferral, lot feasibility, Safety, strategy caps, normal BUY, SELL independence, campaign lifecycle, G110 campaign propagation

No numerical tuning or symbol-specific exception is supported by G111.

G93_DEAD_END_REINTRODUCTION_ALLOWED = NO

## Required Outputs

POST_REPAIR_RUN_ID = runtime-test-historical-extended-smoke-20260825T072702567342Z

BASELINE_RUN_ID = runtime-test-historical-extended-smoke-20260824T055234719725Z

BASELINE_IDENTITY_CONFIRMED = YES

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_DATE = 2022-11-21

FIRST_ACTUAL_PORTFOLIO_DIVERGENCE_SYMBOL = 76470

RECONSIDERATION_DERIVED_CAMPAIGN_COUNT = 3

76470_INITIAL_ENTRY_CAUSED_BY_RECONSIDERATION = YES

76470_LATER_SCALE_CAUSED_BY_EXISTING_ADD_PATH = YES

76470_MAX_WEIGHT = 9.57%

CAPITAL_COMPETITION_DEFECT_COUNT = 0 confirmed G97-specific defects

PROVABLE_CAPITAL_DISPLACEMENT_EVENT_COUNT = 26

RECONSIDERATION_PROVENANCE_CHANGES_FUTURE_PRIORITY = NO

UNINTENDED_RECONSIDERATION_PRIVILEGE_CONFIRMED = NO

ADD_REQUIRES_FULL_INCREMENTAL_CAPITAL_COMPETITION = YES

ACTUAL_ADD_PATH_PERFORMS_FULL_COMPETITION = PARTIAL

RECONSIDERATION_CONNECTIVITY_REPAIR_ARCHITECTURALLY_VALID = YES

PRIMARY_DIVERGENCE_ROOT_CAUSE = C

SECONDARY_DIVERGENCE_ROOT_CAUSES = E, D

POST_HOC_OUTCOME_USED_AS_DECISION_AUTHORITY = NO

REPAIR_REQUIRED = PARTIAL

SAFE_NARROW_REPAIR_POSSIBLE = PARTIAL

CODE_CHANGED = NO

CONFIG_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

RUN_MUTATED = NO

## Final Decision

G111_PERFORMANCE_DIVERGENCE_MIXED_CAUSES_REQUIRE_TARGETED_FOLLOWUP
