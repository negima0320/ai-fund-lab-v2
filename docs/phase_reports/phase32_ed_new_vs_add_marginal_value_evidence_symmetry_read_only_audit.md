# Phase32-ED - NEW vs ADD Marginal Investment Value / Opportunity-Cost Evidence Symmetry READ-ONLY Audit

## Scope

This is a READ-ONLY audit. ED did not modify Production code, SHADOW code,
runtime state, Pending, Ledger, configuration, or source-run artifacts. ED did
not execute fresh-run, resume, recover, replay, or long Historical.

Primary evidence:

- EC analysis root: `reports/runtime_tests/analysis/phase32_ec_add_strength_increment_shadow_20260903T000002`
- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Evidence window: `2022-10-03` through `2023-10-26`
- EC manifest status: `PASS`
- EC manifest flags: `analysis_only=true`, `shadow_only=true`,
  `production_change_executed=false`, `runtime_state_mutated=false`,
  `source_run_artifact_mutated=false`, `future_information_used=false`
- Source baseline commit in EC manifest and current HEAD inspected during ED:
  `1f64f49ee9a8dd48280007e4df656e5f03e231ca`
- EC accepted artifact hash: `5451016e490214f81440f0d4fd154dc89cd76a86f84dd7daed5e8fb383e144a5`
- EC registry hash: `4c07b5647425b32653e3e0a0e1a1164130133cc0db2c22881dcef5b7c97a35ba`

## Architecture Basis

The Architecture SoT keeps authority boundaries separated:

- Portfolio Construction owns target membership, target weight, scarce capital,
  and NEW/ADD/Cash comparison.
- Position Sizing owns target notional, target quantity, quantity delta, and
  order quantity.
- Runtime Planning is a mapper and must not rerank or reoptimize Strategy
  decisions.
- PM ADD is directional intent. It is not an order and not direct quantity
  authority.
- G129 remains order-increment scoped: once PC/PS have produced an authorized
  positive BUY_ADD increment, Submit validates the pending item quantity against
  that PC ADD order-increment authority.

The current source confirms this boundary. In
`src/ai_fund_lab_v2/strategy/portfolio_construction.py`,
`resolve_add_allocation_bridge` consumes canonical ADD investment evidence,
current weight, PM ADD intent, BQ/Entry action, concentration, capital, and
execution feasibility. It can increase target weight only when the ADD bridge
has PASS evidence and a positive increment. It does not convert PM strength into
quantity by itself.

In `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`, EC's
`add_strength_to_increment_target_authority` is SHADOW-only and records
`add_strength_to_increment_target_authoritative_consumer_count = 0`. ED observed
no Production consumer connection.

## Evidence Coverage

EC backfill coverage:

- Business days: `264`
- Competitor rows: `BUY_ADD_NEXT_LOT=152`, `BUY_NEW_NEXT_LOT=2483`,
  `REENTRY_NEXT_LOT=5196`, `CASH_OPTIONALITY=264`
- Stage-B winners: `BUY_NEW_NEXT_LOT=212`, `REENTRY_NEXT_LOT=37`,
  `BUY_ADD_NEXT_LOT=11`, `CASH_OPTIONALITY=3`, `NONE=1`
- EC ADD increment demand: `BLOCKED=73`, `NO_POSITIVE_DEMAND=62`,
  `POSITIVE_INCREMENT_DEMAND=17`
- EC ADD evidence tier: `BLOCKED=73`, `INSUFFICIENT=62`,
  `MODERATE_COMPLETE=17`
- Zero desired ADD reclassification: `REMAIN_ZERO=99`

Additional ED aggregation over EC daily artifacts:

- ADD rows audited: `152`
- ADD incremental value state: `UNKNOWN=116`, `POSITIVE=36`
- ADD opportunity cost: `NEW_BUY_SUPERIOR=84`, `PASS=68`
- Expected edge state: `WEAKENING=72`, `IMPROVING=72`, `UNKNOWN=8`
- PIT comparison status: `COMPARISON_INSUFFICIENT=116`, `PASS=36`

For the `116` ADD `incremental_value=UNKNOWN` rows:

