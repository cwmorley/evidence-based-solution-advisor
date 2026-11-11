"""Regression tests for defects found by an independent review on 2026-11-10.

Each test failed against the code as first written.
"""
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

from solution_advisor.account_scoring import (  # noqa: E402
    load_account_store,
    score_account,
    score_accounts,
    validate_profile,
)
from solution_advisor.crm_writeback import WritebackGuardError, build_batch_updates  # noqa: E402
from solution_advisor.io import AdvisorDataError, load_json  # noqa: E402


KNOWLEDGE = ROOT / "knowledge" / "account-scoring"
ICP = ROOT / "examples" / "icps" / "new-logo-revops.json"
SCORED_AT = "2026-11-10T00:00:00Z"
BEST = "acct-001-brightpath-analytics"


class ReviewFindingTests(unittest.TestCase):
    def setUp(self):
        self.icp = load_json(ICP)
        self.store = load_account_store(KNOWLEDGE)
        self.profile = self.store["scoring"]
        self.result = score_accounts(self.icp, KNOWLEDGE)

    def account(self, account_id: str) -> dict:
        return copy.deepcopy(next(a for a in self.store["accounts"] if a["account_id"] == account_id))

    def rescore(self, account: dict, profile: dict | None = None) -> dict:
        return score_account(self.icp, account, self.store["constraints"], profile or self.profile)

    def refused(self, result: dict, text: str):
        with self.assertRaises(WritebackGuardError) as caught:
            build_batch_updates(result, SCORED_AT)
        self.assertIn(text, str(caught.exception))

    # Finding 1 (medium): two accounts with the same HubSpot company ID are emitted as two inputs.
    def test_f1_guard_refuses_two_accounts_with_the_same_hubspot_company_id(self):
        result = copy.deepcopy(self.result)
        clone = copy.deepcopy(result["scored_accounts"][0])
        clone["account_id"] = "acct-013-brightpath-analytics-duplicate"
        result["scored_accounts"].append(clone)
        self.assertEqual(clone["hubspot_company_id"], result["scored_accounts"][0]["hubspot_company_id"])
        self.refused(result, "9000000001")

    # Finding 2 (medium): a record whose status says "scored" but which carries a failed hard
    # disqualifier is written to the CRM as scored.
    def test_f2_guard_refuses_a_scored_account_that_carries_a_failed_disqualifier(self):
        with self.subTest(case="disqualification_reasons present"):
            result = copy.deepcopy(self.result)
            result["scored_accounts"][0]["disqualification_reasons"] = ["Industry gambling is excluded by the ICP"]
            self.refused(result, "failed disqualifier")
        with self.subTest(case="constraint_results contains a failure"):
            result = copy.deepcopy(self.result)
            for check in result["scored_accounts"][0]["constraint_results"]:
                if check["rule_id"] == "excluded_industry":
                    check["status"] = "failed"
            self.refused(result, "failed disqualifier")

    # Finding 3 (medium): an empty string is treated as a known value. For lookups it scores at the
    # default and can disqualify; for tiers and booleans it aborts the whole scoring run.
    def test_f3_empty_string_is_unknown_like_null_not_a_known_value(self):
        cases = (
            ("firmographics", "employee_band"),
            ("firmographics", "industry"),
            ("signals", "pricing_page_visits_30d"),
            ("signals", "recent_funding"),
        )
        for section, field in cases:
            with self.subTest(field=field):
                blank, as_null = self.account(BEST), self.account(BEST)
                blank[section][field] = ""
                as_null[section][field] = None
                expected = self.rescore(as_null)
                actual = self.rescore(blank)  # raises ScoringProfileError today for tiers and booleans
                self.assertEqual(actual["status"], expected["status"])
                self.assertEqual(actual["score"], expected["score"])
                self.assertEqual(
                    sorted(entry["field"] for entry in actual["missing_data"]),
                    sorted(entry["field"] for entry in expected["missing_data"]),
                )

    # Finding 4 (low): confidence is never validated, so NaN, infinity, out-of-range and
    # wrong-typed values reach the payload (or crash outside the guard).
    def test_f4_guard_refuses_a_non_finite_or_out_of_range_confidence(self):
        for value in (float("nan"), float("inf"), -0.5, 1.5, "0.72", None, True):
            with self.subTest(value=value):
                result = copy.deepcopy(self.result)
                result["scored_accounts"][0]["confidence"]["value"] = value
                self.refused(result, "confidence")

    # Finding 5 (low): the guard trusts the record's own max_points, so a score above 100 passes.
    def test_f5_guard_refuses_a_score_above_one_hundred(self):
        result = copy.deepcopy(self.result)
        account = result["scored_accounts"][0]
        part = account["contributions"][0]
        part["max_points"], part["contribution"] = 200.0, 120.0
        account["score"] = round(sum(item["contribution"] for item in account["contributions"]), 2)
        self.assertEqual(account["score"], 200.0)
        self.refused(result, "outside 0..100")

    # Finding 6 (low): tier scoring takes the first tier in file order, so a profile whose tiers
    # are listed ascending silently under-scores.
    def test_f6_tier_lookup_does_not_depend_on_the_order_tiers_are_listed(self):
        profile = copy.deepcopy(self.profile)
        criterion = next(c for c in profile["criteria"] if c["id"] == "pricing_page_visits")
        criterion["tiers"].reverse()
        validate_profile(profile)
        parts = self.rescore(self.account(BEST), profile=profile)["contributions"]
        part = next(p for p in parts if p["criterion"] == "pricing_page_visits")
        self.assertEqual((part["raw_score"], part["contribution"]), (1.0, 12.0))

    # Finding 7 (low): an account file without a "status" key is silently dropped from the run.
    def test_f7_an_account_without_a_status_is_rejected_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "knowledge"
            shutil.copytree(KNOWLEDGE, root)
            path = root / "accounts" / f"{BEST}.json"
            account = json.loads(path.read_text(encoding="utf-8"))
            del account["status"]
            path.write_text(json.dumps(account), encoding="utf-8")
            with self.assertRaises(AdvisorDataError):
                score_accounts(self.icp, root)


if __name__ == "__main__":
    unittest.main()
