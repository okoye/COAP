Options
=======

Supported Header Options
------------------------

=====================================================  ========================
Name                                                   Default
=====================================================  ========================
:class:`Content-type<coapy.options.ContentType>`       ``text/plain``
:class:`Max-age<coapy.options.MaxAge>`                 60 seconds
:class:`Uri-Scheme<coapy.options.UriScheme>`           ``coap``
:class:`Etag<coapy.options.Etag>`                    
:class:`Uri-Authority<coapy.options.UriAuthority>`   
:class:`Location<coapy.options.Location>`            
:class:`Uri-Path<coapy.options.UriPath>`             
:class:`Block<coapy.options.Block>` **EXPERIMENTAL**             
=====================================================  ========================

.. automodule:: coapy.options
   :members:
   :show-inheritance:

Option Internals
----------------

Base Class for Options
^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: coapy.options._Base
   :members:
   :undoc-members:

Mix-in Classes
^^^^^^^^^^^^^^

The following classes are mixed-in to CoAP option classes to provide common
support for representing and validating the option values.

.. autoclass:: coapy.options._StringValue_mixin
   :members:

.. autoclass:: coapy.options._UriPath_mixin
   :members:

.. autoclass:: coapy.options._IntegerValue_mixin
   :members:
