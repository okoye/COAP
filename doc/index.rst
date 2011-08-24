.. CoAPy documentation master file

*************************************************
CoAPy: Constrained Application Protocol in Python
*************************************************

What it is
==========

From `draft-ietf-core-coap
<http://tools.ietf.org/html/draft-ietf-core-coap>`_:

   ... Constrained Application Protocol (CoAP),
   a specialized RESTful transfer protocol for use with constrained
   networks and nodes for machine-to-machine applications such as smart
   energy and building automation.  These constrained nodes often have
   8-bit microcontrollers with small amounts of ROM and RAM, while
   networks such as 6LoWPAN often have high packet error rates and a
   typical throughput of 10s of kbit/s.  CoAP provides the REST Method/
   Response interaction model between application end-points, supports
   built-in resource discovery, and includes key web concepts such as
   URIs and content-types.  CoAP easily translates to HTTP for
   integration with the web while meeting specialized requirements such
   as multicast support, very low overhead and simplicity for
   constrained environments.

CoAPy is a Python implementation of the protocol, intended to allow Python
clients and servers.  It is developed by `People Power
Co. <http://www.peoplepowerco.com>`_ and released under the `BSD License
<http://www.openoshan.net/wiki/LICENSE>`_.  Get it from `SourceForge
<http://sourceforge.net/projects/coapy/>`_ by::

  git clone git://coapy.git.sourceforge.net/gitroot/coapy/coapy

Very rough now, not really pleasant to use, interfaces will change,
improvement suggestions welcomed, not suitable for use by small children.

Resources
=========

- `IETF CORE Working Group <http://tools.ietf.org/wg/core/>`_
- `CoRE WG Wiki <http://trac.tools.ietf.org/wg/core/trac/wiki>`_
- Current `draft-ietf-core-coap <http://tools.ietf.org/html/draft-ietf-core-coap>`_
- Current `draft-bormann-core-misc <http://tools.ietf.org/html/draft-bormann-coap-misc>`_
- CoAP mailing list archive `browsable <http://www.ietf.org/mail-archive/web/core/current/maillist.html>`_ 
  `downloadable <ftp://ftp.ietf.org/ietf-mail-archive/core/>`_
- Link-format reference at `draft-nottingham-http-link-header <http://tools.ietf.org/html/draft-nottingham-http-link-header>`_
- Service discovery via DNS at `draft-cheshire-dnsext-dns-sd <http://tools.ietf.org/html/draft-cheshire-dnsext-dns-sd>`_
- Hypertext Transfer Protocol--HTTP/1.1 :rfc:`2616`
- Uniform Resource Identifier (URI): Generic Syntax :rfc:`3986`

Contents:

.. toctree::
   :maxdepth: 2

   coapy.rst
   coapy_constants.rst
   coapy_options.rst
   coapy_link.rst
   coapy_connection.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

