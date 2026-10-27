"""Stage 4 checkpoint: the team (builder -> reviewer rounds).

Run just this stage with:  python -m unittest tests.test_4_team -v
"""
import copy
import tempfile
import unittest
from unittest import mock

import models
from team import Team, load_config

MOCK = load_config("team.mock.toml")


class TestTeam(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.events = []

    def tearDown(self):
        self.tmp.cleanup()

    def make_team(self, config=MOCK):
        return Team(copy.deepcopy(config), self.tmp.name, lambda *e: self.events.append(e))

    def rounds(self):
        return [text for who, kind, text in self.events if kind == "round"]

    def test_approved_in_the_first_round(self):
        self.assertTrue(self.make_team().run("write hello"))
        self.assertEqual(len(self.rounds()), 1)

    def test_rejection_sends_feedback_back_to_the_builder(self):
        verdicts = iter(["changes", "approve"])
        real_mock = models._mock

        def reviewer_rejects_once(model, messages):
            reply = real_mock(model, messages)
            call = reply.tool_calls[0]
            if model == "mock/reviewer" and call.name == "finish":
                call.args = {"verdict": next(verdicts), "feedback": "add a docstring"}
            return reply

        with mock.patch.object(models, "_mock", reviewer_rejects_once):
            team = self.make_team()
            self.assertTrue(team.run("write hello"))
        self.assertEqual(len(self.rounds()), 2)
        builder_inbox = [m["content"] for m in team.builder.messages if m["role"] == "user"]
        self.assertIn("add a docstring", builder_inbox[-1])

    def test_gives_up_after_max_rounds(self):
        real_mock = models._mock

        def never_happy(model, messages):
            reply = real_mock(model, messages)
            if model == "mock/reviewer" and reply.tool_calls[0].name == "finish":
                reply.tool_calls[0].args = {"verdict": "changes", "feedback": "no"}
            return reply

        with mock.patch.object(models, "_mock", never_happy):
            self.assertFalse(self.make_team().run("write hello"))
        self.assertEqual(len(self.rounds()), MOCK["settings"]["max_rounds"])

    def test_stops_when_over_budget(self):
        config = copy.deepcopy(MOCK)
        config["settings"]["budget_usd"] = 0.0
        team = self.make_team(config)
        team.builder.cost = 0.01  # pretend we already spent a cent
        self.assertFalse(team.run("write hello"))
        self.assertIn("budget", self.events[-1][2])

    def test_needs_exactly_one_builder_and_one_reviewer(self):
        config = copy.deepcopy(MOCK)
        config["members"]["reviewer"]["kind"] = "builder"
        with self.assertRaises(ValueError):
            self.make_team(config)


if __name__ == "__main__":
    unittest.main()