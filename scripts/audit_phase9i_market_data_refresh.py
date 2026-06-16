#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh


class MockFetcher:
    def __init__(self) -> None:
        self.called = False

    def fetch_daily_quotes(self, *, from_date: str, to_date: str):
        self.called = True
        return [
            {"Date": "2026-06-16", "Code": "72030", "AdjO": 100, "AdjH": 110, "AdjL": 95, "AdjC": 105, "AdjVo": 1000}
        ]

    def fetch_listed_info(self, *, date: str):
        self.called = True
        return [{"Date": date, "Code": "72030", "CompanyName": "Toyota"}]

    def fetch_trading_calendar(self, *, from_date: str, to_date: str):
        self.called = True
        return [{"Date": "2026-06-16", "HolDiv": "1"}]


def main() -> int:
    root = Path("/private/tmp/phase9i_audit")
    dry_root = root / "dry"
    live_root = root / "live"
    dry_fetcher = MockFetcher()
    live_fetcher = MockFetcher()

    dry = run_market_data_refresh(
        from_date="2026-06-02",
        to_date="2026-06-16",
        dry_run=True,
        allow_api_fetch=False,
        raw_output_root=dry_root / "raw",
        normalized_output_root=dry_root / "raw_normalized",
        manifest_output_root=dry_root / "manifest",
        fetcher=dry_fetcher,
        today="2026-06-16",
        markdown_report_path=dry_root / "report.md",
        json_report_path=dry_root / "report.json",
    )
    blocked = run_market_data_refresh(
        from_date="2026-06-02",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=False,
        raw_output_root=root / "blocked/raw",
        normalized_output_root=root / "blocked/raw_normalized",
        manifest_output_root=root / "blocked/manifest",
        today="2026-06-16",
        markdown_report_path=root / "blocked/report.md",
        json_report_path=root / "blocked/report.json",
    )
    live = run_market_data_refresh(
        from_date="2026-06-16",
        to_date="2026-06-16",
        dry_run=False,
        allow_api_fetch=True,
        raw_output_root=live_root / "raw",
        normalized_output_root=live_root / "raw_normalized",
        manifest_output_root=live_root / "manifest",
        fetcher=live_fetcher,
        today="2026-06-16",
        markdown_report_path=live_root / "report.md",
        json_report_path=live_root / "report.json",
    )
    future_blocked = False
    try:
        run_market_data_refresh(
            from_date="2026-06-16",
            to_date="2026-06-17",
            dry_run=True,
            raw_output_root=root / "future/raw",
            normalized_output_root=root / "future/raw_normalized",
            manifest_output_root=root / "future/manifest",
            today="2026-06-16",
            markdown_report_path=root / "future/report.md",
            json_report_path=root / "future/report.json",
        )
    except ValueError:
        future_blocked = True

    combined_text = Path(dry.manifest_path).read_text(encoding="utf-8") + Path(live.manifest_path).read_text(encoding="utf-8")
    secret_free = all(term not in combined_text.lower() for term in ("api_key", "x-api-key", "authorization", "password", "secret"))
    checks = {
        "dry_run_no_api_call": dry.jquants_api_fetch_executed is False and dry_fetcher.called is False,
        "dry_run_no_raw_overwrite": not (dry_root / "raw/jquants/equities_bars_daily/data.parquet").exists(),
        "allow_api_fetch_required": blocked.status == "BLOCKED" and "allow_api_fetch_required" in blocked.blocked_reasons,
        "future_to_date_blocked": future_blocked,
        "manifest_generated": Path(live.manifest_path).exists(),
        "readiness_check_executed": bool(live.readiness_result.get("status")),
        "secret_not_in_manifest": secret_free,
        "no_broker_order": not live.broker_order_api_called,
        "no_open_d": not live.open_d_started,
        "no_unlock_trade": not live.unlock_trade_called,
        "no_virtual_fill": not live.virtual_fill_executed,
        "no_retraining": not live.model_retraining_executed,
        "no_inference": not live.inference_executed,
    }
    # The mock fetcher is shared; verify dry-run did not change its pre-live state by checking dry result flag.
    checks["dry_run_result_flag_no_api"] = dry.jquants_api_fetch_executed is False
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {"phase": "Phase9-I", "status": status, "checks": checks, "live_report": live.json_report_path}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
