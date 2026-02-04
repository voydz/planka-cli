import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import click
import typer
from dotenv import load_dotenv, set_key
from plankapy.v2 import Card, Planka
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup


def get_binary_dir() -> Path:
    argv0 = sys.argv[0]
    path = Path(argv0)
    if not path.is_absolute():
        resolved = shutil.which(argv0)
        if resolved:
            path = Path(resolved)
    if path.exists():
        return path.resolve().parent if path.is_file() else path.resolve()
    return Path(__file__).resolve().parent


ENV_PATH = get_binary_dir() / ".env"

# Load environment variables from the .env next to the binary/script.
load_dotenv(dotenv_path=ENV_PATH)


class HelpOnUnknownCommandGroup(TyperGroup):
    def get_command(self, ctx: click.Context, cmd_name: str):
        command = super().get_command(ctx, cmd_name)
        if command is None:
            click.echo(ctx.get_help())
            ctx.exit(2)
        return command


app = typer.Typer(cls=HelpOnUnknownCommandGroup)
console = Console()
projects_app = typer.Typer(cls=HelpOnUnknownCommandGroup, help="Manage projects")
boards_app = typer.Typer(cls=HelpOnUnknownCommandGroup, help="Manage boards")
lists_app = typer.Typer(cls=HelpOnUnknownCommandGroup, help="Manage lists")
cards_app = typer.Typer(cls=HelpOnUnknownCommandGroup, help="Manage cards")
notifications_app = typer.Typer(cls=HelpOnUnknownCommandGroup, help="Manage notifications")
app.add_typer(projects_app, name="projects")
app.add_typer(boards_app, name="boards")
app.add_typer(lists_app, name="lists")
app.add_typer(cards_app, name="cards")
app.add_typer(notifications_app, name="notifications")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Planka CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def get_env_config() -> tuple[Optional[str], Optional[str], Optional[str]]:
    return (
        os.getenv("PLANKA_URL"),
        os.getenv("PLANKA_USERNAME"),
        os.getenv("PLANKA_PASSWORD"),
    )


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"
    try:
        return datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise typer.BadParameter(
            "Invalid datetime. Use ISO-8601 like 2025-01-31 or 2025-01-31T10:30:00Z."
        ) from exc


def parse_position(value: Optional[str]) -> Optional[Union[str, int]]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("top", "bottom"):
        return normalized
    try:
        return int(value)
    except ValueError as exc:
        raise typer.BadParameter("Position must be 'top', 'bottom', or an integer.") from exc


def find_list(planka: Planka, list_id: str):
    for project in planka.projects:
        for board in project.boards:
            for list_item in board.lists:
                if list_item.id == list_id:
                    return list_item
    return None


def find_list_with_board(planka: Planka, list_id: str):
    """Find a list and return both the list and its parent board."""
    for project in planka.projects:
        for board in project.boards:
            for list_item in board.lists:
                if list_item.id == list_id:
                    return list_item, board
    return None, None


def get_card_by_id(planka: Planka, card_id: str) -> Optional[Card]:
    try:
        card_data = planka.endpoints.getCard(card_id)["item"]
    except Exception:
        return None
    return Card(card_data, planka)


def make_table(title: str) -> Table:
    return Table(
        title=title,
        show_header=True,
        header_style="bold",
        show_edge=False,
        show_lines=False,
        box=None,
    )


def render_notifications(title: str, notifications: list) -> None:
    if not notifications:
        console.print("No notifications found.")
        return

    table = make_table(title)
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Read", justify="center")
    table.add_column("Created At", justify="right")
    table.add_column("Card ID", justify="right")

    for notification in notifications:
        card_id = notification.schema.get("cardId")
        table.add_row(
            str(notification.id),
            str(notification.type),
            "yes" if notification.is_read else "no",
            str(notification.created_at),
            str(card_id),
        )

    console.print(table)


