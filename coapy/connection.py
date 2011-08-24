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

import coapy.options
import socket
import struct
import binascii
import fcntl
import random
import select
import time
import os

class Message (object):
    """Represent the components of a CoAP message.

    - :attr:`.transaction_type` 
    - :attr:`.code`
    - :attr:`.options`
    - :attr:`.payload`

    The transaction ID is not recorded in the message instance.
    Rather, it is recorded in a :class:`TransmissionRecord` or
    :class:`ReceptionRecord`.
    """

    version = property(lambda _s: 1, None, None, "The CoAP protocol version.")

    CON = 0
    """The message transaction type indicating a confirmable message
    (one that requires an acknowledgement)."""
    
    NON = 1
    """The message transaction type indicating a non-confirmable
    message (one that does not evoke an acknowledgement)."""

    ACK = 2
    """The message transaction type indicating acknowledgement of a
    :attr:`confirmable<.CON>` message.  Note that such a message may
    also include a response payload that pertains to the acknowledged
    message."""
    
    RST = 3
    """The message transaction type indicating that a received
    :attr:`confirmable<.CON>` message could not be processed due to
    insufficient context."""

    _TransactionTypeMap = { CON : 'CON',
                            NON : 'NON',
                            ACK : 'ACK',
                            RST : 'RST' }

    OptionKeywords = { 'content_type' : coapy.options.ContentType,
                       'max_age' : coapy.options.MaxAge,
                       'uri_scheme' : coapy.options.UriScheme,
                       'etag' : coapy.options.Etag,
                       'uri_authority' : coapy.options.UriAuthority,
                       'location' : coapy.options.Location,
                       'uri_path' : coapy.options.UriPath }
    """A map from Python identifiers to :mod:`option classes<coapy.options>`.

    These identifiers can be provided as keyword parameters to the
    :meth:`Message.__init__` method; the corresponding option class will be
    invoked with the parameter value to create an option that is
    associated with the message."""

    def __init__ (self, transaction_type=CON, code=0, payload='', **kw):
        """Create a Message instance.

        As a convenience, message options can be created from keyword
        parameters if the keywords are present in
        :attr:`.OptionKeywords`.

        :param transaction_type: One of :attr:`.CON`, :attr:`.NON`,
           :attr:`.ACK`, :attr:`.RST`.  The message transaction type
           cannot be modified after creation.

        :param code: The integral code identifying the method of a
           request message, or the disposition in a response message.
           By default, the code value is ``0``, indicating absence of
           REST content in the message (as suited for :attr:`.RST` or
           :attr:`.ACK` when indicating an asynchronous response will
           follow)

        :param payload: An optional REST payload for the message.  If
           not provided, the message will have no payload unless
           subsequently assigned.
        
        """

        if not (transaction_type in (self.CON, self.NON, self.ACK, self.RST)):
            raise ValueError()
        self.__transactionType = transaction_type
        self.__code = code
        self.__options = {}
        self.__payload  = payload
        for (k, v) in kw.iteritems():
            kw_type = self.OptionKeywords.get(k)
            if kw_type is not None:
                self.addOption(kw_type(v))

    __options = None
    def _get_options (self):
        """A tuple containing the :mod:`options <coapy.options>`
        associated with the message.

        The options are sorted in increasing value of option type.
        """
        return tuple(sorted(self.__options.itervalues(), lambda _a,_b: cmp(_a.Type, _b.Type)))
    options = property(_get_options)

    def addOption (self, opt):
        """Add a new option instance.

        If the option can appear multiple times, this method is
        intended to add the new value to the existing ones.

        :warning: Currently multi-valued options are not supported and
                  this is equivalent to :meth:`.replaceOption`.
        """
        self.__options[type(opt)] = opt
        return self

    def replaceOption (self, opt):
        """Add a new option instance.

        If the option is already present in message, its previous
        value is replaced by the new one.
        """
        self.__options[type(opt)] = opt
        return self

    def _classForOption (self, opt):
        if isinstance(opt, coapy.options._Base):
            opt = type(opt)
        elif isinstance(opt, int):
            opt = coapy.options.Registry.get(opt)
        if not issubclass(opt, coapy.options._Base):
            raise ValueError()
        return opt

    def deleteOption (self, opt):
        """Remove the option from the message.

        :param opt: An option, specified as an option instance, an
          option class, or the type code of an option.
        """
        self.__options.pop(self._classForOption(opt))

    def findOption (self, opt):
        """Locate the given option within the message.

        Returns ``None`` if no matching option can be found.

        :param opt: An option, specified as an option instance, an
          option class, or the type code of an option.
        """
        return self.__options.get(self._classForOption(opt))

    __transactionType = None
    def _get_transaction_type (self):
        """Return the transaction type (one of :attr:`.CON`,
        :attr:`.NON`, :attr:`.ACK`, :attr:`.RST`).

        :note: The transaction type is assigned when the message is
               created, and cannot be changed thereafter."""
        return self.__transactionType
    transaction_type = property(_get_transaction_type)

    __code = 0
    def _get_code (self):
        """The integral request method code or response code of the message."""
        return self.__code
    code = property(_get_code)

    __payload = ''
    def _get_payload (self):
        """The payload of the message as a :class:`str`.

        If this is not an empty string, there should be a
        corresponding :class:`coapy.options.ContentType` option
        present that defines its format (if the default value of
        ``text/plain`` is not appropriate)."""
        return self.__payload
    def _set_payload (self, payload):
        if not isinstance(payload, str):
            raise ValueError()
        self.__payload = payload
    payload = property(_get_payload, _set_payload)

    def build_uri (self, explicit=False):
        uri_scheme = self.findOption(coapy.options.UriScheme)
        uri_authority = self.findOption(coapy.options.UriAuthority)
        uri_path = self.findOption(coapy.options.UriPath)
        resp = []
        val = None
        if uri_scheme is not None:
            val = uri_scheme
        elif explicit:
            val = coapy.options.UriScheme.Default
        if val is not None:
            resp.append(val)
            resp.append(':')
        val = None
        if uri_authority is not None:
            val = uri_authority.value
        elif explicit:
            val = coapy.options.UriAuthority.Default
        if val is not None:
            resp.append('//')
            resp.append(val)

        val = coapy.options.UriPath.Default
        if uri_path is not None:
            val = uri_path.value
        resp.append('/%s' % (val,))
        return ''.join(resp)

    def __str__ (self):
        resp = [ self._TransactionTypeMap[self.__transactionType] ]
        if 0 != self.__code:
            resp.append('+')
            resp.append(coapy.codes.get(self.__code, '%u' % (self.__code,)))
        uri = self.build_uri()
        if uri:
            resp.append(uri)
        return ' '.join(resp)

    def _pack (self, transaction_id):
        """Return the message as an octet sequence.

        :param transaction_id: The transaction ID to be encoded into the sequence
        :rtype: :class:`str`
        """

        data = []
        if self.__options is None:
            num_options = 0
            option_encoding = ''
        else:
            (num_options, option_encoding) = coapy.options.encode(self.__options.itervalues())
        assert isinstance(option_encoding, str)
        data.append(chr((self.version << 6) + ((self.__transactionType & 0x03) << 4) + (num_options & 0x0F)))
        data.append(struct.pack('!BH', self.__code, transaction_id))
        if 0 < num_options:
            data.append(option_encoding)
        if (0 != self.__code) and self.__payload:
            data.append(self.__payload)
        return ''.join(data)

    @classmethod
    def decode (cls, packed):
        """Create a Message instance from a payload.

        This method decodes the payload, and returns a pair (*xid*,
        *message*) where *xid* is the transaction ID extracted from
        the encoded message, and *message* is an instance of
        :class:`Message` initialized to the decoded components of the
        data.

        :param payload: A sequence of octets comprising a complete CoAP packet
        :rtype: (:class:`int`, :class:`Message`)
        """
        
        vtoc = ord(packed[0])
        if 1 != 0x03 & (vtoc >> 6):
            raise Exception()
        transaction_type = 0x03 & (vtoc >> 4)
        num_options = (vtoc & 0x0F)
        (code, transaction_id) = struct.unpack('!BH', packed[1:4])
        (options, packed) = coapy.options.decode(num_options, packed[4:])
        instance = cls(transaction_type=transaction_type, code=code, payload=packed)
        for opt in options:
            instance.__options[type(opt)] = opt
        return (transaction_id, instance)

