import base64
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cmp_to_key, partial
from itertools import groupby
from operator import attrgetter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Generator, Iterator, List, Set

import httpx
from debian.debian_support import Version, version_compare
from semver.version import Version as Semver


@dataclass(frozen=True)
class Package:
    arch: str
    name: str
    version: str
    uid: str

    @property
    def upstream_version(self) -> str:
        return Version(self.version).upstream_version or ""

    def __str__(self) -> str:
        return f"P{self.arch} {self.name} {self.version} {self.uid}"


def sort_cmp(p1: Package, p2: Package) -> int:
    if (version_order := version_compare(p1.version, p2.version)) != 0:
        return version_order
    if p1.arch < p2.arch:
        return -1
    if p1.arch > p2.arch:
        return 1
    return 0


@contextmanager
def client_factory(
    server_url: str, ca_cert: str, client_cert: str, client_key: str
) -> Generator[httpx.Client, None, None]:
    with TemporaryDirectory(prefix="wakemebot_") as base_directory:
        ca_cert_path = Path(base_directory) / "ca.crt"
        ca_cert_path.write_bytes(base64.b64decode(ca_cert))
        client_cert_path = Path(base_directory) / "client.crt"
        client_cert_path.write_bytes(base64.b64decode(client_cert))
        client_key_path = Path(base_directory) / "client.key"
        client_key_path.write_bytes(base64.b64decode(client_key))
        transport = httpx.HTTPTransport(
            retries=2,
            cert=(str(client_cert_path), str(client_key_path)),
            verify=str(ca_cert_path),
        )
        yield httpx.Client(transport=transport, base_url=server_url, timeout=30)


def parse_packages(data: List[str]) -> List[Package]:
    data = [p[1:] for p in data if p[0] == "P"]
    return [Package(*p.split(" ")) for p in data]


def list_packages(client: httpx.Client, repo: str) -> List[Package]:
    data = client.get(f"/repos/{repo}/packages").json()
    return parse_packages(data)


def purge_old_versions(packages: List[Package], retain_how_many: int) -> List[Package]:
    """
    Only keep retain_how_many versions of a package.
    Assumes packages have the same name and arch, and are sorted by versions.
    """
    should_delete = packages[:-retain_how_many]
    return should_delete


def purge_old_revisions(packages: List[Package]) -> List[Package]:
    """
    Only keep the latest package revision.
    Assumes packages have the same name and arch, and are sorted by versions.
    """
    should_delete: List[Package] = []
    for key, group in groupby(packages, attrgetter("upstream_version")):
        package_group = sorted(group, key=cmp_to_key(sort_cmp))
        should_delete.extend(package_group[:-1])
    return should_delete


def purge_old_patches(packages: List[Package]) -> List[Package]:
    """
    Only keep the most recent patch for packages using semantic versioning.
    Example: if we have two releases with version 2.1.1 and 2.2.2, 2.2.1 will be removed.
    Assumes packages have the same name and arch, and are sorted by versions.
    """
    should_delete: List[Package] = []
    packages = [p for p in packages if Semver.isvalid(p.upstream_version)]

    def group_by_key(package: Package) -> Semver:
        return Semver.parse(package.upstream_version).next_version(part="minor")

    for key, group in groupby(packages, key=group_by_key):
        package_group = sorted(group, key=cmp_to_key(sort_cmp))
        should_delete.extend(package_group[:-1])

    return should_delete


def purge_old_packages(packages: List[Package], retain_how_many: int) -> Set[Package]:
    """
    Call the three purge functions defined above.
    Assumes packages have the same name and arch.
    """
    # packages are only sorted once here
    packages = sorted(packages, key=cmp_to_key(sort_cmp))
    packages_to_delete: Set[Package] = set()
    purge_functions: List[Callable[[List[Package]], List[Package]]] = [
        purge_old_revisions,
        partial(purge_old_versions, retain_how_many=retain_how_many),
    ]
    for purge_function in purge_functions:
        packages_to_delete.update(purge_function(packages))
        packages = [p for p in packages if p not in packages_to_delete]
    return packages_to_delete


def delete_packages(client: httpx.Client, packages: Set[Package], repo: str) -> None:
    if not packages:
        return
    packages_str = [str(p) for p in sorted(packages, key=cmp_to_key(sort_cmp))]
    print(f"The following packages are going to be removed from {repo}: {packages_str}")
    data = {"PackageRefs": packages_str}
    response = client.request("DELETE", f"/repos/{repo}/packages", json=data)
    response.raise_for_status()


def purge(client: httpx.Client, repo: str, names: Set[str], retain_how_many: int) -> None:
    all_packages = list_packages(client, repo)
    packages_to_delete: Set[Package] = set()
    for name in names:
        for arch in ["amd64", "arm64", "armhf"]:
            packages = filter(lambda x: x.name == name and x.arch == arch, all_packages)
            packages_to_delete.update(purge_old_packages(list(packages), retain_how_many))
    delete_packages(client, packages_to_delete, repo)


@contextmanager
def upload_directory(client: httpx.Client) -> Iterator[str]:
    directory = str(uuid.uuid4())
    yield directory
    response = client.delete(f"/files/{directory}")
    if response.status_code != 200:
        print(f"Failed to remove upload directory: {directory}")


def upload_packages(client: httpx.Client, packages: List[Path], repo: str) -> None:
    with upload_directory(client) as directory:
        files = {file.name: file.open("rb") for file in packages}
        print(f"Uploading {len(packages)} packages to directory {directory}")
        response = client.post(f"/files/{directory}", files=files)
        response.raise_for_status()
        response = client.post(f"/repos/{repo}/file/{directory}?noRemove=1")
        response.raise_for_status()


def push(
    repo: str,
    package_directory: Path,
    retain: int,
    server_url: str,
    ca_cert: str,
    client_cert: str,
    client_key: str,
) -> None:
    if package_directory.is_dir() is False:
        print(f"{package_directory} is not a directory")
        sys.exit(1)

    packages = list(package_directory.glob("*.deb"))
    print(f"Found {len(packages)} packages in {package_directory}")

    if not packages:
        return

    with client_factory(server_url, ca_cert, client_cert, client_key) as client:
        response = client.get("/repos")
        response.raise_for_status()
        repos = [r["Name"] for r in response.json()]
        if repo not in repos:
            print(f"Aptly repository {repo} not found.")
            return
        upload_packages(client, packages, repo)
        names = {file.name.split("_")[0] for file in packages}
        for repo in repos:
            purge(client, repo, names, retain)


def publish(
    repo: str,
    server_url: str,
    ca_cert: str,
    client_cert: str,
    client_key: str,
) -> None:
    with client_factory(server_url, ca_cert, client_cert, client_key) as client:
        response = client.put(
            f"/publish/{repo}",
            json={
                "ForceOverwrite": True,
                "Signing": {"GpgKey": "wakemebot@protonmail.com", "Batch": True},
            },
        )
        response.raise_for_status()
        print(response.json())
