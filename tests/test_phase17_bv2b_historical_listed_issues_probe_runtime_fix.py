from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def load_probe_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "probe_historical_listed_issues.py"
    spec = importlib.util.spec_from_file_location("probe_historical_listed_issues", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeClient:
    def __init__(self, records=None, error=None):
        self.records = records if records is not None else []
        self.error = error

    def fetch_all_listed_issues(self, *, date=None, code=None, max_pages=100):
        if self.error:
            raise self.error
        return list(self.records)


def args_for(tmp_path: Path, storage_format: str = "parquet"):
    return SimpleNamespace(probe_root=tmp_path / "probe", storage_format=storage_format, max_pages=100)


def settings_stub():
    return SimpleNamespace(jquants=SimpleNamespace())


def listed_issue(date: str, code: str, page: int = 1):
    return {
        "Date": date,
        "Code": code,
        "CoName": f"Company {code}",
        "Mkt": "0101",
        "pagination_page": page,
    }


def test_bv2b_fetch_result_without_storage_format_reads_parquet(monkeypatch, tmp_path):
    probe = load_probe_module()
    records = [listed_issue("2026-06-29", "13010")]
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(records=records))

    result = probe.run_probe_for_date(args_for(tmp_path, "parquet"), settings_stub(), "2026-06-29")

    assert result["classification"] == "FETCH_SUPPORTED_EXACT_DATE"
    assert result["storage_format"] == "parquet"
    assert result["row_count"] == 1
    assert result["request_date"] == "2026-06-29"
    assert result["response_date_unique"] == ["2026-06-29"]
    assert Path(result["storage_path"]).is_file()
    assert not hasattr(probe, "storage_format")


def test_bv2b_jsonl_storage_authority(monkeypatch, tmp_path):
    probe = load_probe_module()
    records = [listed_issue("2026-07-06", "13010")]
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(records=records))

    result = probe.run_probe_for_date(args_for(tmp_path, "jsonl"), settings_stub(), "2026-07-06")

    assert result["classification"] == "FETCH_SUPPORTED_EXACT_DATE"
    assert result["storage_format"] == "jsonl"
    assert result["storage_path"].endswith(".jsonl")


def test_bv2b_multiple_pages_and_response_date_semantics(monkeypatch, tmp_path):
    probe = load_probe_module()
    records = [
        listed_issue("2026-06-28", "13010", page=1),
        listed_issue("2026-06-28", "13050", page=2),
    ]
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(records=records))

    result = probe.run_probe_for_date(args_for(tmp_path, "parquet"), settings_stub(), "2026-06-29")

    assert result["classification"] == "FETCH_SUPPORTED_WITH_PROVIDER_DATE_NORMALIZATION"
    assert result["pagination_pages"] == [1, 2]
    assert result["request_date"] == "2026-06-29"
    assert result["response_date_unique"] == ["2026-06-28"]
    assert "snapshot effective date" in result["snapshot_date_semantics"]["response_Date"]


def test_bv2b_empty_response_is_explicit_no_data(monkeypatch, tmp_path):
    probe = load_probe_module()
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(records=[]))

    result = probe.run_probe_for_date(args_for(tmp_path, "jsonl"), settings_stub(), "2026-06-28")

    assert result["classification"] == "NO_DATA_FOR_DATE"
    assert result["row_count"] == 0
    assert result["validation_status"] == "OK"


def test_bv2b_api_error_is_recorded_without_secret(monkeypatch, tmp_path):
    probe = load_probe_module()
    error = probe.JQuantsClientError(
        "J-Quants request failed",
        diagnostic={
            "endpoint": "/v2/equities/master",
            "date": "2021-01-04",
            "http_status": 400,
            "error_class": "API_PARAM_ERROR",
            "api_key": "SECRET_CANARY",
            "token": "SECRET_CANARY",
            "secret": "SECRET_CANARY",
        },
    )
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(error=error))

    result = probe.run_probe_for_date(args_for(tmp_path, "parquet"), settings_stub(), "2021-01-04")

    serialized = json.dumps(result, sort_keys=True)
    assert result["classification"] == "DATE_OUT_OF_RETENTION"
    assert "SECRET_CANARY" not in serialized
    assert result["records_saved"] == 0


def test_bv2b_runtime_storage_mismatch_is_fail_closed(tmp_path):
    probe = load_probe_module()
    date_root = tmp_path / "probe" / "2026-06-29"
    manifest = date_root / "data" / "raw" / "jquants" / "manifest.jsonl"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "storage_format": "jsonl",
                "storage_path": str(date_root / "data" / "raw" / "jquants" / "listed_issues" / "data.jsonl"),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        probe.resolve_storage_format_authority(
            date_root=date_root,
            requested_storage_format="parquet",
            data_path=date_root / "data" / "raw" / "jquants" / "listed_issues" / "data.parquet",
        )
    except RuntimeError as exc:
        assert "storage format mismatch" in str(exc)
    else:
        raise AssertionError("storage mismatch must fail closed")


def test_bv2b_probe_root_is_isolated(monkeypatch, tmp_path):
    probe = load_probe_module()
    outside = tmp_path / "outside" / "data.parquet"
    records = [listed_issue("2026-07-06", "13010")]
    monkeypatch.setattr(probe, "JQuantsClient", lambda settings, paths: FakeClient(records=records))

    result = probe.run_probe_for_date(args_for(tmp_path, "parquet"), settings_stub(), "2026-07-06")

    assert Path(result["storage_path"]).is_relative_to(tmp_path / "probe")
    assert not outside.exists()
