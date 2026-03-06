"""
Tests for pure text-formatting utilities:

  fmt_ts(s)     — convert integer/float seconds to a [HH:]MM:SS timestamp string
  _clean(text)  — collapse whitespace and capitalise the first character
"""
from __future__ import annotations

import pytest
import transcribe_groq as tg


# ─────────────────────────────────────────────────────────────────────────────
# fmt_ts
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFmtTs:
    """fmt_ts formats a number of seconds as [HH:]MM:SS."""

    @pytest.mark.parametrize("seconds, expected", [
        (0,    "[00:00]"),
        (1,    "[00:01]"),
        (59,   "[00:59]"),
        (60,   "[01:00]"),
        (65,   "[01:05]"),
        (599,  "[09:59]"),
        (3599, "[59:59]"),
        (3600, "[01:00:00]"),
        (3601, "[01:00:01]"),
        (3661, "[01:01:01]"),
        (7261, "[02:01:01]"),
        (86400,"[24:00:00]"),
    ])
    def test_format(self, seconds: int, expected: str) -> None:
        assert tg.fmt_ts(seconds) == expected

    @pytest.mark.parametrize("seconds, expected", [
        (90.9,   "[01:30]"),   # truncated, not rounded
        (59.99,  "[00:59]"),
        (3660.5, "[01:01:00]"),
    ])
    def test_float_truncated(self, seconds: float, expected: str) -> None:
        """float input must be truncated (int()), not rounded."""
        assert tg.fmt_ts(seconds) == expected

    def test_sub_minute_has_no_hour_component(self) -> None:
        result = tg.fmt_ts(45)
        assert result.count(":") == 1          # MM:SS only
        assert result.startswith("[")
        assert result.endswith("]")

    def test_exactly_one_hour_has_hour_component(self) -> None:
        result = tg.fmt_ts(3600)
        assert result.count(":") == 2          # HH:MM:SS


# ─────────────────────────────────────────────────────────────────────────────
# _clean
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestClean:
    """_clean collapses whitespace and capitalises the first character."""

    @pytest.mark.parametrize("text, expected", [
        ("",                  ""),
        ("hello world",       "Hello world"),
        ("ALREADY UPPER",     "ALREADY UPPER"),
        ("  spaces  ",        "Spaces"),
        ("line\nbreak",       "Line break"),
        ("multiple   gaps",   "Multiple gaps"),
        ("hello   world foo", "Hello world foo"),
        ("\ttabbed\t",        "Tabbed"),
        ("a",                 "A"),
        ("123 numbers",       "123 numbers"),
    ])
    def test_clean_parametrized(self, text: str, expected: str) -> None:
        assert tg._clean(text) == expected

    def test_preserves_trailing_punctuation(self) -> None:
        assert tg._clean("hello, world.") == "Hello, world."

    def test_already_clean_unchanged(self) -> None:
        assert tg._clean("Already clean.") == "Already clean."

    def test_only_whitespace_returns_empty(self) -> None:
        assert tg._clean("   ") == ""

    def test_newlines_and_tabs_collapsed(self) -> None:
        result = tg._clean("a\t\n\rb")
        assert result == "A b"
