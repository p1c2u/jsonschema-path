from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from typing import cast
from unittest import mock

import pytest
from referencing import Specification
from referencing.exceptions import Unresolvable

from jsonschema_path.accessors import SchemaAccessor
from jsonschema_path.paths import SchemaPath


class TestSchemaPathFromDict:
    def test_no_kwargs(self, assert_sp):
        schema = mock.sentinel.schema

        sp = SchemaPath.from_dict(schema)

        assert_sp(sp, schema)

    def test_separator(self, assert_sp):
        schema = mock.sentinel.schema
        separator = mock.sentinel.separator

        sp = SchemaPath.from_dict(schema, separator=separator)

        assert_sp(sp, schema, separator=separator)

    def test_specification(self, assert_sp):
        schema = mock.sentinel.schema
        specification = mock.Mock(spec=Specification)

        sp = SchemaPath.from_dict(schema, specification=specification)

        assert_sp(sp, schema, specification=specification)

    def test_base_uri(self, assert_sp):
        schema = mock.sentinel.schema
        base_uri = "mock.sentinel.base_uri"

        sp = SchemaPath.from_dict(schema, base_uri=base_uri)

        assert_sp(sp, schema, base_uri=base_uri)

    def test_handlers(self, assert_sp):
        schema = mock.sentinel.schema
        handlers = mock.sentinel.handlers

        sp = SchemaPath.from_dict(schema, handlers=handlers)

        assert_sp(sp, schema, handlers=handlers)

    def test_resolved_cache_maxsize(self):
        sp = SchemaPath.from_dict(
            {"name": "test"},
            resolved_cache_maxsize=3,
        )

        assert isinstance(sp.accessor, SchemaAccessor)
        assert sp.accessor._resolved_cache_maxsize == 3

    def test_spec_url(self, assert_sp):
        schema = mock.sentinel.schema
        spec_url = "mock.sentinel.spec_url"

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_dict(schema, spec_url=spec_url)

        assert_sp(sp, schema, base_uri=spec_url)

    def test_ref_resolver_handlers(self, assert_sp):
        schema = mock.sentinel.schema
        handlers = mock.sentinel.handlers

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_dict(schema, ref_resolver_handlers=handlers)

        assert_sp(sp, schema, handlers=handlers)

    def test_negative_resolved_cache_maxsize_raises(self):
        with pytest.raises(ValueError):
            SchemaPath.from_dict(
                {"type": "integer"},
                resolved_cache_maxsize=-1,
            )


