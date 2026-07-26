from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from ai_fund_lab_v2.opportunity_ai.market_sector_completion import build_market_sector_features
from ai_fund_lab_v2.paper_trading.canonical_data_source import DEFAULT_CONFIG_PATH, resolve_data_source
from ai_fund_lab_v2.runtime_v2.current_position_authority import resolve_current_position_authority


FEATURES_READY = "FEATURES_READY"
FEATURE_REFRESH_REQUIRED = "FEATURE_REFRESH_REQUIRED"
FEATURE_SCHEMA_REVIEW_REQUIRED = "FEATURE_SCHEMA_REVIEW_REQUIRED"
FEATURE_REFRESH_FAILED = "FEATURE_REFRESH_FAILED"

AI_NAMES = ("candidate", "opportunity", "position", "capital")

DEFAULT_DAILY_QUOTES_PATH = Path(".runtime/data/raw_normalized/jquants/equities_bars_daily/data.parquet")
DEFAULT_LISTED_INFO_PATH = Path(".runtime/data/raw/jquants/listed_issues/data.parquet")
DEFAULT_FEATURE_OUTPUT_ROOT = Path(".runtime/phase9/features")
DEFAULT_MANIFEST_ROOT = Path(".runtime/phase9/feature_refresh")
DEFAULT_MD_REPORT = Path("docs/phase_reports/phase9j_feature_refresh_report.md")
DEFAULT_JSON_REPORT = Path("reports/phase_reports/phase9j_feature_refresh_report.json")

ARTIFACT_FILENAMES = {
    "candidate": "candidate_features.parquet",
    "opportunity": "opportunity_feature_input.parquet",
    "position": "position_feature_input.parquet",
    "capital": "capital_policy_input.parquet",
}

OPPORTUNITY_MODEL_INPUT_COLUMNS = (
    "liquidity_avg_volume_20d",
    "market_breadth_20d",
    "market_breadth_5d",
    "market_downtrend_context",
    "market_downtrend_flag",
    "market_ma_5_20_ratio",
    "market_return_20d",
    "market_return_5d",
    "market_risk_flag",
    "market_volatility_20d",
    "missing_flags_insufficient_history",
    "missing_flags_price",
    "missing_flags_volume",
    "price_momentum_return_20d",
    "price_momentum_return_5d",
    "price_momentum_return_60d",
    "sector_breadth_20d",
    "sector_momentum_flag",
    "sector_rank_20d",
    "sector_return_20d",
    "sector_return_5d",
    "sector_weak_flag",
    "stock_vs_sector_return_20d",
    "trend_close_over_ma_20d",
    "trend_ma_20_60_ratio",
    "trend_ma_5_20_ratio",
    "volatility_return_std_20d",
    "volume_momentum_ratio_1d_20d",
    "volume_momentum_ratio_5d",
)

REQUIRED_COLUMNS = {
    "candidate": (
        "target_date",
        "as_of_date",
        "code",
        "feature_version",
        "source_snapshot_id",
        "feature_set_name",
        "missing_flags_insufficient_history",
        "missing_flags_price",
        "missing_flags_volume",
        "price_momentum_return_5d",
        "price_momentum_return_20d",
        "price_momentum_return_60d",
        "volume_momentum_ratio_5d",
        "volume_momentum_ratio_1d_20d",
        "volatility_return_std_20d",
        "trend_close_over_ma_20d",
        "trend_ma_5_20_ratio",
        "trend_ma_20_60_ratio",
        "liquidity_avg_volume_20d",
        "is_current_listed",
        "has_current_name",
        "is_fresh_price",
        "product_category",
        "market_name",
        "is_allowed_product",
        "universe_exclusion_reason",
    ),
    "opportunity": (
        "target_date",
        "as_of_date",
        "code",
        "feature_version",
        *OPPORTUNITY_MODEL_INPUT_COLUMNS,
    ),
    "position": (
        "target_date",
        "feature_as_of_date",
        "position_state_as_of",
        "entry_date",
        "code",
        "broker_issue_code",
        "holding_days",
        "average_price",
        "current_price",
        "unrealized_return",
        "quantity",
        "price_momentum_return_5d",
        "price_momentum_return_20d",
        "trend_close_over_ma_20d",
        "trend_ma_5_20_ratio",
        "volume_momentum_ratio_5d",
        "volatility_return_std_20d",
        "feature_source_artifact",
        "feature_source_hash",
        "required_features",
        "optional_features",
        "missing_features",
        "defaulted_features",
        "temporal_validation_status",
        "feature_version",
        "data_until",
        "created_at",
    ),
    "capital": (
        "target_date",
        "code",
        "policy_input_type",
        "feature_version",
        "source_candidate_feature_path",
        "source_opportunity_feature_path",
        "source_position_feature_path",
    ),
}

ALLOWED_PHASE9_PRODUCT_CATEGORIES = {"011", "021"}
ALLOWED_PHASE9_MARKETS = {"プライム", "スタンダード", "グロース"}


