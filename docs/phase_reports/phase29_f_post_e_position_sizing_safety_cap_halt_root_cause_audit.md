# Phase29-F Post-E 100BD Position Sizing Safety-Cap HALT Root Cause Audit

Status:

```text
COMPLETE
READ_ONLY ROOT CAUSE AUDIT
NO IMPLEMENTATION
```

Primary Judgment:

```text
PHASE29_F_POST_E_SAFETY_CAP_HALT_LEGITIMATE_SAFETY_BLOCK_ARCHITECTURE_GAP_CONFIRMED
```

## 1. Scope

Phase29-F audited the Phase29-E/E2 approved fresh 100BD run:

```text
runtime-test-historical-smoke-20260809T141932598150Z
```

The run halted on:

```text
2023-06-16 morning
```

No Production code, config, schema, Runtime artifact, Pending artifact, test
fixture, fresh run, resume, 100BD, or Historical execution was changed or run.

Evidence:

```text
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/root_cause.json
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/five_symbol_authority_trace.csv
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/failing_row_trace.json
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/pc_ps_authority_matrix.json
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/previous_day_comparison.json
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/causality_classification.json
reports/phase29_f_post_e_position_sizing_safety_cap_halt_root_cause_audit/resume_gate.json
```

## 2. Direct Halt

Runtime root reason:

```text
morning pipeline review required: strategy_planning_authority_unresolved
```

Strategy Planning Authority unresolved symbols:

```text
21340
40520
67310
94320
99840
```

Direct Strategy shadow error:

```text
Position Sizing Preflight = BLOCK / target_weight_above_safety_cap:0
Position Sizing = BLOCK / target_weight_above_safety_cap:0
Runtime Planning = REVIEW_REQUIRED / upstream_block_propagation:position_sizing_or_portfolio_construction
```

Safety behavior was fail-closed. Broker write and external delivery were false,
Strategy shadow did not mutate Runtime authority, and no downstream execution
proceeded from unresolved quantity.

## 3. Failing Row

`target_weight_above_safety_cap:0` is:

```text
Position Sizing input row 0
symbol = 21340
source = portfolio_construction.json portfolio_members[0]
```

Relevant PC final row values:

```text
membership_intent = RETAIN
pm_action = ADD
current_quantity = 8200
current_weight = 0.262811
target_weight = 0.262811
accepted_incremental_weight = 0.0
lot_aware_accepted_incremental_weight = 0.0
target_weight_change = 0.0
lot_first_rebatch_participant = false
```

The row was not a request-positive rebatch participant and was not preflight-only
evidence. It was a final PC member representing retained existing exposure with
zero executable ADD increment.

## 4. Cap Values

There are two distinct caps:

```text
Portfolio Policy / Strategy single-name cap = 0.18
Safety hard concentration cap = 0.25
```

The error name is `target_weight_above_safety_cap`, and the direct PS comparison
is:

```text
position.target_weight > safety_cap + 0.000001
0.262811 > 0.25 + 0.000001
```

Therefore the absolute Safety cap violation is real:

```text
True cap violation = YES
True executable increment violation = NO
```

## 5. Why PC Passed

PC passed because it preserves existing retained baseline/current exposure and
applies the 0.18 single-name cap to incremental allocation headroom. For 21340,
PC formed no executable ADD:

```text
accepted_incremental_weight = 0.0
lot_aware_accepted_incremental_weight = 0.0
target_weight_change = 0.0
```

This is consistent with the D61/D69 ADD-zero semantics:

```text
PM ADD + no positive executable headroom = valid zero/no-action candidate
```

PC did not create a Phase29-E rebatch overweight. The overweight was the existing
position's current valuation drift.

## 6. Why PS Blocked

PS validates produced absolute `target_weight` against the independent Safety
hard concentration cap. In code, `_validate_position(...)` checks:

```text
target_weight_above_safety_cap:<index>
```

for any target above `safety_maximum_position_weight`.

Position cap validation has a directionally allowed exception for retained
existing baseline/no-increment cases, but the independent Safety hard-cap check
does not use that exception. On 2023-06-16 that distinction mattered for the
first time because 21340 crossed 0.25.

This is not a D69 signed-delta regression. `target_weight_change` remained
observability and was zero. PS did not consume it as executable ADD authority.

## 7. Previous Day Comparison

On 2023-06-15, 21340 was already above the Strategy 0.18 cap:

