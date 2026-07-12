"""Broker-side adapter for Runtime v2 execution ReadOnly snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_fund_lab_v2.broker.settings import BrokerSettings, load_broker_settings
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import run_tachibana_broker_snapshot


def run_runtime_v2_execution_readonly_snapshot(
    *,
    mode: str,
    snapshot_path: Path,
    report_path: Path,
    settings: BrokerSettings | None = None,
    source: str = "runtime_v2_execution_readonly",
) -> Any:
    settings = settings or load_broker_settings()
    if mode == "demo":
        settings.require_demo_environment()
    return run_tachibana_broker_snapshot(
        reports_dir=report_path.parent,
        run_enabled=True,
        report_filename=report_path.name,
        snapshot_path=snapshot_path,
        source=source,
        settings=settings,
        symbols=(),
        include_quotes=False,
    )