def get_planka() -> Planka:
    planka_url, planka_username, planka_password = get_env_config()
    if not planka_url or not planka_username or not planka_password:
        console.print(
            "[bold red]Error:[/bold red] Missing credentials. "
            f"Set PLANKA_URL, PLANKA_USERNAME, and PLANKA_PASSWORD or run "
            f"`planka-cli login --url ... --username ... --password ...` "
            f"to write {ENV_PATH}."
        )
        sys.exit(1)

    try:
        planka = Planka(planka_url)
        planka.login(username=planka_username, password=planka_password)
        return planka
    except Exception as e:
        console.print(f"[bold red]Connection Error:[/bold red] {e}")
        sys.exit(1)


@app.command()
def login(
    url: str = typer.Option(..., "--url", "-u", help="Planka base URL"),
    username: str = typer.Option(..., "--username", "-n", help="Planka username"),
    password: str = typer.Option(..., "--password", "-p", help="Planka password"),
):
    """Store credentials in a .env file next to the binary."""
    try:
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        set_key(str(ENV_PATH), "PLANKA_URL", url)
        set_key(str(ENV_PATH), "PLANKA_USERNAME", username)
        set_key(str(ENV_PATH), "PLANKA_PASSWORD", password)
    except OSError as e:
        console.print(f"[bold red]Error:[/bold red] Could not write {ENV_PATH}: {e}")
        raise typer.Exit(1)

    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass

    console.print(f"[green]Saved credentials to[/green] {ENV_PATH}")


@app.command()
def logout():
    """Delete the stored .env file next to the binary."""
    if not ENV_PATH.exists():
        console.print(f"No stored credentials found at {ENV_PATH}")
        return

    try:
        ENV_PATH.unlink()
    except OSError as e:
        console.print(f"[bold red]Error:[/bold red] Could not delete {ENV_PATH}: {e}")
        raise typer.Exit(1)

    console.print("[green]Logged out.[/green] Removed stored credentials.")


@app.command()
def status():
    """Check connection and print current user info."""
    planka = get_planka()
    try:
        user = planka.me
        console.print(
            f"[green]Connected![/green] Logged in as: [bold]{user.username}[/bold] (ID: {user.id})"
        )
        if user.name:
            console.print(f"Name: {user.name}")
        console.print(f"Email: {user.email}")
    except Exception as e:
        console.print(f"[bold red]Error fetching status:[/bold red] {e}")


@projects_app.command("list")
def list_projects():
    """List all projects."""
    planka = get_planka()
    try:
        projects = planka.projects
        if not projects:
            console.print("No projects found.")
            return

        table = make_table("Projects")
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Created At", justify="right")

        for p in projects:
            table.add_row(str(p.id), p.name, str(p.created_at))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@boards_app.command("list")
