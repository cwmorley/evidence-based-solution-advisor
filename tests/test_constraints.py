from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.constraints import evaluate_rule  # noqa: E402


class ConstraintTests(unittest.TestCase):
    def test_power_uses_continuous_load_factor(self):
        intake = {"environment": {"circuit_amps": 15, "voltage": 120}}
        product = {"specifications": {"power": {"max_draw_w": 1500}}}
        rule = {
            "id": "power",
            "operator": "power_within_circuit",
            "amps_path": "environment.circuit_amps",
            "volts_path": "environment.voltage",
            "product_path": "specifications.power.max_draw_w",
            "continuous_load_factor": 0.8,
            "pass_message": "{observed} <= {available}",
            "fail_message": "{observed} > {available}",
        }
        result = evaluate_rule(intake, product, rule)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.requirement, 1440)

    def test_missing_power_information_remains_unknown(self):
        intake = {"environment": {}}
        product = {"specifications": {"power": {"max_draw_w": 900}}}
        rule = {
            "id": "power",
            "operator": "power_within_circuit",
            "amps_path": "environment.circuit_amps",
            "volts_path": "environment.voltage",
            "product_path": "specifications.power.max_draw_w",
            "unknown_message": "Power is unknown",
            "pass_message": "pass",
            "fail_message": "fail",
        }
        result = evaluate_rule(intake, product, rule)
        self.assertEqual(result.status, "unknown")
        self.assertEqual(result.message, "Power is unknown")

    def test_set_requirement_requires_every_item(self):
        intake = {"requirements": {"apps": ["A", "B"]}}
        product = {"specifications": {"certifications": ["A"]}}
        rule = {
            "id": "certs",
            "operator": "product_contains_all_requirement",
            "requirement_path": "requirements.apps",
            "product_path": "specifications.certifications",
            "pass_message": "pass",
            "fail_message": "missing {requirement}",
        }
        result = evaluate_rule(intake, product, rule)
        self.assertEqual(result.status, "failed")

    def test_exclusion_list_fails_only_listed_values(self):
        intake = {"requirements": {"excluded": ["gambling"]}}
        rule = {
            "id": "excluded",
            "operator": "product_not_in_requirement_list",
            "requirement_path": "requirements.excluded",
            "product_path": "firmographics.industry",
            "pass_message": "{observed} allowed",
            "fail_message": "{observed} excluded",
        }
        listed = evaluate_rule(intake, {"firmographics": {"industry": "gambling"}}, rule)
        other = evaluate_rule(intake, {"firmographics": {"industry": "b2b_saas"}}, rule)
        self.assertEqual((listed.status, listed.message), ("failed", "gambling excluded"))
        self.assertEqual(other.status, "passed")

    def test_missing_product_fact_fails_by_default_and_can_be_declared_unknown(self):
        intake = {"requirements": {"excluded": ["gambling"]}}
        rule = {
            "id": "excluded",
            "operator": "product_not_in_requirement_list",
            "requirement_path": "requirements.excluded",
            "product_path": "firmographics.industry",
            "missing_product_message": "Industry is not recorded",
        }
        for product in ({"firmographics": {}}, {"firmographics": {"industry": None}}):
            self.assertEqual(evaluate_rule(intake, product, rule).status, "failed")
            declared = evaluate_rule(intake, product, {**rule, "on_missing_product": "unknown"})
            self.assertEqual(declared.status, "unknown")
            self.assertEqual(declared.message, "Industry is not recorded")


if __name__ == "__main__":
    unittest.main()
