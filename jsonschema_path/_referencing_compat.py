"""Compatibility shim and workarounds for the ``referencing`` library.

This module is the *only* place in jsonschema-path that touches
``referencing._core`` internals (the ``_base_uri``, ``_registry``, and
``_previous`` attributes on ``Resolver``). Every other module must go
through the helpers here.

The motivation is firewalling: if a future ``referencing`` release
reshapes those internals, the breakage is contained to this file. The
``assert_referencing_layout`` call at import time also converts what
would otherwise be silent wrong-results into a loud ``ImportError`` that
names the issue, so version-skew bugs surface immediately.

The helpers intentionally use ``Any``-typed generics because
``referencing`` does not expose ``Resolver`` / ``Resolved`` as
``attrs``-typed classes to type checkers, and ``Resolver._evolve``
itself is declared ``**kwargs: Any``. The runtime invariants are
enforced by ``assert_referencing_layout``; ``mypy`` is asked to trust
this single module.

Supported ``referencing`` versions: the upper bound is pinned in
``pyproject.toml``; the lower bound is implied by these internals being
``attrs`` fields named ``_base_uri``, ``_registry``, and ``_previous``.

----------------------------------------------------------------------------
Known ``referencing`` limitations worked around in this module
----------------------------------------------------------------------------

**1. ``resolver.lookup`` cannot traverse list items via JSON Pointer**
   (tracked upstream as a bug)

   When resolving a pointer fragment such as ``#/allOf/0`` or
   ``#/prefixItems/1``, ``referencing`` calls ``maybe_in_subresource``
   at each step to check for embedded resources.  That helper calls
   ``node.get("$id")`` unconditionally, but list nodes have no ``.get``
   method, so any pointer that passes through an array raises
   ``AttributeError``.

   Workaround: :func:`decode_pointer_fragment` parses pointer fragments
   directly against the raw Python dict/list tree, coercing numeric
   tokens to ``int`` when the current node is a list.  Remove it and
   delegate back to ``resolver.lookup`` once the upstream bug is fixed.

**2. ``resolver.lookup`` cannot resolve anchors in arbitrary document
   structures**
   (design limitation — the library only crawls known-vocabulary keywords)

   Before an anchor can be resolved via ``resolver.lookup("#myAnchor")``,
   it must be registered during the document crawl.  The crawl descends
   only into known JSON Schema vocabulary keywords (``$defs``,
   ``properties``, ``items``, …).  Anchors placed in non-standard keys
   (e.g. OpenAPI's ``components/schemas``, or any user-defined key) are
   never discovered, and ``resolver.lookup`` raises ``NoSuchAnchor``.

   Workaround: :func:`find_anchor_in_doc` performs a full depth-first
   scan of the raw document, searching every key for
   ``$anchor``/``$dynamicAnchor``, respecting embedded-resource
   boundaries (``$id`` / draft-04 ``id``).  Remove it and delegate back
   to ``resolver.lookup`` if the upstream crawler is extended to cover
   arbitrary document structures.

Both workarounds are applied together in :func:`resolve_ref`, which
is the single drop-in replacement for ``resolver.lookup`` used throughout
this codebase.  Callers should use ``resolve_ref`` rather than calling
``decode_pointer_fragment`` or ``find_anchor_in_doc`` directly.  When
either upstream issue is fixed, only ``resolve_ref`` needs updating.
"""

from __future__ import annotations

from typing import Any
from typing import NamedTuple
from typing import cast
from urllib.parse import unquote as _url_unquote

import attrs
from referencing import Registry
from referencing._core import Resolved
from referencing._core import Resolver
from referencing.exceptions import Unresolvable

from jsonschema_path.typing import SchemaKey


class LookupResult(NamedTuple):
    """Return type of :func:`resolve_ref`.

    ``resolved`` is the ``Resolved`` object for the target node (same
    shape as ``resolver.lookup`` returns).  ``parts`` is the tuple of
    path segments from the target document root to that node — needed by
    ``SchemaPath.canonical`` to build a ``SchemaPath`` without a separate
    identity scan.
    """

    resolved: Resolved[Any]
    parts: tuple[SchemaKey, ...]


_REQUIRED_RESOLVER_FIELDS = frozenset({"_base_uri", "_registry", "_previous"})


def assert_referencing_layout() -> None:
    """Verify ``referencing.Resolver`` exposes the attrs fields we rebind.

    Called once at import time. Raises ``ImportError`` if the installed
    ``referencing`` is incompatible, instead of allowing rebind operations
    to silently produce wrong results.
    """
    fields = {
        field.name
        for field in attrs.fields(Resolver)  # type: ignore[arg-type]
    }
    missing = _REQUIRED_RESOLVER_FIELDS - fields
    if missing:
        raise ImportError(
            "jsonschema-path is incompatible with the installed version "
            "of `referencing`. Expected `Resolver` attrs fields to "
            f"include {sorted(_REQUIRED_RESOLVER_FIELDS)}; missing "
            f"{sorted(missing)}. Pin `referencing` to a supported "
            "version (see jsonschema_path/_referencing_compat.py)."
        )


