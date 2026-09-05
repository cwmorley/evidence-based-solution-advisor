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
- Support fit

Weights belong to the vertical scoring profile and should be tested with domain experts. Changing a weight is a visible policy decision, not hidden model behavior.

## Validation protocol

Before extending features, evaluate the method with representative cases:

1. Capture the expert's recommendation before showing the engine result.
2. Run the same structured intake through the advisor.
3. Compare rejected products, top-two ranking, missing questions, and services.
4. Record disagreements by cause: bad fact, missing fact, bad rule, bad weight, or expert preference.
5. Correct the smallest responsible layer.
6. Re-run prior cases to check for regression.

A polished explanation does not count as validation. Useful evidence is agreement on technical reasoning, discovery of a missed constraint, improved evaluation quality, fewer deployment surprises, or adoption in a real workflow.
