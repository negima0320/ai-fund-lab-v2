# Phase29-L21P - Post-L21K Re-entry Target Materialization Focused Validation

## Executive Summary

L21P focused validation result: `PASS_FOR_LOCAL_AUTHORITY_CHAIN`, with user fresh-run validation still required for portfolio-level metrics.

L21K prior EXIT materialization reaches Portfolio Construction (PC). The 23880 fixture now supplies `prior_exit_business_date=2022-08-30`, PC classifies the row as `REENTRY`, and the existing recovery hurdle is evaluated. The 23880 case remains blocked by existing REENTRY policy because the observed `runtime_opportunity_score=0.00797852` is below the existing `0.10` recovery threshold, not because prior EXIT state is still missing.

No production repair was made in L21P. Only focused regression tests were added.

## L21O Baseline

L21O baseline run: `runtime-test-historical-smoke-20260811T152905733571Z`.

Reproduced L21O PC candidate baseline:

| Metric | Count |
| --- | ---: |
| PC ADD candidates | 548 |
| Positive allocation | 72 |
| Zero allocation | 476 |
| REENTRY policy zeros | 309 |
| `reentry_corporate_action_status_missing` | 193 |
| `reentry_expected_edge_below_threshold` | 116 |
| Official minimum-policy-lot Safety hard-cap zeros | 153 |

This is old-run evidence. It must not be rewritten as post-L21K behavior.

## L21K Authority Chain

L21K materializes prior EXIT state from `persistent_ledger/executions.jsonl`, using only executions with `execution_business_date < decision_business_date`.

Observed authority chain in code:

1. `shadow_runtime._resolve_prior_closed_campaigns_from_executions` derives the latest closed same-symbol campaign before the decision date.
2. `shadow_runtime._attach_prior_exit_to_summary` attaches `prior_exit_business_date` to candidate and opportunity rows when the symbol is not currently held and no explicit prior EXIT field already exists.
3. `portfolio_construction._semantic_reentry_evidence` consumes `prior_exit_business_date` and classifies BUY_NEW rows as `REENTRY` when prior EXIT exists before the decision date.
4. `portfolio_construction._reentry_recovery_evidence` evaluates the existing recovery hurdle.
5. PC target adjustment zeroes final target when cooldown or recovery does not PASS, and leaves the normal target path available when both PASS.

Key code references:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1179`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py:1226`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1033`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1145`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1175`

## 23880 Focused Case

Focused fixture:

- 2022-08-23: 23880 BUY 1200
- 2022-08-29: 23880 SELL 300
- 2022-08-30: 23880 SELL 900
- 2022-09-01: 23880 candidate returns

Observed post-L21K behavior:

- `prior_exit_business_date=2022-08-30`
- `semantic_buy_type=REENTRY`
- `business_days_since_exit=1`
- `reentry_recovery_status=FAIL_CLOSED`
- `reentry_recovery_reason=reentry_expected_edge_below_threshold`

Judgment: 23880 now reaches the existing REENTRY authority chain. The remaining block is policy evaluation, not missing prior EXIT materialization.

## Corporate Action Recovery Audit

PC consumes corporate action evidence from these row fields:

- `corporate_action_status`
- `corporate_event_status`
- `corporate_action_blocking_status`
- `corporate_event_blocking_status`

Focused L21P regression results:

- When `corporate_action_status=NO_EVENT` is present and all other recovery inputs pass, REENTRY recovery returns `PASS`.
- When corporate action evidence is absent and all other recovery inputs pass, REENTRY recovery returns `REVIEW_REQUIRED` with `reentry_corporate_action_status_missing`.

Judgment:

- L21K did not cause the L21O 193 corporate-action-status missing cases.
- L21K also does not repair corporate action source materialization. It only supplies prior EXIT state.
- No PC consumer integration gap was found for corporate action fields when the field reaches the row.
- A remaining upstream/source coverage question remains for user fresh-run metrics: how many post-L21K REENTRY rows still lack row-level corporate action status.

## Expected Edge Recovery Audit

Focused L21P regression confirms `runtime_opportunity_score` is the canonical score consumed by REENTRY recovery. If both `runtime_opportunity_score` and legacy `expected_edge_score` are present, `runtime_opportunity_score` wins.

Observed:

- `runtime_opportunity_score=0.20`, `expected_edge_score=-0.50` => recovery can PASS.
- `runtime_opportunity_score=0.01`, `expected_edge_score=0.50` => recovery fails with `reentry_expected_edge_below_threshold`.

Judgment: the 116 L21O `reentry_expected_edge_below_threshold` cases align with the current L21I canonical field direction in the local authority chain. L21P did not change the existing threshold or reinterpret the score.

## Focused Regression Results

Command executed:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase29_l21k_prior_exit_materialization.py -q
```

