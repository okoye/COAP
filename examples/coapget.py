import sys
import getopt
import coapy.connection
import coapy.options
import coapy.link
import socket

uri_path = '.well-known/r'
host = 'ns.tzi.org'
port = 61616
verbose = False
output_path = None
block_option = None
address_family = socket.AF_INET

try:
    opts, args = getopt.getopt(sys.argv[1:], 'u:h:p:vo:b:46', [ 'uri-path=', 'host=', 'port=', 'verbose', '--output-path=', '--start-block=', '--ipv4', '--ipv6'])
    for (o, a) in opts:
        if o in ('-u', '--uri-path'):
            uri_path = a
        elif o in ('-h', '--host'):
            host = a
        elif o in ('-p', '--port'):
            port = int(a)
        elif o in ('-v', '--verbose'):
            verbose = True
        elif o in ('-o', '--output-path'):
            output_path = a
        elif o in ('-b', '--start-block'):
            block_option = coapy.options.Block(block_number=int(a), size_exponent=coapy.options.Block.MAX_SIZE_EXPONENT)
        elif o in ('-4', '--ipv4'):
            address_family = socket.AF_INET
        elif o in ('-6', '--ipv6'):
            address_family = socket.AF_INET6
except getopt.GetoptError, e:
    print 'Option error: %s' % (e,)
    sys.exit(1)

if socket.AF_INET == address_family:
    remote = (host, port)
elif socket.AF_INET6 == address_family:
    remote = (host, port, 0, 0)
req = coapy.connection.Message(code=coapy.GET, uri_path=uri_path)
if block_option is not None:
    req.addOption(block_option)

ep = coapy.connection.EndPoint(address_family=address_family)
tx_rec = ep.send(req, remote)

outfile = None
if output_path is not None:
    outfile = file(output_path, 'w')

while True:
    rv = ep.process(1000)
    if rv is None:
        print 'No message received; waiting'
        continue
    msg = rv.message
    if verbose:
        print msg
        for o in msg.options:
            print ' %s' % (str(o),)
        print ' %s' % (msg.payload,)

    if tx_rec is None:
        # Pertinent if URI path matches
        if msg.CON != msg.transaction_type:
            print 'Non-confirmable message while awaiting async response'
            continue
        up = msg.findOption(coapy.options.UriPath)
        if up is None:
            print 'Confirmable message no path'
            rv.reset()
            continue
        if up.value != uri_path:
            print 'Confirmable message mismatched path'
            rv.reset()
            continue
        if coapy.OK != msg.code:
            print 'Async pertinent response code not OK: %d (%s)' % (msg.code, coapy.codes.get(msg.code, 'UNDEFINED'))
            rv.ack()
            break
    else:
        if rv.pertains_to != tx_rec:
            print 'Response not pertinent; waiting'
            if msg.CON == msg.transaction_type:
                rv.reset()
            continue
        if msg.RST == tx_rec.response_type:
            print 'Server responded with reset'
            break
        if coapy.OK != msg.code:
            if 0 != msg.code:
                print 'Pertinent response code not OK: %d (%s)' % (msg.code, coapy.codes.get(msg.code, 'UNDEFINED'))
                break
            print 'Ack for async response'
            tx_rec = None
            continue
    
    if outfile is not None:
        outfile.write(msg.payload)

    ct = msg.findOption(coapy.options.ContentType)
    if (ct is None) or (ct.value_as_string.startswith('text/')):
        print msg.payload
    elif 'application/link-format' == ct.value_as_string:
        (resources, _) = coapy.link.decode_resource_descriptions(msg.payload)
        print '%d resources available at %s:' % (len(resources), uri_path)
        for link in resources:
            print '  %s' % (link.encode(),)
    else:
        print 'Unhandled content type %s: %s' % (ct.value, binascii.hexlify(msg.payload))

    block_option = msg.findOption(coapy.options.Block)
    if block_option is None:
        break
    if block_option.more:
        nblk = coapy.options.Block(block_number=block_option.block_number+1, size_exponent=block_option.size_exponent)
        req.replaceOption(nblk)
        tx_rec = ep.send(req, remote)

