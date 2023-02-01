"""JSONSchema spec handlers file module."""
from io import StringIO
from json import dumps
from json import loads
from typing import IO
from typing import Any
from typing import List
from typing import Union
from urllib.parse import urlparse

from yaml import load

from jsonschema_spec.handlers.protocols import SupportsRead
from jsonschema_spec.handlers.utils import uri_to_path
from jsonschema_spec.loaders import JsonschemaSafeLoader


class FileHandler:
    """File-like object handler."""

    def __init__(self, loader: Any = JsonschemaSafeLoader):
        self.loader = loader

    def __call__(self, f: SupportsRead) -> Any:
        data = self._load(f)
        return loads(dumps(data))

    def _load(self, f: SupportsRead) -> Any:
        return load(f, self.loader)


class BaseFilePathHandler(FileHandler):
    """Base file path handler."""

    allowed_schemes: List[str] = NotImplemented

    def __call__(self, uri: Union[SupportsRead, str]) -> Any:
        if isinstance(uri, SupportsRead):
            return super().__call__(uri)

        parsed_url = urlparse(uri)
        if parsed_url.scheme not in self.allowed_schemes:
            raise ValueError("Not allowed scheme")

        return self._open(uri)

    def _open(self, uri: str) -> Any:
        raise NotImplementedError


class FilePathHandler(BaseFilePathHandler):
    """File path handler."""

    allowed_schemes = ["file"]

    def _open(self, uri: str) -> Any:
        filepath = uri_to_path(uri)
        with open(filepath) as fh:
            return super().__call__(fh)
