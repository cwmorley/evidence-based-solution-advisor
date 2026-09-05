from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_readme_explains_use_before_implementation(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        plain_language = readme.index("## What this is for")
        practical_applications = readme.index("## Practical applications")
        technical_detail = readme.index("## How it works")
        self.assertLess(plain_language, technical_detail)
        self.assertLess(practical_applications, technical_detail)
        self.assertIn("more defensible buying decision", readme)

    def test_architecture_leads_with_practical_benefit(self):
        architecture = (ROOT / "docs" / "ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        plain_language = architecture.index("## The plain-language version")
        technical_detail = architecture.index("## System components")
        self.assertLess(plain_language, technical_detail)
        self.assertIn("more defensible buying decision", architecture)
        self.assertIn("fewer avoidable deployment surprises", architecture)


if __name__ == "__main__":
    unittest.main()
