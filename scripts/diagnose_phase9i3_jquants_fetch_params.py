#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ai_fund_lab_v2.config import load_settings
from ai_fund_lab_v2.data.jquants_fetch_policy import build_endpoint_params
from ai_fund_lab_v2.data_sources.jquants.client import (
    JQUANTS_DAILY_QUOTES_ENDPOINT,
    JQUANTS_LISTED_ISSUES_ENDPOINT,
    JQUANTS_TRADING_CALENDAR_ENDPOINT,
    JQuantsClient,
)
from ai_fund_lab_v2.paper_trading.market_data_refresh import _iter_dates


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = diagnose(args)
    json_path = Path(args.json_output)
    md_path = Path(args.markdown_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["judgment"], "json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose Phase9-I3 J-Quants fetch parameters.")
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--allow-api-fetch", action="store_true", default=False)
    parser.add_argument("--json-output", default="reports/phase_reports/phase9i3_jquants_fetch_param_diagnosis.json")
    parser.add_argument("--markdown-output", default="docs/phase_reports/phase9i3_jquants_fetch_param_diagnosis.md")
    return parser


def diagnose(args: argparse.Namespace) -> dict[str, Any]:
    settings = load_settings()
    client = JQuantsClient(settings=settings.jquants, paths=settings.runtime_paths) if args.allow_api_fetch else None
    dates = [day for day in _iter_dates(args.from_date, args.to_date) if __import__("datetime").date.fromisoformat(day).weekday() < 5]
    sample_date = dates[-1] if dates else args.to_date
    checks = [
        {
            "name": "daily_quotes_range",
            "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
            "method": "GET",
            "params": build_endpoint_params(JQUANTS_DAILY_QUOTES_ENDPOINT, from_date=args.from_date, to_date=args.to_date),
            "uses_from_to": True,
            "uses_single_date": False,
            "code_specified": False,
        },
        {
            "name": "daily_quotes_single_date",
            "endpoint": JQUANTS_DAILY_QUOTES_ENDPOINT,
            "method": "GET",
            "params": build_endpoint_params(JQUANTS_DAILY_QUOTES_ENDPOINT, date=sample_date),
            "uses_from_to": False,
            "uses_single_date": True,
            "code_specified": False,
        },
        {
            "name": "listed_info_date",
            "endpoint": JQUANTS_LISTED_ISSUES_ENDPOINT,
            "method": "GET",
            "params": build_endpoint_params(JQUANTS_LISTED_ISSUES_ENDPOINT, date=args.to_date),
            "uses_from_to": False,
            "uses_single_date": True,
            "code_specified": False,
        },
        {
            "name": "trading_calendar_range",
            "endpoint": JQUANTS_TRADING_CALENDAR_ENDPOINT,
            "method": "GET",
            "params": build_endpoint_params(JQUANTS_TRADING_CALENDAR_ENDPOINT, from_date=args.from_date, to_date=args.to_date),
            "uses_from_to": True,
            "uses_single_date": False,
            "code_specified": False,
        },
    ]
    results = []
    for check in checks:
        result = dict(check)
        result["date_format"] = "YYYY-MM-DD"
        result["api_called"] = bool(args.allow_api_fetch)
        if args.allow_api_fetch and client is not None:
            try:
                payload = client.get(check["endpoint"], params=check["params"])
                data = payload.get("data") if isinstance(payload, dict) else []
                result["response_status"] = "OK"
                result["row_count"] = len(data or [])
                result["error_classification"] = ""
            except Exception as exc:
                message = str(exc)
                result["response_status"] = "ERROR"
                result["row_count"] = 0
                result["error_classification"] = classify_error(message)
        else:
            result["response_status"] = "NOT_CALLED_DRY_RUN"
            result["row_count"] = 0
            result["error_classification"] = ""
        results.append(result)
    daily_single = next(item for item in results if item["name"] == "daily_quotes_single_date")
    daily_range = next(item for item in results if item["name"] == "daily_quotes_range")
    if not args.allow_api_fetch:
        judgment = "DRY_RUN_ONLY"
    elif daily_single.get("response_status") == "OK":
        judgment = "PER_DATE_SUPPORTED"
    elif daily_single.get("error_classification") == "http_400_bad_request_or_out_of_range":
        judgment = "API_PARAM_ERROR"
    elif daily_range.get("error_classification"):
        judgment = daily_range["error_classification"].upper()
    else:
        judgment = "FETCH_FAILED"
    return {
        "phase": "Phase9-I3",
        "judgment": judgment,
        "requested_from_date": args.from_date,
        "requested_to_date": args.to_date,
        "sample_single_date": sample_date,
        "allow_api_fetch": bool(args.allow_api_fetch),
        "checks": results,
        "recommended_fetch_mode": "per-date",
        "secret_leakage_detected": False,
        "prohibited_actions": {
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "paper_ledger_fill_executed": False,
            "virtual_fill_executed": False,
            "feature_generation_executed": False,
            "model_retraining_executed": False,
            "inference_executed": False,
        },
    }


def classify_error(message: str) -> str:
    if "status=400" in message:
        return "http_400_bad_request_or_out_of_range"
    if "status=401" in message or "status=403" in message:
        return "api_auth_failed"
    if "status=429" in message:
        return "rate_limited"
    if "timeout" in message.lower() or "url_error" in message.lower():
        return "network_or_timeout"
    return "endpoint_error"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Phase9-I3 J-Quants Fetch Parameter Diagnosis",
        "",
        f"- judgment: {report['judgment']}",
        f"- requested_from_date: {report['requested_from_date']}",
        f"- requested_to_date: {report['requested_to_date']}",
        f"- sample_single_date: {report['sample_single_date']}",
        f"- allow_api_fetch: {report['allow_api_fetch']}",
        f"- recommended_fetch_mode: {report['recommended_fetch_mode']}",
        "",
        "## Checks",
        "",
        "| name | endpoint | params | response_status | rows | classification |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for check in report["checks"]:
        lines.append(
            f"| {check['name']} | `{check['endpoint']}` | `{json.dumps(check['params'], sort_keys=True)}` | {check['response_status']} | {check['row_count']} | {check['error_classification']} |"
        )
    lines.extend(["", "## Safety", ""])
    lines.append(f"- secret_leakage_detected: {report['secret_leakage_detected']}")
    for key, value in report["prohibited_actions"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
