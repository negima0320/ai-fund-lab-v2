# Phase31-G82 — Post-G81 Fresh-Run First-Day Zero-BUY Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G82_POST_G81_FIRST_DAY_ZERO_BUY_CAUSE_CONFIRMED_REPAIR_REQUIRED

## Scope

READ-ONLY actual-artifact audit only.

- Pre-G81 comparison run: `runtime-test-historical-extended-smoke-20260823T140946562431Z`
- Post-G81 target run: `runtime-test-historical-extended-smoke-20260823T230627195532Z`
- Target business date: `2022-10-03`
- No code/config/threshold/weight changes.
- No fresh-run, resume, replay, or long Historical execution by Codex.
- No current run mutation.
- No future information or Historical outcome was used as Strategy input.

## Executive Conclusion

The first-day zero-BUY is caused by the interaction of:

1. Existing `2022-10-03` bootstrap evidence classifying all selected positive security competitors as `CASH_PREFERRED`.
2. G81 making `CASH_PREFERRED` binding at final PC security/Cash partition.
3. No separate bootstrap participation semantic preserving reduced exploratory allocation for empty / near-empty portfolio state.

The first divergence is inside:

```text
Portfolio Construction
-> capital_competition.canonical_multi_allocation_deployment_set
-> security_allocations / cash_preferred_security_deferrals
```

G81 is directly causal for the change from pre-G81 positive security allocation to post-G81 zero security allocation, but the deeper design gap is that the producer uses the same `CASH_PREFERRED` result for both:

- weak-tail optional Cash preference in already-deployed / plateau contexts, and
- valid reduced-risk bootstrap participation contexts.

Do not solve this by reverting G81. G80 remains valid: weak-tail `CASH_PREFERRED` rows must not consume capital merely because Cash is calculated as residual. The repair should distinguish bootstrap participation from weak-tail optional Cash preference using existing architecture authority, not Historical thresholds.

## Stage-by-Stage Evidence

| Stage | Pre-G81 `140946...` | Post-G81 `230627...` | Diff |
| --- | ---: | ---: | --- |
| BUY decision count | 50 | 50 | same |
| BUY action distribution | BUY_WAIT 16, FULL 1, REDUCED 22, REJECT 11 | BUY_WAIT 16, FULL 1, REDUCED 22, REJECT 11 | same |
| Portfolio Policy risk pacing | `CAUTIOUS_DEPLOYMENT` | `CAUTIOUS_DEPLOYMENT` | same |
| Capital budget | `0.74` | `0.74` | same |
| Capacity state | `SELECTIVE_DEPLOYMENT_CAPACITY` | `SELECTIVE_DEPLOYMENT_CAPACITY` | same |
| Cash/bootstrap state | `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP` | `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP` | same |
| PC competitors | 22 | 22 | same |
| Market-candidate-Cash `DEPLOY_ELIGIBLE` | 0 | 0 | same |
| Market-candidate-Cash `SELECTIVE_COMPETITION` | 0 | 0 | same |
| Market-candidate-Cash `CASH_PREFERRED` | 9 | 9 | same |
| Market-candidate-Cash `FAIL_CLOSED` | 13 | 13 | same |
| Final security allocations | 9 | 0 | first divergence |
| G81 Cash-preferred deferrals | not available / 0 | 9 | G81 binding activated |
| Authorized Cash allocation | `0.003286` | `0.74` | deferred budget returned to Cash |
| G61 compatibility rows | 9 | 0 | follows PC allocation |
| G61 lot executable count | 9 | 0 | follows PC allocation |
| Runtime BUY plan count | 9 | 0 | follows PS/PC binding |
| Morning pending item count | 9 | 0 | follows Runtime |
| Submit accepted order count | 7 | 0 | follows pending |
| Execution BUY fills | 7 | 0 | follows submit |

## 2022-10-03 Candidate / Policy Equivalence

Candidate and BUY-quality evidence did not materially change between runs.

Top BUY decision evidence was the same in both runs, including:

| Rank | Symbol | runtime opportunity score |
| ---: | --- | ---: |
| 1 | 94320 | 0.40111528 |
| 2 | 76920 | 0.27087727 |
| 3 | 94340 | 0.24034924 |
| 4 | 93180 | -0.07958341 |
| 5 | 44220 | -0.09398367 |
| 6 | 37820 | -0.16026542 |
| 10 | 93600 | -0.20107329 |

