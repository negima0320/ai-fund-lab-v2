"""Market / Quote Evidence producer for Runtime v2."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.runtime_v2.temporal import (
    FreshnessStatus,
    MarketTemporalState,
    PublicationWindow,
    evaluate_market_freshness,
    resolve_temporal_context,
)


MARKET_EVIDENCE_SCHEMA_VERSION = "runtime_v2_market_evidence_v1"
SUPPORTED_PRICE_TYPES = {
    "daily_close",
    "intraday_quote",
    "broker_valuation_price",
    "jquants_daily_quote",
}


@dataclass(frozen=True)
class MarketEvidenceProducerResult:
    status: str
    reason: str
    runtime_business_date: str
    market_date: str
    latest_expected_trading_date: str
    latest_available_market_date: str
    artifact_path: str
    latest_pointer_path: str
    history_artifact_path: str
    quote_count: int
    missing_quote_count: int
    quote_status: str
    market_summary_status: str
    market_freshness_status: str
    publication_status: str
    provider_status: str
    data_not_yet_available: bool
    stale: bool
    production_equivalent: bool

    def to_manifest_fields(self) -> dict[str, Any]:
        return {
            "market_evidence_status": self.status,
            "market_evidence_reason": self.reason,
            "market_evidence_path": self.artifact_path,
            "market_evidence_latest_pointer_path": self.latest_pointer_path,
            "market_evidence_history_artifact_path": self.history_artifact_path,
            "market_date": self.market_date,
            "latest_expected_trading_date": self.latest_expected_trading_date,
            "latest_available_market_date": self.latest_available_market_date,
            "market_freshness_status": self.market_freshness_status,
            "quote_status": self.quote_status,
            "quote_count": self.quote_count,
            "missing_quote_count": self.missing_quote_count,
            "publication_status": self.publication_status,
            "provider_status": self.provider_status,
            "market_summary_status": self.market_summary_status,
            "market_data_status": self.status,
        }

    def to_stage_details(self) -> dict[str, Any]:
        return asdict(self)


def produce_market_quote_evidence(
    *,
    runtime_root: Path | str,
    operations_root: Path | str,
    runtime_business_date: str,
    latest_available_market_date: str | None = None,
    mode: str = "demo",
    data_provider: str = "jquants",
    provider_status: str = "READY",
    publication_window: PublicationWindow | None = None,
    current_symbols: tuple[str, ...] = (),
    pending_symbols: tuple[str, ...] = (),
    candidate_symbols: tuple[str, ...] = (),
    quote_source_path: Path | str | None = None,
    source_authority: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> MarketEvidenceProducerResult:
    now_dt = now or datetime.now(timezone.utc)
    runtime_root_path = Path(runtime_root)
    operations_root_path = Path(operations_root)
    available_date = latest_available_market_date or _latest_available_daily_quote_date(operations_root_path)
    context = resolve_temporal_context(
        runtime_business_date=runtime_business_date,
        runtime_mode=mode,
        broker_environment=mode,
        latest_available_market_date=available_date or None,
        publication_window=publication_window,
        now=now_dt,
        root=_base_dir_for_runtime_root(runtime_root_path),
    )
    market_date = available_date or context.latest_available_market_date
    temporal = evaluate_market_freshness(
        context=context,
        actual_date=market_date or None,
        generated_at=now_dt.isoformat(),
        source=data_provider,
        now=now_dt,
    )
    quotes, missing_symbols, quote_source = _load_quotes(
        operations_root=operations_root_path,
        market_date=market_date,
        required_symbols=_required_symbols(current_symbols, pending_symbols),
        quote_source_path=quote_source_path,
    )
    if temporal.status in {FreshnessStatus.DATA_NOT_YET_AVAILABLE, FreshnessStatus.STALE}:
        quotes = []
    if temporal.status == FreshnessStatus.MISSING:
        provider_status = "MISSING"
    if provider_status not in {"READY", "DRY_RUN", "PARTIAL_AVAILABLE"}:
        status = FreshnessStatus.REVIEW_REQUIRED
        reason = f"market_provider_status:{provider_status}"
    elif temporal.status in {FreshnessStatus.READY, FreshnessStatus.VALID_CARRYOVER}:
        status = FreshnessStatus.READY if not missing_symbols else FreshnessStatus.REVIEW_REQUIRED
        reason = "market_evidence_ready" if not missing_symbols else "quote_missing_for_monitored_symbols"
    elif temporal.status == FreshnessStatus.DATA_NOT_YET_AVAILABLE:
        status = FreshnessStatus.DATA_NOT_YET_AVAILABLE
        reason = temporal.reason
    elif temporal.status == FreshnessStatus.STALE:
        status = FreshnessStatus.STALE
        reason = temporal.reason
    else:
        status = FreshnessStatus.REVIEW_REQUIRED
        reason = temporal.reason
    if not market_date:
        status = FreshnessStatus.REVIEW_REQUIRED
        reason = "market_date_missing"
    elif temporal.status in {FreshnessStatus.READY, FreshnessStatus.VALID_CARRYOVER} and not quotes:
        status = FreshnessStatus.REVIEW_REQUIRED
        reason = "quote_source_empty"
    quote_status = _quote_status(status=status, missing_symbols=missing_symbols, quotes=quotes)
    market_summary = _market_summary(
        market_date=market_date,
        quotes=quotes,
        missing_symbols=missing_symbols,
        summary_source=quote_source,
    )
    market_model = MarketTemporalState(
        market_date=market_date,
        latest_expected_trading_date=context.latest_expected_trading_date,
        latest_available_market_date=context.latest_available_market_date,
        publication_status=_publication_status(temporal.status),
        provider_status=provider_status,
    )
    authority = dict(source_authority or {})
    quote_source_authority = str(authority.get("quote_source_authority") or quote_source)
    source_business_date = str(authority.get("source_business_date") or runtime_business_date)
    logical_cutoff = str(authority.get("logical_cutoff") or market_date or runtime_business_date)
    payload = {
        "schema_version": MARKET_EVIDENCE_SCHEMA_VERSION,
        "runtime_business_date": runtime_business_date,
        "business_date": runtime_business_date,
        "market_date": market_date,
        "latest_expected_trading_date": context.latest_expected_trading_date,
        "latest_available_market_date": context.latest_available_market_date,
        "generated_at": now_dt.isoformat(),
        "calendar_source": context.calendar_source,
        "calendar_status": "READY",
        "trading_day": runtime_business_date == context.latest_expected_trading_date,
        "market_status": status.value,
        "market_freshness_status": temporal.status.value,
        "quote_status": quote_status,
        "market_summary": market_summary,
        "candidate_universe_market_summary": {
            "market_crash": False,
            "daily_loss_pct": "0",
            "summary_source": "market_evidence_no_crash_detector_configured",
        },
        "quotes": {quote["symbol"]: quote for quote in quotes},
        "data_provider": data_provider,
        "provider_status": provider_status,
        "data_not_yet_available": status == FreshnessStatus.DATA_NOT_YET_AVAILABLE,
        "stale": status == FreshnessStatus.STALE,
        "fallback_used": context.calendar_source == "fallback",
        "production_equivalent": mode == "production",
        "temporal_evidence": temporal.to_payload(),
        "market_temporal_model": market_model.to_payload(),
        "expected_publication_window": publication_window.to_payload() if publication_window else None,
        "current_time": now_dt.isoformat(),
        "publication_status": _publication_status(temporal.status),
        "monitored_symbols": sorted(_required_symbols(current_symbols, pending_symbols)),
        "candidate_universe_symbol_count": len(set(candidate_symbols)),
        "missing_quote_symbols": sorted(missing_symbols),
        "reason": reason,
        "quote_source": quote_source,
        "source_role": str(authority.get("source_role") or "operations_canonical"),
        "quote_source_authority": quote_source_authority,
        "source_business_date": source_business_date,
        "logical_cutoff": logical_cutoff,
        "historical_asof_status": str(authority.get("historical_asof_status") or ""),
        "historical_logical_input_manifest_path": str(authority.get("historical_logical_input_manifest_path") or ""),
        "historical_logical_input_manifest_hash": str(authority.get("historical_logical_input_manifest_hash") or ""),
        "future_rows_excluded": bool(authority.get("future_rows_excluded", False)),
        "source_authority": authority,
        "no_feature_artifact_price_derivation": True,
        "fake_or_default_quote_generated": False,
    }
    artifact_path, latest_path, history_path = _write_market_evidence(
        runtime_root=runtime_root_path,
        market_date=market_date or runtime_business_date,
        payload=payload,
    )
    return MarketEvidenceProducerResult(
        status=status.value,
        reason=reason,
        runtime_business_date=runtime_business_date,
        market_date=market_date,
        latest_expected_trading_date=context.latest_expected_trading_date,
        latest_available_market_date=context.latest_available_market_date,
        artifact_path=str(artifact_path),
        latest_pointer_path=str(latest_path),
        history_artifact_path=str(history_path),
        quote_count=len(quotes),
        missing_quote_count=len(missing_symbols),
        quote_status=quote_status,
        market_summary_status="READY" if market_summary else "REVIEW_REQUIRED",
        market_freshness_status=temporal.status.value,
        publication_status=_publication_status(temporal.status),
        provider_status=provider_status,
        data_not_yet_available=status == FreshnessStatus.DATA_NOT_YET_AVAILABLE,
        stale=status == FreshnessStatus.STALE,
        production_equivalent=mode == "production",
    )


def _load_quotes(
    *,
    operations_root: Path,
    market_date: str,
    required_symbols: set[str],
    quote_source_path: Path | str | None = None,
) -> tuple[list[dict[str, Any]], set[str], str]:
    source_path = Path(quote_source_path) if quote_source_path else operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    if not source_path.exists() or not market_date:
        return [], set(required_symbols), str(source_path)
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
    except Exception:
        return [], set(required_symbols), str(source_path)
    if frame.empty:
        return [], set(required_symbols), str(source_path)
    date_column = _first_column(frame, ("target_date", "Date", "date", "market_date"))
    code_column = _first_column(frame, ("code", "Code", "LocalCode", "symbol", "issue_code"))
    close_column = _first_column(frame, ("close", "Close", "AdjustmentClose", "adjustment_close", "price"))
    if not date_column or not code_column or not close_column:
        return [], set(required_symbols), str(source_path)
    rows = frame[frame[date_column].astype(str) == market_date].copy()
    if rows.empty:
        return [], set(required_symbols), str(source_path)
    quotes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows.to_dict(orient="records"):
        symbol = _normalize_symbol(str(row.get(code_column) or ""))
        if not symbol:
            continue
        if required_symbols and symbol not in required_symbols:
            continue
        price = row.get(close_column)
        if price is None:
            continue
        quotes.append(
            {
                "symbol": symbol,
                "price": float(price),
                "price_type": "jquants_daily_quote",
                "market_date": market_date,
                "observed_at": market_date,
                "source": str(source_path),
                "freshness_status": FreshnessStatus.READY.value,
                "adjusted": close_column.lower().startswith("adjust"),
                "age_seconds": 0,
                "stale": False,
            }
        )
        seen.add(symbol)
    missing = set(required_symbols) - seen
    return quotes, missing, str(source_path)


def _latest_available_daily_quote_date(operations_root: Path) -> str:
    source_path = operations_root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    if not source_path.exists():
        return ""
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path, columns=None)
    except Exception:
        return ""
    if frame.empty:
        return ""
    date_column = _first_column(frame, ("target_date", "Date", "date", "market_date"))
    if not date_column:
        return ""
    values = [str(value) for value in frame[date_column].dropna().tolist() if str(value)]
    return max(values) if values else ""


def _market_summary(*, market_date: str, quotes: list[dict[str, Any]], missing_symbols: set[str], summary_source: str) -> dict[str, Any]:
    return {
        "market_date": market_date,
        "symbol_count": len({quote["symbol"] for quote in quotes}),
        "quote_count": len(quotes),
        "missing_quote_count": len(missing_symbols),
        "market_crash": False,
        "summary_source": summary_source,
    }


def _quote_status(*, status: FreshnessStatus, missing_symbols: set[str], quotes: list[dict[str, Any]]) -> str:
    if status in {FreshnessStatus.DATA_NOT_YET_AVAILABLE, FreshnessStatus.STALE}:
        return status.value
    if missing_symbols:
        return FreshnessStatus.REVIEW_REQUIRED.value
    if quotes:
        return FreshnessStatus.READY.value
    return FreshnessStatus.NOT_REQUIRED.value


def _publication_status(status: FreshnessStatus) -> str:
    if status == FreshnessStatus.DATA_NOT_YET_AVAILABLE:
        return "DATA_NOT_YET_AVAILABLE"
    if status == FreshnessStatus.STALE:
        return "STALE_AFTER_PUBLICATION_WINDOW"
    if status == FreshnessStatus.VALID_CARRYOVER:
        return "VALID_CARRYOVER"
    if status == FreshnessStatus.READY:
        return "READY"
    return "REVIEW_REQUIRED"


def _write_market_evidence(*, runtime_root: Path, market_date: str, payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    market_root = runtime_root / "runtime_state" / "market"
    artifact_path = market_root / market_date / "market_evidence.json"
    latest_path = market_root / "latest.json"
    digest = _payload_hash(payload)
    history_path = market_root / "history" / market_date / f"{digest}.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        existing = json.loads(artifact_path.read_text(encoding="utf-8"))
        existing_digest = _payload_hash(existing)
        if existing_digest != digest:
            previous_path = market_root / "history" / market_date / f"{existing_digest}.json"
            previous_path.parent.mkdir(parents=True, exist_ok=True)
            if not previous_path.exists():
                shutil.copy2(artifact_path, previous_path)
    _write_json(artifact_path, payload)
    if not history_path.exists():
        _write_json(history_path, payload)
    latest = {
        "schema_version": "runtime_v2_market_evidence_latest_pointer_v1",
        "market_date": market_date,
        "artifact_path": str(artifact_path),
        "history_artifact_path": str(history_path),
        "market_status": payload.get("market_status"),
        "quote_status": payload.get("quote_status"),
        "generated_at": payload.get("generated_at"),
    }
    _write_json(latest_path, latest)
    return artifact_path, latest_path, history_path


def _required_symbols(current_symbols: tuple[str, ...], pending_symbols: tuple[str, ...]) -> set[str]:
    return {_normalize_symbol(symbol) for symbol in (*current_symbols, *pending_symbols) if _normalize_symbol(symbol)}


def _normalize_symbol(value: str) -> str:
    text = value.strip()
    if text.endswith(".T"):
        text = text[:-2]
    if text.endswith("0") and len(text) == 5:
        text = text[:-1]
    return text


def _first_column(frame: Any, candidates: tuple[str, ...]) -> str:
    columns = {str(column): str(column) for column in frame.columns}
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    lower = {str(column).lower(): str(column) for column in frame.columns}
    for candidate in candidates:
        match = lower.get(candidate.lower())
        if match:
            return match
    return ""


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _base_dir_for_runtime_root(runtime_root: Path) -> Path:
    return runtime_root.parent if runtime_root.name == ".runtime" else Path(".")
