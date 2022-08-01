from pathlib import Path
from typing import Optional

import pygit2
import typer
from pydantic import BaseModel, Field, HttpUrl

from wakemebot import aptly, bot

from . import __version__

app = typer.Typer()
aptly_app = typer.Typer()


class DebianRepository(BaseModel):
    url: HttpUrl
    distribution: str = Field(..., regex=r"[a-zA-Z0-9]+")


def check_access_token(value: Optional[str]) -> str:
    if value is None:
        raise typer.BadParameter("Missing Github Access Token")
    return value


def get_git_repo_path(path: Path) -> Path:
    repo_path = pygit2.discover_repository(path)
    if not repo_path:
        raise typer.BadParameter(f"No repository found at '{path}'")
    return Path(repo_path).parent


@app.command(help="Look for updates and create pull requests")
def create_pull_requests(
    repository_path: Path = typer.Option(
        Path("."),
        help="Path to WakeMeOps repository",
        callback=get_git_repo_path,
    ),
    access_token: str = typer.Option(
        None,
        help="Github Personal Access Token",
        envvar="WAKEMEBOT_GITHUB_ACCESS_TOKEN",
        callback=check_access_token,
    ),
) -> None:
    bot.create_pull_requests(repository_path, access_token)


@app.command(help="Output wakemebot version")
def version() -> None:
    typer.secho(__version__)


@aptly_app.command(name="push", help="Push debian sources packages to aptly repository")
def aptly_push(
    repository: str = typer.Argument(..., help="Aptly repository name"),
    package_directory: Path = typer.Argument(
        ..., help="Directory containing debian packages to upload"
    ),
    retain: int = typer.Option(
        100, help="For each package, how many versions will be kept"
    ),
    server: str = typer.Option(
        "/var/lib/aptly/aptly.sock", help="Path to server unix socket"
    ),
) -> None:
    aptly.push(repository, package_directory, retain, server)


app.add_typer(aptly_app, name="aptly")


def main() -> None:
    app()
