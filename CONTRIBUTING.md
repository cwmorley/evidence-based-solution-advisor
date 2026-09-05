# Contributing

Contributions are welcome when they improve the transparency, correctness, or portability of the decision method.

## Good contributions

- A reproducible bug case
- A clearer failure explanation
- A new deterministic operator with tests
- Better handling of missing or conflicting evidence
- A fully synthetic vertical example with domain-reviewed constraints
- Accessibility or usability improvements to generated reports
- Documentation that makes the method easier to evaluate honestly

## Before opening a pull request

1. Keep customer, employer, vendor-confidential, and proprietary catalog data out of the repository.
2. Clearly label fictional data as synthetic.
3. Add or update tests for behavior changes.
4. Explain whether the change affects facts, hard constraints, scoring, or presentation.
5. Do not convert uncertain information into a hard-coded fact.
6. Run:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Design principle

A recommendation that cannot explain its facts, constraints, tradeoffs, uncertainty, and decision authority is not ready to automate.
