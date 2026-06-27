from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.broker.models import utc_now_iso
from ai_fund_lab_v2.paper_trading.ledger import PaperTradingLedger, load_ledger, write_ledger
from ai_fund_lab_v2.paper_trading.virtual_fill_processor import VirtualFillResult, process_virtual_fills


DATA_NOT_READY = "DATA_NOT_READY"
FIRST_VIRTUAL_FILL_DRY_RUN = "FIRST_VIRTUAL_FILL_DRY_RUN"
FIRST_VIRTUAL_FILL_EXECUTED = "FIRST_VIRTUAL_FILL_EXECUTED"
FIRST_VIRTUAL_FILL_BLOCKED = "FIRST_VIRTUAL_FILL_BLOCKED"
FILL_MODES = {"dry-run", "execute"}


@dataclass(frozen=True)
class FirstVirtualFillRunResult:
    status: str
    mode: str
    execution_date: str
    data_readiness: str
    run_date: str = ""
    fill_execution_date: str = ""
    pending_orders_before: int = 0
    filled_order_count: int = 0
    no_fill_order_count: int = 0
    cash_before: str = "0"
    cash_after: str = "0"
    positions_before: int = 0
    positions_after: int = 0
    realized_pnl: str = "0"
    unrealized_pnl: str = "0"
    ledger_latest_updated: bool = False
    ledger_snapshot_dir: str = ""
    execution_record_path: str = ""
    manifest_path: str = ""
    markdown_report_path: str = ""
    json_report_path: str = ""
    public_summary_path: str = ""
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    prohibited_flags: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["prohibited_flags"] = self.prohibited_flags or prohibited_flags()
        return payload


def run_first_virtual_fill(
    *,
    ledger_path: Path | str,
    quotes_path: Path | str,
    execution_date: str,
    run_date: str | None = None,
    mode: str = "dry-run",
    runtime_dir: Path | str = ".runtime",
    docs_report_path: Path | str = "docs/phase_reports/phase9p_first_virtual_fill.md",
    json_report_path: Path | str = "reports/phase_reports/phase9p_first_virtual_fill.json",
    public_summary_path: Path | str | None = None,
) -> FirstVirtualFillRunResult:
    if mode not in FILL_MODES:
        raise ValueError(f"Unsupported first virtual fill mode: {mode}")
    run_date = run_date or execution_date
    ledger = load_ledger(ledger_path)
    pending = [order for order in ledger.pending_orders if order.status in {"APPROVED", "PENDING_VIRTUAL_FILL"}]
    cash_before = ledger.cash
    positions_before = len(ledger.positions)
    readiness = _check_execution_data_readiness(quotes_path=Path(quotes_path), execution_date=execution_date)
    if readiness["status"] != "DATA_READY":
        result = FirstVirtualFillRunResult(
            status=DATA_NOT_READY,
            mode=mode,
            execution_date=execution_date,
            run_date=run_date,
            fill_execution_date=execution_date,
            data_readiness=readiness["status"],
            pending_orders_before=len(pending),
            cash_before=str(cash_before),
            cash_after=str(cash_before),
            positions_before=positions_before,
            positions_after=positions_before,
            ledger_latest_updated=False,
            markdown_report_path=str(docs_report_path),
            json_report_path=str(json_report_path),
            public_summary_path=str(public_summary_path or _default_public_summary_path(execution_date)),
            warnings=tuple(readiness["warnings"]),
            blocked_reasons=tuple(readiness["blocked_reasons"]),
            prohibited_flags=prohibited_flags(),
        )
        _write_reports(result=result, fill=None, docs_report_path=docs_report_path, json_report_path=json_report_path, public_summary_path=public_summary_path)
        return result
    quote_rows = readiness["quote_rows"]
    fill = process_virtual_fills(
        ledger=ledger,
        quote_rows=quote_rows,
        execution_date=execution_date,
        runtime_dir=runtime_dir,
        output_root=Path(runtime_dir) / "phase9p_tmp_outputs",
        dry_run=True,
    )
    snapshot_dir = Path(runtime_dir) / "phase9" / "ledger_runs" / f"{execution_date}_first_virtual_fill"
    paths = _write_phase9p_outputs(snapshot_dir=snapshot_dir, execution_date=execution_date, run_date=run_date, fill=fill, runtime_dir=Path(runtime_dir))
    latest_updated = False
    if mode == "execute":
        write_ledger(fill.ledger_after, runtime_dir=runtime_dir)
        latest_updated = True
    result = FirstVirtualFillRunResult(
        status=FIRST_VIRTUAL_FILL_EXECUTED if mode == "execute" else FIRST_VIRTUAL_FILL_DRY_RUN,
        mode=mode,
        execution_date=execution_date,
        run_date=run_date,
        fill_execution_date=execution_date,
        data_readiness=readiness["status"],
        pending_orders_before=len(pending),
        filled_order_count=len(fill.executions),
        no_fill_order_count=len(fill.no_fill_orders),
        cash_before=str(cash_before),
        cash_after=str(fill.ledger_after.cash),
        positions_before=positions_before,
        positions_after=len(fill.ledger_after.positions),
        realized_pnl=str(fill.ledger_after.performance.realized_pnl),
        unrealized_pnl=str(fill.ledger_after.performance.unrealized_pnl),
        ledger_latest_updated=latest_updated,
        ledger_snapshot_dir=str(snapshot_dir),
        execution_record_path=paths["executions"],
        manifest_path=paths["manifest"],
        markdown_report_path=str(docs_report_path),
        json_report_path=str(json_report_path),
        public_summary_path=str(public_summary_path or _default_public_summary_path(execution_date)),
        prohibited_flags=prohibited_flags(),
    )
    _write_reports(result=result, fill=fill, docs_report_path=docs_report_path, json_report_path=json_report_path, public_summary_path=public_summary_path)
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
        "real_trade_executed": False,
        "model_retraining_executed": False,
        "full_backtest_executed": False,
        "scheduler_auto_registered": False,
    }


