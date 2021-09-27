from unittest.mock import Mock, patch

import pytest

from wakemebot import git


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (
            "* Add kubectl v1.20",
            git.Entry(verb="Add", name="kubectl", version="1.20"),
        ),
        (
            "* Update kubectl to v1.20",
            git.Entry(verb="Update", name="kubectl", version="1.20"),
        ),
    ],
)
def test_parse_line_should_succeed_when_message_is_properly_formatted(
    test_input, expected
):
    entry = git.parse_line(test_input)
    assert entry == expected


@pytest.mark.parametrize(
    "test_input",
    [
        "* Add Kubectl v1.20",
        "* Udpate kubectl to v1.20",
        "* Update kubectl ot v1.20",
    ],
)
def test_parse_line_should_fail_when_message_is_ill_formed(test_input):
    with pytest.raises(ValueError):
        git.parse_line(test_input)


mock_git_message = """

* Add mypackage1 v1.0.0
* Add mypackage2 v1.0.0
* Add mypackage3 v1.0.0
"""


def test_parse_commit_message_should_succeed_with_valid_git_message():
    git.parse_commit_message(mock_git_message)
