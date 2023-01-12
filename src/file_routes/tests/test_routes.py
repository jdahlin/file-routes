import dataclasses
import enum
import pathlib
import textwrap
from typing import Any

import pytest
from django.test import Client
from django.urls import URLResolver, path
from flask import Flask

from file_routes.directoryvisitor import DirectoryVisitor
from file_routes.filerouteinfo import WebFramework
from file_routes.frameworks.django import DjangoWebFramework, autodiscover
from file_routes.frameworks.flask import FlaskFSRoutes, FlaskWebFramework


class ViewType(enum.StrEnum):
    CLASS = "class"
    FUNCTION = "function"


class FrameworkType(enum.StrEnum):
    DJANGO = "django"
    FLASK = "flask"


ParameterName = str
ParameterType = str  # int/path/slug/uuid
urlpatterns: list[URLResolver] = []


def get_view_template(framework_type: FrameworkType, view_type: ViewType) -> str:
    template = ""
    indent = 0

    def write(text: str = "") -> None:
        nonlocal template
        template += textwrap.indent(text + "\n", " " * (indent * 4))

    if framework_type == FrameworkType.DJANGO:
        write("from typing import Self")
        write()
        write("from django import views")
        write("from django.http import JsonResponse")
        write()
        if view_type == ViewType.CLASS:
            write("class {view_name}(views.View):")
            indent += 1
            write("def dispatch(self, request, {params}):")
            indent += 1
        else:
            write("def {view_name}(request, {params}):")
            indent += 1
        write("return JsonResponse({{")
        indent += 1
        write('"method": request.method,')
        write('"path": request.path,')
        write('"params": {response_params}, ')
        indent -= 1
        write("}})\n")
    elif framework_type == FrameworkType.FLASK:
        write("from flask import request, views")
        write()
        if view_type == ViewType.CLASS:
            write("class {view_name}(views.View):")
            indent += 1
            write("def dispatch_request(self, {params}):")
        else:
            write("def {view_name}({params}):")
        indent += 1
        write("return {{")
        write('"method": request.method,')
        write('"path": request.path,')
        write('"params": {response_params}, ')
        indent -= 1
        write("}}\n")
    else:
        raise NotImplementedError(framework_type)
    return template


@dataclasses.dataclass
class Test:
    __test__ = False
    url: str
    status: int = 200
    method: str = "GET"
    params: dict[str, Any] = dataclasses.field(default_factory=dict)


class View:
    def __init__(self, *filenames: str, tests: list[Test]):
        self.paths = [pathlib.Path(f) for f in filenames]
        self.tests = tests


def parse_url(
    visitor: DirectoryVisitor, url: str
) -> dict[ParameterName, ParameterType]:
    params = {}
    for part in url.split("/"):
        visitor.expand_filename(part)
        filename, is_wildcard = visitor.expand_filename(part)
        if not is_wildcard:
            continue
        parameter_type, parameter_name = filename[1:-1].split(":")
        if parameter_type != "int":
            parameter_type = "str"
        params[parameter_name] = parameter_type
    return params


def generate_view_source(
    visitor: DirectoryVisitor,
    framework_type: FrameworkType,
    view_type: ViewType,
    url: str,
) -> str:
    groups = parse_url(visitor=visitor, url=url)
    response_params = [f'"{pname}": {pname}' for pname in groups.keys()]
    params = [f"{pname}: {ptype}" for pname, ptype in groups.items()]
    if view_type == ViewType.CLASS:
        view_name = "View"
    elif view_type == ViewType.FUNCTION:
        view_name = "view"
    else:
        raise NotImplementedError(view_type)
    view_source = get_view_template(
        framework_type=framework_type, view_type=view_type
    ).format(
        view_name=view_name,
        params=", ".join(params),
        response_params=f'{{{", ".join(response_params)}}}',
    )
    return view_source


@pytest.fixture()
def flask_app() -> Flask:
    return Flask(__name__)


@pytest.mark.parametrize("framework_type", list(FrameworkType))
@pytest.mark.parametrize("view_type", list(ViewType))
@pytest.mark.parametrize(
    "view",
    [
        pytest.param(View("/index", tests=[Test("/")]), id="root"),
        pytest.param(View("/home", tests=[Test("/home")]), id="simple"),
        pytest.param(View("/with-hyphen", tests=[Test("/with-hyphen")]), id="hyphen"),
        pytest.param(View("/sub/page", tests=[Test("/sub/page")]), id="sub-page"),
        pytest.param(
            View("/[str]", tests=[Test("/str", params={"str": "str"})]),
            id="wildcard-str",
        ),
        pytest.param(
            View("/[int]", tests=[Test("/0", params={"int": 0})]), id="wildcard-int-0"
        ),
        pytest.param(
            View("/[int]", tests=[Test("/1234", params={"int": 1234})]),
            id="wildcard-int-1138",
        ),
        pytest.param(
            View(
                "/[username]/settings",
                tests=[Test("/bob/settings", params={"username": "bob"})],
            ),
            id="wildcard-directory",
        ),
        pytest.param(
            View(
                "/blog/[int_year]/[int_month]/[slug]",
                tests=[
                    Test(
                        "/blog/2022/01/test",
                        status=200,
                        params={"month": 1, "slug": "test", "year": 2022},
                    ),
                ],
            ),
            id="deep-wildcards",
        ),
        pytest.param(
            View(
                "/normal",
                "/[str]",
                tests=[
                    Test("/normal"),
                    Test("/fallback", params={"str": "fallback"}),
                    Test("/str", params={"str": "str"}),
                ],
            ),
            id="fallback",
        ),
    ],
)
@pytest.mark.urls(__name__)
def test_routes(
    tmp_path: pathlib.Path,
    view: View,
    framework_type: FrameworkType,
    view_type: ViewType,
    flask_app: Flask,
) -> None:
    framework: WebFramework
    root = tmp_path / "routes"
    if framework_type == FrameworkType.DJANGO:
        framework = DjangoWebFramework()
    elif framework_type == FrameworkType.FLASK:
        framework = FlaskWebFramework()
        flask_app.config["FS_ROUTES_DIRECTORY"] = str(root)
        FlaskFSRoutes().init_app(flask_app)
    else:
        raise NotImplementedError(framework_type)

    visitor = DirectoryVisitor(framework=framework)
    for view_path in view.paths:
        full = root / (str(pathlib.Path(*view_path.parts[1:])) + ".py")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(
            generate_view_source(
                visitor,
                framework_type=framework_type,
                url=str(view_path),
                view_type=view_type,
            )
        )

    if framework_type == FrameworkType.DJANGO:
        urlpatterns[:] = [path("", autodiscover(str(root)))]
    elif framework_type == FrameworkType.FLASK:
        flask_app.config["FS_ROUTES_DIRECTORY"] = str(root)
        FlaskFSRoutes().init_app(flask_app)

    for test in view.tests:
        if framework_type == FrameworkType.DJANGO:
            django_response = Client().generic(
                test.method, test.url, format="application/json"
            )
            status_code = django_response.status_code
            body = django_response.json()
        elif framework_type == FrameworkType.FLASK:
            flask_response = flask_app.test_client().open(test.url, method=test.method)
            body = flask_response.json
            status_code = flask_response.status_code
        else:
            raise NotImplementedError(framework_type)

        assert status_code == test.status
        assert body["method"] == test.method
        assert body["params"] == test.params
        assert body["path"] == test.url
