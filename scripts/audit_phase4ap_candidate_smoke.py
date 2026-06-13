#!/usr/bin/env python3
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.train_phase4ap_candidate_smoke import (  # noqa: E402
    READY,
    SUMMARY_PATH,
    train_phase4ap_candidate_smoke,
)

JSON_REPORT_PATH = Path("reports/phase_reports/phase4ap_candidate_training_smoke_audit.json")
MARKDOWN_REPORT_PATH = Path("docs/phase_reports/phase4ap_candidate_training_smoke_audit.md")


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if result.get("status") == "complete" else 1


def run_audit(
    *,
    runtime_dir: Path | str = ".runtime",
    report_dir: Path | str = "reports/candidate_ai/full_range",
    summary_path: Path = SUMMARY_PATH,
    json_report_path: Path = JSON_REPORT_PATH,
    markdown_report_path: Path = MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    summary = _read_json_optional(summary_path)
    model_path = Path(str(summary.get("model_artifact_path") or ""))
    if not summary or not model_path.is_file():
        summary = train_phase4ap_candidate_smoke(runtime_dir=runtime_dir, report_dir=report_dir)
        model_path = Path(str(summary.get("model_artifact_path") or ""))
    manifest_path = Path(str(summary.get("model_manifest_path") or ""))
    manifest = _read_json_optional(manifest_path)
    model_payload = _read_pickle_optional(model_path)

    checks = {
        "summary_exists": summary_path.is_file(),
        "training_executed": summary.get("training_executed") is True,
        "smoke_test": summary.get("smoke_test") is True,
        "readiness_ready_for_candidate_inference_smoke": summary.get("readiness_status") == READY,
        "model_artifact_exists": model_path.is_file(),
        "model_manifest_exists": manifest_path.is_file(),
        "model_payload_has_feature_columns": isinstance(model_payload.get("feature_columns"), list)
        and bool(model_payload.get("feature_columns")),
        "dataset_rows_positive": int(summary.get("dataset_row_count") or 0) > 0,
        "smoke_train_rows_positive": int(summary.get("smoke_train_row_count") or 0) > 0,
        "smoke_validation_rows_positive": int(summary.get("smoke_validation_row_count") or 0) > 0,
        "positive_labels_positive": int(summary.get("positive_label_count") or 0) > 0,
        "random_split_not_used": summary.get("random_split_used") is False,
        "no_future_column_used_as_feature": summary.get("future_column_used_as_feature") is False,
        "no_label_column_used_as_feature": summary.get("label_column_used_as_feature") is False,
        "leakage_audit_ok": summary.get("leakage_audit_status") == "OK",
        "metrics_recorded": all(key in summary for key in ("auc", "average_precision", "accuracy", "precision_at_top_50")),
        "no_production_promotion": summary.get("production_model_promoted") is False
        and manifest.get("production_model_promoted") is False,
        "inference_backtest_trading_not_executed": all(
            summary.get(key) is False for key in ("inference_executed", "backtest_executed", "trading_executed")
        ),
        "secret_terms_not_emitted": _no_secret_terms(summary)
        and _no_secret_terms(manifest)
        and _no_secret_terms({"model_payload": {k: v for k, v in model_payload.items() if k != "model"}}),
    }
    result = {
        "phase": "Phase4-AP",
        "status": "complete" if all(checks.values()) else "incomplete",
        "checks": checks,
        "readiness_status": summary.get("readiness_status"),
        "summary": _compact_summary(summary),
        "summary_path": str(summary_path),
        "pytest_hint": "python3 -m pytest tests/test_phase4ap_candidate_training_smoke.py && python3 -m pytest -q",
    }
    _write_json(json_report_path, result)
    _write_markdown(markdown_report_path, result)
    return result


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "status",
        "readiness_status",
        "model_type",
        "dataset_row_count",
        "smoke_train_row_count",
        "smoke_validation_row_count",
        "feature_column_count",
        "label_column_count",
        "positive_label_rate",
        "auc",
        "average_precision",
        "accuracy",
        "precision_at_top_50",
        "leakage_audit_status",
        "recommended_next_action",
    )
    return {key: summary.get(key) for key in keys}


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_pickle_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Phase4-AP Candidate Training Smoke Audit",
        "",
        "## Audit Result",
        "",
        f"- status: {result['status']}",
        f"- readiness_status: `{result.get('readiness_status')}`",
        f"- summary: `{result['summary_path']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Checks", ""])
    for name, value in result["checks"].items():
        mark = "OK" if value else "NG"
        lines.append(f"- {mark}: `{name}`")
    lines.extend(
        [
            "",
            "## Scope Guard",
            "",
            "- This audit checks Candidate AI training smoke only.",
            "- It confirms no random split is used.",
            "- It confirms future and label columns are not used as features.",
            "- It confirms no production promotion, backtest, or trading is executed.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _no_secret_terms(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=True, default=str)
    terms = ("sAuthId", "Authorization", "x-api-key", "JQUANTS_API_KEY", "TACHIBANA", "password", "cookie", "token")
    return not any(term in text for term in terms)


if __name__ == "__main__":
    raise SystemExit(main())
