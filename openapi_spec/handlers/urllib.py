"""OpenAPI spec handlers requests module."""
from typing import Any
from urllib.request import urlopen

from openapi_spec.handlers.file import BaseFilePathHandler


class UrllibHandler(BaseFilePathHandler):
    """OpenAPI spec URL (urllib) scheme handler."""

    def __init__(self, *allowed_schemes: str, **options: Any):
        self.timeout = options.pop("timeout", 10)
        super().__init__(**options)
        self.allowed_schemes = list(allowed_schemes)

    def _open(self, url: str) -> Any:
        with urlopen(url, timeout=self.timeout) as fh:
            return super().__call__(fh)