- Lot/increment root profile:
  - `NO_POSITIVE_DESIRED_INCREMENT=92`
  - `NO_ACCEPTED_CONTINUOUS_INCREMENT=16`
  - `BQ_BLOCKS_INCREMENT=8`
- Opportunity quality profile:
  - `BLOCKED=76`
  - `INSUFFICIENT=40`
- Top symbols:
  - `94320=33`
  - `94340=16`
  - `99840=15`
  - `83060=13`
  - `43880=12`
  - `45940=8`
  - `40520=7`
  - `54010=5`

For the `84` `NEW_BUY_SUPERIOR` ADD rows:

- All had `incremental_value=UNKNOWN` and
  `pit_validation_status=COMPARISON_INSUFFICIENT`.
- Expected edge split: `WEAKENING=42`, `IMPROVING=36`, `UNKNOWN=6`.
- Lot/increment split:
  - `NO_POSITIVE_DESIRED_INCREMENT=66`
  - `NO_ACCEPTED_CONTINUOUS_INCREMENT=12`
  - `BQ_BLOCKS_INCREMENT=6`

Same-day evidence profile for dates with at least one ADD
`incremental_value=UNKNOWN`:

- Unique dates: `92`
- `NEW` complete and feasible on `91` of those dates.
- Cash evidence complete on all `92` dates.
- REENTRY evidence complete on `59` of those dates.
- Representative same-day cases show many dates where ADD was UNKNOWN while NEW
  rows were complete and feasible and Stage-B selected NEW or REENTRY.

June through September 2023 ADD profile:

- ADD rows: `20`
- Incremental value: `UNKNOWN=16`, `POSITIVE=4`
- Opportunity cost: `NEW_BUY_SUPERIOR=14`, `PASS=6`
- Expected edge: `IMPROVING=12`, `WEAKENING=8`
- EC increment demand: `BLOCKED=16`, `NO_POSITIVE_DEMAND=4`
- Lot/increment status:
  - `NO_POSITIVE_DESIRED_INCREMENT=13`
  - `EXECUTABLE_INCREMENT_AVAILABLE=3`
  - `NO_ACCEPTED_CONTINUOUS_INCREMENT=2`
  - `BQ_BLOCKS_INCREMENT=2`

## Marginal Value Evidence Symmetry Matrix

| Evidence dimension | BUY_NEW | BUY_ADD | REENTRY | Cash |
| --- | --- | --- | --- | --- |
| Lifecycle authority | Opens a new campaign when current quantity is zero. | Extends an existing open campaign only after PM ADD, PC target increase, PS positive delta, and G129 order-increment authority. | New campaign after prior full EXIT; retains REENTRY provenance and prior-exit context. | Portfolio-level optionality competitor; no security lifecycle. |
| Candidate/opportunity evidence | Mature candidate/opportunity path, rank/score, BUY Quality, Entry, incremental eligibility, portfolio fit. | Existing-position path with PM continuation, current weight, campaign continuation, expected edge, incremental value, opportunity cost, no-loss, BQ/Entry ADD action. | BUY_NEW-like current opportunity evidence plus residual REENTRY protection and prior-exit provenance. | Cash optionality and capital preservation evidence. |
| Target semantics | Total position target from zero. | Incremental target above current weight. | Total position target from zero after requalification. | Reserve/no-deploy capital target. |
| Quantity semantics | Positive target quantity from zero maps to BUY_NEW. | Only positive delta maps to BUY_ADD. Zero delta remains no order. | Positive target quantity from zero maps to REENTRY/BUY. | No order quantity. |
| Evidence completeness in EC window | Generally complete and feasible on dates where ADD is UNKNOWN. | Frequently UNKNOWN/BLOCKED/INSUFFICIENT at incremental value and opportunity-cost layers. | Often numerous, but completeness varies with prior-context and current evidence. | Complete in same-day ADD UNKNOWN date set. |
| Opportunity-cost comparability | Has mature cross-sectional alternative evidence. | Partial; `NEW_BUY_SUPERIOR` often occurs when ADD incremental value is UNKNOWN, so the label is not always a clean economic pairwise defeat. | Similar to BUY_NEW after REENTRY safety/provenance passes. | Comparable as optionality, but not lot/execution equivalent. |
| Production consumer status | Active. | Active only through existing PC/PS/G129 bridge; EC strength-to-increment authority is not consumed. | Active after REENTRY gates. | Active. |

