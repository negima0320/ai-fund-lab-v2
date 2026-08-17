from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.buy_ai.producer import (
    _apply_candidate_pit_quality_surface,
    _buy_quality_feature_metadata,
)


def test_phase30_aj2r3_semantic_hybrid_ordering_class_sentinels() -> None:
    rows = [
        _strong("1001", score=0.90, rank=2),
        _caution("1002", score=0.99, rank=1),
        _strong("1003", score=0.49, rank=6),
        _valid("1004", score=0.40, rank=7),
        _strong("1005", score=0.00, rank=8),
        _missing("1006", score=0.80, rank=3),
        _caution("1007", score=0.70, rank=4),
    ]

    ordered, evidence = _apply_candidate_pit_quality_surface(rows, top_n=7)
    symbols = [row["code"] for row in ordered]
    by_code = {row["code"]: row for row in ordered}

    assert symbols == ["1001", "1002", "1007", "1003", "1006", "1004", "1005"]
    assert by_code["1001"]["score_evidence_class"] == "STRONG_DISCOVERY_SCORE"
    assert by_code["1001"]["semantic_hybrid_class"] == "CONFIRMED_DISCOVERY_AND_SURFACE"
    assert by_code["1002"]["semantic_hybrid_class"] == "CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE"
    assert by_code["1003"]["score_evidence_class"] == "MODERATE_DISCOVERY_SCORE"
    assert by_code["1003"]["semantic_hybrid_class"] == "CONFLICT_RESOLUTION_HIGH_DISCOVERY_OR_STRONG_SURFACE"
    assert by_code["1004"]["semantic_hybrid_class"] == "VALID_BUT_INCOMPLETE_CONFIRMATION"
    assert by_code["1005"]["score_evidence_class"] == "WEAK_DISCOVERY_SCORE"
    assert by_code["1005"]["semantic_hybrid_class"] == "LOW_CONVICTION_OR_SURFACE_ONLY_CHALLENGER"
    assert by_code["1006"]["semantic_hybrid_class"] == "VALID_BUT_INCOMPLETE_CONFIRMATION"
    assert symbols.index("1002") < symbols.index("1007") < symbols.index("1003")
    assert symbols.index("1002") < symbols.index("1005")
    assert evidence["ordering_contract"] == (
        "SEMANTIC_HYBRID_ELIGIBILITY_BANDS_WITH_CANDIDATE_SCORE_WITHIN_CLASS_AUTHORITY"
    )
    assert evidence["candidate_score_role"] == "CO_EQUAL_HYBRID_EVIDENCE"
    assert evidence["candidate_surface_role"] == "SEMANTIC_HYBRID_AUTHORITY"
    assert evidence["hard_lexicographic_surface_first_retired"] is True
    assert evidence["score_only_dominance_retired"] is True
    assert evidence["candidate_model_retrained"] is False
    assert evidence["candidate_accepted_generation_changed"] is False


def test_phase30_aj2r3_hybrid_surface_remains_action_effective_without_score_only_recurrence() -> None:
    rows = [
        _caution("2001", score=0.99, rank=1),
        _missing("2002", score=0.98, rank=2),
        _strong("2003", score=0.90, rank=3),
    ]

    top2, evidence = _apply_candidate_pit_quality_surface(rows, top_n=2)
    symbols = [row["code"] for row in top2]
    by_code = {row["code"]: row for row in top2}

    assert symbols == ["2003", "2001"]
    assert "2003" in evidence["quality_aware_added_symbols"]
    assert "2002" in evidence["quality_aware_removed_symbols"]
    assert by_code["2003"]["candidate_rank"] == 3
    assert by_code["2003"]["quality_aware_candidate_rank"] == 1
    assert evidence["score_only_ordering_changed"] is True


def test_phase30_aj2r3_top50_count_preserved() -> None:
    rows = [
        _strong("3001", score=0.90, rank=1),
        _caution("3002", score=0.99, rank=2),
        *[
            _valid(f"{3100 + index}", score=0.80 - index * 0.01, rank=3 + index)
            for index in range(60)
        ],
    ]

    top50, evidence = _apply_candidate_pit_quality_surface(rows, top_n=50)

    assert len(top50) == 50
    assert evidence["top_n"] == 50
    assert evidence["candidate_top50_count_changed"] is False
    assert evidence["top50_semantic_hybrid_class_distribution"]


