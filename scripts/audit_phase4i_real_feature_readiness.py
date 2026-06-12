from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_fund_lab_v2.broker.sanitizer import sanitize_mapping  # noqa: E402


PHASE = "Phase4-I Real Feature Dry-run Readiness Audit"
PYTEST_HINT = (
    "python3 scripts/audit_phase4i_real_feature_readiness.py && "
    "python3 -m pytest tests/test_phase4i_real_feature_readiness.py && "
    "python3 -m pytest -q"
)

DEFAULT_FEATURE_PATH = ROOT / ".runtime/candidate_ai/features/candidate_features_real_dry_run_2026-06-01.json"
DEFAULT_MANIFEST_PATH = ROOT / ".runtime/candidate_ai/manifests/candidate_features_real_dry_run_manifest_2026-06-01.json"
DEFAULT_AUDIT_PATH = ROOT / ".runtime/candidate_ai/audit/candidate_features_real_dry_run_audit_2026-06-01.json"
DEFAULT_SUMMARY_PATH = ROOT / "reports/candidate_ai/phase4h_real_feature_dry_run_summary.json"

REQUIRED_DOCS_AND_OUTPUTS = (
    ROOT / "docs/phase_reports/phase4h_real_feature_dry_run.md",
    ROOT / "docs/phase_reports/phase4h_real_feature_dry_run_audit.md",
    ROOT / "reports/phase_reports/phase4h_real_feature_dry_run_audit.json",
)

REQUIRED_FEATURE_COLUMNS = (
    "price_momentum_return_5d",
    "price_momentum_return_20d",
    "volume_momentum_ratio_5d",
    "volatility_return_std_20d",
    "trend_close_over_ma_20d",
    "liquidity_avg_volume_20d",
    "missing_flags_insufficient_lookback",
)

BLOCKED_IMPLEMENTATION_TERMS = (
    "def train",
    "def predict",
    "def backtest",
    "def generate_labels",
    "submit_order",
    "place_order",
    "BrokerLive",
    "PaperTrading",
)


