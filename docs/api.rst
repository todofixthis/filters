API Documentation
=================

.. automodule:: filters

Extensions
----------

.. automodule:: filters.extensions

.. py:data:: ext
   :module: filters
   :type: filters.extensions.FilterExtensionRegistry

   The registry of filters that other packages register under the
   :py:data:`~filters.extensions.GROUP_NAME` entry point group, each
   available as an attribute (e.g. ``filters.ext.Country``).

Test Helpers
------------

.. automodule:: filters.test

Type Variables and Aliases
--------------------------
The generic parameters and type aliases that the signatures above refer to.

.. autodata:: filters.base.FilterCompatible
   :no-value:

.. autodata:: filters.base.T_allowed1
   :no-value:

.. autodata:: filters.base.T_allowed2
   :no-value:

.. autodata:: filters.base.T_allowed3
   :no-value:

.. autodata:: filters.base.T_out
   :no-value:

.. autodata:: filters.base.T_resolved
   :no-value:

.. autodata:: filters.simple.T_callable
   :no-value:

.. autodata:: filters.simple.T_optional_default
   :no-value:

.. autodata:: filters.complex.T_tuple
   :no-value:

.. autodata:: filters.string.T_choice
   :no-value:
