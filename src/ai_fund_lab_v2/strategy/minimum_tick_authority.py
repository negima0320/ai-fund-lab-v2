from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping


MINIMUM_TICK_AUTHORITY_SCHEMA_VERSION = "minimum_tick_authority.v1"
MINIMUM_TICK_AUTHORITY_TYPE = "MINIMUM_TICK_AUTHORITY"
JPX_TSE_CASH_TICK_RULE_ID = "JPX_TSE_CASH_EQUITY_PRICE_INCREMENT"
JPX_TSE_CASH_TICK_RULE_VERSION_PRE_2027 = "JPX_TSE_CASH_TICK_TABLE_PRE_2027"
JPX_TSE_CASH_TICK_EFFECTIVE_FROM_PRE_2027 = "2014-07-22"
JPX_TSE_CASH_TICK_EFFECTIVE_TO_PRE_2027 = "2027-02-28"

STATUS_KNOWN = "KNOWN"
STATUS_NOT_APPLICABLE = "NOT_APPLICABLE"
STATUS_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

PIT_PASS = "PASS"
PIT_BLOCK = "BLOCK"

TOPIX500_SCALE_CATEGORIES = {
    "TOPIX Core30",
    "TOPIX Large70",
    "TOPIX Mid400",
}

OTHER_ISSUES_TABLE = (
    (3_000.0, 1.0),
    (5_000.0, 5.0),
    (30_000.0, 10.0),
    (50_000.0, 50.0),
    (300_000.0, 100.0),
    (500_000.0, 500.0),
    (3_000_000.0, 1_000.0),
    (5_000_000.0, 5_000.0),
    (30_000_000.0, 10_000.0),
    (float("inf"), 50_000.0),
)

TOPIX500_TABLE = (
    (1_000.0, 0.1),
    (3_000.0, 0.5),
    (10_000.0, 1.0),
    (30_000.0, 5.0),
    (100_000.0, 10.0),
    (300_000.0, 50.0),
    (500_000.0, 100.0),
    (3_000_000.0, 500.0),
    (5_000_000.0, 1_000.0),
    (30_000_000.0, 5_000.0),
    (float("inf"), 10_000.0),
)

ETF_UNIT_1_TABLE = (
    (10_000.0, 1.0),
    (30_000.0, 5.0),
    (100_000.0, 10.0),
    (300_000.0, 50.0),
    (500_000.0, 100.0),
    (3_000_000.0, 500.0),
    (5_000_000.0, 1_000.0),
    (30_000_000.0, 5_000.0),
    (float("inf"), 10_000.0),
)

TICK_TABLES = {
    "OTHER_ISSUES": OTHER_ISSUES_TABLE,
    "TOPIX500": TOPIX500_TABLE,
    "ETF_UNIT_1": ETF_UNIT_1_TABLE,
}


@dataclass(frozen=True)
class MinimumTickResolution:
    symbol: str
    business_date: str
    as_of_date: str
    reference_price: float | None
    reference_price_source: str
    minimum_tick: float | None
    single_tick_pct: float | None
    tick_rule_id: str
    tick_rule_version: str
    tick_rule_effective_from: str
    tick_rule_effective_to: str
    security_type: str
    exchange: str
    market_segment: str
    tick_table_class: str
    classification_source: str
    classification_source_as_of: str
    resolution_status: str
    resolution_reason_codes: tuple[str, ...]
    source_artifact_id: str
    source_artifact_hash: str
    runtime_run_id: str
    producer: str
    pit_status: str

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "schema_version": MINIMUM_TICK_AUTHORITY_SCHEMA_VERSION,
            "authority_type": MINIMUM_TICK_AUTHORITY_TYPE,
            **asdict(self),
        }
        payload["resolution_reason_codes"] = list(self.resolution_reason_codes)
        payload["authority_hash"] = authority_hash(payload)
        return payload


