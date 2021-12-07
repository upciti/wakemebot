import json
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cmp_to_key
from itertools import groupby
from pathlib import Path
from typing import Iterator, List, Set

import httpx
from debian.debian_support import Version, version_compare


@dataclass(frozen=True)
class Package:
    arch: str
    name: str
    version: str
    uid: str

    def __str__(self) -> str:
        return f"P{self.arch} {self.name} {self.version} {self.uid}"


def sort_cmp(p1: Package, p2: Package) -> int:
    return version_compare(p1.version, p2.version)


def client_factory(server: str) -> httpx.Client:
    transport = httpx.HTTPTransport(uds=server, retries=2)
    return httpx.Client(transport=transport, base_url="http://aptly/api")


def parse_packages(data: List[str]) -> List[Package]:
    data = [p[1:] for p in data if p[0] == "P"]
    return [Package(*p.split(" ")) for p in data]


def list_packages(client: httpx.Client, repo: str) -> List[Package]:
    data = client.get(f"/repos/{repo}/packages").json()
    return parse_packages(data)


def purge_old_versions(packages: List[Package], retain_how_many: int) -> List[Package]:
    """Only keep retain_how_many versions of a package"""
    packages = sorted(packages, key=cmp_to_key(sort_cmp))
    should_delete = packages[:-retain_how_many]
    return should_delete


def purge_old_revisions(packages: List[Package]) -> List[Package]:
    """Only keep the latest package revision"""
    should_delete: List[Package] = []
    for key, group in groupby(packages, lambda x: Version(x.version).upstream_version):
        package_group = sorted(group, key=cmp_to_key(sort_cmp))
        should_delete.extend(package_group[:-1])
    return should_delete


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
    for name in names:
        packages = list(filter(lambda x: x.name == name, all_packages))
        should_delete = set(purge_old_revisions(packages))
        should_delete.update(purge_old_versions(packages, retain_how_many))
        delete_packages(client, should_delete, repo)


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


def push(repo: str, package_directory: Path, retain: int, server: str) -> None:
    client = client_factory(server)

    if package_directory.is_dir() is False:
        print(f"{package_directory} is not a directory")
        sys.exit(1)

    packages = list(package_directory.glob("*.deb"))
    print(f"Found {len(packages)} packages in {package_directory}")

    if not packages:
        return

    # List repos matching pattern
    repos = [r["Name"] for r in client.get("/repos").json()]

    if repo not in repos:
        print(f"Aptly repository {repo} not found.")
        return

    upload_packages(client, packages, repo)
    names = {file.name.split("_")[0] for file in packages}
    for repo in repos:
        purge(client, repo, names, retain)


def export(repo: str, server: str, short: bool) -> None:
    client = client_factory(server)
    response = client.get(f"/repos/{repo}/packages{'' if short else '?format=details'}")
    response.raise_for_status()
    response_json = response.json()

    if short is False:
        # FIXME: drop some keys?
        print(json.dumps(response_json))
        return

    # Keep only binary packages
    response_json = [p[1:] for p in response_json if p.startswith("P")]

    # Keep arch, package name and version as a list for each package
    response_json = [p.split(" ")[:-1] for p in response_json]
    print(json.dumps(response_json))
