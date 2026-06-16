from ai_fund_lab_v2.paper_trading.reporting.public_confidence_mapper import map_candidate_public_confidence, public_confidence_label


def test_public_confidence_label_bands() -> None:
    assert public_confidence_label(95) == "非常に強い"
    assert public_confidence_label(80) == "強い"
    assert public_confidence_label(70) == "やや強い"
    assert public_confidence_label(50) == "中立"
    assert public_confidence_label(30) == "弱い"
    assert public_confidence_label(10) == "見送り"


def test_public_confidence_is_explanation_score() -> None:
    confidence = map_candidate_public_confidence({"score": 0.82, "risk_score": 0.10, "reason": "trend"}, safety_status="OK")
    assert confidence.public_confidence_score == 80
    assert confidence.public_confidence_label == "強い"
    assert "勝率" in confidence.caution_note

