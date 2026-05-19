from unittest.mock import Mock
from unittest.mock import patch

import pytest
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from jsonschema_path import SchemaPath
from jsonschema_path.accessors import SchemaAccessor
from jsonschema_path.handlers import default_handlers
from jsonschema_path.nodes import SchemaNode
from jsonschema_path.retrievers import SchemaRetriever


class TestSchemaAccessorOpen:
    def test_dereferences_once(self):
        retrieve = Mock(return_value={"value": "tested"})
        accessor = SchemaAccessor.from_schema(
            {
                "one": {
                    "$ref": "x://testref",
                },
                "two": {
                    "$ref": "x://testref",
                },
            },
            handlers={"x": retrieve},
        )

        assert accessor.read(["one", "value"]) == "tested"
        assert accessor.read(["two", "value"]) == "tested"

        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorKeys:
    def test_dereferences_once(self):
        retrieve = Mock(return_value={"value": "tested"})
        accessor = SchemaAccessor.from_schema(
            {
                "one": {
                    "$ref": "x://testref",
                },
                "two": {
                    "$ref": "x://testref",
                },
            },
            handlers={"x": retrieve},
        )

        assert list(accessor.keys(["one"])) == ["value"]
        assert accessor.read(["two", "value"]) == "tested"

        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorLen:
    def test_empty_path_dict(self):
        accessor = SchemaAccessor.from_schema({"a": 1, "b": 2})

        assert accessor.len([]) == 2

    def test_list_node(self):
        accessor = SchemaAccessor.from_schema({"arr": ["x", "y", "z"]})

        assert accessor.len(["arr"]) == 3

    def test_primitive_raises(self):
        accessor = SchemaAccessor.from_schema({"scalar": 123})

        with pytest.raises(KeyError):
            accessor.len(["scalar"])

    def test_missing_path_raises(self):
        accessor = SchemaAccessor.from_schema({"a": {"b": 1}})

        with pytest.raises(KeyError):
            accessor.len(["missing"])  # type: ignore[list-item]

    def test_dereferences(self):
        retrieve = Mock(return_value={"inner": {"x": 1, "y": 2}})
        accessor = SchemaAccessor.from_schema(
            {"one": {"$ref": "x://testref"}},
            handlers={"x": retrieve},
        )

        assert accessor.len(["one", "inner"]) == 2
        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorContains:
    def test_dict_membership(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        assert accessor.contains([], "a") is True
        assert accessor.contains([], "missing") is False

    def test_list_membership(self):
        accessor = SchemaAccessor.from_schema({"arr": [10, 20]})

        assert accessor.contains(["arr"], 0) is True
        assert accessor.contains(["arr"], 1) is True
        assert accessor.contains(["arr"], 2) is False
        assert accessor.contains(["arr"], "0") is False

    def test_primitive_is_not_traversable(self):
        accessor = SchemaAccessor.from_schema({"scalar": 123})

        assert accessor.contains(["scalar"], "x") is False

    def test_missing_path_is_false(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        assert accessor.contains(["missing"], "x") is False

    def test_dereferences(self):
        retrieve = Mock(return_value={"value": "tested"})
        accessor = SchemaAccessor.from_schema(
            {"one": {"$ref": "x://testref"}},
            handlers={"x": retrieve},
        )

        assert accessor.contains(["one"], "value") is True
        assert accessor.contains(["one"], "missing") is False
        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorRequireChild:
    def test_dict_child(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        accessor.require_child([], "a")
        with pytest.raises(KeyError):
            accessor.require_child([], "missing")

    def test_list_child(self):
        accessor = SchemaAccessor.from_schema({"arr": [10, 20]})

        accessor.require_child(["arr"], 0)
        accessor.require_child(["arr"], 1)
        with pytest.raises(KeyError):
            accessor.require_child(["arr"], 2)
        with pytest.raises(KeyError):
            accessor.require_child(["arr"], "0")

    def test_primitive_raises(self):
        accessor = SchemaAccessor.from_schema({"scalar": 123})

        with pytest.raises(KeyError):
            accessor.require_child(["scalar"], "x")

    def test_missing_parent_path_raises(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        with pytest.raises(KeyError):
            accessor.require_child(["missing"], "x")

    def test_dereferences(self):
        retrieve = Mock(return_value={"value": {"k": "v"}})
        accessor = SchemaAccessor.from_schema(
            {"one": {"$ref": "x://testref"}},
            handlers={"x": retrieve},
        )

        accessor.require_child(["one"], "value")
        with pytest.raises(KeyError):
            accessor.require_child(["one"], "missing")
        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorResolverEvolution:
    def test_does_not_evolve_resolver_when_registry_unchanged(self):
        accessor = SchemaAccessor.from_schema(
            {"a": {"b": 1}},
        )
        initial_resolver = accessor._path_resolver.resolver

        assert accessor.read(["a", "b"]) == 1
        assert accessor._path_resolver.resolver is initial_resolver

        assert accessor.read(["a", "b"]) == 1
        assert accessor._path_resolver.resolver is initial_resolver

    def test_evolves_once_when_registry_changes(self):
        retrieve = Mock(return_value={"value": "tested"})
        accessor = SchemaAccessor.from_schema(
            {
                "one": {
                    "$ref": "x://testref",
                },
            },
            handlers={"x": retrieve},
        )
        initial_resolver = accessor._path_resolver.resolver

        assert accessor.read(["one", "value"]) == "tested"
        evolved_resolver = accessor._path_resolver.resolver
        assert evolved_resolver is not initial_resolver

        assert accessor.read(["one", "value"]) == "tested"
        assert accessor._path_resolver.resolver is evolved_resolver
        retrieve.assert_called_once_with("x://testref")


class TestSchemaAccessorResolvedCache:
    def test_disabled_by_default(self):
        accessor = SchemaAccessor.from_schema({"a": {"b": 1}})

        first = accessor.get_resolved(["a", "b"])
        second = accessor.get_resolved(["a", "b"])

        assert first is not second

    def test_cache_hit_for_same_parts(self):
        accessor = SchemaAccessor.from_schema(
            {"a": {"b": 1}},
            resolved_cache_maxsize=2,
        )

        first = accessor.get_resolved(["a", "b"])
        second = accessor.get_resolved(["a", "b"])

        assert first is second

    def test_lru_eviction(self):
        accessor = SchemaAccessor.from_schema(
            {"a": 1, "b": 2},
            resolved_cache_maxsize=1,
        )

        first_a = accessor.get_resolved(["a"])
        _ = accessor.get_resolved(["b"])
        second_a = accessor.get_resolved(["a"])

        assert first_a is not second_a

    def test_registry_evolution_rebinds_cached_resolved(self):
        retrieve = Mock(side_effect=[{"value": 1}, {"value": 2}])
        accessor = SchemaAccessor.from_schema(
            {
                "one": {
                    "$ref": "x://one",
                },
                "two": {
                    "$ref": "x://two",
                },
            },
            handlers={"x": retrieve},
            resolved_cache_maxsize=8,
        )

        first_one = accessor.get_resolved(["one", "value"])
        assert first_one.contents == 1
        registry_after_first = accessor._path_resolver.resolver._registry
        assert first_one.resolver._registry is registry_after_first

        second_two = accessor.get_resolved(["two", "value"])
        assert second_two.contents == 2
        registry_after_two = accessor._path_resolver.resolver._registry
        assert registry_after_two is not registry_after_first

        # Cache hit rebinds to the current registry instead of
        # re-resolving from scratch: same underlying contents object,
        # new Resolved wrapper carrying the up-to-date registry.
        second_one = accessor.get_resolved(["one", "value"])
        assert second_one.contents == 1
        assert second_one.contents is first_one.contents
        assert second_one.resolver._registry is registry_after_two
        assert second_one is not first_one

        # No re-retrieval — each $ref target is loaded exactly once.
        assert retrieve.call_count == 2

    def test_rebound_cache_hit_preserves_base_uri_and_previous(self):
        retrieve = Mock(side_effect=[{"value": 1}, {"value": 2}])
        accessor = SchemaAccessor.from_schema(
            {
                "one": {"$ref": "x://one"},
                "two": {"$ref": "x://two"},
            },
            handlers={"x": retrieve},
            resolved_cache_maxsize=8,
        )

        first_one = accessor.get_resolved(["one", "value"])
        _ = accessor.get_resolved(["two", "value"])
        rebound = accessor.get_resolved(["one", "value"])

        # Rebind is a pure registry field swap. base_uri and the
        # dynamic-scope `_previous` chain must survive intact, otherwise
        # subsequent $ref resolution under the rebound Resolved would
        # use the wrong scope.
        assert rebound.resolver._base_uri == first_one.resolver._base_uri
        assert rebound.resolver._previous == first_one.resolver._previous


class TestSchemaAccessorPrefixCache:
    def test_reuses_longest_resolved_prefix_for_siblings(self):
        accessor = SchemaAccessor.from_schema(
            {
                "components": {
                    "schemas": {
                        "A": {"type": "string"},
                        "B": {"type": "integer"},
                    }
                }
            }
        )

        with patch.object(
            SchemaNode,
            "_resolve_node",
            wraps=SchemaNode._resolve_node,
        ) as resolve_node:
            accessor.get_resolved(["components", "schemas", "A"])
            first_call_count = resolve_node.call_count

            accessor.get_resolved(["components", "schemas", "B"])
            second_call_increment = resolve_node.call_count - first_call_count

        assert first_call_count == 4
        assert second_call_increment == 1

    def test_keeps_disabled_full_path_identity_behavior(self):
        accessor = SchemaAccessor.from_schema(
            {
                "components": {
                    "schemas": {
                        "A": {"type": "string"},
                    }
                }
            }
        )

        first = accessor.get_resolved(["components", "schemas", "A"])
        second = accessor.get_resolved(["components", "schemas", "A"])

        assert first is not second

    def test_prefix_cache_is_preserved_when_registry_evolves(self):
        retrieve = Mock(return_value={"value": "tested"})
        accessor = SchemaAccessor.from_schema(
            {
                "one": {
                    "$ref": "x://testref",
                },
            },
            handlers={"x": retrieve},
        )
        prefix_cache = accessor._path_resolver.prefix_cache

        _ = accessor.get_resolved(["one", "value"])

        # Prefix cache used to be wiped on registry growth. With the
        # rebind-on-read strategy it retains its intermediate entry.
        assert accessor._path_resolver.prefix_cache is prefix_cache
        assert ("one",) in prefix_cache._cache

    def test_prefix_cache_rebound_avoids_redundant_retrieval(self):
        payloads = {
            "x://one": {
                "fast": "shallow",
                "deep": {"$ref": "x://later"},
            },
            "x://primer": {"primed": {"$ref": "x://later"}},
            "x://later": {"value": "found"},
        }
        retrieve = Mock(side_effect=lambda uri: payloads[uri])
        accessor = SchemaAccessor.from_schema(
            {
                "one": {"$ref": "x://one"},
                "primer": {"$ref": "x://primer"},
            },
            handlers={"x": retrieve},
        )

        # Populate the prefix cache for ("one",) under a registry that
        # only knows x://one. Walking through "fast" avoids loading
        # x://later at this point.
        assert accessor.read(["one", "fast"]) == "shallow"

        # Grow the registry through a different branch, loading
        # x://primer and x://later.
        assert accessor.read(["primer", "primed", "value"]) == "found"

        # Re-enter through the cached ("one",) prefix and follow a
        # $ref into x://later. Without rebind this would either fail
        # (resource unknown to the stale registry) or trigger a
        # second retrieve. With rebind it should reuse the already
        # loaded x://later resource.
        assert accessor.read(["one", "deep", "value"]) == "found"

        calls = sorted(c.args[0] for c in retrieve.call_args_list)
        assert calls == ["x://later", "x://one", "x://primer"]


class TestSchemaAccessorIdentity:
    """Locks in the per-resource-handle identity model.

    SchemaAccessor identity is the accessor instance itself, with
    discrimination on `_node` (by reference) and `_path_resolver`
    (by reference) — not a value tuple of its inputs. This forces the
    recommended lifecycle: construct one SchemaAccessor per schema
    document and reuse it across all derived SchemaPaths.
    """

    def test_same_instance_compares_equal_and_hashes_equal(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        assert accessor == accessor
        assert hash(accessor) == hash(accessor)

    def test_accessor_is_hashable(self):
        accessor = SchemaAccessor.from_schema({"a": 1})

        # Would raise TypeError before this PR (defining __eq__
        # without __hash__ silently makes instances unhashable).
        assert hash(accessor) == hash(accessor)
        {accessor}  # constructable as a set element

    def test_distinct_from_schema_calls_not_equal(self):
        # Each from_schema() call builds its own _path_resolver, so
        # the resulting accessors are distinct resource handles even
        # with identical arguments. This is the "reuse the accessor"
        # assertion: callers must hold onto the accessor instance,
        # not reconstruct it on demand.
        doc = {"a": 1}

        acc1 = SchemaAccessor.from_schema(doc)
        acc2 = SchemaAccessor.from_schema(doc)

        assert acc1 != acc2
        # Hashes are allowed to collide but are very unlikely to here.

    def test_distinct_dicts_not_equal(self):
        # Value-equal but distinct dict objects are distinct resources:
        # `_node is other._node` is false. Included for clarity even
        # though the `_path_resolver` check would also catch it.
        acc1 = SchemaAccessor.from_schema({"a": 1})
        acc2 = SchemaAccessor.from_schema({"a": 1})

        assert acc1 != acc2

    def test_different_base_uri_not_equal(self):
        # Same schema dict by reference, different base_uri → different
        # resources, because $ref resolution differs.
        doc = {"a": 1}

        acc1 = SchemaAccessor.from_schema(doc, base_uri="https://a/")
        acc2 = SchemaAccessor.from_schema(doc, base_uri="https://b/")

        assert acc1 != acc2

    def test_path_equality_follows_accessor_equality(self):
        accessor = SchemaAccessor.from_schema({"a": {"b": 1}})

        p1 = SchemaPath(accessor) / "a"
        p2 = SchemaPath(accessor) / "a"

        # Same accessor instance + same parts → equal paths and
        # equal hashes (delegated to pathable's AccessorPath identity).
        assert p1 == p2
        assert hash(p1) == hash(p2)

    def test_path_inequality_across_distinct_accessors(self):
        doc = {"a": {"b": 1}}
        acc1 = SchemaAccessor.from_schema(doc)
        acc2 = SchemaAccessor.from_schema(doc)

        p1 = SchemaPath(acc1) / "a"
        p2 = SchemaPath(acc2) / "a"

        # Distinct accessor instances → distinct resources → unequal
        # paths even though parts and underlying dict reference match.
        assert p1 != p2

    def test_resolved_cache_shared_when_accessor_reused(self):
        # Two paths over the same accessor hit the same resolved cache.
        # If a future refactor reintroduces per-path caching, this test
        # fails because the second .get_resolved would return a fresh
        # object instead of the cached one.
        accessor = SchemaAccessor.from_schema(
            {"a": {"b": 1}},
            resolved_cache_maxsize=8,
        )

        p1 = SchemaPath(accessor) / "a" / "b"
        p2 = SchemaPath(accessor) / "a" / "b"

        with p1.resolve() as r1:
            with p2.resolve() as r2:
                assert r1 is r2

    def test_hash_stable_across_registry_evolution(self):
        # The inner `_path_resolver.resolver` is reassigned when the
        # registry evolves (see CachedPathResolver._sync_registry).
        # The accessor's hash must NOT read through that swappable
        # field; otherwise set/dict membership corrupts mid-life.
        # This is a tripwire: if a future refactor reintroduces a
        # derived field (e.g. base_uri via the resolver) into
        # __hash__, this test fails.

        accessor = SchemaAccessor.from_schema({"a": 1})

        h_before = hash(accessor)
        bucket = {accessor}

        # Force a registry swap by handing the path resolver a fresh
        # registry instance. `_sync_registry` will rebind
        # `_path_resolver.resolver`, but `_path_resolver` itself stays
        # the same instance.
        path_resolver = accessor._path_resolver
        retriever = SchemaRetriever(default_handlers, DRAFT202012)
        new_registry: Registry = Registry(retrieve=retriever)  # type: ignore
        new_registry = new_registry.with_resource(
            "", DRAFT202012.create_resource({"a": 1})
        )
        changed = path_resolver._sync_registry(new_registry)

        assert changed, "registry swap precondition not met"
        assert hash(accessor) == h_before
        assert accessor in bucket