def is_multicast (address):
    """Return ``True`` iff address is a multicast address.

    This function is used to eliminate retransmissions for confirmable
    messages sent to multicast addresses.

    :param address: A socket address as supported by the Python socket
        functions: i.e. a pair (*host*, *port*) for IPv4 addresses and
        a tuple (*host*, *port*, *flowinfo*, *scopeid*) for IPv6.  The
        host may be either a host name or an IP address in the
        textual notation appropriate to the address family.
    """

    if isinstance(address, str):
        return False
    if not isinstance(address, tuple):
        raise ValueError()
    if 2 == len(address):
        family = socket.AF_INET
        (host, port) = address
    elif 4 == len(address):
        family = socket.AF_INET6
        (host, port, flowinfo, scopeid) = address
    else:
        raise ValueError()
    for (_, _, _, _, sockaddr) in socket.getaddrinfo(host, port, family):
        inaddr = socket.inet_pton(family, sockaddr[0])
        if socket.AF_INET == family:
            return 0xE0 == (0xF0 & ord(inaddr[0]))
        elif socket.AF_INET6 == family:
            return 0xFF == ord(inaddr[0])
    return False

class TransmissionRecord (object):
    """Material related to a transmitted CoAP message.

    - :attr:`.message`
    - :attr:`.remote`
    - :attr:`.transaction_id`
    - :attr:`.end_point`
    - :attr:`.packed`

    """

    __responseTimeout = None

    def __init__ (self, end_point, message, remote):
        """
        :param end_point: The :class:`EndPoint` responsible for
          transmitting the message.

        :param message: An instance of :class:`Message` from which the
          transmission content will be calculated

        :param remote: A Python :mod:`socket` address identifying the
          destination of the transmission.
        """

        self.__endPoint = end_point
        self.__message = message
        self.__transactionId = self.__endPoint._nextTransactionId()
        self.__remote = remote

        self.__packed = message._pack(self.__transactionId)

        self.__transmissionsLeft = 1
        if (Message.CON == message.transaction_type) and (not is_multicast(remote)):
            self.__transmissionsLeft = coapy.MAX_RETRANSMIT
        self.__responseTimeout = coapy.RESPONSE_TIMEOUT
        self.__nextEventTime = time.time()
        self.__allResponses = set()
        if Message.CON == message.transaction_type:
            self.__responseType = None
        else:
            self.__responseType = message.transaction_type

    __endPoint = None
    def _get_end_point (self):
        """The :class:`EndPoint` that transmitted the message."""
        return self.__endPoint
    end_point = property(_get_end_point)

    __message = None
    def _get_message (self):
        """A reference to the :class:`Message` from which the transmission derived.

        :note: The content of the message may have been changed by
           application code subsequent to its transmission."""
        return self.__message
    message = property(_get_message)

    __transactionId = None
    def _get_transaction_id (self):
        """The transmission ID encoded in the packed message."""
        return self.__transactionId
    transaction_id = property(_get_transaction_id)

    __remote = None
    def _get_remote (self):
        """The Python :mod:`socket` address to which the transmission was sent."""
        return self.__remote
    remote = property(_get_remote)

    __packed = None
    def _get_packed (self):
        """The octet sequence representing the message."""
        return self.__packed
    packed = property(_get_packed)

    __responseType = None
    def _get_response_type (self):
        """
        - :attr:`Message.NON` if the message does not require a response

        - :attr:`Message.ACK` if the message has been acknowledged.
          If the acknowledgement carried a response message, it is
          available in :attr:`.response`.

        - :attr:`Message.RST` if the message received could not
          process the message.

        - ``None`` if the message is confirmable and neither an
          :attr:`Message.ACK` nor :attr:`Message.RST` has been
          received.
        """
        return self.__responseType
    response_type = property(_get_response_type)

    __transmissionsLeft = None
    def _get_transmissions_left (self):
        """Return the number of (re-)transmissions yet to occur.

        A positive value requires that :attr:`next_event_time` not be
        ``None``."""
        return self.__transmissionsLeft
    transmissions_left = property(_get_transmissions_left)

    __transmissionTime = None
    def _get_transmission_time (self):
        """The :meth:`time.time` at which the message was first transmitted."""
        return self.__transmissionTime
    def _set_transmission_time (self, transmission_time):
        """Set the :attr:`.transmission_time`.

        :note: Only for use by an :class:`EndPoint`."""
        if self.__transmissionTime is None:
            self.__transmissionTime = transmission_time
        self._set_last_event_time(transmission_time)
    transmission_time = property(_get_transmission_time)

    __lastEventTime = None
    def _get_last_event_time (self):
        """The :meth:`time.time` at which the last event related to the transmission occured.

        Transmission events are:

        - transmission or retranmission of the message
        - receipt of a response to the message
        """
        return self.__lastEventTime
    def _set_last_event_time (self, let=None):
        if let is None:
            let = time.time()
        self.__lastEventTime = let
        return let
    last_event_time = property(_get_last_event_time)

    __nextEventTime = None
    def _get_next_event_time (self):
        """Get the :meth:`time.time` value at which the next event
        associated with this transmission is due.

        Predictable transmission events are:

        - the time at which the message should be retransmitted
        - the time by which a response to the message should be received

        Returns ``None`` if there are no events associated with the
        transmission.
        """
        return self.__nextEventTime
    def _clear_next_event_time (self):
        self.__nextEventTime = None
    next_event_time = property(_get_next_event_time)

    def _decrementTransmissions (self):
        """Record fact-of a (re-)transmission, updating the various counters.

        :note: To be invoked only by an :class:`EndPoint`.
        """
        let = self._set_last_event_time()
        if self.__transmissionTime is None:
            self.__transmissionTime = let
        self.__nextEventTime = let + self.__responseTimeout
        self.__transmissionsLeft -= 1
        self.__responseTimeout *= 2

    __responseRecord = None
    def _get_response (self):
        """The :class:`ReceptionRecord` for the first message that was
        interpreted as a response to this message."""
        return self.__responseRecord
    response = property(_get_response)

    __allResponses = None
    def _get_responses (self):
        """A set containing all :class:`ReceptionRecords` that pertain
        to this transmission."""
        return self.__allResponses
    responses = property(_get_responses)

    def _processResponse (self, rx_record):
        """Process a response to this transmission.

        Cancel any subsequent transmissions.  Add the response to
        :attr:`responses`.  If this is the first reponse, set
        :attr:`response` and record :attr:`response_type`.

        This counts as an event for the purposes of
        :attr:`last_event_time`.
        """
        self.__lastEventTime = time.time()
        self.__nextEventTime = None
        self.__transmissionsLeft = 0
        if self.__responseRecord is None:
            self.__responseRecord = rx_record
        if self.__responseType is None:
            self.__responseType = rx_record.message.transaction_type
        self.__allResponses.add(rx_record)

    def _is_unacknowledged (self):
        """Return ``True`` iff this was a confirmable transaction for
        which the last transmission response wait has elapsed without
        receipt of a response."""
        return (self.__nextEventTime is None) and (self.__responseType is None)
    is_unacknowledged = property(_is_unacknowledged)

    def __str__ (self):
        return '%s[%d]' % (str(self.__message), self.__transactionId)


