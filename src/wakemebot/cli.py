import base64
import re
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator, Optional

import typer
from pydantic import BaseModel, Field, HttpUrl

from wakemebot import __version__
from wakemebot.aptly import AptlyClient, MTLSCredentials

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
) -> Iterator[AptlyClient]:
    with TemporaryDirectory(prefix="wakemebot_") as base_directory:
        ca_cert_path = Path(base_directory) / "ca.crt"
        ca_cert_path.write_bytes(base64.b64decode(ca_cert))
        client_cert_path = Path(base_directory) / "client.crt"
        client_cert_path.write_bytes(base64.b64decode(client_cert))
        client_key_path = Path(base_directory) / "client.key"
        client_key_path.write_bytes(base64.b64decode(client_key))
        credentials = MTLSCredentials(ca_cert_path, client_cert_path, client_key_path)
        yield AptlyClient(server_url, credentials=credentials)


@aptly_app.command(
    name="push", help="Push debian sources packages to matched aptly repositories"
)
def aptly_push(
    repos_regex: str = typer.Argument(..., help="Aptly repository name or regex pattern"),
    package_directory: Path = typer.Argument(
        ...,
        help="Directory containing debian packages to upload",
        callback=package_directory_callback,
    ),
    server_url: str = option_server_url,
    ca_cert: str = option_ca_cert,
    client_cert: str = option_client_cert,
    client_key: str = option_client_key,
) -> None:
    packages = package_directory.glob("*.deb")
    with client_factory(server_url, ca_cert, client_cert, client_key) as client:
        repositories = [repo.name for repo in client.repo_list()]
        repositories = [repo for repo in repositories if re.match(repos_regex, repo)]
        with client.files_upload(packages) as upload_directory:
            for repository in repositories:
                client.repo_add_packages(repository, upload_directory)


@aptly_app.command(name="publish", help="Publish aptly repository")
def aptly_publish(
    prefix: str = typer.Argument(..., help="Aptly publish prefix"),
    server_url: str = option_server_url,
    ca_cert: str = option_ca_cert,
    client_cert: str = option_client_cert,
    client_key: str = option_client_key,
    gpg_key: str = "wakemebot@protonmail.com",
) -> None:
    with client_factory(server_url, ca_cert, client_cert, client_key) as client:
        client.publish_update(prefix, gpg_key=gpg_key)


app.add_typer(aptly_app, name="aptly")


def main() -> None:
    app()
