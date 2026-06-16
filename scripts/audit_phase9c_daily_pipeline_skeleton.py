from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.data_store.storage_backends import JsonlStorageBackend
from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import run_daily_pipeline


def run_audit(*, output_root: Path) -> dict[str, object]:
    backend = JsonlStorageBackend()
    fixture_dir = output_root / "fixtures"
    daily_path = fixture_dir / "daily_quotes.jsonl"
    listed_path = fixture_dir / "listed_info.jsonl"
    future_path = fixture_dir / "daily_quotes_future.jsonl"
    backend.write_records(
        daily_path,
        [
            {"Date": "2026-06-16", "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000},
        ],
    )
    backend.write_records(listed_path, [{"Date": "2026-06-16", "Code": "7203", "CompanyName": "Toyota Motor"}])
    backend.write_records(
        future_path,
        [
            {"Date": "2026-06-17", "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000},
        ],
    )
    ok = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=output_root / ".runtime_ok",
        reports_root=output_root / "reports_ok",
        daily_quotes_path=daily_path,
        listed_info_path=listed_path,
    )
    missing = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=output_root / ".runtime_missing",
        reports_root=output_root / "reports_missing",
        daily_quotes_path=fixture_dir / "missing.jsonl",
        listed_info_path=listed_path,
    )
    future = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=output_root / ".runtime_future",
        reports_root=output_root / "reports_future",
        daily_quotes_path=future_path,
        listed_info_path=listed_path,
    )
    checks = {
        "normal_pipeline_runs": ok.status == "OK",
        "missing_data_halt_report": missing.status == "HALT" and Path(missing.internal_report_md_path).exists(),
        "manifest_generated": Path(ok.manifest_path).exists() and Path(missing.manifest_path).exists(),
        "reports_generated": all(
            Path(path).exists()
            for path in (
                ok.internal_report_md_path,
                ok.public_report_path,
                ok.blog_draft_path,
                missing.internal_report_md_path,
                missing.public_report_path,
                missing.blog_draft_path,
            )
        ),
        "no_broker_order_api": not ok.broker_order_api_called and not missing.broker_order_api_called,
        "no_open_d": not ok.open_d_started and not missing.open_d_started,
        "no_unlock_trade": not ok.unlock_trade_called and not missing.unlock_trade_called,
        "no_paper_ledger_fill": not ok.paper_ledger_fill_executed and not missing.paper_ledger_fill_executed,
        "future_row_invalid": future.market_data.status == "INVALID",
    }
    summary = {
        "phase": "Phase9-C",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "normal": ok.to_dict(),
        "missing": missing.to_dict(),
        "future": future.to_dict(),
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9c_daily_pipeline_skeleton_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-C daily pipeline skeleton.")
    parser.add_argument("--output-root", default="/private/tmp/phase9c_audit")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps({"phase": summary["phase"], "status": summary["status"], "checks": summary["checks"]}, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

