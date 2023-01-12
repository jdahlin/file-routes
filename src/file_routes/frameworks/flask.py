import re

from flask import Flask
from flask.views import View

from file_routes.directoryvisitor import DirectoryVisitor
from file_routes.filerouteinfo import FileRouteInfo, ViewFuncOrClass, WebFramework
from file_routes.inspection import InspectedModuleInfo


class FlaskWebFramework(WebFramework):
    def expand_wildcards(self, filename: str, match: re.Match[str]) -> str:
        _, converter, name = match.groups()
        if converter is None:
            if name in ["int", "float", "path", "string", "uuid"]:
                converter = name
            else:
                converter = "string"
        return f"<{converter}:{name}>"

    def analyze(
        self, file_route: FileRouteInfo, inspected_module: InspectedModuleInfo
    ) -> ViewFuncOrClass | None:
        if function_view := inspected_module.find_function_by_name(["view"]):
            return function_view
        if class_view := inspected_module.find_class_by_name(
            ["View"], issubclass_of=View
        ):
            route_name = inspected_module.get_attribute_by_type(
                "route_name", str, default=file_route.name
            )
            return class_view.as_view(route_name)
        return None


class FlaskFSRoutes:
    def init_app(self, app: Flask) -> None:
        manager = DirectoryVisitor(framework=FlaskWebFramework())
        route_views = manager.visit_and_analyze(app.config["FS_ROUTES_DIRECTORY"])
        for i, (file_route, view_func) in enumerate(route_views, start=1):
            # XXX: defaults
            # XXX: subdomain
            # XXX: methods
            # XXX: endpoint name
            app.add_url_rule(
                "/" + file_route.name, view_func=view_func, endpoint=f"view{i}"
            )
