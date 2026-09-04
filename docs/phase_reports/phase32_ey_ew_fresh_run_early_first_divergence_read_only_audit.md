# Phase32-EY — EW Fresh-Run Early Portfolio First-Divergence READ-ONLY Audit

## Scope

- Current fresh run: `runtime-test-historical-extended-smoke-20260903T205257030508Z`
- Previous reference run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Reference evidence after EX cleanup:
  - `docs/phase_reports/phase32_ex_preserved_old_run_evidence/old_run_daily_metrics.csv`
  - `docs/phase_reports/phase32_ex_preserved_old_run_evidence/old_run_full_inventory_before_cleanup.csv`
  - retained old run `fresh_run_summary.json`, `run_state.json`, `strategy_shadow_summary.json`
- Current run actual evidence inspected through `2022-10-13`.
- READ-ONLY audit. No source/config/schema/accepted-generation/runtime-state/Pending/Ledger mutation was performed.
- No fresh-run, resume, replay, recover, or long Historical command was executed.
- No future price/return/PnL/later campaign outcome was used for Production judgment.

## Required Context

Phase32-EW intentionally changed the BUY path:

- old long-lived `REENTRY` current-decision semantic was removed;
- flat symbols should normally evaluate as `BUY_NEW`;
- old prior ownership should be audit lineage, not permanent current BUY authority;
- only a bounded `recent_exit_guard` may alter current BUY treatment;
- whole-run strict-prior REENTRY scans were removed from the current-decision hot path.

The relevant current implementation path is:

```text
shadow_runtime._supply_prior_exit_state
-> _bounded_recent_exit_guard_state_by_symbol
-> attach only explicit recent_exit_guard index rows
-> portfolio_construction._semantic_reentry_evidence
```

`_bounded_recent_exit_guard_state_by_symbol` only reads:

- `.runtime/runtime_state/recent_exit_guard/<business_date>.json`
- `.runtime/runtime_state/recent_exit_guard.json`
- `<run>/daily/<business_date>/strategy/recent_exit_guard.json`

No such `recent_exit_guard` artifact was present for the current fresh run or runtime state.

## First Portfolio Divergence

The earliest preserved old/new divergence is `2022-10-05`, the third business day.

Old preserved aggregate evidence:

| Date | Old PC members | Old REENTRY suppressed | Old prior-exit target-zero |
| --- | ---: | ---: | ---: |
| 2022-10-03 | 50 | 0 | 0 |
| 2022-10-04 | 50 | 0 | 0 |
| 2022-10-05 | 50 | 2 | 2 |
| 2022-10-06 | 50 | 4 | 4 |
| 2022-10-07 | 50 | 4 | 4 |

Current fresh-run actual evidence:

| Date | New PC members | New prior/recent-guard rows | New prior-exit target-zero |
| --- | ---: | ---: | ---: |
| 2022-10-03 | 50 | 0 | 0 |
| 2022-10-04 | 50 | 0 | 0 |
| 2022-10-05 | 50 | 0 | 0 |
| 2022-10-06 | 50 | 0 | 0 |
| 2022-10-07 | 50 | 0 | 0 |

The first concrete current-run portfolio event tied to the divergence is:

```text
2022-10-04: 83060 SELL_EXIT quantity 100
2022-10-05: 83060 BUY_NEW quantity 100
```

Current-run execution evidence:

- `2022-10-04` fill:
  - symbol: `83060`
  - side: `SELL`
  - quantity: `100`
  - source decision type: `SELL_EXIT`
  - source decision id: `rp-2022-10-04-83060-sell_exit-9a2c234d52b1449f`
  - campaign: `pc-6c27812c4ff1c33a-83060-0001`
- `2022-10-05` fill:
  - symbol: `83060`
  - side: `BUY`
  - quantity: `100`
  - source decision type: `BUY_NEW`
  - source decision id: `rp-2022-10-05-83060-buy_new-93e1a900372d78fb`
  - new campaign: `pc-ec0274eef528adf5-83060-0001`

The same prior-day EXIT / next-day BUY candidate shape also appears for `89180`, but `89180` was review/cash constrained in planning and did not produce the first observed fill:

- `2022-10-04`: `89180` SELL_EXIT, quantity `3700`, reason code `hard_stop_current_return`.
- `2022-10-05`: `89180` PC semantic `BUY_NEW`, target weight `0.034074`, priority index `5`, planning decision `INCLUDE_REVIEW_REQUIRED`.

## First Decision Divergence

For the first concrete filled divergence candidate, `83060`:

