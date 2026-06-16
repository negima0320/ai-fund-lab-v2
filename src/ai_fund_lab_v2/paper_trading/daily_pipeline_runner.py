from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import READY as ARTIFACT_READY
from ai_fund_lab_v2.paper_trading.ai_artifact_adapter import AIArtifactIntegrationResult, AIArtifactPaths, adapt_ai_artifacts
from ai_fund_lab_v2.paper_trading.business_date_resolver import BusinessDateResolution, resolve_business_dates
from ai_fund_lab_v2.paper_trading.daily_run_result import DailyCandidate, DailyRunResult
from ai_fund_lab_v2.paper_trading.ledger import load_latest_ledger, load_ledger
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_ledger_to_daily_result
from ai_fund_lab_v2.paper_trading.mandatory_step_tracker import MandatoryStepTracker
from ai_fund_lab_v2.paper_trading.market_data_readiness import READY, MarketDataReadinessResult, check_market_data_readiness
from ai_fund_lab_v2.paper_trading.model_eligibility import ModelEligibilityResult, check_model_eligibility
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest, write_daily_run_manifest


@dataclass(frozen=True)
class DailyPipelineRunResult:
    status: str
    manifest: DailyRunManifest
    daily_result: DailyRunResult
    dates: BusinessDateResolution
    market_data: MarketDataReadinessResult
    model_eligibility: ModelEligibilityResult
    step_tracker: MandatoryStepTracker
    manifest_path: str
    internal_report_md_path: str
    internal_report_json_path: str
    public_report_path: str
    blog_draft_path: str
    artifact_integration: AIArtifactIntegrationResult | None = None
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    paper_ledger_fill_executed: bool = False
    live_order_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["manifest"] = self.manifest.to_dict()
        payload["daily_result"] = self.daily_result.to_dict()
        payload["dates"] = self.dates.to_dict()
        payload["market_data"] = self.market_data.to_dict()
        payload["model_eligibility"] = self.model_eligibility.to_dict()
        payload["step_tracker"] = self.step_tracker.to_dict()
        payload["artifact_integration"] = self.artifact_integration.to_dict() if self.artifact_integration else None
        return payload


def run_daily_pipeline(
    *,
    run_date: str | None = None,
    runtime_dir: Path | str = ".runtime",
    reports_root: Path | str = "reports",
    daily_quotes_path: Path | None = None,
    listed_info_path: Path | None = None,
    model_manifest: Mapping[str, Any] | None = None,
    artifact_root: Path | None = None,
    candidate_artifact: Path | None = None,
    opportunity_artifact: Path | None = None,
    position_artifact: Path | None = None,
    allocation_artifact: Path | None = None,
    order_plan_artifact: Path | None = None,
    use_artifacts: bool = False,
    ledger_path: Path | None = None,
) -> DailyPipelineRunResult:
    dates = resolve_business_dates(run_date=run_date, runtime_dir=runtime_dir)
    tracker = MandatoryStepTracker()
    tracker = tracker.update("safety_check", status="OK", reason="phase9c_no_live_order_boundary")
    market = check_market_data_readiness(
        decision_for=dates.decision_for,
        runtime_dir=runtime_dir,
        daily_quotes_path=daily_quotes_path,
        listed_info_path=listed_info_path,
    )
    tracker = tracker.update(
        "data_update",
        status="OK" if market.status == READY else "BLOCKED",
        reason=market.status,
    )
    default_model_manifest = {
        "model_version": "phase9c_mock_model_v1",
        "train_until": dates.decision_for,
        "data_until": min(market.data_until or dates.decision_for, dates.decision_for),
        "feature_schema_hash": "phase9c_mock_feature_schema_hash",
        "leakage_audit_status": "OK",
        "training_sources": ["J-Quants"],
    }
    model = check_model_eligibility(model_manifest or default_model_manifest, decision_for=dates.decision_for)
    artifact_paths = _resolve_artifact_paths(
        artifact_root=artifact_root,
        candidate_artifact=candidate_artifact,
        opportunity_artifact=opportunity_artifact,
        position_artifact=position_artifact,
        allocation_artifact=allocation_artifact,
        order_plan_artifact=order_plan_artifact,
    )
    artifact_requested = use_artifacts or any(
        path is not None
        for path in (
            artifact_paths.candidate_artifact,
            artifact_paths.opportunity_artifact,
            artifact_paths.position_artifact,
            artifact_paths.allocation_artifact,
            artifact_paths.order_plan_artifact,
        )
    )
    artifact_integration: AIArtifactIntegrationResult | None = None
    if market.status == READY and model.eligible and artifact_requested:
        artifact_integration = adapt_ai_artifacts(
            decision_for=dates.decision_for,
            data_until=market.data_until or dates.data_until,
            paths=artifact_paths,
        )
    if market.status == READY and model.eligible and (not artifact_requested or (artifact_integration and artifact_integration.status == ARTIFACT_READY)):
        tracker = tracker.update("feature_generation", status="OK", reason="phase9c_skeleton")
        tracker = tracker.update("inference", status="OK", reason="phase9d_artifact_inference" if artifact_requested else "phase9c_mock_inference")
        status = "OK"
        safety_status = "OK"
        human_review_status = "pending"
        report_status = "OK"
        daily_result = (
            _with_state(artifact_integration.daily_result, safety_status=safety_status, review_status=human_review_status)
            if artifact_integration
            else _mock_daily_result(safety_status=safety_status, review_status=human_review_status)
        )
    else:
        tracker = tracker.update("feature_generation", status="BLOCKED", reason="market_or_model_not_ready")
        tracker = tracker.update("inference", status="SKIPPED", reason="fail_closed")
        status = "HALT"
        safety_status = "INVALID_INPUT" if market.status == "INVALID" or not model.eligible or (artifact_integration and artifact_integration.status == "INVALID") else "NOT_READY"
        human_review_status = "review_only"
        report_status = "HALT_REPORT"
        daily_result = (
            _with_state(artifact_integration.daily_result, safety_status=safety_status, review_status=human_review_status)
            if artifact_integration
            else _halt_daily_result(
                market=market,
                model=model,
                safety_status=safety_status,
                review_status=human_review_status,
            )
        )
    ledger = load_ledger(ledger_path) if ledger_path is not None else load_latest_ledger(runtime_dir)
    if ledger is not None:
        daily_result = apply_ledger_to_daily_result(daily_result, ledger)
    manifest = DailyRunManifest(
        run_date=dates.run_date,
        data_until=market.data_until or dates.data_until,
        train_until=str((model_manifest or default_model_manifest).get("train_until") or dates.decision_for),
        decision_for=dates.decision_for,
        virtual_order_date=dates.virtual_order_date,
        virtual_execution_date=dates.virtual_execution_date,
        safety_status=safety_status,
        human_review_status=human_review_status,
        report_status=report_status,
        warnings=market.warnings + model.warnings + (artifact_integration.warnings if artifact_integration else ()),
        blocked_reasons=market.blocked_reasons + model.blocked_reasons + (artifact_integration.blocked_reasons if artifact_integration else ()),
    )
    manifest_path = write_daily_run_manifest(manifest, runtime_dir)
    reports = Path(reports_root)
    internal_md, internal_json = write_internal_daily_report(manifest=manifest, result=daily_result, reports_dir=reports / "phase9" / "daily")
    public_md = write_public_daily_report(manifest=manifest, result=daily_result, reports_dir=reports / "public" / "phase9_daily")
    blog_md = write_blog_draft(manifest=manifest, result=daily_result, reports_dir=reports / "public" / "phase9_daily")
    tracker = tracker.update(
        "report_generation",
        status="OK",
        reason="reports_generated",
        artifact_refs=(str(internal_md), str(internal_json), str(public_md), str(blog_md)),
    )
    tracker = tracker.update("human_review", status="PENDING" if status == "OK" else "SKIPPED", reason=human_review_status)
    return DailyPipelineRunResult(
        status=status,
        manifest=manifest,
        daily_result=daily_result,
        dates=dates,
        market_data=market,
        model_eligibility=model,
        step_tracker=tracker,
        manifest_path=str(manifest_path),
        internal_report_md_path=str(internal_md),
        internal_report_json_path=str(internal_json),
        public_report_path=str(public_md),
        blog_draft_path=str(blog_md),
        artifact_integration=artifact_integration,
    )


