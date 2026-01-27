---
name: planka-cli
description: Working agreement for maintaining CLI behavior and documentation alignment.
---

# AGENTS

## Documentation parity rule

The CLI implementation, `SKILL.md`, and any other documentation must match at all times.

If you change any CLI command, option, output description, or behavior:
- Update `SKILL.md` in the same change.
- Update any other docs or examples to match the implementation.

If you change documentation:
- Ensure the CLI implementation already matches.
- If not, update the implementation in the same change.

No change is complete until code and docs are consistent.
