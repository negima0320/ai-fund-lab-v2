# Phase32-ET — Cross-Cutting Long-Lived History Decision Bias Exhaustive Read-Only Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Evidence inspected: available target-run artifacts through late December 2024, plus current Production source and Architecture/SoT.
- Purpose: find security-level, campaign-level, and portfolio-level history dependencies that may behave like the REENTRY long-lived prior-history penalty.

No Production source/config/schema, SHADOW source/config/schema, runtime state, Pending, Ledger, fresh-run, resume, replay, recover, or long Historical was changed or executed.

No future price, future return, MFE/MAE, final campaign outcome, later SELL result, or Historical PnL was used for Production judgment.

## Executive Judgment

REENTRY remains the only proven cross-run-age, security-level, effectively long-lived current-decision bias.

Other history consumers exist, but the inspected non-REENTRY Production consumers fall into one of these safer categories:

- audit lineage only;
- short/recent execution consistency or cooldown;
- current open-campaign lifecycle;
- current PIT market/price feature history;
- runtime idempotency / recovery / evidence authority.

The closest non-REENTRY candidate is the lot-blocked REDUCE / soft-deterioration persistence machinery, but it is campaign-local, carries recovery/reset evidence, and operates on current open holdings. It is not a never-held-vs-old-held security-level BUY penalty.

Therefore, this is not a general system-wide pattern where all old history contaminates current decisions. It is a narrower pattern: Production still has unbounded prior-exit / same-symbol REENTRY history embedded in the current BUY capitalization path, while several other history surfaces have already been scoped correctly.

## Production History Consumer Reference Graph

| Producer | Consumer | field / state | persistence scope | decision effect | expiry / TTL | campaign reset | security reset | affects current Production decision? | classification |
|---|---|---|---|---|---|---|---|---|---|
| `shadow_runtime._supply_prior_exit_state` | PC REENTRY semantic gate | `prior_exit_context`, `prior_exit_business_date`, `business_days_since_exit`, prior EXIT reason/provenance | strict-prior ledger/PM history by symbol | classifies flat symbol as REENTRY; can force target zero/review | cooldown only; no max relevance boundary found | new accepted campaign starts, but prior symbol lineage remains | no security-level expiry found | YES | `D. CURRENT_DECISION_LONG_LIVED_BIAS` |
| `shadow_runtime._strict_prior_pm_exit_decision_evidence_by_campaign` | PC REENTRY recovery | prior EXIT reason/reason_codes/source PM decision | all prior PM artifacts before decision date | reason-specific recovery / unknown-context gates | none found | prior campaign lineage persists as context | no | YES | `D` for long-lived prior EXIT context |
| `portfolio_construction._semantic_reentry_evidence` | PC member materialization | `semantic_buy_type=REENTRY`, `reentry_cooldown_status` | symbol has strict-prior closed campaign | REENTRY branch instead of ordinary BUY_NEW | 3BD cooldown for immediate churn only | accepted fill creates new campaign, but future prior-exit branch remains possible | no | YES | `B` for cooldown, `D` for permanent branch |
| `portfolio_construction._reentry_recovery_evidence` | `_canonical_reentry_semantic_eligibility` | unknown context, repeated churn, trend/momentum recovery, hard-stop new thesis | same-symbol prior EXIT and current PIT fields | PASS / REVIEW_REQUIRED / FAIL_CLOSED | no age-only expiry | not enough for old symbol penalty | no | YES | `D` / `E` depending reason |
| `marginal_capital_value._evidence_completeness_state` | unified marginal capital evidence | `reentry_not_currently_eligible` | PC member REENTRY state | REENTRY_NEXT_LOT incomplete unless `REENTRY_ELIGIBLE` | inherits PC REENTRY lifecycle | n/a | inherits PC | YES for shadow/PC-adjacent evidence; no independent penalty | `D` via REENTRY dependency |
| `position_management._cooldown_state` | PM ADD/reentry style policy | `days_since_exit`, `days_since_reduce`, `days_since_add` | current PM row fields | blocks ADD/reentry-like PM action while cooldown active | configured finite defaults: post-exit 10BD, post-reduce 5BD, add 3BD | yes for current campaign context | yes after fields age out | YES | `B. RECENT_CONTEXT_JUSTIFIED` |
| `position_management._structured_add_worthiness_evidence` | PM ADD worthiness | `add_history_summary`, `reduce_history_summary` | current open campaign lifecycle | `NO_ADD` if add count >=5 or reduce count >0 | no time TTL, but campaign-local | YES | YES, new campaign resets | YES | `C. CAMPAIGN_LOCAL_JUSTIFIED` |
| `portfolio_construction._campaign_aware_add_worthiness_state` | PC member SI fields | SI lifecycle add/reduce history | current held campaign | `NO_ADD` / `ADD_ALLOWED` | no time TTL, but open-campaign bounded | YES | YES | YES | `C` |
| `sell_semantic_state.evaluate_position_sell_semantic` | PM/SELL semantic severity | `prior_unrepresentable_reduce_summary`, active prior reduce count, soft-deterioration episode | current open campaign | can escalate persistent unrecovered soft deterioration | recovery/reset evidence exists; active episode scope | YES | YES | YES | `C`, with design-review note |
| `unrepresentable_reduce_exit_shadow` / BQ production promotion path | PM/SELL materialization | prior unrepresentable reduce events by campaign | current campaign | FULL EXIT reconsideration after repeated unresolved deterioration | recovery state can preserve/reset; shadow file itself is not direct Production | YES | YES | YES where promoted through PM/SELL | `C` |
| `strategy_intelligence` lifecycle context | PM / PC / MCV | campaign age, current campaign return, observed MFE/giveback, buy/add/reduce/sell summaries | current open campaign | HOLD/ADD/REDUCE/EXIT evidence; not prior closed-campaign BUY penalty | campaign ends at EXIT | YES | YES | YES | `C` |
| `buy_quality._momentum_trajectory_quality` | BQ | `prior_winner_short_horizon_deterioration` reason code | current price-feature window, not ownership history | BUY_WAIT for long-positive but short-negative momentum | rolling PIT feature window | n/a | n/a | YES | `B` / current PIT, name misleading |
| `tick_quantization` / BQ | BQ / trend confidence | `low_price_blacklist_used=false` | none observed | no blacklist active | n/a | n/a | n/a | NO blacklist effect found | `A. AUDIT_ONLY_HISTORY` |
| `dynamic_cash_exposure`, `portfolio_policy`, `dynamic_position_count`, `runtime_planning`, `position_sizing`, `capital_deployment` | validation consumers | `previous_day_*_copied=false` guards | artifact temporal validation | forbids stale previous-day copying | per artifact date | n/a | n/a | YES as fail-closed freshness, not security bias | `B` |
| Runtime Pending / Submit / Ledger | Runtime orchestration | submitted orders, pending states, idempotency keys, retry parent | order lifecycle / run state | avoids duplicate submit/execution and stale pending | bounded by order/recovery lifecycle | n/a | n/a | YES | `B` / audit-control |
| Accepted artifact registry / hashes | Runtime authority resolver | accepted generation/hash/checkpoint | artifact generation | fail-closed on mismatched authority | registry transition contract | n/a | n/a | YES | `A/B`, not security bias |
| Market / technical features | Candidate/BQ/Regime/PC | rolling price/volume/feature histories | PIT market history windows | current evidence construction | rolling feature windows | n/a | n/a | YES | `B`, not ownership penalty |

