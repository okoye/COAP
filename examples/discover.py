# Demonstrate CoAP service discovery.
# On one or more nodes, start a CoAP server:
#
#    python examples/server.py -D `hostname`
#
# You may want to add the -p flag to change the end-point port on one or more.
# On some node, start this script.  If running discovery on the same node
# as one of the servers you started, make sure it uses a different end-point port.
#
#   python examples/discover.py
#
# You should see responses from each end-point.
#  End-point response from ('192.168.66.178', 61616)
#  End-point response from ('192.168.66.14', 61616)
#  End-point response from ('192.168.66.174', 53262)
#
# A future version of this demonstration will follow-up by retrieving
# the resources from each endpoint.

import sys
import getopt
import coapy.connection
import coapy.options
import coapy.link
import socket

uri_path = '.well-known/r'
port = coapy.COAP_PORT
interface_address = socket.gethostname()
verbose = False
address_family = socket.AF_INET

try:
    opts, args = getopt.getopt(sys.argv[1:], 'p:v46i:', [ 'port=', 'verbose', '--ipv4', '--ipv6', '--interface-address='])
    for (o, a) in opts:
        if o in ('-v', '--verbose'):
            verbose = True
        elif o in ('-p', '--port'):
            port = int(a)
        elif o in ('-4', '--ipv4'):
            address_family = socket.AF_INET
        elif o in ('-6', '--ipv6'):
            address_family = socket.AF_INET6
        elif o in ('-i', '--interface-address'):
            interface_address = a
except getopt.GetoptError, e:
    print 'Option error: %s' % (e,)
    sys.exit(1)

if socket.AF_INET == address_family:
    bind_addr = ('', port)
elif socket.AF_INET6 == address_family:
    bind_addr = ('::', port, 0, 0)
ep = coapy.connection.EndPoint(address_family=address_family)
ep.bind(bind_addr)

sap_addresses = set()

(if_sockaddr, mc_sockaddr) = coapy.connection.join_discovery(ep.socket, interface_address)
discovery_msg = coapy.connection.Message()

discovery_tx_rec = ep.send(discovery_msg, mc_sockaddr)
tx_rec = discovery_tx_rec

resource_txr = set()

while True:
    rv = ep.process(1000)
    if rv is None:
        print 'No message received; waiting'
        continue
    msg = rv.message
    if verbose:
        print 'RX %s' % (rv,)
        for o in msg.options:
            print ' %s' % (str(o),)
        print ' %s' % (msg.payload,)

    tx_rec = rv.pertains_to
    if tx_rec is None:
        if msg.CON == msg.transaction_type:
            # TODO: improve this check
            if rv.transaction_id == discovery_tx_rec.transaction_id:
                print 'Probably loopback discovery message'
                continue
            rv.reset()
        print 'Response not pertinent; waiting'
        continue
    if tx_rec == discovery_tx_rec:
        print 'End-point response from %s' % (rv.remote,)
        sap_addresses.add(rv.remote)
        msg = coapy.connection.Message(code=coapy.GET, uri_path=".well-known/r")
        resource_txr.add(ep.send(msg, rv.remote))
        continue
    if msg.RST == tx_rec.response_type:
        print 'Server %s responded with reset' % (rv.remote,)
        break
    if coapy.OK != msg.code:
        if 0 != msg.code:
            print 'Pertinent response code not OK: %d (%s)' % (msg.code, coapy.codes.get(msg.code, 'UNDEFINED'))
            break
        print 'Ack for async response'
        tx_rec = None
        continue
    
    ct = msg.findOption(coapy.options.ContentType)
    if (ct is None) or (ct.value_as_string.startswith('text/')):
        print msg.payload
    elif 'application/link-format' == ct.value_as_string:
        (resources, _) = coapy.link.decode_resource_descriptions(msg.payload)
        print '%d resources available at %s on %s:' % (len(resources), uri_path, rv.remote)
        for link in resources:
            print '  %s' % (link.encode(),)
    else:
        print 'Unhandled content type %s: %s' % (ct.value, binascii.hexlify(msg.payload))

