"""Stage 2 checkpoint: the tools and the project-folder fence.

Run just this stage with:  python -m unittest tests.test_2_tools -v
"""
import tempfile
import unittest

import tools
from tools import FINISH_SCHEMAS, TOOL_SCHEMAS, Workspace


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Workspace(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_then_read(self):
        self.ws.call("me", "write_file", {"path": "src/a.txt", "content": "hi"})
        self.assertEqual(self.ws.call("me", "read_file", {"path": "src/a.txt"}), "hi")

    def test_list_files_is_recursive_and_skips_junk(self):
        self.ws.call("me", "write_file", {"path": "a.py", "content": ""})
        self.ws.call("me", "write_file", {"path": "pkg/b.py", "content": ""})
        self.ws.call("me", "write_file", {"path": "__pycache__/c.pyc", "content": ""})
        listing = self.ws.call("me", "list_files", {}).splitlines()
        self.assertIn("a.py", listing)
        self.assertIn("pkg/b.py", listing)
        self.assertNotIn("__pycache__/c.pyc", listing)

    def test_cannot_escape_the_project_folder(self):
        for bad in ["../evil.txt", "/etc/passwd", "a/../../evil.txt"]:
            result = self.ws.call("me", "write_file", {"path": bad, "content": "x"})
            self.assertIn("escapes the project folder", result, bad)

    def test_run_command_reports_exit_code_and_output(self):
        result = self.ws.call("me", "run_command", {"command": "echo hello"})
        self.assertTrue(result.startswith("exit code 0"))
        self.assertIn("hello", result)

    def test_declined_commands_do_not_run(self):
        ws = Workspace(self.tmp.name, approve_command=lambda agent, cmd: False)
        ws.call("me", "run_command", {"command": "echo hi > should_not_exist"})
        self.assertNotIn("should_not_exist", ws.call("me", "list_files", {}))

    def test_errors_come_back_as_text_not_crashes(self):
        result = self.ws.call("me", "read_file", {"path": "missing.txt"})
        self.assertTrue(result.startswith("error: FileNotFoundError"))

    def test_unknown_tools_are_refused(self):
        self.assertEqual(self.ws.call("me", "delete_everything", {}), "unknown tool: delete_everything")

    def test_long_output_is_truncated(self):
        self.ws.call("me", "write_file", {"path": "big.txt", "content": "x" * (tools.MAX_OUTPUT + 500)})
        result = self.ws.call("me", "read_file", {"path": "big.txt"})
        self.assertIn("truncated", result)
        self.assertLess(len(result), tools.MAX_OUTPUT + 100)


class TestSchemas(unittest.TestCase):
    def test_every_tool_has_a_matching_method(self):
        for name in TOOL_SCHEMAS:
            self.assertTrue(hasattr(Workspace, name), name)

    def test_each_role_has_its_own_finish(self):
        self.assertIn("summary", FINISH_SCHEMAS["builder"]["function"]["parameters"]["properties"])
        self.assertIn("verdict", FINISH_SCHEMAS["reviewer"]["function"]["parameters"]["properties"])


if __name__ == "__main__":
    unittest.main()