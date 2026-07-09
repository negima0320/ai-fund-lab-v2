from decimal import Decimal

from ai_fund_lab_v2.broker.normalizer import normalize_cash_positions, normalize_margin_positions
from ai_fund_lab_v2.broker.response import BrokerResponseEnvelope
from ai_fund_lab_v2.broker.tachibana_broker_snapshot import build_positions_api_safe_diagnosis


def test_phase14d13_position_normalizer_accepts_order_style_position_keys():
    positions = normalize_margin_positions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMShinyouTategyokuList",
                "sResultCode": "0",
                "aShinyouTategyokuList": [
                    {
                        "sOrderIssueCode": "7203",
                        "sOrderOrderSuryou": "100",
                        "sOrderCurrentSuryou": "100",
                        "sOrderBaibaiKubun": "3",
                    }
                ],
            }
        )
    )

    assert len(positions) == 1
    assert positions[0].issue_code == "7203"
    assert positions[0].quantity == Decimal("100")
    assert positions[0].available_quantity == Decimal("100")


def test_phase14d13_position_normalizer_accepts_numeric_cash_position_keys():
    positions = normalize_cash_positions(
        BrokerResponseEnvelope(
            {
                "sCLMID": "CLMGenbutuKabuList",
                "sResultCode": "0",
                "aGenbutuKabuList": [
                    {
                        "860": "7203",
                        "864": "100",
                        "861": "100",
                        "855": "102.0000",
                        "859": "2940.0000",
                        "858": "294000",
                        "856": "283800",
                    }
                ],
            }
        )
    )

    assert len(positions) == 1
    assert positions[0].account_type == "cash"
    assert positions[0].issue_code == "7203"
    assert positions[0].quantity == Decimal("100")
    assert positions[0].available_quantity == Decimal("100")
    assert positions[0].average_price == Decimal("102.0000")
    assert positions[0].market_price == Decimal("2940.0000")
    assert positions[0].market_value == Decimal("294000")
    assert positions[0].unrealized_pnl == Decimal("283800")


def test_phase14d13_safe_diagnosis_counts_order_style_position_keys():
    diagnosis = build_positions_api_safe_diagnosis(
        cash_raw={"sCLMID": "CLMGenbutuKabuList", "aGenbutuKabuList": []},
        margin_raw={
            "sCLMID": "CLMShinyouTategyokuList",
            "aShinyouTategyokuList": [
                {"sOrderIssueCode": "7203", "sOrderOrderSuryou": "100"},
            ],
        },
    )

    assert diagnosis["combined"]["candidate_key_match_rate"]["issue_code"] == "1/1"
    assert diagnosis["combined"]["candidate_key_match_rate"]["quantity"] == "1/1"
    assert diagnosis["margin"]["candidate_key_presence"]["issue_code"] == ["sOrderIssueCode"]
    assert diagnosis["margin"]["candidate_key_presence"]["quantity"] == ["sOrderOrderSuryou"]


def test_phase14d13_safe_diagnosis_counts_numeric_cash_position_keys():
    diagnosis = build_positions_api_safe_diagnosis(
        cash_raw={
            "sCLMID": "CLMGenbutuKabuList",
            "aGenbutuKabuList": [
                {"860": "7203", "864": "100", "858": "294000", "855": "102.0000"},
            ],
        },
        margin_raw={"sCLMID": "CLMShinyouTategyokuList", "aShinyouTategyokuList": []},
    )

    assert diagnosis["combined"]["candidate_key_match_rate"]["issue_code"] == "1/1"
    assert diagnosis["combined"]["candidate_key_match_rate"]["quantity"] == "1/1"
    assert diagnosis["combined"]["candidate_key_match_rate"]["market_value"] == "1/1"
    assert diagnosis["combined"]["candidate_key_match_rate"]["price"] == "1/1"
    assert diagnosis["cash"]["candidate_key_presence"]["issue_code"] == ["860"]
    assert diagnosis["cash"]["candidate_key_presence"]["quantity"] == ["864"]
