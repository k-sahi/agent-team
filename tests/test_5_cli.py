"""Stage 5 checkpoint: the whole program, run exactly as you would from the terminal.

Run just this stage with:  python -m unittest tests.test_5_cli -v
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestCommandLine(unittest.TestCase):
    def test_mock_team_builds_and_approves_hello_py(self):
        with tempfile.TemporaryDirectory() as out:
            run = subprocess.run(
                [sys.executable, "main.py", "write a hello world script",
                 "--config", "team.mock.toml", "--dir", out, "--plain"],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn("[team:done] approved", run.stdout)
            self.assertIn("Hello", (Path(out) / "hello.py").read_text())

    def test_help_works(self):
        run = subprocess.run([sys.executable, "main.py", "--help"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0)
        self.assertIn("--config", run.stdout)


if __name__ == "__main__":
    unittest.main()