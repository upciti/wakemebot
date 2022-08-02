from pathlib import Path
from typing import Optional

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


def client_configuration_callback(value: Optional[str]) -> str:
    if value is None:
        raise typer.BadParameter("Option must be set through env or cli")
    return value


option_server_url: str = typer.Option(
    None,
    help="Aptly server URL",
    envvar="WAKEMEBOT_APTLY_SERVER_URL",
    callback=client_configuration_callback,
)

option_ca_cert: str = typer.Option(
    None,
    help="Base64 encoded CA certificate",
    envvar="WAKEMEBOT_APTLY_CA_CERT",
    callback=client_configuration_callback,
)

option_client_cert: str = typer.Option(
    None,
    help="Base64 encoded client certificate",
    envvar="WAKEMEBOT_APTLY_CLIENT_CERT",
    callback=client_configuration_callback,
)

option_client_key: str = typer.Option(
    None,
    help="Base64 encoded client key",
    envvar="WAKEMEBOT_APTLY_CLIENT_KEY",
    callback=client_configuration_callback,
)


@aptly_app.command(name="push", help="Push debian sources packages to aptly repository")
def aptly_push(
    repository: str = typer.Argument(..., help="Aptly repository name"),
    package_directory: Path = typer.Argument(
        ..., help="Directory containing debian packages to upload"
    ),
    retain: int = typer.Option(
        100, help="For each package, how many versions will be kept"
    ),
    server_url: str = option_server_url,
    ca_cert: str = option_ca_cert,
    client_cert: str = option_client_cert,
    client_key: str = option_client_key,
) -> None:
    aptly.push(
        repository,
        package_directory,
        retain,
        server_url,
        ca_cert,
        client_cert,
        client_key,
    )


@aptly_app.command(name="publish", help="Publish aptly repository")
def aptly_publish(
    repository: str = typer.Argument(..., help="Aptly repository name"),
    server_url: str = option_server_url,
    ca_cert: str = option_ca_cert,
    client_cert: str = option_client_cert,
    client_key: str = option_client_key,
) -> None:
    aptly.publish(
        repository,
        server_url,
        ca_cert,
        client_cert,
        client_key,
    )


app.add_typer(aptly_app, name="aptly")


def main() -> None:
    app()
