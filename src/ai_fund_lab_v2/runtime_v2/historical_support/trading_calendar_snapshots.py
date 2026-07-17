from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ai_fund_lab_v2.data_sources.jquants.client import JQUANTS_TRADING_CALENDAR_ENDPOINT, JQuantsClientError
from ai_fund_lab_v2.data_store.schema import validate_records

CALENDAR_STORE_SCHEMA_VERSION = "historical_trading_calendar_authority_v1"
CANONICAL_COLUMNS = ("calendar_date", "is_trading_day", "holiday_division", "source", "endpoint", "fetched_at")


@dataclass(frozen=True)
class CalendarValidation:
    status: str
    reason: str
    calendar_root: str
    data_path: str
    manifest_path: str
    row_count: int
    unique_date_count: int
    min_date: str
    max_date: str
    trading_day_count: int
    duplicate_date_count: int
    content_hash_verified: bool
    missing_required_dates: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {"schema_version": CALENDAR_STORE_SCHEMA_VERSION, **asdict(self)}


def data_path(calendar_root: Path | str) -> Path:
    return Path(calendar_root) / "data.parquet"


def manifest_path(calendar_root: Path | str) -> Path:
    return Path(calendar_root) / "manifest.json"


def index_path(calendar_root: Path | str) -> Path:
    return Path(calendar_root) / "index.json"


def validation_path(calendar_root: Path | str) -> Path:
    return Path(calendar_root) / "validation.json"


def acquisition_manifest_path(calendar_root: Path | str) -> Path:
    return Path(calendar_root) / "acquisition_manifest.json"


def normalize_calendar_records(records: list[dict[str, Any]], *, fetched_at: str) -> list[dict[str, Any]]:
    normalized = []
    for record in records:
        calendar_date = str(record.get("Date") or record.get("date") or record.get("calendar_date") or "")
        holdiv = str(record.get("HolDiv") or record.get("HolidayDivision") or record.get("holiday_division") or "")
        normalized.append(
            {
                **record,
                "calendar_date": calendar_date,
                "is_trading_day": holdiv == "1",
                "holiday_division": holdiv,
                "source": record.get("source") or "jquants",
                "endpoint": record.get("endpoint") or JQUANTS_TRADING_CALENDAR_ENDPOINT,
                "fetched_at": record.get("fetched_at") or fetched_at,
            }
        )
    return normalized