## Findings

### BUY_NEW Value Evidence Pipeline

BUY_NEW has the most mature and complete evidence path. It starts from current
candidate/opportunity evidence, consumes BUY Quality and Entry, passes through
Portfolio Construction as a new target membership decision, then Position Sizing
materializes total target notional/quantity from zero. Runtime Planning maps the
positive zero-to-position delta to BUY_NEW. In the audited dates where ADD
incremental value was UNKNOWN, NEW rows were complete and feasible in 91 of 92
same-day cases.

### BUY_ADD Value Evidence Pipeline

BUY_ADD is intentionally stricter. The current path is:

`PM ADD intent -> canonical position decision / PC ADD allocation bridge -> ADD investment evidence -> BQ/Entry ADD interpretation -> current-weight vs target-weight delta -> accepted incremental weight -> PS executable positive delta -> Runtime BUY_ADD -> G129 Submit authority`.

This is correct as a control boundary. The gap is that the incumbent's next
capital unit does not yet have the same high-resolution, pairwise marginal value
expression as NEW. Of 152 ADD rows, 116 have `incremental_value=UNKNOWN`, and 84
are labeled `NEW_BUY_SUPERIOR` while still having
`COMPARISON_INSUFFICIENT`. That profile does not prove the incumbent is
economically inferior in every case; it proves the ADD side often lacks complete
positive marginal-value authority.

### REENTRY Value Evidence Pipeline

REENTRY remains a lifecycle/provenance classification for a currently flat
symbol. After residual protection and prior-exit context checks pass, current
BUY authority owns the new funding decision. It is closer to BUY_NEW total-target
sizing than to ADD incremental sizing, while preserving prior campaign lineage
and not becoming fake BUY_NEW.

### Cash Value Evidence Pipeline

Cash is a valid capital competitor and was present as a complete same-day
competitor in all 92 ADD-UNKNOWN date cases. Cash has no lot/execution quantity
constraint, so comparability is portfolio-level rather than security-order-level.

## Root-Cause Characterization

`ADD_INCREMENTAL_VALUE_UNKNOWN` is not a single bug class.

Observed root-cause profile:

- `NO_POSITIVE_DESIRED_INCREMENT` dominates (`92/116` UNKNOWN rows). The current
  Production target/current-weight relationship does not request a positive ADD
  increment even when PM/strategy evidence may show incumbent strength.
- `NO_ACCEPTED_CONTINUOUS_INCREMENT` appears in `16/116` rows. Some rows have a
  conceptual increment path but do not survive PC continuous acceptance.
- `BQ_BLOCKS_INCREMENT` appears in `8/116` rows. This is a legitimate
  action-specific safety/quality block unless separately contradicted by PIT
  evidence.
- `76/116` UNKNOWN rows are classified as opportunity-quality `BLOCKED`; `40/116`
  are `INSUFFICIENT`.
- `36/84` `NEW_BUY_SUPERIOR` rows had `expected_edge=IMPROVING`, showing cases
  where same-day ADD may be blocked by missing/incomplete incremental value
  representation rather than by obvious weakening.
- `42/84` `NEW_BUY_SUPERIOR` rows had `expected_edge=WEAKENING`, showing a real
  legitimate negative subset that must continue to be blocked.

Therefore the profile is mixed:

`SEMANTIC_REPRESENTATION_GAP + MISSING_INCREMENTAL_VALUE_AUTHORITY + LEGITIMATE_NEGATIVE_OR_INSUFFICIENT_CASES`.

ED did not find evidence that this is primarily a downstream propagation bug,
G129 defect, or Strategy performance defect.

## Control Cases

Selected incumbent controls:

- `94320`: 50 ADD rows; `UNKNOWN=33`, `POSITIVE=17`; opportunity cost
  `PASS=34`, `NEW_BUY_SUPERIOR=16`; EC demand `BLOCKED=27`,
  `NO_POSITIVE_DEMAND=14`, `POSITIVE_INCREMENT_DEMAND=9`.
