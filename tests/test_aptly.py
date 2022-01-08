from unittest.mock import patch

from wakemebot.aptly import (
    Package,
    delete_packages,
    parse_packages,
    purge,
    purge_old_patches,
    purge_old_revisions,
    purge_old_versions,
)


def test_parse_packages_should_return_package_list():
    data = [
        "Parmhf kubectl 1.0.0-1 16bd211dbbf80dc6",
        "Parmhf kubectl 1.1.0-1 16bd211dbbf80dc7",
        "Skubectl 1.1.0~ops2deb 16bd211dbbf80dc6",
    ]
    assert parse_packages(data) == [
        Package(arch="armhf", name="kubectl", version="1.0.0-1", uid="16bd211dbbf80dc6"),
        Package(arch="armhf", name="kubectl", version="1.1.0-1", uid="16bd211dbbf80dc7"),
    ]


def test_purge_old_revisions__should_only_keep_latest_revision_of_a_package():
    packages = [
        Package("_", "_", "2.0.1-2~ops2deb", "_"),
        Package("_", "_", "2.0.1-3~ops2deb", "_"),
        Package("_", "_", "2.0.3-1~ops2deb", "_"),
        Package("_", "_", "2.0.3-2~ops2deb", "_"),
        Package("_", "_", "2.0.3-4~ops2deb", "_"),
    ]
    packages = purge_old_revisions(packages)
    assert packages == [
        Package("_", "_", "2.0.1-2~ops2deb", "_"),
        Package("_", "_", "2.0.3-1~ops2deb", "_"),
        Package("_", "_", "2.0.3-2~ops2deb", "_"),
    ]


def test_purge_old_patches__should_only_keep_latest_patch_version_of_a_package():
    packages = [
        Package("_", "_", "notsemver-1~ops2deb", "_"),
        Package("_", "_", "2.0.1-1~ops2deb", "_"),
        Package("_", "_", "2.0.2-1~ops2deb", "_"),
        Package("_", "_", "2.0.3-1~ops2deb", "_"),
        Package("_", "_", "2.1.2-1~ops2deb", "_"),
        Package("_", "_", "2.1.3-1~ops2deb", "_"),
    ]
    packages = purge_old_patches(packages)
    assert packages == [
        Package("_", "_", "2.0.1-1~ops2deb", "_"),
        Package("_", "_", "2.0.2-1~ops2deb", "_"),
        Package("_", "_", "2.1.2-1~ops2deb", "_"),
    ]


def test_purge_old_versions__should_only_keep_latest_versions_of_a_package():
    packages = [
        Package("_", "_", "2.0.1-2~ops2deb", "_"),
        Package("_", "_", "2.0.1-3~ops2deb", "_"),
        Package("_", "_", "2.0.3-2~ops2deb", "_"),
    ]
    packages = purge_old_versions(packages, 2)
    assert packages == [
        Package("_", "_", "2.0.1-2~ops2deb", "_"),
    ]


@patch("wakemebot.aptly.httpx.Client", autospec=True)
def test_delete_packages__should_send_properly_formatted_request(mock_client):
    packages = {
        Package("amd64", "kubectl", "1.0.1-3~ops2deb", "_"),
        Package("amd64", "kubectl", "1.0.0-2~ops2deb", "_"),
    }
    delete_packages(mock_client, packages, "devops")
    mock_client.request.assert_called_once_with(
        "DELETE",
        "/repos/devops/packages",
        json={
            "PackageRefs": [
                "Pamd64 kubectl 1.0.0-2~ops2deb _",
                "Pamd64 kubectl 1.0.1-3~ops2deb _",
            ]
        },
    )


@patch(
    "wakemebot.aptly.list_packages",
    return_value=[
        Package("amd64", "kubectl", "1.0.1-3~ops2deb", "_"),
        Package("amd64", "kubectl", "1.0.1-2~ops2deb", "_"),
        Package("amd64", "kubectl", "1.0.2-2~ops2deb", "_"),
        Package("amd64", "kubectl", "1.0.2-1~ops2deb", "_"),
        Package("amd64", "kustomize", "0.12.0-1~ops2deb", "_"),
        Package("amd64", "kustomize", "0.13.0-1~ops2deb", "_"),
        Package("amd64", "kustomize", "0.15.0-1~ops2deb", "_"),
        Package("amd64", "kustomize", "0.14.0-1~ops2deb", "_"),
        Package("armhf", "kustomize", "0.12.0-1~ops2deb", "_"),
        Package("armhf", "kustomize", "0.12.0-2~ops2deb", "_"),
    ],
)
@patch("wakemebot.aptly.httpx.Client", autospec=True)
def test_purge__should_delete_old_package_versions_and_revisions(_, mock_client):
    purge(mock_client, "devops", {"kubectl", "kustomize"}, retain_how_many=3)
    mock_client.request.assert_called_with(
        "DELETE",
        "/repos/devops/packages",
        json={
            "PackageRefs": [
                "Pamd64 kustomize 0.12.0-1~ops2deb _",
                "Parmhf kustomize 0.12.0-1~ops2deb _",
                "Pamd64 kubectl 1.0.1-2~ops2deb _",
                "Pamd64 kubectl 1.0.1-3~ops2deb _",
                "Pamd64 kubectl 1.0.2-1~ops2deb _",
            ]
        },
    )
