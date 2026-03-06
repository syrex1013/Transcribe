"""
Tests for build_sentences().

build_sentences() operates in two modes:
  • word-mode   — Groq word-level timestamps are available
  • segment-mode — only coarser segment timestamps are available (fallback)

Splitting logic is driven by three thresholds (from transcribe_groq):
  MERGE_GAP_MAX   = 0.45 s  — gap SMALLER than this → words stay in one sentence
  SPLIT_GAP_MIN   = 1.20 s  — gap LARGER than this  → always start a new sentence
  MAX_SENT_CHARS  = 220     — accumulated text beyond this → flush sentence
"""
from __future__ import annotations

import pytest
import transcribe_groq as tg

# Threshold aliases (keep tests readable without magic numbers)
MERGE_GAP = tg.MERGE_GAP_MAX   # 0.45 s
SPLIT_GAP = tg.SPLIT_GAP_MIN   # 1.20 s
MAX_CHARS = tg.MAX_SENT_CHARS   # 220


# ─────────────────────────────────────────────────────────────────────────────
# Local helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_word(text: str, start: float, end: float) -> dict:
    return {"word": text, "start": start, "end": end}


def make_segment(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end}


def texts(sentences: list[dict]) -> list[str]:
    return [s["text"] for s in sentences]


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildSentencesEmpty:
    def test_no_words_no_segments(self) -> None:
        assert tg.build_sentences([], []) == []

    def test_no_words_no_segments_with_offset(self) -> None:
        assert tg.build_sentences([], [], time_offset=999.0) == []


# ─────────────────────────────────────────────────────────────────────────────
# Word-mode
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildSentencesWordMode:

    def test_single_word(self) -> None:
        result = tg.build_sentences([make_word("Hello.", 0.0, 0.5)], [])
        assert len(result) == 1
        assert result[0]["text"] == "Hello."
        assert result[0]["start"] == pytest.approx(0.0)
        assert result[0]["end"]   == pytest.approx(0.5)

    def test_time_offset_positive(self) -> None:
        result = tg.build_sentences([make_word("Hi.", 1.0, 1.5)], [], time_offset=10.0)
        assert result[0]["start"] == pytest.approx(11.0)
        assert result[0]["end"]   == pytest.approx(11.5)

    def test_time_offset_negative(self) -> None:
        result = tg.build_sentences([make_word("Hi.", 10.0, 10.5)], [], time_offset=-5.0)
        assert result[0]["start"] == pytest.approx(5.0)

    def test_merges_gap_below_threshold(self) -> None:
        # gap = MERGE_GAP - ε  → single sentence
        gap = MERGE_GAP - 0.05
        words = [make_word("hello", 0.0, 0.3), make_word("world", 0.3 + gap, 0.8)]
        result = tg.build_sentences(words, [])
        assert len(result) == 1
        assert "hello" in result[0]["text"].lower()
        assert "world" in result[0]["text"].lower()

    def test_splits_gap_above_split_threshold(self) -> None:
        # gap > SPLIT_GAP_MIN → two sentences regardless of punctuation
        gap = SPLIT_GAP + 0.1
        words = [make_word("First", 0.0, 0.5), make_word("Second", 0.5 + gap, 1.0)]
        result = tg.build_sentences(words, [])
        assert len(result) == 2

    def test_splits_on_sentence_end_with_medium_gap(self) -> None:
        # gap is >= MERGE_GAP_MAX but < SPLIT_GAP_MIN, AND ends with punctuation → split
        gap = MERGE_GAP + 0.05   # 0.50 s: above merge threshold, below split threshold
        words = [make_word("Done.", 0.0, 0.5), make_word("Next.", 0.5 + gap, 1.0)]
        result = tg.build_sentences(words, [])
        assert len(result) == 2

    def test_no_split_on_sentence_end_with_tiny_gap(self) -> None:
        # gap < MERGE_GAP_MAX → merge even if text ends with punctuation
        gap = MERGE_GAP - 0.05
        words = [make_word("Done.", 0.0, 0.5), make_word("More.", 0.5 + gap, 1.0)]
        result = tg.build_sentences(words, [])
        assert len(result) == 1

    def test_long_text_triggers_split(self) -> None:
        # Each word is 10 chars; 25 words = 250 chars > MAX_CHARS → at least one flush mid-way
        long_word = "w" * 10
        words = [make_word(long_word, i * 0.1, i * 0.1 + 0.05) for i in range(25)]
        result = tg.build_sentences(words, [])
        assert len(result) >= 2

    def test_output_text_capitalised(self) -> None:
        result = tg.build_sentences([make_word("lowercase.", 0.0, 0.5)], [])
        assert result[0]["text"][0].isupper()

    def test_many_words_single_sentence_when_gap_small(self) -> None:
        # All words close together → one long sentence
        words = [make_word(f"word{i}", i * 0.1, i * 0.1 + 0.05) for i in range(5)]
        result = tg.build_sentences(words, [])
        assert len(result) == 1
        combined = result[0]["text"].lower()
        for i in range(5):
            assert f"word{i}" in combined


# ─────────────────────────────────────────────────────────────────────────────
# Segment-mode (fallback when no word timestamps)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestBuildSentencesSegmentMode:

    def test_single_segment(self) -> None:
        result = tg.build_sentences([], [make_segment(" segment one.", 0.0, 2.0)])
        assert len(result) == 1
        assert result[0]["text"] == "Segment one."

    def test_strips_leading_whitespace(self) -> None:
        result = tg.build_sentences([], [make_segment("   leading", 0.0, 1.0)])
        assert not result[0]["text"].startswith(" ")

    def test_time_offset_applied_to_segments(self) -> None:
        result = tg.build_sentences([], [make_segment("hi.", 1.0, 2.0)], time_offset=5.0)
        assert result[0]["start"] == pytest.approx(6.0)
        assert result[0]["end"]   == pytest.approx(7.0)

    def test_multiple_segments_each_become_sentence(self) -> None:
        # Gap > MERGE_GAP_MAX and text ends with punctuation → each segment is its own sentence
        gap = MERGE_GAP + 0.15  # 0.60 s: above MERGE_GAP_MAX, below SPLIT_GAP_MIN
        duration = 0.9
        segs = [
            make_segment(f" Sentence {i}.", i * (duration + gap), i * (duration + gap) + duration)
            for i in range(3)
        ]
        result = tg.build_sentences([], segs)
        assert len(result) == 3

    def test_empty_segment_text_skipped(self) -> None:
        segs = [make_segment("   ", 0.0, 1.0), make_segment("real text.", 1.0, 2.0)]
        result = tg.build_sentences([], segs)
        # Only the real-text segment should produce output
        assert all(s["text"].strip() for s in result)

    def test_words_take_priority_over_segments(self) -> None:
        words = [make_word("from words.", 0.0, 1.0)]
        segs  = [make_segment("from segments.", 0.0, 1.0)]
        result = tg.build_sentences(words, segs)
        assert "words" in result[0]["text"].lower()
        assert "segments" not in result[0]["text"].lower()
