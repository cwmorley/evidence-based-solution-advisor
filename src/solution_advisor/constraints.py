"""Declarative hard-constraint evaluation.

Generative AI is deliberately absent from this module. A configuration either
meets a stated hard requirement, fails it with a reason, or remains unresolved
because required evidence is missing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .io import get_path


MISSING = object()
SUPPORT_LEVELS = {"standard": 0, "next_business_day": 1, "onsite": 2}


@dataclass(frozen=True)
class ConstraintResult:
    rule_id: str
    status: str
    message: str
    requirement: Any = None
    observed: Any = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_constraints(
    intake: dict[str, Any], product: dict[str, Any], rules: list[dict[str, Any]]
) -> list[ConstraintResult]:
    return [evaluate_rule(intake, product, rule) for rule in rules]


def evaluate_rule(
    intake: dict[str, Any], product: dict[str, Any], rule: dict[str, Any]
) -> ConstraintResult:
    rule_id = rule["id"]
    if not _condition_applies(intake, rule.get("condition")):
        return ConstraintResult(rule_id, "skipped", "Rule condition does not apply")

    operator = rule["operator"]
    if operator == "power_within_circuit":
        return _evaluate_power(intake, product, rule)

    requirement = get_path(intake, rule["requirement_path"], MISSING)
    if requirement is MISSING or requirement is None or requirement == []:
        return _missing_requirement(rule)

    observed = get_path(product, rule["product_path"], MISSING)
    if observed is MISSING or observed is None:
        return ConstraintResult(
            rule_id,
            "failed",
            rule.get("missing_product_message", "Required product evidence is missing"),
            requirement=requirement,
        )

    passed = _compare(operator, observed, requirement)
    template_key = "pass_message" if passed else "fail_message"
    template = rule.get(template_key, f"{rule_id}: {'passed' if passed else 'failed'}")
    message = template.format(requirement=requirement, observed=observed)
    return ConstraintResult(
        rule_id,
        "passed" if passed else "failed",
        message,
        requirement=requirement,
        observed=observed,
    )


def _condition_applies(intake: dict[str, Any], condition: dict[str, Any] | None) -> bool:
    if not condition:
        return True
    actual = get_path(intake, condition["path"], MISSING)
    if "equals" in condition:
        return actual == condition["equals"]
    if "in" in condition:
        return actual in condition["in"]
    return True


def _missing_requirement(rule: dict[str, Any]) -> ConstraintResult:
    behavior = rule.get("on_missing_requirement", "skipped")
    if behavior == "unknown":
        return ConstraintResult(
            rule["id"],
            "unknown",
            rule.get("unknown_message", "Customer requirement has not been established"),
        )
    if behavior == "failed":
        return ConstraintResult(
            rule["id"],
            "failed",
            rule.get("unknown_message", "Required customer information is missing"),
        )
    return ConstraintResult(rule["id"], "skipped", "No corresponding requirement stated")


def _compare(operator: str, observed: Any, requirement: Any) -> bool:
    if operator == "product_gte_requirement":
        return float(observed) >= float(requirement)
    if operator == "product_lte_requirement":
        return float(observed) <= float(requirement)
    if operator == "product_in_requirement_list":
        return observed in requirement
    if operator == "product_contains_all_requirement":
        return set(requirement).issubset(set(observed))
    if operator == "product_equals_requirement":
        return observed == requirement
    if operator == "support_at_least":
        return SUPPORT_LEVELS.get(str(observed), -1) >= SUPPORT_LEVELS.get(str(requirement), 99)
    raise ValueError(f"Unsupported constraint operator: {operator}")


def _evaluate_power(
    intake: dict[str, Any], product: dict[str, Any], rule: dict[str, Any]
) -> ConstraintResult:
    amps = get_path(intake, rule["amps_path"], MISSING)
    volts = get_path(intake, rule["volts_path"], MISSING)
    observed = get_path(product, rule["product_path"], MISSING)
    if amps is MISSING or volts is MISSING:
        return ConstraintResult(
            rule["id"],
            "unknown",
            rule.get("unknown_message", "Available circuit capacity has not been verified"),
            observed=None if observed is MISSING else observed,
        )
    if observed is MISSING:
        return ConstraintResult(
            rule["id"], "failed", "Product maximum power draw is missing"
        )
    factor = float(rule.get("continuous_load_factor", 0.8))
    available_watts = float(amps) * float(volts) * factor
    passed = float(observed) <= available_watts
    template = rule["pass_message" if passed else "fail_message"]
    return ConstraintResult(
        rule["id"],
        "passed" if passed else "failed",
        template.format(observed=observed, available=round(available_watts)),
        requirement=round(available_watts),
        observed=observed,
    )
