"""Turn scored accounts into HubSpot company property updates, as data only.

This module builds request bodies and never sends them. There is no HTTP
client, no token handling, and no network call anywhere in this package.

Request shape checked on 2026-11-10 against HubSpot's reference for
``POST /crm/v3/objects/companies/batch/update``:
https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/companies/batch/update-companies
The body is ``{"inputs": [{"id": "<company id>", "properties": {"<name>": "<string>"}}]}``;
``id`` and ``properties`` are required per input and property values are strings.
The limit of 100 inputs per batch request comes from
https://developers.hubspot.com/docs/api-reference/legacy/crm/using-object-apis
and clearing a value with an empty string from
https://developers.hubspot.com/docs/guides/api/crm/properties

The ``icp_*`` properties are custom. They must be created in the portal before
any real request would succeed; this module does not create them.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from .account_scoring import grade_for

BATCH_UPDATE_METHOD = "POST"
BATCH_UPDATE_PATH = "/crm/v3/objects/companies/batch/update"
MAX_INPUTS_PER_BATCH = 100
REQUIRED_PROPERTIES = (
    "icp_status", "icp_grade", "icp_score", "icp_reasons", "icp_confidence",
    "icp_missing_data", "icp_scored_at", "icp_rules_version",
)


class WritebackGuardError(ValueError):
    """A scored account is not safe to turn into a CRM update."""


def check_writeback(account: dict[str, Any], rules_version: Any, thresholds: list[dict[str, Any]]) -> None:
    """Refuse an account whose score, grade, version, or identity cannot be trusted."""
    label = account.get("account_id", "<unknown>")
    if not isinstance(rules_version, str) or not rules_version.strip():
        raise WritebackGuardError(f"{label}: rules version is missing")
    company_id = account.get("hubspot_company_id")
    if not isinstance(company_id, str) or not company_id.strip():
        raise WritebackGuardError(f"{label}: HubSpot company ID is missing")
    if account.get("status") == "disqualified":
        if not account.get("disqualification_reasons"):
            raise WritebackGuardError(f"{label}: disqualified without a reason")
        if account.get("score") is not None or account.get("grade") is not None:
            raise WritebackGuardError(f"{label}: a disqualified account must not carry a score or grade")
        return
    if account.get("status") != "scored":
        raise WritebackGuardError(f"{label}: unknown status {account.get('status')!r}")
    score = account.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
        raise WritebackGuardError(f"{label}: score is missing or not a finite number")
    contributions = account.get("contributions") or []
    for item in contributions:
        if not 0 <= item["contribution"] <= item["max_points"]:
            raise WritebackGuardError(f"{label}: {item['criterion']} contribution is outside 0..{item['max_points']:g}")
    total = round(sum(item["contribution"] for item in contributions), 2)
    if not contributions or total != score:
        raise WritebackGuardError(f"{label}: contributions sum to {total} but the score is {score}")
    expected = grade_for(score, thresholds)
    if account.get("grade") != expected:
        raise WritebackGuardError(
            f"{label}: grade {account.get('grade')!r} does not match the thresholds (score {score} is grade {expected})"
        )


def company_properties(account: dict[str, Any], rules_version: str, scored_at: str) -> dict[str, str]:
    """Property values for one company. Every value is a string, as the endpoint expects."""
    if account["status"] == "disqualified":
        # Empty strings clear any grade and score left by an earlier run.
        return {
            "icp_status": "disqualified",
            "icp_grade": "",
            "icp_score": "",
            "icp_reasons": "\n".join(f"Disqualified: {reason}" for reason in account["disqualification_reasons"]),
            "icp_confidence": "",
            "icp_missing_data": "",
            "icp_scored_at": scored_at,
            "icp_rules_version": rules_version,
        }
    reasons = account["reasons"]["positive"] + account["reasons"]["negative"]
    return {
        "icp_status": "scored",
        "icp_grade": account["grade"],
        "icp_score": f"{account['score']:.2f}",
        "icp_reasons": "\n".join(reasons),
        "icp_confidence": f"{account['confidence']['value']:.2f}",
        "icp_missing_data": "\n".join(entry["effect"] for entry in account["missing_data"]),
        "icp_scored_at": scored_at,
        "icp_rules_version": rules_version,
    }


def build_batch_updates(result: dict[str, Any], scored_at: str | None = None) -> list[dict[str, Any]]:
    """Describe the batch-update requests for a scoring result without sending them.

    Every account is checked first; one failing account stops the whole batch.
    """
    timestamp = normalize_timestamp(scored_at)
    accounts = result["scored_accounts"] + result["disqualified_accounts"]
    for account in accounts:
        check_writeback(account, result.get("rules_version"), result["grade_thresholds"])
    inputs = [
        {"id": account["hubspot_company_id"], "properties": company_properties(account, result["rules_version"], timestamp)}
        for account in sorted(accounts, key=lambda item: item["account_id"])
    ]
    return [
        {
            "dry_run": True,
            "sent": False,
            "method": BATCH_UPDATE_METHOD,
            "path": BATCH_UPDATE_PATH,
            "body": {"inputs": inputs[start:start + MAX_INPUTS_PER_BATCH]},
        }
        for start in range(0, len(inputs), MAX_INPUTS_PER_BATCH)
    ]


def normalize_timestamp(value: str | None) -> str:
    """Return an ISO 8601 UTC timestamp ending in Z; default to the current time."""
    if value is None:
        moment = datetime.now(timezone.utc)
    else:
        try:
            moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as exc:
            raise WritebackGuardError(f"scored-at is not an ISO 8601 timestamp: {value!r}") from exc
        if moment.tzinfo is None:
            raise WritebackGuardError(f"scored-at must include a UTC offset or Z: {value!r}")
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
