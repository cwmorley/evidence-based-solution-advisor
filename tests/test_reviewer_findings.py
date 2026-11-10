from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.constraints import evaluate_rule  # noqa: E402
from solution_advisor.engine import recommend  # noqa: E402
from solution_advisor.io import load_json, load_knowledge_store  # noqa: E402
from solution_advisor.report import render_markdown  # noqa: E402
from solution_advisor.scoring import score_product  # noqa: E402


KNOWLEDGE = ROOT / "knowledge" / "workstations"
INTAKES = ROOT / "examples" / "intakes"
POWER_RULE = {
    "id": "power",
    "operator": "power_within_circuit",
    "amps_path": "environment.circuit_amps",
    "volts_path": "environment.voltage",
    "product_path": "specifications.power.max_draw_w",
    "unknown_message": "Power is unknown",
    "pass_message": "pass",
    "fail_message": "fail",
}


class NullValueTests(unittest.TestCase):
    def test_null_circuit_values_are_unknown_like_absent_ones(self):
        product = {"specifications": {"power": {"max_draw_w": 900}}}
        absent = evaluate_rule({"environment": {}}, product, POWER_RULE)
        for environment in ({"circuit_amps": None, "voltage": 120}, {"circuit_amps": 15, "voltage": None}):
            with self.subTest(environment=environment):
                result = evaluate_rule({"environment": environment}, product, POWER_RULE)
                self.assertEqual((result.status, result.message), (absent.status, absent.message))
                self.assertEqual(result.status, "unknown")

    def test_null_product_power_draw_fails_like_an_absent_one(self):
        intake = {"environment": {"circuit_amps": 15, "voltage": 120}}
        absent = evaluate_rule(intake, {"specifications": {"power": {}}}, POWER_RULE)
        null = evaluate_rule(intake, {"specifications": {"power": {"max_draw_w": None}}}, POWER_RULE)
        self.assertEqual((null.status, null.message), (absent.status, absent.message))
        self.assertEqual(null.status, "failed")

    def test_null_evidence_confidence_scores_like_an_absent_one(self):
        knowledge = load_knowledge_store(KNOWLEDGE)
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        absent = copy.deepcopy(knowledge["products"][0])
        null = copy.deepcopy(absent)
        del absent["evidence"][0]["confidence"]
        null["evidence"][0]["confidence"] = None
        self.assertEqual(score_product(intake, null, knowledge["scoring"]), score_product(intake, absent, knowledge["scoring"]))

    def test_intake_with_null_circuit_is_reported_as_missing_information(self):
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        intake["environment"]["circuit_amps"] = None
        result = recommend(intake, KNOWLEDGE)
        self.assertEqual(result["status"], "provisional_recommendation")
        self.assertIn("Available circuit capacity has not been measured or reported", result["unresolved_constraints"])


class ContinuousLoadFactorTests(unittest.TestCase):
    def run_with_factor(self, factor):
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "workstations"
            shutil.copytree(KNOWLEDGE, root)
            path = root / "rules" / "constraints.json"
            rules = json.loads(path.read_text(encoding="utf-8"))
            for rule in rules:
                if rule["operator"] == "power_within_circuit":
                    rule["continuous_load_factor"] = factor
            path.write_text(json.dumps(rules), encoding="utf-8")
            selected = recommend(intake, root)["recommendation"]
        amps, volts = intake["environment"]["circuit_amps"], intake["environment"]["voltage"]
        draw = selected["configuration"]["power"]["max_draw_w"]
        return selected, round(amps * volts * factor), draw

    def test_changing_the_rule_changes_the_constraint_and_the_score(self):
        for factor in (0.8, 0.9, 1.0):
            with self.subTest(factor=factor):
                selected, available, draw = self.run_with_factor(factor)
                power = next(item for item in selected["constraint_results"] if item["rule_id"] == "power_capacity")
                self.assertEqual(power["requirement"], available)
                self.assertEqual(
                    selected["score_dimensions"]["deployment_fit"]["explanation"],
                    f"{available - draw} W continuous-load headroom",
                )


class ConversationWordingTests(unittest.TestCase):
    def recommend_language(self, result):
        return next(item for item in result["conversation_guide"] if item["stage"] == "recommend")["seller_language"]

    def test_empty_catalogue_is_not_described_as_every_option_failing(self):
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        intake["vertical"] = "commercial-hvac"
        result = recommend(intake, KNOWLEDGE)
        self.assertEqual(result["rejected_products"], [])
        language = self.recommend_language(result)
        self.assertIn("no products for the commercial-hvac vertical", language)
        self.assertNotIn("fails at least one requirement", language)
        report = render_markdown(result)
        self.assertIn("no active products for the commercial-hvac vertical", report)
        self.assertNotIn("Every candidate failed", report)

    def test_all_products_rejected_says_every_option_fails(self):
        intake = load_json(INTAKES / "architecture-and-engineering.json")
        intake["requirements"]["min_gpu_vram_gb"] = 200
        result = recommend(intake, KNOWLEDGE)
        self.assertTrue(result["rejected_products"])
        language = self.recommend_language(result)
        self.assertIn("Every option fails at least one requirement", language)
        self.assertNotIn("no products for", language)
        self.assertIn("Every candidate failed at least one hard requirement", render_markdown(result))


if __name__ == "__main__":
    unittest.main()
