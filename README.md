[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![Generic badge](https://img.shields.io/badge/type_checked-mypy-informational.svg)](https://mypy.readthedocs.io/en/stable/introduction.html)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# wakemebot

Bunch of tools needed in [wakemeops](https://github.com/upciti/wakemeops) CI pipelines.

## Usage examples

Start aptly sandbox, create a repo, push packages:

```shell
cd aptly
docker-compose up
docker-compose exec aptly aptly repo create wakemeops-devops
cd ..
poetry run wakemebot aptly push wakemeops-devops output --server aptly/aptly.sock
```

Update wakemeops documentation:

```shell
cd wakemeops
wakemebot docs
```

## Building single binary application

Install required build dependencies:

```shell
sudo apt install binutils python3-dev
poetry install -E pyinstaller
```

And run:

```shell
poetry run task single_binary_application
```

Note that if your venv is using a python distribution built using pyenv, pyinstaller may not work.

If this is the case, build inside a docker container, or follow the instructions here:
https://pyinstaller.readthedocs.io/en/stable/development/venv.html
