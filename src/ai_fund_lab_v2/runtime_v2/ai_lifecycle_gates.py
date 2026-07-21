from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class FreshnessThresholds:
    dataset_lag_block_business_days: int = 20
    model_training_lag_review_business_days: int = 5
    model_training_lag_block_business_days: int = 20
    model_acceptance_age_review_business_days: int = 60
    model_acceptance_age_block_business_days: int = 120
    source_data_age_block_business_days: int = 3
    feature_data_age_block_business_days: int = 1


@dataclass(frozen=True)
class DriftThresholds:
    psi_review: float = 0.20
    psi_block: float = 0.30
    positive_rate_review_ratio: float = 0.25
    positive_rate_block_ratio: float = 0.10
    all_negative_review_days: int = 3
    all_negative_block_days: int = 5
    min_population: int = 20


@dataclass(frozen=True)
class GateEvidence:
    name: str
    metric: str
    value: float | int | str | None
    threshold: float | int | str | None
    status: str
    severity: str
    reason: str
    baseline_identity: str = ""
    current_window_identity: str = ""
    evidence_ref: str = ""


@dataclass(frozen=True)
class RuntimeAIGateResult:
    decision: str
    classification: str
    buy_gate: str
    monitoring_action: str
    trading_permission_effect: str
    runtime_integrity_status: str
    runtime_integrity_reason_codes: tuple[str, ...]
    block_buy: bool
    block_sell: bool
    block_submit: bool
    block_buy_planning: bool
    block_buy_submit: bool
    block_sell_planning: bool
    block_sell_submit: bool
    evidence: list[GateEvidence]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "classification": self.classification,
            "model_health_state": self.classification,
            "buy_gate": self.buy_gate,
            "monitoring_action": self.monitoring_action,
            "trading_permission_effect": self.trading_permission_effect,
            "runtime_integrity_status": self.runtime_integrity_status,
            "runtime_integrity_reason_codes": list(self.runtime_integrity_reason_codes),
            "block_buy": self.block_buy,
            "block_sell": self.block_sell,
            "block_submit": self.block_submit,
            "block_buy_planning": self.block_buy_planning,
            "block_buy_submit": self.block_buy_submit,
            "block_sell_planning": self.block_sell_planning,
            "block_sell_submit": self.block_sell_submit,
            "allow_current_refresh": True,
            "allow_valuation_refresh": True,
            "allow_position_management": True,
            "allow_safety_evaluation": True,
            "allow_sell_planning": not self.block_sell_planning,
            "allow_sell_submit_authorization": not self.block_sell_submit,
            "evidence": [asdict(item) for item in self.evidence],
        }