| Stage | Old vs New | Evidence |
| --- | --- | --- |
| Candidate generation | EVIDENCE_UNAVAILABLE at symbol-level old; current has candidate rank `14`, opportunity rank `10` | old daily raw artifact deleted by EX; new `strategy_decision_trace.json` |
| Candidate ranking | EVIDENCE_UNAVAILABLE at symbol-level old; current rank available | old raw deleted; new rank available |
| BQ / quality | EVIDENCE_UNAVAILABLE at symbol-level old; current `BUY_ELIGIBLE`, reduced allocation, tick-normalized trend acceptable | new `buy_quality_decisions.json` |
| Entry decision | EVIDENCE_UNAVAILABLE at symbol-level old; current `entry_mixed_continuation` / caution continuation | new PC/BQ artifacts |
| Position Management | SAME for preceding sell event is strongly supported by aggregate timeline but exact old symbol unavailable | current actual PM says `83060` EXIT on `2022-10-04`; old aggregate has no REENTRY rows before `2022-10-05` |
| Portfolio Construction | DIFFERENT | old aggregate has `reentry_suppressed_count=2` and `prior_exit_target_zero_count=2`; current `83060` has `semantic_buy_type=BUY_NEW`, `recent_exit_guard_state=NOT_APPLICABLE`, target weight `0.063427` |
| Marginal Capital Value | DIFFERENT | current `83060` has `canonical_marginal_capital_priority_index=4`, `marginal_capital_value_class=ELIGIBLE_COMPARABLE`; old REENTRY-suppressed rows were target-zero |
| Order planning | DIFFERENT | current planning includes `83060`, executable quantity `100`, pending item `strategy-16cc54fd108e63de92e0`; old exact item unavailable |
| Execution | DIFFERENT / old exact unavailable | current `83060` BUY fill occurred; old symbol-level fill unavailable after EX cleanup |

Therefore:

```text
FIRST_DIVERGENCE_STAGE = Portfolio Construction / MCV semantic materialization
```

The first bad boundary is not execution. Execution consumed the current `BUY_NEW` authority correctly. The upstream semantic difference was already present in PC/MCV.

## EW Direct Causality

EW direct causality is confirmed, but the causal mechanism is narrower than "old long-lived REENTRY removal works earlier than expected."

Actual causal path:

```text
2022-10-04 EXIT for 83060 / 89180
-> 2022-10-05 current BUY candidates
-> EW current path does not scan strict-prior ledger/PM history
-> no replacement recent_exit_guard index exists
-> prior EXIT is not supplied to candidate/opportunity rows
-> PC sees no prior_exit_business_date
-> _semantic_reentry_evidence returns BUY_NEW + recent_exit_guard_state=NOT_APPLICABLE
-> MCV ranks as ordinary BUY_NEW_NEXT_LOT / comparable marginal
-> runtime planning includes 83060
-> 83060 BUY_NEW fills
```

Current `83060` PC evidence on `2022-10-05`:

- `semantic_buy_type`: `BUY_NEW`
- `target_weight`: `0.063427`
- `recent_exit_guard_state`: `NOT_APPLICABLE`
- `recent_exit_guard_status`: `NOT_APPLICABLE`
- `prior_exit_business_date`: empty
- `business_days_since_exit`: null
- `reentry_semantic_state`: `REENTRY_NOT_APPLICABLE`
- `canonical_marginal_capital_priority_index`: `4`
- `marginal_capital_value_class`: `ELIGIBLE_COMPARABLE`

This conflicts with the EW/EU/EV design intent that short-term churn protection remains possible through a bounded recent-exit guard.

## Why Divergence Appeared On The Third Business Day

The early divergence is explained by immediate same-run history, not long run-age accumulation.

Hypothesis check:

| Hypothesis | Judgment | Evidence |
| --- | --- | --- |
| Run start already had canonical ledger/campaign history | NO for the first divergence | old/new both show no REENTRY/prior suppression on `2022-10-03` and `2022-10-04`; the relevant exits occur on `2022-10-04` inside the fresh run |
| Fresh-run historical context is not zero-start | PARTIAL / not needed | the first concrete issue is same-run prior-day EXIT, not pre-run old ownership |
| EW changed flat-symbol semantic classification itself | YES | flat post-EXIT symbol is now `BUY_NEW` if no bounded guard row is supplied |
| MCV / PC REENTRY treatment changed from the start | YES | current MCV ranks `83060` as ordinary `BUY_NEW` comparable marginal |
| recent_exit_guard boundary difference | YES | no guard index was materialized; state is `NOT_APPLICABLE` instead of active/requalified/blocked |
| accepted generation / source transition difference | EXPECTED SOURCE CHANGE, no mismatch evidence | old run first job source commit `a56f2bc...`; current run source commit `1f64f49...`; active runtime consumer eligibility remains `YES` |
| deterministic ordering difference | NO concrete evidence | divergence is explained by missing guard supply before ordering |
| unrelated state contamination | NO concrete evidence | source/run IDs and evidence roots are current-run scoped; no cross-run guard artifact was found |
| downstream path dependency after first divergence | YES | after `83060` fills, cash/headroom/campaign state can explain subsequent differences |

## Path Dependency

The primary divergence is:

```text
PRIMARY_DIVERGENCE:
2022-10-05 PC/MCV treats prior-day exited 83060 as ordinary BUY_NEW because recent_exit_guard authority is absent.
```