class ReceptionRecord (object):
    """Material related to a received CoAP message.

    - :attr:`.message`
    - :attr:`.remote`
    - :attr:`.transaction_id`
    - :attr:`.pertains_to`
    - :attr:`.end_point`
    """

    def __init__ (self, end_point, packed, remote):
        self.__endPoint = end_point
        (self.__transactionId, self.__message) = Message.decode(packed)
        self.__remote = remote
        if Message.CON == self.__message.transaction_type:
            self.__responseType = None
        else:
            self.__responseType = Message.NON

    __endPoint = None
    def _get_end_point (self):
        """The :class:`EndPoint` that received the message."""
        return self.__endPoint
    end_point = property(_get_end_point)

    __message = None
    def _get_message (self):
        """The :class:`Message` received."""
        return self.__message
    message = property(_get_message)

    __remote = None
    def _get_remote (self):
        """The :mod:`socket` address from which the message was received."""
        return self.__remote
    remote = property(_get_remote)

    __transactionId = None
    def _get_transaction_id (self):
        """The transaction ID of the received message."""
        return self.__transactionId
    transaction_id = property(_get_transaction_id)

    __pertainsTo = None
    def _get_pertains_to (self):
        """The :class:`TransmissionRecord` to which the received
        message was interpreted as a response.

        The value will be ``None`` if the :attr:`.message`
        :meth:`transaction type <Message.transaction_type>` is neither
        :attr:`Message.ACK` nor :attr:`Message.RST`, or if the
        receiving :class:`EndPoint` could not identify the relevant
        message (e.g., it had already been expired from the
        transmission cache).
        """
        return self.__pertainsTo
    def _set_pertains_to (self, pertains_to):
        """Set the :attr:`pertains_to` field and cross-reference to this record.

        :param pertains_to: A :class:`TransmissionRecord` for which
          this message appears to be a response.
        """
        self.__pertainsTo = pertains_to
        pertains_to._processResponse(self)
    pertains_to = property(_get_pertains_to)

    has_responded = property(lambda _s: _s.__responseType is not None)

    def _respond (self, response_msg):
        if self.has_responded:
            raise Exception()
        self.__responseType = response_msg.transaction_type
        self.__endPoint.socket.sendto(response_msg._pack(self.transaction_id), self.__remote)

    def ack (self, response_msg=None):
        if response_msg is None:
            response_msg = Message(Message.ACK)
        self._respond(response_msg)

    def reset (self):
        self._respond(Message(Message.RST))

    def __str__ (self):
        return '%s[%d]' % (str(self.__message), self.__transactionId)

