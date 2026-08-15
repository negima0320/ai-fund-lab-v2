# Phase30-A Phase29 Final State / Clean Baseline Reset / Research Roadmap

## Task

Task ID: `Phase29-L21T-BM`

Mode: READ-ONLY consolidation / documentation update.

The deliverable is Phase30-facing, but the task ID remains
`Phase29-L21T-BM`. Strategy, Runtime, Config, Model, and Thresholds were not
changed. Codex did not run fresh-run, resume, replay, recovery, or long
Historical validation.

## Primary Judgment

`PHASE29_L21T_BM_PHASE30_ENTRY_MATERIAL_REFRESHED_CLEAN_BASELINE_RESET_REQUIRED_RESEARCH_ROADMAP_UPDATED`

## Phase30 Migration Status

Phase30 migration is user-approved, but Phase30 performance tuning is not
authorized until a clean baseline is established.

| Field | Status |
| --- | --- |
| Phase30 migration | `USER_APPROVED` |
| Clean baseline | `VALIDATION_IN_PROGRESS` |
| Formal 4-year baseline | `NOT_ESTABLISHED` |
| Performance tuning | `WAIT_FOR_CLEAN_BASELINE` |
| Immediate Strategy change | `NO` |
| Immediate threshold change | `NO` |

## Current Clean Validation Candidate

Run:

```text
runtime-test-historical-extended-smoke-20260815T030154161245Z
```

Read-only status:

- `run_state.status = RUNNING`
- `next_job = 2022-08-24:market_refresh`
- 20BD completion is not assumed.

Observed clean early evidence:

| Date | Equity | Return | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| `2022-08-10` | `995,860` | `-0.41%` | `745,820` | `25.11%` | `9` |
| `2022-08-12` | `1,000,700` | `+0.07%` | `696,190` | `30.43%` | `8` |
| `2022-08-15` | `998,660` | `-0.13%` | `678,790` | `32.03%` | `9` |
| `2022-08-16` | `986,500` | `-1.35%` | `819,050` | `16.97%` | `7` |

This evidence confirms post-BL valuation plausibility on early days. It is not
yet sufficient for performance acceptance.

## Old Baseline Invalidated

The prior long Historical run:

```text
runtime-test-historical-extended-smoke-20260814T131647480030Z
```

is not valid formal performance evidence.

Phase29-L21T-BF confirmed:

- Primary classification: `CAPITAL_AUTHORITY_CONTAMINATED`
- earliest contamination: `2022-08-10`
- contaminated symbols: `104`
- contaminated days: `299 / 300`
- adjusted price consumption without proper economic/basis reconciliation
- false Equity reached capital authority
- sizing equity contaminated
- position weights contaminated

Invalidated as formal baseline:

- Equity curve
- Final Return
- MDD
- Cash / exposure attribution
- BUY_NEW / ADD / SELL performance
- Regime attribution
- Winner giveback
- Campaign performance
- Deployed-capital quality

Retained use:

```text
RUNTIME_FORENSIC / DEFECT_DISCOVERY_EVIDENCE
```

## Late Phase29 Final State

### Multi-Horizon Momentum / BUY_WAIT

Phase29 implemented multi-horizon trajectory semantics:

- `HEALTHY_CONTINUATION`
- `FADING_PRIOR_WINNER`
- `RECENT_ACCELERATION_OVERHEAT`
- `MIXED_OR_UNRESOLVED`

`BUY_WAIT` means:

- no BUY_NEW order
- no BUY Pending
- no Human Review Pending
- next business day reevaluation
- SELL independence preserved
- BUY_ADD / REENTRY / existing holdings unaffected

Phase30 should measure clean outcomes by class. It should not redesign this
contract before clean validation.

### Feature / BUY Quality Integration

AX found market_refresh did not materialize AV feature columns. AY repaired the
producer integration. BB then found BUY Quality did not receive the generated
multi-horizon features. BC repaired propagation so actual values can classify
HEALTHY / FADING / OVERHEAT / MIXED rather than falling into missing-feature
BUY_WAIT.

### Execution NO_ACTION

AZ found a valid no-order day halted in execution because submit's
`NO_SUBMISSION_REQUIRED` / `AUTHORIZED_NO_ORDER` authority was not accepted by
execution. BA repaired the continuity. Valid authorized no-order days can now
complete without ledger/current/pending mutation; malformed no-order states
remain fail-closed.

### Valuation / Price-Quantity Basis

