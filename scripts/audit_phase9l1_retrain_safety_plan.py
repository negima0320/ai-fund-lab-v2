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

from ai_fund_lab_v2.paper_trading.training_dataset_audit import audit_training_dataset  # noqa: E402

AUDIT_PATH = ROOT / "scripts/audit_phase9l1_training_dataset_safety.py"
SPEC = importlib.util.spec_from_file_location("phase9l1_dataset_audit", AUDIT_PATH)
assert SPEC and SPEC.loader
phase9l1 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase9l1
SPEC.loader.exec_module(phase9l1)


def main() -> int:
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="phase9l1_audit_") as tmp:
        root = Path(tmp)
        quotes = root / "jquants/quotes.parquet"
        listed = root / "jquants/listed.parquet"
        calendar = root / "jquants/calendar.parquet"
        _write_quotes(quotes)
        _write_listed(listed)
        _write_calendar(calendar)
        payload = phase9l1.run_phase9l1_training_dataset_audit(
            normalized_daily_quotes_path=quotes,
            listed_info_path=listed,
            trading_calendar_path=calendar,
            data_until="2026-06-15",
            safe_train_until="2026-05-18",
            train_until="2026-05-18",
            label_horizon=20,
            output_root=root / "datasets",
            markdown_report_path=root / "report.md",
            json_report_path=root / "report.json",
        )
        candidate = payload["datasets"][0]
        forbidden = root / "forbidden.parquet"
        pd.DataFrame(
            [
                {
                    "target_date": "2026-05-19",
                    "code": "10010",
                    "feature__x": 1.0,
                    "label__future_return_20d": 0.1,
                    "cash": 100,
                }
            ]
        ).to_parquet(forbidden, index=False)
        forbidden_audit = audit_training_dataset(
            ai_name="candidate",
            dataset_path=forbidden,
            data_until="2026-06-15",
            safe_train_until="2026-05-18",
            train_until="2026-05-18",
            label_horizon=20,
            source_data_refs={"paper_ledger": ".runtime/phase9/ledger/latest.json"},
            label_source_until="2026-06-15",
        )
        checks = {
            "retrain_safety_plan_exists": Path("docs/phase_reports/phase9l1_retrain_safety_plan.md").is_file(),
            "dataset_candidate_builder_runs": payload["status"] == "TRAINING_DATASETS_READY",
            "training_dataset_audit_runs": bool(candidate["feature_schema_hash"]),
            "safe_train_until_respected": candidate["max_date"] <= "2026-05-18",
            "jquants_source_only": candidate["forbidden_source_check"] == "OK",
            "forbidden_source_detected": "forbidden_source_detected" in forbidden_audit.blocked_reasons,
            "future_leakage_detected": "feature_row_after_train_until" in forbidden_audit.blocked_reasons,
            "no_model_retraining": payload["model_retraining_executed"] is False,
            "no_inference": payload["inference_executed"] is False,
            "no_broker_order": payload["broker_order_api_called"] is False,
            "no_virtual_fill": payload["virtual_fill_executed"] is False,
        }
    checks = {key: bool(value) for key, value in checks.items()}
    result = {"phase": "Phase9-L1", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


def _write_quotes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for code in ("10010", "10020"):
        base = 100.0 if code == "10010" else 150.0
        for index, day in enumerate(pd.bdate_range("2026-03-02", "2026-06-15")):
            rows.append({"date": day.strftime("%Y-%m-%d"), "code": code, "close": base + index, "volume": 1000 + index})
    pd.DataFrame(rows).to_parquet(path, index=False)


def _write_listed(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Date": "2026-06-15", "Code": "10010"}, {"Date": "2026-06-15", "Code": "10020"}]).to_parquet(path, index=False)


def _write_calendar(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dates = pd.bdate_range("2026-03-02", "2026-06-15").strftime("%Y-%m-%d").tolist()
    pd.DataFrame({"Date": dates, "HolDiv": ["1"] * len(dates)}).to_parquet(path, index=False)


if __name__ == "__main__":
    raise SystemExit(main())
