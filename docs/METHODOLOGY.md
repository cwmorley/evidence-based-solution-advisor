# Methodology

## The plain-language version

Do not start by asking which product the customer wants. Start by understanding the work, the measurable problem, the conditions in which the solution must operate, and whether solving it matters enough to justify action.

The advisor turns that discovery into a structured decision. It does not replace the conversation; it makes the reasoning inspectable and reusable.

## The five discovery movements

### 1. The job

Establish what the customer is actually doing:

- Applications or processes
- Project and dataset shape
- Deliverable
- Frequency and concurrency
- The point where the current system becomes the problem

The same product category may contain radically different jobs. Bursty rendering, continuous simulation, interactive design, and local inference should not collapse into “needs a fast computer.”

### 2. The bottleneck

Quantify the current behavior:

- How long does it take?
- How often does it occur?
- What capacity limit is observed?
- What has already been attempted?
- Is it annoying, or is it costing time, revenue, throughput, reliability, or opportunity?

“Rendering is slow” is weak input. “Four final renders per week take four hours each and regularly delay client review” can support evaluation and economic reasoning.

### 3. The environment

Identify constraints around the product:

- Existing equipment
- Seats and fleet size
- Physical location
- Electrical capacity
- Thermal and acoustic limits
- Network and security
- Software versions and plugins
- Certification or compliance
- Support responsibility

For high-power systems, the circuit question is not trivia. A configuration that cannot operate safely in the intended room is not a valid recommendation.

### 4. The economics

Determine whether a technically useful solution can become a responsible purchase:

- Value of solving the bottleneck
- Budget status and ceiling
- Decision participants
- Deadline and forcing event
- Cost of delay
- Cost of deployment failure

The advisor does not manufacture ROI when the inputs do not support it.

### 5. Evaluation and delivery tolerance

Ask every prospect:

- Would you run your own workload before committing?
- How long can delivery take before the answer stops being useful?

These fields improve individual recommendations and create an evidence base about lost opportunities, missing capabilities, and investment priorities.

## From discovery to recommendation

The method preserves four classes of output:

1. **Facts:** confirmed intake values and sourced product observations.
2. **Unknowns:** material values that remain unresolved.
3. **Rules and judgments:** declared feasibility logic and scoring weights.
4. **Decision state:** proposed, human-approved, quoted, ordered, delivered, deployed, or observed outcome.

The reference implementation stops at `human_review_required`.

## Scoring interpretation

The score is a comparison aid, not a scientific truth claim. It is applied only to products that meet the hard constraints.

Current dimensions are:

- Workload fit
- Economic fit
- Delivery fit
- Evidence confidence
- Deployment fit

Weights belong to the vertical scoring profile and should be tested with domain experts. Changing a weight is a visible policy decision, not hidden model behavior.

### Fixed ranges and contributions

The `workstation-balanced-v2` profile removes the constant support score; support remains a hard constraint. Its former weight is redistributed proportionally across the five remaining dimensions. Each scoring function declares a fixed range: workload 65–100, deployment 55–100, and the others 0–100. Deployment includes the existing unresolved-circuit fallback of 55; measured deployment scores remain 70–100. These endpoints describe existing formulas and fallbacks, not validated buyer utility.

For each dimension, `normalized = (raw - range_min) / (range_max - range_min)` and `contribution = 100 * normalized * weight`. The total is the sum of contributions, rounded once to two decimals. A dimension at its minimum contributes zero; at its maximum it contributes its full weighted share of 100. Non-finite or out-of-range values, non-positive range widths, and invalid weight profiles raise `ScoringProfileError`; they are not silently clamped.

JSON retains every raw score and explanation and adds the range, normalized score, weight, and contribution. The Markdown report exposes this arithmetic for the leading recommendation. The profile ID identifies the changed scoring interpretation; v1 and v2 totals are not interchangeable.

Normalization uses fixed declared ranges, never the spread of the current candidate set. Weights express tradeoffs over those ranges, not guaranteed influence in every sample. Products with similar prices can reasonably have similar economic contributions. Fixed scales do not validate the weights or the utility formulas. Missing inputs still use the documented baseline defaults; normalization does not resolve uncertainty, and provisional status and human review remain in force.

### Weight diagnostics

Run `solution-advisor score-diagnostics examples/intakes/architecture-and-engineering.json examples/intakes/local-ai-development.json examples/intakes/mobile-media-production.json`. Add `--format json` for structured output. Every active product of the matching vertical without a failed constraint is included, even if it falls outside the recommendation's top three; unknown constraints remain possible. Each intake/product pair is one observation. With multiple intakes the result pools those observations, so use a single intake when inspecting one customer's ordering.

The table reports observed raw minimum, maximum and spread, the profile weight, and the spread of normalized weighted contributions in points. This is a descriptive sample diagnostic, not causal attribution or evidence that the largest observed spread should receive the largest weight. Empty sets report `n/a`; one observation has zero spread. Diagnostics do not change recommendations or rescale scores.

## Validation protocol

Before extending features, evaluate the method with representative cases:

1. Capture the expert's recommendation before showing the engine result.
2. Run the same structured intake through the advisor.
3. Compare rejected products, top-two ranking, missing questions, and services.
4. Record disagreements by cause: bad fact, missing fact, bad rule, bad weight, or expert preference.
5. Correct the smallest responsible layer.
6. Re-run prior cases to check for regression.

A polished explanation does not count as validation. Useful evidence is agreement on technical reasoning, discovery of a missed constraint, improved evaluation quality, fewer deployment surprises, or adoption in a real workflow.
