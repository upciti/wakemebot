from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, Mock, call

import pytest

from wakemebot.aptly import AptlyPackageRef
from wakemebot.sync import (
    Ops2debDelta,
    Package,
    add_packages_to_repos,
    parse_op2deb_delta,
    remove_packages_from_repos,
)


@pytest.fixture
def ops2deb_delta_path(tmp_path) -> Path:
    return tmp_path / "delta.json"


@pytest.fixture
def ops2deb_delta(ops2deb_delta_path) -> str:
    content = """
    {
      "added": [],
      "removed": [
        {
          "architecture": "amd64",
          "name": "stern",
          "version": "1.11.0-1~ops2deb"
        }
      ]
    }
    """
    content = dedent(content)
    ops2deb_delta_path.write_text(content)
    return content


def test_parse_op2deb_delta__returns_parsed_delta(ops2deb_delta, ops2deb_delta_path):
    delta = parse_op2deb_delta(ops2deb_delta_path)
    assert delta.added == []
    assert delta.removed == [
        Package(architecture="amd64", name="stern", version="1.11.0-1~ops2deb")
    ]


def test_remove_packages_from_repos__calls_aptly_client_remove_packages(
    ops2deb_delta, ops2deb_delta_path
):
    # Given
    repo0 = Mock()
    repo0.name = "repo0"
    repo1 = Mock()
    repo1.name = "repo1"

    package0 = AptlyPackageRef(
        arch="armhf", name="kubectl", version="1.0.0-1", uid="16bd211dbbf80dc6"
    )
    package1 = AptlyPackageRef(
        arch="armhf", name="kubectl", version="1.1.0-1", uid="16bd211dbbf80dc7"
    )
    client = Mock()
    client.repo_list.return_value = [repo0, repo1]
    client.repo_list_packages.return_value = [package0, package1]

    delta = Ops2debDelta(
        added=[],
        removed=[Package(architecture="armhf", name="kubectl", version="1.0.0-1")],
    )

    # When
    remove_packages_from_repos(client, delta)

    # Then
    client.repo_remove_packages.assert_has_calls(
        [call("repo0", [package0]), call("repo1", [package0])]
    )


def test_add_packages_to_repos__adds_packages_to_the_appropriate_aptly_repository(
    tmp_path,
):
    # Given
    client = MagicMock()
    client.files_upload.return_value.__enter__.return_value = "someuuid"
    package0 = tmp_path / "devops" / "package0.deb"
    package1 = tmp_path / "terminal" / "package1.deb"
    package0.parent.mkdir()
    package0.touch()
    package1.parent.mkdir()
    package1.touch()

    # When
    add_packages_to_repos(client, tmp_path, "wakemeops-")

    # Then
    client.repo_add_packages.assert_has_calls(
        [call("wakemeops-devops", "someuuid"), call("wakemeops-terminal", "someuuid")]
    )
