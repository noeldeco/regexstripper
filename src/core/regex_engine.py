"""
Regex Engine for Regex Stripper
Handles single-pass pattern compilation, safe validation, match span discovery,
inverted span computation, line-level filtering, bidirectional text stripping,
string replacement (bulk & step-through), inline diff preview, and line utilities.
Supports both Regex mode and Literal Text matching mode.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from src.config import DeletionMode


@dataclass
class AnalysisResult:
    """Single-pass analysis output to avoid redundant regex compilation/scanning."""
    is_valid: bool = True
    error_message: str = ""
    match_spans: List[Tuple[int, int]] = field(default_factory=list)
    match_count: int = 0
    target_spans: List[Tuple[int, int]] = field(default_factory=list)
    matching_line_count: int = 0
    total_line_count: int = 0
    timed_out: bool = False


_ESCAPE_RE = re.compile(r"\\([nrt\\])")
_ESCAPE_MAP = {"n": "\n", "r": "\r", "t": "\t", "\\": "\\"}
_NATURAL_SPLIT_RE = re.compile(r"(\d+)")


class RegexEngine:
    """Core regex execution engine for matching, inverting, stripping, and line utilities."""

    @staticmethod
    def interpret_escapes(text: str) -> str:
        """Converts \\n, \\r, \\t, and \\\\ escape sequences into literal characters."""
        if not text or "\\" not in text:
            return text
        return _ESCAPE_RE.sub(lambda m: _ESCAPE_MAP[m.group(1)], text)

    @staticmethod
    def _detect_eol(text: str) -> str:
        if "\r\n" in text:
            return "\r\n"
        if "\r" in text and "\n" not in text:
            return "\r"
        return "\n"

    @staticmethod
    def _trailing_eol(text: str) -> str:
        if text.endswith("\r\n"):
            return "\r\n"
        if text.endswith("\n"):
            return "\n"
        if text.endswith("\r"):
            return "\r"
        return ""

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

    @staticmethod
    def _invert_spans(text_len: int, match_spans: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Computes complementary (non-matching) spans directly from sorted match_spans."""
        if text_len <= 0:
            return []
        if not match_spans:
            return [(0, text_len)]

        merged: List[Tuple[int, int]] = []
        for s, e in match_spans:
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
            return [(0, text_len)]

        inverted: List[Tuple[int, int]] = []
        cursor = 0
        for s, e in merged:
            if s > cursor:
                inverted.append((cursor, s))
            cursor = max(cursor, e)

        if cursor < text_len:
            inverted.append((cursor, text_len))

        return inverted

    @staticmethod
    def _compute_line_bounds(text: str) -> List[Tuple[int, int, int]]:
        """
        Returns list of (line_start, content_end, full_end) for each line in text.
        """
        bounds: List[Tuple[int, int, int]] = []
        offset = 0
        for line in text.splitlines(keepends=True):
            line_len = len(line)
            content_len = len(line.rstrip("\r\n"))
            bounds.append((offset, offset + content_len, offset + line_len))
            offset += line_len
        return bounds

    @classmethod
    def _partition_lines_by_matches(
        cls,
        text: str,
        match_spans: List[Tuple[int, int]]
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], int]:
        """
        Partitions lines into matching vs non-matching spans in O(L + M).

        Returns:
            (matching_line_spans, non_matching_line_spans, total_line_count)
        """
        line_bounds = cls._compute_line_bounds(text)
        total_lines = len(line_bounds)
        if not line_bounds:
            return [], [], 0

        matching: List[Tuple[int, int]] = []
        non_matching: List[Tuple[int, int]] = []

        m_idx = 0
        m_len = len(match_spans)

        for l_start, c_end, l_end in line_bounds:
            # Advance matches that ended at or before this line started
            while m_idx < m_len and match_spans[m_idx][1] <= l_start and match_spans[m_idx][0] < l_start:
                m_idx += 1

            has_match = False
            j = m_idx
            while j < m_len:
                ms, me = match_spans[j]
                if ms >= l_end:
                    break
                # Check overlap with line (including zero-width anchor inside line)
                if (ms < l_end and me > l_start) or (ms == me and l_start <= ms <= c_end):
                    has_match = True
                    break
                j += 1

            span = (l_start, c_end if c_end > l_start else l_end)
            if has_match:
                matching.append(span)
            else:
                non_matching.append(span)

        return matching, non_matching, total_lines

    @classmethod
    def _find_spans_with_compiled(
        cls,
        text: str,
        pattern: str,
        compiled: Optional[re.Pattern],
        flags: int,
        exclude_zero_width: bool,
        is_literal: bool
    ) -> Tuple[List[Tuple[int, int]], int]:
        """Internal single-pass span finder returning (spans, match_count)."""
        if not text or not pattern:
            return [], 0

        if not is_literal and pattern.strip() == "^":
            if flags & re.MULTILINE:
                spans: List[Tuple[int, int]] = []
                offset = 0
                lines = text.splitlines(keepends=True)
                for line in lines:
                    spans.append((offset, min(len(text), offset + 1)))
                    offset += len(line)
                return spans, len(lines)
            return [(0, min(len(text), 1))], 1

        if not is_literal and pattern.strip() == "$":
            if flags & re.MULTILINE:
                spans = []
                offset = 0
                lines = text.splitlines(keepends=True)
                for line in lines:
                    content_len = len(line.rstrip("\r\n"))
                    end_pos = offset + content_len
                    spans.append((max(0, end_pos - 1), end_pos if content_len > 0 else end_pos + 1))
                    offset += len(line)
                return spans, len(lines)
            content_len = len(text.rstrip("\r\n"))
            end_pos = content_len
            return [(max(0, end_pos - 1), end_pos if content_len > 0 else end_pos + 1)], 1

        if compiled is None:
            return [], 0

        spans = []
        try:
            for match in compiled.finditer(text):
                start, end = match.span()
                if exclude_zero_width and start == end:
                    continue
                spans.append((start, end))
        except Exception:
            return [], 0

        return spans, len(spans)

    @classmethod
    def analyze(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False,
        mode: DeletionMode = DeletionMode.DELETE_MATCHES
    ) -> AnalysisResult:
        """
        Single-pass pattern analysis: compiles regex once, runs finditer once,
        and derives match_spans, match_count, target_spans, and line counts.
        """
        total_lines = len(text.splitlines()) if text else 0

        if not pattern:
            return AnalysisResult(
                is_valid=True,
                error_message="",
                total_line_count=total_lines
            )

        is_valid, err_msg, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return AnalysisResult(
                is_valid=False,
                error_message=err_msg,
                total_line_count=total_lines
            )

        if not text:
            return AnalysisResult(is_valid=True, error_message="", total_line_count=0)

        match_spans, match_count = cls._find_spans_with_compiled(
            text, pattern, compiled, flags, exclude_zero_width=True, is_literal=is_literal
        )

        matching_line_count = 0
        if mode == DeletionMode.DELETE_MATCHES:
            target_spans = match_spans
        elif mode == DeletionMode.DELETE_NON_MATCHES:
            target_spans = cls._invert_spans(len(text), match_spans)
        elif mode == DeletionMode.DELETE_MATCHING_LINES:
            matching_lines, _, total_lines = cls._partition_lines_by_matches(text, match_spans)
            target_spans = matching_lines
            matching_line_count = len(matching_lines)
        elif mode == DeletionMode.KEEP_MATCHING_LINES:
            matching_lines, non_matching_lines, total_lines = cls._partition_lines_by_matches(text, match_spans)
            target_spans = non_matching_lines
            matching_line_count = len(matching_lines)
        else:
            target_spans = match_spans

        return AnalysisResult(
            is_valid=True,
            error_message="",
            match_spans=match_spans,
            match_count=match_count,
            target_spans=target_spans,
            matching_line_count=matching_line_count,
            total_line_count=total_lines
        )

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

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid:
            return []

        spans, _ = cls._find_spans_with_compiled(
            text, pattern, compiled, flags,
            exclude_zero_width=exclude_zero_width, is_literal=is_literal
        )
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

        return cls._invert_spans(len(text), matches)

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

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid:
            return 0

        _, count = cls._find_spans_with_compiled(
            text, pattern, compiled, flags,
            exclude_zero_width=True, is_literal=is_literal
        )
        return count

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
            return text, 1

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

            actual_separator = cls.interpret_escapes(separator)
            if actual_separator == "\n" and all(m.endswith("\n") for m in extracted):
                joined = "".join(extracted)
            else:
                joined = actual_separator.join(extracted)

            return joined, len(extracted)
        except Exception:
            return text, 0

    @classmethod
    def strip_matching_lines(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[str, int]:
        """
        Deletes every entire line that contains at least one match (grep -v).
        Returns:
            (remaining_text, count_of_lines_removed)
        """
        if not text or not pattern:
            return text, 0

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        lines = text.splitlines(keepends=False)
        if not lines:
            return text, 0

        eol = cls._detect_eol(text)
        trailing = cls._trailing_eol(text)

        kept: List[str] = []
        removed = 0
        for line in lines:
            if compiled.search(line) is not None:
                removed += 1
            else:
                kept.append(line)

        if removed == 0:
            return text, 0
        if not kept:
            return "", removed

        result = eol.join(kept) + trailing
        return result, removed

    @classmethod
    def keep_matching_lines(
        cls,
        text: str,
        pattern: str,
        flags: int = 0,
        is_literal: bool = False
    ) -> Tuple[str, int]:
        """
        Keeps only entire lines that contain at least one match (grep).
        Returns:
            (kept_text, count_of_lines_kept)
        """
        if not text or not pattern:
            return "", 0

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        lines = text.splitlines(keepends=False)
        if not lines:
            return "", 0

        eol = cls._detect_eol(text)
        trailing = cls._trailing_eol(text)

        kept: List[str] = [line for line in lines if compiled.search(line) is not None]
        if not kept:
            return "", 0

        result = eol.join(kept) + trailing
        return result, len(kept)

    @classmethod
    def replace_matches(
        cls,
        text: str,
        pattern: str,
        replacement: str,
        flags: int = 0,
        is_literal: bool = False,
        interpret_escapes: bool = False
    ) -> Tuple[str, int]:
        """
        Replaces all matches with the specified replacement text.
        Supports standard regex backreferences (\\1, \\g<name>) unless in literal mode.
        When interpret_escapes=True, converts \\n, \\t, \\r, \\\\ in replacement text.

        Returns:
            (replaced_text, count_of_replacements)
        """
        if not text or not pattern:
            return text, 0

        actual_repl = cls.interpret_escapes(replacement) if (interpret_escapes and (is_literal or pattern.strip() in ("^", "$"))) else replacement

        # Anchor handling when ^ or $ is used by itself
        if not is_literal and pattern.strip() == "^":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, 0
                return "".join(actual_repl + line for line in lines), len(lines)
            return actual_repl + text, 1

        if not is_literal and pattern.strip() == "$":
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, 0
                result_parts = []
                for line in lines:
                    if line.endswith("\r\n"):
                        result_parts.append(line[:-2] + actual_repl + "\r\n")
                    elif line.endswith("\n"):
                        result_parts.append(line[:-1] + actual_repl + "\n")
                    elif line.endswith("\r"):
                        result_parts.append(line[:-1] + actual_repl + "\r")
                    else:
                        result_parts.append(line + actual_repl)
                return "".join(result_parts), len(lines)
            if text.endswith("\r\n"):
                return text[:-2] + actual_repl + "\r\n", 1
            if text.endswith("\n") or text.endswith("\r"):
                return text[:-1] + actual_repl + text[-1], 1
            return text + actual_repl, 1

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, 0

        try:
            if is_literal:
                replaced, count = compiled.subn(lambda m: actual_repl, text)
            else:
                replaced, count = compiled.subn(replacement, text)
            return replaced, count
        except Exception:
            return text, 0

    @classmethod
    def replace_single_match(
        cls,
        text: str,
        span: Tuple[int, int],
        pattern: str,
        replacement: str,
        flags: int = 0,
        is_literal: bool = False,
        interpret_escapes: bool = False
    ) -> Tuple[str, int, bool]:
        """
        Replaces a single match at `span` in `text`.
        Returns:
            (new_text, end_offset_after_replacement, did_replace)
        """
        if not text or not pattern:
            return text, 0, False

        start, end = span
        actual_repl = cls.interpret_escapes(replacement) if (interpret_escapes and (is_literal or pattern.strip() in ("^", "$"))) else replacement

        if not is_literal and pattern.strip() == "^":
            new_text = text[:start] + actual_repl + text[start:]
            return new_text, start + len(actual_repl), True

        if not is_literal and pattern.strip() == "$":
            insert_pos = end
            new_text = text[:insert_pos] + actual_repl + text[insert_pos:]
            return new_text, insert_pos + len(actual_repl), True

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, start, False

        try:
            m = compiled.match(text, start)
            if m is None or m.span() != (start, end):
                # Fallback search from start
                m = compiled.search(text, start)
                if m is None:
                    return text, start, False
                start, end = m.span()

            if is_literal:
                repl_str = actual_repl
            else:
                try:
                    repl_str = m.expand(replacement)
                except Exception:
                    repl_str = replacement

            new_text = text[:start] + repl_str + text[end:]
            return new_text, start + len(repl_str), True
        except Exception:
            return text, start, False

    @classmethod
    def generate_diff_preview(
        cls,
        text: str,
        pattern: str,
        replacement: str,
        flags: int = 0,
        is_literal: bool = False,
        interpret_escapes: bool = False
    ) -> Tuple[str, List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Generates an inline diff preview where replaced original text appears first
        (red strikethrough/italics) and proposed replacement text appears immediately to its right
        (green bold).

        Returns:
            (preview_text, green_insert_spans, red_delete_spans)
        """
        if not text or not pattern or not replacement:
            return text, [], []

        actual_repl = cls.interpret_escapes(replacement) if (interpret_escapes and (is_literal or pattern.strip() in ("^", "$"))) else replacement

        # Anchor handling for ^
        if not is_literal and pattern.strip() == "^":
            repl_len = len(actual_repl)
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, [], []
                parts: List[str] = []
                green_spans: List[Tuple[int, int]] = []
                offset = 0
                for line in lines:
                    green_spans.append((offset, offset + repl_len))
                    parts.append(actual_repl)
                    offset += repl_len
                    parts.append(line)
                    offset += len(line)
                return "".join(parts), green_spans, []
            return actual_repl + text, [(0, repl_len)], []

        # Anchor handling for $
        if not is_literal and pattern.strip() == "$":
            repl_len = len(actual_repl)
            if flags & re.MULTILINE:
                lines = text.splitlines(keepends=True)
                if not lines:
                    return text, [], []
                parts = []
                green_spans = []
                offset = 0
                for line in lines:
                    if line.endswith("\r\n"):
                        body, ending = line[:-2], "\r\n"
                    elif line.endswith("\n"):
                        body, ending = line[:-1], "\n"
                    elif line.endswith("\r"):
                        body, ending = line[:-1], "\r"
                    else:
                        body, ending = line, ""
                    parts.append(body)
                    offset += len(body)
                    green_spans.append((offset, offset + repl_len))
                    parts.append(actual_repl)
                    offset += repl_len
                    parts.append(ending)
                    offset += len(ending)
                return "".join(parts), green_spans, []
            if text.endswith("\r\n"):
                body, ending = text[:-2], "\r\n"
            elif text.endswith("\n") or text.endswith("\r"):
                body, ending = text[:-1], text[-1]
            else:
                body, ending = text, ""
            preview = body + actual_repl + ending
            return preview, [(len(body), len(body) + repl_len)], []

        is_valid, _, compiled = cls.validate_pattern(pattern, flags, is_literal=is_literal)
        if not is_valid or compiled is None:
            return text, [], []

        try:
            matches = [m for m in compiled.finditer(text) if m.start() != m.end()]
            if not matches:
                return text, [], []

            parts = []
            green_spans = []
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
                    repl_str = actual_repl
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

        eol = cls._detect_eol(text)
        result = eol.join(kept_lines) + cls._trailing_eol(text)
        return result, dup_count

    @classmethod
    def remove_blank_lines(cls, text: str) -> Tuple[str, int]:
        """
        Removes all empty or whitespace-only lines from text.
        Returns:
            (cleaned_text, count_of_blank_lines_removed)
        """
        if not text:
            return "", 0

        lines = text.splitlines(keepends=False)
        if not lines:
            return "", 0

        kept = [line for line in lines if line.strip() != ""]
        removed = len(lines) - len(kept)
        if removed == 0:
            return text, 0
        if not kept:
            return "", removed

        eol = cls._detect_eol(text)
        return eol.join(kept) + cls._trailing_eol(text), removed

    @classmethod
    def trim_lines(cls, text: str) -> Tuple[str, int]:
        """
        Strips leading and trailing spaces/tabs on every line.
        Returns:
            (trimmed_text, count_of_modified_lines)
        """
        if not text:
            return "", 0

        lines = text.splitlines(keepends=False)
        if not lines:
            return "", 0

        trimmed: List[str] = []
        modified = 0
        for line in lines:
            t = line.strip(" \t")
            if t != line:
                modified += 1
            trimmed.append(t)

        if modified == 0:
            return text, 0

        eol = cls._detect_eol(text)
        return eol.join(trimmed) + cls._trailing_eol(text), modified

    @classmethod
    def sort_lines(
        cls,
        text: str,
        mode: str = "asc",
        ignore_case: bool = False
    ) -> Tuple[str, int]:
        """
        Sorts lines in text.
        Supported modes: "asc", "desc", "natural", "length".
        Returns:
            (sorted_text, total_line_count)
        """
        if not text:
            return "", 0

        lines = text.splitlines(keepends=False)
        if len(lines) <= 1:
            return text, len(lines)

        if mode == "desc":
            key_fn = (lambda s: s.lower()) if ignore_case else None
            sorted_lines = sorted(lines, key=key_fn, reverse=True)
        elif mode == "natural":
            def nat_key(s: str):
                target = s.lower() if ignore_case else s
                return [
                    (0, int(tok), "") if tok.isdigit() else (1, 0, tok)
                    for tok in _NATURAL_SPLIT_RE.split(target)
                ]
            sorted_lines = sorted(lines, key=nat_key)
        elif mode == "length":
            sorted_lines = sorted(lines, key=lambda s: (len(s), s.lower() if ignore_case else s))
        else:
            key_fn = (lambda s: s.lower()) if ignore_case else None
            sorted_lines = sorted(lines, key=key_fn)

        eol = cls._detect_eol(text)
        return eol.join(sorted_lines) + cls._trailing_eol(text), len(sorted_lines)
