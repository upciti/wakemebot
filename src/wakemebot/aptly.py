import json
import re
import sys
import uuid
from contextlib import contextmanager
from functools import cmp_to_key
from pathlib import Path
from typing import Iterator, List

import httpx
from debian.debian_support import version_compare


def sort_cmp(p1: str, p2: str) -> int:
    v1 = p1.split(" ")[2]
    v2 = p2.split(" ")[2]
    return version_compare(v1, v2)


def client_factory(server: str) -> httpx.Client:
    transport = httpx.HTTPTransport(uds=server, retries=2)
    return httpx.Client(transport=transport, base_url="http://aptly/api")


def purge(client: httpx.Client, repo: str, name: str, retain_how_many: int) -> None:
    data = client.get(f"/repos/{repo}/packages").json()
    data = list(filter(lambda x: x.split(" ")[1] == name, data))
    data = sorted(data, key=cmp_to_key(sort_cmp))
    should_delete = data[:-retain_how_many]

    if should_delete:
        print(
            f"The following packages are going to be removed from {repo}: {should_delete}"
        )
        data = {"PackageRefs": should_delete}
        response = client.request("DELETE", f"/repos/{repo}/packages", json=data)
        response.raise_for_status()
    else:
        print(f"No version of {name} deleted in {repo}")


@contextmanager
def upload_directory(client: httpx.Client) -> Iterator[str]:
    directory = str(uuid.uuid4())
    yield directory
    response = client.delete(f"/files/{directory}")
    if response.status_code != 200:
        print(f"Failed to remove upload directory: {directory}")


def upload_packages(client: httpx.Client, packages: List[Path], repos: List[str]) -> None:
    with upload_directory(client) as directory:
        files = {file.name: file.open("rb") for file in packages}
        print(f"Uploading {len(packages)} packages to directory {directory}")
        response = client.post(f"/files/{directory}", files=files)
        response.raise_for_status()
        for repo in repos:
            # Add packages to repo
            response = client.post(f"/repos/{repo}/file/{directory}?noRemove=1")
            response.raise_for_status()


def push(repo_pattern: str, package_directory: Path, retain: int, server: str) -> None:
    client = client_factory(server)
    repo_pattern_re = re.compile(repo_pattern)

    if package_directory.is_dir() is False:
        print(f"{package_directory} is not a directory")
        sys.exit(1)

    packages = list(package_directory.glob("*.deb"))
    print(f"Found {len(packages)} packages in {package_directory}")

    if not packages:
        return

    # List repos matching pattern
    repos = [r["Name"] for r in client.get("/repos").json()]
    repos = [r for r in repos if repo_pattern_re.match(r)]
    print(f"Pattern matches the following repositories: {repos})")

    if not repos:
        return

    upload_packages(client, packages, repos)
    names = {file.name.split("_")[0] for file in packages}
    for repo in repos:
        for name in names:
            purge(client, repo, name, retain)


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
