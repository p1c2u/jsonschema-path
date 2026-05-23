"""Tests for the referencing compatibility shim.

The shim is the single firewall against ``referencing`` private-API
drift. These tests pin the behavior we depend on so that a future
``referencing`` release that changes it produces a meaningful failure
here rather than mysterious cache bugs elsewhere.
"""

from unittest.mock import patch

import attrs
import pytest
from referencing import Registry
from referencing._core import Resolved
from referencing._core import Resolver
from referencing.jsonschema import DRAFT202012

from jsonschema_path._referencing_compat import assert_referencing_layout
from jsonschema_path._referencing_compat import base_uri_of
from jsonschema_path._referencing_compat import rebind_registry
from jsonschema_path._referencing_compat import rebind_resolved
from jsonschema_path._referencing_compat import registry_of


def _build_resolver(resources):
    registry = Registry()
    for uri, doc in resources.items():
        registry = registry.with_resource(
            uri, DRAFT202012.create_resource(doc)
        )
    base_uri = next(iter(resources)) if resources else ""
    return registry.resolver(base_uri=base_uri), registry


class TestRebindRegistry:
    def test_swaps_registry_only(self):
        resolver, reg1 = _build_resolver({"a://1": {"v": 1}})
        reg2 = reg1.with_resource(
            "a://2", DRAFT202012.create_resource({"v": 2})
        )

        new_resolver = rebind_registry(resolver, reg2)

        assert new_resolver._registry is reg2
        # base_uri and dynamic-scope previous chain must be untouched
        # — that is the *whole point* of using attrs.evolve rather than
        # Resolver._evolve (which would push to _previous on a
        # differing base_uri).
        assert new_resolver._base_uri == resolver._base_uri
        assert new_resolver._previous == resolver._previous

    def test_rebound_resolver_sees_new_resources(self):
        resolver, reg1 = _build_resolver({"a://1": {"v": 1}})
        reg2 = reg1.with_resource(
            "a://2", DRAFT202012.create_resource({"v": 2})
        )

        rebound = rebind_registry(resolver, reg2)
        looked_up = rebound.lookup("a://2")

        assert looked_up.contents == {"v": 2}

    def test_original_resolver_unchanged(self):
        resolver, reg1 = _build_resolver({"a://1": {"v": 1}})
        reg2 = reg1.with_resource(
            "a://2", DRAFT202012.create_resource({"v": 2})
        )

        _ = rebind_registry(resolver, reg2)

        # attrs.evolve must not mutate the source.
        assert resolver._registry is reg1


class TestRebindResolved:
    def test_preserves_contents_swaps_registry(self):
        resolver, reg1 = _build_resolver({"a://1": {"v": 1}})
        resolved = resolver.lookup("a://1")
        reg2 = reg1.with_resource(
            "a://2", DRAFT202012.create_resource({"v": 2})
        )

        rebound = rebind_resolved(resolved, reg2)

        assert rebound.contents is resolved.contents
        assert rebound.resolver._registry is reg2
        # Source must not be mutated.
        assert resolved.resolver._registry is reg1


class TestRegistryOf:
    def test_for_resolver(self):
        resolver, reg = _build_resolver({"a://1": {"v": 1}})

        assert registry_of(resolver) is reg

    def test_for_resolved(self):
        resolver, reg = _build_resolver({"a://1": {"v": 1}})
        resolved = resolver.lookup("a://1")

        assert isinstance(resolved, Resolved)
        assert registry_of(resolved.resolver) is resolved.resolver._registry


class TestBaseUriOf:
    def test_for_resolver(self):
        resolver, _ = _build_resolver({"a://1": {"v": 1}})

        assert base_uri_of(resolver) == "a://1"

    def test_for_resolved(self):
        resolver, _ = _build_resolver({"a://1": {"v": 1}})
        resolved = resolver.lookup("a://1")

        assert base_uri_of(resolved.resolver) == resolved.resolver._base_uri


class TestAssertReferencingLayout:
    def test_passes_with_current_referencing(self):
        # Must not raise under the supported referencing range.
        assert_referencing_layout()

    def test_raises_when_required_field_missing(self):
        # Simulate a future referencing that renames _registry. The
        # shim must surface a clear ImportError rather than letting
        # silent wrong-results escape into production.
        fake_fields = tuple(
            f for f in attrs.fields(Resolver) if f.name != "_registry"
        )
        with patch(
            "jsonschema_path._referencing_compat.attrs.fields",
            return_value=fake_fields,
        ):
            with pytest.raises(ImportError, match="referencing"):
                assert_referencing_layout()
