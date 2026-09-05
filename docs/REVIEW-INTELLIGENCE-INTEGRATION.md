# Review Intelligence Integration

## The plain-language version

Product specifications describe what a product is supposed to be. Reviews and field reports describe what people experienced. Both are useful, but they answer different questions and should not be blended into one untraceable score.

A review-intelligence pipeline can feed this advisor with resolved product identity, recurring strengths and defects, comparison observations, source dates, evidence confidence, and applicable product versions. The advisor can then show that context beside a recommendation, flag a risk, or ask for validation—without allowing an unsourced review claim to rewrite a hard specification.

## Ownership boundary

The upstream review pipeline owns:

- Source acquisition and terms-of-use compliance
- Duplicate and spam handling
- Make, model, and model-number resolution
- Review-to-product matching confidence
- Aspect and issue extraction
- Competitive mention extraction
- Time and version relevance
- Reviewer and evidence confidence
- Licensed retention of source text

The solution advisor owns:

- Customer requirements
- Product and service feasibility rules
- Preference scoring
- Recommendation and rejection explanations
- Service matching
- Human decision state
- Downstream outcome references

## Suggested exchange record

```json
{
  "observation_id": "review-intel-example-001",
  "product_identity": {
    "make": "Example Make",
    "model": "Example Model",
    "model_number": "EX-100"
  },
  "identity_confidence": 0.94,
  "observed_at": "2026-09-01",
  "applicable_version": "2026 revision",
  "aspect": "display_brightness",
  "observation_type": "measured_review_result",
  "normalized_value": {"value": 438, "unit": "nits"},
  "direction": "risk",
  "evidence_confidence": 0.87,
  "source_reference": "licensed-or-linked-upstream-reference"
}
```

The advisor should reject or quarantine the record when identity cannot be resolved to the applicable make, model, model number, and version.

## Appropriate uses

- Add an unresolved-risk note to the recommendation.
- Reduce evidence confidence for a disputed claim.
- Ask the seller to validate a recurring compatibility problem.
- Compare a manufacturer claim with independent measurement.
- Surface a dated competitive strength or weakness.
- Prioritize which configuration should receive a workload test.

## Inappropriate uses

- Treat sentiment as proof of technical compatibility.
- Copy copyrighted review text into a public knowledge store.
- Apply a complaint about one model number to an entire product family.
- Convert a recurring issue into a hard exclusion without a declared policy and adequate evidence.
- Hide contradictory reviews behind an average score.
- Assume a reviewer's reported configuration matches the buyer's proposed configuration.

## Integration sequence

1. Resolve the observed product identity.
2. Confirm date, version, region, and configuration applicability.
3. Store the observation and its confidence without overwriting primary specifications.
4. Map the observation to a risk, preference, or validation question.
5. Require human review before promoting it to a hard rule.
6. Preserve the upstream reference so the reasoning can be audited.
