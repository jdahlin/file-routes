from types import ModuleType
from typing import Any, Sequence

from django.apps import apps
from django.urls import URLPattern, URLResolver, include, path
from django.views import View

from fs_routes.inspection import CheckWarning
from fs_routes.routes import (
    ViewRoute,
    find_view_routes,
    underscore_to_camel_case,
)

PathType = tuple[Sequence[URLResolver | URLPattern], str | None, str | None]


def create_path_from_module(route: str, module: ModuleType, view: Any) -> Any:
    route_kwargs = getattr(module, "route_kwargs", {})
    if not isinstance(route_kwargs, dict):
        CheckWarning(
            f"{module.__name__}.route_kwargs must be a dict, "
            f"not {type(route_kwargs).__name__}",
            hint="Change route_kwargs to be a dict subclass.",
            code="fsroutes.W006",
        )
        route_kwargs = {}

    route_name = getattr(module, "route_name", None)
    if route_name and not isinstance(route_name, str):
        CheckWarning(
            f"{module.__name__}.route_name must be a str, "
            f"not {type(route_name).__name__}",
            hint="Change route_name to be a string.",
            code="fsroutes.W007",
        )
        route_name = None

    return path(route, view, route_kwargs, name=route_name)


def find_view(view_route: ViewRoute) -> Any:
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
    default_view_name = view_route.get_default_view_name()
    if default_view_name is not None:
        function_names.insert(0, default_view_name + "_view")
        function_names.insert(1, default_view_name)
        class_suggestion = underscore_to_camel_case(default_view_name) + "View"
        class_names.append(class_suggestion)
        function_suggestion = f"{default_view_name}_view or {default_view_name} or view"

    inspected_module = view_route.inspected_module
    function_view = inspected_module.find_function_by_name(function_names)
    if function_view is not None:
        return function_view

    class_view = inspected_module.find_class_by_name(class_names, issubclass_of=View)
    if class_view is not None:
        return class_view.as_view()

    CheckWarning(
        f"Could not find a view in {inspected_module.name}",
        hint=(
            f"Create a view function called {function_suggestion} or "
            f"a class called {class_suggestion}."
        ),
        code="fsroutes.W004",
    )
    return None


def autodiscover_directory(directory: str) -> PathType:
    routes = []
    for view_route in find_view_routes(directory):
        view = find_view(view_route)
        if view is None:
            # A warning has already been emitted inside find_view()
            continue
        route_path = create_path_from_module(
            module=view_route.module,
            route=view_route.name,
            view=view,
        )
        routes.append(route_path)

    return include(routes)


def autodiscover_app_views(app_name: str, views_directory: str = "views") -> PathType:
    app = apps.get_app_config(app_name)
    assert app.module is not None
    return autodiscover_directory(f"{app.module.__name__}/{views_directory}")
