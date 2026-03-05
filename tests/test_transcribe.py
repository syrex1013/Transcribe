"""
Unit tests for transcribe_groq pure utility functions.
No API keys, ffmpeg, torch, or network access required.
"""
import os
import sys
import tempfile
import types

import pytest

# ── Stub heavy optional deps so the module can be imported in CI ──────
for _mod in ["pyannote", "pyannote.audio", "torch", "torchaudio", "requests"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = types.ModuleType(_mod)

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import transcribe_groq as tg  # noqa: E402


# ─────────────────────────────────────────────────────────────
# fmt_ts
# ─────────────────────────────────────────────────────────────

class TestFmtTs:
    def test_seconds_only(self):
        assert tg.fmt_ts(65) == "[01:05]"

    def test_zero(self):
        assert tg.fmt_ts(0) == "[00:00]"

    def test_with_hours(self):
        assert tg.fmt_ts(3661) == "[01:01:01]"

    def test_exactly_one_hour(self):
        assert tg.fmt_ts(3600) == "[01:00:00]"

    def test_fractional_truncated(self):
        # float input: int() truncates
        assert tg.fmt_ts(90.9) == "[01:30]"


# ─────────────────────────────────────────────────────────────
# _clean
# ─────────────────────────────────────────────────────────────

class TestClean:
    def test_collapses_whitespace(self):
        assert tg._clean("hello   world") == "Hello world"

    def test_capitalises_first_letter(self):
        assert tg._clean("lowercase") == "Lowercase"

    def test_already_clean(self):
        assert tg._clean("Already clean.") == "Already clean."

    def test_empty_string(self):
        assert tg._clean("") == ""

    def test_strips_leading_trailing(self):
        assert tg._clean("  spaces  ") == "Spaces"

    def test_newlines_collapsed(self):
        assert tg._clean("line\nbreak") == "Line break"


# ─────────────────────────────────────────────────────────────
# build_sentences  (word-level)
# ─────────────────────────────────────────────────────────────

class TestBuildSentences:
    def _word(self, text, start, end):
        return {"word": text, "start": start, "end": end}

    def test_empty_inputs(self):
        assert tg.build_sentences([], [], 0) == []

    def test_single_word(self):
        words = [self._word("Hello.", 0.0, 0.5)]
        result = tg.build_sentences(words, [])
        assert len(result) == 1
        assert result[0]["text"] == "Hello."

    def test_time_offset_applied(self):
        words = [self._word("Hi.", 1.0, 1.5)]
        result = tg.build_sentences(words, [], time_offset=10.0)
        assert result[0]["start"] == pytest.approx(11.0)
        assert result[0]["end"] == pytest.approx(11.5)

    def test_splits_on_long_gap(self):
        words = [
            self._word("First.", 0.0, 0.5),
            self._word("Second.", 2.0, 2.5),   # gap 1.5s > SPLIT_GAP_MIN
        ]
        result = tg.build_sentences(words, [])
        assert len(result) == 2

    def test_merges_short_gap(self):
        words = [
            self._word("hello", 0.0, 0.3),
            self._word("world", 0.5, 0.8),   # gap 0.2s < MERGE_GAP_MAX
        ]
        result = tg.build_sentences(words, [])
        assert len(result) == 1
        assert "hello" in result[0]["text"].lower()

    def test_falls_back_to_segments(self):
        segments = [{"text": " segment one.", "start": 0.0, "end": 2.0}]
        result = tg.build_sentences([], segments)
        assert len(result) == 1
        assert result[0]["text"] == "Segment one."


# ─────────────────────────────────────────────────────────────
# assign_speaker
# ─────────────────────────────────────────────────────────────

class TestAssignSpeaker:
    def test_no_diar_segs(self):
        assert tg.assign_speaker(0, 1, None, {}) is None
        assert tg.assign_speaker(0, 1, [], {}) is None

    def test_basic_assignment(self):
        segs = [(0.0, 2.0, "SPEAKER_00")]
        mapping = {}
        spk = tg.assign_speaker(0.0, 1.0, segs, mapping)
        assert spk == "Speaker 1"
        assert "SPEAKER_00" in mapping

    def test_consistent_mapping(self):
        segs = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
        mapping = {}
        s1 = tg.assign_speaker(0.0, 1.0, segs, mapping)
        s2 = tg.assign_speaker(2.0, 3.0, segs, mapping)
        assert s1 != s2
        assert s1 == tg.assign_speaker(0.5, 1.5, segs, mapping)

    def test_no_overlap_returns_none(self):
        segs = [(5.0, 7.0, "SPEAKER_00")]
        assert tg.assign_speaker(0.0, 1.0, segs, {}) is None

    def test_votes_for_majority(self):
        segs = [
            (0.0, 0.5, "SPEAKER_00"),   # 0.5 s overlap
            (0.0, 1.0, "SPEAKER_01"),   # 1.0 s overlap → wins
        ]
        mapping = {}
        spk = tg.assign_speaker(0.0, 1.0, segs, mapping)
        assert spk == "Speaker 1"  # SPEAKER_01 mapped first as "Speaker 1"
        # The winner should be SPEAKER_01 (more overlap)
        assert mapping.get("SPEAKER_01") == spk


# ─────────────────────────────────────────────────────────────
# format_output
# ─────────────────────────────────────────────────────────────

class TestFormatOutput:
    def test_no_diarization(self):
        sents = [{"start": 0, "end": 1, "text": "Hello world."}]
        out = tg.format_output(sents, None)
        assert "Hello world." in out
        assert "[00:00]" in out

    def test_speaker_header_inserted(self):
        sents = [
            {"start": 0.0, "end": 1.0, "text": "Hi there."},
            {"start": 2.0, "end": 3.0, "text": "Hello back."},
        ]
        diar = [(0.0, 1.5, "SPK_A"), (1.5, 3.5, "SPK_B")]
        out = tg.format_output(sents, diar)
        assert "Speaker 1" in out
        assert "Speaker 2" in out

    def test_same_speaker_no_duplicate_header(self):
        sents = [
            {"start": 0.0, "end": 1.0, "text": "First."},
            {"start": 1.5, "end": 2.5, "text": "Second."},
        ]
        diar = [(0.0, 3.0, "SPK_A")]
        out = tg.format_output(sents, diar)
        assert out.count("Speaker 1") == 1


# ─────────────────────────────────────────────────────────────
# load_config / save_config
# ─────────────────────────────────────────────────────────────

class TestConfig:
    def test_load_config_sets_env(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config"
        cfg.write_text('MY_TEST_KEY="hello123"\n')
        monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
        monkeypatch.delenv("MY_TEST_KEY", raising=False)
        tg.load_config()
        assert os.environ.get("MY_TEST_KEY") == "hello123"

    def test_load_config_skips_comments(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config"
        cfg.write_text("# THIS_IS_A_COMMENT=value\n")
        monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
        tg.load_config()
        assert "THIS_IS_A_COMMENT" not in os.environ

    def test_load_config_does_not_override_existing_env(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config"
        cfg.write_text('OVERRIDE_KEY="from_file"\n')
        monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
        monkeypatch.setenv("OVERRIDE_KEY", "from_env")
        tg.load_config()
        assert os.environ["OVERRIDE_KEY"] == "from_env"

    def test_save_config_creates_file(self, tmp_path, monkeypatch):
        cfg = tmp_path / "subdir" / "config"
        monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
        tg.save_config("SAVE_KEY", "save_val")
        content = cfg.read_text()
        assert 'SAVE_KEY="save_val"' in content

    def test_save_config_updates_existing_key(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config"
        cfg.write_text('UPDATE_KEY="old"\n')
        monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
        tg.save_config("UPDATE_KEY", "new")
        content = cfg.read_text()
        assert 'UPDATE_KEY="new"' in content
        assert "old" not in content