Portfolio Policy evidence was also the same:

```text
risk_pacing_intent = CAUTIOUS_DEPLOYMENT
risk_pacing_mode = AUTHORITATIVE
risk_pacing_reason_codes = [RISK_PACING_CAUTIOUS]
deployment_capacity_semantic = SELECTIVE_DEPLOYMENT_CAPACITY
bootstrap_or_residual_cash_state = EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP
available_incremental_budget = 0.74
```

Envelope reason codes included:

```text
CASH_STATE_EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP
DEPLOYMENT_INTENSITY_NOT_SECURITY_ADMISSION
EXPLORATION_PARTICIPATION_RISK_PRESERVED
PROFIT_ENGINE_PRESERVATION_CONTEXT
MARKET_QUALITY_CONTEXT_SHORT_TERM_BREADTH_BREAKDOWN
RISK_PACING_CAUTIOUS
```

Therefore the zero-BUY change is not caused by Candidate set, Candidate rank, Market Quality, Risk Pacing, or capital budget changing between runs.

## PC Interaction Evidence

The same 22 PC competitors existed in both runs.

The same 9 selected positive competitors were all classified as `CASH_PREFERRED`:

| Symbol | Rank | Quality | Accepted weight | Interaction |
| --- | ---: | --- | ---: | --- |
| 94340 | 3 | COMPARABLE_MARGINAL | 0.033636 | CASH_PREFERRED |
| 37820 | 6 | COMPARABLE_MARGINAL | 0.033636 | CASH_PREFERRED |
| 93600 | 10 | COMPARABLE_MARGINAL | 0.191100 | CASH_PREFERRED |
| 33700 | 17 | COMPARABLE_MARGINAL | 0.034100 | CASH_PREFERRED |
| 83060 | 20 | COMPARABLE_MARGINAL | 0.064800 | CASH_PREFERRED |
| 92420 | 21 | COMPARABLE_MARGINAL | 0.137500 | CASH_PREFERRED |
| 58200 | 23 | COMPARABLE_MARGINAL | 0.174670 | CASH_PREFERRED |
| 89180 | 25 | COMPARABLE_MARGINAL | 0.033636 | CASH_PREFERRED |
| 76470 | 26 | COMPARABLE_MARGINAL | 0.033636 | CASH_PREFERRED |

Pre-G81:

```text
security_allocation_count = 9
security_allocation_total = 0.736714
authorized_cash_allocation = 0.003286
cash_preferred_security_deferral_count = not available / 0
```

Post-G81:

```text
security_allocation_count = 0
security_allocation_total = 0
cash_preferred_security_deferral_count = 9
authorized_cash_allocation = 0.74
```

This confirms G81’s final partition repair activated exactly at the causal boundary.

## Downstream Evidence

Post-G81 Position Sizing consumed the zero-allocation G61 compatibility evidence correctly:

```text
g61_compatibility_consumed_by_ps = True
allocation_count = 0
lot_executable_count = 0
position_sizing_recomputes_capital_priority = False
position_sizing_quantity_owner = POSITION_SIZING
```

Post-G81 Runtime Planning consumed PS output correctly:

```text
pc_ps_runtime_executable_binding = PASS
runtime_buy_plan_count = 0
runtime_capital_priority_redecision = False
ps_quantity_binds_runtime = True
cash_winner_redecision_runtime = False
```

Morning / Submit / Execution then correctly no-oped:

```text
morning.status = NO_ORDER_AUTHORIZED
morning.reason = strategy_planning_no_order_authorized
pending_item_count = 0
submitted_order_count = 0
execution_action = NO_ACTION
fills = 0
```

PS/Runtime connectivity is therefore not defective; they are faithfully consuming the PC zero-security result.

## Bootstrap Contract Reconciliation

Current common architecture does not support treating this 2022-10-03 bootstrap case as unconditional 100% Cash merely because selected candidates are `CASH_PREFERRED`.

Relevant SoT:

