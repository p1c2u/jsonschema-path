"""JSONSchema spec paths module."""
from typing import Any
from typing import Hashable
from typing import Mapping
from typing import Type
from typing import TypeVar

from jsonschema.validators import RefResolver
from pathable.paths import AccessorPath

from jsonschema_spec.accessors import SpecAccessor
from jsonschema_spec.handlers import default_handlers
from jsonschema_spec.handlers.protocols import SupportsRead
from jsonschema_spec.readers import FilePathReader
from jsonschema_spec.readers import FileReader

TSpec = TypeVar("TSpec", bound="Spec")

SPEC_SEPARATOR = "#"


class Spec(AccessorPath):
    @classmethod
    def from_dict(
        cls: Type[TSpec],
        data: Mapping[Hashable, Any],
        *args: Any,
        spec_url: str = "",
        ref_resolver_handlers: Mapping[str, Any] = default_handlers,
        separator: str = SPEC_SEPARATOR,
    ) -> TSpec:
        ref_resolver = RefResolver(
            spec_url, data, handlers=ref_resolver_handlers
        )
        accessor = SpecAccessor(data, ref_resolver)
        return cls(accessor, *args, separator=separator)

    @classmethod
    def from_file_path(cls: Type[TSpec], file_path: str) -> TSpec:
        reader = FilePathReader(file_path)
        data, spec_url = reader.read()
        return cls.from_dict(data, spec_url=spec_url)

    @classmethod
    def from_file(
        cls: Type[TSpec], fileobj: SupportsRead, spec_url: str = ""
    ) -> TSpec:
        reader = FileReader(fileobj)
        data, _ = reader.read()
        return cls.from_dict(data, spec_url=spec_url)
