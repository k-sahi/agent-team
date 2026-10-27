"""Stage 1 checkpoint: the model layer.

Run just this stage with:  python -m unittest tests.test_1_models -v
"""
import unittest

from models import Reply, ToolCall, chat, parse_text_tool_calls


class TestTextToolCalls(unittest.TestCase):
    """Local models sometimes type tool calls as JSON text. We turn those into real calls."""
    TOOLS = [{"type": "function", "function": {"name": n}} for n in ("run_command", "finish")]

    def test_finds_tool_calls_written_as_text(self):
        text = ('{"name": "run_command", "arguments": {"command": "python -m unittest test_prime.py"}}\n'
                '{"name": "finish", "arguments": {"summary": "done"}}')
        calls = parse_text_tool_calls(text, self.TOOLS)
        self.assertEqual([c.name for c in calls], ["run_command", "finish"])
        self.assertEqual(calls[0].args["command"], "python -m unittest test_prime.py")

    def test_handles_code_fences_and_string_arguments(self):
        text = 'Sure!\n```json\n{"name": "finish", "arguments": "{\\"summary\\": \\"ok\\"}"}\n```'
        calls = parse_text_tool_calls(text, self.TOOLS)
        self.assertEqual(calls[0].args, {"summary": "ok"})

    def test_ignores_json_that_is_not_a_known_tool(self):
        text = '{"name": "delete_everything", "arguments": {}} and {"a": 1}'
        self.assertEqual(parse_text_tool_calls(text, self.TOOLS), [])

    def test_ignores_plain_text(self):
        self.assertEqual(parse_text_tool_calls("I think I'm done!", self.TOOLS), [])