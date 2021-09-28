[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![Generic badge](https://img.shields.io/badge/type_checked-mypy-informational.svg)](https://mypy.readthedocs.io/en/stable/introduction.html)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# wakemebot

Bunch of tools needed in [wakemeops](https://github.com/upciti/wakemeops) CI pipelines.

## Usage examples

This should only build kustomize and helmfile because they do not appear in repository state file:

```shell
poetry run wakemebot generate ops2deb.yml repo-state-example.json
poetry run ops2deb build
```

Start aptly sandbox, create a repo, push packages:

```shell
cd aptly
docker-compose up
docker-compose exec aptly aptly repo create wakemeops-devops
cd ..
poetry run wakemebot aptly push wakemeops-devops output/*.deb --server aptly/aptly.sock
```

Get repo state file:

```shell
poetry run wakemebot aptly export wakemeops-devops --server aptly/aptly.sock
```