def _check_execution_data_readiness(*, quotes_path: Path, execution_date: str) -> dict[str, Any]:
    warnings: list[str] = []
    blocked: list[str] = []
    if not quotes_path.is_file():
        return {"status": "DATA_NOT_READY", "quote_rows": [], "warnings": warnings, "blocked_reasons": ["quotes_path_missing"]}
    try:
        frame = _read_quotes_frame(quotes_path)
    except Exception as exc:
        return {"status": "DATA_NOT_READY", "quote_rows": [], "warnings": warnings, "blocked_reasons": [f"quotes_unreadable:{type(exc).__name__}"]}
    date_column = "date" if "date" in frame.columns else ("Date" if "Date" in frame.columns else "target_date")
    rows = frame[frame[date_column].astype(str) == execution_date].copy()
    if rows.empty:
        return {"status": "DATA_NOT_READY", "quote_rows": [], "warnings": warnings, "blocked_reasons": ["execution_date_quotes_missing"]}
    open_col = "open" if "open" in rows.columns else "Open"
    nonpositive = rows[pd.to_numeric(rows[open_col], errors="coerce").fillna(0) <= 0]
    if not nonpositive.empty:
        warnings.append(f"nonpositive_open_price_rows={len(nonpositive)}")
    return {"status": "DATA_READY", "quote_rows": rows.to_dict(orient="records"), "warnings": warnings, "blocked_reasons": blocked}


def _read_quotes_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return pd.DataFrame(payload.get("rows") or payload.get("daily_quotes") or [])
    return pd.DataFrame(payload)


