import re
from functools import lru_cache
from pathlib import Path
from typing import Any, List

import anybadge
from jinja2 import Environment

from .apt import RepositoryComponent, parse_repository
from .templates import COMPONENT_PACKAGE_LIST, PACKAGE_PERMALINK

environment = Environment()


@lru_cache
def list_markdown_and_html_files() -> List[Path]:
    current_directory = Path(".")
    files: List[Path] = []
    for pattern in ["**/*.md", "**/*.html"]:
        files.extend(current_directory.glob(pattern))
    return files


def update_section(section_name: str, content: Any) -> None:
    start = f"<!-- {section_name}.start -->"
    end = f"<!-- {section_name}.end -->"
    regex = re.compile(rf"{start}(.*){end}", re.DOTALL | re.MULTILINE)
    for file_ in list_markdown_and_html_files():
        file_content = file_.read_text()
        if regex.findall(file_content):
            print(f"Updated section '{section_name}' in {file_}")
            output = regex.sub(f"{start}{content}{end}", file_.read_text())
            file_.write_text(output)


def update_package_permalinks(component: RepositoryComponent) -> None:
    packages_path = Path("docs/packages")
    template = environment.from_string(PACKAGE_PERMALINK)
    for package in component.packages:
        content = template.render(component=component.name, package=package.name)
        package_path = packages_path / package.name
        package_path.mkdir(exist_ok=True, parents=True)
        (package_path / "index.html").write_text(content)
    print(f"Updated permalinks for {component.name} component")


def update_package_badges(component: RepositoryComponent) -> None:
    badges_path = Path("docs/badges")
    badges_path.mkdir(exist_ok=True, parents=True)
    for package in component.packages:
        badge = anybadge.Badge(
            label="wakemeops", value=f"v{package.latest_version}", default_color="purple"
        )
        badge.write_badge(str(badges_path / f"{package.name}.svg"), overwrite=True)
    print(f"Updated badges for {component.name} component")


def update_documentation(repository_url: str, distribution: str) -> None:
    repository = parse_repository(repository_url, distribution)
    update_section("package_count", repository.package_count)
    for component in repository.components:
        template = environment.from_string(COMPONENT_PACKAGE_LIST)
        update_section(component.name, template.render(component=component))
        update_package_permalinks(component)
        update_package_badges(component)