class TestSchemaPathFromFile:
    def test_no_kwargs(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = cast(Any, schema_file_path.open())

        sp = SchemaPath.from_file(schema_file_obj)  # type: ignore[arg-type]

        assert_sp(sp, schema)

    def test_base_uri(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = cast(Any, schema_file_path.open())
        base_uri = "mock.sentinel.base_uri"

        sp = SchemaPath.from_file(  # type: ignore[arg-type]
            schema_file_obj,
            base_uri=base_uri,
        )

        assert_sp(sp, schema, base_uri=base_uri)

    def test_spec_url(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = cast(Any, schema_file_path.open())
        spec_url = "mock.sentinel.spec_url"

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_file(  # type: ignore[arg-type]
                schema_file_obj,
                spec_url=spec_url,
            )

        assert_sp(sp, schema, base_uri=spec_url)

    def test_resolved_cache_maxsize(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = cast(Any, schema_file_path.open())

        sp = SchemaPath.from_file(
            schema_file_obj,  # type: ignore[arg-type]
            resolved_cache_maxsize=3,
        )

        assert isinstance(sp.accessor, SchemaAccessor)
        assert sp.accessor._resolved_cache_maxsize == 3

    def test_negative_resolved_cache_maxsize_raises(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = cast(Any, schema_file_path.open())

        with pytest.raises(ValueError):
            SchemaPath.from_file(
                schema_file_obj,  # type: ignore[arg-type]
                resolved_cache_maxsize=-1,
            )

    @pytest.mark.parametrize(
        ("yaml_data", "expected"),
        [
            ("maximum: 1e2", 100.0),
            ("maximum: .1e2", 10.0),
            ("maximum: 1.e2", 100.0),
        ],
    )
    def test_parses_scientific_notation_as_float(self, yaml_data, expected):
        sp = SchemaPath.from_file(StringIO(yaml_data))

        assert (sp // "maximum").read_value() == expected
        assert type((sp // "maximum").read_value()) is float


class TestSchemaPathFromPath:
    def test_file_no_exist(self, create_file):
        schema_file_path_str = "/invalid/file"
        schema_file_path = Path(schema_file_path_str)

        with pytest.raises(OSError):
            SchemaPath.from_path(schema_file_path)

    def test_no_kwargs(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_uri = schema_file_path.as_uri()

        sp = SchemaPath.from_path(schema_file_path)

        assert_sp(sp, schema, base_uri=schema_file_uri)

    def test_resolved_cache_maxsize(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)

        sp = SchemaPath.from_path(
            schema_file_path,
            resolved_cache_maxsize=3,
        )

        assert isinstance(sp.accessor, SchemaAccessor)
        assert sp.accessor._resolved_cache_maxsize == 3

    def test_negative_resolved_cache_maxsize_raises(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)

        with pytest.raises(ValueError):
            SchemaPath.from_path(
                schema_file_path,
                resolved_cache_maxsize=-1,
            )


class TestSchemaPathFromFilePath:
    def test_no_kwargs(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_uri = Path(schema_file_path_str).as_uri()

        sp = SchemaPath.from_file_path(schema_file_path_str)

        assert_sp(sp, schema, base_uri=schema_file_uri)

    def test_resolved_cache_maxsize(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)

        sp = SchemaPath.from_file_path(
            schema_file_path_str,
            resolved_cache_maxsize=3,
        )

        assert isinstance(sp.accessor, SchemaAccessor)
        assert sp.accessor._resolved_cache_maxsize == 3

    def test_negative_resolved_cache_maxsize_raises(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)

        with pytest.raises(ValueError):
            SchemaPath.from_file_path(
                schema_file_path_str,
                resolved_cache_maxsize=-1,
            )

    def test_parses_scientific_notation_as_float(self):
        with NamedTemporaryFile("w", suffix=".yaml", delete=False) as tf:
            tf.write("maximum: 1e2")
            schema_file_path_str = tf.name

        try:
            sp = SchemaPath.from_file_path(schema_file_path_str)

            assert (sp // "maximum").read_value() == 100.0
            assert type((sp // "maximum").read_value()) is float
        finally:
            Path(schema_file_path_str).unlink()


class TestSchemaPathGetkey:
    def test_returns_nested_value(self, create_file):
        schema = {"a": {"b": 1}}
        schema_file_path_str = create_file(schema)
        sp = SchemaPath.from_file_path(schema_file_path_str)

        value = (sp // "a").read_value()
        assert value == {"b": 1}

    def test_returns_value(self, create_file):
        schema = {"a": {"b": 1}}
        schema_file_path_str = create_file(schema)
        sp = SchemaPath.from_file_path(schema_file_path_str) // "a"

        value = sp.get("b")
        assert value == 1


class TestSchemaPathReadStr:
    def test_returns_string_value(self):
        sp = SchemaPath.from_dict({"name": "test"}) // "name"

        assert sp.read_str() == "test"

    def test_missing_key_raises(self):
        sp = SchemaPath.from_dict({})

        with pytest.raises(KeyError):
            (sp // "missing").read_str()

    def test_missing_key_returns_default(self):
        sp = SchemaPath.from_dict({})
        default = mock.sentinel.default

        assert (sp / "missing").read_str(default=default) is default

    def test_non_string_raises(self):
        sp = SchemaPath.from_dict({"name": 1}) // "name"

        with pytest.raises(TypeError):
            sp.read_str()


class TestSchemaPathReadBool:
    def test_returns_bool_value(self):
        sp = SchemaPath.from_dict({"enabled": True}) // "enabled"

        assert sp.read_bool() is True

    def test_missing_key_raises(self):
        sp = SchemaPath.from_dict({})

        with pytest.raises(KeyError):
            (sp // "missing").read_bool()

    def test_missing_key_returns_default(self):
        sp = SchemaPath.from_dict({})
        default = mock.sentinel.default

        assert (sp / "missing").read_bool(default=default) is default

    def test_non_bool_raises_without_default(self):
        sp = SchemaPath.from_dict({"enabled": "yes"}) // "enabled"

        with pytest.raises(TypeError):
            sp.read_bool()

    def test_non_bool_returns_default(self):
        sp = SchemaPath.from_dict({"enabled": "yes"}) // "enabled"
        default = mock.sentinel.default

        assert sp.read_bool(default=default) is default


class TestSchemaPathReadStrOrList:
    def test_returns_string_value(self):
        sp = SchemaPath.from_dict({"value": "test"}) // "value"

        assert sp.read_str_or_list() == "test"

    def test_returns_list_value(self):
        sp = SchemaPath.from_dict({"value": ["a", "b"]}) // "value"

        assert sp.read_str_or_list() == ["a", "b"]

    def test_missing_key_raises(self):
        sp = SchemaPath.from_dict({})

        with pytest.raises(KeyError):
            (sp // "missing").read_str_or_list()

    def test_missing_key_returns_default(self):
        sp = SchemaPath.from_dict({})
        default = mock.sentinel.default

        assert (sp / "missing").read_str_or_list(default=default) is default

    def test_non_string_or_list_raises(self):
        sp = SchemaPath.from_dict({"value": 1}) // "value"

        with pytest.raises(TypeError):
            sp.read_str_or_list()


class TestSchemaPathHelpers:
    def test_base_uri(self):
        base_uri = "https://example.com/openapi.json"
        sp = SchemaPath.from_dict({"a": {"b": 1}}, base_uri=base_uri)

        assert sp.base_uri == base_uri

    def test_base_uri_for_child_path(self):
        base_uri = "https://example.com/openapi.json"
        sp = SchemaPath.from_dict({"a": {"b": 1}}, base_uri=base_uri)
        child = sp / "a" / "b"

        assert child.base_uri == base_uri

    def test_as_uri(self):
        sp = SchemaPath.from_dict({"a": {"b": 1}}) // "a" // "b"

        assert sp.as_uri() == "#/a#b"

    def test_str_keys(self):
        sp = SchemaPath.from_dict({"a": 1, "b": 2})

        assert set(sp.str_keys()) == {"a", "b"}

    def test_str_items(self):
        sp = SchemaPath.from_dict({"a": 1})
        key, child = list(sp.str_items())[0]

        assert key == "a"
        assert isinstance(child, SchemaPath)
        assert child.read_value() == 1


class TestSchemaPathParseArgs:
    def test_flattens_schema_path(self):
        base = SchemaPath.from_dict({"a": {"b": 1}}) // "a"

        parsed = SchemaPath._parse_args([base, "b"])

        assert parsed == ("a", "b")

    def test_accepts_bytes(self):
        parsed = SchemaPath._parse_args([b"a"])

        assert parsed == ("a",)

    def test_accepts_pathlike(self):
        parsed = SchemaPath._parse_args([Path("a")])

        assert parsed == ("a",)

    def test_skips_empty_and_dot(self):
        parsed = SchemaPath._parse_args(["", ".", "a#.#b##"])

        assert parsed == ("a", "b")

    def test_raises_on_unsupported_type(self):
        with pytest.raises(TypeError):
            SchemaPath._parse_args([object()])


class TestSchemaPathCanonical:
    def test_on_plain_schema(self):
        path = SchemaPath.from_dict({"type": "object"})

        assert path.canonical() is path

    def test_single_ref(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#/$defs/A"},
                "$defs": {"A": {"type": "string"}},
            }
        )

        assert (path / "x").canonical().parts == ("$defs", "A")

    def test_chained_ref(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#/$defs/A"},
                "$defs": {
                    "A": {"$ref": "#/$defs/B"},
                    "B": {"$ref": "#/$defs/C"},
                    "C": {"type": "string"},
                },
            }
        )

        assert (path / "x").canonical().parts == ("$defs", "C")

    def test_recursive_ref(self):
        path = SchemaPath.from_dict({"node": {"$ref": "#/node"}}) / "node"

        canonical = path.canonical()

        assert canonical == path
        assert path.canonical() is canonical
        assert canonical.canonical() == canonical

    def test_cross_path_collapse(self):
        path = SchemaPath.from_dict(
            {
                "properties": {"name": {"$ref": "#/$defs/Name"}},
                "$defs": {
                    "Alias": {"$ref": "#/$defs/Name"},
                    "Name": {"type": "string"},
                },
            }
        )

        via_property = path / "properties" / "name"
        via_alias = path / "$defs" / "Alias"

        assert via_property.canonical() == via_alias.canonical()
        assert via_property.canonical().parts == ("$defs", "Name")

    def test_reaches_same_node(self):
        schema = {
            "x": {"$ref": "#/$defs/A"},
            "$defs": {"A": {"type": "string"}},
        }
        path = SchemaPath.from_dict(schema) / "x"

        assert path.canonical().read_value() is path.read_value()

    def test_idempotent(self):
        path = (
            SchemaPath.from_dict(
                {
                    "x": {"$ref": "#/$defs/A"},
                    "$defs": {"A": {"type": "string"}},
                }
            )
            / "x"
        )

        canonical = path.canonical()

        assert canonical.canonical() is canonical

    def test_boolean_schema(self):
        path = (
            SchemaPath.from_dict(
                {
                    "x": {"$ref": "#/$defs/Flag"},
                    "$defs": {"Flag": True},
                }
            )
            / "x"
        )

        assert path.canonical().read_value() is True

    def test_sibling_keys_follow_ref(self):
        path = (
            SchemaPath.from_dict(
                {
                    "x": {
                        "$ref": "#/$defs/A",
                        "description": "ignored by implicit dereferencing",
                    },
                    "$defs": {"A": {"type": "string"}},
                }
            )
            / "x"
        )

        assert path.canonical().parts == ("$defs", "A")
        assert path.canonical().read_value() is path.read_value()

    def test_canonical_parts_hashable_and_equal(self):
        path = SchemaPath.from_dict(
            {
                "properties": {"name": {"$ref": "#/$defs/Name"}},
                "$defs": {
                    "Alias": {"$ref": "#/$defs/Name"},
                    "Name": {"type": "string"},
                },
            }
        )

        via_property = path / "properties" / "name"
        via_alias = path / "$defs" / "Alias"

        hash((via_property.canonical().parts,))
        assert via_property.canonical().parts == via_alias.canonical().parts

    def test_missing_ref_target_raises(self):
        path = SchemaPath.from_dict({"x": {"$ref": "#/$defs/Missing"}}) / "x"

        with pytest.raises(Unresolvable):
            path.canonical()

    def test_array_pointer_uses_integer_path_part(self):
        path = (
            SchemaPath.from_dict(
                {
                    "x": {"$ref": "#/items/0"},
                    "items": [{"type": "string"}],
                }
            )
            / "x"
        )

        assert path.canonical().parts == ("items", 0)
        assert path.canonical().read_value() == {"type": "string"}

    def test_empty_key_pointer_is_not_root(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#/"},
                "": {"type": "null"},
            }
        )

        assert (path / "x").canonical().parts == ("",)
        assert (path / "x").canonical().read_value() is (
            path / "x"
        ).read_value()

    def test_percent_decodes_pointer_fragment(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#/a%20b"},
                "a b": {"type": "string"},
            }
        )

        assert (path / "x").canonical().parts == ("a b",)
        assert (path / "x").canonical().read_value() is (
            path / "x"
        ).read_value()

    def test_decodes_escaped_pointer_tokens(self):
        path = SchemaPath.from_dict(
            {
                "slash": {"$ref": "#/a~1b"},
                "tilde": {"$ref": "#/c~0d"},
                "a/b": {"type": "string"},
                "c~d": {"type": "integer"},
            }
        )

        assert (path / "slash").canonical().parts == ("a/b",)
        assert (path / "tilde").canonical().parts == ("c~d",)

    def test_anchor_fragment(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#target"},
                "$defs": {
                    "Target": {
                        "$anchor": "target",
                        "type": "string",
                    }
                },
            }
        )

        assert (path / "x").canonical().parts == ("$defs", "Target")
        assert (path / "x").canonical().read_value() is (
            path / "x"
        ).read_value()

    def test_dynamic_anchor_fragment(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#target"},
                "$defs": {
                    "Target": {
                        "$dynamicAnchor": "target",
                        "type": "string",
                    }
                },
            }
        )

        assert (path / "x").canonical().parts == ("$defs", "Target")

    def test_anchor_scan_skips_embedded_resources(self):
        path = SchemaPath.from_dict(
            {
                "x": {"$ref": "#target"},
                "$defs": {
                    "OtherResource": {
                        "$id": "other",
                        "$anchor": "target",
                        "type": "number",
                    },
                    "Target": {
                        "$anchor": "target",
                        "type": "string",
                    },
                },
            }
        )

        assert (path / "x").canonical().parts == ("$defs", "Target")

    def test_missing_anchor_raises(self):
        """A $ref with an anchor fragment that does not exist in the document
        must raise Unresolvable rather than silently resolving to the document
        root."""
        path = (
            SchemaPath.from_dict({"x": {"$ref": "#nonExistentAnchor"}}) / "x"
        )

        with pytest.raises(Unresolvable):
            path.canonical()
