from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys

import pandas as pd
import pytest

from ai_fund_lab_v2.broker.settings import DEMO_BASE_URL, PROD_BASE_URL
from ai_fund_lab_v2.operations.io import OperationPaths, write_json
from ai_fund_lab_v2.operations.operations import (
    run_daily_report,
    run_demo_special_fill_simulation,
    run_fill_monitor,
    run_reconcile,
)


TRADE_DATE = "2026-06-29"


def _write_artifacts(root: Path, *, code: str = "92560", include_buy: bool = True) -> None:
    paths = OperationPaths(root)
    listed_path = root / "feature_refresh" / TRADE_DATE / "jquants" / "listed_issues" / "listed_info_for_feature.parquet"
    listed_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"Code": code, "code": code, "MktNm": "グロース", "ProdCat": "011"}]).to_parquet(listed_path)
    issue = code[:-1] if code.endswith("0") else code
    orders = [
        {
            "issue_code": issue,
            "side": "3",
            "quantity": "100",
            "executed_quantity": "0",
            "remaining_quantity": "100",
            "status": "未約定",
            "price": "5410.0000",
            "raw_response_saved": False,
            "secret_saved": False,
        }
    ] if include_buy else []
    write_json(paths.dated("broker_orders", TRADE_DATE, "orders.json"), {"artifact_type": "broker_orders", "business_date": TRADE_DATE, "orders": orders, "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_executions", TRADE_DATE, "executions.json"), {"artifact_type": "broker_executions", "business_date": TRADE_DATE, "executions": [], "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_positions", TRADE_DATE, "positions.json"), {"artifact_type": "broker_positions", "business_date": TRADE_DATE, "positions": [], "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_buying_power", TRADE_DATE, "buying_power.json"), {"artifact_type": "broker_buying_power", "business_date": TRADE_DATE, "buying_power": "19458494", "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("broker_snapshot_summary", TRADE_DATE, "broker_snapshot_summary.json"), {"orders_count": len(orders), "executions_count": 0, "positions_count": 0, "buying_power": "19458494", "raw_response_saved": False, "secret_saved": False})
    write_json(paths.dated("submitted_orders", TRADE_DATE, "submitted_orders.json"), {"artifact_type": "demo_submit", "business_date": TRADE_DATE, "submitted_orders": []})


def test_demo_special_fill_simulation_updates_ledger_and_events(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path)

    result = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)
    fill = run_fill_monitor(trade_date=TRADE_DATE, root=tmp_path)
    reconcile = run_reconcile(trade_date=TRADE_DATE, root=tmp_path)
    report = run_daily_report(trade_date=TRADE_DATE, root=tmp_path)

    assert result["status"] == "PASS"
    assert result["broker_confirmed_buy_fill"] is False
    assert result["simulated_buy_fill"] is True
    assert result["simulated_sell_fill"] is True
    assert result["performance_metrics_excluded"] is True
    assert result["persistent_demo_ledger"]["simulated_execution_count"] == 2
    lifecycles = {event["lifecycle"] for event in fill["fill_events"]}
    assert "SIMULATED_FILLED" in lifecycles
    assert reconcile["demo_special_fill_simulation"]["reconcile_classification"] == "DEMO_SPECIAL_SIMULATION_RECONCILED"
    refs = Path(report["daily_report_refs_path"]).read_text(encoding="utf-8")
    assert "demo_special_fill_simulation" in refs


def test_demo_special_fill_simulation_fails_closed_in_production(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "production")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", PROD_BASE_URL)
    _write_artifacts(tmp_path)

    result = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)

    assert result["status"] == "BLOCK"
    assert result["production_enabled"] is False
    assert result["simulated_buy_fill"] is False


def test_demo_special_fill_simulation_requires_existing_buy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path, include_buy=False)

    result = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)

    assert result["status"] == "BLOCK"
    assert "existing_buy_waiting_order_not_found" in result["blocks"]


def test_demo_special_fill_cli_returns_zero_when_not_applicable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path, include_buy=False)
    env = os.environ.copy()
    env["TACHIBANA_API_ENV"] = "demo"
    env["TACHIBANA_API_BASE_URL"] = DEMO_BASE_URL

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_demo_special_fill_simulation.py",
            "--trade-date",
            TRADE_DATE,
            "--root",
            str(tmp_path),
            "--enable-simulation",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )

    assert completed.returncode == 0


def test_demo_special_fill_simulation_requires_9000_series(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path, code="72030")

    result = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)

    assert result["status"] == "BLOCK"
    assert "broker_issue_code_not_9000_series" in result["blocks"]


def test_demo_special_fill_simulation_requires_enable_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path)

    result = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=False)

    assert result["status"] == "BLOCK"
    assert "demo_special_fill_simulation_not_enabled" in result["blocks"]


def test_demo_special_fill_simulation_does_not_run_twice_for_same_date(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TACHIBANA_API_ENV", "demo")
    monkeypatch.setenv("TACHIBANA_API_BASE_URL", DEMO_BASE_URL)
    _write_artifacts(tmp_path)

    first = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)
    second = run_demo_special_fill_simulation(trade_date=TRADE_DATE, root=tmp_path, demo_special_fill_simulation_enabled=True)

    assert first["status"] == "PASS"
    assert second["status"] == "BLOCK"
    assert "demo_special_fill_already_simulated_for_same_order" in second["blocks"]
    assert second["simulated_buy_fill"] is False