@dataclass(frozen=True)
class FeatureArtifactStatus:
    ai_name: str
    status: str
    artifact_path: str = ""
    row_count: int = 0
    min_date: str = ""
    max_date: str = ""
    data_until: str = ""
    feature_schema_hash: str = ""
    required_columns_status: str = "UNKNOWN"
    future_leakage_check_status: str = "UNKNOWN"
    source_data_refs: dict[str, str] | None = None
    output_artifact_refs: dict[str, str] | None = None
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        payload["source_data_refs"] = self.source_data_refs or {}
        payload["output_artifact_refs"] = self.output_artifact_refs or {}
        return payload


@dataclass(frozen=True)
class FeatureRefreshResult:
    status: str
    run_id: str
    target_data_until: str
    dry_run: bool
    execute: bool
    manifest_path: str
    markdown_report_path: str
    json_report_path: str
    artifacts: tuple[FeatureArtifactStatus, ...]
    warnings: tuple[str, ...] = ()
    blocked_reasons: tuple[str, ...] = ()
    feature_generation_executed: bool = False
    model_retraining_executed: bool = False
    inference_executed: bool = False
    order_plan_generation_executed: bool = False
    broker_order_api_called: bool = False
    open_d_started: bool = False
    unlock_trade_called: bool = False
    paper_ledger_fill_executed: bool = False
    virtual_fill_executed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = [artifact.to_dict() for artifact in self.artifacts]
        payload["warnings"] = list(self.warnings)
        payload["blocked_reasons"] = list(self.blocked_reasons)
        return payload


def run_feature_refresh(
    *,
    target_data_until: str,
    dry_run: bool = True,
    execute: bool = False,
    daily_quotes_path: Path | str | None = None,
    listed_info_path: Path | str | None = None,
    config_path: Path | str = DEFAULT_CONFIG_PATH,
    feature_output_root: Path | str = DEFAULT_FEATURE_OUTPUT_ROOT,
    manifest_root: Path | str = DEFAULT_MANIFEST_ROOT,
    markdown_report_path: Path | str = DEFAULT_MD_REPORT,
    json_report_path: Path | str = DEFAULT_JSON_REPORT,
    created_at: str | None = None,
    runtime_root: Path | str | None = None,
) -> FeatureRefreshResult:
    if dry_run and execute:
        raise ValueError("dry_run and execute cannot both be true.")
    created_at = created_at or _now()
    run_id = f"phase9j_feature_refresh_{created_at.replace(':', '').replace('+', 'Z')}"
    quotes_ref = resolve_data_source(
        "normalized_daily_quotes",
        override_path=daily_quotes_path,
        config_path=config_path,
        allow_fallback=False,
    )
    listed_ref = resolve_data_source(
        "listed_info",
        override_path=listed_info_path,
        config_path=config_path,
        allow_fallback=False,
    )
    quotes_path = Path(quotes_ref.path) if quotes_ref.path else Path("")
    listed_path = Path(listed_ref.path) if listed_ref.path else Path("")
    feature_root = Path(feature_output_root) / target_data_until
    manifest_path = Path(manifest_root) / target_data_until / "feature_refresh_manifest.json"
    md_path = Path(markdown_report_path)
    json_path = Path(json_report_path)
    source_refs = {
        "normalized_daily_quotes": str(quotes_path),
        "listed_info": str(listed_path),
        "normalized_daily_quotes_resolution": quotes_ref.to_dict(),
        "listed_info_resolution": listed_ref.to_dict(),
    }

    warnings: list[str] = []
    blocked: list[str] = []
    artifacts: list[FeatureArtifactStatus]
    source_blocked = list(quotes_ref.blocked_reasons) + list(listed_ref.blocked_reasons)
    if source_blocked:
        artifacts = [
            FeatureArtifactStatus(
                ai_name=ai_name,
                status=FEATURE_REFRESH_FAILED,
                source_data_refs=source_refs,
                blocked_reasons=tuple(source_blocked),
            )
            for ai_name in AI_NAMES
        ]
    else:
        try:
            if execute:
                artifacts = _execute_refresh(
                    target_data_until=target_data_until,
                    quotes_path=quotes_path,
                    listed_path=listed_path,
                    feature_root=feature_root,
                    source_refs=source_refs,
                    created_at=created_at,
                    runtime_root=Path(runtime_root) if runtime_root is not None else None,
                )
            else:
                artifacts = _audit_existing(
                    target_data_until=target_data_until,
                    feature_root=feature_root,
                    source_refs=source_refs,
                )
        except Exception as exc:  # pragma: no cover - fail closed report path
            artifacts = []
            blocked.append(f"feature_refresh_failed:{type(exc).__name__}")
            warnings.append(str(exc))

    blocked.extend(reason for artifact in artifacts for reason in artifact.blocked_reasons)
    warnings.extend(warning for artifact in artifacts for warning in artifact.warnings)
    status = _overall_status(artifacts=artifacts, blocked=blocked)
    result = FeatureRefreshResult(
        status=status,
        run_id=run_id,
        target_data_until=target_data_until,
        dry_run=dry_run,
        execute=execute,
        manifest_path=str(manifest_path),
        markdown_report_path=str(md_path),
        json_report_path=str(json_path),
        artifacts=tuple(artifacts),
        warnings=tuple(dict.fromkeys(warnings)),
        blocked_reasons=tuple(dict.fromkeys(blocked)),
        feature_generation_executed=bool(execute and status != FEATURE_REFRESH_FAILED),
    )
    _write_outputs(result=result, manifest_path=manifest_path, markdown_path=md_path, json_path=json_path, created_at=created_at)
    return result


