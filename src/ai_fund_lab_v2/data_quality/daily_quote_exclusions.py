from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_fund_lab_v2.data_quality.normalization import ADJUSTED_FIELDS, UNADJUSTED_FIELDS, normalize_daily_quotes, read_daily_quotes_raw
from ai_fund_lab_v2.data_sources.jquants.raw_ingestion import RAW_COLLECTIONS
from ai_fund_lab_v2.data_store import MarketDataStore
from ai_fund_lab_v2.runtime import RuntimePaths


@dataclass(frozen=True)
class DailyQuoteExclusionReport:
    excluded_count: int
    input_record_count: int
    normalized_record_count: int
    by_date: dict[str, int]
    by_code: dict[str, int]
    by_market: dict[str, int]
    by_missing_pattern: dict[str, int]
    by_estimated_reason: dict[str, int]
    affected_dates: list[str]
    affected_codes_sample: list[str]
    joined_listed_issue_sample: list[dict[str, Any]]
    excluded_sample: list[dict[str, Any]]
    recommended_policy: str
    phase2_handling: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def inspect_daily_quote_exclusions(
    paths: RuntimePaths,
    *,
    input_format: str = "auto",
    limit: int = 50,
    raw_records: list[dict[str, Any]] | None = None,
    listed_issues: list[dict[str, Any]] | None = None,
) -> DailyQuoteExclusionReport:
    if raw_records is None:
        raw_records, _, _ = read_daily_quotes_raw(paths, input_format)
    if listed_issues is None:
        listed_issues = MarketDataStore(paths).read_raw_collection(RAW_COLLECTIONS["listed_issues"])

    normalized, normalization_report = normalize_daily_quotes(raw_records, limit_errors=limit)
    normalized_keys = {(str(record.get("Date")), str(record.get("Code"))) for record in normalized}
    issue_by_code = _latest_issue_by_code(listed_issues)

    excluded = [
        record
        for record in raw_records
        if (str(record.get("Date") or record.get("target_date") or ""), str(record.get("Code") or record.get("code") or "")) not in normalized_keys
    ]

    by_date: Counter[str] = Counter()
    by_code: Counter[str] = Counter()
    by_market: Counter[str] = Counter()
    by_missing_pattern: Counter[str] = Counter()
    by_estimated_reason: Counter[str] = Counter()
    joined_sample: list[dict[str, Any]] = []
    excluded_sample: list[dict[str, Any]] = []

    for record in excluded:
        date = str(record.get("Date") or record.get("target_date") or "")
        code = str(record.get("Code") or record.get("code") or "")
        issue = issue_by_code.get(code, {})
        market = str(issue.get("MktNm") or issue.get("MarketName") or issue.get("Mkt") or issue.get("Section") or "unknown")
        pattern = missing_pattern(record)
        reason = estimate_reason(record, issue)

        by_date[date or "unknown"] += 1
        by_code[code or "unknown"] += 1
        by_market[market] += 1
        by_missing_pattern[pattern] += 1
        by_estimated_reason[reason] += 1

        if len(joined_sample) < limit:
            joined_sample.append(
                {
                    "Date": date,
                    "Code": code,
                    "CoName": issue.get("CoName") or issue.get("CompanyName") or issue.get("CompanyNameJapanese"),
                    "Market": market,
                    "missing_pattern": pattern,
                    "estimated_reason": reason,
                }
            )
        if len(excluded_sample) < limit:
            excluded_sample.append(redact_record(record))

    return DailyQuoteExclusionReport(
        excluded_count=len(excluded),
        input_record_count=len(raw_records),
        normalized_record_count=normalization_report.output_record_count,
        by_date=dict(sorted(by_date.items())),
        by_code=dict(by_code.most_common(limit)),
        by_market=dict(by_market.most_common()),
        by_missing_pattern=dict(by_missing_pattern.most_common()),
        by_estimated_reason=dict(by_estimated_reason.most_common()),
        affected_dates=sorted(day for day in by_date if day != "unknown"),
        affected_codes_sample=[code for code, _ in by_code.most_common(limit)],
        joined_listed_issue_sample=joined_sample,
        excluded_sample=excluded_sample,
        recommended_policy=(
            "Do not treat excluded records as normal without a market-data reason. "
            "Keep raw v1 unchanged, keep excluded records out of normalized raw, and investigate unknown/no-price-volume records before Phase2 features."
        ),
        phase2_handling=(
            "Phase2 feature builders should read daily_quotes_normalized only. "
            "Excluded raw records must not enter feature or AI inputs unless a later data-quality rule explicitly normalizes them."
        ),
    )