def test_phase30_aj3b_liquidity_available_restores_surface_sufficiency() -> None:
    source_row = _strong("4001", score=0.90, rank=1)
    metadata = _buy_quality_feature_metadata(source_row)
    row = {
        **source_row,
        **metadata,
    }

    top1, evidence = _apply_candidate_pit_quality_surface(
        [row],
        top_n=1,
        liquidity_lineage_evidence={
            "source_artifact": "fixture/candidate_features.parquet",
            "source_field": "liquidity_avg_volume_20d",
            "source_date": "2026-07-07",
            "as_of_date": "2026-07-07",
            "business_date": "2026-07-08",
            "pit_safety": {"feature_date_lte_business_date": True},
            "missing_status": "PASS",
            "present_row_count": 1,
            "missing_row_count": 0,
            "total_row_count": 1,
            "canonical_liquidity_authority_reused": True,
            "duplicate_liquidity_authority_created": False,
        },
    )

    assert metadata["liquidity_avg_volume_20d"] == source_row["liquidity_avg_volume_20d"]
    assert top1[0]["candidate_pit_surface_state"] == "STRONG_CONTINUATION_SURFACE"
    assert top1[0]["candidate_pit_surface_evidence_sufficiency"] == "SUFFICIENT"
    assert top1[0]["candidate_pit_quality_surface"]["raw_pit_evidence"]["liquidity_avg_volume_20d"] == 1_000_000
    assert evidence["liquidity_present_row_count"] == 1
    assert evidence["liquidity_missing_row_count"] == 0
    assert evidence["liquidity_evidence_lineage"]["canonical_liquidity_authority_reused"] is True
    assert evidence["liquidity_evidence_lineage"]["duplicate_liquidity_authority_created"] is False


def test_phase30_aj3b_liquidity_missing_remains_fail_safe_insufficient() -> None:
    row = _strong("4002", score=0.90, rank=1)
    row.pop("liquidity_avg_volume_20d")

    top1, evidence = _apply_candidate_pit_quality_surface([row], top_n=1)

    assert top1[0]["candidate_pit_surface_state"] == "INSUFFICIENT_SURFACE_EVIDENCE"
    assert top1[0]["candidate_pit_surface_evidence_sufficiency"] == "INSUFFICIENT"
    assert "liquidity_avg_volume_20d" in top1[0]["candidate_pit_quality_surface"]["missing_inputs"]
    assert evidence["liquidity_present_row_count"] == 0
    assert evidence["liquidity_missing_row_count"] == 1


def _strong(code: str, *, score: float, rank: int) -> dict:
    return _row(code, score=score, rank=rank, r5=0.08, r20=0.15, r60=0.22, acc=0.02, volume=1.4, vol=0.02)


def _valid(code: str, *, score: float, rank: int) -> dict:
    return _row(code, score=score, rank=rank, r5=0.03, r20=0.05, r60=-0.01, acc=-0.01, volume=1.1, vol=0.06)


def _caution(code: str, *, score: float, rank: int) -> dict:
    return _row(code, score=score, rank=rank, r5=-0.01, r20=0.28, r60=0.65, acc=-0.29, volume=0.7, vol=0.11)


def _missing(code: str, *, score: float, rank: int) -> dict:
    row = _strong(code, score=score, rank=rank)
    row["trend_close_over_ma_20d"] = None
    row["volume_momentum_ratio_5d"] = None
    return row


def _row(
    code: str,
    *,
    score: float,
    rank: int,
    r5: float | None,
    r20: float | None,
    r60: float | None,
    acc: float | None,
    volume: float | None,
    vol: float | None,
) -> dict:
    return {
        "target_date": "2026-07-07",
        "code": code,
        "candidate_score": score,
        "candidate_rank": rank,
        "score_only_candidate_rank": rank,
        "candidate_reason": "high_candidate_score" if score >= 0.5 else "fixture",
        "model_version": "candidate_model_fixture",
        "price_momentum_return_5d": r5,
        "price_momentum_return_20d": r20,
        "price_momentum_return_60d": r60,
        "trend_close_over_ma_20d": 1.03,
        "trend_ma_5_20_ratio": 1.02,
        "trend_ma_20_60_ratio": 1.01,
        "momentum_5d_vs_20d_delta": acc,
        "volume_momentum_ratio_5d": volume,
        "volatility_return_std_20d": vol,
        "liquidity_avg_volume_20d": 1_000_000,
    }