def _execute_refresh(
    *,
    target_data_until: str,
    quotes_path: Path,
    listed_path: Path,
    feature_root: Path,
    source_refs: dict[str, str],
    created_at: str,
    runtime_root: Path | None,
) -> list[FeatureArtifactStatus]:
    quotes = _read_table(quotes_path)
    if quotes.empty:
        return [
            FeatureArtifactStatus(
                ai_name=ai_name,
                status=FEATURE_REFRESH_FAILED,
                source_data_refs=source_refs,
                blocked_reasons=("normalized_daily_quotes_missing_or_empty",),
            )
            for ai_name in AI_NAMES
        ]
    quotes = quotes[quotes["target_date"].astype(str) <= target_data_until].copy()
    if quotes.empty or str(quotes["target_date"].max()) < target_data_until:
        return [
            FeatureArtifactStatus(
                ai_name=ai_name,
                status=FEATURE_REFRESH_REQUIRED,
                source_data_refs=source_refs,
                blocked_reasons=("normalized_daily_quotes_before_target_data_until",),
            )
            for ai_name in AI_NAMES
        ]
    listed = _read_table(listed_path) if listed_path.is_file() else pd.DataFrame()
    listed = _latest_listed_snapshot(listed, target_data_until=target_data_until)

    candidate = _build_candidate_feature_frame(
        quotes=quotes,
        listed=listed,
        target_data_until=target_data_until,
        created_at=created_at,
    )
    opportunity = _build_opportunity_feature_input(
        candidate=candidate,
        listed=listed,
        target_data_until=target_data_until,
        created_at=created_at,
    )
    position = _build_position_feature_input(
        target_data_until=target_data_until,
        created_at=created_at,
        runtime_root=runtime_root,
        quotes=quotes,
        candidate=candidate,
        candidate_source_path=feature_root / ARTIFACT_FILENAMES["candidate"],
    )
    capital = _build_capital_policy_input(
        target_data_until=target_data_until,
        candidate_path=feature_root / ARTIFACT_FILENAMES["candidate"],
        opportunity_path=feature_root / ARTIFACT_FILENAMES["opportunity"],
        position_path=feature_root / ARTIFACT_FILENAMES["position"],
        created_at=created_at,
    )
    frames = {
        "candidate": candidate,
        "opportunity": opportunity,
        "position": position,
        "capital": capital,
    }

    feature_root.mkdir(parents=True, exist_ok=True)
    statuses: list[FeatureArtifactStatus] = []
    for ai_name, frame in frames.items():
        artifact_path = feature_root / ARTIFACT_FILENAMES[ai_name]
        frame.to_parquet(artifact_path, index=False)
        status = _inspect_artifact(
            ai_name=ai_name,
            path=artifact_path,
            target_data_until=target_data_until,
            source_refs={
                **source_refs,
                "listed_info_row_count": str(len(listed)),
            },
            runtime_root=runtime_root,
        )
        statuses.append(status)
    return statuses


def _audit_existing(*, target_data_until: str, feature_root: Path, source_refs: dict[str, str]) -> list[FeatureArtifactStatus]:
    return [
        _inspect_artifact(
            ai_name=ai_name,
            path=feature_root / ARTIFACT_FILENAMES[ai_name],
            target_data_until=target_data_until,
            source_refs=source_refs,
            runtime_root=None,
        )
        for ai_name in AI_NAMES
    ]


def _build_candidate_feature_frame(
    *,
    quotes: pd.DataFrame,
    listed: pd.DataFrame,
    target_data_until: str,
    created_at: str,
) -> pd.DataFrame:
    frame = _build_formal_candidate_rows(
        quotes=quotes,
        target_data_until=target_data_until,
        created_at=created_at,
    )
    if not frame.empty:
        frame = _apply_phase9_universe_hard_gate(frame, listed=listed, target_data_until=target_data_until)
        frame["created_at"] = created_at
        frame["data_until"] = target_data_until
    return frame


def _latest_listed_snapshot(listed: pd.DataFrame, *, target_data_until: str) -> pd.DataFrame:
    if listed.empty:
        return listed
    date_col = _first_existing_column(listed, ("target_date", "Date", "date"))
    if not date_col:
        return listed.iloc[0:0].copy()
    frame = listed[listed[date_col].astype(str) <= target_data_until].copy()
    if frame.empty:
        return frame
    latest_date = str(frame[date_col].astype(str).max())
    return frame[frame[date_col].astype(str) == latest_date].copy()


