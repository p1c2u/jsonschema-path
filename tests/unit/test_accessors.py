from unittest.mock import Mock

import pytest

from jsonschema_path.accessors import SchemaAccessor


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
        accessor = SchemaAccessor.from_schema({"a": {"b": 1}})
        initial_resolver = accessor.resolver

        assert accessor.read(["a", "b"]) == 1
        assert accessor.resolver is initial_resolver

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
        initial_resolver = accessor.resolver

        assert accessor.read(["one", "value"]) == "tested"
        evolved_resolver = accessor.resolver
        assert evolved_resolver is not initial_resolver

        assert accessor.read(["one", "value"]) == "tested"
        assert accessor.resolver is evolved_resolver
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

    def test_registry_evolution_invalidates_previous_generation(self):
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

        second_two = accessor.get_resolved(["two", "value"])
        assert second_two.contents == 2

        second_one = accessor.get_resolved(["one", "value"])
        assert second_one.contents == 1
        assert second_one is not first_one

        assert retrieve.call_count == 2


class TestSchemaAccessorResolveNode:
    def test_deep_local_ref_chain_resolves(self):
        depth = 1200
        defs = {}

        for i in range(depth):
            if i == depth - 1:
                defs[f"N{i}"] = {"value": "ok"}
            else:
                defs[f"N{i}"] = {"$ref": f"#/$defs/N{i + 1}"}

        accessor = SchemaAccessor.from_schema(
            {
                "$defs": defs,
                "root": {"$ref": "#/$defs/N0"},
            }
        )

        assert accessor.read(["root", "value"]) == "ok"

    def test_cyclic_local_ref_chain_raises_value_error(self):
        accessor = SchemaAccessor.from_schema(
            {
                "$defs": {
                    "A": {"$ref": "#/$defs/B"},
                    "B": {"$ref": "#/$defs/A"},
                },
                "root": {"$ref": "#/$defs/A"},
            }
        )

        with pytest.raises(ValueError, match=r"Cyclic \$ref detected"):
            accessor.read(["root"])