## Security-Level History Findings

### REENTRY / prior EXIT

Finding:

- Proven `D. CURRENT_DECISION_LONG_LIVED_BIAS`.
- Same-symbol prior EXIT history is retained without a semantic max relevance boundary.
- Unknown/generic prior context can remain REVIEW_REQUIRED hundreds of business days later.
- Old EXIT reasons can still alter current Entry/PC/REENTRY treatment.
- This creates the never-held vs old-history asymmetry already identified by ER/ES.

Required candidate classification:

- `AUDIT_LINEAGE_KEEP`: prior campaign id, prior EXIT date, prior EXIT reason/provenance, old fills/ledger.
- `CHURN_GUARD_REPLACE`: immediate/recent EXIT churn protection and unresolved same-thesis risk.
- `CURRENT_DECISION_REMOVE`: permanent REENTRY-only capital/rank/target-zero penalty after the recent-exit guard/requalification lifecycle is no longer current.
- `LEGACY_REMOVE`: generic/unknown old context as indefinite capital block; stale same-symbol prior ownership as ordinary current BUY handicap.

### Buy Quality `prior_winner_short_horizon_deterioration`

Finding:

- Name contains `prior_winner`, but implementation is current PIT feature based: long horizon positive momentum with 1D/3D/5D negative deterioration.
- It does not inspect ownership, prior campaign, or ever-held state.
- Artifact scan found this reason code frequently in late-run BQ files, but it is not a security-level historical ownership penalty.

Classification: `B. RECENT_CONTEXT_JUSTIFIED`.

### Blacklist / exclusion / rejected-candidate history

Finding:

- `low_price_blacklist_used` is explicitly materialized as `false` in the inspected BQ/tick-quantization paths.
- No active Production symbol blacklist, historical rejected-candidate list, or failed-entry history consumer was found that changes current decisions indefinitely.
- Exclusions found in calibration/hash inventory are metadata exclusions, not security selection blacklist authority.

