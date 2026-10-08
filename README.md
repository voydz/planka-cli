# Planka CLI

[![Release](https://img.shields.io/github/v/release/voydz/planka-cli)](https://github.com/voydz/planka-cli/releases)
[![Homebrew Tap](https://img.shields.io/badge/homebrew-voydz%2Fhomebrew--tap-blue?logo=homebrew)](https://github.com/voydz/homebrew-tap)

Cut through the UI and drive your Planka boards from the terminal. This CLI lets you
scan work, create cards, and stay on top of notifications with fast, scriptable commands.

## Why it exists

- Keep momentum without context switching to the browser.
- Script common workflows (triage, cleanup, nightly status pulls).
- Work with Planka from any machine that has Python installed.

## Quick start

Requirements: A Planka account. For Homebrew installs, macOS (Apple Silicon or Intel) or
Linux (x86_64 or arm64, glibc 2.28+) with Homebrew. For source/pipx installs, Python 3.11+.

### Install (Homebrew, recommended)

```bash
brew tap voydz/homebrew-tap
brew install planka-cli
```

Prebuilt binaries are also attached to each
[GitHub release](https://github.com/voydz/planka-cli/releases) as
`planka-cli-<version>-<os>-<arch>.tar.gz` for `macos-arm64`, `macos-x86_64`, `linux-x86_64`
and `linux-arm64`.

### Install (other options)

```bash
# Install from GitHub
pipx install git+https://github.com/voydz/planka-cli
```

### Login

```bash
planka-cli login --url https://planka.example --username alice --password secret
```

### Run

```bash
planka-cli status
planka-cli projects list
planka-cli boards list
```

## Authentication

`login` stores credentials in `~/.config/planka-cli/tokens/credentials.json` by default.
Override with `--tokenstore PATH` or the `PLANKATOKENS` environment variable. You can also
set credentials via environment variables. Note: `--tokenstore` is a global option and
must appear before the command name.

```bash
export PLANKA_URL=https://planka.example
export PLANKA_USERNAME=alice
export PLANKA_PASSWORD=secret
```

## Common commands

```bash
planka-cli
planka-cli status
planka-cli login --url https://planka.example --username alice --password secret
planka-cli logout

planka-cli projects list
planka-cli boards list [PROJECT_ID]
planka-cli lists list <BOARD_ID>
planka-cli cards list <LIST_ID>
planka-cli cards show <CARD_ID>

planka-cli cards create <LIST_ID> "Card title" --description "Details"
planka-cli cards update <CARD_ID> --name "New title"
planka-cli cards delete <CARD_ID>

planka-cli notifications all
planka-cli notifications unread
```

## Maintainers

### Local dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Project layout

- `scripts/planka_cli.py` CLI entrypoint
- `scripts/pyi_rth_plankapy.py` PyInstaller runtime hook
- `planka-cli.spec` PyInstaller spec (committed for reproducible builds)
- `packaging/planka-cli.rb.tmpl` Homebrew formula template, rendered by the release workflow
- `pyproject.toml` packaging metadata
- `Makefile` helpers for setup, binary builds and packaging

### Development

```bash
make setup
make run
make lint
make test
make check
make build     # PyInstaller binary in dist/planka-cli
make smoke     # build + run --help in a clean environment
make package   # build + dist/planka-cli-<version>-<os>-<arch>.tar.gz (+ .sha256)
```

### Release

PyInstaller cannot cross-compile, so the release workflow (`.github/workflows/release.yml`)
builds the binary on one runner per target when a GitHub release is published:

| Target         | Runner                                        |
| -------------- | --------------------------------------------- |
| `macos-arm64`  | `macos-14`                                    |
| `macos-x86_64` | `macos-15-intel`                              |
| `linux-x86_64` | `quay.io/pypa/manylinux_2_28_x86_64` container |
| `linux-arm64`  | `quay.io/pypa/manylinux_2_28_aarch64` container |

Linux builds run inside manylinux containers so the glibc floor is 2.28 (Debian 11+,
Ubuntu 20.04+, RHEL 8+); the resulting x86_64 binary is verified on `debian:11`,
`ubuntu:22.04` and `ubuntu:24.04` before anything is published. The tarballs are then
attached to the release and `packaging/planka-cli.rb.tmpl` is rendered with the four
checksums and pushed to `voydz/homebrew-tap`.

To cut a release, bump `version` in `pyproject.toml` and publish a `vX.Y.Z` GitHub release.

### TBD

- No code signing/notarization of the macOS binaries yet.
