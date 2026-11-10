# Extending a Product Vertical

## The plain-language version

The advisor is not hard-coded to recommend computers, but each category needs its own definition of a good decision. A laptop display, an HVAC compressor, an insurance policy, and a managed service do not share meaningful specifications just because all four can be sold.

To add a vertical, keep the common identity and evidence envelope, then define only the specifications, questions, constraints, services, and preferences that matter to that category.

## Extension checklist

1. Choose one narrow customer decision, not an entire industry.
2. Define product identity: make, model, model number, version, and configuration.
3. Define the vertical specification object.
4. Define the customer intake fields that can establish requirements.
5. Separate hard feasibility constraints from weighted preferences.
6. Add next questions for material missing facts.
7. Define services that reduce implementation or outcome risk.
8. Add source, date, scope, and confidence to product evidence.
9. Create at least three synthetic scenarios, including one with no viable answer.
10. Have domain experts challenge failures, rankings, and missing questions.

## Example: workstation specification object

```json
{
  "form_factor": "laptop",
  "cpu": {"make": "...", "model": "...", "cores": 16, "threads": 32},
  "gpu": {"make": "...", "model": "...", "vram_gb": 16, "memory_type": "GDDR7"},
  "memory": {"capacity_gb": 64, "type": "DDR5", "speed_mt_s": 5600, "ecc": false},
  "storage": {
    "total_capacity_tb": 2,
    "primary": {"capacity_tb": 2, "type": "NVMe SSD", "interface": "PCIe 4.0"}
  },
  "power": {"max_draw_w": 280},
  "display": {
    "size_inches": 16,
    "panel_type": "OLED",
    "resolution_width": 3840,
    "resolution_height": 2400,
    "refresh_hz": 120,
    "brightness_nits": 500,
    "color_gamut_dci_p3_percent": 100
  }
}
```

## Example: unrelated vertical

A commercial cooling system might use:

```json
{
  "capacity_tons": 20,
  "efficiency": {"ieer": 18.2},
  "refrigerant": "example-refrigerant",
  "electrical": {"voltage": 460, "phase": 3},
  "dimensions_mm": {"width": 2200, "depth": 900, "height": 1800},
  "ambient_operating_range_c": {"minimum": -20, "maximum": 52},
  "controls": ["BACnet"],
  "sound_db": 76
}
```

The shared engine can compare numeric, categorical, and set-valued facts, but domain experts must define what constitutes failure and what merely affects preference.

## Rule quality questions

For every proposed rule, ask:

- Is this truly a hard constraint?
- Which intake fact establishes the requirement?
- Which product fact proves compliance?
- What happens if either fact is missing?
- Does the rule apply to every product subtype?
- Is the source current and specific to this model number?
- Can a human understand the failure message?
- What representative case would prove this rule wrong?

If those questions cannot be answered, the rule is not ready to automate.

## Worked example: account scoring

### The plain-language version

A second vertical ships with the repository: deciding which companies a sales team should work first. The business writes its rules down before anything is automated. Some companies are ruled out outright, the rest are graded A to D, and every grade comes with the points behind it and a list of what is still unknown. The practical benefit is a priority list a rep can argue with, because each number traces to a written rule.

All twelve accounts, their signals, the CRM identifiers, the ICP, and every weight are fictional. Nothing has been written to a live CRM, no HubSpot portal or API was called, and the package contains no HTTP client.

### What fit the shared engine and what did not

