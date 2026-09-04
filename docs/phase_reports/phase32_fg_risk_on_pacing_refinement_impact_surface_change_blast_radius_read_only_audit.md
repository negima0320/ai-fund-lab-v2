# Phase32-FG - Risk-On Pacing Refinement Impact Surface / Change-Blast-Radius READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Primary period: `2023-03-01` through `2023-05-08`
- Run observation used: run was `RUNNING`, completed through `2023-05-12`, `next_job = 2023-05-15:market_refresh`.
- Current source identity: `04ded4ca66a9a6308be2bc395c0e26ba1a98b8bf`
- Evidence used: target-run Portfolio Construction, Position Sizing, Runtime Planning / Strategy Authority, fills, current valuation artifacts, Phase32-FE report, Phase32-FF report, and current Architecture SoT.
- Production changed: NO
- SHADOW changed: NO
- Config/schema changed: NO
- Target run mutated: NO
- Runtime state mutated: NO
- fresh-run/resume/replay/recover executed: NO
- Future return/PnL/MFE/MAE/final outcome used for impact judgment: NO

## Executive Summary

Phase32-FE/FF identified a Risk-on pacing semantic concern, not a Runtime correctness defect: during `CAUTIOUS_DEPLOYMENT` and `GRADUAL_REDEPLOYMENT`, valid-but-marginal opportunities can still receive positive PC weight and actual BUY fills.

The direct impact surface is material but bounded. In the target period, actual BUY fills totalled 75. Of those, 48 fills, notional `4,190,860`, were `CAUTIOUS_DEPLOYMENT` / `GRADUAL_REDEPLOYMENT` plus canonical `COMPARABLE_MARGINAL`. Those 48 fills are the direct candidate-level blast radius of any refinement that makes marginal-vs-Cash evidence more binding.

The earliest potentially affected date is `2023-03-01`. The largest affected day is `2023-04-25`, with 6 potentially affected BUY_NEW fills and `527,020` notional. Therefore any Production implementation would require a new fresh validation run for portfolio comparability; same-run continuation would not represent the new decision path.

Selected change-risk class: `C. MATERIAL_PORTFOLIO_PATH_CHANGE`.

## Consumer Reference Graph