def write_calendar_authority(
    *,
    calendar_root: Path | str,
    requested_from_date: str,
    requested_to_date: str,
    records: list[dict[str, Any]],
    fetched_at: str,
    pagination_metadata: dict[str, Any] | None = None,
    skip_verified_existing: bool = True,
) -> dict[str, Any]:
    root = Path(calendar_root)
    root.mkdir(parents=True, exist_ok=True)
    normalized = normalize_calendar_records(records, fetched_at=fetched_at)
    validation = validate_records("trading_calendar", normalized)
    schema = schema_fingerprint(normalized)
    duplicate_count = duplicate_date_count(normalized)
    dates = sorted({str(record.get("calendar_date") or "") for record in normalized if record.get("calendar_date")})

    import pandas as pd

    frame = pd.DataFrame(normalized)
    temp_path = data_path(root).with_suffix(".tmp.parquet")
    frame.to_parquet(temp_path, index=False, engine="pyarrow")
    content_hash = file_hash(temp_path)

    if manifest_path(root).is_file() and data_path(root).is_file() and skip_verified_existing:
        existing = read_json(manifest_path(root))
        if str(existing.get("content_hash") or "") == content_hash:
            temp_path.unlink(missing_ok=True)
            return {
                "status": "SKIPPED",
                "classification": "VERIFIED_EXISTING",
                "reason": "existing_calendar_hash_matches",
                "content_hash": content_hash,
                "row_count": int(existing.get("row_count") or len(normalized)),
            }
        conflict_path = root / f"conflict-{hashlib.sha256(content_hash.encode()).hexdigest()[:12]}.parquet"
        temp_path.replace(conflict_path)
        return {
            "status": "HALT",
            "classification": "CONTENT_HASH_CONFLICT",
            "reason": "calendar_content_hash_differs",
            "storage_path": str(conflict_path),
            "content_hash": content_hash,
        }

    temp_path.replace(data_path(root))
    manifest = {
        "schema_version": CALENDAR_STORE_SCHEMA_VERSION,
        "requested_from_date": requested_from_date,
        "requested_to_date": requested_to_date,
        "response_min_date": dates[0] if dates else "",
        "response_max_date": dates[-1] if dates else "",
        "row_count": len(normalized),
        "unique_date_count": len(dates),
        "schema_columns": schema["columns"],
        "schema_hash": schema["schema_hash"],
        "content_hash": content_hash,
        "fetched_at": fetched_at,
        "endpoint": JQUANTS_TRADING_CALENDAR_ENDPOINT,
        "pagination_metadata": dict(pagination_metadata or {}),
        "request_classification": classify_calendar_response(
            requested_from_date=requested_from_date,
            requested_to_date=requested_to_date,
            response_min_date=dates[0] if dates else "",
            response_max_date=dates[-1] if dates else "",
            row_count=len(normalized),
        ),
        "duplicate_date_count": duplicate_count,
        "missing_date_diagnostics": missing_date_diagnostics(requested_from_date, requested_to_date, dates),
        "calendar_status_distribution": distribution(normalized, "holiday_division"),
        "market_holiday_representation": "HolDiv == '1' means trading day; other values are non-trading or special market status",
        "validation_status": validation.status,
        "source_artifact_references": {"storage_path": str(data_path(root))},
    }
    manifest_path(root).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index = build_index(root)
    validation_payload = validate_calendar_store(
        calendar_root=root,
        required_start_date=requested_from_date,
        required_end_date=requested_to_date,
    ).to_payload()
    validation_path(root).write_text(json.dumps(validation_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "PASS" if validation_payload["status"] == "PASS" and duplicate_count == 0 else "HALT",
        "classification": manifest["request_classification"],
        "reason": validation_payload["reason"],
        "manifest": manifest,
        "index": index,
        "validation": validation_payload,
    }


def build_index(calendar_root: Path | str) -> dict[str, Any]:
    root = Path(calendar_root)
    manifest = read_json(manifest_path(root)) if manifest_path(root).is_file() else {}
    payload = {
        "schema_version": CALENDAR_STORE_SCHEMA_VERSION,
        "status": "PASS" if manifest and data_path(root).is_file() else "HALT",
        "reason": "calendar_index_ready" if manifest and data_path(root).is_file() else "calendar_artifact_missing",
        "data_path": str(data_path(root)),
        "manifest_path": str(manifest_path(root)),
        "content_hash": str(manifest.get("content_hash") or ""),
        "schema_hash": str(manifest.get("schema_hash") or ""),
        "min_date": str(manifest.get("response_min_date") or ""),
        "max_date": str(manifest.get("response_max_date") or ""),
        "row_count": int(manifest.get("row_count") or 0),
        "unique_date_count": int(manifest.get("unique_date_count") or 0),
    }
    index_path(root).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def validate_calendar_store(
    *,
    calendar_root: Path | str,
    required_start_date: str = "",
    required_end_date: str = "",
) -> CalendarValidation:
    root = Path(calendar_root)
    dpath = data_path(root)
    mpath = manifest_path(root)
    if not dpath.is_file() or not mpath.is_file():
        return _validation_halt(root, "calendar_artifact_missing")
    try:
        import pandas as pd

        frame = pd.read_parquet(dpath)
    except Exception:
        return _validation_halt(root, "calendar_parquet_unreadable")
    try:
        manifest = read_json(mpath)
    except Exception:
        return _validation_halt(root, "calendar_manifest_unreadable")
    expected_hash = str(manifest.get("content_hash") or "")
    actual_hash = file_hash(dpath)
    if not expected_hash or actual_hash != expected_hash:
        return _validation_halt(root, "calendar_content_hash_mismatch")
    dates = sorted(str(value) for value in frame["calendar_date"].dropna().unique()) if "calendar_date" in frame else []
    duplicate_count = int(frame.duplicated(["calendar_date"]).sum()) if "calendar_date" in frame else 0
    missing_required = []
    if required_start_date and (not dates or dates[0] > required_start_date):
        missing_required.append(required_start_date)
    if required_end_date and (not dates or dates[-1] < required_end_date):
        missing_required.append(required_end_date)
    status = "PASS"
    reason = "calendar_authority_ready"
    if duplicate_count:
        status = "HALT"
        reason = "duplicate_calendar_date"
    elif missing_required:
        status = "REVIEW_REQUIRED"
        reason = "calendar_required_window_not_fully_covered"
    return CalendarValidation(
        status=status,
        reason=reason,
        calendar_root=str(root),
        data_path=str(dpath),
        manifest_path=str(mpath),
        row_count=int(len(frame)),
        unique_date_count=len(dates),
        min_date=dates[0] if dates else "",
        max_date=dates[-1] if dates else "",
        trading_day_count=int(frame["is_trading_day"].sum()) if "is_trading_day" in frame else 0,
        duplicate_date_count=duplicate_count,
        content_hash_verified=True,
        missing_required_dates=tuple(missing_required),
    )


def list_trading_days(calendar_path: Path | str, *, start_date: str, end_date: str) -> list[str]:
    import pandas as pd

    frame = pd.read_parquet(calendar_path)
    if "calendar_date" not in frame.columns or "is_trading_day" not in frame.columns:
        raise ValueError("canonical calendar columns missing")
    logical = frame[
        (frame["calendar_date"].astype(str) >= start_date)
        & (frame["calendar_date"].astype(str) <= end_date)
        & (frame["is_trading_day"].astype(bool))
    ]
    return sorted(str(value) for value in logical["calendar_date"].dropna().unique())


def acquire_calendar(
    *,
    client: Any,
    calendar_root: Path | str,
    start_date: str,
    end_date: str,
    max_pages: int = 100,
    retry_count: int = 3,
    sleep_seconds: float = 1.0,
    skip_verified_existing: bool = True,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    root = Path(calendar_root)
    root.mkdir(parents=True, exist_ok=True)
    if manifest_path(root).is_file() and data_path(root).is_file() and skip_verified_existing:
        validation = validate_calendar_store(calendar_root=root, required_start_date=start_date, required_end_date=end_date)
        if validation.status == "PASS":
            payload = {"status": "SKIPPED", "classification": "VERIFIED_EXISTING", "validation": validation.to_payload()}
            acquisition_manifest_path(root).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return payload
    result = _fetch_calendar_with_retry(
        client=client,
        calendar_root=root,
        start_date=start_date,
        end_date=end_date,
        max_pages=max_pages,
        retry_count=retry_count,
        skip_verified_existing=skip_verified_existing,
        progress=progress,
    )
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    acquisition_manifest_path(root).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def _fetch_calendar_with_retry(
    *,
    client: Any,
    calendar_root: Path,
    start_date: str,
    end_date: str,
    max_pages: int,
    retry_count: int,
    skip_verified_existing: bool,
    progress: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any]:
    for attempt in range(1, retry_count + 1):
        try:
            records = client.fetch_all_trading_calendar(from_date=start_date, to_date=end_date, max_pages=max_pages)
            write_result = write_calendar_authority(
                calendar_root=calendar_root,
                requested_from_date=start_date,
                requested_to_date=end_date,
                records=records,
                fetched_at=now_utc(),
                pagination_metadata={"max_pages": max_pages, "attempt": attempt},
                skip_verified_existing=skip_verified_existing,
            )
            payload = {"status": write_result["status"], "attempt": attempt, "write_result": write_result}
            if progress:
                progress(payload)
            return payload
        except JQuantsClientError as exc:
            classification = classify_error(exc.diagnostic)
            payload = {
                "status": "FAILED",
                "classification": classification,
                "attempt": attempt,
                "reason": str(exc),
                "diagnostic": sanitize_diagnostic(exc.diagnostic),
            }
            if progress:
                progress(payload)
            if classification not in {"API_RATE_LIMIT", "API_ERROR"}:
                return payload
            time.sleep(min(2**attempt, 30))
    return {"status": "FAILED", "classification": "RETRY_EXHAUSTED", "reason": "retry_count_exhausted"}


def classify_calendar_response(
    *,
    requested_from_date: str,
    requested_to_date: str,
    response_min_date: str,
    response_max_date: str,
    row_count: int,
) -> str:
    if row_count == 0:
        return "NO_DATA_FOR_RANGE"
    if response_min_date <= requested_from_date and response_max_date >= requested_to_date:
        return "FETCH_SUPPORTED_FULL_RANGE"
    if response_min_date and response_max_date:
        return "FETCH_SUPPORTED_PARTIAL_RANGE"
    return "AMBIGUOUS"


def classify_error(diagnostic: dict[str, Any]) -> str:
    status = diagnostic.get("http_status")
    error_class = str(diagnostic.get("error_class") or "")
    if status in (401, 403) or error_class == "API_AUTH_ERROR":
        return "AUTHORIZATION_OR_PLAN_LIMIT"
    if status == 400:
        return "DATE_OUT_OF_RETENTION"
    if status == 429 or error_class == "API_RATE_LIMIT":
        return "API_RATE_LIMIT"
    if error_class:
        return "API_ERROR"
    return "AMBIGUOUS"


def schema_fingerprint(records: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for record in records for key in record})
    types: dict[str, list[str]] = {}
    for column in columns:
        values = {type(record.get(column)).__name__ for record in records if record.get(column) is not None}
        types[column] = sorted(values) if values else ["null"]
    payload = {"columns": columns, "types": types}
    return {
        "columns": columns,
        "schema_hash": hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
    }


def duplicate_date_count(records: list[dict[str, Any]]) -> int:
    counts: dict[str, int] = {}
    for record in records:
        day = str(record.get("calendar_date") or record.get("Date") or "")
        counts[day] = counts.get(day, 0) + 1
    return sum(count - 1 for count in counts.values() if count > 1)


def missing_date_diagnostics(start_date: str, end_date: str, dates: list[str]) -> dict[str, Any]:
    return {
        "requested_from_date_present_or_before": bool(dates and dates[0] <= start_date),
        "requested_to_date_present_or_after": bool(dates and dates[-1] >= end_date),
        "response_min_date": dates[0] if dates else "",
        "response_max_date": dates[-1] if dates else "",
    }


def distribution(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    values: dict[str, int] = {}
    for record in records:
        value = str(record.get(key) or "")
        values[value] = values.get(value, 0) + 1
    return values


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sanitize_diagnostic(diagnostic: dict[str, Any]) -> dict[str, Any]:
    blocked = {"api_key", "token", "authorization", "x-api-key", "password", "id_token", "refresh_token", "secret"}
    return {key: value for key, value in diagnostic.items() if key.lower() not in blocked}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validation_halt(root: Path, reason: str) -> CalendarValidation:
    return CalendarValidation(
        status="HALT",
        reason=reason,
        calendar_root=str(root),
        data_path=str(data_path(root)),
        manifest_path=str(manifest_path(root)),
        row_count=0,
        unique_date_count=0,
        min_date="",
        max_date="",
        trading_day_count=0,
        duplicate_date_count=0,
        content_hash_verified=False,
    )