| Part | Fit | What was done |
|---|---|---|
| Hard constraints (`constraints.py`) | Fits. The ICP is the intake and the account is the product. | Reused unchanged in shape. Two small additions: the `product_not_in_requirement_list` operator for exclusion lists, and an opt-in `on_missing_product: "unknown"` rule setting. Without it a missing product fact fails, which is right for a product specification and wrong for an account whose industry nobody has recorded yet. |
| Weight validation and fixed-range normalization (`scoring.py`) | Fits. | `validate_weights` and `normalize_dimension` are reused, so contributions use the same arithmetic as the workstation vertical. |
| `score_product` (`scoring.py`) | Does not fit. Its five dimensions are workstation formulas (capacity headroom, price against budget, circuit headroom). | Not bent. `account_scoring.py` evaluates criteria declared in the scoring profile instead. |
| Product envelope and `load_knowledge_store` (`io.py`) | Does not fit. An account has no make, model, or model number, and no services or question catalog. | Not bent. `load_account_store` reads `accounts/` and `rules/` and reuses `load_json`, `get_path`, and `validate_intake`. |
| `engine.recommend` | Does not fit. It picks one product and attaches services and a conversation guide. Account scoring grades every account. | A separate `score_accounts` orchestration with the same constraint-then-score order. |

So this is a second vertical under `knowledge/account-scoring/` plus one small module, not a pure data-only extension.

### How the checklist was applied

1. Narrow decision: grade accounts for one sales motion against one ICP.
2. Identity: `account_id`, `name`, and a fictional `crm.hubspot_company_id`.
3. Specification object: `firmographics` and `signals` ([schema](../schemas/account.schema.json)).
4. Intake: the ICP file (`examples/icps/`), with `motion` and `requirements`.
5. Hard and weighted rules are in separate files: `rules/constraints.json` and `rules/scoring-profile.json`.
6. Missing facts: reported per account as `missing_data` instead of a question catalog.
7. Services: not applicable to this decision; none were added.
8. Evidence: every account carries a dated synthetic evidence record. Per-signal source and date are not modelled.
9. Three scenarios: new-logo, expansion, and an enterprise-only ICP that no account meets.
10. Expert challenge: **not done.** No sales or RevOps practitioner has reviewed these rules or weights.

### Hard disqualifiers

| Rule | Fails when | If the account fact is unknown |
|---|---|---|
| `excluded_industry` | Industry is in the ICP's `excluded_industries` | Unresolved, reported, lowers confidence |
| `minimum_size` | Employee band is not in the ICP's `allowed_employee_bands` | Unresolved, reported, lowers confidence |
| `new_logo_only` | The account is an existing customer and the ICP `motion` is `new_logo` | Unresolved, reported, lowers confidence |

A disqualified account receives no score and no grade, so a strong signal cannot rescue it.

### Weights

Weights sum to 1, so each is also the criterion's maximum points out of 100. Fit totals 55 and intent totals 45. Each criterion scores 0 to 1 from a table in the profile, and `points = 100 * score * weight`. The reasoning for each weight is stored beside it as `rationale` in `scoring-profile.json`. These are illustrative policy choices, not fitted to any outcome data.

| Criterion | Group | Weight | Scoring |
|---|---|---:|---|
| Industry fit | fit | 0.15 | b2b_saas 1.0, fintech 0.8, professional_services 0.6, manufacturing 0.4, other 0.2 |
| Company size fit | fit | 0.15 | 201-500 and 501-1000 1.0, 51-200 0.6, 1001-5000 0.5, 5001+ 0.2 |
| Revenue band fit | fit | 0.10 | 10m-50m 1.0, 50m-250m 0.7, 1m-10m 0.6, 250m+ 0.3, <1m 0.1 |
| Tech stack fit | fit | 0.10 | hubspot 1.0, salesforce 0.5, otherwise 0; best entry in the list |
| Region fit | fit | 0.05 | north_america 1.0, emea 0.7, apac and latam 0.4 |
| Pricing-page visits (30 days) | intent | 0.12 | 5 or more 1.0, 2 to 4 0.6, 1 0.3 |
| Hiring for RevOps | intent | 0.10 | 2 or more open roles 1.0, 1 role 0.7 |
| Recent funding | intent | 0.08 | yes 1.0 |
| Champion job change | intent | 0.07 | yes 1.0 |
| Open opportunity | intent | 0.05 | yes 1.0 |
| No incumbent competitor | intent | 0.03 | no competitor 1.0, competitor in use 0 |

