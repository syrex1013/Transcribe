# Changelog

All notable changes to this project will be documented in this file.

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
