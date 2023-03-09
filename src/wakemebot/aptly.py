import contextlib
from dataclasses import dataclass
from functools import total_ordering
from pathlib import Path
from typing import Generator, Iterable
from uuid import uuid4

import httpx
from debian.debian_support import Version
from pydantic import BaseModel


def to_camel(string: str) -> str:
    return "".join(word.capitalize() for word in string.split("_"))


class AptlyClientError(Exception):
    def __init__(self, message: str, response: httpx.Response | None = None) -> None:
        self.response = response
        super().__init__(message)


@dataclass(frozen=True)
class MTLSCredentials:
    ca_cert_path: Path
    client_cert_path: Path
    client_key_path: Path


@total_ordering
@dataclass(frozen=True)
class AptlyPackageRef:
    arch: str
    name: str
    version: str
    uid: str

    @property
    def upstream_version(self) -> str:
        return Version(self.version).upstream_version or ""

    @property
    def ref(self) -> str:
        return f"P{self.arch} {self.name} {self.version} {self.uid}"

    def __lt__(self, other: "AptlyPackageRef") -> bool:
        return (self.name, Version(self.version)) < (other.name, Version(other.version))


class AptlyRepo(BaseModel):
    name: str
    comment: str
    default_distribution: str
    default_component: str

    class Config:
        alias_generator = to_camel


_REPO_DOES_NOT_EXIST_ERROR = "Repo '{}' does not exist"


class AptlyClient:
    def __init__(
        self,
        server_url: str,
        credentials: MTLSCredentials | None = None,
        retries: int = 2,
    ):
        if credentials:
            transport = httpx.HTTPTransport(
                retries=retries,
                cert=(
                    str(credentials.client_cert_path),
                    str(credentials.client_key_path),
                ),
                verify=str(credentials.ca_cert_path),
            )
        else:
            transport = httpx.HTTPTransport(retries=retries)
        self._client = httpx.Client(transport=transport, base_url=server_url, timeout=60)

    @classmethod
    def raise_for_status(
        cls, response: httpx.Response, custom_messages: dict[int, str] | None = None
    ) -> None:
        if response.is_success:
            return

        if (
            custom_messages
            and (custom_message := custom_messages.get(response.status_code)) is not None
        ):
            message = custom_message
        elif response.has_redirect_location:
            message = (
                f"{response.status_code} {response.reason_phrase} for url "
                f"{response.url}\n"
                f"Redirect location: '{response.headers['location']}'\n"
            )
        else:
            message = (
                f"{response.status_code} {response.reason_phrase} for url {response.url}"
            )
        raise AptlyClientError(message, response)

    @contextlib.contextmanager
    def files_upload(self, package_paths: Iterable[Path]) -> Generator[str, None, None]:
        upload_directory = str(uuid4())
        try:
            file_descriptors = {path.name: path.open("rb") for path in package_paths}
        except OSError as e:
            raise AptlyClientError(str(e))
        response = self._client.post(f"/files/{upload_directory}", files=file_descriptors)
        self.raise_for_status(response)
        try:
            yield upload_directory
        finally:
            try:
                self._client.delete(f"/files/{upload_directory}")
            except httpx.HTTPError as e:
                raise AptlyClientError(str(e))

    def repo_list(self) -> list[AptlyRepo]:
        try:
            response = self._client.get("/repos")
        except httpx.HTTPError as e:
            raise AptlyClientError(str(e))
        self.raise_for_status(response)
        return [AptlyRepo.parse_obj(repo) for repo in response.json()]

    def repo_list_packages(self, repo_name: str) -> list[AptlyPackageRef]:
        try:
            response = self._client.get(f"/repos/{repo_name}/packages")
        except httpx.HTTPError as e:
            raise AptlyClientError(str(e))
        self.raise_for_status(
            response, {404: _REPO_DOES_NOT_EXIST_ERROR.format(repo_name)}
        )
        binary_packages = [p[1:] for p in response.json() if p[0] == "P"]
        return [AptlyPackageRef(*p.split(" ")) for p in binary_packages]

    def repo_remove_packages(
        self, repo_name: str, packages: Iterable[AptlyPackageRef]
    ) -> None:
        json = {"PackageRefs": [package.ref for package in packages]}
        try:
            response = self._client.request(
                "DELETE", f"/repos/{repo_name}/packages", json=json
            )
        except httpx.HTTPError as e:
            raise AptlyClientError(str(e))
        self.raise_for_status(response)

    def repo_add_packages(self, repo_name: str, upload_directory: str) -> None:
        response = self._client.post(
            f"/repos/{repo_name}/file/{upload_directory}?noRemove=1"
        )
        self.raise_for_status(
            response, {404: _REPO_DOES_NOT_EXIST_ERROR.format(repo_name)}
        )

    def publish_update(self, prefix: str, gpg_key: str | None = None) -> None:
        try:
            json = (
                {
                    "ForceOverwrite": True,
                    "Signing": {"GpgKey": gpg_key, "Batch": True},
                },
            )
            response = self._client.put(f"/publish/{prefix}", json=json)
        except httpx.HTTPError as e:
            raise AptlyClientError(str(e))
        self.raise_for_status(response)
