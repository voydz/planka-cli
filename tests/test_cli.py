"""Tests for planka-cli."""

from typer.testing import CliRunner

from scripts.planka_cli import app

runner = CliRunner()


class TestHelp:
    """Test help output for all commands."""

    def test_main_help(self):
        """Main command should show help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Planka CLI" in result.output

    def test_projects_help(self):
        """Projects subcommand should show help."""
        result = runner.invoke(app, ["projects", "--help"])
        assert result.exit_code == 0
        assert "Manage projects" in result.output

    def test_boards_help(self):
        """Boards subcommand should show help."""
        result = runner.invoke(app, ["boards", "--help"])
        assert result.exit_code == 0
        assert "Manage boards" in result.output

    def test_lists_help(self):
        """Lists subcommand should show help."""
        result = runner.invoke(app, ["lists", "--help"])
        assert result.exit_code == 0
        assert "Manage lists" in result.output

    def test_cards_help(self):
        """Cards subcommand should show help."""
        result = runner.invoke(app, ["cards", "--help"])
        assert result.exit_code == 0
        assert "Manage cards" in result.output

    def test_notifications_help(self):
        """Notifications subcommand should show help."""
        result = runner.invoke(app, ["notifications", "--help"])
        assert result.exit_code == 0
        assert "Manage notifications" in result.output


class TestUnknownCommand:
    """Test behavior with unknown commands."""

    def test_unknown_subcommand_shows_help(self):
        """Unknown subcommand should show help and exit with code 2."""
        result = runner.invoke(app, ["unknown"])
        assert result.exit_code == 2


class TestLoginLogout:
    """Test login/logout commands (without actually connecting)."""

    def test_login_requires_options(self):
        """Login without options should fail."""
        result = runner.invoke(app, ["login"])
        assert result.exit_code != 0

    def test_logout_without_credentials(self, tmp_path, monkeypatch):
        """Logout without stored credentials should be graceful."""
        # Point ENV_PATH to a temp location
        import scripts.planka_cli as cli_module

        monkeypatch.setattr(cli_module, "ENV_PATH", tmp_path / ".env")
        result = runner.invoke(app, ["logout"])
        assert result.exit_code == 0
        assert "No stored credentials" in result.output
