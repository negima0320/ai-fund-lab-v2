from __future__ import annotations

from ai_fund_lab_v2.runtime_v2.position_management import producer


def test_phase27_d6b_profit_retention_break_is_canonical_risk_review_alias() -> None:
    assert producer._canonical_reason_code("profit_retention_break") == "peak_drawdown_profit_retention_risk"
    aliases = producer._reason_aliases(["profit_retention_break"])

    assert aliases == [
        {
            "legacy_reason_code": "profit_retention_break",
            "canonical_reason_code": "peak_drawdown_profit_retention_risk",
            "compatibility_status": "LEGACY_ALIAS",
            "semantic_change": "CLARIFIED_AS_RISK_REVIEW_NOT_PROFIT_TAKING",
            "action_effect": "NONE",
            "effective_from": producer.PM_REASON_SEMANTICS_CONTRACT_VERSION,
            "consumer_behavior": "legacy_code_readable; must not be interpreted as profit-taking action authority",
        }
    ]


def test_phase27_d6b_risk_increased_legacy_reason_resolves_without_inferred_cause() -> None:
    assert (
        producer._canonical_reason_code(
            "risk_increased_but_trend_not_broken",
            triggers={"reduce_score_threshold": True},
        )
        == "expected_edge_risk_deterioration"
    )
    assert (
        producer._canonical_reason_code(
            "risk_increased_but_trend_not_broken",
            triggers={"high_downside_risk": True},
        )
        == "downside_risk_increased"
    )


def test_phase27_d6b_positive_expected_edge_remains_legacy_readable() -> None:
    assert producer._canonical_reason_code("positive_expected_edge") == "expected_edge_adequate"
    semantics = producer._expected_edge_trace_semantics(
        decision_type="HOLD",
        triggers={"positive_expected_edge": True},
        legacy_reason_codes=["positive_expected_edge"],
        canonical_reason_codes=["expected_edge_adequate"],
    )

    assert semantics["expected_edge_status"] == "ADEQUATE"
    assert semantics["reason_codes_are_action_authority"] is False
    assert semantics["action_effect"] == "NONE"


def test_phase27_d6b_unknown_reason_is_preserved_as_unknown() -> None:
    assert producer._canonical_reason_code("mystery_reason") == "UNKNOWN:mystery_reason"
    aliases = producer._reason_aliases(["mystery_reason"])

    assert aliases[0]["compatibility_status"] == "DEPRECATED_READABLE"
    assert aliases[0]["canonical_reason_code"] == "UNKNOWN:mystery_reason"
    assert aliases[0]["action_effect"] == "NONE"


def test_phase27_d6b_decision_payload_keeps_action_score_and_quantity_unchanged() -> None:
    current = {
        "positions": [
            {"symbol": "1001", "quantity": 100},
            {"symbol": "1002", "quantity": 200},
            {"symbol": "1003", "quantity": 300},
            {"symbol": "1004", "quantity": 400},
        ]
    }
    fixtures = [
        ("1001", "ADD", "strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging", 0.81, 0.0, "NO_SELL_ORDER_ADD_OUT_OF_SELL_SCOPE"),
        ("1002", "HOLD", "positive_expected_edge|downside_risk_contained", 0.62, 0.0, "NO_SELL_ORDER"),
        ("1003", "REDUCE", "risk_increased_but_trend_not_broken", 0.55, 0.0, "SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING"),
        ("1004", "EXIT", "profit_retention_break", 0.88, 400.0, "SELL_FULL_POSITION"),
    ]

    for symbol, action, reason, score, sell_quantity, runtime_action in fixtures:
        payload = producer._decision_payload(
            {
                "target_date": "2026-07-09",
                "code": symbol,
                "action": action,
                "action_reason": reason if action != "EXIT" else "",
                "exit_reason": reason if action == "EXIT" else "",
                "hold_score": score if action == "HOLD" else 0.1,
                "add_score": score if action == "ADD" else 0.1,
                "reduce_score": score if action == "REDUCE" else 0.1,
                "exit_score": score if action == "EXIT" else 0.1,
                "continue_holding": action in {"ADD", "HOLD"},
                "exit_candidate": action == "EXIT",
                "reduce_candidate": action == "REDUCE",
                "add_candidate": action == "ADD",
            },
            current=current,
            generated_at="2026-07-09T00:00:00+00:00",
            decision_trace=None,
        )

        assert payload["decision"] == action
        assert payload["selected_action_score"] == score
        assert payload["runtime_sell_quantity"] == sell_quantity
        assert payload["runtime_action"] == runtime_action
        assert payload["reason_semantics_contract_version"] == producer.PM_REASON_SEMANTICS_CONTRACT_VERSION
        assert payload["expected_edge_semantics"]["action_effect"] == "NONE"
        assert "pending" not in payload
        assert "submit" not in payload