def save_exclusion_report(report: DailyQuoteExclusionReport, paths: RuntimePaths, output: str) -> tuple[Path | None, Path | None]:
    report_dir = paths.reports / "phase1_final"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path: Path | None = None
    markdown_path: Path | None = None
    if output in ("json", "both"):
        json_path = report_dir / f"daily_quote_exclusions_{stamp}.json"
        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    if output in ("markdown", "both"):
        markdown_path = report_dir / f"daily_quote_exclusions_{stamp}.md"
        markdown_path.write_text(render_exclusion_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_exclusion_markdown(report: DailyQuoteExclusionReport) -> str:
    lines = [
        "# Daily Quote Exclusion Inspection",
        "",
        f"- input_record_count: {report.input_record_count}",
        f"- normalized_record_count: {report.normalized_record_count}",
        f"- excluded_count: {report.excluded_count}",
        f"- recommended_policy: {report.recommended_policy}",
        f"- phase2_handling: {report.phase2_handling}",
        "",
        "## Classification Summary",
        "",
        "### By Missing Pattern",
        *_counter_lines(report.by_missing_pattern),
        "",
        "### By Estimated Reason",
        *_counter_lines(report.by_estimated_reason),
        "",
        "### By Date",
        *_counter_lines(report.by_date),
        "",
        "### By Market",
        *_counter_lines(report.by_market),
        "",
        "## Joined Listed Issue Sample",
        "",
    ]
    lines.extend(_sample_lines(report.joined_listed_issue_sample))
    lines.extend(["", "## Excluded Raw Sample", ""])
    lines.extend(_sample_lines(report.excluded_sample))
    lines.append("")
    return "\n".join(lines)


def missing_pattern(record: dict[str, Any]) -> str:
    adjusted_missing = _missing_fields(record, ADJUSTED_FIELDS)
    unadjusted_missing = _missing_fields(record, UNADJUSTED_FIELDS)
    price_fields = ADJUSTED_FIELDS[:4] + UNADJUSTED_FIELDS[:4]
    volume_fields = (ADJUSTED_FIELDS[4], UNADJUSTED_FIELDS[4])
    price_missing_all = all(record.get(field) in (None, "") for field in price_fields)
    volume_missing_all = all(record.get(field) in (None, "") for field in volume_fields)
    price_present_any = any(record.get(field) not in (None, "") for field in price_fields)
    volume_present_any = any(record.get(field) not in (None, "") for field in volume_fields)

    if len(adjusted_missing) == len(ADJUSTED_FIELDS) and len(unadjusted_missing) == len(UNADJUSTED_FIELDS):
        return "all_ohlcv_and_adjusted_ohlcv_missing"
    if price_present_any and volume_missing_all:
        return "volume_only_missing"
    if volume_present_any and price_missing_all:
        return "price_only_missing"
    if len(adjusted_missing) == len(ADJUSTED_FIELDS):
        return "adjusted_ohlcv_all_missing"
    if len(unadjusted_missing) == len(UNADJUSTED_FIELDS):
        return "unadjusted_ohlcv_all_missing"
    return "partial_ohlcv_missing"


def estimate_reason(record: dict[str, Any], listed_issue: dict[str, Any]) -> str:
    pattern = missing_pattern(record)
    name_text = " ".join(str(listed_issue.get(key) or "") for key in ("CoName", "CoNameEn", "MktNm", "Section"))
    if not listed_issue:
        return "unknown_not_joined_to_listed_issues"
    if "上場廃止" in name_text or "delist" in name_text.lower():
        return "delisted_possible"
    if "停止" in name_text or "suspend" in name_text.lower():
        return "trading_suspended_possible"
    if pattern == "all_ohlcv_and_adjusted_ohlcv_missing":
        return "unknown_no_price_volume"
    if pattern == "volume_only_missing":
        return "unknown_volume_missing"
    if pattern == "price_only_missing":
        return "unknown_price_missing"
    return "unknown_partial_market_data_missing"


def _latest_issue_by_code(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        code = str(record.get("Code") or record.get("code") or "")
        if code:
            grouped[code].append(record)
    return {code: sorted(items, key=lambda item: str(item.get("Date") or item.get("target_date") or ""))[-1] for code, items in grouped.items()}


def _missing_fields(record: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if record.get(field) in (None, "")]


def _counter_lines(counter: dict[str, int]) -> list[str]:
    if not counter:
        return ["- (none)"]
    return [f"- {key}: {value}" for key, value in counter.items()]


def _sample_lines(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- (none)"]
    return [f"- `{json.dumps(item, ensure_ascii=False, sort_keys=True)}`" for item in items]


def redact_record(record: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token"}
    return {key: value for key, value in record.items() if key.lower() not in blocked}
