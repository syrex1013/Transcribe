"""
Tests for assign_speaker().

assign_speaker(start, end, diar_segs, speaker_map) returns the human-readable
label for the speaker with the greatest overlap with [start, end], or None
when there is no overlap at all.

speaker_map is mutated in-place to maintain consistent label assignment across
successive calls.
"""
from __future__ import annotations

import pytest
import transcribe_groq as tg


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def diar(*items: tuple) -> list[tuple]:
    """Shorthand for a list of (start, end, label) diarization segments."""
    return list(items)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestAssignSpeakerNoSegments:

    def test_none_returns_none(self) -> None:
        assert tg.assign_speaker(0.0, 1.0, None, {}) is None

    def test_empty_list_returns_none(self) -> None:
        assert tg.assign_speaker(0.0, 1.0, [], {}) is None


@pytest.mark.unit
class TestAssignSpeakerOverlap:

    def test_full_overlap(self) -> None:
        mapping: dict = {}
        result = tg.assign_speaker(0.0, 1.0, diar((0.0, 2.0, "S_00")), mapping)
        assert result == "Speaker 1"
        assert mapping["S_00"] == "Speaker 1"

    def test_partial_overlap_start(self) -> None:
        # Segment (0.5, 1.5) overlaps [0.0, 1.0] by 0.5 s
        result = tg.assign_speaker(0.0, 1.0, diar((0.5, 1.5, "S_00")), {})
        assert result == "Speaker 1"

    def test_no_overlap_before(self) -> None:
        # Segment ends before sentence starts
        assert tg.assign_speaker(2.0, 3.0, diar((0.0, 1.0, "S_00")), {}) is None

    def test_no_overlap_after(self) -> None:
        # Segment starts after sentence ends
        assert tg.assign_speaker(0.0, 1.0, diar((5.0, 7.0, "S_00")), {}) is None

    def test_touch_boundary_is_zero_overlap(self) -> None:
        # Segment ends exactly when sentence starts → overlap = 0
        assert tg.assign_speaker(1.0, 2.0, diar((0.0, 1.0, "S_00")), {}) is None


@pytest.mark.unit
class TestAssignSpeakerVoting:

    def test_longer_overlap_wins(self) -> None:
        segs = diar(
            (0.0, 0.3, "S_MINOR"),   # 0.3 s overlap
            (0.0, 0.8, "S_MAJOR"),   # 0.8 s overlap — should win
        )
        mapping: dict = {}
        result = tg.assign_speaker(0.0, 1.0, segs, mapping)
        assert mapping.get("S_MAJOR") == result

    def test_multiple_non_overlapping_segments_same_speaker(self) -> None:
        # Two short segments of S_00, one long of S_01
        segs = diar(
            (0.0, 0.3, "S_00"),
            (0.4, 0.6, "S_00"),   # cumulative S_00: 0.3+0.2 = 0.5 s
            (0.0, 0.4, "S_01"),   # S_01: 0.4 s
        )
        mapping: dict = {}
        result = tg.assign_speaker(0.0, 1.0, segs, mapping)
        # S_00 has more total overlap → should win
        assert mapping.get("S_00") == result

    def test_consistent_mapping_across_calls(self) -> None:
        segs = diar((0.0, 2.0, "S_00"), (2.0, 4.0, "S_01"))
        mapping: dict = {}
        label_0 = tg.assign_speaker(0.0, 1.0, segs, mapping)
        label_1 = tg.assign_speaker(2.0, 3.0, segs, mapping)
        # Same speaker returns same label on repeated calls
        assert tg.assign_speaker(0.5, 1.5, segs, mapping) == label_0
        assert label_0 != label_1

    def test_speaker_labels_are_unique(self) -> None:
        segs = diar((0.0, 1.0, "S_A"), (1.0, 2.0, "S_B"), (2.0, 3.0, "S_C"))
        mapping: dict = {}
        labels = {
            tg.assign_speaker(0.1, 0.9, segs, mapping),
            tg.assign_speaker(1.1, 1.9, segs, mapping),
            tg.assign_speaker(2.1, 2.9, segs, mapping),
        }
        assert len(labels) == 3


@pytest.mark.unit
class TestAssignSpeakerLabelNumbering:

    @pytest.mark.parametrize("n_speakers", [1, 2, 3, 5])
    def test_labels_numbered_sequentially(self, n_speakers: int) -> None:
        """Speaker labels must be 'Speaker 1', 'Speaker 2', … in encounter order."""
        segs = [(float(i), float(i + 1), f"S_{i:02d}") for i in range(n_speakers)]
        mapping: dict = {}
        seen: list[str] = []
        for i in range(n_speakers):
            label = tg.assign_speaker(float(i) + 0.1, float(i) + 0.9, segs, mapping)
            seen.append(label)
        assert seen == [f"Speaker {i + 1}" for i in range(n_speakers)]
