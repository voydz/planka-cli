# Tap automation

This repo includes a GitHub Actions workflow that builds a macOS release asset and
opens a formula bump PR in the tap repo using `brew bump-formula-pr`.

## One-time setup (tap bootstrap)

Create the tap repo using Homebrew:

```bash
brew tap-new voydz/homebrew-tap
```

Copy the `Formula/` contents from this repo's `homebrew-tap/` folder into the new
tap repo, commit, and push to GitHub.

## Required secrets

Add a repository secret in this repo:

- `HOMEBREW_GITHUB_API_TOKEN`: a GitHub PAT with access to the private tap repo
  (needs `repo` scope for a private repository).

## Release flow

Create a GitHub release in `voydz/planka-cli` with a tag like `v0.1.0`. The
workflow will:

- build the binary with PyInstaller
- upload `planka-cli-<version>-macos.tar.gz` to the release
- run `brew bump-formula-pr` against `voydz/homebrew-tap`
