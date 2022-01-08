from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from wakemebot.apt import Repository, RepositoryComponent, RepositoryPackage
from wakemebot.docs import update_documentation

repository_snapshot = Repository(
    package_count=1,
    components=[
        RepositoryComponent(
            name="devops",
            package_count=1,
            packages=[
                RepositoryPackage(
                    name="sometool",
                    summary="Summary",
                    description="Description",
                    homepage="http://sometool.io",
                    versions={"amd64": ["1.0"]},
                )
            ],
        )
    ],
)

component_section_snapshot = """\
<!-- devops.start --># Devops - 1 packages


## [sometool](http://sometool.io)

__Summary__

Description


<span class="badge arch">amd64</span> <span class="badge version">1.0</span>

<!-- devops.end -->"""


package_count_section_snapshot = "<!-- package_count.start -->1<!-- package_count.end -->"


@pytest.fixture
def section_factory(tmp_path):
    def _section_factory(section_name: str) -> Path:
        sample_file = tmp_path / "sample.md"
        sample_file.write_text(
            f"<!-- {section_name}.start --><!-- {section_name}.end -->"
        )
        return sample_file

    return _section_factory


@pytest.mark.parametrize(
    "section,section_snapshot",
    [
        ("package_count", package_count_section_snapshot),
        ("devops", component_section_snapshot),
    ],
)
@patch("wakemebot.docs.parse_repository", Mock(return_value=repository_snapshot))
def test_update_documentation__documentation_section_should_be_equal_to_snapshot(
    tmp_path_working_directory, section_factory, section, section_snapshot
):
    sample_file = section_factory("package_count")
    update_documentation("http://repourl.com", "stable")
    assert sample_file.read_text() == package_count_section_snapshot
