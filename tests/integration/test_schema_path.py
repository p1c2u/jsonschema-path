import gc
import weakref
from io import BytesIO
from json import dumps
from unittest import mock

import responses

from jsonschema_path import SchemaPath


class TestSchemaPathFromDict:
    def test_dict(self):
        schema = {
            "properties": {
                "info": {
                    "type": "object",
                    "properties": {},
                },
            },
        }
        path = SchemaPath.from_dict(schema)

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path


class TestSchemaPathFromFilePath:
    def test_file_path(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/petstore-separate/spec/openapi.yaml"
        )
        path = SchemaPath.from_file_path(fp)

        assert "paths" in path

    def test_file_path_relative(self):
        fp = "tests/integration/data/v3.0/petstore-separate/spec/openapi.yaml"
        path = SchemaPath.from_file_path(fp)

        assert "paths" in path


class TestSchemaPathFromFile:
    def test_ref_recursive(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/parent-reference/openapi.yaml"
        )
        base_uri = "file://" + fp
        with open(fp) as f:
            path = SchemaPath.from_file(f, base_uri=base_uri)

        assert "paths" in path


class TestSchemaPathExists:
    def test_existing(self):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
        }

        path = SchemaPath.from_dict(schema, "properties")

        assert path.exists() is True

    def test_non_existing(self):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
        }

        path = SchemaPath.from_dict(schema, "invalid")

        assert path.exists() is False


class TestSchemaPathAsUri:
    def test_root(self):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
        }

        path = SchemaPath.from_dict(schema)

        assert path.as_uri() == "#/"

    def test_simple(self):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
        }

        path = SchemaPath.from_dict(schema, "properties", "info")

        assert path.as_uri() == "#/properties#info"

    def test_non_existing(self):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
        }

        path = SchemaPath.from_dict(schema, "properties", "info", "properties")

        assert path.as_uri() == "#/properties#info#properties"


class TestSchemaPathGetitem:
    def test_getitem_resolves_ref(self, defs):
        """Thsi tests verifies that path["key"] on a $ref node resolves correctly to the referenced node, and that the returned node is cached for subsequent access."""
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
            "$defs": defs,
        }
        path = SchemaPath.from_dict(schema)

        info_ref_path = path["properties"]["info"]

        child_path = info_ref_path["properties"]
        with child_path.open() as contents:
            assert contents == {
                "version": {
                    "type": "string",
                    "default": "1.0",
                },
            }

    def test_getitem_keys_consistent_with_ref(self, defs):
        """This tests verifies __getitem__ and keys() return consistent results for a $ref node, and that the keys are consistent with the referenced node."""
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
            "$defs": defs,
        }
        path = SchemaPath.from_dict(schema)

        info_ref_path = path["properties"]["info"]

        with info_ref_path.open() as contents:
            keys_via_open = list(contents.keys())
        keys_via_keys = list(info_ref_path.keys())

        assert keys_via_open == keys_via_keys == ["properties"]

    def test_getitem_updates_resolver_state(self, defs):
        """Test that multiple __getitem__ calls properly update resolver state."""
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
            "$defs": defs,
        }
        path = SchemaPath.from_dict(schema)

        info_path = path["properties"]["info"]
        with info_path.open() as contents:
            assert contents == {
                "properties": {
                    "version": {
                        "type": "string",
                        "default": "1.0",
                    },
                },
            }


