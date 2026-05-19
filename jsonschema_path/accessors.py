"""JSONSchema spec accessors module."""

import warnings
from collections.abc import Hashable
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any
from typing import cast

from pathable.accessors import LookupAccessor
from pathable.types import LookupKey
from pathable.types import LookupNode
from pathable.types import LookupValue
from referencing import Registry
from referencing import Specification
from referencing._core import Resolved
from referencing._core import Resolver
from referencing.jsonschema import DRAFT202012

from jsonschema_path._referencing_compat import rebind_resolved
from jsonschema_path.caches import FullPathResolvedCache
from jsonschema_path.handlers import default_handlers
from jsonschema_path.resolvers import CachedPathResolver
from jsonschema_path.retrievers import SchemaRetriever
from jsonschema_path.typing import ResolverHandlers
from jsonschema_path.typing import Schema


class SchemaAccessor(LookupAccessor):
    """Resource handle binding a schema document to its resolver.

    Identity contract: a `SchemaAccessor` is its own identity token,
    discriminated by the wrapped node (by reference) and the
    `_path_resolver` instance (by reference). Both are set in
    `__init__` and never reassigned, so equality and hash are stable
    for the accessor's lifetime even though the inner registry
    evolves as `$ref`s are resolved.

    Consequence: two `from_schema(doc, ...)` calls produce non-equal
    accessors even with identical arguments, because each call builds
    its own `_path_resolver`. Build one accessor per schema document
    and reuse it across all derived `SchemaPath`s — see "Identity and
    equality" and "Recommended usage" in the README.
    """

    def __init__(
        self,
        schema: Schema,
        resolver: Resolver[Schema],
        resolved_cache_maxsize: int = 128,
    ):
        if resolved_cache_maxsize < 0:
            raise ValueError("resolved_cache_maxsize must be >= 0")

        super().__init__(cast(LookupNode, schema))
        self._path_resolver: CachedPathResolver = CachedPathResolver(
            resolver,
        )
        self._resolved_cache_maxsize = resolved_cache_maxsize
        self._resolved_cache: FullPathResolvedCache = FullPathResolvedCache(
            maxsize=resolved_cache_maxsize
        )

    def __eq__(self, other: object) -> Any:
        if not isinstance(other, SchemaAccessor):
            return NotImplemented
        # See the class docstring for the identity contract. Both
        # discriminators are reference-stable: `_node` is the
        # constructor argument and `_path_resolver` is constructed
        # once in `__init__` and never reassigned (only its inner
        # `resolver` field is swapped when the registry evolves).
        return (
            type(self) is type(other)
            and self._node is other._node
            and self._path_resolver is other._path_resolver
        )

    def __hash__(self) -> int:
        # Reference-stable inputs only — does not depend on the schema
        # dict being hashable or on the mutating registry.
        return hash(
            (
                type(self),
                id(self._node),
                id(self._path_resolver),
            )
        )

    @classmethod
    def from_schema(
        cls,
        schema: Schema,
        specification: Specification[Schema] = DRAFT202012,
        base_uri: str = "",
        handlers: ResolverHandlers | None = None,
        resolved_cache_maxsize: int = 0,
    ) -> "SchemaAccessor":
        if handlers is None:
            handlers = default_handlers
        retriever = SchemaRetriever(handlers, specification)
        base_resource = specification.create_resource(schema)
        registry: Registry[Schema] = Registry(
            retrieve=retriever,  # type: ignore
        )
        registry = registry.with_resource(base_uri, base_resource)
        resolver = registry.resolver(base_uri=base_uri)
        return cls(
            schema,
            resolver,
            resolved_cache_maxsize=resolved_cache_maxsize,
        )

    @property
    def base_uri(self) -> str:
        return self._path_resolver.resolver._base_uri

    @property
    def resolver(self) -> Resolver[Schema]:
        warnings.warn(
            "SchemaAccessor.resolver is deprecated. "
            "Use SchemaPath.base_uri to access the base URI and "
            "SchemaPath.resolve() to resolve paths.",
            DeprecationWarning,
        )
        return self._path_resolver.resolver

    def __getitem__(self, parts: Sequence[LookupKey]) -> LookupNode:
        resolved = self.get_resolved(parts)
        return resolved.contents

    def stat(self, parts: Sequence[Hashable]) -> dict[str, Any] | None:
        try:
            node = self[cast(Sequence[LookupKey], parts)]
        except (KeyError, IndexError, TypeError):
            return None

        if self._is_traversable_node(node):
            return {
                "type": type(node).__name__,
                "length": len(node),
            }
        try:
            length = len(cast(Any, node))
        except TypeError:
            length = None

        return {
            "type": type(node).__name__,
            "length": length,
        }

    def keys(self, parts: Sequence[LookupKey]) -> Sequence[LookupKey]:
        node = self[parts]

        if isinstance(node, dict):
            # dict_keys has O(1) membership, no allocation.
            return cast(Sequence[LookupKey], node.keys())
        if isinstance(node, list):
            # range has O(1) membership and supports iteration.
            return cast(Sequence[LookupKey], range(len(node)))

        # Non-traversable leaf.
        if parts:
            raise KeyError(parts[-1])
        raise KeyError

    def len(self, parts: Sequence[LookupKey]) -> int:
        node = self[parts]
        if isinstance(node, (dict, list)):
            return len(node)
        if parts:
            raise KeyError(parts[-1])
        raise KeyError

    def contains(self, parts: Sequence[LookupKey], key: LookupKey) -> bool:
        try:
            node = self[parts]
        except (KeyError, IndexError, TypeError):
            return False

        if isinstance(node, dict):
            return key in node
        if isinstance(node, list):
            return isinstance(key, int) and 0 <= key < len(node)
        return False

    def require_child(
        self, parts: Sequence[LookupKey], key: LookupKey
    ) -> None:
        # Validate parent path for intermediate diagnostics.
        node = self[parts]

        if isinstance(node, dict):
            if key not in node:
                raise KeyError(key)
            return
        if isinstance(node, list):
            if not (isinstance(key, int) and 0 <= key < len(node)):
                raise KeyError(key)
            return

        raise KeyError(key)

    def read(self, parts: Sequence[LookupKey]) -> LookupValue:
        node = self[parts]
        return self._read_node(node)

    @contextmanager
    def resolve(
        self, parts: Sequence[LookupKey]
    ) -> Iterator[Resolved[LookupNode]]:
        try:
            yield self.get_resolved(parts)
        finally:
            pass

    def get_resolved(self, parts: Sequence[LookupKey]) -> Resolved[LookupNode]:
        cached_resolved = self._resolved_cache.get(parts)
        if cached_resolved is not None:
            # Read `_registry` directly: it is a stable attrs-backed
            # attribute on every supported referencing version (the
            # import-time `assert_referencing_layout` guarantees this)
            # and a plain attribute access is ~30ns vs ~100ns through a
            # helper with isinstance dispatch. The cold-path field
            # *write* still goes through `rebind_resolved`.
            current_registry = self._path_resolver.resolver._registry
            if cached_resolved.resolver._registry is current_registry:
                return cached_resolved
            # Rebind to the current registry rather than discard. Safe
            # under monotonic registry growth (see caches.py docstring).
            rebound = cast(
                Resolved[LookupNode],
                rebind_resolved(cached_resolved, current_registry),
            )
            self._resolved_cache.set(parts, rebound)
            return rebound

        result = self._path_resolver.resolve(self.node, parts)
        self._resolved_cache.set(parts, result.resolved)

        return result.resolved
