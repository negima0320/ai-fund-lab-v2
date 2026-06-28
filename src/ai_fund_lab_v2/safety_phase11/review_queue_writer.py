from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.safety_phase11.event_writer import _phase11_sanitize, _write_json
from ai_fund_lab_v2.safety_phase11.report_schema import build_review_queue_items


def build_review_queue_payload(result: Any, *, safety_report_path: str = "") -> dict[str, Any]:
    items = build_review_queue_items(result, safety_report_path=safety_report_path)
    payload = {
        "schema_version": "phase11_human_review_queue_v1",
        "business_date": getattr(result, "business_date", None) or "unknown_business_date",
        "environment": getattr(result, "environment", None) or "unknown_environment",
        "runtime_id": getattr(result, "runtime_id", None) or "unknown_runtime",
        "item_count": len(items),
        "items": items,
        "no_live_order_confirmation": {
            "broker_api_connected": False,
            "websocket_connected": False,
            "demo_order_submitted": False,
            "production_order_submitted": False,
            "clm_kabu_new_order_executed": False,
        },
    }
    return _phase11_sanitize(payload)


def write_review_queue(
    result: Any,
    *,
    safety_report_path: Path | str = "",
    reports_dir: Path | str = "reports",
) -> Path:
    business_date = getattr(result, "business_date", None) or "unknown_business_date"
    directory = Path(reports_dir) / "safety" / "phase11" / "review_queue"
    path = directory / f"{business_date}_review_queue.json"
    payload = build_review_queue_payload(result, safety_report_path=str(safety_report_path))
    _write_json(path, payload)
    return path


def write_runtime_review_queue(
    result: Any,
    *,
    safety_report_path: Path | str = "",
    runtime_dir: Path | str = ".runtime",
) -> Path:
    business_date = getattr(result, "business_date", None) or "unknown_business_date"
    directory = Path(runtime_dir) / "safety" / "phase11" / "review_queue"
    path = directory / f"{business_date}_review_queue.json"
    payload = build_review_queue_payload(result, safety_report_path=str(safety_report_path))
    _write_json(path, payload)
    return path
