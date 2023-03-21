***************
JSONSchema Spec
***************

.. image:: https://img.shields.io/pypi/v/jsonschema-spec.svg
     :target: https://pypi.python.org/pypi/jsonschema-spec
.. image:: https://travis-ci.org/p1c2u/jsonschema-spec.svg?branch=master
     :target: https://travis-ci.org/p1c2u/jsonschema-spec
.. image:: https://img.shields.io/codecov/c/github/p1c2u/jsonschema-spec/master.svg?style=flat
     :target: https://codecov.io/github/p1c2u/jsonschema-spec?branch=master
.. image:: https://img.shields.io/pypi/pyversions/jsonschema-spec.svg
     :target: https://pypi.python.org/pypi/jsonschema-spec
.. image:: https://img.shields.io/pypi/format/jsonschema-spec.svg
     :target: https://pypi.python.org/pypi/jsonschema-spec
.. image:: https://img.shields.io/pypi/status/jsonschema-spec.svg
     :target: https://pypi.python.org/pypi/jsonschema-spec

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

   pip install jsonschema-spec

Alternatively you can download the code and install from the repository:

.. code-block:: console

   pip install -e git+https://github.com/p1c2u/jsonschema-spec.git#egg=jsonschema_spec


Usage
#####

.. code-block:: python

   >>> from jsonschema_spec import SchemaPath
   
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

Copyright (c) 2017-2022, Artur Maciag, All rights reserved. Apache-2.0