BE through BL repaired the performance-measurement foundation:

- blind adjusted analytical valuation consumption blocked
- raw/economic source materialized
- raw price unconditional selection removed
- price/quantity adjustment-basis contract implemented
- basis mismatch fails closed
- runtime-owned quantity basis persisted
- new positions materialize basis metadata
- ADD / REDUCE / partial SELL preserve basis

This contract should not be reopened in Phase30 without new evidence.

## Updated Research Roadmap

### Priority 0: Clean Performance Measurement Foundation

Before Strategy improvement, confirm:

- Current valuation integrity
- price/quantity basis
- basis persistence
- Corporate Action consistency
- Equity reconciliation
- Daily PnL reconciliation
- cash / exposure / portfolio value
- sizing equity
- position weights

### Priority 1: Clean Long-Horizon Baseline

Order:

1. post-BL 20BD fresh validation
2. valuation integrity audit
3. Runtime stability audit
4. user-operated 4-year fresh Historical
5. clean long-horizon performance attribution

Codex must not run long Historical.

### Priority 2: Deployed-Capital Quality

The question is not whether cash is high. The question is whether deployed
capital produces edge:

- deployed capital return
- marginal capital return
- BUY_NEW quality
- ADD quality
- unused capital reason
- lot/cap/cash/exposure constraints

### Priority 3: Entry Quality / Momentum Trajectory

Clean attribution should measure:

- HEALTHY continuation return and win rate
- FADING avoided outcomes
- OVERHEAT avoided outcomes
- MIXED population quality

Future returns remain read-only attribution evidence only.

### Priority 4: Winner Continuation / Profit Retention

Research candidate:

`STRONG_WINNER_PROFIT_TAKE_REDUCE`

Measure:

- maximum favorable excursion
- peak unrealized profit
- realized profit
- peak-to-exit giveback
- campaign length
- momentum at peak / REDUCE / EXIT

No fixed profit-take percentage is approved.

### Priority 5: Market Regime / Transition

Old contaminated regime numbers are hypothesis-only. Recompute from clean
evidence for:

- BULL
- RANGE
- BEAR
- RECOVERY
- CORRECTION

and transitions such as BULL -> RANGE / CORRECTION / BEAR and RANGE -> BEAR.

### Priority 6: SELL / PM Market Context Authority

New research candidate:

Audit whether Market Context / Regime influences HOLD / REDUCE / EXIT / profit
protection, or whether SELL effectively waits for individual momentum weakness.

BUY / SELL independence must remain intact.

### Remaining Priorities

7. Exit Outcome Separability.
8. ADD Quality.
9. Recovery Re-entry Quality.
10. Formal Expected Edge Calibration.

## Research Candidate Reclassification

| Candidate | Status |
| --- | --- |
| Deployed-Capital Quality | `ACTIVE_AFTER_CLEAN_BASELINE` |
| Winner continuation / premature exit | `ACTIVE_AFTER_CLEAN_BASELINE` |
| Exit Outcome Separability | `REVALIDATION_REQUIRED` |
| Recovery Re-entry Quality | `REVALIDATION_REQUIRED` |
| Profit Retention / Peak Giveback | `ACTIVE_AFTER_CLEAN_BASELINE` |
| Campaign Capital Efficiency | `REVALIDATION_REQUIRED` |
| Formal Expected Edge calibration | `ACTIVE_RESEARCH` |
| REDUCE Pullback vs Breakdown separability | `ACTIVE_RESEARCH` |
| Multi-Horizon Momentum Trajectory outcome | `NEW_ACTIVE_RESEARCH_AFTER_CLEAN_BASELINE` |
| SELL / PM Market Context Authority | `NEW_ACTIVE_RESEARCH_AFTER_CLEAN_BASELINE` |

## Do Not Use For Tuning

- contaminated old baseline
- contaminated regime attribution
- contaminated winner giveback
- forced exposure targets
- fixed BUY count
- Rank1 / Top-N auto-BUY
- negative score absolute reject revival
- blanket Re-entry ban
- REDUCE ceil-to-one-lot
- automatic REDUCE -> EXIT
- fixed profit-take percentage without clean evidence
- Historical-only Strategy
- Production fail-closed weakening
- BUY / SELL coupling
- future returns as Runtime / Ledger / learning input

## Recommended Next Task

Phase30-A clean baseline readiness / post-BL validation audit after the
user-operated short validation has enough completed evidence.
