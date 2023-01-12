import dataclasses
import os
import re
from typing import Iterator

from file_routes.filerouteinfo import FileRouteAndView, FileRouteInfo, WebFramework
from file_routes.inspection import (
    CheckWarning,
    import_filename_and_guess_module_from_path,
    inspect_module,
)
from file_routes.utils import route_contains_invalid_characters

RE_WILDCARD = re.compile(r"\[((?P<converter>[^_]+)_|)(?P<name>[^]]+)]")


@dataclasses.dataclass
class DirectoryVisitor:
    framework: WebFramework
    extensions: list[str] = dataclasses.field(default_factory=lambda: ["py"])

    def visit_and_analyze(self, directory: str) -> list[FileRouteAndView]:
        route_views = []
        for file_route in self.collect_routes_from_directory(
            directory, extensions=self.extensions
        ):
            module = import_filename_and_guess_module_from_path(file_route.filename)
            inspected_module = inspect_module(module)
            if view := self.framework.analyze(
                file_route=file_route, inspected_module=inspected_module
            ):
                route_views.append(FileRouteAndView(file_route, view))
            else:
                CheckWarning(
                    f"Could not find a view in {file_route.name}",
                    hint="Create a view function called view or a class called View.",
                    code="fileroutes.W004",
                )

        return route_views

    def expand_filename(self, filename: str) -> tuple[str, bool]:
        was_transformed = False
        if match := RE_WILDCARD.match(filename):
            filename = self.framework.expand_wildcards(filename, match)
            was_transformed = True
        return filename, was_transformed

    def directory_expand_converters(self, directory_route: str) -> str:
        # foo/[slug]/bar -> foo/<slug:slug>/bar
        if directory_route.startswith("/"):
            directory_route = directory_route[1:]
        parts = []
        for part in directory_route.split(os.path.sep):
            route, _ = self.expand_filename(part)
            parts.append(route)
        directory_route = os.path.join(*parts)
        return directory_route

    def collect_routes_from_directory(
        self, directory: str, extensions: list[str]
    ) -> Iterator[FileRouteInfo]:
        for subdirectory, dirs, filenames in os.walk(directory):
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            relative = subdirectory[len(directory) :]
            yield from self.visit_one_directory(
                directory=subdirectory,
                directory_route=self.directory_expand_converters(relative),
                filenames=filenames,
                extensions=extensions,
            )

    def visit_one_directory(
        self,
        directory: str,
        directory_route: str,
        filenames: list[str],
        extensions: list[str],
    ) -> Iterator[FileRouteInfo]:
        normal_routes: list[FileRouteInfo] = []
        wildcard_routes: list[FileRouteInfo] = []
        for filename in filenames:
            module_name, ext = filename.rsplit(".")
            if ext not in extensions:
                continue
            bad_chars = route_contains_invalid_characters(module_name)
            if bad_chars:
                CheckWarning(
                    f"{filename} contains invalid characters: {bad_chars}",
                    hint="Some characters are not allowed on all supported platforms.",
                    code="fileroutes.W005",
                )

            if module_name == "__init__":
                continue
            elif module_name == "index":
                route_name = directory_route
                if directory_route != "":
                    route_name += "/"
                is_wildcard = False
            else:
                route_name, is_wildcard = self.expand_filename(module_name)
                if directory_route:
                    route_name = directory_route + "/" + route_name
            if is_wildcard:
                routes = wildcard_routes
            else:
                routes = normal_routes
            routes.append(
                FileRouteInfo(
                    name=route_name,
                    filename=os.path.join(directory, filename),
                    is_wildcard=is_wildcard,
                )
            )
        yield from normal_routes
        yield from wildcard_routes
