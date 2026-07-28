from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai_fund_lab_v2.runtime_v2.historical_support.environment import HistoricalSubmitAdapter
from ai_fund_lab_v2.runtime_v2.historical_support.source_identity import build_source_identity
from ai_fund_lab_v2.runtime_v2.submit.models import RuntimeV2SubmitCommand


BUSINESS_DATE = "2026-07-06"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _command() -> RuntimeV2SubmitCommand:
    return RuntimeV2SubmitCommand(
        command_id="cmd-1",
        environment="historical",
        pending_plan_id="pending-1",
        pending_item_id="item-1",
        approval_hash="approval-1",
        symbol="7203",
        side="BUY",
        quantity=100,
        order_type="MARKET",
        price_type="MARKET",
        limit_price=0,
        estimated_amount=250000,
        target_session_date=BUSINESS_DATE,
        live_order_allowed=True,
        listed_info={"code": "7203", "trading_unit": 100},
    )


def _write_sources(root: Path, *, run_id: str = "run-a", open_price: float = 2500.0) -> dict[str, Path]:
    base = root / "reports" / "runtime_tests" / "runs" / run_id / "daily" / BUSINESS_DATE / "market_refresh"
    logical_root = base / "inputs" / "historical_asof" / BUSINESS_DATE
    normalized = logical_root / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    raw = logical_root / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    listed = logical_root / "raw" / "jquants" / "listed_issues" / "data.parquet"
    for path in (normalized, raw, listed):
        path.parent.mkdir(parents=True, exist_ok=True)
    ohlcv = pd.DataFrame(
        [
            {"Date": BUSINESS_DATE, "Code": "7203", "Open": open_price, "Close": open_price + 10, "AdjFactor": 1.0},
        ]
    )
    ohlcv.to_parquet(normalized, index=False)
    ohlcv.to_parquet(raw, index=False)
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "7203", "CompanyName": "Toyota"}]).to_parquet(listed, index=False)
    asof = base / "historical_asof_view.json"
    _write_json(
        asof,
        {
            "schema_version": "runtime_historical_asof_view_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "authorities": [
                {
                    "authority": "listed_issues",
                    "status": "PASS",
                    "business_date": BUSINESS_DATE,
                    "physical_source_path": str(listed),
                    "physical_source_hash": _sha256(listed),
                    "selected_snapshot_date": BUSINESS_DATE,
                }
            ],
        },
    )
    manifest = logical_root / "logical_input_manifest.json"
    materialization_id = f"historical_asof:{run_id}:{BUSINESS_DATE}"
    source_identities = {
        "normalized_ohlcv": build_source_identity(
            normalized,
            logical_source_id="normalized_ohlcv",
            business_date=BUSINESS_DATE,
            feature_date=BUSINESS_DATE,
            as_of_date=BUSINESS_DATE,
            materialization_id=materialization_id,
        ),
        "raw_ohlcv": build_source_identity(
            raw,
            logical_source_id="raw_ohlcv",
            business_date=BUSINESS_DATE,
            feature_date=BUSINESS_DATE,
            as_of_date=BUSINESS_DATE,
            materialization_id=materialization_id,
        ),
        "listed_issues": build_source_identity(
            listed,
            logical_source_id="listed_issues",
            business_date=BUSINESS_DATE,
            feature_date=BUSINESS_DATE,
            as_of_date=BUSINESS_DATE,
            materialization_id=materialization_id,
        ),
    }
    _write_json(
        manifest,
        {
            "schema_version": "runtime_historical_logical_input_manifest_v1",
            "status": "PASS",
            "business_date": BUSINESS_DATE,
            "feature_date": BUSINESS_DATE,
            "as_of_date": BUSINESS_DATE,
            "materialization_id": materialization_id,
            "logical_paths": {
                "normalized_ohlcv": str(normalized),
                "raw_ohlcv": str(raw),
                "listed_issues": str(listed),
            },
            "source_identities": source_identities,
        },
    )
    return {"base": base, "asof": asof, "manifest": manifest, "normalized": normalized, "raw": raw, "listed": listed}


def _adapter(paths: dict[str, Path], *, ohlcv_path: Path | None = None) -> HistoricalSubmitAdapter:
    return HistoricalSubmitAdapter(
        runtime_root=paths["base"].parents[5] / ".runtime",
        business_date=BUSINESS_DATE,
        evaluation_time=f"{BUSINESS_DATE}T08:00:00+09:00",
        historical_asof_view_path=paths["asof"],
        ohlcv_path=ohlcv_path or paths["normalized"],
        raw_ohlcv_path=paths["raw"],
        listed_issues_path=paths["listed"],
    )


