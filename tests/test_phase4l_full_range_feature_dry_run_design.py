from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.audit_phase4l_full_range_feature_dry_run_design import run_audit


DESIGN_DOC = Path("docs/phase_reports/phase4l_full_range_feature_dry_run_design.md")


def test_phase4l_audit_script_runs() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_phase4l_full_range_feature_dry_run_design.py"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "complete"
    assert payload["readiness_decision"] == "DESIGN_READY_FOR_PHASE4_M"


def test_phase4l_audit_writes_reports(tmp_path: Path) -> None:
    result = run_audit(
        json_report_path=tmp_path / "phase4l.json",
        markdown_report_path=tmp_path / "phase4l.md",
    )

    assert result["status"] == "complete"
    assert result["checks"]["design_doc_exists"]
    assert (tmp_path / "phase4l.json").is_file()
    assert (tmp_path / "phase4l.md").is_file()


def test_phase4l_design_includes_chunking_resume_and_storage() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    for term in (
        "chunk_id",
        "date_start",
        "date_end",
        "code_count",
        "eligible_count",
        "excluded_count",
        "成功済みchunkはskip",
        "失敗chunkは再実行",
        "tmp -> final atomic move",
        ".runtime/candidate_ai/features/full_range/",
        ".runtime/candidate_ai/manifests/full_range/",
        ".runtime/candidate_ai/audit/full_range/",
        "reports/candidate_ai/full_range/",
    ):
        assert term in text


def test_phase4l_design_separates_data_source_types() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    assert "mock normalized history" in text
    assert "real_runtime normalized history" in text
    assert "J-Quants API由来 normalized history" in text
    assert "skipped" in text
    assert "Phase4-Kはmock normalized history" in text


def test_phase4l_design_defines_audit_and_readiness_gates() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    for term in (
        "future系feature混入なし",
        "backtest/trade/portfolio/order/cash混入なし",
        "as_of_dateより未来データ使用なし",
        "required feature columns存在",
        "source_snapshot_id記録",
        "data_source_type記録",
        "failed_chunk_count = 0",
        "eligible_count total > 0",
        "feature_version fixed",
        "schema_version fixed",
    ):
        assert term in text


def test_phase4l_design_preserves_candidate_ai_boundary() -> None:
    text = DESIGN_DOC.read_text(encoding="utf-8")

    for term in ("買い判断", "売却判断", "資金配分", "Paper Trading", "発注", "Portfolio更新"):
        assert term in text


def test_phase4l_does_not_add_generation_training_or_trading_code() -> None:
    source = Path("scripts/audit_phase4l_full_range_feature_dry_run_design.py").read_text(encoding="utf-8")

    for forbidden in ("def train", "def predict", "def backtest", "def generate_labels", "submit_order", "place_order"):
        assert forbidden not in source
