import unittest

import ast

from parser.ast_parser import extract_functions, get_expression_name


class ExtractFunctionsTests(unittest.TestCase):
    def test_extracts_sync_and_async_functions_with_lines(self):
        source = "def first():\n    return 1\n\nasync def second():\n    return 2\n"

        functions = extract_functions(source)

        self.assertEqual([item["name"] for item in functions], ["first", "second"])
        self.assertEqual(functions[0]["start_line"], 1)
        self.assertEqual(functions[0]["end_line"], 2)

    def test_empty_source_has_no_functions(self):
        self.assertEqual(extract_functions(""), [])

    def test_invalid_source_raises_syntax_error(self):
        with self.assertRaises(SyntaxError):
            extract_functions("def broken(")

    def test_expression_name_supports_dotted_attributes(self):
        expression = ast.parse("client.chat.create()", mode="eval").body

        self.assertEqual(get_expression_name(expression.func), "client.chat.create")


if __name__ == "__main__":
    unittest.main()