def _write_phase9p_outputs(*, snapshot_dir: Path, execution_date: str, run_date: str, fill: VirtualFillResult, runtime_dir: Path) -> dict[str, str]:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    before_path = snapshot_dir / "ledger_before.json"
    after_path = snapshot_dir / "ledger_after.json"
    diff_path = snapshot_dir / "ledger_diff.json"
    manifest_path = snapshot_dir / "virtual_fill_manifest.json"
    execution_path = runtime_dir / "phase9" / "ledger" / "executions" / f"{execution_date}_executions.json"
    before_path.write_text(json.dumps(fill.ledger_before.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    after_path.write_text(json.dumps(fill.ledger_after.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    diff = _ledger_diff(fill.ledger_before, fill.ledger_after)
    diff_path.write_text(json.dumps(diff, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    execution_path.parent.mkdir(parents=True, exist_ok=True)
    execution_records = [record.to_dict() for record in fill.executions] + [record.to_dict() for record in fill.no_fill_orders]
    execution_path.write_text(json.dumps({"execution_date": execution_date, "records": execution_records}, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "execution_date": execution_date,
        "fill_execution_date": execution_date,
        "run_date": run_date,
        "fill_policy": "next_business_day_open_v1",
        "filled_order_count": len(fill.executions),
        "no_fill_order_count": len(fill.no_fill_orders),
        "ledger_before_path": str(before_path),
        "ledger_after_path": str(after_path),
        "ledger_diff_path": str(diff_path),
        "execution_record_path": str(execution_path),
        "virtual_fill_executed": True,
        "broker_order_api_called": False,
        "open_d_started": False,
        "unlock_trade_called": False,
        "created_at": utc_now_iso(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"before": str(before_path), "after": str(after_path), "diff": str(diff_path), "manifest": str(manifest_path), "executions": str(execution_path)}


def _write_reports(
    *,
    result: FirstVirtualFillRunResult,
    fill: VirtualFillResult | None,
    docs_report_path: Path | str,
    json_report_path: Path | str,
    public_summary_path: Path | str | None,
) -> None:
    payload = result.to_dict()
    if fill:
        payload["filled_orders"] = [record.to_dict() for record in fill.executions]
        payload["no_fill_orders"] = [record.to_dict() for record in fill.no_fill_orders]
        payload["ledger_diff"] = _ledger_diff(fill.ledger_before, fill.ledger_after)
    else:
        payload["filled_orders"] = []
        payload["no_fill_orders"] = []
        payload["ledger_diff"] = {}
    json_path = Path(json_report_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = Path(docs_report_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_markdown(payload), encoding="utf-8")
    public_path = Path(public_summary_path) if public_summary_path else _default_public_summary_path(result.execution_date)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(_render_public_summary(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-P First Virtual Fill",
        "",
        f"- status: {payload['status']}",
        f"- mode: {payload['mode']}",
        f"- run_date: {payload.get('run_date')}",
        f"- execution_date: {payload['execution_date']}",
        f"- fill_execution_date: {payload.get('fill_execution_date')}",
        f"- data_readiness: {payload['data_readiness']}",
        f"- pending_orders_before: {payload['pending_orders_before']}",
        f"- filled_order_count: {payload['filled_order_count']}",
        f"- no_fill_order_count: {payload['no_fill_order_count']}",
        f"- cash_before: {payload['cash_before']}",
        f"- cash_after: {payload['cash_after']}",
        f"- positions_before: {payload['positions_before']}",
        f"- positions_after: {payload['positions_after']}",
        f"- realized_pnl: {payload['realized_pnl']}",
        f"- unrealized_pnl: {payload['unrealized_pnl']}",
        f"- ledger_latest_updated: {str(payload['ledger_latest_updated']).lower()}",
        "",
        "## Paths",
        "",
        f"- ledger_snapshot_dir: {payload['ledger_snapshot_dir'] or 'none'}",
        f"- execution_record_path: {payload['execution_record_path'] or 'none'}",
        "",
        "## Blocked Reasons",
        "",
    ]
    blocked = payload.get("blocked_reasons", [])
    lines.extend([f"- {reason}" for reason in blocked] if blocked else ["- none"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- broker_order_api_called: false",
            "- open_d_started: false",
            "- unlock_trade_called: false",
            "- real_trade_executed: false",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_public_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Phase9 Virtual Fill Summary",
            "",
            f"- execution_date: {payload['execution_date']}",
            f"- status: {payload['status']}",
            f"- filled_order_count: {payload['filled_order_count']}",
            f"- no_fill_order_count: {payload['no_fill_order_count']}",
            f"- virtual_asset_cash: {payload['cash_after']}",
            "",
            "仮想運用の検証記録です。実売買ではありません。",
            "",
        ]
    )


def _ledger_diff(before: PaperTradingLedger, after: PaperTradingLedger) -> dict[str, str]:
    return {
        "cash_change": str(after.cash - before.cash),
        "position_count_change": str(len(after.positions) - len(before.positions)),
        "pending_order_count_change": str(len(after.pending_orders) - len(before.pending_orders)),
        "realized_pnl_change": str(after.performance.realized_pnl - before.performance.realized_pnl),
        "unrealized_pnl_change": str(after.performance.unrealized_pnl - before.performance.unrealized_pnl),
    }


def _default_public_summary_path(execution_date: str) -> Path:
    return Path("reports") / "public" / "phase9_daily" / f"{execution_date}_virtual_fill_summary.md"