Result:

```text
9 passed in 1.84s
```

New L21P coverage:

- REENTRY recovery PASS when prior EXIT, cooldown, score, rank, quality, trend/momentum, liquidity, and corporate action evidence all pass.
- REENTRY recovery REVIEW_REQUIRED when only corporate action evidence is missing.
- Canonical `runtime_opportunity_score` precedence over legacy `expected_edge_score`.

## BUY_NEW Regression Assessment

Existing L21K regression still passes: a normal BUY_NEW without prior EXIT remains `BUY_NEW` and `reentry_cooldown_status=NOT_APPLICABLE`.

Assessment: no normal BUY_NEW regression was found in the focused local tests.

## BUY_ADD Regression Assessment

Existing L21K regression still passes: a current position with ADD intent remains `BUY_ADD`, and prior EXIT materialization is skipped for currently held symbols.

Assessment: no BUY_ADD regression was found in the focused local tests.

## Remaining Gaps

No additional production repair is recommended from L21P local validation.

Remaining gaps are validation gaps, not identified implementation defects:

- A user-operated fresh-run is needed to measure post-L21K aggregate PC counts.
- The L21O 193 corporate action missing cases cannot be declared resolved by L21K, because L21K does not materialize corporate action status.
- Post-run metrics must classify whether any remaining corporate action missing rows are source-missing, upstream row-materialization-missing, or legitimate REVIEW_REQUIRED cases.

## User Validation Command

Codex did not run fresh-run, resume, long historical validation, or any Runtime mutation.

User-operated validation should use the canonical Runtime Test command guide. For a short operator validation:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --start-date 2026-07-06 \
  --business-days 5 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

After the run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py summarize --profile historical-smoke --scope strategy --json
PYTHONPATH=src python3 scripts/runtime_test.py validate --profile historical-smoke --json
```

If the operator intends to validate the historical window comparable to the L21O baseline, use the same profile/window policy that produced the new run and keep the run ID separate from L21O.

## Required Post-Run Metrics

Collect these metrics from the post-L21K user run:

1. PC ADD candidates.
2. Positive allocation count.
3. Zero allocation count.
4. REENTRY candidate count.
5. REENTRY cooldown PASS / FAIL counts.
6. REENTRY recovery PASS / FAIL_CLOSED / REVIEW_REQUIRED counts.
7. `reentry_corporate_action_status_missing` count.
8. `reentry_expected_edge_below_threshold` count.
9. Valid REENTRY PASS rows with `final_risk_adjusted_target_weight > 0`.
10. Valid REENTRY FAIL rows with `final_risk_adjusted_target_weight = 0`.
11. Normal BUY_NEW count and positive/zero allocation split.
12. BUY_ADD count and positive/zero allocation split.

## Recommended Next Task

Proceed to post-L21K user-run validation and aggregate metric reconciliation.

Recommended task ID:

`Phase29-L21Q - Post-L21K Historical Fresh-Run Re-entry Aggregate Validation`

## Primary Judgment

`PHASE29_L21P_POST_L21K_REENTRY_AUTHORITY_CHAIN_VALIDATED_USER_RUN_REQUIRED`

Answers required by L21P:

1. L21K prior EXIT materialization reaches PC: YES.
2. 23880 2022-09-01 gets `prior_exit_business_date=2022-08-30`: YES.
3. REENTRY classification is correct: YES.
4. Recovery hurdle is evaluated: YES.
5. L21O 193 corporate-action-status missing cases were caused by L21K: NO.
6. Corporate action integration gap remains after L21K: no PC consumer gap found when row evidence exists; upstream/source coverage still needs post-run measurement.
7. Expected-edge-below-threshold 116 semantics align with L21I: YES for canonical `runtime_opportunity_score` consumption; threshold policy unchanged.
8. Valid REENTRY PASS can produce final target >0: YES, PC only zeroes REENTRY on cooldown/recovery non-PASS before later low-price/liquidity caps.
9. Valid REENTRY FAIL target is 0: YES.
10. Normal BUY_NEW regression: NO.
11. BUY_ADD regression: NO.
12. Additional production repair needed: NO.
13. User fresh-run validation needed: YES.
14. Next task can proceed: YES.
