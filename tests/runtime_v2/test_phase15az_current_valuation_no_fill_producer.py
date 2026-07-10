from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ai_fund_lab_v2.runtime_v2.cli.run_daily_operation import main
from ai_fund_lab_v2.runtime_v2.current_state.temporal import CURRENT_TEMPORAL_SCHEMA_VERSION
from ai_fund_lab_v2.runtime_v2.current_state.valuation import run_current_valuation_refresh


BUSINESS_DATE = "2026-07-10"


def test_phase15az_no_fill_updates_valuation_only(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    position = result.candidate_current["positions"][0]

    assert result.status == "READY"
    assert result.no_fill is True
    assert result.valuation_as_of == BUSINESS_DATE
    assert position["quantity"] == 100
    assert position["average_price"] == 900
    assert result.candidate_current["last_execution_date"] == "2026-07-09"
    assert result.candidate_current["position_state_as_of"] == "2026-07-09"
    assert position["current_price"] == 1100
    assert position["market_value"] == 110000
    assert position["unrealized_pnl"] == 20000
    assert result.candidate_current["current_position_status"] == "READY"
    assert result.candidate_current["current_valuation_status"] == "READY"


def test_phase15az_non_trading_day_carryover_is_valid(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root, valuation_as_of="2026-07-10", source_market_date="2026-07-10")
    _write_market(root, market_date="2026-07-10", price=1000, freshness="VALID_CARRYOVER")

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date="2026-07-11",
        now=datetime(2026, 7, 11, 9, 0, tzinfo=timezone.utc),
    )

    assert result.status == "READY"
    assert result.candidate_current["current_valuation_status"] == "VALID_CARRYOVER"


def test_phase15az_stale_market_does_not_update(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100, market_status="STALE")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase15az_missing_quote_requires_review_and_no_partial_update(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, quotes={})

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.missing_symbols == ("7203",)
    assert result.valued_position_count == 0


def test_phase15az_invalid_price_requires_review(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=0)

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase15az_quote_stale_requires_review(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100, quote_freshness="STALE")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase15az_quote_date_mismatch_requires_review(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100, quote_market_date="2026-07-09")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase15az_quote_source_missing_requires_review(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100, quote_source="")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.apply_executed is False


def test_phase15az_no_feature_or_previous_price_fallback(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root, current_price=9999)
    _write_market(root, market_date=BUSINESS_DATE, quotes={})
    feature_dir = root / "operations" / "feature_artifacts" / BUSINESS_DATE
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "candidate_features.parquet").write_text("not a price source", encoding="utf-8")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert result.candidate_current["positions"][0]["current_price"] == 9999


def test_phase15az_no_position_ready_without_quotes(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root, positions=[])
    _write_market(root, market_date=BUSINESS_DATE, quotes={})

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "READY"
    assert result.candidate_current["no_position"] is True
    assert result.candidate_current["no_position_reason"] == "current_has_no_runtime_owned_positions"


def test_phase15az_dry_run_does_not_modify_current(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)
    before = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    after = (root / "persistent_ledger" / "state.json").read_text(encoding="utf-8")

    assert result.apply_requested is False
    assert result.apply_executed is False
    assert before == after


