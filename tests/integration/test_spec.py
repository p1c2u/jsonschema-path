from jsonschema_spec import Spec


class TestSpecFromDict:
    def test_ref(self):
        d = {
            "openapi": "3.0.1",
            "info": {
                "$ref": "#/components/Version",
            },
            "paths": {},
            "components": {
                "Version": {
                    "title": "Minimal",
                    "version": "1.0",
                },
            },
        }
        spec = Spec.from_dict(d)

        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec
        assert "components" in spec

        info = spec / "info"

        assert "title" in info
        assert "version" in info

        with info.open() as info_dict:
            assert info_dict == {
                "title": "Minimal",
                "version": "1.0",
            }


class TestSpecFromFilePath:
    def test_ref(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/petstore-separate/spec/openapi.yaml"
        )
        spec = Spec.from_file_path(fp)

        paths = spec / "paths"

        for _, path in paths.items():
            properties = (
                path
                / "get#responses#default#content#application/json#schema#properties"
            )
            with properties.open() as properties_dict:
                assert properties_dict == {
                    "code": {
                        "format": "int32",
                        "type": "integer",
                    },
                    "message": {
                        "type": "string",
                    },
                }

    def test_double_ref(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/petstore-separate/spec/openapi.yaml"
        )
        spec = Spec.from_file_path(fp)

        paths = spec / "paths"

        for _, path in paths.items():
            properties = (
                path
                / "get#responses#200#content#application/json#schema#items#properties"
            )
            with properties.open() as properties_dict:
                assert properties_dict == {
                    "id": {
                        "type": "integer",
                        "format": "int64",
                    },
                    "name": {
                        "type": "string",
                    },
                    "tag": {
                        "type": "string",
                    },
                }


class TestSpecFromFile:
    def test_recursive(self, data_resource_path_getter):
        fp = data_resource_path_getter(
            "data/v3.0/parent-reference/openapi.yaml"
        )
        spec_url = "file://" + fp
        with open(fp) as f:
            spec = Spec.from_file(f, spec_url=spec_url)

        properties = spec._make_child(
            [
                "paths",
                "/pets",
                "get",
                "parameters",
                0,
                "schema",
            ]
        )
        with properties.open() as properties_dict:
            assert properties_dict == {
                "type": "boolean",
            }
