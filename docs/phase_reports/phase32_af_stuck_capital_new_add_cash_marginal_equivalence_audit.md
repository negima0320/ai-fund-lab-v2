# Phase32-AF — Stuck Capital + NEW/ADD/Cash Marginal Capital Equivalence Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted completed measurement window: `2022-10-03` through `2023-10-10`
- Trusted business days used: `252`
- Current run state may contain later recovery/replay state, but this audit intentionally excludes dates after `2023-10-10`.
- This is a READ-ONLY performance architecture audit.

No source, config, runtime state, Strategy parameter, threshold, weight, scoring, or cash-policy changes were made.

## Evidence Used

- Run artifacts under `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily`
- `run_state.json`, filtered to business dates `<= 2023-10-10`
- Daily artifacts:
  - `strategy/portfolio_construction.json`
  - `strategy/position_sizing.json`
  - `strategy/runtime_planning.json`
  - `position_management/pm_decisions.json`
  - `execution/fills.json`
  - `current_valuation_refresh/valuation_projection.json`
  - `positions/position_campaigns.json`
  - `strategy/corporate_event.json`
  - `data_readiness/data_readiness.json`
  - `submit/runtime_manifest.json`
- Current source:
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- Architecture / SoT:
  - `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
  - `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`

Historical profitability and future outcomes were not used to select parameters, thresholds, weights, or Strategy behavior. The post-hoc ADD fill characterization below is explicitly diagnostic only.

## Part A — Stuck Capital / Unresolved Position Accumulation

### Findings

No material stuck-capital mechanism was reproduced inside the trusted 252BD window.

Observed unresolved/trapped-capital indicators through `2023-10-10`:

| Indicator | Count / Value |
| --- | ---: |
| `corporate_event.event_count` | `0` |
| open campaign block events with `REVIEW_REQUIRED` / `corporate_action_event_not_resolved` / `SAFETY_MISSING` / broker unresolved terms | `0` |
| non-ready effective data-readiness component statuses | `0` |
| PM decisions with unresolved safety/corporate-action/provenance terms | `0` |
| submit days with blocked batch guard in trusted window | `0` |
| blocked capital x duration from unresolved positions | `0` |
| peak trapped fraction | `0%` |

Valuation plateau window context:

| Window | First Snapshot | Last Snapshot |
| --- | --- | --- |
| Apr-Oct 2023 | `2023-04-03`: cash `116,080`, market value `1,497,700`, equity `1,613,780`, positions `9` | `2023-10-10`: cash `816,580`, market value `837,970`, equity `1,654,550`, positions `4` |

Average cash fraction across Apr-Oct 2023 was approximately `23.2%`, with a max observed cash fraction of approximately `66.6%`. This is not evidence of trapped position capital. The plateau is better explained by capital deployment/competition semantics and realized position turnover, not unresolved corporate-action or safety blocks inside the trusted window.

### Classification

- Stuck capital materiality: `NO`
- Unresolved positions accumulate: `NO`
- Plateau relevance: `NEGLIGIBLE`
- Repair required for stuck capital: `NO_REPAIR`

## Part B — Where NEW / ADD / Cash Competition Is Decided

The final NEW/ADD/Cash capital competition is owned by Portfolio Construction.

Current source shows `build_capital_competition_framework(...)` builds competitors from PC members, assigns `competitor_type`, `target_weight`, `requested_weight`, `accepted_weight`, opportunity quality, ADD evidence, and sizing evidence. The market candidate / Cash interaction is then computed by `_market_candidate_cash_interaction(...)`.

Important current-source boundaries:

- `build_capital_competition_framework` starts at `portfolio_construction.py:2682`.
- Competitor type and accepted weight are materialized at `portfolio_construction.py:2711-2729`.
- ADD competitor evidence is materialized at `portfolio_construction.py:2733-2745`.
- Cash evidence is owned by PC and records `quantity_authority_owner = POSITION_SIZING` plus no market/risk recomputation at `portfolio_construction.py:6283-6329`.
- `_market_candidate_cash_interaction` starts at `portfolio_construction.py:6334`.
- Competitor interaction classes are assigned from risk pacing and canonical opportunity quality at `portfolio_construction.py:6344-6372`.
- Cash is added as an explicit `CASH_OPTIONALITY` competitor at `portfolio_construction.py:6389-6408`.
- If deployable securities exist, the winner is selected by interaction class, then accepted weight, then symbol at `portfolio_construction.py:6409-6422`.

The final interaction evidence is serialized in PC as `capital_competition.market_candidate_cash_interaction`. Position Sizing and Runtime consume this authority; Runtime must not recompute ranking, cash preference, target weight, or quantity.

## Part C — Same Economic Scale Test

### NEW vs ADD

| Test | Result |
| --- | --- |
| Same decision owner | `YES`, Portfolio Construction |
| Same broad competitor set | `YES`, both can appear in `market_candidate_cash_interaction` |
| Same directionality | `PARTIAL`, stronger classes and accepted weights tend to be favored |
| Same economic quantity | `NO` |
| Same range / calibration basis | `NO` |
| Same marginal-yen interpretation | `NO` |
| Same investment horizon basis | `UNCONFIRMED / NOT EXPLICIT` |

NEW and ADD are compared in the same PC framework, but they are not yet reduced to a common high-resolution marginal capital value unit.

The high-resolution architecture explicitly records that:

- NEW_BUY, BUY_ADD, and Cash do not yet share a common high-resolution marginal capital value unit.
- Security quality is not equal to marginal capital value.
- BUY_ADD value should start from PM ADD intent, campaign continuation, expected-edge evidence, current position state, headroom, Cash competition, and lot feasibility.
- High-resolution marginal capital comparison belongs to a future PC-owned Capital Value Authority.

Current contract also states that this high-resolution authority is architecture-only and not yet implemented as `canonical_high_resolution_marginal_capital_value.v1`.

### Cash

| Test | Result |
| --- | --- |
| Explicit Cash competitor exists | `YES` |
| Cash competes inside PC | `YES` |
| Cash has same marginal-value scale as NEW/ADD | `NO` |
| Cash can beat positive security candidates without calibrated marginal-yen comparison | `YES` |
| Cash classification | `NOT_SEMANTICALLY_COMPARABLE` |

Cash is not absent. It is explicitly represented, but its authority is optionality / risk / residual-capital semantics rather than the same calibrated marginal capital value unit used by NEW/ADD.

### Classification

- NEW and ADD same economic scale: `NO`
- Cash comparable scale: `NO`
- NEW structurally favored: `NOT_PROVEN / NOT_DIRECTLY_COMPARABLE`
- ADD structurally suppressed: `NOT_PROVEN_AS_ACTION_TYPE_BIAS`
- Core issue: `MARGINAL_CAPITAL_SEMANTIC_GAP_CONFIRMED`

## Part D — Actual 252BD Funnel

### PM Decisions

| PM Decision | Count |
| --- | ---: |
| `HOLD` | `1,729` |
| `REDUCE` | `663` |
| `EXIT` | `238` |
| `ADD` | `118` |

### PC Competitor Set

| Competitor Type | Count |
| --- | ---: |
| `NEW_BUY` | `5,575` |
| `ADD` | `99` |
| `CASH_OPTIONALITY` | `252` |

### PC Daily Winner Type

| Winner Type | Count |
| --- | ---: |
| `CASH_OPTIONALITY` | `170` |
| `NEW_BUY` | `82` |
| `ADD` | `0` |

On `82` days, both ADD and NEW competitors were present. Winners on those days were:

| Winner Type | Count |
| --- | ---: |
| `CASH_OPTIONALITY` | `55` |
| `NEW_BUY` | `27` |
| `ADD` | `0` |

No ADD-only days were observed.

### ADD Competitor Outcomes

| ADD Attribute | Count |
| --- | ---: |
| ADD rows | `99` |
| selected | `11` |
| quality `BLOCKED` | `47` |
| quality `INSUFFICIENT` | `30` |
| quality `COMPARABLE_MARGINAL` | `22` |
| interaction `BLOCKED` | `50` |
| interaction `FAIL_CLOSED` | `38` |
| interaction `CASH_PREFERRED` | `10` |
| interaction `DEPLOY_ELIGIBLE` | `1` |

Top ADD reason codes:

| Reason | Count |
| --- | ---: |
| `BLOCKED_NON_ELIGIBLE` | `47` |
| `INSUFFICIENT_FAIL_CLOSED` | `30` |
| `CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED` | `15` |
| `CAUTIOUS_MARGINAL_LOST_TO_CASH` | `15` |
| `competitor_not_selected_by_current_pc_context` | `11` |
| `GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED` | `4` |
| `GRADUAL_MARGINAL_LOST_TO_CASH` | `4` |
| `NORMAL_COMPARABLE_MARGINAL_DEPLOY` | `3` |
| `NORMAL_DEPLOY_ALLOWED` | `3` |

### Runtime / Fill Funnel

| Runtime Plan Type | Count |
| --- | ---: |
| `NO_ORDER` | `5,275` |
| `NO_ACTION` | `1,836` |
| `BUY_NEW` | `807` |
| `SELL_EXIT` | `394` |
| `BUY_ADD` | `11` |

Execution fills:

| Fill Type | Count |
| --- | ---: |
| `BUY BUY_NEW` | `395` |
| `BUY BUY_ADD` | `9` |
| `SELL SELL_EXIT` | `391` |
| `SELL REDUCE` | `40` |

The 9 BUY_ADD fills were:

| Date | Symbol | Qty | Price |
| --- | --- | ---: | ---: |
| `2022-10-06` | `94340` | `100` | `147.8` |
| `2022-10-12` | `94340` | `100` | `146.4` |
| `2022-10-13` | `94340` | `100` | `145.7` |
| `2022-11-01` | `94320` | `100` | `163.9` |
| `2022-11-29` | `76470` | `100` | `28.0` |
| `2022-11-30` | `76470` | `100` | `27.0` |
| `2022-12-01` | `76470` | `100` | `28.0` |
| `2022-12-02` | `76470` | `100` | `26.0` |
| `2022-12-06` | `76470` | `100` | `27.0` |

### Why Only 9 BUY_ADD Fills

The observed funnel is:

```text
PM ADD decisions: 118
-> PC ADD competitors: 99
-> PC selected ADD competitors: 11
-> Runtime BUY_ADD positive plans: 11
-> BUY_ADD fills: 9
```

First loss-boundary classification from PM ADD to fill:

| First Boundary | Count |
| --- | ---: |
| PC value insufficient / non-eligible | `50` |
| ADD tier insufficient | `30` |
| PM ADD did not materialize as PC ADD competitor | `19` |
| BUY_ADD fill | `9` |
| lost to Cash | `7` |
| Runtime/Submit block | `2` |
| other | `1` |

The two Runtime-positive but non-filled BUY_ADD cases were:

- `2022-10-11 94340`: pending item reached Submit but required item-scoped review because reserved notional exceeded dynamic cash capacity.
- `2022-10-28 94320`: ADD remained as defeated competitor lineage with `GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED` / `GRADUAL_MARGINAL_LOST_TO_CASH`; no 94320 order/fill was created.

Therefore the low BUY_ADD count is not caused by stuck capital. It is mainly caused by ADD eligibility/evidence gates, ADD tier insufficiency, Cash preference, and PC/PS/Runtime/Submit narrowing.

## Part E — Representative Actual Cases

### `2022-11-29`: NEW Beats ADD

- PC winner: `NEW_BUY 76920`
- ADD `76470`:
  - quality `COMPARABLE_MARGINAL`
  - accepted weight `0.002405`
  - status `COMPETITOR_SELECTED`
  - interaction `DEPLOY_ELIGIBLE`
- NEW `76920`:
  - quality `COMPARABLE_HIGH`
  - accepted weight `0.014957`
  - status `COMPETITOR_SELECTED`
  - interaction `DEPLOY_ELIGIBLE`

This is reasonable under current coarse PC semantics, but it is not proof that NEW and ADD were compared on calibrated marginal-yen expected value.

### `2022-10-06`: Cash Beats NEW and ADD

- PC winner: `CASH_OPTIONALITY`
- ADD `94340`:
  - quality `COMPARABLE_MARGINAL`
  - accepted weight `0.013786`
  - interaction `CASH_PREFERRED`
- Several NEW candidates were also selected but lost to Cash.
- Cash accepted weight was approximately `0.078167`, with optionality / marginal opportunity / lot residual reasons.

This shows Cash is active and binding, but not on the same explicit high-resolution marginal-value scale.

### `2023-04-03`: Cash Beats Multiple NEW Candidates; ADD Blocked

- PC winner: `CASH_OPTIONALITY`
- ADD `43880`: `BLOCKED_NON_ELIGIBLE`
- NEW candidates were present and selected but `CASH_PREFERRED`.
- Cash reasons included recovery-incomplete optionality.

Again, this supports Cash optionality as a binding PC competitor, not unresolved capital trapping.

## Part F — ADD Double Penalty / Post-Entry Confirmation Evidence

### Double Penalty

Redundant ADD double-penalty is not proven.

Observed ADD narrowing is mostly attributable to distinct authorities:

- PM ADD intent
- BUY-quality / adaptive quality evidence
- PC opportunity quality and current candidate selection
- risk pacing
- Cash optionality
- lot and quantity feasibility
- Runtime/Submit capacity checks

Some semantics can be repetitive in effect, especially when a marginal/weak ADD candidate is both lower-quality and more likely to lose to Cash. However, the evidence does not prove the same signal is being applied twice as an unintended duplicate penalty.

Classification:

- `REDUNDANT_PENALTY_NOT_PROVEN`
- `ORTHOGONAL_GUARDS_WITH_SEMANTIC_COMPRESSION`

### Post-Entry Confirmation Evidence

Post-entry confirmation is used upstream in PM ADD evidence. Examples include PM ADD reason codes such as:

- `strong_trend_continuation`
- `opportunity_rank_still_high`
- `no_loss_averaging`

But current PC competition compresses this into coarse ADD opportunity classes and accepted-weight mechanics. It does not yet convert post-entry confirmation into a high-resolution marginal capital value unit comparable to NEW_BUY and Cash.

Classification:

- Post-entry confirmation valuation: `UNDERREPRESENTED`
- Repair urgency: `DESIGN_REQUIRED_BEFORE_ACTIVATION`, not emergency correctness repair

## Part G — Post-Hoc ADD Fill Characterization

This section is diagnostic only. It was not used to infer parameter, threshold, weight, or Strategy changes.

Approximate later-exit comparison for the 9 BUY_ADD fills:

| Symbol | ADD Date | ADD Price | Later Exit Price Used | Approx Per-Lot Result |
| --- | --- | ---: | ---: | ---: |
| `94340` | `2022-10-06` | `147.8` | `145.9` | `-190` |
| `94340` | `2022-10-12` | `146.4` | `145.9` | `-50` |
| `94340` | `2022-10-13` | `145.7` | `145.9` | `+20` |
| `94320` | `2022-11-01` | `163.9` | `150.0` | `-1,390` |
| `76470` | `2022-11-29` | `28.0` | `26.0` | `-200` |
| `76470` | `2022-11-30` | `27.0` | `26.0` | `-100` |
| `76470` | `2022-12-01` | `28.0` | `26.0` | `-200` |
| `76470` | `2022-12-02` | `26.0` | `26.0` | `0` |
| `76470` | `2022-12-06` | `27.0` | `26.0` | `-100` |

This indicates the actual accepted ADDs were not obviously missed runaway winners in this trusted window. It does not justify changing Strategy thresholds or weights.

## Repair / Design Implications

No narrow correctness repair is required for stuck capital or unresolved position accumulation.

A performance architecture change is justified only as a future marginal-capital semantic design step:

- introduce or shadow-test a PC-owned high-resolution marginal capital value authority;
- normalize NEW, ADD, and Cash into one comparable marginal-capital unit;
- value ADD as executable next-lot increments, not as incumbent campaign strength alone;
- preserve PM, Candidate AI, Market Quality, Risk Pacing, Safety, Position Sizing, and Runtime authority boundaries;
- keep Runtime as a consumer, not a recomputation authority;
- do not tune thresholds, weights, or cash policy from completed-run PnL.

Recommended next highest-value action:

```text
Design and run a read-only/shadow high-resolution marginal capital value comparator for NEW_BUY / BUY_ADD / Cash on existing artifacts, then audit whether it changes only capital semantics rather than Strategy parameterization.
```

## Classifications

| Question | Classification |
| --- | --- |
| Stuck capital materiality | `NO` |
| Unresolved positions accumulate | `NO` |
| NEW/ADD/Cash final decision owner | `PORTFOLIO_CONSTRUCTION` |
| NEW and ADD same economic scale | `NO` |
| Cash same comparable scale | `NO` |
| NEW structurally favored | `NOT_PROVEN / NOT_DIRECTLY_COMPARABLE` |
| ADD structurally suppressed | `NOT_PROVEN_AS_ACTION_TYPE_BIAS` |
| ADD double-penalized | `REDUNDANT_PENALTY_NOT_PROVEN` |
| Post-entry confirmation properly valued | `UNDERREPRESENTED` |
| Performance architecture change justified | `YES`, semantic design only |
| Strategy semantic change made in AF | `NO` |
| Code/config/runtime change made in AF | `NO` |

Overall classification:

```text
MARGINAL_CAPITAL_SEMANTIC_GAP_CONFIRMED
```

## Final Judgment

1. `IS_STUCK_CAPITAL_MATERIAL`: `NO`
2. `DO_UNRESOLVED_POSITIONS_ACCUMULATE`: `NO`
3. `WHERE_IS_NEW_ADD_CASH_COMPETITION_DECIDED`: `PORTFOLIO_CONSTRUCTION`, specifically `capital_competition.market_candidate_cash_interaction`
4. `ARE_NEW_AND_ADD_ON_THE_SAME_ECONOMIC_SCALE`: `NO`
5. `IS_CASH_ON_A_COMPARABLE_SCALE`: `NO`
6. `IS_NEW_STRUCTURALLY_FAVORED`: `NOT_PROVEN`; current evidence is `NOT_DIRECTLY_COMPARABLE` because no shared marginal-value unit exists
7. `IS_ADD_STRUCTURALLY_SUPPRESSED`: `NOT_PROVEN_AS_ACTION_TYPE_BIAS`; ADD is heavily narrowed by eligibility/evidence/Cash gates, but a hidden NEW-first priority was not found
8. `IS_ADD_DOUBLE_PENALIZED`: `REDUNDANT_PENALTY_NOT_PROVEN`; observed behavior is mostly orthogonal guards plus semantic compression
9. `IS_POST_ENTRY_CONFIRMATION_EVIDENCE_PROPERLY_VALUED`: `UNDERREPRESENTED`
10. `WHY_WERE_THERE_ONLY_9_BUY_ADD_FILLS`: PM produced `118` ADD decisions, PC materialized `99` ADD competitors, only `11` became selected positive Runtime BUY_ADD plans, and only `9` filled after Cash/eligibility/tier/Submit-capacity narrowing
11. `IS_ANY_PERFORMANCE_ARCHITECTURE_CHANGE_JUSTIFIED`: `YES`, a future high-resolution marginal capital value authority is justified; no Phase31/Phase32 Strategy parameter tuning is justified by this audit
12. `WHAT_IS_THE_NEXT_HIGHEST_VALUE_ACTION`: build a read-only/shadow NEW_BUY / BUY_ADD / Cash marginal-capital equivalence design and validate it on existing artifacts before any activation

Final classification:

```text
MARGINAL_CAPITAL_SEMANTIC_GAP_CONFIRMED
```
