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
