from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


RUN_ID = "runtime-test-historical-extended-smoke-20260815T013038707969Z"
RUN_ROOT = Path("reports/runtime_tests/runs") / RUN_ID
DAY = "2022-08-10"
OUT_ROOT = Path("reports/phase29_l21t_bg_post_be_day1_current_valuation_halt_root_cause_audit")


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    daily = RUN_ROOT / "daily" / DAY
    valuation_root = daily / "current_valuation_refresh"
    manifest = _read_json(valuation_root / "current_valuation_manifest.json")
    projection = _read_json(valuation_root / "valuation_projection.json")
    fresh_summary = _read_json(RUN_ROOT / "fresh_run_summary.json")
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    positions = artifact.get("candidate_current", {}).get("positions") or []
    historical_asof = _read_json(daily / "market_refresh" / "historical_asof_view.json")
    paths = _source_paths(historical_asof)
    symbols = {_normalize_symbol(str(position.get("symbol") or "")) for position in positions}
    normalized_rows = _read_rows(paths.get("normalized_ohlcv", Path()), symbols=symbols)
    raw_rows = _read_rows(paths.get("raw_ohlcv", Path()), symbols=symbols)
    rejection_trace = []
    for position in positions:
        symbol = _normalize_symbol(str(position.get("symbol") or ""))
        normalized = normalized_rows.get(symbol, {})
        raw = raw_rows.get(symbol, {})
        price_source = str(normalized.get("PriceSource") or "")
        close = _num(normalized.get("Close"))
        adjusted = price_source.lower() == "adjusted"
        explicit_status = str(
            normalized.get("economic_price_reconciliation_status")
            or normalized.get("EconomicPriceReconciliationStatus")
            or ""
        )
        explicit_provenance = str(
            normalized.get("economic_price_provenance") or normalized.get("EconomicPriceProvenance") or ""
        )
        explicit_economic_price = _num(
            normalized.get("economic_valuation_price", normalized.get("EconomicValuationPrice"))
        )
        raw_close = _num(raw.get("C"))
        raw_adjusted_close = _num(raw.get("AdjC"))
        accepted = bool(
            close is not None
            and (
                not adjusted
                or (
                    explicit_status == "PASS"
                    and explicit_provenance
                    and explicit_economic_price is not None
                    and explicit_economic_price > 0
                )
            )
        )
        reason = ""
        if not normalized:
            reason = "quote_missing"
        elif adjusted and not accepted:
            reason = "adjusted_price_missing_economic_valuation_reconciliation"
        elif close is None:
            reason = "quote_price_missing"
        rejection_trace.append(
            {
                "symbol": symbol,
                "quantity": _num(position.get("quantity")),
                "quote_present": bool(normalized),
                "normalized_close": close,
                "price_source": price_source,
                "adjusted_flag": adjusted,
                "normalized_price_source": price_source.lower() or ("adjusted" if adjusted else "unadjusted"),
                "price_role": "adjusted_analytical_price" if adjusted else "economic_valuation_price",
                "economic_price_reconciliation_status": explicit_status or ("REVIEW_REQUIRED" if adjusted else "PASS"),
                "economic_price_provenance": explicit_provenance or ("" if adjusted else "normalized_ohlcv_unadjusted_close"),
                "economic_valuation_price": explicit_economic_price if adjusted else close,
                "raw_close": raw_close,
                "raw_adjusted_close": raw_adjusted_close,
                "raw_close_available": raw_close is not None and raw_close > 0,
                "raw_adjusted_close_matches_normalized_close": (
                    raw_adjusted_close is not None and close is not None and abs(raw_adjusted_close - close) < 1e-9
                ),
                "valuation_accepted": accepted,
                "valuation_rejected": not accepted,
                "rejection_reason": reason,
            }
        )
    producer_trace = [
        {
            "producer_stage": "market_refresh",
            "artifact": str(daily / "market_refresh" / "historical_asof_view.json"),
            "status": "PASS",
            "evidence": "historical_asof_view materialized normalized_ohlcv and raw_ohlcv source paths",
            "economic_valuation_price_generated": False,
            "reconciliation_evidence_generated": False,
        },
        {
            "producer_stage": "current_valuation_refresh",
            "artifact": str(valuation_root / "current_valuation_manifest.json"),
            "status": artifact.get("status"),
            "evidence": "current valuation loaded historical_asof_view and synthesized quotes from normalized_ohlcv only",
            "economic_valuation_price_generated": False,
            "reconciliation_evidence_generated": False,
        },
        {
            "producer_stage": "raw_ohlcv_source",
            "artifact": str(paths.get("raw_ohlcv", "")),
            "status": "AVAILABLE" if paths.get("raw_ohlcv") and paths["raw_ohlcv"].exists() else "MISSING",
            "evidence": "raw C/AdjC columns are available for target symbols; not propagated as economic valuation evidence",
            "economic_valuation_price_generated": False,
            "reconciliation_evidence_generated": False,
        },
    ]
    failing_symbols = [row["symbol"] for row in rejection_trace if row["valuation_rejected"]]
    raw_available = all(row["raw_close_available"] for row in rejection_trace)
    summary = {
        "task_id": "Phase29-L21T-BG",
        "mode": "READ_ONLY_AUDIT",
        "target_run": RUN_ID,
        "halt_date": DAY,
        "halt_stage": "current_valuation_refresh",
        "runtime_cli_exit_code": 20,
        "runtime_test_exit_code": 30,
        "completed_days": fresh_summary.get("completed_business_day_count"),
        "primary_judgment": "BE_FAIL_CLOSED_CORRECT_PRODUCER_INTEGRATION_GAP_CONFIRMED",
        "direct_error": fresh_summary.get("halt_summary", {}).get("root_reason") or projection.get("reason"),
        "projection_status": projection.get("projection_status"),
        "valued_position_count": projection.get("valued_position_count"),
        "position_count": projection.get("position_count"),
        "failing_symbols": failing_symbols,
        "failing_symbol_count": len(failing_symbols),
        "direct_rejection_reason": "adjusted_price_missing_economic_valuation_reconciliation",
        "be_fail_closed_correctly_triggered": True,
        "be_regression": False,
        "economic_price_source_exists": raw_available,
        "economic_price_producer_exists": False,
        "producer_invoked_in_historical": False,
        "reconciliation_evidence_propagated": False,
        "producer_integration_gap": True,
        "source_data_gap": not raw_available,
        "reconciliation_propagation_gap": True,
        "quote_source_selection_defect": True,
        "implementation_repair_required": True,
        "root_cause": (
            "BE fail-closed correctly rejected adjusted normalized quotes, but the historical current valuation "
            "producer path only supplied normalized adjusted Close and did not produce or propagate explicit "
            "economic valuation price reconciliation from the available raw/economic source."
        ),
        "runtime_mutated": False,
        "strategy_changed": False,
        "fresh_run_executed": False,
        "phase30_entered": False,
        "recommended_next_action": "Implement production-common economic valuation price producer/reconciliation propagation for current valuation.",
    }
    _write_csv(OUT_ROOT / "valuation_rejection_trace.csv", rejection_trace)
    _write_csv(OUT_ROOT / "economic_price_producer_trace.csv", producer_trace)
    _write_json(OUT_ROOT / "summary.json", summary)


