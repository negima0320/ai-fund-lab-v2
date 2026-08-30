# Phase32-R - Evidence-Tiered Winner ADD Acceleration Design

## Scope

This is a READ-ONLY DESIGN TASK for a USER-APPROVED PERFORMANCE INITIATIVE.

No production implementation was performed. No source code, config, Strategy parameter, threshold, weight, Cash policy, Risk Pacing, Safety constraint, BUY_ADD/G129 behavior, PM behavior, PS behavior, Runtime behavior, fresh-run, resume, replay, or long Historical execution was performed by Codex.

No future price, future return, future regime, future MFE/MAE, later SELL result, final campaign outcome, Historical profitability, or hindsight winner classification was used.

Final correctness-track premise:

- Phase32-Q accepted Phase32-P actual-path REENTRY provenance.
- Phase32-Q final judgment: `PHASE32_Q_REENTRY_PROVENANCE_ACTUAL_PATH_ACCEPTED_CORRECTNESS_TRACK_READY_TO_CLOSE`

This phase therefore treats ADD acceleration as performance design, not correctness repair.

## Evidence Basis

Sources reviewed:

- Current source at commit `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59`
- Current source is dirty from prior Phase32 work.
- `docs/phase_reports/phase32_m_end_to_end_plateau_susceptibility_root_cause_audit.md`
- `docs/phase_reports/phase32_n_winner_capital_acceleration_growth_engine_architecture_audit.md`
- Current decision-time artifacts from `runtime-test-historical-extended-smoke-20260830T040609131559Z`
- Current PC/PS/Runtime ownership implementation in source

Current run auxiliary coverage at audit snapshot:

- Completed business days observed through `2022-10-26`
- PM ADD-shaped PC rows in completed days: `14`
- ADD eligibility:
  - `PASS`: 5
  - `FAIL_CLOSED`: 9
- ADD expected edge state:
  - `IMPROVING`: 5
  - `WEAKENING`: 8
  - `BUY_QUALITY_INCREMENTAL_ADD_BLOCKED`: 1
- ADD incremental value state:
  - `POSITIVE`: 5
  - `UNKNOWN`: 8
  - `BUY_QUALITY_INCREMENTAL_ADD_BLOCKED`: 1
- ADD opportunity cost:
  - `PASS`: 12
  - `FAIL_CLOSED`: 1
  - `NOT_EVALUATED`: 1
- ADD no-loss averaging:
  - `PASS`: 13
  - `NOT_EVALUATED`: 1
- Buy Quality:
  - `FULL_ALLOCATION_ELIGIBLE`: 5
  - `REDUCED_ALLOCATION_ONLY`: 8
  - `BUY_WAIT`: 1
- Positive PC ADD evidence rows: 5

Phase32-M/N broader decision-path evidence remains the main bottleneck evidence:

- PM ADD decisions: 66
- BUY_ADD fills: 16
- All BUY_ADD fills were one lot
- PC selected `ADD` as final capital winner on only 2 of 76 Strategy days
- PC selected `CASH_OPTIONALITY` on 51 of 76 Strategy days
- ADD funnel: 45 `PC_NO_POSITIVE_ADD_INCREMENT`, 16 `BUY_ADD_FILLED`, 3 `PS_NO_EXECUTABLE_ADD_DELTA`, 2 `NO_BUY_ADD_FILL`

## Current Bottleneck

The system already supports:

```text
BUY_NEW small entry
-> PM detects continuation and emits ADD intent
-> PC determines whether incremental capital is justified
-> PS converts accepted continuous target/increment to executable lot quantity
-> Runtime consumes PS-bound BUY_ADD order increment
```

The bottleneck is not candidate scarcity or Runtime quantity invention. The bottleneck is conservative post-confirmation capital authorization:

- PM can identify ADD-worthy campaigns.
- PC often does not authorize a positive ADD increment.
- When PC does authorize an increment, PS frequently collapses the continuous meaning to one lot or zero lots.
- Cash remains a frequent valid competitor.

This is composed conservatism, not a correctness defect.

## Canonical Authority Map

