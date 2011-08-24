import unittest
from coapy.link import *

class Test_PVS_ptoken (unittest.TestCase):
    cases = [ 'token', 'pt<>stuff&more' ]

    def testDecode (self):
        remainder = ',other'
        for token in self.cases:
            self.assertEqual((token, remainder), PVS_ptoken.decode(token + remainder))
        self.assertEqual(('one', ' and two'), PVS_ptoken.decode('one and two'))
        self.assertEqual((None, '"no quotes"'), PVS_ptoken.decode('"no quotes"'))

    def testEncode (self):
        for token in self.cases:
            self.assertEqual((token, ''), PVS_ptoken.decode(PVS_ptoken.encode(token)))

class Test_PVS_dquotedString (unittest.TestCase):
    cases = [ '', 'one', 'one and two']

    def testDecode (self):
        remainder = ',other'
        for token in self.cases:
            self.assertEqual((token, remainder), PVS_dquotedString.decode('"%s"%s' % (token, remainder)))
        self.assertEqual(('no quotes', ''), PVS_dquotedString.decode('"no quotes"'))

    def testEncode (self):
        self.assertEqual('"text"', PVS_dquotedString.encode('text'))
        for token in self.cases:
            self.assertEqual((token, ''), PVS_dquotedString.decode(PVS_dquotedString.encode(token)))

class Test_PVS_unknown (unittest.TestCase):
    cases = [ '', 'one', 'one and two', 'pt<>stuff&more' ]

    def testDecode (self):
        remainder = ',other'
        for token in [ '', 'one', 'one and two']:
            self.assertEqual((token, remainder), PVS_unknown.decode('"%s"%s' % (token, remainder)))
        for token in [ 'token', 'pt<>stuff&more' ]:
            self.assertEqual((token, remainder), PVS_unknown.decode(token + remainder))
        self.assertEqual(('one', ' and two'), PVS_unknown.decode('one and two'))
        self.assertEqual(('no quotes', ''), PVS_unknown.decode('"no quotes"'))

    def testEncode (self):
        self.assertEqual('"one and two"', PVS_unknown.encode('one and two'))
        for token in self.cases:
            self.assertEqual((token, ''), PVS_unknown.decode(PVS_unknown.encode(token)))

class Test_PVS_squotedString (unittest.TestCase):
    cases = [ '', 'one', 'one and two']

    def testDecode (self):
        remainder = ',other'
        for token in self.cases:
            self.assertEqual((token, remainder), PVS_squotedString.decode("'%s'%s" % (token, remainder)))
        self.assertEqual(('no quotes', ''), PVS_squotedString.decode("'no quotes'"))

    def testEncode (self):
        self.assertEqual("'text'", PVS_squotedString.encode('text'))
        for token in self.cases:
            self.assertEqual((token, ''), PVS_squotedString.decode(PVS_squotedString.encode(token)))

class Test_PVS_anglequotedString (unittest.TestCase):
    cases = [ '', 'one', 'one and two', '"dquoted string"', "'squoted string'"]

    def testDecode (self):
        remainder = ',other'
        for token in self.cases:
            self.assertEqual((token, remainder), PVS_anglequotedString.decode("<%s>%s" % (token, remainder)))
        self.assertEqual(('no quotes', ''), PVS_anglequotedString.decode('<no quotes>'))

    def testEncode (self):
        self.assertEqual('<text>', PVS_anglequotedString.encode('text'))
        for token in self.cases:
            self.assertEqual((token, ''), PVS_anglequotedString.decode(PVS_anglequotedString.encode(token)))

class Test_PVS_integer (unittest.TestCase):
    cases = [ 0, 1, 1234 ]

    def testDecode (self):
        (value, remainder) = PVS_integer.decode('1,other')
        self.assertTrue(isinstance(value, int))
        self.assertEqual(value, 1)
        self.assertEqual(remainder, ',other')
        (value, remainder) = PVS_integer.decode('0123,other')
        self.assertTrue(isinstance(value, int))
        self.assertEqual(value, 123)
        self.assertEqual(remainder, ',other')
        for value in self.cases:
            self.assertEqual((value, remainder), PVS_integer.decode('%u%s' % (value, remainder)))
        self.assertEqual((None, ',other'), PVS_integer.decode(',other'))

    def testEncode (self):
        self.assertEqual('33', PVS_integer.encode(0x21))
        for value in self.cases:
            self.assertEqual((value, ''), PVS_integer.decode(PVS_integer.encode(value)))

class Test_PSV_commaSeparatedIntegers (unittest.TestCase):

    def testDecode (self):
        (value, remainder) = PVS_commaSeparatedIntegers.decode('0,1,2,more')
        self.assertTrue(isinstance(value, list))
        self.assertEqual(3, len(value))
        self.assertEqual(',more', remainder)
        self.assertEqual([0, 1, 2], value)
        (value, remainder) = PVS_commaSeparatedIntegers.decode('2,more')
        self.assertTrue(isinstance(value, list))
        self.assertEqual(1, len(value))
        self.assertEqual(2, value[0])
        self.assertEqual(',more', remainder)
        self.assertEqual((None, ',more'), PVS_commaSeparatedIntegers.decode(',more'))

    def testEncode (self):
        self.assertEqual('1', PVS_commaSeparatedIntegers.encode([1]))
        self.assertEqual('1,2', PVS_commaSeparatedIntegers.encode([1, 2]))
        self.assertEqual('2,1', PVS_commaSeparatedIntegers.encode([2, 1]))
        
class Test_decode_resource_descriptions (unittest.TestCase):
    def testResourceDecode (self):
        text = '</hello>;n="hello";ct=0,</secret>;n="secret";ct=0,</sources>;n="sources";ct=40'
        (links, remainder) = decode_resource_descriptions(text)
        self.assertEqual('', remainder)
        self.assertTrue(isinstance(links, list))
        self.assertEqual(3, len(links))
        l1 = links[0]
        self.assertEqual('/hello', l1.uri)
        self.assertEqual('hello', l1.n)
        self.assertEqual([0], l1.ct)
        l1 = links[1]
        self.assertEqual('/secret', l1.uri)
        self.assertEqual('secret', l1.n)
        self.assertEqual([0], l1.ct)
        l1 = links[2]
        self.assertEqual('/sources', l1.uri)
        self.assertEqual('sources', l1.n)
        self.assertEqual([40], l1.ct)
        
if __name__ == '__main__':
    unittest.main()
    