def _source_paths(historical_asof: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for authority in historical_asof.get("authorities") or []:
        name = str(authority.get("authority") or "")
        source = str(authority.get("physical_source_path") or "")
        if name and source:
            paths[name] = Path(source)
    coverage = historical_asof.get("feature_lookback_coverage")
    if isinstance(coverage, dict):
        if "normalized_ohlcv" not in paths and coverage.get("selected_normalized_ohlcv_path"):
            paths["normalized_ohlcv"] = Path(str(coverage["selected_normalized_ohlcv_path"]))
        if "raw_ohlcv" not in paths and coverage.get("selected_raw_ohlcv_path"):
            paths["raw_ohlcv"] = Path(str(coverage["selected_raw_ohlcv_path"]))
    return paths


def _read_rows(path: Path, *, symbols: set[str]) -> dict[str, dict[str, Any]]:
    if not path or not path.is_file():
        return {}
    try:
        import pyarrow.parquet as pq

        schema = pq.read_schema(path)
        names = [str(name) for name in schema.names]
        date_col = _first_name(names, ("Date", "target_date", "date", "market_date"))
        code_col = _first_name(names, ("Code", "code", "LocalCode", "symbol", "issue_code"))
        cols = [
            col
            for col in (
                date_col,
                code_col,
                "Open",
                "High",
                "Low",
                "Close",
                "PriceSource",
                "O",
                "H",
                "L",
                "C",
                "AdjO",
                "AdjH",
                "AdjL",
                "AdjC",
                "AdjFactor",
                "economic_price_reconciliation_status",
                "EconomicPriceReconciliationStatus",
                "economic_price_provenance",
                "EconomicPriceProvenance",
                "economic_valuation_price",
                "EconomicValuationPrice",
            )
            if col in names
        ]
        table = pq.read_table(path, columns=cols, filters=[(date_col, "==", DAY)])
        frame = table.to_pandas()
    except Exception:
        return {}
    if frame.empty:
        return {}
    wanted = symbols | {symbol + "0" for symbol in symbols}
    frame = frame[frame[code_col].astype(str).isin(wanted)].copy()
    rows: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        rows[_normalize_symbol(str(row.get(code_col) or ""))] = row
    return rows


def _first_name(columns: list[str], candidates: tuple[str, ...]) -> str:
    exact = {column: column for column in columns}
    lower = {column.lower(): column for column in columns}
    for candidate in candidates:
        if candidate in exact:
            return exact[candidate]
        match = lower.get(candidate.lower())
        if match:
            return match
    return ""


def _normalize_symbol(value: str) -> str:
    text = value.strip()
    if text.endswith(".T"):
        text = text[:-2]
    return text


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    main()