Classification: `A. AUDIT_ONLY_HISTORY`.

## Campaign-Level History Findings

### ADD / REDUCE history

Finding:

- `add_history_summary` and `reduce_history_summary` are consumed by Strategy Intelligence, PM, and PC ADD-worthiness logic.
- They can change current ADD decisions:
  - add count >=5 can limit incremental ADD;
  - reduce count >0 can require ADD review/no-add.
- Source and Architecture tie these summaries to the current open campaign.
- Campaign materialization starts a new campaign on BUY after flat/closed state and does not merge new REENTRY/BUY_NEW into the prior closed campaign without explicit open-campaign identity proof.
- Phase ER artifact scan found `0` closed-campaign ADD/REDUCE leak candidates.

Classification: `C. CAMPAIGN_LOCAL_JUSTIFIED`.

### Soft deterioration / prior unrepresentable REDUCE

Finding:

- `sell_semantic_state` and related promoted logic use `prior_unrepresentable_reduce_summary` to identify persistent unrecovered soft deterioration after REDUCE could not be represented due to lot/min-notional constraints.
- Artifact scan observed positive prior-unrepresentable evidence in PM artifacts, but it is current-campaign state.
- It has explicit recovery/de-escalation fields:
  - `last_recovery_reset_date`
  - `prior_soft_deterioration_cleared`
  - `soft_deterioration_episode_state`
  - `zero_lot_reduce_persistence_scope=ACTIVE_SOFT_EPISODE_ONLY`
- It is not a flat-symbol BUY penalty and does not create never-held vs old-held asymmetry.

Classification: `C. CAMPAIGN_LOCAL_JUSTIFIED`, with `E. AMBIGUOUS / NEEDS_DESIGN_REVIEW` only if future evidence shows the active episode cannot close despite current recovery evidence.

### Campaign MFE/giveback/current return

Finding:

- Observed MFE/giveback/current campaign return affect PM/HOLD/REDUCE/EXIT, profit protection, and continuation assessment.
- Architecture states prior closed campaign MFE/giveback must not be inherited as current-campaign state.
- Current source refreshes/updates open campaign observations from decision-time current state.
- No cross-campaign inheritance defect was proven in ET.

Classification: `C. CAMPAIGN_LOCAL_JUSTIFIED`.

## Portfolio-Level / Runtime Accumulated History Findings

### Runtime ledger/order/Pending history

Finding:

- Orders, executions, Pending states, retry parent, and submitted/open/completed orders are consumed for idempotency, recovery, and duplicate prevention.
- These consumers change runtime permission to submit/execute, but not security investment preference.
- They are bounded by order/run lifecycle contracts.

Classification: `B. RECENT_CONTEXT_JUSTIFIED`.

### Previous-day artifact copy guards

Finding:

- Multiple Production artifacts explicitly materialize `previous_day_*_copied=false`.
- Validators reject previous-day-copy use.
- This is temporal freshness fail-closed behavior, not a historical decision bias.

Classification: `B. RECENT_CONTEXT_JUSTIFIED`.

### Market/feature historical windows

Finding:

- Candidate, BQ, market/regime, trend, momentum, volatility, and downside components use historical price/volume windows.
- These are J-Quants/PIT current feature inputs, not ownership/campaign history.
- No outcome, final campaign PnL, or future return input was found in the inspected Production consumers.

Classification: `B. RECENT_CONTEXT_JUSTIFIED`.

### Run-age scaling consumers

Finding:

- EQ already proved run-age performance scaling in market_refresh/morning/submit and strict-prior history scans.
- The source paths include full strict-prior execution/PM/campaign scans for REENTRY/campaign materialization and daily directory discovery.
- This is a real run-age scaling dependency.
- The current-decision capital bias portion is concentrated in REENTRY/prior-exit; other scaling is performance/authority reconstruction rather than direct preference bias.

Classification: `D` for REENTRY current-decision effect; `B/E` for runtime/history reconstruction performance.

## Never-Held vs Old-History Asymmetry

Beyond REENTRY, no independent never-held vs old-history asymmetry was proven.

- ADD/REDUCE applies only to currently held open campaigns.
- SELL semantic persistence applies only to current open holdings.
- BQ `prior_winner_short_horizon_deterioration` does not read prior ownership.
- Runtime idempotency does not change candidate attractiveness.

Therefore:

- `NEVER_HELD_VS_OLD_HISTORY_ASYMMETRY_BEYOND_REENTRY = NO`

## Unknown / Missing Historical Context

Beyond REENTRY, no Production path was found where missing old security/campaign history becomes an indefinite BUY capital block.

Unknown/missing authority exists in Runtime/PM/PC, but:

