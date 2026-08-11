# Phase29-L4-A Bootstrap Post-Commit Evidence / Readiness Repair Implementation

Task ID: `Phase29-L4-A`

Status:

```text
COMPLETE
PRODUCTION-COMMON IMPLEMENTATION
SHORT REGRESSION PASS
NO CONFIG CHANGE
NO STRATEGY CHANGE
NO ACQUISITION
NO LONG BOOTSTRAP
NO HISTORICAL EXECUTION
```

Primary Judgment:

```text
PHASE29_L4_A_BOOTSTRAP_POST_COMMIT_READINESS_AUTHORITY_REPAIRED_SHORT_REGRESSION_PASS_PHASE29_L4_B_READY
```

## 1. Scope

Phase29-L4-A repaired only the Bootstrap post-commit evidence/readiness
authority defect identified in Phase29-L2/L3.

Out of scope and not implemented:

```text
Listed Issues staging -> canonical materialization
Listed PIT snapshots
Trading Calendar materialization / reconciliation
977BD / 979BD Historical execution
Strategy, ADD, BUY_NEW, SELL, EXIT, REDUCE, cash, concentration, Safety, model,
threshold, J1, J2, D61, D69 changes
```

## 2. Files Changed

Production:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py
```

Tests:

```text
tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py
```

Config changed:

```text
NO
```

Strategy changed:

```text
NO
```

## 3. Implementation

Before:

```text
build_market_data_bootstrap_plan
old canonical target warmup_sufficiency computed
_commit_bootstrap_merge replaces target
final evidence keeps old warmup_sufficiency
```

After:

```text
build_market_data_bootstrap_plan
pre_commit_warmup_sufficiency captured as DIAGNOSTIC_ONLY
_commit_bootstrap_merge writes and validates merged parquet
os.replace commits canonical target
committed canonical target is re-read
post_commit_verification validates committed target identity/content
post_commit_warmup_sufficiency is recomputed from committed target
bootstrap_readiness derives from commit_status + verification + post-commit warmup
final warmup_sufficiency compatibility field equals post_commit_warmup_sufficiency
```

New additive evidence fields:

```text
commit_status
pre_commit_warmup_sufficiency
pre_commit_warmup_authority
post_commit_warmup_sufficiency
post_commit_verification
bootstrap_readiness
commit_error
```

No schema version migration was required. The change is backward-compatible:
existing consumers can still read `warmup_sufficiency`, and final run evidence
now maps that field to post-commit authority.

## 4. Post-Commit Verification

Post-commit verification checks:

```text
target path equals expected canonical target
target exists
target readable
duplicate_key_count == 0
schema compatible with normalized OHLCV requirement
row_count matches expected merged inventory
earliest_date matches expected merged inventory
latest_date matches expected merged inventory
schema_hash matches expected merged inventory
content_hash matches expected merged inventory
```

Failure remains fail-closed. A physical commit can succeed while
`bootstrap_readiness` is `BLOCK`; this is now explicit through `commit_status`
versus `bootstrap_readiness`.

## 5. Regression Coverage

Focused bootstrap regression:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py
```

Result:

```text
12 passed in 12.96s
```

Covered:

```text
L4A-R1 old target incomplete + source complete -> post-commit warmup PASS
L4A-R2 committed target lacks required warmup -> bootstrap_readiness BLOCK
L4A-R3 commit failure -> fail-closed BLOCK
L4A-R4 target missing after commit -> BLOCK
L4A-R5 target content/hash mismatch -> BLOCK
L4A-R6 exactly 61BD warmup -> PASS
L4A-R7 only 60BD warmup -> BLOCK
```

Broader short regression:

```bash
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
```

Result:

```text
41 passed in 11.11s
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache \
PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py \
  scripts/runtime_test.py
```

Result:

```text
PASS
```

Note: the bare `pytest` command was unavailable in this shell, so
`python3 -m pytest` was used.

## 6. Gate Result

```text
Root cause confirmed:                 YES
Pre-commit warmup retained:           YES
Pre-commit warmup authority:          DIAGNOSTIC ONLY
Post-commit warmup implemented:       YES
Post-commit canonical target re-read: YES
Commit identity/content verification: YES
Final warmup authority:               POST_COMMIT
Bootstrap readiness post-commit:      YES
Production-common repair:             YES
Fresh long-horizon Ready:             NO
Phase29-L4-B Ready:                   YES
```

Fresh long-horizon remains not ready because L4-B still must repair:

```text
Listed Issues canonical materialization
Trading Calendar authority reconciliation
Read-only long-horizon gate recheck
```

## 7. Deliverables

```text
docs/phase_reports/phase29_l4_a_bootstrap_post_commit_evidence_readiness_repair_implementation.md
reports/phase29_l4_a_bootstrap_post_commit_evidence_readiness_repair_implementation/
```
