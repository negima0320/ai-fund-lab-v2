from __future__ import annotations

from pathlib import Path

from ai_fund_lab_v2.ai_lifecycle.ad_u3_training_artifact_writer import stable_json_hash, validate_artifact_against_schema
from ai_fund_lab_v2.ai_lifecycle.dual_gate_artifact_writer import build_dual_gate_artifact, write_dual_gate_artifact
from ai_fund_lab_v2.ai_lifecycle.opportunity_dual_gate import aggregate_opportunity_dual_gate
from ai_fund_lab_v2.ai_lifecycle.opportunity_global_gate import evaluate_opportunity_global_gate
from ai_fund_lab_v2.ai_lifecycle.opportunity_selection_gate import candidate_selected_rows_hash, evaluate_opportunity_selection_gate, validate_candidate_population_binding
from ai_fund_lab_v2.ai_lifecycle.runtime_separation_guard import guard_runtime_gate_access, runtime_dependency_static_audit, validate_buy_suppression_reason


def _global_metrics() -> dict:
    return {
        "finite_ratio": 1.0,
        "nan_count": 0,
        "inf_count": 0,
        "collapse": False,
        "explosion": False,
        "calibration_status": "PASS",
        "ordering_preservation": True,
        "baseline_comparison": {"model_beats_zero": True, "model_beats_mean": True, "model_beats_median": True},
        "pearson_correlation": 0.12,
        "spearman_rank_correlation": 0.14,
        "prediction_distribution": {"min": -1.0, "max": 1.0, "mean": 0.0, "std": 0.4, "quantiles": {"0.5": 0.0}},
    }


def _bindings() -> dict:
    return {
        "formal_validation_artifact_id": "formal_validation_fixture",
        "formal_validation_artifact_hash": "a" * 64,
        "opportunity_model_hash": "b" * 64,
        "opportunity_scaler_hash": "c" * 64,
        "opportunity_calibration_artifact_hash": "d" * 64,
        "dataset_revision": "dataset_revision_fixture",
        "split_id": "split_fixture",
        "policy_hash": "e" * 64,
    }


def _global_semantics() -> dict:
    return {
        "baseline_comparison": {"all_true": ["model_beats_zero", "model_beats_mean", "model_beats_median"]},
        "pearson_correlation": {"minimum": 0.0},
        "spearman_rank_correlation": {"minimum": 0.0},
    }


def _rows(*, reversed_scores: bool = False, weak_top10: bool = False) -> list[dict]:
    rows = []
    for day in ("2026-01-05", "2026-01-06", "2026-01-07"):
        for rank in range(1, 51):
            strong = rank <= 20
            realized = 1.0 - rank * 0.01 if strong else -0.2 - rank * 0.001
            if weak_top10 and 6 <= rank <= 20:
                realized = -0.5
            score = float(rank if reversed_scores else 51 - rank)
            rows.append(
                {
                    "target_date": day,
                    "symbol": f"{day}-{rank:04d}",
                    "candidate_rank": rank,
                    "candidate_score": float(100 - rank),
                    "score": score,
                    "realized_return": realized,
                    "downside_bad": realized < 0,
                }
            )
    return rows


def _candidate_binding(rows: list[dict]) -> dict:
    source_hash = stable_json_hash({"candidate": "fixture"})
    return {
        "candidate_source_artifact_id": "candidate_fixture",
        "candidate_source_content_hash": source_hash,
        "expected_candidate_source_content_hash": source_hash,
        "candidate_score_field": "candidate_score",
        "candidate_pass_rule": "CandidateTop50",
        "candidate_population_size": len(rows),
        "candidate_selected_rows_hash": candidate_selected_rows_hash(rows),
    }


def _historical_mapping() -> dict:
    return {
        "metrics": [
            {"ag_metric": "Top5 realized return"},
            {"ag_metric": "Top10 realized return"},
            {"ag_metric": "Top20 realized return"},
            {"ag_metric": "Hit Rate"},
            {"ag_metric": "Downside Rate"},
            {"ag_metric": "Rank Lift"},
            {"ag_metric": "NDCG"},
            {"ag_metric": "Correlation"},
            {"ag_metric": "Top-minus-bottom"},
        ]
    }


def _selection_semantics() -> dict:
    return {
        "realized_return": {"minimum": 0.0},
        "top_minus_bottom": {"minimum": 0.0},
        "hit_rate": {"minimum": 0.5},
        "downside_rate": {"maximum": 0.5},
        "rank_lift": {"minimum": 0.0},
        "ndcg": {"minimum": 0.2},
        "spearman_rank_correlation": {"minimum": 0.0},
    }