def rebind_registry(
    resolver: Resolver[Any],
    registry: Registry[Any],
) -> Resolver[Any]:
    """Return a new resolver identical to *resolver* but with *registry*.

    ``referencing.Registry`` instances are immutable and grow
    monotonically via ``with_resource``. A cached ``Resolver`` captured
    before the registry grew can be cheaply rebound to the latest
    registry without re-walking the schema, because:

    * The resolver's ``base_uri`` describes a document scope that the
      newer registry, being a superset, still contains.
    * ``Resolver._previous`` holds URIs (not resolver snapshots), and
      ``Resolver.dynamic_scope`` re-uses ``self._registry`` for every
      frame, so swapping the top resolver's registry rebinds the entire
      dynamic scope in one shot.

    Uses ``attrs.evolve`` rather than ``Resolver._evolve`` because the
    latter pushes onto the dynamic-scope stack when called with a
    differing ``base_uri``. We want a pure field replacement.
    """
    return attrs.evolve(resolver, registry=registry)  # type: ignore[misc]


def rebind_resolved(
    resolved: Resolved[Any],
    registry: Registry[Any],
) -> Resolved[Any]:
    """Return a new ``Resolved`` with the same ``contents`` but a
    resolver rebound to *registry*.

    Centralizing the ``Resolved(...)`` construction here keeps the
    ``call-arg`` type-ignore confined to a single line — production
    callers (``SchemaAccessor.get_resolved`` and
    ``CachedPathResolver._resolve_with_prefix_cache``) work in terms of
    this helper and don't have to construct ``Resolved`` themselves.
    """
    return Resolved(  # type: ignore[call-arg]
        contents=resolved.contents,
        resolver=rebind_registry(resolved.resolver, registry),
    )


def registry_of(resolver: Resolver[Any]) -> Registry[Any]:
    """Return the registry backing *resolver*."""
    return resolver._registry


def base_uri_of(resolver: Resolver[Any]) -> str:
    """Return the base URI of *resolver*."""
    return resolver._base_uri


# ---------------------------------------------------------------------------
# Raw document navigation (no $ref following)
# ---------------------------------------------------------------------------


def raw_lookup(node: Any, parts: tuple[Any, ...]) -> Any:
    """Navigate *node* through *parts* without following ``$ref``.

    Each element of *parts* is a ``str`` key (for dicts) or an ``int``
    index (for lists).  String parts are coerced to ``int`` when the
    current node is a list, matching how pathable stores array indices.

    Raises ``KeyError`` / ``IndexError`` for missing segments so callers
    can detect dead-end paths without catching a generic exception.
    """
    for part in parts:
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            idx = int(part) if isinstance(part, str) else part
            node = node[idx]
        else:
            raise KeyError(part)
    return node


# ---------------------------------------------------------------------------
# Workaround 1: JSON Pointer fragment traversal over list nodes
# See module docstring — remove once the upstream bug is fixed.
# ---------------------------------------------------------------------------


def decode_pointer_fragment(
    root_node: Any,
    fragment: str,
) -> tuple[SchemaKey, ...]:
    """Decode a ``/``-prefixed JSON Pointer fragment into path parts.

    Applies RFC 6901 token unescaping (``~1`` → ``/``, ``~0`` → ``~``)
    and URL percent-decoding.  Numeric tokens are coerced to ``int``
    when the current node is a ``list``, matching how pathable stores
    array indices.

    ``fragment`` must start with ``'/'``.

    This function exists because ``referencing.Resolver.lookup`` crashes
    on pointer fragments that pass through list nodes — see the module
    docstring for details.
    """
    # Special case: bare slash means the empty-string key.
    if fragment == "/":
        return ("",)

    parts: list[SchemaKey] = []
    node: Any = root_node

    for token in fragment[1:].split("/"):
        # RFC 6901 unescaping then percent-decode
        token = token.replace("~1", "/").replace("~0", "~")
        token = _url_unquote(token)

        if isinstance(node, list):
            idx = int(token)  # raises ValueError for malformed pointers
            parts.append(idx)
            node = node[idx] if 0 <= idx < len(node) else None
        elif isinstance(node, dict):
            parts.append(cast(SchemaKey, token))
            node = node.get(token)
        else:
            # Non-traversable node — append as string, stop navigating.
            parts.append(cast(SchemaKey, token))
            node = None

    return tuple(parts)


# ---------------------------------------------------------------------------
# Workaround 2: Anchor resolution in arbitrary document structures
# See module docstring — remove once the upstream crawler is extended.
# ---------------------------------------------------------------------------


