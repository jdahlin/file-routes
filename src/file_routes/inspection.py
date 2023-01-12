import dataclasses
import importlib
import importlib.util
import inspect
import sys
from types import FunctionType, ModuleType
from typing import Any, Protocol, TypeVar, cast, overload


class DjangoView(Protocol):
    def as_view(self) -> Any:
        ...


class FlaskView(Protocol):
    def as_view(self, name: str) -> Any:
        ...


T = TypeVar("T", str, DjangoView, FlaskView)


@dataclasses.dataclass
class CheckWarning:
    message: str
    code: str
    hint: str | None = None


@dataclasses.dataclass
class InspectedModuleInfo:
    module: ModuleType
    attributes: dict[str, Any]
    warnings: list[CheckWarning] = dataclasses.field(default_factory=list)

    @property
    def name(self) -> str:
        return self.module.__name__

    def warning(self, message: str, code: str, hint: str | None = None) -> None:
        self.warnings.append(CheckWarning(message, code, hint))

    def find_function_by_name(self, candidates: list[str]) -> FunctionType | None:
        for candidate in candidates:
            function = self.attributes.get(candidate)
            if function is None:
                continue
            if not inspect.isfunction(function):
                self.warning(
                    f"{candidate} in {self.name} is not a function",
                    code="fileroutes.W001",
                    hint=(
                        f"{candidate} cannot be a {type(function).__name__}, "
                        f"change it to be a function"
                    ),
                )
                continue
            return function
        return None

    def find_class_by_name(
        self, candidates: list[str], issubclass_of: type[T] | None = None
    ) -> T | None:
        for candidate in candidates:
            class_ = cast(T | None, self.attributes.get(candidate))
            if class_ is None:
                continue
            # FIXME: Should this be a warning?
            if not inspect.isclass(class_):
                self.warning(
                    f"{candidate} in {self.name} is not a class",
                    hint=(
                        f"{candidate} cannot be a {type(class_).__name__}, "
                        f"change it to a class"
                    ),
                    code="fileroutes.W002",
                )
                continue
            if issubclass_of is not None:
                if class_ == issubclass_of:
                    continue
                if not issubclass(class_, issubclass_of):
                    self.warning(
                        f"{candidate} in {self.name} is not a subclass "
                        f"of {issubclass_of.__name__}",
                        hint=f"{candidate} must inherit from {issubclass_of.__name__}",
                        code="fileroutes.W003",
                    )
                    continue

            return class_
        return None

    @overload
    def get_attribute_by_type(
        self, attribute: str, attribute_type: type[T], default: T
    ) -> T:
        ...

    @overload
    def get_attribute_by_type(
        self, attribute: str, attribute_type: type[T], default: None
    ) -> T | None:
        ...

    def get_attribute_by_type(
        self, attribute: str, attribute_type: type[T], default: T | None = None
    ) -> T | None:
        route_kwargs = getattr(self.module, attribute, default)
        if not isinstance(route_kwargs, attribute_type):
            CheckWarning(
                f"{self.name}.{attribute} must be a {attribute_type}, "
                f"not {type(route_kwargs).__name__}",
                hint=f"Change {attribute} to be a {attribute_type}.",
                code="fileroutes.W006",
            )
            route_kwargs = default
        return route_kwargs


def inspect_module(module: ModuleType) -> InspectedModuleInfo:
    attributes = {}
    for name, value in inspect.getmembers(module):
        attributes[name] = value
    return InspectedModuleInfo(module=module, attributes=attributes)


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
