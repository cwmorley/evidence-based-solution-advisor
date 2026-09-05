# Knowledge Governance

## The plain-language version

A recommendation is only as trustworthy as the facts beneath it. Product specifications change, model names are reused, prices and availability expire, reviews describe different variants, and confident notes can outlive their sources.

This project therefore treats product knowledge as dated evidence rather than timeless truth. It also keeps proposals, approvals, transactions, and observed results separate. That lets a human inspect why an answer was produced and decide whether the evidence is current enough to use.

## Evidence classes

Do not collapse these into a single undifferentiated confidence score:

| Evidence class | Example | Establishes | Does not establish |
|---|---|---|---|
| Manufacturer claim | Published specification | What the manufacturer currently states | Independent performance or suitability |
| Distributor observation | Price and stock record | What was observed at a place and time | Future price or availability |
| Third-party review | Measured display brightness | A reviewer's observation on a particular sample | Performance of every model variant |
| Builder validation | Workload test on a named configuration | Result under the disclosed method | Formal third-party certification |
| Formal certification | Listed system/configuration | Certification within the program's scope | Fitness for every customer workload |
| Customer report | Current render takes four hours | Reported customer condition | Independently reproduced measurement |
| Engine recommendation | Product A ranks first | What the declared facts and rules produce | Human approval or successful deployment |
| Observed outcome | Accepted system completed the workload | Result of a specific real deployment | Universal suitability |

## Product identity

At minimum, normalize:

- Make
- Model
- Model number
- Vertical
- Product revision or generation where necessary
- Configuration identifier where specifications vary

Model number matters because similar marketing names often hide materially different hardware. A review or specification without resolved product identity should remain unmatched or low-confidence instead of being attached to the nearest plausible record.

Competitive observations use the same identity discipline. Positioning, observed price, lead time, strengths, and weaknesses are dated records. They may inform comparison and future questions, but they do not override a hard specification unless the source directly establishes that fact at sufficient confidence.

## Time and version

Mutable facts should carry:

- `observed_at`
- `effective_from`, when known
- `effective_to`, when known
- Lifecycle status
- Source identifier
- Applicable product/configuration

Price, inventory, lead time, certification, software compatibility, and support terms must be rechecked before an external commitment.

## Conflict handling

When two credible sources disagree:

1. Preserve both records.
2. Check whether they refer to different model numbers, configurations, regions, or dates.
3. Prefer primary evidence for the narrow fact it directly establishes.
4. Record the conflict if it cannot be resolved.
5. Downgrade confidence or block the affected rule when the conflict is material.
6. Ask for human review rather than silently choosing the convenient value.

## Decision and outcome stages

Keep these states distinct:

```text
captured → confirmed → recommended → approved → quoted → ordered
→ delivered → deployed → accepted → renewed / returned / failed
```

A recommendation is not a sale. A sale is not a successful deployment. A successful deployment is not proof that the system caused the customer's business result.

## Public-data boundary

The repository contains fictional examples only. A public deployment must exclude:

- Customer names and contact details
- Confidential workloads or datasets
- Contract pricing
- Non-public product roadmaps
- Proprietary support data
- Vendor-confidential compatibility information
- Private win/loss notes
- Unlicensed review text

Use synthetic examples or properly licensed, attributed public data. Store production customer data outside the public repository with appropriate access, retention, and deletion controls.