def _apply_phase9_universe_hard_gate(
    frame: pd.DataFrame,
    *,
    listed: pd.DataFrame,
    target_data_until: str,
) -> pd.DataFrame:
    output = frame.copy()
    listed_by_code = _listed_snapshot_by_code(listed)
    is_current_listed: list[bool] = []
    has_current_name: list[bool] = []
    product_categories: list[str] = []
    market_names: list[str] = []
    is_allowed_product: list[bool] = []
    is_fresh_price: list[bool] = []
    reasons: list[str] = []
    eligible: list[bool] = []

    for row in output.to_dict(orient="records"):
        code = _normalize_code(row.get("code") or row.get("Code"))
        listed_row = listed_by_code.get(code)
        current = listed_row is not None
        name = str((listed_row or {}).get("CoName") or (listed_row or {}).get("CompanyName") or "").strip()
        product_category = str((listed_row or {}).get("ProdCat") or "")
        market_name = str((listed_row or {}).get("MktNm") or "")
        allowed_product = product_category in ALLOWED_PHASE9_PRODUCT_CATEGORIES and market_name in ALLOWED_PHASE9_MARKETS
        fresh_price = str(row.get("data_end_date") or "") == target_data_until
        enough_lookback = bool(row.get("universe_eligible"))

        row_reasons: list[str] = []
        if not enough_lookback:
            row_reasons.append("insufficient_lookback")
        if not current:
            row_reasons.append("not_current_listed")
        if not name:
            row_reasons.append("missing_name")
        if not fresh_price:
            row_reasons.append("stale_price")
        if not allowed_product:
            row_reasons.append("disallowed_product")

        is_current_listed.append(current)
        has_current_name.append(bool(name))
        product_categories.append(product_category)
        market_names.append(market_name)
        is_allowed_product.append(allowed_product)
        is_fresh_price.append(fresh_price)
        reasons.append(",".join(dict.fromkeys(row_reasons)))
        eligible.append(not row_reasons)

    output["is_current_listed"] = is_current_listed
    output["has_current_name"] = has_current_name
    output["is_fresh_price"] = is_fresh_price
    output["product_category"] = product_categories
    output["market_name"] = market_names
    output["is_allowed_product"] = is_allowed_product
    output["universe_exclusion_reason"] = reasons
    output["universe_eligible"] = eligible
    output["excluded_reason"] = reasons
    return output


