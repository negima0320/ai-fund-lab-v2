#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_fund_lab_v2.paper_trading.feature_refresh import FEATURE_REFRESH_REQUIRED, run_feature_refresh


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase9j_audit_") as tmp:
        tmp_path = Path(tmp)
        dry = run_feature_refresh(
            target_data_until="2026-06-15",
            dry_run=True,
            execute=False,
            daily_quotes_path=".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet",
            listed_info_path=".runtime/data/raw/jquants/listed_issues/data.parquet",
            feature_output_root=tmp_path / "features",
            manifest_root=tmp_path / "manifest",
            markdown_report_path=tmp_path / "dry_report.md",
            json_report_path=tmp_path / "dry_report.json",
        )
        live = run_feature_refresh(
            target_data_until="2026-06-15",
            dry_run=False,
            execute=True,
            daily_quotes_path=".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet",
            listed_info_path=".runtime/data/raw/jquants/listed_issues/data.parquet",
            feature_output_root=tmp_path / "features",
            manifest_root=tmp_path / "manifest",
            markdown_report_path=tmp_path / "live_report.md",
            json_report_path=tmp_path / "live_report.json",
        )
        checks = {
            "dry_run_does_not_generate_features": dry.status == FEATURE_REFRESH_REQUIRED and not dry.feature_generation_executed,
            "execute_generates_features": live.feature_generation_executed and live.status in {"FEATURES_READY", "FEATURE_REFRESH_REQUIRED"},
            "manifest_generated": Path(live.manifest_path).is_file(),
            "report_generated": Path(live.markdown_report_path).is_file() and Path(live.json_report_path).is_file(),
            "lookback_gap_detected": "candidate_no_universe_eligible_rows" in live.blocked_reasons,
            "candidate_status_recorded": any(item.ai_name == "candidate" for item in live.artifacts),
            "opportunity_status_recorded": any(item.ai_name == "opportunity" for item in live.artifacts),
            "position_status_recorded": any(item.ai_name == "position" for item in live.artifacts),
            "capital_status_recorded": any(item.ai_name == "capital" for item in live.artifacts),
            "schema_hash_recorded": all(item.feature_schema_hash for item in live.artifacts),
            "future_leakage_check_ok": all(item.future_leakage_check_status == "OK" for item in live.artifacts),
            "no_model_retraining": not live.model_retraining_executed,
            "no_inference": not live.inference_executed,
            "no_order_plan": not live.order_plan_generation_executed,
            "no_broker_order": not live.broker_order_api_called,
            "no_open_d": not live.open_d_started,
            "no_unlock_trade": not live.unlock_trade_called,
            "no_virtual_fill": not live.virtual_fill_executed,
        }
    payload = {"phase": "Phase9-J", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