def business_days_between(start: date, end: date) -> int:
    if end < start:
        return -business_days_between(end, start)
    days = 0
    cur_ord = start.toordinal()
    while cur_ord < end.toordinal():
        cur_ord += 1
        if date.fromordinal(cur_ord).weekday() < 5:
            days += 1
    return days


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def evaluate_freshness_gate(evidence: dict[str, Any], thresholds: FreshnessThresholds | None = None) -> RuntimeAIGateResult:
    thresholds = thresholds or FreshnessThresholds()
    checks: list[GateEvidence] = []
    missing: list[str] = []

    def require_int(name: str) -> int | None:
        value = evidence.get(name)
        if value is None:
            missing.append(name)
            return None
        return int(value)

    dataset_lag = require_int("dataset_lag_business_days")
    model_training_lag = require_int("model_training_lag_business_days")
    model_acceptance_age = require_int("model_acceptance_age_business_days")
    source_age = evidence.get("source_data_age_business_days")
    feature_age = evidence.get("feature_data_age_business_days")

    if dataset_lag is not None:
        status = "BLOCK" if dataset_lag < 0 or dataset_lag > thresholds.dataset_lag_block_business_days else "PASS"
        checks.append(_status_check("dataset_freshness", "dataset_lag_business_days", dataset_lag, thresholds.dataset_lag_block_business_days, status, "dataset lag is negative/future" if dataset_lag < 0 else "dataset lag exceeds label-safe threshold" if dataset_lag > thresholds.dataset_lag_block_business_days else "dataset lag is within label-safe threshold"))
    if model_training_lag is not None:
        status = "BLOCK" if model_training_lag < 0 or model_training_lag > thresholds.model_training_lag_block_business_days else "REVIEW_REQUIRED" if model_training_lag > thresholds.model_training_lag_review_business_days else "PASS"
        checks.append(_status_check("model_training_freshness", "model_training_lag_business_days", model_training_lag, f"review>{thresholds.model_training_lag_review_business_days};block>{thresholds.model_training_lag_block_business_days}", status, "model training cutoff lag evaluated against label-safe cutoff"))
    if model_acceptance_age is not None:
        status = "BLOCK" if model_acceptance_age < 0 or model_acceptance_age > thresholds.model_acceptance_age_block_business_days else "REVIEW_REQUIRED" if model_acceptance_age > thresholds.model_acceptance_age_review_business_days else "PASS"
        checks.append(_status_check("model_acceptance_age", "model_acceptance_age_business_days", model_acceptance_age, f"review>{thresholds.model_acceptance_age_review_business_days};block>{thresholds.model_acceptance_age_block_business_days}", status, "accepted artifact lifecycle age evaluated"))
    if source_age is not None:
        source_age_int = int(source_age)
        checks.append(_status_check("source_data_freshness", "source_data_age_business_days", source_age_int, thresholds.source_data_age_block_business_days, "BLOCK" if source_age_int > thresholds.source_data_age_block_business_days else "PASS", "market source freshness evaluated"))
    if feature_age is not None:
        feature_age_int = int(feature_age)
        checks.append(_status_check("feature_data_freshness", "feature_data_age_business_days", feature_age_int, thresholds.feature_data_age_block_business_days, "BLOCK" if feature_age_int > thresholds.feature_data_age_block_business_days else "PASS", "runtime feature freshness evaluated"))
    for name in missing:
        checks.append(GateEvidence("freshness_input", name, None, "required", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "missing freshness evidence"))
    for code in evidence.get("reason_codes") or []:
        status = "BLOCK" if any(token in str(code) for token in ("negative_", "future", "calendar_", "weekday_fallback", "after_business_date")) else "REVIEW_REQUIRED"
        checks.append(GateEvidence("freshness_authority", str(code), None, "valid freshness authority", status, "HALT" if status == "BLOCK" else "REVIEW_REQUIRED", f"freshness authority violation: {code}"))
    return _compose_result(checks)


def evaluate_integrity_gate(evidence: dict[str, Any]) -> RuntimeAIGateResult:
    status = str(evidence.get("status") or "")
    reason_codes = list(evidence.get("reason_codes") or [])
    if status == "PASS":
        checks = [GateEvidence("accepted_artifact_integrity", "status", "PASS", "PASS", "PASS", "NONE", "accepted artifact authority verified")]
    elif status == "CRITICAL_AUTHORITY_VIOLATION":
        checks = [
            GateEvidence(
                "accepted_artifact_integrity",
                ",".join(str(code) for code in reason_codes) or "critical_authority_violation",
                status,
                "PASS",
                "BLOCK",
                "HALT",
                "critical authority violation",
            )
        ]
    else:
        checks = [
            GateEvidence(
                "accepted_artifact_integrity",
                ",".join(str(code) for code in reason_codes) or "insufficient_evidence",
                status or None,
                "PASS",
                "REVIEW_REQUIRED",
                "REVIEW_REQUIRED",
                "insufficient accepted artifact evidence",
            )
        ]
    return _compose_result(checks)


