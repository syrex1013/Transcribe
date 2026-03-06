#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
DEB_DIR="$DIST_DIR/deb"

if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "Error: dpkg-deb is required to build .deb packages." >&2
  exit 1
fi

VERSION="$(
  cd "$ROOT_DIR"
  python - <<'PY'
import pathlib
import re

pyproject = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
if not match:
    raise SystemExit("Could not read version from pyproject.toml")
print(match.group(1))
PY
)"

STAGE_DIR="$(mktemp -d)"
PKG_ROOT="$STAGE_DIR/transcribe-all_${VERSION}_all"
trap 'rm -rf "$STAGE_DIR"' EXIT

mkdir -p "$DEB_DIR"
mkdir -p "$PKG_ROOT/DEBIAN"
mkdir -p "$PKG_ROOT/usr/bin"
mkdir -p "$PKG_ROOT/usr/lib/transcribe-all"
mkdir -p "$PKG_ROOT/usr/share/doc/transcribe-all"

install -m 755 "$ROOT_DIR/transcribe" "$PKG_ROOT/usr/bin/transcribe"
install -m 644 "$ROOT_DIR/transcribe_groq.py" "$PKG_ROOT/usr/lib/transcribe-all/transcribe_groq.py"
install -m 644 "$ROOT_DIR/README.md" "$PKG_ROOT/usr/share/doc/transcribe-all/README.md"
install -m 644 "$ROOT_DIR/LICENSE" "$PKG_ROOT/usr/share/doc/transcribe-all/LICENSE"

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: transcribe-all
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Maintainer: transcribe-all maintainers <opensource@transcribe-all.dev>
Depends: bash, ffmpeg, python3, python3-requests, python3-rich
Description: CLI audio transcription via Groq Whisper
 transcribe-all is a terminal-first transcription CLI built around Groq Whisper.
 It supports timestamped text output and optional speaker diarization.
EOF

OUT_FILE="$DEB_DIR/transcribe-all_${VERSION}_all.deb"
dpkg-deb --build "$PKG_ROOT" "$OUT_FILE" >/dev/null

echo "Built $OUT_FILE"
