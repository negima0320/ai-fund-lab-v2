#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_fund_lab_v2.paper_trading.daily_inference_runner import run_daily_inference
from ai_fund_lab_v2.paper_trading.reporting.blog_report_v2_writer import write_blog_report_v2


DOC_PATH = Path("docs/phase_reports/phase9v_score_saturation_fix.md")
JSON_PATH = Path("reports/phase_reports/phase9v_score_saturation_fix.json")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Phase9-V score saturation fix.")
    parser.add_argument("--decision-for", default=None)
    parser.add_argument("--data-until", default=None)
    parser.add_argument("--inference-root", default=".runtime/phase9/inference")
    parser.add_argument("--feature-root", default=".runtime/phase9/features")
    parser.add_argument("--canonical-quotes-path", default=".runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet")
    parser.add_argument("--ledger-path", default=".runtime/phase9/ledger/latest.json")
    parser.add_argument("--runtime-dir", default=".runtime/phase9/score_saturation_fix")
    parser.add_argument("--reports-root", default="reports/phase9v_score_saturation_fix")
    args = parser.parse_args()

    decision_for = args.decision_for or _latest_inference_date(Path(args.inference_root))
    data_until = args.data_until or decision_for
    if not decision_for:
        raise SystemExit("No inference artifact date found.")

    ledger_path = Path(args.ledger_path)
    ledger_hash_before = _sha256_file(ledger_path) if ledger_path.is_file() else None

    before_dir = Path(args.inference_root) / decision_for
    before_candidate = _artifact_rows(before_dir / "candidate_artifact.json")
    before_opportunity = _artifact_rows(before_dir / "opportunity_artifact.json")

    result = run_daily_inference(
        decision_for=decision_for,
        data_until=data_until,
        runtime_dir=Path(args.runtime_dir),
        reports_root=Path(args.reports_root),
        feature_root=Path(args.feature_root),
        canonical_quotes_path=Path(args.canonical_quotes_path),
        ledger_path=ledger_path,
    )

    after_dir = Path(result.output_dir)
    after_candidate = _artifact_rows(after_dir / "candidate_artifact.json")
    after_opportunity = _artifact_rows(after_dir / "opportunity_artifact.json")
    after_allocation = _artifact_rows(after_dir / "allocation_artifact.json")

    blog_result = None
    if result.status == "INFERENCE_READY":
        blog_result = write_blog_report_v2(
            decision_for=decision_for,
            execution_date=_next_business_day(decision_for),
            inference_root=after_dir.parent,
            ledger_path=ledger_path,
            output_root=Path(args.reports_root) / "public" / "phase9_daily",
            report_version="v4",
        )

    ledger_hash_after = _sha256_file(ledger_path) if ledger_path.is_file() else None

    candidate_before = _distribution(before_candidate, "score")
    candidate_after = _distribution(after_candidate, "rank_score")
    opportunity_before = _distribution(before_opportunity, "opportunity_score")
    opportunity_after = _distribution(after_opportunity, "rank_score")
    expected_edge_before = _distribution(before_opportunity, "expected_edge_score")
    expected_edge_after = _distribution(after_opportunity, "expected_edge_score")
    public_after = _distribution(after_opportunity, "public_confidence_score")

    checks = [
        Check("inference_ready", result.status == "INFERENCE_READY", result.status),
        Check("candidate_raw_rank_clipped_present", _has_keys(after_candidate, ("raw_score_preclip", "rank_score", "score_clipped", "score_saturation_flag", "score_source", "rank_tiebreaker"))),
        Check("opportunity_raw_rank_clipped_present", _has_keys(after_opportunity, ("raw_score_preclip", "rank_score", "score_clipped", "candidate_rank_score", "expected_edge_score", "score_saturation_flag", "score_source", "rank_tiebreaker"))),
        Check("candidate_rank_desc", _is_desc(after_candidate, "rank_score")),
        Check("opportunity_rank_desc", _is_desc(after_opportunity, "rank_score")),
        Check("expected_edge_not_all_1", not _all_equal_to(after_opportunity, "expected_edge_score", 1.0)),
        Check("public_confidence_not_all_100", not _all_equal_to(after_opportunity, "public_confidence_score", 100.0)),
        Check("candidate_rank_not_code_asc", _codes(after_candidate[:10]) != sorted(_codes(after_candidate[:10]))),
        Check("opportunity_uses_candidate_rank_score", _uses_candidate_rank_score(after_opportunity)),
        Check("ledger_not_changed", ledger_hash_before == ledger_hash_after),
        Check("broker_scheduler_prohibited_flags_false", all(value is False for value in result.prohibited_flags.values())),
    ]

    candidate_3063 = _find_code(after_candidate, "3063")
    opportunity_3063 = _find_code(after_opportunity, "3063")
    before_candidate_3063 = _find_code(before_candidate, "3063")
    before_opportunity_3063 = _find_code(before_opportunity, "3063")
    after_allocation_3063 = _find_code(after_allocation, "3063")
    decision_3063 = "ALLOCATED" if after_allocation_3063 else "NOT_ALLOCATED"
    if candidate_3063 and not opportunity_3063:
        decision_3063 = "NOT_ALLOCATED_NOT_IN_OPPORTUNITY_TOP20"

    payload = {
        "phase": "Phase9-V",
        "decision_for": decision_for,
        "data_until": data_until,
        "status": "PASS" if all(check.passed for check in checks) else "FAIL",
        "root_cause": "Candidate and Opportunity rankings used clipped 0-100 scores, so many rows tied at 100 and fell through to code ascending order.",
        "fix_summary": {
            "candidate_rank_key": "rank_score from raw_score_preclip",
            "opportunity_rank_key": "rank_score from opportunity raw_score_preclip using candidate_rank_score",
            "tie_breaker": "rank_score desc, liquidity desc, code asc",
            "public_score_policy": "public confidence is bounded 0-100 for display and is separate from rank_score",
        },
        "before": {
            "candidate": candidate_before,
            "opportunity": opportunity_before,
            "expected_edge": expected_edge_before,
            "candidate_top10": _top_rows(before_candidate, score_keys=("score", "raw_score_preclip", "rank_score", "score_clipped")),
            "opportunity_top10": _top_rows(before_opportunity, score_keys=("opportunity_score", "raw_score_preclip", "rank_score", "expected_edge_score")),
            "candidate_3063": before_candidate_3063,
            "opportunity_3063": before_opportunity_3063,
        },
        "after": {
            "candidate": candidate_after,
            "opportunity": opportunity_after,
            "expected_edge": expected_edge_after,
            "public_confidence": public_after,
            "candidate_top10": _top_rows(after_candidate, score_keys=("rank_score", "raw_score_preclip", "score_clipped", "public_confidence_score")),
            "opportunity_top10": _top_rows(after_opportunity, score_keys=("rank_score", "raw_score_preclip", "candidate_rank_score", "expected_edge_score", "public_confidence_score")),
            "candidate_3063": candidate_3063,
            "opportunity_3063": opportunity_3063,
            "allocation_3063": after_allocation_3063,
            "decision_3063": decision_3063,
            "allocation_rows": _top_rows(after_allocation, score_keys=("planned_quantity", "planned_amount", "public_confidence_score")),
        },
        "blog_report": blog_result.to_dict() if blog_result else None,
        "ledger_hash_before": ledger_hash_before,
        "ledger_hash_after": ledger_hash_after,
        "checks": [asdict(check) for check in checks],
        "prohibited_flags": result.prohibited_flags,
        "artifacts": {
            "after_inference_dir": str(after_dir),
            "markdown_report": str(DOC_PATH),
            "json_report": str(JSON_PATH),
        },
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(_markdown(payload), encoding="utf-8")

    print(json.dumps({"status": payload["status"], "decision_for": decision_for, "data_until": data_until, "markdown": str(DOC_PATH), "json": str(JSON_PATH)}, ensure_ascii=True, indent=2))
    return 0 if payload["status"] == "PASS" else 1


def _latest_inference_date(root: Path) -> str:
    dates = sorted(path.name for path in root.iterdir() if path.is_dir() and (path / "candidate_artifact.json").is_file())
    return dates[-1] if dates else ""


def _artifact_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    return rows if isinstance(rows, list) else []


def _distribution(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [_to_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    unique = sorted(set(round(value, 6) for value in values))
    return {
        "key": key,
        "count": len(values),
        "unique_count": len(unique),
        "all_same": len(unique) == 1 if values else False,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "top10_values": [round(value, 6) for value in values[:10]],
    }


def _top_rows(rows: list[dict[str, Any]], *, score_keys: tuple[str, ...]) -> list[dict[str, Any]]:
    output = []
    for row in rows[:10]:
        item = {"rank": row.get("rank"), "code": row.get("code")}
        for key in score_keys:
            if key in row:
                item[key] = row.get(key)
        item["rank_liquidity"] = row.get("rank_liquidity")
        output.append(item)
    return output


def _find_code(rows: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    targets = {str(code), f"{code}0"}
    for row in rows:
        if str(row.get("code")) in targets:
            keys = (
                "rank",
                "code",
                "score",
                "opportunity_score",
                "raw_score_preclip",
                "rank_score",
                "score_clipped",
                "candidate_rank_score",
                "expected_edge_score",
                "public_confidence_score",
                "score_saturation_flag",
            )
            return {key: row.get(key) for key in keys if key in row}
    return None


def _has_keys(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> bool:
    return bool(rows) and all(all(key in row for key in keys) for row in rows)


def _is_desc(rows: list[dict[str, Any]], key: str) -> bool:
    values = [_to_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return all(left >= right for left, right in zip(values, values[1:]))


def _all_equal_to(rows: list[dict[str, Any]], key: str, expected: float) -> bool:
    values = [_to_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return bool(values) and all(abs(value - expected) < 1e-9 for value in values)


def _uses_candidate_rank_score(rows: list[dict[str, Any]]) -> bool:
    values = [_to_float(row.get("candidate_rank_score")) for row in rows]
    return bool(values) and any(value is not None and value > 100.0 for value in values)


def _codes(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("code")) for row in rows]


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _next_business_day(value: str) -> str:
    current = date.fromisoformat(value) + timedelta(days=1)
    while current.weekday() >= 5:
        current += timedelta(days=1)
    return current.isoformat()


def _markdown(payload: dict[str, Any]) -> str:
    before_candidate = payload["before"]["candidate"]
    after_candidate = payload["after"]["candidate"]
    before_opportunity = payload["before"]["opportunity"]
    after_opportunity = payload["after"]["opportunity"]
    before_edge = payload["before"]["expected_edge"]
    after_edge = payload["after"]["expected_edge"]
    lines = [
        "# Phase9-V Score Saturation Fix",
        "",
        f"- status: {payload['status']}",
        f"- decision_for: {payload['decision_for']}",
        f"- data_until: {payload['data_until']}",
        "",
        "## Root Cause",
        "",
        payload["root_cause"],
        "",
        "## Fix",
        "",
        f"- Candidate rank: {payload['fix_summary']['candidate_rank_key']}",
        f"- Opportunity rank: {payload['fix_summary']['opportunity_rank_key']}",
        f"- Tie breaker: {payload['fix_summary']['tie_breaker']}",
        f"- Public score: {payload['fix_summary']['public_score_policy']}",
        "",
        "## Before / After Distribution",
        "",
        f"- Candidate before score unique_count: {before_candidate['unique_count']} min={before_candidate['min']} max={before_candidate['max']}",
        f"- Candidate after rank_score unique_count: {after_candidate['unique_count']} min={after_candidate['min']} max={after_candidate['max']}",
        f"- Opportunity before score unique_count: {before_opportunity['unique_count']} min={before_opportunity['min']} max={before_opportunity['max']}",
        f"- Opportunity after rank_score unique_count: {after_opportunity['unique_count']} min={after_opportunity['min']} max={after_opportunity['max']}",
        f"- expected_edge before unique_count: {before_edge['unique_count']} top10={before_edge['top10_values']}",
        f"- expected_edge after unique_count: {after_edge['unique_count']} top10={after_edge['top10_values']}",
        "",
        "## Top10 Before",
        "",
        "Candidate:",
    ]
    lines.extend(_row_lines(payload["before"]["candidate_top10"]))
    lines += ["", "Opportunity:"]
    lines.extend(_row_lines(payload["before"]["opportunity_top10"]))
    lines += ["", "## Top10 After", "", "Candidate:"]
    lines.extend(_row_lines(payload["after"]["candidate_top10"]))
    lines += ["", "Opportunity:"]
    lines.extend(_row_lines(payload["after"]["opportunity_top10"]))
    lines += [
        "",
        "## 3063 J Group Holdings",
        "",
        f"- before candidate: {payload['before']['candidate_3063']}",
        f"- after candidate: {payload['after']['candidate_3063']}",
        f"- before opportunity: {payload['before']['opportunity_3063']}",
        f"- after opportunity: {payload['after']['opportunity_3063']}",
        f"- after allocation: {payload['after']['allocation_3063']}",
        f"- new decision: {payload['after']['decision_3063']}",
        "",
        "## Allocation After Fix",
        "",
    ]
    lines.extend(_row_lines(payload["after"]["allocation_rows"]))
    lines += [
        "",
        "## Checks",
        "",
    ]
    for check in payload["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- {mark}: {check['name']} {check.get('detail') or ''}".rstrip())
    lines += [
        "",
        "## Safety",
        "",
        f"- ledger hash unchanged: {payload['ledger_hash_before'] == payload['ledger_hash_after']}",
        "- Broker order / OpenD / unlock_trade / real trade / scheduler changes were not executed.",
        "",
    ]
    return "\n".join(lines)


def _row_lines(rows: list[dict[str, Any]]) -> list[str]:
    return [f"- rank {row.get('rank')}: {row.get('code')} {row}" for row in rows]


if __name__ == "__main__":
    raise SystemExit(main())
