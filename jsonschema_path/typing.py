from collections.abc import Hashable
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Union

from pathable.protocols import Subscriptable

# @TODO: replace with types from pathable
LookupKey = Union[str, int]
LookupValue = Union[Mapping[LookupKey, Any], Iterable[Any], Any]
Lookup = Subscriptable[LookupKey, LookupValue]

ResolverHandlers = Mapping[str, Any]
Schema = Mapping[str, Any]
