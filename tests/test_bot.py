import base64
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock, patch

import httpx
import pygit2
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response

from wakemebot.bot import (
    GIT_AUTHOR,
    GIT_COMMITTER,
    create_pull_requests,
    parse_git_remote,
)


@pytest.fixture
def ops2deb_configuration(tmp_path) -> Path:
    configuration = """\
    - name: great-app
      version: 1.0.0
      summary: Great package
      description: A detailed description of the great package.
      fetch:
        url: http://testserver/{{version}}/great-app.tar.gz
        sha256: f1be6dd36b503641d633765655e81cdae1ff8f7f73a2582b7468adceb5e212a9
      script:
        - mv great-app {{src}}/usr/bin/great-app

    - name: super-app
      version: 1.0.0
      summary: Super package
      description: A detailed description of the great package.
      fetch:
        url: http://testserver/{{version}}/great-app.tar.gz
        sha256: f1be6dd36b503641d633765655e81cdae1ff8f7f73a2582b7468adceb5e212a9
      script:
        - mv super-app {{src}}/usr/bin/super-app
    """
    configuration_path = tmp_path / "ops2deb.yml"
    configuration_path.write_text(dedent(configuration))
    return configuration_path


@pytest.fixture
def server() -> Starlette:
    starlette_app = Starlette(debug=True)

    @starlette_app.route("/1.1.0/great-app.tar.gz")
    @starlette_app.route("/1.1.1/great-app.tar.gz")
    async def server_great_app_tar_gz(request: Request):
        response = b"""H4sIAAAAAAAAA+3OMQ7CMBAEQD/FH0CyjSy/xwVCFJAoCf/HFCAqqEI1U9yudF
            fceTn17dDnOewnDa3VZ+ZW02e+hHxsrYxRagkp59FDTDv+9HZft77EGNbLdbp9uf
            u1BwAAAAAAAAAAgD96AGPmdYsAKAAA"""
        return Response(
            base64.b64decode(response),
            status_code=200,
            media_type="application/x-gzip",
        )

    return starlette_app


@pytest.fixture(scope="function")
def client(server):
    real_async_client = httpx.AsyncClient

    def async_client_mock(**kwargs):
        kwargs.pop("transport", None)
        return real_async_client(app=server, **kwargs)

    httpx.AsyncClient = async_client_mock
    yield
    httpx.AsyncClient = real_async_client


@pytest.fixture
def repo(tmp_path, ops2deb_configuration) -> pygit2.init_repository:
    repo = pygit2.init_repository(tmp_path, False)
    repo.index.add(ops2deb_configuration.name)
    repo.index.write()
    tree = repo.index.write_tree()
    repo.create_commit("HEAD", GIT_AUTHOR, GIT_COMMITTER, "initial commit", tree, [])
    repo.remotes.create("origin", "https://github.com/upciti/wakemeops.git")
    return repo


def test_parse_git_remote_should_return_organization_and_repo_names(repo):
    assert parse_git_remote(repo) == "upciti/wakemeops"


@patch("wakemebot.bot.push_branch", Mock())
@patch("wakemebot.bot.create_pull_request", Mock())
def test_create_pull_requests_should_create_as_many_branches_as_they_are_updates(
    client, tmp_path, repo
):
    create_pull_requests(tmp_path, "")
    assert repo.branches.get("chore/wakemebot-update-great-app-from-1.0.0-to-1.1.1")
    assert repo.branches.get("chore/wakemebot-update-super-app-from-1.0.0-to-1.1.1")


@patch("wakemebot.bot.push_branch", Mock())
@patch("wakemebot.bot.create_pull_request", Mock())
def test_create_pull_requests_should_reset_branch_if_it_already_exists(
    client, tmp_path, repo
):
    branch_name = "chore/wakemebot-update-great-app-from-1.0.0-to-1.1.1"
    commit = repo[repo.head.target]
    repo.branches.create(branch_name, commit)
    create_pull_requests(tmp_path, "")


@patch("wakemebot.bot.push_branch", Mock())
@patch("wakemebot.bot.create_pull_request", Mock())
def test_create_pull_requests_commit_message_should_mention_blueprint_and_versions(
    client, tmp_path, repo
):
    create_pull_requests(tmp_path, "")
    branch = repo.branches.get("chore/wakemebot-update-super-app-from-1.0.0-to-1.1.1")
    commit = repo[branch.target]
    commit_message = "chore(bot): update super-app from 1.0.0 to 1.1.1"
    assert commit.message == commit_message
