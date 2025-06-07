from typing import Any
from typing import Mapping

from pathable.types import LookupKey as SchemaKey
from pathable.types import LookupNode as SchemaNode
from pathable.types import LookupValue as SchemaValue

__all__ = [
    "ResolverHandlers",
    "Schema",
    "SchemaNode",
    "SchemaKey",
    "SchemaValue",
]

ResolverHandlers = Mapping[str, Any]
Schema = Mapping[str, Any]
