from pathlib import Path
from random import sample
from typing import Any, Dict, List, Optional

from jinja2 import Environment
from mkdocs.config import Config
from mkdocs.config.config_options import Type
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page
from mkdocs.structure.toc import AnchorLink, TableOfContents

from .apt import parse_repository
from .badges import Badge

filters = {"sample": sample}

environment = Environment()
environment.filters.update(filters)


class WakeMeDocPlugin(BasePlugin):
    config_scheme = (
        ("repository_url", Type(str, default="http://deb.wakemeops.com/wakemeops/")),
        ("distribution", Type(str, default="stable")),
    )

    def __init__(self) -> None:
        self.tmp_path = Path("/tmp/wakemebot")

    def generate_package_navigation(self, nav: List[Any]) -> Optional[Path]:
        packages_dir: Optional[Path] = None
        for entry in nav:
            if isinstance(entry, dict):
                for k, v in entry.items():
                    if isinstance(v, list):
                        packages_dir = self.generate_package_navigation(v)
            if "..." in entry:
                packages_dir = Path(entry["..."]).parent
                nav.remove(entry)
                nav.extend(
                    [
                        {name: str(packages_dir / f"{name}.md")}
                        for name in self.packages.keys()
                    ]
                )
                return packages_dir
        return packages_dir

    def generate_package_markdown(self, files: Files, site_dir: str) -> None:
        if self.packages_dir is None:
            return
        (self.tmp_path / self.packages_dir).mkdir(exist_ok=True, parents=True)

        template_content = None
        for file in files:
            if file.src_path == str(self.packages_dir / "template.md"):
                template_content = Path(file.abs_src_path).read_text()
                files.remove(file)
                break
        if template_content is None:
            return

        for package in self.packages.values():
            file_name = f"{package.name}.md"
            output_path = self.tmp_path / self.packages_dir / file_name
            output_path.write_text(template_content)
            file = File(
                path=str(self.packages_dir / file_name),
                src_dir=str(self.tmp_path),
                dest_dir=site_dir,
                use_directory_urls=True,
            )
            files.append(file)

    def generate_package_badges(self, files: Files, site_dir: str) -> None:
        badges_dir = Path("badges")
        for package in self.packages.values():
            file_name = f"{package.name}.svg"
            output_path = self.tmp_path / badges_dir / file_name
            Badge(package.latest_version).save(output_path)
            file = File(
                path=str(badges_dir / file_name),
                src_dir=str(self.tmp_path),
                dest_dir=site_dir,
                use_directory_urls=True,
            )
            files.append(file)

    def on_config(self, config: Config) -> Config:
        self.repository = parse_repository(
            self.config["repository_url"], self.config["distribution"]
        )
        self.packages = self.repository.packages
        self.docs_dir = Path(config["docs_dir"])
        self.nav = config["nav"]
        self.packages_dir = self.generate_package_navigation(self.nav)
        return config

    def on_files(self, files: Files, config: Config) -> Files:
        self.generate_package_markdown(files, config["site_dir"])
        self.generate_package_badges(files, config["site_dir"])
        return files

    def on_env(self, env: Environment, config: Config, files: Files) -> Environment:
        env.globals.update({"repository": self.repository, "packages": self.packages})
        env.filters.update(filters)
        return env

    def on_page_context(
        self, context: Dict[str, Any], page: Page, config: Config, nav: Navigation
    ) -> Dict[str, Any]:
        # Only enable toc.integrate on Usage page
        features: List[str] = config["theme"]["features"]
        if page.title == "Usage":
            features.append("toc.integrate")
        else:
            if "toc.integrate" in features:
                features.remove("toc.integrate")

        # Use toc to list package versions on package pages
        if (package := self.packages.get(page.title, None)) is not None:
            items = [AnchorLink(v, v, 0) for v in package.versions.keys()]
            page.toc = TableOfContents(items)
            config["mdx_configs"]["toc"] = {"title": "Versions"}
            page.toc.title = "Versions"
        else:
            config["mdx_configs"].pop("toc", None)

        return context

    def on_page_markdown(
        self, markdown: str, page: Page, config: Config, files: Files
    ) -> str:
        template = environment.from_string(markdown)
        return template.render(
            repository=self.repository,
            title=page.title,
            config=config,
        )
