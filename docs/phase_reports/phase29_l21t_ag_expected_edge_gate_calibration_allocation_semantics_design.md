# Phase29-L21T-AG - Expected Edge Gate Calibration / Allocation Semantics Design

## Primary Judgment

`PHASE29_L21T_AG_EXPECTED_EDGE_RELATIVE_ALLOCATION_SEMANTICS_DESIGNED_IMPLEMENTATION_READY`

Current Phase remains `Phase29`.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AG` |
| Task Type | `DESIGN_ONLY` |
| AF Judgment inherited | `PHASE29_L21T_AF_EXPECTED_EDGE_GATE_FORWARD_RETURN_ATTRIBUTION_COMPLETE_REPAIR_DESIGN_REQUIRED` |
| Strategy implementation changed | `NO` |
| Runtime implementation changed | `NO` |
| Config changed | `NO` |
| Model changed | `NO` |
| Training / calibration executed | `NO` |
| Target run mutated | `NO` |
| Long Historical executed | `NO` |

AG is a design artifact only.  It did not stop, resume, replay, recover,
fresh-run, or mutate:

```text
runtime-test-historical-extended-smoke-20260814T005603520480Z
```

## Inherited AF Evidence

AF inspected `7` low-exposure dates / `350` candidates:

| Metric | Value |
| --- | ---: |
| Quality PASS | `286` |
| Positive Expected Edge | `27` |
| non_positive_expected_edge_score | `323` |
| ranking/top20 exclusion | `158` |
| lot/safety blocked | `5` |
| BUY allocated | `10` |
| false negative | `87` |
| false positive | `7` |
| Spearman 5BD | `0.0495` |
| Spearman 10BD | `-0.0611` |
| Spearman 20BD | `-0.1205` |

AF conclusion retained:

```text
2022 autumn high cash was not proven to be the result of correctly excluding
bad opportunities.  The current Expected Edge / ranking semantics missed many
subsequent winners and did not separate forward returns reliably in the
inspected low-exposure sample.
```

## Root Cause

The confirmed semantic defect is:

```text
uncalibrated relative score is used as an absolute expected-return gate
```

Current Runtime artifacts declare:

| Field | Value |
| --- | --- |
| canonical score field | `runtime_opportunity_score` |
| score semantic role | `uncalibrated_relative_model_score` |
| economic units available | `false` |
| calibration applied | `false` |
| deprecated alias | `expected_edge_score` |
| deprecated alias | `expected_return` |

Despite that, Runtime BUY opportunity eligibility still blocks:

```text
expected_edge_score <= 0 -> non_positive_expected_edge_score -> BUY_INELIGIBLE
```

Therefore:

| Question | Judgment |
| --- | --- |
| Absolute zero gate valid | `NO` |
| Top20 fixed eligibility gate valid | `PARTIAL` |
| Calibration applied | `NO` |

Top20 remains useful as ranking metadata / shortlist diagnostics, but AF did
not prove it as a hard BUY eligibility authority.

## Authority Audit

| Authority | Current Owner | Canonical Role | AG Design Role |
| --- | --- | --- | --- |
| Candidate producer | Runtime BUY AI producer | Candidate Top50 source | unchanged |
| Quality producer | `strategy.buy_quality` | Candidate quality and relative opportunity quality | central BUY_NEW quality gate |
| Opportunity score producer | Opportunity AI inference via Runtime BUY AI producer | raw model score | relative signal only unless calibrated |
| `runtime_opportunity_score` | Runtime BUY AI artifact | canonical score field | canonical score field retained |
| `expected_edge_score` alias | Runtime BUY AI artifact | deprecated compatibility alias | retained for compatibility, not economic authority |
| Opportunity ranking | Opportunity AI / Runtime BUY AI | order candidates by score | competition metadata, not fixed BUY permission |
| Top20 | Opportunity ranking artifact | rank metadata | metadata / optional shortlist, not hard eligibility |
| PC consumer | Portfolio Construction | portfolio fit, budget competition, target weights | relative allocation competition |
| PS consumer | Position Sizing | lot-aware quantity realization | unchanged, enforces feasible lots |
| BUY planning consumer | Runtime Planning / Morning Planning | materialize executable BUY intent | consumes PC/PS result, not raw score sign |
| Runtime final authority | Submit / Execution / Safety | fail-closed execution authority | unchanged |

## Option Review

### Option A - Remove Absolute Zero Gate, Preserve Relative Ranking

Design:

```text
score <= 0 is not an absolute rejection when economic_units_available=false.
Quality, risk, broker, CA, market context, PC, PS, lot and safety still compete.
```

Pros:

- Directly fixes the semantic mismatch.
- Avoids future-return-tuned thresholds.
- Allows negative raw scores to be candidates only when they are relatively
  strong and otherwise eligible.

Cons / Degression risk:

- BUY count can rise if downstream relative quality is too permissive.
- Requires very clear no-buy reason separation.
- Must preserve no forced deployment and no rank1 auto-BUY.

Judgment: `NEEDED`, but not sufficient alone.

### Option B - Relative Score Normalization

Existing evidence:

`strategy.buy_quality` already computes:

```text
relative_quality_uses_percentile_robust_z_population_strength
```

using daily population percentile, robust z-score, and population strength.  It
also marks:

```text
rank_not_used_as_fixed_n_gate
rank1_weak_population_not_full
```

Design:

```text
Consolidate on the existing Buy Quality relative_opportunity_quality authority
instead of adding a new component.
```

Pros:

- Reuses existing Production-common Strategy authority.
- Distinguishes weak population Rank1 from stronger populations.
- Keeps Quality / Market Context / Execution / Portfolio Fit as explicit
  components.

Cons / Degression risk:

- Current Runtime opportunity eligibility may block before Strategy can use
  this authority.
- Component weights and action boundaries must not be retuned from AF forward
  returns.

Judgment: `PRIMARY IMPLEMENTATION PATH`.

### Option C - Formal Calibration

Design:

```text
Map raw score to economic expected return / probability / excess return only
through a formal PIT training-validation-calibration process.
```

Required before adoption:

- training / validation split
- leakage prevention
- out-of-sample validation
- model versioning
- Accepted Generation compatibility
- metrics registry
- PIT feature contract

Pros:

- Would allow a future economic absolute gate if validated.
- Better naming clarity for true expected return semantics.

Cons:

- Larger scope than AG/AH.
- Cannot use AF forward-return sample for threshold fitting.
- Requires model lifecycle work and probably a new Accepted Generation.

Judgment: `LATER`, not required before AH.

### Option D - Hybrid

Recommended:

```text
Quality FAIL -> reject
Safety / broker / CA fail -> reject
uncalibrated score -> relative competition
Market Context -> opportunity budget / aggressiveness modifier
PC -> portfolio-fit relative allocation
PS -> lot-aware realization
residual capital -> next feasible opportunity
Submit / Execution -> unchanged fail-closed authority
```

Judgment: `ADOPT`.

## Recommended Design

Recommended score semantic:

```text
runtime_opportunity_score = uncalibrated relative model score
```

Recommended BUY eligibility semantic:

```text
BUY_NEW eligibility must not fail solely because runtime_opportunity_score /
expected_edge_score alias is <= 0 when calibration_applied=false and
economic_units_available=false.
```

The following still fail closed:

- invalid or missing score
- malformed score semantic contract
- calibrated economic score <= 0 when calibration is formally applied
- high downside risk
- corporate action block
- broker unsupported / listing invalid
- data mismatch / stale artifact
- Quality FAIL
- Safety hard cap
- lot infeasibility where one lot exceeds safety hard max
- Re-entry guards
- no eligible opportunity population

Recommended allocation semantic:

```text
relative_opportunity_quality + market_context + signal_reliability +
execution_feasibility + portfolio_fit
-> Buy Quality action / allocation adjustment
-> Portfolio Construction relative capital competition
-> Position Sizing lot-aware executable quantity
-> Runtime Planning BUY only when executable quantity exists
```

Cash remains valid when no candidate survives this chain.  BUY count and
exposure must not be forced.

## Top20 Semantics

Top20 should become:

```text
ranking metadata / diagnostic shortlist
```

not:

```text
hard BUY eligibility authority
```

Reason:

- AF found `NOT_TOP20` had higher average 5BD/10BD/20BD returns than `TOP20`.
- `below_opportunity_top20` overlaps with non-positive uncalibrated score.
- Existing Buy Quality relative quality already uses rank without treating it
  as fixed N permission.

Allowed future use:

- observability
- score distribution diagnostics
- optional conservative cap inside PC if supported by validation

Forbidden:

- automatic BUY for top-N
- automatic reject solely for not top20 when the score is uncalibrated

## Naming / Schema Design

Do not perform a breaking rename in AH.

Recommended compatibility plan:

1. Keep `expected_edge_score` as a deprecated alias.
2. Canonicalize all new authority decisions on `runtime_opportunity_score`.
3. Require authority metadata:

```text
prediction_semantics = runtime_opportunity_score
semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

