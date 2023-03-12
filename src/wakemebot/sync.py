from pathlib import Path

from pydantic import BaseModel

from wakemebot.aptly import AptlyClient, AptlyClientError, AptlyPackageRef


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
        try:
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
        except AptlyClientError as e:
            print(f"Failed to remove packages from repo {repo.name}: {e}")


def add_packages_to_repos(
    client: AptlyClient, package_directory: Path, repos_prefix: str
) -> None:
    for package in package_directory.glob("**/*.deb"):
        component = package.parent.name
        try:
            with client.files_upload([package]) as upload_directory:
                client.repo_add_packages(f"{repos_prefix}{component}", upload_directory)
        except AptlyClientError as e:
            print(f"Failed to add package {package}: {e}")


def publish_debian_repository(
    client: AptlyClient, publish_prefix: str, gpg_key: str
) -> None:
    try:
        client.publish_update(publish_prefix, gpg_key=gpg_key)
    except AptlyClientError as e:
        print(f"Failed to update debian repository: {e}")