Downstream differences after that point should not be counted as independent EW semantic changes without their own first-boundary proof:

```text
83060 BUY_NEW fill
-> cash changes
-> position/campaign set changes
-> available headroom and capital competition change
-> later targets/orders/holdings diverge
```

The same applies to later apparent differences involving `45750`, `94340`, `76470`, or other holdings. They may be path-dependent unless independently traced back to a separate semantic boundary.

## Old-Run Evidence Sufficiency

OLD_RUN_EVIDENCE_SUFFICIENT: `PARTIAL`

Sufficient:

- first aggregate divergence date: `2022-10-05`;
- old aggregate REENTRY/prior-exit target-zero divergence;
- old source commit and run identity;
- evidence that old daily artifacts existed before EX cleanup;
- period/run-age context from EX/EQ/ER/ES/ET.

Insufficient:

- exact old symbol-level PC row for the two `2022-10-05` REENTRY-suppressed rows;
- exact old `83060` / `89180` old PC semantic payload;
- exact old order/fill comparison for `2022-10-05`.

Because old daily raw artifacts were intentionally deleted in Phase32-EX, the exact old symbol-level row cannot be recovered from preserved EX summaries alone. The best supported reconstruction is:

- old aggregate: two prior-exit rows were suppressed on `2022-10-05`;
- current actual: two symbols exited on `2022-10-04` and reappeared as BUY candidates on `2022-10-05` (`83060`, `89180`);
- current first fill: `83060 BUY_NEW 100`.

This is enough to identify the first semantic boundary, but not enough to claim a byte-for-byte old/new symbol-level diff.

## Correctness Judgment

Classification:

```text
C. EW_UNINTENDED_SEMANTIC_EXPANSION
```

Rationale:

- EW intentionally removed long-lived old REENTRY penalties.
- EW did not intend to remove bounded short-term churn protection.
- Actual fresh-run evidence shows no `recent_exit_guard` index/materialized authority for a prior-day EXIT.
- Because no guard authority is supplied, the current BUY path treats a one-business-day post-EXIT symbol as ordinary `BUY_NEW`.
- That behavior is broader than the EW Architecture/SoT boundary.

This is not a performance/PnL judgment. It is a PIT/Architecture contract issue: short-term recent EXIT context is supposed to be bounded current-decision authority, but the actual current-decision hot path has no materialized producer feeding it.

## Required Answers

- `FIRST_PORTFOLIO_DIVERGENCE_DATE = 2022-10-05`
- `FIRST_DIVERGENCE_SYMBOL = 83060` for the first concrete filled current-run event; `89180` is a companion same-boundary candidate but old symbol-level proof is unavailable.
- `FIRST_DIVERGENCE_STAGE = Portfolio Construction / Marginal Capital Value semantic materialization`
- `OLD_DECISION = aggregate old evidence shows REENTRY/prior-exit target-zero suppression count 2 on 2022-10-05; exact symbol-level old decision unavailable after EX cleanup`
- `NEW_DECISION = 83060 BUY_NEW, target_weight 0.063427, executable_quantity 100, filled BUY 100`
- `EW_DIRECT_CAUSALITY = YES`
- `PRIOR_EXIT_CONTEXT_INVOLVED = YES, same-run prior-day EXIT on 2022-10-04`
- `RECENT_EXIT_GUARD_INVOLVED = YES, by absence; expected bounded guard authority was not materialized`
- `MCV_PC_EFFECT_INVOLVED = YES`
- `EARLY_DIVERGENCE_EXPLAINED = YES, immediate same-run prior-day EXIT was not supplied to bounded guard path after EW removed whole-run REENTRY scan`
- `DOWNSTREAM_PATH_DEPENDENCY_CONFIRMED = YES`
- `STATE_OR_GENERATION_DEFECT_FOUND = NO concrete evidence; source commit changed as expected from EW-era source`
- `NONDETERMINISM_FOUND = NO`
- `OLD_RUN_EVIDENCE_SUFFICIENT = PARTIAL`
- `PRODUCTION_REPAIR_JUSTIFIED = YES, narrow repair should materialize/discover bounded recent-exit guard authority without restoring long-lived REENTRY history scan`

## No-Mutation Confirmation

- `PRODUCTION_CHANGED = NO`
- `SHADOW_CHANGED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `PENDING_MUTATED = NO`
- `LEDGER_MUTATED = NO`
- `FRESH_RUN_EXECUTED = NO`
- `RESUME_EXECUTED = NO`
- `REPLAY_EXECUTED = NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT = NO`

## Final Judgment

`PHASE32_EY_EW_EARLY_DIVERGENCE_ROOT_CAUSE_IDENTIFIED_AS_MISSING_BOUNDED_RECENT_EXIT_GUARD_MATERIALIZATION_NOT_LONG_RUN_AGE_EFFECT_PRODUCTION_REPAIR_JUSTIFIED`
