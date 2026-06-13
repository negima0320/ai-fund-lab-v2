from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4aw_long_history_fetch_dry_run import run_audit
from scripts.phase4aw_long_history_fetch_dry_run import (
    READY,
    build_request_sequence,
    iter_weekdays,
    run_phase4aw_long_history_fetch_dry_run,
)


def test_phase4aw_generates_request_sequence_from_av_plan(tmp_path: Path) -> None:
    av_summary = _write_av_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"

    summary = run_phase4aw_long_history_fetch_dry_run(
        runtime_dir=tmp_path / ".runtime",
        phase4av_summary_path=av_summary,
        summary_path=summary_path,
        requests_path=requests_path,
        report_path=tmp_path / "report.md",
    )
    artifact = json.loads(requests_path.read_text(encoding="utf-8"))

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["request_count"] == 5
    assert summary["estimated_request_count"] == 5
    assert summary["request_count_match"] is True
    assert artifact["request_count"] == 5
    assert artifact["requests"][0]["params"] == {"date": "2021-03-09", "code": None, "pagination_key": None}
    assert artifact["requests"][-1]["params"]["date"] == "2021-03-15"


def test_phase4aw_request_schema_matches_dry_run_contract() -> None:
    requests = build_request_sequence(
        business_days=["2021-03-09", "2021-03-10"],
        endpoint="/v2/equities/bars/daily",
    )

    assert requests[0]["method"] == "GET"
    assert requests[0]["endpoint"] == "/v2/equities/bars/daily"
    assert requests[0]["params"]["date"] == "2021-03-09"
    assert requests[0]["params"]["code"] is None
    assert requests[0]["params"]["pagination_key"] is None
    assert requests[0]["pagination"]["enabled"] is True
    assert requests[0]["dry_run_only"] is True


def test_phase4aw_does_not_read_credentials_or_execute_downstream_steps(tmp_path: Path) -> None:
    av_summary = _write_av_summary(tmp_path)

    summary = run_phase4aw_long_history_fetch_dry_run(
        runtime_dir=tmp_path / ".runtime",
        phase4av_summary_path=av_summary,
        summary_path=tmp_path / "summary.json",
        requests_path=tmp_path / "requests.json",
        report_path=tmp_path / "report.md",
    )

    assert summary["api_call_performed"] is False
    assert summary["fetch_executed"] is False
    assert summary["credential_read_performed"] is False
    assert summary["http_client_initialized"] is False
    assert summary["raw_data_modified"] is False
    assert summary["normalized_data_modified"] is False
    assert summary["normalized_rebuild_executed"] is False
    assert summary["feature_generation_executed"] is False
    assert summary["label_generation_executed"] is False
    assert summary["dataset_rebuild_executed"] is False
    assert summary["training_executed"] is False
    assert summary["inference_executed"] is False
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False


def test_phase4aw_audit_completes(tmp_path: Path) -> None:
    av_summary = _write_av_summary(tmp_path)
    summary_path = tmp_path / "summary.json"
    requests_path = tmp_path / "requests.json"
    run_phase4aw_long_history_fetch_dry_run(
        runtime_dir=tmp_path / ".runtime",
        phase4av_summary_path=av_summary,
        summary_path=summary_path,
        requests_path=requests_path,
        report_path=tmp_path / "report.md",
    )

    result = run_audit(
        summary_path=summary_path,
        requests_path=requests_path,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["api_not_called"] is True
    assert result["checks"]["credential_not_read"] is True
    assert result["checks"]["request_count_matches_plan"] is True


def test_phase4aw_iter_weekdays_skips_weekends() -> None:
    assert iter_weekdays("2021-03-12", "2021-03-16") == [
        "2021-03-12",
        "2021-03-15",
        "2021-03-16",
    ]


def _write_av_summary(tmp_path: Path) -> Path:
    path = tmp_path / "phase4av.json"
    raw_path = tmp_path / ".runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    normalized_path = (
        tmp_path / ".runtime" / "data" / "raw_normalized_real_runtime" / "jquants" / "equities_bars_daily"
    )
    payload = {
        "readiness_status": "READY_FOR_LONG_HISTORY_FETCH_DRY_RUN",
        "preferred_fetch_start_date": "2021-03-09",
        "preferred_fetch_end_date": "2021-03-15",
        "estimated_request_count": 5,
        "endpoint": "/v2/equities/bars/daily",
        "rate_limit_policy": "Use configured J-Quants Light plan limit of 60 req/min.",
        "resume_policy": "Skip succeeded manifests and rerun failed/missing manifests.",
        "manifest_policy": "Store manifests under .runtime and reports.",
        "storage_estimate_mb": 12.5,
        "raw_output_path": str(raw_path),
        "normalized_output_path": str(normalized_path),
        "formal_training_possible_after_fetch": True,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
