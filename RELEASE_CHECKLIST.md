# Release Checklist

## Pre-release
- [ ] Confirm `README.md` commands still match current behavior.
- [ ] Verify `install.sh` on a clean machine/user profile.
- [ ] Run smoke tests:
  - [ ] `bash -n transcribe`
  - [ ] `bash -n install.sh`
  - [ ] `python3 -m py_compile transcribe_groq.py`
- [ ] Ensure no secrets are committed (`.env`, API keys, tokens).
- [ ] Update version and changelog entry.

## Tag and publish
- [ ] Create annotated tag (example): `git tag -a v0.1.0 -m "v0.1.0"`
- [ ] Push code and tags:
  - [ ] `git push origin main`
  - [ ] `git push origin --tags`
- [ ] Create GitHub/GitLab release notes from `CHANGELOG.md`.

## Post-release
- [ ] Verify installer docs with live repository URL.
- [ ] Confirm issue templates and labels are ready (if used).
- [ ] Add follow-up tasks to roadmap.
