"""Comment creation through configured authentication and the real SDK."""

import json
from copy import deepcopy

import httpx
import pytest
from plankapy.v2 import Planka
from typer.testing import CliRunner

from scripts import planka_cli

runner = CliRunner()


@pytest.fixture
def comment_api(monkeypatch, tmp_path):
    state = {
        "requests": [],
        "card": {
            "id": "card-123",
            "name": "Ship CLI",
            "description": "Keep this description",
            "listId": "list-456",
            "position": 42,
            "dueDate": "2026-12-01T10:00:00Z",
            "isDueCompleted": False,
            "type": "project",
        },
        "comments": [{"id": "old-comment", "text": "Keep this comment"}],
    }

    def respond(request):
        state["requests"].append(request)
        if request.method == "POST" and request.url.path == "/api/access-tokens":
            if state.get("login_status", 200) >= 400:
                return httpx.Response(
                    state["login_status"],
                    json={"code": "E_UNAUTHORIZED", "message": "Login denied"},
                )
            return httpx.Response(200, json={"item": "test-token"})
        if request.method == "GET" and request.url.path == "/api/users/me":
            return httpx.Response(200, json={"item": {"id": "user-789", "role": "viewer"}})
        if request.method == "POST" and request.url.path == "/api/cards/card-123/comments":
            if "transport_error" in state:
                raise state["transport_error"]("Simulated transport failure", request=request)
            if "reply" in state:
                return httpx.Response(200, json=state["reply"])
            if "raw_reply" in state:
                return httpx.Response(200, content=state["raw_reply"])
            if state.get("status", 200) >= 400:
                code = {
                    400: "E_MISSING_OR_INVALID_PARAMS",
                    401: "E_UNAUTHORIZED",
                    403: "E_FORBIDDEN",
                    404: "E_NOT_FOUND",
                }.get(state["status"], "E_ERROR")
                return httpx.Response(
                    state["status"], json={"code": code, "message": "Request rejected"}
                )
            comment = {
                "id": "comment-987",
                "cardId": "card-123",
                "text": json.loads(request.content)["text"],
                "userId": "user-789",
                "createdAt": "2026-10-10T16:00:00Z",
            }
            state["comments"].append(comment)
            return httpx.Response(200, json={"item": comment})
        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    with httpx.Client(
        base_url="https://planka.example", transport=httpx.MockTransport(respond)
    ) as client:
        monkeypatch.setattr(planka_cli, "Planka", lambda url: Planka(url, client=client))
        monkeypatch.setenv("PLANKA_URL", "https://planka.example")
        monkeypatch.setenv("PLANKA_USERNAME", "test-user")
        monkeypatch.setenv("PLANKA_PASSWORD", "test-password")
        monkeypatch.setenv("PLANKATOKENS", str(tmp_path / "tokens"))
        yield state


@pytest.mark.parametrize("body", ["Ready for review", "  # Überprüfung 📝\n\n- [x] **fertig**\n  "])
def test_comment_posts_inline_text_without_changing_card_or_old_comments(comment_api, body):
    card_before = deepcopy(comment_api["card"])
    comments_before = deepcopy(comment_api["comments"])

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", body])

    assert result.exit_code == 0, result.output
    assert "Created comment comment-987 on card card-123" in result.output
    requests = comment_api["requests"]
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/access-tokens"),
        ("GET", "/api/users/me"),
        ("POST", "/api/cards/card-123/comments"),
    ]
    assert json.loads(requests[0].content) == {
        "emailOrUsername": "test-user",
        "password": "test-password",
        "withHttpOnlyToken": True,
    }
    assert requests[-1].headers["Authorization"] == "Bearer test-token"
    assert json.loads(requests[-1].content) == {"text": body}
    assert comment_api["card"] == card_before
    assert comment_api["comments"][:-1] == comments_before


