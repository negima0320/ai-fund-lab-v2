# Phase29-L21K - Prior EXIT State Materialization Design

## Primary Judgment

```text
PHASE29_L21K_PRIOR_EXIT_STATE_MATERIALIZATION_DESIGN_COMPLETE
```

Step 1 design confirmation found no blocking architecture gap. The L21J defect is not missing L16 re-entry evaluation logic; it is missing production-common materialization of prior same-symbol EXIT state into the BUY_NEW Strategy row.

## Canonical Prior EXIT Authority

Canonical authority:

```text
persistent runtime ledger execution history
```

Rationale:

- `daily/<D>/positions/position_campaigns.json` is observability evidence and may be produced after the daily job boundary; using it directly in Strategy would risk post-hoc historical replay leakage.
- `persistent_ledger/executions.jsonl` is the production/demo/historical common runtime execution history and is already used to derive run-scoped campaign observability.
- Portfolio Construction already consumes `prior_exit_business_date` / `last_exit_business_date` / `previous_exit_business_date` from Strategy input rows; no historical-only authority is required.

Implementation should derive a minimal PIT prior-EXIT context from ledger executions before decision date `D`, then attach `prior_exit_business_date` to non-current-position BUY_NEW candidate/opportunity rows.

## Temporal Safety

Allowed evidence for decision date `D`:

```text
execution.business_date < D
```

Forbidden evidence:

```text
execution.business_date >= D
daily position_campaigns generated after the decision
EOD valuation
future campaign state
realized PnL as a Strategy admission input
```

Same-day later execution must not be consumed by morning Strategy. Future EXIT rows must be ignored even if they exist in a fixture or replay ledger.

## Same-Symbol Closed Campaign Resolution

For a BUY_NEW candidate symbol `S`:

```text
current_quantity == 0
AND latest PIT-valid same-symbol campaign has closed before D
```

materialize:

```text
prior_exit_business_date
prior_exit_campaign_id
prior_exit_reason
prior_exit_state_status
```

The minimum field required by existing L16 is `prior_exit_business_date`. The extra fields are diagnostic context only; they must not introduce a PnL-based Strategy gate.

Latest PIT-valid prior EXIT means the latest same-symbol campaign whose execution sequence reaches zero quantity on a business date `< D`. Multiple old campaigns resolve to the latest such close. Same-day and future closes are ignored.

## Semantic Classification

The existing semantic split remains:

| State | Semantic type | Runtime Planning order intent |
|---|---|---|
| current position exists | `BUY_ADD` or existing-position path | existing ADD/HOLD/REDUCE/EXIT path |
| current position absent, no prior same-symbol EXIT | `BUY_NEW` | `BUY_NEW` |
| current position absent, prior same-symbol EXIT exists | `REENTRY` | `BUY_NEW` |

No new Runtime Planning intent is required. `REENTRY` is Strategy semantic evidence; executable order intent can remain `BUY_NEW`.

## Existing L16 Contract Reuse

Portfolio Construction already has the L16 contract:

- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1033) applies cooldown/recovery checks when a BUY_NEW row is classified as `REENTRY`.
- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1145) classifies semantic REENTRY from prior EXIT fields.
- [portfolio_construction.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/portfolio_construction.py:1289) reads `prior_exit_business_date`, `last_exit_business_date`, or `previous_exit_business_date`.

The predicate should remain unchanged. L21K should repair the missing input materialization before Portfolio Construction.

## 23880 Counterfactual

READ-ONLY reproduction using existing L16 functions and L21J evidence:

```text
business_date = 2022-09-01
prior_exit_business_date = 2022-08-30
rank = 5
runtime_opportunity_score = 0.00797852
quality_action = FULL_ALLOCATION_ELIGIBLE
trend_close_over_ma_20d = 0.9709452004
price_momentum_return_20d = 0.2222222222
corporate_action_status = UNKNOWN
```

Existing L16 output:

```text
semantic_buy_type = REENTRY
business_days_since_exit = 1
reentry_cooldown_threshold_bd = 3
reentry_cooldown_status = FAIL_CLOSED
reentry_recovery_status = FAIL_CLOSED
reentry_recovery_reason = reentry_expected_edge_below_threshold
```

This is not a post-hoc assertion that the trade was bad. It confirms that, once prior EXIT state is materialized, the existing contract evaluates the row as REENTRY instead of ordinary BUY_NEW.

## Implementation Design

Implement a production-common prior EXIT resolver in Strategy input construction:

1. Read the common runtime ledger executions from `persistent_ledger/executions.jsonl`.
2. Derive same-symbol campaign close state from BUY/SELL execution sequence using only rows with `business_date < D`.
3. Build a map by symbol to latest prior closed campaign.
4. Attach `prior_exit_business_date` and diagnostic prior-EXIT fields to candidate/opportunity rows before Buy Quality / Portfolio Construction summaries are built.
5. Let existing L16 Portfolio Construction logic consume the field.

Failure handling:

- If no prior same-symbol closed campaign is resolved, leave normal BUY_NEW unchanged.
- If malformed ledger rows are present but no valid prior EXIT can be established, do not block all BUY_NEW.
- If a row already has explicit prior EXIT fields, preserve explicit row authority and do not overwrite it with weaker derived state.

## Step 2 Authorization

Design is implementable without changing model, Accepted Generation, thresholds, Safety caps, Pending lifecycle, Submit, Execution, or the active historical run. Proceeding to Step 2 is appropriate.
