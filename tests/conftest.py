"""
Shared pytest configuration for the transcribe-all test suite.

Heavy optional dependencies (pyannote, torch, torchaudio, requests) are
registered as empty stub modules in sys.modules *before* transcribe_groq is
imported.  This allows the test suite to run in a lean CI environment without
installing GPU/ML packages.

Fixtures defined here are available to every test module automatically.
"""
from __future__ import annotations

import os
import sys
import types

import pytest

# ── Register stubs BEFORE any test module imports transcribe_groq ─────────────
_HEAVY_DEPS = [
    "pyannote",
    "pyannote.audio",
    "torch",
    "torchaudio",
    "requests",
]
for _dep in _HEAVY_DEPS:
    sys.modules.setdefault(_dep, types.ModuleType(_dep))

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import transcribe_groq as tg  # noqa: E402  (stubs already registered above)


# ── Session-scoped module reference ───────────────────────────────────────────

@pytest.fixture(scope="session")
def tg_module():
    """Return the imported transcribe_groq module (loaded once per session)."""
    return tg


# ── Per-test isolated config file ─────────────────────────────────────────────

@pytest.fixture()
def tmp_config(tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    """
    Patch CONFIG_FILE to a fresh path inside a temporary directory.

    The file is NOT pre-created; tests that need an existing config must write
    it themselves.  The path is returned as a ``pathlib.Path`` for convenience.
    """
    cfg = tmp_path / "transcribe" / "config"
    monkeypatch.setattr(tg, "CONFIG_FILE", str(cfg))
    return cfg


# ── Helpers re-exported for test modules ──────────────────────────────────────

def make_word(text: str, start: float, end: float) -> dict:
    """Build a Groq-style word-timestamp dict."""
    return {"word": text, "start": start, "end": end}


def make_segment(text: str, start: float, end: float) -> dict:
    """Build a Groq-style segment dict."""
    return {"text": text, "start": start, "end": end}
