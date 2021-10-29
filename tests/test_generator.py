from pathlib import Path
from unittest.mock import patch

from wakemebot.generator import generate


@patch("wakemebot.generator.generator.generate")
def test_generate_should_properly_determine_which_blueprints_to_generate(
    mock_generate, mock_ops2deb_config, mock_repo_state_file
):
    generate(mock_ops2deb_config, mock_repo_state_file, Path("output"))
    package_names = [p.name for p in mock_generate.call_args.args[0]]
    assert "helmfile" not in package_names
    assert "istioctl" not in package_names
    assert "mypackage1" in package_names
    assert "mypackage2" in package_names
