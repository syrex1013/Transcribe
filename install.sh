#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║           TRANSCRIBE-AI  ·  Installer                           ║
# ╚══════════════════════════════════════════════════════════════════╝
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/transcribe"
CONFIG_FILE="$CONFIG_DIR/config"
BIN_DEST="/usr/local/bin/transcribe"
LIB_DEST="/usr/local/lib/transcribe_groq.py"

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

# ── Check OS ────────────────────────────────────────────────────────
banner
echo -e "${BOLD}Installing transcribe-ai...${RESET}\n"

# ── ffmpeg ──────────────────────────────────────────────────────────
step "Checking ffmpeg"
if command -v ffmpeg &>/dev/null; then
  ok "ffmpeg found: $(ffmpeg -version 2>&1 | head -1 | cut -d' ' -f3)"
else
  warn "ffmpeg not found — installing via Homebrew"
  if command -v brew &>/dev/null; then
    brew install ffmpeg
    ok "ffmpeg installed"
  else
    fail "Homebrew not found. Install ffmpeg manually: https://ffmpeg.org/download.html"
    exit 1
  fi
fi

# ── Python ──────────────────────────────────────────────────────────
step "Checking Python"
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
  fail "Python 3 not found. Install from https://python.org"
  exit 1
fi
PY_VER=$($PYTHON --version 2>&1)
ok "Found $PY_VER at $PYTHON"

# ── Python packages ─────────────────────────────────────────────────
step "Installing Python dependencies"
$PYTHON -m pip install --quiet --upgrade pip
$PYTHON -m pip install --quiet requests
ok "requests installed"

echo ""
echo -e "  ${YELLOW}Installing pyannote.audio + torch (this may take a few minutes)...${RESET}"
$PYTHON -m pip install --quiet pyannote.audio torch torchaudio && \
  ok "pyannote.audio + torch installed" || \
  warn "pyannote.audio install failed — speaker diarization will be skipped"

# ── Config directory ────────────────────────────────────────────────
step "Setting up config"
mkdir -p "$CONFIG_DIR"
touch "$CONFIG_FILE"
chmod 600 "$CONFIG_FILE"
ok "Config directory: $CONFIG_DIR"

# ── GROQ_API_KEY ────────────────────────────────────────────────────
echo ""
GROQ_KEY=""
# Load existing
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
    # Update or append
    if grep -q "^GROQ_API_KEY=" "$CONFIG_FILE" 2>/dev/null; then
      sed -i.bak "s|^GROQ_API_KEY=.*|GROQ_API_KEY=\"$GROQ_KEY\"|" "$CONFIG_FILE"
    else
      echo "GROQ_API_KEY=\"$GROQ_KEY\"" >> "$CONFIG_FILE"
    fi
    ok "GROQ_API_KEY saved to $CONFIG_FILE"
  else
    warn "Skipped — you can add it later: echo 'GROQ_API_KEY=\"sk_...\"' >> $CONFIG_FILE"
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
step "Installing scripts"
sudo cp "$SCRIPT_DIR/transcribe_groq.py" "$LIB_DEST"
sudo cp "$SCRIPT_DIR/transcribe"         "$BIN_DEST"
sudo chmod +x "$BIN_DEST"
ok "Installed $BIN_DEST"
ok "Installed $LIB_DEST"

# ── Shell profile ───────────────────────────────────────────────────
step "Checking shell profile"
SHELL_RC=""
if [ -n "$ZSH_VERSION" ] || [[ "$SHELL" == */zsh ]]; then
  SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [[ "$SHELL" == */bash ]]; then
  SHELL_RC="$HOME/.bashrc"
fi

SOURCE_LINE="[ -f \"$CONFIG_FILE\" ] && source \"$CONFIG_FILE\""
if [ -n "$SHELL_RC" ]; then
  if ! grep -q "transcribe/config" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# transcribe-ai config" >> "$SHELL_RC"
    echo "$SOURCE_LINE" >> "$SHELL_RC"
    ok "Added config loader to $SHELL_RC"
  else
    ok "Config loader already in $SHELL_RC"
  fi
fi

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✅  transcribe-ai installed successfully!   ${RESET}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Usage:${RESET}"
echo -e "    transcribe recording.mp3 pl"
echo -e "    transcribe recording.mp3 en --no-diarize"
echo -e "    transcribe recording.mp3 de --speakers 3"
echo ""
echo -e "  ${BOLD}Config:${RESET}  $CONFIG_FILE"
echo -e "  ${BOLD}Docs:${RESET}    $(dirname $SCRIPT_DIR)/README.md"
echo ""
if [ -z "$GROQ_KEY" ]; then
  echo -e "  ${YELLOW}⚠️  Add your GROQ_API_KEY to start transcribing:${RESET}"
  echo -e "     echo 'GROQ_API_KEY=\"gsk_...\"' >> $CONFIG_FILE"
  echo ""
fi
echo -e "  Reload your shell: ${BOLD}source $SHELL_RC${RESET}"
echo ""
