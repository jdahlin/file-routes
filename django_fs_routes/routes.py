import dataclasses
import importlib
import importlib.util
import os
import re
import sys
from collections.abc import Iterator
from types import ModuleType

from django_fs_routes.inspection import (
    CheckWarning,
    InspectedModuleInfo,
    inspect_module,
)

RE_CONVERTERS = re.compile(r"\[((?P<converter>[^ ]+) |)(?P<name>[^]]+)]")
# https://stackoverflow.com/q/1976007
FORBIDDEN_FILENAME_CHARS = {
    "<",  # less than
    ">",  # greater than
    ":",  # colon - sometimes works, but is actually NTFS Alternate Data Streams
    '"',  # double quote
    "/",  # forward slash
    "\\",  # backslash
    "|",  # vertical bar or pipe
    "?",  # question mark
    "*",  # asterisk
}


@dataclasses.dataclass
class ViewRoute:
    name: str
    filename: str
    is_wildcard: bool
    module: ModuleType = dataclasses.field(init=False)
    inspected_module: InspectedModuleInfo = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.module = import_filename_and_guess_module_from_path(self.filename)
        self.inspected_module = inspect_module(self.module)

    def get_default_view_name(self) -> str | None:
        default_view_name = None
        base_name = os.path.basename(self.filename)[:-3]
        if self.name == "" or base_name == "index":
            default_view_name = "index"
        # If the view module is not a wildcard, we can provide a default view name
        elif not self.is_wildcard:
            default_view_name = base_name.replace("-", "_")
        return default_view_name


def filename_to_module_path(filename: str) -> str:
    # foo/bar/baz.py -> foo.bar.baz
    return filename[:-3].replace("/", ".")


def import_filename_and_guess_module_from_path(filename: str) -> ModuleType:
    module_name = filename_to_module_path(filename)
    spec = importlib.util.spec_from_file_location(module_name, filename)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def underscore_to_camel_case(word: str) -> str:
    # foo_bar_baz -> FooBarBaz
    return "".join(c.capitalize() or "_" for c in word.split("_"))


def filename_or_directory_expand_converters(
    filename_or_directory: str,
) -> tuple[str, bool]:
    # [slug] -> <slug:slug>
    # [slug customer] -> <slug:customer>
    was_transformed = False
    if match := RE_CONVERTERS.match(filename_or_directory):
        _, converter, name = match.groups()
        if converter is None:
            if name in ["int", "path", "slug", "uuid"]:
                converter = name
            else:
                converter = "str"
        filename_or_directory = f"<{converter}:{name}>"
        was_transformed = True
    return filename_or_directory, was_transformed


def directory_expand_converters(directory_route: str) -> str:
    # foo/[slug]/bar -> foo/<slug:slug>/bar
    if directory_route.startswith("/"):
        directory_route = directory_route[1:]
    parts = []
    for part in directory_route.split(os.path.sep):
        route, _ = filename_or_directory_expand_converters(part)
        parts.append(route)
    directory_route = os.path.join(*parts)
    return directory_route


def directory_discover_view_routes(
    directory: str, directory_route: str, filenames: list[str]
) -> Iterator[ViewRoute]:
    normal_routes: list[ViewRoute] = []
    wildcard_routes: list[ViewRoute] = []
    for filename in filenames:
        module_name = filename[:-3]
        bad_chars = set(module_name) - FORBIDDEN_FILENAME_CHARS
        if bad_chars:
            CheckWarning(
                f"{filename} contains invalid characters: {bad_chars}",
                hint="Some characters are not allowed on all supported platforms.",
                code="fsroutes.W005",
            )

        if module_name == "__init__":
            continue
        elif module_name == "index":
            route = directory_route
            if directory_route != "":
                route += "/"
            is_wildcard = False
        else:
            route, is_wildcard = filename_or_directory_expand_converters(module_name)
            if directory_route:
                route = directory_route + "/" + route
        if is_wildcard:
            routes = wildcard_routes
        else:
            routes = normal_routes
        routes.append(
            ViewRoute(
                name=route,
                filename=os.path.join(directory, filename),
                is_wildcard=is_wildcard,
            )
        )
    yield from normal_routes
    yield from wildcard_routes


def find_view_routes(root: str) -> Iterator[ViewRoute]:
    for directory, dirs, filenames in os.walk(root):
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
        route = directory_expand_converters(directory[len(root) :])
        yield from directory_discover_view_routes(
            directory=directory, directory_route=route, filenames=filenames
        )
