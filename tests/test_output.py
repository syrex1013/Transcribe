"""
Tests for format_output().

format_output(sentences, diar_segs) assembles the final transcript text:
  • One line per sentence:  "<timestamp>  <text>"
  • When diarization is available, a "── Speaker N ────" header is prepended
    whenever the active speaker changes.
  • Consecutive sentences from the same speaker share a single header.
"""
from __future__ import annotations

import pytest
import transcribe_groq as tg


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def sent(text: str, start: float = 0.0, end: float = 1.0) -> dict:
    return {"start": start, "end": end, "text": text}


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestFormatOutputNoDiarization:

    def test_empty_sentences_returns_empty_string(self) -> None:
        assert tg.format_output([], None) == ""

    def test_empty_sentences_empty_diar(self) -> None:
        assert tg.format_output([], []) == ""

    def test_single_sentence_contains_text(self) -> None:
        out = tg.format_output([sent("Hello world.")], None)
        assert "Hello world." in out

    def test_single_sentence_contains_timestamp(self) -> None:
        out = tg.format_output([sent("Hi.", 0.0)], None)
        assert "[00:00]" in out

    def test_timestamp_at_65_seconds(self) -> None:
        out = tg.format_output([sent("Hi.", 65.0)], None)
        assert "[01:05]" in out

    def test_no_speaker_headers_without_diarization(self) -> None:
        out = tg.format_output([sent("Hello."), sent("World.", 2.0)], None)
        assert "Speaker" not in out

    def test_no_speaker_headers_with_empty_diarization(self) -> None:
        out = tg.format_output([sent("Hello.")], [])
        assert "Speaker" not in out

    def test_multiple_sentences_ordered(self) -> None:
        sentences = [sent("First.", 0.0), sent("Second.", 10.0)]
        out = tg.format_output(sentences, None)
        assert out.index("First.") < out.index("Second.")

    def test_each_sentence_on_its_own_line(self) -> None:
        sentences = [sent("Alpha.", 0.0), sent("Beta.", 5.0)]
        lines = tg.format_output(sentences, None).splitlines()
        assert any("Alpha." in l for l in lines)
        assert any("Beta."  in l for l in lines)


@pytest.mark.unit
class TestFormatOutputWithDiarization:

    def test_speaker_header_added_on_change(self) -> None:
        sentences = [sent("Hi there.", 0.0, 1.0), sent("Hello back.", 2.0, 3.0)]
        diar = [(0.0, 1.5, "S_A"), (1.5, 3.5, "S_B")]
        out = tg.format_output(sentences, diar)
        assert "Speaker 1" in out
        assert "Speaker 2" in out

    def test_same_speaker_produces_single_header(self) -> None:
        sentences = [sent("First.", 0.0, 1.0), sent("Second.", 1.5, 2.5)]
        diar = [(0.0, 3.0, "S_A")]
        out = tg.format_output(sentences, diar)
        assert out.count("Speaker 1") == 1

    def test_speaker_header_precedes_first_sentence(self) -> None:
        sentences = [sent("Opening.", 0.0, 1.0)]
        diar = [(0.0, 2.0, "S_A")]
        out = tg.format_output(sentences, diar)
        lines = out.splitlines()
        speaker_line = next(i for i, l in enumerate(lines) if "Speaker" in l)
        text_line    = next(i for i, l in enumerate(lines) if "Opening." in l)
        assert speaker_line < text_line

    def test_speaker_change_inserts_blank_separator(self) -> None:
        sentences = [sent("Line A.", 0.0, 1.0), sent("Line B.", 2.0, 3.0)]
        diar = [(0.0, 1.5, "S_A"), (1.5, 3.5, "S_B")]
        out = tg.format_output(sentences, diar)
        # A blank line separates the two speaker blocks
        assert "\n\n" in out

    def test_no_overlap_sentence_has_no_speaker_header(self) -> None:
        # Diarization segment does not cover the sentence → no header
        sentences = [sent("Uncovered.", 10.0, 11.0)]
        diar = [(0.0, 1.0, "S_A")]
        out = tg.format_output(sentences, diar)
        assert "Speaker" not in out
