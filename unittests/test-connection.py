import unittest
import coapy.options
from coapy.connection import *
import time
import binascii

class Test_is_multicast (unittest.TestCase):
    def testIpv4 (self):
        self.assertFalse(is_multicast(('localhost', 0)))
        self.assertTrue(is_multicast(('224.0.0.1', 0)))
        self.assertTrue(is_multicast(('239.255.255.255', 0)))
        self.assertFalse(is_multicast(('240.0.0.1', 0)))

    def testIpv6 (self):
        self.assertFalse(is_multicast(('::1', 0, 0, 0)))
        self.assertTrue(is_multicast(('ff01::1', 23, 0, 0)))
        self.assertFalse(is_multicast(('fe80::1', 0, 0, 0)))

    def testUnix (self):
        # Unix-domain socket addresses are file system paths.
        self.assertFalse(is_multicast('/dev/null'))

class TestMessage (unittest.TestCase):

    def testConstants (self):
        self.assertEqual(0, Message.CON)
        self.assertEqual('CON', Message._TransactionTypeMap.get(Message.CON))
        self.assertEqual(1, Message.NON)
        self.assertEqual('NON', Message._TransactionTypeMap.get(Message.NON))
        self.assertEqual(2, Message.ACK)
        self.assertEqual('ACK', Message._TransactionTypeMap.get(Message.ACK))
        self.assertEqual(3, Message.RST)
        self.assertEqual('RST', Message._TransactionTypeMap.get(Message.RST))

    def testDefaults (self):
        msg = Message()
        self.assertEqual(Message.CON, msg.transaction_type)
        self.assertEqual(0, msg.code)
        self.assertTrue(isinstance(msg.payload, str))
        self.assertEqual(0, len(msg.payload))
        self.assertTrue(isinstance(msg.options, tuple))
        self.assertEqual(0, len(msg.options))
        packed = msg._pack(0x1234)
        self.assertEqual('\x40\x00\x12\x34', packed)

    def testDecode (self):
        up = coapy.options.UriPath('s')
        opts = set([up])
        payload = '123'
        xid = 0x4321
        (num_opts, opt_data) = coapy.options.encode(opts)
        packed = struct.pack('!BBH', 0x50 + num_opts, coapy.GET, xid) + opt_data + payload
        (txid, msg) = Message.decode(packed)
        self.assertEqual(Message.NON, msg.transaction_type)
        self.assertEqual(xid, txid)
        mopts = msg.options
        self.assertTrue(isinstance(mopts, tuple))
        self.assertEqual(len(opts), len(mopts))
        o = msg.findOption(coapy.options.UriPath)
        self.assertTrue(o is not None)
        self.assertEqual(o.value, up.value)
        self.assertEqual(payload, msg.payload)

    def testMultiOpt (self):
        msg = Message(Message.NON, uri_path='s', uri_authority='host:1234', etag='sth', uri_scheme='coap')
        packed = msg._pack(0x1234)
        print binascii.hexlify(packed)
        opts = msg.options
        self.assertTrue(isinstance(opts, tuple))
        self.assertEqual(4, len(opts))
        self.assertEqual(coapy.options.UriScheme.Type, opts[0].Type) # 3
        self.assertEqual(coapy.options.Etag.Type, opts[1].Type) # 4
        self.assertEqual(coapy.options.UriAuthority.Type, opts[2].Type) # 5
        self.assertEqual(coapy.options.UriPath.Type, opts[3].Type) # 9

