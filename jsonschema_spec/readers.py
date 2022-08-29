"""JSONSchema spec readers module."""
from os import path
from pathlib import Path
from typing import Any
from typing import Hashable
from typing import Mapping
from typing import Tuple

from jsonschema_spec.handlers import all_urls_handler
from jsonschema_spec.handlers import file_handler
from jsonschema_spec.handlers.protocols import SupportsRead


class BaseReader:
    def read(self) -> Tuple[Mapping[Hashable, Any], str]:
        raise NotImplementedError


class FileReader(BaseReader):
    def __init__(self, fileobj: SupportsRead):
        self.fileobj = fileobj

    def read(self) -> Tuple[Mapping[Hashable, Any], str]:
        return file_handler(self.fileobj), ""


class FilePathReader(BaseReader):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> Tuple[Mapping[Hashable, Any], str]:
        if not path.isfile(self.file_path):
            raise OSError(f"No such file: {self.file_path}")

        filename = path.abspath(self.file_path)
        uri = Path(filename).as_uri()
        return all_urls_handler(uri), uri
