from __future__ import annotations

from typing import Any


def review_recent_holdout(
    *,
    candidate_metrics: dict[str, Any] | None,
    opportunity_metrics: dict[str, Any] | None,
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "REVIEW_REQUIRED",
        "reason_codes": ["recent_holdout_relative_degradation_threshold_not_defined_in_approved_policy"],
        "candidate_metrics": candidate_metrics,
        "opportunity_metrics": opportunity_metrics,
        "policy_thresholds_available": {
            "candidate_minimum_recent_holdout_rows": policy["candidate_requirements"].get("minimum_recent_holdout_rows"),
            "candidate_minimum_recent_holdout_business_days": policy["candidate_requirements"].get("minimum_recent_holdout_business_days"),
            "opportunity_minimum_recent_holdout_rows": policy["opportunity_requirements"].get("minimum_recent_holdout_rows"),
            "opportunity_minimum_recent_holdout_business_days": policy["opportunity_requirements"].get("minimum_recent_holdout_business_days"),
            "relative_degradation_threshold": None,
        },
        "generation_eligibility": False,
    }