- `99840`: 26 ADD rows; `UNKNOWN=15`, `POSITIVE=11`; opportunity cost
  `NEW_BUY_SUPERIOR=13`, `PASS=13`; EC demand `BLOCKED=20`,
  `NO_POSITIVE_DEMAND=6`.
- `94340`: 20 ADD rows; `UNKNOWN=16`, `POSITIVE=4`; opportunity cost
  `NEW_BUY_SUPERIOR=15`, `PASS=5`.
- `83060`: 15 ADD rows; `UNKNOWN=13`, `POSITIVE=2`; opportunity cost
  `PASS=10`, `NEW_BUY_SUPERIOR=5`.
- `43880`: 12 ADD rows; all `UNKNOWN`; all `NEW_BUY_SUPERIOR`.

These controls confirm that incumbent evidence exists but is not consistently
materialized as a comparable next-capital-unit value.

## Production Behaviors To Preserve

The current Production behavior is valuable and should be preserved while any
future evidence repair is designed:

- PM ADD must remain intent, not order or quantity authority.
- PC must remain scarce-capital and target-weight authority.
- PS must remain executable quantity authority.
- Runtime must remain a mapper, not a reranker.
- BQ/Entry hard blocks must remain fail-closed.
- Zero desired ADD must not resurrect into positive BUY_ADD.
- G129 positive BUY_ADD remains order-increment scoped.
- REENTRY provenance and prior EXIT context must remain explicit.
- Cash remains a valid competitor.
- EC/DW/DQ SHADOW evidence must not become Production authority without a
  separate acceptance phase.

## Repair Assessment

Production repair is not justified as an immediate target/weight/selection
change from ED alone. ED does justify a future evidence/SHADOW contract step:
represent incumbent next-capital-unit value more explicitly and symmetrically
before any Production promotion.

Narrowest safe future boundary:

- Add or refine a PC-owned, PIT-only, action-aware marginal-capital evidence
  layer that gives BUY_NEW, BUY_ADD, REENTRY, and Cash comparable
  next-capital-unit records.
- Preserve ADD as incremental, not total-target.
- Preserve BQ/Entry, concentration, headroom, lot, and G129 gates.
- Keep authoritative consumer count at zero until shadow validation proves
  Production readiness.
- Do not change Strategy thresholds, weights, candidate ranking, cash policy, or
  runtime mapping in this audit.

Expected portfolio behavior impact if such a future repair is eventually
accepted is potentially material, because the audited window contains 116 ADD
UNKNOWN rows, 84 `NEW_BUY_SUPERIOR` rows with comparison insufficiency, and 92
dates where ADD incompleteness coexisted with generally complete NEW/Cash
evidence. ED does not use PnL to select a repair.

## Required Final Answers