def test_global_gate_pass_fail_and_missing_threshold_review() -> None:
    passed = evaluate_opportunity_global_gate(metric_payload=_global_metrics(), bindings=_bindings(), approved_status_semantics=_global_semantics())
    assert passed["status"] == "PASS"
    assert passed["generation_eligibility"] is True

    failed_payload = {**_global_metrics(), "explosion": True}
    failed = evaluate_opportunity_global_gate(metric_payload=failed_payload, bindings=_bindings(), approved_status_semantics=_global_semantics())
    assert failed["status"] == "FAIL"
    assert failed["generation_eligibility"] is False
    assert "prediction_explosion" in failed["reason_codes"]

    review = evaluate_opportunity_global_gate(metric_payload=_global_metrics(), bindings=_bindings(), approved_status_semantics={})
    assert review["status"] == "REVIEW_REQUIRED"
    assert review["generation_eligibility"] is False

    diagnostic = evaluate_opportunity_global_gate(
        metric_payload={**_global_metrics(), "pearson_correlation": -0.01, "spearman_rank_correlation": -0.02},
        bindings=_bindings(),
        approved_status_semantics={
            "baseline_comparison": {"status_policy": "DIAGNOSTIC_ONLY"},
            "pearson_correlation": {"status_policy": "DIAGNOSTIC_ONLY"},
            "spearman_rank_correlation": {"status_policy": "DIAGNOSTIC_ONLY"},
        },
    )
    assert diagnostic["status"] == "PASS"


def test_selection_gate_topn_fixture_and_failure_modes() -> None:
    rows = _rows()
    passed = evaluate_opportunity_selection_gate(
        rows=rows,
        candidate_binding=_candidate_binding(rows),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics=_selection_semantics(),
    )
    assert passed["status"] == "PASS"
    assert passed["metrics"]["topn"]["top5"]["realized_return_mean"] > 0
    assert passed["metrics"]["topn"]["top10"]["realized_return_mean"] > 0
    assert passed["metrics"]["topn"]["top20"]["realized_return_mean"] > 0

    weak = evaluate_opportunity_selection_gate(
        rows=_rows(weak_top10=True),
        candidate_binding=_candidate_binding(_rows(weak_top10=True)),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics=_selection_semantics(),
    )
    assert weak["status"] == "FAIL"
    assert weak["generation_eligibility"] is False

    reversed_result = evaluate_opportunity_selection_gate(
        rows=_rows(reversed_scores=True),
        candidate_binding=_candidate_binding(_rows(reversed_scores=True)),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics=_selection_semantics(),
    )
    assert reversed_result["status"] == "FAIL"

    missing_threshold = evaluate_opportunity_selection_gate(
        rows=rows,
        candidate_binding=_candidate_binding(rows),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics={},
    )
    assert missing_threshold["status"] == "REVIEW_REQUIRED"

    diagnostic = evaluate_opportunity_selection_gate(
        rows=rows,
        candidate_binding=_candidate_binding(rows),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics={
            "realized_return": {"minimum": 0.0},
            "top_minus_bottom": {"minimum": 0.0},
            "hit_rate": {"status_policy": "DIAGNOSTIC_ONLY"},
            "downside_rate": {"status_policy": "DIAGNOSTIC_ONLY"},
            "rank_lift": {"minimum": 0.0},
            "ndcg": {"status_policy": "DIAGNOSTIC_ONLY"},
            "spearman_rank_correlation": {"status_policy": "DIAGNOSTIC_ONLY"},
        },
    )
    assert diagnostic["status"] == "PASS"


def test_candidate_population_binding_blocks_mismatch() -> None:
    rows = _rows()
    binding = _candidate_binding(rows)
    assert validate_candidate_population_binding(rows=rows, binding=binding)["status"] == "PASS"

    bad_hash = {**binding, "candidate_selected_rows_hash": "0" * 64}
    assert validate_candidate_population_binding(rows=rows, binding=bad_hash)["status"] == "REVIEW_REQUIRED"

    bad_source_hash = {**binding, "candidate_source_content_hash": "0" * 64}
    result = validate_candidate_population_binding(rows=rows, binding=bad_source_hash)
    assert result["status"] == "REVIEW_REQUIRED"
    assert "candidate_source_content_hash_mismatch" in result["reason_codes"]

    bad_population = {**binding, "candidate_population_size": len(rows) + 1}
    assert validate_candidate_population_binding(rows=rows, binding=bad_population)["status"] == "REVIEW_REQUIRED"

    bad_top50_rows = rows + [{**rows[0], "symbol": "bad-rank", "candidate_rank": 51}]
    bad_top50_binding = _candidate_binding(bad_top50_rows)
    assert validate_candidate_population_binding(rows=bad_top50_rows, binding=bad_top50_binding)["status"] == "REVIEW_REQUIRED"