4. Add or preserve explicit metadata:

```text
expected_edge_score_semantic_role = deprecated_alias_uncalibrated_runtime_opportunity_score
expected_return_semantic_role = deprecated_alias_uncalibrated_runtime_opportunity_score_not_economic_return
```

5. If formal calibration later succeeds, introduce a separate calibrated
economic field rather than silently changing the alias meaning.

Schema changes required for AH: `YES`, but compatibility-preserving metadata
only if current schema does not already expose the fields at every consumer
boundary.

## Complexity Assessment

New component required:

```text
NO
```

Complexity:

```text
MEDIUM
```

Reason:

- Existing relative quality authority already exists in Buy Quality.
- Main implementation is authority consolidation and removal of premature
  absolute sign gating from Runtime opportunity eligibility.
- Risk is cross-boundary: Runtime BUY AI, Morning Planning, Buy Quality,
  Portfolio Construction, Position Sizing, Runtime Planning, Submit evidence,
  and tests must agree on the same score semantics.

## Degression Review

| Risk | AG Mitigation |
| --- | --- |
| BUY count急増 | No fixed BUY count; Quality + PC + PS + safety still gate. |
| low-quality buy増加 | Quality FAIL and risk/no-buy reasons remain fail-closed. |
| full-investment bias | Cash remains allowed on weak populations. |
| turnover増加 | PM / SELL unchanged; BUY_NEW path only. |
| Re-entry churn増加 | REENTRY guards stay separate and fail-closed. |
| winner dilution | PC competition and PS lot feasibility still allocate selectively. |
| concentration増加 | Strategy cap 18% and Safety hard cap 25% preserved. |
| cash枯渇 | Market Context, cash reserve, PC budget, Submit/Execution feasibility preserved. |
| mandatory SELL interference | SELL / REDUCE / EXIT unchanged. |
| ADD semantic破壊 | BUY_NEW repair is not mechanically applied to ADD. |
| residual allocation破壊 | Keep lot-aware residual reallocation and next feasible candidate behavior. |
| Runtime / Historical divergence | AH must be Production-common, no Historical branch. |
| Accepted Generation incompatibility | Preserve model artifact and aliases; add metadata only. |