def _listed_snapshot_by_code(listed: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if listed.empty:
        return {}
    code_col = _first_existing_column(listed, ("code", "Code", "LocalCode"))
    if not code_col:
        return {}
    frame = listed.copy()
    date_col = _first_existing_column(frame, ("target_date", "Date", "date"))
    if date_col:
        frame = frame.sort_values([code_col, date_col])
    return {
        _normalize_code(row.get(code_col)): row
        for row in frame.to_dict(orient="records")
        if _normalize_code(row.get(code_col))
    }


def _first_existing_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    for column in candidates:
        if column in frame.columns:
            return column
    return ""


def _normalize_code(value: Any) -> str:
    return str(value or "").strip().upper()


def _build_opportunity_feature_input(
    *,
    candidate: pd.DataFrame,
    listed: pd.DataFrame,
    target_data_until: str,
    created_at: str,
) -> pd.DataFrame:
    if candidate.empty:
        return pd.DataFrame(columns=list(REQUIRED_COLUMNS["opportunity"]) + ["data_until", "created_at"])
    market_sector = build_market_sector_features(
        candidate,
        listed,
        target_dates=[target_data_until],
        created_at=created_at,
    )
    market_sector_columns = [
        column
        for column in OPPORTUNITY_MODEL_INPUT_COLUMNS
        if column.startswith("market_") or column.startswith("sector_") or column == "stock_vs_sector_return_20d"
    ]
    output = candidate[["target_date", "as_of_date", "code", "created_at", "data_until", "feature_version"]].copy()
    output = output.merge(
        market_sector[["target_date", "code", *market_sector_columns]],
        on=["target_date", "code"],
        how="left",
        validate="one_to_one",
    )
    for column in OPPORTUNITY_MODEL_INPUT_COLUMNS:
        if column not in output.columns and column in candidate.columns:
            output[column] = candidate[column]
    output["feature_version"] = "runtime_v2_opportunity_feature_input_v2_market_sector"
    ordered = ["target_date", "as_of_date", "code", "created_at", "data_until", "feature_version", *OPPORTUNITY_MODEL_INPUT_COLUMNS]
    return output[ordered].copy()


def _build_position_feature_input(
    *,
    target_data_until: str,
    created_at: str,
    runtime_root: Path | None,
    quotes: pd.DataFrame,
    candidate: pd.DataFrame | None = None,
    candidate_source_path: Path | None = None,
) -> pd.DataFrame:
    columns = list(REQUIRED_COLUMNS["position"]) + ["no_position_reason"]
    authority = _resolve_current_authority(runtime_root=runtime_root, target_data_until=target_data_until)
    current = authority["payload"]
    positions = current.get("positions") if isinstance(current.get("positions"), list) else []
    if not positions:
        frame = pd.DataFrame(columns=columns)
        frame.attrs["target_data_until"] = target_data_until
        frame.attrs["created_at"] = created_at
        frame.attrs["current_authority"] = authority
        return frame
    quote_by_code = _latest_quote_by_code(quotes=quotes, target_data_until=target_data_until)
    candidate_technicals = _candidate_technical_context(
        candidate=candidate,
        target_data_until=target_data_until,
        candidate_source_path=candidate_source_path,
    )
    position_state_as_of = str(current.get("position_state_as_of") or current.get("business_date") or current.get("as_of") or "")
    rows: list[dict[str, Any]] = []
    for position in positions:
        broker_issue_code = str(position.get("issue_code") or position.get("symbol") or position.get("code") or "").strip()
        if not broker_issue_code:
            continue
        code = _jquants_code_from_broker_issue_code(broker_issue_code)
        quote = quote_by_code.get(code, {})
        current_price = _to_float_or_none(quote.get("Close") or quote.get("close") or position.get("current_price"))
        average_price = _to_float_or_none(position.get("average_price") or position.get("avg_price") or position.get("cost_price"))
        quantity = _to_float_or_none(position.get("quantity"))
        entry_date = str(position.get("entry_date") or position.get("acquired_at") or position.get("last_execution_date") or position_state_as_of or target_data_until)
        technicals = dict(candidate_technicals.get(code) or {})
        missing_technical_features = [
            column
            for column in PM_TECHNICAL_SOURCE_COLUMNS
            if technicals.get(column) in (None, "") or pd.isna(technicals.get(column))
        ]
        rows.append(
            {
                "target_date": target_data_until,
                "feature_as_of_date": target_data_until,
                "position_state_as_of": position_state_as_of,
                "entry_date": entry_date,
                "code": code,
                "broker_issue_code": broker_issue_code,
                "holding_days": _holding_days(entry_date=entry_date, target_date=target_data_until),
                "average_price": average_price,
                "current_price": current_price,
                "unrealized_return": _safe_ratio_value(current_price, average_price),
                "quantity": quantity,
                **{column: technicals.get(column) for column in PM_TECHNICAL_SOURCE_COLUMNS},
                "feature_source_artifact": str(candidate_source_path or "candidate_features.parquet"),
                "feature_source_hash": candidate_technicals.get("__source_hash__", ""),
                "required_features": json.dumps(list(PM_TECHNICAL_SOURCE_COLUMNS), sort_keys=True),
                "optional_features": json.dumps(["no_position_reason"], sort_keys=True),
                "missing_features": json.dumps(missing_technical_features, sort_keys=True),
                "defaulted_features": "[]",
                "temporal_validation_status": "PASS" if not missing_technical_features else "REVIEW_REQUIRED",
                "feature_version": "runtime_v2_pm_feature_input_v2_technical_complete",
                "data_until": target_data_until,
                "created_at": created_at,
                "no_position_reason": "",
            }
        )
    frame = pd.DataFrame(rows, columns=columns)
    frame.attrs["current_authority"] = authority
    return frame


PM_TECHNICAL_SOURCE_COLUMNS = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "trend_close_over_ma_20d",
    "trend_ma_5_20_ratio",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
)


def _candidate_technical_context(
    *,
    candidate: pd.DataFrame | None,
    target_data_until: str,
    candidate_source_path: Path | None,
) -> dict[str, dict[str, Any]]:
    if candidate is None or candidate.empty:
        return {"__source_hash__": ""}
    frame = candidate.copy()
    if "target_date" not in frame.columns or "code" not in frame.columns:
        return {"__source_hash__": ""}
    frame["target_date"] = frame["target_date"].astype(str)
    frame["code"] = frame["code"].astype(str)
    date_rows = frame[frame["target_date"] == target_data_until].copy()
    source_hash = _frame_sha256(date_rows[["target_date", "code", *[c for c in PM_TECHNICAL_SOURCE_COLUMNS if c in date_rows.columns]]])
    context: dict[str, dict[str, Any]] = {"__source_hash__": source_hash}
    for row in date_rows.to_dict("records"):
        code = str(row.get("code") or "").strip()
        if not code:
            continue
        context[code] = {column: row.get(column) for column in PM_TECHNICAL_SOURCE_COLUMNS}
        context[code]["feature_source_artifact"] = str(candidate_source_path or "candidate_features.parquet")
        context[code]["feature_source_hash"] = source_hash
    return context


