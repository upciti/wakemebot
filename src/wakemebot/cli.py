from pathlib import Path
from typing import List

import typer

from wakemebot import aptly, generator

app = typer.Typer()
aptly_app = typer.Typer()


@app.command(help="Generate debian sources packages using last git commit")
def generate(
    ops2deb_config: Path = typer.Argument(..., help="Path to ops2deb configuration file"),
    repo_state: Path = typer.Argument(..., help="Path to repo state file"),
    work_directory: Path = typer.Option(
        "output",
        "--work-dir",
        "-w",
        envvar="OPS2DEB_WORK_DIR",
        help="Directory where debian source packages are generated and built.",
    ),
) -> None:
    generator.generate(ops2deb_config, repo_state, work_directory)


@aptly_app.command(
    name="push", help="Generate debian sources packages using last git commit"
)
def aptly_push(
    repo_pattern: str = typer.Argument(
        ..., help="Pattern matched against the list of aptly repositories"
    ),
    packages: List[str] = typer.Argument(..., help="List of packages to upload"),
    retain: int = typer.Option(
        100, help="For each package, how many versions will be kept"
    ),
    server: str = typer.Option(
        "/var/lib/aptly/aptly.sock", help="Path to server unix socket"
    ),
) -> None:
    aptly.push(repo_pattern, [Path(p) for p in packages], retain, server)


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
