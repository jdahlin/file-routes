import dataclasses
import inspect
from types import FunctionType, ModuleType
from typing import Any, TypeVar


@dataclasses.dataclass
class CheckWarning:
    message: str
    code: str
    hint: str | None = None


T = TypeVar("T")


@dataclasses.dataclass
class InspectedModuleInfo:
    module: ModuleType
    attributes: dict[str, Any]
    warnings: list[CheckWarning] = dataclasses.field(init=False)

    @property
    def name(self) -> str:
        return self.module.__name__

    def warning(self, message, code: str, hint: str | None = None):
        self.warnings.append(CheckWarning(message, code, hint))

    def find_function_by_name(self, candidates: list[str]) -> FunctionType | None:
        for candidate in candidates:
            function = self.attributes.get(candidate)
            if function is None:
                continue
            if not inspect.isfunction(function):
                self.warning(
                    f"{candidate} in {self.name} is not a function",
                    code="fsroutes.W001",
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
    ) -> type[T] | None:
        for candidate in candidates:
            class_ = self.attributes.get(candidate)
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
                    code="fsroutes.W002",
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
                        code="fsroutes.W003",
                    )
                    continue
            return class_
        return None


def inspect_module(module: ModuleType) -> InspectedModuleInfo:
    attributes = {}
    for name, value in inspect.getmembers(module):
        attributes[name] = value
    return InspectedModuleInfo(module=module, attributes=attributes)