def list_boards(
    project_id: Optional[str] = typer.Argument(None, help="Project ID to filter by"),
):
    """List boards. Optionally filter by Project ID."""
    planka = get_planka()
    try:
        if project_id is not None:
            # Find specific project
            project = next((p for p in planka.projects if p.id == project_id), None)
            if not project:
                console.print(f"[red]Project {project_id} not found.[/red]")
                return
            boards_list = project.boards
            title = f"Boards in Project {project.name}"
        else:
            # List all boards from all projects the user has access to
            # plankapy doesn't have a direct 'all_boards', so we iterate projects
            boards_list = []
            for p in planka.projects:
                boards_list.extend(p.boards)
            title = "All Boards"

        if not boards_list:
            console.print("No boards found.")
            return

        planka_url, _, _ = get_env_config()
        table = make_table(title)
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Project ID", justify="right")
        table.add_column("URL", style="magenta")

        for b in boards_list:
            project_id_value = b.schema.get("projectId")
            board_url = None
            if planka_url and b.id:
                board_url = f"{planka_url.rstrip('/')}/boards/{b.id}"
            table.add_row(str(b.id), b.name, str(project_id_value), str(board_url or "-"))

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@lists_app.command("list")
def list_lists(board_id: str):
    """List all lists in a board."""
    planka = get_planka()
    try:
        # We need to find the board first to get its lists
        # This is a bit inefficient in plankapy if we don't know the project, but we can search
        target_board = None
        for p in planka.projects:
            for b in p.boards:
                if b.id == board_id:
                    target_board = b
                    break
            if target_board:
                break

        if not target_board:
            console.print(f"[red]Board {board_id} not found.[/red]")
            return

        table = make_table(f"Lists in Board: {target_board.name}")
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Board ID", justify="right")
        table.add_column("Position", justify="right")

        for list_item in target_board.lists:
            table.add_row(
                str(list_item.id), list_item.name, str(target_board.id), str(list_item.position)
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cards_app.command("list")
def list_cards(list_id: str):
    """List all cards in a list."""
    planka = get_planka()
    try:
        target_list, target_board = find_list_with_board(planka, list_id)

        if not target_list:
            console.print(f"[red]List {list_id} not found.[/red]")
            return

        planka_url, _, _ = get_env_config()
        board_id = target_board.id if target_board else None
        table = make_table(f"Cards in List: {target_list.name}")
        table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("List ID", justify="right")
        table.add_column("Position", justify="right")
        table.add_column("URL", style="magenta")

        for c in target_list.cards:
            card_url = None
            if planka_url and board_id and c.id:
                card_url = f"{planka_url.rstrip('/')}/boards/{board_id}/cards/{c.id}"
            table.add_row(str(c.id), c.name, str(list_id), str(c.position), str(card_url or "-"))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cards_app.command("show")
def show_card(card_id: str):
    """Show details for a card."""
    planka = get_planka()
    try:
        card = get_card_by_id(planka, card_id)
        if not card:
            console.print(f"[red]Card {card_id} not found.[/red]")
            return

        table = make_table(f"Card: {card.name}")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        def safe_attr(obj: object, name: str) -> object:
            try:
                return getattr(obj, name)
            except Exception:
                return None

        def normalize_url(base_url: Optional[str], value: Optional[str]) -> Optional[str]:
            if not value:
                return None
            candidate = str(value).strip()
            if not candidate:
                return None
            if candidate.startswith("http://") or candidate.startswith("https://"):
                return candidate
            if base_url:
                return f"{base_url.rstrip('/')}/{candidate.lstrip('/')}"
            return candidate

        def extract_attachment_url(attachment: object, base_url: Optional[str]) -> Optional[str]:
            data = safe_attr(attachment, "data")
            if isinstance(data, dict):
                for key in (
                    "url",
                    "downloadUrl",
                    "download_url",
                    "link",
                    "href",
                    "path",
                ):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return normalize_url(base_url, value)
                file_info = data.get("file")
                if isinstance(file_info, dict):
                    for key in (
                        "url",
                        "downloadUrl",
                        "download_url",
                        "path",
                        "thumbnailUrl",
                        "thumbUrl",
                        "thumbnail_url",
                    ):
                        value = file_info.get(key)
                        if isinstance(value, str) and value.strip():
                            return normalize_url(base_url, value)
            direct_url = safe_attr(attachment, "url")
            if isinstance(direct_url, str) and direct_url.strip():
                return normalize_url(base_url, direct_url)
            return None

        def add_row(label: str, value: object) -> None:
            if value is None or value == "":
                table.add_row(label, "-")
            else:
                table.add_row(label, str(value))

        try:
            schema = card.schema or {}
        except Exception:
            schema = {}
        list_id_value = schema.get("listId")
        board_id_value = schema.get("boardId")
        list_name_value = None
        list_obj = safe_attr(card, "list")
        if list_obj is not None:
            list_id_value = safe_attr(list_obj, "id") or list_id_value
            list_name_value = safe_attr(list_obj, "name")
            if not board_id_value:
                list_schema = safe_attr(list_obj, "schema")
                if isinstance(list_schema, dict):
                    board_id_value = list_schema.get("boardId")

        list_display = "-"
        if list_name_value and list_id_value:
            list_display = f"{list_name_value} ({list_id_value})"
        elif list_name_value:
            list_display = list_name_value
        elif list_id_value:
            list_display = list_id_value

        due_date = safe_attr(card, "due_date") or schema.get("dueDate")
        due_completed = safe_attr(card, "due_date_completed")
        if due_completed is None:
            due_completed = schema.get("isDueCompleted")
        if isinstance(due_completed, bool):
            due_completed = "yes" if due_completed else "no"

        attachments_error = None
        comments_error = None
        try:
            attachments = list(safe_attr(card, "attachments") or [])
        except Exception as exc:
            attachments = []
            attachments_error = str(exc)
        try:
            comments = list(safe_attr(card, "comments") or [])
        except Exception as exc:
            comments = []
            comments_error = str(exc)

        comments_count = safe_attr(card, "comments_count")
        if comments_count is None and comments_error is None:
            comments_count = len(comments)

        planka_url, _, _ = get_env_config()
        card_url = None
        if planka_url and board_id_value and card.id:
            card_url = f"{planka_url.rstrip('/')}/boards/{board_id_value}/cards/{card.id}"

        add_row("ID", card.id)
        add_row("URL", card_url)
        add_row("Name", card.name)
        add_row("Description", safe_attr(card, "description") or schema.get("description"))
        add_row("Board ID", board_id_value)
        add_row("List", list_display)
        add_row("Position", safe_attr(card, "position") or schema.get("position"))
        add_row("Type", safe_attr(card, "type") or schema.get("type"))
        add_row("Due Date", due_date)
        add_row("Due Completed", due_completed)
        if attachments_error:
            add_row("Attachments", f"Error: {attachments_error}")
        else:
            add_row("Attachments", len(attachments))
        if comments_error:
            add_row("Comments", f"Error: {comments_error}")
        else:
            add_row("Comments", comments_count)
        add_row("Created At", safe_attr(card, "created_at") or schema.get("createdAt"))
        add_row("Updated At", safe_attr(card, "updated_at") or schema.get("updatedAt"))

        console.print(table)

        if attachments and attachments_error is None:
            attachments_table = make_table("Attachments")
            attachments_table.add_column("ID", justify="right", style="cyan", no_wrap=True)
            attachments_table.add_column("Name", style="magenta")
            attachments_table.add_column("Type", style="magenta")
            attachments_table.add_column("URL", style="magenta")
            attachments_table.add_column("Created At", justify="right")

            for attachment in attachments:
                attachment_url = extract_attachment_url(attachment, planka_url)
                attachments_table.add_row(
                    str(safe_attr(attachment, "id") or "-"),
                    str(safe_attr(attachment, "name") or "-"),
                    str(safe_attr(attachment, "type") or "-"),
                    str(attachment_url or "-"),
                    str(safe_attr(attachment, "created_at") or "-"),
                )

            console.print(attachments_table)

        if comments and comments_error is None:
            comments_table = make_table("Comments")
            comments_table.add_column("ID", justify="right", style="cyan", no_wrap=True)
            comments_table.add_column("User", style="magenta")
            comments_table.add_column("Text", style="magenta")
            comments_table.add_column("Created At", justify="right")

            for comment in comments:
                user = safe_attr(comment, "user")
                user_label = (
                    safe_attr(user, "name")
                    or safe_attr(user, "username")
                    or safe_attr(user, "id")
                    or "-"
                )
                text = safe_attr(comment, "text")
                text_label = " ".join(str(text).split()) if text else "-"
                comments_table.add_row(
                    str(safe_attr(comment, "id") or "-"),
                    str(user_label),
                    text_label,
                    str(safe_attr(comment, "created_at") or "-"),
                )

            console.print(comments_table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cards_app.command("create")
def create_card(
    list_id: str = typer.Argument(..., help="List ID to create the card in"),
    name: str = typer.Argument(..., help="Card name/title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Card description"),
    position: str = typer.Option(
        "bottom", "--position", "-p", help="Position: top, bottom, or integer"
    ),
    card_type: str = typer.Option("project", "--type", "-t", help="Card type (project, story)"),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (ISO-8601)"),
    due_completed: bool = typer.Option(False, "--due-completed", help="Mark due date as completed"),
):
    """Create a new card in a list."""
    planka = get_planka()
    try:
        target_list = find_list(planka, list_id)
        if not target_list:
            console.print(f"[red]List {list_id} not found.[/red]")
            return

        parsed_due_date = parse_iso_datetime(due_date)
        parsed_position = parse_position(position) or "bottom"

        card = target_list.create_card(
            name=name,
            position=parsed_position,
            type=card_type,
            description=description,
            due_date=parsed_due_date,
            due_date_completed=due_completed,
        )

        console.print(
            f"[green]Created card[/green] [bold]{card.name}[/bold] "
            f"(ID: {card.id}) in list [bold]{target_list.name}[/bold]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cards_app.command("update")
def update_card(
    card_id: str = typer.Argument(..., help="Card ID to update"),
    name: Optional[str] = typer.Option(None, "--name", help="New card name"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="New card description"
    ),
    clear_description: bool = typer.Option(
        False, "--clear-description", help="Clear the description"
    ),
    position: Optional[str] = typer.Option(
        None, "--position", "-p", help="Position: top, bottom, or integer"
    ),
    list_id: Optional[str] = typer.Option(None, "--list-id", help="Move to a new list"),
    card_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Card type (project, story)"
    ),
    due_date: Optional[str] = typer.Option(None, "--due-date", help="Due date (ISO-8601)"),
    clear_due_date: bool = typer.Option(False, "--clear-due-date", help="Clear the due date"),
    due_completed: Optional[bool] = typer.Option(
        None,
        "--due-completed/--no-due-completed",
        help="Mark due date as completed/uncompleted",
    ),
):
    """Update an existing card."""
    if description is not None and clear_description:
        console.print(
            "[bold red]Error:[/bold red] Use either --description or --clear-description."
        )
        raise typer.Exit(1)
    if due_date is not None and clear_due_date:
        console.print("[bold red]Error:[/bold red] Use either --due-date or --clear-due-date.")
        raise typer.Exit(1)

    planka = get_planka()
    try:
        card = get_card_by_id(planka, card_id)
        if not card:
            console.print(f"[red]Card {card_id} not found.[/red]")
            return

        update_fields: dict[str, object] = {}
        if name is not None:
            update_fields["name"] = name
        if description is not None:
            update_fields["description"] = description
        elif clear_description:
            update_fields["description"] = None
        if card_type is not None:
            update_fields["type"] = card_type
        if due_date is not None:
            update_fields["dueDate"] = parse_iso_datetime(due_date)
        elif clear_due_date:
            update_fields["dueDate"] = None
        if due_completed is not None:
            update_fields["isDueCompleted"] = due_completed

        move_position = parse_position(position)
        if list_id is not None or move_position is not None:
            target_list = find_list(planka, list_id) if list_id is not None else card.list
            if not target_list:
                console.print(f"[red]List {list_id} not found.[/red]")
                return
            card.move(target_list, position=move_position or "top")

        if update_fields:
            card.update(**update_fields)

        if not update_fields and list_id is None and move_position is None:
            console.print("[yellow]No updates provided.[/yellow]")
            return

        console.print(f"[green]Updated card[/green] [bold]{card.name}[/bold] (ID: {card.id})")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@cards_app.command("delete")
def delete_card(
    card_id: str = typer.Argument(..., help="Card ID to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Delete a card."""
    planka = get_planka()
    try:
        card = get_card_by_id(planka, card_id)
        if not card:
            console.print(f"[red]Card {card_id} not found.[/red]")
            return

        if not yes:
            confirm = typer.confirm(f"Delete card '{card.name}' ({card.id})?")
            if not confirm:
                console.print("Cancelled.")
                return

        card.delete()
        console.print(f"[green]Deleted card[/green] {card_id}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@notifications_app.command("all")
def all_notifications():
    """List all notifications."""
    planka = get_planka()
    try:
        render_notifications("Notifications", planka.notifications)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


@notifications_app.command("unread")
def unread_notifications():
    """List unread notifications."""
    planka = get_planka()
    try:
        render_notifications("Unread Notifications", planka.unread_notifications)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    app()
