from json import dumps
from os import unlink
from tempfile import NamedTemporaryFile

import pytest


@pytest.fixture
def create_file():
    files = []

    def create(schema):
        contents = dumps(schema).encode("utf-8")
        with NamedTemporaryFile(delete=False) as tf:
            files.append(tf)
            tf.write(contents)
        return tf.name

    yield create
    for tf in files:
        unlink(tf.name)
