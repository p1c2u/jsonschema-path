from io import StringIO
from pathlib import Path

import pytest

from jsonschema_path.handlers.file import FileHandler
from jsonschema_path.handlers.file import FilePathHandler


class TestFileHandler:
    @pytest.mark.parametrize(
        ("yaml_data", "expected"),
        [
            ("maximum: 1e2", 100.0),
            ("maximum: 1e+2", 100.0),
            ("maximum: 1e-2", 0.01),
            ("maximum: -1e2", -100.0),
            ("maximum: +1E2", 100.0),
            ("maximum: 1.0e2", 100.0),
            ("maximum: .1e2", 10.0),
            ("maximum: 1.e2", 100.0),
        ],
    )
    def test_scientific_notation_parses_as_float(self, yaml_data, expected):
        result = FileHandler()(StringIO(yaml_data))

        assert result["maximum"] == expected
        assert type(result["maximum"]) is float

    def test_quoted_scientific_notation_remains_string(self):
        result = FileHandler()(StringIO('maximum: "1e2"'))

        assert result["maximum"] == "1e2"
        assert type(result["maximum"]) is str

    def test_timestamp_remains_string(self):
        result = FileHandler()(StringIO("created: 2024-01-01"))

        assert result["created"] == "2024-01-01"
        assert type(result["created"]) is str

    def test_leading_zero_scientific_notation_remains_string(self):
        result = FileHandler()(StringIO("maximum: 01e2"))

        assert result["maximum"] == "01e2"
        assert type(result["maximum"]) is str

    def test_underscored_scientific_notation_remains_string(self):
        result = FileHandler()(StringIO("maximum: 1_0e2"))

        assert result["maximum"] == "1_0e2"
        assert type(result["maximum"]) is str


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

        assert result == {}
