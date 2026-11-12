"""
Regex Engine for Regex Stripper
Handles pattern compilation, safe validation, match span discovery,
inverted span computation, bidirectional text stripping, and string replacement.
Supports both Regex mode and Literal Text matching mode.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Optional


class RegexEngine:
    """Core regex execution engine for matching, inverting, and stripping text."""

    @staticmethod
    def validate_pattern(
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[bool, str, Optional[re.Pattern]]:
        """
        Safely validates and compiles a regex pattern.

        Returns:
            (is_valid, error_message, compiled_pattern)
        """
        if not pattern:
            return True, "", None
        try:
            target_pat = re.escape(pattern) if is_literal else pattern
            compiled = re.compile(target_pat, flags)
            return True, "", compiled
        except re.error as e:
            return False, str(e), None

    @classmethod
    def find_match_spans(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        exclude_zero_width: bool = True,
        is_literal: bool = False
    ) -> List[Tuple[int, int]]:
        """
        Finds all match intervals (start, end) within the given text.
        """
        if not text or not pattern:
            return []

        # Special anchor handling when ^ or $ is used by itself in regex mode
        if not is_literal and pattern.strip() == "^":
            if flags & re.MULTILINE:
                spans = []
                offset = 0
                for line in text.splitlines(keepends=True):
                    spans.append((offset, min(len(text), offset + 1)))
                    offset += len(line)
                return spans
            else:
                return [(0, min(len(text), 1))] if text else []

        if not is_literal and pattern.strip() == "$":
            if flags & re.MULTILINE:
                spans = []
                offset = 0
                for line in text.splitlines(keepends=True):
                    content_len = len(line.rstrip("\r\n"))
                    end_pos = offset + content_len
                    spans.append((max(0, end_pos - 1), end_pos if content_len > 0 else end_pos + 1))
                    offset += len(line)
                return spans
            else:
                content_len = len(text.rstrip("\r\n"))
                end_pos = content_len
                return [(max(0, end_pos - 1), end_pos if content_len > 0 else end_pos + 1)] if text else []

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return []

        spans: List[Tuple[int, int]] = []
        try:
            for match in compiled.finditer(text):
                start, end = match.span()
                if exclude_zero_width and start == end:
                    continue
                spans.append((start, end))
        except Exception:
            return []

        return spans

    @classmethod
    def find_inverted_spans(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> List[Tuple[int, int]]:
        """
        Computes complementary intervals (non-matching spans) for the text.
        These are the exact spans targeted for deletion in DELETE_NON_MATCHES mode.
        """
        if not text:
            return []

        if not pattern:
            return [(0, len(text))]

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return []

        try:
            matches = [m.span() for m in compiled.finditer(text)]
        except Exception:
            return []

        if not matches:
            return [(0, len(text))]

        # Merge overlapping/adjacent match spans
        merged: List[Tuple[int, int]] = []
        for s, e in matches:
            if s == e:
                continue
            if not merged:
                merged.append((s, e))
            else:
                last_s, last_e = merged[-1]
                if s <= last_e:
                    merged[-1] = (last_s, max(last_e, e))
                else:
                    merged.append((s, e))

        if not merged:
            return [(0, len(text))]

        # Invert to find gaps
        inverted: List[Tuple[int, int]] = []
        cursor = 0
        for s, e in merged:
            if s > cursor:
                inverted.append((cursor, s))
            cursor = max(cursor, e)

        if cursor < len(text):
            inverted.append((cursor, len(text)))

        return inverted

    @classmethod
    def count_matches(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> int:
        """Counts total matches (including anchor matches for ^ and $)."""
        if not text or not pattern:
            return 0

        # Anchor handling when ^ or $ is used by itself
        if not is_literal and pattern.strip() in ("^", "$"):
            if flags & re.MULTILINE:
                return len(text.splitlines(keepends=True))
            else:
                return 1 if text else 0

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return 0
        try:
            return sum(1 for m in compiled.finditer(text) if m.start() != m.end())
        except Exception:
            return 0

    @classmethod
    def strip_matches(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[str, int]:
        """
        Deletes all matches from the text (Default Mode).
        Returns:
            (stripped_text, count_of_matches_removed)
        """
        if not text or not pattern:
            return text, 0

        # Anchor deletion for ^ or $ leaves text unchanged
        if not is_literal and pattern.strip() in ("^", "$"):
            if flags & re.MULTILINE:
                return text, len(text.splitlines(keepends=True))
            else:
                return text, 1 if text else 0

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        try:
            stripped, count = compiled.subn("", text)
            return stripped, count
        except Exception:
            return text, 0

    @classmethod
    def strip_non_matches(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        separator: str = "\n",
        is_literal: bool = False,
        unique: bool = False,
        capture_group: str = "0"
    ) -> Tuple[str, int]:
        """
        Deletes all non-matching text, keeping only matches (Inverted Mode).
        Supports custom delimiter, deduplication (unique), and capture group extraction.

        Returns:
            (extracted_matches_text, count_of_matches_kept)
        """
        if not text or not pattern:
            return "", 0

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        try:
            raw_matches = [m for m in compiled.finditer(text) if m.start() != m.end()]
            if not raw_matches:
                return "", 0

            # Extract text per match based on capture group or full match
            extracted: List[str] = []
            for m in raw_matches:
                if is_literal or not capture_group or capture_group == "0":
                    val = m.group(0)
                elif capture_group.isdigit():
                    idx = int(capture_group)
                    val = m.group(idx) if idx <= len(m.groups()) and m.group(idx) is not None else m.group(0)
                else:
                    try:
                        val = m.expand(capture_group)
                    except Exception:
                        val = m.group(0)
                extracted.append(val)

            # Deduplicate matches if requested while maintaining first-seen order
            if unique:
                seen = set()
                deduped = []
                for item in extracted:
                    if item not in seen:
                        seen.add(item)
                        deduped.append(item)
                extracted = deduped

            if not extracted:
                return "", 0

            actual_separator = separator.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
            if actual_separator == "\n" and all(m.endswith("\n") for m in extracted):
                joined = "".join(extracted)
            else:
                joined = actual_separator.join(extracted)

            return joined, len(extracted)
        except Exception:
            return text, 0

    @classmethod
    def replace_matches(
        cls,
        text: str,
        pattern: str,
        replacement: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[str, int]:
        """
        Replaces all matches with the specified replacement text.
        Supports standard regex backreferences (\\1, \\g<name>) unless in literal mode.

        Returns:
            (replaced_text, count_of_replacements)
        """
        if not text or not pattern:
            return text, 0

        # Anchor handling when ^ or $ is used by itself
        if not is_literal and pattern.strip() == "^":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, 0
                return "".join(replacement + line for line in lines), len(lines)
            else:
                if not text:
                    return text, 0
                return replacement + text, 1

        if not is_literal and pattern.strip() == "$":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, 0
                result_parts = []
                for line in lines:
                    if line.endswith("\r\n"):
                        result_parts.append(line[:-2] + replacement + "\r\n")
                    elif line.endswith("\n"):
                        result_parts.append(line[:-1] + replacement + "\n")
                    elif line.endswith("\r"):
                        result_parts.append(line[:-1] + replacement + "\r")
                    else:
                        result_parts.append(line + replacement)
                return "".join(result_parts), len(lines)
            else:
                if not text:
                    return text, 0
                if text.endswith("\r\n"):
                    return text[:-2] + replacement + "\r\n", 1
                elif text.endswith("\n") or text.endswith("\r"):
                    return text[:-1] + replacement + text[-1], 1
                else:
                    return text + replacement, 1

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        try:
            if is_literal:
                # In literal mode, treat replacement text 100% literally
                replaced, count = compiled.subn(lambda m: replacement, text)
            else:
                replaced, count = compiled.subn(replacement, text)
            return replaced, count
        except Exception:
            return text, 0

    @classmethod
    def generate_diff_preview(
        cls,
        text: str,
        pattern: str,
        replacement: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[str, List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Generates an inline diff preview where proposed replacements appear to the left of the
        text they replace.

        Returns:
            (preview_text, green_insert_spans, red_delete_spans)
        """
        if not text or not pattern or not replacement:
            return text, [], []

        # Anchor handling for ^
        if not is_literal and pattern.strip() == "^":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, [], []
                parts: List[str] = []
                green_spans: List[Tuple[int, int]] = []
                offset = 0
                repl_len = len(replacement)
                for line in lines:
                    green_spans.append((offset, offset + repl_len))
                    parts.append(replacement)
                    offset += repl_len
                    parts.append(line)
                    offset += len(line)
                return "".join(parts), green_spans, []
            else:
                if not text:
                    return text, [], []
                repl_len = len(replacement)
                return replacement + text, [(0, repl_len)], []

        # Anchor handling for $
        if not is_literal and pattern.strip() == "$":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, [], []
                parts: List[str] = []
                green_spans: List[Tuple[int, int]] = []
                offset = 0
                repl_len = len(replacement)
                for line in lines:
                    if line.endswith("\r\n"):
                        body = line[:-2]
                        ending = "\r\n"
                    elif line.endswith("\n"):
                        body = line[:-1]
                        ending = "\n"
                    elif line.endswith("\r"):
                        body = line[:-1]
                        ending = "\r"
                    else:
                        body = line
                        ending = ""
                    parts.append(body)
                    offset += len(body)
                    green_spans.append((offset, offset + repl_len))
                    parts.append(replacement)
                    offset += repl_len
                    parts.append(ending)
                    offset += len(ending)
                return "".join(parts), green_spans, []
            else:
                if not text:
                    return text, [], []
                repl_len = len(replacement)
                if text.endswith("\r\n"):
                    body = text[:-2]
                    ending = "\r\n"
                elif text.endswith("\n") or text.endswith("\r"):
                    body = text[:-1]
                    ending = text[-1]
                else:
                    body = text
                    ending = ""
                preview = body + replacement + ending
                green_spans = [(len(body), len(body) + repl_len)]
                return preview, green_spans, []

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, [], []

        try:
            raw_matches = list(compiled.finditer(text))
            matches = [m for m in raw_matches if m.start() != m.end()]
            if not matches:
                return text, [], []

            parts: List[str] = []
            green_spans: List[Tuple[int, int]] = []
            red_spans: List[Tuple[int, int]] = []
            cursor = 0
            offset = 0

            for m in matches:
                s, e = m.span()
                before = text[cursor:s]
                if before:
                    parts.append(before)
                    offset += len(before)

                # 1. Original replaced text FIRST (left: red, strikethrough & italics)
                orig_str = text[s:e]
                if orig_str:
                    red_spans.append((offset, offset + len(orig_str)))
                    parts.append(orig_str)
                    offset += len(orig_str)

                # 2. Proposed replacement text SECOND (right: green & bold)
                if is_literal:
                    repl_str = replacement
                else:
                    try:
                        repl_str = m.expand(replacement)
                    except Exception:
                        repl_str = replacement

                if repl_str:
                    green_spans.append((offset, offset + len(repl_str)))
                    parts.append(repl_str)
                    offset += len(repl_str)

                cursor = e

            after = text[cursor:]
            if after:
                parts.append(after)

            return "".join(parts), green_spans, red_spans
        except Exception:
            return text, [], []

    @classmethod
    def delete_duplicate_lines(
        cls,
        text: str,
        ignore_case: bool = False
    ) -> Tuple[str, int]:
        """
        Removes all duplicate lines from the text, retaining only the first
        occurrence of each unique line in its original order.

        Args:
            text: Input text containing lines.
            ignore_case: If True, lines differing only in casing are treated as duplicates.

        Returns:
            (deduped_text, count_of_duplicate_lines_removed)
        """
        if not text:
            return "", 0

        lines = text.splitlines(keepends=False)
        if not lines:
            return "", 0

        seen = set()
        kept_lines: List[str] = []
        dup_count = 0

        for line in lines:
            key = line.lower() if ignore_case else line
            if key not in seen:
                seen.add(key)
                kept_lines.append(line)
            else:
                dup_count += 1

        if dup_count == 0:
            return text, 0

        # Preserve line ending style
        if "\r\n" in text:
            eol = "\r\n"
        elif "\r" in text and "\n" not in text:
            eol = "\r"
        else:
            eol = "\n"

        result = eol.join(kept_lines)

        # Preserve trailing newline if originally present
        if text.endswith("\r\n"):
            result += "\r\n"
        elif text.endswith("\n"):
            result += "\n"
        elif text.endswith("\r"):
            result += "\r"

        return result, dup_count
