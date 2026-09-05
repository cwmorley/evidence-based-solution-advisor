"""Service recommendation from intake and selected-product conditions."""

from __future__ import annotations

from typing import Any

from .io import get_path


MISSING = object()


def recommend_services(
    intake: dict[str, Any], product: dict[str, Any], services: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    recommendations = []
    for service in services:
        matched = []
        for group in service.get("trigger_groups", []):
            results = [_matches(trigger, intake, product) for trigger in group["triggers"]]
            applies = all(results) if group.get("mode", "all") == "all" else any(results)
            if applies:
                matched.append(group.get("reason", "Service trigger matched"))
        if matched:
            recommendations.append(
                {
                    "service_id": service["service_id"],
                    "name": service["name"],
                    "description": service["description"],
                    "reasons": matched,
                }
            )
    return recommendations


def _matches(
    trigger: dict[str, Any], intake: dict[str, Any], product: dict[str, Any]
) -> bool:
    source = intake if trigger.get("source", "intake") == "intake" else product
    value = get_path(source, trigger["path"], MISSING)
    operator = trigger["operator"]
    expected = trigger.get("value")
    if operator == "missing":
        return value is MISSING or value is None
    if value is MISSING:
        return False
    if operator == "equals":
        return value == expected
    if operator == "gte":
        return float(value) >= float(expected)
    if operator == "in":
        return value in expected
    raise ValueError(f"Unsupported service trigger operator: {operator}")
