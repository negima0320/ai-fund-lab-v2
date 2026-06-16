#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

SCRIPT_PATH = ROOT / "scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py"
SPEC = importlib.util.spec_from_file_location("phase9j3_rebuild", SCRIPT_PATH)
assert SPEC and SPEC.loader
phase9j3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase9j3
SPEC.loader.exec_module(phase9j3)


def main() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="phase9j3_audit_") as tmp:
        root = Path(tmp)
        raw_root = root / ".runtime/data/raw/jquants/equities_bars_daily/responses"
        supplemental = root / ".runtime/data/raw/jquants/equities_bars_daily/data.parquet"
        listed = root / ".runtime/data/raw/jquants/listed_issues/data.parquet"
        raw_normalized = root / ".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet"
        output_root = root / ".runtime/phase9/canonical_data/normalized_daily_quotes"
        config = root / "config/phase9_data_sources.yaml"
        _write_raw_responses(raw_root)
        _write_supplemental(supplemental)
        _write_listed(listed)
        raw_normalized.parent.mkdir(parents=True, exist_ok=True)
        raw_normalized.write_text("do-not-overwrite", encoding="utf-8")
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            "\n".join(
                [
                    "phase9_data_sources:",
                    f"  raw_daily_quotes: {raw_root}",
                    "  normalized_daily_quotes: null",
                    f"  listed_info: {listed}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        dry = phase9j3.rebuild_canonical_normalized_daily_quotes(
            raw_root=raw_root,
            target_data_until="2026-06-15",
            dry_run=True,
            execute=False,
            output_root=output_root,
            config_path=config,
            supplemental_raw_table=supplemental,
            listed_info_path=listed,
            markdown_report_path=root / "dry.md",
            json_report_path=root / "dry.json",
        )
        after_dry_config = config.read_text(encoding="utf-8")
        dry_normalized_exists = (output_root / "data.parquet").exists()
        execute = phase9j3.rebuild_canonical_normalized_daily_quotes(
            raw_root=raw_root,
            target_data_until="2026-06-15",
            dry_run=False,
            execute=True,
            output_root=output_root,
            config_path=config,
            supplemental_raw_table=supplemental,
            listed_info_path=listed,
            markdown_report_path=root / "execute.md",
            json_report_path=root / "execute.json",
            feature_output_root=root / ".runtime/phase9/features",
            feature_manifest_root=root / ".runtime/phase9/feature_refresh",
            feature_markdown_report_path=root / "feature.md",
            feature_json_report_path=root / "feature.json",
        )
        frame = pd.read_parquet(output_root / "data.parquet")
        candidate = pd.read_parquet(root / ".runtime/phase9/features/2026-06-15/candidate_features.parquet")
        opportunity = pd.read_parquet(root / ".runtime/phase9/features/2026-06-15/opportunity_feature_input.parquet")
        feature_columns = [column for column in opportunity.columns if column.startswith("feature__")]

        checks = {
            "dry_run_no_normalized_write": not dry_normalized_exists,
            "dry_run_no_config_update": "normalized_daily_quotes: null" in after_dry_config,
            "execute_writes_isolated_normalized": (output_root / "data.parquet").is_file(),
            "existing_raw_normalized_not_overwritten": raw_normalized.read_text(encoding="utf-8") == "do-not-overwrite",
            "config_updated_on_execute": str(output_root / "data.parquet") in config.read_text(encoding="utf-8"),
            "jquants_raw_only": execute.jquants_only_source_used is True and "jquants" in execute.raw_root,
            "future_rows_excluded": frame["date"].astype(str).max() == "2026-06-15" and "2026-06-16" not in set(frame["date"].astype(str)),
            "duplicate_date_code_absent": frame.duplicated(subset=["date", "code"]).sum() == 0,
            "readiness_ready": execute.readiness_status == "READY" and execute.lookback_ready is True,
            "feature_refresh_rerun": execute.feature_refresh_status == "FEATURES_READY",
            "candidate_eligible_rows_positive": int(candidate["universe_eligible"].fillna(False).astype(bool).sum()) > 0,
            "opportunity_non_null_rows_positive": int(opportunity[feature_columns].notna().any(axis=1).sum()) > 0,
            "no_model_retraining": not execute.model_retraining_executed,
            "no_inference": not execute.inference_executed,
            "no_order_plan": not execute.order_plan_generation_executed,
            "no_broker_order": not execute.broker_order_api_called,
            "no_virtual_fill": not execute.virtual_fill_executed,
        }
    checks = {key: bool(value) for key, value in checks.items()}
    payload = {"phase": "Phase9-J3", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 1


def _write_raw_responses(raw_root: Path) -> None:
    raw_root.mkdir(parents=True, exist_ok=True)
    for day in pd.bdate_range("2026-05-01", "2026-06-12"):
        date = day.strftime("%Y-%m-%d")
        payload = {
            "api_call_performed": True,
            "date": date,
            "endpoint": "/v2/equities/bars/daily",
            "payload": {
                "data": [
                    _raw_record(date, "10010", 100 + index)
                    for index in range(2)
                ]
            },
            "phase": 9,
        }
        (raw_root / f"{date}_page_001.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_supplemental(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for day in pd.bdate_range("2026-06-01", "2026-06-16"):
        date = day.strftime("%Y-%m-%d")
        rows.append(_raw_record(date, "10010", 150))
        rows.append(_raw_record(date, "10020", 170))
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"target_date": "2026-06-15", "Date": "2026-06-15", "code": "10010", "Code": "10010"},
            {"target_date": "2026-06-15", "Date": "2026-06-15", "code": "10020", "Code": "10020"},
        ]
    ).to_parquet(path, index=False)


def _raw_record(date: str, code: str, base: float) -> dict[str, object]:
    return {
        "Date": date,
        "Code": code,
        "AdjO": base,
        "AdjH": base + 2,
        "AdjL": base - 1,
        "AdjC": base + 1,
        "AdjVo": 1000,
        "O": base,
        "H": base + 2,
        "L": base - 1,
        "C": base + 1,
        "Vo": 1000,
    }


if __name__ == "__main__":
    raise SystemExit(main())
