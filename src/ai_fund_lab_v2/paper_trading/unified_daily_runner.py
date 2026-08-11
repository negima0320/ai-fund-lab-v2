from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import pandas as pd

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.approval_mode import AUTO_FOR_PAPER_TRADING, validate_approval_mode
from ai_fund_lab_v2.paper_trading.business_day_tracker import update_business_day_tracker
from ai_fund_lab_v2.paper_trading.daily_continuation import run_daily_continuation
from ai_fund_lab_v2.paper_trading.daily_inference_runner import run_daily_inference
from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh
from ai_fund_lab_v2.paper_trading.first_daily_run import run_first_daily_paper_trading_run
from ai_fund_lab_v2.paper_trading.first_virtual_fill import run_first_virtual_fill
from ai_fund_lab_v2.paper_trading.first_virtual_fill import FirstVirtualFillRunResult
from ai_fund_lab_v2.paper_trading.ledger import load_ledger
from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh
from ai_fund_lab_v2.paper_trading.notifications.daily_notification_runner import run_daily_notifications
from ai_fund_lab_v2.paper_trading.operation_log import build_operation_log, write_operation_log
from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import write_blog_report_v2
from ai_fund_lab_v2.paper_trading.run_lock import RunLockError, acquire_run_lock, release_run_lock


UNIFIED_DAILY_RUNNER_COMPLETED = "UNIFIED_DAILY_RUNNER_COMPLETED"
UNIFIED_DAILY_RUNNER_BLOCKED = "UNIFIED_DAILY_RUNNER_BLOCKED"
UNIFIED_MODES = {"dry-run", "paper-trading", "report-only", "fill-only"}


