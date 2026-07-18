from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ComponentLifecycleContract:
    component: str
    classification: str
    lifecycle_owner: str
    required_stages: tuple[str, ...]
    registry_applicable: bool
    runtime_consumer_required: bool
    rollback_required: bool
    trainable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


COMPONENT_CONTRACTS: dict[str, ComponentLifecycleContract] = {
    "candidate_ai": ComponentLifecycleContract(
        "candidate_ai",
        "TRAINABLE_AI",
        "AI Lifecycle Control Plane",
        ("dataset_rebuild", "training", "validation", "promotion_readiness", "authority_review", "registry_acceptance", "rollback"),
        True,
        True,
        True,
        True,
    ),
    "opportunity_ai": ComponentLifecycleContract(
        "opportunity_ai",
        "TRAINABLE_AI",
        "AI Lifecycle Control Plane",
        ("dataset_rebuild", "training", "validation", "promotion_readiness", "authority_review", "registry_acceptance", "rollback"),
        True,
        True,
        True,
        True,
    ),
    "position_management": ComponentLifecycleContract(
        "position_management",
        "RULE_BASED_POLICY_ADAPTER",
        "AI Lifecycle Control Plane",
        ("policy_evidence_update", "semantic_regression", "scenario_validation", "authority_review", "registry_acceptance", "rollback"),
        True,
        True,
        True,
        False,
    ),
    "safety_policy": ComponentLifecycleContract(
        "safety_policy",
        "POLICY_ENGINE",
        "AI Lifecycle Control Plane",
        ("policy_freshness", "threshold_evidence", "semantic_regression", "failure_scenario_validation", "authority_review", "rollback"),
        True,
        True,
        True,
        False,
    ),
    "future_ai": ComponentLifecycleContract(
        "future_ai",
        "ONBOARDING_REQUIRED",
        "Operator / Authority",
        ("classification", "component_contract", "required_artifacts", "runtime_consumer", "rollback", "sot_update"),
        False,
        False,
        True,
        False,
    ),
}


def lifecycle_contract_for(component: str) -> ComponentLifecycleContract:
    try:
        return COMPONENT_CONTRACTS[component]
    except KeyError as exc:
        raise ValueError(f"unknown lifecycle component: {component}") from exc


def all_lifecycle_contracts() -> list[dict[str, Any]]:
    return [contract.to_dict() for contract in COMPONENT_CONTRACTS.values()]
