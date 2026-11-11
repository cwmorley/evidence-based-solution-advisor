"""Score accounts against an ICP: disqualify, score, grade, and explain.

The ICP plays the intake role and each account plays the product role, so hard
disqualifiers run through the shared constraint engine unchanged. The shared
``score_product`` function is specific to the workstation dimensions, so this
module evaluates declarative criteria from the vertical's scoring profile and
reuses the shared weight validation and fixed-range normalization.

Every weight, score, threshold, and band lives in the rules files. Nothing in
this module writes to a CRM.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .constraints import evaluate_constraints
from .io import AdvisorDataError, get_path, load_json, validate_intake
from .scoring import ScoringProfileError, normalize_dimension, validate_weights

ACCOUNT_REQUIRED_FIELDS = ("account_id", "synthetic", "vertical", "status", "name", "firmographics", "signals", "evidence")
SYNTHETIC_NOTICE = (
    "All included accounts, firmographics, signals, CRM identifiers, ICP rules, and weights are fictional "
    "demonstration data. Nothing has been written to a live CRM."
)


def load_account_store(root: str | Path) -> dict[str, Any]:
    base = Path(root)
    accounts_dir = base / "accounts"
    if not accounts_dir.is_dir():
        raise AdvisorDataError(f"Missing accounts directory: {accounts_dir}")
    accounts = [load_json(path) for path in sorted(accounts_dir.glob("*.json"))]
    for account in accounts:
        for field in ACCOUNT_REQUIRED_FIELDS:
            if field not in account:
                raise AdvisorDataError(f"Account {account.get('account_id', '<unknown>')} is missing: {field}")
    identifiers = [account["account_id"] for account in accounts]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        raise AdvisorDataError(f"Duplicate account IDs: {', '.join(duplicates)}")
    return {
        "accounts": accounts,
        "constraints": load_json(base / "rules" / "constraints.json"),
        "scoring": load_json(base / "rules" / "scoring-profile.json"),
    }


def score_accounts(icp: dict[str, Any], knowledge_root: str | Path) -> dict[str, Any]:
    validate_intake(icp)
    store = load_account_store(knowledge_root)
    profile = store["scoring"]
    validate_profile(profile)
    thresholds = profile["grade_thresholds"]
    scored, disqualified = [], []
    for account in store["accounts"]:
        if account["vertical"] != icp["vertical"] or account.get("status") != "active":
            continue
        result = score_account(icp, account, store["constraints"], profile)
        (disqualified if result["status"] == "disqualified" else scored).append(result)
    scored.sort(key=lambda item: (-item["score"], item["account_id"]))
    disqualified.sort(key=lambda item: item["account_id"])
    return {
        "scoring_id": f"score-{icp['intake_id']}",
        "status": "accounts_scored" if scored else "no_qualified_account",
        "vertical": icp["vertical"],
        "icp_id": icp["intake_id"],
        "motion": icp.get("motion"),
        "rules_version": rules_version(icp, profile),
        "synthetic_data_notice": SYNTHETIC_NOTICE,
        "decision_authority": "human_review_required",
        "crm_write_status": "not_written",
        "grade_thresholds": thresholds,
        "scored_accounts": scored,
        "disqualified_accounts": disqualified,
    }


def rules_version(icp: dict[str, Any], profile: dict[str, Any]) -> str | None:
    """Identify the scoring profile and the ICP revision together; None if either is absent."""
    parts = (profile.get("profile_id"), icp.get("intake_id"), icp.get("icp_version"))
    if not all(isinstance(part, str) and part.strip() for part in parts):
        return None
    return f"{parts[0]}/{parts[1]}@{parts[2]}"


def validate_profile(profile: dict[str, Any]) -> None:
    weights = profile["weights"]
    criteria_ids = [criterion["id"] for criterion in profile["criteria"]]
    if len(set(criteria_ids)) != len(criteria_ids) or set(criteria_ids) != set(weights):
        raise ScoringProfileError("weights must name exactly the scoring criteria")
    validate_weights(weights)
    minimums = [float(item["min_score"]) for item in profile["grade_thresholds"]]
    if not minimums or minimums != sorted(minimums, reverse=True) or len(set(minimums)) != len(minimums) or minimums[-1] != 0:
        raise ScoringProfileError("grade thresholds must be strictly descending and end at 0")
    bands = [float(item["min"]) for item in profile["confidence_bands"]]
    if not bands or bands != sorted(bands, reverse=True) or bands[-1] != 0:
        raise ScoringProfileError("confidence bands must be descending and end at 0")


def grade_for(score: float, thresholds: list[dict[str, Any]]) -> str:
    for item in thresholds:
        if score >= float(item["min_score"]):
            return item["grade"]
    raise ScoringProfileError(f"score {score} is below every grade threshold")


def score_account(
    icp: dict[str, Any], account: dict[str, Any], rules: list[dict[str, Any]], profile: dict[str, Any]
) -> dict[str, Any]:
    results = evaluate_constraints(icp, account, rules)
    failures = [item for item in results if item.status == "failed"]
    unknowns = [item for item in results if item.status == "unknown"]
    output: dict[str, Any] = {
        "account_id": account["account_id"],
        "name": account["name"],
        "synthetic": account["synthetic"],
        "hubspot_company_id": get_path(account, "crm.hubspot_company_id"),
        "status": "disqualified" if failures else "scored",
        "constraint_results": [item.as_dict() for item in results],
        "disqualification_reasons": [item.message for item in failures],
    }
    if failures:
        # A hard failure is never scored, so no score exists that could rescue it.
        output.update(grade=None, score=None)
        return output

    contributions = [_evaluate_criterion(account, criterion, profile["weights"]) for criterion in profile["criteria"]]
    score = round(sum(item["contribution"] for item in contributions), 2)
    missing = [item for item in contributions if item["status"] == "missing"]
    ceiling = round(score + sum(item["max_points"] for item in missing), 2)
    thresholds = profile["grade_thresholds"]
    grade, grade_ceiling = grade_for(score, thresholds), grade_for(ceiling, thresholds)

    applicable = [item for item in results if item.status != "skipped"]
    known_weight = sum(item["weight"] for item in contributions if item["status"] == "scored")
    resolved_share = 1.0 if not applicable else (len(applicable) - len(unknowns)) / len(applicable)
    confidence = round(known_weight * resolved_share, 2)
    band = next(item["band"] for item in profile["confidence_bands"] if confidence >= float(item["min"]))

    missing_data = [
        {"field": item.rule_id, "kind": "disqualifier_check", "effect": item.message} for item in unknowns
    ] + [
        {
            "field": item["path"],
            "kind": "criterion",
            "effect": f"{item['label']} is unknown: scored 0 of {item['max_points']:g} possible points until resolved",
        }
        for item in missing
    ]
    output.update(
        grade=grade,
        score=score,
        contributions=contributions,
        reasons=_reasons(contributions, int(profile.get("reason_limit", 3))),
        missing_data=missing_data,
        confidence={
            "value": confidence,
            "band": band,
            "known_criterion_weight": round(known_weight, 4),
            "resolved_disqualifier_share": round(resolved_share, 4),
        },
        score_ceiling_if_resolved=ceiling,
        grade_ceiling_if_resolved=grade_ceiling,
        provisional=bool(missing_data),
    )
    return output


def _evaluate_criterion(account: dict[str, Any], criterion: dict[str, Any], weights: dict[str, Any]) -> dict[str, Any]:
    name = criterion["id"]
    weight = float(weights[name])
    observed = get_path(account, criterion["path"])
    if isinstance(observed, str) and not observed.strip():
        observed = None  # a blank CRM field is unknown, the same as null or absent
    item: dict[str, Any] = {
        "criterion": name,
        "group": criterion["group"],
        "label": criterion["label"],
        "path": criterion["path"],
        "weight": weight,
        "max_points": round(100.0 * weight, 4),
        "observed": observed,
    }
    # A JSON null, an absent key, and a blank string are the same thing: unknown.
    # Unknown is reported and earns no points; it is never treated as a known "no".
    if observed is None:
        item.update(status="missing", raw_score=None, normalized_score=None, contribution=0.0,
                    explanation=f"{criterion['label']} is unknown")
        return item
    raw, explanation = _raw_score(criterion, observed)
    normalized = normalize_dimension(name, {"range_min": 0.0, "range_max": 1.0, "score": raw})
    item.update(status="scored", raw_score=raw, normalized_score=normalized,
                contribution=round(100.0 * normalized * weight, 4), explanation=explanation)
    return item


def _raw_score(criterion: dict[str, Any], observed: Any) -> tuple[float, str]:
    kind = criterion["kind"]
    if kind == "boolean":
        if not isinstance(observed, bool):
            raise ScoringProfileError(f"{criterion['id']}: expected true or false, got {observed!r}")
        key = "true" if observed else "false"
        return float(criterion[f"score_{key}"]), criterion[f"explain_{key}"]
    if kind == "lookup":
        values = observed if isinstance(observed, list) else [observed]
        default = float(criterion["default_score"])
        raw = max((float(criterion["scores"].get(str(value), default)) for value in values), default=default)
        shown = (", ".join(str(value) for value in values) or "empty") if isinstance(observed, list) else observed
        return raw, criterion["explain"].format(observed=shown)
    if kind == "tiers":
        if isinstance(observed, bool) or not isinstance(observed, (int, float)):
            raise ScoringProfileError(f"{criterion['id']}: expected a number, got {observed!r}")
        reached = [tier for tier in criterion["tiers"] if observed >= float(tier["min"])]
        raw = float(max(reached, key=lambda tier: float(tier["min"]))["score"]) if reached else 0.0
        return raw, criterion["explain"].format(observed=observed)
    raise ScoringProfileError(f"{criterion['id']}: unsupported criterion kind {kind!r}")


def _reasons(contributions: list[dict[str, Any]], limit: int) -> dict[str, list[str]]:
    known = [item for item in contributions if item["status"] == "scored"]
    gained = sorted((item for item in known if item["contribution"] > 0),
                    key=lambda item: (-item["contribution"], item["criterion"]))
    lost = sorted((item for item in known if item["max_points"] - item["contribution"] > 0),
                  key=lambda item: (-(item["max_points"] - item["contribution"]), item["criterion"]))
    return {
        "positive": [
            f"+{item['contribution']:g} of {item['max_points']:g}: {item['label']} - {item['explanation']}"
            for item in gained[:limit]
        ],
        "negative": [
            f"-{round(item['max_points'] - item['contribution'], 4):g} of {item['max_points']:g}: {item['label']} - {item['explanation']}"
            for item in lost[:limit]
        ],
    }


def render_account_report(result: dict[str, Any]) -> str:
    thresholds = ", ".join(f"{item['grade']} >= {item['min_score']:g}" for item in result["grade_thresholds"])
    lines = [
        f"# Account scoring: {result['icp_id']}",
        "",
        f"> {result['synthetic_data_notice']}",
        "",
        f"- Status: `{result['status']}`",
        f"- Rules version: `{result['rules_version']}`",
        f"- Grade thresholds: {thresholds}",
        f"- Decision authority: `{result['decision_authority']}`; CRM write status: `{result['crm_write_status']}`",
        "",
        "## Scored accounts",
        "",
    ]
    if not result["scored_accounts"]:
        lines.append("No account passed the hard disqualifiers.")
    for item in result["scored_accounts"]:
        confidence = item["confidence"]
        lines.append(f"### {item['grade']} | {item['score']:.2f} | {item['name']} (`{item['account_id']}`)")
        lines.append("")
        lines.append(f"- Confidence: {confidence['value']:.2f} ({confidence['band']})")
        if item["provisional"]:
            lines.append(
                f"- Provisional: could reach {item['score_ceiling_if_resolved']:.2f} "
                f"(grade {item['grade_ceiling_if_resolved']}) if every unknown resolved favourably"
            )
        lines.extend(f"- {reason}" for reason in item["reasons"]["positive"] + item["reasons"]["negative"])
        lines.extend(f"- Missing: {entry['effect']}" for entry in item["missing_data"])
        lines.extend(["", "| Criterion | Group | Raw | Weight | Points |", "|---|---|---:|---:|---:|"])
        for part in item["contributions"]:
            raw = "unknown" if part["raw_score"] is None else f"{part['raw_score']:.2f}"
            lines.append(f"| {part['label']} | {part['group']} | {raw} | {part['weight']:.2f} | {part['contribution']:.2f} |")
        lines.append("")
    lines.extend(["## Disqualified accounts", ""])
    if not result["disqualified_accounts"]:
        lines.append("None.")
    for item in result["disqualified_accounts"]:
        lines.append(f"- {item['name']} (`{item['account_id']}`): " + "; ".join(item["disqualification_reasons"]))
    return "\n".join(lines) + "\n"
