"""JSONSchema path caches module.

Both caches store ``Resolved`` values keyed on hashable schema paths.
Staleness across ``referencing.Registry`` growth is *not* handled by
invalidation here; the callers rebind cached ``Resolved`` values to the
current registry on read (see
``jsonschema_path._referencing_compat.rebind_registry``). This relies on
the assumption that registries grow monotonically — resources are added,
never replaced. Handlers that return drifting content for the same URI
violate that assumption; users who need to defend against that should
disable caching with ``resolved_cache_maxsize=0``.
"""

from collections import OrderedDict
from collections.abc import Sequence

from pathable.types import LookupKey
from pathable.types import LookupNode
from referencing._core import Resolved


class FullPathResolvedCache:
    def __init__(self, maxsize: int):
        self._maxsize = maxsize
        self._cache: OrderedDict[
            tuple[LookupKey, ...],
            Resolved[LookupNode],
        ] = OrderedDict()

    def _make_key(
        self,
        parts: Sequence[LookupKey],
    ) -> tuple[LookupKey, ...] | None:
        if self._maxsize <= 0:
            return None

        parts_tuple = tuple(parts)
        try:
            hash(parts_tuple)
        except TypeError:
            return None

        return parts_tuple

    def get(
        self,
        parts: Sequence[LookupKey],
    ) -> Resolved[LookupNode] | None:
        key = self._make_key(parts)
        if key is None:
            return None

        cached = self._cache.get(key)
        if cached is None:
            return None

        self._cache.move_to_end(key)
        return cached

    def set(
        self,
        parts: Sequence[LookupKey],
        resolved: Resolved[LookupNode],
    ) -> None:
        key = self._make_key(parts)
        if key is None:
            return

        self._cache[key] = resolved
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)


class PrefixResolvedCache:
    def __init__(self) -> None:
        self._cache: dict[tuple[LookupKey, ...], Resolved[LookupNode]] = {}

    def seed_root(self, resolved: Resolved[LookupNode]) -> None:
        self._cache[()] = resolved

    def longest_prefix_hit(
        self,
        parts: tuple[LookupKey, ...],
    ) -> tuple[int, Resolved[LookupNode]] | None:
        for idx in range(len(parts) - 1, -1, -1):
            prefix = parts[:idx]
            try:
                cached = self._cache.get(prefix)
            except TypeError:
                continue

            if cached is not None:
                return idx, cached

        return None

    def replace(
        self,
        parts: tuple[LookupKey, ...],
        index: int,
        resolved: Resolved[LookupNode],
    ) -> None:
        """Overwrite an existing prefix entry (used after a rebind)."""
        prefix = parts[:index]
        try:
            self._cache[prefix] = resolved
        except TypeError:
            pass

    def store_intermediate(
        self,
        parts: tuple[LookupKey, ...],
        index: int,
        resolved: Resolved[LookupNode],
    ) -> None:
        if index >= len(parts) - 1:
            return

        prefix = parts[: index + 1]
        try:
            self._cache[prefix] = resolved
        except TypeError:
            pass
