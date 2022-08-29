************
OpenAPI Spec
************

.. image:: https://img.shields.io/pypi/v/openapi-spec.svg
     :target: https://pypi.python.org/pypi/openapi-spec
.. image:: https://travis-ci.org/p1c2u/openapi-spec.svg?branch=master
     :target: https://travis-ci.org/p1c2u/openapi-spec
.. image:: https://img.shields.io/codecov/c/github/p1c2u/openapi-spec/master.svg?style=flat
     :target: https://codecov.io/github/p1c2u/openapi-spec?branch=master
.. image:: https://img.shields.io/pypi/pyversions/openapi-spec.svg
     :target: https://pypi.python.org/pypi/openapi-spec
.. image:: https://img.shields.io/pypi/format/openapi-spec.svg
     :target: https://pypi.python.org/pypi/openapi-spec
.. image:: https://img.shields.io/pypi/status/openapi-spec.svg
     :target: https://pypi.python.org/pypi/openapi-spec

About
#####

OpenAPI Spec with object-oriented paths

Key features
************

* Traverse elements like paths
* Access spec on demand with separate dereferencing accessor layer

Installation
############

::

    $ pip install openapi-spec

Alternatively you can download the code and install from the repository:

.. code-block:: bash

   $ pip install -e git+https://github.com/p1c2u/openapi-spec.git#egg=openapi_spec


Usage
#####

.. code-block:: python

   from openapi_spec import Spec
   
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
   
   # Concatenate paths with /
   info = spec / "info"
   
   # Stat path keys
   "title" in info
   
   # Open path dict
   with info.open() as info_dict:
       print(info_dict)


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

Copyright (c) 2017-2022, Artur Maciag, All rights reserved. Apache v2