def test_comment_preserves_utf8_file_content(comment_api, tmp_path):
    body = "# Überprüfung 📝\r\n\r\n- [x] **fertig**\r\n  keep spaces  \r\n"
    body_file = tmp_path / "comment.md"
    body_file.write_bytes(body.encode("utf-8"))
    card_before = deepcopy(comment_api["card"])
    comments_before = deepcopy(comment_api["comments"])

    result = runner.invoke(
        planka_cli.app, ["cards", "comment", "card-123", "--body-file", str(body_file)]
    )

    assert result.exit_code == 0, result.output
    assert "Created comment comment-987 on card card-123" in result.output
    assert json.loads(comment_api["requests"][-1].content) == {"text": body}
    assert comment_api["card"] == card_before
    assert comment_api["comments"][:-1] == comments_before
    assert all(
        request.method not in {"PUT", "PATCH", "DELETE"} for request in comment_api["requests"]
    )


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ([], "Missing argument"),
        (["card-123"], "exactly one"),
        (["card-123", "--text", "Hi", "--body-file", "missing.md"], "exactly one"),
        (["card-123", "--text", ""], "must not be empty"),
        (["card-123", "--text", " \t\r\n"], "must not be empty"),
        (["", "--text", "Hi"], "Card ID must not be empty"),
        ([" \t", "--text", "Hi"], "Card ID must not be empty"),
        (["card-123", "--text"], "requires an argument"),
        (["card-123", "--body-file"], "requires an argument"),
    ],
)
def test_comment_rejects_invalid_arguments_before_authentication(comment_api, arguments, message):
    result = runner.invoke(planka_cli.app, ["cards", "comment", *arguments])

    assert result.exit_code != 0
    assert message in result.output
    assert "Created comment" not in result.output
    assert comment_api["requests"] == []


@pytest.mark.parametrize(
    ("file_kind", "message"),
    [
        ("missing", "Cannot read UTF-8 comment file"),
        ("directory", "Cannot read UTF-8 comment file"),
        ("non-utf8", "Cannot read UTF-8 comment file"),
        ("empty", "must not be empty"),
        ("whitespace", "must not be empty"),
    ],
)
def test_comment_rejects_invalid_body_files_before_authentication(
    comment_api, tmp_path, file_kind, message
):
    path = tmp_path / "body.md"
    if file_kind == "directory":
        path.mkdir()
    elif file_kind == "non-utf8":
        path.write_bytes(b"\xff\xfe")
    elif file_kind == "empty":
        path.write_bytes(b"")
    elif file_kind == "whitespace":
        path.write_bytes(b" \t\r\n")

    result = runner.invoke(
        planka_cli.app, ["cards", "comment", "card-123", "--body-file", str(path)]
    )

    assert result.exit_code != 0
    assert message in result.output
    assert "Created comment" not in result.output
    assert comment_api["requests"] == []


def test_comment_rejects_unreadable_file_before_authentication(comment_api, tmp_path):
    path = tmp_path / "body.md"
    path.write_text("Comment", encoding="utf-8")
    path.chmod(0o000)
    try:
        result = runner.invoke(
            planka_cli.app, ["cards", "comment", "card-123", "--body-file", str(path)]
        )
        assert result.exit_code != 0
        assert "not readable" in result.output
        assert comment_api["requests"] == []
    finally:
        path.chmod(0o600)


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (400, "Could not create comment"),
        (401, "Authentication failed"),
        (403, "Permission denied"),
        (404, "Card card-123 not found"),
        (500, "Could not create comment"),
        (503, "Could not create comment"),
    ],
)
def test_comment_reports_api_failure_without_retry_or_mutation(comment_api, status, message):
    comment_api["status"] = status
    card_before = deepcopy(comment_api["card"])
    comments_before = deepcopy(comment_api["comments"])

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert message in result.output
    assert f"HTTP {status}" in result.output
    assert "Created comment" not in result.output
    requests = comment_api["requests"]
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/access-tokens"),
        ("GET", "/api/users/me"),
        ("POST", "/api/cards/card-123/comments"),
    ]
    assert comment_api["card"] == card_before
    assert comment_api["comments"] == comments_before