class TestEndPoint (unittest.TestCase):

    __endpoint = None
    __address = None
    __socket = None

    __RESPONSE_TIMEOUT = coapy.RESPONSE_TIMEOUT
    __MAX_RETRANSMIT = coapy.MAX_RETRANSMIT

    __send_history = None

    def _faked_sendto (self, message, address):
        self.__send_history.append( (time.time(), message, address) )
        return len(message)

    def setUp (self):
        # Create a temporary file name, and bind a Unix-domain socket to
        # it.  We'll use that for the testing.
        self.__address = os.tmpnam()
        self.__endpoint = EndPoint(address_family=socket.AF_UNIX,
                                   socket_type=socket.SOCK_DGRAM,
                                   socket_proto=0)
        sfd = self.__endpoint.socket
        sfd.bind(self.__address)
        sfd.connect(self.__address)
        self.__socket = sfd
        self._real_sendto = sfd.sendto
        sfd.sendto = self._faked_sendto
        self.__send_history = []

    def tearDown (self):
        # Close the test socket, and remove the temporary file
        sfd = self.__endpoint.socket
        try:
            sfd.close()
        except Exception:
            pass
        os.unlink(self.__address)
        coapy.RESPONSE_TIMEOUT = self.__RESPONSE_TIMEOUT
        coapy.MAX_RETRANSMIT = self.__MAX_RETRANSMIT

    def testPoll (self):
        ep = self.__endpoint
        for duration in ( 0.0, 0.020, 0.050, 0.20, 0.5, 1.0):
            print "poll for %g seconds" % (duration,)
            start = time.time()
            rv = ep.process(1000 * duration)
            done = time.time()
            self.assertAlmostEqual(duration, done - start, 2)

    def testReTransmit (self):
        coapy.RESPONSE_TIMEOUT = 0.010
        m = Message()
        ep = self.__endpoint
        xr = ep.send(m, self.__address)
        self.assertTrue(xr.transaction_id is not None)
        self.assertFalse(xr.next_event_time is None)
        self.assertFalse(xr.is_unacknowledged)
        self.assertEqual(0, len(self.__send_history))
        ep.process(0)
        self.assertEqual(1, len(self.__send_history))
        timeout_ms = 1000 * ((1 << coapy.MAX_RETRANSMIT) + 1) * coapy.RESPONSE_TIMEOUT
        print 'Waiting %g sec for transmission timeout' % (timeout_ms / 1000.0)
        rv = ep.process(timeout_ms)
        self.assertTrue(rv is None)
        self.assertTrue(xr.is_unacknowledged)
        self.assertEqual(coapy.MAX_RETRANSMIT, len(self.__send_history))
        for rep in xrange(coapy.MAX_RETRANSMIT-1):
            lt0 = self.__send_history[rep][0]
            lt1 = self.__send_history[1+rep][0]
            self.assertAlmostEqual(lt1 - lt0, (1 << rep) * coapy.RESPONSE_TIMEOUT, 3)

    def testProcessAck (self):
        coapy.RESPONSE_TIMEOUT = 0.010
        m = Message()
        ep = self.__endpoint
        xr = ep.send(m, self.__address)
        self.assertTrue(xr.response_type is None)
        self.assertTrue(xr.transaction_id is not None)
        self.assertEqual(0, len(self.__send_history))
        rv = ep.process(0)
        self.assertTrue(rv is None)
        self.assertEqual(1, len(self.__send_history))
        ack = Message(Message.ACK)
        self._real_sendto(ack._pack(xr.transaction_id), self.__address)
        rv = ep.process(0)
        self.assertEqual(xr.response_type, Message.ACK)

    def testReceive (self):
        m = Message()
        ep = self.__endpoint

        transaction_id = 0x1234
        packed = m._pack(transaction_id)
        self._real_sendto(packed, self.__address)
        
        self.assertEqual(0, len(self.__send_history))
        rxr = ep.process(0)

        self.assertTrue(isinstance(rxr, ReceptionRecord))
        self.assertEqual(rxr.transaction_id, transaction_id)

        rxr.ack()
        self.assertEqual(1, len(self.__send_history))
        packed = self.__send_history.pop()[1]
        (xid, ack) = Message.decode(packed)
        self.assertEqual(Message.ACK, ack.transaction_type)
        self.assertEqual(xid, transaction_id)
        

if __name__ == '__main__':
    unittest.main()
    
