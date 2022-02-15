from pathlib import Path

import typer
from pydantic import BaseModel, Field, HttpUrl

from wakemebot import aptly

from . import __version__

app = typer.Typer()
aptly_app = typer.Typer()


class DebianRepository(BaseModel):
    url: HttpUrl
    distribution: str = Field(..., regex=r"[a-zA-Z0-9]+")


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
