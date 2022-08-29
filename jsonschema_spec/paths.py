"""JSONSchema spec paths module."""
from typing import Any
from typing import Hashable
from typing import Mapping

from jsonschema.validators import RefResolver
from pathable.paths import AccessorPath

from jsonschema_spec.accessors import SpecAccessor
from jsonschema_spec.handlers import default_handlers
from jsonschema_spec.handlers.protocols import SupportsRead
from jsonschema_spec.readers import FilePathReader
from jsonschema_spec.readers import FileReader

SPEC_SEPARATOR = "#"


class Spec(AccessorPath):
    @classmethod
    def from_dict(
        cls,
        data: Mapping[Hashable, Any],
        *args: Any,
        spec_url: str = "",
        ref_resolver_handlers: Mapping[str, Any] = default_handlers,
        separator: str = SPEC_SEPARATOR,
    ) -> "Spec":
        ref_resolver = RefResolver(
            spec_url, data, handlers=ref_resolver_handlers
        )
        accessor = SpecAccessor(data, ref_resolver)
        return cls(accessor, *args, separator=separator)

    @classmethod
    def from_file_path(cls, file_path: str) -> "Spec":
        reader = FilePathReader(file_path)
        data, spec_url = reader.read()
        return cls.from_dict(data, spec_url=spec_url)

    @classmethod
    def from_file(cls, fileobj: SupportsRead, spec_url: str = "") -> "Spec":
        reader = FileReader(fileobj)
        data, _ = reader.read()
        return cls.from_dict(data, spec_url=spec_url)
