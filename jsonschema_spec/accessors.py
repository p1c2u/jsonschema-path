"""JSONSchema spec accessors module."""
from collections import deque
from contextlib import contextmanager
from typing import Any
from typing import Deque
from typing import Hashable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Union

from jsonschema.validators import RefResolver
from pathable.accessors import LookupAccessor

from jsonschema_spec.utils import is_ref


class SpecAccessor(LookupAccessor):
    def __init__(self, lookup: Mapping[Hashable, Any], resolver: RefResolver):
        super().__init__(lookup)
        self.resolver = resolver

    @contextmanager
    def open(
        self, parts: List[Hashable]
    ) -> Iterator[Union[Mapping[Hashable, Any], Any]]:
        parts_deque = deque(parts)
        try:
            yield self._open(self.lookup, parts_deque)
        finally:
            pass

    def _open(
        self, content: Mapping[Hashable, Any], parts_deque: Deque[Hashable]
    ) -> Any:
        if is_ref(content):
            ref = content["$ref"]
            with self.resolver.resolving(ref) as resolved:
                return self._open(resolved, parts_deque)

        try:
            part = parts_deque.popleft()
        except IndexError:
            return content
        else:
            target = content[part]
            return self._open(target, parts_deque)
