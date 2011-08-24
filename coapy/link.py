# Copyright (c) 2010 People Power Co.
# All rights reserved.
# 
# This open source code was developed with funding from People Power Company
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# - Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the
#   distribution.
# - Neither the name of the People Power Corporation nor the names of
#   its contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
# PEOPLE POWER CO. OR ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE
# 

import re

class ParameterValueSupport (object):
    """Base class for extracting and formatting link-format attributes.

    CoAP link parameters are key/value pairs, separated by an ASCII
    equals sign.  The value pattern can be specific to the key; for
    example, the ``d=`` attribute value is a URI-reference.

    There is a subclass of this class for each type of link-param
    value.  Normally, those subclasses need only override the
    :attr:`._re` and :attr:`._format` attributes; in other cases
    :meth:`._processDecoded` or other methods must also be
    overridden."""
    
    _re = None
    """A :mod:`compiled regular expression<re>` used to extract the
    parameter value.

    The expression should produce a single group the value of which is
    the value of the parameter (e.g., excluding surrounding quotation
    characters).  By default, this expression is used by the
    :meth:`decode` method."""

    _format = '%s'
    """A format string used to express the parameter value in a
    link-value description.

    This should produce a sequence that can be matched by
    :meth:`decode`."""

    @classmethod
    def _processDecoded (self, text):
        """Perform any post-processing on an value string.

        The default implementation simply returns *text* unchanged.
        Override this in subclasses that need to do something more
        complex, such as convert a comma-separated sequence of
        ASCII-encoded integers into a list of Python :class:`int`
        instances.

        :param text: the text to be processed
        :rtype: specific to the subclass
        """
        
        return text

    @classmethod
    def decode (self, text):
        """Extract a parameter value from the text.

        The default implementation matches the :attr:`_re` regular
        expression against the start of *text*.  If the pattern match
        fails, *value* is ``None``.  Otherwise, the extracted pattern
        is run through :meth:`_processDecoded` and returned as
        *value*.  In either case, any matched prefix is stripped from
        the returned *text* value.

        :param text: A string comprising the value for a parameter,
          followed optionally by additional parameters or link
          descriptions.
        :return: A tuple (*value*, *text*)
        """

        m = self._re.match(text)
        if m is None:
            return (None, text)
        text = text[m.end():]
        return (self._processDecoded(m.group(1)), text)

    @classmethod
    def encode (self, value):
        """Convert a parameter value into the text representation used
        in a link description.

        :note: The implementing class is not obliged to validate that
               the result of encoding *value* is a string that can be
               decoded to the same value.  For example, *value* is not
               checked for illegal characters.

        :param value: value to be represented
        :rtype: :class:`str`
        """
        return self._format % (value,)

class PVS_ptoken (ParameterValueSupport):
    """Value support where the value matches the ``ptoken`` rule in the CoAP link-value ABNF."""
    #: Characters that can appear within a ptoken
    _ptoken_char = '!#$%&\'()*+\-./0-9:<=>?@a-zA-Z[\]^_`{|}~'

    #: An expression matching a ptoken
    _re = re.compile('([%s]+)' % (_ptoken_char,))

class PVS_dquotedString (ParameterValueSupport):
    """Value support where the value is a string enclosed in ASCII
    double quotes, e.g. ``"some text"``.

    :note: Quote characters cannot appear within the string body, not
           even if escaped."""
    _re = re.compile(r'"([^"]*)"')
    _format = '"%s"'

class PVS_unknown (ParameterValueSupport):
    """Value support for unrecognized parameters.

    This matches either :class:`PVS_ptoken` or
    :class:`PVS_dquotedString`, depending on the content of the
    value."""

    @classmethod
    def decode (self, text):
        """Override base class to support either dquotedString or ptoken.

        If the text begins with double-quotes, this processes as
        :meth:`PVS_dquotedString.decode`.  Otherwise, it processes as
        :meth:`PVS_ptoken.decode`."""
        if text.startswith('"'):
            return PVS_dquotedString.decode(text)
        return PVS_ptoken.decode(text)

    @classmethod
    def encode (self, value):
        """Override base class to support either dquotedString or ptoken.

        If the value is consistent with the requirements of
        :class:`PVS_ptoken`, this processes as
        :meth:`PVS_ptoken.encode`.  Otherwise, it processes as
        :meth:`PVS_dquotedString.encode`."""
        m = PVS_ptoken._re.match(value)
        if (m is not None) and (len(value) == m.end()):
            return PVS_ptoken.encode(value)
        return PVS_dquotedString.encode(value)

class PVS_squotedString (ParameterValueSupport):
    """Value support where the value is a string enclosed in ASCII
    single quotes, e.g. ``\'some text\'``.

    :note: Quote characters cannot appear within the string body, not
           even if escaped."""
    _re = re.compile(r"'([^']*)'")
    _format = "'%s'"

