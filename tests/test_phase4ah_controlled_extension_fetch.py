from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ai_fund_lab_v2.config.settings import AppSettings, JQuantsSettings
from ai_fund_lab_v2.data_sources.jquants.client import JQuantsClientError
from ai_fund_lab_v2.runtime import RuntimePaths
from scripts.audit_phase4ah_controlled_extension_fetch import run_audit
from scripts.phase4ah_controlled_extension_fetch import READY, run_controlled_extension_fetch


def test_phase4ah_blocks_missing_phase4ag_summary(tmp_path: Path) -> None:
    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=tmp_path / "missing_summary.json",
        phase4ag_requests_path=tmp_path / "missing_requests.json",
        summary_path=tmp_path / "summary.json",
        raw_output_dir=tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        settings_loader=lambda: _settings(tmp_path, api_key="SHOULD_NOT_BE_READ"),
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_MISSING_PHASE4AG_SUMMARY"
    assert summary["credential_read_performed"] is False
    assert summary["api_call_performed"] is False
    assert summary["extension_fetch_executed"] is False


def test_phase4ah_blocks_phase4ag_not_ready(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path, readiness_status="BLOCKED_BY_TEST")

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        settings_loader=lambda: _settings(tmp_path, api_key="SHOULD_NOT_BE_READ"),
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_PHASE4AG_NOT_READY"
    assert summary["credential_read_performed"] is False


def test_phase4ah_blocks_missing_credential(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily",
        settings_loader=lambda: _settings(tmp_path, api_key=None),
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_MISSING_CREDENTIAL"
    assert summary["credential_read_performed"] is True
    assert summary["secret_present"] is False
    assert summary["api_call_performed"] is False


def test_phase4ah_controlled_fetch_success_with_pagination_and_secret_safety(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)
    raw_output_dir = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    fake_client = FakeClient(
        {
            ("2026-03-02", None): {"data": [{"Date": "2026-03-02", "Code": "7203"}], "pagination_key": "NEXT"},
            ("2026-03-02", "NEXT"): {"data": [{"Date": "2026-03-02", "Code": "6758"}]},
            ("2026-03-03", None): {"data": [{"Date": "2026-03-03", "Code": "7203"}]},
        }
    )

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=raw_output_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SUPERSECRET"),
        client_factory=lambda settings: fake_client,
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY
    assert summary["api_call_performed"] is True
    assert summary["extension_fetch_executed"] is True
    assert summary["credential_read_performed"] is True
    assert summary["http_client_initialized"] is True
    assert summary["raw_data_written"] is True
    assert summary["raw_manifest_updated"] is True
    assert summary["normalized_data_written"] is False
    assert summary["promotion_performed"] is False
    assert summary["reader_switch_performed"] is False
    assert summary["executed_extension_request_count"] == 2
    assert summary["succeeded_extension_request_count"] == 2
    assert summary["failed_extension_request_count"] == 0
    assert summary["pagination_request_count"] == 1
    assert summary["fetched_extension_row_count"] == 3
    assert summary["fetched_extension_code_count"] == 2
    assert summary["fetched_extension_date_min"] == "2026-03-02"
    assert summary["fetched_extension_date_max"] == "2026-03-03"
    assert (raw_output_dir / "manifest.json").is_file()
    assert (raw_output_dir / "request_manifests" / "2026-03-02.json").is_file()
    assert (raw_output_dir / "responses" / "2026-03-02_page_001.json").is_file()
    combined = _read_all_text(raw_output_dir, tmp_path / "summary.json")
    assert "SUPERSECRET" not in combined
    assert "Authorization" not in combined
    assert "x-api-key" not in combined


def test_phase4ah_resume_skips_success_manifest(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)
    raw_output_dir = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    manifest_dir = raw_output_dir / "request_manifests"
    response_dir = raw_output_dir / "responses"
    manifest_dir.mkdir(parents=True)
    response_dir.mkdir(parents=True)
    (manifest_dir / "2026-03-02.json").write_text(
        json.dumps({"status": "SUCCESS", "target_date": "2026-03-02"}),
        encoding="utf-8",
    )
    (response_dir / "2026-03-02_page_001.json").write_text(
        json.dumps({"payload": {"data": [{"Date": "2026-03-02", "Code": "7203"}]}}),
        encoding="utf-8",
    )
    fake_client = FakeClient({("2026-03-03", None): {"data": [{"Date": "2026-03-03", "Code": "6758"}]}})

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=raw_output_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SUPERSECRET"),
        client_factory=lambda settings: fake_client,
    )

    assert summary["status"] == "OK"
    assert summary["skipped_extension_request_count"] == 1
    assert summary["executed_extension_request_count"] == 1
    assert fake_client.calls == [("2026-03-03", None)]


