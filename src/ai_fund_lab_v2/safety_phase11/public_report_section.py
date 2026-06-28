from __future__ import annotations

from typing import Any

from ai_fund_lab_v2.safety_phase11.models import SafetyState


def safety_market_review_from_result_safety_state(safety_state: dict[str, Any] | None) -> dict[str, Any]:
    state = dict(safety_state or {})
    next_state = str(state.get("next_recommended_safety_state") or state.get("state") or state.get("status") or "UNKNOWN")
    review_items = list(state.get("review_required_items") or state.get("review_items") or [])
    reason_codes = {str(item.get("reason_code") or item) for item in review_items}
    market_stress = bool(state.get("market_stress")) or next_state == SafetyState.MARKET_STRESS.value or bool(reason_codes & {"MARKET_STRESS", "MARKET_STRESS_DAILY_LOSS"})
    buy_opportunity = bool(state.get("buy_opportunity_review")) or next_state == SafetyState.BUY_OPPORTUNITY_REVIEW.value or "BUY_OPPORTUNITY_REVIEW" in reason_codes
    sell_review = bool(state.get("sell_review_required")) or "SELL_REVIEW_REQUIRED" in reason_codes
    high_risk = bool(state.get("high_risk_review")) or "HIGH_RISK_REVIEW" in reason_codes
    system_emergency = bool(state.get("system_emergency")) or next_state in {SafetyState.SYSTEM_EMERGENCY_STOP.value, SafetyState.EMERGENCY_STOP.value}
    blocked_orders = list(state.get("blocked_orders") or [])
    actions = list(state.get("recommended_human_actions") or state.get("recommended_actions") or [])
    return {
        "safety_state": next_state,
        "system_emergency": system_emergency,
        "market_stress": market_stress,
        "buy_opportunity_review": buy_opportunity,
        "position_review": sell_review or high_risk or bool(reason_codes & {"DAILY_LOSS_REVIEW_REQUIRED", "MARKET_STRESS_DAILY_LOSS"}),
        "sell_review_required": sell_review,
        "high_risk_review": high_risk,
        "blocked_orders": blocked_orders,
        "review_required_items": sorted(reason_codes),
        "recommended_human_actions": actions,
        "auto_sell_executed": False,
        "auto_recovery_executed": False,
        "live_order_executed": False,
    }


def render_safety_market_review_section(safety_review: dict[str, Any] | None) -> str:
    review = safety_market_review_from_result_safety_state(safety_review)
    lines = [
        "## Safety / Market Review",
        "",
        f"- Safety State: {review['safety_state']}",
        f"- System Emergency: {_yes_no(review['system_emergency'])}",
        f"- Market Stress: {_yes_no(review['market_stress'])}",
        f"- Buy Opportunity Review: {_yes_no(review['buy_opportunity_review'])}",
        f"- Position Review: {_yes_no(review['position_review'])}",
        f"- Sell Review Required: {_yes_no(review['sell_review_required'])}",
        f"- High Risk Review: {_yes_no(review['high_risk_review'])}",
        f"- Blocked Orders: {_list_or_none(review['blocked_orders'])}",
        f"- Review Required Items: {_list_or_none(review['review_required_items'])}",
        f"- Recommended Human Actions: {_list_or_none(review['recommended_human_actions'])}",
        "- Auto Sell Executed: false",
        "- Auto Recovery Executed: false",
        "- Live Order Executed: false",
        "",
    ]
    if review["system_emergency"]:
        lines.extend(
            [
                "System Emergency はシステム事故またはBroker不整合の可能性があるため、発注停止 / 人間確認必須として扱います。",
                "",
            ]
        )
    elif review["market_stress"] or review["buy_opportunity_review"]:
        lines.extend(
            [
                "市場下落を検知しました。自動停止ではありません。買い場候補として確認してください。",
                "自動売却はしていません。人間確認対象です。",
                "",
            ]
        )
    elif review["position_review"]:
        lines.extend(
            [
                "保有銘柄の大きな変動を検知しました。自動売却はしていません。",
                "売却 / 保有 / 買い増しを確認してください。",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _list_or_none(values: list[Any]) -> str:
    clean = [str(value) for value in values if str(value)]
    return ", ".join(clean) if clean else "none"
