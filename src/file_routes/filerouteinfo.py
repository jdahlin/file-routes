import dataclasses
import os
import re
from abc import ABC, abstractmethod
from typing import Any, NamedTuple

from file_routes.inspection import InspectedModuleInfo

ViewFuncOrClass = Any


@dataclasses.dataclass
class FileRouteInfo:
    # The filename of this route
    filename: str

    # The name of this route
    name: str

    # If this is a wildcard route, if it contains any dynamic parts, e.g converters
    # in the filename
    is_wildcard: bool

    def get_default_view_name(self) -> str | None:
        default_view_name = None
        base_name = os.path.basename(self.filename)[:-3]
        if self.name == "" or base_name == "index":
            default_view_name = "index"
        # If the view module is not a wildcard, we can provide a default view name
        elif not self.is_wildcard:
            default_view_name = base_name.replace("-", "_")
        return default_view_name


class FileRouteAndView(NamedTuple):
    route: FileRouteInfo
    view_func: ViewFuncOrClass


class WebFramework(ABC):
    @abstractmethod
    def expand_wildcards(self, filename: str, match: re.Match[str]) -> str:
        raise NotImplementedError()

    @abstractmethod
    def analyze(
        self, file_route: FileRouteInfo, inspected_module: InspectedModuleInfo
    ) -> ViewFuncOrClass:
        raise NotImplementedError()