@dataclass(frozen=True)
class BusinessDates:
    run_date: str
    business_date: str
    market_data_target_date: str
    data_target_date: str
    decision_for: str
    valuation_date: str
    latest_available_quote_date: str
    virtual_order_date: str
    virtual_execution_date: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class UnifiedDailyRunResult:
    status: str
    run_id: str
    mode: str
    approval_mode: str
    business_dates: BusinessDates
    step_statuses: dict[str, Any]
    manifest_path: str
    operation_log_json_path: str
    operation_log_markdown_path: str
    report_markdown_path: str
    report_json_path: str
    blog_report_v2_markdown_path: str = ""
    blog_report_v2_json_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    live_order_allowed: bool = False
    scheduler_auto_registered: bool = False
    model_retraining_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["business_dates"] = self.business_dates.to_dict()
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def run_unified_daily_paper_trading(
    *,
    run_date: str,
    ledger_path: Path | str = ".runtime/phase9/ledger/latest.json",
    mode: str = "dry-run",
    approval_mode: str = AUTO_FOR_PAPER_TRADING,
    allow_api_fetch: bool = False,
    skip_market_data_refresh: bool = False,
    skip_feature_refresh: bool = False,
    skip_inference: bool = False,
    skip_virtual_fill: bool = False,
    skip_tracker_update: bool = False,
    skip_blog_report_v2: bool = False,
    skip_notifications: bool = False,
    force_unlock: bool = False,
    runtime_dir: Path | str = ".runtime",
    operation_root: Path | str = ".runtime/daily_operation",
    quotes_path: Path | str = ".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet",
    feature_root: Path | str = ".runtime/phase9/features",
    reports_root: Path | str = "reports",
    phase_report_markdown_path: Path | str = "docs/phase_reports/phase9u_unified_daily_paper_trading_runner.md",
    phase_report_json_path: Path | str = "reports/phase_reports/phase9u_unified_daily_paper_trading_runner.json",
    market_data_refresh_runner: Callable[..., Any] | None = None,
    notification_runner: Callable[..., Any] | None = None,
) -> UnifiedDailyRunResult:
    if mode not in UNIFIED_MODES:
        raise ValueError(f"Unsupported unified daily mode: {mode}")
    approval = validate_approval_mode(approval_mode=approval_mode, execution_mode=mode)
    if approval_mode == AUTO_FOR_PAPER_TRADING and mode != "paper-trading":
        approval_mode = "review_only"
        approval = validate_approval_mode(approval_mode=approval_mode, execution_mode=mode)
    if not approval.allowed:
        raise ValueError(",".join(approval.blocked_reasons))
    run_id = f"aifundlab_daily_{run_date}_{uuid4().hex}"
    started_at = utc_now_iso()
    lock = acquire_run_lock(run_id=run_id, run_date=run_date, mode=mode, operation_root=operation_root, force_unlock=force_unlock)
    step_statuses: dict[str, Any] = {"run_lock": "ACQUIRED"}
    warnings: list[str] = []
    blocked: list[str] = []
    report_refs: dict[str, str] = {}
    ledger_refs: dict[str, str] = {"ledger_path": str(ledger_path)}
    artifact_refs: dict[str, str] = {}
    blog_md = ""
    blog_json = ""
    status = UNIFIED_DAILY_RUNNER_COMPLETED
    try:
        dates = resolve_business_dates(run_date=run_date, quotes_path=quotes_path)
        step_statuses["business_date_resolve"] = dates.to_dict()

        if skip_market_data_refresh:
            step_statuses["market_data_refresh"] = "SKIPPED_BY_FLAG"
        elif allow_api_fetch:
            refresh_runner = market_data_refresh_runner or run_market_data_refresh
            refresh = refresh_runner(
                from_date=dates.market_data_target_date,
                to_date=dates.market_data_target_date,
                dry_run=False,
                allow_api_fetch=True,
                backup_existing=True,
                fetch_mode="per-date",
            )
            step_statuses["market_data_refresh"] = _refresh_attr(refresh, "status", "UNKNOWN")
            step_statuses["market_data_refresh_context"] = {
                "requested_from_date": _refresh_attr(refresh, "requested_from_date", dates.market_data_target_date),
                "requested_to_date": _refresh_attr(refresh, "requested_to_date", dates.market_data_target_date),
                "data_until": _refresh_attr(refresh, "data_until", ""),
                "latest_successful_daily_quotes_date": _refresh_attr(refresh, "latest_successful_daily_quotes_date", ""),
                "latest_normalized_daily_quotes_date": _refresh_attr(refresh, "latest_normalized_daily_quotes_date", ""),
                "jquants_api_fetch_executed": _refresh_attr(refresh, "jquants_api_fetch_executed", False),
            }
            warnings.extend(_refresh_sequence(refresh, "warnings"))
            blocked.extend(_refresh_sequence(refresh, "blocked_reasons"))
            canonical_status, canonical_blocked = _sync_refreshed_daily_quotes_to_canonical(
                refresh=refresh,
                quotes_path=Path(quotes_path),
                target_date=dates.market_data_target_date,
            )
            step_statuses["canonical_normalized_update"] = canonical_status
            blocked.extend(canonical_blocked)
            dates = resolve_business_dates(run_date=run_date, quotes_path=quotes_path)
            step_statuses["business_date_resolve_after_market_refresh"] = dates.to_dict()
            if dates.latest_available_quote_date < dates.market_data_target_date:
                blocked.append(f"market_data_not_ready_for_run_date:{dates.latest_available_quote_date}<target:{dates.market_data_target_date}")
        else:
            step_statuses["market_data_refresh"] = "SKIPPED_API_FETCH_NOT_ALLOWED"

        if "canonical_normalized_update" not in step_statuses:
            step_statuses["canonical_normalized_update"] = "USING_EXISTING_CANONICAL_NORMALIZED"

        if skip_feature_refresh:
            step_statuses["feature_refresh"] = "SKIPPED_BY_FLAG"
        else:
            feature_audit = run_feature_refresh(
                target_data_until=dates.data_target_date,
                dry_run=True,
                execute=False,
                daily_quotes_path=quotes_path,
                feature_output_root=feature_root,
            )
            feature = feature_audit
            step_statuses["feature_refresh_audit"] = feature_audit.status
            if feature_audit.status != "FEATURES_READY":
                feature = run_feature_refresh(
                    target_data_until=dates.data_target_date,
                    dry_run=False,
                    execute=True,
                    daily_quotes_path=quotes_path,
                    feature_output_root=feature_root,
                )
                step_statuses["feature_refresh_execute"] = feature.status
            step_statuses["feature_refresh"] = feature.status
            artifact_refs["feature_refresh_manifest"] = feature.manifest_path
            warnings.extend(feature.warnings)
            if feature.status != "FEATURES_READY":
                blocked.append(f"feature_refresh_not_ready:{feature.status}")
            if feature.blocked_reasons:
                blocked.extend(feature.blocked_reasons)

        fill_results: list[FirstVirtualFillRunResult] = []
        if skip_virtual_fill:
            step_statuses["virtual_fill"] = "SKIPPED_BY_FLAG"
        elif mode in {"paper-trading", "fill-only", "dry-run"}:
            due_execution_dates = _due_pending_execution_dates(ledger_path=ledger_path, run_date=run_date)
            if due_execution_dates:
                fill_results = _run_due_virtual_fills(
                    ledger_path=ledger_path,
                    quotes_path=quotes_path,
                    run_date=run_date,
                    fill_execution_dates=due_execution_dates,
                    mode="execute" if mode in {"paper-trading", "fill-only"} else "dry-run",
                    runtime_dir=runtime_dir,
                    reports_root=reports_root,
                    phase_report_markdown_root=Path(phase_report_markdown_path).parent,
                    phase_report_json_root=Path(phase_report_json_path).parent,
                )
                step_statuses["virtual_fill_context"] = {
                    "run_date": run_date,
                    "fill_execution_dates": due_execution_dates,
                    "results": [result.to_dict() for result in fill_results],
                }
                if len(fill_results) == 1:
                    step_statuses["virtual_fill"] = fill_results[0].status
                    ledger_refs["virtual_fill_execution_record"] = fill_results[0].execution_record_path
                else:
                    step_statuses["virtual_fill"] = "VIRTUAL_FILL_GROUPS_PROCESSED"
                    ledger_refs["virtual_fill_execution_records"] = ",".join(result.execution_record_path for result in fill_results if result.execution_record_path)
                for fill_result in fill_results:
                    warnings.extend(fill_result.warnings)
                    blocked.extend(fill_result.blocked_reasons)
                    if fill_result.status == "DATA_NOT_READY":
                        blocked.append(f"virtual_fill_data_not_ready:{fill_result.execution_date}")
            else:
                step_statuses["virtual_fill"] = "NO_DUE_PENDING_ORDERS"
        else:
            step_statuses["virtual_fill"] = "NO_DUE_PENDING_ORDERS"

        if mode != "fill-only":
            continuation = run_daily_continuation(
                run_date=dates.data_target_date,
                ledger_path=ledger_path,
                quotes_path=quotes_path,
                mode="paper-trading" if mode == "paper-trading" and not blocked else "dry-run",
                approval_mode=approval_mode,
                operation_run_date=run_date,
                expected_valuation_date=run_date if mode == "paper-trading" else dates.data_target_date,
                run_id=run_id,
                runtime_dir=runtime_dir,
                update_tracker=False,
                reports_root=reports_root,
                docs_report_path=Path("docs/phase_reports") / "phase9u_unified_daily_continuation.md",
                json_report_path=Path("reports/phase_reports") / "phase9u_unified_daily_continuation.json",
            )
            step_statuses["ledger_valuation"] = continuation.valuation_status
            valuation_payload = _read_json_safely(Path(continuation.performance_report_json_path)).get("valuation", {})
            step_statuses["valuation_context"] = {
                "run_date": run_date,
                "decision_for": dates.decision_for,
                "data_target_date": dates.data_target_date,
                "business_date": dates.business_date,
                "market_data_target_date": dates.market_data_target_date,
                "latest_available_quote_date": dates.latest_available_quote_date,
                "valuation_date": valuation_payload.get("valuation_date", dates.data_target_date),
                "quote_source_path": valuation_payload.get("quote_source_path", str(quotes_path)),
                "quote_source_max_date": valuation_payload.get("quote_source_max_date", ""),
                "stale_price_source": valuation_payload.get("stale_price_source", False),
                "market_data_refresh_status": step_statuses["market_data_refresh"],
            }
            if bool(valuation_payload.get("stale_price_source", False)):
                blocked.append("stale_price_source_blocked")
            quote_source_max_date = str(valuation_payload.get("quote_source_max_date") or "")
            valuation_date = str(valuation_payload.get("valuation_date") or dates.valuation_date)
            if quote_source_max_date and quote_source_max_date < valuation_date:
                blocked.append(f"quote_source_max_date_stale:{quote_source_max_date}<valuation:{valuation_date}")
            report_refs["daily_performance_report"] = continuation.performance_report_json_path
            warnings.extend(continuation.warnings)
            blocked.extend(continuation.blocked_reasons)
        else:
            step_statuses["ledger_valuation"] = "SKIPPED_FILL_ONLY"

        if skip_inference or mode in {"fill-only", "report-only"}:
            step_statuses["daily_inference"] = "SKIPPED_BY_MODE_OR_FLAG"
        elif blocked:
            step_statuses["daily_inference"] = "SKIPPED_BLOCKED"
        elif mode == "paper-trading":
            first_run = run_first_daily_paper_trading_run(
                decision_for=dates.decision_for,
                data_until=dates.data_target_date,
                ledger_path=ledger_path,
                mode="paper-trading",
                runtime_dir=runtime_dir,
                reports_root=reports_root,
                feature_root=feature_root,
                canonical_quotes_path=quotes_path,
                approval_mode=approval_mode,
            )
            step_statuses["daily_inference"] = first_run.inference_status
            step_statuses["auto_approval"] = "CREATED" if first_run.auto_approval_json_path else "SKIPPED"
            step_statuses["pending_order_creation"] = first_run.pending_order_count
            step_statuses["pending_order_dedup_skipped_count"] = first_run.pending_order_dedup_skipped_count
            artifact_refs["first_daily_run_manifest"] = first_run.manifest_path
            warnings.extend(first_run.warnings)
            blocked.extend(first_run.blocked_reasons)
        else:
            inference = run_daily_inference(
                decision_for=dates.decision_for,
                data_until=dates.data_target_date,
                runtime_dir=runtime_dir,
                reports_root=reports_root,
                feature_root=feature_root,
                canonical_quotes_path=quotes_path,
                ledger_path=ledger_path,
            )
            step_statuses["daily_inference"] = inference.status
            step_statuses["auto_approval"] = "SKIPPED_NON_PAPER_MODE"
            step_statuses["pending_order_creation"] = 0
            artifact_refs["daily_inference_manifest"] = inference.manifest_path
            warnings.extend(inference.warnings)
            blocked.extend(inference.blocked_reasons)

        if skip_tracker_update:
            step_statuses["tracker_update"] = "SKIPPED_BY_FLAG"
        elif blocked:
            step_statuses["tracker_update"] = "SKIPPED_BLOCKED"
        else:
            tracker = update_business_day_tracker(
                ledger_path=ledger_path,
                business_day_index=_next_tracker_index(Path(runtime_dir) / "phase9" / "tracker" / "phase9_30bd_tracker.json"),
                run_date=run_date,
                decision_for=dates.decision_for,
                status="UNIFIED_DAILY_RUN_DONE",
                tracker_root=Path(runtime_dir) / "phase9" / "tracker",
                report_root=Path(reports_root) / "phase9" / "tracker",
            )
            step_statuses["tracker_update"] = tracker.status
            report_refs["tracker_report"] = tracker.report_json_path
            if tracker.blocked_reasons:
                warnings.extend(tracker.blocked_reasons)

        if skip_blog_report_v2:
            step_statuses["blog_report_v2"] = "SKIPPED_BY_FLAG"
        else:
            blog = write_blog_report_v2(
                decision_for=dates.decision_for,
                execution_date=run_date,
                inference_root=Path(runtime_dir) / "phase9" / "inference",
                ledger_path=ledger_path,
                performance_report_path=report_refs.get("daily_performance_report") or None,
                output_root=Path(reports_root) / "public" / "phase9_daily",
            )
            step_statuses["blog_report_v2"] = blog.status
            if step_statuses.get("valuation_context", {}).get("stale_price_source") is True:
                step_statuses["blog_report_v2"] = "BLOG_REPORT_V2_STALE_PRICE_SOURCE"
                blocked.append("blog_report_stale_price_source")
            blog_md = blog.markdown_path
            blog_json = blog.json_path
            report_refs["blog_report_v2"] = blog.json_path
            if blog.redaction_violations:
                blocked.extend(f"blog_redaction:{item}" for item in blog.redaction_violations)

        if blocked:
            status = UNIFIED_DAILY_RUNNER_BLOCKED
        if skip_notifications:
            step_statuses["line_notification"] = "SKIPPED_BY_FLAG"
            step_statuses["discord_notification"] = "SKIPPED_BY_FLAG"
        else:
            notify_runner = notification_runner or run_daily_notifications
            try:
                notification = notify_runner(
                    run_date=run_date,
                    runner_status=status,
                    ledger_path=ledger_path,
                    blog_report_markdown_path=blog_md,
                    blog_report_json_path=blog_json,
                    step_statuses=step_statuses,
                    dry_run=mode != "paper-trading",
                )
                notification_payload = notification.to_dict() if hasattr(notification, "to_dict") else dict(notification)
                step_statuses["line_notification"] = str(notification_payload.get("line_notification") or "FAILED_NON_FATAL")
                step_statuses["discord_notification"] = str(notification_payload.get("discord_notification") or "FAILED_NON_FATAL")
                step_statuses["notification_context"] = notification_payload
            except Exception as exc:
                step_statuses["line_notification"] = "FAILED_NON_FATAL"
                step_statuses["discord_notification"] = "FAILED_NON_FATAL"
                step_statuses["notification_context"] = {"status": "FAILED_NON_FATAL", "error_type": type(exc).__name__}
        manifest_path = _write_manifest(
            run_id=run_id,
            run_date=run_date,
            status=status,
            dates=dates,
            mode=mode,
            approval_mode=approval_mode,
            step_statuses=step_statuses,
            warnings=warnings,
            blocked=blocked,
            operation_root=operation_root,
        )
        phase_report_md, phase_report_json = _write_phase_report(
            run_id=run_id,
            run_date=run_date,
            status=status,
            mode=mode,
            dates=dates,
            step_statuses=step_statuses,
            warnings=warnings,
            blocked=blocked,
            blog_md=blog_md,
            blog_json=blog_json,
            markdown_path=phase_report_markdown_path,
            json_path=phase_report_json_path,
        )
        op_log = build_operation_log(
            run_id=run_id,
            date=run_date,
            mode=mode,
            started_at=started_at,
            status=status,
            step_statuses=step_statuses,
            artifact_refs=artifact_refs,
            ledger_refs=ledger_refs,
            report_refs={**report_refs, "phase9u_report": str(phase_report_json)},
            warnings=tuple(dict.fromkeys(warnings)),
            blocked_reasons=tuple(dict.fromkeys(blocked)),
            prohibited_flags=prohibited_flags(),
        )
        log_json, log_md = write_operation_log(op_log, operation_root)
        return UnifiedDailyRunResult(
            status=status,
            run_id=run_id,
            mode=mode,
            approval_mode=approval_mode,
            business_dates=dates,
            step_statuses=step_statuses,
            manifest_path=str(manifest_path),
            operation_log_json_path=str(log_json),
            operation_log_markdown_path=str(log_md),
            report_markdown_path=str(phase_report_md),
            report_json_path=str(phase_report_json),
            blog_report_v2_markdown_path=blog_md,
            blog_report_v2_json_path=blog_json,
            warnings=tuple(dict.fromkeys(warnings)),
            blocked_reasons=tuple(dict.fromkeys(blocked)),
        )
    finally:
        release_run_lock(run_id=lock.run_id, operation_root=operation_root)