def evaluate_drift_gate(evidence: dict[str, Any], thresholds: DriftThresholds | None = None) -> RuntimeAIGateResult:
    thresholds = thresholds or DriftThresholds()
    checks: list[GateEvidence] = []
    baseline_identity = str(evidence.get("baseline_identity") or "")
    current_identity = str(evidence.get("current_window_identity") or "")
    evidence_ref = str(evidence.get("evidence_ref") or "")
    prediction_contract = _contract_compatibility(
        evidence.get("baseline_prediction_contract"),
        evidence.get("current_prediction_contract"),
        keys=("prediction_metric_name", "prediction_semantics", "transformation_stage", "calibration_applied", "population_scope"),
    )
    feature_contract = _contract_compatibility(
        evidence.get("baseline_feature_contract"),
        evidence.get("current_feature_contract"),
        keys=("feature_order_hash", "feature_count", "population_scope", "aggregation_method"),
    )
    population_contract = _contract_compatibility(
        evidence.get("baseline_population_contract"),
        evidence.get("current_population_contract"),
        keys=("population_scope",),
    )
    baseline_scores = _numbers(evidence.get("baseline_prediction_scores"))
    current_scores = _numbers(evidence.get("current_prediction_scores"))
    if prediction_contract["status"] != "PASS":
        checks.append(GateEvidence("prediction_distribution_drift", "BASELINE_CURRENT_SEMANTICS_MISMATCH", None, "compatible prediction semantics", "REVIEW_REQUIRED", "REVIEW_REQUIRED", prediction_contract["reason"], baseline_identity, current_identity, evidence_ref))
    elif baseline_scores and current_scores:
        psi = population_stability_index(baseline_scores, current_scores)
        status = "REVIEW_REQUIRED" if psi > thresholds.psi_review else "PASS"
        checks.append(_status_check("prediction_distribution_drift", "psi", round(psi, 6), f"review>{thresholds.psi_review};block>{thresholds.psi_block}", status, "prediction distribution PSI evaluated", baseline_identity, current_identity, evidence_ref))
    else:
        checks.append(GateEvidence("prediction_distribution_drift", "psi", None, "baseline/current required", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "insufficient prediction distribution evidence", baseline_identity, current_identity, evidence_ref))

    baseline_feature = _numbers(evidence.get("baseline_feature_values"))
    current_feature = _numbers(evidence.get("current_feature_values"))
    if feature_contract["status"] != "PASS":
        checks.append(GateEvidence("feature_drift", "BASELINE_CURRENT_FEATURE_SEMANTICS_MISMATCH", None, "compatible feature semantics", "REVIEW_REQUIRED", "REVIEW_REQUIRED", feature_contract["reason"], baseline_identity, current_identity, evidence_ref))
    elif baseline_feature and current_feature:
        feature_psi = population_stability_index(baseline_feature, current_feature)
        status = "REVIEW_REQUIRED" if feature_psi > thresholds.psi_review else "PASS"
        checks.append(_status_check("feature_drift", "feature_psi", round(feature_psi, 6), f"review>{thresholds.psi_review};block>{thresholds.psi_block}", status, "feature drift PSI evaluated", baseline_identity, current_identity, evidence_ref))
    else:
        checks.append(GateEvidence("feature_drift", "feature_psi", None, "baseline/current required", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "insufficient feature drift evidence", baseline_identity, current_identity, evidence_ref))

    baseline_positive = evidence.get("baseline_positive_coverage")
    current_positive = evidence.get("current_positive_coverage")
    if baseline_positive is not None and current_positive is not None:
        base = float(baseline_positive)
        cur = float(current_positive)
        ratio = cur / base if base > 0 else math.inf if cur > 0 else 1.0
        status = "REVIEW_REQUIRED" if ratio < thresholds.positive_rate_review_ratio else "PASS"
        checks.append(_status_check("positive_coverage_drift", "current_to_baseline_ratio", round(ratio, 6), f"review<{thresholds.positive_rate_review_ratio};block<{thresholds.positive_rate_block_ratio}", status, "positive coverage compared with accepted baseline", baseline_identity, current_identity, evidence_ref))
    else:
        checks.append(GateEvidence("positive_coverage_drift", "current_to_baseline_ratio", None, "baseline/current required", "REVIEW_REQUIRED", "REVIEW_REQUIRED", "insufficient positive coverage evidence", baseline_identity, current_identity, evidence_ref))

    current_population = int(evidence.get("current_candidate_population") or 0)
    baseline_population = evidence.get("baseline_candidate_population")
    status = "REVIEW_REQUIRED" if current_population < thresholds.min_population else "PASS"
    checks.append(_status_check("candidate_population", "current_candidate_population", current_population, thresholds.min_population, status, "candidate population must support drift interpretation", baseline_identity, current_identity, evidence_ref))
    if baseline_population is not None:
        if population_contract["status"] != "PASS":
            checks.append(GateEvidence("candidate_population_drift", "BASELINE_CURRENT_POPULATION_SCOPE_MISMATCH", None, "compatible population scope", "REVIEW_REQUIRED", "REVIEW_REQUIRED", population_contract["reason"], baseline_identity, current_identity, evidence_ref))
        else:
            base_pop = max(int(baseline_population), 1)
            pop_ratio = current_population / base_pop
            pop_status = "REVIEW_REQUIRED" if pop_ratio < 0.25 else "PASS"
            checks.append(_status_check("candidate_population_drift", "current_to_baseline_population_ratio", round(pop_ratio, 6), "review<0.25;block<0.10", pop_status, "candidate population compared with accepted baseline", baseline_identity, current_identity, evidence_ref))

    all_negative_days = int(evidence.get("all_negative_consecutive_business_days") or 0)
    status = "REVIEW_REQUIRED" if all_negative_days >= thresholds.all_negative_review_days else "PASS"
    checks.append(_status_check("all_negative_sequence", "consecutive_business_days", all_negative_days, f"review>={thresholds.all_negative_review_days};block>={thresholds.all_negative_block_days}", status, "all-negative sequence is an alarm, not forced BUY", baseline_identity, current_identity, evidence_ref))

    return _compose_result(checks, market_no_opportunity=_market_no_opportunity(evidence, checks))


