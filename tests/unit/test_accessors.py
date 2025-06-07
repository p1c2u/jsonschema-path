from unittest.mock import Mock

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