class TestSchemaPathOpen:
    def test_dict(self, defs):
        schema = {
            "properties": {
                "info": {
                    "$ref": "#/$defs/Info",
                },
            },
            "$defs": defs,
        }
        path = SchemaPath.from_dict(schema)

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path

        version_path = info_path / "properties" / "version"

        expected_contents = {"type": "string", "default": "1.0"}
        with version_path.resolve() as resolved, version_path.open() as contents:
            assert resolved.contents == expected_contents
            assert contents == expected_contents
            assert id(resolved.contents) == id(contents)

    def test_file(self, defs, create_file):
        defs_file = create_file(defs)
        schema = {
            "properties": {
                "info": {
                    "$ref": f"{defs_file}#/Info",
                },
            },
        }
        path = SchemaPath.from_dict(schema, base_uri="file:///")

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path

        version_path = info_path / "properties" / "version"

        expected_contents = {"type": "string", "default": "1.0"}
        with version_path.resolve() as resolved, version_path.open() as contents:
            assert resolved.contents == expected_contents
            assert contents == expected_contents
            assert id(resolved.contents) == id(contents)

    @responses.activate
    def test_remote(self, defs):
        schema = {
            "properties": {
                "info": {
                    "$ref": "https://example.com/defs.json#/Info",
                },
            },
        }
        responses.add(
            responses.GET,
            "https://example.com/defs.json",
            json=defs,
        )
        path = SchemaPath.from_dict(schema)

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path

        version_path = info_path / "properties" / "version"

        expected_contents = {"type": "string", "default": "1.0"}
        with version_path.resolve() as resolved, version_path.open() as contents:
            assert resolved.contents == expected_contents
            assert contents == expected_contents
            assert id(resolved.contents) == id(contents)

    @responses.activate
    def test_remote_fallback_requests(self, defs):
        schema = {
            "properties": {
                "info": {
                    "$ref": "https://example.com/defs.json#/Info",
                },
            },
        }
        responses.add(
            responses.GET,
            "https://example.com/defs.json",
            json=defs,
        )
        path = SchemaPath.from_dict(schema, handlers={})

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path

        version_path = info_path / "properties" / "version"

        expected_contents = {"type": "string", "default": "1.0"}
        with version_path.resolve() as resolved, version_path.open() as contents:
            assert resolved.contents == expected_contents
            assert contents == expected_contents
            assert id(resolved.contents) == id(contents)

    @mock.patch("jsonschema_path.retrievers.USE_REQUESTS", False)
    @mock.patch("jsonschema_path.retrievers.urlopen")
    def test_remote_fallback_urllib(self, mock_urlopen, defs):
        schema = {
            "properties": {
                "info": {
                    "$ref": "https://example.com/defs.json#/Info",
                },
            },
        }
        data_bytes = dumps(defs).encode()
        mock_urlopen.side_effect = lambda m: BytesIO(data_bytes)
        path = SchemaPath.from_dict(schema, handlers={})

        assert "properties" in path

        info_path = path / "properties" / "info"

        assert "properties" in info_path

        version_path = info_path / "properties" / "version"

        expected_contents = {"type": "string", "default": "1.0"}
        with version_path.resolve() as resolved, version_path.open() as contents:
            assert resolved.contents == expected_contents
            assert contents == expected_contents
            assert id(resolved.contents) == id(contents)

    def test_file_ref(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/petstore-separate/spec/openapi.yaml"
        )
        path = SchemaPath.from_file_path(fp)

        paths = path / "paths"

        for _, path in paths.items():
            properties = (
                path
                / "get#responses#default#content#application/json#schema#properties"
            )
            with properties.open() as properties_dict:
                assert properties_dict == {
                    "code": {
                        "format": "int32",
                        "type": "integer",
                    },
                    "message": {
                        "type": "string",
                    },
                }

    def test_double_ref(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/petstore-separate/spec/openapi.yaml"
        )
        path = SchemaPath.from_file_path(fp)

        paths_path = path / "paths"

        for _, path_path in paths_path.items():
            properties_path = (
                path_path
                / "get#responses#200#content#application/json#schema#items#properties"
            )
            with properties_path.open() as contents:
                assert contents == {
                    "id": {
                        "type": "integer",
                        "format": "int64",
                    },
                    "name": {
                        "type": "string",
                    },
                    "tag": {
                        "type": "string",
                    },
                }

    def test_ref_recursive(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/parent-reference/openapi.yaml"
        )
        base_uri = "file://" + fp
        with open(fp) as f:
            path = SchemaPath.from_file(f, base_uri=base_uri)

        property_schema_path = path._make_child(
            [
                "paths",
                "/pets",
                "get",
                "parameters",
                0,
                "schema",
            ]
        )
        expected_contents = {"type": "boolean"}
        with property_schema_path.resolve() as resolved:
            assert resolved.contents == expected_contents
        with property_schema_path.open() as contents:
            assert contents == expected_contents


