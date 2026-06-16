from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.daily_pipeline_runner import DailyPipelineRunResult, run_daily_pipeline
from ai_fund_lab_v2.paper_trading.ledger_integration import apply_virtual_fill_to_daily_result
from ai_fund_lab_v2.paper_trading.operation_log import OperationLog, build_operation_log, write_operation_log
from ai_fund_lab_v2.paper_trading.reporting.blog_draft_writer import write_blog_draft
from ai_fund_lab_v2.paper_trading.reporting.internal_daily_report_writer import write_internal_daily_report
from ai_fund_lab_v2.paper_trading.reporting.public_daily_report_writer import write_public_daily_report
from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock, release_run_lock
from ai_fund_lab_v2.paper_trading.run_manifest import DailyRunManifest
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import VirtualFillResult, process_virtual_fills_from_files


OPERATION_MODES = {"dry-run", "paper-trading", "report-only", "fill-only"}


@dataclass(frozen=True)
class DailyOperationResult:
    status: str
    mode: str
    run_id: str
    operation_log_json_path: str
    operation_log_md_path: str
    pipeline_result: DailyPipelineRunResult | None = None
    fill_result: VirtualFillResult | None = None
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    live_order_allowed: bool = False
    scheduler_auto_registered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "mode": self.mode,
            "run_id": self.run_id,
            "operation_log_json_path": self.operation_log_json_path,
            "operation_log_md_path": self.operation_log_md_path,
            "pipeline_result": self.pipeline_result.to_dict() if self.pipeline_result else None,
            "fill_result": self.fill_result.to_dict() if self.fill_result else None,
            "broker_order_api_called": self.broker_order_api_called,
            "open_d_started": self.open_d_started,
            "unlock_trade_called": self.unlock_trade_called,
            "live_order_allowed": self.live_order_allowed,
            "scheduler_auto_registered": self.scheduler_auto_registered,
        }


def run_daily_operation(
    *,
    run_date: str,
    mode: str = "dry-run",
    operation_root: Path | str = ".runtime/phase9",
    runtime_dir: Path | str = ".runtime",
    reports_root: Path | str = "reports",
    ledger_path: Path | None = None,
    artifact_root: Path | None = None,
    quotes_path: Path | None = None,
    listed_info_path: Path | None = None,
    daily_quotes_path: Path | None = None,
    force_unlock: bool = False,
) -> DailyOperationResult:
    if mode not in OPERATION_MODES:
        raise ValueError(f"Unsupported Phase9 daily operation mode: {mode}")
    run_id = f"phase9_operation_{run_date}_{utc_now_iso().replace(':', '').replace('+', 'Z')}"
    started_at = utc_now_iso()
    lock = acquire_run_lock(run_id=run_id, run_date=run_date, mode=mode, operation_root=operation_root, force_unlock=force_unlock)
    pipeline: DailyPipelineRunResult | None = None
    fill: VirtualFillResult | None = None
    status = "OK"
    try:
        if mode in {"dry-run", "paper-trading", "report-only"}:
            pipeline = run_daily_pipeline(
                run_date=run_date,
                runtime_dir=runtime_dir,
                reports_root=reports_root,
                daily_quotes_path=daily_quotes_path or quotes_path,
                listed_info_path=listed_info_path,
                artifact_root=artifact_root,
                use_artifacts=artifact_root is not None,
                ledger_path=ledger_path,
            )
            status = pipeline.status
        if mode in {"paper-trading", "fill-only"} and ledger_path is not None and quotes_path is not None:
            fill = process_virtual_fills_from_files(
                ledger_path=ledger_path,
                quotes_path=quotes_path,
                execution_date=run_date,
                runtime_dir=runtime_dir,
                output_root=operation_root,
                dry_run=False,
            )
            if pipeline is not None:
                daily_result = apply_virtual_fill_to_daily_result(pipeline.daily_result, fill)
                internal_md, internal_json = write_internal_daily_report(
                    manifest=pipeline.manifest,
                    result=daily_result,
                    reports_dir=Path(reports_root) / "phase9" / "daily",
                )
                public_md = write_public_daily_report(
                    manifest=pipeline.manifest,
                    result=daily_result,
                    reports_dir=Path(reports_root) / "public" / "phase9_daily",
                )
                blog_md = write_blog_draft(
                    manifest=pipeline.manifest,
                    result=daily_result,
                    reports_dir=Path(reports_root) / "public" / "phase9_daily",
                )
        if mode == "dry-run" and ledger_path is not None and quotes_path is not None:
            fill = process_virtual_fills_from_files(
                ledger_path=ledger_path,
                quotes_path=quotes_path,
                execution_date=run_date,
                runtime_dir=runtime_dir,
                output_root=operation_root,
                dry_run=True,
            )
        if mode == "fill-only" and fill is None:
            status = "BLOCKED"
        log = _build_log(
            run_id=run_id,
            run_date=run_date,
            mode=mode,
            started_at=started_at,
            status=status,
            pipeline=pipeline,
            fill=fill,
        )
        log_json, log_md = write_operation_log(log, operation_root)
        return DailyOperationResult(
            status=status,
            mode=mode,
            run_id=run_id,
            operation_log_json_path=str(log_json),
            operation_log_md_path=str(log_md),
            pipeline_result=pipeline,
            fill_result=fill,
        )
    except Exception:
        status = "FAILED"
        log = _build_log(run_id=run_id, run_date=run_date, mode=mode, started_at=started_at, status=status, pipeline=pipeline, fill=fill)
        log_json, log_md = write_operation_log(log, operation_root)
        raise
    finally:
        release_run_lock(run_id=lock.run_id, operation_root=operation_root)


def _build_log(
    *,
    run_id: str,
    run_date: str,
    mode: str,
    started_at: str,
    status: str,
    pipeline: DailyPipelineRunResult | None,
    fill: VirtualFillResult | None,
) -> OperationLog:
    report_refs: dict[str, str] = {}
    ledger_refs: dict[str, str] = {}
    artifact_refs: dict[str, str] = {}
    step_statuses: dict[str, Any] = {}
    warnings: tuple[str, ...] = ()
    blocked: tuple[str, ...] = ()
    if pipeline:
        report_refs.update(
            {
                "internal_report_md": pipeline.internal_report_md_path,
                "internal_report_json": pipeline.internal_report_json_path,
                "public_report": pipeline.public_report_path,
                "blog_draft": pipeline.blog_draft_path,
                "manifest": pipeline.manifest_path,
            }
        )
        step_statuses = pipeline.step_tracker.to_dict()
        warnings = pipeline.manifest.warnings
        blocked = pipeline.manifest.blocked_reasons
        if pipeline.artifact_integration:
            artifact_refs["artifact_integration_status"] = pipeline.artifact_integration.status
    if fill:
        ledger_refs.update(
            {
                "ledger_before": fill.ledger_before_path,
                "ledger_after": fill.ledger_after_path,
                "ledger_diff": fill.ledger_diff_path,
            }
        )
        for index, path in enumerate(fill.execution_paths):
            ledger_refs[f"execution_{index}"] = path
    return build_operation_log(
        run_id=run_id,
        date=run_date,
        mode=mode,
        started_at=started_at,
        status=status,
        step_statuses=step_statuses,
        artifact_refs=artifact_refs,
        ledger_refs=ledger_refs,
        report_refs=report_refs,
        warnings=warnings,
        blocked_reasons=blocked,
    )

