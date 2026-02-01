"""JSONSchema spec accessors module."""

from collections.abc import Hashable
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any
from typing import Iterator
from typing import Optional
from typing import cast

from pathable.accessors import LookupAccessor
from pathable.types import LookupKey
from pathable.types import LookupNode
from pathable.types import LookupValue
from pyrsistent import PDeque
from pyrsistent import pdeque
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
    _resolver_refs: dict[int, Optional[Resolver[Schema]]] = {}

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
        handlers: Optional[ResolverHandlers] = None,
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

    def stat(self, parts: Sequence[Hashable]) -> dict[str, Any]:
        d: Any = self.node
        for part in parts:
            if not isinstance(d, dict) or part not in d:
                return {"exists": False}
            d = cast(Any, d[part])
        return {"exists": True}

    def keys(self, parts: Sequence[LookupKey]) -> Sequence[LookupKey]:
        resolved = self.get_resolved(pdeque(parts))
        node = resolved.contents
        if isinstance(node, dict):
            # dict_keys has O(1) membership, no allocation.
            return cast(Sequence[LookupKey], node.keys())
        if isinstance(node, list):
            # range has O(1) membership and supports iteration.
            return cast(Sequence[LookupKey], range(len(node)))
        raise AttributeError

    def read(self, parts: Sequence[LookupKey]) -> LookupValue:
        resolved = self.get_resolved(pdeque(parts))
        return self._read_node(resolved.contents)

    @contextmanager
    def resolve(
        self, parts: Sequence[LookupKey]
    ) -> Iterator[Resolved[LookupNode]]:
        try:
            yield self.get_resolved(pdeque(parts))
        finally:
            pass

    def get_node(self, parts: PDeque[LookupKey]) -> LookupNode:
        resolved = self.get_resolved(parts)
        return resolved.contents

    def get_resolved(self, parts: PDeque[LookupKey]) -> Resolved[LookupNode]:
        resolved = self._get_resolved(
            self.node, pdeque(parts), resolver=self.resolver
        )
        self.resolver = self.resolver._evolve(
            self.resolver._base_uri,
            registry=resolved.resolver._registry,
        )
        return resolved

    @classmethod
    def _get_node(
        cls,
        node: LookupNode,
        parts: PDeque[LookupKey],
        resolver: Optional[Resolver[Schema]] = None,
    ) -> LookupNode:
        resolved = cls._get_resolved(node, parts, resolver)
        return resolved.contents

    @classmethod
    def _get_resolved(
        cls,
        node: LookupNode,
        parts: PDeque[LookupKey],
        resolver: Optional[Resolver[Schema]] = None,
    ) -> Resolved[LookupNode]:
        if resolver is not None:
            resolved = cls._resolve_node(node, resolver)
            node, resolver = resolved.contents, resolved.resolver

        try:
            part, parts = cls._pop_next_part(parts)
        except IndexError:
            return Resolved(node, resolver)  # type: ignore

        subnode = cls._get_subnode(node, part)
        return cls._get_resolved(subnode, parts, resolver=resolver)

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
