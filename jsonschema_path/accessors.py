"""JSONSchema spec accessors module."""

import warnings
import weakref
from collections.abc import Hashable
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Any
from typing import ClassVar
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

from jsonschema_path._referencing_compat import base_uri_of
from jsonschema_path._referencing_compat import raw_lookup
from jsonschema_path._referencing_compat import rebind_resolved
from jsonschema_path._referencing_compat import registry_of
from jsonschema_path._referencing_compat import resolve_ref
from jsonschema_path.caches import FullPathResolvedCache
from jsonschema_path.handlers import default_handlers
from jsonschema_path.resolvers import CachedPathResolver
from jsonschema_path.retrievers import SchemaRetriever
from jsonschema_path.typing import ResolverHandlers
from jsonschema_path.typing import Schema
from jsonschema_path.utils import is_ref


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

    # Class-level weak-value cache: maps id(root_schema) → SchemaAccessor.
    # Used by SchemaPath.canonical so that any two canonical computations
    # that resolve to the same external document share a single accessor
    # instance (required for `canonical_a.accessor is canonical_b.accessor`
    # when both point to the same document).  WeakValue semantics mean the
    # cached accessor is collected as soon as no SchemaPath holds it.
    #
    # Why id(root_schema) is the right key:
    #   ``referencing`` guarantees that ``registry.contents(uri)`` returns
    #   the *same Python object* for a given URI throughout a single registry
    #   lineage.  Two independent traversal chains start from separate
    #   lineages, so without intervention they would produce different Python
    #   objects for the same file (breaking id-based sharing).
    #
    #   ``SchemaPath.canonical`` closes this gap with a registry sync-back:
    #   after following a cross-document chain it propagates the fully-loaded
    #   registry back to the originating accessor.  The next traversal from
    #   that accessor therefore finds the document already present in its
    #   lineage and ``registry.contents(uri)`` returns the identical object.
    #
    #   Compared with URI-only keying, id(root_schema) is stricter: two
    #   different schema objects at the same URI (only possible if separate
    #   registries were built from different content) will never share an
    #   accessor, eliminating the stale-entry risk entirely.
    #
    # Safety against id reuse:
    #   The cache holds the accessor weakly; the accessor in turn holds a
    #   strong reference to root_schema.  An id can only be recycled after
    #   both the accessor *and* root_schema have been freed, at which point
    #   the WeakValue entry has already been removed — so there is no
    #   collision.
    _canonical_cache: ClassVar[
        weakref.WeakValueDictionary[int, "SchemaAccessor"]
    ] = weakref.WeakValueDictionary()

    @classmethod
    def _get_or_build_canonical(
        cls,
        root_schema: Any,
        target_base_uri: str,
        target_registry: Any,
    ) -> "SchemaAccessor":
        """Return (or lazily create and cache) a ``SchemaAccessor`` for the
        external document at *target_base_uri*.

        The cache is class-level (``_canonical_cache``) so that any
        two ``canonical`` computations pointing at the same document URI share
        a single accessor instance — necessary for the
        ``canonical_a.accessor is canonical_b.accessor`` guarantee when both
        paths resolve to the same external schema.

        Values are held weakly: an accessor is evicted once no
        ``SchemaPath.canonical`` references it.  See ``_canonical_cache`` for
        the rationale behind keying on ``id(root_schema)``.
        """
        cache_key = id(root_schema)
        cached = cls._canonical_cache.get(cache_key)
        if cached is not None:
            return cached
        root_resolver = target_registry.resolver(base_uri=target_base_uri)
        new_accessor = cls(root_schema, root_resolver)
        cls._canonical_cache[cache_key] = new_accessor
        return new_accessor

    def _resolve_ref_hop(
        self,
        ref: str,
    ) -> tuple["SchemaAccessor", tuple[LookupKey, ...]]:
        """Follow a single ``$ref`` hop; return ``(target_accessor, target_parts)``.

        Delegates all URI parsing and fragment resolution to
        :func:`~jsonschema_path._referencing_compat.resolve_ref` (which
        applies both referencing workarounds).  This method's sole
        responsibility is converting the ``LookupResult`` into the
        ``(SchemaAccessor, parts)`` shape that the ``canonical`` loop needs.
        """
        pr = self._path_resolver
        result = resolve_ref(pr.resolver, ref)

        target_registry = registry_of(result.resolved.resolver)
        target_base_uri: str = base_uri_of(result.resolved.resolver)

        # Sync the source accessor's resolver so subsequent lookups in this
        # chain start from the now-expanded registry.
        pr._sync_registry(target_registry)

        if target_base_uri == self.base_uri:
            # Same-document ref — reuse this accessor.
            return self, result.parts

        # Cross-document ref — build or retrieve a shared accessor for the
        # target document (shared so canonical_a.accessor is canonical_b.accessor
        # when both paths resolve to the same external schema).
        root_schema: Any = target_registry.contents(target_base_uri)
        target_accessor = type(self)._get_or_build_canonical(
            root_schema, target_base_uri, target_registry
        )
        return target_accessor, result.parts

    def _resolve_canonical(
        self,
        parts: tuple[LookupKey, ...],
    ) -> tuple["SchemaAccessor", tuple[LookupKey, ...]]:
        """Follow ``$ref`` chains from ``(self, parts)`` to their canonical
        destination, returning ``(target_accessor, target_parts)``.

        This is the core loop for :meth:`SchemaPath.canonical`.  Keeping it
        here co-locates the hop logic, the cycle guard, and the registry
        sync-back — all of which are accessor-level concerns — so that
        ``SchemaPath.canonical`` only needs to translate the result into a
        path object.

        ``$dynamicRef`` is not followed (see ``SchemaPath.canonical``
        docstring for rationale).

        After a cross-document traversal the originating accessor's registry
        is synced with the final destination's registry.  This ensures that a
        subsequent call from the same document finds any newly loaded schemas
        already in the registry lineage, which stabilises
        ``registry.contents(uri)`` object identity — a requirement for the
        ``_canonical_cache`` key to hit correctly.
        """
        accessor: SchemaAccessor = self
        # Track (id(accessor), parts) pairs already visited so $ref cycles
        # terminate.  id() is safe: this loop is synchronous so no GC can
        # recycle an accessor's id mid-call.
        visited: set[tuple[int, tuple[LookupKey, ...]]] = set()

        while True:
            key = (id(accessor), parts)
            if key in visited:
                break
            visited.add(key)

            raw_node = raw_lookup(accessor._node, parts)

            if not is_ref(raw_node):
                break

            # $dynamicRef is intentionally not followed — its target is
            # scope-dependent and cannot be resolved statically.  When only
            # $dynamicRef is present, is_ref() returns False and the loop
            # already broke above.  When both $ref and $dynamicRef coexist,
            # we refuse to follow either rather than silently return a result
            # the schema author did not intend.
            if "$dynamicRef" in raw_node:
                break

            ref: str = raw_node["$ref"]
            accessor, parts = accessor._resolve_ref_hop(ref)

        # Propagate documents loaded during this traversal back to the
        # originating accessor's registry (see docstring).
        if accessor is not self:
            self._path_resolver._sync_registry(
                registry_of(accessor._path_resolver.resolver)
            )

        return accessor, parts

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
        return base_uri_of(self._path_resolver.resolver)

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
            # The cold-path write goes through `rebind_resolved`.
            current_registry = registry_of(self._path_resolver.resolver)
            if registry_of(cached_resolved.resolver) is current_registry:
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
