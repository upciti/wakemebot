import contextlib
import re
import sys
from pathlib import Path
from typing import Any, Dict, Generator, List, Union

import pygit2
import ruamel.yaml
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from ops2deb.exceptions import Ops2debError
from ops2deb.parser import parse
from ops2deb.updater import FixIndentEmitter, LatestRelease, find_latest_releases
from ruamel.yaml import YAML, YAMLError

GIT_AUTHOR = pygit2.Signature("wakemebot", "wakemebot@users.noreply.github.com")
GIT_COMMITTER = pygit2.Signature("wakemebot", "wakemebot@protonmail.com")

BRANCH_NAME_TEMPLATE = (
    "chore/wakemebot-update-{release.blueprint.name}-"
    "from-{release.blueprint.version}-to-{release.version}"
)

COMMIT_MESSAGE_TEMPLATE = (
    "chore(bot): update {release.blueprint.name} "
    "from {release.blueprint.version} to {release.version}"
)


def load(
    configuration_content: str, yaml: YAML = YAML()
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        return yaml.load(configuration_content)
    except YAMLError as e:
        print(f"Invalid YAML file.\n{e}")
        sys.exit(1)


def yaml_factory() -> ruamel.yaml.YAML:
    yaml = ruamel.yaml.YAML(typ="rt")
    yaml.Emitter = FixIndentEmitter
    return yaml


def find_configuration_files(repository_path: Path) -> List[Path]:
    paths = list(repository_path.glob("**/*ops2deb*.yml"))
    print(f"Found {len(paths)} ops2deb configuration files")
    return paths


def find_blueprint_updates(
    configuration_path: Path,
    skip_names: List[str] = None,
) -> Generator[LatestRelease, None, None]:
    try:
        blueprints = parse(configuration_path)
    except Ops2debError as e:
        print(e)
        return

    print(f"Looking for new releases in {configuration_path}")
    releases, _ = find_latest_releases(blueprints, skip_names)
    releases or print("Did not find any updates")

    for release in releases:
        yield release


@contextlib.contextmanager
def update_configuration(
    configuration_path: Path, release: LatestRelease
) -> Generator[None, None, None]:
    original_content = configuration_path.read_text()
    yaml = yaml_factory()
    configuration_dict = yaml.load(configuration_path.read_text())
    release.update_configuration(configuration_dict)
    with configuration_path.open("w") as output:
        yaml.dump(configuration_dict, output)
    yield
    configuration_path.write_text(original_content)


def parse_git_remote(repo: pygit2.Repository) -> str:
    remote = repo.remotes["origin"]
    result = re.search(r"/([^/]+/[^/]+).git", remote.url)
    if result is None:
        raise ValueError("Not a Github repository")
    return result.group(1)


def create_branch_and_commit(
    repo: pygit2.Repository,
    configuration_path: Path,
    branch_name: str,
    commit_message: str,
) -> None:
    try:
        commit = repo[repo.head.target]
        branch = repo.branches.create(branch_name, commit, force=True)
        repository_path = Path(
            pygit2.discover_repository(configuration_path.parent)
        ).parent
        repo.index.add(configuration_path.relative_to(repository_path))
        repo.index.write()
        tree = repo.index.write_tree()
        parent, ref = repo.resolve_refish(refish=branch.name)
        repo.create_commit(
            branch.name, GIT_AUTHOR, GIT_COMMITTER, commit_message, tree, [parent.oid]
        )
    except pygit2.GitError as e:
        print(f"Failed to create branch {branch_name}: {e}")


def push_branch(repo: pygit2.Repository, access_token: str, branch_name: str) -> None:
    try:
        remote = repo.remotes["origin"]
        credentials = pygit2.UserPass("wakemebot", access_token)
        callbacks = pygit2.RemoteCallbacks(credentials)
        branch = repo.branches.get(branch_name)
        remote.push([branch.name], callbacks)
    except pygit2.GitError as e:
        print(f"Failed to push branch {branch_name}: {e}")


def create_pull_request(
    repo: pygit2.Repository,
    access_token: str,
    branch_name: str,
    commit_message: str,
) -> None:
    transport = AIOHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)
    query = gql(
        """
        query createPullRequest ($code: ID!) {
          continent (code: $code) {
            name
          }
        }
    """
    )
    github_repo = parse_git_remote(repo)
    result = client.execute(query, variable_values={"repo": github_repo})
    print(result)


def create_pull_requests(repository_path: Path, access_token: str) -> None:
    configuration_paths = find_configuration_files(repository_path)
    repo = pygit2.Repository(repository_path)
    for configuration_path in configuration_paths:
        for release in find_blueprint_updates(configuration_path):
            with update_configuration(configuration_path, release):
                branch_name = BRANCH_NAME_TEMPLATE.format(release=release)
                commit_message = COMMIT_MESSAGE_TEMPLATE.format(release=release)
                create_branch_and_commit(
                    repo, configuration_path, branch_name, commit_message
                )
                push_branch(repo, access_token, branch_name)
                create_pull_request(repo, access_token, branch_name, commit_message)
