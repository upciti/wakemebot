from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from textwrap import dedent
from typing import Callable, Dict, Generator, List, Set

import httpx
from debian.deb822 import Packages, Release
from debian.debian_support import Version


@dataclass
class RepositoryPackage:
    name: str
    summary: str
    description: str
    homepage: str
    latest_version: str
    component: str
    versions: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))


@dataclass
class RepositoryComponent:
    name: str
    package_count: int
    packages: List[RepositoryPackage]


@dataclass
class Repository:
    architectures: List[str]
    components: List[RepositoryComponent]
    packages: Dict[str, RepositoryPackage]
    package_count: int


@contextmanager
def read_page_content(base_url: str) -> Generator[Callable[[str], str], None, None]:
    with httpx.Client(base_url=base_url, follow_redirects=True) as client:

        def _get(url: str) -> str:
            content_path = Path("/tmp/wakemebot") / url[1:]
            if content_path.exists():
                return content_path.read_text()
            else:
                print(f"Downloading {url}...")
                response = client.get(url)
                response.raise_for_status()
                content_path.parent.mkdir(exist_ok=True, parents=True)
                content_path.write_text(response.text)
                return response.text

        yield _get


def _parse_repository_packages_file(
    component: str, content: str, packages: Dict[str, RepositoryPackage]
) -> None:
    """Extract package names and versions from a repo Packages file"""
    for src in Packages.iter_paragraphs(content, use_apt_pkg=False):
        package_name = src["Package"]
        architecture = src["Architecture"]
        version = Version(src["Version"]).upstream_version
        if package_name not in packages.keys():
            packages[package_name] = RepositoryPackage(
                description=dedent("\n".join(src["Description"].split("\n")[1:])),
                homepage=src.get("Homepage", None),
                name=package_name,
                summary=src["Description"].split("\n")[0],
                latest_version=version or "unknown",
                component=component,
            )
        versions = packages[package_name].versions
        if version is not None:
            versions[version].add(architecture)


def parse_repository(repository_url: str, distribution: str) -> Repository:
    with read_page_content(repository_url) as reader:
        packages: Dict[str, RepositoryPackage] = {}
        release = Release(reader(f"/dists/{distribution}/Release"))
        architectures = release["Architectures"].split(" ")
        component_names = release["Components"].split(" ")
        for component, arch in product(component_names, architectures):
            content = reader(f"/dists/stable/{component}/binary-{arch}/Packages")
            _parse_repository_packages_file(component, content, packages)

    components = []
    for component in component_names:
        component_packages = [p for p in packages.values() if p.component == component]
        repository_component = RepositoryComponent(
            name=component,
            package_count=len(component_packages),
            packages=component_packages,
        )
        components.append(repository_component)

    return Repository(
        architectures=architectures,
        components=components,
        packages={k: v for k, v in sorted(packages.items())},
        package_count=len(packages),
    )
