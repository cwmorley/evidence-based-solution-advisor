from __future__ import annotations

import io
import os
import re
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from solution_advisor.cli import main  # noqa: E402


COMMAND = "solution-advisor"
PATH_OPTIONS = ("--json-out", "--markdown-out")


def readme_commands() -> list[list[str]]:
    """Every `solution-advisor ...` command shown in a README code block."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    commands = []
    for block in re.findall(r"```[a-z]*\n(.*?)```", readme, flags=re.DOTALL):
        # PowerShell continues a line with a trailing backtick.
        joined = re.sub(r"`\s*\n\s*", " ", block)
        for line in joined.splitlines():
            line = line.strip()
            if line.startswith("python -m solution_advisor "):
                line = COMMAND + line[len("python -m solution_advisor"):]
            if line.startswith(COMMAND + " "):
                commands.append(shlex.split(line)[1:])
    return commands


class ReadmeCommandTests(unittest.TestCase):
    def test_readme_shows_commands(self):
        subcommands = {command[0] for command in readme_commands()}
        self.assertLessEqual({"recommend", "score-diagnostics"}, subcommands)

    def test_every_readme_command_runs_against_the_examples(self):
        # README commands use paths relative to the repository root.
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(ROOT)
        with tempfile.TemporaryDirectory() as folder:
            for command in readme_commands():
                with self.subTest(command=" ".join(command)):
                    # Keep documented output files out of the working tree.
                    args = [
                        str(Path(folder) / Path(token).name) if index and command[index - 1] in PATH_OPTIONS else token
                        for index, token in enumerate(command)
                    ]
                    output, errors = io.StringIO(), io.StringIO()
                    with redirect_stdout(output), redirect_stderr(errors):
                        code = main(args)
                    self.assertEqual(code, 0, errors.getvalue())
                    self.assertTrue(output.getvalue().strip())
                    for index, token in enumerate(args):
                        if index and args[index - 1] in PATH_OPTIONS:
                            self.assertGreater(Path(token).stat().st_size, 0)

    def test_every_readme_path_argument_exists(self):
        for command in readme_commands():
            inputs = [token for token in command[1:] if token.endswith(".json") and not token.startswith("outputs/")]
            self.assertTrue(inputs, command)
            for token in inputs:
                self.assertTrue((ROOT / token).is_file(), token)


if __name__ == "__main__":
    unittest.main()
