from os import path

import pytest


@pytest.fixture
def data_resource_path_getter():
    def get_full_path(data_file):
        directory = path.abspath(path.dirname(__file__))
        return path.join(directory, data_file)

    return get_full_path