def resolve_business_dates(*, run_date: str, quotes_path: Path | str) -> BusinessDates:
    latest_available = _latest_available_date(run_date=run_date, quotes_path=Path(quotes_path))
    next_day = _next_business_day(run_date)
    return BusinessDates(
        run_date=run_date,
        business_date=run_date,
        market_data_target_date=run_date,
        data_target_date=run_date,
        decision_for=run_date,
        valuation_date=run_date,
        latest_available_quote_date=latest_available,
        virtual_order_date=next_day,
        virtual_execution_date=next_day,
    )


def prohibited_flags() -> dict[str, bool]:
    return {
        "broker_order_api_called": False,
        "moomoo_simulate_order_called": False,
        "tachibana_order_called": False,
        "open_d_started": False,
        "login_called": False,
        "logout_called": False,
        "unlock_trade_called": False,
        "real_trade_executed": False,
        "live_order_allowed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _latest_available_date(*, run_date: str, quotes_path: Path) -> str:
    if not quotes_path.is_file():
        return run_date
    frame = pd.read_parquet(quotes_path)
    date_col = "date" if "date" in frame.columns else "Date"
    dates = sorted({str(value) for value in frame[date_col].astype(str) if str(value) <= run_date})
    return dates[-1] if dates else run_date


def _sync_refreshed_daily_quotes_to_canonical(*, refresh: Any, quotes_path: Path, target_date: str) -> tuple[str, list[str]]:
    normalized_path = _refresh_daily_quotes_normalized_path(refresh)
    data_until = str(_refresh_attr(refresh, "data_until", "") or "")
    blocked: list[str] = []
    if data_until < target_date:
        blocked.append(f"market_data_refresh_data_until_before_target:{data_until}<target:{target_date}")
    if not normalized_path:
        blocked.append("market_data_refresh_normalized_daily_quotes_path_missing")
        return "CANONICAL_NORMALIZED_NOT_UPDATED", blocked
    source = Path(normalized_path)
    if not source.is_file():
        blocked.append("market_data_refresh_normalized_daily_quotes_file_missing")
        return "CANONICAL_NORMALIZED_NOT_UPDATED", blocked
    if data_until < target_date:
        return "CANONICAL_NORMALIZED_NOT_UPDATED_DATA_NOT_READY", blocked
    quotes_path.parent.mkdir(parents=True, exist_ok=True)
    _write_canonical_daily_quotes(source=source, destination=quotes_path)
    max_date = _latest_available_date(run_date=target_date, quotes_path=quotes_path)
    if max_date < target_date:
        blocked.append(f"canonical_normalized_max_date_before_target:{max_date}<target:{target_date}")
        return "CANONICAL_NORMALIZED_UPDATED_BUT_STALE", blocked
    return "CANONICAL_NORMALIZED_UPDATED", blocked


def _write_canonical_daily_quotes(*, source: Path, destination: Path) -> None:
    frame = _canonicalized_daily_quote_frame(pd.read_parquet(source))
    if destination.is_file():
        existing = _canonicalized_daily_quote_frame(pd.read_parquet(destination))
        refresh_dates = set(frame["date"].dropna().astype(str).tolist())
        if refresh_dates and "date" in existing.columns:
            existing = existing[~existing["date"].astype(str).isin(refresh_dates)].copy()
        frame = pd.concat([existing, frame], ignore_index=True)
        if {"date", "code"}.issubset(frame.columns):
            frame = frame.drop_duplicates(subset=["date", "code"], keep="last")
            frame = frame.sort_values(["date", "code"]).reset_index(drop=True)
    frame.to_parquet(destination, index=False)


def _canonicalized_daily_quote_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    alias_pairs = {
        "date": ("target_date", "Date"),
        "code": ("Code",),
        "open": ("Open", "O", "AdjO"),
        "high": ("High", "H", "AdjH"),
        "low": ("Low", "L", "AdjL"),
        "close": ("Close", "C", "AdjC"),
        "volume": ("Volume", "Vo", "AdjVo"),
        "traded_value": ("TradingValue", "Va", "TurnoverValue"),
    }
    for target, sources in alias_pairs.items():
        if target in frame.columns:
            continue
        for source_column in sources:
            if source_column in frame.columns:
                frame[target] = frame[source_column]
                break
    required = {"date", "code", "open", "high", "low", "close", "volume"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"canonical_daily_quotes_required_columns_missing:{','.join(missing)}")
    return frame


def _refresh_attr(refresh: Any, name: str, default: Any = None) -> Any:
    if isinstance(refresh, dict):
        return refresh.get(name, default)
    return getattr(refresh, name, default)


def _refresh_sequence(refresh: Any, name: str) -> list[str]:
    value = _refresh_attr(refresh, name, ())
    return [str(item) for item in value] if value else []


def _refresh_daily_quotes_normalized_path(refresh: Any) -> str:
    endpoints = _refresh_attr(refresh, "endpoints", ()) or ()
    if isinstance(refresh, dict):
        endpoints = refresh.get("endpoints", ()) or ()
    for endpoint in endpoints:
        endpoint_name = _refresh_attr(endpoint, "endpoint", "")
        if endpoint_name != "daily_quotes":
            continue
        return str(_refresh_attr(endpoint, "normalized_path", "") or "")
    return ""


def _has_due_pending_orders(*, ledger_path: Path | str, run_date: str) -> bool:
    return bool(_due_pending_execution_dates(ledger_path=ledger_path, run_date=run_date))


def _due_pending_execution_dates(*, ledger_path: Path | str, run_date: str) -> list[str]:
    ledger = load_ledger(ledger_path)
    dates: set[str] = set()
    for order in ledger.pending_orders:
        if order.status not in {"APPROVED", "PENDING_VIRTUAL_FILL"}:
            continue
        due = order.virtual_execution_date or run_date
        if due <= run_date:
            dates.add(due)
    return sorted(dates)


def _run_due_virtual_fills(
    *,
    ledger_path: Path | str,
    quotes_path: Path | str,
    run_date: str,
    fill_execution_dates: list[str],
    mode: str,
    runtime_dir: Path | str,
    reports_root: Path | str,
    phase_report_markdown_root: Path | str,
    phase_report_json_root: Path | str,
) -> list[FirstVirtualFillRunResult]:
    results: list[FirstVirtualFillRunResult] = []
    current_ledger_path: Path | str = ledger_path
    for fill_execution_date in fill_execution_dates:
        result = run_first_virtual_fill(
            ledger_path=current_ledger_path,
            quotes_path=quotes_path,
            execution_date=fill_execution_date,
            run_date=run_date,
            mode=mode,
            runtime_dir=runtime_dir,
            docs_report_path=Path(phase_report_markdown_root) / f"phase9u_unified_virtual_fill_{fill_execution_date}.md",
            json_report_path=Path(phase_report_json_root) / f"phase9u_unified_virtual_fill_{fill_execution_date}.json",
            public_summary_path=Path(reports_root) / "public" / "phase9_daily" / f"{fill_execution_date}_virtual_fill_summary.md",
        )
        results.append(result)
        if result.ledger_latest_updated:
            current_ledger_path = Path(runtime_dir) / "phase9" / "ledger" / "latest.json"
    return results


def _next_tracker_index(path: Path) -> int:
    if not path.is_file():
        return 1
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    if not entries:
        return 1
    return max(int(entry.get("business_day_index") or 0) for entry in entries) + 1


def _read_json_safely(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _next_business_day(value: str) -> str:
    current = date.fromisoformat(value) + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()


def _write_manifest(
    *,
    run_id: str,
    run_date: str,
    status: str,
    dates: BusinessDates,
    mode: str,
    approval_mode: str,
    step_statuses: dict[str, Any],
    warnings: list[str],
    blocked: list[str],
    operation_root: Path | str,
) -> Path:
    path = Path(operation_root) / "runs" / run_date / "unified_daily_run_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": status,
                "run_id": run_id,
                "run_date": run_date,
                "mode": mode,
                "approval_mode": approval_mode,
                "business_dates": dates.to_dict(),
                "step_statuses": step_statuses,
                "warnings": list(dict.fromkeys(warnings)),
                "blocked_reasons": list(dict.fromkeys(blocked)),
                "prohibited_flags": prohibited_flags(),
                "created_at": utc_now_iso(),
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_phase_report(
    *,
    run_id: str,
    run_date: str,
    status: str,
    mode: str,
    dates: BusinessDates,
    step_statuses: dict[str, Any],
    warnings: list[str],
    blocked: list[str],
    blog_md: str,
    blog_json: str,
    markdown_path: Path | str,
    json_path: Path | str,
) -> tuple[Path, Path]:
    payload = {
        "status": status,
        "run_id": run_id,
        "run_date": run_date,
        "mode": mode,
        "launchd_command": "python3 scripts/run_aifundlab_daily_paper_trading.py --mode paper-trading --approval-mode auto_for_paper_trading --allow-api-fetch",
        "business_dates": dates.to_dict(),
        "step_statuses": step_statuses,
        "blog_report_v2_markdown_path": blog_md,
        "blog_report_v2_json_path": blog_json,
        "warnings": list(dict.fromkeys(warnings)),
        "blocked_reasons": list(dict.fromkeys(blocked)),
        "prohibited_flags": prohibited_flags(),
    }
    json_path = Path(json_path)
    md_path = Path(markdown_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_phase_report(payload), encoding="utf-8")
    return md_path, json_path


def _render_phase_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-U Unified Daily Paper Trading Runner",
        "",
        f"- status: {payload['status']}",
        f"- run_date: {payload['run_date']}",
        f"- mode: {payload['mode']}",
        f"- launchd_command: `{payload['launchd_command']}`",
        "",
        "## Business Dates",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in payload["business_dates"].items())
    lines += ["", "## Step Statuses", ""]
    lines.extend(f"- {key}: {value}" for key, value in payload["step_statuses"].items())
    lines += ["", "## Reports", "", f"- blog_report_v2: {payload['blog_report_v2_markdown_path']}", ""]
    if payload["blocked_reasons"]:
        lines += ["## Blocked Reasons", ""]
        lines.extend(f"- {reason}" for reason in payload["blocked_reasons"])
    return "\n".join(lines) + "\n"
