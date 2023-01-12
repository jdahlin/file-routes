import re
from typing import Any, Sequence, cast

from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path
from django.urls.converters import get_converters
from django.views import View

from file_routes.directoryvisitor import DirectoryVisitor
from file_routes.filerouteinfo import FileRouteInfo, WebFramework
from file_routes.inspection import InspectedModuleInfo

ViewFunc = Any
PathType = tuple[Sequence[URLResolver | URLPattern], str | None, str | None]
_ALL_CONVERTERS = get_converters().keys()


class DjangoWebFramework(WebFramework):
    def expand_wildcards(self, filename: str, match: re.Match[str]) -> str:
        # [slug] -> <slug:slug>
        # [slug_customer] -> <slug:customer>
        _, converter, name = match.groups()
        if converter is None:
            if name in _ALL_CONVERTERS:
                converter = name
            else:
                converter = "str"
        return f"<{converter}:{name}>"

    def analyze(
        self, file_route: FileRouteInfo, inspected_module: InspectedModuleInfo
    ) -> ViewFunc | None:
        if function_view := inspected_module.find_function_by_name(["view"]):
            return function_view
        if class_view := inspected_module.find_class_by_name(
            ["View"], issubclass_of=View
        ):
            return class_view.as_view()
        return None


def autodiscover(directory: str | None = None) -> PathType:
    if directory is None:
        directory = getattr(settings, "FILE_ROUTES_DIRECTORY", "routes")
    directory_visitor = DirectoryVisitor(framework=DjangoWebFramework())

    routes = []
    for file_route, view_func in directory_visitor.visit_and_analyze(
        directory=directory
    ):
        routes.append(
            path(
                route=file_route.name,
                view=view_func,
                kwargs=getattr(view_func, "route_kwargs", {}),
                name=cast(str, getattr(view_func, "route_name", None)),
            )
        )
    return include(routes)
