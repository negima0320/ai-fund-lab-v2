#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.canonical_data_source import load_phase9_data_source_config, resolve_data_source  # noqa: E402
from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh  # noqa: E402


def main() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="phase9j2_audit_") as tmp:
        root = Path(tmp)
        quotes = root / "jquants/quotes.parquet"
        listed = root / "jquants/listed.parquet"
        prohibited = root / "broker/snapshot.parquet"
        _write_quotes(quotes)
        _write_listed(listed)
        prohibited.parent.mkdir(parents=True)
        pd.DataFrame([{"target_date": "2026-06-15"}]).to_parquet(prohibited, index=False)
        config = root / "phase9_data_sources.yaml"
        config.write_text(
            "\n".join(
                [
                    "phase9_data_sources:",
                    f"  normalized_daily_quotes: {quotes}",
                    f"  listed_info: {listed}",
                    "  raw_daily_quotes: null",
                    "  trading_calendar: null",
                    "  candidate_features: null",
                    "  opportunity_features: null",
                    "  position_features: null",
                    "  capital_policy_inputs: null",
                    "  model_manifests: null",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        loaded = load_phase9_data_source_config(config)
        config_ref = resolve_data_source("normalized_daily_quotes", config_path=config)
        override_ref = resolve_data_source("normalized_daily_quotes", override_path=listed, config_path=config)
        fallback_ref = resolve_data_source("normalized_daily_quotes", config_path=root / "missing.yaml", allow_fallback=True)
        prohibited_ref = resolve_data_source("normalized_daily_quotes", override_path=prohibited, config_path=config)
        missing_config = root / "missing_normalized.yaml"
        missing_config.write_text(
            "\n".join(
                [
                    "phase9_data_sources:",
                    "  normalized_daily_quotes: null",
                    f"  listed_info: {listed}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        missing_result = run_feature_refresh(
            target_data_until="2026-06-15",
            dry_run=False,
            execute=True,
            config_path=missing_config,
            feature_output_root=root / "features_missing",
            manifest_root=root / "manifest_missing",
            markdown_report_path=root / "missing.md",
            json_report_path=root / "missing.json",
        )
        live_result = run_feature_refresh(
            target_data_until="2026-06-15",
            dry_run=False,
            execute=True,
            config_path=config,
            feature_output_root=root / "features_live",
            manifest_root=root / "manifest_live",
            markdown_report_path=root / "live.md",
            json_report_path=root / "live.json",
        )
        live_manifest = json.loads(Path(live_result.manifest_path).read_text(encoding="utf-8"))
        checks = {
            "canonical_config_readable": loaded.get("normalized_daily_quotes") == str(quotes),
            "config_priority": config_ref.path == str(quotes) and config_ref.source == "config",
            "cli_override_priority": override_ref.path == str(listed) and override_ref.source == "cli_override",
            "fallback_recorded": fallback_ref.fallback_used is True or fallback_ref.source == "missing",
            "prohibited_source_rejected": prohibited_ref.usable_for_phase9 is False and bool(prohibited_ref.blocked_reasons),
            "missing_canonical_path_fail_closed": missing_result.status == "FEATURE_REFRESH_FAILED",
            "feature_refresh_uses_resolver": live_manifest["artifacts"][0]["source_data_refs"]["normalized_daily_quotes_resolution"]["source"] == "config",
            "feature_refresh_manifest_records_path": str(quotes) in json.dumps(live_manifest),
            "no_model_retraining": not live_result.model_retraining_executed,
            "no_inference": not live_result.inference_executed,
            "no_order_plan": not live_result.order_plan_generation_executed,
            "no_broker_order": not live_result.broker_order_api_called,
            "no_virtual_fill": not live_result.virtual_fill_executed,
        }
    payload = {"phase": "Phase9-J2", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def _write_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for day in pd.bdate_range("2026-05-01", periods=32):
        rows.append(
            {
                "target_date": day.strftime("%Y-%m-%d"),
                "Date": day.strftime("%Y-%m-%d"),
                "code": "10010",
                "Code": "10010",
                "Close": 100.0,
                "Volume": 1000,
            }
        )
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"target_date": "2026-06-15", "Date": "2026-06-15", "code": "10010", "Code": "10010"}]).to_parquet(path, index=False)


if __name__ == "__main__":
    raise SystemExit(main())
