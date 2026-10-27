"""Stage 1 checkpoint: the model layer.

Run just this stage with:  python -m unittest tests.test_1_models -v
"""
import unittest

from models import Reply, ToolCall, chat


class TestMockModels(unittest.TestCase):
    def test_mock_builder_first_step_writes_a_file(self):
        msgs = [{"role": "system", "content": "x"}, {"role": "user", "content": "go"}]
        reply = chat("mock/builder", msgs, tools=[])
        self.assertIsInstance(reply, Reply)
        self.assertEqual(len(reply.tool_calls), 1)
        self.assertIsInstance(reply.tool_calls[0], ToolCall)
        self.assertEqual(reply.tool_calls[0].name, "write_file")

    def test_mock_counts_steps_since_last_user_message(self):
        msgs = [{"role": "user", "content": "go"},
                {"role": "assistant", "content": "did step 0"}]
        reply = chat("mock/builder", msgs, tools=[])
        self.assertEqual(reply.tool_calls[0].name, "finish")

    def test_mock_restarts_after_a_new_user_message(self):
        msgs = [{"role": "user", "content": "go"},
                {"role": "assistant", "content": "a"},
                {"role": "user", "content": "round 2"}]
        reply = chat("mock/builder", msgs, tools=[])
        self.assertEqual(reply.tool_calls[0].name, "write_file")

    def test_mock_reviewer_ends_with_an_approval(self):
        msgs = [{"role": "user", "content": "review"}] + [{"role": "assistant", "content": ""}] * 2
        reply = chat("mock/reviewer", msgs, tools=[])
        self.assertEqual(reply.tool_calls[0].name, "finish")
        self.assertEqual(reply.tool_calls[0].args["verdict"], "approve")

    def test_mock_models_are_free(self):
        reply = chat("mock/builder", [{"role": "user", "content": "go"}], tools=[])
        self.assertEqual(reply.cost, 0.0)


if __name__ == "__main__":
    unittest.main()