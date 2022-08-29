"""JSONSchema spec handlers requests module."""
from contextlib import closing
from io import StringIO
from typing import Any

import requests

from jsonschema_spec.handlers.file import BaseFilePathHandler


class UrlRequestsHandler(BaseFilePathHandler):
    """URL (requests) scheme handler."""

    def __init__(self, *allowed_schemes: str, **options: Any):
        self.timeout = options.pop("timeout", 10)
        super().__init__(**options)
        self.allowed_schemes = list(allowed_schemes)

    def _open(self, url: str) -> Any:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()

        data = StringIO(response.text)
        with closing(data) as fh:
            return super().__call__(fh)