def evaluate_runtime_ai_gate(evidence: dict[str, Any]) -> RuntimeAIGateResult:
    integrity = evaluate_integrity_gate(evidence.get("integrity", {}))
    freshness = evaluate_freshness_gate(evidence.get("freshness", {}))
    drift = evaluate_drift_gate(evidence.get("drift", {}))
    return _compose_result(integrity.evidence + freshness.evidence + drift.evidence, market_no_opportunity=drift.classification == "MARKET_NO_OPPORTUNITY")


def population_stability_index(expected: Sequence[float], actual: Sequence[float], buckets: int = 10) -> float:
    if not expected or not actual:
        raise ValueError("expected and actual distributions are required")
    lo = min(min(expected), min(actual))
    hi = max(max(expected), max(actual))
    if lo == hi:
        return 0.0
    step = (hi - lo) / buckets
    eps = 1e-6
    total = 0.0
    for idx in range(buckets):
        left = lo + idx * step
        right = hi if idx == buckets - 1 else left + step
        exp_count = _bucket_count(expected, left, right, include_right=idx == buckets - 1)
        act_count = _bucket_count(actual, left, right, include_right=idx == buckets - 1)
        exp_pct = max(exp_count / len(expected), eps)
        act_pct = max(act_count / len(actual), eps)
        total += (act_pct - exp_pct) * math.log(act_pct / exp_pct)
    return total


def _bucket_count(values: Sequence[float], left: float, right: float, *, include_right: bool) -> int:
    if include_right:
        return sum(1 for value in values if left <= value <= right)
    return sum(1 for value in values if left <= value < right)


def _numbers(values: Any) -> list[float]:
    if values is None:
        return []
    if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
        return []
    out: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            out.append(number)
    return out


def _status_check(name: str, metric: str, value: float | int | str, threshold: float | int | str, status: str, reason: str, baseline_identity: str = "", current_window_identity: str = "", evidence_ref: str = "") -> GateEvidence:
    severity = "HALT" if status == "BLOCK" else "REVIEW_REQUIRED" if status == "REVIEW_REQUIRED" else "NONE"
    return GateEvidence(name, metric, value, threshold, status, severity, reason, baseline_identity, current_window_identity, evidence_ref)


def _contract_compatibility(baseline: Any, current: Any, *, keys: Sequence[str]) -> dict[str, str]:
    if not isinstance(baseline, dict) or not isinstance(current, dict):
        return {"status": "PASS", "reason": "legacy evidence without explicit semantics"}
    mismatches: list[str] = []
    for key in keys:
        left = baseline.get(key)
        right = current.get(key)
        if left in (None, "", []) and right in (None, "", []):
            continue
        if left != right:
            mismatches.append(f"{key}:{left}!={right}")
    return {
        "status": "PASS" if not mismatches else "REVIEW_REQUIRED",
        "reason": "compatible semantics" if not mismatches else "BASELINE_CURRENT_SEMANTICS_MISMATCH " + ";".join(mismatches),
    }