```text
current_weight = target_weight = 0.234346
pm_action = HOLD
PS status = PASS
Safety hard cap = 0.25
```

On 2023-06-16:

```text
current_weight = target_weight = 0.262811
pm_action = ADD
PS status = BLOCK
Safety hard cap = 0.25
```

Search across completed days found many successful retained-baseline cases above
0.18, but 2023-06-16 was the first and only case through the halt where a
current/final target exceeded the independent Safety hard cap 0.25.

## 8. Five-Symbol Summary

The five unresolved symbols are downstream symptoms of the PS block:

| Symbol | Type | PC Final Target | Final Increment | Runtime Quantity |
|---|---|---:|---:|---|
| 21340 | ADD retained existing | 0.262811 | 0.000000 | unresolved by upstream block |
| 94320 | ADD retained existing | 0.159823 | 0.000000 | unresolved by upstream block |
| 67310 | BUY_NEW candidate | 0.000000 | 0.000000 | unresolved by upstream block |
| 40520 | BUY_NEW candidate | 0.000000 | 0.000000 | unresolved by upstream block |
| 99840 | BUY_NEW candidate | 0.000000 | 0.000000 | unresolved by upstream block |

The failing row is only 21340. The other four appear unresolved because
Position Sizing stopped before producing final quantity authority.

## 9. Classification

Root Cause classification:

```text
F — LEGITIMATE_SAFETY_BLOCK
```

Phase29-E causality classification:

```text
F4 — LEGITIMATE_SAFETY_BLOCK
Phase29-E causal = NO
```

More precise wording:

```text
LEGITIMATE_SAFETY_BLOCK_WITH_PC_PS_OBSERVABILITY_ARCHITECTURE_GAP
```

The block is legitimate because the produced absolute target/current weight
exceeded independent Safety hard cap 0.25. The architecture gap is that PC can
PASS retained baseline drift beyond the Safety hard cap and leave PS to surface
it as a shadow schema error rather than a rich symbol-level Safety drift block.

## 10. D61 / D69 / Rebatch

D61 preserved:

```text
YES
```

21340 has zero accepted incremental ADD authority.

D69 preserved:

```text
YES
```

`target_weight_change` is not used as executable ADD authority.

Phase29-E rebatch causal:

```text
NO
```

21340 was not a rebatch participant, no rebatch allocation was made on 2023-06-16,
and no repeated recycle pass accumulated the symbol above cap.

Capital conservation:

```text
PASS
```

Per-symbol concentration/Safety:

```text
Safety hard cap exceeded by existing 21340 current weight.
```

## 11. Resume Gate

Fresh-run required:

```text
NO
```

Resume under unchanged code:

```text
NO, expected to hit the same halt.
```

Resume after operator decision or focused repair:

```text
YES
```

The failed job was morning planning, broker write and external delivery were
false, Strategy shadow did not mutate Runtime authority, and no downstream
Runtime execution followed the unresolved plan.

## 12. Required Future Regression Contract

Next repair/design task should include:

```text
REG-1 request-positive preference > cap but final executable target <= cap -> PS PASS
REG-2 PC final executable target > cap -> fail-closed BLOCK
REG-3 existing ADD current weight + one lot <= cap -> valid ADD
REG-4 existing ADD current weight + one lot > cap -> ADD zero/no-action, same-symbol recycle prohibited
REG-5 preflight-only row must not masquerade as final target authority
REG-6 rebatch multiple pass must not accumulate above cap
REG-7 D61 current-baseline semantics preserved
REG-8 D69 signed observability preserved
REG-9 Safety block must not be bypassed
REG-10 Capital conservation remains PASS
REG-11 existing retained baseline above Safety hard cap is surfaced as explicit Safety drift block, not schema-style shadow generation error
```

## 13. Recommended Next Task

```text
Phase29-G PC/PS Safety-Cap Drift Authority and Observability Repair Design
```

Repair goal should not be to bypass Safety. It should decide and implement the
proper Production-common authority boundary for retained existing positions that
drift above the independent Safety hard cap:

```text
Either PC blocks earlier with explicit symbol-level Safety hard-cap drift evidence,
or PS materializes a rich BLOCK artifact that Runtime Planning can report without
schema-error ambiguity.
```

## 14. Final Judgment

```text
PHASE29_F_POST_E_SAFETY_CAP_HALT_LEGITIMATE_SAFETY_BLOCK_ARCHITECTURE_GAP_CONFIRMED
```

