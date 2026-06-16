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
from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import AIArtifactPaths, adapt_ai_artifacts
from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import run_daily_pipeline
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction


def run_audit(*, output_root: Path) -> dict[str, object]:
    fixture = output_root / "fixtures"
    artifact_root = fixture / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    daily_path, listed_path = _write_market_fixtures(fixture)
    _write_artifacts(artifact_root)
    adapter = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(
            candidate_artifact=artifact_root / "candidate_artifact.json",
            opportunity_artifact=artifact_root / "opportunity_artifact.json",
            position_artifact=artifact_root / "position_artifact.json",
            allocation_artifact=artifact_root / "allocation_artifact.json",
            order_plan_artifact=artifact_root / "order_plan_artifact.json",
        ),
    )
    pipeline = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=output_root / ".runtime",
        reports_root=output_root / "reports",
        daily_quotes_path=daily_path,
        listed_info_path=listed_path,
        artifact_root=artifact_root,
        use_artifacts=True,
    )
    missing = run_daily_pipeline(
        run_date="2026-06-16",
        runtime_dir=output_root / ".runtime_missing",
        reports_root=output_root / "reports_missing",
        daily_quotes_path=daily_path,
        listed_info_path=listed_path,
        artifact_root=fixture / "missing_artifacts",
        use_artifacts=True,
    )
    invalid_order_plan_path = artifact_root / "order_plan_invalid.json"
    invalid_order_plan_path.write_text(
        json.dumps({"executable": True, "live_order_allowed": False, "requires_human_review": True, "items": []}),
        encoding="utf-8",
    )
    invalid_order_plan = adapt_ai_artifacts(
        decision_for="2026-06-16",
        data_until="2026-06-16",
        paths=AIArtifactPaths(order_plan_artifact=invalid_order_plan_path),
    )
    public_text = Path(pipeline.public_report_path).read_text(encoding="utf-8")
    redaction = check_public_report_redaction(public_text)
    checks = {
        "candidate_loaded": any(status.name == "candidate" and status.status == "READY" for status in adapter.artifact_statuses),
        "opportunity_loaded": any(status.name == "opportunity" and status.status == "READY" for status in adapter.artifact_statuses),
        "position_loaded": any(status.name == "position" and status.status == "READY" for status in adapter.artifact_statuses),
        "allocation_loaded": any(status.name == "allocation" and status.status == "READY" for status in adapter.artifact_statuses),
        "order_plan_loaded": any(status.name == "order_plan" and status.status == "READY" for status in adapter.artifact_statuses),
        "daily_result_reflected": bool(pipeline.daily_result.buy_candidates and pipeline.daily_result.sell_candidates and pipeline.daily_result.hold_candidates),
        "order_plan_safety_invariant": invalid_order_plan.status == "INVALID",
        "missing_artifact_halt_report": missing.status == "HALT" and Path(missing.internal_report_md_path).exists(),
        "public_redaction_ready": redaction.ready,
        "no_broker_order_api": not pipeline.broker_order_api_called,
        "no_open_d": not pipeline.open_d_started,
        "no_unlock_trade": not pipeline.unlock_trade_called,
        "no_paper_ledger_fill": not pipeline.paper_ledger_fill_executed,
    }
    summary = {
        "phase": "Phase9-D",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "pipeline": pipeline.to_dict(),
        "missing": missing.to_dict(),
        "invalid_order_plan": invalid_order_plan.to_dict(),
    }
    audit_path = output_root / "reports" / "phase_reports" / "phase9d_ai_artifact_integration_audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _write_market_fixtures(root: Path) -> tuple[Path, Path]:
    backend = JsonlStorageBackend()
    daily = root / "daily_quotes.jsonl"
    listed = root / "listed_info.jsonl"
    backend.write_records(daily, [{"Date": "2026-06-16", "Code": "7203", "Open": 100, "High": 110, "Low": 99, "Close": 108, "Volume": 1000}])
    backend.write_records(listed, [{"Date": "2026-06-16", "Code": "7203"}])
    return daily, listed


def _write_artifacts(root: Path) -> None:
    payloads = {
        "candidate_artifact.json": {"rows": [{"code": "7203", "name": "Toyota Motor", "rank": 1, "candidate_score": 0.80, "data_until": "2026-06-16", "decision_for": "2026-06-16", "reason": "candidate"}]},
        "opportunity_artifact.json": {"rows": [{"code": "7203", "name": "Toyota Motor", "buy_rank": 1, "expected_edge_score": 0.81, "data_until": "2026-06-16", "decision_for": "2026-06-16", "reason": "opportunity"}]},
        "position_artifact.json": {"rows": [{"code": "9432", "name": "NTT", "action": "HOLD", "position_score": 0.66, "data_until": "2026-06-16", "decision_for": "2026-06-16", "reason": "hold"}]},
        "allocation_artifact.json": {"decisions": [{"code": "7203", "action": "BUY", "quantity": 100, "buy_amount": 100000, "expected_edge_score": 0.81, "reason": "allocation"}]},
        "order_plan_artifact.json": {"plan_id": "order_plan_mock", "executable": False, "live_order_allowed": False, "requires_human_review": True, "items": [{"issue_code": "6758", "issue_name": "Sony Group", "side": "SELL", "quantity": 100, "estimated_value": 120000, "reason_code": "order_plan"}]},
    }
    for filename, payload in payloads.items():
        (root / filename).write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-D AI artifact integration.")
    parser.add_argument("--output-root", default="/private/tmp/phase9d_audit")
    args = parser.parse_args(argv)
    summary = run_audit(output_root=Path(args.output_root))
    print(json.dumps({"phase": summary["phase"], "status": summary["status"], "checks": summary["checks"]}, ensure_ascii=True, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

