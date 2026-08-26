# Phase31-G74 — PC ADD Target-Weight Authority Repair

## PRIMARY_JUDGMENT

PHASE31_G74_PC_ADD_TARGET_WEIGHT_AUTHORITY_REPAIRED_ACCEPTED

G73で確定した `CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY` のauthority defectを修理した。
PM explicit ADD と canonical `add_investment_evidence.v1` がADD action requirementsを満たす場合、
Strategy Intelligence由来の interpretation-only `NO_ADD` fields はADD target incrementを0化する
独立hard gateとして使用しない。

実行中long Historical runは停止・変更していない。fresh-run / resume / replay / Historical追加実行は
行っていない。

## Repair Boundary

修理対象:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `_resolve_canonical_add_allocation_bridge()`
- authority = `CANONICAL_ADD_ALLOCATION_BRIDGE_AUTHORITY`

修理内容:

- `strategy_intelligence_add_worthiness_state`
- `entry_admission_action`
- `entry_admission_state`

をADD increment eligibilityの独立hard gateから除外した。

これらのSI fieldsは以下として保持する:

- context / diagnostic evidence
- `si_interpretation_context.interpretation_only = true`
- `si_interpretation_context.hard_add_increment_gate = false`
- reason code = `SI_INTERPRETATION_ONLY_NOT_ADD_INCREMENT_AUTHORITY`

Canonical ADD increment authorityは以下に限定した:

- PM explicit ADD
- current weight observed
- campaign continuation PASS
- expected edge PASS
- incremental investment value PASS
- opportunity cost PASS
- no-loss averaging PASS
- concentration PASS
- capital availability PASS
- execution feasibility not BLOCK
- positive ADD increment request

Broker fail-closed, expected-edge weakening fail-closed, missing evidence fail-closed,
concentration/capital/execution constraintsは維持した。

## Mandatory Case Acceptance

| Case | PM ADD | Incremental Value | Opportunity Cost | SI NO_ADD Visibility | Requested Increment | Proposed Increment | Result |
|---|---|---|---|---|---:|---:|---|
| 2022-10-21 / 94320 equivalent | YES | POSITIVE / PASS | PASS | preserved as diagnostic | > 0 | > 0 | PASS |
| 2022-11-10 / 99840 equivalent | YES | POSITIVE / PASS | PASS | preserved as diagnostic | > 0 | > 0 | PASS |
| 2023-06-20 / 40520 equivalent | YES | UNKNOWN / FAIL_CLOSED | PASS | preserved as diagnostic | 0 | 0 | PASS |

Notes:

- 94320 and 99840 now proceed into capital competition as positive ADD competitors when
  canonical ADD evidence passes, even when SI interpretation remains `NO_ADD`.
- Final allocation is not guaranteed by this repair. Later legitimate capital competition,
  cap, lot, or residual constraints may still reject or reduce ADD.
- 40520 remains blocked because expected edge is `WEAKENING / FAIL_CLOSED` and incremental
  value is `UNKNOWN / FAIL_CLOSED`. The SI gate removal did not create fail-open behavior.

## Regression Evidence

Focused ADD bridge regression:

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'g74 or canonical_add_bridge or d55_a or d61_add_current_above_base'
10 passed, 112 deselected in 1.79s
```

Focused downstream compatibility regression:

```text
python3 -m pytest tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g50_final_capital_winner_binding.py
16 passed in 1.52s
```

Python compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-g74 python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py
PASS
```

Diff whitespace check:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase22_e_portfolio_construction.py
PASS
```

## Acceptance Matrix

ADD_TARGET_WEIGHT_AUTHORITY_REPAIRED = YES

INTERPRETATION_ONLY_SI_HARD_ADD_GATE = NO

94320_POSITIVE_ADD_INCREMENT = YES

99840_POSITIVE_ADD_INCREMENT = YES

40520_EXPECTED_EDGE_WEAKENING_STILL_BLOCKS = YES

ADD_INVESTMENT_EVIDENCE_AUTHORITY_PRESERVED = YES

NEW_BUY_COMPETITION_PRESERVED = YES

CAP_SAFETY_PRESERVED = YES

PS_QUANTITY_AUTHORITY_PRESERVED = YES

RUNTIME_PRIORITY_REDECISION = NO

MARKET_QUALITY_CHANGED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_REGRESSION = PASS

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

## Scope Preservation

Unchanged:

- Market Quality / Risk Pacing semantics
- PM ADD thresholds / semantics
- Candidate ranking / NEW_BUY semantics
- ADD investment evidence producer semantics
- expected-edge weakening fail-closed
- PC / PS / Runtime ownership boundaries
- BUY / SELL independence
- Strategy parameters, thresholds, weights

## Next

G74修正は現在実行中のlong Historicalへ途中適用しない。
現在runはそのまま継続し、G74修正の性能Validationは現在run完了後の別fresh-runで行う。