def _frame_sha256(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    normalized = frame.copy().sort_values([column for column in ("target_date", "code") if column in frame.columns])
    payload = normalized.to_json(orient="records", date_format="iso", force_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_formal_candidate_rows(*, quotes: pd.DataFrame, target_data_until: str, created_at: str) -> pd.DataFrame:
    source = pd.DataFrame(
        {
            "date": quotes["target_date"].astype(str),
            "code": quotes["code"].astype(str),
            "close": pd.to_numeric(quotes["Close"], errors="coerce"),
            "volume": pd.to_numeric(quotes["Volume"], errors="coerce"),
        }
    )
    source = source[source["date"] <= target_data_until].sort_values(["code", "date"])
    rows: list[dict[str, Any]] = []
    for code, group in source.groupby("code", sort=True):
        visible = group.reset_index(drop=True)
        closes = visible["close"]
        volumes = visible["volume"]
        insufficient_history = len(visible) < 61
        price_missing = _window_has_missing(closes, 61)
        volume_missing = _window_has_missing(volumes, 20)
        eligible = not insufficient_history and not price_missing and not volume_missing
        row: dict[str, Any] = {
            "as_of_date": target_data_until,
            "target_date": target_data_until,
            "code": str(code),
            "feature_version": "runtime_v2_candidate_features_v1",
            "source_snapshot_id": f"jquants_normalized_daily_quotes_until_{target_data_until}",
            "feature_set_name": "runtime_v2_formal_candidate_feature_producer_v1",
            "created_at": created_at,
            "data_start_date": str(visible["date"].iloc[0]) if len(visible) else None,
            "data_end_date": str(visible["date"].iloc[-1]) if len(visible) else None,
            "universe_eligible": eligible,
            "excluded_reason": "" if eligible else _candidate_exclusion_reason(insufficient_history, price_missing, volume_missing),
            "missing_flags_insufficient_history": bool(insufficient_history),
            "missing_flags_price": bool(price_missing),
            "missing_flags_volume": bool(volume_missing),
        }
        row.update(_formal_feature_values(closes=closes, volumes=volumes, eligible=eligible))
        rows.append(row)
    return pd.DataFrame(rows)


def _formal_feature_values(*, closes: pd.Series, volumes: pd.Series, eligible: bool) -> dict[str, Any]:
    if not eligible:
        return {
            "price_momentum_return_5d": None,
            "price_momentum_return_20d": None,
            "price_momentum_return_60d": None,
            "volume_momentum_ratio_5d": None,
            "volume_momentum_ratio_1d_20d": None,
            "volatility_return_std_20d": None,
            "trend_close_over_ma_20d": None,
            "trend_ma_5_20_ratio": None,
            "trend_ma_20_60_ratio": None,
            "liquidity_avg_volume_20d": None,
        }
    close_values = [float(value) for value in closes.tail(61).tolist()]
    volume_values = [float(value) for value in volumes.tail(20).tolist()]
    returns_20d = [_safe_ratio_value(close_values[index], close_values[index - 1]) for index in range(len(close_values) - 20, len(close_values))]
    ma5 = sum(close_values[-5:]) / 5
    ma20 = sum(close_values[-20:]) / 20
    ma60 = sum(close_values[-60:]) / 60
    avg_volume_5 = sum(volume_values[-5:]) / 5
    avg_volume_20 = sum(volume_values[-20:]) / 20
    return {
        "price_momentum_return_5d": _round(_safe_ratio_value(close_values[-1], close_values[-6])),
        "price_momentum_return_20d": _round(_safe_ratio_value(close_values[-1], close_values[-21])),
        "price_momentum_return_60d": _round(_safe_ratio_value(close_values[-1], close_values[-61])),
        "volume_momentum_ratio_5d": _round(_safe_divide(avg_volume_5, avg_volume_20)),
        "volume_momentum_ratio_1d_20d": _round(_safe_divide(volume_values[-1], avg_volume_20)),
        "volatility_return_std_20d": _round(float(pd.Series(returns_20d).std(ddof=0))),
        "trend_close_over_ma_20d": _round(_safe_divide(close_values[-1], ma20)),
        "trend_ma_5_20_ratio": _round(_safe_divide(ma5, ma20)),
        "trend_ma_20_60_ratio": _round(_safe_divide(ma20, ma60)),
        "liquidity_avg_volume_20d": _round(avg_volume_20),
    }


def _window_has_missing(values: pd.Series, size: int) -> bool:
    if len(values) < size:
        return True
    return bool(values.tail(size).isna().any())


def _candidate_exclusion_reason(insufficient_history: bool, price_missing: bool, volume_missing: bool) -> str:
    reasons = []
    if insufficient_history:
        reasons.append("insufficient_history")
    if price_missing:
        reasons.append("missing_price")
    if volume_missing:
        reasons.append("missing_volume")
    return ",".join(reasons)


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_current_authority(*, runtime_root: Path | None, target_data_until: str) -> dict[str, Any]:
    authority = resolve_current_position_authority(runtime_root=runtime_root, target_data_until=target_data_until)
    if authority["status"] == "READY_EMPTY" and authority["reason"] == "current_positions_confirmed_empty":
        return {**authority, "reason": "position_feature_ready_confirmed_empty_current"}
    return authority


def _current_authority_payload(
    *,
    status: str,
    path: str,
    payload: dict[str, Any],
    target_data_until: str,
    reason: str,
) -> dict[str, Any]:
    positions = payload.get("positions") if isinstance(payload.get("positions"), list) else []
    position_state_as_of = str(payload.get("position_state_as_of") or payload.get("business_date") or payload.get("as_of") or "")
    return {
        "status": status,
        "path": path,
        "payload": payload,
        "position_count": len(positions),
        "position_state_as_of": position_state_as_of[:10],
        "feature_target_date": target_data_until,
        "no_fill_carry_used": bool(position_state_as_of and position_state_as_of[:10] < target_data_until),
        "reason": reason,
    }


def _latest_quote_by_code(*, quotes: pd.DataFrame, target_data_until: str) -> dict[str, dict[str, Any]]:
    if quotes.empty:
        return {}
    frame = quotes[quotes["target_date"].astype(str) <= target_data_until].copy()
    if frame.empty:
        return {}
    frame["_code"] = frame["code"].astype(str)
    frame["_target_date"] = frame["target_date"].astype(str)
    frame = frame.sort_values(["_code", "_target_date"])
    return {str(row["_code"]): row for row in frame.groupby("_code", sort=False).tail(1).to_dict("records")}


def _jquants_code_from_broker_issue_code(value: Any) -> str:
    code = str(value or "").strip().upper()
    if len(code) == 4:
        return code + "0"
    return code


def _to_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(parsed):
        return None
    return parsed


def _holding_days(*, entry_date: str, target_date: str) -> int | None:
    try:
        return max(0, (datetime.fromisoformat(target_date[:10]) - datetime.fromisoformat(entry_date[:10])).days)
    except ValueError:
        return None


def _safe_ratio_value(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in {None, 0}:
        return None
    return current / previous - 1.0


def _safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return numerator / denominator


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)


def _build_capital_policy_input(
    *,
    target_data_until: str,
    candidate_path: Path,
    opportunity_path: Path,
    position_path: Path,
    created_at: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "target_date": target_data_until,
                "code": "__POLICY_INPUT__",
                "policy_input_type": "phase9_artifact_refs",
                "feature_version": "phase9_capital_policy_input_v1",
                "source_candidate_feature_path": str(candidate_path),
                "source_opportunity_feature_path": str(opportunity_path),
                "source_position_feature_path": str(position_path),
                "data_until": target_data_until,
                "created_at": created_at,
            }
        ]
    )


