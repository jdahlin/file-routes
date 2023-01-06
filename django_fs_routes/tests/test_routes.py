import dataclasses
import pathlib
from typing import Any

import pytest
from django.test import Client
from django.urls import URLResolver, path

from django_fs_routes.routes import (
    autodiscover_directory,
    filename_or_directory_expand_converters,
)

ParameterName = str
ParameterType = str  # int/path/slug/uuid
urlpatterns: list[URLResolver] = []
FUNCTION_VIEW_TEMPLATE = """
from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse


def {view_name}(request: HttpRequest, {params}) -> HttpResponse:
    return JsonResponse({{
        "method": request.method, 
        "path": request.path, 
        "params": {response_params}
    }})
"""


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


def parse_url(url: str) -> dict[ParameterName, ParameterType]:
    params = {}
    for part in url.split("/"):
        filename, is_wildcard = filename_or_directory_expand_converters(part)
        if not is_wildcard:
            continue
        parameter_type, parameter_name = filename[1:-1].split(":")
        if parameter_type != "int":
            parameter_type = "str"
        params[parameter_name] = parameter_type
    return params


def generate_view_source(url: str) -> str:
    groups = parse_url(url)
    response_params = [f'"{pname}": {pname}' for pname in groups.keys()]
    params = [f"{pname}: {ptype}" for pname, ptype in groups.items()]
    view_source = FUNCTION_VIEW_TEMPLATE.format(
        view_name="view",
        params=", ".join(params),
        response_params=f'{{{", ".join(response_params)}}}',
    )
    return view_source


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
                "/blog/[int year]/[int month]/[slug]",
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
def test_routes(tmp_path: pathlib.Path, view: View) -> None:
    root = tmp_path / "views"
    for view_path in view.paths:
        full = root / (str(pathlib.Path(*view_path.parts[1:])) + ".py")
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(generate_view_source(str(view_path)))

    urlpatterns[:] = [path("", autodiscover_directory(str(root)))]
    client = Client()
    for test in view.tests:
        response = client.generic(test.method, test.url, format="application/json")
        assert response.status_code == test.status
        body = response.json()
        assert body["method"] == test.method
        assert body["params"] == test.params
        assert body["path"] == test.url


# FIXME: test warnings