| Stage | Owner | Authority | Phase32-R Design Constraint |
|---|---|---|---|
| Candidate discovery | Candidate / Opportunity AI | BUY_NEW candidate/rank evidence | Do not broaden BUY_NEW as part of this design |
| Buy Quality | Buy Quality | eligibility/reduction/wait/reject evidence | Required input and hard brake for ADD tiering |
| PM | Position Management | ADD directional lifecycle intent | PM must not decide ADD quantity or lot count |
| PC | Portfolio Construction | ADD tier, marginal capital authorization, NEW/ADD/Cash competition | Correct owner of acceleration tier and continuous magnitude |
| PS | Position Sizing | discrete executable lot quantity | Converts PC authority to feasible quantity; does not raise strategy magnitude |
| Runtime Planning | Runtime | consumes PS-bound order increment | Must not enlarge BUY_ADD |
| Pending/Submit/Execution | Runtime | operational order lifecycle | Must preserve G129 order-increment semantics |
| REDUCE/EXIT | PM + sell lifecycle | de-risk / full campaign exit | Must remain as-is; no sell loosening |

Canonical design boundary:

```text
PM ADD intent
-> PC evidence-tiered ADD capital authority
-> PS discrete quantity conversion
-> Runtime PS-bound BUY_ADD consumer
```

## ADD Tier Semantics

Recommended PC-owned semantic taxonomy:

| Tier | Meaning | Capital Semantics | Required Posture |
|---|---|---|---|
| `NORMAL_ADD` | PM ADD is valid and core evidence is positive, but confirmation is ordinary or some evidence is reduced/limited | One staged incremental authorization or current baseline ADD behavior | Conservative |
| `STRONG_ADD` | Existing campaign has materially strengthened with aligned PIT evidence and no major constraint conflict | Larger continuous incremental weight than normal, eligible to become multiple executable lots after PS | Acceleration |
| `EXCEPTIONAL_ADD` | Rare case where confirmation, opportunity superiority, risk headroom, liquidity, and pacing are all unusually clean | Upper-range continuous ADD increment within cap/headroom; PS may produce several lots | Scarce, heavily guarded |
| `NO_ACCELERATION` | PM ADD exists but evidence is missing, weakening, blocked, or inferior to NEW/Cash | No positive incremental authorization | Fail-closed |

Names should be finalized against local naming conventions during implementation. The semantic contract matters more than exact labels.

Do not set production mappings like `STRONG_ADD=2 lots` or `EXCEPTIONAL_ADD=3 lots` in Phase32-R. This phase defines authority and admissible shape only.

## Evidence Classification

| Evidence | Classification | Rationale |
|---|---|---|
| PM ADD intent | REQUIRED | Confirms lifecycle direction; without PM ADD there is no ADD acceleration |
| PM `strong_trend_continuation` | REQUIRED for `STRONG_ADD`, SUPPORTIVE for `NORMAL_ADD` | Existing accepted signal of winner continuation |
| `opportunity_rank_still_high` | REQUIRED for `STRONG_ADD`, SUPPORTIVE for `NORMAL_ADD` | Confirms opportunity remains competitive at decision time |
| `expected_edge_improvement_state` | REQUIRED | Direct current-vs-prior same-campaign evidence for marginal ADD |
| `incremental_investment_value_state` | REQUIRED | Core proof that extra capital has positive decision-time value |
| `opportunity_cost_status` | REQUIRED | Prevents automatic ADD victory over strong NEW/Cash alternatives |
| Buy Quality eligibility | REQUIRED | `BUY_WAIT` / explicit zero must block incremental ADD; `FULL` supports higher tier; `REDUCED` can cap tier |
| Momentum trajectory | SUPPORTIVE | Useful confirmation, but should not alone authorize larger capital |
| Short trend / MA evidence | SUPPORTIVE | Useful for confirmation and REENTRY/entry context; not standalone magnitude authority |
| Campaign continuation / health | REQUIRED | Existing campaign must be healthy and same campaign identity/provenance must pass |
| `no_loss_averaging_status` | REQUIRED | Prevents averaging down under the guise of winner acceleration |
| Current weight | RISK_CONSTRAINT | Determines current exposure and marginal room; not a strength signal by itself |
| Concentration headroom / single-name cap | RISK_CONSTRAINT | Hard cap on magnitude and tier admissibility |
| Cash availability / pending reservations | RISK_CONSTRAINT | Capital cannot be authorized if unavailable or reserved |
| Risk Pacing | RISK_CONSTRAINT | Can down-tier or cap acceleration; must not be bypassed |
| Safety hard constraints | RISK_CONSTRAINT | Fail-closed block |
| Broker eligibility | RISK_CONSTRAINT | Fail-closed block |
| Corporate action | RISK_CONSTRAINT | Fail-closed block when blocking event or unknown required evidence |
| Lot feasibility | RISK_CONSTRAINT | PS-owned feasibility; should not define tier, only executable outcome |
| Liquidity feasibility | RISK_CONSTRAINT | Caps or blocks large increments |
| Historical PnL / realized return | NOT_APPROPRIATE_FOR_TIERING | Forbidden hindsight |
| Future regime / future MFE/MAE | NOT_APPROPRIATE_FOR_TIERING | Forbidden future information |
| Final campaign outcome | NOT_APPROPRIATE_FOR_TIERING | Hindsight |

