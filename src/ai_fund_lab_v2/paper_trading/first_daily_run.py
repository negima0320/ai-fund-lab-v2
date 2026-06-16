from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_FOR_PAPER_TRADING, MANUAL_REQUIRED, REVIEW_ONLY
from ai_fund_lab_v2.paper_trading.auto_approval import create_auto_approval_artifact
from ai_fund_lab_v2.paper_trading.daily_inference_runner import run_daily_inference
from ai_fund_lab_v2.paper_trading.human_review_artifact import create_human_review_request
from ai_fund_lab_v2.paper_trading.pending_order_creator import (
    PENDING_ORDERS_SKIPPED,
    PendingOrderCreationResult,
    create_pending_orders_from_approved_review,
)


FIRST_RUN_READY_FOR_REVIEW = "FIRST_RUN_READY_FOR_REVIEW"
FIRST_RUN_PENDING_ORDERS_CREATED = "FIRST_RUN_PENDING_ORDERS_CREATED"
FIRST_RUN_BLOCKED = "FIRST_RUN_BLOCKED"
FIRST_RUN_MODES = {"review-only", "paper-trading"}


@dataclass(frozen=True)
class FirstDailyRunResult:
    status: str
    mode: str
    decision_for: str
    data_until: str
    virtual_order_date: str
    inference_status: str
    candidate_count: int
    opportunity_count: int
    allocation_count: int
    order_plan_count: int
    human_review_json_path: str
    human_review_markdown_path: str
    review_status: str
    pending_order_created: bool
    pending_order_count: int
    ledger_changed: bool
    manifest_path: str
    tracker_marker_path: str
    report_paths: dict[str, str]
    approval_mode: str = REVIEW_ONLY
    auto_approval_json_path: str = ""
    auto_approval_markdown_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["prohibited_flags"] = self.prohibited_flags or prohibited_flags()
        return payload


