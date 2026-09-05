"""Describe observed score variation without using it to rescale candidates."""

from pathlib import Path
from typing import Any

from .constraints import evaluate_constraints
from .io import load_knowledge_store, validate_intake
from .scoring import score_product


def score_diagnostics(intakes: list[dict[str, Any]], knowledge_root: str | Path) -> dict:
    knowledge = load_knowledge_store(knowledge_root)
    observations: dict[str, list[dict]] = {name: [] for name in knowledge["scoring"]["weights"]}
    count = 0
    for intake in intakes:
        validate_intake(intake)
        for product in knowledge["products"]:
            if product["vertical"] != intake["vertical"] or product.get("status") != "active":
                continue
            constraints = evaluate_constraints(intake, product, knowledge["constraints"])
            if any(item.status == "failed" for item in constraints):
                continue
            _, dimensions = score_product(intake, product, knowledge["scoring"])
            count += 1
            for name, dimension in dimensions.items():
                observations[name].append(dimension)
    rows = []
    for name, values in observations.items():
        raw = [value["score"] for value in values]
        contributions = [value["weighted_contribution"] for value in values]
        rows.append({
            "dimension": name,
            "observed_min": min(raw) if raw else None,
            "observed_max": max(raw) if raw else None,
            "observed_spread": max(raw) - min(raw) if raw else None,
            "weight": knowledge["scoring"]["weights"][name],
            "realized_weighted_influence": max(contributions) - min(contributions) if contributions else None,
        })
    return {"profile_id": knowledge["scoring"]["profile_id"], "viable_observations": count, "dimensions": rows}


def render_diagnostics(result: dict) -> str:
    lines = [
        f"Scoring profile: {result['profile_id']}; viable intake/product observations: {result['viable_observations']}",
        "",
        "| Dimension | Observed min | Max | Spread | Weight | Contribution spread (points) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["dimensions"]:
        numbers = [row[key] for key in ("observed_min", "observed_max", "observed_spread", "weight", "realized_weighted_influence")]
        cells = ["n/a" if value is None else f"{value:.4f}" for value in numbers]
        lines.append("| " + " | ".join([row["dimension"], *cells]) + " |")
    lines.extend(["", "Observed spread describes this sample; it is not causal importance or validation of the weights."])
    return "\n".join(lines)
