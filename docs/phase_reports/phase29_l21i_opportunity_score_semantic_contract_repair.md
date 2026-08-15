# Phase29-L21I - Opportunity Score Semantic Contract Repair

## Primary Judgment

`PHASE29_L21I_OPPORTUNITY_SCORE_SEMANTIC_CONTRACT_REPAIRED_SHORT_VALIDATION_PASS`

The targeted semantic repair is implemented and short validation passed. Runtime Opportunity output is now explicitly materialized as uncalibrated `runtime_opportunity_score`, with legacy score aliases marked as deprecated non-economic aliases. Buy Quality now separates calibrated economic expected-return gating from uncalibrated relative/model-score quality evaluation.

## Root Cause Repaired

YES. The repaired root cause was:

```text
uncalibrated model score
-> expected_edge_score / expected_return aliases
-> Buy Quality score <= 0 economic hard gate
```

After the repair, uncalibrated negative score alone no longer produces `UNUSABLE` / `REJECT`. Calibrated economic scores still use the sign gate.

## Canonical Opportunity Semantics

Canonical runtime field:

```text
runtime_opportunity_score
```

Current Runtime v2 BUY AI producer semantics:

```text
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
prediction_semantics = runtime_opportunity_score
```

## Calibration Contract

Buy Quality now resolves an explicit score contract:

- `calibration_applied=true` plus economic semantics allows expected-return sign gating.
- `calibration_applied=false` treats the score as relative/model signal, not economic return.
- malformed calibrated metadata fails closed as `REVIEW_REQUIRED`.
- unknown uncalibrated semantics fails closed/review.

## Field Alias Changes

Changed `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`.

Rows now include:

```text
runtime_opportunity_score
score_semantic_role
economic_units_available
expected_edge_score_semantic_role
expected_return_semantic_role
opportunity_score_semantic_role
```

Artifact-level metadata now includes:

```text
canonical_score_field = runtime_opportunity_score
deprecated_score_aliases
economic_units_available = false
```

Legacy fields remain for compatibility, but are no longer semantically silent.

## Buy Quality Eligibility Changes

Changed `src/ai_fund_lab_v2/strategy/buy_quality.py`.

Buy Quality now:

- prefers `runtime_opportunity_score` over legacy `expected_edge_score`;
- records `runtime_opportunity_score_authority`;
- uses `calibrated_non_positive_expected_return` only when economic units are available;
- uses `uncalibrated_relative_score_non_positive_not_economic_gate` for negative uncalibrated relative scores;
- rejects weak uncalibrated rows through `uncalibrated_relative_score_weak`, based on relative quality, not raw sign.

## Uncalibrated Negative Score Behavior

Repaired. A high-rank, relatively strong, uncalibrated negative score is no longer automatically `UNUSABLE` solely because `score < 0`. It proceeds through relative quality, market, reliability, execution feasibility, and portfolio-fit evaluation.

## Calibrated Negative Expected Return Behavior

Preserved. With:

```text
calibration_applied = true
prediction_semantics = calibrated_expected_return
score <= 0
```

Buy Quality rejects with:

```text
calibrated_non_positive_expected_return
```

## Downside Risk Preservation

Preserved. `high_downside_risk_score` remains a critical no-buy reason. A positive score with high downside risk still rejects.

## BUY_NEW Behavior

No forced BUY_NEW expansion was added. The repair may allow more candidates to reach quality evaluation when their uncalibrated score is negative but relatively strong. It does not add fixed Top-N buying, minimum buys, cash-spend forcing, or negative-score auto-PASS.

## BUY_ADD Behavior

No BUY_ADD semantic change was added. Phase28/L21D/L21F ADD economics and lot-aware BUY_ADD behavior remain separate from this shared Opportunity / Buy Quality score contract repair.

## Safety Behavior

No Safety behavior was changed. Safety hard boundaries, corporate-event blocks, liquidity blocks, invalid score fail-closed behavior, and high-downside-risk rejection are preserved.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py`
- `src/ai_fund_lab_v2/strategy/buy_quality.py`
- `tests/strategy/test_phase26_h_adaptive_buy_quality.py`
- `docs/phase_reports/phase29_l21i_opportunity_score_semantic_contract_repair.md`

## Tests

PASS:

```text
python3 -m pytest tests/strategy/test_phase26_h_adaptive_buy_quality.py
```

Result:

```text
18 passed
```

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase22_g_runtime_planning.py
```

Result:

```text
199 passed
```

PASS:

```text
python3 -m pytest tests/runtime_v2/test_phase23_bi_buy_ai_import_boundary.py \
  tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py
```

Result:

```text
11 passed
```

PASS:

```text
python3 -m pytest tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py \
  tests/runtime_v2/test_phase17_bl_feature_date_authority_unification.py \
  tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py \
  tests/runtime_v2/test_phase19_bm_lifecycle_permission_separation.py
```

Result:

```text
24 passed
```

## py_compile

Initial direct `py_compile` failed because macOS Python attempted to write bytecode under `/Users/negishi/Library/Caches`, outside the allowed sandbox.

PASS after redirecting pycache to `/tmp`:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/buy_quality.py \
  src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

## git diff --check

PASS for changed implementation/test files before report creation, and final full diff check also passed after report creation.

```text
git diff --check -- src/ai_fund_lab_v2/strategy/buy_quality.py \
  src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py \
  tests/strategy/test_phase26_h_adaptive_buy_quality.py
```

Final full command:

```text
git diff --check
```

## Regression Judgment

| Item | Judgment |
|---|---|
| Opportunity Semantic Contract Repaired | YES |
| Uncalibrated Score Sign Economic Gate Removed | YES |
| Calibrated Expected Return Gate Preserved | YES |
| High Downside Risk Preserved | YES |
| BUY_NEW Forced Expansion Added | NO |
| BUY_ADD Semantics Regressed | NO |
| Safety Semantics Changed | NO |
| New Component Added | NO |
| Historical-only Logic Added | NO |

## Long Historical Executed NO

YES. No fresh run, resume, 100BD, 4-year Historical, long Historical, pending lifecycle, repair, or runtime mutation was executed.

## Current Run Mutated NO

YES. The halted target run was not mutated.

## Recommended Next Validation

User/operator-owned next validation should be a short historical/resume validation that inspects whether Buy Quality reason codes now distinguish uncalibrated relative-score evaluation from calibrated economic rejection. Success should be judged by semantic consistency and downstream safety preservation, not by forcing a specific BUY count.
