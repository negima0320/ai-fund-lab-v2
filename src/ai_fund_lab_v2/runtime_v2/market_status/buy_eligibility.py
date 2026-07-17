"""BUY eligibility guard based on point-in-time market status authority."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from ai_fund_lab_v2.runtime_v2.historical_support.listed_issues_snapshots import (
    resolve_listed_issues_snapshot,
)

BUY_ELIGIBILITY_SCHEMA_VERSION = "runtime_v2_buy_eligibility_v1"

INELIGIBLE_STATUS_VALUES = {
    "DELISTED",
    "DELISTING",
    "DELISTING_DECIDED",
    "DELISTING_SCHEDULED",
    "LISTING_TERMINATED",
    "SPECIAL_SUPERVISION",
    "SUPERVISION",
    "SECURITIES_UNDER_SUPERVISION",
    "ARRANGING",
    "SECURITIES_TO_BE_DELISTED",
    "BUY_INELIGIBLE",
}

REVIEW_STATUS_VALUES = {
    "UNKNOWN",
    "TRADING_HALTED",
    "HALTED",
    "SUSPENDED",
    "CORPORATE_ACTION_PENDING",
}

STATUS_FIELD_NAMES = (
    "buy_eligibility",
    "market_status",
    "listing_status",
    "listed_status",
    "special_supervision_status",
    "supervision_status",
    "delisting_status",
    "lifecycle_status",
    "security_lifecycle_status",
)

DELISTING_DATE_FIELD_NAMES = (
    "delisting_date",
    "scheduled_delisting_date",
    "listing_termination_date",
)


@dataclass(frozen=True)
class BuyEligibilityResult:
    status: str
    buy_eligibility: str
    eligible: bool
    reason_code: str
    reason: str
    symbol: str
    business_date: str
    authority_source: str
    authority_path: str = ""
    authority_hash: str = ""
    authority_as_of: str = ""
    authority_type: str = ""
    current_listed: bool | None = None
    market_status: str = ""
    listing_status: str = ""
    special_supervision_status: str = ""
    delisting_date: str = ""
    point_in_time: bool = True
    future_authority_used: bool = False
    missing_authority: bool = False
    stale_authority: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {"schema_version": BUY_ELIGIBILITY_SCHEMA_VERSION, **asdict(self)}


def evaluate_buy_eligibility(
    *,
    symbol: str,
    business_date: str,
    mode: str,
    listed_info: Mapping[str, Any] | None = None,
    runtime_root: Path | str | None = None,
    listed_snapshot_path: Path | str | None = None,
    authority_source: str = "",
) -> BuyEligibilityResult:
    """Resolve whether a new BUY is allowed for a symbol.

    The resolver is intentionally point-in-time. It can reject symbols that are
    not listed as of the business date or that carry explicit ineligible market
    status fields. It does not infer pre-delisting ineligibility from later
    snapshots.
    """

    normalized_symbol = _normalize_symbol(symbol)
    info = dict(listed_info or {})
    source = authority_source or "pending_listed_info"
    authority_path = ""
    authority_hash = ""
    authority_as_of = _text(info.get("Date") or info.get("date") or info.get("as_of") or business_date)
    authority_type = "EMBEDDED_LISTED_INFO" if info else ""

    if listed_snapshot_path is not None:
        path = Path(listed_snapshot_path)
        snapshot = _listed_info_from_snapshot(path=path, symbol=normalized_symbol)
        if snapshot["status"] != "PASS":
            return _result(
                status="REVIEW_REQUIRED",
                eligibility="REVIEW_REQUIRED",
                reason_code=str(snapshot["reason"]),
                reason="BUY eligibility authority is missing or unreadable",
                symbol=normalized_symbol,
                business_date=business_date,
                authority_source=source or "listed_snapshot",
                authority_path=str(path),
                authority_hash=_file_hash(path),
                authority_as_of="",
                authority_type="LISTED_ISSUES_SNAPSHOT",
                missing_authority=True,
            )
        info = dict(snapshot["listed_info"])
        source = source or "listed_snapshot"
        authority_path = str(path)
        authority_hash = _file_hash(path)
        authority_as_of = str(info.get("Date") or info.get("date") or "")
        authority_type = "LISTED_ISSUES_SNAPSHOT"
    elif runtime_root is not None and mode == "historical":
        resolution = resolve_listed_issues_snapshot(
            snapshot_root=Path(runtime_root) / "operations" / "jquants" / "historical_snapshots" / "listed_issues",
            business_date=business_date,
            mode="historical",
        )
        if resolution.status == "PASS":
            return evaluate_buy_eligibility(
                symbol=normalized_symbol,
                business_date=business_date,
                mode=mode,
                listed_info=listed_info,
                listed_snapshot_path=resolution.selected_snapshot_path,
                authority_source="historical_listed_issues_snapshot",
            )
        if not info:
            return _result(
                status="REVIEW_REQUIRED",
                eligibility="REVIEW_REQUIRED",
                reason_code="market_status_authority_missing",
                reason=resolution.reason,
                symbol=normalized_symbol,
                business_date=business_date,
                authority_source="historical_listed_issues_snapshot",
                authority_path=resolution.selected_snapshot_path,
                authority_type="LISTED_ISSUES_SNAPSHOT",
                missing_authority=True,
            )

    if not info:
        return _result(
            status="REVIEW_REQUIRED",
            eligibility="REVIEW_REQUIRED",
            reason_code="market_status_authority_missing",
            reason="BUY eligibility listed authority is required",
            symbol=normalized_symbol,
            business_date=business_date,
            authority_source=source or "listed_info",
            missing_authority=True,
        )

    code = _normalize_symbol(info.get("code") or info.get("Code") or info.get("issue_code") or normalized_symbol)
    if code != normalized_symbol:
        return _result(
            status="REVIEW_REQUIRED",
            eligibility="REVIEW_REQUIRED",
            reason_code="market_status_symbol_mismatch",
            reason=f"listed authority code {code} does not match {normalized_symbol}",
            symbol=normalized_symbol,
            business_date=business_date,
            authority_source=source,
            authority_path=authority_path,
            authority_hash=authority_hash,
            authority_as_of=authority_as_of,
            authority_type=authority_type,
            missing_authority=False,
        )

    if _bool_false(info.get("current_listed")) or _bool_false(info.get("is_current_listed")):
        return _result_from_info(
            info,
            status="BLOCKED",
            eligibility="INELIGIBLE",
            reason_code="symbol_not_listed_as_of_business_date",
            reason="symbol is not listed as of business date",
            symbol=normalized_symbol,
            business_date=business_date,
            authority_source=source,
            authority_path=authority_path,
            authority_hash=authority_hash,
            authority_as_of=authority_as_of,
            authority_type=authority_type,
        )

    if _bool_false(info.get("buy_eligible")):
        return _result_from_info(
            info,
            status="BLOCKED",
            eligibility="INELIGIBLE",
            reason_code=_text(info.get("buy_ineligible_reason") or "explicit_buy_ineligible"),
            reason="listed authority explicitly marks BUY ineligible",
            symbol=normalized_symbol,
            business_date=business_date,
            authority_source=source,
            authority_path=authority_path,
            authority_hash=authority_hash,
            authority_as_of=authority_as_of,
            authority_type=authority_type,
        )

    for field in STATUS_FIELD_NAMES:
        value = _status_value(info.get(field))
        if not value:
            continue
        if value in INELIGIBLE_STATUS_VALUES:
            return _result_from_info(
                info,
                status="BLOCKED",
                eligibility="INELIGIBLE",
                reason_code=f"market_status_buy_ineligible:{field}:{value}",
                reason="market status authority blocks new BUY",
                symbol=normalized_symbol,
                business_date=business_date,
                authority_source=source,
                authority_path=authority_path,
                authority_hash=authority_hash,
                authority_as_of=authority_as_of,
                authority_type=authority_type,
            )
        if value in REVIEW_STATUS_VALUES:
            return _result_from_info(
                info,
                status="REVIEW_REQUIRED",
                eligibility="REVIEW_REQUIRED",
                reason_code=f"market_status_review_required:{field}:{value}",
                reason="market status authority requires review before new BUY",
                symbol=normalized_symbol,
                business_date=business_date,
                authority_source=source,
                authority_path=authority_path,
                authority_hash=authority_hash,
                authority_as_of=authority_as_of,
                authority_type=authority_type,
            )

    for field in DELISTING_DATE_FIELD_NAMES:
        delisting_date = _text(info.get(field))
        if not delisting_date:
            continue
        if delisting_date <= business_date:
            reason_code = "delisting_date_on_or_before_business_date"
        else:
            reason_code = "scheduled_delisting_buy_ineligible"
        return _result_from_info(
            info,
            status="BLOCKED",
            eligibility="INELIGIBLE",
            reason_code=reason_code,
            reason="new BUY is not allowed for delisted or delisting-scheduled symbol",
            symbol=normalized_symbol,
            business_date=business_date,
            authority_source=source,
            authority_path=authority_path,
            authority_hash=authority_hash,
            authority_as_of=authority_as_of,
            authority_type=authority_type,
        )

    return _result_from_info(
        info,
        status="PASS",
        eligibility="ELIGIBLE",
        reason_code="market_status_buy_eligible",
        reason="listed authority permits new BUY",
        symbol=normalized_symbol,
        business_date=business_date,
        authority_source=source,
        authority_path=authority_path,
        authority_hash=authority_hash,
        authority_as_of=authority_as_of,
        authority_type=authority_type,
    )


def _listed_info_from_snapshot(*, path: Path, symbol: str) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "REVIEW_REQUIRED", "reason": "listed_snapshot_missing"}
    try:
        import pandas as pd

        frame = pd.read_parquet(path)
    except Exception:
        return {"status": "REVIEW_REQUIRED", "reason": "listed_snapshot_unreadable"}
    if frame.empty:
        return {"status": "REVIEW_REQUIRED", "reason": "listed_snapshot_empty"}
    code_column = "Code" if "Code" in frame.columns else "code" if "code" in frame.columns else ""
    if not code_column:
        return {"status": "REVIEW_REQUIRED", "reason": "listed_snapshot_code_column_missing"}
    codes = frame[code_column].astype(str).str.strip().str.upper()
    matches = frame.loc[codes == symbol]
    if matches.empty:
        return {
            "status": "PASS",
            "listed_info": {
                "code": symbol,
                "current_listed": False,
                "Date": _snapshot_date_from_frame(frame),
            },
        }
    return {"status": "PASS", "listed_info": dict(matches.iloc[0].to_dict())}


def _result_from_info(
    info: Mapping[str, Any],
    *,
    status: str,
    eligibility: str,
    reason_code: str,
    reason: str,
    symbol: str,
    business_date: str,
    authority_source: str,
    authority_path: str = "",
    authority_hash: str = "",
    authority_as_of: str = "",
    authority_type: str = "",
) -> BuyEligibilityResult:
    return _result(
        status=status,
        eligibility=eligibility,
        reason_code=reason_code,
        reason=reason,
        symbol=symbol,
        business_date=business_date,
        authority_source=authority_source,
        authority_path=authority_path,
        authority_hash=authority_hash,
        authority_as_of=authority_as_of,
        authority_type=authority_type,
        current_listed=_current_listed(info),
        market_status=_text(info.get("market_status") or info.get("MktNm") or info.get("market")),
        listing_status=_text(info.get("listing_status") or info.get("listed_status")),
        special_supervision_status=_text(info.get("special_supervision_status") or info.get("supervision_status")),
        delisting_date=_text(
            info.get("delisting_date")
            or info.get("scheduled_delisting_date")
            or info.get("listing_termination_date")
        ),
    )


def _result(
    *,
    status: str,
    eligibility: str,
    reason_code: str,
    reason: str,
    symbol: str,
    business_date: str,
    authority_source: str,
    authority_path: str = "",
    authority_hash: str = "",
    authority_as_of: str = "",
    authority_type: str = "",
    current_listed: bool | None = None,
    market_status: str = "",
    listing_status: str = "",
    special_supervision_status: str = "",
    delisting_date: str = "",
    missing_authority: bool = False,
    stale_authority: bool = False,
) -> BuyEligibilityResult:
    return BuyEligibilityResult(
        status=status,
        buy_eligibility=eligibility,
        eligible=status == "PASS" and eligibility == "ELIGIBLE",
        reason_code=reason_code,
        reason=reason,
        symbol=symbol,
        business_date=business_date,
        authority_source=authority_source,
        authority_path=authority_path,
        authority_hash=authority_hash,
        authority_as_of=authority_as_of,
        authority_type=authority_type,
        current_listed=current_listed,
        market_status=market_status,
        listing_status=listing_status,
        special_supervision_status=special_supervision_status,
        delisting_date=delisting_date,
        missing_authority=missing_authority,
        stale_authority=stale_authority,
    )


def _snapshot_date_from_frame(frame: Any) -> str:
    if "Date" not in frame.columns and "date" not in frame.columns:
        return ""
    column = "Date" if "Date" in frame.columns else "date"
    values = sorted({_text(value)[:10] for value in frame[column].dropna().unique() if _text(value)})
    return values[-1] if values else ""


def _current_listed(info: Mapping[str, Any]) -> bool | None:
    if "current_listed" in info:
        return not _bool_false(info.get("current_listed"))
    if "is_current_listed" in info:
        return not _bool_false(info.get("is_current_listed"))
    return None


def _bool_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    return str(value).strip().lower() in {"false", "0", "no", "n"}


def _status_value(value: Any) -> str:
    return _text(value).strip().upper().replace(" ", "_").replace("-", "_")


def _normalize_symbol(value: Any) -> str:
    return str(value or "").strip().upper().removesuffix(".T")


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _file_hash(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
