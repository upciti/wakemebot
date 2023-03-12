from pathlib import Path

from pydantic import BaseModel

from wakemebot.aptly import AptlyClient, AptlyPackageRef


class Package(BaseModel):
    architecture: str
    name: str
    version: str


class Ops2debDelta(BaseModel):
    added: list[Package]
    removed: list[Package]


def parse_op2deb_delta(path: Path) -> Ops2debDelta:
    return Ops2debDelta.parse_file(path)


def remove_packages_from_repos(client: AptlyClient, delta: Ops2debDelta) -> None:
    repositories = client.repo_list()
    for repo in repositories:
        repo_packages = client.repo_list_packages(repo.name)
        to_remove: list[AptlyPackageRef] = []
        for repo_package in repo_packages:
            for package in delta.removed:
                if (
                    repo_package.name == package.name
                    and repo_package.version == package.version
                    and repo_package.arch == package.architecture
                ):
                    to_remove.append(repo_package)
        client.repo_remove_packages(repo.name, to_remove)
