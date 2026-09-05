# Architecture

## The plain-language version

This system helps a seller or advisor avoid recommending the wrong thing confidently.

It begins with what the customer needs to accomplish, what is currently failing, and which practical constraints matter. It checks those needs against a maintained catalog of products and services. Products that cannot do the job are rejected with explicit reasons. The remaining choices are ranked, their tradeoffs are explained, and relevant services are included so the solution has a better chance of working after it arrives.

The benefit is not simply faster quoting. It is a more defensible buying decision, fewer avoidable deployment surprises, clearer customer communication, and a reusable record of why the recommendation was made.

The system can later use AI to ask questions or explain technical details. AI does not get to change a product specification, waive a compatibility failure, or convert missing evidence into a fact.

## System components

| Component | Job | Does not do |
|---|---|---|
| Intake | Records the customer's job, bottleneck, environment, economics, and requirements | Assume the requested part number is the requirement |
| Question catalog | Finds high-value missing information | Ask endless generic questions |
| Product knowledge | Stores stable identity, vertical specifications, commercial observations, and evidence | Treat stale or conflicting facts as timeless truth |
| Competitive observations | Logs dated comparison products, positioning, strengths, risks, price, and lead time by resolved identity | Turn a market claim into a verified product fact |
| Service knowledge | Represents assessment, evaluation, migration, deployment, training, and support as recommendable offers | Add services merely to increase order value |
| Constraint engine | Rejects configurations that fail hard requirements | Average a hard failure into a weighted score |
| Ranking engine | Compares viable configurations using visible dimensions and weights | Pretend the score is objective or universally correct |
| Report generator | Explains the recommendation, alternatives, unknowns, and rejected choices | Approve a quote or make a customer commitment |
| Conversation guide | Adapts seller language to confirmed facts, missing questions, and the recommendation state | Generate unsupported persuasion or conceal uncertainty |
| Human decision gate | Verifies facts and accepts responsibility for external use | Rubber-stamp generated output |
| Outcome loop | Records what was sold, deployed, observed, or rejected | Treat a recommendation as a successful outcome |

## Processing sequence

```text
1. Load and minimally validate the intake.
2. Load the vertical's products, services, constraints, questions, and scoring profile.
3. Evaluate every active product against every applicable hard constraint.
4. Preserve passed, failed, skipped, and unknown results separately.
5. Remove products with one or more failures from ranking.
6. Score viable products across declared dimensions.
7. Select the leading recommendation and alternatives.
8. Match services to intake and selected-product conditions.
9. Identify unanswered discovery questions.
10. Generate JSON for systems and Markdown for humans.
11. Hold the result at human_review_required.
```

## Why constraints and scoring are separate

Suppose a configuration is inexpensive, available tomorrow, and supported by excellent evidence—but has 48 GB of GPU memory when the workload requires 96 GB. A weighted scoring model could still rank it highly if price and availability have enough weight. That would be mathematically tidy and technically wrong.

The advisor therefore uses two stages:

- **Feasibility:** Does the product satisfy every stated hard requirement?
- **Preference:** Among feasible products, which best balances fit, cost, delivery, evidence, deployment, and support?

No score can rescue a feasibility failure.

## Stable envelope, flexible vertical

Product records separate universal identity and evidence fields from vertical specifications.

Universal fields include:

- Product ID
- Make
- Model
- Model number
- Vertical
- Vertical schema version
- Lifecycle status
- Effective dates
- Commercial observations
- Evidence records

The `specifications` object is vertical-specific. Workstations use processor, graphics, memory, storage, power, operating system, certification, form factor, and display fields. A commercial HVAC vertical could instead use capacity, efficiency, refrigerant, electrical service, climate constraints, dimensions, controls, and installation requirements.

This avoids both extremes: a rigid universal schema that cannot represent real products and an unstructured document store that cannot support deterministic decisions.

## Knowledge sources and future integrations

The reference implementation reads version-controlled JSON files. A production implementation could ingest governed outputs from:

- Manufacturer catalogs and documentation
- Distributor availability and pricing feeds
- Product information management systems
- Review and competitive-intelligence pipelines
- Benchmark repositories
- CRM discovery records
- Support, return, and deployment systems
- Human-approved knowledge records

Integration does not erase provenance. Each imported claim should retain source, observation date, product identity, applicable version, and confidence.

## Optional AI layer

An AI adapter can sit around the deterministic core to:

- Convert a conversation into proposed structured intake fields
- Detect contradictions or ambiguity
- Ask the next best question
- Explain technical tradeoffs in the buyer's language
- Draft a follow-up or CRM summary

The adapter should receive explicit tools rather than unrestricted write access:

```text
propose_intake_update()
get_missing_questions()
evaluate_constraints()
rank_viable_products()
explain_recommendation()
request_human_approval()
```

Every AI-derived intake value remains a proposal until the seller or customer confirms it. The model must cite the structured fields and evidence records used in an explanation.

## Production concerns deliberately outside v0.1

- Authentication and permissions
- Customer-data encryption and retention
- Catalog ingestion and conflict resolution
- Temporal databases or event sourcing
- CRM and CPQ integration
- Multi-tenant isolation
- Quote generation and approval routing
- Regulated-product controls
- Outcome analytics and causal validation
- Language-model provider adapters

Those are real production requirements. They are excluded so the reference implementation can prove the reasoning boundary first.