class PVS_anglequotedString (ParameterValueSupport):
    """Value support where the value is a string enclosed in angle brackets, e.g. ``</path>``.

    :note: A close-angle-bracket (``>``) character cannot appear
           within the string body, not even if escaped."""
    _re = re.compile(r'<([^>]*)>')
    _format = '<%s>'

class PVS_integer (ParameterValueSupport):
    """Value support where the value is a sequence of one or more
    ASCII digits, e.g. ``42``."""
    _re = re.compile(r'([0-9]+)')
    _format = '%u'
    _processDecoded = int

class PVS_commaSeparatedIntegers (ParameterValueSupport):
    """Value support where the value is a sequence of ASCII integers
    separated by commas, e.g. ``0,41``.

    The represented value is expressed as a Python list of
    :class:`int` instances. """
    
    _re = re.compile(r'([0-9]+(?:,[0-9]+)*)')

    @classmethod
    def _processDecoded (self, text):
        return [ int(_v) for _v in text.split(',') ]

    @classmethod
    def encode (self, value):
        return ','.join(['%u' % (_v,) for _v in value ])

class LinkValue (object):
    """A CoAP link.

    A link represents a resource supported by a CoAP end-point.  Links
    comprise the URI-reference at which the resource may be accessed,
    along with a set of parameters that can be used to provide
    additional information about the resource and how to use it.

    Link resources are described in a text format registered as
    ``application/link-format`` and can be obtained from a CoAP
    end-point by getting the ``/.well-known/r`` resource from that
    endpoint.
    """
    
    # : Characters that can appear within a parmname token
    _parmname_char = r'a-zA-Z0-9!#$&+\-.^_`|~'

    _parmnameEquals_re = re.compile('([%s]+)(=)?' % (_parmname_char,))

    _DefaultLinkProcessing = PVS_unknown
    """Define processing for an unrecognized link parameter."""

    _LinkParameterDefinitions = {
        'd' : PVS_dquotedString,
        'sh' : PVS_dquotedString,
        'n' : PVS_dquotedString,
        'ct' : PVS_commaSeparatedIntegers,
        'id' : PVS_integer,
        }
    """Map from param names to a subclass of
    :class:`ParameterValueSupport` that can encode and decode the value
    for the parameter."""
    
    def __init__ (self, uri, **kw):
        """Create a LinkValue instance from a URI and a set of
        parameters.

        Arbitrary keywords are accepted and stored as link
        parameters."""
        self.__uri = uri
        self.__params = kw

    uri = property(lambda _s: _s.__uri)
    d = property(lambda _s: _s.__params.get('d'))
    sh = property(lambda _s: _s.__params.get('sh'))
    n = property(lambda _s: _s.__params.get('n'))
    ct = property(lambda _s: _s.__params.get('ct'))
    id = property(lambda _s: _s.__params.get('id'))

    @classmethod
    def decode (cls, text):
        """Extract and create a LinkValue instance from a resource
        description.

        The ABNF grammar for link-value in CoAP is evaluated against
        *text* to extract the URI and associated link parameters of a
        link value.  An instance of this class is created to hold
        those parameters, and returned as *link*.  The octets consumed
        in defining the link are stripped, and the remainder returned
        in *remainder*.

        :param text: A sequence of octets comprising a resource
           description, optionally followed by other text.
        :return: (*link*, *remainder*)
        """

        m = PVS_anglequotedString._re.match(text)
        if m is None:
            raise Exception()
        uri = m.group(1)
        params = { }
        text = text[m.end():]
        while text.startswith(';'):
            text = text[1:]
            m = cls._parmnameEquals_re.match(text)
            if m is None:
                raise Exception()
            paramname = m.group(1).lower()
            paramval = None
            text = text[m.end():]
            if m.group(2):
                pvs = cls._LinkParameterDefinitions.get(paramname, cls._DefaultLinkProcessing)
                (paramval, text) = pvs.decode(text)
                if paramval is None:
                    raise Exception()
            params.setdefault(paramname, paramval)
        return (cls(uri, **params), text)

    def encode (self):
        """Return a string encoding the link-format representation of
        the link."""
        seq = [ PVS_anglequotedString.encode(self.__uri) ]
        keys = sorted(self.__params.keys())
        for k in keys:
            v = self.__params[k]
            if v is None:
                seq.append(k)
            else:
                seq.append('%s=%s' % (k, self._LinkParameterDefinitions.get(k, self._DefaultLinkProcessing).encode(v)))
        return ';'.join(seq)

def decode_resource_descriptions (text):
    links = []
    while text:
        (link, text) = LinkValue.decode(text)
        links.append(link)
        if not text.startswith(','):
            break
        text = text[1:]
    return (links, text)