def _mock_daily_result(*, safety_status: str, review_status: str) -> DailyRunResult:
    return DailyRunResult(
        buy_candidates=(
            DailyCandidate(
                issue_code="7203",
                issue_name="Toyota Motor",
                side="BUY",
                public_confidence_score=64,
                short_reason="Phase9-C mock inference candidate.",
                caution_note="仮想運用での検証中です。",
            ),
        ),
        sell_candidates=(),
        hold_candidates=(),
        cash=Decimal("1000000"),
        total_equity=Decimal("1000000"),
        safety_state={"status": safety_status},
        review_state={"status": review_status},
    )


def _halt_daily_result(
    *,
    market: MarketDataReadinessResult,
    model: ModelEligibilityResult,
    safety_status: str,
    review_status: str,
) -> DailyRunResult:
    reasons = list(market.blocked_reasons) + list(model.blocked_reasons)
    return DailyRunResult(
        buy_candidates=(),
        sell_candidates=(),
        hold_candidates=(
            DailyCandidate(
                issue_code="",
                side="HOLD",
                public_confidence_score=25,
                short_reason="入力不足のため日次判断は停止しました。",
                caution_note="fail closedにより仮想注文は作成していません。",
                reason="|".join(reasons),
            ),
        ),
        cash=Decimal("0"),
        total_equity=Decimal("0"),
        safety_state={"status": safety_status, "blocked_reasons": reasons},
        review_state={"status": review_status},
    )


def _with_state(result: DailyRunResult, *, safety_status: str, review_status: str) -> DailyRunResult:
    return DailyRunResult(
        buy_candidates=result.buy_candidates,
        sell_candidates=result.sell_candidates,
        hold_candidates=result.hold_candidates,
        cash=result.cash,
        positions=result.positions,
        total_equity=result.total_equity,
        realized_pnl=result.realized_pnl,
        unrealized_pnl=result.unrealized_pnl,
        trade_count=result.trade_count,
        safety_state={**result.safety_state, "status": safety_status},
        review_state={**result.review_state, "status": review_status},
        artifact_state=result.artifact_state,
        execution_state=result.execution_state,
    )


def _resolve_artifact_paths(
    *,
    artifact_root: Path | None,
    candidate_artifact: Path | None,
    opportunity_artifact: Path | None,
    position_artifact: Path | None,
    allocation_artifact: Path | None,
    order_plan_artifact: Path | None,
) -> AIArtifactPaths:
    root = Path(artifact_root) if artifact_root else None
    return AIArtifactPaths(
        candidate_artifact=candidate_artifact or _root_path(root, "candidate_artifact.json"),
        opportunity_artifact=opportunity_artifact or _root_path(root, "opportunity_artifact.json"),
        position_artifact=position_artifact or _root_path(root, "position_artifact.json"),
        allocation_artifact=allocation_artifact or _root_path(root, "allocation_artifact.json"),
        order_plan_artifact=order_plan_artifact or _root_path(root, "order_plan_artifact.json"),
    )


def _root_path(root: Path | None, filename: str) -> Path | None:
    return root / filename if root is not None else None
