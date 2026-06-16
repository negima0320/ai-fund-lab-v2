from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.paper_trading.daily_inference_runner import INFERENCE_READY, run_daily_inference
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction


DOC_PATH = ROOT / "docs" / "phase_reports" / "phase9l2_daily_inference_integration_audit.md"
JSON_PATH = ROOT / "reports" / "phase_reports" / "phase9l2_daily_inference_integration_audit.json"


def main() -> int:
    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        allow_initial_ledger=True,
    )
    payload = result.to_dict()
    checks = {
        "daily_inference_ready": result.status == INFERENCE_READY,
        "candidate_artifact_created": Path(result.artifact_paths.get("candidate", "")).is_file(),
        "opportunity_artifact_created": Path(result.artifact_paths.get("opportunity", "")).is_file(),
        "position_artifact_created": Path(result.artifact_paths.get("position", "")).is_file(),
        "allocation_artifact_created": Path(result.artifact_paths.get("allocation", "")).is_file(),
        "order_plan_artifact_created": Path(result.artifact_paths.get("order_plan", "")).is_file(),
        "internal_report_created": Path(result.report_paths.get("internal_markdown", "")).is_file(),
        "public_report_created": Path(result.report_paths.get("public_markdown", "")).is_file(),
        "blog_draft_created": Path(result.report_paths.get("blog_draft", "")).is_file(),
        "prohibited_flags_false": not any(bool(value) for value in (result.prohibited_flags or {}).values()),
    }
    order_payload = json.loads(Path(result.artifact_paths.get("order_plan", "")).read_text(encoding="utf-8")) if checks["order_plan_artifact_created"] else {}
    checks.update(
        {
            "order_plan_executable_false": order_payload.get("executable") is False,
            "order_plan_live_order_allowed_false": order_payload.get("live_order_allowed") is False,
            "order_plan_requires_human_review_true": order_payload.get("requires_human_review") is True,
        }
    )
    public_path = Path(result.report_paths.get("public_markdown", ""))
    blog_path = Path(result.report_paths.get("blog_draft", ""))
    public_ready = check_public_report_redaction(public_path.read_text(encoding="utf-8")).ready if public_path.is_file() else False
    blog_ready = check_public_report_redaction(blog_path.read_text(encoding="utf-8")).ready if blog_path.is_file() else False
    checks["public_report_redaction_ready"] = public_ready
    checks["blog_draft_redaction_ready"] = blog_ready
    status = "PASS" if all(checks.values()) else "FAIL"
    payload["audit_status"] = status
    payload["checks"] = checks

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps({"audit_status": status, "json": str(JSON_PATH), "markdown": str(DOC_PATH)}, ensure_ascii=True, sort_keys=True))
    return 0 if status == "PASS" else 1


def _render_markdown(payload: dict[str, object]) -> str:
    checks = payload.get("checks", {})
    lines = [
        "# Phase9-L2 Daily Inference Integration Audit",
        "",
        f"- status: {payload.get('audit_status')}",
        f"- decision_for: {payload.get('decision_for')}",
        f"- data_until: {payload.get('data_until')}",
        f"- runtime_status: {payload.get('status')}",
        "",
        "## Checks",
        "",
    ]
    if isinstance(checks, dict):
        for key, value in sorted(checks.items()):
            lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(
        [
            "",
            "## Phase9 Boundary",
            "",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "- virtual_fill_executed: false",
            "- model_retraining_executed: false",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

