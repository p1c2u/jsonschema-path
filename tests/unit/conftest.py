import pytest
from referencing import Registry
from referencing._core import Resolver
from referencing.jsonschema import DRAFT202012

from jsonschema_path.accessors import SchemaAccessor
from jsonschema_path.handlers import default_handlers
from jsonschema_path.paths import SPEC_SEPARATOR
from jsonschema_path.paths import SchemaPath
from jsonschema_path.retrievers import SchemaRetriever


@pytest.fixture
def assert_ra():
    def func(
        sa,
        schema,
        base_uri="",
        handlers=default_handlers,
        specification=DRAFT202012,
    ):
        assert sa.lookup == schema
        resolver = sa.resolver
        assert type(resolver) is Resolver
        assert resolver._base_uri == base_uri
        registry = resolver._registry
        assert type(registry) is Registry
        assert type(registry._retrieve) is SchemaRetriever
        assert registry._retrieve.handlers == handlers
        assert registry._retrieve.specification == specification

    return func


@pytest.fixture
def assert_sa():
    def func(
        sa,
        schema,
        base_uri="",
        handlers=default_handlers,
        specification=DRAFT202012,
    ):
        assert type(sa) is SchemaAccessor
        assert sa.lookup == schema
        resolver = sa.resolver
        assert type(resolver) is Resolver
        assert resolver._base_uri == base_uri
        registry = resolver._registry
        assert type(registry) is Registry
        assert type(registry._retrieve) is SchemaRetriever
        assert registry._retrieve.handlers == handlers
        assert registry._retrieve.specification == specification

    return func


@pytest.fixture
def assert_sp(assert_sa):
    def func(
        sp,
        schema,
        separator=SPEC_SEPARATOR,
        base_uri="",
        handlers=default_handlers,
        specification=DRAFT202012,
    ):
        assert sp.separator == separator
        assert sp.parts == []
        assert_sa(
            sp.accessor,
            schema,
            base_uri=base_uri,
            handlers=handlers,
            specification=specification,
        )

    return func