Conclusion:

Existing PIT evidence is sufficient to support a first evidence-tiered ADD design. New feature families are not required for the first implementation.

## Capital Magnitude Alternatives

### A. Multiple Lots Directly

- Philosophy fit: medium
- Expected acceleration strength: high
- Existing PIT evidence use: medium
- Architecture cleanliness: low-medium
- Concentration risk: high
- Implementation complexity: medium
- Regression risk: high
- Recommendation: do not make PC directly authorize lots as the primary semantic.

Direct lot count blurs PC/PS authority. It is tempting because the symptom is one-lot ADD, but the clean architecture is continuous PC authority followed by PS lot conversion.

### B. Larger `accepted_incremental_weight`

- Philosophy fit: high
- Expected acceleration strength: high
- Existing PIT evidence use: high
- Architecture cleanliness: high
- Concentration risk: controlled by caps
- Implementation complexity: medium
- Regression risk: medium
- Recommendation: primary mechanism.

This best matches existing architecture:

```text
PC continuous/marginal capital authority
-> PS discrete quantity
-> Runtime order increment
```

### C. Dynamic Confirmed-Winner Target Weight

- Philosophy fit: high if ADD-only; low if global
- Expected acceleration strength: medium-high
- Existing PIT evidence use: high
- Architecture cleanliness: medium-high
- Concentration risk: medium-high
- Implementation complexity: medium
- Regression risk: medium-high
- Recommendation: use only as internal PC ADD target derivation, not as a global target-weight expansion.

This can express movement from initial small entry toward cap, but must not become a blanket target uplift.

### D. Staged Multi-Increment Budget

- Philosophy fit: high
- Expected acceleration strength: medium-high
- Existing PIT evidence use: high
- Architecture cleanliness: medium-high
- Concentration risk: controlled
- Implementation complexity: medium-high
- Regression risk: medium
- Recommendation: acceptable second layer after larger incremental weight.

This is useful for auditability: PC may authorize a tiered continuous increment, then PS executes feasible lots. Repeated confirmation can refresh the stage.

### E. Other Existing Semantic

- Winner priority in PC competition: high fit, but must not auto-defeat NEW/Cash.
- Faster ADD cadence: medium fit; current evidence shows cadence can already be fast.
- Broader deployment breadth: medium fit; may dilute winner concentration.
- Cash optionality rebalance: medium fit; dangerous if blanket.

## Selected Capital Magnitude Design

Recommended:

```text
PC-owned evidence-tiered larger accepted_incremental_weight
with an auditable ADD tier semantic,
then PS-owned discrete quantity conversion.
```

This may result in multi-lot BUY_ADD when:

- PC tier and continuous increment are high enough,
- cash and risk budget exist,
- single-name cap and concentration headroom allow it,
- PS lot/liquidity feasibility can execute it.

But the design should not encode a direct `tier -> fixed lot count` rule in PC.

## Winner vs NEW vs Cash Comparison Contract

Strong ADD must not automatically defeat NEW or Cash.

Recommended comparison contract:

1. Build deployable candidates:
   - existing ADD competitors with tier evidence,
   - BUY_NEW competitors with current candidate/opportunity/BQ evidence,
   - Cash optionality with market/pacing/residual evidence.
2. Require ADD-specific gates before tiering:
   - PM ADD,
   - current campaign identity/provenance PASS,
   - current position authority PASS,
   - incremental value PASS,
   - no-loss-averaging PASS.
3. Assign ADD tier only after gates pass.
4. Convert tier to an admissible continuous increment range, not fixed lots.
5. Compare ADD/NEW/Cash using categorical evidence first:
   - ADD can outrank NEW only when opportunity-cost status is PASS and ADD evidence is stronger or at least not inferior.
   - NEW can still win when its current opportunity is superior.
   - Cash can still win under marginal opportunity set, cautionary Risk Pacing, residual/lot infeasibility, or safety constraints.
