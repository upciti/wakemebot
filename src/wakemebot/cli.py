import sys
from pathlib import Path

import typer
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from wakemebot import aptly, docs

from . import __version__

app = typer.Typer()
aptly_app = typer.Typer()


class DebianRepository(BaseModel):
    url: HttpUrl
    distribution: str = Field(..., regex=r"[a-zA-Z0-9]+")


@app.command(help="Output ops2deb version")
def version() -> None:
    typer.secho(__version__)


@app.command(name="docs", help="Update documentation")
def update_documentation(
    debian_repository: str = typer.Option(
        "http://deb.wakemeops.com/wakemeops/ stable",
        "--repository",
        "-r",
        envvar="OPS2DEB_REPOSITORY",
        help='Format: "{debian_repository_url} {distribution_name}". '
        'Example: "http://deb.wakemeops.com/ stable". '
        "Packages already published in the repo won't be generated.",
    ),
) -> None:
    try:
        url, distribution = debian_repository.split(" ")
    except ValueError:
        print(
            "The expected format for the --repository option is "
            '"{repository_url} {distribution}"'
        )
        sys.exit(1)
    try:
        DebianRepository(url=url, distribution=distribution)
    except ValidationError as e:
        print(e)
        sys.exit(1)
    docs.update_documentation(url, distribution)


@aptly_app.command(
    name="push", help="Generate debian sources packages using last git commit"
)
def aptly_push(
    repo_pattern: str = typer.Argument(
        ..., help="Pattern matched against the list of aptly repositories"
    ),
    package_directory: Path = typer.Argument(
        ..., help="A directory containing debian packages to upload"
    ),
    retain: int = typer.Option(
        100, help="For each package, how many versions will be kept"
    ),
    server: str = typer.Option(
        "/var/lib/aptly/aptly.sock", help="Path to server unix socket"
    ),
) -> None:
    aptly.push(repo_pattern, package_directory, retain, server)


@aptly_app.command(name="export", help="Save repo package list as JSON")
def aptly_export(
    repo: str = typer.Argument(..., help="Aptly repository name"),
    server: str = typer.Option(
        "/var/lib/aptly/aptly.sock", help="Path to server unix socket"
    ),
    short: bool = typer.Option(True),
) -> None:
    aptly.export(repo, server, short)


app.add_typer(aptly_app, name="aptly")


def main() -> None:
    app()