def run_first_daily_paper_trading_run(
    *,
    decision_for: str,
    data_until: str,
    ledger_path: Path | str,
    mode: str = "review-only",
    runtime_dir: Path | str = ".runtime",
    reports_root: Path | str = "reports",
    feature_root: Path | str = ".runtime/phase9/features",
    canonical_quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    human_review_path: Path | str | None = None,
    approval_mode: str = AUTO_FOR_PAPER_TRADING,
) -> FirstDailyRunResult:
    if mode not in FIRST_RUN_MODES:
        raise ValueError(f"Unsupported first daily run mode: {mode}")
    ledger_file = Path(ledger_path)
    before_hash = _file_hash(ledger_file)
    inference = run_daily_inference(
        decision_for=decision_for,
        data_until=data_until,
        runtime_dir=runtime_dir,
        reports_root=reports_root,
        feature_root=feature_root,
        canonical_quotes_path=canonical_quotes_path,
        ledger_path=ledger_file,
    )
    order_plan_path = Path(inference.artifact_paths.get("order_plan", ""))
    virtual_order_date = _read_order_plan_date(order_plan_path, fallback=_next_business_day(decision_for))
    review_request = create_human_review_request(
        order_plan_path=order_plan_path,
        decision_for=decision_for,
        virtual_order_date=virtual_order_date,
        output_root=Path(runtime_dir) / "phase9" / "human_review",
        safety_status="READY_FOR_REVIEW",
    )
    pending_result = PendingOrderCreationResult(
        status=PENDING_ORDERS_SKIPPED,
        review_status="pending",
        pending_order_created=False,
        pending_order_count=0,
        ledger_path=str(ledger_file),
        latest_path=str(ledger_file),
        warnings=("review_only_no_pending_order",),
        prohibited_flags=prohibited_flags(),
    )
    auto_approval_json_path = ""
    auto_approval_markdown_path = ""
    active_review_path = Path(human_review_path) if human_review_path else Path(review_request.json_path)
    if mode == "paper-trading":
        if approval_mode == AUTO_FOR_PAPER_TRADING and human_review_path is None:
            auto_approval = create_auto_approval_artifact(
                order_plan_path=order_plan_path,
                decision_for=decision_for,
                virtual_order_date=virtual_order_date,
                output_root=Path(runtime_dir) / "phase9" / "auto_approval",
                approval_mode=approval_mode,
                execution_mode="paper-trading",
            )
            auto_approval_json_path = auto_approval.json_path
            auto_approval_markdown_path = auto_approval.markdown_path
            if auto_approval.json_path:
                active_review_path = Path(auto_approval.json_path)
        elif approval_mode == REVIEW_ONLY:
            active_review_path = Path(review_request.json_path)
        elif approval_mode == MANUAL_REQUIRED and human_review_path is None:
            active_review_path = Path(review_request.json_path)
        pending_result = create_pending_orders_from_approved_review(
            ledger_path=ledger_file,
            order_plan_path=order_plan_path,
            human_review_path=active_review_path,
            runtime_dir=runtime_dir,
        )
    after_hash = _file_hash(ledger_file)
    counts = _artifact_counts(inference.artifact_paths)
    status = FIRST_RUN_BLOCKED if inference.status != "INFERENCE_READY" else FIRST_RUN_READY_FOR_REVIEW
    if pending_result.pending_order_created:
        status = FIRST_RUN_PENDING_ORDERS_CREATED
    manifest_dir = Path(runtime_dir) / "phase9" / "first_daily_runs" / decision_for
    manifest_path = manifest_dir / "first_daily_run_manifest.json"
    tracker_path = Path(runtime_dir) / "phase9" / "tracker" / "pending_first_run_marker.json"
    result = FirstDailyRunResult(
        status=status,
        mode=mode,
        decision_for=decision_for,
        data_until=data_until,
        virtual_order_date=virtual_order_date,
        inference_status=inference.status,
        candidate_count=counts["candidate"],
        opportunity_count=counts["opportunity"],
        allocation_count=counts["allocation"],
        order_plan_count=counts["order_plan"],
        human_review_json_path=review_request.json_path,
        human_review_markdown_path=review_request.markdown_path,
        review_status=pending_result.review_status,
        pending_order_created=pending_result.pending_order_created,
        pending_order_count=pending_result.pending_order_count,
        ledger_changed=before_hash != after_hash,
        manifest_path=str(manifest_path),
        tracker_marker_path=str(tracker_path),
        report_paths=inference.report_paths,
        approval_mode=approval_mode if mode == "paper-trading" else REVIEW_ONLY,
        auto_approval_json_path=auto_approval_json_path,
        auto_approval_markdown_path=auto_approval_markdown_path,
        warnings=tuple(list(inference.warnings) + list(pending_result.warnings)),
        blocked_reasons=tuple(list(inference.blocked_reasons) + list(pending_result.blocked_reasons)),
        prohibited_flags=prohibited_flags(),
    )
    _write_json(manifest_path, _manifest_payload(result, inference_manifest_path=inference.manifest_path))
    _write_json(
        tracker_path,
        {
            "decision_for": decision_for,
            "run_status": result.status,
            "review_status": result.review_status,
            "pending_order_created": result.pending_order_created,
            "report_refs": result.report_paths,
            "created_at": utc_now_iso(),
        },
    )
    return result


def prohibited_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "paper_ledger_fill_executed": False,
        "virtual_fill_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _artifact_counts(paths: dict[str, str]) -> dict[str, int]:
    counts = {"candidate": 0, "opportunity": 0, "allocation": 0, "order_plan": 0}
    for key in ("candidate", "opportunity", "allocation"):
        path = Path(paths.get(key, ""))
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            counts[key] = int(payload.get("row_count") or len(payload.get("rows", [])))
    order_path = Path(paths.get("order_plan", ""))
    if order_path.is_file():
        payload = json.loads(order_path.read_text(encoding="utf-8"))
        counts["order_plan"] = len(payload.get("items", []))
    return counts


def _read_order_plan_date(path: Path, *, fallback: str) -> str:
    if not path.is_file():
        return fallback
    payload = json.loads(path.read_text(encoding="utf-8"))
    return str(payload.get("virtual_order_date") or payload.get("virtual_execution_date") or fallback)


def _manifest_payload(result: FirstDailyRunResult, *, inference_manifest_path: str) -> dict[str, Any]:
    payload = result.to_dict()
    payload.update(
        {
            "first_daily_run": True,
            "pending_order_created": result.pending_order_created,
            "pending_order_count": result.pending_order_count,
            "virtual_fill_executed": False,
            "broker_order_api_called": False,
            "open_d_started": False,
            "unlock_trade_called": False,
            "inference_manifest_path": inference_manifest_path,
            "created_at": utc_now_iso(),
        }
    )
    return payload


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    return __import__("hashlib").sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _next_business_day(value: str) -> str:
    from datetime import date, timedelta

    current = date.fromisoformat(value) + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()
