import os
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path_working_directory(tmp_path):
    previous_cwd = Path.cwd()
    os.chdir(str(tmp_path))
    yield
    os.chdir(previous_cwd)
