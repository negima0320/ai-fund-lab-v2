from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_phase4ar_candidate_output_smoke import (
    BLOCKED_LEAKAGE,
    BLOCKED_MISSING,
    BLOCKED_RESPONSIBILITY,
    BLOCKED_SCHEMA,
    READY_FORMAL_AUDIT,
    READY_WITH_QUALITY_BLOCK,
    audit_candidate_schema,
    audit_forbidden_terms,
    audit_phase4ar_candidate_output_smoke,
    calculate_score_stats,
    resolve_readiness,
)


def test_phase4ar_detects_all_same_score_quality_block(tmp_path: Path) -> None:
    aq_summary = _prepare_fixture(tmp_path, scores=[0.1] * 50)

    summary = audit_phase4ar_candidate_output_smoke(
        phase4aq_summary_path=aq_summary,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert summary["status"] == "OK"
    assert summary["readiness_status"] == READY_WITH_QUALITY_BLOCK
    assert summary["candidate_count"] == 50
    assert summary["candidate_rank_valid"] is True
    assert summary["unique_candidate_score_count"] == 1
    assert summary["all_same_score"] is True
    assert summary["ranking_effective"] is False
    assert summary["responsibility_boundary_status"] == "OK"
    assert summary["backtest_executed"] is False
    assert summary["trading_executed"] is False
    assert summary["broker_api_called"] is False
    assert summary["order_executed"] is False


def test_phase4ar_ready_when_scores_vary_and_ranking_effective(tmp_path: Path) -> None:
    aq_summary = _prepare_fixture(tmp_path, scores=[1.0 - index * 0.01 for index in range(50)])

    summary = audit_phase4ar_candidate_output_smoke(
        phase4aq_summary_path=aq_summary,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert summary["readiness_status"] == READY_FORMAL_AUDIT
    assert summary["unique_candidate_score_count"] == 50
    assert summary["all_same_score"] is False
    assert summary["ranking_effective"] is True


def test_phase4ar_blocks_missing_artifact(tmp_path: Path) -> None:
    aq_summary = tmp_path / "aq_summary.json"
    aq_summary.write_text(json.dumps({"top50_json_path": str(tmp_path / "missing.json")}), encoding="utf-8")

    summary = audit_phase4ar_candidate_output_smoke(
        phase4aq_summary_path=aq_summary,
        summary_path=tmp_path / "summary.json",
        json_report_path=tmp_path / "audit.json",
        markdown_report_path=tmp_path / "audit.md",
    )

    assert summary["readiness_status"] == BLOCKED_MISSING
    assert summary["candidate_artifact_detected"] is False


def test_phase4ar_schema_requires_50_candidates_and_valid_rank() -> None:
    rows = [_candidate_row(index + 1, 0.1) for index in range(49)]
    assert audit_candidate_schema(rows)["status"] == "ERROR"

    rows = [_candidate_row(index + 1, 0.1) for index in range(50)]
    rows[10]["candidate_rank"] = 1
    result = audit_candidate_schema(rows)
    assert result["status"] == "ERROR"
    assert result["candidate_rank_valid"] is False


def test_phase4ar_forbidden_terms_block_responsibility_boundary() -> None:
    leakage = audit_forbidden_terms({"rows": [{"future_return_20d": 0.1, "buy_signal": True, "order_id": "x"}]})

    assert leakage["status"] == "ERROR"
    assert leakage["future_column_detected"] is True
    assert leakage["buy_sell_hold_detected"] is True
    assert leakage["order_detected"] is True
    assert resolve_readiness(
        schema_ok=True,
        leakage_ok=False,
        responsibility_status="OK",
        all_same_score=False,
        ranking_effective=True,
    ) == BLOCKED_LEAKAGE
    assert resolve_readiness(
        schema_ok=True,
        leakage_ok=True,
        responsibility_status="ERROR",
        all_same_score=False,
        ranking_effective=True,
    ) == BLOCKED_RESPONSIBILITY


def test_phase4ar_score_stats() -> None:
    stats = calculate_score_stats([_candidate_row(1, 0.1), _candidate_row(2, 0.2), _candidate_row(3, 0.3)])

    assert stats["candidate_score_min"] == 0.1
    assert stats["candidate_score_max"] == 0.3
    assert stats["unique_candidate_score_count"] == 3
    assert resolve_readiness(
        schema_ok=False,
        leakage_ok=True,
        responsibility_status="OK",
        all_same_score=False,
        ranking_effective=True,
    ) == BLOCKED_SCHEMA


def test_phase4ar_report_documents_quality_block() -> None:
    report = Path("docs/phase_reports/phase4ar_candidate_output_smoke.md").read_text(encoding="utf-8")

    assert "TECHNICAL_PHASE4_SMOKE_COMPLETE_WITH_MODEL_QUALITY_BLOCKED" in report
    assert "all-same-score" in report
    assert "buy / sell / hold" in report


def _prepare_fixture(tmp_path: Path, *, scores: list[float]) -> Path:
    candidate_path = tmp_path / "top50.json"
    inference_path = tmp_path / "scores.json"
    rows = [_candidate_row(index + 1, score) for index, score in enumerate(scores)]
    candidate_path.write_text(json.dumps({"rows": rows, "target_date": "2026-05-29"}), encoding="utf-8")
    inference_path.write_text(json.dumps({"rows": rows, "scored_count": 50}), encoding="utf-8")
    aq_summary = tmp_path / "aq_summary.json"
    aq_summary.write_text(
        json.dumps(
            {
                "target_date": "2026-05-29",
                "top50_json_path": str(candidate_path),
                "inference_output_path": str(inference_path),
                "candidate_count": 50,
                "scored_count": 50,
                "eligible_input_count": 50,
                "production_model_promoted": False,
                "backtest_executed": False,
                "trading_executed": False,
                "paper_trading_executed": False,
                "broker_api_called": False,
                "order_executed": False,
            }
        ),
        encoding="utf-8",
    )
    return aq_summary


def _candidate_row(rank: int, score: float) -> dict[str, object]:
    return {
        "target_date": "2026-05-29",
        "code": f"{1000 + rank}",
        "candidate_score": score,
        "candidate_rank": rank,
        "candidate_reason": "smoke_score_ranked",
        "excluded_reason": "",
        "feature_snapshot_id": "snapshot",
        "model_version": "phase4ap_candidate_smoke",
        "audit_flags": ["smoke_model", "not_buy_decision", "not_production_model"],
    }
