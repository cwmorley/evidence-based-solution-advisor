import copy
import io
import json
import math
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.cli import main
from solution_advisor.diagnostics import score_diagnostics
from solution_advisor.engine import recommend
from solution_advisor.io import load_json, load_knowledge_store
from solution_advisor.scoring import ScoringProfileError, normalize_dimension, score_product
from solution_advisor.report import render_markdown

KNOWLEDGE = ROOT / "knowledge/workstations"
INTAKES = ROOT / "examples/intakes"


class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.knowledge = load_knowledge_store(KNOWLEDGE)
        self.profile = self.knowledge["scoring"]
        self.intake = load_json(INTAKES / "architecture-and-engineering.json")

    def test_support_removed_and_weights_redistributed_proportionally(self):
        old = dict(workload_fit=.35, economic_fit=.20, delivery_fit=.15, evidence_confidence=.15, deployment_fit=.10)
        self.assertEqual(set(old), set(self.profile["weights"]))
        self.assertAlmostEqual(sum(self.profile["weights"].values()), 1)
        for name, value in old.items():
            self.assertAlmostEqual(self.profile["weights"][name], value / .95)

    def test_each_dimension_endpoints_map_to_zero_and_full_contribution(self):
        _, dimensions = score_product(self.intake, self.knowledge["products"][0], self.profile)
        for name, dimension in dimensions.items():
            for key, expected in (("range_min", 0), ("range_max", 1)):
                probe = {**dimension, "score": dimension[key]}
                contribution = 100 * normalize_dimension(name, probe) * dimension["weight"]
                self.assertAlmostEqual(contribution, 100 * expected * dimension["weight"])

    def test_invalid_ranges_scores_and_weights_raise_named_error(self):
        for low, high, score in ((1, 1, 1), (2, 1, 1), (0, 1, 2), (0, 1, math.nan)):
            with self.subTest(low=low, high=high, score=score), self.assertRaises(ScoringProfileError):
                normalize_dimension("probe", dict(range_min=low, range_max=high, score=score))
        for value in (-1, math.nan, 2):
            profile = copy.deepcopy(self.profile)
            profile["weights"]["economic_fit"] = value
            with self.assertRaises(ScoringProfileError):
                score_product(self.intake, self.knowledge["products"][0], profile)

    def test_incomplete_deployment_is_in_declared_range_and_remains_provisional(self):
        result = recommend(load_json(INTAKES / "incomplete-discovery.json"), KNOWLEDGE)
        dimension = result["recommendation"]["score_dimensions"]["deployment_fit"]
        self.assertEqual(dimension["score"], 55)
        self.assertEqual(dimension["normalized_score"], 0)
        self.assertEqual(result["status"], "provisional_recommendation")
        self.assertEqual(result["decision_authority"], "human_review_required")

    def test_weight_sensitivity_reverses_a_constructed_tradeoff(self):
        # Same viable hardware: lower price competes with better documented evidence.
        first = copy.deepcopy(next(p for p in self.knowledge["products"] if p["product_id"] == "northstar-arcstation-as-4200"))
        second = copy.deepcopy(first)
        budget = self.intake["commercial"]["budget_usd_max"]
        first["commercial"]["sample_price_usd"] = budget * .75
        second["commercial"]["sample_price_usd"] = budget
        first["evidence"] = [{"confidence": .7}]
        second["evidence"] = [{"confidence": .9}]
        base_first = score_product(self.intake, first, self.profile)[0]
        base_second = score_product(self.intake, second, self.profile)[0]
        self.assertLess(base_first, base_second)
        changed = copy.deepcopy(self.profile)
        weight = changed["weights"]["economic_fit"]
        scale = (1 - 2 * weight) / (1 - weight)
        changed["weights"] = {name: (2 * value if name == "economic_fit" else value * scale) for name, value in changed["weights"].items()}
        self.assertGreater(score_product(self.intake, first, changed)[0], score_product(self.intake, second, changed)[0])

    def test_total_is_reconstructible_and_deterministic_for_every_example(self):
        for path in INTAKES.glob("*.json"):
            result = recommend(load_json(path), KNOWLEDGE)
            repeated = recommend(load_json(path), KNOWLEDGE)
            self.assertEqual(result["recommendation"], repeated["recommendation"])
            self.assertEqual(result["alternatives"], repeated["alternatives"])
            for candidate in [result["recommendation"], *result["alternatives"]]:
                if candidate:
                    dimensions = candidate["score_dimensions"]
                    self.assertNotIn("support_fit", dimensions)
                    self.assertEqual(candidate["score"], round(sum(d["weighted_contribution"] for d in dimensions.values()), 2))
                    self.assertTrue(all(0 <= d["normalized_score"] <= 1 for d in dimensions.values()))

    def test_diagnostics_include_all_viable_products_and_do_not_change_results(self):
        intake = copy.deepcopy(self.intake)
        intake.update(requirements={}, environment={}, commercial={})
        before = recommend(intake, KNOWLEDGE)
        result = score_diagnostics([intake], KNOWLEDGE)
        expected = len(self.knowledge["products"]) - len(before["rejected_products"])
        self.assertEqual(result["viable_observations"], expected)
        self.assertGreater(expected, 3)
        self.assertEqual(before["recommendation"], recommend(intake, KNOWLEDGE)["recommendation"])
        self.assertEqual(len(result["dimensions"]), 5)

    def test_diagnostics_empty_and_single_viable_sets(self):
        intake = copy.deepcopy(self.intake)
        intake["requirements"]["min_gpu_vram_gb"] = 10000
        empty = score_diagnostics([intake], KNOWLEDGE)
        self.assertEqual(empty["viable_observations"], 0)
        self.assertTrue(all(d["observed_min"] is None for d in empty["dimensions"]))
        ai = load_json(INTAKES / "local-ai-development.json")
        ai["commercial"]["budget_usd_max"] = 18000
        # Establish the singleton using the actual hard constraints.
        from solution_advisor.constraints import evaluate_constraints
        viable = [p for p in self.knowledge["products"] if not any(c.status == "failed" for c in evaluate_constraints(ai, p, self.knowledge["constraints"]))]
        if len(viable) != 1:
            self.fail(f"constructed singleton must have exactly one viable product, got {len(viable)}")
        single = score_diagnostics([ai], KNOWLEDGE)
        self.assertEqual(single["viable_observations"], 1)
        self.assertTrue(all(d["realized_weighted_influence"] == 0 for d in single["dimensions"]))

    def test_diagnostics_cli_json(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["score-diagnostics", str(INTAKES / "architecture-and-engineering.json"), "--knowledge", str(KNOWLEDGE), "--format", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["profile_id"], "workstation-balanced-v2")

    def test_report_exposes_each_leading_contribution_and_raw_explanation(self):
        result = recommend(self.intake, KNOWLEDGE)
        report = render_markdown(result)
        for dimension in result["recommendation"]["score_dimensions"].values():
            self.assertIn(f"raw {dimension['score']} / 100", report)
            self.assertIn(dimension["explanation"], report)
            self.assertIn(f"contribution {dimension['weighted_contribution']:.2f} points", report)
