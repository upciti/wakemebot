import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List

from ops2deb import generator, parser


@dataclass
class Package:
    arch: str
    name: str
    version: str


@lru_cache
def parse(file: Path):
    return parser.parse(file).__root__


def match(blueprint: parser.Blueprint, packages: List[Package]) -> bool:
    debian_version = f"{blueprint.version}-{blueprint.revision}~ops2deb"
    # FIXME: handle case where package has been built for multiple archs
    for package in packages:
        if package.name == blueprint.name and package.version == debian_version:
            return True
    return False


def generate(ops2deb_config: Path, repo_state: Path):
    # Packages available in the repo
    packages: List[Package] = [Package(*p) for p in json.load(repo_state.open("r"))]

    # Packages that we need to build because not yet present in repo
    blueprints = parse(ops2deb_config)
    blueprints = [b for b in blueprints if not match(b, packages)]

    generator.generate(blueprints)
