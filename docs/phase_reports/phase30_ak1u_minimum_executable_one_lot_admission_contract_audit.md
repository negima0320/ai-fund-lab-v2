# Phase30-AK1U - Minimum Executable One-Lot Admission Contract Audit

## Scope

Task ID: `Phase30-AK1U`

Type: `READ_ONLY_DESIGN_CONFORMANCE_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260816T121454359538Z
```

No implementation, threshold change, cap change, forced BUY, fixed exposure,
Candidate/model change, lot-size change, resume/replay/fresh run, or target run
mutation was performed.

AK1U audit read point:

```text
LATEST_STRATEGY_ARTIFACT_DATE_READ = 2023-10-23
LATEST_DAILY_DIRECTORY_PRESENT = 2023-10-24
```

Canonical quantitative population is the Phase30-AK1T frozen PC-positive
BUY_NEW / REENTRY population:

```text
SOURCE_CUTOFF_DATE = 2023-10-10
SOURCE_COMPLETED_BUSINESS_DAYS = 287
```

AK1U uses AK1T evidence as architecture-conformance input only. No performance
or future return was used for parameter selection.

## Primary Judgment

```text
MINIMUM_EXECUTABLE_ONE_LOT_SEMANTIC_CONFORMS_TO_ARCHITECTURE = YES
ONE_LOT_ROUND_UP_PRESERVES_PC_INTENT = YES
ONE_LOT_LINEAGE_CLASSIFICATION = PRE_EXISTING_INCOMPLETE_ACTION_EFFECT
MINIMUM_ONE_LOT_POLICY_CONFORMS_TO_INVESTMENT_PHILOSOPHY = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

The intended Production-common design already contains the idea that Portfolio
Construction may authorize a minimum executable lot after Position Sizing has
shown the discrete-lot economics. This is not a new forced-buy policy.

However, AK1T showed that the current action path is still not effective enough
for BUY_NEW / REENTRY sub-lot targets. A candidate can have positive PC
allocation intent, but final runtime executable quantity still overwhelmingly
collapses to zero when target notional is below one lot.

## Original One-Lot Admission Purpose

```text
ORIGINAL_ONE_LOT_ADMISSION_PURPOSE =
Prevent excessive zero-rounding when continuous PC target weights are converted
to Japanese 100-share execution units, while preserving PC allocation authority,
PS quantity authority, opportunity cost, cash as a valid endpoint, Strategy cap,
Safety hard cap, broker feasibility, and entry/risk guards.
```

Reviewed design lineage:

- Phase28-D54: designed the two-pass PC economic draft -> PS lot feasibility
  preflight -> PC final reallocation -> PS final sizing contract.
- Phase28-D55-B: implemented lot-aware PC/PS capital conversion without forced
  one-lot behavior.
- Phase29-L19: separated Strategy cap and Safety hard cap, added cap-constrained
  lot floor and residual recycling evidence.
- Phase30-V/W: added quality-adjusted one-lot admission so Safety hard-cap pass
  alone cannot authorize Strategy concentration overshoot.

The purpose did include preventing over-rounding to zero. It also explicitly
did not mean `target_weight > 0` always buys one lot.

## Current One-Lot Contract

```text
CURRENT_ONE_LOT_ADMISSION_CONTRACT =
PC prepares BUY_NEW / BUY_ADD participants; PS preflight supplies reference
price, trading unit, one_lot_weight, one_lot_notional, cap headroom, and
boundary classification; PC may promote a positive request below one lot to
minimum_executable_weight only if one_lot_fallback applies, Safety hard cap is
preserved, broker/lot feasibility is available, quality-adjusted one-lot
admission passes, Strategy cap/soft-overshoot rules pass, and remaining budget
is sufficient. PS then remains final quantity authority.
```

Implementation references:

- `apply_lot_aware_final_reallocation` promotes sub-lot requests to
  `minimum_executable_weight` only after PS lot preflight evidence exists.
- `_quality_adjusted_reallocation_order` prioritizes healthy/allowed entries
  over caution and BUY_WAIT/reversal/overheated states.
- `_quality_adjusted_one_lot_admission` fail-closes Safety hard-cap breaches,
  defers BUY_WAIT / overheated / reversal entry states, and allows BUY_NEW only
  for `BUY_NEW_ALLOWED`, `BUY_NEW_REDUCED_ONLY`, or backward-compatible empty
  action.
- Position Sizing owns reference price, trading unit, one-lot notional, and
  final quantity.

## Sub-Lot Admission Blockers

Canonical AK1T source population:

```text
PC_POSITIVE_TOTAL = 4,246
ALLOCATION_SUCCESS_COUNT = 170
PC_POSITIVE_FINAL_ZERO_COUNT = 4,076
```

Target-to-one-lot curve:

| target / one-lot | total | success | zero | success rate |
| --- | ---: | ---: | ---: | ---: |
| `<0.5` | 1,873 | 0 | 1,873 | 0.0000 |
| `0.5-<0.75` | 252 | 0 | 252 | 0.0000 |
| `0.75-<1.0` | 880 | 3 | 877 | 0.0034 |
| `1.0-<1.5` | 1,015 | 43 | 972 | 0.0424 |
| `>=1.5` | 226 | 124 | 102 | 0.5487 |

```text
SUB_LOT_ADMISSION_BLOCKER_DISTRIBUTION = {
  LOT_ECONOMICS_FRICTION: 2250,
  GENUINE_EXECUTION_CONSTRAINT: 752
}
```

For the focused `0.75 <= target/lot < 1.0` bucket:

```text
TOTAL = 880
SUCCESS = 3
ZERO = 877
BLOCKER_DISTRIBUTION = {
  LOT_ECONOMICS_FRICTION: 877
}
```

This is the key AK1U finding. The near-one-lot bucket is not primarily failing
because of explicit Entry rejection, Safety breach, or Strategy cap breach. It
is failing because final executable conversion remains highly sensitive to
being just below one lot.

## Minimum Executable Position Semantics

```text
MINIMUM_EXECUTABLE_ONE_LOT_SEMANTIC_CONFORMS_TO_ARCHITECTURE = YES
```

For BUY_NEW / REENTRY with current quantity zero, one lot is the minimum real
execution unit. If PC has issued positive allocation and the candidate passes
Quality, Entry, Risk, Cash, Strategy cap, Safety cap, lifecycle, broker, and
corporate-action guards, rounding up to one executable lot preserves the
investment intent better than rounding down to zero.

This semantic is limited to the first executable lot. It does not apply to
existing-position ADD or to 1lot -> 2lot+ increases in this audit.

## PC Authority Preservation

```text
ONE_LOT_ROUND_UP_PRESERVES_PC_INTENT = YES
```

When PC target is 70,000 JPY and one executable lot is 100,000 JPY, both 0 and
100,000 are approximations. Under the required guards, 100,000 is closer to
PC's positive allocation intent because it represents the minimum executable
expression of that intent. Position Sizing does not become allocation authority
because PS only supplies the executable lot facts; PC must explicitly authorize
the promoted final target.

## Required Guards

```text
MINIMUM_ONE_LOT_REQUIRED_GUARDS = [
  "PC positive BUY_NEW / REENTRY target",
  "current quantity = 0",
  "one-lot only; no ADD and no second-lot expansion",
  "Entry Admission PASS or reduced-only allowed",
  "BUY_WAIT / REJECT / REVIEW_REQUIRED blocked",
  "OVERHEATED_DECELERATING_ENTRY and REVERSAL_RISK_ENTRY deferred",
  "Downside Risk not fail-closed",
  "Selection / Candidate quality not reject",
  "liquidity and price/tick risk acceptable",
  "reference price PIT authority PASS",
  "tradable unit and broker feasibility PASS",
  "cash and remaining budget sufficient",
  "Strategy concentration cap preserved or explicitly permitted within policy",
  "Safety hard cap never breached",
  "lifecycle and pending conflict clear",
  "corporate action / listing ambiguity not blocking",
  "residual recycling and opportunity cost respected",
  "future_information_used = false"
]
```

## Concentration Impact

```text
ONE_LOT_PROJECTED_WEIGHT_DISTRIBUTION = {
  "<=5%":     {total: 1009, success: 139, zero: 870},
  ">5-10%":   {total: 1077, success: 10,  zero: 1067},
  ">10-15%":  {total: 726,  success: 12,  zero: 714},
  ">15-18%":  {total: 255,  success: 2,   zero: 253},
  ">18-25%":  {total: 427,  success: 7,   zero: 420},
  ">25%":     {total: 752,  success: 0,   zero: 752}
}

