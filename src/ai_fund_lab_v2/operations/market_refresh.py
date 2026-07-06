from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.operations.io import OperationPaths, read_json, stable_hash, utc_now_iso, write_json
from ai_fund_lab_v2.paper_trading.feature_refresh import run_feature_refresh
from ai_fund_lab_v2.paper_trading.market_data_refresh import run_market_data_refresh

DEFAULT_MAX_BUY_ORDERS_PER_DAY = 5
DEFAULT_MAX_POSITIONS = 5


def run_operations_market_refresh(
    *,
    trade_date: str,
    root: Path,
    allow_api_fetch: bool = False,
    from_date: str | None = None,
    fetch_mode: str = "per-date",
    fetcher: Any | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    start = from_date or _default_from_date(trade_date)
    raw_root = paths.root / "jquants" / "raw"
    normalized_root = paths.root / "jquants" / "raw_normalized"
    detail_root = paths.root / "jquants" / "market_data_refresh_detail"
    feature_artifact_root = paths.root / "feature_artifacts"
    market_detail = run_market_data_refresh(
        from_date=start,
        to_date=trade_date,
        dry_run=not allow_api_fetch,
        allow_api_fetch=allow_api_fetch,
        raw_output_root=raw_root,
        normalized_output_root=normalized_root,
        manifest_output_root=detail_root,
        backup_existing=False,
        fetch_mode=fetch_mode,
        fetcher=fetcher,
        markdown_report_path=paths.dated("market_refresh", trade_date, "market_data_refresh_detail.md"),
        json_report_path=paths.dated("market_refresh", trade_date, "market_data_refresh_detail.json"),
    )
    latest_available_market_date = _latest_available_market_date(market_detail.to_dict(), fallback=trade_date)
    feature_freshness_status = _feature_freshness_status(
        decision_for=trade_date,
        latest_available_market_date=latest_available_market_date,
        market_status=market_detail.status,
    )
    listed_info_for_feature = _listed_info_for_feature(
        raw_root / "jquants" / "listed_issues" / "data.parquet",
        feature_date=latest_available_market_date,
        output_path=paths.root / "feature_refresh" / trade_date / "jquants" / "listed_issues" / "listed_info_for_feature.parquet",
    )
    feature_detail = run_feature_refresh(
        target_data_until=latest_available_market_date,
        dry_run=not allow_api_fetch,
        execute=allow_api_fetch,
        daily_quotes_path=normalized_root / "jquants" / "equities_bars_daily" / "data.parquet",
        listed_info_path=listed_info_for_feature,
        feature_output_root=feature_artifact_root,
        manifest_root=paths.root / "feature_refresh_detail",
        markdown_report_path=paths.dated("feature_refresh", trade_date, "feature_refresh_detail.md"),
        json_report_path=paths.dated("feature_refresh", trade_date, "feature_refresh_detail.json"),
    )
    candidate = next((item for item in feature_detail.to_dict().get("artifacts", []) if item.get("ai_name") == "candidate"), {})
    feature_marker_path = paths.dated("feature_refresh", trade_date, "latest_features.json")
    feature_marker = {
        "artifact_type": "latest_feature_marker",
        "business_date": trade_date,
        "decision_for": trade_date,
        "data_until": latest_available_market_date,
        "latest_available_market_date": latest_available_market_date,
        "feature_freshness_status": feature_freshness_status,
        "sources": ["jquants_daily_quotes", "jquants_listed_info", "jquants_trading_calendar"],
        "jquants_only": True,
        "feature_schema_hash": candidate.get("feature_schema_hash") or stable_hash(feature_detail.to_dict()),
        "candidate_feature_path": candidate.get("artifact_path", ""),
        "feature_refresh_detail_manifest_path": feature_detail.manifest_path,
        "broker_snapshot_used_for_ai": False,
        "paper_ledger_used_for_ai": False,
        "safety_result_used_for_ai": False,
        "audit_result_used_for_ai": False,
        "cash_portfolio_pnl_used_for_ai": False,
    }
    write_json(feature_marker_path, feature_marker)
    market_ok_statuses = {
        "COMPLETED",
        "PARTIAL_AVAILABLE",
        "MARKET_DATA_READY_FOR_LATEST_AVAILABLE",
        "DRY_RUN",
    }
    feature_ok_statuses = {"FEATURES_READY", "FEATURE_REFRESH_REQUIRED"}
    blocked: list[str] = []
    if market_detail.status not in market_ok_statuses:
        market_blocks = [reason for reason in market_detail.blocked_reasons if reason != "data_until_before_decision_for"]
        if market_blocks:
            blocked.extend(market_blocks)
        elif market_detail.status not in {"PARTIAL", "PARTIAL_AVAILABLE", "MARKET_DATA_READY_FOR_LATEST_AVAILABLE"}:
            blocked.append(f"market_data_refresh_status:{market_detail.status}")
    if feature_detail.status not in feature_ok_statuses:
        blocked.extend(feature_detail.blocked_reasons or (f"feature_refresh_status:{feature_detail.status}",))
    status = "PASS" if not blocked else "BLOCK"
    if status != "PASS":
        data_quality_status = "BLOCK"
    elif feature_freshness_status == "FEATURE_READY":
        data_quality_status = "PASS"
    else:
        data_quality_status = "REVIEW_REQUIRED"
    return {
        "status": status,
        "blocked_reasons": list(dict.fromkeys(blocked)),
        "data_quality_status": data_quality_status,
        "decision_for": trade_date,
        "latest_available_market_date": latest_available_market_date,
        "feature_freshness_status": feature_freshness_status,
        "data_until": latest_available_market_date,
        "jquants_api_fetch_executed": market_detail.jquants_api_fetch_executed,
        "raw_daily_quotes_updated": _endpoint_updated(market_detail.to_dict(), "daily_quotes"),
        "listed_info_updated": _endpoint_updated(market_detail.to_dict(), "listed_info"),
        "trading_calendar_updated": _endpoint_updated(market_detail.to_dict(), "trading_calendar"),
        "canonical_normalized_updated": bool(market_detail.latest_normalized_daily_quotes_date),
        "feature_refresh_executed": feature_detail.feature_generation_executed,
        "feature_refresh_status": feature_detail.status,
        "feature_artifact_path": str(feature_marker_path),
        "candidate_feature_path": candidate.get("artifact_path", ""),
        "listed_info_for_feature_path": str(listed_info_for_feature),
        "market_data_refresh_detail": market_detail.to_dict(),
        "feature_refresh_detail": feature_detail.to_dict(),
        "created_at": utc_now_iso(),
    }


def load_feature_buy_candidates(
    *,
    root: Path,
    trade_date: str,
    max_items: int = DEFAULT_MAX_BUY_ORDERS_PER_DAY,
    candidate_pool_size: int | None = None,
) -> dict[str, Any]:
    paths = OperationPaths(root)
    max_items = max(0, int(max_items))
    pool_limit = max_items if candidate_pool_size is None else max(max_items, int(candidate_pool_size))
    marker_path = paths.dated("feature_refresh", trade_date, "latest_features.json")
    if not marker_path.exists():
        return {"status": "NO_FEATURE_MARKER", "buy_items": [], "reason": "feature_marker_missing"}
    marker = read_json(marker_path)
    diagnostics = feature_candidate_diagnostics(root=root, trade_date=trade_date)
    freshness = str(marker.get("feature_freshness_status") or "")
    if freshness and freshness not in {"FEATURE_READY", "MARKET_DATA_NOT_YET_AVAILABLE"}:
        return {**diagnostics, "status": freshness, "buy_items": [], "reason": freshness.lower(), "candidate_feature_path": str(marker.get("candidate_feature_path") or "")}
    candidate_path_text = str(marker.get("candidate_feature_path") or "")
    if not candidate_path_text:
        return {**diagnostics, "status": "NO_FEATURE_ARTIFACT", "buy_items": [], "reason": "candidate_feature_path_missing", "candidate_feature_path": ""}
    candidate_path = Path(candidate_path_text)
    if not candidate_path.exists():
        return {**diagnostics, "status": "NO_FEATURE_ARTIFACT", "buy_items": [], "reason": "candidate_feature_path_missing", "candidate_feature_path": str(candidate_path)}
    try:
        import pandas as pd

        frame = pd.read_parquet(candidate_path)
    except Exception as exc:  # noqa: BLE001 - fail closed summary.
        return {**diagnostics, "status": "FEATURE_ARTIFACT_UNREADABLE", "buy_items": [], "reason": type(exc).__name__, "candidate_feature_path": str(candidate_path)}
    if frame.empty:
        return {
            **diagnostics,
            "status": "NO_SIGNAL",
            "buy_items": [],
            "reason": "candidate_feature_empty",
            "candidate_feature_path": str(candidate_path),
            "max_buy_orders_per_day": max_items,
            "max_items_source": "operations_runtime_config",
        }
    universe_rows_before_gate = int(len(frame))
    if "universe_eligible" in frame.columns:
        frame = frame[frame["universe_eligible"].fillna(False).astype(bool)].copy()
    universe_rows_after_gate = int(len(frame))
    if frame.empty:
        return {
            **diagnostics,
            "status": "NO_SIGNAL",
            "buy_items": [],
            "reason": "candidate_no_universe_eligible_rows",
            "candidate_feature_path": str(candidate_path),
            "universe_rows_before_gate": universe_rows_before_gate,
            "universe_rows_after_gate": universe_rows_after_gate,
            "candidate_count": 0,
            "max_buy_orders_per_day": max_items,
            "max_items_source": "operations_runtime_config",
        }
    sort_cols = [col for col in ("price_momentum_return_20d", "price_momentum_return_5d", "liquidity_avg_volume_20d") if col in frame.columns]
    if sort_cols:
        frame = frame.sort_values(sort_cols, ascending=[False] * len(sort_cols))
    items = []
    for index, row in enumerate(frame.head(pool_limit).to_dict(orient="records"), start=1):
        code = str(row.get("code") or row.get("issue_code") or "")
        if not code:
            continue
        items.append(
            {
                "item_id": f"buy_{trade_date}_{code}_{index:03d}",
                "issue_code": code,
                "code": code,
                "side": "BUY",
                "quantity": "100",
                "order_type": "CASH_EQUITY",
                "price_type": "LIMIT",
                "limit_price": "0",
                "estimated_value": "0",
                "expected_notional": "0",
                "source": "operations_feature_buy_candidate",
                "feature_snapshot_path": str(candidate_path),
                "approval_required": True,
                "production_order_allowed": False,
                "demo_order_allowed": False,
            }
        )
    return {
        **diagnostics,
        "status": "PASS" if items else "NO_SIGNAL",
        "buy_items": items,
        "reason": "" if items else "candidate_rows_missing_code",
        "candidate_feature_path": str(candidate_path),
        "universe_rows_before_gate": universe_rows_before_gate,
        "universe_rows_after_gate": universe_rows_after_gate,
        "candidate_count": universe_rows_after_gate,
        "selected_buy_count": len(items),
        "max_buy_orders_per_day": max_items,
        "candidate_pool_size": pool_limit,
        "max_positions": DEFAULT_MAX_POSITIONS,
        "max_items_source": "operations_runtime_config",
    }


def feature_candidate_diagnostics(*, root: Path, trade_date: str) -> dict[str, Any]:
    paths = OperationPaths(root)
    marker_path = paths.dated("feature_refresh", trade_date, "latest_features.json")
    marker = read_json(marker_path) if marker_path.exists() else {}
    candidate_path = Path(str(marker.get("candidate_feature_path") or ""))
    data_until = str(marker.get("data_until") or "")
    opportunity_path = candidate_path.parent / "opportunity_feature_input.parquet" if str(candidate_path) else Path("")
    raw_path = paths.root / "jquants" / "raw" / "jquants" / "equities_bars_daily" / "data.parquet"
    normalized_path = paths.root / "jquants" / "raw_normalized" / "jquants" / "equities_bars_daily" / "data.parquet"
    candidate_frame = _read_parquet_or_empty(candidate_path)
    opportunity_frame = _read_parquet_or_empty(opportunity_path)
    eligible = 0
    if not candidate_frame.empty and "universe_eligible" in candidate_frame.columns:
        eligible = int(candidate_frame["universe_eligible"].fillna(False).astype(bool).sum())
    exclusion_counts = {}
    for column in ("universe_exclusion_reason", "excluded_reason"):
        if column in candidate_frame.columns:
            exclusion_counts = candidate_frame[column].fillna("").astype(str).value_counts().head(20).to_dict()
            break
    return {
        "feature_path_audited": True,
        "candidate_path_audited": True,
        "jquants_raw_rows": _parquet_row_count(raw_path),
        "normalized_rows": _parquet_row_count(normalized_path),
        "feature_rows": int(len(candidate_frame)) if candidate_path.exists() else 0,
        "feature_data_until": data_until,
        "candidate_feature_path": str(candidate_path) if str(candidate_path) else "",
        "opportunity_feature_path": str(opportunity_path) if str(opportunity_path) else "",
        "universe_rows_before_gate": int(len(candidate_frame)) if candidate_path.exists() else 0,
        "universe_rows_after_gate": eligible,
        "candidate_count": eligible,
        "opportunity_count": int(len(opportunity_frame)) if opportunity_path.exists() else 0,
        "universe_exclusion_reason_counts": exclusion_counts,
    }


def _default_from_date(trade_date: str) -> str:
    return (date.fromisoformat(trade_date) - timedelta(days=140)).isoformat()


def _endpoint_updated(payload: dict[str, Any], endpoint: str) -> bool:
    for item in payload.get("endpoints") or []:
        if item.get("endpoint") == endpoint:
            return int(item.get("fetched_row_count") or 0) > 0
    return False


def _latest_available_market_date(payload: dict[str, Any], *, fallback: str) -> str:
    candidates = [
        str(payload.get("latest_normalized_daily_quotes_date") or ""),
        str(payload.get("latest_successful_daily_quotes_date") or ""),
        str(payload.get("data_until") or ""),
    ]
    present = [item for item in candidates if item]
    return max(present) if present else fallback


def _feature_freshness_status(*, decision_for: str, latest_available_market_date: str, market_status: str) -> str:
    if not latest_available_market_date:
        return "FEATURE_MISSING"
    if market_status in {"FETCH_FAILED", "FAILED", "BLOCKED", "API_PARAM_ERROR"}:
        return "MARKET_DATA_NOT_YET_AVAILABLE"
    if latest_available_market_date > decision_for:
        return "FEATURE_STALE"
    return "FEATURE_READY"


def _listed_info_for_feature(source_path: Path, *, feature_date: str, output_path: Path) -> Path:
    if not source_path.exists():
        return source_path
    try:
        import pandas as pd

        frame = pd.read_parquet(source_path)
        if frame.empty:
            return source_path
        output = frame.copy()
        if "Date" in output.columns:
            output["Date"] = feature_date
        if "target_date" in output.columns:
            output["target_date"] = feature_date
        elif "Date" in output.columns:
            output["target_date"] = output["Date"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output.to_parquet(output_path, index=False)
        return output_path
    except Exception:
        return source_path


def _parquet_row_count(path: Path) -> int:
    frame = _read_parquet_or_empty(path)
    return int(len(frame))


def _read_parquet_or_empty(path: Path):
    import pandas as pd

    if not path or not str(path) or not path.exists() or path.is_dir():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path)
    except Exception:
        return pd.DataFrame()
