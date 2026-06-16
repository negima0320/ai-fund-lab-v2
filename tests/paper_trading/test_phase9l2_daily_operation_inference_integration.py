from __future__ import annotations

import json
from pathlib import Path

from ai_fund_lab_v2.paper_trading.daily_inference_runner import INFERENCE_READY, run_daily_inference
from ai_fund_lab_v2.paper_trading.reporting.redaction_checker import check_public_report_redaction
from tests.paper_trading.test_phase9l2_daily_inference_runner import _write_l2_inputs


def test_phase9l2_reports_are_generated_and_public_outputs_are_redacted(tmp_path: Path) -> None:
    feature_root, quotes_path = _write_l2_inputs(tmp_path)

    result = run_daily_inference(
        decision_for="2026-06-15",
        data_until="2026-06-15",
        runtime_dir=tmp_path / ".runtime",
        reports_root=tmp_path / "reports",
        feature_root=feature_root,
        canonical_quotes_path=quotes_path,
        allow_initial_ledger=True,
    )

    public_report = Path(result.report_paths["public_markdown"]).read_text(encoding="utf-8")
    blog_draft = Path(result.report_paths["blog_draft"]).read_text(encoding="utf-8")
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))

    assert result.status == INFERENCE_READY
    assert check_public_report_redaction(public_report).ready
    assert check_public_report_redaction(blog_draft).ready
    assert "feature_schema_hash" not in public_report
    assert "artifact path" not in public_report.lower()
    assert "仮想運用" in blog_draft
    assert "検証中" in blog_draft
    assert "投資判断は自己責任" in blog_draft
    assert manifest["retrain_mode"] == "WEEKLY_RETRAIN_DAILY_INFERENCE"
    assert manifest["training_executed"] is False
    assert not any(manifest["prohibited_flags"].values())

