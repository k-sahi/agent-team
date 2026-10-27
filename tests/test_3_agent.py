"""Stage 3 checkpoint: the agent loop.

These tests swap the real model for a tiny fake one so we control every reply.
Run just this stage with:  python -m unittest tests.test_3_agent -v
"""
import tempfile
import unittest
from unittest import mock

import agent as agent_module
from agent import Agent
from models import Reply, ToolCall
from tools import Workspace


def scripted(*replies):
    """A fake chat() that returns the given replies in order."""
    it = iter(replies)
    return lambda model, messages, tools: next(it)


class TestAgentLoop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.events = []
        self.agent = Agent("builder", "builder", "fake/model", "You build things.",
                           ["read_file", "write_file"], Workspace(self.tmp.name),
                           emit=lambda *e: self.events.append(e), max_steps=5)

    def tearDown(self):
        self.tmp.cleanup()

    def test_runs_tools_then_returns_finish_arguments(self):
        fake = scripted(
            Reply("", [ToolCall("1", "write_file", {"path": "x.txt", "content": "hi"})], cost=0.01),
            Reply("", [ToolCall("2", "finish", {"summary": "done"})], cost=0.02))
        with mock.patch.object(agent_module, "chat", fake):
            result = self.agent.run("make x.txt")
        self.assertEqual(result, {"summary": "done"})
        self.assertEqual(self.agent.workspace.read_file("t", "x.txt"), "hi")
        self.assertAlmostEqual(self.agent.cost, 0.03)

    def test_every_tool_call_gets_a_tool_reply(self):
        fake = scripted(Reply("", [ToolCall("1", "write_file", {"path": "a", "content": ""}),
                                   ToolCall("2", "finish", {"summary": "ok"})]))
        with mock.patch.object(agent_module, "chat", fake):
            self.agent.run("go")
        tool_ids = [m["tool_call_id"] for m in self.agent.messages if m["role"] == "tool"]
        self.assertEqual(tool_ids, ["1", "2"])

    def test_plain_text_reply_gets_a_nudge(self):
        fake = scripted(Reply("I think I'm done!"),
                        Reply("", [ToolCall("1", "finish", {"summary": "ok"})]))
        with mock.patch.object(agent_module, "chat", fake):
            self.agent.run("go")
        users = [m["content"] for m in self.agent.messages if m["role"] == "user"]
        self.assertEqual(users[0], "go")
        self.assertIn("Call finish", users[1])

    def test_stops_at_the_step_limit(self):
        loop_forever = lambda *a: Reply("", [ToolCall("1", "read_file", {"path": "nope"})])
        with mock.patch.object(agent_module, "chat", loop_forever):
            result = self.agent.run("go")
        self.assertEqual(result, {"error": "step limit"})

    def test_model_errors_are_reported_not_raised(self):
        def broken(*a):
            raise ConnectionError("no internet")
        with mock.patch.object(agent_module, "chat", broken):
            result = self.agent.run("go")
        self.assertIn("no internet", result["error"])

    def test_history_is_kept_between_runs(self):
        fake = scripted(Reply("", [ToolCall("1", "finish", {"summary": "a"})]),
                        Reply("", [ToolCall("2", "finish", {"summary": "b"})]))
        with mock.patch.object(agent_module, "chat", fake):
            self.agent.run("first")
            self.agent.run("second")
        users = [m["content"] for m in self.agent.messages if m["role"] == "user"]
        self.assertEqual(users, ["first", "second"])


if __name__ == "__main__":
    unittest.main()