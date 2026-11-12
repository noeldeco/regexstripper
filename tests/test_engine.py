"""
Unit tests for RegexEngine
"""

import unittest
import re
from src.core.regex_engine import RegexEngine


class TestRegexEngine(unittest.TestCase):

    def test_validate_pattern_valid(self):
        is_valid, err, compiled = RegexEngine.validate_pattern(r"\d+")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")
        self.assertIsNotNone(compiled)

    def test_validate_pattern_invalid(self):
        is_valid, err, compiled = RegexEngine.validate_pattern(r"[\d+")
        self.assertFalse(is_valid)
        self.assertNotEqual(err, "")
        self.assertIsNone(compiled)

    def test_validate_pattern_empty(self):
        is_valid, err, compiled = RegexEngine.validate_pattern("")
        self.assertTrue(is_valid)
        self.assertEqual(err, "")
        self.assertIsNone(compiled)

    def test_find_match_spans(self):
        text = "Order #123 and Order #456 completed."
        spans = RegexEngine.find_match_spans(text, r"#\d+")
        self.assertEqual(len(spans), 2)
        self.assertEqual(text[spans[0][0]:spans[0][1]], "#123")
        self.assertEqual(text[spans[1][0]:spans[1][1]], "#456")

    def test_find_match_spans_case_insensitive(self):
        text = "Hello hello HELLO"
        spans_no_flag = RegexEngine.find_match_spans(text, r"hello")
        self.assertEqual(len(spans_no_flag), 1)

        spans_flag = RegexEngine.find_match_spans(text, r"hello", flags=re.IGNORECASE)
        self.assertEqual(len(spans_flag), 3)

    def test_find_inverted_spans_middle(self):
        text = "abc123def456ghi"
        # Matches: [123 at (3, 6), 456 at (9, 12)]
        inverted = RegexEngine.find_inverted_spans(text, r"\d+")
        self.assertEqual(len(inverted), 3)
        self.assertEqual(text[inverted[0][0]:inverted[0][1]], "abc")
        self.assertEqual(text[inverted[1][0]:inverted[1][1]], "def")
        self.assertEqual(text[inverted[2][0]:inverted[2][1]], "ghi")

    def test_find_inverted_spans_edges(self):
        text = "123middle456"
        inverted = RegexEngine.find_inverted_spans(text, r"\d+")
        self.assertEqual(len(inverted), 1)
        self.assertEqual(text[inverted[0][0]:inverted[0][1]], "middle")

    def test_find_inverted_spans_no_matches(self):
        text = "pure letters"
        inverted = RegexEngine.find_inverted_spans(text, r"\d+")
        self.assertEqual(len(inverted), 1)
        self.assertEqual(inverted[0], (0, len(text)))

    def test_find_inverted_spans_empty_text(self):
        inverted = RegexEngine.find_inverted_spans("", r"\d+")
        self.assertEqual(inverted, [])

    def test_strip_matches(self):
        text = "Keep this [DELETE] and this [DELETE]."
        result, count = RegexEngine.strip_matches(text, r"\[DELETE\]\s*")
        self.assertEqual(count, 2)
        self.assertEqual(result, "Keep this and this .")

    def test_strip_matches_empty_or_invalid(self):
        text = "Sample text"
        res, count = RegexEngine.strip_matches(text, "")
        self.assertEqual(res, text)
        self.assertEqual(count, 0)

        res2, count2 = RegexEngine.strip_matches(text, "[invalid")
        self.assertEqual(res2, text)
        self.assertEqual(count2, 0)

    def test_strip_non_matches(self):
        text = "Contact: test@example.com or admin@domain.org for info."
        pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
        result, count = RegexEngine.strip_non_matches(text, pattern, separator="\n")
        self.assertEqual(count, 2)
        self.assertEqual(result, "test@example.com\nadmin@domain.org")

    def test_strip_non_matches_multiline_flag(self):
        text = "apple\nbanana\napricot\nberry"
        # Match lines starting with 'a'
        pattern = r"^a\w+"
        spans_no_flag = RegexEngine.find_match_spans(text, pattern)
        self.assertEqual(len(spans_no_flag), 1)  # only 'apple' at start of string

        spans_multiline = RegexEngine.find_match_spans(text, pattern, flags=re.MULTILINE)
        self.assertEqual(len(spans_multiline), 2)  # 'apple' and 'apricot'

    def test_strip_non_matches_custom_delimiter_and_unique(self):
        text = "id: 10, id: 20, id: 10, id: 30"
        pattern = r"\d+"
        # Without unique:
        res, count = RegexEngine.strip_non_matches(text, pattern, separator=", ", unique=False)
        self.assertEqual(count, 4)
        self.assertEqual(res, "10, 20, 10, 30")

        # With unique:
        res_unique, count_unique = RegexEngine.strip_non_matches(text, pattern, separator=" | ", unique=True)
        self.assertEqual(count_unique, 3)
        self.assertEqual(res_unique, "10 | 20 | 30")

    def test_strip_non_matches_capture_group(self):
        text = "key1=val1; key2=val2"
        pattern = r"(\w+)=(\w+)"
        # Extract group 2 (only values)
        res, count = RegexEngine.strip_non_matches(text, pattern, separator=",", capture_group="2")
        self.assertEqual(count, 2)
        self.assertEqual(res, "val1,val2")

    def test_strip_non_matches_zero_matches(self):
        text = "No digits here"
        result, count = RegexEngine.strip_non_matches(text, r"\d+")
        self.assertEqual(count, 0)
        self.assertEqual(result, "")

    def test_replace_matches_literal(self):
        text = "Apple 100, Banana 200"
        result, count = RegexEngine.replace_matches(text, r"\d+", "999")
        self.assertEqual(count, 2)
        self.assertEqual(result, "Apple 999, Banana 999")

    def test_replace_matches_backreferences(self):
        text = "Name: Doe, John"
        pattern = r"(\w+),\s*(\w+)"
        result, count = RegexEngine.replace_matches(text, pattern, r"\2 \1")
        self.assertEqual(count, 1)
        self.assertEqual(result, "Name: John Doe")

    def test_replace_matches_zero_matches(self):
        text = "Hello world"
        result, count = RegexEngine.replace_matches(text, r"\d+", "xxx")
        self.assertEqual(count, 0)
        self.assertEqual(result, text)

    def test_literal_match_mode_escapes_tokens(self):
        # In literal mode, r"\n" must match literal backslash followed by 'n', NOT newline
        text = r"Line with literal \n and real" + "\nnewline."

        # Regex mode: matches real newline
        regex_spans = RegexEngine.find_match_spans(text, r"\n", is_literal=False)
        self.assertEqual(len(regex_spans), 1)
        self.assertEqual(text[regex_spans[0][0]:regex_spans[0][1]], "\n")

        # Literal mode: matches literal "\n"
        literal_spans = RegexEngine.find_match_spans(text, r"\n", is_literal=True)
        self.assertEqual(len(literal_spans), 1)
        self.assertEqual(text[literal_spans[0][0]:literal_spans[0][1]], r"\n")

    def test_literal_strip_and_replace(self):
        text = "file[1].txt and file[2].txt"
        # Regex [1] would be a char class; literal '[1]' matches exact characters '[1]'
        res, count = RegexEngine.strip_matches(text, "[1]", is_literal=True)
        self.assertEqual(count, 1)
        self.assertEqual(res, "file.txt and file[2].txt")

        # Literal replace
        res2, count2 = RegexEngine.replace_matches(text, "[2]", "(two)", is_literal=True)
        self.assertEqual(count2, 1)
        self.assertEqual(res2, "file[1].txt and file(two).txt")

    def test_replace_matches_caret_anchor(self):
        text = "Alpha\nBeta\nGamma\n"
        res, count = RegexEngine.replace_matches(text, "^", "♪")
        self.assertEqual(count, 3)
        self.assertEqual(res, "♪Alpha\n♪Beta\n♪Gamma\n")

        # Without trailing newline
        text_no_trailing = "Alpha\nBeta\nGamma"
        res2, count2 = RegexEngine.replace_matches(text_no_trailing, "^", "♪")
        self.assertEqual(count2, 3)
        self.assertEqual(res2, "♪Alpha\n♪Beta\n♪Gamma")

    def test_replace_matches_dollar_anchor(self):
        text = "Alpha\nBeta\nGamma\n"
        res, count = RegexEngine.replace_matches(text, "$", "♪")
        self.assertEqual(count, 3)
        self.assertEqual(res, "Alpha♪\nBeta♪\nGamma♪\n")

        # Windows CRLF
        text_crlf = "Alpha\r\nBeta\r\nGamma\r\n"
        res_crlf, count_crlf = RegexEngine.replace_matches(text_crlf, "$", "♪")
        self.assertEqual(count_crlf, 3)
        self.assertEqual(res_crlf, "Alpha♪\r\nBeta♪\r\nGamma♪\r\n")

        # Without trailing newline
        text_no_trailing = "Alpha\nBeta\nGamma"
        res2, count2 = RegexEngine.replace_matches(text_no_trailing, "$", "♪")
        self.assertEqual(count2, 3)
        self.assertEqual(res2, "Alpha♪\nBeta♪\nGamma♪")

    def test_literal_mode_caret_and_dollar(self):
        # In literal mode, ^ and $ should match literal symbols, not act as line anchors
        text = "^line1$\n^line2$\n"
        res_caret, count_caret = RegexEngine.replace_matches(text, "^", "♪", is_literal=True)
        self.assertEqual(count_caret, 2)
        self.assertEqual(res_caret, "♪line1$\n♪line2$\n")

        res_dollar, count_dollar = RegexEngine.replace_matches(text, "$", "♪", is_literal=True)
        self.assertEqual(count_dollar, 2)
        self.assertEqual(res_dollar, "^line1♪\n^line2♪\n")

    def test_generate_diff_preview_normal(self):
        text = "user: alice, user: bob"
        pattern = r"user:\s*(\w+)"
        replacement = r"admin[\1]"

        preview, green_spans, red_spans = RegexEngine.generate_diff_preview(
            text, pattern, replacement
        )

        self.assertEqual(preview, "user: aliceadmin[alice], user: bobadmin[bob]")
        self.assertEqual(len(green_spans), 2)
        self.assertEqual(len(red_spans), 2)

        # Verify green spans extract the replacement strings
        self.assertEqual([preview[s:e] for s, e in green_spans], ["admin[alice]", "admin[bob]"])
        # Verify red spans extract the original matched strings
        self.assertEqual([preview[s:e] for s, e in red_spans], ["user: alice", "user: bob"])

    def test_generate_diff_preview_caret_anchor(self):
        text = "line1\nline2\n"
        preview, green_spans, red_spans = RegexEngine.generate_diff_preview(text, "^", "♪")
        self.assertEqual(preview, "♪line1\n♪line2\n")
        self.assertEqual(len(green_spans), 2)
        self.assertEqual(len(red_spans), 0)
        self.assertEqual([preview[s:e] for s, e in green_spans], ["♪", "♪"])

    def test_generate_diff_preview_dollar_anchor(self):
        text = "line1\nline2\n"
        preview, green_spans, red_spans = RegexEngine.generate_diff_preview(text, "$", "♪")
        self.assertEqual(preview, "line1♪\nline2♪\n")
        self.assertEqual(len(green_spans), 2)
        self.assertEqual(len(red_spans), 0)
        self.assertEqual([preview[s:e] for s, e in green_spans], ["♪", "♪"])

    def test_generate_diff_preview_empty_or_no_matches(self):
        text = "hello world"
        preview, green, red = RegexEngine.generate_diff_preview(text, r"\d+", "999")
        self.assertEqual(preview, text)
        self.assertEqual(green, [])
        self.assertEqual(red, [])


if __name__ == "__main__":
    unittest.main()