def test_same_logical_content_different_physical_path_has_same_identity(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    copy_path = tmp_path / "copy" / "data.parquet"
    copy_path.parent.mkdir(parents=True)
    pd.read_parquet(paths["normalized"]).to_parquet(copy_path, index=False)

    expected = build_source_identity(paths["normalized"], logical_source_id="normalized_ohlcv", business_date=BUSINESS_DATE)
    actual = build_source_identity(copy_path, logical_source_id="normalized_ohlcv", business_date=BUSINESS_DATE)

    assert expected["content_hash"] == actual["content_hash"]
    assert expected["source_identity_hash"] == actual["source_identity_hash"]


def test_pending_bound_manifest_accepts_run_scoped_source_without_phase17_hash_fallback(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)

    result = _adapter(paths).preflight(_command())

    assert result.status == "DRY_RUN_READY"
    assert result.response_classification["source_identity_validation"]["mismatch_class"] == "NONE"
    assert result.response_classification["source_hash"] != "c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d"


def test_isolated_historical_submit_writes_simulated_evidence_without_broker_write(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    runtime_root = tmp_path / ".runtime"
    adapter = HistoricalSubmitAdapter(
        runtime_root=runtime_root,
        business_date=BUSINESS_DATE,
        evaluation_time=f"{BUSINESS_DATE}T08:00:00+09:00",
        historical_asof_view_path=paths["asof"],
        ohlcv_path=paths["normalized"],
        raw_ohlcv_path=paths["raw"],
        listed_issues_path=paths["listed"],
    )

    result = adapter.submit(_command())

    evidence_paths = list((runtime_root / "runtime_state" / "historical_broker" / BUSINESS_DATE).glob("*.json"))
    assert result.status == "ACCEPTED"
    assert result.broker_api_called is False
    assert evidence_paths
    evidence = json.loads(evidence_paths[0].read_text(encoding="utf-8"))
    assert evidence["broker_write"] is False
    assert evidence["simulation"] is True
    assert evidence["historical_replay"] is True
    assert evidence["source_identity"]["logical_source_id"] == "normalized_ohlcv"


def test_same_path_content_change_halts_with_content_mismatch(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "7203", "Open": 2600.0, "Close": 2600.0, "AdjFactor": 1.0}]).to_parquet(
        paths["normalized"],
        index=False,
    )

    result = _adapter(paths).preflight(_command())

    assert result.status == "HALT"
    assert result.response_classification["mismatch_class"] == "CONTENT_HASH_MISMATCH"


def test_raw_vs_normalized_source_halts_with_specific_class(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    pd.DataFrame([{"Date": BUSINESS_DATE, "Code": "7203", "Open": 2600.0, "Close": 2600.0, "AdjFactor": 1.0}]).to_parquet(
        paths["raw"],
        index=False,
    )

    result = _adapter(paths, ohlcv_path=paths["raw"]).preflight(_command())

    assert result.status == "HALT"
    assert result.response_classification["mismatch_class"] == "RAW_VS_NORMALIZED_MISMATCH"


def test_cross_run_source_rejected(tmp_path: Path) -> None:
    paths_a = _write_sources(tmp_path, run_id="run-a")
    paths_b = _write_sources(tmp_path, run_id="run-b")

    result = _adapter(paths_a, ohlcv_path=paths_b["normalized"]).preflight(_command())

    assert result.status == "HALT"
    assert result.response_classification["mismatch_class"] == "CROSS_RUN_SOURCE_REJECTION"


def test_business_date_mismatch_rejected(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    manifest["business_date"] = "2026-07-07"
    _write_json(paths["manifest"], manifest)

    result = _adapter(paths).preflight(_command())

    assert result.status == "HALT"
    assert result.response_classification["mismatch_class"] == "BUSINESS_DATE_MISMATCH"


def test_no_global_latest_fallback_when_bound_manifest_missing(tmp_path: Path) -> None:
    paths = _write_sources(tmp_path)
    paths["manifest"].unlink()
    global_latest = tmp_path / ".runtime" / "operations" / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    global_latest.parent.mkdir(parents=True)
    pd.read_parquet(paths["normalized"]).to_parquet(global_latest, index=False)

    result = _adapter(paths, ohlcv_path=global_latest).preflight(_command())

    assert result.status == "HALT"
    assert result.response_classification["mismatch_class"] == "BOUND_SOURCE_MANIFEST_MISSING"
    assert result.response_classification["actual_source_path"] == str(global_latest)