def _inspect_artifact(
    *,
    ai_name: str,
    path: Path,
    target_data_until: str,
    source_refs: dict[str, str],
    runtime_root: Path | None,
) -> FeatureArtifactStatus:
    if not path.is_file():
        return FeatureArtifactStatus(
            ai_name=ai_name,
            status=FEATURE_REFRESH_REQUIRED,
            artifact_path=str(path),
            source_data_refs=source_refs,
            blocked_reasons=(f"{ai_name}_feature_artifact_missing",),
        )
    try:
        frame = _read_table(path)
    except Exception as exc:
        return FeatureArtifactStatus(
            ai_name=ai_name,
            status=FEATURE_REFRESH_FAILED,
            artifact_path=str(path),
            source_data_refs=source_refs,
            blocked_reasons=(f"{ai_name}_feature_artifact_unreadable:{type(exc).__name__}",),
        )
    missing = sorted(set(REQUIRED_COLUMNS[ai_name]) - set(frame.columns))
    date_values = _date_values(frame)
    min_date = min(date_values, default=target_data_until if frame.empty and ai_name == "position" else "")
    max_date = max(date_values, default=target_data_until if frame.empty and ai_name == "position" else "")
    future_dates = [value for value in date_values if value > target_data_until]
    blocked: list[str] = []
    warnings: list[str] = []
    reason = "consumer_schema_ready"
    current_authority = _resolve_current_authority(runtime_root=runtime_root, target_data_until=target_data_until) if ai_name == "position" else {}
    if missing:
        blocked.append(f"{ai_name}_required_columns_missing:{','.join(missing)}")
    if future_dates:
        blocked.append(f"{ai_name}_future_rows_present")
    if max_date and max_date < target_data_until:
        blocked.append(f"{ai_name}_feature_before_target_data_until")
    if not max_date:
        blocked.append(f"{ai_name}_feature_date_missing")
    if frame.empty and ai_name != "position":
        blocked.append(f"{ai_name}_feature_empty")
    if ai_name == "position":
        current_position_count = int(current_authority.get("position_count") or 0)
        if current_authority:
            source_refs = {
                **source_refs,
                "current_authority_status": str(current_authority.get("status") or ""),
                "current_authority_path": str(current_authority.get("path") or ""),
                "current_position_count": str(current_position_count),
                "current_position_state_as_of": str(current_authority.get("position_state_as_of") or ""),
                "feature_target_date": target_data_until,
                "no_fill_carry_used": str(bool(current_authority.get("no_fill_carry_used"))),
                "input_symbol_count": str(current_position_count),
                "matched_symbol_count": str(len(frame)),
                "unmatched_symbols": "",
                "output_row_count": str(len(frame)),
                "position_feature_reason": str(current_authority.get("reason") or ""),
            }
        if str(current_authority.get("status") or "") not in {"READY", "READY_EMPTY"}:
            blocked.append(str(current_authority.get("reason") or "current_authority_not_ready"))
            reason = str(current_authority.get("reason") or "current_authority_not_ready")
        elif current_position_count > 0 and len(frame) == 0:
            blocked.append("position_feature_current_output_mismatch")
            reason = "position_feature_current_output_mismatch"
        elif current_position_count == 0 and len(frame) == 0:
            reason = str(current_authority.get("reason") or "position_feature_ready_confirmed_empty_current")
        else:
            reason = "position_feature_ready"
    if frame.empty and ai_name == "position" and not blocked:
        warnings.append("position_feature_empty_no_current_positions")
    if ai_name == "candidate" and "universe_eligible" in frame.columns:
        eligible_count = int(frame["universe_eligible"].fillna(False).astype(bool).sum())
        if eligible_count == 0:
            blocked.append("candidate_no_universe_eligible_rows")
        elif eligible_count < max(1, int(len(frame) * 0.10)):
            warnings.append(f"candidate_low_universe_eligible_rows:{eligible_count}")
    if ai_name == "opportunity":
        feature_columns = [column for column in frame.columns if column.startswith("feature__")]
        if feature_columns and frame[feature_columns].notna().sum().sum() == 0:
            blocked.append("opportunity_feature_values_all_null")
    required_status = "OK" if not missing else "MISSING"
    leakage_status = "OK" if not future_dates else "FAILED"
    status = FEATURE_SCHEMA_REVIEW_REQUIRED if missing or future_dates else (FEATURE_REFRESH_REQUIRED if blocked else FEATURES_READY)
    return FeatureArtifactStatus(
        ai_name=ai_name,
        status=status,
        artifact_path=str(path),
        row_count=int(len(frame)),
        min_date=min_date,
        max_date=max_date,
        data_until=max_date,
        feature_schema_hash=_schema_hash(frame),
        required_columns_status=required_status,
        future_leakage_check_status=leakage_status,
        source_data_refs=source_refs,
        output_artifact_refs={"artifact": str(path)},
        warnings=tuple(warnings),
        blocked_reasons=tuple(blocked),
        reason=reason,
    )


