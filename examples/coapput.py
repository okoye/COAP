import sys
import getopt
import coapy.connection
import time

uri_path = 'sink'
host = 'ns.tzi.org'
port = 61616
verbose = False

try:
    opts, args = getopt.getopt(sys.argv[1:], 'u:h:p:v', [ 'uri-path=', 'host=', 'port=', 'verbose' ])
    for (o, a) in opts:
        if o in ('-u', '--uri-path'):
            uri_path = a
        elif o in ('-h', '--host'):
            host = a
        elif o in ('-p', '--port'):
            port = int(a)
        elif o in ('-v', '--verbose'):
            verbose = True
except getopt.GetoptError, e:
    print 'Option error: %s' % (e,)
    sys.exit(1)

remote = (host, port)
ep = coapy.connection.EndPoint()
ep.socket.bind(('', coapy.COAP_PORT))

def wait_for_response (ep, txr):
    global verbose
    
    while True:
        rxr = ep.process(1000)
        if rxr is None:
            print 'No message received; waiting'
            continue
        if verbose:
            print rxr.message
            print "\n".join(['  %s' % (str(_o),) for _o in rxr.message.options])
            print '  %s' % (rxr.message.payload,)
        if rxr.pertains_to != txr:
            print 'Irrelevant; waiting'
            continue
        return rxr.message

def getResource (ep, uri_path, remote):
    msg = coapy.connection.Message(code=coapy.GET, uri_path=uri_path)
    resp = wait_for_response(ep, ep.send(msg, remote))
    return resp.payload

def putResource (ep, uri_path, remote, value):
    msg = coapy.connection.Message(code=coapy.PUT, payload=value, uri_path=uri_path)
    resp = wait_for_response(ep, ep.send(msg, remote))
    return resp.payload

data = getResource(ep, uri_path, remote)
print 'Initial setting: %s' % (data,)
new_data = 'hello %s' % (time.time(),)
print 'Put value: %s' % (new_data,)
resp = putResource(ep, uri_path, remote, new_data)
print 'Put returned: %s' % (resp,)
data = getResource(ep, uri_path, remote)
print 'Get returned: %s' % (data,)
