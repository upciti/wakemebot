import json
from unittest.mock import Mock, patch

import httpx
import pytest

from wakemebot.aptly import AptlyClient, AptlyClientError, AptlyPackageRef


@patch("wakemebot.aptly.uuid4", Mock(return_value="someuuid"))
def test_files_upload_uploads_files_to_directory(httpx_mock, tmp_path):
    # Given
    package_path = tmp_path / "package.deb"
    package_path.touch()
    httpx_mock.add_response(
        method="POST",
        url="http://test_url/files/someuuid",
    )
    httpx_mock.add_response(
        method="DELETE",
        url="http://test_url/files/someuuid",
    )

    # When
    client = AptlyClient("http://test_url")
    with client.files_upload([package_path]) as upload_directory:
        pass

    # Then
    first_request = httpx_mock.get_requests()[0]
    assert "multipart/form-data;" in first_request.headers["content-type"]
    assert upload_directory == "someuuid"


@patch("wakemebot.aptly.uuid4", Mock(return_value="someuuid"))
def test_files_upload_deletes_upload_directory_when_error_occurs_in_with(
    httpx_mock, tmp_path
):
    # Given
    package_path = tmp_path / "package.deb"
    package_path.touch()
    httpx_mock.add_response(
        method="POST",
        url="http://test_url/files/someuuid",
    )
    httpx_mock.add_response(
        method="DELETE",
        url="http://test_url/files/someuuid",
    )

    # When
    client = AptlyClient("http://test_url")
    with pytest.raises(OSError) as exc:
        with client.files_upload([package_path]):
            raise OSError("great error")

    # Then
    exc.match("great error")


def test_files_upload__raises_when_a_file_does_not_exist(httpx_mock, tmp_path):
    # Given
    client = AptlyClient("http://test_url")

    # When
    with pytest.raises(AptlyClientError) as exc:
        with client.files_upload([tmp_path / "notfound"]):
            pass

    # Then
    assert exc.match(r"No such file or directory: .+notfound")


def test_files_upload__raises_when_a_file_is_a_directory(httpx_mock, tmp_path):
    # Given
    client = AptlyClient("http://test_url")

    # When
    with pytest.raises(AptlyClientError) as exc:
        with client.files_upload([tmp_path]):
            pass

    # Then
    assert exc.match(r"Is a directory: .+")


def test_repo_list__returns_parsed_list_of_aptly_repositories(httpx_mock):
    # Given
    httpx_mock.add_response(
        url="http://test_url/repos",
        json=[
            {
                "Name": "myrepo",
                "Comment": "comment",
                "DefaultDistribution": "buster",
                "DefaultComponent": "main",
            }
        ],
    )

    # When
    client = AptlyClient("http://test_url")
    repos = client.repo_list()

    # Then
    assert repos[0].name == "myrepo"
    assert repos[0].comment == "comment"
    assert repos[0].default_distribution == "buster"
    assert repos[0].default_component == "main"


def test_repo_list__raises_on_httpx_errors(httpx_mock):
    # Given
    httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))

    # When
    client = AptlyClient("http://test_url")

    with pytest.raises(AptlyClientError) as exc:
        client.repo_list()

    # Then
    exc.match("Unable to read within timeout")


def test_repo_list_packages__returns_package_list_when_http_request_succeeds(httpx_mock):
    # Given
    httpx_mock.add_response(
        url="http://test_url/repos/myrepo/packages",
        json=[
            "Parmhf kubectl 1.0.0-1 16bd211dbbf80dc6",
            "Parmhf kubectl 1.1.0-1 16bd211dbbf80dc7",
            "Skubectl 1.1.0~ops2deb 16bd211dbbf80dc6",
        ],
    )

    expected_package_list = [
        AptlyPackageRef(
            arch="armhf", name="kubectl", version="1.0.0-1", uid="16bd211dbbf80dc6"
        ),
        AptlyPackageRef(
            arch="armhf", name="kubectl", version="1.1.0-1", uid="16bd211dbbf80dc7"
        ),
    ]

    # When
    client = AptlyClient("http://test_url")
    packages = client.repo_list_packages("myrepo")

    # Then
    assert packages == expected_package_list


def test_repo_list_packages__raises_aptly_client_error_on_client_error(httpx_mock):
    # Given
    httpx_mock.add_response(
        url="http://test_url/repos/myrepo/packages",
        status_code=404,
    )

    # When
    client = AptlyClient("http://test_url")
    with pytest.raises(AptlyClientError) as exc:
        client.repo_list_packages("myrepo")

    # Then
    assert exc.match("Repo 'myrepo' does not exist")


def test_repo_list_packages__raises_aptly_client_error_on_server_error(httpx_mock):
    # Given
    httpx_mock.add_response(
        url="http://test_url/repos/myrepo/packages",
        status_code=500,
    )

    # When
    client = AptlyClient("http://test_url")
    with pytest.raises(AptlyClientError) as exc:
        client.repo_list_packages("myrepo")

    # Then
    assert exc.match(
        "500 Internal Server Error for url http://test_url/repos/myrepo/packages"
    )


def test_repo_add_packages__adds_packages_from_upload_directory_to_repo(
    httpx_mock, tmp_path
):
    # Given
    httpx_mock.add_response(
        method="POST",
        url="http://test_url/repos/myrepo/file/someuuid?noRemove=1",
    )

    # When
    client = AptlyClient("http://test_url")
    client.repo_add_packages("myrepo", "someuuid")

    # Then


def test_repo_add_packages__raises_when_repo_does_not_exist(httpx_mock, tmp_path):
    # Given
    httpx_mock.add_response(status_code=404)
    client = AptlyClient("http://test_url")

    # When
    with pytest.raises(AptlyClientError) as exc:
        client.repo_add_packages("myrepo", "someuuid")

    # Then
    assert exc.match("Repo 'myrepo' does not exist")


def test_repo_remove_packages__does_delete_request_with_package_list_in_body(httpx_mock):
    # Given
    packages = [
        AptlyPackageRef("amd64", "kubectl", "1.0.0-2~ops2deb", "_"),
        AptlyPackageRef("amd64", "kubectl", "1.0.1-3~ops2deb", "_"),
    ]

    httpx_mock.add_response(
        method="DELETE",
        url="http://test_url/repos/myrepo/packages",
    )

    expected_request_dict = {
        "PackageRefs": [
            "Pamd64 kubectl 1.0.0-2~ops2deb _",
            "Pamd64 kubectl 1.0.1-3~ops2deb _",
        ]
    }

    # When
    client = AptlyClient("http://test_url")
    client.repo_remove_packages("myrepo", packages)

    # Then
    assert json.loads(httpx_mock.get_request().content) == expected_request_dict


def test_publish_update__does_put_request_with_prefix_on_publish_endpoint(httpx_mock):
    # Given
    httpx_mock.add_response(
        method="PUT",
        url="http://test_url/publish/myprefix:.",
    )

    expected_request_dict = [
        {"ForceOverwrite": True, "Signing": {"GpgKey": "mykey", "Batch": True}}
    ]

    # When
    client = AptlyClient("http://test_url")
    client.publish_update("myprefix:.", "mykey")

    # Then
    assert json.loads(httpx_mock.get_request().content) == expected_request_dict
