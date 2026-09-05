"""Human-readable recommendation report."""

from __future__ import annotations

from typing import Any


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Solution Recommendation",
        "",
        f"**Status:** `{result['status']}`  ",
        f"**Decision authority:** `{result['decision_authority']}`  ",
        f"**Vertical:** `{result['vertical']}`",
        "",
        f"> **Synthetic demonstration:** {result['synthetic_data_notice']}",
        "",
        "## What we heard",
        "",
    ]
    summary = result["intake_summary"]
    lines.extend(
        [
            f"- **Organization:** {summary.get('organization_type') or 'Not supplied'}",
            f"- **Seats:** {summary.get('seats') or 'Not supplied'}",
            f"- **Primary job:** {summary.get('primary_job') or 'Not supplied'}",
            f"- **Applications:** {', '.join(summary.get('applications') or []) or 'Not supplied'}",
            f"- **Measured bottleneck:** {summary.get('quantified_bottleneck') or 'Not supplied'}",
            f"- **Business impact:** {summary.get('business_impact') or 'Not supplied'}",
            "",
        ]
    )

    selected = result.get("recommendation")
    if not selected:
        lines.extend(
            [
                "## No viable configuration",
                "",
                "Every candidate failed at least one hard requirement. Review the rejection reasons instead of forcing a recommendation.",
                "",
            ]
        )
    else:
        identity = selected["identity"]
        lines.extend(
            [
                "## Leading recommendation",
                "",
                f"### {identity['make']} {identity['model']} {identity['model_number']}",
                "",
                f"**Fit score:** {selected['score']} / 100",
                "",
                selected["description"],
                "",
                "### Configuration",
                "",
            ]
        )
        lines.extend(_configuration_lines(selected["configuration"]))
        lines.extend(["", "### Why it ranks first", ""])
        for name, dimension in selected["score_dimensions"].items():
            label = name.replace("_", " ").title()
            lines.append(
                f"- **{label} — {dimension['score']} / 100:** {dimension['explanation']}"
            )
        lines.append("")

    if result["recommended_services"]:
        lines.extend(["## Recommended services", ""])
        for service in result["recommended_services"]:
            lines.append(f"### {service['name']}")
            lines.append("")
            lines.append(service["description"])
            lines.append("")
            for reason in service["reasons"]:
                lines.append(f"- {reason}")
            lines.append("")

    if result["alternatives"]:
        lines.extend(["## Alternatives", ""])
        for alternative in result["alternatives"]:
            identity = alternative["identity"]
            lines.append(
                f"- **{identity['make']} {identity['model']} {identity['model_number']} — "
                f"{alternative['score']} / 100.** "
                f"{alternative['score_dimensions']['workload_fit']['explanation']}."
            )
        lines.append("")

    if result.get("competitive_context"):
        lines.extend(["## Competitive product observations", ""])
        lines.append(
            "These are dated, synthetic observations. They provide comparison context and do not override product constraints or evidence."
        )
        lines.append("")
        for observation in result["competitive_context"]:
            identity = observation["identity"]
            lines.append(
                f"### {identity['make']} {identity['model']} {identity['model_number']}"
            )
            lines.append("")
            lines.append(f"- **Observed:** {observation['observed_at']}")
            lines.append(
                f"- **Observed positioning:** {observation.get('positioning_observed', 'Not supplied')}"
            )
            for strength in observation.get("strengths_observed", []):
                lines.append(f"- **Observed strength:** {strength}")
            for risk in observation.get("risks_or_unknowns", []):
                lines.append(f"- **Risk or unknown:** {risk}")
            lines.append("")

    if result.get("conversation_guide"):
        lines.extend(["## Evidence-grounded conversation guide", ""])
        for step in result["conversation_guide"]:
            lines.append(f"### {step['stage'].title()}")
            lines.append("")
            if step.get("seller_language"):
                lines.append(f"> {step['seller_language']}")
                lines.append("")
            for question in step.get("questions", []):
                lines.append(f"- **Ask:** {question['seller_language']}")
                lines.append(f"  - **Reason:** {question['reason']}")
            if step.get("instruction"):
                lines.append(f"- **Instruction:** {step['instruction']}")
            for guardrail in step.get("guardrails", []):
                lines.append(f"- **Guardrail:** {guardrail}")
            if step.get("questions") or step.get("instruction") or step.get("guardrails"):
                lines.append("")

    unknowns = list(result.get("unresolved_constraints", []))
    questions = result.get("next_questions", [])
    if unknowns or questions:
        lines.extend(["## What still needs to be established", ""])
        for unknown in unknowns:
            lines.append(f"- **Unresolved constraint:** {unknown}")
        for question in questions:
            lines.append(
                f"- **Ask:** {question['question']} _Why: {question['why_it_matters']}_"
            )
        lines.append("")

    lines.extend(["## Rejected configurations", ""])
    if not result["rejected_products"]:
        lines.append("No products were rejected.")
    else:
        for product in result["rejected_products"]:
            identity = product["identity"]
            lines.append(
                f"### {identity['make']} {identity['model']} {identity['model_number']}"
            )
            lines.append("")
            for reason in product["failure_reasons"]:
                lines.append(f"- {reason}")
            lines.append("")

    lines.extend(
        [
            "## Human decision gate",
            "",
            "This output is decision support, not an approved quote or customer commitment. A qualified human must verify the intake, product evidence, current price, availability, compatibility, and recommendation before external use.",
            "",
        ]
    )
    return "\n".join(lines)


def _configuration_lines(specs: dict[str, Any]) -> list[str]:
    cpu = specs["cpu"]
    gpu = specs["gpu"]
    memory = specs["memory"]
    storage = specs["storage"]
    lines = [
        f"- **Form factor:** {specs['form_factor']}",
        f"- **CPU:** {cpu['make']} {cpu['model']}, {cpu['cores']} cores / {cpu['threads']} threads",
        f"- **GPU:** {gpu['make']} {gpu['model']}, {gpu['vram_gb']} GB {gpu['memory_type']}",
        f"- **Memory:** {memory['capacity_gb']} GB {memory['type']} {memory['speed_mt_s']} MT/s"
        + (" ECC" if memory.get("ecc") else ""),
        f"- **Primary storage:** {storage['primary']['capacity_tb']} TB {storage['primary']['type']} ({storage['primary']['interface']})",
        f"- **Total storage:** {storage['total_capacity_tb']} TB",
        f"- **Maximum system draw:** {specs['power']['max_draw_w']} W",
    ]
    display = specs.get("display")
    if display:
        lines.extend(
            [
                f"- **Display:** {display['size_inches']}-inch {display['panel_type']}, {display['resolution_width']}×{display['resolution_height']}",
                f"- **Display performance:** {display['refresh_hz']} Hz, {display['brightness_nits']} nits, {display['color_gamut_dci_p3_percent']}% DCI-P3",
            ]
        )
    return lines
