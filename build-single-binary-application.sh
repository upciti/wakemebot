#!/usr/bin/env bash

set -e

if ! which poetry objdump; then
  echo "Some dependencies are missing, please install"
  echo "poetry, objdump"
  exit 1
fi

# install project dependencies in .venv
POETRY_VIRTUALENVS_IN_PROJECT=true poetry install --no-dev

# https://pyinstaller.readthedocs.io/en/stable
poetry run pip install pyinstaller
poetry run pyinstaller --onefile src/wakemebot/__main__.py --name wakemebot -s

# test wakemebot help cli
dist/wakemebot --help
