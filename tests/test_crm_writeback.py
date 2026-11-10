from __future__ import annotations

import ast
import copy
import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor import crm_writeback  # noqa: E402
from solution_advisor.account_scoring import score_accounts  # noqa: E402
from solution_advisor.cli import main  # noqa: E402
from solution_advisor.crm_writeback import (  # noqa: E402
    REQUIRED_PROPERTIES,
    WritebackGuardError,
    build_batch_updates,
    check_writeback,
)
from solution_advisor.io import load_json  # noqa: E402


KNOWLEDGE = ROOT / "knowledge" / "account-scoring"
ICP = ROOT / "examples" / "icps" / "new-logo-revops.json"
SCORED_AT = "2026-11-10T00:00:00Z"


class CrmWritebackTests(unittest.TestCase):
    def setUp(self):
        self.result = score_accounts(load_json(ICP), KNOWLEDGE)

    def refused(self, result: dict, text: str):
        with self.assertRaises(WritebackGuardError) as caught:
            build_batch_updates(result, SCORED_AT)
        self.assertIn(text, str(caught.exception))

    def test_payload_matches_the_batch_update_request_shape(self):
        requests = build_batch_updates(self.result, SCORED_AT)
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual((request["method"], request["path"]), ("POST", "/crm/v3/objects/companies/batch/update"))
        self.assertEqual((request["dry_run"], request["sent"]), (True, False))
        self.assertEqual(set(request["body"]), {"inputs"})
        inputs = request["body"]["inputs"]
        self.assertEqual(len(inputs), 12)
        self.assertEqual([item["id"] for item in inputs], sorted(item["id"] for item in inputs))
        for item in inputs:
            self.assertEqual(set(item), {"id", "properties"})
            self.assertIsInstance(item["id"], str)
            self.assertEqual(set(item["properties"]), set(REQUIRED_PROPERTIES))
            for value in item["properties"].values():
                self.assertIsInstance(value, str)
            self.assertEqual(item["properties"]["icp_scored_at"], SCORED_AT)
            self.assertEqual(item["properties"]["icp_rules_version"], self.result["rules_version"])
        json.dumps(requests)

    def test_scored_and_disqualified_property_values(self):
        inputs = {item["id"]: item["properties"] for item in build_batch_updates(self.result, SCORED_AT)[0]["body"]["inputs"]}
        best = inputs["9000000001"]
        self.assertEqual((best["icp_status"], best["icp_grade"], best["icp_score"]), ("scored", "A", "95.00"))
        self.assertIn("+15 of 15: Industry fit - industry is b2b_saas", best["icp_reasons"].splitlines())
        rejected = inputs["9000000005"]
        self.assertEqual(rejected["icp_status"], "disqualified")
        self.assertEqual((rejected["icp_grade"], rejected["icp_score"]), ("", ""))
        self.assertEqual(rejected["icp_reasons"], "Disqualified: Industry gambling is excluded by the ICP")
        partial = inputs["9000000008"]
        self.assertEqual(partial["icp_confidence"], "0.72")
        self.assertEqual(len(partial["icp_missing_data"].splitlines()), 3)

    def test_guard_refuses_when_contributions_do_not_sum_to_the_score(self):
        result = copy.deepcopy(self.result)
        result["scored_accounts"][0]["score"] = 96.0
        self.refused(result, "contributions sum to 95.0 but the score is 96.0")
        result = copy.deepcopy(self.result)
        result["scored_accounts"][0]["contributions"][0]["contribution"] = 14.0
        self.refused(result, "contributions sum to 94.0 but the score is 95.0")
        result = copy.deepcopy(self.result)
        result["scored_accounts"][0]["contributions"][0]["contribution"] = 16.0
        self.refused(result, "industry_fit contribution is outside 0..15")

    def test_guard_refuses_when_the_rules_version_is_missing(self):
        for value in (None, "", "   "):
            result = copy.deepcopy(self.result)
            result["rules_version"] = value
            self.refused(result, "rules version is missing")
        result = copy.deepcopy(self.result)
        del result["rules_version"]
        self.refused(result, "rules version is missing")
        icp = load_json(ICP)
        del icp["icp_version"]
        self.assertIsNone(score_accounts(icp, KNOWLEDGE)["rules_version"])

    def test_guard_refuses_when_the_grade_does_not_match_the_thresholds(self):
        result = copy.deepcopy(self.result)
        result["scored_accounts"][1]["grade"] = "A"
        self.refused(result, "grade 'A' does not match the thresholds (score 63.2 is grade B)")
        result = copy.deepcopy(self.result)
        result["grade_thresholds"][0]["min_score"] = 96
        self.refused(result, "grade 'A' does not match the thresholds (score 95.0 is grade B)")

    def test_guard_refuses_missing_identity_and_inconsistent_disqualification(self):
        result = copy.deepcopy(self.result)
        result["scored_accounts"][0]["hubspot_company_id"] = None
        self.refused(result, "HubSpot company ID is missing")
        result = copy.deepcopy(self.result)
        result["disqualified_accounts"][0]["disqualification_reasons"] = []
        self.refused(result, "disqualified without a reason")
        result = copy.deepcopy(self.result)
        result["disqualified_accounts"][0]["score"] = 90.0
        self.refused(result, "must not carry a score or grade")

    def test_one_bad_account_stops_the_whole_batch(self):
        result = copy.deepcopy(self.result)
        result["scored_accounts"][-1]["grade"] = "A"
        self.refused(result, "acct-003-cobalt-forge-manufacturing")
        for account in self.result["scored_accounts"] + self.result["disqualified_accounts"]:
            check_writeback(account, self.result["rules_version"], self.result["grade_thresholds"])

    def test_batches_hold_at_most_one_hundred_inputs(self):
        result = copy.deepcopy(self.result)
        template = result["scored_accounts"][0]
        result["scored_accounts"] = [
            {**template, "account_id": f"acct-{index:04d}", "hubspot_company_id": str(index)} for index in range(205)
        ]
        result["disqualified_accounts"] = []
        sizes = [len(request["body"]["inputs"]) for request in build_batch_updates(result, SCORED_AT)]
        self.assertEqual(sizes, [100, 100, 5])

    def test_timestamp_is_normalised_to_utc_or_refused(self):
        request = build_batch_updates(self.result, "2026-11-10T02:30:00+02:00")[0]
        self.assertEqual(request["body"]["inputs"][0]["properties"]["icp_scored_at"], "2026-11-10T00:30:00Z")
        for value in ("yesterday", "2026-11-10T00:00:00"):
            with self.assertRaises(WritebackGuardError):
                build_batch_updates(self.result, value)
        default = build_batch_updates(self.result)[0]["body"]["inputs"][0]["properties"]["icp_scored_at"]
        self.assertRegex(default, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_module_imports_no_network_client(self):
        tree = ast.parse(Path(crm_writeback.__file__).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported.add((node.module or "").split(".")[0])
        self.assertEqual(imported, {"__future__", "math", "datetime", "typing"})

    def test_cli_dry_run_prints_payloads_and_reports_guard_failures(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["score-accounts", str(ICP), "--knowledge", str(KNOWLEDGE), "--dry-run", "--scored-at", SCORED_AT])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue()), build_batch_updates(self.result, SCORED_AT))
        errors = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(errors):
            code = main(["score-accounts", str(ICP), "--knowledge", str(KNOWLEDGE), "--dry-run", "--scored-at", "nope"])
        self.assertEqual(code, 1)
        self.assertIn("scored-at is not an ISO 8601 timestamp", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
