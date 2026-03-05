# Installation Guide

## What the installer does

Running `./install.sh` performs all setup required for normal usage:

1. Checks and installs `ffmpeg`/`ffprobe` (via Homebrew if missing)
2. Installs Python dependencies from `requirements.txt`
3. Installs `transcribe` CLI and `transcribe_groq.py` runtime
4. Adds shell profile entries so command is available in terminal sessions
5. Creates secure config file at `~/.config/transcribe/config` (`chmod 600`)

## Install

```bash
chmod +x install.sh transcribe
./install.sh
source ~/.zshrc   # or ~/.bashrc / ~/.profile
```

## Global path behavior

- Preferred install:
  - CLI: `/usr/local/bin/transcribe`
  - Runtime: `/usr/local/lib/transcribe_groq.py`
- Fallback install (no system write access):
  - CLI: `~/.local/bin/transcribe`
  - Runtime: `~/.local/lib/transcribe-ai/transcribe_groq.py`

The installer appends:

```bash
export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
```

to your shell profile so `transcribe` is accessible everywhere.

## Required environment

- Required: `GROQ_API_KEY`
- Optional: `HF_TOKEN`
- Optional (local mode): `WHISPER_MODEL_PATH`

Reference template: `.env.example`

## Verify installation

```bash
command -v transcribe
transcribe --help
```

If the command is not found:

1. Reload shell profile (`source ~/.zshrc` or equivalent)
2. Open a new terminal
3. Confirm `PATH` contains `/usr/local/bin` and/or `~/.local/bin`
