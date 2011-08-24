# Demonstration local server.
# In one window:
#  python server.py -D localhost
# In another window:
#  python coapget.py -h localhost -v
#  python coapget.py -h localhost -u uptime
#  python coapget.py -h localhost -u counter
#  python coapget.py -h localhost -u unknown

import sys
import coapy.connection
import coapy.options
import coapy.link
import time
import socket
import getopt

# --verbose (-v): Print all message metadata
verbose = False
port = coapy.COAP_PORT
address_family = socket.AF_INET
# --discovery-addresses csv (-D): Provide a comma-separated list of
#   host names for local interfaces on which CoAP service discovery
#   should be supported.
discovery_addresses = None

try:
    opts, args = getopt.getopt(sys.argv[1:], 'vp:46D:', [ 'verbose', '--port=', '--ipv4', '--ipv6', '--discovery-addresses=' ])
    for (o, a) in opts:
        if o in ('-v', '--verbose'):
            verbose = True
        elif o in ('-p', '--port'):
            port = int(a)
        elif o in ('-4', '--ipv4'):
            address_family = socket.AF_INET
        elif o in ('-6', '--ipv6'):
            address_family = socket.AF_INET6
        elif o in ('-D', '--discovery_addresses'):
            discovery_addresses = a
except getopt.GetoptError, e:
    print 'Option error: %s' % (e,)
    sys.exit(1)

if socket.AF_INET == address_family:
    bind_addr = ('', port)
elif socket.AF_INET6 == address_family:
    bind_addr = ('::', port, 0, 0)
ep = coapy.connection.EndPoint(address_family=address_family)
ep.bind(bind_addr)
if discovery_addresses is not None:
    for da_fqdn in discovery_addresses.split(','):
        ep.bindDiscovery(da_fqdn)

class CounterService (coapy.link.LinkValue):
    __counter = 0

    def process (self, rx_record):
        ctr = self.__counter
        self.__counter += 1
        msg = coapy.connection.Message(coapy.connection.Message.ACK, code=coapy.OK, payload='%d' % (ctr,))
        rx_record.ack(msg)

class AsyncCounterService (coapy.link.LinkValue):
    __counter = 0

    def process (self, rx_record):
        rx_record.ack()
        ctr = self.__counter
        self.__counter += 1
        msg = coapy.connection.Message(coapy.connection.Message.CON, code=coapy.OK, payload='%d delayed' % (ctr,))
        for opt in rx_record.message.options:
            msg.addOption(opt)
        rx_record.end_point.send(msg, rx_record.remote)

class UptimeService (coapy.link.LinkValue):
    __started = time.time()

    def process (self, rx_record):
        uptime = time.time() - self.__started
        msg = coapy.connection.Message(coapy.connection.Message.ACK, code=coapy.OK, payload='%g' % (uptime,))
        rx_record.ack(msg)

class ResourceService (coapy.link.LinkValue):

    __services = None

    def __init__ (self, *args, **kw):
        super(ResourceService, self).__init__('.well-known/r', ct=[coapy.media_types_rev.get('application/link-format')])
        self.__services = { self.uri : self }

    def add_service (self, service):
        self.__services[service.uri] = service
        
    def lookup (self, uri):
        return self.__services.get(uri)

    def process (self, rx_record):
        msg = coapy.connection.Message(coapy.connection.Message.ACK, code=coapy.OK, content_type='application/link-format')
        msg.payload = ",".join([ _s.encode() for _s in self.__services.itervalues() ])
        rx_record.ack(msg)

services = ResourceService()
services.add_service(CounterService('counter'))
services.add_service(UptimeService('uptime'))
services.add_service(AsyncCounterService('async'))

while True:
    rxr = ep.process(10000)
    if rxr is None:
        print 'No activity'
        continue
    print '%s: %s' % (rxr.remote, rxr.message)
    msg = rxr.message
    if coapy.GET != msg.code:
        rxr.reset()
        continue
    uri = msg.findOption(coapy.options.UriPath)
    if uri is None:
        continue
    service = services.lookup(uri.value)
    print 'Lookup %s got %s' % (uri, service)
    if service is None:
        rxr.reset()
        continue
    service.process(rxr)
