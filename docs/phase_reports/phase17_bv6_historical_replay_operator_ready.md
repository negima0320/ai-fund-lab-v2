# Phase17-BV6 Historical Replay Operator Ready

## Summary

Final judgment: `PHASE17_BV6_OPERATOR_READY`

Runtime Test execution was not performed. Runtime Test plan execution was also not performed. This phase only inspected and prepared the Operator command boundary.

## Findings

- `runtime_test.py plan` and `runtime_test.py run` already supported `--start-date`, `--business-days`, `--date-from`, and `--date-to`.
- BV6 added `--end-date` as an alias for `--date-to` so the Operator can use the requested start/end vocabulary.
- Existing `historical-smoke` profile was not changed.
- Existing `historical-extended-smoke` profile is used for BV6.
- Date resolution now uses the accepted Historical Trading Calendar authority when present: `.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet`.

## Calendar Fact

The requested range `2021-07-16` through `2021-07-30` contains 9 JP trading days, not 10, because `2021-07-22` and `2021-07-23` are non-trading days in the accepted calendar.

Trading days:

```text
2021-07-16
2021-07-19
2021-07-20
2021-07-21
2021-07-26
2021-07-27
2021-07-28
2021-07-29
2021-07-30
```

If the acceptance must be exactly 10 trading days starting from `2021-07-16`, the resolved end date is `2021-08-02`.

## Recommended Operator Command

Strict requested range plan command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-extended-smoke --date-from 2021-07-16 --end-date 2021-07-30 --write-evidence --json
```

After the plan is accepted, the matching run command is:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run --profile historical-extended-smoke --date-from 2021-07-16 --end-date 2021-07-30 --confirm --yes-i-understand-this-mutates-trading-state --json
```

If the next phase requires literal 10 trading days instead of the stated end date:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-extended-smoke --business-days 10 --start-date 2021-07-16 --write-evidence --json
```

Then, after plan acceptance:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run --profile historical-extended-smoke --business-days 10 --start-date 2021-07-16 --confirm --yes-i-understand-this-mutates-trading-state --json
```

## Verification

- Targeted tests: `13 passed in 3.58s`
- Full `tests/runtime_v2`: `906 passed in 23.04s`
- py_compile: PASS
- git diff --check: PASS

## Prohibited Operations

No Runtime Test `run`, `resume`, `reset`, `rollback`, or `close` was executed. No Frozen Run was edited. No broker write, order submit, external notification, J-Quants fetch, or Registry refresh was performed.
