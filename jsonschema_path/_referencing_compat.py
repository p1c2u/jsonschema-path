"""Compatibility shim for the ``referencing`` library's private API.

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
"""

from __future__ import annotations

from typing import Any
from typing import Union

import attrs
from referencing import Registry
from referencing._core import Resolved
from referencing._core import Resolver

ResolvedOrResolver = Union[Resolved[Any], Resolver[Any]]

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


def registry_of(target: ResolvedOrResolver) -> Registry[Any]:
    """Return the registry backing a Resolved or Resolver."""
    if isinstance(target, Resolved):
        return target.resolver._registry
    return target._registry


def base_uri_of(target: ResolvedOrResolver) -> str:
    """Return the base URI of a Resolved or Resolver."""
    if isinstance(target, Resolved):
        return target.resolver._base_uri
    return target._base_uri


# Verify referencing layout at import time so version-skew fails loud.
assert_referencing_layout()
