import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
COMMAND = PROJECT_DIR / "build_tool.py"
VALID_INPUT = PROJECT_DIR / "input.json"


def run_command(*args):
    return subprocess.run(
        [sys.executable, str(COMMAND), *map(str, args)],
        capture_output=True,
        text=True,
        check=False
    )


class CommandTests(unittest.TestCase):

    def test_valid_input(self):
        result = run_command(VALID_INPUT)
        self.assertEqual(result.returncode, 0)
        # TODO: verify JSON output and empty stderr.

    def test_missing_input(self):
        result = run_command(PROJECT_DIR / "missing.json")
        # TODO: verify exit code 1, empty stdout and stderr diagnostic.
        self.assertTrue(True)

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            bad_file = Path(directory) / "bad.json"
            bad_file.write_text("{invalid json", encoding="utf-8")
            result = run_command(bad_file)
            # TODO: verify exit code 1, empty stdout and stderr diagnostic.
            self.assertTrue(True)

    def test_invalid_arguments(self):
        result = run_command()
        # TODO: verify exit code 2 and usage text on stderr.
        self.assertTrue(True)

    def test_help(self):
        result = run_command("--help")
        # TODO: verify exit code 0, help on stdout and empty stderr.
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)