| Evidence / field | Producer / owner | Current consumer behavior | Refinement impact surface |
| --- | --- | --- | --- |
| `canonical_opportunity_quality_class` | `strategy.marginal_capital_value.classify_opportunity_quality` | Preserves `STRONG`, `COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, `WEAK_VALID`, etc. It records PIT and no-future flags. | Direct. A refinement would likely consume this class more sharply in PC/cash binding. |
| `COMPARABLE_HIGH` | MCV opportunity quality | Mapped to legacy `ELIGIBLE_STRONG`. Can pass CAUTIOUS/GRADUAL sufficiency; cash interaction can still be `CASH_PREFERRED` in CAUTIOUS if symbol evidence is missing. | Direct but limited. Most should remain deployable if current confirmation is strong; weakly confirmed high rows are design-dependent. |
| `COMPARABLE_MARGINAL` | MCV opportunity quality | Mapped to legacy `ELIGIBLE_COMPARABLE`; Risk Pacing sufficiency currently treats it as allowed in CAUTIOUS/GRADUAL. Cash interaction often says `CASH_PREFERRED`. | Direct primary blast radius. |
| `marginal_capital_value_class` | MCV compatibility layer | `COMPARABLE_HIGH -> ELIGIBLE_STRONG`; `COMPARABLE_MARGINAL/WEAK_VALID -> ELIGIBLE_COMPARABLE`. | Direct. The compatibility compression is the first information-loss boundary for effective risk pacing. |
| `ELIGIBLE_STRONG` | MCV compatibility class | Considered sufficient by PC Risk Pacing. | Mostly unaffected, except if future design distinguishes weakly confirmed `COMPARABLE_HIGH`. |
| `ELIGIBLE_COMPARABLE` | MCV compatibility class | Considered sufficient by PC Risk Pacing for CAUTIOUS/GRADUAL. | Direct. A refinement would stop treating all comparable rows equally. |
| `risk_pacing_intent` | Portfolio Policy | Consumed by PC, BUY Quality, and Position Sizing as consumer of PC targets. SoT says CAUTIOUS requires stronger contemporaneous evidence and GRADUAL uses confirmed competitors. | Direct. Target scope is CAUTIOUS/GRADUAL; NORMAL remains ordinary competition. |
| `canonical_cash_competitor_evidence` | PC | Produces optionality/Cash evidence from market quality, risk pacing, opportunity distribution, residual/capital context. | Direct. Refinement would make Cash participation/deferral more binding for marginal rows. |
| `market_candidate_cash_interaction` | PC | Produces `DEPLOY_ELIGIBLE`, `SELECTIVE_COMPETITION`, `CASH_PREFERRED`, `BLOCKED`, `FAIL_CLOSED`. It already marks CAUTIOUS/GRADUAL `COMPARABLE_MARGINAL` as `CASH_PREFERRED`. | Direct. Existing evidence is sufficient for a future design to bind without new PIT data. |
| `CASH_PREFERRED` | PC interaction evidence | Not an automatic hard zero after G81/G86/G90. It must pass PC participation-vs-deferral resolution. Rows may remain positive if `CASH_PREFERRED_PARTICIPATION_VALID`. | Direct. The blast radius depends on whether future design reduces participation or defers to zero. |
| accepted PC `target_weight` | PC | Final portfolio allocation authority. It may contain positive weight for `CASH_PREFERRED` marginal rows. | Direct. Any refinement changes target weights first here. |
| Position Sizing quantity | Position Sizing | Converts PC target/increment to notional and lots. Does not choose capital winner. | Secondary/direct mechanical effect after PC target changes. |
| Runtime Planning / Pending | Runtime Planning / Strategy Authority | Maps authoritative PS quantity into pending orders; carries MCV/campaign/provenance; does not redecide Cash/quality. | Secondary. It should only reflect changed upstream PC/PS output. |
| Submit / Execution / Fill | Runtime v2 | Executes approved pending items. | Secondary. Fill count/notional changes only if upstream pending set changes. |

Source anchors:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`: Risk Pacing owner/consumer and intent semantics state that CAUTIOUS needs stronger contemporaneous evidence and GRADUAL should use confirmed competitors.
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`: PC owns final capital winner; PS must not reinterpret rank/score/Cash; `CASH_PREFERRED` requires PC-owned participation-vs-deferral resolution and is not an automatic blanket exclusion.
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`: canonical quality classes are distinct, but compatibility maps `COMPARABLE_MARGINAL` to `ELIGIBLE_COMPARABLE`.
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`: `_risk_pacing_competitor_decision` treats `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE` as sufficient in CAUTIOUS/GRADUAL; `_interaction_result_for_quality` separately marks CAUTIOUS/GRADUAL `COMPARABLE_MARGINAL` as `CASH_PREFERRED`.
- `src/ai_fund_lab_v2/strategy/runtime_planning.py` and `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`: downstream layers carry authority lineage and quantities; they do not own risk-pacing or Cash winner decisions.

## Candidate Decision Blast Radius

Classification uses existing PIT evidence only. No new thresholds are introduced.

| Class | Definition | Observed impact |
| --- | --- | --- |
| A. unaffected strong | `STRONG` in CAUTIOUS/GRADUAL with deploy/selective evidence | Directly unaffected unless a future design incorrectly tightens strong cases. |
| B. unaffected comparable-high | `COMPARABLE_HIGH` with current confirmation | Mostly unaffected; 4 actual BUY_NEW fills in CAUTIOUS/GRADUAL, `266,230` notional. |
| C. marginal but stronger-confirmed | `COMPARABLE_MARGINAL` but healthy/robust/high-confidence evidence | Potentially reduced or retained depending design; e.g. `64240` on 3/22 and `69270` on 5/01. |
| D. ordinary marginal | `COMPARABLE_MARGINAL`, valid reduced allocation, mixed continuation | Potentially reduced. |
| E. fragile/unconfirmed marginal | `COMPARABLE_MARGINAL` with mixed/unresolved, acceptable/quantized, weak priority, or Cash-preferred evidence | Potentially zeroed or deferred to Cash. |
| F. already cash-defeated | `CASH_PREFERRED` with positive weight/fill today | Primary direct surface: 125 positive selected rows; 48 fills. |
| G. blocked/zero-weight | no positive selected weight or terminal/review state | No direct fill impact, but counts may shift path-dependently if capital is reallocated. |

## Potential Allocation Change Count

Positive PC-selected CAUTIOUS/GRADUAL rows in the observed scope:

| Category | Count | Interpretation |
| --- | ---: | --- |
| unchanged positive allocation | 7 | Strong / comparable-high positive rows likely survive a quality-aware refinement. |
| reduced allocation candidate | 115 | `COMPARABLE_MARGINAL` positive rows whose current interaction was not clean final `CASH_PREFERRED` in the extracted interaction surface, or whose participation-vs-deferral outcome is design-dependent. |
| zero-allocation candidate | 125 | `COMPARABLE_MARGINAL` positive rows with `CASH_PREFERRED` interaction; if future design makes Cash-preferred binding harder, these are the cleanest zero/defer candidates. |
| uncertain design-dependent | 15 | Positive ADD rows whose top-level canonical class was not materialized in the same extraction path; direct fill evidence only confirms 2 affected ADD executions. |

This is an impact envelope, not a Production rule. `CASH_PREFERRED` is not currently a blanket hard zero by SoT.

## Potential Fill Change Count

Actual BUY fills, `2023-03-01` through `2023-05-08`:

| Risk intent / quality | BUY_NEW | BUY_ADD | Notional | Impact |
| --- | ---: | ---: | ---: | --- |
| CAUTIOUS/GRADUAL `STRONG` or `COMPARABLE_HIGH` | 6 | 0 | 347,530 | definitely or likely unaffected |
| CAUTIOUS `COMPARABLE_MARGINAL` | 34 | 2 | 2,839,530 | potentially reduced/suppressed |
| GRADUAL `COMPARABLE_MARGINAL` | 12 | 0 | 1,351,330 | potentially reduced/suppressed |
| NORMAL `COMPARABLE_HIGH` / `COMPARABLE_MARGINAL` | 21 | 0 | 1,731,730 | no direct impact if refinement is limited to CAUTIOUS/GRADUAL |

Required counts:

- `POTENTIALLY_AFFECTED_BUY_NEW_COUNT = 46`
- `POTENTIALLY_AFFECTED_BUY_ADD_COUNT = 2`
- `POTENTIALLY_AFFECTED_NOTIONAL = 4,190,860`

The FF ADD-specific observation is preserved: the affected BUY_ADD sample is small but real, 2 fills and `208,700` notional.

## Date-Level Impact

`FIRST_POTENTIALLY_AFFECTED_DATE = 2023-03-01`

`AFFECTED_DECISION_DAY_COUNT = 23`

| Date | Potentially affected BUY count | BUY_NEW | BUY_ADD | Potentially affected notional |
| --- | ---: | ---: | ---: | ---: |
| 2023-03-01 | 3 | 3 | 0 | 218,800 |
| 2023-03-10 | 1 | 1 | 0 | 48,000 |
| 2023-03-13 | 2 | 2 | 0 | 207,400 |
| 2023-03-14 | 2 | 2 | 0 | 96,500 |
| 2023-03-15 | 2 | 2 | 0 | 197,600 |
| 2023-03-16 | 2 | 2 | 0 | 101,300 |
| 2023-03-17 | 1 | 1 | 0 | 159,800 |
| 2023-03-20 | 1 | 1 | 0 | 20,500 |
| 2023-03-22 | 2 | 2 | 0 | 284,200 |
| 2023-03-27 | 1 | 1 | 0 | 178,400 |
| 2023-03-28 | 1 | 1 | 0 | 52,000 |
| 2023-03-30 | 2 | 1 | 1 | 151,180 |
| 2023-03-31 | 1 | 1 | 0 | 156,750 |
| 2023-04-04 | 1 | 0 | 1 | 85,800 |
| 2023-04-10 | 1 | 1 | 0 | 53,600 |
| 2023-04-11 | 4 | 4 | 0 | 149,330 |
| 2023-04-21 | 2 | 2 | 0 | 298,800 |
| 2023-04-24 | 3 | 3 | 0 | 247,000 |
| 2023-04-25 | 6 | 6 | 0 | 527,020 |
| 2023-04-26 | 2 | 2 | 0 | 264,700 |
| 2023-04-27 | 3 | 3 | 0 | 221,800 |
| 2023-05-01 | 2 | 2 | 0 | 370,400 |
| 2023-05-02 | 3 | 3 | 0 | 99,980 |

- Max potentially affected BUY count/day: 6 on `2023-04-25`.
- Max potentially affected notional/day: `527,020` on `2023-04-25`.

Focus dates:

| Date | Impact envelope |
| --- | --- |
| `2023-03-22` | 2 marginal BUY_NEW fills, `284,200`; one strong BUY_NEW `67750` is likely unaffected. |
| `2023-03-27` | 1 marginal BUY_NEW fill, `178,400`; GRADUAL / Cash-preferred. |
| `2023-04-11` | 4 marginal BUY_NEW fills, `149,330`; 2 comparable-high BUY_NEW fills, `174,300`, likely survive a refined high/strong path. |
| `2023-04-24` | 3 marginal BUY_NEW fills, `247,000`; one strong BUY_NEW `69270`, `57,000`, likely unaffected. |
| `2023-05-01` | 2 marginal BUY_NEW fills, `370,400`; both GRADUAL / Cash-preferred. |

## 2023-04-11 Impact Envelope

Context: `CORRECTION`, `SHORT_TERM_BREADTH_BREAKDOWN`, `CAUTIOUS_DEPLOYMENT`, target gross `0.90`.

| Symbol | Notional | Quality | MCV | Cash interaction | Impact envelope |
| --- | ---: | --- | --- | --- | --- |
| `27210` | 43,500 | `COMPARABLE_HIGH` | `ELIGIBLE_STRONG` | `CASH_PREFERRED` | likely unaffected or reduced only if future design demands stronger high-row evidence; not a primary suppression case. |
| `45980` | 130,800 | `COMPARABLE_HIGH` | `ELIGIBLE_STRONG` | `CASH_PREFERRED` | likely unaffected or reduced only if future design treats CAUTIOUS high rows with Cash preference strictly. |
| `94340` | 30,060 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | potentially suppressed; mixed momentum and acceptable tick state. |
| `54010` | 59,900 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | potentially suppressed; mixed momentum, acceptable tick, negative 20d momentum. |
| `45860` | 33,400 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | design-dependent/reduced; robust tick but mixed momentum. |
| `44920` | 25,970 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | design-dependent/reduced; robust tick and positive 20d momentum but mixed momentum. |

Strict Cash-preferred binding envelope for 4/11 marginal rows: cash +`149,330`, exposure roughly -10.16 percentage points versus actual EOD equity. If comparable-high rows were also reduced, maximum direct same-day BUY impact would be `323,630`, but that is a broader design envelope and not justified as the minimal marginal-quality refinement.

## 2023-03-22 Impact Envelope

Context: `RANGE`, `CONFLICTED_MARKET_STRUCTURE`, `CAUTIOUS_DEPLOYMENT`.

| Symbol | Notional | Quality | MCV | Cash interaction | Impact envelope |
| --- | ---: | --- | --- | --- | --- |
| `67750` | 24,300 | `STRONG` | `ELIGIBLE_STRONG` | `SELECTIVE_COMPETITION` | definitely unaffected under a marginal-only refinement. |
| `43880` | 119,200 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | design-dependent/reduced; robust tick and high 20d momentum, but mixed momentum classification. |
| `64240` | 165,000 | `COMPARABLE_MARGINAL` | `ELIGIBLE_COMPARABLE` | `CASH_PREFERRED` | design-dependent/reduced; stronger-within-marginal candidate with healthy momentum and robust tick. |

Strict marginal Cash-preferred envelope for 3/22: cash +`284,200`, exposure roughly -22.57 percentage points versus actual EOD equity.

## BUY_ADD Impact

The same semantic concern applies to BUY_NEW and BUY_ADD because both compete for marginal capital and both are PC-owned allocations before PS quantity conversion. However, observed direct ADD blast radius is much smaller:

- CAUTIOUS/GRADUAL `COMPARABLE_MARGINAL` BUY_ADD fills: 2
- Notional: `208,700`
- Dates: `2023-03-30` and `2023-04-04`

Refinement should be common at the marginal-capital competition / Cash interaction boundary, with ADD-specific guardrails preserved:

- PM ADD intent remains the source of ADD eligibility.
- G129 positive BUY_ADD quantity remains order-increment scoped.
- PC may reduce/defer an ADD allocation only through the same PC-owned capital competition authority used for BUY_NEW.
- Runtime must not recreate an ADD from pre-binding target or residual mechanics.

## Cash / Exposure Secondary Effects

If direct affected BUYs are reduced or deferred, the immediate mechanical effect is higher EOD Cash and lower EOD exposure by the notional not deployed. This is a same-day accounting envelope, not a future-performance claim.

Focus-date maximum marginal-only effects:

| Date | Affected notional | EOD equity basis | Max cash increase | Max exposure reduction |
| --- | ---: | ---: | ---: | ---: |
| `2023-03-22` | 284,200 | 1,259,450 | +284,200 | -22.57 pp |
| `2023-03-27` | 178,400 | 1,348,470 | +178,400 | -13.23 pp |
| `2023-04-11` | 149,330 | 1,469,730 | +149,330 | -10.16 pp |
| `2023-04-24` | 247,000 | 1,486,690 | +247,000 | -16.61 pp |
| `2023-05-01` | 370,400 | 1,579,060 | +370,400 | -23.46 pp |

Full observed-period maximum: `2023-04-25`, cash +`527,020`, exposure roughly -34.34 pp versus actual EOD equity if every affected marginal BUY on that date were deferred.

## Path Dependency Classification

| Path | Classification | Reason |
| --- | --- | --- |
| available cash | DIRECT | Reduced/deferred BUY immediately changes cash. |
| affordability | SECONDARY | Higher cash may permit later BUYs that were previously unaffordable. |
| BUY_NEW rank | NO_IMPACT for rank itself; PATH_DEPENDENT for realized membership | Refinement should not mutate candidate rank, but later portfolio state can alter feasible realized buys. |
| BUY_ADD rank | NO_IMPACT for rank itself; PATH_DEPENDENT for realized ADD opportunities | ADD opportunity rank remains PIT evidence; later holdings/headroom can diverge. |
| MCV | DIRECT if refined there; otherwise direct consumer input to PC | The compression boundary is MCV compatibility class. |
| cap/headroom | SECONDARY | Fewer fills leaves more single-name and gross headroom later. |
| position count | DIRECT/SECONDARY | Same-day count may fall when BUYs are deferred; later count path changes. |
| campaign identity | PATH_DEPENDENT | Deferred BUY_NEW means campaigns may not be created; existing identity logic not directly changed. |
| PM lifecycle | PATH_DEPENDENT | Fewer/later positions changes future PM HOLD/REDUCE/EXIT population. |
| sell/exit timing | PATH_DEPENDENT | A position not opened cannot later sell; no immediate SELL rule change. |
| recent-exit guard generation | PATH_DEPENDENT | Different buy/sell lifecycle can change future recent-exit state. |
| Runtime Pending / Submit | SECONDARY | Pending items only change after PC/PS changes; Runtime remains mapper. |

`PATH_DEPENDENCY_MATERIAL = YES`

## Risk-Off Path Safety

SELL/REDUCE/EXIT paths should have `NO_DIRECT_IMPACT`. Risk Pacing SoT explicitly keeps Safety and SELL independence under CAUTIOUS deployment. A future implementation must preserve:

- PM SELL/REDUCE/EXIT authority.
- Corporate Action fail-closed behavior.
- Pending review item separation.
- Runtime Planning as mapper, not strategy redecider.
- Position Sizing as quantity converter, not capital winner.

`RISK_OFF_SELL_PATH_IMPACT = NO_DIRECT_IMPACT_EXPECTED`

## REENTRY / Recent-Exit Isolation

This impact surface does not require changing recent-exit guard semantics. REENTRY-as-current-decision history has already been removed/rebounded in prior phases; a Risk-on pacing refinement should consume only current-day candidate/opportunity/BQ/Entry/risk/Cash evidence.

`REENTRY_GUARD_PATH_IMPACT = PATH_DEPENDENT_ONLY`

## Architecture / Schema Impact

Minimal change surface:

- likely source-only change in `strategy.marginal_capital_value` and/or `strategy.portfolio_construction`;
- preserve existing canonical class fields;
- preserve existing `market_candidate_cash_interaction` and `canonical_cash_competitor_evidence`;
- make final PC participation-vs-deferral binding more quality-aware for CAUTIOUS/GRADUAL;
- do not change Strategy candidate selection, thresholds, weights, ranking, SELL, Runtime, Pending, Ledger, or accepted evidence validation semantics.

Schema:

- `SCHEMA_CHANGE_REQUIRED = NO_FOR_MINIMAL_REFINEMENT`
- Optional artifact field addition may be useful if design wants explicit audit labels such as `risk_on_pacing_quality_binding_result`, but the current artifacts already contain enough evidence to implement a narrow source-level refinement.

Migration:

- `MIGRATION_REQUIRED = NO`
- Existing old-run comparability after implementation: `NO` for decision-path comparison after the first affected date, because portfolio state can diverge.
- Fresh validation after implementation: `YES`

## Test Surface

Required focused tests before any Production promotion:

- MCV preserves `COMPARABLE_HIGH` vs `COMPARABLE_MARGINAL` and does not regress legacy lineage.
- CAUTIOUS strong/high rows remain deployable when current confirmation is sufficient.
- CAUTIOUS marginal Cash-preferred rows are reduced/deferred according to the selected binding rule.
- GRADUAL strong/high rows remain deployable.
- GRADUAL marginal Cash-preferred rows are reduced/deferred according to the selected binding rule.
- `CASH_PREFERRED_PARTICIPATION_VALID` vs `CASH_PREFERRED_DEFER` remains PC-owned and auditable.
- BUY_NEW and BUY_ADD use the same marginal-capital competition contract while preserving G129 order-increment semantics.
- Position Sizing does not reintroduce positive quantity for PC-deferred rows.
- Runtime Planning/Pending does not regenerate defeated security buys from pre-binding targets.
- SELL/REDUCE/EXIT, Corporate Action, KI-004, KI-006, recent-exit guard, and G129 focused regressions remain PASS.
- Fixture coverage for focus dates: `2023-03-22`, `2023-03-27`, `2023-04-11`, `2023-04-24`, `2023-05-01`.

## Required Answers

- `FIRST_POTENTIALLY_AFFECTED_DATE = 2023-03-01`
- `AFFECTED_DECISION_DAY_COUNT = 23`
- `POTENTIALLY_AFFECTED_BUY_NEW_COUNT = 46`
- `POTENTIALLY_AFFECTED_BUY_ADD_COUNT = 2`
- `POTENTIALLY_AFFECTED_NOTIONAL = 4,190,860`
- `NORMAL_DEPLOYMENT_IMPACT = NO_DIRECT_IMPACT_IF_SCOPE_LIMITED_TO_CAUTIOUS_GRADUAL`
- `CAUTIOUS_DEPLOYMENT_IMPACT = MATERIAL_DIRECT; 36 COMPARABLE_MARGINAL fills, 2,839,530 notional`
- `GRADUAL_REDEPLOYMENT_IMPACT = MATERIAL_DIRECT; 12 COMPARABLE_MARGINAL fills, 1,351,330 notional`
- `RISK_OFF_SELL_PATH_IMPACT = NO_DIRECT_IMPACT_EXPECTED`
- `REENTRY_GUARD_PATH_IMPACT = PATH_DEPENDENT_ONLY`
- `CASH_EOD_IMPACT_RANGE = 0 to +527,020 same-day cash in observed period; focus-date max +370,400 on 2023-05-01`
- `EXPOSURE_EOD_IMPACT_RANGE = 0 to -34.34 pp same-day exposure in observed period; focus-date max -23.46 pp on 2023-05-01`
- `PATH_DEPENDENCY_MATERIAL = YES`
- `SCHEMA_CHANGE_REQUIRED = NO_FOR_MINIMAL_REFINEMENT`
- `MIGRATION_REQUIRED = NO`
- `FRESH_VALIDATION_REQUIRED_AFTER_IMPLEMENTATION = YES`
- `CHANGE_RISK_CLASS = C. MATERIAL_PORTFOLIO_PATH_CHANGE`
- `DESIGN_PHASE_SAFE_TO_START = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NOT_YET; DESIGN_REFINEMENT_JUSTIFIED = YES`

## Final Judgment

`PHASE32_FG_RISK_ON_PACING_REFINEMENT_IMPACT_SURFACE_COMPLETE_MATERIAL_PORTFOLIO_PATH_CHANGE_DESIGN_PHASE_SAFE_TO_START`