Grade thresholds: A at 75 or more, B at 55, C at 35, D below 35. Each contribution is rounded to four decimals and the score is the sum of those contributions rounded to two, so the parts always reconstruct the total. Ties are ordered by `account_id`.

### Unknown values

A JSON `null` and an absent key mean the same thing: unknown. An empty list is a known "none". An unknown criterion earns 0 points, is marked `missing`, appears in `missing_data`, and is left out of the negative reasons, because "we do not know" is not evidence against the account. The output also shows `score_ceiling_if_resolved` and `grade_ceiling_if_resolved`, and sets `provisional`.

`confidence = (weight of criteria with known values) * (share of applicable disqualifier checks that were resolved)`. Bands are in the profile: high at 0.85, medium at 0.6, otherwise low. This is a completeness measure, not a probability of winning the deal.

### CRM write-back as data

`crm_writeback.build_batch_updates` turns a scoring result into request descriptions for HubSpot's company batch update. It builds data and stops. Run it with `solution-advisor score-accounts examples/icps/new-logo-revops.json --dry-run`.

```json
{
  "dry_run": true,
  "sent": false,
  "method": "POST",
  "path": "/crm/v3/objects/companies/batch/update",
  "body": {"inputs": [{"id": "9000000001", "properties": {"icp_grade": "A", "icp_score": "95.00"}}]}
}
```

These custom company properties must exist in the portal before a real request could succeed. This repository does not create them. Suggested types are a proposal, not something HubSpot requires:

| Property | Suggested type | Value |
|---|---|---|
| `icp_status` | dropdown: scored, disqualified | Whether the account was graded or ruled out |
| `icp_grade` | dropdown: A, B, C, D | Cleared when disqualified |
| `icp_score` | number | Two decimals; cleared when disqualified |
| `icp_reasons` | multi-line text | Top positive and negative drivers, or the disqualification reason |
| `icp_confidence` | number | 0 to 1 |
| `icp_missing_data` | multi-line text | One line per unknown |
| `icp_scored_at` | date and time | ISO 8601 UTC |
| `icp_rules_version` | single-line text | Scoring profile, ICP, and ICP revision |

Before any payload is produced, a guard refuses the whole batch if for any account the contributions do not sum to the score, a contribution is outside its range, the rules version is missing, the grade does not match the thresholds, the company ID is missing, or a disqualified account carries a score or lacks a reason.

### What was checked against HubSpot's documentation

Checked on 2026-11-10 by reading the public documentation only:

- `POST /crm/v3/objects/companies/batch/update` takes `{"inputs": [{"id": "...", "properties": {...}}]}`. `id` and `properties` are required per input, property values are strings, `idProperty` and `objectWriteTraceId` are optional, and the scope is `crm.objects.companies.write`. Source: <https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/companies/batch/update-companies>
- Object batch endpoints accept at most 100 inputs per request. Source: <https://developers.hubspot.com/docs/api-reference/legacy/crm/using-object-apis>
- An empty string clears a property value, and date-time values may be ISO 8601 strings in UTC. Source: <https://developers.hubspot.com/docs/guides/api/crm/properties>

Not verified:

- No request was sent to HubSpot, so acceptance of these exact bodies by a real portal is untested.
- HubSpot files this endpoint's specification under a `legacy` path and also documents date-versioned paths such as `/crm/objects/2026-09/companies/{companyId}`. Whether the batch update has a date-versioned equivalent that should be preferred was not confirmed.
- Empty-string clearing is documented for single-record updates; it was not confirmed specifically for the batch endpoint.
- Rate limits, partial-failure (HTTP 207) handling, retries, and idempotency are not implemented.
- The synthetic company IDs do not exist anywhere. Matching real accounts to company records is out of scope.