- `strategy_architecture_v1.md`: empty / near-empty portfolio bootstrap cash is semantically different from residual optionality cash and may justify reduced-risk initial participation when valid opportunities exist.
- `dual_path_market_quality_and_capital_competition_contract.md`: bootstrap must not become a permanent optionality trap; reduced-risk initial entry / initial exploration allocation is defined.
- `phase31_g54`: `DEFENSIVE_DEPLOYMENT_CAPACITY` may allow reduced-risk participation, and `BOOTSTRAP_CAN_DEPLOY_WITHOUT_FORCED_BUY = YES`.
- `phase31_g58`: `2022-10-03` was the bootstrap participation witness with `CAUTIOUS_DEPLOYMENT`, `SELECTIVE_DEPLOYMENT_CAPACITY`, `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP`, valid opportunities, non-zero security allocation, and Cash coexistence.

Thus, for this date, `CASH_PREFERRED` cannot be interpreted as simply:

```text
security participation must be exactly zero
```

without violating bootstrap participation semantics. The better interpretation is:

```text
Cash is preferred over full deployment,
but bootstrap may still require explicit reduced-risk exploratory participation
when PIT-valid opportunities exist and evidence is complete.
```

The current producer does not expose a separate final interaction state for that distinction.

## G81 Acceptance Gap

G81 focused regressions did not catch this because:

1. The all-CASH_PREFERRED regression represented 2023-07 weak-tail / plateau behavior, not `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP`.
2. The Profit Burst-style preservation fixture used NORMAL or STRONG/SELECTIVE paths, not actual 2022-10-03 bootstrap `CAUTIOUS_DEPLOYMENT + COMPARABLE_MARGINAL + CASH_PREFERRED` evidence.
3. No actual 2022-10-03 production artifact fixture asserted non-zero bootstrap participation after G81.
4. The regression accepted `CASH_PREFERRED -> zero security` as universally binding, while SoT requires differentiating weak-tail optionality from bootstrap participation.

Therefore:

```text
G81_ACCEPTANCE_GAP = YES
```

## Required Judgment

FIRST_DAY_ZERO_BUY_ROOT_CAUSE =
G81_BOUND_CASH_PREFERRED_TO_ZERO_SECURITY_IN_FINAL_PC_ALLOCATION_WITHOUT_BOOTSTRAP_PARTICIPATION_SEMANTIC_DISTINCTION

PRE_G81_POSITIVE_SECURITY_COUNT = 9

POST_G81_POSITIVE_SECURITY_COUNT = 0

POST_G81_CASH_PREFERRED_DEFERRAL_COUNT = 9

MARKET_QUALITY_DIRECT_SUPPRESSION = NO

CAPITAL_BUDGET_ZERO = NO

G81_DIRECT_CAUSAL = YES

BOOTSTRAP_PARTICIPATION_SEMANTIC_GAP = YES

MARKET_CANDIDATE_CASH_INTERACTION_SEMANTIC_GAP = YES

PS_RUNTIME_CONNECTIVITY = PASS

G81_ACCEPTANCE_GAP = YES

REPAIR_REQUIRED = YES

## Non-Causes

Candidate set changed = NO

BUY eligibility / rank / confidence changed = NO

Market Quality changed = NO

Risk Pacing changed = NO

Capital budget zero = NO

PS quantity authority defect = NO

Runtime priority redecision = NO

Submit / Execution defect = NO

## Repair Boundary Recommendation

Do not revert G81.

Next repair should be limited to the PC / market-candidate-Cash interaction boundary:

```text
market_candidate_cash_interaction
-> final PC security/Cash partition
-> bootstrap participation semantics
```

Required semantic separation:

1. Weak-tail optional Cash preference in already-deployed / plateau contexts must remain binding to zero security, preserving G80/G81.
2. Empty / near-empty bootstrap with PIT-valid opportunities and `EXPLORATION_PARTICIPATION_RISK_PRESERVED` must be able to materialize reduced-risk exploratory security allocation without creating fixed BUY counts, fixed exposure targets, thresholds, or Historical-return-tuned parameters.

Potential next task:

```text
Phase31-G83 — Bootstrap-Aware Cash Preference / Initial Participation Partition Repair
```

## Preservation Flags

CODE_CHANGED = NO

CONFIG_CHANGED = NO

THRESHOLD_WEIGHT_TUNING = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

CURRENT_RUN_MODIFIED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