def _compose_result(checks: list[GateEvidence], *, market_no_opportunity: bool = False) -> RuntimeAIGateResult:
    statuses = {item.status for item in checks}
    runtime_integrity_reason_codes = tuple(_runtime_integrity_reason_codes(checks))
    runtime_integrity_block = bool(runtime_integrity_reason_codes)
    if runtime_integrity_block:
        decision = "BLOCK"
        state = "CRITICAL_AUTHORITY_VIOLATION" if any("critical authority" in item.reason for item in checks if item.status == "BLOCK") else "RUNTIME_INTEGRITY_BLOCK"
        buy_gate = "BUY_BLOCK"
        monitoring_action = "HUMAN_REVIEW"
        trading_permission_effect = "BUY_BLOCK"
        runtime_integrity_status = "BLOCK"
        block_buy = True
        block_submit = True
    elif "BLOCK" in statuses:
        decision = "REVIEW_REQUIRED"
        state = "MODEL_HEALTH_REVIEW_REQUIRED"
        buy_gate = "BUY_LIFECYCLE_REVIEW_ONLY"
        monitoring_action = "HUMAN_REVIEW"
        trading_permission_effect = "NONE"
        runtime_integrity_status = "PASS"
        block_buy = False
        block_submit = False
    elif "REVIEW_REQUIRED" in statuses:
        if market_no_opportunity and _only_market_opportunity_review(checks):
            decision = "PASS"
            state = "MARKET_NO_OPPORTUNITY"
            buy_gate = "BUY_PASS_NO_OPPORTUNITY"
            monitoring_action = "NONE"
            trading_permission_effect = "NONE"
            runtime_integrity_status = "PASS"
            block_buy = False
            block_submit = False
        elif _only_statistical_drift_review(checks):
            decision = "REVIEW_REQUIRED"
            state = "STATISTICAL_DRIFT_REVIEW_REQUIRED"
            buy_gate = "BUY_REVIEW_REQUIRED_NO_AUTO_STOP"
            monitoring_action = "HUMAN_REVIEW"
            trading_permission_effect = "NONE"
            runtime_integrity_status = "PASS"
            block_buy = False
            block_submit = False
        else:
            decision = "REVIEW_REQUIRED"
            state = "INSUFFICIENT_EVIDENCE" if any("insufficient" in item.reason for item in checks if item.status == "REVIEW_REQUIRED") else "MODEL_HEALTH_REVIEW_REQUIRED"
            buy_gate = "BUY_LIFECYCLE_REVIEW_ONLY"
            monitoring_action = "HUMAN_REVIEW"
            trading_permission_effect = "NONE"
            runtime_integrity_status = "PASS"
            block_buy = False
            block_submit = False
    else:
        decision = "PASS"
        state = "MARKET_NO_OPPORTUNITY" if market_no_opportunity else "HEALTHY"
        buy_gate = "BUY_PASS_NO_OPPORTUNITY" if market_no_opportunity else "BUY_PASS"
        monitoring_action = "NONE"
        trading_permission_effect = "NONE"
        runtime_integrity_status = "PASS"
        block_buy = False
        block_submit = False
    return RuntimeAIGateResult(
        decision=decision,
        classification=state,
        buy_gate=buy_gate,
        monitoring_action=monitoring_action,
        trading_permission_effect=trading_permission_effect,
        runtime_integrity_status=runtime_integrity_status,
        runtime_integrity_reason_codes=runtime_integrity_reason_codes,
        block_buy=block_buy,
        block_sell=False,
        block_submit=block_submit,
        block_buy_planning=block_buy,
        block_buy_submit=block_submit,
        block_sell_planning=False,
        block_sell_submit=False,
        evidence=checks,
    )


def _runtime_integrity_reason_codes(checks: list[GateEvidence]) -> list[str]:
    reason_codes: list[str] = []
    for item in checks:
        if _is_runtime_integrity_failure(item):
            reason_codes.append(str(item.metric or item.name))
    return reason_codes


def _is_runtime_integrity_failure(item: GateEvidence) -> bool:
    if item.name == "accepted_artifact_integrity" and item.status != "PASS":
        return True
    if item.name == "freshness_authority" and item.status == "BLOCK":
        return True
    return False


def _market_no_opportunity(evidence: dict[str, Any], checks: list[GateEvidence]) -> bool:
    if evidence.get("current_positive_coverage") is not None and float(evidence.get("current_positive_coverage") or 0.0) == 0.0:
        return not any(item.status == "BLOCK" for item in checks)
    if int(evidence.get("all_negative_consecutive_business_days") or 0) > 0:
        return not any(item.status == "BLOCK" for item in checks)
    return False


def _only_market_opportunity_review(checks: list[GateEvidence]) -> bool:
    allowed = {"positive_coverage_drift", "all_negative_sequence"}
    return all(item.status == "PASS" or item.name in allowed for item in checks)


def _only_statistical_drift_review(checks: list[GateEvidence]) -> bool:
    allowed = {
        "prediction_distribution_drift",
        "feature_drift",
        "positive_coverage_drift",
        "candidate_population_drift",
        "all_negative_sequence",
    }
    return all(
        item.status == "PASS"
        or (item.name in allowed and "MISMATCH" not in str(item.metric))
        for item in checks
    )
