from __future__ import annotations

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.account_scoring import (  # noqa: E402
    grade_for,
    load_account_store,
    render_account_report,
    score_account,
    score_accounts,
    validate_profile,
)
from solution_advisor.cli import main  # noqa: E402
from solution_advisor.io import load_json  # noqa: E402
from solution_advisor.scoring import ScoringProfileError  # noqa: E402


KNOWLEDGE = ROOT / "knowledge" / "account-scoring"
ICPS = ROOT / "examples" / "icps"


class AccountScoringTests(unittest.TestCase):
    def setUp(self):
        self.icp = load_json(ICPS / "new-logo-revops.json")
        self.store = load_account_store(KNOWLEDGE)
        self.profile = self.store["scoring"]
        self.result = score_accounts(self.icp, KNOWLEDGE)
        self.scored = {item["account_id"]: item for item in self.result["scored_accounts"]}
        self.rejected = {item["account_id"]: item for item in self.result["disqualified_accounts"]}

    def account(self, account_id: str) -> dict:
        return copy.deepcopy(next(a for a in self.store["accounts"] if a["account_id"] == account_id))

    def rescore(self, account: dict, icp: dict | None = None, profile: dict | None = None) -> dict:
        return score_account(icp or self.icp, account, self.store["constraints"], profile or self.profile)

    def test_every_record_is_labelled_synthetic(self):
        self.assertEqual(len(self.store["accounts"]), 12)
        for account in self.store["accounts"]:
            self.assertIs(account["synthetic"], True)
            self.assertIn("(fictional)", account["name"])
        self.assertIs(self.profile["synthetic"], True)
        self.assertIn("fictional", self.result["synthetic_data_notice"])
        self.assertEqual(self.result["crm_write_status"], "not_written")
        self.assertEqual(self.result["decision_authority"], "human_review_required")

    def test_each_hard_disqualifier_rejects_with_its_reason_and_no_score(self):
        expected = {
            "acct-005-lucky-reel-gaming": "Industry gambling is excluded by the ICP",
            "acct-006-tinyseed-labs": "Employee band 11-50 is not a company size this ICP sells to",
            "acct-007-quillstream-software": "Existing customer; out of scope for a new-logo motion",
        }
        self.assertEqual(set(self.rejected), set(expected))
        for account_id, reason in expected.items():
            item = self.rejected[account_id]
            self.assertEqual(item["disqualification_reasons"], [reason])
            self.assertIsNone(item["score"])
            self.assertIsNone(item["grade"])
            self.assertNotIn("contributions", item)

    def test_strong_signals_cannot_rescue_a_disqualified_account(self):
        account = self.account("acct-001-brightpath-analytics")
        self.assertEqual(self.rescore(account)["grade"], "A")
        account["firmographics"]["industry"] = "gambling"
        self.assertEqual(self.rescore(account)["status"], "disqualified")

    def test_new_logo_rule_applies_only_to_the_new_logo_motion(self):
        expansion = score_accounts(load_json(ICPS / "expansion-revops.json"), KNOWLEDGE)
        scored = {item["account_id"] for item in expansion["scored_accounts"]}
        self.assertIn("acct-007-quillstream-software", scored)
        self.assertNotIn("acct-005-lucky-reel-gaming", scored)

    def test_icp_that_matches_nothing_reports_no_qualified_account(self):
        result = score_accounts(load_json(ICPS / "enterprise-only-no-match.json"), KNOWLEDGE)
        self.assertEqual(result["status"], "no_qualified_account")
        self.assertEqual(result["scored_accounts"], [])
        self.assertEqual(len(result["disqualified_accounts"]), 12)
        self.assertIn("No account passed the hard disqualifiers.", render_account_report(result))

    def test_contributions_sum_to_the_score_for_every_scored_account(self):
        self.assertEqual(len(self.scored), 9)
        for item in self.scored.values():
            parts = item["contributions"]
            self.assertEqual(set(part["criterion"] for part in parts), set(self.profile["weights"]))
            self.assertEqual(item["score"], round(sum(part["contribution"] for part in parts), 2))
            for part in parts:
                self.assertGreaterEqual(part["contribution"], 0)
                self.assertLessEqual(part["contribution"], part["max_points"])

    def test_weights_are_documented_and_sum_to_one(self):
        self.assertAlmostEqual(sum(self.profile["weights"].values()), 1)
        for criterion in self.profile["criteria"]:
            self.assertTrue(criterion["rationale"].strip(), criterion["id"])
        for rule in self.store["constraints"]:
            self.assertTrue(rule["rationale"].strip(), rule["id"])

    def test_changing_a_weight_in_the_rules_changes_the_contribution(self):
        account = self.account("acct-001-brightpath-analytics")
        profile = copy.deepcopy(self.profile)
        profile["weights"]["industry_fit"] = 0.05
        profile["weights"]["open_opportunity"] = 0.15
        validate_profile(profile)
        parts = {part["criterion"]: part for part in self.rescore(account, profile=profile)["contributions"]}
        self.assertEqual(parts["industry_fit"]["contribution"], 5.0)
        self.assertEqual(self.rescore(account, profile=profile)["score"], 85.0)

    def test_invalid_profiles_raise_the_shared_named_error(self):
        for mutate in (
            lambda p: p["weights"].update(industry_fit=0.5),
            lambda p: p["weights"].pop("region_fit"),
            lambda p: p["grade_thresholds"].reverse(),
            lambda p: p["grade_thresholds"][-1].update(min_score=10),
        ):
            profile = copy.deepcopy(self.profile)
            mutate(profile)
            with self.assertRaises(ScoringProfileError):
                validate_profile(profile)
        profile = copy.deepcopy(self.profile)
        profile["criteria"][0]["scores"]["b2b_saas"] = 1.5
        with self.assertRaises(ScoringProfileError):
            self.rescore(self.account("acct-001-brightpath-analytics"), profile=profile)

    def test_grade_thresholds_at_and_around_each_boundary(self):
        thresholds = self.profile["grade_thresholds"]
        cases = {100: "A", 75: "A", 74.99: "B", 55: "B", 54.99: "C", 35: "C", 34.99: "D", 0: "D"}
        for score, grade in cases.items():
            with self.subTest(score=score):
                self.assertEqual(grade_for(score, thresholds), grade)
        with self.assertRaises(ScoringProfileError):
            grade_for(-1, thresholds)
        for item in self.scored.values():
            self.assertEqual(item["grade"], grade_for(item["score"], thresholds))
        self.assertEqual(self.scored["acct-001-brightpath-analytics"]["grade"], "A")
        self.assertEqual(self.scored["acct-012-pinecrest-staffing"]["grade"], "C")
        self.assertEqual(self.scored["acct-003-cobalt-forge-manufacturing"]["grade"], "D")

    def test_unknown_criteria_are_reported_and_lower_confidence(self):
        item = self.scored["acct-008-meridian-loop"]
        missing = {entry["field"] for entry in item["missing_data"]}
        self.assertEqual(missing, {"firmographics.tech_stack", "firmographics.arr_band", "signals.recent_funding"})
        for part in item["contributions"]:
            if part["path"] in missing:
                self.assertEqual((part["status"], part["raw_score"], part["contribution"]), ("missing", None, 0.0))
        self.assertTrue(item["provisional"])
        self.assertEqual(item["confidence"]["value"], 0.72)
        self.assertEqual(item["confidence"]["band"], "medium")
        self.assertEqual((item["score"], item["grade"]), (60.0, "B"))
        self.assertEqual((item["score_ceiling_if_resolved"], item["grade_ceiling_if_resolved"]), (88.0, "A"))
        complete = self.scored["acct-001-brightpath-analytics"]
        self.assertEqual((complete["confidence"]["value"], complete["provisional"], complete["missing_data"]), (1.0, False, []))

    def test_unknown_is_not_scored_as_a_known_negative_or_a_pass(self):
        account = self.account("acct-001-brightpath-analytics")
        account["signals"]["competitor_in_use"] = None
        unknown = self.rescore(account)
        part = next(p for p in unknown["contributions"] if p["criterion"] == "no_incumbent_competitor")
        self.assertEqual((part["status"], part["contribution"]), ("missing", 0.0))
        self.assertLess(unknown["confidence"]["value"], 1.0)
        self.assertNotIn("competitor", " ".join(unknown["reasons"]["negative"]))
        account["signals"]["competitor_in_use"] = False
        self.assertEqual(self.rescore(account)["score"], unknown["score"] + 3)

    def test_null_and_absent_values_are_handled_identically(self):
        for section, field in (("firmographics", "industry"), ("firmographics", "tech_stack"),
                               ("signals", "pricing_page_visits_30d"), ("signals", "existing_customer")):
            with self.subTest(field=field):
                as_null = self.account("acct-001-brightpath-analytics")
                absent = self.account("acct-001-brightpath-analytics")
                as_null[section][field] = None
                del absent[section][field]
                first, second = self.rescore(as_null), self.rescore(absent)
                self.assertEqual(first, second)
                self.assertEqual(first["status"], "scored")
                self.assertTrue(first["missing_data"])

    def test_unknown_disqualifier_fact_is_unresolved_not_passed_or_failed(self):
        item = self.scored["acct-009-driftwood-systems"]
        check = next(c for c in item["constraint_results"] if c["rule_id"] == "excluded_industry")
        self.assertEqual(check["status"], "unknown")
        kinds = {(entry["field"], entry["kind"]) for entry in item["missing_data"]}
        self.assertEqual(kinds, {("excluded_industry", "disqualifier_check"), ("firmographics.industry", "criterion")})
        self.assertEqual(item["confidence"]["band"], "low")
        self.assertTrue(item["provisional"])

    def test_missing_icp_requirement_is_reported_not_skipped(self):
        icp = copy.deepcopy(self.icp)
        icp["requirements"]["excluded_industries"] = None
        item = self.rescore(self.account("acct-005-lucky-reel-gaming"), icp=icp)
        self.assertEqual(item["status"], "scored")
        self.assertIn("The ICP does not state its excluded industries", [e["effect"] for e in item["missing_data"]])

    def test_empty_list_is_a_known_no_match_not_missing(self):
        item = self.scored["acct-012-pinecrest-staffing"]
        part = next(p for p in item["contributions"] if p["criterion"] == "tech_stack_fit")
        self.assertEqual((part["status"], part["raw_score"]), ("scored", 0.0))
        self.assertEqual(item["missing_data"], [])

    def test_ordering_is_deterministic_and_ties_break_by_account_id(self):
        order = [item["account_id"] for item in self.result["scored_accounts"]]
        scores = [item["score"] for item in self.result["scored_accounts"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        tied = ["acct-010-aster-ledger", "acct-011-zephyr-cloudworks"]
        self.assertEqual(self.scored[tied[0]]["score"], self.scored[tied[1]]["score"])
        self.assertNotEqual(self.scored[tied[0]]["contributions"], self.scored[tied[1]]["contributions"])
        self.assertEqual(order[order.index(tied[0]):order.index(tied[0]) + 2], tied)
        self.assertEqual(self.result, score_accounts(self.icp, KNOWLEDGE))
        self.assertEqual(sorted(self.rejected), [item["account_id"] for item in self.result["disqualified_accounts"]])

    def test_reasons_name_top_drivers_in_plain_language(self):
        reasons = self.scored["acct-002-ledgerline-financial"]["reasons"]
        self.assertEqual(reasons["positive"][0], "+15 of 15: Company size fit - 501-1000 employees")
        self.assertEqual(reasons["negative"][0], "-8 of 8: Recent funding - no funding in the last 12 months")
        self.assertLessEqual(len(reasons["positive"]), self.profile["reason_limit"])
        self.assertLessEqual(len(reasons["negative"]), self.profile["reason_limit"])

    def test_cli_report_shows_grades_and_exit_codes(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["score-accounts", str(ICPS / "new-logo-revops.json"), "--knowledge", str(KNOWLEDGE)])
        self.assertEqual(code, 0)
        self.assertIn("### A | 95.00 | Brightpath Analytics (fictional)", output.getvalue())
        self.assertIn("Nothing has been written to a live CRM", output.getvalue())
        with redirect_stdout(io.StringIO()):
            code = main(["score-accounts", str(ICPS / "enterprise-only-no-match.json"), "--knowledge", str(KNOWLEDGE)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
