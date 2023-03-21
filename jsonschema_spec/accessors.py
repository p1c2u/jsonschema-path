"""JSONSchema spec accessors module."""
from collections import deque
from contextlib import contextmanager
from typing import Any
from typing import Deque
from typing import Hashable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union

from pathable.accessors import LookupAccessor
from referencing import Registry
from referencing import Specification
from referencing._core import Resolver
from referencing.jsonschema import DRAFT202012

from jsonschema_spec.handlers import default_handlers
from jsonschema_spec.retrievers import HandlersRetriever
from jsonschema_spec.typing import ResolverHandlers
from jsonschema_spec.typing import Schema
from jsonschema_spec.utils import is_ref


class ResolverAccessor(LookupAccessor):
    def __init__(self, schema: Schema, resolver: Resolver[Schema]):
        super().__init__(schema)
        self.resolver = resolver

    @classmethod
    def from_schema(
        cls,
        schema: Schema,
        specification: Specification[Schema] = DRAFT202012,
        base_uri: str = "",
        handlers: ResolverHandlers = default_handlers,
    ) -> "ResolverAccessor":
        retriever = HandlersRetriever(handlers, specification)
        base_resource = specification.create_resource(schema)
        registry: Registry[Schema] = Registry(
            retrieve=retriever,  # type: ignore
        )
        registry = registry.with_resource(base_uri, base_resource)
        resolver = registry.resolver(base_uri=base_uri)
        return cls(schema, resolver)

    @contextmanager
    def open(self, parts: List[Hashable]) -> Iterator[Union[Schema, Any]]:
        parts_deque = deque(parts)
        try:
            yield self._open(self.lookup, parts_deque)
        finally:
            pass

    def _open(
        self,
        content: Schema,
        parts_deque: Deque[Hashable],
        resolver: Optional[Resolver[Schema]] = None,
    ) -> Any:
        if is_ref(content):
            ref = content["$ref"]
            resolver = resolver or self.resolver
            resolved = resolver.lookup(ref)
            return self._open(
                resolved.contents, parts_deque, resolver=resolved.resolver
            )

        try:
            part = parts_deque.popleft()
        except IndexError:
            return content
        else:
            target = content[part]
            return self._open(target, parts_deque, resolver=resolver)