def join_discovery (dfd, interface_address):
    """Join a socket to a multicast address for discovery.

    The *interface_address* must be a host name or IP address string
    that resolves to an IP (or IPv6) address bound to one of the
    network interfaces on the local host.  The socket passed as *dfd*
    will be made to join the family-specific all-hosts multicast group
    on the corresponding interface.

    The function returns a pair (*if_sockaddr*, *mc_sockaddr*) which
    are Python socket address tuples including the default COAP port
    and identifying the network interface to on which the socket has
    joined and the address to which discovery messages should be
    transmitted.

    :param dfd: A Python socket instance.

    :param interface_address: An IP address or host name in the
       address family associated with *dfd*.

    :return: (*if_sockaddr*, *mc_sockaddr*)

    """

    print 'address %s' % (interface_address,)
    rv = socket.getaddrinfo(interface_address, coapy.COAP_PORT, dfd.family, dfd.type, dfd.proto)
    if_sockaddr = rv[0][4]
    if socket.AF_INET == dfd.family:
        mc_address = '224.0.0.1'
    elif socket.AF_INET6 == dfd.family:
        mc_address = 'ff02::1'
    else:
        raise Exception('Unsupported address family')

    rv = socket.getaddrinfo(mc_address, coapy.COAP_PORT, dfd.family, dfd.type, dfd.proto)
    mc_sockaddr = rv[0][4]

    if_addr = if_sockaddr[0]
    if 2 == len(if_sockaddr):
        if_addr_packed = socket.inet_pton(socket.AF_INET, if_addr)
        mc_addr_packed = socket.inet_pton(socket.AF_INET, mc_sockaddr[0])
        dfd.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, if_addr_packed)
        dfd.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, mc_addr_packed+if_addr_packed)
    elif 4 == len(if_sockaddr):
        if_addr_packed = socket.inet_pton(socket.AF_INET6, if_addr)
        if_index = if_sockaddr[3]
        if 0 == if_index:
            # Interface address did not include scope id.  Try to find it.
            # NB: This probably only works on Linux.
            if_hexstr = binascii.hexlify(if_addr_packed)
            for if6 in file('/proc/net/if_inet6').readlines():
                if if6.startswith(if_hexstr):
                    if_index = int(if6.split()[1], 16)
                    if_sockaddr = if_sockaddr[:3] + (if_index,)
                    break
        if_index_packed = struct.pack('I', if_index)
        dfd.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_IF, if_index_packed)
        mc_sockaddr = mc_sockaddr[:3] + (if_index,)
        mreq_packed = socket.inet_pton(socket.AF_INET6, mc_sockaddr[0]) + if_index_packed
        dfd.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq_packed)
    else:
        raise Exception('Multicast not supported on interface %s' % (interface_address,))

    return (if_sockaddr, mc_sockaddr)

