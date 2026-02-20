"""JSONSchema spec accessors module."""

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

from jsonschema_path.handlers import default_handlers
from jsonschema_path.retrievers import SchemaRetriever
from jsonschema_path.typing import ResolverHandlers
from jsonschema_path.typing import Schema
from jsonschema_path.utils import is_ref


class SchemaAccessor(LookupAccessor):
    _resolver_refs: dict[int, Resolver[Schema] | None] = {}

    def __init__(self, schema: Schema, resolver: Resolver[Schema]):
        super().__init__(cast(LookupNode, schema))
        self.resolver = resolver

        self._resolver_refs[id(schema)] = resolver

    @classmethod
    def from_schema(
        cls,
        schema: Schema,
        specification: Specification[Schema] = DRAFT202012,
        base_uri: str = "",
        handlers: ResolverHandlers | None = None,
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
        return cls(schema, resolver)

    def __getitem__(self, parts: Sequence[LookupKey]) -> LookupNode:
        return self._get_node(self.node, parts, self.resolver)

    def stat(self, parts: Sequence[Hashable]) -> dict[str, Any] | None:
        try:
            resolved = self.get_resolved(cast(Sequence[LookupKey], parts))
        except (KeyError, IndexError, TypeError):
            return None

        node = resolved.contents

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
        resolved = self.get_resolved(parts)
        node = resolved.contents

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
        resolved = self.get_resolved(parts)
        node = resolved.contents
        if isinstance(node, (dict, list)):
            return len(node)
        if parts:
            raise KeyError(parts[-1])
        raise KeyError

    def contains(self, parts: Sequence[LookupKey], key: LookupKey) -> bool:
        try:
            resolved = self.get_resolved(parts)
        except (KeyError, IndexError, TypeError):
            return False

        node = resolved.contents
        if isinstance(node, dict):
            return key in node
        if isinstance(node, list):
            return isinstance(key, int) and 0 <= key < len(node)
        return False

    def require_child(
        self, parts: Sequence[LookupKey], key: LookupKey
    ) -> None:
        # Validate parent path for intermediate diagnostics.
        resolved = self.get_resolved(parts)
        node = resolved.contents

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
        resolved = self.get_resolved(parts)
        return self._read_node(resolved.contents)

    @contextmanager
    def resolve(
        self, parts: Sequence[LookupKey]
    ) -> Iterator[Resolved[LookupNode]]:
        try:
            yield self.get_resolved(parts)
        finally:
            pass

    def get_resolved(self, parts: Sequence[LookupKey]) -> Resolved[LookupNode]:
        resolved = self._get_resolved(self.node, parts, resolver=self.resolver)
        self.resolver = self.resolver._evolve(
            self.resolver._base_uri,
            registry=resolved.resolver._registry,
        )
        return resolved

    @classmethod
    def _get_resolved(
        cls,
        node: LookupNode,
        parts: Sequence[LookupKey],
        resolver: Resolver[Schema] | None = None,
    ) -> Resolved[LookupNode]:
        if resolver is None:
            raise ValueError("resolver must be provided")

        current_node: LookupNode = node
        current_resolver: Resolver[Schema] = resolver

        for part in parts:
            resolved = cls._resolve_node(current_node, current_resolver)
            current_node, current_resolver = (
                resolved.contents,
                resolved.resolver,
            )
            current_node = cls._get_subnode(current_node, part)

        resolved = cls._resolve_node(current_node, current_resolver)
        return cast(Resolved[LookupNode], resolved)

    @classmethod
    def _resolve_node(
        cls,
        node: LookupNode,
        resolver: Resolver[Schema],
    ) -> Resolved[Schema]:
        if is_ref(node):
            ref_node = cls._get_subnode(node, "$ref")
            ref = cls._read_node(ref_node)
            resolved = resolver.lookup(ref)
            return cls._resolve_node(
                resolved.contents,
                resolved.resolver,
            )
        return Resolved(cast(Schema, node), resolver)  # type: ignore

    @classmethod
    def _get_node(
        cls,
        node: LookupNode,
        parts: Sequence[LookupKey],
        resolver: Resolver[Schema] | None = None,
    ) -> LookupNode:
        if resolver is None:
            raise ValueError("resolver must be provided")

        current_node: LookupNode = node
        current_resolver: Resolver[Schema] = resolver

        for part in parts:
            resolved = cls._resolve_node(current_node, current_resolver)
            current_node, current_resolver = (
                resolved.contents,
                resolved.resolver,
            )
            current_node = cls._get_subnode(current_node, part)
        return current_node