@pytest.mark.parametrize("transport_error", [httpx.ConnectError, httpx.ReadTimeout])
def test_comment_reports_transport_failure_without_retry(comment_api, transport_error):
    comment_api["transport_error"] = transport_error

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert "Could not confirm comment creation" in result.output
    assert "Created comment" not in result.output
    assert len(comment_api["requests"]) == 3


def test_comment_uses_stored_credentials(comment_api, tmp_path, monkeypatch):
    for name in ("PLANKA_URL", "PLANKA_USERNAME", "PLANKA_PASSWORD"):
        monkeypatch.delenv(name)
    tokenstore = tmp_path / "stored-login"
    tokenstore.mkdir()
    (tokenstore / "credentials.json").write_text(
        json.dumps(
            {
                "PLANKA_URL": "https://planka.example",
                "PLANKA_USERNAME": "stored-test-user",
                "PLANKA_PASSWORD": "stored-test-password",
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        planka_cli.app,
        ["--tokenstore", str(tokenstore), "cards", "comment", "card-123", "--text", "Hi"],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(comment_api["requests"][0].content) == {
        "emailOrUsername": "stored-test-user",
        "password": "stored-test-password",
        "withHttpOnlyToken": True,
    }
    assert comment_api["requests"][-1].headers["Authorization"] == "Bearer test-token"


def test_comment_requires_configured_credentials(comment_api, monkeypatch):
    for name in ("PLANKA_URL", "PLANKA_USERNAME", "PLANKA_PASSWORD"):
        monkeypatch.delenv(name)

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert "Missing credentials" in result.output
    assert "Created comment" not in result.output
    assert comment_api["requests"] == []


@pytest.mark.parametrize("status", [401, 403, 500])
def test_comment_does_not_post_when_login_fails(comment_api, status):
    comment_api["login_status"] = status

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert "Connection Error" in result.output
    assert "Created comment" not in result.output
    assert [(r.method, r.url.path) for r in comment_api["requests"]] == [
        ("POST", "/api/access-tokens")
    ]


def test_comment_help_describes_exclusive_inputs_without_authentication(comment_api):
    result = runner.invoke(planka_cli.app, ["cards", "comment", "--help"])

    assert result.exit_code == 0
    assert "CARD_ID" in result.output
    assert "--text" in result.output
    assert "--body-file" in result.output
    assert "UTF-8" in result.output
    assert "exactly one" in result.output
    assert comment_api["requests"] == []
    cards_help = runner.invoke(planka_cli.app, ["cards", "--help"])
    assert cards_help.exit_code == 0
    assert "comment" in cards_help.output


@pytest.mark.parametrize(
    "reply",
    [
        None,
        [],
        "not a comment response",
        {},
        {"item": None},
        {"item": []},
        {"item": "not a comment"},
        {"item": {}},
        {"item": {"id": "comment-987"}},
        *({"item": {"id": value, "cardId": "card-123"}} for value in (None, "", " \t", 123, True)),
        *(
            {"item": {"id": "comment-987", "cardId": value}}
            for value in (None, "", 123, True, "other-card")
        ),
    ],
)
def test_comment_rejects_malformed_response_without_retry(comment_api, reply):
    comment_api["reply"] = reply

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert "Could not confirm comment creation" in result.output
    assert "Created comment" not in result.output
    assert len(comment_api["requests"]) == 3


def test_comment_rejects_non_json_response_without_retry(comment_api):
    comment_api["raw_reply"] = b"<html>Not a JSON response</html>"

    result = runner.invoke(planka_cli.app, ["cards", "comment", "card-123", "--text", "Hi"])

    assert result.exit_code != 0
    assert "Could not confirm comment creation" in result.output
    assert "Created comment" not in result.output
    assert len(comment_api["requests"]) == 3
