# Installation Guide

## macOS / Linux

### What the installer does

Running `./install.sh` performs all setup required for normal usage:

1. Checks and installs `ffmpeg`/`ffprobe` (via Homebrew if missing)
2. Installs Python dependencies from `requirements.txt`
3. Installs `transcribe` CLI and `transcribe_groq.py` runtime
4. Adds shell profile entries so the command is available in new terminals
5. Creates a secure config file at `~/.config/transcribe/config` (`chmod 600`)

### Install

```bash
chmod +x install.sh transcribe
./install.sh
source ~/.zshrc   # or ~/.bashrc / ~/.profile
```

### Global path behavior

- Preferred install:
  - CLI: `/usr/local/bin/transcribe`
  - Runtime: `/usr/local/lib/transcribe_groq.py`
- Fallback install (no system write access):
  - CLI: `~/.local/bin/transcribe`
  - Runtime: `~/.local/lib/transcribe-ai/transcribe_groq.py`

The installer appends `export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"` to your shell profile.

---

## Windows

### Prerequisites

1. **Python 3.9+** — download from <https://python.org> (check *Add to PATH* during install)
2. **ffmpeg** — install via one of:
   ```
   winget install Gyan.FFmpeg
   choco install ffmpeg
   scoop install ffmpeg
   ```

### Install (PowerShell)

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\install.ps1
```

The installer:
- Installs Python dependencies with `pip`
- Registers the `transcribe` command via `pip install -e .`
- Saves API keys to `%APPDATA%\transcribe\config`

After install, **open a new terminal** for the `transcribe` command to be available.

### Manual install (any platform)

```bash
pip install -e .          # installs the transcribe entry-point
pip install -r requirements.txt   # install all runtime deps
```

---

## Required environment

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Groq Whisper transcription |
| `HF_TOKEN` | Optional | Speaker diarization (pyannote) |
| `WHISPER_MODEL_PATH` | Optional | Local whisper.cpp mode |

Reference template: `.env.example`

---

## Verify installation

```bash
transcribe --help
```

If the command is not found:

- **macOS/Linux**: reload shell profile (`source ~/.zshrc` or equivalent), then confirm `PATH` contains `/usr/local/bin` and/or `~/.local/bin`
- **Windows**: open a new terminal window (the PATH is updated for new sessions only)
