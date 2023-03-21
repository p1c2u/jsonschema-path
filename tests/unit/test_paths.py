from pathlib import Path
from unittest import mock

import pytest
from pathable.paths import SEPARATOR
from referencing import Registry
from referencing import Specification
from referencing._core import Resolver
from referencing.jsonschema import DRAFT202012

from jsonschema_spec.accessors import ResolverAccessor
from jsonschema_spec.handlers import default_handlers
from jsonschema_spec.paths import SPEC_SEPARATOR
from jsonschema_spec.paths import SchemaPath
from jsonschema_spec.paths import Spec
from jsonschema_spec.retrievers import HandlersRetriever


class BaseTestSchemaPath:
    def assert_sp(
        self,
        sp,
        schema,
        separator=SPEC_SEPARATOR,
        base_uri="",
        handlers=default_handlers,
        specification=DRAFT202012,
    ):
        assert sp.separator == separator
        assert sp.parts == []
        accessor = sp.accessor
        assert type(accessor) is ResolverAccessor
        assert accessor.lookup == schema
        resolver = accessor.resolver
        assert type(resolver) is Resolver
        assert resolver._base_uri == base_uri
        registry = resolver._registry
        assert type(registry) is Registry
        assert type(registry._retrieve) is HandlersRetriever
        assert registry._retrieve.handlers == handlers
        assert registry._retrieve.specification == specification


class TestSpec(BaseTestSchemaPath):
    def test_no_kwargs(self):
        schema = mock.sentinel.schema
        retriever = HandlersRetriever(default_handlers, DRAFT202012)
        registry = Registry(retrieve=retriever)
        resolver = Resolver("", registry)
        accessor = ResolverAccessor(schema, resolver)

        with pytest.warns(DeprecationWarning):
            sp = Spec(accessor)

        self.assert_sp(sp, schema, separator=SEPARATOR)


class TestSchemaPathFromDict(BaseTestSchemaPath):
    def test_no_kwargs(self):
        schema = mock.sentinel.schema

        sp = SchemaPath.from_dict(schema)

        self.assert_sp(sp, schema)

    def test_separator(self):
        schema = mock.sentinel.schema
        separator = mock.sentinel.separator

        sp = SchemaPath.from_dict(schema, separator=separator)

        self.assert_sp(sp, schema, separator=separator)

    def test_specification(self):
        schema = mock.sentinel.schema
        specification = mock.Mock(spec=Specification)

        sp = SchemaPath.from_dict(schema, specification=specification)

        self.assert_sp(sp, schema, specification=specification)

    def test_base_uri(self):
        schema = mock.sentinel.schema
        base_uri = "mock.sentinel.base_uri"

        sp = SchemaPath.from_dict(schema, base_uri=base_uri)

        self.assert_sp(sp, schema, base_uri=base_uri)

    def test_handlers(self):
        schema = mock.sentinel.schema
        handlers = mock.sentinel.handlers

        sp = SchemaPath.from_dict(schema, handlers=handlers)

        self.assert_sp(sp, schema, handlers=handlers)

    def test_spec_url(self):
        schema = mock.sentinel.schema
        spec_url = "mock.sentinel.spec_url"

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_dict(schema, spec_url=spec_url)

        self.assert_sp(sp, schema, base_uri=spec_url)

    def test_ref_resolver_handlers(self):
        schema = mock.sentinel.schema
        handlers = mock.sentinel.handlers

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_dict(schema, ref_resolver_handlers=handlers)

        self.assert_sp(sp, schema, handlers=handlers)


class TestSchemaPathFromFile(BaseTestSchemaPath):
    def test_no_kwargs(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()

        sp = SchemaPath.from_file(schema_file_obj)

        self.assert_sp(sp, schema)

    def test_base_uri(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()
        base_uri = "mock.sentinel.base_uri"

        sp = SchemaPath.from_file(schema_file_obj, base_uri=base_uri)

        self.assert_sp(sp, schema, base_uri=base_uri)

    def test_base_uri(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_obj = schema_file_path.open()
        spec_url = "mock.sentinel.spec_url"

        with pytest.warns(DeprecationWarning):
            sp = SchemaPath.from_file(schema_file_obj, spec_url=spec_url)

        self.assert_sp(sp, schema, base_uri=spec_url)


class TestSchemaPathFromPath(BaseTestSchemaPath):
    def test_file_no_exist(self, create_file):
        schema_file_path_str = "/invalid/file"
        schema_file_path = Path(schema_file_path_str)
        schema_file_uri = schema_file_path.as_uri()

        with pytest.raises(OSError):
            SchemaPath.from_path(schema_file_path)

    def test_no_kwargs(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_path = Path(schema_file_path_str)
        schema_file_uri = schema_file_path.as_uri()

        sp = SchemaPath.from_path(schema_file_path)

        self.assert_sp(sp, schema, base_uri=schema_file_uri)


class TestSchemaPathFromFilePath(BaseTestSchemaPath):
    def test_no_kwargs(self, create_file):
        schema = {"type": "integer"}
        schema_file_path_str = create_file(schema)
        schema_file_uri = Path(schema_file_path_str).as_uri()

        sp = SchemaPath.from_file_path(schema_file_path_str)

        self.assert_sp(sp, schema, base_uri=schema_file_uri)
