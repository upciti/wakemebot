import base64
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator, Optional

import typer
from pydantic import BaseModel, Field, HttpUrl

from wakemebot import __version__
from wakemebot.aptly import AptlyClient, MTLSCredentials
from wakemebot.sync import (
    add_packages_to_repos,
    parse_op2deb_delta,
    remove_packages_from_repos,
    update_debian_repository,
)

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


def package_directory_callback(path: Path) -> Path:
    if path.is_dir() is False:
        raise typer.BadParameter(f"{path} is not a directory")
    return path


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


@contextmanager
def client_factory(
    server_url: str, ca_cert: str, client_cert: str, client_key: str
) -> Generator[AptlyClient, None, None]:
    with TemporaryDirectory(prefix="wakemebot_") as base_directory:
        ca_cert_path = Path(base_directory) / "ca.crt"
        ca_cert_path.write_bytes(base64.b64decode(ca_cert))
        client_cert_path = Path(base_directory) / "client.crt"
        client_cert_path.write_bytes(base64.b64decode(client_cert))
        client_key_path = Path(base_directory) / "client.key"
        client_key_path.write_bytes(base64.b64decode(client_key))
        credentials = MTLSCredentials(ca_cert_path, client_cert_path, client_key_path)
        yield AptlyClient(server_url, credentials=credentials)


@app.command(
    name="sync",
    help="Sync state of debian repository with packages defined in ops2deb blueprints."
    "Uses ops2deb delta output to know which packages need to be removed."
    "Add adds packages in package directory to the appropriate aptly repository",
)
def aptly_sync(
    server_url: str = option_server_url,
    ca_cert: str = option_ca_cert,
    client_cert: str = option_client_cert,
    client_key: str = option_client_key,
    publish_prefix: str = typer.Option(
        "s3:wakemeops-eu-west-3:wakemeops/stable", help="Aptly publish prefix"
    ),
    gpg_key: str = "wakemebot@protonmail.com",
    repos_prefix: str = typer.Option(
        "wakemeops-", help="Aptly repository name or regex pattern"
    ),
    package_directory: Path = typer.Argument(
        ...,
        help="Directory containing debian packages to add and ops2deb-delta.json",
        callback=package_directory_callback,
    ),
) -> None:
    delta = parse_op2deb_delta(package_directory / "ops2deb-delta.json")
    with client_factory(server_url, ca_cert, client_cert, client_key) as client:
        add_packages_to_repos(client, package_directory, repos_prefix)
        remove_packages_from_repos(client, delta)
        update_debian_repository(client, publish_prefix, gpg_key=gpg_key)


def main() -> None:
    app()
