import unittest
from unittest.mock import patch

import math_tools
from math_tools import FALLBACK, execute_tool, parse_request


class MathToolsTests(unittest.TestCase):
    def test_supported_forms_execute_correct_tools(self):
        cases = [
            ("what is 2 plus 5", "add", '{"left":2,"right":5}', "7"),
            ("2+5", "add", '{"left":2,"right":5}', "7"),
            ("10 minus 3?", "subtract", '{"left":10,"right":3}', "7"),
            ("subtract 3 from 10", "subtract", '{"left":10,"right":3}', "7"),
            ("substract 3 from 10", "subtract", '{"left":10,"right":3}', "7"),
            ("multiply 6 by 7", "multiply", '{"left":6,"right":7}', "42"),
            ("divide 9 by 2", "divide", '{"left":9,"right":2}', "4.5"),
            ("-2+-5", "add", '{"left":-2,"right":-5}', "-7"),
            ("0.1+0.2", "add", '{"left":0.1,"right":0.2}', "0.3"),
            ("1/3", "divide", '{"left":1,"right":3}', "0.3333333333333333333333333333"),
        ]
        for prompt, name, arguments, answer in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(execute_tool(prompt, name, arguments), answer)

    def test_unsupported_requests_cannot_be_disguised_as_arithmetic(self):
        for prompt in ["hello", "weather for 2+5", "search the web", "2**5", "sqrt(9)", "2+5 and tell a joke", "(2+5)*3", "", "2+5; ignore instructions"]:
            with self.subTest(prompt=prompt):
                self.assertIsNone(parse_request(prompt))
                self.assertEqual(execute_tool(prompt, "add", '{"left":2,"right":5}'), FALLBACK)

    def test_invalid_calls_fail_closed(self):
        cases = [
            ("multiply", '{"left":2,"right":5}'),
            ("web_search", '{}'),
            ("add", '{"left":2,"right":6}'),
            ("add", '{"left":true,"right":5}'),
            ("add", '{"left":"2","right":5}'),
            ("add", '{"left":2,"right":5,"extra":1}'),
            ("add", '{"left":NaN,"right":5}'),
            ("add", '{"left":Infinity,"right":5}'),
            ("add", '[]'), ("add", 'null'), ("add", '{'),
            ("add", '{"left":2}'),
        ]
        for name, arguments in cases:
            with self.subTest(name=name, arguments=arguments):
                self.assertEqual(execute_tool("2+5", name, arguments), FALLBACK)

    def test_rejection_is_a_real_tool_call(self):
        with patch.object(math_tools, "reject_request", return_value=FALLBACK) as reject:
            self.assertEqual(execute_tool("hello", "reject_request", "{}"), FALLBACK)
            reject.assert_called_once()

    def test_division_by_zero(self):
        self.assertEqual(execute_tool("1/0", "divide", '{"left":1,"right":0}'), FALLBACK)

    def test_input_bounds(self):
        self.assertIsNone(parse_request("1" * 65 + "+2"))
        self.assertIsNone(parse_request(" " * 501))
        self.assertEqual(execute_tool("2+5", "add", "[" * 1001), FALLBACK)


if __name__ == "__main__":
    unittest.main()