def _overall_status(*, artifacts: list[FeatureArtifactStatus], blocked: list[str]) -> str:
    if blocked or any(artifact.status == FEATURE_REFRESH_FAILED for artifact in artifacts):
        if any("failed" in reason.lower() or "canonical_path_missing" in reason.lower() for reason in blocked):
            return FEATURE_REFRESH_FAILED
        return FEATURE_REFRESH_REQUIRED
    if any(artifact.status == FEATURE_SCHEMA_REVIEW_REQUIRED for artifact in artifacts):
        return FEATURE_SCHEMA_REVIEW_REQUIRED
    if any(artifact.status == FEATURE_REFRESH_REQUIRED for artifact in artifacts):
        return FEATURE_REFRESH_REQUIRED
    return FEATURES_READY


def _date_values(frame: pd.DataFrame) -> list[str]:
    values: list[str] = []
    for column in ("target_date", "as_of_date", "data_until"):
        if column in frame.columns:
            values.extend(str(value) for value in frame[column].dropna().astype(str).tolist() if value)
    return values


def _schema_hash(frame: pd.DataFrame) -> str:
    columns = [str(column) for column in frame.columns]
    payload = json.dumps(columns, ensure_ascii=True, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            for key in ("rows", "items", "candidates", "decisions"):
                if isinstance(payload.get(key), list):
                    return pd.DataFrame(payload[key])
            return pd.DataFrame([payload])
    raise ValueError(f"unsupported table format: {path}")


def _write_outputs(
    *,
    result: FeatureRefreshResult,
    manifest_path: Path,
    markdown_path: Path,
    json_path: Path,
    created_at: str,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = result.to_dict()
    payload["created_at"] = created_at
    manifest_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Phase9-J Feature Refresh Report",
        "",
        f"- status: {payload['status']}",
        f"- target_data_until: {payload['target_data_until']}",
        f"- dry_run: {payload['dry_run']}",
        f"- execute: {payload['execute']}",
        f"- manifest_path: `{payload['manifest_path']}`",
        "",
        "## Artifacts",
        "",
        "| AI | status | rows | max_date | schema_hash | artifact |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for artifact in payload["artifacts"]:
        lines.append(
            f"| {artifact['ai_name']} | {artifact['status']} | {artifact['row_count']} | "
            f"{artifact['max_date']} | `{artifact['feature_schema_hash']}` | `{artifact['artifact_path']}` |"
        )
    lines.extend(["", "## Blocked Reasons", ""])
    if payload["blocked_reasons"]:
        lines.extend(f"- {reason}" for reason in payload["blocked_reasons"])
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if payload["warnings"]:
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Safety Flags",
            "",
            f"- feature_generation_executed: {payload['feature_generation_executed']}",
            f"- model_retraining_executed: {payload['model_retraining_executed']}",
            f"- inference_executed: {payload['inference_executed']}",
            f"- order_plan_generation_executed: {payload['order_plan_generation_executed']}",
            f"- broker_order_api_called: {payload['broker_order_api_called']}",
            f"- open_d_started: {payload['open_d_started']}",
            f"- unlock_trade_called: {payload['unlock_trade_called']}",
            f"- paper_ledger_fill_executed: {payload['paper_ledger_fill_executed']}",
            f"- virtual_fill_executed: {payload['virtual_fill_executed']}",
            "",
        ]
    )
    return "\n".join(lines)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