class EndPoint (object):
    __transactionId = None

    __pendingTransmissions = None

    MAX_TX_HISTORY_SEC = 10

    def __init__ (self,
                  address_family=socket.AF_INET,
                  socket_type=socket.SOCK_DGRAM,
                  socket_proto=socket.IPPROTO_UDP):
        """Create a CoAP endpoint.

        A socket is created in the specified address family.  The
        caller should invoke the :meth:`.bind` method to associate
        with the socket a unicast address and port at which the
        endpoint will listen for CoAP messages.  The :meth:`.process`
        method can be used to detect incoming messages and do
        transaction-level CoAP processing.

        If the end-point is to participate in CoAP service discovery,
        :meth:`.bindDiscovery` should be invoked providing each
        network interface on which the endpoint should listen for
        discovery messages.  
        """

        self.__transactionId = random.randint(0, 65535)
        self.__filenoMap = { }
        self.__discoverySockets = set()
        self.__poller = select.poll()
        self.__pendingTransmissions = { }
        self.__socket = socket.socket(address_family, socket_type, socket_proto)
        self.register(self.__socket)

    __address = None
    def bind (self, address):
        """Bind the end-point to the given address.

        :param address: A Python unicast address in the appropriate
           family as defined when the endpoint was created.
        """
        self.__socket.bind(address)
        self.register(self.__socket)
    def _get_address (self):
        """Return the end-point address."""
        return self.__address
    address = property(_get_address)

    def bindDiscovery (self, interface_address):
        """Listen for CoAP discovery messages on the specified interface.

        This method ensures that there is a socket listening on the
        specified interface and accepting CoAP messages sent to the
        all-hosts multicast group on the default CoAP port.  If the
        standard endpoint socket meets those requirements, it is used;
        otherwise a new socket is created.  In the latter case, if a
        message is received on that socket a :attr:`Message.RST`
        message is transmitted to the sender from the end-point
        socket, allowing the sender to locate the supported end-point.

        :todo: Something sensible if the end-point socket is bound to
          a specific interface which is not the same as
          *interface_address*.

        :todo: Something to avoid multiple responses if we're listing
          on different interfaces.

        :param interface_address: The host name or IP address string
          identifying a network interface on this host on which
          service discovery multicast messages should be received.
        """

        # If the endpoint's socket uses the standard port, we can just
        # join it to the multicast address.  If it listens on a
        # different port, we need to create a new socket that listens
        # on the standard port and join it.

        ep_sockaddr = self.__socket.getsockname()
        do_bind = (ep_sockaddr[1] != coapy.COAP_PORT)
        if do_bind:
            dfd = socket.socket(self.__socket.family, self.__socket.type, self.__socket.proto)
            dfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print 'Discovery on new socket %s' % (dfd,)
        else:
            dfd = self.__socket
            print 'Discovery on endpoint socket %s' % (dfd,)

        (if_sockaddr, mc_sockaddr) = join_discovery(dfd, interface_address)
        if do_bind:
            dfd.bind(mc_sockaddr)
            self.__discoverySockets.add(dfd)
            self.register(dfd)

    __socket = None
    def _get_socket (self):
        """Return a reference to the primary socket associated with the end-point.

        If this end-point is expected to receive REST requests, the
        socket should be bound to a known port so that clients can
        identify the server."""
        return self.__socket
    socket = property(_get_socket)

    def register (self, sfd):
        """Register the given socket as a potential source of incoming messages.

        The primary :attr:`socket` is automatically registered.  This
        method can be used to associate additional sockets, such as
        multicast ones, with this end-point.

        :note: Regardless of the socket on which a message is
               received, any response will be transmitted from
               :attr:`socket`.
        """
        self.__filenoMap[sfd.fileno()] = sfd
        fcntl.fcntl(sfd, fcntl.F_SETFL, os.O_NONBLOCK | fcntl.fcntl(sfd, fcntl.F_GETFL))
        self.__poller.register(sfd, select.POLLIN)

    def _nextTransactionId (self):
        """Reserve and return a new transaction identifier."""
        transaction_id = self.__transactionId
        self.__transactionId = 0xFFFF & (1 + self.__transactionId)
        return transaction_id

    def send (self, message, remote):
        """Transmit a message to the remote.

        The message should have a code of either :attr:`Message.CON`
        or :attr:`Message.NON`; acknowledgements and resets should be
        generated through the :class:`ReceptionRecord` methods.

        The :class:`TransmissionRecord` associated with the
        transmission is returned.

        :note: Invoking this does not actually transmit the message:
               it merely records it and queues it for transmission on
               the next invocation of :meth:`.process`.
        """
        tx_record = TransmissionRecord(self, message, remote)
        self.__pendingTransmissions[tx_record.transaction_id] = tx_record
        return tx_record

    def _markAsUnacknowledged (self, tx_record):
        """Invoked by the end-point when the last transmission for a
        message has gone unacknowledged.

        Sub-classes may post-extend this to provide asynchronous
        notification of such an event."""
        tx_record._clear_next_event_time()
        return tx_record

    def _removeTransmission (self, tx_record):
        """Invoked by the end-point when a transmission record is to
        be removed from the cache.

        Sub-classes may post-extend this to provide asynchronous
        notification of such an event."""
        del self.__pendingTransmissions[tx_record.transaction_id]
        return tx_record

    def process (self, timeout_ms):
        """Process network activity related to CoAP messages on this
        end-point.

        This method is responsible for transmitting (and
        re-transmitting) outgoing messages, and for receiving incoming
        messages.  It will block until the timeout is reached, or an
        incoming message is received.

        Incoming messages that are transaction responses are, if
        possible, associated with the transmission record to which
        they pertain.  A :class:`ReceptionRecord` is returned.

        :note: The infrastructure does not automatically acknowledge
          any incoming message; this is an application responsibility.

        :param timeout_ms: The maximum time, in milliseconds, that
           this method should block.  A value of ``None`` indicates no
           limit: the method will block forever if no activity occurs.
        :return: *rx_record* or ``None``
        :rtype: :class:`ReceptionRecord`
        """

        start_time = time.time()
        end_time = None
        if timeout_ms is not None:
            end_time = start_time + timeout_ms / 1000.0
        rx_record = None
        did_pass = False
        while rx_record is None:
            now = time.time()

            # If we've been through at least once, and we're supposed
            # to return at a particular point, stop if the remaining
            # time is less than a millisecond.
            if did_pass and (end_time is not None):
                end_in_ms = int(1000 * (end_time - now))
                if 0 >= end_in_ms:
                    break

            # Figure out which records are outdated, which are due to
            # be retransmitted, and when we need to wake up to do the
            # next retransmission.
            next_event_time = None
            transmit_due = set()
            expire_set = set()
            for tx_record in self.__pendingTransmissions.itervalues():
                event_time = tx_record.next_event_time
                if (event_time is not None) and (event_time <= now):
                    if 0 < tx_record.transmissions_left:
                        transmit_due.add(tx_record)
                    else:
                        self._markAsUnacknowledged(tx_record)
                        event_time = tx_record.next_event_time
                if event_time is None:
                    if now > (tx_record.last_event_time + self.MAX_TX_HISTORY_SEC):
                        expire_set.add(tx_record)
                else:
                    if (next_event_time is None) or (event_time < next_event_time):
                        next_event_time = event_time

            # Flush the cache
            for tx_record in expire_set:
                self._removeTransmission(tx_record)

            evt = select.POLLIN
            if transmit_due:
                evt += select.POLLOUT
                poll_timeout_ms = 0
            else:
                if (end_time is not None) and ((next_event_time is None) or (end_time < next_event_time)):
                    next_event_time = end_time
                poll_timeout_ms = None
                if next_event_time is not None:
                    if next_event_time <= now:
                        poll_timeout_ms = 0
                    else:
                        poll_timeout_ms = (next_event_time - now) * 1000
            self.__poller.register(self.__socket, evt)

            for (sfd, evt) in self.__poller.poll(poll_timeout_ms):
                sock = self.__filenoMap.get(sfd)
                if evt & select.POLLOUT:
                    assert sock == self.__socket
                    try:
                        while transmit_due:
                            tx_record = transmit_due.pop()
                            self.__socket.sendto(tx_record.packed, tx_record.remote)
                            tx_record._decrementTransmissions()
                    except Exception, e:
                        # On EAGAIN, just stop for now (filled output buffer).
                        # On EINTR, could resume now or retry on another loop.
                        # Others are errors.  Need test harness.
                        print 'EndPoint sendto failed: %s' % (e,)
                        raise
                if evt & select.POLLIN:
                    (msg, remote) = sock.recvfrom(8192)
                    rx_record = ReceptionRecord(self, msg, remote)
                    if rx_record.message.transaction_type in (Message.ACK, Message.RST):
                        tx_record = self.__pendingTransmissions.get(rx_record.transaction_id)
                        if tx_record is not None:
                            rx_record._set_pertains_to(tx_record)
                    if sock in self.__discoverySockets:
                        rx_record.reset()
                        rx_record = None
            did_pass = True
        return rx_record
