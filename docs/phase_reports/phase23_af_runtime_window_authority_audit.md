# Phase23-AF Runtime Window Authority Audit

## Judgment

`PHASE23_AF_REPAIR_REQUIRED`

## Scope

Evidence Reviewのみ。実装修正、Historical Test、Runtime Switch、Broker Write、J-Quants取得、canonical mutation は実施していない。

## 対象Run

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260729T111715014852Z/`

## A-1: 10BDが8BDへ変換された箇所

`scripts/runtime_test.py:4908-4915` で `build_plan()` が `resolve_business_dates()` の戻り値を `dates` として受け取る。

`scripts/runtime_test.py:4920` と `scripts/runtime_test.py:4966` で `requested_business_days` に CLI要求値ではなく `len(dates)` を保存している。

対象runの `plan.json` は以下を保存している。

```text
requested_start_date = 2026-07-06
requested_end_date   = 2026-07-15
requested_business_days = 8
business_dates = 2026-07-06, 07, 08, 09, 10, 13, 14, 15
```

`fresh_run_summary.json` も `business_days=8`, `date_from=2026-07-06`, `date_to=2026-07-15` で整合している。

## A-2: 2026-07-16 / 2026-07-17 除外根拠

`resolve_business_dates()` は `scripts/runtime_test.py:5415` で `load_trading_calendar_business_days()` を呼ぶ。

`load_trading_calendar_business_days()` のauthority pathは `scripts/runtime_test.py:5435-5437` により以下。

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet
```

このcalendar authorityは `validation.json` で `status=PASS`, `reason=calendar_authority_ready`, `max_date=2026-07-15`。実データも最大日付は `2026-07-15`。

Phase23-AD staging calendar には `2026-07-16` と `2026-07-17` が存在するが、Plan builderのcalendar authorityには含まれていない。そのため `start_date=2026-07-06` 以降で最大10件を取る処理は8件で終了した。

## A-3: 設計仕様かImplementation Bugか

Implementation Bug / Contract Gap。

理由は2つ。

- `requested_business_days` が「operator requested value」ではなく「resolved date list length」として保存され、10BD要求がPlan artifact上で消失している。
- Historical logical source compositionはPhase23-AEで normalized/raw/calendar のlogical inputに導入されたが、Runtime Test plan window authority は staging overlay calendar を見ない。

「available calendar authority内で可能な日数だけ実行する」仕様なら、Planには `requested_business_days=10`, `resolved_business_days=8`, `truncated_reason=calendar_authority_max_date_2026-07-15` のような区別が必要。現状はその区別がない。

## A-4: CLI / Plan / Run / Summary 整合

Plan保存後の整合は取れている。

- Plan: 8BD
- Run state: completed 8BD
- Fresh summary: 8BD
- Final summary: PASS

ただし、CLI/operator intent の10BDとPlan artifactの8BDは整合していない。変換理由もartifactに保持されていない。

## Root Cause

`PLAN_WINDOW_REQUEST_LOST_BY_RESOLVED_DATE_LIST_LENGTH_AND_CALENDAR_AUTHORITY_TRUNCATION`

## 修正要否

修正必要。Phase23-AGで、Plan window request preservation と resolved/truncated window authority の明示化が必要。

