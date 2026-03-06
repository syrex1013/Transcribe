#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DEB_DIR="${1:-$ROOT_DIR/dist/deb}"
OUT_DIR="${2:-$ROOT_DIR/dist/apt}"

if ! command -v dpkg-scanpackages >/dev/null 2>&1; then
  echo "Error: dpkg-scanpackages is required (package: dpkg-dev)." >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
find "$OUT_DIR" -mindepth 1 -maxdepth 1 -type f \( -name "*.deb" -o -name "Packages" -o -name "Packages.gz" \) -delete

shopt -s nullglob
deb_files=("$DEB_DIR"/*.deb)
shopt -u nullglob

if [ "${#deb_files[@]}" -eq 0 ]; then
  echo "Error: No .deb files found in $DEB_DIR" >&2
  exit 1
fi

cp "${deb_files[@]}" "$OUT_DIR/"

(
  cd "$OUT_DIR"
  dpkg-scanpackages --multiversion . /dev/null > Packages
  gzip -9c Packages > Packages.gz
)

echo "APT repo metadata generated in $OUT_DIR"
