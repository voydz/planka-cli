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

Requirements: A Planka account. For Homebrew installs, macOS + Homebrew. For source/pipx
installs, Python 3.11+.

### Install (Homebrew, recommended)

```bash
brew tap voydz/homebrew-tap
brew install planka-cli
```

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

`login` stores credentials in a `.env` file next to the `planka-cli` binary (or next to
`scripts/planka_cli.py` when running from source). You can also set credentials via
environment variables:

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

planka-cli cards create <LIST_ID> "Card title" --description "Details"
planka-cli cards update <CARD_ID> --name "New title"
planka-cli cards delete <CARD_ID>

planka-cli notifications all
planka-cli notifications unread
```

## Maintainers

Developer docs live in `docs/`. Release automation notes are in `docs/tap-automation.md`.

### Local dev

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Project layout

- `scripts/planka_cli.py` CLI entrypoint
- `docs/` supporting documentation
- `pyproject.toml` packaging metadata
- `Makefile` helpers for setup and binary builds

### Development

```bash
make setup
make run
make build
```

### TBD

- Release workflow only builds the macOS binary.
- Release workflow assumes a GitHub release is already published.
- No signing/notarization or multi-platform release assets yet.