def test_dual_gate_aggregator_decision_table() -> None:
    global_pass = {"status": "PASS", "reason_codes": []}
    selection_pass = {"status": "PASS", "reason_codes": []}
    assert aggregate_opportunity_dual_gate(global_gate_result=global_pass, selection_gate_result=selection_pass)["status"] == "DUAL_GATE_PASS"

    global_fail = {"status": "FAIL", "reason_codes": ["global_bad"]}
    assert aggregate_opportunity_dual_gate(global_gate_result=global_fail, selection_gate_result=selection_pass)["status"] == "DUAL_GATE_FAIL"

    selection_fail = {"status": "FAIL", "reason_codes": ["selection_bad"]}
    assert aggregate_opportunity_dual_gate(global_gate_result=global_pass, selection_gate_result=selection_fail)["status"] == "DUAL_GATE_FAIL"

    review = {"status": "REVIEW_REQUIRED", "reason_codes": ["threshold_missing"]}
    assert aggregate_opportunity_dual_gate(global_gate_result=review, selection_gate_result=selection_pass)["status"] == "DUAL_GATE_REVIEW_REQUIRED"

    unavailable = {"status": "METRIC_UNAVAILABLE", "reason_codes": ["metric_missing"]}
    assert aggregate_opportunity_dual_gate(global_gate_result=global_pass, selection_gate_result=unavailable)["status"] == "DUAL_GATE_REVIEW_REQUIRED"


def test_dual_gate_artifact_schema_and_hash_inventory(tmp_path: Path) -> None:
    for name in ("candidate.json", "validation.json", "contract.md", "runtime_contract.json"):
        (tmp_path / name).write_text(name)
    global_result = evaluate_opportunity_global_gate(metric_payload=_global_metrics(), bindings=_bindings(), approved_status_semantics=_global_semantics())
    rows = _rows()
    selection_result = evaluate_opportunity_selection_gate(
        rows=rows,
        candidate_binding=_candidate_binding(rows),
        historical_metric_mapping=_historical_mapping(),
        approved_status_semantics=_selection_semantics(),
    )
    dual = aggregate_opportunity_dual_gate(global_gate_result=global_result, selection_gate_result=selection_result)
    artifact = build_dual_gate_artifact(
        artifact_id="dual_gate_fixture",
        global_gate_result=global_result,
        selection_gate_result=selection_result,
        dual_gate_result=dual,
        bindings={"formal_validation_artifact": "fixture", "candidate_source_artifact": "fixture"},
        hash_sources={
            "candidate_source_artifact": tmp_path / "candidate.json",
            "formal_validation_artifact": tmp_path / "validation.json",
            "dual_gate_contract": tmp_path / "contract.md",
            "runtime_separation_contract": tmp_path / "runtime_contract.json",
        },
    )
    result = write_dual_gate_artifact(artifact=artifact, path=tmp_path / "dual_gate_artifact.json", schema_dir=Path("schemas/ai_lifecycle"))
    assert result["status"] == "PASS"
    assert result["artifact"]["runtime_eligibility"] is False
    assert result["artifact"]["accepted"] is False
    assert validate_artifact_against_schema(result["artifact"], Path("schemas/ai_lifecycle/opportunity_dual_gate_artifact.schema.json"))["status"] == "PASS"


def test_runtime_separation_guard_and_static_audit(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime_v2"
    runtime_root.mkdir()
    (runtime_root / "producer.py").write_text("def run():\n    return 'accepted generation only'\n")
    assert runtime_dependency_static_audit(runtime_root=runtime_root)["status"] == "PASS"

    (runtime_root / "bad.py").write_text("from ai_fund_lab_v2.ai_lifecycle.opportunity_dual_gate import aggregate_opportunity_dual_gate\n")
    assert runtime_dependency_static_audit(runtime_root=runtime_root)["status"] == "BLOCK"

    blocked = guard_runtime_gate_access(action="daily_buy", referenced_authorities=["Dual Gate Evidence"])
    assert blocked["status"] == "BLOCK"

    allowed = guard_runtime_gate_access(action="daily_buy", referenced_authorities=["Accepted Generation manifest"])
    assert allowed["status"] == "PASS"

    assert validate_buy_suppression_reason("gate disagreement between global and selection")["status"] == "BLOCK"
    assert validate_buy_suppression_reason("accepted generation unavailable")["status"] == "PASS"
