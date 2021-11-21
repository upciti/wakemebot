import re
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from jinja2 import Environment, PackageLoader

from .apt import parse_repository

_environment = Environment(loader=PackageLoader("wakemebot", "templates"))


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


def update_documentation() -> None:
    repository = parse_repository("http://deb.wakemeops.com", "stable")
    update_section("package_count", repository.package_count)
    for component in repository.components:
        template = _environment.get_template("component.md")
        update_section(component.name, template.render(component=component))
