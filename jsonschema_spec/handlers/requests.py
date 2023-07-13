"""JSONSchema spec handlers requests module."""
from contextlib import closing
from io import StringIO
from typing import ContextManager
from typing import Optional

import requests

from jsonschema_spec.handlers.file import BaseFilePathHandler
from jsonschema_spec.handlers.file import FileHandler
from jsonschema_spec.handlers.protocols import SupportsRead


class UrlRequestsHandler(BaseFilePathHandler):
    """URL (requests) scheme handler."""

    def __init__(
        self,
        *allowed_schemes: str,
        file_handler: Optional[FileHandler] = None,
        timeout: int = 10
    ):
        super().__init__(*allowed_schemes, file_handler=file_handler)
        self.timeout = timeout

    def _open(self, uri: str) -> ContextManager[SupportsRead]:
        response = requests.get(uri, timeout=self.timeout)
        response.raise_for_status()

        data = StringIO(response.text)
        return closing(data)
