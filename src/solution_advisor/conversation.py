"""Build an adaptive, evidence-grounded conversation guide.

This is deliberately not free-form persuasion. The guide changes according to
confirmed intake facts, missing information, constraint results, and the current
recommendation state.
"""

from __future__ import annotations

from typing import Any


def build_conversation_guide(
    intake: dict[str, Any], result: dict[str, Any]
) -> list[dict[str, Any]]:
    workload = intake.get("workload", {})
    primary_job = workload.get("primary_job")
    bottleneck = workload.get("quantified_bottleneck")
    impact = workload.get("business_impact")
    guide: list[dict[str, Any]] = []

    if primary_job:
        opener = (
            "Before we get to a configuration, I want to make sure we solve the right problem. "
            f"You are trying to {primary_job[0].lower() + primary_job[1:]}. "
            "Walk me through where the current system gets in the way."
        )
    else:
        opener = (
            "Happy to get to products and specifications, but recommending one before I understand "
            "the work would be an expensive guess. What are you trying to accomplish, and where "
            "does the current solution get in the way?"
        )
    guide.append({"stage": "frame", "seller_language": opener})

    if bottleneck or impact:
        facts = [item for item in (bottleneck, impact) if item]
        guide.append(
            {
                "stage": "playback",
                "seller_language": "Let me make sure I have this right: " + " ".join(facts),
                "instruction": "Ask the buyer to correct the playback before proceeding.",
            }
        )

    questions = result.get("next_questions", [])
    if questions:
        guide.append(
            {
                "stage": "diagnose",
                "questions": [
                    {
                        "seller_language": item["question"],
                        "reason": item["why_it_matters"],
                    }
                    for item in questions
                ],
            }
        )

    selected = result.get("recommendation")
    if selected:
        identity = selected["identity"]
        unknowns = result.get("unresolved_constraints", [])
        guide.append(
            {
                "stage": "recommend",
                "seller_language": (
                    f"Based on what we have established so far, the leading fit is the "
                    f"{identity['make']} {identity['model']} {identity['model_number']}. "
                    "That is a provisional recommendation until the remaining facts and current "
                    "commercial details are verified."
                ),
                "unresolved_before_quote": unknowns,
            }
        )
    else:
        guide.append(
            {
                "stage": "recommend",
                "seller_language": (
                    "I do not have a responsible configuration to recommend from the current "
                    "catalog. Every option fails at least one requirement, so the next step is to "
                    "verify the requirements or find a different solution—not force a quote."
                ),
            }
        )

    guide.append(
        {
            "stage": "close",
            "seller_language": (
                "The next useful step is to verify the unresolved facts, confirm current product "
                "evidence and availability, and agree on the evaluation or decision date."
            ),
            "guardrails": [
                "Do not present synthetic prices, lead times, products, or certifications as real.",
                "Do not claim a configuration is approved until a qualified human reviews it.",
                "Do not hide failed constraints or unresolved facts to preserve momentum.",
            ],
        }
    )
    return guide
