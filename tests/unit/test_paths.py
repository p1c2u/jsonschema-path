from pathlib import Path
from unittest import mock

import pytest
from referencing import Specification

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


class TestSchemaPathFromFile:
    def test_no_kwargs(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()

        sp = SchemaPath.from_file(schema_file_obj)

        assert_sp(sp, schema)

    def test_base_uri(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()
        base_uri = "mock.sentinel.base_uri"

        sp = SchemaPath.from_file(schema_file_obj, base_uri=base_uri)

        assert_sp(sp, schema, base_uri=base_uri)

    def test_spec_url(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()
        spec_url = "mock.sentinel.spec_url"

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_file(schema_file_obj, spec_url=spec_url)

        assert_sp(sp, schema, base_uri=spec_url)


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


class TestSchemaPathFromFilePath:
    def test_no_kwargs(self, create_file, assert_sp):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_uri = Path(schema_file_path_str).as_uri()

        sp = SchemaPath.from_file_path(schema_file_path_str)

        assert_sp(sp, schema, base_uri=schema_file_uri)


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


class TestSchemaPathHelpers:
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
