***************
JSONSchema Path
***************

.. image:: https://img.shields.io/pypi/v/jsonschema-path.svg
     :target: https://pypi.python.org/pypi/jsonschema-path
.. image:: https://travis-ci.org/p1c2u/jsonschema-path.svg?branch=master
     :target: https://travis-ci.org/p1c2u/jsonschema-path
.. image:: https://img.shields.io/codecov/c/github/p1c2u/jsonschema-path/master.svg?style=flat
     :target: https://codecov.io/github/p1c2u/jsonschema-path?branch=master
.. image:: https://img.shields.io/pypi/pyversions/jsonschema-path.svg
     :target: https://pypi.python.org/pypi/jsonschema-path
.. image:: https://img.shields.io/pypi/format/jsonschema-path.svg
     :target: https://pypi.python.org/pypi/jsonschema-path
.. image:: https://img.shields.io/pypi/status/jsonschema-path.svg
     :target: https://pypi.python.org/pypi/jsonschema-path

About
#####

Object-oriented JSONSchema

Key features
############

* Traverse schema like paths
* Access schema on demand with separate dereferencing accessor layer

Installation
############

.. code-block:: console

   pip install jsonschema-path

Alternatively you can download the code and install from the repository:

.. code-block:: console

   pip install -e git+https://github.com/p1c2u/jsonschema-path.git#egg=jsonschema_path


Usage
#####

.. code-block:: python

   >>> from jsonschema_path import SchemaPath
   
   >>> d = {
   ...     "properties": {
   ...        "info": {
   ...            "$ref": "#/$defs/Info",
   ...        },
   ...     },
   ...     "$defs": {
   ...         "Info": {
   ...             "properties": {
   ...                 "title": {
   ...                     "$ref": "http://example.com",
   ...                 },
   ...                 "version": {
   ...                     "type": "string",
   ...                     "default": "1.0",
   ...                 },
   ...             },
   ...         },
   ...     },
   ... }
   
   >>> path = SchemaPath.from_dict(d)
   
   >>> # Stat keys
   >>> "properties" in path
   True
   
   >>> # Concatenate paths with /
   >>> info_path = path / "properties" / "info"
   
   >>> # Stat keys with implicit dereferencing
   >>> "properties" in info_path
   True
   
   >>> # Concatenate paths with implicit dereferencing
   >>> version_path = info_path / "properties" / "version"
   
   >>> # Open content with implicit dereferencing
   >>> with version_path.open() as contents:
   ...     print(contents)
   {'type': 'string', 'default': '1.0'}


Related projects
################

* `openapi-core <https://github.com/p1c2u/openapi-core>`__
   Python library that adds client-side and server-side support for the OpenAPI.
* `openapi-spec-validator <https://github.com/p1c2u/openapi-spec-validator>`__
   Python library that validates OpenAPI Specs against the OpenAPI 2.0 (aka Swagger) and OpenAPI 3.0 specification
* `openapi-schema-validator <https://github.com/p1c2u/openapi-schema-validator>`__
   Python library that validates schema against the OpenAPI Schema Specification v3.0.

License
#######

Copyright (c) 2017-2025, Artur Maciag, All rights reserved. Apache-2.0