6. Preserve existing marginal priority machinery. Improve categorical ADD evidence before introducing a universal scalar.

`canonical_high_resolution_marginal_capital_value.v1`:

- Relevant: YES
- Required now: NO

The current categorical evidence is enough for a first implementation. High-resolution marginal value should be introduced only if focused tests and long Historical characterization show ambiguous ADD vs NEW vs Cash ordering that cannot be resolved with the existing categorical contract.

## Acceleration Guardrails

Minimum guardrails for any `STRONG_ADD` or `EXCEPTIONAL_ADD`:

- PM action is `ADD`.
- campaign identity/provenance PASS.
- current position authority PASS.
- expected edge improvement PASS.
- incremental investment value PASS.
- opportunity-cost PASS.
- no-loss-averaging PASS.
- Buy Quality not blocking.
- `BUY_WAIT`, `TEMPORARY_BUY_INELIGIBLE`, or explicit zero quality adjustment blocks incremental ADD.
- concentration and single-name cap headroom PASS.
- Risk Pacing compatible.
- Safety hard cap PASS.
- broker eligibility PASS.
- corporate-action status PASS / no blocking event.
- liquidity capacity sufficient for proposed increment.
- PS lot feasibility can convert continuous intent to executable quantity.
- cash after pending reservations sufficient.
- missing/conflicting evidence fails closed to `NO_ACCELERATION` or `NORMAL_ADD` cap, never silent uplift.

Suggested down-tier rules:

- `REDUCED_ALLOCATION_ONLY`: cannot exceed `NORMAL_ADD` unless another explicit authority says reduced-but-eligible remains strong enough.
- `CAUTIOUS_DEPLOYMENT`: cap at `NORMAL_ADD` or require smaller `STRONG_ADD` range.
- `GRADUAL_REDEPLOYMENT`: allow `STRONG_ADD` but block `EXCEPTIONAL_ADD`.
- liquidity `WATCH`: cap magnitude even if tier is strong.
- any REVIEW_REQUIRED: no acceleration beyond current baseline.

## De-Risk Compatibility

Larger ADD can coexist with current REDUCE/EXIT if acceleration remains PC/PS-authorized and cap-aware.

Design confirmations:

- Larger ADD increases current position size, but does not change campaign identity.
- REDUCE quantity authority remains sell-side and can compute partial de-risk from current position.
- EXIT remains campaign-wide semantics on breakdown.
- Sell thresholds do not need to change.
- Concentration increase must be visible in Safety and PC caps before the ADD is authorized.
- Runtime sell path must remain a consumer of sell authority, not a compensating late risk engine.

Do not loosen SELL, REDUCE, EXIT, profit retention, hard-stop, or breakdown semantics as part of this initiative.

## BUY_NEW / REENTRY Interaction

Acceleration priority:

1. Existing confirmed ADD campaign.
2. Accepted REENTRY after it becomes a new campaign and later proves strength through ADD.
3. BUY_NEW initial entry.

BUY_NEW:

- stays cautious,
- does not receive multi-lot initial sizing from this design,
- remains subject to BQ/PC/Cash/PS constraints.

REENTRY:

- first accepted REENTRY remains cautious, like BUY_NEW,
- prior campaign context is used for safety/provenance, not automatic size,
- after the new campaign is open and later earns PM ADD with strong evidence, it can use the same tiered ADD design.

This preserves Phase32-Q provenance acceptance and prevents old campaign outcome from becoming a hindsight sizing signal.

## Required Alternatives Comparison

| Alternative | Philosophy Fit | Acceleration Strength | Existing PIT Evidence | Architecture Cleanliness | Concentration Risk | Complexity | Regression Risk | Recommendation |
|---|---|---|---|---|---|---|---|---|
| Evidence-tiered multi-lot ADD | High | High | High | Medium-high if expressed as PC weight -> PS lots | High but controllable | Medium | Medium | Implement as outcome of PC weight tier, not direct PC lot rule |
| Larger PC incremental weight | Very high | High | High | Very high | Controlled by caps | Medium | Medium | Primary recommendation |
| Dynamic winner target expansion | High if ADD-only | Medium-high | High | Medium-high | Medium-high | Medium | Medium-high | Use internally for ADD target range; avoid global target change |
| Winner priority in PC competition | High | Medium-high | Medium-high | High | Medium | Medium | Medium | Add as categorical priority only when opportunity-cost PASS |
| Faster ADD cadence | Medium | Medium | Medium | High | Medium | Low-medium | Low-medium | Secondary; cadence is not primary bottleneck |
| Broader deployment breadth | Medium | Medium | Medium | Medium | Medium | Medium | Medium | Defer; may dilute winner capitalization |
| Cash optionality rebalance | Medium | Medium-high | Medium | Medium | Medium | Medium | Medium-high | Defer; Cash must remain first-class |

