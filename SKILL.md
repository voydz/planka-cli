---
name: planka
description: Manage Planka (Kanban) projects, boards, lists, cards, and notifications via a custom Python CLI.
metadata: {"clawdbot":{"emoji":"📋","requires":{"bins":["python3"],"env":["PLANKA_URL","PLANKA_USERNAME","PLANKA_PASSWORD"]}}}
---

# Planka CLI

This skill provides a CLI wrapper around the `plankapy` library to interact with a Planka instance.

## Setup

1.  **Dependencies:**
    Navigate to the skill's scripts directory and install dependencies:
    ```bash
    cd scripts/
    pip install -r requirements.txt
    ```

2.  **Configuration:**
    Use the `login` command to store credentials in a `.env` file next to the binary
    (or next to `scripts/planka_cli.py` when running from source):
    ```bash
    planka-cli login --url https://planka.example --username alice --password secret
    # or: python3 scripts/planka_cli.py login --url https://planka.example --username alice --password secret
    ```

## Usage

Run the CLI using Python from the `scripts` directory (or referenced via absolute path):

```bash
# Check connection
python3 scripts/planka_cli.py status

# Save credentials next to the binary/script
python3 scripts/planka_cli.py login --url https://planka.example --username alice --password secret

# Remove stored credentials
python3 scripts/planka_cli.py logout

# List Projects
python3 scripts/planka_cli.py projects list

# List Boards (optionally by project ID)
python3 scripts/planka_cli.py boards list [PROJECT_ID]

# List Lists in a Board
python3 scripts/planka_cli.py lists list <BOARD_ID>

# List Cards in a List
python3 scripts/planka_cli.py cards list <LIST_ID>

# Create a Card
python3 scripts/planka_cli.py cards create <LIST_ID> "Card title"

# Update a Card
python3 scripts/planka_cli.py cards update <CARD_ID> --name "New title"

# Delete a Card
python3 scripts/planka_cli.py cards delete <CARD_ID>

# Notifications
python3 scripts/planka_cli.py notifications all
python3 scripts/planka_cli.py notifications unread
```

## Examples

**List all boards:**
```bash
python3 scripts/planka_cli.py boards list
```

**Show cards in list ID 42:**
```bash
python3 scripts/planka_cli.py cards list 42
```

**Create a card in list ID 42:**
```bash
python3 scripts/planka_cli.py cards create 42 "Ship CLI"
```

**Mark a card done by updating its name:**
```bash
python3 scripts/planka_cli.py cards update <CARD_ID> --name "Done: Ship CLI"
```