def resolve_minimum_tick(
    *,
    symbol: str,
    business_date: str,
    reference_price: Any,
    security_metadata: Mapping[str, Any] | None = None,
    reference_price_source: str = "",
    source_artifact_id: str = "",
    source_artifact_hash: str = "",
    runtime_run_id: str = "",
    producer: str = "strategy_input_materializer",
) -> dict[str, Any]:
    metadata = dict(security_metadata or {})
    normalized_symbol = _symbol(symbol or metadata.get("code") or metadata.get("Code"))
    price = _positive_float(reference_price)
    metadata_date = _metadata_date(metadata) or business_date
    source = str(metadata.get("classification_source") or metadata.get("source") or source_artifact_id or "")
    source_hash = str(metadata.get("classification_source_hash") or source_artifact_hash or "")
    security_type = _security_type(metadata)
    market = _market(metadata)
    scale_category = str(metadata.get("ScaleCat") or metadata.get("scale_category") or metadata.get("scale_cat") or "").strip()
    tick_table_class, class_reasons = _tick_table_class(metadata, security_type=security_type, scale_category=scale_category)
    reason_codes: list[str] = []
    if not normalized_symbol:
        reason_codes.append("symbol_missing")
    if not business_date:
        reason_codes.append("business_date_missing")
    if metadata_date and business_date and metadata_date > business_date:
        reason_codes.append("future_security_metadata_rejected")
    if price is None:
        reason_codes.append("reference_price_missing_or_invalid")
    if not security_type:
        reason_codes.append("security_type_missing")
    if not tick_table_class:
        reason_codes.extend(class_reasons or ["tick_table_class_missing"])

    rule_version, effective_from, effective_to = _rule_version_for_date(business_date)
    if not rule_version:
        reason_codes.append("tick_rule_version_not_implemented_for_business_date")

    status = STATUS_INSUFFICIENT_EVIDENCE
    tick = None
    single_tick_pct = None
    if reason_codes:
        if "unsupported_security_type" in reason_codes:
            status = STATUS_NOT_APPLICABLE
    else:
        tick = _resolve_from_table(tick_table_class, price)
        if tick is None:
            reason_codes.append("tick_table_resolution_failed")
        else:
            status = STATUS_KNOWN
            single_tick_pct = round(tick / price, 8)
            reason_codes.append("minimum_tick_resolved")

    pit_status = PIT_PASS if status == STATUS_KNOWN and "future_security_metadata_rejected" not in reason_codes else PIT_BLOCK
    return MinimumTickResolution(
        symbol=normalized_symbol,
        business_date=str(business_date or ""),
        as_of_date=str(metadata_date or ""),
        reference_price=round(price, 10) if price is not None else None,
        reference_price_source=str(reference_price_source or ""),
        minimum_tick=tick,
        single_tick_pct=single_tick_pct,
        tick_rule_id=JPX_TSE_CASH_TICK_RULE_ID if rule_version else "",
        tick_rule_version=rule_version,
        tick_rule_effective_from=effective_from,
        tick_rule_effective_to=effective_to,
        security_type=security_type,
        exchange=str(metadata.get("exchange") or metadata.get("Mkt") or ""),
        market_segment=market,
        tick_table_class=tick_table_class,
        classification_source=source,
        classification_source_as_of=str(metadata_date or ""),
        resolution_status=status,
        resolution_reason_codes=tuple(sorted(set(reason_codes))),
        source_artifact_id=str(source_artifact_id or source or ""),
        source_artifact_hash=source_hash,
        runtime_run_id=str(runtime_run_id or ""),
        producer=producer,
        pit_status=pit_status,
    ).to_payload()


