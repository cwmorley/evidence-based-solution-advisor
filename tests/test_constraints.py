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


if __name__ == "__main__":
    unittest.main()
