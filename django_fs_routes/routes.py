import importlib
import importlib.util
import inspect
import os
import re
import sys
from collections.abc import Iterator
from types import ModuleType
from typing import Any, NamedTuple, Sequence

from django.apps import apps
from django.core import checks
from django.urls import include, path, URLResolver, URLPattern
from django.views import View

RE_CONVERTERS = re.compile(r"\[((?P<converter>[^ ]+) |)(?P<name>[^]]+)]")
PathType = tuple[Sequence[URLResolver | URLPattern], str | None, str | None]


class ViewRoute(NamedTuple):
    name: str
    filename: str
    is_wildcard: bool


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


def find_view(
    module: ModuleType, default_view_name: str | None
) -> Any:
    # for a given module, figure out the view
    # 1. function "module_name"
    # 2. function "module_name_view"
    # 3. function "view"
    # 4. class "ModuleNameView"
    # 5. class "View"
    function_suggestion = "view"
    class_suggestion = "View"
    class_names = [class_suggestion]
    function_names = [function_suggestion]
    if default_view_name is not None:
        function_names.insert(0, default_view_name + "_view")
        function_names.insert(1, default_view_name)
        class_suggestion = underscore_to_camel_case(default_view_name) + "View"
        class_names.append(class_suggestion)
        function_suggestion = f"{default_view_name}_view or {default_view_name} or view"

    for function_name in function_names:
        view = getattr(module, function_name, None)
        if view is None:
            continue
        if not inspect.isfunction(view):
            checks.Warning(
                f"{function_name} in {module.__name__} is not a function",
                hint=(
                    f"{function_name} cannot be a {type(view).__name__}, "
                    f"change it to be a function"
                ),
                id="viewfinder.W001",
            )
            continue
        return view

    for class_name in class_names:
        view = getattr(module, class_name, None)
        if view is None:
            continue
        if view == View:
            # FIXME: Should this be a warning?
            continue
        if not inspect.isclass(view):
            checks.Warning(
                f"{class_name} in {module.__name__} is not a class",
                hint=(
                    f"{class_name} cannot be a {type(view).__name__}, "
                    f"change it to a class"
                ),
                id="viewfinder.W002",
            )
            continue
        if not issubclass(view, View):
            checks.Warning(
                f"{class_name} in {module.__name__} is not a subclass "
                f"of django.views.View",
                hint=f"{class_name} must inherit from django.views.View.",
                id="viewfinder.W003",
            )
            continue
        return view.as_view()

    checks.Warning(
        f"Could not find a view in {module.__name__}",
        hint=(
            f"Create a view function called {function_suggestion} or "
            f"a class called {class_suggestion}."
        ),
        id="viewfinder.W004",
    )
    return None


def get_default_view_name(view_route: ViewRoute) -> str | None:
    default_view_name = None
    base_name = os.path.basename(view_route.filename)[:-3]
    if view_route.name == "" or base_name == "index":
        default_view_name = "index"
    # If the view module is not a wildcard, we can provide a default view name
    elif not view_route.is_wildcard:
        default_view_name = base_name.replace("-", "_")
    return default_view_name


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


def directory_discover_view_routes(
    directory: str, directory_route: str, filenames: list[str]
) -> Iterator[ViewRoute]:
    normal_routes: list[ViewRoute] = []
    wildcard_routes: list[ViewRoute] = []
    for filename in filenames:
        module_name = filename[:-3]
        bad_chars = set(module_name) - FORBIDDEN_FILENAME_CHARS
        if bad_chars:
            checks.Warning(
                f"{filename} contains invalid characters: {bad_chars}",
                hint="Some characters are not allowed on all supported platforms.",
                id="viewfinder.W007",
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


def create_path_from_module(route: str, module: ModuleType, view: Any) -> Any:
    route_kwargs = getattr(module, "route_kwargs", {})
    if not isinstance(route_kwargs, dict):
        checks.Warning(
            f"{module.__name__}.route_kwargs must be a dict, "
            f"not {type(route_kwargs).__name__}",
            hint="Change route_kwargs to be a dict subclass.",
            id="viewfinder.W006",
        )
        route_kwargs = {}

    route_name = getattr(module, "route_name", None)
    if route_name and not isinstance(route_name, str):
        checks.Warning(
            f"{module.__name__}.route_name must be a str, "
            f"not {type(route_name).__name__}",
            hint="Change route_name to be a string.",
            id="viewfinder.W007",
        )
        route_name = None

    return path(route, view, route_kwargs, name=route_name)


def autodiscover_directory(directory: str) -> PathType:
    routes = []
    for view_route in find_view_routes(directory):
        module = import_filename_and_guess_module_from_path(view_route.filename)
        view = find_view(module, default_view_name=get_default_view_name(view_route))
        if view is None:
            # A warning has already been emitted inside find_view()
            continue
        route_path = create_path_from_module(
            route=view_route.name,
            view=view,
            module=module,
        )
        routes.append(route_path)

    return include(routes)


def autodiscover_app_views(app_name: str, views_directory: str = "views") -> PathType:
    app = apps.get_app_config(app_name)
    assert app.module is not None
    return autodiscover_directory(f"{app.module.__name__}/{views_directory}")