1. `CURRENT_PRODUCTION_CONTROL_PRESERVED = YES`
2. `BUY_NEW_VALUE_EVIDENCE_PIPELINE = Candidate/Opportunity + BUY Quality + Entry + incremental eligibility + PC total target from zero + PS lot quantity + Runtime BUY_NEW`
3. `BUY_ADD_VALUE_EVIDENCE_PIPELINE = PM ADD intent + campaign/current-position evidence + PC ADD bridge + incremental value/opportunity cost/no-loss/BQ/Entry/headroom + PS positive delta + Runtime BUY_ADD + G129`
4. `REENTRY_VALUE_EVIDENCE_PIPELINE = prior-exit/provenance protection + renewed PIT BUY authority + PC total target from zero + PS quantity; REENTRY remains lifecycle-explicit`
5. `CASH_VALUE_EVIDENCE_PIPELINE = portfolio optionality/reserve competitor evidence; complete in same-day ADD-UNKNOWN date set`
6. `MARGINAL_VALUE_EVIDENCE_SYMMETRY_MATRIX = PARTIAL; NEW/REENTRY/Cash have more complete comparable records than ADD next-increment evidence`
7. `ADD_INCREMENTAL_VALUE_UNKNOWN_ROOT_CAUSE_PROFILE = MIXED_SEMANTIC_REPRESENTATION_GAP_AND_MISSING_INCREMENTAL_AUTHORITY_WITH_LEGITIMATE_NEGATIVE_SUBSET`
8. `SAME_DAY_NEW_VS_ADD_EVIDENCE_COMPLETENESS = NEW complete and feasible on 91/92 ADD-UNKNOWN dates; Cash complete on 92/92; ADD frequently UNKNOWN`
9. `NEW_BUY_SUPERIOR_ROOT_CAUSE_PROFILE = MIXED; often comparison-insufficient ADD evidence, not always clean pairwise economic superiority`
10. `PAIRWISE_MARGINAL_VALUE_COMPARABILITY = PARTIAL`
11. `AVAILABLE_INCUMBENT_VALUE_EVIDENCE = PM ADD reasons, campaign continuity, current quantity/weight, expected edge, incremental value state, opportunity cost state, no-loss, BQ/Entry action, headroom, lot/execution feasibility, DQ/DW/EC shadow records`
12. `INCUMBENT_VALUE_GAP_TYPE = SEMANTIC_REPRESENTATION_GAP_PLUS_MISSING_AUTHORITY; not primarily G129 or downstream Submit propagation`
13. `BQ_ENTRY_CROSS_ACTION_SYMMETRY = PARTIAL_ACTION_SPECIFIC_EQUIVALENT`
14. `TARGET_WEIGHT_ASYMMETRY_JUDGMENT = NECESSARY_BUT_INCOMPLETE`
15. `NEXT_CAPITAL_UNIT_COMPARABILITY = PARTIAL`
16. `94320_INCREMENTAL_VALUE_CONTROL = MIXED; 50 rows, 33 UNKNOWN, 17 POSITIVE, 9 EC positive increment demand rows`
17. `FAILED_GRADUATION_VALUE_EVIDENCE_CONTROLS = 94340/99840/83060/43880 and others show repeated incumbent evidence without durable comparable positive increment authority`
18. `2023_JUN_SEP_ADD_VALUE_EVIDENCE_ROOT_CAUSE = 20 ADD rows; 16 UNKNOWN; 14 NEW_BUY_SUPERIOR; mostly BLOCKED or NO_POSITIVE_DEMAND, confirming persistent ADD evidence asymmetry`
19. `PRODUCTION_BEHAVIORS_TO_PRESERVE = PM intent boundary, PC allocation authority, PS quantity authority, Runtime mapper role, BQ/Entry fail-closed, zero ADD preservation, G129, REENTRY provenance, Cash competitor`
20. `CURRENT_VS_DESIRED_PHILOSOPHY_ALIGNMENT = PARTIAL; current control is correct but desired philosophy needs more symmetric marginal-value evidence before stronger winner capitalization`
21. `PRODUCTION_REPAIR_JUSTIFIED = CONDITIONAL; evidence repair/shadow refinement justified, direct Production allocation change not justified by ED alone`
22. `NARROWEST_SAFE_REPAIR_BOUNDARY = PC-owned PIT marginal-capital evidence normalization for incumbent next-increment value and opportunity cost, initially SHADOW-only`
23. `EXPECTED_PORTFOLIO_BEHAVIOR_IMPACT = POTENTIALLY_MATERIAL_BUT_UNPROVEN_BY_ED`
24. `HISTORICAL_PERFORMANCE_USED_FOR_REPAIR_SELECTION = NO`
25. `PRODUCTION_CHANGE_EXECUTED = NO`
26. `SHADOW_CHANGE_EXECUTED = NO`
27. `TARGET_RUN_MUTATED = NO`
28. `RUNTIME_STATE_MUTATED = NO`
29. `LONG_RUNTIME_EXECUTED = NO`
30. `NEXT_RECOMMENDED_STEP = Design a SHADOW-only PC marginal-capital evidence symmetry contract for BUY_NEW/BUY_ADD/REENTRY/Cash, preserving all Production controls`
31. `FINAL_JUDGMENT = PHASE32_ED_NEW_VS_ADD_MARGINAL_VALUE_EVIDENCE_ASYMMETRY_CONFIRMED_CONDITIONAL_SHADOW_EVIDENCE_REPAIR_RECOMMENDED_NO_PRODUCTION_CHANGE`

