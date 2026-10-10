"""Card detail regressions through the CLI and real plankapy models."""

import re

import httpx
import pytest
from plankapy.v2 import Planka
from typer.testing import CliRunner

from scripts import planka_cli

runner = CliRunner()


@pytest.fixture
def card_schema(monkeypatch):
    schema = {
        "id": "card-123",
        "name": "Ship CLI",
        "description": "Release checklist",
        "boardId": "board-456",
        "listId": "list-789",
        "position": 42,
        "type": "project",
        "dueDate": None,
        "isDueCompleted": False,
        "commentsTotal": 0,
        "createdAt": "2026-01-01T10:00:00Z",
        "updatedAt": "2026-01-02T10:00:00Z",
    }

    def respond(request):
        assert request.method == "GET"
        if request.url.path == "/api/cards/card-123":
            return httpx.Response(200, json={"item": schema, "included": {"attachments": []}})
        if request.url.path == "/api/lists/list-789":
            return httpx.Response(
                200, json={"item": {"id": "list-789", "name": "Ready", "boardId": "board-456"}}
            )
        if request.url.path == "/api/cards/card-123/comments":
            return httpx.Response(200, json={"items": []})
        raise AssertionError(f"Unexpected request: {request.url.path}")

    with httpx.Client(
        base_url="https://planka.example", transport=httpx.MockTransport(respond)
    ) as client:
        session = Planka(client=client)
        monkeypatch.setattr(planka_cli, "get_planka", lambda: session)
        monkeypatch.setattr(
            planka_cli, "get_env_config", lambda: ("https://planka.example", None, None)
        )
        yield schema


@pytest.mark.parametrize(
    ("description", "expected_lines"),
    [
        pytest.param("Release checklist", ["Release checklist"], id="distinct-description"),
        pytest.param(None, ["-"], id="null-description"),
        pytest.param("", ["-"], id="empty-description"),
        pytest.param(
            "Review changelog\nPublish build",
            ["Review changelog", "Publish build"],
            id="multiline-description",
        ),
    ],
)
def test_show_card_displays_schema_description(card_schema, description, expected_lines):
    card_schema["description"] = description
    original_schema = card_schema.copy()

    result = runner.invoke(planka_cli.app, ["cards", "show", "card-123"])

    assert result.exit_code == 0
    assert "Description" in result.output, result.output
    lines = result.output.splitlines()
    description_index = next(
        index for index, line in enumerate(lines) if line.strip().startswith("Description")
    )
    assert lines[description_index].strip().split(maxsplit=1) == ["Description", expected_lines[0]]
    for offset, expected_line in enumerate(expected_lines[1:], start=1):
        assert lines[description_index + offset].strip() == expected_line

    expected_fields = {
        "ID": "card-123",
        "URL": "https://planka.example/boards/board-456/cards/card-123",
        "Name": "Ship CLI",
        "Board ID": "board-456",
        "List": "Ready (list-789)",
        "Position": "42",
        "Type": "project",
        "Due Date": "-",
        "Due Completed": "no",
        "Attachments": "0",
        "Comments": "0",
        "Created At": "2026-01-01 10:00:00+00:00",
        "Updated At": "2026-01-02 10:00:00+00:00",
    }
    for field, value in expected_fields.items():
        assert re.search(
            rf"^\s*{re.escape(field)}\s+{re.escape(value)}\s*$", result.output, re.MULTILINE
        ), result.output
    assert card_schema == original_schema