ONE_LOT_OVER_STRATEGY_CAP_COUNT = 1179
ONE_LOT_OVER_SAFETY_CAP_COUNT = 752
```

The concentration risk is real. A one-lot exception cannot simply buy any
sub-lot positive target. Safety hard-cap breaches must remain terminal.
Strategy cap overshoot must remain narrow, explicit, and evidence-backed.

## Scope Boundary

```text
ONE_LOT_EXCEPTION_SCOPE = {
  BUY_NEW_MINIMUM_ONE_LOT: "candidate",
  REENTRY_MINIMUM_ONE_LOT: "candidate",
  BUY_ADD_MINIMUM_ONE_LOT: "out of scope",
  SECOND_LOT_AND_ABOVE: "out of scope"
}
```

## Existing Contract vs Repair

```text
ONE_LOT_LINEAGE_CLASSIFICATION = PRE_EXISTING_INCOMPLETE_ACTION_EFFECT
```

This is not a new policy decision from scratch, and not a rollback. The
architecture already intended controlled one-lot admission, but AK1T proves
that action-effect is incomplete for BUY_NEW / REENTRY sub-lot targets,
especially near one lot.

This is also not a Runtime defect:

```text
PC_PS_RUNTIME_DEFECT = NO
```

It is a production-common Strategy/PC/PS authority-effectiveness gap:

```text
PC_PS_AUTHORITY_DEFECT = YES
```

## Philosophy Conformance

```text
MINIMUM_ONE_LOT_POLICY_CONFORMS_TO_INVESTMENT_PHILOSOPHY = YES
```

The policy conforms only with guards. It preserves:

- Opportunity absent -> Cash is valid.
- No forced BUY, exposure, or position count.
- Quality and risk first.
- Japanese 100-share lots as real execution units.
- Strategy cap and Safety hard cap separation.
- No winner concentration policy change.
- No historical outcome fitting.

## Required Final Judgments

```text
ORIGINAL_ONE_LOT_ADMISSION_PURPOSE =
Prevent excessive zero-rounding of positive PC target weights at the Japanese
100-share execution boundary, under PC-controlled and guard-constrained
minimum executable allocation.