## Minimum-Change Recommendation

Implement one PC-owned performance feature:

```text
Evidence-tiered ADD acceleration authority
that produces add_acceleration_tier and a tier-bounded continuous incremental weight request,
then lets existing incremental budget reconciliation, capital competition, Risk Pacing,
lot-aware final reallocation, PS, and Runtime G129 consume the result.
```

Minimum implementation scope:

1. Add an internal PC resolver, e.g. `resolve_add_acceleration_tier()`.
2. Inputs are existing member fields:
   - PM ADD/action reasons,
   - expected edge improvement,
   - incremental investment value,
   - opportunity cost,
   - Buy Quality action/adjustment,
   - campaign/current position authority,
   - no-loss-averaging,
   - concentration/current weight/headroom,
   - Risk Pacing,
   - Safety/broker/CA,
   - liquidity/lot context where available.
3. Output auditable fields:
   - `add_acceleration_tier`
   - `add_acceleration_status`
   - `add_acceleration_reason_codes`
   - `add_acceleration_authority`
   - `pre_acceleration_incremental_weight`
   - `tier_bounded_incremental_weight`
   - `post_acceleration_target_weight`
   - guardrail statuses.
4. Wire output into PC ADD bridge before incremental budget reconciliation.
5. Keep PS as the only discrete lot quantity authority.
6. Keep Runtime as PS-bound order increment consumer.
7. Fail closed on missing or conflicting required evidence.

Implementation should not touch:

- PM thresholds,
- candidate selection,
- BUY_NEW initial sizing,
- REENTRY initial sizing,
- BQ scoring,
- Risk Pacing policy,
- sell thresholds,
- G129 Runtime BUY_ADD consumer logic.

## Parameter-Selection Boundary

`PARAMETER_SELECTION_DEFERRED`

Phase32-R does not select production tier boundaries, lot multipliers, or exact target uplifts from Historical profitability.

Admissible design ranges for future implementation:

- `NORMAL_ADD`: current baseline behavior or one staged increment.
- `STRONG_ADD`: larger continuous increment than baseline, bounded by current weight, single-name cap, available budget, Risk Pacing, liquidity, and PS feasibility.
- `EXCEPTIONAL_ADD`: rare upper-range increment, only when all required evidence is PASS and Risk Pacing is constructive.

The exact boundaries should be selected from:

- decision-time evidence semantics,
- risk constraints,
- execution feasibility,
- user-approved risk appetite,
- focused invariant tests,
- long-run funnel characterization.

They must not be selected by maximizing realized return.

## Validation Plan

Focused tests before Historical:

1. `NORMAL_ADD` when PM ADD plus baseline evidence passes but strong evidence is incomplete.
2. `STRONG_ADD` when PM ADD, improving edge, positive incremental value, opportunity-cost PASS, BQ eligible, no-loss-averaging PASS, campaign/current authority PASS, and headroom PASS.
3. `EXCEPTIONAL_ADD` only when all required evidence is PASS and Risk Pacing/liquidity/headroom are constructive.
4. `BUY_WAIT` / explicit zero quality allocation blocks acceleration.
5. Weakening expected edge blocks acceleration.
6. Unknown incremental value blocks acceleration.
7. Opportunity-cost fail prevents ADD from beating NEW.
8. Cash remains selected when Risk Pacing or marginal opportunity state requires it.
9. Single-name cap and concentration headroom cap the tier-bounded increment.
10. Liquidity/lot feasibility can reduce executable lots without Runtime overriding PS.
11. Missing campaign identity/provenance fails closed.
12. Missing current position authority fails closed.
13. REENTRY initial buy does not accelerate until later ADD.
14. BUY_NEW remains cautious and unaffected.
15. REDUCE and EXIT after larger ADD preserve original sell authority.
16. G129 BUY_ADD remains order-increment scoped.
17. No Runtime path can increase BUY_ADD beyond PS quantity.
18. Hash/fail-closed validation remains intact for genuine mismatches.

Future Historical characterization metrics:

