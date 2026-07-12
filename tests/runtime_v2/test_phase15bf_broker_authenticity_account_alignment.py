from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.broker.normalizer import normalize_cash_positions
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.runtime_v2.broker_readonly import refresh as broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.broker_readonly.refresh import run_broker_readonly_refresh
from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main


BUSINESS_DATE = "2026-07-10"
EVALUATION_TIME = datetime(2026, 7, 10, 9, 10, tzinfo=timezone.utc)


def test_phase15bf_api_origin_normalizer_does_not_keep_legacy_mock_source() -> None:
    positions = normalize_cash_positions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMGenbutuKabuList",
                "sResultCode": "0",
                "aGenbutuKabuList": [{"sIssueCode": "7203", "sZanKabuSuu": "100"}],
            }
        ),
        origin_metadata={
            "provider": "tachibana",
            "adapter": "tachibana_broker_snapshot",
            "transport": "HTTP_POST",
            "data_origin": "BROKER_API",
            "fixture_used": False,
            "mock_used": False,
            "read_only": True,
        },
    )

    assert positions[0].source == "broker_api"
    assert positions[0].data_origin == "BROKER_API"
    assert positions[0].mock_used is False
    assert positions[0].fixture_used is False


def test_phase15bf_fixture_and_mock_do_not_become_authenticity_ready(tmp_path: Path) -> None:
    fixture = run_broker_readonly_refresh(
        runtime_root=_runtime_root(tmp_path / "fixture", positions=[]),
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="FIXTURE", symbols=("7203",), account_identity=True),
    )
    mock = run_broker_readonly_refresh(
        runtime_root=_runtime_root(tmp_path / "mock", positions=[]),
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="MOCK", symbols=("7203",), account_identity=True),
    )

    assert fixture.data_origin == "FIXTURE"
    assert fixture.fixture_used is True
    assert fixture.authenticity_status == "REVIEW_REQUIRED"
    assert mock.data_origin == "MOCK"
    assert mock.mock_used is True
    assert mock.authenticity_status == "REVIEW_REQUIRED"


def test_phase15bf_api_response_requires_account_identity(tmp_path: Path) -> None:
    result = run_broker_readonly_refresh(
        runtime_root=_runtime_root(tmp_path, positions=[]),
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="BROKER_API", symbols=("7203",), account_identity=False),
    )

    assert result.data_origin == "BROKER_API"
    assert result.authenticity_status == "READY"
    assert result.account_identity_status == "UNKNOWN"
    assert result.status == "REVIEW_REQUIRED"
    assert result.reason == "broker_account_identity_unknown"