def find_anchor_in_doc(
    node: Any,
    anchor_name: str,
    *,
    is_root: bool = True,
) -> tuple[SchemaKey, ...] | None:
    """Find the JSON Pointer parts to the schema node whose ``$anchor`` or
    ``$dynamicAnchor`` equals *anchor_name* within *node*.

    Embedded resources (nodes with ``$id`` other than the root) are not
    searched — anchor names are scoped to their containing resource.

    Returns the parts tuple from *node* to the anchor, or ``None`` if the
    anchor is not present in the (root) resource scope.

    This function exists because ``referencing.Resolver.lookup`` cannot
    find anchors placed outside known JSON Schema vocabulary keywords —
    see the module docstring for details.
    """
    if not isinstance(node, dict):
        return None

    # Embedded resources own their anchor namespace; skip their subtrees.
    # "$id" is the draft 2019-09/2020-12 keyword; "id" (no dollar) is the
    # draft-04/06/07 equivalent — both mark a resource boundary.
    if not is_root and (
        isinstance(node.get("$id"), str) or isinstance(node.get("id"), str)
    ):
        return None

    # Does this node itself carry the anchor?
    if (
        node.get("$anchor") == anchor_name
        or node.get("$dynamicAnchor") == anchor_name
    ):
        return ()

    # Recurse depth-first into dict values and list elements.
    for key, value in node.items():
        if isinstance(value, dict):
            result = find_anchor_in_doc(value, anchor_name, is_root=False)
            if result is not None:
                return (cast(SchemaKey, key),) + result
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    result = find_anchor_in_doc(
                        item, anchor_name, is_root=False
                    )
                    if result is not None:
                        return (cast(SchemaKey, key), idx) + result

    return None


# ---------------------------------------------------------------------------
# Unified replacement for resolver.lookup — applies both workarounds.
# See module docstring.  To remove a workaround, update only this function.
# ---------------------------------------------------------------------------


def resolve_ref(resolver: Resolver[Any], ref: str) -> LookupResult:
    """Resolve *ref* against *resolver*, applying both referencing workarounds.

    Drop-in replacement for ``resolver.lookup(ref)`` that additionally:

    * Parses JSON Pointer fragments manually to avoid the list-traversal
      bug (workaround 1).
    * Scans the document for ``$anchor``/``$dynamicAnchor`` instead of
      relying on the registry crawl (workaround 2).

    Returns a :class:`LookupResult` with the resolved node and the parts
    path from the target document root to that node.

    **URI resolution** (relative URIs, base-URI joining) is still
    delegated to ``resolver.lookup`` for the document-loading step;
    only the fragment resolution part is handled here.

    ``$dynamicRef`` is intentionally not handled — its target is
    scope-dependent and cannot be resolved statically.

    **Error contract** — like ``resolver.lookup``, this function raises
    :class:`referencing.exceptions.Unresolvable` when the target cannot
    be reached:

    * A missing JSON Pointer path (e.g. ``#/$defs/Missing``) —
      ``raw_lookup`` raises ``KeyError`` internally, which is caught and
      re-raised as ``Unresolvable``.
    * A missing anchor (e.g. ``#nonExistent``) — raises ``Unresolvable``
      rather than the library's ``NoSuchAnchor`` (a subclass of
      ``Unresolvable``), since we locate anchors without the registry
      crawler.
    """
    # ------------------------------------------------------------------ #
    # 1. Split the ref into a base URI and a fragment at the first '#'.   #
    # ------------------------------------------------------------------ #
    hash_idx = ref.find("#")
    if hash_idx >= 0:
        base_part: str = ref[:hash_idx]
        fragment: str = ref[hash_idx + 1 :]
    else:
        base_part = ref
        fragment = ""

    # ------------------------------------------------------------------ #
    # 2. Load the target document if the ref crosses a document boundary. #
    #    We append "#" to force resolver.lookup to treat the URI as a     #
    #    document root reference (empty fragment = root node).            #
    # ------------------------------------------------------------------ #
    if base_part:
        ext_resolved = resolver.lookup(base_part + "#")
        target_resolver: Resolver[Any] = ext_resolved.resolver
    else:
        target_resolver = resolver

    # ------------------------------------------------------------------ #
    # 3. Obtain the root schema from the registry.                        #
    #    registry.contents(uri) returns the same Python object for the    #
    #    same URI within a registry lineage — identity is stable.         #
    # ------------------------------------------------------------------ #
    root_schema: Any = target_resolver._registry.contents(
        target_resolver._base_uri
    )

    # ------------------------------------------------------------------ #
    # 4. Resolve the fragment using our workarounds.                      #
    # ------------------------------------------------------------------ #
    if not fragment:
        # "#" or "file:///x.json#" — the document root.
        parts: tuple[Any, ...] = ()
    elif fragment.startswith("/"):
        # JSON Pointer — workaround 1.
        parts = decode_pointer_fragment(root_schema, fragment)
    else:
        # Anchor — workaround 2.
        found = find_anchor_in_doc(root_schema, fragment)
        if found is None:
            raise Unresolvable(ref)
        parts = found

    try:
        node = raw_lookup(root_schema, parts) if parts else root_schema
    except (KeyError, IndexError, ValueError) as exc:
        raise Unresolvable(ref) from exc
    return LookupResult(
        resolved=Resolved(  # type: ignore[call-arg]
            contents=node,
            resolver=target_resolver,
        ),
        parts=parts,
    )


# Verify referencing layout at import time so version-skew fails loud.
assert_referencing_layout()
