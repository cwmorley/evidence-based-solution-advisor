"""Orchestrate intake, constraints, scoring, services, and explanations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .conversation import build_conversation_guide
from .constraints import evaluate_constraints
from .io import load_knowledge_store, validate_intake
from .questions import next_questions
from .scoring import score_product
from .services import recommend_services


def recommend(intake: dict[str, Any], knowledge_root: str | Path) -> dict[str, Any]:
    validate_intake(intake)
    knowledge = load_knowledge_store(knowledge_root)
    vertical = intake["vertical"]
    candidates = []

    for product in knowledge["products"]:
        if product["vertical"] != vertical or product.get("status") != "active":
            continue
        results = evaluate_constraints(intake, product, knowledge["constraints"])
        failures = [result for result in results if result.status == "failed"]
        unknowns = [result for result in results if result.status == "unknown"]
        candidate: dict[str, Any] = {
            "product_id": product["product_id"],
            "identity": product["identity"],
            "description": product["description"],
            "synthetic": product["synthetic"],
            "viable": not failures,
            "constraint_results": [result.as_dict() for result in results],
            "failure_reasons": [result.message for result in failures],
            "unknowns": [result.message for result in unknowns],
        }
        if not failures:
            score, dimensions = score_product(intake, product, knowledge["scoring"])
            candidate["score"] = score
            candidate["score_dimensions"] = dimensions
            candidate["configuration"] = product["specifications"]
            candidate["commercial"] = product["commercial"]
            candidate["evidence"] = product["evidence"]
        candidates.append(candidate)

    viable = sorted(
        (item for item in candidates if item["viable"]),
        key=lambda item: (-item["score"], item["product_id"]),
    )
    rejected = sorted(
        (item for item in candidates if not item["viable"]),
        key=lambda item: (len(item["failure_reasons"]), item["product_id"]),
    )
    products_by_id = {product["product_id"]: product for product in knowledge["products"]}
    selected = viable[0] if viable else None
    services = []
    if selected:
        services = recommend_services(
            intake, products_by_id[selected["product_id"]], knowledge["services"]
        )

    all_unknowns = sorted({message for item in viable for message in item["unknowns"]})
    if not selected:
        status = "no_viable_configuration"
    elif all_unknowns:
        status = "provisional_recommendation"
    else:
        status = "recommendation_ready"
    comparison_ids = [item["product_id"] for item in viable[:3]]
    result = {
        "recommendation_id": f"rec-{intake['intake_id']}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "vertical": vertical,
        "synthetic_data_notice": (
            "All included product identities, specifications, prices, lead times, and evidence are fictional demonstration data."
        ),
        "decision_authority": "human_review_required",
        "intake_summary": _intake_summary(intake),
        "next_questions": next_questions(intake, knowledge["questions"]),
        "recommendation": selected,
        "alternatives": viable[1:3],
        "recommended_services": services,
        "competitive_context": _competitive_context(
            knowledge["competitive_observations"], comparison_ids
        ),
        "unresolved_constraints": all_unknowns,
        "rejected_products": rejected,
    }
    result["conversation_guide"] = build_conversation_guide(intake, result)
    return result


def _intake_summary(intake: dict[str, Any]) -> dict[str, Any]:
    context = intake.get("customer_context", {})
    workload = intake.get("workload", {})
    return {
        "organization_type": context.get("organization_type"),
        "seats": context.get("seats"),
        "primary_job": workload.get("primary_job"),
        "applications": workload.get("applications", []),
        "quantified_bottleneck": workload.get("quantified_bottleneck"),
        "business_impact": workload.get("business_impact"),
    }


def _competitive_context(
    snapshots: list[dict[str, Any]], product_ids: list[str]
) -> list[dict[str, Any]]:
    relevant = []
    wanted = set(product_ids)
    for snapshot in snapshots:
        for product in snapshot.get("products", []):
            if product.get("linked_product_id") not in wanted:
                continue
            relevant.append(
                {
                    "observation_id": snapshot["observation_id"],
                    "observed_at": snapshot["observed_at"],
                    "synthetic": snapshot.get("synthetic", False),
                    "source": snapshot.get("source", {}),
                    **product,
                }
            )
    return relevant