def test_phase15bf_runtime_owned_missing_is_alignment_mismatch(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path, positions=[{"symbol": "4591", "quantity": 100, "source_execution_id": "exec-1"}])

    result = run_broker_readonly_refresh(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="BROKER_API", symbols=("6501",), account_identity=True),
    )
    snapshot = _load_json(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")

    assert result.authenticity_status == "READY"
    assert result.account_alignment_status == "MISMATCH"
    assert snapshot["runtime_owned_symbols_missing_in_broker"] == ["4591"]
    assert result.status == "REVIEW_REQUIRED"


def test_phase15bf_broker_only_unrelated_positions_are_partial_match(tmp_path: Path) -> None:
    runtime_root = _runtime_root(tmp_path, positions=[{"symbol": "4591", "quantity": 100, "source_execution_id": "exec-1"}])

    result = run_broker_readonly_refresh(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="BROKER_API", symbols=("4591", "6501"), account_identity=True),
    )
    snapshot = _load_json(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")

    assert result.status == "READY"
    assert result.account_alignment_status == "RUNTIME_SCOPE_PARTIAL_MATCH"
    assert snapshot["broker_only_position_classification"] == "OUT_OF_RUNTIME_OWNED_SCOPE"
    assert snapshot["broker_symbols_not_runtime_owned"] == ["6501"]


def test_phase15bf_projection_current_without_broker_link_is_not_broker_reconciled(tmp_path: Path) -> None:
    runtime_root = _runtime_root(
        tmp_path,
        positions=[{"symbol": "4591", "quantity": 100, "source": "runtime_v2_runtime_owned_fill_projection"}],
    )

    result = run_broker_readonly_refresh(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        mode="demo",
        evaluation_time=EVALUATION_TIME,
        snapshot_provider=lambda **kwargs: _snapshot_provider(**kwargs, data_origin="BROKER_API", symbols=("6501", "6502", "9984"), account_identity=True),
    )
    snapshot = _load_json(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")

    assert result.status == "READY"
    assert result.account_alignment_status == "RUNTIME_SCOPE_NOT_BROKER_RECONCILED"
    assert snapshot["broker_only_position_classification"] == "OUT_OF_RUNTIME_OWNED_SCOPE"
    assert snapshot["runtime_owned_symbols_missing_in_broker"] == []
    assert snapshot["broker_symbols_not_runtime_owned"] == []


def test_phase15bf_regular_cli_snapshot_only_no_broker_write_or_state_mutation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(broker_readonly_refresh, "_default_snapshot_provider", lambda: _snapshot_provider)
    runtime_root = _runtime_root(tmp_path, positions=[])
    before_current = (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")
    before_pending = (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8")

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "broker_readonly_refresh",
            "--business-date",
            BUSINESS_DATE,
            "--evaluation-time",
            EVALUATION_TIME.isoformat(),
            "--submit-enabled",
            "false",
            "--notification-mode",
            "payload-only",
            "--runtime-root",
            str(runtime_root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(tmp_path / ".runtime" / "runtime_state" / "run_manifest"),
            "--log-root",
            str(tmp_path / ".runtime" / "runtime_state" / "logs"),
        ]
    )
    snapshot = _load_json(runtime_root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "tachibana_snapshot.json")

    assert exit_code == 0
    assert snapshot["data_origin"] == "BROKER_API"
    assert snapshot["authenticity_status"] == "READY"
    assert snapshot["broker_write_executed"] is False
    assert snapshot["ledger_appended"] is False
    assert snapshot["current_position_apply_executed"] is False
    assert snapshot["pending_mutation_executed"] is False
    assert (runtime_root / "persistent_ledger" / "state.json").read_text(encoding="utf-8") == before_current
    assert (runtime_root / "pending_order_plan" / "pending_order_plan.json").read_text(encoding="utf-8") == before_pending


def _runtime_root(tmp_path: Path, *, positions: list[dict]) -> Path:
    runtime_root = tmp_path / ".runtime"
    _write_json(
        runtime_root / "persistent_ledger" / "state.json",
        {
            "business_date": BUSINESS_DATE,
            "positions": positions,
            "cash": 1000000,
            "buying_power": 1000000,
        },
    )
    _write_json(
        runtime_root / "pending_order_plan" / "pending_order_plan.json",
        {
            "schema_version": "runtime_v2_pending_slot_v1",
            "state": "EMPTY",
            "active_pending": False,
        },
    )
    return runtime_root


def _snapshot_provider(
    *,
    snapshot_path: Path,
    report_path: Path,
    source: str = "runtime_v2_broker_readonly_refresh",
    data_origin: str = "BROKER_API",
    symbols: tuple[str, ...] = ("7203",),
    account_identity: bool = True,
    **_: object,
):
    payload = {
        "schema_version": "tachibana_broker_snapshot_v1",
        "broker": "tachibana",
        "provider": "tachibana",
        "adapter": "tachibana_broker_snapshot",
        "transport": "HTTP_POST",
        "raw_response_origin": "TACHIBANA_API_RESPONSE" if data_origin == "BROKER_API" else data_origin,
        "environment": "demo",
        "session_environment": "demo",
        "generated_at": "2026-07-10T09:05:00+00:00",
        "session_status": "PASS",
        "source": source,
        "data_origin": data_origin,
        "fixture_used": data_origin == "FIXTURE",
        "mock_used": data_origin == "MOCK",
        "read_only": True,
        "account_summary": {"data_origin": data_origin, "cash_available": "1000000"},
        "buying_power": {"data_origin": data_origin, "buying_power": "1000000"},
        "positions": [
            {"data_origin": data_origin, "issue_code": symbol, "quantity": "100", "available_quantity": "100"}
            for symbol in symbols
        ],
        "orders": [],
        "executions": [],
        "redaction_status": {"auth_identifier_saved": False, "private_secret_saved": False},
    }
    if account_identity:
        payload.update(
            {
                "account_identity_hash": "sha256:test-account",
                "account_identity_status": "REFERENCE_HASHED",
                "credential_reference_id": "sha256:test-credential",
            }
        )
    _write_json(snapshot_path, payload)
    _write_json(report_path, {"status": "PASS", "source": source, "data_origin": data_origin})
    return type("SnapshotResult", (), {"status": "PASS"})()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
