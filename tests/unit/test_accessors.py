from unittest.mock import Mock

from jsonschema_spec.accessors import SchemaAccessor


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

        with accessor.open(["one", "value"]) as opened:
            assert opened == "tested"
        with accessor.open(["two", "value"]) as opened:
            assert opened == "tested"

        retrieve.assert_called_once_with("x://testref")
