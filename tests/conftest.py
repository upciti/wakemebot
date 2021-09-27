import json
from pathlib import Path

import pytest

devops_yml = """
- name: mypackage1
  version: 1.0.0
  arch: all
  summary: Great package
  description: Great description 
  script:
    - touch {{src}}/usr/bin/great-app

- name: mypackage2
  version: 1.0.0
  arch: all
  summary: Great package
  description: Great description 
  script:
    - touch {{src}}/usr/bin/great-app
    
- name: helmfile
  version: 0.135.0
  arch: amd64
  summary: Great package
  description: Great description 
  script:
    - touch {{src}}/usr/bin/great-app
    
- name: istioctl 
  version: 1.6.13
  arch: amd64
  revision: 2
  summary: Great package
  description: Great description 
  script:
    - touch {{src}}/usr/bin/great-app
"""


@pytest.fixture
def mock_repo_state():
    return [
        ["amd64", "helmfile", "0.135.0-1~ops2deb"],
        ["amd64", "istioctl", "1.6.13-2~ops2deb"],
        ["amd64", "istioctl", "1.6.13-1~ops2deb"],
        ["amd64", "istioctl", "1.8.1-1~ops2deb"],
        ["amd64", "kubectl", "1.20.1-1~ops2deb"],
        ["amd64", "kubeseal", "0.13.1-1~ops2deb"],
        ["amd64", "kustomize", "3.8.8-1~ops2deb"],
        ["amd64", "minikube", "1.16.0-1~ops2deb"],
        ["amd64", "helm", "3.4.2-1~ops2deb"],
    ]


@pytest.fixture
def mock_ops2deb_config(tmp_path) -> Path:
    path = tmp_path / "devops.yml"
    path.write_text(devops_yml)
    return path


@pytest.fixture
def mock_repo_state_file(tmp_path, mock_repo_state):
    path = tmp_path / "repo-state.json"
    path.write_text(json.dumps(mock_repo_state))
    return path
