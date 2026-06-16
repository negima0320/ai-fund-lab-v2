#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.training_dataset_candidate import build_training_dataset_candidates  # noqa: E402


DEFAULT_MD_REPORT = Path("docs/phase_reports/phase9l1_training_dataset_safety_audit.md")
DEFAULT_JSON_REPORT = Path("reports/phase_reports/phase9l1_training_dataset_safety_audit.json")


def run_phase9l1_training_dataset_audit(
    *,
    normalized_daily_quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    listed_info_path: Path | str = ".runtime/data/raw/jquants/listed_issues/data.parquet",
    trading_calendar_path: Path | str = ".runtime/data/raw/jquants/trading_calendar/data.parquet",
    data_until: str = "2026-06-15",
    safe_train_until: str = "2026-05-18",
    train_until: str = "2026-05-18",
    label_horizon: int = 20,
    output_root: Path | str = ".runtime/phase9/training_dataset_candidates",
    markdown_report_path: Path | str = DEFAULT_MD_REPORT,
    json_report_path: Path | str = DEFAULT_JSON_REPORT,
) -> dict:
    result = build_training_dataset_candidates(
        normalized_daily_quotes_path=normalized_daily_quotes_path,
        listed_info_path=listed_info_path,
        trading_calendar_path=trading_calendar_path,
        data_until=data_until,
        safe_train_until=safe_train_until,
        train_until=train_until,
        label_horizon=label_horizon,
        output_root=output_root,
    )
    payload = {
        "phase": "Phase9-L1",
        "status": result.status,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "data_until": data_until,
        "safe_train_until": safe_train_until,
        "train_until": train_until,
        "label_horizon": label_horizon,
        "dataset_manifest_path": result.manifest_path,
        "datasets": [item.to_dict() for item in result.datasets],
        "next_action": _next_action(result.status),
        "model_retraining_executed": False,
        "inference_executed": False,
        "order_plan_generation_executed": False,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
    }
    _write_outputs(payload, Path(markdown_report_path), Path(json_report_path))
    return payload


def _next_action(status: str) -> str:
    if status == "TRAINING_DATASETS_READY":
        return "Proceed to Phase9-L2 controlled retrain execution plan; do not promote models automatically."
    if status == "TRAINING_DATASET_REPAIR_REQUIRED":
        return "Review null-rate and schema warnings before retrain."
    return "Repair dataset blockers before any retrain."


def _write_outputs(payload: dict, markdown_path: Path, json_path: Path) -> None:
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict) -> str:
    lines = [
        "# Phase9-L1 Training Dataset Safety Audit",
        "",
        f"- status: {payload['status']}",
        f"- data_until: {payload['data_until']}",
        f"- safe_train_until: {payload['safe_train_until']}",
        f"- train_until: {payload['train_until']}",
        f"- label_horizon: {payload['label_horizon']}",
        f"- dataset_manifest_path: `{payload['dataset_manifest_path']}`",
        "",
        "## Datasets",
        "",
        "| AI | status | rows | min_date | max_date | code_count | schema_hash | forbidden | leakage |",
        "| --- | --- | ---: | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in payload["datasets"]:
        lines.append(
            f"| {item['ai_name']} | {item['status']} | {item['row_count']} | {item['min_date']} | "
            f"{item['max_date']} | {item['code_count']} | `{item['feature_schema_hash']}` | "
            f"{item['forbidden_source_check']}/{item['forbidden_columns_check']} | {item['future_leakage_check']} |"
        )
    lines.extend(["", "## Blockers", ""])
    blockers = [f"{item['ai_name']}: {reason}" for item in payload["datasets"] for reason in item["blocked_reasons"]]
    lines.extend([f"- {reason}" for reason in blockers] or ["- none"])
    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- model_retraining_executed: {payload['model_retraining_executed']}",
            f"- inference_executed: {payload['inference_executed']}",
            f"- order_plan_generation_executed: {payload['order_plan_generation_executed']}",
            f"- broker_order_api_called: {payload['broker_order_api_called']}",
            f"- virtual_fill_executed: {payload['virtual_fill_executed']}",
            "",
            "## Next Action",
            "",
            f"- {payload['next_action']}",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-L1 training dataset safety.")
    parser.add_argument("--normalized-daily-quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--listed-info-path", default=".runtime/data/raw/jquants/listed_issues/data.parquet")
    parser.add_argument("--trading-calendar-path", default=".runtime/data/raw/jquants/trading_calendar/data.parquet")
    parser.add_argument("--data-until", default="2026-06-15")
    parser.add_argument("--safe-train-until", default="2026-05-18")
    parser.add_argument("--train-until", default="2026-05-18")
    parser.add_argument("--label-horizon", type=int, default=20)
    parser.add_argument("--output-root", default=".runtime/phase9/training_dataset_candidates")
    parser.add_argument("--markdown-report-path", default=str(DEFAULT_MD_REPORT))
    parser.add_argument("--json-report-path", default=str(DEFAULT_JSON_REPORT))
    args = parser.parse_args()
    payload = run_phase9l1_training_dataset_audit(
        normalized_daily_quotes_path=args.normalized_daily_quotes_path,
        listed_info_path=args.listed_info_path,
        trading_calendar_path=args.trading_calendar_path,
        data_until=args.data_until,
        safe_train_until=args.safe_train_until,
        train_until=args.train_until,
        label_horizon=args.label_horizon,
        output_root=args.output_root,
        markdown_report_path=args.markdown_report_path,
        json_report_path=args.json_report_path,
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "TRAINING_DATASETS_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