def test_phase15az_apply_writes_backup_and_current_atomically(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    result = run_current_valuation_refresh(
        runtime_root=root,
        business_date=BUSINESS_DATE,
        apply_current_valuation=True,
        now=_now(),
    )
    current = _load_json(root / "persistent_ledger" / "state.json")

    assert result.apply_requested is True
    assert result.apply_executed is True
    assert Path(result.backup_path).is_file()
    assert current["positions"][0]["current_price"] == 1100


def test_phase15az_idempotent_history_for_same_content(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    first = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    second = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())
    first_payload = _load_json(Path(first.artifact_path))
    second_payload = _load_json(Path(second.artifact_path))

    assert first_payload["history_path"] == second_payload["history_path"]


def test_phase15az_corrupt_current_halts(tmp_path):
    root = _runtime_root(tmp_path)
    path = root / "persistent_ledger" / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "HALT"


def test_phase15az_legacy_current_requires_migration_first(tmp_path):
    root = _runtime_root(tmp_path)
    _write_legacy_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.status == "REVIEW_REQUIRED"
    assert "current_temporal_migration_required_before_valuation" in result.candidate_current.get("warnings", []) or result.review_required


def test_phase15az_broker_only_position_not_added(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root, positions=[])
    _write_market(root, market_date=BUSINESS_DATE, price=1100)
    _write_json(root / "runtime_state" / "broker_readonly" / BUSINESS_DATE / "snapshot.json", {"positions": [_position("9999")]})

    result = run_current_valuation_refresh(runtime_root=root, business_date=BUSINESS_DATE, now=_now())

    assert result.candidate_current.get("positions") == []


def test_phase15az_cli_job_dry_run_writes_artifact(tmp_path):
    root = _runtime_root(tmp_path)
    _write_current(root)
    _write_market(root, market_date=BUSINESS_DATE, price=1100)

    exit_code = main(
        [
            "--mode",
            "demo",
            "--job",
            "current_valuation_refresh",
            "--business-date",
            BUSINESS_DATE,
            "--runtime-root",
            str(root),
            "--reports-root",
            str(tmp_path / "reports" / "runtime_v2"),
            "--public-reports-root",
            str(tmp_path / "reports" / "public" / "runtime_v2"),
            "--manifest-root",
            str(root / "runtime_state" / "run_manifest"),
            "--log-root",
            str(root / "runtime_state" / "logs"),
            "--evaluation-time",
            _now().isoformat(),
        ]
    )
    artifact = root / "runtime_state" / "current_valuation" / BUSINESS_DATE / "current_valuation_refresh.json"
    payload = _load_json(artifact)

    assert exit_code == 0
    assert payload["apply_requested"] is False
    assert payload["apply_executed"] is False


def _runtime_root(tmp_path: Path) -> Path:
    root = tmp_path / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_current(
    root: Path,
    *,
    positions: list[dict] | None = None,
    valuation_as_of: str = "2026-07-09",
    source_market_date: str = "2026-07-09",
    current_price: float = 1000,
) -> None:
    current_positions = [_position("7203", current_price=current_price)] if positions is None else positions
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "temporal_schema_version": CURRENT_TEMPORAL_SCHEMA_VERSION,
            "position_state_as_of": "2026-07-09",
            "valuation_as_of": valuation_as_of,
            "source_market_date": source_market_date,
            "last_execution_date": "2026-07-09",
            "last_reconciled_at": "2026-07-10T08:00:00+00:00",
            "updated_at": "2026-07-10T08:00:00+00:00",
            "positions": current_positions,
            "cash": 900000,
            "buying_power": 900000,
            "market_value": sum(float(position.get("market_value") or 0) for position in current_positions),
            "total_equity": 1000000,
            "production_equivalent": True,
        },
    )


def _write_legacy_current(root: Path) -> None:
    _write_json(
        root / "persistent_ledger" / "state.json",
        {
            "schema_version": "1",
            "as_of": "2026-07-09",
            "updated_at": "2026-07-09T00:00:00+00:00",
            "positions": [_position("7203")],
        },
    )


def _write_market(
    root: Path,
    *,
    market_date: str,
    price: float | None = None,
    quotes: dict | None = None,
    market_status: str = "READY",
    freshness: str = "READY",
    quote_freshness: str | None = None,
    quote_market_date: str | None = None,
    quote_source: str | None = "runtime_state/market/test",
) -> None:
    quote_payload = quotes
    if quote_payload is None:
        quote_payload = {
            "7203": {
                "symbol": "7203",
                "price": price,
                "price_type": "jquants_daily_quote",
                "market_date": quote_market_date or market_date,
                "observed_at": market_date,
                "source": quote_source,
                "freshness_status": quote_freshness or freshness,
                "adjusted": False,
            }
        }
    artifact = root / "runtime_state" / "market" / market_date / "market_evidence.json"
    _write_json(
        artifact,
        {
            "schema_version": "runtime_v2_market_evidence_v1",
            "runtime_business_date": BUSINESS_DATE,
            "market_date": market_date,
            "latest_expected_trading_date": market_date,
            "latest_available_market_date": market_date,
            "market_status": market_status,
            "market_freshness_status": freshness,
            "quote_status": "READY" if quote_payload else "REVIEW_REQUIRED",
            "quotes": quote_payload,
        },
    )
    _write_json(root / "runtime_state" / "market" / "latest.json", {"artifact_path": str(artifact), "market_date": market_date})


def _position(symbol: str, *, current_price: float = 1000) -> dict:
    return {
        "symbol": symbol,
        "quantity": 100,
        "average_price": 900,
        "current_price": current_price,
        "market_value": 100 * current_price,
        "unrealized_pnl": (current_price - 900) * 100,
        "ownership": "runtime_owned",
    }


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> datetime:
    return datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
