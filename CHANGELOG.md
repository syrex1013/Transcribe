# Changelog

All notable changes to this project will be documented in this file.

## [0.4.0] - 2026-03-06

### Added
- **Unified release workflow** (`release.yml`): single tag push triggers all publish jobs.
- **PyInstaller binary builds**: standalone `transcribe` executables for Linux x86-64,
  macOS Intel, macOS Apple Silicon, and Windows x86-64 — no Python required.
- **GitHub Releases**: binaries automatically attached to every `v*` release.
- **npm package** (`npm/transcribe-all`): wraps native binaries; `npm install -g transcribe-all`
  downloads the correct binary for the host platform during postinstall.
- **Homebrew auto-update**: `publish-brew.yml` patches `Formula/transcribe-all.rb`
  URL and SHA256 after each release and commits back to the repo.
- **Standalone `publish-brew.yml`** and **`publish-npm.yml`** workflows for manual dispatch.
- `workflow_dispatch:` trigger added to `ci.yml` for on-demand test runs.

### Changed
- Homebrew formula URL updated from `main` branch tarball to tag-based tarball for
  reproducible, versioned installs.
- README updated with npm install instructions, pre-built binary download table,
  release pipeline summary, and additional badges (Release CI, PyPI version, npm version).

## [0.3.0] - 2026-03-06

### Added
- Homebrew formula for `transcribe-all` (`Formula/transcribe-all.rb`).
- Debian package build script (`scripts/build_deb.sh`).
- APT repository metadata build script (`scripts/build_apt_repo.sh`).
- GitHub Actions workflow to publish PyPI releases (`publish-pypi.yml`).
- GitHub Actions workflow to publish APT metadata to GitHub Pages (`publish-apt.yml`).

### Changed
- Renamed package distribution from `transcribe-ai` to `transcribe-all` for pip/Homebrew/APT installs.
- Updated install docs and release checklist for package-manager distribution.
- Installer now supports `apt-get` fallback for automatic `ffmpeg` installation.

## [0.1.0] - 2026-03-05

### Added
- Initial public release structure and docs.
- Release-grade `.gitignore`.
- Professional README with local graphic assets.
- `.env.example` token/config template.
- `RELEASE_CHECKLIST.md` for publish workflow.
- MIT `LICENSE`.

### Changed
- `transcribe` local mode now supports `WHISPER_MODEL_PATH` and no longer uses a machine-specific hardcoded model path.