- PM ADD count.
- ADD tier distribution.
- PC positive increment count.
- PC requested vs accepted incremental weight.
- PS quantity lots per ADD.
- BUY_ADD fills.
- ADD notional share.
- time from BUY_NEW to first ADD.
- time to meaningful position weight.
- Cash defeat frequency when strong ADD exists.
- NEW defeat frequency when strong ADD exists.
- concentration / single-name cap utilization.
- REDUCE/EXIT after larger positions.
- MDD / Equity only as characterization, not tier selection.
- cases where strong ADD was blocked by each guardrail.

Do not use future outcome or realized return to choose tier boundaries.

## What Remains Unchanged

- BUY_NEW remains cautious and small.
- Strong winners remain HOLD while strengthening.
- ADD stops when evidence weakens.
- REDUCE remains active on risk increase.
- EXIT remains active on breakdown.
- Cash remains a first-class alternative.
- Risk Pacing remains authoritative.
- Safety hard constraints remain fail-closed.
- PM ADD remains directional only.
- PC owns capital magnitude.
- PS owns executable lot quantity.
- Runtime consumes PS-bound order increment.
- G129 BUY_ADD semantics remain intact.
- Phase32-P/Q REENTRY provenance and Phase32-L campaign identity remain intact.

## USER_APPROVED_PERFORMANCE_INITIATIVE Confirmation

Confirmed. Phase32-R is treated as a user-approved performance initiative design, not a correctness repair.

## NO CODE CHANGE

Confirmed. This phase report is the only file created by Phase32-R.

## NO Future-Information Use

Confirmed. The design uses current source, SoT/Architecture boundaries, Phase32-M/N/Q evidence, current decision-time artifacts, and PIT-only constraints. It does not use future outcomes or Historical profitability to select parameters.

## Final Judgment

1. `CAN_EXISTING_PIT_EVIDENCE_SUPPORT_SAFE_EVIDENCE_TIERED_ADD_ACCELERATION`

   YES. Existing PM ADD, expected edge improvement, incremental investment value, opportunity-cost, Buy Quality, no-loss-averaging, campaign/current authority, Risk Pacing, Safety/broker/CA, concentration, cash, liquidity, and lot evidence are sufficient for a first evidence-tiered ADD acceleration design.

2. `WHAT_SHOULD_OWN_ACCELERATION_TIER_AND_CAPITAL_MAGNITUDE`

   Portfolio Construction should own both the ADD acceleration tier and continuous capital magnitude. PS should own discrete executable quantity. Runtime should remain the PS-bound order increment consumer.

3. `HOW_SHOULD_STRONG_ADD_DIFFER_FROM_NORMAL_ADD`

   `NORMAL_ADD` should preserve baseline staged ADD behavior. `STRONG_ADD` should authorize a larger tier-bounded continuous incremental weight when all required confirmation and risk evidence pass. `EXCEPTIONAL_ADD` should be rare and only authorize upper-range continuous increments under complete, constructive evidence and cap headroom.

4. `SHOULD_MULTI_LOT_ADD_BE_IMPLEMENTED`

   YES, but only as a possible PS result of larger PC continuous ADD authority. Do not implement PC as a direct fixed `tier -> lot count` rule.

5. `IS_HIGH_RESOLUTION_MARGINAL_CAPITAL_VALUE_REQUIRED_NOW`

   NO. It is relevant but not required for the first implementation. Use existing categorical PIT evidence first; revisit `canonical_high_resolution_marginal_capital_value.v1` only if ADD vs NEW vs Cash comparisons remain ambiguous.

6. `WHAT_IS_THE_MINIMUM_IMPLEMENTATION_SCOPE`

   Add a PC-owned `resolve_add_acceleration_tier()` style authority that emits tier, reason codes, guardrail statuses, and a tier-bounded continuous incremental weight; wire it into existing ADD bridge / incremental budget / capital competition; keep PS and Runtime authority unchanged.

7. `WHAT_MUST_BE_VALIDATED_BEFORE_LONG_HISTORICAL_ACCEPTANCE`

   Focused tests must prove tier gating, fail-closed missing evidence, BQ zero preservation, cap/liquidity/Risk Pacing constraints, Cash/NEW competition, REENTRY/BUY_NEW non-acceleration, REDUCE/EXIT compatibility, PS-only quantity authority, Runtime no-redecision, and G129 order-increment semantics. Historical should then characterize funnel metrics and risk behavior without tuning to realized returns.

Final classification:

`PHASE32_R_PC_OWNED_EVIDENCE_TIERED_ADD_ACCELERATION_DESIGN_READY`
