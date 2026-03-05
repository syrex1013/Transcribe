#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║           TRANSCRIBE-AI  ·  Installer                           ║
# ╚══════════════════════════════════════════════════════════════════╝
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/transcribe"
CONFIG_FILE="$CONFIG_DIR/config"
LOCAL_BIN_DIR="$HOME/.local/bin"
LOCAL_LIB_DIR="$HOME/.local/lib/transcribe-ai"
SYSTEM_BIN_DIR="/usr/local/bin"
SYSTEM_LIB_DIR="/usr/local/lib"

# ── Colors ──────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
cat << 'EOF'

  ████████╗██████╗  █████╗ ███╗   ██╗███████╗ ██████╗██████╗ ██╗██████╗ ███████╗      █████╗ ██╗
     ██║   ██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔════╝██╔══██╗██║██╔══██╗██╔════╝     ██╔══██╗██║
     ██║   ██████╔╝███████║██╔██╗ ██║███████╗██║     ██████╔╝██║██████╔╝█████╗  █████╗███████║██║
     ██║   ██╔══██╗██╔══██║██║╚██╗██║╚════██║██║     ██╔══██╗██║██╔══██╗██╔══╝  ╚════╝██╔══██║██║
     ██║   ██║  ██║██║  ██║██║ ╚████║███████║╚██████╗██║  ██║██║██████╔╝███████╗      ██║  ██║██║
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═════╝ ╚══════╝      ╚═╝  ╚═╝╚═╝

  Powered by Groq Whisper · pyannote.audio · ffmpeg
  Smart sentence splitting · Auto speaker diarization · Timestamps

EOF
}

step()  { echo -e "${CYAN}${BOLD}▶ $1${RESET}"; }
ok()    { echo -e "${GREEN}  ✅ $1${RESET}"; }
warn()  { echo -e "${YELLOW}  ⚠️  $1${RESET}"; }
fail()  { echo -e "${RED}  ❌ $1${RESET}"; }
info()  { echo -e "     $1"; }

append_if_missing() {
  local file="$1"
  local marker="$2"
  local line="$3"
  touch "$file"
  if ! grep -Fq "$marker" "$file" 2>/dev/null; then
    echo "" >> "$file"
    echo "$line" >> "$file"
    return 0
  fi
  return 1
}

run_sudo_install() {
  if [ "$(id -u)" -eq 0 ]; then
    install "$@"
  else
    sudo install "$@"
  fi
}

install_python_deps() {
  local req_file="$SCRIPT_DIR/requirements.txt"

  "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true
  "$PYTHON" -m pip install --quiet --upgrade pip

  if [ -f "$req_file" ]; then
    if "$PYTHON" -m pip install --quiet -r "$req_file"; then
      return 0
    fi
    warn "System Python package install failed, retrying with --user"
    "$PYTHON" -m pip install --quiet --user -r "$req_file"
    return 0
  fi

  local pkgs=(requests rich pyannote.audio torch torchaudio)
  if "$PYTHON" -m pip install --quiet "${pkgs[@]}"; then
    return 0
  fi
  warn "System Python package install failed, retrying with --user"
  "$PYTHON" -m pip install --quiet --user "${pkgs[@]}"
}

detect_shell_rc() {
  if [ -n "${ZSH_VERSION:-}" ] || [[ "${SHELL:-}" == */zsh ]]; then
    echo "$HOME/.zshrc"
    return 0
  fi
  if [ -n "${BASH_VERSION:-}" ] || [[ "${SHELL:-}" == */bash ]]; then
    echo "$HOME/.bashrc"
    return 0
  fi
  echo "$HOME/.profile"
}

banner
echo -e "${BOLD}Installing transcribe-ai...${RESET}\n"

# ── ffmpeg ──────────────────────────────────────────────────────────
step "Checking ffmpeg"
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "ffmpeg found: $(ffmpeg -version 2>&1 | head -1)"
else
  warn "ffmpeg/ffprobe not found — attempting install via Homebrew"
  if command -v brew >/dev/null 2>&1; then
    brew install ffmpeg
    ok "ffmpeg installed"
  else
    fail "Homebrew not found. Install ffmpeg manually: https://ffmpeg.org/download.html"
    exit 1
  fi
