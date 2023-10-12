from pathlib import Path

import pytest

from jsonschema_path.handlers.file import FilePathHandler


class TestFilePathHandler:
    def test_invalid_scheme(self):
        uri = "invalid:///"
        handler = FilePathHandler()

        with pytest.raises(ValueError):
            handler(uri)

    def test_valid(self, create_file):
        test_file = create_file({})
        test_file_uri = Path(test_file).as_uri()
        handler = FilePathHandler()

        result = handler(test_file_uri)
