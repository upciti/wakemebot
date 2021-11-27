from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Iterator, List

import httpx
from debian.deb822 import Packages, Release
from debian.debian_support import Version


@dataclass
class RepositoryPackage:
    name: str
    versions: List[Version]
    summary: str
    description: str


@dataclass
class RepositoryComponent:
    name: str
    package_count: int
    packages: List[RepositoryPackage]


@dataclass
class Repository:
    package_count: int
    components: List[RepositoryComponent]


def _download_repository_release_file(client: httpx.Client, distribution: str) -> Release:
    url = f"/dists/{distribution}/Release"
    response = client.get(url)
    response.raise_for_status()
    return Release(response.text)


@lru_cache
def _download_repository_packages_file(
    client: httpx.Client, distribution: str, component: str, arch: str
) -> bytes:
    url = f"/dists/{distribution}/{component}/binary-{arch}/Packages"
    print(f"Downloading {url}...")
    with client.stream("GET", url) as response:
        response.raise_for_status()
        return response.read()


def _parse_repository_packages_file(content: bytes) -> Iterator[RepositoryPackage]:
    """Extract package names and versions from a repo Packages file"""
    packages: Dict[str, Dict[str, Any]] = {}
    for src in Packages.iter_paragraphs(content, use_apt_pkg=False):
        package_name = src["Package"]
        if package_name not in packages.keys():
            packages[package_name] = {"description": src["Description"], "versions": []}
        packages[package_name]["versions"].append(Version(src["Version"]))
    for name, info in packages.items():
        description_lines = info["description"].split("\n")
        summary = description_lines[0]
        description = "\n".join(description_lines[1:])
        yield RepositoryPackage(name, info["versions"], summary, description)


def _build_repository_component(
    client: httpx.Client, component: str, architectures: List[str]
) -> RepositoryComponent:
    packages: List[RepositoryPackage] = []
    for architecture in architectures:
        content = _download_repository_packages_file(
            client, "stable", component, architecture
        )
        packages.extend(_parse_repository_packages_file(content))
    return RepositoryComponent(
        name=component, packages=packages, package_count=len(packages)
    )


def parse_repository(
    repository_url: str,
    distribution: str,
) -> Repository:
    with httpx.Client(base_url=repository_url) as client:
        release = _download_repository_release_file(client, distribution)
        architectures = release["Architectures"].split(" ")
        components = release["Components"].split(" ")
        repository_components = [
            _build_repository_component(client, c, architectures) for c in components
        ]
    return Repository(
        components=repository_components,
        package_count=sum([c.package_count for c in repository_components]),
    )
