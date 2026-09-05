from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.engine import recommend  # noqa: E402
from solution_advisor.io import load_json, load_knowledge_store  # noqa: E402
from solution_advisor.report import render_markdown  # noqa: E402


KNOWLEDGE = ROOT / "knowledge" / "workstations"
INTAKES = ROOT / "examples" / "intakes"


class RecommendationEngineTests(unittest.TestCase):
    def run_example(self, name: str):
        return recommend(load_json(INTAKES / name), KNOWLEDGE)

    def test_aec_selects_balanced_configuration(self):
        result = self.run_example("architecture-and-engineering.json")
        self.assertEqual(result["status"], "recommendation_ready")
        self.assertEqual(
            result["recommendation"]["product_id"], "northstar-arcstation-as-4200"
        )
        service_ids = {item["service_id"] for item in result["recommended_services"]}
        self.assertEqual(
            service_ids,
            {
                "application-optimization",
                "deployment-readiness",
                "migration-and-rollout",
                "workload-validation",
            },
        )

    def test_local_ai_rejects_insufficient_gpu_memory(self):
        result = self.run_example("local-ai-development.json")
        self.assertEqual(result["recommendation"]["configuration"]["gpu"]["vram_gb"], 96)
        self.assertEqual(
            result["recommendation"]["product_id"], "vertex-machine-cognition-cm-96"
        )
        self.assertEqual(
            result["alternatives"][0]["product_id"], "northstar-arcstation-as-9600"
        )
        rejected = {item["product_id"]: item for item in result["rejected_products"]}
        self.assertTrue(
            any(
                "at least 96 GB" in reason
                for reason in rejected["northstar-render-rack-rr-4800"]["failure_reasons"]
            )
        )

    def test_mobile_scenario_evaluates_display_requirements(self):
        result = self.run_example("mobile-media-production.json")
        selected = result["recommendation"]
        self.assertEqual(selected["configuration"]["form_factor"], "laptop")
        display = selected["configuration"]["display"]
        self.assertEqual(display["panel_type"], "OLED")
        self.assertGreaterEqual(display["resolution_width"], 3840)
        self.assertGreaterEqual(display["color_gamut_dci_p3_percent"], 95)
        rule_status = {
            item["rule_id"]: item["status"] for item in selected["constraint_results"]
        }
        for rule in (
            "laptop_panel_type",
            "laptop_display_size",
            "laptop_horizontal_resolution",
            "laptop_vertical_resolution",
            "laptop_color_gamut",
            "laptop_brightness",
            "laptop_refresh_rate",
        ):
            self.assertEqual(rule_status[rule], "passed")

    def test_hard_failure_cannot_be_rescued_by_scoring(self):
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        intake = copy.deepcopy(intake)
        intake["requirements"]["min_gpu_vram_gb"] = 200
        result = recommend(intake, KNOWLEDGE)
        self.assertEqual(result["status"], "no_viable_configuration")
        self.assertIsNone(result["recommendation"])
        self.assertEqual(result["alternatives"], [])
        self.assertTrue(result["rejected_products"])
        for product in result["rejected_products"]:
            self.assertNotIn("score", product)

    def test_incomplete_discovery_exposes_unknowns_and_questions(self):
        result = self.run_example("incomplete-discovery.json")
        self.assertEqual(result["status"], "provisional_recommendation")
        fields = {item["field"] for item in result["next_questions"]}
        self.assertIn("workload.primary_job", fields)
        self.assertIn("workload.quantified_bottleneck", fields)
        self.assertIn("workload.business_impact", fields)
        self.assertIn(
            "Available circuit capacity has not been measured or reported",
            result["unresolved_constraints"],
        )
        self.assertEqual(result["decision_authority"], "human_review_required")

    def test_all_product_identities_are_complete_and_synthetic(self):
        knowledge = load_knowledge_store(KNOWLEDGE)
        for product in knowledge["products"]:
            self.assertTrue(product["synthetic"])
            self.assertTrue(product["identity"]["make"])
            self.assertTrue(product["identity"]["model"])
            self.assertTrue(product["identity"]["model_number"])
        self.assertGreaterEqual(
            len({product["identity"]["make"] for product in knowledge["products"]}), 3
        )

    def test_competitive_observations_are_dated_and_identity_resolved(self):
        result = self.run_example("architecture-and-engineering.json")
        self.assertTrue(result["competitive_context"])
        for observation in result["competitive_context"]:
            self.assertTrue(observation["observed_at"])
            self.assertTrue(observation["synthetic"])
            self.assertTrue(observation["identity"]["make"])
            self.assertTrue(observation["identity"]["model"])
            self.assertTrue(observation["identity"]["model_number"])

    def test_report_carries_synthetic_and_human_review_boundaries(self):
        report = render_markdown(self.run_example("architecture-and-engineering.json"))
        self.assertIn("Synthetic demonstration", report)
        self.assertIn("Human decision gate", report)
        self.assertIn("human_review_required", report)
        self.assertIn("AS-4200", report)

    def test_conversation_guide_adapts_to_missing_information(self):
        complete = self.run_example("architecture-and-engineering.json")
        incomplete = self.run_example("incomplete-discovery.json")
        complete_stages = {item["stage"] for item in complete["conversation_guide"]}
        incomplete_stages = {item["stage"] for item in incomplete["conversation_guide"]}
        self.assertNotIn("diagnose", complete_stages)
        self.assertIn("diagnose", incomplete_stages)
        recommend_step = next(
            item for item in incomplete["conversation_guide"] if item["stage"] == "recommend"
        )
        self.assertTrue(recommend_step["unresolved_before_quote"])


if __name__ == "__main__":
    unittest.main()
