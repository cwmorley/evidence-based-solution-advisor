"""Transparent scoring for configurations that pass hard constraints."""

from __future__ import annotations

import math
from typing import Any

from .io import get_path


class ScoringProfileError(ValueError):
    """Invalid score range, weight, or dimension value."""


def score_product(
    intake: dict[str, Any], product: dict[str, Any], profile: dict[str, Any]
) -> tuple[float, dict[str, dict[str, Any]]]:
    dimensions = {
        "workload_fit": _workload_fit(intake, product, profile),
        "economic_fit": _economic_fit(intake, product),
        "delivery_fit": _delivery_fit(intake, product),
        "evidence_confidence": _evidence_confidence(product),
        "deployment_fit": _deployment_fit(intake, product),
    }
    weights = profile["weights"]
    if set(weights) != set(dimensions):
        raise ScoringProfileError("weights must name exactly the scoring dimensions")
    values = [float(value) for value in weights.values()]
    if any(not math.isfinite(value) or value < 0 for value in values) or not math.isclose(sum(values), 1.0, abs_tol=1e-9):
        raise ScoringProfileError("weights must be finite, nonnegative, and sum to 1")
    total = 0.0
    for name, dimension in dimensions.items():
        normalized = normalize_dimension(name, dimension)
        weight = float(weights[name])
        contribution = 100.0 * normalized * weight
        dimension.update(normalized_score=normalized, weight=weight, weighted_contribution=contribution)
        total += contribution
    return round(total, 2), dimensions


def normalize_dimension(name: str, dimension: dict[str, Any]) -> float:
    low, high = dimension["range_min"], dimension["range_max"]
    raw = dimension["score"]
    if not all(math.isfinite(value) for value in (low, high, raw)):
        raise ScoringProfileError(f"{name}: score and bounds must be finite")
    if high <= low:
        raise ScoringProfileError(f"{name}: score range must have positive width")
    if not low <= raw <= high:
        raise ScoringProfileError(f"{name}: score {raw} outside declared range [{low}, {high}]")
    return (raw - low) / (high - low)


def _workload_fit(
    intake: dict[str, Any], product: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    comparisons = []
    for item in profile["capacity_dimensions"]:
        required = get_path(intake, item["requirement_path"])
        observed = get_path(product, item["product_path"])
        if required in (None, 0) or observed is None:
            continue
        ratio = float(observed) / float(required)
        target = float(item.get("target_headroom_ratio", 1.25))
        score = max(65.0, 100.0 - abs(ratio - target) * 40.0)
        comparisons.append((item["label"], round(ratio, 2), score))
    if not comparisons:
        return {"range_min": 65.0, "range_max": 100.0, "score": 70.0, "explanation": "No capacity targets were supplied"}
    score = sum(item[2] for item in comparisons) / len(comparisons)
    detail = ", ".join(f"{label} {ratio}x minimum" for label, ratio, _ in comparisons)
    return {"range_min": 65.0, "range_max": 100.0, "score": round(score, 2), "explanation": detail}


def _economic_fit(intake: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    budget = get_path(intake, "commercial.budget_usd_max")
    price = get_path(product, "commercial.sample_price_usd")
    if not budget or price is None:
        return {"range_min": 0.0, "range_max": 100.0, "score": 65.0, "explanation": "Budget or sample price is unresolved"}
    utilization = float(price) / float(budget)
    score = max(0.0, 100.0 - utilization * 40.0)
    return {
        "range_min": 0.0, "range_max": 100.0,
        "score": round(score, 2),
        "explanation": f"Synthetic sample price uses {utilization:.0%} of stated ceiling",
    }


def _delivery_fit(intake: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    maximum = get_path(intake, "commercial.lead_time_weeks_max")
    lead = get_path(product, "commercial.sample_lead_time_weeks")
    if not maximum or lead is None:
        return {"range_min": 0.0, "range_max": 100.0, "score": 65.0, "explanation": "Delivery tolerance or lead time is unresolved"}
    utilization = float(lead) / float(maximum)
    score = max(0.0, 100.0 - utilization * 30.0)
    return {
        "range_min": 0.0, "range_max": 100.0,
        "score": round(score, 2),
        "explanation": f"Synthetic lead time uses {utilization:.0%} of allowed window",
    }


def _evidence_confidence(product: dict[str, Any]) -> dict[str, Any]:
    records = product.get("evidence", [])
    if not records:
        return {"range_min": 0.0, "range_max": 100.0, "score": 0.0, "explanation": "No evidence records supplied"}
    score = sum(float(record.get("confidence", 0)) for record in records) / len(records) * 100
    return {
        "range_min": 0.0, "range_max": 100.0,
        "score": round(score, 2),
        "explanation": f"Mean confidence across {len(records)} evidence record(s)",
    }


def _deployment_fit(intake: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    amps = get_path(intake, "environment.circuit_amps")
    volts = get_path(intake, "environment.voltage")
    draw = get_path(product, "specifications.power.max_draw_w")
    if not amps or not volts or draw is None:
        return {"range_min": 55.0, "range_max": 100.0, "score": 55.0, "explanation": "Circuit capacity remains unverified"}
    available = float(amps) * float(volts) * 0.8
    headroom = max(0.0, 1.0 - float(draw) / available)
    return {
        "range_min": 55.0, "range_max": 100.0,
        "score": round(min(100.0, 70.0 + headroom * 30.0), 2),
        "explanation": f"{round(available - float(draw))} W continuous-load headroom",
    }
