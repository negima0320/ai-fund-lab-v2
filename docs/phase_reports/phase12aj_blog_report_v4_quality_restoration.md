# Phase12-AJ Blog Report v4 Quality Restoration

## Status

```text
PHASE12AJ_BLOG_REPORT_V4_QUALITY_RESTORATION_COMPLETE
```

Phase12 Daily Report writer was restored from an operations-log style report to a Phase9 `blog_report_v4`-equivalent daily blog format.

## Regression Cause

The Phase12 writer had been generating Markdown directly from Operations status dictionaries. That produced table-heavy internal logs and weak BUY explanations, including `-` in reason columns. It also omitted Candidate Top50 and the candidate-by-candidate explanation section expected from Phase9 v4.

## Writer Fix

Updated:

```text
src/ai_fund_lab_v2/operations/operations.py
```

The writer now builds a report model from:

- Order Plan
- submitted orders
- Fill Monitor
- Broker read-only artifacts
- Persistent Demo Ledger / ledger summary
- Safety Monitor
- Reconcile
- Operation Audit
- J-Quants listed info
- Operations candidate feature artifact

The Markdown renderer now produces blog chapters rather than dict dumps.

## Required Chapters

Generated `blog_draft.md` and `public_report.md` include:

```text
資産状況
現在保有中の銘柄
本日注文・約定した銘柄
本日の売却銘柄
Candidate Top50
翌営業日の購入予定候補 Top5
なぜこの5銘柄が購入候補なのか
Broker / Demo運用状況
Safety / Reconcile / Audit
AIの総括
注意書き
```

## Candidate Explanation

Candidate Top50 is generated from the Operations feature artifact. Top5 explanations include:

- internal code
- broker issue code
- issue name
- market
- Candidate rank
- Opportunity rank
- 5-day return
- 20-day return
- volume ratio
- 20-day average volume
- 20-day moving-average divergence
- public confidence score

High-ratio fields that are not present in the current Operations artifact are described naturally as unavailable in the artifact, rather than printed as `-`.

The public confidence score is rank-based explanation scoring, not win probability or future return probability.

## Today Regeneration

Regenerated for `2026-06-30`:

```text
.runtime/operations/reports/2026-06-30/blog_draft.md
.runtime/operations/reports/2026-06-30/public_report.md
.runtime/operations/reports/2026-06-30/safety_report.md
.runtime/operations/reports/2026-06-30/line_payload.json
.runtime/operations/reports/2026-06-30/discord_payload.json
.runtime/operations/daily_report_refs/2026-06-30/daily_report_refs.json
```

Metadata:

```text
regenerated=true
regenerated_reason=phase12aj_blog_report_v4_quality_restoration
```

## Notification Payload

`line_payload.json` and `discord_payload.json` now include:

- report date
- BUY candidate Top5 summary
- same-day order result
- Safety
- Reconcile
- Audit
- report path

No LINE or Discord actual send was executed during this restoration pass.

## Safety

```text
demo_order_executed=false
production_order_executed=false
production_unlock_executed=false
ai_retraining_executed=false
backtest_rerun=false
raw_request_saved=false
raw_response_saved=false
secret_saved=false
launchctl_bootstrap_executed=false
```

## Verification

```bash
python3 -m pytest tests/phase12 -q
PYTHONPYCACHEPREFIX=/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/operations.py src/ai_fund_lab_v2/operations/notifications.py scripts/run_daily_report.py
python3 scripts/run_daily_report.py --trade-date 2026-06-30 --root .runtime/operations
python3 -m json.tool reports/phase_reports/phase12aj_blog_report_v4_quality_restoration.json
```

Results:

```text
pytest=74 passed
py_compile=PASS
daily_report_regeneration=PASS
json_validation=PASS
dict_repr_scan=PASS_NO_MATCH
```