fi

# ── Python ──────────────────────────────────────────────────────────
step "Checking Python"
PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$PYTHON" ]; then
  fail "Python 3 not found. Install from https://python.org"
  exit 1
fi
PY_VER="$($PYTHON --version 2>&1)"
ok "Found $PY_VER at $PYTHON"

# ── Python packages ─────────────────────────────────────────────────
step "Installing Python dependencies (this may take a few minutes)"
if install_python_deps; then
  ok "Dependencies installed (requests, rich, pyannote.audio, torch, torchaudio)"
else
  fail "Could not install required Python dependencies."
  exit 1
fi

# ── Config directory ────────────────────────────────────────────────
step "Setting up config"
mkdir -p "$CONFIG_DIR"
touch "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"
ok "Config directory: $CONFIG_DIR"

# ── GROQ_API_KEY ────────────────────────────────────────────────────
echo ""
GROQ_KEY=""
if grep -q "^GROQ_API_KEY=" "$CONFIG_FILE" 2>/dev/null; then
  GROQ_KEY=$(grep "^GROQ_API_KEY=" "$CONFIG_FILE" | cut -d'"' -f2)
fi
[ -z "$GROQ_KEY" ] && GROQ_KEY="${GROQ_API_KEY:-}"

if [ -n "$GROQ_KEY" ]; then
  ok "GROQ_API_KEY already configured"
else
  echo -e "${CYAN}${BOLD}▶ Groq API Key required${RESET}"
  info "Groq provides FREE Whisper transcription (no credit card)."
  info "Get your key at: ${BOLD}https://console.groq.com${RESET}"
  echo ""
  read -rp "  Paste your GROQ_API_KEY (or press Enter to skip): " GROQ_KEY
  if [ -n "$GROQ_KEY" ]; then
    if grep -q "^GROQ_API_KEY=" "$CONFIG_FILE" 2>/dev/null; then
      sed -i.bak "s|^GROQ_API_KEY=.*|GROQ_API_KEY=\"$GROQ_KEY\"|" "$CONFIG_FILE"
    else
      echo "GROQ_API_KEY=\"$GROQ_KEY\"" >> "$CONFIG_FILE"
    fi
    ok "GROQ_API_KEY saved to $CONFIG_FILE"
  else
    warn "Skipped — you can add it later: echo 'GROQ_API_KEY=\"gsk_...\"' >> $CONFIG_FILE"
  fi
fi

# ── HF_TOKEN ────────────────────────────────────────────────────────
echo ""
HF_KEY=""
if grep -q "^HF_TOKEN=" "$CONFIG_FILE" 2>/dev/null; then
  HF_KEY=$(grep "^HF_TOKEN=" "$CONFIG_FILE" | cut -d'"' -f2)
fi
[ -z "$HF_KEY" ] && HF_KEY="${HF_TOKEN:-}"

if [ -n "$HF_KEY" ]; then
  ok "HF_TOKEN already configured"
else
  echo -e "${CYAN}${BOLD}▶ HuggingFace Token (for speaker diarization)${RESET}"
  info "Required for pyannote speaker detection (free, no credit card)."
  info "1. Get token at: ${BOLD}https://huggingface.co/settings/tokens${RESET}"
  info "2. Accept model terms: ${BOLD}https://huggingface.co/pyannote/speaker-diarization-3.1${RESET}"
  echo ""
  read -rp "  Paste your HF_TOKEN (or press Enter to skip): " HF_KEY
  if [ -n "$HF_KEY" ]; then
    if grep -q "^HF_TOKEN=" "$CONFIG_FILE" 2>/dev/null; then
      sed -i.bak "s|^HF_TOKEN=.*|HF_TOKEN=\"$HF_KEY\"|" "$CONFIG_FILE"
    else
      echo "HF_TOKEN=\"$HF_KEY\"" >> "$CONFIG_FILE"
    fi
    ok "HF_TOKEN saved to $CONFIG_FILE"
  else
    warn "Skipped — speaker diarization will be disabled until HF_TOKEN is set"
  fi
