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
