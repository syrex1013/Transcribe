# transcribe-all

<p align="center">
  <img src="assets/hero-banner.svg" alt="transcribe-all banner" width="100%" />
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9+-1e3a8a?style=for-the-badge&logo=python&logoColor=ffd43b">
  <img alt="Groq" src="https://img.shields.io/badge/Groq-Whisper%20v3-111827?style=for-the-badge">
  <img alt="pyannote" src="https://img.shields.io/badge/pyannote-Diarization-0f766e?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-166534?style=for-the-badge">
  <a href="https://github.com/syrex1013/Transcribe/actions/workflows/release.yml">
    <img alt="Release" src="https://img.shields.io/github/actions/workflow/status/syrex1013/Transcribe/release.yml?style=for-the-badge&label=Release&logo=github">
  </a>
  <a href="https://pypi.org/project/transcribe-all/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/transcribe-all?style=for-the-badge&logo=pypi&logoColor=white&color=006dad">
  </a>
  <a href="https://www.npmjs.com/package/transcribe-all">
    <img alt="npm" src="https://img.shields.io/npm/v/transcribe-all?style=for-the-badge&logo=npm&color=cb3837">
  </a>
</p>

Cloud-first transcription CLI with optional speaker diarization.
Built for fast hackathon delivery: simple install, practical output, and clear timestamps.

## Why this project

- Fast transcription via Groq Whisper models
- Speaker segmentation via pyannote (optional)
- Clean sentence blocks with timestamp formatting
- Handles large files by splitting and merging automatically
- Works from terminal with one command

<p align="center">
  <img src="assets/pipeline-diagram.svg" alt="Pipeline diagram" width="100%" />
</p>

## Quick start

```bash
git clone https://github.com/syrex1013/Transcribe.git
cd Transcribe
chmod +x install.sh transcribe
./install.sh
```

Transcribe:

```bash
transcribe recording.mp3 en
```

## Easy install (copy/paste)

### Compatibility

| OS | Compatible |
|---|---|
| macOS | ✅ |
| Ubuntu/Debian | ✅ |
| Other Linux distros | ✅ |
| Windows | ✅ |
| WSL (Ubuntu/Debian) | ✅ |

### Install options

#### Homebrew (macOS / Linux)

```bash
brew tap syrex1013/transcribe-all https://github.com/syrex1013/Transcribe
brew install transcribe-all
```

#### apt-get (Debian / Ubuntu)

```bash
echo "deb [trusted=yes] https://syrex1013.github.io/Transcribe/apt ./" \
  | sudo tee /etc/apt/sources.list.d/transcribe-all.list
sudo apt-get update
sudo apt-get install -y transcribe-all
```

#### pip (all platforms)

```bash
pip install transcribe-all
```

Optional diarization extras:

```bash
pip install "transcribe-all[diarize]"
```

#### npm (all platforms — no Python required)

```bash
npm install -g transcribe-all
```

The npm package downloads the correct pre-built native binary for your OS/arch
during installation. No Python or pip needed.

#### Pre-built binaries (manual download)

Grab the right binary for your platform from the
[latest GitHub Release](https://github.com/syrex1013/Transcribe/releases/latest):

| Platform | Binary |
|----------|--------|
| Linux x86-64 | `transcribe-linux-x64` |
| macOS Apple Silicon | `transcribe-darwin-arm64` |
| Windows x86-64 | `transcribe-windows-x64.exe` |

```bash
# Linux / macOS example
chmod +x transcribe-linux-x64
sudo mv transcribe-linux-x64 /usr/local/bin/transcribe
transcribe --help
```

Verify any install method:

```bash
transcribe --help
```

Full install details and troubleshooting: [INSTALLATION.md](INSTALLATION.md)

## Usage

```bash
# basic
transcribe input.mp3 en

# expected speaker count
transcribe interview.mp3 en --speakers 2

# disable diarization
transcribe lecture.mp3 en --no-diarize

# local whisper.cpp mode
transcribe input.mp3 en --local
```

## Configuration

The tool reads tokens from environment variables and from:

```text
~/.config/transcribe/config
```

Required:

- `GROQ_API_KEY`

Optional:

- `HF_TOKEN` for pyannote speaker diarization
- `WHISPER_MODEL_PATH` for `--local` mode (path to `ggml-large-v3.bin`)

Use `.env.example` as reference.

## Example output

```text
-- Speaker 1 ----------------------------------------
[00:00]  Welcome to the demo recording.
[00:04]  Today we will test HTTP interception in Burp.

-- Speaker 2 ----------------------------------------
[01:32]  Open the Proxy tab and enable intercept.
[01:38]  Now inspect headers and session cookies.
```

## Project layout

```text
.
├── transcribe              # CLI entrypoint (bash wrapper)
├── transcribe_groq.py      # Core transcription + diarization pipeline
├── npm/                    # npm package (binary distribution)
├── Formula/                # Homebrew formula
├── scripts/                # Debian packaging scripts
├── install.sh              # Installer for dependencies and shell setup
├── INSTALLATION.md         # Detailed install and PATH guide
├── .env.example            # Environment variable template
├── CHANGELOG.md
├── RELEASE_CHECKLIST.md
└── assets/
    ├── hero-banner.svg
    └── pipeline-diagram.svg
```

## Release pipeline

Every `v*` tag triggers a fully automated release:

| Step | What happens |
|------|-------------|
| **Binaries** | PyInstaller builds for Linux, macOS (Intel + Apple Silicon), and Windows |
| **GitHub Release** | All binaries attached automatically |
| **PyPI** | Wheel + sdist published via OIDC trusted publishing |
| **APT repo** | `.deb` package rebuilt and pushed to GitHub Pages |
| **Homebrew** | Formula URL and SHA256 patched and committed automatically |
| **npm** | Binary-wrapper package published to the npm registry |

## Installation guide

The installer is designed to:

- Install required dependencies: `ffmpeg`, `ffprobe`, Python packages from `requirements.txt`
- Install `transcribe` globally in `/usr/local/bin` when possible
- Fallback to user-local install in `~/.local/bin` when system install is unavailable
- Update shell profile so `transcribe` is available everywhere
- Persist token config in `~/.config/transcribe/config`

## License

MIT. See [LICENSE](LICENSE).
