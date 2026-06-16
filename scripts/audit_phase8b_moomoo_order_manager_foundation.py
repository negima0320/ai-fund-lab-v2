from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ai_fund_lab_v2.broker.moomoo.readonly_methods import MOOMOO_READ_ONLY_METHODS
from ai_fund_lab_v2.order_manager import OrderPlan, OrderPlanItem, OrderPlanItemSide

PHASE8_SOURCE_PATHS = (
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "broker" / "moomoo",
    REPO_ROOT / "src" / "ai_fund_lab_v2" / "order_manager",
)

EXPECTED_READ_ONLY_METHODS = frozenset(
    {
        "get_acc_list",
        "accinfo_query",
        "position_list_query",
        "order_list_query",
        "history_order_list_query",
    }
)

FORBIDDEN_METHOD_TOKENS = (
    "place_order",
    "place_combo_order",
    "modify_order",
    "cancel_order",
    "unlock_trade",
    "OpenSecTradeContext",
    "OpenFutureTradeContext",
    "futu",
    "OpenD",
    "login",
    "logout",
)

FORBIDDEN_TACHIBANA_TOKENS = (
    "CLMID",
    "CLMAuth",
    "CLMZanKai",
    "CLMGenbutu",
    "CLMShinyou",
    "CLMOrder",
    "Tachibana",
)


def run_audit() -> dict[str, object]:
    source_files = list(_iter_source_files(PHASE8_SOURCE_PATHS))
    forbidden_hits = _find_tokens(source_files, FORBIDDEN_METHOD_TOKENS)
    tachibana_hits = _find_tokens(source_files, FORBIDDEN_TACHIBANA_TOKENS)
    order_plan = OrderPlan(
        broker_snapshot_id="broker_snapshot_mock",
        policy_id="CAP5",
        items=(OrderPlanItem(issue_code="7203", side=OrderPlanItemSide.HOLD, action="HOLD_PLAN"),),
    )
    checks = {
        "phase8_source_files_present": bool(source_files),
        "read_only_methods_exact": MOOMOO_READ_ONLY_METHODS == EXPECTED_READ_ONLY_METHODS,
        "forbidden_method_tokens_absent": not forbidden_hits,
        "tachibana_tokens_absent_from_phase8_source": not tachibana_hits,
        "order_plan_executable_false": order_plan.executable is False,
        "order_plan_live_order_allowed_false": order_plan.live_order_allowed is False,
        "order_plan_requires_human_review_true": order_plan.requires_human_review is True,
        "order_plan_items_executable_false": all(item.executable is False for item in order_plan.items),
    }
    passed = all(checks.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "forbidden_method_hits": forbidden_hits,
        "tachibana_hits": tachibana_hits,
        "source_files": [str(path.relative_to(REPO_ROOT)) for path in source_files],
    }


def _iter_source_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(child for child in path.rglob("*.py") if child.is_file())


def _find_tokens(files: list[Path], tokens: tuple[str, ...]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        found = [token for token in tokens if _contains_token(text, token)]
        if found:
            hits[str(path.relative_to(REPO_ROOT))] = found
    return hits


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])", text) is not None


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