CURRENT_ONE_LOT_ADMISSION_CONTRACT =
PARTIAL_ACTION_EFFECTIVE: PC has explicit one-lot admission and can promote
minimum executable weight, but canonical AK1T runtime evidence shows sub-lot
BUY_NEW / REENTRY still almost always materializes as zero final quantity.

SUB_LOT_ADMISSION_BLOCKER_DISTRIBUTION = {
  LOT_ECONOMICS_FRICTION: 2250,
  GENUINE_EXECUTION_CONSTRAINT: 752
}

MINIMUM_EXECUTABLE_ONE_LOT_SEMANTIC_CONFORMS_TO_ARCHITECTURE = YES
ONE_LOT_ROUND_UP_PRESERVES_PC_INTENT = YES

ONE_LOT_PROJECTED_WEIGHT_DISTRIBUTION = {
  <=5%: 1009,
  >5-10%: 1077,
  >10-15%: 726,
  >15-18%: 255,
  >18-25%: 427,
  >25%: 752
}

ONE_LOT_OVER_STRATEGY_CAP_COUNT = 1179
ONE_LOT_OVER_SAFETY_CAP_COUNT = 752

ONE_LOT_EXCEPTION_SCOPE =
BUY_NEW / REENTRY 0 -> 1lot only; ADD and second-lot-plus are out of scope.

ONE_LOT_LINEAGE_CLASSIFICATION = PRE_EXISTING_INCOMPLETE_ACTION_EFFECT
MINIMUM_ONE_LOT_POLICY_CONFORMS_TO_INVESTMENT_PHILOSOPHY = YES
IMPLEMENTATION_REPAIR_JUSTIFIED = YES
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK1U
```

## Evidence Files

```text
reports/phase_reports/phase30_ak1u/ak1t_canonical_one_lot_design_distribution.json
reports/phase_reports/phase30_ak1u/sub_lot_zero_canonical.csv
reports/phase_reports/phase30_ak1u/ratio_075_1_zero_canonical.csv
reports/phase_reports/phase30_ak1u/analysis_summary.json
reports/phase_reports/phase30_ak1u/pc_positive_buy_new_reentry_rows.csv
reports/phase_reports/phase30_ak1u/sub_lot_zero_rows.csv
reports/phase_reports/phase30_ak1u/ratio_075_1_zero_rows.csv
reports/phase_reports/phase30_ak1u/strict_suspicious_rows.csv
```

## Recommended Next Task

```text
Phase30-AK2 - Minimum Executable One-Lot Admission Repair Implementation
```

Repair scope should be narrow:

```text
BUY_NEW / REENTRY
current quantity = 0
0 -> 1lot only
all AK1U guards preserved
no forced exposure
no cap loosening
no ADD / second-lot behavior change
```
