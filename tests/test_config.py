"""
Tests for load_config() and save_config().

Both functions operate on the CONFIG_FILE path, which is patched to a
temporary location by the ``tmp_config`` fixture (defined in conftest.py).
"""
from __future__ import annotations

import os
import stat

import pytest
import transcribe_groq as tg


# ─────────────────────────────────────────────────────────────────────────────
# load_config
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestLoadConfig:

    def test_missing_file_does_not_raise(self, tmp_config) -> None:
        """load_config is a no-op when the file does not exist."""
        assert not tmp_config.exists()
        tg.load_config()  # must not raise

    def test_sets_env_variable(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('MY_LOAD_KEY="hello123"\n')
        monkeypatch.delenv("MY_LOAD_KEY", raising=False)
        tg.load_config()
        assert os.environ.get("MY_LOAD_KEY") == "hello123"

    def test_strips_double_quotes(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('QUOTED_KEY="stripped"\n')
        monkeypatch.delenv("QUOTED_KEY", raising=False)
        tg.load_config()
        assert os.environ["QUOTED_KEY"] == "stripped"

    def test_strips_single_quotes(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text("SINGLE_KEY='value'\n")
        monkeypatch.delenv("SINGLE_KEY", raising=False)
        tg.load_config()
        assert os.environ["SINGLE_KEY"] == "value"

    def test_skips_comment_lines(self, tmp_config) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text("# COMMENTED_KEY=value\n")
        tg.load_config()
        assert "COMMENTED_KEY" not in os.environ

    def test_skips_blank_lines(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('\nBLANK_AROUND="yes"\n\n')
        monkeypatch.delenv("BLANK_AROUND", raising=False)
        tg.load_config()
        assert os.environ["BLANK_AROUND"] == "yes"

    def test_does_not_override_existing_env(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('OVERRIDE_KEY="from_file"\n')
        monkeypatch.setenv("OVERRIDE_KEY", "from_env")
        tg.load_config()
        assert os.environ["OVERRIDE_KEY"] == "from_env"

    def test_multiple_keys_loaded(self, tmp_config, monkeypatch) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('KEY_A="alpha"\nKEY_B="beta"\n')
        monkeypatch.delenv("KEY_A", raising=False)
        monkeypatch.delenv("KEY_B", raising=False)
        tg.load_config()
        assert os.environ["KEY_A"] == "alpha"
        assert os.environ["KEY_B"] == "beta"

    def test_value_with_equals_sign(self, tmp_config, monkeypatch) -> None:
        """Values may themselves contain '=' — only the first '=' is the separator."""
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('TOKEN_KEY="abc=def"\n')
        monkeypatch.delenv("TOKEN_KEY", raising=False)
        tg.load_config()
        assert os.environ["TOKEN_KEY"] == "abc=def"


# ─────────────────────────────────────────────────────────────────────────────
# save_config
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestSaveConfig:

    def test_creates_file_and_parent_dirs(self, tmp_config) -> None:
        assert not tmp_config.exists()
        tg.save_config("NEW_KEY", "new_value")
        assert tmp_config.exists()

    def test_written_content_format(self, tmp_config) -> None:
        tg.save_config("FORMAT_KEY", "format_value")
        assert 'FORMAT_KEY="format_value"' in tmp_config.read_text()

    def test_appends_new_key(self, tmp_config) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('EXISTING="yes"\n')
        tg.save_config("APPENDED_KEY", "appended")
        content = tmp_config.read_text()
        assert 'EXISTING="yes"' in content
        assert 'APPENDED_KEY="appended"' in content

    def test_updates_existing_key(self, tmp_config) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('UPDATE_ME="old"\n')
        tg.save_config("UPDATE_ME", "new")
        content = tmp_config.read_text()
        assert 'UPDATE_ME="new"' in content
        assert "old" not in content

    def test_update_preserves_other_keys(self, tmp_config) -> None:
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text('KEEP_ME="safe"\nCHANGE_ME="old"\n')
        tg.save_config("CHANGE_ME", "new")
        content = tmp_config.read_text()
        assert 'KEEP_ME="safe"' in content
        assert 'CHANGE_ME="new"' in content

    def test_empty_string_value(self, tmp_config) -> None:
        tg.save_config("EMPTY_KEY", "")
        assert 'EMPTY_KEY=""' in tmp_config.read_text()

    def test_value_with_special_characters(self, tmp_config) -> None:
        tg.save_config("SPECIAL_KEY", "val=ue!@#")
        assert 'SPECIAL_KEY="val=ue!@#"' in tmp_config.read_text()

    @pytest.mark.skipif(os.name == "nt", reason="chmod not meaningful on Windows")
    def test_file_permissions_are_600(self, tmp_config) -> None:
        tg.save_config("PERM_KEY", "perm_value")
        mode = stat.S_IMODE(tmp_config.stat().st_mode)
        assert mode == 0o600


# ─────────────────────────────────────────────────────────────────────────────
# Round-trip
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestConfigRoundTrip:

    def test_save_then_load(self, tmp_config, monkeypatch) -> None:
        tg.save_config("ROUND_TRIP_KEY", "round_trip_value")
        monkeypatch.delenv("ROUND_TRIP_KEY", raising=False)
        tg.load_config()
        assert os.environ.get("ROUND_TRIP_KEY") == "round_trip_value"

    def test_overwrite_then_load(self, tmp_config, monkeypatch) -> None:
        tg.save_config("OW_KEY", "first")
        tg.save_config("OW_KEY", "second")
        monkeypatch.delenv("OW_KEY", raising=False)
        tg.load_config()
        assert os.environ.get("OW_KEY") == "second"