def validate_minimum_tick_authority(
    authority: Mapping[str, Any] | None,
    *,
    expected_symbol: str = "",
    expected_business_date: str = "",
    expected_runtime_run_id: str = "",
) -> tuple[str, tuple[str, ...]]:
    payload = dict(authority or {})
    reasons: list[str] = []
    if payload.get("schema_version") != MINIMUM_TICK_AUTHORITY_SCHEMA_VERSION:
        reasons.append("schema_version_mismatch")
    if payload.get("resolution_status") != STATUS_KNOWN:
        reasons.append("resolution_status_not_known")
    if payload.get("pit_status") != PIT_PASS:
        reasons.append("pit_status_not_pass")
    if expected_symbol and _symbol(payload.get("symbol")) != _symbol(expected_symbol):
        reasons.append("symbol_mismatch")
    if expected_business_date and str(payload.get("business_date") or "") != expected_business_date:
        reasons.append("business_date_mismatch")
    if expected_runtime_run_id and str(payload.get("runtime_run_id") or "") != expected_runtime_run_id:
        reasons.append("runtime_run_id_mismatch")
    as_of = str(payload.get("as_of_date") or "")
    business_date = str(payload.get("business_date") or "")
    if as_of and business_date and as_of > business_date:
        reasons.append("future_security_metadata_rejected")
    expected_hash = payload.get("authority_hash")
    if expected_hash and expected_hash != authority_hash({k: v for k, v in payload.items() if k != "authority_hash"}):
        reasons.append("authority_hash_mismatch")
    return ("PASS" if not reasons else "BLOCK", tuple(sorted(set(reasons))))


def authority_hash(payload: Mapping[str, Any]) -> str:
    normalized = {k: v for k, v in dict(payload).items() if k != "authority_hash"}
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _rule_version_for_date(business_date: str) -> tuple[str, str, str]:
    if not business_date:
        return "", "", ""
    if business_date <= JPX_TSE_CASH_TICK_EFFECTIVE_TO_PRE_2027:
        return (
            JPX_TSE_CASH_TICK_RULE_VERSION_PRE_2027,
            JPX_TSE_CASH_TICK_EFFECTIVE_FROM_PRE_2027,
            JPX_TSE_CASH_TICK_EFFECTIVE_TO_PRE_2027,
        )
    return "", "", ""


def _resolve_from_table(tick_table_class: str, reference_price: float | None) -> float | None:
    if reference_price is None or reference_price <= 0:
        return None
    table = TICK_TABLES.get(tick_table_class)
    if not table:
        return None
    for upper, tick in table:
        if reference_price <= upper:
            return tick
    return None


def _tick_table_class(metadata: Mapping[str, Any], *, security_type: str, scale_category: str) -> tuple[str, list[str]]:
    explicit = str(metadata.get("tick_table_class") or metadata.get("minimum_tick_table_class") or "").strip().upper()
    if explicit in TICK_TABLES:
        return explicit, []
    if security_type in {"011", "COMMON_STOCK", "DOMESTIC_COMMON_STOCK"}:
        if scale_category in TOPIX500_SCALE_CATEGORIES:
            return "TOPIX500", []
        return "OTHER_ISSUES", []
    if explicit:
        return "", ["unsupported_tick_table_class"]
    if not security_type:
        return "", ["tick_table_class_missing"]
    return "", ["unsupported_security_type"]


def _security_type(metadata: Mapping[str, Any]) -> str:
    return str(
        metadata.get("security_type")
        or metadata.get("product_category")
        or metadata.get("ProdCat")
        or metadata.get("SecType")
        or metadata.get("Type")
        or ""
    ).strip()


def _market(metadata: Mapping[str, Any]) -> str:
    return str(metadata.get("market_name") or metadata.get("MktNm") or metadata.get("market") or "").strip()


def _metadata_date(metadata: Mapping[str, Any]) -> str:
    return str(
        metadata.get("as_of_date")
        or metadata.get("Date")
        or metadata.get("date")
        or metadata.get("classification_source_as_of")
        or ""
    ).strip()


def _symbol(value: Any) -> str:
    return str(value or "").strip()


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number