def test_phase4ah_failed_request_writes_failed_manifest(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)
    raw_output_dir = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    fake_client = FailingClient()

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=raw_output_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SUPERSECRET"),
        client_factory=lambda settings: fake_client,
    )

    assert summary["status"] == "BLOCKED"
    assert summary["readiness_status"] == "BLOCKED_BY_EXTENSION_FETCH_FAILURE"
    assert summary["failed_extension_request_count"] == 2
    failed_manifest = json.loads((raw_output_dir / "request_manifests" / "2026-03-02.json").read_text())
    assert failed_manifest["status"] == "FAILED"
    assert "SUPERSECRET" not in json.dumps(failed_manifest)


def test_phase4ah_only_fetches_extension_requested_dates(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)
    raw_output_dir = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    fake_client = FakeClient(
        {
            ("2026-03-02", None): {"data": [{"Date": "2026-03-02", "Code": "7203"}]},
            ("2026-03-03", None): {"data": [{"Date": "2026-03-03", "Code": "6758"}]},
            ("2026-03-10", None): {"data": [{"Date": "2026-03-10", "Code": "9984"}]},
        }
    )

    summary = run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=tmp_path / "summary.json",
        raw_output_dir=raw_output_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SUPERSECRET"),
        client_factory=lambda settings: fake_client,
    )

    assert summary["status"] == "OK"
    assert fake_client.calls == [("2026-03-02", None), ("2026-03-03", None)]


def test_phase4ah_audit_completes_after_success(tmp_path: Path) -> None:
    phase4ag_summary, requests = _write_phase4ag_inputs(tmp_path)
    raw_output_dir = tmp_path / "runtime" / "data" / "raw" / "jquants" / "equities_bars_daily"
    fake_client = FakeClient(
        {
            ("2026-03-02", None): {"data": [{"Date": "2026-03-02", "Code": "7203"}]},
            ("2026-03-03", None): {"data": [{"Date": "2026-03-03", "Code": "6758"}]},
        }
    )
    summary_path = tmp_path / "summary.json"
    run_controlled_extension_fetch(
        phase4ag_summary_path=phase4ag_summary,
        phase4ag_requests_path=requests,
        summary_path=summary_path,
        raw_output_dir=raw_output_dir,
        settings_loader=lambda: _settings(tmp_path, api_key="SUPERSECRET"),
        client_factory=lambda settings: fake_client,
    )

    result = run_audit(
        summary_path=summary_path,
        raw_output_dir=raw_output_dir,
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert result["status"] == "complete"
    assert all(result["checks"].values())
    assert result["readiness_status"] == READY


def test_phase4ah_script_blocks_safely_without_inputs() -> None:
    script_path = Path("scripts/phase4ah_controlled_extension_fetch.py").resolve()
    import tempfile

    temp_dir = tempfile.TemporaryDirectory()
    completed = subprocess.run(
        [sys.executable, str(script_path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=temp_dir.name,
    )
    temp_dir.cleanup()

    assert "Phase4-AH controlled extension raw fetch" in completed.stdout
    assert "readiness_status=BLOCKED_BY_MISSING_PHASE4AG_SUMMARY" in completed.stdout
    assert "secret_value_logged=false" in completed.stdout
    assert "Authorization" not in completed.stdout
    assert "x-api-key" not in completed.stdout


def _write_phase4ag_inputs(tmp_path: Path, *, readiness_status: str = "READY_FOR_CONTROLLED_EXTENSION_FETCH"):
    summary_path = tmp_path / "phase4ag_summary.json"
    requests_path = tmp_path / "phase4ag_requests.json"
    dates = ["2026-03-02", "2026-03-03"]
    summary_path.write_text(
        json.dumps(
            {
                "status": "OK",
                "readiness_status": readiness_status,
                "extension_fetch_start_date": dates[0],
                "extension_fetch_end_date": dates[-1],
                "extension_requested_dates": dates,
                "extension_request_count": len(dates),
                "rate_limit_policy": "60 req/min",
                "retry_policy": "bounded transient retry",
            }
        ),
        encoding="utf-8",
    )
    requests_path.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "request_index": index,
                        "extension_request_index": index,
                        "endpoint": "/v2/equities/bars/daily",
                        "method": "GET",
                        "date": target_date,
                        "params": {"date": target_date, "code": None, "pagination_key": None},
                    }
                    for index, target_date in enumerate(dates, start=1)
                ]
            }
        ),
        encoding="utf-8",
    )
    return summary_path, requests_path


def _settings(tmp_path: Path, *, api_key: str | None) -> AppSettings:
    return AppSettings(
        runtime_paths=RuntimePaths(runtime_dir=tmp_path / "runtime"),
        jquants=JQuantsSettings(api_key=api_key, base_url="https://example.invalid", rate_limit_per_minute=60),
    )


def _read_all_text(*paths: Path) -> str:
    chunks: list[str] = []
    for path in paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
        elif path.is_dir():
            for item in sorted(path.rglob("*.json")):
                chunks.append(item.read_text(encoding="utf-8"))
    return "\n".join(chunks)


class FakeClient:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def fetch_daily_quotes(self, *, date, pagination_key=None):
        self.calls.append((date, pagination_key))
        return self.payloads[(date, pagination_key)]


class FailingClient:
    def fetch_daily_quotes(self, *, date, pagination_key=None):
        raise JQuantsClientError("safe failure without credential value")