def run_audit(
    *,
    feature_path: Path | str = DEFAULT_FEATURE_PATH,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    audit_path: Path | str = DEFAULT_AUDIT_PATH,
    summary_path: Path | str = DEFAULT_SUMMARY_PATH,
    json_report_path: Path | str = "reports/phase_reports/phase4i_real_feature_readiness_audit.json",
    markdown_report_path: Path | str = "docs/phase_reports/phase4i_real_feature_readiness_audit.md",
) -> dict[str, Any]:
    feature_path = Path(feature_path)
    manifest_path = Path(manifest_path)
    audit_path = Path(audit_path)
    summary_path = Path(summary_path)

    feature_payload = _read_json(feature_path)
    manifest_payload = _read_json(manifest_path)
    audit_payload = _read_json(audit_path)
    summary_payload = _read_json(summary_path)
    rows = [dict(row) for row in feature_payload.get("rows", [])] if feature_payload else []
    row_count = int(audit_payload.get("row_count", len(rows)) or 0)
    eligible_count = int(audit_payload.get("eligible_count", _count_eligible(rows)) or 0)
    excluded_count = int(audit_payload.get("excluded_count", row_count - eligible_count) or 0)
    excluded_reason_counts = dict(audit_payload.get("excluded_reason_counts") or _excluded_reason_counts(rows))
    generated_feature_columns = _feature_columns(rows)
    missing_feature_columns = [column for column in REQUIRED_FEATURE_COLUMNS if column not in generated_feature_columns]
    null_counts = _null_counts(rows, generated_feature_columns)
    schema_validation_status = _status_from_summary_or_audit(summary_payload, audit_payload, "schema_validation_status")
    leakage_audit_status = _status_from_summary_or_audit(summary_payload, audit_payload, "leakage_audit_status")
    readiness_status, readiness_reason = _readiness_status(
        outputs_exist=bool(feature_payload and manifest_payload and audit_payload),
        row_count=row_count,
        eligible_count=eligible_count,
        excluded_reason_counts=excluded_reason_counts,
        schema_validation_status=schema_validation_status,
        leakage_audit_status=leakage_audit_status,
        missing_feature_columns=missing_feature_columns,
    )
    next_actions = _next_actions(readiness_status)
    result = sanitize_mapping(
        {
            "phase": PHASE,
            "status": "complete" if readiness_status != "SKIPPED" else "skipped",
            "readiness_status": readiness_status,
            "readiness_reason": readiness_reason,
            "checks": {
                "required_phase4h_docs_present": all(path.is_file() for path in REQUIRED_DOCS_AND_OUTPUTS),
                "feature_output_exists_or_skipped": feature_path.is_file() or summary_payload.get("status") == "SKIPPED",
                "manifest_output_exists_or_skipped": manifest_path.is_file() or summary_payload.get("status") == "SKIPPED",
                "audit_output_exists_or_skipped": audit_path.is_file() or summary_payload.get("status") == "SKIPPED",
                "schema_validation_ok_or_skipped": schema_validation_status in {"OK", "SKIPPED"},
                "leakage_audit_ok_or_skipped": leakage_audit_status in {"OK", "SKIPPED"},
                "required_features_checked": not missing_feature_columns or not rows,
                "forbidden_implementation_absent": _forbidden_implementation_absent(),
            },
            "review": {
                "row_count": row_count,
                "eligible_count": eligible_count,
                "excluded_count": excluded_count,
                "excluded_reason_counts": excluded_reason_counts,
                "generated_feature_columns": generated_feature_columns,
                "missing_feature_columns": missing_feature_columns,
                "null_counts": null_counts,
                "schema_validation_status": schema_validation_status,
                "leakage_audit_status": leakage_audit_status,
                "dropped_future_row_count": int(audit_payload.get("dropped_future_row_count", manifest_payload.get("dropped_future_row_count", 0)) or 0),
                "storage_format": manifest_payload.get("storage_format") or summary_payload.get("storage_format"),
                "normalized_as_of_date": manifest_payload.get("normalized_as_of_date") or summary_payload.get("normalized_as_of_date"),
                "window_start_date": manifest_payload.get("window_start_date") or summary_payload.get("window_start_date"),
                "feature_data_start_date_min": _min_row_value(rows, "data_start_date"),
                "feature_data_end_date_max": _max_row_value(rows, "data_end_date"),
            },
            "cause_analysis": _cause_analysis(rows, excluded_reason_counts, manifest_payload),
            "next_actions": next_actions,
            "pytest_hint": PYTEST_HINT,
            "reports": {"json": str(json_report_path), "markdown": str(markdown_report_path)},
        }
    )
    _write_json(Path(json_report_path), result)
    _write_markdown(Path(markdown_report_path), result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit Phase4-I real feature dry-run readiness.")
    parser.add_argument("--feature-path", default=str(DEFAULT_FEATURE_PATH))
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--audit-path", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--json-report", default="reports/phase_reports/phase4i_real_feature_readiness_audit.json")
    parser.add_argument("--markdown-report", default="docs/phase_reports/phase4i_real_feature_readiness_audit.md")
    args = parser.parse_args(argv)
    result = run_audit(
        feature_path=args.feature_path,
        manifest_path=args.manifest_path,
        audit_path=args.audit_path,
        summary_path=args.summary_path,
        json_report_path=args.json_report,
        markdown_report_path=args.markdown_report,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result["status"] in {"complete", "skipped"} else 1


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _status_from_summary_or_audit(summary: dict[str, Any], audit: dict[str, Any], summary_key: str) -> str:
    audit_status = str(audit.get("status") or "")
    summary_status = str(summary.get(summary_key) or "")
    if audit_status == "OK":
        return "OK"
    return summary_status or audit_status or "UNKNOWN"


def _count_eligible(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row.get("universe_eligible") is True)


def _excluded_reason_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        if row.get("universe_eligible") is True:
            continue
        counter[str(row.get("excluded_reason") or "unknown")] += 1
    return dict(counter)


def _feature_columns(rows: list[dict[str, Any]]) -> list[str]:
    prefixes = (
        "price_momentum_",
        "volume_momentum_",
        "volatility_",
        "trend_",
        "liquidity_",
        "missing_flags_",
    )
    columns: set[str] = set()
    for row in rows:
        columns.update(column for column in row if column.startswith(prefixes))
    return sorted(columns)


def _null_counts(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, int]:
    return {column: sum(1 for row in rows if row.get(column) is None) for column in columns}


def _readiness_status(
    *,
    outputs_exist: bool,
    row_count: int,
    eligible_count: int,
    excluded_reason_counts: dict[str, int],
    schema_validation_status: str,
    leakage_audit_status: str,
    missing_feature_columns: list[str],
) -> tuple[str, str]:
    if not outputs_exist:
        return "SKIPPED", "Phase4-H output is missing; readiness audit skipped safely."
    if schema_validation_status != "OK":
        return "BLOCKED_BY_SCHEMA", "Feature schema validation is not OK."
    if leakage_audit_status != "OK":
        return "BLOCKED_BY_LEAKAGE", "Leakage audit is not OK."
    if row_count <= 0 or missing_feature_columns:
        return "BLOCKED_BY_RUNTIME_OUTPUT", "Feature output is empty or missing required feature columns."
    if eligible_count <= 0 and excluded_reason_counts.get("insufficient_lookback") == row_count:
        return (
            "BLOCKED_BY_DATA_WINDOW",
            "All rows were excluded by insufficient_lookback; current dry-run window does not provide enough per-code history.",
        )
    return "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN", "Dry-run output is ready for broader feature dry-run."


def _next_actions(readiness_status: str) -> list[str]:
    if readiness_status == "BLOCKED_BY_DATA_WINDOW":
        return [
            "Select an as_of_date with enough historical normalized data behind it.",
            "Ensure lookback_business_days >= 60 for broader dry-run.",
            "Increase max_rows to at least code_count x lookback rows.",
            "Ensure reader preserves enough per-code history before feature generation.",
        ]
    if readiness_status == "READY_FOR_FULL_RANGE_FEATURE_DRY_RUN":
        return [
            "Run a broader but still capped feature dry-run.",
            "Compare eligible/excluded distribution by as_of_date.",
            "Keep labels, training, inference, and backtest out of scope.",
        ]
    if readiness_status == "SKIPPED":
        return ["Regenerate Phase4-H outputs before readiness review."]
    return ["Fix the blocking schema/leakage/runtime issue before expanding scope."]


def _cause_analysis(rows: list[dict[str, Any]], excluded_reason_counts: dict[str, int], manifest: dict[str, Any]) -> dict[str, Any]:
    row_count = len(rows)
    all_insufficient = bool(row_count and excluded_reason_counts.get("insufficient_lookback") == row_count)
    start_dates = sorted({str(row.get("data_start_date")) for row in rows if row.get("data_start_date")})
    end_dates = sorted({str(row.get("data_end_date")) for row in rows if row.get("data_end_date")})
    return {
        "all_rows_insufficient_lookback": all_insufficient,
        "likely_cause": (
            "Expected dry-run limitation: current input window contains too few per-code rows for MIN_LOOKBACK_ROWS=21."
            if all_insufficient
            else "No universal insufficient_lookback issue detected."
        ),
        "data_window_observation": {
            "data_start_date_min": start_dates[0] if start_dates else None,
            "data_end_date_max": end_dates[-1] if end_dates else None,
            "window_start_date": manifest.get("window_start_date"),
            "normalized_as_of_date": manifest.get("normalized_as_of_date"),
            "lookback_business_days": manifest.get("lookback_business_days"),
            "max_codes": manifest.get("max_codes"),
            "max_rows": manifest.get("max_rows"),
        },
        "ruled_out": [
            "schema validation problem" if manifest else "manifest missing",
            "leakage audit problem" if manifest else "audit missing",
            "feature builder lookback bug is unlikely because MIN_LOOKBACK_ROWS=21 and rows only contain insufficient history",
        ],
    }


def _min_row_value(rows: list[dict[str, Any]], key: str) -> str | None:
    values = sorted(str(row.get(key)) for row in rows if row.get(key))
    return values[0] if values else None


def _max_row_value(rows: list[dict[str, Any]], key: str) -> str | None:
    values = sorted(str(row.get(key)) for row in rows if row.get(key))
    return values[-1] if values else None


def _forbidden_implementation_absent() -> bool:
    paths = [
        ROOT / "src/ai_fund_lab_v2/candidate_ai/feature_builder.py",
        ROOT / "src/ai_fund_lab_v2/candidate_ai/normalized_data_reader.py",
        ROOT / "scripts/build_candidate_features_real_dry_run.py",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.is_file())
    return all(term not in text for term in BLOCKED_IMPLEMENTATION_TERMS)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    review = payload["review"]
    lines = [
        "# AI Fund Lab vNext Phase4-I Real Feature Dry-run Readiness Audit",
        "",
        "## Audit Result",
        "",
        f"- phase: `{payload['phase']}`",
        f"- status: `{payload['status']}`",
        f"- readiness_status: `{payload['readiness_status']}`",
        f"- readiness_reason: {payload['readiness_reason']}",
        "",
        "## Dry-run Review",
        "",
        f"- row_count: `{review['row_count']}`",
        f"- eligible_count: `{review['eligible_count']}`",
        f"- excluded_count: `{review['excluded_count']}`",
        f"- excluded_reason_counts: `{review['excluded_reason_counts']}`",
        f"- schema_validation_status: `{review['schema_validation_status']}`",
        f"- leakage_audit_status: `{review['leakage_audit_status']}`",
        f"- storage_format: `{review['storage_format']}`",
        f"- normalized_as_of_date: `{review['normalized_as_of_date']}`",
        f"- window_start_date: `{review['window_start_date']}`",
        "",
        "## Feature Completeness",
        "",
        f"- generated_feature_columns: `{review['generated_feature_columns']}`",
        f"- missing_feature_columns: `{review['missing_feature_columns']}`",
        f"- null_counts: `{review['null_counts']}`",
        "",
        "## Cause Analysis",
        "",
        f"- likely_cause: {payload['cause_analysis']['likely_cause']}",
        "",
        "## Next Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in payload["next_actions"])
    lines.extend(
        [
            "",
            "## Forbidden Scope",
            "",
            "Label generation, dataset builder, Candidate AI body, training, inference, backtest, trading, broker live access, ordering, and portfolio auto-update are not implemented.",
            "",
            "## pytest",
            "",
            f"`{payload['pytest_hint']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
