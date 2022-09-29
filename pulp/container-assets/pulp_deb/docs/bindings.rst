Client Bindings
================================================================================

.. include:: external_references.rst


Python Client
--------------------------------------------------------------------------------

The `pulp-deb-client package`_ on PyPI provides bindings for all ``pulp_deb`` :ref:`REST API <rest_api>` endpoints.
It is currently published daily and with every RC.

The `pulpcore-client package`_ on PyPI provides bindings for all pulpcore :ref:`REST API <rest_api>` endpoints.
It is currently published daily and with every RC.


Ruby Client
--------------------------------------------------------------------------------

The `pulp_deb_client Ruby Gem`_ on rubygems.org provides bindings for all ``pulp_deb`` :ref:`REST API <rest_api>` endpoints.
It is currently published daily and with every RC.

The `pulpcore_client Ruby Gem`_ on rubygems.org provides bindings for all pulpcore :ref:`REST API <rest_api>` endpoints.
It is currently published daily and with every RC.


Client in a Language of Your Choice
--------------------------------------------------------------------------------

A client can be generated using Pulp's OpenAPI schema and any of the available `OpenAPI generators`_.

Generating a client is a two step process:

1) Download the OpenAPI schema for pulpcore and all installed plugins:

   .. code-block:: bash

      curl -o api.json http://<pulp-hostname>:24817/pulp/api/v3/docs/api.json

   The OpenAPI schema for a specific plugin can be downloaded by specifying the plugin's module name as a GET parameter.
   For example for ``pulp_deb`` only endpoints use a query like this:

   .. code-block:: bash

      curl -o api.json http://<pulp-hostname>:24817/pulp/api/v3/docs/api.json?plugin=pulp_deb

2) Generate a client using OpenAPI generator:

   The schema can then be used as input to the ``openapi-generator-cli``.
   See `try OpenAPI generator`_ for documentation on getting started.


Generating a Client on dev Environment
--------------------------------------------------------------------------------

The easiest way to set up a Pulp development environment is to use a Vagrant box from the `pulp Ansible installer`_ repo.
These development boxes provide the ``pbindings`` alias for generating bindings (aka clients):

For example, use the following for generating Python bindings for ``pulp_deb``:

.. code-block:: bash

   pbindings pulp_deb python

As another example, use the following for generating Ruby bindings for version ``2.5.0b1`` of ``pulp_deb``:

.. code-block:: bash

   pbindings pulp_deb ruby 2.5.0b1