class TestSchemaPathCanonical:
    def test_external_ref(self, create_file):
        target = {
            "Thing": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            }
        }
        target_file = create_file(target)
        path = SchemaPath.from_dict(
            {
                "properties": {
                    "a": {"$ref": f"{target_file}#/Thing"},
                    "b": {"$ref": f"{target_file}#/Thing"},
                }
            },
            base_uri="file:///",
        )

        first = (path / "properties" / "a").canonical()
        second = (path / "properties" / "b").canonical()

        assert first.accessor is not path.accessor
        assert first.accessor is second.accessor
        assert first == second
        assert first.parts == ("Thing",)
        assert first.read_value() == target["Thing"]

    def test_direct_and_indirect_refs_share_accessor(self, create_file):
        target = {"Target": {"type": "string"}}
        target_file = create_file(target)
        intermediate_file = create_file(
            {"Thing": {"$ref": f"{target_file}#/Target"}}
        )
        path = SchemaPath.from_dict(
            {
                "direct": {"$ref": f"{target_file}#/Target"},
                "via": {"$ref": f"{intermediate_file}#/Thing"},
            },
            base_uri="file:///",
        )

        direct = (path / "direct").canonical()
        indirect = (path / "via").canonical()

        assert direct == indirect
        assert direct.accessor is indirect.accessor
        assert direct.parts == indirect.parts == ("Target",)

    def test_indirect_and_direct_refs_share_accessor(self, create_file):
        target = {"Target": {"type": "string"}}
        target_file = create_file(target)
        intermediate_file = create_file(
            {"Thing": {"$ref": f"{target_file}#/Target"}}
        )
        path = SchemaPath.from_dict(
            {
                "direct": {"$ref": f"{target_file}#/Target"},
                "via": {"$ref": f"{intermediate_file}#/Thing"},
            },
            base_uri="file:///",
        )

        indirect = (path / "via").canonical()
        direct = (path / "direct").canonical()

        assert direct == indirect
        assert direct.accessor is indirect.accessor
        assert direct.parts == indirect.parts == ("Target",)

    def test_external_anchor_matches_pointer(self, create_file):
        target = {
            "Thing": {
                "$anchor": "thing",
                "type": "string",
            }
        }
        target_file = create_file(target)
        path = SchemaPath.from_dict(
            {
                "anchor": {"$ref": f"{target_file}#thing"},
                "pointer": {"$ref": f"{target_file}#/Thing"},
            },
            base_uri="file:///",
        )

        anchor = (path / "anchor").canonical()
        pointer = (path / "pointer").canonical()

        assert anchor == pointer
        assert anchor.accessor is pointer.accessor
        assert anchor.parts == ("Thing",)

    def test_external_boolean_root(self, create_file):
        target_file = create_file(True)
        path = SchemaPath.from_dict(
            {"x": {"$ref": f"{target_file}#"}},
            base_uri="file:///",
        )

        canonical = (path / "x").canonical()

        assert canonical.accessor is not path.accessor
        assert canonical.parts == ()
        assert canonical.read_value() is True

    def test_does_not_keep_source_accessor_alive(self, create_file):
        target_file = create_file({"Thing": {"type": "string"}})
        path = SchemaPath.from_dict(
            {"x": {"$ref": f"{target_file}#/Thing"}},
            base_uri="file:///",
        )
        source_accessor_ref = weakref.ref(path.accessor)

        canonical = (path / "x").canonical()
        del path
        gc.collect()

        assert canonical.read_value() == {"type": "string"}
        assert source_accessor_ref() is None