## Implementation Scope Proposal For AH

Candidate files for next task:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
src/ai_fund_lab_v2/strategy/buy_quality.py
src/ai_fund_lab_v2/strategy/portfolio_construction.py
src/ai_fund_lab_v2/strategy/position_sizing.py
src/ai_fund_lab_v2/strategy/runtime_planning.py
tests/runtime_v2/
tests/strategy/
docs/02_architecture/
docs/03_operations/
```

Expected AH implementation shape:

1. Teach Runtime opportunity eligibility to read semantic metadata.
2. Treat `score <= 0` as hard rejection only when calibrated economic units are
   available.
3. Preserve hard block for high downside risk, CA, broker/listing, stale/missing
   artifacts, malformed contracts, and invalid score.
4. Preserve Buy Quality relative quality as the canonical relative competition
   authority.
5. Ensure PC/PS consume `runtime_opportunity_score` and authority metadata, not
   deprecated alias semantics.
6. Keep Submit/Execution unchanged.
7. Add compatibility evidence showing `expected_edge_score` remains an alias,
   not an economic return.

Config changes required: `NO` for AH.  
Model changes required: `NO` for AH.  
Retraining required: `NO` for AH.  
Formal calibration required: `LATER`.  
Accepted Generation impact: `COMPATIBILITY_PRESERVED`, no new generation needed
for AH if schema metadata is backward-compatible.

## Validation Design For AH

Focused validation cases:

| ID | Case | Expected |
| --- | --- | --- |
| V1 | uncalibrated negative score but strong relative population candidate | candidate may reach relative allocation competition |
| V2 | Quality FAIL | reject |
| V3 | Safety / broker / CA fail | reject |
| V4 | one lot > Safety hard cap | reject |
| V5 | many eligible candidates | BUY count not fixed |
| V6 | no eligible opportunity / weak population | Cash allowed |
| V7 | residual capital after blocked candidate | next feasible candidate can receive allocation |
| V8 | ADD path | Phase28/29 ADD contract preserved |
| V9 | SELL / REDUCE / EXIT | unchanged |
| V10 | REENTRY | cooldown / hurdle / low-price safeguards preserved |
| V11 | Runtime / Historical | common path, no Historical branch |
| V12 | future returns | no Runtime input leakage |

Suggested short validation order after AH:

1. unit / focused regression for Runtime opportunity eligibility
2. Buy Quality / PC / PS focused strategy tests
3. Runtime Planning focused tests
4. Pending / Submit visibility focused tests
5. selected-day isolated replay-equivalent fixture if available
6. short Historical smoke only if existing short contract permits
7. user-executed fresh 4-year Historical if implementation is accepted

Codex must not run long Historical in AH unless explicitly instructed by a
future task and allowed by its scope.

## Common SoT Updates For AH

AH should update common documentation for:

- `runtime_opportunity_score` semantics
- `expected_edge_score` alias semantics
- calibration status and economic unit contract
- BUY eligibility contract
- relative competition contract
- top20 metadata vs eligibility distinction

Suggested docs:

```text
docs/02_architecture/
docs/03_operations/
docs/01_requirements/phase_roadmap.md
```

## Required Final Fields

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AG` |
| Primary Judgment | `PHASE29_L21T_AG_EXPECTED_EDGE_RELATIVE_ALLOCATION_SEMANTICS_DESIGNED_IMPLEMENTATION_READY` |
| Current Phase | `Phase29` |
| AF Judgment inherited | `PHASE29_L21T_AF_EXPECTED_EDGE_GATE_FORWARD_RETURN_ATTRIBUTION_COMPLETE_REPAIR_DESIGN_REQUIRED` |
| Root Cause | `uncalibrated_relative_score_used_as_absolute_expected_return_gate` |
| Current score semantic | `uncalibrated_relative_model_score` |
| Calibration applied | `NO` |
| Absolute zero gate valid | `NO` |
| Top20 gate valid | `PARTIAL` |
| Recommended score semantic | `runtime_opportunity_score as relative competition signal` |
| Recommended BUY eligibility semantic | `no absolute zero rejection unless calibrated economic units are available` |
| Recommended allocation semantic | `relative quality + market + fit + feasibility competition` |
| Formal calibration required | `LATER` |
| New component required | `NO` |
| Complexity assessment | `MEDIUM` |
| Schema changes required | `YES - compatibility metadata / contract clarification` |
| Config changes required | `NO` |
| Model changes required | `NO` |
| Retraining required | `NO` |
| Accepted Generation impact | `COMPATIBILITY_PRESERVED` |
| BUY count forced | `NO` |
| Exposure forced | `NO` |
| SELL semantics changed | `NO` |
| ADD semantics changed | `NO` |
| REENTRY safeguards preserved | `YES` |
| Lot/Safety safeguards preserved | `YES` |
| Future return used as Runtime input | `NO` |
| Target run mutated | `NO` |
| Long Historical executed | `NO` |
| Phase30 entered | `NO` |

## Recommended Next Task

```text
Phase29-L21T-AH — Expected Edge Relative Allocation Semantics Implementation
```

AH is the first task where Production-common implementation should occur.
