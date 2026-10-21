import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import foundry_agent
from foundry_agent import FoundryMathAgent, build_definition, validate_definition
from math_tools import FALLBACK


def response(*items, status="completed"):
    return SimpleNamespace(id="resp_test", status=status, output=list(items), output_text="Untrusted text")


def call(name="add", arguments='{"left":2,"right":5}'):
    return SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id="call_test")


class FoundryAgentTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.agent = FoundryMathAgent(self.client, "1")

    def test_tool_result_is_authoritative(self):
        self.client.responses.create.side_effect = [response(call()), response(SimpleNamespace(type="message"))]
        self.assertEqual(self.agent.solve("what is 2 plus 5"), "7")
        first, second = self.client.responses.create.call_args_list
        self.assertEqual(first.kwargs["tool_choice"], "required")
        self.assertFalse(first.kwargs["parallel_tool_calls"])
        self.assertEqual(first.kwargs["extra_body"]["agent_reference"]["version"], "1")
        self.assertEqual(second.kwargs["tool_choice"], "none")
        self.assertEqual(second.kwargs["previous_response_id"], "resp_test")
        self.assertEqual(second.kwargs["input"][0]["call_id"], "call_test")
        self.assertEqual(second.kwargs["input"][0]["output"], '{"answer": "7"}')

    def test_no_tool_multiple_tools_or_search_fail_closed(self):
        for result in [response(SimpleNamespace(type="message")), response(call(), call()), response(call(), SimpleNamespace(type="web_search_call")), response(call(), status="incomplete")]:
            with self.subTest(result=result):
                self.client.responses.create.reset_mock(side_effect=True)
                self.client.responses.create.return_value = result
                with patch.object(foundry_agent, "reject_request", return_value=FALLBACK) as reject:
                    self.assertEqual(self.agent.solve("2+5"), FALLBACK)
                    reject.assert_called_once()
                self.client.responses.create.assert_called_once()

    def test_reject_tool_for_unsupported_input(self):
        self.client.responses.create.side_effect = [response(call("reject_request", "{}")), response()]
        self.assertEqual(self.agent.solve("search the web"), FALLBACK)

    def test_fabricated_arithmetic_for_unsupported_input_is_rejected(self):
        self.client.responses.create.side_effect = [response(call()), response()]
        self.assertEqual(self.agent.solve("tell a joke and compute 2+5"), FALLBACK)

    def test_model_cannot_call_more_tools_after_result(self):
        self.client.responses.create.side_effect = [response(call()), response(call())]
        self.assertEqual(self.agent.solve("2+5"), FALLBACK)

    def test_empty_or_oversized_input_uses_local_rejection_tool(self):
        for prompt in ["", " " * 501]:
            self.assertEqual(self.agent.solve(prompt), FALLBACK)
        self.client.responses.create.assert_not_called()

    def test_definition_contains_only_allowed_function_tools(self):
        definition = build_definition("gpt-5.4-nano")
        validate_definition(definition, "gpt-5.4-nano")
        payload = definition.as_dict()
        self.assertEqual(payload["model"], "gpt-5.4-nano")
        self.assertNotIn("tool_choice", payload)
        self.assertEqual({tool["name"] for tool in payload["tools"]}, {"add", "subtract", "multiply", "divide", "reject_request"})
        self.assertTrue(all(tool["type"] == "function" and tool["strict"] for tool in payload["tools"]))

    def test_fixed_remote_tool_choice_requires_redeployment(self):
        for choice in ["required", "none", "auto"]:
            with self.subTest(choice=choice):
                definition = build_definition("gpt-5.4-nano")
                definition.tool_choice = choice
                with self.assertRaisesRegex(ValueError, "deploy a new version"):
                    validate_definition(definition, "gpt-5.4-nano")

    def test_changed_remote_definition_is_rejected(self):
        definition = build_definition("gpt-5.4-nano")
        definition.instructions = "Use web search"
        with self.assertRaises(ValueError):
            validate_definition(definition, "gpt-5.4-nano")


if __name__ == "__main__":
    unittest.main()