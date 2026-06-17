"""JSONSchema spec nodes module."""

from typing import cast

from pathable.accessors import LookupAccessor
from pathable.types import LookupNode
from referencing._core import Resolved
from referencing._core import Resolver

from jsonschema_path._referencing_compat import resolve_ref
from jsonschema_path.typing import Schema
from jsonschema_path.utils import is_ref


class SchemaNode(LookupAccessor):
    @classmethod
    def _resolve_node(
        cls,
        node: LookupNode,
        resolver: Resolver[Schema],
    ) -> Resolved[Schema]:
        if is_ref(node):
            ref_node = cls._get_subnode(node, "$ref")
            ref = cls._read_node(ref_node)
            result = resolve_ref(resolver, ref)
            return cls._resolve_node(
                result.resolved.contents,
                result.resolved.resolver,
            )
        return Resolved(cast(Schema, node), resolver)  # type: ignore