- missing current open campaign authority is fail-closed for held-position PM/ADD/SELL correctness;
- missing order/Pending/registry authority is fail-closed for runtime safety;
- these are not old flat-symbol investment penalties.

Therefore:

- `UNKNOWN_HISTORY_LONG_LIVED_BLOCK_BEYOND_REENTRY = NO`

## Duration / TTL / Window Audit

| Dependency | TTL/window present? | Judgment |
|---|---|---|
| REENTRY cooldown | YES, short finite cooldown | valid short churn guard |
| REENTRY prior-exit branch | NO semantic max relevance boundary found | defect/design target |
| PM post-exit/reduce/add cooldown | YES, finite configured defaults | valid |
| ADD/REDUCE current campaign history | no time TTL, but bounded by campaign lifecycle | valid campaign-local |
| soft deterioration episode | reset/recovery fields present; current open campaign | valid with review note |
| price/momentum/trend/volatility features | rolling market windows | valid PIT evidence |
| runtime orders/pending/idempotency | order/run lifecycle | valid |
| registry/hash authority | accepted generation lifecycle | valid |

## Production Classification Summary

| Finding | Classification |
|---|---|
| REENTRY long-lived prior-exit / unknown context | `D. CURRENT_DECISION_LONG_LIVED_BIAS` |
| REENTRY cooldown / immediate churn | `B. RECENT_CONTEXT_JUSTIFIED` |
| REENTRY lineage/provenance fields | `A. AUDIT_ONLY_HISTORY` if not used as current penalty |
| ADD/REDUCE history in open campaign | `C. CAMPAIGN_LOCAL_JUSTIFIED` |
| soft deterioration persistence in open campaign | `C. CAMPAIGN_LOCAL_JUSTIFIED` |
| BQ `prior_winner_short_horizon_deterioration` | `B. RECENT_CONTEXT_JUSTIFIED`; current PIT feature, name misleading |
| low-price blacklist flag | `A. AUDIT_ONLY_HISTORY`; inactive/false in inspected paths |
| prior rank/allocation in SHADOW comparison | `A. AUDIT_ONLY_HISTORY`; no Production consumer found |
| runtime retry/idempotency/order history | `B. RECENT_CONTEXT_JUSTIFIED` |
| accepted artifact registry/history | `A/B`; authority safety, not security bias |
| previous-day copy guards | `B`; stale-data prevention |
| whole-run strict-prior scans | `D` only where feeding REENTRY current decision; otherwise performance/reconstruction dependency |

## Is REENTRY Special?

Yes. REENTRY is special in the current evidence.

The broader codebase does contain many history fields, but most are correctly scoped. The unique REENTRY defect pattern is:

```text
flat same-symbol old ownership
-> strict-prior closed campaign
-> permanent REENTRY branch
-> old/missing prior EXIT context affects current BUY/PC
-> target zero / non-capitalization
```

No other inspected Production path reproduces this same shape as a security-level, old-history, current BUY capital penalty.

However, REENTRY is also a warning about a broader design discipline: every history consumer must state whether it is audit-only, recent-context, campaign-local, or current-decision authority. The codebase has several correctly scoped consumers, but REENTRY still mixes lineage with current decision authority.

## Required Answers

- `LONG_LIVED_HISTORY_BIAS_BEYOND_REENTRY_FOUND = NO`
- `OTHER_EFFECTIVE_PERMANENT_PENALTIES_FOUND = NO`
- `NEVER_HELD_VS_OLD_HISTORY_ASYMMETRY_BEYOND_REENTRY = NO`
- `UNKNOWN_HISTORY_LONG_LIVED_BLOCK_BEYOND_REENTRY = NO`
- `CROSS_CAMPAIGN_HISTORY_LEAK_FOUND = NO`
- `UNBOUNDED_HISTORY_DECISION_DEPENDENCIES_FOUND = YES`
- `RUN_AGE_SCALING_DECISION_DEPENDENCIES_FOUND = YES`
- `ALL_PRODUCTION_HISTORY_CONSUMERS_ENUMERATED = YES`
- `REENTRY_REMOVAL_REFERENCE_GRAPH_COMPLETE = YES`
- `DESIGN_PHASE_SAFE_TO_START = YES`
- `PRODUCTION_CHANGED = NO`
- `SHADOW_CHANGED = NO`
- `TARGET_RUN_MUTATED = NO`
- `RUNTIME_STATE_MUTATED = NO`
- `FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT = NO`

## Final Judgment

`PHASE32_ET_REENTRY_IS_THE_ONLY_PROVEN_LONG_LIVED_SECURITY_LEVEL_HISTORY_BIAS_BEYOND_REENTRY_NO_OTHER_EFFECTIVE_PERMANENT_PENALTY_FOUND_DESIGN_PHASE_SAFE_TO_START`
