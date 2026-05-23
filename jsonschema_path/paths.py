"""JSONSchema spec paths module."""

from __future__ import annotations

import os
import warnings
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from typing import TypeVar
from typing import overload

from pathable import AccessorPath
from referencing import Specification
from referencing._core import Resolved
from referencing.jsonschema import DRAFT202012

from jsonschema_path.accessors import SchemaAccessor
from jsonschema_path.handlers import default_handlers
from jsonschema_path.handlers.protocols import SupportsRead
from jsonschema_path.readers import FilePathReader
from jsonschema_path.readers import FileReader
from jsonschema_path.readers import PathReader
from jsonschema_path.typing import ResolverHandlers
from jsonschema_path.typing import Schema
from jsonschema_path.typing import SchemaKey
from jsonschema_path.typing import SchemaNode
from jsonschema_path.typing import SchemaValue
from jsonschema_path.typing import is_str_sequence

TDefault = TypeVar("TDefault")
# Python 3.11+ shortcut: typing.Self
TSchemaPath = TypeVar("TSchemaPath", bound="SchemaPath")

SPEC_SEPARATOR = "#"
NOTSET = object()


class SchemaPath(AccessorPath[SchemaNode, SchemaKey, SchemaValue]):

    @classmethod
    def _parse_args(
        cls,
        args: Sequence[Any],
        sep: str = SPEC_SEPARATOR,
    ) -> tuple[SchemaKey, ...]:
        parts: list[SchemaKey] = []
        append = parts.append
        extend = parts.extend

        for a in args:
            if isinstance(a, cls):
                extend(a.parts)
                continue

            # Fast-path: benchmarks overwhelmingly pass `str`/`int` parts.
            if isinstance(a, int):
                append(a)
                continue

            if isinstance(a, bytes):
                a = a.decode("ascii")

            if isinstance(a, str):
                if a and a != ".":
                    if sep in a:
                        for x in a.split(sep):
                            if x and x != ".":
                                append(x)
                    else:
                        append(a)
                continue

            # PathLike is relatively expensive to check; keep it after common types.
            if isinstance(a, os.PathLike):
                a = os.fspath(a)
                if isinstance(a, bytes):
                    a = a.decode("ascii")
                if isinstance(a, str):
                    if a and a != ".":
                        if sep in a:
                            for x in a.split(sep):
                                if x and x != ".":
                                    append(x)
                        else:
                            append(a)
                    continue

            raise TypeError(
                "argument must be str, int, bytes, os.PathLike, or SchemaPath; got %r"
                % (type(a),)
            )

        return tuple(parts)

    @classmethod
    def from_dict(
        cls: type[TSchemaPath],
        data: Schema,
        *args: Any,
        separator: str = SPEC_SEPARATOR,
        specification: Specification[Schema] = DRAFT202012,
        base_uri: str = "",
        handlers: ResolverHandlers = default_handlers,
        resolved_cache_maxsize: int = 0,
        spec_url: str | None = None,
        ref_resolver_handlers: ResolverHandlers | None = None,
    ) -> TSchemaPath:
        if spec_url is not None:
            warnings.warn(
                "spec_url parameter is deprecated. " "Use base_uri instead.",
                DeprecationWarning,
            )
            base_uri = spec_url
        if ref_resolver_handlers is not None:
            warnings.warn(
                "ref_resolver_handlers parameter is deprecated. "
                "Use handlers instead.",
                DeprecationWarning,
            )
            handlers = ref_resolver_handlers

        accessor: SchemaAccessor = SchemaAccessor.from_schema(
            data,
            specification=specification,
            base_uri=base_uri,
            handlers=handlers,
            resolved_cache_maxsize=resolved_cache_maxsize,
        )

        return cls(accessor, *args, separator=separator)

    @classmethod
    def from_path(
        cls: type[TSchemaPath],
        path: Path,
        resolved_cache_maxsize: int = 0,
    ) -> TSchemaPath:
        reader = PathReader(path)
        data, base_uri = reader.read()
        return cls.from_dict(
            data,
            base_uri=base_uri,
            resolved_cache_maxsize=resolved_cache_maxsize,
        )

    @classmethod
    def from_file_path(
        cls: type[TSchemaPath],
        file_path: str,
        resolved_cache_maxsize: int = 0,
    ) -> TSchemaPath:
        reader = FilePathReader(file_path)
        data, base_uri = reader.read()
        return cls.from_dict(
            data,
            base_uri=base_uri,
            resolved_cache_maxsize=resolved_cache_maxsize,
        )

    @classmethod
    def from_file(
        cls: type[TSchemaPath],
        fileobj: SupportsRead,
        base_uri: str = "",
        spec_url: str | None = None,
        resolved_cache_maxsize: int = 0,
    ) -> TSchemaPath:
        reader = FileReader(fileobj)
        data, _ = reader.read()
        return cls.from_dict(
            data,
            base_uri=base_uri,
            spec_url=spec_url,
            resolved_cache_maxsize=resolved_cache_maxsize,
        )

    @property
    def base_uri(self) -> str:
        assert isinstance(self.accessor, SchemaAccessor)
        return self.accessor.base_uri

    def str_keys(self) -> Sequence[str]:
        keys = list(self.keys())
        if not is_str_sequence(keys):
            raise TypeError(
                f"Expected string keys, got {[type(x) for x in keys]}"
            )
        return keys

    def str_items(self) -> Iterator[tuple[str, SchemaPath]]:
        for key, value in self.items():
            if not isinstance(key, str):
                raise TypeError(f"Expected string keys, got {type(key)}")
            yield key, value

    @overload
    def read_str(self) -> str: ...

    @overload
    def read_str(self, default: TDefault) -> str | TDefault: ...

    def read_str(self, default: object = NOTSET) -> object:
        try:
            value = self.read_value()
        except KeyError:
            if default is not NOTSET:
                return default
            raise
        if not isinstance(value, str):
            raise TypeError(f"Expected a string value, got {type(value)}")
        return value

    @overload
    def read_str_or_list(self) -> str | list[str]: ...

    @overload
    def read_str_or_list(
        self, default: TDefault
    ) -> str | list[str] | TDefault: ...

    def read_str_or_list(self, default: object = NOTSET) -> object:
        try:
            value = self.read_value()
        except KeyError:
            if default is not NOTSET:
                return default
            raise
        if not isinstance(value, (str, list)):
            raise TypeError(
                f"Expected a string or a list of strings, got {type(value)}"
            )
        return value

    @overload
    def read_bool(self) -> bool: ...

    @overload
    def read_bool(self, default: TDefault) -> bool | TDefault: ...

    def read_bool(self, default: object = NOTSET) -> object:
        try:
            value = self.read_value()
        except KeyError:
            if default is not NOTSET:
                return default
            raise
        if not isinstance(value, bool):
            if default is not NOTSET:
                return default
            raise TypeError(f"Expected a bool value, got {type(value)}")
        return value

    def as_uri(self) -> str:
        return f"#/{str(self)}"

    @contextmanager
    def open(self) -> Any:
        """Open the path."""
        with self.resolve() as resolved:
            yield resolved.contents

    @contextmanager
    def resolve(self) -> Iterator[Resolved[SchemaNode]]:
        """Resolve the path."""
        assert isinstance(self.accessor, SchemaAccessor)
        with self.accessor.resolve(self.parts) as resolved:
            yield resolved

    def canonical(self) -> SchemaPath:
        """Return a SchemaPath whose ``parts`` are the JSON pointer of the
        resolved target node, collapsing ``$ref`` navigation.

        Analogous to :meth:`pathlib.Path.resolve`: follows ``$ref``
        indirections (as symlinks are followed) and returns the path of the
        node they ultimately point to.

        Two SchemaPaths with equal ``canonical()`` refer to the same resolved
        node regardless of the navigation path that reached them.  Use as a
        cache key for content-level memoisation (where "the answer depends
        only on *what* the schema is, not *how* we got here").  For
        context-aware uses such as error reporting or discriminator
        resolution, use the SchemaPath directly.

        The result is not cached — store it yourself if you call this in a
        loop (``c = path.canonical()``).

        Guarantees:

        * **Idempotent** — ``p.canonical().canonical() == p.canonical()``.
        * **Reachable-equivalent** — ``p.canonical().read_value() is
          p.read_value()`` for same-document refs; value-equal for
          cross-document refs.
        * **Cycle-safe** — self-referential ``$ref`` schemas resolve
          without raising or looping.
        * **Accessor-transparent** — ``p.canonical().accessor`` may differ
          from ``p.accessor`` when a ``$ref`` crosses a document boundary;
          that is expected, not a bug.

        Known limitation — ``$dynamicRef`` is not followed.
        ``$dynamicRef`` is intentionally late-bound: its target depends on
        the dynamic scope at validation time and cannot be determined from
        the document structure alone.  A path whose node contains only
        ``$dynamicRef`` (no ``$ref``) is returned as-is.

        Raises :class:`referencing.exceptions.Unresolvable` if a ``$ref``
        target cannot be reached; wrap the call if you need to handle that.
        """
        assert isinstance(self.accessor, SchemaAccessor)
        accessor, parts = self.accessor._resolve_canonical(self.parts)
        if accessor is self.accessor and parts == self.parts:
            return self
        return type(self)._from_parsed_parts(
            parts=parts,
            separator=self.separator,
            accessor=accessor,
        )
