import unittest
from coapy.constants import *

class TestConstants (unittest.TestCase):
    def test (self):
        self.assertEqual(61616, COAP_PORT)
        self.assertEqual(1, RESPONSE_TIMEOUT)
        self.assertEqual(5, MAX_RETRANSMIT)
                         

if __name__ == '__main__':
    unittest.main()
    