fi
rm -f "$CONFIG_FILE.bak"

# ── Install scripts ─────────────────────────────────────────────────
step "Installing CLI and runtime files"
BIN_DEST=""
LIB_DEST=""
INSTALL_MODE="local"

if [ -w "$SYSTEM_BIN_DIR" ] && [ -w "$SYSTEM_LIB_DIR" ]; then
  install -m 755 "$SCRIPT_DIR/transcribe" "$SYSTEM_BIN_DIR/transcribe"
  install -m 644 "$SCRIPT_DIR/transcribe_groq.py" "$SYSTEM_LIB_DIR/transcribe_groq.py"
  BIN_DEST="$SYSTEM_BIN_DIR/transcribe"
  LIB_DEST="$SYSTEM_LIB_DIR/transcribe_groq.py"
  INSTALL_MODE="system"
elif command -v sudo >/dev/null 2>&1; then
  if run_sudo_install -m 755 "$SCRIPT_DIR/transcribe" "$SYSTEM_BIN_DIR/transcribe" && \
     run_sudo_install -m 644 "$SCRIPT_DIR/transcribe_groq.py" "$SYSTEM_LIB_DIR/transcribe_groq.py"; then
    BIN_DEST="$SYSTEM_BIN_DIR/transcribe"
    LIB_DEST="$SYSTEM_LIB_DIR/transcribe_groq.py"
    INSTALL_MODE="system"
  else
    warn "System install failed. Falling back to user-local install."
  fi
fi

if [ "$INSTALL_MODE" = "local" ]; then
  mkdir -p "$LOCAL_BIN_DIR" "$LOCAL_LIB_DIR"
  install -m 755 "$SCRIPT_DIR/transcribe" "$LOCAL_BIN_DIR/transcribe"
  install -m 644 "$SCRIPT_DIR/transcribe_groq.py" "$LOCAL_LIB_DIR/transcribe_groq.py"
  BIN_DEST="$LOCAL_BIN_DIR/transcribe"
  LIB_DEST="$LOCAL_LIB_DIR/transcribe_groq.py"
fi

ok "Installed CLI: $BIN_DEST"
ok "Installed runtime: $LIB_DEST"

# ── Shell profile ───────────────────────────────────────────────────
step "Updating shell profile"
SHELL_RC="$(detect_shell_rc)"
SOURCE_LINE="[ -f \"$CONFIG_FILE\" ] && source \"$CONFIG_FILE\""
PATH_LINE='export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"'

if append_if_missing "$SHELL_RC" "transcribe-ai config" "# transcribe-ai config"; then
  echo "$SOURCE_LINE" >> "$SHELL_RC"
  ok "Added config loader to $SHELL_RC"
else
  ok "Config loader already in $SHELL_RC"
fi

if append_if_missing "$SHELL_RC" "transcribe-ai path" "# transcribe-ai path"; then
  echo "$PATH_LINE" >> "$SHELL_RC"
  ok "Added PATH update to $SHELL_RC"
else
  ok "PATH update already in $SHELL_RC"
fi

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✅  transcribe-ai installed successfully!   ${RESET}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Install mode:${RESET} $INSTALL_MODE"
echo -e "  ${BOLD}CLI path:${RESET}    $BIN_DEST"
echo -e "  ${BOLD}Runtime path:${RESET} $LIB_DEST"
echo -e "  ${BOLD}Config:${RESET}      $CONFIG_FILE"
echo ""
echo -e "  ${BOLD}Usage:${RESET}"
echo -e "    transcribe recording.mp3 pl"
echo -e "    transcribe recording.mp3 en --no-diarize"
echo -e "    transcribe recording.mp3 de --speakers 3"
echo ""
if [ -z "$GROQ_KEY" ]; then
  echo -e "  ${YELLOW}⚠️  Add your GROQ_API_KEY to start transcribing:${RESET}"
  echo -e "     echo 'GROQ_API_KEY=\"gsk_...\"' >> $CONFIG_FILE"
  echo ""
fi
echo -e "  Reload your shell: ${BOLD}source $SHELL_RC${RESET}"
echo ""
