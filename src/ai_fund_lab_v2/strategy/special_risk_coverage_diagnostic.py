"""Read-only special-risk coverage diagnostics for Strategy Intelligence artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


def summarize_special_risk_coverage(payload: Mapping[str, Any]) -> dict[str, Any]:
    rows = payload.get("symbol_intelligence") if isinstance(payload.get("symbol_intelligence"), Mapping) else {}
    counts = {
        "total_symbols": 0,
        "known_safe": 0,
        "known_risk": 0,
        "unknown": 0,
        "partial": 0,
        "stale": 0,
    }
    for row in rows.values():
        if not isinstance(row, Mapping):
            continue
        counts["total_symbols"] += 1
        eligibility = row.get("eligibility") if isinstance(row.get("eligibility"), Mapping) else {}
        authority = eligibility.get("special_risk_authority") if isinstance(eligibility.get("special_risk_authority"), Mapping) else {}
        coverage_state = str(authority.get("coverage_state") or "")
        universe_coverage_state = str(authority.get("universe_coverage_state") or "")
        risk_state = str(authority.get("risk_state") or "")
        implication = str(authority.get("eligibility_implication") or "")
        if coverage_state == "STALE":
            counts["stale"] += 1
        elif coverage_state == "KNOWN" and risk_state == "NORMAL" and implication == "BUY_ALLOWED":
            counts["known_safe"] += 1
        elif risk_state == "REVIEW_REQUIRED":
            counts["known_risk"] += 1
        elif universe_coverage_state == "KNOWN_PARTIAL" or coverage_state == "CONFLICT":
            counts["partial"] += 1
        else:
            counts["unknown"] += 1
    total = counts["total_symbols"]
    coverage_rate = (counts["known_safe"] + counts["known_risk"]) / total if total else 0.0
    return {
        "date": str(payload.get("business_date") or payload.get("as_of_business_date") or ""),
        **counts,
        "coverage_rate": coverage_rate,
    }


def format_special_risk_coverage_summary(summary: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            "DATE        TOTAL_SYMBOLS KNOWN_SAFE KNOWN_RISK UNKNOWN PARTIAL STALE COVERAGE_RATE",
            (
                f"{summary.get('date') or '-':<10} "
                f"{int(summary.get('total_symbols') or 0):>13} "
                f"{int(summary.get('known_safe') or 0):>10} "
                f"{int(summary.get('known_risk') or 0):>10} "
                f"{int(summary.get('unknown') or 0):>7} "
                f"{int(summary.get('partial') or 0):>7} "
                f"{int(summary.get('stale') or 0):>5} "
                f"{float(summary.get('coverage_rate') or 0.0):>13.2%}"
            ),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read Strategy Intelligence special-risk coverage summary.")
    parser.add_argument("strategy_intelligence_artifact", type=Path)
    args = parser.parse_args(argv)
    payload = json.loads(args.strategy_intelligence_artifact.read_text(encoding="utf-8"))
    print(format_special_risk_coverage_summary(summarize_special_risk_coverage(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
